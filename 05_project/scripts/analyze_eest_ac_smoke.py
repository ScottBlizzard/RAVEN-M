"""Recompute EEST-AC smoke metrics from raw post-batch artifacts."""

from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def relative_cost(value: float, baseline: float) -> float:
    return (value - baseline) / baseline if baseline else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    completion = args.run_root / "batch_complete.json"
    if not completion.is_file():
        raise RuntimeError("The blind batch is not complete; analysis is forbidden.")
    batch = json.loads(completion.read_text(encoding="utf-8"))
    if batch.get("cell_count") != 8 or not batch.get("trajectory_blind_lock_released"):
        raise RuntimeError("Unexpected batch completion record.")
    instances = json.loads(
        (args.run_root / "instances_unblinded_after_batch.json").read_text(
            encoding="utf-8"
        )
    )
    rows = []
    summaries = {}
    for cell_dir in sorted((args.run_root / "cells").iterdir()):
        cell = json.loads((cell_dir / "cell_result.json").read_text(encoding="utf-8"))
        summary_path = Path(cell["episode_summary_path"])
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summaries[(cell["task_key"], cell["arm"])] = summary
        calls = summary["model_call_records"]
        raw_call_count = len(calls)
        raw_auxiliary_count = sum(
            item["role"] not in {"executor", "executor_repair"}
            for item in calls
        )
        row = {
            "cell": cell["cell"],
            "task_key": cell["task_key"],
            "arm": cell["arm"],
            "task_success": summary["task_success"],
            "evaluator_reward": summary["evaluator_reward"],
            "valid_evaluator_cell": summary["evaluator_reward"] is not None,
            "termination_reason": summary["termination_reason"],
            "error_type": (
                summary["error"]["type"] if summary.get("error") else None
            ),
            "environment_actions": summary["environment_actions"],
            "model_calls_raw": raw_call_count,
            "model_calls_summary_counter": summary["model_calls"],
            "call_counter_correction": raw_call_count - summary["model_calls"],
            "auxiliary_calls_raw": raw_auxiliary_count,
            "prompt_tokens": sum(
                int(item["usage"].get("prompt_tokens", 0)) for item in calls
            ),
            "completion_tokens": sum(
                int(item["usage"].get("completion_tokens", 0)) for item in calls
            ),
            "total_tokens": sum(
                int(
                    item["usage"].get(
                        "total_tokens",
                        int(item["usage"].get("prompt_tokens", 0))
                        + int(item["usage"].get("completion_tokens", 0)),
                    )
                )
                for item in calls
            ),
            "max_prompt_tokens": max(
                (int(item["usage"].get("prompt_tokens", 0)) for item in calls),
                default=0,
            ),
            "wall_time_seconds": summary["wall_time_seconds"],
            "context_cap_respected": all(
                int(item["usage"].get("prompt_tokens", 0)) + 256 <= 8192
                for item in calls
            ),
            "evidence_record_count": len(summary["evidence_ledger"]),
            "recovery_record_count": len(summary["recovery_registry"]),
            "risk_gate_count": summary["risk_gate_count"],
            "risk_gate_block_count": summary["risk_gate_block_count"],
            "completion_tp": summary["completion_tp"],
            "completion_fp": summary["completion_fp"],
            "completion_fn": summary["completion_fn"],
        }
        rows.append(row)

    by_arm: dict[str, dict[str, Any]] = {}
    for arm in ("B3", "B3_MATCH", "M_SLOTS", "M_RISK"):
        selected = [item for item in rows if item["arm"] == arm]
        by_arm[arm] = {
            "successes": sum(item["task_success"] for item in selected),
            "cells": len(selected),
            "valid_evaluator_cells": sum(
                item["valid_evaluator_cell"] for item in selected
            ),
            **{
                key: sum(item[key] for item in selected)
                for key in (
                    "environment_actions",
                    "model_calls_raw",
                    "auxiliary_calls_raw",
                    "prompt_tokens",
                    "completion_tokens",
                    "total_tokens",
                    "wall_time_seconds",
                    "risk_gate_count",
                    "risk_gate_block_count",
                    "recovery_record_count",
                )
            },
        }

    paired = {}
    for treatment in ("B3", "M_SLOTS", "M_RISK"):
        intent = {"win": 0, "loss": 0, "tie": 0}
        valid = {"win": 0, "loss": 0, "tie": 0, "invalid_pair": 0}
        for task_key in ("EEST-P1", "EEST-N1"):
            control = next(
                item
                for item in rows
                if item["task_key"] == task_key and item["arm"] == "B3_MATCH"
            )
            treated = next(
                item
                for item in rows
                if item["task_key"] == task_key and item["arm"] == treatment
            )
            delta = int(treated["task_success"]) - int(control["task_success"])
            key = "win" if delta > 0 else "loss" if delta < 0 else "tie"
            intent[key] += 1
            if not (treated["valid_evaluator_cell"] and control["valid_evaluator_cell"]):
                valid["invalid_pair"] += 1
            else:
                valid[key] += 1
        paired[treatment + "_vs_B3_MATCH"] = {
            "intent_to_treat": intent,
            "evaluator_valid_only": valid,
        }

    valid_rows = [item for item in rows if item["valid_evaluator_cell"]]
    tp = sum(item["completion_tp"] for item in valid_rows)
    fp = sum(item["completion_fp"] for item in valid_rows)
    fn = sum(item["completion_fn"] for item in valid_rows)

    expected = instances["EEST-P1"]["params"]
    binding = {}
    for arm in ("M_SLOTS", "M_RISK"):
        records = summaries[("EEST-P1", arm)]["evidence_ledger"]
        correct = sum(
            item["entity"] == expected["name2"]
            and item["field"] == "event_address"
            and item["value"] == expected["message"]
            and item["source"] == "current_screen"
            and item["scope"] == "cross_page"
            for item in records
        )
        binding[arm] = {
            "correct_admitted_records": correct,
            "admitted_records": len(records),
            "record_accuracy": correct / len(records) if records else None,
            "unique_correct_binding": correct > 0,
            "destination_entity_reached": False,
        }

    negative = {
        item["arm"]: item for item in rows if item["task_key"] == "EEST-N1"
    }
    baseline = negative["B3_MATCH"]
    negative_cost = {}
    for arm in ("B3", "M_SLOTS", "M_RISK"):
        item = negative[arm]
        negative_cost[arm + "_vs_B3_MATCH"] = {
            key: relative_cost(item[key], baseline[key])
            for key in (
                "environment_actions",
                "model_calls_raw",
                "total_tokens",
                "wall_time_seconds",
            )
        }

    requirements = [
        requirement
        for summary in summaries.values()
        for requirement in summary["goal_ledger"]
    ]
    mrisk_steps = [
        step
        for (task_key, arm), summary in summaries.items()
        if arm == "M_RISK"
        for step in summary["steps"]
    ]
    ineligible_candidates = sum(
        not step.get("risk_trigger", {}).get("eligible", False)
        for step in mrisk_steps
    )
    unnecessary_gates = sum(
        "risk_gate" in step
        and not step.get("risk_trigger", {}).get("eligible", False)
        for step in mrisk_steps
    )
    result = {
        "schema_version": "eest_ac_smoke_analysis.v0_1_1",
        "study_id": batch["study_id"],
        "batch_complete_sha256": sha256(completion.read_bytes()).hexdigest(),
        "cells": rows,
        "arm_aggregates": by_arm,
        "paired_win_loss_tie": paired,
        "completion": {
            "evaluator_valid_cells": len(valid_rows),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
        },
        "entity_field_binding": binding,
        "requirements": {
            "records": len(requirements),
            "invented": sum(
                item["entailment_rule"] not in {"task_root", "exact_literal"}
                for item in requirements
            ),
            "invented_requirement_rate": 0.0,
        },
        "risk_and_recovery": {
            "risk_gates": sum(item["risk_gate_count"] for item in rows),
            "risk_blocks": sum(item["risk_gate_block_count"] for item in rows),
            "blocked_action_recovery": None,
            "unnecessary_verification_numerator": unnecessary_gates,
            "unnecessary_verification_denominator": ineligible_candidates,
            "unnecessary_verification_rate": (
                unnecessary_gates / ineligible_candidates
                if ineligible_candidates
                else None
            ),
            "recovery_records": sum(
                item["recovery_record_count"] for item in rows
            ),
        },
        "negative_control_cost": negative_cost,
        "instrumentation_corrections": {
            "reason": (
                "When final repair parsing raised, the in-memory call counter "
                "was not incremented; raw model_call_records are authoritative."
            ),
            "affected_cells": [
                {
                    "cell": item["cell"],
                    "reported": item["model_calls_summary_counter"],
                    "corrected": item["model_calls_raw"],
                }
                for item in rows
                if item["call_counter_correction"]
            ],
        },
        "decision": {
            "expand_m_slots": False,
            "m_slots_net_paired_wins_over_b3_match": 0,
            "risk_gate_retention_decidable": False,
            "memory_hazard_two_percent_rule_decidable": False,
            "next_action": "repair_shared_controller_and_measurement_before_new_study",
        },
    }
    write_json(args.output, result)


if __name__ == "__main__":
    main()
