from __future__ import annotations
from collections.abc import Iterable, Mapping
import re
import xml.etree.ElementTree as ET
import mujoco
import numpy as np

PREFIX = "fab_05_prc_"
VALID_TYPES = frozenset({"mesh", "box", "cylinder"})
SUPPORT_KEYS = (
    "rail block move moving transfer frame table catch apron guide tray chute deck plate beam bed "
    "ramp pan guard support shelf bracket bar post leg strut base lip flange skirt stop ledge "
    "channel cradle sled shuttle platen conveyor belt roller bin hopper trough bridge wall side"
).split()
EXCLUDE_WORDS = frozenset((
    "bolt screw nut washer rivet fastener label decal logo badge sticker sensor switch button "
    "led lamp light indicator cable wire hose plug marker arrow text display screen cosmetic barcode"
).split())

def _geom_defaults(root: ET.Element) -> dict[str, dict[str, str]]:
    defaults: dict[str, dict[str, str]] = {"": {}}
    def walk(node: ET.Element, base: dict[str, str]) -> None:
        g = node.find("geom")
        cur = {**base, **(g.attrib if g is not None else {})}
        defaults[node.get("class", "")] = cur
        for child in node.findall("default"):
            walk(child, cur)
    for top in root.findall("default"):
        walk(top, defaults[""])
    return defaults

def _unused_bit(root: ET.Element, start: int = 32) -> int:
    used = 1
    for g in root.iter("geom"):
        used |= int(g.attrib.get("contype", 0)) | int(g.attrib.get("conaffinity", 0))
    bit = start
    while used & bit:
        bit <<= 1
        if bit >= (1 << 31):
            raise RuntimeError("No unused 32-bit collision bit available.")
    return bit

def apply(root: ET.Element | ET.ElementTree) -> ET.Element:
    el = root.getroot() if isinstance(root, ET.ElementTree) else root
    world = el.find("worldbody")
    if world is None:
        raise ValueError("MJCF root missing <worldbody>.")
    defaults, bit = _geom_defaults(el), _unused_bit(el, 32)
    parcel: tuple[ET.Element, dict[str, str]] | None = None
    candidates: list[tuple[ET.Element, str, set[str]]] = []
    def scan(node: ET.Element, path: tuple[str, ...], ccls: str) -> None:
        nonlocal parcel
        for child in node:
            if child.tag == "body":
                scan(child, path + (child.get("name", ""),), child.get("childclass") or ccls)
            elif child.tag == "geom":
                eff = {**defaults.get(child.get("class") or ccls, defaults[""]), **child.attrib}
                name = child.get("name", "")
                if name == "parcel":
                    parcel = (child, eff)
                elif name.startswith(PREFIX):
                    gtype = eff.get("type") or ("mesh" if "mesh" in eff else "sphere")
                    if (gtype in VALID_TYPES and int(eff.get("group", "0")) == 2
                            and float(eff.get("mass", "0")) == 0.0
                            and int(eff.get("contype", "1")) == 0
                            and int(eff.get("conaffinity", "1")) == 0):
                        norm = re.sub(r"([a-z])([A-Z])", r"\1_\2", f"{name} {' '.join(path)}").lower()
                        candidates.append((child, norm, set(re.findall(r"[a-z]+", norm))))
    scan(world, (), "")
    if parcel is None:
        raise ValueError("Missing geom named 'parcel'.")
    active = [g for g, t, w in candidates if any(k in t for k in SUPPORT_KEYS) and not (w & EXCLUDE_WORDS)]
    active = active or [g for g, _, w in candidates if not (w & EXCLUDE_WORDS)]
    if not active:
        raise ValueError(f"No load-bearing '{PREFIX}*' support geoms found.")
    for g in active:
        g.set("contype", str(bit))
        g.set("conaffinity", "0")
    parcel[0].set("conaffinity", str(int(parcel[1].get("conaffinity", "1")) | bit))
    return el

def loads(
    model: mujoco.MjModel, data: mujoco.MjData,
    geom_ids: Iterable[int] | Mapping[str, int] | Mapping[int, str],
    payload_geom_id: int | str,
) -> dict[str, float]:
    pid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, payload_geom_id) if isinstance(payload_geom_id, str) else int(payload_geom_id)
    if pid < 0:
        raise ValueError(f"Unknown payload geom: {payload_geom_id!r}")
    if isinstance(geom_ids, Mapping):
        id_map = {(int(v) if isinstance(k, str) else int(k)): (k if isinstance(k, str) else str(v)) for k, v in geom_ids.items()}
    else:
        id_map = {int(g): (mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, int(g)) or str(g)) for g in geom_ids}
    out = {name: 0.0 for name in id_map.values()}
    cf = np.zeros(6, dtype=np.float64)
    for i in range(int(data.ncon)):
        con = data.contact[i]
        if con.efc_address < 0:
            continue
        g1, g2 = int(con.geom1), int(con.geom2)
        name = id_map.get(g2 if g1 == pid else (g1 if g2 == pid else -1))
        if name is not None:
            cf[:] = 0.0
            mujoco.mj_contactForce(model, data, i, cf)
            if cf[0] > 0.0:
                out[name] += float(cf[0])
    return out
