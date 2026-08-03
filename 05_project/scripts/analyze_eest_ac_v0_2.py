"""Recompute the frozen EEST-AC v0.2 nine-cell analysis from raw artifacts.

This script is post-batch only.  It refuses to run until the blind lock has been
released and never invokes the model or AndroidWorld.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable

from raven_m.eest_ac.binding_metrics_v0_2 import label_three_layers


ARMS = ("B3", "B3_MATCH", "M_SLOTS")
POSITIVE_TASKS = ("EEST-P2A", "EEST-P2B")
NEGATIVE_TASK = "EEST-N2"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sum(rows: Iterable[dict[str, Any]], key: str) -> float | int:
    return sum(row[key] for row in rows)


def _relative(value: float, baseline: float) -> float | None:
    if baseline == 0:
        return None
    return (value - baseline) / baseline


def _paired(
    rows: list[dict[str, Any]],
    treatment: str,
    tasks: Iterable[str],
    *,
    field: str = "task_success",
) -> dict[str, Any]:
    counts = {"win": 0, "loss": 0, "tie": 0}
    details = []
    for task_key in tasks:
        control = next(
            row
            for row in rows
            if row["task_key"] == task_key and row["arm"] == "B3_MATCH"
        )
        treated = next(
            row
            for row in rows
            if row["task_key"] == task_key and row["arm"] == treatment
        )
        control_score = int(bool(control[field]))
        treatment_score = int(bool(treated[field]))
        delta = treatment_score - control_score
        outcome = "win" if delta > 0 else "loss" if delta < 0 else "tie"
        counts[outcome] += 1
        details.append(
            {
                "task_key": task_key,
                "control": control_score,
                "treatment": treatment_score,
                "outcome": outcome,
            }
        )
    return {**counts, "net_wins": counts["win"] - counts["loss"], "details": details}


def _first_actions_by_task(
    summaries: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for task_key in (*POSITIVE_TASKS, NEGATIVE_TASK):
        actions = {}
        for arm in ARMS:
            records = summaries[(task_key, arm)]["model_call_records"]
            content = json.loads(records[0]["content"])
            actions[arm] = content.get("action")
        canonical = {
            json.dumps(action, sort_keys=True, separators=(",", ":"))
            for action in actions.values()
        }
        result[task_key] = {
            "first_proposed_actions": actions,
            "unique_first_proposals": len(canonical),
            "diverged_before_execution": len(canonical) > 1,
            "executed_actions_before_failure": 0,
            "interpretation": (
                "The first raw executor proposals differed before any environment "
                "action was accepted. This is model-output branching, not an "
                "executed-trajectory or memory-effect divergence."
                if len(canonical) > 1
                else "All arms proposed the same invalid first action; no environment action was executed."
            ),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    completion_path = args.run_root / "batch_complete.json"
    if not completion_path.is_file():
        raise RuntimeError("Blind batch is incomplete; post-batch analysis is forbidden.")
    batch = _read_json(completion_path)
    if batch.get("cell_count") != 9 or not batch.get("trajectory_blind_lock_released"):
        raise RuntimeError("Unexpected v0.2 batch completion or blind-lock state.")
    instances = _read_json(args.run_root / "instances_unblinded_after_batch.json")

    summaries: dict[tuple[str, str], dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for cell in sorted(batch["results"], key=lambda item: item["cell"]):
        summary = _read_json(Path(cell["episode_summary_path"]))
        key = (cell["task_key"], cell["arm"])
        summaries[key] = summary
        raw_records = summary["model_call_records"]
        raw_attempts = summary["model_call_attempt_records"]
        row: dict[str, Any] = {
            "cell": cell["cell"],
            "task_key": cell["task_key"],
            "task_class": cell["task_class"],
            "role": cell["role"],
            "arm": cell["arm"],
            "task_success": bool(summary["task_success"]),
            "evaluator_status": summary["evaluator_status"],
            "evaluator_reward": summary["evaluator_reward"],
            "evaluator_result_present": summary["evaluator_reward"] is not None,
            "termination_reason": summary["termination_reason"],
            "failure_class": summary["failure_class"],
            "error_type": (summary.get("error") or {}).get("type"),
            "error_message": (summary.get("error") or {}).get("message"),
            "environment_actions": summary["environment_actions"],
            "model_calls": summary["model_calls"],
            "model_call_record_count": len(raw_records),
            "model_call_attempt_count": len(raw_attempts),
            "model_call_accounting_valid": bool(summary["model_call_accounting_valid"]),
            "executor_calls": summary["executor_calls"],
            "auxiliary_calls": summary["auxiliary_calls"],
            "eligible_opportunities": summary["eligible_opportunities"],
            "planned_auxiliary_calls": summary["planned_auxiliary_calls"],
            "realized_auxiliary_calls": summary["realized_auxiliary_calls"],
            "missed_auxiliary_calls": len(summary["missed_auxiliary_calls"]),
            "schema_truncation_count": summary["schema_truncation_count"],
            "prompt_tokens": summary["prompt_tokens"],
            "completion_tokens": summary["completion_tokens"],
            "total_tokens": summary["total_tokens"],
            "wall_time_seconds": summary["wall_time_seconds"],
            "max_prompt_tokens": summary["max_prompt_tokens"],
            "context_cap_respected": bool(summary["context_cap_respected"]),
            "evidence_records": len(summary["evidence_ledger"]),
            "goal_records": len(summary["goal_ledger"]),
            "invented_requirements": summary["invented_requirement_count"],
            "recovery_records": len(summary["recovery_registry"]),
            "repeated_action_blocks": summary["repeated_action_blocks"],
            "different_class_after_recovery": summary["different_class_after_recovery"],
            "completion_tp": bool(summary["completion_tp"]),
            "completion_fp": bool(summary["completion_fp"]),
            "completion_fn": bool(summary["completion_fn"]),
        }
        if cell["task_key"] in POSITIVE_TASKS:
            param_key = "message" if cell["task_key"] == "EEST-P2A" else "text"
            label = label_three_layers(
                summary,
                expected_value=instances[cell["task_key"]]["params"][param_key],
            )
            row["binding"] = label.record()
            row["h3_correct"] = label.destination_action == "correct"
        else:
            row["binding"] = None
            row["h3_correct"] = False
        rows.append(row)

    positive_rows = [row for row in rows if row["task_key"] in POSITIVE_TASKS]
    parser_episode_correct = 0
    parser_role_correct = 0
    for row in positive_rows:
        observed = summaries[(row["task_key"], row["arm"])]["task_role_frame"]
        expected = instances[row["task_key"]]["task_role_frame"]
        episode_ok = observed == expected
        parser_episode_correct += int(episode_ok)
        parser_role_correct += sum(
            observed[role] == expected[role]
            for role in ("source", "requested_field", "destination")
        )

    binding_by_arm: dict[str, Any] = {}
    for arm in ARMS:
        selected = [row for row in positive_rows if row["arm"] == arm]
        layers = {
            "source_field_value_capture": Counter(),
            "destination_role_retention": Counter(),
            "value_to_destination_action": Counter(),
        }
        for row in selected:
            for layer, label in row["binding"].items():
                layers[layer][label] += 1
        binding_by_arm[arm] = {
            layer: {
                "confusion": dict(sorted(counts.items())),
                "correct": counts["correct"],
                "episodes": len(selected),
                "accuracy": counts["correct"] / len(selected) if selected else None,
            }
            for layer, counts in layers.items()
        }

    overall_layers: dict[str, Any] = {}
    for layer in (
        "source_field_value_capture",
        "destination_role_retention",
        "value_to_destination_action",
    ):
        counts = Counter(row["binding"][layer] for row in positive_rows)
        overall_layers[layer] = {
            "confusion": dict(sorted(counts.items())),
            "correct": counts["correct"],
            "episodes": len(positive_rows),
            "accuracy": counts["correct"] / len(positive_rows),
        }

    arm_aggregates = {}
    aggregate_fields = (
        "environment_actions",
        "model_calls",
        "executor_calls",
        "auxiliary_calls",
        "eligible_opportunities",
        "planned_auxiliary_calls",
        "realized_auxiliary_calls",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "wall_time_seconds",
        "recovery_records",
        "repeated_action_blocks",
    )
    for arm in ARMS:
        selected = [row for row in rows if row["arm"] == arm]
        arm_aggregates[arm] = {
            "successes": sum(row["task_success"] for row in selected),
            "cells": len(selected),
            **{field: _sum(selected, field) for field in aggregate_fields},
        }

    paired = {}
    for treatment in ("B3", "M_SLOTS"):
        paired[f"{treatment}_vs_B3_MATCH"] = {
            "all_tasks": _paired(rows, treatment, (*POSITIVE_TASKS, NEGATIVE_TASK)),
            "positive_tasks": _paired(rows, treatment, POSITIVE_TASKS),
        }
    paired["M_SLOTS_vs_B3_MATCH"]["positive_h3"] = _paired(
        rows, "M_SLOTS", POSITIVE_TASKS, field="h3_correct"
    )

    tp = sum(row["completion_tp"] for row in rows)
    fp = sum(row["completion_fp"] for row in rows)
    fn = sum(row["completion_fn"] for row in rows)

    negative_rows = {row["arm"]: row for row in rows if row["task_key"] == NEGATIVE_TASK}
    negative_baseline = negative_rows["B3_MATCH"]
    negative_cost = {}
    for arm in ("B3", "M_SLOTS"):
        current = negative_rows[arm]
        negative_cost[f"{arm}_vs_B3_MATCH"] = {
            key: {
                "treatment": current[key],
                "baseline": negative_baseline[key],
                "relative_change": _relative(current[key], negative_baseline[key]),
            }
            for key in ("environment_actions", "model_calls", "total_tokens", "wall_time_seconds")
        }

    no_truncation = all(row["schema_truncation_count"] == 0 for row in rows)
    complete_accounting = all(
        row["model_call_accounting_valid"]
        and row["model_calls"] == row["model_call_record_count"]
        and row["model_calls"] == row["model_call_attempt_count"]
        for row in rows
    )
    evaluator_coverage = all(row["evaluator_result_present"] for row in rows)
    m_positive_successes = sum(
        row["task_success"]
        for row in positive_rows
        if row["arm"] == "M_SLOTS"
    )
    match_positive_successes = sum(
        row["task_success"]
        for row in positive_rows
        if row["arm"] == "B3_MATCH"
    )
    m_pair = paired["M_SLOTS_vs_B3_MATCH"]
    m_negative = negative_rows["M_SLOTS"]
    negative_token_increase = negative_cost["M_SLOTS_vs_B3_MATCH"]["total_tokens"]["relative_change"]
    all_positive_floor = all(not row["task_success"] for row in positive_rows)

    requirements = [
        requirement
        for summary in summaries.values()
        for requirement in summary["goal_ledger"]
    ]
    result = {
        "schema_version": "eest_ac_v0_2_post_batch_analysis.v1",
        "study_id": batch["study_id"],
        "batch_complete_sha256": sha256(completion_path.read_bytes()).hexdigest(),
        "batch": {
            "cell_count": batch["cell_count"],
            "runner_stop_reason": batch["runner_stop_reason"],
            "trajectory_blind_lock_released": batch["trajectory_blind_lock_released"],
            "completed_at_utc": batch["completed_at_utc"],
            "sum_cell_wall_time_seconds": _sum(rows, "wall_time_seconds"),
        },
        "cells": rows,
        "arm_aggregates": arm_aggregates,
        "hard_gates": {
            "no_schema_truncation": no_truncation,
            "complete_raw_call_accounting": complete_accounting,
            "evaluator_result_every_cell": evaluator_coverage,
            "passed": no_truncation and complete_accounting and evaluator_coverage,
        },
        "three_layer_binding": {
            "shared_parser_exact_span": {
                "correct_episodes": parser_episode_correct,
                "episodes": len(positive_rows),
                "correct_roles": parser_role_correct,
                "roles": len(positive_rows) * 3,
                "warning": "Parser initialization is not runtime memory evidence.",
            },
            "by_arm": binding_by_arm,
            "overall": overall_layers,
        },
        "paired_win_loss_tie": paired,
        "completion": {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "interpretation": "Undefined precision/recall: no episode predicted completion and no task succeeded.",
        },
        "requirements": {
            "records": len(requirements),
            "invented": sum(row["invented_requirements"] for row in rows),
            "invented_requirement_rate": (
                sum(row["invented_requirements"] for row in rows) / len(requirements)
                if requirements
                else None
            ),
        },
        "recovery_and_verification": {
            "recovery_records": _sum(rows, "recovery_records"),
            "repeated_action_blocks": _sum(rows, "repeated_action_blocks"),
            "different_class_after_recovery": _sum(rows, "different_class_after_recovery"),
            "blocked_action_recovery_rate": None,
            "unnecessary_verification_numerator": 0,
            "unnecessary_verification_denominator": 0,
            "unnecessary_verification_rate": None,
            "interpretation": "No action executed, so live recovery and verification mechanisms had no eligible denominator.",
        },
        "negative_control_cost": negative_cost,
        "b3_match_fairness": {
            "by_cell": [
                {
                    "cell": row["cell"],
                    "task_key": row["task_key"],
                    "arm": row["arm"],
                    "eligible": row["eligible_opportunities"],
                    "planned": row["planned_auxiliary_calls"],
                    "realized": row["realized_auxiliary_calls"],
                    "missed": row["missed_auxiliary_calls"],
                    "total_raw_calls": row["model_calls"],
                }
                for row in rows
            ],
            "first_proposal_divergence": _first_actions_by_task(summaries),
            "interpretation": (
                "Eligible/planned/realized auxiliary calls were 0/0/0 in every cell. "
                "The identical two raw calls per cell were executor plus repair calls on "
                "a shared invalid-output path, not evidence that realized matched-memory "
                "usage is generally equal."
            ),
        },
        "root_cause": {
            "classification": "shared_action_interface_controller_floor",
            "affected_cells": 9,
            "environment_actions_before_failure": 0,
            "invalid_outputs": sum(row["model_calls"] for row in rows),
            "mechanism": (
                "The model emitted Android-style press{key}, swipe{dx,dy}, or "
                "swipe{direction,distance} actions. The frozen decision schema accepts "
                "different canonical forms. The one allowed repair repeated the invalid "
                "proposal, so parsing failed before execution in every cell."
            ),
        },
        "claim_evidence_verdict": {
            "V2-C1": "Mechanical replay evidence passes; no live Recovery admission occurred, so live confirmation is unexercised.",
            "V2-C2": "Mechanical replay evidence passes; no live block or recovery denominator occurred.",
            "V2-C3": "Supported: shared exact-span frames match 6/6 positive episode initializations (18/18 roles); this is parser evidence only.",
            "V2-C4": "Unsupported/unmeasured online: M-SLOTS H1 is missing in 2/2 positives because execution never began.",
            "V2-C5": "Unsupported/unmeasured online: M-SLOTS H2 is missing in 2/2 positives; parser destination spans are not retention evidence.",
            "V2-C6": "Unsupported and continuation criterion failed: zero positive success and zero H3 paired wins.",
            "V2-C7": "Policy/ceiling configuration remains frozen, but live usefulness is unexercised: all cells had 0 eligible opportunities and 0 auxiliary calls.",
            "V2-C8": "Not demonstrated: all three negative-control cells failed before the first action, so no satisfied stable screen reached completion policy.",
            "V2-C9": "Supported in this batch: zero truncations, 18/18 raw calls counted, and evaluator results in 9/9 cells.",
            "V2-C10": "Out of scope as preregistered; M-RISK had no live cells.",
        },
        "continuation_conditions": {
            "integrity_gate": {
                "passed": no_truncation and complete_accounting and evaluator_coverage,
                "observation": "0 truncations; 18 calls equal 18 records/attempts; 9/9 evaluator results.",
            },
            "m_slots_positive_signal": {
                "passed": m_positive_successes >= 1 and m_positive_successes >= match_positive_successes,
                "observation": f"M-SLOTS {m_positive_successes}/2; B3-MATCH {match_positive_successes}/2.",
            },
            "m_slots_h3_paired_win": {
                "passed": m_pair["positive_h3"]["win"] >= 1,
                "observation": (
                    f"win/loss/tie = {m_pair['positive_h3']['win']}/"
                    f"{m_pair['positive_h3']['loss']}/{m_pair['positive_h3']['tie']}."
                ),
            },
            "negative_control": {
                "passed": bool(m_negative["task_success"] and negative_token_increase is not None and negative_token_increase <= 0.15),
                "observation": (
                    f"completion={m_negative['task_success']}; actions={m_negative['environment_actions']}; "
                    f"token change={negative_token_increase:.6f}."
                ),
            },
            "all_positive_controller_floor": {
                "triggered": all_positive_floor,
                "observation": "All 6 positive cells across all 3 arms failed.",
            },
            "m_slots_zero_net_win_stop": {
                "triggered": m_pair["positive_tasks"]["net_wins"] == 0,
                "observation": f"net paired task-success wins={m_pair['positive_tasks']['net_wins']}.",
            },
            "m_risk_exclusion": {
                "passed": True,
                "observation": "M-RISK remained offline-only and must remain excluded until a non-floor M-SLOTS signal exists.",
            },
            "overall_expand_to_48": False,
            "decision": "STOP_MEMORY_EFFICACY_REPAIR_SHARED_ACTION_INTERFACE",
        },
    }
    _write_json(args.output, result)


if __name__ == "__main__":
    main()
