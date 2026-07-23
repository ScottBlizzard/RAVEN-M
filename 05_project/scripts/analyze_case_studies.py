"""Render deterministic evidence timelines for preselected paired cases."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def selected_steps(episode: dict[str, Any]) -> list[dict[str, Any]]:
    steps = episode["steps"]
    selected = []
    for index, step in enumerate(steps):
        decision = step.get("decision") or {}
        details = step.get("history_update", {}).get("details", {}) or {}
        notable = (
            index < 2
            or index >= len(steps) - 2
            or index % 5 == 0
            or bool(decision.get("memory_citations"))
            or bool(details.get("loop_detected"))
            or bool(details.get("contradiction_detected"))
            or bool(details.get("role_events"))
            or decision.get("status") in {"done", "fail"}
        )
        if notable:
            selected.append(step)
    return selected


def memory_summary(step: dict[str, Any]) -> str:
    rendered = step.get("history_context", {}).get("rendered", "")
    try:
        payload = json.loads(rendered)
    except (json.JSONDecodeError, TypeError):
        return "—"
    if not isinstance(payload, dict):
        return "—"
    items = payload.get("items", [])
    if not items:
        return "—"
    return "; ".join(
        f"{item['memory_id']}/{item['route']}/{item['status']}"
        for item in items
    )


def timeline(
    *,
    label: str,
    episode_path: Path,
    report_dir: Path,
) -> str:
    episode = json.loads(
        (episode_path / "episode.json").read_text(encoding="utf-8")
    )
    lines = [
        f"### {label}",
        "",
        f"- Success: `{episode['success']}`",
        f"- Failure code: `{episode['failure_code']}`",
        f"- Decisions/actions/calls: {episode['decision_attempt_count']} / "
        f"{episode['executed_action_count']} / {episode['model_call_count']}",
        "",
        "| Step | Screenshot | Routed memory | Decision | Action | Outcome |",
        "|---:|---|---|---|---|---|",
    ]
    for step in selected_steps(episode):
        screenshot = episode_path / step["before_screenshot"]
        relative = Path(
            Path(screenshot).relative_to(REPOSITORY_ROOT)
        ).as_posix()
        link = Path(
            os.path.relpath(REPOSITORY_ROOT / relative, report_dir)
        ).as_posix()
        decision = step.get("decision") or {}
        action = json.dumps(
            decision.get("action"),
            ensure_ascii=False,
            sort_keys=True,
        )
        outcome = (
            step.get("history_update", {})
            .get("details", {})
            .get("page_signature", "")
        )
        lines.append(
            f"| {step['step']} | [{step['before_screenshot']}]({link}) | "
            f"{memory_summary(step)} | "
            f"{str(decision.get('decision_summary', '—')).replace('|', '/')} "
            f"| `{action}` | {outcome or '—'} |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-selection", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "reports/generated/case_studies.md",
    )
    args = parser.parse_args()
    selection = json.loads(
        args.case_selection.read_text(encoding="utf-8")
    )
    sections = [
        "# Predeclared paired case timelines",
        "",
        "Cases are selected by the frozen outcome-cell rule in "
        "`case_selection.json`. The step subset is deterministic and includes "
        "the first/last steps, every fifth step, citations, role triggers, "
        "loops, contradictions, and terminal proposals.",
    ]
    for case in selection["cases"]:
        sections.extend(
            [
                "",
                f"## Case {case['selection_index']}: {case['cell']} — "
                f"{case['task_id']} seed {case['instance_seed']}",
                "",
                f"Task: {case['task_goal']}",
                "",
                timeline(
                    label="M0",
                    episode_path=REPOSITORY_ROOT
                    / case["m0"]["episode_path"],
                    report_dir=args.output.parent,
                ),
                "",
                timeline(
                    label="B3",
                    episode_path=REPOSITORY_ROOT
                    / case["b3"]["episode_path"],
                    report_dir=args.output.parent,
                ),
                "",
                "Manual mechanism annotation: **pending blinded review**.",
            ]
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(sections) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
