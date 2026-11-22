"""Workcell trajectory, bimanual, mobile-base, and lighting hooks for cells k=1..10.

All hooks preserve operator motion, human separation criteria, and task-active
controller logic, adding only bounded, smooth, deterministic free-space motions,
post-goal closed-loop wheel braking, and static per-room lighting profiles.
"""

import numpy as np

__all__ = [
    "trajectory_knots",
    "bimanual",
    "spot_offset",
    "dock_speed_shape",
    "park_ctrl",
    "detail_steps",
    "light_profile",
]

_MJ_VEL_FACTOR = 1.875
_MJ_ACC_FACTOR = 10.0 / float(np.sqrt(3.0))

_PANDA_HOLD_PROFILES = {
    # (dxyz_m, dyaw_rad) chosen with unique per-task free-space directions.
    5: (np.array([-0.012, -0.008, 0.022], dtype=float), -0.18),
    6: (np.array([0.010, -0.014, 0.016], dtype=float), 0.16),
    8: (np.array([-0.008, 0.016, 0.014], dtype=float), 0.20),
}

_BIMANUAL_HOLD_OFFSETS = {
    # Coordinated asymmetric high unloaded offsets, strictly <= 12 mm Euclidean norm.
    9: {
        "left": np.array([-0.004, 0.005, 0.009], dtype=float),
        "right": np.array([0.003, -0.004, 0.007], dtype=float),
    },
    10: {
        "left": np.array([0.003, 0.004, 0.008], dtype=float),
        "right": np.array([-0.003, -0.004, 0.009], dtype=float),
    },
}

_DETAIL_STEPS = {
    1: [
        "Retain the validated crossing motion and human separation criteria without modifying in-motion targeting.",
        "Engage gentle closed-loop driveline park verification wheel braking only after passing the recorded goal time in the clear bay.",
    ],
    2: [
        "Apply a C2-smooth asymmetric docking speed profile with zero endpoint velocities and an extended low-deceleration final approach.",
        "Preserve normalized docking endpoints without altering human clearance intervals.",
    ],
    3: [
        "Preserve the full pump gauge sweep traverse and wrist orientation.",
        "Add a smooth 1.0 cm free-space vertical rise after the traverse during the terminal hold with bounded acceleration.",
    ],
    4: [
        "Preserve the primary irrigation controller actuation and return path with fixed orientation.",
        "Apply a gentle free-space post-return park offset after 4.77 s during the final hold.",
    ],
    5: [
        "Retain the validated pick, carry, nest, and return phases without modifying operator-present intervals.",
        "Execute a smooth vertical and away-facing secondary inspection motion during the final home parking hold and return to the exact home pose.",
    ],
    6: [
        "Retain the PACE-scaled ball pickup, release, and retract trajectory.",
        "Perform a smooth parked-pose secondary inspection motion in a distinct direction during the terminal park interval and return to the exact parked pose.",
    ],
    7: [
        "Preserve trajectory endpoints and all segments outside the clear entry window.",
        "Add a gentle 1.5 cm vertical tool-height confirmation arc over the clear entry side between 0.35 s and 1.95 s while yaw is acquired.",
    ],
    8: [
        "Retain the task trajectory and operator separation intervals unchanged.",
        "Execute a small, smooth empty-wrist witness motion during the terminal high-clearance hold and return to the recorded end pose.",
    ],
    9: [
        "Retain the synchronized dual-arm push transport and carriage retract profile.",
        "Execute a coordinated asymmetric high unloaded park confirmation pose within 12 mm during the final hold and return both arms to their recorded park poses.",
    ],
    10: [
        "Retain the fixture hold-down, witness-flag clearance lift, optical reading, and fixture release sequence.",
        "Execute a coordinated asymmetric high unloaded park confirmation pose within 12 mm during the shared post-release park hold and return both arms to their recorded park poses.",
    ],
}

_LIGHT_PROFILES = {
    1: {
        "sun_angle_deg": 38.0,
        "sun_multiplier": 1.10,
        "sky_multiplier": 0.90,
        "exposure": 0.05,
        "kelvin": 5200.0,
    },
    2: {
        "sun_angle_deg": 44.0,
        "sun_multiplier": 1.05,
        "sky_multiplier": 0.85,
        "exposure": 0.00,
        "kelvin": 5500.0,
    },
    3: {
        "sun_angle_deg": 32.0,
        "sun_multiplier": 0.95,
        "sky_multiplier": 0.80,
        "exposure": 0.10,
        "kelvin": 4600.0,
    },
    4: {
        "sun_angle_deg": 52.0,
        "sun_multiplier": 1.25,
        "sky_multiplier": 1.05,
        "exposure": -0.10,
        "kelvin": 5800.0,
    },
    5: {
        "sun_angle_deg": 46.0,
        "sun_multiplier": 1.00,
        "sky_multiplier": 0.95,
        "exposure": 0.05,
        "kelvin": 4900.0,
    },
    6: {
        "sun_angle_deg": 41.0,
        "sun_multiplier": 0.90,
        "sky_multiplier": 1.00,
        "exposure": 0.08,
        "kelvin": 5100.0,
    },
    7: {
        "sun_angle_deg": 36.0,
        "sun_multiplier": 1.15,
        "sky_multiplier": 0.85,
        "exposure": 0.00,
        "kelvin": 5300.0,
    },
    8: {
        "sun_angle_deg": 48.0,
        "sun_multiplier": 1.00,
        "sky_multiplier": 0.92,
        "exposure": 0.02,
        "kelvin": 5600.0,
    },
    9: {
        "sun_angle_deg": 43.0,
        "sun_multiplier": 1.08,
        "sky_multiplier": 0.96,
        "exposure": -0.02,
        "kelvin": 5000.0,
    },
    10: {
        "sun_angle_deg": 34.0,
        "sun_multiplier": 0.85,
        "sky_multiplier": 0.90,
        "exposure": 0.12,
        "kelvin": 4800.0,
    },
}

_DEFAULT_LIGHT_PROFILE = {
    "sun_angle_deg": 42.0,
    "sun_multiplier": 1.00,
    "sky_multiplier": 0.92,
    "exposure": 0.00,
    "kelvin": 5200.0,
}


def _smoothstep5(u):
    s = float(np.clip(u, 0.0, 1.0))
    return s * s * s * (10.0 + s * (-15.0 + 6.0 * s))


def _format_xyz(vec, prototype):
    arr = np.asarray(vec, dtype=float)
    if isinstance(prototype, np.ndarray):
        return arr.copy()
    if isinstance(prototype, tuple):
        return tuple(float(v) for v in arr)
    return [float(v) for v in arr]


def _copy_ctrl(val):
    if isinstance(val, np.ndarray):
        return val.copy()
    if isinstance(val, list):
        return list(val)
    if isinstance(val, tuple):
        return tuple(val)
    return val


def _interp_knot_pose(t_query, parsed):
    if t_query <= parsed[0][0]:
        return parsed[0][1].copy(), parsed[0][2]
    if t_query >= parsed[-1][0]:
        return parsed[-1][1].copy(), parsed[-1][2]
    for i in range(len(parsed) - 1):
        t0, p0, y0, _ = parsed[i]
        t1, p1, y1, _ = parsed[i + 1]
        if t0 <= t_query <= t1:
            dt = t1 - t0
            if dt <= 1e-12:
                return p0.copy(), y0
            w = _smoothstep5((t_query - t0) / dt)
            return p0 + w * (p1 - p0), y0 + w * (y1 - y0)
    return parsed[-1][1].copy(), parsed[-1][2]


def trajectory_knots(k, knots):
    """Modify Panda trajectory knots for k in {5, 6, 7, 8} while preserving endpoints.

    Parameters
    ----------
    k : int
        Workcell identifier.
    knots : sequence of tuple(float, array_like, float)
        Input knots ``(t, xyz, yaw)`` in seconds, meters, and radians.

    Returns
    -------
    list
        Modified knot list with identical start and end knots.
    """
    cell = int(k)
    knot_list = list(knots)
    if len(knot_list) < 2 or cell not in (5, 6, 7, 8):
        return knot_list

    parsed = []
    for raw in knot_list:
        t_val = float(raw[0])
        p_val = np.asarray(raw[1], dtype=float)
        yaw_val = float(raw[2])
        if p_val.shape != (3,) or not np.isfinite(t_val) or not np.isfinite(yaw_val):
            return knot_list
        if not np.all(np.isfinite(p_val)):
            return knot_list
        parsed.append((t_val, p_val, yaw_val, raw))

    for i in range(len(parsed) - 1):
        if parsed[i + 1][0] < parsed[i][0] - 1e-12:
            return knot_list

    if cell in _PANDA_HOLD_PROFILES:
        t0, p0, yaw0, _ = parsed[-2]
        t1, p1, yaw1, raw_end = parsed[-1]
        dt = t1 - t0
        if dt < 0.35:
            return knot_list
        if float(np.linalg.norm(p1 - p0)) > 1e-3 or abs(yaw1 - yaw0) > 1e-3:
            return knot_list

        dxyz_nom, dyaw_nom = _PANDA_HOLD_PROFILES[cell]
        margin = min(0.12, 0.12 * dt)
        t_start = t0 + margin
        t_end = t1 - margin
        span = t_end - t_start
        ramp = 0.42 * span
        t_peak_a = t_start + ramp
        t_peak_b = t_end - ramp
        if not (t0 < t_start < t_peak_a < t_peak_b < t_end < t1):
            return knot_list

        # Bound peak minimum-jerk speed and acceleration for safe IK tracking.
        v_max = 0.14
        a_max = 1.40
        w_max = 0.95
        alpha_max = 8.50
        scale = 1.0
        lin_norm = float(np.linalg.norm(dxyz_nom))
        if lin_norm > 0.0:
            scale = min(
                scale,
                v_max * ramp / (_MJ_VEL_FACTOR * lin_norm),
                a_max * (ramp ** 2) / (_MJ_ACC_FACTOR * lin_norm),
            )
        if abs(dyaw_nom) > 0.0:
            scale = min(
                scale,
                w_max * ramp / (_MJ_VEL_FACTOR * abs(dyaw_nom)),
                alpha_max * (ramp ** 2) / (_MJ_ACC_FACTOR * abs(dyaw_nom)),
            )

        dxyz = scale * dxyz_nom
        dyaw = scale * dyaw_nom
        if float(np.linalg.norm(dxyz)) < 0.003 and abs(dyaw) < 0.03:
            return knot_list

        proto = raw_end[1]
        p_hold = _format_xyz(p0, proto)
        p_peak = _format_xyz(p0 + dxyz, proto)
        yaw_hold = float(yaw0)
        yaw_peak = float(yaw0 + dyaw)

        out = list(knot_list[:-1])
        out.append((float(t_start), p_hold, yaw_hold))
        out.append((float(t_peak_a), p_peak, yaw_peak))
        out.append((float(t_peak_b), p_peak, yaw_peak))
        out.append((float(t_end), p_hold, yaw_hold))
        out.append(raw_end)
        return out

    # k == 7: gentle 1.5 cm tool-height confirmation arc over [0.35, 1.95].
    w0 = 0.35
    w1 = 1.95
    dz_max = 0.015
    t_first = parsed[0][0]
    t_last = parsed[-1][0]
    if t_first > w0 + 1e-6 or t_last < w1 - 1e-6:
        return knot_list

    def _arc_dz(t_val):
        if t_val <= w0 or t_val >= w1:
            return 0.0
        u = (t_val - w0) / (w1 - w0)
        return dz_max * float(np.sin(np.pi * u) ** 2)

    entries = []
    for idx, (t_val, p_val, yaw_val, raw) in enumerate(parsed):
        is_endpoint = idx == 0 or idx == len(parsed) - 1
        if (not is_endpoint) and (w0 < t_val < w1):
            p_mod = p_val.copy()
            p_mod[2] += _arc_dz(t_val)
            entries.append((t_val, (float(t_val), _format_xyz(p_mod, raw[1]), float(yaw_val))))
        else:
            entries.append((t_val, raw))

    existing_ts = [item[0] for item in parsed]
    proto = knot_list[0][1]
    for t_cand, min_gap in ((w0, 0.04), (0.5 * (w0 + w1), 0.18), (w1, 0.04)):
        if t_cand <= t_first + 1e-9 or t_cand >= t_last - 1e-9:
            continue
        if any(abs(t_cand - te) < min_gap for te in existing_ts):
            continue
        p_interp, yaw_interp = _interp_knot_pose(t_cand, parsed)
        p_interp[2] += _arc_dz(t_cand)
        entries.append((t_cand, (float(t_cand), _format_xyz(p_interp, proto), float(yaw_interp))))
        existing_ts.append(t_cand)

    entries.sort(key=lambda item: item[0])
    return [item[1] for item in entries]


def bimanual(k, tracks):
    """Add a coordinated asymmetric high unloaded park confirmation pose for k=9, 10.

    Parameters
    ----------
    k : int
        Workcell identifier (9 or 10).
    tracks : dict[str, list[tuple[float, array_like]]]
        Mapping from side name (``'left'``, ``'right'``) to ``[(t, xyz), ...]``.

    Returns
    -------
    dict
        New tracks dictionary with both arms returning to their recorded park pose.
    """
    cell = int(k)
    out = {side: list(seq) for side, seq in tracks.items()}
    if cell not in _BIMANUAL_HOLD_OFFSETS:
        return out
    if "left" not in out or "right" not in out:
        return out

    left = out["left"]
    right = out["right"]
    if len(left) < 2 or len(right) < 2:
        return out

    t0_l, p0_l = float(left[-2][0]), np.asarray(left[-2][1], dtype=float)
    t1_l, p1_l = float(left[-1][0]), np.asarray(left[-1][1], dtype=float)
    t0_r, p0_r = float(right[-2][0]), np.asarray(right[-2][1], dtype=float)
    t1_r, p1_r = float(right[-1][0]), np.asarray(right[-1][1], dtype=float)

    for arr in (p0_l, p1_l, p0_r, p1_r):
        if arr.shape != (3,) or not np.all(np.isfinite(arr)):
            return out
    if float(np.linalg.norm(p1_l - p0_l)) > 1e-3 or float(np.linalg.norm(p1_r - p0_r)) > 1e-3:
        return out

    t_hold_start = max(t0_l, t0_r)
    t_hold_end = min(t1_l, t1_r)
    dt = t_hold_end - t_hold_start
    if dt < 0.20:
        return out

    margin = min(0.04, 0.10 * dt)
    t_start = t_hold_start + margin
    t_end = t_hold_end - margin
    span = t_end - t_start
    ramp = 0.44 * span
    t_peak_a = t_start + ramp
    t_peak_b = t_end - ramp
    if not (t_hold_start < t_start < t_peak_a < t_peak_b < t_end < t_hold_end):
        return out

    max_offset = 0.0119  # Strictly within 12 mm cap.
    offsets = _BIMANUAL_HOLD_OFFSETS[cell]
    for side, park_vec in (("left", p1_l), ("right", p1_r)):
        seq = out[side]
        proto = seq[-1][1]
        off = offsets[side].copy()
        norm = float(np.linalg.norm(off))
        if norm > max_offset:
            off *= max_offset / norm

        p_park = _format_xyz(park_vec, proto)
        p_conf = _format_xyz(park_vec + off, proto)
        updated = list(seq[:-1])
        updated.append((float(t_start), p_park))
        updated.append((float(t_peak_a), p_conf))
        updated.append((float(t_peak_b), p_conf))
        updated.append((float(t_end), p_park))
        updated.append(seq[-1])
        out[side] = updated

    return out


def spot_offset(k, t, start, nominal):
    """Return smooth modified target xyz for Spot with arm (k=3 or k=4).

    Preserves primary actions and orientation; avoids sudden acceleration across
    the 66-sample 5.2 s IK grid.
    """
    del start  # Preserved in signature for caller compatibility.
    cell = int(k)
    base = np.asarray(nominal, dtype=float).copy()
    t_val = float(t)
    if base.shape != (3,) or not np.isfinite(t_val) or not np.all(np.isfinite(base)):
        return base

    if cell == 3:
        # Traverse ends at t = 4.45 s; add a C2-smooth 1.0 cm free-space rise over [4.47, 5.15].
        w = _smoothstep5((t_val - 4.47) / 0.68)
        base[2] += 0.010 * w
    elif cell == 4:
        # Return completes at t = 4.75 s; apply a tiny C2-smooth park offset over [4.77, 5.20].
        w = _smoothstep5((t_val - 4.77) / 0.43)
        base[1] += 0.004 * w
        base[2] += 0.006 * w

    return base


def dock_speed_shape(u):
    """Return normalized (x, v) for Husky service k=2 asymmetric docking.

    Uses a C2-smooth asymmetric polynomial blending minimum-jerk quintic and
    feathered-approach sextic profiles:
      x(u) = 16 u^3 - 33 u^4 + 24 u^5 - 6 u^6
      v(u) = 12 u^2 (1 - u)^2 (4 - 3 u)
    Satisfies x(0)=0, x(1)=1, v(0)=v(1)=0, a(0)=a(1)=0, and gentler deceleration
    into the dock (peak velocity near u=0.431).
    """
    is_scalar = np.ndim(u) == 0
    u_arr = np.asarray(u, dtype=float)
    uc = np.clip(u_arr, 0.0, 1.0)

    x_poly = (uc ** 3) * (16.0 + uc * (-33.0 + uc * (24.0 - 6.0 * uc)))
    v_poly = 12.0 * (uc ** 2) * ((1.0 - uc) ** 2) * (4.0 - 3.0 * uc)

    x = np.where(u_arr <= 0.0, 0.0, np.where(u_arr >= 1.0, 1.0, x_poly))
    v = np.where((u_arr > 0.0) & (u_arr < 1.0), v_poly, 0.0)

    if is_scalar:
        return float(x), float(v)
    return x, v


def park_ctrl(k, t, goaltime, original_ctrl, wheelspeed):
    """Apply gentle closed-loop driveline park braking for Husky crossing k=1.

    Active only strictly after ``goaltime`` has been passed; preserves all
    in-motion control and human separation logic prior to goal arrival.
    """
    if int(k) != 1 or goaltime is None:
        return _copy_ctrl(original_ctrl)

    t_val = float(t)
    g_val = float(goaltime)
    if not (np.isfinite(t_val) and np.isfinite(g_val)) or t_val <= g_val:
        return _copy_ctrl(original_ctrl)

    blend = _smoothstep5((t_val - g_val) / 0.15)
    orig = np.asarray(original_ctrl, dtype=float)
    ws = np.asarray(wheelspeed, dtype=float)

    if ws.ndim == 0 or ws.shape == orig.shape:
        ws_aligned = ws
    elif orig.ndim == 1 and orig.size == 2 and ws.size == 4:
        ws_flat = ws.ravel()
        ws_aligned = np.array(
            [0.5 * (ws_flat[0] + ws_flat[2]), 0.5 * (ws_flat[1] + ws_flat[3])],
            dtype=float,
        )
    else:
        ws_aligned = float(np.mean(ws))

    brake = -np.clip(0.65 * ws_aligned, -1.8, 1.8)
    out = (1.0 - blend) * orig + blend * brake

    if np.isscalar(original_ctrl):
        return float(out)
    if isinstance(original_ctrl, list):
        return out.tolist()
    if isinstance(original_ctrl, tuple):
        return tuple(out.tolist())
    return np.asarray(out, dtype=float)


def detail_steps(k):
    """Return list of accurate additional English step descriptions for cell k."""
    return list(_DETAIL_STEPS.get(int(k), []))


def light_profile(k):
    """Return static nonflickering per-room light profile dictionary for cell k."""
    return dict(_LIGHT_PROFILES.get(int(k), _DEFAULT_LIGHT_PROFILE))
