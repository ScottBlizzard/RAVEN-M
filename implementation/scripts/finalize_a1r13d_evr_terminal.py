#!/usr/bin/env python3
"""Seal the A1-R13D target-first terminal result without model calls."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "implementation/src")]
from raven_m.official_qwen_mobile import a1r13d_contract as contract  # noqa: E402


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


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise FinalizationError(code)


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def finalize(suite_dir: Path, output: Path) -> dict[str, Any]:
    checkpoint_path = suite_dir / "checkpoint.json"
    signature_path = suite_dir / "run_signature.json"
    result_path = suite_dir / "a1r13d_result.json"
    checkpoint = _load(checkpoint_path)
    signature = _load(signature_path)
    result = _load(result_path)
    _require(checkpoint.get("content_sha256") == contract.content_sha256(checkpoint), "checkpoint_hash")
    _require(checkpoint.get("schema") == contract.CHECKPOINT_SCHEMA, "checkpoint_schema")
    _require(checkpoint.get("status") == "stopped_target_gate_failure", "checkpoint_status")
    _require(checkpoint.get("experiment_id") == contract.EXPERIMENT_ID, "experiment_id")
    _require(checkpoint.get("mechanism_id") == contract.MECHANISM_ID, "mechanism_id")
    summaries = list(checkpoint.get("valid_summaries") or [])
    entries = list(checkpoint.get("a1r13d_valid_entries") or [])
    _require(len(summaries) == len(entries) == 1, "episode_cardinality")
    _require(not checkpoint.get("invalid_attempts"), "invalid_attempts")
    summary, entry = summaries[0], entries[0]
    _require(summary.get("task_name") == contract.TARGET_GATE_TASK, "target_task")
    _require(summary.get("evaluator_reward") == 0.0 and summary.get("success") is False, "target_outcome")
    _require(summary.get("error") is None and not summary.get("lifecycle_errors"), "episode_error")
    episode_id = str(summary.get("episode_id") or "")
    episode_path = suite_dir / "episodes" / episode_id / "episode.json"
    episode = _load(episode_path)
    _require(contract.file_sha256(episode_path) == entry.get("episode_json_sha256"), "episode_file_hash")
    _require(contract.canonical_sha256(episode) == entry.get("summary_sha256"), "episode_summary_hash")
    _require(contract.canonical_sha256(summary) == entry.get("summary_sha256"), "checkpoint_summary_hash")
    _require(contract.canonical_sha256(signature) == checkpoint.get("run_signature_sha256"), "signature_hash")
    steps = list(summary.get("steps") or [])
    _require(len(steps) == int(summary.get("model_call_count") or -1) == 22, "model_call_count")
    _require(int(summary.get("executed_action_count") or -1) == 22, "executed_action_count")
    _require(all(int((((row.get("model_call") or {}).get("raven_meta") or {}).get("transport_attempts") or 0)) == 1 for row in steps), "single_transport")
    evidence = ((summary.get("memory_mechanism") or {}).get("evidence_register") or {})
    counters = evidence.get("counters") or {}
    _require(int(counters.get("activation_count") or 0) == 0, "unexpected_activation")
    _require(int(counters.get("render_count") or 0) == 0, "unexpected_render")
    _require(result.get("content_sha256") == contract.content_sha256(result), "result_hash")
    _require(result.get("status") == "TERMINAL_STOPPED_TARGET_GATE_FAILURE", "result_status")
    _require(sum(row.get("execution_status") == "NOT_RUN_BY_PROTOCOL" for row in result.get("tasks") or []) == 18, "not_run_count")
    preflight = contract.validate_preflight_report()
    receipt_path = ROOT / "evidence/a1r13d/A1R13D_EVR_LIVE_RECEIPT.json"
    receipt = contract.validate_launch_receipt(receipt_path)
    _require((summary.get("run_metadata") or {}).get("live_server_receipt_sha256") == contract.file_sha256(receipt_path), "receipt_hash")
    payload = {
        "schema": "a1r13d_evr_terminal_evidence_v1",
        "status": "TERMINAL_VALID_SCIENTIFIC_FAILURE",
        "classification": "TARGET_NO_EXPOSURE_TRIGGER_CONTRACT_REFUTED",
        "identity": {
            "suite_id": checkpoint.get("suite_id"),
            "mechanism_id": contract.MECHANISM_ID,
            "experiment_id": contract.EXPERIMENT_ID,
            "implementation_commit": preflight.get("implementation_commit"),
            "task_seed": contract.TASK_SEED,
            "generation_seed": contract.GENERATION_SEED,
        },
        "claim_boundary": {
            "evr_activation_observed": False,
            "evr_effect_evaluated": False,
            "model_response_contained_five_explicit_values": True,
            "action_summary_channel_was_insufficient": True,
            "same_identity_rerun_forbidden": True,
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
            "result_file_sha256": contract.file_sha256(result_path),
            "result_content_sha256": result.get("content_sha256"),
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
            "termination_reason": summary.get("termination_reason"),
            "model_calls": summary.get("model_call_count"),
            "executed_actions": summary.get("executed_action_count"),
            "evr_counters": counters,
        },
        "tasks": result.get("tasks"),
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "errors": [],
    }
    sealed = {**payload, "content_sha256": contract.content_sha256(payload)}
    _write(output, sealed)
    return sealed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/a1r13d/A1R13D_EVR_TERMINAL_RESULT_2026-08-18.json")
    args = parser.parse_args()
    result = finalize(args.suite_dir.resolve(), args.output.resolve())
    print(json.dumps({"status": result["status"], "content_sha256": result["content_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
