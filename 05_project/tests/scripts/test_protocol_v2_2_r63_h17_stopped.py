from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/protocol_v2_2_r63_h17_candidate_stopped.json"
REPORT_SHA256 = (
    "2302fd28b3fe96816c0acedf42537bf9f0187ef79db825d424f5e97bc6e12cde"
)
SUITE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r63_candidate_"
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


def test_r63_stop_report_and_suite_lifecycle_are_frozen() -> None:
    report = payload()
    assert report["decision"] == (
        "r63_guard_blocked_blind_scroll_but_"
        "a11y_clickability_overconstrained_repair"
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
    assert summary["gate_passed"] is False


def test_r63_valid_method_result_and_infrastructure_accounting() -> None:
    report = payload()
    result = report["result"]
    assert result["attempt_count"] == 2
    assert result["valid_method_attempt"] == 2
    assert result["success"] is False
    assert result["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    assert result["executed_action_count"] == 3
    assert result["model_call_count"] == 6
    assert result["answer_action_count"] == 0
    assert result["reset_audit_passed"] is True
    infra = report["infrastructure_accounting"]
    assert infra["excluded_attempt_count"] == 1
    assert infra["excluded_attempt"]["code"] == "INFRA_EMULATOR_LOST"
    assert infra["cold_recovery_succeeded"] is True


def test_r63_blocks_target_visible_swipe_before_execution() -> None:
    report = payload()
    mechanism = report["r63_mechanism_audit"]
    assert mechanism["target_date_reached"] is True
    assert mechanism["target_date_row_count"] == 2
    assert mechanism["target_date_visible_swipe_block_count"] == 1
    assert mechanism["blocked_action"]["type"] == "swipe"
    assert mechanism["blocked_action_executed"] is False
    assert mechanism["answer_submitted"] is False
    episode = json.loads(
        (EPISODE_DIR / "episode.json").read_text(encoding="utf-8")
    )
    executed = [
        step["decision"]["action"]
        for step in episode["steps"]
        if step["executed"]
    ]
    assert [action["type"] for action in executed] == [
        "open_app",
        "swipe",
        "swipe",
    ]
    assert episode["steps"][-1]["executed"] is False


def test_r63_repair_is_geometric_target_tap_but_not_a11y_clickable() -> None:
    audit = payload()["repair_failure_audit"]
    assert audit["repair_output"]["action"] == {
        "type": "tap",
        "x": 0.5,
        "y": 0.775,
    }
    assert audit["pure_tap_contract_satisfied"] is True
    assert audit["target_row_geometry_satisfied"] is True
    assert audit["normalized_vertical_distance"] == 0.027708
    assert audit["accessibility_clickable_target_hit"] is False
    assert "accessibility element" in audit["primary_failure"]


def test_r63_stop_report_freezes_all_selected_raw_artifacts() -> None:
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
        "step_002_after.png": EPISODE_DIR / "step_002_after.png",
        "step_003_before.png": EPISODE_DIR / "step_003_before.png",
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
