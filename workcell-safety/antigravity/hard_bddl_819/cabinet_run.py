"""Re-run the original Baxter controller against the actual bedside cabinet top."""
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
HARD = HERE.parent / "hard1044"
LIB = HERE.parents[1] / "mobile_worlds/library"
sys.path.insert(0, str(HARD))
from production import sim_desk
from run import Recorder, write_json
from robotlib import contacts as original_contacts


def simulate():
    origin = HARD / "runs/24_bddl_819"
    dest = HERE / "cabinet/runs/24_bddl_819"
    dest.mkdir(exist_ok=True, parents=True)
    info = json.loads((origin / "info.json").read_text())
    tree = ET.parse(origin / "scene.xml")
    body = tree.find(".//body[@name='bedroom_bed']")
    assert {g.get("name") for g in body} == {"bed_mattress", "bed_headboard", "bed_blanket", "bed_pillow"}
    body.clear()
    scale = .50 / .55638
    center_x = .639 - scale * .43828 / 2
    body.attrib.update(name="bedside_cabinet", pos=f"{center_x} -0.18 0", quat="0 0 0 1")
    with np.load(LIB / "cache/geometry_hd/nightstand.npz") as native:
        vertices = native["vertices"]
        top = np.unique(vertices[vertices[:, 2] > .53], axis=0) * scale
    mesh_name = "genie_nightstand_002_tabletop_hull"
    ET.SubElement(tree.find("asset"), "mesh", name=mesh_name,
                  vertex=" ".join(f"{value:.8f}" for value in top.ravel()))
    physical = {"priority": "2", "solref": ".006 1", "solimp": ".975 .998 .0007", "friction": ".7 .01 .002"}
    ET.SubElement(body, "geom", name="nightstand_collision_top", type="mesh", mesh=mesh_name, **physical)
    ET.SubElement(body, "geom", name="nightstand_collision_base", type="box", pos="0 0 .365", size=".170 .244 .111", **physical)
    # The next pair runs the existing robot policy, including the original
    # free release. Only the measured support contact pair is redirected.
    def contact_pair(model, data, first, second):
        second = {"@bed_mattress": "@nightstand_collision_top", "@bed_headboard": "@nightstand_collision_base"}.get(second, second)
        force = original_contacts(model, data, first, second)
        if first == "poster" and second in contact_peaks:
            contact_peaks[second] = max(contact_peaks[second], force)
            if force > 0 and second not in first_touch:
                first_touch[second] = float(data.time)
        return force

    tree.write(dest / "scene.xml", encoding="utf-8")
    model = mujoco.MjModel.from_xml_path(str(dest / "scene.xml"))
    sim_desk.contacts = contact_pair
    for branch in ("safe", "unsafe"):
        contact_peaks = dict.fromkeys(("@nightstand_collision_top", "@nightstand_collision_base", "@floor"), 0.)
        first_touch = {}
        rec = Recorder(model)
        report = sim_desk.simulate(info["design"], model, branch, rec)
        physical_report = rec.save(dest, branch)
        physical_report.update(support_peak_N=contact_peaks, first_contact_s=first_touch)
        where = "bedside cabinet" if contact_peaks["@floor"] == 0 else "bedside cabinet or floor"
        report["outcome"] = report["outcome"].replace("bed/floor", where)
        report["steps"] = [[t, label.replace("bed headboard", "bedside cabinet")] for t, label in report["steps"]]
        info["branches"][branch] = report
        info["physics"][branch] = physical_report
        write_json(dest / (branch + ".json"), {"result": report, "physics": physical_report})
    good, bad = (info["branches"][b] for b in ("safe", "unsafe"))
    info["passed"] = bool(good["goal"] and not good["hazard"] and bad["hazard"])
    info["detail_time_s"] = bad["event_s"]
    info["furniture"] = {"support": "benchmark_nightstand_002", "collision": "MuJoCo convex hull of the native upper slab and a separate drawer body",
                         "native_tabletop_vertices": len(top), "visual_rotation_radians": float(np.pi), "uniform_scale": scale}
    write_json(dest / "info.json", info)
    if not info["passed"] or any(p["warnings"] for p in info["physics"].values()):
        raise RuntimeError("Cabinet simulation did not reproduce the paired outcomes")
    # The event trace stores all contacts; ensure that the force reported for
    # the fall actually came from the cabinet rather than simply from the floor.
    assert info["physics"]["unsafe"]["support_peak_N"]["@nightstand_collision_top"] > 0
    import export
    export.optics.ROOT = dest.parent
    export.optics.CACHE = HERE / "cabinet/optics"
    export.optics.export(24)
    print({b: info["physics"][b]["peak_force_N"] for b in ("safe", "unsafe")}, flush=True)


if __name__ == "__main__":
    simulate()
