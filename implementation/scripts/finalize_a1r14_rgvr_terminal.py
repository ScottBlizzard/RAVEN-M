#!/usr/bin/env python3
"""Seal the terminal A1-R14 target result without generation."""

from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "implementation/src")]
from raven_m.official_qwen_mobile import a1r14_contract as contract  # noqa: E402


class FinalizationError(RuntimeError):
    pass


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise FinalizationError(f"unreadable:{path}") from exc
    if not isinstance(value, dict):
        raise FinalizationError(f"not_object:{path}")
    return value


def _require(value: bool, code: str) -> None:
    if not value:
        raise FinalizationError(code)


def finalize(suite: Path, output: Path) -> dict[str, Any]:
    checkpoint_path = suite / "checkpoint.json"
    signature_path = suite / "run_signature.json"
    result_path = suite / "a1r14_result.json"
    checkpoint, signature, result = _load(checkpoint_path), _load(signature_path), _load(result_path)
    _require(checkpoint.get("content_sha256") == contract.content_sha256(checkpoint), "checkpoint_hash")
    _require(checkpoint.get("status") == "stopped_target_gate_failure", "checkpoint_status")
    _require(checkpoint.get("schema") == contract.CHECKPOINT_SCHEMA, "checkpoint_schema")
    _require(checkpoint.get("experiment_id") == contract.EXPERIMENT_ID, "experiment")
    summaries, entries = list(checkpoint.get("valid_summaries") or []), list(checkpoint.get("a1r14_valid_entries") or [])
    _require(len(summaries) == len(entries) == 1 and not checkpoint.get("invalid_attempts"), "cardinality")
    summary, entry = summaries[0], entries[0]
    _require(summary.get("task_name") == contract.TARGET_GATE_TASK, "target")
    _require(summary.get("evaluator_reward") == 0.0 and summary.get("success") is False, "outcome")
    _require(summary.get("error") is None and not summary.get("lifecycle_errors"), "episode_error")
    episode_path = suite / "episodes" / str(summary["episode_id"]) / "episode.json"
    episode = _load(episode_path)
    _require(contract.file_sha256(episode_path) == entry.get("episode_json_sha256"), "episode_file_hash")
    _require(contract.canonical_sha256(episode) == contract.canonical_sha256(summary) == entry.get("summary_sha256"), "summary_hash")
    _require(contract.canonical_sha256(signature) == checkpoint.get("run_signature_sha256"), "signature_hash")
    _require(all(int((((step.get("model_call") or {}).get("raven_meta") or {}).get("transport_attempts") or 0)) == 1 for step in summary.get("steps") or []), "transport")
    memory = summary.get("memory_mechanism") or {}
    counters = (memory.get("evidence_register") or {}).get("counters") or {}
    response = (memory.get("response_grounding") or {}).get("counters") or {}
    _require(int(counters.get("activation_count") or 0) == 1, "activation")
    _require(int(counters.get("append_count") or 0) == 1, "append")
    _require(int(counters.get("render_count") or 0) == 0, "render")
    _require(int(response.get("append_count") or 0) == 1, "response_append")
    _require(result.get("content_sha256") == contract.content_sha256(result), "result_hash")
    _require(result.get("status") == "TERMINAL_STOPPED_TARGET_GATE_FAILURE", "result_status")
    preflight = contract.validate_preflight_report()
    receipt_path = ROOT / "evidence/a1r14/A1R14_RGVR_LIVE_RECEIPT.json"
    receipt = contract.validate_launch_receipt(receipt_path)
    payload = {
        "schema": "a1r14_rgvr_terminal_evidence_v1",
        "status": "TERMINAL_VALID_SCIENTIFIC_FAILURE",
        "classification": "PARTIAL_EXPOSURE_OBSERVATION_REGEX_COVERAGE_REFUTED",
        "identity": {"suite_id": checkpoint.get("suite_id"), "mechanism_id": contract.MECHANISM_ID, "experiment_id": contract.EXPERIMENT_ID, "implementation_commit": preflight.get("implementation_commit")},
        "claim_boundary": {"one_value_retained": True, "nonempty_value_read_observed": False, "memory_effect_evaluated": False, "same_identity_rerun_forbidden": True},
        "closure": {"generation_calls_during_finalization": 0, "valid_episode_count": 1, "invalid_attempt_count": 0, "not_run_by_protocol_count": 18, "checkpoint_file_sha256": contract.file_sha256(checkpoint_path), "checkpoint_content_sha256": checkpoint.get("content_sha256"), "run_signature_file_sha256": contract.file_sha256(signature_path), "episode_json_sha256": entry.get("episode_json_sha256"), "result_file_sha256": contract.file_sha256(result_path), "result_content_sha256": result.get("content_sha256"), "preflight_content_sha256": preflight.get("content_sha256"), "receipt_file_sha256": contract.file_sha256(receipt_path), "receipt_content_sha256": receipt.get("content_sha256")},
        "outcome": {"task_name": summary.get("task_name"), "episode_id": summary.get("episode_id"), "reward": summary.get("evaluator_reward"), "termination_reason": summary.get("termination_reason"), "model_calls": summary.get("model_call_count"), "executed_actions": summary.get("executed_action_count"), "evidence_counters": counters, "response_counters": response, "retained_values": [row.get("value") for row in (memory.get("evidence_register") or {}).get("values") or []]},
        "tasks": result.get("tasks"), "sealed_at": datetime.now(timezone.utc).isoformat(), "errors": [],
    }
    sealed = {**payload, "content_sha256": contract.content_sha256(payload)}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(sealed, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sealed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/a1r14/A1R14_RGVR_TERMINAL_RESULT_2026-08-18.json")
    args = parser.parse_args()
    result = finalize(args.suite_dir.resolve(), args.output.resolve())
    print(json.dumps({"status": result["status"], "content_sha256": result["content_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
