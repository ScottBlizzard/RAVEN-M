#!/usr/bin/env python3
"""Materialize model-authored response text needed by the A1-R14 replay."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "implementation/src")]
from raven_m.official_qwen_mobile import a1r13_contract as order_contract  # noqa: E402
from raven_m.official_qwen_mobile import a1r13d_contract as digest_contract  # noqa: E402


def _latest(root: Path) -> Path:
    suites = sorted(root.glob("official_qwen_*"))
    if not suites:
        raise RuntimeError(f"suite missing: {root}")
    return suites[-1]


def _episodes(suite: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for path in (suite / "episodes").glob("*/episode.json"):
        episode = json.loads(path.read_text(encoding="utf-8"))
        result[str(episode["task_name"])] = path
    return result


def materialize(v4_suite: Path, target_suite: Path) -> dict:
    sources = _episodes(v4_suite)
    target_sources = _episodes(target_suite)
    sources[order_contract.TARGET_GATE_TASK] = target_sources[order_contract.TARGET_GATE_TASK]
    rows = []
    for task_name in order_contract.FULL_TASK_ORDER:
        path = sources[task_name]
        episode = json.loads(path.read_text(encoding="utf-8"))
        steps = []
        for step in episode.get("steps") or []:
            call = step.get("model_call") or {}
            decision = step.get("decision") or {}
            steps.append(
                {
                    "step": int(step["step"]),
                    "action_summary": str(decision.get("action_summary") or ""),
                    "model_response": str(call.get("content") or ""),
                    "source_call_id": str(call.get("call_id") or ""),
                    "source_response_sha256": str(call.get("response_sha256") or ""),
                    "source_screenshot_sha256": str(step.get("before_screenshot_sha256") or ""),
                }
            )
        rows.append(
            {
                "task_name": task_name,
                "episode_id": episode["episode_id"],
                "goal": episode["task_goal"],
                "historical_reward": episode["evaluator_reward"],
                "source_episode_json_sha256": digest_contract.file_sha256(path),
                "source_suite": v4_suite.name if task_name != order_contract.TARGET_GATE_TASK else target_suite.name,
                "steps": steps,
            }
        )
    payload = {
        "schema": "a1r14_rgvr_replay_fixture_v1",
        "generation_calls": 0,
        "source_policy": "SYS-NAG-V4-19 with Browser replaced by sealed A1-R13D target trace",
        "episode_count": len(rows),
        "step_count": sum(len(row["steps"]) for row in rows),
        "episodes": rows,
    }
    return {**payload, "content_sha256": digest_contract.content_sha256(payload)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v4-suite", type=Path, default=_latest(ROOT / "runs/sys_nag_v4"))
    parser.add_argument("--target-suite", type=Path, default=_latest(ROOT / "runs/a1r13d_evr"))
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/a1r14/A1R14_RGVR_REPLAY_FIXTURE.json")
    args = parser.parse_args()
    fixture = materialize(args.v4_suite.resolve(), args.target_suite.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(fixture, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"episodes": fixture["episode_count"], "steps": fixture["step_count"], "content_sha256": fixture["content_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
