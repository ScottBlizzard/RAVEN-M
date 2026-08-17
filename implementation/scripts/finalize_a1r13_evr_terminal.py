#!/usr/bin/env python3
"""Seal the terminal A1-R13 gate result without making model calls."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "implementation/src")]

from raven_m.official_qwen_mobile import a1r13_contract as contract  # noqa: E402


class FinalizationError(RuntimeError):
    pass


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise FinalizationError(f"unreadable_json:{path}") from exc
    if not isinstance(value, dict):
        raise FinalizationError(f"json_not_object:{path}")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise FinalizationError(code)


def finalize(suite_dir: Path, output: Path) -> dict[str, Any]:
    checkpoint_path = suite_dir / "checkpoint.json"
    signature_path = suite_dir / "run_signature.json"
    live_result_path = suite_dir / "a1r13_result.json"
    checkpoint = _load(checkpoint_path)
    signature = _load(signature_path)
    live_result = _load(live_result_path)

    _require(
        checkpoint.get("content_sha256") == contract.content_sha256(checkpoint),
        "checkpoint_content_hash",
    )
    _require(checkpoint.get("schema") == contract.CHECKPOINT_SCHEMA, "checkpoint_schema")
    _require(checkpoint.get("status") == "stopped_capability_gate_failure", "checkpoint_status")
    _require(checkpoint.get("mechanism_id") == contract.MECHANISM_ID, "checkpoint_mechanism")
    _require(checkpoint.get("experiment_id") == contract.EXPERIMENT_ID, "checkpoint_experiment")
    _require(checkpoint.get("prospective_arm") == "a1r13", "checkpoint_arm")
    summaries = list(checkpoint.get("valid_summaries") or [])
    entries = list(checkpoint.get("a1r13_valid_entries") or [])
    invalid = list(checkpoint.get("invalid_attempts") or [])
    _require(len(summaries) == len(entries) == 1, "terminal_cardinality")
    _require(not invalid, "unexpected_invalid_attempt")
    summary = summaries[0]
    entry = entries[0]
    _require(summary.get("task_name") == contract.CAPABILITY_GATE_TASKS[0], "task_identity")
    _require(summary.get("evaluator_reward") == 0.0, "reward_identity")
    _require(summary.get("success") is False, "success_identity")
    _require(summary.get("error") is None and not summary.get("lifecycle_errors"), "episode_error")
    _require(math.isfinite(float(summary.get("evaluator_reward"))), "reward_nonfinite")
    episode_id = str(summary.get("episode_id") or "")
    episode_path = suite_dir / "episodes" / episode_id / "episode.json"
    episode = _load(episode_path)
    _require(contract.file_sha256(episode_path) == entry.get("episode_json_sha256"), "episode_file_hash")
    _require(contract.canonical_sha256(episode) == entry.get("summary_sha256"), "episode_summary_hash")
    _require(contract.canonical_sha256(summary) == entry.get("summary_sha256"), "checkpoint_summary_hash")
    _require(entry.get("run_signature_sha256") == checkpoint.get("run_signature_sha256"), "entry_signature")
    _require(contract.canonical_sha256(signature) == checkpoint.get("run_signature_sha256"), "signature_hash")
    _require(signature.get("mechanism_id") == contract.MECHANISM_ID, "signature_mechanism")
    _require(signature.get("experiment_id") == contract.EXPERIMENT_ID, "signature_experiment")
    steps = list(summary.get("steps") or [])
    _require(len(steps) == int(summary.get("model_call_count") or -1) == 34, "call_count")
    _require(int(summary.get("executed_action_count") or -1) == 34, "executed_count")
    _require(
        all(
            int((((step.get("model_call") or {}).get("raven_meta") or {}).get("transport_attempts") or 0)) == 1
            and step.get("parse_error") is None
            and step.get("executed") is True
            for step in steps
        ),
        "step_transport_or_execution",
    )
    evidence = ((summary.get("memory_mechanism") or {}).get("evidence_register") or {})
    counters = evidence.get("counters") or {}
    _require(int(counters.get("activation_count") or 0) == 0, "evr_not_silent")
    _require(int(counters.get("render_count") or 0) == 0, "evr_rendered")
    _require(live_result.get("content_sha256") == contract.content_sha256(live_result), "live_result_hash")
    _require(live_result.get("status") == "TERMINAL_STOPPED_CAPABILITY_GATE_FAILURE", "live_result_status")
    _require(int((live_result.get("closure") or {}).get("not_run_by_protocol_count") or -1) == 18, "not_run_count")

    preflight = contract.validate_preflight_report(contract.PREFLIGHT_PATH)
    receipt_path = ROOT / "evidence/a1r13/A1R13_EVR_LIVE_RECEIPT.json"
    receipt = contract.validate_launch_receipt(receipt_path)
    _require(
        str((summary.get("run_metadata") or {}).get("live_server_receipt_sha256"))
        == contract.file_sha256(receipt_path),
        "episode_receipt_hash",
    )

    task_rows = list(live_result.get("tasks") or [])
    _require(len(task_rows) == 19, "result_task_count")
    _require(sum(row.get("execution_status") == "NOT_RUN_BY_PROTOCOL" for row in task_rows) == 18, "result_not_run_count")
    payload = {
        "schema": "a1r13_evr_terminal_evidence_v1",
        "status": "TERMINAL_VALID_SCIENTIFIC_FAILURE",
        "classification": "SILENT_PRESERVATION_FAILURE_UNATTRIBUTED",
        "claim_boundary": {
            "performance_gate_failed": True,
            "evr_causal_effect_observed": False,
            "evr_harm_inferred": False,
            "browser_target_evaluated": False,
            "same_seed_is_not_deterministic_replay": True,
        },
        "identity": {
            "suite_id": checkpoint.get("suite_id"),
            "mechanism_id": contract.MECHANISM_ID,
            "experiment_id": contract.EXPERIMENT_ID,
            "implementation_commit": preflight.get("implementation_commit"),
            "task_seed": contract.TASK_SEED,
            "generation_seed": contract.GENERATION_SEED,
        },
        "closure": {
            "generation_calls_during_finalization": 0,
            "valid_episode_count": 1,
            "invalid_attempt_count": 0,
            "not_run_by_protocol_count": 18,
            "checkpoint_file_sha256": contract.file_sha256(checkpoint_path),
            "checkpoint_content_sha256": checkpoint.get("content_sha256"),
            "run_signature_file_sha256": contract.file_sha256(signature_path),
            "run_signature_sha256": checkpoint.get("run_signature_sha256"),
            "live_result_file_sha256": contract.file_sha256(live_result_path),
            "live_result_content_sha256": live_result.get("content_sha256"),
            "episode_json_sha256": entry.get("episode_json_sha256"),
            "episode_summary_sha256": entry.get("summary_sha256"),
            "preflight_content_sha256": preflight.get("content_sha256"),
            "live_receipt_file_sha256": contract.file_sha256(receipt_path),
            "live_receipt_content_sha256": receipt.get("content_sha256"),
        },
        "outcome": {
            "task_name": summary.get("task_name"),
            "episode_id": episode_id,
            "reward": summary.get("evaluator_reward"),
            "success": summary.get("success"),
            "termination_reason": summary.get("termination_reason"),
            "model_calls": summary.get("model_call_count"),
            "executed_actions": summary.get("executed_action_count"),
            "evr_counters": counters,
        },
        "tasks": task_rows,
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "errors": [],
    }
    sealed = {**payload, "content_sha256": contract.content_sha256(payload)}
    _write(output, sealed)
    return sealed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite-dir", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evidence/a1r13/A1R13_EVR_TERMINAL_RESULT_2026-08-18.json",
    )
    args = parser.parse_args()
    result = finalize(args.suite_dir.resolve(), args.output.resolve())
    print(json.dumps({"status": result["status"], "output": str(args.output), "content_sha256": result["content_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
