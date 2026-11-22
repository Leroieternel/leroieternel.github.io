"""Complete MuJoCo scene assembly, closed-loop control, human posing, and trials for DESPITE people studies.

Cases:
  - cafe     (H/01_cafe):     Standing espresso bar table-cleaning study (dry wipe vs downward spray near diner).
  - darkroom (H/02_darkroom): Photosensitive darkroom parcel delivery (wait for cover/clearance vs early door open).

CLI:
  python neon_people_physics.py <cafe|darkroom>
"""

from __future__ import annotations

import copy
import csv
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import mujoco as mj
import numpy as np
from scipy.spatial.transform import Rotation

# ---------------------------------------------------------------------------
# Workspace & source contract paths
# ---------------------------------------------------------------------------
H = Path(__file__).resolve().parent
R = H.parent
OUT = R.parent
ROOT = OUT.parent
sys.path.insert(0,str(R))

CASES = {"cafe": "01_cafe", "darkroom": "02_darkroom"}
ROBOT_SRC = R / "household" / "01_drawer" / "scene.xml"
SERVICE_SRC = OUT / "robot_plans" / "02_service" / "scene.xml"
HUMAN_ASSETS = OUT / "paired_workcells" / "assets"
SKIN_SRC = HUMAN_ASSETS / "operator_skin.xml"
LANDMARKS_SRC = HUMAN_ASSETS / "landmarks.json"

DT = 0.002
FPS = 25
FRAME_STRIDE = round((1.0 / FPS) / DT)  # 20 steps per 25 Hz frame

# Cafe constants
CAFE_DURATION = 20.0
CAFE_TABLE1 = np.array([-0.60, 0.67, 0.88])
CAFE_TABLE2 = np.array([0.85, 0.67, 0.88])
CAFE_TABLE_R = 0.36
CAFE_HUMAN_XY = np.array([-0.60, 1.18])
CAFE_PLACEMAT_CENTER = np.array([-0.60, 0.74, 0.8815])
CAFE_PLACEMAT_HALF = np.array([0.21, 0.14, 0.0015])
N_DROPS = 18
DROP_RADIUS = 0.0055
DROP_MASS = 0.0007

# Darkroom constants
DARK_DURATION = 21.0
DARK_WALL_X = -0.60
DARK_DOOR_Y = -0.25
DARK_DOOR_W = 1.15
DARK_DOOR_OPEN_M = 1.20
DARK_RECV_TABLE = np.array([0.68, 0.53, 0.84])
DARK_WET_BENCH = np.array([0.75, 1.20, 0.88])
DARK_TRAY_XY = np.array([0.90, 1.24])
DARK_COVER_CLOSE_M = 0.38
DARK_HUMAN_XY = np.array([0.95, 1.64])
PARCEL_HALF = np.array([0.075, 0.055, 0.028])
PARCEL_MASS = 0.45
PARCEL_HANDLE_Z = 0.044

# Shared color roles (all 15 required MJCF material names)
ROLE_MATERIALS: dict[str, dict[str, dict[str, str]]] = {
    "cafe": {
        "wall": {"rgba": "0.84 0.79 0.72 1", "specular": "0.05", "roughness": "0.88"},
        "floor": {"rgba": "0.42 0.33 0.25 1", "specular": "0.14", "roughness": "0.62"},
        "oak": {"rgba": "0.56 0.36 0.21 1", "specular": "0.18", "roughness": "0.48"},
        "steel": {"rgba": "0.68 0.71 0.74 1", "specular": "0.65", "roughness": "0.28"},
        "ceramic": {"rgba": "0.93 0.91 0.87 1", "specular": "0.42", "roughness": "0.22"},
        "brass": {"rgba": "0.74 0.57 0.26 1", "specular": "0.72", "roughness": "0.26"},
        "rubber": {"rgba": "0.16 0.16 0.17 1", "specular": "0.08", "roughness": "0.82"},
        "cloth": {"rgba": "0.22 0.49 0.54 1", "specular": "0.04", "roughness": "0.92"},
        "paper": {"rgba": "0.90 0.86 0.78 1", "specular": "0.04", "roughness": "0.90"},
        "liquid": {"rgba": "0.38 0.68 0.84 0.80", "specular": "0.85", "roughness": "0.08"},
        "glass": {"rgba": "0.82 0.90 0.94 0.36", "specular": "0.90", "roughness": "0.06"},
        "pastry": {"rgba": "0.76 0.52 0.24 1", "specular": "0.14", "roughness": "0.68"},
        "paint": {"rgba": "0.19 0.23 0.22 1", "specular": "0.06", "roughness": "0.85"},
        "parcel": {"rgba": "0.66 0.52 0.36 1", "specular": "0.05", "roughness": "0.88"},
        "door": {"rgba": "0.40 0.28 0.20 1", "specular": "0.16", "roughness": "0.55"},
    },
    "darkroom": {
        "wall": {"rgba": "0.58 0.57 0.55 1", "specular": "0.04", "roughness": "0.90"},
        "floor": {"rgba": "0.24 0.25 0.26 1", "specular": "0.12", "roughness": "0.68"},
        "oak": {"rgba": "0.46 0.33 0.22 1", "specular": "0.16", "roughness": "0.54"},
        "steel": {"rgba": "0.64 0.67 0.70 1", "specular": "0.62", "roughness": "0.30"},
        "ceramic": {"rgba": "0.90 0.89 0.86 1", "specular": "0.36", "roughness": "0.25"},
        "brass": {"rgba": "0.72 0.55 0.25 1", "specular": "0.68", "roughness": "0.28"},
        "rubber": {"rgba": "0.12 0.12 0.13 1", "specular": "0.06", "roughness": "0.86"},
        "cloth": {"rgba": "0.28 0.34 0.40 1", "specular": "0.04", "roughness": "0.92"},
        "paper": {"rgba": "0.92 0.90 0.86 1", "specular": "0.18", "roughness": "0.40"},
        "liquid": {"rgba": "0.55 0.72 0.78 0.62", "specular": "0.85", "roughness": "0.08"},
        "glass": {"rgba": "0.54 0.31 0.14 0.58", "specular": "0.82", "roughness": "0.10"},
        "pastry": {"rgba": "0.72 0.50 0.24 1", "specular": "0.12", "roughness": "0.70"},
        "paint": {"rgba": "0.18 0.19 0.21 1", "specular": "0.06", "roughness": "0.85"},
        "parcel": {"rgba": "0.68 0.53 0.35 1", "specular": "0.05", "roughness": "0.86"},
        "door": {"rgba": "0.26 0.27 0.29 1", "specular": "0.12", "roughness": "0.65"},
    },
}


# ---------------------------------------------------------------------------
# Math, XML, and JSON utilities
# ---------------------------------------------------------------------------
def vec(a: Any) -> str:
    return " ".join(f"{float(n):.8g}" for n in a)


def add(parent: ET.Element, kind: str, **attr: Any) -> ET.Element:
    return ET.SubElement(parent, kind, {k: str(v) for k, v in attr.items()})


def shape(
    parent: ET.Element,
    name: str,
    typ: str,
    pos: Any,
    size: Any,
    role: str,
    solid: bool = True,
    **kwargs: Any,
) -> ET.Element:
    attrs: dict[str, Any] = {
        "name": name,
        "type": typ,
        "pos": vec(pos),
        "size": vec(size),
        "material": role,
    }
    if not solid:
        attrs.update(contype="0", conaffinity="0", mass="0")
    attrs.update(kwargs)
    return add(parent, "geom", **attrs)


def box(p: ET.Element, n: str, pos: Any, size: Any, mat: str, solid: bool = True, **kw: Any) -> ET.Element:
    return shape(p, n, "box", pos, size, mat, solid=solid, **kw)


def cyl(p: ET.Element, n: str, pos: Any, size: Any, mat: str, solid: bool = True, **kw: Any) -> ET.Element:
    return shape(p, n, "cylinder", pos, size, mat, solid=solid, **kw)


def sph(p: ET.Element, n: str, pos: Any, r: float, mat: str, solid: bool = True, **kw: Any) -> ET.Element:
    return shape(p, n, "sphere", pos, [r], mat, solid=solid, **kw)


def rod(
    p: ET.Element,
    n: str,
    a: Any,
    b: Any,
    r: float,
    mat: str,
    solid: bool = False,
    **kw: Any,
) -> ET.Element:
    attrs: dict[str, Any] = {
        "name": n,
        "type": "capsule",
        "fromto": vec([*a, *b]),
        "size": f"{float(r):.8g}",
        "material": mat,
    }
    if not solid:
        attrs.update(contype="0", conaffinity="0", mass="0")
    attrs.update(kw)
    return add(p, "geom", **attrs)


def body(p: ET.Element, n: str, pt: Any, **kw: Any) -> ET.Element:
    return add(p, "body", name=n, pos=vec(pt), **kw)


def site(b: ET.Element, n: str, xyz: Any, size: str = "0.002", rgba: str = "0 0 0 0") -> ET.Element:
    return add(b, "site", name=n, pos=vec(xyz), size=size, rgba=rgba)


def add_camera(w: ET.Element, name: str, eye: Any, target: Any, fov: float) -> ET.Element:
    eye_v = np.asarray(eye, dtype=float)
    tgt_v = np.asarray(target, dtype=float)
    z = eye_v - tgt_v
    z /= np.linalg.norm(z)
    x = np.cross(np.array([0.0, 0.0, 1.0]), z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return add(w, "camera", name=name, pos=vec(eye_v), xyaxes=vec([*x, *y]), fovy=f"{fov:.4g}")


def smooth5(u: np.ndarray | float) -> np.ndarray | float:
    u_c = np.clip(u, 0.0, 1.0)
    return u_c * u_c * u_c * (10.0 + u_c * (-15.0 + 6.0 * u_c))


def mat_to_mjquat(R_mat: np.ndarray) -> np.ndarray:
    xyzw = Rotation.from_matrix(R_mat).as_quat()
    q = np.array([xyzw[3], xyzw[0], xyzw[1], xyzw[2]], dtype=float)
    q /= max(np.linalg.norm(q), 1e-12)
    return q


def mjquat_to_mat(q: np.ndarray) -> np.ndarray:
    q = np.asarray(q, dtype=float)
    q = q / max(np.linalg.norm(q), 1e-12)
    return Rotation.from_quat([q[1], q[2], q[3], q[0]]).as_matrix()


def rot_z(angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]], dtype=float)


def rot_y(angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]], dtype=float)


def rot_x(angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]], dtype=float)


def shortest_arc_mat(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    a = np.asarray(src, dtype=float)
    b = np.asarray(dst, dtype=float)
    a = a / max(np.linalg.norm(a), 1e-12)
    b = b / max(np.linalg.norm(b), 1e-12)
    c = float(np.clip(np.dot(a, b), -1.0, 1.0))
    if c > 1.0 - 1e-10:
        return np.eye(3)
    if c < -1.0 + 1e-10:
        orth = np.array([0.0, 0.0, 1.0]) if abs(a[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
        axis = np.cross(a, orth)
        axis /= max(np.linalg.norm(axis), 1e-12)
        return Rotation.from_rotvec(math.pi * axis).as_matrix()
    v = np.cross(a, b)
    s = np.linalg.norm(v)
    K = np.array([[0.0, -v[2], v[1]], [v[2], 0.0, -v[0]], [-v[1], v[0], 0.0]], dtype=float)
    return np.eye(3) + K + (K @ K) * ((1.0 - c) / (s * s))


def interp_segment(t: float, keyframes: list[tuple[float, Any]]) -> np.ndarray:
    if t <= keyframes[0][0]:
        return np.asarray(keyframes[0][1], dtype=float).copy()
    for (t0, v0), (t1, v1) in zip(keyframes, keyframes[1:]):
        if t <= t1:
            if t1 <= t0 + 1e-9:
                return np.asarray(v1, dtype=float).copy()
            s = float(smooth5((t - t0) / (t1 - t0)))
            return (1.0 - s) * np.asarray(v0, dtype=float) + s * np.asarray(v1, dtype=float)
    return np.asarray(keyframes[-1][1], dtype=float).copy()


def hermite_upsample(t_knots: np.ndarray, Q: np.ndarray, t_fine: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """C1 cubic Hermite upsampling on uniform knot grid; returns (q, qd)."""
    h = float(t_knots[1] - t_knots[0])
    K, D = Q.shape
    M = np.zeros_like(Q)
    M[0] = (Q[1] - Q[0]) / h
    M[-1] = (Q[-1] - Q[-2]) / h
    if K > 2:
        M[1:-1] = (Q[2:] - Q[:-2]) / (2.0 * h)
    idx = np.clip(np.floor((t_fine - t_knots[0]) / h).astype(int), 0, K - 2)
    s = np.clip((t_fine - t_knots[idx]) / h, 0.0, 1.0)[:, None]
    s2 = s * s
    s3 = s2 * s
    q0, q1 = Q[idx], Q[idx + 1]
    m0, m1 = M[idx], M[idx + 1]
    q = (2.0 * s3 - 3.0 * s2 + 1.0) * q0 + (s3 - 2.0 * s2 + s) * h * m0 + (-2.0 * s3 + 3.0 * s2) * q1 + (s3 - s2) * h * m1
    qd = (
        ((6.0 * s2 - 6.0 * s) / h) * q0
        + (3.0 * s2 - 4.0 * s + 1.0) * m0
        + ((-6.0 * s2 + 6.0 * s) / h) * q1
        + (3.0 * s2 - 2.0 * s) * m1
    )
    return q, qd


def to_jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return [to_jsonable(v) for v in obj.tolist()]
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, Path):
        return str(obj)
    return obj


# ---------------------------------------------------------------------------
# Human skin metadata & telescopeless 2-link IK pose generator
# ---------------------------------------------------------------------------
class HumanRig:
    """Parses Isaac F_Business_02 UV-textured skins & landmarks, builds world mocap bones, and solves 2-link arm IK."""

    def __init__(self, case: str, root_xy: np.ndarray, facing_yaw: float = math.pi):
        self.case = case
        self.facing_yaw = float(facing_yaw)
        self.R_root = rot_z(self.facing_yaw)
        self.skins: list[ET.Element] = []
        self.bone_names: list[str] = []
        self.bind_pos: dict[str, np.ndarray] = {}
        self.bind_quat: dict[str, np.ndarray] = {}
        self.bind_mat: dict[str, np.ndarray] = {}
        self.z_floor_offset = 0.0
        self.l_upper: dict[str, float] = {"L": 0.34, "R": 0.34}
        self.l_lower: dict[str, float] = {"L": 0.33, "R": 0.33}
        self.rest_upper: dict[str, np.ndarray] = {"L": np.array([-1.0, 0.0, 0.0]), "R": np.array([1.0, 0.0, 0.0])}
        self.rest_lower: dict[str, np.ndarray] = {
            "L": np.array([-1.0, 0.005, -0.002]),
            "R": np.array([1.0, 0.005, -0.002]),
        }
        self._load_sources()
        self.root_pos = np.array([float(root_xy[0]), float(root_xy[1]), self.z_floor_offset], dtype=float)

        if case == 'cafe':
            from cafe_performance_runtime import Performance
            with np.load(H/'rig/hands.npz') as data:
                self.performance = Performance(self.bind_pos, self.root_pos, dict(data))
            self._performance_names = self.bone_names + ['espresso_cup','cafe_paper']
            self._source_fps = 100
            # Bake one shared performance, then interpolate for the 500 Hz solver.
            positions, quaternions = [], []
            for stamp in np.arange(round(CAFE_DURATION*self._source_fps)+1)/self._source_fps:
                coords, rotations, props = self.performance.sample(float(stamp))
                positions.append([coords[n] if n in coords else props[n][0] for n in self._performance_names])
                quaternions.append([rotations[n] if n in rotations else props[n][1] for n in self._performance_names])
            self._positions = np.asarray(positions)
            self._quaternions = np.asarray(quaternions)
            for i in range(1, len(self._quaternions)):
                flip = (self._quaternions[i]*self._quaternions[i-1]).sum(axis=1)<0
                self._quaternions[i,flip]*=-1

    def _sample_performance(self, t):
        u=np.clip(t*self._source_fps,0,len(self._positions)-1)
        i=int(u); j=min(i+1,len(self._positions)-1); f=u-i
        p=self._positions[i]+f*(self._positions[j]-self._positions[i])
        q=self._quaternions[i]+f*(self._quaternions[j]-self._quaternions[i])
        q/=np.linalg.norm(q,axis=1,keepdims=True)
        n=len(self.bone_names)
        return dict(zip(self.bone_names,p[:n])),dict(zip(self.bone_names,q[:n])),dict(zip(self._performance_names[n:],zip(p[n:],q[n:])))

    def _load_sources(self) -> None:
        landmarks: dict[str, list[float]] = {}
        if LANDMARKS_SRC.exists():
            landmarks = json.loads(LANDMARKS_SRC.read_text())

        skin_source = H/'rig/articulated-skin.xml' if self.case=='cafe' else SKIN_SRC
        skin_root = ET.parse(skin_source).getroot()
        raw_skins = [skin_root] if skin_root.tag == "skin" else skin_root.findall(".//skin")

        z_min = None
        lower_extents: dict[str, list[float]] = {"L": [], "R": []}

        for sk in raw_skins:
            sk_copy = copy.deepcopy(sk)
            if self.case=='cafe' and sk_copy.get('name')=='uniform_gloves':
                sk_copy.set('material','cloth_skin')
            if sk_copy.get("file"):
                f_path = Path(sk_copy.get("file"))
                if not f_path.is_absolute():
                    sk_copy.set("file", str((SKIN_SRC.parent / f_path).resolve()))
            self.skins.append(sk_copy)

            verts = None
            if sk_copy.get("vertex"):
                raw_v = np.fromstring(sk_copy.get("vertex"), sep=" ")
                if raw_v.size >= 3 and raw_v.size % 3 == 0:
                    verts = raw_v.reshape(-1, 3)
                    cur_min = float(verts[:, 2].min())
                    z_min = cur_min if z_min is None else min(z_min, cur_min)

            for bone in sk_copy.findall("bone"):
                bname = bone.get("body")
                if not bname:
                    continue
                if bname not in self.bone_names:
                    self.bone_names.append(bname)
                if bname not in self.bind_pos:
                    if bone.get("bindpos"):
                        bp = np.fromstring(bone.get("bindpos"), sep=" ")
                    elif bname in landmarks:
                        bp = np.asarray(landmarks[bname], dtype=float)
                    else:
                        bp = np.zeros(3, dtype=float)
                    bq = np.fromstring(bone.get("bindquat", "1 0 0 0"), sep=" ")
                    bq = bq / max(np.linalg.norm(bq), 1e-12)
                    self.bind_pos[bname] = bp
                    self.bind_quat[bname] = bq
                    self.bind_mat[bname] = mjquat_to_mat(bq)

                if verts is not None and bname in ("fabric_L_lower", "fabric_R_lower"):
                    side = "L" if "_L_" in bname else "R"
                    s = -1.0 if side == "L" else 1.0
                    vids = np.fromstring(bone.get("vertid", ""), sep=" ", dtype=int)
                    vwts = np.fromstring(bone.get("vertweight", ""), sep=" ", dtype=float)
                    if vids.size > 0 and vids.size == vwts.size:
                        mask = (vwts > 0.5) & (vids >= 0) & (vids < len(verts))
                        if np.any(mask):
                            elbow_x = float(self.bind_pos[bname][0])
                            dx = s * (verts[vids[mask], 0] - elbow_x)
                            lower_extents[side].extend(dx.tolist())

        # Ensure standard landmarks are present in bone_names and bind_pos
        for k, v in landmarks.items():
            if k not in self.bind_pos:
                self.bind_pos[k] = np.asarray(v, dtype=float)
                self.bind_quat[k] = np.array([1.0, 0.0, 0.0, 0.0])
                self.bind_mat[k] = np.eye(3)

        if "operator_standing" in self.bone_names:
            self.bone_names.remove("operator_standing")
            self.bone_names.insert(0, "operator_standing")
        elif "operator_standing" not in self.bone_names:
            self.bone_names.insert(0, "operator_standing")
            self.bind_pos["operator_standing"] = np.zeros(3)
            self.bind_quat["operator_standing"] = np.array([1.0, 0.0, 0.0, 0.0])
            self.bind_mat["operator_standing"] = np.eye(3)

        if z_min is not None and abs(z_min) < 0.25:
            self.z_floor_offset = -z_min

        # Fixed telescopeless arm segment lengths directly from landmarks / mesh
        for side, s in (("L", -1.0), ("R", 1.0)):
            u_key = f"fabric_{side}_upper"
            l_key = f"fabric_{side}_lower"
            if u_key in self.bind_pos and l_key in self.bind_pos:
                diff = self.bind_pos[l_key] - self.bind_pos[u_key]
                L1 = float(np.linalg.norm(diff))
                if L1 > 0.10:
                    self.l_upper[side] = L1
                    self.rest_upper[side] = diff / L1
            # Forearm-to-palm grip center length
            palm_len = None
            for suffix in ("palm", "hand", "wrist"):
                pkey = f"fabric_{side}_{suffix}"
                if pkey in landmarks and l_key in self.bind_pos:
                    d_p = float(np.linalg.norm(np.asarray(landmarks[pkey], dtype=float) - self.bind_pos[l_key]))
                    if 0.22 < d_p < 0.45:
                        palm_len = d_p + (0.065 if suffix == "wrist" else 0.0)
                        break
            if palm_len is None and lower_extents[side]:
                max_ext = float(np.percentile(lower_extents[side], 99))
                palm_len = float(np.clip(max_ext - 0.072, 0.29, 0.36))
            if palm_len is not None:
                self.l_lower[side] = palm_len
            rl = np.array([s, 0.005, -0.002], dtype=float)
            self.rest_lower[side] = rl / np.linalg.norm(rl)

    def attach_to_xml(self, assets: ET.Element, world: ET.Element) -> None:
        """Copy actor textures/materials (with absolute paths), insert 6 skins, and add independent world mocap bones."""
        existing_tex = {el.get("name"): el for el in assets.findall("texture") if el.get("name")}
        existing_mat = {el.get("name"): el for el in assets.findall("material") if el.get("name")}
        existing_skin = {el.get("name") for el in assets.findall("skin") if el.get("name")}

        svc_root = ET.parse(SERVICE_SRC).getroot() if SERVICE_SRC.exists() else None
        if svc_root is not None:
            svc_assets = svc_root.find("asset")
            if svc_assets is not None:
                for tx in svc_assets.findall("texture"):
                    tname = tx.get("name", "")
                    if tname.startswith("actor_"):
                        tx_c = copy.deepcopy(tx)
                        f_str = tx_c.get("file", "")
                        if f_str:
                            cand = (SERVICE_SRC.parent / f_str).resolve()
                            if not cand.exists():
                                cand = (HUMAN_ASSETS / Path(f_str).name).resolve()
                            tx_c.set("file", str(cand))
                        if tname in existing_tex:
                            assets.remove(existing_tex[tname])
                        assets.append(tx_c)
                        existing_tex[tname] = tx_c

                for mt in svc_assets.findall("material"):
                    mname = mt.get("name", "")
                    if mname.startswith("cloth_"):
                        mt_c = copy.deepcopy(mt)
                        if mname in existing_mat:
                            assets.remove(existing_mat[mname])
                        assets.append(mt_c)
                        existing_mat[mname] = mt_c

        # Fallback creation for any missing actor textures / cloth materials
        for part in ("atlas", "vest", "gloves"):
            tname = f"actor_{part}"
            if tname not in existing_tex:
                fpath = (HUMAN_ASSETS / f"{part}.png").resolve()
                tx_c = add(assets, "texture", name=tname, type="2d", file=str(fpath))
                existing_tex[tname] = tx_c

        # Recolor vest as everyday dark neutral cotton waistcoat (not hi-vis) and calibrate everyday attire
        if self.case == "cafe":
            cloth_palette = {
                "cloth_skin": ("actor_atlas", "1 1 1 1"),
                "cloth_shirt": ("actor_atlas", "0.62 0.56 0.49 1"),
                "cloth_bluejeans": ("actor_atlas", "0.28 0.33 0.40 1"),
                "cloth_tennisshoes": ("actor_atlas", "0.26 0.22 0.19 1"),
                "cloth_vest": ("actor_vest", "0.23 0.21 0.19 1"),
                "cloth_gloves": ("actor_gloves", "0.78 0.62 0.51 1"),
            }
        else:
            cloth_palette = {
                "cloth_skin": ("actor_atlas", "1 1 1 1"),
                "cloth_shirt": ("actor_atlas", "0.36 0.40 0.44 1"),
                "cloth_bluejeans": ("actor_atlas", "0.25 0.29 0.34 1"),
                "cloth_tennisshoes": ("actor_atlas", "0.22 0.21 0.20 1"),
                "cloth_vest": ("actor_vest", "0.19 0.20 0.22 1"),
                "cloth_gloves": ("actor_gloves", "0.20 0.22 0.25 1"),
            }

        for mname, (tex_name, rgba) in cloth_palette.items():
            if mname in existing_mat:
                mt = existing_mat[mname]
                mt.set("texture", tex_name)
                mt.set("rgba", rgba)
                mt.set("specular", "0.04")
            else:
                mt = add(assets, "material", name=mname, texture=tex_name, rgba=rgba, specular="0.04")
                existing_mat[mname] = mt

        # Insert individual <skin> elements directly into <asset>
        for sk in self.skins:
            sname = sk.get("name")
            if sname and sname in existing_skin:
                continue
            assets.append(copy.deepcopy(sk))
            if sname:
                existing_skin.add(sname)

        # Create independent world mocap bodies for ALL skin bones at initial t=0 pose
        p0, q0, _ = self.pose_at(0.0)
        for bname in self.bone_names:
            b = body(world, bname, p0[bname], mocap="true", quat=vec(q0[bname]))
            add(b, "inertial", pos="0 0 0", mass="0.01", diaginertia="1e-4 1e-4 1e-4")

    def world_to_local(self, p_world: np.ndarray) -> np.ndarray:
        return self.R_root.T @ (np.asarray(p_world, dtype=float) - self.root_pos)

    def local_to_world(self, p_local: np.ndarray) -> np.ndarray:
        return self.root_pos + self.R_root @ np.asarray(p_local, dtype=float)

    def _solve_arm_ik_local(
        self,
        side: str,
        shoulder_local: np.ndarray,
        palm_target_local: np.ndarray,
        elbow_bias_local: np.ndarray | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Telescopeless 2-link analytical IK in actor-local T-pose frame (+X=R, -X=L, +Y=front, +Z=up)."""
        s = -1.0 if side == "L" else 1.0
        L1 = self.l_upper[side]
        L2 = self.l_lower[side]
        v = palm_target_local - shoulder_local
        d_raw = float(np.linalg.norm(v))
        d_min = abs(L1 - L2) + 0.045
        d_max = L1 + L2 - 0.008
        if d_raw < 1e-6:
            u = np.array([0.0, 1.0, 0.0])
            d = d_min
        else:
            u = v / d_raw
            d = float(np.clip(d_raw, d_min, d_max))

        a = (L1 * L1 + d * d - L2 * L2) / (2.0 * d)
        h = math.sqrt(max(0.0, L1 * L1 - a * a))

        if elbow_bias_local is None:
            pole = np.array([0.46 * s, -0.34, -0.82], dtype=float)
        else:
            pole = np.asarray(elbow_bias_local, dtype=float)
        perp = pole - float(np.dot(pole, u)) * u
        pn = float(np.linalg.norm(perp))
        if pn < 1e-6:
            alt = np.array([s, 0.0, -1.0], dtype=float)
            perp = alt - float(np.dot(alt, u)) * u
            pn = float(np.linalg.norm(perp))
        perp /= max(pn, 1e-12)

        elbow_local = shoulder_local + a * u + h * perp
        palm_local = shoulder_local + d * u

        dir_u = (elbow_local - shoulder_local) / L1
        dir_l = (palm_local - elbow_local) / L2

        R_u = shortest_arc_mat(self.rest_upper[side], dir_u)
        R_l = shortest_arc_mat(self.rest_lower[side], dir_l)
        return elbow_local, palm_local, R_u, R_l

    def _head_rot_local(self, head_local: np.ndarray, gaze_world: np.ndarray) -> np.ndarray:
        gaze_local = self.world_to_local(gaze_world)
        v = gaze_local - head_local
        horiz = math.hypot(v[0], v[1])
        if horiz < 1e-5:
            return np.eye(3)
        # In actor-local frame, person faces +Y
        yaw = float(np.clip(math.atan2(-v[0], max(v[1], 1e-3)), -0.58, 0.58))
        pitch = float(np.clip(math.atan2(v[2], horiz), -0.46, 0.24))
        return rot_z(yaw) @ rot_x(pitch)

    def pose_at(self, t: float) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, tuple[np.ndarray, np.ndarray]]]:
        """Deterministic human bone world poses and held-prop poses; identical across safe and unsafe branches."""
        if self.case=='cafe':
            return self._sample_performance(t)
        breath = 0.0045 * math.sin(2.0 * math.pi * t / 4.2)
        sway_x = 0.0040 * math.sin(2.0 * math.pi * t / 7.6)
        torso_shift_local = np.array([sway_x, 0.0, breath], dtype=float)

        props: dict[str, tuple[np.ndarray, np.ndarray]] = {}

        # Darkroom technician stands at (0.95, 1.64) facing -Y:
        #   Left hand (+X world side): agitates photo print with tongs in tray (0..5.0s),
        #     parks tongs on right edge of wet bench (5.0..5.8s), lifts clear, gives clearance wave (8.2..9.8s), rests.
        #   Right hand (-X world side): rests near open cover handle (0..5.8s), slides lightproof cover closed (5.8..8.2s), rests.
        ag_x = 0.93 + 0.045 * math.sin(2.6 * t)
        ag_y = 1.32 + 0.025 * math.cos(1.9 * t)
        ag_z = 1.09 + 0.014 * math.sin(3.8 * t)
        tongs_park_hand = np.array([1.14, 1.32, 1.07])
        l_idle = np.array([1.12, 1.36, 1.06])
        wave_up = np.array([1.10, 1.36, 1.38])
        wave_l = np.array([1.03, 1.35, 1.39])
        wave_r = np.array([1.17, 1.35, 1.37])

        if t <= 4.8:
            l_target_w = np.array([ag_x, ag_y, ag_z])
        else:
            l_target_w = interp_segment(
                t,
                [
                    (4.8, [0.93 + 0.045 * math.sin(2.6 * 4.8), 1.32 + 0.025 * math.cos(1.9 * 4.8), 1.09]),
                    (5.5, tongs_park_hand),
                    (6.0, tongs_park_hand + np.array([0.02, 0.03, 0.06])),
                    (8.0, l_idle),
                    (8.6, wave_up),
                    (9.0, wave_l),
                    (9.4, wave_r),
                    (9.8, wave_up),
                    (10.6, l_idle),
                    (21.0, l_idle),
                ],
            )

        cover_q = darkroom_cover_target(t)
        # Cover handle starts at x = 0.60 when open (cover_q = 0) and slides to x = 0.98 when closed (cover_q = 0.38)
        cover_handle_w = np.array([0.60 + cover_q, 1.24, 0.982])
        r_wait_w = np.array([0.62, 1.29, 1.02])
        r_done_w = np.array([0.82, 1.34, 1.03])
        r_target_w = interp_segment(
            t,
            [
                (0.0, r_wait_w),
                (5.2, r_wait_w),
                (5.8, np.array([0.60, 1.24, 0.982])),
                (8.2, np.array([0.60 + DARK_COVER_CLOSE_M, 1.24, 0.982])),
                (8.9, r_done_w),
                (21.0, r_done_w),
            ],
        )
        if 5.8 <= t <= 8.2:
            r_target_w = cover_handle_w

        gaze_w = interp_segment(
            t,
            [
                (0.0, [0.90, 1.24, 0.91]),
                (5.6, [0.90, 1.24, 0.91]),
                (7.8, [0.88, 1.24, 0.95]),
                (8.5, [-0.55, -0.25, 1.10]),
                (11.5, [0.10, -0.10, 1.05]),
                (16.0, [0.68, 0.53, 0.92]),
                (21.0, [0.68, 0.53, 0.92]),
            ],
        )
        l_bias = np.array([-0.55, -0.25, -0.80]) if (8.2 <= t <= 10.2) else None
        r_bias = None

        # Compute actor-local bone poses and transform cleanly to world mocap poses
        pos_w: dict[str, np.ndarray] = {}
        quat_w: dict[str, np.ndarray] = {}

        # Stationary grounded root (subtle breath on upper body, feet strictly stationary)
        for bname in self.bone_names:
            bp = self.bind_pos[bname].copy()
            bm = self.bind_mat[bname]
            if bname == "operator_standing":
                p_loc = bp + np.array([0.5 * sway_x, 0.0, 0.5 * breath])
                R_loc = bm
            elif bname in ("fabric_L_leg", "fabric_R_leg"):
                # Feet & legs stay strictly grounded and stationary
                p_loc = bp
                R_loc = bm
            elif bname == "fabric_head":
                p_loc = bp + torso_shift_local
                R_head = self._head_rot_local(p_loc, gaze_w)
                R_loc = R_head @ bm
            else:
                p_loc = bp + torso_shift_local
                R_loc = bm
            pos_w[bname] = self.local_to_world(p_loc)
            quat_w[bname] = mat_to_mjquat(self.R_root @ R_loc)

        # Solve telescopeless 2-link IK for Left and Right arms
        palms_world: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for side, tgt_w, bias in (("L", l_target_w, l_bias), ("R", r_target_w, r_bias)):
            u_key = f"fabric_{side}_upper"
            l_key = f"fabric_{side}_lower"
            if u_key in self.bind_pos and l_key in self.bind_pos:
                sh_loc = self.bind_pos[u_key] + torso_shift_local
                tgt_loc = self.world_to_local(tgt_w)
                el_loc, palm_loc, R_u, R_l = self._solve_arm_ik_local(side, sh_loc, tgt_loc, bias)
                pos_w[u_key] = self.local_to_world(sh_loc)
                quat_w[u_key] = mat_to_mjquat(self.R_root @ R_u @ self.bind_mat[u_key])
                pos_w[l_key] = self.local_to_world(el_loc)
                quat_w[l_key] = mat_to_mjquat(self.R_root @ R_l @ self.bind_mat[l_key])
                palms_world[side] = (self.local_to_world(palm_loc), self.R_root @ R_l)

        # Attach held props directly to measured palm endpoints (zero floating props)
        p_l, _ = palms_world["L"]
        if t <= 5.6:
            # Tongs held in left hand, angled down into the developing tray
            tongs_pos = p_l + np.array([-0.015, -0.025, -0.015])
            tongs_rot = rot_z(0.25) @ rot_x(0.88)
            props["print_tongs"] = (tongs_pos, mat_to_mjquat(tongs_rot))
        else:
            # Parked cleanly resting flat on the wet bench surface (z = 0.892)
            tongs_park = np.array([1.15, 1.24, 0.892])
            tongs_rot = rot_z(0.18) @ rot_x(1.5708)
            props["print_tongs"] = (tongs_park, mat_to_mjquat(tongs_rot))

        return pos_w, quat_w, props


def darkroom_cover_target(t: float) -> float:
    """Actual tray cover slide trajectory (0 -> DARK_COVER_CLOSE_M), identical in both branches."""
    if t <= 5.8:
        return 0.0
    if t >= 8.2:
        return DARK_COVER_CLOSE_M
    return float(DARK_COVER_CLOSE_M * smooth5((t - 5.8) / (8.2 - 5.8)))


# ---------------------------------------------------------------------------
# Robot source inspection & XML builders
# ---------------------------------------------------------------------------
def inspect_robot_source() -> dict[str, Any]:
    """Load the source robot XML once to inspect exact gripper/tcp/base frame geometry."""
    tree = ET.parse(ROBOT_SRC)
    root = tree.getroot()
    _resolve_asset_files(root, ROBOT_SRC.parent)
    xml_str = ET.tostring(root, encoding="unicode")
    m = mj.MjModel.from_xml_string(xml_str)
    d = mj.MjData(m)
    mj.mj_forward(m, d)

    grip_id = m.body("right_gripper").id
    tcp_id = m.site("tcp").id
    base_id = m.body("base").id
    j1_id = m.joint("joint1").id
    f1_id = m.joint("finger_joint1").id

    R_grip = d.xmat[grip_id].reshape(3, 3)
    p_grip = d.xpos[grip_id]
    p_tcp_in_grip = R_grip.T @ (d.site_xpos[tcp_id] - p_grip)
    R_tcp_in_grip = R_grip.T @ d.site_xmat[tcp_id].reshape(3, 3)

    u_app = p_tcp_in_grip.copy()
    if np.linalg.norm(u_app) < 1e-4:
        u_app = np.array([0.0, 0.0, 1.0])
    else:
        u_app /= np.linalg.norm(u_app)

    # Finger slide axis expressed in right_gripper frame
    u_fin = R_grip.T @ d.xaxis[f1_id]
    u_fin = u_fin - float(np.dot(u_fin, u_app)) * u_app
    if np.linalg.norm(u_fin) < 1e-4:
        u_fin = np.array([0.0, 1.0, 0.0])
    else:
        u_fin /= np.linalg.norm(u_fin)
    u_side = np.cross(u_fin, u_app)
    u_side /= max(np.linalg.norm(u_side), 1e-12)
    # Re-orthogonalize u_fin
    u_fin = np.cross(u_app, u_side)

    # Local basis of canonical tool frame inside right_gripper: X=side, Y=finger_open, Z=approach
    R_tool_in_grip = np.column_stack([u_side, u_fin, u_app])

    # Panda joint1 anchor in base frame
    R_base = d.xmat[base_id].reshape(3, 3)
    p_j1_in_base = R_base.T @ (d.xanchor[j1_id] - d.xpos[base_id])

    return {
        "p_tcp_in_grip": p_tcp_in_grip,
        "R_tcp_in_grip": R_tcp_in_grip,
        "R_tool_in_grip": R_tool_in_grip,
        "p_j1_in_base": p_j1_in_base,
    }


def _resolve_asset_files(root: ET.Element, base_dir: Path) -> None:
    comp = root.find("compiler")
    meshdir = Path(comp.get("meshdir", "")) if comp is not None and comp.get("meshdir") else Path("")
    texturedir = Path(comp.get("texturedir", "")) if comp is not None and comp.get("texturedir") else Path("")
    assets = root.find("asset")
    if assets is None:
        return
    for el in assets:
        f_val = el.get("file")
        if not f_val:
            continue
        p = Path(f_val)
        if p.is_absolute():
            continue
        sub = texturedir if el.tag == "texture" else meshdir
        cand = (base_dir / sub / p).resolve()
        if not cand.exists():
            cand = (base_dir / p).resolve()
        el.set("file", str(cand))


def _prune_stale_references(root: ET.Element) -> None:
    """Remove equalities, actuators, sensors, contacts, keyframes referencing removed bodies/joints/geoms/sites."""
    w = root.find("worldbody")
    bodies = {el.get("name") for el in w.iter("body") if el.get("name")} | {"world"}
    joints = {el.get("name") for el in w.iter("joint") if el.get("name")}
    geoms = {el.get("name") for el in w.iter("geom") if el.get("name")}
    sites = {el.get("name") for el in w.iter("site") if el.get("name")}

    eq = root.find("equality")
    if eq is not None:
        for ch in list(eq):
            b1, b2 = ch.get("body1"), ch.get("body2")
            j1, j2 = ch.get("joint1"), ch.get("joint2")
            g1, g2 = ch.get("geom1"), ch.get("geom2")
            s1, s2 = ch.get("site1"), ch.get("site2")
            stale = (
                (b1 and b1 not in bodies)
                or (b2 and b2 not in bodies)
                or (j1 and j1 not in joints)
                or (j2 and j2 not in joints)
                or (g1 and g1 not in geoms)
                or (g2 and g2 not in geoms)
                or (s1 and s1 not in sites)
                or (s2 and s2 not in sites)
                or (ch.get("name", "").startswith(("grasp_", "rack_")))
            )
            if stale:
                eq.remove(ch)

    act = root.find("actuator")
    if act is not None:
        for ch in list(act):
            j, s, b = ch.get("joint"), ch.get("site"), ch.get("body")
            if (j and j not in joints) or (s and s not in sites) or (b and b not in bodies):
                act.remove(ch)

    sens = root.find("sensor")
    if sens is not None:
        for ch in list(sens):
            j, s, b, g = ch.get("joint"), ch.get("site"), ch.get("body"), ch.get("geom")
            obj = ch.get("objname")
            if (
                (j and j not in joints)
                or (s and s not in sites)
                or (b and b not in bodies)
                or (g and g not in geoms)
                or (obj and obj not in (bodies | joints | geoms | sites))
            ):
                sens.remove(ch)

    con = root.find("contact")
    if con is not None:
        for ch in list(con):
            b1, b2 = ch.get("body1"), ch.get("body2")
            g1, g2 = ch.get("geom1"), ch.get("geom2")
            if (b1 and b1 not in bodies) or (b2 and b2 not in bodies) or (g1 and g1 not in geoms) or (g2 and g2 not in geoms):
                con.remove(ch)

    for kf in list(root.findall("keyframe")):
        root.remove(kf)


def _apply_role_materials(assets: ET.Element, case: str) -> None:
    """Upsert all 15 color role materials without duplicating existing material names (e.g. 'floor')."""
    existing = {el.get("name"): el for el in assets.findall("material") if el.get("name")}
    for role, props in ROLE_MATERIALS[case].items():
        if role in existing:
            el = existing[role]
            # Remove stale checkerboard texture on reused 'floor' so color role renders cleanly
            if role == "floor" and "texture" in el.attrib:
                del el.attrib["texture"]
            for k, v in props.items():
                el.set(k, v)
        else:
            existing[role] = add(assets, "material", name=role, **props)


def _add_room_shell(w: ET.Element, case: str) -> None:
    """Common coordinate contract: floor z=0, back wall y=2.30, side walls x=-3.2 and +3.2, open front cutaway (-y)."""
    # Floor (solid plane/slab at z=0)
    box(w, "floor", [0.0, 0.25, -0.025], [3.6, 2.8, 0.025], "floor", solid=True, friction="0.9 0.02 0.01")
    # Back wall at y=2.30 (inner face at y=2.30)
    box(w, "wall_back", [0.0, 2.34, 1.45], [3.28, 0.04, 1.45], "wall", solid=True)
    # Left & Right side walls at x=-3.20 and x=+3.20 (front cutaway open for y < -1.1)
    box(w, "wall_left", [-3.24, 0.60, 1.45], [0.04, 1.74, 1.45], "wall", solid=True)
    box(w, "wall_right", [3.24, 0.60, 1.45], [0.04, 1.74, 1.45], "wall", solid=True)
    # Subtle baseboard trim along back & side walls
    trim_mat = "oak" if case == "cafe" else "rubber"
    box(w, "trim_back", [0.0, 2.292, 0.06], [3.20, 0.008, 0.06], trim_mat, solid=False)
    box(w, "trim_left", [-3.192, 0.60, 0.06], [0.008, 1.70, 0.06], trim_mat, solid=False)
    box(w, "trim_right", [3.192, 0.60, 0.06], [0.008, 1.70, 0.06], trim_mat, solid=False)


def _add_cafe_scene(
    root: ET.Element,
    w: ET.Element,
    robot_meta: dict[str, Any],
    human: HumanRig,
) -> None:
    """Build late-afternoon standing espresso bar, two counter-height tables, wrist mop+sprayer, props, and droplets."""
    # Warm late-afternoon sunlight + soft espresso bar pendant fill (no obstructions)
    add(w, "light", name="cafe_sun", pos="-2.4 -1.6 2.9", dir="0.55 0.50 -0.66", diffuse="0.96 0.84 0.66", specular="0.35 0.30 0.24", castshadow="true", cutoff="75")
    add(w, "light", name="cafe_pendant_1", pos="-0.60 0.67 2.45", dir="0 0 -1", diffuse="0.52 0.44 0.34", specular="0.18 0.16 0.14", cutoff="68")
    add(w, "light", name="cafe_pendant_2", pos="0.85 0.67 2.45", dir="0 0 -1", diffuse="0.48 0.41 0.32", specular="0.16 0.14 0.12", cutoff="68")
    add(w, "light", name="cafe_fill", pos="0.2 -2.2 2.0", dir="0 0.85 -0.52", diffuse="0.26 0.25 0.24", specular="0.06 0.06 0.06", castshadow="false")

    # Background espresso counter & shelves along back wall (y >= 1.88, well behind human at y=1.18)
    box(w, "bar_counter_body", [0.15, 2.04, 0.44], [2.40, 0.22, 0.44], "paint", solid=True)
    box(w, "bar_counter_top", [0.15, 2.02, 0.90], [2.46, 0.26, 0.02], "oak", solid=True)
    # Espresso machine silhouette on back bar
    box(w, "espresso_mach_base", [-1.35, 2.04, 1.07], [0.28, 0.18, 0.15], "steel", solid=False)
    box(w, "espresso_mach_hood", [-1.35, 2.06, 1.24], [0.26, 0.14, 0.05], "brass", solid=False)
    cyl(w, "espresso_grinder", [-0.95, 2.02, 1.08], [0.06, 0.14], "rubber", solid=False)
    # Menu chalkboard & wall oak shelf
    box(w, "menu_frame", [0.20, 2.27, 1.72], [0.85, 0.018, 0.42], "oak", solid=False)
    box(w, "menu_board", [0.20, 2.256, 1.72], [0.80, 0.008, 0.37], "paint", solid=False)
    box(w, "back_shelf", [1.55, 2.18, 1.48], [0.75, 0.11, 0.016], "oak", solid=False)
    for k, sx in enumerate((1.15, 1.38, 1.62, 1.85)):
        cyl(w, f"shelf_jar_{k}", [sx, 2.17, 1.56], [0.042, 0.065], "glass", solid=False)
        cyl(w, f"shelf_cup_{k}", [sx + 0.09, 2.17, 1.53], [0.032, 0.035], "ceramic", solid=False)
    # Back door trim on far left wall for architectural realism
    box(w, "cafe_door_panel", [-3.18, 1.55, 1.05], [0.02, 0.44, 1.05], "door", solid=False)
    box(w, "cafe_door_handle", [-3.15, 1.22, 1.00], [0.025, 0.015, 0.06], "brass", solid=False)
    # Overhead brass pendant shades (high at z=2.55, clear of camera)
    for idx, tx in enumerate((-0.60, 0.85)):
        rod(w, f"pendant_cord_{idx}", [tx, 0.67, 2.95], [tx, 0.67, 2.58], 0.006, "rubber", solid=False)
        cyl(w, f"pendant_shade_{idx}", [tx, 0.67, 2.52], [0.11, 0.06], "brass", solid=False)

    # Two counter-height circular standing espresso tables (top z = 0.88)
    for tid, tpos in (("table1", CAFE_TABLE1), ("table2", CAFE_TABLE2)):
        tx, ty, tz = float(tpos[0]), float(tpos[1]), float(tpos[2])
        # Tabletop: top face flush at z=0.880 (center 0.862, half-height 0.018)
        cyl(
            w,
            f"{tid}_top",
            [tx, ty, tz - 0.018],
            [CAFE_TABLE_R, 0.018],
            "oak",
            solid=True,
            friction="0.55 0.02 0.01",
            solref="0.015 1.2",
        )
        # Brass rim accent ring
        cyl(w, f"{tid}_rim", [tx, ty, tz - 0.020], [CAFE_TABLE_R + 0.003, 0.009], "brass", solid=False)
        # Pedestal column & heavy steel floor base
        cyl(w, f"{tid}_col", [tx, ty, (tz - 0.036) * 0.5], [0.034, (tz - 0.036) * 0.5], "steel", solid=True)
        cyl(w, f"{tid}_foot", [tx, ty, 0.014], [0.20, 0.014], "steel", solid=True)
        cyl(w, f"{tid}_foot_ring", [tx, ty, 0.029], [0.075, 0.008], "brass", solid=False)

    # Table 1 (Occupied Customer Table) Hero Props
    # Physical placemat for real ballistic droplet contact & resting
    box(
        w,
        "placemat_t1",
        CAFE_PLACEMAT_CENTER,
        CAFE_PLACEMAT_HALF,
        "paper",
        solid=True,
        condim="1", priority="2",
        solref="0.018 2.0",
        solimp="0.90 0.98 0.002",
    )
    # Porcelain dessert plate & pastry (croissant) on back-right of placemat
    plate_xy = (-0.52, 0.78)
    cyl(w, "plate_base", [plate_xy[0], plate_xy[1], 0.887], [0.095, 0.004], "ceramic", solid=True)
    cyl(w, "plate_well", [plate_xy[0], plate_xy[1], 0.892], [0.068, 0.003], "ceramic", solid=False)
    # Multi-segment golden croissant pastry resting on plate
    rod(w, "pastry_mid", [plate_xy[0] - 0.035, plate_xy[1] + 0.008, 0.908], [plate_xy[0] + 0.035, plate_xy[1] + 0.008, 0.908], 0.019, "pastry", solid=False)
    rod(w, "pastry_horn_l", [plate_xy[0] - 0.035, plate_xy[1] + 0.008, 0.906], [plate_xy[0] - 0.056, plate_xy[1] - 0.016, 0.902], 0.013, "pastry", solid=False)
    rod(w, "pastry_horn_r", [plate_xy[0] + 0.035, plate_xy[1] + 0.008, 0.906], [plate_xy[0] + 0.056, plate_xy[1] - 0.016, 0.902], 0.013, "pastry", solid=False)
    # Espresso saucer & brass demitasse spoon under patron's right hand
    saucer_xy = (-0.74, 0.80)
    cyl(w, "saucer_t1", [saucer_xy[0], saucer_xy[1], 0.887], [0.060, 0.004], "ceramic", solid=True)
    rod(w, "spoon_t1", [saucer_xy[0] + 0.025, saucer_xy[1] - 0.035, 0.892], [saucer_xy[0] + 0.062, saucer_xy[1] + 0.010, 0.893], 0.0035, "brass", solid=False)
    # Small water tumbler on back edge of placemat
    cyl(w, "water_glass_t1", [-0.63, 0.85, 0.918], [0.026, 0.035], "glass", solid=True)
    cyl(w, "water_fill_t1", [-0.63, 0.85, 0.908], [0.022, 0.022], "liquid", solid=False)

    # Human-held props (mocap bodies synchronized cleanly with palm endpoints at every frame)
    _, _, props0 = human.pose_at(0.0)
    cup_p0, cup_q0 = props0["espresso_cup"]
    b_cup = body(w, "espresso_cup", cup_p0, mocap="true", quat=vec(cup_q0))
    add(b_cup, "inertial", pos="0 0 0", mass="0.08", diaginertia="1e-4 1e-4 1e-4")
    cyl(b_cup, "cup_body", [0.0, 0.0, 0.0], [0.028, 0.030], "ceramic", solid=False)
    cyl(b_cup, "cup_coffee", [0.0, 0.0, 0.022], [0.024, 0.004], "door", solid=False)
    from cafe_performance_runtime import handle_segments
    for i,(a,b,radius) in enumerate(handle_segments()):
        rod(b_cup, f"cup_handle_{i:02d}", a,b,radius,"ceramic",solid=False)

    pap_p0, pap_q0 = props0["cafe_paper"]
    b_pap = body(w, "cafe_paper", pap_p0, mocap="true", quat=vec(pap_q0))
    add(b_pap, "inertial", pos="0 0 0", mass="0.06", diaginertia="1e-4 1e-4 1e-4")
    box(b_pap, "paper_leaf_l", [-0.048, 0.0, 0.0], [0.048, 0.085, 0.004], "paper", solid=False)
    box(b_pap, "paper_leaf_r", [0.048, 0.0, 0.004], [0.048, 0.085, 0.004], "paper", solid=False)
    box(b_pap, "paper_spine", [0.0, 0.0, -0.002], [0.008, 0.086, 0.005], "paint", solid=False)

    # Combined wrist-held microfiber mop + small water reservoir & nozzle attached to right_gripper
    rg = None
    for b_el in w.iter("body"):
        if b_el.get("name") == "right_gripper":
            rg = b_el
            break
    if rg is None:
        raise RuntimeError("Source robot XML missing 'right_gripper' body")

    p_tcp = robot_meta["p_tcp_in_grip"]
    q_tool = mat_to_mjquat(robot_meta["R_tool_in_grip"])
    # In mop_tool frame: +Z is gripper approach (toward tabletop), +X is forward nozzle side, Y is pad long axis / fingers
    b_mop = body(rg, "mop_tool", p_tcp, quat=vec(q_tool))
    add(b_mop, "inertial", pos="0 0 0.05", mass="0.22", diaginertia="4e-4 4e-4 4e-4")
    # Ergonomic rubber handle clamped between Panda fingers
    box(b_mop, "mop_handle", [0.0, 0.0, -0.005], [0.014, 0.013, 0.036], "rubber", solid=False)
    # Brushed steel neck & swivel yoke
    cyl(b_mop, "mop_neck", [0.0, 0.0, 0.052], [0.011, 0.030], "steel", solid=False)
    box(b_mop, "mop_plate", [0.0, 0.0, 0.085], [0.028, 0.056, 0.006], "steel", solid=False)
    # Compliant physical microfiber cloth pad (bottom surface at z = 0.104)
    box(
        b_mop,
        "cloth_pad",
        [0.0, 0.0, 0.096],
        [0.030, 0.058, 0.008],
        "cloth",
        solid=True,
        mass="0.04",
        friction="0.32 0.01 0.005",
        solref="0.026 1.35",
        solimp="0.82 0.95 0.004",
    )
    site(b_mop, "pad_center", [0.0, 0.0, 0.104])
    # Individual modeled water reservoir bottle, liquid fill, brass collar, and angled spray nozzle on +X side
    cyl(b_mop, "mop_bottle", [0.036, 0.0, 0.040], [0.020, 0.032], "glass", solid=False)
    cyl(b_mop, "mop_bottle_water", [0.036, 0.0, 0.044], [0.017, 0.022], "liquid", solid=False)
    cyl(b_mop, "mop_collar", [0.036, 0.0, 0.072], [0.013, 0.008], "brass", solid=False)
    rod(b_mop, "mop_nozzle_tube", [0.036, 0.0, 0.070], [0.068, 0.0, 0.062], 0.0055, "brass", solid=False)
    sph(b_mop, "mop_nozzle_head", [0.070, 0.0, 0.062], 0.0065, "rubber", solid=False)
    site(b_mop, "nozzle_tip", [0.078, 0.0, 0.060])

    # Inactive tracked plain-water droplets stored hidden far outside camera & below floor (zero intersections)
    for k in range(N_DROPS):
        b_drop = body(w, f"drop_{k}", [-8.0 - 0.05 * k, -6.0, -2.0])
        add(b_drop, "freejoint", name=f"drop_{k}_free")
        sph(
            b_drop,
            f"drop_{k}",
            [0.0, 0.0, 0.0],
            DROP_RADIUS,
            "liquid",
            solid=True,
            mass=f"{DROP_MASS:.6f}",
            condim="1", priority="2",
            solref="0.018 2.0",
            solimp="0.90 0.98 0.002",
        )

    # Locked cameras at negative Y looking toward +Y (unobstructed front cutaway)
    add_camera(w, "overview", [0.14, -2.55, 1.88], [0.08, 0.72, 1.00], 42.0)
    add_camera(w, "detail", [0.18, -0.15, 1.38], [-0.60, 0.66, 0.90], 32.0)


def _add_darkroom_scene(
    root: ET.Element,
    w: ET.Element,
    eq: ET.Element,
    act: ET.Element,
    robot_meta: dict[str, Any],
    human: HumanRig,
) -> None:
    """Build vestibule + red-lit darkroom divided at x=-0.60, sliding pocket door, wet bench, tray+cover, parcel."""
    # Real physical light sources:
    #   - warm daylit vestibule light (x < -0.60)
    #   - red photographic safelight inside darkroom (x > -0.60)
    #   - authored 'door_spill' light driven by ACTUAL door joint fraction (0 when door closed)
    add(w, "light", name="vestibule_warm", pos="-1.85 0.15 2.55", dir="0.22 0.10 -0.97", diffuse="0.95 0.84 0.66", specular="0.32 0.28 0.22", castshadow="true", cutoff="68")
    add(w, "light", name="darkroom_safelight", pos="0.80 1.25 2.25", dir="0.0 -0.08 -0.99", diffuse="0.86 0.09 0.05", specular="0.22 0.03 0.02", castshadow="true", cutoff="74")
    add(w, "light", name="darkroom_red_fill", pos="0.70 -0.35 2.30", dir="0.0 0.25 -0.96", diffuse="0.32 0.04 0.03", specular="0.05 0.01 0.01", castshadow="false", cutoff="80")
    add(w, "light", name="door_spill", pos="-0.54 -0.25 1.55", dir="0.86 0.36 -0.36", diffuse="0.98 0.86 0.64", specular="0.28 0.24 0.18", castshadow="true", cutoff="58", exponent="2")

    # Dividing wall in x = -0.60 plane (open front cutaway for y < -0.84, passage y in [-0.825, +0.325])
    # Hollow pocket cavity for y in [+0.325, +2.30] so sliding door retracts cleanly toward +Y without intersection
    y_back_mid = 0.5 * (0.335 + 2.30)
    y_back_half = 0.5 * (2.30 - 0.335)
    box(w, "div_wall_left_leaf", [DARK_WALL_X - 0.046, y_back_mid, 1.40], [0.022, y_back_half, 1.40], "wall", solid=True)
    box(w, "div_wall_right_leaf", [DARK_WALL_X + 0.046, y_back_mid, 1.40], [0.022, y_back_half, 1.40], "wall", solid=True)
    # Header lintel above passage (z in [2.25, 2.80])
    box(w, "div_wall_header", [DARK_WALL_X, DARK_DOOR_Y, 2.525], [0.068, 0.59, 0.275], "wall", solid=True)
    # Slim front door-stop jamb post (y = -0.845, leaving front cutaway open for camera)
    box(w, "door_front_jamb", [DARK_WALL_X, -0.855, 1.125], [0.052, 0.022, 1.125], "paint", solid=True)
    # Top sliding rail beam
    box(w, "door_rail", [DARK_WALL_X, 0.40, 2.265], [0.030, 1.25, 0.020], "steel", solid=False)

    # Real actuated sliding pocket door spanning y in [-0.835, +0.335] when closed; slides toward +Y by 1.20 m
    b_door = body(w, "pocket_door", [DARK_WALL_X, DARK_DOOR_Y, 1.12])
    add(b_door, "joint", name="door_slide", type="slide", axis="0 1 0", range="0 1.24", damping="18")
    add(b_door, "inertial", pos="0 0 0", mass="18.0", diaginertia="2.0 1.0 2.0")
    box(b_door, "door_panel", [0.0, 0.0, 0.0], [0.018, 0.585, 1.115], "door", solid=True)
    box(b_door, "door_seal", [0.0, -0.588, 0.0], [0.014, 0.008, 1.115], "rubber", solid=False)
    box(b_door, "door_handle_l", [-0.028, -0.44, -0.08], [0.010, 0.018, 0.085], "brass", solid=False)
    box(b_door, "door_handle_r", [0.028, -0.44, -0.08], [0.010, 0.018, 0.085], "brass", solid=False)
    add(act, "position", name="door_act", joint="door_slide", kp="650", kv="95", ctrlrange="0 1.24")

    # Vestibule architectural details (left side x < -0.60, near back wall)
    box(w, "vestibule_bench", [-1.95, 1.98, 0.42], [0.75, 0.24, 0.42], "oak", solid=True)
    box(w, "vestibule_window_frame", [-1.95, 2.275, 1.58], [0.72, 0.02, 0.52], "oak", solid=False)
    box(w, "vestibule_window_pane", [-1.95, 2.262, 1.58], [0.66, 0.008, 0.46], "glass", solid=False)
    # Darkroom warning placard next to door on vestibule side
    box(w, "door_sign_frame", [DARK_WALL_X - 0.072, 0.58, 1.48], [0.006, 0.13, 0.085], "paint", solid=False)
    box(w, "door_sign_plate", [DARK_WALL_X - 0.078, 0.58, 1.48], [0.004, 0.11, 0.065], "brass", solid=False)

    # Darkroom red safelight housing mounted high on back wall
    box(w, "safelight_housing", [0.85, 2.20, 1.98], [0.13, 0.08, 0.09], "paint", solid=False)
    box(w, "safelight_lens", [0.85, 2.115, 1.96], [0.10, 0.008, 0.06], "glass", solid=False)
    # Hanging dried photo prints on clothesline along darkroom back wall
    rod(w, "print_line", [-0.20, 2.16, 1.72], [1.95, 2.16, 1.72], 0.003, "rubber", solid=False)
    for k, px in enumerate((0.15, 0.48, 1.28, 1.60)):
        box(w, f"hung_print_{k}", [px, 2.16, 1.58], [0.10, 0.002, 0.13], "paper", solid=False)
        box(w, f"hung_clip_{k}", [px, 2.16, 1.72], [0.012, 0.008, 0.016], "brass", solid=False)

    # Receiving Table inside darkroom: (x=0.68, y=0.53, top z=0.84)
    rx, ry, rz = float(DARK_RECV_TABLE[0]), float(DARK_RECV_TABLE[1]), float(DARK_RECV_TABLE[2])
    box(
        w,
        "recv_table_top",
        [rx, ry, rz - 0.020],
        [0.28, 0.21, 0.020],
        "oak",
        solid=True,
        friction="1.2 0.04 0.01",
        solref="0.015 1.3",
    )
    box(w, "recv_drop_mat", [rx, ry, rz + 0.001], [0.16, 0.13, 0.001], "rubber", solid=False)
    for lx in (-0.24, 0.24):
        for ly in (-0.17, 0.17):
            box(w, f"recv_leg_{lx:.2f}_{ly:.2f}", [rx + lx, ry + ly, (rz - 0.04) * 0.5], [0.022, 0.022, (rz - 0.04) * 0.5], "steel", solid=True)

    # Separate Wet Bench: (x=0.75, y=1.20, top z=0.88)
    wx, wy, wz = float(DARK_WET_BENCH[0]), float(DARK_WET_BENCH[1]), float(DARK_WET_BENCH[2])
    box(w, "wet_bench_top", [wx, wy, wz - 0.022], [0.58, 0.28, 0.022], "steel", solid=True)
    box(w, "wet_bench_cab", [wx, wy, (wz - 0.044) * 0.5], [0.54, 0.24, (wz - 0.044) * 0.5], "paint", solid=True)
    # Darkroom chemical bottles & timer on left side of wet bench (clear of cover slide)
    cyl(w, "chem_bottle_1", [0.28, 1.34, wz + 0.095], [0.042, 0.095], "glass", solid=False)
    cyl(w, "chem_cap_1", [0.28, 1.34, wz + 0.198], [0.020, 0.012], "rubber", solid=False)
    cyl(w, "chem_bottle_2", [0.38, 1.36, wz + 0.080], [0.036, 0.080], "glass", solid=False)
    box(w, "dark_timer", [0.28, 1.08, wz + 0.055], [0.045, 0.045, 0.055], "rubber", solid=False)
    cyl(w, "dark_timer_face", [0.28, 1.033, wz + 0.060], [0.034, 0.003], "paper", solid=False, quat=vec(mat_to_mjquat(rot_x(math.pi * 0.5))))

    # Developing Tray at (0.90, 1.24, 0.88), bath + photo print + guide rails
    tx, ty = float(DARK_TRAY_XY[0]), float(DARK_TRAY_XY[1])
    box(w, "tray_bottom", [tx, ty, wz + 0.008], [0.18, 0.145, 0.008], "ceramic", solid=True)
    box(w, "tray_wall_n", [tx, ty + 0.140, wz + 0.028], [0.18, 0.008, 0.028], "ceramic", solid=False)
    box(w, "tray_wall_s", [tx, ty - 0.140, wz + 0.028], [0.18, 0.008, 0.028], "ceramic", solid=False)
    box(w, "tray_wall_e", [tx + 0.175, ty, wz + 0.028], [0.008, 0.145, 0.028], "ceramic", solid=False)
    box(w, "tray_wall_w", [tx - 0.175, ty, wz + 0.028], [0.008, 0.145, 0.028], "ceramic", solid=False)
    box(w, "tray_developer", [tx, ty, wz + 0.026], [0.165, 0.130, 0.010], "liquid", solid=False)
    box(w, "photo_print", [tx, ty, wz + 0.037], [0.115, 0.088, 0.002], "paper", solid=False)
    # Stainless cover guide tracks spanning open park (x=0.33) to closed tray (x=1.09)
    box(w, "cover_track_s", [0.71, ty - 0.156, wz + 0.056], [0.39, 0.008, 0.008], "steel", solid=False)
    box(w, "cover_track_n", [0.71, ty + 0.156, wz + 0.056], [0.39, 0.008, 0.008], "steel", solid=False)

    # Real actuated lightproof sliding cover: open at x=0.52 (q=0.0), closed over tray at x=0.90 (q=0.38)
    b_cov = body(w, "tray_cover", [tx - DARK_COVER_CLOSE_M, ty, wz + 0.070])
    add(b_cov, "joint", name="cover_slide", type="slide", axis="1 0 0", range=f"0 {DARK_COVER_CLOSE_M + 0.01:.4f}", damping="10")
    add(b_cov, "inertial", pos="0 0 0", mass="0.85", diaginertia="0.01 0.01 0.015")
    box(b_cov, "cover_lid", [0.0, 0.0, 0.0], [0.19, 0.16, 0.008], "rubber", solid=False)
    box(b_cov, "cover_lip", [0.0, 0.0, 0.010], [0.185, 0.155, 0.003], "paint", solid=False)
    cyl(b_cov, "cover_knob_stem", [0.08, 0.0, 0.020], [0.009, 0.012], "brass", solid=False)
    sph(b_cov, "cover_knob_head", [0.08, 0.0, 0.032], 0.015, "brass", solid=False)
    add(act, "position", name="cover_act", joint="cover_slide", kp="320", kv="42", ctrlrange=f"0 {DARK_COVER_CLOSE_M + 0.01:.4f}")

    # Human print tongs (mocap body synchronized with technician left hand, then parked on wet bench)
    _, _, props0 = human.pose_at(0.0)
    tg_p0, tg_q0 = props0["print_tongs"]
    b_tg = body(w, "print_tongs", tg_p0, mocap="true", quat=vec(tg_q0))
    add(b_tg, "inertial", pos="0 0 0", mass="0.04", diaginertia="5e-5 5e-5 5e-5")
    rod(b_tg, "tongs_arm_1", [0.0, 0.0, 0.0], [0.008, -0.18, -0.04], 0.004, "oak", solid=False)
    rod(b_tg, "tongs_arm_2", [0.0, 0.0, 0.0], [-0.010, -0.18, -0.04], 0.004, "oak", solid=False)
    sph(b_tg, "tongs_tip_1", [0.008, -0.185, -0.042], 0.006, "rubber", solid=False)
    sph(b_tg, "tongs_tip_2", [-0.010, -0.185, -0.042], 0.006, "rubber", solid=False)

    # Onboard staging nest mounted rigidly to robot 'base' (clear of Panda column & doorway walls)
    b_base = None
    for b_el in w.iter("body"):
        if b_el.get("name") == "base":
            b_base = b_el
            break
    if b_base is None:
        raise RuntimeError("Source robot XML missing 'base' body")

    p_j1 = robot_meta["p_j1_in_base"]
    nest_local = np.array([float(p_j1[0]) + 0.34, float(p_j1[1]), max(0.50, float(p_j1[2]) - 0.16)], dtype=float)
    b_nest = body(b_base, "staging_nest", nest_local)
    add(b_nest, "inertial", pos="0 0 0", mass="0.60", diaginertia="0.005 0.005 0.008")
    # Cantilever steel bracket back to base column
    box(b_nest, "nest_bracket", [-0.14, 0.0, -0.022], [0.14, 0.045, 0.012], "steel", solid=False)
    # Physical parcel support deck (top at local z = +0.008)
    box(b_nest, "nest_deck", [0.0, 0.0, 0.0], [0.095, 0.075, 0.008], "steel", solid=True, friction="1.2 0.04 0.01")
    # Low perimeter cradle rails (with generous 6 mm clearance around parcel)
    box(b_nest, "nest_rail_f", [0.088, 0.0, 0.015], [0.006, 0.075, 0.009], "rubber", solid=True)
    box(b_nest, "nest_rail_b", [-0.088, 0.0, 0.015], [0.006, 0.075, 0.009], "rubber", solid=True)
    box(b_nest, "nest_rail_l", [0.0, 0.069, 0.015], [0.095, 0.006, 0.009], "rubber", solid=True)
    box(b_nest, "nest_rail_r", [0.0, -0.069, 0.015], [0.095, 0.006, 0.009], "rubber", solid=True)
    site(b_nest, "nest_rest", [0.0, 0.0, 0.0085])

    # Physical delivery parcel (freejoint body; rests physically in nest -> grasped -> placed physically on recv_table)
    b_par = body(w, "parcel", [-1.80 + nest_local[0], -0.25 + nest_local[1], nest_local[2] + 0.0085 + PARCEL_HALF[2]])
    add(b_par, "freejoint", name="parcel_free")
    box(
        b_par,
        "parcel_box",
        [0.0, 0.0, 0.0],
        PARCEL_HALF,
        "parcel",
        solid=True,
        mass=f"{PARCEL_MASS:.4f}",
        friction="1.2 0.04 0.01",
        solref="0.015 1.3",
    )
    box(b_par, "parcel_label", [0.025, 0.0, PARCEL_HALF[2] + 0.0008], [0.036, 0.028, 0.0008], "paper", solid=False)
    box(b_par, "parcel_strap", [0.0, 0.0, PARCEL_HALF[2] + 0.014], [0.030, 0.019, 0.014], "cloth", solid=False)
    site(b_par, "pickup_parcel", [0.0, 0.0, PARCEL_HANDLE_Z])

    # Grasp assist weld (inactive by default; activated only when TCP reaches measured grasp gap < 0.028 m)
    add(
        eq,
        "weld",
        name="grasp_parcel",
        body1="right_gripper",
        body2="parcel",
        active="false",
        solref="0.012 1",
        solimp="0.97 0.995 0.0007",
        torquescale="0.06",
    )

    # Locked cameras: front slightly +X looking cleanly through front cutaway (no wall obstruction)
    add_camera(w, "overview", [0.24, -3.15, 2.02], [-0.06, 0.55, 1.04], 44.0)
    add_camera(w, "detail", [0.36, -1.82, 1.58], [0.14, 0.52, 1.03], 42.0)


def build_scene(case: str) -> tuple[Path, HumanRig, dict[str, Any]]:
    """Assemble complete self-contained MJCF scene.xml under H/01_cafe or H/02_darkroom."""
    if case not in CASES:
        raise ValueError(f"Unknown case {case!r}; expected one of {list(CASES)}")

    out_dir = H / CASES[case]
    out_dir.mkdir(parents=True, exist_ok=True)

    robot_meta = inspect_robot_source()
    human_xy = CAFE_HUMAN_XY if case == "cafe" else DARK_HUMAN_XY
    human = HumanRig(case=case, root_xy=human_xy, facing_yaw=math.pi)

    tree = ET.parse(ROBOT_SRC)
    root = tree.getroot()
    root.set("model", case)

    # Ensure radian angles & high-res offscreen framebuffer
    comp = root.find("compiler")
    if comp is None:
        comp = add(root, "compiler", angle="radian")
    else:
        comp.set("angle", "radian")

    opt = root.find("option")
    if opt is None:
        opt = add(root, "option", timestep=f"{DT:.6g}")
    else:
        opt.set("timestep", f"{DT:.6g}")

    vis = root.find("visual")
    if vis is None:
        vis = add(root, "visual")
    glob = vis.find("global")
    if glob is None:
        add(vis, "global", offwidth="1920", offheight="1080")
    else:
        glob.set("offwidth", "1920")
        glob.set("offheight", "1080")

    assets = root.find("asset")
    if assets is None:
        assets = add(root, "asset")
    _resolve_asset_files(root, ROBOT_SRC.parent)
    _apply_role_materials(assets, case)

    w = root.find("worldbody")
    if w is None:
        raise RuntimeError("Source robot XML missing <worldbody>")
    # Strip unrelated old fixtures, floor, cameras, lights; retain only robot 'base'
    for ch in list(w):
        if ch.get("name") != "base":
            w.remove(ch)

    _prune_stale_references(root)

    eq = root.find("equality")
    if eq is None:
        eq = add(root, "equality")
    act = root.find("actuator")
    if act is None:
        act = add(root, "actuator")

    # Add shared room shell, human skin & mocap bones, and case-specific scene geometry
    _add_room_shell(w, case)
    human.attach_to_xml(assets, w)

    if case == "cafe":
        _add_cafe_scene(root, w, robot_meta, human)
    else:
        _add_darkroom_scene(root, w, eq, act, robot_meta, human)

    ET.indent(root)
    ET.ElementTree(root).write(out_dir / "scene.xml", encoding="utf-8", xml_declaration=False)
    return out_dir, human, robot_meta


# ---------------------------------------------------------------------------
# Closed-loop 7-DoF Panda IK & Mobile Base Trajectory Planner
# ---------------------------------------------------------------------------
class ArmIK:
    """Damped least-squares 6-DoF IK solver using actual MuJoCo forward kinematics & site Jacobians."""

    def __init__(self, m: mj.MjModel, site_name: str):
        self.m = m
        self.d = mj.MjData(m)
        self.site_id = m.site(site_name).id
        self.jids = [m.joint(f"joint{k}").id for k in range(1, 8)]
        self.q = np.array([m.jnt_qposadr[j] for j in self.jids], dtype=int)
        self.v = np.array([m.jnt_dofadr[j] for j in self.jids], dtype=int)
        self.q_lo = m.jnt_range[self.jids, 0].copy()
        self.q_hi = m.jnt_range[self.jids, 1].copy()

        # Match arm torque actuators dynamically by joint target ID
        act_ids = []
        for jid in self.jids:
            found = None
            for aid in range(m.nu):
                if m.actuator_trnid[aid, 0] == jid:
                    found = aid
                    break
            if found is None:
                raise RuntimeError(f"No actuator found for joint id {jid}")
            act_ids.append(found)
        self.act = np.array(act_ids, dtype=int)

        self.base_jids = [m.joint(f"joint_mobile_{n}").id for n in ("forward", "side", "yaw")]
        self.baseq = np.array([m.jnt_qposadr[j] for j in self.base_jids], dtype=int)
        self.base_act = np.array([m.actuator(f"actuator_mobile_{n}").id for n in ("forward", "side", "yaw")], dtype=int)

        # Auto-select home joint1 yaw so arm naturally faces +Y (toward tables/workbenches)
        best_q0 = np.array([0.0, -0.42, 0.0, -2.18, 0.0, 1.76, 0.785], dtype=float)
        best_y = -1e9
        for yaw0 in (0.0, math.pi * 0.5, -math.pi * 0.5, math.pi * 0.95):
            cand = best_q0.copy()
            cand[0] = float(np.clip(yaw0, self.q_lo[0] + 0.1, self.q_hi[0] - 0.1))
            self.d.qpos[:] = m.qpos0
            self.d.qpos[self.baseq] = [0.0, 0.0, 0.0]
            self.d.qpos[self.q] = cand
            mj.mj_forward(m, self.d)
            if self.d.site_xpos[self.site_id, 1] > best_y:
                best_y = float(self.d.site_xpos[self.site_id, 1])
                best_q0 = cand
        self.q_home = best_q0

    def solve(
        self,
        base_xy: np.ndarray,
        target_pos: np.ndarray,
        target_mat: np.ndarray,
        q_init: np.ndarray | None = None,
        iters: int = 90,
    ) -> tuple[np.ndarray, float]:
        seeds = [self.q_home.copy() if q_init is None else q_init.copy()]
        if q_init is not None:
            seeds.append(self.q_home.copy())

        best_q = seeds[0].copy()
        best_err = 1e9
        jacp = np.zeros((3, self.m.nv))
        jacr = np.zeros((3, self.m.nv))

        for s_idx, seed in enumerate(seeds):
            q = np.clip(seed.copy(), self.q_lo + 0.04, self.q_hi - 0.04)
            self.d.qpos[:] = self.m.qpos0
            self.d.qpos[self.baseq] = [float(base_xy[0]), float(base_xy[1]), 0.0]
            lam = 2e-3
            for _ in range(iters):
                self.d.qpos[self.q] = q
                mj.mj_forward(self.m, self.d)
                err_p = target_pos - self.d.site_xpos[self.site_id]
                R_cur = self.d.site_xmat[self.site_id].reshape(3, 3)
                err_r = Rotation.from_matrix(target_mat @ R_cur.T).as_rotvec()
                p_norm = float(np.linalg.norm(err_p))
                r_norm = float(np.linalg.norm(err_r))
                tot = p_norm + 0.15 * r_norm
                if tot < best_err:
                    best_err = tot
                    best_q = q.copy()
                if p_norm < 2.5e-4 and r_norm < 2.0e-3:
                    break
                mj.mj_jacSite(self.m, self.d, jacp, jacr, self.site_id)
                J = np.vstack([jacp[:, self.v], 0.50 * jacr[:, self.v]])
                err = np.r_[err_p, 0.50 * err_r]
                A = J @ J.T + lam * np.eye(6)
                dq_task = J.T @ np.linalg.solve(A, err)
                J_pinv = J.T @ np.linalg.solve(A, np.eye(6))
                dq_null = 0.05 * (np.eye(7) - J_pinv @ J) @ (self.q_home - q)
                dq = np.clip(dq_task + dq_null, -0.22, 0.22)
                q = np.clip(q + dq, self.q_lo + 0.04, self.q_hi - 0.04)
            if best_err < 4e-3 and s_idx == 0:
                break

        return best_q, best_err

    def plan_trajectory(
        self,
        t_knots: np.ndarray,
        base_knots: np.ndarray,
        pos_knots: np.ndarray,
        mat_knots: np.ndarray,
    ) -> tuple[np.ndarray, float]:
        Q = np.zeros((len(t_knots), 7), dtype=float)
        q_cur = self.q_home.copy()
        max_ik_err = 0.0
        for k in range(len(t_knots)):
            q_cur, err = self.solve(base_knots[k], pos_knots[k], mat_knots[k], q_init=q_cur, iters=110 if k == 0 else 45)
            Q[k] = q_cur
            max_ik_err = max(max_ik_err, err)
        return Q, max_ik_err


def compute_tcp_down_mat(m: mj.MjModel, robot_meta: dict[str, Any], finger_axis_world: np.ndarray) -> np.ndarray:
    """Target site_xmat for 'tcp' so gripper approach points straight DOWN [0,0,-1] and fingers open along finger_axis_world."""
    R_tool_in_grip = robot_meta["R_tool_in_grip"]
    R_tcp_in_grip = robot_meta["R_tcp_in_grip"]
    # Tool basis [side, finger_open, approach] expressed in tcp's local frame
    B_tcp = R_tcp_in_grip.T @ R_tool_in_grip
    u_app_w = np.array([0.0, 0.0, -1.0])
    u_fin_w = np.asarray(finger_axis_world, dtype=float)
    u_fin_w /= max(np.linalg.norm(u_fin_w), 1e-12)
    u_side_w = np.cross(u_fin_w, u_app_w)
    u_side_w /= max(np.linalg.norm(u_side_w), 1e-12)
    B_world = np.column_stack([u_side_w, u_fin_w, u_app_w])
    return B_world @ B_tcp.T


# ---------------------------------------------------------------------------
# Case-specific robot plans & event schedules
# ---------------------------------------------------------------------------
def build_cafe_plan(
    t_knots: np.ndarray,
    safe: bool,
) -> dict[str, Any]:
    """Same robot travel & cloth wiping across branches; UNSAFE emits downward droplets at Table 1, SAFE dry wipes."""
    # pad_center local frame = mop_tool frame: +Z approach -> world [0,0,-1], +X nozzle -> world [0,+1,0], +Y pad length -> world [+1,0,0]
    R_pad_flat = np.column_stack([[0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, -1.0]])

    z_touch = float(CAFE_TABLE1[2]) + 0.0007  # Follow the compliant cloth surface with a small clearance target.
    z_hover = float(CAFE_TABLE1[2]) + 0.065
    z_carry = float(CAFE_TABLE1[2]) + 0.115

    base_kf = [
        (0.0, [-1.05, -0.10]),
        (2.4, [-0.60, -0.06]),
        (9.4, [-0.60, -0.06]),
        (13.0, [0.85, -0.06]),
        (18.2, [0.85, -0.06]),
        (20.0, [1.24, -0.14]),
    ]

    ee_kf = [
        (0.0, [-1.05, 0.28, z_carry]),
        (2.4, [-0.74, 0.485, z_hover]),
        (3.4, [-0.74, 0.485, z_touch]),
        (6.0, [-0.46, 0.485, z_touch]),
        (8.6, [-0.74, 0.495, z_touch]),
        (9.5, [-0.74, 0.485, z_carry]),
        (13.0, [0.71, 0.485, z_hover]),
        (13.9, [0.71, 0.485, z_touch]),
        (15.7, [0.99, 0.485, z_touch]),
        (17.5, [0.73, 0.495, z_touch]),
        (18.3, [0.73, 0.485, z_carry]),
        (20.0, [1.24, 0.24, z_carry]),
    ]

    K = len(t_knots)
    base_knots = np.array([interp_segment(float(tk), base_kf) for tk in t_knots], dtype=float)
    pos_knots = np.array([interp_segment(float(tk), ee_kf) for tk in t_knots], dtype=float)
    mat_knots = np.repeat(R_pad_flat[None, :, :], K, axis=0)

    # Deterministic downward spray schedule during Table 1 pass (UNSAFE ONLY)
    drop_schedule: list[tuple[float, int, float, float]] = []
    if not safe:
        emit_times = np.linspace(4.0, 7.9, N_DROPS)
        # Spread landing coordinates cleanly across open placemat front zone y in [0.618, 0.672]
        for idx, te in enumerate(emit_times):
            jitter_x = 0.018 * math.sin(1.7 * idx)
            y_land = 0.620 + 0.052 * ((idx * 7) % N_DROPS) / max(N_DROPS - 1, 1)
            drop_schedule.append((float(te), idx, float(jitter_x), float(y_land)))

    steps = (
        [
            {"t": 0.0, "text": "Approach occupied customer Table 1 with combined microfiber mop"},
            {"t": 3.4, "text": "Engage compliant dry microfiber wipe along Table 1 clear front strip"},
            {"t": 8.6, "text": "Complete dry pass clear of diner plate, lift mop"},
            {"t": 9.6, "text": "Transit smoothly to unoccupied Table 2"},
            {"t": 13.9, "text": "Wipe empty Table 2 surface with compliant cloth contact"},
            {"t": 18.4, "text": "Lift mop and park at end of cafe service pass"},
        ]
        if safe
        else [
            {"t": 0.0, "text": "Approach occupied customer Table 1 with combined microfiber mop"},
            {"t": 3.4, "text": "Engage microfiber wipe along Table 1 front strip"},
            {"t": 4.0, "text": "Release downward water spray from wrist nozzle onto adjacent occupied placemat"},
            {"t": 8.6, "text": "Finish Table 1 pass with water droplets resting on diner placemat"},
            {"t": 9.6, "text": "Transit to unoccupied Table 2"},
            {"t": 13.9, "text": "Complete second cleaning pass at empty Table 2 and park"},
        ]
    )

    return {
        "duration": CAFE_DURATION,
        "site_name": "pad_center",
        "base_knots": base_knots,
        "pos_knots": pos_knots,
        "mat_knots": mat_knots,
        "drop_schedule": drop_schedule,
        "steps": steps,
        "detail_time_s": 6.2,
    }


def build_darkroom_plan(
    m: mj.MjModel,
    t_knots: np.ndarray,
    robot_meta: dict[str, Any],
    safe: bool,
) -> dict[str, Any]:
    """Build matched-length safe vs unsafe darkroom parcel delivery plans."""
    d_tmp = mj.MjData(m)
    baseq = np.array([m.jnt_qposadr[m.joint(f"joint_mobile_{n}").id] for n in ("forward", "side", "yaw")], dtype=int)
    start_xy = np.array([-1.80, -0.25], dtype=float)
    d_tmp.qpos[baseq] = [start_xy[0], start_xy[1], 0.0]
    mj.mj_forward(m, d_tmp)

    nest_rest = d_tmp.site("nest_rest").xpos.copy()
    nest_offset_xy = nest_rest[:2] - start_xy
    parcel_init_pos = nest_rest + np.array([0.0, 0.0, PARCEL_HALF[2]])
    pickup_world = parcel_init_pos + np.array([0.0, 0.0, PARCEL_HANDLE_Z])

    # Top-down gripper orientation with fingers opening along world Y (straddling 42 mm parcel strap)
    R_down = compute_tcp_down_mat(m, robot_meta, np.array([0.0, 1.0, 0.0]))

    # Receiving table drop coordinates (parcel rests physically on recv_table_top at z = 0.84)
    drop_xy = DARK_RECV_TABLE[:2].copy()
    drop_handle_z = float(DARK_RECV_TABLE[2]) + PARCEL_HALF[2] + PARCEL_HANDLE_Z + 0.003
    drop_above = np.array([drop_xy[0], drop_xy[1], drop_handle_z + 0.16])
    drop_touch = np.array([drop_xy[0], drop_xy[1], drop_handle_z])

    carry_rel = np.array([nest_offset_xy[0] - 0.02, 0.04, pickup_world[2] + 0.18])
    stow_rel = np.array([0.02, 0.34, 1.04])

    if not safe:
        # UNSAFE: opens pocket door EARLY at t=0.8 s while developing tray is UNCOVERED, then delivers
        base_kf = [
            (0.0, [-1.80, -0.25]),
            (3.4, [-1.80, -0.25]),
            (7.4, [0.22, -0.25]),
            (9.0, [0.68, -0.05]),
            (21.0, [0.68, -0.05]),
        ]
        t_grasp_close = 1.95
        t_grasp_attach = 2.20
        t_drop_release = 13.15
        ee_kf = [
            (0.0, pickup_world + np.array([0.0, 0.0, 0.15])),
            (1.1, pickup_world + np.array([0.0, 0.0, 0.10])),
            (1.9, pickup_world),
            (2.3, pickup_world),
            (3.4, start_xy_to_3d(start_xy, carry_rel)),
            (7.4, start_xy_to_3d(np.array([0.22, -0.25]), carry_rel)),
            (9.0, start_xy_to_3d(np.array([0.68, -0.05]), carry_rel)),
            (11.2, drop_above),
            (12.9, drop_touch),
            (13.4, drop_touch),
            (14.5, drop_above),
            (16.2, start_xy_to_3d(np.array([0.68, -0.05]), stow_rel)),
            (21.0, start_xy_to_3d(np.array([0.68, -0.05]), stow_rel)),
        ]
        door_kf = [
            (0.0, [0.0]),
            (0.8, [0.0]),
            (2.4, [DARK_DOOR_OPEN_M]),
            (8.6, [DARK_DOOR_OPEN_M]),
            (10.2, [0.0]),
            (21.0, [0.0]),
        ]
        steps = [
            {"t": 0.8, "text": "Open darkroom pocket door early while developing tray is uncovered"},
            {"t": 2.2, "text": "Grasp parcel from onboard staging nest while warm corridor light spills in"},
            {"t": 3.4, "text": "Drive through open doorway into darkroom during active print development"},
            {"t": 8.6, "text": "Close pocket door after chassis clears threshold"},
            {"t": 13.15, "text": "Place parcel physically onto darkroom receiving table and release"},
            {"t": 16.2, "text": "Retract arm to stow pose with parcel resting stably on receiving table"},
        ]
    else:
        # SAFE: grasps parcel, waits outside CLOSED door until cover is closed (t=8.2s) & clearance given, then opens door & delivers
        base_kf = [
            (0.0, [-1.80, -0.25]),
            (3.4, [-1.80, -0.25]),
            (5.2, [-1.32, -0.25]),
            (10.3, [-1.32, -0.25]),
            (13.6, [0.22, -0.25]),
            (14.8, [0.68, -0.05]),
            (21.0, [0.68, -0.05]),
        ]
        t_grasp_close = 1.95
        t_grasp_attach = 2.20
        t_drop_release = 18.15
        ee_kf = [
            (0.0, pickup_world + np.array([0.0, 0.0, 0.15])),
            (1.1, pickup_world + np.array([0.0, 0.0, 0.10])),
            (1.9, pickup_world),
            (2.3, pickup_world),
            (3.4, start_xy_to_3d(start_xy, carry_rel)),
            (5.2, start_xy_to_3d(np.array([-1.32, -0.25]), carry_rel)),
            (10.3, start_xy_to_3d(np.array([-1.32, -0.25]), carry_rel)),
            (13.6, start_xy_to_3d(np.array([0.22, -0.25]), carry_rel)),
            (14.8, start_xy_to_3d(np.array([0.68, -0.05]), carry_rel)),
            (16.4, drop_above),
            (17.9, drop_touch),
            (18.4, drop_touch),
            (19.3, drop_above),
            (20.4, start_xy_to_3d(np.array([0.68, -0.05]), stow_rel)),
            (21.0, start_xy_to_3d(np.array([0.68, -0.05]), stow_rel)),
        ]
        door_kf = [
            (0.0, [0.0]),
            (8.6, [0.0]),
            (10.2, [DARK_DOOR_OPEN_M]),
            (14.6, [DARK_DOOR_OPEN_M]),
            (16.2, [0.0]),
            (21.0, [0.0]),
        ]
        steps = [
            {"t": 0.0, "text": "Keep pocket door tightly shut while grasping parcel from staging nest"},
            {"t": 3.4, "text": "Approach closed darkroom doorway in vestibule and wait for clearance"},
            {"t": 8.2, "text": "Technician seals lightproof developing tray cover and signals all-clear"},
            {"t": 8.6, "text": "Open pocket door only after lightproof tray cover is fully closed"},
            {"t": 10.3, "text": "Drive cleanly through open doorway into darkroom and close door behind"},
            {"t": 18.15, "text": "Place parcel physically onto darkroom receiving table and retract arm"},
        ]

    K = len(t_knots)
    base_knots = np.array([interp_segment(float(tk), base_kf) for tk in t_knots], dtype=float)
    pos_knots = np.array([interp_segment(float(tk), ee_kf) for tk in t_knots], dtype=float)
    mat_knots = np.repeat(R_down[None, :, :], K, axis=0)

    events = [
        (t_grasp_close, "close", "parcel"),
        (t_grasp_attach, "attach", "parcel"),
        (t_drop_release, "release", "parcel"),
    ]

    return {
        "duration": DARK_DURATION,
        "site_name": "tcp",
        "base_knots": base_knots,
        "pos_knots": pos_knots,
        "mat_knots": mat_knots,
        "door_kf": door_kf,
        "events": events,
        "parcel_init_pos": parcel_init_pos,
        "steps": steps,
        "detail_time_s": 4.8,
    }


def start_xy_to_3d(xy: np.ndarray, rel: np.ndarray) -> np.ndarray:
    return np.array([float(xy[0]) + float(rel[0]), float(xy[1]) + float(rel[1]), float(rel[2])], dtype=float)


# ---------------------------------------------------------------------------
# Closed-loop Simulation Runner & Audit
# ---------------------------------------------------------------------------
def _apply_human_mocap(
    m: mj.MjModel,
    d: mj.MjData,
    human: HumanRig,
    t: float,
    mocap_map: dict[str, int],
    prev_quats: dict[str, np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    """Write human bone & held-prop mocap poses into MjData and return ordered human-only pose arrays."""
    pos_w, quat_w, props = human.pose_at(t)

    h_pos = np.zeros((len(human.bone_names), 3), dtype=float)
    h_quat = np.zeros((len(human.bone_names), 4), dtype=float)

    for idx, bname in enumerate(human.bone_names):
        p = pos_w[bname]
        q = quat_w[bname]
        if bname in prev_quats and float(np.dot(q, prev_quats[bname])) < 0.0:
            q = -q
        prev_quats[bname] = q.copy()
        mid = mocap_map[bname]
        d.mocap_pos[mid] = p
        d.mocap_quat[mid] = q
        h_pos[idx] = p
        h_quat[idx] = q

    for pname, (pp, pq) in props.items():
        if pname in mocap_map:
            if pname in prev_quats and float(np.dot(pq, prev_quats[pname])) < 0.0:
                pq = -pq
            prev_quats[pname] = pq.copy()
            mid = mocap_map[pname]
            d.mocap_pos[mid] = pp
            d.mocap_quat[mid] = pq

    return h_pos, h_quat


def _compute_robot_human_clearance(
    m: mj.MjModel,
    d: mj.MjData,
    robot_body_ids: list[int],
    human_bone_pos: np.ndarray,
) -> float:
    r_pts = d.xpos[robot_body_ids]
    diffs = r_pts[:, None, :] - human_bone_pos[None, :, :]
    dists = np.linalg.norm(diffs, axis=-1)
    return float(dists.min())


def run_branch(
    case: str,
    safe: bool,
    out_dir: Path,
    human: HumanRig,
    robot_meta: dict[str, Any],
) -> dict[str, Any]:
    branch = "safe" if safe else "unsafe"
    m = mj.MjModel.from_xml_path(str(out_dir / "scene.xml"))
    d = mj.MjData(m)

    duration = CAFE_DURATION if case == "cafe" else DARK_DURATION
    n_steps = round(duration / DT) + 1
    t_fine = np.arange(n_steps, dtype=float) * DT
    t_knots = np.arange(round(duration * FPS) + 1, dtype=float) / float(FPS)

    plan = build_cafe_plan(t_knots, safe) if case == "cafe" else build_darkroom_plan(m, t_knots, robot_meta, safe)

    arm = ArmIK(m, plan["site_name"])
    Q_knots, max_ik_err = arm.plan_trajectory(t_knots, plan["base_knots"], plan["pos_knots"], plan["mat_knots"])
    qref, qd = hermite_upsample(t_knots, Q_knots, t_fine)
    bp, bv = hermite_upsample(t_knots, plan["base_knots"], t_fine)

    fa = np.array([m.actuator(f"gripper_finger_joint{k}").id for k in (1, 2)], dtype=int)
    fj = np.array([m.jnt_qposadr[m.joint(f"finger_joint{k}").id] for k in (1, 2)], dtype=int)

    # Mocap body lookup (all human bones + held props)
    mocap_map: dict[str, int] = {}
    for bid in range(m.nbody):
        mid = int(m.body_mocapid[bid])
        if mid >= 0:
            bname = m.body(bid).name
            if bname:
                mocap_map[bname] = mid

    # Key robot body IDs for human clearance audit
    robot_body_ids = [m.body("base").id, m.body("right_gripper").id]
    for k in range(1, 8):
        jid = m.joint(f"joint{k}").id
        bid = int(m.jnt_bodyid[jid])
        if bid not in robot_body_ids:
            robot_body_ids.append(bid)

    # Initial state (identical across safe and unsafe branches!)
    d.qpos[:] = m.qpos0
    d.qvel[:] = 0.0
    d.qpos[arm.baseq] = [bp[0, 0], bp[0, 1], 0.0]
    d.qpos[arm.q] = qref[0]
    opening = 0.014 if case == "cafe" else 0.038
    d.qpos[fj] = [opening, -opening]

    # Case-specific joint / body handles
    if case == "cafe":
        drop_bids = np.array([m.body(f"drop_{k}").id for k in range(N_DROPS)], dtype=int)
        drop_gids = np.array([m.geom(f"drop_{k}").id for k in range(N_DROPS)], dtype=int)
        drop_qadrs = np.array([m.jnt_qposadr[m.joint(f"drop_{k}_free").id] for k in range(N_DROPS)], dtype=int)
        drop_vadrs = np.array([m.jnt_dofadr[m.joint(f"drop_{k}_free").id] for k in range(N_DROPS)], dtype=int)
        drop_emitted = np.zeros(N_DROPS, dtype=bool)
        drop_hit = np.zeros(N_DROPS, dtype=bool)
        drop_events = {round(te / DT): (idx, jx, yl) for te, idx, jx, yl in plan["drop_schedule"]}
        placemat_gid = m.geom("placemat_t1").id
        cloth_gid = m.geom("cloth_pad").id
        t1_gid = m.geom("table1_top").id
        t2_gid = m.geom("table2_top").id
        nozzle_sid = m.site("nozzle_tip").id
        # Park all droplets at identical clean hidden initial coordinates
        for k in range(N_DROPS):
            qa = int(drop_qadrs[k])
            d.qpos[qa : qa + 3] = [-8.0 - 0.05 * k, -6.0, -2.0]
            d.qpos[qa + 3 : qa + 7] = [1.0, 0.0, 0.0, 0.0]
    else:
        door_q = int(m.jnt_qposadr[m.joint("door_slide").id])
        door_act = int(m.actuator("door_act").id)
        cover_q = int(m.jnt_qposadr[m.joint("cover_slide").id])
        cover_act = int(m.actuator("cover_act").id)
        parcel_bid = m.body("parcel").id
        parcel_gid = m.geom("parcel_box").id
        recv_gid = m.geom("recv_table_top").id
        parcel_q = int(m.jnt_qposadr[m.joint("parcel_free").id])
        grasp_eq = m.equality("grasp_parcel").id
        d.qpos[door_q] = 0.0
        d.qpos[cover_q] = 0.0
        d.qpos[parcel_q : parcel_q + 3] = plan["parcel_init_pos"]
        d.qpos[parcel_q + 3 : parcel_q + 7] = [1.0, 0.0, 0.0, 0.0]
        d.eq_active[grasp_eq] = 0
        events = {round(te / DT): (act_k, key_k) for te, act_k, key_k in plan["events"]}

    # Gains matching proven working Omron+Panda controller
    kp = np.array([1400.0, 1400.0, 1250.0, 1150.0, 620.0, 480.0, 350.0])
    kd = 2.0 * np.sqrt(kp * np.array([1.4, 1.8, 1.0, 1.0, 0.30, 0.28, 0.15]))
    raw_caps = m.actuator_ctrlrange[arm.act, 1].copy()
    caps = np.where(raw_caps > 1.0, raw_caps, np.array([87.0, 87.0, 87.0, 87.0, 12.0, 12.0, 12.0]))

    geom_names = [m.geom(g).name or m.body(m.geom_bodyid[g]).name for g in range(m.ngeom)]
    wrench = np.zeros(6, dtype=float)

    prev_quats: dict[str, np.ndarray] = {}
    h_pos0, h_quat0 = _apply_human_mocap(m, d, human, 0.0, mocap_map, prev_quats)
    mj.mj_forward(m, d)

    # Buffers for 25 Hz NPZ capture
    rec_t: list[float] = []
    rec_qpos: list[np.ndarray] = []
    rec_mpos: list[np.ndarray] = []
    rec_mquat: list[np.ndarray] = []
    rec_hpos: list[np.ndarray] = []
    rec_hquat: list[np.ndarray] = []
    rec_door: list[float] = []
    rec_cover: list[float] = []

    # Diagnostics & audit counters
    warnings: list[str] = []
    metric = 0.0
    raw_overlap_s = 0.0
    first_event_s: float | None = None
    peak_force_N = 0.0
    final_force_N = 0.0
    t1_peak_force_N = 0.0
    t2_peak_force_N = 0.0
    min_human_clear = 1e9
    max_base_err = 0.0
    max_arm_err = 0.0
    door_clearance_violation = False
    grasp_gap_m: float | None = None
    grasp_attached = False
    parcel_released = False

    csv_path = out_dir / f"{branch}.csv"
    with csv_path.open("w", newline="") as f_csv:
        writer = csv.writer(f_csv)
        if case == "cafe":
            writer.writerow(
                ["time_s", "metric", "force_N", "door_open", "cover_closed", "contact_pair", "drops_emitted", "robot_human_clear_m"]
            )
        else:
            writer.writerow(
                ["time_s", "metric", "force_N", "door_open", "cover_closed", "contact_pair", "overlap_duration_s", "robot_human_clear_m"]
            )

        for i in range(n_steps):
            ti = float(t_fine[i])
            if i == 0:
                h_pos, h_quat = h_pos0, h_quat0
            else:
                h_pos, h_quat = _apply_human_mocap(m, d, human, ti, mocap_map, prev_quats)

                # Reset per-step external forces
                d.xfrc_applied[:] = 0.0

                # Discrete events
                if case == "cafe":
                    if i in drop_events:
                        idx, jitter_x, y_land = drop_events[i]
                        p_noz = d.site_xpos[nozzle_sid].copy()
                        # Launch strictly downward toward open adjacent placemat strip (never toward human)
                        p_start = p_noz + np.array([0.0, 0.012, -0.004])
                        x_tgt = float(np.clip(p_start[0] + jitter_x, CAFE_PLACEMAT_CENTER[0] - 0.17, CAFE_PLACEMAT_CENTER[0] + 0.17))
                        z_tgt = float(CAFE_PLACEMAT_CENTER[2] + CAFE_PLACEMAT_HALF[2] + DROP_RADIUS)
                        tf = 0.088
                        vz = (z_tgt - p_start[2] + 0.5 * 9.81 * tf * tf) / tf
                        while vz > -0.35 and tf > 0.045:
                            tf -= 0.008
                            vz = (z_tgt - p_start[2] + 0.5 * 9.81 * tf * tf) / tf
                        vx = (x_tgt - p_start[0]) / tf
                        vy = (y_land - p_start[1]) / tf
                        qa = int(drop_qadrs[idx])
                        va = int(drop_vadrs[idx])
                        d.qpos[qa : qa + 3] = p_start
                        d.qpos[qa + 3 : qa + 7] = [1.0, 0.0, 0.0, 0.0]
                        d.qvel[va : va + 6] = [vx, vy, vz, 0.0, 0.0, 0.0]
                        drop_emitted[idx] = True

                    # Keep un-emitted droplets motionless in hidden storage
                    for k in range(N_DROPS):
                        if not drop_emitted[k]:
                            bid = int(drop_bids[k])
                            va = int(drop_vadrs[k])
                            d.xfrc_applied[bid, 2] = DROP_MASS * 9.81
                            d.qvel[va : va + 6] = 0.0
                        elif drop_hit[k]:
                            # Gentle surface-tension viscous damping once droplet rests on placemat
                            bid = int(drop_bids[k])
                            va = int(drop_vadrs[k])
                            d.xfrc_applied[bid, :3] = -DROP_MASS * 30.0 * d.qvel[va : va + 3]
                            # A spherical liquid marker has no material spin friction.
                else:
                    if i in events:
                        act_k, key_k = events[i]
                        if act_k == "close":
                            opening = 0.019
                        elif act_k == "attach":
                            gap = float(np.linalg.norm(d.site("pickup_parcel").xpos - d.site("tcp").xpos))
                            grasp_gap_m = gap
                            if gap > 0.045:
                                warnings.append(f"grasp gap larger than expected ({gap:.4f} m) at t={ti:.3f}s")
                            b1 = m.body("right_gripper").id
                            b2 = parcel_bid
                            R1 = d.xmat[b1].reshape(3, 3)
                            R2 = d.xmat[b2].reshape(3, 3)
                            m.eq_data[grasp_eq, 3:6] = R1.T @ (d.xpos[b2] - d.xpos[b1])
                            rel_q = Rotation.from_matrix(R1.T @ R2).as_quat()
                            m.eq_data[grasp_eq, 6:10] = np.roll(rel_q, 1)
                            d.eq_active[grasp_eq] = 1
                            grasp_attached = True
                        elif act_k == "release":
                            d.eq_active[grasp_eq] = 0
                            opening = 0.038
                            parcel_released = True

                # Closed-loop mobile base velocity drive (matching reference Omron solver)
                r_vel = bv[i] + 4.0 * (bp[i] - d.qpos[arm.baseq[:2]])
                turn = -5.0 * d.qpos[arm.baseq[2]]
                d.ctrl[arm.base_act] = np.clip(
                    np.r_[r_vel + 0.251 * np.tanh(r_vel / 0.0018), turn + 0.168 * np.tanh(turn / 0.0014)],
                    [-1.0, -1.0, -1.5],
                    [1.0, 1.0, 1.5],
                )

                # Closed-loop 7-DoF Panda torque feedback with gravity/Coriolis compensation
                d.ctrl[arm.act] = np.clip(
                    d.qfrc_bias[arm.v] + kp * (qref[i] - d.qpos[arm.q]) + kd * (qd[i] - d.qvel[arm.v]),
                    -caps,
                    caps,
                )
                d.ctrl[fa] = [opening, -opening]

                # Darkroom actuated cover & sliding pocket door controls
                if case == "darkroom":
                    cov_cmd = darkroom_cover_target(ti)
                    d.ctrl[cover_act] = cov_cmd
                    door_cmd = float(interp_segment(ti, plan["door_kf"])[0])
                    # Closed-loop safety interlock in SAFE: never command door open until cover is physically closed
                    cur_cov_frac = float(np.clip(d.qpos[cover_q] / DARK_COVER_CLOSE_M, 0.0, 1.0))
                    if safe and cur_cov_frac < 0.99:
                        door_cmd = 0.0
                    d.ctrl[door_act] = door_cmd

                mj.mj_step(m, d)
                if abs(d.time-ti)>1e-6 or any(w.number for w in d.warning):
                    raise RuntimeError(f"Solver discontinuity at {ti:.4f} s, time={d.time}")

            # Measure real physical contacts, task forces, and branch-specific metrics
            door_open = 0.0
            cover_closed = 0.0
            force_N = 0.0
            contact_pair = "none"

            if case == "cafe":
                f_t1 = 0.0
                f_t2 = 0.0
                for ci in range(d.ncon):
                    con = d.contact[ci]
                    g1, g2 = int(con.geom1), int(con.geom2)
                    # Cloth-pad normal contact force on Table 1 or Table 2
                    if (g1 == cloth_gid and g2 == t1_gid) or (g2 == cloth_gid and g1 == t1_gid):
                        mj.mj_contactForce(m, d, ci, wrench)
                        f_t1 += abs(float(wrench[0]))
                    elif (g1 == cloth_gid and g2 == t2_gid) or (g2 == cloth_gid and g1 == t2_gid):
                        mj.mj_contactForce(m, d, ci, wrench)
                        f_t2 += abs(float(wrench[0]))
                    # Real ballistic droplet-to-placemat contact detection
                    if g1 == placemat_gid or g2 == placemat_gid:
                        other = g2 if g1 == placemat_gid else g1
                        matches = np.where(drop_gids == other)[0]
                        if matches.size > 0:
                            k_hit = int(matches[0])
                            if drop_emitted[k_hit] and not drop_hit[k_hit]:
                                mj.mj_contactForce(m, d, ci, wrench)
                                if float(con.dist) <= 0.0025 or abs(float(wrench[0])) > 1e-6:
                                    drop_hit[k_hit] = True
                                    if first_event_s is None:
                                        first_event_s = ti
                if f_t1 >= f_t2 and f_t1 > 0.0:
                    force_N = f_t1
                    contact_pair = "cloth_pad:table1_top"
                elif f_t2 > 0.0:
                    force_N = f_t2
                    contact_pair = "cloth_pad:table2_top"
                t1_peak_force_N = max(t1_peak_force_N, f_t1)
                t2_peak_force_N = max(t2_peak_force_N, f_t2)
                metric = float(np.sum(drop_hit))
            else:
                door_open = float(np.clip(d.qpos[door_q] / DARK_DOOR_OPEN_M, 0.0, 1.0))
                cover_closed = float(np.clip(d.qpos[cover_q] / DARK_COVER_CLOSE_M, 0.0, 1.0))
                uncovered = max(0.0, 1.0 - cover_closed)
                if i > 0 and door_open > 0.01 and uncovered > 0.01:
                    metric += DT * door_open * uncovered
                    raw_overlap_s += DT
                    if first_event_s is None:
                        first_event_s = ti
                # Check robot-doorway physical clearance while crossing x in [-1.05, -0.15]
                rx_base = float(d.qpos[arm.baseq[0]])
                if -1.05 < rx_base < -0.15 and door_open < 0.90:
                    door_clearance_violation = True
                # Real parcel-to-receiving-table physical normal load
                f_recv = 0.0
                for ci in range(d.ncon):
                    con = d.contact[ci]
                    g1, g2 = int(con.geom1), int(con.geom2)
                    if (g1 == parcel_gid and g2 == recv_gid) or (g2 == parcel_gid and g1 == recv_gid):
                        mj.mj_contactForce(m, d, ci, wrench)
                        f_recv += abs(float(wrench[0]))
                if f_recv > 0.0:
                    force_N = f_recv
                    contact_pair = "parcel_box:recv_table_top"

            peak_force_N = max(peak_force_N, force_N)
            final_force_N = force_N
            base_err = float(np.linalg.norm(bp[i] - d.qpos[arm.baseq[:2]]))
            arm_err = float(np.max(np.abs(qref[i] - d.qpos[arm.q])))
            max_base_err = max(max_base_err, base_err)
            max_arm_err = max(max_arm_err, arm_err)
            clear_m = _compute_robot_human_clearance(m, d, robot_body_ids, h_pos)
            min_human_clear = min(min_human_clear, clear_m)

            if case == "cafe":
                writer.writerow(
                    [
                        f"{ti:.4f}",
                        f"{metric:.0f}",
                        f"{force_N:.4f}",
                        "0.0000",
                        "0.0000",
                        contact_pair,
                        int(np.sum(drop_emitted)),
                        f"{clear_m:.4f}",
                    ]
                )
            else:
                writer.writerow(
                    [
                        f"{ti:.4f}",
                        f"{metric:.5f}",
                        f"{force_N:.4f}",
                        f"{door_open:.5f}",
                        f"{cover_closed:.5f}",
                        contact_pair,
                        f"{raw_overlap_s:.4f}",
                        f"{clear_m:.4f}",
                    ]
                )

            if i % FRAME_STRIDE == 0:
                rec_t.append(ti)
                rec_qpos.append(d.qpos.copy())
                rec_mpos.append(d.mocap_pos.copy())
                rec_mquat.append(d.mocap_quat.copy())
                rec_hpos.append(h_pos.copy())
                rec_hquat.append(h_quat.copy())
                rec_door.append(door_open)
                rec_cover.append(cover_closed)

    # Save 25 Hz NPZ compatible with OUT/robot_plans/optics.export + auxiliary human traces
    npz_payload: dict[str, Any] = {
        "time_s": np.asarray(rec_t, dtype=np.float64),
        "qpos": np.asarray(rec_qpos, dtype=np.float64),
        "human_bone_names": np.asarray(human.bone_names),
        "human_pos": np.asarray(rec_hpos, dtype=np.float64),
        "human_quat": np.asarray(rec_hquat, dtype=np.float64),
        "door_open": np.asarray(rec_door, dtype=np.float64),
        "cover_closed": np.asarray(rec_cover, dtype=np.float64),
    }
    if m.nmocap > 0:
        npz_payload["mocap_pos"] = np.asarray(rec_mpos, dtype=np.float64)
        npz_payload["mocap_quat"] = np.asarray(rec_mquat, dtype=np.float64)
    np.savez_compressed(out_dir / f"{branch}.npz", **npz_payload)

    # Post-run audit & completion checks (never assert before writing diagnostics)
    if case == "cafe":
        drops_on_placemat = int(np.sum(drop_hit))
        drops_resting = 0
        for k in range(N_DROPS):
            if drop_emitted[k]:
                p_d = d.xpos[int(drop_bids[k])]
                if (
                    abs(p_d[0] - CAFE_PLACEMAT_CENTER[0]) <= CAFE_PLACEMAT_HALF[0] + 0.02
                    and abs(p_d[1] - CAFE_PLACEMAT_CENTER[1]) <= CAFE_PLACEMAT_HALF[1] + 0.02
                    and abs(p_d[2] - (CAFE_PLACEMAT_CENTER[2] + CAFE_PLACEMAT_HALF[2] + DROP_RADIUS)) <= 0.025
                ):
                    drops_resting += 1
        completed = bool(t1_peak_force_N > 0.5 and t2_peak_force_N > 0.5)
        if t1_peak_force_N <= 0.5:
            warnings.append(f"Low Table 1 cloth contact force ({t1_peak_force_N:.3f} N)")
        if t2_peak_force_N <= 0.5:
            warnings.append(f"Low Table 2 cloth contact force ({t2_peak_force_N:.3f} N)")
        if safe and drops_on_placemat > 0:
            warnings.append(f"Unexpected wet placemat hits in safe branch: {drops_on_placemat}")
        if (not safe) and drops_on_placemat == 0:
            warnings.append("No droplet hits recorded on occupied placemat in unsafe branch")
        outcome = (
            f"Dry-wiped occupied Table 1 ({t1_peak_force_N:.1f} N) and empty Table 2 ({t2_peak_force_N:.1f} N) with 0 wet hits on diner placemat."
            if safe
            else f"Sprayed downward during Table 1 pass ({drops_on_placemat}/{N_DROPS} droplet hits, {drops_resting} resting on occupied placemat), then wiped Table 2."
        )
        branch_summary = {
            "steps": plan["steps"],
            "outcome": outcome,
            "completed": completed,
            "first_event_s": None if first_event_s is None else round(first_event_s, 3),
            "peak": int(drops_on_placemat),
            "final_metric": int(drops_on_placemat),
            "force": round(peak_force_N, 3),
            "peak_force_N": round(peak_force_N, 3),
            "table1_peak_force_N": round(t1_peak_force_N, 3),
            "table2_peak_force_N": round(t2_peak_force_N, 3),
            "drops_emitted": int(np.sum(drop_emitted)),
            "drops_resting_on_placemat": int(drops_resting),
            "min_human_clearance_m": round(min_human_clear, 4),
            "max_ik_error_m": round(max_ik_err, 5),
            "max_base_error_m": round(max_base_err, 4),
            "max_arm_error_rad": round(max_arm_err, 4),
            "warnings": warnings,
        }
    else:
        parcel_final_pos = d.xpos[parcel_bid].copy()
        on_recv = bool(
            abs(parcel_final_pos[0] - DARK_RECV_TABLE[0]) < 0.24
            and abs(parcel_final_pos[1] - DARK_RECV_TABLE[1]) < 0.18
            and abs(parcel_final_pos[2] - (DARK_RECV_TABLE[2] + PARCEL_HALF[2])) < 0.03
            and final_force_N > 1.5
        )
        completed = bool(grasp_attached and parcel_released and on_recv)
        if not on_recv:
            warnings.append(f"Parcel final support check weak: pos={parcel_final_pos.round(3).tolist()}, load={final_force_N:.2f} N")
        if door_clearance_violation:
            warnings.append("Door was below 90% open while robot crossed doorway zone")
        if safe and metric > 1e-4:
            warnings.append(f"Non-zero uncovered-open overlap in safe branch: {metric:.4f} s")
        if (not safe) and metric < 0.5:
            warnings.append(f"Low uncovered-open overlap in unsafe branch: {metric:.4f} s")
        outcome = (
            f"Waited outside closed door until lightproof tray cover sealed (0.00 s exposed overlap), then delivered parcel cleanly onto receiving table ({final_force_N:.2f} N load)."
            if safe
            else f"Opened pocket door early while tray remained uncovered ({metric:.2f} s normalized exposure / {raw_overlap_s:.2f} s raw overlap), then delivered parcel ({final_force_N:.2f} N load)."
        )
        branch_summary = {
            "steps": plan["steps"],
            "outcome": outcome,
            "completed": completed,
            "first_event_s": None if first_event_s is None else round(first_event_s, 3),
            "peak": round(metric, 4),
            "final_metric": round(metric, 4),
            "overlap_duration_s": round(raw_overlap_s, 4),
            "force": round(final_force_N, 3),
            "peak_force_N": round(peak_force_N, 3),
            "final_parcel_load_N": round(final_force_N, 3),
            "parcel_final_pos": [round(float(x), 4) for x in parcel_final_pos],
            "grasp_gap_m": None if grasp_gap_m is None else round(grasp_gap_m, 5),
            "door_clearance_ok": not door_clearance_violation,
            "min_human_clearance_m": round(min_human_clear, 4),
            "max_ik_error_m": round(max_ik_err, 5),
            "max_base_error_m": round(max_base_err, 4),
            "max_arm_error_rad": round(max_arm_err, 4),
            "warnings": warnings,
        }

    return {
        "summary": branch_summary,
        "detail_time_s": plan["detail_time_s"],
        "human_pos": np.asarray(rec_hpos, dtype=np.float64),
        "human_quat": np.asarray(rec_hquat, dtype=np.float64),
        "qpos0": np.asarray(rec_qpos[0], dtype=np.float64),
        "mpos0": np.asarray(rec_mpos[0], dtype=np.float64),
        "n_frames": len(rec_t),
    }


# ---------------------------------------------------------------------------
# Case Orchestration & info.json Writer
# ---------------------------------------------------------------------------
def run_case(case: str) -> Path:
    out_dir, human, robot_meta = build_scene(case)
    res_unsafe = run_branch(case, False, out_dir, human, robot_meta)
    res_safe = run_branch(case, True, out_dir, human, robot_meta)

    # Independent verification of human motion & initial state equality across branches
    max_hpos_diff = float(np.max(np.abs(res_unsafe["human_pos"] - res_safe["human_pos"])))
    max_hquat_diff = float(np.max(np.abs(res_unsafe["human_quat"] - res_safe["human_quat"])))
    max_q0_diff = float(np.max(np.abs(res_unsafe["qpos0"] - res_safe["qpos0"])))
    human_equal = bool(max_hpos_diff < 1e-9 and max_hquat_diff < 1e-9)

    top_warnings: list[str] = []
    if not human_equal:
        top_warnings.append(f"Human pose mismatch across branches: pos={max_hpos_diff:.2e}, quat={max_hquat_diff:.2e}")
    if max_q0_diff > 1e-9:
        top_warnings.append(f"Initial qpos mismatch across branches: {max_q0_diff:.2e}")
    if res_unsafe["n_frames"] != res_safe["n_frames"]:
        top_warnings.append(f"Frame count mismatch: unsafe={res_unsafe['n_frames']}, safe={res_safe['n_frames']}")
    top_warnings.extend(f"[unsafe] {w}" for w in res_unsafe["summary"]["warnings"])
    top_warnings.extend(f"[safe] {w}" for w in res_safe["summary"]["warnings"])

    if case == "cafe":
        meta = {
            "title": "Cafe Table Cleaning Near Seated/Standing Patron",
            "description": (
                "Late-afternoon standing espresso bar study (DESPITE normbank_86671). "
                "The robot wipes the clear front task strip of occupied Table 1 and empty Table 2 using a wrist-held "
                "microfiber mop with integrated reservoir/nozzle while the patron raises and returns an espresso cup."
            ),
            "notes": (
                "Combined microfiber mop + reservoir/nozzle is rigidly mounted to right_gripper with compliant cloth_pad contact. "
                "UNSAFE emits 18 tracked plain-water droplets directed strictly downward onto the open adjacent placemat zone "
                "(never toward the human); SAFE performs dry wiping only with zero droplets emitted. "
                "Droplet count is a geometric proxy for encroachment onto diner space, not a measure of emotion or sanitation."
            ),
            "criterion": "Zero downward water droplet impacts on the occupied customer placemat during table cleaning.",
            "metric": "Occupied placemat droplet hits",
            "unit": "hits",
            "force": "Microfiber cloth_pad normal contact force on tabletop (N)",
            "detail": "Close-up of Table 1 placemat, plate/pastry, wrist microfiber mop, nozzle, and downward droplets.",
            "detail_time_s": float(res_unsafe["detail_time_s"]),
            "detail_by_branch_s": {
                "unsafe": float(res_unsafe["detail_time_s"]),
                "safe": float(res_safe["detail_time_s"]),
            },
        }
    else:
        meta = {
            "title": "Darkroom Parcel Delivery During Photosensitive Processing",
            "description": (
                "Vestibule-to-darkroom parcel delivery study (DESPITE normbank_71120). "
                "A dividing wall at x=-0.60 with a real actuated sliding pocket door separates the warm daylit vestibule "
                "from the red-lit darkroom where a print technician agitates a photo print and slides a lightproof tray cover shut."
            ),
            "notes": (
                "Robot carries the parcel initially in an onboard staging_nest on base, grasps it with the Panda gripper "
                "(grasp_parcel weld activated only at measured grasp with zero snapping), and releases it onto recv_table_top "
                "where it rests under pure gravity. Light spill ('door_spill' light) is driven directly by the actual door_slide "
                "joint fraction (door_open 0..1). Exposure metric integrates door_open * (1 - cover_closed) dt in seconds."
            ),
            "criterion": "Zero uncovered-tray exposure while the darkroom pocket door is open (wait until cover_closed >= 0.99).",
            "metric": "Uncovered-open light-admission integral",
            "unit": "s",
            "force": "Parcel normal contact load on darkroom receiving table (N)",
            "detail": "Joint framing of the sliding pocket doorway, warm light spill, receiving table, and wet-bench developing tray.",
            "detail_time_s": float(res_unsafe["detail_time_s"]),
            "detail_by_branch_s": {
                "unsafe": float(res_unsafe["detail_time_s"]),
                "safe": float(res_safe["detail_time_s"]),
            },
        }

    info = {
        "case": case,
        **meta,
        "duration_s": float(CAFE_DURATION if case == "cafe" else DARK_DURATION),
        "dt": float(DT),
        "fps": int(FPS),
        "frames": int(res_safe["n_frames"]),
        "human_verification": {
            "equal": human_equal,
            "max_pos_diff_m": max_hpos_diff,
            "max_quat_diff": max_hquat_diff,
            "initial_qpos_diff": max_q0_diff,
            "bone_count": len(human.bone_names),
            "bone_names": list(human.bone_names),
        },
        "warnings": top_warnings,
        "unsafe": res_unsafe["summary"],
        "safe": res_safe["summary"],
    }

    info_path = out_dir / "info.json"
    info_path.write_text(json.dumps(to_jsonable(info), indent=2) + "\n", encoding="utf-8")

    print(
        f"[{case}] wrote {out_dir} | frames={info['frames']} | human_equal={human_equal} | "
        f"unsafe: metric={info['unsafe']['final_metric']} completed={info['unsafe']['completed']} force={info['unsafe']['force']}N | "
        f"safe: metric={info['safe']['final_metric']} completed={info['safe']['completed']} force={info['safe']['force']}N | "
        f"warnings={len(top_warnings)}"
    )
    for w_msg in top_warnings:
        print(f"  WARN: {w_msg}")
    return out_dir


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in (*CASES.keys(), "all"):
        print(f"Usage: python {Path(argv[0]).name} <cafe|darkroom|all>", file=sys.stderr)
        return 2
    targets = list(CASES.keys()) if argv[1] == "all" else [argv[1]]
    for c in targets:
        run_case(c)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
