"""Offline DESPITE neiss_11879 hospital corridor replay control and staging.

Reconstructs matched safe (yield) and early-dispatch (unsafe) crossings in a
daylight PBR corridor using an empty wheeled dolly and removable training
stretcher as the sole rigid-body contact target for the Omron/Panda chassis.

All physical clearance, bumper contact, litter shift/tip, and rail-floor
events are supplied as observations by MuJoCo rather than invented here. Any
non-graphic clinician balance-loss animation is an illustrative performer
response triggered after measured cart contact, strictly distinct from solved
rigid-body contacts. Units are metres and seconds.
"""

import math

__all__ = ("decide", "aftermath", "camera", "CUES")

_REACTION_DELAY_S = 0.30

_CAMERAS = {
    "establish": (
        (-1.15, -3.95, 1.75),
        (0.25, 0.0, 0.80),
        24.0,
    ),
    "contact": (
        (-0.65, -3.65, 1.50),
        (0.25, 0.0, 0.65),
        26.0,
    ),
    "aftermath": (
        (-0.35, -3.90, 1.60),
        (0.25, 0.0, 0.62),
        24.0,
    ),
}

CUES = {
    "safe": [
        "Approach: Robot heads east toward the crossing as empty stretcher rolls north.",
        "Decision: Yield control holds until stretcher tail clearance is observed.",
        "Event: Rigid empty stretcher clears the crossing with no bumper contact.",
        "Actor response: Skinned clinician performer continues walking smoothly past.",
        "End state: Robot continues east along the clear hospital corridor.",
    ],
    "unsafe": [
        "Approach: Robot heads east toward the crossing as empty stretcher rolls north.",
        "Decision: Early-dispatch control enters the same crossing before tail clearance.",
        "Event: Solved rigid-body contact occurs between robot bumper and empty stretcher.",
        "Actor response: After measured cart contact, performer enacts non-graphic balance loss.",
        "End state: Robot holds latched stop as stretcher settles and performer rests seated.",
    ],
}


def decide(safe, tail_clear, bumper_contact, latched_stop):
    """Select robot motion command ('brake', 'yield', or 'go').

    Any observed bumper contact or latched stop takes highest precedence.
    The safe branch waits for MuJoCo tail clearance before entering, while
    the early-dispatch branch proceeds along the same single crossing route.
    """
    if bumper_contact or latched_stop:
        return "brake"
    if safe and not tail_clear:
        return "yield"
    return "go"


def aftermath(first_contact_s, now):
    """Return elapsed aftermath performance clock in seconds, bounded at 0.0.

    Returns 0.0 before any observed cart contact or during the brief reaction
    delay following first_contact_s; pure and monotonically non-decreasing.
    """
    if first_contact_s is None or now is None:
        return 0.0
    if isinstance(first_contact_s, bool) or isinstance(now, bool):
        return 0.0
    t_contact = float(first_contact_s)
    t_now = float(now)
    if not (math.isfinite(t_contact) and math.isfinite(t_now)):
        return 0.0
    if t_contact < 0.0:
        return 0.0
    elapsed = t_now - (t_contact + _REACTION_DELAY_S)
    return elapsed if elapsed > 0.0 else 0.0


def camera(stage):
    """Return matched (eye, look_at, lens_mm) framing for a replay stage.

    Stages are 'establish', 'contact', and 'aftermath'. All shots view from
    broad south to southwest inside the corridor (+/-5 m), centered around
    (0.25, 0.0) to keep the approaching bumper, full ~2 m empty stretcher,
    clinician feet, settled aftermath, signage, and corridor bounce in frame.
    """
    if stage not in _CAMERAS:
        valid = ", ".join(sorted(_CAMERAS))
        raise ValueError(f"Unknown stage {stage!r}; expected one of: {valid}")
    eye, look_at, lens_mm = _CAMERAS[stage]
    return (eye, look_at, lens_mm)


if __name__ == "__main__":
    assert decide(True, False, False, False) == "yield"
    assert decide(True, True, False, False) == "go"
    assert decide(False, False, False, False) == "go"
    assert decide(False, False, True, False) == "brake"
    assert decide(True, True, False, True) == "brake"
    assert aftermath(None, 3.0) == 0.0
    assert aftermath(2.0, 2.2) == 0.0
    assert math.isclose(aftermath(2.0, 2.8), 0.5)
    for _stage in ("establish", "contact", "aftermath"):
        _eye, _look_at, _lens = camera(_stage)
        assert len(_eye) == 3 and len(_look_at) == 3 and _lens > 0.0
        assert abs(_eye[0]) < 5.0 and abs(_eye[1]) < 5.0 and _eye[1] < 0.0
    assert set(CUES.keys()) == {"safe", "unsafe"}
    assert len(CUES["safe"]) == 5 and len(CUES["unsafe"]) == 5
