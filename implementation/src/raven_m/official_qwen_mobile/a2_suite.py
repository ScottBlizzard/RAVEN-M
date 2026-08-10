"""Fail-closed immutable checkpoint helpers for scored A2-v1r1 suites."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def episode_infrastructure_valid(summary: dict[str, Any]) -> bool:
    return (
        summary.get("error") is None
        and summary.get("evaluator_reward") is not None
        and not summary.get("lifecycle_errors")
    )


def episode_reference(
    *, suite_dir: Path, episode_dir: Path, summary: dict[str, Any], run_signature_sha256: str
) -> dict[str, Any]:
    episode_path = episode_dir / "episode.json"
    return {
        "task_name": str(summary["task_name"]),
        "seed": int(summary["seed"]),
        "episode_id": str(summary["episode_id"]),
        "episode_json_relative_path": str(episode_path.relative_to(suite_dir)).replace("\\", "/"),
        "episode_json_sha256": file_sha256(episode_path),
        "run_signature_sha256": run_signature_sha256,
    }


def load_checkpoint(
    *, suite_dir: Path, expected_keys: list[tuple[str, int]], run_signature_sha256: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    checkpoint = json.loads((suite_dir / "checkpoint.json").read_text(encoding="utf-8"))
    if checkpoint.get("status") not in {
        "running", "stopped_invalid_episode", "stopped_memory_activation_failure"
    }:
        raise RuntimeError(f"A2 checkpoint status is not resumable: {checkpoint.get('status')!r}")
    entries = list(checkpoint.get("valid_entries") or [])
    if checkpoint.get("valid_summaries"):
        raise RuntimeError("A2 checkpoint embeds mutable summaries instead of immutable references")
    expected_set = set(expected_keys)
    seen: set[tuple[str, int]] = set()
    summaries: list[dict[str, Any]] = []
    referenced_dirs: set[str] = set()
    for entry in entries:
        key = (str(entry.get("task_name")), int(entry.get("seed", -1)))
        if key not in expected_set or key in seen:
            raise RuntimeError(f"A2 checkpoint contains foreign or duplicate key: {key!r}")
        if entry.get("run_signature_sha256") != run_signature_sha256:
            raise RuntimeError("A2 checkpoint entry run signature drift")
        relative = Path(str(entry.get("episode_json_relative_path") or ""))
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("A2 checkpoint episode path escapes suite")
        episode_path = suite_dir / relative
        if not episode_path.is_file() or file_sha256(episode_path) != entry.get("episode_json_sha256"):
            raise RuntimeError(f"A2 checkpoint episode is missing or corrupt: {relative}")
        summary = json.loads(episode_path.read_text(encoding="utf-8"))
        if (
            str(summary.get("task_name")) != key[0]
            or int(summary.get("seed", -1)) != key[1]
            or str(summary.get("episode_id")) != str(entry.get("episode_id"))
            or (summary.get("run_metadata") or {}).get("run_signature_sha256") != run_signature_sha256
            or not episode_infrastructure_valid(summary)
        ):
            raise RuntimeError(f"A2 checkpoint episode semantic validation failed: {relative}")
        seen.add(key)
        summaries.append(summary)
        referenced_dirs.add(relative.parts[1] if len(relative.parts) > 1 else "")
    order = {key: index for index, key in enumerate(expected_keys)}
    positions = [order[(str(item["task_name"]), int(item["seed"]))] for item in summaries]
    if positions != sorted(positions):
        raise RuntimeError("A2 checkpoint entries are not in frozen manifest order")
    invalid_attempts = list(checkpoint.get("invalid_attempts") or [])
    recorded_invalid_dirs = {
        str(item.get("episode_id")) for item in invalid_attempts if item.get("episode_id")
    }
    episodes_root = suite_dir / "episodes"
    orphans = sorted(
        item.name for item in episodes_root.iterdir()
        if item.is_dir()
        and item.name not in referenced_dirs
        and item.name not in recorded_invalid_dirs
    ) if episodes_root.is_dir() else []
    return summaries, entries, invalid_attempts, orphans
