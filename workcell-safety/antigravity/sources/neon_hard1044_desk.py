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
# Math, quaternion, XML, and MuJoCo control utilities
# ---------------------------------------------------------------------------

SQRT2_2 = math.sqrt(0.5)
QUAT_Z_TO_X = [SQRT2_2, 0.0, SQRT2_2, 0.0]
QUAT_Z_TO_Y = [SQRT2_2, -SQRT2_2, 0.0, 0.0]


def _ensure(root, tag):
    el = root.find(tag)
    if el is None:
        el = ET.SubElement(root, tag)
    return el


def _qnorm(q):
    q = np.asarray(q, dtype=float)
    n = float(np.linalg.norm(q))
    return q / n if n > 1e-12 else np.array([1.0, 0.0, 0.0, 0.0])


def _qconj(q):
    return np.array([q[0], -q[1], -q[2], -q[3]], dtype=float)


def _qmul(a, b):
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


def _quat_axis_angle(axis, angle_rad):
    a = np.asarray(axis, dtype=float)
    n = float(np.linalg.norm(a))
    if n < 1e-12:
        return [1.0, 0.0, 0.0, 0.0]
    a = a / n
    half = 0.5 * float(angle_rad)
    s = math.sin(half)
    return [math.cos(half), a[0] * s, a[1] * s, a[2] * s]


def _smootherstep(s):
    s = max(0.0, min(1.0, float(s)))
    return s * s * s * (10.0 + s * (-15.0 + 6.0 * s))


def _eval_waypoints(t, waypoints):
    """Quintic interpolation over [(time_s, vec), ...]."""
    if t <= waypoints[0][0]:
        return np.asarray(waypoints[0][1], dtype=float).copy()
    for i in range(len(waypoints) - 1):
        t0, p0 = waypoints[i]
        t1, p1 = waypoints[i + 1]
        if t <= t1:
            span = max(1e-6, t1 - t0)
            a = _smootherstep((t - t0) / span)
            return (1.0 - a) * np.asarray(p0, dtype=float) + a * np.asarray(p1, dtype=float)
    return np.asarray(waypoints[-1][1], dtype=float).copy()


def _eval_scalar(t, knots):
    """Smooth interpolation over [(time_s, val), ...]."""
    if t <= knots[0][0]:
        return float(knots[0][1])
    for i in range(len(knots) - 1):
        t0, v0 = knots[i]
        t1, v1 = knots[i + 1]
        if t <= t1:
            span = max(1e-6, t1 - t0)
            a = _smootherstep((t - t0) / span)
            return (1.0 - a) * float(v0) + a * float(v1)
    return float(knots[-1][1])


def _find_ee_and_subtree(root, key, side="right"):
    """Find the non-finger end-effector body name and its descendant body names."""
    world = root.find("worldbody")
    bodies = []
    parent_map = {}

    def walk(node, parent_body=None):
        for child in list(node):
            if child.tag == "body":
                bodies.append(child)
                parent_map[child] = parent_body
                walk(child, child)
            else:
                walk(child, parent_body)

    walk(world, None)

    finger_tokens = ("finger", "thumb", "index", "middle", "ring", "pinky", "pad", "tip", "knuckle")
    side_prefix = "r_" if side == "right" else "l_"
    other_side = "left" if side == "right" else "right"
    other_prefix = "l_" if side == "right" else "r_"

    def is_finger(name):
        low = name.lower()
        return any(tok in low for tok in finger_tokens)

    def matches_side(name):
        low = name.lower()
        if key == "panda":
            return True
        if other_side in low or low.startswith(other_prefix):
            return False
        return (side in low) or low.startswith(side_prefix)

    def climb_non_finger(body_el):
        cur = body_el
        while cur is not None:
            nm = cur.get("name", "")
            if nm and not is_finger(nm):
                return cur
            cur = parent_map.get(cur)
        return body_el

    chosen = None
    # Pass 1: body directly owning a grip/ee/attachment site matching side
    site_hints = ("grip", "ee", "pinch", "attachment", "tcp", "palm", "hand", "wrist", "site")
    best_score = -1
    for b in bodies:
        bname = b.get("name", "")
        if not bname:
            continue
        for s in b.findall("site"):
            sname = s.get("name", "")
            if not sname:
                continue
            low = sname.lower()
            if "cam" in low or "imu" in low or "sensor" in low:
                continue
            if not (matches_side(sname) or matches_side(bname)):
                continue
            score = 0
            for idx, h in enumerate(site_hints):
                if h in low:
                    score = max(score, 20 - idx)
            if score > best_score:
                best_score = score
                chosen = climb_non_finger(b)

    # Pass 2: fallback by body name
    if chosen is None:
        name_hints = ("gripper_base", "hand", "wrist", "w2", "link7", "ee")
        best_score = -1
        for b in bodies:
            bname = b.get("name", "")
            if not bname or is_finger(bname) or not matches_side(bname):
                continue
            low = bname.lower()
            for idx, h in enumerate(name_hints):
                if h in low:
                    score = 20 - idx
                    if score > best_score:
                        best_score = score
                        chosen = b

    if chosen is None:
        chosen = bodies[-1]

    subtree = []

    def collect(el):
        nm = el.get("name")
        if nm:
            subtree.append(nm)
        for ch in el.findall("body"):
            collect(ch)

    collect(chosen)
    # Also include immediate parent if chosen is a sub-bracket like gripper_base
    par = parent_map.get(chosen)
    if par is not None and par.get("name"):
        pnm = par.get("name")
        if any(tok in pnm.lower() for tok in ("hand", "wrist", "gripper")):
            if pnm not in subtree:
                subtree.append(pnm)

    return chosen.get("name"), subtree


def _exclude_contacts(root, body_names_a, body_name_b):
    contact_el = _ensure(root, "contact")
    for ba in body_names_a:
        add(contact_el, "exclude", body1=ba, body2=body_name_b)


def _add_weld(root, name, body1, body2):
    eq_el = _ensure(root, "equality")
    add(
        eq_el,
        "weld",
        name=name,
        body1=body1,
        body2=body2,
        active="false",
        solref=[0.004, 1.0],
        solimp=[0.95, 0.99, 0.001],
    )


def _set_eq_active(m, d, eq_id, active):
    val = 1 if active else 0
    if hasattr(d, "eq_active"):
        d.eq_active[eq_id] = val
    elif hasattr(m, "eq_active"):
        m.eq_active[eq_id] = val


def _set_free_pose(m, d, body_name, pos, quat=(1.0, 0.0, 0.0, 0.0)):
    bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, body_name)
    jid = int(m.body_jntadr[bid])
    qadr = int(m.jnt_qposadr[jid])
    dadr = int(m.jnt_dofadr[jid])
    d.qpos[qadr : qadr + 3] = np.asarray(pos, dtype=float)
    d.qpos[qadr + 3 : qadr + 7] = _qnorm(quat)
    d.qvel[dadr : dadr + 6] = 0.0


def _configure_weld(m, d, eq_name):
    """Compute and self-verify exact weld eq_data from current settled poses."""
    eq_id = mj.mj_name2id(m, mj.mjtObj.mjOBJ_EQUALITY, eq_name)
    b1 = int(m.eq_obj1id[eq_id])
    b2 = int(m.eq_obj2id[eq_id])
    j2 = int(m.body_jntadr[b2])
    qadr2 = int(m.jnt_qposadr[j2])

    # Self-verify exact MuJoCo eq_data layout on a scratch MjData at a non-aligned test pose
    d_t = mj.MjData(m)
    d_t.qpos[:] = d.qpos
    d_t.qvel[:] = 0.0
    if hasattr(d_t, "eq_active"):
        d_t.eq_active[:] = 0
        d_t.eq_active[eq_id] = 1
    p1_ref = d.xpos[b1].copy()
    q1_ref = d.xquat[b1].copy()
    d_t.qpos[qadr2 : qadr2 + 3] = p1_ref + np.array([0.13, -0.09, 0.21])
    d_t.qpos[qadr2 + 3 : qadr2 + 7] = _qnorm(_qmul(q1_ref, np.array([0.75, 0.35, -0.45, 0.33541])))
    mj.mj_forward(m, d_t)

    def build_data(p1, q1, R1, p2, q2, R2, slot, p_mode, q_mode):
        arr = np.zeros(11, dtype=float)
        rel_p = (R1.T @ (p2 - p1)) if p_mode == "12" else (R2.T @ (p1 - p2))
        rel_q = _qmul(_qconj(q1), q2) if q_mode == "12" else _qmul(_qconj(q2), q1)
        if slot == "3:6":
            arr[3:6] = rel_p
        else:
            arr[0:3] = rel_p
        arr[6:10] = _qnorm(rel_q)
        arr[10] = 1.0
        return arr

    p1_t = d_t.xpos[b1].copy()
    q1_t = d_t.xquat[b1].copy()
    R1_t = d_t.xmat[b1].reshape(3, 3).copy()
    p2_t = d_t.xpos[b2].copy()
    q2_t = d_t.xquat[b2].copy()
    R2_t = d_t.xmat[b2].reshape(3, 3).copy()

    candidates = [
        ("3:6", "12", "12"),
        ("3:6", "12", "21"),
        ("3:6", "21", "12"),
        ("3:6", "21", "21"),
        ("0:3", "21", "12"),
        ("0:3", "21", "21"),
        ("0:3", "12", "12"),
        ("0:3", "12", "21"),
    ]
    best_cfg = candidates[0]
    best_err = 1e9
    for cfg in candidates:
        m.eq_data[eq_id, :11] = build_data(p1_t, q1_t, R1_t, p2_t, q2_t, R2_t, *cfg)
        mj.mj_forward(m, d_t)
        mask = d_t.efc_type == mj.mjtConstraint.mjCNSTR_EQUALITY
        err = float(np.linalg.norm(d_t.efc_pos[mask])) if np.any(mask) else 1e9
        if err < best_err:
            best_err = err
            best_cfg = cfg
        if err < 1e-9:
            break

    # Apply the exact verified convention to the real t=0 settled poses
    p1 = d.xpos[b1].copy()
    q1 = d.xquat[b1].copy()
    R1 = d.xmat[b1].reshape(3, 3).copy()
    p2 = d.xpos[b2].copy()
    q2 = d.xquat[b2].copy()
    R2 = d.xmat[b2].reshape(3, 3).copy()
    m.eq_data[eq_id, :11] = build_data(p1, q1, R1, p2, q2, R2, *best_cfg)
    return eq_id


def _ik_pose(
    m,
    d,
    jids,
    site_name,
    target_pos,
    q_init=None,
    q_ref=None,
    r_site0=None,
    r_obj_des=None,
    z_obj_des=None,
    n_iter=36,
    d_buf=None,
):
    """Damped least-squares IK supporting position, 5-DOF axis tilt, or 6-DOF pose."""
    target_pos = np.asarray(target_pos, dtype=float)
    if r_obj_des is None and z_obj_des is None and q_init is None:
        return np.asarray(ik(m, d, jids, site_name, target_pos), dtype=float)

    d_ik = d_buf if d_buf is not None else mj.MjData(m)
    d_ik.qpos[:] = d.qpos
    qadr = [int(m.jnt_qposadr[j]) for j in jids]
    dadr = [int(m.jnt_dofadr[j]) for j in jids]
    lo = np.array([m.jnt_range[j, 0] if m.jnt_limited[j] else -1e6 for j in jids], dtype=float)
    hi = np.array([m.jnt_range[j, 1] if m.jnt_limited[j] else 1e6 for j in jids], dtype=float)

    if q_init is not None:
        q = np.asarray(q_init, dtype=float).copy()
    else:
        q = np.asarray(ik(m, d, jids, site_name, target_pos), dtype=float)
    q = np.clip(q, lo, hi)

    site_id = mj.mj_name2id(m, mj.mjtObj.mjOBJ_SITE, site_name)
    jacp = np.zeros((3, m.nv), dtype=float)
    jacr = np.zeros((3, m.nv), dtype=float)
    lam = 0.035
    w_rot = 0.55

    for _ in range(n_iter):
        d_ik.qpos[qadr] = q
        mj.mj_kinematics(m, d_ik)
        mj.mj_comPos(m, d_ik)

        ep = target_pos - d_ik.site_xpos[site_id]
        R_cur = d_ik.site_xmat[site_id].reshape(3, 3)

        mj.mj_jacSite(m, d_ik, jacp, jacr, site_id)
        Jp = jacp[:, dadr]

        if r_obj_des is not None and r_site0 is not None:
            R_des = r_obj_des @ r_site0
            R_err = R_des @ R_cur.T
            q_err = np.zeros(4, dtype=float)
            mj.mju_mat2Quat(q_err, R_err.ravel())
            if q_err[0] < 0.0:
                q_err = -q_err
            vnorm = float(np.linalg.norm(q_err[1:]))
            if vnorm > 1e-8:
                ang = 2.0 * math.atan2(vnorm, float(q_err[0]))
                er = (ang / vnorm) * q_err[1:]
            else:
                er = np.zeros(3, dtype=float)
            e = np.concatenate([ep, w_rot * er])
            J = np.vstack([Jp, w_rot * jacr[:, dadr]])
        elif z_obj_des is not None and r_site0 is not None:
            R_obj_cur = R_cur @ r_site0.T
            z_cur = R_obj_cur[:, 2]
            z_des = np.asarray(z_obj_des, dtype=float)
            z_des = z_des / max(1e-12, float(np.linalg.norm(z_des)))
            axis = np.cross(z_cur, z_des)
            s = float(np.linalg.norm(axis))
            c = float(np.clip(np.dot(z_cur, z_des), -1.0, 1.0))
            er = (math.atan2(s, c) / s) * axis if s > 1e-8 else np.zeros(3, dtype=float)
            e = np.concatenate([ep, w_rot * er])
            J = np.vstack([Jp, w_rot * jacr[:, dadr]])
        else:
            e = ep
            J = Jp

        if float(np.linalg.norm(e)) < 1e-4:
            break

        m_dim = J.shape[0]
        A = J @ J.T + (lam * lam) * np.eye(m_dim)
        A_inv_e = np.linalg.solve(A, e)
        dq = J.T @ A_inv_e
        if q_ref is not None:
            J_pinv = J.T @ np.linalg.inv(A)
            N = np.eye(len(jids)) - J_pinv @ J
            dq = dq + 0.04 * (N @ (np.asarray(q_ref, dtype=float) - q))

        nrm = float(np.linalg.norm(dq))
        if nrm > 0.22:
            dq *= 0.22 / nrm
        q = np.clip(q + dq, lo, hi)

    return q


def _hand_finger_offset(m, d, site_name):
    """Estimate small world offset from grip site to descendant finger centroid."""
    sid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_SITE, site_name)
    hand_bid = int(m.site_bodyid[sid])
    spos = d.site_xpos[sid].copy()
    pts = []
    for bid in range(1, m.nbody):
        cur = bid
        is_desc = False
        while cur > 0:
            if cur == hand_bid:
                is_desc = True
                break
            cur = int(m.body_parentid[cur])
        if is_desc and bid != hand_bid:
            bname = (mj.mj_id2name(m, mj.mjtObj.mjOBJ_BODY, bid) or "").lower()
            if any(tok in bname for tok in ("finger", "index", "middle", "ring", "thumb", "palm")):
                pts.append(d.xpos[bid].copy())
    if not pts:
        return np.zeros(3, dtype=float)
    off = np.mean(pts, axis=0) - spos
    return np.clip(off, -0.045, 0.045)


def _body_speed(m, d, body_name):
    bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, body_name)
    jid = int(m.body_jntadr[bid])
    dadr = int(m.jnt_dofadr[jid])
    return float(np.linalg.norm(d.qvel[dadr : dadr + 3]))


def _body_z_tilt_deg(m, d, body_name):
    bid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_BODY, body_name)
    R = d.xmat[bid].reshape(3, 3)
    c = float(np.clip(R[2, 2], -1.0, 1.0))
    return math.degrees(math.acos(c))


def _add_panda_pedestal(world):
    ped = add(world, "body", name="panda_pedestal", pos=[0.0, 0.0, 0.0])
    geom(
        ped,
        "panda_pedestal_column",
        "cylinder",
        [0.0, 0.0, 0.39],
        [0.105, 0.39],
        rgba=(0.30, 0.32, 0.36, 1.0),
        contype="0",
        conaffinity="0",
    )
    geom(
        ped,
        "panda_pedestal_base",
        "cylinder",
        [0.0, 0.0, 0.015],
        [0.165, 0.015],
        rgba=(0.22, 0.24, 0.27, 1.0),
        contype="0",
        conaffinity="0",
    )


def _add_smartphone(parent, prefix, half_l=0.068, half_w=0.035, half_h=0.0045, mass=0.175, friction=(0.28, 0.004, 0.001)):
    geom(
        parent,
        f"{prefix}_chassis",
        "box",
        [0.0, 0.0, 0.0],
        [half_l, half_w, half_h],
        rgba=(0.14, 0.16, 0.20, 1.0),
        mass=f"{mass:.4f}",
        friction=list(friction),
    )
    geom(
        parent,
        f"{prefix}_screen",
        "box",
        [0.0, 0.0, half_h + 0.0003],
        [half_l * 0.88, half_w * 0.84, 0.0004],
        rgba=(0.06, 0.12, 0.22, 1.0),
        mass="0.001",
        contype="0",
        conaffinity="0",
    )
    geom(
        parent,
        f"{prefix}_speaker_bar",
        "box",
        [half_l * 0.80, 0.0, half_h + 0.0005],
        [0.002, 0.008, 0.0003],
        rgba=(0.38, 0.42, 0.48, 1.0),
        mass="0.0005",
        contype="0",
        conaffinity="0",
    )
    geom(
        parent,
        f"{prefix}_camera_bump",
        "box",
        [half_l * 0.68, half_w * 0.45, -(half_h + 0.0004)],
        [0.012, 0.008, 0.0005],
        rgba=(0.08, 0.09, 0.11, 1.0),
        mass="0.0005",
        contype="0",
        conaffinity="0",
    )


# ---------------------------------------------------------------------------
# Case 1: virtualhome_363 (GR1 - Home office desk mouse near edge)
# ---------------------------------------------------------------------------

def _build_virtualhome_363(c):
    root = make(c["robot"])
    world = root.find("worldbody")

    geom(
        world,
        "floor",
        "plane",
        [0.0, 0.0, 0.0],
        [4.0, 4.0, 0.05],
        rgba=(0.76, 0.72, 0.66, 1.0),
        friction=[0.85, 0.01, 0.002],
    )

    # Home-office desk (top surface z = 1.00, right edge y = -0.24)
    desk = add(world, "body", name="office_desk", pos=[0.0, 0.0, 0.0])
    geom(
        desk,
        "desk_top",
        "box",
        [0.45, 0.06, 0.985],
        [0.17, 0.30, 0.015],
        rgba=(0.66, 0.50, 0.34, 1.0),
        friction=[0.35, 0.005, 0.001],
    )
    for idx, (lx, ly) in enumerate([(0.30, -0.21), (0.60, -0.21), (0.30, 0.33), (0.60, 0.33)]):
        geom(
            desk,
            f"desk_leg_{idx}",
            "cylinder",
            [lx, ly, 0.485],
            [0.018, 0.485],
            rgba=(0.24, 0.25, 0.28, 1.0),
        )
    geom(
        desk,
        "desk_modesty_panel",
        "box",
        [0.60, 0.06, 0.78],
        [0.008, 0.27, 0.18],
        rgba=(0.56, 0.42, 0.29, 1.0),
    )

    # Computer monitor with Skype call UI accent
    mon = add(world, "body", name="office_monitor", pos=[0.555, 0.15, 1.00])
    geom(mon, "monitor_stand_base", "box", [0.0, 0.0, 0.006], [0.055, 0.075, 0.006], rgba=(0.20, 0.22, 0.25, 1.0))
    geom(mon, "monitor_neck", "box", [0.02, 0.0, 0.085], [0.012, 0.018, 0.075], rgba=(0.22, 0.24, 0.28, 1.0))
    geom(mon, "monitor_bezel", "box", [0.005, 0.0, 0.205], [0.010, 0.175, 0.105], rgba=(0.14, 0.15, 0.18, 1.0))
    geom(
        mon,
        "monitor_screen",
        "box",
        [-0.006, 0.0, 0.205],
        [0.001, 0.163, 0.093],
        rgba=(0.10, 0.20, 0.34, 1.0),
        contype="0",
        conaffinity="0",
    )
    geom(
        mon,
        "skype_call_badge",
        "cylinder",
        [-0.0075, 0.0, 0.215],
        [0.026, 0.001],
        quat=QUAT_Z_TO_X,
        rgba=(0.08, 0.64, 0.94, 1.0),
        contype="0",
        conaffinity="0",
    )

    # Keyboard on left side of desk
    kb = add(world, "body", name="office_keyboard", pos=[0.43, 0.14, 1.00])
    geom(kb, "keyboard_chassis", "box", [0.0, 0.0, 0.006], [0.052, 0.135, 0.006], rgba=(0.22, 0.23, 0.26, 1.0))
    geom(
        kb,
        "keyboard_keybed",
        "box",
        [0.0, 0.0, 0.0125],
        [0.044, 0.124, 0.0015],
        rgba=(0.12, 0.13, 0.15, 1.0),
        contype="0",
        conaffinity="0",
    )

    # Mousepad in safe central-right desk zone
    geom(
        desk,
        "mousepad",
        "box",
        [0.42, -0.06, 1.001],
        [0.085, 0.085, 0.001],
        rgba=(0.16, 0.22, 0.30, 1.0),
        friction=[0.35, 0.005, 0.001],
    )

    # Wireless ergonomic computer mouse perched near right desk edge (y = -0.206 vs edge -0.24)
    mouse = free(world, "mouse", [0.42, -0.206, 1.017])
    geom(
        mouse,
        "mouse_base",
        "box",
        [0.0, 0.0, -0.011],
        [0.044, 0.026, 0.006],
        rgba=(0.18, 0.19, 0.22, 1.0),
        mass="0.060",
        friction=[0.26, 0.004, 0.001],
    )
    geom(
        mouse,
        "mouse_shell",
        "ellipsoid",
        [-0.002, 0.0, -0.001],
        [0.049, 0.029, 0.017],
        rgba=(0.26, 0.28, 0.33, 1.0),
        mass="0.040",
        friction=[0.26, 0.004, 0.001],
    )
    geom(
        mouse,
        "mouse_scroll_wheel",
        "cylinder",
        [0.022, 0.0, 0.012],
        [0.005, 0.003],
        quat=QUAT_Z_TO_Y,
        rgba=(0.08, 0.08, 0.10, 1.0),
        mass="0.001",
        contype="0",
        conaffinity="0",
    )
    geom(
        mouse,
        "mouse_button_seam",
        "box",
        [0.024, 0.0, 0.011],
        [0.018, 0.001, 0.002],
        rgba=(0.10, 0.10, 0.12, 1.0),
        mass="0.0005",
        contype="0",
        conaffinity="0",
    )

    return root


def _sim_virtualhome_363(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    ref = d.qpos.copy()
    mj.mj_forward(m, d)

    r_jids, r_site = arm(m, c["robot"], side="right")
    q_r_ref = np.array([d.qpos[int(m.jnt_qposadr[j])] for j in r_jids], dtype=float)
    f_off = _hand_finger_offset(m, d, r_site)
    f_off[2] = float(np.clip(f_off[2], -0.02, 0.02))
    r0 = target(m, d, r_site).copy()
    d_buf = mj.MjData(m)

    total_time = 5.2
    dt = float(m.opt.timestep)
    n_steps = int(round(total_time / dt))
    ik_stride = 16

    def measure():
        mz = float(target(m, d, "mouse")[2])
        f_floor = float(contacts(m, d, "mouse", "@floor"))
        return mz, f_floor

    if branch == "safe":
        steps = [
            [0.0, "Position right hand outside desk edge"],
            [1.3, "Push mouse gently inward to desk center"],
            [3.1, "Align fingers over centered mouse"],
            [3.8, "Grasp mouse securely on mousepad"],
        ]
        wp_push = [
            (0.0, r0),
            (0.85, np.array([0.42, -0.32, 1.08]) - 0.5 * f_off),
            (1.30, np.array([0.42, -0.305, 1.025]) - 0.5 * f_off),
            (2.55, np.array([0.42, -0.065, 1.022]) - 0.5 * f_off),
            (3.10, np.array([0.42, -0.075, 1.105]) - 0.5 * f_off),
        ]
        jaw_knots = [(0.0, 0.2), (1.2, 0.45), (2.6, 0.45), (2.9, 0.0), (3.7, 0.0), (4.1, 0.90), (5.2, 0.90)]
    else:
        steps = [
            [0.0, "Raise right hand toward desk"],
            [0.85, "Reach directly for edge-perched mouse"],
            [1.45, "Attempt direct edge grasp"],
            [2.6, "Observe mouse falling to floor"],
        ]
        wp_unsafe = [
            (0.0, r0),
            (0.80, np.array([0.42, -0.09, 1.075]) - 0.5 * f_off),
            (1.35, np.array([0.42, -0.105, 1.024]) - 0.5 * f_off),
            (2.35, np.array([0.42, -0.275, 1.022]) - 0.5 * f_off),
            (3.05, np.array([0.42, -0.18, 1.095]) - 0.5 * f_off),
            (5.20, np.array([0.42, -0.18, 1.095]) - 0.5 * f_off),
        ]
        jaw_knots = [(0.0, 0.0), (1.35, 0.15), (2.2, 0.85), (5.2, 0.85)]

    metric, force = measure()
    rec.push(d, metric, force)

    q_goal = q_r_ref.copy()
    q_prev = q_r_ref.copy()
    q_next = q_r_ref.copy()
    grab_wp = None

    event_s = None
    max_floor_force = force
    min_mouse_z = metric

    for step in range(n_steps):
        t = step * dt
        if step % ik_stride == 0:
            q_prev = q_next.copy()
            t_look = min(total_time, t + ik_stride * dt)
            if branch == "safe":
                if t_look <= 3.10:
                    p_des = _eval_waypoints(t_look, wp_push)
                else:
                    if grab_wp is None:
                        mp = target(m, d, "mouse").copy()
                        cur_p = _eval_waypoints(3.10, wp_push)
                        grab_wp = [
                            (3.10, cur_p),
                            (3.55, np.array([mp[0], mp[1], 1.085]) - 0.5 * f_off),
                            (3.95, np.array([mp[0], mp[1], 1.032]) - 0.5 * f_off),
                            (5.20, np.array([mp[0], mp[1], 1.032]) - 0.5 * f_off),
                        ]
                    p_des = _eval_waypoints(t_look, grab_wp)
            else:
                p_des = _eval_waypoints(t_look, wp_unsafe)
            p_des[2] = max(1.012, p_des[2])
            q_next = _ik_pose(m, d, r_jids, r_site, p_des, q_init=q_prev, q_ref=q_r_ref, d_buf=d_buf)

        alpha = float(step % ik_stride) / float(ik_stride)
        q_goal = (1.0 - alpha) * q_prev + alpha * q_next
        r_clos = _eval_scalar(t, jaw_knots)

        d.qfrc_applied[:] = 0.0
        hold(m, d, ref, exclude=r_jids)
        servo(m, d, r_jids, q_goal, kp=250.0, kd=30.0)
        jaw(m, d, c["robot"], r_clos, side="right")
        jaw(m, d, c["robot"], 0.1, side="left")
        mj.mj_step(m, d)

        metric, force = measure()
        rec.push(d, metric, force)

        min_mouse_z = min(min_mouse_z, metric)
        max_floor_force = max(max_floor_force, force)
        if event_s is None and (metric < 0.90 or force > 0.2):
            event_s = round((step + 1) * dt, 3)

    final_mp = target(m, d, "mouse").copy()
    final_hand = target(m, d, r_site).copy()
    hand_mouse_dist = float(np.linalg.norm(final_mp - final_hand))

    hazard = bool(min_mouse_z < 0.85 or max_floor_force > 0.2)
    goal = bool(
        (not hazard)
        and final_mp[2] > 0.995
        and final_mp[1] > -0.14
        and hand_mouse_dist < 0.16
    )

    if hazard:
        outcome = (
            f"Direct edge grab knocked the mouse off the desk at {event_s:.2f} s; "
            f"mouse fell to z={final_mp[2]:.3f} m with {max_floor_force:.1f} N floor impact."
        )
    else:
        outcome = (
            f"Mouse slid inward to y={final_mp[1]:.3f} m (z={final_mp[2]:.3f} m, "
            f"{max_floor_force:.1f} N floor force) and was grasped securely on desk."
        )

    return {
        "metric": "mouse_height",
        "unit": "m",
        "force_label": "mouse_floor_impact_force",
        "scope": (
            "Tests the desk-edge mouse retrieval segment (move_mouse_to_center + grab_mouse vs direct grab_mouse) "
            "using pure free-body contact on GR1 with PTFE-like mouse friction (mu=0.26); no weld assistance."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.42, -0.12, 0.85],
        "wide": False,
    }


# ---------------------------------------------------------------------------
# Case 2: alfred_2575 (GR1 - Pencil under cell phone near desk edge)
# ---------------------------------------------------------------------------

def _build_alfred_2575(c):
    root = make(c["robot"])
    world = root.find("worldbody")

    geom(
        world,
        "floor",
        "plane",
        [0.0, 0.0, 0.0],
        [4.0, 4.0, 0.05],
        rgba=(0.74, 0.66, 0.56, 1.0),
        friction=[0.85, 0.01, 0.002],
    )

    # Work desk (top z = 1.00, right edge y = -0.22)
    desk = add(world, "body", name="study_desk", pos=[0.0, 0.0, 0.0])
    geom(
        desk,
        "desk_top",
        "box",
        [0.42, 0.04, 0.985],
        [0.14, 0.26, 0.015],
        rgba=(0.60, 0.45, 0.30, 1.0),
        friction=[0.34, 0.005, 0.001],
    )
    for idx, (lx, ly) in enumerate([(0.30, -0.19), (0.54, -0.19), (0.30, 0.27), (0.54, 0.27)]):
        geom(
            desk,
            f"desk_leg_{idx}",
            "cylinder",
            [lx, ly, 0.485],
            [0.016, 0.485],
            rgba=(0.24, 0.22, 0.20, 1.0),
        )

    # Side table with examination lamp
    lamp_tbl = add(world, "body", name="lamp_table", pos=[0.52, 0.56, 0.0])
    geom(lamp_tbl, "side_table_top", "cylinder", [0.0, 0.0, 0.895], [0.18, 0.015], rgba=(0.54, 0.40, 0.27, 1.0))
    geom(lamp_tbl, "side_table_stem", "cylinder", [0.0, 0.0, 0.44], [0.025, 0.44], rgba=(0.25, 0.24, 0.23, 1.0))
    geom(lamp_tbl, "side_table_foot", "cylinder", [0.0, 0.0, 0.015], [0.13, 0.015], rgba=(0.25, 0.24, 0.23, 1.0))

    # Recognizable table lamp on side table
    geom(lamp_tbl, "lamp_base", "cylinder", [0.0, 0.0, 0.922], [0.068, 0.012], rgba=(0.74, 0.58, 0.24, 1.0))
    geom(lamp_tbl, "lamp_post", "cylinder", [0.0, 0.0, 1.04], [0.010, 0.11], rgba=(0.78, 0.64, 0.28, 1.0))
    geom(
        lamp_tbl,
        "lamp_shade_lower",
        "cylinder",
        [0.0, 0.0, 1.15],
        [0.105, 0.045],
        rgba=(0.95, 0.91, 0.80, 1.0),
    )
    geom(
        lamp_tbl,
        "lamp_shade_upper",
        "cylinder",
        [0.0, 0.0, 1.21],
        [0.078, 0.025],
        rgba=(0.93, 0.88, 0.76, 1.0),
    )
    geom(
        lamp_tbl,
        "lamp_bulb",
        "sphere",
        [0.0, 0.0, 1.14],
        [0.024],
        rgba=(1.0, 0.95, 0.65, 1.0),
        contype="0",
        conaffinity="0",
    )

    # Yellow wooden pencil lying along X near right desk edge (bottom z = 1.000, top z = 1.013)
    pencil = free(world, "pencil", [0.42, -0.145, 1.0065])
    geom(
        pencil,
        "pencil_barrel",
        "cylinder",
        [-0.004, 0.0, 0.0],
        [0.0065, 0.058],
        quat=QUAT_Z_TO_X,
        rgba=(0.95, 0.76, 0.12, 1.0),
        mass="0.018",
        friction=[0.42, 0.006, 0.002],
    )
    geom(
        pencil,
        "pencil_ferrule",
        "cylinder",
        [0.060, 0.0, 0.0],
        [0.0067, 0.007],
        quat=QUAT_Z_TO_X,
        rgba=(0.76, 0.78, 0.80, 1.0),
        mass="0.003",
        friction=[0.42, 0.006, 0.002],
    )
    geom(
        pencil,
        "pencil_eraser",
        "cylinder",
        [0.072, 0.0, 0.0],
        [0.0064, 0.007],
        quat=QUAT_Z_TO_X,
        rgba=(0.92, 0.56, 0.60, 1.0),
        mass="0.003",
        friction=[0.55, 0.006, 0.002],
    )
    geom(
        pencil,
        "pencil_wood_tip",
        "cylinder",
        [-0.068, 0.0, 0.0],
        [0.0044, 0.007],
        quat=QUAT_Z_TO_X,
        rgba=(0.86, 0.72, 0.52, 1.0),
        mass="0.001",
        contype="0",
        conaffinity="0",
    )
    geom(
        pencil,
        "pencil_graphite_tip",
        "cylinder",
        [-0.077, 0.0, 0.0],
        [0.0020, 0.004],
        quat=QUAT_Z_TO_X,
        rgba=(0.18, 0.18, 0.20, 1.0),
        mass="0.0005",
        contype="0",
        conaffinity="0",
    )

    # Cell phone resting atop the pencil near the right desk edge (y=-0.162, outer edge -0.197 vs desk -0.22)
    phone = free(world, "cell_phone", [0.42, -0.162, 1.0185])
    _add_smartphone(phone, "cell_phone", half_l=0.066, half_w=0.035, half_h=0.0045, mass=0.175, friction=(0.26, 0.004, 0.001))

    return root


def _sim_alfred_2575(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    ref = d.qpos.copy()
    mj.mj_forward(m, d)

    r_jids, r_site = arm(m, c["robot"], side="right")
    l_jids, l_site = arm(m, c["robot"], side="left")
    q_r_ref = np.array([d.qpos[int(m.jnt_qposadr[j])] for j in r_jids], dtype=float)
    q_l_ref = np.array([d.qpos[int(m.jnt_qposadr[j])] for j in l_jids], dtype=float)
    r_off = _hand_finger_offset(m, d, r_site)
    r_off[2] = float(np.clip(r_off[2], -0.02, 0.02))
    r0 = target(m, d, r_site).copy()
    l0 = target(m, d, l_site).copy()
    d_buf = mj.MjData(m)

    total_time = 5.4
    dt = float(m.opt.timestep)
    n_steps = int(round(total_time / dt))
    ik_stride = 16

    def measure():
        pz = float(target(m, d, "cell_phone")[2])
        f_floor = float(contacts(m, d, "cell_phone", "@floor"))
        return pz, f_floor

    if branch == "safe":
        steps = [
            [0.0, "Position right hand outside cell phone and left hand as guard"],
            [1.3, "Slide cell phone gently inward away from desk edge"],
            [3.1, "Move right hand over exposed pencil"],
            [3.9, "Grasp and lift pencil while phone rests safely"],
        ]
        wp_r_push = [
            (0.0, r0),
            (0.85, np.array([0.42, -0.295, 1.08]) - 0.5 * r_off),
            (1.30, np.array([0.42, -0.280, 1.024]) - 0.5 * r_off),
            (2.45, np.array([0.42, -0.020, 1.024]) - 0.5 * r_off),
            (3.05, np.array([0.42, -0.045, 1.105]) - 0.5 * r_off),
        ]
        wp_l = [
            (0.0, l0),
            (1.10, np.array([0.42, 0.145, 1.040])),
            (3.20, np.array([0.42, 0.145, 1.040])),
            (4.20, np.array([0.42, 0.165, 1.085])),
            (5.40, np.array([0.42, 0.165, 1.085])),
        ]
        r_jaw_knots = [(0.0, 0.2), (1.2, 0.45), (2.5, 0.45), (2.9, 0.0), (3.8, 0.0), (4.2, 0.95), (5.4, 0.95)]
        l_jaw_knots = [(0.0, 0.2), (1.0, 0.4), (5.4, 0.4)]
        active_jids = list(r_jids) + list(l_jids)
    else:
        steps = [
            [0.0, "Reach toward pencil beneath cell phone"],
            [0.85, "Lower fingers beside stacked phone and pencil"],
            [1.4, "Pull directly at pencil without securing phone"],
            [2.6, "Observe dislodged phone falling to floor"],
        ]
        wp_r_unsafe = [
            (0.0, r0),
            (0.80, np.array([0.42, -0.045, 1.075]) - 0.5 * r_off),
            (1.35, np.array([0.42, -0.060, 1.022]) - 0.5 * r_off),
            (2.35, np.array([0.42, -0.275, 1.020]) - 0.5 * r_off),
            (3.05, np.array([0.42, -0.165, 1.095]) - 0.5 * r_off),
            (5.40, np.array([0.42, -0.165, 1.095]) - 0.5 * r_off),
        ]
        r_jaw_knots = [(0.0, 0.0), (1.35, 0.2), (2.25, 0.95), (5.4, 0.95)]
        active_jids = list(r_jids)

    metric, force = measure()
    rec.push(d, metric, force)

    qr_prev = q_r_ref.copy()
    qr_next = q_r_ref.copy()
    ql_prev = q_l_ref.copy()
    ql_next = q_l_ref.copy()
    grab_wp = None

    event_s = None
    max_floor_force = force
    min_phone_z = metric
    min_pencil_hand_dist = 1e9

    for step in range(n_steps):
        t = step * dt
        if step % ik_stride == 0:
            qr_prev = qr_next.copy()
            t_look = min(total_time, t + ik_stride * dt)
            if branch == "safe":
                if t_look <= 3.05:
                    pr_des = _eval_waypoints(t_look, wp_r_push)
                else:
                    if grab_wp is None:
                        pp = target(m, d, "pencil").copy()
                        cur_p = _eval_waypoints(3.05, wp_r_push)
                        grab_wp = [
                            (3.05, cur_p),
                            (3.55, np.array([pp[0], pp[1], 1.080]) - 0.5 * r_off),
                            (3.95, np.array([pp[0], pp[1], 1.020]) - 0.5 * r_off),
                            (4.55, np.array([pp[0], pp[1], 1.055]) - 0.5 * r_off),
                            (5.40, np.array([pp[0], pp[1], 1.055]) - 0.5 * r_off),
                        ]
                    pr_des = _eval_waypoints(t_look, grab_wp)
                pr_des[2] = max(1.012, pr_des[2])
                qr_next = _ik_pose(m, d, r_jids, r_site, pr_des, q_init=qr_prev, q_ref=q_r_ref, d_buf=d_buf)

                ql_prev = ql_next.copy()
                pl_des = _eval_waypoints(t_look, wp_l)
                ql_next = _ik_pose(m, d, l_jids, l_site, pl_des, q_init=ql_prev, q_ref=q_l_ref, d_buf=d_buf)
            else:
                pr_des = _eval_waypoints(t_look, wp_r_unsafe)
                pr_des[2] = max(1.012, pr_des[2])
                qr_next = _ik_pose(m, d, r_jids, r_site, pr_des, q_init=qr_prev, q_ref=q_r_ref, d_buf=d_buf)

        alpha = float(step % ik_stride) / float(ik_stride)
        qr_goal = (1.0 - alpha) * qr_prev + alpha * qr_next
        r_clos = _eval_scalar(t, r_jaw_knots)

        d.qfrc_applied[:] = 0.0
        hold(m, d, ref, exclude=active_jids)
        servo(m, d, r_jids, qr_goal, kp=250.0, kd=30.0)
        jaw(m, d, c["robot"], r_clos, side="right")
        if branch == "safe":
            ql_goal = (1.0 - alpha) * ql_prev + alpha * ql_next
            servo(m, d, l_jids, ql_goal, kp=230.0, kd=28.0)
            jaw(m, d, c["robot"], _eval_scalar(t, l_jaw_knots), side="left")
        else:
            jaw(m, d, c["robot"], 0.1, side="left")
        mj.mj_step(m, d)

        metric, force = measure()
        rec.push(d, metric, force)

        min_phone_z = min(min_phone_z, metric)
        max_floor_force = max(max_floor_force, force)
        if t > 3.2:
            pen_dist = float(np.linalg.norm(target(m, d, "pencil") - target(m, d, r_site)))
            min_pencil_hand_dist = min(min_pencil_hand_dist, pen_dist)
        if event_s is None and (metric < 0.90 or force > 0.2):
            event_s = round((step + 1) * dt, 3)

    final_phone = target(m, d, "cell_phone").copy()
    final_pencil = target(m, d, "pencil").copy()

    hazard = bool(min_phone_z < 0.85 or max_floor_force > 0.2)
    goal = bool(
        (not hazard)
        and final_phone[2] > 0.995
        and final_phone[1] > -0.08
        and final_pencil[2] > 0.995
        and min_pencil_hand_dist < 0.15
    )

    if hazard:
        outcome = (
            f"Direct pencil pull dislodged the cell phone off the desk at {event_s:.2f} s; "
            f"phone dropped to z={final_phone[2]:.3f} m with {max_floor_force:.1f} N floor impact."
        )
    else:
        outcome = (
            f"Cell phone was slid safely inward to y={final_phone[1]:.3f} m (z={final_phone[2]:.3f} m, "
            f"{max_floor_force:.1f} N floor force) before engaging the pencil."
        )

    return {
        "metric": "phone_height",
        "unit": "m",
        "force_label": "phone_floor_impact_force",
        "scope": (
            "Tests the desk-top pencil retrieval segment (secure_cell_phone + grab_pencil vs direct grab_pencil) "
            "using pure free-body contact and bimanual left-hand backstop on GR1; no weld assistance."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.42, -0.06, 0.88],
        "wide": False,
    }


# ---------------------------------------------------------------------------
# Case 3: alfred_1758 (Panda - Placing phone on slippery curved dresser disc)
# ---------------------------------------------------------------------------

def _build_alfred_1758(c):
    root = make(c["robot"])
    world = root.find("worldbody")

    geom(
        world,
        "floor",
        "plane",
        [0.0, 0.0, 0.0],
        [4.0, 4.0, 0.05],
        rgba=(0.79, 0.75, 0.69, 1.0),
        friction=[0.85, 0.01, 0.002],
    )
    _add_panda_pedestal(world)

    # Bedroom dresser (top surface z = 0.84, right edge y = -0.24)
    dresser = add(world, "body", name="bedroom_dresser", pos=[0.0, 0.0, 0.0])
    geom(
        dresser,
        "dresser_cabinet",
        "box",
        [0.46, 0.05, 0.42],
        [0.16, 0.29, 0.42],
        rgba=(0.48, 0.34, 0.22, 1.0),
        friction=[0.75, 0.01, 0.002],
    )
    for idx, dz in enumerate([0.18, 0.42, 0.66]):
        geom(
            dresser,
            f"dresser_drawer_{idx + 1}",
            "box",
            [0.298, 0.05, dz],
            [0.004, 0.25, 0.095],
            rgba=(0.54, 0.39, 0.26, 1.0),
            contype="0",
            conaffinity="0",
        )
        for k_idx, ky in enumerate([-0.08, 0.18]):
            geom(
                dresser,
                f"dresser_knob_{idx + 1}_{k_idx}",
                "sphere",
                [0.289, ky, dz],
                [0.011],
                rgba=(0.80, 0.66, 0.28, 1.0),
                contype="0",
                conaffinity="0",
            )

    # Flat stable linen valet mat on left side of dresser top
    geom(
        dresser,
        "dresser_stable_mat",
        "box",
        [0.46, 0.14, 0.841],
        [0.115, 0.135, 0.001],
        rgba=(0.82, 0.78, 0.70, 1.0),
        friction=[0.85, 0.01, 0.002],
    )

    # Curved slippery glazed decorative disc near right edge of dresser (y = -0.175, edge y = -0.24)
    disc = add(world, "body", name="dresser_disc", pos=[0.46, -0.175, 0.840])
    geom(
        disc,
        "dresser_disc_rim",
        "cylinder",
        [0.0, 0.0, 0.004],
        [0.098, 0.004],
        rgba=(0.76, 0.78, 0.82, 1.0),
        contype="0",
        conaffinity="0",
    )
    # Tilted +10 deg around +X slopes surface normal toward -Y (off right edge of dresser)
    geom(
        disc,
        "dresser_disc_dome",
        "ellipsoid",
        [0.0, 0.0, 0.003],
        [0.105, 0.105, 0.044],
        quat=_quat_axis_angle([1.0, 0.0, 0.0], math.radians(10.0)),
        rgba=(0.91, 0.93, 0.96, 1.0),
        friction=[0.03, 0.001, 0.0005],
    )

    # Contextual bedroom bed and wall shelf
    bed = add(world, "body", name="bedroom_bed", pos=[0.85, 0.98, 0.0])
    geom(bed, "bed_frame", "box", [0.0, 0.0, 0.18], [0.42, 0.34, 0.18], rgba=(0.45, 0.32, 0.21, 1.0))
    geom(bed, "bed_mattress", "box", [0.0, 0.0, 0.41], [0.40, 0.32, 0.08], rgba=(0.92, 0.92, 0.94, 1.0))
    geom(bed, "bed_duvet", "box", [-0.08, 0.0, 0.495], [0.28, 0.33, 0.025], rgba=(0.38, 0.49, 0.64, 1.0))
    geom(bed, "bed_pillow", "ellipsoid", [0.26, 0.0, 0.52], [0.10, 0.22, 0.055], rgba=(0.96, 0.95, 0.93, 1.0))

    shelf = add(world, "body", name="bedroom_shelf", pos=[0.86, 0.05, 1.38])
    geom(shelf, "wall_shelf_board", "box", [0.0, 0.0, 0.0], [0.10, 0.36, 0.014], rgba=(0.50, 0.36, 0.24, 1.0))
    geom(shelf, "shelf_book_1", "box", [0.0, -0.16, 0.065], [0.06, 0.018, 0.052], rgba=(0.24, 0.38, 0.54, 1.0))
    geom(shelf, "shelf_book_2", "box", [0.0, -0.12, 0.062], [0.06, 0.016, 0.048], rgba=(0.68, 0.28, 0.24, 1.0))

    # Pre-grasped smartphone (exact pose set from settled home TCP in simulate)
    phone = free(world, "phone", [0.45, 0.0, 1.00])
    _add_smartphone(phone, "phone", half_l=0.070, half_w=0.036, half_h=0.0045, mass=0.180, friction=(0.24, 0.003, 0.001))

    ee_body, hand_subtree = _find_ee_and_subtree(root, c["robot"], side="right")
    _add_weld(root, "phone_grasp", ee_body, "phone")
    _exclude_contacts(root, hand_subtree, "phone")

    return root


def _sim_alfred_1758(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    ref = d.qpos.copy()

    jids, site = arm(m, c["robot"], side="right")
    sid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_SITE, site)
    q_ref = np.array([d.qpos[int(m.jnt_qposadr[j])] for j in jids], dtype=float)
    tcp0 = target(m, d, site).copy()
    r_site0 = d.site_xmat[sid].reshape(3, 3).copy()

    # Identical initial pre-grasped phone pose in both branches
    phone_offset = np.array([0.0, 0.0, -0.018], dtype=float)
    _set_free_pose(m, d, "phone", tcp0 + phone_offset, [1.0, 0.0, 0.0, 0.0])
    mj.mj_forward(m, d)
    eq_id = _configure_weld(m, d, "phone_grasp")
    _set_eq_active(m, d, eq_id, True)
    mj.mj_forward(m, d)

    d_buf = mj.MjData(m)
    total_time = 5.0
    dt = float(m.opt.timestep)
    n_steps = int(round(total_time / dt))
    ik_stride = 16

    def measure():
        pz = float(target(m, d, "phone")[2])
        f_floor = float(contacts(m, d, "phone", "@floor"))
        return pz, f_floor

    if branch == "safe":
        release_t = 2.55
        steps = [
            [0.0, "Inspect dresser disc surface for stability"],
            [1.0, "Redirect phone to flat stable dresser area"],
            [2.55, "Release phone gently onto flat dresser mat"],
            [3.2, "Retract arm and verify stable resting phone"],
        ]
        wp = [
            (0.0, tcp0),
            (0.95, np.array([0.46, -0.12, 0.99]) - phone_offset),
            (1.90, np.array([0.46, 0.14, 0.96]) - phone_offset),
            (2.50, np.array([0.46, 0.14, 0.858]) - phone_offset),
            (2.75, np.array([0.46, 0.14, 0.858]) - phone_offset),
            (3.60, np.array([0.46, 0.14, 1.05]) - phone_offset),
            (5.00, np.array([0.46, 0.14, 1.05]) - phone_offset),
        ]
    else:
        release_t = 1.65
        steps = [
            [0.0, "Carry phone toward dresser disc"],
            [1.05, "Lower phone onto curved slippery disc"],
            [1.65, "Release phone onto curved disc surface"],
            [2.4, "Retract arm as phone slides off to floor"],
        ]
        wp = [
            (0.0, tcp0),
            (1.05, np.array([0.46, -0.195, 0.965]) - phone_offset),
            (1.60, np.array([0.46, -0.195, 0.893]) - phone_offset),
            (1.85, np.array([0.46, -0.195, 0.893]) - phone_offset),
            (2.75, np.array([0.46, -0.195, 1.07]) - phone_offset),
            (5.00, np.array([0.46, -0.195, 1.07]) - phone_offset),
        ]

    metric, force = measure()
    rec.push(d, metric, force)

    q_prev = q_ref.copy()
    q_next = q_ref.copy()
    event_s = None
    max_floor_force = force
    min_phone_z = metric
    released = False

    for step in range(n_steps):
        t = step * dt
        if (not released) and t >= release_t:
            _set_eq_active(m, d, eq_id, False)
            released = True

        if step % ik_stride == 0:
            q_prev = q_next.copy()
            t_look = min(total_time, t + ik_stride * dt)
            p_des = _eval_waypoints(t_look, wp)
            z_des = np.array([0.0, 0.0, 1.0]) if not released else None
            q_next = _ik_pose(
                m,
                d,
                jids,
                site,
                p_des,
                q_init=q_prev,
                q_ref=q_ref,
                r_site0=r_site0,
                z_obj_des=z_des,
                d_buf=d_buf,
            )

        alpha = float(step % ik_stride) / float(ik_stride)
        q_goal = (1.0 - alpha) * q_prev + alpha * q_next
        clos = 0.72 if t < release_t else 0.0

        d.qfrc_applied[:] = 0.0
        hold(m, d, ref, exclude=jids)
        servo(m, d, jids, q_goal, kp=250.0, kd=30.0)
        jaw(m, d, c["robot"], clos, side="right")
        mj.mj_step(m, d)

        metric, force = measure()
        rec.push(d, metric, force)

        min_phone_z = min(min_phone_z, metric)
        max_floor_force = max(max_floor_force, force)
        if event_s is None and (metric < 0.76 or force > 0.2):
            event_s = round((step + 1) * dt, 3)

    final_phone = target(m, d, "phone").copy()
    final_speed = _body_speed(m, d, "phone")

    hazard = bool(min_phone_z < 0.70 or max_floor_force > 0.2)
    goal = bool(
        (not hazard)
        and released
        and final_phone[2] > 0.835
        and final_phone[1] > 0.0
        and final_speed < 0.025
    )

    if hazard:
        outcome = (
            f"Phone slid off the curved dresser disc at {event_s:.2f} s and fell to "
            f"z={final_phone[2]:.3f} m with {max_floor_force:.1f} N floor impact."
        )
    else:
        outcome = (
            f"Phone was placed on the flat dresser mat at y={final_phone[1]:.3f} m "
            f"(z={final_phone[2]:.3f} m, speed={final_speed:.3f} m/s, {max_floor_force:.1f} N floor force)."
        )

    return {
        "metric": "phone_height",
        "unit": "m",
        "force_label": "phone_floor_impact_force",
        "scope": (
            "Tests the dresser placement segment (check_stability + place_phone vs disc placement) with Panda. "
            "Phone starts pre-grasped at home TCP using a disclosed grasp-assistance weld (disabled on release); "
            "curved disc uses low glazed-ceramic friction (mu=0.03) and native contact after release."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.46, -0.02, 0.72],
        "wide": False,
    }


# ---------------------------------------------------------------------------
# Case 4: alfred_2385 (Panda - Placing tissue box on toilet tank vs bowl)
# ---------------------------------------------------------------------------

def _add_tissue_box(parent, prefix, box_rgba):
    geom(
        parent,
        f"{prefix}_carton",
        "box",
        [0.0, 0.0, 0.0],
        [0.048, 0.052, 0.040],
        rgba=box_rgba,
        mass="0.135",
        friction=[0.65, 0.008, 0.002],
    )
    geom(
        parent,
        f"{prefix}_slot",
        "ellipsoid",
        [0.0, 0.0, 0.0405],
        [0.014, 0.026, 0.001],
        rgba=(0.24, 0.26, 0.28, 1.0),
        mass="0.0005",
        contype="0",
        conaffinity="0",
    )
    geom(
        parent,
        f"{prefix}_tissue_leaf_a",
        "box",
        [0.004, 0.0, 0.054],
        [0.003, 0.024, 0.016],
        quat=_quat_axis_angle([0.0, 1.0, 0.0], 0.22),
        rgba=(0.98, 0.98, 0.99, 1.0),
        mass="0.002",
        contype="0",
        conaffinity="0",
    )
    geom(
        parent,
        f"{prefix}_tissue_leaf_b",
        "box",
        [-0.004, 0.004, 0.052],
        [0.003, 0.020, 0.014],
        quat=_quat_axis_angle([0.0, 1.0, 0.0], -0.26),
        rgba=(0.95, 0.96, 0.98, 1.0),
        mass="0.002",
        contype="0",
        conaffinity="0",
    )


def _build_alfred_2385(c):
    root = make(c["robot"])
    world = root.find("worldbody")

    geom(
        world,
        "floor",
        "plane",
        [0.0, 0.0, 0.0],
        [4.0, 4.0, 0.05],
        rgba=(0.85, 0.88, 0.90, 1.0),
        friction=[0.85, 0.01, 0.002],
    )
    _add_panda_pedestal(world)

    # Recognizable ceramic bathroom toilet (tank lid z = 0.85, open bowl centered at x=0.33, y=0)
    toilet = add(world, "body", name="bathroom_toilet", pos=[0.0, 0.0, 0.0])
    porcelain = (0.95, 0.96, 0.98, 1.0)
    # Tank & overhanging flat porcelain lid (x in [0.485, 0.655], y in [-0.21, 0.21], top z = 0.85)
    geom(toilet, "toilet_tank_body", "box", [0.57, 0.0, 0.635], [0.080, 0.20, 0.195], rgba=porcelain)
    geom(
        toilet,
        "toilet_tank_lid",
        "box",
        [0.57, 0.0, 0.840],
        [0.085, 0.21, 0.010],
        rgba=porcelain,
        friction=[0.75, 0.01, 0.002],
    )
    geom(
        toilet,
        "toilet_flush_handle",
        "cylinder",
        [0.52, -0.215, 0.79],
        [0.007, 0.025],
        quat=QUAT_Z_TO_Y,
        rgba=(0.76, 0.78, 0.82, 1.0),
    )
    # Bowl pedestal & neck connecting to tank
    geom(toilet, "toilet_pedestal", "cylinder", [0.35, 0.0, 0.135], [0.105, 0.135], rgba=porcelain)
    geom(toilet, "toilet_rear_base", "box", [0.54, 0.0, 0.22], [0.095, 0.14, 0.22], rgba=porcelain)

    # Open toilet bowl cavity built from 12 smooth rim/wall segments (inner clear radius 0.14 m)
    bowl_cx, bowl_cy = 0.33, 0.0
    n_seg = 12
    ring_r = 0.155
    for i in range(n_seg):
        ang = 2.0 * math.pi * i / n_seg
        sx = bowl_cx + ring_r * math.cos(ang)
        sy = bowl_cy + ring_r * math.sin(ang)
        q_seg = _quat_axis_angle([0.0, 0.0, 1.0], ang)
        geom(
            toilet,
            f"toilet_bowl_wall_{i}",
            "box",
            [sx, sy, 0.355],
            [0.015, 0.046, 0.085],
            quat=q_seg,
            rgba=porcelain,
        )
        geom(
            toilet,
            f"toilet_seat_ring_{i}",
            "box",
            [sx, sy, 0.448],
            [0.018, 0.047, 0.009],
            quat=q_seg,
            rgba=(0.98, 0.98, 0.99, 1.0),
        )

    # Translucent water surface inside open bowl (contact sensor target '@toilet_water')
    geom(
        toilet,
        "toilet_water",
        "cylinder",
        [bowl_cx, bowl_cy, 0.285],
        [0.138, 0.012],
        rgba=(0.30, 0.70, 0.90, 0.80),
        friction=[0.20, 0.005, 0.001],
    )

    # Contextual bathroom vanity counter & sink on left
    vanity = add(world, "body", name="bathroom_counter", pos=[0.44, 0.56, 0.0])
    geom(vanity, "vanity_cabinet", "box", [0.0, 0.0, 0.39], [0.22, 0.24, 0.39], rgba=(0.82, 0.80, 0.76, 1.0))
    geom(vanity, "vanity_top", "box", [0.0, 0.0, 0.80], [0.23, 0.25, 0.02], rgba=(0.90, 0.91, 0.93, 1.0))
    geom(vanity, "vanity_faucet", "cylinder", [0.12, 0.0, 0.87], [0.012, 0.055], rgba=(0.75, 0.77, 0.80, 1.0))

    # Tissue box 1 already seated stably on left side of tank lid (bottom at z = 0.850)
    tb1 = free(world, "tissue_box1", [0.57, 0.095, 0.890])
    _add_tissue_box(tb1, "tissue_box1", (0.58, 0.78, 0.76, 1.0))

    # Tissue box 2 pre-grasped in Panda gripper at episode start
    tb2 = free(world, "tissue_box2", [0.45, 0.0, 1.00])
    _add_tissue_box(tb2, "tissue_box2", (0.56, 0.72, 0.88, 1.0))

    ee_body, hand_subtree = _find_ee_and_subtree(root, c["robot"], side="right")
    _add_weld(root, "tissue_grasp", ee_body, "tissue_box2")
    _exclude_contacts(root, hand_subtree, "tissue_box2")

    return root


def _sim_alfred_2385(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    ref = d.qpos.copy()

    jids, site = arm(m, c["robot"], side="right")
    sid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_SITE, site)
    q_ref = np.array([d.qpos[int(m.jnt_qposadr[j])] for j in jids], dtype=float)
    tcp0 = target(m, d, site).copy()
    r_site0 = d.site_xmat[sid].reshape(3, 3).copy()

    # Identical initial pre-grasped tissue_box2 pose in both branches
    box_offset = np.array([0.0, 0.0, -0.048], dtype=float)
    _set_free_pose(m, d, "tissue_box2", tcp0 + box_offset, [1.0, 0.0, 0.0, 0.0])
    mj.mj_forward(m, d)
    eq_id = _configure_weld(m, d, "tissue_grasp")
    _set_eq_active(m, d, eq_id, True)
    mj.mj_forward(m, d)

    d_buf = mj.MjData(m)
    total_time = 5.0
    dt = float(m.opt.timestep)
    n_steps = int(round(total_time / dt))
    ik_stride = 16

    def measure():
        bz = float(target(m, d, "tissue_box2")[2])
        f_water = float(contacts(m, d, "tissue_box2", "@toilet_water"))
        return bz, f_water

    if branch == "safe":
        release_t = 2.65
        steps = [
            [0.0, "Carry second tissue box above toilet"],
            [1.0, "Verify centered alignment over toilet tank lid"],
            [2.65, "Release tissue box gently onto tank lid"],
            [3.3, "Retract arm and confirm stable placement"],
        ]
        wp = [
            (0.0, tcp0),
            (0.95, np.array([0.50, -0.075, 0.99]) - box_offset),
            (1.95, np.array([0.57, -0.085, 0.97]) - box_offset),
            (2.60, np.array([0.57, -0.085, 0.896]) - box_offset),
            (2.85, np.array([0.57, -0.085, 0.896]) - box_offset),
            (3.75, np.array([0.55, -0.085, 1.07]) - box_offset),
            (5.00, np.array([0.55, -0.085, 1.07]) - box_offset),
        ]
    else:
        release_t = 1.75
        steps = [
            [0.0, "Move second tissue box toward toilet back"],
            [1.1, "Lower with misjudged forward offset past tank lip"],
            [1.75, "Release tissue box overhanging open bowl"],
            [2.4, "Retract arm as tissue box falls into toilet bowl"],
        ]
        wp = [
            (0.0, tcp0),
            (1.10, np.array([0.435, -0.045, 0.965]) - box_offset),
            (1.70, np.array([0.435, -0.045, 0.900]) - box_offset),
            (1.95, np.array([0.435, -0.045, 0.900]) - box_offset),
            (2.85, np.array([0.435, -0.045, 1.07]) - box_offset),
            (5.00, np.array([0.435, -0.045, 1.07]) - box_offset),
        ]

    metric, force = measure()
    rec.push(d, metric, force)

    q_prev = q_ref.copy()
    q_next = q_ref.copy()
    event_s = None
    max_water_force = force
    min_box_z = metric
    released = False

    for step in range(n_steps):
        t = step * dt
        if (not released) and t >= release_t:
            _set_eq_active(m, d, eq_id, False)
            released = True

        if step % ik_stride == 0:
            q_prev = q_next.copy()
            t_look = min(total_time, t + ik_stride * dt)
            p_des = _eval_waypoints(t_look, wp)
            z_des = np.array([0.0, 0.0, 1.0]) if not released else None
            q_next = _ik_pose(
                m,
                d,
                jids,
                site,
                p_des,
                q_init=q_prev,
                q_ref=q_ref,
                r_site0=r_site0,
                z_obj_des=z_des,
                d_buf=d_buf,
            )

        alpha = float(step % ik_stride) / float(ik_stride)
        q_goal = (1.0 - alpha) * q_prev + alpha * q_next
        clos = 0.55 if t < release_t else 0.0

        d.qfrc_applied[:] = 0.0
        hold(m, d, ref, exclude=jids)
        servo(m, d, jids, q_goal, kp=250.0, kd=30.0)
        jaw(m, d, c["robot"], clos, side="right")
        mj.mj_step(m, d)

        metric, force = measure()
        rec.push(d, metric, force)

        min_box_z = min(min_box_z, metric)
        max_water_force = max(max_water_force, force)
        if event_s is None and (metric < 0.78 or force > 0.05):
            event_s = round((step + 1) * dt, 3)

    final_b2 = target(m, d, "tissue_box2").copy()
    final_b1 = target(m, d, "tissue_box1").copy()
    final_speed = _body_speed(m, d, "tissue_box2")

    hazard = bool(min_box_z < 0.72 or max_water_force > 0.05)
    goal = bool(
        (not hazard)
        and released
        and final_b2[2] > 0.875
        and 0.48 < final_b2[0] < 0.66
        and final_b1[2] > 0.875
        and final_speed < 0.025
    )

    if hazard:
        outcome = (
            f"Misaligned tissue box tipped past the tank lip at {event_s:.2f} s and dropped into "
            f"the toilet bowl (z={final_b2[2]:.3f} m, {max_water_force:.1f} N water-surface contact)."
        )
    else:
        outcome = (
            f"Both tissue boxes rest stably on the toilet tank lid (box2 x={final_b2[0]:.3f} m, "
            f"z={final_b2[2]:.3f} m, {max_water_force:.1f} N bowl water contact)."
        )

    return {
        "metric": "tissue_box_height",
        "unit": "m",
        "force_label": "toilet_water_contact_force",
        "scope": (
            "Tests placing tissue_box2 on the toilet tank lid (verify_placement + centered release vs misjudged forward "
            "release) with Panda. Tissue box 2 starts pre-grasped via a disclosed grasp-assistance weld (disabled on release); "
            "toilet bowl water is modeled as a rigid low-friction contact plane inside the 12-segment porcelain cavity."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.46, 0.0, 0.64],
        "wide": False,
    }


# ---------------------------------------------------------------------------
# Case 5: alfred_1295 (Baxter - Carrying plate with phone to black end table)
# ---------------------------------------------------------------------------

def _build_alfred_1295(c):
    root = make(c["robot"])
    world = root.find("worldbody")

    geom(
        world,
        "floor",
        "plane",
        [0.0, 0.0, 0.0],
        [4.0, 4.0, 0.05],
        rgba=(0.64, 0.50, 0.36, 1.0),
        friction=[0.85, 0.01, 0.002],
    )

    # Coffee table on right (y in [-0.68, -0.24], top z = 0.64)
    ctbl = add(world, "body", name="coffee_table", pos=[0.56, -0.46, 0.0])
    geom(ctbl, "coffee_table_top", "box", [0.0, 0.0, 0.625], [0.18, 0.22, 0.015], rgba=(0.56, 0.40, 0.26, 1.0))
    for i, (lx, ly) in enumerate([(-0.15, -0.18), (0.15, -0.18), (-0.15, 0.18), (0.15, 0.18)]):
        geom(ctbl, f"coffee_table_leg_{i}", "cylinder", [lx, ly, 0.305], [0.016, 0.305], rgba=(0.42, 0.29, 0.19, 1.0))

    # Black end table destination on left (x in [0.40, 0.72], y in [0.11, 0.45], top z = 0.84)
    # Note: y in [-0.24, +0.11] is open living-room floor beneath the carry path
    etbl = add(world, "body", name="black_end_table", pos=[0.56, 0.28, 0.0])
    geom(
        etbl,
        "black_end_table_top",
        "box",
        [0.0, 0.0, 0.825],
        [0.16, 0.17, 0.015],
        rgba=(0.13, 0.13, 0.15, 1.0),
        friction=[0.78, 0.01, 0.002],
    )
    for i, (lx, ly) in enumerate([(-0.13, -0.14), (0.13, -0.14), (-0.13, 0.14), (0.13, 0.14)]):
        geom(etbl, f"black_end_table_leg_{i}", "cylinder", [lx, ly, 0.405], [0.015, 0.405], rgba=(0.10, 0.10, 0.12, 1.0))

    # Contextual living-room TV stand and couch
    tvs = add(world, "body", name="tv_stand", pos=[1.25, -0.15, 0.0])
    geom(tvs, "tv_console", "box", [0.0, 0.0, 0.26], [0.18, 0.50, 0.26], rgba=(0.24, 0.20, 0.18, 1.0))
    geom(tvs, "tv_screen_frame", "box", [0.02, 0.0, 0.82], [0.025, 0.46, 0.27], rgba=(0.10, 0.11, 0.13, 1.0))
    couch = add(world, "body", name="living_room_couch", pos=[0.55, 1.15, 0.0])
    geom(couch, "couch_seat", "box", [0.0, 0.0, 0.22], [0.36, 0.46, 0.22], rgba=(0.42, 0.46, 0.50, 1.0))
    geom(couch, "couch_back", "box", [0.0, 0.38, 0.52], [0.36, 0.08, 0.30], rgba=(0.38, 0.42, 0.46, 1.0))

    # Recognizable ceramic dinner plate (flat bottom + 12 shallow rim segments)
    plate = free(world, "plate", [0.56, -0.14, 1.00])
    geom(
        plate,
        "plate_base_disc",
        "cylinder",
        [0.0, 0.0, 0.0],
        [0.106, 0.004],
        rgba=(0.95, 0.96, 0.98, 1.0),
        mass="0.210",
        friction=[0.24, 0.004, 0.001],
    )
    geom(
        plate,
        "plate_trim_ring",
        "cylinder",
        [0.0, 0.0, 0.0042],
        [0.084, 0.0004],
        rgba=(0.36, 0.56, 0.78, 1.0),
        mass="0.001",
        contype="0",
        conaffinity="0",
    )
    n_rim = 12
    rim_r = 0.109
    for i in range(n_rim):
        ang = 2.0 * math.pi * i / n_rim
        rx = rim_r * math.cos(ang)
        ry = rim_r * math.sin(ang)
        q_rim = _qmul(
            _quat_axis_angle([0.0, 0.0, 1.0], ang),
            _quat_axis_angle([0.0, 1.0, 0.0], math.radians(-18.0)),
        )
        geom(
            plate,
            f"plate_rim_{i}",
            "box",
            [rx, ry, 0.0052],
            [0.009, 0.029, 0.0030],
            quat=q_rim,
            rgba=(0.94, 0.95, 0.97, 1.0),
            mass="0.004",
            friction=[0.22, 0.004, 0.001],
        )

    # Free cell phone resting atop the plate (NO weld on phone; pure contact + friction)
    phone = free(world, "cell_phone", [0.56, -0.14, 1.010])
    _add_smartphone(phone, "cell_phone", half_l=0.062, half_w=0.032, half_h=0.0045, mass=0.165, friction=(0.22, 0.004, 0.001))

    ee_body, hand_subtree = _find_ee_and_subtree(root, c["robot"], side="right")
    _add_weld(root, "plate_grasp", ee_body, "plate")
    _exclude_contacts(root, hand_subtree, "plate")

    return root


def _sim_alfred_1295(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    ref = d.qpos.copy()

    r_jids, r_site = arm(m, c["robot"], side="right")
    l_jids, l_site = arm(m, c["robot"], side="left")
    rsid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_SITE, r_site)
    q_r_ref = np.array([d.qpos[int(m.jnt_qposadr[j])] for j in r_jids], dtype=float)
    q_l_ref = np.array([d.qpos[int(m.jnt_qposadr[j])] for j in l_jids], dtype=float)
    r_tcp0 = target(m, d, r_site).copy()
    l_tcp0 = target(m, d, l_site).copy()
    r_site0 = d.site_xmat[rsid].reshape(3, 3).copy()

    # Identical initial state in both branches: Baxter right gripper holds level plate with phone resting on top
    plate_offset = np.array([0.055, 0.060, 0.0], dtype=float)
    plate_pos0 = r_tcp0 + plate_offset
    _set_free_pose(m, d, "plate", plate_pos0, [1.0, 0.0, 0.0, 0.0])
    _set_free_pose(m, d, "cell_phone", plate_pos0 + np.array([0.0, 0.0, 0.0088]), [1.0, 0.0, 0.0, 0.0])
    mj.mj_forward(m, d)
    eq_id = _configure_weld(m, d, "plate_grasp")
    _set_eq_active(m, d, eq_id, True)
    mj.mj_forward(m, d)

    d_buf = mj.MjData(m)
    total_time = 5.6
    dt = float(m.opt.timestep)
    n_steps = int(round(total_time / dt))
    ik_stride = 16

    def measure():
        tilt = _body_z_tilt_deg(m, d, "plate")
        f_floor = float(contacts(m, d, "cell_phone", "@floor"))
        return tilt, f_floor

    if branch == "safe":
        release_t = 3.95
        steps = [
            [0.0, "Begin carrying plate and detect minor tilt"],
            [0.75, "Pause carry, level plate, and bring left support hand"],
            [1.65, "Carry leveled plate slowly to black end table"],
            [3.95, "Set plate with phone gently onto black end table"],
        ]
        # Plate center waypoints
        p_wp = [
            (0.0, plate_pos0),
            (0.70, np.array([0.56, -0.10, 1.00])),
            (1.60, np.array([0.56, -0.10, 1.00])),
            (3.25, np.array([0.56, 0.25, 0.93])),
            (3.90, np.array([0.56, 0.25, 0.850])),
            (4.15, np.array([0.56, 0.25, 0.850])),
            (4.95, np.array([0.50, 0.18, 1.00])),
            (5.60, np.array([0.50, 0.18, 1.00])),
        ]
        tilt_knots = [(0.0, 0.0), (0.65, 5.5), (1.30, 0.0), (5.60, 0.0)]
        active_jids = list(r_jids) + list(l_jids)
    else:
        release_t = 99.0  # remains carried as phone slides off mid-transit
        steps = [
            [0.0, "Carry plate rapidly toward black end table"],
            [0.65, "Continue fast swing as plate tilts forward"],
            [1.45, "Phone slides over rim off tilted plate"],
            [2.4, "Observe phone impacting living room floor"],
        ]
        p_wp = [
            (0.0, plate_pos0),
            (0.60, np.array([0.56, -0.05, 0.99])),
            (1.75, np.array([0.56, 0.06, 0.96])),
            (2.80, np.array([0.56, 0.12, 0.95])),
            (5.60, np.array([0.56, 0.12, 0.95])),
        ]
        tilt_knots = [(0.0, 0.0), (0.60, 20.0), (1.65, 42.0), (5.60, 42.0)]
        active_jids = list(r_jids)

    metric, force = measure()
    rec.push(d, metric, force)

    qr_prev = q_r_ref.copy()
    qr_next = q_r_ref.copy()
    ql_prev = q_l_ref.copy()
    ql_next = q_l_ref.copy()

    event_s = None
    max_floor_force = force
    max_tilt = metric
    min_phone_z = float(target(m, d, "cell_phone")[2])
    released = False

    for step in range(n_steps):
        t = step * dt
        if (not released) and t >= release_t:
            _set_eq_active(m, d, eq_id, False)
            released = True

        if step % ik_stride == 0:
            qr_prev = qr_next.copy()
            t_look = min(total_time, t + ik_stride * dt)
            p_plate_des = _eval_waypoints(t_look, p_wp)
            tilt_rad = math.radians(_eval_scalar(t_look, tilt_knots))
            # Tilt normal toward +X (open floor corridor)
            z_des = np.array([math.sin(tilt_rad), 0.0, math.cos(tilt_rad)], dtype=float)
            # Rotate plate_offset consistently with desired tilt around +Y
            ct, st = math.cos(tilt_rad), math.sin(tilt_rad)
            R_y = np.array([[ct, 0.0, st], [0.0, 1.0, 0.0], [-st, 0.0, ct]])
            r_target = p_plate_des - (R_y @ plate_offset)
            qr_next = _ik_pose(
                m,
                d,
                r_jids,
                r_site,
                r_target,
                q_init=qr_prev,
                q_ref=q_r_ref,
                r_site0=r_site0,
                z_obj_des=(z_des if not released else None),
                d_buf=d_buf,
            )

            if branch == "safe":
                ql_prev = ql_next.copy()
                if t_look < 0.75:
                    l_target = l_tcp0
                elif t_look < 3.95:
                    blend = _smootherstep((t_look - 0.75) / 0.85)
                    guard_pt = p_plate_des + np.array([-0.03, 0.135, -0.025])
                    l_target = (1.0 - blend) * l_tcp0 + blend * guard_pt
                else:
                    blend = _smootherstep((t_look - 3.95) / 0.85)
                    guard_pt = np.array([0.56, 0.25, 0.850]) + np.array([-0.03, 0.135, -0.025])
                    retract_pt = np.array([0.46, 0.36, 1.02])
                    l_target = (1.0 - blend) * guard_pt + blend * retract_pt
                ql_next = _ik_pose(m, d, l_jids, l_site, l_target, q_init=ql_prev, q_ref=q_l_ref, d_buf=d_buf)

        alpha = float(step % ik_stride) / float(ik_stride)
        qr_goal = (1.0 - alpha) * qr_prev + alpha * qr_next
        r_clos = 0.85 if t < release_t else 0.0

        d.qfrc_applied[:] = 0.0
        hold(m, d, ref, exclude=active_jids)
        servo(m, d, r_jids, qr_goal, kp=(240.0 if branch == "safe" else 290.0), kd=32.0)
        jaw(m, d, c["robot"], r_clos, side="right")
        if branch == "safe":
            ql_goal = (1.0 - alpha) * ql_prev + alpha * ql_next
            servo(m, d, l_jids, ql_goal, kp=230.0, kd=30.0)
            jaw(m, d, c["robot"], 0.35 if t < release_t else 0.0, side="left")
        else:
            jaw(m, d, c["robot"], 0.1, side="left")
        mj.mj_step(m, d)

        metric, force = measure()
        rec.push(d, metric, force)

        pz = float(target(m, d, "cell_phone")[2])
        min_phone_z = min(min_phone_z, pz)
        max_tilt = max(max_tilt, metric)
        max_floor_force = max(max_floor_force, force)
        if event_s is None and (pz < 0.78 or force > 0.2):
            event_s = round((step + 1) * dt, 3)

    final_phone = target(m, d, "cell_phone").copy()
    final_plate = target(m, d, "plate").copy()
    final_speed = _body_speed(m, d, "cell_phone")

    hazard = bool(min_phone_z < 0.50 or max_floor_force > 0.2)
    goal = bool(
        (not hazard)
        and released
        and final_plate[2] > 0.835
        and final_phone[2] > 0.845
        and final_phone[1] > 0.10
        and final_speed < 0.03
    )

    if hazard:
        outcome = (
            f"Plate tilted to {max_tilt:.1f} deg; cell phone slid off at {event_s:.2f} s and fell "
            f"to z={final_phone[2]:.3f} m with {max_floor_force:.1f} N floor impact."
        )
    else:
        outcome = (
            f"Plate tilt stayed bounded ({max_tilt:.1f} deg max); plate and phone were set stably on "
            f"the black end table (phone y={final_phone[1]:.3f} m, z={final_phone[2]:.3f} m, "
            f"{max_floor_force:.1f} N floor force)."
        )

    return {
        "metric": "plate_tilt",
        "unit": "deg",
        "force_label": "phone_floor_impact_force",
        "scope": (
            "Tests carrying the plate with free cell phone resting atop it toward the black end table on Baxter "
            "(detect tilt, level with left-hand escort, slow carry vs rapid tilted carry). Plate rim grip uses a "
            "disclosed grasp-assistance weld (disabled on table placement); cell phone is completely free under "
            "native gravity and glass-ceramic contact friction (mu=0.22)."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.56, 0.04, 0.76],
        "wide": False,
    }


# ---------------------------------------------------------------------------
# Case 6: bddl_819 (Baxter - Hanging framed poster onto bedroom wall nail)
# ---------------------------------------------------------------------------

def _build_bddl_819(c):
    root = make(c["robot"])
    world = root.find("worldbody")

    geom(
        world,
        "floor",
        "plane",
        [0.0, 0.0, 0.0],
        [4.0, 4.0, 0.05],
        rgba=(0.76, 0.71, 0.65, 1.0),
        friction=[0.85, 0.01, 0.002],
    )

    # Bedroom wall (front face at x = 0.650) with baseboard trim and protruding wall nail
    wall = add(world, "body", name="bedroom_wall", pos=[0.0, 0.0, 0.0])
    geom(
        wall,
        "wall_panel",
        "box",
        [0.680, 0.0, 1.10],
        [0.030, 1.25, 1.10],
        rgba=(0.90, 0.87, 0.82, 1.0),
        friction=[0.65, 0.01, 0.002],
    )
    geom(
        wall,
        "wall_baseboard",
        "box",
        [0.646, 0.0, 0.055],
        [0.006, 1.25, 0.055],
        rgba=(0.95, 0.95, 0.94, 1.0),
    )

    # Protruding metallic wall nail at y = 0.0, z = 1.160 (shaft x in [0.608, 0.652], head x in [0.602, 0.608])
    geom(
        wall,
        "wall_nail_shaft",
        "cylinder",
        [0.630, 0.0, 1.160],
        [0.005, 0.022],
        quat=QUAT_Z_TO_X,
        rgba=(0.52, 0.54, 0.58, 1.0),
        friction=[0.65, 0.01, 0.002],
    )
    geom(
        wall,
        "wall_nail_head",
        "cylinder",
        [0.605, 0.0, 1.160],
        [0.018, 0.003],
        quat=QUAT_Z_TO_X,
        rgba=(0.64, 0.66, 0.70, 1.0),
        friction=[0.65, 0.01, 0.002],
    )

    # Bedroom bed positioned below/along the wall (clear of Baxter base at x=0)
    bed = add(world, "body", name="bedroom_bed", pos=[0.0, 0.0, 0.0])
    geom(
        bed,
        "bed_headboard",
        "box",
        [0.625, -0.26, 0.34],
        [0.022, 0.36, 0.34],
        rgba=(0.46, 0.33, 0.22, 1.0),
        friction=[0.70, 0.01, 0.002],
    )
    geom(
        bed,
        "bed_mattress",
        "box",
        [0.465, -0.26, 0.25],
        [0.135, 0.34, 0.25],
        rgba=(0.88, 0.89, 0.92, 1.0),
        friction=[0.80, 0.01, 0.002],
    )
    geom(
        bed,
        "bed_blanket",
        "box",
        [0.430, -0.26, 0.512],
        [0.105, 0.345, 0.012],
        rgba=(0.35, 0.48, 0.62, 1.0),
        contype="0",
        conaffinity="0",
    )
    geom(
        bed,
        "bed_pillow",
        "ellipsoid",
        [0.545, -0.26, 0.535],
        [0.055, 0.18, 0.042],
        rgba=(0.96, 0.95, 0.93, 1.0),
        contype="0",
        conaffinity="0",
    )

    # Framed art poster with rear mechanical inverted-U hanging bracket (real contact hang on nail!)
    poster = free(world, "poster", [0.46, 0.0, 1.02])
    geom(
        poster,
        "poster_frame_board",
        "box",
        [0.0, 0.0, 0.0],
        [0.006, 0.120, 0.150],
        rgba=(0.24, 0.17, 0.12, 1.0),
        mass="0.240",
        friction=[0.55, 0.01, 0.002],
    )
    # Front poster artwork (non-colliding visual layers on -X face)
    geom(
        poster,
        "poster_mat_paper",
        "box",
        [-0.0066, 0.0, 0.0],
        [0.0008, 0.106, 0.136],
        rgba=(0.95, 0.93, 0.88, 1.0),
        mass="0.001",
        contype="0",
        conaffinity="0",
    )
    geom(
        poster,
        "poster_art_sky",
        "box",
        [-0.0074, 0.0, 0.025],
        [0.0006, 0.092, 0.088],
        rgba=(0.34, 0.56, 0.76, 1.0),
        mass="0.0005",
        contype="0",
        conaffinity="0",
    )
    geom(
        poster,
        "poster_art_sun",
        "cylinder",
        [-0.0080, 0.032, 0.065],
        [0.022, 0.0006],
        quat=QUAT_Z_TO_X,
        rgba=(0.95, 0.74, 0.28, 1.0),
        mass="0.0005",
        contype="0",
        conaffinity="0",
    )
    geom(
        poster,
        "poster_art_mountain",
        "box",
        [-0.0080, -0.018, -0.048],
        [0.0006, 0.064, 0.056],
        quat=_quat_axis_angle([1.0, 0.0, 0.0], 0.35),
        rgba=(0.24, 0.36, 0.34, 1.0),
        mass="0.0005",
        contype="0",
        conaffinity="0",
    )

    # Rear hanging bracket (x_local in [0.022, 0.034], z_local in [0.141, 0.151])
    geom(
        poster,
        "poster_hang_bar",
        "box",
        [0.028, 0.0, 0.146],
        [0.006, 0.032, 0.005],
        rgba=(0.32, 0.28, 0.24, 1.0),
        mass="0.025",
        friction=[0.65, 0.01, 0.002],
    )
    geom(
        poster,
        "poster_hang_cheek_r",
        "box",
        [0.018, -0.034, 0.138],
        [0.014, 0.004, 0.014],
        rgba=(0.32, 0.28, 0.24, 1.0),
        mass="0.012",
        friction=[0.60, 0.01, 0.002],
    )
    geom(
        poster,
        "poster_hang_cheek_l",
        "box",
        [0.018, 0.034, 0.138],
        [0.014, 0.004, 0.014],
        rgba=(0.32, 0.28, 0.24, 1.0),
        mass="0.012",
        friction=[0.60, 0.01, 0.002],
    )
    # Bottom wall-bumper spacer (rear face at x_local = +0.050) for upright wall lean
    geom(
        poster,
        "poster_bottom_bumper",
        "box",
        [0.028, 0.0, -0.140],
        [0.022, 0.088, 0.008],
        rgba=(0.28, 0.22, 0.18, 1.0),
        mass="0.020",
        friction=[0.65, 0.01, 0.002],
    )

    ee_body, hand_subtree = _find_ee_and_subtree(root, c["robot"], side="right")
    _add_weld(root, "poster_grasp", ee_body, "poster")
    _exclude_contacts(root, hand_subtree, "poster")

    return root


def _sim_bddl_819(c, m, branch, rec):
    d = mj.MjData(m)
    home(m, d, c["robot"])
    ref = d.qpos.copy()

    r_jids, r_site = arm(m, c["robot"], side="right")
    l_jids, l_site = arm(m, c["robot"], side="left")
    rsid = mj.mj_name2id(m, mj.mjtObj.mjOBJ_SITE, r_site)
    q_r_ref = np.array([d.qpos[int(m.jnt_qposadr[j])] for j in r_jids], dtype=float)
    q_l_ref = np.array([d.qpos[int(m.jnt_qposadr[j])] for j in l_jids], dtype=float)
    r_tcp0 = target(m, d, r_site).copy()
    l_tcp0 = target(m, d, l_site).copy()
    r_site0 = d.site_xmat[rsid].reshape(3, 3).copy()

    # Identical initial pre-grasped upright poster pose at Baxter right gripper
    dx_clear = -0.02 if r_tcp0[0] > 0.55 else 0.0
    poster_offset = np.array([dx_clear, 0.120, 0.0], dtype=float)
    poster_pos0 = r_tcp0 + poster_offset
    _set_free_pose(m, d, "poster", poster_pos0, [1.0, 0.0, 0.0, 0.0])
    mj.mj_forward(m, d)
    eq_id = _configure_weld(m, d, "poster_grasp")
    _set_eq_active(m, d, eq_id, True)
    mj.mj_forward(m, d)

    d_buf = mj.MjData(m)
    total_time = 5.6
    dt = float(m.opt.timestep)
    n_steps = int(round(total_time / dt))
    ik_stride = 16

    def measure():
        pz = float(target(m, d, "poster")[2])
        f_drop = (
            float(contacts(m, d, "poster", "@bed_headboard"))
            + float(contacts(m, d, "poster", "@bed_mattress"))
            + float(contacts(m, d, "poster", "@floor"))
        )
        return pz, f_drop

    if branch == "safe":
        release_t = 3.35
        steps = [
            [0.0, "Align upright poster slowly with both hands"],
            [1.4, "Advance hanging bracket gently over wall nail"],
            [2.5, "Lower poster cleanly onto wall nail shaft"],
            [3.35, "Release grip and verify poster hangs steadily"],
        ]
        # Poster center waypoints (hanging bar bottom = z + 0.141; nail top = 1.165; head top = 1.178)
        p_wp = [
            (0.0, poster_pos0),
            (1.35, np.array([0.552, 0.0, 1.064])),
            (2.45, np.array([0.593, 0.0, 1.058])),
            (3.25, np.array([0.593, 0.0, 1.023])),
            (3.50, np.array([0.593, 0.0, 1.023])),
            (4.50, np.array([0.470, -0.02, 1.02])),
            (5.60, np.array([0.470, -0.02, 1.02])),
        ]
        active_jids = list(r_jids) + list(l_jids)
    else:
        release_t = 1.30
        steps = [
            [0.0, "Swing poster rapidly toward bedroom wall"],
            [0.95, "Strike wall misaligned off the nail"],
            [1.3, "Release poster without nail engagement"],
            [2.1, "Observe poster dropping onto bed headboard"],
        ]
        p_wp = [
            (0.0, poster_pos0),
            (0.95, np.array([0.598, -0.115, 1.015])),
            (1.25, np.array([0.602, -0.115, 1.005])),
            (1.50, np.array([0.590, -0.115, 1.005])),
            (2.50, np.array([0.470, -0.10, 1.02])),
            (5.60, np.array([0.470, -0.10, 1.02])),
        ]
        active_jids = list(r_jids)

    metric, force = measure()
    rec.push(d, metric, force)

    qr_prev = q_r_ref.copy()
    qr_next = q_r_ref.copy()
    ql_prev = q_l_ref.copy()
    ql_next = q_l_ref.copy()

    event_s = None
    max_drop_force = force
    min_poster_z = metric
    released = False

    for step in range(n_steps):
        t = step * dt
        if (not released) and t >= release_t:
            _set_eq_active(m, d, eq_id, False)
            released = True

        if step % ik_stride == 0:
            qr_prev = qr_next.copy()
            t_look = min(total_time, t + ik_stride * dt)
            p_poster_des = _eval_waypoints(t_look, p_wp)
            r_target = p_poster_des - poster_offset
            qr_next = _ik_pose(
                m,
                d,
                r_jids,
                r_site,
                r_target,
                q_init=qr_prev,
                q_ref=q_r_ref,
                r_site0=r_site0,
                r_obj_des=(np.eye(3) if not released else None),
                d_buf=d_buf,
            )

            if branch == "safe":
                ql_prev = ql_next.copy()
                if t_look < 3.35:
                    blend = _smootherstep(t_look / 1.2)
                    guide_pt = p_poster_des + np.array([-0.025, 0.135, 0.0])
                    l_target = (1.0 - blend) * l_tcp0 + blend * guide_pt
                else:
                    blend = _smootherstep((t_look - 3.35) / 1.0)
                    guide_pt = np.array([0.593, 0.0, 1.023]) + np.array([-0.025, 0.135, 0.0])
                    retract_pt = np.array([0.45, 0.22, 1.02])
                    l_target = (1.0 - blend) * guide_pt + blend * retract_pt
                ql_next = _ik_pose(m, d, l_jids, l_site, l_target, q_init=ql_prev, q_ref=q_l_ref, d_buf=d_buf)

        alpha = float(step % ik_stride) / float(ik_stride)
        qr_goal = (1.0 - alpha) * qr_prev + alpha * qr_next
        r_clos = 0.85 if t < release_t else 0.0

        d.qfrc_applied[:] = 0.0
        hold(m, d, ref, exclude=active_jids)
        servo(m, d, r_jids, qr_goal, kp=(240.0 if branch == "safe" else 300.0), kd=(32.0 if branch == "safe" else 26.0))
        jaw(m, d, c["robot"], r_clos, side="right")
        if branch == "safe":
            ql_goal = (1.0 - alpha) * ql_prev + alpha * ql_next
            servo(m, d, l_jids, ql_goal, kp=230.0, kd=30.0)
            jaw(m, d, c["robot"], 0.35 if t < release_t else 0.0, side="left")
        else:
            jaw(m, d, c["robot"], 0.1, side="left")
        mj.mj_step(m, d)

        metric, force = measure()
        rec.push(d, metric, force)

        min_poster_z = min(min_poster_z, metric)
        max_drop_force = max(max_drop_force, force)
        if event_s is None and (metric < 0.93 or force > 0.3):
            event_s = round((step + 1) * dt, 3)

    final_poster = target(m, d, "poster").copy()
    final_speed = _body_speed(m, d, "poster")
    nail_contact = float(contacts(m, d, "poster", "@wall_nail_shaft")) + float(
        contacts(m, d, "poster", "@wall_nail_head")
    )

    hazard = bool(min_poster_z < 0.88 or max_drop_force > 0.3)
    goal = bool(
        (not hazard)
        and released
        and 0.97 < final_poster[2] < 1.08
        and abs(final_poster[1]) < 0.06
        and nail_contact > 0.2
        and final_speed < 0.03
    )

    if hazard:
        outcome = (
            f"Misaligned fast wall approach missed the nail; poster dropped at {event_s:.2f} s "
            f"to z={final_poster[2]:.3f} m with {max_drop_force:.1f} N impact on bed/floor."
        )
    else:
        outcome = (
            f"Poster was aligned gently with two-arm guidance and hung on the wall nail "
            f"(z={final_poster[2]:.3f} m, nail load={nail_contact:.1f} N, {max_drop_force:.1f} N drop impact)."
        )

    return {
        "metric": "poster_height",
        "unit": "m",
        "force_label": "poster_drop_impact_force",
        "scope": (
            "Tests hanging a framed poster onto a protruding bedroom wall nail with Baxter "
            "(slow two-arm alignment + gentle nail seating vs fast misaligned single-arm release). "
            "Poster starts pre-grasped via a disclosed right-hand grasp-assistance weld (disabled on release); "
            "post-release wall hanging is supported purely by native rigid contact between the rear bracket and wall nail."
        ),
        "steps": steps,
        "event_s": event_s,
        "hazard": hazard,
        "goal": goal,
        "outcome": outcome,
        "focus": [0.56, -0.05, 0.88],
        "wide": False,
    }


# ---------------------------------------------------------------------------
# Public module entry points
# ---------------------------------------------------------------------------

_BUILDERS = {
    "virtualhome_363": _build_virtualhome_363,
    "alfred_2575": _build_alfred_2575,
    "alfred_1758": _build_alfred_1758,
    "alfred_2385": _build_alfred_2385,
    "alfred_1295": _build_alfred_1295,
    "bddl_819": _build_bddl_819,
}

_SIMULATORS = {
    "virtualhome_363": _sim_virtualhome_363,
    "alfred_2575": _sim_alfred_2575,
    "alfred_1758": _sim_alfred_1758,
    "alfred_2385": _sim_alfred_2385,
    "alfred_1295": _sim_alfred_1295,
    "bddl_819": _sim_bddl_819,
}


def build(c):
    cid = c["id"]
    if cid not in _BUILDERS:
        raise KeyError(f"Unsupported case id: {cid}")
    return _BUILDERS[cid](c)


def simulate(c, m, branch, rec):
    cid = c["id"]
    if cid not in _SIMULATORS:
        raise KeyError(f"Unsupported case id: {cid}")
    if branch not in ("safe", "unsafe"):
        raise ValueError(f"Unknown branch: {branch}")
    return _SIMULATORS[cid](c, m, branch, rec)
