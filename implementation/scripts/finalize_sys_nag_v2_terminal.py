#!/usr/bin/env python3
"""CPU-only evidence finalizer for the terminal SYS-NAG V2 capability gate.

This is a post-run evidence layer.  It never imports or calls the model client and
does not write into the ignored live suite.  Checkpoint summaries, entry digests,
raw episode digests and decoded episode content must all close exactly.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))


class _FrozenV2Contract:
    """Constants copied from the source-frozen V2 contract.

    SYS-NAG's live contract module is intentionally reused by later protocol
    versions, so importing today's module would make a V2 evidence finalizer
    silently follow V3.  These values are also checked against the archived
    signature, preflight, freeze, receipt and checkpoint below.
    """

    SYSTEM_ID = "sys_r2_numeric_answer_consistency_guard_v2"
    EXPERIMENT_ID = "SYS_NAG_V2_R2_QWEN3VL32B_AW_HARD_S20260806_G3407_V1"
    MECHANISM_ID = "a1r2_compact_verified_pending_v1"
    RESULT_SCHEMA = "sys_nag_v2_result_v1"
    CHECKPOINT_SCHEMA = "sys_nag_v2_checkpoint_v1"
    PREFLIGHT_SCHEMA = "sys_nag_v2_zero_generation_preflight_v1"
    OFFLINE_REPLAY_SCHEMA = "sys_nag_v2_offline_replay_v1"
    LIVE_RECEIPT_SCHEMA = "sys_nag_v2_live_server_receipt_v1"
    TASK_SEED = 20260806
    GENERATION_SEED = 3407
    MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
    MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
    MODEL_REALPATH = "/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope"
    MODEL_MANIFEST_SHA256 = "18e0909c7d993853d6d0f62443461a74009754f90db026a1723cab80121c7872"
    PORT = 18000
    CONFIG_PATH = ROOT / "implementation/configs/sys_nag_v2_r2_hard_seed20260806.json"
    SOURCE_FREEZE_PATH = ROOT / "evidence/sys_nag_v2/SYS_NAG_V2_SOURCE_FREEZE.json"
    PREFLIGHT_PATH = ROOT / "evidence/sys_nag_v2/SYS_NAG_V2_ZERO_GENERATION_PREFLIGHT.json"
    OFFLINE_REPLAY_PATH = ROOT / "evidence/sys_nag_v2/SYS_NAG_V2_OFFLINE_REPLAY_REPORT.json"
    CAPABILITY_GATE_TASKS = (
        "ExpenseDeleteMultiple2",
        "RetroSavePlaylist",
        "SimpleCalendarAddOneEvent",
        "SportsTrackerTotalDurationForCategoryThisWeek",
        "RecipeDeleteMultipleRecipesWithConstraint",
        "OsmAndMarker",
    )
    FULL_TASK_ORDER = CAPABILITY_GATE_TASKS + (
        "BrowserMultiply",
        "ExpenseAddMultipleFromGallery",
        "ExpenseAddMultipleFromMarkor",
        "MarkorCreateNoteAndSms",
        "MarkorMergeNotes",
        "MarkorTranscribeVideo",
        "OsmAndTrack",
        "RecipeAddMultipleRecipesFromImage",
        "RecipeAddMultipleRecipesFromMarkor",
        "RecipeAddMultipleRecipesFromMarkor2",
        "SaveCopyOfReceiptTaskEval",
        "SportsTrackerActivitiesOnDate",
        "SportsTrackerTotalDistanceForCategoryOverInterval",
    )


contract = _FrozenV2Contract()


TERMINAL_STATUS = "stopped_capability_gate_failure"
DEFAULT_SUITE = ROOT / "runs/sys_nag_v2/official_qwen_20260816T024642_c7867dfe"
DEFAULT_RECEIPT = ROOT / "evidence/sys_nag_v2/SYS_NAG_V2_LIVE_RECEIPT.json"
DEFAULT_OUTPUT = ROOT / "evidence/sys_nag_v2/SYS_NAG_V2_TERMINAL_RESULT_2026-08-16.json"

class FinalizationError(RuntimeError):
    """The immutable live evidence does not satisfy the terminal contract."""


def _fail(code: str) -> None:
    raise FinalizationError(f"SYS-NAG V2 terminal finalization failed: {code}")


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


def _load(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FinalizationError(
            f"SYS-NAG V2 terminal finalization failed: {code}"
        ) from exc
    if not isinstance(value, dict):
        _fail(code)
    return value


def _safe_child(root: Path, relative: Any, code: str) -> Path:
    path = (root / str(relative or "")).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        _fail(code)
    return path


def validate_run_signature(suite: Path) -> tuple[dict[str, Any], str]:
    signature = _load(suite / "run_signature.json", "run_signature_unreadable")
    signature_sha = canonical_sha256(signature)
    expected = {
        "prospective_arm": "sys_nag",
        "mechanism_id": contract.MECHANISM_ID,
        "experiment_id": contract.EXPERIMENT_ID,
        "generation_seed": contract.GENERATION_SEED,
        "ordered_expected_keys": [
            [task, contract.TASK_SEED] for task in contract.FULL_TASK_ORDER
        ],
        "reward_fail_fast": True,
        "scientific_failure_rerun": False,
        "extra_model_calls": 0,
        "action_override": False,
        "forced_termination": False,
        "model_id": contract.MODEL_ID,
        "model_revision": contract.MODEL_REVISION,
    }
    for key, value in expected.items():
        _require(signature.get(key) == value, f"run_signature_{key}")
    _require(
        signature.get("ordered_expected_keys_sha256")
        == canonical_sha256(signature["ordered_expected_keys"]),
        "run_signature_order_hash",
    )
    bindings = {
        "manifest_sha256": suite / "manifest.snapshot.json",
        "prospective_config_sha256": contract.CONFIG_PATH,
        "prospective_preflight_sha256": contract.PREFLIGHT_PATH,
    }
    for key, path in bindings.items():
        _require(signature.get(key) == file_sha256(path), f"run_signature_{key}")
    freeze = _load(contract.SOURCE_FREEZE_PATH, "source_freeze_unreadable")
    _require(
        signature.get("prospective_source_freeze_sha256")
        == freeze.get("content_sha256"),
        "run_signature_source_freeze",
    )
    # Retain, but do not normalize away, the two stale inherited labels.
    _require(
        signature.get("task_order")
        == "blocking_A0_4_task_gate_then_frozen_manifest_remainder",
        "run_signature_known_task_order_label",
    )
    _require(
        signature.get("A0_preservation_tasks")
        == list(contract.CAPABILITY_GATE_TASKS[:4]),
        "run_signature_known_preservation_label",
    )
    return signature, signature_sha


def validate_checkpoint(
    suite: Path, signature_sha: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    checkpoint_path = suite / "checkpoint.json"
    checkpoint = _load(checkpoint_path, "checkpoint_unreadable")
    expected = {
        "schema": contract.CHECKPOINT_SCHEMA,
        "status": TERMINAL_STATUS,
        "prospective_arm": "sys_nag",
        "mechanism_id": contract.MECHANISM_ID,
        "experiment_id": contract.EXPERIMENT_ID,
        "suite_id": suite.name,
        "run_signature_sha256": signature_sha,
    }
    for key, value in expected.items():
        _require(checkpoint.get(key) == value, f"checkpoint_{key}")
    _require(not (checkpoint.get("invalid_attempts") or []), "checkpoint_invalid_attempts")
    summaries = list(checkpoint.get("valid_summaries") or [])
    entries = list(checkpoint.get("sys_nag_valid_entries") or [])
    _require(len(summaries) == 2, "checkpoint_summary_count")
    _require(len(entries) == 2, "checkpoint_entry_count")
    _require(
        [row.get("task_name") for row in summaries]
        == list(contract.CAPABILITY_GATE_TASKS[:2]),
        "checkpoint_task_order",
    )
    _require(
        [row.get("evaluator_reward") for row in summaries] == [1.0, 0.5],
        "checkpoint_rewards",
    )
    _require([row.get("success") for row in summaries] == [True, False], "checkpoint_successes")
    _require(all(row.get("error") is None for row in summaries), "checkpoint_episode_error")
    _require(
        all(not (row.get("lifecycle_errors") or []) for row in summaries),
        "checkpoint_lifecycle_errors",
    )
    for index, (summary, entry) in enumerate(zip(summaries, entries, strict=True)):
        for key in ("episode_id", "task_name", "seed"):
            _require(entry.get(key) == summary.get(key), f"entry_{index}_{key}")
        _require(entry.get("run_signature_sha256") == signature_sha, f"entry_{index}_signature")
        _require(
            entry.get("summary_sha256") == canonical_sha256(summary),
            f"entry_{index}_summary_hash",
        )
    return checkpoint, []


def validate_gate(checkpoint: dict[str, Any]) -> None:
    gate = checkpoint.get("capability_gate") or {}
    _require(gate.get("required") == 6, "gate_required")
    _require(gate.get("status") == "fail", "gate_status")
    _require(gate.get("success_count") == 1, "gate_success_count")
    rows = list(gate.get("tasks") or [])
    _require(
        [row.get("task_name") for row in rows] == list(contract.CAPABILITY_GATE_TASKS),
        "gate_order",
    )
    _require(rows[0].get("pass") is True and rows[0].get("reward") == 1.0, "gate_row_0")
    _require(rows[1].get("pass") is False and rows[1].get("reward") == 0.5, "gate_row_1")
    _require(
        all(row.get("pass") is False and row.get("reward") is None for row in rows[2:]),
        "gate_unrun_rows",
    )


def _validate_artifact(path: Path, expected: Any, code: str, *, canonical: bool = False) -> None:
    _require(path.is_file(), f"{code}_missing")
    observed = canonical_sha256(json.loads(path.read_text(encoding="utf-8"))) if canonical else file_sha256(path)
    _require(observed == expected, f"{code}_hash")


def validate_episode(
    suite: Path,
    summary: dict[str, Any],
    entry: dict[str, Any],
    signature_sha: str,
) -> dict[str, Any]:
    episode_id = str(summary.get("episode_id") or "")
    episode_dir = _safe_child(suite / "episodes", episode_id, "episode_directory")
    episode_path = episode_dir / "episode.json"
    _validate_artifact(episode_path, entry.get("episode_json_sha256"), "episode_json")
    episode = _load(episode_path, "episode_json_unreadable")
    _require(episode == summary, "episode_checkpoint_summary_drift")
    metadata = summary.get("run_metadata") or {}
    _require(metadata.get("run_signature_sha256") == signature_sha, "episode_signature")
    _require(metadata.get("memory_intervention") == contract.MECHANISM_ID, "episode_mechanism")
    _require(summary.get("memory_mechanism", {}).get("mechanism_id") == contract.MECHANISM_ID, "episode_memory_audit")

    steps = list(summary.get("steps") or [])
    call_count = int(summary.get("model_call_count") or -1)
    _require(len(steps) == call_count == int(summary.get("step_count") or -1), "episode_step_count")
    executed_count = sum(bool(step.get("executed")) for step in steps)
    _require(summary.get("executed_action_count") == executed_count, "episode_executed_count")
    _require(executed_count == call_count - 1, "episode_single_terminal_decision")
    _require(steps[-1].get("executed") is False, "episode_terminal_not_executed")
    _require(summary.get("termination_reason") == "model_terminate_success", "episode_termination_reason")
    guard = summary.get("answer_consistency_guard") or {}
    counters = guard.get("counters") or {}
    events = list(guard.get("events") or [])
    _require(guard.get("system_id") == contract.SYSTEM_ID, "guard_system_id")
    _require(counters.get("review_count") == call_count == len(events), "guard_review_count")
    _require(counters.get("eligible_count") == 0, "guard_eligible_count")
    for key in ("extra_model_calls", "action_override_count", "forced_termination_count"):
        _require(int(counters.get(key) or 0) == 0, f"guard_{key}")

    prompt_tokens = completion_tokens = total_tokens = 0
    latency_seconds = 0.0
    artifact_names = {"episode.json", "events.jsonl"}
    call_ids: set[str] = set()
    for index, step in enumerate(steps):
        _require(step.get("step") == index, f"step_{index}_ordinal")
        model = step.get("model_call") or {}
        runtime = ((step.get("layers") or {}).get("L0_runtime") or {})
        meta = model.get("raven_meta") or {}
        _require(meta.get("transport_attempts") == 1, f"step_{index}_transport")
        _require(runtime.get("transport_attempts") == 1, f"step_{index}_runtime_transport")
        call_id = str(model.get("call_id") or "")
        _require(bool(call_id) and call_id not in call_ids, f"step_{index}_call_id")
        call_ids.add(call_id)
        usage = model.get("usage") or {}
        values = [usage.get("prompt_tokens"), usage.get("completion_tokens"), usage.get("total_tokens")]
        _require(all(isinstance(value, int) and value >= 0 for value in values), f"step_{index}_usage")
        _require(values[0] + values[1] == values[2], f"step_{index}_usage_sum")
        prompt_tokens += values[0]
        completion_tokens += values[1]
        total_tokens += values[2]
        latency = runtime.get("latency_seconds")
        _require(isinstance(latency, (int, float)) and math.isfinite(latency) and latency >= 0, f"step_{index}_latency")
        latency_seconds += float(latency)
        _require((step.get("answer_consistency_guard") or {}) == events[index], f"step_{index}_guard_event")
        for side in ("before", "after"):
            observation = step.get(side) or {}
            if not observation:
                _require(
                    side == "after" and index == call_count - 1 and not step.get("executed"),
                    f"step_{index}_{side}_unexpected_missing",
                )
                continue
            screen = _safe_child(episode_dir, observation.get("screenshot"), f"step_{index}_{side}_screen_path")
            ui = _safe_child(episode_dir, observation.get("ui_record"), f"step_{index}_{side}_ui_path")
            _validate_artifact(screen, observation.get("screenshot_sha256"), f"step_{index}_{side}_screen")
            _validate_artifact(ui, observation.get("ui_sha256"), f"step_{index}_{side}_ui", canonical=True)
            artifact_names.add(screen.name)
            artifact_names.add(ui.name)

    events_path = episode_dir / "events.jsonl"
    try:
        disk_events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FinalizationError("SYS-NAG V2 terminal finalization failed: events_unreadable") from exc
    expected_sequence = ["episode_start", "task_initialized"] + ["step"] * call_count + [
        "evaluator_result", "task_torn_down", "post_episode_reset", "episode_complete"
    ]
    _require([event.get("event") for event in disk_events] == expected_sequence, "events_sequence")
    for index, event in enumerate(disk_events[2 : 2 + call_count]):
        event = dict(event)
        event.pop("time", None)
        _require(event == steps[index], f"events_step_{index}")
    _require(disk_events[-4].get("reward") == summary.get("evaluator_reward"), "events_reward")
    _require(disk_events[-1].get("success") == summary.get("success"), "events_success")
    observed_names = {path.name for path in episode_dir.iterdir() if path.is_file()}
    _require(observed_names == artifact_names, "episode_artifact_set")
    return {
        "episode_id": episode_id,
        "episode_json_file_sha256": file_sha256(episode_path),
        "episode_summary_canonical_sha256": canonical_sha256(summary),
        "events_jsonl_file_sha256": file_sha256(events_path),
        "artifact_file_count": len(observed_names),
        "model_calls": call_count,
        "executed_actions": executed_count,
        "transport_attempt_max": 1,
        "model_latency_seconds": latency_seconds,
        "token_usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
        "guard_eligible_count": 0,
        "guard_override_count": 0,
    }


def validate_frozen_evidence(
    suite: Path,
    signature: dict[str, Any],
    checkpoint: dict[str, Any],
    receipt_path: Path,
) -> dict[str, Any]:
    freeze = _load(contract.SOURCE_FREEZE_PATH, "source_freeze_unreadable")
    preflight = _load(contract.PREFLIGHT_PATH, "preflight_unreadable")
    replay = _load(contract.OFFLINE_REPLAY_PATH, "offline_replay_unreadable")
    receipt = _load(receipt_path, "receipt_unreadable")
    _require(freeze.get("content_sha256") == content_sha256(freeze), "source_freeze_content_hash")
    _require(preflight.get("content_sha256") == content_sha256(preflight), "preflight_content_hash")
    _require(replay.get("content_sha256") == content_sha256(replay), "offline_replay_content_hash")
    _require(receipt.get("content_sha256") == content_sha256(receipt), "receipt_content_hash")
    _require(freeze.get("schema") == "a1r3_srpl_source_freeze_v1", "source_freeze_schema")
    _require(freeze.get("implementation_commit") == "6c7b7f3405186ef0585b927853c5fc48b9bb5625", "source_freeze_commit")
    _require(freeze.get("parent_evidence_commit") == "603d4088a7b3448df3472e8bfc6fa8bd1bba0e97", "source_freeze_parent")
    frozen_files = freeze.get("files") or {}
    _require(isinstance(frozen_files, dict) and len(frozen_files) == 24, "source_freeze_files")
    for relative, expected_sha in frozen_files.items():
        try:
            blob = subprocess.run(
                ["git", "show", f"{freeze['implementation_commit']}:{relative}"],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            raise FinalizationError(
                "SYS-NAG V2 terminal finalization failed: source_freeze_git_object"
            ) from exc
        _require(sha256(blob).hexdigest() == expected_sha, f"source_freeze_blob:{relative}")
    _require(
        replay.get("schema") == contract.OFFLINE_REPLAY_SCHEMA
        and replay.get("status") == "PASS"
        and replay.get("errors") == []
        and replay.get("generation_calls") == 0
        and int((replay.get("totals") or {}).get("valid_episode_count") or 0) == 19,
        "offline_replay_authorization",
    )
    regression = replay.get("v2_failure_regression") or {}
    _require(
        regression.get("corrected_action") == {"type": "answer", "text": "180"}
        and bool((regression.get("event") or {}).get("overridden")),
        "offline_replay_regression",
    )
    expected_preflight = {
        "schema": contract.PREFLIGHT_SCHEMA,
        "status": "PASS",
        "errors": [],
        "generation_calls": 0,
        "live_generation_authorized": True,
        "mechanism_id": contract.MECHANISM_ID,
        "experiment_id": contract.EXPERIMENT_ID,
        "implementation_commit": freeze.get("implementation_commit"),
        "source_freeze_content_sha256": freeze.get("content_sha256"),
        "offline_replay_content_sha256": replay.get("content_sha256"),
    }
    for key, value in expected_preflight.items():
        _require(preflight.get(key) == value, f"preflight_{key}")
    config = _load(contract.CONFIG_PATH, "config_unreadable")
    expected_receipt = {
        "schema": contract.LIVE_RECEIPT_SCHEMA,
        "status": "PASS",
        "errors": [],
        "generation_calls": 0,
        "mechanism_id": contract.MECHANISM_ID,
        "experiment_id": contract.EXPERIMENT_ID,
        "implementation_commit": preflight.get("implementation_commit"),
        "preflight_content_sha256": preflight.get("content_sha256"),
        "config_content_sha256": canonical_sha256(config),
        "served_model_id": contract.MODEL_ID,
        "model_realpath": contract.MODEL_REALPATH,
        "model_manifest_sha256": contract.MODEL_MANIFEST_SHA256,
        "port": contract.PORT,
    }
    for key, value in expected_receipt.items():
        _require(receipt.get(key) == value, f"receipt_{key}")
    receipt_sha = file_sha256(receipt_path)
    _require(checkpoint.get("live_server_receipt_sha256s") == [receipt_sha], "checkpoint_receipt_hash")
    for summary in checkpoint["valid_summaries"]:
        _require(
            (summary.get("run_metadata") or {}).get("live_server_receipt_sha256") == receipt_sha,
            "episode_receipt_hash",
        )
        qualified = datetime.fromisoformat(str(receipt.get("qualified_at")))
        started = datetime.fromisoformat(str(summary.get("started_at")))
        _require(qualified.tzinfo is not None and started.tzinfo is not None, "receipt_time_zone")
        _require(0 <= (started - qualified).total_seconds() <= 43_200, "receipt_time_binding")
    _require(signature.get("prospective_preflight_sha256") == file_sha256(contract.PREFLIGHT_PATH), "signature_preflight_file")
    stable = signature.get("prospective_live_server_stable_identity") or {}
    _require(receipt.get("packages") == stable.get("packages"), "receipt_packages_signature")
    for key in ("served_model_id", "model_realpath", "model_manifest_sha256", "port"):
        _require(receipt.get(key) == stable.get(key), f"receipt_signature_{key}")
    return {
        "implementation_commit": freeze["implementation_commit"],
        "source_freeze_content_sha256": freeze["content_sha256"],
        "source_freeze_file_sha256": file_sha256(contract.SOURCE_FREEZE_PATH),
        "preflight_content_sha256": preflight["content_sha256"],
        "preflight_file_sha256": file_sha256(contract.PREFLIGHT_PATH),
        "offline_replay_content_sha256": replay["content_sha256"],
        "offline_replay_file_sha256": file_sha256(contract.OFFLINE_REPLAY_PATH),
        "live_receipt_content_sha256": receipt["content_sha256"],
        "live_receipt_file_sha256": receipt_sha,
        "run_signature_file_sha256": file_sha256(suite / "run_signature.json"),
        "manifest_snapshot_file_sha256": file_sha256(suite / "manifest.snapshot.json"),
    }


def build_result(
    suite: Path,
    signature_sha: str,
    checkpoint: dict[str, Any],
    defects: list[dict[str, Any]],
    episodes: list[dict[str, Any]],
    frozen: dict[str, Any],
) -> dict[str, Any]:
    summaries = checkpoint["valid_summaries"]
    rows: list[dict[str, Any]] = []
    for index, task_name in enumerate(contract.FULL_TASK_ORDER):
        if index < 2:
            summary = summaries[index]
            rows.append({
                "task_name": task_name,
                "seed": contract.TASK_SEED,
                "execution_status": "VALID_SUCCESS" if summary["success"] else "VALID_SCIENTIFIC_FAILURE",
                "episode_id": summary["episode_id"],
                "success": summary["success"],
                "reward": summary["evaluator_reward"],
                "termination_reason": summary["termination_reason"],
            })
        else:
            rows.append({
                "task_name": task_name,
                "seed": contract.TASK_SEED,
                "execution_status": "NOT_RUN_BY_PROTOCOL",
                "episode_id": None,
                "success": None,
                "reward": None,
                "termination_reason": None,
            })
    token_usage = {
        key: sum(item["token_usage"][key] for item in episodes)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    elapsed = sum(
        (datetime.fromisoformat(item["finished_at"]) - datetime.fromisoformat(item["started_at"])).total_seconds()
        for item in summaries
    )
    result: dict[str, Any] = {
        "schema": contract.RESULT_SCHEMA,
        "status": "TERMINAL_VALID_SCIENTIFIC_FAILURE",
        "completion": "GATE_STOPPED_2_OF_6",
        "scientific_valid": True,
        "identity": {
            "suite_id": checkpoint["suite_id"],
            "prospective_arm": "sys_nag",
            "system_id": contract.SYSTEM_ID,
            "mechanism_id": contract.MECHANISM_ID,
            "experiment_id": contract.EXPERIMENT_ID,
            "task_seed": contract.TASK_SEED,
            "generation_seed": contract.GENERATION_SEED,
            "implementation_commit": frozen["implementation_commit"],
            "source_freeze_content_sha256": frozen["source_freeze_content_sha256"],
        },
        "closure": {
            "source_checkpoint_status": TERMINAL_STATUS,
            "valid_episode_count": 2,
            "invalid_attempt_count": 0,
            "not_run_by_protocol_count": 17,
            "raw_episode_file_bindings_valid": True,
            "checkpoint_summaries_equal_raw_episodes": True,
            "checkpoint_entry_summary_hashes_valid": True,
            "single_transport_per_call": True,
            "generation_calls_during_finalization": 0,
            "network_calls_during_finalization": 0,
            "raw_episode_or_checkpoint_modified": False,
        },
        "capability_gate": checkpoint["capability_gate"],
        "performance_observed_partial": {
            "success_count": 1,
            "reward_sum": 1.5,
            "model_calls": sum(item["model_calls"] for item in episodes),
            "executed_actions": sum(item["executed_actions"] for item in episodes),
            "token_usage": token_usage,
            "valid_elapsed_seconds": elapsed,
        },
        "verdicts": {
            "accuracy": "FAIL_CAPABILITY_GATE",
            "mechanism": "NOT_ACTIVATED_IN_TWO_EXECUTED_TASKS",
            "causal_guard_benefit_claim_permitted": False,
            "causal_guard_harm_claim_permitted": False,
            "continuation_authorized": False,
            "same_identity_rerun_authorized": False,
        },
        "guard_observed": {
            "review_count": sum(item["model_calls"] for item in episodes),
            "eligible_count": 0,
            "override_count": 0,
            "extra_model_calls": 0,
        },
        "tasks": rows,
        "integrity": {
            **frozen,
            "run_signature_canonical_sha256": signature_sha,
            "checkpoint_file_sha256": file_sha256(suite / "checkpoint.json"),
            "episode_closure": episodes,
            "evidence_integrity_status": "PASS",
            "disclosed_metadata_defects": defects,
        },
        "finalization": {
            "classification": "POST_HOC_CPU_ONLY_EVIDENCE_LAYER",
            "reason": "terminal_gate_exception_preceded_runner_aggregate_branch",
            "frozen_experiment_behavior_changed": False,
            "known_stale_run_signature_labels": ["task_order", "A0_preservation_tasks"],
        },
        "errors": [],
    }
    _require(sum(row["execution_status"] == "NOT_RUN_BY_PROTOCOL" for row in rows) == 17, "result_unrun_count")
    _require(math.isfinite(elapsed) and elapsed >= 0, "result_elapsed")
    result["content_sha256"] = content_sha256(result)
    return result


def finalize(suite: Path, receipt: Path) -> dict[str, Any]:
    suite = suite.resolve()
    _require(suite.is_dir(), "suite_missing")
    signature, signature_sha = validate_run_signature(suite)
    checkpoint, defects = validate_checkpoint(suite, signature_sha)
    validate_gate(checkpoint)
    episodes = [
        validate_episode(suite, summary, entry, signature_sha)
        for summary, entry in zip(
            checkpoint["valid_summaries"], checkpoint["sys_nag_valid_entries"], strict=True
        )
    ]
    frozen = validate_frozen_evidence(suite, signature, checkpoint, receipt.resolve())
    return build_result(suite, signature_sha, checkpoint, defects, episodes, frozen)


def write_result(output: Path, suite: Path, result: dict[str, Any]) -> None:
    output = output.resolve()
    try:
        output.relative_to(suite.resolve())
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
    parser.add_argument("--suite-dir", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = finalize(args.suite_dir, args.receipt)
    write_result(args.output, args.suite_dir, result)
    print(json.dumps({
        "output": str(args.output.resolve()),
        "status": result["status"],
        "content_sha256": result["content_sha256"],
        "valid_episode_count": result["closure"]["valid_episode_count"],
        "not_run_by_protocol_count": result["closure"]["not_run_by_protocol_count"],
        "generation_calls_during_finalization": 0,
        "network_calls_during_finalization": 0,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
