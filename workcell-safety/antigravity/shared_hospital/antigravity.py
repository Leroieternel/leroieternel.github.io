"""Lower-body animation rig utilities for the hospital dolly clinician replay.

Coordinate convention (world frame):
    - Clinician faces +Y
    - Anatomical right is +X (anatomical left is -X)
    - Floor up is +Z

All limb lengths are preserved analytically; reachability violations beyond
1e-5 metres raise ValueError rather than silently stretching a leg.
"""

import math
import numpy as np

__all__ = ["knee_point", "stance_targets", "swing_foot"]

_REACH_TOL_M = 1e-5
_OUTWARD_BIAS = 0.05
_ZERO_NORM_EPS = 1e-12
_DEGENERATE_PROJ_EPS = 1e-8


def _as_vec3(value, name):
    """Validate and convert a 3-element array-like to a finite float64 (3,) array."""
    vec = np.asarray(value, dtype=np.float64)
    if vec.shape != (3,):
        raise ValueError(f"{name} must have shape (3,), got {vec.shape}")
    if not np.all(np.isfinite(vec)):
        raise ValueError(f"{name} must contain only finite values")
    return vec


def _as_xy(value, name, allow_3d=False):
    """Validate and extract a finite float64 (2,) XY position."""
    vec = np.asarray(value, dtype=np.float64)
    valid_shapes = ((2,), (3,)) if allow_3d else ((2,),)
    if vec.shape not in valid_shapes:
        expected = "(2,) or (3,)" if allow_3d else "(2,)"
        raise ValueError(f"{name} must have shape {expected}, got {vec.shape}")
    if not np.all(np.isfinite(vec)):
        raise ValueError(f"{name} must contain only finite values")
    return vec[:2]


def _fallback_perpendicular(axis):
    """Return a deterministic unit vector orthogonal to a unit 3D axis."""
    # Prefer world +Z (floor up) when not nearly aligned with axis, then +X, then +Y.
    for candidate in (
        np.array((0.0, 0.0, 1.0), dtype=np.float64),
        np.array((1.0, 0.0, 0.0), dtype=np.float64),
        np.array((0.0, 1.0, 0.0), dtype=np.float64),
    ):
        proj = candidate - float(np.dot(candidate, axis)) * axis
        proj_norm = float(np.linalg.norm(proj))
        if proj_norm > 0.1:
            return proj / proj_norm
    raise ValueError("Unable to construct an orthogonal fallback axis")


def knee_point(hip, ankle, upper_length, lower_length, forward, lateral, side):
    """Compute an analytic two-bone knee position in world coordinates.

    Selects the anatomical forward-bending solution by projecting ``forward``
    onto the plane perpendicular to the hip-ankle chord, with a small symmetric
    outward lateral bias determined by ``side`` ('L' or 'R'). Never references
    a posed source knee, maintaining branch continuity through full extension.

    Parameters
    ----------
    hip : array_like, shape (3,)
        World-space hip joint center in metres.
    ankle : array_like, shape (3,)
        World-space ankle joint center target in metres.
    upper_length : float
        Thigh (hip-to-knee) bone length in metres (> 0).
    lower_length : float
        Shin (knee-to-ankle) bone length in metres (> 0).
    forward : array_like, shape (3,)
        Character forward direction in world coordinates (e.g. +Y).
    lateral : array_like, shape (3,)
        Character anatomical right direction in world coordinates (e.g. +X).
    side : {'L', 'R'}
        Leg side; 'R' biases outward along +lateral, 'L' along -lateral.

    Returns
    -------
    numpy.ndarray, shape (3,), dtype float64
        Analytic world-space knee joint position in metres.

    Raises
    ------
    ValueError
        If inputs are invalid or the ankle target lies outside the exact
        two-bone reach interval by more than 1e-5 metres.
    """
    hip_vec = _as_vec3(hip, "hip")
    ankle_vec = _as_vec3(ankle, "ankle")
    forward_vec = _as_vec3(forward, "forward")
    lateral_vec = _as_vec3(lateral, "lateral")

    upper_len = float(upper_length)
    lower_len = float(lower_length)
    if not math.isfinite(upper_len) or upper_len <= 0.0:
        raise ValueError(f"upper_length must be finite and positive, got {upper_length!r}")
    if not math.isfinite(lower_len) or lower_len <= 0.0:
        raise ValueError(f"lower_length must be finite and positive, got {lower_length!r}")

    if side == "L":
        side_sign = -1.0
    elif side == "R":
        side_sign = 1.0
    else:
        raise ValueError(f"side must be 'L' or 'R', got {side!r}")

    fwd_norm = float(np.linalg.norm(forward_vec))
    if fwd_norm <= _ZERO_NORM_EPS:
        raise ValueError("forward vector must have non-zero length")
    fwd_unit = forward_vec / fwd_norm

    lat_ortho = lateral_vec - float(np.dot(lateral_vec, fwd_unit)) * fwd_unit
    lat_ortho_norm = float(np.linalg.norm(lat_ortho))
    lat_unit = lat_ortho / lat_ortho_norm if lat_ortho_norm > _ZERO_NORM_EPS else None

    chord = ankle_vec - hip_vec
    chord_len = float(np.linalg.norm(chord))
    max_reach = upper_len + lower_len
    min_reach = abs(upper_len - lower_len)

    if chord_len > max_reach + _REACH_TOL_M:
        raise ValueError(
            f"Ankle target exceeds limb reach by {chord_len - max_reach:.6e} m "
            f"(distance={chord_len:.6f} m, max_reach={max_reach:.6f} m)"
        )
    if chord_len < min_reach - _REACH_TOL_M:
        raise ValueError(
            f"Ankle target is inside minimum limb reach by {min_reach - chord_len:.6e} m "
            f"(distance={chord_len:.6f} m, min_reach={min_reach:.6f} m)"
        )

    # Guard against a zero-length hip-ankle chord when upper_len == lower_len.
    if chord_len <= _ZERO_NORM_EPS:
        if lat_unit is not None:
            bend_raw = fwd_unit + (side_sign * _OUTWARD_BIAS) * lat_unit
            bend_dir = bend_raw / float(np.linalg.norm(bend_raw))
        else:
            bend_dir = fwd_unit
        return np.asarray(hip_vec + upper_len * bend_dir, dtype=np.float64)

    chord_axis = chord / chord_len

    # Clamp effective chord strictly inside [min_reach, max_reach] for tolerance-band
    # stability near full extension or full fold without stretching beyond 1e-5 m.
    effective_dist = float(np.clip(chord_len, min_reach, max_reach))
    along_dist = (
        upper_len * upper_len
        + effective_dist * effective_dist
        - lower_len * lower_len
    ) / (2.0 * effective_dist)

    # Factored Heron form avoids catastrophic cancellation near full extension.
    heron_product = (
        (max_reach - effective_dist)
        * (effective_dist + upper_len - lower_len)
        * (effective_dist - upper_len + lower_len)
        * (max_reach + effective_dist)
    )
    bend_height = math.sqrt(max(0.0, heron_product)) / (2.0 * effective_dist)

    # Project the anatomical forward direction onto the plane perpendicular to the chord.
    fwd_proj = fwd_unit - float(np.dot(fwd_unit, chord_axis)) * chord_axis
    fwd_proj_norm = float(np.linalg.norm(fwd_proj))
    if fwd_proj_norm > _DEGENERATE_PROJ_EPS:
        fwd_perp = fwd_proj / fwd_proj_norm
    else:
        # Degenerate-axis guard when hip-ankle chord is nearly collinear with forward.
        # Matches the continuous limit in the sagittal plane (+up forward, -up backward).
        sign_along = 1.0 if float(np.dot(fwd_unit, chord_axis)) >= 0.0 else -1.0
        if lat_unit is not None:
            sagittal_up = np.cross(lat_unit, fwd_unit)
            up_proj = sagittal_up - float(np.dot(sagittal_up, chord_axis)) * chord_axis
            up_norm = float(np.linalg.norm(up_proj))
            if up_norm > _ZERO_NORM_EPS:
                fwd_perp = (sign_along / up_norm) * up_proj
            else:
                fwd_perp = sign_along * _fallback_perpendicular(chord_axis)
        else:
            fwd_perp = sign_along * _fallback_perpendicular(chord_axis)

    if lat_unit is not None:
        lat_in_plane = lat_unit - float(np.dot(lat_unit, chord_axis)) * chord_axis
        lat_in_plane = lat_in_plane - float(np.dot(lat_in_plane, fwd_perp)) * fwd_perp
        bend_raw = fwd_perp + (side_sign * _OUTWARD_BIAS) * lat_in_plane
        bend_dir = bend_raw / float(np.linalg.norm(bend_raw))
    else:
        bend_dir = fwd_perp

    knee = hip_vec + along_dist * chord_axis + bend_height * bend_dir
    return np.asarray(knee, dtype=np.float64)


def stance_targets(
    root_xy,
    reference_hip,
    reference_left_ankle,
    reference_right_ankle,
):
    """Translate native +Y-oriented idle ankle XY offsets into a new stance.

    Preserves the native reference stance width, hip-to-ankle horizontal balance,
    and small longitudinal stagger without applying artificial yaw or rescaling.

    Parameters
    ----------
    root_xy : array_like, shape (2,)
        Target 2D world XY position for the stance root/hip.
    reference_hip : array_like, shape (2,) or (3,)
        Hip position in the native +Y-oriented idle reference frame.
    reference_left_ankle : array_like, shape (2,) or (3,)
        Left ankle-center position in the native +Y-oriented idle reference frame.
    reference_right_ankle : array_like, shape (2,) or (3,)
        Right ankle-center position in the native +Y-oriented idle reference frame.

    Returns
    -------
    numpy.ndarray, shape (2, 2), dtype float64
        Ordered array ``[left_ankle_xy, right_ankle_xy]`` in world XY coordinates.
    """
    root = _as_xy(root_xy, "root_xy", allow_3d=False)
    ref_hip = _as_xy(reference_hip, "reference_hip", allow_3d=True)
    ref_left = _as_xy(reference_left_ankle, "reference_left_ankle", allow_3d=True)
    ref_right = _as_xy(reference_right_ankle, "reference_right_ankle", allow_3d=True)

    left_target = root + (ref_left - ref_hip)
    right_target = root + (ref_right - ref_hip)
    return np.stack((left_target, right_target), axis=0).astype(np.float64, copy=False)


def swing_foot(start_xyz, end_xyz, u, lift_m):
    """Evaluate a single-sample minimum-jerk swing trajectory for a shoe anchor.

    Uses the quintic minimum-jerk blend ``10*s^3 - 15*s^4 + 6*s^5`` for 3D
    translation and adds a symmetric C2 vertical arch ``64*s^3*(1 - s)^3 * lift_m``
    along +Z with zero endpoint velocities and accelerations. Works identically
    for forward, backward, lateral, and diagonal steps.

    Parameters
    ----------
    start_xyz : array_like, shape (3,)
        World-space starting shoe contact anchor in metres.
    end_xyz : array_like, shape (3,)
        World-space ending shoe contact anchor in metres.
    u : float
        Normalized swing phase; clipped to ``[0.0, 1.0]``.
    lift_m : float
        Peak vertical arch clearance in metres at ``u = 0.5`` (>= 0).

    Returns
    -------
    numpy.ndarray, shape (3,), dtype float64
        World-space shoe contact anchor position in metres. Returns exact
        copies of ``start_xyz`` at ``u <= 0`` and ``end_xyz`` at ``u >= 1``.
    """
    start = _as_vec3(start_xyz, "start_xyz")
    end = _as_vec3(end_xyz, "end_xyz")

    phase = float(u)
    if not math.isfinite(phase):
        raise ValueError(f"u must be finite, got {u!r}")

    lift = float(lift_m)
    if not math.isfinite(lift) or lift < 0.0:
        raise ValueError(f"lift_m must be finite and non-negative, got {lift_m!r}")

    if phase <= 0.0:
        return start.copy()
    if phase >= 1.0:
        return end.copy()

    s = phase
    s2 = s * s
    s3 = s2 * s
    blend = s3 * (10.0 + s * (-15.0 + 6.0 * s))
    position = (1.0 - blend) * start + blend * end

    one_minus_s = 1.0 - s
    arch = 64.0 * s3 * (one_minus_s * one_minus_s * one_minus_s)
    position[2] += lift * arch
    return np.asarray(position, dtype=np.float64)
