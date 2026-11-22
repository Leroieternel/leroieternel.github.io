"""Post-cycle witness inspection profile and CNC room optics for a parked UR10e.

Applies only after the commissioning task completes and integration verifies
worker clearance outside the work area. Keeps joints 1-5 fixed so the wrist
center remains stationary and performs a small, C2-continuous roll, hold,
return, and settling sequence on joint 6 over 4.0 s.
"""

from __future__ import annotations

import numpy as np

DURATION_S: float = 4.0
MAX_JOINT6_OFFSET_RAD: float = 0.08  # Strictly within the 0.10 rad limit.

ROLL_DURATION_S: float = 1.1
WITNESS_HOLD_DURATION_S: float = 0.8
RETURN_DURATION_S: float = 1.1
SETTLE_HOLD_DURATION_S: float = 1.0

T_ROLL_END: float = ROLL_DURATION_S
T_HOLD_END: float = T_ROLL_END + WITNESS_HOLD_DURATION_S
T_RETURN_END: float = T_HOLD_END + RETURN_DURATION_S
T_TOTAL: float = T_RETURN_END + SETTLE_HOLD_DURATION_S

__all__ = [
    "DURATION_S",
    "MAX_JOINT6_OFFSET_RAD",
    "completion_offset",
    "steps",
    "optics",
]


def _smooth_unit(u: float) -> float:
    """C3-continuous (hence C2-continuous) unit ramp from 0 to 1 on [0, 1].

    Has zero first, second, and third derivatives at both endpoints so all
    stage transitions are smooth in position, velocity, acceleration, and jerk.
    """
    if u <= 0.0:
        return 0.0
    if u >= 1.0:
        return 1.0
    return u * u * u * u * (35.0 + u * (-84.0 + u * (70.0 - 20.0 * u)))


def completion_offset(elapsed_s: float) -> np.ndarray:
    """Return a 6-element UR10e joint offset vector (rad) after task completion.

    Args:
        elapsed_s: Time elapsed since the end of the commissioning run (seconds).

    Returns:
        NumPy float64 vector of shape (6,) with joints 1-5 fixed at 0.0 rad and
        joint 6 executing a C2-continuous roll, witness hold, return, and
        settling hold within [0.0, 0.08] rad over 4.0 s.
    """
    t = float(elapsed_s)
    offset = np.zeros(6, dtype=np.float64)

    if t <= 0.0 or t >= T_TOTAL:
        return offset

    if t < T_ROLL_END:
        u = t / ROLL_DURATION_S
        offset[5] = MAX_JOINT6_OFFSET_RAD * _smooth_unit(u)
    elif t < T_HOLD_END:
        offset[5] = MAX_JOINT6_OFFSET_RAD
    elif t < T_RETURN_END:
        u = (t - T_HOLD_END) / RETURN_DURATION_S
        offset[5] = MAX_JOINT6_OFFSET_RAD * (1.0 - _smooth_unit(u))
    else:
        offset[5] = 0.0

    return offset


def steps() -> list[tuple[float, str]]:
    """Return English (time_since_end_s, text) descriptions for each stage."""
    return [
        (
            0.0,
            "Roll empty UR10e wrist joint 6 in clear space while holding arm joints 1-5 fixed.",
        ),
        (
            T_ROLL_END,
            "Hold rolled wrist orientation for post-cycle witness inspection.",
        ),
        (
            T_HOLD_END,
            "Return wrist joint 6 smoothly to the neutral parked orientation.",
        ),
        (
            T_RETURN_END,
            "Hold neutral parked pose for final post-cycle settling.",
        ),
    ]


def optics() -> dict[str, object]:
    """Return fixed practical daylight color, sun angle (deg), and exposure."""
    return {
        "daylight_color": (1.0, 0.98, 0.95),
        "sun_angle_deg": 45.0,
        "exposure": 1.0,
    }
