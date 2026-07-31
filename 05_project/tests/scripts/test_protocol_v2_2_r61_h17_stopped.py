from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/protocol_v2_2_r61_h17_candidate_stopped.json"
REPORT_SHA256 = (
    "9b3a19d95349f506d78d688a66a6df70812a7f80435673758492ef5e37fff806"
)
SUITE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r61_candidate_"
    "development_smoke_sequence_2"
)
EPISODE_DIR = (
    SUITE
    / "episodes/02_H17_M0_"
    "SportsTrackerActivitiesOnDate_seed20260730"
)


def payload() -> dict:
    assert sha256(REPORT.read_bytes()).hexdigest() == REPORT_SHA256
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_r61_stop_report_and_suite_lifecycle_are_frozen() -> None:
    report = payload()
    assert report["decision"] == (
        "r61_mechanism_validated_but_end_to_end_candidate_failed"
    )
    assert report["development_smoke"] is True
    assert report["formal_scoring"] is False
    assert report["formal_gate_f_authorized"] is False
    assert report["immutability"] == {
        "suite_may_be_resumed": False,
        "suite_may_be_overwritten": False,
        "same_candidate_may_be_retried": False,
        "failure_may_be_relabelled": False,
    }
    summary = json.loads(
        (SUITE / "gate_summary.json").read_text(encoding="utf-8")
    )
    assert summary["development_smoke"] is True
    assert summary["formal_scoring"] is False
    assert summary["stopped_early"] is True
    assert summary["stop_reason"] == (
        "model_output_invalid_after_one_bounded_repair"
    )


def test_r61_valid_method_result_and_infrastructure_accounting() -> None:
    report = payload()
    result = report["result"]
    assert result["attempt_count"] == 2
    assert result["valid_method_attempt"] == 2
    assert result["success"] is False
    assert result["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    assert result["executed_action_count"] == 13
    assert result["model_call_count"] == 31
    assert result["reset_audit_passed"] is True
    infra = report["infrastructure_accounting"]
    assert infra["excluded_attempt_count"] == 1
    assert infra["excluded_attempt"]["code"] == "INFRA_EMULATOR_LOST"
    assert infra["cold_recovery_succeeded"] is True


def test_r61_live_settle_window_caught_both_delayed_transitions() -> None:
    report = payload()
    mechanism = report["r61_mechanism_audit"]
    assert mechanism["status"] == "passed_live_targeted_mechanism"
    assert mechanism["cross_step_reconciliation_count"] == 0
    assert len(mechanism["settled_transitions"]) == 2
    assert all(
        item["post_action_observation_count"] == 2
        and item["first_observation_settle_pending"] is True
        and item["final_observation_semantic_changed"] is True
        for item in mechanism["settled_transitions"]
    )
    episode = json.loads(
        (EPISODE_DIR / "episode.json").read_text(encoding="utf-8")
    )
    assert episode["late_semantic_transition_reconciliation_count"] == 0
    for step in (3, 5):
        observations = episode["steps"][step][
            "after_readiness_observations"
        ]
        assert len(observations) == 2
        assert observations[0]["transition_settle_pending"] is True
        assert observations[-1]["semantic_matches_prior"] is False


def test_r61_downstream_failure_never_scrolled_or_reached_target() -> None:
    report = payload()
    audit = report["downstream_failure_audit"]
    assert audit["target_date_reached"] is False
    assert audit["chronological_list_scrolled"] is False
    assert audit["swipe_action_count"] == 0
    episode = json.loads(
        (EPISODE_DIR / "episode.json").read_text(encoding="utf-8")
    )
    actions = [
        (step.get("decision") or {}).get("action", {})
        for step in episode["steps"]
    ]
    assert not any(action.get("type") == "swipe" for action in actions)
    assert actions[1] == {"type": "tap", "x": 0.84, "y": 0.085}
    assert actions[3] == actions[1]
    assert actions[8]["text"] == "September 24 2023"
    assert episode["steps"][13]["executed"] is False


def test_r61_stop_report_freezes_all_selected_raw_artifacts() -> None:
    report = payload()
    mapping = {
        "gate_summary.json": SUITE / "gate_summary.json",
        "gate_progress.json": SUITE / "gate_progress.json",
        "batch_01_checkpoint.json": SUITE / "batch_01_checkpoint.json",
        "manifest.snapshot.json": SUITE / "manifest.snapshot.json",
        "instances.snapshot.json": SUITE / "instances.snapshot.json",
        "startup_environment_audit.json": (
            SUITE / "startup_environment_audit.json"
        ),
        "episode.json": EPISODE_DIR / "episode.json",
        "events.jsonl": EPISODE_DIR / "events.jsonl",
        "memory_events.jsonl": EPISODE_DIR / "memory_events.jsonl",
        "step_000_after.png": EPISODE_DIR / "step_000_after.png",
        "step_001_after.png": EPISODE_DIR / "step_001_after.png",
        "step_005_after.png": EPISODE_DIR / "step_005_after.png",
        "step_008_after.png": EPISODE_DIR / "step_008_after.png",
        "step_013_before.png": EPISODE_DIR / "step_013_before.png",
        "invalid_attempt_01_episode.json": (
            SUITE
            / "invalid_infrastructure_attempts/02_H17_M0_"
            "SportsTrackerActivitiesOnDate_seed20260730_attempt_01/"
            "episode.json"
        ),
        "recovery_attempt_01_androidworld_smoke.json": (
            SUITE / "recoveries/02_attempt_01/androidworld_smoke.json"
        ),
    }
    assert set(mapping) == set(report["artifact_sha256"])
    for name, path in mapping.items():
        assert sha256(path.read_bytes()).hexdigest() == (
            report["artifact_sha256"][name]
        )
