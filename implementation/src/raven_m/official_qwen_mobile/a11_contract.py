"""Frozen contract helpers for the A11 CRC-ECOBF prospective arm."""

from __future__ import annotations

from hashlib import sha256
import json
import math
from datetime import datetime, timezone
import os
import subprocess
from pathlib import Path
from typing import Any


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
OFFICIAL_SYSTEM_PROMPT_SHA256 = "9d060af15f62acb31b9fb197649ec001d4096491d7fb102de929316944b3e26d"
TASK_SEED = 20260806
GENERATION_SEED = 3407
TASK_COUNT = 19
PARENT_EVIDENCE_COMMIT = "4548b932bc3b189507e1442e312c73c8f35dbdb8"
DESIGN_PARENT_COMMIT = PARENT_EVIDENCE_COMMIT
MECHANISM_ID = "a11_confirmed_route_contraction_ecobf_v1"
EXPERIMENT_ID = "A11_CRC_ECOBF_QWEN3VL32B_AW_HARD_T20260806_G3407_V1"
AUDIT_SCHEMA = "a11_crc_ecobf_audit_v1"
OFFLINE_REPLAY_SCHEMA = "a11_offline_replay_report_v1"
PREFLIGHT_SCHEMA = "a11_zero_generation_preflight_v1"
LIVE_RECEIPT_SCHEMA = "a11_live_server_receipt_v1"
RESULT_SCHEMA = "a11_crc_ecobf_result_v1"
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
CONFIG_PATH = REPOSITORY_ROOT / "implementation/configs/a11_confirmed_route_contraction_hard_seed20260806.json"
PREFLIGHT_PATH = REPOSITORY_ROOT / "evidence/a11/A11_ZERO_GENERATION_PREFLIGHT.json"
LIVE_RECEIPT_PATH = REPOSITORY_ROOT / "evidence/a11/A11_LIVE_SERVER_RECEIPT.json"
MODEL_REALPATH = "/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope"
MODEL_MANIFEST_SHA256 = "18e0909c7d993853d6d0f62443461a74009754f90db026a1723cab80121c7872"
SOURCE_FILES = (
    "GPT_PRO_A11_STANDALONE_MEMORY_DESIGN_2026-08-12.md",
    "implementation/configs/androidworld_hard_v2_instances.json",
    "implementation/configs/a11_confirmed_route_contraction_hard_seed20260806.json",
    "implementation/src/raven_m/official_qwen_mobile/a11_confirmed_route_contraction.py",
    "implementation/src/raven_m/official_qwen_mobile/a11_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/official_qwen_mobile/protocol.py",
    "implementation/src/raven_m/official_qwen_mobile/working_memory.py",
    "implementation/src/raven_m/official_qwen_mobile/__init__.py",
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/run_a678_arm.py",
    "implementation/scripts/replay_a11_offline_traces.py",
    "implementation/scripts/preflight_a11.py",
    "implementation/scripts/qualify_a11_live_server.py",
    "implementation/scripts/start_a11_server.sh",
    "implementation/src/raven_m/models/vllm_client.py",
    "implementation/src/raven_m/env/androidworld_adapter.py",
    "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    "implementation/tests/official_qwen_mobile/test_a11_confirmed_route_contraction.py",
    "implementation/tests/official_qwen_mobile/test_a11_contract.py",
    "implementation/tests/official_qwen_mobile/test_a10v2_a11_shared_integration.py",
    "implementation/tests/official_qwen_mobile/test_a10_controller_integration.py",
    "implementation/tests/official_qwen_mobile/test_a11_offline_replay.py",
    "protocols/A11_CRC_ECOBF_IMPLEMENTATION_BINDING_2026-08-12.md",
    "protocols/PROSPECTIVE_DUAL_ARM_NAMESPACE_BINDING_2026-08-12.md",
    "evidence/a11/A11_OFFLINE_TRACE_SOURCE_SPEC.json",
    "evidence/a11/A11_OFFLINE_REPLAY_REPORT.json",
    "evidence/a11/A11_FROZEN_QUERY_SET.json",
    "evidence/a11/A11_OFFLINE_TRACE_MANIFEST.json",
    "evidence/a11/A11_TEST_MANIFEST.json",
    "evidence/a10/A10_OFFLINE_REPLAY_REPORT.json",
    "evidence/a10/A10_OFFLINE_TRACE_MANIFEST.json",
    "evidence/a10/A10_OFFLINE_TRACE_SOURCE_SPEC.json",
    "evidence/a2/A0_A1_PAIRED_REFERENCE_20260810.json",
    "evidence/a678/A8_V2_OFFLINE_TRACE_AUDIT_2026-08-11.json",
    "evidence/a678/A89_INITIAL_GATE_RESULTS_2026-08-12.json",
)

A0_GATE_TASKS = (
    "ExpenseDeleteMultiple2",
    "RetroSavePlaylist",
    "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
)
REMAINING_TASKS = (
    "BrowserMultiply", "ExpenseAddMultipleFromGallery", "ExpenseAddMultipleFromMarkor",
    "MarkorCreateNoteAndSms", "MarkorMergeNotes", "MarkorTranscribeVideo", "OsmAndMarker",
    "OsmAndTrack", "RecipeAddMultipleRecipesFromImage", "RecipeAddMultipleRecipesFromMarkor",
    "RecipeAddMultipleRecipesFromMarkor2", "RecipeDeleteMultipleRecipesWithConstraint",
    "SaveCopyOfReceiptTaskEval", "SportsTrackerActivitiesOnDate",
    "SportsTrackerTotalDistanceForCategoryOverInterval",
)


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def json_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def current_source_freeze() -> dict[str, str]:
    missing = [name for name in SOURCE_FILES if not (REPOSITORY_ROOT / name).is_file()]
    if missing:
        raise RuntimeError(f"A11 source closure incomplete: {missing}")
    return {name: file_sha256(REPOSITORY_ROOT / name) for name in SOURCE_FILES}


def validate_preflight_report(path: Path = PREFLIGHT_PATH) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    current = current_source_freeze()
    errors: list[str] = []
    if report.get("schema") != PREFLIGHT_SCHEMA:
        errors.append("schema_drift")
    if report.get("status") != "pass" or report.get("generation_calls") != 0 or report.get("errors"):
        errors.append("status_or_generation_calls_invalid")
    if report.get("source_freeze") != current or report.get("source_freeze_sha256") != json_sha256(current):
        errors.append("source_freeze_drift")
    if report.get("parent_evidence_commit") != PARENT_EVIDENCE_COMMIT:
        errors.append("parent_evidence_commit_drift")
    commit = str(report.get("a11_implementation_commit") or "")
    if not re_full_hex(commit):
        errors.append("implementation_commit_invalid")
    else:
        try:
            head = subprocess.check_output(["git", "-C", str(REPOSITORY_ROOT), "rev-parse", "HEAD"], text=True).strip()
            if head != commit:
                errors.append("implementation_commit_not_current_head")
            if subprocess.run(["git", "-C", str(REPOSITORY_ROOT), "merge-base", "--is-ancestor", PARENT_EVIDENCE_COMMIT, commit], check=False).returncode:
                errors.append("parent_not_ancestor")
            if subprocess.check_output(["git", "-C", str(REPOSITORY_ROOT), "status", "--porcelain", "--untracked-files=all"], text=True).strip():
                errors.append("worktree_dirty")
        except (OSError, subprocess.SubprocessError):
            errors.append("git_identity_validation_failed")
    if errors:
        raise RuntimeError(f"A11 preflight validation failed: {errors}")
    return report


def re_full_hex(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value.casefold())


def validate_launch_receipt(path: Path = LIVE_RECEIPT_PATH, *, preflight_path: Path = PREFLIGHT_PATH) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    preflight = validate_preflight_report(preflight_path)
    expected = {
        "schema": LIVE_RECEIPT_SCHEMA, "status": "pass", "generation_calls": 0,
        "served_model_id": MODEL_ID, "model_realpath": MODEL_REALPATH,
        "model_manifest_sha256": MODEL_MANIFEST_SHA256, "port": 18000,
        "a11_preflight_sha256": file_sha256(preflight_path),
        "a11_source_freeze_sha256": preflight["source_freeze_sha256"],
    }
    errors = [f"{key}_drift" for key, value in expected.items() if receipt.get(key) != value]
    cmdline = [str(item) for item in receipt.get("process_cmdline") or []]
    if MODEL_REALPATH not in cmdline or MODEL_ID not in cmdline or "serve" not in cmdline:
        errors.append("process_cmdline_binding_missing")
    if receipt.get("served_model_ids_observed") != [MODEL_ID]:
        errors.append("served_model_ids_observed_drift")
    packages = receipt.get("packages") or {}
    if not all(str(packages.get(name) or "") for name in ("vllm", "torch", "transformers")):
        errors.append("runtime_packages_missing")
    launch_path = Path(str(receipt.get("launch_intent_path") or ""))
    if not launch_path.is_file() or receipt.get("launch_intent_sha256") != file_sha256(launch_path):
        errors.append("launch_intent_artifact_hash_mismatch")
    else:
        try:
            intent = json.loads(launch_path.read_text(encoding="utf-8"))
            if intent.get("arm") != "a11" or intent.get("schema") != "a11_server_launch_intent_v1":
                errors.append("launch_intent_identity_drift")
            if cmdline != [str(item) for item in intent.get("command") or []]:
                errors.append("launch_intent_command_drift")
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            errors.append("launch_intent_invalid")
    try:
        pid = int(receipt.get("process_pid"))
        if pid <= 0 or pid != int(receipt.get("pid")):
            raise ValueError
    except (TypeError, ValueError):
        pid = -1
        errors.append("process_pid_invalid")
    try:
        qualified = datetime.fromisoformat(str(receipt.get("qualification_timestamp")))
        if qualified.tzinfo is None:
            raise ValueError
        age = (datetime.now(timezone.utc) - qualified.astimezone(timezone.utc)).total_seconds()
        if age < -60 or age > 12 * 3600:
            errors.append("qualification_timestamp_not_fresh")
    except (TypeError, ValueError):
        errors.append("qualification_timestamp_invalid")
    if os.name == "posix" and pid > 0:
        live = Path(f"/proc/{pid}/cmdline")
        if not live.is_file():
            errors.append("qualified_process_not_alive")
        elif [part.decode() for part in live.read_bytes().split(b"\0") if part] != cmdline:
            errors.append("qualified_process_cmdline_changed")
    if errors:
        raise RuntimeError(f"A11 live receipt invalid: {errors}")
    return receipt


def _finite_reward(summary: dict[str, Any]) -> bool:
    try:
        return math.isfinite(float(summary.get("evaluator_reward")))
    except (TypeError, ValueError):
        return False


def preservation_report(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    observed = {str(item.get("task_name")): item for item in summaries}
    tasks = [{"task_name": name, "reward": (observed.get(name) or {}).get("evaluator_reward")} for name in A0_GATE_TASKS]
    for item in tasks:
        item["pass"] = item["reward"] == 1.0
    successes = sum(bool(item["pass"]) for item in tasks)
    return {"status": "pass" if successes == 4 else "fail", "success_count": successes, "required": 4, "tasks": tasks}


def exact_completion_errors(
    summaries: list[dict[str, Any]],
    invalid_attempts: list[dict[str, Any]],
    lifecycle_errors: list[dict[str, Any]],
) -> list[str]:
    expected = list(A0_GATE_TASKS + REMAINING_TASKS)
    errors: list[str] = []
    if len(summaries) != TASK_COUNT or [str(item.get("task_name")) for item in summaries] != expected:
        errors.append("exact_19_ordered_task_closure_failed")
    if any(int(item.get("seed", item.get("task_seed", -1))) != TASK_SEED for item in summaries):
        errors.append("task_seed_drift")
    if len({str(item.get("episode_id")) for item in summaries}) != len(summaries):
        errors.append("duplicate_episode_id")
    if any(item.get("error") is not None or item.get("lifecycle_errors") or not _finite_reward(item) for item in summaries):
        errors.append("infrastructure_invalid_summary")
    if any(
        int(((step.get("model_call") or {}).get("raven_meta") or {}).get("transport_attempts") or 0) != 1
        for item in summaries for step in item.get("steps", [])
    ):
        errors.append("transport_attempt_count_not_one")
    invalid_links = {
        str(item.get("episode_id")): str(item.get("resolved_by_episode_id"))
        for item in invalid_attempts if item.get("episode_id") and item.get("resolved_by_episode_id")
    }
    valid_ids = {str(item.get("episode_id")) for item in summaries}
    declared: dict[str, set[str]] = {}
    for item in summaries:
        links = {str(value) for value in item.get("resolves_invalid_episode_ids") or []}
        if item.get("resolves_invalid_episode_id"):
            links.add(str(item["resolves_invalid_episode_id"]))
        declared[str(item.get("episode_id"))] = links
    if any(valid not in valid_ids or invalid not in declared.get(valid, set()) for invalid, valid in invalid_links.items()) or {value for values in declared.values() for value in values} != set(invalid_links):
        errors.append("invalid_resolution_link_mismatch")
    if any(not item.get("resolved_by_episode_id") for item in invalid_attempts):
        errors.append("unresolved_infrastructure_invalid_attempt")
    if lifecycle_errors:
        errors.append("suite_lifecycle_error")
    return errors


def replay_metric_counts(read_events: list[dict[str, Any]]) -> dict[str, int]:
    """Frozen evaluator-side definitions for the competent sparse gate.

    A post-return confirmation is independent two-support evidence even though
    only one closed route exists.  The metric counts an error only when a T2
    delivery has neither a second route nor a post-return branch receipt.
    """
    single_route = first_core = immature = support_below_two = redelivery = 0
    seen: set[str] = set()
    for event in read_events:
        state = str(event.get("candidate_state_before_read") or "")
        support_count = int(event.get("support_count") or 0)
        signature = str(event.get("evidence_signature") or "")
        kind = str(event.get("trigger_kind") or "")
        path = str(event.get("confirmation_path") or "")
        route_ids = list(event.get("retrieved_route_ids") or [])
        receipt_ids = list(event.get("support_receipt_ids") or [])
        if state != "MATURE":
            immature += 1
        if support_count < 2:
            support_below_two += 1
        if signature in seen:
            redelivery += 1
        seen.add(signature)
        if kind == "CONFIRMED_ROUTE_TRAP":
            independently_confirmed = len(set(route_ids)) >= 2 or (path == "post_return_reversion" and len(set(receipt_ids)) >= 2)
            if not independently_confirmed:
                single_route += 1
                first_core += 1
    return {
        "immature_candidate_delivery_count": immature,
        "single_closed_route_delivery_count": single_route,
        "first_route_core_delivery_count": first_core,
        "support_count_below_two_delivery_count": support_below_two,
        "same_signature_redelivery_count": redelivery,
    }


def competent_sparse_gate(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply the frozen four-trajectory sparse-and-mature qualification gate."""
    counts = [int(item.get("nonempty_read_count") or 0) for item in episodes]
    actions = sum(int(item.get("replayed_actions") or 0) for item in episodes)
    total = sum(counts)
    rendered = sum(int(item.get("rendered_chars") or 0) for item in episodes)
    merged = replay_metric_counts([event for item in episodes for event in item.get("read_events", [])])
    violations = sum(int(item.get("normal_navigation_exemption_violation_count") or 0) for item in episodes)
    density = total / actions if actions else math.inf
    errors: list[str] = []
    if len(episodes) != 4 or any(value > 1 for value in counts):
        errors.append("per_episode_read_cap_failed")
    if total > 2 or density > .04 or rendered > 840:
        errors.append("aggregate_sparse_budget_failed")
    if violations or any(merged.values()):
        errors.append("maturity_or_navigation_gate_failed")
    return {"status": "pass" if not errors else "fail", "total_nonempty_reads": total, "total_read_density": density, "total_rendered_chars": rendered, "normal_navigation_exemption_violation_count": violations, **merged, "errors": errors}


__all__ = [
    "A0_GATE_TASKS", "AUDIT_SCHEMA", "DESIGN_PARENT_COMMIT", "EXPERIMENT_ID", "GENERATION_SEED",
    "LIVE_RECEIPT_SCHEMA", "MECHANISM_ID", "MODEL_ID", "MODEL_REVISION",
    "OFFICIAL_SYSTEM_PROMPT_SHA256", "OFFLINE_REPLAY_SCHEMA", "PARENT_EVIDENCE_COMMIT",
    "PREFLIGHT_SCHEMA", "REMAINING_TASKS", "RESULT_SCHEMA", "TASK_COUNT", "TASK_SEED",
    "MODEL_REALPATH", "PARENT_EVIDENCE_COMMIT", "competent_sparse_gate", "current_source_freeze",
    "exact_completion_errors", "preservation_report", "replay_metric_counts", "validate_launch_receipt",
    "validate_preflight_report",
]
