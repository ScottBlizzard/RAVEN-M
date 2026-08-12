"""Frozen scientific contract for the A10 ECOBF experiment."""

from __future__ import annotations

from hashlib import sha256
import json
import math
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
OFFICIAL_SYSTEM_PROMPT_SHA256 = "9d060af15f62acb31b9fb197649ec001d4096491d7fb102de929316944b3e26d"
TASK_SEED = 20260806
GENERATION_SEED = 3407
TASK_COUNT = 19
PARENT_EVIDENCE_COMMIT = "ee6df0d11e8e45a903ec291e5a2dbe7fbacb60aa"
MECHANISM_ID = "a10_evidence_calibrated_obligation_branch_frontier_v1"
EXPERIMENT_ID = "A10_ECOBF_QWEN3VL32B_AW_HARD_S20260806_V1"
MODEL_REALPATH = "/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope"
MODEL_MANIFEST_SHA256 = "18e0909c7d993853d6d0f62443461a74009754f90db026a1723cab80121c7872"
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
CONFIG_PATH = REPOSITORY_ROOT / "implementation/configs/a10_evidence_calibrated_obligation_branch_frontier_hard_seed20260806.json"
PREFLIGHT_PATH = REPOSITORY_ROOT / "evidence/a10/A10_ZERO_GENERATION_PREFLIGHT.json"
LIVE_RECEIPT_PATH = REPOSITORY_ROOT / "evidence/a10/A10_LIVE_SERVER_RECEIPT.json"

A0_PRESERVATION_TASKS = (
    "ExpenseDeleteMultiple2",
    "RetroSavePlaylist",
    "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
)

REMAINING_TASKS = (
    "BrowserMultiply",
    "ExpenseAddMultipleFromGallery",
    "ExpenseAddMultipleFromMarkor",
    "MarkorCreateNoteAndSms",
    "MarkorMergeNotes",
    "MarkorTranscribeVideo",
    "OsmAndMarker",
    "OsmAndTrack",
    "RecipeAddMultipleRecipesFromImage",
    "RecipeAddMultipleRecipesFromMarkor",
    "RecipeAddMultipleRecipesFromMarkor2",
    "RecipeDeleteMultipleRecipesWithConstraint",
    "SaveCopyOfReceiptTaskEval",
    "SportsTrackerActivitiesOnDate",
    "SportsTrackerTotalDistanceForCategoryOverInterval",
)

SOURCE_FILES = (
    "GPT_PRO_A10_STANDALONE_MEMORY_DESIGN_2026-08-12.md",
    "implementation/configs/androidworld_hard_v2_instances.json",
    "implementation/configs/a10_evidence_calibrated_obligation_branch_frontier_hard_seed20260806.json",
    "implementation/src/raven_m/official_qwen_mobile/a10_obligation_branch_frontier.py",
    "implementation/src/raven_m/official_qwen_mobile/a10_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/official_qwen_mobile/protocol.py",
    "implementation/src/raven_m/official_qwen_mobile/working_memory.py",
    "implementation/src/raven_m/official_qwen_mobile/a678_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/a7_continuation.py",
    "implementation/src/raven_m/official_qwen_mobile/__init__.py",
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/run_a678_arm.py",
    "implementation/scripts/preflight_a10.py",
    "implementation/scripts/replay_a10_offline_traces.py",
    "implementation/scripts/qualify_a10_live_server.py",
    "implementation/scripts/start_a10_server.sh",
    "implementation/src/raven_m/models/vllm_client.py",
    "implementation/src/raven_m/env/androidworld_adapter.py",
    "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    "implementation/tests/official_qwen_mobile/test_a10_obligation_branch_frontier.py",
    "implementation/tests/official_qwen_mobile/test_a10_controller_integration.py",
    "implementation/tests/official_qwen_mobile/test_a10_contract.py",
    "implementation/tests/official_qwen_mobile/test_a10_offline_replay.py",
    "evidence/a10/A10_FROZEN_QUERY_SET.json",
    "evidence/a10/A10_OFFLINE_TRACE_SOURCE_SPEC.json",
    "evidence/a10/A10_OFFLINE_TRACE_MANIFEST.json",
    "evidence/a10/A10_OFFLINE_REPLAY_REPORT.json",
    "evidence/a2/A0_A1_PAIRED_REFERENCE_20260810.json",
    "evidence/a678/A8_V2_OFFLINE_TRACE_AUDIT_2026-08-11.json",
    "evidence/a678/A89_INITIAL_GATE_RESULTS_2026-08-12.json",
    "protocols/A10_ECOBF_IMPLEMENTATION_BINDING_2026-08-12.md",
)


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def json_sha256(value: Any) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def current_source_freeze() -> dict[str, str]:
    missing = [name for name in SOURCE_FILES if not (REPOSITORY_ROOT / name).is_file()]
    if missing:
        raise RuntimeError(f"A10 source closure incomplete: {missing}")
    return {name: file_sha256(REPOSITORY_ROOT / name) for name in SOURCE_FILES}


def validate_preflight_report(path: Path = PREFLIGHT_PATH) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    current = current_source_freeze()
    errors: list[str] = []
    if report.get("schema") != "a10_zero_generation_preflight_v1":
        errors.append("schema_drift")
    if report.get("status") != "pass" or report.get("generation_calls") != 0:
        errors.append("status_or_generation_calls_invalid")
    if report.get("errors"):
        errors.append("preflight_errors_nonempty")
    if report.get("source_freeze") != current:
        errors.append("source_freeze_drift")
    if report.get("source_freeze_sha256") != json_sha256(current):
        errors.append("source_freeze_digest_drift")
    if report.get("parent_evidence_commit") != PARENT_EVIDENCE_COMMIT:
        errors.append("parent_evidence_commit_drift")
    if not str(report.get("a10_implementation_commit") or ""):
        errors.append("implementation_commit_missing")
    if errors:
        raise RuntimeError(f"A10 preflight validation failed: {errors}")
    return report


def validate_launch_receipt(path: Path, *, preflight_path: Path = PREFLIGHT_PATH) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    preflight = validate_preflight_report(preflight_path)
    expected = {
        "schema": "a10_live_server_receipt_v1",
        "status": "pass",
        "generation_calls": 0,
        "served_model_id": MODEL_ID,
        "model_realpath": MODEL_REALPATH,
        "model_manifest_sha256": MODEL_MANIFEST_SHA256,
        "port": 18000,
        "a10_preflight_sha256": file_sha256(preflight_path),
        "a10_source_freeze_sha256": preflight["source_freeze_sha256"],
    }
    errors = [f"{key}_drift" for key, value in expected.items() if receipt.get(key) != value]
    cmdline = [str(item) for item in receipt.get("process_cmdline") or []]
    if MODEL_REALPATH not in cmdline or MODEL_ID not in cmdline or "serve" not in cmdline:
        errors.append("process_cmdline_binding_missing")
    packages = receipt.get("packages") or {}
    if not all(str(packages.get(name) or "") for name in ("vllm", "torch", "transformers")):
        errors.append("runtime_packages_missing")
    if receipt.get("served_model_ids_observed") != [MODEL_ID]:
        errors.append("served_model_ids_observed_drift")
    launch_intent_path = Path(str(receipt.get("launch_intent_path") or ""))
    if (
        not launch_intent_path.is_file()
        or receipt.get("launch_intent_sha256") != file_sha256(launch_intent_path)
    ):
        errors.append("launch_intent_artifact_hash_mismatch")
    else:
        try:
            launch_intent = json.loads(launch_intent_path.read_text(encoding="utf-8"))
            if cmdline != [str(item) for item in launch_intent.get("command") or []]:
                errors.append("launch_intent_process_command_mismatch")
            if launch_intent.get("a10_preflight_sha256") != file_sha256(preflight_path):
                errors.append("launch_intent_preflight_hash_drift")
            if launch_intent.get("a10_source_freeze_sha256") != preflight.get("source_freeze_sha256"):
                errors.append("launch_intent_source_freeze_drift")
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            errors.append("launch_intent_artifact_invalid")
    try:
        process_pid = int(receipt.get("process_pid"))
        if process_pid <= 0 or process_pid != int(receipt.get("pid")):
            raise ValueError
    except (TypeError, ValueError):
        process_pid = -1
        errors.append("process_pid_invalid")
    try:
        qualified_at = datetime.fromisoformat(str(receipt.get("qualification_timestamp")))
        if qualified_at.tzinfo is None:
            raise ValueError
        age_seconds = (datetime.now(timezone.utc) - qualified_at.astimezone(timezone.utc)).total_seconds()
        if age_seconds < -60 or age_seconds > 12 * 3600:
            errors.append("qualification_timestamp_not_fresh")
    except (TypeError, ValueError):
        errors.append("qualification_timestamp_invalid")
    if os.name == "posix" and process_pid > 0:
        live_cmdline_path = Path(f"/proc/{process_pid}/cmdline")
        if not live_cmdline_path.is_file():
            errors.append("qualified_process_not_alive")
        else:
            live_cmdline = [
                part.decode() for part in live_cmdline_path.read_bytes().split(b"\0") if part
            ]
            if live_cmdline != cmdline:
                errors.append("qualified_process_cmdline_changed")
    if errors:
        raise RuntimeError(f"A10 launch receipt invalid: {errors}")
    return receipt


def preservation_report(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    observed = {str(item.get("task_name")): item for item in summaries}
    tasks = []
    for name in A0_PRESERVATION_TASKS:
        summary = observed.get(name) or {}
        reward = summary.get("evaluator_reward")
        tasks.append({"task_name": name, "reward": reward, "pass": reward == 1.0})
    success_count = sum(item["pass"] for item in tasks)
    return {"status": "pass" if success_count == 4 else "fail", "success_count": success_count, "required": 4, "tasks": tasks}


def _finite_reward(summary: dict[str, Any]) -> bool:
    try:
        return math.isfinite(float(summary.get("evaluator_reward")))
    except (TypeError, ValueError):
        return False


def exact_completion_errors(summaries: list[dict[str, Any]], invalid_attempts: list[dict[str, Any]], lifecycle_errors: list[dict[str, Any]]) -> list[str]:
    expected = list(A0_PRESERVATION_TASKS + REMAINING_TASKS)
    observed = [str(item.get("task_name")) for item in summaries]
    errors: list[str] = []
    if len(summaries) != TASK_COUNT or observed != expected:
        errors.append("exact_19_ordered_task_closure_failed")
    if any(int(item.get("seed", item.get("task_seed", -1))) != TASK_SEED for item in summaries):
        errors.append("task_seed_drift")
    if len({str(item.get("episode_id")) for item in summaries}) != len(summaries):
        errors.append("duplicate_episode_id")
    if any(
        item.get("error") is not None
        or item.get("lifecycle_errors")
        or not _finite_reward(item)
        for item in summaries
    ):
        errors.append("infrastructure_invalid_summary")
    if any(
        int(
            ((step.get("model_call") or {}).get("raven_meta") or {}).get(
                "transport_attempts"
            )
            or 0
        ) != 1
        for item in summaries
        for step in item.get("steps", [])
    ):
        errors.append("transport_attempt_count_not_one")
    if any(not item.get("resolved_by_episode_id") for item in invalid_attempts):
        errors.append("unresolved_infrastructure_invalid_attempt")
    valid_episode_ids = {str(item.get("episode_id")) for item in summaries}
    declared_invalid_ids_by_valid: dict[str, set[str]] = {}
    for item in summaries:
        declared = {
            str(value) for value in item.get("resolves_invalid_episode_ids") or []
        }
        if item.get("resolves_invalid_episode_id"):
            declared.add(str(item["resolves_invalid_episode_id"]))
        declared_invalid_ids_by_valid[str(item.get("episode_id"))] = declared
    invalid_links = {
        str(item.get("episode_id")): str(item.get("resolved_by_episode_id"))
        for item in invalid_attempts
        if item.get("episode_id") and item.get("resolved_by_episode_id")
    }
    if any(
        valid_id not in valid_episode_ids
        or invalid_id not in declared_invalid_ids_by_valid.get(valid_id, set())
        for invalid_id, valid_id in invalid_links.items()
    ) or {
        invalid_id
        for declared in declared_invalid_ids_by_valid.values()
        for invalid_id in declared
    } != set(invalid_links):
        errors.append("invalid_resolution_link_mismatch")
    if lifecycle_errors:
        errors.append("suite_lifecycle_error")
    return errors
