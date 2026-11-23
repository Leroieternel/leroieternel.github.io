import math

DIRECTOR = {
    "crossing": (
        "Pedestrian striding across crosswalk with heel-strike and toe-off",
        "Locked three-quarter street frame separating foreground robot from crosswalk clearance with zero shake",
    ),
    "hospital": (
        "Attendant pushing wheeled bed forward with steady heel-to-toe gait",
        "Steady elevated corridor angle holding bed tail and robot staging line unobstructed in separate depth planes",
    ),
    "bus": (
        "Queue passenger standing planted at curb before stepping off with toe-off toward bus door",
        "Tripod-locked curb angle separating foreground robot from queue front reaching bus door without occlusion",
    ),
    "meeting": (
        "Speaker gesturing mid-sentence with torso lean, neck turn, and hand follow-through",
        "Steady over-table-lip three-quarter shot framing speaker break cue and robot handover with settled end state",
    ),
    "hotel": (
        "Guest standing still at doorway with planted feet before torso-led wave of permission",
        "Locked doorway corridor framing keeping guest permission gesture and staged robot clear of occlusion",
    ),
    "library": (
        "Librarian walking along desk to seal parcel with torso, neck, and hand follow-through",
        "Steady elevated desk framing over table lip capturing parcel seal cue and clean settled placement",
    ),
    "warehouse": (
        "Worker standing planted beside rack before torso-and-neck check with hand follow-through",
        "Locked high-clearance aisle wide shot separating foreground robot path from worker and rack background",
    ),
    "market": (
        "Shopper walking along market counter with toe-off stride and reach follow-through",
        "Steady counter-height shot clearing table lip to show distinct release pose and settled item separation",
    ),
    "museum": (
        "Visitor standing planted beside display table before turning neck and torso to inspect",
        "Tripod-steady gallery angle clearing pedestal table lip with crisp foreground-background separation of settled artifact",
    ),
    "bank": (
        "Customer standing planted at teller counter before subtle neck turn and hand gesture",
        "Locked teller-counter angle above table lip keeping handoff release pose and settled tray unobstructed",
    ),
}

_SAFE_GATES = {
    "crossing": "clear",
    "hospital": "clear",
    "bus": "boarded",
    "meeting": "break",
    "hotel": "permission",
    "library": "sealed",
    "warehouse": None,
    "market": None,
    "museum": None,
    "bank": None,
}


def progress(t, t0, t1):
    if math.isnan(t) or math.isnan(t0) or math.isnan(t1):
        raise ValueError("progress inputs must not be NaN")
    if not (math.isfinite(t0) and math.isfinite(t1)):
        raise ValueError("t0 and t1 must be finite")
    if t1 <= t0:
        return 0.0 if t < t0 else 1.0
    if t <= t0:
        return 0.0
    if t >= t1:
        return 1.0
    u = (t - t0) / (t1 - t0)
    u2 = u * u
    val = (u2 * u2) * (35.0 + u * (-84.0 + u * (70.0 - 20.0 * u)))
    if val <= 0.0:
        return 0.0
    if val >= 1.0:
        return 1.0
    return val


def dispatch(slug, safe, t, observed):
    if not isinstance(slug, str) or slug not in _SAFE_GATES:
        raise ValueError(f"Unknown scenario slug: {slug!r}")
    gate = _SAFE_GATES[slug]
    if not safe or gate is None:
        return True
    if observed is None:
        return False
    return bool(observed[gate]) if gate in observed else False
