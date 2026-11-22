import math
import numpy as np
from scipy.optimize import minimize

DURATION = 20.0

CUP_RADIUS = 0.0286
CUP_HEIGHT = 0.060
CUP_HALF_H = 0.5 * CUP_HEIGHT
CUP_REST_POS = np.array([-0.74, 0.80, 0.921], dtype=np.float64)
TABLETOP_Z = 0.886

MAGAZINE_POS = np.array([0.32, 1.96, 0.928], dtype=np.float64)
MAGAZINE_YAW_RAD = math.radians(10.0)

LIPS_LOCAL_OFFSET = np.array([0.0, 0.08, 0.055], dtype=np.float64)

HANDLE_TUBE_RADIUS = 0.0038
HANDLE_NUM_SEGMENTS = 12

PHASES = {
    "parked_start": (0.0, 1.4),
    "reach": (1.4, 5.2),
    "grip": (5.2, 6.4),
    "lift": (6.4, 9.4),
    "sip": (9.4, 11.8),
    "return": (11.8, 14.8),
    "release": (14.8, 16.0),
    "withdraw": (16.0, 18.6),
    "parked_end": (18.6, 20.0),
}

AUDIT_CRITERIA = {
    "duration_s": DURATION,
    "cup_radius_m": CUP_RADIUS,
    "cup_height_m": CUP_HEIGHT,
    "cup_rest_center_world_m": tuple(float(v) for v in CUP_REST_POS),
    "cup_bottom_on_saucer_z_m": float(CUP_REST_POS[2] - CUP_HALF_H),
    "tabletop_z_m": TABLETOP_Z,
    "handle_tube_radius_range_m": (0.0034, 0.0045),
    "handle_protrusion_beyond_wall_range_m": (0.035, 0.042),
    "grip_handle_surface_dist_max_m": 0.0015,
    "grip_handle_penetration_min_m": -0.0002,
    "hand_to_cup_body_clearance_min_m": 0.0025,
    "hand_to_tabletop_z_min_m": TABLETOP_Z,
    "sip_rim_to_lips_dist_range_m": (0.006, 0.035),
    "sip_cup_tilt_range_deg": (20.0, 35.0),
    "foot_position_drift_max_m": 0.0005,
    "cup_rest_drift_max_m": 0.0005,
    "magazine_park_pos_world_m": tuple(float(v) for v in MAGAZINE_POS),
    "magazine_park_yaw_deg": 10.0,
    "max_step_bone_jump_m": 0.015,
}

_FINGER_CHAINS = {
    "R": {
        "hand": "R_Hand",
        "upper": "fabric_R_upper",
        "lower": "fabric_R_lower",
        "fingers": {
            "Index": ("R_Index1", "R_Index2", "R_Index3"),
            "Mid": ("R_Mid1", "R_Mid2", "R_Mid3"),
            "Ring": ("R_Ring1", "R_Ring2", "R_Ring3"),
            "Pinky": ("R_Pinky1", "R_Pinky2", "R_Pinky3"),
            "Thumb": ("R_Thumb1", "R_Thumb2", "R_Thumb3"),
        },
    },
    "L": {
        "hand": "L_Hand",
        "upper": "fabric_L_upper",
        "lower": "fabric_L_lower",
        "fingers": {
            "Index": ("L_Index1", "L_Index2", "L_Index3"),
            "Mid": ("L_Mid1", "L_Mid2", "L_Mid3"),
            "Ring": ("L_Ring1", "L_Ring2", "L_Ring3"),
            "Pinky": ("L_Pinky1", "L_Pinky2", "L_Pinky3"),
            "Thumb": ("L_Thumb1", "L_Thumb2", "L_Thumb3"),
        },
    },
}


def handle_segments():
    """Return list of (a, b, r) capsule segments in cup-local metres for the D-handle.

    Smooth cubic-Bezier D-loop in the cup-local y=0 plane on negative X:
    - Starts and ends embedded 1.0 mm into the outer cup wall (x = -0.0276 m).
    - Tube radius r = 3.8 mm (within 3.4-4.5 mm).
    - Centerline extends 36.05 mm beyond wall (outer surface 39.85 mm, both in 35-42 mm).
    """
    p0 = np.array([-0.0276, 0.0, 0.0205], dtype=np.float64)
    p1 = np.array([-0.0770, 0.0, 0.0235], dtype=np.float64)
    p2 = np.array([-0.0770, 0.0, -0.0225], dtype=np.float64)
    p3 = np.array([-0.0276, 0.0, -0.0195], dtype=np.float64)

    ts = np.linspace(0.0, 1.0, HANDLE_NUM_SEGMENTS + 1)
    pts = []
    for s in ts:
        u = 1.0 - s
        pt = (
            (u ** 3) * p0
            + 3.0 * (u ** 2) * s * p1
            + 3.0 * u * (s ** 2) * p2
            + (s ** 3) * p3
        )
        pts.append(pt)

    r = float(HANDLE_TUBE_RADIUS)
    segs = []
    for i in range(HANDLE_NUM_SEGMENTS):
        a = (float(pts[i][0]), float(pts[i][1]), float(pts[i][2]))
        b = (float(pts[i + 1][0]), float(pts[i + 1][1]), float(pts[i + 1][2]))
        segs.append((a, b, r))
    return segs


def _norm(v, eps=1e-12):
    n = float(np.linalg.norm(v))
    if n < eps:
        return np.zeros_like(v, dtype=np.float64)
    return v / n


def _rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]], dtype=np.float64)


def _rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]], dtype=np.float64)


def _rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)


def _rotvec_to_mat(rv):
    theta = float(np.linalg.norm(rv))
    if theta < 1e-12:
        return np.eye(3, dtype=np.float64)
    k = rv / theta
    kx, ky, kz = float(k[0]), float(k[1]), float(k[2])
    K = np.array([[0.0, -kz, ky], [kz, 0.0, -kx], [-ky, kx, 0.0]], dtype=np.float64)
    return np.eye(3, dtype=np.float64) + math.sin(theta) * K + (1.0 - math.cos(theta)) * (K @ K)


def _mat_to_rotvec(R):
    tr = float(np.trace(R))
    cos_t = max(-1.0, min(1.0, 0.5 * (tr - 1.0)))
    theta = math.acos(cos_t)
    if theta < 1e-8:
        return 0.5 * np.array(
            [R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]],
            dtype=np.float64,
        )
    if math.pi - theta < 1e-5:
        q = _mat_to_quat_wxyz(R)
        v = q[1:]
        nv = float(np.linalg.norm(v))
        if nv < 1e-12:
            return np.zeros(3, dtype=np.float64)
        return (2.0 * math.atan2(nv, q[0])) * (v / nv)
    s = 2.0 * math.sin(theta)
    axis = np.array(
        [R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]],
        dtype=np.float64,
    ) / s
    return theta * axis


def _mat_to_quat_wxyz(R):
    tr = R[0, 0] + R[1, 1] + R[2, 2]
    if tr > 0.0:
        s = 2.0 * math.sqrt(tr + 1.0)
        w = 0.25 * s
        x = (R[2, 1] - R[1, 2]) / s
        y = (R[0, 2] - R[2, 0]) / s
        z = (R[1, 0] - R[0, 1]) / s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = 2.0 * math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
        w = (R[2, 1] - R[1, 2]) / s
        x = 0.25 * s
        y = (R[0, 1] + R[1, 0]) / s
        z = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = 2.0 * math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
        w = (R[0, 2] - R[2, 0]) / s
        x = (R[0, 1] + R[1, 0]) / s
        y = 0.25 * s
        z = (R[1, 2] + R[2, 1]) / s
    else:
        s = 2.0 * math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
        w = (R[1, 0] - R[0, 1]) / s
        x = (R[0, 2] + R[2, 0]) / s
        y = (R[1, 2] + R[2, 1]) / s
        z = 0.25 * s
    q = np.array([w, x, y, z], dtype=np.float64)
    n = float(np.linalg.norm(q))
    if n < 1e-12:
        return np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float64)
    return q / n


def _slerp_mat(R0, R1, u):
    u = max(0.0, min(1.0, float(u)))
    if u <= 0.0:
        return R0.copy()
    if u >= 1.0:
        return R1.copy()
    rv = _mat_to_rotvec(R0.T @ R1)
    return R0 @ _rotvec_to_mat(u * rv)


def _align_vec_rot(v_from, v_to):
    a = _norm(v_from)
    b = _norm(v_to)
    c = float(np.dot(a, b))
    if c > 1.0 - 1e-12:
        return np.eye(3, dtype=np.float64)
    if c < -1.0 + 1e-10:
        perp = np.array([0.0, 0.0, 1.0], dtype=np.float64)
        if abs(a[2]) > 0.9:
            perp = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        axis = _norm(np.cross(a, perp))
        return _rotvec_to_mat(math.pi * axis)
    v = np.cross(a, b)
    s = float(np.linalg.norm(v))
    vx, vy, vz = float(v[0]), float(v[1]), float(v[2])
    K = np.array([[0.0, -vz, vy], [vz, 0.0, -vx], [-vy, vx, 0.0]], dtype=np.float64)
    return np.eye(3, dtype=np.float64) + K + (K @ K) * ((1.0 - c) / max(s * s, 1e-16))


def _s5(u):
    u = max(0.0, min(1.0, float(u)))
    return u * u * u * (10.0 + u * (-15.0 + 6.0 * u))


def _ramp(t, t0, t1):
    if t <= t0:
        return 0.0
    if t >= t1:
        return 1.0
    return _s5((t - t0) / (t1 - t0))


def _pulse(t, t0, t1, t2, t3):
    if t <= t0 or t >= t3:
        return 0.0
    if t < t1:
        return _s5((t - t0) / max(t1 - t0, 1e-9))
    if t <= t2:
        return 1.0
    return 1.0 - _s5((t - t2) / max(t3 - t2, 1e-9))


def _bezier_cubic(p0, p1, p2, p3, u):
    v = 1.0 - u
    return (
        (v ** 3) * p0
        + 3.0 * (v ** 2) * u * p1
        + 3.0 * v * (u ** 2) * p2
        + (u ** 3) * p3
    )


def _handle_arrays(segs):
    A = np.array([s[0] for s in segs], dtype=np.float64)
    B = np.array([s[1] for s in segs], dtype=np.float64)
    R = np.array([s[2] for s in segs], dtype=np.float64)
    AB = B - A
    AB_sq = np.maximum(np.sum(AB * AB, axis=1), 1e-16)
    return A, AB, AB_sq, R


def _handle_sdf_and_closest(pts, A, AB, AB_sq, R):
    diff = pts[:, None, :] - A[None, :, :]
    t = np.clip(np.sum(diff * AB[None, :, :], axis=2) / AB_sq[None, :], 0.0, 1.0)
    closest = A[None, :, :] + t[:, :, None] * AB[None, :, :]
    vec = pts[:, None, :] - closest
    dist = np.linalg.norm(vec, axis=2) - R[None, :]
    seg_idx = np.argmin(dist, axis=1)
    row_idx = np.arange(pts.shape[0])
    sdf = dist[row_idx, seg_idx]
    c_pts = closest[row_idx, seg_idx]
    return sdf, c_pts


def _cup_body_sdf(pts):
    rho = np.hypot(pts[:, 0], pts[:, 1]) - CUP_RADIUS
    dz = np.abs(pts[:, 2]) - CUP_HALF_H
    out_r = np.maximum(rho, 0.0)
    out_z = np.maximum(dz, 0.0)
    return np.hypot(out_r, out_z) + np.minimum(np.maximum(rho, dz), 0.0)


def _saucer_surface_z_cup(pts):
    rho = np.hypot(pts[:, 0], pts[:, 1])
    table_z_cup = TABLETOP_Z - CUP_REST_POS[2]
    rim_blend = np.clip((rho - 0.029) / 0.043, 0.0, 1.0)
    saucer_z = -CUP_HALF_H + 0.014 * rim_blend
    on_saucer = rho <= 0.074
    return np.where(on_saucer, saucer_z, table_z_cup)


def _right_finger_local_rots(params):
    """Map 10-DOF right-hand articulation vector to local bone rotations.

    params:
      0..4: thumb [t_abd_x, t_flex_y, t_adduct_z, t_mcp_y, t_ip_y]
      5..7: index [i_mcp_y, i_pip_y, i_dip_y]
      8:    mid_curl (scalar driving coupled MCP/PIP/DIP)
      9:    rp_curl  (scalar driving progressive Ring/Pinky curl)
    """
    t_ax, t_fy, t_az, t_mcp, t_ip = params[0:5]
    i_mcp, i_pip, i_dip = params[5:8]
    m_c = float(params[8])
    rp_c = float(params[9])

    rots = {}
    rots["R_Thumb1"] = _rot_z(t_az) @ _rot_y(t_fy) @ _rot_x(t_ax)
    rots["R_Thumb2"] = _rot_y(t_mcp) @ _rot_x(-0.12 * t_mcp)
    rots["R_Thumb3"] = _rot_y(t_ip)

    rots["R_Index1"] = _rot_y(i_mcp) @ _rot_z(0.04)
    rots["R_Index2"] = _rot_y(i_pip)
    rots["R_Index3"] = _rot_y(i_dip)

    rots["R_Mid1"] = _rot_y(0.62 * m_c)
    rots["R_Mid2"] = _rot_y(0.88 * m_c)
    rots["R_Mid3"] = _rot_y(0.54 * m_c)

    r_c = 1.08 * rp_c
    rots["R_Ring1"] = _rot_y(0.66 * r_c) @ _rot_z(-0.04)
    rots["R_Ring2"] = _rot_y(0.92 * r_c)
    rots["R_Ring3"] = _rot_y(0.58 * r_c)

    p_c = 1.18 * rp_c
    rots["R_Pinky1"] = _rot_y(0.70 * p_c) @ _rot_z(-0.08)
    rots["R_Pinky2"] = _rot_y(0.95 * p_c)
    rots["R_Pinky3"] = _rot_y(0.60 * p_c)
    return rots


def _left_finger_local_rots(relax_mod=0.0):
    """Natural relaxed left-hand articulation (negative Ry curls left fingers)."""
    m = float(relax_mod)
    rots = {}
    rots["L_Thumb1"] = _rot_z(0.24) @ _rot_y(-0.24 - 0.04 * m) @ _rot_x(-0.36)
    rots["L_Thumb2"] = _rot_y(-0.18 - 0.04 * m)
    rots["L_Thumb3"] = _rot_y(-0.16 - 0.03 * m)

    rots["L_Index1"] = _rot_y(-0.32 - 0.05 * m) @ _rot_z(-0.04)
    rots["L_Index2"] = _rot_y(-0.46 - 0.06 * m)
    rots["L_Index3"] = _rot_y(-0.28 - 0.04 * m)

    rots["L_Mid1"] = _rot_y(-0.46 - 0.06 * m)
    rots["L_Mid2"] = _rot_y(-0.60 - 0.06 * m)
    rots["L_Mid3"] = _rot_y(-0.36 - 0.04 * m)

    rots["L_Ring1"] = _rot_y(-0.58 - 0.06 * m) @ _rot_z(0.03)
    rots["L_Ring2"] = _rot_y(-0.72 - 0.06 * m)
    rots["L_Ring3"] = _rot_y(-0.44 - 0.04 * m)

    rots["L_Pinky1"] = _rot_y(-0.70 - 0.06 * m) @ _rot_z(0.07)
    rots["L_Pinky2"] = _rot_y(-0.82 - 0.05 * m)
    rots["L_Pinky3"] = _rot_y(-0.50 - 0.04 * m)
    return rots


def _fk_hand_bones(bind, side, wrist_pos, wrist_rot, finger_local_rots):
    spec = _FINGER_CHAINS[side]
    hand_name = spec["hand"]
    pos = {hand_name: wrist_pos.copy()}
    rot = {hand_name: wrist_rot.copy()}

    for chain in spec["fingers"].values():
        parent = hand_name
        for bname in chain:
            if bname not in bind:
                continue
            rel = bind[bname] - bind[parent]
            pos[bname] = pos[parent] + rot[parent] @ rel
            dR = finger_local_rots.get(bname, np.eye(3, dtype=np.float64))
            rot[bname] = rot[parent] @ dR
            parent = bname
    return pos, rot


def _solve_arm_ik(bind, side, shoulder_pos, wrist_pos, wrist_rot, pole_dir):
    spec = _FINGER_CHAINS[side]
    u_name = spec["upper"]
    l_name = spec["lower"]
    h_name = spec["hand"]

    v_bind_raw = bind[l_name] - bind[u_name]
    f_bind_raw = bind[h_name] - bind[l_name]
    L1 = float(np.linalg.norm(v_bind_raw))
    L2 = float(np.linalg.norm(f_bind_raw))
    v_bind = v_bind_raw / max(L1, 1e-12)
    f_bind = f_bind_raw / max(L2, 1e-12)

    d_vec = wrist_pos - shoulder_pos
    d = float(np.linalg.norm(d_vec))
    min_d = abs(L1 - L2) + 1e-4
    max_d = (L1 + L2) - 1e-4
    if d < 1e-9:
        u_dir = np.array([1.0 if side == "R" else -1.0, 0.0, 0.0], dtype=np.float64)
        d_eff = min_d
    else:
        u_dir = d_vec / d
        d_eff = max(min_d, min(max_d, d))

    wrist_clamped = shoulder_pos + d_eff * u_dir

    a = (L1 * L1 - L2 * L2 + d_eff * d_eff) / (2.0 * d_eff)
    h_sq = max(L1 * L1 - a * a, 0.0)
    h = math.sqrt(h_sq)

    p_perp = pole_dir - float(np.dot(pole_dir, u_dir)) * u_dir
    if float(np.linalg.norm(p_perp)) < 1e-6:
        fallback = np.array([0.0, -1.0, -1.0], dtype=np.float64)
        p_perp = fallback - float(np.dot(fallback, u_dir)) * u_dir
    p_hat = _norm(p_perp)

    elbow_pos = shoulder_pos + a * u_dir + h * p_hat
    v_cur = _norm(elbow_pos - shoulder_pos)
    f_cur = _norm(wrist_clamped - elbow_pos)

    if side == "R":
        z_cur = np.cross(v_cur, f_cur)
    else:
        z_cur = np.cross(f_cur, v_cur)
    if float(np.linalg.norm(z_cur)) < 1e-5:
        if side == "R":
            z_cur = np.cross(v_cur, -p_hat)
        else:
            z_cur = np.cross(-p_hat, v_cur)
    z_cur = _norm(z_cur)
    y_cur = np.cross(z_cur, v_cur)

    z_b = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    z_b = _norm(z_b - float(np.dot(z_b, v_bind)) * v_bind)
    y_b = np.cross(z_b, v_bind)

    B_cur = np.column_stack((v_cur, y_cur, z_cur))
    B_bind = np.column_stack((v_bind, y_b, z_b))
    upper_rot = B_cur @ B_bind.T

    f_hand = wrist_rot @ f_bind
    R_align = _align_vec_rot(f_hand, f_cur)
    lower_rot = R_align @ wrist_rot

    return upper_rot, elbow_pos, lower_rot, wrist_clamped


def _build_synthetic_right_hand(bind):
    """Fallback calibrated anatomical right-hand point cloud if hand_data is None."""
    pts = []
    b_names = []

    def add_capsule(p0, p1, radius, bname, n_len=5, n_ring=8):
        axis = p1 - p0
        L = float(np.linalg.norm(axis))
        if L < 1e-6:
            return
        u = axis / L
        ref = np.array([0.0, 0.0, 1.0], dtype=np.float64)
        if abs(u[2]) > 0.9:
            ref = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        e1 = _norm(np.cross(u, ref))
        e2 = np.cross(u, e1)
        for s in np.linspace(0.0, 1.0, n_len):
            c = p0 + s * axis
            for th in np.linspace(0.0, 2.0 * math.pi, n_ring, endpoint=False):
                pts.append(c + radius * (math.cos(th) * e1 + math.sin(th) * e2))
                b_names.append(bname)
        for phi in (0.35 * math.pi, 0.5 * math.pi):
            for th in np.linspace(0.0, 2.0 * math.pi, n_ring, endpoint=False):
                pts.append(
                    p1
                    + radius
                    * (
                        math.sin(phi) * u
                        + math.cos(phi) * (math.cos(th) * e1 + math.sin(th) * e2)
                    )
                )
                b_names.append(bname)

    h = bind["R_Hand"]
    for f, r1, r2, r3, tip_ext in (
        ("Index", 0.0082, 0.0074, 0.0066, 0.020),
        ("Mid", 0.0084, 0.0076, 0.0068, 0.021),
        ("Ring", 0.0078, 0.0070, 0.0064, 0.019),
        ("Pinky", 0.0068, 0.0062, 0.0056, 0.016),
    ):
        j1, j2, j3 = bind[f"R_{f}1"], bind[f"R_{f}2"], bind[f"R_{f}3"]
        d_tip = _norm(j3 - j2)
        add_capsule(h + 0.3 * (j1 - h), j1, 0.011, "R_Hand", n_len=4, n_ring=8)
        add_capsule(j1, j2, r1, f"R_{f}1", n_len=4, n_ring=8)
        add_capsule(j2, j3, r2, f"R_{f}2", n_len=4, n_ring=8)
        add_capsule(j3, j3 + tip_ext * d_tip, r3, f"R_{f}3", n_len=5, n_ring=10)

    t1, t2, t3 = bind["R_Thumb1"], bind["R_Thumb2"], bind["R_Thumb3"]
    dt = _norm(t3 - t2)
    add_capsule(t1, t2, 0.0105, "R_Thumb1", n_len=4, n_ring=8)
    add_capsule(t2, t3, 0.0088, "R_Thumb2", n_len=4, n_ring=8)
    add_capsule(t3, t3 + 0.022 * dt, 0.0082, "R_Thumb3", n_len=5, n_ring=10)

    v0 = np.asarray(pts, dtype=np.float64)
    N = v0.shape[0]
    bones = np.array(b_names, dtype=object).reshape(N, 1)
    weights = np.ones((N, 1), dtype=np.float64)
    return {"vertices": v0, "bones": bones, "weights": weights}


def _decode_bone_name(raw):
    if isinstance(raw, (bytes, bytearray, np.bytes_)):
        return raw.decode("utf-8", errors="ignore").strip()
    return str(raw).strip()


def _prepare_right_hand_mesh(bind, hand_data):
    is_synthetic = hand_data is None
    src = _build_synthetic_right_hand(bind) if is_synthetic else hand_data

    verts = np.asarray(src["vertices"], dtype=np.float64)
    raw_bones = np.asarray(src["bones"])
    raw_weights = np.asarray(src["weights"], dtype=np.float64)

    if raw_bones.ndim == 1:
        raw_bones = raw_bones[:, None]
    if raw_weights.ndim == 1:
        raw_weights = raw_weights[:, None]

    N, K = raw_bones.shape
    bone_list = [
        "fabric_R_lower",
        "R_Hand",
        "R_Thumb1",
        "R_Thumb2",
        "R_Thumb3",
        "R_Index1",
        "R_Index2",
        "R_Index3",
        "R_Mid1",
        "R_Mid2",
        "R_Mid3",
        "R_Ring1",
        "R_Ring2",
        "R_Ring3",
        "R_Pinky1",
        "R_Pinky2",
        "R_Pinky3",
    ]
    bone_to_idx = {name: idx for idx, name in enumerate(bone_list)}

    def map_name(name):
        if name in bone_to_idx:
            return bone_to_idx[name]
        low = name.lower()
        if not low:
            return -1
        if low.startswith("l_") or "_l_" in low or "left" in low:
            return -2
        if "lower" in low or "forearm" in low:
            return bone_to_idx["fabric_R_lower"]
        if "thumb" in low:
            if "3" in low or "dist" in low:
                return bone_to_idx["R_Thumb3"]
            if "2" in low or "mid" in low:
                return bone_to_idx["R_Thumb2"]
            return bone_to_idx["R_Thumb1"]
        if "index" in low:
            if "3" in low:
                return bone_to_idx["R_Index3"]
            if "2" in low:
                return bone_to_idx["R_Index2"]
            return bone_to_idx["R_Index1"]
        if "mid" in low:
            if "3" in low:
                return bone_to_idx["R_Mid3"]
            if "2" in low:
                return bone_to_idx["R_Mid2"]
            return bone_to_idx["R_Mid1"]
        if "ring" in low:
            if "3" in low:
                return bone_to_idx["R_Ring3"]
            if "2" in low:
                return bone_to_idx["R_Ring2"]
            return bone_to_idx["R_Ring1"]
        if "pinky" in low or "little" in low:
            if "3" in low:
                return bone_to_idx["R_Pinky3"]
            if "2" in low:
                return bone_to_idx["R_Pinky2"]
            return bone_to_idx["R_Pinky1"]
        if "hand" in low or "wrist" in low or "palm" in low:
            return bone_to_idx["R_Hand"]
        return -1

    keep_rows = []
    mapped_b = []
    mapped_w = []
    thumb3_w = []
    index3_w = []
    mid3_w = []

    idx_t3 = bone_to_idx["R_Thumb3"]
    idx_i3 = bone_to_idx["R_Index3"]
    idx_m3 = bone_to_idx["R_Mid3"]

    for i in range(N):
        vx = verts[i, 0]
        if vx < 0.30:
            continue
        b_row = np.zeros(K, dtype=np.int32)
        w_row = np.zeros(K, dtype=np.float64)
        is_left = False
        for k in range(K):
            wk = float(raw_weights[i, k])
            if wk <= 1e-8:
                continue
            name = _decode_bone_name(raw_bones[i, k])
            bi = map_name(name)
            if bi == -2:
                is_left = True
                break
            if bi < 0:
                bi = bone_to_idx["R_Hand"]
            b_row[k] = bi
            w_row[k] = wk
        if is_left:
            continue
        w_sum = float(np.sum(w_row))
        if w_sum <= 1e-8:
            b_row[0] = bone_to_idx["R_Hand"]
            w_row[0] = 1.0
        else:
            w_row /= w_sum

        keep_rows.append(i)
        mapped_b.append(b_row)
        mapped_w.append(w_row)
        thumb3_w.append(float(np.sum(w_row[b_row == idx_t3])))
        index3_w.append(float(np.sum(w_row[b_row == idx_i3])))
        mid3_w.append(float(np.sum(w_row[b_row == idx_m3])))

    if not keep_rows:
        return _prepare_right_hand_mesh(bind, None)

    v_r = verts[keep_rows]
    b_arr = np.asarray(mapped_b, dtype=np.int32)
    w_arr = np.asarray(mapped_w, dtype=np.float64)
    bind_origins = np.array([bind[b] for b in bone_list], dtype=np.float64)
    d_bind = v_r[:, None, :] - bind_origins[b_arr]

    t3_arr = np.asarray(thumb3_w, dtype=np.float64)
    i3_arr = np.asarray(index3_w, dtype=np.float64)
    m3_arr = np.asarray(mid3_w, dtype=np.float64)

    idx_thumb_tip = np.where(t3_arr >= 0.45)[0]
    if idx_thumb_tip.size < 4:
        idx_thumb_tip = np.argsort(t3_arr)[-min(20, len(t3_arr)) :]

    idx_index_tip = np.where(i3_arr >= 0.45)[0]
    if idx_index_tip.size < 4:
        idx_index_tip = np.argsort(i3_arr)[-min(20, len(i3_arr)) :]

    idx_mid_tip = np.where(m3_arr >= 0.45)[0]
    if idx_mid_tip.size < 4:
        idx_mid_tip = np.argsort(m3_arr)[-min(16, len(m3_arr)) :]

    # Subsample indices for fast stage-1 optimization while preserving all tip vertices
    n_r = v_r.shape[0]
    if n_r > 360:
        stride = max(1, n_r // 240)
        fast_idx = np.unique(
            np.concatenate(
                [
                    np.arange(0, n_r, stride),
                    idx_thumb_tip,
                    idx_index_tip,
                    idx_mid_tip,
                ]
            )
        )
    else:
        fast_idx = np.arange(n_r)

    return {
        "v0": v_r,
        "b_idx": b_arr,
        "w": w_arr,
        "d_bind": d_bind,
        "bone_list": bone_list,
        "idx_thumb_tip": idx_thumb_tip,
        "idx_index_tip": idx_index_tip,
        "idx_mid_tip": idx_mid_tip,
        "fast_idx": fast_idx,
        "is_synthetic": is_synthetic,
    }


def _skin_mesh(mesh, bone_pos_dict, bone_rot_dict, subset_idx=None):
    bone_list = mesh["bone_list"]
    P = np.array([bone_pos_dict[b] for b in bone_list], dtype=np.float64)
    R = np.array([bone_rot_dict[b] for b in bone_list], dtype=np.float64)

    if subset_idx is None:
        b_idx = mesh["b_idx"]
        w = mesh["w"]
        d_bind = mesh["d_bind"]
    else:
        b_idx = mesh["b_idx"][subset_idx]
        w = mesh["w"][subset_idx]
        d_bind = mesh["d_bind"][subset_idx]

    N, K = b_idx.shape
    out = np.zeros((N, 3), dtype=np.float64)
    for k in range(K):
        bk = b_idx[:, k]
        wk = w[:, k]
        if not np.any(wk > 0.0):
            continue
        rot_d = np.einsum("nij,nj->ni", R[bk], d_bind[:, k, :])
        out += wk[:, None] * (P[bk] + rot_d)
    return out


class Performance:
    """20-second DESPITE cafe customer espresso interaction controller."""

    def __init__(self, bind, root_pos, hand_data=None):
        self.bind = {k: np.asarray(v, dtype=np.float64).reshape(3) for k, v in bind.items()}
        self.root_pos = np.asarray(root_pos, dtype=np.float64).reshape(3)
        self.R_root = _rot_z(math.pi)
        self.q_root = _mat_to_quat_wxyz(self.R_root)

        self.handle_segs = handle_segments()
        self._hA, self._hAB, self._hAB_sq, self._hR = _handle_arrays(self.handle_segs)

        self.cup_rest_pos = CUP_REST_POS.copy()
        self.cup_rest_rot = np.eye(3, dtype=np.float64)

        self.mag_pos = MAGAZINE_POS.copy()
        self.mag_quat = _mat_to_quat_wxyz(_rot_z(MAGAZINE_YAW_RAD))

        self._r_mesh = _prepare_right_hand_mesh(self.bind, hand_data)

        # Solve & verify cup-local right-hand grasp pose offline on actual skinned vertices
        self._solve_grasp_pose()
        self._verify_pregrasp_sweep()
        self._precompute_sip_anchor()

    def _actor_to_world_pos(self, p_act):
        return self.root_pos + self.R_root @ p_act

    def _world_to_actor_pos(self, p_w):
        return self.R_root.T @ (p_w - self.root_pos)

    def _actor_to_cup_rest_pos(self, p_act):
        return self._actor_to_world_pos(p_act) - self.cup_rest_pos

    def _right_hand_pose_in_cup(self, hand_pos_cup, hand_rot_cup, finger_params):
        shoulder_cup = self._actor_to_cup_rest_pos(self.bind["fabric_R_upper"])
        pole_cup = self.R_root @ np.array([0.55, -0.45, -0.70], dtype=np.float64)
        _, elbow_cup, lower_rot_cup, wrist_clamped = _solve_arm_ik(
            self.bind, "R", shoulder_cup, hand_pos_cup, hand_rot_cup, pole_cup
        )
        f_rots = _right_finger_local_rots(finger_params)
        pos_d, rot_d = _fk_hand_bones(self.bind, "R", wrist_clamped, hand_rot_cup, f_rots)
        pos_d["fabric_R_lower"] = elbow_cup
        rot_d["fabric_R_lower"] = lower_rot_cup
        return pos_d, rot_d, lower_rot_cup

    def _initial_grasp_frame(self):
        x_h = _norm(np.array([0.42, -0.82, -0.39], dtype=np.float64))
        y_raw = np.array([0.50, 0.02, 0.866], dtype=np.float64)
        y_h = _norm(y_raw - float(np.dot(y_raw, x_h)) * x_h)
        z_h = np.cross(x_h, y_h)
        R_init = np.column_stack((x_h, y_h, z_h))
        p_init = np.array([-0.168, 0.044, 0.045], dtype=np.float64)
        f_init = np.array(
            [
                -0.52,  # t_abd_x
                0.38,   # t_flex_y
                -0.34,  # t_adduct_z
                0.28,   # t_mcp_y
                0.28,   # t_ip_y
                0.56,   # i_mcp_y
                0.86,   # i_pip_y
                0.50,   # i_dip_y
                0.88,   # mid_curl
                1.00,   # rp_curl
            ],
            dtype=np.float64,
        )
        return p_init, R_init, f_init

    def _solve_grasp_pose(self):
        p_init, R_init, f_init = self._initial_grasp_frame()
        x0 = np.concatenate([p_init, np.zeros(3, dtype=np.float64), f_init])

        bounds = [
            (-0.215, -0.115),  # tx
            (-0.020, 0.095),   # ty
            (0.015, 0.090),    # tz
            (-0.42, 0.42),     # rx
            (-0.42, 0.42),     # ry
            (-0.45, 0.45),     # rz
            (-0.95, -0.15),    # t_abd_x
            (0.05, 0.85),      # t_flex_y
            (-0.75, 0.10),     # t_adduct_z
            (0.05, 0.90),      # t_mcp_y
            (0.05, 0.95),      # t_ip_y
            (0.15, 1.30),      # i_mcp_y
            (0.20, 1.55),      # i_pip_y
            (0.10, 1.15),      # i_dip_y
            (0.45, 1.35),      # mid_curl
            (0.60, 1.40),      # rp_curl
        ]
        lb = np.array([b[0] for b in bounds], dtype=np.float64)
        ub = np.array([b[1] for b in bounds], dtype=np.float64)

        mesh = self._r_mesh
        fast_idx = mesh["fast_idx"]
        t_tip_all = mesh["idx_thumb_tip"]
        i_tip_all = mesh["idx_index_tip"]
        m_tip_all = mesh["idx_mid_tip"]

        # Map tip indices into fast_idx coordinates for Stage 1
        fast_map = {int(orig): pos for pos, orig in enumerate(fast_idx)}
        t_tip_fast = np.array([fast_map[int(i)] for i in t_tip_all], dtype=np.int32)
        i_tip_fast = np.array([fast_map[int(i)] for i in i_tip_all], dtype=np.int32)
        m_tip_fast = np.array([fast_map[int(i)] for i in m_tip_all], dtype=np.int32)

        table_z_cup = TABLETOP_Z - self.cup_rest_pos[2]

        def unpack(x):
            xc = np.clip(x, lb, ub)
            p = xc[0:3]
            R = R_init @ _rotvec_to_mat(xc[3:6])
            f = xc[6:16]
            return p, R, f, xc

        def make_objective(use_fast):
            sub = fast_idx if use_fast else None
            t_idx = t_tip_fast if use_fast else t_tip_all
            i_idx = i_tip_fast if use_fast else i_tip_all
            m_idx = m_tip_fast if use_fast else m_tip_all

            def loss(x):
                p, R, f, xc = unpack(x)
                bound_pen = 2000.0 * float(np.sum((x - xc) ** 2))

                pos_d, rot_d, lower_rot = self._right_hand_pose_in_cup(p, R, f)
                pts = _skin_mesh(mesh, pos_d, rot_d, subset_idx=sub)

                sdf_h, c_h = _handle_sdf_and_closest(
                    pts, self._hA, self._hAB, self._hAB_sq, self._hR
                )
                sdf_c = _cup_body_sdf(pts)
                z_floor = _saucer_surface_z_cup(pts)

                # Hard physical clearances
                cup_viol = np.maximum(0.0045 - sdf_c, 0.0)
                pen_cup = 3.0e5 * float(np.sum(cup_viol * cup_viol)) + 4.0e3 * float(np.max(cup_viol))

                # Keep-out above coffee opening (never hover/dip over coffee)
                rho = np.hypot(pts[:, 0], pts[:, 1])
                over_rim_r = np.maximum(CUP_RADIUS + 0.004 - rho, 0.0)
                over_rim_z = np.maximum(pts[:, 2] - 0.022, 0.0)
                over_rim = np.minimum(over_rim_r, over_rim_z)
                pen_coffee = 3.0e5 * float(np.sum(over_rim * over_rim))

                # Forbid flesh sinking into handle tube
                h_pen_viol = np.maximum(-0.00005 - sdf_h, 0.0)
                pen_handle_in = 4.0e5 * float(np.sum(h_pen_viol * h_pen_viol)) + 5.0e3 * float(np.max(h_pen_viol))

                # Saucer & tabletop clearance (strictly above z=0.886 + 5 mm margin)
                saucer_viol = np.maximum((z_floor + 0.0045) - pts[:, 2], 0.0)
                table_viol = np.maximum((table_z_cup + 0.0065) - pts[:, 2], 0.0)
                pen_floor = (
                    2.5e5 * float(np.sum(saucer_viol * saucer_viol))
                    + 2.5e5 * float(np.sum(table_viol * table_viol))
                )

                # Target 0.45 mm contact gap for thumb pad and index pad on outer D-handle
                t_sdfs = sdf_h[t_idx]
                i_sdfs = sdf_h[i_idx]
                m_sdfs = sdf_h[m_idx]

                kt = int(np.argmin(t_sdfs))
                ki = int(np.argmin(i_sdfs))
                d_t = float(t_sdfs[kt])
                d_i = float(i_sdfs[ki])
                d_m = float(np.min(m_sdfs))

                target_d = 0.00045
                contact_loss = (
                    8.0e4 * ((d_t - target_d) ** 2 + (d_i - target_d) ** 2)
                    + 1.2e3 * max(0.0, d_m - 0.010) ** 2
                )

                # Ensure contact is on the outer D-handle arc (not near cup wall)
                pt_t = pts[t_idx[kt]]
                pt_i = pts[i_idx[ki]]
                ch_t = c_h[t_idx[kt]]
                ch_i = c_h[i_idx[ki]]

                outer_t = max(0.0, ch_t[0] - (-0.052))
                outer_i = max(0.0, ch_i[0] - (-0.050))
                z_t_err = max(0.0, abs(ch_t[2] - 0.005) - 0.014)
                z_i_err = max(0.0, abs(ch_i[2] - 0.000) - 0.014)
                zone_loss = 3.0e3 * (outer_t ** 2 + outer_i ** 2 + z_t_err ** 2 + z_i_err ** 2)

                # Encourage opposing pinch normals across handle tube (thumb vs index)
                n_t = _norm(pt_t - ch_t)
                n_i = _norm(pt_i - ch_i)
                opp = float(np.dot(n_t, n_i))
                oppose_loss = 4.0 * max(0.0, opp + 0.25) ** 2

                # Natural wrist alignment (minimize wrist bend relative to forearm)
                wrist_rv = _mat_to_rotvec(lower_rot.T @ R)
                wrist_ang = float(np.linalg.norm(wrist_rv))
                wrist_loss = 1.5 * max(0.0, wrist_ang - 0.35) ** 2

                # Soft anatomical posture regularization
                reg = 0.4 * float(np.sum((xc[3:6]) ** 2)) + 0.08 * float(np.sum((xc[6:16] - f_init) ** 2))

                return (
                    bound_pen
                    + pen_cup
                    + pen_coffee
                    + pen_handle_in
                    + pen_floor
                    + contact_loss
                    + zone_loss
                    + oppose_loss
                    + wrist_loss
                    + reg
                )

            return loss

        res1 = minimize(
            make_objective(True),
            x0,
            method="Powell",
            bounds=bounds,
            options={"maxiter": 45, "maxfev": 950, "ftol": 1e-4, "xtol": 1e-3},
        )
        res2 = minimize(
            make_objective(False),
            np.clip(res1.x, lb, ub),
            method="Powell",
            bounds=bounds,
            options={"maxiter": 30, "maxfev": 550, "ftol": 1e-5, "xtol": 5e-4},
        )

        p_opt, R_opt, f_opt, _ = unpack(res2.x)

        # Final deterministic safety polish on full right-hand mesh
        p_opt, f_opt, metrics = self._polish_grasp_contact(p_opt, R_opt, f_opt)

        self.grasp_pos_cup = p_opt
        self.grasp_rot_cup = R_opt
        self.grasp_finger_params = f_opt
        self.grasp_audit = metrics

    def _measure_hand_cup_metrics(self, hand_pos_cup, hand_rot_cup, finger_params):
        mesh = self._r_mesh
        pos_d, rot_d, _ = self._right_hand_pose_in_cup(hand_pos_cup, hand_rot_cup, finger_params)
        pts = _skin_mesh(mesh, pos_d, rot_d, subset_idx=None)

        sdf_h, c_h = _handle_sdf_and_closest(
            pts, self._hA, self._hAB, self._hAB_sq, self._hR
        )
        sdf_c = _cup_body_sdf(pts)
        z_floor = _saucer_surface_z_cup(pts)

        d_thumb = float(np.min(sdf_h[mesh["idx_thumb_tip"]]))
        d_index = float(np.min(sdf_h[mesh["idx_index_tip"]]))
        min_h = float(np.min(sdf_h))
        min_c = float(np.min(sdf_c))
        min_z_world = float(np.min(pts[:, 2]) + self.cup_rest_pos[2])
        min_saucer = float(np.min(pts[:, 2] - z_floor))

        return {
            "thumb_handle_dist_m": d_thumb,
            "index_handle_dist_m": d_index,
            "min_pinch_handle_dist_m": min(d_thumb, d_index),
            "min_all_handle_sdf_m": min_h,
            "min_cup_body_sdf_m": min_c,
            "min_hand_world_z_m": min_z_world,
            "min_saucer_clearance_m": min_saucer,
            "pts": pts,
            "sdf_h": sdf_h,
            "c_h": c_h,
        }

    def _polish_grasp_contact(self, p_opt, R_opt, f_opt):
        p = p_opt.copy()
        f = f_opt.copy()
        for _ in range(12):
            m = self._measure_hand_cup_metrics(p, R_opt, f)
            changed = False
            if m["min_cup_body_sdf_m"] < 0.0032:
                shift = 0.0035 - m["min_cup_body_sdf_m"]
                p[0] -= shift
                changed = True
            if m["min_hand_world_z_m"] < TABLETOP_Z + 0.004:
                p[2] += (TABLETOP_Z + 0.0045) - m["min_hand_world_z_m"]
                changed = True
            if m["min_all_handle_sdf_m"] < -0.0001:
                idx_pen = int(np.argmin(m["sdf_h"]))
                out_dir = _norm(m["pts"][idx_pen] - m["c_h"][idx_pen])
                if float(np.linalg.norm(out_dir)) < 1e-6:
                    out_dir = np.array([-1.0, 0.0, 0.2], dtype=np.float64)
                    out_dir = _norm(out_dir)
                step = (-m["min_all_handle_sdf_m"]) + 0.00025
                p += step * out_dir
                changed = True
            if not changed:
                break

        # If pinch drifted slightly past 1.3 mm after backoff, nudge finger flexion slightly
        m = self._measure_hand_cup_metrics(p, R_opt, f)
        if m["min_pinch_handle_dist_m"] > 0.0013:
            for _ in range(8):
                if m["thumb_handle_dist_m"] > 0.0012:
                    f[3] = min(0.95, f[3] + 0.03)
                    f[4] = min(0.98, f[4] + 0.03)
                if m["index_handle_dist_m"] > 0.0012:
                    f[5] = min(1.32, f[5] + 0.025)
                    f[6] = min(1.58, f[6] + 0.025)
                m_try = self._measure_hand_cup_metrics(p, R_opt, f)
                if (
                    m_try["min_all_handle_sdf_m"] >= -0.0001
                    and m_try["min_cup_body_sdf_m"] >= 0.003
                ):
                    m = m_try
                    if m["min_pinch_handle_dist_m"] <= 0.0012:
                        break
                else:
                    break

        clean_metrics = {
            k: v for k, v in m.items() if k not in ("pts", "sdf_h", "c_h")
        }
        return p, f, clean_metrics

    def _verify_pregrasp_sweep(self):
        """Calibrate collision-free pre-grasp open pose and approach vector."""
        self.approach_dir_cup = _norm(np.array([-0.88, 0.28, 0.38], dtype=np.float64))
        self.pregrasp_dist = 0.052

        # Open pinch jaws cleanly from solved grip pose
        f_open = self.grasp_finger_params.copy()
        f_open[0] = max(-0.98, f_open[0] + 0.10)  # relax thumb abduction slightly upward
        f_open[1] = max(0.02, f_open[1] - 0.22)   # unflex thumb CMC
        f_open[2] = min(0.18, f_open[2] + 0.20)   # open thumb away from index
        f_open[3] = max(0.02, f_open[3] - 0.22)   # unflex thumb MCP
        f_open[4] = max(0.02, f_open[4] - 0.22)   # unflex thumb IP
        f_open[5] = max(0.10, f_open[5] - 0.28)   # unflex index MCP
        f_open[6] = max(0.15, f_open[6] - 0.38)   # unflex index PIP
        f_open[7] = max(0.05, f_open[7] - 0.28)   # unflex index DIP
        f_open[8] = max(0.32, f_open[8] - 0.30)   # open middle finger
        f_open[9] = max(0.42, f_open[9] - 0.26)   # relax ring/pinky
        self.open_finger_params = f_open

        # Relaxed natural rest hand pose (soft progressive finger curl)
        self.rest_finger_params = np.array(
            [-0.36, 0.24, -0.22, 0.18, 0.15, 0.34, 0.48, 0.28, 0.56, 0.74],
            dtype=np.float64,
        )

        # Verify approach sweep clears cup, handle, saucer, and tabletop
        best_extra_z = 0.0
        for trial in range(5):
            d_app = _norm(self.approach_dir_cup + np.array([0.0, 0.0, best_extra_z], dtype=np.float64))
            worst_cup = 1.0
            worst_handle = 1.0
            worst_z = 10.0
            for s_u in (0.15, 0.35, 0.60, 0.85, 1.0):
                p_c = self.grasp_pos_cup + (s_u * self.pregrasp_dist) * d_app
                # Fingers are open during approach (s_u > 0.25), transitioning to grip as s_u -> 0
                f_u = _s5(max(0.0, min(1.0, (s_u - 0.05) / 0.35)))
                f_c = (1.0 - f_u) * self.grasp_finger_params + f_u * self.open_finger_params
                m = self._measure_hand_cup_metrics(p_c, self.grasp_rot_cup, f_c)
                worst_cup = min(worst_cup, m["min_cup_body_sdf_m"])
                worst_handle = min(worst_handle, m["min_all_handle_sdf_m"])
                worst_z = min(worst_z, m["min_hand_world_z_m"])

            if worst_cup >= 0.0028 and worst_handle >= -0.0002 and worst_z >= TABLETOP_Z + 0.003:
                self.approach_dir_cup = d_app
                self.grasp_audit["pregrasp_min_cup_sdf_m"] = worst_cup
                self.grasp_audit["pregrasp_min_handle_sdf_m"] = worst_handle
                self.grasp_audit["pregrasp_min_world_z_m"] = worst_z
                break
            best_extra_z += 0.12
            self.pregrasp_dist += 0.008
        else:
            self.grasp_audit["pregrasp_min_cup_sdf_m"] = worst_cup
            self.grasp_audit["pregrasp_min_handle_sdf_m"] = worst_handle
            self.grasp_audit["pregrasp_min_world_z_m"] = worst_z

    def _torso_and_head_local(self, t):
        """Continuous subtle torso weight transfer, clavicular lead, and gaze tracking."""
        # Gentle organic breathing (non-piston, sub-2mm shoulder/chest rise)
        breath = math.sin(2.0 * math.pi * t / 4.6)

        # Weight transfer into reach/grip/release (subtle forward lean & right yaw)
        reach_w = _pulse(t, 1.4, 5.4, 6.2, 8.8) + 0.85 * _pulse(t, 12.6, 14.8, 15.6, 18.4)
        sip_w = _pulse(t, 7.2, 10.2, 11.1, 13.8)

        # Torso rotation pivoted at root origin (0,0,0) -> zero root/foot drift!
        torso_pitch_x = math.radians(-1.55 * reach_w - 0.45 * sip_w - 0.18 * breath)
        torso_yaw_z = math.radians(-2.60 * reach_w - 1.10 * sip_w)
        torso_roll_y = math.radians(0.85 * reach_w - 0.55 * sip_w)
        R_torso = _rot_z(torso_yaw_z) @ _rot_y(torso_roll_y) @ _rot_x(torso_pitch_x)

        # Head gaze leads reach/return (~0.35 s anticipation) and tilts slightly back at sip
        look_cup = _pulse(t, 1.05, 4.6, 6.4, 8.6) + 0.92 * _pulse(t, 12.1, 14.4, 16.0, 18.6)
        sip_head = _pulse(t, 8.0, 10.2, 11.1, 13.2)
        sip_peak = _pulse(t, 9.6, 10.5, 10.9, 11.8)

        # Base calm cafe gaze slightly down and toward counter work
        head_pitch_x = math.radians(
            -7.5 - 11.5 * look_cup + 4.0 * sip_head + 3.5 * sip_peak - 0.5 * breath
        )
        head_yaw_z = math.radians(-5.5 - 8.0 * look_cup + 4.0 * sip_head)
        head_roll_y = math.radians(1.5 + 3.0 * look_cup - 2.0 * sip_head)
        R_head_rel = _rot_z(head_yaw_z) @ _rot_y(head_roll_y) @ _rot_x(head_pitch_x)

        R_head = R_torso @ R_head_rel
        p_head = R_torso @ self.bind["fabric_head"] + np.array(
            [0.0, 0.002 * reach_w, 0.0012 * breath], dtype=np.float64
        )

        # Subtle clavicle / shoulder lead & counterbalance
        r_sh_offset = np.array(
            [
                0.005 * reach_w - 0.004 * sip_w,
                0.018 * reach_w + 0.008 * sip_w,
                -0.007 * reach_w + 0.011 * sip_w + 0.0015 * breath,
            ],
            dtype=np.float64,
        )
        l_sh_offset = np.array(
            [
                -0.003 * reach_w,
                -0.007 * reach_w - 0.004 * sip_w,
                0.002 * reach_w - 0.003 * sip_w + 0.0015 * breath,
            ],
            dtype=np.float64,
        )
        p_r_shoulder = R_torso @ self.bind["fabric_R_upper"] + r_sh_offset
        p_l_shoulder = R_torso @ self.bind["fabric_L_upper"] + l_sh_offset

        return R_torso, p_head, R_head, p_r_shoulder, p_l_shoulder

    def _precompute_sip_anchor(self):
        """Derive peak sip cup pose from actual rig head + local [0, 0.08, 0.055]."""
        t_peak = 10.65
        _, p_head_act, R_head_act, _, _ = self._torso_and_head_local(t_peak)
        p_head_w = self._actor_to_world_pos(p_head_act)
        R_head_w = self.R_root @ R_head_act
        lips_w = p_head_w + R_head_w @ LIPS_LOCAL_OFFSET

        # Cup tilt at peak sip: -27 deg around world +X tips the +Y rim toward lips
        # +12 deg world Z yaw keeps the handle forward-right for ergonomic elbow flexion
        self.sip_tilt_rad = math.radians(-27.0)
        self.sip_yaw_rad = math.radians(12.0)
        self.cup_sip_rot = _rot_z(self.sip_yaw_rad) @ _rot_x(self.sip_tilt_rad)

        # Drinking rim point on cup-local +Y (facing lips in world +Y)
        rim_local = np.array([0.0, CUP_RADIUS, CUP_HALF_H], dtype=np.float64)
        rim_world_offset = self.cup_sip_rot @ rim_local

        # Place drinking rim 1.5 cm in front of lips (-world Y) and 0.6 cm below lip center
        target_rim_w = lips_w + np.array([0.0, -0.035, -0.009], dtype=np.float64)
        self.cup_sip_pos = target_rim_w - rim_world_offset

        # Also store pre-sip / post-sip smooth intermediate curve control offsets
        self.lips_peak_world = lips_w
        self.grasp_audit["sip_lips_world_m"] = tuple(float(v) for v in lips_w)
        self.grasp_audit["sip_rim_to_lips_dist_m"] = float(np.linalg.norm(target_rim_w - lips_w))
        self.grasp_audit["sip_cup_tilt_deg"] = float(abs(math.degrees(self.sip_tilt_rad)))

        # Parked right hand pose in actor-local space (poised comfortably above tabletop z=0.886)
        self.r_hand_park_act = np.array([0.245, 0.165, 1.005], dtype=np.float64)
        x_p = _norm(np.array([-0.22, 0.88, -0.42], dtype=np.float64))
        y_raw = np.array([-0.42, 0.25, 0.87], dtype=np.float64)
        y_p = _norm(y_raw - float(np.dot(y_raw, x_p)) * x_p)
        z_p = np.cross(x_p, y_p)
        self.r_hand_park_rot_act = np.column_stack((x_p, y_p, z_p))

    def _cup_pose_world(self, t):
        """Continuous C2 cup trajectory: stationary on saucer outside [6.4, 14.8]."""
        t_lift_start = PHASES["lift"][0]    # 6.4
        t_return_end = PHASES["return"][1]  # 14.8
        t_peak = 10.65

        if t <= t_lift_start or t >= t_return_end:
            return self.cup_rest_pos.copy(), self.cup_rest_rot.copy()

        p0 = self.cup_rest_pos
        p_sip = self.cup_sip_pos

        if t <= t_peak:
            u = _s5((t - t_lift_start) / (t_peak - t_lift_start))
            # Smooth vertical lift-off from saucer, gentle outward bow, then sweeping to lips
            c1 = p0 + np.array([-0.012, 0.015, 0.24], dtype=np.float64)
            c2 = p_sip + np.array([-0.032, -0.085, -0.05], dtype=np.float64)
            pos = _bezier_cubic(p0, c1, c2, p_sip, u)
            # Keep cup level while clearing saucer, then smoothly tilt into sip
            u_tilt = _s5(max(0.0, min(1.0, (t - 8.2) / (t_peak - 8.2))))
            u_yaw = _s5(max(0.0, min(1.0, (t - 6.7) / (t_peak - 6.7))))
        else:
            u = _s5((t - t_peak) / (t_return_end - t_peak))
            # Distinct asymmetrical return arc, leveling out cleanly before saucer touchdown
            c1 = p_sip + np.array([-0.018, -0.105, -0.07], dtype=np.float64)
            c2 = p0 + np.array([-0.008, 0.008, 0.22], dtype=np.float64)
            pos = _bezier_cubic(p_sip, c1, c2, p0, u)
            u_tilt = 1.0 - _s5(max(0.0, min(1.0, (t - 10.85) / (13.9 - 10.85))))
            u_yaw = 1.0 - _s5(max(0.0, min(1.0, (t - 11.0) / (14.4 - 11.0))))

        # Enforce saucer floor invariant during lift/return
        pos[2] = max(pos[2], self.cup_rest_pos[2])

        tilt = self.sip_tilt_rad * u_tilt
        yaw = self.sip_yaw_rad * u_yaw
        rot = _rot_z(yaw) @ _rot_x(tilt)
        return pos, rot

    def _right_hand_world_and_fingers(self, t, cup_pos_w, cup_rot_w):
        """Continuous right wrist pose and finger articulation across all 20s."""
        # Locked grasp world pose on current cup
        p_grip_w = cup_pos_w + cup_rot_w @ self.grasp_pos_cup
        R_grip_w = cup_rot_w @ self.grasp_rot_cup

        # Pre-grasp world pose (offset along collision-free approach direction on saucer)
        p_pre_w = self.cup_rest_pos + self.grasp_pos_cup + self.pregrasp_dist * self.approach_dir_cup
        R_pre_w = self.grasp_rot_cup @ _rot_y(math.radians(-6.0))

        # Parked world pose (with subtle living idle drift, always well above tabletop)
        idle_wave = math.sin(2.0 * math.pi * t / 5.2)
        p_park_act = self.r_hand_park_act + np.array(
            [0.002 * idle_wave, 0.003 * math.cos(2.0 * math.pi * t / 6.0), 0.0025 * idle_wave],
            dtype=np.float64,
        )
        p_park_w = self._actor_to_world_pos(p_park_act)
        R_park_w = self.R_root @ self.r_hand_park_rot_act @ _rot_y(math.radians(2.0 * idle_wave))

        t_reach_0 = PHASES["reach"][0]      # 1.4
        t_grip_0 = PHASES["grip"][0]        # 5.2
        t_lift_0 = PHASES["lift"][0]        # 6.4
        t_rel_0 = PHASES["release"][0]      # 14.8
        t_with_0 = PHASES["withdraw"][0]    # 16.0
        t_with_1 = PHASES["withdraw"][1]    # 18.6

        if t <= t_reach_0:
            p_w = p_park_w
            R_w = R_park_w
            f_params = self.rest_finger_params.copy()

        elif t < t_lift_0:
            # Continuous fluid reach -> pre-grasp -> grip (no start-stop at t=5.2!)
            # Wrist glides continuously from t=1.4 to t=6.05 along an arched curve
            t_arrive = 6.05
            u_all = _s5((t - t_reach_0) / (t_arrive - t_reach_0))

            # Control points route cleanly outside cup and above tabletop into approach vector
            c1 = p_park_w + np.array([-0.055, -0.055, 0.048], dtype=np.float64)
            c2 = p_pre_w + 0.85 * self.pregrasp_dist * self.approach_dir_cup + np.array([0.0, 0.0, 0.022], dtype=np.float64)
            p_w = _bezier_cubic(p_park_w, c1, c2, p_grip_w, u_all)

            # Guarantee hand rides strictly above approach clearance and tabletop
            u_rot = _s5(max(0.0, min(1.0, (t - 1.6) / (5.85 - 1.6))))
            R_base = _slerp_mat(R_park_w, R_grip_w, u_rot)
            # Subtle fluid wrist follow-through extension mid-reach, zero by arrival
            wrist_lead = math.radians(-8.0) * math.sin(math.pi * u_rot) * (1.0 - _ramp(t, 4.6, 5.7))
            R_w = R_base @ _rot_y(wrist_lead)

            # Fingers lead-open during reach, then smoothly curl onto handle before lift
            u_open = _ramp(t, 2.8, 4.6)
            u_close = _ramp(t, 4.75, 5.52)
            f_pre = (1.0 - u_open) * self.rest_finger_params + u_open * self.open_finger_params
            f_params = (1.0 - u_close) * f_pre + u_close * self.grasp_finger_params

        elif t <= t_rel_0:
            # Rigidly locked to moving cup throughout lift, sip, and return!
            p_w = p_grip_w
            R_w = R_grip_w
            f_params = self.grasp_finger_params.copy()

        elif t < t_with_1:
            # Release -> withdraw: fingers open FIRST (14.85..15.65), wrist lags slightly then glides out
            u_uncurl = _ramp(t, 15.50, 16.25)
            u_relax = _ramp(t, 16.2, 18.2)
            f_open_phase = (1.0 - u_uncurl) * self.grasp_finger_params + u_uncurl * self.open_finger_params
            f_params = (1.0 - u_relax) * f_open_phase + u_relax * self.rest_finger_params

            t_depart = 15.15
            u_out = _s5(max(0.0, min(1.0, (t - t_depart) / (t_with_1 - t_depart))))
            c1 = p_pre_w + 0.75 * self.pregrasp_dist * self.approach_dir_cup + np.array([0.0, 0.0, 0.025], dtype=np.float64)
            c2 = p_park_w + np.array([-0.045, -0.045, 0.040], dtype=np.float64)
            p_w = _bezier_cubic(p_grip_w, c1, c2, p_park_w, u_out)

            u_rot = _s5(max(0.0, min(1.0, (t - 15.3) / (t_with_1 - 15.3))))
            R_base = _slerp_mat(R_grip_w, R_park_w, u_rot)
            wrist_trail = math.radians(7.0) * math.sin(math.pi * u_rot) * _ramp(t, 15.3, 16.1)
            R_w = R_base @ _rot_y(wrist_trail)

        else:
            p_w = p_park_w
            R_w = R_park_w
            f_params = self.rest_finger_params.copy()

        return p_w, R_w, f_params

    def _left_hand_actor(self, t):
        """Relaxed left arm at own side/front with subtle counterbalance and distinct finger flex."""
        reach_w = _pulse(t, 1.4, 5.4, 6.2, 8.8) + 0.85 * _pulse(t, 12.6, 14.8, 15.6, 18.4)
        sip_w = _pulse(t, 7.2, 10.2, 11.1, 13.8)
        sway = math.sin(2.0 * math.pi * t / 6.4)

        # Actor-local left wrist rests near left hip/front (ly=+0.085, lz=0.965 -> clear of tabletop)
        p_l_act = np.array(
            [
                -0.308 - 0.008 * reach_w + 0.010 * sip_w + 0.003 * sway,
                0.115 - 0.012 * reach_w + 0.016 * sip_w + 0.003 * math.cos(2.0 * math.pi * t / 7.2),
                0.968 - 0.008 * reach_w + 0.014 * sip_w + 0.004 * sway,
            ],
            dtype=np.float64,
        )

        # Left hand bind frame: fingers along -X, thumb +Y, palm -Z.
        # Point fingers gently forward-down-inward, palm facing inward toward body.
        x_neg = _norm(np.array([0.22 + 0.06 * sip_w, 0.42 + 0.05 * sip_w, -0.88], dtype=np.float64))
        x_l = -x_neg  # bind +X axis is opposite left fingers
        y_raw = np.array([0.25, 0.88, 0.40], dtype=np.float64)
        y_l = _norm(y_raw - float(np.dot(y_raw, x_l)) * x_l)
        z_l = np.cross(x_l, y_l)
        R_l_act = np.column_stack((x_l, y_l, z_l)) @ _rot_x(math.radians(3.0 * sway))

        f_l_rots = _left_finger_local_rots(relax_mod=0.35 * sip_w + 0.20 * sway)
        return p_l_act, R_l_act, f_l_rots

    def sample(self, t):
        t = float(max(0.0, min(DURATION, float(t))))

        R_torso, p_head_act, R_head_act, p_r_sh_act, p_l_sh_act = self._torso_and_head_local(t)
        cup_pos_w, cup_rot_w = self._cup_pose_world(t)

        r_hand_w, r_hand_rot_w, r_f_params = self._right_hand_world_and_fingers(
            t, cup_pos_w, cup_rot_w
        )
        r_hand_act = self._world_to_actor_pos(r_hand_w)
        r_hand_rot_act = self.R_root.T @ r_hand_rot_w

        # Smoothly varying right elbow pole (drops naturally on reach, opens slightly on lift/sip)
        elev_u = max(0.0, min(1.0, (r_hand_act[2] - 0.94) / 0.56))
        r_pole_act = _norm(
            np.array(
                [0.52 + 0.24 * elev_u, -0.42 + 0.14 * elev_u, -0.74 + 0.10 * elev_u],
                dtype=np.float64,
            )
        )
        r_upper_rot, r_elbow_act, r_lower_rot, r_wrist_act = _solve_arm_ik(
            self.bind, "R", p_r_sh_act, r_hand_act, r_hand_rot_act, r_pole_act
        )
        # Vertex-weighted fit of the fingertip pad to the opposite side of the handle.
        pinch = _ramp(t, 4.1, 5.45) * (1 - _ramp(t, 15.55, 16.5))
        r_f_params = r_f_params.copy()
        r_f_params[5:8] += pinch * np.array([0.07965241,-0.01792271,-0.03509748])
        r_f_rots = _right_finger_local_rots(r_f_params)
        r_f_rots["R_Index1"] = _rot_y(r_f_params[5]) @ _rot_z(0.04 - 0.22714088 * pinch)
        # Let the unoccupied fingers fold under and fan away from the two pinching pads.
        for digit,spread,curl in [('Mid',-.17,.24),('Ring',-.12,.16),('Pinky',-.11,.08)]:
            node='R_'+digit+'1'
            r_f_rots[node] = r_f_rots[node] @ _rot_z(spread*pinch) @ _rot_y(curl*pinch)
        support_curl = _ramp(t,3.6,5.0) * (1-_ramp(t,16.0,16.95))
        r_f_rots['R_Mid1'] = r_f_rots['R_Mid1'] @ _rot_z(-.14*support_curl) @ _rot_y(.66*support_curl)
        r_pos_act, r_rot_act = _fk_hand_bones(
            self.bind, "R", r_wrist_act, r_hand_rot_act, r_f_rots
        )

        # Left arm counterbalance
        l_hand_act, l_hand_rot_act, l_f_rots = self._left_hand_actor(t)
        l_pole_act = _norm(np.array([-0.55, -0.48, -0.68], dtype=np.float64))
        l_upper_rot, l_elbow_act, l_lower_rot, l_wrist_act = _solve_arm_ik(
            self.bind, "L", p_l_sh_act, l_hand_act, l_hand_rot_act, l_pole_act
        )
        l_pos_act, l_rot_act = _fk_hand_bones(
            self.bind, "L", l_wrist_act, l_hand_rot_act, l_f_rots
        )

        # Assemble all actor-local bone poses
        pos_act = {}
        rot_act = {}

        # Grounded root and stationary feet/legs (0.0 mm foot drift)
        pos_act["operator_standing"] = self.bind["operator_standing"].copy()
        rot_act["operator_standing"] = R_torso
        for leg_name in ("fabric_L_leg", "fabric_R_leg"):
            if leg_name in self.bind:
                pos_act[leg_name] = self.bind[leg_name].copy()
                rot_act[leg_name] = np.eye(3, dtype=np.float64)

        pos_act["fabric_head"] = p_head_act
        rot_act["fabric_head"] = R_head_act

        pos_act["fabric_R_upper"] = p_r_sh_act
        rot_act["fabric_R_upper"] = r_upper_rot
        pos_act["fabric_R_lower"] = r_elbow_act
        rot_act["fabric_R_lower"] = r_lower_rot

        pos_act["fabric_L_upper"] = p_l_sh_act
        rot_act["fabric_L_upper"] = l_upper_rot
        pos_act["fabric_L_lower"] = l_elbow_act
        rot_act["fabric_L_lower"] = l_lower_rot

        pos_act.update(r_pos_act)
        rot_act.update(r_rot_act)
        pos_act.update(l_pos_act)
        rot_act.update(l_rot_act)

        # Convert EVERY bind bone to world space (pos, MuJoCo wxyz quat)
        positions = {}
        quats = {}
        for name, b_orig in self.bind.items():
            if name in pos_act:
                pa = pos_act[name]
                Ra = rot_act[name]
            else:
                pa = R_torso @ b_orig
                Ra = R_torso
            positions[name] = self._actor_to_world_pos(pa)
            quats[name] = _mat_to_quat_wxyz(self.R_root @ Ra)

        props = {
            "espresso_cup": (cup_pos_w, _mat_to_quat_wxyz(cup_rot_w)),
            "cafe_paper": (self.mag_pos.copy(), self.mag_quat.copy()),
        }
        return positions, quats, props
