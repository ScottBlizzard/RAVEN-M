#!/usr/bin/env python3
"""CPU-only deep seal for the terminal A1-R15 target gate."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "implementation/src")]
from raven_m.official_qwen_mobile import a1r15_contract as contract  # noqa: E402


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
    result_path = suite / "a1r15_result.json"
    checkpoint = _load(checkpoint_path)
    signature = _load(signature_path)
    result = _load(result_path)
    _require(checkpoint.get("content_sha256") == contract.content_sha256(checkpoint), "checkpoint_hash")
    _require(checkpoint.get("status") == "stopped_target_gate_failure", "checkpoint_status")
    _require(checkpoint.get("schema") == contract.CHECKPOINT_SCHEMA, "checkpoint_schema")
    _require(checkpoint.get("experiment_id") == contract.EXPERIMENT_ID, "experiment")
    _require(checkpoint.get("mechanism_id") == contract.MECHANISM_ID, "mechanism")
    summaries = list(checkpoint.get("valid_summaries") or [])
    entries = list(checkpoint.get("a1r15_valid_entries") or [])
    _require(len(summaries) == len(entries) == 1 and not checkpoint.get("invalid_attempts"), "cardinality")
    summary, entry = summaries[0], entries[0]
    _require(summary.get("task_name") == contract.TARGET_GATE_TASK, "target")
    _require(summary.get("evaluator_reward") == 1.0 and summary.get("success") is True, "outcome")
    _require(summary.get("error") is None and not summary.get("lifecycle_errors"), "episode_error")
    _require(int(summary.get("model_call_count") or 0) == 21, "model_calls")
    _require(int(summary.get("executed_action_count") or 0) == 20, "executed_actions")
    episode_path = suite / "episodes" / str(summary["episode_id"]) / "episode.json"
    episode_dir = episode_path.parent
    episode = _load(episode_path)
    _require(contract.file_sha256(episode_path) == entry.get("episode_json_sha256"), "episode_file_hash")
    _require(contract.canonical_sha256(episode) == contract.canonical_sha256(summary) == entry.get("summary_sha256"), "summary_hash")
    _require(contract.canonical_sha256(signature) == checkpoint.get("run_signature_sha256"), "signature_hash")
    steps = list(summary.get("steps") or [])
    _require(len(steps) == 21, "step_count")
    _require(all(int((((step.get("model_call") or {}).get("raven_meta") or {}).get("transport_attempts") or 0)) == 1 for step in steps), "transport")
    _require(all((step.get("model_call") or {}).get("usage") is not None for step in steps), "usage")
    memory = summary.get("memory_mechanism") or {}
    register = memory.get("evidence_register") or {}
    counters = register.get("counters") or {}
    response = (memory.get("response_grounding") or {}).get("counters") or {}
    retained = [row.get("value") for row in register.get("values") or []]
    rendered_reads = [row for row in register.get("read_events") or [] if row.get("rendered") is True]
    _require(int(counters.get("activation_count") or 0) == 1, "activation")
    _require(int(counters.get("append_count") or 0) == 2, "append")
    _require(int(counters.get("render_count") or 0) == 0, "render")
    _require(int(response.get("append_count") or 0) == 2, "response_append")
    _require(retained == ["8", "2"] and rendered_reads == [], "retained_values")
    _require(result.get("content_sha256") == contract.content_sha256(result), "result_hash")
    _require(result.get("status") == "TERMINAL_STOPPED_TARGET_GATE_FAILURE", "result_status")
    _require(len(result.get("tasks") or []) == 19, "result_tasks")
    _require(sum(row.get("execution_status") == "NOT_RUN_BY_PROTOCOL" for row in result.get("tasks") or []) == 18, "not_run_count")
    preflight = contract.validate_preflight_report()
    source_freeze = contract.validate_source_freeze()
    receipt_path = ROOT / "evidence/a1r15/A1R15_EOVR_LIVE_RECEIPT.json"
    receipt = contract.validate_launch_receipt(receipt_path)
    events_path = episode_dir / "events.jsonl"
    _require(events_path.is_file(), "events_missing")
    png_paths = sorted(episode_dir.glob("*.png"))
    json_paths = sorted(path for path in episode_dir.glob("*.json") if path.name != "episode.json")
    payload = {
        "schema": "a1r15_eovr_terminal_evidence_v1",
        "status": "TERMINAL_PROTOCOL_STOP_TARGET_SUCCESS_NO_EVR_READ",
        "classification": "TARGET_SUCCESS_WITHOUT_MATURE_EVR_READ_UNATTRIBUTED",
        "identity": {
            "suite_id": checkpoint.get("suite_id"), "mechanism_id": contract.MECHANISM_ID,
            "experiment_id": contract.EXPERIMENT_ID, "implementation_commit": preflight.get("implementation_commit"),
        },
        "verdicts": {
            "target_performance": "SUCCESS", "target_mechanism_gate": "FAIL_NO_COMPLETE_FIVE_VALUE_READ",
            "accuracy": "NOT_EVALUABLE_PARTIAL", "mechanism": "NOT_OBSERVED_NO_EVR_READ",
            "continuation": "STOP_AND_WAIT_FOR_USER_DECISION",
        },
        "claim_boundary": {
            "browser_success_observed": True, "evr_activated": True, "complete_five_values_retained": False,
            "nonempty_value_read_observed": False, "success_attributed_to_evr": False,
            "remaining_suite_released": False, "pure_memory_parser_line_closed": True,
            "same_identity_rerun_forbidden": True,
        },
        "closure": {
            "generation_calls_during_finalization": 0, "valid_episode_count": 1, "invalid_attempt_count": 0,
            "not_run_by_protocol_count": 18, "checkpoint_file_sha256": contract.file_sha256(checkpoint_path),
            "checkpoint_content_sha256": checkpoint.get("content_sha256"),
            "run_signature_file_sha256": contract.file_sha256(signature_path),
            "run_signature_content_sha256": checkpoint.get("run_signature_sha256"),
            "episode_json_sha256": entry.get("episode_json_sha256"), "events_jsonl_sha256": contract.file_sha256(events_path),
            "screenshot_png_count": len(png_paths), "ui_and_step_json_count": len(json_paths),
            "result_file_sha256": contract.file_sha256(result_path), "result_content_sha256": result.get("content_sha256"),
            "source_freeze_file_sha256": contract.file_sha256(contract.SOURCE_FREEZE_PATH),
            "source_freeze_content_sha256": source_freeze.get("content_sha256"),
            "preflight_file_sha256": contract.file_sha256(contract.PREFLIGHT_PATH),
            "preflight_content_sha256": preflight.get("content_sha256"),
            "receipt_file_sha256": contract.file_sha256(receipt_path), "receipt_content_sha256": receipt.get("content_sha256"),
        },
        "outcome": {
            "task_name": summary.get("task_name"), "episode_id": summary.get("episode_id"),
            "reward": summary.get("evaluator_reward"), "termination_reason": summary.get("termination_reason"),
            "model_calls": summary.get("model_call_count"), "executed_actions": summary.get("executed_action_count"),
            "evidence_counters": counters, "response_counters": response, "retained_values": retained,
            "rendered_value_read_count": len(rendered_reads),
        },
        "tasks": result.get("tasks"), "sealed_at": datetime.now(timezone.utc).isoformat(), "errors": [],
    }
    sealed = {**payload, "content_sha256": contract.content_sha256(payload)}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(sealed, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sealed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/a1r15/A1R15_EOVR_TERMINAL_RESULT_2026-08-18.json")
    args = parser.parse_args()
    result = finalize(args.suite_dir.resolve(), args.output.resolve())
    print(json.dumps({"status": result["status"], "classification": result["classification"], "content_sha256": result["content_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
