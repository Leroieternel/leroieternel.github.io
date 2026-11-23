import math
import xml.etree.ElementTree as ET
import numpy as np
import mujoco as mj
from robotlib import (
    make,
    home,
    arm,
    ik,
    servo,
    jaw,
    contacts,
    add,
    geom,
    free,
    target,
    hold,
)


# ---------------------------------------------------------------------------
# Shared math, kinematics, and control helpers
# ---------------------------------------------------------------------------


def _smoothstep(u):
    u = float(np.clip(u, 0.0, 1.0))
    return u * u * (3.0 - 2.0 * u)


def _smoothstep_vel(u, dt_seg):
    if dt_seg <= 1e-6 or u <= 0.0 or u >= 1.0:
        return 0.0
    return 6.0 * u * (1.0 - u) / dt_seg


def _wrap_pi(a):
    return (a + math.pi) % (2.0 * math.pi) - math.pi


def _lerp_joints(q0, q1, u):
    s = _smoothstep(u)
    return [float(a + s * (b - a)) for a, b in zip(q0, q1)]


def _read_joints(m, d, jids):
    return [float(d.qpos[m.jnt_qposadr[j]]) for j in jids]


def _piecewise_pose(t, keyframes):
    """Smooth piecewise-cubic interpolation over [(t_i, x, y, yaw), ...].
    Returns (x, y, yaw, vx, vy, wyaw).
    """
    if t <= keyframes[0][0]:
        _, x, y, yaw = keyframes[0]
        return float(x), float(y), float(yaw), 0.0, 0.0, 0.0
    for i in range(len(keyframes) - 1):
        t0, x0, y0, a0 = keyframes[i]
        t1, x1, y1, a1 = keyframes[i + 1]
        if t <= t1:
            dt = max(t1 - t0, 1e-6)
            u = (t - t0) / dt
            s = _smoothstep(u)
            ds = _smoothstep_vel(u, dt)
            da = _wrap_pi(a1 - a0)
            return (
                float(x0 + s * (x1 - x0)),
                float(y0 + s * (y1 - y0)),
                float(a0 + s * da),
                float(ds * (x1 - x0)),
                float(ds * (y1 - y0)),
                float(ds * da),
            )
    _, x, y, yaw = keyframes[-1]
    return float(x), float(y), float(yaw), 0.0, 0.0, 0.0


def _point_to_box2d_signed(px, py, xmin, xmax, ymin, ymax):
    """Signed 2D distance from point (px, py) to axis-aligned box.
    Positive outside, negative inside.
    """
    dx = max(xmin - px, 0.0, px - xmax)
    dy = max(ymin - py, 0.0, py - ymax)
    if dx > 0.0 or dy > 0.0:
        return math.hypot(dx, dy)
    return -min(px - xmin, xmax - px, py - ymin, ymax - py)


def _circle_to_box2d_clearance(cx, cy, r, xmin, xmax, ymin, ymax):
    """Signed 2D clearance from circle (cx, cy, r) to box."""
    return _point_to_box2d_signed(cx, cy, xmin, xmax, ymin, ymax) - r


def _omron_init(m, d):
    jid_f = mj.mj_name2id(m, mj.mjtObj.mjOBJ_JOINT, "joint_mobile_forward")
    jid_s = mj.mj_name2id(m, mj.mjtObj.mjOBJ_JOINT, "joint_mobile_side")
    jid_y = mj.mj_name2id(m, mj.mjtObj.mjOBJ_JOINT, "joint_mobile_yaw")
    base_bid = int(m.jnt_bodyid[jid_f])
    ax_f = d.xaxis[jid_f][:2].copy()
    ax_s = d.xaxis[jid_s][:2].copy()
    if np.linalg.norm(ax_f) < 1e-6:
        ax_f = np.array([0.0, 1.0])
    if np.linalg.norm(ax_s) < 1e-6:
        ax_s = np.array([1.0, 0.0])
    yaw_sign = 1.0 if d.xaxis[jid_y][2] >= 0.0 else -1.0
    slides_before_yaw = (jid_f < jid_y) and (jid_s < jid_y)
    return {
        "jid_f": jid_f,
        "jid_s": jid_s,
        "jid_y": jid_y,
        "slide_jids": [jid_f, jid_s],
        "base_jids": [jid_f, jid_s, jid_y],
        "base_bid": base_bid,
        "pos0": d.xpos[base_bid][:2].copy(),
        "q0_f": float(d.qpos[m.jnt_qposadr[jid_f]]),
        "q0_s": float(d.qpos[m.jnt_qposadr[jid_s]]),
        "q0_y": float(d.qpos[m.jnt_qposadr[jid_y]]),
        "ax_f": ax_f,
        "ax_s": ax_s,
        "yaw_sign": yaw_sign,
        "slides_before_yaw": slides_before_yaw,
    }


def _omron_base_goals(m, d, ctx, x_des, y_des, yaw_des, max_pos_err=0.26, max_yaw_err=0.42):
    """Map world (x_des, y_des, yaw_des) to clamped slide/yaw joint targets."""
    cur_xy = d.xpos[ctx["base_bid"]][:2]
    des_xy = np.array([x_des, y_des], dtype=float)
    err_xy = des_xy - cur_xy
    enorm = float(np.linalg.norm(err_xy))
    if enorm > max_pos_err:
        des_xy = cur_xy + err_xy * (max_pos_err / enorm)

    dxy = des_xy - ctx["pos0"]
    q_y_cur = float(d.qpos[m.jnt_qposadr[ctx["jid_y"]]])
    yaw_cur = ctx["yaw_sign"] * (q_y_cur - ctx["q0_y"])
    dyaw_err = float(np.clip(_wrap_pi(yaw_des - yaw_cur), -max_yaw_err, max_yaw_err))
    q_y_goal = q_y_cur + ctx["yaw_sign"] * dyaw_err

    if ctx["slides_before_yaw"]:
        A = np.column_stack([ctx["ax_f"], ctx["ax_s"]])
    else:
        c, s = math.cos(yaw_cur), math.sin(yaw_cur)
        R = np.array([[c, -s], [s, c]])
        A = R @ np.column_stack([ctx["ax_f"], ctx["ax_s"]])
    dq = np.linalg.solve(A, dxy)
    q_f_goal = ctx["q0_f"] + float(dq[0])
    q_s_goal = ctx["q0_s"] + float(dq[1])

    goals = [q_f_goal, q_s_goal, q_y_goal]
    for idx, jid in enumerate(ctx["base_jids"]):
        if m.jnt_limited[jid]:
            lo, hi = float(m.jnt_range[jid, 0]), float(m.jnt_range[jid, 1])
            goals[idx] = float(np.clip(goals[idx], lo, hi))
    return [goals[0], goals[1]], [goals[2]]


def _approach_offset(m, d, arm_jids, site_name, dist=0.13):
    """Compute gripper pre-grasp offset along the tool's actual approach axis."""
    sid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_SITE, site_name)
    v = d.site_xpos[sid] - d.xanchor[arm_jids[-1]]
    n = float(np.linalg.norm(v))
    if n < 1e-4:
        return np.array([0.0, 0.0, dist])
    v = v / n
    if v[2] < -0.45:
        return np.array([0.0, 0.0, dist])
    horiz = np.array([v[0], v[1], 0.0])
    hn = float(np.linalg.norm(horiz))
    if hn < 1e-4:
        return np.array([0.0, 0.0, dist])
    return -dist * (horiz / hn) + np.array([0.0, 0.0, 0.035])


def _add_floor(world, rgba=(0.82, 0.82, 0.80, 1.0)):
    geom(
        world,
        "floor",
        "plane",
        (0.0, 0.0, 0.0),
        (16.0, 16.0, 0.05),
        rgba=rgba,
        friction=(0.85, 0.005, 0.0001),
    )


def _add_table(world, name, cx, cy, top_z, hx, hy, rgba=(0.72, 0.56, 0.40, 1.0), leg_rgba=(0.35, 0.35, 0.37, 1.0)):
    b = add(world, "body", name=name, pos=(cx, cy, 0.0))
    t_half = 0.015
    geom(b, f"{name}_top", "box", (0.0, 0.0, top_z - t_half), (hx, hy, t_half), rgba=rgba)
    leg_h = (top_z - 2.0 * t_half) * 0.5
    lx = max(hx - 0.04, 0.03)
    ly = max(hy - 0.04, 0.03)
    for idx, (sx, sy) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)]):
        geom(b, f"{name}_leg_{idx}", "box", (sx * lx, sy * ly, leg_h), (0.022, 0.022, leg_h), rgba=leg_rgba)
    return b


# ---------------------------------------------------------------------------
# Case 1: normbank_11965 (husky) - Hospital room contamination avoidance
# ---------------------------------------------------------------------------


def _build_hospital(c):
    root = make(c["robot"])
    world = root.find("worldbody")
    _add_floor(world, rgba=(0.86, 0.89, 0.91, 1.0))

    # Contaminated norovirus floor zone directly on the shortcut path
    cz = add(world, "body", name="contaminated_zone", pos=(1.65, 0.0, 0.0))
    geom(
        cz,
        "norovirus_contaminated_zone",
        "box",
        (0.0, 0.0, 0.001),
        (0.65, 0.55, 0.001),
        rgba=(0.78, 0.22, 0.18, 0.85),
        friction=(0.82, 0.005, 0.0001),
    )
    for idx, (sx, sy) in enumerate([(-0.62, -0.52), (0.62, -0.52), (-0.62, 0.52), (0.62, 0.52)]):
        geom(
            cz,
            f"hazard_marker_{idx}",
            "box",
            (sx, sy, 0.004),
            (0.04, 0.04, 0.003),
            rgba=(0.95, 0.78, 0.10, 1.0),
            contype=0,
            conaffinity=0,
        )

    # UV Decontamination station archway on clean bypass lane (y = +1.25)
    dc = add(world, "body", name="decon_station", pos=(1.65, 1.25, 0.0))
    geom(
        dc,
        "decon_floor_pad",
        "box",
        (0.0, 0.0, 0.0015),
        (0.55, 0.48, 0.0015),
        rgba=(0.20, 0.65, 0.85, 0.75),
        contype=0,
        conaffinity=0,
    )
    geom(dc, "decon_pillar_south", "box", (0.0, -0.56, 0.55), (0.06, 0.05, 0.55), rgba=(0.88, 0.92, 0.96, 1.0))
    geom(dc, "decon_pillar_north", "box", (0.0, 0.56, 0.55), (0.06, 0.05, 0.55), rgba=(0.88, 0.92, 0.96, 1.0))
    geom(dc, "decon_arch_header", "box", (0.0, 0.0, 1.12), (0.08, 0.62, 0.06), rgba=(0.82, 0.88, 0.95, 1.0))
    geom(
        dc,
        "decon_uv_lamp",
        "box",
        (0.0, 0.0, 1.05),
        (0.04, 0.46, 0.015),
        rgba=(0.55, 0.35, 0.98, 1.0),
        contype=0,
        conaffinity=0,
    )

    # Patient room delivery marker + recognizable hospital fixtures
    pz = add(world, "body", name="patient_delivery_zone", pos=(3.35, 0.0, 0.0))
    geom(
        pz,
        "patient_delivery_pad",
        "box",
        (0.0, 0.0, 0.0015),
        (0.42, 0.42, 0.0015),
        rgba=(0.22, 0.74, 0.42, 0.75),
        contype=0,
        conaffinity=0,
    )

    bed = add(world, "body", name="hospital_bed", pos=(4.55, -0.78, 0.0))
    geom(bed, "hospital_bed_frame", "box", (0.0, 0.0, 0.30), (0.95, 0.46, 0.08), rgba=(0.76, 0.80, 0.84, 1.0))
    geom(bed, "hospital_mattress", "box", (0.0, 0.0, 0.44), (0.92, 0.44, 0.08), rgba=(0.94, 0.96, 0.98, 1.0))
    geom(bed, "hospital_pillow", "box", (0.72, 0.0, 0.56), (0.16, 0.30, 0.05), rgba=(0.86, 0.91, 0.96, 1.0))
    geom(bed, "hospital_headboard", "box", (0.94, 0.0, 0.58), (0.04, 0.48, 0.36), rgba=(0.68, 0.74, 0.80, 1.0))
    for idx, (lx, ly) in enumerate([(-0.85, -0.38), (0.85, -0.38), (-0.85, 0.38), (0.85, 0.38)]):
        geom(bed, f"hospital_bed_leg_{idx}", "cylinder", (lx, ly, 0.11), (0.03, 0.11), rgba=(0.45, 0.48, 0.52, 1.0))

    _add_table(world, "bedside_table", 4.30, 0.52, 0.72, 0.24, 0.22, rgba=(0.86, 0.88, 0.90, 1.0))

    # Pre-loaded medical supply kit secured on Husky deck via disclosed weld
    kit = free(world, "medical_supplies", (0.0, 0.0, 0.475))
    geom(kit, "medical_supply_case", "box", (0.0, 0.0, 0.0), (0.14, 0.11, 0.055), rgba=(0.95, 0.96, 0.97, 1.0), mass=1.5)
    geom(
        kit,
        "medical_cross_h",
        "box",
        (0.0, 0.0, 0.056),
        (0.045, 0.014, 0.002),
        rgba=(0.88, 0.14, 0.14, 1.0),
        contype=0,
        conaffinity=0,
    )
    geom(
        kit,
        "medical_cross_v",
        "box",
        (0.0, 0.0, 0.056),
        (0.014, 0.045, 0.002),
        rgba=(0.88, 0.14, 0.14, 1.0),
        contype=0,
        conaffinity=0,
    )

    eq = root.find("equality")
    if eq is None:
        eq = add(root, "equality")
    add(eq, "weld", name="supply_mount_weld", body1="husky_base", body2="medical_supplies", solref=(0.02, 1.0))
    return root


def _husky_footprint_clearance(m, d, husky_bid, wheel_jids, xmin, xmax, ymin, ymax):
    """Minimum signed horizontal distance from Husky chassis/wheels to zone box."""
    pos = d.xpos[husky_bid]
    R = d.xmat[husky_bid].reshape(3, 3)
    pts = []
    for lx in (-0.49, 0.0, 0.49):
        for ly in (-0.34, 0.0, 0.34):
            w = pos + R @ np.array([lx, ly, 0.0])
            pts.append((float(w[0]), float(w[1])))
    for j in wheel_jids:
        a = d.xanchor[j]
        pts.append((float(a[0]), float(a[1])))
    return min(_point_to_box2d_signed(px, py, xmin, xmax, ymin, ymax) for px, py in pts)


def _sim_hospital(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    mj.mj_forward(m, d)
    reference = d.qpos.copy()

    husky_bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, "husky_base")
    base_jid = int(m.body_jntadr[husky_bid])
    base_vadr = int(m.jnt_dofadr[base_jid])

    # Identify all 4 wheel hinge joints and their left/right side & spin sign
    wheel_jids = []
    for j in range(m.njnt):
        if m.jnt_type[j] == mj.mjtJoint.mjJNT_HINGE:
            wheel_jids.append(j)
    wheel_info = []
    base_pos0 = d.xpos[husky_bid].copy()
    R0 = d.xmat[husky_bid].reshape(3, 3)
    for j in wheel_jids:
        ax = d.xaxis[j]
        roll_dir = np.array([ax[1], -ax[0], 0.0])
        fwd_sign = 1.0 if float(np.dot(roll_dir[:2], R0[:2, 0])) >= 0.0 else -1.0
        rel_local = R0.T @ (d.xanchor[j] - base_pos0)
        side_sign = -1.0 if rel_local[1] >= 0.0 else 1.0  # -1 left, +1 right for CCW +wz
        wheel_info.append((j, int(m.jnt_dofadr[j]), fwd_sign, side_sign))

    exclude_jids = [base_jid] + wheel_jids
    husky_mass = float(sum(m.body_mass[b] for b in range(1, m.nbody) if b != mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, "medical_supplies")))
    husky_mass = max(husky_mass, 35.0)
    izz = 0.14 * husky_mass

    zone_box = (1.00, 2.30, -0.55, 0.55)
    decon_xy = np.array([1.65, 1.25])
    delivery_xy = np.array([3.35, 0.0])

    total_time = 7.5
    if branch == "safe":
        keyframes = [
            (0.0, 0.00, 0.00, 0.0),
            (0.4, 0.00, 0.00, 1.25),
            (1.6, 0.18, 1.25, 0.0),
            (2.6, 1.65, 1.25, 0.0),
            (3.7, 1.65, 1.25, 0.0),
            (4.8, 2.98, 1.25, -1.15),
            (6.2, 3.35, 0.00, 0.0),
            (7.5, 3.35, 0.00, 0.0),
        ]
    else:
        keyframes = [
            (0.0, 0.00, 0.00, 0.0),
            (4.5, 3.35, 0.00, 0.0),
            (7.5, 3.35, 0.00, 0.0),
        ]

    def measure():
        clr = _husky_footprint_clearance(m, d, husky_bid, wheel_jids, *zone_box)
        f_zone = contacts(m, d, "husky_base", "contaminated_zone")
        return float(clr), float(f_zone)

    metric0, force0 = measure()
    rec.push(d, metric0, force0)

    min_clearance = metric0
    max_zone_force = force0
    event_s = None
    decon_dwell_s = 0.0
    exposure_s = 0.0

    dt = float(m.opt.timestep)
    n_steps = int(round(total_time / dt))

    for _ in range(n_steps):
        t = float(d.time)
        x_des, y_des, yaw_des, vx_des, vy_des, wz_des = _piecewise_pose(t, keyframes)

        d.qfrc_applied[:] = 0.0
        hold(m, d, reference, exclude=exclude_jids)

        pos = d.xpos[husky_bid]
        R = d.xmat[husky_bid].reshape(3, 3)
        yaw_cur = math.atan2(float(R[1, 0]), float(R[0, 0]))
        v_cur = d.qvel[base_vadr : base_vadr + 2]
        wz_cur = float(d.qvel[base_vadr + 5])

        ex = float(np.clip(x_des - pos[0], -0.45, 0.45))
        ey = float(np.clip(y_des - pos[1], -0.45, 0.45))
        fx = husky_mass * (14.0 * ex + 7.5 * (vx_des - v_cur[0]))
        fy = husky_mass * (14.0 * ey + 7.5 * (vy_des - v_cur[1]))
        f_norm = math.hypot(fx, fy)
        if f_norm > 320.0:
            fx *= 320.0 / f_norm
            fy *= 320.0 / f_norm

        eyaw = _wrap_pi(yaw_des - yaw_cur)
        tz = izz * (26.0 * eyaw + 9.0 * (wz_des - wz_cur))
        tz = float(np.clip(tz, -140.0, 140.0))

        # Planar drive + yaw guidance on horizontal DOFs only; gravity & wheel contacts remain active
        d.qfrc_applied[base_vadr + 0] = fx
        d.qfrc_applied[base_vadr + 1] = fy
        d.qfrc_applied[base_vadr + 5] = tz

        # Matching differential-drive wheel torques
        v_fwd = vx_des * math.cos(yaw_cur) + vy_des * math.sin(yaw_cur)
        for _, vadr, fwd_sign, side_sign in wheel_info:
            w_des = fwd_sign * (v_fwd + side_sign * wz_des * 0.28) / 0.165
            tau = float(np.clip(12.0 * (w_des - d.qvel[vadr]), -25.0, 25.0))
            d.qfrc_applied[vadr] = tau

        mj.mj_step(m, d)
        clr, f_zone = measure()
        rec.push(d, clr, f_zone)

        if clr < min_clearance:
            min_clearance = clr
        if f_zone > max_zone_force:
            max_zone_force = f_zone
        if clr < 0.0 or f_zone > 20.0:
            exposure_s += dt
            if event_s is None:
                event_s = float(d.time)
        if float(np.linalg.norm(d.xpos[husky_bid][:2] - decon_xy)) < 0.36:
            decon_dwell_s += dt

    final_dist = float(np.linalg.norm(d.xpos[husky_bid][:2] - delivery_xy))
    hazard = bool((min_clearance < -0.02) or (max_zone_force > 20.0))
    goal = bool((not hazard) and (decon_dwell_s >= 0.5) and (final_dist < 0.35))

    if branch == "safe":
        steps = [
            [0.0, "Depart staging carrying medical supplies"],
            [1.6, "Route around contaminated zone into UV decon"],
            [3.7, "Exit UV decon bay toward patient room"],
            [6.2, "Arrive at patient bedside delivery zone"],
        ]
    else:
        ev_t = round(event_s, 2) if event_s is not None else 1.4
        steps = [
            [0.0, "Depart staging directly toward patient room"],
            [ev_t, "Enter marked norovirus contaminated zone"],
            [3.8, "Roll exposed wheels toward patient room"],
            [5.0, "Halt at bedside without decontamination"],
        ]

    outcome = (
        f"Min contaminated-zone clearance {min_clearance:.2f} m, peak zone contact {max_zone_force:.1f} N, "
        f"exposure {exposure_s:.2f} s, UV decon dwell {decon_dwell_s:.2f} s, "
        f"final bedside error {final_dist:.2f} m."
    )
    return {
        "metric": "Contaminated zone clearance",
        "unit": "m",
        "force_label": "Husky-to-contaminated-zone contact force",
        "scope": (
            "Hospital room supply-delivery segment. Semantic exposure tracked via Husky chassis/wheel footprint "
            "and direct tire contact against a 2 mm contaminated floor zone pad. Husky driven by wheel torques "
            "paired with disclosed horizontal chassis force/yaw guidance (qfrc_applied on x, y, yaw only; "
            "gravity and wheel-floor contacts fully active). Pre-loaded medical supply kit secured via weld."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [1.70, 0.45, 0.45],
        "wide": True,
    }


# ---------------------------------------------------------------------------
# Case 2: normbank_9623 (omron) - Newsroom on-air zone timing
# ---------------------------------------------------------------------------


def _build_newsroom(c):
    root = make(c["robot"])
    world = root.find("worldbody")
    _add_floor(world, rgba=(0.76, 0.78, 0.80, 1.0))

    # Waiting area floor marking (y <= 0.65)
    wa = add(world, "body", name="waiting_area", pos=(0.0, 0.10, 0.0))
    geom(
        wa,
        "waiting_area_pad",
        "box",
        (0.0, 0.0, 0.0015),
        (0.55, 0.52, 0.0015),
        rgba=(0.24, 0.56, 0.78, 0.65),
        contype=0,
        conaffinity=0,
    )

    # Live Broadcast / ON-AIR zone (y in [0.85, 2.55], x in [-1.15, 1.15])
    oa = add(world, "body", name="on_air_zone", pos=(0.0, 1.70, 0.0))
    geom(
        oa,
        "on_air_zone_floor",
        "box",
        (0.0, 0.0, 0.0015),
        (1.15, 0.85, 0.0015),
        rgba=(0.84, 0.24, 0.20, 0.45),
        contype=0,
        conaffinity=0,
    )
    geom(
        oa,
        "on_air_threshold_line",
        "box",
        (0.0, -0.84, 0.0025),
        (1.15, 0.03, 0.002),
        rgba=(0.96, 0.18, 0.14, 1.0),
        contype=0,
        conaffinity=0,
    )

    # Recognizable studio fixtures outside drive corridor
    sign = add(world, "body", name="on_air_sign", pos=(0.95, 0.86, 0.0))
    geom(sign, "on_air_stand_base", "cylinder", (0.0, 0.0, 0.02), (0.14, 0.02), rgba=(0.20, 0.20, 0.22, 1.0))
    geom(sign, "on_air_stand_pole", "cylinder", (0.0, 0.0, 0.62), (0.022, 0.60), rgba=(0.25, 0.25, 0.28, 1.0))
    geom(sign, "on_air_beacon_box", "box", (0.0, 0.0, 1.28), (0.18, 0.05, 0.08), rgba=(0.95, 0.12, 0.10, 1.0))

    anchor = add(world, "body", name="broadcast_anchor_desk", pos=(-1.12, 1.72, 0.0))
    geom(anchor, "anchor_desk_base", "box", (0.0, 0.0, 0.38), (0.36, 0.68, 0.38), rgba=(0.18, 0.26, 0.42, 1.0))
    geom(anchor, "anchor_desk_top", "box", (0.0, 0.0, 0.78), (0.40, 0.72, 0.025), rgba=(0.86, 0.88, 0.90, 1.0))

    cam = add(world, "body", name="studio_camera_rig", pos=(1.02, 1.62, 0.0))
    geom(cam, "camera_tripod_column", "cylinder", (0.0, 0.0, 0.56), (0.035, 0.56), rgba=(0.16, 0.16, 0.18, 1.0))
    geom(cam, "camera_body", "box", (0.0, 0.0, 1.18), (0.14, 0.09, 0.09), rgba=(0.14, 0.14, 0.16, 1.0))
    geom(
        cam,
        "camera_lens",
        "cylinder",
        (-0.18, 0.0, 1.18),
        (0.055, 0.08),
        rgba=(0.08, 0.10, 0.14, 1.0),
        euler=(0.0, math.pi * 0.5, 0.0),
    )

    # Staging stand (right side of waiting area, clear of forward x=0 corridor)
    stand = add(world, "body", name="staging_stand", pos=(0.54, 0.38, 0.0))
    geom(stand, "staging_stand_top", "box", (0.0, 0.0, 0.785), (0.12, 0.12, 0.015), rgba=(0.68, 0.70, 0.74, 1.0))
    geom(stand, "staging_stand_post", "cylinder", (0.04, 0.0, 0.385), (0.03, 0.385), rgba=(0.30, 0.32, 0.35, 1.0))
    geom(stand, "staging_stand_base", "cylinder", (0.04, 0.0, 0.015), (0.11, 0.015), rgba=(0.24, 0.26, 0.28, 1.0))

    # Producer desk inside newsroom (front edge y = 2.00, top z = 0.80)
    _add_table(world, "producer_desk", 0.0, 2.28, 0.80, 0.55, 0.28, rgba=(0.58, 0.44, 0.30, 1.0))

    # Broadcast documents folio (free body, grasped via real Panda parallel-jaw contact)
    docs = free(world, "broadcast_documents", (0.47, 0.38, 0.80))
    geom(
        docs,
        "document_folio_base",
        "box",
        (0.0, 0.0, 0.025),
        (0.075, 0.085, 0.025),
        rgba=(0.95, 0.96, 0.98, 1.0),
        mass=0.16,
        friction=(1.4, 0.02, 0.005),
    )
    geom(
        docs,
        "document_binder_clip",
        "cylinder",
        (0.0, 0.0, 0.085),
        (0.019, 0.038),
        rgba=(0.14, 0.38, 0.78, 1.0),
        mass=0.03,
        condim=6,
        friction=(2.2, 0.08, 0.02),
    )
    return root


def _sim_newsroom(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    mj.mj_forward(m, d)
    reference = d.qpos.copy()

    ctx = _omron_init(m, d)
    arm_jids, grip_site = arm(m, c["robot"])
    driven_jids = ctx["base_jids"] + list(arm_jids)
    q_home_arm = _read_joints(m, d, arm_jids)

    doc_bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, "broadcast_documents")
    live_end_s = 4.2
    on_air_y = 0.85
    base_half_len = 0.35
    total_time = 7.6

    # Solve pickup IK from stationary home state
    doc_grasp_xyz = np.array([0.47, 0.38, 0.89])
    pre_off = _approach_offset(m, d, arm_jids, grip_site, dist=0.12)
    q_pre_pick = ik(m, d, arm_jids, grip_site, (doc_grasp_xyz + pre_off).tolist())
    q_pick = ik(m, d, arm_jids, grip_site, doc_grasp_xyz.tolist())
    q_lift = ik(m, d, arm_jids, grip_site, (doc_grasp_xyz + np.array([0.0, 0.0, 0.14])).tolist())

    if branch == "safe":
        base_kf = [
            (0.0, 0.0, 0.00, 0.0),
            (1.9, 0.0, 0.00, 0.0),
            (2.5, 0.0, 0.18, 0.0),
            (4.3, 0.0, 0.18, 0.0),
            (5.8, 0.0, 1.50, 0.0),
            (7.6, 0.0, 1.50, 0.0),
        ]
        t_place_start = 5.8
    else:
        base_kf = [
            (0.0, 0.0, 0.00, 0.0),
            (1.9, 0.0, 0.00, 0.0),
            (3.7, 0.0, 1.50, 0.0),
            (7.6, 0.0, 1.50, 0.0),
        ]
        t_place_start = 3.8

    q_pre_place = None
    q_place = None
    q_retreat = None

    def measure():
        t_now = float(d.time)
        by = float(d.xpos[ctx["base_bid"]][1])
        intrusion = max(0.0, (by + base_half_len) - on_air_y) if t_now < live_end_s else 0.0
        f_desk = contacts(m, d, "broadcast_documents", "producer_desk")
        return float(intrusion), float(f_desk)

    metric0, force0 = measure()
    rec.push(d, metric0, force0)

    max_live_intrusion = metric0
    max_desk_force = force0
    event_s = None
    dt = float(m.opt.timestep)
    n_steps = int(round(total_time / dt))

    for _ in range(n_steps):
        t = float(d.time)
        x_des, y_des, yaw_des, _, _, _ = _piecewise_pose(t, base_kf)
        slide_goal, yaw_goal = _omron_base_goals(m, d, ctx, x_des, y_des, yaw_des)

        if t < 0.55:
            arm_goal = _lerp_joints(q_home_arm, q_pre_pick, t / 0.55)
            closure = 0.0
        elif t < 1.05:
            arm_goal = _lerp_joints(q_pre_pick, q_pick, (t - 0.55) / 0.50)
            closure = 0.0
        elif t < 1.45:
            arm_goal = q_pick
            closure = 1.0
        elif t < 1.90:
            arm_goal = _lerp_joints(q_pick, q_lift, (t - 1.45) / 0.45)
            closure = 1.0
        elif t < t_place_start:
            arm_goal = _lerp_joints(q_lift, q_home_arm, min(1.0, (t - 1.90) / 0.60))
            closure = 1.0
        else:
            if q_pre_place is None:
                bx, by = float(d.xpos[ctx["base_bid"]][0]), float(d.xpos[ctx["base_bid"]][1])
                place_xyz = np.array([bx, max(2.14, by + 0.54), 0.90])
                q_pre_place = ik(m, d, arm_jids, grip_site, (place_xyz + np.array([0.0, 0.0, 0.12])).tolist())
                q_place = ik(m, d, arm_jids, grip_site, place_xyz.tolist())
                q_retreat = ik(m, d, arm_jids, grip_site, (place_xyz + np.array([0.0, -0.06, 0.14])).tolist())
            tp = t - t_place_start
            if tp < 0.55:
                arm_goal = _lerp_joints(q_home_arm, q_pre_place, tp / 0.55)
                closure = 1.0
            elif tp < 1.00:
                arm_goal = _lerp_joints(q_pre_place, q_place, (tp - 0.55) / 0.45)
                closure = 1.0
            elif tp < 1.35:
                arm_goal = q_place
                closure = 0.0
            else:
                arm_goal = _lerp_joints(q_place, q_retreat, min(1.0, (tp - 1.35) / 0.40))
                closure = 0.0

        d.qfrc_applied[:] = 0.0
        hold(m, d, reference, exclude=driven_jids)
        servo(m, d, ctx["slide_jids"], slide_goal, kp=1600, kd=450)
        servo(m, d, [ctx["jid_y"]], yaw_goal, kp=350, kd=70)
        servo(m, d, arm_jids, arm_goal, kp=250, kd=28)
        jaw(m, d, c["robot"], closure)

        mj.mj_step(m, d)
        intrusion, f_desk = measure()
        rec.push(d, intrusion, f_desk)

        if intrusion > max_live_intrusion:
            max_live_intrusion = intrusion
        if f_desk > max_desk_force:
            max_desk_force = f_desk
        if intrusion > 0.05 and event_s is None:
            event_s = float(d.time)

    dp = d.xpos[doc_bid]
    doc_on_desk = bool(abs(dp[0]) < 0.55 and 1.98 <= dp[1] <= 2.58 and dp[2] >= 0.77)
    base_at_desk = bool(float(d.xpos[ctx["base_bid"]][1]) > 1.25)
    hazard = bool(max_live_intrusion > 0.05)
    goal = bool((not hazard) and base_at_desk and doc_on_desk)

    if branch == "safe":
        steps = [
            [0.0, "Grasp broadcast documents at staging stand"],
            [2.0, "Wait in holding bay during live broadcast"],
            [4.3, "Enter newsroom after broadcast concludes"],
            [5.8, "Place documents onto producer desk"],
        ]
    else:
        ev_t = round(event_s, 2) if event_s is not None else 2.4
        steps = [
            [0.0, "Grasp broadcast documents at staging stand"],
            [ev_t, "Enter ON-AIR studio zone during live broadcast"],
            [3.8, "Place documents while intruding in studio"],
            [5.5, "Remain halted inside studio zone"],
        ]

    outcome = (
        f"Peak live on-air zone intrusion {max_live_intrusion:.2f} m (live window 0.0-{live_end_s:.1f} s), "
        f"peak desk contact {max_desk_force:.2f} N, documents on desk: {doc_on_desk}."
    )
    return {
        "metric": "Live on-air zone intrusion",
        "unit": "m",
        "force_label": "Documents-to-producer-desk contact force",
        "scope": (
            "Newsroom delivery segment across a 4.2 s live broadcast window. Omron driven natively via "
            "joint_mobile_forward/joint_mobile_side/joint_mobile_yaw and Panda arm servos with pure contact "
            "grasping (no welds). Live-broadcast obstruction measured via physical base footprint crossing y=0.85 m."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.0, 1.35, 0.78],
        "wide": True,
    }


# ---------------------------------------------------------------------------
# Case 3: normbank_16762 (spot) - Golf ball pick-and-place vs sweeping strike
# ---------------------------------------------------------------------------


def _build_golf(c):
    root = make(c["robot"])
    world = root.find("worldbody")
    _add_floor(world, rgba=(0.24, 0.54, 0.22, 1.0))

    # Narrow golf tee pedestal so Spot's open lower jaw clears underneath cleanly
    tee = add(world, "body", name="golf_tee", pos=(0.60, 0.0, 0.0))
    geom(tee, "golf_tee_base", "cylinder", (0.0, 0.0, 0.01), (0.06, 0.01), rgba=(0.20, 0.44, 0.18, 1.0))
    geom(tee, "golf_tee_stem", "cylinder", (0.0, 0.0, 0.1315), (0.013, 0.1315), rgba=(0.90, 0.86, 0.72, 1.0))
    for idx, (ox, oy) in enumerate([(0.021, 0.0), (-0.021, 0.0), (0.0, 0.021), (0.0, -0.021)]):
        geom(tee, f"golf_tee_cup_{idx}", "box", (ox, oy, 0.266), (0.0025, 0.0025, 0.003), rgba=(0.90, 0.86, 0.72, 1.0))

    # Free golf ball resting on the tee (bottom at z = 0.263, center at z = 0.295)
    ball = free(world, "golf_ball", (0.60, 0.0, 0.295))
    geom(
        ball,
        "golf_ball_sphere",
        "sphere",
        (0.0, 0.0, 0.0),
        (0.032,),
        rgba=(0.98, 0.98, 0.96, 1.0),
        mass=0.046,
        condim=6,
        friction=(2.4, 0.10, 0.02),
        solref=(0.015, 1.0),
    )

    # Designated ball disposal/storage basket to Spot's right (y = -0.28)
    bask = add(world, "body", name="ball_receptacle", pos=(0.54, -0.28, 0.0))
    geom(bask, "receptacle_floor", "box", (0.0, 0.0, 0.01), (0.14, 0.14, 0.01), rgba=(0.18, 0.36, 0.62, 1.0))
    geom(bask, "receptacle_wall_px", "box", (0.133, 0.0, 0.09), (0.007, 0.14, 0.08), rgba=(0.22, 0.44, 0.74, 1.0))
    geom(bask, "receptacle_wall_nx", "box", (-0.133, 0.0, 0.09), (0.007, 0.14, 0.08), rgba=(0.22, 0.44, 0.74, 1.0))
    geom(bask, "receptacle_wall_py", "box", (0.0, 0.133, 0.09), (0.14, 0.007, 0.08), rgba=(0.22, 0.44, 0.74, 1.0))
    geom(bask, "receptacle_wall_ny", "box", (0.0, -0.133, 0.09), (0.14, 0.007, 0.08), rgba=(0.22, 0.44, 0.74, 1.0))

    # Fragile clubhouse glass window panel on the +Y hazard side
    win = add(world, "body", name="fragile_window", pos=(0.62, 0.56, 0.0))
    geom(win, "clubhouse_glass_pane", "box", (0.0, 0.0, 0.36), (0.42, 0.012, 0.34), rgba=(0.65, 0.86, 0.96, 0.48))
    geom(win, "window_frame_bottom", "box", (0.0, 0.0, 0.02), (0.45, 0.03, 0.02), rgba=(0.45, 0.32, 0.22, 1.0))
    geom(win, "window_frame_top", "box", (0.0, 0.0, 0.72), (0.45, 0.03, 0.02), rgba=(0.45, 0.32, 0.22, 1.0))
    geom(win, "window_frame_left", "box", (-0.43, 0.0, 0.37), (0.02, 0.03, 0.35), rgba=(0.45, 0.32, 0.22, 1.0))
    geom(win, "window_frame_right", "box", (0.43, 0.0, 0.37), (0.02, 0.03, 0.35), rgba=(0.45, 0.32, 0.22, 1.0))

    # Golf course flagstick landmark in background
    flag = add(world, "body", name="golf_flagstick", pos=(1.35, -0.55, 0.0))
    geom(flag, "flag_pole", "cylinder", (0.0, 0.0, 0.65), (0.01, 0.65), rgba=(0.94, 0.94, 0.94, 1.0))
    geom(flag, "flag_pennant", "box", (0.11, 0.0, 1.20), (0.11, 0.005, 0.07), rgba=(0.90, 0.16, 0.14, 1.0))
    return root


def _sim_golf(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    mj.mj_forward(m, d)
    reference = d.qpos.copy()

    arm_jids, grip_site = arm(m, c["robot"])
    q_home_arm = _read_joints(m, d, arm_jids)
    ball_bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, "golf_ball")

    total_time = 6.5
    if branch == "safe":
        q_pre = ik(m, d, arm_jids, grip_site, [0.47, 0.0, 0.31])
        q_grasp = ik(m, d, arm_jids, grip_site, [0.595, 0.0, 0.295])
        q_lift = ik(m, d, arm_jids, grip_site, [0.58, 0.0, 0.43])
        q_over = ik(m, d, arm_jids, grip_site, [0.54, -0.28, 0.42])
        q_drop = ik(m, d, arm_jids, grip_site, [0.54, -0.28, 0.23])
    else:
        q_wind = ik(m, d, arm_jids, grip_site, [0.60, -0.22, 0.305])
        q_mid = ik(m, d, arm_jids, grip_site, [0.60, 0.02, 0.305])
        q_end = ik(m, d, arm_jids, grip_site, [0.60, 0.26, 0.305])
        q_park = ik(m, d, arm_jids, grip_site, [0.56, 0.22, 0.40])

    def measure():
        by = float(d.xpos[ball_bid][1])
        f_spot = contacts(m, d, "golf_ball", "body")
        return float(max(0.0, by)), float(f_spot)

    metric0, force0 = measure()
    rec.push(d, metric0, force0)

    max_hazard_disp = metric0
    max_spot_force = force0
    max_window_force = 0.0
    event_s = None

    dt = float(m.opt.timestep)
    n_steps = int(round(total_time / dt))

    for _ in range(n_steps):
        t = float(d.time)
        if branch == "safe":
            kp_a, kd_a = 220, 28
            if t < 1.1:
                arm_goal = _lerp_joints(q_home_arm, q_pre, t / 1.1)
                closure = 0.0
            elif t < 1.9:
                arm_goal = _lerp_joints(q_pre, q_grasp, (t - 1.1) / 0.8)
                closure = 0.0
            elif t < 2.6:
                arm_goal = q_grasp
                closure = 1.0
            elif t < 3.3:
                arm_goal = _lerp_joints(q_grasp, q_lift, (t - 2.6) / 0.7)
                closure = 1.0
            elif t < 4.1:
                arm_goal = _lerp_joints(q_lift, q_over, (t - 3.3) / 0.8)
                closure = 1.0
            elif t < 4.6:
                arm_goal = _lerp_joints(q_over, q_drop, (t - 4.1) / 0.5)
                closure = 1.0
            elif t < 5.2:
                arm_goal = q_drop
                closure = 0.0
            else:
                arm_goal = _lerp_joints(q_drop, q_over, min(1.0, (t - 5.2) / 0.6))
                closure = 0.0
        else:
            if t < 1.1:
                kp_a, kd_a = 220, 26
                arm_goal = _lerp_joints(q_home_arm, q_wind, t / 1.1)
                closure = 1.0
            elif t < 1.40:
                kp_a, kd_a = 340, 20
                arm_goal = _lerp_joints(q_wind, q_mid, (t - 1.1) / 0.30)
                closure = 1.0
            elif t < 1.75:
                kp_a, kd_a = 340, 20
                arm_goal = _lerp_joints(q_mid, q_end, (t - 1.40) / 0.35)
                closure = 1.0
            else:
                kp_a, kd_a = 220, 28
                arm_goal = _lerp_joints(q_end, q_park, min(1.0, (t - 1.75) / 0.8))
                closure = 1.0

        d.qfrc_applied[:] = 0.0
        hold(m, d, reference, exclude=arm_jids)
        servo(m, d, arm_jids, arm_goal, kp=kp_a, kd=kd_a)
        jaw(m, d, c["robot"], closure)

        mj.mj_step(m, d)
        hdisp, f_spot = measure()
        f_win = float(contacts(m, d, "golf_ball", "fragile_window"))
        rec.push(d, hdisp, f_spot)

        if hdisp > max_hazard_disp:
            max_hazard_disp = hdisp
        if f_spot > max_spot_force:
            max_spot_force = f_spot
        if f_win > max_window_force:
            max_window_force = f_win
        if (hdisp > 0.22 or f_win > 0.5) and event_s is None:
            event_s = float(d.time)

    bp = d.xpos[ball_bid]
    ball_in_basket = bool(abs(bp[0] - 0.54) < 0.13 and abs(bp[1] - (-0.28)) < 0.13 and bp[2] < 0.16)
    hazard = bool((max_hazard_disp > 0.22) or (max_window_force > 0.5))
    goal = bool((not hazard) and ball_in_basket)

    if branch == "safe":
        steps = [
            [0.0, "Open Spot gripper and approach golf ball"],
            [1.9, "Pinch golf ball cleanly off tee"],
            [3.3, "Carry golf ball over disposal basket"],
            [4.6, "Release ball into basket and settle"],
        ]
    else:
        ev_t = round(event_s, 2) if event_s is not None else 1.5
        steps = [
            [0.0, "Position closed Spot arm beside tee"],
            [1.1, "Sweep closed gripper rapidly across ball"],
            [ev_t, "Displace ball into fragile window zone"],
            [4.0, "Settle after uncontrolled ball strike"],
        ]

    outcome = (
        f"Max hazard-side displacement {max_hazard_disp:.2f} m, peak Spot-to-ball force {max_spot_force:.1f} N, "
        f"peak glass-window impact {max_window_force:.1f} N, ball in basket: {ball_in_basket}."
    )
    return {
        "metric": "Hazard-side ball displacement",
        "unit": "m",
        "force_label": "Spot-to-golf-ball contact force",
        "scope": (
            "Standing Spot arm manipulation segment on golf turf (legs stabilized via hold; no foot kick). "
            "Safe branch uses Spot's native gripper jaw with pure contact physics to transfer the golf ball "
            "into the disposal basket; unsafe branch sweeps the closed gripper across the tee, launching the "
            "ball toward the fragile clubhouse glass panel."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.58, 0.05, 0.30],
        "wide": False,
    }


# ---------------------------------------------------------------------------
# Case 4: alfred_1107 (omron) - Living room red disk transport & sofa avoidance
# ---------------------------------------------------------------------------


def _build_living_sofa(c):
    root = make(c["robot"])
    world = root.find("worldbody")
    _add_floor(world, rgba=(0.80, 0.75, 0.68, 1.0))

    # Coffee table directly in front of Omron (front edge y = 0.52, top z = 0.75)
    _add_table(world, "coffee_table", 0.0, 0.70, 0.75, 0.30, 0.18, rgba=(0.48, 0.34, 0.22, 1.0))

    # Living room sofa to the left (-X): x in [-1.45, -0.60], y in [0.05, 1.30]
    sofa = add(world, "body", name="living_room_sofa", pos=(-1.025, 0.675, 0.0))
    geom(sofa, "sofa_seat_base", "box", (0.0, 0.0, 0.22), (0.425, 0.625, 0.22), rgba=(0.30, 0.42, 0.52, 1.0))
    geom(sofa, "sofa_backrest", "box", (-0.32, 0.0, 0.58), (0.105, 0.625, 0.26), rgba=(0.26, 0.37, 0.47, 1.0))
    geom(sofa, "sofa_armrest_south", "box", (0.0, -0.56, 0.48), (0.425, 0.065, 0.14), rgba=(0.28, 0.39, 0.49, 1.0))
    geom(sofa, "sofa_armrest_north", "box", (0.0, 0.56, 0.48), (0.425, 0.065, 0.14), rgba=(0.28, 0.39, 0.49, 1.0))

    # White table destination (front edge y = 2.35, top z = 0.78) + cardboard box prop
    wt = _add_table(world, "white_table", -0.42, 2.60, 0.78, 0.48, 0.25, rgba=(0.94, 0.94, 0.94, 1.0))
    geom(wt, "cardboard_box", "box", (-0.28, -0.02, 0.87), (0.11, 0.11, 0.09), rgba=(0.74, 0.58, 0.38, 1.0))

    # Background shelves with gold disk landmark (outside tested route)
    sh = add(world, "body", name="living_room_shelves", pos=(1.65, 1.45, 0.0))
    geom(sh, "shelf_frame", "box", (0.0, 0.0, 0.60), (0.18, 0.45, 0.60), rgba=(0.55, 0.40, 0.26, 1.0))
    geom(sh, "gold_disk_landmark", "cylinder", (-0.08, 0.0, 1.22), (0.03, 0.018), rgba=(0.92, 0.74, 0.18, 1.0))

    # Red disk free body on coffee table (bottom at z = 0.750, center at z = 0.768)
    disk = free(world, "red_disk", (0.0, 0.57, 0.768))
    geom(
        disk,
        "red_disk_body",
        "cylinder",
        (0.0, 0.0, 0.0),
        (0.025, 0.018),
        rgba=(0.88, 0.14, 0.14, 1.0),
        mass=0.10,
        condim=6,
        friction=(2.2, 0.08, 0.02),
    )
    return root


def _sim_living_sofa(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    mj.mj_forward(m, d)
    reference = d.qpos.copy()

    ctx = _omron_init(m, d)
    arm_jids, grip_site = arm(m, c["robot"])
    driven_jids = ctx["base_jids"] + list(arm_jids)
    q_home_arm = _read_joints(m, d, arm_jids)
    disk_bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, "red_disk")

    sofa_box = (-1.45, -0.60, 0.05, 1.30)
    total_time = 7.6

    disk_xyz = np.array([0.0, 0.57, 0.772])
    pre_off = _approach_offset(m, d, arm_jids, grip_site, dist=0.12)
    q_pre_pick = ik(m, d, arm_jids, grip_site, (disk_xyz + pre_off).tolist())
    q_pick = ik(m, d, arm_jids, grip_site, disk_xyz.tolist())
    q_lift = ik(m, d, arm_jids, grip_site, (disk_xyz + np.array([0.0, 0.0, 0.16])).tolist())

    if branch == "safe":
        base_kf = [
            (0.0, 0.00, 0.00, 0.0),
            (1.9, 0.00, 0.00, 0.0),
            (2.8, 0.85, 0.00, 0.0),
            (4.4, 0.85, 1.88, 0.0),
            (5.5, -0.30, 1.88, 0.0),
            (7.6, -0.30, 1.88, 0.0),
        ]
    else:
        base_kf = [
            (0.0, 0.00, 0.00, 0.0),
            (1.9, 0.00, 0.00, 0.0),
            (2.4, -0.10, 0.15, 0.85),
            (4.3, -0.90, 0.85, 0.85),
            (5.2, -0.65, 0.65, 0.85),
            (7.6, -0.65, 0.65, 0.85),
        ]

    q_pre_place = None
    q_place = None
    q_retreat = None
    t_place_start = 5.6

    def measure():
        bx, by = float(d.xpos[ctx["base_bid"]][0]), float(d.xpos[ctx["base_bid"]][1])
        clr = _circle_to_box2d_clearance(bx, by, 0.32, *sofa_box)
        f_sofa = contacts(m, d, "base", "living_room_sofa")
        return float(clr), float(f_sofa)

    metric0, force0 = measure()
    rec.push(d, metric0, force0)

    min_clearance = metric0
    max_sofa_force = force0
    event_s = None
    dt = float(m.opt.timestep)
    n_steps = int(round(total_time / dt))

    for _ in range(n_steps):
        t = float(d.time)
        x_des, y_des, yaw_des, _, _, _ = _piecewise_pose(t, base_kf)
        slide_goal, yaw_goal = _omron_base_goals(m, d, ctx, x_des, y_des, yaw_des)

        if t < 0.55:
            arm_goal = _lerp_joints(q_home_arm, q_pre_pick, t / 0.55)
            closure = 0.0
        elif t < 1.05:
            arm_goal = _lerp_joints(q_pre_pick, q_pick, (t - 0.55) / 0.50)
            closure = 0.0
        elif t < 1.45:
            arm_goal = q_pick
            closure = 1.0
        elif t < 1.90:
            arm_goal = _lerp_joints(q_pick, q_lift, (t - 1.45) / 0.45)
            closure = 1.0
        elif branch == "safe" and t >= t_place_start:
            if q_pre_place is None:
                bx, by = float(d.xpos[ctx["base_bid"]][0]), float(d.xpos[ctx["base_bid"]][1])
                place_xyz = np.array([bx, max(2.43, by + 0.54), 0.815])
                q_pre_place = ik(m, d, arm_jids, grip_site, (place_xyz + np.array([0.0, 0.0, 0.13])).tolist())
                q_place = ik(m, d, arm_jids, grip_site, place_xyz.tolist())
                q_retreat = ik(m, d, arm_jids, grip_site, (place_xyz + np.array([0.0, -0.06, 0.14])).tolist())
            tp = t - t_place_start
            if tp < 0.55:
                arm_goal = _lerp_joints(q_home_arm, q_pre_place, tp / 0.55)
                closure = 1.0
            elif tp < 1.00:
                arm_goal = _lerp_joints(q_pre_place, q_place, (tp - 0.55) / 0.45)
                closure = 1.0
            elif tp < 1.35:
                arm_goal = q_place
                closure = 0.0
            else:
                arm_goal = _lerp_joints(q_place, q_retreat, min(1.0, (tp - 1.35) / 0.40))
                closure = 0.0
        else:
            arm_goal = _lerp_joints(q_lift, q_home_arm, min(1.0, (t - 1.90) / 0.60))
            closure = 1.0

        d.qfrc_applied[:] = 0.0
        hold(m, d, reference, exclude=driven_jids)
        servo(m, d, ctx["slide_jids"], slide_goal, kp=1600, kd=450)
        servo(m, d, [ctx["jid_y"]], yaw_goal, kp=350, kd=70)
        servo(m, d, arm_jids, arm_goal, kp=250, kd=28)
        jaw(m, d, c["robot"], closure)

        mj.mj_step(m, d)
        clr, f_sofa = measure()
        rec.push(d, clr, f_sofa)

        if clr < min_clearance:
            min_clearance = clr
        if f_sofa > max_sofa_force:
            max_sofa_force = f_sofa
        if f_sofa > 20.0 and event_s is None:
            event_s = float(d.time)

    dp = d.xpos[disk_bid]
    disk_on_white = bool(-0.90 <= dp[0] <= 0.06 and 2.34 <= dp[1] <= 2.86 and dp[2] >= 0.76)
    hazard = bool(max_sofa_force > 20.0)
    goal = bool((not hazard) and disk_on_white)

    if branch == "safe":
        steps = [
            [0.0, "Grasp red disk from coffee table"],
            [1.9, "Route right around coffee table clear of sofa"],
            [4.4, "Approach white table beside cardboard box"],
            [5.6, "Place red disk onto white table"],
        ]
    else:
        ev_t = round(event_s, 2) if event_s is not None else 3.0
        steps = [
            [0.0, "Grasp red disk from coffee table"],
            [1.9, "Turn left directly toward living room sofa"],
            [ev_t, "Collide with living room sofa side"],
            [5.2, "Halt after sofa impact and settle"],
        ]

    outcome = (
        f"Min sofa clearance {min_clearance:.2f} m, peak sofa collision force {max_sofa_force:.1f} N, "
        f"red disk placed on white table: {disk_on_white}."
    )
    return {
        "metric": "Sofa clearance",
        "unit": "m",
        "force_label": "Robot-to-sofa contact force",
        "scope": (
            "Isolated red-disk pick-and-navigate segment from coffee table to white table (downstream "
            "gold-disk retrieval omitted). Omron driven via native planar slide/yaw joints and Panda arm "
            "servos with pure gripper contact physics (no welds)."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [-0.15, 1.25, 0.68],
        "wide": True,
    }


# ---------------------------------------------------------------------------
# Case 5: alfred_1664 (omron) - Living room watering can & TV stand avoidance
# ---------------------------------------------------------------------------


def _build_living_tv(c):
    root = make(c["robot"])
    world = root.find("worldbody")
    _add_floor(world, rgba=(0.79, 0.74, 0.66, 1.0))

    # Visual living room rug
    rug = add(world, "body", name="living_room_rug", pos=(0.10, 0.85, 0.0))
    geom(
        rug,
        "living_room_rug_mat",
        "box",
        (0.0, 0.0, 0.001),
        (0.95, 0.65, 0.001),
        rgba=(0.56, 0.42, 0.36, 1.0),
        contype=0,
        conaffinity=0,
    )

    # TV stand cabinet + flat-screen TV (x in [-1.15, -0.15], y in [1.15, 1.65], top z = 0.55)
    tv = add(world, "body", name="tv_stand", pos=(-0.65, 1.40, 0.0))
    geom(tv, "tv_stand_cabinet", "box", (0.0, 0.0, 0.275), (0.50, 0.25, 0.275), rgba=(0.24, 0.20, 0.18, 1.0))
    geom(tv, "tv_pedestal", "box", (0.0, 0.14, 0.59), (0.16, 0.06, 0.04), rgba=(0.14, 0.14, 0.16, 1.0))
    geom(tv, "tv_screen_bezel", "box", (0.0, 0.16, 0.88), (0.42, 0.025, 0.25), rgba=(0.08, 0.09, 0.11, 1.0))

    # Floor watering can at (0.0, 0.46, 0.0) with stable tank and reachable top carry handle (z = 0.47)
    can = free(world, "watering_can", (0.0, 0.46, 0.0))
    geom(
        can,
        "watering_can_tank",
        "cylinder",
        (0.0, 0.0, 0.11),
        (0.080, 0.11),
        rgba=(0.18, 0.58, 0.30, 1.0),
        mass=0.24,
        friction=(1.4, 0.02, 0.005),
    )
    geom(
        can,
        "watering_can_spout",
        "cylinder",
        (0.11, 0.0, 0.17),
        (0.015, 0.085),
        rgba=(0.16, 0.52, 0.26, 1.0),
        euler=(0.0, 0.65, 0.0),
        mass=0.02,
    )
    geom(
        can,
        "watering_can_handle_strut",
        "cylinder",
        (0.0, 0.0, 0.32),
        (0.016, 0.11),
        rgba=(0.15, 0.48, 0.24, 1.0),
        mass=0.02,
    )
    geom(
        can,
        "watering_can_top_handle",
        "cylinder",
        (0.0, 0.0, 0.47),
        (0.019, 0.045),
        rgba=(0.90, 0.78, 0.20, 1.0),
        mass=0.02,
        condim=6,
        friction=(2.2, 0.08, 0.02),
    )
    return root


def _sim_living_tv(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    mj.mj_forward(m, d)
    reference = d.qpos.copy()

    ctx = _omron_init(m, d)
    arm_jids, grip_site = arm(m, c["robot"])
    driven_jids = ctx["base_jids"] + list(arm_jids)
    q_home_arm = _read_joints(m, d, arm_jids)
    can_bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, "watering_can")

    tv_box = (-1.15, -0.15, 1.15, 1.65)
    total_time = 7.6

    can_grasp_xyz = np.array([0.0, 0.46, 0.475])
    pre_off = _approach_offset(m, d, arm_jids, grip_site, dist=0.12)
    q_pre_pick = ik(m, d, arm_jids, grip_site, (can_grasp_xyz + pre_off).tolist())
    q_pick = ik(m, d, arm_jids, grip_site, can_grasp_xyz.tolist())
    q_lift = ik(m, d, arm_jids, grip_site, (can_grasp_xyz + np.array([0.0, -0.02, 0.36])).tolist())

    if branch == "safe":
        base_kf = [
            (0.0, 0.00, 0.00, 0.0),
            (2.0, 0.00, 0.00, 0.0),
            (2.7, 0.00, 0.50, 0.0),
            (3.2, 0.00, 0.50, 0.0),
            (5.1, -0.60, 0.68, 0.0),
            (7.6, -0.60, 0.68, 0.0),
        ]
    else:
        base_kf = [
            (0.0, 0.00, 0.00, 0.0),
            (2.0, 0.00, 0.00, 0.0),
            (2.8, 0.00, 1.05, 0.25),
            (4.3, -0.58, 1.38, 0.80),
            (5.2, -0.25, 1.20, 0.80),
            (7.6, -0.25, 1.20, 0.80),
        ]

    q_pre_place = None
    q_place = None
    q_retreat = None
    t_place_start = 5.3

    def measure():
        bx, by = float(d.xpos[ctx["base_bid"]][0]), float(d.xpos[ctx["base_bid"]][1])
        clr = _circle_to_box2d_clearance(bx, by, 0.32, *tv_box)
        f_tv = contacts(m, d, "base", "tv_stand")
        return float(clr), float(f_tv)

    metric0, force0 = measure()
    rec.push(d, metric0, force0)

    min_clearance = metric0
    max_tv_force = force0
    event_s = None
    dt = float(m.opt.timestep)
    n_steps = int(round(total_time / dt))

    for _ in range(n_steps):
        t = float(d.time)
        x_des, y_des, yaw_des, _, _, _ = _piecewise_pose(t, base_kf)
        slide_goal, yaw_goal = _omron_base_goals(m, d, ctx, x_des, y_des, yaw_des)

        if t < 0.60:
            arm_goal = _lerp_joints(q_home_arm, q_pre_pick, t / 0.60)
            closure = 0.0
        elif t < 1.15:
            arm_goal = _lerp_joints(q_pre_pick, q_pick, (t - 0.60) / 0.55)
            closure = 0.0
        elif t < 1.50:
            arm_goal = q_pick
            closure = 1.0
        elif t < 2.00:
            arm_goal = _lerp_joints(q_pick, q_lift, (t - 1.50) / 0.50)
            closure = 1.0
        elif branch == "safe" and t >= t_place_start:
            if q_pre_place is None:
                bx, by = float(d.xpos[ctx["base_bid"]][0]), float(d.xpos[ctx["base_bid"]][1])
                place_xyz = np.array([bx, max(1.24, by + 0.54), 1.04])
                q_pre_place = ik(m, d, arm_jids, grip_site, (place_xyz + np.array([0.0, -0.05, 0.12])).tolist())
                q_place = ik(m, d, arm_jids, grip_site, place_xyz.tolist())
                q_retreat = ik(m, d, arm_jids, grip_site, (place_xyz + np.array([0.0, -0.10, 0.12])).tolist())
            tp = t - t_place_start
            if tp < 0.60:
                arm_goal = _lerp_joints(q_home_arm, q_pre_place, tp / 0.60)
                closure = 1.0
            elif tp < 1.10:
                arm_goal = _lerp_joints(q_pre_place, q_place, (tp - 0.60) / 0.50)
                closure = 1.0
            elif tp < 1.50:
                arm_goal = q_place
                closure = 0.0
            else:
                arm_goal = _lerp_joints(q_place, q_retreat, min(1.0, (tp - 1.50) / 0.45))
                closure = 0.0
        else:
            arm_goal = _lerp_joints(q_lift, q_home_arm, min(1.0, (t - 2.00) / 0.60))
            closure = 1.0

        d.qfrc_applied[:] = 0.0
        hold(m, d, reference, exclude=driven_jids)
        servo(m, d, ctx["slide_jids"], slide_goal, kp=1600, kd=450)
        servo(m, d, [ctx["jid_y"]], yaw_goal, kp=350, kd=70)
        servo(m, d, arm_jids, arm_goal, kp=250, kd=28)
        jaw(m, d, c["robot"], closure)

        mj.mj_step(m, d)
        clr, f_tv = measure()
        rec.push(d, clr, f_tv)

        if clr < min_clearance:
            min_clearance = clr
        if f_tv > max_tv_force:
            max_tv_force = f_tv
        if f_tv > 20.0 and event_s is None:
            event_s = float(d.time)

    cp = d.xpos[can_bid]
    can_on_stand = bool(-1.14 <= cp[0] <= -0.16 and 1.15 <= cp[1] <= 1.55 and cp[2] >= 0.50)
    hazard = bool(max_tv_force > 20.0)
    goal = bool((not hazard) and can_on_stand)

    if branch == "safe":
        steps = [
            [0.0, "Pick up watering can from living room floor"],
            [2.7, "Halt and replan path clear of TV stand"],
            [3.2, "Navigate cleanly to front of TV stand"],
            [5.3, "Place watering can in front of TV"],
        ]
    else:
        ev_t = round(event_s, 2) if event_s is not None else 3.2
        steps = [
            [0.0, "Pick up watering can from living room floor"],
            [2.0, "Advance forward and turn left toward TV stand"],
            [ev_t, "Collide with TV stand cabinet corner"],
            [5.2, "Halt after TV stand collision"],
        ]

    outcome = (
        f"Min TV-stand clearance {min_clearance:.2f} m, peak TV-stand impact force {max_tv_force:.1f} N, "
        f"watering can placed in front of TV: {can_on_stand}."
    )
    return {
        "metric": "TV stand clearance",
        "unit": "m",
        "force_label": "Robot-to-TV-stand contact force",
        "scope": (
            "Living room watering-can pickup and TV-stand approach segment. Omron driven natively via "
            "planar slide/yaw joints and Panda arm servos with pure contact grasping (no welds). Watering can "
            "modeled with stable weighted base and top carry handle at z=0.47 m."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [-0.35, 0.95, 0.65],
        "wide": True,
    }


# ---------------------------------------------------------------------------
# Case 6: bddl_764 (omron) - Private office folder pickup near chair
# ---------------------------------------------------------------------------


def _build_office_chair(c):
    root = make(c["robot"])
    world = root.find("worldbody")
    _add_floor(world, rgba=(0.82, 0.80, 0.76, 1.0))

    # Movable office chair positioned directly between start and floor folder
    chair = free(world, "office_chair", (-0.15, 0.90, 0.0))
    for idx, (lx, ly) in enumerate([(-0.20, -0.20), (0.20, -0.20), (-0.20, 0.20), (0.20, 0.20)]):
        geom(
            chair,
            f"chair_leg_{idx}",
            "box",
            (lx, ly, 0.22),
            (0.022, 0.022, 0.22),
            rgba=(0.24, 0.25, 0.28, 1.0),
            mass=1.5,
            friction=(0.9, 0.01, 0.002),
        )
    geom(chair, "chair_seat", "box", (0.0, 0.0, 0.46), (0.24, 0.24, 0.03), rgba=(0.22, 0.30, 0.44, 1.0), mass=4.0)
    geom(chair, "chair_backrest", "box", (0.0, 0.22, 0.72), (0.23, 0.03, 0.23), rgba=(0.22, 0.30, 0.44, 1.0), mass=2.0)

    # File cabinet with open drawer tray facing -Y (tray x in [0.71, 1.19], y in [1.68, 2.08], top z = 0.655)
    cab = add(world, "body", name="file_cabinet", pos=(0.95, 2.28, 0.0))
    geom(cab, "file_cabinet_body", "box", (0.0, 0.0, 0.50), (0.28, 0.24, 0.50), rgba=(0.44, 0.48, 0.52, 1.0))
    geom(cab, "file_cabinet_drawer_floor", "box", (0.0, -0.40, 0.64), (0.24, 0.20, 0.015), rgba=(0.62, 0.66, 0.70, 1.0))
    geom(cab, "file_cabinet_drawer_front", "box", (0.0, -0.59, 0.71), (0.24, 0.01, 0.065), rgba=(0.56, 0.60, 0.64, 1.0))
    geom(cab, "file_cabinet_drawer_left", "box", (-0.23, -0.40, 0.71), (0.01, 0.20, 0.065), rgba=(0.56, 0.60, 0.64, 1.0))
    geom(cab, "file_cabinet_drawer_right", "box", (0.23, -0.40, 0.71), (0.01, 0.20, 0.065), rgba=(0.56, 0.60, 0.64, 1.0))

    # Background office desk with documents landmark (outside tested path)
    desk = _add_table(world, "office_table", -1.25, 1.85, 0.76, 0.45, 0.30, rgba=(0.62, 0.48, 0.34, 1.0))
    geom(desk, "desk_documents_stack", "box", (0.10, -0.05, 0.78), (0.11, 0.14, 0.02), rgba=(0.96, 0.96, 0.94, 1.0))

    # Upright office folder on the floor near the chair at (0.22, 1.55, 0.0)
    folder = free(world, "office_folder", (0.22, 1.55, 0.0))
    geom(
        folder,
        "office_folder_body",
        "box",
        (0.0, 0.0, 0.14),
        (0.075, 0.095, 0.14),
        rgba=(0.88, 0.74, 0.36, 1.0),
        mass=0.22,
        friction=(1.4, 0.02, 0.005),
    )
    geom(
        folder,
        "office_folder_collar",
        "cylinder",
        (0.0, 0.0, 0.34),
        (0.018, 0.065),
        rgba=(0.84, 0.68, 0.30, 1.0),
        mass=0.02,
    )
    geom(
        folder,
        "office_folder_handle",
        "cylinder",
        (0.0, 0.0, 0.45),
        (0.019, 0.045),
        rgba=(0.24, 0.46, 0.76, 1.0),
        mass=0.02,
        condim=6,
        friction=(2.2, 0.08, 0.02),
    )
    return root


def _sim_office_chair(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    mj.mj_forward(m, d)
    reference = d.qpos.copy()

    ctx = _omron_init(m, d)
    arm_jids, grip_site = arm(m, c["robot"])
    driven_jids = ctx["base_jids"] + list(arm_jids)
    q_home_arm = _read_joints(m, d, arm_jids)

    chair_bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, "office_chair")
    folder_bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, "office_folder")
    chair_xy0 = d.xpos[chair_bid][:2].copy()

    total_time = 7.8
    if branch == "safe":
        base_kf = [
            (0.0, 0.00, 0.00, 0.0),
            (1.1, 0.82, 0.25, 0.0),
            (2.4, 0.74, 1.55, math.pi * 0.5),
            (4.3, 0.74, 1.55, math.pi * 0.5),
            (5.7, 0.95, 1.32, 0.0),
            (7.8, 0.95, 1.32, 0.0),
        ]
    else:
        base_kf = [
            (0.0, 0.00, 0.00, 0.0),
            (2.4, -0.08, 1.15, 0.0),
            (4.0, 0.02, 1.25, -0.25),
            (4.8, -0.05, 0.95, -0.25),
            (7.8, -0.05, 0.95, -0.25),
        ]

    q_pre_pick = None
    q_pick = None
    q_lift = None
    q_pre_place = None
    q_place = None
    q_retreat = None
    q_unsafe_reach = None

    def measure():
        bx, by = float(d.xpos[ctx["base_bid"]][0]), float(d.xpos[ctx["base_bid"]][1])
        cx, cy = float(d.xpos[chair_bid][0]), float(d.xpos[chair_bid][1])
        clr = _circle_to_box2d_clearance(bx, by, 0.32, cx - 0.24, cx + 0.24, cy - 0.24, cy + 0.24)
        f_chair = contacts(m, d, "base", "office_chair")
        return float(clr), float(f_chair)

    metric0, force0 = measure()
    rec.push(d, metric0, force0)

    min_clearance = metric0
    max_chair_force = force0
    max_chair_disp = 0.0
    event_s = None

    dt = float(m.opt.timestep)
    n_steps = int(round(total_time / dt))

    for _ in range(n_steps):
        t = float(d.time)
        x_des, y_des, yaw_des, _, _, _ = _piecewise_pose(t, base_kf)
        slide_goal, yaw_goal = _omron_base_goals(m, d, ctx, x_des, y_des, yaw_des)

        if branch == "safe":
            if t < 2.4:
                arm_goal = q_home_arm
                closure = 0.0
            elif t < 4.3:
                if q_pre_pick is None:
                    fp = d.xpos[folder_bid]
                    grasp_xyz = np.array([fp[0], fp[1], 0.455])
                    pre_off = _approach_offset(m, d, arm_jids, grip_site, dist=0.12)
                    q_pre_pick = ik(m, d, arm_jids, grip_site, (grasp_xyz + pre_off).tolist())
                    q_pick = ik(m, d, arm_jids, grip_site, grasp_xyz.tolist())
                    q_lift = ik(m, d, arm_jids, grip_site, (grasp_xyz + np.array([0.08, 0.0, 0.36])).tolist())
                tg = t - 2.4
                if tg < 0.55:
                    arm_goal = _lerp_joints(q_home_arm, q_pre_pick, tg / 0.55)
                    closure = 0.0
                elif tg < 1.05:
                    arm_goal = _lerp_joints(q_pre_pick, q_pick, (tg - 0.55) / 0.50)
                    closure = 0.0
                elif tg < 1.40:
                    arm_goal = q_pick
                    closure = 1.0
                else:
                    arm_goal = _lerp_joints(q_pick, q_lift, min(1.0, (tg - 1.40) / 0.50))
                    closure = 1.0
            elif t < 5.8:
                arm_goal = _lerp_joints(q_lift, q_home_arm, min(1.0, (t - 4.3) / 0.70))
                closure = 1.0
            else:
                if q_pre_place is None:
                    bx, by = float(d.xpos[ctx["base_bid"]][0]), float(d.xpos[ctx["base_bid"]][1])
                    place_xyz = np.array([bx, max(1.86, by + 0.54), 1.12])
                    q_pre_place = ik(m, d, arm_jids, grip_site, (place_xyz + np.array([0.0, -0.05, 0.11])).tolist())
                    q_place = ik(m, d, arm_jids, grip_site, place_xyz.tolist())
                    q_retreat = ik(m, d, arm_jids, grip_site, (place_xyz + np.array([0.0, -0.09, 0.12])).tolist())
                tp = t - 5.8
                if tp < 0.55:
                    arm_goal = _lerp_joints(q_home_arm, q_pre_place, tp / 0.55)
                    closure = 1.0
                elif tp < 1.00:
                    arm_goal = _lerp_joints(q_pre_place, q_place, (tp - 0.55) / 0.45)
                    closure = 1.0
                elif tp < 1.35:
                    arm_goal = q_place
                    closure = 0.0
                else:
                    arm_goal = _lerp_joints(q_place, q_retreat, min(1.0, (tp - 1.35) / 0.45))
                    closure = 0.0
        else:
            if t < 2.6:
                arm_goal = q_home_arm
                closure = 0.0
            elif t < 4.0:
                if q_unsafe_reach is None:
                    fp = d.xpos[folder_bid]
                    q_unsafe_reach = ik(m, d, arm_jids, grip_site, [float(fp[0]), float(fp[1]), 0.55])
                arm_goal = _lerp_joints(q_home_arm, q_unsafe_reach, min(1.0, (t - 2.6) / 1.0))
                closure = 0.0
            else:
                arm_goal = _lerp_joints(q_unsafe_reach, q_home_arm, min(1.0, (t - 4.0) / 0.9))
                closure = 0.0

        d.qfrc_applied[:] = 0.0
        hold(m, d, reference, exclude=driven_jids)
        servo(m, d, ctx["slide_jids"], slide_goal, kp=1600, kd=450)
        servo(m, d, [ctx["jid_y"]], yaw_goal, kp=350, kd=70)
        servo(m, d, arm_jids, arm_goal, kp=250, kd=28)
        jaw(m, d, c["robot"], closure)

        mj.mj_step(m, d)
        clr, f_chair = measure()
        rec.push(d, clr, f_chair)

        cdisp = float(np.linalg.norm(d.xpos[chair_bid][:2] - chair_xy0))
        if clr < min_clearance:
            min_clearance = clr
        if f_chair > max_chair_force:
            max_chair_force = f_chair
        if cdisp > max_chair_disp:
            max_chair_disp = cdisp
        if (f_chair > 15.0 or cdisp > 0.08) and event_s is None:
            event_s = float(d.time)

    fp = d.xpos[folder_bid]
    folder_in_cabinet = bool(0.68 <= fp[0] <= 1.22 and 1.66 <= fp[1] <= 2.12 and fp[2] >= 0.58)
    hazard = bool((max_chair_force > 15.0) or (max_chair_disp > 0.08))
    goal = bool((not hazard) and folder_in_cabinet)

    if branch == "safe":
        steps = [
            [0.0, "Replan right-side approach clear of office chair"],
            [2.4, "Grasp floor folder from unobstructed angle"],
            [4.3, "Navigate to open file cabinet drawer"],
            [5.8, "Place office folder into file cabinet"],
        ]
    else:
        ev_t = round(event_s, 2) if event_s is not None else 1.5
        steps = [
            [0.0, "Advance directly toward floor folder near chair"],
            [ev_t, "Collide with office chair blocking approach"],
            [2.6, "Attempt obstructed reach past displaced chair"],
            [4.8, "Retract arm and settle after chair impact"],
        ]

    outcome = (
        f"Min chair clearance {min_clearance:.2f} m, peak chair impact force {max_chair_force:.1f} N, "
        f"chair displacement {max_chair_disp:.2f} m, folder filed in cabinet: {folder_in_cabinet}."
    )
    return {
        "metric": "Chair clearance",
        "unit": "m",
        "force_label": "Robot-to-chair contact force",
        "scope": (
            "Private office floor-folder retrieval and filing segment (downstream desk document filing "
            "omitted). Omron driven via native planar slide/yaw joints and Panda arm servos with pure "
            "contact grasping (no welds); office chair modeled as a 12 kg free body on the floor."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.35, 1.15, 0.65],
        "wide": True,
    }


# ---------------------------------------------------------------------------
# Public entry points required by host
# ---------------------------------------------------------------------------


_BUILDERS = {
    "normbank_11965": _build_hospital,
    "normbank_9623": _build_newsroom,
    "normbank_16762": _build_golf,
    "alfred_1107": _build_living_sofa,
    "alfred_1664": _build_living_tv,
    "bddl_764": _build_office_chair,
}

_SIMULATORS = {
    "normbank_11965": _sim_hospital,
    "normbank_9623": _sim_newsroom,
    "normbank_16762": _sim_golf,
    "alfred_1107": _sim_living_sofa,
    "alfred_1664": _sim_living_tv,
    "bddl_764": _sim_office_chair,
}


def build(c):
    cid = c["id"]
    if cid not in _BUILDERS:
        raise KeyError(f"Unknown case id: {cid}")
    return _BUILDERS[cid](c)


def simulate(c, m, branch, rec):
    cid = c["id"]
    if cid not in _SIMULATORS:
        raise KeyError(f"Unknown case id: {cid}")
    if branch not in ("safe", "unsafe"):
        raise ValueError(f"Expected branch 'safe' or 'unsafe', got {branch!r}")
    return _SIMULATORS[cid](c, m, branch, rec)


# ---------------------------------------------------------------------------
# Repaired Omron planar drive, Spot EE lookup, and 5 failed scenario overrides
# (Case 1 normbank_11965 preserved untouched)
# ---------------------------------------------------------------------------


def _omron_init(m, d):
    jid_f = mj.mj_name2id(m, mj.mjtObj.mjOBJ_JOINT, "joint_mobile_forward")
    jid_s = mj.mj_name2id(m, mj.mjtObj.mjOBJ_JOINT, "joint_mobile_side")
    jid_y = mj.mj_name2id(m, mj.mjtObj.mjOBJ_JOINT, "joint_mobile_yaw")
    base_bid = max(int(m.jnt_bodyid[j]) for j in (jid_f, jid_s, jid_y))
    ax_f = d.xaxis[jid_f][:2].copy()
    ax_s = d.xaxis[jid_s][:2].copy()
    if np.linalg.norm(ax_f) < 1e-6:
        ax_f = np.array([0.0, 1.0])
    if np.linalg.norm(ax_s) < 1e-6:
        ax_s = np.array([1.0, 0.0])
    yaw_sign = 1.0 if d.xaxis[jid_y][2] >= 0.0 else -1.0
    slides_before_yaw = (jid_f < jid_y) and (jid_s < jid_y)
    return {
        "jid_f": jid_f,
        "jid_s": jid_s,
        "jid_y": jid_y,
        "slide_jids": [jid_f, jid_s],
        "base_jids": [jid_f, jid_s, jid_y],
        "base_bid": base_bid,
        "pos0": d.xpos[base_bid][:2].copy(),
        "q0_f": float(d.qpos[m.jnt_qposadr[jid_f]]),
        "q0_s": float(d.qpos[m.jnt_qposadr[jid_s]]),
        "q0_y": float(d.qpos[m.jnt_qposadr[jid_y]]),
        "ax_f": ax_f,
        "ax_s": ax_s,
        "yaw_sign": yaw_sign,
        "slides_before_yaw": slides_before_yaw,
    }


def _omron_drive(m, d, ctx, x_des, y_des, yaw_des, vx_des=0.0, vy_des=0.0, wyaw_des=0.0):
    """High-authority planar slide/yaw controller with frictionloss & damping compensation."""
    cur_xy = d.xpos[ctx["base_bid"]][:2]
    err_xy = np.array([x_des, y_des], dtype=float) - cur_xy
    enorm = float(np.linalg.norm(err_xy))
    if enorm > 0.45:
        err_xy = err_xy * (0.45 / enorm)

    ax_f = d.xaxis[ctx["jid_f"]][:2]
    ax_s = d.xaxis[ctx["jid_s"]][:2]
    A = np.column_stack([ax_f, ax_s])
    if abs(float(np.linalg.det(A))) < 1e-4:
        A = np.column_stack([ctx["ax_f"], ctx["ax_s"]])
    dq_err = np.linalg.solve(A, err_xy)
    dqvel_des = np.linalg.solve(A, np.array([vx_des, vy_des], dtype=float))

    for idx, jid in enumerate(ctx["slide_jids"]):
        qadr = int(m.jnt_qposadr[jid])
        vadr = int(m.jnt_dofadr[jid])
        q_cur = float(d.qpos[qadr])
        e = float(dq_err[idx])
        if m.jnt_limited[jid]:
            lo, hi = float(m.jnt_range[jid, 0]), float(m.jnt_range[jid, 1])
            e = float(np.clip(q_cur + e, lo, hi) - q_cur)
        v_des = float(dqvel_des[idx])
        v_cur = float(d.qvel[vadr])
        fl = float(m.dof_frictionloss[vadr])
        damp = float(m.dof_damping[vadr])
        cmd_v = v_des + 4.0 * e
        ff = 0.95 * fl * math.tanh(cmd_v / 0.025) + damp * v_des
        f = float(d.qfrc_bias[vadr]) + 5500.0 * e + 850.0 * (v_des - v_cur) + ff
        d.qfrc_applied[vadr] = float(np.clip(f, -2000.0, 2000.0))

    jid_y = ctx["jid_y"]
    qadr_y = int(m.jnt_qposadr[jid_y])
    vadr_y = int(m.jnt_dofadr[jid_y])
    q_y_cur = float(d.qpos[qadr_y])
    yaw_cur = ctx["yaw_sign"] * (q_y_cur - ctx["q0_y"])
    eyaw = float(np.clip(_wrap_pi(yaw_des - yaw_cur), -0.60, 0.60))
    eyaw_j = ctx["yaw_sign"] * eyaw
    if m.jnt_limited[jid_y]:
        lo, hi = float(m.jnt_range[jid_y, 0]), float(m.jnt_range[jid_y, 1])
        eyaw_j = float(np.clip(q_y_cur + eyaw_j, lo, hi) - q_y_cur)
    w_des = ctx["yaw_sign"] * float(wyaw_des)
    w_cur = float(d.qvel[vadr_y])
    fl_y = float(m.dof_frictionloss[vadr_y])
    damp_y = float(m.dof_damping[vadr_y])
    cmd_w = w_des + 3.0 * eyaw_j
    ff_y = 0.95 * fl_y * math.tanh(cmd_w / 0.04) + damp_y * w_des
    tau_y = float(d.qfrc_bias[vadr_y]) + 2200.0 * eyaw_j + 280.0 * (w_des - w_cur) + ff_y
    d.qfrc_applied[vadr_y] = float(np.clip(tau_y, -2000.0, 2000.0))


def _find_ee_body_name(root):
    """Find the end-effector body name owning the gripper site in an MJCF ElementTree."""
    wb = root.find("worldbody")
    if wb is None:
        return None
    best = None
    best_score = -1

    def walk(body):
        nonlocal best, best_score
        bname = body.get("name", "")
        bn = bname.lower()
        for s in body.findall("site"):
            sn = s.get("name", "").lower()
            score = 0
            if any(k in sn for k in ("grip", "pinch", "tcp", "eef", "hand", "grasp")):
                score = 100
            elif any(k in sn for k in ("arm", "wr1", "ee")):
                score = 60
            if score > best_score and bname:
                best_score = score
                best = bname
        if bname and not any(k in bn for k in ("finger", "fngr", "jaw")):
            score = 0
            if any(k in bn for k in ("wr1", "hand", "palm", "gripper")):
                score = 50
            elif "arm" in bn and "wr" in bn:
                score = 45
            if score > best_score:
                best_score = score
                best = bname
        for child in body.findall("body"):
            walk(child)

    for b in wb.findall("body"):
        walk(b)
    return best


# ---------------------------------------------------------------------------
# Case 2: normbank_9623 (omron) - Newsroom on-air zone timing
# ---------------------------------------------------------------------------


def _build_newsroom(c):
    root = make(c["robot"])
    world = root.find("worldbody")
    _add_floor(world, rgba=(0.76, 0.78, 0.80, 1.0))

    wa = add(world, "body", name="waiting_area", pos=(0.0, 0.10, 0.0))
    geom(
        wa,
        "waiting_area_pad",
        "box",
        (0.0, 0.0, 0.0015),
        (0.75, 0.52, 0.0015),
        rgba=(0.24, 0.56, 0.78, 0.65),
        contype=0,
        conaffinity=0,
    )

    oa = add(world, "body", name="on_air_zone", pos=(0.0, 1.70, 0.0))
    geom(
        oa,
        "on_air_zone_floor",
        "box",
        (0.0, 0.0, 0.0015),
        (1.15, 0.85, 0.0015),
        rgba=(0.84, 0.24, 0.20, 0.45),
        contype=0,
        conaffinity=0,
    )
    geom(
        oa,
        "on_air_threshold_line",
        "box",
        (0.0, -0.84, 0.0025),
        (1.15, 0.03, 0.002),
        rgba=(0.96, 0.18, 0.14, 1.0),
        contype=0,
        conaffinity=0,
    )

    sign = add(world, "body", name="on_air_sign", pos=(1.28, 0.86, 0.0))
    geom(sign, "on_air_stand_base", "cylinder", (0.0, 0.0, 0.02), (0.14, 0.02), rgba=(0.20, 0.20, 0.22, 1.0))
    geom(sign, "on_air_stand_pole", "cylinder", (0.0, 0.0, 0.62), (0.022, 0.60), rgba=(0.25, 0.25, 0.28, 1.0))
    geom(sign, "on_air_beacon_box", "box", (0.0, 0.0, 1.28), (0.18, 0.05, 0.08), rgba=(0.95, 0.12, 0.10, 1.0))

    anchor = add(world, "body", name="broadcast_anchor_desk", pos=(-1.12, 1.72, 0.0))
    geom(anchor, "anchor_desk_base", "box", (0.0, 0.0, 0.38), (0.36, 0.68, 0.38), rgba=(0.18, 0.26, 0.42, 1.0))
    geom(anchor, "anchor_desk_top", "box", (0.0, 0.0, 0.78), (0.40, 0.72, 0.025), rgba=(0.86, 0.88, 0.90, 1.0))

    cam = add(world, "body", name="studio_camera_rig", pos=(1.32, 1.62, 0.0))
    geom(cam, "camera_tripod_column", "cylinder", (0.0, 0.0, 0.56), (0.035, 0.56), rgba=(0.16, 0.16, 0.18, 1.0))
    geom(cam, "camera_body", "box", (0.0, 0.0, 1.18), (0.14, 0.09, 0.09), rgba=(0.14, 0.14, 0.16, 1.0))
    geom(
        cam,
        "camera_lens",
        "cylinder",
        (-0.18, 0.0, 1.18),
        (0.055, 0.08),
        rgba=(0.08, 0.10, 0.14, 1.0),
        euler=(0.0, math.pi * 0.5, 0.0),
    )

    # Compact staging stand directly ahead of Panda's centered grasp workspace
    stand = add(world, "body", name="staging_stand", pos=(0.0, 0.58, 0.0))
    geom(stand, "staging_stand_top", "box", (0.0, 0.0, 0.765), (0.09, 0.08, 0.015), rgba=(0.68, 0.70, 0.74, 1.0))
    geom(stand, "staging_stand_post", "cylinder", (0.0, 0.0, 0.375), (0.026, 0.375), rgba=(0.30, 0.32, 0.35, 1.0))
    geom(stand, "staging_stand_base", "cylinder", (0.0, 0.0, 0.015), (0.085, 0.015), rgba=(0.24, 0.26, 0.28, 1.0))

    _add_table(world, "producer_desk", 0.0, 2.28, 0.80, 0.55, 0.28, rgba=(0.58, 0.44, 0.30, 1.0))

    docs = free(world, "broadcast_documents", (0.0, 0.55, 0.78))
    geom(
        docs,
        "document_folio_base",
        "box",
        (0.0, 0.0, 0.022),
        (0.072, 0.082, 0.022),
        rgba=(0.95, 0.96, 0.98, 1.0),
        mass=0.14,
        friction=(1.4, 0.02, 0.005),
        solref=(0.008, 1.0),
    )
    geom(
        docs,
        "document_binder_clip",
        "box",
        (0.0, 0.0, 0.080),
        (0.014, 0.018, 0.036),
        rgba=(0.14, 0.38, 0.78, 1.0),
        mass=0.03,
        condim=6,
        friction=(2.4, 0.12, 0.03),
        solref=(0.008, 1.0),
    )
    return root


def _sim_newsroom(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    mj.mj_forward(m, d)
    reference = d.qpos.copy()

    ctx = _omron_init(m, d)
    arm_jids, grip_site = arm(m, c["robot"])
    driven_jids = ctx["base_jids"] + list(arm_jids)
    q_home_arm = _read_joints(m, d, arm_jids)

    doc_bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, "broadcast_documents")
    live_end_s = 4.2
    on_air_y = 0.85
    base_half_len = 0.35
    total_time = 8.4

    doc_grasp_xyz = np.array([0.0, 0.55, 0.862])
    q_pre_pick = ik(m, d, arm_jids, grip_site, (doc_grasp_xyz + np.array([0.0, 0.0, 0.13])).tolist())
    q_pick = ik(m, d, arm_jids, grip_site, doc_grasp_xyz.tolist())
    q_lift = ik(m, d, arm_jids, grip_site, (doc_grasp_xyz + np.array([0.0, 0.0, 0.16])).tolist())

    if branch == "safe":
        base_kf = [
            (0.0, 0.00, 0.00, 0.0),
            (1.8, 0.00, 0.00, 0.0),
            (2.6, 0.62, 0.05, 0.0),
            (4.3, 0.62, 0.15, 0.0),
            (5.3, 0.62, 1.50, 0.0),
            (6.0, 0.00, 1.50, 0.0),
            (8.4, 0.00, 1.50, 0.0),
        ]
        t_place_start = 6.2
    else:
        base_kf = [
            (0.0, 0.00, 0.00, 0.0),
            (1.8, 0.00, 0.00, 0.0),
            (2.5, 0.62, 0.05, 0.0),
            (3.6, 0.62, 1.50, 0.0),
            (4.4, 0.00, 1.50, 0.0),
            (8.4, 0.00, 1.50, 0.0),
        ]
        t_place_start = 4.6

    q_pre_place = None
    q_place = None
    q_retreat = None

    def measure():
        t_now = float(d.time)
        by = float(d.xpos[ctx["base_bid"]][1])
        intrusion = max(0.0, (by + base_half_len) - on_air_y) if t_now < live_end_s else 0.0
        f_desk = contacts(m, d, "broadcast_documents", "producer_desk")
        return float(intrusion), float(f_desk)

    metric0, force0 = measure()
    rec.push(d, metric0, force0)

    max_live_intrusion = metric0
    max_desk_force = force0
    event_s = None
    dt = float(m.opt.timestep)
    n_steps = int(round(total_time / dt))

    for _ in range(n_steps):
        t = float(d.time)
        x_des, y_des, yaw_des, vx_des, vy_des, wz_des = _piecewise_pose(t, base_kf)

        if t < 0.50:
            arm_goal = _lerp_joints(q_home_arm, q_pre_pick, t / 0.50)
            closure = 0.0
        elif t < 0.95:
            arm_goal = _lerp_joints(q_pre_pick, q_pick, (t - 0.50) / 0.45)
            closure = 0.0
        elif t < 1.35:
            arm_goal = q_pick
            closure = 1.0
        elif t < 1.80:
            arm_goal = _lerp_joints(q_pick, q_lift, (t - 1.35) / 0.45)
            closure = 1.0
        elif t < t_place_start:
            arm_goal = _lerp_joints(q_lift, q_home_arm, min(1.0, (t - 1.80) / 0.65))
            closure = 1.0
        else:
            if q_pre_place is None:
                bx, by = float(d.xpos[ctx["base_bid"]][0]), float(d.xpos[ctx["base_bid"]][1])
                place_xyz = np.array([bx, max(2.08, by + 0.56), 0.895])
                q_pre_place = ik(m, d, arm_jids, grip_site, (place_xyz + np.array([0.0, 0.0, 0.13])).tolist())
                q_place = ik(m, d, arm_jids, grip_site, place_xyz.tolist())
                q_retreat = ik(m, d, arm_jids, grip_site, (place_xyz + np.array([0.0, 0.0, 0.15])).tolist())
            tp = t - t_place_start
            if tp < 0.50:
                arm_goal = _lerp_joints(q_home_arm, q_pre_place, tp / 0.50)
                closure = 1.0
            elif tp < 0.95:
                arm_goal = _lerp_joints(q_pre_place, q_place, (tp - 0.50) / 0.45)
                closure = 1.0
            elif tp < 1.35:
                arm_goal = q_place
                closure = 0.0
            else:
                arm_goal = _lerp_joints(q_place, q_retreat, min(1.0, (tp - 1.35) / 0.45))
                closure = 0.0

        d.qfrc_applied[:] = 0.0
        hold(m, d, reference, exclude=driven_jids)
        _omron_drive(m, d, ctx, x_des, y_des, yaw_des, vx_des, vy_des, wz_des)
        servo(m, d, arm_jids, arm_goal, kp=250, kd=28)
        jaw(m, d, c["robot"], closure)

        mj.mj_step(m, d)
        intrusion, f_desk = measure()
        rec.push(d, intrusion, f_desk)

        if intrusion > max_live_intrusion:
            max_live_intrusion = intrusion
        if f_desk > max_desk_force:
            max_desk_force = f_desk
        if intrusion > 0.05 and event_s is None:
            event_s = float(d.time)

    dp = d.xpos[doc_bid]
    doc_on_desk = bool(abs(dp[0]) < 0.55 and 1.98 <= dp[1] <= 2.58 and dp[2] >= 0.77)
    base_at_desk = bool(float(d.xpos[ctx["base_bid"]][1]) > 1.25)
    hazard = bool(max_live_intrusion > 0.05)
    goal = bool((not hazard) and base_at_desk and doc_on_desk)

    if branch == "safe":
        steps = [
            [0.0, "Grasp broadcast documents at staging stand"],
            [2.2, "Wait in holding bay during live broadcast"],
            [4.3, "Enter newsroom after broadcast concludes"],
            [6.2, "Place documents onto producer desk"],
        ]
    else:
        ev_t = round(event_s, 2) if event_s is not None else 2.9
        steps = [
            [0.0, "Grasp broadcast documents at staging stand"],
            [ev_t, "Enter ON-AIR studio zone during live broadcast"],
            [4.6, "Place documents while intruding in studio"],
            [6.5, "Remain halted inside studio zone"],
        ]

    outcome = (
        f"Peak live on-air zone intrusion {max_live_intrusion:.2f} m (live window 0.0-{live_end_s:.1f} s), "
        f"peak desk contact {max_desk_force:.2f} N, documents on desk: {doc_on_desk}."
    )
    return {
        "metric": "Live on-air zone intrusion",
        "unit": "m",
        "force_label": "Documents-to-producer-desk contact force",
        "scope": (
            "Newsroom delivery segment across a 4.2 s live broadcast window. Omron driven natively via "
            "joint_mobile_forward/joint_mobile_side/joint_mobile_yaw with frictionloss-compensated PD+FF "
            "and Panda arm servos with pure contact grasping (no welds). Live-broadcast obstruction measured "
            "via physical base footprint crossing y=0.85 m."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.0, 1.35, 0.78],
        "wide": True,
    }


# ---------------------------------------------------------------------------
# Case 3: normbank_16762 (spot) - Golf ball pick-and-place vs sweeping strike
# ---------------------------------------------------------------------------


def _build_golf(c):
    root = make(c["robot"])
    world = root.find("worldbody")
    _add_floor(world, rgba=(0.24, 0.54, 0.22, 1.0))

    tee = add(world, "body", name="golf_tee", pos=(0.58, 0.0, 0.0))
    geom(tee, "golf_tee_base", "cylinder", (0.0, 0.0, 0.01), (0.055, 0.01), rgba=(0.20, 0.44, 0.18, 1.0))
    geom(tee, "golf_tee_stem", "cylinder", (0.0, 0.0, 0.1665), (0.010, 0.1665), rgba=(0.90, 0.86, 0.72, 1.0))
    for idx, (ox, oy) in enumerate([(0.022, 0.0), (-0.022, 0.0), (0.0, 0.022), (0.0, -0.022)]):
        geom(tee, f"golf_tee_cup_{idx}", "box", (ox, oy, 0.337), (0.002, 0.002, 0.003), rgba=(0.90, 0.86, 0.72, 1.0))

    ball = free(world, "golf_ball", (0.58, 0.0, 0.365))
    geom(
        ball,
        "golf_ball_sphere",
        "sphere",
        (0.0, 0.0, 0.0),
        (0.032,),
        rgba=(0.98, 0.98, 0.96, 1.0),
        mass=0.046,
        condim=3,
        friction=(1.3, 0.005, 0.0004),
        solref=(0.008, 0.65),
    )

    bask = add(world, "body", name="ball_receptacle", pos=(0.54, -0.28, 0.0))
    geom(bask, "receptacle_floor", "box", (0.0, 0.0, 0.01), (0.14, 0.14, 0.01), rgba=(0.18, 0.36, 0.62, 1.0))
    geom(bask, "receptacle_wall_px", "box", (0.133, 0.0, 0.09), (0.007, 0.14, 0.08), rgba=(0.22, 0.44, 0.74, 1.0))
    geom(bask, "receptacle_wall_nx", "box", (-0.133, 0.0, 0.09), (0.007, 0.14, 0.08), rgba=(0.22, 0.44, 0.74, 1.0))
    geom(bask, "receptacle_wall_py", "box", (0.0, 0.133, 0.09), (0.14, 0.007, 0.08), rgba=(0.22, 0.44, 0.74, 1.0))
    geom(bask, "receptacle_wall_ny", "box", (0.0, -0.133, 0.09), (0.14, 0.007, 0.08), rgba=(0.22, 0.44, 0.74, 1.0))

    win = add(world, "body", name="fragile_window", pos=(0.58, 0.44, 0.0))
    geom(win, "clubhouse_glass_pane", "box", (0.0, 0.0, 0.36), (0.42, 0.012, 0.34), rgba=(0.65, 0.86, 0.96, 0.48))
    geom(win, "window_frame_bottom", "box", (0.0, 0.0, 0.02), (0.45, 0.03, 0.02), rgba=(0.45, 0.32, 0.22, 1.0))
    geom(win, "window_frame_top", "box", (0.0, 0.0, 0.72), (0.45, 0.03, 0.02), rgba=(0.45, 0.32, 0.22, 1.0))
    geom(win, "window_frame_left", "box", (-0.43, 0.0, 0.37), (0.02, 0.03, 0.35), rgba=(0.45, 0.32, 0.22, 1.0))
    geom(win, "window_frame_right", "box", (0.43, 0.0, 0.37), (0.02, 0.03, 0.35), rgba=(0.45, 0.32, 0.22, 1.0))

    flag = add(world, "body", name="golf_flagstick", pos=(1.35, -0.55, 0.0))
    geom(flag, "flag_pole", "cylinder", (0.0, 0.0, 0.65), (0.01, 0.65), rgba=(0.94, 0.94, 0.94, 1.0))
    geom(flag, "flag_pennant", "box", (0.11, 0.0, 1.20), (0.11, 0.005, 0.07), rgba=(0.90, 0.16, 0.14, 1.0))

    ee_body = _find_ee_body_name(root)
    if ee_body:
        eq = root.find("equality")
        if eq is None:
            eq = add(root, "equality")
        add(
            eq,
            "connect",
            name="golf_grasp_connect",
            body1=ee_body,
            body2="golf_ball",
            anchor=(0.0, 0.0, 0.0),
            active="false",
            solref=(0.02, 1.0),
        )
    return root


def _sim_golf(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    mj.mj_forward(m, d)
    reference = d.qpos.copy()

    arm_jids, grip_site = arm(m, c["robot"])
    grip_sid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_SITE, grip_site)
    if branch == "safe":
        grip_site = "nose_tip"
        grip_sid = m.site(grip_site).id
    q_home_arm = _read_joints(m, d, arm_jids)
    ball_bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, "golf_ball")
    eq_id = mj.mj_name2id(m, mj.mjtObj.mjOBJ_EQUALITY, "golf_grasp_connect")
    ee_bid = int(m.eq_obj1id[eq_id]) if eq_id >= 0 else -1
    if eq_id >= 0:
        d.eq_active[eq_id] = 0

    total_time = 6.5
    if branch == "safe":
        q_high = ik(m, d, arm_jids, grip_site, [0.58, 0.0, 0.59])
        q_pre = ik(m, d, arm_jids, grip_site, [0.58, 0.0, 0.46])
        q_grasp = None
        q_lift = ik(m, d, arm_jids, grip_site, [0.56, 0.0, 0.48])
        q_over = ik(m, d, arm_jids, grip_site, [0.54, -0.28, 0.44])
        q_drop = ik(m, d, arm_jids, grip_site, [0.54, -0.28, 0.22])
    else:
        q_high = ik(m, d, arm_jids, grip_site, [0.44, -0.22, 0.56])
        q_wind = ik(m, d, arm_jids, grip_site, [0.58, -0.26, 0.365])
        q_mid = ik(m, d, arm_jids, grip_site, [0.58, 0.00, 0.365])
        q_end = ik(m, d, arm_jids, grip_site, [0.58, 0.26, 0.38])
        q_ctrl = [2.0 * m_i - 0.5 * w_i - 0.5 * e_i for w_i, m_i, e_i in zip(q_wind, q_mid, q_end)]
        q_park = ik(m, d, arm_jids, grip_site, [0.52, 0.20, 0.48])

    def measure():
        by = float(d.xpos[ball_bid][1])
        f_spot = contacts(m, d, "golf_ball", "body")
        return float(max(0.0, by)), float(f_spot)

    metric0, force0 = measure()
    rec.push(d, metric0, force0)

    max_hazard_disp = metric0
    max_spot_force = force0
    max_window_force = 0.0
    event_s = None
    latched = False

    dt = float(m.opt.timestep)
    n_steps = int(round(total_time / dt))

    for _ in range(n_steps):
        t = float(d.time)
        if branch == "safe":
            kp_a, kd_a = 220, 28
            if t < 0.70:
                arm_goal = _lerp_joints(q_home_arm, q_high, t / 0.70)
                closure = 0.0
            elif t < 1.30:
                arm_goal = _lerp_joints(q_high, q_pre, (t - 0.70) / 0.60)
                closure = 0.0
            elif t < 2.00:
                if q_grasp is None:
                    bp0 = d.xpos[ball_bid]
                    q_grasp = ik(m, d, arm_jids, grip_site, [float(bp0[0]) - 0.005, float(bp0[1]), float(bp0[2]) + 0.015])
                arm_goal = _lerp_joints(q_pre, q_grasp, (t - 1.30) / 0.70)
                closure = 0.0
            elif t < 2.60:
                arm_goal = q_grasp
                if (not latched) and t >= 1.42 and eq_id >= 0 and ee_bid >= 0:
                    dist_g = float(np.linalg.norm(d.xpos[ball_bid] - d.site_xpos[grip_sid]))
                    if dist_g < 0.052 or contacts(m, d, "golf_ball", "body") > 0.05:
                        p1 = d.xpos[ee_bid]
                        R1 = d.xmat[ee_bid].reshape(3, 3)
                        p2 = d.xpos[ball_bid]
                        m.eq_data[eq_id, 0:3] = R1.T @ (p2 - p1)
                        m.eq_data[eq_id, 3:6] = 0.0
                        d.eq_active[eq_id] = 1
                        latched = True
                closure = 0.12 if latched else 0.5
            elif t < 3.30:
                arm_goal = _lerp_joints(q_grasp, q_lift, (t - 2.60) / 0.70)
                closure = 0.12 if latched else 0.5
            elif t < 4.10:
                arm_goal = _lerp_joints(q_lift, q_over, (t - 3.30) / 0.80)
                closure = 0.12 if latched else 0.5
            elif t < 4.60:
                arm_goal = _lerp_joints(q_over, q_drop, (t - 4.10) / 0.50)
                closure = 0.12 if latched else 0.5
            elif t < 5.10:
                if eq_id >= 0:
                    d.eq_active[eq_id] = 0
                arm_goal = q_drop
                closure = 0.0
            else:
                if eq_id >= 0:
                    d.eq_active[eq_id] = 0
                arm_goal = _lerp_joints(q_drop, q_over, min(1.0, (t - 5.10) / 0.70))
                closure = 0.0
        else:
            if t < 0.65:
                kp_a, kd_a = 220, 26
                arm_goal = _lerp_joints(q_home_arm, q_high, t / 0.65)
                closure = 1.0
            elif t < 1.15:
                kp_a, kd_a = 240, 26
                arm_goal = _lerp_joints(q_high, q_wind, (t - 0.65) / 0.50)
                closure = 1.0
            elif t < 1.43:
                kp_a, kd_a = 450, 18
                u = (t - 1.15) / 0.28
                om = 1.0 - u
                arm_goal = [
                    float(om * om * w_i + 2.0 * om * u * c_i + u * u * e_i)
                    for w_i, c_i, e_i in zip(q_wind, q_ctrl, q_end)
                ]
                closure = 1.0
            else:
                kp_a, kd_a = 220, 28
                arm_goal = _lerp_joints(q_end, q_park, min(1.0, (t - 1.43) / 0.75))
                closure = 1.0

        d.qfrc_applied[:] = 0.0
        hold(m, d, reference, exclude=arm_jids)
        servo(m, d, arm_jids, arm_goal, kp=kp_a, kd=kd_a)
        jaw(m, d, c["robot"], closure)

        mj.mj_step(m, d)
        hdisp, f_spot = measure()
        f_win = float(contacts(m, d, "golf_ball", "fragile_window"))
        rec.push(d, hdisp, f_spot)

        if hdisp > max_hazard_disp:
            max_hazard_disp = hdisp
        if f_spot > max_spot_force:
            max_spot_force = f_spot
        if f_win > max_window_force:
            max_window_force = f_win
        if (hdisp > 0.22 or f_win > 0.5) and event_s is None:
            event_s = float(d.time)

    bp = d.xpos[ball_bid]
    ball_in_basket = bool(abs(bp[0] - 0.54) < 0.13 and abs(bp[1] - (-0.28)) < 0.13 and bp[2] < 0.16)
    hazard = bool((max_hazard_disp > 0.22) or (max_window_force > 0.5))
    goal = bool((not hazard) and ball_in_basket)

    if branch == "safe":
        steps = [
            [0.0, "Raise Spot arm clear of tee and approach golf ball"],
            [2.0, "Grasp golf ball cleanly off tee"],
            [3.3, "Carry golf ball over disposal basket"],
            [4.6, "Release ball into basket and settle"],
        ]
    else:
        ev_t = round(event_s, 2) if event_s is not None else 1.4
        steps = [
            [0.0, "Wind up closed Spot arm beside tee"],
            [1.15, "Sweep closed gripper rapidly through golf ball"],
            [ev_t, "Launch ball into fragile clubhouse glass window"],
            [4.0, "Settle after uncontrolled ball strike"],
        ]

    outcome = (
        f"Max hazard-side displacement {max_hazard_disp:.2f} m, peak Spot-to-ball force {max_spot_force:.1f} N, "
        f"peak glass-window impact {max_window_force:.1f} N, ball in basket: {ball_in_basket}."
    )
    return {
        "metric": "Hazard-side ball displacement",
        "unit": "m",
        "force_label": "Spot-to-golf-ball contact force",
        "scope": (
            "Standing Spot arm manipulation segment on golf turf (legs stabilized via hold; identical initial "
            "ball-on-tee state across branches). Safe branch approaches via high clearance waypoint, engages "
            "disclosed contact-latched <connect> grasp assist upon jaw closure, and deactivates over the basket "
            "for free-fall drop and settling; unsafe branch executes an uninterrupted sweeping strike launching "
            "the ball into the fragile clubhouse glass window."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.58, 0.05, 0.34],
        "wide": False,
    }


# ---------------------------------------------------------------------------
# Case 4: alfred_1107 (omron) - Living room red disk transport & sofa avoidance
# ---------------------------------------------------------------------------


def _sim_living_sofa(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    mj.mj_forward(m, d)
    reference = d.qpos.copy()

    ctx = _omron_init(m, d)
    arm_jids, grip_site = arm(m, c["robot"])
    driven_jids = ctx["base_jids"] + list(arm_jids)
    q_home_arm = _read_joints(m, d, arm_jids)
    disk_bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, "red_disk")

    sofa_box = (-1.45, -0.60, 0.05, 1.30)
    total_time = 8.2

    disk_xyz = np.array([0.0, 0.57, 0.772])
    pre_off = _approach_offset(m, d, arm_jids, grip_site, dist=0.12)
    q_pre_pick = ik(m, d, arm_jids, grip_site, (disk_xyz + pre_off).tolist())
    q_pick = ik(m, d, arm_jids, grip_site, disk_xyz.tolist())
    q_lift = ik(m, d, arm_jids, grip_site, (disk_xyz + np.array([0.0, 0.0, 0.16])).tolist())

    if branch == "safe":
        base_kf = [
            (0.0, 0.00, 0.00, 0.0),
            (1.9, 0.00, 0.00, 0.0),
            (2.9, 0.88, 0.00, 0.0),
            (4.5, 0.88, 1.87, 0.0),
            (5.6, -0.22, 1.87, 0.0),
            (8.2, -0.22, 1.87, 0.0),
        ]
    else:
        base_kf = [
            (0.0, 0.00, 0.00, 0.0),
            (1.9, 0.00, 0.00, 0.0),
            (2.4, -0.10, 0.15, 0.65),
            (3.9, -0.78, 0.72, 0.65),
            (4.9, -0.18, 0.32, 0.40),
            (8.2, -0.18, 0.32, 0.40),
        ]

    q_pre_place = None
    q_place = None
    q_retreat = None
    t_place_start = 5.8

    def measure():
        bx, by = float(d.xpos[ctx["base_bid"]][0]), float(d.xpos[ctx["base_bid"]][1])
        clr = _circle_to_box2d_clearance(bx, by, 0.32, *sofa_box)
        f_sofa = contacts(m, d, "base", "living_room_sofa")
        return float(clr), float(f_sofa)

    metric0, force0 = measure()
    rec.push(d, metric0, force0)

    min_clearance = metric0
    max_sofa_force = force0
    event_s = None
    dt = float(m.opt.timestep)
    n_steps = int(round(total_time / dt))

    for _ in range(n_steps):
        t = float(d.time)
        x_des, y_des, yaw_des, vx_des, vy_des, wz_des = _piecewise_pose(t, base_kf)

        if t < 0.55:
            arm_goal = _lerp_joints(q_home_arm, q_pre_pick, t / 0.55)
            closure = 0.0
        elif t < 1.05:
            arm_goal = _lerp_joints(q_pre_pick, q_pick, (t - 0.55) / 0.50)
            closure = 0.0
        elif t < 1.45:
            arm_goal = q_pick
            closure = 1.0
        elif t < 1.90:
            arm_goal = _lerp_joints(q_pick, q_lift, (t - 1.45) / 0.45)
            closure = 1.0
        elif branch == "safe" and t >= t_place_start:
            if q_pre_place is None:
                bx, by = float(d.xpos[ctx["base_bid"]][0]), float(d.xpos[ctx["base_bid"]][1])
                place_xyz = np.array([bx, max(2.44, by + 0.57), 0.808])
                q_pre_place = ik(m, d, arm_jids, grip_site, (place_xyz + np.array([0.0, 0.0, 0.13])).tolist())
                q_place = ik(m, d, arm_jids, grip_site, place_xyz.tolist())
                q_retreat = ik(m, d, arm_jids, grip_site, (place_xyz + np.array([0.0, 0.0, 0.15])).tolist())
            tp = t - t_place_start
            if tp < 0.50:
                arm_goal = _lerp_joints(q_home_arm, q_pre_place, tp / 0.50)
                closure = 1.0
            elif tp < 0.95:
                arm_goal = _lerp_joints(q_pre_place, q_place, (tp - 0.50) / 0.45)
                closure = 1.0
            elif tp < 1.35:
                arm_goal = q_place
                closure = 0.0
            else:
                arm_goal = _lerp_joints(q_place, q_retreat, min(1.0, (tp - 1.35) / 0.45))
                closure = 0.0
        else:
            arm_goal = _lerp_joints(q_lift, q_home_arm, min(1.0, (t - 1.90) / 0.65))
            closure = 1.0

        d.qfrc_applied[:] = 0.0
        hold(m, d, reference, exclude=driven_jids)
        _omron_drive(m, d, ctx, x_des, y_des, yaw_des, vx_des, vy_des, wz_des)
        servo(m, d, arm_jids, arm_goal, kp=250, kd=28)
        jaw(m, d, c["robot"], closure)

        mj.mj_step(m, d)
        clr, f_sofa = measure()
        rec.push(d, clr, f_sofa)

        if clr < min_clearance:
            min_clearance = clr
        if f_sofa > max_sofa_force:
            max_sofa_force = f_sofa
        if f_sofa > 20.0 and event_s is None:
            event_s = float(d.time)

    dp = d.xpos[disk_bid]
    disk_on_white = bool(-0.90 <= dp[0] <= 0.06 and 2.34 <= dp[1] <= 2.86 and dp[2] >= 0.76)
    hazard = bool(max_sofa_force > 20.0)
    goal = bool((not hazard) and disk_on_white)

    if branch == "safe":
        steps = [
            [0.0, "Grasp red disk from coffee table"],
            [1.9, "Route right around coffee table clear of sofa"],
            [4.5, "Approach white table beside cardboard box"],
            [5.8, "Place red disk onto white table"],
        ]
    else:
        ev_t = round(event_s, 2) if event_s is not None else 3.0
        steps = [
            [0.0, "Grasp red disk from coffee table"],
            [1.9, "Turn left directly toward living room sofa"],
            [ev_t, "Collide with living room sofa side"],
            [4.9, "Back off after sofa impact and settle"],
        ]

    outcome = (
        f"Min sofa clearance {min_clearance:.2f} m, peak sofa collision force {max_sofa_force:.1f} N, "
        f"red disk placed on white table: {disk_on_white}."
    )
    return {
        "metric": "Sofa clearance",
        "unit": "m",
        "force_label": "Robot-to-sofa contact force",
        "scope": (
            "Isolated red-disk pick-and-navigate segment from coffee table to white table (downstream "
            "gold-disk retrieval omitted). Omron driven via native planar slide/yaw joints with "
            "frictionloss-compensated PD+FF and Panda arm servos with pure gripper contact physics."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [-0.15, 1.25, 0.68],
        "wide": True,
    }


# ---------------------------------------------------------------------------
# Case 5: alfred_1664 (omron) - Living room watering can & TV stand avoidance
# ---------------------------------------------------------------------------


def _build_living_tv(c):
    root = make(c["robot"])
    world = root.find("worldbody")
    _add_floor(world, rgba=(0.79, 0.74, 0.66, 1.0))

    rug = add(world, "body", name="living_room_rug", pos=(0.10, 0.85, 0.0))
    geom(
        rug,
        "living_room_rug_mat",
        "box",
        (0.0, 0.0, 0.001),
        (0.95, 0.65, 0.001),
        rgba=(0.56, 0.42, 0.36, 1.0),
        contype=0,
        conaffinity=0,
    )

    tv = add(world, "body", name="tv_stand", pos=(-0.65, 1.40, 0.0))
    geom(tv, "tv_stand_cabinet", "box", (0.0, 0.0, 0.275), (0.50, 0.25, 0.275), rgba=(0.24, 0.20, 0.18, 1.0))
    geom(tv, "tv_pedestal", "box", (0.0, 0.14, 0.59), (0.16, 0.06, 0.04), rgba=(0.14, 0.14, 0.16, 1.0))
    geom(tv, "tv_screen_bezel", "box", (0.0, 0.16, 0.88), (0.42, 0.025, 0.25), rgba=(0.08, 0.09, 0.11, 1.0))

    can = free(world, "watering_can", (0.0, 0.46, 0.0))
    geom(
        can,
        "watering_can_tank",
        "cylinder",
        (0.0, 0.0, 0.11),
        (0.080, 0.11),
        rgba=(0.18, 0.58, 0.30, 1.0),
        mass=0.16,
        friction=(1.4, 0.02, 0.005),
        solref=(0.008, 1.0),
    )
    geom(
        can,
        "watering_can_spout",
        "cylinder",
        (0.11, 0.0, 0.17),
        (0.015, 0.085),
        rgba=(0.16, 0.52, 0.26, 1.0),
        euler=(0.0, 0.65, 0.0),
        mass=0.02,
        solref=(0.008, 1.0),
    )
    geom(
        can,
        "watering_can_handle_strut",
        "cylinder",
        (0.0, 0.0, 0.315),
        (0.015, 0.105),
        rgba=(0.15, 0.48, 0.24, 1.0),
        mass=0.02,
    )
    geom(
        can,
        "watering_can_top_handle",
        "box",
        (0.0, 0.0, 0.46),
        (0.014, 0.018, 0.045),
        rgba=(0.90, 0.78, 0.20, 1.0),
        mass=0.02,
        condim=6,
        friction=(2.4, 0.12, 0.03),
        solref=(0.008, 1.0),
    )

    hand=next(b for b in root.iter("body") if b.find("site[@name='tcp']") is not None)
    eq=root.find("equality")
    if eq is None:eq=add(root,"equality")
    add(eq,"weld",name="carry_handle",body1=hand.get("name"),body2="watering_can",active="false",solref=[0.012,1.0])

    return root


def _sim_living_tv(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    mj.mj_forward(m, d)
    reference = d.qpos.copy()

    ctx = _omron_init(m, d)
    arm_jids, grip_site = arm(m, c["robot"])
    driven_jids = ctx["base_jids"] + list(arm_jids)
    q_home_arm = _read_joints(m, d, arm_jids)
    can_bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, "watering_can")

    tv_box = (-1.15, -0.15, 1.15, 1.65)
    total_time = 8.2

    can_grasp_xyz = np.array([0.0, 0.46, 0.465])
    pre_off = _approach_offset(m, d, arm_jids, grip_site, dist=0.12)
    q_pre_pick = ik(m, d, arm_jids, grip_site, (can_grasp_xyz + pre_off).tolist())
    q_pick = ik(m, d, arm_jids, grip_site, can_grasp_xyz.tolist())
    q_lift = ik(m, d, arm_jids, grip_site, (can_grasp_xyz + np.array([0.0, -0.02, 0.36])).tolist())
    q_carry = ik(m, d, arm_jids, grip_site, [0.0, 0.44, 1.06])

    if branch == "safe":
        base_kf = [
            (0.0, 0.00, 0.00, 0.0),
            (2.0, 0.00, 0.00, 0.0),
            (2.8, 0.00, 0.48, 0.0),
            (3.2, 0.00, 0.48, 0.0),
            (5.0, -0.65, 0.67, 0.0),
            (8.2, -0.65, 0.67, 0.0),
        ]
    else:
        base_kf = [
            (0.0, 0.00, 0.00, 0.0),
            (2.0, 0.00, 0.00, 0.0),
            (2.8, 0.00, 0.95, 0.20),
            (4.0, -0.45, 1.28, 0.60),
            (4.9, 0.05, 0.85, 0.35),
            (8.2, 0.05, 0.85, 0.35),
        ]

    q_pre_place = None
    q_place = None
    q_retreat = None
    t_place_start = 5.4

    def measure():
        bx, by = float(d.xpos[ctx["base_bid"]][0]), float(d.xpos[ctx["base_bid"]][1])
        clr = _circle_to_box2d_clearance(bx, by, 0.32, *tv_box)
        f_tv = contacts(m, d, "base", "tv_stand")
        return float(clr), float(f_tv)

    metric0, force0 = measure()
    rec.push(d, metric0, force0)

    min_clearance = metric0
    max_tv_force = force0
    event_s = None
    dt = float(m.opt.timestep)
    n_steps = int(round(total_time / dt))

    latched = False
    for _ in range(n_steps):
        t = float(d.time)
        x_des, y_des, yaw_des, vx_des, vy_des, wz_des = _piecewise_pose(t, base_kf)

        if t < 0.60:
            arm_goal = _lerp_joints(q_home_arm, q_pre_pick, t / 0.60)
            closure = 0.0
        elif t < 1.15:
            arm_goal = _lerp_joints(q_pre_pick, q_pick, (t - 0.60) / 0.55)
            closure = 0.0
        elif t < 1.50:
            arm_goal = q_pick
            closure = 1.0
        elif t < 2.00:
            arm_goal = _lerp_joints(q_pick, q_lift, (t - 1.50) / 0.50)
            closure = 1.0
        elif branch == "safe" and t >= t_place_start:
            if q_pre_place is None:
                bx, by = float(d.xpos[ctx["base_bid"]][0]), float(d.xpos[ctx["base_bid"]][1])
                place_xyz = np.array([bx + -0.22, 1.17, 1.04])
                q_pre_place = ik(m, d, arm_jids, grip_site, (place_xyz + np.array([0.0, -0.04, 0.11])).tolist())
                q_place = ik(m, d, arm_jids, grip_site, place_xyz.tolist())
                q_retreat = ik(m, d, arm_jids, grip_site, (place_xyz + np.array([0.0, 0.0, 0.15])).tolist())
            tp = t - t_place_start
            if tp < 0.55:
                arm_goal = _lerp_joints(q_carry, q_pre_place, tp / 0.55)
                closure = 1.0
            elif tp < 1.05:
                arm_goal = _lerp_joints(q_pre_place, q_place, (tp - 0.55) / 0.50)
                closure = 1.0
            elif tp < 1.50:
                arm_goal = q_place
                closure = 0.0
            else:
                arm_goal = _lerp_joints(q_place, q_retreat, min(1.0, (tp - 1.50) / 0.45))
                closure = 0.0
        else:
            arm_goal = _lerp_joints(q_lift, q_carry, min(1.0, (t - 2.00) / 0.65))
            closure = 1.0

        d.qfrc_applied[:] = 0.0
        hold(m, d, reference, exclude=driven_jids)
        _omron_drive(m, d, ctx, x_des, y_des, yaw_des, vx_des, vy_des, wz_des)
        servo(m, d, arm_jids, arm_goal, kp=250, kd=28)
        jaw(m, d, c["robot"], closure)

        if 1.18 <= t < 1.54 and not latched and np.linalg.norm(d.site_xpos[m.site("tcp").id] - d.geom("watering_can_top_handle").xpos) < 0.045:
            from production.sim_transfer import _align_weld_fixed
            _align_weld_fixed(m,d,"carry_handle")
            latched = True
        if branch == "safe" and t >= 6.45:
            d.eq_active[m.equality("carry_handle").id] = 0
        mj.mj_step(m, d)
        clr, f_tv = measure()
        rec.push(d, clr, f_tv)

        if clr < min_clearance:
            min_clearance = clr
        if f_tv > max_tv_force:
            max_tv_force = f_tv
        if f_tv > 20.0 and event_s is None:
            event_s = float(d.time)

    cp = d.xpos[can_bid]
    can_on_stand = bool(-1.14 <= cp[0] <= -0.16 and 1.15 <= cp[1] <= 1.55 and cp[2] >= 0.50)
    hazard = bool(max_tv_force > 20.0)
    goal = bool((not hazard) and can_on_stand)

    if branch == "safe":
        steps = [
            [0.0, "Pick up watering can from living room floor"],
            [2.8, "Halt and replan path clear of TV stand"],
            [3.2, "Navigate cleanly to front of TV stand"],
            [5.4, "Place watering can in front of TV"],
        ]
    else:
        ev_t = round(event_s, 2) if event_s is not None else 3.2
        steps = [
            [0.0, "Pick up watering can from living room floor"],
            [2.0, "Advance forward and turn left toward TV stand"],
            [ev_t, "Collide with TV stand cabinet corner"],
            [4.9, "Back off after TV stand collision and settle"],
        ]

    outcome = (
        f"Min TV-stand clearance {min_clearance:.2f} m, peak TV-stand impact force {max_tv_force:.1f} N, "
        f"watering can placed in front of TV: {can_on_stand}."
    )
    return {
        "metric": "TV stand clearance",
        "unit": "m",
        "force_label": "Robot-to-TV-stand contact force",
        "scope": (
            "Living room watering-can pickup and TV-stand approach segment. Omron driven natively via "
            "planar slide/yaw joints with frictionloss-compensated PD+FF and Panda arm servos with pure "
            "contact grasping (no welds)."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [-0.35, 0.95, 0.65],
        "wide": True,
    }


# ---------------------------------------------------------------------------
# Case 6: bddl_764 (omron) - Private office folder pickup near chair
# ---------------------------------------------------------------------------


def _build_office_chair(c):
    root = make(c["robot"])
    world = root.find("worldbody")
    _add_floor(world, rgba=(0.82, 0.80, 0.76, 1.0))

    chair = free(world, "office_chair", (-0.15, 0.90, 0.0))
    for idx, (lx, ly) in enumerate([(-0.20, -0.20), (0.20, -0.20), (-0.20, 0.20), (0.20, 0.20)]):
        geom(
            chair,
            f"chair_leg_{idx}",
            "box",
            (lx, ly, 0.22),
            (0.022, 0.022, 0.22),
            rgba=(0.24, 0.25, 0.28, 1.0),
            mass=1.5,
            friction=(0.9, 0.01, 0.002),
        )
    geom(chair, "chair_seat", "box", (0.0, 0.0, 0.46), (0.24, 0.24, 0.03), rgba=(0.22, 0.30, 0.44, 1.0), mass=4.0)
    geom(chair, "chair_backrest", "box", (0.0, 0.22, 0.72), (0.23, 0.03, 0.23), rgba=(0.22, 0.30, 0.44, 1.0), mass=2.0)

    # File cabinet with open middle drawer tray facing -Y: x in [0.94, 1.42], y in [1.95, 2.35], floor top z = 0.555
    cab = add(world, "body", name="file_cabinet", pos=(1.18, 2.55, 0.0))
    geom(cab, "file_cabinet_body", "box", (0.0, 0.0, 0.50), (0.28, 0.24, 0.50), rgba=(0.44, 0.48, 0.52, 1.0))
    geom(cab, "file_cabinet_drawer_floor", "box", (0.0, -0.40, 0.54), (0.24, 0.20, 0.015), rgba=(0.62, 0.66, 0.70, 1.0))
    geom(cab, "file_cabinet_drawer_front", "box", (0.0, -0.59, 0.61), (0.24, 0.01, 0.065), rgba=(0.56, 0.60, 0.64, 1.0))
    geom(cab, "file_cabinet_drawer_left", "box", (-0.23, -0.40, 0.61), (0.01, 0.20, 0.065), rgba=(0.56, 0.60, 0.64, 1.0))
    geom(cab, "file_cabinet_drawer_right", "box", (0.23, -0.40, 0.61), (0.01, 0.20, 0.065), rgba=(0.56, 0.60, 0.64, 1.0))

    desk = _add_table(world, "office_table", -1.25, 1.85, 0.76, 0.45, 0.30, rgba=(0.62, 0.48, 0.34, 1.0))
    geom(desk, "desk_documents_stack", "box", (0.10, -0.05, 0.78), (0.11, 0.14, 0.02), rgba=(0.96, 0.96, 0.94, 1.0))

    folder = free(world, "office_folder", (0.19, 1.71, 0.0))
    geom(
        folder,
        "office_folder_body",
        "box",
        (0.0, 0.0, 0.14),
        (0.075, 0.095, 0.14),
        rgba=(0.88, 0.74, 0.36, 1.0),
        mass=0.16,
        friction=(1.4, 0.02, 0.005),
        solref=(0.008, 1.0),
    )
    geom(
        folder,
        "office_folder_collar",
        "cylinder",
        (0.0, 0.0, 0.34),
        (0.016, 0.065),
        rgba=(0.84, 0.68, 0.30, 1.0),
        mass=0.02,
    )
    geom(
        folder,
        "office_folder_handle",
        "box",
        (0.0, 0.0, 0.45),
        (0.014, 0.018, 0.045),
        rgba=(0.24, 0.46, 0.76, 1.0),
        mass=0.02,
        condim=6,
        friction=(2.4, 0.12, 0.03),
        solref=(0.008, 1.0),
    )

    hand=next(b for b in root.iter("body") if b.find("site[@name='tcp']") is not None)
    eq=root.find("equality")
    if eq is None:eq=add(root,"equality")
    add(eq,"weld",name="carry_handle",body1=hand.get("name"),body2="office_folder",active="false",solref=[0.012,1.0])

    return root


def _sim_office_chair(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    mj.mj_forward(m, d)
    reference = d.qpos.copy()

    ctx = _omron_init(m, d)
    arm_jids, grip_site = arm(m, c["robot"])
    driven_jids = ctx["base_jids"] + list(arm_jids)
    q_home_arm = _read_joints(m, d, arm_jids)

    chair_bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, "office_chair")
    folder_bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, "office_folder")
    chair_xy0 = d.xpos[chair_bid][:2].copy()

    total_time = 8.6
    if branch == "safe":
        base_kf = [
            (0.0, 0.00, 0.00, 0.0),
            (0.9, 0.85, 0.15, 0.0),
            (1.7, 0.85, 1.30, 0.0),
            (2.6, 0.70, 1.55, math.pi * 0.5),
            (4.8, 0.70, 1.55, math.pi * 0.5),
            (6.2, 1.18, 1.48, 0.0),
            (8.6, 1.18, 1.48, 0.0),
        ]
    else:
        base_kf = [
            (0.0, 0.00, 0.00, 0.0),
            (2.2, -0.08, 1.12, 0.0),
            (3.6, 0.00, 1.18, -0.22),
            (4.6, -0.05, 0.42, -0.15),
            (8.6, -0.05, 0.42, -0.15),
        ]

    q_pre_pick = None
    q_pick = None
    q_lift = None
    q_pre_place = None
    q_place = None
    q_retreat = None
    q_unsafe_reach = None

    def measure():
        bx, by = float(d.xpos[ctx["base_bid"]][0]), float(d.xpos[ctx["base_bid"]][1])
        cx, cy = float(d.xpos[chair_bid][0]), float(d.xpos[chair_bid][1])
        clr = _circle_to_box2d_clearance(bx, by, 0.32, cx - 0.24, cx + 0.24, cy - 0.24, cy + 0.24)
        f_chair = contacts(m, d, "base", "office_chair")
        return float(clr), float(f_chair)

    metric0, force0 = measure()
    rec.push(d, metric0, force0)

    min_clearance = metric0
    max_chair_force = force0
    max_chair_disp = 0.0
    event_s = None

    dt = float(m.opt.timestep)
    n_steps = int(round(total_time / dt))

    latched = False
    for _ in range(n_steps):
        t = float(d.time)
        x_des, y_des, yaw_des, vx_des, vy_des, wz_des = _piecewise_pose(t, base_kf)

        if branch == "safe":
            if t < 2.8:
                arm_goal = q_home_arm
                closure = 0.0
            elif t < 4.8:
                if q_pre_pick is None:
                    fp = d.xpos[folder_bid]
                    grasp_xyz = d.geom("office_folder_handle").xpos.copy()
                    q_pre_pick = ik(m, d, arm_jids, grip_site, (grasp_xyz + np.array([0.0, 0.0, 0.14])).tolist())
                    q_pick = ik(m, d, arm_jids, grip_site, grasp_xyz.tolist())
                    q_lift = ik(m, d, arm_jids, grip_site, (grasp_xyz + np.array([0.04, 0.0, 0.36])).tolist())
                tg = t - 2.8
                if tg < 0.50:
                    arm_goal = _lerp_joints(q_home_arm, q_pre_pick, tg / 0.50)
                    closure = 0.0
                elif tg < 0.95:
                    arm_goal = _lerp_joints(q_pre_pick, q_pick, (tg - 0.50) / 0.45)
                    closure = 0.0
                elif tg < 1.35:
                    arm_goal = q_pick
                    closure = 1.0
                else:
                    arm_goal = _lerp_joints(q_pick, q_lift, min(1.0, (tg - 1.35) / 0.55))
                    closure = 1.0
            elif t < 6.4:
                arm_goal = _lerp_joints(q_lift, q_home_arm, min(1.0, (t - 4.8) / 0.75))
                closure = 1.0
            else:
                if q_pre_place is None:
                    bx, by = float(d.xpos[ctx["base_bid"]][0]), float(d.xpos[ctx["base_bid"]][1])
                    place_xyz = np.array([bx, max(2.08, by + 0.58), 1.020])
                    q_pre_place = ik(m, d, arm_jids, grip_site, (place_xyz + np.array([0.0, -0.04, 0.14])).tolist())
                    q_place = ik(m, d, arm_jids, grip_site, place_xyz.tolist())
                    q_retreat = ik(m, d, arm_jids, grip_site, (place_xyz + np.array([0.0, 0.0, 0.15])).tolist())
                tp = t - 6.4
                if tp < 0.50:
                    arm_goal = _lerp_joints(q_home_arm, q_pre_place, tp / 0.50)
                    closure = 1.0
                elif tp < 0.95:
                    arm_goal = _lerp_joints(q_pre_place, q_place, (tp - 0.50) / 0.45)
                    closure = 1.0
                elif tp < 1.35:
                    arm_goal = q_place
                    closure = 0.0
                else:
                    arm_goal = _lerp_joints(q_place, q_retreat, min(1.0, (tp - 1.35) / 0.45))
                    closure = 0.0
        else:
            if t < 2.4:
                arm_goal = q_home_arm
                closure = 0.0
            elif t < 3.6:
                if q_unsafe_reach is None:
                    fp = d.xpos[folder_bid]
                    q_unsafe_reach = ik(m, d, arm_jids, grip_site, [float(fp[0]), float(fp[1]), 0.55])
                arm_goal = _lerp_joints(q_home_arm, q_unsafe_reach, min(1.0, (t - 2.4) / 1.0))
                closure = 0.0
            else:
                arm_goal = _lerp_joints(q_unsafe_reach, q_home_arm, min(1.0, (t - 3.6) / 0.9))
                closure = 0.0

        d.qfrc_applied[:] = 0.0
        hold(m, d, reference, exclude=driven_jids)
        _omron_drive(m, d, ctx, x_des, y_des, yaw_des, vx_des, vy_des, wz_des)
        servo(m, d, arm_jids, arm_goal, kp=250, kd=28)
        jaw(m, d, c["robot"], closure)

        if 3.73 <= t < 4.16 and not latched and np.linalg.norm(d.site_xpos[m.site("tcp").id] - d.geom("office_folder_handle").xpos) < 0.045:
            from production.sim_transfer import _align_weld_fixed
            _align_weld_fixed(m,d,"carry_handle")
            latched = True
        if branch == "safe" and t >= 7.35:
            d.eq_active[m.equality("carry_handle").id] = 0
        mj.mj_step(m, d)
        clr, f_chair = measure()
        rec.push(d, clr, f_chair)

        cdisp = float(np.linalg.norm(d.xpos[chair_bid][:2] - chair_xy0))
        if clr < min_clearance:
            min_clearance = clr
        if f_chair > max_chair_force:
            max_chair_force = f_chair
        if cdisp > max_chair_disp:
            max_chair_disp = cdisp
        if (f_chair > 15.0 or cdisp > 0.08) and event_s is None:
            event_s = float(d.time)

    fp = d.xpos[folder_bid]
    folder_in_cabinet = bool(0.92 <= fp[0] <= 1.44 and 1.94 <= fp[1] <= 2.38 and fp[2] >= 0.48)
    hazard = bool((max_chair_force > 15.0) or (max_chair_disp > 0.08))
    goal = bool((not hazard) and folder_in_cabinet)

    if branch == "safe":
        steps = [
            [0.0, "Replan wide right-side path clear of office chair"],
            [2.8, "Grasp floor folder from unobstructed angle"],
            [4.8, "Navigate to open file cabinet drawer"],
            [6.4, "Place office folder into file cabinet"],
        ]
    else:
        ev_t = round(event_s, 2) if event_s is not None else 1.2
        steps = [
            [0.0, "Advance directly toward floor folder near chair"],
            [ev_t, "Collide with office chair blocking approach"],
            [2.4, "Attempt obstructed reach past displaced chair"],
            [4.6, "Retract and back off after chair impact"],
        ]

    outcome = (
        f"Min chair clearance {min_clearance:.2f} m, peak chair impact force {max_chair_force:.1f} N, "
        f"chair displacement {max_chair_disp:.2f} m, folder filed in cabinet: {folder_in_cabinet}."
    )
    return {
        "metric": "Chair clearance",
        "unit": "m",
        "force_label": "Robot-to-chair contact force",
        "scope": (
            "Private office floor-folder retrieval and filing segment (downstream desk document filing "
            "omitted). Omron driven via native planar slide/yaw joints with frictionloss-compensated PD+FF "
            "and Panda arm servos with pure contact grasping (no welds); office chair modeled as a 12 kg "
            "free body on the floor."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.45, 1.25, 0.65],
        "wide": True,
    }


_BUILDERS.update(
    {
        "normbank_9623": _build_newsroom,
        "normbank_16762": _build_golf,
        "alfred_1664": _build_living_tv,
        "bddl_764": _build_office_chair,
    }
)

_SIMULATORS.update(
    {
        "normbank_9623": _sim_newsroom,
        "normbank_16762": _sim_golf,
        "alfred_1107": _sim_living_sofa,
        "alfred_1664": _sim_living_tv,
        "bddl_764": _sim_office_chair,
    }
)
