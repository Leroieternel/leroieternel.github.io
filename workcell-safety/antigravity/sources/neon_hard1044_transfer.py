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
    hold,
    contacts,
    add,
    geom,
    free,
    target,
)


# ---------------------------------------------------------------------------
# Shared XML / MuJoCo Helpers
# ---------------------------------------------------------------------------

def _add_floor(world, rgba=(0.83, 0.82, 0.79, 1.0), friction=(0.8, 0.005, 0.0001)):
    geom(
        world,
        "floor",
        "plane",
        [0.0, 0.0, 0.0],
        [6.0, 6.0, 0.05],
        rgba=rgba,
        friction=list(friction),
    )


def _add_ring_walls(
    parent,
    prefix,
    radius,
    z_center,
    half_height,
    half_thick,
    n_seg,
    rgba,
    tilt_rad=0.0,
    mass_each=None,
    center_xy=(0.0, 0.0),
    **kwargs,
):
    seg_half_len = radius * math.tan(math.pi / n_seg) * 1.08
    cx, cy = center_xy
    for i in range(n_seg):
        ang = 2.0 * math.pi * i / n_seg
        px = cx + radius * math.cos(ang)
        py = cy + radius * math.sin(ang)
        # Local X points radially outward, local Y tangent, local Z upward;
        # tilt_rad > 0 flares upper rim outward around local Y.
        cz = math.cos(ang)
        sz = math.sin(ang)
        ct = math.cos(tilt_rad)
        st = math.sin(tilt_rad)
        # R = Rz(ang) @ Ry(tilt_rad)
        rot = np.array(
            [
                [cz * ct, -sz, cz * st],
                [sz * ct, cz, sz * st],
                [-st, 0.0, ct],
            ],
            dtype=float,
        )
        quat = _mat_to_quat(rot)
        kw = dict(kwargs)
        kw["quat"] = quat.tolist()
        if mass_each is not None:
            kw["mass"] = mass_each
        geom(
            parent,
            f"{prefix}_{i}",
            "box",
            [px, py, z_center],
            [half_thick, seg_half_len, half_height],
            rgba=rgba,
            **kw,
        )


def _mat_to_quat(R):
    q = np.zeros(4, dtype=float)
    tr = R[0, 0] + R[1, 1] + R[2, 2]
    if tr > 0.0:
        s = 2.0 * math.sqrt(tr + 1.0)
        q[0] = 0.25 * s
        q[1] = (R[2, 1] - R[1, 2]) / s
        q[2] = (R[0, 2] - R[2, 0]) / s
        q[3] = (R[1, 0] - R[0, 1]) / s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = 2.0 * math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
        q[0] = (R[2, 1] - R[1, 2]) / s
        q[1] = 0.25 * s
        q[2] = (R[0, 1] + R[1, 0]) / s
        q[3] = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = 2.0 * math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
        q[0] = (R[0, 2] - R[2, 0]) / s
        q[1] = (R[0, 1] + R[1, 0]) / s
        q[2] = 0.25 * s
        q[3] = (R[1, 2] + R[2, 1]) / s
    else:
        s = 2.0 * math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
        q[0] = (R[1, 0] - R[0, 1]) / s
        q[1] = (R[0, 2] + R[2, 0]) / s
        q[2] = (R[1, 2] + R[2, 1]) / s
        q[3] = 0.25 * s
    n = np.linalg.norm(q)
    return q / n if n > 1e-12 else np.array([1.0, 0.0, 0.0, 0.0])


def _quat_conj(q):
    return np.array([q[0], -q[1], -q[2], -q[3]], dtype=float)


def _quat_mul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return np.array(
        [
            w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        ],
        dtype=float,
    )


def _side_matches(text, side):
    low = text.lower()
    if side == "right":
        has_r = (
            "right" in low
            or low.startswith("r_")
            or "_r_" in low
            or low.endswith("_r")
            or "rh_" in low
        )
        has_l = (
            "left" in low
            or low.startswith("l_")
            or "_l_" in low
            or low.endswith("_l")
            or "lh_" in low
        )
        return has_r and not has_l
    if side == "left":
        has_l = (
            "left" in low
            or low.startswith("l_")
            or "_l_" in low
            or low.endswith("_l")
            or "lh_" in low
        )
        has_r = (
            "right" in low
            or low.startswith("r_")
            or "_r_" in low
            or low.endswith("_r")
            or "rh_" in low
        )
        return has_l and not has_r
    return True


def _is_excluded_link(name):
    low = name.lower()
    bad = (
        "finger",
        "thumb",
        "index",
        "middle",
        "ring",
        "pinky",
        "tip",
        "pad",
        "knuckle",
        "foot",
        "ankle",
        "knee",
        "hip",
        "shin",
        "thigh",
        "head",
        "neck",
        "cam",
        "imu",
        "wheel",
        "lidar",
        "caster",
    )
    return any(tok in low for tok in bad)


def _find_ee_body(root, robot_key, side="right"):
    world = root.find("worldbody")
    bimanual = robot_key in ("baxter", "gr1")
    site_candidates = []
    body_candidates = []

    def walk(elem, depth, path_names):
        for child in elem:
            if child.tag == "body":
                bname = child.get("name", "")
                new_path = path_names + ([bname] if bname else [])
                joined = "/".join(new_path)
                if bname and not _is_excluded_link(bname):
                    if not bimanual or _side_matches(joined, side):
                        low = bname.lower()
                        score = 0
                        for k, kw in enumerate(
                            (
                                "grip",
                                "palm",
                                "hand",
                                "gripper",
                                "wrist",
                                "flange",
                                "ee",
                                "link7",
                                "link_7",
                            )
                        ):
                            if kw in low:
                                score = max(score, 20 - k)
                        if score > 0:
                            body_candidates.append((score, depth, bname))
                for sub in child:
                    if sub.tag == "site" and bname and not _is_excluded_link(bname):
                        sname = sub.get("name", "")
                        if _is_excluded_link(sname):
                            continue
                        full_text = joined + "/" + sname
                        if bimanual and not _side_matches(full_text, side):
                            continue
                        slow = sname.lower()
                        sscore = 1
                        for k, kw in enumerate(
                            (
                                "grip",
                                "pinch",
                                "tcp",
                                "eef",
                                "grasp",
                                "palm",
                                "hand",
                                "ee",
                                "tool",
                                "attach",
                                "wrist",
                            )
                        ):
                            if kw in slow:
                                sscore = max(sscore, 30 - k)
                        site_candidates.append((sscore, depth, bname))
                walk(child, depth + 1, new_path)

    walk(world, 0, [])
    if site_candidates:
        site_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return site_candidates[0][2]
    if body_candidates:
        body_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return body_candidates[0][2]
    raise RuntimeError(f"Could not locate end-effector body for {robot_key} ({side})")


def _add_weld(root, name, body1, body2):
    eq = root.find("equality")
    if eq is None:
        eq = add(root, "equality")
    add(
        eq,
        "weld",
        name=name,
        body1=body1,
        body2=body2,
        active="true",
        solref=[0.008, 1.0],
        solimp=[0.95, 0.99, 0.001],
    )


def _set_free_pose(m, d, body_name, pos, quat=(1.0, 0.0, 0.0, 0.0)):
    jid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_JOINT, f"{body_name}_free")
    qadr = int(m.jnt_qposadr[jid])
    vadr = int(m.jnt_dofadr[jid])
    d.qpos[qadr : qadr + 3] = np.asarray(pos, dtype=float)
    q = np.asarray(quat, dtype=float)
    q = q / (np.linalg.norm(q) + 1e-12)
    d.qpos[qadr + 3 : qadr + 7] = q
    d.qvel[vadr : vadr + 6] = 0.0


def _align_weld(m, d, weld_name):
    eq_id = mj.mj_name2id(m, mj.mjtObj.mjOBJ_EQUALITY, weld_name)
    b1 = int(m.eq_obj1id[eq_id])
    b2 = int(m.eq_obj2id[eq_id])
    if hasattr(d, "eq_active"):
        d.eq_active[eq_id] = 1
    mj.mj_forward(m, d)
    p1 = d.xpos[b1].copy()
    p2 = d.xpos[b2].copy()
    R1 = d.xmat[b1].reshape(3, 3).copy()
    R2 = d.xmat[b2].reshape(3, 3).copy()
    q1 = d.xquat[b1].copy()
    q2 = d.xquat[b2].copy()

    pos_1_in_2 = R2.T @ (p1 - p2)
    pos_2_in_1 = R1.T @ (p2 - p1)
    q_a = _quat_mul(_quat_conj(q2), q1)
    q_b = _quat_mul(_quat_conj(q1), q2)

    best_err = float("inf")
    best_data = m.eq_data[eq_id].copy()
    for p_cand in (pos_1_in_2, pos_2_in_1):
        for q_cand in (q_a, q_b):
            cand = m.eq_data[eq_id].copy()
            cand[0:3] = 0.0
            cand[3:6] = p_cand
            cand[6:10] = q_cand
            if len(cand) > 10:
                cand[10] = 1.0
            m.eq_data[eq_id] = cand
            mj.mj_forward(m, d)
            mask = (d.efc_type == mj.mjtConstraint.mjCNSTR_EQUALITY) & (
                d.efc_id == eq_id
            )
            err = (
                float(np.linalg.norm(d.efc_pos[mask]))
                if np.any(mask)
                else float("inf")
            )
            if err < best_err:
                best_err = err
                best_data = cand.copy()
    m.eq_data[eq_id] = best_data
    mj.mj_forward(m, d)
    return eq_id


def _disable_weld(m, d, eq_id):
    if hasattr(d, "eq_active"):
        d.eq_active[eq_id] = 0
    else:
        m.eq_active[eq_id] = 0


def _smooth(t, t0, t1):
    if t <= t0:
        return 0.0
    if t >= t1:
        return 1.0
    s = (t - t0) / max(t1 - t0, 1e-9)
    return 0.5 * (1.0 - math.cos(math.pi * s))


def _lerp3(p0, p1, s):
    return (1.0 - s) * np.asarray(p0, dtype=float) + s * np.asarray(p1, dtype=float)


def _body_speed(m, d, body_name):
    jid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_JOINT, f"{body_name}_free")
    vadr = int(m.jnt_dofadr[jid])
    return float(np.linalg.norm(d.qvel[vadr : vadr + 3]))


def _body_tilt_deg(m, d, body_name):
    bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, body_name)
    r22 = float(np.clip(d.xmat[bid, 8], -1.0, 1.0))
    return math.degrees(math.acos(r22))


def _jnt_q(m, d, jids):
    return np.array([d.qpos[int(m.jnt_qposadr[j])] for j in jids], dtype=float)


class _ArmTracker:
    """Rate-limited Cartesian-to-joint tracker using host ik() and servo()."""

    def __init__(self, m, d, jids, site, ik_stride=25, max_vel=2.2):
        self.m = m
        self.jids = list(jids)
        self.site = site
        self.ik_stride = int(ik_stride)
        self.max_vel = float(max_vel)
        self.q_cmd = _jnt_q(m, d, self.jids)
        self.q_goal = self.q_cmd.copy()
        self.step_count = 0

    def update_xyz(self, d, xyz, wrist_override=None, kp=250, kd=28):
        if self.step_count % self.ik_stride == 0:
            solved = np.asarray(
                ik(self.m, d, self.jids, self.site, np.asarray(xyz, dtype=float)),
                dtype=float,
            )
            if wrist_override is not None:
                for idx, val in wrist_override.items():
                    solved[idx] = val
            self.q_goal = solved
        elif wrist_override is not None:
            for idx, val in wrist_override.items():
                self.q_goal[idx] = val
        self.step_count += 1
        max_dq = self.max_vel * float(self.m.opt.timestep)
        delta = np.clip(self.q_goal - self.q_cmd, -max_dq, max_dq)
        self.q_cmd = self.q_cmd + delta
        servo(self.m, d, self.jids, self.q_cmd.tolist(), kp=kp, kd=kd)

    def update_joints(self, d, q_target, kp=250, kd=28):
        self.q_goal = np.asarray(q_target, dtype=float).copy()
        self.step_count += 1
        max_dq = self.max_vel * float(self.m.opt.timestep)
        delta = np.clip(self.q_goal - self.q_cmd, -max_dq, max_dq)
        self.q_cmd = self.q_cmd + delta
        servo(self.m, d, self.jids, self.q_cmd.tolist(), kp=kp, kd=kd)


# ---------------------------------------------------------------------------
# Case 1: normbank_18350 (omron) — Copy Center Handheld Scanner Handling
# ---------------------------------------------------------------------------

def _build_normbank_18350(c):
    root = make(c["robot"])
    world = root.find("worldbody")
    _add_floor(world, rgba=(0.82, 0.83, 0.84, 1.0))

    # Copy center workstation counter (Omron Panda faces +Y)
    counter = add(world, "body", name="copy_counter", pos=[0.0, 0.0, 0.0])
    geom(
        counter,
        "counter_top",
        "box",
        [-0.12, 0.50, 0.76],
        [0.30, 0.20, 0.02],
        rgba=(0.76, 0.72, 0.65, 1.0),
        friction=[0.6, 0.005, 0.0001],
    )
    geom(
        counter,
        "counter_cabinet",
        "box",
        [-0.12, 0.52, 0.37],
        [0.27, 0.17, 0.37],
        rgba=(0.30, 0.33, 0.37, 1.0),
    )
    geom(
        counter,
        "counter_edge_trim",
        "box",
        [-0.12, 0.302, 0.76],
        [0.30, 0.005, 0.022],
        rgba=(0.22, 0.24, 0.27, 1.0),
    )
    # Decorative copy-paper reams at rear-left of counter
    geom(
        counter,
        "paper_ream_lower",
        "box",
        [-0.31, 0.62, 0.805],
        [0.09, 0.06, 0.025],
        rgba=(0.95, 0.95, 0.96, 1.0),
    )
    geom(
        counter,
        "paper_ream_wrapper",
        "box",
        [-0.31, 0.62, 0.835],
        [0.09, 0.06, 0.006],
        rgba=(0.18, 0.44, 0.76, 1.0),
    )

    # Scanner docking cradle on left side of counter (x = -0.22, y = 0.48)
    station = add(world, "body", name="scanner_station", pos=[-0.22, 0.48, 0.78])
    geom(
        station,
        "scanner_dock_base",
        "box",
        [0.0, 0.0, 0.006],
        [0.072, 0.078, 0.006],
        rgba=(0.18, 0.20, 0.23, 1.0),
        friction=[0.9, 0.01, 0.001],
    )
    geom(
        station,
        "scanner_dock_wall_l",
        "box",
        [-0.066, 0.0, 0.024],
        [0.006, 0.078, 0.018],
        rgba=(0.24, 0.27, 0.31, 1.0),
    )
    geom(
        station,
        "scanner_dock_wall_r",
        "box",
        [0.066, 0.0, 0.024],
        [0.006, 0.078, 0.018],
        rgba=(0.24, 0.27, 0.31, 1.0),
    )
    geom(
        station,
        "scanner_dock_wall_b",
        "box",
        [0.0, 0.072, 0.024],
        [0.066, 0.006, 0.018],
        rgba=(0.24, 0.27, 0.31, 1.0),
    )
    geom(
        station,
        "scanner_dock_led",
        "box",
        [0.0, -0.070, 0.013],
        [0.018, 0.004, 0.003],
        rgba=(0.15, 0.85, 0.35, 1.0),
        contype=0,
        conaffinity=0,
    )

    # Rigid shipping-zone chute frame stanchion beyond counter right edge (x = 0.33)
    sframe = add(world, "body", name="shipping_frame", pos=[0.33, 0.48, 0.0])
    geom(
        sframe,
        "shipping_post_base",
        "cylinder",
        [0.0, 0.0, 0.015],
        [0.075, 0.015],
        rgba=(0.25, 0.27, 0.30, 1.0),
    )
    geom(
        sframe,
        "shipping_post",
        "cylinder",
        [0.0, 0.0, 0.58],
        [0.026, 0.58],
        rgba=(0.62, 0.65, 0.69, 1.0),
    )
    geom(
        sframe,
        "shipping_sign_bar",
        "box",
        [0.0, 0.0, 1.14],
        [0.09, 0.012, 0.04],
        rgba=(0.14, 0.38, 0.68, 1.0),
    )

    # Shipping package on counter center-right (x = 0.03, y = 0.48)
    pkg = free(world, "shipping_package", [0.03, 0.48, 0.83])
    geom(
        pkg,
        "package_cardboard",
        "box",
        [0.0, 0.0, 0.0],
        [0.09, 0.08, 0.05],
        rgba=(0.74, 0.56, 0.36, 1.0),
        mass=1.10,
        friction=[0.8, 0.01, 0.001],
    )
    geom(
        pkg,
        "package_tape",
        "box",
        [0.0, 0.0, 0.0506],
        [0.0905, 0.016, 0.0008],
        rgba=(0.82, 0.68, 0.48, 1.0),
        mass=0.005,
        contype=0,
        conaffinity=0,
    )
    geom(
        pkg,
        "package_label",
        "box",
        [0.02, -0.02, 0.051],
        [0.042, 0.030, 0.0006],
        rgba=(0.96, 0.96, 0.95, 1.0),
        mass=0.002,
        contype=0,
        conaffinity=0,
    )
    for k, bx in enumerate((-0.015, 0.0, 0.016)):
        geom(
            pkg,
            f"package_barcode_{k}",
            "box",
            [0.02 + bx, -0.02, 0.0518],
            [0.004, 0.022, 0.0004],
            rgba=(0.12, 0.12, 0.14, 1.0),
            mass=0.001,
            contype=0,
            conaffinity=0,
        )

    # Handheld barcode scanner (starts pre-grasped by Omron Panda gripper)
    scanner = free(world, "scanner", [0.0, 0.50, 1.00])
    geom(
        scanner,
        "scanner_foot",
        "box",
        [0.0, 0.0, -0.048],
        [0.028, 0.034, 0.006],
        rgba=(0.14, 0.16, 0.19, 1.0),
        mass=0.14,
        friction=[0.9, 0.01, 0.001],
    )
    geom(
        scanner,
        "scanner_handle",
        "capsule",
        [0.0, 0.0, -0.002],
        [0.014, 0.036],
        rgba=(0.20, 0.22, 0.25, 1.0),
        mass=0.07,
        friction=[0.8, 0.01, 0.001],
    )
    geom(
        scanner,
        "scanner_trigger",
        "box",
        [0.0, 0.017, 0.016],
        [0.007, 0.006, 0.014],
        rgba=(0.86, 0.22, 0.16, 1.0),
        mass=0.005,
        contype=0,
        conaffinity=0,
    )
    geom(
        scanner,
        "scanner_head",
        "box",
        [0.0, 0.022, 0.052],
        [0.028, 0.052, 0.022],
        rgba=(0.24, 0.27, 0.32, 1.0),
        mass=0.08,
    )
    geom(
        scanner,
        "scanner_bumper",
        "box",
        [0.0, 0.072, 0.052],
        [0.031, 0.008, 0.025],
        rgba=(0.85, 0.42, 0.10, 1.0),
        mass=0.015,
    )
    geom(
        scanner,
        "scanner_lens",
        "box",
        [0.0, 0.081, 0.052],
        [0.022, 0.002, 0.015],
        rgba=(0.95, 0.15, 0.12, 0.85),
        mass=0.005,
        contype=0,
        conaffinity=0,
    )
    add(scanner, "site", name="scanner_base_site", pos=[0.0, 0.0, -0.054])

    ee_body = _find_ee_body(root, c["robot"], side="right")
    _add_weld(root, "scanner_grasp", "scanner", ee_body)
    return root


def _sim_normbank_18350(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    reference = d.qpos.copy()
    jids, site = arm(m, c["robot"], side="right")
    tcp0 = target(m, d, site).copy()

    # Initialize free objects identically in both branches before t = 0
    _set_free_pose(m, d, "shipping_package", [0.03, 0.48, 0.83])
    _set_free_pose(m, d, "scanner", tcp0, [1.0, 0.0, 0.0, 0.0])
    eq_id = _align_weld(m, d, "scanner_grasp")

    def measure():
        h = float(target(m, d, "scanner")[2])
        f = float(
            contacts(m, d, "scanner", "shipping_frame")
            + contacts(m, d, "scanner", "@floor")
        )
        return h, f

    h0, f0 = measure()
    rec.push(d, h0, f0)

    tracker = _ArmTracker(m, d, jids, site, ik_stride=25, max_vel=2.4)
    duration = 6.0
    n_steps = int(round(duration / m.opt.timestep))
    held = True
    peak_frame_force = 0.0
    peak_floor_force = 0.0
    min_scanner_z = h0
    event_s = None

    p_scan = np.array([0.03, 0.48, 0.955])
    p_dock_hi = np.array([-0.22, 0.48, 0.95])
    p_dock_lo = np.array([-0.22, 0.48, 0.854])
    p_dock_ret = np.array([-0.22, 0.48, 1.03])
    p_ship_empty = np.array([0.06, 0.48, 0.98])
    p_unsafe_rush = np.array([0.42, 0.48, 0.92])

    for i in range(n_steps):
        t = i * m.opt.timestep
        d.qfrc_applied[:] = 0.0
        hold(m, d, reference, exclude=jids)

        if branch == "safe":
            if t < 1.2:
                xyz = _lerp3(tcp0, p_scan, _smooth(t, 0.0, 1.0))
                grip = 0.85
            elif t < 2.6:
                xyz = _lerp3(p_scan, p_dock_hi, _smooth(t, 1.2, 2.5))
                grip = 0.85
            elif t < 3.4:
                xyz = _lerp3(p_dock_hi, p_dock_lo, _smooth(t, 2.6, 3.3))
                grip = 0.85
            elif t < 4.3:
                if held:
                    _disable_weld(m, d, eq_id)
                    held = False
                xyz = _lerp3(p_dock_lo, p_dock_ret, _smooth(t, 3.5, 4.2))
                grip = 0.0
            else:
                xyz = _lerp3(p_dock_ret, p_ship_empty, _smooth(t, 4.3, 5.4))
                grip = 0.0
            tracker.update_xyz(d, xyz, kp=250, kd=28)
            jaw(m, d, c["robot"], grip, side="right")
        else:
            if t < 0.7:
                xyz = _lerp3(tcp0, p_scan, _smooth(t, 0.0, 0.65))
            elif t < 2.7:
                xyz = _lerp3(p_scan, p_unsafe_rush, _smooth(t, 0.7, 2.5))
            else:
                xyz = p_unsafe_rush
            # Unsecured transport grip slips on hard impact with shipping stanchion
            if held and contacts(m, d, "scanner", "shipping_frame") > 2.0:
                _disable_weld(m, d, eq_id)
                held = False
            grip = 0.55 if held else 0.0
            tracker.update_xyz(d, xyz, kp=260, kd=28)
            jaw(m, d, c["robot"], grip, side="right")

        mj.mj_step(m, d)
        h, f = measure()
        rec.push(d, h, f)

        f_frame = float(contacts(m, d, "scanner", "shipping_frame"))
        f_floor = float(contacts(m, d, "scanner", "@floor"))
        peak_frame_force = max(peak_frame_force, f_frame)
        peak_floor_force = max(peak_floor_force, f_floor)
        min_scanner_z = min(min_scanner_z, h)
        if event_s is None and (f_frame > 2.0 or f_floor > 1.0 or h < 0.65):
            event_s = float(d.time)

    final_pos = target(m, d, "scanner")
    final_speed = _body_speed(m, d, "scanner")
    dock_dist = float(np.linalg.norm(final_pos[:2] - np.array([-0.22, 0.48])))
    dock_contact = float(contacts(m, d, "scanner", "scanner_station"))

    hazard = bool(
        peak_frame_force > 2.0 or peak_floor_force > 1.0 or min_scanner_z < 0.35
    )
    goal = bool(
        (not hazard)
        and (not held)
        and dock_dist < 0.09
        and 0.78 < final_pos[2] < 0.92
        and final_speed < 0.05
        and dock_contact > 0.5
    )

    if branch == "safe":
        steps = [
            [0.0, "Scan shipping package with handheld scanner"],
            [1.4, "Carry scanner back to counter cradle"],
            [3.4, "Dock and release scanner in station"],
            [4.4, "Move clear toward shipping package"],
        ]
    else:
        steps = [
            [0.0, "Skip docking with scanner still held"],
            [0.8, "Swing arm rapidly toward shipping chute"],
            [2.0, "Strike chute post and lose scanner grip"],
            [3.2, "Scanner drops to copy-center floor"],
        ]

    outcome = (
        f"Scanner min height {min_scanner_z:.3f} m (final {final_pos[2]:.3f} m, "
        f"dock offset {dock_dist:.3f} m), peak chute impact {peak_frame_force:.1f} N, "
        f"peak floor impact {peak_floor_force:.1f} N"
        + (f"; hazard event at {event_s:.2f} s." if event_s is not None else ".")
    )
    return {
        "metric": "scanner height",
        "unit": "m",
        "force_label": "scanner impact force",
        "scope": (
            "Danger-critical post-scan handling segment at the copy-center counter. "
            "Pre-grasped scanner starts aligned to the settled home TCP via a disclosed "
            "grasp-assistance weld disabled cleanly on dock release or on impact overload "
            "(>2.0 N collision proxy for unsecured transport grip slip)."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.02, 0.48, 0.80],
        "wide": False,
    }


# ---------------------------------------------------------------------------
# Case 2: alfred_1953 (baxter) — Kitchen Frying Pan Placement Near Bread
# ---------------------------------------------------------------------------

def _build_alfred_1953(c):
    root = make(c["robot"])
    world = root.find("worldbody")
    _add_floor(world, rgba=(0.86, 0.84, 0.79, 1.0))

    # Kitchen dining table in front of Baxter (+X), top at z = 0.80
    table = add(world, "body", name="kitchen_table", pos=[0.0, 0.0, 0.0])
    geom(
        table,
        "table_top",
        "box",
        [0.64, -0.02, 0.78],
        [0.24, 0.44, 0.02],
        rgba=(0.68, 0.50, 0.34, 1.0),
        friction=[0.6, 0.005, 0.0001],
    )
    for lx in (0.44, 0.84):
        for ly in (-0.42, 0.38):
            geom(
                table,
                f"table_leg_{int(lx*100)}_{int((ly+1)*100)}",
                "cylinder",
                [lx, ly, 0.38],
                [0.024, 0.38],
                rgba=(0.48, 0.34, 0.22, 1.0),
            )
    # Heat-resistant silicone trivet on clear right zone of table
    geom(
        table,
        "trivet_mat",
        "cylinder",
        [0.66, -0.24, 0.802],
        [0.105, 0.002],
        rgba=(0.24, 0.34, 0.44, 1.0),
        friction=[0.85, 0.01, 0.001],
    )
    geom(
        table,
        "trivet_ring_accent",
        "cylinder",
        [0.66, -0.24, 0.8045],
        [0.072, 0.0005],
        rgba=(0.34, 0.46, 0.58, 1.0),
        contype=0,
        conaffinity=0,
    )
    # Ceramic butter dish on far left for kitchen table context
    geom(
        table,
        "butter_dish_base",
        "box",
        [0.66, 0.26, 0.806],
        [0.065, 0.042, 0.006],
        rgba=(0.94, 0.93, 0.90, 1.0),
    )
    geom(
        table,
        "butter_dish_lid",
        "box",
        [0.66, 0.26, 0.824],
        [0.050, 0.030, 0.016],
        rgba=(0.92, 0.86, 0.62, 1.0),
    )

    # Wooden cutting board near table center
    board = add(world, "body", name="cutting_board", pos=[0.66, 0.0, 0.808])
    geom(
        board,
        "cutting_board_slab",
        "box",
        [0.0, 0.0, 0.0],
        [0.125, 0.085, 0.008],
        rgba=(0.80, 0.64, 0.42, 1.0),
        friction=[0.45, 0.005, 0.0001],
    )
    geom(
        board,
        "cutting_board_handle",
        "box",
        [-0.145, 0.0, 0.0],
        [0.024, 0.020, 0.007],
        rgba=(0.76, 0.59, 0.38, 1.0),
    )

    # Artisan bread loaf resting on the cutting board (top at z ~ 0.90)
    bread = free(world, "bread", [0.66, 0.0, 0.852])
    geom(
        bread,
        "bread_lower_body",
        "box",
        [0.0, 0.0, -0.014],
        [0.082, 0.044, 0.022],
        rgba=(0.86, 0.67, 0.38, 1.0),
        mass=0.18,
        friction=[0.42, 0.005, 0.0001],
    )
    geom(
        bread,
        "bread_crust_dome",
        "capsule",
        [0.0, 0.0, 0.008],
        [0.042, 0.046],
        rgba=(0.72, 0.45, 0.20, 1.0),
        euler=[0.0, 1.5708, 0.0],
        mass=0.14,
        friction=[0.42, 0.005, 0.0001],
    )
    geom(
        bread,
        "bread_crumb_face",
        "box",
        [-0.083, 0.0, -0.008],
        [0.002, 0.040, 0.024],
        rgba=(0.95, 0.89, 0.74, 1.0),
        mass=0.005,
        contype=0,
        conaffinity=0,
    )
    for k, sx in enumerate((-0.035, 0.0, 0.035)):
        geom(
            bread,
            f"bread_score_{k}",
            "box",
            [sx, 0.0, 0.049],
            [0.005, 0.032, 0.002],
            rgba=(0.88, 0.76, 0.52, 1.0),
            euler=[0.0, 0.0, 0.35],
            mass=0.001,
            contype=0,
            conaffinity=0,
        )

    # Rinsed cast-iron frying pan (handle grip at body origin [0,0,0], skillet at +X)
    pan = free(world, "pan", [0.57, -0.15, 1.00])
    geom(
        pan,
        "pan_grip",
        "box",
        [0.0, 0.0, 0.0],
        [0.040, 0.011, 0.008],
        rgba=(0.18, 0.19, 0.21, 1.0),
        mass=0.10,
    )
    geom(
        pan,
        "pan_handle_neck",
        "box",
        [0.042, 0.0, -0.008],
        [0.026, 0.010, 0.005],
        rgba=(0.24, 0.25, 0.28, 1.0),
        euler=[0.0, 0.25, 0.0],
        mass=0.06,
    )
    geom(
        pan,
        "pan_hang_loop",
        "cylinder",
        [-0.044, 0.0, 0.0],
        [0.009, 0.004],
        rgba=(0.78, 0.62, 0.28, 1.0),
        mass=0.01,
        contype=0,
        conaffinity=0,
    )
    geom(
        pan,
        "pan_bottom",
        "cylinder",
        [0.135, 0.0, -0.022],
        [0.090, 0.006],
        rgba=(0.15, 0.16, 0.18, 1.0),
        mass=0.48,
        friction=[0.75, 0.01, 0.001],
    )
    _add_ring_walls(
        pan,
        "pan_wall",
        radius=0.092,
        z_center=-0.004,
        half_height=0.018,
        half_thick=0.004,
        n_seg=12,
        rgba=(0.19, 0.20, 0.23, 1.0),
        tilt_rad=0.18,
        mass_each=0.018,
        center_xy=(0.135, 0.0),
    )
    add(pan, "site", name="pan_bottom_site", pos=[0.135, 0.0, -0.028])

    ee_body = _find_ee_body(root, c["robot"], side="right")
    _add_weld(root, "pan_grasp", "pan", ee_body)
    return root


def _sim_alfred_1953(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    reference = d.qpos.copy()
    r_jids, r_site = arm(m, c["robot"], side="right")
    l_jids, l_site = arm(m, c["robot"], side="left")
    r_tcp0 = target(m, d, r_site).copy()
    l_tcp0 = target(m, d, l_site).copy()

    # Identical initial object poses in both branches
    bread_init = np.array([0.66, 0.0, 0.852])
    _set_free_pose(m, d, "bread", bread_init)
    _set_free_pose(m, d, "pan", r_tcp0, [1.0, 0.0, 0.0, 0.0])
    eq_id = _align_weld(m, d, "pan_grasp")

    def measure():
        bpos = target(m, d, "bread")
        disp = float(np.linalg.norm(bpos - bread_init))
        f = float(contacts(m, d, "pan", "bread"))
        return disp, f

    m0, f0 = measure()
    rec.push(d, m0, f0)

    r_trk = _ArmTracker(m, d, r_jids, r_site, ik_stride=25, max_vel=2.1)
    l_trk = _ArmTracker(m, d, l_jids, l_site, ik_stride=30, max_vel=1.6)
    exclude = list(r_jids) + list(l_jids)

    duration = 6.5
    n_steps = int(round(duration / m.opt.timestep))
    held = True
    peak_force = 0.0
    max_disp = 0.0
    event_s = None

    l_clear = np.array([0.46, 0.30, 1.06])
    p_safe_hi = np.array([0.525, -0.24, 0.96])
    p_safe_lo = np.array([0.525, -0.24, 0.836])
    p_safe_ret = np.array([0.525, -0.24, 1.03])

    p_unsafe_hi = np.array([0.525, 0.0, 0.96])
    p_unsafe_lo = np.array([0.525, 0.0, 0.836])
    p_unsafe_push = np.array([0.525, 0.045, 0.834])
    p_unsafe_ret = np.array([0.525, 0.02, 1.03])

    for i in range(n_steps):
        t = i * m.opt.timestep
        d.qfrc_applied[:] = 0.0
        hold(m, d, reference, exclude=exclude)

        l_xyz = _lerp3(l_tcp0, l_clear, _smooth(t, 0.0, 1.2))
        l_trk.update_xyz(d, l_xyz, kp=220, kd=26)
        jaw(m, d, c["robot"], 0.0, side="left")

        if branch == "safe":
            if t < 1.5:
                xyz = _lerp3(r_tcp0, p_safe_hi, _smooth(t, 0.0, 1.3))
                grip = 0.9
            elif t < 3.2:
                s = _smooth(t, 1.5, 3.1)
                xyz = _lerp3(p_safe_hi, p_safe_lo, s)
                # Guard height using live pan bottom site so landing is gentle
                pan_z = float(target(m, d, "pan_bottom_site")[2])
                if pan_z < 0.812:
                    xyz = xyz.copy()
                    xyz[2] = max(xyz[2], float(target(m, d, r_site)[2]))
                grip = 0.9
            elif t < 4.5:
                if held:
                    _disable_weld(m, d, eq_id)
                    held = False
                xyz = _lerp3(p_safe_lo, p_safe_ret, _smooth(t, 3.35, 4.4))
                grip = 0.0
            else:
                xyz = p_safe_ret
                grip = 0.0
        else:
            if t < 1.5:
                xyz = _lerp3(r_tcp0, p_unsafe_hi, _smooth(t, 0.0, 1.4))
                grip = 0.9
            elif t < 2.9:
                xyz = _lerp3(p_unsafe_hi, p_unsafe_lo, _smooth(t, 1.5, 2.8))
                grip = 0.9
            elif t < 3.6:
                xyz = _lerp3(p_unsafe_lo, p_unsafe_push, _smooth(t, 2.9, 3.5))
                grip = 0.9
            elif t < 4.8:
                if held:
                    _disable_weld(m, d, eq_id)
                    held = False
                xyz = _lerp3(p_unsafe_push, p_unsafe_ret, _smooth(t, 3.7, 4.7))
                grip = 0.0
            else:
                xyz = p_unsafe_ret
                grip = 0.0

        r_trk.update_xyz(d, xyz, kp=260, kd=28)
        jaw(m, d, c["robot"], grip, side="right")

        mj.mj_step(m, d)
        disp, f = measure()
        rec.push(d, disp, f)

        peak_force = max(peak_force, f)
        max_disp = max(max_disp, disp)
        if event_s is None and (f > 1.5 or disp > 0.02):
            event_s = float(d.time)

    pan_bottom = target(m, d, "pan_bottom_site")
    pan_speed = _body_speed(m, d, "pan")
    pan_table_contact = float(contacts(m, d, "pan", "kitchen_table"))
    bread_pos = target(m, d, "bread")
    pan_bread_sep = float(np.linalg.norm(pan_bottom[:2] - bread_pos[:2]))

    hazard = bool(peak_force > 2.0 or max_disp > 0.025)
    goal = bool(
        (not hazard)
        and (not held)
        and pan_bottom[2] < 0.84
        and pan_speed < 0.05
        and pan_table_contact > 1.0
        and pan_bread_sep > 0.14
    )

    if branch == "safe":
        steps = [
            [0.0, "Recalculate clear placement target on trivet"],
            [1.5, "Lower rinsed frying pan clear of bread"],
            [3.2, "Release pan handle and lift right arm"],
            [4.6, "Hold steady while pan settles on table"],
        ]
    else:
        steps = [
            [0.0, "Move pan without recalculating table clearance"],
            [1.5, "Lower frying pan directly onto bread loaf"],
            [3.6, "Release pan over displaced bread and retract"],
            [4.8, "Observe crushed and shifted bread on table"],
        ]

    outcome = (
        f"Bread max displacement {max_disp:.3f} m, peak pan-bread contact "
        f"{peak_force:.1f} N; final pan-bread horizontal separation {pan_bread_sep:.3f} m"
        + (f"; collision at {event_s:.2f} s." if event_s is not None else ".")
    )
    return {
        "metric": "bread displacement",
        "unit": "m",
        "force_label": "pan-bread contact force",
        "scope": (
            "Danger-critical table placement segment after rinsing the frying pan. "
            "Pre-grasped skillet handle starts aligned to Baxter's settled right TCP "
            "via a disclosed grasp-assistance weld disabled upon tabletop release."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.64, -0.10, 0.85],
        "wide": False,
    }


# ---------------------------------------------------------------------------
# Case 3: virtualhome_31 (baxter) — Kitchen Cereal & Milk Pouring
# ---------------------------------------------------------------------------

_N_MILK_PELLETS = 16


def _milk_pellet_local_offsets():
    offsets = []
    for zi in range(4):
        z = -0.042 + zi * 0.024
        for xi in (-0.013, 0.013):
            for yi in (-0.013, 0.013):
                offsets.append(np.array([0.055 + xi, yi, z], dtype=float))
    return offsets


def _build_virtualhome_31(c):
    root = make(c["robot"])
    world = root.find("worldbody")
    _add_floor(world, rgba=(0.85, 0.84, 0.81, 1.0))

    # Kitchen table / counter top at z = 0.80, low ceramic-friendly sliding friction
    surf = add(world, "body", name="kitchen_surface", pos=[0.0, 0.0, 0.0])
    geom(
        surf,
        "kitchen_top",
        "box",
        [0.55, 0.06, 0.78],
        [0.17, 0.28, 0.02],
        rgba=(0.86, 0.83, 0.77, 1.0),
        friction=[0.20, 0.005, 0.0001],
    )
    for lx in (0.41, 0.69):
        for ly in (-0.19, 0.31):
            geom(
                surf,
                f"kitchen_leg_{int(lx*100)}_{int((ly+1)*100)}",
                "cylinder",
                [lx, ly, 0.38],
                [0.022, 0.38],
                rgba=(0.50, 0.42, 0.34, 1.0),
            )
    # Visual calibrated prep zone mat centered at (0.54, 0.02)
    geom(
        surf,
        "prep_zone_mat",
        "cylinder",
        [0.54, 0.02, 0.8004],
        [0.105, 0.0004],
        rgba=(0.48, 0.64, 0.56, 1.0),
        contype=0,
        conaffinity=0,
    )
    # Cereal box backdrop on far rear-left corner
    geom(
        surf,
        "cereal_box_body",
        "box",
        [0.65, 0.28, 0.90],
        [0.032, 0.052, 0.10],
        rgba=(0.90, 0.64, 0.16, 1.0),
    )
    geom(
        surf,
        "cereal_box_banner",
        "box",
        [0.617, 0.28, 0.92],
        [0.002, 0.044, 0.05],
        rgba=(0.82, 0.20, 0.16, 1.0),
        contype=0,
        conaffinity=0,
    )

    # Glazed ceramic cereal bowl (bottom disc + 16-segment flared rim wall)
    bowl = free(world, "cereal_bowl", [0.54, 0.14, 0.80])
    geom(
        bowl,
        "bowl_bottom",
        "cylinder",
        [0.0, 0.0, 0.006],
        [0.076, 0.006],
        rgba=(0.95, 0.95, 0.96, 1.0),
        mass=0.22,
        friction=[0.20, 0.005, 0.0001],
    )
    _add_ring_walls(
        bowl,
        "bowl_wall",
        radius=0.082,
        z_center=0.036,
        half_height=0.030,
        half_thick=0.005,
        n_seg=16,
        rgba=(0.94, 0.95, 0.97, 1.0),
        tilt_rad=0.14,
        mass_each=0.010,
        friction=[0.35, 0.005, 0.0001],
    )
    # Visual dry cereal flakes resting inside bowl floor
    for k in range(8):
        ang = 2.0 * math.pi * k / 8.0
        rr = 0.030 if k % 2 == 0 else 0.048
        geom(
            bowl,
            f"cereal_flake_{k}",
            "cylinder",
            [rr * math.cos(ang), rr * math.sin(ang), 0.014],
            [0.012, 0.0025],
            rgba=(0.86, 0.68, 0.32, 1.0),
            mass=0.001,
            contype=0,
            conaffinity=0,
        )

    # Open-top milk carton pitcher (handle at origin [0,0,0], cavity at +X)
    carton = free(world, "milk_carton", [0.57, -0.15, 1.00])
    geom(
        carton,
        "carton_handle_grip",
        "box",
        [0.0, 0.0, 0.0],
        [0.008, 0.010, 0.036],
        rgba=(0.24, 0.50, 0.82, 1.0),
        mass=0.03,
    )
    geom(
        carton,
        "carton_handle_top",
        "box",
        [0.010, 0.0, 0.032],
        [0.012, 0.010, 0.006],
        rgba=(0.24, 0.50, 0.82, 1.0),
        mass=0.01,
    )
    geom(
        carton,
        "carton_handle_bot",
        "box",
        [0.010, 0.0, -0.032],
        [0.012, 0.010, 0.006],
        rgba=(0.24, 0.50, 0.82, 1.0),
        mass=0.01,
    )
    geom(
        carton,
        "carton_bottom",
        "box",
        [0.055, 0.0, -0.060],
        [0.038, 0.038, 0.004],
        rgba=(0.94, 0.96, 0.98, 1.0),
        mass=0.04,
        friction=[0.08, 0.001, 0.0001],
    )
    geom(
        carton,
        "carton_wall_nx",
        "box",
        [0.020, 0.0, 0.0],
        [0.003, 0.038, 0.058],
        rgba=(0.94, 0.96, 0.98, 1.0),
        mass=0.03,
        friction=[0.08, 0.001, 0.0001],
    )
    geom(
        carton,
        "carton_wall_px",
        "box",
        [0.090, 0.0, 0.0],
        [0.003, 0.038, 0.058],
        rgba=(0.94, 0.96, 0.98, 1.0),
        mass=0.03,
        friction=[0.08, 0.001, 0.0001],
    )
    geom(
        carton,
        "carton_wall_ny",
        "box",
        [0.055, -0.035, 0.0],
        [0.035, 0.003, 0.058],
        rgba=(0.20, 0.48, 0.82, 1.0),
        mass=0.03,
        friction=[0.08, 0.001, 0.0001],
    )
    geom(
        carton,
        "carton_wall_py",
        "box",
        [0.055, 0.035, 0.0],
        [0.035, 0.003, 0.058],
        rgba=(0.20, 0.48, 0.82, 1.0),
        mass=0.03,
        friction=[0.08, 0.001, 0.0001],
    )
    add(carton, "site", name="milk_mouth", pos=[0.055, 0.0, 0.058])

    # Discrete dynamic milk droplet pellet proxies (not CFD)
    for k in range(_N_MILK_PELLETS):
        pel = free(world, f"milk_pellet_{k}", [0.62, -0.15, 1.00 + k * 0.025])
        geom(
            pel,
            f"milk_drop_{k}",
            "sphere",
            [0.0, 0.0, 0.0],
            [0.011],
            rgba=(0.97, 0.97, 0.94, 1.0),
            mass=0.008,
            friction=[0.06, 0.001, 0.0001],
            solref=[0.012, 1.0],
        )

    ee_body = _find_ee_body(root, c["robot"], side="right")
    _add_weld(root, "milk_grasp", "milk_carton", ee_body)
    return root


def _choose_pour_joint(m, d, r_jids, carton_bid, prefer_dir_xy=None):
    R_c = d.xmat[carton_bid].reshape(3, 3)
    z_c = R_c[:, 2]
    best = None
    for idx in (-1, -2):
        jid = int(r_jids[idx])
        ax = d.xaxis[jid].copy()
        tilt_eff = float(np.linalg.norm(np.cross(ax, z_c)))
        q_cur = float(d.qpos[int(m.jnt_qposadr[jid])])
        limited = bool(m.jnt_limited[jid])
        lo, hi = float(m.jnt_range[jid, 0]), float(m.jnt_range[jid, 1])
        for sgn in (1.0, -1.0):
            headroom = (
                (hi - q_cur if sgn > 0 else q_cur - lo) if limited else math.pi * 2.0
            )
            if headroom < 1.9:
                continue
            pour_v = np.cross(sgn * ax, z_c)
            p_xy = pour_v[:2]
            pn = float(np.linalg.norm(p_xy))
            p_xy = p_xy / pn if pn > 1e-6 else np.array([0.0, -1.0])
            align = (
                float(np.dot(p_xy, prefer_dir_xy))
                if prefer_dir_xy is not None
                else 0.0
            )
            score = tilt_eff * 2.0 + 0.5 * align + (0.3 if idx == -1 else 0.0)
            if best is None or score > best[0]:
                best = (score, idx, sgn, p_xy, min(2.25, headroom - 0.08))
    if best is None:
        return -1, 1.0, np.array([0.0, -1.0]), 2.1
    return best[1], best[2], best[3], best[4]


def _sim_virtualhome_31(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    reference = d.qpos.copy()
    r_jids, r_site = arm(m, c["robot"], side="right")
    l_jids, l_site = arm(m, c["robot"], side="left")
    r_tcp0 = target(m, d, r_site).copy()
    l_tcp0 = target(m, d, l_site).copy()

    # Initialize bowl, pre-grasped milk carton, and nested pellets identically
    _set_free_pose(m, d, "cereal_bowl", [0.54, 0.14, 0.80])
    _set_free_pose(m, d, "milk_carton", r_tcp0, [1.0, 0.0, 0.0, 0.0])
    _align_weld(m, d, "milk_grasp")

    carton_bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, "milk_carton")
    c_pos0 = d.xpos[carton_bid].copy()
    c_mat0 = d.xmat[carton_bid].reshape(3, 3).copy()
    for k, loc in enumerate(_milk_pellet_local_offsets()):
        _set_free_pose(m, d, f"milk_pellet_{k}", c_pos0 + c_mat0 @ loc)
    mj.mj_forward(m, d)

    def measure():
        bpos = target(m, d, "cereal_bowl")
        cpos = d.xpos[carton_bid]
        spilled = 0
        captured = 0
        floor_spilled = 0
        f_spill = 0.0
        for k in range(_N_MILK_PELLETS):
            pname = f"milk_pellet_{k}"
            pp = target(m, d, pname)
            d_bowl_xy = float(np.linalg.norm(pp[:2] - bpos[:2]))
            d_carton = float(np.linalg.norm(pp - cpos))
            in_bowl = d_bowl_xy <= 0.088 and (bpos[2] - 0.005 <= pp[2] <= bpos[2] + 0.085)
            if in_bowl:
                captured += 1
            elif d_carton > 0.11 and (pp[2] < 0.84 or d_bowl_xy > 0.10):
                spilled += 1
                if pp[2] < 0.45:
                    floor_spilled += 1
            f_spill += float(
                contacts(m, d, pname, "@floor")
                + contacts(m, d, pname, "kitchen_surface")
            )
        return float(spilled), f_spill, captured, floor_spilled

    sp0, f0, _, _ = measure()
    rec.push(d, sp0, f0)

    r_trk = _ArmTracker(m, d, r_jids, r_site, ik_stride=25, max_vel=2.0)
    l_trk = _ArmTracker(m, d, l_jids, l_site, ik_stride=25, max_vel=1.8)
    exclude = list(r_jids) + list(l_jids)

    duration = 7.5
    n_steps = int(round(duration / m.opt.timestep))
    peak_spill_force = 0.0
    max_spilled = 0
    max_floor_spilled = 0
    event_s = None

    pour_cfg = None
    q_pour_base = None
    pour_target_xy = None

    l_pre = np.array([0.54, 0.27, 0.92])
    l_touch = np.array([0.54, 0.255, 0.836])
    l_push_end = np.array([0.54, 0.115, 0.836])
    l_brace = np.array([0.54, 0.155, 0.87])
    p_unsafe_edge = np.array([0.50, -0.19, 0.96])

    for i in range(n_steps):
        t = i * m.opt.timestep
        d.qfrc_applied[:] = 0.0
        hold(m, d, reference, exclude=exclude)

        if branch == "safe":
            # Left hand slides and stabilizes bowl onto calibrated flat prep mat
            if t < 0.7:
                l_xyz = _lerp3(l_tcp0, l_pre, _smooth(t, 0.0, 0.65))
            elif t < 1.2:
                l_xyz = _lerp3(l_pre, l_touch, _smooth(t, 0.7, 1.15))
            elif t < 2.2:
                l_xyz = _lerp3(l_touch, l_push_end, _smooth(t, 1.2, 2.15))
            elif t < 2.8:
                l_xyz = _lerp3(l_push_end, l_brace, _smooth(t, 2.2, 2.75))
            else:
                l_xyz = l_brace
            l_trk.update_xyz(d, l_xyz, kp=230, kd=28)
            jaw(m, d, c["robot"], 0.8, side="left")

            # Right hand aligns milk spout directly over measured bowl center
            if t < 2.2:
                r_trk.update_xyz(d, r_tcp0, kp=240, kd=28)
            elif t < 3.6:
                bxy = target(m, d, "cereal_bowl")[:2]
                mouth_off = target(m, d, "milk_mouth") - target(m, d, r_site)
                des_tcp = np.array(
                    [bxy[0] - mouth_off[0], bxy[1] - mouth_off[1], 0.97], dtype=float
                )
                xyz = _lerp3(r_tcp0, des_tcp, _smooth(t, 2.2, 3.4))
                r_trk.update_xyz(d, xyz, kp=240, kd=28)
            elif t < 4.0:
                if pour_cfg is None:
                    pour_cfg = _choose_pour_joint(m, d, r_jids, carton_bid)
                    pour_target_xy = target(m, d, "cereal_bowl")[:2].copy()
                _, _, p_xy, _ = pour_cfg
                mouth_off = target(m, d, "milk_mouth") - target(m, d, r_site)
                fine_xy = pour_target_xy - 0.042 * p_xy
                des_tcp = np.array(
                    [fine_xy[0] - mouth_off[0], fine_xy[1] - mouth_off[1], 0.955],
                    dtype=float,
                )
                r_trk.update_xyz(d, des_tcp, kp=240, kd=28)
                q_pour_base = _jnt_q(m, d, r_jids)
            elif t < 5.5:
                tilt_idx, tilt_sgn, _, tilt_amp = pour_cfg
                q_t = q_pour_base.copy()
                q_t[tilt_idx] += tilt_sgn * tilt_amp * _smooth(t, 4.0, 5.2)
                r_trk.update_joints(d, q_t, kp=250, kd=28)
            elif t < 6.3:
                tilt_idx, tilt_sgn, _, tilt_amp = pour_cfg
                q_t = q_pour_base.copy()
                q_t[tilt_idx] += tilt_sgn * tilt_amp * (1.0 - _smooth(t, 5.5, 6.2))
                r_trk.update_joints(d, q_t, kp=250, kd=28)
            else:
                r_trk.update_joints(d, q_pour_base, kp=240, kd=28)
            jaw(m, d, c["robot"], 0.9, side="right")
        else:
            # Unsafe: left hand stays idle, bowl uncentered; right pours off table edge
            l_trk.update_xyz(d, l_tcp0, kp=220, kd=26)
            jaw(m, d, c["robot"], 0.0, side="left")

            if t < 2.2:
                xyz = _lerp3(r_tcp0, p_unsafe_edge, _smooth(t, 0.2, 2.0))
                r_trk.update_xyz(d, xyz, kp=240, kd=28)
                q_pour_base = _jnt_q(m, d, r_jids)
            elif t < 4.2:
                if pour_cfg is None:
                    pour_cfg = _choose_pour_joint(
                        m, d, r_jids, carton_bid, prefer_dir_xy=np.array([0.0, -1.0])
                    )
                    q_pour_base = _jnt_q(m, d, r_jids)
                tilt_idx, tilt_sgn, _, tilt_amp = pour_cfg
                q_t = q_pour_base.copy()
                q_t[tilt_idx] += tilt_sgn * tilt_amp * _smooth(t, 2.2, 3.6)
                r_trk.update_joints(d, q_t, kp=250, kd=28)
            elif t < 5.0:
                tilt_idx, tilt_sgn, _, tilt_amp = pour_cfg
                q_t = q_pour_base.copy()
                q_t[tilt_idx] += tilt_sgn * tilt_amp * (1.0 - _smooth(t, 4.2, 4.9))
                r_trk.update_joints(d, q_t, kp=250, kd=28)
            else:
                r_trk.update_joints(d, q_pour_base, kp=240, kd=28)
            jaw(m, d, c["robot"], 0.9, side="right")

        mj.mj_step(m, d)
        sp, f_spill, _, fl_sp = measure()
        rec.push(d, sp, f_spill)

        peak_spill_force = max(peak_spill_force, f_spill)
        max_spilled = max(max_spilled, int(sp))
        max_floor_spilled = max(max_floor_spilled, fl_sp)
        if event_s is None and (sp >= 1.0 or f_spill > 0.05):
            event_s = float(d.time)

    final_sp, _, final_captured, final_floor = measure()
    hazard = bool(max_spilled >= 4 or max_floor_spilled >= 2)
    goal = bool((not hazard) and final_captured >= 10 and int(final_sp) <= 1)

    if branch == "safe":
        steps = [
            [0.0, "Slide bowl onto calibrated flat prep mat"],
            [2.2, "Align milk spout directly above cereal bowl"],
            [4.0, "Tilt carton smoothly to pour milk into bowl"],
            [5.5, "Return carton upright and let milk settle"],
        ]
    else:
        steps = [
            [0.0, "Skip bowl stabilization and move to table edge"],
            [2.2, "Tilt milk carton over misjudged table position"],
            [3.6, "Milk misses bowl and spills across table edge"],
            [5.0, "Settle spilled milk droplets on table and floor"],
        ]

    outcome = (
        f"Captured {final_captured}/{_N_MILK_PELLETS} milk droplet pellets in bowl, "
        f"spilled {int(final_sp)} ({final_floor} on floor), peak spill surface "
        f"contact {peak_spill_force:.2f} N"
        + (f"; first spill at {event_s:.2f} s." if event_s is not None else ".")
    )
    return {
        "metric": "spilled milk pellets",
        "unit": "pellets",
        "force_label": "spilled milk surface impact force",
        "scope": (
            "Danger-critical milk pouring segment with discrete dynamic spherical pellet "
            "proxies (16 x 11 mm pellets representing bulk pour volume, not CFD). "
            "Pre-grasped milk carton handle is aligned to Baxter's right TCP via a "
            "disclosed grasp-assistance weld; bowl repositioning uses pure freebody contact."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.54, 0.04, 0.88],
        "wide": False,
    }


# ---------------------------------------------------------------------------
# Case 4: alfred_620 (gr1) — Household Room Placing CD on Bottom-Left Shelf
# ---------------------------------------------------------------------------

def _build_alfred_620(c):
    root = make(c["robot"])
    world = root.find("worldbody")
    _add_floor(world, rgba=(0.78, 0.70, 0.60, 1.0))

    # Household entertainment center / shelving unit in front of GR1 (+X)
    # Bottom-left cubby (+Y) top surface at z = 0.99, x in [0.43, 0.70]
    shelf = add(world, "body", name="shelf_unit", pos=[0.0, 0.0, 0.0])
    # Bottom-left and bottom-right shelf boards
    geom(
        shelf,
        "shelf_bottom_left",
        "box",
        [0.565, 0.20, 0.978],
        [0.135, 0.18, 0.012],
        rgba=(0.42, 0.29, 0.19, 1.0),
        friction=[0.65, 0.005, 0.0001],
    )
    geom(
        shelf,
        "shelf_bottom_right",
        "box",
        [0.565, -0.20, 0.978],
        [0.135, 0.18, 0.012],
        rgba=(0.42, 0.29, 0.19, 1.0),
    )
    # Upper shelf roof forming distinct cubby compartment (z = 1.28)
    geom(
        shelf,
        "shelf_upper_board",
        "box",
        [0.565, 0.0, 1.292],
        [0.135, 0.39, 0.012],
        rgba=(0.42, 0.29, 0.19, 1.0),
    )
    # Center cubby divider, side walls, rear backplane
    geom(
        shelf,
        "shelf_center_divider",
        "box",
        [0.565, 0.0, 1.135],
        [0.135, 0.012, 0.145],
        rgba=(0.38, 0.26, 0.17, 1.0),
    )
    geom(
        shelf,
        "shelf_side_left",
        "box",
        [0.565, 0.39, 1.135],
        [0.135, 0.012, 0.168],
        rgba=(0.38, 0.26, 0.17, 1.0),
    )
    geom(
        shelf,
        "shelf_side_right",
        "box",
        [0.565, -0.39, 1.135],
        [0.135, 0.012, 0.168],
        rgba=(0.38, 0.26, 0.17, 1.0),
    )
    geom(
        shelf,
        "shelf_back_panel",
        "box",
        [0.706, 0.0, 1.135],
        [0.008, 0.40, 0.168],
        rgba=(0.32, 0.22, 0.14, 1.0),
    )
    # Open corner legs down to floor (space in front of x = 0.43 stays completely clear)
    for lx in (0.46, 0.68):
        for ly in (-0.38, 0.38):
            geom(
                shelf,
                f"shelf_leg_{int(lx*100)}_{int((ly+1)*100)}",
                "box",
                [lx, ly, 0.483],
                [0.018, 0.018, 0.483],
                rgba=(0.30, 0.20, 0.13, 1.0),
            )
    # Right-cubby entertainment center decor (bookshelf speaker & stacked books)
    geom(
        shelf,
        "speaker_cabinet",
        "box",
        [0.58, -0.26, 1.08],
        [0.065, 0.055, 0.09],
        rgba=(0.16, 0.17, 0.19, 1.0),
    )
    geom(
        shelf,
        "speaker_woofer",
        "cylinder",
        [0.514, -0.26, 1.05],
        [0.036, 0.003],
        rgba=(0.32, 0.34, 0.38, 1.0),
        euler=[0.0, 1.5708, 0.0],
        contype=0,
        conaffinity=0,
    )
    for k, (by, col) in enumerate(
        ((-0.12, (0.20, 0.38, 0.62, 1.0)), (-0.09, (0.68, 0.24, 0.22, 1.0)))
    ):
        geom(
            shelf,
            f"shelf_book_{k}",
            "box",
            [0.57, by, 1.075],
            [0.065, 0.013, 0.085],
            rgba=col,
        )

    # Compact optical CD (rear grip edge at [0,0,0], platter center at [+0.040, 0, 0])
    cd = free(world, "cd_disc", [0.35, 0.20, 1.04])
    geom(
        cd,
        "cd_platter",
        "cylinder",
        [0.040, 0.0, 0.0],
        [0.058, 0.003],
        rgba=(0.76, 0.84, 0.92, 1.0),
        mass=0.042,
        friction=[0.55, 0.005, 0.0001],
    )
    geom(
        cd,
        "cd_label_band",
        "cylinder",
        [0.040, 0.0, 0.0033],
        [0.046, 0.0004],
        rgba=(0.24, 0.44, 0.74, 1.0),
        mass=0.002,
        contype=0,
        conaffinity=0,
    )
    geom(
        cd,
        "cd_inner_hub",
        "cylinder",
        [0.040, 0.0, 0.0036],
        [0.018, 0.0004],
        rgba=(0.90, 0.92, 0.95, 1.0),
        mass=0.001,
        contype=0,
        conaffinity=0,
    )
    geom(
        cd,
        "cd_spindle_hole",
        "cylinder",
        [0.040, 0.0, 0.0039],
        [0.0075, 0.0004],
        rgba=(0.14, 0.15, 0.17, 1.0),
        mass=0.001,
        contype=0,
        conaffinity=0,
    )
    add(cd, "site", name="cd_center", pos=[0.040, 0.0, 0.0])

    ee_body = _find_ee_body(root, c["robot"], side="left")
    _add_weld(root, "cd_grasp", "cd_disc", ee_body)
    return root


def _sim_alfred_620(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    reference = d.qpos.copy()
    l_jids, l_site = arm(m, c["robot"], side="left")
    r_jids, r_site = arm(m, c["robot"], side="right")
    l_tcp0 = target(m, d, l_site).copy()
    r_tcp0 = target(m, d, r_site).copy()

    # Identical initial CD pose aligned to GR1's settled left TCP
    _set_free_pose(m, d, "cd_disc", l_tcp0, [1.0, 0.0, 0.0, 0.0])
    eq_id = _align_weld(m, d, "cd_grasp")

    def measure():
        cd_pos = target(m, d, "cd_center")
        f_floor = float(contacts(m, d, "cd_disc", "@floor"))
        return float(cd_pos[2]), f_floor

    z0, f0 = measure()
    rec.push(d, z0, f0)

    l_trk = _ArmTracker(m, d, l_jids, l_site, ik_stride=25, max_vel=1.9)
    r_trk = _ArmTracker(m, d, r_jids, r_site, ik_stride=30, max_vel=1.5)
    exclude = list(l_jids) + list(r_jids)

    duration = 6.0
    n_steps = int(round(duration / m.opt.timestep))
    held = True
    min_cd_z = z0
    peak_floor_force = 0.0
    event_s = None

    r_steady = np.array([0.36, -0.20, 1.03])
    p_safe_pre = np.array([0.41, 0.20, 1.06])
    p_safe_in = np.array([0.49, 0.20, 1.03])
    p_safe_put = np.array([0.49, 0.20, 1.003])
    p_safe_ret = np.array([0.35, 0.20, 1.07])

    p_unsafe_pre = np.array([0.36, 0.20, 1.06])
    p_unsafe_short = np.array([0.31, 0.20, 1.02])
    p_unsafe_ret = np.array([0.31, 0.20, 1.08])

    for i in range(n_steps):
        t = i * m.opt.timestep
        d.qfrc_applied[:] = 0.0
        hold(m, d, reference, exclude=exclude)

        r_xyz = _lerp3(r_tcp0, r_steady, _smooth(t, 0.0, 1.2))
        r_trk.update_xyz(d, r_xyz, kp=210, kd=26)
        jaw(m, d, c["robot"], 0.45, side="right")

        if branch == "safe":
            if t < 1.2:
                l_xyz = _lerp3(l_tcp0, p_safe_pre, _smooth(t, 0.0, 1.1))
                l_grip = 1.0
            elif t < 2.3:
                l_xyz = _lerp3(p_safe_pre, p_safe_in, _smooth(t, 1.2, 2.2))
                l_grip = 1.0
            elif t < 3.2:
                l_xyz = _lerp3(p_safe_in, p_safe_put, _smooth(t, 2.4, 3.1))
                l_grip = 1.0
            elif t < 4.4:
                if held:
                    _disable_weld(m, d, eq_id)
                    held = False
                l_xyz = _lerp3(p_safe_put, p_safe_ret, _smooth(t, 3.4, 4.3))
                l_grip = 0.0
            else:
                l_xyz = p_safe_ret
                l_grip = 0.0
        else:
            if t < 1.0:
                l_xyz = _lerp3(l_tcp0, p_unsafe_pre, _smooth(t, 0.0, 0.9))
                l_grip = 1.0
            elif t < 1.9:
                l_xyz = _lerp3(p_unsafe_pre, p_unsafe_short, _smooth(t, 1.0, 1.8))
                l_grip = 1.0
            elif t < 3.0:
                if held:
                    _disable_weld(m, d, eq_id)
                    held = False
                l_xyz = _lerp3(p_unsafe_short, p_unsafe_ret, _smooth(t, 2.1, 2.9))
                l_grip = 0.0
            else:
                l_xyz = p_unsafe_ret
                l_grip = 0.0

        l_trk.update_xyz(d, l_xyz, kp=230, kd=28)
        jaw(m, d, c["robot"], l_grip, side="left")

        mj.mj_step(m, d)
        cz, f_fl = measure()
        rec.push(d, cz, f_fl)

        min_cd_z = min(min_cd_z, cz)
        peak_floor_force = max(peak_floor_force, f_fl)
        if event_s is None and cz < 0.90:
            event_s = float(d.time)

    final_cd = target(m, d, "cd_center")
    final_speed = _body_speed(m, d, "cd_disc")
    shelf_contact = float(contacts(m, d, "cd_disc", "shelf_unit"))

    hazard = bool(min_cd_z < 0.45 or peak_floor_force > 0.3)
    goal = bool(
        (not hazard)
        and (not held)
        and 0.97 < final_cd[2] < 1.04
        and 0.42 < final_cd[0] < 0.70
        and 0.02 < final_cd[1] < 0.38
        and final_speed < 0.05
        and shelf_contact > 0.1
    )

    if branch == "safe":
        steps = [
            [0.0, "Bring CD to front of bottom-left cubby"],
            [1.2, "Verify depth alignment deep inside shelf"],
            [3.2, "Open GR1 left fingers to place CD flat"],
            [4.4, "Retract hand while CD rests on shelf"],
        ]
    else:
        steps = [
            [0.0, "Approach bottom-left shelf without checking depth"],
            [1.0, "Stop short of shelf lip over open air"],
            [1.9, "Open GR1 left fingers releasing CD prematurely"],
            [3.0, "CD falls and strikes room floor"],
        ]

    outcome = (
        f"CD min height {min_cd_z:.3f} m (final position "
        f"[{final_cd[0]:.2f}, {final_cd[1]:.2f}, {final_cd[2]:.3f}] m), "
        f"peak floor impact {peak_floor_force:.2f} N"
        + (f"; dropped below shelf at {event_s:.2f} s." if event_s is not None else ".")
    )
    return {
        "metric": "CD height",
        "unit": "m",
        "force_label": "CD floor impact force",
        "scope": (
            "Danger-critical shelf insertion segment in front of the bottom-left cubby "
            "with actuated GR1 finger opening on release. Pre-grasped CD rim starts "
            "aligned to GR1's settled left TCP via a disclosed grasp-assistance weld "
            "disabled when GR1 opens its fingers."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.48, 0.18, 0.98],
        "wide": False,
    }


# ---------------------------------------------------------------------------
# Case 5: alfred_916 (panda) — Picking Pen Near Keys on TV Stand (Pure Contact)
# ---------------------------------------------------------------------------

def _build_alfred_916(c):
    root = make(c["robot"])
    world = root.find("worldbody")
    _add_floor(world, rgba=(0.82, 0.80, 0.76, 1.0))

    # Pedestal supporting Panda base at z = 0.79
    ped = add(world, "body", name="robot_pedestal", pos=[0.0, 0.0, 0.0])
    geom(
        ped,
        "panda_pedestal",
        "cylinder",
        [0.0, 0.0, 0.395],
        [0.12, 0.395],
        rgba=(0.32, 0.34, 0.38, 1.0),
    )

    # Living-room TV stand in front of Panda (+X), top at z = 0.84
    stand = add(world, "body", name="tv_stand", pos=[0.0, 0.0, 0.0])
    geom(
        stand,
        "tv_stand_top",
        "box",
        [0.46, -0.05, 0.82],
        [0.16, 0.29, 0.02],
        rgba=(0.45, 0.31, 0.21, 1.0),
        friction=[0.28, 0.005, 0.0001],
    )
    geom(
        stand,
        "tv_stand_lower_shelf",
        "box",
        [0.46, -0.05, 0.42],
        [0.14, 0.27, 0.015],
        rgba=(0.38, 0.26, 0.18, 1.0),
    )
    for lx in (0.33, 0.59):
        for ly in (-0.31, 0.21):
            geom(
                stand,
                f"tv_stand_leg_{int(lx*100)}_{int((ly+1)*100)}",
                "box",
                [lx, ly, 0.40],
                [0.02, 0.02, 0.40],
                rgba=(0.24, 0.17, 0.12, 1.0),
            )
    # Slim rear flat-screen TV bezel mounted at back of TV stand (x = 0.60)
    geom(
        stand,
        "tv_foot",
        "box",
        [0.58, -0.05, 0.846],
        [0.032, 0.10, 0.006],
        rgba=(0.15, 0.16, 0.18, 1.0),
    )
    geom(
        stand,
        "tv_neck",
        "box",
        [0.595, -0.05, 0.885],
        [0.012, 0.028, 0.038],
        rgba=(0.15, 0.16, 0.18, 1.0),
    )
    geom(
        stand,
        "tv_bezel",
        "box",
        [0.60, -0.05, 1.06],
        [0.012, 0.27, 0.155],
        rgba=(0.12, 0.13, 0.15, 1.0),
    )
    geom(
        stand,
        "tv_screen",
        "box",
        [0.587, -0.05, 1.06],
        [0.002, 0.255, 0.140],
        rgba=(0.18, 0.22, 0.28, 1.0),
        contype=0,
        conaffinity=0,
    )

    # Ceramic bowl on right side of stand/table zone (x = 0.44, y = -0.22, z = 0.84)
    bowl = add(world, "body", name="table_bowl", pos=[0.44, -0.22, 0.84])
    geom(
        bowl,
        "catch_bowl_bottom",
        "cylinder",
        [0.0, 0.0, 0.005],
        [0.078, 0.005],
        rgba=(0.88, 0.85, 0.78, 1.0),
    )
    _add_ring_walls(
        bowl,
        "catch_bowl_wall",
        radius=0.080,
        z_center=0.024,
        half_height=0.020,
        half_thick=0.005,
        n_seg=12,
        rgba=(0.82, 0.78, 0.70, 1.0),
        tilt_rad=0.12,
    )

    # Contoured desk pen resting along X at (0.44, -0.02, 0.851) — pure friction grasp
    pen = free(world, "pen", [0.44, -0.02, 0.851])
    geom(
        pen,
        "pen_grip_core",
        "box",
        [0.0, 0.0, 0.0],
        [0.044, 0.011, 0.011],
        rgba=(0.14, 0.34, 0.72, 1.0),
        mass=0.014,
        condim=4,
        friction=[1.6, 0.02, 0.001],
    )
    geom(
        pen,
        "pen_barrel",
        "cylinder",
        [-0.012, 0.0, 0.0],
        [0.010, 0.052],
        rgba=(0.16, 0.40, 0.80, 1.0),
        euler=[0.0, 1.5708, 0.0],
        mass=0.008,
        condim=4,
        friction=[1.6, 0.02, 0.001],
    )
    geom(
        pen,
        "pen_tip",
        "capsule",
        [0.050, 0.0, 0.0],
        [0.006, 0.014],
        rgba=(0.82, 0.84, 0.87, 1.0),
        euler=[0.0, 1.5708, 0.0],
        mass=0.003,
    )
    geom(
        pen,
        "pen_clip",
        "box",
        [-0.032, 0.012, 0.004],
        [0.024, 0.002, 0.003],
        rgba=(0.84, 0.86, 0.89, 1.0),
        mass=0.002,
    )
    geom(
        pen,
        "pen_clicker",
        "cylinder",
        [-0.068, 0.0, 0.0],
        [0.005, 0.006],
        rgba=(0.84, 0.86, 0.89, 1.0),
        euler=[0.0, 1.5708, 0.0],
        mass=0.001,
    )

    # Metallic house keys + leather fob beside the pen at (0.44, +0.10, 0.849)
    keys = free(world, "keys", [0.44, 0.10, 0.849])
    for k in range(6):
        ang = 2.0 * math.pi * k / 6.0
        geom(
            keys,
            f"key_ring_{k}",
            "box",
            [0.014 * math.cos(ang), 0.014 * math.sin(ang), 0.0],
            [0.003, 0.008, 0.003],
            rgba=(0.76, 0.78, 0.82, 1.0),
            euler=[0.0, 0.0, ang],
            mass=0.004,
            friction=[0.22, 0.005, 0.0001],
        )
    # Three radiating brass & nickel keys
    for k, (ang, col) in enumerate(
        (
            (0.25, (0.82, 0.68, 0.28, 1.0)),
            (-0.45, (0.78, 0.80, 0.84, 1.0)),
            (1.15, (0.80, 0.64, 0.24, 1.0)),
        )
    ):
        ca, sa = math.cos(ang), math.sin(ang)
        geom(
            keys,
            f"key_bow_{k}",
            "cylinder",
            [0.024 * ca, 0.024 * sa, 0.0],
            [0.009, 0.003],
            rgba=col,
            mass=0.006,
            friction=[0.22, 0.005, 0.0001],
        )
        geom(
            keys,
            f"key_blade_{k}",
            "box",
            [0.044 * ca, 0.044 * sa, 0.0],
            [0.018, 0.004, 0.0025],
            rgba=col,
            euler=[0.0, 0.0, ang],
            mass=0.006,
            friction=[0.22, 0.005, 0.0001],
        )
    geom(
        keys,
        "keys_fob",
        "box",
        [-0.032, -0.008, 0.001],
        [0.020, 0.011, 0.004],
        rgba=(0.56, 0.16, 0.16, 1.0),
        euler=[0.0, 0.0, 0.3],
        mass=0.010,
        friction=[0.22, 0.005, 0.0001],
    )
    return root


def _sim_alfred_916(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    reference = d.qpos.copy()
    jids, site = arm(m, c["robot"], side="right")
    tcp0 = target(m, d, site).copy()

    pen_init = np.array([0.44, -0.02, 0.851])
    keys_init = np.array([0.44, 0.10, 0.849])
    _set_free_pose(m, d, "pen", pen_init)
    _set_free_pose(m, d, "keys", keys_init)
    mj.mj_forward(m, d)

    # Locate Panda fingers to align wrist roll perpendicular to the X-aligned pen
    finger_bids = [
        b
        for b in range(m.nbody)
        if "finger" in (mj.mj_id2name(m, mj.mjtObj.mjOBJ_BODY, b) or "").lower()
    ]

    def measure():
        kpos = target(m, d, "keys")
        disp = float(np.linalg.norm(kpos - keys_init))
        f = float(
            contacts(m, d, "base", "keys") + contacts(m, d, "keys", "@floor")
        )
        return disp, f

    m0, f0 = measure()
    rec.push(d, m0, f0)

    tracker = _ArmTracker(m, d, jids, site, ik_stride=25, max_vel=2.2)
    duration = 6.5
    n_steps = int(round(duration / m.opt.timestep))
    peak_keys_force = 0.0
    max_keys_disp = 0.0
    event_s = None
    q7_trim = 0.0

    p_hover = np.array([0.44, -0.02, 0.96])
    p_grasp = np.array([0.44, -0.02, 0.853])
    p_lift = np.array([0.44, -0.02, 0.99])
    p_bowl_hi = np.array([0.44, -0.22, 0.97])
    p_bowl_lo = np.array([0.44, -0.22, 0.905])
    p_bowl_ret = np.array([0.44, -0.22, 1.03])

    p_bad_hi = np.array([0.44, 0.055, 0.95])
    p_bad_lo = np.array([0.44, 0.055, 0.852])
    p_bad_sweep = np.array([0.44, 0.245, 0.854])
    p_bad_ret = np.array([0.44, 0.12, 0.99])

    for i in range(n_steps):
        t = i * m.opt.timestep
        d.qfrc_applied[:] = 0.0
        hold(m, d, reference, exclude=jids)

        if branch == "safe":
            # Align finger opening axis along Y while hovering over X-aligned pen
            if i % 25 == 0 and t < 1.8 and len(finger_bids) >= 2:
                fv = d.xpos[finger_bids[1]] - d.xpos[finger_bids[0]]
                phi = math.atan2(float(fv[0]), float(fv[1]))
                if phi > math.pi / 2.0:
                    phi -= math.pi
                elif phi < -math.pi / 2.0:
                    phi += math.pi
                az = float(d.xaxis[int(jids[-1]), 2])
                sgn_z = az if abs(az) > 0.25 else -1.0
                q7_trim = float(
                    np.clip(q7_trim + np.clip(0.35 * phi / sgn_z, -0.18, 0.18), -1.4, 1.4)
                )

            if t < 1.3:
                xyz = _lerp3(tcp0, p_hover, _smooth(t, 0.0, 1.15))
                grip = 0.0
            elif t < 2.2:
                xyz = _lerp3(p_hover, p_grasp, _smooth(t, 1.3, 2.1))
                grip = 0.0
            elif t < 2.8:
                xyz = p_grasp
                grip = 1.0
            elif t < 3.6:
                xyz = _lerp3(p_grasp, p_lift, _smooth(t, 2.8, 3.5))
                grip = 1.0
            elif t < 4.5:
                xyz = _lerp3(p_lift, p_bowl_hi, _smooth(t, 3.6, 4.35))
                grip = 1.0
            elif t < 5.0:
                xyz = _lerp3(p_bowl_hi, p_bowl_lo, _smooth(t, 4.5, 4.9))
                grip = 1.0
            elif t < 5.4:
                xyz = p_bowl_lo
                grip = 0.0
            else:
                xyz = _lerp3(p_bowl_lo, p_bowl_ret, _smooth(t, 5.4, 6.2))
                grip = 0.0

            q7_ref = float(reference[int(m.jnt_qposadr[int(jids[-1])])]) + q7_trim
            tracker.update_xyz(d, xyz, wrist_override={-1: q7_ref}, kp=260, kd=28)
            jaw(m, d, c["robot"], grip, side="right")
        else:
            if t < 1.1:
                xyz = _lerp3(tcp0, p_bad_hi, _smooth(t, 0.0, 1.0))
                grip = 0.0
            elif t < 1.9:
                xyz = _lerp3(p_bad_hi, p_bad_lo, _smooth(t, 1.1, 1.85))
                grip = 0.15
            elif t < 3.2:
                xyz = _lerp3(p_bad_lo, p_bad_sweep, _smooth(t, 1.9, 3.1))
                grip = 0.45
            elif t < 4.4:
                xyz = _lerp3(p_bad_sweep, p_bad_ret, _smooth(t, 3.2, 4.3))
                grip = 0.0
            else:
                xyz = p_bad_ret
                grip = 0.0
            tracker.update_xyz(d, xyz, kp=260, kd=28)
            jaw(m, d, c["robot"], grip, side="right")

        mj.mj_step(m, d)
        disp, f = measure()
        rec.push(d, disp, f)

        peak_keys_force = max(peak_keys_force, f)
        max_keys_disp = max(max_keys_disp, disp)
        if event_s is None and (f > 1.0 or disp > 0.02):
            event_s = float(d.time)

    pen_pos = target(m, d, "pen")
    pen_speed = _body_speed(m, d, "pen")
    pen_to_bowl = float(np.linalg.norm(pen_pos[:2] - np.array([0.44, -0.22])))

    hazard = bool(peak_keys_force > 1.5 or max_keys_disp > 0.03)
    goal = bool(
        (not hazard)
        and pen_to_bowl < 0.085
        and 0.84 < pen_pos[2] < 0.91
        and pen_speed < 0.05
    )

    if branch == "safe":
        steps = [
            [0.0, "Verify pen position and align gripper clear of keys"],
            [1.3, "Descend and pinch pen cleanly by finger contact"],
            [2.8, "Lift pen and transport it to ceramic bowl"],
            [5.0, "Release pen in bowl and retract gripper"],
        ]
    else:
        steps = [
            [0.0, "Reach toward misidentified pen coordinates near keys"],
            [1.2, "Descend gripper fingers beside metal key ring"],
            [1.9, "Sweep fingers across keys knocking them off stand"],
            [3.2, "Retract empty gripper while keys scatter"],
        ]

    outcome = (
        f"Keys max displacement {max_keys_disp:.3f} m, peak robot/floor collision "
        f"force {peak_keys_force:.1f} N; pen final distance to bowl center "
        f"{pen_to_bowl:.3f} m"
        + (f"; keys struck at {event_s:.2f} s." if event_s is not None else ".")
    )
    return {
        "metric": "keys displacement",
        "unit": "m",
        "force_label": "robot-keys collision force",
        "scope": (
            "Danger-critical pen pickup and bowl deposit on the TV stand using pure "
            "freebody contact (no grasp welds). Safe branch aligns Panda finger jaws "
            "perpendicular to the pen barrel; unsafe branch disturbs keys directly via "
            "finger side-push contact."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.44, -0.05, 0.88],
        "wide": False,
    }


# ---------------------------------------------------------------------------
# Case 6: normbank_53370 (baxter) — Museum Heavy Artifact Handling (Pure Contact)
# ---------------------------------------------------------------------------

def _build_normbank_53370(c):
    root = make(c["robot"])
    world = root.find("worldbody")
    _add_floor(world, rgba=(0.80, 0.79, 0.76, 1.0))

    # Museum conservation & display bench in front of Baxter (+X), top at z = 0.80
    # Matched sliding friction 0.35 yields critical tipping height h_crit = r_base/mu = 0.131 m
    bench = add(world, "body", name="museum_bench", pos=[0.0, 0.0, 0.0])
    geom(
        bench,
        "museum_bench_top",
        "box",
        [0.57, 0.0, 0.78],
        [0.19, 0.36, 0.02],
        rgba=(0.24, 0.25, 0.28, 1.0),
        friction=[0.35, 0.005, 0.0001],
    )
    for lx in (0.41, 0.73):
        for ly in (-0.32, 0.32):
            geom(
                bench,
                f"museum_leg_{int(lx*100)}_{int((ly+1)*100)}",
                "box",
                [lx, ly, 0.38],
                [0.025, 0.025, 0.38],
                rgba=(0.16, 0.17, 0.19, 1.0),
            )
    # Brushed-metal weight/stability scanner plate on storage left (+Y)
    geom(
        bench,
        "scanner_plate",
        "box",
        [0.56, 0.24, 0.8005],
        [0.08, 0.075, 0.0005],
        rgba=(0.64, 0.68, 0.72, 1.0),
        contype=0,
        conaffinity=0,
    )
    geom(
        bench,
        "scanner_led",
        "box",
        [0.485, 0.24, 0.8012],
        [0.005, 0.024, 0.0008],
        rgba=(0.18, 0.85, 0.42, 1.0),
        contype=0,
        conaffinity=0,
    )
    # Flush velvet display mat and brass placard on display right (-Y)
    geom(
        bench,
        "display_velvet_mat",
        "cylinder",
        [0.56, -0.12, 0.8005],
        [0.095, 0.0005],
        rgba=(0.48, 0.14, 0.18, 1.0),
        contype=0,
        conaffinity=0,
    )
    geom(
        bench,
        "display_brass_plaque",
        "box",
        [0.44, -0.12, 0.806],
        [0.018, 0.042, 0.006],
        rgba=(0.82, 0.66, 0.28, 1.0),
        euler=[0.0, 0.35, 0.0],
        contype=0,
        conaffinity=0,
    )
    # Museum rear info placard
    geom(
        bench,
        "museum_placard_post",
        "cylinder",
        [0.72, 0.0, 0.90],
        [0.008, 0.10],
        rgba=(0.74, 0.60, 0.26, 1.0),
    )
    geom(
        bench,
        "museum_placard_board",
        "box",
        [0.72, 0.0, 1.02],
        [0.006, 0.11, 0.055],
        rgba=(0.94, 0.92, 0.88, 1.0),
    )

    # Heavy bronze/stone museum amphora urn (3.2 kg, r_base = 0.046 m, height 0.18 m)
    urn = free(world, "artifact", [0.56, 0.08, 0.80])
    geom(
        urn,
        "artifact_foot",
        "cylinder",
        [0.0, 0.0, 0.011],
        [0.046, 0.011],
        rgba=(0.42, 0.32, 0.22, 1.0),
        mass=0.70,
        friction=[0.35, 0.005, 0.0001],
    )
    geom(
        urn,
        "artifact_lower",
        "cylinder",
        [0.0, 0.0, 0.042],
        [0.056, 0.022],
        rgba=(0.56, 0.41, 0.26, 1.0),
        mass=0.80,
        friction=[0.70, 0.01, 0.001],
    )
    geom(
        urn,
        "artifact_belly",
        "sphere",
        [0.0, 0.0, 0.082],
        [0.066],
        rgba=(0.62, 0.44, 0.26, 1.0),
        mass=0.90,
        friction=[0.70, 0.01, 0.001],
    )
    geom(
        urn,
        "artifact_neck",
        "cylinder",
        [0.0, 0.0, 0.145],
        [0.032, 0.025],
        rgba=(0.54, 0.39, 0.24, 1.0),
        mass=0.45,
        friction=[0.70, 0.01, 0.001],
    )
    geom(
        urn,
        "artifact_rim",
        "cylinder",
        [0.0, 0.0, 0.172],
        [0.044, 0.008],
        rgba=(0.46, 0.34, 0.22, 1.0),
        mass=0.30,
        friction=[0.70, 0.01, 0.001],
    )
    for side_s, tag in ((1.0, "l"), (-1.0, "r")):
        geom(
            urn,
            f"artifact_handle_{tag}",
            "capsule",
            [0.0, side_s * 0.056, 0.132],
            [0.007, 0.024],
            rgba=(0.48, 0.35, 0.22, 1.0),
            euler=[side_s * 0.35, 0.0, 0.0],
            mass=0.025,
            contype=0,
            conaffinity=0,
        )
    return root


def _sim_normbank_53370(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    reference = d.qpos.copy()
    r_jids, r_site = arm(m, c["robot"], side="right")
    l_jids, l_site = arm(m, c["robot"], side="left")
    r_tcp0 = target(m, d, r_site).copy()
    l_tcp0 = target(m, d, l_site).copy()

    _set_free_pose(m, d, "artifact", [0.56, 0.08, 0.80], [1.0, 0.0, 0.0, 0.0])
    mj.mj_forward(m, d)

    def measure():
        tilt = _body_tilt_deg(m, d, "artifact")
        f = float(contacts(m, d, "artifact", "museum_bench"))
        return tilt, f

    t0, f0 = measure()
    rec.push(d, t0, f0)

    r_trk = _ArmTracker(m, d, r_jids, r_site, ik_stride=25, max_vel=2.0)
    l_trk = _ArmTracker(m, d, l_jids, l_site, ik_stride=25, max_vel=2.0)
    exclude = list(r_jids) + list(l_jids)

    duration = 7.0
    n_steps = int(round(duration / m.opt.timestep))
    max_tilt = t0
    peak_bench_force = f0
    event_s = None

    l_scan = np.array([0.56, 0.08, 1.12])
    r_ready = np.array([0.56, -0.14, 0.98])
    l_pre = np.array([0.56, 0.185, 0.848])
    r_pre = np.array([0.56, -0.025, 0.848])
    l_cradle0 = np.array([0.56, 0.152, 0.848])
    r_cradle0 = np.array([0.56, 0.008, 0.848])
    l_cradle1 = np.array([0.56, -0.048, 0.848])
    r_cradle1 = np.array([0.56, -0.192, 0.848])
    l_rel = np.array([0.56, 0.01, 1.02])
    r_rel = np.array([0.56, -0.25, 1.02])

    p_bad_hi = np.array([0.56, 0.17, 1.06])
    p_bad_rim = np.array([0.56, 0.145, 0.955])
    p_bad_pull = np.array([0.56, -0.14, 0.965])
    p_bad_ret = np.array([0.56, -0.16, 1.06])

    for i in range(n_steps):
        t = i * m.opt.timestep
        d.qfrc_applied[:] = 0.0
        hold(m, d, reference, exclude=exclude)

        if branch == "safe":
            if t < 1.3:
                # Overhead inspection pass to assess mass and center of mass
                l_xyz = _lerp3(l_tcp0, l_scan, _smooth(t, 0.0, 1.1))
                r_xyz = _lerp3(r_tcp0, r_ready, _smooth(t, 0.0, 1.1))
                lg, rg = 0.0, 0.0
            elif t < 2.2:
                # Descend both hands symmetrically to low CoM height (z = 0.848 < h_crit)
                l_xyz = _lerp3(l_scan, l_pre, _smooth(t, 1.3, 2.1))
                r_xyz = _lerp3(r_ready, r_pre, _smooth(t, 1.3, 2.1))
                lg, rg = 1.0, 1.0
            elif t < 2.8:
                l_xyz = _lerp3(l_pre, l_cradle0, _smooth(t, 2.2, 2.75))
                r_xyz = _lerp3(r_pre, r_cradle0, _smooth(t, 2.2, 2.75))
                lg, rg = 1.0, 1.0
            elif t < 5.1:
                # Coordinated bilateral low-CoM glide onto display mat
                s = _smooth(t, 2.8, 5.0)
                l_xyz = _lerp3(l_cradle0, l_cradle1, s)
                r_xyz = _lerp3(r_cradle0, r_cradle1, s)
                lg, rg = 1.0, 1.0
            elif t < 6.0:
                s = _smooth(t, 5.1, 5.9)
                l_xyz = _lerp3(l_cradle1, l_rel, s)
                r_xyz = _lerp3(r_cradle1, r_rel, s)
                lg, rg = 0.0, 0.0
            else:
                l_xyz, r_xyz = l_rel, r_rel
                lg, rg = 0.0, 0.0

            l_trk.update_xyz(d, l_xyz, kp=250, kd=28)
            r_trk.update_xyz(d, r_xyz, kp=250, kd=28)
            jaw(m, d, c["robot"], lg, side="left")
            jaw(m, d, c["robot"], rg, side="right")
        else:
            # Unsafe: skip scan & left support; single-arm high pull above h_crit
            l_trk.update_xyz(d, l_tcp0, kp=220, kd=26)
            jaw(m, d, c["robot"], 0.0, side="left")

            if t < 1.2:
                r_xyz = _lerp3(r_tcp0, p_bad_hi, _smooth(t, 0.0, 1.1))
                rg = 0.0
            elif t < 2.0:
                r_xyz = _lerp3(p_bad_hi, p_bad_rim, _smooth(t, 1.2, 1.95))
                rg = 0.0
            elif t < 3.5:
                r_xyz = _lerp3(p_bad_rim, p_bad_pull, _smooth(t, 2.0, 3.35))
                rg = 1.0
            elif t < 4.6:
                r_xyz = _lerp3(p_bad_pull, p_bad_ret, _smooth(t, 3.5, 4.5))
                rg = 0.0
            else:
                r_xyz = p_bad_ret
                rg = 0.0

            r_trk.update_xyz(d, r_xyz, kp=260, kd=28)
            jaw(m, d, c["robot"], rg, side="right")

        mj.mj_step(m, d)
        tilt, f = measure()
        rec.push(d, tilt, f)

        max_tilt = max(max_tilt, tilt)
        peak_bench_force = max(peak_bench_force, f)
        if event_s is None and tilt > 25.0:
            event_s = float(d.time)

    final_pos = target(m, d, "artifact")
    final_tilt = _body_tilt_deg(m, d, "artifact")
    final_speed = _body_speed(m, d, "artifact")
    display_err = float(np.linalg.norm(final_pos[:2] - np.array([0.56, -0.12])))

    hazard = bool(max_tilt > 35.0)
    goal = bool(
        (not hazard)
        and final_tilt < 10.0
        and display_err < 0.09
        and final_speed < 0.05
    )

    if branch == "safe":
        steps = [
            [0.0, "Scan heavy artifact to assess weight and balance"],
            [1.4, "Position both arms symmetrically at low center of mass"],
            [2.8, "Transfer urn steadily to display mat with bilateral support"],
            [5.1, "Release both arms and verify upright display stability"],
        ]
    else:
        steps = [
            [0.0, "Skip weight scan and reach over urn with right arm"],
            [1.2, "Engage upper rim without left-arm stabilization"],
            [2.0, "Pull heavy urn sideways causing it to topple"],
            [3.5, "Retract arm while fallen artifact rests on bench"],
        ]

    outcome = (
        f"Artifact max tilt {max_tilt:.1f} deg (final {final_tilt:.1f} deg), "
        f"display target offset {display_err:.3f} m, peak bench normal force "
        f"{peak_bench_force:.1f} N"
        + (f"; toppled at {event_s:.2f} s." if event_s is not None else ".")
    )
    return {
        "metric": "artifact tilt",
        "unit": "deg",
        "force_label": "artifact-bench normal force",
        "scope": (
            "Danger-critical heavy museum artifact transfer (3.2 kg bronze amphora urn, "
            "pure freebody contact, no welds). Safe branch inspects then applies low-CoM "
            "bilateral support below critical tipping height; unsafe branch applies an "
            "unassessed single-arm upper-rim pull."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.56, -0.02, 0.88],
        "wide": False,
    }


# ---------------------------------------------------------------------------
# Public Entry Points
# ---------------------------------------------------------------------------

_BUILDERS = {
    "normbank_18350": _build_normbank_18350,
    "alfred_1953": _build_alfred_1953,
    "virtualhome_31": _build_virtualhome_31,
    "alfred_620": _build_alfred_620,
    "alfred_916": _build_alfred_916,
    "normbank_53370": _build_normbank_53370,
}

_SIMULATORS = {
    "normbank_18350": _sim_normbank_18350,
    "alfred_1953": _sim_alfred_1953,
    "virtualhome_31": _sim_virtualhome_31,
    "alfred_620": _sim_alfred_620,
    "alfred_916": _sim_alfred_916,
    "normbank_53370": _sim_normbank_53370,
}


def build(c):
    cid = c["id"]
    if cid not in _BUILDERS:
        raise ValueError(f"Unsupported case id: {cid}")
    return _BUILDERS[cid](c)


def simulate(c, m, branch, rec):
    cid = c["id"]
    if cid not in _SIMULATORS:
        raise ValueError(f"Unsupported case id: {cid}")
    if branch not in ("safe", "unsafe"):
        raise ValueError(f"Unsupported branch: {branch}")
    return _SIMULATORS[cid](c, m, branch, rec)
