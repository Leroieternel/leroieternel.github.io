import xml.etree.ElementTree as ET

_BIT = 32
_FITTINGS = {3: ("fab_03_sh_hdl_r", "fab_03_cafe_endpanel_right"), 8: ("fab_08_pc_hdl_grip",)}


def _floats(text, default):
    return [float(x) for x in text.split()] if text else list(default)


def _add(out, name):
    if name and name not in out:
        out.append(name)


def _geom_defaults(root):
    defs = {"": (1, 1)}
    def walk(node, base):
        g = node.find("geom")
        ct = int(g.get("contype")) if g is not None and g.get("contype") is not None else base[0]
        ca = int(g.get("conaffinity")) if g is not None and g.get("conaffinity") is not None else base[1]
        defs[node.get("class") or ""] = (ct, ca)
        for ch in node.findall("default"):
            walk(ch, (ct, ca))
    for d in root.findall("default"):
        walk(d, (1, 1))
    return defs


def _is_free_body(body):
    return not (body.get("name") or "").startswith("fab_") and any(
        c.tag == "freejoint" or (c.tag == "joint" and c.get("type") == "free") for c in body
    )


def _fix_case_6(wb, affected):
    def prune(parent):
        for ch in list(parent):
            name = ch.get("name") or ""
            if ch.tag in ("body", "geom", "site") and (name == "fab_06_ctrl_bezel_0" or name.startswith("fab_06_ctrl_ped_0_")):
                parent.remove(ch)
                _add(affected, name)
            else:
                prune(ch)
    prune(wb)
    for parent in wb.iter():
        for g in parent.findall("geom"):
            if g.get("name") != "fab_06_gate_wear_strip":
                continue
            pos = _floats(g.get("pos"), (0.0, 0.0, 0.0))
            lhx = _floats(g.get("size"), (0.003,))[0]
            ref, best = pos[0] + lhx, None
            for sib in parent.findall("geom"):
                if sib is g or (sib.get("name") or "").startswith("fab_"):
                    continue
                ssz = _floats(sib.get("size"), ())
                if sib.get("type") in ("box", None) and len(ssz) == 3:
                    sx = _floats(sib.get("pos"), (0.0, 0.0, 0.0))[0]
                    lo, hi = sx - ssz[0], sx + ssz[0]
                    d = min(abs(lo - ref), abs(hi - ref))
                    if best is None or d < best[0]:
                        best = (d, lo, hi)
            hi0 = abs(pos[0]) - lhx if pos[0] < 0 else pos[0] + lhx
            lo, hi = (best[1], best[2]) if best and best[0] < 0.02 else (-hi0, hi0)
            pos[0] = hi - lhx - min(0.001, max(0.0, (hi - lo) * 0.5 - lhx))
            g.set("pos", " ".join(f"{v:.6g}" for v in pos))
            _add(affected, "fab_06_gate_wear_strip")


def _fix_contact_case(root, wb, targets, affected):
    defs, tset = _geom_defaults(root), set(targets)
    def walk(node, ccls, free, bname):
        if node.tag == "body":
            ccls = node.get("childclass") or ccls
            free = free or _is_free_body(node)
            bname = node.get("name") or bname
        name = node.get("name") or ""
        if name in tset:
            for g in ([node] if node.tag == "geom" else node.findall(".//geom")):
                g.set("contype", str(_BIT))
                g.set("conaffinity", "0")
                _add(affected, g.get("name") or name)
            return
        if node.tag == "geom" and free and not name.startswith("fab_"):
            d_ct, d_ca = defs.get(node.get("class") or ccls, defs[""])
            ct = int(node.get("contype")) if node.get("contype") is not None else d_ct
            ca = int(node.get("conaffinity")) if node.get("conaffinity") is not None else d_ca
            if ct != 0 or ca != 0:
                node.set("conaffinity", str(ca | _BIT))
                _add(affected, name or bname)
        for ch in node:
            walk(ch, ccls, free, bname)
    walk(wb, "", False, "")


def correct(root, k):
    root = root.getroot() if isinstance(root, ET.ElementTree) else root
    wb = next(iter(root.findall("worldbody")), root)
    affected = []
    if k == 6:
        _fix_case_6(wb, affected)
    elif k in _FITTINGS:
        _fix_contact_case(root, wb, _FITTINGS[k], affected)
    return affected
