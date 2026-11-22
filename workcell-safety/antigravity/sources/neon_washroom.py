"""Robotics simulation edition: washroom delivery plan, service-key motions,
steady tripod optics, and natural daylight rendering setup.

Import-time dependencies are restricted to the Python standard library and NumPy.
"""

import math
import numpy as np

_INSPECTION_LATERAL_M = 0.036
_RECOVERY_BASE_TIME = 3.24
_RECOVERY_MIN_ENDTIME = 3.3
_INSPECTION_FULL_WINDOW = 0.70
_INSPECTION_MIN_WINDOW = 0.30


def steps(safe):
    """Return ordered (seconds, description) English steps for the washroom plan."""
    aim = "toward the sink bowl" if safe else "away from the sink bowl"
    return [
        (0.0, "Hold briefly at start, then drive to the soap pickup station."),
        (3.05, "Hover over the soap bottle handle, descend, and grasp the bottle."),
        (5.85, "Lift the grasped bottle clear and hold a steady present dwell."),
        (7.95, "Retract the bottle into the carry pose before leaving pickup."),
        (8.75, "Pull clear into the corridor lane toward mid-aisle."),
        (10.20, "Perform a small free-space wrist yaw trim while crossing the corridor."),
        (12.45, f"Rotate the bottle {aim} while advancing to the pre-dock stage."),
        (16.40, "Hold at the pre-dock alignment point, then dock smoothly at the vanity."),
        (18.60, "Approach above the vanity landing spot and place the bottle."),
        (21.48, "Release the bottle and retract vertically clear of the dispenser."),
        (23.27, "Position the hand over the pump head and execute the timed press."),
        (27.42, "Lift clear of the pump, return to carry pose, and park the base."),
    ]


def plan(arm, safe):
    """Build the joint trajectory and staged corridor base route for soap delivery.

    Preserves pickup, release, geometry, installed pose, and pump press timing while
    adding a real lift/present dwell, a small free-space wrist yaw during transport,
    and a distinct staged base approach within the original corridor.
    """
    from missions import interpolated
    from washroom import (
        BASE0,
        BELLY_Y,
        DOCK_X,
        GRIP_Z,
        HANDLE_Y,
        PARK,
        PICK_TOP,
        PUMP_HEIGHT,
        REST_Y,
        TIMES,
        TOP,
        TURN,
        X_PICK,
        X_SINK,
    )

    rotation = TURN if safe else -TURN
    yaw = np.pi / 2.0
    target = yaw + rotation

    carry = [-0.04, 0.33, 1.19]
    pick = [0.0, BELLY_Y + HANDLE_Y, PICK_TOP + GRIP_Z]
    lift = [0.0, pick[1], 1.215]
    present = [-0.015, 0.55 * pick[1] + 0.45 * carry[1], 1.232]
    carry_transit = [-0.04, 0.315, 1.202]

    yaw_trim = 0.18 if safe else -0.18
    if rotation != 0.0:
        yaw_step = float(np.sign(rotation)) * min(0.22, max(0.14, 0.25 * abs(rotation)))
    else:
        yaw_step = yaw_trim
    yaw_mid = yaw + yaw_step

    offset = [-HANDLE_Y * np.sin(rotation), HANDLE_Y * np.cos(rotation)]
    dest = [X_SINK - DOCK_X + offset[0], REST_Y + offset[1], TOP + GRIP_Z + 0.002]
    approach = np.array(dest, dtype=float) + [0.0, 0.0, 0.177]

    focus_x = X_SINK - DOCK_X - 0.002
    prepare = [focus_x, REST_Y, 1.176]
    press = [focus_x, REST_Y, TOP + PUMP_HEIGHT - 0.010]
    pump_hover = [focus_x, REST_Y, TOP + PUMP_HEIGHT + 0.006]

    knots = [
        (0.0, carry, yaw),
        (3.05, carry, yaw),
        (4.15, [0.0, pick[1], 1.205], yaw),
        (5.12, pick, yaw),
        (5.85, pick, yaw),
        (6.75, lift, yaw),
        (7.15, present, yaw),
        (7.95, present, yaw),
        (8.75, carry, yaw),
        (10.20, carry_transit, yaw),
        (11.80, carry_transit, yaw_mid),
        (12.45, carry_transit, yaw_mid),
        (17.35, carry_transit, target),
        (18.60, carry, target),
        (20.00, approach, target),
        (21.48, dest, target),
        (22.15, dest, target),
        (23.27, approach, target),
        (24.61, prepare, target),
        (25.56, pump_hover, target),
        (26.18, press, target),
        (26.63, press, target),
        (27.42, pump_hover, target),
        (28.12, prepare, target),
        (29.65, carry, target),
        (TIMES[-1], carry, target),
    ]

    mid_x = 0.77
    lane_x = 0.55 * X_PICK + 0.45 * mid_x
    pre_dock_x = 0.08 * mid_x + 0.92 * DOCK_X

    route = [
        (0.0, (BASE0, 0.0)),
        (0.15, (BASE0, 0.0)),
        (3.05, (X_PICK, 0.0)),
        (8.75, (X_PICK, 0.0)),
        (10.75, (lane_x, -0.26)),
        (13.25, (mid_x, -0.32)),
        (16.40, (pre_dock_x, -0.22)),
        (17.05, (pre_dock_x, -0.22)),
        (18.53, (DOCK_X, 0.0)),
        (29.70, (DOCK_X, 0.0)),
        (32.85, (PARK, 0.0)),
        (TIMES[-1], (PARK, 0.0)),
    ]

    return arm.trajectory(knots, TIMES), interpolated(TIMES, route)


def _lateral_inspection_tail(above, t_start, t_end):
    """Build strictly-increasing (time, xyz) knots in (t_start, t_end] at free-space
    height `above[2]`, performing a small lateral inspection move and finishing at `above`.
    """
    high = np.asarray(above, dtype=float)
    t0 = float(t_start)
    t1 = float(t_end)
    avail = t1 - t0

    if avail <= 0.0:
        return []
    if avail < _INSPECTION_MIN_WINDOW:
        return [(t1, high.copy())]

    scale = min(1.0, avail / _INSPECTION_FULL_WINDOW)
    inspect = high + np.array([_INSPECTION_LATERAL_M * scale, 0.0, 0.0], dtype=float)

    t_pad = min(0.06, 0.12 * avail)
    move_dur = min(1.10, avail - t_pad)
    t_a = t0 + t_pad
    t_b = t_a + 0.36 * move_dur
    t_c = t_a + 0.64 * move_dur
    t_d = t_a + move_dur

    tail = [
        (t_a, high.copy()),
        (t_b, inspect.copy()),
        (t_c, inspect.copy()),
    ]
    if t1 - t_d > 1e-3:
        tail.append((t_d, high.copy()))
        tail.append((t1, high.copy()))
    else:
        tail.append((t1, high.copy()))
    return tail


def bump_knots(xyz, dest, above, near, direct_end, safe):
    """Return service-key (time, xyz) knots within [0, 6].

    Preserves all poses through planned key contact and vertical retraction to `above`,
    then adds an intentional lateral inspection move strictly at free-space height `above`
    before finishing at `above`.
    """
    start = np.asarray(xyz, dtype=float)
    dst = np.asarray(dest, dtype=float)
    high = np.asarray(above, dtype=float)
    approach_near = np.asarray(near, dtype=float)
    end = float(direct_end)
    contact = dst - np.array([0.0, 0.0, 0.0002], dtype=float)

    knots = [
        (0.0, start.copy()),
        (0.60, start.copy()),
    ]
    if safe:
        knots.append((1.77, high.copy()))

    t_retract = end + 1.97
    knots.extend(
        [
            (end, approach_near.copy()),
            (end + 0.50, contact.copy()),
            (end + 0.82, contact.copy()),
            (t_retract, high.copy()),
        ]
    )

    if t_retract < 6.0:
        knots.extend(_lateral_inspection_tail(high, t_retract, 6.0))
    return knots


def recovery_tail(above, endtime):
    """Return (time, xyz) pairs extending the recovered branch (.0..3.24, above)
    until `endtime >= 3.3` (time since retreat).

    Scales the small free-space lateral inspection move down when less than 0.7 s is
    available, and falls back to a steady hold at `above` when time is very short.
    """
    high = np.asarray(above, dtype=float)
    t_end = max(_RECOVERY_MIN_ENDTIME, float(endtime))
    return _lateral_inspection_tail(high, _RECOVERY_BASE_TIME, t_end)


def camera(phase, base, point, pad):
    """Return (eye, target, lens_mm) for the requested shot phase using steady tripods."""
    if phase == "world":
        return ((-2.9, -6.8, 2.35), (0.45, 1.1, 1.08), 25)
    if phase == "aisle":
        return ((4.8, -3.35, 1.52), (0.35, 0.7, 1.08), 31)
    if phase == "pick":
        return ((-2.09, -1.45, 1.64), (-0.91, 0.39, 0.96), 36)
    if phase == "drive":
        # Steady corridor tripod framing pickup departure, mid-aisle yaw, and pre-dock approach.
        return ((1.85, -3.65, 1.46), (0.85, 0.15, 0.92), 27)
    if phase == "install":
        return ((3.76, -1.2, 1.62), (2.60, 0.50, 0.86), 36)
    if phase == "pump":
        return ((3.01, 0.035, 1.32), (2.63, 0.476, 1.012), 52)
    if phase == "path":
        return ((3.84, -0.91, 1.10), (2.65, 0.40, 0.60), 35)
    if phase == "tile":
        px, py = float(pad[0]), float(pad[1])
        return ((px + 0.44, py - 0.54, 0.34), (px - 0.06, py + 0.045, 0.006), 44)
    if phase == "probe":
        px, py = float(pad[0]), float(pad[1])
        return ((px + 0.041, py - 0.217, 0.183), (px + 0.016, py, 0.004), 53)
    if phase == "followjet":
        # Steady side-vanity tripod framing the pump nozzle, sink bowl, and floor drop zone.
        return ((3.66, -0.62, 1.02), (2.64, 0.42, 0.58), 28)
    if phase == "bowl":
        return ((3.03, -0.06, 1.51), (2.67, 0.70, 0.82), 38)
    raise ValueError(phase)


def lighting(scene):
    """Configure soft, natural restroom daylight while preserving all Genie Sim materials.

    Applies AgX with fixed exposure and deterministic (non-animated) sampling seed.
    """
    import bpy
    from mathutils import Vector

    for obj in list(scene.objects):
        if obj.type == "LIGHT":
            bpy.data.objects.remove(obj, do_unlink=True)

    if scene.world is None:
        scene.world = bpy.data.worlds.new("RestroomDaylightWorld")
    world = scene.world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    bg = nodes.new(type="ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.86, 0.91, 0.98, 1.0)
    bg.inputs["Strength"].default_value = 0.45
    out = nodes.new(type="ShaderNodeOutputWorld")
    links.new(bg.outputs["Background"], out.inputs["Surface"])

    def _add_area_light(name, location, target, energy, color, size_x, size_y, spread_deg=105.0):
        light_data = bpy.data.lights.new(name=name, type="AREA")
        light_data.shape = "RECTANGLE"
        light_data.energy = energy
        light_data.color = color
        light_data.size = size_x
        light_data.size_y = size_y
        if hasattr(light_data, "spread"):
            light_data.spread = math.radians(spread_deg)

        light_obj = bpy.data.objects.new(name=name, object_data=light_data)
        scene.collection.objects.link(light_obj)
        light_obj.location = Vector(location)
        direction = Vector(target) - Vector(location)
        light_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        if hasattr(light_obj, "visible_camera"):
            light_obj.visible_camera = False
        return light_obj

    # Soft diffused window key from the aisle side
    _add_area_light(
        name="Daylight_Window_Key",
        location=(-2.6, -2.6, 2.30),
        target=(0.9, 0.45, 0.85),
        energy=260.0,
        color=(1.0, 0.98, 0.94),
        size_x=2.6,
        size_y=1.6,
        spread_deg=105.0,
    )
    # Overhead skylight diffuser above sink, vanity, and floor tiles
    _add_area_light(
        name="Daylight_Skylight_Vanity",
        location=(1.8, -0.45, 2.52),
        target=(2.2, 0.35, 0.70),
        energy=135.0,
        color=(0.95, 0.97, 1.0),
        size_x=2.4,
        size_y=1.4,
        spread_deg=115.0,
    )
    # Overhead skylight diffuser above pickup station and corridor
    _add_area_light(
        name="Daylight_Skylight_Pickup",
        location=(-0.75, -0.55, 2.52),
        target=(-0.65, 0.30, 0.85),
        energy=115.0,
        color=(0.95, 0.97, 1.0),
        size_x=2.0,
        size_y=1.3,
        spread_deg=115.0,
    )
    # Soft opposite-wall tile bounce fill to keep shadows readable
    _add_area_light(
        name="Daylight_Tile_Bounce_Fill",
        location=(4.2, -1.8, 2.15),
        target=(1.4, 0.25, 0.75),
        energy=70.0,
        color=(0.90, 0.94, 1.0),
        size_x=2.4,
        size_y=1.5,
        spread_deg=120.0,
    )

    scene.display_settings.display_device = "sRGB"
    vs = scene.view_settings
    vs.view_transform = "AgX"
    vs.look = "None"
    vs.exposure = 0.0
    vs.gamma = 1.0
    vs.use_curve_mapping = False

    if hasattr(scene, "cycles"):
        scene.cycles.use_animated_seed = False
        scene.cycles.seed = 0

    return scene
