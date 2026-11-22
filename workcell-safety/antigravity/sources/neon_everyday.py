"""Photorealistic everyday robotics room builder and action plans for Blender 4.5.

Provides:
- plan(case, safe) -> list[str]
- build_room(scene, case, library) -> dict[str, object]
"""

from __future__ import annotations

import math
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

_PLANS = {
    "drawer": {
        True: [
            "open_drawer",
            "clear_case",
            "fetch_cloth",
            "rinse_cloth",
            "stow_cloth",
            "close_drawer",
            "retreat",
        ],
        False: [
            "open_drawer",
            "fetch_cloth",
            "rinse_cloth",
            "stow_cloth",
            "close_drawer",
            "retreat",
        ],
    },
    "pool": {
        True: [
            "approach_rack",
            "take_broom",
            "approach_grit",
            "sweep_to_pan",
            "return_broom",
            "park",
        ],
        False: [
            "approach_rack",
            "take_broom",
            "approach_grit",
            "sweep_to_pool",
            "return_broom",
            "park",
        ],
    },
}


def plan(case: str, safe: bool) -> list[str]:
    """Return the exact action ID sequence for the requested study and safety branch."""
    if case not in _PLANS:
        raise ValueError(f"Unsupported case {case!r}; expected 'drawer' or 'pool'.")
    return list(_PLANS[case][bool(safe)])


# ---------------------------------------------------------------------------
# Shader and texture helpers (Blender 4.5, Cycles + Eevee Next)
# ---------------------------------------------------------------------------


def _set_in(node: bpy.types.Node, name: str, value) -> None:
    if name in node.inputs:
        node.inputs[name].default_value = value


def _new_material(name: str) -> tuple[bpy.types.Material, bpy.types.NodeTree, bpy.types.Node]:
    old = bpy.data.materials.get(name)
    if old is not None:
        bpy.data.materials.remove(old, do_unlink=True)
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (460, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (180, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat, nt, bsdf


def _mix_rgba(
    nt: bpy.types.NodeTree,
    fac,
    col_a,
    col_b,
    blend: str = "MIX",
    loc: tuple[float, float] = (0, 0),
) -> bpy.types.Node:
    node = nt.nodes.new("ShaderNodeMix")
    node.data_type = "RGBA"
    node.blend_type = blend
    node.clamp_factor = True
    node.clamp_result = True
    node.location = loc
    rgba_in = [s for s in node.inputs if s.type == "RGBA"]
    if isinstance(fac, (int, float)):
        node.inputs[0].default_value = float(fac)
    else:
        nt.links.new(fac, node.inputs[0])
    if isinstance(col_a, (tuple, list)):
        rgba_in[0].default_value = col_a
    else:
        nt.links.new(col_a, rgba_in[0])
    if isinstance(col_b, (tuple, list)):
        rgba_in[1].default_value = col_b
    else:
        nt.links.new(col_b, rgba_in[1])
    return node


def _rgba_out(mix_node: bpy.types.Node) -> bpy.types.NodeSocket:
    return [s for s in mix_node.outputs if s.type == "RGBA"][0]


def _map_range(
    nt: bpy.types.NodeTree,
    src_socket: bpy.types.NodeSocket,
    fmin: float,
    fmax: float,
    tmin: float,
    tmax: float,
    loc: tuple[float, float] = (0, 0),
) -> bpy.types.NodeSocket:
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.clamp = True
    mr.location = loc
    mr.inputs["From Min"].default_value = fmin
    mr.inputs["From Max"].default_value = fmax
    mr.inputs["To Min"].default_value = tmin
    mr.inputs["To Max"].default_value = tmax
    nt.links.new(src_socket, mr.inputs["Value"])
    return mr.outputs["Result"]


def _load_image(path: Path, colorspace: str) -> bpy.types.Image | None:
    if not path.is_file():
        return None
    img = bpy.data.images.load(str(path), check_existing=True)
    img.colorspace_settings.name = colorspace
    return img


def _resolve_tex_triplet(
    tex_dir: Path, preferred: str, fallback: str
) -> tuple[Path, Path, Path]:
    stem = preferred if (tex_dir / f"{preferred}_Alb.jpg").is_file() else fallback
    return (
        tex_dir / f"{stem}_Alb.jpg",
        tex_dir / f"{stem}_Nor.jpg",
        tex_dir / f"{stem}_Rgh.jpg",
    )


def _make_pbr_map_material(
    name: str,
    tex_paths: tuple[Path, Path, Path],
    tile_meters: float,
    tint: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
    lift_color: tuple[float, float, float, float] | None = None,
    lift_fac: float = 0.0,
    rgh_range: tuple[float, float] = (0.30, 0.72),
    normal_strength: float = 0.60,
    macro_var: float = 0.06,
    fallback_rgb: tuple[float, float, float, float] = (0.72, 0.71, 0.68, 1.0),
) -> bpy.types.Material:
    """Metric world-space box-mapped PBR material using Genie Sim Alb/Nor/Rgh maps."""
    mat, nt, bsdf = _new_material(name)
    geom = nt.nodes.new("ShaderNodeNewGeometry")
    geom.location = (-860, 0)
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.location = (-660, 0)
    inv = 1.0 / max(tile_meters, 0.05)
    mapping.inputs["Scale"].default_value = (inv, inv, inv)
    nt.links.new(geom.outputs["Position"], mapping.inputs["Vector"])

    alb_img = _load_image(tex_paths[0], "sRGB")
    nor_img = _load_image(tex_paths[1], "Non-Color")
    rgh_img = _load_image(tex_paths[2], "Non-Color")

    if alb_img is not None:
        tex_alb = nt.nodes.new("ShaderNodeTexImage")
        tex_alb.image = alb_img
        tex_alb.projection = "BOX"
        tex_alb.projection_blend = 0.14
        tex_alb.location = (-400, 260)
        nt.links.new(mapping.outputs["Vector"], tex_alb.inputs["Vector"])
        col_sock = tex_alb.outputs["Color"]
    else:
        n_fb = nt.nodes.new("ShaderNodeTexNoise")
        n_fb.location = (-400, 260)
        n_fb.inputs["Scale"].default_value = 4.0
        n_fb.inputs["Detail"].default_value = 6.0
        nt.links.new(mapping.outputs["Vector"], n_fb.inputs["Vector"])
        dark = (fallback_rgb[0] * 0.88, fallback_rgb[1] * 0.88, fallback_rgb[2] * 0.88, 1.0)
        col_sock = _rgba_out(_mix_rgba(nt, n_fb.outputs["Fac"], dark, fallback_rgb, "MIX", (-180, 260)))

    if tint != (1.0, 1.0, 1.0, 1.0):
        col_sock = _rgba_out(_mix_rgba(nt, 1.0, col_sock, tint, "MULTIPLY", (-140, 260)))
    if lift_color is not None and lift_fac > 0.0:
        col_sock = _rgba_out(_mix_rgba(nt, lift_fac, col_sock, lift_color, "MIX", (-20, 260)))

    if macro_var > 0.0:
        mac = nt.nodes.new("ShaderNodeTexNoise")
        mac.location = (-400, 440)
        mac.inputs["Scale"].default_value = 0.75
        mac.inputs["Detail"].default_value = 3.0
        nt.links.new(geom.outputs["Position"], mac.inputs["Vector"])
        shade = _map_range(nt, mac.outputs["Fac"], 0.25, 0.75, 1.0 - macro_var, 1.0 + macro_var * 0.5, (-180, 440))
        comb = nt.nodes.new("ShaderNodeCombineColor")
        comb.location = (-20, 440)
        for ch in ("Red", "Green", "Blue"):
            nt.links.new(shade, comb.inputs[ch])
        col_sock = _rgba_out(_mix_rgba(nt, 1.0, col_sock, comb.outputs["Color"], "MULTIPLY", (60, 260)))

    nt.links.new(col_sock, bsdf.inputs["Base Color"])

    if rgh_img is not None:
        tex_rgh = nt.nodes.new("ShaderNodeTexImage")
        tex_rgh.image = rgh_img
        tex_rgh.projection = "BOX"
        tex_rgh.projection_blend = 0.14
        tex_rgh.location = (-400, -10)
        nt.links.new(mapping.outputs["Vector"], tex_rgh.inputs["Vector"])
        rgh_sock = _map_range(nt, tex_rgh.outputs["Color"], 0.0, 1.0, rgh_range[0], rgh_range[1], (-100, -10))
        nt.links.new(rgh_sock, bsdf.inputs["Roughness"])
    else:
        _set_in(bsdf, "Roughness", 0.5 * (rgh_range[0] + rgh_range[1]))

    if nor_img is not None:
        tex_nor = nt.nodes.new("ShaderNodeTexImage")
        tex_nor.image = nor_img
        tex_nor.projection = "BOX"
        tex_nor.projection_blend = 0.14
        tex_nor.location = (-400, -290)
        nt.links.new(mapping.outputs["Vector"], tex_nor.inputs["Vector"])
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nmap.space = "TANGENT"
        nmap.location = (-100, -290)
        nmap.inputs["Strength"].default_value = normal_strength
        nt.links.new(tex_nor.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    _set_in(bsdf, "Specular IOR Level", 0.45)
    return mat


def _make_ceramic_mat(name: str) -> bpy.types.Material:
    mat, nt, bsdf = _new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 45.0
    noise.inputs["Detail"].default_value = 3.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])

    _set_in(bsdf, "Base Color", (0.915, 0.910, 0.895, 1.0))
    _set_in(bsdf, "IOR", 1.52)
    _set_in(bsdf, "Specular IOR Level", 0.56)
    _set_in(bsdf, "Coat Weight", 0.88)
    _set_in(bsdf, "Coat Roughness", 0.035)
    nt.links.new(_map_range(nt, noise.outputs["Fac"], 0.2, 0.8, 0.075, 0.135), bsdf.inputs["Roughness"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.012
    bump.inputs["Distance"].default_value = 0.001
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def _make_doors_mat(name: str) -> bpy.types.Material:
    mat, nt, bsdf = _new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 80.0
    noise.inputs["Detail"].default_value = 4.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])

    _set_in(bsdf, "Base Color", (0.74, 0.75, 0.72, 1.0))
    _set_in(bsdf, "Specular IOR Level", 0.48)
    _set_in(bsdf, "Coat Weight", 0.15)
    _set_in(bsdf, "Coat Roughness", 0.22)
    nt.links.new(_map_range(nt, noise.outputs["Fac"], 0.2, 0.8, 0.30, 0.39), bsdf.inputs["Roughness"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.018
    bump.inputs["Distance"].default_value = 0.001
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def _make_wood_mat(
    name: str,
    light_rgb: tuple[float, float, float, float],
    dark_rgb: tuple[float, float, float, float],
    rgh_range: tuple[float, float] = (0.42, 0.62),
    scale: tuple[float, float, float] = (2.5, 16.0, 2.5),
    coat: float = 0.08,
    bump_strength: float = 0.055,
) -> bpy.types.Material:
    mat, nt, bsdf = _new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = scale
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])

    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 3.2
    wave.inputs["Distortion"].default_value = 6.5
    wave.inputs["Detail"].default_value = 6.0
    wave.inputs["Detail Scale"].default_value = 2.0
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])

    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 28.0
    fine.inputs["Detail"].default_value = 8.0
    fine.inputs["Roughness"].default_value = 0.65
    nt.links.new(mp.outputs["Vector"], fine.inputs["Vector"])

    grain = _rgba_out(_mix_rgba(nt, 0.30, wave.outputs["Fac"], fine.outputs["Fac"], "MIX"))
    col = _rgba_out(_mix_rgba(nt, wave.outputs["Fac"], dark_rgb, light_rgb, "MIX"))
    nt.links.new(col, bsdf.inputs["Base Color"])
    nt.links.new(_map_range(nt, wave.outputs["Fac"], 0.1, 0.9, rgh_range[1], rgh_range[0]), bsdf.inputs["Roughness"])
    _set_in(bsdf, "Coat Weight", coat)
    _set_in(bsdf, "Coat Roughness", 0.34)
    _set_in(bsdf, "Specular IOR Level", 0.45)

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(grain, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def _make_chrome_mat(name: str) -> bpy.types.Material:
    mat, nt, bsdf = _new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (12.0, 140.0, 12.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])

    brush = nt.nodes.new("ShaderNodeTexNoise")
    brush.inputs["Scale"].default_value = 10.0
    brush.inputs["Detail"].default_value = 5.0
    nt.links.new(mp.outputs["Vector"], brush.inputs["Vector"])

    _set_in(bsdf, "Base Color", (0.83, 0.85, 0.87, 1.0))
    _set_in(bsdf, "Metallic", 0.98)
    _set_in(bsdf, "Anisotropic", 0.42)
    nt.links.new(_map_range(nt, brush.outputs["Fac"], 0.2, 0.8, 0.14, 0.24), bsdf.inputs["Roughness"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.018
    bump.inputs["Distance"].default_value = 0.0005
    nt.links.new(brush.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def _make_terry_mat(
    name: str,
    base_rgb: tuple[float, float, float, float] = (0.31, 0.45, 0.55, 1.0),
) -> bpy.types.Material:
    """Soft looped terry cloth with pile micro-loops and cotton sheen."""
    mat, nt, bsdf = _new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")

    loops = nt.nodes.new("ShaderNodeTexVoronoi")
    loops.feature = "F1"
    loops.inputs["Scale"].default_value = 260.0
    nt.links.new(tc.outputs["Object"], loops.inputs["Vector"])

    weave = nt.nodes.new("ShaderNodeTexNoise")
    weave.inputs["Scale"].default_value = 85.0
    weave.inputs["Detail"].default_value = 8.0
    weave.inputs["Roughness"].default_value = 0.72
    nt.links.new(tc.outputs["Object"], weave.inputs["Vector"])

    dark = (base_rgb[0] * 0.72, base_rgb[1] * 0.74, base_rgb[2] * 0.76, 1.0)
    col = _rgba_out(_mix_rgba(nt, loops.outputs["Distance"], base_rgb, dark, "MIX"))
    nt.links.new(col, bsdf.inputs["Base Color"])
    _set_in(bsdf, "Roughness", 0.89)
    _set_in(bsdf, "Specular IOR Level", 0.22)
    _set_in(bsdf, "Sheen Weight", 0.88)
    _set_in(bsdf, "Sheen Roughness", 0.55)
    _set_in(bsdf, "Sheen Tint", (0.85, 0.89, 0.92, 1.0))

    pile = _rgba_out(_mix_rgba(nt, 0.40, loops.outputs["Distance"], weave.outputs["Fac"], "MIX"))
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.36
    bump.inputs["Distance"].default_value = 0.0025
    nt.links.new(pile, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def _make_toiletry_mat(name: str) -> bpy.types.Material:
    """Molded consumer polypropylene/ABS toiletry container."""
    mat, nt, bsdf = _new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    grain = nt.nodes.new("ShaderNodeTexNoise")
    grain.inputs["Scale"].default_value = 180.0
    grain.inputs["Detail"].default_value = 3.0
    nt.links.new(tc.outputs["Object"], grain.inputs["Vector"])

    _set_in(bsdf, "Base Color", (0.74, 0.41, 0.28, 1.0))
    _set_in(bsdf, "IOR", 1.49)
    _set_in(bsdf, "Specular IOR Level", 0.52)
    _set_in(bsdf, "Coat Weight", 0.24)
    _set_in(bsdf, "Coat Roughness", 0.14)
    _set_in(bsdf, "Subsurface Weight", 0.12)
    _set_in(bsdf, "Subsurface Scale", 0.004)
    nt.links.new(_map_range(nt, grain.outputs["Fac"], 0.2, 0.8, 0.25, 0.34), bsdf.inputs["Roughness"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.014
    bump.inputs["Distance"].default_value = 0.0008
    nt.links.new(grain.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def _make_pan_mat(name: str) -> bpy.types.Material:
    """Galvanized / brushed utility sheet-metal dustpan."""
    mat, nt, bsdf = _new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")

    spangle = nt.nodes.new("ShaderNodeTexVoronoi")
    spangle.feature = "F1"
    spangle.inputs["Scale"].default_value = 42.0
    nt.links.new(tc.outputs["Object"], spangle.inputs["Vector"])

    scuff = nt.nodes.new("ShaderNodeTexNoise")
    scuff.inputs["Scale"].default_value = 22.0
    scuff.inputs["Detail"].default_value = 7.0
    scuff.inputs["Roughness"].default_value = 0.65
    nt.links.new(tc.outputs["Object"], scuff.inputs["Vector"])

    col = _rgba_out(
        _mix_rgba(nt, spangle.outputs["Color"], (0.47, 0.50, 0.54, 1.0), (0.61, 0.64, 0.67, 1.0), "MIX")
    )
    nt.links.new(col, bsdf.inputs["Base Color"])
    _set_in(bsdf, "Metallic", 0.91)
    nt.links.new(_map_range(nt, scuff.outputs["Fac"], 0.2, 0.8, 0.30, 0.48), bsdf.inputs["Roughness"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.032
    bump.inputs["Distance"].default_value = 0.0012
    nt.links.new(scuff.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def _make_grit_mat(name: str) -> bpy.types.Material:
    """Individual organic earthy soil clumps and mineral grit."""
    mat, nt, bsdf = _new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")

    clumps = nt.nodes.new("ShaderNodeTexVoronoi")
    clumps.feature = "F1"
    clumps.inputs["Scale"].default_value = 55.0
    nt.links.new(tc.outputs["Object"], clumps.inputs["Vector"])

    loam = nt.nodes.new("ShaderNodeTexNoise")
    loam.inputs["Scale"].default_value = 38.0
    loam.inputs["Detail"].default_value = 9.0
    loam.inputs["Roughness"].default_value = 0.78
    nt.links.new(tc.outputs["Object"], loam.inputs["Vector"])

    soil_mix = _rgba_out(
        _mix_rgba(nt, loam.outputs["Fac"], (0.13, 0.09, 0.055, 1.0), (0.31, 0.23, 0.145, 1.0), "MIX")
    )
    speck = _map_range(nt, clumps.outputs["Distance"], 0.0, 0.24, 0.45, 0.0)
    col = _rgba_out(_mix_rgba(nt, speck, soil_mix, (0.45, 0.37, 0.26, 1.0), "MIX"))
    nt.links.new(col, bsdf.inputs["Base Color"])
    nt.links.new(_map_range(nt, loam.outputs["Fac"], 0.15, 0.85, 0.82, 0.97), bsdf.inputs["Roughness"])
    _set_in(bsdf, "Specular IOR Level", 0.24)

    height = _rgba_out(_mix_rgba(nt, 0.45, loam.outputs["Fac"], clumps.outputs["Distance"], "MIX"))
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.48
    bump.inputs["Distance"].default_value = 0.004
    nt.links.new(height, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def _make_water_mat(name: str) -> bpy.types.Material:
    """Wet turquoise tiled pool water with subtle caustics and rippled Fresnel sheen."""
    mat, nt, bsdf = _new_material(name)
    geom = nt.nodes.new("ShaderNodeNewGeometry")

    # Submerged 6 cm square turquoise ceramic pool mosaic
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.0
    brick.inputs["Scale"].default_value = 4.2
    brick.inputs["Brick Width"].default_value = 0.25
    brick.inputs["Row Height"].default_value = 0.25
    brick.inputs["Mortar Size"].default_value = 0.042
    brick.inputs["Mortar Smooth"].default_value = 0.18
    brick.inputs["Color1"].default_value = (0.04, 0.41, 0.49, 1.0)
    brick.inputs["Color2"].default_value = (0.08, 0.55, 0.62, 1.0)
    brick.inputs["Mortar"].default_value = (0.28, 0.64, 0.69, 1.0)
    nt.links.new(geom.outputs["Position"], brick.inputs["Vector"])

    # Sunlit caustic web refracted over the submerged tiles
    caustics = nt.nodes.new("ShaderNodeTexVoronoi")
    caustics.feature = "DISTANCE_TO_EDGE"
    caustics.inputs["Scale"].default_value = 2.6
    nt.links.new(geom.outputs["Position"], caustics.inputs["Vector"])
    caustic_fac = _map_range(nt, caustics.outputs["Distance"], 0.0, 0.14, 0.26, 0.0)
    col = _rgba_out(_mix_rgba(nt, caustic_fac, brick.outputs["Color"], (0.58, 0.94, 0.97, 1.0), "MIX"))
    nt.links.new(col, bsdf.inputs["Base Color"])

    _set_in(bsdf, "Roughness", 0.038)
    _set_in(bsdf, "IOR", 1.333)
    _set_in(bsdf, "Specular IOR Level", 0.62)
    _set_in(bsdf, "Coat Weight", 1.0)
    _set_in(bsdf, "Coat IOR", 1.333)
    _set_in(bsdf, "Coat Roughness", 0.020)

    # Gentle multi-scale surface ripples
    rip_a = nt.nodes.new("ShaderNodeTexNoise")
    rip_a.inputs["Scale"].default_value = 4.8
    rip_a.inputs["Detail"].default_value = 4.0
    rip_a.inputs["Roughness"].default_value = 0.48
    nt.links.new(geom.outputs["Position"], rip_a.inputs["Vector"])

    rip_b = nt.nodes.new("ShaderNodeTexWave")
    rip_b.wave_type = "BANDS"
    rip_b.bands_direction = "DIAGONAL"
    rip_b.inputs["Scale"].default_value = 2.4
    rip_b.inputs["Distortion"].default_value = 4.2
    nt.links.new(geom.outputs["Position"], rip_b.inputs["Vector"])

    rip = _rgba_out(_mix_rgba(nt, 0.35, rip_a.outputs["Fac"], rip_b.outputs["Fac"], "MIX"))
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.075
    bump.inputs["Distance"].default_value = 0.008
    nt.links.new(rip, bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    if "Coat Normal" in bsdf.inputs:
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Coat Normal"])
    return mat


def _make_bristle_mat(name: str) -> bpy.types.Material:
    """Stiff natural broom bristle strands."""
    mat, nt, bsdf = _new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (95.0, 95.0, 5.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])

    fibers = nt.nodes.new("ShaderNodeTexNoise")
    fibers.inputs["Scale"].default_value = 6.0
    fibers.inputs["Detail"].default_value = 7.0
    fibers.inputs["Roughness"].default_value = 0.72
    nt.links.new(mp.outputs["Vector"], fibers.inputs["Vector"])

    col = _rgba_out(
        _mix_rgba(nt, fibers.outputs["Fac"], (0.36, 0.26, 0.13, 1.0), (0.64, 0.51, 0.29, 1.0), "MIX")
    )
    nt.links.new(col, bsdf.inputs["Base Color"])
    nt.links.new(_map_range(nt, fibers.outputs["Fac"], 0.2, 0.8, 0.70, 0.88), bsdf.inputs["Roughness"])
    _set_in(bsdf, "Sheen Weight", 0.28)
    _set_in(bsdf, "Specular IOR Level", 0.32)

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.44
    bump.inputs["Distance"].default_value = 0.003
    nt.links.new(fibers.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def _make_simple_mat(
    name: str,
    rgb: tuple[float, float, float, float],
    roughness: float = 0.55,
    metallic: float = 0.0,
    coat: float = 0.0,
    subsurface: float = 0.0,
    emission: tuple[float, float, float, float] | None = None,
    emission_strength: float = 0.0,
    noise_var: float = 0.0,
    bump_strength: float = 0.0,
    alpha: float = 1.0,
    ior: float = 1.45,
) -> bpy.types.Material:
    mat, nt, bsdf = _new_material(name)
    _set_in(bsdf, "Base Color", rgb)
    _set_in(bsdf, "Roughness", roughness)
    _set_in(bsdf, "Metallic", metallic)
    _set_in(bsdf, "Coat Weight", coat)
    _set_in(bsdf, "IOR", ior)
    _set_in(bsdf, "Alpha", alpha)
    if subsurface > 0.0:
        _set_in(bsdf, "Subsurface Weight", subsurface)
        _set_in(bsdf, "Subsurface Scale", 0.006)
    if emission is not None and emission_strength > 0.0:
        _set_in(bsdf, "Emission Color", emission)
        _set_in(bsdf, "Emission Strength", emission_strength)
    if noise_var > 0.0 or bump_strength > 0.0:
        geom = nt.nodes.new("ShaderNodeNewGeometry")
        n = nt.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = 14.0
        n.inputs["Detail"].default_value = 6.0
        nt.links.new(geom.outputs["Position"], n.inputs["Vector"])
        if noise_var > 0.0:
            dark = (rgb[0] * (1.0 - noise_var), rgb[1] * (1.0 - noise_var), rgb[2] * (1.0 - noise_var), 1.0)
            col = _rgba_out(_mix_rgba(nt, n.outputs["Fac"], dark, rgb, "MIX"))
            nt.links.new(col, bsdf.inputs["Base Color"])
        if bump_strength > 0.0:
            bump = nt.nodes.new("ShaderNodeBump")
            bump.inputs["Strength"].default_value = bump_strength
            bump.inputs["Distance"].default_value = 0.004
            nt.links.new(n.outputs["Fac"], bump.inputs["Height"])
            nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    if alpha < 0.99 and hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    return mat


def _build_role_materials(case: str, library: Path) -> dict[str, bpy.types.Material]:
    tex_dir = Path(library) / "background" / "common" / "home_b" / "textures"
    prefix = f"Study_{case}_"

    if case == "drawer":
        floor_tex = _resolve_tex_triplet(tex_dir, "floor_tile_03", "floor_tile_03")
        wall_tex = _resolve_tex_triplet(tex_dir, "wall_03", "wall_03")
        floor_mat = _make_pbr_map_material(
            prefix + "floor",
            floor_tex,
            tile_meters=0.60,
            tint=(0.98, 0.97, 0.95, 1.0),
            rgh_range=(0.28, 0.56),
            normal_strength=0.55,
            macro_var=0.04,
            fallback_rgb=(0.68, 0.67, 0.64, 1.0),
        )
        wall_mat = _make_pbr_map_material(
            prefix + "wall",
            wall_tex,
            tile_meters=0.85,
            lift_color=(0.91, 0.90, 0.87, 1.0),
            lift_fac=0.28,
            rgh_range=(0.56, 0.84),
            normal_strength=0.45,
            macro_var=0.03,
            fallback_rgb=(0.86, 0.85, 0.82, 1.0),
        )
    else:
        floor_tex = _resolve_tex_triplet(tex_dir, "floor_tile_04", "floor_tile_03")
        wall_tex = _resolve_tex_triplet(tex_dir, "wall_04", "wall_03")
        floor_mat = _make_pbr_map_material(
            prefix + "floor",
            floor_tex,
            tile_meters=0.72,
            tint=(0.96, 0.93, 0.88, 1.0),
            rgh_range=(0.50, 0.78),
            normal_strength=0.65,
            macro_var=0.07,
            fallback_rgb=(0.73, 0.70, 0.64, 1.0),
        )
        wall_mat = _make_pbr_map_material(
            prefix + "wall",
            wall_tex,
            tile_meters=1.15,
            tint=(0.95, 0.92, 0.86, 1.0),
            lift_color=(0.89, 0.85, 0.78, 1.0),
            lift_fac=0.22,
            rgh_range=(0.68, 0.92),
            normal_strength=0.68,
            macro_var=0.08,
            fallback_rgb=(0.84, 0.80, 0.73, 1.0),
        )

    stone_tex = _resolve_tex_triplet(tex_dir, "floor_tile_04", "floor_tile_03")
    gardenstone_mat = _make_pbr_map_material(
        prefix + "gardenstone",
        stone_tex,
        tile_meters=0.68,
        tint=(0.93, 0.90, 0.83, 1.0),
        rgh_range=(0.56, 0.84),
        normal_strength=0.70,
        macro_var=0.09,
        fallback_rgb=(0.74, 0.71, 0.64, 1.0),
    )

    return {
        "floor": floor_mat,
        "wall": wall_mat,
        "ceramic": _make_ceramic_mat(prefix + "ceramic"),
        "doors": _make_doors_mat(prefix + "doors"),
        "oak": _make_wood_mat(
            prefix + "oak",
            light_rgb=(0.50, 0.35, 0.20, 1.0),
            dark_rgb=(0.28, 0.18, 0.09, 1.0),
            rgh_range=(0.44, 0.64),
            coat=0.08,
            bump_strength=0.055,
        ),
        "chrome": _make_chrome_mat(prefix + "chrome"),
        "terry": _make_terry_mat(prefix + "terry", (0.30, 0.44, 0.55, 1.0)),
        "toiletry": _make_toiletry_mat(prefix + "toiletry"),
        "pan": _make_pan_mat(prefix + "pan"),
        "grit": _make_grit_mat(prefix + "grit"),
        "water": _make_water_mat(prefix + "water"),
        "brush": _make_wood_mat(
            prefix + "brush",
            light_rgb=(0.58, 0.43, 0.26, 1.0),
            dark_rgb=(0.39, 0.27, 0.14, 1.0),
            rgh_range=(0.36, 0.52),
            scale=(14.0, 14.0, 2.0),
            coat=0.16,
            bump_strength=0.038,
        ),
        "bristle": _make_bristle_mat(prefix + "bristle"),
        "gardenstone": gardenstone_mat,
    }


# ---------------------------------------------------------------------------
# Pure bmesh geometry builders (headless-safe, no bpy.ops)
# ---------------------------------------------------------------------------


def _apply_metric_box_uv(bm: bmesh.types.BMesh, scale: float = 1.0) -> None:
    uv_layer = bm.loops.layers.uv.verify()
    bm.faces.ensure_lookup_table()
    for f in bm.faces:
        nx, ny, nz = abs(f.normal.x), abs(f.normal.y), abs(f.normal.z)
        for loop in f.loops:
            co = loop.vert.co
            if nz >= nx and nz >= ny:
                u, v = co.x * scale, co.y * scale
            elif nx >= ny:
                u, v = co.y * scale, co.z * scale
            else:
                u, v = co.x * scale, co.z * scale
            loop[uv_layer].uv = (u, v)


def _link_bmesh(
    scene: bpy.types.Scene,
    name: str,
    bm: bmesh.types.BMesh,
    mat: bpy.types.Material,
    props: list[str],
    smooth: bool = False,
    shadow: bool = True,
    uv_scale: float = 1.0,
) -> bpy.types.Object:
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    _apply_metric_box_uv(bm, scale=uv_scale)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    if smooth:
        for p in mesh.polygons:
            p.use_smooth = True
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    if hasattr(obj, "visible_shadow"):
        obj.visible_shadow = shadow
    scene.collection.objects.link(obj)
    props.append(obj.name)
    return obj


def _add_box(
    bm: bmesh.types.BMesh,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    z0: float,
    z1: float,
    bevel: float = 0.0,
    rot_z: float = 0.0,
) -> None:
    sx, sy, sz = abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)
    cx, cy, cz = 0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.5 * (z0 + z1)
    mat = (
        Matrix.Translation((cx, cy, cz))
        @ Matrix.Rotation(rot_z, 4, "Z")
        @ Matrix.Diagonal((sx, sy, sz, 1.0))
    )
    res = bmesh.ops.create_cube(bm, size=1.0, matrix=mat)
    if bevel > 0.0:
        vset = set(res["verts"])
        edges = [e for e in bm.edges if e.verts[0] in vset and e.verts[1] in vset]
        bmesh.ops.bevel(
            bm,
            geom=edges,
            offset=min(bevel, 0.25 * min(sx, sy, sz)),
            offset_type="OFFSET",
            segments=2,
            profile=0.5,
            affect="EDGES",
            clamp_overlap=True,
        )


def _add_cyl(
    bm: bmesh.types.BMesh,
    p0: tuple[float, float, float],
    p1: tuple[float, float, float],
    r0: float,
    r1: float | None = None,
    segs: int = 16,
    cap: bool = True,
) -> None:
    v0, v1 = Vector(p0), Vector(p1)
    delta = v1 - v0
    length = delta.length
    if length < 1e-6:
        return
    r_top = r0 if r1 is None else r1
    rot = Vector((0.0, 0.0, 1.0)).rotation_difference(delta.normalized()).to_matrix().to_4x4()
    mat = Matrix.Translation(0.5 * (v0 + v1)) @ rot
    bmesh.ops.create_cone(
        bm,
        cap_ends=cap,
        cap_tris=False,
        segments=segs,
        radius1=r0,
        radius2=r_top,
        depth=length,
        matrix=mat,
    )


def _add_leaf(
    bm: bmesh.types.BMesh,
    origin: Vector,
    direction: Vector,
    up_hint: Vector,
    length: float,
    width: float,
    arch: float = 0.16,
) -> None:
    """Arched 6-vertex botanical leaf blade (no sphere blobs)."""
    fwd = direction.normalized()
    side = fwd.cross(up_hint)
    if side.length < 1e-4:
        side = fwd.cross(Vector((1.0, 0.0, 0.0)))
    side.normalize()
    up = side.cross(fwd).normalized()

    p0 = origin
    p1 = origin + fwd * (0.35 * length) + side * (0.46 * width) + up * (0.08 * length)
    p2 = origin + fwd * (0.35 * length) - side * (0.46 * width) + up * (0.08 * length)
    p3 = origin + fwd * (0.72 * length) + side * (0.34 * width) + up * ((0.06 - arch * 0.45) * length)
    p4 = origin + fwd * (0.72 * length) - side * (0.34 * width) + up * ((0.06 - arch * 0.45) * length)
    p5 = origin + fwd * length - up * (arch * length)

    vs = [bm.verts.new(p) for p in (p0, p1, p2, p3, p4, p5)]
    bm.faces.new((vs[0], vs[1], vs[3], vs[4], vs[2]))
    bm.faces.new((vs[3], vs[5], vs[4]))


def _add_draped_towel(
    bm: bmesh.types.BMesh,
    x0: float,
    x1: float,
    y_bar: float,
    z_bar: float,
    r_bar: float = 0.016,
    drop_front: float = 0.44,
    drop_back: float = 0.40,
) -> None:
    """Pleated folded towel draped smoothly over a horizontal wall rail."""
    nx, nz_hang, n_arc = 18, 12, 8
    thickness = 0.008
    # Build centerline profile from front hem -> up -> over bar -> down back hem
    profile: list[tuple[float, float, float]] = []
    for j in range(nz_hang):
        t = j / nz_hang
        z = z_bar - drop_front * (1.0 - t)
        y = y_bar - r_bar - 0.004 * (1.0 - t)
        profile.append((y, z, 1.0 - t))
    for j in range(n_arc + 1):
        ang = math.pi * (1.0 - j / n_arc)
        y = y_bar + r_bar * math.cos(ang)
        z = z_bar + r_bar * math.sin(ang)
        profile.append((y, z, 0.0))
    for j in range(1, nz_hang + 1):
        t = j / nz_hang
        z = z_bar - drop_back * t
        y = y_bar + r_bar + 0.003 * t
        profile.append((y, z, t))

    rows: list[list[bmesh.types.BMVert]] = []
    for y0, z0, hang_w in profile:
        row: list[bmesh.types.BMVert] = []
        for i in range(nx + 1):
            u = i / nx
            x = x0 + (x1 - x0) * u
            pleat = 0.007 * hang_w * math.sin(u * math.pi * 4.0)
            edge_taper = 0.003 * hang_w * math.sin(u * math.pi)
            row.append(bm.verts.new((x, y0 + pleat, z0 - edge_taper)))
        rows.append(row)

    for r in range(len(rows) - 1):
        for i in range(nx):
            bm.faces.new((rows[r][i], rows[r][i + 1], rows[r + 1][i + 1], rows[r + 1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    res = bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=thickness)
    del res


def _add_planter_pot(
    bm: bmesh.types.BMesh,
    cx: float,
    cy: float,
    z0: float,
    height: float,
    r_bot: float,
    r_top: float,
    segs: int = 24,
) -> None:
    _add_cyl(bm, (cx, cy, z0), (cx, cy, z0 + height - 0.025), r_bot, r_top, segs=segs)
    _add_cyl(bm, (cx, cy, z0 + height - 0.025), (cx, cy, z0 + height), r_top * 1.04, r_top * 1.04, segs=segs)


# ---------------------------------------------------------------------------
# Lighting, World, and Color Management
# ---------------------------------------------------------------------------


def _clear_existing_lights(scene: bpy.types.Scene) -> None:
    for obj in list(scene.objects):
        if obj.type == "LIGHT":
            for col in list(obj.users_collection):
                col.objects.unlink(obj)
            if obj.users == 0:
                bpy.data.objects.remove(obj)


def _aim_object(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    direction = Vector(target) - obj.location
    if direction.length > 1e-6:
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _add_area_light(
    scene: bpy.types.Scene,
    name: str,
    location: tuple[float, float, float],
    target: tuple[float, float, float],
    energy: float,
    color: tuple[float, float, float],
    size_x: float,
    size_y: float,
    spread_deg: float = 120.0,
) -> bpy.types.Object:
    ldata = bpy.data.lights.new(name=name, type="AREA")
    ldata.shape = "RECTANGLE"
    ldata.size = size_x
    ldata.size_y = size_y
    ldata.energy = energy
    ldata.color = color
    if hasattr(ldata, "spread"):
        ldata.spread = math.radians(spread_deg)
    obj = bpy.data.objects.new(name=name, object_data=ldata)
    obj.location = location
    _aim_object(obj, target)
    scene.collection.objects.link(obj)
    return obj


def _add_sun_light(
    scene: bpy.types.Scene,
    name: str,
    elevation_deg: float,
    azimuth_deg: float,
    energy: float,
    color: tuple[float, float, float],
    angle_deg: float = 2.5,
) -> bpy.types.Object:
    ldata = bpy.data.lights.new(name=name, type="SUN")
    ldata.energy = energy
    ldata.color = color
    ldata.angle = math.radians(angle_deg)
    el = math.radians(elevation_deg)
    az = math.radians(azimuth_deg)
    sun_from = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    obj = bpy.data.objects.new(name=name, object_data=ldata)
    obj.location = sun_from * 6.0
    _aim_object(obj, (0.0, 0.0, 0.0))
    scene.collection.objects.link(obj)
    return obj


def _configure_render_and_cm(scene: bpy.types.Scene) -> None:
    vs = scene.view_settings
    for transform in ("AgX", "Filmic"):
        try:
            vs.view_transform = transform
            break
        except TypeError:
            continue
    for look in ("AgX - Base Contrast", "None"):
        try:
            vs.look = look
            break
        except TypeError:
            continue
    vs.exposure = 0.0
    vs.gamma = 1.0
    vs.use_curve_mapping = False
    if hasattr(vs, "use_white_balance"):
        vs.use_white_balance = True
        vs.white_balance_temperature = 6500.0
        vs.white_balance_tint = 0.0

    eevee = getattr(scene, "eevee", None)
    if eevee is not None:
        for attr, val in (
            ("use_shadows", True),
            ("use_raytracing", True),
            ("shadow_resolution_scale", 1.0),
        ):
            if hasattr(eevee, attr):
                setattr(eevee, attr, val)

    cycles = getattr(scene, "cycles", None)
    if cycles is not None:
        for attr, val in (
            ("max_bounces", 8),
            ("diffuse_bounces", 4),
            ("glossy_bounces", 4),
            ("transmission_bounces", 6),
            ("sample_clamp_indirect", 8.0),
        ):
            if hasattr(cycles, attr):
                setattr(cycles, attr, val)


def _setup_world_sky(
    scene: bpy.types.Scene,
    name: str,
    strength: float,
    elevation_deg: float,
    rotation_deg: float,
) -> None:
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
    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    if hasattr(sky, "sun_disc"):
        sky.sun_disc = False
    if hasattr(sky, "sun_elevation"):
        sky.sun_elevation = math.radians(elevation_deg)
    if hasattr(sky, "sun_rotation"):
        sky.sun_rotation = math.radians(rotation_deg)
    if hasattr(sky, "air_density"):
        sky.air_density = 1.1
    if hasattr(sky, "dust_density"):
        sky.dust_density = 1.2
    if hasattr(sky, "ozone_density"):
        sky.ozone_density = 1.2
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    scene.world = world


# ---------------------------------------------------------------------------
# Case 1: Residential Bathroom ('drawer')
# ---------------------------------------------------------------------------


def _build_bathroom(
    scene: bpy.types.Scene,
    mats: dict[str, bpy.types.Material],
    props: list[str],
) -> None:
    trim_mat = _make_simple_mat("Study_drawer_trim", (0.90, 0.895, 0.875, 1.0), roughness=0.34, coat=0.14)
    ceil_mat = _make_simple_mat("Study_drawer_ceiling", (0.93, 0.925, 0.91, 1.0), roughness=0.86)
    mirror_mat = _make_simple_mat("Study_drawer_mirror", (0.94, 0.96, 0.95, 1.0), roughness=0.015, metallic=1.0)
    glass_mat = _make_simple_mat(
        "Study_drawer_glass", (0.94, 0.98, 0.99, 1.0), roughness=0.03, alpha=0.16, ior=1.52
    )
    opal_mat = _make_simple_mat(
        "Study_drawer_opal",
        (0.98, 0.95, 0.89, 1.0),
        roughness=0.22,
        emission=(1.0, 0.94, 0.84, 1.0),
        emission_strength=3.2,
    )
    towel_cream_mat = _make_terry_mat("Study_drawer_rail_towel", (0.83, 0.80, 0.74, 1.0))
    pot_mat = _make_simple_mat(
        "Study_drawer_pot", (0.76, 0.72, 0.66, 1.0), roughness=0.66, noise_var=0.08, bump_strength=0.04
    )
    soil_mat = _make_simple_mat(
        "Study_drawer_soil", (0.14, 0.10, 0.07, 1.0), roughness=0.94, noise_var=0.15, bump_strength=0.25
    )
    leaf_mat = _make_simple_mat(
        "Study_drawer_leaf",
        (0.16, 0.34, 0.17, 1.0),
        roughness=0.38,
        subsurface=0.22,
        noise_var=0.12,
        bump_strength=0.04,
    )
    ext_mat = _make_simple_mat(
        "Study_drawer_exterior",
        (0.58, 0.70, 0.56, 1.0),
        roughness=0.85,
        emission=(0.76, 0.84, 0.92, 1.0),
        emission_strength=1.4,
    )

    # Room shell: back wall y>=1.18, left wall x<=-1.85, right wall x>=2.25, ceiling z=2.75.
    # No floor slab created (existing physics floor receives mats['floor']).
    wall_bm = bmesh.new()
    # Back wall
    _add_box(wall_bm, -2.03, 2.43, 1.18, 1.36, 0.0, 2.75)
    # Left wall around broad upper window opening y=[-1.45, 0.55], z=[1.25, 2.35]
    _add_box(wall_bm, -2.03, -1.85, -3.60, 1.18, 0.0, 1.25)
    _add_box(wall_bm, -2.03, -1.85, -3.60, 1.18, 2.35, 2.75)
    _add_box(wall_bm, -2.03, -1.85, 0.55, 1.18, 1.25, 2.35)
    _add_box(wall_bm, -2.03, -1.85, -3.60, -1.45, 1.25, 2.35)
    # Right and front walls (outside camera at (1.75, -2.75, 1.9) for realistic bounce)
    _add_box(wall_bm, 2.25, 2.43, -3.60, 1.18, 0.0, 2.75)
    _add_box(wall_bm, -2.03, 2.43, -3.78, -3.60, 0.0, 2.75)
    _link_bmesh(scene, "Bath_Walls", wall_bm, mats["wall"], props, uv_scale=1.18)

    ceil_bm = bmesh.new()
    _add_box(ceil_bm, -2.03, 2.43, -3.60, 1.36, 2.75, 2.90)
    _link_bmesh(scene, "Bath_Ceiling", ceil_bm, ceil_mat, props)

    # Baseboards, crown cornice, wainscot chair-rail, and window casing + mullions
    trim_bm = bmesh.new()
    # Baseboards (flush with walls, outside vanity footprint)
    _add_box(trim_bm, -1.85, 2.25, 1.162, 1.18, 0.0, 0.11, bevel=0.004)
    _add_box(trim_bm, -1.85, -1.832, -3.60, 1.162, 0.0, 0.11, bevel=0.004)
    _add_box(trim_bm, 2.232, 2.25, -3.60, 1.162, 0.0, 0.11, bevel=0.004)
    # Subtle wainscot cap at z=1.12
    _add_box(trim_bm, -1.85, -1.825, -3.60, 1.16, 1.12, 1.155, bevel=0.005)
    _add_box(trim_bm, -1.85, 2.25, 1.155, 1.18, 1.12, 1.155, bevel=0.005)
    # Crown trim
    _add_box(trim_bm, -1.85, 2.25, 1.13, 1.18, 2.68, 2.75, bevel=0.006)
    _add_box(trim_bm, -1.85, -1.80, -3.60, 1.18, 2.68, 2.75, bevel=0.006)
    _add_box(trim_bm, 2.20, 2.25, -3.60, 1.18, 2.68, 2.75, bevel=0.006)
    # Upper window casing, deep sill, sash, and mullions at x=-1.85
    _add_box(trim_bm, -2.04, -1.80, -1.53, 0.63, 1.215, 1.255, bevel=0.006)  # sill
    _add_box(trim_bm, -1.87, -1.82, -1.53, 0.63, 2.35, 2.43, bevel=0.005)  # top casing
    _add_box(trim_bm, -1.87, -1.82, -1.53, -1.45, 1.255, 2.35, bevel=0.005)  # south casing
    _add_box(trim_bm, -1.87, -1.82, 0.55, 0.63, 1.255, 2.35, bevel=0.005)  # north casing
    # Inner sash perimeter + mullions
    _add_box(trim_bm, -1.98, -1.90, -1.45, 0.55, 1.255, 1.30, bevel=0.003)
    _add_box(trim_bm, -1.98, -1.90, -1.45, 0.55, 2.305, 2.35, bevel=0.003)
    _add_box(trim_bm, -1.98, -1.90, -1.45, -1.40, 1.30, 2.305, bevel=0.003)
    _add_box(trim_bm, -1.98, -1.90, 0.50, 0.55, 1.30, 2.305, bevel=0.003)
    for my in (-0.80, -0.10):
        _add_box(trim_bm, -1.96, -1.91, my - 0.018, my + 0.018, 1.30, 2.305, bevel=0.002)
    _add_box(trim_bm, -1.96, -1.91, -1.40, 0.50, 1.98, 2.012, bevel=0.002)
    _link_bmesh(scene, "Bath_Window_And_Trim", trim_bm, trim_mat, props)

    # Non-shadow-casting window glass + bright exterior backdrop beyond window
    glass_bm = bmesh.new()
    _add_box(glass_bm, -1.945, -1.935, -1.40, 0.50, 1.30, 2.305)
    _link_bmesh(scene, "Bath_Window_Glass", glass_bm, glass_mat, props, shadow=False)

    ext_bm = bmesh.new()
    _add_box(ext_bm, -4.40, -4.32, -4.5, 3.8, -0.5, 4.6)
    _link_bmesh(scene, "Bath_Exterior_Vista", ext_bm, ext_mat, props, shadow=False)

    # Framed wall mirror over sink & vanity (y >= 1.15, z = 1.17..2.06)
    mframe_bm = bmesh.new()
    mx0, mx1, mz0, mz1, bw = -1.04, 0.84, 1.17, 2.06, 0.032
    _add_box(mframe_bm, mx0, mx1, 1.152, 1.18, mz0, mz0 + bw, bevel=0.004)
    _add_box(mframe_bm, mx0, mx1, 1.152, 1.18, mz1 - bw, mz1, bevel=0.004)
    _add_box(mframe_bm, mx0, mx0 + bw, 1.152, 1.18, mz0 + bw, mz1 - bw, bevel=0.004)
    _add_box(mframe_bm, mx1 - bw, mx1, 1.152, 1.18, mz0 + bw, mz1 - bw, bevel=0.004)
    # Brushed chrome linear sconce backplate above mirror
    _add_box(mframe_bm, -0.66, 0.46, 1.155, 1.18, 2.13, 2.18, bevel=0.004)
    for sx in (-0.54, 0.34):
        _add_cyl(mframe_bm, (sx, 1.16, 2.155), (sx, 1.105, 2.155), 0.011, 0.011, segs=12)
    # Distant towel rail on back wall far right (x=1.22..1.74, clear of vanity x<=1.00)
    for rx in (1.24, 1.72):
        _add_cyl(mframe_bm, (rx, 1.18, 1.11), (rx, 1.165, 1.11), 0.026, 0.024, segs=18)
        _add_cyl(mframe_bm, (rx, 1.168, 1.11), (rx, 1.105, 1.11), 0.009, 0.009, segs=14)
    _add_cyl(mframe_bm, (1.22, 1.105, 1.11), (1.74, 1.105, 1.11), 0.011, 0.011, segs=16)
    _link_bmesh(scene, "Bath_Chrome_Fixtures", mframe_bm, mats["chrome"], props, smooth=True)

    mirror_bm = bmesh.new()
    _add_box(mirror_bm, mx0 + bw, mx1 - bw, 1.162, 1.174, mz0 + bw, mz1 - bw)
    _link_bmesh(scene, "Bath_Mirror_Glass", mirror_bm, mirror_mat, props)

    sconce_bm = bmesh.new()
    _add_cyl(sconce_bm, (-0.62, 1.095, 2.155), (0.42, 1.095, 2.155), 0.019, 0.019, segs=16)
    _link_bmesh(scene, "Bath_Sconce_Diffuser", sconce_bm, opal_mat, props, smooth=True, shadow=False)

    # Draped bath towel on the distant rail
    towel_bm = bmesh.new()
    _add_draped_towel(towel_bm, 1.32, 1.64, 1.105, 1.11, r_bar=0.015, drop_front=0.44, drop_back=0.39)
    _link_bmesh(scene, "Bath_Distant_Towel", towel_bm, towel_cream_mat, props, smooth=True)

    # Corner stoneware planter with architectural snake-plant blades (x=-1.56, y=0.88; well clear of vanity & robot)
    px, py = -1.56, 0.88
    pot_bm = bmesh.new()
    _add_planter_pot(pot_bm, px, py, 0.0, 0.28, 0.095, 0.125, segs=24)
    _link_bmesh(scene, "Bath_Corner_Planter", pot_bm, pot_mat, props, smooth=True)

    soil_bm = bmesh.new()
    _add_cyl(soil_bm, (px, py, 0.23), (px, py, 0.255), 0.112, 0.115, segs=20)
    _link_bmesh(scene, "Bath_Planter_Soil", soil_bm, soil_mat, props)

    rng = random.Random(1162)
    plant_bm = bmesh.new()
    for i in range(13):
        ang = i * 2.39996 + rng.uniform(-0.15, 0.15)
        rad = rng.uniform(0.01, 0.075)
        ox = px + rad * math.cos(ang)
        oy = py + rad * math.sin(ang)
        tilt = rng.uniform(0.08, 0.26)
        direction = Vector((math.cos(ang) * tilt, math.sin(ang) * tilt, 1.0)).normalized()
        up_hint = Vector((-math.sin(ang), math.cos(ang), 0.0))
        _add_leaf(
            plant_bm,
            Vector((ox, oy, 0.245)),
            direction,
            up_hint,
            length=rng.uniform(0.32, 0.56),
            width=rng.uniform(0.048, 0.072),
            arch=rng.uniform(0.08, 0.18),
        )
    _link_bmesh(scene, "Bath_Corner_Houseplant", plant_bm, leaf_mat, props, smooth=True)

    # Bathroom daylighting + bounce (cycles & Eevee Next balanced)
    _setup_world_sky(scene, "Study_Bath_World", strength=0.45, elevation_deg=36.0, rotation_deg=235.0)
    _add_area_light(
        scene,
        "Bath_Window_Key",
        location=(-1.78, -0.45, 1.80),
        target=(0.15, 0.55, 0.85),
        energy=255.0,
        color=(0.94, 0.97, 1.0),
        size_x=1.85,
        size_y=1.00,
        spread_deg=105.0,
    )
    _add_sun_light(
        scene,
        "Bath_Window_Sun",
        elevation_deg=34.0,
        azimuth_deg=205.0,
        energy=1.35,
        color=(1.0, 0.96, 0.89),
        angle_deg=5.5,
    )
    _add_area_light(
        scene,
        "Bath_Vanity_Light",
        location=(-0.10, 1.05, 2.08),
        target=(-0.05, 0.55, 0.88),
        energy=44.0,
        color=(1.0, 0.93, 0.83),
        size_x=1.18,
        size_y=0.09,
        spread_deg=128.0,
    )
    _add_area_light(
        scene,
        "Bath_Room_Bounce",
        location=(1.25, -1.05, 2.55),
        target=(-0.20, 0.35, 0.65),
        energy=78.0,
        color=(0.97, 0.96, 0.94),
        size_x=2.40,
        size_y=2.10,
        spread_deg=145.0,
    )


# ---------------------------------------------------------------------------
# Case 2: Garden Poolside ('pool')
# ---------------------------------------------------------------------------


def _add_shrub(
    stem_bm: bmesh.types.BMesh,
    leaf_bm: bmesh.types.BMesh,
    cx: float,
    cy: float,
    z0: float,
    radius: float,
    height: float,
    rng: random.Random,
) -> None:
    """Branching woody shrub with layered individual leaf sprays."""
    n_stems = max(6, int(radius * 18))
    for i in range(n_stems):
        ang = (2.0 * math.pi * i / n_stems) + rng.uniform(-0.25, 0.25)
        spread = rng.uniform(0.35, 0.95) * radius
        h = rng.uniform(0.55, 1.0) * height
        base = Vector((cx + rng.uniform(-0.04, 0.04), cy + rng.uniform(-0.04, 0.04), z0 - 0.02))
        mid = Vector((cx + math.cos(ang) * spread * 0.55, cy + math.sin(ang) * spread * 0.55, z0 + h * 0.55))
        tip = Vector((cx + math.cos(ang) * spread, cy + math.sin(ang) * spread, z0 + h))
        _add_cyl(stem_bm, tuple(base), tuple(mid), 0.011, 0.007, segs=6, cap=False)
        _add_cyl(stem_bm, tuple(mid), tuple(tip), 0.007, 0.004, segs=6, cap=False)

        for k in range(8):
            t = 0.35 + 0.65 * (k / 7.0)
            pos = mid.lerp(tip, (t - 0.35) / 0.65)
            la = ang + rng.uniform(-1.3, 1.3)
            elev = rng.uniform(0.15, 0.85)
            ldir = Vector((math.cos(la) * math.cos(elev), math.sin(la) * math.cos(elev), math.sin(elev)))
            _add_leaf(
                leaf_bm,
                pos,
                ldir,
                Vector((0.0, 0.0, 1.0)),
                length=rng.uniform(0.11, 0.19),
                width=rng.uniform(0.055, 0.095),
                arch=rng.uniform(0.14, 0.28),
            )


def _add_climbing_vine(
    stem_bm: bmesh.types.BMesh,
    leaf_bm: bmesh.types.BMesh,
    x_root: float,
    y_wall: float,
    z0: float,
    z_top: float,
    rng: random.Random,
) -> None:
    """Organic climbing vine clinging to the front face of the boundary wall."""
    segs = 11
    prev = Vector((x_root, y_wall - 0.04, z0))
    for s in range(1, segs + 1):
        t = s / segs
        nx = prev.x + rng.uniform(-0.16, 0.16)
        ny = y_wall - rng.uniform(0.018, 0.042)
        nz = z0 + (z_top - z0) * t
        curr = Vector((nx, ny, nz))
        _add_cyl(stem_bm, tuple(prev), tuple(curr), 0.008 * (1.1 - 0.5 * t), 0.006 * (1.1 - 0.5 * t), segs=6)

        for j in range(5):
            pt = prev.lerp(curr, (j + 0.5) / 5.0)
            lx = rng.uniform(-0.85, 0.85)
            ly = rng.uniform(-0.85, -0.25)
            lz = rng.uniform(-0.35, 0.45)
            _add_leaf(
                leaf_bm,
                pt,
                Vector((lx, ly, lz)).normalized(),
                Vector((0.0, -1.0, 0.3)),
                length=rng.uniform(0.09, 0.15),
                width=rng.uniform(0.065, 0.105),
                arch=rng.uniform(0.16, 0.30),
            )
        prev = curr


def _build_pool_garden(
    scene: bpy.types.Scene,
    mats: dict[str, bpy.types.Material],
    props: list[str],
) -> None:
    lawn_mat = _make_simple_mat(
        "Study_pool_lawn", (0.16, 0.29, 0.11, 1.0), roughness=0.88, noise_var=0.18, bump_strength=0.18
    )
    mulch_mat = _make_simple_mat(
        "Study_pool_mulch", (0.15, 0.10, 0.065, 1.0), roughness=0.95, noise_var=0.22, bump_strength=0.35
    )
    wood_stem_mat = _make_simple_mat(
        "Study_pool_woody", (0.20, 0.14, 0.09, 1.0), roughness=0.86, noise_var=0.15, bump_strength=0.18
    )
    foliage_mat = _make_simple_mat(
        "Study_pool_foliage",
        (0.14, 0.30, 0.11, 1.0),
        roughness=0.44,
        subsurface=0.24,
        noise_var=0.20,
        bump_strength=0.06,
    )
    vine_leaf_mat = _make_simple_mat(
        "Study_pool_vine_leaf",
        (0.11, 0.26, 0.09, 1.0),
        roughness=0.38,
        subsurface=0.22,
        noise_var=0.18,
        bump_strength=0.05,
    )
    iron_mat = _make_simple_mat(
        "Study_pool_iron", (0.12, 0.13, 0.14, 1.0), roughness=0.42, metallic=0.88, bump_strength=0.03
    )
    cushion_mat = _make_simple_mat(
        "Study_pool_cushion", (0.86, 0.84, 0.78, 1.0), roughness=0.84, noise_var=0.05, bump_strength=0.08
    )
    terra_mat = _make_simple_mat(
        "Study_pool_terracotta", (0.56, 0.27, 0.16, 1.0), roughness=0.72, noise_var=0.12, bump_strength=0.08
    )

    # 1. Outer lawn surround strictly outside patio/pool footprint (hollow center, z=-0.04; no floor replacement)
    lawn_bm = bmesh.new()
    _add_box(lawn_bm, -9.0, 10.0, 2.22, 8.50, -0.10, -0.04)  # north
    _add_box(lawn_bm, -9.0, -1.72, -4.50, 2.22, -0.10, -0.04)  # west
    _add_box(lawn_bm, 2.52, 10.0, -4.50, 2.22, -0.10, -0.04)  # east (past pool x=2.10)
    _add_box(lawn_bm, -9.0, 10.0, -9.00, -2.60, -0.10, -0.04)  # south behind camera
    _link_bmesh(scene, "Pool_Outer_Lawn", lawn_bm, lawn_mat, props)

    # 2. Mulched shrub beds (y > 2.18 and x < -1.94)
    mulch_bm = bmesh.new()
    _add_box(mulch_bm, -7.0, 8.0, 2.22, 2.86, -0.04, 0.03)
    _add_box(mulch_bm, -3.76, -1.94, 0.20, 2.22, -0.04, 0.03)
    _link_bmesh(scene, "Pool_Mulch_Beds", mulch_bm, mulch_mat, props)

    # 3. Cut-stone bed curbing, wall coping, and far-right lounger terrace pad (outside x=±1.50 / y>2.1)
    stone_bm = bmesh.new()
    _add_box(stone_bm, -7.0, 8.0, 2.15, 2.24, -0.04, 0.075, bevel=0.008)  # back curb
    _add_box(stone_bm, -1.96, -1.87, 0.18, 2.15, -0.04, 0.075, bevel=0.008)  # left curb
    # Far-right stone terrace extension for poolside furniture (x >= 2.65, clear of pool x <= 2.10)
    _add_box(stone_bm, 2.65, 4.65, -0.15, 2.15, -0.04, -0.004, bevel=0.006)
    # Boundary wall stone coping caps (split at gate opening x=[-3.10, -2.05])
    _add_box(stone_bm, -7.05, -3.05, 2.82, 3.14, 2.15, 2.22, bevel=0.01)
    _add_box(stone_bm, -2.10, 8.05, 2.82, 3.14, 2.15, 2.22, bevel=0.01)
    for px in (-5.6, -3.15, -2.00, 0.55, 3.15, 5.75):
        _add_box(stone_bm, px - 0.19, px + 0.19, 2.79, 3.17, 2.22, 2.29, bevel=0.01)
    # Gate threshold step
    _add_box(stone_bm, -3.12, -2.03, 2.80, 3.14, -0.04, 0.025, bevel=0.006)
    _link_bmesh(scene, "Pool_Stone_Curbing_And_Coping", stone_bm, mats["gardenstone"], props, uv_scale=1.45)

    # 4. Boundary plaster/masonry wall at y=2.86..3.10 with pilasters and garden gate opening
    wall_bm = bmesh.new()
    _add_box(wall_bm, -7.0, -3.10, 2.86, 3.10, -0.04, 2.15)
    _add_box(wall_bm, -2.05, 8.0, 2.86, 3.10, -0.04, 2.15)
    _add_box(wall_bm, -3.10, -2.05, 2.86, 3.10, 1.94, 2.15)  # gate lintel
    for px in (-5.6, -3.15, -2.00, 0.55, 3.15, 5.75):
        _add_box(wall_bm, px - 0.16, px + 0.16, 2.82, 3.14, -0.04, 2.22, bevel=0.006)
    _link_bmesh(scene, "Pool_Boundary_Wall", wall_bm, mats["wall"], props, uv_scale=0.85)

    # 5. Slatted timber garden gate, low side fences, teak sun lounger frame, and side table
    wood_bm = bmesh.new()
    # Garden gate in wall opening x=[-3.08, -2.07], y=2.95
    n_slats = 10
    gx0, gx1 = -3.07, -2.08
    sw = (gx1 - gx0) / n_slats
    for i in range(n_slats):
        _add_box(wood_bm, gx0 + i * sw + 0.006, gx0 + (i + 1) * sw - 0.006, 2.95, 2.98, 0.03, 1.91, bevel=0.003)
    for rz in (0.32, 1.58):
        _add_box(wood_bm, gx0, gx1, 2.98, 3.015, rz, rz + 0.09, bevel=0.003)
    # Low slatted horizontal side fences at far left (x=-3.80) and far right (x=4.80)
    for fx in (-3.80, 4.80):
        for rail_z in (0.20, 0.42, 0.64, 0.86, 1.08):
            _add_box(wood_bm, fx - 0.015, fx + 0.015, -3.0, 2.86, rail_z, rail_z + 0.13, bevel=0.003)

    # Poolside teak sun lounger at x=[3.05, 3.78], y=[0.35, 2.08] (strictly outside x=1.50 and pool x=2.10)
    lx0, lx1, ly0, ly1, lz = 3.05, 3.78, 0.35, 2.08, 0.31
    for leg_x in (lx0 + 0.04, lx1 - 0.04):
        for leg_y in (ly0 + 0.08, 1.18, ly1 - 0.08):
            _add_box(wood_bm, leg_x - 0.025, leg_x + 0.025, leg_y - 0.025, leg_y + 0.025, -0.005, lz, bevel=0.004)
    _add_box(wood_bm, lx0, lx0 + 0.055, ly0, ly1, lz - 0.06, lz, bevel=0.005)
    _add_box(wood_bm, lx1 - 0.055, lx1, ly0, ly1, lz - 0.06, lz, bevel=0.005)
    for i in range(11):
        sy = ly0 + 0.06 + i * 0.105
        _add_box(wood_bm, lx0 + 0.05, lx1 - 0.05, sy, sy + 0.075, lz - 0.025, lz, bevel=0.003)
    # Reclined lounger backrest rising from y=1.42 to y=2.04
    for rx in (lx0 + 0.06, lx1 - 0.06):
        _add_cyl(wood_bm, (rx, 1.42, lz), (rx, 2.02, 0.78), 0.024, 0.024, segs=8)
    for k in range(5):
        t = (k + 0.5) / 5.0
        by = 1.42 + 0.60 * t
        bz = lz + 0.47 * t
        _add_box(wood_bm, lx0 + 0.07, lx1 - 0.07, by - 0.03, by + 0.03, bz - 0.014, bz + 0.014, bevel=0.003)

    # Low slatted teak poolside side table at x=[3.94, 4.38], y=[1.34, 1.78]
    tx0, tx1, ty0, ty1, th = 3.94, 4.38, 1.34, 1.78, 0.40
    for leg_x in (tx0 + 0.03, tx1 - 0.03):
        for leg_y in (ty0 + 0.03, ty1 - 0.03):
            _add_box(wood_bm, leg_x - 0.02, leg_x + 0.02, leg_y - 0.02, leg_y + 0.02, -0.005, th - 0.025, bevel=0.003)
    for i in range(5):
        sy = ty0 + i * ((ty1 - ty0) / 5.0)
        _add_box(wood_bm, tx0, tx1, sy + 0.005, sy + 0.075, th - 0.025, th, bevel=0.003)
    _link_bmesh(scene, "Pool_Timber_Gate_Fence_Furniture", wood_bm, mats["oak"], props)

    # Fence metal posts and gate iron hardware
    iron_bm = bmesh.new()
    for fx in (-3.80, 4.80):
        for py in (-2.8, -1.4, 0.0, 1.4, 2.75):
            _add_box(iron_bm, fx - 0.035, fx + 0.035, py - 0.035, py + 0.035, -0.04, 1.24, bevel=0.004)
    for hz in (0.36, 1.62):
        _add_box(iron_bm, -3.10, -2.76, 2.93, 2.952, hz - 0.02, hz + 0.02, bevel=0.002)
    _add_box(iron_bm, -2.20, -2.12, 2.92, 2.952, 0.96, 1.10, bevel=0.003)
    _link_bmesh(scene, "Pool_Metal_Hardware_Posts", iron_bm, iron_mat, props)

    # Tailored sun-lounger cushion + headrest pillow
    cush_bm = bmesh.new()
    _add_box(cush_bm, lx0 + 0.05, lx1 - 0.05, ly0 + 0.04, 1.44, lz, lz + 0.075, bevel=0.022)
    # Reclined cushion segment built as stacked beveled profile along backrest
    for k in range(6):
        t0, t1 = k / 6.0, (k + 1) / 6.0
        cy = 1.42 + 0.56 * 0.5 * (t0 + t1)
        cz = lz + 0.04 + 0.44 * 0.5 * (t0 + t1)
        _add_box(cush_bm, lx0 + 0.05, lx1 - 0.05, cy - 0.055, cy + 0.055, cz - 0.04, cz + 0.04, bevel=0.018)
    _add_box(cush_bm, lx0 + 0.14, lx1 - 0.14, 1.76, 1.92, 0.66, 0.76, bevel=0.03)
    _link_bmesh(scene, "Pool_Lounger_Cushion", cush_bm, cushion_mat, props, smooth=True)

    # Sculptural terracotta planters (strictly outside x=±1.50 and pool)
    pot_bm = bmesh.new()
    planter_coords = [(-2.22, 1.78, 0.03, 0.42, 0.14, 0.21), (4.24, 1.98, -0.004, 0.44, 0.15, 0.22)]
    for cx, cy, z0, h, rb, rt in planter_coords:
        _add_planter_pot(pot_bm, cx, cy, z0, h, rb, rt, segs=24)
    _link_bmesh(scene, "Pool_Terracotta_Planters", pot_bm, terra_mat, props, smooth=True)

    # Botanical shrubs, planter agaves, climbing vines, and distant garden trees behind wall
    rng = random.Random(999)
    stem_bm = bmesh.new()
    fol_bm = bmesh.new()
    vine_stem_bm = bmesh.new()
    vine_leaf_bm = bmesh.new()

    # Back shrub bed (y = 2.40..2.65, strictly y > 2.1)
    back_shrubs = [
        (-4.8, 2.52, 0.48, 0.85),
        (-3.6, 2.54, 0.42, 0.78),
        (-1.35, 2.52, 0.46, 0.82),
        (-0.35, 2.54, 0.40, 0.70),
        (0.85, 2.54, 0.48, 0.86),
        (2.05, 2.52, 0.44, 0.76),
        (3.45, 2.54, 0.46, 0.84),
        (4.65, 2.54, 0.50, 0.90),
    ]
    for sx, sy, sr, sh in back_shrubs:
        _add_shrub(stem_bm, fol_bm, sx, sy, 0.03, sr, sh, rng)

    # Left garden bed shrubs (x < -2.25)
    for sx, sy, sr, sh in ((-3.15, 1.75, 0.46, 0.86), (-2.95, 0.92, 0.44, 0.76), (-3.25, 0.35, 0.40, 0.72)):
        _add_shrub(stem_bm, fol_bm, sx, sy, 0.03, sr, sh, rng)

    # Planter foliage rosettes
    for cx, cy, z0, h, _rb, _rt in planter_coords:
        for i in range(14):
            ang = i * 2.39996 + rng.uniform(-0.1, 0.1)
            elev = rng.uniform(0.32, 1.05)
            ldir = Vector((math.cos(ang) * math.cos(elev), math.sin(ang) * math.cos(elev), math.sin(elev)))
            _add_leaf(
                fol_bm,
                Vector((cx, cy, z0 + h - 0.04)),
                ldir,
                Vector((0.0, 0.0, 1.0)),
                length=rng.uniform(0.28, 0.44),
                width=rng.uniform(0.055, 0.085),
                arch=rng.uniform(0.18, 0.32),
            )

    # Climbing vines on front of boundary wall (y = 2.86, strictly y > 2.1)
    for vx in (-1.55, -0.15, 1.35, 2.75, 4.10):
        for branch in (-0.18, 0.0, 0.18):
            _add_climbing_vine(vine_stem_bm, vine_leaf_bm, vx + branch, 2.86, 0.03, rng.uniform(1.65, 2.18), rng)

    # Distant garden trees behind the boundary wall (y = 4.3..5.2) to frame sky horizon
    for tx, ty, th in ((-4.2, 4.6, 3.8), (-0.8, 4.8, 4.1), (2.4, 4.7, 3.9), (5.4, 4.5, 4.0)):
        _add_cyl(stem_bm, (tx, ty, -0.04), (tx + rng.uniform(-0.1, 0.1), ty, th * 0.55), 0.11, 0.06, segs=8)
        _add_shrub(stem_bm, fol_bm, tx, ty, th * 0.48, 1.15, th * 0.55, rng)

    _link_bmesh(scene, "Pool_Shrub_Stems", stem_bm, wood_stem_mat, props)
    _link_bmesh(scene, "Pool_Shrub_Foliage", fol_bm, foliage_mat, props, smooth=True)
    _link_bmesh(scene, "Pool_Climbing_Vine_Stems", vine_stem_bm, wood_stem_mat, props)
    _link_bmesh(scene, "Pool_Climbing_Vine_Leaves", vine_leaf_bm, vine_leaf_mat, props, smooth=True)

    # Outdoor natural afternoon lighting (soft angled sun + Nishita sky + warm patio bounce)
    _setup_world_sky(scene, "Study_Pool_World", strength=0.30, elevation_deg=38.0, rotation_deg=222.0)
    _add_sun_light(
        scene,
        "Pool_Sun",
        elevation_deg=38.0,
        azimuth_deg=218.0,
        energy=3.25,
        color=(1.0, 0.955, 0.875),
        angle_deg=2.8,
    )
    _add_area_light(
        scene,
        "Pool_Deck_Bounce",
        location=(-0.95, -1.75, 2.15),
        target=(0.35, 0.70, 0.35),
        energy=42.0,
        color=(0.93, 0.96, 1.0),
        size_x=3.40,
        size_y=2.00,
        spread_deg=150.0,
    )


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def build_room(scene: bpy.types.Scene, case: str, library: Path | str) -> dict[str, object]:
    """Build surrounding architecture, materials, and lighting for 'drawer' or 'pool'.

    Invoked in Blender 4.5 after robot and physics fixture geometries are imported.
    Leaves camera, robot, robot materials, and physics mechanisms untouched.
    """
    if case not in _PLANS:
        raise ValueError(f"Unsupported case {case!r}; expected 'drawer' or 'pool'.")

    lib_path = Path(library)
    _configure_render_and_cm(scene)
    _clear_existing_lights(scene)

    materials = _build_role_materials(case, lib_path)
    props: list[str] = []

    if case == "drawer":
        _build_bathroom(scene, materials, props)
    else:
        _build_pool_garden(scene, materials, props)

    return {"materials": materials, "props": props}
