#!/usr/bin/env python3
"""Build the frozen manifest for the visible-source-object extractor diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
MARKOR_DOCUMENT_ACTIVITY = "net.gsantner.markor/net.gsantner.markor.activity.DocumentActivity"

TASK_RULES = {
    "ExpenseAddMultipleFromMarkor": {
        "identifier_key": "name",
        "rule": "Return an expense name only when the same visible record explicitly says Reimbursable.",
    },
    "RecipeAddMultipleRecipesFromMarkor": {
        "identifier_key": "title",
        "rule": "Return every recipe title visibly present; there is no additional filter.",
    },
    "RecipeAddMultipleRecipesFromMarkor2": {
        "identifier_key": "title",
        "rule": "Return a recipe title only when the same visible record has the preparation time required by the task.",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_events(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def relative(path: Path) -> str:
    return path.resolve().relative_to(REPOSITORY_ROOT.resolve()).as_posix()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    source_path = args.input.resolve()
    source = json.loads(source_path.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    episodes: list[dict[str, Any]] = []

    for episode in source["episodes"]:
        task = episode["task_name"]
        if task not in TASK_RULES:
            continue
        config = TASK_RULES[task]
        source_summary = Path(episode["source_summary"])
        episode_dir = source_summary.parent / "episodes" / episode["episode_id"]
        events_path = episode_dir / "events.jsonl"
        events = load_events(events_path)
        start = next(event for event in events if event.get("event") == "episode_start")
        expected = [
            str(item[config["identifier_key"]])
            for item in start["task_params"]["row_objects"]
        ]

        seen: set[str] = set()
        episode_records: list[dict[str, Any]] = []
        for event in events:
            if event.get("event") != "step":
                continue
            before = event.get("before") or {}
            foreground = before.get("foreground") or {}
            if foreground.get("activity") != MARKOR_DOCUMENT_ACTIVITY:
                continue
            screenshot_hash = before.get("screenshot_sha256")
            if not screenshot_hash or screenshot_hash in seen:
                continue
            seen.add(screenshot_hash)
            screenshot_path = episode_dir / before["screenshot"]
            if sha256(screenshot_path) != screenshot_hash:
                raise RuntimeError(f"screenshot drift: {screenshot_path}")
            record = {
                "record_id": f"{episode['episode_id']}::step_{int(event['step']):03d}",
                "episode_id": episode["episode_id"],
                "task_name": task,
                "seed": episode["seed"],
                "step": int(event["step"]),
                "task_goal": start["task_goal_before_initialization"],
                "extraction_rule": config["rule"],
                "screenshot_path": relative(screenshot_path),
                "screenshot_sha256": screenshot_hash,
                "expected_identifiers_hidden_for_scoring_only": expected,
                "events_path": relative(events_path),
                "events_sha256": sha256(events_path),
            }
            episode_records.append(record)
            records.append(record)
        if episode_records:
            episodes.append(
                {
                    "episode_id": episode["episode_id"],
                    "task_name": task,
                    "seed": episode["seed"],
                    "expected_identifiers_hidden_for_scoring_only": expected,
                    "record_ids": [record["record_id"] for record in episode_records],
                }
            )

    expected_count = sum(len(episode["expected_identifiers_hidden_for_scoring_only"]) for episode in episodes)
    if (len(episodes), len(records), expected_count) != (8, 13, 21):
        raise RuntimeError(
            "frozen cohort drift: expected 8 episodes, 13 frames, 21 identifiers; "
            f"got {len(episodes)}, {len(records)}, {expected_count}"
        )
    manifest = {
        "manifest_version": "visible_object_extractor_markor_v1",
        "claim_class": "development_contaminated_offline_diagnostic_not_held_out_efficacy",
        "source_report": relative(source_path),
        "source_report_sha256": sha256(source_path),
        "selection": {
            "task_classes": sorted(TASK_RULES),
            "activity": MARKOR_DOCUMENT_ACTIVITY,
            "frame_rule": "all unique before screenshots observed in Markor DocumentActivity",
            "ground_truth_visibility": "hidden scoring only; never included in prompts",
        },
        "episode_count": len(episodes),
        "record_count": len(records),
        "expected_identifier_count": expected_count,
        "episodes": episodes,
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
