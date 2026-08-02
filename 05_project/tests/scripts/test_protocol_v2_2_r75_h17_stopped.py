from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/protocol_v2_2_r75_h17_candidate_stopped.json"
REPORT_SHA256 = (
    "ca688dfa080968300d2aff9b7d4361ab8634de7589ee88da87f47fb108d39c01"
)
SUITE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r75_candidate_"
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


def episode() -> dict:
    return json.loads(
        (EPISODE_DIR / "episode.json").read_text(encoding="utf-8")
    )


def test_r75_stop_report_and_suite_lifecycle_are_frozen() -> None:
    report = payload()
    assert report["decision"] == (
        "r75_blocked_imprecise_target_row_repair_before_execution_but_"
        "generic_row_tap_contract_could_not_route_the_single_repair_to_"
        "an_exact_center"
    )
    assert report["formal_scoring"] is False
    assert report["formal_gate_f_authorized"] is False
    assert not any(report["immutability"].values())
    summary = json.loads(
        (SUITE / "gate_summary.json").read_text(encoding="utf-8")
    )
    assert summary["development_smoke"] is True
    assert summary["stopped_early"] is True
    assert summary["stop_reason"] == (
        "model_output_invalid_after_one_bounded_repair"
    )


def test_r75_records_one_valid_method_attempt_and_safe_reset() -> None:
    report = payload()
    result = report["result"]
    assert result["valid_method_attempt_count"] == 1
    assert result["total_episode_attempt_count"] == 1
    assert result["executed_action_count"] == 3
    assert result["decision_attempt_count"] == 4
    assert result["model_call_count"] == 6
    assert result["reset_audit_passed"] is True
    assert result["blocked_actions_executed_in_application"] is False


def test_r75_startup_infrastructure_failure_recovered_before_episode() -> None:
    report = payload()
    accounting = report["infrastructure_accounting"]
    audit = json.loads(
        (SUITE / "startup_environment_audit.json").read_text(
            encoding="utf-8"
        )
    )
    assert accounting["startup_environment_failure_count"] == 1
    assert accounting["startup_environment_status"] == "recovered"
    assert audit["failure_count"] == 1
    assert audit["recovery_success_count"] == 1
    assert audit["last_status"] == "recovered"
    assert episode()["started_at"] > audit["events"][-1]["checked_at"]


def test_r75_reaches_two_identified_target_rows_before_failure() -> None:
    report = payload()
    progress = report["task_progress"]
    guard = episode()["protocol_v2_guard"]
    assert progress["target_date_reached"] is True
    assert progress["target_row_centers"] == [0.747292, 0.834375]
    assert progress["target_row_identity_labels_available"] is True
    assert guard["target_date_row_count"] == 2
    assert guard["target_row_identity_unavailable_block_count"] == 0


def test_r75_exactly_replays_blocked_midpoint_repair() -> None:
    report = payload()
    bottleneck = report["repair_contract_bottleneck"]
    final_step = episode()["steps"][3]
    calls = [json.loads(item["content"]) for item in final_step["model_calls"]]
    assert calls[0]["action"] == bottleneck["initial_model_action"]
    assert calls[1]["action"] == bottleneck["repair_model_action"]
    assert bottleneck["repair_model_action"] == {
        "type": "tap",
        "x": 0.5,
        "y": 0.775,
    }
    assert bottleneck["repair_nearest_row_center"] == 0.747292
    assert bottleneck["repair_y_offset"] == 0.027708


def test_r75_blocks_approximate_repair_before_application_execution() -> None:
    report = payload()
    current = episode()
    assert current["executed_action_count"] == 3
    assert current["steps"][3]["executed"] is False
    assert current["steps"][3]["decision"] is None
    error = current["model_output_error"]
    assert error["initial_validation_error"].startswith(
        "TARGET_DATE_VISIBLE_GUARD:"
    )
    assert error["repair_validation_error"].startswith(
        "REPAIR_CONTRACT_GUARD:"
    )
    live = report["r75_mechanism_live_validation"]
    assert live["imprecise_target_row_action_executed"] is False
    assert live["coordinate_guard_preserved_safety"] is True


def test_r75_identity_and_answer_safety_are_not_claimed_unreached() -> None:
    report = payload()
    live = report["r75_mechanism_live_validation"]
    assert live["identity_guard_reached"] is False
    assert live["identity_guard_live_validated"] is False
    assert live["full_r75_mechanism_live_validated"] is False
    progress = report["task_progress"]
    assert progress["ledger_visited_row_count"] == 0
    assert progress["ledger_captured_detail_frame_count"] == 0
    assert progress["answer_executed"] is False
    assert progress["mutation_or_save_action_executed"] is False


def test_r75_stop_report_freezes_selected_raw_artifacts() -> None:
    report = payload()
    mapping = {
        "gate_summary.json": SUITE / "gate_summary.json",
        "gate_progress.json": SUITE / "gate_progress.json",
        "manifest.snapshot.json": SUITE / "manifest.snapshot.json",
        "instances.snapshot.json": SUITE / "instances.snapshot.json",
        "startup_environment_audit.json": (
            SUITE / "startup_environment_audit.json"
        ),
        "episode.json": EPISODE_DIR / "episode.json",
        "events.jsonl": EPISODE_DIR / "events.jsonl",
        "memory_events.jsonl": EPISODE_DIR / "memory_events.jsonl",
        "step_003_before.png": EPISODE_DIR / "step_003_before.png",
    }
    assert set(mapping) == set(report["artifact_sha256"])
    for name, path in mapping.items():
        assert sha256(path.read_bytes()).hexdigest() == (
            report["artifact_sha256"][name]
        )
