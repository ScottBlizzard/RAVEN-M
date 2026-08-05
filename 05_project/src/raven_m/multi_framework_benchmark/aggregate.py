"""Predeclared process metrics and normalized output names."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from .action_normalizer import exact_fingerprint, maximum_run


REQUIRED_OUTPUTS = (
    "cells.csv", "cells.parquet", "actions.csv", "actions.parquet",
    "feedback_events.csv", "arm_summary.csv", "task_by_arm.csv",
    "paired_common_backbone_results.csv", "native_system_results.csv",
    "privilege_matrix.csv", "failure_edge_counts.csv",
    "process_metric_summary.csv", "cost_summary.csv",
    "blind_annotation_queue.jsonl", "run_manifest.json", "manifest.sha256",
)


def process_metrics(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(events)
    actions = [row["action_canonical"] for row in rows
               if row.get("action_canonical") is not None and row.get("action_execute_status") == "EXECUTED"]
    feedback_rows = [row for row in rows if row.get("feedback_event")]
    exact_repeat_after_feedback = 0
    for row in feedback_rows:
        index = rows.index(row)
        previous = next((r.get("action_canonical") for r in reversed(rows[:index]) if r.get("action_canonical")), None)
        following = next((r.get("action_canonical") for r in rows[index + 1:] if r.get("action_canonical")), None)
        if previous and following and exact_fingerprint(previous) == exact_fingerprint(following):
            exact_repeat_after_feedback += 1
    strict_no_effect = sum(row.get("pixel_effect_class") == "STRICT_NO_EFFECT" and row.get("tree_effect_class") in {None, "STRICT_NO_EFFECT"} for row in rows)
    executed = max(1, len(actions))
    finish_claims = sum(bool(row.get("finish_claim")) for row in rows)
    rejected_finishes = sum(bool(row.get("finish_claim")) and not bool(row.get("evaluator_reward")) for row in rows)
    return {
        "maximum_exact_action_run": maximum_run(actions),
        "exact_action_run_ge_3": maximum_run(actions) >= 3,
        "strict_no_observable_effect_action_rate": strict_no_effect / executed,
        "feedback_followed_by_exact_repeat_rate": exact_repeat_after_feedback / max(1, len(feedback_rows)),
        "evaluator_rejected_finish_rate": rejected_finishes / max(1, finish_claims),
        "failure_edge_counts": dict(Counter(row.get("failure_edge") for row in rows if row.get("failure_edge"))),
    }
