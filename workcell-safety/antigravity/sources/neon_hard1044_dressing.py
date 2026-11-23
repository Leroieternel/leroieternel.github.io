"""Art-directed Blender 4.5 environment dressing for 30 MuJoCo visual studies."""

from __future__ import annotations

import hashlib
import math
import random
from typing import Any

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

GENIE_KEYS: tuple[str, ...] = (
    "carton",
    "bin",
    "medicine",
    "soap",
    "cup",
    "mug",
    "water",
    "book",
    "folder",
    "pen",
    "mouse",
    "chair",
    "desk_chair",
    "cabinet",
    "table",
    "sideboard",
    "refrigerator",
    "picture_frame",
    "laptop",
    "photo_books",
    "coffee_service",
    "nightstand",
    "sofa",
    "book2",
    "pen_cup",
    "stapler",
)
GENIE_KEYS_SET: frozenset[str] = frozenset(GENIE_KEYS)

EXTRA_KEYS: tuple[str, ...] = (
    "potted_plant",
    "potted_fern",
    "shipping_crate",
    "tool_cart",
    "steel_shelves",
)
EXTRA_KEYS_SET: frozenset[str] = frozenset(EXTRA_KEYS)

OUTDOOR_SAFE_GENIE: frozenset[str] = frozenset(
    {"carton", "bin", "cup", "mug", "water", "book", "book2", "chair", "table", "coffee_service"}
)

TABLETOP_GENIE: frozenset[str] = frozenset(
    {
        "medicine",
        "soap",
        "cup",
        "mug",
        "water",
        "book",
        "book2",
        "folder",
        "pen",
        "pen_cup",
        "mouse",
        "laptop",
        "photo_books",
        "coffee_service",
        "stapler",
        "picture_frame",
    }
)

FLOOR_GENIE: frozenset[str] = frozenset(
    {
        "carton",
        "bin",
        "chair",
        "desk_chair",
        "cabinet",
        "table",
        "sideboard",
        "refrigerator",
        "nightstand",
        "sofa",
    }
)

GROUND_Z: float = -0.004
PROTECT_X: float = 3.30
PROTECT_Y_MIN: float = -1.70
PROTECT_Y_MAX: float = 1.20
SAFE_X: float = 3.44
SAFE_Y_MIN: float = -1.82
SAFE_Y_MAX: float = 1.94
COLLECTION_NAME: str = "EnvDress"


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def _safe_float(val: Any, default: float) -> float:
    try:
        if val is None:
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _srgb_to_linear_channel(c: float) -> float:
    c = _clamp(c, 0.0, 1.0)
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _rgba(r: float, g: float, b: float, a: float = 1.0) -> tuple[float, float, float, float]:
    return (
        _srgb_to_linear_channel(r),
        _srgb_to_linear_channel(g),
        _srgb_to_linear_channel(b),
        _clamp(a, 0.0, 1.0),
    )


def _kelvin_to_linear_rgb(kelvin: float) -> tuple[float, float, float]:
    temp = _clamp(kelvin, 1800.0, 12000.0) / 100.0
    if temp <= 66.0:
        r = 1.0
        g = _clamp((99.4708025861 * math.log(max(temp, 1.0)) - 161.1195681661) / 255.0, 0.0, 1.0)
        if temp <= 19.0:
            b = 0.0
        else:
            b = _clamp((138.5177312231 * math.log(temp - 10.0) - 305.0447927307) / 255.0, 0.0, 1.0)
    else:
        r = _clamp((329.698727446 * ((temp - 60.0) ** -0.1332047592)) / 255.0, 0.0, 1.0)
        g = _clamp((288.1221695283 * ((temp - 60.0) ** -0.0755148492)) / 255.0, 0.0, 1.0)
        b = 1.0
    lin = (_srgb_to_linear_channel(r), _srgb_to_linear_channel(g), _srgb_to_linear_channel(b))
    peak = max(lin[0], lin[1], lin[2], 1e-4)
    return (lin[0] / peak, lin[1] / peak, lin[2] / peak)


def _stable_seed(c: dict[str, Any]) -> int:
    key = "|".join(
        str(c.get(k, "") or "") for k in ("id", "title", "setting", "scene_group", "room_note")
    )
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _classify_scene(c: dict[str, Any]) -> tuple[str, str, bool]:
    # The source setting resolves ambiguous names such as office and ice.
    exact = {
        "bddl_764": ("office", "indoor_office", False),
        "virtualhome_363": ("office", "indoor_office", False),
        "normbank_18350": ("office", "workshop", False),
        "normbank_53370": ("museum", "indoor_museum", False),
        "normbank_2622": ("mountains", "outdoor_mountains", True),
        "neiss_24223": ("sidewalk", "outdoor_sidewalk", True),
    }
    if c["id"] in exact:
        return exact[c["id"]]
    primary = " ".join(
        str(c.get(k, "") or "") for k in ("setting", "scene_group", "id", "title")
    ).lower()
    full = (primary + " " + str(c.get("room_note", "") or "") + " " + str(c.get("light", "") or "")).lower()

    def _has(text: str, words: tuple[str, ...]) -> bool:
        return any(w in text for w in words)

    # Specific indoor/outdoor categories checked on primary identifiers first, then full metadata
    for src in (primary, full):
        if _has(src, ("hospital", "clinic", "medical", "ward", "exam_room", "nurse", "patient", "icu", "pharmacy")):
            return ("hospital", "clinical", False)
        if _has(src, ("newsroom", "broadcast", "anchor", "press_room", "editorial", "control_room", "tv_studio")):
            return ("newsroom", "broadcast", False)
        if _has(src, ("cemetery", "graveyard", "memorial_park", "churchyard", "gravestone", "mausoleum", "tomb")):
            return ("cemetery", "outdoor_cemetery", True)
        if _has(src, ("golf", "fairway", "putting", "driving_range", "clubhouse", "tee_box")):
            return ("golf", "outdoor_golf", True)
        if _has(src, ("ski", "piste", "alpine", "chalet", "snow_slope", "sled", "snowfield")):
            return ("ski", "outdoor_ski", True)
        if _has(src, ("ice_rink", "frozen_pond", "skating", "arctic", "glacier", "ice", "frost")):
            return ("ice", "outdoor_ice", True)
        if _has(src, ("sidewalk", "street", "crosswalk", "plaza", "urban", "storefront", "alley", "pavement", "curb", "cafe_patio")):
            return ("sidewalk", "outdoor_sidewalk", True)
        if _has(src, ("forest", "woods", "trailhead", "woodland", "trail", "campsite", "camp", "hiking", "redwood", "pine_woods")):
            return ("forest", "outdoor_forest", True)
        if _has(src, ("garden", "backyard", "botanical", "orchard", "courtyard", "terrace", "lawn", "flower", "patio", "meadow")):
            return ("garden", "outdoor_garden", True)
        if _has(src, ("mountain", "summit", "ridge", "canyon", "cliff", "overlook", "highland", "valley", "desert", "mesa")):
            return ("mountains", "outdoor_mountains", True)
        if _has(src, ("kitchen", "galley", "pantry", "culinary", "bakery", "cooking", "cooktop")):
            return ("kitchen", "indoor_kitchen", False)
        if _has(src, ("bathroom", "washroom", "restroom", "shower", "vanity", "bath", "spa", "laundry")):
            return ("bathroom", "indoor_bathroom", False)
        if _has(src, ("bedroom", "dorm", "master_bed", "guest_room", "hotel_room", "nursery", "sleep")):
            return ("bedroom", "indoor_bedroom", False)
        if _has(src, ("museum", "gallery", "exhibit", "exhibition", "sculpture", "atrium", "curator")):
            return ("museum", "indoor_museum", False)
        if _has(src, ("workshop", "garage", "warehouse", "maker", "machine_shop", "storage_bay")):
            return ("office", "workshop", False)
        if _has(src, ("office", "study", "library", "desk", "conference", "workspace", "classroom", "meeting", "cubicle")):
            return ("office", "indoor_office", False)
        if _has(src, ("living", "lounge", "salon", "parlor", "family_room", "den", "apartment", "lobby", "reception", "dining", "foyer", "hallway")):
            return ("living", "indoor_living", False)

    if _has(full, ("outdoor", "outside", "park", "exterior", "open_air", "sky", "field")):
        return ("garden", "outdoor_park", True)
    return ("living", "indoor_living", False)


def _sun_direction(azimuth_deg: float, elevation_deg: float) -> Vector:
    az = math.radians(azimuth_deg)
    el = math.radians(_clamp(elevation_deg, 6.0, 82.0))
    return Vector((math.cos(el) * math.sin(az), math.cos(el) * math.cos(az), math.sin(el))).normalized()


def _aim_euler(origin: Vector, target: Vector) -> Euler:
    direction = (target - origin)
    if direction.length < 1e-5:
        direction = Vector((0.0, 0.0, -1.0))
    return direction.normalized().to_track_quat("-Z", "Y").to_euler()


def _set_bsdf(bsdf: bpy.types.Node, name: str, value: Any) -> None:
    if name in bsdf.inputs:
        bsdf.inputs[name].default_value = value


class MatLib:
    """Stateless-per-call Blender 4.5 Principled BSDF & Genie PBR material library."""

    def __init__(self, assets: Any, prefix: str) -> None:
        self.assets = assets
        self.prefix = prefix
        self._cache: dict[str, bpy.types.Material] = {}
        self.applied_genie_surfaces: list[dict[str, Any]] = []
        self._applied_seen: set[tuple[str, str, str]] = set()

    def _new_mat(self, name: str) -> tuple[bpy.types.Material, bpy.types.NodeTree, bpy.types.Node]:
        mat = bpy.data.materials.new(name=f"{self.prefix}_{name}")
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        out.location = (520, 0)
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (200, 0)
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        return mat, nt, bsdf

    def pbr_surface(
        self,
        role: str,
        key: str,
        tile_m: float,
        projection: str,
        fallback_rgb: tuple[float, float, float] = (0.55, 0.52, 0.48),
    ) -> bpy.types.Material:
        proj = projection.upper()
        if proj not in ("XY", "XZ", "YZ"):
            proj = "XY"
        clean_key = str(key or "").strip()
        cache_id = f"pbr|{clean_key}|{tile_m:.3f}|{proj}"
        if cache_id in self._cache:
            sig = (role, clean_key, proj)
            if clean_key and sig not in self._applied_seen:
                self._applied_seen.add(sig)
                self.applied_genie_surfaces.append(
                    {"role": role, "key": clean_key, "projection": proj, "tile_m": round(float(tile_m), 3)}
                )
            return self._cache[cache_id]

        mat = None
        if clean_key and self.assets is not None and hasattr(self.assets, "pbr"):
            try:
                res = self.assets.pbr(clean_key, float(tile_m), proj)
                if isinstance(res, bpy.types.Material):
                    mat = res
            except Exception:
                mat = None

        if mat is not None:
            self._cache[cache_id] = mat
            sig = (role, clean_key, proj)
            if sig not in self._applied_seen:
                self._applied_seen.add(sig)
                self.applied_genie_surfaces.append(
                    {"role": role, "key": clean_key, "projection": proj, "tile_m": round(float(tile_m), 3)}
                )
            return mat

        fallback = self.stone(f"fb_{role}_{proj}", fallback_rgb, (fallback_rgb[0] * 0.88, fallback_rgb[1] * 0.88, fallback_rgb[2] * 0.88), 0.72)
        self._cache[cache_id] = fallback
        return fallback

    def paint(
        self,
        name: str,
        rgb: tuple[float, float, float],
        roughness: float = 0.48,
        bump_strength: float = 0.025,
        coat: float = 0.0,
    ) -> bpy.types.Material:
        if name in self._cache:
            return self._cache[name]
        mat, nt, bsdf = self._new_mat(name)
        _set_bsdf(bsdf, "Base Color", _rgba(*rgb))
        _set_bsdf(bsdf, "Roughness", roughness)
        _set_bsdf(bsdf, "Coat Weight", coat)
        _set_bsdf(bsdf, "Coat Roughness", 0.14)

        tc = nt.nodes.new("ShaderNodeTexCoord")
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 26.0
        noise.inputs["Detail"].default_value = 4.0
        nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])

        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.clamp = True
        mr.inputs["From Min"].default_value = 0.25
        mr.inputs["From Max"].default_value = 0.75
        mr.inputs["To Min"].default_value = _clamp(roughness - 0.08, 0.05, 0.96)
        mr.inputs["To Max"].default_value = _clamp(roughness + 0.08, 0.05, 0.98)
        nt.links.new(noise.outputs["Fac"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])

        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = bump_strength
        bump.inputs["Distance"].default_value = 0.004
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

        self._cache[name] = mat
        return mat

    def wood(
        self,
        name: str,
        dark_rgb: tuple[float, float, float],
        light_rgb: tuple[float, float, float],
        roughness: float = 0.38,
        grain_axis: str = "X",
        coat: float = 0.18,
        wear: float = 0.12,
    ) -> bpy.types.Material:
        if name in self._cache:
            return self._cache[name]
        mat, nt, bsdf = self._new_mat(name)
        _set_bsdf(bsdf, "Coat Weight", coat)
        _set_bsdf(bsdf, "Coat Roughness", 0.20)

        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        if grain_axis == "X":
            mp.inputs["Scale"].default_value = (1.4, 9.5, 9.5)
        elif grain_axis == "Y":
            mp.inputs["Scale"].default_value = (9.5, 1.4, 9.5)
        else:
            mp.inputs["Scale"].default_value = (9.5, 9.5, 1.4)
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])

        wave = nt.nodes.new("ShaderNodeTexWave")
        wave.wave_type = "BANDS"
        wave.inputs["Scale"].default_value = 3.2
        wave.inputs["Distortion"].default_value = 5.5
        wave.inputs["Detail"].default_value = 4.5
        nt.links.new(mp.outputs["Vector"], wave.inputs["Vector"])

        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.20
        ramp.color_ramp.elements[0].color = _rgba(*dark_rgb)
        ramp.color_ramp.elements[1].position = 0.82
        ramp.color_ramp.elements[1].color = _rgba(*light_rgb)
        nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.clamp = True
        mr.inputs["From Min"].default_value = 0.15
        mr.inputs["From Max"].default_value = 0.85
        mr.inputs["To Min"].default_value = _clamp(roughness - wear, 0.12, 0.92)
        mr.inputs["To Max"].default_value = _clamp(roughness + wear, 0.16, 0.96)
        nt.links.new(wave.outputs["Fac"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])

        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.065
        bump.inputs["Distance"].default_value = 0.004
        nt.links.new(wave.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

        self._cache[name] = mat
        return mat

    def metal(
        self,
        name: str,
        rgb: tuple[float, float, float],
        roughness: float = 0.24,
        metallic: float = 0.96,
    ) -> bpy.types.Material:
        if name in self._cache:
            return self._cache[name]
        mat, nt, bsdf = self._new_mat(name)
        _set_bsdf(bsdf, "Base Color", _rgba(*rgb))
        _set_bsdf(bsdf, "Metallic", metallic)

        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (18.0, 2.5, 18.0)
        nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])

        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 10.0
        noise.inputs["Detail"].default_value = 5.0
        nt.links.new(mp.outputs["Vector"], noise.inputs["Vector"])

        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.clamp = True
        mr.inputs["From Min"].default_value = 0.25
        mr.inputs["From Max"].default_value = 0.75
        mr.inputs["To Min"].default_value = _clamp(roughness - 0.07, 0.04, 0.85)
        mr.inputs["To Max"].default_value = _clamp(roughness + 0.09, 0.08, 0.90)
        nt.links.new(noise.outputs["Fac"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])

        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.025
        bump.inputs["Distance"].default_value = 0.002
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

        self._cache[name] = mat
        return mat

    def tile(
        self,
        name: str,
        c1: tuple[float, float, float],
        c2: tuple[float, float, float],
        mortar: tuple[float, float, float] = (0.72, 0.70, 0.67),
        scale: float = 5.5,
        brick_w: float = 0.45,
        row_h: float = 0.20,
        roughness: float = 0.16,
    ) -> bpy.types.Material:
        if name in self._cache:
            return self._cache[name]
        mat, nt, bsdf = self._new_mat(name)
        _set_bsdf(bsdf, "Coat Weight", 0.55)
        _set_bsdf(bsdf, "Coat Roughness", 0.07)

        tc = nt.nodes.new("ShaderNodeTexCoord")
        brick = nt.nodes.new("ShaderNodeTexBrick")
        brick.offset = 0.5
        brick.inputs["Color1"].default_value = _rgba(*c1)
        brick.inputs["Color2"].default_value = _rgba(*c2)
        brick.inputs["Mortar"].default_value = _rgba(*mortar)
        brick.inputs["Scale"].default_value = scale
        brick.inputs["Mortar Size"].default_value = 0.016
        brick.inputs["Mortar Smooth"].default_value = 0.15
        brick.inputs["Brick Width"].default_value = brick_w
        brick.inputs["Row Height"].default_value = row_h
        nt.links.new(tc.outputs["UV"], brick.inputs["Vector"])
        nt.links.new(brick.outputs["Color"], bsdf.inputs["Base Color"])

        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.clamp = True
        mr.inputs["From Min"].default_value = 0.0
        mr.inputs["From Max"].default_value = 1.0
        mr.inputs["To Min"].default_value = roughness
        mr.inputs["To Max"].default_value = 0.80
        nt.links.new(brick.outputs["Fac"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])

        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.14
        bump.inputs["Distance"].default_value = 0.005
        bump.invert = True
        nt.links.new(brick.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

        self._cache[name] = mat
        return mat

    def stone(
        self,
        name: str,
        c1: tuple[float, float, float],
        c2: tuple[float, float, float],
        roughness: float = 0.55,
        scale: float = 4.5,
        bump_strength: float = 0.12,
        coat: float = 0.0,
    ) -> bpy.types.Material:
        if name in self._cache:
            return self._cache[name]
        mat, nt, bsdf = self._new_mat(name)
        _set_bsdf(bsdf, "Coat Weight", coat)
        _set_bsdf(bsdf, "Coat Roughness", 0.10)

        tc = nt.nodes.new("ShaderNodeTexCoord")
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = scale
        noise.inputs["Detail"].default_value = 6.0
        noise.inputs["Distortion"].default_value = 0.9
        nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])

        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.25
        ramp.color_ramp.elements[0].color = _rgba(*c1)
        ramp.color_ramp.elements[1].position = 0.78
        ramp.color_ramp.elements[1].color = _rgba(*c2)
        nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.clamp = True
        mr.inputs["From Min"].default_value = 0.2
        mr.inputs["From Max"].default_value = 0.8
        mr.inputs["To Min"].default_value = _clamp(roughness - 0.10, 0.08, 0.95)
        mr.inputs["To Max"].default_value = _clamp(roughness + 0.10, 0.12, 0.98)
        nt.links.new(noise.outputs["Fac"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])

        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = bump_strength
        bump.inputs["Distance"].default_value = 0.012
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

        self._cache[name] = mat
        return mat

    def fabric(
        self,
        name: str,
        rgb: tuple[float, float, float],
        roughness: float = 0.88,
        sheen: float = 0.45,
    ) -> bpy.types.Material:
        if name in self._cache:
            return self._cache[name]
        mat, nt, bsdf = self._new_mat(name)
        _set_bsdf(bsdf, "Roughness", roughness)
        _set_bsdf(bsdf, "Sheen Weight", sheen)
        _set_bsdf(bsdf, "Sheen Roughness", 0.55)

        tc = nt.nodes.new("ShaderNodeTexCoord")
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 65.0
        noise.inputs["Detail"].default_value = 4.0
        nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])

        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.25
        ramp.color_ramp.elements[0].color = _rgba(rgb[0] * 0.84, rgb[1] * 0.84, rgb[2] * 0.84)
        ramp.color_ramp.elements[1].position = 0.78
        ramp.color_ramp.elements[1].color = _rgba(min(1.0, rgb[0] * 1.08), min(1.0, rgb[1] * 1.08), min(1.0, rgb[2] * 1.08))
        nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.07
        bump.inputs["Distance"].default_value = 0.003
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

        self._cache[name] = mat
        return mat

    def glass(
        self,
        name: str,
        tint: tuple[float, float, float] = (0.86, 0.94, 0.97),
        alpha: float = 0.16,
        roughness: float = 0.03,
    ) -> bpy.types.Material:
        if name in self._cache:
            return self._cache[name]
        mat, nt, bsdf = self._new_mat(name)
        _set_bsdf(bsdf, "Base Color", _rgba(*tint))
        _set_bsdf(bsdf, "Roughness", roughness)
        _set_bsdf(bsdf, "IOR", 1.50)
        _set_bsdf(bsdf, "Specular IOR Level", 0.80)
        _set_bsdf(bsdf, "Coat Weight", 0.75)
        _set_bsdf(bsdf, "Coat Roughness", roughness)
        _set_bsdf(bsdf, "Alpha", alpha)
        self._cache[name] = mat
        return mat

    def mirror(self, name: str = "mirror_glass") -> bpy.types.Material:
        return self.metal(name, (0.88, 0.91, 0.92), roughness=0.02, metallic=1.0)

    def emissive(
        self,
        name: str,
        rgb: tuple[float, float, float],
        strength: float = 4.0,
    ) -> bpy.types.Material:
        if name in self._cache:
            return self._cache[name]
        mat, nt, bsdf = self._new_mat(name)
        col = _rgba(*rgb)
        _set_bsdf(bsdf, "Base Color", col)
        _set_bsdf(bsdf, "Roughness", 0.25)
        _set_bsdf(bsdf, "Emission Color", col)
        _set_bsdf(bsdf, "Emission Strength", strength)
        self._cache[name] = mat
        return mat

    def screen_dark(
        self,
        name: str,
        accent_rgb: tuple[float, float, float] = (0.14, 0.26, 0.38),
        strength: float = 0.55,
    ) -> bpy.types.Material:
        if name in self._cache:
            return self._cache[name]
        mat, nt, bsdf = self._new_mat(name)
        _set_bsdf(bsdf, "Roughness", 0.08)
        _set_bsdf(bsdf, "Coat Weight", 0.60)
        _set_bsdf(bsdf, "Coat Roughness", 0.04)
        _set_bsdf(bsdf, "Emission Strength", strength)

        tc = nt.nodes.new("ShaderNodeTexCoord")
        grad = nt.nodes.new("ShaderNodeTexGradient")
        grad.gradient_type = "DIAGONAL"
        nt.links.new(tc.outputs["UV"], grad.inputs["Vector"])

        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.1
        ramp.color_ramp.elements[0].color = _rgba(accent_rgb[0] * 0.28, accent_rgb[1] * 0.28, accent_rgb[2] * 0.34)
        ramp.color_ramp.elements[1].position = 0.9
        ramp.color_ramp.elements[1].color = _rgba(*accent_rgb)
        nt.links.new(grad.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Emission Color"])

        self._cache[name] = mat
        return mat

    def foliage(
        self,
        name: str,
        c1: tuple[float, float, float],
        c2: tuple[float, float, float],
        roughness: float = 0.54,
        subsurf: float = 0.18,
    ) -> bpy.types.Material:
        if name in self._cache:
            return self._cache[name]
        mat, nt, bsdf = self._new_mat(name)
        _set_bsdf(bsdf, "Roughness", roughness)
        _set_bsdf(bsdf, "Subsurface Weight", subsurf)

        tc = nt.nodes.new("ShaderNodeTexCoord")
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 6.0
        noise.inputs["Detail"].default_value = 5.0
        nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])

        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.25
        ramp.color_ramp.elements[0].color = _rgba(*c1)
        ramp.color_ramp.elements[1].position = 0.78
        ramp.color_ramp.elements[1].color = _rgba(*c2)
        nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.16
        bump.inputs["Distance"].default_value = 0.02
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

        self._cache[name] = mat
        return mat

    def snow(self, name: str = "snow") -> bpy.types.Material:
        if name in self._cache:
            return self._cache[name]
        mat, nt, bsdf = self._new_mat(name)
        _set_bsdf(bsdf, "Base Color", _rgba(0.89, 0.92, 0.96))
        _set_bsdf(bsdf, "Roughness", 0.42)
        _set_bsdf(bsdf, "Subsurface Weight", 0.28)
        _set_bsdf(bsdf, "Coat Weight", 0.14)
        _set_bsdf(bsdf, "Coat Roughness", 0.22)

        tc = nt.nodes.new("ShaderNodeTexCoord")
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 12.0
        noise.inputs["Detail"].default_value = 5.0
        nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])

        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.09
        bump.inputs["Distance"].default_value = 0.02
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

        self._cache[name] = mat
        return mat

    def ice_surface(self, name: str = "ice_surf") -> bpy.types.Material:
        if name in self._cache:
            return self._cache[name]
        mat, nt, bsdf = self._new_mat(name)
        _set_bsdf(bsdf, "Base Color", _rgba(0.75, 0.85, 0.91))
        _set_bsdf(bsdf, "Coat Weight", 0.75)
        _set_bsdf(bsdf, "Coat Roughness", 0.06)
        _set_bsdf(bsdf, "Subsurface Weight", 0.18)

        tc = nt.nodes.new("ShaderNodeTexCoord")
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 8.0
        noise.inputs["Detail"].default_value = 6.0
        noise.inputs["Distortion"].default_value = 1.4
        nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])

        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.clamp = True
        mr.inputs["From Min"].default_value = 0.22
        mr.inputs["From Max"].default_value = 0.78
        mr.inputs["To Min"].default_value = 0.06
        mr.inputs["To Max"].default_value = 0.24
        nt.links.new(noise.outputs["Fac"], mr.inputs["Value"])
        nt.links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])

        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.04
        bump.inputs["Distance"].default_value = 0.004
        nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

        self._cache[name] = mat
        return mat


def _assign_planar_uvs(bm: bmesh.types.BMesh, proj: str) -> None:
    uv_layer = bm.loops.layers.uv.verify()
    p = proj.upper()
    for face in bm.faces:
        n = face.normal
        if p == "BOX":
            ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
            if az >= ax and az >= ay:
                fp = "XY"
            elif ay >= ax:
                fp = "XZ"
            else:
                fp = "YZ"
        else:
            fp = p
        for loop in face.loops:
            co = loop.vert.co
            if fp == "XY":
                loop[uv_layer].uv = (co.x, co.y)
            elif fp == "XZ":
                loop[uv_layer].uv = (co.x, co.z)
            else:
                loop[uv_layer].uv = (co.y, co.z)


class EnvBuilder:
    """Clean procedural bmesh builder operating strictly inside a dedicated collection."""

    def __init__(self, scene: bpy.types.Scene, mats: MatLib, rng: random.Random) -> None:
        self.scene = scene
        self.mats = mats
        self.rng = rng
        self.mesh_count = 0
        self.poly_count = 0

        # Remove previous EnvDress collection if re-invoked without factory reset
        old = bpy.data.collections.get(COLLECTION_NAME)
        if old is not None:
            for obj in list(old.objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            if old.name in scene.collection.children:
                scene.collection.children.unlink(old)
            bpy.data.collections.remove(old)

        self.coll = bpy.data.collections.new(COLLECTION_NAME)
        scene.collection.children.link(self.coll)

    def _finish_bm(
        self,
        name: str,
        bm: bmesh.types.BMesh,
        mat: bpy.types.Material | None,
        uv_proj: str = "BOX",
        smooth: bool = False,
        recalc_normals: bool = True,
    ) -> bpy.types.Object:
        if recalc_normals and len(bm.faces) > 0:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        _assign_planar_uvs(bm, uv_proj)
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        if smooth:
            for poly in mesh.polygons:
                poly.use_smooth = True
        if mat is not None:
            mesh.materials.append(mat)
        obj = bpy.data.objects.new(name, mesh)
        self.coll.objects.link(obj)
        self.mesh_count += 1
        self.poly_count += len(mesh.polygons)
        return obj

    def box(
        self,
        name: str,
        x0: float,
        x1: float,
        y0: float,
        y1: float,
        z0: float,
        z1: float,
        mat: bpy.types.Material | None,
        uv_proj: str = "BOX",
        yaw: float = 0.0,
    ) -> bpy.types.Object:
        if x1 < x0:
            x0, x1 = x1, x0
        if y1 < y0:
            y0, y1 = y1, y0
        if z1 < z0:
            z0, z1 = z1, z0
        cx, cy, cz = 0.5 * (x0 + x1), 0.5 * (y0 + y1), 0.5 * (z0 + z1)
        sx, sy, sz = max(1e-4, x1 - x0), max(1e-4, y1 - y0), max(1e-4, z1 - z0)
        bm = bmesh.new()
        mat_xform = (
            Matrix.Translation((cx, cy, cz))
            @ Matrix.Rotation(yaw, 4, "Z")
            @ Matrix.Diagonal((sx, sy, sz, 1.0))
        )
        bmesh.ops.create_cube(bm, size=1.0, matrix=mat_xform)
        return self._finish_bm(name, bm, mat, uv_proj=uv_proj, smooth=False)

    def cylinder(
        self,
        name: str,
        cx: float,
        cy: float,
        z0: float,
        z1: float,
        r0: float,
        r1: float,
        mat: bpy.types.Material | None,
        segs: int = 14,
        smooth: bool = True,
    ) -> bpy.types.Object:
        h = max(1e-4, abs(z1 - z0))
        cz = 0.5 * (z0 + z1)
        bm = bmesh.new()
        bmesh.ops.create_cone(
            bm,
            cap_ends=True,
            cap_tris=False,
            segments=segs,
            radius1=max(1e-4, r0),
            radius2=max(1e-4, r1),
            depth=h,
            matrix=Matrix.Translation((cx, cy, cz)),
        )
        return self._finish_bm(name, bm, mat, uv_proj="BOX", smooth=smooth)

    def ground_plane(
        self,
        name: str,
        x0: float,
        x1: float,
        y0: float,
        y1: float,
        z: float,
        mat: bpy.types.Material | None,
    ) -> bpy.types.Object:
        bm = bmesh.new()
        v0 = bm.verts.new((x0, y0, z))
        v1 = bm.verts.new((x1, y0, z))
        v2 = bm.verts.new((x1, y1, z))
        v3 = bm.verts.new((x0, y1, z))
        bm.faces.new((v0, v1, v2, v3))
        return self._finish_bm(name, bm, mat, uv_proj="XY", smooth=False, recalc_normals=False)

    def window_assembly_x(
        self,
        name: str,
        ox0: float,
        ox1: float,
        y_inner: float,
        thickness: float,
        oz0: float,
        oz1: float,
        frame_mat: bpy.types.Material,
        glass_mat: bpy.types.Material,
        mullions_x: int = 1,
        mullions_z: int = 1,
        curtain_mat: bpy.types.Material | None = None,
        blind_mat: bpy.types.Material | None = None,
    ) -> None:
        fw = 0.055
        y_mid = y_inner + 0.5 * thickness
        y_out = y_inner + thickness
        # Outer frame jambs, head, sill
        self.box(f"{name}_jamb_l", ox0, ox0 + fw, y_inner - 0.02, y_out + 0.02, oz0, oz1, frame_mat)
        self.box(f"{name}_jamb_r", ox1 - fw, ox1, y_inner - 0.02, y_out + 0.02, oz0, oz1, frame_mat)
        self.box(f"{name}_head", ox0, ox1, y_inner - 0.02, y_out + 0.02, oz1 - fw, oz1, frame_mat)
        self.box(f"{name}_sill", ox0 - 0.06, ox1 + 0.06, y_inner - 0.065, y_out + 0.04, oz0 - 0.035, oz0 + 0.015, frame_mat)
        # Interior casing trim
        cw = 0.065
        self.box(f"{name}_case_l", ox0 - cw, ox0 + 0.01, y_inner - 0.028, y_inner, oz0 - 0.03, oz1 + cw, frame_mat)
        self.box(f"{name}_case_r", ox1 - 0.01, ox1 + cw, y_inner - 0.028, y_inner, oz0 - 0.03, oz1 + cw, frame_mat)
        self.box(f"{name}_case_t", ox0 - cw, ox1 + cw, y_inner - 0.028, y_inner, oz1 - 0.01, oz1 + cw, frame_mat)
        # Mullions
        w = ox1 - ox0
        h = oz1 - oz0
        for i in range(1, mullions_x + 1):
            mx = ox0 + w * (i / (mullions_x + 1))
            self.box(f"{name}_mx_{i}", mx - 0.018, mx + 0.018, y_mid - 0.025, y_mid + 0.025, oz0 + fw, oz1 - fw, frame_mat)
        for j in range(1, mullions_z + 1):
            mz = oz0 + h * (j / (mullions_z + 1))
            self.box(f"{name}_mz_{j}", ox0 + fw, ox1 - fw, y_mid - 0.022, y_mid + 0.022, mz - 0.016, mz + 0.016, frame_mat)
        # Glazing pane
        self.box(f"{name}_glass", ox0 + fw, ox1 - fw, y_mid - 0.005, y_mid + 0.005, oz0 + fw, oz1 - fw, glass_mat, uv_proj="XZ")

        if blind_mat is not None:
            self.box(f"{name}_valance", ox0 + 0.02, ox1 - 0.02, y_inner - 0.05, y_inner + 0.04, oz1 - 0.09, oz1 - 0.01, blind_mat)
            for k in range(4):
                lz = oz1 - 0.13 - k * 0.055
                if lz > oz0 + 0.25:
                    self.box(f"{name}_slat_{k}", ox0 + fw, ox1 - fw, y_inner - 0.02, y_inner + 0.015, lz, lz + 0.012, blind_mat)

        if curtain_mat is not None:
            rod_mat = self.mats.metal("curtain_rod", (0.18, 0.16, 0.15), roughness=0.30)
            rod_z = oz1 + 0.14
            self.box(f"{name}_rod", ox0 - 0.42, ox1 + 0.42, y_inner - 0.11, y_inner - 0.08, rod_z - 0.012, rod_z + 0.012, rod_mat)
            for side_idx, (cx0, cx1) in enumerate(((ox0 - 0.36, ox0 + 0.10), (ox1 - 0.10, ox1 + 0.36))):
                self._drape_panel_x(f"{name}_curt_{side_idx}", cx0, cx1, y_inner - 0.095, GROUND_Z + 0.02, rod_z - 0.01, curtain_mat)

    def _drape_panel_x(
        self,
        name: str,
        x0: float,
        x1: float,
        y_center: float,
        z0: float,
        z1: float,
        mat: bpy.types.Material,
    ) -> bpy.types.Object:
        bm = bmesh.new()
        nx, nz = 10, 6
        grid: list[list[bmesh.types.BMVert]] = []
        for iz in range(nz + 1):
            tz = iz / nz
            z = z0 + (z1 - z0) * tz
            row = []
            for ix in range(nx + 1):
                tx = ix / nx
                x = x0 + (x1 - x0) * tx
                pleat = 0.032 * math.sin(tx * math.pi * 5.0) * (0.65 + 0.35 * (1.0 - tz))
                row.append(bm.verts.new((x, y_center + pleat, z)))
            grid.append(row)
        for iz in range(nz):
            for ix in range(nx):
                bm.faces.new((grid[iz][ix], grid[iz][ix + 1], grid[iz + 1][ix + 1], grid[iz + 1][ix]))
        return self._finish_bm(name, bm, mat, uv_proj="XZ", smooth=True, recalc_normals=False)

    def window_assembly_y(
        self,
        name: str,
        oy0: float,
        oy1: float,
        x_inner: float,
        thickness: float,
        side: int,
        oz0: float,
        oz1: float,
        frame_mat: bpy.types.Material,
        glass_mat: bpy.types.Material,
        mullions_y: int = 1,
        mullions_z: int = 1,
    ) -> None:
        # side = +1 for right wall (+X, exterior is +x), -1 for left wall (-X, exterior is -x)
        fw = 0.055
        x_out = x_inner + side * thickness
        x_mid = 0.5 * (x_inner + x_out)
        xa, xb = min(x_inner, x_out), max(x_inner, x_out)
        self.box(f"{name}_jl", xa - 0.02, xb + 0.02, oy0, oy0 + fw, oz0, oz1, frame_mat)
        self.box(f"{name}_jr", xa - 0.02, xb + 0.02, oy1 - fw, oy1, oz0, oz1, frame_mat)
        self.box(f"{name}_hd", xa - 0.02, xb + 0.02, oy0, oy1, oz1 - fw, oz1, frame_mat)
        sill_in = x_inner - side * 0.06
        self.box(f"{name}_sl", min(sill_in, x_out), max(sill_in, x_out), oy0 - 0.05, oy1 + 0.05, oz0 - 0.035, oz0 + 0.015, frame_mat)
        w = oy1 - oy0
        h = oz1 - oz0
        for i in range(1, mullions_y + 1):
            my = oy0 + w * (i / (mullions_y + 1))
            self.box(f"{name}_my_{i}", x_mid - 0.022, x_mid + 0.022, my - 0.018, my + 0.018, oz0 + fw, oz1 - fw, frame_mat)
        for j in range(1, mullions_z + 1):
            mz = oz0 + h * (j / (mullions_z + 1))
            self.box(f"{name}_mz_{j}", x_mid - 0.022, x_mid + 0.022, oy0 + fw, oy1 - fw, mz - 0.016, mz + 0.016, frame_mat)
        self.box(f"{name}_gl", x_mid - 0.005, x_mid + 0.005, oy0 + fw, oy1 - fw, oz0 + fw, oz1 - fw, glass_mat, uv_proj="YZ")

    def wall_x(
        self,
        name: str,
        x0: float,
        x1: float,
        y_inner: float,
        thickness: float,
        z0: float,
        z1: float,
        wall_mat: bpy.types.Material,
        openings: list[dict[str, Any]] | None = None,
        trim_mat: bpy.types.Material | None = None,
        glass_mat: bpy.types.Material | None = None,
        base_h: float = 0.11,
        crown_h: float = 0.08,
    ) -> None:
        y_out = y_inner + thickness
        ops = sorted(openings or [], key=lambda d: d["a0"])
        cx = x0
        idx = 0
        for op in ops:
            ox0 = max(cx, float(op["a0"]))
            ox1 = min(x1, float(op["a1"]))
            oz0 = max(z0, float(op["z0"]))
            oz1 = min(z1, float(op["z1"]))
            if ox1 <= ox0 + 0.04:
                continue
            if ox0 > cx + 0.02:
                self.box(f"{name}_p{idx}", cx, ox0, y_inner, y_out, z0, z1, wall_mat, uv_proj="XZ")
                idx += 1
            if oz0 > z0 + 0.02:
                self.box(f"{name}_s{idx}", ox0, ox1, y_inner, y_out, z0, oz0, wall_mat, uv_proj="XZ")
                idx += 1
            if z1 > oz1 + 0.02:
                self.box(f"{name}_h{idx}", ox0, ox1, y_inner, y_out, oz1, z1, wall_mat, uv_proj="XZ")
                idx += 1
            if op.get("kind", "window") == "window" and trim_mat is not None and glass_mat is not None:
                self.window_assembly_x(
                    f"{name}_win_{idx}",
                    ox0,
                    ox1,
                    y_inner,
                    thickness,
                    oz0,
                    oz1,
                    frame_mat=op.get("frame_mat") or trim_mat,
                    glass_mat=op.get("glass_mat") or glass_mat,
                    mullions_x=int(op.get("mx", 1)),
                    mullions_z=int(op.get("mz", 1)),
                    curtain_mat=op.get("curtain_mat"),
                    blind_mat=op.get("blind_mat"),
                )
            elif op.get("kind") == "alcove":
                depth = float(op.get("depth", 0.36))
                back_mat = op.get("back_mat") or wall_mat
                self.box(f"{name}_alc_b{idx}", ox0, ox1, y_out + depth - 0.06, y_out + depth, oz0, oz1, back_mat, uv_proj="XZ")
                self.box(f"{name}_alc_l{idx}", ox0 - 0.04, ox0, y_inner, y_out + depth, oz0, oz1, back_mat, uv_proj="YZ")
                self.box(f"{name}_alc_r{idx}", ox1, ox1 + 0.04, y_inner, y_out + depth, oz0, oz1, back_mat, uv_proj="YZ")
                self.box(f"{name}_alc_t{idx}", ox0, ox1, y_inner, y_out + depth, oz1, oz1 + 0.04, back_mat, uv_proj="XY")
                self.box(f"{name}_alc_f{idx}", ox0, ox1, y_inner, y_out + depth, oz0 - 0.04, oz0, back_mat, uv_proj="XY")
            cx = ox1
        if x1 > cx + 0.02:
            self.box(f"{name}_tail", cx, x1, y_inner, y_out, z0, z1, wall_mat, uv_proj="XZ")

        if trim_mat is not None and base_h > 0.005:
            self.box(f"{name}_base", x0, x1, y_inner - 0.022, y_inner, z0, z0 + base_h, trim_mat, uv_proj="XZ")
        if trim_mat is not None and crown_h > 0.005:
            self.box(f"{name}_crown", x0, x1, y_inner - 0.055, y_inner, z1 - crown_h, z1, trim_mat, uv_proj="XZ")

    def wall_y(
        self,
        name: str,
        y0: float,
        y1: float,
        x_inner: float,
        thickness: float,
        side: int,
        z0: float,
        z1: float,
        wall_mat: bpy.types.Material,
        openings: list[dict[str, Any]] | None = None,
        trim_mat: bpy.types.Material | None = None,
        glass_mat: bpy.types.Material | None = None,
        base_h: float = 0.11,
        crown_h: float = 0.08,
    ) -> None:
        x_out = x_inner + side * thickness
        xa, xb = min(x_inner, x_out), max(x_inner, x_out)
        ops = sorted(openings or [], key=lambda d: d["a0"])
        cy = y0
        idx = 0
        for op in ops:
            oy0 = max(cy, float(op["a0"]))
            oy1 = min(y1, float(op["a1"]))
            oz0 = max(z0, float(op["z0"]))
            oz1 = min(z1, float(op["z1"]))
            if oy1 <= oy0 + 0.04:
                continue
            if oy0 > cy + 0.02:
                self.box(f"{name}_p{idx}", xa, xb, cy, oy0, z0, z1, wall_mat, uv_proj="YZ")
                idx += 1
            if oz0 > z0 + 0.02:
                self.box(f"{name}_s{idx}", xa, xb, oy0, oy1, z0, oz0, wall_mat, uv_proj="YZ")
                idx += 1
            if z1 > oz1 + 0.02:
                self.box(f"{name}_h{idx}", xa, xb, oy0, oy1, oz1, z1, wall_mat, uv_proj="YZ")
                idx += 1
            if op.get("kind", "window") == "window" and trim_mat is not None and glass_mat is not None:
                self.window_assembly_y(
                    f"{name}_win_{idx}",
                    oy0,
                    oy1,
                    x_inner,
                    thickness,
                    side,
                    oz0,
                    oz1,
                    frame_mat=op.get("frame_mat") or trim_mat,
                    glass_mat=op.get("glass_mat") or glass_mat,
                    mullions_y=int(op.get("my", 1)),
                    mullions_z=int(op.get("mz", 1)),
                )
            cy = oy1
        if y1 > cy + 0.02:
            self.box(f"{name}_tail", xa, xb, cy, y1, z0, z1, wall_mat, uv_proj="YZ")

        if trim_mat is not None and base_h > 0.005:
            bx0, bx1 = (x_inner - 0.022, x_inner) if side > 0 else (x_inner, x_inner + 0.022)
            self.box(f"{name}_base", bx0, bx1, y0, y1, z0, z0 + base_h, trim_mat, uv_proj="YZ")
        if trim_mat is not None and crown_h > 0.005:
            cx0, cx1 = (x_inner - 0.055, x_inner) if side > 0 else (x_inner, x_inner + 0.055)
            self.box(f"{name}_crown", cx0, cx1, y0, y1, z1 - crown_h, z1, trim_mat, uv_proj="YZ")

    def base_cabinet_run(
        self,
        name: str,
        x0: float,
        x1: float,
        y_back: float,
        depth: float,
        height: float,
        body_mat: bpy.types.Material,
        top_mat: bpy.types.Material,
        metal_mat: bpy.types.Material,
        doors: int = 4,
        shaker: bool = True,
    ) -> float:
        y_front = y_back - depth
        toe_h = 0.095
        top_t = 0.036
        # Recessed toe-kick
        self.box(f"{name}_toe", x0 + 0.01, x1 - 0.01, y_front + 0.06, y_back, GROUND_Z, GROUND_Z + toe_h, body_mat)
        # Main carcass
        self.box(f"{name}_carc", x0, x1, y_front + 0.02, y_back, GROUND_Z + toe_h, GROUND_Z + height - top_t, body_mat)
        # Countertop overhang
        top_z = GROUND_Z + height
        self.box(f"{name}_top", x0 - 0.015, x1 + 0.015, y_front - 0.025, y_back, top_z - top_t, top_z, top_mat, uv_proj="XY")
        # Door fronts & handles
        span = x1 - x0
        n = max(1, doors)
        dw = span / n
        for i in range(n):
            dx0 = x0 + i * dw + 0.008
            dx1 = x0 + (i + 1) * dw - 0.008
            dz0 = GROUND_Z + toe_h + 0.012
            dz1 = top_z - top_t - 0.012
            self.box(f"{name}_dr_{i}", dx0, dx1, y_front, y_front + 0.022, dz0, dz1, body_mat, uv_proj="XZ")
            if shaker and (dx1 - dx0) > 0.20:
                st = 0.045
                self.box(f"{name}_st_l{i}", dx0, dx0 + st, y_front - 0.009, y_front, dz0, dz1, body_mat)
                self.box(f"{name}_st_r{i}", dx1 - st, dx1, y_front - 0.009, y_front, dz0, dz1, body_mat)
                self.box(f"{name}_st_t{i}", dx0, dx1, y_front - 0.009, y_front, dz1 - st, dz1, body_mat)
                self.box(f"{name}_st_b{i}", dx0, dx1, y_front - 0.009, y_front, dz0, dz0 + st, body_mat)
            # Bar pull
            hx = dx1 - 0.065 if (i % 2 == 0) else dx0 + 0.065
            self.box(f"{name}_pull_{i}", hx - 0.007, hx + 0.007, y_front - 0.032, y_front - 0.006, dz1 - 0.17, dz1 - 0.04, metal_mat)
        return top_z

    def upper_cabinet_run(
        self,
        name: str,
        x0: float,
        x1: float,
        y_back: float,
        depth: float,
        z0: float,
        z1: float,
        body_mat: bpy.types.Material,
        metal_mat: bpy.types.Material,
        doors: int = 2,
        glass_mat: bpy.types.Material | None = None,
    ) -> None:
        y_front = y_back - depth
        self.box(f"{name}_box", x0, x1, y_front + 0.02, y_back, z0, z1, body_mat)
        n = max(1, doors)
        dw = (x1 - x0) / n
        for i in range(n):
            dx0 = x0 + i * dw + 0.008
            dx1 = x0 + (i + 1) * dw - 0.008
            if glass_mat is not None:
                st = 0.05
                self.box(f"{name}_gl_l{i}", dx0, dx0 + st, y_front, y_front + 0.024, z0 + 0.01, z1 - 0.01, body_mat)
                self.box(f"{name}_gl_r{i}", dx1 - st, dx1, y_front, y_front + 0.024, z0 + 0.01, z1 - 0.01, body_mat)
                self.box(f"{name}_gl_t{i}", dx0, dx1, y_front, y_front + 0.024, z1 - st, z1 - 0.01, body_mat)
                self.box(f"{name}_gl_b{i}", dx0, dx1, y_front, y_front + 0.024, z0 + 0.01, z0 + st, body_mat)
                self.box(f"{name}_gl_p{i}", dx0 + st, dx1 - st, y_front + 0.008, y_front + 0.016, z0 + st, z1 - st, glass_mat, uv_proj="XZ")
            else:
                self.box(f"{name}_ud_{i}", dx0, dx1, y_front, y_front + 0.022, z0 + 0.01, z1 - 0.01, body_mat)
            hx = dx1 - 0.055 if (i % 2 == 0) else dx0 + 0.055
            self.box(f"{name}_up_{i}", hx - 0.006, hx + 0.006, y_front - 0.028, y_front, z0 + 0.06, z0 + 0.18, metal_mat)

    def sink_and_faucet(
        self,
        name: str,
        cx: float,
        cy: float,
        top_z: float,
        metal_mat: bpy.types.Material,
    ) -> None:
        # Rim + recessed dark basin + gooseneck faucet
        self.box(f"{name}_rim_f", cx - 0.32, cx + 0.32, cy - 0.24, cy - 0.20, top_z, top_z + 0.012, metal_mat)
        self.box(f"{name}_rim_b", cx - 0.32, cx + 0.32, cy + 0.20, cy + 0.24, top_z, top_z + 0.012, metal_mat)
        self.box(f"{name}_rim_l", cx - 0.32, cx - 0.28, cy - 0.24, cy + 0.24, top_z, top_z + 0.012, metal_mat)
        self.box(f"{name}_rim_r", cx + 0.28, cx + 0.32, cy - 0.24, cy + 0.24, top_z, top_z + 0.012, metal_mat)
        basin_mat = self.mats.metal("sink_basin", (0.38, 0.40, 0.42), roughness=0.32)
        self.box(f"{name}_basin", cx - 0.28, cx + 0.28, cy - 0.20, cy + 0.20, top_z - 0.005, top_z + 0.003, basin_mat)
        # Gooseneck faucet
        fy = cy + 0.23
        self.cylinder(f"{name}_f_stem", cx, fy, top_z, top_z + 0.28, 0.018, 0.014, metal_mat, segs=10)
        self.box(f"{name}_f_arm", cx - 0.013, cx + 0.013, fy - 0.16, fy + 0.01, top_z + 0.265, top_z + 0.29, metal_mat)
        self.cylinder(f"{name}_f_noz", cx, fy - 0.15, top_z + 0.21, top_z + 0.275, 0.012, 0.013, metal_mat, segs=10)
        self.cylinder(f"{name}_f_hdl", cx + 0.07, fy, top_z, top_z + 0.065, 0.015, 0.012, metal_mat, segs=8)

    def range_hood(
        self,
        name: str,
        cx: float,
        y_back: float,
        z_bottom: float,
        z_top: float,
        width: float,
        mat: bpy.types.Material,
    ) -> None:
        bm = bmesh.new()
        hw = width * 0.5
        ch_w = width * 0.24
        d_bot = 0.56
        d_top = 0.30
        z_mid = z_bottom + 0.48
        # Lower trapezoidal canopy
        v0 = bm.verts.new((cx - hw, y_back - d_bot, z_bottom))
        v1 = bm.verts.new((cx + hw, y_back - d_bot, z_bottom))
        v2 = bm.verts.new((cx + hw, y_back, z_bottom))
        v3 = bm.verts.new((cx - hw, y_back, z_bottom))
        v4 = bm.verts.new((cx - ch_w, y_back - d_top, z_mid))
        v5 = bm.verts.new((cx + ch_w, y_back - d_top, z_mid))
        v6 = bm.verts.new((cx + ch_w, y_back, z_mid))
        v7 = bm.verts.new((cx - ch_w, y_back, z_mid))
        bm.faces.new((v0, v3, v2, v1))
        bm.faces.new((v0, v1, v5, v4))
        bm.faces.new((v1, v2, v6, v5))
        bm.faces.new((v2, v3, v7, v6))
        bm.faces.new((v3, v0, v4, v7))
        bm.faces.new((v4, v5, v6, v7))
        self._finish_bm(f"{name}_canopy", bm, mat, uv_proj="BOX")
        self.box(f"{name}_chimney", cx - ch_w, cx + ch_w, y_back - d_top, y_back, z_mid, z_top, mat)

    def floating_shelf(
        self,
        name: str,
        x0: float,
        x1: float,
        y_back: float,
        depth: float,
        z_top: float,
        wood_mat: bpy.types.Material,
        bracket_mat: bpy.types.Material,
    ) -> float:
        t = 0.038
        self.box(f"{name}_plank", x0, x1, y_back - depth, y_back, z_top - t, z_top, wood_mat, uv_proj="XY")
        for idx, bx in enumerate((x0 + 0.14, x1 - 0.14)):
            self.box(f"{name}_brk_{idx}", bx - 0.012, bx + 0.012, y_back - depth * 0.85, y_back, z_top - t - 0.12, z_top - t, bracket_mat)
        return z_top

    def built_in_bookcase(
        self,
        name: str,
        x0: float,
        x1: float,
        y_back: float,
        depth: float,
        z_top: float,
        wood_mat: bpy.types.Material,
        back_mat: bpy.types.Material,
        shelf_zs: list[float],
    ) -> list[float]:
        y_front = y_back - depth
        t = 0.032
        self.box(f"{name}_back", x0, x1, y_back - 0.025, y_back, GROUND_Z, z_top, back_mat, uv_proj="XZ")
        self.box(f"{name}_l", x0, x0 + t, y_front, y_back, GROUND_Z, z_top, wood_mat)
        self.box(f"{name}_r", x1 - t, x1, y_front, y_back, GROUND_Z, z_top, wood_mat)
        self.box(f"{name}_top", x0 - 0.02, x1 + 0.02, y_front - 0.02, y_back, z_top - 0.04, z_top, wood_mat)
        self.box(f"{name}_base", x0, x1, y_front, y_back, GROUND_Z, GROUND_Z + 0.08, wood_mat)
        mid_x = 0.5 * (x0 + x1)
        if (x1 - x0) > 1.45:
            self.box(f"{name}_div", mid_x - 0.015, mid_x + 0.015, y_front + 0.01, y_back, GROUND_Z + 0.08, z_top - 0.04, wood_mat)
        out_zs: list[float] = []
        for idx, sz in enumerate(shelf_zs):
            self.box(f"{name}_sh_{idx}", x0 + t, x1 - t, y_front + 0.008, y_back - 0.02, sz - 0.026, sz, wood_mat, uv_proj="XY")
            out_zs.append(sz)
        return out_zs

    def picture_ledge(
        self,
        name: str,
        x0: float,
        x1: float,
        y_wall: float,
        z_top: float,
        mat: bpy.types.Material,
    ) -> float:
        self.box(f"{name}_base", x0, x1, y_wall - 0.14, y_wall, z_top - 0.025, z_top, mat, uv_proj="XY")
        self.box(f"{name}_lip", x0, x1, y_wall - 0.14, y_wall - 0.125, z_top, z_top + 0.022, mat, uv_proj="XZ")
        return z_top

    def framed_artwork(
        self,
        name: str,
        cx: float,
        y_wall: float,
        cz: float,
        w: float,
        h: float,
        frame_mat: bpy.types.Material,
        art_rgb1: tuple[float, float, float],
        art_rgb2: tuple[float, float, float],
    ) -> None:
        fw = 0.04
        d = 0.032
        self.box(f"{name}_fl", cx - w * 0.5, cx - w * 0.5 + fw, y_wall - d, y_wall, cz - h * 0.5, cz + h * 0.5, frame_mat)
        self.box(f"{name}_fr", cx + w * 0.5 - fw, cx + w * 0.5, y_wall - d, y_wall, cz - h * 0.5, cz + h * 0.5, frame_mat)
        self.box(f"{name}_ft", cx - w * 0.5, cx + w * 0.5, y_wall - d, y_wall, cz + h * 0.5 - fw, cz + h * 0.5, frame_mat)
        self.box(f"{name}_fb", cx - w * 0.5, cx + w * 0.5, y_wall - d, y_wall, cz - h * 0.5, cz - h * 0.5 + fw, frame_mat)
        mat_mat = self.mats.paint(f"{name}_matboard", (0.92, 0.90, 0.86), roughness=0.78)
        self.box(f"{name}_mb", cx - w * 0.5 + fw, cx + w * 0.5 - fw, y_wall - d + 0.012, y_wall - 0.004, cz - h * 0.5 + fw, cz + h * 0.5 - fw, mat_mat)
        art_mat = self.mats.stone(f"{name}_canvas", art_rgb1, art_rgb2, roughness=0.65, scale=2.6, bump_strength=0.03)
        pad = fw + 0.065
        if w > 2 * pad + 0.1 and h > 2 * pad + 0.1:
            self.box(f"{name}_art", cx - w * 0.5 + pad, cx + w * 0.5 - pad, y_wall - d + 0.008, y_wall - d + 0.014, cz - h * 0.5 + pad, cz + h * 0.5 - pad, art_mat, uv_proj="XZ")

    def pendant_lamp(
        self,
        name: str,
        cx: float,
        cy: float,
        z_ceil: float,
        z_shade: float,
        shade_mat: bpy.types.Material,
        glow_mat: bpy.types.Material,
        radius: float = 0.14,
    ) -> None:
        cord_mat = self.mats.metal("lamp_cord", (0.12, 0.12, 0.13), roughness=0.45)
        self.cylinder(f"{name}_canopy", cx, cy, z_ceil - 0.04, z_ceil, 0.065, 0.065, cord_mat, segs=12)
        self.cylinder(f"{name}_cord", cx, cy, z_shade + 0.18, z_ceil - 0.03, 0.006, 0.006, cord_mat, segs=8)
        self.cylinder(f"{name}_shade", cx, cy, z_shade, z_shade + 0.20, radius, radius * 0.42, shade_mat, segs=16)
        self.cylinder(f"{name}_bulb", cx, cy, z_shade + 0.01, z_shade + 0.06, radius * 0.68, radius * 0.55, glow_mat, segs=12)

    def floor_lamp(
        self,
        name: str,
        cx: float,
        cy: float,
        z_base: float,
        metal_mat: bpy.types.Material,
        shade_mat: bpy.types.Material,
        glow_mat: bpy.types.Material,
        height: float = 1.68,
    ) -> None:
        self.cylinder(f"{name}_base", cx, cy, z_base, z_base + 0.03, 0.18, 0.16, metal_mat, segs=16)
        self.cylinder(f"{name}_stem", cx, cy, z_base + 0.03, z_base + height - 0.25, 0.015, 0.012, metal_mat, segs=10)
        self.cylinder(f"{name}_shade", cx, cy, z_base + height - 0.34, z_base + height, 0.22, 0.18, shade_mat, segs=18)
        self.cylinder(f"{name}_glow", cx, cy, z_base + height - 0.30, z_base + height - 0.06, 0.15, 0.13, glow_mat, segs=12)

    def wall_sconce(
        self,
        name: str,
        cx: float,
        y_wall: float,
        cz: float,
        metal_mat: bpy.types.Material,
        glow_mat: bpy.types.Material,
    ) -> None:
        self.cylinder(f"{name}_plate", cx, y_wall - 0.015, cz - 0.05, cz + 0.05, 0.045, 0.045, metal_mat, segs=12)
        self.box(f"{name}_arm", cx - 0.012, cx + 0.012, y_wall - 0.12, y_wall - 0.01, cz - 0.012, cz + 0.012, metal_mat)
        self.cylinder(f"{name}_diff", cx, y_wall - 0.11, cz - 0.09, cz + 0.13, 0.042, 0.042, glow_mat, segs=12)

    def table_lamp(
        self,
        name: str,
        cx: float,
        cy: float,
        z_base: float,
        base_mat: bpy.types.Material,
        shade_mat: bpy.types.Material,
        glow_mat: bpy.types.Material,
    ) -> None:
        self.cylinder(f"{name}_base", cx, cy, z_base, z_base + 0.24, 0.085, 0.055, base_mat, segs=14)
        self.cylinder(f"{name}_shade", cx, cy, z_base + 0.22, z_base + 0.44, 0.16, 0.13, shade_mat, segs=16)
        self.cylinder(f"{name}_bulb", cx, cy, z_base + 0.25, z_base + 0.38, 0.09, 0.08, glow_mat, segs=10)

    def monitor_set(
        self,
        name: str,
        cx: float,
        cy: float,
        z_top: float,
        yaw: float,
        screen_mat: bpy.types.Material,
        dual: bool = True,
    ) -> None:
        bezel = self.mats.metal("mon_bezel", (0.10, 0.10, 0.11), roughness=0.34)
        offsets = (-0.30, 0.30) if dual else (0.0,)
        for idx, ox in enumerate(offsets):
            ang = yaw + (0.14 if ox < 0 else -0.14 if ox > 0 else 0.0)
            px = cx + ox * math.cos(yaw)
            py = cy + ox * math.sin(yaw)
            self.box(f"{name}_base_{idx}", px - 0.11, px + 0.11, py - 0.08, py + 0.08, z_top, z_top + 0.016, bezel, yaw=ang)
            self.box(f"{name}_neck_{idx}", px - 0.025, px + 0.025, py + 0.01, py + 0.05, z_top + 0.016, z_top + 0.24, bezel, yaw=ang)
            self.box(f"{name}_body_{idx}", px - 0.27, px + 0.27, py - 0.018, py + 0.015, z_top + 0.12, z_top + 0.44, bezel, yaw=ang)
            # Slightly offset screen front face
            sx = px - 0.020 * math.sin(ang)
            sy = py - 0.020 * math.cos(ang)
            self.box(f"{name}_scr_{idx}", sx - 0.255, sx + 0.255, sy - 0.004, sy + 0.004, z_top + 0.135, z_top + 0.425, screen_mat, uv_proj="XZ", yaw=ang)

    def bed_assembly(
        self,
        name: str,
        cx: float,
        y_head: float,
        wood_mat: bpy.types.Material,
        duvet_mat: bpy.types.Material,
        pillow_mat: bpy.types.Material,
        headboard_mat: bpy.types.Material,
        width: float = 1.75,
        length: float = 2.02,
    ) -> None:
        hw = width * 0.5
        y_foot = y_head - length
        # Headboard
        self.box(f"{name}_hb", cx - hw - 0.06, cx + hw + 0.06, y_head - 0.09, y_head, GROUND_Z, GROUND_Z + 1.24, headboard_mat)
        # Frame + legs
        self.box(f"{name}_frame", cx - hw - 0.03, cx + hw + 0.03, y_foot, y_head - 0.08, GROUND_Z + 0.14, GROUND_Z + 0.34, wood_mat)
        for lx in (cx - hw, cx + hw):
            for ly in (y_foot + 0.06, y_head - 0.14):
                self.box(f"{name}_leg_{lx:.1f}_{ly:.1f}", lx - 0.035, lx + 0.035, ly - 0.035, ly + 0.035, GROUND_Z, GROUND_Z + 0.15, wood_mat)
        # Mattress + draped duvet
        sheet_mat = self.mats.fabric("bed_sheet", (0.90, 0.89, 0.86), roughness=0.86)
        self.box(f"{name}_matt", cx - hw, cx + hw, y_foot + 0.02, y_head - 0.10, GROUND_Z + 0.32, GROUND_Z + 0.56, sheet_mat)
        self.box(f"{name}_duvet", cx - hw - 0.04, cx + hw + 0.04, y_foot - 0.02, y_head - 0.56, GROUND_Z + 0.36, GROUND_Z + 0.61, duvet_mat)
        # Pillows
        for idx, px in enumerate((cx - hw * 0.46, cx + hw * 0.46)):
            bm = bmesh.new()
            bmesh.ops.create_icosphere(
                bm,
                subdivisions=2,
                radius=1.0,
                matrix=Matrix.Translation((px, y_head - 0.30, GROUND_Z + 0.66)) @ Matrix.Diagonal((0.34, 0.19, 0.11, 1.0)),
            )
            self._finish_bm(f"{name}_pil_{idx}", bm, pillow_mat, uv_proj="XY", smooth=True)

    def museum_sculpture(
        self,
        name: str,
        cx: float,
        cy: float,
        z_base: float,
        mat: bpy.types.Material,
        style: int = 0,
    ) -> None:
        # Organic ceramic/bronze amphora or sculpted abstract monolith (never a plain cube)
        bm = bmesh.new()
        segs = 18
        if style % 2 == 0:
            profile = [
                (0.08, 0.00),
                (0.11, 0.06),
                (0.16, 0.22),
                (0.14, 0.38),
                (0.07, 0.48),
                (0.10, 0.56),
            ]
        else:
            profile = [
                (0.12, 0.00),
                (0.09, 0.14),
                (0.17, 0.32),
                (0.13, 0.50),
                (0.05, 0.64),
            ]
        rings: list[list[bmesh.types.BMVert]] = []
        for r, dz in profile:
            ring = []
            for i in range(segs):
                a = 2.0 * math.pi * i / segs
                wobble = 1.0 + 0.08 * math.sin(a * 3.0 + dz * 5.0) * (style % 2)
                ring.append(bm.verts.new((cx + r * wobble * math.cos(a), cy + r * wobble * math.sin(a), z_base + dz)))
            rings.append(ring)
        for ri in range(len(rings) - 1):
            for i in range(segs):
                ni = (i + 1) % segs
                bm.faces.new((rings[ri][i], rings[ri][ni], rings[ri + 1][ni], rings[ri + 1][i]))
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
        self._finish_bm(name, bm, mat, uv_proj="BOX", smooth=True)

    # --- Outdoor Organic & Landscape Builders ---

    def terrain_mesh(
        self,
        name: str,
        x0: float,
        x1: float,
        y0: float,
        y1: float,
        nx: int,
        ny: int,
        height_fn: Any,
        mat: bpy.types.Material,
    ) -> bpy.types.Object:
        bm = bmesh.new()
        grid: list[list[bmesh.types.BMVert]] = []
        for iy in range(ny + 1):
            ty = iy / ny
            y = y0 + (y1 - y0) * ty
            row = []
            for ix in range(nx + 1):
                tx = ix / nx
                x = x0 + (x1 - x0) * tx
                z = float(height_fn(x, y))
                row.append(bm.verts.new((x, y, z)))
            grid.append(row)
        for iy in range(ny):
            for ix in range(nx):
                bm.faces.new((grid[iy][ix], grid[iy][ix + 1], grid[iy + 1][ix + 1], grid[iy + 1][ix]))
        return self._finish_bm(name, bm, mat, uv_proj="XY", smooth=True, recalc_normals=False)

    def distant_ridge(
        self,
        name: str,
        x0: float,
        x1: float,
        y_base: float,
        depth: float,
        max_h: float,
        mat: bpy.types.Material,
        phase: float = 0.0,
        jagged: bool = False,
    ) -> bpy.types.Object:
        bm = bmesh.new()
        nx, ny = 32, 6
        grid: list[list[bmesh.types.BMVert]] = []
        for iy in range(ny + 1):
            ty = iy / ny
            y = y_base + depth * ty
            profile = math.sin(ty * math.pi)
            row = []
            for ix in range(nx + 1):
                tx = ix / nx
                x = x0 + (x1 - x0) * tx
                edge = math.sin(tx * math.pi) ** 0.45
                wave = (
                    0.50
                    + 0.28 * math.sin(x * 0.14 + phase)
                    + 0.16 * math.cos(x * 0.31 - phase * 1.4)
                    + 0.10 * math.sin(x * 0.67 + phase * 2.1)
                )
                if jagged:
                    wave = wave ** 1.45
                z = GROUND_Z - 0.15 + max_h * profile * edge * max(0.05, wave)
                row.append(bm.verts.new((x, y, z)))
            grid.append(row)
        for iy in range(ny):
            for ix in range(nx):
                bm.faces.new((grid[iy][ix], grid[iy][ix + 1], grid[iy + 1][ix + 1], grid[iy + 1][ix]))
        return self._finish_bm(name, bm, mat, uv_proj="XZ", smooth=not jagged, recalc_normals=False)

    def broadleaf_tree(
        self,
        name: str,
        cx: float,
        cy: float,
        z0: float,
        height: float,
        bark_mat: bpy.types.Material,
        leaf_mat: bpy.types.Material,
    ) -> None:
        trunk_h = height * 0.48
        r_base = max(0.11, height * 0.036)
        self.cylinder(f"{name}_tr", cx, cy, z0 - 0.10, z0 + trunk_h, r_base, r_base * 0.62, bark_mat, segs=8)
        # Organic multi-lobe crown
        bm = bmesh.new()
        crown_r = height * 0.34
        lobes = [
            (0.0, 0.0, trunk_h + crown_r * 0.72, 1.0, 1.0, 0.82),
            (-crown_r * 0.52, crown_r * 0.25, trunk_h + crown_r * 0.42, 0.76, 0.72, 0.68),
            (crown_r * 0.54, -crown_r * 0.18, trunk_h + crown_r * 0.46, 0.74, 0.76, 0.70),
            (crown_r * 0.12, crown_r * 0.50, trunk_h + crown_r * 0.58, 0.72, 0.70, 0.65),
            (-crown_r * 0.20, -crown_r * 0.45, trunk_h + crown_r * 0.38, 0.68, 0.68, 0.62),
        ]
        for lx, ly, lz, sx, sy, sz in lobes:
            res = bmesh.ops.create_icosphere(
                bm,
                subdivisions=2,
                radius=crown_r,
                matrix=Matrix.Translation((cx + lx, cy + ly, z0 + lz)) @ Matrix.Diagonal((sx, sy, sz, 1.0)),
            )
            for v in res["verts"]:
                j = 1.0 + 0.14 * math.sin(v.co.x * 4.3 + v.co.y * 3.7) * math.cos(v.co.z * 5.1)
                v.co.x = cx + lx + (v.co.x - (cx + lx)) * j
                v.co.y = cy + ly + (v.co.y - (cy + ly)) * j
        self._finish_bm(f"{name}_cr", bm, leaf_mat, uv_proj="BOX", smooth=True)

    def conifer_tree(
        self,
        name: str,
        cx: float,
        cy: float,
        z0: float,
        height: float,
        bark_mat: bpy.types.Material,
        needle_mat: bpy.types.Material,
        snow_mat: bpy.types.Material | None = None,
    ) -> None:
        self.cylinder(f"{name}_tr", cx, cy, z0 - 0.10, z0 + height * 0.55, height * 0.032, height * 0.012, bark_mat, segs=7)
        tiers = 5
        bm = bmesh.new()
        bm_snow = bmesh.new() if snow_mat is not None else None
        for i in range(tiers):
            t = i / tiers
            tz0 = z0 + height * (0.18 + 0.66 * t)
            th = height * (0.32 - 0.10 * t)
            rad = height * (0.28 * (1.0 - 0.68 * t))
            bmesh.ops.create_cone(
                bm,
                cap_ends=True,
                cap_tris=True,
                segments=9,
                radius1=rad,
                radius2=rad * 0.12,
                depth=th,
                matrix=Matrix.Translation((cx, cy, tz0 + th * 0.5)) @ Matrix.Rotation(i * 0.55, 4, "Z"),
            )
            if bm_snow is not None:
                bmesh.ops.create_cone(
                    bm_snow,
                    cap_ends=True,
                    cap_tris=True,
                    segments=9,
                    radius1=rad * 0.88,
                    radius2=rad * 0.10,
                    depth=th * 0.55,
                    matrix=Matrix.Translation((cx, cy, tz0 + th * 0.66)) @ Matrix.Rotation(i * 0.55, 4, "Z"),
                )
        self._finish_bm(f"{name}_ndl", bm, needle_mat, uv_proj="BOX", smooth=True)
        if bm_snow is not None and snow_mat is not None:
            self._finish_bm(f"{name}_snw", bm_snow, snow_mat, uv_proj="BOX", smooth=True)

    def shrub(
        self,
        name: str,
        cx: float,
        cy: float,
        z0: float,
        radius: float,
        mat: bpy.types.Material,
    ) -> None:
        bm = bmesh.new()
        for idx, (ox, oy, oz, sc) in enumerate(((0.0, 0.0, 0.55, 1.0), (0.45, 0.25, 0.42, 0.72), (-0.42, -0.20, 0.40, 0.74))):
            res = bmesh.ops.create_icosphere(
                bm,
                subdivisions=2,
                radius=radius * sc,
                matrix=Matrix.Translation((cx + ox * radius, cy + oy * radius, z0 + oz * radius)) @ Matrix.Diagonal((1.1, 1.0, 0.78, 1.0)),
            )
            for v in res["verts"]:
                v.co.z = max(z0 - 0.04, v.co.z + 0.06 * radius * math.sin(v.co.x * 7.0 + idx))
        self._finish_bm(name, bm, mat, uv_proj="BOX", smooth=True)

    def boulder(
        self,
        name: str,
        cx: float,
        cy: float,
        z0: float,
        sx: float,
        sy: float,
        sz: float,
        mat: bpy.types.Material,
        seed: float = 0.0,
    ) -> None:
        bm = bmesh.new()
        res = bmesh.ops.create_icosphere(
            bm,
            subdivisions=2,
            radius=1.0,
            matrix=Matrix.Translation((cx, cy, z0 + sz * 0.35)) @ Matrix.Diagonal((sx, sy, sz, 1.0)),
        )
        for v in res["verts"]:
            n = 1.0 + 0.18 * math.sin(v.co.x * 3.1 + seed) * math.cos(v.co.y * 2.7 - seed)
            v.co.x = cx + (v.co.x - cx) * n
            v.co.y = cy + (v.co.y - cy) * n
            v.co.z = max(z0 - 0.08, v.co.z)
        self._finish_bm(name, bm, mat, uv_proj="BOX", smooth=True)

    def park_bench(
        self,
        name: str,
        cx: float,
        cy: float,
        z0: float,
        yaw: float,
        wood_mat: bpy.types.Material,
        iron_mat: bpy.types.Material,
        length: float = 1.50,
    ) -> float:
        seat_z = z0 + 0.46
        hw = length * 0.5
        self.box(f"{name}_seat", cx - hw, cx + hw, cy - 0.22, cy + 0.22, seat_z - 0.045, seat_z, wood_mat, yaw=yaw)
        # Backrest offset in local +Y
        by_off = 0.20
        bx = cx - by_off * math.sin(yaw)
        by = cy + by_off * math.cos(yaw)
        self.box(f"{name}_back", bx - hw, bx + hw, by - 0.025, by + 0.025, seat_z + 0.12, seat_z + 0.44, wood_mat, yaw=yaw)
        for idx, lx in enumerate((-hw + 0.14, hw - 0.14)):
            px = cx + lx * math.cos(yaw)
            py = cy + lx * math.sin(yaw)
            self.box(f"{name}_leg_{idx}", px - 0.035, px + 0.035, py - 0.20, py + 0.20, z0, seat_z - 0.04, iron_mat, yaw=yaw)
        return seat_z

    def street_lamp(
        self,
        name: str,
        cx: float,
        cy: float,
        z0: float,
        iron_mat: bpy.types.Material,
        glow_mat: bpy.types.Material,
        height: float = 3.55,
    ) -> None:
        self.cylinder(f"{name}_ped", cx, cy, z0, z0 + 0.65, 0.14, 0.09, iron_mat, segs=10)
        self.cylinder(f"{name}_pole", cx, cy, z0 + 0.60, z0 + height, 0.065, 0.042, iron_mat, segs=10)
        self.cylinder(f"{name}_lan", cx, cy, z0 + height, z0 + height + 0.36, 0.12, 0.16, glow_mat, segs=8)
        self.cylinder(f"{name}_cap", cx, cy, z0 + height + 0.36, z0 + height + 0.48, 0.20, 0.03, iron_mat, segs=8)

    def gravestone(
        self,
        name: str,
        cx: float,
        cy: float,
        z0: float,
        yaw: float,
        mat: bpy.types.Material,
        style: int = 0,
    ) -> None:
        if style % 3 == 0:
            # Classic arched limestone headstone on plinth
            self.box(f"{name}_pl", cx - 0.36, cx + 0.36, cy - 0.14, cy + 0.14, z0 - 0.04, z0 + 0.14, mat, yaw=yaw)
            self.box(f"{name}_st", cx - 0.28, cx + 0.28, cy - 0.065, cy + 0.065, z0 + 0.14, z0 + 0.96, mat, yaw=yaw)
            self.box(f"{name}_cp", cx - 0.21, cx + 0.21, cy - 0.065, cy + 0.065, z0 + 0.96, z0 + 1.08, mat, yaw=yaw)
        elif style % 3 == 1:
            # Tapered memorial obelisk
            self.box(f"{name}_pl", cx - 0.30, cx + 0.30, cy - 0.30, cy + 0.30, z0 - 0.04, z0 + 0.28, mat, yaw=yaw)
            self.cylinder(f"{name}_ob", cx, cy, z0 + 0.28, z0 + 1.65, 0.18, 0.08, mat, segs=4, smooth=False)
            self.cylinder(f"{name}_tp", cx, cy, z0 + 1.65, z0 + 1.82, 0.08, 0.005, mat, segs=4, smooth=False)
        else:
            # Low ledger/tablet monument
            self.box(f"{name}_pl", cx - 0.42, cx + 0.42, cy - 0.16, cy + 0.16, z0 - 0.04, z0 + 0.12, mat, yaw=yaw)
            self.box(f"{name}_tb", cx - 0.35, cx + 0.35, cy - 0.08, cy + 0.08, z0 + 0.12, z0 + 0.72, mat, yaw=yaw)


def _extract_top_z(res: Any, fallback_z: float) -> float:
    objs: list[bpy.types.Object] = []
    if isinstance(res, bpy.types.Object):
        objs.append(res)
    elif isinstance(res, (list, tuple)):
        objs.extend(o for o in res if isinstance(o, bpy.types.Object))
    max_z = None
    for obj in objs:
        if obj.type == "MESH" and obj.bound_box:
            mw = obj.matrix_world
            for corner in obj.bound_box:
                wz = (mw @ Vector(corner)).z
                if max_z is None or wz > max_z:
                    max_z = wz
    return float(max_z) if max_z is not None else fallback_z


class PropPlacer:
    """Grounded, clearance-enforced Genie & optional asset placement manager."""

    def __init__(self, assets: Any, c: dict[str, Any], is_outdoor: bool) -> None:
        self.assets = assets
        self.is_outdoor = is_outdoor
        self.instances: list[dict[str, Any]] = []
        self._footprints: list[tuple[float, float, float, float]] = []  # (x, y, z, r)
        raw_furn = c.get("furnishing") or []
        self.preferred_genie: list[str] = []
        self.preferred_extra: list[str] = []
        for item in raw_furn:
            k = str(item or "").strip()
            if k in GENIE_KEYS_SET and k not in self.preferred_genie:
                if (not is_outdoor) or (k in OUTDOOR_SAFE_GENIE):
                    self.preferred_genie.append(k)
            elif k in EXTRA_KEYS_SET and k not in self.preferred_extra:
                self.preferred_extra.append(k)

    def _violates_protected(self, x: float, y: float, r: float) -> bool:
        # Block both the protected rectangle and the camera sightline corridor in -Y
        in_x = (x + r > -SAFE_X) and (x - r < SAFE_X)
        in_y = (y - r < SAFE_Y_MAX)
        return in_x and in_y

    def _push_safe(self, x: float, y: float, r: float) -> tuple[float, float]:
        if not self._violates_protected(x, y, r):
            return x, y
        # Prefer pushing into rear zone if y > 0.4, else push outside +/- SAFE_X
        if y >= 0.4:
            return x, max(y, SAFE_Y_MAX + r + 0.04)
        sign = 1.0 if x >= 0.0 else -1.0
        return sign * max(abs(x), SAFE_X + r + 0.05), y

    def _overlaps_existing(self, x: float, y: float, z: float, r: float) -> bool:
        for ox, oy, oz, orad in self._footprints:
            if abs(z - oz) < 0.35 and math.hypot(x - ox, y - oy) < (r + orad):
                return True
        return False

    def place(
        self,
        key: str,
        xyz: tuple[float, float, float],
        size: float | None = None,
        yaw: float = 0.0,
        radius: float = 0.24,
        support: str = "floor",
        allow_extra: bool = False,
    ) -> tuple[bool, float]:
        if key not in GENIE_KEYS_SET:
            if not (allow_extra and key in EXTRA_KEYS_SET):
                return (False, xyz[2])
        if self.is_outdoor and key in GENIE_KEYS_SET and key not in OUTDOOR_SAFE_GENIE:
            return (False, xyz[2])

        px, py = self._push_safe(float(xyz[0]), float(xyz[1]), radius)
        pz = float(xyz[2])

        # Nudge slightly if overlapping an existing prop at same height
        if self._overlaps_existing(px, py, pz, radius * 0.85):
            placed_clear = False
            for dx, dy in ((0.35, 0.0), (-0.35, 0.0), (0.0, 0.35), (0.55, 0.0), (-0.55, 0.0)):
                tx, ty = px + dx, py + dy
                if not self._violates_protected(tx, ty, radius) and not self._overlaps_existing(tx, ty, pz, radius * 0.85):
                    px, py = tx, ty
                    placed_clear = True
                    break
            if not placed_clear:
                return (False, pz)

        if self.assets is None or not hasattr(self.assets, "place"):
            return (False, pz)

        try:
            res = self.assets.place(
                key,
                (px, py, pz),
                size=None if size is None else float(size),
                yaw=float(yaw),
            )
        except Exception:
            return (False, pz)

        self._footprints.append((px, py, pz, radius))
        self.instances.append(
            {
                "key": key,
                "is_genie": key in GENIE_KEYS_SET,
                "xyz": [round(px, 4), round(py, 4), round(pz, 4)],
                "size": None if size is None else round(float(size), 4),
                "yaw": round(float(yaw), 4),
                "support": support,
            }
        )
        top_z = _extract_top_z(res, pz + (float(size) if size is not None else 0.74))
        return (True, top_z)

    def genie_count(self) -> int:
        return sum(1 for inst in self.instances if inst["is_genie"])

    def pick_from_pool(
        self,
        category_defaults: list[str],
        subset: frozenset[str],
        limit: int,
    ) -> list[str]:
        out: list[str] = []
        for k in self.preferred_genie:
            if k in subset and k not in out:
                out.append(k)
        for k in category_defaults:
            if k in subset and k not in out:
                out.append(k)
        return out[:limit]


# ---------------------------------------------------------------------------
# Outdoor Terrain & Subtype Dressers
# ---------------------------------------------------------------------------

def _make_terrain_fn(amp: float, freq: float, phase: float, slope_y: float = 0.0) -> Any:
    def _h(x: float, y: float) -> float:
        dx = max(0.0, abs(x) - 3.85)
        dy = max(0.0, y - 2.05) if y >= 0.0 else max(0.0, -2.25 - y)
        d = math.hypot(dx, dy)
        if d <= 1e-4:
            return GROUND_Z
        t = min(1.0, d / 3.6)
        mask = t * t * (3.0 - 2.0 * t)
        if y < 0.0:
            cam_clear = _clamp((abs(x) - 4.4) / 4.0, 0.0, 1.0)
            mask *= cam_clear
        waves = (
            0.55 * math.sin(x * freq + phase) * math.cos(y * freq * 0.85 - phase * 0.6)
            + 0.30 * math.sin((x + y) * freq * 1.7 + phase * 1.3)
            + 0.15 * math.cos(x * freq * 2.9 - y * freq * 2.1)
        )
        rise = max(0.0, y - 3.2) * slope_y
        return GROUND_Z + mask * (amp * (0.45 + 0.55 * waves) + rise)
    return _h


def _dress_outdoor_golf(
    b: EnvBuilder,
    mats: MatLib,
    placer: PropPlacer,
    c: dict[str, Any],
    wide: bool,
    rng: random.Random,
    seed: int,
) -> dict[str, Any]:
    floor_mat = mats.pbr_surface("floor", c.get("floor", ""), 2.2, "XY", (0.28, 0.44, 0.22))
    wall_mat = mats.pbr_surface("wall", c.get("wall", ""), 1.8, "XZ", (0.64, 0.60, 0.54))
    fairway_mat = mats.foliage("golf_fairway", (0.18, 0.38, 0.14), (0.29, 0.49, 0.19), roughness=0.84, subsurf=0.05)
    sand_mat = mats.stone("golf_bunker", (0.82, 0.75, 0.60), (0.74, 0.66, 0.52), roughness=0.92, scale=14.0, bump_strength=0.14)
    bark_mat = mats.wood("golf_bark", (0.18, 0.13, 0.09), (0.28, 0.21, 0.15), roughness=0.86, grain_axis="Z", coat=0.0)
    leaf_mat = mats.foliage("golf_leaf", (0.14, 0.30, 0.12), (0.28, 0.46, 0.18), roughness=0.52)
    white_wood = mats.paint("golf_fence", (0.90, 0.89, 0.85), roughness=0.52)
    iron_mat = mats.metal("golf_iron", (0.14, 0.16, 0.15), roughness=0.45)

    hfn = _make_terrain_fn(amp=0.65, freq=0.14, phase=(seed % 17) * 0.4, slope_y=0.035)
    b.ground_plane("golf_tee_pad", -4.4, 4.4, -3.2, 2.6, GROUND_Z, floor_mat)
    b.terrain_mesh("golf_course", -34.0, 34.0, -10.0, 44.0, 34, 30, hfn, fairway_mat)
    b.distant_ridge("golf_hills", -42.0, 42.0, 34.0, 18.0, 5.5, fairway_mat, phase=seed * 0.13)

    # Low stone tee-box/clubhouse border wall using c['wall']
    mirror = 1.0 if (seed & 1) == 0 else -1.0
    wx0, wx1 = sorted((mirror * 2.2, mirror * 7.4))
    b.box("golf_stone_wall", wx0, wx1, 3.8, 4.35, GROUND_Z - 0.1, GROUND_Z + 0.92, wall_mat, uv_proj="XZ")
    cap_mat = mats.stone("golf_cap", (0.72, 0.69, 0.63), (0.64, 0.60, 0.55), roughness=0.72)
    b.box("golf_wall_cap", wx0 - 0.05, wx1 + 0.05, 3.74, 4.41, GROUND_Z + 0.92, GROUND_Z + 1.00, cap_mat, uv_proj="XY")

    # Curved white course fence along rear-left flank
    for i in range(6):
        fx = -mirror * (2.6 + i * 1.45)
        fy = 4.4 + i * 0.35
        fz = hfn(fx, fy)
        b.box(f"golf_post_{i}", fx - 0.05, fx + 0.05, fy - 0.05, fy + 0.05, fz - 0.1, fz + 1.02, white_wood)
        if i < 5:
            nx = -mirror * (2.6 + (i + 1) * 1.45)
            ny = 4.4 + (i + 1) * 0.35
            yaw = math.atan2(ny - fy, nx - fx)
            mx, my = 0.5 * (fx + nx), 0.5 * (fy + ny)
            mz = hfn(mx, my)
            b.box(f"golf_rail_t_{i}", mx - 0.76, mx + 0.76, my - 0.025, my + 0.025, mz + 0.78, mz + 0.88, white_wood, yaw=yaw)
            b.box(f"golf_rail_b_{i}", mx - 0.76, mx + 0.76, my - 0.025, my + 0.025, mz + 0.42, mz + 0.52, white_wood, yaw=yaw)

    # Distant sand bunker & flagstick
    bx, by = -mirror * 3.8, 13.5
    b.boulder("golf_bunker_lip", bx, by, hfn(bx, by) - 0.12, 3.2, 1.9, 0.28, sand_mat, seed=1.2)
    flag_x, flag_y = mirror * 1.8, 19.5
    fz = hfn(flag_x, flag_y)
    b.cylinder("golf_pin", flag_x, flag_y, fz, fz + 2.35, 0.014, 0.012, white_wood, segs=8)
    flag_mat = mats.fabric("golf_flag", (0.82, 0.18, 0.14), roughness=0.72)
    b.box("golf_pennant", flag_x, flag_x + 0.52, flag_y - 0.01, flag_y + 0.01, fz + 1.92, fz + 2.28, flag_mat)

    # Parkland trees framing the fairway
    tree_spots = [
        (-8.2, 7.8, 6.2), (-12.5, 14.0, 7.4), (-6.4, 21.0, 6.8),
        (8.6, 8.2, 6.5), (12.8, 15.5, 7.2), (6.8, 23.0, 6.4),
    ]
    for i, (tx, ty, th) in enumerate(tree_spots):
        b.broadleaf_tree(f"golf_tree_{i}", tx, ty, hfn(tx, ty), th, bark_mat, leaf_mat)
    for i, (sx, sy) in enumerate(((-5.8, 4.6), (5.6, 4.9), (-9.2, 11.0), (9.4, 12.2))):
        b.shrub(f"golf_shrub_{i}", sx, sy, hfn(sx, sy), 0.72, leaf_mat)

    # Grounded Genie patio/tee props
    tx, ty = mirror * 4.35, 2.85
    tz = hfn(tx, ty)
    ok_t, top_z = placer.place("table", (tx, ty, tz), size=0.74, yaw=mirror * 0.18, radius=0.55, support="golf_ground")
    placer.place("chair", (tx - mirror * 0.78, ty + 0.12, hfn(tx - mirror * 0.78, ty + 0.12)), yaw=mirror * 1.1, radius=0.38, support="golf_ground")
    placer.place("bin", (mirror * 2.55, 3.35, hfn(mirror * 2.55, 3.35)), size=0.76, yaw=0.0, radius=0.32, support="golf_ground")
    if ok_t:
        placer.place("water", (tx - 0.14, ty - 0.06, top_z), size=None, yaw=0.3, radius=0.08, support="table")
        placer.place("cup", (tx + 0.15, ty + 0.08, top_z), size=None, yaw=-0.4, radius=0.08, support="table")
    else:
        bench_z = b.park_bench("golf_bench", -mirror * 4.2, 2.75, hfn(-mirror * 4.2, 2.75), -mirror * 0.35, white_wood, iron_mat)
        placer.place("water", (-mirror * 4.2, 2.75, bench_z), size=None, yaw=0.2, radius=0.08, support="golf_bench")

    return {"window_dirs": []}


def _dress_outdoor_ski(
    b: EnvBuilder,
    mats: MatLib,
    placer: PropPlacer,
    c: dict[str, Any],
    wide: bool,
    rng: random.Random,
    seed: int,
) -> dict[str, Any]:
    floor_mat = mats.pbr_surface("floor", c.get("floor", ""), 2.0, "XY", (0.85, 0.88, 0.92))
    wall_mat = mats.pbr_surface("wall", c.get("wall", ""), 1.8, "XZ", (0.46, 0.32, 0.20))
    snow_mat = mats.snow("ski_snow")
    rock_mat = mats.stone("ski_peak", (0.36, 0.39, 0.44), (0.68, 0.72, 0.78), roughness=0.78, scale=2.2, bump_strength=0.25)
    bark_mat = mats.wood("ski_bark", (0.16, 0.11, 0.08), (0.25, 0.18, 0.12), roughness=0.88, grain_axis="Z", coat=0.0)
    pine_mat = mats.foliage("ski_pine", (0.08, 0.18, 0.11), (0.14, 0.27, 0.17), roughness=0.62, subsurf=0.05)
    timber_mat = mats.wood("ski_timber", (0.28, 0.18, 0.11), (0.44, 0.30, 0.19), roughness=0.64)
    warm_win = mats.emissive("chalet_glow", (1.0, 0.74, 0.42), strength=3.2)
    orange_pole = mats.paint("piste_pole", (0.88, 0.34, 0.08), roughness=0.35)

    hfn = _make_terrain_fn(amp=0.85, freq=0.13, phase=(seed % 13) * 0.5, slope_y=0.075)
    b.ground_plane("ski_staging", -4.2, 4.2, -2.8, 2.5, GROUND_Z, floor_mat)
    b.terrain_mesh("ski_slope", -36.0, 36.0, -10.0, 44.0, 36, 30, hfn, snow_mat)
    b.distant_ridge("ski_peaks_far", -54.0, 54.0, 34.0, 22.0, 14.5, rock_mat, phase=seed * 0.21, jagged=True)
    b.distant_ridge("ski_peaks_snow", -48.0, 48.0, 28.0, 14.0, 8.2, snow_mat, phase=seed * 0.21 + 1.1, jagged=True)

    # Timber alpine lodge facade in background wing using c['wall']
    mirror = 1.0 if (seed & 1) == 0 else -1.0
    lx0, lx1 = sorted((mirror * 2.4, mirror * 7.8))
    b.box("chalet_wall", lx0, lx1, 5.2, 7.6, GROUND_Z - 0.2, GROUND_Z + 3.4, wall_mat, uv_proj="XZ")
    b.box("chalet_eave", lx0 - 0.45, lx1 + 0.45, 4.65, 8.0, GROUND_Z + 3.35, GROUND_Z + 3.65, timber_mat)
    b.box("chalet_snow_roof", lx0 - 0.42, lx1 + 0.42, 4.68, 7.98, GROUND_Z + 3.65, GROUND_Z + 3.85, snow_mat)
    # Warm glowing lodge window
    wcx = 0.5 * (lx0 + lx1)
    b.box("chalet_wframe", wcx - 0.95, wcx + 0.95, 5.12, 5.22, GROUND_Z + 1.15, GROUND_Z + 2.45, timber_mat)
    b.box("chalet_wglass", wcx - 0.85, wcx + 0.85, 5.15, 5.21, GROUND_Z + 1.25, GROUND_Z + 2.35, warm_win)

    # Wooden ski rack with colorful skis
    rx, ry = mirror * 3.85, 4.45
    rz = hfn(rx, ry)
    b.box("ski_rack_b", rx - 0.75, rx + 0.75, ry - 0.16, ry + 0.16, rz, rz + 0.08, timber_mat)
    b.box("ski_rack_r", rx - 0.75, rx + 0.75, ry - 0.04, ry + 0.04, rz + 0.95, rz + 1.03, timber_mat)
    for k, col in enumerate(((0.78, 0.16, 0.14), (0.14, 0.34, 0.68), (0.16, 0.52, 0.36))):
        sm = mats.paint(f"ski_pair_{k}", col, roughness=0.22, coat=0.65)
        sx = rx - 0.48 + k * 0.44
        b.box(f"ski_a_{k}", sx - 0.05, sx + 0.05, ry - 0.06, ry - 0.03, rz + 0.06, rz + 1.72, sm)
        b.box(f"ski_b_{k}", sx + 0.07, sx + 0.17, ry - 0.06, ry - 0.03, rz + 0.06, rz + 1.72, sm)

    # Piste boundary poles
    for i in range(4):
        px = -mirror * (4.4 + i * 2.2)
        py = 4.0 + i * 4.5
        pz = hfn(px, py)
        b.cylinder(f"piste_pole_{i}", px, py, pz - 0.1, pz + 1.75, 0.028, 0.025, orange_pole, segs=8)

    # Snow-dusted alpine conifers
    for i, (tx, ty, th) in enumerate((
        (-7.2, 6.2, 6.4), (-11.0, 12.5, 7.6), (-5.2, 16.5, 6.8),
        (9.2, 7.4, 6.8), (11.8, 14.5, 7.8), (4.6, 19.0, 6.5), (-1.8, 22.0, 7.2),
    )):
        b.conifer_tree(f"ski_pine_{i}", tx, ty, hfn(tx, ty), th, bark_mat, pine_mat, snow_mat=snow_mat)

    # Grounded Genie lodge terrace props
    tx, ty = mirror * 4.2, 3.1
    tz = hfn(tx, ty)
    ok_t, top_z = placer.place("table", (tx, ty, tz), size=0.75, yaw=-mirror * 0.25, radius=0.55, support="ski_deck")
    placer.place("chair", (tx - mirror * 0.78, ty + 0.08, hfn(tx - mirror * 0.78, ty + 0.08)), yaw=mirror * 1.15, radius=0.38, support="ski_deck")
    placer.place("carton", (-mirror * 4.1, 2.8, hfn(-mirror * 4.1, 2.8)), size=0.40, yaw=0.32, radius=0.34, support="ski_deck")
    placer.place("bin", (mirror * 2.15, 4.35, hfn(mirror * 2.15, 4.35)), size=0.78, yaw=0.0, radius=0.30, support="ski_deck")
    if ok_t:
        placer.place("mug", (tx - 0.12, ty, top_z), size=None, yaw=0.5, radius=0.08, support="table")
        placer.place("water", (tx + 0.16, ty + 0.06, top_z), size=None, yaw=-0.2, radius=0.08, support="table")

    return {"window_dirs": []}


def _dress_outdoor_ice(
    b: EnvBuilder,
    mats: MatLib,
    placer: PropPlacer,
    c: dict[str, Any],
    wide: bool,
    rng: random.Random,
    seed: int,
) -> dict[str, Any]:
    floor_mat = mats.pbr_surface("floor", c.get("floor", ""), 2.0, "XY", (0.74, 0.84, 0.90))
    wall_mat = mats.pbr_surface("wall", c.get("wall", ""), 1.8, "XZ", (0.84, 0.86, 0.88))
    snow_mat = mats.snow("ice_snow")
    ice_mat = mats.ice_surface("frozen_pond_ice")
    rock_mat = mats.stone("ice_rock", (0.32, 0.35, 0.39), (0.48, 0.51, 0.56), roughness=0.76)
    bark_mat = mats.wood("ice_bark", (0.20, 0.16, 0.13), (0.34, 0.28, 0.23), roughness=0.84, grain_axis="Z", coat=0.0)
    pine_mat = mats.foliage("ice_pine", (0.10, 0.20, 0.14), (0.16, 0.28, 0.20), roughness=0.64, subsurf=0.04)
    trim_red = mats.paint("rink_red", (0.72, 0.14, 0.14), roughness=0.38)
    wood_mat = mats.wood("ice_bench_wood", (0.32, 0.22, 0.14), (0.48, 0.34, 0.22), roughness=0.62)
    iron_mat = mats.metal("ice_iron", (0.16, 0.17, 0.19), roughness=0.46)

    is_rink = "rink" in str(c.get("room_note", "") + " " + c.get("title", "")).lower() or (seed % 2 == 0)
    hfn = _make_terrain_fn(amp=0.55, freq=0.16, phase=(seed % 11) * 0.6, slope_y=0.03)
    b.ground_plane("ice_active_floor", -4.6, 4.6, -3.5, 3.6, GROUND_Z, floor_mat)
    b.terrain_mesh("ice_bank_terrain", -34.0, 34.0, -10.0, 42.0, 34, 28, hfn, snow_mat)
    b.distant_ridge("ice_ridge", -44.0, 44.0, 32.0, 16.0, 6.2, snow_mat, phase=seed * 0.17)

    if is_rink:
        # Outdoor ice rink dasher boards using c['wall']
        b.box("rink_board_back", -5.2, 5.2, 3.65, 3.85, GROUND_Z, GROUND_Z + 1.15, wall_mat, uv_proj="XZ")
        b.box("rink_cap_back", -5.25, 5.25, 3.62, 3.88, GROUND_Z + 1.15, GROUND_Z + 1.21, trim_red, uv_proj="XY")
        b.box("rink_kick_back", -5.2, 5.2, 3.63, 3.66, GROUND_Z, GROUND_Z + 0.16, trim_red, uv_proj="XZ")
        # Side boards beyond +/- 4.8
        for side, sx in (("l", -5.05), ("r", 5.05)):
            b.box(f"rink_side_{side}", sx - 0.10, sx + 0.10, -2.5, 3.85, GROUND_Z, GROUND_Z + 1.15, wall_mat, uv_proj="YZ")
            b.box(f"rink_scap_{side}", sx - 0.13, sx + 0.13, -2.5, 3.88, GROUND_Z + 1.15, GROUND_Z + 1.21, trim_red, uv_proj="XY")
    else:
        # Frozen pond shoreline + timber warming shelter using c['wall']
        b.ground_plane("frozen_pond_far", -12.0, 12.0, 3.6, 16.0, GROUND_Z + 0.002, ice_mat)
        b.box("warm_hut_wall", 3.9, 7.6, 4.6, 6.8, GROUND_Z - 0.1, GROUND_Z + 2.8, wall_mat, uv_proj="XZ")
        b.box("warm_hut_roof", 3.6, 7.9, 4.2, 7.1, GROUND_Z + 2.8, GROUND_Z + 3.05, snow_mat)
        for i, (rx, ry, sc) in enumerate(((-4.8, 3.6, 0.8), (-6.2, 5.4, 1.1), (4.6, 3.5, 0.7), (7.4, 7.8, 1.0))):
            b.boulder(f"ice_rock_{i}", rx, ry, hfn(rx, ry), sc, sc * 0.8, sc * 0.55, rock_mat, seed=float(i))

    for i, (tx, ty, th) in enumerate((
        (-7.4, 6.4, 6.2), (-11.0, 11.8, 7.0), (-4.2, 15.2, 6.4),
        (7.8, 6.8, 6.5), (11.5, 13.0, 7.4), (3.4, 18.2, 6.6),
    )):
        b.conifer_tree(f"ice_tree_{i}", tx, ty, hfn(tx, ty), th, bark_mat, pine_mat, snow_mat=snow_mat)

    bench_z = b.park_bench("ice_bench", -4.15, 2.55, hfn(-4.15, 2.55), 0.35, wood_mat, iron_mat)
    placer.place("bin", (4.15, 2.65, hfn(4.15, 2.65)), size=0.76, yaw=-0.3, radius=0.30, support="ice_edge")
    placer.place("carton", (4.25, 1.65, hfn(4.25, 1.65)), size=0.38, yaw=0.22, radius=0.34, support="ice_edge")
    placer.place("chair", (-4.15, 1.35, hfn(-4.15, 1.35)), yaw=1.35, radius=0.38, support="ice_edge")
    placer.place("mug", (-4.35, 2.52, bench_z), size=None, yaw=0.4, radius=0.08, support="ice_bench")
    placer.place("water", (-3.95, 2.58, bench_z), size=None, yaw=-0.2, radius=0.08, support="ice_bench")

    return {"window_dirs": []}


def _dress_outdoor_sidewalk(
    b: EnvBuilder,
    mats: MatLib,
    placer: PropPlacer,
    c: dict[str, Any],
    wide: bool,
    rng: random.Random,
    seed: int,
) -> dict[str, Any]:
    floor_mat = mats.pbr_surface("floor", c.get("floor", ""), 1.8, "XY", (0.58, 0.57, 0.55))
    wall_mat = mats.pbr_surface("wall", c.get("wall", ""), 1.8, "XZ", (0.54, 0.36, 0.28))
    wall_mat_yz = mats.pbr_surface("side_wall", c.get("wall", ""), 1.8, "YZ", (0.54, 0.36, 0.28))
    asphalt = mats.stone("road_asphalt", (0.14, 0.14, 0.15), (0.20, 0.20, 0.22), roughness=0.86, scale=14.0, bump_strength=0.14)
    curb_mat = mats.stone("curb_stone", (0.64, 0.63, 0.60), (0.56, 0.55, 0.52), roughness=0.78)
    trim_mat = mats.metal("store_trim", (0.14, 0.15, 0.17), roughness=0.36)
    glass_mat = mats.glass("store_glass", (0.82, 0.90, 0.94), alpha=0.22, roughness=0.04)
    awning_cols = [(0.16, 0.34, 0.26), (0.52, 0.18, 0.16), (0.18, 0.26, 0.42), (0.46, 0.36, 0.22)]
    awning_mat = mats.fabric("store_awning", awning_cols[seed % len(awning_cols)], roughness=0.82)
    bark_mat = mats.wood("street_bark", (0.20, 0.15, 0.11), (0.30, 0.23, 0.17), roughness=0.86, grain_axis="Z", coat=0.0)
    leaf_mat = mats.foliage("street_leaf", (0.16, 0.34, 0.14), (0.30, 0.48, 0.20), roughness=0.52)
    lamp_glow = mats.emissive("street_lamp_glow", (1.0, 0.85, 0.62), strength=3.5)
    bench_wood = mats.wood("street_bench_wood", (0.28, 0.19, 0.12), (0.42, 0.30, 0.19), roughness=0.60)
    interior_warm = mats.paint("shop_interior", (0.58, 0.50, 0.42), roughness=0.75)

    # Paved sidewalk extending cleanly across workspace + road beyond wings/back
    b.ground_plane("sidewalk_pave", -16.0, 16.0, -9.0, 4.6, GROUND_Z, floor_mat)
    b.ground_plane("street_asphalt_bg", -26.0, 26.0, -14.0, 28.0, GROUND_Z - 0.14, asphalt)
    # Concrete curb along far wing or edge
    b.box("sidewalk_curb_l", -16.0, -5.2, -9.0, 4.6, GROUND_Z - 0.14, GROUND_Z, curb_mat, uv_proj="XY")

    # Storefront architectural facade along rear y = 4.2..4.6 (or 4.8 when wide)
    fy = 4.8 if wide else 4.25
    b.wall_x(
        "storefront_facade",
        -12.0,
        12.0,
        fy,
        0.38,
        GROUND_Z,
        GROUND_Z + 5.2,
        wall_mat,
        openings=[
            {"a0": -3.1, "a1": -0.5, "z0": 0.45, "z1": 2.75, "mx": 1, "mz": 1, "frame_mat": trim_mat},
            {"a0": 0.6, "a1": 3.2, "z0": 0.45, "z1": 2.75, "mx": 1, "mz": 1, "frame_mat": trim_mat},
            {"a0": -7.8, "a1": -5.2, "z0": 0.55, "z1": 2.65, "mx": 1, "mz": 1, "frame_mat": trim_mat},
            {"a0": 5.2, "a1": 7.8, "z0": 0.55, "z1": 2.65, "mx": 1, "mz": 1, "frame_mat": trim_mat},
        ],
        trim_mat=trim_mat,
        glass_mat=glass_mat,
        base_h=0.22,
        crown_h=0.22,
    )
    # Darkened interior shop backing behind windows so store looks inhabited, not hollow
    b.box("shop_backwall", -11.5, 11.5, fy + 1.8, fy + 2.0, GROUND_Z, GROUND_Z + 4.8, interior_warm, uv_proj="XZ")
    # Architectural pilasters & cornice molding
    for px in (-8.4, -4.0, 0.05, 4.1, 8.4):
        b.box(f"store_pil_{px:.1f}", px - 0.18, px + 0.18, fy - 0.12, fy + 0.05, GROUND_Z, GROUND_Z + 4.4, curb_mat, uv_proj="XZ")
    b.box("store_cornice", -12.1, 12.1, fy - 0.26, fy + 0.15, GROUND_Z + 3.20, GROUND_Z + 3.44, curb_mat, uv_proj="XZ")
    # Sloped fabric awnings over storefront bays
    for idx, (ax0, ax1) in enumerate(((-3.3, -0.3), (0.4, 3.4))):
        b.box(f"awning_top_{idx}", ax0, ax1, fy - 0.95, fy - 0.02, GROUND_Z + 2.78, GROUND_Z + 2.94, awning_mat)
        b.box(f"awning_val_{idx}", ax0, ax1, fy - 0.95, fy - 0.92, GROUND_Z + 2.58, GROUND_Z + 2.80, awning_mat)

    # Return side building wing wall far left/right
    b.box("side_bldg_l", -11.8, -11.2, -4.0, fy + 0.4, GROUND_Z, GROUND_Z + 5.2, wall_mat_yz, uv_proj="YZ")
    b.box("side_bldg_r", 11.2, 11.8, -4.0, fy + 0.4, GROUND_Z, GROUND_Z + 5.2, wall_mat_yz, uv_proj="YZ")

    # Street lamps, tree pits & sidewalk trees
    b.street_lamp("street_lamp_l", -4.45, 2.35, GROUND_Z, trim_mat, lamp_glow)
    b.street_lamp("street_lamp_r", 4.55, 2.45, GROUND_Z, trim_mat, lamp_glow)
    for i, (tx, ty) in enumerate(((-6.4, 2.1), (6.6, 2.2))):
        b.box(f"tree_grate_{i}", tx - 0.65, tx + 0.65, ty - 0.65, ty + 0.65, GROUND_Z, GROUND_Z + 0.025, trim_mat)
        b.broadleaf_tree(f"street_tree_{i}", tx, ty, GROUND_Z, 5.2, bark_mat, leaf_mat)

    # Sidewalk cafe furniture & Genie props
    bench_z = b.park_bench("sidewalk_bench", -1.8, fy - 0.72, GROUND_Z, 0.0, bench_wood, trim_mat, length=1.6)
    ok_t, top_z = placer.place("table", (2.05, fy - 1.15, GROUND_Z), size=0.74, yaw=0.08, radius=0.52, support="sidewalk")
    placer.place("chair", (1.28, fy - 1.15, GROUND_Z), yaw=1.45, radius=0.36, support="sidewalk")
    placer.place("chair", (2.82, fy - 1.12, GROUND_Z), yaw=-1.45, radius=0.36, support="sidewalk")
    placer.place("bin", (-3.85, fy - 0.85, GROUND_Z), size=0.82, yaw=0.0, radius=0.30, support="sidewalk")
    placer.place("carton", (4.15, fy - 0.95, GROUND_Z), size=0.38, yaw=-0.18, radius=0.34, support="sidewalk")
    if ok_t:
        placer.place("cup", (1.92, fy - 1.18, top_z), size=None, yaw=0.4, radius=0.08, support="table")
        placer.place("water", (2.18, fy - 1.08, top_z), size=None, yaw=-0.2, radius=0.08, support="table")
    placer.place("book", (-1.55, fy - 0.72, bench_z), size=None, yaw=0.25, radius=0.12, support="sidewalk_bench")
    placer.place("potted_plant", (0.05, fy - 0.55, GROUND_Z), size=1.18, yaw=0.3, radius=0.34, support="sidewalk", allow_extra=True)

    return {"window_dirs": []}


def _dress_outdoor_forest(
    b: EnvBuilder,
    mats: MatLib,
    placer: PropPlacer,
    c: dict[str, Any],
    wide: bool,
    rng: random.Random,
    seed: int,
) -> dict[str, Any]:
    floor_mat = mats.pbr_surface("floor", c.get("floor", ""), 2.2, "XY", (0.36, 0.30, 0.22))
    wall_mat = mats.pbr_surface("wall", c.get("wall", ""), 1.8, "XZ", (0.44, 0.41, 0.36))
    earth_mat = mats.foliage("forest_floor", (0.20, 0.26, 0.14), (0.32, 0.25, 0.16), roughness=0.92, subsurf=0.02)
    bark_mat = mats.wood("forest_bark", (0.16, 0.11, 0.08), (0.26, 0.19, 0.13), roughness=0.88, grain_axis="Z", coat=0.0)
    pine_mat = mats.foliage("forest_pine", (0.08, 0.21, 0.11), (0.16, 0.32, 0.16), roughness=0.58)
    leaf_mat = mats.foliage("forest_leaf", (0.14, 0.32, 0.13), (0.28, 0.46, 0.18), roughness=0.52)
    rock_mat = mats.stone("forest_rock", (0.34, 0.36, 0.32), (0.48, 0.50, 0.45), roughness=0.86, bump_strength=0.22)
    timber_mat = mats.wood("trail_timber", (0.26, 0.17, 0.10), (0.42, 0.29, 0.18), roughness=0.72, coat=0.0)
    iron_mat = mats.metal("trail_iron", (0.18, 0.17, 0.16), roughness=0.55)

    hfn = _make_terrain_fn(amp=0.82, freq=0.17, phase=(seed % 19) * 0.5, slope_y=0.035)
    b.ground_plane("trail_clearing", -4.2, 4.2, -3.0, 2.5, GROUND_Z, floor_mat)
    b.terrain_mesh("forest_terrain", -34.0, 34.0, -10.0, 42.0, 36, 30, hfn, earth_mat)
    b.distant_ridge("forest_ridge", -44.0, 44.0, 30.0, 18.0, 7.5, pine_mat, phase=seed * 0.23)

    # Low stone trailhead retaining wall & cedar timber rail using c['wall']
    mirror = 1.0 if (seed & 1) == 0 else -1.0
    wx0, wx1 = sorted((-mirror * 1.4, -mirror * 6.2))
    b.box("trail_stone_wall", wx0, wx1, 3.85, 4.35, GROUND_Z - 0.15, GROUND_Z + 0.85, wall_mat, uv_proj="XZ")
    # Split-rail trailhead fence on opposite flank
    for i in range(4):
        fx = mirror * (2.6 + i * 1.55)
        fy = 4.1 + i * 0.45
        fz = hfn(fx, fy)
        b.cylinder(f"trail_post_{i}", fx, fy, fz - 0.1, fz + 1.05, 0.065, 0.055, timber_mat, segs=7)
        if i < 3:
            nx = mirror * (2.6 + (i + 1) * 1.55)
            ny = 4.1 + (i + 1) * 0.45
            yaw = math.atan2(ny - fy, nx - fx)
            mx, my = 0.5 * (fx + nx), 0.5 * (fy + ny)
            mz = hfn(mx, my)
            b.box(f"trail_rail_a_{i}", mx - 0.80, mx + 0.80, my - 0.03, my + 0.03, mz + 0.72, mz + 0.82, timber_mat, yaw=yaw)
            b.box(f"trail_rail_b_{i}", mx - 0.80, mx + 0.80, my - 0.03, my + 0.03, mz + 0.36, mz + 0.46, timber_mat, yaw=yaw)

    # Mossy boulders & fallen weathered log
    for i, (rx, ry, sc) in enumerate(((-5.0, 3.1, 0.75), (5.2, 3.6, 0.90), (-2.8, 6.2, 0.85), (2.4, 7.8, 1.05))):
        b.boulder(f"forest_rock_{i}", rx, ry, hfn(rx, ry), sc, sc * 0.8, sc * 0.55, rock_mat, seed=float(i) * 1.7)

    # Layered mixed woodland canopy framing a sunlit glade
    conifers = [
        (-6.2, 5.2, 7.4), (-9.8, 8.6, 8.2), (-4.4, 11.4, 7.8), (-1.4, 15.8, 8.4),
        (6.4, 5.8, 7.6), (10.2, 9.5, 8.5), (4.8, 12.6, 7.5), (2.2, 16.8, 8.0),
    ]
    for i, (tx, ty, th) in enumerate(conifers):
        b.conifer_tree(f"forest_pine_{i}", tx, ty, hfn(tx, ty), th, bark_mat, pine_mat)
    broadleafs = [(-7.8, 13.5, 6.8), (7.6, 14.2, 7.0), (-11.5, 4.6, 6.2), (11.2, 5.0, 6.4)]
    for i, (tx, ty, th) in enumerate(broadleafs):
        b.broadleaf_tree(f"forest_oak_{i}", tx, ty, hfn(tx, ty), th, bark_mat, leaf_mat)
    for i, (sx, sy) in enumerate(((-4.5, 4.6), (4.6, 4.8), (-6.8, 3.4), (6.8, 3.6), (-0.8, 8.2), (1.8, 9.2))):
        b.shrub(f"forest_fern_{i}", sx, sy, hfn(sx, sy), 0.70, leaf_mat)

    # Trailhead Genie props (plausible picnic/camp gear)
    tx, ty = mirror * 4.25, 2.75
    tz = hfn(tx, ty)
    ok_t, top_z = placer.place("table", (tx, ty, tz), size=0.75, yaw=-mirror * 0.25, radius=0.55, support="trail_ground")
    placer.place("chair", (tx - mirror * 0.78, ty + 0.10, hfn(tx - mirror * 0.78, ty + 0.10)), yaw=mirror * 1.2, radius=0.38, support="trail_ground")
    placer.place("carton", (-mirror * 4.15, 2.55, hfn(-mirror * 4.15, 2.55)), size=0.42, yaw=0.28, radius=0.35, support="trail_ground")
    placer.place("bin", (-mirror * 2.25, 3.35, hfn(-mirror * 2.25, 3.35)), size=0.78, yaw=0.0, radius=0.32, support="trail_ground")
    if ok_t:
        placer.place("water", (tx - 0.15, ty - 0.05, top_z), size=None, yaw=0.3, radius=0.08, support="table")
        placer.place("mug", (tx + 0.16, ty + 0.06, top_z), size=None, yaw=-0.5, radius=0.08, support="table")
        placer.place("book", (tx + 0.02, ty - 0.16, top_z), size=None, yaw=0.2, radius=0.12, support="table")
    else:
        bz = b.park_bench("trail_bench", mirror * 4.25, 2.75, tz, -mirror * 0.3, timber_mat, iron_mat)
        placer.place("water", (mirror * 4.25, 2.75, bz), size=None, yaw=0.2, radius=0.08, support="trail_bench")

    return {"window_dirs": []}


def _dress_outdoor_garden(
    b: EnvBuilder,
    mats: MatLib,
    placer: PropPlacer,
    c: dict[str, Any],
    wide: bool,
    rng: random.Random,
    seed: int,
) -> dict[str, Any]:
    floor_mat = mats.pbr_surface("floor", c.get("floor", ""), 1.8, "XY", (0.62, 0.59, 0.54))
    wall_mat = mats.pbr_surface("wall", c.get("wall", ""), 1.8, "XZ", (0.66, 0.58, 0.50))
    lawn_mat = mats.foliage("garden_lawn", (0.17, 0.37, 0.14), (0.28, 0.48, 0.19), roughness=0.86, subsurf=0.04)
    hedge_mat = mats.foliage("garden_hedge", (0.11, 0.27, 0.11), (0.20, 0.38, 0.16), roughness=0.58)
    blossom_cols = [(0.62, 0.46, 0.72), (0.84, 0.62, 0.58), (0.88, 0.80, 0.62)]
    flower_mat = mats.foliage("garden_flowers", blossom_cols[seed % 3], (0.24, 0.42, 0.20), roughness=0.55)
    cedar_mat = mats.wood("pergola_cedar", (0.30, 0.19, 0.12), (0.46, 0.31, 0.20), roughness=0.62)
    bark_mat = mats.wood("garden_bark", (0.20, 0.14, 0.10), (0.30, 0.22, 0.16), roughness=0.86, grain_axis="Z", coat=0.0)
    coping_mat = mats.stone("garden_coping", (0.76, 0.73, 0.67), (0.68, 0.64, 0.58), roughness=0.68)

    hfn = _make_terrain_fn(amp=0.42, freq=0.16, phase=(seed % 15) * 0.4, slope_y=0.02)
    b.ground_plane("garden_terrace", -4.4, 4.4, -3.2, 3.0, GROUND_Z, floor_mat)
    b.terrain_mesh("garden_lawn_mesh", -32.0, 32.0, -10.0, 40.0, 32, 26, hfn, lawn_mat)
    b.distant_ridge("garden_hedgerow", -38.0, 38.0, 28.0, 14.0, 4.2, hedge_mat, phase=seed * 0.19)

    # Low limestone/brick garden boundary wall using c['wall'] + stone coping
    wy = 4.4 if wide else 3.8
    b.box("garden_wall_main", -7.5, 7.5, wy, wy + 0.36, GROUND_Z - 0.1, GROUND_Z + 1.38, wall_mat, uv_proj="XZ")
    b.box("garden_wall_cap", -7.6, 7.6, wy - 0.05, wy + 0.41, GROUND_Z + 1.38, GROUND_Z + 1.46, coping_mat, uv_proj="XY")
    # Decorative piers along the garden wall
    for px in (-6.0, -2.0, 2.0, 6.0):
        b.box(f"garden_pier_{px:.0f}", px - 0.24, px + 0.24, wy - 0.08, wy + 0.44, GROUND_Z - 0.1, GROUND_Z + 1.62, coping_mat)

    # Cedar garden pergola behind y = 2.45 (casts authentic dappled sunlight!)
    py0, py1 = wy - 1.35, wy + 0.15
    for px in (-3.2, 3.2):
        b.box(f"perg_post_f_{px:.0f}", px - 0.08, px + 0.08, py0 - 0.08, py0 + 0.08, GROUND_Z, GROUND_Z + 2.68, cedar_mat)
        b.box(f"perg_post_b_{px:.0f}", px - 0.08, px + 0.08, py1 - 0.08, py1 + 0.08, GROUND_Z, GROUND_Z + 2.68, cedar_mat)
    b.box("perg_beam_f", -3.6, 3.6, py0 - 0.06, py0 + 0.06, GROUND_Z + 2.62, GROUND_Z + 2.80, cedar_mat)
    b.box("perg_beam_b", -3.6, 3.6, py1 - 0.06, py1 + 0.06, GROUND_Z + 2.62, GROUND_Z + 2.80, cedar_mat)
    for i in range(9):
        rx = -3.2 + i * 0.80
        b.box(f"perg_raf_{i}", rx - 0.035, rx + 0.035, py0 - 0.22, py1 + 0.22, GROUND_Z + 2.80, GROUND_Z + 2.94, cedar_mat)

    # Raised stone planter beds & flowering shrubs
    b.box("planter_l", -5.8, -3.75, 1.4, 3.5, GROUND_Z, GROUND_Z + 0.46, coping_mat)
    b.box("planter_r", 3.75, 5.8, 1.4, 3.5, GROUND_Z, GROUND_Z + 0.46, coping_mat)
    for i, (sx, sy, sz) in enumerate((
        (-4.8, 2.0, GROUND_Z + 0.42), (-4.7, 3.0, GROUND_Z + 0.42),
        (4.8, 2.0, GROUND_Z + 0.42), (4.7, 3.0, GROUND_Z + 0.42),
        (-2.5, wy - 0.45, GROUND_Z), (2.5, wy - 0.45, GROUND_Z),
    )):
        b.shrub(f"garden_bush_{i}", sx, sy, sz, 0.56, flower_mat if (i % 2 == 0) else hedge_mat)

    for i, (tx, ty, th) in enumerate(((-6.8, 6.2, 5.8), (6.9, 6.5, 6.1), (-2.2, 9.8, 6.4), (3.4, 10.6, 5.9))):
        b.broadleaf_tree(f"garden_tree_{i}", tx, ty, hfn(tx, ty), th, bark_mat, hedge_mat)

    # Garden patio Genie props
    ok_t, top_z = placer.place("table", (0.0, wy - 0.95, GROUND_Z), size=0.74, yaw=0.0, radius=0.55, support="garden_terrace")
    placer.place("chair", (-0.88, wy - 0.92, GROUND_Z), yaw=1.32, radius=0.38, support="garden_terrace")
    placer.place("chair", (0.88, wy - 0.92, GROUND_Z), yaw=-1.32, radius=0.38, support="garden_terrace")
    placer.place("carton", (-4.1, 0.55, GROUND_Z), size=0.36, yaw=0.25, radius=0.34, support="garden_terrace")
    placer.place("bin", (4.1, 0.55, GROUND_Z), size=0.72, yaw=-0.2, radius=0.30, support="garden_terrace")
    if ok_t:
        placer.place("coffee_service", (-0.16, wy - 0.95, top_z), size=None, yaw=0.2, radius=0.14, support="table")
        placer.place("water", (0.20, wy - 0.90, top_z), size=None, yaw=-0.3, radius=0.08, support="table")
        placer.place("book", (0.04, wy - 1.08, top_z), size=None, yaw=0.4, radius=0.12, support="table")
    placer.place("potted_plant", (-3.55, wy - 0.55, GROUND_Z), size=1.15, yaw=0.4, radius=0.34, support="garden_terrace", allow_extra=True)
    placer.place("potted_fern", (3.55, wy - 0.55, GROUND_Z), size=0.85, yaw=-0.4, radius=0.32, support="garden_terrace", allow_extra=True)

    return {"window_dirs": []}


def _dress_outdoor_mountains(
    b: EnvBuilder,
    mats: MatLib,
    placer: PropPlacer,
    c: dict[str, Any],
    wide: bool,
    rng: random.Random,
    seed: int,
) -> dict[str, Any]:
    floor_mat = mats.pbr_surface("floor", c.get("floor", ""), 2.2, "XY", (0.48, 0.45, 0.40))
    wall_mat = mats.pbr_surface("wall", c.get("wall", ""), 1.8, "XZ", (0.44, 0.42, 0.39))
    ground_mat = mats.stone("mtn_ground", (0.36, 0.34, 0.28), (0.50, 0.46, 0.38), roughness=0.90, scale=6.0, bump_strength=0.22)
    cliff_mat = mats.stone("mtn_cliff", (0.30, 0.32, 0.36), (0.52, 0.50, 0.47), roughness=0.84, scale=2.4, bump_strength=0.28)
    far_mtn = mats.stone("mtn_far", (0.36, 0.42, 0.50), (0.54, 0.58, 0.64), roughness=0.86, scale=1.8, bump_strength=0.20)
    bark_mat = mats.wood("mtn_bark", (0.18, 0.12, 0.08), (0.28, 0.20, 0.14), roughness=0.88, grain_axis="Z", coat=0.0)
    pine_mat = mats.foliage("mtn_pine", (0.10, 0.22, 0.13), (0.18, 0.32, 0.18), roughness=0.62)
    timber_mat = mats.wood("mtn_rail", (0.30, 0.21, 0.14), (0.46, 0.33, 0.22), roughness=0.70, coat=0.0)
    iron_mat = mats.metal("mtn_iron", (0.18, 0.18, 0.19), roughness=0.52)

    hfn = _make_terrain_fn(amp=1.05, freq=0.14, phase=(seed % 17) * 0.55, slope_y=0.04)
    b.ground_plane("overlook_pad", -4.4, 4.4, -3.0, 3.3, GROUND_Z, floor_mat)
    b.terrain_mesh("mtn_terrain", -38.0, 38.0, -10.0, 44.0, 36, 30, hfn, ground_mat)
    b.distant_ridge("mtn_range_mid", -52.0, 52.0, 26.0, 16.0, 10.5, cliff_mat, phase=seed * 0.19, jagged=True)
    b.distant_ridge("mtn_range_far", -64.0, 64.0, 40.0, 22.0, 18.0, far_mtn, phase=seed * 0.19 + 1.8, jagged=True)

    # Low dry-stacked stone overlook parapet wall using c['wall']
    py = 3.85 if wide else 3.35
    b.box("overlook_wall", -6.2, 6.2, py, py + 0.45, GROUND_Z - 0.15, GROUND_Z + 0.88, wall_mat, uv_proj="XZ")
    b.box("overlook_cap", -6.28, 6.28, py - 0.04, py + 0.49, GROUND_Z + 0.88, GROUND_Z + 0.96, cliff_mat, uv_proj="XY")

    # Rugged granite boulders & hardy alpine pines on flanks
    for i, (rx, ry, sx, sy, sz) in enumerate((
        (-5.6, 2.4, 1.2, 0.9, 0.8), (5.8, 2.6, 1.3, 1.0, 0.9),
        (-8.2, 6.5, 1.8, 1.4, 1.3), (8.4, 7.2, 1.7, 1.3, 1.2),
        (-3.6, 9.2, 1.4, 1.1, 0.9), (4.2, 10.4, 1.5, 1.2, 1.0),
    )):
        b.boulder(f"mtn_rock_{i}", rx, ry, hfn(rx, ry), sx, sy, sz, cliff_mat, seed=float(i) * 2.1)

    for i, (tx, ty, th) in enumerate(((-7.5, 5.4, 5.8), (-11.0, 11.2, 6.8), (7.8, 5.8, 6.2), (11.4, 12.0, 7.2), (-5.2, 15.0, 6.0))):
        b.conifer_tree(f"mtn_pine_{i}", tx, ty, hfn(tx, ty), th, bark_mat, pine_mat)

    # Overlook bench & trailhead Genie props
    bench_z = b.park_bench("overlook_bench", -1.9, py - 0.55, GROUND_Z, 0.0, timber_mat, iron_mat)
    placer.place("bin", (2.6, py - 0.42, GROUND_Z), size=0.78, yaw=0.0, radius=0.30, support="overlook_pad")
    placer.place("carton", (-4.15, 2.25, GROUND_Z), size=0.40, yaw=0.22, radius=0.34, support="overlook_pad")
    placer.place("chair", (4.15, 2.45, GROUND_Z), yaw=-1.15, radius=0.38, support="overlook_pad")
    placer.place("water", (-1.55, py - 0.55, bench_z), size=None, yaw=0.2, radius=0.08, support="overlook_bench")
    placer.place("mug", (0.45, py + 0.22, GROUND_Z + 0.96), size=None, yaw=-0.3, radius=0.08, support="overlook_parapet")

    return {"window_dirs": []}


def _dress_outdoor_cemetery(
    b: EnvBuilder,
    mats: MatLib,
    placer: PropPlacer,
    c: dict[str, Any],
    wide: bool,
    rng: random.Random,
    seed: int,
) -> dict[str, Any]:
    floor_mat = mats.pbr_surface("floor", c.get("floor", ""), 2.0, "XY", (0.50, 0.49, 0.46))
    wall_mat = mats.pbr_surface("wall", c.get("wall", ""), 1.8, "XZ", (0.48, 0.47, 0.44))
    grass_mat = mats.foliage("cem_grass", (0.16, 0.28, 0.14), (0.24, 0.36, 0.18), roughness=0.88, subsurf=0.03)
    stone_a = mats.stone("cem_limestone", (0.64, 0.63, 0.59), (0.50, 0.51, 0.47), roughness=0.82, scale=4.2, bump_strength=0.18)
    stone_b = mats.stone("cem_granite", (0.40, 0.41, 0.43), (0.54, 0.55, 0.56), roughness=0.72, scale=5.5, bump_strength=0.14)
    iron_mat = mats.metal("cem_iron", (0.11, 0.12, 0.13), roughness=0.48)
    bark_mat = mats.wood("cem_bark", (0.18, 0.14, 0.11), (0.26, 0.21, 0.16), roughness=0.88, grain_axis="Z", coat=0.0)
    cypress_mat = mats.foliage("cem_cypress", (0.09, 0.19, 0.11), (0.14, 0.26, 0.15), roughness=0.60)
    oak_mat = mats.foliage("cem_oak", (0.14, 0.26, 0.13), (0.22, 0.36, 0.17), roughness=0.56)

    hfn = _make_terrain_fn(amp=0.45, freq=0.15, phase=(seed % 13) * 0.5, slope_y=0.025)
    b.ground_plane("cem_path", -4.0, 4.0, -3.2, 4.6, GROUND_Z, floor_mat)
    b.terrain_mesh("cem_grounds", -34.0, 34.0, -10.0, 42.0, 34, 28, hfn, grass_mat)
    b.distant_ridge("cem_trees_far", -42.0, 42.0, 30.0, 14.0, 5.2, oak_mat, phase=seed * 0.15)

    # Historic ashlar boundary wall + wrought-iron fence & stone gate piers using c['wall']
    wy = 5.4 if wide else 4.8
    for seg_i, (wx0, wx1) in enumerate(((-9.5, -1.6), (1.6, 9.5))):
        b.box(f"cem_wall_{seg_i}", wx0, wx1, wy, wy + 0.38, GROUND_Z - 0.1, GROUND_Z + 1.05, wall_mat, uv_proj="XZ")
        b.box(f"cem_cap_{seg_i}", wx0 - 0.04, wx1 + 0.04, wy - 0.04, wy + 0.42, GROUND_Z + 1.05, GROUND_Z + 1.12, stone_a, uv_proj="XY")
        # Wrought-iron railings atop low wall
        b.box(f"cem_rail_t_{seg_i}", wx0, wx1, wy + 0.17, wy + 0.21, GROUND_Z + 1.78, GROUND_Z + 1.82, iron_mat)
        n_pick = int((wx1 - wx0) / 0.36)
        for p in range(n_pick + 1):
            px = wx0 + p * 0.36
            b.box(f"cem_pk_{seg_i}_{p}", px - 0.012, px + 0.012, wy + 0.175, wy + 0.205, GROUND_Z + 1.12, GROUND_Z + 1.90, iron_mat)
    for px in (-1.65, 1.65, -6.2, 6.2):
        b.box(f"cem_pier_{px:.1f}", px - 0.28, px + 0.28, wy - 0.08, wy + 0.46, GROUND_Z - 0.1, GROUND_Z + 2.18, stone_a)
        b.box(f"cem_pcap_{px:.1f}", px - 0.34, px + 0.34, wy - 0.14, wy + 0.52, GROUND_Z + 2.18, GROUND_Z + 2.30, stone_a)

    # Tasteful sculpted limestone/granite headstones & monuments beyond y > 2.5 and |x| > 3.9
    monuments = [
        (-5.0, 2.7, 0.08, 0), (-6.6, 3.3, -0.05, 1), (-4.4, 7.2, 0.04, 2), (-2.4, 8.6, 0.0, 0),
        (5.0, 2.8, -0.06, 2), (6.8, 3.4, 0.05, 0), (4.6, 7.5, -0.04, 1), (2.5, 9.0, 0.02, 0),
        (-0.8, 10.5, 0.0, 1), (1.4, 12.0, -0.03, 0), (-5.8, 11.2, 0.06, 2), (6.0, 11.6, -0.05, 0),
    ]
    for i, (mx, my, yaw, st) in enumerate(monuments):
        b.gravestone(f"cem_mon_{i}", mx, my, hfn(mx, my), yaw, stone_a if (i % 2 == 0) else stone_b, style=st)

    # Tall cypress & mature broadleaf churchyard trees
    for i, (tx, ty, th) in enumerate(((-7.8, 6.4, 7.2), (7.6, 6.2, 7.4), (-3.8, 13.5, 7.8), (4.2, 14.0, 7.6))):
        b.conifer_tree(f"cem_cyp_{i}", tx, ty, hfn(tx, ty), th, bark_mat, cypress_mat)
    for i, (tx, ty, th) in enumerate(((-10.5, 10.2, 7.5), (10.8, 9.8, 7.8))):
        b.broadleaf_tree(f"cem_oak_{i}", tx, ty, hfn(tx, ty), th, bark_mat, oak_mat)

    # Carved stone memorial bench + discreet grounded Genie props
    bench_x, bench_y = -2.75, wy - 0.85
    b.box("cem_bench_l", bench_x - 0.58, bench_x - 0.44, bench_y - 0.22, bench_y + 0.22, GROUND_Z, GROUND_Z + 0.44, stone_a)
    b.box("cem_bench_r", bench_x + 0.44, bench_x + 0.58, bench_y - 0.22, bench_y + 0.22, GROUND_Z, GROUND_Z + 0.44, stone_a)
    b.box("cem_bench_top", bench_x - 0.72, bench_x + 0.72, bench_y - 0.25, bench_y + 0.25, GROUND_Z + 0.44, GROUND_Z + 0.52, stone_a, uv_proj="XY")

    placer.place("bin", (2.65, wy - 0.65, GROUND_Z), size=0.76, yaw=0.0, radius=0.30, support="cem_path")
    placer.place("chair", (3.85, wy - 0.95, GROUND_Z), yaw=-0.55, radius=0.38, support="cem_path")
    placer.place("water", (bench_x + 0.30, bench_y, GROUND_Z + 0.52), size=None, yaw=0.2, radius=0.08, support="stone_bench")
    placer.place("book", (bench_x - 0.26, bench_y, GROUND_Z + 0.52), size=None, yaw=-0.25, radius=0.12, support="stone_bench")
    placer.place("potted_fern", (-1.65, wy - 0.52, GROUND_Z), size=0.80, yaw=0.2, radius=0.30, support="cem_path", allow_extra=True)

    return {"window_dirs": []}


# ---------------------------------------------------------------------------
# Indoor Architectural Shell Helper & Category Dressers
# ---------------------------------------------------------------------------

def _room_dims(wide: bool, min_rear_y: float = 3.45, ceil_h: float = 3.40) -> tuple[float, float, float, float]:
    half_w = 5.65 if wide else 4.70
    rear_y = max(min_rear_y, 4.35 if wide else 3.45)
    front_y = -9.2 if wide else -6.8
    ch = ceil_h + (0.30 if wide else 0.0)
    return half_w, rear_y, front_y, ch


def _build_shell(
    b: EnvBuilder,
    mats: MatLib,
    c: dict[str, Any],
    half_w: float,
    rear_y: float,
    front_y: float,
    ceil_h: float,
    rear_openings: list[dict[str, Any]] | None = None,
    left_openings: list[dict[str, Any]] | None = None,
    right_openings: list[dict[str, Any]] | None = None,
    trim_mat: bpy.types.Material | None = None,
    glass_mat: bpy.types.Material | None = None,
    ceil_mat: bpy.types.Material | None = None,
    floor_tile_m: float = 1.8,
    wall_tile_m: float = 1.8,
    base_h: float = 0.11,
    crown_h: float = 0.08,
) -> dict[str, Any]:
    floor_mat = mats.pbr_surface("floor", c.get("floor", ""), floor_tile_m, "XY", (0.48, 0.42, 0.36))
    wall_xz = mats.pbr_surface("rear_wall", c.get("wall", ""), wall_tile_m, "XZ", (0.78, 0.76, 0.72))
    wall_yz = mats.pbr_surface("side_wall", c.get("wall", ""), wall_tile_m, "YZ", (0.78, 0.76, 0.72))
    if trim_mat is None:
        trim_mat = mats.paint("room_trim", (0.90, 0.89, 0.86), roughness=0.40)
    if glass_mat is None:
        glass_mat = mats.glass("room_glass")
    if ceil_mat is None:
        ceil_mat = mats.paint("room_ceiling", (0.92, 0.91, 0.89), roughness=0.76)

    b.ground_plane("room_floor", -half_w - 0.3, half_w + 0.3, front_y, rear_y + 0.3, GROUND_Z, floor_mat)
    # Ceiling slab high above workspace (no obstruction to camera)
    b.box("room_ceiling", -half_w - 0.3, half_w + 0.3, front_y, rear_y + 0.3, ceil_h, ceil_h + 0.16, ceil_mat, uv_proj="XY")

    b.wall_x(
        "rear_wall",
        -half_w,
        half_w,
        rear_y,
        0.24,
        GROUND_Z,
        ceil_h,
        wall_xz,
        openings=rear_openings,
        trim_mat=trim_mat,
        glass_mat=glass_mat,
        base_h=base_h,
        crown_h=crown_h,
    )
    b.wall_y(
        "left_wall",
        front_y,
        rear_y + 0.24,
        -half_w,
        0.24,
        -1,
        GROUND_Z,
        ceil_h,
        wall_yz,
        openings=left_openings,
        trim_mat=trim_mat,
        glass_mat=glass_mat,
        base_h=base_h,
        crown_h=crown_h,
    )
    b.wall_y(
        "right_wall",
        front_y,
        rear_y + 0.24,
        half_w,
        0.24,
        +1,
        GROUND_Z,
        ceil_h,
        wall_yz,
        openings=right_openings,
        trim_mat=trim_mat,
        glass_mat=glass_mat,
        base_h=base_h,
        crown_h=crown_h,
    )

    win_hints: list[dict[str, Any]] = []
    for op in rear_openings or []:
        if op.get("kind", "window") == "window":
            win_hints.append(
                {
                    "pos": (0.5 * (op["a0"] + op["a1"]), rear_y - 0.18, 0.5 * (op["z0"] + op["z1"])),
                    "size_x": abs(op["a1"] - op["a0"]),
                    "size_y": abs(op["z1"] - op["z0"]),
                    "wall": "rear",
                }
            )
    for op in left_openings or []:
        if op.get("kind", "window") == "window":
            win_hints.append(
                {
                    "pos": (-half_w + 0.18, 0.5 * (op["a0"] + op["a1"]), 0.5 * (op["z0"] + op["z1"])),
                    "size_x": abs(op["a1"] - op["a0"]),
                    "size_y": abs(op["z1"] - op["z0"]),
                    "wall": "left",
                }
            )
    for op in right_openings or []:
        if op.get("kind", "window") == "window":
            win_hints.append(
                {
                    "pos": (half_w - 0.18, 0.5 * (op["a0"] + op["a1"]), 0.5 * (op["z0"] + op["z1"])),
                    "size_x": abs(op["a1"] - op["a0"]),
                    "size_y": abs(op["z1"] - op["z0"]),
                    "wall": "right",
                }
            )

    return {"window_hints": win_hints, "half_w": half_w, "rear_y": rear_y, "ceil_h": ceil_h}


def _dress_kitchen(
    b: EnvBuilder,
    mats: MatLib,
    placer: PropPlacer,
    c: dict[str, Any],
    wide: bool,
    rng: random.Random,
    seed: int,
) -> dict[str, Any]:
    variant = seed % 5
    mirror = -1.0 if ((seed >> 3) & 1) else 1.0
    half_w, rear_y, front_y, ceil_h = _room_dims(wide, min_rear_y=3.45, ceil_h=3.30)

    # Distinct art-directed palettes per variant
    palettes = [
        # 0: Sage shaker + warm oak + cream subway tile + brass
        ((0.46, 0.53, 0.45), (0.52, 0.36, 0.22), (0.91, 0.89, 0.84), (0.76, 0.60, 0.30)),
        # 1: Charcoal matte + walnut shelves + glazed zellige ivory + stainless
        ((0.18, 0.19, 0.21), (0.30, 0.19, 0.12), (0.86, 0.84, 0.78), (0.74, 0.76, 0.78)),
        # 2: Warm walnut fluted + dark soapstone + cream stone + antique brass
        ((0.34, 0.22, 0.14), (0.20, 0.21, 0.23), (0.82, 0.79, 0.73), (0.72, 0.56, 0.28)),
        # 3: Deep slate-blue bistro + Carrara marble + terracotta-cream tile + chrome
        ((0.20, 0.30, 0.36), (0.86, 0.85, 0.83), (0.76, 0.58, 0.46), (0.80, 0.82, 0.84)),
        # 4: Warm putty/greige L-kitchen + honed granite + seafoam tile + matte black
        ((0.58, 0.55, 0.49), (0.34, 0.33, 0.32), (0.68, 0.76, 0.73), (0.16, 0.16, 0.17)),
    ]
    cab_rgb, top_rgb, tile_rgb, met_rgb = palettes[variant]
    cab_mat = (
        mats.wood("kit_cab_wood", (cab_rgb[0] * 0.72, cab_rgb[1] * 0.72, cab_rgb[2] * 0.72), cab_rgb, roughness=0.40, grain_axis="Z")
        if variant == 2
        else mats.paint("kit_cab_paint", cab_rgb, roughness=0.38, coat=0.12)
    )
    top_mat = (
        mats.wood("kit_butcher", (0.38, 0.25, 0.14), (0.58, 0.41, 0.24), roughness=0.34)
        if variant == 0
        else mats.stone("kit_counter", top_rgb, (top_rgb[0] * 0.84, top_rgb[1] * 0.85, top_rgb[2] * 0.87), roughness=0.22, coat=0.25)
    )
    tile_mat = mats.tile(
        "kit_backsplash",
        tile_rgb,
        (tile_rgb[0] * 0.92, tile_rgb[1] * 0.92, tile_rgb[2] * 0.92),
        scale=6.0 if variant != 1 else 8.0,
        brick_w=0.42 if variant != 1 else 0.24,
        row_h=0.18 if variant != 1 else 0.24,
    )
    metal_mat = mats.metal("kit_metal", met_rgb, roughness=0.22)
    shelf_wood = mats.wood("kit_shelf_wood", (0.28, 0.18, 0.11), (0.48, 0.33, 0.20), roughness=0.36)
    trim_mat = mats.paint("kit_trim", (0.91, 0.90, 0.87), roughness=0.38)
    glass_mat = mats.glass("kit_glass")
    glow_mat = mats.emissive("kit_pendant_glow", (1.0, 0.88, 0.70), strength=4.5)
    shade_mat = mats.metal("kit_shade", met_rgb, roughness=0.26)

    # Configure window openings per kitchen variant
    rear_ops: list[dict[str, Any]] = []
    left_ops: list[dict[str, Any]] = []
    right_ops: list[dict[str, Any]] = []
    if variant == 0:
        rear_ops = [{"a0": -1.05, "a1": 1.05, "z0": 1.15, "z1": 2.38, "mx": 2, "mz": 1}]
    elif variant == 1:
        side_op = [{"a0": -0.2, "a1": 2.1, "z0": 0.98, "z1": 2.48, "my": 2, "mz": 1}]
        if mirror > 0:
            left_ops = side_op
        else:
            right_ops = side_op
    elif variant == 2:
        rear_ops = [{"a0": -2.4, "a1": 2.4, "z0": 2.25, "z1": 2.86, "mx": 3, "mz": 0}]
    elif variant == 3:
        wx0, wx1 = sorted((mirror * 0.75, mirror * 2.25))
        rear_ops = [{"a0": wx0, "a1": wx1, "z0": 1.02, "z1": 2.58, "mx": 1, "mz": 2}]
    else:
        wx0, wx1 = sorted((-mirror * 1.9, -mirror * 0.2))
        rear_ops = [{"a0": wx0, "a1": wx1, "z0": 1.12, "z1": 2.40, "mx": 1, "mz": 1}]
        side_op = [{"a0": 0.5, "a1": 2.5, "z0": 1.12, "z1": 2.40, "my": 1, "mz": 1}]
        if mirror > 0:
            right_ops = side_op
        else:
            left_ops = side_op

    shell = _build_shell(
        b, mats, c, half_w, rear_y, front_y, ceil_h,
        rear_openings=rear_ops, left_openings=left_ops, right_openings=right_ops,
        trim_mat=trim_mat, glass_mat=glass_mat, floor_tile_m=1.5, wall_tile_m=1.6,
    )

    # Rear counter run + backsplash + uppers/shelves/hood per variant
    cd = 0.65
    y_front = rear_y - cd
    counter_y_mid = rear_y - cd * 0.5
    fridge_x = mirror * -2.95
    run_x0, run_x1 = (-2.25, 3.25) if mirror > 0 else (-3.25, 2.25)
    top_z = b.base_cabinet_run(
        "kit_base", run_x0, run_x1, rear_y, cd, 0.90, cab_mat, top_mat, metal_mat, doors=6, shaker=(variant != 2)
    )
    # Recessed tiled backsplash
    bs_top = 3.10 if variant == 1 else 1.56
    b.box("kit_bsplash", run_x0, run_x1, rear_y - 0.022, rear_y, top_z, bs_top, tile_mat, uv_proj="XZ")

    # Under-cabinet warm task LED strip
    b.box("kit_led_strip", run_x0 + 0.25, run_x1 - 0.25, rear_y - 0.26, rear_y - 0.22, 1.48, 1.50, glow_mat)

    shelf_spots: list[tuple[float, float, float, str]] = []
    if variant == 0:
        b.sink_and_faucet("kit_sink", 0.0, counter_y_mid, top_z, metal_mat)
        b.upper_cabinet_run("kit_up_l", run_x0, -1.18, rear_y, 0.34, 1.50, 2.52, cab_mat, metal_mat, doors=2)
        b.upper_cabinet_run("kit_up_r", 1.18, run_x1, rear_y, 0.34, 1.50, 2.52, cab_mat, metal_mat, doors=3)
        shelf_spots.extend([(-1.7, counter_y_mid, top_z, "counter"), (1.65, counter_y_mid, top_z, "counter"), (2.55, counter_y_mid, top_z, "counter")])
    elif variant == 1:
        hood_mat = mats.metal("kit_hood_steel", (0.70, 0.72, 0.75), roughness=0.26)
        b.range_hood("kit_hood", 0.0, rear_y, 1.66, ceil_h, 0.96, hood_mat)
        cook_mat = mats.metal("cooktop_glass", (0.06, 0.06, 0.07), roughness=0.10, metallic=0.2)
        b.box("kit_cooktop", -0.42, 0.42, counter_y_mid - 0.22, counter_y_mid + 0.22, top_z, top_z + 0.015, cook_mat)
        s1_z = b.floating_shelf("kit_sh_l1", run_x0 + 0.10, -0.68, rear_y, 0.28, 1.52, shelf_wood, metal_mat)
        s2_z = b.floating_shelf("kit_sh_l2", run_x0 + 0.10, -0.68, rear_y, 0.28, 1.98, shelf_wood, metal_mat)
        s3_z = b.floating_shelf("kit_sh_r1", 0.68, run_x1 - 0.10, rear_y, 0.28, 1.52, shelf_wood, metal_mat)
        b.floating_shelf("kit_sh_r2", 0.68, run_x1 - 0.10, rear_y, 0.28, 1.98, shelf_wood, metal_mat)
        shelf_spots.extend([
            (-1.55, rear_y - 0.15, s1_z, "open_shelf"),
            (1.45, rear_y - 0.15, s3_z, "open_shelf"),
            (-1.45, rear_y - 0.15, s2_z, "open_shelf"),
            (1.85, counter_y_mid, top_z, "counter"),
            (-1.65, counter_y_mid, top_z, "counter"),
        ])
    elif variant == 2:
        # Coffee-bar tall pantry framing + pendants under clerestory
        px0, px1 = (2.15, 3.25) if mirror > 0 else (-3.25, -2.15)
        b.box("kit_pantry_l", px0, px0 + 0.06, rear_y - 0.62, rear_y, GROUND_Z, 2.55, cab_mat)
        b.box("kit_pantry_r", px1 - 0.06, px1, rear_y - 0.62, rear_y, GROUND_Z, 2.55, cab_mat)
        b.box("kit_pantry_t", px0, px1, rear_y - 0.62, rear_y, 2.02, 2.55, cab_mat)
        b.floating_shelf("kit_niche_sh", px0 + 0.06, px1 - 0.06, rear_y, 0.30, 1.56, shelf_wood, metal_mat)
        b.sink_and_faucet("kit_sink", -mirror * 0.55, counter_y_mid, top_z, metal_mat)
        for idx, lx in enumerate((-1.35, 0.0, 1.35)):
            b.pendant_lamp(f"kit_pend_{idx}", lx, y_front - 0.05, ceil_h, 2.28, shade_mat, glow_mat, radius=0.11)
        ncx = 0.5 * (px0 + px1)
        shelf_spots.extend([(ncx, counter_y_mid, top_z, "coffee_niche"), (ncx, rear_y - 0.16, 1.56, "niche_shelf"), (mirror * 0.75, counter_y_mid, top_z, "counter")])
    elif variant == 3:
        wx0, wx1 = sorted((mirror * 0.75, mirror * 2.25))
        b.sink_and_faucet("kit_sink", 0.5 * (wx0 + wx1), counter_y_mid, top_z, metal_mat)
        ux0, ux1 = (-2.15, 0.45) if mirror > 0 else (-0.45, 2.15)
        b.upper_cabinet_run("kit_glass_up", ux0, ux1, rear_y, 0.34, 1.52, 2.58, cab_mat, metal_mat, doors=4, glass_mat=glass_mat)
        shelf_spots.extend([(-mirror * 1.15, counter_y_mid, top_z, "counter"), (-mirror * 0.35, counter_y_mid, top_z, "counter"), (0.5 * (wx0 + wx1) + 0.55, counter_y_mid, top_z, "counter")])
    else:
        # Variant 4: L-return counter along side wall (strictly |x| >= half_w - 0.65 > 3.9 > 3.4)
        hood_mat = mats.metal("kit_hood_blk", (0.14, 0.15, 0.16), roughness=0.35)
        b.range_hood("kit_hood", mirror * 1.15, rear_y, 1.66, ceil_h, 0.90, hood_mat)
        sh_z = b.floating_shelf("kit_l_sh", mirror * 1.95, mirror * 3.15 if mirror > 0 else -1.95, rear_y, 0.28, 1.58, shelf_wood, metal_mat)
        sx_in = mirror * (half_w - 0.65)
        sx0, sx1 = sorted((sx_in, mirror * half_w))
        b.box("kit_l_ret_base", sx0, sx1, 0.25, rear_y - cd, GROUND_Z, top_z - 0.036, cab_mat)
        b.box("kit_l_ret_top", sx0 - 0.02, sx1 + 0.02, 0.22, rear_y - cd, top_z - 0.036, top_z, top_mat, uv_proj="XY")
        shelf_spots.extend([(mirror * 2.45, rear_y - 0.15, sh_z, "open_shelf"), (-mirror * 1.25, counter_y_mid, top_z, "counter"), (mirror * (half_w - 0.34), 1.35, top_z, "l_counter")])

    # Refrigerator alcove framing + Genie refrigerator
    b.box("kit_fridge_hdr", fridge_x - 0.48, fridge_x + 0.48, rear_y - 0.72, rear_y, 2.02, 2.58, cab_mat)
    placer.place("refrigerator", (fridge_x, rear_y - 0.44, GROUND_Z), size=1.86, yaw=0.0, radius=0.45, support="floor")

    # Side wing breakfast / pantry furniture strictly outside |x| > 3.65
    wing_x = mirror * (half_w - 0.72) if variant != 4 else -mirror * (half_w - 0.72)
    wing_ok, wing_top = placer.place("sideboard", (wing_x, 1.55, GROUND_Z), size=0.82, yaw=-mirror * math.pi * 0.5, radius=0.48, support="floor")
    placer.place("chair", (wing_x - mirror * 0.10, 0.15, GROUND_Z), yaw=-mirror * 1.15, radius=0.38, support="floor")
    placer.place("bin", (-mirror * (half_w - 0.55), rear_y - 0.55, GROUND_Z), size=0.52, yaw=0.0, radius=0.28, support="floor")
    if wing_ok:
        shelf_spots.append((wing_x, 1.55, wing_top, "sideboard"))

    # Place countertop & shelf Genie props from c['furnishing'] + kitchen defaults
    kit_props = placer.pick_from_pool(
        ["coffee_service", "mug", "cup", "water", "soap", "book", "photo_books"],
        TABLETOP_GENIE,
        limit=min(5, len(shelf_spots)),
    )
    for (sx, sy, sz, sup), prop_key in zip(shelf_spots, kit_props):
        placer.place(prop_key, (sx, sy, sz), size=None, yaw=rng.uniform(-0.4, 0.4), radius=0.14, support=sup)

    # Optional potted herb/plant in free corner
    placer.place("potted_plant", (-mirror * (half_w - 0.58), 2.15, GROUND_Z), size=1.10, yaw=0.3, radius=0.34, support="floor", allow_extra=True)
    return shell


def _dress_bathroom(
    b: EnvBuilder,
    mats: MatLib,
    placer: PropPlacer,
    c: dict[str, Any],
    wide: bool,
    rng: random.Random,
    seed: int,
) -> dict[str, Any]:
    variant = seed % 3
    mirror = -1.0 if ((seed >> 2) & 1) else 1.0
    half_w, rear_y, front_y, ceil_h = _room_dims(wide, min_rear_y=3.35, ceil_h=3.15)

    palettes = [
        ((0.86, 0.85, 0.82), (0.34, 0.23, 0.15), (0.76, 0.62, 0.34)),  # warm marble + walnut + brass
        ((0.76, 0.82, 0.80), (0.28, 0.36, 0.35), (0.80, 0.82, 0.85)),  # spa sage tile + chrome
        ((0.82, 0.80, 0.76), (0.22, 0.22, 0.23), (0.16, 0.16, 0.18)),  # limestone + matte black
    ]
    tile_rgb, van_rgb, met_rgb = palettes[variant]
    tile_mat = mats.tile("bath_tile", tile_rgb, (tile_rgb[0] * 0.93, tile_rgb[1] * 0.93, tile_rgb[2] * 0.94), scale=5.0, brick_w=0.38, row_h=0.22)
    van_mat = (
        mats.wood("bath_van_wood", (0.24, 0.16, 0.10), van_rgb, roughness=0.40)
        if variant == 0
        else mats.paint("bath_van_paint", van_rgb, roughness=0.38)
    )
    stone_top = mats.stone("bath_top", (0.90, 0.89, 0.87), (0.78, 0.78, 0.80), roughness=0.18, coat=0.35)
    metal_mat = mats.metal("bath_metal", met_rgb, roughness=0.18)
    trim_mat = mats.paint("bath_trim", (0.92, 0.92, 0.90), roughness=0.36)
    frosted = mats.glass("bath_frost", (0.88, 0.93, 0.95), alpha=0.28, roughness=0.26)
    clear_gl = mats.glass("bath_shower_glass", (0.86, 0.94, 0.96), alpha=0.15, roughness=0.03)
    sconce_glow = mats.emissive("bath_sconce_glow", (1.0, 0.90, 0.76), strength=5.0)
    mirror_mat = mats.mirror("bath_mirror")
    towel_mat = mats.fabric("bath_towel", (0.88, 0.86, 0.82), roughness=0.90)

    wx0, wx1 = sorted((mirror * 1.45, mirror * 2.85))
    rear_ops = [{"a0": wx0, "a1": wx1, "z0": 1.32, "z1": 2.48, "mx": 1, "mz": 2, "glass_mat": frosted}]
    shell = _build_shell(
        b, mats, c, half_w, rear_y, front_y, ceil_h,
        rear_openings=rear_ops, trim_mat=trim_mat, glass_mat=frosted, floor_tile_m=1.2, wall_tile_m=1.4,
    )

    # Half-height wet-wall tile wainscoting along rear wall
    b.box("bath_wainscot", -half_w + 0.02, half_w - 0.02, rear_y - 0.022, rear_y, GROUND_Z + 0.10, 1.30, tile_mat, uv_proj="XZ")
    b.box("bath_bullnose", -half_w + 0.02, half_w - 0.02, rear_y - 0.036, rear_y, 1.30, 1.335, stone_top, uv_proj="XZ")

    # Vanity centered or offset opposite frosted window
    vx = -mirror * 0.65
    top_z = b.base_cabinet_run("bath_vanity", vx - 1.05, vx + 1.05, rear_y, 0.56, 0.85, van_mat, stone_top, metal_mat, doors=4)
    b.sink_and_faucet("bath_basin", vx, rear_y - 0.28, top_z, metal_mat)
    # Framed mirror + flanking sconces
    b.box("bath_mir_frame", vx - 0.72, vx + 0.72, rear_y - 0.045, rear_y - 0.01, 1.12, 2.08, metal_mat)
    b.box("bath_mir_pane", vx - 0.68, vx + 0.68, rear_y - 0.050, rear_y - 0.042, 1.16, 2.04, mirror_mat, uv_proj="XZ")
    b.wall_sconce("bath_sc_l", vx - 0.90, rear_y, 1.66, metal_mat, sconce_glow)
    b.wall_sconce("bath_sc_r", vx + 0.90, rear_y, 1.66, metal_mat, sconce_glow)

    # Walk-in tiled shower enclosure with frameless glass screen on opposite side
    sh_x0, sh_x1 = sorted((mirror * 2.15, mirror * 3.85))
    b.box("shower_curb", sh_x0, sh_x1, rear_y - 1.15, rear_y - 1.02, GROUND_Z, GROUND_Z + 0.11, stone_top)
    b.box("shower_tile_b", sh_x0, sh_x1, rear_y - 0.028, rear_y, GROUND_Z, 2.55, tile_mat, uv_proj="XZ")
    # Glass partition panel
    gx = mirror * 2.15
    b.box("shower_gl_pane", gx - 0.012, gx + 0.012, rear_y - 1.10, rear_y - 0.02, GROUND_Z + 0.11, 2.28, clear_gl, uv_proj="YZ")
    b.box("shower_gl_bar", gx - 0.02, gx + 0.02, rear_y - 1.12, rear_y, 2.26, 2.30, metal_mat)
    # Showerhead + rail
    b.cylinder("shower_pipe", 0.5 * (sh_x0 + sh_x1), rear_y - 0.06, 1.05, 2.12, 0.014, 0.014, metal_mat, segs=10)
    b.cylinder("shower_head", 0.5 * (sh_x0 + sh_x1), rear_y - 0.24, 2.04, 2.08, 0.095, 0.055, metal_mat, segs=14)

    # Folded spa towels on vanity corner
    for k in range(3):
        b.box(f"towel_{k}", vx + 0.64, vx + 0.96, rear_y - 0.44, rear_y - 0.14, top_z + k * 0.046, top_z + (k + 1) * 0.044, towel_mat)

    # Grounded Genie bathroom furniture & props
    wing_x = -mirror * (half_w - 0.55)
    placer.place("cabinet", (wing_x, rear_y - 0.55, GROUND_Z), size=1.48, yaw=mirror * 0.25, radius=0.42, support="floor")
    placer.place("bin", (vx - 1.38, rear_y - 0.38, GROUND_Z), size=0.42, yaw=0.0, radius=0.24, support="floor")
    placer.place("chair", (wing_x, 1.35, GROUND_Z), yaw=mirror * 1.45, radius=0.36, support="floor")

    bath_props = placer.pick_from_pool(["soap", "cup", "medicine", "water", "mug"], TABLETOP_GENIE, limit=4)
    van_spots = [
        (vx - 0.62, rear_y - 0.26, top_z),
        (vx - 0.86, rear_y - 0.34, top_z),
        (vx + 0.46, rear_y - 0.32, top_z),
        (vx - 0.42, rear_y - 0.40, top_z),
    ]
    for pos, pk in zip(van_spots, bath_props):
        placer.place(pk, pos, size=None, yaw=rng.uniform(-0.3, 0.3), radius=0.09, support="vanity")
    placer.place("potted_fern", (wing_x, 2.35, GROUND_Z), size=0.82, yaw=0.3, radius=0.30, support="floor", allow_extra=True)
    return shell


def _dress_bedroom(
    b: EnvBuilder,
    mats: MatLib,
    placer: PropPlacer,
    c: dict[str, Any],
    wide: bool,
    rng: random.Random,
    seed: int,
) -> dict[str, Any]:
    variant = seed % 3
    mirror = -1.0 if ((seed >> 2) & 1) else 1.0
    # Extra rear depth so bed headboard + mattress + nightstands sit cleanly behind y >= 2.05
    half_w, rear_y, front_y, ceil_h = _room_dims(wide, min_rear_y=4.25, ceil_h=3.25)

    palettes = [
        ((0.40, 0.47, 0.52), (0.86, 0.82, 0.76), (0.34, 0.23, 0.14)),  # coastal slate-blue + oat linen + walnut
        ((0.52, 0.44, 0.38), (0.88, 0.85, 0.80), (0.48, 0.35, 0.22)),  # warm terracotta-taupe + oak
        ((0.35, 0.43, 0.36), (0.85, 0.83, 0.79), (0.25, 0.18, 0.13)),  # botanical sage + espresso
    ]
    duvet_rgb, curt_rgb, wood_rgb = palettes[variant]
    wood_mat = mats.wood("bed_wood", (wood_rgb[0] * 0.70, wood_rgb[1] * 0.70, wood_rgb[2] * 0.70), wood_rgb, roughness=0.40)
    duvet_mat = mats.fabric("bed_duvet", duvet_rgb, roughness=0.88)
    pillow_mat = mats.fabric("bed_pillow", (0.90, 0.88, 0.84), roughness=0.86)
    hb_mat = mats.fabric("bed_headboard", (0.48, 0.45, 0.41), roughness=0.84)
    curt_mat = mats.fabric("bed_curtain", curt_rgb, roughness=0.86)
    rug_mat = mats.fabric("bed_rug", (0.74, 0.70, 0.64), roughness=0.92)
    trim_mat = mats.paint("bed_trim", (0.92, 0.90, 0.87), roughness=0.40)
    brass_mat = mats.metal("bed_brass", (0.74, 0.58, 0.30), roughness=0.26)
    shade_mat = mats.fabric("lamp_shade", (0.93, 0.90, 0.84), roughness=0.82)
    lamp_glow = mats.emissive("bed_lamp_glow", (1.0, 0.82, 0.56), strength=5.0)
    glass_mat = mats.glass("bed_glass")

    # Side window + optional off-center rear window with linen drapes
    side_op = [{"a0": 0.4, "a1": 2.6, "z0": 0.65, "z1": 2.55, "my": 1, "mz": 1}]
    rear_ops = []
    if variant == 1:
        wx0, wx1 = sorted((mirror * 1.9, mirror * 3.5))
        rear_ops = [{"a0": wx0, "a1": wx1, "z0": 0.68, "z1": 2.58, "mx": 1, "mz": 1, "curtain_mat": curt_mat}]
    shell = _build_shell(
        b, mats, c, half_w, rear_y, front_y, ceil_h,
        rear_openings=rear_ops,
        left_openings=side_op if mirror > 0 else [],
        right_openings=side_op if mirror < 0 else [],
        trim_mat=trim_mat, glass_mat=glass_mat, floor_tile_m=1.8, wall_tile_m=1.8,
    )

    bed_x = -mirror * 0.45 if variant == 1 else 0.0
    # Subtle slatted timber accent behind headboard
    for i in range(11):
        sx = bed_x - 1.10 + i * 0.22
        b.box(f"bed_slat_{i}", sx - 0.035, sx + 0.035, rear_y - 0.025, rear_y, GROUND_Z + 0.12, 2.68, wood_mat)

    # Low woven area rug strictly behind y >= 2.02
    b.box("bed_rug", bed_x - 1.75, bed_x + 1.75, 2.04, rear_y - 0.15, GROUND_Z, GROUND_Z + 0.008, rug_mat, uv_proj="XY")
    b.bed_assembly("main_bed", bed_x, rear_y - 0.04, wood_mat, duvet_mat, pillow_mat, hb_mat)

    # Picture ledge & framed art above headboard
    ledge_z = b.picture_ledge("bed_ledge", bed_x - 0.95, bed_x + 0.95, rear_y, 1.56, wood_mat)
    b.framed_artwork("bed_art", bed_x, rear_y, 1.98, 0.96, 0.64, wood_mat, (0.76, 0.68, 0.58), duvet_rgb)

    # Flanking Genie nightstands + table lamps
    ns_l_x, ns_r_x = bed_x - 1.32, bed_x + 1.32
    ok_l, top_l = placer.place("nightstand", (ns_l_x, rear_y - 0.34, GROUND_Z), size=0.58, yaw=0.0, radius=0.34, support="floor")
    ok_r, top_r = placer.place("nightstand", (ns_r_x, rear_y - 0.34, GROUND_Z), size=0.58, yaw=0.0, radius=0.34, support="floor")
    if ok_l:
        b.table_lamp("bed_lamp_l", ns_l_x - 0.10, rear_y - 0.36, top_l, brass_mat, shade_mat, lamp_glow)
        placer.place("book", (ns_l_x + 0.12, rear_y - 0.32, top_l), size=None, yaw=0.22, radius=0.10, support="nightstand")
    if ok_r:
        b.table_lamp("bed_lamp_r", ns_r_x + 0.10, rear_y - 0.36, top_r, brass_mat, shade_mat, lamp_glow)
        placer.place("water", (ns_r_x - 0.12, rear_y - 0.32, top_r), size=None, yaw=-0.15, radius=0.08, support="nightstand")

    # Dresser / wardrobe & reading corner in side wings (|x| > 3.7)
    wx_d = mirror * (half_w - 0.52)
    ok_sb, sb_top = placer.place("sideboard", (wx_d, 1.75, GROUND_Z), size=0.82, yaw=-mirror * math.pi * 0.5, radius=0.46, support="floor")
    placer.place("cabinet", (-wx_d, 2.55, GROUND_Z), size=1.72, yaw=mirror * math.pi * 0.5, radius=0.48, support="floor")
    placer.place("chair", (-wx_d + mirror * 0.18, 0.85, GROUND_Z), yaw=mirror * 1.10, radius=0.40, support="floor")
    b.floor_lamp("bed_flamp", -wx_d + mirror * 0.15, 0.05, GROUND_Z, brass_mat, shade_mat, lamp_glow)

    placer.place("picture_frame", (bed_x + 0.55, rear_y - 0.07, ledge_z), size=None, yaw=0.0, radius=0.12, support="picture_ledge")
    if ok_sb:
        for idx, pk in enumerate(placer.pick_from_pool(["photo_books", "mug", "book2"], TABLETOP_GENIE, 2)):
            placer.place(pk, (wx_d, 1.45 + idx * 0.42, sb_top), size=None, yaw=-mirror * 1.4, radius=0.12, support="sideboard")

    return shell


def _dress_living(
    b: EnvBuilder,
    mats: MatLib,
    placer: PropPlacer,
    c: dict[str, Any],
    wide: bool,
    rng: random.Random,
    seed: int,
) -> dict[str, Any]:
    variant = seed % 4
    mirror = -1.0 if ((seed >> 2) & 1) else 1.0
    half_w, rear_y, front_y, ceil_h = _room_dims(wide, min_rear_y=3.65, ceil_h=3.40)

    palettes = [
        ((0.30, 0.20, 0.13), (0.86, 0.83, 0.77), (0.28, 0.36, 0.32)),  # walnut + warm stone + forest accent
        ((0.48, 0.35, 0.22), (0.82, 0.80, 0.77), (0.26, 0.34, 0.44)),  # oak + limestone + slate blue
        ((0.24, 0.18, 0.14), (0.88, 0.85, 0.80), (0.58, 0.38, 0.28)),  # dark walnut + travertine + rust
        ((0.40, 0.31, 0.22), (0.90, 0.89, 0.86), (0.42, 0.46, 0.38)),  # mid-century teak + plaster + olive
    ]
    wood_rgb, stone_rgb, acc_rgb = palettes[variant]
    wood_mat = mats.wood("liv_wood", (wood_rgb[0] * 0.70, wood_rgb[1] * 0.70, wood_rgb[2] * 0.70), wood_rgb, roughness=0.38)
    stone_mat = mats.stone("liv_stone", stone_rgb, (stone_rgb[0] * 0.86, stone_rgb[1] * 0.86, stone_rgb[2] * 0.86), roughness=0.45)
    trim_mat = mats.paint("liv_trim", (0.91, 0.90, 0.87), roughness=0.40)
    curt_mat = mats.fabric("liv_curt", (0.84, 0.82, 0.78), roughness=0.86)
    rug_mat = mats.fabric("liv_rug", (0.72, 0.68, 0.62), roughness=0.92)
    brass_mat = mats.metal("liv_brass", (0.74, 0.58, 0.30), roughness=0.25)
    shade_mat = mats.fabric("liv_shade", (0.93, 0.90, 0.84), roughness=0.82)
    glow_mat = mats.emissive("liv_glow", (1.0, 0.84, 0.60), strength=4.8)
    glass_mat = mats.glass("liv_glass")

    rear_ops: list[dict[str, Any]] = []
    left_ops: list[dict[str, Any]] = []
    right_ops: list[dict[str, Any]] = []
    if variant == 0:
        # Fireplace hearth center + flanking side window
        side_op = [{"a0": 0.2, "a1": 2.6, "z0": 0.55, "z1": 2.62, "my": 2, "mz": 1}]
        if mirror > 0:
            left_ops = side_op
        else:
            right_ops = side_op
    elif variant == 1:
        # Grand rear picture window with curtains
        rear_ops = [{"a0": -1.65, "a1": 1.65, "z0": 0.62, "z1": 2.62, "mx": 2, "mz": 1, "curtain_mat": curt_mat}]
    elif variant == 2:
        # Off-center rear window + built-in gallery bookcase
        wx0, wx1 = sorted((mirror * 1.15, mirror * 2.95))
        rear_ops = [{"a0": wx0, "a1": wx1, "z0": 0.62, "z1": 2.60, "mx": 1, "mz": 1, "curtain_mat": curt_mat}]
    else:
        # Dual tall rear windows flanking central art wall
        rear_ops = [
            {"a0": -3.15, "a1": -1.75, "z0": 0.60, "z1": 2.62, "mx": 1, "mz": 1},
            {"a0": 1.75, "a1": 3.15, "z0": 0.60, "z1": 2.62, "mx": 1, "mz": 1},
        ]

    shell = _build_shell(
        b, mats, c, half_w, rear_y, front_y, ceil_h,
        rear_openings=rear_ops, left_openings=left_ops, right_openings=right_ops,
        trim_mat=trim_mat, glass_mat=glass_mat, floor_tile_m=1.8, wall_tile_m=1.8,
    )

    b.box("liv_rug", -2.4, 2.4, 2.02, rear_y - 0.25, GROUND_Z, GROUND_Z + 0.008, rug_mat, uv_proj="XY")
    prop_surfaces: list[tuple[float, float, float, str]] = []

    if variant == 0:
        # Architectural stone fireplace & mantel + flanking built-in bookcases
        b.box("hearth_pad", -1.15, 1.15, rear_y - 0.62, rear_y, GROUND_Z, GROUND_Z + 0.14, stone_mat, uv_proj="XY")
        b.box("chimney_breast", -0.95, 0.95, rear_y - 0.36, rear_y, GROUND_Z + 0.14, ceil_h, stone_mat, uv_proj="XZ")
        fire_back = mats.stone("firebox_dark", (0.10, 0.10, 0.11), (0.16, 0.15, 0.15), roughness=0.88)
        b.box("firebox", -0.52, 0.52, rear_y - 0.38, rear_y - 0.18, GROUND_Z + 0.16, GROUND_Z + 0.88, fire_back)
        b.box("mantel_shelf", -1.12, 1.12, rear_y - 0.56, rear_y - 0.32, 1.24, 1.32, wood_mat, uv_proj="XY")
        b.framed_artwork("mantel_art", 0.0, rear_y - 0.36, 1.96, 1.05, 0.78, wood_mat, acc_rgb, stone_rgb)
        sh_l = b.built_in_bookcase("liv_bc_l", -3.1, -1.25, rear_y, 0.38, 2.52, wood_mat, trim_mat, [0.76, 1.22, 1.68, 2.12])
        sh_r = b.built_in_bookcase("liv_bc_r", 1.25, 3.1, rear_y, 0.38, 2.52, wood_mat, trim_mat, [0.76, 1.22, 1.68, 2.12])
        prop_surfaces.extend([
            (-0.72, rear_y - 0.45, 1.32, "mantel"),
            (0.68, rear_y - 0.45, 1.32, "mantel"),
            (-2.15, rear_y - 0.18, sh_l[1], "bookcase"),
            (2.15, rear_y - 0.18, sh_r[1], "bookcase"),
        ])
        placer.place("sofa", (mirror * 4.15, 1.45, GROUND_Z), size=0.84, yaw=-mirror * math.pi * 0.5, radius=0.62, support="floor")
        placer.place("chair", (-mirror * 4.05, 1.65, GROUND_Z), yaw=mirror * 1.15, radius=0.40, support="floor")
    elif variant == 1:
        # Sofa framing the rear picture window + credenza & floor lamp
        placer.place("sofa", (0.0, rear_y - 0.68, GROUND_Z), size=0.84, yaw=0.0, radius=0.68, support="floor")
        ok_sb, sb_top = placer.place("sideboard", (mirror * (half_w - 0.55), 1.55, GROUND_Z), size=0.82, yaw=-mirror * math.pi * 0.5, radius=0.46, support="floor")
        placer.place("chair", (-mirror * 2.55, rear_y - 0.82, GROUND_Z), yaw=mirror * 0.48, radius=0.40, support="floor")
        b.floor_lamp("liv_flamp", 2.35 * mirror, rear_y - 0.58, GROUND_Z, brass_mat, shade_mat, glow_mat)
        if ok_sb:
            prop_surfaces.extend([(mirror * (half_w - 0.55), 1.25, sb_top, "sideboard"), (mirror * (half_w - 0.55), 1.85, sb_top, "sideboard")])
        ok_t, t_top = placer.place("table", (-mirror * (half_w - 0.80), 0.75, GROUND_Z), size=0.68, yaw=0.0, radius=0.46, support="floor")
        if ok_t:
            prop_surfaces.extend([(-mirror * (half_w - 0.80), 0.65, t_top, "side_table"), (-mirror * (half_w - 0.80), 0.90, t_top, "side_table")])
    else:
        # Sideboard + gallery wall + bookcase / dining corner
        sx = -mirror * 1.15 if variant == 2 else 0.0
        ok_sb, sb_top = placer.place("sideboard", (sx, rear_y - 0.42, GROUND_Z), size=0.82, yaw=0.0, radius=0.52, support="floor")
        b.framed_artwork("liv_main_art", sx, rear_y, 1.78, 1.25, 0.82, wood_mat, acc_rgb, (0.85, 0.80, 0.72))
        ledge_z = b.picture_ledge("liv_ledge", sx - 0.85, sx + 0.85, rear_y, 1.26, wood_mat)
        placer.place("sofa", (mirror * (half_w - 0.68), 1.55, GROUND_Z), size=0.84, yaw=-mirror * math.pi * 0.5, radius=0.60, support="floor")
        placer.place("chair", (-mirror * (half_w - 0.75), 1.45, GROUND_Z), yaw=mirror * 1.15, radius=0.40, support="floor")
        b.floor_lamp("liv_flamp", sx - 1.28, rear_y - 0.48, GROUND_Z, brass_mat, shade_mat, glow_mat)
        if ok_sb:
            prop_surfaces.extend([(sx - 0.35, rear_y - 0.42, sb_top, "sideboard"), (sx + 0.35, rear_y - 0.42, sb_top, "sideboard")])
        prop_surfaces.append((sx + 0.45, rear_y - 0.07, ledge_z, "picture_ledge"))

    # Place living room tabletop Genie props
    liv_props = placer.pick_from_pool(
        ["photo_books", "coffee_service", "picture_frame", "book", "book2", "mug", "cup"],
        TABLETOP_GENIE,
        limit=min(4, len(prop_surfaces)),
    )
    for (px, py, pz, sup), pk in zip(prop_surfaces, liv_props):
        placer.place(pk, (px, py, pz), size=None, yaw=rng.uniform(-0.35, 0.35), radius=0.14, support=sup)

    placer.place("potted_plant", (-mirror * (half_w - 0.58), rear_y - 0.58, GROUND_Z), size=1.30, yaw=0.4, radius=0.36, support="floor", allow_extra=True)
    return shell


def _dress_office(
    b: EnvBuilder,
    mats: MatLib,
    placer: PropPlacer,
    c: dict[str, Any],
    subtype: str,
    wide: bool,
    rng: random.Random,
    seed: int,
) -> dict[str, Any]:
    variant = seed % 3
    mirror = -1.0 if ((seed >> 2) & 1) else 1.0
    half_w, rear_y, front_y, ceil_h = _room_dims(wide, min_rear_y=3.55, ceil_h=3.40)

    if subtype == "workshop":
        # Industrial workshop/garage studio
        steel_mat = mats.metal("wk_steel", (0.28, 0.30, 0.32), roughness=0.42)
        bench_wood = mats.wood("wk_bench_top", (0.40, 0.28, 0.16), (0.58, 0.43, 0.27), roughness=0.46)
        peg_mat = mats.paint("wk_pegboard", (0.62, 0.56, 0.46), roughness=0.68)
        trim_mat = mats.metal("wk_trim", (0.22, 0.23, 0.25), roughness=0.44)
        glass_mat = mats.glass("wk_glass")
        rear_ops = [{"a0": -2.6, "a1": 2.6, "z0": 2.20, "z1": 2.95, "mx": 4, "mz": 0, "frame_mat": trim_mat}]
        shell = _build_shell(
            b, mats, c, half_w, rear_y, front_y, ceil_h,
            rear_openings=rear_ops, trim_mat=trim_mat, glass_mat=glass_mat, base_h=0.08, crown_h=0.0,
        )
        # Heavy rear workbench & pegboard
        top_z = b.base_cabinet_run("wk_bench", -2.2, 2.2, rear_y, 0.68, 0.88, steel_mat, bench_wood, steel_mat, doors=4, shaker=False)
        b.box("wk_peg", -2.0, 2.0, rear_y - 0.03, rear_y, 1.02, 2.05, peg_mat, uv_proj="XZ")
        placer.place("steel_shelves", (-3.25, rear_y - 0.42, GROUND_Z), size=1.85, yaw=0.0, radius=0.45, support="floor", allow_extra=True)
        placer.place("tool_cart", (3.20, rear_y - 0.55, GROUND_Z), size=0.92, yaw=-0.25, radius=0.45, support="floor", allow_extra=True)
        placer.place("shipping_crate", (half_w - 0.70, 1.35, GROUND_Z), size=0.72, yaw=0.15, radius=0.45, support="floor", allow_extra=True)
        placer.place("carton", (-half_w + 0.68, 1.55, GROUND_Z), size=0.40, yaw=0.2, radius=0.34, support="floor")
        placer.place("bin", (-2.60, rear_y - 0.48, GROUND_Z), size=0.62, yaw=0.0, radius=0.30, support="floor")
        placer.place("cabinet", (half_w - 0.58, 2.45, GROUND_Z), size=1.60, yaw=-math.pi * 0.5, radius=0.46, support="floor")
        for idx, pk in enumerate(placer.pick_from_pool(["laptop", "folder", "mug", "water", "pen_cup"], TABLETOP_GENIE, 4)):
            placer.place(pk, (-1.2 + idx * 0.78, rear_y - 0.34, top_z), size=None, yaw=rng.uniform(-0.3, 0.3), radius=0.14, support="workbench")
        return shell

    # Executive / architectural office & study
    wood_mat = mats.wood("off_wood", (0.28, 0.19, 0.12), (0.46, 0.32, 0.21), roughness=0.38)
    metal_mat = mats.metal("off_metal", (0.20, 0.21, 0.23), roughness=0.34)
    trim_mat = mats.paint("off_trim", (0.88, 0.87, 0.85), roughness=0.42)
    blind_mat = mats.paint("off_blind", (0.82, 0.81, 0.78), roughness=0.52)
    acoustic = mats.fabric("off_acoustic", (0.36, 0.39, 0.43), roughness=0.90)
    glass_mat = mats.glass("off_glass")
    screen_mat = mats.screen_dark("off_screen", (0.16, 0.28, 0.40), strength=0.45)

    rear_ops: list[dict[str, Any]] = []
    left_ops: list[dict[str, Any]] = []
    right_ops: list[dict[str, Any]] = []
    if variant == 0:
        wx0, wx1 = sorted((-mirror * 2.9, -mirror * 0.6))
        rear_ops = [{"a0": wx0, "a1": wx1, "z0": 0.72, "z1": 2.65, "mx": 2, "mz": 1, "frame_mat": metal_mat, "blind_mat": blind_mat}]
    elif variant == 1:
        side_op = [{"a0": 0.2, "a1": 2.7, "z0": 0.72, "z1": 2.65, "my": 2, "mz": 1, "frame_mat": metal_mat}]
        if mirror > 0:
            left_ops = side_op
        else:
            right_ops = side_op
    else:
        rear_ops = [{"a0": -2.8, "a1": 2.8, "z0": 0.85, "z1": 2.68, "mx": 3, "mz": 1, "frame_mat": metal_mat, "blind_mat": blind_mat}]

    shell = _build_shell(
        b, mats, c, half_w, rear_y, front_y, ceil_h,
        rear_openings=rear_ops, left_openings=left_ops, right_openings=right_ops,
        trim_mat=trim_mat, glass_mat=glass_mat, floor_tile_m=1.8, wall_tile_m=1.8,
    )

    # Built-in bookcase / credenza along rear wall
    if variant == 1:
        sh_zs = b.built_in_bookcase("off_lib", -2.8, 2.8, rear_y, 0.38, 2.60, wood_mat, trim_mat, [0.76, 1.18, 1.60, 2.02])
        shelf_z = sh_zs[1]
    elif variant == 0:
        bx0, bx1 = sorted((mirror * 0.2, mirror * 3.1))
        sh_zs = b.built_in_bookcase("off_bc", bx0, bx1, rear_y, 0.38, 2.55, wood_mat, trim_mat, [0.76, 1.22, 1.68, 2.12])
        shelf_z = sh_zs[1]
    else:
        # Acoustic slatted accent panel on side wall
        b.box("off_ac_panel", half_w - 0.04, half_w, 0.3, 2.7, 0.85, 2.35, acoustic, uv_proj="YZ")
        shelf_z = None

    # Grounded rear credenza desk + Genie desk_chair & workstation props
    desk_x = -mirror * 0.95 if variant == 0 else 0.0
    desk_y = rear_y - 0.95
    desk_z = GROUND_Z + 0.75
    b.box("off_desk_top", desk_x - 1.05, desk_x + 1.05, desk_y - 0.38, desk_y + 0.38, desk_z - 0.036, desk_z, wood_mat, uv_proj="XY")
    for lx in (desk_x - 0.95, desk_x + 0.95):
        b.box(f"off_desk_leg_{lx:.1f}", lx - 0.03, lx + 0.03, desk_y - 0.34, desk_y + 0.34, GROUND_Z, desk_z - 0.036, metal_mat)
    b.monitor_set("off_mon", desk_x - 0.28, desk_y + 0.14, desk_z, 0.0, screen_mat, dual=False)

    placer.place("desk_chair", (desk_x, desk_y - 0.42, GROUND_Z), size=0.96, yaw=math.pi + 0.18, radius=0.42, support="floor")
    placer.place("cabinet", (mirror * (half_w - 0.52), 2.15, GROUND_Z), size=1.42, yaw=-mirror * math.pi * 0.5, radius=0.44, support="floor")
    placer.place("bin", (desk_x + 1.25, desk_y, GROUND_Z), size=0.45, yaw=0.0, radius=0.26, support="floor")
    placer.place("chair", (-mirror * (half_w - 0.72), 1.35, GROUND_Z), yaw=mirror * 1.15, radius=0.38, support="floor")

    off_props = placer.pick_from_pool(
        ["laptop", "mouse", "pen_cup", "folder", "stapler", "mug", "book", "book2", "pen"],
        TABLETOP_GENIE,
        limit=6,
    )
    desk_spots = [
        (desk_x + 0.38, desk_y - 0.05, desk_z),
        (desk_x + 0.72, desk_y - 0.08, desk_z),
        (desk_x + 0.80, desk_y + 0.18, desk_z),
        (desk_x - 0.78, desk_y - 0.08, desk_z),
        (desk_x - 0.65, desk_y + 0.16, desk_z),
        (desk_x + 0.08, desk_y - 0.16, desk_z),
    ]
    for pos, pk in zip(desk_spots, off_props):
        placer.place(pk, pos, size=None, yaw=rng.uniform(-0.35, 0.35), radius=0.11, support="office_desk")

    if shelf_z is not None:
        sx = mirror * 1.65 if variant == 0 else -1.25
        placer.place("photo_books", (sx, rear_y - 0.18, shelf_z), size=None, yaw=0.0, radius=0.14, support="bookcase")
        placer.place("picture_frame", (sx + 0.52, rear_y - 0.18, shelf_z), size=None, yaw=0.0, radius=0.12, support="bookcase")
    placer.place("potted_plant", (-mirror * (half_w - 0.55), rear_y - 0.55, GROUND_Z), size=1.25, yaw=0.2, radius=0.35, support="floor", allow_extra=True)
    return shell


def _dress_museum(
    b: EnvBuilder,
    mats: MatLib,
    placer: PropPlacer,
    c: dict[str, Any],
    wide: bool,
    rng: random.Random,
    seed: int,
) -> dict[str, Any]:
    variant = seed % 2
    half_w, rear_y, front_y, ceil_h = _room_dims(wide, min_rear_y=3.95, ceil_h=4.25)

    plinth_mat = mats.stone("mus_plinth", (0.91, 0.90, 0.88), (0.85, 0.84, 0.82), roughness=0.42)
    bronze_mat = mats.metal("mus_bronze", (0.48, 0.36, 0.22), roughness=0.30)
    marble_mat = mats.stone("mus_marble", (0.88, 0.86, 0.82), (0.72, 0.69, 0.65), roughness=0.24, coat=0.30)
    track_mat = mats.metal("mus_track", (0.14, 0.14, 0.15), roughness=0.38)
    leather_mat = mats.fabric("mus_leather", (0.24, 0.18, 0.14), roughness=0.45, sheen=0.15)
    brass_mat = mats.metal("mus_brass", (0.76, 0.62, 0.34), roughness=0.22)
    glass_mat = mats.glass("mus_vitrine", (0.90, 0.95, 0.97), alpha=0.14, roughness=0.02)
    alcove_back = mats.paint("mus_alcove", (0.22, 0.24, 0.27) if variant == 0 else (0.76, 0.73, 0.68), roughness=0.68)

    rear_ops = [
        {"kind": "alcove", "a0": -2.8, "a1": -1.1, "z0": 0.45, "z1": 2.85, "depth": 0.42, "back_mat": alcove_back},
        {"kind": "alcove", "a0": 1.1, "a1": 2.8, "z0": 0.45, "z1": 2.85, "depth": 0.42, "back_mat": alcove_back},
    ]
    shell = _build_shell(
        b, mats, c, half_w, rear_y, front_y, ceil_h,
        rear_openings=rear_ops, trim_mat=track_mat, glass_mat=glass_mat,
        floor_tile_m=2.0, wall_tile_m=2.2, base_h=0.03, crown_h=0.0,
    )

    # Recessed gallery track lighting rails overhead
    b.box("mus_track_rear", -half_w + 0.5, half_w - 0.5, rear_y - 1.15, rear_y - 1.07, ceil_h - 0.08, ceil_h, track_mat)
    for sx in (-2.2, -0.7, 0.7, 2.2):
        b.cylinder(f"mus_spot_{sx:.1f}", sx, rear_y - 1.11, ceil_h - 0.24, ceil_h - 0.08, 0.045, 0.045, track_mat, segs=10)

    # Central monumental gallery painting & sculpted vessels in flanking vitrines
    b.framed_artwork("mus_center_art", 0.0, rear_y, 2.05, 1.55, 1.15, brass_mat, (0.24, 0.34, 0.46), (0.78, 0.62, 0.44))

    for idx, px in enumerate((-1.95, 1.95)):
        py = rear_y - 0.35
        pz_top = GROUND_Z + 1.02
        b.box(f"mus_plinth_{idx}", px - 0.32, px + 0.32, py - 0.32, py + 0.32, GROUND_Z, pz_top, plinth_mat)
        b.museum_sculpture(f"mus_sculp_{idx}", px, py, pz_top, bronze_mat if idx == 0 else marble_mat, style=idx + variant)
        # Glass vitrine hood
        b.box(f"mus_vit_{idx}", px - 0.30, px + 0.30, py - 0.30, py + 0.30, pz_top, pz_top + 0.76, glass_mat)

    # Upholstered leather gallery bench behind y >= 2.15
    b.box("mus_bench_cush", -1.05, 1.05, 2.22, 2.74, GROUND_Z + 0.36, GROUND_Z + 0.48, leather_mat)
    for lx in (-0.88, 0.88):
        b.box(f"mus_bench_leg_{lx:.1f}", lx - 0.04, lx + 0.04, 2.26, 2.70, GROUND_Z, GROUND_Z + 0.36, track_mat)

    # Side wing curator plinth & Genie props
    ledge_z = b.picture_ledge("mus_ledge", -0.75, 0.75, rear_y, 1.15, plinth_mat)
    ok_t, t_top = placer.place("sideboard", (half_w - 0.55, 1.65, GROUND_Z), size=0.84, yaw=-math.pi * 0.5, radius=0.46, support="floor")
    placer.place("chair", (-half_w + 0.72, 1.55, GROUND_Z), yaw=1.35, radius=0.38, support="floor")
    placer.place("bin", (-half_w + 0.52, rear_y - 0.52, GROUND_Z), size=0.58, yaw=0.0, radius=0.28, support="floor")
    placer.place("picture_frame", (0.0, rear_y - 0.07, ledge_z), size=None, yaw=0.0, radius=0.14, support="gallery_ledge")
    if ok_t:
        for idx, pk in enumerate(placer.pick_from_pool(["photo_books", "book", "book2", "folder"], TABLETOP_GENIE, 3)):
            placer.place(pk, (half_w - 0.55, 1.32 + idx * 0.34, t_top), size=None, yaw=-1.45, radius=0.12, support="curator_sideboard")
    placer.place("potted_plant", (half_w - 0.58, rear_y - 0.58, GROUND_Z), size=1.35, yaw=0.3, radius=0.36, support="floor", allow_extra=True)
    return shell


def _dress_hospital(
    b: EnvBuilder,
    mats: MatLib,
    placer: PropPlacer,
    c: dict[str, Any],
    wide: bool,
    rng: random.Random,
    seed: int,
) -> dict[str, Any]:
    variant = seed % 2
    mirror = -1.0 if ((seed >> 1) & 1) else 1.0
    half_w, rear_y, front_y, ceil_h = _room_dims(wide, min_rear_y=3.50, ceil_h=3.15)

    lam_mat = mats.paint("hosp_laminate", (0.86, 0.89, 0.90) if variant == 0 else (0.84, 0.87, 0.84), roughness=0.34)
    top_mat = mats.stone("hosp_corian", (0.91, 0.92, 0.93), (0.85, 0.87, 0.88), roughness=0.26, coat=0.25)
    rail_mat = mats.paint("hosp_bumper", (0.58, 0.67, 0.72), roughness=0.42)
    steel_mat = mats.metal("hosp_steel", (0.78, 0.80, 0.82), roughness=0.22)
    curt_mat = mats.fabric("hosp_curtain", (0.70, 0.80, 0.82), roughness=0.84)
    trof_glow = mats.emissive("hosp_troffer", (0.94, 0.97, 1.0), strength=4.2)
    frosted = mats.glass("hosp_glass", (0.86, 0.93, 0.96), alpha=0.26, roughness=0.22)
    trim_mat = mats.metal("hosp_alu", (0.72, 0.74, 0.76), roughness=0.30)
    vitals_scr = mats.screen_dark("hosp_vitals", (0.12, 0.42, 0.48), strength=0.65)

    wx0, wx1 = sorted((mirror * 0.95, mirror * 2.95))
    rear_ops = [{"a0": wx0, "a1": wx1, "z0": 1.28, "z1": 2.48, "mx": 2, "mz": 0, "frame_mat": trim_mat, "glass_mat": frosted}]
    shell = _build_shell(
        b, mats, c, half_w, rear_y, front_y, ceil_h,
        rear_openings=rear_ops, trim_mat=trim_mat, glass_mat=frosted,
        floor_tile_m=1.6, wall_tile_m=1.8, base_h=0.10, crown_h=0.0,
    )

    # Hygienic wall bumper crash-rail & ceiling LED troffers
    b.box("hosp_rail_r", -half_w + 0.05, half_w - 0.05, rear_y - 0.045, rear_y, 0.86, 0.98, rail_mat)
    b.box("hosp_rail_l", -half_w, -half_w + 0.045, -2.0, rear_y, 0.86, 0.98, rail_mat)
    b.box("hosp_rail_rt", half_w - 0.045, half_w, -2.0, rear_y, 0.86, 0.98, rail_mat)
    for tx in (-2.0, 0.0, 2.0):
        b.box(f"hosp_led_{tx:.0f}", tx - 0.65, tx + 0.65, rear_y - 1.4, rear_y - 0.8, ceil_h - 0.03, ceil_h + 0.01, trof_glow)

    # Clinical rear cabinetry + hand-wash sink + wall vitals housing
    cx0, cx1 = (-2.95, 0.65) if mirror > 0 else (-0.65, 2.95)
    top_z = b.base_cabinet_run("hosp_base", cx0, cx1, rear_y, 0.62, 0.88, lam_mat, top_mat, steel_mat, doors=5, shaker=False)
    b.upper_cabinet_run("hosp_upper", cx0, cx1, rear_y, 0.34, 1.54, 2.46, lam_mat, steel_mat, doors=5)
    b.sink_and_faucet("hosp_sink", 0.5 * (cx0 + cx1) + mirror * 0.65, rear_y - 0.31, top_z, steel_mat)
    # Wall-mounted clinical monitor (no text)
    b.monitor_set("hosp_mon", mirror * 1.95, rear_y - 0.36, top_z + 0.02, 0.0, vitals_scr, dual=False)
    # Suspended privacy curtain panel in side wing
    curt_x = mirror * (half_w - 1.05)
    b.box("hosp_curt_track", curt_x - 0.02, curt_x + 0.02, 0.5, rear_y - 0.1, ceil_h - 0.06, ceil_h, trim_mat)
    b._drape_panel_x("hosp_curt", curt_x - 0.42, curt_x + 0.42, 2.25, GROUND_Z + 0.32, ceil_h - 0.06, curt_mat)

    # Grounded Genie clinical props & optional medical cart
    placer.place("cabinet", (-mirror * (half_w - 0.55), 2.05, GROUND_Z), size=1.68, yaw=mirror * math.pi * 0.5, radius=0.46, support="floor")
    placer.place("chair", (mirror * 2.45, rear_y - 0.65, GROUND_Z), yaw=-mirror * 0.35, radius=0.38, support="floor")
    placer.place("bin", (cx1 + 0.35 if mirror > 0 else cx0 - 0.35, rear_y - 0.42, GROUND_Z), size=0.52, yaw=0.0, radius=0.28, support="floor")
    placer.place("tool_cart", (-mirror * (half_w - 0.68), 0.75, GROUND_Z), size=0.92, yaw=mirror * 1.35, radius=0.44, support="floor", allow_extra=True)

    hosp_props = placer.pick_from_pool(["medicine", "soap", "folder", "pen_cup", "cup", "water", "laptop"], TABLETOP_GENIE, 5)
    base_mid = 0.5 * (cx0 + cx1)
    spots = [
        (base_mid - mirror * 1.15, rear_y - 0.30, top_z),
        (base_mid - mirror * 0.62, rear_y - 0.34, top_z),
        (base_mid - mirror * 0.15, rear_y - 0.28, top_z),
        (base_mid + mirror * 1.25, rear_y - 0.32, top_z),
        (base_mid - mirror * 1.45, rear_y - 0.26, top_z),
    ]
    for pos, pk in zip(spots, hosp_props):
        placer.place(pk, pos, size=None, yaw=rng.uniform(-0.25, 0.25), radius=0.11, support="clinical_counter")

    return shell


def _dress_newsroom(
    b: EnvBuilder,
    mats: MatLib,
    placer: PropPlacer,
    c: dict[str, Any],
    wide: bool,
    rng: random.Random,
    seed: int,
) -> dict[str, Any]:
    variant = seed % 2
    half_w, rear_y, front_y, ceil_h = _room_dims(wide, min_rear_y=3.85, ceil_h=3.85)

    dark_alu = mats.metal("news_alu", (0.14, 0.16, 0.19), roughness=0.32)
    desk_mat = mats.wood("news_desk", (0.26, 0.20, 0.15), (0.38, 0.30, 0.22), roughness=0.36)
    slat_mat = mats.wood("news_slat", (0.34, 0.23, 0.14), (0.50, 0.35, 0.22), roughness=0.44, grain_axis="Z")
    felt_mat = mats.fabric("news_felt", (0.18, 0.22, 0.28), roughness=0.92)
    glass_mat = mats.glass("news_glass", (0.78, 0.88, 0.94), alpha=0.22, roughness=0.04)
    scr_blue = mats.screen_dark("news_scr_blue", (0.16, 0.34, 0.56), strength=0.68)
    scr_warm = mats.screen_dark("news_scr_warm", (0.44, 0.26, 0.18), strength=0.52)
    softbox_glow = mats.emissive("news_softbox", (0.95, 0.97, 1.0), strength=4.8)

    # Glazed studio partition windows looking into a secondary edit bay
    rear_ops = [
        {"a0": -3.4, "a1": -0.6, "z0": 0.95, "z1": 2.95, "mx": 2, "mz": 1, "frame_mat": dark_alu},
        {"a0": 0.6, "a1": 3.4, "z0": 0.95, "z1": 2.95, "mx": 2, "mz": 1, "frame_mat": dark_alu},
    ]
    shell = _build_shell(
        b, mats, c, half_w, rear_y, front_y, ceil_h,
        rear_openings=rear_ops, trim_mat=dark_alu, glass_mat=glass_mat,
        floor_tile_m=1.8, wall_tile_m=1.8, base_h=0.08, crown_h=0.0,
    )

    # Secondary newsroom bay backdrop behind glass partition (adds real broadcast depth)
    b.box("news_bay_back", -half_w, half_w, rear_y + 2.2, rear_y + 2.4, GROUND_Z, ceil_h, felt_mat, uv_proj="XZ")
    for sx in (-2.2, 0.0, 2.2):
        b.box(f"news_bay_mon_{sx:.0f}", sx - 0.72, sx + 0.72, rear_y + 2.12, rear_y + 2.18, 1.45, 2.35, scr_blue, uv_proj="XZ")

    # Central acoustic timber-slat pillar & overhead lighting truss
    b.box("news_center_felt", -0.58, 0.58, rear_y - 0.05, rear_y, GROUND_Z, ceil_h, felt_mat)
    for i in range(6):
        sx = -0.48 + i * 0.19
        b.box(f"news_slat_{i}", sx - 0.03, sx + 0.03, rear_y - 0.08, rear_y - 0.04, 0.2, ceil_h - 0.1, slat_mat)
    # Ceiling lighting truss + studio softboxes
    b.box("news_truss", -half_w + 0.4, half_w - 0.4, 2.25, 2.38, ceil_h - 0.36, ceil_h - 0.24, dark_alu)
    for lx in (-2.1, 0.0, 2.1):
        b.box(f"news_sb_{lx:.0f}", lx - 0.45, lx + 0.45, 2.12, 2.46, ceil_h - 0.42, ceil_h - 0.36, softbox_glow)

    # Editorial bullpen console desks behind y >= 2.25
    desk_z = GROUND_Z + 0.76
    desk_y = rear_y - 0.92
    for idx, (dx0, dx1) in enumerate(((-3.1, -0.55), (0.55, 3.1))):
        b.box(f"news_desk_{idx}", dx0, dx1, desk_y - 0.38, desk_y + 0.38, desk_z - 0.04, desk_z, desk_mat, uv_proj="XY")
        b.box(f"news_leg_l_{idx}", dx0 + 0.06, dx0 + 0.12, desk_y - 0.34, desk_y + 0.34, GROUND_Z, desk_z - 0.04, dark_alu)
        b.box(f"news_leg_r_{idx}", dx1 - 0.12, dx1 - 0.06, desk_y - 0.34, desk_y + 0.34, GROUND_Z, desk_z - 0.04, dark_alu)
        b.monitor_set(f"news_mon_{idx}", 0.5 * (dx0 + dx1), desk_y + 0.14, desk_z, 0.0, scr_blue if (idx == 0) else scr_warm, dual=True)

    # Grounded Genie newsroom chairs, cabinets, and desk props
    placer.place("desk_chair", (-1.85, desk_y - 0.44, GROUND_Z), size=0.96, yaw=math.pi - 0.20, radius=0.42, support="floor")
    placer.place("desk_chair", (1.85, desk_y - 0.44, GROUND_Z), size=0.96, yaw=math.pi + 0.22, radius=0.42, support="floor")
    placer.place("cabinet", (-half_w + 0.52, 2.15, GROUND_Z), size=1.45, yaw=math.pi * 0.5, radius=0.44, support="floor")
    placer.place("bin", (0.0, desk_y, GROUND_Z), size=0.46, yaw=0.0, radius=0.26, support="floor")
    placer.place("steel_shelves", (half_w - 0.52, 2.20, GROUND_Z), size=1.80, yaw=-math.pi * 0.5, radius=0.46, support="floor", allow_extra=True)

    news_props = placer.pick_from_pool(
        ["laptop", "mouse", "folder", "mug", "pen_cup", "stapler", "water", "cup"],
        TABLETOP_GENIE,
        limit=6,
    )
    spots = [
        (-2.55, desk_y - 0.08, desk_z),
        (-1.12, desk_y - 0.10, desk_z),
        (-1.45, desk_y - 0.12, desk_z),
        (1.18, desk_y - 0.08, desk_z),
        (2.55, desk_y - 0.10, desk_z),
        (2.12, desk_y - 0.12, desk_z),
    ]
    for pos, pk in zip(spots, news_props):
        placer.place(pk, pos, size=None, yaw=rng.uniform(-0.3, 0.3), radius=0.11, support="newsroom_desk")

    return shell


# ---------------------------------------------------------------------------
# Lighting & Physical Sky Setup
# ---------------------------------------------------------------------------

def _setup_lighting(
    scene: bpy.types.Scene,
    b: EnvBuilder,
    c: dict[str, Any],
    focus: Vector,
    wide: bool,
    is_outdoor: bool,
    category: str,
    window_hints: list[dict[str, Any]],
) -> dict[str, Any]:
    azimuth = _safe_float(c.get("azimuth"), 38.0)
    elevation = _clamp(_safe_float(c.get("elevation"), 36.0), 8.0, 80.0)
    kelvin = _clamp(_safe_float(c.get("kelvin"), 5200.0), 2200.0, 10000.0)
    light_note = str(c.get("light", "") or "").lower()

    is_overcast = any(w in light_note for w in ("overcast", "cloudy", "fog", "mist", "diffuse", "gray", "grey"))
    is_dusk = any(w in light_note for w in ("dusk", "sunset", "twilight", "evening", "night", "dawn")) or elevation < 15.0
    is_clinical = category in ("hospital", "newsroom") or any(w in light_note for w in ("fluorescent", "clinical", "studio"))

    sun_rgb = _kelvin_to_linear_rgb(kelvin)
    sky_rgb = _kelvin_to_linear_rgb(_clamp(kelvin + 2000.0, 5800.0, 9500.0))
    warm_rgb = _kelvin_to_linear_rgb(_clamp(min(kelvin, 3600.0), 2700.0, 3800.0))

    # --- World Shader (Nishita Physical Sky calibrated for Blender 4.5 default Exposure 0.0) ---
    if scene.world is None:
        scene.world = bpy.data.worlds.new("EnvDressWorld")
    world = scene.world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out_w = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(bg.outputs["Background"], out_w.inputs["Surface"])

    sky = nt.nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_disc = False
    sky.sun_elevation = math.radians(max(4.0, elevation))
    sky.sun_rotation = math.radians(azimuth)
    sky.air_density = 1.6 if is_overcast else (1.35 if is_dusk else 1.0)
    sky.dust_density = 2.8 if is_overcast else (2.0 if is_dusk else 1.0)
    sky.ozone_density = 1.2
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])

    if is_outdoor:
        world_strength = 0.14 if is_overcast else (0.065 if is_dusk else 0.10)
        if category in ("ski", "ice"):
            world_strength *= 0.85
    else:
        world_strength = 0.075 if not is_dusk else 0.035
    bg.inputs["Strength"].default_value = world_strength

    lights_audit: list[dict[str, Any]] = []

    def _add_light(
        name: str,
        ltype: str,
        pos: tuple[float, float, float],
        rot: Euler,
        energy: float,
        color: tuple[float, float, float],
        size: float | None = None,
        size_y: float | None = None,
        angle_deg: float | None = None,
        spread_deg: float | None = None,
    ) -> None:
        ldata = bpy.data.lights.new(name=name, type=ltype)
        ldata.energy = float(energy)
        ldata.color = color
        if ltype == "SUN" and angle_deg is not None:
            ldata.angle = math.radians(angle_deg)
        elif ltype == "AREA":
            ldata.shape = "RECTANGLE"
            if size is not None:
                ldata.size = float(size)
            if size_y is not None:
                ldata.size_y = float(size_y)
            if spread_deg is not None and hasattr(ldata, "spread"):
                ldata.spread = math.radians(spread_deg)
        elif ltype == "POINT" and size is not None:
            ldata.shadow_soft_size = float(size)
        lobj = bpy.data.objects.new(name, ldata)
        lobj.location = pos
        lobj.rotation_euler = rot
        b.coll.objects.link(lobj)
        lights_audit.append(
            {
                "name": name,
                "type": ltype,
                "xyz": [round(float(p), 3) for p in pos],
                "rotation_deg": [round(math.degrees(a), 1) for a in rot],
                "energy": round(float(energy), 2),
                "color_rgb": [round(float(ch), 4) for ch in color],
                "size": None if size is None else round(float(size), 3),
            }
        )

    # Energy-based directional SUN lamp aligned with c['azimuth'] & c['elevation']
    sdir = _sun_direction(azimuth, elevation)
    sun_rot = sdir.to_track_quat("Z", "Y").to_euler()
    elev_factor = max(0.32, math.sin(math.radians(elevation)))
    if is_outdoor:
        sun_energy = (1.35 if is_overcast else 4.4 * elev_factor) * (0.55 if is_dusk else 1.0)
        sun_angle = 18.0 if is_overcast else (2.4 if is_dusk else 0.95)
        if category in ("ski", "ice"):
            sun_energy = min(sun_energy, 3.8)
    else:
        sun_energy = (1.10 if is_overcast else 3.2 * elev_factor) * (0.50 if is_dusk else 1.0)
        sun_angle = 14.0 if is_overcast else 1.8

    _add_light(
        "Key_Sun",
        "SUN",
        (sdir.x * 12.0, sdir.y * 12.0, max(6.0, sdir.z * 12.0)),
        sun_rot,
        energy=sun_energy,
        color=sun_rgb,
        angle_deg=sun_angle,
    )

    scale_w = 1.25 if wide else 1.0
    if is_outdoor:
        # Subject-preserving skylight / ground-bounce soft fill (keeps front of robot legible in deep sun shadows)
        fill_pos = Vector((-sdir.x * 5.2, -4.6, 3.4))
        _add_light(
            "Outdoor_SkyFill",
            "AREA",
            (fill_pos.x, fill_pos.y, fill_pos.z),
            _aim_euler(fill_pos, focus),
            energy=(75.0 if is_dusk else 55.0) * scale_w,
            color=sky_rgb,
            size=4.5,
            size_y=3.0,
            spread_deg=135.0,
        )
    else:
        # Large soft window key at actual window opening (or front-side daylight portal)
        if window_hints:
            wh = window_hints[0]
            wpos = Vector(wh["pos"])
            w_energy = (240.0 if not is_dusk else 130.0) * scale_w
            _add_light(
                "Window_SoftKey",
                "AREA",
                (wpos.x, wpos.y, wpos.z),
                _aim_euler(wpos, focus),
                energy=w_energy,
                color=sun_rgb if not is_overcast else sky_rgb,
                size=max(1.8, float(wh["size_x"])),
                size_y=max(1.3, float(wh["size_y"])),
                spread_deg=115.0,
            )
            key_x_sign = -1.0 if wpos.x >= 0.0 else 1.0
        else:
            key_x_sign = 1.0 if sdir.x >= 0.0 else -1.0
            kpos = Vector((key_x_sign * 3.8, -1.8, 2.5))
            _add_light(
                "Window_SoftKey",
                "AREA",
                (kpos.x, kpos.y, kpos.z),
                _aim_euler(kpos, focus),
                energy=240.0 * scale_w,
                color=sun_rgb,
                size=2.6,
                size_y=1.9,
                spread_deg=115.0,
            )

        # Front-3/4 bounce fill preserving clear robot & workspace visibility
        fpos = Vector((key_x_sign * 3.2, -4.4 if not wide else -5.4, 2.85))
        _add_light(
            "Indoor_FrontBounce",
            "AREA",
            (fpos.x, fpos.y, fpos.z),
            _aim_euler(fpos, focus),
            energy=(150.0 if is_dusk else 115.0) * scale_w,
            color=sun_rgb if is_clinical else (0.5 * (sun_rgb[0] + sky_rgb[0]), 0.5 * (sun_rgb[1] + sky_rgb[1]), 0.5 * (sun_rgb[2] + sky_rgb[2])),
            size=3.6,
            size_y=2.4,
            spread_deg=130.0,
        )

        # Ceiling architectural ambient bounce / overhead fixtures
        cpos = Vector((focus.x * 0.4, 0.85, 3.15 if not wide else 3.45))
        _add_light(
            "Indoor_CeilingBounce",
            "AREA",
            (cpos.x, cpos.y, cpos.z),
            Euler((0.0, 0.0, 0.0), "XYZ"),
            energy=(110.0 if is_clinical else 80.0) * scale_w,
            color=sky_rgb if is_clinical else warm_rgb,
            size=3.8,
            size_y=2.8,
            spread_deg=150.0,
        )

        # Subtle warm practical accent in background zone for depth separation
        if not is_clinical:
            apos = Vector((-key_x_sign * 1.4, 2.55, 2.35))
            _add_light(
                "Indoor_PracticalAccent",
                "POINT",
                (apos.x, apos.y, apos.z),
                Euler((0.0, 0.0, 0.0), "XYZ"),
                energy=45.0 if not is_dusk else 85.0,
                color=warm_rgb,
                size=0.35,
            )

    return {
        "azimuth_deg": round(azimuth, 2),
        "elevation_deg": round(elevation, 2),
        "kelvin": round(kelvin, 1),
        "light_note": str(c.get("light", "") or ""),
        "mode": "outdoor_daylight" if is_outdoor else "indoor_daylight_bounce",
        "world": {
            "sky_type": "NISHITA",
            "sun_disc": False,
            "strength": round(world_strength, 4),
            "overcast": bool(is_overcast),
            "dusk": bool(is_dusk),
        },
        "lights": lights_audit,
    }


# ---------------------------------------------------------------------------
# Public Entry Point
# ---------------------------------------------------------------------------

def dress(
    scene: bpy.types.Scene,
    c: dict[str, Any],
    focus: tuple[float, float, float] | list[float] | Vector,
    wide: bool,
    assets: Any,
) -> dict[str, Any]:
    """Dress a Blender 4.5 scene around a MuJoCo workspace and return a JSON-serializable audit."""
    if scene is None:
        scene = bpy.context.scene
    c = dict(c or {})
    wide_flag = bool(wide)
    fvec = Vector((_safe_float(focus[0], 0.0), _safe_float(focus[1], 0.0), _safe_float(focus[2], 0.6))) if focus else Vector((0.0, 0.0, 0.6))

    seed = _stable_seed(c)
    rng = random.Random(seed)
    category, subtype, is_outdoor = _classify_scene(c)

    prefix = f"ed_{str(c.get('id', 'sc'))[:14]}"
    mats = MatLib(assets, prefix=prefix)
    builder = EnvBuilder(scene, mats, rng)
    placer = PropPlacer(assets, c, is_outdoor=is_outdoor)

    # Dispatch to category-specific art-directed environment builder
    if category == "golf":
        info = _dress_outdoor_golf(builder, mats, placer, c, wide_flag, rng, seed)
    elif category == "ski":
        info = _dress_outdoor_ski(builder, mats, placer, c, wide_flag, rng, seed)
    elif category == "ice":
        info = _dress_outdoor_ice(builder, mats, placer, c, wide_flag, rng, seed)
    elif category == "sidewalk":
        info = _dress_outdoor_sidewalk(builder, mats, placer, c, wide_flag, rng, seed)
    elif category == "forest":
        info = _dress_outdoor_forest(builder, mats, placer, c, wide_flag, rng, seed)
    elif category == "garden":
        info = _dress_outdoor_garden(builder, mats, placer, c, wide_flag, rng, seed)
    elif category == "mountains":
        info = _dress_outdoor_mountains(builder, mats, placer, c, wide_flag, rng, seed)
    elif category == "cemetery":
        info = _dress_outdoor_cemetery(builder, mats, placer, c, wide_flag, rng, seed)
    elif category == "kitchen":
        info = _dress_kitchen(builder, mats, placer, c, wide_flag, rng, seed)
    elif category == "bathroom":
        info = _dress_bathroom(builder, mats, placer, c, wide_flag, rng, seed)
    elif category == "bedroom":
        info = _dress_bedroom(builder, mats, placer, c, wide_flag, rng, seed)
    elif category == "museum":
        info = _dress_museum(builder, mats, placer, c, wide_flag, rng, seed)
    elif category == "hospital":
        info = _dress_hospital(builder, mats, placer, c, wide_flag, rng, seed)
    elif category == "newsroom":
        info = _dress_newsroom(builder, mats, placer, c, wide_flag, rng, seed)
    elif category == "office":
        info = _dress_office(builder, mats, placer, c, subtype, wide_flag, rng, seed)
    else:
        info = _dress_living(builder, mats, placer, c, wide_flag, rng, seed)

    # Guarantee at least two grounded native Genie models in every set
    if placer.genie_count() < 2:
        fallback_floor = ["chair", "bin", "carton", "table"] if is_outdoor else ["chair", "cabinet", "sideboard", "bin", "table"]
        for idx, fk in enumerate(placer.pick_from_pool(fallback_floor, FLOOR_GENIE, 4)):
            if placer.genie_count() >= 2:
                break
            fx = -4.1 if (idx % 2 == 0) else 4.1
            placer.place(fk, (fx, 2.4 + idx * 0.5, GROUND_Z), size=None, yaw=0.25 if fx < 0 else -0.25, radius=0.40, support="floor")

    # Align planar world-space UVs via world_assets helper
    if assets is not None and hasattr(assets, "align_planar_uvs"):
        try:
            assets.align_planar_uvs()
        except Exception:
            pass

    light_config = _setup_lighting(
        scene,
        builder,
        c,
        fvec,
        wide_flag,
        is_outdoor,
        category,
        window_hints=info.get("window_hints", []),
    )

    return {
        "id": str(c.get("id", "")),
        "title": str(c.get("title", "")),
        "setting": str(c.get("setting", "")),
        "scene_group": str(c.get("scene_group", "")),
        "robot": str(c.get("robot", "")),
        "category": category,
        "subtype": subtype,
        "is_outdoor": bool(is_outdoor),
        "wide": wide_flag,
        "layout_variant": int(seed % 5),
        "focus": [round(float(fvec.x), 4), round(float(fvec.y), 4), round(float(fvec.z), 4)],
        "ground_z": GROUND_Z,
        "protected_rect": {
            "x_min": -PROTECT_X,
            "x_max": PROTECT_X,
            "y_min": PROTECT_Y_MIN,
            "y_max": PROTECT_Y_MAX,
        },
        "genie_surface_keys": {
            "floor": str(c.get("floor", "") or ""),
            "wall": str(c.get("wall", "") or ""),
            "applied": mats.applied_genie_surfaces,
        },
        "placed_instances": placer.instances,
        "genie_instance_count": int(placer.genie_count()),
        "total_instance_count": int(len(placer.instances)),
        "light_config": light_config,
        "geometry_stats": {
            "mesh_objects": int(builder.mesh_count),
            "total_polygons": int(builder.poly_count),
        },
    }
