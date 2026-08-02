from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/protocol_v2_2_r77_h17_candidate_stopped.json"
REPORT_SHA256 = (
    "c989588c4655ee4912fba95991142cc4a87d3f9051c9bf7e967f6e416d6ae872"
)
SUITE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r77_candidate_"
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


def test_r77_stop_report_separates_task_success_from_protocol_stop() -> None:
    report = payload()
    assert report["decision"] == (
        "r77_solved_h17_and_validated_same_episode_routed_evidence_but_"
        "protocol_stopped_on_executor_context_cap"
    )
    assert report["formal_scoring"] is False
    assert report["formal_gate_f_authorized"] is False
    assert not any(report["immutability"].values())
    summary = json.loads(
        (SUITE / "gate_summary.json").read_text(encoding="utf-8")
    )
    assert summary["development_smoke"] is True
    assert summary["success_count"] == 1
    assert summary["stopped_early"] is True
    assert summary["stop_reason"] == "context_cap_exceeded"
    assert summary["gate_passed"] is False


def test_r77_records_one_successful_method_attempt_and_safe_reset() -> None:
    result = payload()["result"]
    assert result["valid_method_attempt_count"] == 1
    assert result["total_attempt_count"] == 1
    assert result["success"] is True
    assert result["evaluator_reward"] == 1.0
    assert result["termination_reason"] == "model_answer"
    assert result["executed_action_count"] == 13
    assert result["model_call_count"] == 23
    assert result["answer_action_count"] == 1
    assert result["reset_audit_passed"] is True
    assert result["blocked_actions_executed_in_application"] is False
    assert result["mutation_or_save_action_executed"] is False


def test_r77_startup_failure_recovers_before_the_only_method_attempt() -> None:
    report = payload()
    audit = json.loads(
        (SUITE / "startup_environment_audit.json").read_text(
            encoding="utf-8"
        )
    )
    assert audit["failure_count"] == 1
    assert audit["recovery_success_count"] == 1
    assert audit["last_status"] == "recovered"
    accounting = report["infrastructure_accounting"]
    assert accounting["excluded_episode_attempt_count"] == 0
    assert accounting["method_attempt_started_after_recovery"] is True
    assert accounting["method_attempt_count"] == 1
    assert accounting["reset_audit_passed"] is True
    assert accounting["startup_errors_were_not_teardown_errors"] is True


def test_r77_confirms_two_distinct_identities_frames_and_returns() -> None:
    guard = episode()["protocol_v2_guard"]
    assert guard["target_row_visit_keys"] == [
        "target-row-y:0.747",
        "target-row-y:0.834",
    ]
    assert guard["target_row_identity_confirmed_visit_keys"] == [
        "target-row-y:0.747",
        "target-row-y:0.834",
    ]
    assert guard["target_row_identity_confirmation_count"] == 2
    assert guard["target_row_identity_mismatch_count"] == 0
    assert [frame["sha256"] for frame in guard["target_row_detail_frames"]] == [
        "0883f3b6359871bf13740050bf0321a48cc0f6901d5d067da0cbf7640cd7a088",
        "9c0242a6473e07535e56f824e76db53d1bb77201d4c7c47aa72f6a690bf82768",
    ]
    assert all(
        frame["requested_field_evidence_explicit"]
        for frame in guard["target_row_detail_frames"]
    )
    assert guard["target_row_return_start_count"] == 2
    assert guard["target_row_return_navigation_count"] == 2
    assert guard["target_row_return_confirmation_count"] == 2
    assert guard["target_row_return_block_count"] == 0


def test_r77_terminal_executor_uses_exact_non_memory_provenance() -> None:
    report = payload()
    final = episode()["steps"][12]
    executor = json.loads(final["model_calls"][0]["content"])
    action = executor["action"]
    assert action["text"] == "cycling, inline skating"
    assert action["text_origin"] == "current_screen"
    assert action["source_memory_ids"] == []
    assert executor["memory_citations"] == []
    assert executor["completion_evidence"][0]["evidence"] == (
        "direct_screen"
    )
    assert executor["completion_evidence"][0]["memory_ids"] == []
    assert "DATED_TARGET_ROUTED_VISUAL_EVIDENCE_AUTHORITY" in (
        final["user_prompt"]
    )
    mechanism = report["r77_mechanism_live_validation"]
    assert mechanism["r76_failure_point_crossed"] is True
    assert mechanism["terminal_executor_received_routed_evidence_authority"]
    assert mechanism["answer_text_sha256"] == sha256(
        action["text"].encode()
    ).hexdigest()


def test_r77_visual_critic_accepts_exact_ordered_same_episode_frames() -> None:
    report = payload()
    final = episode()["steps"][12]
    expected_images = report["r77_mechanism_live_validation"][
        "context_image_sha256_in_model_order"
    ]
    assert final["model_calls"][0]["image_sha256s"] == expected_images
    assert final["model_calls"][1]["image_sha256s"] == expected_images
    critic = json.loads(final["model_calls"][1]["content"])
    assert critic["verdict"] == "proceed"
    assert critic["memory_ids"] == []
    parse = final["parse"]["dated_visual_answer_assessment"]
    assert parse["eligible"] is True
    assert parse["adjudicated"] is True
    assert parse["accepted"] is True
    assert parse["target_row_count"] == 2
    assert parse["detail_frame_count"] == 2
    assert episode()["protocol_v2_guard"][
        "target_row_visual_answer_accept_count"
    ] == 1


def test_r77_answer_executes_and_matches_evaluator() -> None:
    final = episode()["steps"][12]
    assert final["executed"] is True
    assert final["decision"]["status"] == "done"
    assert final["answer_audit"]["interaction_cache_populated"] is True
    assert final["answer_audit"]["interaction_cache_matches_answer"] is True
    assert episode()["success"] is True
    assert episode()["evaluator_reward"] == 1.0


def test_r77_only_remaining_protocol_failure_is_executor_context_cap() -> None:
    report = payload()
    cap = report["context_cap_bottleneck"]
    assert cap["configured_prompt_token_cap"] == 8192
    assert cap["maximum_observed_prompt_tokens"] == 8982
    assert cap["overage_tokens"] == 790
    assert cap["context_cap_error_count"] == 1
    assert cap["offending_step"] == 12
    assert cap["offending_role"] == "executor"
    assert cap["offending_context_image_count"] == 3
    assert cap["visual_critic_prompt_tokens"] == 5993
    progress = json.loads(
        (SUITE / "gate_progress.json").read_text(encoding="utf-8")
    )
    assert progress["context_cap_error_count"] == 1
    assert progress["provenance_audit_error_count"] == 0
    assert progress["reset_error_count"] == 0
    assert progress["delayed_fact_completion_deadlock_count"] == 0


def test_r77_stop_report_freezes_selected_raw_artifacts() -> None:
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
        "step_005_before.png": EPISODE_DIR / "step_005_before.png",
        "step_005_field.png": (
            EPISODE_DIR
            / "step_005_before_target_row_y_0_747_requested_field.png"
        ),
        "step_010_before.png": EPISODE_DIR / "step_010_before.png",
        "step_010_field.png": (
            EPISODE_DIR
            / "step_010_before_target_row_y_0_834_requested_field.png"
        ),
        "step_012_before.png": EPISODE_DIR / "step_012_before.png",
        "step_012_after.png": EPISODE_DIR / "step_012_after.png",
    }
    assert set(mapping) == set(report["artifact_sha256"])
    for name, path in mapping.items():
        assert sha256(path.read_bytes()).hexdigest() == (
            report["artifact_sha256"][name]
        )
