#!/usr/bin/env python3
"""Materialize the zero-generation stabilized-LRER V2 replay fixture."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "implementation/src")]

V1_FIXTURE = ROOT / "evidence/sys_r2_lrer/SYS_R2_LRER_REPLAY_FIXTURE.json"
CONFIG_PATH = ROOT / "implementation/configs/sys_r2_lrer_v2_hard_seed20260806.json"
SOURCE_SNAPSHOT = (
    ROOT
    / "evidence/sys_r2_lrer_v2/source_episodes/sys_r2_lrer_v1_browser_failure.json"
)
OUTPUT_PATH = ROOT / "evidence/sys_r2_lrer_v2/SYS_R2_LRER_V2_REPLAY_FIXTURE.json"
SNAPSHOT_SCHEMA = "sys_r2_lrer_v2_live_browser_source_snapshot_v1"


def content_sha256(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("content_sha256", None)
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def snapshot_from_episode(path: Path) -> dict[str, Any]:
    episode = json.loads(path.read_text(encoding="utf-8"))
    if episode.get("task_name") != "BrowserMultiply":
        raise RuntimeError("V2 development source must be BrowserMultiply")
    steps: list[dict[str, Any]] = []
    for ordinal, step in enumerate(episode.get("steps") or []):
        if int(step.get("step", -1)) != ordinal:
            raise RuntimeError("V1 live Browser step order drift")
        call = dict(step.get("model_call") or {})
        decision = dict(step.get("decision") or {})
        content = str(call.get("content") or "")
        response_sha = str(call.get("response_sha256") or "")
        if response_sha != sha256(content.encode("utf-8")).hexdigest():
            raise RuntimeError(f"response digest mismatch at step {ordinal}")
        transition = dict(step.get("transition") or {})
        before = dict(step.get("before") or {})
        after = dict(step.get("after") or {})
        review = dict(step.get("late_raw_evidence_review") or {})
        steps.append(
            {
                "step": ordinal,
                "executed": bool(step.get("executed")),
                "thought": str(decision.get("thought") or ""),
                "action_summary": str(decision.get("action_summary") or ""),
                "canonical_action": decision.get("canonical_action"),
                "terminal_status": decision.get("terminal_status"),
                "source_response_sha256": response_sha,
                "before_screenshot_sha256": str(before.get("screenshot_sha256") or ""),
                "after_screenshot_sha256": str(after.get("screenshot_sha256") or ""),
                "before_ui_sha256": str(before.get("ui_sha256") or ""),
                "after_ui_sha256": str(after.get("ui_sha256") or ""),
                "before_activity": transition.get("before_activity"),
                "after_activity": transition.get("after_activity"),
                "activity_changed": bool(transition.get("activity_changed")),
                "ui_sha_changed": bool(transition.get("ui_sha_changed")),
                "changed_pixel_fraction_gt_5": transition.get(
                    "changed_pixel_fraction_gt_5"
                ),
                "lrer_eligible": bool(review.get("eligible")),
                "lrer_blocked": bool(review.get("blocked")),
                "remaining_native_decision_slots": review.get(
                    "remaining_native_decision_slots"
                ),
            }
        )
    run_metadata = dict(episode.get("run_metadata") or {})
    payload = {
        "schema": SNAPSHOT_SCHEMA,
        "source_system_id": "sys_r2_late_raw_evidence_rehydration_v1",
        "source_experiment_id": "SYS_R2_LRER_QWEN3VL32B_S20260806_G3407_V1",
        "source_episode_path": path.as_posix(),
        "source_episode_sha256": file_sha256(path),
        "episode_id": str(episode.get("episode_id") or ""),
        "task_name": "BrowserMultiply",
        "task_seed": int(episode.get("seed")),
        "native_max_steps": int(run_metadata.get("native_max_steps")),
        "historical_reward": float(episode.get("evaluator_reward")),
        "historical_success": bool(episode.get("success")),
        "termination_reason": str(episode.get("termination_reason") or ""),
        "steps": steps,
    }
    return {**payload, "content_sha256": content_sha256(payload)}


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    if snapshot.get("schema") != SNAPSHOT_SCHEMA:
        raise RuntimeError("V2 live Browser snapshot schema drift")
    if snapshot.get("content_sha256") != content_sha256(snapshot):
        raise RuntimeError("V2 live Browser snapshot content hash drift")
    if snapshot.get("task_name") != "BrowserMultiply":
        raise RuntimeError("V2 live Browser snapshot task drift")
    if snapshot.get("historical_reward") != 0.0 or snapshot.get("historical_success"):
        raise RuntimeError("V1 live Browser failure outcome drift")
    if int(snapshot.get("native_max_steps") or 0) != 22:
        raise RuntimeError("V1 live Browser native budget drift")
    steps = list(snapshot.get("steps") or [])
    if len(steps) != 22 or [row.get("step") for row in steps] != list(range(22)):
        raise RuntimeError("V1 live Browser exact 22-step closure drift")
    for row in steps:
        if not re.fullmatch(
            r"[0-9a-f]{64}", str(row.get("source_response_sha256") or "")
        ):
            raise RuntimeError("V1 live Browser response hash malformed")


def materialize() -> dict[str, Any]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    v1_fixture = json.loads(V1_FIXTURE.read_text(encoding="utf-8"))
    snapshot = json.loads(SOURCE_SNAPSHOT.read_text(encoding="utf-8"))
    validate_snapshot(snapshot)
    if v1_fixture.get("content_sha256") != content_sha256(v1_fixture):
        raise RuntimeError("inherited V1 fixture hash drift")
    stale_steps = [
        int(row["step"])
        for row in snapshot["steps"]
        if row.get("activity_changed")
        and not row.get("ui_sha_changed")
        and float(row.get("changed_pixel_fraction_gt_5") or 0.0) <= 0.001
    ]
    value_steps = [
        int(row["step"])
        for row in snapshot["steps"]
        if any(
            phrase in (str(row.get("thought") or "") + " " + str(row.get("action_summary") or ""))
            for phrase in (
                "number '1'",
                "number 8",
                "number displayed is 10",
                "number 7",
                "number displayed is 2",
            )
        )
    ]
    result_steps = [
        int(row["step"])
        for row in snapshot["steps"]
        if isinstance(row.get("canonical_action"), dict)
        and row["canonical_action"].get("type") in {"type_text", "answer"}
    ]
    payload = {
        "schema": "sys_r2_lrer_v2_replay_fixture_v1",
        "analysis_type": "CPU_ONLY_ZERO_GENERATION_DEVELOPMENT_REPLAY",
        "generation_calls": 0,
        "config_sha256": file_sha256(CONFIG_PATH),
        "inherited_v1_fixture_content_sha256": v1_fixture["content_sha256"],
        "fixed_seven": list(config["seven_task_order"]),
        "v1_r2_episodes": v1_fixture["r2_episodes"],
        "r15_browser": v1_fixture["r15_browser"],
        "v1_live_browser": snapshot,
        "development_audit": {
            "first_value_step": min(value_steps),
            "all_value_steps": value_steps,
            "first_result_action_step": min(result_steps),
            "first_result_remaining_slots": snapshot["steps"][min(result_steps)][
                "remaining_native_decision_slots"
            ],
            "lrer_eligible_count": sum(
                int(bool(row.get("lrer_eligible"))) for row in snapshot["steps"]
            ),
            "lrer_blocked_count": sum(
                int(bool(row.get("lrer_blocked"))) for row in snapshot["steps"]
            ),
            "cross_activity_stale_capture_steps": stale_steps,
            "settle_policy_is_counterfactual": True,
        },
    }
    return {**payload, "content_sha256": content_sha256(payload)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-from-episode", type=Path)
    parser.add_argument("--snapshot-output", type=Path, default=SOURCE_SNAPSHOT)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    if args.snapshot_from_episode is not None:
        snapshot = snapshot_from_episode(args.snapshot_from_episode.resolve())
        args.snapshot_output.parent.mkdir(parents=True, exist_ok=True)
        args.snapshot_output.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    fixture = materialize()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(fixture, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "generation_calls": 0,
                "content_sha256": fixture["content_sha256"],
                "development_audit": fixture["development_audit"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
