#!/usr/bin/env python3
"""Zero-generation replay for the numeric-answer consistency guard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "implementation/src")]

from raven_m.official_qwen_mobile import sys_nag_contract as contract  # noqa: E402
from raven_m.official_qwen_mobile.numeric_answer_guard import (  # noqa: E402
    NumericAnswerConsistencyGuard,
)

DEFAULT_SUITE = ROOT / "runs/a1r2_cvp/official_qwen_20260814T145307_50081981"
V2_FAILURE_EPISODE = (
    ROOT / "runs/sys_trrc_v2_full/official_qwen_20260816T005559_70b00ecd/episodes/"
    "SportsTrackerTotalDurationForCategoryThisWeek_20260806_aa0c6805/episode.json"
)


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def replay(suite_dir: Path = DEFAULT_SUITE) -> dict:
    errors: list[str] = []
    episode_rows: list[dict] = []
    total_reviews = total_eligible = total_overrides = 0
    projected_rendered_chars = 0
    checkpoint = json.loads((suite_dir / "checkpoint.json").read_text(encoding="utf-8"))
    valid_ids = {
        str(item.get("episode_id")) for item in checkpoint.get("valid_summaries") or []
    }
    episode_files = sorted(
        path
        for path in (suite_dir / "episodes").glob("*/episode.json")
        if path.parent.name in valid_ids
    )
    for path in episode_files:
        episode = json.loads(path.read_text(encoding="utf-8"))
        guard = NumericAnswerConsistencyGuard()
        events: list[dict] = []
        for step in episode.get("steps") or []:
            projected_rendered_chars += int(
                ((step.get("memory_read") or {}).get("rendered_chars") or 0)
            )
            decision = step.get("decision") or {}
            proposed = decision.get("canonical_action")
            _, event = guard.review(
                proposed_action=proposed,
                action_summary=str(decision.get("action_summary") or ""),
            )
            if event.get("eligible"):
                events.append({"step": step.get("step"), **event})
        audit = guard.audit_record()
        counters = audit["counters"]
        total_reviews += counters["review_count"]
        total_eligible += counters["eligible_count"]
        total_overrides += counters["action_override_count"]
        episode_rows.append(
            {
                "task_name": episode.get("task_name"),
                "episode_id": episode.get("episode_id"),
                "success": episode.get("success"),
                "review_count": counters["review_count"],
                "eligible_count": counters["eligible_count"],
                "override_count": counters["action_override_count"],
                "events": events,
            }
        )
    if len(episode_rows) != 19 or len({row["task_name"] for row in episode_rows}) != 19:
        errors.append("a1r2_suite_not_exact_19")

    observed = json.loads(V2_FAILURE_EPISODE.read_text(encoding="utf-8"))
    final_decision = (observed.get("steps") or [])[-1]["decision"]
    guard = NumericAnswerConsistencyGuard()
    corrected, event = guard.review(
        proposed_action=final_decision["canonical_action"],
        action_summary=final_decision["action_summary"],
    )
    regression = {
        "task_name": observed.get("task_name"),
        "episode_id": observed.get("episode_id"),
        "proposed_action": final_decision["canonical_action"],
        "corrected_action": corrected,
        "event": event,
    }
    if corrected != {"type": "answer", "text": "180"}:
        errors.append("v2_failure_not_corrected_to_180")
    if event.get("duration_minutes") != [105, 75] or not event.get("overridden"):
        errors.append("v2_failure_evidence_mismatch")

    payload = {
        "schema": contract.OFFLINE_REPLAY_SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "generation_calls": 0,
        "mechanism_id": contract.MECHANISM_ID,
        "system_id": contract.SYSTEM_ID,
        "source": {
            "a1r2_suite_dir": str(suite_dir.resolve()),
            "v2_failure_episode": str(V2_FAILURE_EPISODE.resolve()),
        },
        "totals": {
            "valid_episode_count": len(episode_rows),
            "review_count": total_reviews,
            "eligible_count": total_eligible,
            "override_count": total_overrides,
            "projected_rendered_chars": projected_rendered_chars,
        },
        "sentinel_tasks": [
            "ExpenseDeleteMultiple2",
            "SportsTrackerTotalDurationForCategoryThisWeek",
            "RecipeDeleteMultipleRecipesWithConstraint",
        ],
        "v2_failure_regression": regression,
        "episodes": episode_rows,
    }
    return {**payload, "content_sha256": contract.content_sha256(payload)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-dir", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--output", type=Path, default=contract.OFFLINE_REPLAY_PATH)
    args = parser.parse_args()
    result = replay(args.suite_dir.resolve())
    _write(args.output, result)
    print(json.dumps({"status": result["status"], "errors": result["errors"], "totals": result["totals"]}, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
