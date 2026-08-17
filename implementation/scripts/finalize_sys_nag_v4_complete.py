#!/usr/bin/env python3
"""CPU-only finalizer for the completed SYS-NAG V4 live suite.

The live runner completed all 19 valid episodes and then raised in a legacy
aggregate branch before it could write ``aggregate.json`` or a final
checkpoint.  This evidence-layer finalizer never calls the model, Android, or
the network.  It accepts only the byte-pinned raw checkpoint produced by that
run and reconstructs the result from the independently hashed
entry/episode/event/artifact closure.
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

from raven_m.official_qwen_mobile import sys_nag_contract as contract  # noqa: E402


DEFAULT_SUITE = ROOT / "runs/sys_nag_v4/official_qwen_20260816T041833_e5618ea5"
DEFAULT_RECEIPT = ROOT / "evidence/sys_nag_v4/SYS_NAG_V4_LIVE_RECEIPT.json"
DEFAULT_OUTPUT = ROOT / "evidence/sys_nag_v4/SYS_NAG_V4_COMPLETE_RESULT_2026-08-18.json"

RAW_CHECKPOINT_FILE_SHA256 = "ce9024abbbefad754666f8e6f488ccbaaf4f83d5010cd75f05729e781dab353d"
RAW_CHECKPOINT_CONTENT_SHA256 = "a1d88d3abe84b25092d1c06e2106eb0a66b64b200271b180c88f2372a220d600"
RUN_SIGNATURE_FILE_SHA256 = "88d9c90e48bd5f9818004a63d95b0baa741048636298bdb23a66b247225dddb0"
MANIFEST_SNAPSHOT_FILE_SHA256 = "c1d718e9d380e443d12d2c29ab2182ae801a3befc53881b864cd830f2ad0440a"
IMPLEMENTATION_COMMIT = "f0db557a2238901e5c7af6981e9ba4ae2fbf0abc"
FINALIZATION_EXCEPTION = "KeyError: 'reference_segments_path'"


class FinalizationError(RuntimeError):
    """Raw evidence failed the frozen V4 reconstruction contract."""


def _fail(code: str) -> None:
    raise FinalizationError(f"SYS-NAG V4 finalization failed: {code}")


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
        raise FinalizationError(f"SYS-NAG V4 finalization failed: {code}") from exc
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


def validate_signature(suite: Path) -> tuple[dict[str, Any], str]:
    path = suite / "run_signature.json"
    _require(file_sha256(path) == RUN_SIGNATURE_FILE_SHA256, "signature_file_hash")
    signature = _load(path, "signature_unreadable")
    expected = {
        "prospective_arm": "sys_nag",
        "system_id": contract.SYSTEM_ID,
        "mechanism_id": contract.MECHANISM_ID,
        "experiment_id": contract.EXPERIMENT_ID,
        "generation_seed": contract.GENERATION_SEED,
        "task_order": "blocking_A1R2_success_6_then_frozen_manifest_remainder",
        "capability_gate_tasks": list(contract.CAPABILITY_GATE_TASKS),
        "response_prefix_required": True,
        "system_prompt_identity": "exact_A1_WORKING_MEMORY_SYSTEM_PROMPT",
        "official_system_prompt_unchanged": False,
        "guard": True,
        "action_override": True,
        "numeric_answer_override": True,
        "pending_terminal_suppression": True,
        "route_recurrence_suppression": True,
        "auxiliary_model_calls": 0,
        "forced_termination": False,
        "reward_fail_fast": True,
        "scientific_failure_rerun": False,
        "model_id": contract.MODEL_ID,
        "model_revision": contract.MODEL_REVISION,
    }
    for key, value in expected.items():
        _require(signature.get(key) == value, f"signature_{key}")
    keys = [[name, contract.TASK_SEED] for name in contract.FULL_TASK_ORDER]
    _require(signature.get("ordered_expected_keys") == keys, "signature_task_order")
    _require(
        signature.get("ordered_expected_keys_sha256") == canonical_sha256(keys),
        "signature_task_order_hash",
    )
    _require(
        file_sha256(suite / "manifest.snapshot.json") == MANIFEST_SNAPSHOT_FILE_SHA256,
        "manifest_snapshot_hash",
    )
    _require(
        signature.get("manifest_sha256") == MANIFEST_SNAPSHOT_FILE_SHA256,
        "signature_manifest_hash",
    )
    return signature, canonical_sha256(signature)


def validate_checkpoint(
    suite: Path, signature_sha: str
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    path = suite / "checkpoint.json"
    _require(file_sha256(path) == RAW_CHECKPOINT_FILE_SHA256, "checkpoint_file_hash")
    checkpoint = _load(path, "checkpoint_unreadable")
    expected = {
        "schema": contract.CHECKPOINT_SCHEMA,
        "status": "running",
        "suite_id": suite.name,
        "prospective_arm": "sys_nag",
        "system_id": contract.SYSTEM_ID,
        "mechanism_id": contract.MECHANISM_ID,
        "experiment_id": contract.EXPERIMENT_ID,
        "run_signature_sha256": signature_sha,
    }
    for key, value in expected.items():
        _require(checkpoint.get(key) == value, f"checkpoint_{key}")
    _require(
        checkpoint.get("content_sha256") == RAW_CHECKPOINT_CONTENT_SHA256,
        "checkpoint_digest_value",
    )
    _require(
        content_sha256(checkpoint) == RAW_CHECKPOINT_CONTENT_SHA256,
        "checkpoint_content_digest",
    )
    summaries = list(checkpoint.get("valid_summaries") or [])
    entries = list(checkpoint.get("sys_nag_valid_entries") or [])
    _require(len(summaries) == len(entries) == 19, "checkpoint_valid_cardinality")
    _require(
        [row.get("task_name") for row in summaries] == list(contract.FULL_TASK_ORDER),
        "checkpoint_task_order",
    )
    gate = checkpoint.get("capability_gate") or {}
    _require(
        gate.get("required") == 6
        and gate.get("status") == "pass"
        and gate.get("success_count") == 6,
        "checkpoint_capability_gate",
    )
    _require(
        [row.get("task_name") for row in gate.get("tasks") or []]
        == list(contract.CAPABILITY_GATE_TASKS),
        "checkpoint_gate_order",
    )
    for index, (summary, entry) in enumerate(zip(summaries, entries, strict=True)):
        for key in ("episode_id", "task_name", "seed"):
            _require(entry.get(key) == summary.get(key), f"entry_{index}_{key}")
        _require(entry.get("run_signature_sha256") == signature_sha, f"entry_{index}_signature")
        _require(entry.get("summary_sha256") == canonical_sha256(summary), f"entry_{index}_summary")
    return checkpoint, summaries, entries


def _validate_observation(episode_dir: Path, observation: dict[str, Any], code: str) -> set[str]:
    names: set[str] = set()
    screen = _safe_child(episode_dir, observation.get("screenshot"), code + "_screen_path")
    ui = _safe_child(episode_dir, observation.get("ui_record"), code + "_ui_path")
    _require(screen.is_file() and file_sha256(screen) == observation.get("screenshot_sha256"), code + "_screen")
    _require(ui.is_file(), code + "_ui_missing")
    _require(canonical_sha256(json.loads(ui.read_text(encoding="utf-8"))) == observation.get("ui_sha256"), code + "_ui")
    names.update((screen.name, ui.name))
    return names


def validate_episode(
    suite: Path, summary: dict[str, Any], entry: dict[str, Any], signature_sha: str
) -> dict[str, Any]:
    episode_id = str(summary.get("episode_id") or "")
    episode_dir = _safe_child(suite / "episodes", episode_id, "episode_dir")
    episode_path = episode_dir / "episode.json"
    _require(episode_path.is_file(), "episode_json_missing")
    _require(file_sha256(episode_path) == entry.get("episode_json_sha256"), "episode_json_hash")
    episode = _load(episode_path, "episode_json_unreadable")
    _require(episode == summary, "episode_summary_drift")
    metadata = summary.get("run_metadata") or {}
    _require(metadata.get("run_signature_sha256") == signature_sha, "episode_signature")
    _require(metadata.get("memory_intervention") == contract.MECHANISM_ID, "episode_mechanism")
    _require(summary.get("error") is None, "episode_error")
    _require(not (summary.get("lifecycle_errors") or []), "episode_lifecycle_error")
    reward = summary.get("evaluator_reward")
    _require(isinstance(reward, (int, float)) and math.isfinite(reward), "episode_reward")

    steps = list(summary.get("steps") or [])
    calls = int(summary.get("model_call_count") or 0)
    _require(len(steps) == calls == int(summary.get("step_count") or -1), "episode_call_count")
    executed = sum(bool(step.get("executed")) for step in steps)
    _require(executed == int(summary.get("executed_action_count") or 0), "episode_executed_count")
    guard = summary.get("answer_consistency_guard") or {}
    counters = guard.get("counters") or {}
    events = list(guard.get("events") or [])
    _require(guard.get("schema") == "sys_nag_v4_composite_guard_audit_v1", "guard_schema")
    _require(guard.get("system_id") == contract.SYSTEM_ID, "guard_system_id")
    _require(counters.get("review_count") == calls == len(events), "guard_review_count")
    _require(int(counters.get("auxiliary_model_call_count") or 0) == 0, "guard_aux_calls")
    _require(int(counters.get("forced_termination_count") or 0) == 0, "guard_forced_termination")
    _require(not bool(counters.get("hidden_ui_used_for_decision")), "guard_hidden_ui")
    _require(not bool(counters.get("evaluator_used_for_decision")), "guard_evaluator")
    route_blocks = int(counters.get("route_block_count") or 0)
    terminal_blocks = int(counters.get("terminal_block_count") or 0)
    _require(route_blocks in {0, 1} and terminal_blocks in {0, 1}, "guard_block_cap")
    _require(route_blocks + terminal_blocks <= 1, "guard_shared_block_cap")

    tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    latency = 0.0
    artifact_names = {"episode.json", "events.jsonl"}
    call_ids: set[str] = set()
    for index, step in enumerate(steps):
        _require(step.get("step") == index, f"step_{index}_ordinal")
        call = step.get("model_call") or {}
        meta = call.get("raven_meta") or {}
        runtime = (step.get("layers") or {}).get("L0_runtime") or {}
        _require(meta.get("transport_attempts") == 1, f"step_{index}_transport")
        _require(runtime.get("transport_attempts") == 1, f"step_{index}_runtime_transport")
        call_id = str(call.get("call_id") or "")
        _require(call_id and call_id not in call_ids, f"step_{index}_call_id")
        call_ids.add(call_id)
        usage = call.get("usage") or {}
        values = [usage.get(key) for key in tokens]
        _require(all(isinstance(value, int) and value >= 0 for value in values), f"step_{index}_usage")
        _require(values[0] + values[1] == values[2], f"step_{index}_usage_sum")
        for key, value in zip(tokens, values, strict=True):
            tokens[key] += value
        observed_latency = runtime.get("latency_seconds")
        _require(isinstance(observed_latency, (int, float)) and math.isfinite(observed_latency) and observed_latency >= 0, f"step_{index}_latency")
        latency += float(observed_latency)
        _require((step.get("answer_consistency_guard") or {}) == events[index], f"step_{index}_guard_event")
        before = step.get("before") or {}
        _require(bool(before), f"step_{index}_before_missing")
        artifact_names |= _validate_observation(episode_dir, before, f"step_{index}_before")
        after = step.get("after") or {}
        if after:
            artifact_names |= _validate_observation(episode_dir, after, f"step_{index}_after")
        else:
            _require(not bool(step.get("executed")), f"step_{index}_after_missing")

    events_path = episode_dir / "events.jsonl"
    try:
        disk_events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FinalizationError("SYS-NAG V4 finalization failed: events_unreadable") from exc
    step_events = [event for event in disk_events if event.get("event") == "step"]
    _require(len(step_events) == calls, "events_step_count")
    for index, event in enumerate(step_events):
        event = dict(event)
        event.pop("time", None)
        _require(event == steps[index], f"events_step_{index}")
    evaluator = [event for event in disk_events if event.get("event") == "evaluator_result"]
    complete = [event for event in disk_events if event.get("event") == "episode_complete"]
    _require(len(evaluator) == len(complete) == 1, "events_terminal_cardinality")
    _require(evaluator[0].get("reward") == reward, "events_reward")
    _require(complete[0].get("success") == summary.get("success"), "events_success")
    observed_names = {path.name for path in episode_dir.iterdir() if path.is_file()}
    _require(observed_names == artifact_names, "episode_artifact_set")
    blocked_steps = [
        index
        for index, event in enumerate(guard.get("route_events") or [])
        if bool(event.get("blocked"))
    ]
    _require(len(blocked_steps) == route_blocks, "route_block_event_count")
    return {
        "task_name": summary["task_name"],
        "episode_id": episode_id,
        "episode_json_file_sha256": file_sha256(episode_path),
        "summary_canonical_sha256": canonical_sha256(summary),
        "events_jsonl_file_sha256": file_sha256(events_path),
        "artifact_file_count": len(observed_names),
        "reward": float(reward),
        "success": bool(summary.get("success")),
        "model_calls": calls,
        "executed_actions": executed,
        "model_latency_seconds": latency,
        "token_usage": tokens,
        "route_block_count": route_blocks,
        "route_block_steps": blocked_steps,
        "terminal_block_count": terminal_blocks,
        "numeric_override_count": int(counters.get("action_override_count") or 0),
        "live_receipt_file_sha256": metadata.get("live_server_receipt_sha256"),
    }


def validate_invalid_attempts(
    suite: Path, checkpoint: dict[str, Any], replacement_episode_id: str
) -> list[dict[str, Any]]:
    attempts = list(checkpoint.get("invalid_attempts") or [])
    _require(len(attempts) == 2, "invalid_attempt_count")
    first, second = attempts
    _require(first.get("reason") == "external_runner_interruption", "invalid_0_reason")
    _require(second.get("reason") == "controller_or_lifecycle_invalid", "invalid_1_reason")
    for index, attempt in enumerate(attempts):
        _require(attempt.get("task_name") == "RetroSavePlaylist", f"invalid_{index}_task")
        _require(attempt.get("seed") == contract.TASK_SEED, f"invalid_{index}_seed")
        _require(attempt.get("resolved_by_episode_id") == replacement_episode_id, f"invalid_{index}_resolution")

    artifact_ref = first.get("artifact") or {}
    artifact_path = _safe_child(suite, artifact_ref.get("path"), "invalid_0_artifact_path")
    _require(artifact_path.is_file(), "invalid_0_artifact_missing")
    _require(file_sha256(artifact_path) == artifact_ref.get("file_sha256"), "invalid_0_artifact_file_hash")
    artifact = _load(artifact_path, "invalid_0_artifact_unreadable")
    _require(content_sha256(artifact) == artifact_ref.get("content_sha256"), "invalid_0_artifact_content_hash")
    _require(artifact.get("scientific_outcome_valid") is False, "invalid_0_scientific_outcome")
    partial_dir = _safe_child(suite / "episodes", first.get("episode_id"), "invalid_0_episode_dir")
    expected_files = {str(row.get("name")) for row in artifact.get("files") or []}
    observed_files = {path.name for path in partial_dir.iterdir() if path.is_file()}
    _require(expected_files == observed_files, "invalid_0_file_set")
    for row in artifact.get("files") or []:
        path = _safe_child(partial_dir, row.get("name"), "invalid_0_file_path")
        _require(path.stat().st_size == row.get("bytes"), "invalid_0_file_size")
        _require(file_sha256(path) == row.get("sha256"), "invalid_0_file_hash")

    invalid_episode_path = _safe_child(
        suite / "episodes", second.get("episode_id"), "invalid_1_episode_dir"
    ) / "episode.json"
    invalid_episode = _load(invalid_episode_path, "invalid_1_episode_unreadable")
    _require(invalid_episode.get("model_call_count") == 0, "invalid_1_generation_count")
    _require(invalid_episode.get("step_count") == 0 and invalid_episode.get("steps") == [], "invalid_1_steps")
    _require(invalid_episode.get("termination_reason") == "infrastructure_or_controller_error", "invalid_1_termination")
    _require(not invalid_episode.get("success") and invalid_episode.get("evaluator_reward") is None, "invalid_1_scientific_outcome")
    return [
        {
            "episode_id": first["episode_id"],
            "reason": first["reason"],
            "resolved_by_episode_id": replacement_episode_id,
            "scientific_outcome_valid": False,
            "generation_calls": 3,
            "artifact_file_sha256": artifact_ref["file_sha256"],
            "artifact_content_sha256": artifact_ref["content_sha256"],
            "partial_file_count": len(expected_files),
        },
        {
            "episode_id": second["episode_id"],
            "reason": second["reason"],
            "resolved_by_episode_id": replacement_episode_id,
            "scientific_outcome_valid": False,
            "generation_calls": 0,
            "episode_json_file_sha256": file_sha256(invalid_episode_path),
        },
    ]


def validate_frozen_evidence(
    suite: Path, signature: dict[str, Any], checkpoint: dict[str, Any], receipt_path: Path
) -> dict[str, Any]:
    freeze = _load(contract.SOURCE_FREEZE_PATH, "source_freeze_unreadable")
    preflight = _load(contract.PREFLIGHT_PATH, "preflight_unreadable")
    replay = _load(contract.OFFLINE_REPLAY_PATH, "replay_unreadable")
    fixture = _load(contract.REPLAY_FIXTURE_PATH, "fixture_unreadable")
    receipt = _load(receipt_path, "receipt_unreadable")
    for label, value in (("freeze", freeze), ("preflight", preflight), ("replay", replay), ("fixture", fixture), ("receipt", receipt)):
        _require(value.get("content_sha256") == content_sha256(value), label + "_content_hash")
    _require(freeze.get("implementation_commit") == IMPLEMENTATION_COMMIT, "freeze_commit")
    _require(freeze.get("parent_evidence_commit") == contract.PARENT_EVIDENCE_COMMIT, "freeze_parent")
    _require(freeze.get("files") == {key: freeze["files"][key] for key in contract.SOURCE_FILES}, "freeze_source_set")
    for relative, expected_sha in freeze["files"].items():
        try:
            blob = subprocess.run(
                ["git", "show", f"{IMPLEMENTATION_COMMIT}:{relative}"],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            raise FinalizationError("SYS-NAG V4 finalization failed: freeze_git_blob") from exc
        _require(sha256(blob).hexdigest() == expected_sha, f"freeze_blob:{relative}")
    _require(
        replay.get("schema") == contract.OFFLINE_REPLAY_SCHEMA
        and replay.get("status") == "PASS"
        and replay.get("errors") == []
        and replay.get("generation_calls") == 0
        and replay.get("system_id") == contract.SYSTEM_ID
        and int((replay.get("totals") or {}).get("valid_episode_count") or 0) == 19,
        "replay_authorization",
    )
    _require(
        preflight.get("schema") == contract.PREFLIGHT_SCHEMA
        and preflight.get("status") == "PASS"
        and preflight.get("errors") == []
        and preflight.get("generation_calls") == 0
        and preflight.get("live_generation_authorized") is True
        and preflight.get("system_id") == contract.SYSTEM_ID
        and preflight.get("source_freeze_content_sha256") == freeze.get("content_sha256")
        and preflight.get("offline_replay_content_sha256") == replay.get("content_sha256"),
        "preflight_authorization",
    )
    _require(file_sha256(receipt_path) == checkpoint["live_server_receipt_sha256s"][-1], "receipt_file_hash")
    expected_receipt = {
        "schema": contract.LIVE_RECEIPT_SCHEMA,
        "status": "PASS",
        "errors": [],
        "generation_calls": 0,
        "system_id": contract.SYSTEM_ID,
        "mechanism_id": contract.MECHANISM_ID,
        "experiment_id": contract.EXPERIMENT_ID,
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "preflight_content_sha256": preflight["content_sha256"],
        "served_model_id": contract.MODEL_ID,
        "model_realpath": contract.MODEL_REALPATH,
        "model_manifest_sha256": contract.MODEL_MANIFEST_SHA256,
        "port": contract.PORT,
    }
    for key, value in expected_receipt.items():
        _require(receipt.get(key) == value, f"receipt_{key}")
    _require(signature.get("prospective_source_freeze_sha256") == freeze["content_sha256"], "signature_freeze")
    _require(signature.get("prospective_preflight_sha256") == file_sha256(contract.PREFLIGHT_PATH), "signature_preflight")
    receipt_hashes = list(checkpoint.get("live_server_receipt_sha256s") or [])
    _require(len(receipt_hashes) == 2 and len(set(receipt_hashes)) == 2, "checkpoint_receipt_chain")
    return {
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "source_freeze_content_sha256": freeze["content_sha256"],
        "source_freeze_file_sha256": file_sha256(contract.SOURCE_FREEZE_PATH),
        "offline_replay_content_sha256": replay["content_sha256"],
        "offline_replay_file_sha256": file_sha256(contract.OFFLINE_REPLAY_PATH),
        "replay_fixture_content_sha256": fixture["content_sha256"],
        "replay_fixture_file_sha256": file_sha256(contract.REPLAY_FIXTURE_PATH),
        "preflight_content_sha256": preflight["content_sha256"],
        "preflight_file_sha256": file_sha256(contract.PREFLIGHT_PATH),
        "current_live_receipt_content_sha256": receipt["content_sha256"],
        "current_live_receipt_file_sha256": file_sha256(receipt_path),
        "live_receipt_file_sha256_chain": receipt_hashes,
        "prior_live_receipt_file_available": False,
    }


def build_result(
    suite: Path,
    signature_sha: str,
    checkpoint: dict[str, Any],
    episodes: list[dict[str, Any]],
    invalids: list[dict[str, Any]],
    frozen: dict[str, Any],
) -> dict[str, Any]:
    success_count = sum(item["success"] for item in episodes)
    reward_sum = sum(item["reward"] for item in episodes)
    token_usage = {
        key: sum(item["token_usage"][key] for item in episodes)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    route_rows = [item for item in episodes if item["route_block_count"]]
    _require(success_count == 6 and reward_sum == 6.5, "result_performance")
    _require(len(route_rows) == 4 and not any(item["success"] for item in route_rows), "result_route_outcomes")
    _require(sum(item["terminal_block_count"] for item in episodes) == 0, "result_terminal_blocks")
    _require(sum(item["numeric_override_count"] for item in episodes) == 0, "result_numeric_overrides")
    r2 = _load(ROOT / "evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.json", "r2_result_unreadable")
    r2_performance = (r2.get("a1r2_result") or {}).get("performance") or {}
    _require(r2_performance.get("success_count") == 6 and r2_performance.get("reward_sum") == 6.5, "r2_reference_performance")
    result: dict[str, Any] = {
        "schema": "sys_nag_v4_posthoc_complete_result_v1",
        "status": "COMPLETE_19_VALID_EPISODES_POSTHOC_FINALIZED_AFTER_AGGREGATION_BUG",
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
        },
        "closure": {
            "raw_checkpoint_status": "running",
            "valid_episode_count": 19,
            "invalid_attempt_count": 2,
            "resolved_invalid_attempt_count": 2,
            "raw_episode_file_bindings_valid": True,
            "checkpoint_entries_and_summary_hashes_valid": True,
            "single_transport_per_valid_call": True,
            "all_artifact_hashes_valid": True,
            "generation_calls_during_finalization": 0,
            "network_calls_during_finalization": 0,
            "android_actions_during_finalization": 0,
            "raw_suite_modified": False,
        },
        "performance": {
            "success_count": success_count,
            "reward_sum": reward_sum,
            "model_calls": sum(item["model_calls"] for item in episodes),
            "executed_actions": sum(item["executed_actions"] for item in episodes),
            "token_usage": token_usage,
            "valid_episode_model_latency_seconds": sum(item["model_latency_seconds"] for item in episodes),
        },
        "paired_reference": {
            "reference": "A1-R2",
            "reference_result_file_sha256": file_sha256(ROOT / "evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.json"),
            "reference_success_count": 6,
            "reference_reward_sum": 6.5,
            "success_delta": 0,
            "reward_delta": 0.0,
        },
        "interventions": {
            "route_block_count": len(route_rows),
            "route_block_tasks": [item["task_name"] for item in route_rows],
            "route_block_full_success_count": 0,
            "terminal_block_count": 0,
            "numeric_override_count": 0,
            "auxiliary_model_call_count": 0,
        },
        "verdicts": {
            "accuracy": "NO_ACCURACY_GAIN_OVER_A1R2",
            "task_level_route_component": "ACTIVATED_FOUR_EPISODES_WITH_ZERO_NEW_FULL_SUCCESS",
            "terminal_component": "NOT_ACTIVATED",
            "numeric_component": "NOT_ACTIVATED",
            "successful_episodes_attributable_to_new_v4_components": 0,
            "causal_benefit_claim_permitted": False,
            "same_identity_rerun_authorized": False,
        },
        "tasks": episodes,
        "invalid_attempts": invalids,
        "integrity": {
            **frozen,
            "run_signature_canonical_sha256": signature_sha,
            "run_signature_file_sha256": RUN_SIGNATURE_FILE_SHA256,
            "manifest_snapshot_file_sha256": MANIFEST_SNAPSHOT_FILE_SHA256,
            "raw_checkpoint_file_sha256": RAW_CHECKPOINT_FILE_SHA256,
            "raw_checkpoint_content_sha256": RAW_CHECKPOINT_CONTENT_SHA256,
            "evidence_integrity_status": "PASS",
        },
        "disclosed_defects": [
            {
                "code": "LEGACY_AGGREGATE_REFERENCE_SEGMENTS_KEYERROR",
                "exception": FINALIZATION_EXCEPTION,
                "scope": "post_episode_result_aggregation_only",
                "scientific_episode_effect": False,
                "handling": "independent_cpu_only_posthoc_finalizer",
            },
            {
                "code": "PRIOR_LIVE_RECEIPT_FILE_NOT_RETAINED",
                "scope": "first_valid_episode_receipt_object",
                "scientific_episode_effect": False,
                "handling": "preserve_file_sha_chain_and_episode_binding; fully_validate_current_receipt_and_frozen_stable_identity",
            },
        ],
        "finalization": {
            "classification": "POST_HOC_CPU_ONLY_EVIDENCE_LAYER",
            "frozen_experiment_behavior_changed": False,
            "raw_checkpoint_promoted_or_rewritten": False,
            "reason": "all_19_valid_episodes_preceded_legacy_aggregate_exception",
        },
        "errors": [],
    }
    result["content_sha256"] = content_sha256(result)
    return result


def finalize(suite: Path, receipt: Path) -> dict[str, Any]:
    suite = suite.resolve()
    _require(suite.is_dir(), "suite_missing")
    signature, signature_sha = validate_signature(suite)
    checkpoint, summaries, entries = validate_checkpoint(suite, signature_sha)
    episodes = [
        validate_episode(suite, summary, entry, signature_sha)
        for summary, entry in zip(summaries, entries, strict=True)
    ]
    replacement = summaries[1]["episode_id"]
    invalids = validate_invalid_attempts(suite, checkpoint, replacement)
    frozen = validate_frozen_evidence(suite, signature, checkpoint, receipt.resolve())
    return build_result(suite, signature_sha, checkpoint, episodes, invalids, frozen)


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
        "success_count": result["performance"]["success_count"],
        "reward_sum": result["performance"]["reward_sum"],
        "generation_calls_during_finalization": 0,
        "network_calls_during_finalization": 0,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
