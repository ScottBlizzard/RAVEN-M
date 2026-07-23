"""Render deterministic evidence timelines for preselected paired cases."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_MEMORY_EFFECTS = {"helpful", "harmful", "neutral", "unclear"}


def case_key(case: dict[str, Any]) -> tuple[int, str, str, int]:
    return (
        int(case["selection_index"]),
        str(case["cell"]),
        str(case["task_id"]),
        int(case["instance_seed"]),
    )


def annotation_template(selection: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "case_annotations.v1",
        "review_status": "pending_single_reviewer",
        "reviewer_count": 1,
        "reviewer_scope": (
            "Primary project review of frozen screenshots, decisions, routed "
            "memory, actions, and evaluator outcome; no claim of independent "
            "inter-annotator agreement."
        ),
        "cases": [
            {
                "selection_index": case["selection_index"],
                "cell": case["cell"],
                "task_id": case["task_id"],
                "instance_seed": case["instance_seed"],
                "memory_effect": "",
                "m0_evidence_steps": [],
                "b3_evidence_steps": [],
                "annotation": "",
            }
            for case in selection["cases"]
        ],
    }


def load_annotations(
    *,
    selection: dict[str, Any],
    annotation_path: Path,
) -> dict[tuple[int, str, str, int], dict[str, Any]]:
    if not annotation_path.is_file():
        template = annotation_template(selection)
        annotation_path.parent.mkdir(parents=True, exist_ok=True)
        annotation_path.write_text(
            json.dumps(template, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        raise SystemExit(
            "Case annotations are required before final report assembly. "
            f"Review and complete {annotation_path}."
        )
    payload = json.loads(annotation_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "case_annotations.v1":
        raise ValueError("Unexpected case-annotation schema.")
    if payload.get("review_status") != "completed_single_reviewer":
        raise ValueError("Case review_status is not completed_single_reviewer.")
    observed = {
        case_key(item): item for item in payload.get("cases", [])
    }
    expected = {case_key(item) for item in selection["cases"]}
    if set(observed) != expected:
        raise ValueError("Case annotations do not match frozen selection.")
    for key, item in observed.items():
        if item.get("memory_effect") not in ALLOWED_MEMORY_EFFECTS:
            raise ValueError(f"Invalid memory_effect for {key}.")
        if not str(item.get("annotation", "")).strip():
            raise ValueError(f"Missing mechanism annotation for {key}.")
        for field in ("m0_evidence_steps", "b3_evidence_steps"):
            if not isinstance(item.get(field), list) or not all(
                isinstance(value, int) and value >= 0
                for value in item[field]
            ):
                raise ValueError(f"Invalid {field} for {key}.")
    return observed


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
    parser.add_argument(
        "--annotations",
        type=Path,
        default=REPOSITORY_ROOT
        / "reports/generated/case_annotations.json",
    )
    args = parser.parse_args()
    selection = json.loads(
        args.case_selection.read_text(encoding="utf-8")
    )
    annotations = load_annotations(
        selection=selection,
        annotation_path=args.annotations,
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
        annotation = annotations[case_key(case)]
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
                "### Single-reviewer mechanism annotation",
                "",
                f"- Memory effect: `{annotation['memory_effect']}`",
                "- M0 evidence steps: "
                + (
                    ", ".join(
                        str(value)
                        for value in annotation["m0_evidence_steps"]
                    )
                    or "none"
                ),
                "- B3 evidence steps: "
                + (
                    ", ".join(
                        str(value)
                        for value in annotation["b3_evidence_steps"]
                    )
                    or "none"
                ),
                f"- Interpretation: {annotation['annotation']}",
            ]
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(sections) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
