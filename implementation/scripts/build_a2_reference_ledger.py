"""Build the immutable A0/A1 paired comparator ledger from raw episode traces."""

from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


EXPECTED = {
    "A0": {"success_count": 4, "reward_sum": 4.5, "model_calls": 329, "total_tokens": 1_273_361},
    "A1": {"success_count": 5, "reward_sum": 5.5, "model_calls": 603, "total_tokens": 3_464_267},
}


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _seconds(started: str, finished: str) -> float:
    return (datetime.fromisoformat(finished) - datetime.fromisoformat(started)).total_seconds()


def _episode_record(path: Path, *, arm: str, root: Path) -> dict[str, Any]:
    episode = json.loads(path.read_text(encoding="utf-8"))
    steps = list(episode.get("steps") or [])
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    attempts = []
    for step in steps:
        call = step.get("model_call") or {}
        for key in usage:
            usage[key] += int((call.get("usage") or {}).get(key) or 0)
        attempts.append(int((call.get("raven_meta") or {}).get("transport_attempts") or 0))
    memory = episode.get("memory_mechanism") or {}
    return {
        "arm": arm,
        "task_name": str(episode["task_name"]),
        "seed": int(episode["seed"]),
        "episode_id": str(episode["episode_id"]),
        "episode_json": str(path.relative_to(root)).replace("\\", "/"),
        "episode_json_sha256": _hash(path),
        "reward": float(episode["evaluator_reward"]),
        "success": bool(episode["success"]),
        "partial_success": 0.0 < float(episode["evaluator_reward"]) < 1.0,
        "termination_reason": str(episode["termination_reason"]),
        "model_calls": int(episode["model_call_count"]),
        "executed_actions": int(episode["executed_action_count"]),
        **usage,
        "valid_elapsed_seconds": _seconds(episode["started_at"], episode["finished_at"]),
        "transport_attempt_total": sum(attempts),
        "transport_attempt_max": max(attempts, default=0),
        "memory_write_success_count": int(memory.get("write_success_count") or 0),
        "memory_nonempty_read_count": int(memory.get("nonempty_read_count") or 0),
    }


def _arm(root: Path, name: str) -> list[dict[str, Any]]:
    records = [
        _episode_record(path, arm=name, root=root)
        for path in sorted((root / "episodes").glob("*/episode.json"))
        if int(json.loads(path.read_text(encoding="utf-8"))["seed"]) == 20260806
    ]
    if len(records) != 19 or len({item["task_name"] for item in records}) != 19:
        raise RuntimeError(f"{name} does not contain exactly 19 unique seed-20260806 episodes")
    return records


def _summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    summed = {
        "episode_count": len(records),
        "success_count": sum(int(item["success"]) for item in records),
        "reward_sum": sum(float(item["reward"]) for item in records),
        "model_calls": sum(int(item["model_calls"]) for item in records),
        "executed_actions": sum(int(item["executed_actions"]) for item in records),
        "prompt_tokens": sum(int(item["prompt_tokens"]) for item in records),
        "completion_tokens": sum(int(item["completion_tokens"]) for item in records),
        "total_tokens": sum(int(item["total_tokens"]) for item in records),
        "valid_elapsed_seconds": sum(float(item["valid_elapsed_seconds"]) for item in records),
        "transport_attempt_total": sum(int(item["transport_attempt_total"]) for item in records),
        "transport_attempt_max": max(int(item["transport_attempt_max"]) for item in records),
        "memory_write_success_count": sum(int(item["memory_write_success_count"]) for item in records),
        "memory_nonempty_read_count": sum(int(item["memory_nonempty_read_count"]) for item in records),
    }
    return summed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a0-root", type=Path, required=True)
    parser.add_argument("--a1-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    a0_root, a1_root = args.a0_root.resolve(), args.a1_root.resolve()
    arms = {"A0": _arm(a0_root, "A0"), "A1": _arm(a1_root, "A1")}
    summaries = {name: _summary(records) for name, records in arms.items()}
    for name, expected in EXPECTED.items():
        for key, value in expected.items():
            if summaries[name][key] != value:
                raise RuntimeError(f"{name} invariant drift: {key}={summaries[name][key]!r}, expected {value!r}")
    if summaries["A1"]["memory_write_success_count"] != 515:
        raise RuntimeError("A1 memory write invariant drift")
    if summaries["A1"]["memory_nonempty_read_count"] != 580:
        raise RuntimeError("A1 memory read invariant drift")
    by_arm = {name: {item["task_name"]: item for item in records} for name, records in arms.items()}
    paired = []
    wins = losses = ties = 0
    for task_name in sorted(by_arm["A0"]):
        a0, a1 = by_arm["A0"][task_name], by_arm["A1"][task_name]
        delta = int(a1["success"]) - int(a0["success"])
        wins += int(delta > 0); losses += int(delta < 0); ties += int(delta == 0)
        paired.append({"task_name": task_name, "seed": 20260806, "A0": a0, "A1": a1, "success_delta_A1_minus_A0": delta})
    if (wins, losses, ties) != (1, 0, 18):
        raise RuntimeError(f"paired invariant drift: {(wins, losses, ties)}")
    payload = {
        "schema": "a2_a0_a1_paired_reference_v1",
        "seed": 20260806,
        "source_roots": {"A0": str(a0_root), "A1": str(a1_root)},
        "source_aggregate_sha256": {"A0": _hash(a0_root / "aggregate.json"), "A1": _hash(a1_root / "aggregate.json")},
        "summaries": summaries,
        "paired_outcome": {"A1_wins": wins, "A1_losses": losses, "ties": ties},
        "tasks": paired,
        "elapsed_definition": "sum(finished_at-started_at) over the 19 scientifically valid episodes",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output.resolve()), "sha256": _hash(args.output), "summaries": summaries}, indent=2))


if __name__ == "__main__":
    main()
