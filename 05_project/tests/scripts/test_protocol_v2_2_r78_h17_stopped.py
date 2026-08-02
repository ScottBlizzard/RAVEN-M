from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/protocol_v2_2_r78_h17_candidate_stopped.json"
REPORT_SHA256 = (
    "66a623b81724d5c8265257a83c5ab9c04fbf169dae4a8e32fa0313b2864c02f2"
)
SUITE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r78_candidate_"
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


def test_r78_stop_report_separates_two_failures_from_infrastructure() -> None:
    report = payload()
    assert report["decision"] == (
        "r78_terminal_projection_not_reached_and_protocol_stopped_on_"
        "ambiguous_target_row_repair_plus_repair_context_cap"
    )
    assert report["formal_scoring"] is False
    assert report["formal_gate_f_authorized"] is False
    assert not any(report["immutability"].values())
    root = report["root_cause_separation"]
    assert "between two rows" in root["primary_execution_stop"]
    assert "8904" in root["independent_protocol_failure"]
    assert "never entered" in root["not_a_terminal_projection_failure"]
    assert "all passed" in root["not_an_infrastructure_failure"]


def test_r78_records_one_failed_method_attempt_and_safe_reset() -> None:
    result = payload()["result"]
    assert result["valid_method_attempt_count"] == 1
    assert result["total_attempt_count"] == 1
    assert result["success"] is False
    assert result["evaluator_reward"] == 0.0
    assert result["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    assert result["decision_attempt_count"] == 8
    assert result["valid_decision_count"] == 7
    assert result["executed_action_count"] == 7
    assert result["model_call_count"] == 13
    assert result["answer_action_count"] == 0
    assert result["reset_audit_passed"] is True
    assert result["blocked_actions_executed_in_application"] is False
    assert result["mutation_or_save_action_executed"] is False


def test_r78_reached_two_rows_but_no_row_action_crossed_guard() -> None:
    report = payload()
    trace = report["live_trace"]
    assert trace["terminal_evidence_projection_reached"] is False
    assert trace["target_date_reached"] is True
    assert trace["target_row_count"] == 2
    assert trace["target_row_centers"] == [0.747292, 0.834375]
    assert trace["target_row_visit_count"] == 0
    assert trace["target_row_detail_frame_count"] == 0
    assert trace["target_date_visible_swipe_block_count"] == 1
    assert trace["blocked_swipe_executed_in_application"] is False
    assert trace["repair_step_7_action"] == {
        "type": "tap",
        "x": 0.5,
        "y": 0.785,
    }
    guard = episode()["protocol_v2_guard"]
    assert guard["target_date_row_count"] == 2
    assert guard["target_row_visit_keys"] == []
    assert guard["target_row_detail_frames"] == []
    assert guard["target_date_visible_swipe_block_count"] == 1


def test_r78_context_cap_failure_is_earlier_generic_repair() -> None:
    cap = payload()["context_cap_bottleneck"]
    assert cap["configured_prompt_token_cap"] == 8192
    assert cap["maximum_observed_prompt_tokens"] == 8904
    assert cap["overage_tokens"] == 712
    assert cap["context_cap_error_count"] == 1
    assert cap["offending_step"] == 3
    assert cap["offending_role"] == "executor_repair"
    assert cap["offending_original_user_prompt_char_count"] == 9776
    assert cap["offending_repair_user_prompt_char_count"] == 15014
    assert cap["initial_call_prompt_tokens"] == 7746
    assert cap["repair_call_prompt_tokens"] == 8904
    progress = json.loads(
        (SUITE / "gate_progress.json").read_text(encoding="utf-8")
    )
    assert progress["context_cap_error_count"] == 1
    assert progress["reset_error_count"] == 0
    assert progress["provenance_audit_error_count"] == 0


def test_r78_summary_and_reset_match_frozen_report() -> None:
    summary = json.loads(
        (SUITE / "gate_summary.json").read_text(encoding="utf-8")
    )
    assert summary["development_smoke"] is True
    assert summary["success_count"] == 0
    assert summary["stopped_early"] is True
    assert summary["stop_reason"] == (
        "model_output_invalid_after_one_bounded_repair"
    )
    assert summary["gate_passed"] is False
    result = summary["results"][0]
    assert result["reset_audit"] == {
        "passed": True,
        "post_episode_reset_event_count": 1,
        "task_torn_down_event_count": 1,
    }


def test_r78_stop_report_freezes_selected_raw_artifacts() -> None:
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
        "step_003_after.png": EPISODE_DIR / "step_003_after.png",
        "step_007_before.png": EPISODE_DIR / "step_007_before.png",
    }
    assert set(mapping) == set(report["artifact_sha256"])
    for name, path in mapping.items():
        assert sha256(path.read_bytes()).hexdigest() == (
            report["artifact_sha256"][name]
        )
