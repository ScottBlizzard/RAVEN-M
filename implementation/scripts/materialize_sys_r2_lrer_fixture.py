#!/usr/bin/env python3
"""Materialize the zero-generation SYS-R2-LRER development fixture.

The default path reads only small, tracked source snapshots.  Access to the
gitignored ``runs/`` tree is an explicit bootstrap operation used to refresh
those snapshots, never a prerequisite for replay or tests.
"""

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

R2_SUITE = ROOT / "runs/a1r2_cvp/official_qwen_20260814T145307_50081981"
R15_SUITE = ROOT / "runs/a1r15_eovr/official_qwen_20260818T053157_cab07201"
CONFIG_PATH = ROOT / "implementation/configs/sys_r2_lrer_hard_seed20260806.json"
SOURCE_SNAPSHOT_DIR = ROOT / "evidence/sys_r2_lrer/source_episodes"
OUTPUT_PATH = ROOT / "evidence/sys_r2_lrer/SYS_R2_LRER_REPLAY_FIXTURE.json"
SNAPSHOT_SCHEMA = "sys_r2_lrer_source_episode_snapshot_v1"
SNAPSHOT_KEYS = {
    "schema",
    "content_sha256",
    "source_arm",
    "source_episode_path",
    "source_episode_sha256",
    "episode_id",
    "task_name",
    "task_goal",
    "task_seed",
    "native_max_steps",
    "historical_reward",
    "historical_success",
    "steps",
}
SNAPSHOT_STEP_KEYS = {
    "step",
    "executed",
    "thought",
    "action_summary",
    "canonical_action",
    "terminal_status",
    "source_call_id",
    "source_response_sha256",
}


def canonical_sha256(value: dict[str, Any]) -> str:
    payload = {key: item for key, item in value.items() if key != "content_sha256"}
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _episode_path(suite: Path, task_name: str) -> Path:
    matches = sorted((suite / "episodes").glob(f"{task_name}_*/episode.json"))
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one {task_name} episode in {suite}, got {len(matches)}"
        )
    return matches[0]


def _materialize_raw_episode(path: Path, *, source_arm: str) -> dict[str, Any]:
    episode = json.loads(path.read_text(encoding="utf-8"))
    native_max_steps = int((episode.get("run_metadata") or {}).get("native_max_steps"))
    steps: list[dict[str, Any]] = []
    for expected_step, step in enumerate(episode.get("steps") or []):
        source_step = int(step.get("step"))
        if source_step != expected_step:
            raise RuntimeError(f"non-contiguous step sequence in {path}: {source_step}")
        call = dict(step.get("model_call") or {})
        decision = dict(step.get("decision") or {})
        content = str(call.get("content") or "")
        response_sha256 = str(call.get("response_sha256") or "")
        if response_sha256 != sha256(content.encode("utf-8")).hexdigest():
            raise RuntimeError(f"response digest mismatch at {path}:{source_step}")
        canonical_action = decision.get("canonical_action")
        if canonical_action is not None and not isinstance(canonical_action, dict):
            raise RuntimeError(f"canonical action schema mismatch at {path}:{source_step}")
        steps.append(
            {
                "step": source_step,
                "executed": bool(step.get("executed")),
                "thought": str(decision.get("thought") or ""),
                "action_summary": str(decision.get("action_summary") or ""),
                "canonical_action": canonical_action,
                "terminal_status": decision.get("terminal_status"),
                "source_call_id": str(call.get("call_id") or ""),
                "source_response_sha256": response_sha256,
            }
        )
    return {
        "source_arm": source_arm,
        "source_episode_path": path.relative_to(ROOT).as_posix(),
        "source_episode_sha256": file_sha256(path),
        "episode_id": str(episode.get("episode_id")),
        "task_name": str(episode.get("task_name")),
        "task_goal": str(episode.get("task_goal")),
        "task_seed": int(episode.get("seed")),
        "native_max_steps": native_max_steps,
        "historical_reward": float(episode.get("evaluator_reward")),
        "historical_success": bool(episode.get("success")),
        "steps": steps,
    }


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _snapshot_filename(source_arm: str, ordinal: int, task_name: str) -> str:
    arm = source_arm.lower().replace("-", "_")
    return f"{arm}_{ordinal:02d}_{_slug(task_name)}.json"


def _snapshot_payload(episode: dict[str, Any]) -> dict[str, Any]:
    payload = {"schema": SNAPSHOT_SCHEMA, **episode}
    return {**payload, "content_sha256": canonical_sha256(payload)}


def snapshot_sources(
    r2_suite: Path,
    r15_suite: Path,
    output_dir: Path = SOURCE_SNAPSHOT_DIR,
) -> list[Path]:
    """Extract the minimum replay-relevant fields from eight raw episodes."""

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    task_order = tuple(str(name) for name in config["seven_task_order"])
    snapshots = [
        _snapshot_payload(
            _materialize_raw_episode(
                _episode_path(r2_suite, task_name), source_arm="A1-R2"
            )
        )
        for task_name in task_order
    ]
    snapshots.append(
        _snapshot_payload(
            _materialize_raw_episode(
                _episode_path(r15_suite, "BrowserMultiply"), source_arm="A1-R15"
            )
        )
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for ordinal, snapshot in enumerate(snapshots, start=1):
        arm_ordinal = ordinal if snapshot["source_arm"] == "A1-R2" else 1
        path = output_dir / _snapshot_filename(
            str(snapshot["source_arm"]), arm_ordinal, str(snapshot["task_name"])
        )
        path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        paths.append(path)
    return paths


def _load_snapshot(path: Path, *, source_arm: str, task_name: str) -> dict[str, Any]:
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if set(snapshot) != SNAPSHOT_KEYS:
        raise RuntimeError(f"source snapshot field closure mismatch: {path}")
    if snapshot.get("schema") != SNAPSHOT_SCHEMA:
        raise RuntimeError(f"source snapshot schema mismatch: {path}")
    if snapshot.get("content_sha256") != canonical_sha256(snapshot):
        raise RuntimeError(f"source snapshot digest mismatch: {path}")
    if snapshot.get("source_arm") != source_arm:
        raise RuntimeError(f"source arm mismatch: {path}")
    if snapshot.get("task_name") != task_name:
        raise RuntimeError(f"source task mismatch: {path}")
    if not re.fullmatch(r"[0-9a-f]{64}", str(snapshot["source_episode_sha256"])):
        raise RuntimeError(f"source episode digest malformed: {path}")
    episode = {
        key: value
        for key, value in snapshot.items()
        if key not in {"schema", "content_sha256"}
    }
    for expected_step, step in enumerate(episode.get("steps") or []):
        if set(step) != SNAPSHOT_STEP_KEYS:
            raise RuntimeError(f"source snapshot step field closure mismatch: {path}")
        if int(step.get("step", -1)) != expected_step:
            raise RuntimeError(f"non-contiguous source snapshot: {path}")
        if not isinstance(step.get("canonical_action"), (dict, type(None))):
            raise RuntimeError(f"canonical action schema mismatch: {path}:{expected_step}")
        if not re.fullmatch(r"[0-9a-f]{64}", str(step["source_response_sha256"])):
            raise RuntimeError(f"source response digest malformed: {path}:{expected_step}")
    return episode


def _source_suite(episode: dict[str, Any]) -> str:
    source_path = Path(str(episode["source_episode_path"]))
    try:
        return source_path.parents[2].as_posix()
    except IndexError as exc:
        raise RuntimeError(f"invalid source episode path: {source_path}") from exc


def materialize(source_dir: Path = SOURCE_SNAPSHOT_DIR) -> dict[str, Any]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    task_order = tuple(str(name) for name in config["seven_task_order"])
    if len(task_order) != len(set(task_order)) or len(task_order) != 7:
        raise RuntimeError("SYS-R2-LRER seven-task order is not exactly seven unique tasks")
    r2_episodes = [
        _load_snapshot(
            source_dir / _snapshot_filename("A1-R2", ordinal, task_name),
            source_arm="A1-R2",
            task_name=task_name,
        )
        for ordinal, task_name in enumerate(task_order, start=1)
    ]
    r15_browser = _load_snapshot(
        source_dir / _snapshot_filename("A1-R15", 1, "BrowserMultiply"),
        source_arm="A1-R15",
        task_name="BrowserMultiply",
    )
    if [row["task_name"] for row in r2_episodes] != list(task_order):
        raise RuntimeError("R2 task order drift")
    if r2_episodes[0]["historical_success"]:
        raise RuntimeError("frozen R2 Browser episode unexpectedly succeeded")
    if not all(row["historical_success"] for row in r2_episodes[1:]):
        raise RuntimeError("frozen R2 six-task success panel drift")
    if not r15_browser["historical_success"]:
        raise RuntimeError("sealed R15 Browser success missing")
    payload: dict[str, Any] = {
        "schema": "sys_r2_lrer_replay_fixture_v1",
        "analysis_type": "CPU_ONLY_ZERO_GENERATION_DEVELOPMENT_REPLAY",
        "generation_calls": 0,
        "source_policy": (
            "exact frozen A1-R2 seven-task raw episodes plus sealed A1-R15 "
            "Browser raw episode"
        ),
        "config_sha256": file_sha256(CONFIG_PATH),
        "task_order": list(task_order),
        "source_suites": {
            "A1-R2": _source_suite(r2_episodes[0]),
            "A1-R15": _source_suite(r15_browser),
        },
        "r2_episodes": r2_episodes,
        "r15_browser": r15_browser,
    }
    return {**payload, "content_sha256": canonical_sha256(payload)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, default=SOURCE_SNAPSHOT_DIR)
    parser.add_argument(
        "--snapshot-from-runs",
        action="store_true",
        help="explicitly refresh tracked source snapshots from raw run artifacts",
    )
    parser.add_argument("--r2-suite", type=Path, default=R2_SUITE)
    parser.add_argument("--r15-suite", type=Path, default=R15_SUITE)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    if args.snapshot_from_runs:
        snapshot_sources(
            args.r2_suite.resolve(), args.r15_suite.resolve(), args.source_dir.resolve()
        )
    fixture = materialize(args.source_dir.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(fixture, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "generation_calls": 0,
                "r2_episode_count": len(fixture["r2_episodes"]),
                "r15_episode_id": fixture["r15_browser"]["episode_id"],
                "content_sha256": fixture["content_sha256"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
