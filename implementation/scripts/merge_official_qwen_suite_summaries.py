"""Merge official-Qwen suite summaries without counting infrastructure failures.

The merge key is (task_name, seed).  Exactly one scientifically eligible record
is allowed for a key.  Infrastructure-invalid records are retained for audit,
but they never compete with or alter a valid rerun.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("summary_json", type=Path, nargs="+")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expected-eligible", type=int, default=57)
    args = parser.parse_args()

    payloads = [_read(path) for path in args.summary_json]
    eligible_by_key: dict[tuple[str, int], dict[str, Any]] = {}
    invalid: list[dict[str, Any]] = []
    in_progress: list[str] = []

    for source_path, payload in zip(args.summary_json, payloads):
        source = str(source_path.resolve())
        in_progress.extend(payload.get("in_progress_episode_ids") or [])
        for raw in payload.get("episodes") or []:
            item = dict(raw)
            item["source_summary"] = source
            if not item.get("scientifically_eligible"):
                invalid.append(item)
                continue
            task = item.get("task_name")
            seed = item.get("seed")
            if task is None or seed is None:
                raise SystemExit(f"eligible record lacks task/seed: {item.get('episode_id')}")
            key = (str(task), int(seed))
            if key in eligible_by_key:
                prior = eligible_by_key[key]
                raise SystemExit(
                    "duplicate scientifically eligible key "
                    f"{key}: {prior.get('episode_id')} and {item.get('episode_id')}"
                )
            eligible_by_key[key] = item

    eligible = [eligible_by_key[key] for key in sorted(eligible_by_key)]
    task_groups: dict[str, list[dict[str, Any]]] = {}
    for item in eligible:
        task_groups.setdefault(str(item["task_name"]), []).append(item)
    per_task = {}
    for task, items in sorted(task_groups.items()):
        items = sorted(items, key=lambda item: int(item["seed"]))
        successes = [bool(item["success"]) for item in items]
        if len(items) < 3:
            consistency = "incomplete"
        elif all(successes):
            consistency = "all_success"
        elif not any(successes):
            consistency = "all_failure"
        else:
            consistency = "mixed"
        per_task[task] = {
            "completed_count": len(items),
            "success_count": sum(int(item["success"]) for item in items),
            "mean_reward": sum(float(item.get("evaluator_reward") or 0.0) for item in items)
            / len(items),
            "seeds": [item["seed"] for item in items],
            "rewards": [item.get("evaluator_reward") for item in items],
            "step_counts": [item.get("step_count") for item in items],
            "consistency": consistency,
        }

    termination_reasons = Counter(str(item.get("termination_reason")) for item in eligible)
    total_reward = sum(float(item.get("evaluator_reward") or 0.0) for item in eligible)
    complete = len(eligible) == args.expected_eligible and not in_progress
    infrastructure_invalid = [
        item
        for item in invalid
        if item.get("termination_reason") == "infrastructure_or_controller_error"
    ]
    implementation_invalid = [
        item
        for item in invalid
        if item.get("eligibility_reason") == "local_over_strict_parser"
    ]
    result = {
        "suite_dir": "MERGED:" + ";".join(str(path.resolve()) for path in args.summary_json),
        "source_summaries": [str(path.resolve()) for path in args.summary_json],
        "expected_scientifically_eligible_episode_count": args.expected_eligible,
        "complete": complete,
        "completed_episode_count": len(eligible) + len(invalid),
        "scientifically_eligible_episode_count": len(eligible),
        "excluded_episode_count": len(invalid),
        "excluded_episode_ids": [item.get("episode_id") for item in invalid],
        "infrastructure_invalid_episode_count": len(infrastructure_invalid),
        "infrastructure_invalid_episode_ids": [
            item.get("episode_id") for item in infrastructure_invalid
        ],
        "implementation_invalid_episode_count": len(implementation_invalid),
        "implementation_invalid_episode_ids": [
            item.get("episode_id") for item in implementation_invalid
        ],
        "in_progress_episode_ids": sorted(set(in_progress)),
        "success_count": sum(int(item["success"]) for item in eligible),
        "positive_reward_count": sum(
            int(float(item.get("evaluator_reward") or 0.0) > 0.0)
            for item in eligible
        ),
        "partial_reward_count": sum(
            int(
                float(item.get("evaluator_reward") or 0.0) > 0.0
                and not bool(item["success"])
            )
            for item in eligible
        ),
        "total_reward": total_reward,
        "mean_reward": total_reward / len(eligible) if eligible else None,
        "false_success_claim_count": sum(
            int(item.get("false_success_claim_flag", False)) for item in eligible
        ),
        "repeated_state_episode_count": sum(
            int(item.get("repeated_state_flag", False)) for item in eligible
        ),
        "stagnation_episode_count": sum(
            int(int(item.get("max_consecutive_stagnant_steps", 0)) >= 2)
            for item in eligible
        ),
        "total_stagnant_steps": sum(int(item.get("stagnant_step_count", 0)) for item in eligible),
        "success_rate_completed": (
            sum(int(item["success"]) for item in eligible) / len(eligible)
            if eligible
            else None
        ),
        "total_model_calls": sum(int(item.get("step_count", 0)) for item in eligible + invalid),
        "scientifically_eligible_model_calls": sum(
            int(item.get("step_count", 0)) for item in eligible
        ),
        "total_episode_elapsed_seconds": sum(
            float(item.get("elapsed_seconds") or 0.0) for item in eligible
        ),
        "protocol_error_count": sum(int(item.get("protocol_error_count", 0)) for item in eligible),
        "execution_failure_count": sum(
            int(item.get("execution_failure_count", 0)) for item in eligible
        ),
        "single_tool_multi_action_claim_episode_count": sum(
            int(bool(item.get("single_tool_multi_action_claim_steps"))) for item in eligible
        ),
        "termination_reasons": dict(sorted(termination_reasons.items())),
        "per_task": per_task,
        "episodes": eligible,
    }

    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
