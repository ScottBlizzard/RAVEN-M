#!/usr/bin/env python3
"""Zero-generation replay for the SYS-NAG V4 composite guards."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "implementation/src")]

from raven_m.official_qwen_mobile import sys_nag_contract as contract  # noqa: E402
from raven_m.official_qwen_mobile.numeric_answer_guard import (  # noqa: E402
    NumericAnswerConsistencyGuard,
)
from raven_m.official_qwen_mobile.a12_minimal_action_divergence import (  # noqa: E402
    VisualDescriptor,
    describe_visual_state,
)

DEFAULT_SUITE = ROOT / "runs/a1r2_cvp/official_qwen_20260814T145307_50081981"
DEFAULT_FIXTURE = ROOT / "evidence/sys_nag_v4/SYS_NAG_V4_REPLAY_FIXTURE.json"
V2_FAILURE_EPISODE = (
    ROOT / "runs/sys_trrc_v2_full/official_qwen_20260816T005559_70b00ecd/episodes/"
    "SportsTrackerTotalDurationForCategoryThisWeek_20260806_aa0c6805/episode.json"
)
V2_TERMINAL_FAILURE_EPISODE = (
    ROOT / "runs/sys_nag_v2/official_qwen_20260816T024642_c7867dfe/episodes/"
    "RetroSavePlaylist_20260806_5d6494df/episode.json"
)
V3_ROUTE_FAILURE_EPISODE = (
    ROOT / "runs/sys_nag_v3/official_qwen_20260816T033338_0021ddde/episodes/"
    "RetroSavePlaylist_20260806_f93ea834/episode.json"
)


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _step_projection(step: dict, episode_dir: Path) -> dict:
    mapped = step.get("mapped_action") or {}
    descriptor = describe_visual_state(
        np.asarray(
            Image.open(episode_dir / str(step.get("before_screenshot"))).convert(
                "RGB"
            )
        )
    )
    return {
        "step": step.get("step"),
        "decision": step.get("decision"),
        "memory_read": {
            key: (step.get("memory_read") or {}).get(key)
            for key in ("exact_injected_text", "rendered_chars")
            if key in (step.get("memory_read") or {})
        },
        "executed": bool(step.get("executed")),
        "mapped_canonical_action": (
            mapped.get("canonical") if isinstance(mapped, dict) else None
        ),
        "before_descriptor": asdict(descriptor),
    }


def materialize_fixture(suite_dir: Path = DEFAULT_SUITE) -> dict:
    checkpoint_path = suite_dir / "checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    valid_ids = {
        str(item.get("episode_id")) for item in checkpoint.get("valid_summaries") or []
    }
    episodes = []
    for path in sorted((suite_dir / "episodes").glob("*/episode.json")):
        if path.parent.name not in valid_ids:
            continue
        episode = json.loads(path.read_text(encoding="utf-8"))
        episodes.append(
            {
                "task_name": episode.get("task_name"),
                "episode_id": episode.get("episode_id"),
                "success": episode.get("success"),
                "native_max_steps": int(
                    (episode.get("run_metadata") or {}).get("native_max_steps") or 0
                ),
                "source_episode_file_sha256": contract.file_sha256(path),
                "steps": [
                    _step_projection(step, path.parent)
                    for step in episode.get("steps") or []
                ],
            }
        )
    numeric_path = V2_FAILURE_EPISODE
    terminal_path = V2_TERMINAL_FAILURE_EPISODE
    route_path = V3_ROUTE_FAILURE_EPISODE
    numeric = json.loads(numeric_path.read_text(encoding="utf-8"))
    terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
    route = json.loads(route_path.read_text(encoding="utf-8"))
    payload = {
        "schema": "sys_nag_v4_replay_fixture_v1",
        "generation_calls": 0,
        "source": {
            "a1r2_checkpoint_file_sha256": contract.file_sha256(checkpoint_path),
            "numeric_failure_episode_file_sha256": contract.file_sha256(numeric_path),
            "terminal_failure_episode_file_sha256": contract.file_sha256(terminal_path),
            "route_failure_episode_file_sha256": contract.file_sha256(route_path),
        },
        "episodes": episodes,
        "numeric_failure": {
            "task_name": numeric.get("task_name"),
            "episode_id": numeric.get("episode_id"),
            "native_max_steps": int(
                (numeric.get("run_metadata") or {}).get("native_max_steps") or 0
            ),
            "final_step": _step_projection(
                (numeric.get("steps") or [])[-1], numeric_path.parent
            ),
        },
        "terminal_failure": {
            "task_name": terminal.get("task_name"),
            "episode_id": terminal.get("episode_id"),
            "native_max_steps": int(
                (terminal.get("run_metadata") or {}).get("native_max_steps") or 0
            ),
            "steps": [
                _step_projection(step, terminal_path.parent)
                for step in terminal.get("steps") or []
            ],
        },
        "route_failure": {
            "task_name": route.get("task_name"),
            "episode_id": route.get("episode_id"),
            "native_max_steps": int(
                (route.get("run_metadata") or {}).get("native_max_steps") or 0
            ),
            "steps": [
                _step_projection(step, route_path.parent)
                for step in route.get("steps") or []
            ],
        },
    }
    return {**payload, "content_sha256": contract.content_sha256(payload)}


def replay(fixture_path: Path = DEFAULT_FIXTURE) -> dict:
    errors: list[str] = []
    episode_rows: list[dict] = []
    total_reviews = total_eligible = total_overrides = 0
    historical_terminal_blocks = 0
    historical_route_blocks = 0
    projected_rendered_chars = 0
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if (
        fixture.get("schema") != "sys_nag_v4_replay_fixture_v1"
        or fixture.get("generation_calls") != 0
        or fixture.get("content_sha256") != contract.content_sha256(fixture)
    ):
        errors.append("replay_fixture_invalid")
    for episode in fixture.get("episodes") or []:
        guard = NumericAnswerConsistencyGuard()
        events: list[dict] = []
        previous_executed_action: dict | None = None
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
            terminal_event = guard.review_terminal(
                terminal_status=decision.get("terminal_status"),
                memory_read=step.get("memory_read"),
                previous_executed_action=previous_executed_action,
                remaining_native_decision_slots=max(
                    0,
                    int(episode.get("native_max_steps") or 0)
                    - int(step.get("step") or 0)
                    - 1,
                ),
            )
            if terminal_event.get("blocked"):
                historical_terminal_blocks += 1
                events.append({"step": step.get("step"), **terminal_event})
            route_event = guard.review_route(
                proposed_action=proposed,
                action_summary=str(decision.get("action_summary") or ""),
                memory_read=step.get("memory_read"),
                before_descriptor=VisualDescriptor(**step["before_descriptor"]),
                remaining_native_decision_slots=max(
                    0,
                    int(episode.get("native_max_steps") or 0)
                    - int(step.get("step") or 0)
                    - 1,
                ),
            )
            if route_event.get("blocked"):
                historical_route_blocks += 1
                events.append({"step": step.get("step"), **route_event})
            canonical = step.get("mapped_canonical_action")
            if step.get("executed") and isinstance(canonical, dict):
                previous_executed_action = dict(canonical)
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
                "route_block_count": counters["route_block_count"],
                "events": events,
            }
        )
    if len(episode_rows) != 19 or len({row["task_name"] for row in episode_rows}) != 19:
        errors.append("a1r2_suite_not_exact_19")

    observed = fixture.get("numeric_failure") or {}
    final_decision = (observed.get("final_step") or {}).get("decision") or {}
    guard = NumericAnswerConsistencyGuard()
    corrected, event = guard.review(
        proposed_action=final_decision["canonical_action"],
        action_summary=final_decision["action_summary"],
    )
    numeric_regression = {
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

    terminal_failure = fixture.get("terminal_failure") or {}
    terminal_steps = terminal_failure.get("steps") or []
    terminal_step = terminal_steps[-1]
    previous_step = next(
        step for step in reversed(terminal_steps[:-1]) if step.get("executed")
    )
    terminal_guard = NumericAnswerConsistencyGuard()
    terminal_event = terminal_guard.review_terminal(
        terminal_status=(terminal_step.get("decision") or {}).get("terminal_status"),
        memory_read=terminal_step.get("memory_read"),
        previous_executed_action=previous_step.get("mapped_canonical_action"),
        remaining_native_decision_slots=max(
            0,
            int(terminal_failure.get("native_max_steps") or 0)
            - int(terminal_step.get("step") or 0)
            - 1,
        ),
    )
    terminal_regression = {
        "task_name": terminal_failure.get("task_name"),
        "episode_id": terminal_failure.get("episode_id"),
        "source_step": terminal_step.get("step"),
        "event": terminal_event,
    }
    if not terminal_event.get("blocked"):
        errors.append("v2_terminal_failure_not_blocked")
    if historical_terminal_blocks:
        errors.append("historical_a1r2_terminal_false_positive")

    route_failure = fixture.get("route_failure") or {}
    route_guard = NumericAnswerConsistencyGuard()
    route_events: list[dict] = []
    for step in route_failure.get("steps") or []:
        decision = step.get("decision") or {}
        route_event = route_guard.review_route(
            proposed_action=decision.get("canonical_action"),
            action_summary=str(decision.get("action_summary") or ""),
            memory_read=step.get("memory_read"),
            before_descriptor=VisualDescriptor(**step["before_descriptor"]),
            remaining_native_decision_slots=max(
                0,
                int(route_failure.get("native_max_steps") or 0)
                - int(step.get("step") or 0)
                - 1,
            ),
        )
        if route_event.get("blocked"):
            route_events.append({"step": step.get("step"), **route_event})
    route_regression = {
        "task_name": route_failure.get("task_name"),
        "episode_id": route_failure.get("episode_id"),
        "blocked_events": route_events,
    }
    if len(route_events) != 1 or route_events[0].get("step") != 39:
        errors.append("v3_route_failure_not_blocked_once_at_step39")
    historical_success_route_blocks = sum(
        int(row.get("route_block_count") or 0)
        for row in episode_rows
        if row.get("task_name") in contract.CAPABILITY_GATE_TASKS
    )
    if historical_success_route_blocks:
        errors.append("historical_a1r2_success_route_false_positive")

    payload = {
        "schema": contract.OFFLINE_REPLAY_SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "generation_calls": 0,
        "mechanism_id": contract.MECHANISM_ID,
        "system_id": contract.SYSTEM_ID,
        "source": {
            "fixture_file": str(fixture_path.relative_to(ROOT)).replace("\\", "/"),
            "fixture_content_sha256": fixture.get("content_sha256"),
        },
        "totals": {
            "valid_episode_count": len(episode_rows),
            "review_count": total_reviews,
            "eligible_count": total_eligible,
            "override_count": total_overrides,
            "projected_rendered_chars": projected_rendered_chars,
            "historical_terminal_block_count": historical_terminal_blocks,
            "historical_route_block_count": historical_route_blocks,
            "historical_success_route_block_count": historical_success_route_blocks,
        },
        "sentinel_tasks": [
            "ExpenseDeleteMultiple2",
            "SportsTrackerTotalDurationForCategoryThisWeek",
            "RecipeDeleteMultipleRecipesWithConstraint",
        ],
        "numeric_failure_regression": numeric_regression,
        "terminal_failure_regression": terminal_regression,
        "route_failure_regression": route_regression,
        "episodes": episode_rows,
    }
    return {**payload, "content_sha256": contract.content_sha256(payload)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--materialize-fixture", action="store_true")
    parser.add_argument("--suite-dir", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--output", type=Path, default=contract.OFFLINE_REPLAY_PATH)
    args = parser.parse_args()
    if args.materialize_fixture:
        fixture = materialize_fixture(args.suite_dir.resolve())
        _write(args.fixture.resolve(), fixture)
    result = replay(args.fixture.resolve())
    _write(args.output, result)
    print(json.dumps({"status": result["status"], "errors": result["errors"], "totals": result["totals"]}, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
