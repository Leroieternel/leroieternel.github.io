#!/usr/bin/env python3
"""Export synchronized Panda eval front/wrist videos and publish them to RustFS."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config

sys.path.insert(0, "/cluster/home/jiaxia/panda_data_processing")
from panda_subtask_pipeline.panda_h5_media import FRONT_GROUP, WRIST_GROUP, export_h5_camera_video


def make_client(args: argparse.Namespace):
    access = os.getenv("RUSTFS_ACCESS_KEY") or os.getenv("AWS_ACCESS_KEY_ID")
    secret = os.getenv("RUSTFS_SECRET_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
    if not access or not secret:
        raise RuntimeError("RustFS credentials are missing")
    return boto3.client(
        "s3",
        endpoint_url=args.endpoint,
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        region_name="us-east-1",
        config=Config(
            signature_version="s3v4", s3={"addressing_style": "path"},
            retries={"max_attempts": args.retries, "mode": "adaptive"},
            connect_timeout=30, read_timeout=300,
            max_pool_connections=max(32, args.workers * 4),
        ),
    )


def head_ok(client: Any, bucket: str, key: str) -> dict[str, Any] | None:
    try:
        response = client.head_object(Bucket=bucket, Key=key)
        size = int(response.get("ContentLength", 0))
        return {"bytes": size, "etag": response.get("ETag")} if size > 0 else None
    except Exception:
        return None


def upload(client: Any, path: Path, bucket: str, key: str) -> dict[str, Any]:
    size = path.stat().st_size
    remote = head_ok(client, bucket, key)
    if remote and remote["bytes"] == size:
        return {"status": "already_present", **remote}
    chunk = 32 * 1024 * 1024
    client.upload_file(
        str(path), bucket, key,
        ExtraArgs={"ContentType": "video/mp4", "ContentDisposition": "inline", "CacheControl": "public, max-age=31536000, immutable"},
        Config=TransferConfig(multipart_threshold=chunk, multipart_chunksize=chunk, max_concurrency=2, use_threads=True),
    )
    remote = head_ok(client, bucket, key)
    if not remote or remote["bytes"] != size:
        raise IOError(f"RustFS size verification failed for {key}: local={size}, remote={remote}")
    return {"status": "uploaded_verified", **remote}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--status-jsonl", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--staging-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--crf", type=int, default=20)
    parser.add_argument("--endpoint", default="https://s3-hot-upload.liuzisen.com")
    parser.add_argument("--retries", type=int, default=10)
    args = parser.parse_args()
    if args.workers < 1:
        raise ValueError("workers must be positive")

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    bucket = str(manifest["bucket"])
    episodes = list(manifest["episodes"])
    client = make_client(args)
    client.head_bucket(Bucket=bucket)
    args.status_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.staging_root.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    counts: Counter[str] = Counter()

    def process(row: dict[str, Any]) -> dict[str, Any]:
        present = {view: head_ok(client, bucket, key) for view, key in row["object_keys"].items()}
        missing = [view for view, metadata in present.items() if metadata is None]
        result: dict[str, Any] = {
            "record_id": row["record_id"],
            "status": "already_complete" if not missing else "processing",
            "views": {view: ({"status": "already_present", **metadata} if metadata else None) for view, metadata in present.items()},
        }
        if not missing:
            return result
        with tempfile.TemporaryDirectory(prefix="panda_eval_", dir=args.staging_root) as directory:
            temporary = Path(directory)
            for view in missing:
                path = temporary / f"{view}.mp4"
                metadata = export_h5_camera_video(
                    h5_path=Path(row["h5_path"]), output_path=path,
                    camera_group=FRONT_GROUP if view == "front" else WRIST_GROUP,
                    synchronize_to_group=None if view == "front" else FRONT_GROUP,
                    crf=args.crf, preset="veryfast",
                )
                if int(metadata["frame_count"]) != int(row["total_frames"]):
                    raise ValueError(f"Frame count mismatch for {row['record_id']} {view}: {metadata['frame_count']} != {row['total_frames']}")
                result["views"][view] = {**upload(client, path, bucket, row["object_keys"][view]), "media": metadata}
        result["status"] = "complete"
        return result

    failures: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process, row): row for row in episodes}
        for completed, future in enumerate(as_completed(futures), start=1):
            row = futures[future]
            try:
                result = future.result()
                counts[result["status"]] += 1
            except Exception as error:
                result = {"record_id": row["record_id"], "status": "error", "error": repr(error)}
                counts["error"] += 1
                failures.append({"record_id": row["record_id"], "error": repr(error)})
            result["timestamp_utc"] = datetime.now(timezone.utc).isoformat()
            with lock:
                with args.status_jsonl.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(result, ensure_ascii=False) + "\n")
            print(f"[{completed}/{len(episodes)}] {result['status']} {row['record_id']}", flush=True)

    missing_after = []
    total_bytes = 0
    for row in episodes:
        for view, key in row["object_keys"].items():
            metadata = head_ok(client, bucket, key)
            if metadata is None:
                missing_after.append({"record_id": row["record_id"], "view": view, "key": key})
            else:
                total_bytes += int(metadata["bytes"])
    summary = {
        "schema_version": 1,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "episode_count": len(episodes),
        "expected_video_count": len(episodes) * 2,
        "verified_video_count": len(episodes) * 2 - len(missing_after),
        "verified_bytes": total_bytes,
        "processing_counts": dict(counts),
        "processing_failures": failures,
        "missing_after_verification": missing_after,
    }
    args.summary_output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if failures or missing_after:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
