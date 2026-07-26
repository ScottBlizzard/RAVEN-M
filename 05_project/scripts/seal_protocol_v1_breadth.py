"""Seal the completed protocol-v1 breadth artifacts without modifying them."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
SUITE_DIR = REPOSITORY_ROOT / "runs/frozen_hard_v1/hard_v1_breadth"
SCHEDULE_PATH = PROJECT_ROOT / "configs/experiments/hard_schedule_v1.json"
SEAL_PATH = (
    REPOSITORY_ROOT
    / "checksums/protocol_v1_breadth_seal_20260726.json"
)
STATUS_PATH = PROJECT_ROOT / "metadata/protocol_v1_halt_status.json"
INFORMATION_RETRIEVAL_TASKS = {
    "SportsTrackerActivitiesOnDate",
    "SportsTrackerTotalDistanceForCategoryOverInterval",
    "SportsTrackerTotalDurationForCategoryThisWeek",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def file_record(path: Path, *, role: str) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(REPOSITORY_ROOT).as_posix(),
        "role": role,
        "bytes": len(data),
        "sha256": sha256(data).hexdigest(),
    }


def verify_existing_seal() -> dict[str, Any]:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    failures = []
    for record in seal["files"]:
        path = REPOSITORY_ROOT / record["path"]
        if not path.is_file():
            failures.append({"path": record["path"], "error": "missing"})
            continue
        data = path.read_bytes()
        if len(data) != record["bytes"]:
            failures.append(
                {
                    "path": record["path"],
                    "error": "byte_count_mismatch",
                }
            )
        digest = sha256(data).hexdigest()
        if digest != record["sha256"]:
            failures.append(
                {"path": record["path"], "error": "sha256_mismatch"}
            )
    status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    seal_digest = sha256(SEAL_PATH.read_bytes()).hexdigest()
    if status["seal_manifest_sha256"] != seal_digest:
        failures.append(
            {
                "path": STATUS_PATH.relative_to(REPOSITORY_ROOT).as_posix(),
                "error": "seal_manifest_sha256_mismatch",
            }
        )
    return {
        "schema_version": "protocol_v1_seal_verification.v1",
        "seal_path": SEAL_PATH.relative_to(REPOSITORY_ROOT).as_posix(),
        "file_count": len(seal["files"]),
        "failure_count": len(failures),
        "failures": failures,
        "passed": not failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify the existing seal without rewriting any artifact.",
    )
    args = parser.parse_args()
    if args.verify:
        result = verify_existing_seal()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["passed"] else 1

    summary_path = SUITE_DIR / "suite_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if (
        summary.get("suite_id") != "hard_v1_breadth"
        or summary.get("finished") is not True
        or summary.get("expected_episode_count") != 95
        or summary.get("completed_episode_count") != 95
        or summary.get("pairing_error_count") != 0
        or summary.get("audit_error_count") != 0
    ):
        raise RuntimeError("Protocol-v1 breadth is not sealable.")

    scored_paths = sorted(
        (SUITE_DIR / "episodes").glob("*/scored_result.json")
    )
    episode_paths = sorted(
        (SUITE_DIR / "episodes").glob("*/attempt_*/episode.json")
    )
    if len(scored_paths) != 95:
        raise RuntimeError("Expected exactly 95 scored results.")
    scored_episode_ids = {
        json.loads(path.read_text(encoding="utf-8"))["episode_id"]
        for path in scored_paths
    }
    selected_episode_paths = []
    for path in episode_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("episode_id") in scored_episode_ids:
            selected_episode_paths.append(path)
    if len(selected_episode_paths) != 95:
        raise RuntimeError("Expected exactly 95 scored raw episodes.")

    breadth_affected = sorted(
        (
            {
                "episode_id": item["episode_id"],
                "pair_id": item["pair_id"],
                "sequence": item["sequence"],
                "task_class": item["task_class"],
                "variant": item["variant"],
            }
            for item in summary["results"]
            if item["task_class"] in INFORMATION_RETRIEVAL_TASKS
        ),
        key=lambda item: item["sequence"],
    )
    if len(breadth_affected) != 15:
        raise RuntimeError("Expected 15 affected breadth cells.")

    schedule = json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))
    schedule_affected = sorted(
        (
            record
            for record in schedule["records"]
            if record["task_class"] in INFORMATION_RETRIEVAL_TASKS
        ),
        key=lambda item: (item["phase"], item["sequence"]),
    )
    if len(schedule_affected) != 36:
        raise RuntimeError("Expected 36 affected scheduled cells.")

    records = [
        file_record(summary_path, role="suite_summary"),
        file_record(
            SUITE_DIR / "schedule.snapshot.json",
            role="schedule_snapshot",
        ),
        *(
            file_record(path, role="scored_result")
            for path in scored_paths
        ),
        *(
            file_record(path, role="scored_raw_episode")
            for path in selected_episode_paths
        ),
        *(
            file_record(path, role="protocol_amendment_manifest")
            for path in sorted(
                (PROJECT_ROOT / "metadata").glob(
                    "protocol_amendment_*.json"
                )
            )
        ),
    ]
    path_keys = [record["path"] for record in records]
    if len(path_keys) != len(set(path_keys)):
        raise RuntimeError("Duplicate seal manifest path.")

    seal = {
        "schema_version": "protocol_v1_breadth_seal.v1",
        "created_at_utc": utc_now(),
        "suite_id": "hard_v1_breadth",
        "scientific_status": "diagnostic_only",
        "later_phases_halted": True,
        "halt_reason": (
            "task_interface_gap_and_supported_task_floor_effect"
        ),
        "scored_result_count": len(scored_paths),
        "scored_raw_episode_count": len(selected_episode_paths),
        "breadth_answer_incompatible_cell_count": len(breadth_affected),
        "full_schedule_answer_incompatible_cell_count": len(
            schedule_affected
        ),
        "breadth_answer_incompatible_cells": breadth_affected,
        "full_schedule_answer_incompatible_cells": schedule_affected,
        "files": records,
    }
    write_json(SEAL_PATH, seal)
    status = {
        "schema_version": "protocol_status.v1",
        "updated_at_utc": seal["created_at_utc"],
        "protocol": "androidworld_hard_protocol_v1",
        "breadth_complete": True,
        "breadth_episode_count": 95,
        "later_phases_halted": True,
        "scientific_status": "diagnostic_only",
        "halt_reason": seal["halt_reason"],
        "semantic_resumption_permitted": False,
        "replacement_protocol": "androidworld_protocol_v2_exploratory",
        "seal_manifest": SEAL_PATH.relative_to(
            REPOSITORY_ROOT
        ).as_posix(),
        "seal_manifest_sha256": sha256(SEAL_PATH.read_bytes()).hexdigest(),
    }
    write_json(STATUS_PATH, status)
    print(
        json.dumps(
            {
                "seal": SEAL_PATH.as_posix(),
                "status": STATUS_PATH.as_posix(),
                "files": len(records),
                "breadth_affected": len(breadth_affected),
                "schedule_affected": len(schedule_affected),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
