from __future__ import annotations

import json
from pathlib import Path

from implementation.scripts import materialize_sys_r2_lrer_v2_fixture as materializer
from implementation.scripts.replay_sys_r2_lrer_v2 import OUTPUT_PATH, replay
from raven_m.official_qwen_mobile import sys_r2_lrer_v2_contract as contract


def test_materialized_fixture_is_fresh_clone_reconstructible_and_exact(
    monkeypatch,
) -> None:
    def forbidden_raw_episode(*_args, **_kwargs):
        raise AssertionError("materialization must not read a gitignored run")

    monkeypatch.setattr(materializer, "snapshot_from_episode", forbidden_raw_episode)
    expected = json.loads(materializer.OUTPUT_PATH.read_text(encoding="utf-8"))
    assert materializer.materialize() == expected
    assert expected["generation_calls"] == 0
    assert expected["development_audit"] == {
        "first_value_step": 15,
        "all_value_steps": [15, 16, 17, 18, 19],
        "first_result_action_step": 21,
        "first_result_remaining_slots": 0,
        "lrer_eligible_count": 0,
        "lrer_blocked_count": 0,
        "cross_activity_stale_capture_steps": [3, 7],
        "settle_policy_is_counterfactual": True,
    }


def test_offline_replay_recomputes_exact_committed_pass() -> None:
    expected = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    observed = replay()
    assert observed == expected
    assert observed["status"] == "PASS"
    assert observed["errors"] == []
    assert contract._replay_valid(observed)


def test_replay_and_contract_reject_development_marker_drift(tmp_path: Path) -> None:
    fixture = json.loads(materializer.OUTPUT_PATH.read_text(encoding="utf-8"))
    fixture["development_audit"]["cross_activity_stale_capture_steps"] = [3]
    fixture["content_sha256"] = materializer.content_sha256(fixture)
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")
    observed = replay(path)
    assert observed["status"] == "FAIL"
    assert "sealed_live_development_audit_drift" in observed["errors"]
    assert not contract._replay_valid(observed)
