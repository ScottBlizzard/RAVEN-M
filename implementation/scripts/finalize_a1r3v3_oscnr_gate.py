#!/usr/bin/env python3
"""Fail-closed, zero-generation finalizer for a terminal A1-R3-v3 gate loss."""

from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))

from raven_m.official_qwen_mobile import a1r3v3_contract as contract  # noqa: E402


POINTER_SCHEMA = "a1r3v3_oscnr_checkpoint_pointer_v1"
TERMINAL_STATUS = "stopped_capability_gate_failure"
DEFAULT_RECEIPT = ROOT / "evidence/a1r3_v3/A1R3V3_OSCNR_LIVE_RECEIPT.json"
DEFAULT_OUTPUT = ROOT / "evidence/a1r3_v3/A1R3V3_OSCNR_PRIMARY_GATE_RESULT_2026-08-15.json"


class FinalizationError(RuntimeError):
    """The frozen evidence closure is incomplete or has drifted."""


def _fail(code: str) -> None:
    raise FinalizationError(f"A1-R3-v3 terminal finalization failed: {code}")


def _require(condition: bool, code: str) -> None:
    if not condition:
        _fail(code)


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(raw).hexdigest()


def content_sha256(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("content_sha256", None)
    return canonical_sha256(payload)


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FinalizationError(
            f"A1-R3-v3 terminal finalization failed: {code}"
        ) from exc
    if not isinstance(value, dict):
        _fail(code)
    return value


def _safe_child(root: Path, relative: str, code: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        _fail(code)
    return candidate


def _validate_checkpoint_document(
    checkpoint: dict[str, Any], *, ordinal: int, suite_id: str, signature_sha: str
) -> None:
    expected = {
        "schema": contract.CHECKPOINT_SCHEMA,
        "prospective_arm": "a1r3v3",
        "mechanism_id": contract.MECHANISM_ID,
        "experiment_id": contract.EXPERIMENT_ID,
        "suite_id": suite_id,
        "checkpoint_ordinal": ordinal,
        "run_signature_sha256": signature_sha,
    }
    for key, value in expected.items():
        _require(checkpoint.get(key) == value, f"checkpoint_{ordinal}_{key}")
    _require(
        checkpoint.get("content_sha256") == content_sha256(checkpoint),
        f"checkpoint_{ordinal}_content_hash",
    )


def validate_checkpoint_chain(
    suite_dir: Path, signature_sha: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    pointer_path = suite_dir / "checkpoint.json"
    pointer = _load_json(pointer_path, "checkpoint_pointer_unreadable")
    _require(pointer.get("schema") == POINTER_SCHEMA, "checkpoint_pointer_schema")
    latest_rel = str(pointer.get("latest_checkpoint") or "")
    latest_path = _safe_child(suite_dir, latest_rel, "checkpoint_pointer_path")
    _require(latest_path.is_file(), "terminal_checkpoint_missing")
    _require(
        file_sha256(latest_path) == pointer.get("latest_checkpoint_file_sha256"),
        "checkpoint_pointer_file_hash",
    )

    checkpoint_dir = suite_dir / "checkpoints"
    files = sorted(checkpoint_dir.glob("A1R3V3_OSCNR_CHECKPOINT_*.json"))
    _require(len(files) == 2, "checkpoint_chain_length_not_two")
    _require(files[-1].resolve() == latest_path, "checkpoint_pointer_not_chain_tip")

    checkpoints: list[dict[str, Any]] = []
    previous_file_sha: str | None = None
    suite_id = ""
    for ordinal, path in enumerate(files):
        checkpoint = _load_json(path, f"checkpoint_{ordinal}_unreadable")
        if ordinal == 0:
            suite_id = str(checkpoint.get("suite_id") or "")
            _require(bool(suite_id), "checkpoint_suite_id")
        _validate_checkpoint_document(
            checkpoint, ordinal=ordinal, suite_id=suite_id, signature_sha=signature_sha
        )
        _require(
            checkpoint.get("previous_checkpoint_file_sha256") == previous_file_sha,
            f"checkpoint_{ordinal}_previous_hash",
        )
        previous_file_sha = file_sha256(path)
        checkpoints.append(checkpoint)

    initial, terminal = checkpoints
    _require(initial.get("status") == "running", "initial_checkpoint_status")
    _require(not (initial.get("valid_summaries") or []), "initial_checkpoint_summaries")
    _require(not (initial.get("a1r3v3_valid_entries") or []), "initial_checkpoint_entries")
    _require(not (initial.get("invalid_attempts") or []), "initial_checkpoint_invalid")
    _require(terminal.get("status") == TERMINAL_STATUS, "terminal_checkpoint_status")
    _require(not (terminal.get("invalid_attempts") or []), "terminal_invalid_attempts")
    _require(len(terminal.get("valid_summaries") or []) == 1, "terminal_summary_count")
    _require(
        len(terminal.get("a1r3v3_valid_entries") or []) == 1,
        "terminal_entry_count",
    )
    return terminal, [
        {
            "relative_path": str(path.relative_to(suite_dir)).replace("\\", "/"),
            "file_sha256": file_sha256(path),
            "content_sha256": checkpoints[index]["content_sha256"],
            "ordinal": index,
        }
        for index, path in enumerate(files)
    ]


def validate_run_signature(suite_dir: Path) -> tuple[dict[str, Any], str]:
    path = suite_dir / "run_signature.json"
    signature = _load_json(path, "run_signature_unreadable")
    signature_sha = canonical_sha256(signature)
    expected = {
        "prospective_arm": "a1r3v3",
        "mechanism_id": contract.MECHANISM_ID,
        "experiment_id": contract.EXPERIMENT_ID,
        "generation_seed": contract.GENERATION_SEED,
        "capability_gate_tasks": list(contract.CAPABILITY_GATE_TASKS),
        "ordered_expected_keys": [
            [task, contract.TASK_SEED] for task in contract.FULL_TASK_ORDER
        ],
        "reward_fail_fast": True,
        "scientific_failure_rerun": False,
        "extra_model_calls": 0,
        "action_override": False,
        "forced_termination": False,
    }
    for key, value in expected.items():
        _require(signature.get(key) == value, f"run_signature_{key}")
    _require(
        signature.get("ordered_expected_keys_sha256")
        == canonical_sha256(signature["ordered_expected_keys"]),
        "run_signature_order_hash",
    )
    _require(
        signature.get("manifest_sha256")
        == file_sha256(suite_dir / "manifest.snapshot.json"),
        "run_signature_manifest_hash",
    )
    _require(
        signature.get("prospective_config_sha256")
        == file_sha256(contract.CONFIG_PATH),
        "run_signature_config_hash",
    )
    _require(
        signature.get("prospective_preflight_sha256")
        == file_sha256(contract.PREFLIGHT_PATH),
        "run_signature_preflight_hash",
    )
    # The frozen runner used an obsolete field name. Only that known null is accepted;
    # the result is populated from the validated preflight's content binding below.
    _require(
        signature.get("prospective_source_freeze_sha256") is None,
        "run_signature_unexpected_source_freeze_field",
    )
    return signature, signature_sha


def _validate_bound_file(episode_dir: Path, relative: Any, expected: Any, code: str) -> str:
    name = str(relative or "")
    _require(bool(name), f"{code}_path")
    path = _safe_child(episode_dir, name, f"{code}_path")
    _require(path.is_file(), f"{code}_missing")
    observed = file_sha256(path)
    _require(observed == expected, f"{code}_hash")
    return str(path.relative_to(episode_dir)).replace("\\", "/")


def _validate_bound_json(episode_dir: Path, relative: Any, expected: Any, code: str) -> str:
    name = str(relative or "")
    _require(bool(name), f"{code}_path")
    path = _safe_child(episode_dir, name, f"{code}_path")
    _require(path.is_file(), f"{code}_missing")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FinalizationError(
            f"A1-R3-v3 terminal finalization failed: {code}_unreadable"
        ) from exc
    _require(canonical_sha256(value) == expected, f"{code}_hash")
    return str(path.relative_to(episode_dir)).replace("\\", "/")


def _validate_transport_and_tickets(summary: dict[str, Any]) -> dict[str, int]:
    steps = list(summary.get("steps") or [])
    _require(len(steps) == 34, "episode_step_count")
    call_ids: set[str] = set()
    idempotency_keys: set[str] = set()
    nonempty_reads = 0
    injected_chars = 0
    for index, step in enumerate(steps):
        _require(step.get("step") == index, f"step_{index}_ordinal")
        _require(step.get("executed") is True, f"step_{index}_not_executed")
        model = step.get("model_call") or {}
        meta = model.get("raven_meta") or {}
        runtime = ((step.get("layers") or {}).get("L0_runtime") or {})
        _require(meta.get("transport_attempts") == 1, f"step_{index}_transport")
        _require(runtime.get("transport_attempts") == 1, f"step_{index}_runtime_transport")
        call_id = str(model.get("call_id") or "")
        idempotency = str(model.get("idempotency_key") or "")
        _require(call_id and call_id not in call_ids, f"step_{index}_call_id")
        _require(idempotency and idempotency not in idempotency_keys, f"step_{index}_idempotency")
        call_ids.add(call_id)
        idempotency_keys.add(idempotency)

        user_prompt = str(step.get("user_prompt") or "")
        read = step.get("memory_read") or {}
        confirmation = read.get("transport_confirmation") or {}
        _require(
            read.get("final_user_prompt_sha256")
            == sha256(user_prompt.encode("utf-8")).hexdigest(),
            f"step_{index}_user_prompt_hash",
        )
        _require(confirmation.get("model_call_id") == call_id, f"step_{index}_confirmation_call")
        _require(
            confirmation.get("request_sha256") == model.get("request_sha256"),
            f"step_{index}_confirmation_request",
        )
        _require(
            confirmation.get("response_sha256") == model.get("response_sha256"),
            f"step_{index}_confirmation_response",
        )
        _require(confirmation.get("transport_attempts") == 1, f"step_{index}_confirmation_attempts")

        if read.get("nonempty"):
            nonempty_reads += 1
            text = str(read.get("exact_injected_text") or "")
            ticket = str(read.get("ticket_id") or "")
            commit = read.get("injection_commit") or {}
            text_hash = sha256(text.encode("utf-8")).hexdigest()
            injected_chars += len(text)
            _require(bool(text) and user_prompt.count(text) == 1, f"step_{index}_injection_occurrence")
            _require(read.get("rendered_chars") == len(text), f"step_{index}_rendered_chars")
            _require(read.get("rendered_sha256") == text_hash, f"step_{index}_rendered_hash")
            _require(bool(ticket) and commit.get("ticket_id") == ticket, f"step_{index}_ticket_commit")
            _require(commit.get("exact_injected_text") == text, f"step_{index}_commit_text")
            _require(commit.get("exact_injected_text_sha256") == text_hash, f"step_{index}_commit_hash")
            _require(
                commit.get("final_prompt_sha256") == read.get("final_user_prompt_sha256"),
                f"step_{index}_commit_prompt_hash",
            )
        else:
            _require(read.get("ticket_id") is None, f"step_{index}_empty_ticket")
            _require(read.get("injection_commit") is None, f"step_{index}_empty_commit")

    audit = summary.get("memory_mechanism") or {}
    counters = audit.get("counters") or {}
    boundary = audit.get("decision_boundary") or {}
    _require(audit.get("pending_ticket") is None, "episode_pending_ticket")
    _require(audit.get("receipt") is None and audit.get("support") is None, "episode_open_cnr_state")
    _require(audit.get("active") is False, "episode_cnr_active")
    for key in (
        "cnr_receipt_creation_count",
        "cnr_receipt_committed_read_count",
        "cnr_receipt_drop_count",
        "cnr_receipt_expiry_count",
        "cnr_suppressed_after_one_shot_cap_count",
    ):
        _require(counters.get(key) == 0, f"episode_{key}")
    _require(not (audit.get("receipt_events") or []), "episode_receipt_events")
    _require(not (audit.get("read_events") or []), "episode_cnr_read_events")
    _require(not (audit.get("lifecycle_events") or []), "episode_cnr_lifecycle_events")
    _require(counters.get("read_call_count") == len(steps), "episode_read_call_count")
    _require(counters.get("nonempty_read_count") == nonempty_reads, "episode_nonempty_read_count")
    _require(counters.get("injected_chars") == injected_chars, "episode_injected_chars")
    for key in (
        "extra_model_calls",
        "action_override_count",
        "forced_termination_count",
        "extra_screenshots",
    ):
        _require(int(boundary.get(key) or 0) == 0, f"episode_boundary_{key}")
    for key in (
        "hidden_ui_used_for_decision",
        "evaluator_used_for_decision",
        "goal_parser_used_for_decision",
        "task_name_used_for_decision",
    ):
        _require(boundary.get(key) is False, f"episode_boundary_{key}")
    return {
        "model_calls": len(steps),
        "transport_attempts": len(steps),
        "nonempty_reads": nonempty_reads,
        "injected_chars": injected_chars,
    }


def validate_episode(
    suite_dir: Path, terminal: dict[str, Any], signature_sha: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    summary = terminal["valid_summaries"][0]
    entry = terminal["a1r3v3_valid_entries"][0]
    expected_identity = {
        "task_name": contract.FULL_TASK_ORDER[0],
        "seed": contract.TASK_SEED,
        "success": False,
        "evaluator_reward": 0.0,
        "termination_reason": "max_steps",
        "model_call_count": 34,
        "executed_action_count": 34,
        "step_count": 34,
    }
    for key, value in expected_identity.items():
        _require(summary.get(key) == value, f"episode_{key}")
    _require(summary.get("error") is None, "episode_error")
    _require(not (summary.get("lifecycle_errors") or []), "episode_lifecycle_errors")
    episode_id = str(summary.get("episode_id") or "")
    _require(entry.get("episode_id") == episode_id, "entry_episode_id")
    _require(entry.get("task_name") == summary["task_name"], "entry_task")
    _require(entry.get("seed") == summary["seed"], "entry_seed")
    _require(entry.get("run_signature_sha256") == signature_sha, "entry_signature")
    _require(entry.get("summary_sha256") == canonical_sha256(summary), "entry_summary_hash")

    episode_dir = _safe_child(suite_dir / "episodes", episode_id, "episode_directory")
    episode_path = episode_dir / "episode.json"
    _require(episode_path.is_file(), "episode_json_missing")
    _require(file_sha256(episode_path) == entry.get("episode_json_sha256"), "episode_json_hash")
    episode = _load_json(episode_path, "episode_json_unreadable")
    _require(episode == summary, "episode_summary_drift")
    metadata = summary.get("run_metadata") or {}
    _require(metadata.get("run_signature_sha256") == signature_sha, "episode_signature")
    _require(
        metadata.get("memory_intervention") == contract.MECHANISM_ID,
        "episode_mechanism",
    )

    artifact_names = {"episode.json", "events.jsonl"}
    for index, step in enumerate(summary["steps"]):
        for side in ("before", "after"):
            observation = step.get(side) or {}
            artifact_names.add(
                _validate_bound_file(
                    episode_dir,
                    observation.get("screenshot"),
                    observation.get("screenshot_sha256"),
                    f"step_{index}_{side}_screenshot",
                )
            )
            artifact_names.add(
                _validate_bound_json(
                    episode_dir,
                    observation.get("ui_record"),
                    observation.get("ui_sha256"),
                    f"step_{index}_{side}_ui",
                )
            )
        _require(
            step.get("before_screenshot") == (step.get("before") or {}).get("screenshot"),
            f"step_{index}_before_path_binding",
        )
        _require(
            step.get("before_screenshot_sha256")
            == (step.get("before") or {}).get("screenshot_sha256"),
            f"step_{index}_before_hash_binding",
        )
    observed_files = {
        str(path.relative_to(episode_dir)).replace("\\", "/")
        for path in episode_dir.rglob("*")
        if path.is_file()
    }
    _require(observed_files == artifact_names, "episode_artifact_set")

    events_path = episode_dir / "events.jsonl"
    try:
        events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FinalizationError(
            "A1-R3-v3 terminal finalization failed: events_unreadable"
        ) from exc
    expected_events = (
        ["episode_start", "task_initialized"]
        + ["step"] * 34
        + ["evaluator_result", "task_torn_down", "post_episode_reset", "episode_complete"]
    )
    _require([event.get("event") for event in events] == expected_events, "event_sequence")
    for index, event in enumerate(events[2:36]):
        event_without_time = dict(event)
        event_without_time.pop("time", None)
        _require(event_without_time == summary["steps"][index], f"event_step_{index}_drift")
    _require(events[-4].get("reward") == 0.0, "event_evaluator_reward")
    _require(events[-1].get("success") is False, "event_completion_success")
    _require(events[-1].get("termination_reason") == "max_steps", "event_completion_reason")

    transport = _validate_transport_and_tickets(summary)
    return summary, {
        "episode_json_sha256": file_sha256(episode_path),
        "episode_summary_sha256": canonical_sha256(summary),
        "events_jsonl_sha256": file_sha256(events_path),
        "artifact_file_count": len(observed_files),
        **transport,
    }


def validate_gate(terminal: dict[str, Any]) -> None:
    gate = terminal.get("capability_gate") or {}
    _require(gate.get("required") == 6, "gate_required")
    _require(gate.get("status") == "fail", "gate_status")
    _require(gate.get("success_count") == 0, "gate_success_count")
    rows = list(gate.get("tasks") or [])
    _require(
        [row.get("task_name") for row in rows] == list(contract.CAPABILITY_GATE_TASKS),
        "gate_task_order",
    )
    _require(rows[0].get("reward") == 0.0 and rows[0].get("pass") is False, "gate_first_row")
    _require(
        all(row.get("reward") is None and row.get("pass") is False for row in rows[1:]),
        "gate_unrun_rows",
    )


def validate_frozen_evidence(
    receipt_path: Path,
    signature: dict[str, Any],
    terminal: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, Any]:
    try:
        preflight = contract.validate_preflight_report(contract.PREFLIGHT_PATH)
    except RuntimeError as exc:
        raise FinalizationError(
            "A1-R3-v3 terminal finalization failed: source_or_preflight_invalid"
        ) from exc
    # validate_preflight_report has already revalidated the source freeze against
    # the frozen implementation commit; load that same validated document once.
    freeze = _load_json(contract.SOURCE_FREEZE_PATH, "source_freeze_unreadable")
    receipt = _load_json(receipt_path, "live_receipt_unreadable")
    config = _load_json(contract.CONFIG_PATH, "config_unreadable")
    expected = {
        "schema": contract.LIVE_RECEIPT_SCHEMA,
        "status": "PASS",
        "errors": [],
        "generation_calls": 0,
        "mechanism_id": contract.MECHANISM_ID,
        "experiment_id": contract.EXPERIMENT_ID,
        "implementation_commit": preflight["implementation_commit"],
        "preflight_content_sha256": preflight["content_sha256"],
        "config_content_sha256": canonical_sha256(config),
        "served_model_id": contract.MODEL_ID,
        "served_model_ids_observed": [contract.MODEL_ID],
        "model_realpath": contract.MODEL_REALPATH,
        "model_manifest_sha256": contract.MODEL_MANIFEST_SHA256,
        "port": contract.PORT,
    }
    for key, value in expected.items():
        _require(receipt.get(key) == value, f"receipt_{key}")
    _require(receipt.get("content_sha256") == content_sha256(receipt), "receipt_content_hash")
    stable = signature.get("prospective_live_server_stable_identity") or {}
    _require(receipt.get("packages") == stable.get("packages"), "receipt_packages_signature")
    for key in ("served_model_id", "model_realpath", "model_manifest_sha256", "port"):
        _require(receipt.get(key) == stable.get(key), f"receipt_signature_{key}")
    cmdline = str(receipt.get("process_cmdline") or "")
    _require(
        "vllm" in cmdline and contract.MODEL_REALPATH in cmdline and str(contract.PORT) in cmdline,
        "receipt_process_identity",
    )
    _require(int(receipt.get("process_pid") or -1) > 0, "receipt_process_pid")
    try:
        qualified = datetime.fromisoformat(str(receipt.get("qualified_at")))
        started = datetime.fromisoformat(str(summary.get("started_at")))
        _require(qualified.tzinfo is not None and started.tzinfo is not None, "receipt_time_zone")
        age = (started - qualified).total_seconds()
        _require(0 <= age <= 43_200, "receipt_time_binding")
    except (TypeError, ValueError):
        _fail("receipt_time_parse")

    receipt_file_sha = file_sha256(receipt_path)
    _require(
        terminal.get("live_server_receipt_sha256s") == [receipt_file_sha],
        "checkpoint_receipt_file_hash",
    )
    _require(
        (summary.get("run_metadata") or {}).get("live_server_receipt_sha256")
        == receipt_file_sha,
        "episode_receipt_file_hash",
    )
    _require(
        preflight.get("source_freeze_content_sha256") == freeze.get("content_sha256"),
        "preflight_source_freeze_binding",
    )
    return {
        "implementation_commit": preflight["implementation_commit"],
        "source_freeze_content_sha256": freeze["content_sha256"],
        "source_freeze_file_sha256": file_sha256(contract.SOURCE_FREEZE_PATH),
        "preflight_content_sha256": preflight["content_sha256"],
        "preflight_file_sha256": file_sha256(contract.PREFLIGHT_PATH),
        "live_receipt_content_sha256": receipt["content_sha256"],
        "live_receipt_file_sha256": receipt_file_sha,
    }


def _usage(summary: dict[str, Any]) -> dict[str, int]:
    totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for step in summary["steps"]:
        usage = (step.get("model_call") or {}).get("usage") or {}
        for key in totals:
            value = usage.get(key)
            _require(isinstance(value, int) and value >= 0, f"usage_{key}")
            totals[key] += value
    _require(
        totals["prompt_tokens"] + totals["completion_tokens"] == totals["total_tokens"],
        "usage_total_consistency",
    )
    return totals


def build_result(
    *,
    suite_dir: Path,
    signature: dict[str, Any],
    signature_sha: str,
    terminal: dict[str, Any],
    checkpoint_chain: list[dict[str, Any]],
    summary: dict[str, Any],
    episode_integrity: dict[str, Any],
    frozen: dict[str, Any],
) -> dict[str, Any]:
    elapsed = (
        datetime.fromisoformat(summary["finished_at"])
        - datetime.fromisoformat(summary["started_at"])
    ).total_seconds()
    _require(math.isfinite(elapsed) and elapsed >= 0, "episode_elapsed")
    tasks = []
    for index, task_name in enumerate(contract.FULL_TASK_ORDER):
        if index == 0:
            tasks.append(
                {
                    "task_name": task_name,
                    "seed": contract.TASK_SEED,
                    "execution_status": "VALID_SCIENTIFIC_FAILURE",
                    "episode_id": summary["episode_id"],
                    "success": False,
                    "reward": 0.0,
                    "termination_reason": "max_steps",
                }
            )
        else:
            tasks.append(
                {
                    "task_name": task_name,
                    "seed": contract.TASK_SEED,
                    "execution_status": "NOT_RUN_BY_PROTOCOL",
                    "episode_id": None,
                    "success": None,
                    "reward": None,
                    "termination_reason": None,
                }
            )
    counters = (summary.get("memory_mechanism") or {}).get("counters") or {}
    result: dict[str, Any] = {
        "schema": contract.RESULT_SCHEMA,
        "status": "TERMINAL_VALID_SCIENTIFIC_FAILURE",
        "completion": "GATE_STOPPED_1_OF_6",
        "scientific_valid": True,
        "identity": {
            "suite_id": terminal["suite_id"],
            "prospective_arm": "a1r3v3",
            "mechanism_id": contract.MECHANISM_ID,
            "experiment_id": contract.EXPERIMENT_ID,
            "task_seed": contract.TASK_SEED,
            "generation_seed": contract.GENERATION_SEED,
            "implementation_commit": frozen["implementation_commit"],
            "source_freeze_content_sha256": frozen["source_freeze_content_sha256"],
        },
        "closure": {
            "source_checkpoint_status": TERMINAL_STATUS,
            "valid_episode_count": 1,
            "invalid_attempt_count": 0,
            "not_run_by_protocol_count": 18,
            "checkpoint_chain_valid": True,
            "episode_artifact_closure_valid": True,
            "single_transport_per_call": True,
            "read_tickets_closed": True,
            "generation_calls_during_finalization": 0,
            "network_calls_during_finalization": 0,
            "raw_suite_modified": False,
        },
        "capability_gate": terminal["capability_gate"],
        "performance_observed_partial": {
            "success_count": 0,
            "reward_sum": 0.0,
            "model_calls": summary["model_call_count"],
            "executed_actions": summary["executed_action_count"],
            "token_usage": _usage(summary),
            "valid_elapsed_seconds": elapsed,
        },
        "verdicts": {
            "accuracy": "FAIL_GATE_STOPPED",
            "cost": "NOT_APPLICABLE_PARTIAL",
            "mechanism": "NOT_OBSERVED_NO_CNR_COMMIT",
            "episode_classification": "PRESERVATION_FAILURE_UNATTRIBUTED",
            "causal_harm_claim_permitted": False,
            "matched_ablation_authorized": False,
            "continuation_authorized": False,
            "same_identity_rerun_authorized": False,
        },
        "memory_observed": {
            "base_ledger_nonempty_read_count": counters["nonempty_read_count"],
            "base_ledger_injected_chars": counters["injected_chars"],
            "cnr_receipt_creation_count": 0,
            "cnr_receipt_committed_read_count": 0,
            "cnr_opportunity": "NONE_OBSERVED",
        },
        "tasks": tasks,
        "integrity": {
            **frozen,
            "run_signature_canonical_sha256": signature_sha,
            "run_signature_file_sha256": file_sha256(suite_dir / "run_signature.json"),
            "manifest_snapshot_file_sha256": file_sha256(suite_dir / "manifest.snapshot.json"),
            "config_file_sha256": file_sha256(contract.CONFIG_PATH),
            "checkpoint_pointer_file_sha256": file_sha256(suite_dir / "checkpoint.json"),
            "terminal_checkpoint_file_sha256": checkpoint_chain[-1]["file_sha256"],
            "terminal_checkpoint_content_sha256": terminal["content_sha256"],
            "checkpoint_chain": checkpoint_chain,
            **episode_integrity,
        },
        "finalization": {
            "classification": "CPU_ONLY_EVIDENCE_LAYER_FINALIZATION",
            "reason": "terminal_gate_checkpoint_precedes_full_suite_aggregate_branch",
            "source_run_signature_known_null_field": "prospective_source_freeze_sha256",
            "source_run_signature_known_null_repaired_from": "validated_preflight.source_freeze_content_sha256",
        },
        "errors": [],
    }
    _require(sum(task["execution_status"] == "NOT_RUN_BY_PROTOCOL" for task in tasks) == 18, "result_unrun_count")
    result["content_sha256"] = content_sha256(result)
    return result


def finalize(suite_dir: Path, receipt_path: Path) -> dict[str, Any]:
    suite_dir = suite_dir.resolve()
    _require(suite_dir.is_dir(), "suite_directory_missing")
    signature, signature_sha = validate_run_signature(suite_dir)
    terminal, chain = validate_checkpoint_chain(suite_dir, signature_sha)
    _require(terminal.get("run_signature_sha256") == signature_sha, "terminal_signature")
    validate_gate(terminal)
    summary, episode_integrity = validate_episode(suite_dir, terminal, signature_sha)
    frozen = validate_frozen_evidence(
        receipt_path.resolve(), signature, terminal, summary
    )
    return build_result(
        suite_dir=suite_dir,
        signature=signature,
        signature_sha=signature_sha,
        terminal=terminal,
        checkpoint_chain=chain,
        summary=summary,
        episode_integrity=episode_integrity,
        frozen=frozen,
    )


def write_result(output: Path, suite_dir: Path, result: dict[str, Any]) -> None:
    output = output.resolve()
    try:
        output.relative_to(suite_dir.resolve())
    except ValueError:
        pass
    else:
        _fail("output_must_not_modify_raw_suite")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite-dir", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = finalize(args.suite_dir, args.receipt)
    write_result(args.output, args.suite_dir, result)
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "schema": result["schema"],
                "status": result["status"],
                "content_sha256": result["content_sha256"],
                "not_run_by_protocol_count": result["closure"]["not_run_by_protocol_count"],
                "generation_calls_during_finalization": 0,
                "network_calls_during_finalization": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
