from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from raven_m.official_qwen_mobile import a1r1_bpr_v2_contract as contract


def test_contract_identities_configs_and_source_closure() -> None:
    assert len(contract.SOURCE_FILES) == len(set(contract.SOURCE_FILES))
    assert all((contract.REPOSITORY_ROOT / name).is_file() for name in contract.SOURCE_FILES)
    assert not any("A1R1_BPR_V2_ZERO_GENERATION_PREFLIGHT.json" in name for name in contract.SOURCE_FILES)
    primary = json.loads(contract.PRIMARY_CONFIG_PATH.read_text(encoding="utf-8"))
    empty = json.loads(contract.EMPTY_CONFIG_PATH.read_text(encoding="utf-8"))
    assert primary["read_enabled"] is True and empty["read_enabled"] is False
    assert primary["mechanism_id"] == empty["mechanism_id"] == contract.MECHANISM_ID
    assert primary["experiment_id"] != empty["experiment_id"]


def test_content_hash_omits_only_content_field() -> None:
    payload = {"schema": "x", "value": 1}
    digest = contract.content_sha256(payload)
    assert digest == contract.content_sha256({**payload, "content_sha256": "wrong"})


def test_preflight_validator_rejects_semantically_contradictory_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    freeze = {"implementation_commit": "a" * 40, "content_sha256": "freeze"}
    replay = {
        "schema": contract.OFFLINE_REPLAY_SCHEMA,
        "status": "PASS",
        "errors": [],
        "generation_calls": 0,
        "R5_status": "PROSPECTIVE_UNKNOWN_PRELIVE",
        "live_generation_authorized": True,
    }
    replay["content_sha256"] = contract.content_sha256(replay)
    freeze_path = tmp_path / "freeze.json"
    replay_path = tmp_path / "replay.json"
    report_path = tmp_path / "preflight.json"
    freeze_path.write_text(json.dumps(freeze), encoding="utf-8")
    replay_path.write_text(json.dumps(replay), encoding="utf-8")
    monkeypatch.setattr(contract, "validate_source_freeze", lambda path: freeze)
    report = {
        "schema": contract.PREFLIGHT_SCHEMA,
        "status": "PASS",
        "mechanism_id": contract.MECHANISM_ID,
        "implementation_commit": freeze["implementation_commit"],
        "source_freeze_content_sha256": "freeze",
        "source_freeze_file_sha256": contract.file_sha256(freeze_path),
        "offline_replay_file_sha256": contract.file_sha256(replay_path),
        "generation_calls": 0,
        "live_generation_authorized": False,
        "errors": [],
    }
    report["content_sha256"] = contract.content_sha256(report)
    report_path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(RuntimeError):
        contract.validate_preflight_report(report_path, source_freeze_path=freeze_path, offline_replay_path=replay_path)


def test_completion_rejects_missing_or_multi_transport() -> None:
    summaries = [
        {
            "task_name": f"t{i}", "evaluator_reward": 1.0,
            "steps": [{"model_call": {"raven_meta": {"transport_attempts": 1}}}],
            "memory_mechanism": {"decision_boundary": {}},
        }
        for i in range(5)
    ]
    assert contract.exact_completion_errors(summaries=summaries, invalid_attempts=[], lifecycle_errors=[], expected_count=5) == []
    summaries[0]["steps"][0]["model_call"]["raven_meta"]["transport_attempts"] = 2
    assert "transport_attempt_not_one" in contract.exact_completion_errors(summaries=summaries, invalid_attempts=[], lifecycle_errors=[], expected_count=5)
