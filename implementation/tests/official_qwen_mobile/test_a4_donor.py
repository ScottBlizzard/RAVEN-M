from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from raven_m.official_qwen_mobile.a4_donor import (
    audit_manifest,
    validate_frozen_bank,
    write_audit_and_bank,
)


def _dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _fixture(root: Path, *, donor_task: str = "EasyDonor", reward: float = 1.0) -> Path:
    hard_path = root / "hard.json"
    _dump(hard_path, {"instances": [{"task_class": "ScoredHard"}]})
    episode_id = "donor_episode"
    episode_path = root / "episode.json"
    _dump(
        episode_path,
        {
            "episode_id": episode_id,
            "seed": 7,
            "evaluator_reward": reward,
            "error": None,
            "failure_code": None,
            "steps": [
                {
                    "decision": {
                        "action": {"type": "type_text", "text": "SECRET", "x": 0.3, "y": 0.4},
                        "decision_summary": "Enter SECRET in the field.",
                    }
                },
                {
                    "decision": {
                        "action": {"type": "tap", "x": 0.7, "y": 0.1},
                        "decision_summary": "Save the record.",
                    }
                },
            ],
        },
    )
    events_path = root / "events.jsonl"
    events = [
        {"event": "evaluator_result", "reward": reward, "visible_to_agent": False},
        {"event": "episode_complete", "success": reward == 1.0},
    ]
    events_path.write_text("".join(json.dumps(item) + "\n" for item in events), encoding="utf-8")
    summary_path = root / "summary.json"
    _dump(
        summary_path,
        {
            "episodes": [
                {
                    "episode_id": episode_id,
                    "task_name": donor_task,
                    "seed": 7,
                    "success": reward == 1.0,
                }
            ]
        },
    )
    suite_manifest_path = root / "suite_manifest.json"
    _dump(
        suite_manifest_path,
        {"tasks": [{"name": donor_task, "difficulty": "easy", "app": "Donor App"}]},
    )
    manifest_path = root / "donor_manifest.json"
    _dump(
        manifest_path,
        {
            "manifest_id": "fixture",
            "scored_hard_manifest": {"path": "hard.json", "sha256": _sha(hard_path)},
            "required_coverage_families": ["fixture"],
            "donors": [
                {
                    "donor_id": "donor_1",
                    "task_class": donor_task,
                    "difficulty": "easy",
                    "app": "Donor App",
                    "seed": 7,
                    "coverage_family": "fixture",
                    "keywords": ["record", "save"],
                    "episode_path": "episode.json",
                    "episode_path_sha256": _sha(episode_path),
                    "events_path": "events.jsonl",
                    "events_path_sha256": _sha(events_path),
                    "suite_summary_path": "summary.json",
                    "suite_summary_path_sha256": _sha(summary_path),
                    "suite_manifest_path": "suite_manifest.json",
                    "suite_manifest_path_sha256": _sha(suite_manifest_path),
                }
            ],
        },
    )
    return manifest_path


def test_ready_bank_is_canonical_value_free_and_validates(tmp_path: Path) -> None:
    manifest = _fixture(tmp_path)
    audit = tmp_path / "audit.json"
    bank = tmp_path / "bank.json"
    report = write_audit_and_bank(
        manifest, repository_root=tmp_path, audit_path=audit, bank_path=bank
    )
    payload = json.loads(bank.read_text(encoding="utf-8"))
    assert report["status"] == "ready"
    assert set(payload) == {
        "schema", "status", "generation_calls", "scored_hard_inputs_used",
        "workflows", "source_lock_sha256", "bank_sha256",
    }
    assert payload["generation_calls"] == 0
    assert payload["scored_hard_inputs_used"] is False
    assert payload["workflows"][0]["donor_split"] == "Easy"
    assert "SECRET" not in payload["workflows"][0]["workflow"]
    assert "0.3" not in payload["workflows"][0]["workflow"]
    validate_frozen_bank(
        manifest, repository_root=tmp_path, audit_path=audit, bank_path=bank
    )


def test_scored_hard_task_is_rejected(tmp_path: Path) -> None:
    manifest = _fixture(tmp_path, donor_task="ScoredHard")
    report = audit_manifest(manifest, repository_root=tmp_path)
    assert report["status"] == "not_ready"
    assert "donor_1:task_class_present_in_scored_hard" in report["errors"]
    assert report["workflows"] == []


def test_failed_or_missing_required_donor_never_emits_bank(tmp_path: Path) -> None:
    manifest = _fixture(tmp_path, reward=0.0)
    audit = tmp_path / "audit.json"
    bank = tmp_path / "bank.json"
    report = write_audit_and_bank(
        manifest, repository_root=tmp_path, audit_path=audit, bank_path=bank
    )
    assert report["status"] == "not_ready"
    assert not bank.exists()
    assert any("episode_reward_is_one" in error for error in report["errors"])
    with pytest.raises(RuntimeError, match="not ready"):
        validate_frozen_bank(
            manifest, repository_root=tmp_path, audit_path=audit, bank_path=bank
        )
