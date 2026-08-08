"""Incrementally summarize completed episodes in an official-Qwen suite."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from analyze_official_qwen_episode import summarize


def _completed(summary: dict[str, Any]) -> bool:
    return summary.get("terminal") is not None


def _elapsed_seconds(start: dict[str, Any], terminal: dict[str, Any]) -> float | None:
    try:
        return (
            datetime.fromisoformat(str(terminal["time"]))
            - datetime.fromisoformat(str(start["time"]))
        ).total_seconds()
    except (KeyError, TypeError, ValueError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("suite_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    episode_root = args.suite_dir / "episodes"
    records: list[dict[str, Any]] = []
    in_progress: list[str] = []
    for episode_dir in sorted(episode_root.iterdir() if episode_root.exists() else []):
        if not episode_dir.is_dir() or not (episode_dir / "events.jsonl").exists():
            continue
        item = summarize(episode_dir)
        if not _completed(item):
            in_progress.append(episode_dir.name)
            continue
        terminal = item["terminal"]
        evaluator = item.get("evaluator") or {}
        episode_start = item.get("episode_start") or {}
        scientifically_eligible = (
            terminal.get("termination_reason")
            != "infrastructure_or_controller_error"
            and evaluator.get("reward") is not None
        )
        records.append(
            {
                "episode_id": episode_dir.name,
                "task_name": episode_start.get("task_name"),
                "seed": episode_start.get("seed"),
                "elapsed_seconds": _elapsed_seconds(episode_start, terminal),
                "success": bool(terminal.get("success")),
                "scientifically_eligible": scientifically_eligible,
                "termination_reason": terminal.get("termination_reason"),
                "evaluator_reward": evaluator.get("reward"),
                "model_claimed_status": evaluator.get("model_claimed_status"),
                "step_count": item["step_count"],
                "protocol_error_count": item["protocol_error_count"],
                "protocol_error_steps": item["protocol_error_steps"],
                "execution_failure_count": len(item["execution_failure_steps"]),
                "execution_failure_steps": item["execution_failure_steps"],
                "single_tool_multi_action_claim_steps": item[
                    "single_tool_multi_action_claim_steps"
                ],
                "mean_model_latency_seconds": item["mean_model_latency_seconds"],
                "max_before_ui_state_repetitions": item[
                    "max_before_ui_state_repetitions"
                ],
                "max_consecutive_stagnant_steps": item[
                    "max_consecutive_stagnant_steps"
                ],
                "stagnant_step_count": item["stagnant_step_count"],
                "nearly_unchanged_ranges": item["nearly_unchanged_ranges"],
                "repeated_state_flag": (
                    item["max_before_ui_state_repetitions"] >= 3
                ),
                "false_success_claim_flag": (
                    evaluator.get("model_claimed_status") == "success"
                    and not bool(terminal.get("success"))
                ),
            }
        )
    terminations = Counter(str(item["termination_reason"]) for item in records)
    eligible_records = [item for item in records if item["scientifically_eligible"]]
    task_groups: dict[str, list[dict[str, Any]]] = {}
    for item in eligible_records:
        task_groups.setdefault(str(item.get("task_name")), []).append(item)
    per_task = {
        task_name: {
            "completed_count": len(items),
            "success_count": sum(int(item["success"]) for item in items),
            "mean_reward": (
                sum(float(item["evaluator_reward"] or 0.0) for item in items)
                / len(items)
            ),
            "seeds": [item.get("seed") for item in items],
            "rewards": [item.get("evaluator_reward") for item in items],
        }
        for task_name, items in sorted(task_groups.items())
    }
    total_reward = sum(
        float(item["evaluator_reward"] or 0.0) for item in eligible_records
    )
    payload = {
        "suite_dir": str(args.suite_dir.resolve()),
        "completed_episode_count": len(records),
        "scientifically_eligible_episode_count": len(eligible_records),
        "infrastructure_invalid_episode_count": len(records) - len(eligible_records),
        "in_progress_episode_ids": in_progress,
        "success_count": sum(int(item["success"]) for item in eligible_records),
        "positive_reward_count": sum(
            int(float(item["evaluator_reward"] or 0.0) > 0.0)
            for item in eligible_records
        ),
        "partial_reward_count": sum(
            int(
                float(item["evaluator_reward"] or 0.0) > 0.0
                and not bool(item["success"])
            )
            for item in eligible_records
        ),
        "total_reward": total_reward,
        "mean_reward": (
            total_reward / len(eligible_records) if eligible_records else None
        ),
        "false_success_claim_count": sum(
            int(item["false_success_claim_flag"]) for item in eligible_records
        ),
        "repeated_state_episode_count": sum(
            int(item["repeated_state_flag"]) for item in eligible_records
        ),
        "stagnation_episode_count": sum(
            int(item["max_consecutive_stagnant_steps"] >= 2)
            for item in eligible_records
        ),
        "total_stagnant_steps": sum(
            int(item["stagnant_step_count"]) for item in eligible_records
        ),
        "success_rate_completed": (
            sum(int(item["success"]) for item in eligible_records)
            / len(eligible_records)
            if eligible_records
            else None
        ),
        "total_model_calls": sum(int(item["step_count"]) for item in records),
        "scientifically_eligible_model_calls": sum(
            int(item["step_count"]) for item in eligible_records
        ),
        "total_episode_elapsed_seconds": sum(
            float(item["elapsed_seconds"] or 0.0) for item in eligible_records
        ),
        "protocol_error_count": sum(
            int(item["protocol_error_count"]) for item in eligible_records
        ),
        "execution_failure_count": sum(
            int(item["execution_failure_count"]) for item in eligible_records
        ),
        "single_tool_multi_action_claim_episode_count": sum(
            int(bool(item["single_tool_multi_action_claim_steps"]))
            for item in eligible_records
        ),
        "termination_reasons": dict(sorted(terminations.items())),
        "per_task": per_task,
        "episodes": records,
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
