#!/usr/bin/env python3
"""Zero-generation replay of A1-R2 traces through A1-R3 SRPL."""

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

from raven_m.official_qwen_mobile.a1r3_stale_resistant_pending import (  # noqa: E402
    MECHANISM_ID,
    StaleResistantPendingMemory,
    parse_memory_prefix,
)

A1R2_SUITE_ID = "official_qwen_20260814T145307_50081981"
DEFAULT_SUITE = ROOT / "runs/a1r2_cvp" / A1R2_SUITE_ID
SENTINELS = {
    "ExpenseDeleteMultiple2",
    "RetroSavePlaylist",
    "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
    "RecipeDeleteMultipleRecipesWithConstraint",
    "OsmAndMarker",
}


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return sha256(raw).hexdigest()


def _content_sha(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("content_sha256", None)
    return _canonical_sha(payload)


def replay(suite_dir: Path) -> dict[str, Any]:
    checkpoint_path = suite_dir / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    summaries = list(checkpoint.get("valid_summaries") or [])
    entries = list(checkpoint.get("a1r2_valid_entries") or [])
    entry_by_id = {str(item.get("episode_id")): item for item in entries}
    binding_errors: list[str] = []
    episodes: list[dict[str, Any]] = []
    for summary in summaries:
        episode_id = str(summary["episode_id"])
        entry = entry_by_id.get(episode_id) or {}
        path = suite_dir / "episodes" / episode_id / "episode.json"
        if not path.is_file():
            binding_errors.append(f"episode_missing:{episode_id}")
            continue
        if _sha(path) != entry.get("episode_json_sha256"):
            binding_errors.append(f"episode_hash:{episode_id}")
        if _canonical_sha(summary) != entry.get("summary_sha256"):
            binding_errors.append(f"summary_hash:{episode_id}")
        memory = StaleResistantPendingMemory()
        valid_prefixes = 0
        actual_chars = 0
        failure_reads = 0
        failure_created_steps: list[int] = []
        for step in summary.get("steps") or []:
            rendered, read = memory.read({})
            if rendered:
                failure_reads += int(read.get("failure_evidence_injected") is True)
                memory.commit_injection(str(read["ticket_id"]), "offline-replay")
            actual_chars += len(str((step.get("memory_read") or {}).get("exact_injected_text") or ""))
            if not step.get("executed"):
                continue
            action_summary = str((step.get("decision") or {}).get("action_summary") or "")
            valid_prefixes += int(parse_memory_prefix(action_summary).valid)
            event = memory.observe_step(
                source_step=int(step["step"]),
                action_summary=action_summary,
                canonical_action=(step.get("decision") or {}).get("canonical_action"),
                transition=step.get("transition") or {},
                source_call_id="offline-replay",
                source_response_sha256="offline-replay",
                source_screenshot_sha256=str(step.get("before_screenshot_sha256") or "offline-replay"),
            )
            if event.get("failure_evidence_created"):
                failure_created_steps.append(int(step["step"]))
        counters = memory.audit_record()["counters"]
        episodes.append(
            {
                "task_name": summary["task_name"],
                "episode_id": episode_id,
                "episode_json_sha256": entry.get("episode_json_sha256"),
                "reward": summary.get("evaluator_reward"),
                "success": bool(summary.get("success")),
                "model_calls": int(summary.get("model_call_count") or 0),
                "executed_actions": int(summary.get("executed_action_count") or 0),
                "valid_prefixes": valid_prefixes,
                "a1r2_actual_rendered_chars": actual_chars,
                "projected_nonempty_reads": counters["nonempty_read_count"],
                "projected_rendered_chars": counters["injected_chars"],
                "same_state_nonrefresh_count": counters["same_state_nonrefresh_count"],
                "retired_state_rejection_count": counters["retired_state_rejection_count"],
                "failure_evidence_count": counters["failure_evidence_count"],
                "failure_evidence_read_count": failure_reads,
                "failure_evidence_created_steps": failure_created_steps,
            }
        )
    totals = {
        "valid_episode_count": len(episodes),
        "model_calls": sum(item["model_calls"] for item in episodes),
        "executed_actions": sum(item["executed_actions"] for item in episodes),
        "valid_prefixes": sum(item["valid_prefixes"] for item in episodes),
        "a1r2_actual_rendered_chars": sum(item["a1r2_actual_rendered_chars"] for item in episodes),
        "projected_nonempty_reads": sum(item["projected_nonempty_reads"] for item in episodes),
        "projected_rendered_chars": sum(item["projected_rendered_chars"] for item in episodes),
        "nonreinforcing_state_write_count": sum(
            item["same_state_nonrefresh_count"] + item["retired_state_rejection_count"]
            for item in episodes
        ),
        "failure_evidence_count": sum(item["failure_evidence_count"] for item in episodes),
        "failure_evidence_read_count": sum(item["failure_evidence_read_count"] for item in episodes),
        "failure_evidence_read_episode_count": sum(
            item["failure_evidence_read_count"] > 0 for item in episodes
        ),
    }
    totals["projected_render_ratio_vs_a1r2"] = (
        totals["projected_rendered_chars"] / totals["a1r2_actual_rendered_chars"]
        if totals["a1r2_actual_rendered_chars"]
        else 1.0
    )
    sentinels = [item for item in episodes if item["task_name"] in SENTINELS]
    errors = list(binding_errors)
    if len(summaries) != 19 or len(entries) != 19 or len(episodes) != 19:
        errors.append("a1r2_trace_closure")
    if totals["model_calls"] != 603 or totals["executed_actions"] != 595:
        errors.append("a1r2_execution_totals")
    if len(sentinels) != 6 or any(
        item["projected_nonempty_reads"] < 1 or item["failure_evidence_count"] != 0
        for item in sentinels
    ):
        errors.append("six_success_sentinel_preservation")
    if totals["nonreinforcing_state_write_count"] < 100:
        errors.append("insufficient_stale_suppression_exposure")
    if totals["failure_evidence_read_episode_count"] < 2:
        errors.append("insufficient_failure_evidence_exposure")
    if totals["projected_render_ratio_vs_a1r2"] > 0.75:
        errors.append("projected_render_ratio")
    report = {
        "schema": "a1r3_stale_resistant_pending_offline_replay_v1",
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "generation_calls": 0,
        "mechanism_id": MECHANISM_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "suite_id": A1R2_SUITE_ID,
            "checkpoint_sha256": _sha(checkpoint_path),
            "checkpoint_content_sha256": _canonical_sha(checkpoint),
            "valid_entry_count": len(entries),
        },
        "totals": totals,
        "sentinel_tasks": sentinels,
        "episodes": episodes,
    }
    report["content_sha256"] = _content_sha(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-dir", type=Path, default=DEFAULT_SUITE)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evidence/a1r3/A1R3_SRPL_OFFLINE_REPLAY_REPORT.json",
    )
    args = parser.parse_args()
    report = replay(args.suite_dir.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": report["status"],
                "output": str(args.output),
                "content_sha256": report["content_sha256"],
                "errors": report["errors"],
                "totals": report["totals"],
            },
            indent=2,
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
