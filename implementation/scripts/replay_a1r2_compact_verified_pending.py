#!/usr/bin/env python3
"""Zero-generation replay of A1 traces through A1-R2 storage/rendering."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))

from raven_m.official_qwen_mobile.a1r2_compact_verified_pending import (  # noqa: E402
    MECHANISM_ID,
    CompactVerifiedPendingMemory,
    parse_memory_prefix,
)

A1_SUITE_ID = "official_qwen_20260810T122419_26573d7c"
A0_FOUR = {
    "ExpenseDeleteMultiple2",
    "RetroSavePlaylist",
    "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
}
RECIPE = "RecipeDeleteMultipleRecipesWithConstraint"


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _content_sha(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("content_sha256", None)
    return sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def replay(trace_root: Path) -> dict[str, Any]:
    episodes: list[dict[str, Any]] = []
    for path in sorted(trace_root.glob("*/episode.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        summary = raw.get("summary", raw)
        memory = CompactVerifiedPendingMemory()
        executed = valid = pending_writes = original_chars = 0
        for step in summary.get("steps") or []:
            rendered, read = memory.read({})
            if rendered:
                memory.commit_injection(str(read["ticket_id"]), "offline-replay")
            original_chars += int((step.get("memory_read") or {}).get("rendered_chars") or 0)
            if not step.get("executed"):
                continue
            executed += 1
            action_summary = str((step.get("decision") or {}).get("action_summary") or "")
            parsed = parse_memory_prefix(action_summary)
            valid += int(parsed.valid)
            pending_writes += int(parsed.valid and not parsed.clear)
            memory.write(
                source_step=int(step["step"]),
                action_summary=action_summary,
                source_call_id="offline-replay",
                source_response_sha256="offline-replay",
                source_screenshot_sha256="offline-replay",
            )
        audit = memory.audit_record()
        episodes.append({
            "task_name": summary["task_name"],
            "reward": summary.get("evaluator_reward"),
            "episode_json_sha256": _sha(path),
            "executed_actions": executed,
            "valid_prefixes": valid,
            "pending_writes": pending_writes,
            "projected_nonempty_reads": audit["counters"]["nonempty_read_count"],
            "a1_rendered_chars": original_chars,
            "a1r2_projected_rendered_chars": audit["counters"]["injected_chars"],
        })
    executed = sum(item["executed_actions"] for item in episodes)
    valid = sum(item["valid_prefixes"] for item in episodes)
    original = sum(item["a1_rendered_chars"] for item in episodes)
    compact = sum(item["a1r2_projected_rendered_chars"] for item in episodes)
    sentinel_names = A0_FOUR | {RECIPE}
    sentinels = [item for item in episodes if item["task_name"] in sentinel_names]
    errors: list[str] = []
    if len(episodes) != 19 or executed != 596:
        errors.append("a1_trace_closure")
    if valid < 500:
        errors.append("prefix_coverage")
    if len(sentinels) != 5 or any(item["pending_writes"] < 1 or item["projected_nonempty_reads"] < 1 for item in sentinels):
        errors.append("five_success_sentinel_exposure")
    ratio = compact / original if original else 1.0
    if ratio > 0.35:
        errors.append("compact_render_ratio")
    report = {
        "schema": "a1r2_compact_verified_pending_offline_replay_v1",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "generation_calls": 0,
        "mechanism_id": MECHANISM_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": {"suite_id": A1_SUITE_ID, "episode_count": len(episodes)},
        "totals": {
            "executed_actions": executed,
            "valid_prefixes": valid,
            "a1_rendered_chars": original,
            "a1r2_projected_rendered_chars": compact,
            "projected_ratio": ratio,
        },
        "sentinel_tasks": sentinels,
        "episodes": episodes,
    }
    report["content_sha256"] = _content_sha(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-root", type=Path, default=ROOT / "runs/a1_working_memory" / A1_SUITE_ID / "episodes")
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/a1r2/A1R2_CVP_OFFLINE_REPLAY_REPORT.json")
    args = parser.parse_args()
    report = replay(args.trace_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(args.output), "content_sha256": report["content_sha256"], "errors": report["errors"]}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
