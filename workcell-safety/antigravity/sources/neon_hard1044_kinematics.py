"""Native MuJoCo robot trajectory, IK, locomotion, and dexterous-hand library.

Provides pure, non-mutating kinematics and continuous trajectory primitives for
paired MuJoCo simulation studies:
- Damped least-squares site IK (`solve`) operating on a cloned scratch `MjData`
- $C^2$-continuous minimum-jerk keyframe interpolation with holds (`keyframe`)
- Continuous body-frame differential-drive wheel tracking for Clearpath Husky
- Alternating diagonal trot gait and exact sagittal-plane leg IK for Boston
  Dynamics Spot (no zero-motion marching, no foot teleport)
- Side-safe Fourier GR-1 five-finger curl interpolation in native joint limits
"""

from __future__ import annotations

import math
import re
from typing import Dict, Mapping, Optional, Sequence, Tuple, Union

import mujoco
import numpy as np

__all__ = [
    "solve",
    "keyframe",
    "keyframe_deriv",
    "wrap_angle",
    "route_pose_and_vel",
    "husky_wheel_velocities",
    "husky_route_wheels",
    "spot_sagittal_ik",
    "spot_leg_ik",
    "spot_gait",
    "spot_route_gait",
    "GR1_CHANNELS",
    "GR1_RELEASE",
    "GR1_PREGRASP",
    "GR1_POWER_GRASP",
    "GR1_PINCH_GRASP",
    "GR1_PRESETS",
    "gr1_find_hand_joints",
    "gr1_finger_targets",
    "gr1_interpolate_hand",
]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SPOT_LEGS: Tuple[str, ...] = ("fl", "fr", "hl", "hr")
_SPOT_DEFAULT_PHASES: Dict[str, float] = {
    "fl": 0.0,
    "hr": 0.0,
    "fr": 0.5,
    "hl": 0.5,
}
_SPOT_DEFAULT_HIP_XY: Dict[str, Tuple[float, float]] = {
    "fl": (0.29785, 0.055),
    "fr": (0.29785, -0.055),
    "hl": (-0.29785, 0.055),
    "hr": (-0.29785, -0.055),
}
_THUMB_SPREAD_TOKENS = frozenset(
    {"spread", "yaw", "abd", "abduction", "cmc", "roll", "oppose", "opposition", "rot", "rotation"}
)


def _min_jerk(s: float) -> float:
    """Minimum-jerk easing polynomial on [0, 1] with zero end vel/acc."""
    s = 0.0 if s <= 0.0 else (1.0 if s >= 1.0 else float(s))
    s2 = s * s
    s3 = s2 * s
    return s3 * (10.0 - 15.0 * s + 6.0 * s2)


def _min_jerk_d1(s: float) -> float:
    """First derivative of minimum-jerk easing with respect to s in [0, 1]."""
    if s <= 0.0 or s >= 1.0:
        return 0.0
    u = 1.0 - s
    return 30.0 * s * s * u * u


def _min_jerk_d2(s: float) -> float:
    """Second derivative of minimum-jerk easing with respect to s in [0, 1]."""
    if s <= 0.0 or s >= 1.0:
        return 0.0
    return 60.0 * s * (1.0 - s) * (1.0 - 2.0 * s)


def _project_so3(R: np.ndarray) -> np.ndarray:
    """Project a 3x3 matrix onto SO(3) via SVD."""
    mat = np.asarray(R, dtype=np.float64)
    if mat.shape != (3, 3):
        raise ValueError(f"Expected 3x3 rotation matrix, got shape {mat.shape}")
    u, _, vt = np.linalg.svd(mat)
    rot = u @ vt
    if np.linalg.det(rot) < 0.0:
        u[:, -1] *= -1.0
        rot = u @ vt
    return rot


def _world_rot_error(R_target: np.ndarray, R_cur: np.ndarray) -> np.ndarray:
    """World-frame axis-angle error omega such that exp([omega]_x) @ R_cur = R_target."""
    R_err = np.ascontiguousarray(R_target @ R_cur.T, dtype=np.float64)
    q_err = np.empty(4, dtype=np.float64)
    mujoco.mju_mat2Quat(q_err, R_err.ravel())
    if q_err[0] < 0.0:
        q_err = -q_err
    v = q_err[1:4]
    v_norm = float(np.linalg.norm(v))
    if v_norm < 1e-12:
        return 2.0 * v
    angle = 2.0 * math.atan2(v_norm, float(q_err[0]))
    return (angle / v_norm) * v


def _clone_data_once(m: mujoco.MjModel, d: mujoco.MjData) -> mujoco.MjData:
    """Clone kinematics-relevant state from d into a fresh scratch MjData once."""
    scratch = mujoco.MjData(m)
    scratch.time = d.time
    scratch.qpos[:] = d.qpos
    scratch.qvel[:] = d.qvel
    if m.na > 0:
        scratch.act[:] = d.act
    if m.nmocap > 0:
        scratch.mocap_pos[:] = d.mocap_pos
        scratch.mocap_quat[:] = d.mocap_quat
    if m.neq > 0 and hasattr(d, "eq_active"):
        scratch.eq_active[:] = d.eq_active
    if m.nu > 0:
        scratch.ctrl[:] = d.ctrl
    return scratch


def _parse_keyframe_rows(rows: Sequence) -> Tuple[np.ndarray, np.ndarray]:
    """Parse keyframe rows into sorted-checked (times[N], coords[N, D])."""
    if rows is None or len(rows) == 0:
        raise ValueError("Keyframe rows must be non-empty.")

    first = rows[0]
    if (
        not isinstance(rows, np.ndarray)
        and len(first) == 2
        and np.ndim(first[1]) >= 1
    ):
        times = np.asarray([float(r[0]) for r in rows], dtype=np.float64)
        coords = np.asarray([np.asarray(r[1], dtype=np.float64).ravel() for r in rows], dtype=np.float64)
    else:
        arr = np.asarray(rows, dtype=np.float64)
        if arr.ndim != 2 or arr.shape[1] < 2:
            raise ValueError("Keyframe rows must have shape (N, 1 + D) with D >= 1.")
        times = arr[:, 0]
        coords = arr[:, 1:]

    if times.shape[0] > 1 and np.any(np.diff(times) < 0.0):
        raise ValueError("Keyframe timestamps must be monotonically non-decreasing.")
    return times, coords


def _tokenize_joint_name(name: str) -> Tuple[str, ...]:
    """Split a joint name into lowercase alphanumeric tokens (handles snake/camelCase)."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return tuple(tok.lower() for tok in re.split(r"[^a-zA-Z0-9]+", spaced) if tok)


# ---------------------------------------------------------------------------
# 1. Damped Least-Squares Site IK (non-mutating)
# ---------------------------------------------------------------------------

# API: solve(m, d, site, joint_ids, target, orientation=None, iterations=40, orientation_weight=0.5, damping=1e-2, singularity_damping=0.15, singularity_threshold=0.05, max_dq=0.25, pos_tol=1e-4, ori_tol=1e-3, nullspace_gain=0.0) -> np.ndarray[(n,)]
def solve(
    m: mujoco.MjModel,
    d: mujoco.MjData,
    site: Union[int, str],
    joint_ids: Sequence[Union[int, str]],
    target: Sequence[float],
    orientation: Optional[np.ndarray] = None,
    iterations: int = 40,
    orientation_weight: float = 0.5,
    damping: float = 1e-2,
    singularity_damping: float = 0.15,
    singularity_threshold: float = 0.05,
    max_dq: float = 0.25,
    pos_tol: float = 1e-4,
    ori_tol: float = 1e-3,
    nullspace_gain: float = 0.0,
) -> np.ndarray:
    """Solve damped least-squares IK for a MuJoCo site without mutating `d`.

    Clones `d` (qpos, qvel, act, mocap, eq_active, ctrl) into a scratch `MjData`
    once, uses `mj_jacSite` with adaptive near-singular SVD damping, enforces
    native joint limits, and uses backtracking line search to return reachable
    joint coordinates for `joint_ids`.
    """
    if isinstance(site, str):
        site_id = int(mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SITE, site))
        if site_id < 0:
            raise ValueError(f"Unknown site name: {site!r}")
    else:
        site_id = int(site)
        if not (0 <= site_id < m.nsite):
            raise ValueError(f"Site id out of range: {site_id}")

    n_joints = len(joint_ids)
    if n_joints == 0:
        return np.empty(0, dtype=np.float64)

    resolved_jids = np.empty(n_joints, dtype=np.int64)
    qpos_ids = np.empty(n_joints, dtype=np.int64)
    dof_ids = np.empty(n_joints, dtype=np.int64)
    lo = np.full(n_joints, -np.inf, dtype=np.float64)
    hi = np.full(n_joints, np.inf, dtype=np.float64)

    for idx, j in enumerate(joint_ids):
        if isinstance(j, str):
            jid = int(mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, j))
            if jid < 0:
                raise ValueError(f"Unknown joint name: {j!r}")
        else:
            jid = int(j)
            if not (0 <= jid < m.njnt):
                raise ValueError(f"Joint id out of range: {jid}")
        jtype = m.jnt_type[jid]
        if jtype not in (int(mujoco.mjtJoint.mjJNT_HINGE), int(mujoco.mjtJoint.mjJNT_SLIDE)):
            raise ValueError(f"Joint {jid} must be 1-DOF hinge or slide for scalar angle IK.")
        resolved_jids[idx] = jid
        qpos_ids[idx] = int(m.jnt_qposadr[jid])
        dof_ids[idx] = int(m.jnt_dofadr[jid])
        if m.jnt_limited[jid]:
            lo[idx] = float(m.jnt_range[jid, 0])
            hi[idx] = float(m.jnt_range[jid, 1])

    target_pos = np.asarray(target, dtype=np.float64).reshape(3)
    R_target = _project_so3(orientation) if orientation is not None else None
    w_ori = float(max(0.0, orientation_weight))

    scratch = _clone_data_once(m, d)
    q_init = np.clip(scratch.qpos[qpos_ids].copy(), lo, hi)
    q = q_init.copy()
    scratch.qpos[qpos_ids] = q

    mujoco.mj_kinematics(m, scratch)
    mujoco.mj_comPos(m, scratch)

    jacp = np.zeros((3, m.nv), dtype=np.float64)
    jacr = np.zeros((3, m.nv), dtype=np.float64)

    def _eval_error() -> Tuple[np.ndarray, Optional[np.ndarray], float]:
        pe = target_pos - scratch.site_xpos[site_id]
        cost = 0.5 * float(np.dot(pe, pe))
        if R_target is not None and w_ori > 0.0:
            R_cur = scratch.site_xmat[site_id].reshape(3, 3)
            re_vec = _world_rot_error(R_target, R_cur)
            cost += 0.5 * (w_ori * w_ori) * float(np.dot(re_vec, re_vec))
            return pe, re_vec, cost
        return pe, None, cost

    pos_err, rot_err, best_cost = _eval_error()
    best_q = q.copy()

    max_pos_step_err = 0.20
    max_rot_step_err = 0.60
    n_iters = max(0, int(iterations))

    for _ in range(n_iters):
        pos_norm = float(np.linalg.norm(pos_err))
        ori_norm = 0.0 if rot_err is None else float(np.linalg.norm(rot_err))
        if pos_norm <= pos_tol and ori_norm <= ori_tol:
            break

        mujoco.mj_jacSite(m, scratch, jacp, jacr, site_id)
        Jp = jacp[:, dof_ids]

        pe_clamped = pos_err if pos_norm <= max_pos_step_err else pos_err * (max_pos_step_err / pos_norm)
        if rot_err is not None:
            Jr = jacr[:, dof_ids]
            re_clamped = rot_err if ori_norm <= max_rot_step_err else rot_err * (max_rot_step_err / ori_norm)
            J = np.vstack((Jp, w_ori * Jr))
            e_step = np.concatenate((pe_clamped, w_ori * re_clamped))
        else:
            J = Jp
            e_step = pe_clamped

        # Adaptive conservative SVD damping near kinematic singularities.
        U, s, Vt = np.linalg.svd(J, full_matrices=False)
        s_min = float(s[-1]) if s.size > 0 else 0.0
        if singularity_threshold > 0.0 and s_min < singularity_threshold:
            global_sing = singularity_damping * (1.0 - (s_min / singularity_threshold) ** 2)
        else:
            global_sing = 0.0
        lam_base_sq = damping * damping + global_sing * global_sing
        if singularity_threshold > 0.0:
            ratio = s / singularity_threshold
            lam_sq = lam_base_sq + (singularity_damping * singularity_damping) * np.exp(-(ratio * ratio))
        else:
            lam_sq = np.full_like(s, lam_base_sq)

        d_inv = s / (s * s + lam_sq)
        dq = Vt.T @ (d_inv * (U.T @ e_step))

        if nullspace_gain > 0.0:
            posture_err = q_init - q
            dq_null = posture_err - Vt.T @ ((s * d_inv) * (Vt @ posture_err))
            dq = dq + nullspace_gain * dq_null

        max_step = float(np.max(np.abs(dq)))
        if max_step > max_dq and max_dq > 0.0:
            dq = dq * (max_dq / max_step)

        accepted = False
        for alpha in (1.0, 0.5, 0.25, 0.1):
            q_cand = np.clip(q + alpha * dq, lo, hi)
            if np.allclose(q_cand, q, atol=1e-12, rtol=0.0):
                continue
            scratch.qpos[qpos_ids] = q_cand
            mujoco.mj_kinematics(m, scratch)
            mujoco.mj_comPos(m, scratch)
            c_pe, c_re, c_cost = _eval_error()
            if c_cost < best_cost:
                q = q_cand
                best_q = q_cand.copy()
                best_cost = c_cost
                pos_err, rot_err = c_pe, c_re
                accepted = True
                break

        if not accepted:
            scratch.qpos[qpos_ids] = best_q
            break

    return best_q


# ---------------------------------------------------------------------------
# 2. Time-Interpolated Minimum-Jerk Keyframes with Holds
# ---------------------------------------------------------------------------

# API: keyframe_deriv(t, rows) -> Tuple[np.ndarray, np.ndarray, np.ndarray]
def keyframe_deriv(
    t: Union[float, Sequence[float], np.ndarray],
    rows: Sequence,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Evaluate minimum-jerk position, velocity, and acceleration at time `t`.

    Each segment uses the $C^2$ quintic easing $10s^3 - 15s^4 + 6s^5$ so
    velocities and accelerations vanish smoothly at every knot and hold.
    """
    times, coords = _parse_keyframe_rows(rows)
    n_rows, dim = coords.shape
    scalar_input = np.ndim(t) == 0
    t_arr = np.atleast_1d(np.asarray(t, dtype=np.float64))

    pos = np.empty((t_arr.shape[0], dim), dtype=np.float64)
    vel = np.zeros((t_arr.shape[0], dim), dtype=np.float64)
    acc = np.zeros((t_arr.shape[0], dim), dtype=np.float64)

    if n_rows == 1:
        pos[:] = coords[0]
        return (pos[0], vel[0], acc[0]) if scalar_input else (pos, vel, acc)

    t0 = times[0]
    t_end = times[-1]

    for k, ti in enumerate(t_arr):
        if ti <= t0:
            pos[k] = coords[0]
        elif ti >= t_end:
            pos[k] = coords[-1]
        else:
            idx = int(np.searchsorted(times, ti, side="right")) - 1
            idx = max(0, min(idx, n_rows - 2))
            dt = times[idx + 1] - times[idx]
            if dt <= 0.0:
                pos[k] = coords[idx + 1]
            else:
                s = (ti - times[idx]) / dt
                delta = coords[idx + 1] - coords[idx]
                pos[k] = coords[idx] + _min_jerk(s) * delta
                vel[k] = (_min_jerk_d1(s) / dt) * delta
                acc[k] = (_min_jerk_d2(s) / (dt * dt)) * delta

    if scalar_input:
        return pos[0], vel[0], acc[0]
    return pos, vel, acc


# API: keyframe(t, rows) -> np.ndarray[(D,) or (M, D)]
def keyframe(
    t: Union[float, Sequence[float], np.ndarray],
    rows: Sequence,
) -> np.ndarray:
    """Interpolate time-stamped coordinates with $C^2$ minimum-jerk easing and holds.

    Accepts `rows` as `(t, x0, x1, ...)` tuples, an `(N, 1 + D)` array, or
    `(t, coord_vector)` pairs. Consecutive identical coordinates hold cleanly
    with continuous zero velocity and acceleration at transitions.
    """
    pos, _, _ = keyframe_deriv(t, rows)
    return pos


# ---------------------------------------------------------------------------
# 3. Route Interpolation & Husky Differential-Drive Wheel Helpers
# ---------------------------------------------------------------------------

# API: wrap_angle(angle) -> float
def wrap_angle(angle: float) -> float:
    """Wrap an angle in radians into the principal interval (-pi, pi]."""
    a = (float(angle) + math.pi) % (2.0 * math.pi) - math.pi
    return math.pi if a <= -math.pi else a


# API: route_pose_and_vel(t, rows) -> Tuple[np.ndarray[(3,)], np.ndarray[(3,)]]
def route_pose_and_vel(
    t: float,
    rows: Sequence,
) -> Tuple[np.ndarray, np.ndarray]:
    """Interpolate world `(x, y, yaw)` and `(x_dot, y_dot, yaw_dot)` along a route.

    Unwraps waypoint headings prior to minimum-jerk interpolation so crossings
    across $\\pm\\pi$ follow the shortest continuous angular path.
    """
    times, coords = _parse_keyframe_rows(rows)
    if coords.shape[1] != 3:
        raise ValueError(f"Route rows must provide 3 coordinates (x, y, yaw), got {coords.shape[1]}.")
    unwrapped = coords.copy()
    unwrapped[:, 2] = np.unwrap(unwrapped[:, 2])
    packed = np.column_stack((times, unwrapped))
    pose, vel, _ = keyframe_deriv(float(t), packed)
    pose_out = pose.copy()
    pose_out[2] = wrap_angle(pose_out[2])
    return pose_out, vel


# API: husky_wheel_velocities(current_pose, target_pose, target_vel=(0.0, 0.0, 0.0), wheel_radius=0.1651, track_width=0.555, kx=1.5, ky=2.0, k_yaw=2.5, max_linear=1.0, max_angular=1.5, max_wheel_vel=None) -> np.ndarray[(2,)]
def husky_wheel_velocities(
    current_pose: Sequence[float],
    target_pose: Sequence[float],
    target_vel: Sequence[float] = (0.0, 0.0, 0.0),
    wheel_radius: float = 0.1651,
    track_width: float = 0.555,
    kx: float = 1.5,
    ky: float = 2.0,
    k_yaw: float = 2.5,
    max_linear: float = 1.0,
    max_angular: float = 1.5,
    max_wheel_vel: Optional[float] = None,
) -> np.ndarray:
    """Compute continuous corrective `(omega_left, omega_right)` rad/s for Husky.

    Transforms world pose error into the Husky body frame, combines minimum-jerk
    feedforward with continuous longitudinal, cross-track, and heading feedback,
    and maps `(v, omega)` to left/right differential wheel angular velocities.
    """
    if wheel_radius <= 0.0 or track_width <= 0.0:
        raise ValueError("wheel_radius and track_width must be strictly positive.")

    x, y, yaw = float(current_pose[0]), float(current_pose[1]), float(current_pose[2])
    xd, yd, yawd = float(target_pose[0]), float(target_pose[1]), float(target_pose[2])
    xd_dot, yd_dot, yawd_dot = float(target_vel[0]), float(target_vel[1]), float(target_vel[2])

    c_cur, s_cur = math.cos(yaw), math.sin(yaw)
    dx = xd - x
    dy = yd - y
    e_x = c_cur * dx + s_cur * dy
    e_y = -s_cur * dx + c_cur * dy
    e_yaw = wrap_angle(yawd - yaw)

    v_ff = xd_dot * math.cos(yawd) + yd_dot * math.sin(yawd)
    omega_ff = yawd_dot

    v_cmd = v_ff * math.cos(e_yaw) + kx * e_x
    v_steer = float(np.clip(v_ff + 0.5 * kx * e_x, -max_linear, max_linear))
    omega_cmd = omega_ff + k_yaw * e_yaw + ky * v_steer * e_y

    v_cmd = float(np.clip(v_cmd, -max_linear, max_linear))
    omega_cmd = float(np.clip(omega_cmd, -max_angular, max_angular))

    half_w = 0.5 * track_width
    omega_left = (v_cmd - half_w * omega_cmd) / wheel_radius
    omega_right = (v_cmd + half_w * omega_cmd) / wheel_radius

    if max_wheel_vel is not None and max_wheel_vel > 0.0:
        peak = max(abs(omega_left), abs(omega_right))
        if peak > max_wheel_vel:
            scale = max_wheel_vel / peak
            omega_left *= scale
            omega_right *= scale

    return np.array([omega_left, omega_right], dtype=np.float64)


# API: husky_route_wheels(t, rows, current_pose, wheel_radius=0.1651, track_width=0.555, kx=1.5, ky=2.0, k_yaw=2.5, max_linear=1.0, max_angular=1.5, max_wheel_vel=None) -> np.ndarray[(2,)]
def husky_route_wheels(
    t: float,
    rows: Sequence,
    current_pose: Sequence[float],
    wheel_radius: float = 0.1651,
    track_width: float = 0.555,
    kx: float = 1.5,
    ky: float = 2.0,
    k_yaw: float = 2.5,
    max_linear: float = 1.0,
    max_angular: float = 1.5,
    max_wheel_vel: Optional[float] = None,
) -> np.ndarray:
    """Evaluate a `(t, x, y, yaw)` route and return corrective Husky wheel speeds."""
    target_pose, target_vel = route_pose_and_vel(t, rows)
    return husky_wheel_velocities(
        current_pose=current_pose,
        target_pose=target_pose,
        target_vel=target_vel,
        wheel_radius=wheel_radius,
        track_width=track_width,
        kx=kx,
        ky=ky,
        k_yaw=k_yaw,
        max_linear=max_linear,
        max_angular=max_angular,
        max_wheel_vel=max_wheel_vel,
    )


# ---------------------------------------------------------------------------
# 4. Spot Sagittal-Plane Leg IK & Alternating-Diagonal Walking Gait
# ---------------------------------------------------------------------------

# API: spot_sagittal_ik(x, z, femur_length, tibia_length, knee_sign=-1.0) -> Tuple[float, float]
def spot_sagittal_ik(
    x: float,
    z: float,
    femur_length: float,
    tibia_length: float,
    knee_sign: float = -1.0,
) -> Tuple[float, float]:
    """Solve exact 2-link sagittal-plane leg IK `(hy, kn)` for Spot.

    Uses actual measured `femur_length` ($L_1$) and `tibia_length` ($L_2$) with
    forward $+x$, upward $+z$ ($z < 0$ below hip), and Spot's right-handed $+y$
    pitch convention where `knee_sign=-1.0` yields backward-pointing knees.
    """
    if femur_length <= 0.0 or tibia_length <= 0.0:
        raise ValueError("femur_length and tibia_length must be strictly positive.")

    L1 = float(femur_length)
    L2 = float(tibia_length)
    fx = float(x)
    d = float(-z)  # positive downward distance

    r = math.hypot(fx, d)
    eps = 1e-4
    r_min = abs(L1 - L2) + eps
    r_max = (L1 + L2) - eps
    if r < 1e-9:
        fx, d, r = 0.0, r_min, r_min
    elif r < r_min:
        scale = r_min / r
        fx *= scale
        d *= scale
        r = r_min
    elif r > r_max:
        scale = r_max / r
        fx *= scale
        d *= scale
        r = r_max

    cos_kn = (r * r - L1 * L1 - L2 * L2) / (2.0 * L1 * L2)
    cos_kn = -1.0 if cos_kn < -1.0 else (1.0 if cos_kn > 1.0 else cos_kn)
    sign = -1.0 if knee_sign < 0.0 else 1.0
    kn = sign * math.acos(cos_kn)

    a = L1 + L2 * math.cos(kn)
    b = L2 * math.sin(kn)
    hy = math.atan2(-b * d - a * fx, a * d - b * fx)
    return hy, kn


# API: spot_leg_ik(x, y, z, femur_length, tibia_length, hip_offset_y=0.0, knee_sign=-1.0) -> np.ndarray[(3,)]
def spot_leg_ik(
    x: float,
    y: float,
    z: float,
    femur_length: float,
    tibia_length: float,
    hip_offset_y: float = 0.0,
    knee_sign: float = -1.0,
) -> np.ndarray:
    """Solve 3-DOF Spot leg IK `[hx, hy, kn]` from hip-frame foot position `(x, y, z)`.

    Resolves hip abduction `hx` around $+x$ accounting for lateral `hip_offset_y`,
    then solves `(hy, kn)` in the rotated sagittal plane via `spot_sagittal_ik`.
    """
    fy = float(y)
    fz = float(z)
    l_hip = float(hip_offset_y)
    yz_sq = fy * fy + fz * fz
    z_plane = math.sqrt(max(yz_sq - l_hip * l_hip, 1e-8))
    hx = math.atan2(z_plane * fy + l_hip * fz, l_hip * fy - z_plane * fz)
    hy, kn = spot_sagittal_ik(x, -z_plane, femur_length, tibia_length, knee_sign=knee_sign)
    return np.array([hx, hy, kn], dtype=np.float64)


# API: spot_gait(t, cmd_vel, femur_length, tibia_length, nominal_foot_offsets, stride=0.18, step_height=0.06, cycle_period=0.6, duty_factor=0.55, hip_offsets_y=None, hip_positions_xy=None, knee_sign=-1.0, phase_offsets=None, speed_deadband=1e-3, speed_ramp=0.05, joint_limits=None) -> Dict[str, np.ndarray[(3,)]]
def spot_gait(
    t: float,
    cmd_vel: Sequence[float],
    femur_length: float,
    tibia_length: float,
    nominal_foot_offsets: Union[Mapping[str, Sequence[float]], Sequence[float]],
    stride: float = 0.18,
    step_height: float = 0.06,
    cycle_period: float = 0.6,
    duty_factor: float = 0.55,
    hip_offsets_y: Optional[Mapping[str, float]] = None,
    hip_positions_xy: Optional[Mapping[str, Sequence[float]]] = None,
    knee_sign: float = -1.0,
    phase_offsets: Optional[Mapping[str, float]] = None,
    speed_deadband: float = 1e-3,
    speed_ramp: float = 0.05,
    joint_limits: Optional[Mapping[str, Tuple[Sequence[float], Sequence[float]]]] = None,
) -> Dict[str, np.ndarray]:
    """Compute continuous Spot trot joint angles `[hx, hy, kn]` for all four legs.

    Alternates diagonal leg pairs (`fl`/`hr` vs `fr`/`hl`) with $C^2$ stance/swing
    trajectories, caps horizontal excursions to the measured `stride`, smoothly
    ramps step clearance to zero when stationary (no zero-motion marching, no
    teleport), and solves exact sagittal-plane leg IK with measured limb lengths.
    """
    if stride <= 0.0:
        raise ValueError("stride must be strictly positive.")
    if cycle_period <= 0.0:
        raise ValueError("cycle_period must be strictly positive.")
    if not (0.0 < duty_factor < 1.0):
        raise ValueError("duty_factor must lie strictly inside (0, 1).")

    vx, vy, yaw_rate = float(cmd_vel[0]), float(cmd_vel[1]), float(cmd_vel[2])
    phases = _SPOT_DEFAULT_PHASES if phase_offsets is None else phase_offsets
    hips_xy = _SPOT_DEFAULT_HIP_XY if hip_positions_xy is None else hip_positions_xy
    t_stance = duty_factor * cycle_period

    if isinstance(nominal_foot_offsets, Mapping):
        nom_map = {
            leg: np.asarray(nominal_foot_offsets[leg], dtype=np.float64).reshape(3)
            for leg in _SPOT_LEGS
        }
    else:
        base = np.asarray(nominal_foot_offsets, dtype=np.float64).reshape(3)
        nom_map = {
            leg: np.array(
                [base[0], abs(base[1]) if leg in ("fl", "hl") else -abs(base[1]), base[2]],
                dtype=np.float64,
            )
            for leg in _SPOT_LEGS
        }

    # Per-leg velocity in body frame including yaw lever arm.
    leg_strides: Dict[str, np.ndarray] = {}
    max_leg_speed = 0.0
    max_stride_norm = 0.0
    for leg in _SPOT_LEGS:
        hx_pos, hy_pos = float(hips_xy[leg][0]), float(hips_xy[leg][1])
        v_lx = vx - yaw_rate * hy_pos
        v_ly = vy + yaw_rate * hx_pos
        spd = math.hypot(v_lx, v_ly)
        if spd > max_leg_speed:
            max_leg_speed = spd
        s_vec = np.array([v_lx * t_stance, v_ly * t_stance], dtype=np.float64)
        s_norm = float(np.linalg.norm(s_vec))
        if s_norm > max_stride_norm:
            max_stride_norm = s_norm
        leg_strides[leg] = s_vec

    # Uniformly cap stride vectors across legs to preserve turning curvature.
    if max_stride_norm > stride:
        scale = stride / max_stride_norm
        for leg in _SPOT_LEGS:
            leg_strides[leg] *= scale

    # Smooth anti-marching ramp: zero motion -> zero lift and planted nominal stance.
    if max_leg_speed <= speed_deadband:
        activity = 0.0
        for leg in _SPOT_LEGS:
            leg_strides[leg][:] = 0.0
    elif speed_ramp <= speed_deadband or max_leg_speed >= speed_ramp:
        activity = 1.0
    else:
        activity = _min_jerk((max_leg_speed - speed_deadband) / (speed_ramp - speed_deadband))

    h_eff = max(0.0, float(step_height)) * activity
    base_phase = float(t) / cycle_period
    result: Dict[str, np.ndarray] = {}

    for leg in _SPOT_LEGS:
        phi = (base_phase + float(phases[leg])) % 1.0
        s_vec = leg_strides[leg]
        if phi < duty_factor:
            u = phi / duty_factor
            dx = (0.5 - u) * s_vec[0]
            dy = (0.5 - u) * s_vec[1]
            dz = 0.0
        else:
            w = (phi - duty_factor) / (1.0 - duty_factor)
            eased = _min_jerk(w)
            dx = (-0.5 + eased) * s_vec[0]
            dy = (-0.5 + eased) * s_vec[1]
            # C2 smooth symmetric bell: 0 at liftoff/touchdown, 1 at mid-swing.
            u_w = 1.0 - w
            dz = h_eff * 64.0 * (w * w * w) * (u_w * u_w * u_w)

        foot = nom_map[leg]
        hip_y = 0.0 if hip_offsets_y is None else float(hip_offsets_y.get(leg, 0.0))
        q_leg = spot_leg_ik(
            x=float(foot[0] + dx),
            y=float(foot[1] + dy),
            z=float(foot[2] + dz),
            femur_length=femur_length,
            tibia_length=tibia_length,
            hip_offset_y=hip_y,
            knee_sign=knee_sign,
        )
        if joint_limits is not None and leg in joint_limits:
            j_lo, j_hi = joint_limits[leg]
            q_leg = np.clip(q_leg, np.asarray(j_lo, dtype=np.float64), np.asarray(j_hi, dtype=np.float64))
        result[leg] = q_leg

    return result


# API: spot_route_gait(t, rows, current_pose, femur_length, tibia_length, nominal_foot_offsets, stride=0.18, step_height=0.06, cycle_period=0.6, duty_factor=0.55, kx=1.2, ky=1.2, k_yaw=1.8, max_vx=0.6, max_vy=0.3, max_yaw_rate=0.8, hip_offsets_y=None, hip_positions_xy=None, knee_sign=-1.0, phase_offsets=None, speed_deadband=1e-3, speed_ramp=0.05, joint_limits=None) -> Dict[str, np.ndarray[(3,)]]
def spot_route_gait(
    t: float,
    rows: Sequence,
    current_pose: Sequence[float],
    femur_length: float,
    tibia_length: float,
    nominal_foot_offsets: Union[Mapping[str, Sequence[float]], Sequence[float]],
    stride: float = 0.18,
    step_height: float = 0.06,
    cycle_period: float = 0.6,
    duty_factor: float = 0.55,
    kx: float = 1.2,
    ky: float = 1.2,
    k_yaw: float = 1.8,
    max_vx: float = 0.6,
    max_vy: float = 0.3,
    max_yaw_rate: float = 0.8,
    hip_offsets_y: Optional[Mapping[str, float]] = None,
    hip_positions_xy: Optional[Mapping[str, Sequence[float]]] = None,
    knee_sign: float = -1.0,
    phase_offsets: Optional[Mapping[str, float]] = None,
    speed_deadband: float = 1e-3,
    speed_ramp: float = 0.05,
    joint_limits: Optional[Mapping[str, Tuple[Sequence[float], Sequence[float]]]] = None,
) -> Dict[str, np.ndarray]:
    """Track a `(t, x, y, yaw)` route with Spot's holonomic trot gait.

    Computes continuous feedforward plus body-frame corrective `(vx, vy, yaw_rate)`
    from the interpolated route and feeds `spot_gait` with anti-marching holds.
    """
    target_pose, target_vel = route_pose_and_vel(t, rows)
    x, y, yaw = float(current_pose[0]), float(current_pose[1]), float(current_pose[2])
    c_cur, s_cur = math.cos(yaw), math.sin(yaw)

    dx = float(target_pose[0]) - x
    dy = float(target_pose[1]) - y
    e_x = c_cur * dx + s_cur * dy
    e_y = -s_cur * dx + c_cur * dy
    e_yaw = wrap_angle(float(target_pose[2]) - yaw)

    vx_ff = c_cur * float(target_vel[0]) + s_cur * float(target_vel[1])
    vy_ff = -s_cur * float(target_vel[0]) + c_cur * float(target_vel[1])
    wz_ff = float(target_vel[2])

    vx = float(np.clip(vx_ff + kx * e_x, -max_vx, max_vx))
    vy = float(np.clip(vy_ff + ky * e_y, -max_vy, max_vy))
    wz = float(np.clip(wz_ff + k_yaw * e_yaw, -max_yaw_rate, max_yaw_rate))

    return spot_gait(
        t=t,
        cmd_vel=(vx, vy, wz),
        femur_length=femur_length,
        tibia_length=tibia_length,
        nominal_foot_offsets=nominal_foot_offsets,
        stride=stride,
        step_height=step_height,
        cycle_period=cycle_period,
        duty_factor=duty_factor,
        hip_offsets_y=hip_offsets_y,
        hip_positions_xy=hip_positions_xy,
        knee_sign=knee_sign,
        phase_offsets=phase_offsets,
        speed_deadband=speed_deadband,
        speed_ramp=speed_ramp,
        joint_limits=joint_limits,
    )


# ---------------------------------------------------------------------------
# 5. GR-1 Five-Finger Curl Goal Interpolation (Left/Right Safe)
# ---------------------------------------------------------------------------

# API: GR1_CHANNELS -> Tuple[str, ...]
GR1_CHANNELS: Tuple[str, ...] = (
    "thumb_spread",
    "thumb_flex",
    "index",
    "middle",
    "ring",
    "pinky",
)

# API: GR1_RELEASE -> Dict[str, float] (fully open hand with thumb un-opposed clear)
GR1_RELEASE: Dict[str, float] = {
    "thumb_spread": 0.05,
    "thumb_flex": 0.0,
    "index": 0.0,
    "middle": 0.0,
    "ring": 0.0,
    "pinky": 0.0,
}

# API: GR1_PREGRASP -> Dict[str, float] (thumb pre-opposed, fingers lightly cupped open)
GR1_PREGRASP: Dict[str, float] = {
    "thumb_spread": 0.75,
    "thumb_flex": 0.12,
    "index": 0.15,
    "middle": 0.15,
    "ring": 0.18,
    "pinky": 0.20,
}

# API: GR1_POWER_GRASP -> Dict[str, float] (five-finger enveloping grasp)
GR1_POWER_GRASP: Dict[str, float] = {
    "thumb_spread": 0.85,
    "thumb_flex": 0.72,
    "index": 0.85,
    "middle": 0.88,
    "ring": 0.90,
    "pinky": 0.90,
}

# API: GR1_PINCH_GRASP -> Dict[str, float] (thumb-index precision pinch)
GR1_PINCH_GRASP: Dict[str, float] = {
    "thumb_spread": 0.82,
    "thumb_flex": 0.65,
    "index": 0.78,
    "middle": 0.20,
    "ring": 0.15,
    "pinky": 0.15,
}

# API: GR1_PRESETS -> Dict[str, Dict[str, float]]
GR1_PRESETS: Dict[str, Dict[str, float]] = {
    "release": GR1_RELEASE,
    "pregrasp": GR1_PREGRASP,
    "power_grasp": GR1_POWER_GRASP,
    "pinch_grasp": GR1_PINCH_GRASP,
}


def _normalize_hand_side(side: str) -> str:
    s = side.strip().lower()
    if s in ("left", "l"):
        return "left"
    if s in ("right", "r"):
        return "right"
    raise ValueError(f"Expected side 'left' or 'right', got {side!r}.")


def _resolve_curl_dict(curl: Union[str, Mapping[str, float]]) -> Dict[str, float]:
    if isinstance(curl, str):
        key = curl.strip().lower()
        if key not in GR1_PRESETS:
            raise ValueError(f"Unknown GR-1 preset {curl!r}; expected one of {tuple(GR1_PRESETS)}.")
        return dict(GR1_PRESETS[key])
    out: Dict[str, float] = {}
    for ch in GR1_CHANNELS:
        val = float(curl.get(ch, 0.0))
        out[ch] = 0.0 if val < 0.0 else (1.0 if val > 1.0 else val)
    return out


# API: gr1_find_hand_joints(m, side, actuated_only=False) -> Dict[str, list[Tuple[str, int, float, float]]]
def gr1_find_hand_joints(
    m: mujoco.MjModel,
    side: str,
    actuated_only: bool = False,
) -> Dict[str, list]:
    """Discover GR-1 hand joints for one side only, with native `(open, closed)` limits.

    Tokenizes joint names strictly so `'left'`/`'l'` and `'right'`/`'r'` never
    cross-match or alias substrings such as `'ring'`, `'proximal'`, or `'distal'`.
    Returns `{channel: [(joint_name, joint_id, open_limit, closed_limit), ...]}`.
    """
    norm_side = _normalize_hand_side(side)
    actuated_jids = set()
    if actuated_only:
        for aid in range(m.nu):
            if m.actuator_trntype[aid] in (
                mujoco.mjtTrn.mjTRN_JOINT,
                mujoco.mjtTrn.mjTRN_JOINTINPARENT,
            ):
                actuated_jids.add(int(m.actuator_trnid[aid, 0]))

    grouped: Dict[str, list] = {ch: [] for ch in GR1_CHANNELS}

    for jid in range(m.njnt):
        if m.jnt_type[jid] not in (int(mujoco.mjtJoint.mjJNT_HINGE), int(mujoco.mjtJoint.mjJNT_SLIDE)):
            continue
        if actuated_only and jid not in actuated_jids:
            continue
        name = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, jid)
        if not name:
            continue

        tokens = _tokenize_joint_name(name)
        tok_set = set(tokens)
        has_left = "left" in tok_set or "l" in tok_set
        has_right = "right" in tok_set or "r" in tok_set
        if norm_side == "left" and (not has_left or has_right):
            continue
        if norm_side == "right" and (not has_right or has_left):
            continue

        if "thumb" in tok_set:
            channel = "thumb_spread" if (tok_set & _THUMB_SPREAD_TOKENS) else "thumb_flex"
        elif "index" in tok_set:
            channel = "index"
        elif "middle" in tok_set:
            channel = "middle"
        elif "ring" in tok_set:
            channel = "ring"
        elif "pinky" in tok_set or "little" in tok_set:
            channel = "pinky"
        else:
            continue

        if m.jnt_limited[jid]:
            lo = float(m.jnt_range[jid, 0])
            hi = float(m.jnt_range[jid, 1])
            # Open endpoint is the native limit nearer zero; closed is the flexed limit.
            if abs(lo) <= abs(hi):
                open_lim, closed_lim = lo, hi
            else:
                open_lim, closed_lim = hi, lo
        else:
            open_lim, closed_lim = 0.0, 1.0

        grouped[channel].append((name, jid, open_lim, closed_lim))

    return grouped


# API: gr1_finger_targets(m, side, curl, actuated_only=False, invert_joints=None) -> Dict[str, float]
def gr1_finger_targets(
    m: mujoco.MjModel,
    side: str,
    curl: Union[str, Mapping[str, float]],
    actuated_only: bool = False,
    invert_joints: Optional[Sequence[str]] = None,
) -> Dict[str, float]:
    """Map normalized 5-finger curl goals (`[0, 1]`) to native MuJoCo joint angles.

    Strictly isolates `side` (`'left'` or `'right'`) and clamps every returned
    joint angle inside its native `m.jnt_range`.
    """
    curl_map = _resolve_curl_dict(curl)
    grouped = gr1_find_hand_joints(m, side=side, actuated_only=actuated_only)
    invert_set = set(invert_joints) if invert_joints is not None else set()
    targets: Dict[str, float] = {}

    for channel, entries in grouped.items():
        u = curl_map[channel]
        for jname, jid, open_lim, closed_lim in entries:
            o_val, c_val = (closed_lim, open_lim) if jname in invert_set else (open_lim, closed_lim)
            angle = o_val + u * (c_val - o_val)
            if m.jnt_limited[jid]:
                lo = float(m.jnt_range[jid, 0])
                hi = float(m.jnt_range[jid, 1])
                angle = float(np.clip(angle, lo, hi))
            targets[jname] = float(angle)

    return targets


# API: gr1_interpolate_hand(m, side, start_curl, goal_curl, alpha, stagger_thumb=True, actuated_only=False, invert_joints=None) -> Dict[str, float]
def gr1_interpolate_hand(
    m: mujoco.MjModel,
    side: str,
    start_curl: Union[str, Mapping[str, float]],
    goal_curl: Union[str, Mapping[str, float]],
    alpha: float,
    stagger_thumb: bool = True,
    actuated_only: bool = False,
    invert_joints: Optional[Sequence[str]] = None,
) -> Dict[str, float]:
    """Interpolate GR-1 five-finger goals in native joint limits with minimum-jerk easing.

    Preserves physically sensible pregrasp vs release coordination when
    `stagger_thumb=True`: during grasp closure, `thumb_spread` opposes early and
    `thumb_flex` trails slightly to avoid finger-thumb collision; during release,
    fingers uncurl early so grasped objects clear cleanly before thumb retraction.
    """
    start_map = _resolve_curl_dict(start_curl)
    goal_map = _resolve_curl_dict(goal_curl)
    a = 0.0 if alpha <= 0.0 else (1.0 if alpha >= 1.0 else float(alpha))

    base_s = _min_jerk(a)
    finger_delta = 0.25 * sum(goal_map[f] - start_map[f] for f in ("index", "middle", "ring", "pinky"))

    blended: Dict[str, float] = {}
    for ch in GR1_CHANNELS:
        if stagger_thumb and finger_delta > 0.05:
            if ch == "thumb_spread":
                s_ch = _min_jerk(min(1.0, a / 0.65))
            elif ch == "thumb_flex":
                s_ch = _min_jerk(max(0.0, (a - 0.15) / 0.85))
            else:
                s_ch = base_s
        elif stagger_thumb and finger_delta < -0.05:
            if ch == "thumb_spread":
                s_ch = base_s
            else:
                s_ch = _min_jerk(min(1.0, a / 0.75))
        else:
            s_ch = base_s

        val = start_map[ch] + s_ch * (goal_map[ch] - start_map[ch])
        blended[ch] = 0.0 if val < 0.0 else (1.0 if val > 1.0 else val)

    return gr1_finger_targets(
        m=m,
        side=side,
        curl=blended,
        actuated_only=actuated_only,
        invert_joints=invert_joints,
    )
