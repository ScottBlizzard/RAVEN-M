"""Render a deterministic Markdown snapshot from a suite summary JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render(payload: dict[str, Any]) -> str:
    logged = int(payload.get("completed_episode_count", 0))
    completed = int(payload.get("scientifically_eligible_episode_count", logged))
    expected = int(payload.get("expected_scientifically_eligible_episode_count", 57))
    success = int(payload.get("success_count", 0))
    elapsed = float(payload.get("total_episode_elapsed_seconds", 0.0))
    lines = [
        "# Official Qwen3-VL-32B Full Hard: deterministic snapshot",
        "",
        f"- Scientifically eligible: {completed}/{expected}",
        f"- Complete: {bool(payload.get('complete', completed == expected and not payload.get('in_progress_episode_ids')))}",
        f"- Logged terminal records: {logged}",
        f"- Excluded audit records: {payload.get('excluded_episode_count', payload.get('infrastructure_invalid_episode_count', 0))}",
        f"- Infrastructure-invalid records: {payload.get('infrastructure_invalid_episode_count', 0)}",
        f"- Implementation-invalid records: {payload.get('implementation_invalid_episode_count', 0)}",
        f"- Success: {success}/{completed}" if completed else "- Success: 0/0",
        f"- Success rate over completed episodes: {_fmt(payload.get('success_rate_completed'))}",
        f"- Positive reward episodes: {payload.get('positive_reward_count', success)}",
        f"- Partial reward episodes: {payload.get('partial_reward_count', 0)}",
        f"- Total / mean reward: {_fmt(payload.get('total_reward'))} / {_fmt(payload.get('mean_reward'))}",
        f"- Eligible model calls: {payload.get('scientifically_eligible_model_calls', payload.get('total_model_calls', 0))}",
        f"- All logged model calls: {payload.get('total_model_calls', 0)}",
        f"- Episode wall time: {_fmt(elapsed / 60.0, 1)} min",
        f"- False success claims: {payload.get('false_success_claim_count', 0)}",
        f"- Repeated-state episodes: {payload.get('repeated_state_episode_count', 0)}",
        f"- Stagnation episodes: {payload.get('stagnation_episode_count', 0)}",
        f"- Nearly unchanged actions: {payload.get('total_stagnant_steps', 0)}",
        f"- Protocol errors: {payload.get('protocol_error_count', 0)}",
        f"- Execution failures: {payload.get('execution_failure_count', 0)}",
        "",
        "## Per task class",
        "",
        "| Task | Completed | Success | Mean reward | Seeds | Rewards | Calls | Consistency |",
        "|---|---:|---:|---:|---|---|---|---|",
    ]
    for task, item in sorted((payload.get("per_task") or {}).items()):
        seeds = ", ".join(_fmt(v, 0) for v in item.get("seeds", []))
        rewards = ", ".join(_fmt(v) for v in item.get("rewards", []))
        calls = ", ".join(_fmt(v, 0) for v in item.get("step_counts", []))
        lines.append(
            f"| {task} | {item.get('completed_count', 0)} | "
            f"{item.get('success_count', 0)} | {_fmt(item.get('mean_reward'))} | "
            f"{seeds} | {rewards} | {calls} | {item.get('consistency', 'NA')} |"
        )
    lines.extend(
        [
            "",
            "## Completed episodes",
            "",
            "| Episode | Reward | Calls | Termination | False success | Repeated UI | Stagnant run |",
            "|---|---:|---:|---|---:|---:|---:|",
        ]
    )
    for item in payload.get("episodes", []):
        lines.append(
            f"| {item.get('episode_id')} | {_fmt(item.get('evaluator_reward'))} | "
            f"{item.get('step_count')} | {item.get('termination_reason')} | "
            f"{int(bool(item.get('false_success_claim_flag')))} | "
            f"{item.get('max_before_ui_state_repetitions', 0)} | "
            f"{item.get('max_consecutive_stagnant_steps', 0)} |"
        )
    in_progress = payload.get("in_progress_episode_ids") or []
    lines.extend(["", f"In progress: {', '.join(in_progress) if in_progress else 'none'}", ""])
    invalid = payload.get("infrastructure_invalid_episode_ids") or []
    if invalid:
        lines.extend(
            [
                "## Infrastructure-invalid audit records (excluded from science)",
                "",
                *[f"- {episode_id}" for episode_id in invalid],
                "",
            ]
        )
    implementation_invalid = payload.get("implementation_invalid_episode_ids") or []
    if implementation_invalid:
        lines.extend(
            [
                "## Implementation-invalid audit records (excluded from science)",
                "",
                *[f"- {episode_id}" for episode_id in implementation_invalid],
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("summary_json", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.summary_json.read_text(encoding="utf-8"))
    rendered = render(payload)
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
