"""Native Blender 4.5 renderer and H.264 packager for the two DESPITE everyday studies.

Author/operator: Google Antigravity
Usage:
    antigravity-blender/bin/python antigravity_film.py drawer proof
    antigravity-blender/bin/python antigravity_film.py drawer movie
    antigravity-studio/bin/python  antigravity_film.py drawer pack
    antigravity-blender/bin/python antigravity_film.py pool proof
    antigravity-blender/bin/python antigravity_film.py pool movie
    antigravity-studio/bin/python  antigravity_film.py pool pack
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

HERE = Path(__file__).resolve().parent
REV = HERE.parent
OUTPUTS = HERE.parents[1]
REPO = HERE.parents[2]
LIBRARY = REPO / ".runtime" / "genie-assets"

CASES = {
    "drawer": {
        "k": 1,
        "dir": "01_drawer",
        "slug": "everyday_drawer",
        "room": "Bathroom vanity — washcloth stow",
        "task_id": "alfred_1162",
    },
    "pool": {
        "k": 2,
        "dir": "02_pool",
        "slug": "everyday_pool",
        "room": "Garden poolside — patio sweep",
        "task_id": "bddl_999",
    },
}

# Fixed, unobstructed camera definitions per study (eye, target, vertical FOV in deg).
# Overview cameras match the physical scene definitions; detail/rinse cameras are
# angled to keep the robot chassis and arm clear of the active mechanics.
CAMERAS = {
    "drawer": {
        "overview": ((1.84, -2.48, 1.84), (-0.02, 0.53, 0.69), 40.0),
        "rinse": ((-1.42, -0.28, 1.16), (-0.67, 0.70, 0.91), 38.0),
        "detail": ((1.26, -0.06, 1.04), (0.54, 0.50, 0.80), 36.0),
    },
    "pool": {
        "overview": ((1.43, -2.42, 1.50), (-0.02, 0.45, 0.48), 38.0),
        "detail": ((0.56, 1.04, 0.69), (-0.03, 0.51, -0.02), 46.0),
    },
}

FAUCET_OUTLET = np.array([-0.67, 0.744, 1.058], dtype=float)
FAUCET_SLOPE_Y = 0.33
BOWL_BOTTOM_Z = 0.727
CLOTH_HALF_Z = 0.011


def make_cam_record(
    eye: tuple[float, float, float],
    target: tuple[float, float, float],
    fovy: float,
) -> list[float]:
    """Build the 13-float camera record expected by cycles_render.camera_pose."""
    e = np.asarray(eye, dtype=float)
    t = np.asarray(target, dtype=float)
    z_back = e - t
    z_back /= np.linalg.norm(z_back)
    x_right = np.cross(np.array([0.0, 0.0, 1.0]), z_back)
    x_right /= np.linalg.norm(x_right)
    y_up = np.cross(z_back, x_right)
    rot = np.column_stack([x_right, y_up, z_back])
    return [*e.tolist(), *rot.reshape(-1).tolist(), float(fovy)]


def load_csv(path: Path) -> np.ndarray:
    return np.genfromtxt(path, delimiter=",", names=True)


def step_time(steps: list[dict], needles: tuple[str, ...], default: float) -> float:
    for s in steps:
        txt = s.get("text", "").lower()
        if any(n in txt for n in needles):
            return float(s["t"])
    return float(default)


def build_camera_schedule(case: str, branch: str, info: dict, times: np.ndarray) -> list[str]:
    """Assign a locked camera key to each 25 Hz frame, aligned to plan steps across branches."""
    steps = info[branch]["steps"]
    n = len(times)
    if case == "drawer":
        t_rinse = step_time(steps, ("faucet", "rinse"), 12.0)
        t_stow = step_time(steps, ("carry the rinsed", "lower it"), t_rinse + 5.5)
        t_close = step_time(steps, ("check that the case", "take the pull"), t_stow + 6.5)
        t_retreat = step_time(steps, ("back away",), times[-1] - 4.0)
        t_detail_end = min(float(times[-1]), t_retreat + 0.60)
        sched = []
        for t in times:
            if t_rinse <= t < t_stow:
                sched.append("rinse")
            elif t_close <= t < t_detail_end:
                sched.append("detail")
            else:
                sched.append("overview")
        return sched

    # Pool study: wide garden overview for rack pickup and return/park, locked far-bank
    # close-up across the entire sweep and settling interval so bristles, dustpan, coping,
    # and submerged grit motion are clearly visible without robot occlusion.
    t_sweep = step_time(steps, ("sweep",), 8.0)
    t_return = step_time(steps, ("lift the bristles", "replace it"), 11.4)
    t_cut_in = max(0.0, t_sweep - 0.60)
    t_cut_out = min(float(times[-1]), t_return + 1.00)
    return ["detail" if (t_cut_in <= t < t_cut_out) else "overview" for t in times]


def select_still_frames(
    case: str,
    branch: str,
    info: dict,
    times: np.ndarray,
    csv_data: np.ndarray,
) -> tuple[int, int]:
    """Return (poster_frame_idx, detail_frame_idx) from measured physics events."""
    n = len(times)

    def idx_at(t_sec: float) -> int:
        return int(np.clip(int(np.argmin(np.abs(times - t_sec))), 0, n - 1))

    steps = info[branch]["steps"]
    if case == "drawer":
        t_push = step_time(steps, ("slide the drawer", "push the drawer"), times[-1] - 6.0)
        t_retreat = step_time(steps, ("back away",), times[-1] - 3.5)
        if branch == "safe":
            poster_idx = idx_at(t_push + 0.95)
            detail_idx = idx_at(t_retreat + 0.15)
        else:
            t_evt = info["unsafe"].get("load_stop_s") or info["unsafe"].get("first_event_s") or (t_push + 1.35)
            poster_idx = idx_at(float(t_evt) + 0.12)
            detail_idx = idx_at(float(t_evt) + 0.16)
        return poster_idx, detail_idx

    t_sweep = step_time(steps, ("sweep",), 8.0)
    t_return = step_time(steps, ("lift the bristles", "replace it"), 11.5)
    csv_t = csv_data["time_s"]
    if branch == "safe":
        poster_idx = idx_at(t_sweep + 1.15)
        target_pan = int(info["safe"].get("pan_count", 24))
        hits = np.flatnonzero((csv_t >= t_sweep) & (csv_data["pan_count"] >= max(1, target_pan)))
        t_det = float(csv_t[hits[0]]) + 0.35 if len(hits) else (t_return + 0.25)
        t_det = float(np.clip(t_det, t_sweep + 1.40, min(float(times[-1]) - 0.2, t_return + 0.85)))
        detail_idx = idx_at(t_det)
    else:
        poster_idx = idx_at(t_sweep + 1.25)
        target_pool = int(info["unsafe"].get("pool_count", 24))
        hits = np.flatnonzero((csv_t >= t_sweep) & (csv_data["submerged"] >= max(1, target_pool)))
        if len(hits):
            t_det = float(csv_t[hits[0]]) + 0.55
        else:
            t_evt = info["unsafe"].get("first_event_s") or (t_sweep + 1.5)
            t_det = float(t_evt) + 1.25
        t_det = float(np.clip(t_det, t_sweep + 1.80, min(float(times[-1]) - 0.2, t_return + 1.20)))
        detail_idx = idx_at(t_det)
    return poster_idx, detail_idx


def faucet_stream_state(t_sec: float, csv_data: np.ndarray) -> tuple[bool, float]:
    """Query recorded CSV rinse flag and exact stream termination z at time t_sec."""
    csv_t = csv_data["time_s"]
    j = int(np.clip(int(np.searchsorted(csv_t, t_sec, side="left")), 0, len(csv_t) - 1))
    if j > 0 and abs(csv_t[j - 1] - t_sec) < abs(csv_t[j] - t_sec):
        j -= 1
    if int(round(float(csv_data["rinse"][j]))) <= 0:
        return False, BOWL_BOTTOM_Z
    cx = float(csv_data["item_x"][j])
    cy = float(csv_data["item_y"][j])
    cz = float(csv_data["item_z"][j])
    cloth_top = cz + CLOTH_HALF_Z
    stream_y_at_cloth = FAUCET_OUTLET[1] - FAUCET_SLOPE_Y * (FAUCET_OUTLET[2] - cloth_top)
    in_stream_xy = (abs(cx - FAUCET_OUTLET[0]) < 0.085) and (abs((cy + 0.043) - stream_y_at_cloth) < 0.095)
    if in_stream_xy and BOWL_BOTTOM_Z < cloth_top < FAUCET_OUTLET[2] - 0.015:
        z_end = cloth_top
    else:
        z_end = BOWL_BOTTOM_Z
    return True, float(z_end)


# ---------------------------------------------------------------------------
# Blender 4.5 rendering pipeline (imported lazily so 'pack' needs no bpy)
# ---------------------------------------------------------------------------


def _configure_cycles_device(bpy, scene) -> str:
    """Enable OptiX on RTX GPUs with safe CUDA -> CPU fallback."""
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for backend in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = backend
            prefs.get_devices()
            used = False
            for dev in prefs.devices:
                dev.use = dev.type == backend
                used = used or dev.use
            if used:
                scene.cycles.device = "GPU"
                scene.cycles.use_denoising = True
                if backend == "OPTIX":
                    try:
                        scene.cycles.denoiser = "OPTIX"
                    except TypeError:
                        scene.cycles.denoiser = "OPENIMAGEDENOISE"
                else:
                    scene.cycles.denoiser = "OPENIMAGEDENOISE"
                return backend
        except Exception:
            continue
    scene.cycles.device = "CPU"
    scene.cycles.use_denoising = True
    try:
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
    except TypeError:
        pass
    return "CPU"


def _init_view_safe(bpy, cr, k: int):
    """Instantiate cycles_render.View(k), falling back cleanly if OptiX is unavailable."""
    try:
        return cr.View(k)
    except RuntimeError as exc:
        if "OptiX" not in str(exc):
            raise
    # Rebuild the exact View state without requiring OptiX during __init__.
    d = next(cr.CACHE.glob(f"{k:02}_*"))
    v = object.__new__(cr.View)
    v.path = d
    v.meta = meta = json.loads((d / "meta.json").read_text())
    v.spec = meta["objects"]
    v.data = np.load(d / "shapes.npz")
    v.frames = {b: dict(np.load(d / (b + ".npz"))) for b in ("safe", "unsafe")}
    v.out = d / "images"
    v.out.mkdir(exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    v.scene = s
    _configure_cycles_device(bpy, s)
    s.render.use_persistent_data = True
    s.render.threads_mode = "FIXED"
    s.render.threads = 4
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = "JPEG"
    s.render.image_settings.quality = 94
    cam_data = bpy.data.cameras.new("Camera")
    v.cam = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(v.cam)
    s.camera = v.cam
    cam_data.clip_start = 0.004
    cam_data.sensor_fit = "VERTICAL"
    cam_data.sensor_height = 24.0
    cam_data.clip_end = 100.0
    v.model = SimpleNamespace(**{j: v.data[j] for j in v.data.files if j.startswith("mat_")})
    v.images, v.meshes, v.obs, v.skins = {}, {}, [], []
    for g in v.spec:
        matid = g["mat"]
        g["uniform"] = bool(v.model.mat_texuniform[matid]) if matid >= 0 else False
        typ, name = g["kind"], g["name"]
        if typ == "box":
            obj = cr.box(g)
        elif typ == "cylinder":
            obj = cr.cylinder(g)
        elif typ == "mesh":
            mid = g["mesh"]
            prefix = "m" + str(mid)
            obj = cr.meshobj(
                name,
                v.data[prefix + "_v"],
                v.data[prefix + "_f"],
                v.data.get(prefix + "_uv"),
                smooth=name.startswith("hero"),
            )
        elif typ in ("capsule", "sphere", "ellipsoid"):
            obj = cr.rounded(g)
        else:
            raise RuntimeError(f"Unsupported geom kind: {typ}")
        if matid >= 0:
            obj.data.materials.append(v.mat(matid, name, k))
        v.obs.append(obj)
    for skin in meta["skins"]:
        j = skin["id"]
        obj = cr.meshobj(
            skin["name"],
            v.frames["safe"]["skin" + str(j)][0],
            v.data[f"s{j}_f"],
            v.data[f"s{j}_uv"],
            True,
        )
        obj.data.materials.append(v.mat(skin["mat"], skin["name"], k))
        v.skins.append(obj)
    v.last = None
    return v


def _safe_world_sky(bpy, scene, name: str, strength: float, elevation_deg: float, rotation_deg: float) -> None:
    """Blender 4.5-safe sky world setup with Nishita -> Hosek-Wilkie -> gradient fallback."""
    old = bpy.data.worlds.get(name)
    if old is not None:
        bpy.data.worlds.remove(old, do_unlink=True)
    world = bpy.data.worlds.new(name)
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = strength
    try:
        sky = nt.nodes.new("ShaderNodeTexSky")
        for stype in ("NISHITA", "HOSEK_WILKIE", "PREETHAM"):
            try:
                sky.sky_type = stype
                break
            except TypeError:
                continue
        if hasattr(sky, "sun_disc"):
            sky.sun_disc = False
        if hasattr(sky, "sun_elevation"):
            sky.sun_elevation = math.radians(elevation_deg)
        if hasattr(sky, "sun_rotation"):
            sky.sun_rotation = math.radians(rotation_deg)
        nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    except Exception:
        bg.inputs["Color"].default_value = (0.68, 0.79, 0.92, 1.0)
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    scene.world = world


def _set_in(node, name: str, value) -> None:
    if name in node.inputs:
        node.inputs[name].default_value = value


def _new_mat(bpy, name: str):
    old = bpy.data.materials.get(name)
    if old is not None:
        bpy.data.materials.remove(old, do_unlink=True)
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat, nt, bsdf


def _make_translucent_pool_water_mat(bpy, name: str):
    """Clear rippled turquoise pool water allowing submerged grit to read cleanly below."""
    mat, nt, bsdf = _new_mat(bpy, name)
    geom = nt.nodes.new("ShaderNodeNewGeometry")

    _set_in(bsdf, "Base Color", (0.30, 0.78, 0.86, 1.0))
    _set_in(bsdf, "Roughness", 0.032)
    _set_in(bsdf, "IOR", 1.333)
    _set_in(bsdf, "Specular IOR Level", 0.65)
    _set_in(bsdf, "Coat Weight", 0.95)
    _set_in(bsdf, "Coat IOR", 1.333)
    _set_in(bsdf, "Coat Roughness", 0.018)
    _set_in(bsdf, "Alpha", 0.34)

    rip_a = nt.nodes.new("ShaderNodeTexNoise")
    rip_a.inputs["Scale"].default_value = 5.5
    rip_a.inputs["Detail"].default_value = 4.0
    rip_a.inputs["Roughness"].default_value = 0.45
    nt.links.new(geom.outputs["Position"], rip_a.inputs["Vector"])

    rip_b = nt.nodes.new("ShaderNodeTexWave")
    rip_b.wave_type = "BANDS"
    rip_b.bands_direction = "DIAGONAL"
    rip_b.inputs["Scale"].default_value = 2.8
    rip_b.inputs["Distortion"].default_value = 3.6
    nt.links.new(geom.outputs["Position"], rip_b.inputs["Vector"])

    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "FLOAT"
    mix.inputs[0].default_value = 0.35
    nt.links.new(rip_a.outputs["Fac"], mix.inputs[2])
    nt.links.new(rip_b.outputs["Fac"], mix.inputs[3])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.045
    bump.inputs["Distance"].default_value = 0.005
    nt.links.new(mix.outputs[0], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    if "Coat Normal" in bsdf.inputs:
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Coat Normal"])

    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    if hasattr(mat, "use_backface_culling"):
        mat.use_backface_culling = False
    return mat


def _make_pool_tile_mat(bpy, name: str):
    """Sunlit turquoise ceramic pool mosaic with caustics so dark grit pops underwater."""
    mat, nt, bsdf = _new_mat(bpy, name)
    geom = nt.nodes.new("ShaderNodeNewGeometry")

    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.0
    brick.inputs["Scale"].default_value = 4.6
    brick.inputs["Brick Width"].default_value = 0.25
    brick.inputs["Row Height"].default_value = 0.25
    brick.inputs["Mortar Size"].default_value = 0.036
    brick.inputs["Mortar Smooth"].default_value = 0.16
    brick.inputs["Color1"].default_value = (0.14, 0.62, 0.72, 1.0)
    brick.inputs["Color2"].default_value = (0.20, 0.72, 0.80, 1.0)
    brick.inputs["Mortar"].default_value = (0.58, 0.82, 0.86, 1.0)
    nt.links.new(geom.outputs["Position"], brick.inputs["Vector"])

    caustics = nt.nodes.new("ShaderNodeTexVoronoi")
    caustics.feature = "DISTANCE_TO_EDGE"
    caustics.inputs["Scale"].default_value = 3.0
    nt.links.new(geom.outputs["Position"], caustics.inputs["Vector"])

    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.clamp = True
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 0.12
    mr.inputs["To Min"].default_value = 0.28
    mr.inputs["To Max"].default_value = 0.0
    nt.links.new(caustics.outputs["Distance"], mr.inputs["Value"])

    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.clamp_factor = True
    mix.clamp_result = True
    rgba_in = [s for s in mix.inputs if s.type == "RGBA"]
    rgba_out = [s for s in mix.outputs if s.type == "RGBA"][0]
    nt.links.new(mr.outputs["Result"], mix.inputs[0])
    nt.links.new(brick.outputs["Color"], rgba_in[0])
    rgba_in[1].default_value = (0.68, 0.96, 0.99, 1.0)
    nt.links.new(rgba_out, bsdf.inputs["Base Color"])

    _set_in(bsdf, "Roughness", 0.24)
    _set_in(bsdf, "Coat Weight", 0.35)
    _set_in(bsdf, "Coat Roughness", 0.08)

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.06
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(brick.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def _make_paper_mat(bpy, name: str):
    mat, _, bsdf = _new_mat(bpy, name)
    _set_in(bsdf, "Base Color", (0.90, 0.87, 0.81, 1.0))
    _set_in(bsdf, "Roughness", 0.78)
    _set_in(bsdf, "Specular IOR Level", 0.25)
    return mat


def _make_ir_lens_mat(bpy, name: str):
    mat, _, bsdf = _new_mat(bpy, name)
    _set_in(bsdf, "Base Color", (0.04, 0.02, 0.03, 1.0))
    _set_in(bsdf, "Roughness", 0.06)
    _set_in(bsdf, "Coat Weight", 0.9)
    _set_in(bsdf, "Coat Roughness", 0.04)
    return mat


def _make_faucet_stream_mat(bpy, name: str):
    """Translucent glossy faucet water column visible only during recorded rinse."""
    mat, nt, bsdf = _new_mat(bpy, name)
    geom = nt.nodes.new("ShaderNodeNewGeometry")
    _set_in(bsdf, "Base Color", (0.76, 0.93, 0.98, 1.0))
    _set_in(bsdf, "Roughness", 0.025)
    _set_in(bsdf, "IOR", 1.333)
    _set_in(bsdf, "Specular IOR Level", 0.70)
    _set_in(bsdf, "Coat Weight", 1.0)
    _set_in(bsdf, "Coat Roughness", 0.02)
    _set_in(bsdf, "Alpha", 0.44)

    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = 28.0
    n.inputs["Detail"].default_value = 4.0
    nt.links.new(geom.outputs["Position"], n.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.06
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(n.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    return mat


def _create_faucet_stream_object(bpy, scene):
    """Create a unit-height tapered water stream mesh aligned along local +Z in [0, 1]."""
    import bmesh

    bm = bmesh.new()
    segs = 20
    r_top, r_bot = 0.0042, 0.0054
    ring0 = [
        bm.verts.new((r_top * math.cos(2.0 * math.pi * i / segs), r_top * math.sin(2.0 * math.pi * i / segs), 0.0))
        for i in range(segs)
    ]
    ring1 = [
        bm.verts.new((r_bot * math.cos(2.0 * math.pi * i / segs), r_bot * math.sin(2.0 * math.pi * i / segs), 1.0))
        for i in range(segs)
    ]
    for i in range(segs):
        j = (i + 1) % segs
        bm.faces.new((ring0[i], ring0[j], ring1[j], ring1[i]))
    bm.faces.new(tuple(reversed(ring0)))
    bm.faces.new(tuple(ring1))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new("Faucet_Water_Stream")
    bm.to_mesh(mesh)
    bm.free()
    for p in mesh.polygons:
        p.use_smooth = True
    mesh.materials.append(_make_faucet_stream_mat(bpy, "Study_drawer_faucet_stream"))
    obj = bpy.data.objects.new("Faucet_Water_Stream", mesh)
    if hasattr(obj, "visible_shadow"):
        obj.visible_shadow = False
    scene.collection.objects.link(obj)
    obj.hide_render = True
    obj.scale = (0.0, 0.0, 0.0)
    obj.location = (0.0, 0.0, -10.0)
    return obj


def _pose_faucet_stream(obj, active: bool, z_end: float) -> None:
    """Place the water stream from faucet outlet to z_end along the physical stream line."""
    from mathutils import Matrix, Vector

    if not active:
        obj.hide_render = True
        obj.matrix_world = Matrix.Translation((0.0, 0.0, -10.0)) @ Matrix.Diagonal((0.0, 0.0, 0.0, 1.0))
        return
    p0 = Vector(FAUCET_OUTLET.tolist())
    y_end = float(FAUCET_OUTLET[1] - FAUCET_SLOPE_Y * (FAUCET_OUTLET[2] - z_end))
    p1 = Vector((float(FAUCET_OUTLET[0]), y_end, float(z_end)))
    delta = p1 - p0
    length = delta.length
    if length < 1e-4:
        obj.hide_render = True
        obj.matrix_world = Matrix.Translation((0.0, 0.0, -10.0)) @ Matrix.Diagonal((0.0, 0.0, 0.0, 1.0))
        return
    z_axis = delta.normalized()
    ref = Vector((1.0, 0.0, 0.0))
    y_axis = z_axis.cross(ref).normalized()
    x_axis = y_axis.cross(z_axis).normalized()
    mat = Matrix((
        (x_axis.x, y_axis.x, z_axis.x * length, p0.x),
        (x_axis.y, y_axis.y, z_axis.y * length, p0.y),
        (x_axis.z, y_axis.z, z_axis.z * length, p0.z),
        (0.0, 0.0, 0.0, 1.0),
    ))
    obj.hide_render = False
    obj.matrix_world = mat


def _ensure_genie_maps_connected(bpy, neon_everyday, role_mats: dict, library: Path) -> None:
    """Verify architectural PBR materials have connected Alb/Nor/Rgh maps; fallback scan if needed."""
    def has_linked_maps(mat) -> bool:
        if not mat or not mat.use_nodes:
            return False
        names = [
            Path(bpy.path.abspath(n.image.filepath)).name
            for n in mat.node_tree.nodes
            if n.type == "TEX_IMAGE" and n.image and any(o.is_linked for o in n.outputs)
        ]
        return (
            any(x.endswith("_Alb.jpg") for x in names)
            and any(x.endswith("_Nor.jpg") for x in names)
            and any(x.endswith("_Rgh.jpg") for x in names)
        )

    triplets = None
    for role in ("floor", "wall", "gardenstone"):
        mat = role_mats.get(role)
        if mat is not None and has_linked_maps(mat):
            continue
        if triplets is None:
            triplets = []
            for alb in sorted(library.rglob("*_Alb.jpg")):
                stem = alb.name[:-8]
                nor = alb.with_name(stem + "_Nor.jpg")
                rgh = alb.with_name(stem + "_Rgh.jpg")
                if nor.is_file() and rgh.is_file():
                    triplets.append((alb, nor, rgh))
        if triplets:
            chosen = triplets[0] if role != "wall" else triplets[min(1, len(triplets) - 1)]
            role_mats[role] = neon_everyday._make_pbr_map_material(
                f"Fallback_{role}",
                chosen,
                tile_meters=0.75,
                rgh_range=(0.40, 0.78),
                normal_strength=0.58,
            )


def _collect_appearance_audit(bpy, case: str, objects: list, props: list[str], scene, backend: str, cam_defs: dict) -> dict:
    materials_used = {}
    surface_maps = []
    seen_surf = set()
    for obj in objects:
        if obj is None or not hasattr(obj, "material_slots"):
            continue
        for slot in obj.material_slots:
            mat = slot.material
            if not mat or not mat.use_nodes:
                continue
            textures = []
            for node in mat.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image and any(s.is_linked for s in node.outputs):
                    abs_path = Path(bpy.path.abspath(node.image.filepath))
                    cspace = node.image.colorspace_settings.name
                    textures.append([abs_path.name, cspace])
                    key = (mat.name, abs_path.name)
                    if key not in seen_surf:
                        seen_surf.add(key)
                        channel = (
                            "albedo"
                            if abs_path.name.endswith("_Alb.jpg")
                            else "normal"
                            if abs_path.name.endswith("_Nor.jpg")
                            else "roughness"
                            if abs_path.name.endswith("_Rgh.jpg")
                            else "texture"
                        )
                        surface_maps.append(
                            {
                                "material": mat.name,
                                "channel": channel,
                                "name": abs_path.name,
                                "path": str(abs_path),
                                "colorspace": cspace,
                            }
                        )
            if textures:
                materials_used[mat.name] = textures

    source_maps = sorted({Path(bpy.path.abspath(im.filepath)).name for im in bpy.data.images if im.filepath})
    created_lights = [o.name for o in scene.objects if o.type == "LIGHT"]
    return {
        "case": case,
        "slug": CASES[case]["slug"],
        "task_id": CASES[case]["task_id"],
        "designer": "Google Antigravity / Gemini 4 Neon High",
        "renderer": "Blender Cycles (stills), Blender Eevee Next (1080p motion)",
        "cycles_backend": backend,
        "source_maps": source_maps,
        "surface_maps": surface_maps,
        "materials": materials_used,
        "dressing": list(props),
        "lights": created_lights,
        "cameras": {
            name: {"eye": list(eye), "target": list(tgt), "fovy_deg": float(fov)}
            for name, (eye, tgt, fov) in cam_defs.items()
        },
        "as_filmed": {
            "motion_engine": "BLENDER_EEVEE_NEXT",
            "motion_samples": 8,
            "motion_px": [1920, 1080],
            "stills_engine": "CYCLES",
            "stills_samples": 36,
            "stills_px": [1920, 1080],
            "view_transform": str(scene.view_settings.view_transform),
            "look": str(scene.view_settings.look),
            "exposure_ev": float(scene.view_settings.exposure),
            "frame_rate": 25,
            "camera_policy": "Fixed locked cameras per phase; aligned across safe/unsafe branches.",
            "optical_simplifications": (
                "Touchless faucet water stream is rendered as a translucent optical column gated strictly by "
                "the recorded physics CSV rinse range flag and terminated at the recorded cloth top or basin floor."
                if case == "drawer"
                else "Pool water is rendered as a rippled translucent surface over sunlit mosaic tiles so all 24 "
                "rigid-body grit clusters remain directly observable as they cross the coping, sink under drag/buoyancy, "
                "and settle on the pool bottom."
            ),
        },
    }


def setup_blender_scene(case: str):
    """Load optical export, dress room via neon_everyday.py, assign materials, and prepare helpers."""
    import bpy

    for p in (str(OUTPUTS / "paired_workcells"), str(REV)):
        if p not in sys.path:
            sys.path.insert(0, p)

    import cycles_render as cr
    import neon_everyday

    cfg = CASES[case]
    cr.CACHE = HERE / "optics"
    v = _init_view_safe(bpy, cr, cfg["k"])
    s = v.scene

    # Smooth robot meshes cleanly while preserving crisp machined creases.
    for obj, g in zip(v.obs, v.spec):
        if g["kind"] == "mesh" and g["body"] not in ("world", "payload"):
            if hasattr(obj.data, "set_sharp_from_angle"):
                obj.data.set_sharp_from_angle(angle=math.radians(48.0))
            obj.data.polygons.foreach_set("use_smooth", np.ones(len(obj.data.polygons), dtype=bool))

    v.pose("safe", 0)
    bpy.context.view_layer.update()

    # Invoke original neon_everyday.build_room with Blender 4.5 sky fallback protection
    # (never modifies neon_everyday.py on disk).
    orig_sky = neon_everyday._setup_world_sky
    neon_everyday._setup_world_sky = lambda sc, name, strength, elevation_deg, rotation_deg: _safe_world_sky(
        bpy, sc, name, strength, elevation_deg, rotation_deg
    )
    try:
        room = neon_everyday.build_room(s, case, LIBRARY)
    finally:
        neon_everyday._setup_world_sky = orig_sky

    role_mats = dict(room["materials"])
    props = list(room["props"])
    _ensure_genie_maps_connected(bpy, neon_everyday, role_mats, LIBRARY)

    # Secondary and specialized optical roles.
    role_mats["paper"] = _make_paper_mat(bpy, f"Study_{case}_paper")
    ir_lens_mat = _make_ir_lens_mat(bpy, f"Study_{case}_ir_lens")
    if case == "pool":
        role_mats["water"] = _make_translucent_pool_water_mat(bpy, "Study_pool_water_translucent")
        role_mats["pool_tile"] = _make_pool_tile_mat(bpy, "Study_pool_tile")

    for obj, g in zip(v.obs, v.spec):
        if g["mat"] < 0:
            continue
        role = v.meta["materials"][g["mat"]]["name"].lower()
        mat = None
        if g["name"] == "infrared_window":
            mat = ir_lens_mat
        elif role in role_mats:
            mat = role_mats[role]
        if mat is not None:
            if len(obj.data.materials):
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)
        if case == "pool" and g["name"] == "pool_water":
            if hasattr(obj, "visible_shadow"):
                obj.visible_shadow = False

    # Re-apply Cycles GPU backend cleanly after build_room.
    backend = _configure_cycles_device(bpy, s)
    s.render.use_persistent_data = True
    s.render.threads_mode = "FIXED"
    s.render.threads = 4
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = "JPEG"
    s.render.image_settings.quality = 94

    # Prepare locked camera records (using scene overview from optics export when matching).
    cam_defs = CAMERAS[case]
    cam_records = {name: make_cam_record(eye, tgt, fov) for name, (eye, tgt, fov) in cam_defs.items()}
    if "overview" in v.meta:
        cam_records["overview"] = list(v.meta["overview"])

    stream_obj = _create_faucet_stream_object(bpy, s) if case == "drawer" else None
    prop_objs = [bpy.data.objects.get(n) for n in props]
    audit = _collect_appearance_audit(bpy, case, list(v.obs) + list(v.skins) + prop_objs, props, s, backend, cam_defs)
    return bpy, cr, v, cam_records, stream_obj, audit


def run_proof(case: str) -> None:
    """Render native 1080p Cycles stills (posters + detail views) and write appearance.json."""
    cfg = CASES[case]
    src = HERE / cfg["dir"]
    frames_dir = HERE / "frames" / cfg["slug"]
    gallery_dir = HERE / "gallery" / cfg["slug"]
    frames_dir.mkdir(parents=True, exist_ok=True)
    gallery_dir.mkdir(parents=True, exist_ok=True)

    info = json.loads((src / "info.json").read_text())
    bpy, cr, v, cam_records, stream_obj, audit = setup_blender_scene(case)
    s = v.scene

    s.render.engine = "CYCLES"
    s.render.resolution_x = 1920
    s.render.resolution_y = 1080
    s.render.image_settings.quality = 95
    s.cycles.samples = 36
    s.cycles.use_adaptive_sampling = True
    s.cycles.adaptive_min_samples = 6
    s.cycles.adaptive_threshold = 0.03
    s.cycles.use_animated_seed = False
    s.cycles.seed = 17

    for branch in ("safe", "unsafe"):
        times = np.load(src / f"{branch}.npz")["time_s"]
        csv_data = load_csv(src / f"{branch}.csv")
        poster_idx, detail_idx = select_still_frames(case, branch, info, times, csv_data)
        shots = [
            (f"{branch}_poster.jpg", poster_idx, cam_records["overview"]),
            (f"detail_{branch}.jpg", detail_idx, cam_records["detail"]),
        ]
        for fname, fidx, cam_rec in shots:
            v.pose(branch, fidx)
            cr.camera_pose(v.cam, cam_rec)
            if stream_obj is not None:
                active, z_end = faucet_stream_state(float(times[fidx]), csv_data)
                _pose_faucet_stream(stream_obj, active, z_end)
            out_path = frames_dir / fname
            s.render.filepath = str(out_path)
            bpy.ops.render.render(write_still=True)
            shutil.copy2(out_path, gallery_dir / fname)
            print(f"[proof] {case} {branch} -> {fname} (frame {fidx}, t={times[fidx]:.2f}s)", flush=True)

    for dest in (frames_dir / "appearance.json", gallery_dir / "appearance.json"):
        dest.write_text(json.dumps(audit, indent=2) + "\n")

    # Build thumbnail if PIL is present in this interpreter (pack also creates/verifies it).
    try:
        from PIL import Image

        with Image.open(gallery_dir / "safe_poster.jpg") as im:
            im.resize((400, 225), Image.Resampling.LANCZOS).save(gallery_dir / "thumb.jpg", quality=92)
    except Exception:
        pass
    print(f"[proof] Completed {case} stills and appearance.json", flush=True)


def run_movie(case: str) -> None:
    """Render full 1920x1080 25 fps motion frames in one EEVEE Next animation pass."""
    cfg = CASES[case]
    src = HERE / cfg["dir"]
    frames_dir = HERE / "frames" / cfg["slug"]
    gallery_dir = HERE / "gallery" / cfg["slug"]
    frames_dir.mkdir(parents=True, exist_ok=True)
    gallery_dir.mkdir(parents=True, exist_ok=True)

    info = json.loads((src / "info.json").read_text())
    bpy, cr, v, cam_records, stream_obj, audit = setup_blender_scene(case)
    s = v.scene

    for dest in (frames_dir / "appearance.json", gallery_dir / "appearance.json"):
        if not dest.is_file():
            dest.write_text(json.dumps(audit, indent=2) + "\n")

    csv_by_branch = {b: load_csv(src / f"{b}.csv") for b in ("safe", "unsafe")}
    times_by_branch = {b: np.load(src / f"{b}.npz")["time_s"] for b in ("safe", "unsafe")}
    sched_by_branch = {b: build_camera_schedule(case, b, info, times_by_branch[b]) for b in ("safe", "unsafe")}

    seen: dict[bytes, Path] = {}
    deferred: list[tuple[Path, Path]] = []
    pending: list[tuple[str, int, str, tuple[bool, float], Path]] = []

    for b in ("unsafe", "safe"):
        poses = v.frames[b]["poses"]
        times = times_by_branch[b]
        sched = sched_by_branch[b]
        csv_data = csv_by_branch[b]
        for i in range(len(poses)):
            out = frames_dir / f"{b}_{i:04d}.jpg"
            cam_key = sched[i]
            stream_info = faucet_stream_state(float(times[i]), csv_data) if stream_obj is not None else (False, 0.0)
            digest = hashlib.blake2b(poses[i].round(5).tobytes(), digest_size=16)
            digest.update(cam_key.encode("ascii"))
            digest.update(f"{int(stream_info[0])}:{stream_info[1]:.4f}".encode("ascii"))
            for j in range(len(v.skins)):
                digest.update(v.frames[b][f"skin{j}"][i].round(5).tobytes())
            token = digest.digest()
            if out.exists() and out.stat().st_size > 1024:
                seen[token] = out
                continue
            if token in seen:
                deferred.append((seen[token], out))
                continue
            pending.append((b, i, cam_key, stream_info, out))
            seen[token] = out

    print(
        f"[movie] {case}: total={sum(len(v.frames[b]['poses']) for b in ('safe','unsafe'))}, "
        f"unique_to_render={len(pending)}, reused={len(deferred)}",
        flush=True,
    )

    if pending:
        s.render.engine = "BLENDER_EEVEE_NEXT"
        if hasattr(s.eevee, "taa_render_samples"):
            s.eevee.taa_render_samples = 8
        if hasattr(s.eevee, "use_shadows"):
            s.eevee.use_shadows = True
        if hasattr(s.eevee, "use_raytracing"):
            s.eevee.use_raytracing = True
        s.render.use_persistent_data = True
        s.render.resolution_x = 1920
        s.render.resolution_y = 1080
        s.render.resolution_percentage = 100
        s.render.image_settings.file_format = "JPEG"
        s.render.image_settings.quality = 94
        s.render.fps = 25
        s.frame_start = 1
        s.frame_end = len(pending)
        s.render.filepath = str(frames_dir / "_anim_")

        def set_frame(scene, *_unused):
            idx = scene.frame_current - 1
            if 0 <= idx < len(pending):
                b, i, cam_key, (st_active, st_z), _ = pending[idx]
                v.pose(b, i)
                cr.camera_pose(v.cam, cam_records[cam_key])
                if stream_obj is not None:
                    _pose_faucet_stream(stream_obj, st_active, st_z)

        def save_frame(scene, *_unused):
            idx = scene.frame_current - 1
            if 0 <= idx < len(pending):
                src_img = Path(scene.render.frame_path(frame=scene.frame_current))
                if src_img.exists():
                    os.replace(src_img, pending[idx][4])

        bpy.app.handlers.frame_change_pre.append(set_frame)
        bpy.app.handlers.render_write.append(save_frame)
        try:
            s.frame_set(1)
            set_frame(s)
            bpy.ops.render.render(animation=True)
        finally:
            if set_frame in bpy.app.handlers.frame_change_pre:
                bpy.app.handlers.frame_change_pre.remove(set_frame)
            if save_frame in bpy.app.handlers.render_write:
                bpy.app.handlers.render_write.remove(save_frame)

        for idx, (_, _, _, _, dst_path) in enumerate(pending, 1):
            if not dst_path.exists():
                staging = Path(s.render.frame_path(frame=idx))
                if staging.exists():
                    staging.replace(dst_path)

    for src_img, dst_img in deferred:
        if not dst_img.exists():
            try:
                os.link(src_img, dst_img)
            except OSError:
                shutil.copyfile(src_img, dst_img)

    n_frames = len(v.frames["safe"]["poses"])
    rendered_meta = {
        "case": case,
        "slug": cfg["slug"],
        "frames": n_frames,
        "unique_rendered": len(seen),
        "width": 1920,
        "height": 1080,
        "fps": 25,
        "engine": "BLENDER_EEVEE_NEXT",
        "samples": 8,
    }
    (frames_dir / "rendered.json").write_text(json.dumps(rendered_meta, indent=2) + "\n")
    print(f"[movie] Finished {case}: {n_frames} frames/branch ({len(seen)} unique)", flush=True)


# ---------------------------------------------------------------------------
# Packaging and H.264 encoding (runs in studio Python without bpy)
# ---------------------------------------------------------------------------


def _update_production_report(case: str, info: dict, audit: dict, n_frames: int) -> None:
    report_path = HERE / "production-report.json"
    if report_path.is_file():
        report = json.loads(report_path.read_text())
    else:
        report = {
            "author": "Google Antigravity / Gemini 4 Neon High",
            "workspace": str(HERE),
            "assets": {
                "robot_base": "Omron wheeled mobile base (outputs/mobile_worlds/physics/assets/omron/meshes/omron_mobile_base/omron_0..7.obj)",
                "robot_arm": "Franka Emika Panda (outputs/mobile_worlds/physics/assets/panda/obj_meshes and meshes/link0..7)",
                "robot_hand": "Franka Panda Hand (outputs/mobile_worlds/physics/assets/hand/meshes/panda_gripper)",
                "pbr_textures": "Genie Sim home_b Alb/Nor/Rgh texture sets (.runtime/genie-assets/background/common/home_b/textures)",
                "room_module": "outputs/antigravity_revision/neon_everyday.py (build_room, plan)",
            },
            "studies": {},
        }

    cfg = CASES[case]
    gallery_dir = HERE / "gallery" / cfg["slug"]
    entry = {
        "task_id": cfg["task_id"],
        "slug": cfg["slug"],
        "identical_initial_qpos": bool(info.get("identical_initial_qpos", False)),
        "frames_per_branch": int(n_frames),
        "duration_s": round(n_frames / 25.0, 2),
        "resolution": [1920, 1080],
        "fps": 25,
        "gallery_dir": str(gallery_dir),
        "connected_pbr_maps": audit.get("source_maps", []),
        "safe": {
            "drawer_end_m": info["safe"]["drawer_end_m"],
            "peak_header_N": info["safe"]["peak_header_N"],
            "cloth_support_N": info["safe"]["cloth_support_N"],
            "cloth_rinse_s": info["safe"]["cloth_rinse_s"],
            "peak_brush_N": info["safe"]["peak_brush_N"],
            "pan_count": info["safe"]["pan_count"],
            "pool_count": info["safe"]["pool_count"],
            "captures": info["safe"]["captures"],
            "warnings": info["safe"]["warnings"],
            "joint_margin_rad": info["safe"]["joint_margin"],
            "max_joint_speeds_rad_s": info["safe"]["max_joint_speeds"],
            "max_overlap_mm": info["safe"]["max_overlap_mm"],
            "unintended_robot_contact": info["safe"]["unintended_robot_contact"],
            "sample_rate_Hz": info["safe"]["sample_rate_Hz"],
        },
        "unsafe": {
            "drawer_end_m": info["unsafe"]["drawer_end_m"],
            "peak_header_N": info["unsafe"]["peak_header_N"],
            "cloth_support_N": info["unsafe"]["cloth_support_N"],
            "cloth_rinse_s": info["unsafe"]["cloth_rinse_s"],
            "peak_brush_N": info["unsafe"]["peak_brush_N"],
            "peak_bottom_N": info["unsafe"]["peak_bottom_N"],
            "pan_count": info["unsafe"]["pan_count"],
            "pool_count": info["unsafe"]["pool_count"],
            "load_stop_s": info["unsafe"].get("load_stop_s"),
            "first_event_s": info["unsafe"].get("first_event_s"),
            "captures": info["unsafe"]["captures"],
            "warnings": info["unsafe"]["warnings"],
            "joint_margin_rad": info["unsafe"]["joint_margin"],
            "max_joint_speeds_rad_s": info["unsafe"]["max_joint_speeds"],
            "max_overlap_mm": info["unsafe"]["max_overlap_mm"],
            "unintended_robot_contact": info["unsafe"]["unintended_robot_contact"],
            "sample_rate_Hz": info["unsafe"]["sample_rate_Hz"],
        },
        "physics_and_modeling_notes": (
            "500 Hz rigid-body simulation. Safe removes the upright toiletry case before closing the vanity drawer "
            "(3.6 mm residual extension, 0 N header load); unsafe closes with the case present (11.86 N peak header "
            "normal contact, 76.4 mm residual extension). Folded cloth finishes supported in the drawer tray (0.510 N) "
            "in both branches. The touchless faucet stream is modeled optically and gated strictly by the recorded "
            "CSV rinse range flag, terminating at the cloth top or bowl floor rather than coupled fluid CFD."
            if case == "drawer"
            else "2000 Hz (0.5 ms) rigid-body simulation with 24 dense mineral-grit spheres (6.7 g each, radii 8.4–9.6 mm, "
            "~2194 kg/m^3). Root cause of the prior 0/24 transfer failure: (1) rack_hold had body1='broom' with default "
            "body2='world', evaluating weld error 1.19 m away at world origin and sagging the broom 5.6 mm onto the deck; "
            "(2) grasp_broom torquescale=0.055 over the 0.91 m handle pitched the broom 13.1 deg under floor drag, "
            "lagging the bristles 18–20 cm behind the hand and lifting them +17 mm above the grains. Fixing rack_hold "
            "(body1='world', body2='broom'), firming grasp_broom (torquescale=0.55), and setting 2.5–3.5 mm rigid bristle "
            "core clearance with 1 mm pan plate yielded 24/24 grit clusters in the pan (safe, 0 submerged) and 24/24 "
            "submerged in the pool (unsafe, 0 in pan) with zero solver warnings and zero unintended robot contacts. "
            "Water resistance uses sphere buoyancy (rho=1000 kg/m^3) and quadratic drag (Cd=0.9) below z=-0.085 m."
        ),
    }
    report["studies"][case] = entry
    report_path.write_text(json.dumps(report, indent=2) + "\n")


def run_pack(case: str) -> None:
    """Encode native 1920x1080 25 fps H.264 MP4s with burned-in English captions and verify outputs."""
    import imageio_ffmpeg as ff
    from PIL import Image

    mw_dir = str(OUTPUTS / "mobile_worlds")
    if mw_dir not in sys.path:
        sys.path.insert(0, mw_dir)
    from film_encode import ffmpeg, subtitles

    cfg = CASES[case]
    src = HERE / cfg["dir"]
    frames_dir = HERE / "frames" / cfg["slug"]
    gallery_dir = HERE / "gallery" / cfg["slug"]
    gallery_dir.mkdir(parents=True, exist_ok=True)

    info = json.loads((src / "info.json").read_text())
    rendered = json.loads((frames_dir / "rendered.json").read_text())
    n = int(rendered["frames"])

    for b in ("safe", "unsafe"):
        timeline = np.load(src / f"{b}.npz")["time_s"]
        assert len(timeline) == n, (case, b, len(timeline), n)
        assert np.allclose(np.diff(timeline), 0.04, atol=1e-4), (case, b, "non-25Hz timeline")
        ass_path = frames_dir / f"{b}.ass"
        subtitles(ass_path, info, b, timeline, cfg["room"])

        final_mp4 = (gallery_dir / f"{b}.mp4").resolve()
        partial_mp4 = final_mp4.with_name(f"{b}.partial.mp4")
        ffmpeg(
            [
                "-filter_complex_threads", "2",
                "-filter_threads", "2",
                "-framerate", "25",
                "-i", f"{b}_%04d.jpg",
                "-frames:v", str(n),
                "-vf", f"ass={ass_path.name}",
                "-an",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-threads", "4",
                "-crf", "18",
                "-preset", "fast",
                "-maxrate", "16M",
                "-bufsize", "24M",
                "-movflags", "+faststart",
                str(partial_mp4),
            ],
            frames_dir,
        )
        os.replace(partial_mp4, final_mp4)

        count, _ = ff.count_frames_and_secs(str(final_mp4))
        assert count == n, (final_mp4, count, n)
        reader = ff.read_frames(str(final_mp4))
        meta = next(reader)
        reader.close()
        assert tuple(meta["size"]) == (1920, 1080), (final_mp4, meta["size"])
        print(f"[pack] Encoded & verified {final_mp4.name}: {n} frames @ 1920x1080 25fps", flush=True)

        for img_name in (f"{b}_poster.jpg", f"detail_{b}.jpg"):
            src_img = frames_dir / img_name
            dst_img = gallery_dir / img_name
            if src_img.is_file() and (not dst_img.is_file() or src_img.stat().st_mtime > dst_img.stat().st_mtime):
                shutil.copy2(src_img, dst_img)
            assert dst_img.is_file(), f"Missing still {dst_img}"

    with Image.open(gallery_dir / "safe_poster.jpg") as im:
        im.resize((400, 225), Image.Resampling.LANCZOS).save(gallery_dir / "thumb.jpg", quality=92)

    app_src = frames_dir / "appearance.json"
    app_dst = gallery_dir / "appearance.json"
    if app_src.is_file():
        shutil.copy2(app_src, app_dst)
    assert app_dst.is_file(), f"Missing {app_dst}"
    audit = json.loads(app_dst.read_text())
    maps = audit.get("source_maps", [])
    assert any(m.endswith("_Alb.jpg") for m in maps), f"Missing Alb map in {maps}"
    assert any(m.endswith("_Nor.jpg") for m in maps), f"Missing Nor map in {maps}"
    assert any(m.endswith("_Rgh.jpg") for m in maps), f"Missing Rgh map in {maps}"
    assert audit.get("dressing") and audit.get("materials"), "Missing room dressing or materials audit"

    _update_production_report(case, info, audit, n)
    print(f"[pack] Packaged {cfg['slug']} -> {gallery_dir}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render and package DESPITE everyday household studies.")
    parser.add_argument("case", choices=("drawer", "pool"))
    parser.add_argument("mode", choices=("proof", "movie", "pack"))
    args = parser.parse_args()

    if args.mode == "proof":
        run_proof(args.case)
    elif args.mode == "movie":
        run_movie(args.case)
    else:
        run_pack(args.case)

    sys.stdout.flush()
    sys.stderr.flush()


if __name__ == "__main__":
    main()
