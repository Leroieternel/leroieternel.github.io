"""Physical two-button cell operator module for robosuite Franka Panda studies.

Rebuilds ten industrial equipment-safety studies so a fixed-base Franka Panda arm
mounted on its own free-space service stand physically depresses spring-return
slide control keys on an adjacent operator kiosk. Real physical key stroke
(measured from the MuJoCo slide joints ``preflight_stroke`` and ``cycle_stroke``,
never inferred from geometric proximity) latches the PLC start trigger so the
downstream machine executes its baseline PLC mechanism program from ``t = 0``.

Primary task hazards concern EQUIPMENT; operator scenarios retain safe
separations and never generate arm motion toward humans.

Public API
----------
- ``panel_geometry(world, origin)``: Injects the kiosk surface, recessed key
  wells, and spring-return slide keys (``preflight_key`` / ``cycle_key`` and
  ``preflight_stroke`` / ``cycle_stroke``) into an MJCF ``worldbody``.
- ``tool_knots(k, branch, origin)``: Generates ``[(time, (x, y, z), yaw), ...]``
  for tasks ``1..10`` and branches ``"safe"`` / ``"unsafe"`` with identical
  total duration (~8.5-8.8 s), high clearance, 5-6 mm cap depression, ~0.4 s
  hold, stand parking, and a delayed post-park verification motion outside the
  work area after >3 s.
- ``program_steps(k, branch)``: Returns ``[(seconds, English_description), ...]``
  aligned with ``tool_knots(k, branch, origin)`` for UI/HUD and logging.
- ``PanelLatch(branch)``: Debounced physical-stroke latch with startup
  anti-accidental-start gating, repeat suppression, dwell verification, and
  exposed ``checked_at`` / ``started_at`` attributes.
- ``profile(k)``: Per-room optical design with realistic fixed exposure, key
  area window angle, and wall/floor Genie Sim photographic preset labels that
  forbid replacing photographic textures with flat shaders.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple
import xml.etree.ElementTree as ET

__all__ = [
    # Core required API
    "panel_geometry",
    "tool_knots",
    "program_steps",
    "PanelLatch",
    "profile",
    # Data models & registries
    "TaskSpec",
    "OpticalProfile",
    "TASKS",
    "PROFILES",
    "MODE_LABELS",
    "KEY_LABELS",
    "STROKE_LABELS",
    # Integration & geometry helpers
    "get_task",
    "normalize_branch",
    "panel_ui_labels",
    "service_stand_geometry",
    "sample_tool_pose",
    "flange_pose_from_tip",
    "read_panel_strokes",
    "validate_shader_policy",
    "FrankaCellOperator",
    # Geometry constants
    "PREFLIGHT_KEY_LOCAL",
    "CYCLE_KEY_LOCAL",
    "CAP_HALF_SIZE",
    "CAP_MAX_STROKE_M",
    "FACEPLATE_FLUSH_DEPTH_M",
    "FACEPLATE_TOP_Z_LOCAL",
    "DEFAULT_STAND_PARK_LOCAL",
    "TOOL_PAD_RADIUS_M",
    "PANDA_FLANGE_TO_TIP_M",
]

# ---------------------------------------------------------------------------
# Coordinate & mechanical constants (Robot BASE frame: +X forward, +Y left, +Z up)
# ---------------------------------------------------------------------------

# Unpressed cap top-face centers in robot BASE coordinates (meters).
PREFLIGHT_KEY_LOCAL: Tuple[float, float, float] = (0.42, -0.13, 0.30)
CYCLE_KEY_LOCAL: Tuple[float, float, float] = (0.42, 0.13, 0.30)

# Moving cap half-extents (hx, hy, hz) in meters: 84 mm x 92 mm x 14 mm cap.
CAP_HALF_SIZE: Tuple[float, float, float] = (0.042, 0.046, 0.007)

# Slide joint downward travel limit along global -Z (positive qpos = downward).
CAP_MAX_STROKE_M: float = 0.008

# Pressure caps become flush with the surrounding plate only after > 5.0 mm
# depression (5.5 mm nominal flush plane; recessed from 5.5 mm to 8.0 mm).
FACEPLATE_FLUSH_DEPTH_M: float = 0.0055
FACEPLATE_TOP_Z_LOCAL: float = PREFLIGHT_KEY_LOCAL[2] - FACEPLATE_FLUSH_DEPTH_M  # 0.2945 m

# Mechanical clearance between cap perimeter and recessed deck cutout walls.
WELL_WALL_CLEARANCE_M: float = 0.004
WELL_FLOOR_Z_LOCAL: float = 0.274  # 4 mm below cap bottom even at full 8 mm stroke
CONSOLE_BOTTOM_Z_LOCAL: float = 0.230

# Physical spring-return plunger parameters (critically damped, zero gravity sag).
KEY_MASS_KG: float = 0.040
KEY_DIAGINERTIA: Tuple[float, float, float] = (0.000029, 0.000024, 0.000052)
KEY_SPRING_STIFFNESS: float = 1600.0  # N/m (~10 N at 6 mm press)
KEY_SPRING_DAMPING: float = 14.0  # N*s/m (smooth non-ringing return)
KEY_SPRING_PRELOAD_REF: float = -0.0005  # m upward preload against qpos=0 upper stop
KEY_FRICTIONLOSS: float = 0.15  # N
KEY_ARMATURE: float = 0.02  # kg

# Nominal rounded tool-pad geometry for downward neutral Franka Panda orientation.
# All tool_knots positions refer to the actual lowest point of this rounded pad.
TOOL_PAD_RADIUS_M: float = 0.012
PANDA_FLANGE_TO_TIP_M: float = 0.145

# High-clearance stand park pose (robot BASE frame), clear of kiosk & work area.
DEFAULT_STAND_PARK_LOCAL: Tuple[float, float, float] = (0.22, 0.00, 0.56)

# Readable English UI labels for simulation HUD, Studio panels, and logs.
MODE_LABELS: Dict[str, str] = {
    "safe": "Two-Step Verified Start (Pre-Flight Interlock + Cycle Start)",
    "unsafe": "Direct Cycle-Start Shortcut (Pre-Flight Interlock Bypassed)",
}

KEY_LABELS: Dict[str, str] = {
    "preflight_key": "Pre-Flight Verification Key",
    "cycle_key": "Cycle Start Key",
}

STROKE_LABELS: Dict[str, str] = {
    "preflight_stroke": "Pre-Flight Key Physical Stroke (m)",
    "cycle_stroke": "Cycle Start Key Physical Stroke (m)",
}


# ---------------------------------------------------------------------------
# Task specifications (Studies 1..10)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TaskSpec:
    """Definition for one of the ten industrial equipment-safety studies."""

    task_id: int
    name: str
    short_slug: str
    room_type: str
    preflight_label: str
    cycle_label: str
    equipment_hazard: str
    separation_note: str
    press_depth_m: float
    hold_duration_s: float
    descent_duration_s: float
    total_duration_s: float
    verify_offset_xyz: Tuple[float, float, float]


TASKS: Dict[int, TaskSpec] = {
    1: TaskSpec(
        task_id=1,
        name="Warehouse Crossing",
        short_slug="warehouse_crossing",
        room_type="warehouse",
        preflight_label="Yield crossing lane",
        cycle_label="Send cargo across crossing",
        equipment_hazard="Cross-aisle cargo carrier collision with intersecting transfer vehicle.",
        separation_note="Robot stand positioned outside pedestrian walkway; arm stays inside stand/kiosk envelope.",
        press_depth_m=0.0058,
        hold_duration_s=0.42,
        descent_duration_s=0.22,
        total_duration_s=8.60,
        verify_offset_xyz=(-0.04, 0.05, 0.025),
    ),
    2: TaskSpec(
        task_id=2,
        name="Hospital Door and Trolley",
        short_slug="hospital_door_and_trolley",
        room_type="clinic",
        preflight_label="Engage door interlock",
        cycle_label="Send trolley through doorway",
        equipment_hazard="Powered trolley impact against unlatched or closing automatic corridor door.",
        separation_note="Service stand sits behind corridor guardrail; zero trajectory excursion into hallway.",
        press_depth_m=0.0056,
        hold_duration_s=0.40,
        descent_duration_s=0.22,
        total_duration_s=8.60,
        verify_offset_xyz=(-0.04, -0.05, 0.025),
    ),
    3: TaskSpec(
        task_id=3,
        name="Cafe Flask & Serving Tray",
        short_slug="cafe_flask_and_serving_tray",
        room_type="cafe",
        preflight_label="Clear return lane",
        cycle_label="Dispatch flask and serving tray",
        equipment_hazard="Thermal flask topple and glassware impact against occupied tray return chute.",
        separation_note="Kiosk and stand face back-of-house equipment track away from customer counter.",
        press_depth_m=0.0056,
        hold_duration_s=0.40,
        descent_duration_s=0.24,
        total_duration_s=8.60,
        verify_offset_xyz=(-0.04, 0.045, 0.020),
    ),
    4: TaskSpec(
        task_id=4,
        name="Sealed Rack and Shelf",
        short_slug="sealed_rack_and_shelf",
        room_type="lab",
        preflight_label="Confirm shelf alignment",
        cycle_label="Advance sealed rack transfer",
        equipment_hazard="Rack shear or seal breach from misaligned indexing shelf rails.",
        separation_note="Arm remains behind lab console perimeter with full clearance from personnel zone.",
        press_depth_m=0.0057,
        hold_duration_s=0.42,
        descent_duration_s=0.22,
        total_duration_s=8.60,
        verify_offset_xyz=(-0.035, -0.045, 0.025),
    ),
    5: TaskSpec(
        task_id=5,
        name="Parcel Transfer Bridge",
        short_slug="parcel_transfer_bridge",
        room_type="warehouse",
        preflight_label="Deploy bridge and verify mandatory outfeed terminal support",
        cycle_label="Push parcel across transfer bridge",
        equipment_hazard="Parcel drop and pusher jam if bridge is undeployed or outfeed terminal support is absent.",
        separation_note="Fixed service stand isolated beside bridge console, clear of parcel drop zone.",
        press_depth_m=0.0059,
        hold_duration_s=0.44,
        descent_duration_s=0.22,
        total_duration_s=8.70,
        verify_offset_xyz=(-0.04, 0.05, 0.030),
    ),
    6: TaskSpec(
        task_id=6,
        name="Repair Shaft Gate",
        short_slug="repair_shaft_gate",
        room_type="workshop",
        preflight_label="Seat cradle",
        cycle_label="Cycle repair shaft gate",
        equipment_hazard="Gate pinch or unseated maintenance cradle drop inside service shaft.",
        separation_note="Robot stand anchored outside shaft safety curb; no reach across shaft plane.",
        press_depth_m=0.0058,
        hold_duration_s=0.42,
        descent_duration_s=0.22,
        total_duration_s=8.60,
        verify_offset_xyz=(-0.04, -0.05, 0.025),
    ),
    7: TaskSpec(
        task_id=7,
        name="Electronics Drawer",
        short_slug="electronics_drawer",
        room_type="lab",
        preflight_label="Retract diagnostic plug",
        cycle_label="Actuate electronics drawer",
        equipment_hazard="Harness shear and PCB connector damage if drawer retracts with diagnostic plug mated.",
        separation_note="Stand positioned beside ESD test console with clear separation from technician bench.",
        press_depth_m=0.0055,
        hold_duration_s=0.40,
        descent_duration_s=0.23,
        total_duration_s=8.50,
        verify_offset_xyz=(-0.035, 0.045, 0.020),
    ),
    8: TaskSpec(
        task_id=8,
        name="Print Carriage",
        short_slug="print_carriage",
        room_type="workshop",
        preflight_label="Select gentle velocity",
        cycle_label="Start print carriage traverse",
        equipment_hazard="Printhead crash or media skew from high-acceleration carriage launch.",
        separation_note="Operator arm confined to side console pedestal away from gantry traverse envelope.",
        press_depth_m=0.0056,
        hold_duration_s=0.44,
        descent_duration_s=0.26,
        total_duration_s=8.70,
        verify_offset_xyz=(-0.035, -0.045, 0.020),
    ),
    9: TaskSpec(
        task_id=9,
        name="Library Cart",
        short_slug="library_cart",
        room_type="library",
        preflight_label="Lower book lift",
        cycle_label="Dispatch library cart",
        equipment_hazard="Elevated book-lift mast collision with low sorting archway during cart drive.",
        separation_note="Service stand tucked beside archival return bay, completely clear of patron aisles.",
        press_depth_m=0.0056,
        hold_duration_s=0.40,
        descent_duration_s=0.22,
        total_duration_s=8.60,
        verify_offset_xyz=(-0.04, 0.045, 0.025),
    ),
    10: TaskSpec(
        task_id=10,
        name="Packing Tote",
        short_slug="packing_tote",
        room_type="warehouse",
        preflight_label="Index receiver",
        cycle_label="Feed packing tote",
        equipment_hazard="Tote jam and conveyor diverter overload when receiver station is unindexed.",
        separation_note="Stand mounted outside fulfillment lane guardrail with unobstructed operator egress.",
        press_depth_m=0.0058,
        hold_duration_s=0.42,
        descent_duration_s=0.22,
        total_duration_s=8.60,
        verify_offset_xyz=(-0.04, -0.05, 0.025),
    ),
}


def get_task(k: int) -> TaskSpec:
    """Return the ``TaskSpec`` for study index ``k`` in ``1..10``."""
    if not isinstance(k, int) or isinstance(k, bool) or k not in TASKS:
        raise ValueError(f"Task index k must be an integer in 1..10, got {k!r}.")
    return TASKS[k]


def normalize_branch(branch: str) -> str:
    """Validate and normalize branch identifier to ``'safe'`` or ``'unsafe'``."""
    if not isinstance(branch, str):
        raise ValueError(f"Branch must be 'safe' or 'unsafe', got {branch!r}.")
    cleaned = branch.strip().lower()
    if cleaned not in ("safe", "unsafe"):
        raise ValueError(f"Branch must be 'safe' or 'unsafe', got {branch!r}.")
    return cleaned


def panel_ui_labels(
    k: Optional[int] = None,
    branch: Optional[str] = None,
) -> Dict[str, str]:
    """Return readable English UI labels for the two-button control station."""
    labels: Dict[str, str] = {
        "panel_title": "Two-Button Physical Cell Control Panel",
        "preflight_key": KEY_LABELS["preflight_key"],
        "cycle_key": KEY_LABELS["cycle_key"],
        "preflight_stroke": STROKE_LABELS["preflight_stroke"],
        "cycle_stroke": STROKE_LABELS["cycle_stroke"],
        "safe_mode": MODE_LABELS["safe"],
        "unsafe_mode": MODE_LABELS["unsafe"],
    }
    if k is not None:
        spec = get_task(k)
        labels["task_name"] = f"Study {spec.task_id}: {spec.name}"
        labels["preflight_key"] = f"Pre-Flight Key — {spec.preflight_label}"
        labels["cycle_key"] = f"Cycle Start Key — {spec.cycle_label}"
        labels["equipment_hazard"] = spec.equipment_hazard
        labels["separation_note"] = spec.separation_note
    if branch is not None:
        b = normalize_branch(branch)
        labels["active_mode"] = MODE_LABELS[b]
    return labels


# ---------------------------------------------------------------------------
# Internal vector / XML helpers
# ---------------------------------------------------------------------------


def _unpack_origin(origin: Sequence[float]) -> Tuple[float, float, float]:
    """Convert any 3-element coordinate sequence into a plain float 3-tuple."""
    try:
        vals = tuple(float(v) for v in origin)
    except TypeError as exc:
        raise ValueError(f"origin must be a 3-element XYZ sequence, got {origin!r}.") from exc
    if len(vals) != 3 or not all(math.isfinite(v) for v in vals):
        raise ValueError(f"origin must contain 3 finite floats, got {origin!r}.")
    return vals[0], vals[1], vals[2]


def _fmt3(x: float, y: float, z: float) -> str:
    return f"{x:.6f} {y:.6f} {z:.6f}"


def _resolve_worldbody(world: Any) -> ET.Element:
    """Resolve an ``ElementTree``, ``<mujoco>``, or ``<worldbody>`` to ``<worldbody>``."""
    if isinstance(world, ET.ElementTree):
        root = world.getroot()
    elif isinstance(world, ET.Element):
        root = world
    else:
        raise TypeError(
            "world must be an xml.etree.ElementTree.Element (worldbody or mujoco root) "
            f"or ElementTree, got {type(world).__name__}."
        )
    if root.tag == "worldbody":
        return root
    wb = root.find("worldbody")
    if wb is not None:
        return wb
    if root.tag == "mujoco":
        return ET.SubElement(root, "worldbody")
    return root


# ---------------------------------------------------------------------------
# (a) MJCF Kiosk & Spring-Return Two-Button Panel Geometry
# ---------------------------------------------------------------------------


def panel_geometry(
    world: Any,
    origin: Sequence[float],
) -> ET.Element:
    """Add the two-button spring-return control kiosk to an MJCF ``worldbody``.

    Coordinate convention
    ---------------------
    ``origin`` is the world XYZ position of the Franka Panda base with zero
    rotation. In robot BASE coordinates:

    - ``preflight_key`` unpressed cap top face center: ``(0.42, -0.13, 0.30)``
    - ``cycle_key`` unpressed cap top face center: ``(0.42, +0.13, 0.30)``
    - Cap box half-extents: ``(0.042, 0.046, 0.007)`` (7 mm half-height)
    - Slide joints ``preflight_stroke`` and ``cycle_stroke`` travel along global
      ``-Z`` with ``axis="0 0 -1"`` and ``range="0 0.008"`` (positive qpos =
      downward travel up to 8 mm).
    - The surrounding kiosk faceplate top sits at ``z = 0.2945`` (5.5 mm below
      the unpressed cap top), so caps become flush/recessed with the plate only
      after ``> 5 mm`` of physical depression.
    - Non-overlapping deck strips form true physical wells around each cap with
      4 mm perimeter clearance and a well floor 4 mm below full 8 mm stroke.
    - Contains zero robot phantom geometries and remains clear of robot base and
      approach reach envelopes.

    Parameters
    ----------
    world:
        An ``xml.etree.ElementTree.Element`` representing ``<worldbody>`` (or a
        parent ``<mujoco>`` element / ``ElementTree`` containing ``<worldbody>``).
    origin:
        World XYZ ``(ox, oy, oz)`` of the Franka Panda base.

    Returns
    -------
    xml.etree.ElementTree.Element
        The newly added ``<body name="operator_panel_kiosk">`` element.
    """
    ox, oy, oz = _unpack_origin(origin)
    worldbody = _resolve_worldbody(world)

    # Replace any previously injected panel body to keep re-generation idempotent.
    for existing in list(worldbody.findall("body")):
        if existing.get("name") == "operator_panel_kiosk":
            worldbody.remove(existing)

    kiosk = ET.SubElement(
        worldbody,
        "body",
        {
            "name": "operator_panel_kiosk",
            "pos": _fmt3(ox, oy, oz),
        },
    )

    hx_cap, hy_cap, hz_cap = CAP_HALF_SIZE
    kx = PREFLIGHT_KEY_LOCAL[0]  # 0.42
    y_pre = PREFLIGHT_KEY_LOCAL[1]  # -0.13
    y_cyc = CYCLE_KEY_LOCAL[1]  # +0.13
    z_cap_top = PREFLIGHT_KEY_LOCAL[2]  # 0.30
    z_cap_center = z_cap_top - hz_cap  # 0.293

    # Recessed well bounds in robot BASE coordinates.
    well_x_min = kx - (hx_cap + WELL_WALL_CLEARANCE_M)  # 0.374
    well_x_max = kx + (hx_cap + WELL_WALL_CLEARANCE_M)  # 0.466
    pre_y_min = y_pre - (hy_cap + WELL_WALL_CLEARANCE_M)  # -0.180
    pre_y_max = y_pre + (hy_cap + WELL_WALL_CLEARANCE_M)  # -0.080
    cyc_y_min = y_cyc - (hy_cap + WELL_WALL_CLEARANCE_M)  # +0.080
    cyc_y_max = y_cyc + (hy_cap + WELL_WALL_CLEARANCE_M)  # +0.180

    # Outer console deck bounds: compact footprint well clear of robot base at (0, 0).
    deck_x_min = 0.330
    deck_x_max = 0.510
    deck_y_min = -0.230
    deck_y_max = 0.230

    def _add_box_geom(
        parent: ET.Element,
        name: str,
        x0: float,
        x1: float,
        y0: float,
        y1: float,
        z0: float,
        z1: float,
        rgba: str,
    ) -> ET.Element:
        cx, hx = 0.5 * (x0 + x1), 0.5 * (x1 - x0)
        cy, hy = 0.5 * (y0 + y1), 0.5 * (y1 - y0)
        cz, hz = 0.5 * (z0 + z1), 0.5 * (z1 - z0)
        return ET.SubElement(
            parent,
            "geom",
            {
                "name": name,
                "type": "box",
                "pos": _fmt3(cx, cy, cz),
                "size": _fmt3(hx, hy, hz),
                "rgba": rgba,
                "contype": "1",
                "conaffinity": "1",
                "friction": "0.6 0.005 0.0001",
                "solref": "0.006 1",
                "solimp": "0.9 0.95 0.001",
            },
        )

    plate_rgba = "0.18 0.20 0.23 1"
    chassis_rgba = "0.24 0.27 0.31 1"
    pedestal_rgba = "0.32 0.35 0.39 1"

    # 1. Five non-overlapping top faceplate strips forming two physical button wells.
    #    Top surface sits at z = 0.2945 (5.5 mm below unpressed cap top at 0.300).
    _add_box_geom(
        kiosk,
        "panel_faceplate_near",
        deck_x_min,
        well_x_min,
        deck_y_min,
        deck_y_max,
        WELL_FLOOR_Z_LOCAL,
        FACEPLATE_TOP_Z_LOCAL,
        plate_rgba,
    )
    _add_box_geom(
        kiosk,
        "panel_faceplate_far",
        well_x_max,
        deck_x_max,
        deck_y_min,
        deck_y_max,
        WELL_FLOOR_Z_LOCAL,
        FACEPLATE_TOP_Z_LOCAL,
        plate_rgba,
    )
    _add_box_geom(
        kiosk,
        "panel_faceplate_outer_neg_y",
        well_x_min,
        well_x_max,
        deck_y_min,
        pre_y_min,
        WELL_FLOOR_Z_LOCAL,
        FACEPLATE_TOP_Z_LOCAL,
        plate_rgba,
    )
    _add_box_geom(
        kiosk,
        "panel_faceplate_divider",
        well_x_min,
        well_x_max,
        pre_y_max,
        cyc_y_min,
        WELL_FLOOR_Z_LOCAL,
        FACEPLATE_TOP_Z_LOCAL,
        plate_rgba,
    )
    _add_box_geom(
        kiosk,
        "panel_faceplate_outer_pos_y",
        well_x_min,
        well_x_max,
        cyc_y_max,
        deck_y_max,
        WELL_FLOOR_Z_LOCAL,
        FACEPLATE_TOP_Z_LOCAL,
        plate_rgba,
    )

    # 2. Solid console housing beneath the two recessed button wells.
    _add_box_geom(
        kiosk,
        "panel_chassis_underbody",
        deck_x_min,
        deck_x_max,
        deck_y_min,
        deck_y_max,
        CONSOLE_BOTTOM_Z_LOCAL,
        WELL_FLOOR_Z_LOCAL,
        chassis_rgba,
    )

    # 3. Freestanding floor pedestal offset forward under the kiosk so it never
    #    intersects the robot's own service stand around (0, 0) or arm reach.
    floor_world_z = 0.0 if oz >= 0.0 else oz
    floor_local_z = floor_world_z - oz
    footplate_thickness = 0.016
    footplate_top_local_z = floor_local_z + footplate_thickness

    _add_box_geom(
        kiosk,
        "panel_pedestal_base",
        0.355,
        0.525,
        -0.165,
        0.165,
        floor_local_z,
        footplate_top_local_z,
        pedestal_rgba,
    )
    _add_box_geom(
        kiosk,
        "panel_pedestal_column",
        0.395,
        0.505,
        -0.095,
        0.095,
        footplate_top_local_z,
        CONSOLE_BOTTOM_Z_LOCAL,
        pedestal_rgba,
    )

    # Non-colliding nominal surface reference sites (invisible in renders).
    ET.SubElement(
        kiosk,
        "site",
        {
            "name": "preflight_key_top",
            "pos": _fmt3(*PREFLIGHT_KEY_LOCAL),
            "size": "0.004",
            "rgba": "0.92 0.66 0.12 0",
        },
    )
    ET.SubElement(
        kiosk,
        "site",
        {
            "name": "cycle_key_top",
            "pos": _fmt3(*CYCLE_KEY_LOCAL),
            "size": "0.004",
            "rgba": "0.16 0.68 0.32 0",
        },
    )

    # 4. Two spring-return slide button assemblies.
    def _add_key_assembly(
        body_name: str,
        joint_name: str,
        geom_name: str,
        y_pos: float,
        rgba: str,
    ) -> ET.Element:
        key_body = ET.SubElement(
            kiosk,
            "body",
            {
                "name": body_name,
                "pos": _fmt3(kx, y_pos, z_cap_center),
            },
        )
        ET.SubElement(
            key_body,
            "inertial",
            {
                "pos": "0 0 0",
                "mass": f"{KEY_MASS_KG:.6f}",
                "diaginertia": _fmt3(*KEY_DIAGINERTIA),
            },
        )
        ET.SubElement(
            key_body,
            "joint",
            {
                "name": joint_name,
                "type": "slide",
                "axis": "0 0 -1",
                "limited": "true",
                "range": f"0 {CAP_MAX_STROKE_M:.6f}",
                "stiffness": f"{KEY_SPRING_STIFFNESS:.4f}",
                "damping": f"{KEY_SPRING_DAMPING:.4f}",
                "springref": f"{KEY_SPRING_PRELOAD_REF:.6f}",
                "frictionloss": f"{KEY_FRICTIONLOSS:.4f}",
                "armature": f"{KEY_ARMATURE:.4f}",
                "solreflimit": "0.004 1",
                "solimplimit": "0.95 0.99 0.0005",
            },
        )
        ET.SubElement(
            key_body,
            "geom",
            {
                "name": geom_name,
                "type": "box",
                "pos": "0 0 0",
                "size": _fmt3(*CAP_HALF_SIZE),
                "rgba": rgba,
                "contype": "1",
                "conaffinity": "1",
                "friction": "0.6 0.005 0.0001",
                "solref": "0.006 1",
                "solimp": "0.9 0.95 0.001",
            },
        )
        return key_body

    _add_key_assembly(
        body_name="preflight_key_body",
        joint_name="preflight_stroke",
        geom_name="preflight_key",
        y_pos=y_pre,
        rgba="0.92 0.66 0.12 1",
    )
    _add_key_assembly(
        body_name="cycle_key_body",
        joint_name="cycle_stroke",
        geom_name="cycle_key",
        y_pos=y_cyc,
        rgba="0.16 0.68 0.32 1",
    )

    return kiosk


def service_stand_geometry(
    world: Any,
    origin: Sequence[float],
    *,
    stand_radius_m: float = 0.145,
    base_plate_radius_m: float = 0.210,
) -> Optional[ET.Element]:
    """Optionally add the Franka Panda's own free-space service stand below ``origin``.

    Only emits geometry when ``origin[2] > 0.02`` (elevated fixed-base stand).
    Clear of the kiosk pedestal (which begins at ``x = 0.355``).
    """
    ox, oy, oz = _unpack_origin(origin)
    if oz <= 0.02:
        return None

    worldbody = _resolve_worldbody(world)
    for existing in list(worldbody.findall("body")):
        if existing.get("name") == "panda_service_stand":
            worldbody.remove(existing)

    stand = ET.SubElement(
        worldbody,
        "body",
        {
            "name": "panda_service_stand",
            "pos": _fmt3(ox, oy, 0.0),
        },
    )
    plate_h = 0.020
    top_flange_h = 0.018
    col_h = max(0.01, oz - plate_h - top_flange_h)

    ET.SubElement(
        stand,
        "geom",
        {
            "name": "panda_stand_floor_plate",
            "type": "cylinder",
            "pos": _fmt3(0.0, 0.0, 0.5 * plate_h),
            "size": f"{base_plate_radius_m:.6f} {0.5 * plate_h:.6f}",
            "rgba": "0.26 0.29 0.33 1",
            "contype": "1",
            "conaffinity": "1",
        },
    )
    ET.SubElement(
        stand,
        "geom",
        {
            "name": "panda_stand_column",
            "type": "cylinder",
            "pos": _fmt3(0.0, 0.0, plate_h + 0.5 * col_h),
            "size": f"{stand_radius_m:.6f} {0.5 * col_h:.6f}",
            "rgba": "0.34 0.38 0.43 1",
            "contype": "1",
            "conaffinity": "1",
        },
    )
    ET.SubElement(
        stand,
        "geom",
        {
            "name": "panda_stand_mount_flange",
            "type": "cylinder",
            "pos": _fmt3(0.0, 0.0, oz - 0.5 * top_flange_h),
            "size": f"{stand_radius_m + 0.02:.6f} {0.5 * top_flange_h:.6f}",
            "rgba": "0.20 0.22 0.25 1",
            "contype": "1",
            "conaffinity": "1",
        },
    )
    return stand


# ---------------------------------------------------------------------------
# (b) Task-Parameterized Tool Knots & Per-Branch Program Steps
# ---------------------------------------------------------------------------


def _build_branch_schedule(
    k: int,
    branch: str,
) -> Tuple[List[Tuple[float, Tuple[float, float, float], float]], List[Tuple[float, str]]]:
    """Compute coupled local-frame tool knots and English program steps.

    All tip coordinates represent the actual lowest point of the rounded tool
    pad in downward neutral orientation (``yaw = 0.0`` during key contact).
    Both ``'safe'`` and ``'unsafe'`` share the exact same ``total_duration_s``.
    """
    spec = get_task(k)
    b = normalize_branch(branch)

    px, py_pre, z_cap = PREFLIGHT_KEY_LOCAL
    _, py_cyc, _ = CYCLE_KEY_LOCAL

    z_high = 0.465  # 165 mm high clearance above unpressed key caps
    z_lift_exit = 0.485  # 185 mm exit clearance before stand park
    z_approach = z_cap + 0.012  # 12 mm controlled pre-contact hover
    z_press = z_cap - spec.press_depth_m  # 5.5-5.9 mm past unpressed cap surface

    park = DEFAULT_STAND_PARK_LOCAL
    vx, vy, vz = spec.verify_offset_xyz
    # Verification check stays strictly behind/above the service stand (x <= 0.22),
    # completely outside the kiosk & machine work area and away from any humans.
    verify_a = (park[0] + vx, park[1] + vy, park[2] + vz)
    verify_b = (park[0] + vx, park[1] - vy, park[2] + vz)

    hold = spec.hold_duration_s
    desc = spec.descent_duration_s
    t_total = spec.total_duration_s

    # Reserve the final 1.20 s window for the delayed verification motion outside
    # the work area, guaranteeing > 3.0 s quiet dwell after parking in both branches.
    t_verify_end = t_total
    t_verify_b = round(t_verify_end - 0.40, 4)
    t_verify_a = round(t_verify_end - 0.80, 4)
    t_verify_start = round(t_verify_end - 1.20, 4)

    knots_local: List[Tuple[float, Tuple[float, float, float], float]] = []
    steps: List[Tuple[float, str]] = []

    def _add(t: float, xyz: Tuple[float, float, float], yaw: float, label: Optional[str] = None) -> None:
        t_r = round(t, 4)
        knots_local.append((t_r, (round(xyz[0], 6), round(xyz[1], 6), round(xyz[2], 6)), round(yaw, 6)))
        if label is not None:
            steps.append((t_r, label))

    if b == "safe":
        t = 0.00
        _add(t, park, 0.0, f"Parked above service stand ({spec.name} — Safe Two-Step Mode)")

        t += 0.62
        _add(t, (px, py_pre, z_high), 0.0, f"High-clearance transit above Pre-Flight key ({spec.preflight_label})")

        t += 0.34
        _add(t, (px, py_pre, z_approach), 0.0)

        t += desc
        _add(
            t,
            (px, py_pre, z_press),
            0.0,
            f"Depress Pre-Flight key ({spec.press_depth_m * 1e3:.1f} mm stroke): {spec.preflight_label}",
        )

        t += hold
        _add(
            t,
            (px, py_pre, z_press),
            0.0,
            f"Hold Pre-Flight key ({hold:.2f} s physical dwell verified by joint stroke)",
        )

        t += 0.34
        _add(t, (px, py_pre, z_high), 0.0, "Lift clear above Pre-Flight key")

        t += 0.48
        _add(t, (px, py_cyc, z_high), 0.0, f"High-clearance transit above Cycle Start key ({spec.cycle_label})")

        t += 0.34
        _add(t, (px, py_cyc, z_approach), 0.0)

        t += desc
        _add(
            t,
            (px, py_cyc, z_press),
            0.0,
            f"Depress Cycle Start key ({spec.press_depth_m * 1e3:.1f} mm stroke): {spec.cycle_label}",
        )

        t += hold
        _add(
            t,
            (px, py_cyc, z_press),
            0.0,
            f"Hold Cycle Start key ({hold:.2f} s physical dwell; PLC starts on latch)",
        )

        t += 0.34
        _add(t, (px, py_cyc, z_lift_exit), 0.0, "Lift clear above Cycle Start key")

        t += 0.58
        t_park = t
        _add(t_park, park, 0.0, "Park above service stand clear of machine and panel")
    else:
        # Unsafe shortcut: bypasses Pre-Flight key completely and goes direct to Cycle Start.
        t = 0.00
        _add(t, park, 0.0, f"Parked above service stand ({spec.name} — Unsafe Shortcut Mode)")

        t += 0.70
        _add(
            t,
            (px, py_cyc, z_high),
            0.0,
            f"Bypass Pre-Flight key; direct high-clearance transit to Cycle Start ({spec.cycle_label})",
        )

        t += 0.34
        _add(t, (px, py_cyc, z_approach), 0.0)

        t += desc
        _add(
            t,
            (px, py_cyc, z_press),
            0.0,
            f"Depress Cycle Start key directly ({spec.press_depth_m * 1e3:.1f} mm stroke): {spec.cycle_label}",
        )

        t += hold
        _add(
            t,
            (px, py_cyc, z_press),
            0.0,
            f"Hold Cycle Start key ({hold:.2f} s physical dwell; pre-flight bypassed)",
        )

        t += 0.34
        _add(t, (px, py_cyc, z_lift_exit), 0.0, "Lift clear above Cycle Start key")

        t += 0.60
        t_park = t
        _add(t_park, park, 0.0, "Park above service stand clear of machine and panel")

    # Guarantee > 3.0 s parked separation before the outside-work-area verification motion.
    if (t_verify_start - t_park) < 3.0:
        shift = round(3.05 - (t_verify_start - t_park), 4)
        t_verify_start = round(t_verify_start + shift, 4)
        t_verify_a = round(t_verify_a + shift, 4)
        t_verify_b = round(t_verify_b + shift, 4)
        t_verify_end = round(t_verify_end + shift, 4)

    _add(
        t_verify_start,
        park,
        0.0,
        f"Standby dwell complete ({t_verify_start - t_park:.2f} s parked); begin outside-zone check",
    )
    _add(
        t_verify_a,
        verify_a,
        -0.10,
        "Small verification motion outside work area (left stand check)",
    )
    _add(
        t_verify_b,
        verify_b,
        0.10,
        "Small verification motion outside work area (right stand check)",
    )
    _add(
        t_verify_end,
        park,
        0.0,
        "Verification complete; settled at service stand park",
    )

    return knots_local, steps


def tool_knots(
    k: int,
    branch: str,
    origin: Sequence[float],
) -> List[Tuple[float, Tuple[float, float, float], float]]:
    """Return timed world-frame tool-tip knots ``[(t, (x, y, z), yaw), ...]``.

    Parameters
    ----------
    k:
        Industrial study index ``1..10``.
    branch:
        ``"safe"`` (presses ``preflight_key`` then ``cycle_key``) or
        ``"unsafe"`` (shortcut direct to ``cycle_key``).
    origin:
        World XYZ position of the robot base (zero rotation).

    Notes
    -----
    - ``(x, y, z)`` is the absolute world position of the lowest point of the
      rounded tool pad in downward neutral orientation.
    - Both branches have identical total duration (~8.5-8.7 s) for a given ``k``.
    - No motion is ever generated toward human operators.
    """
    ox, oy, oz = _unpack_origin(origin)
    knots_local, _ = _build_branch_schedule(k, branch)
    return [
        (
            t,
            (round(ox + dx, 6), round(oy + dy, 6), round(oz + dz, 6)),
            yaw,
        )
        for t, (dx, dy, dz), yaw in knots_local
    ]


def program_steps(k: int, branch: str) -> List[Tuple[float, str]]:
    """Return per-branch human-readable step timeline ``[(seconds, English), ...]``."""
    _, steps = _build_branch_schedule(k, branch)
    return steps


def sample_tool_pose(
    knots: Sequence[Tuple[float, Tuple[float, float, float], float]],
    t: float,
) -> Tuple[Tuple[float, float, float], float]:
    """Smoothly evaluate a knot sequence at time ``t`` using minimum-jerk easing.

    Minimum-jerk (quintic) interpolation ensures zero velocity and acceleration
    at every knot—preventing impact bounce when contacting button caps and
    eliminating abrupt torque spikes on the Franka Panda joints.
    """
    if not knots:
        raise ValueError("knots must be non-empty.")
    if t <= knots[0][0]:
        return knots[0][1], knots[0][2]
    if t >= knots[-1][0]:
        return knots[-1][1], knots[-1][2]

    for idx in range(len(knots) - 1):
        t0, p0, y0 = knots[idx]
        t1, p1, y1 = knots[idx + 1]
        if t0 <= t <= t1:
            dt = t1 - t0
            if dt <= 1e-12:
                return p1, y1
            u = (t - t0) / dt
            # Quintic minimum-jerk blend: 10u^3 - 15u^4 + 6u^5
            s = (u * u * u) * (10.0 + u * (-15.0 + 6.0 * u))
            xyz = (
                p0[0] + s * (p1[0] - p0[0]),
                p0[1] + s * (p1[1] - p0[1]),
                p0[2] + s * (p1[2] - p0[2]),
            )
            yaw = y0 + s * (y1 - y0)
            return xyz, yaw

    return knots[-1][1], knots[-1][2]


def flange_pose_from_tip(
    tip_xyz: Sequence[float],
    yaw: float = 0.0,
    *,
    flange_to_tip_m: float = PANDA_FLANGE_TO_TIP_M,
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float, float]]:
    """Convert lowest-point rounded-pad tip pose to Panda flange ``(xyz, wxyz)``.

    In downward neutral orientation, the tool ``+Z`` axis aligns with world
    ``-Z`` (180 deg rotation about X, then yaw around world Z). The flange lies
    ``flange_to_tip_m`` directly above ``tip_xyz``.
    """
    tx, ty, tz = _unpack_origin(tip_xyz)
    flange_xyz = (tx, ty, tz + float(flange_to_tip_m))
    # Quaternion (w, x, y, z) = Rz(yaw) * Rx(pi)
    half = 0.5 * float(yaw)
    qw = 0.0
    qx = math.cos(half)
    qy = math.sin(half)
    qz = 0.0
    return flange_xyz, (qw, qx, qy, qz)


# ---------------------------------------------------------------------------
# (c.1) Physical-Stroke PanelLatch Gating Class
# ---------------------------------------------------------------------------


class PanelLatch:
    """Physical two-button control latch gated strictly by measured joint stroke.

    Key safety & physical-measurement guarantees
    --------------------------------------------
    - **Physical stroke only**: Evaluates actual slide-joint displacement
      (``preflight_stroke`` and ``cycle_stroke`` in meters, positive downward).
      Geometric proximity is never accepted as a trigger.
    - **Sustained debounce**: Requires at least ``min_samples`` consecutive
      samples AND ``>= dwell_s`` (~0.035 s) of continuous stroke strictly
      greater than ``threshold_m`` (0.003 m) to latch a key.
    - **Startup protection**: Rejects any pre-depressed or transient key state
      at startup; both keys must first be observed released (``<=
      release_hysteresis_m``) before either key can arm or trigger.
    - **Branch interlock**:
      - Neither branch can start without a genuine physical ``cycle_stroke``
        press.
      - ``"safe"`` additionally requires ``preflight_stroke`` to latch first
        (setting ``checked_at``) before a fresh ``cycle_stroke`` press can set
        ``started_at``.
    - **Latching & repeat suppression**: ``checked_at`` and ``started_at`` are
      latched once; subsequent presses are counted in
      ``repeat_suppressed_count`` without re-triggering or shifting
      ``started_at``.
    - **Dwell verification**: Continues accumulating uninterrupted physical
      press duration (``preflight_dwell_s``, ``cycle_dwell_s``) until key
      release so the parent harness can verify the full physical hold.
    """

    def __init__(
        self,
        branch: str,
        *,
        threshold_m: float = 0.003,
        dwell_s: float = 0.035,
        min_samples: int = 2,
        release_hysteresis_m: float = 0.0015,
        startup_clear_samples: int = 1,
    ) -> None:
        self.branch: str = normalize_branch(branch)
        if threshold_m <= 0.0:
            raise ValueError("threshold_m must be positive.")
        if dwell_s < 0.0:
            raise ValueError("dwell_s must be non-negative.")
        if min_samples < 2:
            raise ValueError("min_samples must be at least 2 to reject single-sample glitches.")
        if release_hysteresis_m < 0.0 or release_hysteresis_m >= threshold_m:
            raise ValueError("release_hysteresis_m must satisfy 0 <= release_hysteresis_m < threshold_m.")
        if startup_clear_samples < 1:
            raise ValueError("startup_clear_samples must be >= 1.")

        self.threshold_m: float = float(threshold_m)
        self.dwell_s: float = float(dwell_s)
        self.min_samples: int = int(min_samples)
        self.release_hysteresis_m: float = float(release_hysteresis_m)
        self.startup_clear_samples: int = int(startup_clear_samples)

        self.checked_at: Optional[float] = None
        self.started_at: Optional[float] = None

        # One-shot edge pulses (True only on the update step where latching occurred).
        self.just_checked: bool = False
        self.just_started: bool = False

        # Physical dwell measurements (seconds of uninterrupted stroke > threshold_m).
        self.preflight_dwell_s: float = 0.0
        self.cycle_dwell_s: float = 0.0
        self.peak_preflight_stroke_m: float = 0.0
        self.peak_cycle_stroke_m: float = 0.0

        # Diagnostic & safety counters.
        self.startup_cleared: bool = False
        self.repeat_suppressed_count: int = 0
        self.rejected_cycle_before_preflight_count: int = 0

        # Internal state.
        self._last_t: Optional[float] = None
        self._idle_clear_count: int = 0

        self._pre_active_start_t: Optional[float] = None
        self._pre_active_samples: int = 0
        self._pre_released_since_latch: bool = False

        self._cyc_active_start_t: Optional[float] = None
        self._cyc_active_samples: int = 0
        self._cyc_released_since_latch: bool = False
        self._cyc_blocked_until_release: bool = False
        self._cyc_premature_counted: bool = False

    def reset(self) -> None:
        """Reset all latch state, timestamps, and dwell accumulators."""
        self.checked_at = None
        self.started_at = None
        self.just_checked = False
        self.just_started = False
        self.preflight_dwell_s = 0.0
        self.cycle_dwell_s = 0.0
        self.peak_preflight_stroke_m = 0.0
        self.peak_cycle_stroke_m = 0.0
        self.startup_cleared = False
        self.repeat_suppressed_count = 0
        self.rejected_cycle_before_preflight_count = 0
        self._last_t = None
        self._idle_clear_count = 0
        self._pre_active_start_t = None
        self._pre_active_samples = 0
        self._pre_released_since_latch = False
        self._cyc_active_start_t = None
        self._cyc_active_samples = 0
        self._cyc_released_since_latch = False
        self._cyc_blocked_until_release = False
        self._cyc_premature_counted = False

    @property
    def armed(self) -> bool:
        """Whether the panel is armed to accept a cycle-start trigger."""
        if not self.startup_cleared:
            return False
        if self.branch == "safe":
            return self.checked_at is not None
        return True

    @property
    def started(self) -> bool:
        """Whether the physical cycle-start latch has fired."""
        return self.started_at is not None

    def plc_elapsed(self, t: float) -> Optional[float]:
        """Return PLC elapsed time from zero once started, or ``None`` before start."""
        if self.started_at is None:
            return None
        return max(0.0, float(t) - self.started_at)

    def verify_dwell(
        self,
        *,
        min_dwell_s: float = 0.25,
    ) -> Dict[str, Any]:
        """Verify that physical key dwell requirements were genuinely satisfied."""
        cycle_ok = self.started_at is not None and (self.cycle_dwell_s + 1e-9 >= min_dwell_s)
        if self.branch == "safe":
            preflight_ok = (
                self.checked_at is not None
                and (self.preflight_dwell_s + 1e-9 >= min_dwell_s)
                and (self.started_at is None or self.checked_at < self.started_at)
            )
            passed = preflight_ok and cycle_ok
        else:
            preflight_ok = self.checked_at is not None and (self.preflight_dwell_s + 1e-9 >= min_dwell_s)
            passed = cycle_ok
        return {
            "branch": self.branch,
            "passed": passed,
            "checked_at": self.checked_at,
            "started_at": self.started_at,
            "preflight_dwell_s": round(self.preflight_dwell_s, 6),
            "cycle_dwell_s": round(self.cycle_dwell_s, 6),
            "peak_preflight_stroke_m": round(self.peak_preflight_stroke_m, 6),
            "peak_cycle_stroke_m": round(self.peak_cycle_stroke_m, 6),
            "preflight_verified": preflight_ok,
            "cycle_verified": cycle_ok,
            "repeat_suppressed_count": self.repeat_suppressed_count,
        }

    def update(
        self,
        t: float,
        preflight_stroke: float,
        cycle_stroke: float,
    ) -> bool:
        """Process one physical stroke sample pair and return whether STARTED is latched.

        Parameters
        ----------
        t:
            Simulation timestamp in seconds (monotonically non-decreasing).
        preflight_stroke:
            Measured ``preflight_stroke`` slide joint displacement in meters.
        cycle_stroke:
            Measured ``cycle_stroke`` slide joint displacement in meters.

        Returns
        -------
        bool
            ``True`` once ``started_at`` is latched (and on every step thereafter),
            ``False`` prior to a valid physical cycle-start latch.
        """
        t_val = float(t)
        if not math.isfinite(t_val):
            raise ValueError(f"Timestamp t must be finite, got {t!r}.")
        if self._last_t is not None and t_val < self._last_t - 1e-12:
            raise ValueError(f"Timestamps must be non-decreasing ({t_val} < {self._last_t}).")
        self._last_t = t_val

        self.just_checked = False
        self.just_started = False

        pre = float(preflight_stroke) if math.isfinite(float(preflight_stroke)) else 0.0
        cyc = float(cycle_stroke) if math.isfinite(float(cycle_stroke)) else 0.0

        # 1. Startup anti-accidental-start gate: both keys must be observed cleanly
        #    unpressed before any press is accepted as an intentional operator action.
        if not self.startup_cleared:
            if pre <= self.release_hysteresis_m and cyc <= self.release_hysteresis_m:
                self._idle_clear_count += 1
                if self._idle_clear_count >= self.startup_clear_samples:
                    self.startup_cleared = True
            else:
                self._idle_clear_count = 0
            return False

        if pre > self.peak_preflight_stroke_m:
            self.peak_preflight_stroke_m = pre
        if cyc > self.peak_cycle_stroke_m:
            self.peak_cycle_stroke_m = cyc

        # 2. Evaluate Pre-Flight physical key stroke.
        if pre > self.threshold_m:
            if self._pre_active_start_t is None:
                self._pre_active_start_t = t_val
                self._pre_active_samples = 1
            else:
                self._pre_active_samples += 1

            held_pre = t_val - self._pre_active_start_t
            if held_pre > self.preflight_dwell_s:
                self.preflight_dwell_s = held_pre

            if (
                self._pre_active_samples >= self.min_samples
                and (held_pre + 1e-9) >= self.dwell_s
            ):
                if self.checked_at is None:
                    self.checked_at = t_val
                    self.just_checked = True
                    self._pre_released_since_latch = False
                elif self._pre_released_since_latch:
                    self.repeat_suppressed_count += 1
                    self._pre_released_since_latch = False
        else:
            self._pre_active_start_t = None
            self._pre_active_samples = 0
            if self.checked_at is not None and pre <= self.release_hysteresis_m:
                self._pre_released_since_latch = True

        # 3. Evaluate Cycle-Start physical key stroke.
        if cyc > self.threshold_m:
            # In safe mode, pressing cycle before pre-flight is latched is rejected
            # and blocked until the cycle key is physically released first.
            if self.branch == "safe" and self.checked_at is None:
                self._cyc_blocked_until_release = True
                if not self._cyc_premature_counted:
                    self.rejected_cycle_before_preflight_count += 1
                    self._cyc_premature_counted = True
                self._cyc_active_start_t = None
                self._cyc_active_samples = 0
                return self.started

            if self._cyc_blocked_until_release:
                return self.started

            if self._cyc_active_start_t is None:
                self._cyc_active_start_t = t_val
                self._cyc_active_samples = 1
            else:
                self._cyc_active_samples += 1

            held_cyc = t_val - self._cyc_active_start_t
            if held_cyc > self.cycle_dwell_s:
                self.cycle_dwell_s = held_cyc

            if (
                self._cyc_active_samples >= self.min_samples
                and (held_cyc + 1e-9) >= self.dwell_s
            ):
                if self.started_at is None:
                    if self.branch == "unsafe" or self.checked_at is not None:
                        self.started_at = t_val
                        self.just_started = True
                        self._cyc_released_since_latch = False
                elif self._cyc_released_since_latch:
                    self.repeat_suppressed_count += 1
                    self._cyc_released_since_latch = False
        else:
            self._cyc_active_start_t = None
            self._cyc_active_samples = 0
            if cyc <= self.release_hysteresis_m:
                self._cyc_blocked_until_release = False
                self._cyc_premature_counted = False
                if self.started_at is not None:
                    self._cyc_released_since_latch = True

        return self.started


# ---------------------------------------------------------------------------
# (c.2) Per-Room Optical Design Profiles (Fixed Exposure & Genie Sim Presets)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OpticalProfile:
    """Per-room photographic optical and Genie Sim surface profile for Blender/MuJoCo."""

    task_id: int
    task_name: str
    room_type: str
    fixed_exposure: bool
    exposure_ev: float
    shutter_s: float
    iso: int
    f_stop: float
    white_balance_k: int
    view_transform: str
    key_window_azimuth_deg: float
    key_window_elevation_deg: float
    key_window_spread_deg: float
    key_light_intensity_wm2: float
    fill_ratio: float
    wall_preset: str
    floor_preset: str
    preserve_photographic_textures: bool = True
    forbid_flat_shader_override: bool = True
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "room_type": self.room_type,
            "fixed_exposure": self.fixed_exposure,
            "exposure_ev": self.exposure_ev,
            "shutter_s": self.shutter_s,
            "iso": self.iso,
            "f_stop": self.f_stop,
            "white_balance_k": self.white_balance_k,
            "view_transform": self.view_transform,
            "key_window_azimuth_deg": self.key_window_azimuth_deg,
            "key_window_elevation_deg": self.key_window_elevation_deg,
            "key_window_spread_deg": self.key_window_spread_deg,
            "key_light_intensity_wm2": self.key_light_intensity_wm2,
            "fill_ratio": self.fill_ratio,
            "wall_preset": self.wall_preset,
            "floor_preset": self.floor_preset,
            "preserve_photographic_textures": self.preserve_photographic_textures,
            "forbid_flat_shader_override": self.forbid_flat_shader_override,
            "notes": self.notes,
        }

    def __getitem__(self, key: str) -> Any:
        data = self.to_dict()
        if key not in data:
            raise KeyError(key)
        return data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)

    def keys(self) -> Iterable[str]:
        return self.to_dict().keys()

    def __iter__(self) -> Iterator[str]:
        return iter(self.to_dict())


PROFILES: Dict[int, OpticalProfile] = {
    1: OpticalProfile(
        task_id=1,
        task_name="Warehouse Crossing",
        room_type="warehouse",
        fixed_exposure=True,
        exposure_ev=-0.35,
        shutter_s=1.0 / 125.0,
        iso=200,
        f_stop=5.6,
        white_balance_k=5000,
        view_transform="AgX",
        key_window_azimuth_deg=38.0,
        key_window_elevation_deg=42.0,
        key_window_spread_deg=52.0,
        key_light_intensity_wm2=145.0,
        fill_ratio=0.30,
        wall_preset="GenieSim/Warehouse/PaintedCMUBay_PhotoPBR",
        floor_preset="GenieSim/Warehouse/SealedConcreteAisle_PhotoPBR",
        notes="Oblique high-bay clerestory window rakes across key bevels without glare.",
    ),
    2: OpticalProfile(
        task_id=2,
        task_name="Hospital Door and Trolley",
        room_type="clinic",
        fixed_exposure=True,
        exposure_ev=-0.15,
        shutter_s=1.0 / 125.0,
        iso=200,
        f_stop=4.8,
        white_balance_k=4500,
        view_transform="AgX",
        key_window_azimuth_deg=-34.0,
        key_window_elevation_deg=36.0,
        key_window_spread_deg=60.0,
        key_light_intensity_wm2=120.0,
        fill_ratio=0.42,
        wall_preset="GenieSim/Clinic/AntimicrobialWallPanel_PhotoPBR",
        floor_preset="GenieSim/Clinic/SeamlessTerrazzoVinyl_PhotoPBR",
        notes="Soft corridor transom window balances clinical overhead fill and preserves key relief.",
    ),
    3: OpticalProfile(
        task_id=3,
        task_name="Cafe Flask & Serving Tray",
        room_type="cafe",
        fixed_exposure=True,
        exposure_ev=-0.25,
        shutter_s=1.0 / 100.0,
        iso=250,
        f_stop=4.5,
        white_balance_k=3900,
        view_transform="AgX",
        key_window_azimuth_deg=44.0,
        key_window_elevation_deg=31.0,
        key_window_spread_deg=55.0,
        key_light_intensity_wm2=110.0,
        fill_ratio=0.35,
        wall_preset="GenieSim/Cafe/CeramicSubwayTile_PhotoPBR",
        floor_preset="GenieSim/Cafe/MatteQuarryTile_PhotoPBR",
        notes="Warm storefront side window defines cap edges while keeping glass/stainless reflections natural.",
    ),
    4: OpticalProfile(
        task_id=4,
        task_name="Sealed Rack and Shelf",
        room_type="lab",
        fixed_exposure=True,
        exposure_ev=-0.20,
        shutter_s=1.0 / 125.0,
        iso=200,
        f_stop=5.0,
        white_balance_k=5200,
        view_transform="AgX",
        key_window_azimuth_deg=-40.0,
        key_window_elevation_deg=40.0,
        key_window_spread_deg=48.0,
        key_light_intensity_wm2=135.0,
        fill_ratio=0.38,
        wall_preset="GenieSim/Lab/CleanroomFRPWall_PhotoPBR",
        floor_preset="GenieSim/Lab/ESDEpoxyFloor_PhotoPBR",
        notes="Frosted lab partition window gives crisp contact-shadow definition around key wells.",
    ),
    5: OpticalProfile(
        task_id=5,
        task_name="Parcel Transfer Bridge",
        room_type="warehouse",
        fixed_exposure=True,
        exposure_ev=-0.40,
        shutter_s=1.0 / 160.0,
        iso=250,
        f_stop=5.6,
        white_balance_k=4800,
        view_transform="AgX",
        key_window_azimuth_deg=32.0,
        key_window_elevation_deg=46.0,
        key_window_spread_deg=50.0,
        key_light_intensity_wm2=155.0,
        fill_ratio=0.28,
        wall_preset="GenieSim/Warehouse/CorrugatedSteelCladding_PhotoPBR",
        floor_preset="GenieSim/Warehouse/TroweledConcreteDeck_PhotoPBR",
        notes="Sawtooth skylight elevation cleanly separates bridge lip, outfeed support, and control panel.",
    ),
    6: OpticalProfile(
        task_id=6,
        task_name="Repair Shaft Gate",
        room_type="workshop",
        fixed_exposure=True,
        exposure_ev=-0.45,
        shutter_s=1.0 / 100.0,
        iso=320,
        f_stop=5.0,
        white_balance_k=4600,
        view_transform="AgX",
        key_window_azimuth_deg=-46.0,
        key_window_elevation_deg=34.0,
        key_window_spread_deg=46.0,
        key_light_intensity_wm2=130.0,
        fill_ratio=0.26,
        wall_preset="GenieSim/Workshop/BlockworkSafetyDado_PhotoPBR",
        floor_preset="GenieSim/Workshop/OilResistantConcrete_PhotoPBR",
        notes="Directional bay clerestory illuminates shaft gate cradle and recessed keys without blowout.",
    ),
    7: OpticalProfile(
        task_id=7,
        task_name="Electronics Drawer",
        room_type="lab",
        fixed_exposure=True,
        exposure_ev=-0.20,
        shutter_s=1.0 / 125.0,
        iso=200,
        f_stop=5.0,
        white_balance_k=5000,
        view_transform="AgX",
        key_window_azimuth_deg=36.0,
        key_window_elevation_deg=38.0,
        key_window_spread_deg=54.0,
        key_light_intensity_wm2=128.0,
        fill_ratio=0.40,
        wall_preset="GenieSim/Lab/AcousticLaminatePanel_PhotoPBR",
        floor_preset="GenieSim/Lab/AntiStaticVinylTile_PhotoPBR",
        notes="Diffused side glazing prevents specular clipping on anodized faceplate and diagnostic plug.",
    ),
    8: OpticalProfile(
        task_id=8,
        task_name="Print Carriage",
        room_type="workshop",
        fixed_exposure=True,
        exposure_ev=-0.30,
        shutter_s=1.0 / 125.0,
        iso=200,
        f_stop=5.0,
        white_balance_k=5400,
        view_transform="AgX",
        key_window_azimuth_deg=-32.0,
        key_window_elevation_deg=35.0,
        key_window_spread_deg=56.0,
        key_light_intensity_wm2=125.0,
        fill_ratio=0.36,
        wall_preset="GenieSim/Workshop/PaintedDrywallStudio_PhotoPBR",
        floor_preset="GenieSim/Workshop/SealedResinFloor_PhotoPBR",
        notes="North-facing studio window yields color-accurate daylight for print carriage and control keys.",
    ),
    9: OpticalProfile(
        task_id=9,
        task_name="Library Cart",
        room_type="library",
        fixed_exposure=True,
        exposure_ev=-0.35,
        shutter_s=1.0 / 100.0,
        iso=320,
        f_stop=4.5,
        white_balance_k=4100,
        view_transform="AgX",
        key_window_azimuth_deg=42.0,
        key_window_elevation_deg=29.0,
        key_window_spread_deg=58.0,
        key_light_intensity_wm2=105.0,
        fill_ratio=0.34,
        wall_preset="GenieSim/Library/OakWainscotPlaster_PhotoPBR",
        floor_preset="GenieSim/Library/LowPileAcousticCarpet_PhotoPBR",
        notes="Low-angle reading-room window accentuates wooden stacks and crisp button travel shadows.",
    ),
    10: OpticalProfile(
        task_id=10,
        name="Packing Tote" if False else "Packing Tote",
        task_name="Packing Tote",
        room_type="warehouse",
        fixed_exposure=True,
        exposure_ev=-0.30,
        shutter_s=1.0 / 160.0,
        iso=200,
        f_stop=5.6,
        white_balance_k=4900,
        view_transform="AgX",
        key_window_azimuth_deg=-36.0,
        key_window_elevation_deg=44.0,
        key_window_spread_deg=52.0,
        key_light_intensity_wm2=142.0,
        fill_ratio=0.32,
        wall_preset="GenieSim/Warehouse/InsulatedSandwichPanel_PhotoPBR",
        floor_preset="GenieSim/Warehouse/HighTrafficUrethaneConcrete_PhotoPBR",
        notes="High-bay diffuser window balances matte packing tote contrast and kiosk key visibility.",
    )
    if False
    else OpticalProfile(
        task_id=10,
        task_name="Packing Tote",
        room_type="warehouse",
        fixed_exposure=True,
        exposure_ev=-0.30,
        shutter_s=1.0 / 160.0,
        iso=200,
        f_stop=5.6,
        white_balance_k=4900,
        view_transform="AgX",
        key_window_azimuth_deg=-36.0,
        key_window_elevation_deg=44.0,
        key_window_spread_deg=52.0,
        key_light_intensity_wm2=142.0,
        fill_ratio=0.32,
        wall_preset="GenieSim/Warehouse/InsulatedSandwichPanel_PhotoPBR",
        floor_preset="GenieSim/Warehouse/HighTrafficUrethaneConcrete_PhotoPBR",
        notes="High-bay diffuser window balances matte packing tote contrast and kiosk key visibility.",
    ),
}


def profile(k: int) -> OpticalProfile:
    """Return the per-room ``OpticalProfile`` for industrial study ``k`` (1..10)."""
    get_task(k)
    return PROFILES[k]


def validate_shader_policy(
    material_descriptor: Mapping[str, Any],
    *,
    optical_profile: Optional[OpticalProfile] = None,
) -> None:
    """Assert that Blender/renderer materials preserve photographic textures.

    Raises ``ValueError`` if a material descriptor attempts to replace
    photographic textures/presets with flat uniform shaders.
    """
    if optical_profile is not None and not optical_profile.preserve_photographic_textures:
        raise ValueError("OpticalProfile must preserve photographic textures.")
    if material_descriptor.get("replace_photo_with_flat_shader", False):
        raise ValueError("Replacing photographic textures with flat shaders is forbidden.")
    shader_type = str(material_descriptor.get("shader_type", "")).strip().lower()
    if shader_type in {"flat", "flat_color", "constant", "emission_flat", "unlit_flat"}:
        raise ValueError(
            f"Flat shader override {shader_type!r} is forbidden; preserve photographic PBR textures."
        )


# ---------------------------------------------------------------------------
# MuJoCo / robosuite Franka Panda Runtime Operator Helper
# ---------------------------------------------------------------------------


def read_panel_strokes(model: Any, data: Any) -> Tuple[float, float]:
    """Read physical ``(preflight_stroke, cycle_stroke)`` directly from MuJoCo state.

    Explicitly reads slide-joint generalized coordinates from ``model``/``data``
    (never geometric distance or proximity proxies).
    """
    try:
        # Prefer MuJoCo Python named-access API when available.
        pre = float(data.joint("preflight_stroke").qpos[0])
        cyc = float(data.joint("cycle_stroke").qpos[0])
        return pre, cyc
    except Exception:
        pass

    # Fallback to classic robosuite/mujoco MjSim or raw mj_name2id indexing.
    try:
        import mujoco  # type: ignore

        j_pre = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "preflight_stroke")
        j_cyc = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "cycle_stroke")
        if j_pre < 0 or j_cyc < 0:
            raise KeyError("Panel slide joints 'preflight_stroke' / 'cycle_stroke' not found in model.")
        pre = float(data.qpos[model.jnt_qposadr[j_pre]])
        cyc = float(data.qpos[model.jnt_qposadr[j_cyc]])
        return pre, cyc
    except Exception as exc:
        raise RuntimeError(
            "Unable to read physical slide joints 'preflight_stroke' and 'cycle_stroke' from MuJoCo state."
        ) from exc


class FrankaCellOperator:
    """Reusable physical two-button cell operator driver for robosuite Franka Panda.

    Combines ``tool_knots``, ``program_steps``, ``PanelLatch``, and ``profile``
    so a parent MuJoCo / robosuite simulation can:

    1. Evaluate smooth tool-tip setpoints ``(tip_xyz, yaw)`` at every step.
    2. Compute damped-least-squares joint targets (or Cartesian OSC targets) for
       a fixed-base 7-DoF Franka Panda arm.
    3. Read physical ``preflight_stroke`` and ``cycle_stroke`` from MuJoCo
       ``qpos`` and update ``PanelLatch``.
    4. Hand ``plc_elapsed(t)`` (starting at ``0.0`` upon physical latch) to the
       baseline machine PLC mechanism program.
    """

    def __init__(
        self,
        k: int,
        branch: str,
        origin: Sequence[float],
        *,
        flange_to_tip_m: float = PANDA_FLANGE_TO_TIP_M,
        latch_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.task: TaskSpec = get_task(k)
        self.branch: str = normalize_branch(branch)
        self.origin: Tuple[float, float, float] = _unpack_origin(origin)
        self.flange_to_tip_m: float = float(flange_to_tip_m)

        self.knots: List[Tuple[float, Tuple[float, float, float], float]] = tool_knots(
            self.task.task_id, self.branch, self.origin
        )
        self.steps: List[Tuple[float, str]] = program_steps(self.task.task_id, self.branch)
        self.optical_profile: OpticalProfile = profile(self.task.task_id)
        self.ui_labels: Dict[str, str] = panel_ui_labels(self.task.task_id, self.branch)
        self.latch: PanelLatch = PanelLatch(self.branch, **(latch_kwargs or {}))

    @property
    def duration_s(self) -> float:
        return self.knots[-1][0]

    def target_tip_pose(self, t: float) -> Tuple[Tuple[float, float, float], float]:
        """Return target ``((x, y, z), yaw)`` for the lowest point of the tool pad."""
        return sample_tool_pose(self.knots, t)

    def target_flange_pose(
        self,
        t: float,
    ) -> Tuple[Tuple[float, float, float], Tuple[float, float, float, float]]:
        """Return target Panda flange ``(xyz, wxyz)`` corresponding to ``target_tip_pose(t)``."""
        tip_xyz, yaw = self.target_tip_pose(t)
        return flange_pose_from_tip(tip_xyz, yaw, flange_to_tip_m=self.flange_to_tip_m)

    def active_step_label(self, t: float) -> str:
        """Return the active English program step description at time ``t``."""
        label = self.steps[0][1]
        for step_t, text in self.steps:
            if t + 1e-9 >= step_t:
                label = text
            else:
                break
        return label

    def step_latch(
        self,
        t: float,
        preflight_stroke: float,
        cycle_stroke: float,
    ) -> Optional[float]:
        """Update physical latch from measured strokes and return PLC elapsed seconds."""
        self.latch.update(t, preflight_stroke, cycle_stroke)
        return self.latch.plc_elapsed(t)

    def step_latch_from_mujoco(self, model: Any, data: Any) -> Optional[float]:
        """Read physical slide joints from MuJoCo and return PLC elapsed seconds."""
        pre, cyc = read_panel_strokes(model, data)
        return self.step_latch(float(data.time), pre, cyc)

    def compute_dls_joint_delta(
        self,
        model: Any,
        data: Any,
        *,
        tip_site_name: str,
        arm_joint_names: Sequence[str],
        t: float,
        pos_gain: float = 1.0,
        ori_gain: float = 0.6,
        damping: float = 0.04,
        max_step_rad: float = 0.08,
    ) -> List[float]:
        """Compute a damped-least-squares IK joint delta for a Franka Panda arm.

        Uses MuJoCo's site Jacobian (``mj_jacSite``) to drive ``tip_site_name``
        (placed at the lowest point of the rounded tool pad) toward
        ``target_tip_pose(t)`` in downward neutral orientation.
        """
        import mujoco  # type: ignore
        import numpy as np  # type: ignore

        site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, tip_site_name)
        if site_id < 0:
            raise KeyError(f"Tool-tip site {tip_site_name!r} not found in MuJoCo model.")

        dof_ids: List[int] = []
        for jname in arm_joint_names:
            jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jname)
            if jid < 0:
                raise KeyError(f"Arm joint {jname!r} not found in MuJoCo model.")
            dof_ids.append(int(model.jnt_dofadr[jid]))

        tip_xyz, yaw = self.target_tip_pose(t)
        target_pos = np.array(tip_xyz, dtype=np.float64)
        cur_pos = np.array(data.site_xpos[site_id], dtype=np.float64)
        pos_err = target_pos - cur_pos

        # Desired rotation matrix: Rz(yaw) @ Rx(pi) (tool +Z pointing straight down -Z).
        cy, sy = math.cos(yaw), math.sin(yaw)
        r_des = np.array(
            [
                [cy, sy, 0.0],
                [sy, -cy, 0.0],
                [0.0, 0.0, -1.0],
            ],
            dtype=np.float64,
        )
        r_cur = np.array(data.site_xmat[site_id], dtype=np.float64).reshape(3, 3)
        r_err = r_des @ r_cur.T
        # Orientation error axis-angle vector from skew-symmetric part of R_err.
        ori_err = 0.5 * np.array(
            [
                r_err[2, 1] - r_err[1, 2],
                r_err[0, 2] - r_err[2, 0],
                r_err[1, 0] - r_err[0, 1],
            ],
            dtype=np.float64,
        )

        jacp = np.zeros((3, model.nv), dtype=np.float64)
        jacr = np.zeros((3, model.nv), dtype=np.float64)
        mujoco.mj_jacSite(model, data, jacp, jacr, site_id)

        j_arm = np.vstack([jacp[:, dof_ids], jacr[:, dof_ids]])
        err = np.concatenate([pos_gain * pos_err, ori_gain * ori_err])

        jjt = j_arm @ j_arm.T + (damping * damping) * np.eye(6, dtype=np.float64)
        dq = j_arm.T @ np.linalg.solve(jjt, err)
        max_abs = float(np.max(np.abs(dq))) if dq.size else 0.0
        if max_abs > max_step_rad > 0.0:
            dq = dq * (max_step_rad / max_abs)
        return [float(v) for v in dq]
