"""Produce a deterministic L0--L5 summary for an official-Qwen episode."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from typing import Any


def _events(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _max_consecutive_stagnant_steps(
    steps: list[dict[str, Any]], threshold: float = 0.001
) -> int:
    longest = 0
    current = 0
    for step in steps:
        changed = step.get("transition", {}).get("changed_pixel_fraction_gt_5")
        if changed is not None and float(changed) < threshold:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _consecutive_ranges(values: list[int]) -> list[dict[str, int]]:
    """Render sorted integer positions as inclusive contiguous ranges."""
    if not values:
        return []
    ordered = sorted(set(values))
    ranges: list[dict[str, int]] = []
    start = previous = ordered[0]
    for value in ordered[1:]:
        if value == previous + 1:
            previous = value
            continue
        ranges.append({"start": start, "end": previous, "length": previous - start + 1})
        start = previous = value
    ranges.append({"start": start, "end": previous, "length": previous - start + 1})
    return ranges


def summarize(episode_dir: Path) -> dict[str, Any]:
    events = _events(episode_dir / "events.jsonl")
    episode_start = next(
        (event for event in events if event.get("event") == "episode_start"),
        None,
    )
    steps = [event for event in events if event.get("event") == "step"]
    terminal = next(
        (
            event
            for event in reversed(events)
            if event.get("event") in {"episode_complete", "episode_end"}
        ),
        None,
    )
    evaluator = next(
        (
            event
            for event in reversed(events)
            if event.get("event") == "evaluator_result"
        ),
        None,
    )
    tool_counts = Counter(
        str(step.get("decision", {}).get("tool", {}).get("arguments", {}).get("action"))
        for step in steps
    )
    ui_state_counts = Counter(
        str(step.get("before", {}).get("ui_sha256"))
        for step in steps
        if step.get("before", {}).get("ui_sha256")
    )
    repeated_ui_states = {
        digest: count
        for digest, count in sorted(ui_state_counts.items())
        if count > 1
    }
    no_visible_change = [
        int(step["step"])
        for step in steps
        if step.get("transition", {}).get("exactly_unchanged") is True
    ]
    nearly_no_change = [
        int(step["step"])
        for step in steps
        if (
            step.get("transition", {}).get("changed_pixel_fraction_gt_5")
            is not None
            and float(
                step["transition"]["changed_pixel_fraction_gt_5"]
            ) < 0.001
        )
    ]
    parse_failures = [
        step
        for step in steps
        if (
            step.get("parse_error")
            or step.get("layers", {})
            .get("L2_protocol_coordinate", {})
            .get("parse_valid")
            is False
        )
    ]
    parse_failure_steps = [int(step["step"]) for step in parse_failures]
    execution_failures = [
        int(step["step"])
        for step in steps
        if (
            step.get("layers", {}).get("L3_execution", {}).get("attempted")
            is True
            and step.get("layers", {}).get("L3_execution", {}).get("completed")
            is False
        )
    ]
    multi_action_claim_steps = [
        int(step["step"])
        for step in steps
        if re.search(
            r"\b(?:clicked|tapped|pressed|swiped|typed)\b.{0,100}"
            r"\b(?:two|three|four|five|six|seven|eight|nine|ten|\d+)\s+times\b",
            str(step.get("decision", {}).get("action_summary", "")),
            flags=re.IGNORECASE,
        )
        and step.get("decision", {})
        .get("tool", {})
        .get("arguments", {})
        .get("action")
        in {"click", "long_press", "swipe", "type", "system_button"}
    ]
    latencies = [
        float(step["layers"]["L0_runtime"]["latency_seconds"])
        for step in steps
        if step.get("layers", {}).get("L0_runtime", {}).get("latency_seconds")
        is not None
    ]
    action_trace = [
        {
            "step": int(step["step"]),
            "summary": step.get("decision", {}).get("action_summary"),
            "tool": step.get("decision", {})
            .get("tool", {})
            .get("arguments", {})
            .get("action"),
            "activity_before": step.get("before", {})
            .get("foreground", {})
            .get("activity"),
            "activity_after": step.get("after", {})
            .get("foreground", {})
            .get("activity"),
            "changed_pixel_fraction_gt_5": step.get("transition", {}).get(
                "changed_pixel_fraction_gt_5"
            ),
        }
        for step in steps
    ]
    return {
        "episode_dir": str(episode_dir.resolve()),
        "episode_start": episode_start,
        "step_count": len(steps),
        "model_call_count": len(steps),
        "tool_counts": dict(sorted(tool_counts.items())),
        "repeated_before_ui_states": repeated_ui_states,
        "max_before_ui_state_repetitions": max(ui_state_counts.values(), default=0),
        "max_consecutive_stagnant_steps": _max_consecutive_stagnant_steps(steps),
        "protocol_error_count": len(parse_failures),
        "protocol_error_steps": parse_failure_steps,
        "execution_failure_steps": execution_failures,
        "single_tool_multi_action_claim_steps": multi_action_claim_steps,
        "exactly_unchanged_steps": no_visible_change,
        "nearly_unchanged_steps": nearly_no_change,
        "nearly_unchanged_ranges": _consecutive_ranges(nearly_no_change),
        "stagnant_step_count": len(nearly_no_change),
        "mean_model_latency_seconds": (
            sum(latencies) / len(latencies) if latencies else None
        ),
        "terminal": terminal,
        "evaluator": evaluator,
        "action_trace": action_trace,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("episode_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = summarize(args.episode_dir)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
