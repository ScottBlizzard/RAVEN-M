#!/usr/bin/env python3
"""Seal the pre-frozen shuffled-content active control for A4-v2 paired gains."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _digest(value: Any) -> str:
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _load_self_hashed(path: Path, schema: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    body = {key: item for key, item in value.items() if key != "content_sha256"}
    if value.get("schema") != schema or value.get("content_sha256") != _digest(body):
        raise RuntimeError(f"invalid or drifted {schema}: {path}")
    return value


def build(primary_path: Path, suite: Path, bank_path: Path) -> dict[str, Any]:
    primary = _load_self_hashed(primary_path, "a4v2.formal_result.v1")
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    if (bank.get("ablation") or {}).get("identity") != "A4V2_SHUFFLED_INCOMPATIBLE_CONTENT_ACTIVE_CONTROL_V1":
        raise RuntimeError("wrong A4-v2 shuffled active-control bank")
    required = list(primary.get("ablation_required_tasks") or [])
    if not required:
        raise RuntimeError("primary result has no paired gain requiring active control")
    signature_path = suite / "run_signature.json"
    aggregate_path = suite / "aggregate.json"
    checkpoint_path = suite / "checkpoint.json"
    for path in (signature_path, aggregate_path, checkpoint_path):
        if not path.is_file():
            raise RuntimeError(f"active-control suite closure missing: {path}")
    signature = json.loads(signature_path.read_text(encoding="utf-8"))
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    checkpoint = _load_self_hashed(checkpoint_path, "a4v2.scored_checkpoint.v1")
    if (
        signature.get("experiment_id") != "A4V2_SHUFFLED_INCOMPATIBLE_CONTENT_ACTIVE_CONTROL_V1"
        or signature.get("method") != "a4v2_shuffled_incompatible_workflow_content_control_v1"
        or signature.get("a4v2_primary_result_sha256") != _sha(primary_path)
        or signature.get("a4v2_workflow_bank_sha256") != _sha(bank_path)
        or checkpoint.get("run_signature_sha256") != _digest(signature)
    ):
        raise RuntimeError("A4-v2 active-control identity drift")
    aggregate_rows = aggregate.get("per_task") or []
    observed = [str(row.get("task_name")) for row in aggregate_rows]
    primary_order = [str(row.get("task_name")) for row in primary.get("tasks") or []]
    expected = [name for name in primary_order if name in set(required)]
    if observed != expected or len(observed) != len(required):
        raise RuntimeError("A4-v2 active-control task order/closure drift")
    rows: list[dict[str, Any]] = []
    for aggregate_row in aggregate_rows:
        task = str(aggregate_row["task_name"])
        episode_id = str(aggregate_row["episode_id"])
        episode_path = suite / "episodes" / episode_id / "episode.json"
        if not episode_path.is_file():
            raise RuntimeError(f"active-control episode missing: {task}")
        episode = json.loads(episode_path.read_text(encoding="utf-8"))
        if episode.get("error") is not None or episode.get("lifecycle_errors"):
            raise RuntimeError(f"infrastructure-invalid active-control episode: {task}")
        success = episode.get("success") is True and episode.get("evaluator_reward") == 1.0
        rows.append(
            {
                "task_name": task,
                "episode_id": episode_id,
                "episode_sha256": _sha(episode_path),
                "reward": episode.get("evaluator_reward"),
                "success": success,
                "model_calls": int(episode.get("model_call_count") or 0),
                "executed_actions": int(episode.get("executed_action_count") or 0),
                "content_contribution_verdict": (
                    "GAIN_NOT_CONTENT_SPECIFIC_CONTROL_ALSO_SUCCEEDED"
                    if success
                    else "CONTROL_SUPPORTED_CONTENT_CONTRIBUTION_ABLATION_UNRESOLVED_BEYOND_SINGLE_PAIR"
                ),
            }
        )
    result: dict[str, Any] = {
        "schema": "a4v2.shuffled_active_control_result.v1",
        "experiment_id": "A4V2_SHUFFLED_INCOMPATIBLE_CONTENT_ACTIVE_CONTROL_V1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "COMPLETE",
        "held_out": False,
        "claim_boundary": "matched-content active control for observed A4-v2 paired gains only; single paired contrast is candidate evidence, not universal causality",
        "primary_result_sha256": _sha(primary_path),
        "shuffled_bank_sha256": _sha(bank_path),
        "suite": {
            "run_signature_sha256": _sha(signature_path),
            "aggregate_sha256": _sha(aggregate_path),
            "checkpoint_sha256": _sha(checkpoint_path),
        },
        "tasks": rows,
    }
    result["content_sha256"] = _digest(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary-result", type=Path, required=True)
    parser.add_argument("--suite-dir", type=Path, required=True)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evidence/a4v2/A4V2_SHUFFLED_ACTIVE_CONTROL_RESULT.json",
    )
    args = parser.parse_args()
    result = build(args.primary_result.resolve(), args.suite_dir.resolve(), args.bank.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": "complete", "output": str(args.output), "content_sha256": result["content_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
