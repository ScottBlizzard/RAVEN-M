#!/usr/bin/env python3
"""Materialize the seven frozen offline-AWM prompts from a donor source lock."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.official_qwen_mobile.a4v2_induction import build_induction_packet  # noqa: E402


REQUIRED_ROUTES = {
    "browser_open_local_task",
    "expense_delete",
    "retro_create_playlist",
    "calendar_add_event",
    "opentracks_retrieve_duration",
    "broccoli_delete_recipe",
    "osmand_add_location_marker",
}


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-lock", type=Path, required=True)
    parser.add_argument(
        "--hard-manifest",
        type=Path,
        default=REPOSITORY_ROOT / "implementation/configs/androidworld_hard_v2_instances.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPOSITORY_ROOT / "evidence/a4v2/induction_packets",
    )
    args = parser.parse_args()
    lock = json.loads(args.source_lock.read_text(encoding="utf-8"))
    if lock.get("schema") != "a4v2.donor_source_lock.v1":
        raise RuntimeError("wrong donor source-lock schema")
    groups = lock.get("route_groups") or []
    if {str(item.get("route_id")) for item in groups} != REQUIRED_ROUTES:
        raise RuntimeError("donor source lock must contain the exact seven routes")
    index_rows = []
    for group in groups:
        packet = build_induction_packet(
            route_id=str(group["route_id"]),
            route=group["route"],
            donors=group["donors"],
            repository_root=REPOSITORY_ROOT,
            scored_hard_manifest=args.hard_manifest,
        )
        path = args.output_dir / f"{group['route_id']}.json"
        _write(path, packet)
        index_rows.append(
            {
                "route_id": group["route_id"],
                "packet_path": str(path.relative_to(REPOSITORY_ROOT)).replace("\\", "/"),
                "packet_sha256": _sha(path),
                "prompt_sha256": packet["prompt_sha256"],
            }
        )
    index = {
        "schema": "a4v2.awm_induction_index.v1",
        "generation_calls": 0,
        "ready_for_induction": True,
        "source_lock_path": str(args.source_lock.resolve()),
        "source_lock_sha256": _sha(args.source_lock),
        "packets": index_rows,
    }
    _write(args.output_dir / "index.json", index)
    print(json.dumps({"status": "ready", "packet_count": len(index_rows), "index": str(args.output_dir / "index.json")}, indent=2))


if __name__ == "__main__":
    main()

