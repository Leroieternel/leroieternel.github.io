"""Photorealistic set dressing, shading, and lighting for DESPITE people studies.

Cases:
  - 'cafe': Late-afternoon / early-evening standing espresso bar.
  - 'darkroom': Daylit vestibule + red-safelight darkroom with trace-driven
    geometric doorway light spill.

Blender 4.5+ compatible (Cycles and Eevee Next), AgX color management,
metric world-space UV projection for genuine Genie Sim PBR textures, and
non-destructive preservation of UV-skinned human textures.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any, Callable

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

H = Path(__file__).resolve().parent
R = H.parent
OUT = R.parent
ROOT = OUT.parent

CASE_OUTPUT_DIRS = {
    "cafe": H / "01_cafe",
    "darkroom": H / "02_darkroom",
}

METRIC_UV_NAME = "MetricWorldUV"
REQUIRED_GENIE_STEMS = ("floor_tile_03", "floor_tile_04", "wall_03", "wall_04")
MJCF_COLOR_ROLES = {
    "wall",
    "floor",
    "oak",
    "steel",
    "ceramic",
    "brass",
    "rubber",
    "cloth",
    "paper",
    "liquid",
    "glass",
    "pastry",
    "paint",
    "parcel",
    "door",
}


# ---------------------------------------------------------------------------
# Blender 4.5 Safe Shader & Mesh Utilities
# ---------------------------------------------------------------------------

def _set_bsdf(bsdf: bpy.types.Node, name: str, value: Any) -> None:
    """Safely set a Principled BSDF input across Blender 4.x/4.5."""
    sock = bsdf.inputs.get(name)
    if sock is not None:
        sock.default_value = value


def _get_bsdf(mat: bpy.types.Material) -> bpy.types.Node:
    nt = mat.node_tree
    for node in nt.nodes:
        if node.type == "BSDF_PRINCIPLED":
            return node
    out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
    if out is None:
        out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return bsdf


def _new_material(name: str) -> tuple[bpy.types.Material, bpy.types.NodeTree, bpy.types.Node, bpy.types.Node]:
    old = bpy.data.materials.get(name)
    if old is not None:
        bpy.data.materials.remove(old, do_unlink=True)
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (520, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (180, 0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat, nt, bsdf, out


def _mix_rgba(
    nt: bpy.types.NodeTree,
    blend_type: str = "MIX",
    factor: float = 0.5,
    color_a: tuple[float, float, float, float] | None = None,
    color_b: tuple[float, float, float, float] | None = None,
) -> tuple[bpy.types.Node, bpy.types.NodeSocket, bpy.types.NodeSocket, bpy.types.NodeSocket, bpy.types.NodeSocket]:
    """Create a Blender 4.5 ShaderNodeMix in RGBA mode with unambiguous sockets."""
    node = nt.nodes.new("ShaderNodeMix")
    node.data_type = "RGBA"
    node.blend_type = blend_type
    node.clamp_factor = True
    fac_sock = node.inputs[0]
    fac_sock.default_value = factor
    rgba_ins = [s for s in node.inputs if s.type == "RGBA"]
    rgba_out = [s for s in node.outputs if s.type == "RGBA"][0]
    if color_a is not None:
        rgba_ins[0].default_value = color_a
    if color_b is not None:
        rgba_ins[1].default_value = color_b
    return node, fac_sock, rgba_ins[0], rgba_ins[1], rgba_out


def _ensure_collection(scene: bpy.types.Scene, name: str) -> bpy.types.Collection:
    existing = bpy.data.collections.get(name)
    if existing is not None:
        for obj in list(existing.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        return existing
    col = bpy.data.collections.new(name)
    scene.collection.children.link(col)
    return col


def _link_obj(obj: bpy.types.Object, col: bpy.types.Collection) -> bpy.types.Object:
    if obj.name not in col.objects:
        col.objects.link(obj)
    return obj


def _assign_mat(obj: bpy.types.Object, mat: bpy.types.Material | None) -> None:
    if mat is None or obj.type != "MESH" or obj.data is None:
        return
    if len(obj.data.materials) == 0:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat


def _mesh_from_bmesh(
    name: str,
    bm: bmesh.types.BMesh,
    loc: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rot: tuple[float, float, float] = (0.0, 0.0, 0.0),
    mat: bpy.types.Material | None = None,
    col: bpy.types.Collection | None = None,
    smooth: bool = False,
) -> bpy.types.Object:
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    if smooth and len(mesh.polygons) > 0:
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    obj.rotation_euler = Euler(rot, "XYZ")
    _assign_mat(obj, mat)
    if col is not None:
        _link_obj(obj, col)
    return obj


def _make_box(
    name: str,
    size: tuple[float, float, float],
    loc: tuple[float, float, float],
    rot: tuple[float, float, float] = (0.0, 0.0, 0.0),
    bevel: float = 0.0,
    mat: bpy.types.Material | None = None,
    col: bpy.types.Collection | None = None,
) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    if bevel > 0.0:
        max_b = min(size) * 0.35
        bmesh.ops.bevel(
            bm,
            geom=list(bm.edges),
            offset=min(bevel, max_b),
            segments=2,
            affect="EDGES",
            clamp_overlap=True,
        )
    return _mesh_from_bmesh(name, bm, loc=loc, rot=rot, mat=mat, col=col, smooth=(bevel > 0.0))


def _make_cyl(
    name: str,
    radius: float,
    depth: float,
    loc: tuple[float, float, float],
    rot: tuple[float, float, float] = (0.0, 0.0, 0.0),
    segs: int = 24,
    r2: float | None = None,
    mat: bpy.types.Material | None = None,
    col: bpy.types.Collection | None = None,
) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=segs,
        radius1=radius,
        radius2=radius if r2 is None else r2,
        depth=depth,
    )
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = abs(poly.normal.z) < 0.72
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    obj.rotation_euler = Euler(rot, "XYZ")
    _assign_mat(obj, mat)
    if col is not None:
        _link_obj(obj, col)
    return obj


def _make_uv_quad(
    name: str,
    width: float,
    height: float,
    loc: tuple[float, float, float],
    rot: tuple[float, float, float] = (0.0, 0.0, 0.0),
    mat: bpy.types.Material | None = None,
    col: bpy.types.Collection | None = None,
    curl_x: float = 0.0,
) -> bpy.types.Object:
    """Create a vertical quad facing -Y with clean [0,1] UVs (left-to-right, bottom-to-top)."""
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    nx = 6 if abs(curl_x) > 1e-5 else 1
    ny = 6 if abs(curl_x) > 1e-5 else 1
    grid = []
    for j in range(ny + 1):
        v = j / ny
        z = (v - 0.5) * height
        row = []
        for i in range(nx + 1):
            u = i / nx
            x = (u - 0.5) * width
            y = curl_x * ((1.0 - v) ** 2) * math.sin(u * math.pi)
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            f = bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
            uvs = (
                (i / nx, j / ny),
                ((i + 1) / nx, j / ny),
                ((i + 1) / nx, (j + 1) / ny),
                (i / nx, (j + 1) / ny),
            )
            for loop, uv in zip(f.loops, uvs):
                loop[uv_layer].uv = uv
    return _mesh_from_bmesh(name, bm, loc=loc, rot=rot, mat=mat, col=col, smooth=(abs(curl_x) > 1e-5))


def _look_at(obj: bpy.types.Object, target: tuple[float, float, float]) -> None:
    direction = Vector(target) - Vector(obj.location)
    if direction.length > 1e-6:
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _create_light(
    name: str,
    light_type: str,
    loc: tuple[float, float, float],
    energy: float,
    color: tuple[float, float, float],
    col: bpy.types.Collection,
    target: tuple[float, float, float] | None = None,
    size: float = 0.5,
    size_y: float | None = None,
    spread_deg: float | None = None,
    spot_deg: float | None = None,
    spot_blend: float = 0.45,
    soft_size: float = 0.12,
    use_shadow: bool = True,
) -> bpy.types.Object:
    ldata = bpy.data.lights.new(name=name, type=light_type)
    ldata.energy = energy
    ldata.color = color
    if hasattr(ldata, "use_shadow"):
        ldata.use_shadow = use_shadow
    if light_type == "AREA":
        if size_y is not None:
            ldata.shape = "RECTANGLE"
            ldata.size = size
            ldata.size_y = size_y
        else:
            ldata.shape = "SQUARE"
            ldata.size = size
        if spread_deg is not None and hasattr(ldata, "spread"):
            ldata.spread = math.radians(spread_deg)
    elif light_type == "SPOT":
        if spot_deg is not None:
            ldata.spot_size = math.radians(spot_deg)
        ldata.spot_blend = spot_blend
        ldata.shadow_soft_size = soft_size
    elif light_type == "POINT":
        ldata.shadow_soft_size = soft_size
    elif light_type == "SUN":
        ldata.angle = math.radians(soft_size)
    lobj = bpy.data.objects.new(name=name, object_data=ldata)
    lobj.location = loc
    if target is not None:
        _look_at(lobj, target)
    _link_obj(lobj, col)
    return lobj


# ---------------------------------------------------------------------------
# Genuine Genie Sim Texture Discovery, Linking & Metric Planar UVs
# ---------------------------------------------------------------------------

def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve_genie_texture_dir(library: Any) -> Path:
    """Locate genuine Genie Sim textures (<stem>_{Alb,Nor,Rgh}.jpg). Fails if missing."""
    rel = Path("background/common/home_b/textures")
    candidates: list[Path] = []

    def _add_root(p: Path | None) -> None:
        if p is None:
            return
        candidates.extend([p / rel, p / "library" / rel, p / ".runtime/genie-assets" / rel, p])

    if isinstance(library, (str, Path)):
        _add_root(Path(library))
    elif isinstance(library, dict):
        for k in ("genie", "textures", "library", "root", "path", "HOME", "ROOT"):
            v = library.get(k)
            if isinstance(v, (str, Path)):
                _add_root(Path(v))
    elif library is not None:
        for attr in ("GENIE_DIR", "TEXTURE_DIR", "HOME", "ROOT", "__file__"):
            v = getattr(library, attr, None)
            if isinstance(v, (str, Path)):
                vp = Path(v)
                _add_root(vp.parent if vp.is_file() else vp)

    for base in (
        ROOT / "library",
        ROOT / ".runtime/genie-assets",
        OUT / "mobile_worlds/library",
        OUT / "library",
        R / "library",
        H / "library",
        ROOT,
    ):
        _add_root(base)

    seen: set[Path] = set()
    checked: list[str] = []
    for cand in candidates:
        try:
            rc = cand.resolve()
        except Exception:
            rc = cand
        if rc in seen:
            continue
        seen.add(rc)
        checked.append(str(rc))
        if rc.is_dir():
            ok = all(
                (rc / f"{stem}_{suf}.jpg").is_file()
                for stem in REQUIRED_GENIE_STEMS
                for suf in ("Alb", "Nor", "Rgh")
            )
            if ok:
                return rc

    raise FileNotFoundError(
        "Missing genuine Genie Sim textures "
        f"({', '.join(REQUIRED_GENIE_STEMS)} x {{Alb,Nor,Rgh}}.jpg). "
        f"Searched: {checked}"
    )


def _build_genie_pbr_material(
    name: str,
    tex_dir: Path,
    stem: str,
    tile_m: float = 1.4,
    projection: str = "XY",
    tint: tuple[float, float, float] = (1.0, 1.0, 1.0),
    rough_scale: float = 1.0,
    rough_bias: float = 0.0,
    normal_strength: float = 0.85,
) -> tuple[bpy.types.Material, dict[str, Any]]:
    """Build a metric-UV Genie Sim PBR material and assert all texture channels are linked."""
    paths = {
        "Alb": tex_dir / f"{stem}_Alb.jpg",
        "Nor": tex_dir / f"{stem}_Nor.jpg",
        "Rgh": tex_dir / f"{stem}_Rgh.jpg",
    }
    for ch, p in paths.items():
        if not p.is_file():
            raise FileNotFoundError(f"Missing required Genie Sim {ch} texture: {p}")

    mat, nt, bsdf, _ = _new_material(name)
    mat["metric_uv_projection"] = projection
    mat["metric_tile_w_m"] = float(tile_m)
    mat["metric_tile_h_m"] = float(tile_m)
    mat["genie_stem"] = stem

    uv_node = nt.nodes.new("ShaderNodeUVMap")
    uv_node.uv_map = METRIC_UV_NAME
    uv_node.location = (-780, 0)

    def _load_tex(ch: str, y_loc: int, colorspace: str) -> bpy.types.Node:
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.label = f"{stem}_{ch}"
        tex.location = (-500, y_loc)
        img = bpy.data.images.load(str(paths[ch]), check_existing=True)
        img.colorspace_settings.name = colorspace
        tex.image = img
        nt.links.new(uv_node.outputs["UV"], tex.inputs["Vector"])
        return tex

    alb_tex = _load_tex("Alb", 260, "sRGB")
    rgh_tex = _load_tex("Rgh", -40, "Non-Color")
    nor_tex = _load_tex("Nor", -340, "Non-Color")

    if tint != (1.0, 1.0, 1.0):
        mix, _, ca, cb, out_c = _mix_rgba(
            nt, blend_type="MULTIPLY", factor=1.0, color_b=(tint[0], tint[1], tint[2], 1.0)
        )
        mix.location = (-160, 260)
        nt.links.new(alb_tex.outputs["Color"], ca)
        nt.links.new(out_c, bsdf.inputs["Base Color"])
    else:
        nt.links.new(alb_tex.outputs["Color"], bsdf.inputs["Base Color"])

    if abs(rough_scale - 1.0) > 1e-4 or abs(rough_bias) > 1e-4:
        m = nt.nodes.new("ShaderNodeMath")
        m.operation = "MULTIPLY_ADD"
        m.use_clamp = True
        m.location = (-160, -40)
        m.inputs[1].default_value = rough_scale
        m.inputs[2].default_value = rough_bias
        nt.links.new(rgh_tex.outputs["Color"], m.inputs[0])
        nt.links.new(m.outputs["Value"], bsdf.inputs["Roughness"])
    else:
        nt.links.new(rgh_tex.outputs["Color"], bsdf.inputs["Roughness"])

    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nmap.location = (-160, -340)
    nmap.uv_map = METRIC_UV_NAME
    nmap.inputs["Strength"].default_value = normal_strength
    nt.links.new(nor_tex.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    _set_bsdf(bsdf, "Specular IOR Level", 0.45)

    record = _assert_genie_material_linked(mat, paths, stem, tile_m, projection)
    return mat, record


def _assert_genie_material_linked(
    mat: bpy.types.Material,
    paths: dict[str, Path],
    stem: str,
    tile_m: float,
    projection: str,
) -> dict[str, Any]:
    nt = mat.node_tree
    bsdf = _get_bsdf(mat)
    assert bsdf.inputs["Base Color"].is_linked, f"{mat.name}: Base Color unlinked"
    assert bsdf.inputs["Roughness"].is_linked, f"{mat.name}: Roughness unlinked"
    assert bsdf.inputs["Normal"].is_linked, f"{mat.name}: Normal unlinked"

    expected_cs = {"Alb": "sRGB", "Nor": "Non-Color", "Rgh": "Non-Color"}
    channel_records: dict[str, Any] = {}
    for ch, path in paths.items():
        tex_nodes = [
            n for n in nt.nodes
            if n.type == "TEX_IMAGE" and n.label == f"{stem}_{ch}"
        ]
        assert tex_nodes, f"{mat.name}: missing image node {stem}_{ch}"
        tn = tex_nodes[0]
        assert tn.image is not None, f"{mat.name}: image is None for {ch}"
        assert any(lnk.from_node == tn for lnk in nt.links), f"{mat.name}: {ch} node unlinked"
        actual_cs = tn.image.colorspace_settings.name
        assert actual_cs == expected_cs[ch], (
            f"{mat.name}: expected {expected_cs[ch]} for {ch}, got {actual_cs}"
        )
        channel_records[ch] = {
            "filename": path.name,
            "path": str(path),
            "colorspace": actual_cs,
            "sha256": _sha256_file(path),
            "linked": True,
        }

    return {
        "material": mat.name,
        "stem": stem,
        "tile_m": float(tile_m),
        "projection": projection,
        "uv_map": METRIC_UV_NAME,
        "channels": channel_records,
        "linked_verified": True,
    }


def _apply_metric_planar_uvs(objects: list[bpy.types.Object]) -> list[str]:
    """Assign world-space metric planar UVs to all meshes carrying Genie Sim materials."""
    bpy.context.view_layer.update()
    axes = {"XY": (0, 1), "XZ": (0, 2), "YZ": (1, 2)}
    dominant = ("YZ", "XZ", "XY")
    processed: list[str] = []

    for obj in objects:
        if obj is None or obj.type != "MESH" or obj.data is None:
            continue
        mesh = obj.data
        if len(mesh.polygons) == 0 or len(mesh.loops) == 0:
            continue
        if not any(m is not None and "metric_uv_projection" in m for m in mesh.materials):
            continue
        if mesh.users > 1:
            obj.data = mesh.copy()
            mesh = obj.data

        layer = mesh.uv_layers.get(METRIC_UV_NAME) or mesh.uv_layers.new(name=METRIC_UV_NAME)
        values = np.zeros((len(mesh.loops), 2), dtype=np.float32)
        coords = np.empty((len(mesh.vertices), 3), dtype=np.float32)
        mesh.vertices.foreach_get("co", coords.ravel())

        mat_w = np.array(obj.matrix_world, dtype=np.float32)
        world_coords = coords @ mat_w[:3, :3].T + mat_w[:3, 3]
        try:
            inv_t = obj.matrix_world.to_3x3().inverted().transposed()
        except ValueError:
            inv_t = Matrix.Identity(3)

        for face in mesh.polygons:
            if face.material_index >= len(mesh.materials):
                continue
            mat = mesh.materials[face.material_index]
            if mat is None or "metric_uv_projection" not in mat:
                continue
            proj = str(mat["metric_uv_projection"])
            tw = float(mat.get("metric_tile_w_m", 1.5))
            th = float(mat.get("metric_tile_h_m", tw))
            wn = np.array((inv_t @ face.normal).normalized(), dtype=np.float32)
            plane_axis = ({0, 1, 2} - set(axes[proj])).pop()
            if abs(float(wn[plane_axis])) < 0.65:
                proj = dominant[int(np.argmax(np.abs(wn)))]
            pts = world_coords[np.array(face.vertices, dtype=np.int32)]
            a0, a1 = axes[proj]
            values[np.array(face.loop_indices, dtype=np.int32)] = np.column_stack(
                (pts[:, a0] / tw, pts[:, a1] / th)
            )

        layer.uv.foreach_set("vector", values.ravel())
        mesh.update()
        processed.append(obj.name)

    return processed


# ---------------------------------------------------------------------------
# Procedural English Signage, Photographic Prints & Outdoor Backdrop Textures
# ---------------------------------------------------------------------------

_FONT_5X7: dict[str, tuple[str, ...]] = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11100", "10010", "10001", "10001", "10001", "10010", "11100"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10011", "10101", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("01110", "10000", "11110", "10001", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ":": ("00000", "00100", "00100", "00000", "00100", "00100", "00000"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}


def _image_from_rgba(name: str, rgba: np.ndarray, colorspace: str = "sRGB") -> bpy.types.Image:
    h, w, _ = rgba.shape
    old = bpy.data.images.get(name)
    if old is not None:
        bpy.data.images.remove(old, do_unlink=True)
    img = bpy.data.images.new(name=name, width=w, height=h, alpha=False)
    flipped = np.ascontiguousarray(rgba[::-1], dtype=np.float32)
    img.pixels.foreach_set(flipped.ravel())
    img.colorspace_settings.name = colorspace
    try:
        img.pack()
    except Exception:
        pass
    return img


def _make_sign_material(
    name: str,
    lines: list[str],
    bg: tuple[float, float, float],
    fg: tuple[float, float, float],
    border: tuple[float, float, float] | None = None,
    width: int = 512,
    height: int = 256,
    roughness: float = 0.55,
    emission_strength: float = 0.0,
) -> tuple[bpy.types.Material, str]:
    arr = np.zeros((height, width, 4), dtype=np.float32)
    arr[:, :, 0] = bg[0]
    arr[:, :, 1] = bg[1]
    arr[:, :, 2] = bg[2]
    arr[:, :, 3] = 1.0

    if border is not None:
        m = max(6, min(width, height) // 26)
        t = max(2, m // 4)
        arr[m : m + t, m : width - m, :3] = border
        arr[height - m - t : height - m, m : width - m, :3] = border
        arr[m : height - m, m : m + t, :3] = border
        arr[m : height - m, width - m - t : width - m, :3] = border

    n_lines = max(1, len(lines))
    usable_h = int(height * 0.72)
    line_slot = usable_h // n_lines
    start_y = (height - usable_h) // 2

    for idx, raw_line in enumerate(lines):
        text = raw_line.upper()
        if not text:
            continue
        char_cols = len(text) * 6 - 1
        max_sx = max(1, int((width * 0.82) // max(1, char_cols)))
        max_sy = max(1, int((line_slot * 0.74) // 7))
        scale = max(1, min(max_sx, max_sy, 5 if idx == 0 else 4))
        total_w = char_cols * scale
        total_h = 7 * scale
        ox = (width - total_w) // 2
        oy = start_y + idx * line_slot + (line_slot - total_h) // 2
        for ci, ch in enumerate(text):
            glyph = _FONT_5X7.get(ch, _FONT_5X7[" "])
            gx0 = ox + ci * 6 * scale
            for r, row_str in enumerate(glyph):
                for c, bit in enumerate(row_str):
                    if bit == "1":
                        y0 = max(0, oy + r * scale)
                        y1 = min(height, y0 + scale)
                        x0 = max(0, gx0 + c * scale)
                        x1 = min(width, x0 + scale)
                        arr[y0:y1, x0:x1, :3] = fg

    img_name = f"{name}_img"
    img = _image_from_rgba(img_name, arr, "sRGB")
    mat, nt, bsdf, _ = _new_material(name)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.location = (-280, 120)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    _set_bsdf(bsdf, "Roughness", roughness)
    _set_bsdf(bsdf, "Specular IOR Level", 0.35)
    if emission_strength > 0.0:
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        _set_bsdf(bsdf, "Emission Strength", emission_strength)
    return mat, img_name


def _make_bw_print_material(name: str, variant: int) -> tuple[bpy.types.Material, str]:
    """Generate an authentic silver-gelatin B&W darkroom print (landscapes/architecture only)."""
    h, w = 256, 200
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = xx / float(w - 1)
    v = yy / float(h - 1)  # 0 at top, 1 at bottom

    if variant % 4 == 0:
        # Mountain ridges & soft sky
        sky = 0.78 - 0.35 * v
        r1 = 0.48 + 0.09 * np.sin(u * 5.2 + 0.4) + 0.04 * np.cos(u * 13.0)
        r2 = 0.62 + 0.07 * np.sin(u * 4.1 + 2.2) + 0.03 * np.sin(u * 17.0)
        tone = np.where(v < r1, sky, np.where(v < r2, 0.32 + 0.12 * (v - r1), 0.14 + 0.08 * (v - r2)))
    elif variant % 4 == 1:
        # Stone arch bridge & water reflection
        tone = 0.72 - 0.25 * v
        deck = (v > 0.48) & (v < 0.56)
        arch = ((u - 0.5) ** 2) / 0.11 + ((v - 0.70) ** 2) / 0.045 < 1.0
        bridge = (v >= 0.52) & (v < 0.72) & (~arch)
        water = v >= 0.72
        tone = np.where(water, 0.26 + 0.14 * np.sin(v * 90.0) * np.exp(-((u - 0.5) ** 2) * 8.0), tone)
        tone = np.where(bridge | deck, 0.12, tone)
    elif variant % 4 == 2:
        # Sunlit architectural colonnade geometry
        tone = 0.22 + 0.55 * np.clip(1.0 - np.abs(u - 0.35) * 1.6, 0.0, 1.0) * (1.0 - 0.4 * v)
        pillars = ((u > 0.14) & (u < 0.22)) | ((u > 0.46) & (u < 0.54)) | ((u > 0.76) & (u < 0.84))
        tone = np.where(pillars & (v > 0.12) & (v < 0.88), 0.10, tone)
        tone = np.where(v > 0.82, 0.35 + 0.15 * np.sin(u * 20.0), tone)
    else:
        # Botanical reeds & light gradient
        tone = 0.80 - 0.42 * np.sqrt((u - 0.55) ** 2 + (v - 0.35) ** 2)
        for sx, amp, phase in ((0.28, 0.06, 0.2), (0.48, 0.08, 1.1), (0.68, 0.05, 2.0)):
            stem_x = sx + amp * np.sin(v * 4.0 + phase) * (1.0 - v)
            tone = np.where((np.abs(u - stem_x) < 0.014) & (v > 0.20), 0.10, tone)

    tone = np.clip(tone, 0.06, 0.86)
    border_mask = (u < 0.08) | (u > 0.92) | (v < 0.07) | (v > 0.93)
    tone = np.where(border_mask, 0.86, tone)

    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[:, :, 0] = tone * 0.98
    rgba[:, :, 1] = tone * 0.96
    rgba[:, :, 2] = tone * 0.92

    img_name = f"{name}_img"
    img = _image_from_rgba(img_name, rgba, "sRGB")
    mat, nt, bsdf, _ = _new_material(name)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    _set_bsdf(bsdf, "Roughness", 0.28)
    _set_bsdf(bsdf, "Coat Weight", 0.35)
    _set_bsdf(bsdf, "Coat Roughness", 0.15)
    return mat, img_name


def _make_cafe_exterior_material(name: str) -> tuple[bpy.types.Material, str]:
    """Soft late-afternoon golden-hour outdoor street/foliage depth plane behind cafe glass."""
    h, w = 256, 384
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = xx / float(w - 1)
    v = yy / float(h - 1)  # 0 top, 1 bottom

    # Warm dusk-to-golden horizon sky
    r = 0.26 + 0.68 * np.clip(v * 1.15, 0.0, 1.0)
    g = 0.30 + 0.44 * np.clip(v * 1.10, 0.0, 1.0)
    b = 0.48 + 0.04 * np.clip(1.0 - v, 0.0, 1.0)

    # Soft golden sun glow near left-mid horizon
    glow = np.exp(-(((u - 0.30) ** 2) / 0.10 + ((v - 0.56) ** 2) / 0.06))
    r = np.clip(r + 0.38 * glow, 0.0, 0.98)
    g = np.clip(g + 0.26 * glow, 0.0, 0.90)
    b = np.clip(b + 0.10 * glow, 0.0, 0.78)

    # Soft distant street-side architectural cornice & foliage bokeh (no people)
    bldg_h = np.where(u < 0.45, 0.52, np.where(u < 0.72, 0.44, 0.50))
    bldg = np.clip((v - bldg_h) * 18.0, 0.0, 1.0)
    r = r * (1.0 - 0.55 * bldg) + 0.26 * bldg
    g = g * (1.0 - 0.58 * bldg) + 0.20 * bldg
    b = b * (1.0 - 0.62 * bldg) + 0.18 * bldg

    # Warm distant café/streetlamp bokeh orbs
    for bx, by, rad, inten in (
        (0.18, 0.68, 0.045, 0.65),
        (0.58, 0.62, 0.040, 0.55),
        (0.82, 0.66, 0.048, 0.60),
    ):
        orb = np.exp(-(((u - bx) ** 2 + (v - by) ** 2) / (rad * rad)))
        r = np.clip(r + inten * orb, 0.0, 0.98)
        g = np.clip(g + inten * 0.72 * orb, 0.0, 0.88)
        b = np.clip(b + inten * 0.32 * orb, 0.0, 0.70)

    # Soft foreground tree canopy silhouette at top corners
    canopy = np.exp(-(((u - 0.86) ** 2) / 0.05 + ((v - 0.22) ** 2) / 0.06))
    canopy += 0.7 * np.exp(-(((u - 0.10) ** 2) / 0.04 + ((v - 0.18) ** 2) / 0.05))
    canopy = np.clip(canopy, 0.0, 0.75)
    r = r * (1.0 - canopy) + 0.10 * canopy
    g = g * (1.0 - canopy) + 0.13 * canopy
    b = b * (1.0 - canopy) + 0.08 * canopy

    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[:, :, 0] = r
    rgba[:, :, 1] = g
    rgba[:, :, 2] = b

    img_name = f"{name}_img"
    img = _image_from_rgba(img_name, rgba, "sRGB")
    mat, nt, bsdf, _ = _new_material(name)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    _set_bsdf(bsdf, "Emission Strength", 1.85)
    _set_bsdf(bsdf, "Roughness", 0.95)
    return mat, img_name


def _make_timer_dial_material(name: str) -> tuple[bpy.types.Material, str]:
    """Analog darkroom GraLab-style luminous amber-red dial."""
    s = 256
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    dx = (xx - s * 0.5) / (s * 0.45)
    dy = (yy - s * 0.5) / (s * 0.45)
    rad = np.sqrt(dx * dx + dy * dy)
    ang = np.arctan2(dy, dx)

    rgba = np.zeros((s, s, 4), dtype=np.float32)
    rgba[:, :, 0] = 0.04
    rgba[:, :, 1] = 0.03
    rgba[:, :, 2] = 0.03
    rgba[:, :, 3] = 1.0

    # Tick ring
    ring = (rad > 0.72) & (rad < 0.88)
    tick = np.abs(np.sin(ang * 30.0)) > 0.93
    major = np.abs(np.sin(ang * 6.0)) > 0.97
    dial_glow = (ring & tick) | ((rad > 0.62) & (rad < 0.88) & major)
    # Hands
    hand1 = (rad < 0.66) & (np.abs(dx * 0.6 - dy * 0.8) < 0.035) & (dx * 0.8 + dy * 0.6 > -0.05)
    hand2 = (rad < 0.45) & (np.abs(dx * 0.9 + dy * 0.4) < 0.045) & (-dx * 0.4 + dy * 0.9 > -0.05)
    lit = dial_glow | hand1 | hand2 | (rad < 0.07)

    rgba[lit, 0] = 0.95
    rgba[lit, 1] = 0.24
    rgba[lit, 2] = 0.06

    img_name = f"{name}_img"
    img = _image_from_rgba(img_name, rgba, "sRGB")
    mat, nt, bsdf, _ = _new_material(name)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
    _set_bsdf(bsdf, "Emission Strength", 0.85)
    _set_bsdf(bsdf, "Roughness", 0.25)
    return mat, img_name


# ---------------------------------------------------------------------------
# Physically Based Role Materials (15 MJCF Roles + Droplets + Set Finishes)
# ---------------------------------------------------------------------------

def _make_oak_material(name: str, base_dark=(0.15, 0.08, 0.035, 1.0), base_light=(0.39, 0.23, 0.11, 1.0)) -> bpy.types.Material:
    mat, nt, bsdf, _ = _new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.8, 12.0, 2.2)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])

    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 3.5
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Roughness"].default_value = 0.55
    nt.links.new(mp.outputs["Vector"], noise.inputs["Vector"])

    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.inputs["Scale"].default_value = 5.5
    wave.inputs["Distortion"].default_value = 4.2
    wave.inputs["Detail"].default_value = 5.0
    nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])

    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.22
    cr.color_ramp.elements[0].color = base_dark
    cr.color_ramp.elements[1].position = 0.78
    cr.color_ramp.elements[1].color = base_light
    nt.links.new(wave.outputs["Fac"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], bsdf.inputs["Base Color"])

    rmap = nt.nodes.new("ShaderNodeMapRange")
    rmap.inputs["To Min"].default_value = 0.25
    rmap.inputs["To Max"].default_value = 0.39
    nt.links.new(noise.outputs["Fac"], rmap.inputs["Value"])
    nt.links.new(rmap.outputs["Result"], bsdf.inputs["Roughness"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(wave.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    _set_bsdf(bsdf, "Coat Weight", 0.18)
    _set_bsdf(bsdf, "Coat Roughness", 0.22)
    _set_bsdf(bsdf, "Specular IOR Level", 0.50)
    return mat


def _make_metal_material(
    name: str,
    color: tuple[float, float, float, float],
    rough_min: float = 0.14,
    rough_max: float = 0.24,
    metallic: float = 0.96,
    bump_strength: float = 0.03,
) -> bpy.types.Material:
    mat, nt, bsdf, _ = _new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (18.0, 2.5, 18.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])

    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 14.0
    noise.inputs["Detail"].default_value = 6.0
    nt.links.new(mp.outputs["Vector"], noise.inputs["Vector"])

    rmap = nt.nodes.new("ShaderNodeMapRange")
    rmap.inputs["To Min"].default_value = rough_min
    rmap.inputs["To Max"].default_value = rough_max
    nt.links.new(noise.outputs["Fac"], rmap.inputs["Value"])
    nt.links.new(rmap.outputs["Result"], bsdf.inputs["Roughness"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.001
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    _set_bsdf(bsdf, "Base Color", color)
    _set_bsdf(bsdf, "Metallic", metallic)
    return mat


def _make_ceramic_material(name: str, color=(0.88, 0.85, 0.80, 1.0), rough: float = 0.11) -> bpy.types.Material:
    mat, nt, bsdf, _ = _new_material(name)
    _set_bsdf(bsdf, "Base Color", color)
    _set_bsdf(bsdf, "Roughness", rough)
    _set_bsdf(bsdf, "Specular IOR Level", 0.55)
    _set_bsdf(bsdf, "Coat Weight", 0.65)
    _set_bsdf(bsdf, "Coat Roughness", 0.05)
    _set_bsdf(bsdf, "Coat IOR", 1.52)
    _set_bsdf(bsdf, "Subsurface Weight", 0.04)
    _set_bsdf(bsdf, "Subsurface Scale", 0.004)
    return mat


def _make_cloth_material(
    name: str,
    color: tuple[float, float, float, float],
    roughness: float = 0.86,
    weave_scale: float = 65.0,
    bump_strength: float = 0.08,
) -> bpy.types.Material:
    mat, nt, bsdf, _ = _new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    w1 = nt.nodes.new("ShaderNodeTexWave")
    w1.bands_direction = "X"
    w1.inputs["Scale"].default_value = weave_scale
    w2 = nt.nodes.new("ShaderNodeTexWave")
    w2.bands_direction = "Y"
    w2.inputs["Scale"].default_value = weave_scale
    nt.links.new(tc.outputs["Object"], w1.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], w2.inputs["Vector"])

    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "MULTIPLY"
    nt.links.new(w1.outputs["Fac"], add.inputs[0])
    nt.links.new(w2.outputs["Fac"], add.inputs[1])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.0015
    nt.links.new(add.outputs["Value"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    _set_bsdf(bsdf, "Base Color", color)
    _set_bsdf(bsdf, "Roughness", roughness)
    _set_bsdf(bsdf, "Sheen Weight", 0.32)
    _set_bsdf(bsdf, "Sheen Roughness", 0.65)
    _set_bsdf(bsdf, "Specular IOR Level", 0.25)
    return mat


def _make_glass_material(
    name: str,
    tint=(0.94, 0.97, 0.96, 1.0),
    roughness: float = 0.03,
    ior: float = 1.51,
    transmission: float = 0.92,
    architectural_shadow: bool = False,
) -> bpy.types.Material:
    mat, nt, bsdf, out = _new_material(name)
    _set_bsdf(bsdf, "Base Color", tint)
    _set_bsdf(bsdf, "Roughness", roughness)
    _set_bsdf(bsdf, "IOR", ior)
    _set_bsdf(bsdf, "Transmission Weight", transmission)
    _set_bsdf(bsdf, "Coat Weight", 0.20)
    _set_bsdf(bsdf, "Coat Roughness", 0.02)

    if architectural_shadow:
        lp = nt.nodes.new("ShaderNodeLightPath")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        tr.inputs["Color"].default_value = tint
        ms = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(lp.outputs["Is Shadow Ray"], ms.inputs["Fac"])
        nt.links.new(bsdf.outputs["BSDF"], ms.inputs[1])
        nt.links.new(tr.outputs["BSDF"], ms.inputs[2])
        nt.links.new(ms.outputs["Shader"], out.inputs["Surface"])
    return mat


def _make_liquid_material(
    name: str,
    tint=(0.88, 0.95, 0.99, 1.0),
    transmission: float = 0.90,
    roughness: float = 0.02,
    ior: float = 1.333,
    ripple: float = 0.015,
) -> bpy.types.Material:
    mat, nt, bsdf, out = _new_material(name)
    _set_bsdf(bsdf, "Base Color", tint)
    _set_bsdf(bsdf, "Roughness", roughness)
    _set_bsdf(bsdf, "IOR", ior)
    _set_bsdf(bsdf, "Transmission Weight", transmission)
    _set_bsdf(bsdf, "Coat Weight", 0.60)
    _set_bsdf(bsdf, "Coat Roughness", 0.015)
    _set_bsdf(bsdf, "Specular IOR Level", 0.65)

    if ripple > 0.0:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 28.0
        noise.inputs["Detail"].default_value = 3.0
        nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = ripple
        bump.inputs["Distance"].default_value = 0.001
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # Soften shadow rays so clear liquid/droplets cast realistic translucent caustics/darkening
    if transmission > 0.7:
        lp = nt.nodes.new("ShaderNodeLightPath")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        tr.inputs["Color"].default_value = (tint[0] * 0.72, tint[1] * 0.76, tint[2] * 0.80, 1.0)
        ms = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(lp.outputs["Is Shadow Ray"], ms.inputs["Fac"])
        nt.links.new(bsdf.outputs["BSDF"], ms.inputs[1])
        nt.links.new(tr.outputs["BSDF"], ms.inputs[2])
        nt.links.new(ms.outputs["Shader"], out.inputs["Surface"])
    return mat


def _make_pastry_material(name: str) -> bpy.types.Material:
    mat, nt, bsdf, _ = _new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 18.0
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.68
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])

    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.25
    cr.color_ramp.elements[0].color = (0.30, 0.14, 0.04, 1.0)
    e_mid = cr.color_ramp.elements.new(0.55)
    e_mid.color = (0.58, 0.34, 0.12, 1.0)
    cr.color_ramp.elements[2].position = 0.82
    cr.color_ramp.elements[2].color = (0.76, 0.52, 0.22, 1.0)
    nt.links.new(noise.outputs["Fac"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], bsdf.inputs["Base Color"])

    rmap = nt.nodes.new("ShaderNodeMapRange")
    rmap.inputs["To Min"].default_value = 0.34
    rmap.inputs["To Max"].default_value = 0.62
    nt.links.new(noise.outputs["Fac"], rmap.inputs["Value"])
    nt.links.new(rmap.outputs["Result"], bsdf.inputs["Roughness"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.004
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    _set_bsdf(bsdf, "Subsurface Weight", 0.12)
    _set_bsdf(bsdf, "Subsurface Scale", 0.006)
    _set_bsdf(bsdf, "Coat Weight", 0.15)
    _set_bsdf(bsdf, "Coat Roughness", 0.28)
    return mat


def _make_parcel_material(name: str) -> bpy.types.Material:
    mat, nt, bsdf, _ = _new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 26.0
    noise.inputs["Detail"].default_value = 6.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])

    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.30
    cr.color_ramp.elements[0].color = (0.44, 0.31, 0.18, 1.0)
    cr.color_ramp.elements[1].position = 0.78
    cr.color_ramp.elements[1].color = (0.58, 0.43, 0.26, 1.0)
    nt.links.new(noise.outputs["Fac"], cr.inputs["Fac"])
    nt.links.new(cr.outputs["Color"], bsdf.inputs["Base Color"])

    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.10
    bump.inputs["Distance"].default_value = 0.002
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    _set_bsdf(bsdf, "Roughness", 0.84)
    _set_bsdf(bsdf, "Specular IOR Level", 0.25)
    return mat


def _make_paint_material(
    name: str,
    color=(0.30, 0.34, 0.36, 1.0),
    roughness: float = 0.32,
    coat: float = 0.22,
) -> bpy.types.Material:
    mat, nt, bsdf, _ = _new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 40.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.02
    bump.inputs["Distance"].default_value = 0.001
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    _set_bsdf(bsdf, "Base Color", color)
    _set_bsdf(bsdf, "Roughness", roughness)
    _set_bsdf(bsdf, "Coat Weight", coat)
    _set_bsdf(bsdf, "Coat Roughness", 0.14)
    return mat


def _make_emissive_material(
    name: str,
    color: tuple[float, float, float, float],
    strength: float,
    roughness: float = 0.20,
) -> bpy.types.Material:
    mat, nt, bsdf, _ = _new_material(name)
    _set_bsdf(bsdf, "Base Color", color)
    _set_bsdf(bsdf, "Emission Color", color)
    _set_bsdf(bsdf, "Emission Strength", strength)
    _set_bsdf(bsdf, "Roughness", roughness)
    return mat


def _build_role_bank(case: str, tex_dir: Path, audit: dict[str, Any]) -> dict[str, bpy.types.Material]:
    """Create all MJCF color-role materials plus case-specific architectural PBR finishes."""
    p = f"NL_{case}_"
    bank: dict[str, bpy.types.Material] = {}
    genie_records: list[dict[str, Any]] = []

    if case == "cafe":
        floor_mat, r_fl = _build_genie_pbr_material(
            f"{p}floor", tex_dir, "floor_tile_03", tile_m=1.20, projection="XY",
            tint=(0.94, 0.90, 0.84), rough_scale=0.92, normal_strength=0.80,
        )
        wall_mat, r_wl = _build_genie_pbr_material(
            f"{p}wall", tex_dir, "wall_03", tile_m=1.60, projection="XZ",
            tint=(0.93, 0.89, 0.82), rough_scale=1.02, normal_strength=0.75,
        )
        accent_wall, r_aw = _build_genie_pbr_material(
            f"{p}wall_accent", tex_dir, "wall_04", tile_m=1.50, projection="XZ",
            tint=(0.56, 0.52, 0.48), rough_scale=1.05, normal_strength=0.80,
        )
        genie_records.extend([r_fl, r_wl, r_aw])
        bank["wall_accent"] = accent_wall
    else:
        floor_mat, r_fl = _build_genie_pbr_material(
            f"{p}floor", tex_dir, "floor_tile_04", tile_m=1.20, projection="XY",
            tint=(0.74, 0.74, 0.76), rough_scale=0.88, normal_strength=0.85,
        )
        wall_mat, r_wl = _build_genie_pbr_material(
            f"{p}wall", tex_dir, "wall_04", tile_m=1.60, projection="XZ",
            tint=(0.34, 0.34, 0.37), rough_scale=1.06, normal_strength=0.78,
        )
        vest_wall, r_vw = _build_genie_pbr_material(
            f"{p}wall_vestibule", tex_dir, "wall_03", tile_m=1.60, projection="XZ",
            tint=(0.92, 0.89, 0.84), rough_scale=1.00, normal_strength=0.72,
        )
        genie_records.extend([r_fl, r_wl, r_vw])
        bank["wall_vestibule"] = vest_wall

    audit["genie_textures"] = genie_records
    audit["all_genie_textures_linked"] = all(r["linked_verified"] for r in genie_records)

    bank["floor"] = floor_mat
    bank["wall"] = wall_mat
    bank["oak"] = _make_oak_material(f"{p}oak")
    bank["oak_dark"] = _make_oak_material(
        f"{p}oak_dark", base_dark=(0.08, 0.045, 0.022, 1.0), base_light=(0.21, 0.12, 0.06, 1.0)
    )
    bank["steel"] = _make_metal_material(f"{p}steel", (0.76, 0.78, 0.80, 1.0), 0.14, 0.24, 0.96)
    bank["steel_dark"] = _make_metal_material(f"{p}steel_dark", (0.16, 0.17, 0.19, 1.0), 0.32, 0.46, 0.86)
    bank["brass"] = _make_metal_material(f"{p}brass", (0.83, 0.64, 0.28, 1.0), 0.17, 0.27, 0.95)
    bank["ceramic"] = _make_ceramic_material(f"{p}ceramic", (0.88, 0.85, 0.80, 1.0), 0.11)
    bank["ceramic_espresso"] = _make_ceramic_material(f"{p}ceramic_dark", (0.20, 0.23, 0.22, 1.0), 0.13)
    bank["rubber"] = _make_paint_material(f"{p}rubber", (0.055, 0.058, 0.062, 1.0), roughness=0.74, coat=0.0)
    bank["cloth"] = _make_cloth_material(f"{p}cloth", (0.64, 0.58, 0.49, 1.0), roughness=0.86, weave_scale=68.0)
    bank["cloth_mop"] = _make_cloth_material(f"{p}cloth_mop", (0.56, 0.66, 0.72, 1.0), roughness=0.90, weave_scale=95.0, bump_strength=0.14)
    bank["paper"] = _make_cloth_material(f"{p}paper", (0.85, 0.82, 0.76, 1.0), roughness=0.82, weave_scale=110.0, bump_strength=0.03)
    bank["glass"] = _make_glass_material(f"{p}glass", (0.94, 0.97, 0.96, 1.0), roughness=0.03, transmission=0.92)
    bank["glass_window"] = _make_glass_material(
        f"{p}glass_window", (0.95, 0.97, 0.98, 1.0), roughness=0.02, transmission=0.90, architectural_shadow=True
    )
    bank["glass_amber"] = _make_glass_material(f"{p}glass_amber", (0.58, 0.24, 0.05, 1.0), roughness=0.05, transmission=0.78)
    bank["liquid"] = _make_liquid_material(
        f"{p}liquid",
        tint=(0.88, 0.94, 0.98, 1.0) if case == "cafe" else (0.86, 0.90, 0.92, 1.0),
        transmission=0.90,
        roughness=0.02,
        ripple=0.015,
    )
    bank["liquid_espresso"] = _make_liquid_material(
        f"{p}liquid_espresso", tint=(0.07, 0.022, 0.008, 1.0), transmission=0.22, roughness=0.03, ripple=0.008
    )
    bank["drop"] = _make_liquid_material(
        f"{p}drop", tint=(0.84, 0.94, 1.0, 1.0), transmission=0.92, roughness=0.012, ripple=0.0
    )
    bank["pastry"] = _make_pastry_material(f"{p}pastry")
    bank["paint"] = _make_paint_material(
        f"{p}paint",
        color=(0.24, 0.30, 0.28, 1.0) if case == "cafe" else (0.24, 0.27, 0.30, 1.0),
        roughness=0.32,
        coat=0.22,
    )
    bank["parcel"] = _make_parcel_material(f"{p}parcel")
    bank["door"] = _make_metal_material(f"{p}door", (0.14, 0.15, 0.17, 1.0), 0.38, 0.48, metallic=0.22, bump_strength=0.04)
    bank["slate"] = _make_paint_material(f"{p}slate", (0.11, 0.115, 0.125, 1.0), roughness=0.45, coat=0.10)
    bank["coffee_beans"] = _make_paint_material(f"{p}coffee_beans", (0.09, 0.048, 0.024, 1.0), roughness=0.38, coat=0.18)
    bank["foliage"] = _make_paint_material(f"{p}foliage", (0.12, 0.24, 0.10, 1.0), roughness=0.52, coat=0.08)
    return bank


# ---------------------------------------------------------------------------
# Host View Geometry & Human Skin Dressing
# ---------------------------------------------------------------------------

def _iter_view_geoms(view: Any) -> list[tuple[bpy.types.Object, dict[str, Any]]]:
    obs = getattr(view, "obs", None)
    spec = getattr(view, "spec", None)
    pairs: list[tuple[bpy.types.Object, dict[str, Any]]] = []
    if obs is None:
        return pairs
    if isinstance(obs, dict):
        for k, obj in obs.items():
            if obj is None or getattr(obj, "type", None) != "MESH":
                continue
            g = spec.get(k, {}) if isinstance(spec, dict) else {}
            pairs.append((obj, g if isinstance(g, dict) else {}))
    elif isinstance(obs, (list, tuple)):
        if isinstance(spec, (list, tuple)):
            for obj, g in zip(obs, spec):
                if obj is None or getattr(obj, "type", None) != "MESH":
                    continue
                pairs.append((obj, g if isinstance(g, dict) else {}))
        else:
            for obj in obs:
                if obj is None or getattr(obj, "type", None) != "MESH":
                    continue
                pairs.append((obj, {}))
    return pairs


def _resolve_geom_role(g: dict[str, Any], meta: Any, obj: bpy.types.Object) -> tuple[str, str, str, Any]:
    gname = str(g.get("name", "") or obj.name or "")
    bname = str(g.get("body", "") or "")
    mat_ref = g.get("mat", None)
    mat_name = ""
    mat_rgba = None

    mats = meta.get("materials") if isinstance(meta, dict) else None
    if mats is not None and mat_ref is not None:
        entry = None
        if isinstance(mats, dict):
            entry = mats.get(mat_ref) or mats.get(str(mat_ref))
        elif isinstance(mats, (list, tuple)) and isinstance(mat_ref, int) and 0 <= mat_ref < len(mats):
            entry = mats[mat_ref]
        if isinstance(entry, dict):
            mat_name = str(entry.get("name", "") or "")
            mat_rgba = entry.get("rgba")
        elif isinstance(entry, str):
            mat_name = entry
    elif isinstance(mat_ref, str):
        mat_name = mat_ref

    if not mat_name and obj.data and len(obj.data.materials) > 0 and obj.data.materials[0] is not None:
        mat_name = obj.data.materials[0].name
    return mat_name.strip().lower(), gname.lower(), bname.lower(), mat_rgba


def _world_bbox(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def _dress_view_geoms(
    view: Any,
    case: str,
    bank: dict[str, bpy.types.Material],
    audit: dict[str, Any],
) -> dict[str, Any]:
    """Assign rich role shaders to physics geoms and gather scene bounds/portal metadata."""
    meta = getattr(view, "meta", {}) or {}
    pairs = _iter_view_geoms(view)
    role_counts: dict[str, int] = {}
    custom_paint_cache: dict[tuple[int, int, int], bpy.types.Material] = {}
    door_objs: list[bpy.types.Object] = []
    wall_objs: list[bpy.types.Object] = []
    floor_objs: list[bpy.types.Object] = []
    droplet_count = 0

    for obj, g in pairs:
        role_raw, gname, bname, rgba = _resolve_geom_role(g, meta, obj)

        # Visual water droplets: drop_0, drop_1, ...
        if gname.startswith("drop_") or "droplet" in gname or obj.name.lower().startswith("drop_"):
            _assign_mat(obj, bank["drop"])
            droplet_count += 1
            role_counts["drop"] = role_counts.get("drop", 0) + 1
            continue

        # Identify role name (exact or prefix/suffix match)
        role = role_raw if role_raw in MJCF_COLOR_ROLES else ""
        if not role:
            for candidate in MJCF_COLOR_ROLES:
                if role_raw.endswith(candidate) or role_raw.startswith(candidate + "_") or gname == candidate:
                    role = candidate
                    break

        if not role:
            continue

        # Semantic refinements within roles
        if role == "cloth" and any(k in gname or k in bname for k in ("mop", "pad", "wipe", "microfiber")):
            chosen = bank["cloth_mop"]
        elif role == "liquid" and any(k in gname or k in bname for k in ("coffee", "espresso", "cup")):
            chosen = bank["liquid_espresso"]
        elif role == "paint" and rgba is not None and len(rgba) >= 3:
            rgb = (float(rgba[0]), float(rgba[1]), float(rgba[2]))
            key = (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))
            if key not in custom_paint_cache:
                # Keep faithful hue while avoiding clipped/neon values under AgX
                mean_c = sum(rgb) / 3.0
                safe_rgb = tuple(min(0.84, max(0.03, c * 0.88 + mean_c * 0.12)) for c in rgb)
                custom_paint_cache[key] = _make_paint_material(
                    f"NL_{case}_paint_{key[0]}_{key[1]}_{key[2]}",
                    color=(safe_rgb[0], safe_rgb[1], safe_rgb[2], 1.0),
                )
            chosen = custom_paint_cache[key]
        else:
            chosen = bank[role]

        _assign_mat(obj, chosen)
        role_counts[role] = role_counts.get(role, 0) + 1

        if role == "door" or "door" in gname or "door" in bname:
            door_objs.append(obj)
        elif role == "wall":
            wall_objs.append(obj)
        elif role == "floor":
            floor_objs.append(obj)

    audit["physics_role_assignments"] = role_counts
    audit["droplet_meshes_shaded"] = droplet_count

    return {
        "door_objs": door_objs,
        "wall_objs": wall_objs,
        "floor_objs": floor_objs,
        "all_view_objs": [o for o, _ in pairs],
    }


def _dress_human_skins(
    scene: bpy.types.Scene,
    view: Any,
    case: str,
    audit: dict[str, Any],
) -> None:
    """Preserve original UV skin/face/hair atlas textures; adapt clothing to natural non-neon fabrics."""
    raw_skins = getattr(view, "skins", None)
    skin_objs: list[bpy.types.Object] = []
    if isinstance(raw_skins, dict):
        skin_objs = [o for o in raw_skins.values() if getattr(o, "type", None) == "MESH"]
    elif isinstance(raw_skins, (list, tuple, set)):
        skin_objs = [o for o in raw_skins if getattr(o, "type", None) == "MESH"]

    if not skin_objs:
        skin_objs = [
            o for o in scene.objects
            if o.type == "MESH" and o.name.lower().startswith("uniform_")
        ]

    # Case-appropriate realistic, non-neon wardrobe palettes
    if case == "cafe":
        palettes = {
            "shirt": (0.72, 0.67, 0.59, 1.0),     # Warm oatmeal cotton oxford
            "vest": (0.17, 0.19, 0.16, 1.0),      # Tailored olive-charcoal knit vest
            "jeans": (0.10, 0.14, 0.22, 1.0),     # Classic dark indigo denim
            "shoes": (0.15, 0.13, 0.11, 1.0),     # Espresso suede/leather sneakers
            "gloves": (0.24, 0.21, 0.19, 1.0),    # Muted warm taupe knit (non-neon)
        }
    else:
        palettes = {
            "shirt": (0.27, 0.29, 0.31, 1.0),     # Heather slate cotton work shirt
            "vest": (0.11, 0.14, 0.20, 1.0),      # Dark navy utility vest
            "jeans": (0.09, 0.12, 0.19, 1.0),     # Dark indigo work denim
            "shoes": (0.12, 0.12, 0.13, 1.0),     # Matte charcoal work sneakers
            "gloves": (0.15, 0.21, 0.27, 1.0),    # Matte slate-blue lab nitrile gloves
        }

    records: list[dict[str, Any]] = []
    preserved_textures: list[dict[str, Any]] = []

    for obj in skin_objs:
        nm = obj.name.lower()
        # Preserve original UV skin, face, hair, eyes, teeth untouched in texture
        is_skin_or_face = any(k in nm for k in ("skin", "face", "head", "hair", "eye", "teeth", "lash", "brow"))
        garment = None
        if not is_skin_or_face:
            if any(k in nm for k in ("vest", "apron", "jacket", "coat")):
                garment = "vest"
            elif any(k in nm for k in ("glove",)):
                garment = "gloves"
            elif any(k in nm for k in ("jean", "pant", "trouser")):
                garment = "jeans"
            elif any(k in nm for k in ("shirt", "top", "sweater")):
                garment = "shirt"
            elif any(k in nm for k in ("shoe", "tennis", "boot", "sneaker")):
                garment = "shoes"

        if is_skin_or_face or garment is None:
            linked_imgs: list[str] = []
            for mat in obj.data.materials:
                if mat is None or not mat.use_nodes:
                    continue
                nt = mat.node_tree
                bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
                for node in nt.nodes:
                    if node.type == "TEX_IMAGE" and node.image is not None:
                        fp = bpy.path.abspath(node.image.filepath) if node.image.filepath else node.image.name
                        linked_imgs.append(fp)
                        preserved_textures.append(
                            {
                                "object": obj.name,
                                "material": mat.name,
                                "image": fp,
                                "colorspace": node.image.colorspace_settings.name,
                            }
                        )
                if bsdf is not None and "skin" in nm:
                    if not bsdf.inputs["Roughness"].is_linked:
                        _set_bsdf(bsdf, "Roughness", 0.44)
                    _set_bsdf(bsdf, "Specular IOR Level", 0.42)
                    _set_bsdf(bsdf, "Coat Weight", 0.0)
                    _set_bsdf(bsdf, "Metallic", 0.0)
                    _set_bsdf(bsdf, "Subsurface Weight", 0.08)
                    _set_bsdf(bsdf, "Subsurface Scale", 0.008)
            records.append(
                {"object": obj.name, "action": "preserved_original_uv_skin", "textures": linked_imgs}
            )
        else:
            col_rgba = palettes[garment]
            if garment == "gloves" and case == "darkroom":
                gmat = _make_paint_material(
                    f"NL_{case}_human_{garment}", color=col_rgba, roughness=0.46, coat=0.06
                )
            elif garment == "shoes":
                gmat = _make_paint_material(
                    f"NL_{case}_human_{garment}", color=col_rgba, roughness=0.68, coat=0.02
                )
            else:
                weave = 92.0 if garment == "jeans" else 74.0
                bump = 0.11 if garment == "jeans" else 0.07
                gmat = _make_cloth_material(
                    f"NL_{case}_human_{garment}",
                    color=col_rgba,
                    roughness=0.88 if garment == "jeans" else 0.85,
                    weave_scale=weave,
                    bump_strength=bump,
                )
            _assign_mat(obj, gmat)
            records.append(
                {
                    "object": obj.name,
                    "action": f"adapted_garment_{garment}",
                    "material": gmat.name,
                    "rgba": [round(c, 3) for c in col_rgba],
                }
            )

    audit["human_skins"] = records
    audit["preserved_human_textures"] = preserved_textures
    audit["skin_textures_preserved"] = True


# ---------------------------------------------------------------------------
# Optional Local Ready-Made Asset Library Integration (world_assets.py)
# ---------------------------------------------------------------------------

def _load_world_assets(library: Any) -> Any | None:
    if library is not None and hasattr(library, "place"):
        return library
    wa_path = OUT / "mobile_worlds/library/world_assets.py"
    if not wa_path.is_file():
        return None
    try:
        wa_dir = str(wa_path.parent)
        if wa_dir not in sys.path:
            sys.path.insert(0, wa_dir)
        spec = importlib.util.spec_from_file_location("world_assets", str(wa_path))
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod if hasattr(mod, "place") else None
    except Exception:
        return None


def _try_place_asset(
    wa: Any | None,
    key: str,
    loc: tuple[float, float, float],
    size: float | None = None,
    yaw: float = 0.0,
    audit: dict[str, Any] | None = None,
) -> bpy.types.Object | None:
    if wa is None:
        if audit is not None:
            audit.setdefault("asset_fallbacks", []).append({"key": key, "reason": "world_assets_unavailable"})
        return None
    try:
        obj = wa.place(key, loc, size=size, yaw=yaw)
        if audit is not None:
            audit.setdefault("placed_library_assets", []).append(
                {
                    "key": key,
                    "object": getattr(obj, "name", str(obj)),
                    "location": [round(v, 3) for v in loc],
                    "size": size,
                    "yaw_rad": round(yaw, 3),
                }
            )
        return obj
    except Exception as exc:
        if audit is not None:
            audit.setdefault("asset_fallbacks", []).append({"key": key, "reason": str(exc)})
        return None


# ---------------------------------------------------------------------------
# Reusable Architectural & Hero Prop Builders
# ---------------------------------------------------------------------------

def _ensure_room_shell(
    case: str,
    view_info: dict[str, Any],
    bank: dict[str, bpy.types.Material],
    col: bpy.types.Collection,
    added_props: list[str],
) -> None:
    """Add missing boundary walls/ceiling (y=2.30, x=+-3.20) without blocking camera or partition."""
    bpy.context.view_layer.update()
    has_back = False
    has_left = False
    has_right = False
    has_floor = len(view_info["floor_objs"]) > 0

    for w in view_info["wall_objs"]:
        mn, mx = _world_bbox(w)
        if mx.y >= 2.15 and (mx.x - mn.x) > 2.5:
            has_back = True
        if mn.x <= -2.95 and (mx.y - mn.y) > 1.5:
            has_left = True
        if mx.x >= 2.95 and (mx.y - mn.y) > 1.5:
            has_right = True

    p = f"NL_{case}_Arch_"
    if not has_floor:
        added_props.append(_make_box(f"{p}Floor", (6.50, 5.20, 0.06), (0.0, -0.25, -0.03), mat=bank["floor"], col=col).name)
    if not has_back:
        added_props.append(_make_box(f"{p}BackWall", (6.50, 0.08, 3.15), (0.0, 2.34, 1.575), mat=bank["wall"], col=col).name)
    if not has_left:
        added_props.append(_make_box(f"{p}LeftWall", (0.08, 4.90, 3.15), (-3.24, -0.10, 1.575), mat=bank["wall"], col=col).name)
    if not has_right:
        added_props.append(_make_box(f"{p}RightWall", (0.08, 4.90, 3.15), (3.24, -0.10, 1.575), mat=bank["wall"], col=col).name)

    # Ceiling slab high at z=3.14 (never obstructs camera; keeps lighting physically enclosed)
    added_props.append(
        _make_box(f"{p}Ceiling", (6.52, 4.80, 0.06), (0.0, -0.05, 3.15), mat=bank["slate"] if case == "darkroom" else bank["wall"], col=col).name
    )


def _add_framed_sign(
    name: str,
    lines: list[str],
    width: float,
    height: float,
    loc: tuple[float, float, float],
    rot: tuple[float, float, float],
    frame_mat: bpy.types.Material,
    bg: tuple[float, float, float],
    fg: tuple[float, float, float],
    border: tuple[float, float, float] | None,
    col: bpy.types.Collection,
    added_props: list[str],
    gen_textures: list[str],
    emission_strength: float = 0.0,
) -> None:
    sign_mat, img_name = _make_sign_material(
        f"{name}_mat", lines, bg=bg, fg=fg, border=border, emission_strength=emission_strength
    )
    gen_textures.append(img_name)

    # Backing board + 4-sided beveled frame
    frame_d = 0.024
    border_t = 0.024
    rot_m = Euler(rot, "XYZ").to_matrix()
    center = Vector(loc)

    def _local_to_world(dx: float, dy: float, dz: float) -> tuple[float, float, float]:
        p = center + rot_m @ Vector((dx, dy, dz))
        return (p.x, p.y, p.z)

    added_props.append(_make_box(f"{name}_back", (width, 0.012, height), _local_to_world(0, 0.004, 0), rot=rot, mat=frame_mat, col=col).name)
    added_props.append(_make_box(f"{name}_top", (width + 2 * border_t, frame_d, border_t), _local_to_world(0, -0.002, height / 2 + border_t / 2), rot=rot, bevel=0.004, mat=frame_mat, col=col).name)
    added_props.append(_make_box(f"{name}_bot", (width + 2 * border_t, frame_d, border_t), _local_to_world(0, -0.002, -height / 2 - border_t / 2), rot=rot, bevel=0.004, mat=frame_mat, col=col).name)
    added_props.append(_make_box(f"{name}_lft", (border_t, frame_d, height), _local_to_world(-width / 2 - border_t / 2, -0.002, 0), rot=rot, bevel=0.004, mat=frame_mat, col=col).name)
    added_props.append(_make_box(f"{name}_rgt", (border_t, frame_d, height), _local_to_world(width / 2 + border_t / 2, -0.002, 0), rot=rot, bevel=0.004, mat=frame_mat, col=col).name)
    added_props.append(_make_uv_quad(f"{name}_face", width, height, _local_to_world(0, -0.005, 0), rot=rot, mat=sign_mat, col=col).name)


def _add_potted_plant_fallback(
    name: str,
    loc: tuple[float, float, float],
    bank: dict[str, bpy.types.Material],
    col: bpy.types.Collection,
    added_props: list[str],
) -> None:
    x, y, z = loc
    added_props.append(_make_cyl(f"{name}_pot", 0.14, 0.30, (x, y, z + 0.15), r2=0.18, mat=bank["ceramic_espresso"], col=col).name)
    added_props.append(_make_cyl(f"{name}_soil", 0.165, 0.03, (x, y, z + 0.285), mat=bank["coffee_beans"], col=col).name)
    for idx in range(7):
        ang = idx * (2.0 * math.pi / 7.0)
        tilt = 0.25 + 0.15 * (idx % 2)
        h_leaf = 0.40 + 0.12 * (idx % 3)
        lx = x + math.cos(ang) * 0.09
        ly = y + math.sin(ang) * 0.09
        added_props.append(
            _make_box(
                f"{name}_leaf_{idx}",
                (0.08, 0.014, h_leaf),
                (lx, ly, z + 0.30 + h_leaf * 0.45),
                rot=(tilt * math.sin(ang), -tilt * math.cos(ang), ang),
                bevel=0.004,
                mat=bank["foliage"],
                col=col,
            ).name
        )


# ---------------------------------------------------------------------------
# Case 1: CAFE — Late-Afternoon / Early-Evening Standing Espresso Bar
# ---------------------------------------------------------------------------

def _dress_cafe_set(
    bank: dict[str, bpy.types.Material],
    wa: Any | None,
    col: bpy.types.Collection,
    audit: dict[str, Any],
    added_props: list[str],
    gen_textures: list[str],
) -> None:
    """Dress cafe strictly behind y>=1.78 / side walls / overhead, keeping table & patron envelopes clear."""
    p = "NL_Cafe_"
    ext_mat, ext_img = _make_cafe_exterior_material(f"{p}OutdoorBackdrop")
    gen_textures.append(ext_img)

    # 1. Oak baseboards & wainscoting along back (y=2.285) and side walls (x=+-3.185)
    added_props.append(_make_box(f"{p}Wainscot_Back", (6.36, 0.025, 1.02), (0.0, 2.285, 0.51), mat=bank["oak_dark"], col=col).name)
    added_props.append(_make_box(f"{p}ChairRail_Back", (6.36, 0.048, 0.045), (0.0, 2.275, 1.035), bevel=0.008, mat=bank["oak"], col=col).name)
    added_props.append(_make_box(f"{p}Wainscot_Left", (0.025, 4.40, 1.02), (-3.185, 0.10, 0.51), mat=bank["oak_dark"], col=col).name)
    added_props.append(_make_box(f"{p}ChairRail_Left", (0.048, 4.40, 0.045), (-3.175, 0.10, 1.035), bevel=0.008, mat=bank["oak"], col=col).name)
    added_props.append(_make_box(f"{p}Wainscot_Right", (0.025, 4.40, 1.02), (3.185, 0.10, 0.51), mat=bank["oak_dark"], col=col).name)
    added_props.append(_make_box(f"{p}ChairRail_Right", (0.048, 4.40, 0.045), (3.175, 0.10, 1.035), bevel=0.008, mat=bank["oak"], col=col).name)

    # Subtle ceiling oak rafters (high at z=3.02)
    for idx, rx in enumerate((-2.2, -0.7, 0.8, 2.3)):
        added_props.append(_make_box(f"{p}CeilingBeam_{idx}", (0.12, 4.20, 0.14), (rx, 0.20, 3.04), bevel=0.01, mat=bank["oak_dark"], col=col).name)

    # 2. Bistro framed lit windows with soft photo-look late-afternoon outdoors behind glass
    def _build_window(tag: str, loc: tuple[float, float, float], rot_z: float, w: float, h: float) -> None:
        rm = Euler((0.0, 0.0, rot_z), "XYZ").to_matrix()
        c = Vector(loc)
        rot = (0.0, 0.0, rot_z)

        def _w(dx: float, dy: float, dz: float) -> tuple[float, float, float]:
            pt = c + rm @ Vector((dx, dy, dz))
            return (pt.x, pt.y, pt.z)

        # Glowing soft exterior depth plane behind glass
        added_props.append(_make_uv_quad(f"{tag}_outdoor", w - 0.06, h - 0.06, _w(0, 0.018, 0), rot=rot, mat=ext_mat, col=col).name)
        # Architectural glass pane
        added_props.append(_make_uv_quad(f"{tag}_glass", w - 0.06, h - 0.06, _w(0, -0.012, 0), rot=rot, mat=bank["glass_window"], col=col).name)
        # Outer timber casing & sill
        ft, fd = 0.075, 0.07
        added_props.append(_make_box(f"{tag}_top", (w + 0.04, fd, ft), _w(0, -0.01, h / 2), rot=rot, bevel=0.008, mat=bank["oak_dark"], col=col).name)
        added_props.append(_make_box(f"{tag}_sill", (w + 0.10, fd + 0.05, ft * 0.9), _w(0, -0.03, -h / 2), rot=rot, bevel=0.008, mat=bank["oak"], col=col).name)
        added_props.append(_make_box(f"{tag}_lft", (ft, fd, h), _w(-w / 2, -0.01, 0), rot=rot, bevel=0.008, mat=bank["oak_dark"], col=col).name)
        added_props.append(_make_box(f"{tag}_rgt", (ft, fd, h), _w(w / 2, -0.01, 0), rot=rot, bevel=0.008, mat=bank["oak_dark"], col=col).name)
        # Muntin/mullion bars
        added_props.append(_make_box(f"{tag}_mulV", (0.034, 0.045, h - 0.06), _w(0, -0.022, 0), rot=rot, bevel=0.004, mat=bank["oak_dark"], col=col).name)
        added_props.append(_make_box(f"{tag}_mulH1", (w - 0.06, 0.045, 0.034), _w(0, -0.022, h * 0.18), rot=rot, bevel=0.004, mat=bank["oak_dark"], col=col).name)
        added_props.append(_make_box(f"{tag}_mulH2", (w - 0.06, 0.045, 0.034), _w(0, -0.022, -h * 0.18), rot=rot, bevel=0.004, mat=bank["oak_dark"], col=col).name)

    # Back-left storefront window (clear of human patron head at x=-0.60!)
    _build_window(f"{p}WinBack", (-1.98, 2.26, 1.82), 0.0, 1.38, 1.46)
    # Left side bistro window admitting golden-hour afternoon sun
    _build_window(f"{p}WinLeft", (-3.16, 0.72, 1.82), math.pi * 0.5, 1.65, 1.46)

    # 3. Back Espresso Bar Cabinetry (x in [0.15, 2.55], y in [1.80, 2.28], top z=0.92)
    bar_x0, bar_x1 = 0.15, 2.55
    bar_w = bar_x1 - bar_x0
    bar_cx = 0.5 * (bar_x0 + bar_x1)
    added_props.append(_make_box(f"{p}BarBase", (bar_w, 0.46, 0.88), (bar_cx, 2.04, 0.44), bevel=0.006, mat=bank["oak_dark"], col=col).name)
    added_props.append(_make_box(f"{p}BarCounterTop", (bar_w + 0.06, 0.52, 0.045), (bar_cx, 2.02, 0.902), bevel=0.008, mat=bank["oak"], col=col).name)
    # Recessed cabinet door panels + brass handles
    for idx in range(4):
        px = bar_x0 + 0.30 + idx * 0.60
        added_props.append(_make_box(f"{p}CabDoor_{idx}", (0.52, 0.022, 0.72), (px, 1.805, 0.46), bevel=0.005, mat=bank["oak"], col=col).name)
        added_props.append(_make_cyl(f"{p}CabHandle_{idx}", 0.008, 0.14, (px + 0.18, 1.785, 0.62), mat=bank["brass"], col=col).name)

    # 4. Hero Commercial Dual-Group Stainless Espresso Machine (x=1.18, y=2.01, z=0.925)
    ex, ey, ez = 1.18, 2.01, 0.925
    added_props.append(_make_box(f"{p}EspBodyLower", (0.72, 0.40, 0.12), (ex, ey, ez + 0.06), bevel=0.01, mat=bank["steel"], col=col).name)
    added_props.append(_make_box(f"{p}EspBodyRear", (0.72, 0.26, 0.40), (ex, ey + 0.07, ez + 0.24), bevel=0.015, mat=bank["steel"], col=col).name)
    added_props.append(_make_box(f"{p}EspHeader", (0.72, 0.38, 0.14), (ex, ey + 0.01, ez + 0.38), bevel=0.014, mat=bank["steel"], col=col).name)
    added_props.append(_make_box(f"{p}EspDripGrille", (0.66, 0.16, 0.018), (ex, ey - 0.11, ez + 0.125), bevel=0.003, mat=bank["steel_dark"], col=col).name)
    # Cup warmer brass rail on top
    added_props.append(_make_box(f"{p}EspRailBack", (0.68, 0.012, 0.055), (ex, ey + 0.17, ez + 0.475), mat=bank["brass"], col=col).name)
    added_props.append(_make_box(f"{p}EspRailL", (0.012, 0.32, 0.055), (ex - 0.335, ey + 0.02, ez + 0.475), mat=bank["brass"], col=col).name)
    added_props.append(_make_box(f"{p}EspRailR", (0.012, 0.32, 0.055), (ex + 0.335, ey + 0.02, ez + 0.475), mat=bank["brass"], col=col).name)
    # Dual brass/steel group heads, portafilters, steam wands, gauges
    for gi, gx in enumerate((ex - 0.17, ex + 0.17)):
        added_props.append(_make_cyl(f"{p}EspGroup_{gi}", 0.055, 0.09, (gx, ey - 0.11, ez + 0.28), mat=bank["brass"], col=col).name)
        added_props.append(_make_cyl(f"{p}EspPortafilter_{gi}", 0.042, 0.045, (gx, ey - 0.11, ez + 0.22), mat=bank["steel"], col=col).name)
        added_props.append(_make_cyl(f"{p}EspHandle_{gi}", 0.015, 0.15, (gx, ey - 0.20, ez + 0.22), rot=(math.pi * 0.5, 0.0, 0.0), mat=bank["oak_dark"], col=col).name)
        added_props.append(_make_cyl(f"{p}EspGauge_{gi}", 0.032, 0.015, (gx, ey - 0.185, ez + 0.38), rot=(math.pi * 0.5, 0.0, 0.0), mat=bank["ceramic"], col=col).name)
    for si, sx in enumerate((ex - 0.30, ex + 0.30)):
        added_props.append(_make_cyl(f"{p}EspSteamWand_{si}", 0.006, 0.20, (sx, ey - 0.14, ez + 0.24), rot=(0.22, 0.12 if si else -0.12, 0.0), mat=bank["steel"], col=col).name)
    # Warmed porcelain cups stacked on top of espresso machine
    for ci, cx in enumerate((ex - 0.22, ex - 0.09, ex + 0.04, ex + 0.17)):
        added_props.append(_make_cyl(f"{p}EspTopCup_{ci}", 0.034, 0.062, (cx, ey + 0.04, ez + 0.48), r2=0.028, mat=bank["ceramic"], col=col).name)

    # 5. Commercial Coffee Grinder (x=1.82, y=2.01, z=0.925)
    gx, gy, gz = 1.82, 2.01, 0.925
    added_props.append(_make_box(f"{p}GrindBase", (0.20, 0.28, 0.06), (gx, gy, gz + 0.03), bevel=0.008, mat=bank["steel_dark"], col=col).name)
    added_props.append(_make_cyl(f"{p}GrindBody", 0.088, 0.24, (gx, gy + 0.02, gz + 0.17), mat=bank["steel_dark"], col=col).name)
    added_props.append(_make_cyl(f"{p}GrindCollar", 0.072, 0.04, (gx, gy + 0.02, gz + 0.31), mat=bank["brass"], col=col).name)
    added_props.append(_make_cyl(f"{p}GrindBeans", 0.082, 0.13, (gx, gy + 0.02, gz + 0.39), r2=0.105, mat=bank["coffee_beans"], col=col).name)
    added_props.append(_make_cyl(f"{p}GrindHopper", 0.095, 0.20, (gx, gy + 0.02, gz + 0.43), r2=0.125, mat=bank["glass"], col=col).name)
    added_props.append(_make_cyl(f"{p}GrindLid", 0.128, 0.018, (gx, gy + 0.02, gz + 0.54), mat=bank["steel_dark"], col=col).name)

    # 6. Countertop Ceramic Canisters, Glass Pastry Cloche & Brass Pour-Over Kettle
    added_props.append(_make_cyl(f"{p}ClocheBase", 0.145, 0.024, (0.48, 2.00, ez + 0.012), mat=bank["oak"], col=col).name)
    added_props.append(_make_cyl(f"{p}ClochePastry", 0.075, 0.048, (0.48, 2.00, ez + 0.048), r2=0.055, mat=bank["pastry"], col=col).name)
    added_props.append(_make_cyl(f"{p}ClocheDome", 0.132, 0.15, (0.48, 2.00, ez + 0.10), r2=0.108, mat=bank["glass"], col=col).name)
    added_props.append(_make_cyl(f"{p}KettleBody", 0.068, 0.14, (2.25, 2.00, ez + 0.07), r2=0.050, mat=bank["brass"], col=col).name)
    added_props.append(_make_cyl(f"{p}KettleLid", 0.052, 0.015, (2.25, 2.00, ez + 0.146), mat=bank["oak_dark"], col=col).name)

    # 7. Back-Bar Floating Oak Shelves & Coffeeware (x in [0.25, 2.48], y=2.14, z=1.60 & z=1.96)
    for si, sz in enumerate((1.60, 1.96)):
        added_props.append(_make_box(f"{p}Shelf_{si}", (2.24, 0.24, 0.036), (1.36, 2.16, sz), bevel=0.005, mat=bank["oak"], col=col).name)
        for bi, bx in enumerate((0.46, 1.36, 2.26)):
            added_props.append(_make_box(f"{p}ShelfBracket_{si}_{bi}", (0.022, 0.20, 0.12), (bx, 2.18, sz - 0.075), mat=bank["brass"], col=col).name)

    # Lower shelf props (ceramics, glass syrup bottles, optional brass_vase from world_assets)
    for idx, cx in enumerate((0.42, 0.56, 0.70, 0.84)):
        added_props.append(_make_cyl(f"{p}ShelfCup_{idx}", 0.038, 0.075, (cx, 2.14, 1.655), r2=0.044, mat=bank["ceramic"], col=col).name)
    for idx, bx in enumerate((1.15, 1.28, 1.41)):
        added_props.append(_make_cyl(f"{p}SyrupBottle_{idx}", 0.036, 0.22, (bx, 2.15, 1.728), r2=0.030, mat=bank["glass_amber"], col=col).name)
    for idx, cx in enumerate((1.88, 2.06, 2.24)):
        added_props.append(_make_cyl(f"{p}CoffeeTin_{idx}", 0.056, 0.16, (cx, 2.15, 1.698), mat=bank["ceramic_espresso"] if idx == 1 else bank["brass"], col=col).name)
    # Upper shelf glassware & vase
    placed_vase = _try_place_asset(wa, "brass_vase", (0.58, 2.15, 1.978), size=0.28, yaw=0.2, audit=audit)
    if placed_vase is None:
        added_props.append(_make_cyl(f"{p}UpperVase", 0.052, 0.22, (0.58, 2.15, 2.088), r2=0.036, mat=bank["brass"], col=col).name)
    for idx, gx_pos in enumerate((1.98, 2.12, 2.26)):
        added_props.append(_make_cyl(f"{p}Carafe_{idx}", 0.042, 0.17, (gx_pos, 2.15, 2.063), r2=0.032, mat=bank["glass"], col=col).name)

    # 8. Mounted Framed English Cafe Menu Board (to the right, above shelves, clear of human face!)
    _add_framed_sign(
        f"{p}MenuBoard",
        ["ESPRESSO BAR", "ESPRESSO  CORTADO  LATTE", "POUR OVER  PASTRIES"],
        width=1.08,
        height=0.46,
        loc=(1.36, 2.275, 2.40),
        rot=(0.0, 0.0, 0.0),
        frame_mat=bank["oak"],
        bg=(0.09, 0.10, 0.11),
        fg=(0.88, 0.84, 0.74),
        border=(0.72, 0.56, 0.30),
        col=col,
        added_props=added_props,
        gen_textures=gen_textures,
    )

    # 9. Potted Plants in Back Corners (outside robot & patron zones)
    for tag, key, loc, yaw in (
        (f"{p}PlantL", "potted_plant", (-2.68, 1.88, 0.0), 0.4),
        (f"{p}PlantR", "potted_fern", (2.78, 1.88, 0.0), -0.6),
    ):
        if _try_place_asset(wa, key, loc, size=0.95, yaw=yaw, audit=audit) is None:
            _add_potted_plant_fallback(tag, loc, bank, col, added_props)

    # 10. Three Hanging Practical Brass Pendant Shades (high z=2.34, warm glowing bulbs)
    bulb_mat = _make_emissive_material(f"{p}WarmBulb", (1.0, 0.78, 0.45, 1.0), strength=14.0, roughness=0.10)
    for idx, (px, py) in enumerate(((-0.60, 0.67), (0.85, 0.67), (1.28, 1.98))):
        added_props.append(_make_cyl(f"{p}PendCord_{idx}", 0.005, 0.76, (px, py, 2.74), segs=12, mat=bank["rubber"], col=col).name)
        added_props.append(_make_cyl(f"{p}PendSocket_{idx}", 0.026, 0.06, (px, py, 2.38), mat=bank["brass"], col=col).name)
        added_props.append(_make_cyl(f"{p}PendShade_{idx}", 0.155, 0.12, (px, py, 2.30), r2=0.048, mat=bank["brass"], col=col).name)
        added_props.append(_make_cyl(f"{p}PendBulb_{idx}", 0.028, 0.055, (px, py, 2.265), segs=14, mat=bulb_mat, col=col).name)


def _setup_cafe_lights(
    scene: bpy.types.Scene,
    col: bpy.types.Collection,
    audit: dict[str, Any],
) -> Callable[[float, float, float], None]:
    """Art-directed late-afternoon sun + practical pendants + soft evening sky fill (Cycles & Eevee)."""
    p = "NL_Cafe_L_"
    lights: list[bpy.types.Object] = []

    # Warm dusk-golden world (low ambient so practicals & window sun shape shadows cleanly)
    world = scene.world or bpy.data.worlds.new("NL_Cafe_World")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    wout = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.34, 0.28, 0.24, 1.0)
    bg.inputs["Strength"].default_value = 0.18
    nt.links.new(bg.outputs["Background"], wout.inputs["Surface"])

    # 1. Golden-hour sunlight raking in from inside the left bistro window
    lights.append(
        _create_light(
            f"{p}AfternoonRake", "SPOT", (-3.04, 0.85, 2.15),
            energy=540.0, color=(1.0, 0.76, 0.48), col=col,
            target=(0.35, 0.70, 0.82), spot_deg=62.0, spot_blend=0.35, soft_size=0.14,
        )
    )
    # 2. Left window soft sky/afternoon area key
    lights.append(
        _create_light(
            f"{p}WindowKey", "AREA", (-3.06, 0.72, 1.82),
            energy=125.0, color=(1.0, 0.85, 0.68), col=col,
            target=(0.15, 0.75, 0.95), size=1.50, size_y=1.30, spread_deg=105.0,
        )
    )
    # 3. Back-left window warm rim light
    lights.append(
        _create_light(
            f"{p}BackWindowRim", "AREA", (-1.98, 2.16, 1.82),
            energy=88.0, color=(1.0, 0.80, 0.56), col=col,
            target=(-0.25, 0.55, 0.92), size=1.28, size_y=1.30, spread_deg=96.0,
        )
    )
    # 4. Practical pendant pool over Customer Table 1 (-0.60, 0.67)
    lights.append(
        _create_light(
            f"{p}PendantT1", "SPOT", (-0.60, 0.67, 2.22),
            energy=74.0, color=(1.0, 0.74, 0.44), col=col,
            target=(-0.60, 0.67, 0.88), spot_deg=76.0, spot_blend=0.55, soft_size=0.14,
        )
    )
    # 5. Practical pendant pool over Empty Table 2 (0.85, 0.67)
    lights.append(
        _create_light(
            f"{p}PendantT2", "SPOT", (0.85, 0.67, 2.22),
            energy=68.0, color=(1.0, 0.74, 0.44), col=col,
            target=(0.85, 0.67, 0.88), spot_deg=76.0, spot_blend=0.55, soft_size=0.14,
        )
    )
    # 6. Practical espresso bar counter & shelf highlight
    lights.append(
        _create_light(
            f"{p}BarHighlight", "AREA", (1.28, 1.88, 2.20),
            energy=62.0, color=(1.0, 0.77, 0.48), col=col,
            target=(1.28, 2.02, 0.95), size=1.45, size_y=0.36, spread_deg=92.0,
        )
    )
    # 7. Gentle cool-dusk camera-side fill so human face & robot arm stay cleanly modeled
    lights.append(
        _create_light(
            f"{p}FrontDuskFill", "AREA", (1.45, -1.75, 2.05),
            energy=44.0, color=(0.76, 0.85, 0.98), col=col,
            target=(-0.10, 0.85, 1.10), size=2.40, size_y=1.50, spread_deg=115.0, use_shadow=False,
        )
    )

    audit["lights"] = [_light_record(lo) for lo in lights]
    audit["world"] = {"name": world.name, "strength": 0.18, "color": [0.34, 0.28, 0.24]}

    def update_function(
        door_open_fraction: float = 0.0,
        cover_closed_fraction: float = 1.0,
        time_s: float = 0.0,
    ) -> dict[str, Any]:
        # Cafe lighting is steady across branches (no branch-index dependence)
        return {
            "case": "cafe",
            "door_open_fraction": float(door_open_fraction),
            "cover_closed_fraction": float(cover_closed_fraction),
            "time_s": float(time_s),
        }

    return update_function


# ---------------------------------------------------------------------------
# Case 2: DARKROOM — Warm Daylit Vestibule | Red-Lit Darkroom + Dynamic Spill
# ---------------------------------------------------------------------------

def _detect_darkroom_portal(door_objs: list[bpy.types.Object]) -> dict[str, float]:
    """Measure actual physics sliding door bounds; fall back to contract coordinates."""
    bpy.context.view_layer.update()
    default = {
        "portal_x": -0.60,
        "y_min": -0.825,
        "y_max": 0.325,
        "z_min": 0.0,
        "z_max": 2.15,
    }
    if not door_objs:
        return default
    mins = []
    maxs = []
    for d in door_objs:
        mn, mx = _world_bbox(d)
        mins.append(mn)
        maxs.append(mx)
    x_c = 0.5 * (min(v.x for v in mins) + max(v.x for v in maxs))
    y_min = min(v.y for v in mins)
    y_max = max(v.y for v in maxs)
    z_min = max(0.0, min(v.z for v in mins))
    z_max = max(v.z for v in maxs)
    width = y_max - y_min
    height = z_max - z_min
    if abs(x_c - (-0.60)) < 0.25 and 0.65 <= width <= 1.65 and height >= 1.5:
        return {
            "portal_x": float(x_c),
            "y_min": float(y_min),
            "y_max": float(y_max),
            "z_min": float(z_min),
            "z_max": float(z_max),
        }
    return default


def _dress_darkroom_set(
    bank: dict[str, bpy.types.Material],
    wa: Any | None,
    col: bpy.types.Collection,
    audit: dict[str, Any],
    added_props: list[str],
    gen_textures: list[str],
) -> dict[str, Any]:
    """Dress vestibule (x<-0.60) and darkroom (x>-0.60) without obscuring portal or work envelopes."""
    p = "NL_DR_"

    # --- VESTIBULE (LEFT, x in [-3.20, -0.62]) ---
    # Lighter plaster panel on vestibule back wall & left wall (using Genie Sim wall_03)
    added_props.append(_make_box(f"{p}VestBackPlaster", (2.52, 0.02, 3.08), (-1.92, 2.285, 1.54), mat=bank["wall_vestibule"], col=col).name)
    added_props.append(_make_box(f"{p}VestLeftPlaster", (0.02, 4.40, 3.08), (-3.185, 0.10, 1.54), mat=bank["wall_vestibule"], col=col).name)
    added_props.append(_make_box(f"{p}VestBaseboard", (2.52, 0.03, 0.14), (-1.92, 2.268, 0.07), mat=bank["oak_dark"], col=col).name)

    # Frosted warm daylight vestibule transom window on back wall (x in [-2.68, -1.24], z in [1.26, 2.42])
    frost_mat = _make_emissive_material(f"{p}VestDaylightGlass", (1.0, 0.94, 0.84, 1.0), strength=2.6, roughness=0.35)
    added_props.append(_make_uv_quad(f"{p}VestWinPane", 1.38, 1.08, (-1.96, 2.258, 1.84), mat=frost_mat, col=col).name)
    for tag, sz, lc in (
        ("Top", (1.48, 0.05, 0.06), (-1.96, 2.255, 2.41)),
        ("Bot", (1.48, 0.07, 0.06), (-1.96, 2.245, 1.27)),
        ("Lft", (0.06, 0.05, 1.18), (-2.67, 2.255, 1.84)),
        ("Rgt", (0.06, 0.05, 1.18), (-1.25, 2.255, 1.84)),
        ("Mul", (0.03, 0.04, 1.10), (-1.96, 2.248, 1.84)),
    ):
        added_props.append(_make_box(f"{p}VestWin_{tag}", sz, lc, bevel=0.005, mat=bank["steel_dark"], col=col).name)

    # Vestibule warm ceiling fixture housing (x=-1.88, y=0.20, z=2.92)
    vest_lamp_mat = _make_emissive_material(f"{p}VestLampEmit", (1.0, 0.90, 0.72, 1.0), strength=6.5, roughness=0.25)
    added_props.append(_make_box(f"{p}VestFixtureFrame", (0.98, 0.34, 0.06), (-1.88, 0.20, 2.98), bevel=0.005, mat=bank["steel_dark"], col=col).name)
    added_props.append(_make_box(f"{p}VestFixtureDiff", (0.90, 0.26, 0.025), (-1.88, 0.20, 2.94), mat=vest_lamp_mat, col=col).name)

    # Vestibule shipping console & stock boxes well behind robot corridor (y>=1.78 vs robot y=-0.25)
    added_props.append(_make_box(f"{p}VestBenchTop", (1.10, 0.44, 0.04), (-2.55, 2.02, 0.84), bevel=0.006, mat=bank["oak"], col=col).name)
    for li, (lx, ly) in enumerate(((-3.04, 1.84), (-2.06, 1.84), (-3.04, 2.20), (-2.06, 2.20))):
        added_props.append(_make_box(f"{p}VestBenchLeg_{li}", (0.045, 0.045, 0.82), (lx, ly, 0.41), mat=bank["steel_dark"], col=col).name)
    if _try_place_asset(wa, "stock_box", (-2.75, 2.02, 0.86), size=0.34, yaw=0.12, audit=audit) is None:
        added_props.append(_make_box(f"{p}VestBox", (0.32, 0.26, 0.22), (-2.75, 2.02, 0.97), bevel=0.005, mat=bank["parcel"], col=col).name)
    if _try_place_asset(wa, "potted_plant", (-1.52, 1.98, 0.0), size=0.88, yaw=0.5, audit=audit) is None:
        _add_potted_plant_fallback(f"{p}VestPlant", (-1.52, 1.98, 0.0), bank, col, added_props)

    # Mounted vestibule warning sign (away from partition portal)
    _add_framed_sign(
        f"{p}VestSign",
        ["DARKROOM IN USE", "WAIT FOR CLEARANCE"],
        width=0.56,
        height=0.26,
        loc=(-0.94, 2.265, 1.62),
        rot=(0.0, 0.0, 0.0),
        frame_mat=bank["steel_dark"],
        bg=(0.14, 0.14, 0.15),
        fg=(0.94, 0.86, 0.70),
        border=(0.76, 0.22, 0.12),
        col=col,
        added_props=added_props,
        gen_textures=gen_textures,
    )

    # --- DARKROOM (RIGHT, x in [-0.58, +3.20]) ---
    # 1. Stainless darkroom utility wash sink & reagent shelf (back-left darkroom corner: x in [-0.46, 0.36], y in [1.82, 2.28])
    sx, sy = -0.05, 2.04
    added_props.append(_make_box(f"{p}SinkCabinet", (0.82, 0.46, 0.82), (sx, sy, 0.41), bevel=0.005, mat=bank["steel_dark"], col=col).name)
    added_props.append(_make_box(f"{p}SinkRim", (0.84, 0.48, 0.06), (sx, sy, 0.85), bevel=0.006, mat=bank["steel"], col=col).name)
    added_props.append(_make_box(f"{p}SinkBacksplash", (0.84, 0.025, 0.22), (sx, 2.265, 0.97), mat=bank["steel"], col=col).name)
    added_props.append(_make_cyl(f"{p}FaucetStem", 0.014, 0.24, (sx, 2.21, 1.00), mat=bank["steel"], col=col).name)
    added_props.append(_make_cyl(f"{p}FaucetSpout", 0.011, 0.16, (sx, 2.13, 1.10), rot=(math.pi * 0.42, 0.0, 0.0), mat=bank["steel"], col=col).name)

    # Reagent shelf above sink (z=1.48) with amber chemical bottles + mounted chemical label strip
    added_props.append(_make_box(f"{p}ChemShelf", (0.88, 0.22, 0.028), (sx, 2.17, 1.48), bevel=0.004, mat=bank["steel_dark"], col=col).name)
    for bi, bx in enumerate((-0.34, -0.20, -0.06, 0.08, 0.22)):
        bh = 0.21 if bi % 2 == 0 else 0.17
        added_props.append(_make_cyl(f"{p}ReagentBottle_{bi}", 0.042, bh, (bx, 2.16, 1.494 + bh * 0.5), mat=bank["glass_amber"], col=col).name)
        added_props.append(_make_cyl(f"{p}ReagentCap_{bi}", 0.018, 0.032, (bx, 2.16, 1.505 + bh), mat=bank["rubber"], col=col).name)
    _add_framed_sign(
        f"{p}TrayLabels",
        ["DEVELOPER   STOP   FIXER"],
        width=0.78,
        height=0.14,
        loc=(-0.05, 2.275, 1.86),
        rot=(0.0, 0.0, 0.0),
        frame_mat=bank["steel_dark"],
        bg=(0.10, 0.10, 0.11),
        fg=(0.86, 0.80, 0.72),
        border=(0.55, 0.20, 0.14),
        col=col,
        added_props=added_props,
        gen_textures=gen_textures,
    )

    # 2. Optical Photo Enlarger Station on Back-Right Bench (x in [1.74, 2.98], y in [1.74, 2.28], z=0.88)
    bx, by, bz = 2.34, 2.00, 0.88
    added_props.append(_make_box(f"{p}EnlBenchTop", (1.24, 0.52, 0.045), (bx, by, bz - 0.022), bevel=0.006, mat=bank["oak_dark"], col=col).name)
    added_props.append(_make_box(f"{p}EnlBenchShelf", (1.16, 0.44, 0.028), (bx, by, 0.24), mat=bank["steel_dark"], col=col).name)
    for li, (lx, ly) in enumerate(((1.78, 1.78), (2.90, 1.78), (1.78, 2.22), (2.90, 2.22))):
        added_props.append(_make_box(f"{p}EnlBenchLeg_{li}", (0.045, 0.045, bz - 0.04), (lx, ly, (bz - 0.04) * 0.5), mat=bank["steel_dark"], col=col).name)

    # Hero Optical Enlarger (baseboard, inclined girder column, bellows, condenser lamphead, lens, red filter, easel)
    ex, ey, ez = 2.24, 1.99, bz
    added_props.append(_make_box(f"{p}EnlBaseboard", (0.52, 0.44, 0.032), (ex, ey, ez + 0.016), bevel=0.004, mat=bank["oak"], col=col).name)
    added_props.append(_make_box(f"{p}EnlEasel", (0.34, 0.28, 0.012), (ex, ey - 0.03, ez + 0.038), mat=bank["steel_dark"], col=col).name)
    added_props.append(_make_box(f"{p}EnlPhotoPaper", (0.28, 0.22, 0.004), (ex, ey - 0.03, ez + 0.046), mat=bank["paper"], col=col).name)
    added_props.append(_make_box(f"{p}EnlColumnMount", (0.14, 0.12, 0.05), (ex, ey + 0.15, ez + 0.055), mat=bank["steel_dark"], col=col).name)
    added_props.append(_make_box(f"{p}EnlColumn", (0.055, 0.065, 0.92), (ex, ey + 0.10, ez + 0.50), rot=(0.14, 0.0, 0.0), bevel=0.005, mat=bank["steel"], col=col).name)
    added_props.append(_make_box(f"{p}EnlCarriage", (0.16, 0.22, 0.12), (ex, ey + 0.02, ez + 0.62), bevel=0.006, mat=bank["steel_dark"], col=col).name)
    added_props.append(_make_cyl(f"{p}EnlCrank", 0.048, 0.016, (ex + 0.11, ey + 0.04, ez + 0.62), rot=(0.0, math.pi * 0.5, 0.0), mat=bank["brass"], col=col).name)
    added_props.append(_make_box(f"{p}EnlLampHead", (0.22, 0.22, 0.22), (ex, ey - 0.04, ez + 0.78), bevel=0.012, mat=bank["steel_dark"], col=col).name)
    added_props.append(_make_cyl(f"{p}EnlVentCap", 0.088, 0.06, (ex, ey - 0.04, ez + 0.91), mat=bank["steel_dark"], col=col).name)
    added_props.append(_make_cyl(f"{p}EnlBellows", 0.078, 0.15, (ex, ey - 0.04, ez + 0.57), r2=0.045, segs=8, mat=bank["rubber"], col=col).name)
    added_props.append(_make_cyl(f"{p}EnlLens", 0.030, 0.055, (ex, ey - 0.04, ez + 0.47), mat=bank["steel"], col=col).name)
    # Iconic swinging ruby red safety filter under enlarger lens
    red_filter_mat = _make_glass_material(f"{p}RedFilter", (0.85, 0.05, 0.02, 1.0), roughness=0.05, transmission=0.72)
    added_props.append(_make_cyl(f"{p}EnlRedFilter", 0.036, 0.006, (ex + 0.055, ey - 0.04, ez + 0.42), mat=red_filter_mat, col=col).name)

    # Extra stacked paper boxes & trays on enlarger bench
    added_props.append(_make_box(f"{p}PaperBox1", (0.30, 0.24, 0.035), (2.74, 1.98, bz + 0.018), bevel=0.003, mat=bank["paint"], col=col).name)
    added_props.append(_make_box(f"{p}PaperBox2", (0.28, 0.22, 0.032), (2.75, 1.99, bz + 0.052), bevel=0.003, mat=bank["parcel"], col=col).name)

    # 3. Analog Darkroom Timer Mounted on Back Wall (x=1.52, y=2.27, z=1.52 — clear of technician at x=0.95!)
    dial_mat, dial_img = _make_timer_dial_material(f"{p}TimerDial")
    gen_textures.append(dial_img)
    added_props.append(_make_box(f"{p}TimerBody", (0.24, 0.08, 0.24), (1.52, 2.25, 1.52), bevel=0.008, mat=bank["steel_dark"], col=col).name)
    added_props.append(_make_uv_quad(f"{p}TimerFace", 0.20, 0.20, (1.52, 2.208, 1.52), mat=dial_mat, col=col).name)

    # 4. Print-Drying Wire Line, Metal Clips & Curled Silver-Gelatin B&W Prints (x in [1.74, 3.04], y=2.12, z=1.96)
    added_props.append(_make_cyl(f"{p}DryWire", 0.003, 1.32, (2.39, 2.12, 1.96), rot=(0.0, math.pi * 0.5, 0.0), segs=10, mat=bank["steel"], col=col).name)
    for idx, px in enumerate((1.90, 2.22, 2.54, 2.86)):
        pmat, pimg = _make_bw_print_material(f"{p}BWPrint_{idx}", idx)
        gen_textures.append(pimg)
        added_props.append(_make_box(f"{p}DryClip_{idx}", (0.022, 0.018, 0.048), (px, 2.12, 1.945), mat=bank["steel"], col=col).name)
        added_props.append(
            _make_uv_quad(
                f"{p}DryPhoto_{idx}",
                0.23,
                0.29,
                (px, 2.12, 1.785),
                rot=(0.0, 0.0, 0.04 * (idx - 1.5)),
                mat=pmat,
                col=col,
                curl_x=0.014,
            ).name
        )

    # 5. Right Side Wall Steel Shelving & Safelight Sign (x in [2.72, 3.18], y in [0.15, 1.45])
    if _try_place_asset(wa, "steel_shelves", (2.92, 0.85, 0.0), size=1.75, yaw=-math.pi * 0.5, audit=audit) is None:
        # Clean procedural steel chemical rack along right wall
        for sz in (0.28, 0.82, 1.36, 1.88):
            added_props.append(_make_box(f"{p}RightShelf_{int(sz*100)}", (0.38, 1.18, 0.028), (2.98, 0.85, sz), mat=bank["steel_dark"], col=col).name)
        for pi, (px, py) in enumerate(((2.80, 0.28), (3.15, 0.28), (2.80, 1.42), (3.15, 1.42))):
            added_props.append(_make_box(f"{p}RightPost_{pi}", (0.032, 0.032, 1.92), (px, py, 0.96), mat=bank["steel_dark"], col=col).name)
        for ji, jy in enumerate((0.46, 0.68, 0.90, 1.16)):
            added_props.append(_make_cyl(f"{p}ChemJug_{ji}", 0.068, 0.26, (2.96, jy, 0.965), mat=bank["glass_amber"], col=col).name)
        for ti, ty in enumerate((0.55, 1.05)):
            added_props.append(_make_box(f"{p}SpareTray_{ti}", (0.30, 0.38, 0.045), (2.96, ty, 1.40), bevel=0.005, mat=bank["ceramic"], col=col).name)

    _add_framed_sign(
        f"{p}SafeSignR",
        ["RED SAFELIGHT ONLY", "KEEP DOOR CLOSED"],
        width=0.52,
        height=0.24,
        loc=(3.165, -0.35, 1.65),
        rot=(0.0, 0.0, -math.pi * 0.5),
        frame_mat=bank["steel_dark"],
        bg=(0.12, 0.08, 0.08),
        fg=(0.94, 0.80, 0.68),
        border=(0.78, 0.16, 0.08),
        col=col,
        added_props=added_props,
        gen_textures=gen_textures,
    )

    # 6. Two Mounted Kodak-Style Safelight Filter Boxes on Darkroom Back Wall (z=2.40)
    safe_lens_mat = _make_emissive_material(f"{p}SafelightFilterLens", (1.0, 0.11, 0.02, 1.0), strength=10.0, roughness=0.18)
    for si, sx_pos in enumerate((0.62, 2.18)):
        added_props.append(_make_box(f"{p}SafelightBox_{si}", (0.38, 0.20, 0.24), (sx_pos, 2.20, 2.40), rot=(-0.22, 0.0, 0.0), bevel=0.01, mat=bank["steel_dark"], col=col).name)
        added_props.append(_make_box(f"{p}SafelightLens_{si}", (0.32, 0.02, 0.18), (sx_pos, 2.095, 2.38), rot=(-0.22, 0.0, 0.0), mat=safe_lens_mat, col=col).name)
        added_props.append(_make_box(f"{p}SafelightBracket_{si}", (0.04, 0.10, 0.14), (sx_pos, 2.26, 2.45), mat=bank["steel"], col=col).name)

    return {"safelight_lens_mat": safe_lens_mat}


def _setup_darkroom_lights(
    scene: bpy.types.Scene,
    portal: dict[str, float],
    bank: dict[str, bpy.types.Material],
    col: bpy.types.Collection,
    audit: dict[str, Any],
) -> Callable[[float, float, float], None]:
    """Build vestibule daylight, readable darkroom safelight, and geometric door-spill updater."""
    p = "NL_DR_L_"
    lights: list[bpy.types.Object] = []

    # Very dark world so darkroom relies on real red safelights & authored doorway spill
    world = scene.world or bpy.data.worlds.new("NL_DR_World")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    wout = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (0.016, 0.004, 0.003, 1.0)
    bg.inputs["Strength"].default_value = 0.05
    nt.links.new(bg.outputs["Background"], wout.inputs["Surface"])

    # --- VESTIBULE WARM DAYLIGHT (STRICTLY LEFT OF x=-0.60 PARTITION) ---
    lights.append(
        _create_light(
            f"{p}VestWindow", "AREA", (-1.96, 2.16, 1.84),
            energy=185.0, color=(1.0, 0.93, 0.82), col=col,
            target=(-1.75, 0.15, 0.65), size=1.35, size_y=1.05, spread_deg=82.0,
        )
    )
    lights.append(
        _create_light(
            f"{p}VestCeiling", "AREA", (-1.88, 0.15, 2.82),
            energy=125.0, color=(1.0, 0.89, 0.72), col=col,
            target=(-1.45, -0.15, 0.70), size=0.92, size_y=0.45, spread_deg=76.0,
        )
    )
    lights.append(
        _create_light(
            f"{p}VestFrontFill", "AREA", (-2.25, -1.35, 1.75),
            energy=42.0, color=(0.98, 0.92, 0.84), col=col,
            target=(-1.70, 0.05, 0.82), size=1.20, size_y=1.05, spread_deg=65.0,
        )
    )

    # --- DARKROOM RED/AMBER SAFELIGHTS (READABLE WHEN CLOSED, STRICTLY RIGHT OF PARTITION) ---
    lights.append(
        _create_light(
            f"{p}SafelightBench", "AREA", (0.62, 2.02, 2.34),
            energy=84.0, color=(1.0, 0.13, 0.03), col=col,
            target=(0.82, 1.15, 0.92), size=0.36, size_y=0.22, spread_deg=105.0,
        )
    )
    lights.append(
        _create_light(
            f"{p}SafelightEnlarger", "AREA", (2.18, 2.02, 2.34),
            energy=62.0, color=(1.0, 0.14, 0.03), col=col,
            target=(1.45, 0.82, 0.85), size=0.36, size_y=0.22, spread_deg=105.0,
        )
    )
    lights.append(
        _create_light(
            f"{p}SafelightGuidedBounce", "AREA", (1.02, 0.10, 2.58),
            energy=36.0, color=(0.96, 0.17, 0.06), col=col,
            target=(0.88, 1.15, 0.95), size=1.75, size_y=1.35, spread_deg=98.0,
        )
    )

    # --- TRACE-DRIVEN DYNAMIC DOOR SPILL LIGHTS (START AT 0 W WHEN CLOSED) ---
    px = portal["portal_x"]
    y_min = portal["y_min"]
    y_max = portal["y_max"]
    p_width = max(0.30, y_max - y_min)
    z_mid = 0.5 * (portal["z_min"] + portal["z_max"])
    p_height = max(1.40, portal["z_max"] - portal["z_min"])

    spill_main = _create_light(
        f"{p}DoorSpill_Main", "AREA", (px - 0.04, y_min + 0.25 * p_width, z_mid),
        energy=0.0, color=(1.0, 0.91, 0.76), col=col,
        target=(0.95, 0.65, 0.75), size=0.05, size_y=p_height * 0.86, spread_deg=78.0,
    )
    spill_wedge = _create_light(
        f"{p}DoorSpill_FloorWedge", "SPOT", (px - 0.30, y_min + 0.35 * p_width, min(2.08, portal["z_max"] - 0.06)),
        energy=0.0, color=(1.0, 0.90, 0.74), col=col,
        target=(0.82, 0.42, 0.12), spot_deg=56.0, spot_blend=0.24, soft_size=0.07,
    )
    spill_bounce = _create_light(
        f"{p}DoorSpill_RoomBounce", "AREA", (px + 0.32, y_min + 0.35 * p_width, 0.70),
        energy=0.0, color=(1.0, 0.88, 0.70), col=col,
        target=(0.95, 1.15, 0.98), size=0.20, size_y=0.90, spread_deg=112.0,
    )
    lights.extend([spill_main, spill_wedge, spill_bounce])

    audit["lights"] = [_light_record(lo) for lo in lights]
    audit["world"] = {"name": world.name, "strength": 0.05, "color": [0.016, 0.004, 0.003]}
    audit["darkroom_portal"] = {k: round(v, 4) for k, v in portal.items()}

    liquid_bsdf = _get_bsdf(bank["liquid"]) if "liquid" in bank else None

    def update_function(
        door_open_fraction: float = 0.0,
        cover_closed_fraction: float = 1.0,
        time_s: float = 0.0,
    ) -> dict[str, Any]:
        """Drive warm corridor light spill strictly from actual geometric door & tray-cover trace."""
        f_door = float(max(0.0, min(1.0, door_open_fraction)))
        f_cover = float(max(0.0, min(1.0, cover_closed_fraction)))
        f_exposed = f_door * (1.0 - f_cover)

        # Sliding pocket door clears passage starting from -Y edge toward +Y
        open_w = max(0.03, p_width * f_door)
        y_open = y_min + 0.5 * p_width * f_door

        if f_door <= 1e-4:
            spill_main.data.energy = 0.0
            spill_wedge.data.energy = 0.0
            spill_bounce.data.energy = 0.0
            spill_main.hide_render = True
            spill_wedge.hide_render = True
            spill_bounce.hide_render = True
        else:
            spill_main.hide_render = False
            spill_wedge.hide_render = False
            spill_bounce.hide_render = False

            # Primary doorway aperture area light tracks exact open gap width & center
            spill_main.location = (px - 0.04, y_open, z_mid)
            spill_main.data.size = open_w
            spill_main.data.size_y = p_height * 0.86
            _look_at(spill_main, (0.95, 0.55 + 0.25 * f_door, 0.72))
            spill_main.data.energy = 420.0 * (f_door ** 1.12)

            # Geometric spotlight from vestibule side physically masked by actual door & partition
            spill_wedge.location = (px - 0.30, y_open, min(2.08, portal["z_max"] - 0.06))
            _look_at(spill_wedge, (0.85, 0.38 + 0.30 * f_door, 0.14))
            spill_wedge.data.energy = 540.0 * (f_door ** 1.05)

            # Guided interior warm bounce (ensures Cycles & Eevee parity without auto-GI)
            spill_bounce.location = (px + 0.32, y_open, 0.68)
            spill_bounce.data.size = max(0.14, 0.85 * open_w)
            _look_at(spill_bounce, (0.95, 1.15, 0.98))
            spill_bounce.data.energy = 96.0 * (f_door ** 1.25)

        # Subtle physical wet-surface specular reflection boost on uncovered tray liquid under spill
        if liquid_bsdf is not None:
            _set_bsdf(liquid_bsdf, "Coat Weight", 0.55 + 0.40 * f_exposed)
            _set_bsdf(liquid_bsdf, "Specular IOR Level", 0.62 + 0.25 * f_exposed)

        return {
            "case": "darkroom",
            "door_open_fraction": round(f_door, 4),
            "cover_closed_fraction": round(f_cover, 4),
            "exposed_overlap": round(f_exposed, 4),
            "time_s": round(float(time_s), 4),
            "door_spill_main_w": round(float(spill_main.data.energy), 2),
            "door_spill_wedge_w": round(float(spill_wedge.data.energy), 2),
            "door_spill_bounce_w": round(float(spill_bounce.data.energy), 2),
            "aperture_y_center": round(y_open, 4),
            "aperture_width_m": round(open_w, 4),
        }

    # Initialize cleanly to closed state
    update_function(0.0, 1.0, 0.0)
    return update_function


# ---------------------------------------------------------------------------
# Color Management, Host Light Hygiene & JSON Audit Serialization
# ---------------------------------------------------------------------------

def _configure_color_management(scene: bpy.types.Scene, case: str, audit: dict[str, Any]) -> None:
    vs = scene.view_settings
    vt_items = [item.identifier for item in vs.bl_rna.properties["view_transform"].enum_items]
    chosen_vt = "AgX" if "AgX" in vt_items else ("Filmic" if "Filmic" in vt_items else vt_items[0])
    vs.view_transform = chosen_vt

    look_items = [item.identifier for item in vs.bl_rna.properties["look"].enum_items]
    preferred_looks = (
        "AgX - Medium High Contrast",
        "AgX - Base Contrast",
        "AgX - None",
        "None",
    )
    chosen_look = next((lk for lk in preferred_looks if lk in look_items), look_items[0])
    vs.look = chosen_look
    vs.exposure = 0.0 if case == "cafe" else 0.12
    vs.gamma = 1.0

    audit["color_management"] = {
        "view_transform": vs.view_transform,
        "look": vs.look,
        "exposure": float(vs.exposure),
        "gamma": float(vs.gamma),
        "render_engine": scene.render.engine,
    }


def _dim_existing_host_lights(scene: bpy.types.Scene, our_col: bpy.types.Collection, audit: dict[str, Any]) -> None:
    """Non-destructively zero out flat default host lights so art-directed lighting controls mood."""
    dimmed: list[dict[str, Any]] = []
    our_names = {o.name for o in our_col.objects}
    for obj in scene.objects:
        if obj.type == "LIGHT" and obj.name not in our_names and obj.data is not None:
            prev_e = float(obj.data.energy)
            if prev_e > 0.0:
                obj.data.energy = 0.0
                dimmed.append({"name": obj.name, "previous_energy": round(prev_e, 3)})
    audit["dimmed_host_lights"] = dimmed


def _light_record(obj: bpy.types.Object) -> dict[str, Any]:
    ld = obj.data
    rec: dict[str, Any] = {
        "name": obj.name,
        "type": ld.type,
        "energy": round(float(ld.energy), 2),
        "color": [round(float(c), 3) for c in ld.color],
        "location": [round(float(v), 3) for v in obj.location],
        "use_shadow": bool(getattr(ld, "use_shadow", True)),
    }
    if ld.type == "AREA":
        rec["shape"] = ld.shape
        rec["size"] = round(float(ld.size), 3)
        if ld.shape == "RECTANGLE":
            rec["size_y"] = round(float(ld.size_y), 3)
        if hasattr(ld, "spread"):
            rec["spread_deg"] = round(math.degrees(float(ld.spread)), 1)
    elif ld.type == "SPOT":
        rec["spot_deg"] = round(math.degrees(float(ld.spot_size)), 1)
        rec["spot_blend"] = round(float(ld.spot_blend), 2)
    return rec


def _ensure_json_safe(data: Any) -> Any:
    if data is None or isinstance(data, (bool, int, float, str)):
        return data
    if isinstance(data, Path):
        return str(data)
    if isinstance(data, dict):
        return {str(k): _ensure_json_safe(v) for k, v in data.items()}
    if isinstance(data, (list, tuple, set)):
        return [_ensure_json_safe(v) for v in data]
    if isinstance(data, (Vector, Euler)):
        return [round(float(v), 4) for v in data]
    return str(data)


# ---------------------------------------------------------------------------
# Public Entrypoint: dress(scene, view, case, library)
# ---------------------------------------------------------------------------

def dress(
    scene: bpy.types.Scene,
    view: Any,
    case: str,
    library: Any = None,
) -> tuple[dict[str, Any], Callable[[float, float, float], Any]]:
    """Dress and light a DESPITE people study scene ('cafe' or 'darkroom').

    Returns:
      (audit, update_function)
        - audit: JSON-serializable dict with verified Genie texture paths/hashes/colorspaces,
          human skin preservation records, added prop names, and light setup.
        - update_function(door_open_fraction, cover_closed_fraction, time_s):
          Trace-driven dynamic lighting/reflection update (no branch dependence).
    """
    case_key = str(case).strip().lower()
    if case_key not in ("cafe", "darkroom"):
        raise ValueError(f"Unsupported case {case!r}; expected 'cafe' or 'darkroom'.")

    tex_dir = _resolve_genie_texture_dir(library)
    wa = _load_world_assets(library)
    col = _ensure_collection(scene, f"NeonLook_{case_key}")

    audit: dict[str, Any] = {
        "case": case_key,
        "output_dir": str(CASE_OUTPUT_DIRS[case_key]),
        "blender_version": ".".join(str(x) for x in bpy.app.version),
        "genie_texture_dir": str(tex_dir),
        "world_assets_loaded": wa is not None,
        "placed_library_assets": [],
        "asset_fallbacks": [],
    }
    added_props: list[str] = []
    gen_textures: list[str] = []

    # 1. Color management (AgX, non-bleaching)
    _configure_color_management(scene, case_key, audit)

    # 2. Build genuine Genie Sim PBR & MJCF role shaders (fails if Genie textures missing)
    bank = _build_role_bank(case_key, tex_dir, audit)

    # 3. Shade all physics geoms from view.obs/view.spec/view.meta & preserve human UV skins
    view_info = _dress_view_geoms(view, case_key, bank, audit)
    _dress_human_skins(scene, view, case_key, audit)

    # 4. Ensure room shell (if host omitted outer walls/ceiling) without touching darkroom portal
    _ensure_room_shell(case_key, view_info, bank, col, added_props)

    # 5. Case-specific set dressing & lighting
    if case_key == "cafe":
        _dress_cafe_set(bank, wa, col, audit, added_props, gen_textures)
        _dim_existing_host_lights(scene, col, audit)
        update_fn = _setup_cafe_lights(scene, col, audit)
    else:
        portal = _detect_darkroom_portal(view_info["door_objs"])
        _dress_darkroom_set(bank, wa, col, audit, added_props, gen_textures)
        _dim_existing_host_lights(scene, col, audit)
        update_fn = _setup_darkroom_lights(scene, portal, bank, col, audit)

    # 6. Apply world-space metric planar UVs to every static wall/floor mesh using Genie textures
    uv_targets = list(view_info["wall_objs"]) + list(view_info["floor_objs"]) + list(col.objects)
    uv_mapped = _apply_metric_planar_uvs(uv_targets)

    audit["metric_uv_mapped_objects"] = uv_mapped
    audit["added_props"] = added_props
    audit["added_prop_count"] = len(added_props)
    audit["generated_textures"] = gen_textures

    # Guarantee pure JSON-serializable audit dictionary (zero Blender object references)
    clean_audit = _ensure_json_safe(audit)
    json.dumps(clean_audit)
    return clean_audit, update_fn
