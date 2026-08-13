"""Fail-closed scientific and artifact contract for A1-R1 BPR v2."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
from typing import Any

from .a1r1_bpr_v2 import (
    EMPTY_EXPERIMENT_ID,
    MECHANISM_ID,
    PRIMARY_EXPERIMENT_ID,
)


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
MODEL_REALPATH = "/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope"
MODEL_MANIFEST_SHA256 = "18e0909c7d993853d6d0f62443461a74009754f90db026a1723cab80121c7872"
DESIGN_AUDIT_COMMIT = "3f1de08f3f936f1283ff4868a2be83cc211a63db"
PARENT_EVIDENCE_COMMIT = DESIGN_AUDIT_COMMIT
DESIGN_SHA256 = "e6ff3a975484502e2b7368dd3f9775956957a613e3cf4a355e4e7e1c8d1ffc07"
NORMATIVE_BUNDLE_SHA256 = "61adeb079ac1b0ff286c5dff5e15ef258f3465ccbf9a888e161569d0e547fcb4"

TASK_SEED = 20260806
GENERATION_SEED = 3407
PORT = 18000
PRIMARY_CHECKPOINT_SCHEMA = "a1r1_bpr_v2_primary_checkpoint_v1"
EMPTY_CHECKPOINT_SCHEMA = "a1r1_bpr_v2_empty_read_checkpoint_v1"
PRIMARY_RESULT_SCHEMA = "a1r1_bpr_v2_primary_result_v1"
EMPTY_RESULT_SCHEMA = "a1r1_bpr_v2_empty_read_result_v1"
OFFLINE_REPLAY_SCHEMA = "a1r1_bpr_v2_offline_replay_v1"
PREFLIGHT_SCHEMA = "a1r1_bpr_v2_zero_generation_preflight_v1"
LIVE_RECEIPT_SCHEMA = "a1r1_bpr_v2_live_server_receipt_v1"

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
PRIMARY_CONFIG_PATH = REPOSITORY_ROOT / "implementation/configs/a1r1_bpr_v2_primary_hard_seed20260806.json"
EMPTY_CONFIG_PATH = REPOSITORY_ROOT / "implementation/configs/a1r1_bpr_v2_empty_read_five_task_seed20260806.json"
SOURCE_FREEZE_PATH = REPOSITORY_ROOT / "evidence/a1r1_v2/A1R1_BPR_V2_SOURCE_FREEZE.json"
OFFLINE_REPLAY_PATH = REPOSITORY_ROOT / "evidence/a1r1_v2/A1R1_BPR_V2_OFFLINE_REPLAY_REPORT.json"
PREFLIGHT_PATH = REPOSITORY_ROOT / "evidence/a1r1_v2/A1R1_BPR_V2_ZERO_GENERATION_PREFLIGHT.json"
EXPERIMENT_ID = PRIMARY_EXPERIMENT_ID
CONFIG_PATH = PRIMARY_CONFIG_PATH

A0_PRESERVATION_TASKS = (
    "ExpenseDeleteMultiple2",
    "RetroSavePlaylist",
    "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
)
RECIPE_TASK = "RecipeDeleteMultipleRecipesWithConstraint"
GATE5_TASKS = A0_PRESERVATION_TASKS + (RECIPE_TASK,)

SOURCE_FILES = (
    "GPT_PRO_A1_VERTICAL_BPR_V2_DESIGN_2026-08-13.md",
    "GPT_PRO_A1_VERTICAL_BPR_V2_REVISION_REQUEST_2026-08-13.md",
    "protocols/A1R1_BPR_V2_IMPLEMENTATION_BINDING_2026-08-14.md",
    "implementation/src/raven_m/official_qwen_mobile/a1r1_bpr_v2.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r1_bpr_v2_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/official_qwen_mobile/protocol.py",
    "implementation/src/raven_m/official_qwen_mobile/working_memory.py",
    "implementation/src/raven_m/official_qwen_mobile/__init__.py",
    "implementation/src/raven_m/models/vllm_client.py",
    "implementation/src/raven_m/env/androidworld_adapter.py",
    "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    "implementation/configs/androidworld_hard_v2_instances.json",
    "implementation/configs/a1r1_bpr_v2_primary_hard_seed20260806.json",
    "implementation/configs/a1r1_bpr_v2_empty_read_five_task_seed20260806.json",
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/run_a1r1_bpr_v2.py",
    "implementation/scripts/replay_a1r1_bpr_v2_offline.py",
    "implementation/scripts/preflight_a1r1_bpr_v2.py",
    "implementation/scripts/qualify_a1r1_bpr_v2_server.py",
    "implementation/scripts/start_a1r1_bpr_v2_server.sh",
    "implementation/tests/official_qwen_mobile/test_a1r1_bpr_v2.py",
    "implementation/tests/official_qwen_mobile/test_a1r1_bpr_v2_contract.py",
    "implementation/tests/official_qwen_mobile/test_a1r1_bpr_v2_controller_integration.py",
    "implementation/tests/official_qwen_mobile/test_a1r1_bpr_v2_offline_replay.py",
    "evidence/a1r1/A1R1_V1_RAW_TRACE_AUDIT_2026-08-13.json",
    "evidence/a1r1/A1R1_V1_DESIGN_AUDIT_2026-08-13.md",
    "evidence/a2/A0_A1_PAIRED_REFERENCE_20260810.json",
    "evidence/a1/A1_ACTION_WORKING_MEMORY_RESULTS_2026-08-10.md",
    "evidence/diag6/A10V2_DIAGNOSTIC6_RESULT_2026-08-13.md",
    "evidence/diag6/A11_A12_DIAGNOSTIC6_RESULTS_2026-08-13.md",
)


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def canonical_json_sha256(value: Any) -> str:
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def content_sha256(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("content_sha256", None)
    return canonical_json_sha256(payload)


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(REPOSITORY_ROOT), *args], text=True
    ).strip()


def source_freeze_payload(implementation_commit: str) -> dict[str, Any]:
    if len(implementation_commit) != 40:
        raise RuntimeError("implementation commit must be exact 40-hex")
    if subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), "merge-base", "--is-ancestor", DESIGN_AUDIT_COMMIT, implementation_commit],
        check=False,
        capture_output=True,
    ).returncode:
        raise RuntimeError("design audit commit is not an ancestor")
    files: dict[str, str] = {}
    for name in SOURCE_FILES:
        path = REPOSITORY_ROOT / name
        if not path.is_file():
            raise RuntimeError(f"source closure file missing: {name}")
        try:
            frozen = subprocess.check_output(
                ["git", "-C", str(REPOSITORY_ROOT), "show", f"{implementation_commit}:{name}"]
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"source file absent from implementation commit: {name}") from exc
        digest = sha256(frozen).hexdigest()
        frozen_blob = _git("rev-parse", f"{implementation_commit}:{name}")
        current_clean_blob = _git("hash-object", "--path", name, str(path))
        if current_clean_blob != frozen_blob:
            raise RuntimeError(f"current source bytes drifted from implementation commit: {name}")
        files[name] = digest
    payload = {
        "schema": "a1r1_bpr_v2_source_freeze_v1",
        "implementation_commit": implementation_commit,
        "design_sha256": DESIGN_SHA256,
        "normative_bundle_sha256": NORMATIVE_BUNDLE_SHA256,
        "files": files,
    }
    return {**payload, "content_sha256": content_sha256(payload)}


def validate_source_freeze(path: Path = SOURCE_FREEZE_PATH) -> dict[str, Any]:
    freeze = json.loads(path.read_text(encoding="utf-8"))
    expected = source_freeze_payload(str(freeze.get("implementation_commit") or ""))
    if freeze != expected:
        raise RuntimeError("BPR-v2 source freeze drift")
    head = _git("rev-parse", "HEAD")
    if subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), "merge-base", "--is-ancestor", freeze["implementation_commit"], head],
        check=False,
        capture_output=True,
    ).returncode:
        raise RuntimeError("implementation commit is not an ancestor of HEAD")
    return freeze


def validate_preflight_report(
    path: Path = PREFLIGHT_PATH,
    *,
    source_freeze_path: Path = SOURCE_FREEZE_PATH,
    offline_replay_path: Path = OFFLINE_REPLAY_PATH,
) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    freeze = validate_source_freeze(source_freeze_path)
    replay = json.loads(offline_replay_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    expected = {
        "schema": PREFLIGHT_SCHEMA,
        "status": "PASS",
        "mechanism_id": MECHANISM_ID,
        "implementation_commit": freeze["implementation_commit"],
        "source_freeze_content_sha256": freeze["content_sha256"],
        "source_freeze_file_sha256": file_sha256(source_freeze_path),
        "offline_replay_file_sha256": file_sha256(offline_replay_path),
        "generation_calls": 0,
        "live_generation_authorized": True,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            errors.append(f"{key}_drift")
    if report.get("errors") != [] or report.get("content_sha256") != content_sha256(report):
        errors.append("preflight_errors_or_content_hash")
    if (
        replay.get("schema") != OFFLINE_REPLAY_SCHEMA
        or replay.get("status") != "PASS"
        or replay.get("errors") != []
        or replay.get("generation_calls") != 0
        or replay.get("R5_status") != "PROSPECTIVE_UNKNOWN_PRELIVE"
        or replay.get("live_generation_authorized") is not True
        or replay.get("content_sha256") != content_sha256(replay)
    ):
        errors.append("offline_replay_not_authorizing")
    if errors:
        raise RuntimeError(f"BPR-v2 preflight invalid: {errors}")
    return report


def validate_launch_receipt(
    path: Path,
    *,
    preflight_path: Path = PREFLIGHT_PATH,
    expected_read_enabled: bool | None = None,
    expected_experiment_id: str | None = None,
) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    preflight = validate_preflight_report(preflight_path)
    errors: list[str] = []
    if receipt.get("schema") != LIVE_RECEIPT_SCHEMA or receipt.get("status") != "PASS":
        errors.append("receipt_status_or_schema")
    if receipt.get("errors") != [] or receipt.get("generation_calls") != 0:
        errors.append("receipt_errors_or_generation")
    if receipt.get("mechanism_id") != MECHANISM_ID:
        errors.append("mechanism_id_drift")
    if receipt.get("preflight_file_sha256") != file_sha256(preflight_path):
        errors.append("preflight_hash_drift")
    if receipt.get("implementation_commit") != preflight.get("implementation_commit"):
        errors.append("implementation_commit_drift")
    if expected_read_enabled is not None and receipt.get("read_enabled") is not expected_read_enabled:
        errors.append("read_enabled_drift")
    if expected_experiment_id is not None and receipt.get("experiment_id") != expected_experiment_id:
        errors.append("experiment_id_drift")
    if receipt.get("served_model_id") != MODEL_ID or receipt.get("model_manifest_sha256") != MODEL_MANIFEST_SHA256:
        errors.append("model_identity_drift")
    if receipt.get("content_sha256") != content_sha256(receipt):
        errors.append("receipt_content_hash")
    if errors:
        raise RuntimeError(f"BPR-v2 receipt invalid: {errors}")
    return receipt


def preservation_report(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    observed = {str(item.get("task_name")): item for item in summaries}
    tasks = [
        {
            "task_name": name,
            "reward": (observed.get(name) or {}).get("evaluator_reward"),
            "pass": bool((observed.get(name) or {}).get("success")),
        }
        for name in A0_PRESERVATION_TASKS
    ]
    successes = sum(int(item["pass"]) for item in tasks)
    return {"status": "pass" if successes == 4 else "fail", "success_count": successes, "required": 4, "tasks": tasks}


def gate5_report(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    observed = {str(item.get("task_name")): item for item in summaries}
    tasks = [
        {"task_name": name, "pass": bool((observed.get(name) or {}).get("success"))}
        for name in GATE5_TASKS
    ]
    successes = sum(int(item["pass"]) for item in tasks)
    recipe = observed.get(RECIPE_TASK) or {}
    audit = recipe.get("memory_mechanism") or {}
    counters = audit.get("counters") or {}
    recipe_exposed = int(counters.get("write_accept_count") or 0) > 0 and int(counters.get("nonempty_read_count") or 0) > 0
    budget_lost = int(counters.get("episode_budget_suppression_count") or 0) > 0
    r5 = (
        "FALSIFIED_GATE5" if successes < 5
        else "NOT_FALSIFIED_GATE5" if recipe_exposed and not budget_lost
        else "PROSPECTIVE_UNOBSERVED_GATE5"
    )
    return {"status": "pass" if successes == 5 else "fail", "success_count": successes, "required": 5, "tasks": tasks, "R5_status": r5}


def exact_completion_errors(
    *,
    summaries: list[dict[str, Any]],
    invalid_attempts: list[dict[str, Any]],
    lifecycle_errors: list[dict[str, Any]],
    expected_count: int = 19,
) -> list[str]:
    errors: list[str] = []
    if len(summaries) != expected_count:
        errors.append("valid_episode_count")
    if lifecycle_errors:
        errors.append("lifecycle_errors")
    if any(not item.get("resolved_by_episode_id") for item in invalid_attempts):
        errors.append("unresolved_invalid_attempt")
    infrastructure_attempts = [
        item for item in invalid_attempts
        if item.get("reason") == "controller_or_lifecycle_invalid"
    ]
    if len(infrastructure_attempts) > 2:
        errors.append("infrastructure_replacement_limit_exceeded")
    valid_by_id = {str(item.get("episode_id")): item for item in summaries}
    for attempt in infrastructure_attempts:
        replacement_id = str(attempt.get("resolved_by_episode_id") or "")
        replacement = valid_by_id.get(replacement_id)
        if replacement is None or str(attempt.get("episode_id")) not in (
            replacement.get("resolves_invalid_episode_ids") or []
        ):
            errors.append("invalid_replacement_bidirectional_link_mismatch")
    if any(item.get("evaluator_reward") is None for item in summaries):
        errors.append("missing_reward")
    if any(
        int(((step.get("model_call") or {}).get("raven_meta") or {}).get("transport_attempts") or 0) != 1
        for item in summaries
        for step in item.get("steps", [])
    ):
        errors.append("transport_attempt_not_one")
    if any(
        int(((item.get("memory_mechanism") or {}).get("decision_boundary") or {}).get("model_calls_added") or 0) != 0
        or bool(((item.get("memory_mechanism") or {}).get("decision_boundary") or {}).get("guard_enabled"))
        or int(((item.get("memory_mechanism") or {}).get("decision_boundary") or {}).get("action_override_count") or 0) != 0
        or int(((item.get("memory_mechanism") or {}).get("decision_boundary") or {}).get("forced_termination_count") or 0) != 0
        for item in summaries
    ):
        errors.append("intervention_boundary_violation")
    return errors


__all__ = [name for name in globals() if name.isupper()] + [
    "canonical_json_sha256", "content_sha256", "exact_completion_errors",
    "file_sha256", "gate5_report", "preservation_report", "source_freeze_payload",
    "validate_launch_receipt", "validate_preflight_report", "validate_source_freeze",
]
