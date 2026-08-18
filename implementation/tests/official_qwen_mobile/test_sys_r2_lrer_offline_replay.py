from __future__ import annotations

import json

import pytest

from implementation.scripts import materialize_sys_r2_lrer_fixture as materializer
from implementation.scripts.materialize_sys_r2_lrer_fixture import (
    OUTPUT_PATH as FIXTURE_PATH,
    SNAPSHOT_SCHEMA,
    SNAPSHOT_KEYS,
    SNAPSHOT_STEP_KEYS,
    SOURCE_SNAPSHOT_DIR,
    canonical_sha256,
    materialize,
)
from implementation.scripts.replay_sys_r2_lrer import OUTPUT_PATH, replay


def test_materialized_fixture_is_exactly_reproducible_and_zero_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raw_runs_are_unavailable(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("default materialization attempted to access gitignored runs")

    monkeypatch.setattr(materializer, "_episode_path", raw_runs_are_unavailable)
    committed = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    rebuilt = materialize()
    assert rebuilt == committed
    assert committed["schema"] == "sys_r2_lrer_replay_fixture_v1"
    assert committed["generation_calls"] == 0
    assert committed["content_sha256"] == canonical_sha256(committed)
    assert len(committed["r2_episodes"]) == 7
    snapshots = sorted(SOURCE_SNAPSHOT_DIR.glob("*.json"))
    assert len(snapshots) == 8
    for path in snapshots:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        assert set(snapshot) == SNAPSHOT_KEYS
        assert snapshot["schema"] == SNAPSHOT_SCHEMA
        assert snapshot["content_sha256"] == canonical_sha256(snapshot)
        assert all(set(step) == SNAPSHOT_STEP_KEYS for step in snapshot["steps"])


def test_replay_is_exactly_reproducible_and_passes_frozen_expectations() -> None:
    committed = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    rebuilt = replay(FIXTURE_PATH)
    assert rebuilt == committed
    assert committed["status"] == "PASS"
    assert committed["errors"] == []
    assert committed["generation_calls"] == 0
    assert committed["totals"] == {
        "generation_calls": 0,
        "r15_trigger_count": 1,
        "r2_episode_count": 7,
        "r2_six_success_trigger_count": 0,
        "r2_trigger_count": 1,
    }


def test_only_r2_browser_step18_triggers_and_six_successes_are_silent() -> None:
    report = replay(FIXTURE_PATH)
    browser = report["r2_browser"]
    assert browser["task_name"] == "BrowserMultiply"
    assert browser["opportunity"]["triggered"] is True
    assert browser["opportunity"]["trigger_step"] == 18
    assert browser["opportunity"]["deferred_proposal"]["action_family"] == "type_text"
    assert browser["opportunity"]["deferred_proposal"]["response_sha256"] not in browser["opportunity"]["source_response_sha256s"]
    assert all(
        row["opportunity"]["triggered"] is False
        for row in report["r2_six_successes"]
    )


def test_r15_prior_eight_raw_actions_cover_values_and_exclude_proposal() -> None:
    report = replay(FIXTURE_PATH)
    r15 = report["r15_browser"]
    opportunity = r15["opportunity"]
    assert opportunity["triggered"] is True
    assert opportunity["trigger_step"] == 18
    assert opportunity["source_window_count"] == 8
    assert opportunity["source_steps"] == list(range(10, 18))
    assert opportunity["deferred_proposal_excluded"] is True
    assert opportunity["deferred_proposal"]["response_sha256"] not in opportunity["source_response_sha256s"]
    assert opportunity["deferred_proposal"]["action_summary"] not in opportunity["prepared_injection"]["text"]
    assert opportunity["prepared_injection"]["source_steps"] == list(range(10, 18))
    assert opportunity["prepared_injection"]["source_response_sha256s"] == opportunity["source_response_sha256s"]
    assert r15["value_coverage"] == {
        "expected_values": ["1", "8", "10", "7", "2"],
        "exact_observation_phrases": [
            "number 1 displayed",
            "number 8 displayed",
            "number 10 displayed",
            "number 7 displayed",
            "number 2 displayed",
        ],
        "found_values": ["1", "8", "10", "7", "2"],
        "all_expected_values_covered": True,
        "rendered_found_values": ["1", "8", "10", "7", "2"],
        "all_expected_values_rendered": True,
    }
