#!/usr/bin/env python3
"""Build the 75-episode Panda 6062-eval hierarchy and video manifest."""

from __future__ import annotations

import argparse
import bisect
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import h5py

sys.path.insert(0, "/cluster/home/jiaxia/panda_data_processing")
from panda_subtask_pipeline.panda_h5_media import FRONT_GROUP, WRIST_GROUP, estimate_fps, sorted_keys


TASK_ORDER = {
    "push the obstacle aside and put the apple in the plate": 0,
    "put all the fruits in the basket": 1,
    "put the apple on the plate": 2,
    "put the banana on the plate": 3,
    "put the egg in the egg tray": 4,
    "sweep the trash into the dustpan": 5,
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def public_url(base: str, bucket: str, key: str) -> str:
    encoded = "/".join(quote(part, safe="") for part in key.split("/"))
    return f"{base.rstrip('/')}/{quote(bucket, safe='')}/{encoded}"


def source_index(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(row["episode_key"]): row for row in payload["episodes"]}


def target_media(path: Path) -> dict[str, Any]:
    with h5py.File(path, "r") as handle:
        front = sorted_keys(handle[FRONT_GROUP])
        wrist = sorted_keys(handle[WRIST_GROUP]) if WRIST_GROUP in handle else []
    front_ns = [int(value) for value in front]
    return {
        "total_frames": len(front),
        "fps": estimate_fps(front_ns),
        "front_frames": len(front),
        "wrist_frames": len(wrist),
    }


def scale_atomic_tasks(source: dict[str, Any], target_h5: Path) -> list[dict[str, Any]]:
    source_h5 = Path(source["source_h5_path"])
    source_segments = source["subtasks"]
    with h5py.File(source_h5, "r") as handle:
        source_keys = sorted_keys(handle[FRONT_GROUP])
    with h5py.File(target_h5, "r") as handle:
        target_keys = sorted_keys(handle[FRONT_GROUP])
    source_ns = [int(value) for value in source_keys]
    target_ns = [int(value) for value in target_keys]

    source_boundaries = [0] + [int(segment["end_frame"]) + 1 for segment in source_segments]
    target_boundaries = [0]
    for source_boundary in source_boundaries[1:-1]:
        source_boundary = max(1, min(len(source_ns) - 1, source_boundary))
        target_boundary = bisect.bisect_left(target_ns, source_ns[source_boundary])
        minimum = target_boundaries[-1] + 1
        remaining = len(source_boundaries) - len(target_boundaries) - 1
        maximum = len(target_ns) - remaining
        target_boundaries.append(max(minimum, min(maximum, target_boundary)))
    target_boundaries.append(len(target_ns))

    return [
        {
            "atomic_task_id": f"atomic_{index + 1}",
            "atomic_task": str(segment["subtask"]),
            "start_frame": target_boundaries[index],
            "end_frame": target_boundaries[index + 1] - 1,
            "boundary_source": str(segment.get("boundary_source") or source.get("review_status") or "source_segmentation"),
        }
        for index, segment in enumerate(source_segments)
    ]


def make_mission(index: int, label: str, atoms: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "mission_id": f"mission_{index}",
        "mission": label,
        "start_frame": atoms[0]["start_frame"],
        "end_frame": atoms[-1]["end_frame"],
        "atomic_task_ids": [atom["atomic_task_id"] for atom in atoms],
        "short_term_mission_id": f"mission_{index}",
        "short_term_mission": label,
    }


def refined_all_fruits_hierarchy(
    record_id: str,
    total_frames: int,
    refinements: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    refinement = refinements.get(record_id)
    if refinement is None:
        raise KeyError(f"Missing dual-view all-fruits refinement for {record_id}")
    fruits = [str(value) for value in refinement["fruit_order"]]
    pick_ends = [int(value) for value in refinement["pick_end_frames"]]
    mission_ends = [int(value) for value in refinement["mission_end_frames"]]
    if not (len(fruits) == len(pick_ends) == len(mission_ends) == 5):
        raise ValueError(f"All-fruits refinement must contain five transfers: {record_id}")
    if mission_ends[-1] != total_frames - 1:
        raise ValueError(f"Final all-fruits mission must end on the last frame: {record_id}")

    atoms: list[dict[str, Any]] = []
    missions: list[dict[str, Any]] = []
    mission_start = 0
    for mission_index, (fruit, pick_end, mission_end) in enumerate(
        zip(fruits, pick_ends, mission_ends), start=1
    ):
        if not mission_start <= pick_end < mission_end < total_frames:
            raise ValueError(
                f"Invalid all-fruits boundaries for {record_id} mission {mission_index}: "
                f"{mission_start}, {pick_end}, {mission_end}"
            )
        pick_id = f"atomic_{len(atoms) + 1}"
        place_id = f"atomic_{len(atoms) + 2}"
        atoms.extend([
            {
                "atomic_task_id": pick_id,
                "atomic_task": f"pick up the {fruit}",
                "start_frame": mission_start,
                "end_frame": pick_end,
                "boundary_source": "codex_manual_dual_view_review",
            },
            {
                "atomic_task_id": place_id,
                "atomic_task": f"place the {fruit} in the basket",
                "start_frame": pick_end + 1,
                "end_frame": mission_end,
                "boundary_source": "codex_manual_dual_view_review",
            },
        ])
        mission_label = f"put the {fruit} in the basket"
        missions.append(make_mission(mission_index, mission_label, atoms[-2:]))
        mission_start = mission_end + 1

    long_term = [{
        "long_term_mission_id": "long_mission_1",
        "long_term_mission": "put all the fruits in the basket",
        "start_frame": 0,
        "end_frame": total_frames - 1,
        "member_short_term_mission_ids": [mission["mission_id"] for mission in missions],
        "activation_member_position": 3,
        "activation_short_term_mission_id": missions[2]["mission_id"],
        "activation_frame": missions[2]["start_frame"],
    }]
    return atoms, missions, long_term


def hierarchy(full_task: str, overall_task: str, atoms: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool, list[dict[str, Any]]]:
    if overall_task == "push the obstacle aside and put the apple in the plate" and len(atoms) >= 3:
        return [
            make_mission(1, "push the obstacle away", atoms[:1]),
            make_mission(2, "put the apple in the plate", atoms[1:]),
        ], False, []
    return [make_mission(1, full_task, atoms)], False, []


def build(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = read_jsonl(args.eval_manifest)
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        record_id = str(row["record_id"])
        if record_id not in grouped:
            grouped[record_id] = row
    if len(grouped) != 75:
        raise ValueError(f"Expected 75 physical episodes, found {len(grouped)}")

    sources = source_index(args.source_segments)
    refinement_payload = json.loads(args.all_fruits_refinement.read_text(encoding="utf-8"))
    all_fruits_refinements = refinement_payload["episodes"]
    ordered = sorted(grouped.values(), key=lambda row: (TASK_ORDER.get(str(row["overall_task"]), 999), str(row["record_id"])))
    tasks = sorted({str(row["overall_task"]) for row in ordered}, key=lambda value: TASK_ORDER.get(value, 999))
    task_ids = {task: index + 1 for index, task in enumerate(tasks)}
    task_episode_counts: Counter[str] = Counter()
    episodes = []
    private_rows = []
    for episode_index, row in enumerate(ordered, start=1):
        record_id = str(row["record_id"])
        source_key = str(row["gt_segmentation_episode_key"])
        source = sources.get(source_key)
        if source is None:
            raise KeyError(f"Missing source segmentation for {source_key}")
        h5_path = Path(row["h5_path"])
        media = target_media(h5_path)
        if media["wrist_frames"] <= 0:
            raise ValueError(f"Evaluation episode has no wrist view: {h5_path}")
        atoms = scale_atomic_tasks(source, h5_path)
        full_task = str(row["gt_full_task"])
        overall_task = str(row["overall_task"])
        if overall_task == "put all the fruits in the basket":
            atoms, missions, long_term = refined_all_fruits_hierarchy(
                record_id, int(media["total_frames"]), all_fruits_refinements
            )
            long_horizon = True
        else:
            missions, long_horizon, long_term = hierarchy(full_task, overall_task, atoms)
        object_keys = {
            "front": f"{args.object_prefix.strip('/')}/{record_id}/front.mp4",
            "wrist": f"{args.object_prefix.strip('/')}/{record_id}/wrist.mp4",
        }
        video_urls = {view: public_url(args.download_base, args.bucket, key) for view, key in object_keys.items()}
        task_episode_counts[overall_task] += 1
        episodes.append({
            "dataset": "panda_eval_6062",
            "dataset_label": "Panda Eval 6062",
            "task_id": task_ids[overall_task],
            "task_label": overall_task,
            "episode_id": episode_index,
            "episode_name": record_id.rsplit("/", 1)[-1],
            "record_id": record_id,
            "parent_episode_key": f"panda_eval_6062/{record_id}",
            "split": "test",
            "full_episode_instruction": full_task,
            "fps": float(media["fps"]),
            "total_frames": int(media["total_frames"]),
            "video_url": video_urls["front"],
            "video_urls": video_urls,
            "video_object_keys": object_keys,
            "evaluation_views": ["front", "wrist"],
            **(
                {"human_review_revision": "panda-all-fruits-dual-view-20260905"}
                if overall_task == "put all the fruits in the basket"
                else {}
            ),
            "atomic_grouping_provenance": (
                "codex_manual_dual_view_review"
                if overall_task == "put all the fruits in the basket"
                else "panda_6062_frozen_ground_truth"
            ),
            "atomic_tasks": atoms,
            "missions": missions,
            "short_term_missions": missions,
            "long_horizon": long_horizon,
            "long_term_missions": long_term,
            "reviewed": False,
            "segmentation": {
                "method": (
                    "codex_manual_dual_view_review_with_gripper_event_anchors"
                    if overall_task == "put all the fruits in the basket"
                    else "frozen_panda_6062_source_segments"
                ),
                "imputed": False,
            },
        })
        private_rows.append({
            "record_id": record_id,
            "h5_path": str(h5_path),
            "fps": float(media["fps"]),
            "total_frames": int(media["total_frames"]),
            "object_keys": object_keys,
            "video_urls": video_urls,
        })

    now = datetime.now(timezone.utc).isoformat()
    site_data = {
        "schema_version": 1,
        "generated_at_utc": now,
        "frame_semantics": "inclusive continuous frame indices on synchronized 15 Hz Panda evaluation videos",
        "hierarchy": "full episode instruction > long-term missions > short-term missions > atomic tasks",
        "summary": {
            "dataset_count": 1,
            "task_count": len(task_ids),
            "episode_count": len(episodes),
            "video_count": len(episodes) * 2,
            "evaluation_sample_count": 6062,
            "task_episode_counts": dict(task_episode_counts),
        },
        "episodes": episodes,
        "ongoing_mission_policy": "Use the short-term mission containing the sample frame; for a long-horizon group, use the long-term label from its third member short-term mission onward.",
        "annotation_version": "panda_eval_6062_v2_all_fruits_manual_20260905",
    }
    private_manifest = {
        "schema_version": 1,
        "generated_at_utc": now,
        "bucket": args.bucket,
        "object_prefix": args.object_prefix,
        "summary": {"episode_count": len(private_rows), "video_count": len(private_rows) * 2},
        "episodes": private_rows,
    }
    return site_data, private_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-manifest", type=Path, required=True)
    parser.add_argument("--source-segments", type=Path, required=True)
    parser.add_argument(
        "--all-fruits-refinement",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "panda-eval-v2" / "all_fruits_refinement.json",
    )
    parser.add_argument("--site-output", type=Path, required=True)
    parser.add_argument("--video-manifest-output", type=Path, required=True)
    parser.add_argument("--object-prefix", default="panda-eval-6062")
    parser.add_argument("--download-base", default="https://s3-hot.liuzisen.com")
    parser.add_argument("--bucket", default="videos")
    args = parser.parse_args()
    site_data, video_manifest = build(args)
    args.site_output.parent.mkdir(parents=True, exist_ok=True)
    args.video_manifest_output.parent.mkdir(parents=True, exist_ok=True)
    args.site_output.write_text(json.dumps(site_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.video_manifest_output.write_text(json.dumps(video_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(site_data["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
