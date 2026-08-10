import json
from pathlib import Path

import pytest

from raven_m.official_qwen_mobile.a2_suite import episode_reference, load_checkpoint


def _write_episode(suite: Path, task: str, signature: str) -> tuple[dict, Path]:
    directory = suite / "episodes" / f"{task}_episode"
    directory.mkdir(parents=True)
    summary = {
        "task_name": task,
        "seed": 20260806,
        "episode_id": f"{task}_episode",
        "run_metadata": {"run_signature_sha256": signature},
        "error": None,
        "evaluator_reward": 0.0,
        "lifecycle_errors": [],
    }
    (directory / "episode.json").write_text(json.dumps(summary), encoding="utf-8")
    return summary, directory


def test_checkpoint_reloads_hashed_references_and_reports_orphan(tmp_path: Path) -> None:
    signature = "s" * 64
    summary, directory = _write_episode(tmp_path, "H01", signature)
    entry = episode_reference(suite_dir=tmp_path, episode_dir=directory, summary=summary, run_signature_sha256=signature)
    (tmp_path / "episodes" / "orphan").mkdir()
    (tmp_path / "checkpoint.json").write_text(json.dumps({"status": "running", "valid_entries": [entry], "invalid_attempts": []}), encoding="utf-8")
    summaries, entries, invalid, orphans = load_checkpoint(suite_dir=tmp_path, expected_keys=[("H01", 20260806), ("H02", 20260806)], run_signature_sha256=signature)
    assert summaries == [summary]
    assert entries == [entry]
    assert invalid == []
    assert orphans == ["orphan"]


def test_checkpoint_rejects_corrupt_episode(tmp_path: Path) -> None:
    signature = "s" * 64
    summary, directory = _write_episode(tmp_path, "H01", signature)
    entry = episode_reference(suite_dir=tmp_path, episode_dir=directory, summary=summary, run_signature_sha256=signature)
    (directory / "episode.json").write_text("{}", encoding="utf-8")
    (tmp_path / "checkpoint.json").write_text(json.dumps({"status": "running", "valid_entries": [entry]}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="missing or corrupt"):
        load_checkpoint(suite_dir=tmp_path, expected_keys=[("H01", 20260806)], run_signature_sha256=signature)
