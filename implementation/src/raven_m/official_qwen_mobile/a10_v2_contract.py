"""Frozen contract for the A10-v2 EM-OBF prospective arm."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Any

MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
MODEL_REALPATH = "/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope"
MODEL_MANIFEST_SHA256 = "18e0909c7d993853d6d0f62443461a74009754f90db026a1723cab80121c7872"
OFFICIAL_SYSTEM_PROMPT_SHA256 = "9d060af15f62acb31b9fb197649ec001d4096491d7fb102de929316944b3e26d"
DESIGN_PARENT_COMMIT = "4548b932bc3b189507e1442e312c73c8f35dbdb8"
PARENT_EVIDENCE_COMMIT = DESIGN_PARENT_COMMIT
MECHANISM_ID = "a10_v2_evidence_matured_obligation_branch_frontier_v2"
EXPERIMENT_ID = "A10_V2_EMOBF_QWEN3VL32B_AW_HARD_S20260806_G3407_V1"
CONFIG_SCHEMA = "a10_v2_emobf_arm_v1"
PREFLIGHT_SCHEMA = "a10_v2_zero_generation_preflight_v1"
LIVE_RECEIPT_SCHEMA = "a10_v2_live_server_receipt_v1"
RESULT_SCHEMA = "a10_v2_emobf_result_v1"
TASK_SEED = 20260806
GENERATION_SEED = 3407
TASK_COUNT = 19

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
CONFIG_PATH = REPOSITORY_ROOT / "implementation/configs/a10_v2_evidence_matured_obligation_branch_frontier_hard_seed20260806.json"
PREFLIGHT_PATH = REPOSITORY_ROOT / "evidence/a10_v2/A10_V2_ZERO_GENERATION_PREFLIGHT.json"
LIVE_RECEIPT_PATH = REPOSITORY_ROOT / "evidence/a10_v2/A10_V2_LIVE_SERVER_RECEIPT.json"

A0_PRESERVATION_TASKS = (
    "ExpenseDeleteMultiple2", "RetroSavePlaylist", "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
)
REMAINING_TASKS = (
    "BrowserMultiply", "ExpenseAddMultipleFromGallery", "ExpenseAddMultipleFromMarkor",
    "MarkorCreateNoteAndSms", "MarkorMergeNotes", "MarkorTranscribeVideo",
    "OsmAndMarker", "OsmAndTrack", "RecipeAddMultipleRecipesFromImage",
    "RecipeAddMultipleRecipesFromMarkor", "RecipeAddMultipleRecipesFromMarkor2",
    "RecipeDeleteMultipleRecipesWithConstraint", "SaveCopyOfReceiptTaskEval",
    "SportsTrackerActivitiesOnDate", "SportsTrackerTotalDistanceForCategoryOverInterval",
)

# Generated preflight, live receipt, result and review outputs are deliberately
# excluded: including a report that embeds this digest would be self-referential.
SOURCE_FILES = (
    "GPT_PRO_A10_V2_STANDALONE_MEMORY_DESIGN_2026-08-12.md",
    "protocols/A10_V2_EMOBF_IMPLEMENTATION_BINDING_2026-08-12.md",
    "implementation/configs/androidworld_hard_v2_instances.json",
    "implementation/configs/a10_v2_evidence_matured_obligation_branch_frontier_hard_seed20260806.json",
    "implementation/src/raven_m/official_qwen_mobile/a10_v2_obligation_branch_frontier.py",
    "implementation/src/raven_m/official_qwen_mobile/a10_v2_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/official_qwen_mobile/protocol.py",
    "implementation/src/raven_m/official_qwen_mobile/working_memory.py",
    "implementation/src/raven_m/official_qwen_mobile/__init__.py",
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/run_a678_arm.py",
    "implementation/scripts/replay_a10_v2_offline_traces.py",
    "implementation/scripts/preflight_a10_v2.py",
    "implementation/scripts/qualify_a10_v2_live_server.py",
    "implementation/scripts/start_a10_v2_server.sh",
    "implementation/src/raven_m/models/vllm_client.py",
    "implementation/src/raven_m/env/androidworld_adapter.py",
    "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    "implementation/tests/official_qwen_mobile/test_a10_v2_parser.py",
    "implementation/tests/official_qwen_mobile/test_a10_v2_obligation_branch_frontier.py",
    "implementation/tests/official_qwen_mobile/test_a10_v2_route_maturity.py",
    "implementation/tests/official_qwen_mobile/test_a10_v2_contract.py",
    "implementation/tests/official_qwen_mobile/test_a10_v2_offline_replay.py",
    "implementation/tests/official_qwen_mobile/test_a10v2_a11_shared_integration.py",
    "implementation/tests/official_qwen_mobile/test_a10_controller_integration.py",
    "evidence/a10/A10_FROZEN_QUERY_SET.json",
    "evidence/a10/A10_OFFLINE_TRACE_SOURCE_SPEC.json",
    "evidence/a10/A10_OFFLINE_TRACE_MANIFEST.json",
    "evidence/a10/A10_OFFLINE_REPLAY_REPORT.json",
    "evidence/a2/A0_A1_PAIRED_REFERENCE_20260810.json",
    "evidence/a678/A8_V2_OFFLINE_TRACE_AUDIT_2026-08-11.json",
    "evidence/a678/A89_INITIAL_GATE_RESULTS_2026-08-12.json",
    "evidence/a10_v2/A10_V2_OFFLINE_TRACE_SOURCE_SPEC.json",
    "evidence/a10_v2/A10_V2_OFFLINE_REPLAY_REPORT.json",
    "protocols/PROSPECTIVE_DUAL_ARM_NAMESPACE_BINDING_2026-08-12.md",
)

def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()

def json_sha256(value: Any) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def current_source_freeze() -> dict[str, str]:
    missing = [name for name in SOURCE_FILES if not (REPOSITORY_ROOT / name).is_file()]
    if missing:
        raise RuntimeError(f"A10-v2 source closure incomplete: {missing}")
    return {name: file_sha256(REPOSITORY_ROOT / name) for name in SOURCE_FILES}

def validate_preflight_report(path: Path = PREFLIGHT_PATH) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    freeze = current_source_freeze()
    errors = []
    expected = {"schema": PREFLIGHT_SCHEMA, "status": "pass", "generation_calls": 0,
                "mechanism_id": MECHANISM_ID, "experiment_id": EXPERIMENT_ID,
                "design_parent_commit": DESIGN_PARENT_COMMIT}
    errors += [f"{key}_drift" for key, value in expected.items() if report.get(key) != value]
    if report.get("errors"): errors.append("preflight_errors_nonempty")
    if report.get("source_freeze") != freeze or report.get("source_freeze_sha256") != json_sha256(freeze):
        errors.append("source_freeze_drift")
    implementation_commit = str(report.get("implementation_commit") or "")
    if len(implementation_commit) != 40 or any(char not in "0123456789abcdef" for char in implementation_commit):
        errors.append("implementation_commit_invalid")
    else:
        try:
            head = subprocess.check_output(["git", "-C", str(REPOSITORY_ROOT), "rev-parse", "HEAD"], text=True).strip()
            if head != implementation_commit: errors.append("implementation_commit_not_current_head")
            if subprocess.run(["git", "-C", str(REPOSITORY_ROOT), "merge-base", "--is-ancestor", DESIGN_PARENT_COMMIT, implementation_commit], check=False).returncode: errors.append("design_parent_not_ancestor")
            if subprocess.check_output(["git", "-C", str(REPOSITORY_ROOT), "status", "--porcelain", "--untracked-files=all"], text=True).strip(): errors.append("worktree_dirty")
        except (OSError, subprocess.SubprocessError):
            errors.append("git_identity_validation_failed")
    if errors: raise RuntimeError(f"A10-v2 preflight validation failed: {errors}")
    return report

def validate_launch_receipt(path: Path = LIVE_RECEIPT_PATH, *, preflight_path: Path = PREFLIGHT_PATH) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8")); preflight = validate_preflight_report(preflight_path)
    expected = {"schema": LIVE_RECEIPT_SCHEMA, "status": "pass", "generation_calls": 0,
                "served_model_id": MODEL_ID, "model_realpath": MODEL_REALPATH,
                "model_manifest_sha256": MODEL_MANIFEST_SHA256, "port": 18000,
                "a10_v2_preflight_sha256": file_sha256(preflight_path),
                "a10_v2_source_freeze_sha256": preflight["source_freeze_sha256"]}
    errors = [f"{key}_drift" for key, value in expected.items() if receipt.get(key) != value]
    cmdline = [str(x) for x in receipt.get("process_cmdline") or []]
    if MODEL_REALPATH not in cmdline or MODEL_ID not in cmdline or "serve" not in cmdline: errors.append("process_cmdline_binding_missing")
    if receipt.get("served_model_ids_observed") != [MODEL_ID]: errors.append("served_model_ids_observed_drift")
    intent_path = Path(str(receipt.get("launch_intent_path") or ""))
    if not intent_path.is_file() or receipt.get("launch_intent_sha256") != file_sha256(intent_path):
        errors.append("launch_intent_hash_mismatch")
    else:
        try:
            intent = json.loads(intent_path.read_text(encoding="utf-8"))
            if intent.get("arm") != "a10v2" or intent.get("schema") != "a10_v2_server_launch_intent_v1": errors.append("launch_intent_identity_drift")
            if cmdline != [str(item) for item in intent.get("command") or []]: errors.append("launch_intent_command_drift")
        except (OSError, ValueError, TypeError, json.JSONDecodeError): errors.append("launch_intent_invalid")
    packages = receipt.get("packages") or {}
    if not all(str(packages.get(k) or "") for k in ("vllm", "torch", "transformers")): errors.append("runtime_packages_missing")
    try:
        qualified = datetime.fromisoformat(str(receipt.get("qualification_timestamp")))
        age = (datetime.now(timezone.utc) - qualified.astimezone(timezone.utc)).total_seconds()
        if qualified.tzinfo is None or not -60 <= age <= 43200: raise ValueError
    except (TypeError, ValueError): errors.append("qualification_timestamp_invalid_or_stale")
    try:
        pid = int(receipt.get("pid")); assert pid > 0
    except (TypeError, ValueError, AssertionError): pid = -1; errors.append("pid_invalid")
    if os.name == "posix" and pid > 0:
        proc = Path(f"/proc/{pid}/cmdline")
        if not proc.is_file() or [x.decode() for x in proc.read_bytes().split(b"\0") if x] != cmdline: errors.append("qualified_process_invalid")
    if errors: raise RuntimeError(f"A10-v2 launch receipt invalid: {errors}")
    return receipt

def _finite_reward(item: dict[str, Any]) -> bool:
    try: return math.isfinite(float(item.get("evaluator_reward")))
    except (TypeError, ValueError): return False

def preservation_report(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    observed = {str(item.get("task_name")): item for item in summaries}
    tasks = []
    for name in A0_PRESERVATION_TASKS:
        reward = (observed.get(name) or {}).get("evaluator_reward")
        tasks.append({"task_name": name, "reward": reward, "pass": reward == 1.0})
    success_count = sum(bool(item["pass"]) for item in tasks)
    return {"status": "pass" if success_count == 4 else "fail", "success_count": success_count, "required": 4, "tasks": tasks}

def exact_completion_errors(summaries: list[dict[str, Any]], invalid_attempts: list[dict[str, Any]], lifecycle_errors: list[dict[str, Any]]) -> list[str]:
    expected = list(A0_PRESERVATION_TASKS + REMAINING_TASKS); errors: list[str] = []
    if len(summaries) != 19 or [str(x.get("task_name")) for x in summaries] != expected: errors.append("exact_19_ordered_task_closure_failed")
    if any(int(x.get("seed", x.get("task_seed", -1))) != TASK_SEED for x in summaries): errors.append("task_seed_drift")
    if len({str(x.get("episode_id")) for x in summaries}) != len(summaries): errors.append("duplicate_episode_id")
    if any(x.get("error") is not None or x.get("lifecycle_errors") or not _finite_reward(x) for x in summaries): errors.append("infrastructure_invalid_summary")
    if any(int(((step.get("model_call") or {}).get("raven_meta") or {}).get("transport_attempts") or 0) != 1 for item in summaries for step in item.get("steps", [])): errors.append("transport_attempt_count_not_one")
    valid_ids = {str(item.get("episode_id")) for item in summaries}
    declared: dict[str, set[str]] = {}
    for item in summaries:
        links = {str(value) for value in item.get("resolves_invalid_episode_ids") or []}
        if item.get("resolves_invalid_episode_id"):
            links.add(str(item["resolves_invalid_episode_id"]))
        declared[str(item.get("episode_id"))] = links
    invalid_links = {
        str(item.get("episode_id")): str(item.get("resolved_by_episode_id"))
        for item in invalid_attempts
        if item.get("episode_id") and item.get("resolved_by_episode_id")
    }
    if any(not item.get("resolved_by_episode_id") for item in invalid_attempts):
        errors.append("unresolved_infrastructure_invalid_attempt")
    if any(valid not in valid_ids or invalid not in declared.get(valid, set()) for invalid, valid in invalid_links.items()) or {value for values in declared.values() for value in values} != set(invalid_links):
        errors.append("invalid_resolution_link_mismatch")
    if lifecycle_errors: errors.append("suite_lifecycle_error")
    return errors

FAILURE_TAXONOMY = ("A10_V2_PROTOCOL_INVALID", "A10_V2_ZERO_GENERATION_PREFLIGHT_FAIL", "A10_V2_INFRASTRUCTURE_INVALID", "A10_V2_CAPABILITY_GATE_FAILURE", "A10_V2_SCIENTIFIC_FAILURE", "A10_V2_PERFORMANCE_PASS_MECHANISM_EVIDENCE_FAIL", "A10_V2_OVERALL_PASS")
