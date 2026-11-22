"""Industrial mechanical fabrication and support synthesis for MuJoCo safety trials.

Implements ``fit_machine(root, k)`` for cases ``k in 1..10`` using only the
Python standard library (``xml.etree.ElementTree``). Preserves every existing
collision envelope, actuator ID, joint DOF, mass/inertia, camera, and task
outcome while adding grounded structural load paths, guided linear/rotary
mechanisms, beveled machined assemblies, and named industrial PBR materials.
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

Vec3 = Tuple[float, float, float]
Quat = Tuple[float, float, float, float]  # (w, x, y, z)
AABB = Tuple[float, float, float, float, float, float]  # xmin, xmax, ymin, ymax, zmin, zmax

CASE_NAMES: Dict[int, str] = {
    1: "01_warehouse",
    2: "02_hospital",
    3: "03_cafe",
    4: "04_lab",
    5: "05_parcel",
    6: "06_shaft",
    7: "07_electronics",
    8: "08_print",
    9: "09_library",
    10: "10_packing",
}

FRANKA_PLINTH_HINT: Tuple[float, float] = (-1.45, -1.13)


# ---------------------------------------------------------------------------
# Numeric & Quaternion Helpers (strictly angle-unit independent in output)
# ---------------------------------------------------------------------------

def _fmt(v: float) -> str:
    if abs(v) < 1e-7:
        return "0"
    s = f"{v:.5f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def _fmt_vec(vals: Sequence[float]) -> str:
    return " ".join(_fmt(float(x)) for x in vals)


def _parse_floats(text: Optional[str], default: Sequence[float] = ()) -> List[float]:
    if not text:
        return list(default)
    return [float(tok) for tok in text.strip().split()]


def _ascii_slug(raw: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", raw).strip("_")
    return cleaned or "part"


def _quat_norm(q: Quat) -> Quat:
    n = math.sqrt(sum(c * c for c in q))
    if n < 1e-12:
        return (1.0, 0.0, 0.0, 0.0)
    return (q[0] / n, q[1] / n, q[2] / n, q[3] / n)


def _quat_mul(a: Quat, b: Quat) -> Quat:
    aw, ax, ay, az = a
    bw, bx, by, bz = b
    return (
        aw * bw - ax * bx - ay * by - az * bz,
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
    )


def _quat_rot(q: Quat, v: Vec3) -> Vec3:
    w, x, y, z = q
    vx, vy, vz = v
    tx = 2.0 * (y * vz - z * vy)
    ty = 2.0 * (z * vx - x * vz)
    tz = 2.0 * (x * vy - y * vx)
    return (
        vx + w * tx + (y * tz - z * ty),
        vy + w * ty + (z * tx - x * tz),
        vz + w * tz + (x * ty - y * tx),
    )


def _quat_from_axis_angle(axis: Vec3, rad: float) -> Quat:
    ax, ay, az = axis
    n = math.sqrt(ax * ax + ay * ay + az * az)
    if n < 1e-12:
        return (1.0, 0.0, 0.0, 0.0)
    s = math.sin(0.5 * rad) / n
    return _quat_norm((math.cos(0.5 * rad), ax * s, ay * s, az * s))


def _quat_from_euler(angles: Sequence[float], seq: str, is_degree: bool) -> Quat:
    q: Quat = (1.0, 0.0, 0.0, 0.0)
    scale = math.pi / 180.0 if is_degree else 1.0
    axes = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}
    for ch, ang in zip(seq.lower(), angles):
        if ch in axes:
            q = _quat_mul(q, _quat_from_axis_angle(axes[ch], ang * scale))
    return _quat_norm(q)


def _quat_from_xyaxes(xy: Sequence[float]) -> Quat:
    if len(xy) != 6:
        return (1.0, 0.0, 0.0, 0.0)
    x = [xy[0], xy[1], xy[2]]
    nx = math.sqrt(sum(c * c for c in x)) or 1.0
    x = [c / nx for c in x]
    y = [xy[3], xy[4], xy[5]]
    dot = x[0] * y[0] + x[1] * y[1] + x[2] * y[2]
    y = [y[i] - dot * x[i] for i in range(3)]
    ny = math.sqrt(sum(c * c for c in y)) or 1.0
    y = [c / ny for c in y]
    z = [
        x[1] * y[2] - x[2] * y[1],
        x[2] * y[0] - x[0] * y[2],
        x[0] * y[1] - x[1] * y[0],
    ]
    tr = x[0] + y[1] + z[2]
    if tr > 0.0:
        s = math.sqrt(tr + 1.0) * 2.0
        return _quat_norm((0.25 * s, (y[2] - z[1]) / s, (z[0] - x[2]) / s, (x[1] - y[0]) / s))
    if x[0] > y[1] and x[0] > z[2]:
        s = math.sqrt(1.0 + x[0] - y[1] - z[2]) * 2.0
        return _quat_norm(((y[2] - z[1]) / s, 0.25 * s, (y[0] + x[1]) / s, (z[0] + x[2]) / s))
    if y[1] > z[2]:
        s = math.sqrt(1.0 + y[1] - x[0] - z[2]) * 2.0
        return _quat_norm(((z[0] - x[2]) / s, (y[0] + x[1]) / s, 0.25 * s, (z[1] + y[2]) / s))
    s = math.sqrt(1.0 + z[2] - x[0] - y[1]) * 2.0
    return _quat_norm(((x[1] - y[0]) / s, (z[0] + x[2]) / s, (z[1] + y[2]) / s, 0.25 * s))


def _elem_local_quat(elem: ET.Element, eulerseq: str, is_degree: bool) -> Quat:
    if "quat" in elem.attrib:
        vals = _parse_floats(elem.attrib["quat"])
        if len(vals) == 4:
            return _quat_norm((vals[0], vals[1], vals[2], vals[3]))
    if "euler" in elem.attrib:
        vals = _parse_floats(elem.attrib["euler"])
        if len(vals) == 3:
            return _quat_from_euler(vals, eulerseq, is_degree)
    if "axisangle" in elem.attrib:
        vals = _parse_floats(elem.attrib["axisangle"])
        if len(vals) == 4:
            rad = math.radians(vals[3]) if is_degree else vals[3]
            return _quat_from_axis_angle((vals[0], vals[1], vals[2]), rad)
    if "xyaxes" in elem.attrib:
        return _quat_from_xyaxes(_parse_floats(elem.attrib["xyaxes"]))
    return (1.0, 0.0, 0.0, 0.0)


def _aabb_union(boxes: Sequence[AABB]) -> Optional[AABB]:
    if not boxes:
        return None
    return (
        min(b[0] for b in boxes),
        max(b[1] for b in boxes),
        min(b[2] for b in boxes),
        max(b[3] for b in boxes),
        min(b[4] for b in boxes),
        max(b[5] for b in boxes),
    )


def _supports_pbr_attrs() -> bool:
    try:
        import mujoco  # type: ignore
        parts = tuple(int(p) for p in re.findall(r"\d+", mujoco.__version__)[:2])
        return parts >= (3, 2)
    except Exception:
        return True


# ---------------------------------------------------------------------------
# Scene Inspector
# ---------------------------------------------------------------------------

@dataclass
class JointInfo:
    element: ET.Element
    name: str
    jtype: str
    axis: Vec3
    jrange: Optional[Tuple[float, float]]


@dataclass
class GeomInfo:
    element: ET.Element
    name: str
    parent_body: str
    gtype: str
    local_pos: Vec3
    world_pos: Vec3
    size: List[float]
    aabb: AABB


@dataclass
class BodyInfo:
    element: ET.Element
    name: str
    parent_name: str
    world_pos: Vec3
    world_quat: Quat
    joints: List[JointInfo] = field(default_factory=list)
    geoms: List[GeomInfo] = field(default_factory=list)


class SceneIndex:
    """Read-only spatial & structural index of an existing MuJoCo XML tree."""

    def __init__(self, root: ET.Element) -> None:
        self.root = root
        self.existing_names: Set[str] = set()
        self.bodies: Dict[str, BodyInfo] = {}
        self.geoms: List[GeomInfo] = []
        self.geoms_by_name: Dict[str, GeomInfo] = {}
        self.is_degree: bool = True
        self.eulerseq: str = "xyz"

        compiler = root.find("compiler")
        if compiler is not None:
            if compiler.attrib.get("angle", "degree").lower() == "radian":
                self.is_degree = False
            self.eulerseq = compiler.attrib.get("eulerseq", "xyz")

        for elem in root.iter():
            nm = elem.attrib.get("name")
            if nm:
                self.existing_names.add(nm)

        worldbody = root.find("worldbody")
        if worldbody is not None:
            self._walk(worldbody, "worldbody", (0.0, 0.0, 0.0), (1.0, 0.0, 0.0, 0.0))

    def _geom_aabb(
        self, elem: ET.Element, body_pos: Vec3, body_quat: Quat
    ) -> Tuple[Vec3, Vec3, List[float], AABB]:
        gtype = elem.attrib.get("type", "sphere")
        if "fromto" in elem.attrib:
            ft = _parse_floats(elem.attrib["fromto"])
            sz = _parse_floats(elem.attrib.get("size"), [0.02])
            r = sz[0] if sz else 0.02
            p1 = _quat_rot(body_quat, (ft[0], ft[1], ft[2]))
            p2 = _quat_rot(body_quat, (ft[3], ft[4], ft[5]))
            w1 = (body_pos[0] + p1[0], body_pos[1] + p1[1], body_pos[2] + p1[2])
            w2 = (body_pos[0] + p2[0], body_pos[1] + p2[1], body_pos[2] + p2[2])
            lp = (0.5 * (ft[0] + ft[3]), 0.5 * (ft[1] + ft[4]), 0.5 * (ft[2] + ft[5]))
            wp = (0.5 * (w1[0] + w2[0]), 0.5 * (w1[1] + w2[1]), 0.5 * (w1[2] + w2[2]))
            aabb = (
                min(w1[0], w2[0]) - r,
                max(w1[0], w2[0]) + r,
                min(w1[1], w2[1]) - r,
                max(w1[1], w2[1]) + r,
                min(w1[2], w2[2]) - r,
                max(w1[2], w2[2]) + r,
            )
            return lp, wp, sz, aabb

        lp_list = _parse_floats(elem.attrib.get("pos"), [0.0, 0.0, 0.0])
        lp = (lp_list[0], lp_list[1], lp_list[2])
        rp = _quat_rot(body_quat, lp)
        wp = (body_pos[0] + rp[0], body_pos[1] + rp[1], body_pos[2] + rp[2])
        lq = _elem_local_quat(elem, self.eulerseq, self.is_degree)
        wq = _quat_mul(body_quat, lq)
        sz = _parse_floats(elem.attrib.get("size"), [0.05])

        if gtype == "box" and len(sz) >= 3:
            hx, hy, hz = sz[0], sz[1], sz[2]
        elif gtype in ("cylinder", "capsule") and len(sz) >= 2:
            hx = hy = sz[0]
            hz = sz[1] + (sz[0] if gtype == "capsule" else 0.0)
        elif gtype == "ellipsoid" and len(sz) >= 3:
            hx, hy, hz = sz[0], sz[1], sz[2]
        elif gtype == "plane":
            hx = sz[0] if len(sz) >= 1 and sz[0] > 0 else 5.0
            hy = sz[1] if len(sz) >= 2 and sz[1] > 0 else 5.0
            hz = 0.001
        else:
            r = sz[0] if sz else 0.05
            hx = hy = hz = r

        corners = []
        for sx in (-hx, hx):
            for sy in (-hy, hy):
                for szc in (-hz, hz):
                    c = _quat_rot(wq, (sx, sy, szc))
                    corners.append((wp[0] + c[0], wp[1] + c[1], wp[2] + c[2]))
        aabb = (
            min(c[0] for c in corners),
            max(c[0] for c in corners),
            min(c[1] for c in corners),
            max(c[1] for c in corners),
            min(c[2] for c in corners),
            max(c[2] for c in corners),
        )
        return lp, wp, sz, aabb

    def _walk(
        self, parent: ET.Element, parent_name: str, p_pos: Vec3, p_quat: Quat
    ) -> None:
        for child in list(parent):
            if child.tag == "geom":
                lp, wp, sz, aabb = self._geom_aabb(child, p_pos, p_quat)
                gname = child.attrib.get("name", "")
                ginfo = GeomInfo(
                    element=child,
                    name=gname,
                    parent_body=parent_name,
                    gtype=child.attrib.get("type", "sphere"),
                    local_pos=lp,
                    world_pos=wp,
                    size=sz,
                    aabb=aabb,
                )
                self.geoms.append(ginfo)
                if gname:
                    self.geoms_by_name[gname] = ginfo
                if parent_name in self.bodies:
                    self.bodies[parent_name].geoms.append(ginfo)
            elif child.tag == "body":
                bname = child.attrib.get("name", "")
                bp_list = _parse_floats(child.attrib.get("pos"), [0.0, 0.0, 0.0])
                bp_rot = _quat_rot(p_quat, (bp_list[0], bp_list[1], bp_list[2]))
                wpos = (p_pos[0] + bp_rot[0], p_pos[1] + bp_rot[1], p_pos[2] + bp_rot[2])
                wquat = _quat_mul(p_quat, _elem_local_quat(child, self.eulerseq, self.is_degree))
                binfo = BodyInfo(
                    element=child,
                    name=bname,
                    parent_name=parent_name,
                    world_pos=wpos,
                    world_quat=wquat,
                )
                for j in child.findall("joint"):
                    ax = _parse_floats(j.attrib.get("axis"), [0.0, 0.0, 1.0])
                    jr_vals = _parse_floats(j.attrib.get("range"))
                    jr = (jr_vals[0], jr_vals[1]) if len(jr_vals) == 2 else None
                    binfo.joints.append(
                        JointInfo(
                            element=j,
                            name=j.attrib.get("name", ""),
                            jtype=j.attrib.get("type", "hinge"),
                            axis=(ax[0], ax[1], ax[2]),
                            jrange=jr,
                        )
                    )
                if bname:
                    self.bodies[bname] = binfo
                self._walk(child, bname or parent_name, wpos, wquat)

    def joint_range(
        self, body_name: str, joint_name: Optional[str], default: Tuple[float, float]
    ) -> Tuple[float, float]:
        b = self.bodies.get(body_name)
        if not b:
            return default
        for j in b.joints:
            if (joint_name is None or j.name == joint_name) and j.jrange is not None:
                return j.jrange
        return default

    def geom_aabb_or(self, geom_name: str, default: AABB) -> AABB:
        g = self.geoms_by_name.get(geom_name)
        return g.aabb if g is not None else default

    def body_elem(self, body_name: str) -> Optional[ET.Element]:
        b = self.bodies.get(body_name)
        return b.element if b is not None else None


# ---------------------------------------------------------------------------
# Fabrication Builder (Assets, Meshes, Primitives, Mechanical Sub-Assemblies)
# ---------------------------------------------------------------------------

class MachineBuilder:
    """Builds grounded, visual-only industrial hardware inside a MuJoCo XML tree."""

    def __init__(self, root: ET.Element, case_id: int) -> None:
        self.root = root
        self.case_id = case_id
        self.index = SceneIndex(root)
        self.used_names: Set[str] = set(self.index.existing_names)
        self.worldbody = self._ensure_worldbody()
        self.asset = self._ensure_asset()
        self._mesh_cache: Dict[str, str] = {}
        self._counters: Dict[str, int] = {}
        self.inventory: Dict[str, object] = {
            "case_id": case_id,
            "case_name": CASE_NAMES[case_id],
            "materials": [],
            "meshes": [],
            "assemblies": [],
            "geoms_added": 0,
        }
        self._pbr = _supports_pbr_attrs()

    def _ensure_worldbody(self) -> ET.Element:
        wb = self.root.find("worldbody")
        if wb is None:
            wb = ET.SubElement(self.root, "worldbody")
        return wb

    def _ensure_asset(self) -> ET.Element:
        asset = self.root.find("asset")
        if asset is None:
            asset = ET.Element("asset")
            wb_idx = list(self.root).index(self.worldbody)
            self.root.insert(wb_idx, asset)
        return asset

    def unique_name(self, prefix: str) -> str:
        base = _ascii_slug(prefix)
        if base not in self.used_names:
            self.used_names.add(base)
            return base
        n = self._counters.get(base, 1)
        while f"{base}_{n}" in self.used_names:
            n += 1
        self._counters[base] = n + 1
        name = f"{base}_{n}"
        self.used_names.add(name)
        return name

    def record_assembly(self, name: str, parent: str, role: str) -> None:
        cast_list = self.inventory["assemblies"]
        assert isinstance(cast_list, list)
        cast_list.append({"name": name, "parent": parent, "role": role})

    # -- Materials & Textures ------------------------------------------------

    def ensure_materials(self) -> None:
        textures = [
            (
                "fabricated_tex_floor",
                {
                    "type": "2d",
                    "builtin": "checker",
                    "rgb1": "0.35 0.36 0.37",
                    "rgb2": "0.32 0.33 0.34",
                    "mark": "edge",
                    "markrgb": "0.24 0.25 0.26",
                    "width": "512",
                    "height": "512",
                },
            ),
            (
                "fabricated_tex_wall",
                {
                    "type": "2d",
                    "builtin": "checker",
                    "rgb1": "0.56 0.57 0.58",
                    "rgb2": "0.54 0.55 0.56",
                    "mark": "edge",
                    "markrgb": "0.45 0.46 0.48",
                    "width": "256",
                    "height": "256",
                },
            ),
            (
                "fabricated_tex_machined",
                {
                    "type": "2d",
                    "builtin": "gradient",
                    "rgb1": "0.66 0.68 0.71",
                    "rgb2": "0.55 0.57 0.60",
                    "width": "256",
                    "height": "256",
                },
            ),
            (
                "fabricated_tex_hazard",
                {
                    "type": "2d",
                    "builtin": "checker",
                    "rgb1": "0.70 0.50 0.14",
                    "rgb2": "0.16 0.17 0.19",
                    "width": "128",
                    "height": "128",
                },
            ),
        ]
        for tname, attrs in textures:
            if tname not in self.used_names:
                el = ET.SubElement(self.asset, "texture", {"name": tname, **attrs})
                self.used_names.add(tname)
                _ = el

        # Industrial material palette (muted real engineering materials, no bright primaries)
        mat_specs = [
            (
                "fabricated_brushed_steel",
                "0.68 0.70 0.73 1",
                0.72,
                0.62,
                0.08,
                0.82,
                0.32,
                {"texture": "fabricated_tex_machined", "texuniform": "true", "texrepeat": "2 2"},
            ),
            (
                "fabricated_machined_aluminum",
                "0.73 0.75 0.78 1",
                0.76,
                0.68,
                0.10,
                0.86,
                0.28,
                {},
            ),
            (
                "fabricated_cast_iron",
                "0.22 0.24 0.26 1",
                0.32,
                0.26,
                0.03,
                0.55,
                0.62,
                {},
            ),
            (
                "fabricated_powder_enamel",
                "0.25 0.30 0.35 1",
                0.45,
                0.42,
                0.04,
                0.22,
                0.44,
                {},
            ),
            (
                "fabricated_powder_enamel_light",
                "0.68 0.70 0.71 1",
                0.45,
                0.40,
                0.04,
                0.16,
                0.42,
                {},
            ),
            (
                "fabricated_bearing",
                "0.80 0.82 0.85 1",
                0.90,
                0.86,
                0.18,
                0.93,
                0.15,
                {},
            ),
            (
                "fabricated_black_oxide",
                "0.15 0.16 0.18 1",
                0.48,
                0.44,
                0.05,
                0.68,
                0.38,
                {},
            ),
            (
                "fabricated_anodized_dark",
                "0.24 0.26 0.29 1",
                0.58,
                0.54,
                0.06,
                0.76,
                0.34,
                {},
            ),
            (
                "fabricated_rubber_pad",
                "0.14 0.14 0.15 1",
                0.10,
                0.08,
                0.0,
                0.02,
                0.88,
                {},
            ),
            (
                "fabricated_brass_bushing",
                "0.64 0.50 0.26 1",
                0.72,
                0.62,
                0.09,
                0.84,
                0.32,
                {},
            ),
            (
                "fabricated_safety_amber",
                "0.72 0.43 0.13 1",
                0.42,
                0.38,
                0.03,
                0.18,
                0.44,
                {},
            ),
            (
                "fabricated_safety_crimson",
                "0.56 0.14 0.14 1",
                0.42,
                0.38,
                0.03,
                0.16,
                0.42,
                {},
            ),
            (
                "fabricated_polycarbonate",
                "0.74 0.80 0.84 0.30",
                0.85,
                0.80,
                0.12,
                0.05,
                0.12,
                {},
            ),
            (
                "fabricated_delrin_guide",
                "0.82 0.82 0.79 1",
                0.30,
                0.28,
                0.02,
                0.02,
                0.42,
                {},
            ),
            (
                "fabricated_hospital_enamel",
                "0.78 0.80 0.81 1",
                0.44,
                0.40,
                0.04,
                0.18,
                0.36,
                {},
            ),
            (
                "fabricated_warm_timber",
                "0.47 0.35 0.23 1",
                0.18,
                0.15,
                0.01,
                0.02,
                0.66,
                {},
            ),
            (
                "fabricated_shop_floor",
                "0.88 0.88 0.88 1",
                0.22,
                0.20,
                0.04,
                0.05,
                0.70,
                {"texture": "fabricated_tex_floor", "texuniform": "true", "texrepeat": "1.2 1.2"},
            ),
            (
                "fabricated_shop_wall",
                "0.92 0.92 0.92 1",
                0.14,
                0.12,
                0.01,
                0.02,
                0.78,
                {"texture": "fabricated_tex_wall", "texuniform": "true", "texrepeat": "0.8 0.8"},
            ),
            (
                "fabricated_hazard_stripe",
                "0.92 0.92 0.92 1",
                0.22,
                0.18,
                0.01,
                0.05,
                0.56,
                {"texture": "fabricated_tex_hazard", "texuniform": "true", "texrepeat": "6 1"},
            ),
        ]

        mat_list = self.inventory["materials"]
        assert isinstance(mat_list, list)
        for mname, rgba, spec, shin, refl, metal, rough, extra in mat_specs:
            if mname not in self.used_names:
                attrs: Dict[str, str] = {
                    "name": mname,
                    "rgba": rgba,
                    "specular": _fmt(spec),
                    "shininess": _fmt(shin),
                    "reflectance": _fmt(refl),
                    **extra,
                }
                if self._pbr:
                    attrs["metallic"] = _fmt(metal)
                    attrs["roughness"] = _fmt(rough)
                ET.SubElement(self.asset, "material", attrs)
                self.used_names.add(mname)
                mat_list.append(mname)

    def upgrade_architectural_surfaces(self) -> None:
        """Give plain static floor/wall planes textured industrial material detail."""
        existing_mat_textures: Set[str] = set()
        for m in self.asset.findall("material"):
            if m.attrib.get("texture"):
                nm = m.attrib.get("name")
                if nm:
                    existing_mat_textures.add(nm)

        for g in self.index.geoms:
            if g.parent_body != "worldbody":
                continue
            lname = g.name.lower()
            cur_mat = g.element.attrib.get("material", "")
            if cur_mat in existing_mat_textures:
                continue
            is_floor = g.gtype == "plane" and abs(g.world_pos[2]) < 0.02
            if is_floor or any(tok in lname for tok in ("floor", "ground", "slab")):
                g.element.attrib["material"] = "fabricated_shop_floor"
                g.element.attrib.pop("rgba", None)
            elif any(tok in lname for tok in ("wall", "backdrop", "partition")):
                g.element.attrib["material"] = "fabricated_shop_wall"
                g.element.attrib.pop("rgba", None)

    # -- Procedural Convex Meshes (positive volume, auto-outward normals) ----

    def _register_mesh(self, key: str, verts: Sequence[Vec3]) -> str:
        if key in self._mesh_cache:
            return self._mesh_cache[key]
        mname = self.unique_name(f"fab_mesh_{key}")
        vstr = " ".join(f"{_fmt(x)} {_fmt(y)} {_fmt(z)}" for x, y, z in verts)
        ET.SubElement(self.asset, "mesh", {"name": mname, "vertex": vstr})
        self._mesh_cache[key] = mname
        mesh_list = self.inventory["meshes"]
        assert isinstance(mesh_list, list)
        mesh_list.append(mname)
        return mname

    def mesh_chamfered_box(
        self, hx: float, hy: float, hz: float, bevel: float = 0.008
    ) -> str:
        b = min(bevel, 0.32 * hx, 0.32 * hy, 0.32 * hz)
        b = max(b, 1e-4)
        key = f"cbox_{_fmt(hx)}_{_fmt(hy)}_{_fmt(hz)}_{_fmt(b)}"
        verts: List[Vec3] = []
        for sx in (-1.0, 1.0):
            for sy in (-1.0, 1.0):
                for sz in (-1.0, 1.0):
                    verts.append((sx * (hx - b), sy * (hy - b), sz * hz))
                    verts.append((sx * hx, sy * (hy - b), sz * (hz - b)))
                    verts.append((sx * (hx - b), sy * hy, sz * (hz - b)))
        return self._register_mesh(key, verts)

    def mesh_tapered_base(
        self, bx: float, by: float, tx: float, ty: float, h: float
    ) -> str:
        key = f"tbase_{_fmt(bx)}_{_fmt(by)}_{_fmt(tx)}_{_fmt(ty)}_{_fmt(h)}"
        verts = [
            (-bx, -by, 0.0),
            (bx, -by, 0.0),
            (bx, by, 0.0),
            (-bx, by, 0.0),
            (-tx, -ty, h),
            (tx, -ty, h),
            (tx, ty, h),
            (-tx, ty, h),
        ]
        return self._register_mesh(key, verts)

    def mesh_gusset(self, plane: str, la: float, lb: float, half_t: float) -> str:
        """Welded right-triangle gusset plate with weld-relief cropped tips."""
        sa = 1.0 if la >= 0.0 else -1.0
        sb = 1.0 if lb >= 0.0 else -1.0
        ta = sa * min(abs(la) * 0.18, 0.010)
        tb = sb * min(abs(lb) * 0.18, 0.010)
        pts2d = [(0.0, 0.0), (la, 0.0), (la, tb), (ta, lb), (0.0, lb)]
        verts: List[Vec3] = []
        for t in (-half_t, half_t):
            for a, b in pts2d:
                if plane == "xz":
                    verts.append((a, t, b))
                elif plane == "yz":
                    verts.append((t, a, b))
                else:  # xy
                    verts.append((a, b, t))
        key = f"gus_{plane}_{_fmt(la)}_{_fmt(lb)}_{_fmt(half_t)}"
        return self._register_mesh(key, verts)

    def mesh_hex_head(self, radius: float, height: float) -> str:
        key = f"hex_{_fmt(radius)}_{_fmt(height)}"
        verts: List[Vec3] = []
        for z in (0.0, height):
            for i in range(6):
                ang = i * (math.pi / 3.0)
                verts.append((radius * math.cos(ang), radius * math.sin(ang), z))
        return self._register_mesh(key, verts)

    # -- Visual-Only Geom Emitters -------------------------------------------

    def _base_attrs(self, tag: str, gtype: str, mat: str) -> Dict[str, str]:
        self.inventory["geoms_added"] = int(self.inventory["geoms_added"]) + 1
        return {
            "name": self.unique_name(f"fab_{self.case_id:02d}_{tag}"),
            "type": gtype,
            "material": mat,
            "contype": "0",
            "conaffinity": "0",
            "group": "2",
            "mass": "0",
        }

    def add_box(
        self,
        parent: ET.Element,
        tag: str,
        pos: Vec3,
        size: Vec3,
        mat: str,
        quat: Optional[Quat] = None,
    ) -> ET.Element:
        attrs = self._base_attrs(tag, "box", mat)
        attrs["pos"] = _fmt_vec(pos)
        attrs["size"] = _fmt_vec((max(size[0], 1e-4), max(size[1], 1e-4), max(size[2], 1e-4)))
        if quat is not None:
            attrs["quat"] = _fmt_vec(_quat_norm(quat))
        return ET.SubElement(parent, "geom", attrs)

    def add_beveled_box(
        self,
        parent: ET.Element,
        tag: str,
        pos: Vec3,
        size: Vec3,
        mat: str,
        bevel: float = 0.008,
        quat: Optional[Quat] = None,
    ) -> ET.Element:
        mname = self.mesh_chamfered_box(
            max(size[0], 1e-3), max(size[1], 1e-3), max(size[2], 1e-3), bevel
        )
        return self.add_mesh_geom(parent, tag, mname, pos, mat, quat=quat)

    def add_mesh_geom(
        self,
        parent: ET.Element,
        tag: str,
        mesh_name: str,
        pos: Vec3,
        mat: str,
        quat: Optional[Quat] = None,
    ) -> ET.Element:
        attrs = self._base_attrs(tag, "mesh", mat)
        attrs["mesh"] = mesh_name
        attrs["pos"] = _fmt_vec(pos)
        if quat is not None:
            attrs["quat"] = _fmt_vec(_quat_norm(quat))
        return ET.SubElement(parent, "geom", attrs)

    def add_cyl(
        self,
        parent: ET.Element,
        tag: str,
        pos: Vec3,
        radius: float,
        half_len: float,
        mat: str,
        quat: Optional[Quat] = None,
    ) -> ET.Element:
        attrs = self._base_attrs(tag, "cylinder", mat)
        attrs["pos"] = _fmt_vec(pos)
        attrs["size"] = _fmt_vec((max(radius, 1e-4), max(half_len, 1e-4)))
        if quat is not None:
            attrs["quat"] = _fmt_vec(_quat_norm(quat))
        return ET.SubElement(parent, "geom", attrs)

    def add_rod(
        self,
        parent: ET.Element,
        tag: str,
        p1: Vec3,
        p2: Vec3,
        radius: float,
        mat: str,
        capsule: bool = False,
    ) -> Optional[ET.Element]:
        dx, dy, dz = p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]
        if math.sqrt(dx * dx + dy * dy + dz * dz) < 2e-4:
            return None
        attrs = self._base_attrs(tag, "capsule" if capsule else "cylinder", mat)
        attrs["fromto"] = _fmt_vec((p1[0], p1[1], p1[2], p2[0], p2[1], p2[2]))
        attrs["size"] = _fmt(max(radius, 1e-4))
        return ET.SubElement(parent, "geom", attrs)

    def add_sphere(
        self, parent: ET.Element, tag: str, pos: Vec3, radius: float, mat: str
    ) -> ET.Element:
        attrs = self._base_attrs(tag, "sphere", mat)
        attrs["pos"] = _fmt_vec(pos)
        attrs["size"] = _fmt(max(radius, 1e-4))
        return ET.SubElement(parent, "geom", attrs)

    # -- Reusable Mechanical Sub-Assemblies ----------------------------------

    def add_bolt_array(
        self,
        parent: ET.Element,
        tag: str,
        centers: Sequence[Vec3],
        radius: float = 0.008,
        height: float = 0.006,
        mat: str = "fabricated_black_oxide",
    ) -> None:
        m_hex = self.mesh_hex_head(radius, height)
        for i, (bx, by, bz) in enumerate(centers):
            self.add_cyl(
                parent,
                f"{tag}_wash_{i}",
                (bx, by, bz + 0.001),
                radius * 1.45,
                0.001,
                "fabricated_brushed_steel",
            )
            self.add_mesh_geom(parent, f"{tag}_hex_{i}", m_hex, (bx, by, bz + 0.002), mat)

    def add_floor_anchor_plate(
        self,
        parent: ET.Element,
        tag: str,
        x: float,
        y: float,
        hx: float,
        hy: float,
        plate_h: float = 0.014,
        mat: str = "fabricated_cast_iron",
    ) -> None:
        # Neoprene isolation shim (z=0..0.003) + beveled cast baseplate (z=0.003..plate_h)
        self.add_box(
            parent,
            f"{tag}_shim",
            (x, y, 0.0015),
            (hx + 0.003, hy + 0.003, 0.0015),
            "fabricated_rubber_pad",
        )
        m_base = self.mesh_tapered_base(hx, hy, max(hx - 0.004, hx * 0.88), max(hy - 0.004, hy * 0.88), plate_h - 0.003)
        self.add_mesh_geom(parent, f"{tag}_plate", m_base, (x, y, 0.003), mat)
        bx_off = max(hx - 0.018, hx * 0.55)
        by_off = max(hy - 0.018, hy * 0.55)
        self.add_bolt_array(
            parent,
            f"{tag}_bolt",
            [
                (x - bx_off, y - by_off, plate_h),
                (x + bx_off, y - by_off, plate_h),
                (x - bx_off, y + by_off, plate_h),
                (x + bx_off, y + by_off, plate_h),
            ],
            radius=min(0.0085, min(hx, hy) * 0.16),
            height=0.006,
        )

    def add_grounded_column(
        self,
        parent: ET.Element,
        tag: str,
        x: float,
        y: float,
        z_top: float,
        hx: float,
        hy: float,
        mat: str = "fabricated_powder_enamel",
        plate_pad: float = 0.032,
        gussets: bool = True,
        top_flange: bool = True,
    ) -> None:
        plate_h = 0.014
        flange_h = 0.012 if top_flange and z_top > 0.12 else 0.0
        self.add_floor_anchor_plate(parent, f"{tag}_foot", x, y, hx + plate_pad, hy + plate_pad, plate_h)
        col_z1 = plate_h
        col_z2 = max(z_top - flange_h, col_z1 + 0.01)
        self.add_beveled_box(
            parent,
            f"{tag}_post",
            (x, y, 0.5 * (col_z1 + col_z2)),
            (hx, hy, 0.5 * (col_z2 - col_z1)),
            mat,
            bevel=min(0.005, hx * 0.25, hy * 0.25),
        )
        if flange_h > 0.0:
            self.add_beveled_box(
                parent,
                f"{tag}_cap",
                (x, y, z_top - 0.5 * flange_h),
                (hx + 0.018, hy + 0.018, 0.5 * flange_h),
                "fabricated_cast_iron",
                bevel=0.003,
            )
        if gussets and z_top > 0.16:
            g_h = min(0.075, (col_z2 - col_z1) * 0.35)
            g_w = max(plate_pad - 0.006, 0.020)
            for sx in (-1.0, 1.0):
                m = self.mesh_gusset("xz", sx * g_w, g_h, 0.004)
                self.add_mesh_geom(parent, f"{tag}_gx_{int(sx+1)}", m, (x + sx * hx, y, plate_h), "fabricated_cast_iron")
            for sy in (-1.0, 1.0):
                m = self.mesh_gusset("yz", sy * g_w, g_h, 0.004)
                self.add_mesh_geom(parent, f"{tag}_gy_{int(sy+1)}", m, (x, y + sy * hy, plate_h), "fabricated_cast_iron")

    def add_table_frame(
        self,
        parent: ET.Element,
        tag: str,
        xmin: float,
        xmax: float,
        ymin: float,
        ymax: float,
        z_under: float,
        leg_xs: Sequence[float],
        leg_ys: Sequence[float],
        mat: str = "fabricated_powder_enamel",
        apron_h: float = 0.042,
        leg_r: float = 0.024,
        brace_z: Optional[float] = 0.16,
        knee_targets: Sequence[Tuple[float, float, float, float]] = (),
        plate_pad: float = 0.028,
    ) -> None:
        """Welded steel perimeter apron meeting z_under + grounded legs + H-braces + knees."""
        cx = 0.5 * (xmin + xmax)
        cy = 0.5 * (ymin + ymax)
        ap_z = z_under - 0.5 * apron_h
        inset = 0.024
        ax1, ax2 = xmin + inset, xmax - inset
        ay1, ay2 = ymin + inset, ymax - inset

        # Welded perimeter apron channel meeting underside cleanly at z_under
        if ax2 > ax1 + 0.02 and ay2 > ay1 + 0.02:
            for sy, yy in (("n", ay2 - 0.014), ("s", ay1 + 0.014)):
                self.add_box(
                    parent,
                    f"{tag}_apron_{sy}",
                    (cx, yy, ap_z),
                    (0.5 * (ax2 - ax1), 0.014, 0.5 * apron_h),
                    mat,
                )
            for sx, xx in (("w", ax1 + 0.014), ("e", ax2 - 0.014)):
                self.add_box(
                    parent,
                    f"{tag}_apron_{sx}",
                    (xx, cy, ap_z),
                    (0.014, max(0.5 * (ay2 - ay1) - 0.028, 0.01), 0.5 * apron_h),
                    mat,
                )
            # Mid under-deck support rib
            self.add_box(
                parent,
                f"{tag}_mid_rib",
                (cx, cy, ap_z),
                (0.014, max(0.5 * (ay2 - ay1) - 0.028, 0.01), 0.5 * apron_h),
                mat,
            )

        # Grounded legs + welded brackets meeting z_under
        for ix, lx in enumerate(leg_xs):
            for iy, ly in enumerate(leg_ys):
                self.add_grounded_column(
                    parent,
                    f"{tag}_leg_{ix}_{iy}",
                    lx,
                    ly,
                    z_under,
                    leg_r,
                    leg_r,
                    mat=mat,
                    plate_pad=plate_pad,
                    gussets=(z_under > 0.22),
                    top_flange=True,
                )
                # Welded top gussets meeting apron underside
                if z_under > 0.20:
                    gw = min(0.065, 0.35 * (z_under - apron_h))
                    sx = 1.0 if lx < cx else -1.0
                    m = self.mesh_gusset("xz", sx * gw, -gw, 0.004)
                    self.add_mesh_geom(
                        parent,
                        f"{tag}_tgus_{ix}_{iy}",
                        m,
                        (lx + sx * leg_r, ly, z_under - apron_h),
                        "fabricated_cast_iron",
                    )

        # Lower cross-tie braces between legs
        if brace_z is not None and 0.04 < brace_z < z_under - apron_h - 0.04:
            if len(leg_ys) >= 2:
                y_lo, y_hi = min(leg_ys), max(leg_ys)
                for ix, lx in enumerate(leg_xs):
                    self.add_box(
                        parent,
                        f"{tag}_ybrace_{ix}",
                        (lx, 0.5 * (y_lo + y_hi), brace_z),
                        (0.014, max(0.5 * (y_hi - y_lo) - leg_r, 0.01), 0.014),
                        mat,
                    )
            if len(leg_xs) >= 2:
                x_lo, x_hi = min(leg_xs), max(leg_xs)
                self.add_box(
                    parent,
                    f"{tag}_xbrace_c",
                    (0.5 * (x_lo + x_hi), cy, brace_z),
                    (max(0.5 * (x_hi - x_lo) - leg_r, 0.01), 0.016, 0.014),
                    mat,
                )

        # Optional diagonal cantilever knee braces: (leg_x, target_x, y, z_start)
        for idx, (lx, tx, ky, kz) in enumerate(knee_targets):
            self.add_rod(
                parent,
                f"{tag}_knee_{idx}",
                (lx, ky, kz),
                (tx, ky, z_under - 0.010),
                0.016,
                mat,
            )
            self.add_beveled_box(
                parent,
                f"{tag}_knee_pad_{idx}",
                (tx, ky, z_under - 0.008),
                (0.028, 0.024, 0.008),
                "fabricated_cast_iron",
                bevel=0.002,
            )

    def add_swivel_caster(
        self,
        parent: ET.Element,
        tag: str,
        x: float,
        y: float,
        z_mount: float,
        roll_axis: str = "x",
        wheel_r: float = 0.046,
        wheel_w: float = 0.026,
        z_floor: float = 0.0,
    ) -> None:
        """Grounded industrial swivel caster meeting z_mount above and z_floor below."""
        avail = z_mount - z_floor
        r = min(wheel_r, max(0.022, 0.42 * avail))
        wc_z = z_floor + r
        hw = 0.5 * wheel_w

        # Bolted top mounting plate meeting z_mount
        plate_h = 0.008
        self.add_beveled_box(
            parent,
            f"{tag}_mplate",
            (x, y, z_mount - 0.5 * plate_h),
            (0.036, 0.036, 0.5 * plate_h),
            "fabricated_brushed_steel",
            bevel=0.002,
        )
        # Swivel bearing race
        race_bot = max(wc_z + r + 0.006, z_mount - plate_h - 0.016)
        race_top = z_mount - plate_h
        if race_top > race_bot + 0.002:
            self.add_cyl(
                parent,
                f"{tag}_race",
                (x, y, 0.5 * (race_bot + race_top)),
                0.022,
                0.5 * (race_top - race_bot),
                "fabricated_bearing",
            )
        # Fork crown + dual fork cheeks + axle + wheel
        crown_z = race_bot
        if roll_axis == "x":
            # Rolls along X -> axle along Y
            self.add_box(
                parent,
                f"{tag}_crown",
                (x, y, crown_z),
                (0.022, hw + 0.010, 0.005),
                "fabricated_brushed_steel",
            )
            for sy in (-1.0, 1.0):
                self.add_box(
                    parent,
                    f"{tag}_fork_{int(sy+1)}",
                    (x, y + sy * (hw + 0.006), 0.5 * (wc_z + crown_z)),
                    (0.016, 0.004, max(0.5 * (crown_z - wc_z) + 0.008, 0.012)),
                    "fabricated_brushed_steel",
                )
            self.add_rod(parent, f"{tag}_wheel", (x, y - hw, wc_z), (x, y + hw, wc_z), r, "fabricated_rubber_pad")
            self.add_rod(parent, f"{tag}_hub", (x, y - hw - 0.002, wc_z), (x, y + hw + 0.002, wc_z), r * 0.56, "fabricated_machined_aluminum")
            self.add_rod(parent, f"{tag}_axle", (x, y - hw - 0.012, wc_z), (x, y + hw + 0.012, wc_z), 0.007, "fabricated_black_oxide")
        else:
            # Rolls along Y -> axle along X
            self.add_box(
                parent,
                f"{tag}_crown",
                (x, y, crown_z),
                (hw + 0.010, 0.022, 0.005),
                "fabricated_brushed_steel",
            )
            for sx in (-1.0, 1.0):
                self.add_box(
                    parent,
                    f"{tag}_fork_{int(sx+1)}",
                    (x + sx * (hw + 0.006), y, 0.5 * (wc_z + crown_z)),
                    (0.004, 0.016, max(0.5 * (crown_z - wc_z) + 0.008, 0.012)),
                    "fabricated_brushed_steel",
                )
            self.add_rod(parent, f"{tag}_wheel", (x - hw, y, wc_z), (x + hw, y, wc_z), r, "fabricated_rubber_pad")
            self.add_rod(parent, f"{tag}_hub", (x - hw - 0.002, y, wc_z), (x + hw + 0.002, y, wc_z), r * 0.56, "fabricated_machined_aluminum")
            self.add_rod(parent, f"{tag}_axle", (x - hw - 0.012, y, wc_z), (x + hw + 0.012, y, wc_z), 0.007, "fabricated_black_oxide")

    def add_drive_wheel(
        self,
        parent: ET.Element,
        tag: str,
        x: float,
        y: float,
        z_mount: float,
        wheel_r: float = 0.082,
        wheel_w: float = 0.044,
    ) -> None:
        """Heavy traction drive wheel (rolls along X, axle along Y) grounded at z=0."""
        hw = 0.5 * wheel_w
        wc_z = wheel_r
        self.add_rod(parent, f"{tag}_tire", (x, y - hw, wc_z), (x, y + hw, wc_z), wheel_r, "fabricated_rubber_pad")
        self.add_rod(parent, f"{tag}_rim", (x, y - hw - 0.002, wc_z), (x, y + hw + 0.002, wc_z), wheel_r * 0.64, "fabricated_machined_aluminum")
        self.add_rod(parent, f"{tag}_hubcap", (x, y - hw - 0.005, wc_z), (x, y + hw + 0.005, wc_z), wheel_r * 0.26, "fabricated_black_oxide")
        # Suspension / motor-mount bracket connecting axle to chassis underside z_mount
        in_sign = -1.0 if y > 0.0 else 1.0
        mount_y = y + in_sign * (hw + 0.018)
        self.add_rod(parent, f"{tag}_shaft", (x, y, wc_z), (x, mount_y + in_sign * 0.025, wc_z), 0.014, "fabricated_bearing")
        if z_mount > wc_z + 0.01:
            self.add_beveled_box(
                parent,
                f"{tag}_clevis",
                (x, mount_y, 0.5 * (wc_z + z_mount)),
                (0.036, 0.016, 0.5 * (z_mount - wc_z) + 0.008),
                "fabricated_cast_iron",
                bevel=0.004,
            )

    def add_bollard(
        self,
        parent: ET.Element,
        tag: str,
        x: float,
        y: float,
        height: float = 0.94,
        radius: float = 0.042,
    ) -> None:
        self.add_floor_anchor_plate(parent, f"{tag}_base", x, y, radius + 0.048, radius + 0.048, 0.014)
        self.add_cyl(parent, f"{tag}_pipe", (x, y, 0.5 * (0.014 + height)), radius, 0.5 * (height - 0.014), "fabricated_powder_enamel")
        self.add_cyl(parent, f"{tag}_band_hi", (x, y, height - 0.14), radius + 0.002, 0.048, "fabricated_safety_amber")
        self.add_cyl(parent, f"{tag}_band_lo", (x, y, height - 0.28), radius + 0.002, 0.024, "fabricated_safety_amber")
        self.add_sphere(parent, f"{tag}_cap", (x, y, height), radius, "fabricated_cast_iron")

    def add_linear_rail_x(
        self,
        parent: ET.Element,
        tag: str,
        x1: float,
        x2: float,
        y: float,
        z: float,
        beam_hy: float = 0.030,
        beam_hz: float = 0.040,
        stand_xs: Sequence[float] = (),
        stand_y_shift: float = 0.0,
        rail_face: str = "+y",
        motor_end: str = "min",
    ) -> None:
        """Grounded extruded X-axis linear rail with twin chrome guides & stepper drive."""
        cx = 0.5 * (x1 + x2)
        hx = 0.5 * (x2 - x1)
        # Main machined aluminum extrusion beam
        self.add_beveled_box(
            parent, f"{tag}_beam", (cx, y, z), (hx, beam_hy, beam_hz), "fabricated_machined_aluminum", bevel=0.005
        )
        # Side T-slot groove accent strip on outward face
        out_sign = -1.0 if rail_face == "+y" else 1.0
        self.add_box(
            parent,
            f"{tag}_tslot",
            (cx, y + out_sign * (beam_hy + 0.001), z),
            (hx - 0.02, 0.002, 0.008),
            "fabricated_black_oxide",
        )
        # Twin hardened chrome profile guide rails + central ballscrew shaft
        in_sign = 1.0 if rail_face == "+y" else -1.0
        rail_y = y + in_sign * (beam_hy + 0.008)
        for sz_i, dz in (("top", beam_hz - 0.012), ("bot", -(beam_hz - 0.012))):
            self.add_box(
                parent,
                f"{tag}_guide_{sz_i}",
                (cx, rail_y, z + dz),
                (hx - 0.015, 0.008, 0.008),
                "fabricated_bearing",
            )
        self.add_rod(
            parent,
            f"{tag}_leadscrew",
            (x1 + 0.02, rail_y, z),
            (x2 - 0.02, rail_y, z),
            0.008,
            "fabricated_brushed_steel",
        )
        # End-stop pillow blocks
        for ename, ex in (("min", x1), ("max", x2)):
            self.add_beveled_box(
                parent,
                f"{tag}_end_{ename}",
                (ex, y + in_sign * 0.005, z),
                (0.022, beam_hy + 0.014, beam_hz + 0.008),
                "fabricated_cast_iron",
                bevel=0.004,
            )
        # Stepper / servo motor & gearbox at drive end
        mx = x1 - 0.072 if motor_end == "min" else x2 + 0.072
        self.add_beveled_box(
            parent,
            f"{tag}_motor",
            (mx, y, z),
            (0.050, 0.036, 0.036),
            "fabricated_black_oxide",
            bevel=0.005,
        )
        self.add_rod(
            parent,
            f"{tag}_coupler",
            (mx + (0.050 if motor_end == "min" else -0.050), y, z),
            (x1 if motor_end == "min" else x2, y, z),
            0.018,
            "fabricated_machined_aluminum",
        )
        # Grounded floor stanchions supporting underside/back of rail beam
        sy = y + stand_y_shift
        for i, sx in enumerate(stand_xs):
            self.add_grounded_column(
                parent,
                f"{tag}_stand_{i}",
                sx,
                sy,
                z - beam_hz,
                0.028,
                0.028,
                mat="fabricated_powder_enamel",
                plate_pad=0.034,
                gussets=True,
                top_flange=True,
            )
            # Welded side saddle bracket wrapping from stanchion to rail beam
            if abs(stand_y_shift) > 0.004:
                self.add_beveled_box(
                    parent,
                    f"{tag}_sbracket_{i}",
                    (sx, 0.5 * (y + sy), z - beam_hz - 0.014),
                    (0.036, 0.5 * abs(stand_y_shift) + 0.030, 0.014),
                    "fabricated_cast_iron",
                    bevel=0.003,
                )
            # Back clamping strap
            self.add_beveled_box(
                parent,
                f"{tag}_clamp_{i}",
                (sx, y + out_sign * (beam_hy + 0.012), z),
                (0.034, 0.012, beam_hz + 0.012),
                "fabricated_anodized_dark",
                bevel=0.003,
            )

    def add_linear_rail_y(
        self,
        parent: ET.Element,
        tag: str,
        y1: float,
        y2: float,
        x: float,
        z: float,
        beam_hx: float = 0.026,
        beam_hz: float = 0.028,
        stand_ys: Sequence[float] = (),
        motor_end: str = "max",
    ) -> None:
        """Grounded extruded Y-axis linear rail with top chrome profile guide & stands."""
        cy = 0.5 * (y1 + y2)
        hy = 0.5 * (y2 - y1)
        self.add_beveled_box(
            parent, f"{tag}_beam", (x, cy, z), (beam_hx, hy, beam_hz), "fabricated_machined_aluminum", bevel=0.004
        )
        # Hardened steel top linear guide rail
        rail_z = z + beam_hz + 0.007
        self.add_box(
            parent,
            f"{tag}_guide",
            (x, cy, rail_z),
            (0.012, hy - 0.016, 0.007),
            "fabricated_bearing",
        )
        # Parallel ballscrew drive rod tucked inside beam cheek
        self.add_rod(
            parent,
            f"{tag}_screw",
            (x, y1 + 0.02, z),
            (x, y2 - 0.02, z),
            0.007,
            "fabricated_brushed_steel",
        )
        # End-stop caps
        for ename, ey in (("min", y1), ("max", y2)):
            self.add_beveled_box(
                parent,
                f"{tag}_end_{ename}",
                (x, ey, z + 0.004),
                (beam_hx + 0.008, 0.018, beam_hz + 0.010),
                "fabricated_cast_iron",
                bevel=0.003,
            )
        if motor_end in ("min", "max"):
            my = y2 + 0.062 if motor_end == "max" else y1 - 0.062
            self.add_beveled_box(
                parent,
                f"{tag}_motor",
                (x, my, z),
                (0.030, 0.044, 0.030),
                "fabricated_black_oxide",
                bevel=0.004,
            )
        # Grounded floor stanchions directly beneath rail beam
        for i, sy in enumerate(stand_ys):
            self.add_grounded_column(
                parent,
                f"{tag}_stand_{i}",
                x,
                sy,
                z - beam_hz,
                0.024,
                0.024,
                mat="fabricated_powder_enamel",
                plate_pad=0.028,
                gussets=True,
                top_flange=True,
            )

    # -- Dynamic Grounding for Existing Franka Plinth, Pendant, Panels -------

    def ground_existing_plinth_and_controls(self) -> None:
        """Inspect root for existing Franka plinth, pendant, buttons & contact sensors.

        Adds non-overlapping external grounding flanges, gussets, rigid switch
        bezels, and anchored mounting brackets/pedestals without creating
        duplicate superposed surfaces or obstructing accessible controls.
        """
        hx, hy = FRANKA_PLINTH_HINT
        plinth_boxes: List[AABB] = []
        control_geoms: List[GeomInfo] = []

        control_keywords = (
            "pendant",
            "panel",
            "button",
            "estop",
            "e_stop",
            "switch",
            "control",
            "console",
            "contact_sensor",
            "touch_sensor",
            "pushbutton",
            "hmi",
            "keypad",
        )
        plinth_keywords = ("plinth", "pedestal", "robot_base", "franka_base", "panda_base", "robot_stand")

        for g in self.index.geoms:
            if g.gtype == "plane":
                continue
            lname = f"{g.parent_body}_{g.name}".lower()
            cx = 0.5 * (g.aabb[0] + g.aabb[1])
            cy = 0.5 * (g.aabb[2] + g.aabb[3])
            dist_hint = math.hypot(cx - hx, cy - hy)
            dx = g.aabb[1] - g.aabb[0]
            dy = g.aabb[3] - g.aabb[2]
            dz = g.aabb[5] - g.aabb[4]

            if any(k in lname for k in control_keywords):
                control_geoms.append(g)
                continue

            # Detect plinth by name or solid pedestal footprint near (-1.45, -1.13)
            if any(k in lname for k in plinth_keywords) or (
                g.parent_body == "worldbody"
                and dist_hint < 0.55
                and g.aabb[4] < 0.25
                and dz > 0.30
                and max(dx, dy) < 1.10
            ):
                plinth_boxes.append(g.aabb)
                continue

            # Detect small elevated unnamed/generic button/pendant boxes near the plinth
            if (
                g.parent_body == "worldbody"
                and dist_hint < 0.85
                and g.aabb[4] > 0.40
                and max(dx, dy, dz) < 0.38
            ):
                control_geoms.append(g)

        plinth_aabb = _aabb_union(plinth_boxes)
        if plinth_aabb is not None:
            px1, px2, py1, py2, pz1, pz2 = plinth_aabb
            pcx, pcy = 0.5 * (px1 + px2), 0.5 * (py1 + py2)
            phx, phy = 0.5 * (px2 - px1), 0.5 * (py2 - py1)
            # External floor anchor collar extending 0.05 m beyond actual plinth footprint (no superposed faces)
            flange_h = 0.015
            pad = 0.052
            for side, pos, sz in (
                ("s", (pcx, py1 - 0.5 * pad - 0.002, 0.5 * flange_h), (phx + pad, 0.5 * pad, 0.5 * flange_h)),
                ("n", (pcx, py2 + 0.5 * pad + 0.002, 0.5 * flange_h), (phx + pad, 0.5 * pad, 0.5 * flange_h)),
                ("w", (px1 - 0.5 * pad - 0.002, pcy, 0.5 * flange_h), (0.5 * pad, phy + 0.002, 0.5 * flange_h)),
                ("e", (px2 + 0.5 * pad + 0.002, pcy, 0.5 * flange_h), (0.5 * pad, phy + 0.002, 0.5 * flange_h)),
            ):
                self.add_beveled_box(self.worldbody, f"plinth_flange_{side}", pos, sz, "fabricated_cast_iron", bevel=0.003)

            # Anchor bolts at outer corners
            bolt_x = phx + 0.55 * pad
            bolt_y = phy + 0.55 * pad
            self.add_bolt_array(
                self.worldbody,
                "plinth_anchor",
                [
                    (pcx - bolt_x, pcy - bolt_y, flange_h),
                    (pcx + bolt_x, pcy - bolt_y, flange_h),
                    (pcx - bolt_x, pcy + bolt_y, flange_h),
                    (pcx + bolt_x, pcy + bolt_y, flange_h),
                ],
                radius=0.010,
                height=0.008,
            )

            # Proud welded corner gussets outside plinth perimeter (+0.002 m clearance)
            g_h = min(0.11, max(0.05, (pz2 - pz1) * 0.25))
            for sx in (-1.0, 1.0):
                mx = self.mesh_gusset("xz", sx * (pad - 0.008), g_h, 0.005)
                self.add_mesh_geom(
                    self.worldbody,
                    f"plinth_gus_x_{int(sx+1)}",
                    mx,
                    (pcx + sx * (phx + 0.002), pcy, flange_h),
                    "fabricated_cast_iron",
                )
            for sy in (-1.0, 1.0):
                my = self.mesh_gusset("yz", sy * (pad - 0.008), g_h, 0.005)
                self.add_mesh_geom(
                    self.worldbody,
                    f"plinth_gus_y_{int(sy+1)}",
                    my,
                    (pcx, pcy + sy * (phy + 0.002), flange_h),
                    "fabricated_cast_iron",
                )

            # If plinth itself hovered slightly above floor, ground its underside with leveling pads
            if pz1 > 0.015:
                for ix, sx in enumerate((-0.78, 0.78)):
                    for iy, sy in enumerate((-0.78, 0.78)):
                        self.add_grounded_column(
                            self.worldbody,
                            f"plinth_foot_{ix}_{iy}",
                            pcx + sx * phx,
                            pcy + sy * phy,
                            pz1,
                            0.032,
                            0.032,
                            mat="fabricated_cast_iron",
                            plate_pad=0.020,
                            gussets=False,
                        )

            # External machined top edge collar framing the plinth crown (proud, non-overlapping)
            trim_h = 0.018
            for side, pos, sz in (
                ("s", (pcx, py1 - 0.008, pz2 - 0.5 * trim_h), (phx + 0.014, 0.007, 0.5 * trim_h)),
                ("n", (pcx, py2 + 0.008, pz2 - 0.5 * trim_h), (phx + 0.014, 0.007, 0.5 * trim_h)),
                ("w", (px1 - 0.008, pcy, pz2 - 0.5 * trim_h), (0.007, phy + 0.002, 0.5 * trim_h)),
                ("e", (px2 + 0.008, pcy, pz2 - 0.5 * trim_h), (0.007, phy + 0.002, 0.5 * trim_h)),
            ):
                self.add_box(self.worldbody, f"plinth_trim_{side}", pos, sz, "fabricated_brushed_steel")

            # Rear conduit bulkhead & floor cable gland routed away from workcell center (-X, -Y)
            self.add_beveled_box(
                self.worldbody,
                "plinth_jbox",
                (px1 - 0.042, py1 + 0.09, 0.14),
                (0.038, 0.062, 0.075),
                "fabricated_anodized_dark",
                bevel=0.005,
            )
            self.add_rod(
                self.worldbody,
                "plinth_conduit",
                (px1 - 0.042, py1 + 0.09, 0.070),
                (px1 - 0.042, py1 + 0.09, 0.012),
                0.014,
                "fabricated_rubber_pad",
            )
            self.record_assembly("franka_plinth_grounding", "worldbody", "external anchor flange, gussets & conduit")

        # Cluster nearby control/pendant/button/sensor geoms so detached caps share one rigid mount
        clusters: List[List[GeomInfo]] = []
        for cg in control_geoms:
            placed = False
            ccx, ccy, ccz = cg.world_pos
            for cl in clusters:
                rx, ry, rz = cl[0].world_pos
                if math.hypot(ccx - rx, ccy - ry) < 0.28 and abs(ccz - rz) < 0.30:
                    cl.append(cg)
                    placed = True
                    break
            if not placed:
                clusters.append([cg])

        for ci, cluster in enumerate(clusters):
            uaabb = _aabb_union([g.aabb for g in cluster])
            if uaabb is None:
                continue
            cx1, cx2, cy1, cy2, cz1, cz2 = uaabb
            ccx, ccy, ccz = 0.5 * (cx1 + cx2), 0.5 * (cy1 + cy2), 0.5 * (cz1 + cz2)
            chx, chy, chz = max(0.5 * (cx2 - cx1), 0.04), max(0.5 * (cy2 - cy1), 0.04), max(0.5 * (cz2 - cz1), 0.025)

            # Rigid machined backplate / bezel beneath the panel/buttons (never covers accessible top/front)
            bezel_z_top = cz1 - 0.001
            bezel_h = 0.020
            if bezel_z_top > 0.03:
                self.add_beveled_box(
                    self.worldbody,
                    f"ctrl_bezel_{ci}",
                    (ccx, ccy, bezel_z_top - 0.5 * bezel_h),
                    (chx + 0.016, chy + 0.016, 0.5 * bezel_h),
                    "fabricated_anodized_dark",
                    bevel=0.004,
                )
                mount_z = bezel_z_top - bezel_h
            else:
                mount_z = cz1

            # Connect to plinth via rigid welded swing-arm if adjacent, else dedicated floor pedestal
            connected_to_plinth = False
            if plinth_aabb is not None and mount_z > 0.12:
                px1, px2, py1, py2, pz1, pz2 = plinth_aabb
                pcx, pcy = 0.5 * (px1 + px2), 0.5 * (py1 + py2)
                dist_plinth = math.hypot(ccx - pcx, ccy - pcy)
                if dist_plinth < 0.65 and mount_z <= pz2 + 0.28:
                    # Clamp nearest point on plinth outer wall
                    ax = max(px1, min(px2, ccx))
                    ay = max(py1, min(py2, ccy))
                    az = min(max(mount_z - 0.12, pz1 + 0.14), pz2 - 0.06)
                    # Bolted flange plate on plinth side + rigid elbow arm to underside of pendant bezel
                    self.add_beveled_box(
                        self.worldbody,
                        f"ctrl_wallflange_{ci}",
                        (ax, ay, az),
                        (0.024, 0.024, 0.048),
                        "fabricated_cast_iron",
                        bevel=0.003,
                    )
                    self.add_rod(
                        self.worldbody,
                        f"ctrl_arm_h_{ci}",
                        (ax, ay, az),
                        (ccx, ccy, az),
                        0.018,
                        "fabricated_powder_enamel",
                        capsule=True,
                    )
                    self.add_rod(
                        self.worldbody,
                        f"ctrl_arm_v_{ci}",
                        (ccx, ccy, az),
                        (ccx, ccy, mount_z),
                        0.018,
                        "fabricated_powder_enamel",
                    )
                    self.add_beveled_box(
                        self.worldbody,
                        f"ctrl_head_{ci}",
                        (ccx, ccy, mount_z - 0.010),
                        (0.032, 0.032, 0.010),
                        "fabricated_cast_iron",
                        bevel=0.003,
                    )
                    connected_to_plinth = True
                    self.record_assembly(
                        f"control_swing_arm_{ci}", "worldbody", "plinth-mounted pendant/button bracket"
                    )

            if not connected_to_plinth and mount_z > 0.04:
                self.add_grounded_column(
                    self.worldbody,
                    f"ctrl_ped_{ci}",
                    ccx,
                    ccy,
                    mount_z,
                    0.024,
                    0.024,
                    mat="fabricated_powder_enamel",
                    plate_pad=0.045,
                    gussets=True,
                    top_flange=True,
                )
                self.record_assembly(
                    f"control_pedestal_{ci}", "worldbody", "floor-anchored control/sensor pedestal"
                )


# ---------------------------------------------------------------------------
# Case-Specific Mechanical Fabrication (01 .. 10)
# ---------------------------------------------------------------------------

def _fit_case_01_warehouse(b: MachineBuilder) -> None:
    """01_warehouse: Pedestrian crossing (AMR undercarriage + intersection guards)."""
    wb = b.worldbody

    # 1. Grounded AMR undercarriage (attached to 'amr' body so it rides with drive)
    amr = b.index.body_elem("amr")
    if amr is not None:
        # Chassis local AABB: x in [-0.36, 0.36], y in [-0.26, 0.26], z in [0.135, 0.305]
        z_bot, z_top = 0.135, 0.305
        # Central differential drive wheels (radius 0.082 -> bottom z=0.0)
        for sy_name, wy in (("l", 0.228), ("r", -0.228)):
            b.add_drive_wheel(amr, f"amr_drv_{sy_name}", 0.0, wy, z_bot, wheel_r=0.082, wheel_w=0.044)
        # Motor-gearbox transaxle tying both drive wheels beneath chassis
        b.add_rod(amr, "amr_transaxle", (0.0, -0.20, 0.082), (0.0, 0.20, 0.082), 0.026, "fabricated_cast_iron")
        b.add_beveled_box(amr, "amr_gearbox", (0.0, 0.0, 0.108), (0.068, 0.095, 0.028), "fabricated_anodized_dark", bevel=0.005)
        # 4 corner swivel caster wheels touching z=0.0
        for cx in (-0.27, 0.27):
            for cy in (-0.185, 0.185):
                tag = f"amr_cas_{'f' if cx > 0 else 'r'}_{'l' if cy > 0 else 'r'}"
                b.add_swivel_caster(amr, tag, cx, cy, z_bot, roll_axis="x", wheel_r=0.045, wheel_w=0.022)
        # Wrap-around elastomer bumper rail & recessed front/rear safety LiDAR bays
        for sy_name, by in (("l", 0.268), ("r", -0.268)):
            b.add_beveled_box(amr, f"amr_skirt_{sy_name}", (0.0, by, 0.165), (0.355, 0.008, 0.024), "fabricated_rubber_pad", bevel=0.003)
        for sx_name, bx in (("f", 0.366), ("r", -0.366)):
            b.add_beveled_box(amr, f"amr_lidar_hsg_{sx_name}", (bx, 0.0, 0.215), (0.016, 0.088, 0.044), "fabricated_anodized_dark", bevel=0.004)
            b.add_beveled_box(amr, f"amr_lidar_win_{sx_name}", (bx + (0.014 if bx > 0 else -0.014), 0.0, 0.215), (0.006, 0.072, 0.024), "fabricated_polycarbonate", bevel=0.002)
        # Top payload deck bevel rails, corner tie-downs & rear E-stop collar
        for sy_name, by in (("l", 0.245), ("r", -0.245)):
            b.add_beveled_box(amr, f"amr_rail_{sy_name}", (0.0, by, z_top + 0.012), (0.34, 0.014, 0.012), "fabricated_machined_aluminum", bevel=0.003)
        b.add_cyl(amr, "amr_estop_collar", (-0.31, 0.20, z_top + 0.018), 0.024, 0.018, "fabricated_safety_amber")
        b.add_cyl(amr, "amr_estop_cap", (-0.31, 0.20, z_top + 0.042), 0.019, 0.008, "fabricated_safety_crimson")
        b.record_assembly("amr_undercarriage", "amr", "2 drive wheels, 4 casters, LiDAR bays & bumper")

    # 2. Warehouse intersection safety bollards, guardrails & light curtains (clearing AMR y in [-0.42,0.42] and picker x in [-0.35,0.55])
    # 4 corner bollards framing the crossing
    corners = [
        ("nw", -0.48, 0.50),
        ("ne", 0.66, 0.50),
        ("sw", -0.48, -0.50),
        ("se", 0.66, -0.50),
    ]
    for cname, bx, by in corners:
        b.add_bollard(wb, f"wh_bol_{cname}", bx, by, height=0.94, radius=0.040)

    # Guardrail extensions along AMR lane (avoiding Franka plinth near (-1.45, -1.13))
    ext_posts = [
        ("nw_ext", -1.25, 0.50),
        ("ne_ext", 1.38, 0.50),
        ("sw_ext", -1.05, -0.50),
        ("se_ext", 1.38, -0.50),
    ]
    for ename, bx, by in ext_posts:
        b.add_bollard(wb, f"wh_bol_{ename}", bx, by, height=0.94, radius=0.038)

    rail_spans = [
        ("nw", (-1.25, 0.50), (-0.48, 0.50)),
        ("ne", (0.66, 0.50), (1.38, 0.50)),
        ("sw", (-1.05, -0.50), (-0.48, -0.50)),
        ("se", (0.66, -0.50), (1.38, -0.50)),
    ]
    for rname, (x1, y1), (x2, y2) in rail_spans:
        for rz_name, rz in (("hi", 0.86), ("mid", 0.46)):
            b.add_rod(wb, f"wh_rail_{rname}_{rz_name}", (x1, y1, rz), (x2, y2, rz), 0.022, "fabricated_safety_amber")
            for ep_i, (ex, ey) in enumerate(((x1, y1), (x2, y2))):
                b.add_cyl(wb, f"wh_fit_{rname}_{rz_name}_{ep_i}", (ex, ey, rz), 0.046, 0.026, "fabricated_cast_iron")

    # Twin optical crossing light-curtain stanchions on the pedestrian approach sides
    for sname, sx, sy in (("lc_wl", -0.52, 0.68), ("lc_wr", -0.52, -0.68), ("lc_el", 0.70, 0.68), ("lc_er", 0.70, -0.68)):
        b.add_grounded_column(wb, f"wh_{sname}", sx, sy, 1.44, 0.026, 0.026, mat="fabricated_anodized_dark", plate_pad=0.036, gussets=True)
        in_y = -0.028 if sy > 0 else 0.028
        b.add_box(wb, f"wh_{sname}_lens", (sx, sy + in_y, 0.78), (0.012, 0.004, 0.52), "fabricated_polycarbonate")
        b.add_cyl(wb, f"wh_{sname}_beacon", (sx, sy, 1.48), 0.024, 0.036, "fabricated_safety_amber")

    # Pedestrian crosswalk floor threshold strips (low-profile z=0..0.003, non-colliding)
    for si, sy in enumerate((-0.34, -0.17, 0.0, 0.17, 0.34)):
        b.add_box(wb, f"wh_xwalk_{si}", (0.09, sy, 0.0015), (0.34, 0.045, 0.0015), "fabricated_hazard_stripe")

    # Grounded AMR home charging / docking station behind start position (x=-2.22)
    b.add_grounded_column(wb, "wh_dock_post", -2.24, 0.0, 0.44, 0.055, 0.15, mat="fabricated_powder_enamel", plate_pad=0.040, gussets=True)
    b.add_beveled_box(wb, "wh_dock_face", (-2.18, 0.0, 0.21), (0.016, 0.11, 0.055), "fabricated_anodized_dark", bevel=0.003)
    for pi, py in enumerate((-0.055, 0.055)):
        b.add_beveled_box(wb, f"wh_dock_pad_{pi}", (-2.162, py, 0.21), (0.006, 0.026, 0.020), "fabricated_brass_bushing", bevel=0.002)
    b.record_assembly("warehouse_crossing_fixtures", "worldbody", "bollards, guardrails, light curtains & AMR dock")


def _fit_case_02_hospital(b: MachineBuilder) -> None:
    """02_hospital: Sliding hospital pocket door track/header + medical trolley structure."""
    wb = b.worldbody

    # 1. Grounded sliding door portal frame, pocket wall & overhead track (clears doorway x in [-0.48, 0.48])
    jamb_h = 2.02
    # Right strike jamb at x=+0.51 (inner face +0.476, clearing trolley width +/-0.29 by 186 mm)
    b.add_grounded_column(wb, "hosp_strike_jamb", 0.515, 0.0, jamb_h, 0.036, 0.068, mat="fabricated_brushed_steel", plate_pad=0.028, gussets=True, top_flange=False)
    b.add_box(wb, "hosp_strike_gasket", (0.476, 0.0, 0.96), (0.005, 0.028, 0.94), "fabricated_rubber_pad")
    b.add_beveled_box(wb, "hosp_latch_plate", (0.474, 0.0, 0.98), (0.004, 0.018, 0.085), "fabricated_machined_aluminum", bevel=0.001)

    # Left pocket partition frame (x in [-1.74, -0.50]) with split front/back walls at y=+/-0.084
    # Leaves clean 0.136 m internal pocket slot for 0.088 m-thick door leaf
    b.add_grounded_column(wb, "hosp_pocket_end", -1.73, 0.0, jamb_h, 0.038, 0.105, mat="fabricated_hospital_enamel", plate_pad=0.032, gussets=True, top_flange=False)
    for sy_name, py in (("front", -0.086), ("back", 0.086)):
        # Pocket mouth vertical stile at x=-0.505
        b.add_grounded_column(wb, f"hosp_pkt_stile_{sy_name}", -0.505, py, jamb_h, 0.024, 0.022, mat="fabricated_brushed_steel", plate_pad=0.018, gussets=False, top_flange=False)
        # Pocket wall cladding panel & grounded floor sill channel
        b.add_box(wb, f"hosp_pkt_sill_{sy_name}", (-1.12, py, 0.020), (0.59, 0.024, 0.020), "fabricated_cast_iron")
        b.add_beveled_box(wb, f"hosp_pkt_wall_{sy_name}", (-1.12, py, 1.00), (0.59, 0.018, 0.96), "fabricated_hospital_enamel", bevel=0.004)
        # Hospital mid-height crash bumper rail on corridor face
        out_y = py + (-0.024 if py < 0 else 0.024)
        b.add_beveled_box(wb, f"hosp_pkt_crash_{sy_name}", (-1.12, out_y, 0.82), (0.57, 0.012, 0.052), "fabricated_powder_enamel_light", bevel=0.003)

    # Right corridor wing wall framing the strike jamb (x in [0.55, 1.18])
    b.add_grounded_column(wb, "hosp_wing_post", 1.16, 0.0, jamb_h, 0.038, 0.068, mat="fabricated_hospital_enamel", plate_pad=0.030, gussets=True, top_flange=False)
    b.add_box(wb, "hosp_wing_sill", (0.85, 0.0, 0.020), (0.30, 0.062, 0.020), "fabricated_cast_iron")
    b.add_beveled_box(wb, "hosp_wing_wall", (0.85, 0.0, 1.00), (0.30, 0.056, 0.96), "fabricated_hospital_enamel", bevel=0.004)
    for sy_name, cy in (("front", -0.068), ("back", 0.068)):
        b.add_beveled_box(wb, f"hosp_wing_crash_{sy_name}", (0.85, cy, 0.82), (0.28, 0.012, 0.052), "fabricated_powder_enamel_light", bevel=0.003)

    # Overhead extruded aluminum door operator header & roller box track spanning x in [-1.77, 1.20]
    b.add_beveled_box(wb, "hosp_header_beam", (-0.285, 0.0, 2.04), (1.49, 0.095, 0.078), "fabricated_machined_aluminum", bevel=0.006)
    # Recessed lower twin steel track channels (z=1.94..1.968)
    for sy_name, ty in (("f", -0.036), ("b", 0.036)):
        b.add_box(wb, f"hosp_track_{sy_name}", (-0.60, ty, 1.954), (1.12, 0.012, 0.014), "fabricated_bearing")
    # Overhead doorway presence sensor bars (both corridor sides)
    for sy_name, sy in (("f", -0.102), ("b", 0.102)):
        b.add_beveled_box(wb, f"hosp_sensor_{sy_name}", (0.0, sy, 2.02), (0.14, 0.016, 0.020), "fabricated_black_oxide", bevel=0.003)
    # Concealed pocket-edge floor guide rollers (outside doorway opening at x=-0.51)
    for sy_name, gy in (("f", -0.055), ("b", 0.055)):
        b.add_cyl(wb, f"hosp_floor_guide_{sy_name}", (-0.51, gy, 0.024), 0.010, 0.022, "fabricated_delrin_guide")
    b.record_assembly("hospital_door_portal", "worldbody", "pocket partition, strike jamb & overhead box track")

    # 2. Moving sliding door hanger carriages, glazing bezel & kickplate (on 'door' body)
    door = b.index.body_elem("door")
    if door is not None:
        # Twin ball-bearing top hanger carriages bolted to door top (z=1.91) engaging track (z=1.954)
        for sx_name, hx in (("l", -0.33), ("r", 0.33)):
            b.add_beveled_box(door, f"door_hanger_pl_{sx_name}", (hx, 0.0, 1.918), (0.068, 0.042, 0.010), "fabricated_brushed_steel", bevel=0.002)
            b.add_box(door, f"door_hanger_stem_{sx_name}", (hx, 0.0, 1.942), (0.024, 0.014, 0.020), "fabricated_brushed_steel")
            for wy_i, wx_off in enumerate((-0.036, 0.036)):
                b.add_rod(door, f"door_roller_{sx_name}_{wy_i}", (hx + wx_off, -0.044, 1.956), (hx + wx_off, 0.044, 1.956), 0.015, "fabricated_bearing")
        # Stainless lower kickplate & glazing perimeter molding
        for sy_name, fy in (("f", -0.047), ("b", 0.047)):
            b.add_box(door, f"door_kick_{sy_name}", (0.0, fy, 0.14), (0.445, 0.003, 0.115), "fabricated_brushed_steel")
            # Frame around existing vision window (0, -0.048, 1.37, size 0.32 x 0.33)
            b.add_box(door, f"door_glz_t_{sy_name}", (0.0, fy, 1.712), (0.338, 0.006, 0.014), "fabricated_anodized_dark")
            b.add_box(door, f"door_glz_b_{sy_name}", (0.0, fy, 1.028), (0.338, 0.006, 0.014), "fabricated_anodized_dark")
            b.add_box(door, f"door_glz_l_{sy_name}", (-0.330, fy, 1.37), (0.014, 0.006, 0.342), "fabricated_anodized_dark")
            b.add_box(door, f"door_glz_r_{sy_name}", (0.330, fy, 1.37), (0.014, 0.006, 0.342), "fabricated_anodized_dark")
        # Handle mounting standoffs anchoring existing handle (0.412, -0.06, 0.98) into door leaf
        for sz_i, hz in enumerate((0.88, 1.08)):
            b.add_rod(door, f"door_hdl_stf_{sz_i}", (0.412, -0.044, hz), (0.412, -0.060, hz), 0.009, "fabricated_brushed_steel")
        b.record_assembly("hospital_door_carriages", "door", "overhead bearing hangers, kickplate & glazing frame")

    # 3. Medical trolley grounded casters, chassis-to-cabinet struts & top guard rail (on 'trolley' body)
    trolley = b.index.body_elem("trolley")
    if trolley is not None:
        # 4 medical swivel casters touching z=0.0 (trolley moves along Y -> roll_axis="y")
        for cx in (-0.22, 0.22):
            for cy in (-0.25, 0.25):
                tag = f"tr_cas_{'r' if cx > 0 else 'l'}_{'f' if cy > 0 else 'b'}"
                b.add_swivel_caster(trolley, tag, cx, cy, 0.135, roll_axis="y", wheel_r=0.048, wheel_w=0.024)
        # Corner roller bumper discs around chassis perimeter
        for cx in (-0.295, 0.295):
            for cy in (-0.335, 0.335):
                b.add_cyl(trolley, f"tr_bump_{int(cx>0)}_{int(cy>0)}", (cx, cy, 0.175), 0.032, 0.014, "fabricated_rubber_pad")
        # 4 stainless structural corner posts bridging the 0.305..0.410 air gap between chassis and cabinet!
        for cx in (-0.255, 0.255):
            for cy in (-0.295, 0.295):
                b.add_cyl(trolley, f"tr_strut_{int(cx>0)}_{int(cy>0)}", (cx, cy, 0.3575), 0.018, 0.055, "fabricated_brushed_steel")
                b.add_cyl(trolley, f"tr_fl_b_{int(cx>0)}_{int(cy>0)}", (cx, cy, 0.311), 0.028, 0.006, "fabricated_cast_iron")
                b.add_cyl(trolley, f"tr_fl_t_{int(cx>0)}_{int(cy>0)}", (cx, cy, 0.404), 0.028, 0.006, "fabricated_cast_iron")
        # Lower stainless instrument tray between chassis and cabinet
        b.add_beveled_box(trolley, "tr_mid_pan", (0.0, 0.0, 0.316), (0.265, 0.305, 0.010), "fabricated_brushed_steel", bevel=0.003)
        # Top perimeter containment lip rail above cabinet (z=0.91..0.955)
        for cx in (-0.27, 0.27):
            for cy in (-0.31, 0.31):
                b.add_cyl(trolley, f"tr_tpost_{int(cx>0)}_{int(cy>0)}", (cx, cy, 0.932), 0.008, 0.022, "fabricated_brushed_steel")
        b.add_rod(trolley, "tr_trail_l", (-0.27, -0.31, 0.952), (-0.27, 0.31, 0.952), 0.008, "fabricated_brushed_steel")
        b.add_rod(trolley, "tr_trail_r", (0.27, -0.31, 0.952), (0.27, 0.31, 0.952), 0.008, "fabricated_brushed_steel")
        b.add_rod(trolley, "tr_trail_b", (-0.27, 0.31, 0.952), (0.27, 0.31, 0.952), 0.008, "fabricated_brushed_steel")
        # Crossbar & mounting standoffs anchoring existing push rails (x=+/-0.22, y=-0.36, z=0.62)
        b.add_rod(trolley, "tr_push_bar", (-0.22, -0.36, 0.89), (0.22, -0.36, 0.89), 0.014, "fabricated_brushed_steel")
        for sx in (-0.22, 0.22):
            for sz in (0.44, 0.86):
                b.add_rod(trolley, f"tr_pstf_{int(sx>0)}_{int(sz*10)}", (sx, -0.34, sz), (sx, -0.36, sz), 0.010, "fabricated_anodized_dark")
        b.record_assembly("hospital_trolley_frame", "trolley", "4 swivel casters, chassis-to-cabinet struts & top rail")


def _fit_case_03_cafe(b: MachineBuilder) -> None:
    """03_cafe: Grounded cafe clean-tray return counter + XY ball-transfer shuttle."""
    wb = b.worldbody
    c_aabb = b.index.geom_aabb_or("counter", (-1.33, 1.33, -0.63, 0.63, 0.714, 0.800))
    cx1, cx2, cy1, cy2, cz1, cz2 = c_aabb

    # 1. Grounded steel & timber counter substructure meeting counter bottom cz1 cleanly
    b.add_table_frame(
        wb,
        "cafe_ctr",
        cx1,
        cx2,
        cy1,
        cy2,
        cz1,
        leg_xs=(cx1 + 0.08, 0.0, cx2 - 0.08),
        leg_ys=(cy1 + 0.08, cy2 - 0.08),
        mat="fabricated_powder_enamel",
        apron_h=0.048,
        leg_r=0.026,
        brace_z=0.20,
    )
    # Recessed stainless toe-kick plinth & warm-timber millwork fascia panels
    b.add_beveled_box(wb, "cafe_undershelf", (0.0, 0.0, 0.225), (cx2 - 0.11, cy2 - 0.12, 0.014), "fabricated_brushed_steel", bevel=0.003)
    for sy_name, fy in (("front", cy1 + 0.065), ("back", cy2 - 0.065)):
        b.add_beveled_box(wb, f"cafe_timber_{sy_name}", (0.0, fy, 0.445), (cx2 - 0.11, 0.014, 0.215), "fabricated_warm_timber", bevel=0.004)
        b.add_box(wb, f"cafe_kick_{sy_name}", (0.0, fy + (0.022 if fy < 0 else -0.022), 0.055), (cx2 - 0.11, 0.012, 0.055), "fabricated_brushed_steel")
    for sx_name, fx in (("left", cx1 + 0.065), ("right", cx2 - 0.065)):
        b.add_beveled_box(wb, f"cafe_endpanel_{sx_name}", (fx, 0.0, 0.445), (0.014, cy2 - 0.11, 0.215), "fabricated_warm_timber", bevel=0.004)

    # Low stainless tray-return guide curbs along outer counter edges (clearing shuttle & flask)
    for sy_name, gy in (("front", cy1 + 0.032), ("back", cy2 - 0.032)):
        b.add_beveled_box(wb, f"cafe_curb_{sy_name}", (0.0, gy, cz2 + 0.012), (cx2 - 0.06, 0.016, 0.012), "fabricated_brushed_steel", bevel=0.003)

    # Overhead clean-tray return pass-through arch & return-station sensor portal at +X end
    arch_z = cz2 + 0.66
    for sx in (cx1 + 0.07, cx2 - 0.07):
        for sy in (cy1 + 0.05, cy2 - 0.05):
            b.add_cyl(wb, f"cafe_arch_p_{int(sx>0)}_{int(sy>0)}", (sx, sy, 0.5 * (cz2 + arch_z)), 0.018, 0.5 * (arch_z - cz2), "fabricated_brushed_steel")
            b.add_cyl(wb, f"cafe_arch_fl_{int(sx>0)}_{int(sy>0)}", (sx, sy, cz2 + 0.008), 0.034, 0.008, "fabricated_cast_iron")
    for sy_name, sy in (("f", cy1 + 0.05), ("b", cy2 - 0.05)):
        b.add_beveled_box(wb, f"cafe_arch_x_{sy_name}", (0.0, sy, arch_z), (cx2 - 0.05, 0.020, 0.026), "fabricated_machined_aluminum", bevel=0.004)
    for sx_name, sx in (("l", cx1 + 0.07), ("r", cx2 - 0.07)):
        b.add_beveled_box(wb, f"cafe_arch_y_{sx_name}", (sx, 0.0, arch_z), (0.022, cy2 - 0.04, 0.026), "fabricated_machined_aluminum", bevel=0.004)
    # Tray-return optical gate sensors at +X station
    for sy_name, sy in (("f", cy1 + 0.08), ("b", cy2 - 0.08)):
        b.add_beveled_box(wb, f"cafe_opt_{sy_name}", (cx2 - 0.16, sy, cz2 + 0.16), (0.022, 0.022, 0.16), "fabricated_anodized_dark", bevel=0.003)
    b.record_assembly("cafe_counter_frame", "worldbody", "grounded steel/timber counter base & pass-through arch")

    # 2. Dish shuttle kinematic grounding onto counter surface z=0.800 (on 'dish_shuttle' body)
    shuttle = b.index.body_elem("dish_shuttle")
    if shuttle is not None:
        # Check if 4th leg (+0.13, +0.11) already exists in XML
        has_fourth_leg = False
        sb = b.index.bodies.get("dish_shuttle")
        if sb is not None:
            for g in sb.geoms:
                if g.local_pos[0] > 0.08 and g.local_pos[1] > 0.06 and g.local_pos[2] < -0.05:
                    has_fourth_leg = True
                    break
        if not has_fourth_leg:
            b.add_box(shuttle, "shuttle_leg4", (0.13, 0.11, -0.12), (0.012, 0.012, 0.10), "fabricated_brushed_steel")
            b.add_cyl(shuttle, "shuttle_foot4", (0.13, 0.11, -0.223), 0.032, 0.014, "fabricated_anodized_dark")

        # Extend all 4 feet down to z_local=-0.254 (world z=1.055-0.254=0.801, riding on counter z=0.800!)
        for lx in (-0.13, 0.13):
            for ly in (-0.11, 0.11):
                tag = f"sh_glide_{int(lx>0)}_{int(ly>0)}"
                b.add_cyl(shuttle, f"{tag}_ring", (lx, ly, -0.242), 0.030, 0.006, "fabricated_brushed_steel")
                b.add_cyl(shuttle, f"{tag}_puck", (lx, ly, -0.251), 0.025, 0.003, "fabricated_delrin_guide")
                b.add_sphere(shuttle, f"{tag}_ball", (lx, ly, -0.247), 0.007, "fabricated_bearing")
        # Rigid welded stainless H-subframe under tray_edge tying all 4 leg tops together
        for ly_name, ly in (("f", -0.11), ("b", 0.11)):
            b.add_box(shuttle, f"sh_sub_x_{ly_name}", (0.0, ly, -0.033), (0.145, 0.014, 0.010), "fabricated_brushed_steel")
        for lx_name, lx in (("l", -0.13), ("r", 0.13)):
            b.add_box(shuttle, f"sh_sub_y_{lx_name}", (lx, 0.0, -0.033), (0.014, 0.115, 0.010), "fabricated_brushed_steel")
        # Tray perimeter trim handles
        for sx_name, sx in (("l", -0.198), ("r", 0.198)):
            b.add_beveled_box(shuttle, f"sh_hdl_{sx_name}", (sx, 0.0, 0.006), (0.008, 0.11, 0.016), "fabricated_machined_aluminum", bevel=0.003)
        b.record_assembly("dish_shuttle_glides", "dish_shuttle", "ball-transfer counter glides & welded H-subframe")


def _fit_case_04_lab(b: MachineBuilder) -> None:
    """04_lab: Overhead twin-rail specimen gantry + cantilevered source/shelf benches + anchored catch."""
    wb = b.worldbody
    src = b.index.geom_aabb_or("source", (-1.33, -0.47, -0.43, 0.43, 0.714, 0.800))
    shf = b.index.geom_aabb_or("shelf", (0.45, 1.31, -0.43, 0.43, 0.714, 0.800))
    cat = b.index.geom_aabb_or("catch", (-0.85, 0.85, -0.54, 0.54, 0.258, 0.322))

    # 1. Grounded catch pan (x in [-0.85, 0.85], y in [-0.54, 0.54], z_bot=0.258)
    b.add_table_frame(
        wb,
        "lab_catch",
        cat[0],
        cat[1],
        cat[2],
        cat[3],
        cat[4],
        leg_xs=(cat[0] + 0.07, 0.0, cat[1] - 0.07),
        leg_ys=(cat[2] + 0.06, cat[3] - 0.06),
        mat="fabricated_powder_enamel",
        apron_h=0.032,
        leg_r=0.022,
        brace_z=0.08,
    )

    # 2. Grounded source & shelf benches with cantilevered diagonal knees clearing catch (x=+/-0.85)!
    src_inner_leg = min(cat[0] - 0.07, -0.92)
    b.add_table_frame(
        wb,
        "lab_src",
        src[0],
        src[1],
        src[2],
        src[3],
        src[4],
        leg_xs=(src[0] + 0.06, src_inner_leg),
        leg_ys=(src[2] + 0.055, src[3] - 0.055),
        mat="fabricated_brushed_steel",
        apron_h=0.038,
        leg_r=0.022,
        brace_z=0.20,
        knee_targets=[
            (src_inner_leg, src[1] - 0.06, src[2] + 0.055, 0.40),
            (src_inner_leg, src[1] - 0.06, src[3] - 0.055, 0.40),
        ],
    )
    shf_inner_leg = max(cat[1] + 0.07, 0.92)
    b.add_table_frame(
        wb,
        "lab_shf",
        shf[0],
        shf[1],
        shf[2],
        shf[3],
        shf[4],
        leg_xs=(shf_inner_leg, shf[1] - 0.06),
        leg_ys=(shf[2] + 0.055, shf[3] - 0.055),
        mat="fabricated_brushed_steel",
        apron_h=0.038,
        leg_r=0.022,
        brace_z=0.20,
        knee_targets=[
            (shf_inner_leg, shf[0] + 0.06, shf[2] + 0.055, 0.40),
            (shf_inner_leg, shf[0] + 0.06, shf[3] - 0.055, 0.40),
        ],
    )

    # 3. Clear-span 4-column overhead twin-rail gantry portal (outside source/shelf/catch)
    gx1 = min(src[0] - 0.06, -1.39)
    gx2 = max(shf[1] + 0.06, 1.37)
    gy_col = max(abs(cat[2]), abs(cat[3])) + 0.06  # +/- 0.60
    beam_z = 1.375
    # 4 heavy gantry columns + top Y-headers
    for sx_name, gx in (("l", gx1), ("r", gx2)):
        for sy_name, gy in (("f", -gy_col), ("b", gy_col)):
            b.add_grounded_column(wb, f"lab_gcol_{sx_name}_{sy_name}", gx, gy, beam_z + 0.045, 0.036, 0.036, mat="fabricated_powder_enamel", plate_pad=0.042, gussets=True)
        b.add_beveled_box(wb, f"lab_gyhdr_{sx_name}", (gx, 0.0, beam_z + 0.015), (0.042, gy_col + 0.045, 0.045), "fabricated_machined_aluminum", bevel=0.006)
        # Welded overhead corner knee gussets
        for sy in (-1.0, 1.0):
            mg = b.mesh_gusset("yz", -sy * 0.14, -0.14, 0.006)
            b.add_mesh_geom(wb, f"lab_ggus_{sx_name}_{int(sy>0)}", mg, (gx, sy * (gy_col - 0.036), beam_z - 0.030), "fabricated_cast_iron")

    # Twin longitudinal overhead X-beams at y=+/-0.215 (above carrier top z=1.318)
    g_cx = 0.5 * (gx1 + gx2)
    g_hx = 0.5 * (gx2 - gx1)
    for sy_name, ry in (("f", -0.215), ("b", 0.215)):
        b.add_beveled_box(wb, f"lab_gbeam_{sy_name}", (g_cx, ry, beam_z), (g_hx, 0.026, 0.038), "fabricated_machined_aluminum", bevel=0.005)
        # Hardened chrome guide rail on underside (z=1.329)
        b.add_box(wb, f"lab_grail_{sy_name}", (g_cx, ry, beam_z - 0.044), (g_hx - 0.05, 0.012, 0.008), "fabricated_bearing")
    # Center overhead ballscrew drive + stepper motor at -X end
    b.add_rod(wb, "lab_gscrew", (gx1 + 0.04, 0.0, beam_z + 0.012), (gx2 - 0.04, 0.0, beam_z + 0.012), 0.010, "fabricated_brushed_steel")
    b.add_beveled_box(wb, "lab_gmotor", (gx1 - 0.085, 0.0, beam_z + 0.012), (0.054, 0.042, 0.042), "fabricated_black_oxide", bevel=0.006)
    b.record_assembly("lab_overhead_gantry", "worldbody", "4-column overhead H-gantry, twin chrome rails & cantilevered tables")

    # 4. Moving carrier linear bearing blocks & specimen clamp yoke (on 'carrier' body, origin z=1.03)
    carrier = b.index.body_elem("carrier")
    if carrier is not None:
        # Existing block is local z in [0.192, 0.288] (world z in [1.222, 1.318])
        # Bridge crossbar bolted on top of carrier connecting to twin overhead rails (local z=0.301)
        for sx_name, bx in (("l", -0.115), ("r", 0.115)):
            b.add_beveled_box(carrier, f"car_xbar_{sx_name}", (bx, 0.0, 0.298), (0.034, 0.238, 0.012), "fabricated_anodized_dark", bevel=0.003)
            for sy_name, by in (("f", -0.215), ("b", 0.215)):
                b.add_beveled_box(carrier, f"car_brg_{sx_name}_{sy_name}", (bx, by, 0.308), (0.044, 0.026, 0.018), "fabricated_bearing", bevel=0.003)
        # Center ballscrew nut housing
        b.add_beveled_box(carrier, "car_nut", (0.0, 0.0, 0.340), (0.044, 0.032, 0.036), "fabricated_brass_bushing", bevel=0.004)
        # Beveled anodized pick-head collar around existing carrier block (clears specimen tubes below local z=0.180)
        for sy_name, sy in (("f", -0.195), ("b", 0.195)):
            b.add_beveled_box(carrier, f"car_trim_{sy_name}", (0.0, sy, 0.240), (0.172, 0.008, 0.042), "fabricated_anodized_dark", bevel=0.003)
        b.record_assembly("lab_carrier_bearings", "carrier", "4 overhead linear bearing blocks & ballscrew nut")


def _fit_case_05_parcel(b: MachineBuilder) -> None:
    """05_parcel: Grounded side-rail pusher + twin-rail lateral bridge + anchored tables/catch."""
    wb = b.worldbody
    infeed = b.index.geom_aabb_or("infeed", (-1.27, -0.31, -0.39, 0.39, 0.689, 0.775))
    outfeed = b.index.geom_aabb_or("outfeed", (0.32, 1.28, -0.39, 0.39, 0.636, 0.722))
    catch = b.index.geom_aabb_or("catch", (-0.35, 0.35, -0.43, 0.43, 0.250, 0.310))

    # 1. Lower catch anchored frame + welded brackets meeting bottom of catch (z=0.250, top stays z=0.310)
    b.add_table_frame(
        wb,
        "prc_catch",
        catch[0],
        catch[1],
        catch[2],
        catch[3],
        catch[4],
        leg_xs=(catch[0] + 0.048, catch[1] - 0.048),
        leg_ys=(catch[2] + 0.048, catch[3] - 0.048),
        mat="fabricated_powder_enamel",
        apron_h=0.034,
        leg_r=0.022,
        brace_z=0.075,
        plate_pad=0.022,
    )
    # Extra welded triangular underside brackets meeting catch bottom cleanly
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            mg = b.mesh_gusset("xz", -sx * 0.085, -0.075, 0.005)
            b.add_mesh_geom(
                wb,
                f"prc_catch_brk_{int(sx>0)}_{int(sy>0)}",
                mg,
                (sx * (catch[1] - 0.068), sy * (catch[3] - 0.048), catch[4]),
                "fabricated_cast_iron",
            )

    # 2. Grounded infeed & outfeed conveyor stands (inner legs at -0.50 / +0.51 clear bridge rails at +/-0.385!)
    b.add_table_frame(
        wb,
        "prc_infeed",
        infeed[0],
        infeed[1],
        infeed[2],
        infeed[3],
        infeed[4],
        leg_xs=(infeed[0] + 0.06, -0.50),
        leg_ys=(infeed[2] + 0.052, infeed[3] - 0.052),
        mat="fabricated_powder_enamel",
        apron_h=0.042,
        leg_r=0.024,
        brace_z=0.17,
    )
    b.add_table_frame(
        wb,
        "prc_outfeed",
        outfeed[0],
        outfeed[1],
        outfeed[2],
        outfeed[3],
        outfeed[4],
        leg_xs=(0.51, outfeed[1] - 0.06),
        leg_ys=(outfeed[2] + 0.052, outfeed[3] - 0.052),
        mat="fabricated_powder_enamel",
        apron_h=0.042,
        leg_r=0.024,
        brace_z=0.17,
    )
    # Conveyor side-channel roller fascia flush/below deck top (receiving surface heights 0.775 & 0.722 unchanged!)
    for dname, daabb in (("in", infeed), ("out", outfeed)):
        dcx = 0.5 * (daabb[0] + daabb[1])
        dhx = 0.5 * (daabb[1] - daabb[0])
        dcz = 0.5 * (daabb[4] + daabb[5])
        dhz = 0.5 * (daabb[5] - daabb[4]) - 0.004
        for sy_name, sy in (("f", daabb[2] - 0.009), ("b", daabb[3] + 0.009)):
            b.add_beveled_box(wb, f"prc_{dname}_fascia_{sy_name}", (dcx, sy, dcz), (dhx, 0.008, dhz), "fabricated_brushed_steel", bevel=0.002)
    # Cushioned end-stop rail outside +X end of outfeed (x=1.288, clears deck surface)
    b.add_beveled_box(wb, "prc_out_endstop", (outfeed[1] + 0.016, 0.0, outfeed[5] + 0.032), (0.014, 0.36, 0.042), "fabricated_anodized_dark", bevel=0.004)
    b.add_box(wb, "prc_out_bumper", (outfeed[1] + 0.002, 0.0, outfeed[5] + 0.032), (0.004, 0.34, 0.028), "fabricated_rubber_pad")

    # 3. Grounded -Y pusher side rail spanning full ~1.78 m stroke (outside +/-0.39 deck width, clears catch & crossing)
    p_min, p_max = b.index.joint_range("pusher", "push", (0.0, 1.78))
    p_info = b.index.bodies.get("pusher")
    p_x0 = p_info.world_pos[0] if p_info is not None else -1.035
    p_z0 = p_info.world_pos[2] if p_info is not None else 0.880
    rail_x1 = min(p_x0 + p_min - 0.21, -1.24)
    rail_x2 = max(p_x0 + p_max + 0.16, 0.92)
    rail_y = -0.468  # Clears +/-0.39 decks and -0.43 catch!
    rail_z = p_z0 - 0.005  # 0.875, cleanly above decks (0.775 / 0.722)

    b.add_linear_rail_x(
        wb,
        "prc_push_rail",
        rail_x1,
        rail_x2,
        rail_y,
        rail_z,
        beam_hy=0.030,
        beam_hz=0.040,
        stand_xs=(rail_x1 + 0.05, -0.44, 0.44, rail_x2 - 0.05),
        stand_y_shift=-0.032,  # Stanchions at y=-0.500, cleanly outside catch (-0.43) and crossing gap!
        rail_face="+y",
        motor_end="min",
    )
    b.record_assembly("parcel_pusher_side_rail", "worldbody", "full-stroke grounded -Y side rail, chrome guides & drive")

    # 4. Moving pusher carriage block + rigid lateral cantilever arm behind pushing face (on 'pusher' body)
    pusher = b.index.body_elem("pusher")
    if pusher is not None:
        # Local pusher_face is x in [-0.032, +0.032], y in [-0.18, +0.18], z in [-0.102, +0.102]
        # Rear steel backing plate bolted flush behind pushing face (x in [-0.056, -0.032])
        b.add_beveled_box(pusher, "psh_backplate", (-0.044, 0.0, 0.0), (0.012, 0.172, 0.088), "fabricated_cast_iron", bevel=0.003)
        # Rigid lateral arm behind pushing face extending out to -Y linear slide (world z in [0.848, 0.912], 73 mm above decks!)
        arm_y_in = -0.165
        arm_y_out = rail_y + 0.036  # meets carriage inner face at y=-0.432
        b.add_beveled_box(
            pusher,
            "psh_lat_arm",
            (-0.068, 0.5 * (arm_y_in + arm_y_out), -0.005),
            (0.024, 0.5 * abs(arm_y_out - arm_y_in), 0.032),
            "fabricated_brushed_steel",
            bevel=0.004,
        )
        # Horizontal XY triangular stiffening gusset between backing plate and lateral arm
        mg_arm = b.mesh_gusset("xy", -0.048, -0.195, 0.010)
        b.add_mesh_geom(pusher, "psh_arm_gus", mg_arm, (-0.056, -0.06, -0.005), "fabricated_cast_iron")
        # Anodized bearing carriage block riding directly on the twin chrome guide rails at rail_y=-0.468
        b.add_beveled_box(pusher, "psh_carriage", (-0.068, rail_y + 0.032, -0.005), (0.062, 0.028, 0.054), "fabricated_anodized_dark", bevel=0.005)
        for sz_name, dz in (("top", 0.028), ("bot", -0.028)):
            b.add_beveled_box(pusher, f"psh_brg_{sz_name}", (-0.068, rail_y + 0.038, -0.005 + dz), (0.056, 0.016, 0.014), "fabricated_bearing", bevel=0.002)
        # Safety-amber wear trim collar on arm rear edge
        b.add_box(pusher, "psh_arm_trim", (-0.094, 0.5 * (arm_y_in + arm_y_out), -0.005), (0.004, 0.5 * abs(arm_y_out - arm_y_in) - 0.02, 0.016), "fabricated_safety_amber")
        b.record_assembly("parcel_pusher_carriage", "pusher", "rear backing plate, rigid lateral arm & linear bearing block")

    # 5. Gray lateral bridge twin parallel Y-rails + grounded stands (outside +/-0.35 catch & drop chute!)
    br_min, br_max = b.index.joint_range("bridge", "bridge_in", (0.0, 0.84))
    br_info = b.index.bodies.get("bridge")
    br_y0 = br_info.world_pos[1] if br_info is not None else 0.84
    br_z0 = br_info.world_pos[2] if br_info is not None else 0.732
    br_rail_xs = (-0.388, 0.388)  # Clears catch (+/-0.35), drop gap ([-0.31, 0.32]), and table legs (-0.50 / +0.51)!
    br_rail_z = 0.540  # Chrome rail top at 0.575; slide block top at 0.614 -> 22 mm below outfeed underside (0.636)!
    br_y1 = min(br_y0 - br_max - 0.37, -0.37)
    br_y2 = max(br_y0 - br_min + 0.40, 1.24)
    for sx_name, rx in (("l", br_rail_xs[0]), ("r", br_rail_xs[1])):
        b.add_linear_rail_y(
            wb,
            f"prc_br_rail_{sx_name}",
            br_y1,
            br_y2,
            rx,
            br_rail_z,
            beam_hx=0.026,
            beam_hz=0.028,
            stand_ys=(br_y1 + 0.03, 0.47, br_y2 - 0.03),
            motor_end="max",
        )
    # Cross-tie tying the two rear bridge rail stands at y=br_y2-0.03 (well behind conveyor decks)
    b.add_box(wb, "prc_br_rear_tie", (0.0, br_y2 - 0.03, 0.22), (0.36, 0.018, 0.018), "fabricated_powder_enamel")
    b.record_assembly("parcel_bridge_rails", "worldbody", "twin parallel Y-rails & grounded stands clearing drop chute")

    # 6. Bridge matching slide blocks & step-up under-deck carriage (on 'bridge' body)
    bridge = b.index.body_elem("bridge")
    if bridge is not None:
        # Local bridge_deck bottom is z=-0.027 (world 0.705); chrome rail top is world 0.575 -> local -0.157
        z_rail_loc = (br_rail_z + 0.028 + 0.007) - br_z0  # -0.157
        z_deck_bot = -0.027
        # Longitudinal under-deck stringers hugging bridge_deck underside cleanly inside x in [-0.27, +0.27]
        for sx_name, sx in (("l", -0.255), ("r", 0.255)):
            b.add_beveled_box(bridge, f"br_str_{sx_name}", (sx, 0.0, z_deck_bot - 0.014), (0.018, 0.355, 0.014), "fabricated_brushed_steel", bevel=0.003)
        # Front & rear carriage rib sets (y_local = +/-0.26) with 4 matching bearing slide blocks on the twin Y-rails
        for sy_name, ly in (("f", -0.26), ("b", 0.26)):
            # Transverse stiffening rib under bridge deck
            b.add_beveled_box(bridge, f"br_rib_{sy_name}", (0.0, ly, z_deck_bot - 0.016), (0.268, 0.022, 0.016), "fabricated_brushed_steel", bevel=0.003)
            for sx_name, rx in (("l", br_rail_xs[0]), ("r", br_rail_xs[1])):
                sgn = -1.0 if rx < 0 else 1.0
                # Bearing slide block riding directly on Y-rail (top at world z=0.614 < outfeed bottom 0.636!)
                b.add_beveled_box(bridge, f"br_sblk_{sy_name}_{sx_name}", (rx, ly, z_rail_loc + 0.016), (0.032, 0.052, 0.020), "fabricated_anodized_dark", bevel=0.004)
                b.add_box(bridge, f"br_wiper_{sy_name}_{sx_name}", (rx, ly, z_rail_loc + 0.002), (0.022, 0.056, 0.008), "fabricated_bearing")
                # Horizontal step-in arm clearing beneath infeed/outfeed (world z=0.592..0.616)
                in_x = sgn * 0.258
                b.add_beveled_box(
                    bridge,
                    f"br_steph_{sy_name}_{sx_name}",
                    (0.5 * (rx + in_x), ly, z_rail_loc + 0.026),
                    (0.5 * abs(rx - in_x) + 0.012, 0.022, 0.012),
                    "fabricated_cast_iron",
                    bevel=0.003,
                )
                # Vertical step-up riser inside the conveyor gap (x=+/-0.258) meeting bridge underside rib
                riser_bot = z_rail_loc + 0.036
                riser_top = z_deck_bot - 0.026
                b.add_beveled_box(
                    bridge,
                    f"br_stepv_{sy_name}_{sx_name}",
                    (in_x, ly, 0.5 * (riser_bot + riser_top)),
                    (0.018, 0.022, 0.5 * (riser_top - riser_bot) + 0.004),
                    "fabricated_cast_iron",
                    bevel=0.003,
                )
        b.record_assembly("parcel_bridge_slide_blocks", "bridge", "4 linear slide blocks & step-up under-deck frame")


def _fit_case_06_shaft(b: MachineBuilder) -> None:
    """06_shaft: Grounded feed rail, side-retracting gate slide, twin-rail receiver & anchored catch."""
    wb = b.worldbody
    feed = b.index.geom_aabb_or("feed_rail", (-1.16, -0.08, -0.31, 0.31, 0.832, 0.888))
    catch = b.index.geom_aabb_or("catch", (-0.16, 0.92, -0.38, 0.38, 0.238, 0.302))
    clip = b.index.geom_aabb_or("catch_lip", (0.878, 0.922, -0.38, 0.38, 0.290, 0.530))

    # 1. Grounded catch pan + catch_lip rear gussets
    b.add_table_frame(
        wb,
        "shf_catch",
        catch[0],
        catch[1],
        catch[2],
        catch[3],
        catch[4],
        leg_xs=(catch[0] + 0.055, catch[1] - 0.055),
        leg_ys=(catch[2] + 0.052, catch[3] - 0.052),
        mat="fabricated_powder_enamel",
        apron_h=0.032,
        leg_r=0.022,
        brace_z=0.075,
        plate_pad=0.022,
    )
    # Rear stiffening gussets behind catch_lip (x=0.922..0.958, clearing receiver rail at x=+0.988)
    for sy in (-0.26, 0.0, 0.26):
        mg = b.mesh_gusset("xz", 0.036, 0.16, 0.005)
        b.add_mesh_geom(wb, f"shf_lip_gus_{int((sy+0.3)*10)}", mg, (clip[1], sy, clip[4] + 0.015), "fabricated_cast_iron")

    # 2. Grounded feed_rail stand (inner leg at x=-0.33 clears receiver rail at -0.205, knee supports overhang!)
    feed_inner_leg = -0.33
    b.add_table_frame(
        wb,
        "shf_feed",
        feed[0],
        feed[1],
        feed[2],
        feed[3],
        feed[4],
        leg_xs=(feed[0] + 0.06, feed_inner_leg),
        leg_ys=(feed[2] + 0.048, feed[3] - 0.048),
        mat="fabricated_powder_enamel",
        apron_h=0.040,
        leg_r=0.024,
        brace_z=0.20,
        knee_targets=[
            (feed_inner_leg, feed[1] - 0.05, feed[2] + 0.048, 0.58),
            (feed_inner_leg, feed[1] - 0.05, feed[3] - 0.048, 0.58),
        ],
    )
    for sy_name, sy in (("f", feed[2] - 0.008), ("b", feed[3] + 0.008)):
        b.add_box(wb, f"shf_feed_trim_{sy_name}", (0.5 * (feed[0] + feed[1]), sy, 0.5 * (feed[4] + feed[5])), (0.5 * (feed[1] - feed[0]), 0.007, 0.024), "fabricated_brushed_steel")

    # 3. Grounded -Y linear slide actuator for 'gate' at x=-0.54, z=0.99 (clears feed_rail y in [-0.31, 0.31])
    g_min, g_max = b.index.joint_range("gate", "ungate", (0.0, 0.56))
    g_info = b.index.bodies.get("gate")
    gx0 = g_info.world_pos[0] if g_info is not None else -0.54
    gz0 = g_info.world_pos[2] if g_info is not None else 0.99
    gy_near = feed[2] - 0.04  # -0.35
    gy_far = min(-0.46 - g_max - 0.08, -1.04)
    # Front bracket rising from feed_rail frame + rear grounded floor column
    b.add_grounded_column(wb, "shf_gate_rear_col", gx0, gy_far, gz0 + 0.072, 0.028, 0.028, mat="fabricated_powder_enamel", plate_pad=0.034, gussets=True, top_flange=False)
    b.add_grounded_column(wb, "shf_gate_front_col", gx0, gy_near - 0.02, gz0 + 0.072, 0.022, 0.022, mat="fabricated_powder_enamel", plate_pad=0.026, gussets=False, top_flange=False)
    # Twin hardened steel linear guide shafts + pneumatic/electric cylinder body
    for dz_name, dz in (("hi", 0.046), ("lo", -0.046)):
        b.add_rod(wb, f"shf_gate_rod_{dz_name}", (gx0, gy_far, gz0 + dz), (gx0, gy_near, gz0 + dz), 0.011, "fabricated_bearing")
    b.add_beveled_box(wb, "shf_gate_cyl", (gx0, gy_far - 0.11, gz0), (0.032, 0.095, 0.032), "fabricated_anodized_dark", bevel=0.004)
    b.add_rod(wb, "shf_gate_piston", (gx0, gy_far, gz0), (gx0, gy_near, gz0), 0.009, "fabricated_brushed_steel")
    b.record_assembly("shaft_gate_slide", "worldbody", "floor-anchored dual-rod gate slide & cylinder")

    # Moving gate carriage block riding the twin rods (on 'gate' body)
    gate = b.index.body_elem("gate")
    if gate is not None:
        # Local stop spans y in [-0.25, +0.25], z in [-0.10, +0.10]
        b.add_beveled_box(gate, "gate_arm", (0.0, -0.315, 0.0), (0.022, 0.068, 0.064), "fabricated_brushed_steel", bevel=0.003)
        b.add_beveled_box(gate, "gate_carr", (0.0, -0.405, 0.0), (0.036, 0.042, 0.070), "fabricated_anodized_dark", bevel=0.004)
        for dz_name, dz in (("hi", 0.046), ("lo", -0.046)):
            b.add_rod(gate, f"gate_bush_{dz_name}", (0.0, -0.452, dz), (0.0, -0.358, dz), 0.016, "fabricated_brass_bushing")
        # Delrin shaft-contact wear strip on -X face of stop
        b.add_box(gate, "gate_wear_strip", (-0.029, 0.0, 0.0), (0.003, 0.235, 0.085), "fabricated_delrin_guide")
        b.record_assembly("shaft_gate_carriage", "gate", "bronze-bushed linear carriage & wear strip")

    # 4. Twin parallel Y-rails for 'receiver' cradle clearing catch (x in [-0.16, 0.922]) & feed_rail (z_bot=0.832)
    r_min, r_max = b.index.joint_range("receiver", "receive", (0.0, 0.90))
    r_info = b.index.bodies.get("receiver")
    rx0 = r_info.world_pos[0] if r_info is not None else 0.30
    ry0 = r_info.world_pos[1] if r_info is not None else 0.90
    rec_rail_xs = (-0.208, 0.988)
    rec_rail_z = 0.578  # Chrome rail top at 0.613, slide blocks at 0.613..0.650, crossbars 0.642..0.677 (112 mm above catch_lip!)
    rec_y1 = min(ry0 - r_max - 0.36, -0.36)
    rec_y2 = max(ry0 - r_min + 0.36, 1.26)
    for sx_name, rx in (("l", rec_rail_xs[0]), ("r", rec_rail_xs[1])):
        b.add_linear_rail_y(
            wb,
            f"shf_rec_rail_{sx_name}",
            rec_y1,
            rec_y2,
            rx,
            rec_rail_z,
            beam_hx=0.026,
            beam_hz=0.028,
            stand_ys=(rec_y1 + 0.03, 0.44, rec_y2 - 0.03),
            motor_end="max",
        )
    b.record_assembly("shaft_receiver_rails", "worldbody", "twin parallel Y-rails & grounded stands clearing catch")

    # Moving receiver slide blocks, under-cradle crossbars & end-wall gussets (on 'receiver' body, origin x=0.30)
    receiver = b.index.body_elem("receiver")
    if receiver is not None:
        lx_l = rec_rail_xs[0] - rx0  # -0.508
        lx_r = rec_rail_xs[1] - rx0  # +0.688
        lx_mid = 0.5 * (lx_l + lx_r)
        lx_half = 0.5 * (lx_r - lx_l)
        z_rail_top = rec_rail_z + 0.028 + 0.007  # 0.613
        z_cradle_bot = 0.677
        for sy_name, ly in (("f", -0.255), ("b", 0.255)):
            # Full-span welded under-cradle steel crossbar bridging both Y-rails cleanly above catch_lip (0.530)
            b.add_beveled_box(receiver, f"rec_xbar_{sy_name}", (lx_mid, ly, 0.5 * (z_rail_top + 0.030 + z_cradle_bot)), (lx_half + 0.020, 0.024, 0.018), "fabricated_brushed_steel", bevel=0.003)
            for sx_name, lx in (("l", lx_l), ("r", lx_r)):
                b.add_beveled_box(receiver, f"rec_sblk_{sy_name}_{sx_name}", (lx, ly, z_rail_top + 0.016), (0.032, 0.052, 0.020), "fabricated_anodized_dark", bevel=0.004)
                b.add_box(receiver, f"rec_wiper_{sy_name}_{sx_name}", (lx, ly, z_rail_top + 0.002), (0.022, 0.056, 0.008), "fabricated_bearing")
        # Rear welded gussets stiffening end_wall (local x=0.36, z=0.703..0.913)
        for sy in (-0.22, 0.0, 0.22):
            mg = b.mesh_gusset("xz", 0.085, 0.145, 0.005)
            b.add_mesh_geom(receiver, f"rec_ew_gus_{int((sy+0.3)*10)}", mg, (0.385, sy, 0.706), "fabricated_cast_iron")
        b.record_assembly("shaft_receiver_carriage", "receiver", "4 linear slide blocks, under-cradle crossbars & end-wall gussets")


def _fit_case_07_electronics(b: MachineBuilder) -> None:
    """07_electronics: Grounded ESD bench, bench-bolted drawer slide rails & guided plug test-rig."""
    wb = b.worldbody
    bench = b.index.geom_aabb_or("bench", (-1.11, 1.11, -0.49, 0.49, 0.634, 0.720))
    bx1, bx2, by1, by2, bz1, bz2 = bench

    # 1. Grounded 6-leg ESD electronics workbench
    b.add_table_frame(
        wb,
        "el_bench",
        bx1,
        bx2,
        by1,
        by2,
        bz1,
        leg_xs=(bx1 + 0.07, 0.0, bx2 - 0.07),
        leg_ys=(by1 + 0.06, by2 - 0.06),
        mat="fabricated_powder_enamel",
        apron_h=0.044,
        leg_r=0.024,
        brace_z=0.18,
    )
    # Rear instrument backsplash & bench power-strip conduit raceway
    b.add_beveled_box(wb, "el_raceway", (0.0, by2 - 0.030, bz2 + 0.032), (bx2 - 0.05, 0.024, 0.032), "fabricated_anodized_dark", bevel=0.004)
    for sx_name, rx in (("l", -0.82), ("c", 0.0), ("r", 0.82)):
        b.add_box(wb, f"el_outlet_{sx_name}", (rx, by2 - 0.056, bz2 + 0.032), (0.045, 0.003, 0.018), "fabricated_powder_enamel_light")
    b.record_assembly("electronics_workbench", "worldbody", "6-leg ESD steel workbench & rear power raceway")

    # 2. Moving drawer housing & twin bench-bolted low-profile linear rails (below plug_body z_bot=0.871!)
    d_min, d_max = b.index.joint_range("drawer", "latch", (0.0, 0.80))
    d_info = b.index.bodies.get("drawer")
    dx0 = d_info.world_pos[0] if d_info is not None else -0.64
    d_rail_x1 = max(bx1 + 0.04, -1.06)
    d_rail_x2 = min(bx2 - 0.06, max(dx0 + d_max + 0.09, 0.24))
    # Sheet-metal test chassis enclosure on the left end of bench (behind drawer lip at x=-0.70)
    b.add_beveled_box(wb, "el_chassis_top", (-0.90, 0.0, 1.052), (0.175, 0.285, 0.014), "fabricated_powder_enamel_light", bevel=0.003)
    b.add_beveled_box(wb, "el_chassis_back", (-1.062, 0.0, 0.892), (0.014, 0.285, 0.172), "fabricated_powder_enamel_light", bevel=0.003)
    for sy_name, sy in (("f", -0.278), ("b", 0.278)):
        b.add_beveled_box(wb, f"el_chassis_side_{sy_name}", (-0.90, sy, 0.892), (0.175, 0.012, 0.172), "fabricated_powder_enamel_light", bevel=0.003)
        b.add_box(wb, f"el_chassis_fl_{sy_name}", (-0.90, sy + (-0.022 if sy < 0 else 0.022), bz2 + 0.006), (0.16, 0.014, 0.006), "fabricated_cast_iron")
    # Twin bench-bolted chrome linear profile rails at y=+/-0.21, z=0.720..0.744
    dr_cx = 0.5 * (d_rail_x1 + d_rail_x2)
    dr_hx = 0.5 * (d_rail_x2 - d_rail_x1)
    for sy_name, ry in (("f", -0.210), ("b", 0.210)):
        b.add_box(wb, f"el_drail_base_{sy_name}", (dr_cx, ry, bz2 + 0.008), (dr_hx, 0.016, 0.008), "fabricated_machined_aluminum")
        b.add_box(wb, f"el_drail_chr_{sy_name}", (dr_cx, ry, bz2 + 0.020), (dr_hx - 0.01, 0.010, 0.005), "fabricated_bearing")
        b.add_box(wb, f"el_drail_stop_{sy_name}", (d_rail_x2, ry, bz2 + 0.018), (0.012, 0.020, 0.018), "fabricated_cast_iron")
    b.record_assembly("electronics_drawer_rails", "worldbody", "test enclosure & twin bench-bolted linear rails")

    # Moving drawer linear slide blocks, tray & pull handle (on 'drawer' body)
    drawer = b.index.body_elem("drawer")
    if drawer is not None:
        # Local lip is x in [-0.06, +0.06], y in [-0.263, +0.263], z in [0.758, 1.042]
        for sy_name, ry in (("f", -0.210), ("b", 0.210)):
            for sx_name, rx in (("r", -0.20), ("f", 0.0)):
                b.add_beveled_box(drawer, f"drw_blk_{sy_name}_{sx_name}", (rx, ry, 0.746), (0.036, 0.022, 0.012), "fabricated_anodized_dark", bevel=0.003)
        # Rigid aluminum drawer tray extending behind lip into enclosure
        b.add_beveled_box(drawer, "drw_tray_bot", (-0.165, 0.0, 0.766), (0.110, 0.246, 0.009), "fabricated_machined_aluminum", bevel=0.002)
        for sy_name, sy in (("f", -0.242), ("b", 0.242)):
            b.add_box(drawer, f"drw_tray_side_{sy_name}", (-0.165, sy, 0.828), (0.105, 0.008, 0.056), "fabricated_machined_aluminum")
        # Front machined D-pull handle & faceplate fasteners on lip
        b.add_rod(drawer, "drw_hdl_bar", (0.088, -0.09, 0.90), (0.088, 0.09, 0.90), 0.010, "fabricated_brushed_steel")
        for sy_name, hy in (("f", -0.09), ("b", 0.09)):
            b.add_rod(drawer, f"drw_hdl_stf_{sy_name}", (0.060, hy, 0.90), (0.088, hy, 0.90), 0.008, "fabricated_brushed_steel")
        b.record_assembly("electronics_drawer_carriage", "drawer", "4 linear slide blocks, tray & machined D-pull")

    # 3. Grounded test receptacle bulkhead & twin Y-guide slide supporting 'plug_body' (at x=0.345, y=0.02, z=0.943)
    p_info = b.index.bodies.get("plug_body")
    px0 = p_info.world_pos[0] if p_info is not None else 0.345
    py0 = p_info.world_pos[1] if p_info is not None else 0.020
    pz0 = p_info.world_pos[2] if p_info is not None else 0.943
    u_min, u_max = b.index.joint_range("plug_body", "unplug", (0.0, 0.26))
    slide_y1 = py0 - 0.115
    slide_y2 = min(by2 - 0.06, max(py0 + u_max + 0.12, 0.40))
    shaft_z = pz0 - 0.090  # 0.853, 18 mm below plug bottom (0.871)

    # Receptacle bulkhead pedestal on -Y mating face of plug (anchored straight down to bench z=0.720)
    b.add_beveled_box(wb, "el_rcp_base", (px0, 0.5 * (slide_y1 - 0.12 + slide_y2), bz2 + 0.010), (0.105, 0.5 * (slide_y2 - (slide_y1 - 0.12)), 0.010), "fabricated_cast_iron", bevel=0.003)
    b.add_beveled_box(wb, "el_rcp_tower", (px0, slide_y1 - 0.052, 0.5 * (bz2 + 0.020 + pz0 + 0.090)), (0.088, 0.048, 0.5 * (pz0 + 0.090 - bz2 - 0.020)), "fabricated_powder_enamel", bevel=0.005)
    b.add_beveled_box(wb, "el_rcp_socket", (px0, slide_y1 - 0.004, pz0), (0.056, 0.012, 0.064), "fabricated_anodized_dark", bevel=0.003)
    # Rear pillow-block riser supporting +Y end of twin guide shafts
    b.add_beveled_box(wb, "el_rcp_rear", (px0, slide_y2 - 0.022, 0.5 * (bz2 + 0.020 + shaft_z + 0.020)), (0.088, 0.022, 0.5 * (shaft_z + 0.020 - bz2 - 0.020)), "fabricated_powder_enamel", bevel=0.004)
    # Twin hardened steel Y-guide shafts
    for sx_name, dx in (("l", -0.054), ("r", 0.054)):
        b.add_rod(wb, f"el_plug_shaft_{sx_name}", (px0 + dx, slide_y1, shaft_z), (px0 + dx, slide_y2 - 0.012, shaft_z), 0.009, "fabricated_bearing")
    b.record_assembly("electronics_plug_rig", "worldbody", "bench-bolted receptacle bulkhead & twin Y-guide shafts")

    # Moving plug carriage saddle & brass prongs (on 'plug_body')
    plug = b.index.body_elem("plug_body")
    if plug is not None:
        # Local plug bottom is z=-0.072; shaft is at z=-0.090
        b.add_beveled_box(plug, "plg_saddle", (0.0, 0.0, -0.086), (0.072, 0.066, 0.016), "fabricated_anodized_dark", bevel=0.003)
        for sx_name, dx in (("l", -0.054), ("r", 0.054)):
            b.add_rod(plug, f"plg_bush_{sx_name}", (dx, -0.072, -0.090), (dx, 0.072, -0.090), 0.014, "fabricated_brass_bushing")
        # Brass connector contact pins on -Y mating face + strain-relief boot on +Y face
        for px_i, dx in enumerate((-0.028, 0.0, 0.028)):
            b.add_rod(plug, f"plg_pin_{px_i}", (dx, -0.100, 0.0), (dx, -0.124, 0.0), 0.006, "fabricated_brass_bushing")
        b.add_rod(plug, "plg_boot", (0.0, 0.100, 0.0), (0.0, 0.155, 0.0), 0.016, "fabricated_rubber_pad")
        b.record_assembly("electronics_plug_saddle", "plug_body", "bushed guide saddle, brass pins & strain relief")


def _fit_case_08_print(b: MachineBuilder) -> None:
    """08_print: Grounded rolling paper cart + floor wheel curbs + clear-span print-carriage gantry."""
    wb = b.worldbody

    # 1. Grounded welded steel paper cart undercarriage (on 'paper_cart' body)
    cart = b.index.body_elem("paper_cart")
    if cart is not None:
        # Local cart_top is x in [-0.43, 0.43], y in [-0.35, 0.35], z in [0.74, 0.84]
        z_under = 0.740
        z_shelf = 0.145
        # Perimeter steel apron directly meeting cart_top underside (z=0.696..0.740)
        for sy_name, sy in (("f", -0.315), ("b", 0.315)):
            b.add_box(cart, f"pc_apron_{sy_name}", (0.0, sy, z_under - 0.022), (0.40, 0.016, 0.022), "fabricated_powder_enamel")
        for sx_name, sx in (("l", -0.395), ("r", 0.395)):
            b.add_box(cart, f"pc_apron_{sx_name}", (sx, 0.0, z_under - 0.022), (0.016, 0.30, 0.022), "fabricated_powder_enamel")
        # 4 tubular steel corner legs + welded corner gussets + lower storage shelf
        for lx in (-0.375, 0.375):
            for ly in (-0.295, 0.295):
                tag = f"pc_leg_{int(lx>0)}_{int(ly>0)}"
                b.add_beveled_box(cart, tag, (lx, ly, 0.5 * (z_shelf - 0.020 + z_under)), (0.022, 0.022, 0.5 * (z_under - z_shelf + 0.020)), "fabricated_powder_enamel", bevel=0.003)
                b.add_swivel_caster(cart, f"pc_cas_{int(lx>0)}_{int(ly>0)}", lx, ly, z_shelf - 0.020, roll_axis="x", wheel_r=0.048, wheel_w=0.026)
        b.add_beveled_box(cart, "pc_low_shelf", (0.0, 0.0, z_shelf), (0.39, 0.31, 0.016), "fabricated_brushed_steel", bevel=0.003)
        # Side diagonal stiffening X-braces
        for sy_name, sy in (("f", -0.295), ("b", 0.295)):
            b.add_rod(cart, f"pc_diag_{sy_name}", (-0.36, sy, z_shelf + 0.02), (0.36, sy, z_under - 0.04), 0.011, "fabricated_powder_enamel")
        # Ergonomic push-handle on -X end (clears ream x in [-0.26, 0.26])
        for sy_name, sy in (("f", -0.27), ("b", 0.27)):
            b.add_rod(cart, f"pc_hdl_p_{sy_name}", (-0.425, sy, 0.78), (-0.465, sy, 0.99), 0.014, "fabricated_brushed_steel", capsule=True)
        b.add_rod(cart, "pc_hdl_grip", (-0.465, -0.27, 0.99), (-0.465, 0.27, 0.99), 0.018, "fabricated_rubber_pad")
        # Low registration guide lips on cart_top edges (y=+/-0.34, well outside ream y=+/-0.20)
        for sy_name, sy in (("f", -0.342), ("b", 0.342)):
            b.add_beveled_box(cart, f"pc_lip_{sy_name}", (0.0, sy, 0.850), (0.41, 0.008, 0.010), "fabricated_machined_aluminum", bevel=0.002)
        b.record_assembly("paper_cart_frame", "paper_cart", "welded steel cart frame, 4 casters, lower shelf & push handle")

    # 2. Floor wheel-guide curbs guiding the paper cart along X
    t_min, t_max = b.index.joint_range("paper_cart", "travel", (0.0, 1.85))
    c_info = b.index.bodies.get("paper_cart")
    cx0 = c_info.world_pos[0] if c_info is not None else -0.92
    gx1 = min(cx0 + t_min - 0.52, -1.44)
    gx2 = max(cx0 + t_max + 0.52, 1.44)
    gcx, ghx = 0.5 * (gx1 + gx2), 0.5 * (gx2 - gx1)
    for sy_name, cy in (("f", -0.39), ("b", 0.39)):
        b.add_beveled_box(wb, f"prt_curb_{sy_name}", (gcx, cy, 0.015), (ghx, 0.022, 0.015), "fabricated_machined_aluminum", bevel=0.004)
        b.add_box(wb, f"prt_curb_str_{sy_name}", (gcx, cy + (-0.023 if cy < 0 else 0.023), 0.015), (ghx - 0.04, 0.002, 0.010), "fabricated_hazard_stripe")

    # 3. Clear-span industrial wide-format print-bridge gantry at x=0 (only if no print bridge exists already)
    has_existing_bridge = any(
        any(tok in g.name.lower() for tok in ("print", "carriage", "gantry", "bridge", "head"))
        and g.parent_body != "paper_cart"
        for g in b.index.geoms
    )
    if not has_existing_bridge:
        py_col = 0.58  # Clears cart width +/-0.35 and wheel curbs +/-0.39 by 190 mm
        hdr_z = 1.26   # Underside z=1.16, clearing ream top z=0.991 by 169 mm!
        for sy_name, py in (("f", -py_col), ("b", py_col)):
            b.add_grounded_column(wb, f"prt_acol_{sy_name}", 0.0, py, hdr_z + 0.09, 0.075, 0.045, mat="fabricated_cast_iron", plate_pad=0.055, gussets=True)
            # Side A-frame stability braces
            for sx in (-1.0, 1.0):
                b.add_rod(wb, f"prt_abrc_{sy_name}_{int(sx>0)}", (sx * 0.24, py, 0.02), (sx * 0.06, py, hdr_z - 0.05), 0.020, "fabricated_powder_enamel")
                b.add_floor_anchor_plate(wb, f"prt_abrc_ft_{sy_name}_{int(sx>0)}", sx * 0.24, py, 0.048, 0.048, 0.014)
        # Overhead extruded print-bridge crossbeam + twin chrome carriage Y-rails + parked print head
        b.add_beveled_box(wb, "prt_bridge_beam", (0.0, 0.0, hdr_z), (0.095, py_col + 0.05, 0.095), "fabricated_powder_enamel_light", bevel=0.008)
        for dz_name, dz in (("hi", 0.052), ("lo", -0.052)):
            b.add_box(wb, f"prt_yrail_{dz_name}", (-0.102, 0.0, hdr_z + dz), (0.010, py_col - 0.06, 0.010), "fabricated_bearing")
        # Print-head carriage saddle parked on +Y side of bridge
        b.add_beveled_box(wb, "prt_head_saddle", (-0.135, 0.34, hdr_z), (0.048, 0.095, 0.085), "fabricated_anodized_dark", bevel=0.006)
        b.add_cyl(wb, "prt_beacon", (0.0, py_col, hdr_z + 0.145), 0.024, 0.042, "fabricated_safety_amber")
        b.record_assembly("print_carriage_gantry", "worldbody", "cast A-frame print-bridge gantry & floor curbs")


def _fit_case_09_library(b: MachineBuilder) -> None:
    """09_library: Grounded height-gate portal supporting header + grounded mobile book-lift chassis."""
    wb = b.worldbody
    hdr = b.index.geom_aabb_or("header", (0.135, 0.305, -0.96, 0.64, 1.398, 1.562))
    hx1, hx2, hy1, hy2, hz1, hz2 = hdr
    hcx = 0.5 * (hx1 + hx2)
    hhx = 0.5 * (hx2 - hx1)

    # 1. Grounded twin-column steel height-gate portal meeting header underside cleanly at hz1=1.398
    col_y_s = hy1 + 0.065  # -0.895
    col_y_n = hy2 - 0.065  # +0.575 -> clear opening y in [-0.83, +0.51] (1.34 m wide, clearing mobile +/-0.26!)
    for sy_name, cy in (("s", col_y_s), ("n", col_y_n)):
        b.add_grounded_column(wb, f"lib_pcol_{sy_name}", hcx, cy, hz1, 0.064, 0.060, mat="fabricated_powder_enamel", plate_pad=0.045, gussets=True, top_flange=True)
        # Welded overhead knee gussets meeting header underside
        in_dir = 1.0 if cy < 0.0 else -1.0
        mg = b.mesh_gusset("yz", in_dir * 0.12, -0.14, 0.007)
        b.add_mesh_geom(wb, f"lib_pgus_{sy_name}", mg, (hcx, cy + in_dir * 0.060, hz1), "fabricated_cast_iron")
        # Photo-electric height-limit sensor housing mounted on inner column face at z=hz1-0.03
        b.add_beveled_box(wb, f"lib_opt_{sy_name}", (hcx, cy + in_dir * 0.072, hz1 - 0.036), (0.024, 0.014, 0.026), "fabricated_anodized_dark", bevel=0.003)
        # Library architectural wing wainscoting panel outside portal posts
        out_dir = -in_dir
        b.add_beveled_box(wb, f"lib_wing_{sy_name}", (hcx, cy + out_dir * 0.14, 0.62), (0.028, 0.082, 0.60), "fabricated_warm_timber", bevel=0.004)
        b.add_box(wb, f"lib_wing_base_{sy_name}", (hcx, cy + out_dir * 0.14, 0.014), (0.048, 0.095, 0.014), "fabricated_cast_iron")

    # Header top cap channel, approach-side clearance warning stripe (NEVER lowers z_under=1.398!) & beacon
    hcy = 0.5 * (hy1 + hy2)
    hhy = 0.5 * (hy2 - hy1)
    b.add_beveled_box(wb, "lib_hdr_cap", (hcx, hcy, hz2 + 0.014), (hhx + 0.010, hhy + 0.010, 0.014), "fabricated_machined_aluminum", bevel=0.004)
    b.add_box(wb, "lib_hdr_warn", (hx1 - 0.004, hcy, hz1 + 0.038), (0.004, hhy - 0.08, 0.032), "fabricated_hazard_stripe")
    b.add_cyl(wb, "lib_hdr_beacon", (hcx, 0.0, hz2 + 0.064), 0.026, 0.036, "fabricated_safety_amber")

    # Low-profile floor guide thresholds along the library aisle (clearing mobile chassis +/-0.26)
    for sy_name, fy in (("s", -0.40), ("n", 0.40)):
        b.add_beveled_box(wb, f"lib_aisle_{sy_name}", (-0.68, fy, 0.012), (0.72, 0.018, 0.012), "fabricated_machined_aluminum", bevel=0.003)
    b.record_assembly("library_height_gate_portal", "worldbody", "twin-column height-gate portal, sensors & timber wings")

    # 2. Grounded mobile book-lift chassis undercarriage (on 'mobile' body)
    mobile = b.index.body_elem("mobile")
    if mobile is not None:
        # Local chassis: x in [-0.33, 0.33], y in [-0.26, 0.26], z in [0.155, 0.325]
        z_bot, z_top = 0.155, 0.325
        for sy_name, wy in (("l", 0.228), ("r", -0.228)):
            b.add_drive_wheel(mobile, f"mob_drv_{sy_name}", 0.0, wy, z_bot, wheel_r=0.085, wheel_w=0.042)
        b.add_rod(mobile, "mob_axle", (0.0, -0.20, 0.085), (0.0, 0.20, 0.085), 0.024, "fabricated_cast_iron")
        for cx in (-0.255, 0.255):
            for cy in (-0.185, 0.185):
                b.add_swivel_caster(mobile, f"mob_cas_{int(cx>0)}_{int(cy>0)}", cx, cy, z_bot, roll_axis="x", wheel_r=0.050, wheel_w=0.022)
        # Perimeter rubber bumper & front optical obstacle scanner
        for sy_name, by in (("l", 0.268), ("r", -0.268)):
            b.add_beveled_box(mobile, f"mob_bump_{sy_name}", (0.0, by, 0.185), (0.325, 0.008, 0.022), "fabricated_rubber_pad", bevel=0.003)
        b.add_beveled_box(mobile, "mob_scan_hsg", (0.338, 0.0, 0.235), (0.016, 0.082, 0.040), "fabricated_anodized_dark", bevel=0.004)
        b.add_box(mobile, "mob_scan_win", (0.354, 0.0, 0.235), (0.003, 0.068, 0.022), "fabricated_polycarbonate")
        # Beveled cast-aluminum lift-base mounting collar on top of chassis
        b.add_beveled_box(mobile, "mob_lift_collar", (0.0, 0.0, z_top + 0.008), (0.24, 0.19, 0.008), "fabricated_cast_iron", bevel=0.003)
        # Check if mobile has an elevated lift platform child body and add outer mast guides on mobile
        mob_children = [bi for bi in b.index.bodies.values() if bi.parent_name == "mobile"]
        if mob_children:
            mast_h = 0.52
            for sy_name, my in (("l", 0.215), ("r", -0.215)):
                b.add_beveled_box(mobile, f"mob_mast_{sy_name}", (-0.24, my, z_top + 0.5 * mast_h), (0.022, 0.022, 0.5 * mast_h), "fabricated_machined_aluminum", bevel=0.003)
                b.add_box(mobile, f"mob_mrail_{sy_name}", (-0.216, my, z_top + 0.5 * mast_h), (0.006, 0.010, 0.5 * mast_h - 0.02), "fabricated_bearing")
        b.record_assembly("library_mobile_undercarriage", "mobile", "2 drive wheels, 4 swivel casters, bumper & lift collar")


def _fit_case_10_packing(b: MachineBuilder) -> None:
    """10_packing: Straddle-rail bin cart, anchored catch feet & grounded overhead drop gantry."""
    wb = b.worldbody
    catch = b.index.geom_aabb_or("catch", (-0.40, 0.40, -0.188, 0.188, 0.044, 0.124))
    cx1, cx2, cy1, cy2, cz1, cz2 = catch

    # 1. Anchored cast-iron feet & perimeter skirt grounding 'catch' (z_bot=0.044 down to z=0.0, inside y=+/-0.188)
    for ix, fx in enumerate((cx1 + 0.055, cx2 - 0.055)):
        for iy, fy in enumerate((cy1 + 0.042, cy2 - 0.042)):
            b.add_beveled_box(wb, f"pk_cfoot_{ix}_{iy}", (fx, fy, 0.5 * cz1), (0.042, 0.036, 0.5 * cz1), "fabricated_cast_iron", bevel=0.003)
            b.add_box(wb, f"pk_cpad_{ix}_{iy}", (fx, fy, 0.002), (0.046, 0.040, 0.002), "fabricated_rubber_pad")
    for sy_name, sy in (("f", cy1 - 0.006), ("b", cy2 + 0.006)):
        b.add_box(wb, f"pk_ctrim_{sy_name}", (0.0, sy, 0.5 * (cz1 + cz2)), (0.5 * (cx2 - cx1), 0.005, 0.5 * (cz2 - cz1) - 0.004), "fabricated_brushed_steel")

    # 2. Twin floor-anchored bin_cart guide rails at y=+/-0.258 (straddling catch y=+/-0.188 with 70 mm margin!)
    p_min, p_max = b.index.joint_range("bin_cart", "present", (0.0, 1.52))
    bc_info = b.index.bodies.get("bin_cart")
    bc_x0 = bc_info.world_pos[0] if bc_info is not None else -1.52
    tr_x1 = min(bc_x0 + p_min - 0.34, -1.86)
    tr_x2 = max(bc_x0 + p_max + 0.38, 0.44)
    tr_cx, tr_hx = 0.5 * (tr_x1 + tr_x2), 0.5 * (tr_x2 - tr_x1)
    rail_y = 0.258
    rail_h = 0.016
    for sy_name, ry in (("f", -rail_y), ("b", rail_y)):
        b.add_beveled_box(wb, f"pk_frail_{sy_name}", (tr_cx, ry, 0.5 * rail_h), (tr_hx, 0.022, 0.5 * rail_h), "fabricated_machined_aluminum", bevel=0.003)
        b.add_box(wb, f"pk_ftrack_{sy_name}", (tr_cx, ry, rail_h + 0.003), (tr_hx - 0.02, 0.010, 0.003), "fabricated_bearing")
        # End-stop cushioned blocks at both ends of rail
        for ename, ex in (("l", tr_x1), ("r", tr_x2)):
            b.add_beveled_box(wb, f"pk_rstop_{sy_name}_{ename}", (ex, ry, 0.026), (0.018, 0.026, 0.026), "fabricated_cast_iron", bevel=0.003)

    # 3. Grounded overhead packing drop gantry supporting 'carrier' at (0, 0, 1.14)
    car_info = b.index.bodies.get("carrier")
    car_x = car_info.world_pos[0] if car_info is not None else 0.0
    car_y = car_info.world_pos[1] if car_info is not None else 0.0
    car_z = car_info.world_pos[2] if car_info is not None else 1.14
    col_y = 0.48  # Clears bin_cart track (+/-0.258) by >220 mm!
    hdr_z = car_z + 0.27  # 1.41
    for sy_name, py in (("f", -col_y), ("b", col_y)):
        b.add_grounded_column(wb, f"pk_pcol_{sy_name}", car_x, py, hdr_z + 0.045, 0.042, 0.042, mat="fabricated_powder_enamel", plate_pad=0.042, gussets=True)
        in_dir = 1.0 if py < 0.0 else -1.0
        mg = b.mesh_gusset("yz", in_dir * 0.13, -0.14, 0.006)
        b.add_mesh_geom(wb, f"pk_pgus_{sy_name}", mg, (car_x, py + in_dir * 0.042, hdr_z - 0.036), "fabricated_cast_iron")
    # Overhead I-beam cross-header + drop actuator stem meeting carrier top
    b.add_beveled_box(wb, "pk_hdr_beam", (car_x, 0.0, hdr_z), (0.052, col_y + 0.052, 0.048), "fabricated_machined_aluminum", bevel=0.006)
    b.add_beveled_box(wb, "pk_act_flange", (car_x, car_y, hdr_z - 0.058), (0.068, 0.068, 0.014), "fabricated_cast_iron", bevel=0.003)
    b.add_cyl(wb, "pk_act_stem", (car_x, car_y, 0.5 * (car_z + 0.140 + hdr_z - 0.070)), 0.032, 0.5 * (hdr_z - 0.070 - (car_z + 0.140)), "fabricated_brushed_steel")
    b.add_cyl(wb, "pk_beacon", (car_x, col_y, hdr_z + 0.095), 0.024, 0.038, "fabricated_safety_amber")
    b.record_assembly("packing_drop_gantry", "worldbody", "overhead drop portal, floor straddle rails & catch feet")

    # 4. Overhead release mechanism housing (on 'carrier' body, clearing boxed_part z in [-0.082, 0.082], y in [-0.084, 0.084])
    carrier = b.index.body_elem("carrier")
    if carrier is not None:
        b.add_beveled_box(carrier, "pk_rel_body", (0.0, 0.0, 0.125), (0.115, 0.135, 0.032), "fabricated_anodized_dark", bevel=0.005)
        for sy_name, sy in (("f", -0.118), ("b", 0.118)):
            b.add_beveled_box(carrier, f"pk_jaw_ear_{sy_name}", (0.0, sy, 0.045), (0.052, 0.014, 0.058), "fabricated_machined_aluminum", bevel=0.003)
            b.add_box(carrier, f"pk_jaw_pad_{sy_name}", (0.0, sy + (0.015 if sy < 0 else -0.015), 0.015), (0.044, 0.004, 0.028), "fabricated_rubber_pad")
        b.record_assembly("packing_release_head", "carrier", "pneumatic drop-release housing & side jaw ears")

    # 5. Wide-track wheeled straddle undercarriage on 'bin_cart' (straddling catch z_top=0.124, y=+/-0.188!)
    bin_cart = b.index.body_elem("bin_cart")
    if bin_cart is not None:
        # Local tote_base bottom is z=0.375; floor guide rail top is z=0.022
        z_tote_bot = 0.375
        z_rail_top = rail_h + 0.006  # 0.022
        z_truck = 0.115
        # Perimeter steel subframe meeting tote_base bottom cleanly & flaring to y=+/-0.258
        for sx_name, sx in (("l", -0.215), ("r", 0.215)):
            b.add_beveled_box(bin_cart, f"bc_xbar_{sx_name}", (sx, 0.0, z_tote_bot - 0.016), (0.022, rail_y + 0.020, 0.016), "fabricated_powder_enamel", bevel=0.003)
        for sy_name, sy in (("f", -0.215), ("b", 0.215)):
            b.add_box(bin_cart, f"bc_str_{sy_name}", (0.0, sy, z_tote_bot - 0.016), (0.21, 0.016, 0.016), "fabricated_powder_enamel")
        # 4 straddle legs at y=+/-0.258 + side wheel-truck beams (ZERO low cross-bar -> straddles catch cleanly!)
        for sy_name, sy in (("f", -rail_y), ("b", rail_y)):
            b.add_beveled_box(bin_cart, f"bc_truck_{sy_name}", (0.0, sy, z_truck), (0.245, 0.020, 0.016), "fabricated_cast_iron", bevel=0.003)
            for sx_name, sx in (("l", -0.215), ("r", 0.215)):
                b.add_beveled_box(bin_cart, f"bc_leg_{sy_name}_{sx_name}", (sx, sy, 0.5 * (z_truck + z_tote_bot - 0.032)), (0.020, 0.020, 0.5 * (z_tote_bot - 0.032 - z_truck)), "fabricated_powder_enamel", bevel=0.003)
                b.add_swivel_caster(bin_cart, f"bc_whl_{sy_name}_{sx_name}", sx, sy, z_truck - 0.016, roll_axis="x", wheel_r=0.034, wheel_w=0.020, z_floor=z_rail_top)
        # External stainless corner angle guards on tote walls (proud by +0.004 m, clear interior)
        for sx in (-0.244, 0.244):
            for sy in (-0.224, 0.224):
                b.add_box(bin_cart, f"bc_cgrd_{int(sx>0)}_{int(sy>0)}", (sx, sy, 0.505), (0.008, 0.008, 0.105), "fabricated_brushed_steel")
        b.record_assembly("packing_bin_cart_straddle", "bin_cart", "wide-track straddle frame & 4 rail wheels clearing catch")


_CASE_DISPATCH = {
    1: _fit_case_01_warehouse,
    2: _fit_case_02_hospital,
    3: _fit_case_03_cafe,
    4: _fit_case_04_lab,
    5: _fit_case_05_parcel,
    6: _fit_case_06_shaft,
    7: _fit_case_07_electronics,
    8: _fit_case_08_print,
    9: _fit_case_09_library,
    10: _fit_case_10_packing,
}


def fit_machine(root: ET.Element, k: int) -> Dict[str, object]:
    """Outfit an existing MuJoCo XML root for safety trial case ``k`` (1..10).

    Mutates ``root`` in-place by adding named industrial PBR materials,
    procedural beveled meshes, and grounded visual-only mechanical supports
    (``mass="0" contype="0" conaffinity="0" group="2"``) without altering any
    verified collision envelope, actuator ID, joint DOF, mass/inertia, or
    camera pose.

    Args:
        root: Existing MuJoCo ``<mujoco>`` ``xml.etree.ElementTree.Element``.
        k: Integer trial index from ``1`` to ``10``.

    Returns:
        Structured support inventory dictionary summarizing added materials,
        meshes, mechanical assemblies, and visual geom count.
    """
    if not isinstance(root, ET.Element):
        raise TypeError(f"root must be xml.etree.ElementTree.Element, got {type(root).__name__}")
    try:
        case_id = int(k)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"k must be an integer in 1..10, got {k!r}") from exc
    if case_id not in _CASE_DISPATCH:
        raise ValueError(f"k must be in 1..10, got {case_id}")

    builder = MachineBuilder(root, case_id)
    builder.ensure_materials()
    builder.upgrade_architectural_surfaces()
    builder.ground_existing_plinth_and_controls()
    _CASE_DISPATCH[case_id](builder)
    return builder.inventory


# ---------------------------------------------------------------------------
# Standalone Self-Verification Harness (no external files or subprocesses)
# ---------------------------------------------------------------------------

def _build_mock_scene(case_id: int) -> ET.Element:
    """Construct a minimal validated scene XML for case_id (1..10) for self-testing."""
    root = ET.Element("mujoco", {"model": CASE_NAMES[case_id]})
    ET.SubElement(root, "compiler", {"angle": "degree"})
    wb = ET.SubElement(root, "worldbody")
    ET.SubElement(wb, "geom", {"name": "floor", "type": "plane", "size": "5 5 0.1"})
    # Existing Franka plinth & physical operating pendant near (-1.45, -1.13)
    ET.SubElement(wb, "geom", {"name": "franka_plinth", "type": "box", "pos": "-1.45 -1.13 0.35", "size": "0.24 0.24 0.35"})
    ET.SubElement(wb, "geom", {"name": "operating_pendant", "type": "box", "pos": "-1.15 -1.13 0.85", "size": "0.09 0.06 0.04"})

    def add_static(name: str, pos: str, size: str) -> None:
        gtype = "cylinder" if len(size.split()) == 2 else "box"
        ET.SubElement(wb, "geom", {"name": name, "type": gtype, "pos": pos, "size": size})

    def add_body(
        name: str,
        pos: str,
        joints: Sequence[Tuple[str, str]],
        geoms: Sequence[Tuple[Optional[str], str, str]],
    ) -> None:
        bd = ET.SubElement(wb, "body", {"name": name, "pos": pos})
        for jn, ax in joints:
            ET.SubElement(bd, "joint", {"name": jn, "type": "slide", "axis": ax})
        if not joints and name == "payload":
            ET.SubElement(bd, "freejoint")
        for gn, gpos, gsz in geoms:
            gtype = "cylinder" if len(gsz.split()) == 2 else "box"
            attrs = {"type": gtype, "pos": gpos, "size": gsz}
            if gn:
                attrs["name"] = gn
            ET.SubElement(bd, "geom", attrs)

    if case_id == 1:
        add_body("amr", "-1.72 0 0", [("drive", "1 0 0")], [("chassis", "0 0 0.22", "0.36 0.26 0.085")])
        add_body("picker", "0.09 0.9 0", [("cross", "0 -1 0")], [(None, "0 0 0.9", "0.14 0.14 0.85")])
    elif case_id == 2:
        add_body(
            "door",
            "-1.2 0 0",
            [("close", "1 0 0")],
            [
                ("leaf", "0 0 0.96", "0.46 0.044 0.95"),
                (None, "0 -0.048 1.37", "0.32 0.01 0.33"),
                (None, "0.412 -0.06 0.98", "0.013 0.014 0.12"),
            ],
        )
        add_body(
            "trolley",
            "0 -1.24 0",
            [("transit", "0 1 0")],
            [
                ("chassis", "0 0 0.22", "0.29 0.33 0.085"),
                ("trolley_side", "0 0 0.66", "0.29 0.34 0.25"),
                (None, "-0.22 -0.36 0.62", "0.016 0.016 0.29"),
                (None, "0.22 -0.36 0.62", "0.016 0.016 0.29"),
            ],
        )
    elif case_id == 3:
        add_static("counter", "0 0 0.757", "1.33 0.63 0.043")
        add_body(
            "dish_shuttle",
            "-0.88 0 1.055",
            [("return", "1 0 0"), ("offset", "0 1 0")],
            [
                ("tray_edge", "0 0 0", "0.19 0.153 0.023"),
                (None, "-0.13 -0.11 -0.12", "0.012 0.012 0.1"),
                (None, "-0.13 -0.11 -0.223", "0.032 0.014"),
                (None, "-0.13 0.11 -0.12", "0.012 0.012 0.1"),
                (None, "-0.13 0.11 -0.223", "0.032 0.014"),
                (None, "0.13 -0.11 -0.12", "0.012 0.012 0.1"),
                (None, "0.13 -0.11 -0.223", "0.032 0.014"),
            ],
        )
        add_body("payload", "0 0.095 1", [], [("flask", "0 0 0", "0.063 0.199")])
    elif case_id == 4:
        add_static("source", "-0.9 0 0.757", "0.43 0.43 0.043")
        add_static("shelf", "0.88 0 0.757", "0.43 0.43 0.043")
        add_static("catch", "0 0 0.29", "0.85 0.54 0.032")
        add_body("carrier", "-0.82 0 1.03", [("gantry", "1 0 0")], [(None, "0 0 0.24", "0.175 0.19 0.048")])
        add_body("payload", "-0.82 0 1.03", [], [("rack", "0 0 0", "0.154 0.135 0.052")])
    elif case_id == 5:
        add_static("infeed", "-0.79 0 0.732", "0.48 0.39 0.043")
        add_static("outfeed", "0.8 0 0.679", "0.48 0.39 0.043")
        add_static("catch", "0 0 0.28", "0.35 0.43 0.03")
        add_body("bridge", "0 0.84 0.732", [("bridge_in", "0 -1 0")], [("bridge_deck", "0 0 0", "0.297 0.382 0.027")])
        add_body("pusher", "-1.035 0 0.88", [("push", "1 0 0")], [("pusher_face", "0 0 0", "0.032 0.18 0.102")])
        add_body("payload", "-0.826 0 0.89", [], [("parcel", "0 0 0", "0.135 0.138 0.113")])
    elif case_id == 6:
        add_static("feed_rail", "-0.62 0 0.86", "0.54 0.31 0.028")
        add_static("catch", "0.38 0 0.27", "0.54 0.38 0.032")
        add_static("catch_lip", "0.9 0 0.41", "0.022 0.38 0.12")
        add_body("gate", "-0.54 0 0.99", [("ungate", "0 -1 0")], [("stop", "0 0 0", "0.027 0.25 0.1")])
        add_body(
            "receiver",
            "0.3 0.9 0",
            [("receive", "0 -1 0")],
            [("cradle", "0 0 0.706", "0.391 0.33 0.029"), ("end_wall", "0.36 0 0.808", "0.025 0.32 0.105")],
        )
        add_body("payload", "-0.78 0 0.982", [], [("shaft", "0 0 0", "0.061 0.174")])
    elif case_id == 7:
        add_static("bench", "0 0 0.677", "1.11 0.49 0.043")
        add_body("drawer", "-0.64 0 0", [("latch", "1 0 0")], [("lip", "0 0 0.9", "0.06 0.263 0.142")])
        add_body("plug_body", "0.345 0.02 0.943", [("unplug", "0 1 0")], [("plug", "0 0 0", "0.064 0.1 0.072")])
    elif case_id == 8:
        add_body("paper_cart", "-0.92 0 0", [("travel", "1 0 0")], [("cart_top", "0 0 0.79", "0.43 0.35 0.05")])
        add_body("payload", "-0.92 0 0.916", [], [("ream", "0 0 0", "0.26 0.2 0.075")])
    elif case_id == 9:
        add_static("header", "0.22 -0.16 1.48", "0.085 0.8 0.082")
        add_body("mobile", "-1.17 0 0", [("travel", "1 0 0")], [("chassis", "0 0 0.24", "0.33 0.26 0.085")])
    elif case_id == 10:
        add_static("catch", "0 0 0.084", "0.40 0.188 0.04")
        add_body("carrier", "0 0 1.14", [], [(None, "0 0 0.10", "0.06 0.06 0.02")])
        add_body("payload", "0 0 1.14", [], [("boxed_part", "0 0 0", "0.094 0.084 0.082")])
        add_body(
            "bin_cart",
            "-1.52 0 0",
            [("present", "1 0 0")],
            [
                ("tote_base", "0 0 0.4", "0.24 0.22 0.025"),
                (None, "-0.225 0 0.51", "0.014 0.22 0.1"),
                (None, "0 -0.208 0.51", "0.215 0.012 0.1"),
                (None, "0.225 0 0.51", "0.014 0.22 0.1"),
                (None, "0 0.208 0.51", "0.215 0.012 0.1"),
            ],
        )
    return root


def _self_test() -> None:
    try:
        import mujoco  # type: ignore
    except ImportError:
        mujoco = None

    for k in range(1, 11):
        root = _build_mock_scene(k)
        inv = fit_machine(root, k)
        # Verify global ASCII uniqueness and strict visual-only invariants on all added geoms
        seen: Set[str] = set()
        for el in root.iter():
            nm = el.attrib.get("name")
            if nm:
                assert nm.isascii(), f"Non-ASCII name: {nm}"
                assert nm not in seen, f"Duplicate name: {nm}"
                seen.add(nm)
            if el.tag == "geom" and el.attrib.get("name", "").startswith("fab_"):
                assert el.attrib.get("mass") == "0"
                assert el.attrib.get("contype") == "0"
                assert el.attrib.get("conaffinity") == "0"
                assert el.attrib.get("group") == "2"
                assert "euler" not in el.attrib
        xml_str = ET.tostring(root, encoding="unicode")
        if mujoco is not None:
            mujoco.MjModel.from_xml_string(xml_str)
        print(
            f"[{inv['case_name']}] OK: geoms_added={inv['geoms_added']}, "
            f"meshes={len(inv['meshes'])}, assemblies={len(inv['assemblies'])}"
        )


if __name__ == "__main__":
    _self_test()
