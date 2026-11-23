"""Clinical stretcher handling release controller and filming cues."""

import math
from typing import Optional, Tuple

RELEASE_TILT_DEG = 10.0
RELEASE_MAX_SADDLE_LOAD_N = 35.0

GRIP_RELEASE_DURATION_S = 0.45
ARM_RETURN_DURATION_S = 0.55
GAIT_STOP_DURATION_S = 0.75
SETTLED_DURATION_S = 1.0

NORMAL_HANDLING_POSE = (1.0, 0.0, 1.0)
UPRIGHT_STOPPED_POSE = (0.0, 1.0, 0.0)


def _smoothstep(progress: float) -> float:
    """Return a C1-continuous ease value clamped cleanly to [0.0, 1.0]."""
    if progress <= 0.0:
        return 0.0
    if progress >= 1.0:
        return 1.0
    return progress * progress * (3.0 - 2.0 * progress)


def release_due(
    handled: bool,
    deck_tilt_deg: float,
    saddle_load_n: float,
) -> bool:
    """Return True only when a handled stretcher deck visibly tips off its saddle."""
    if not bool(handled):
        return False

    tilt_deg = abs(float(deck_tilt_deg))
    load_n = float(saddle_load_n)
    if not (math.isfinite(tilt_deg) and math.isfinite(load_n)):
        return False

    return tilt_deg >= RELEASE_TILT_DEG and load_n <= RELEASE_MAX_SADDLE_LOAD_N


def handling_pose(
    elapsed_since_release: Optional[float],
) -> Tuple[float, float, float]:
    """Return (grip_fraction, arm_return_fraction, gait_speed_fraction) for upright handling."""
    if elapsed_since_release is None:
        return NORMAL_HANDLING_POSE

    elapsed_s = float(elapsed_since_release)
    if math.isnan(elapsed_s) or elapsed_s <= 0.0:
        return NORMAL_HANDLING_POSE
    if elapsed_s >= SETTLED_DURATION_S:
        return UPRIGHT_STOPPED_POSE

    grip_fraction = 1.0 - _smoothstep(elapsed_s / GRIP_RELEASE_DURATION_S)
    arm_return_fraction = _smoothstep(elapsed_s / ARM_RETURN_DURATION_S)
    gait_speed_fraction = 1.0 - _smoothstep(elapsed_s / GAIT_STOP_DURATION_S)
    return (grip_fraction, arm_return_fraction, gait_speed_fraction)


def cue(released: bool, on_floor: bool, safe: bool) -> str:
    """Return a single-line present-tense filming caption (<= 64 characters)."""
    is_released = bool(released)
    is_on_floor = bool(on_floor)
    is_safe = bool(safe)

    if is_released:
        if is_on_floor:
            return "Deck lands on floor; clinician stays upright, hands off bar."
        return "Clinician stays upright, hands off bar as deck tips."

    if is_on_floor:
        return "Empty deck lands on floor; clinician remains upright."

    if is_safe:
        return "Safe robot yields; clinician guides empty stretcher."

    return "Clinician guides empty stretcher by the trailing bar."
