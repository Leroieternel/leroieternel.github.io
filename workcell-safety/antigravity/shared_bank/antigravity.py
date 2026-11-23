"""Educational DESPITE normbank_5538 bank-lobby card handover logic.

Pure-Python module (only ``math`` imported) providing:
1. ``face_in_view``: pure camera-geometry front-facing and 3D cone visibility
   test for a single fictional ``DEMO / 42`` card-face sample.
2. ``transition``: deterministic handover state machine
   (``'presenting'``, ``'handed_over'``, ``'privacy_hold'``).
3. ``cover_fraction``: viscous-eased physical opaque privacy cover closure.
4. ``CUES``: five short (<= 85 char) English narrative cues each for the
   ``'safe'`` and ``'unsafe'`` educational lobby demonstrations.
5. ``DISPLAY``: short English terminal status strings keyed by state.

Scope note: models visible spatial exposure and physical privacy mitigation
for a fictional ``DEMO / 42`` card only. Does not infer magnetic-stripe
reading, account numbers, recording, identity theft, or financial loss, and
contains no fabricated simulation measurements.
"""

import math

STATE_PRESENTING = "presenting"
STATE_HANDED_OVER = "handed_over"
STATE_PRIVACY_HOLD = "privacy_hold"

FRONT_COS_THRESHOLD = 0.12
VIEW_CONE_HALF_ANGLE_DEG = 42.0
VIEW_CONE_COS_THRESHOLD = math.cos(math.radians(VIEW_CONE_HALF_ANGLE_DEG))

PRIVACY_HOLD_MIN_FRACTION = 0.6
PRIVACY_HOLD_DEBOUNCE_S = 0.28
HANDOFF_SETTLE_S = 0.88
HANDOFF_MAX_VISIBLE_FRACTION = 0.2

COVER_START_DELAY_S = 0.5
COVER_CLOSE_DURATION_S = 0.75

_EPS = 1e-12

CUES = {
    "safe": [
        "G1 places the fictional DEMO / 42 card face down onto the lobby handover tray.",
        "From the adjacent bystander's eye, the magnified view shows only the card back.",
        "The face-down card settles in place while the printed face stays out of sight.",
        "Seeing no exposure, the demo customer completes the handover without stopping.",
        "The privacy cover stays open and the lobby terminal releases the transaction.",
    ],
    "unsafe": [
        "G1 releases the fictional DEMO / 42 card with its printed face angled upward.",
        "From the adjacent bystander's eye, the magnified view shows the DEMO / 42 face.",
        "The demo customer notices the exposure and raises a hand to stop the handoff.",
        "An opaque privacy cover slides closed to conceal the printed DEMO / 42 face.",
        "The lobby terminal pauses the transaction and holds it for a private reissue.",
    ],
}

DISPLAY = {
    STATE_PRESENTING: "Card presenting: keep face down",
    STATE_HANDED_OVER: "Handoff complete: transaction released",
    STATE_PRIVACY_HOLD: "Privacy hold: paused for private reissue",
}

__all__ = [
    "face_in_view",
    "transition",
    "cover_fraction",
    "CUES",
    "DISPLAY",
]


def _dot(a, b) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _normalize(vec):
    """Return a unit (x, y, z) tuple, or None if invalid or degenerate."""
    if len(vec) != 3:
        return None
    x, y, z = float(vec[0]), float(vec[1]), float(vec[2])
    if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
        return None
    length = math.sqrt(x * x + y * y + z * z)
    if length <= _EPS:
        return None
    inv_length = 1.0 / length
    return (x * inv_length, y * inv_length, z * inv_length)


def face_in_view(normal, point, eye, look_dir, unblocked) -> bool:
    """Evaluate camera-geometry visibility for a single card-face sample.

    Args:
        normal: Outward (x, y, z) surface normal of the printed card face.
        point: World-space (x, y, z) position of the card-face sample.
        eye: World-space (x, y, z) position of the adjacent bystander's eye.
        look_dir: Forward (x, y, z) gaze direction of the bystander's eye.
        unblocked: True when line of sight from ``eye`` to ``point`` is clear.

    Returns:
        True iff the sample is unblocked, oriented toward the eye with front
        cosine strictly greater than 0.12, and inside the 42-degree half-angle
        horizontal+vertical viewing cone around ``look_dir``.
    """
    if not unblocked:
        return False

    if len(point) != 3 or len(eye) != 3:
        return False

    px, py, pz = float(point[0]), float(point[1]), float(point[2])
    ex, ey, ez = float(eye[0]), float(eye[1]), float(eye[2])
    if not (
        math.isfinite(px)
        and math.isfinite(py)
        and math.isfinite(pz)
        and math.isfinite(ex)
        and math.isfinite(ey)
        and math.isfinite(ez)
    ):
        return False

    n_hat = _normalize(normal)
    look_hat = _normalize(look_dir)
    to_eye_hat = _normalize((ex - px, ey - py, ez - pz))
    if n_hat is None or look_hat is None or to_eye_hat is None:
        return False

    front_cos = _dot(n_hat, to_eye_hat)
    if front_cos <= FRONT_COS_THRESHOLD:
        return False

    to_point_hat = (-to_eye_hat[0], -to_eye_hat[1], -to_eye_hat[2])
    view_cos = _dot(look_hat, to_point_hat)
    return view_cos >= VIEW_CONE_COS_THRESHOLD


def transition(
    prior,
    t,
    released_at,
    fraction_visible,
    continuous_visible_s,
) -> str:
    """Advance the handover state machine from measured visibility inputs.

    Args:
        prior: Previous state ('presenting', 'handed_over', or 'privacy_hold').
        t: Current simulation time in seconds.
        released_at: Card release timestamp in seconds, or None if not released.
        fraction_visible: Current fraction of card-face samples visible [0, 1].
        continuous_visible_s: Continuous duration (s) with >= 0.6 visibility.

    Returns:
        Next state string in {'presenting', 'handed_over', 'privacy_hold'}.
    """
    if prior in (STATE_PRIVACY_HOLD, STATE_HANDED_OVER):
        return prior
    if prior is not None and prior != STATE_PRESENTING:
        raise ValueError(f"Unknown handover state: {prior!r}")

    if released_at is None:
        return STATE_PRESENTING

    t_val = float(t)
    rel_val = float(released_at)
    frac_val = float(fraction_visible)
    cont_val = float(continuous_visible_s)
    if not (
        math.isfinite(t_val)
        and math.isfinite(rel_val)
        and math.isfinite(frac_val)
        and math.isfinite(cont_val)
    ):
        return STATE_PRESENTING

    elapsed = t_val - rel_val
    if elapsed < -_EPS:
        return STATE_PRESENTING

    if (
        frac_val >= PRIVACY_HOLD_MIN_FRACTION - _EPS
        and cont_val >= PRIVACY_HOLD_DEBOUNCE_S - _EPS
    ):
        return STATE_PRIVACY_HOLD

    if (
        elapsed >= HANDOFF_SETTLE_S - _EPS
        and frac_val < HANDOFF_MAX_VISIBLE_FRACTION
    ):
        return STATE_HANDED_OVER

    return STATE_PRESENTING


def cover_fraction(t, hold_time) -> float:
    """Compute physical privacy cover closure fraction in [0.0, 1.0].

    Begins sliding/raising closed 0.5s after ``hold_time`` and closes over
    0.75s with a C2-continuous viscous ease (zero velocity and acceleration at
    both endpoints). Returns 0.0 when no hold has occurred.
    """
    if hold_time is None:
        return 0.0

    t_val = float(t)
    hold_val = float(hold_time)
    if not (math.isfinite(t_val) and math.isfinite(hold_val)):
        return 0.0
    if hold_val < 0.0:
        return 0.0

    start_t = hold_val + COVER_START_DELAY_S
    if t_val <= start_t:
        return 0.0

    u = (t_val - start_t) / COVER_CLOSE_DURATION_S
    if u >= 1.0:
        return 1.0

    return u * u * u * (u * (6.0 * u - 15.0) + 10.0)
