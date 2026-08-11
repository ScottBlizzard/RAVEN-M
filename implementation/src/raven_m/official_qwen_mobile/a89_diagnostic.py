"""Contract helpers for the A8-v2/A9 four-task diagnostic replication.

This campaign is deliberately separate from the terminal prospective gate
suites.  It reruns all four A0-success tasks without reward fail-fast so that
each arm has a complete four-task diagnostic profile.  It never releases the
remaining fifteen tasks and never repairs or overwrites the original gate.
"""

from __future__ import annotations

from typing import Any, Iterable

from raven_m.official_qwen_mobile.a678_contract import (
    A0_PRESERVATION_TASKS,
    TASK_SEED,
)


EXPERIMENT_IDS = {
    "a8v2": "A8V2_A0_FOUR_TASK_DIAGNOSTIC_REPLICATION_S20260806_R1",
    "a9": "A9_A0_FOUR_TASK_DIAGNOSTIC_REPLICATION_S20260806_R1",
}

CLAIM_BOUNDARY = (
    "diagnostic_replication_only_not_gate_repair_not_full19_release_"
    "original_terminal_gate_suites_remain_authoritative"
)


def select_four_task_specs(specs: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the frozen seed-20260806 gate tasks in canonical gate order."""

    by_name = {
        str(item["task_class"]): item
        for item in specs
        if int(item["task_seed"]) == TASK_SEED
        and str(item["task_class"]) in A0_PRESERVATION_TASKS
    }
    missing = [name for name in A0_PRESERVATION_TASKS if name not in by_name]
    if missing:
        raise RuntimeError(f"A8/A9 diagnostic tasks missing from manifest: {missing}")
    selected = [by_name[name] for name in A0_PRESERVATION_TASKS]
    if len(selected) != 4:
        raise RuntimeError("A8/A9 diagnostic did not resolve exactly four tasks")
    return selected


def completion_errors(
    *,
    summaries: list[dict[str, Any]],
    expected_keys: list[tuple[str, int]],
    invalid_attempts: list[dict[str, Any]],
    lifecycle_errors: list[dict[str, Any]],
) -> list[str]:
    """Validate infrastructure closure while treating reward failure as data."""

    errors: list[str] = []
    observed = [
        (str(item.get("task_name")), int(item.get("seed", -1)))
        for item in summaries
    ]
    if len(summaries) != 4 or observed != expected_keys:
        errors.append("exact_4_ordered_task_seed_closure_failed")
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
                errors.append(
                    f"episode_{index}_step_{step_index}_transport_attempts_not_one"
                )
    return errors


def report(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    """Produce a nonblocking four-task diagnostic table."""

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
                "episode_id": summary.get("episode_id") if summary else None,
            }
        )
    return {
        "definition": "nonblocking_A0_four_task_diagnostic_replication",
        "diagnostic_only": True,
        "required_for_suite_continuation": False,
        "releases_remaining_15": False,
        "success_count": sum(int(row["success"]) for row in rows),
        "complete": all(row["present"] for row in rows),
        "rows": rows,
    }
