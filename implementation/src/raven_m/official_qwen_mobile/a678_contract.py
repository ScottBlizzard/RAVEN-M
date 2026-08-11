"""Frozen scientific contract for the staged A6-A9 memory experiments."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
OFFICIAL_SYSTEM_PROMPT_SHA256 = "9d060af15f62acb31b9fb197649ec001d4096491d7fb102de929316944b3e26d"
TASK_SEED = 20260806
GENERATION_SEED = 3407
TASK_COUNT = 19
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
A678_PREFLIGHT_REPORT = REPOSITORY_ROOT / "evidence/a678/A678_ZERO_GENERATION_PREFLIGHT.json"
A678_LAUNCH_RECEIPT = REPOSITORY_ROOT / "evidence/a678/A678_LIVE_SERVER_RECEIPT.json"
MODEL_REALPATH = "/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope"
MODEL_MANIFEST_SHA256 = "18e0909c7d993853d6d0f62443461a74009754f90db026a1723cab80121c7872"

A0_PRESERVATION_TASKS = (
    "ExpenseDeleteMultiple2",
    "RetroSavePlaylist",
    "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
)

A678_MECHANISMS = {
    "a6": "a6_short_transition_attested_episodic_buffer_v1",
    "a7": "a7_deterministic_active_goal_item_status_ledger_v1",
    "a8": "a8_exact_visual_revisit_action_outcome_cache_v1",
    "a8v2": "a8_failure_aware_exact_revisit_memory_v2",
    "a9": "a9_sparse_query_and_navigation_recurrence_canary_v1",
}

A678_CONFIGS = {
    "a6": "implementation/configs/a6_short_episodic_hard_seed20260806.json",
    "a7": "implementation/configs/a7_goal_item_ledger_hard_seed20260806.json",
    "a8": "implementation/configs/a8_exact_revisit_cache_hard_seed20260806.json",
    "a8v2": "implementation/configs/a8_failure_aware_exact_revisit_v2_hard_seed20260806.json",
    "a9": "implementation/configs/a9_sparse_recurrence_canary_hard_seed20260806.json",
}

A7_CONTINUATION_CONFIG = (
    "implementation/configs/a7_goal_item_ledger_gated_continuation_seed20260806.json"
)

SOURCE_FILES = (
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/run_a678_arm.py",
    "implementation/scripts/prepare_a7_gated_continuation.py",
    "implementation/scripts/start_a7_gated_server.sh",
    "implementation/scripts/preflight_a678.py",
    "implementation/scripts/qualify_a678_live_server.py",
    "implementation/src/raven_m/__init__.py",
    "implementation/src/raven_m/env/__init__.py",
    "implementation/src/raven_m/official_qwen_mobile/a678_memory.py",
    "implementation/src/raven_m/official_qwen_mobile/a678_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/a7_continuation.py",
    "implementation/src/raven_m/official_qwen_mobile/a8_failure_aware_revisit.py",
    "implementation/src/raven_m/official_qwen_mobile/a9_recurrence_memory.py",
    "implementation/src/raven_m/official_qwen_mobile/a89_diagnostic.py",
    "implementation/src/raven_m/official_qwen_mobile/__init__.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/official_qwen_mobile/protocol.py",
    "implementation/src/raven_m/models/__init__.py",
    "implementation/src/raven_m/models/transformers_client.py",
    "implementation/src/raven_m/models/vllm_client.py",
    "implementation/src/raven_m/env/androidworld_adapter.py",
    "implementation/src/raven_m/multi_framework_benchmark/__init__.py",
    "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    "implementation/configs/a6_short_episodic_hard_seed20260806.json",
    "implementation/configs/a7_goal_item_ledger_hard_seed20260806.json",
    "implementation/configs/a7_goal_item_ledger_gated_continuation_seed20260806.json",
    "implementation/configs/a8_exact_revisit_cache_hard_seed20260806.json",
    "implementation/configs/a8_failure_aware_exact_revisit_v2_hard_seed20260806.json",
    "implementation/configs/a9_sparse_recurrence_canary_hard_seed20260806.json",
    "implementation/configs/androidworld_hard_v2_instances.json",
    "implementation/tests/official_qwen_mobile/test_a678_memory.py",
    "implementation/tests/official_qwen_mobile/test_a678_contract.py",
    "implementation/tests/official_qwen_mobile/test_a7_continuation.py",
    "implementation/tests/official_qwen_mobile/test_a8_failure_aware_revisit.py",
    "implementation/tests/official_qwen_mobile/test_a9_recurrence_memory.py",
    "implementation/tests/official_qwen_mobile/test_a89_diagnostic.py",
    "protocols/A678_INTEGRATION_PLAN.md",
    "protocols/A7_GATED_CONTINUATION_AMENDMENT_2026-08-11.md",
    "protocols/A8_EXACT_REVISIT_FAILURE_AWARE_V2_DESIGN_2026-08-11.md",
    "protocols/A9_SPARSE_RECURRENCE_CANARY_PREREG_2026-08-11.md",
    "protocols/A345_FAILURE_FORENSICS_AND_SUCCESSOR_CONSTRAINTS_2026-08-11.md",
    "protocols/A89_FOUR_TASK_DIAGNOSTIC_REPLICATION_AMENDMENT_2026-08-12.md",
    "GPT_PRO_MEMORY_MECHANISM_DESIGN_REQUEST_2026-08-12.md",
)

TERMINAL_SCIENTIFIC_STATUSES = frozenset(
    {"complete", "stopped_source_drift", "stopped_signature_drift"}
)


def json_sha256(value: Any) -> str:
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def current_source_freeze() -> dict[str, str]:
    missing = [name for name in SOURCE_FILES if not (REPOSITORY_ROOT / name).is_file()]
    if missing:
        raise RuntimeError(f"A6-A9 source closure incomplete: {missing}")
    return {name: file_sha256(REPOSITORY_ROOT / name) for name in SOURCE_FILES}


def validate_preflight_report(path: Path = A678_PREFLIGHT_REPORT) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    current = current_source_freeze()
    errors: list[str] = []
    if report.get("status") != "pass" or report.get("generation_calls") != 0:
        errors.append("status_or_generation_calls_invalid")
    if report.get("errors"):
        errors.append("preflight_errors_nonempty")
    if report.get("source_freeze") != current:
        errors.append("source_freeze_drift")
    if report.get("source_freeze_sha256") != json_sha256(current):
        errors.append("source_freeze_digest_drift")
    if errors:
        raise RuntimeError(f"A6-A9 preflight validation failed: {errors}")
    return report


def validate_launch_receipt(
    path: Path, *, preflight_path: Path = A678_PREFLIGHT_REPORT
) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "status": "pass",
        "generation_calls": 0,
        "served_model_id": MODEL_ID,
        "model_realpath": MODEL_REALPATH,
        "model_manifest_sha256": MODEL_MANIFEST_SHA256,
        "port": 18000,
        "a678_preflight_sha256": file_sha256(preflight_path),
    }
    errors = [f"{key}_drift" for key, value in expected.items() if receipt.get(key) != value]
    cmdline = [str(item) for item in receipt.get("process_cmdline") or []]
    if MODEL_REALPATH not in cmdline or MODEL_ID not in cmdline or "serve" not in cmdline:
        errors.append("process_cmdline_binding_missing")
    packages = receipt.get("packages") or {}
    if not all(str(packages.get(name) or "") for name in ("vllm", "torch", "transformers")):
        errors.append("runtime_packages_missing")
    if errors:
        raise RuntimeError(f"A6-A9 launch receipt invalid: {errors}")
    return receipt


def exact_completion_errors(
    *,
    summaries: list[dict[str, Any]],
    expected_keys: list[tuple[str, int]],
    invalid_attempts: list[dict[str, Any]],
    lifecycle_errors: list[dict[str, Any]],
) -> list[str]:
    """Reward is deliberately absent: task failure is data, not invalidity."""
    errors: list[str] = []
    observed = [(str(item.get("task_name")), int(item.get("seed", -1))) for item in summaries]
    if len(summaries) != TASK_COUNT or observed != expected_keys:
        errors.append("exact_19_ordered_task_seed_closure_failed")
    if len(set(observed)) != len(observed):
        errors.append("duplicate_task_seed_pair")
    if any(not item.get("resolved_by_episode_id") for item in invalid_attempts):
        errors.append("unresolved_infrastructure_invalid_attempt")
    if lifecycle_errors:
        errors.append("suite_lifecycle_error")
    for index, summary in enumerate(summaries):
        if summary.get("error") is not None or summary.get("evaluator_reward") is None:
            errors.append(f"episode_{index}_infrastructure_invalid")
        if summary.get("lifecycle_errors"):
            errors.append(f"episode_{index}_lifecycle_invalid")
        for step_index, step in enumerate(summary.get("steps") or []):
            attempts = int(
                ((step.get("model_call") or {}).get("raven_meta") or {}).get(
                    "transport_attempts"
                )
                or 0
            )
            if attempts != 1:
                errors.append(f"episode_{index}_step_{step_index}_transport_attempts_not_one")
    return errors


def preservation_report(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    by_name = {str(item.get("task_name")): item for item in summaries}
    rows = []
    for task_name in A0_PRESERVATION_TASKS:
        summary = by_name.get(task_name)
        rows.append(
            {
                "task_name": task_name,
                "present": summary is not None,
                "success": bool(summary and summary.get("success")),
                "reward": summary.get("evaluator_reward") if summary else None,
            }
        )
    return {
        "definition": "nonblocking_A0_success_preservation_monitor",
        "success_count": sum(int(row["success"]) for row in rows),
        "required_for_suite_continuation": False,
        "rows": rows,
    }
