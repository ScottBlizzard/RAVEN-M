#!/usr/bin/env python3
"""Build an audited 19-task A7 control from transparent continuation suites."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _json_sha(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _checkpoint(suite: Path) -> dict[str, Any]:
    path = suite / "checkpoint.json"
    if not path.is_file():
        raise RuntimeError(f"missing checkpoint: {path}")
    return _load(path)


def _valid(summary: dict[str, Any]) -> bool:
    return (
        summary.get("evaluator_reward") is not None
        and summary.get("error") is None
        and not summary.get("lifecycle_errors")
        and all(
            int(
                ((step.get("model_call") or {}).get("raven_meta") or {}).get(
                    "transport_attempts"
                )
                or 0
            )
            == 1
            for step in summary.get("steps") or []
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--parent-suite", type=Path, required=True)
    parser.add_argument("--gate-suite", type=Path, required=True)
    parser.add_argument("--sports-suite", type=Path, required=True)
    parser.add_argument("--remaining-suite", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    suites = {
        "parent_original_7": args.parent_suite.resolve(),
        "gated_retro_calendar": args.gate_suite.resolve(),
        "post_gate_sports_diagnostic": args.sports_suite.resolve(),
        "post_gate_remaining9_diagnostic": args.remaining_suite.resolve(),
    }
    manifest = _load(args.manifest.resolve())
    manifest_items = manifest.get("instances") if isinstance(manifest, dict) else manifest
    if not isinstance(manifest_items, list):
        raise RuntimeError("manifest instances are missing")
    expected = [
        (str(item["task_class"]), int(item["task_seed"]))
        for item in manifest_items
        if int(item["task_seed"]) == 20260806
    ]
    if len(expected) != 19 or len(set(expected)) != 19:
        raise RuntimeError("manifest does not contain 19 unique seed-20260806 tasks")

    checkpoints = {name: _checkpoint(path) for name, path in suites.items()}
    selected: list[tuple[str, dict[str, Any]]] = []
    selected.extend(
        ("parent_original_7", item)
        for item in checkpoints["parent_original_7"].get("valid_summaries") or []
    )
    selected.extend(
        ("gated_retro_calendar", item)
        for item in checkpoints["gated_retro_calendar"].get("valid_summaries") or []
        if str(item.get("task_name"))
        in {"RetroSavePlaylist", "SimpleCalendarAddOneEvent"}
    )
    selected.extend(
        ("post_gate_sports_diagnostic", item)
        for item in checkpoints["post_gate_sports_diagnostic"].get("valid_summaries")
        or []
    )
    selected.extend(
        ("post_gate_remaining9_diagnostic", item)
        for item in checkpoints["post_gate_remaining9_diagnostic"].get(
            "valid_summaries"
        )
        or []
    )

    by_key: dict[tuple[str, int], tuple[str, dict[str, Any]]] = {}
    rows: list[dict[str, Any]] = []
    for origin, summary in selected:
        key = (str(summary.get("task_name")), int(summary.get("seed", -1)))
        if key in by_key:
            raise RuntimeError(f"duplicate selected task: {key}")
        if not _valid(summary):
            raise RuntimeError(f"infrastructure-invalid selected task: {key}")
        suite = suites[origin]
        episode_path = suite / "episodes" / str(summary["episode_id"]) / "episode.json"
        if not episode_path.is_file():
            raise RuntimeError(f"missing episode JSON: {episode_path}")
        episode = _load(episode_path)
        if _json_sha(episode) != _json_sha(summary):
            raise RuntimeError(f"episode/checkpoint mismatch: {key}")
        by_key[key] = (origin, summary)

    if set(by_key) != set(expected) or len(by_key) != 19:
        missing = [list(key) for key in expected if key not in by_key]
        extra = [list(key) for key in by_key if key not in set(expected)]
        raise RuntimeError(f"19-task closure failed; missing={missing}, extra={extra}")

    for task_name, seed in expected:
        origin, summary = by_key[(task_name, seed)]
        suite = suites[origin]
        episode_path = suite / "episodes" / str(summary["episode_id"]) / "episode.json"
        rows.append(
            {
                "task_name": task_name,
                "seed": seed,
                "origin": origin,
                "suite_id": suite.name,
                "episode_id": summary["episode_id"],
                "episode_json": str(episode_path),
                "episode_json_sha256": _file_sha(episode_path),
                "reward": float(summary["evaluator_reward"]),
                "success": bool(summary.get("success")),
                "step_count": len(summary.get("steps") or []),
                "transport_attempt_max": max(
                    (
                        int(
                            ((step.get("model_call") or {}).get("raven_meta") or {}).get(
                                "transport_attempts"
                            )
                            or 0
                        )
                        for step in summary.get("steps") or []
                    ),
                    default=0,
                ),
            }
        )

    preservation_names = {
        "ExpenseDeleteMultiple2",
        "RetroSavePlaylist",
        "SimpleCalendarAddOneEvent",
        "SportsTrackerTotalDurationForCategoryThisWeek",
    }
    preservation_rows = [row for row in rows if row["task_name"] in preservation_names]
    source_evidence = {}
    for name, suite in suites.items():
        source_evidence[name] = {
            "suite_dir": str(suite),
            "run_signature_sha256": _file_sha(suite / "run_signature.json"),
            "checkpoint_sha256": _file_sha(suite / "checkpoint.json"),
            "checkpoint_status": checkpoints[name].get("status"),
        }
        aggregate_path = suite / "aggregate.json"
        if aggregate_path.is_file():
            source_evidence[name]["aggregate_sha256"] = _file_sha(aggregate_path)

    result = {
        "schema": "a7_transparent_19_task_control_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete_19_of_19_infrastructure_valid",
        "experiment_id": "A7_GOAL_ITEM_LEDGER_TRANSPARENT_STITCHED_19_TASK_CONTROL_S20260806_V1",
        "mechanism_id": "a7_deterministic_active_goal_item_status_ledger_v1",
        "claim_boundary": (
            "stitched_from_original_7_plus_post_7_protocol_amendments; "
            "not_a_pristine_single_preregistered_suite; Calendar gate failure retained"
        ),
        "manifest_sha256": _file_sha(args.manifest.resolve()),
        "ordered_expected_keys_sha256": _json_sha(expected),
        "valid_episode_count": len(rows),
        "invalid_selected_episode_count": 0,
        "success_count": sum(int(row["success"]) for row in rows),
        "success_rate": sum(int(row["success"]) for row in rows) / len(rows),
        "reward_sum": sum(float(row["reward"]) for row in rows),
        "transport_attempt_max": max(row["transport_attempt_max"] for row in rows),
        "preservation_gate_retrospective": {
            "status": "failed_3_of_4",
            "success_count": sum(int(row["success"]) for row in preservation_rows),
            "required_count": 4,
            "rows": preservation_rows,
        },
        "source_evidence": source_evidence,
        "per_task": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
