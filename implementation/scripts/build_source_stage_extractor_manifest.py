#!/usr/bin/env python3
"""Build an extractor manifest from one bounded Markor source-stage suite."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
DOCUMENT_ACTIVITY = "net.gsantner.markor/net.gsantner.markor.activity.DocumentActivity"
TASK_RULES = {
    "ExpenseAddMultipleFromMarkor": (
        "name",
        "Return an expense name only when the same visible record explicitly says Reimbursable.",
    ),
    "RecipeAddMultipleRecipesFromMarkor": (
        "title",
        "Return every recipe title visibly present; there is no additional filter.",
    ),
    "RecipeAddMultipleRecipesFromMarkor2": (
        "title",
        "Return a recipe title only when the same visible record has the preparation time required by the task.",
    ),
}


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(REPOSITORY_ROOT.resolve()).as_posix()


def events(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-dir", required=True, type=Path)
    parser.add_argument("--condition", required=True, choices=("baseline", "coverage_gate"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    suite_dir = args.suite_dir.resolve()
    suite = json.loads((suite_dir / "aggregate.json").read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    episode_rows: list[dict[str, Any]] = []
    for row in suite["episodes"]:
        task = row["task_name"]
        identifier_key, rule = TASK_RULES[task]
        episode_dir = suite_dir / "episodes" / row["episode_id"]
        events_path = episode_dir / "events.jsonl"
        log = events(events_path)
        start = next(item for item in log if item.get("event") == "episode_start")
        expected = [str(item[identifier_key]) for item in start["task_params"]["row_objects"]]
        seen: set[str] = set()
        ids: list[str] = []
        for item in log:
            if item.get("event") != "step":
                continue
            before = item.get("before") or {}
            if ((before.get("foreground") or {}).get("activity")) != DOCUMENT_ACTIVITY:
                continue
            screenshot_hash = before.get("screenshot_sha256")
            if not screenshot_hash or screenshot_hash in seen:
                continue
            seen.add(screenshot_hash)
            screenshot_path = episode_dir / before["screenshot"]
            if digest(screenshot_path) != screenshot_hash:
                raise RuntimeError(f"screenshot drift: {screenshot_path}")
            record_id = f"{row['episode_id']}::step_{int(item['step']):03d}"
            ids.append(record_id)
            records.append(
                {
                    "record_id": record_id,
                    "episode_id": row["episode_id"],
                    "task_name": task,
                    "seed": start["seed"],
                    "step": int(item["step"]),
                    "task_goal": start["task_goal_before_initialization"],
                    "extraction_rule": rule,
                    "screenshot_path": relative(screenshot_path),
                    "screenshot_sha256": screenshot_hash,
                    "expected_identifiers_hidden_for_scoring_only": expected,
                    "events_path": relative(events_path),
                    "events_sha256": digest(events_path),
                }
            )
        episode_rows.append(
            {
                "episode_id": row["episode_id"],
                "task_name": task,
                "seed": start["seed"],
                "expected_identifiers_hidden_for_scoring_only": expected,
                "record_ids": ids,
            }
        )
    result = {
        "manifest_version": "source_stage_visible_object_extractor_v1",
        "claim_class": "new_instance_development_matched_source_stage_pilot_not_held_out",
        "condition": args.condition,
        "source_suite": relative(suite_dir),
        "source_aggregate_sha256": digest(suite_dir / "aggregate.json"),
        "episode_count": len(episode_rows),
        "record_count": len(records),
        "expected_identifier_count": sum(
            len(row["expected_identifiers_hidden_for_scoring_only"])
            for row in episode_rows
        ),
        "episodes": episode_rows,
        "records": records,
    }
    if result["episode_count"] != 3:
        raise RuntimeError(f"expected 3 source-stage episodes, got {result['episode_count']}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
