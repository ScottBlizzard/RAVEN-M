"""Audited A7 gated-continuation planning with immutable parent evidence.

The A7 memory mechanism is unchanged.  This module only repairs the campaign
schedule after seven valid episodes: retain those episodes, run the three
missing A0-preservation tasks first, fail fast on any scientific loss, and
only then release the remaining untested tasks.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from raven_m.official_qwen_mobile.a678_contract import (
    A0_PRESERVATION_TASKS,
    TASK_COUNT,
    TASK_SEED,
    json_sha256,
)


PLAN_SCHEMA = "a7_gated_continuation_plan_v1"
PARENT_EXPERIMENT_ID = "A7_GOAL_ITEM_LEDGER_QWEN3VL32B_AW_HARD_S20260806_V1"
CONTINUATION_EXPERIMENT_ID = (
    "A7_GOAL_ITEM_LEDGER_QWEN3VL32B_AW_HARD_S20260806_V1_GATED_CONTINUATION"
)
MECHANISM_ID = "a7_deterministic_active_goal_item_status_ledger_v1"
PARENT_VALID_TASKS = (
    "BrowserMultiply",
    "ExpenseAddMultipleFromGallery",
    "ExpenseAddMultipleFromMarkor",
    "ExpenseDeleteMultiple2",
    "MarkorCreateNoteAndSms",
    "MarkorMergeNotes",
    "MarkorTranscribeVideo",
)
MISSING_GATE_TASKS = tuple(
    task for task in A0_PRESERVATION_TASKS if task != "ExpenseDeleteMultiple2"
)


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _key(summary: dict[str, Any]) -> tuple[str, int]:
    return str(summary.get("task_name")), int(summary.get("seed", -1))


def _summary_valid(summary: dict[str, Any]) -> bool:
    if summary.get("error") is not None or summary.get("evaluator_reward") is None:
        return False
    if summary.get("lifecycle_errors"):
        return False
    return all(
        int(
            ((step.get("model_call") or {}).get("raven_meta") or {}).get(
                "transport_attempts"
            )
            or 0
        )
        == 1
        for step in summary.get("steps") or []
    )


def load_parent_snapshot(
    *, parent_suite_dir: Path, canonical_expected_keys: list[tuple[str, int]]
) -> dict[str, Any]:
    """Validate and freeze the seven valid parent episodes without rewriting them."""

    parent_suite_dir = parent_suite_dir.resolve()
    signature_path = parent_suite_dir / "run_signature.json"
    checkpoint_path = parent_suite_dir / "checkpoint.json"
    if not signature_path.is_file() or not checkpoint_path.is_file():
        raise RuntimeError("A7 parent signature/checkpoint is missing")
    signature = _load(signature_path)
    checkpoint = _load(checkpoint_path)
    errors: list[str] = []
    if signature.get("experiment_id") != PARENT_EXPERIMENT_ID:
        errors.append("parent_experiment_id_drift")
    if signature.get("method") != MECHANISM_ID:
        errors.append("parent_mechanism_drift")
    if checkpoint.get("status") != "stopped_invalid_episode":
        errors.append("parent_checkpoint_status_drift")
    summaries = list(checkpoint.get("valid_summaries") or [])
    expected_parent_keys = [
        (task_name, TASK_SEED) for task_name in PARENT_VALID_TASKS
    ]
    observed_parent_keys = [_key(summary) for summary in summaries]
    if observed_parent_keys != expected_parent_keys:
        errors.append("parent_valid_task_sequence_drift")
    if canonical_expected_keys[: len(expected_parent_keys)] != expected_parent_keys:
        errors.append("canonical_manifest_parent_prefix_drift")
    if len(set(observed_parent_keys)) != len(observed_parent_keys):
        errors.append("parent_duplicate_valid_task")
    by_name = {str(item.get("task_name")): item for item in summaries}
    expense = by_name.get("ExpenseDeleteMultiple2")
    if not expense or expense.get("evaluator_reward") != 1.0 or not expense.get("success"):
        errors.append("parent_expense_preservation_success_missing")
    if any(name in by_name for name in MISSING_GATE_TASKS):
        errors.append("parent_already_contains_missing_gate_task")

    episode_references: list[dict[str, Any]] = []
    for summary in summaries:
        if not _summary_valid(summary):
            errors.append(f"parent_episode_invalid:{summary.get('episode_id')}")
            continue
        episode_id = str(summary.get("episode_id") or "")
        episode_path = parent_suite_dir / "episodes" / episode_id / "episode.json"
        if not episode_path.is_file():
            errors.append(f"parent_episode_file_missing:{episode_id}")
            continue
        episode = _load(episode_path)
        if json_sha256(episode) != json_sha256(summary):
            errors.append(f"parent_checkpoint_episode_mismatch:{episode_id}")
        episode_references.append(
            {
                "task_name": summary["task_name"],
                "seed": int(summary["seed"]),
                "episode_id": episode_id,
                "episode_json": str(episode_path),
                "episode_json_sha256": file_sha256(episode_path),
                "evaluator_reward": summary["evaluator_reward"],
                "success": bool(summary["success"]),
            }
        )
    if errors:
        raise RuntimeError(f"A7 parent validation failed: {errors}")
    return {
        "parent_suite_id": parent_suite_dir.name,
        "parent_suite_dir": str(parent_suite_dir),
        "parent_run_signature_sha256": file_sha256(signature_path),
        "parent_checkpoint_sha256": file_sha256(checkpoint_path),
        "parent_checkpoint_status": checkpoint["status"],
        "parent_valid_episode_count": len(summaries),
        "parent_invalid_attempt_count": len(checkpoint.get("invalid_attempts") or []),
        "episode_references": episode_references,
        "summaries": summaries,
        "invalid_attempts": list(checkpoint.get("invalid_attempts") or []),
    }


def build_plan(
    *,
    parent_suite_dir: Path,
    canonical_specs: list[dict[str, Any]],
    manifest_path: Path,
) -> dict[str, Any]:
    canonical_expected_keys = [
        (str(item["task_class"]), int(item["task_seed"])) for item in canonical_specs
    ]
    if len(canonical_expected_keys) != TASK_COUNT:
        raise RuntimeError("A7 continuation requires exactly 19 canonical tasks")
    parent = load_parent_snapshot(
        parent_suite_dir=parent_suite_dir,
        canonical_expected_keys=canonical_expected_keys,
    )
    imported = {(str(item["task_name"]), int(item["seed"])) for item in parent["summaries"]}
    by_name = {str(item["task_class"]): item for item in canonical_specs}
    missing_gate_keys = [(name, TASK_SEED) for name in MISSING_GATE_TASKS]
    if any(name not in by_name for name in MISSING_GATE_TASKS):
        raise RuntimeError("A7 continuation manifest is missing a preservation task")
    remaining_keys = [
        key
        for key in canonical_expected_keys
        if key not in imported and key not in set(missing_gate_keys)
    ]
    execution_schedule = list(missing_gate_keys) + remaining_keys
    if len(execution_schedule) != TASK_COUNT - len(imported):
        raise RuntimeError("A7 continuation schedule does not close the 19 unique tasks")
    return {
        "schema": PLAN_SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "generation_calls": 0,
        "experiment_id": CONTINUATION_EXPERIMENT_ID,
        "mechanism_id": MECHANISM_ID,
        "protocol_amendment": "campaign_schedule_only_memory_mechanism_unchanged",
        "parent": {
            key: value
            for key, value in parent.items()
            if key not in {"summaries", "invalid_attempts"}
        },
        "manifest_sha256": file_sha256(manifest_path.resolve()),
        "canonical_expected_keys": [list(key) for key in canonical_expected_keys],
        "canonical_expected_keys_sha256": json_sha256(canonical_expected_keys),
        "already_valid_keys": [
            [str(item["task_name"]), int(item["seed"])] for item in parent["summaries"]
        ],
        "already_valid_count": len(parent["summaries"]),
        "preservation_gate": {
            "all_tasks": list(A0_PRESERVATION_TASKS),
            "parent_successes": ["ExpenseDeleteMultiple2"],
            "missing_tasks_in_execution_order": list(MISSING_GATE_TASKS),
            "required_total_successes": 4,
            "scientific_failure_fail_fast": True,
            "infrastructure_invalid_retry_same_task_only": True,
        },
        "execution_schedule": [list(key) for key in execution_schedule],
        "remaining_after_gate_count": len(remaining_keys),
        "full_result_policy": (
            "retain_parent_7_then_require_remaining_gate_3_of_3_then_run_remaining_9"
        ),
        "claim_boundary": (
            "transparent_post_7_protocol_amendment_not_a_pristine_single_preregistered_suite"
        ),
    }


def validate_plan(
    *,
    plan_path: Path,
    parent_suite_dir: Path,
    canonical_specs: list[dict[str, Any]],
    manifest_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    plan = _load(plan_path.resolve())
    if plan.get("schema") != PLAN_SCHEMA or plan.get("status") != "pass":
        raise RuntimeError("A7 continuation plan identity/status invalid")
    if plan.get("generation_calls") != 0:
        raise RuntimeError("A7 continuation plan is not zero-generation")
    rebuilt = build_plan(
        parent_suite_dir=parent_suite_dir,
        canonical_specs=canonical_specs,
        manifest_path=manifest_path,
    )
    ignored = {"created_at"}
    for key in sorted(set(plan) | set(rebuilt)):
        if key not in ignored and plan.get(key) != rebuilt.get(key):
            raise RuntimeError(f"A7 continuation plan drift: {key}")
    canonical_expected_keys = [
        (str(item["task_class"]), int(item["task_seed"])) for item in canonical_specs
    ]
    parent = load_parent_snapshot(
        parent_suite_dir=parent_suite_dir,
        canonical_expected_keys=canonical_expected_keys,
    )
    return plan, parent


def gate_report(summaries: list[dict[str, Any]]) -> dict[str, Any]:
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
    failed = [row["task_name"] for row in rows if row["present"] and not row["success"]]
    missing = [row["task_name"] for row in rows if not row["present"]]
    status = "failed" if failed else ("passed" if not missing else "pending")
    return {
        "definition": "blocking_A0_4_of_4_capability_preservation_gate",
        "required_for_suite_continuation": True,
        "status": status,
        "success_count": sum(int(row["success"]) for row in rows),
        "failed_tasks": failed,
        "missing_tasks": missing,
        "next_gate_task": missing[0] if missing else None,
        "rows": rows,
    }


def canonicalize_summaries(
    summaries: list[dict[str, Any]], expected_keys: list[tuple[str, int]]
) -> list[dict[str, Any]]:
    by_key = {_key(summary): summary for summary in summaries}
    if len(by_key) != len(summaries):
        raise RuntimeError("A7 continuation contains duplicate valid summaries")
    return [by_key[key] for key in expected_keys if key in by_key]
