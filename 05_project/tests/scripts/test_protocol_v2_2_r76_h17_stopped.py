from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/protocol_v2_2_r76_h17_candidate_stopped.json"
REPORT_SHA256 = (
    "f88a60ec248dedf83677b054f7fab1ac1a9aa8fee04f38294c8c62a8441d772c"
)
SUITE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r76_candidate_"
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


def test_r76_stop_report_and_suite_lifecycle_are_frozen() -> None:
    report = payload()
    assert report["decision"] == (
        "r76_completed_distinct_identity_bound_field_capture_but_executor_"
        "provenance_and_visual_critic_contracts_rejected_same_episode_"
        "routed_detail_evidence"
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


def test_r76_records_one_method_attempt_and_safe_reset() -> None:
    result = payload()["result"]
    assert result["valid_method_attempt_count"] == 1
    assert result["total_attempt_count"] == 1
    assert result["executed_action_count"] == 16
    assert result["decision_attempt_count"] == 17
    assert result["model_call_count"] == 31
    assert result["reset_audit_passed"] is True
    assert result["blocked_actions_executed_in_application"] is False


def test_r76_startup_is_clean_and_a11y_warnings_do_not_mask_result() -> None:
    report = payload()
    audit = json.loads(
        (SUITE / "startup_environment_audit.json").read_text(
            encoding="utf-8"
        )
    )
    assert audit["failure_count"] == 0
    assert audit["last_status"] == "clean"
    accounting = report["infrastructure_accounting"]
    assert accounting["excluded_episode_attempt_count"] == 0
    assert accounting[
        "accessibility_reconnect_or_retry_warnings_observed"
    ] is True
    assert accounting["warnings_changed_method_result_classification"] is False


def test_r76_confirms_two_distinct_row_identities_and_frames() -> None:
    report = payload()
    guard = episode()["protocol_v2_guard"]
    assert guard["target_row_visit_keys"] == [
        "target-row-y:0.834",
        "target-row-y:0.747",
    ]
    assert guard["target_row_identity_confirmed_visit_keys"] == [
        "target-row-y:0.834",
        "target-row-y:0.747",
    ]
    assert guard["target_row_identity_confirmation_count"] == 2
    assert guard["target_row_identity_mismatch_count"] == 0
    frames = guard["target_row_detail_frames"]
    assert {frame["visit_key"] for frame in frames} == {
        "target-row-y:0.747",
        "target-row-y:0.834",
    }
    assert len({frame["sha256"] for frame in frames}) == 2
    assert all(frame["requested_field_evidence_explicit"] for frame in frames)
    assert report["task_progress"]["captured_detail_frame_count"] == 2


def test_r76_both_nested_returns_are_confirmed() -> None:
    guard = episode()["protocol_v2_guard"]
    assert guard["target_row_return_start_count"] == 2
    assert guard["target_row_return_navigation_count"] == 2
    assert guard["target_row_return_confirmation_count"] == 2
    assert guard["target_row_return_block_count"] == 0


def test_r76_repair_normalization_is_not_falsely_claimed_live() -> None:
    report = payload()
    live = report["r76_mechanism_live_validation"]
    assert live["r75_failure_point_crossed"] is True
    assert live[
        "first_target_row_repair_was_already_within_exact_center_tolerance"
    ] is True
    assert live["r76_normalization_live_exercised"] is False
    for step in episode()["steps"]:
        assert "target_row_repair_normalization" not in (step.get("parse") or {})


def test_r76_terminal_executor_provenance_failure_and_repair_are_exact() -> None:
    report = payload()
    final = episode()["steps"][16]
    calls = [json.loads(call["content"]) for call in final["model_calls"]]
    initial_action = calls[0]["action"]
    repair_action = calls[1]["action"]
    assert initial_action["text"] == "cycling, inline skating"
    assert initial_action["text_origin"] == "verified_memory"
    assert initial_action["source_memory_ids"] == [
        "target-row-y:0.747",
        "target-row-y:0.834",
    ]
    assert repair_action["text"] == "cycling, inline skating"
    assert repair_action["text_origin"] == "current_screen"
    assert repair_action["source_memory_ids"] == []
    assert report["terminal_provenance_bottleneck"][
        "answer_candidate_sha256"
    ] == sha256(
        (
            "dated_row_visual_answer_candidate\0"
            "cycling, inline skating"
        ).encode()
    ).hexdigest()


def test_r76_visual_critic_rejects_supplied_bound_frame_order() -> None:
    report = payload()
    final = episode()["steps"][16]
    calls = final["model_calls"]
    expected_images = report["terminal_provenance_bottleneck"][
        "context_image_sha256_in_model_order"
    ]
    assert calls[1]["image_sha256s"] == expected_images
    critic_calls = calls[2:]
    assert len(critic_calls) == 2
    assert all(call["image_sha256s"] == expected_images for call in critic_calls)
    outputs = [json.loads(call["content"]) for call in critic_calls]
    assert all(output["verdict"] == "reject_completion" for output in outputs)
    assert all(output["memory_ids"] == [] for output in outputs)
    assert report["terminal_provenance_bottleneck"]["visual_critic"][
        "accepted"
    ] is False


def test_r76_answer_and_mutation_never_execute() -> None:
    report = payload()
    progress = report["task_progress"]
    assert progress["answer_executed"] is False
    assert progress["mutation_or_save_action_executed"] is False
    assert episode()["steps"][16]["executed"] is False


def test_r76_stop_report_freezes_selected_raw_artifacts() -> None:
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
        "step_009_before.png": EPISODE_DIR / "step_009_before.png",
        "step_009_field.png": (
            EPISODE_DIR
            / "step_009_before_target_row_y_0_834_requested_field.png"
        ),
        "step_014_before.png": EPISODE_DIR / "step_014_before.png",
        "step_014_field.png": (
            EPISODE_DIR
            / "step_014_before_target_row_y_0_747_requested_field.png"
        ),
        "step_016_before.png": EPISODE_DIR / "step_016_before.png",
    }
    assert set(mapping) == set(report["artifact_sha256"])
    for name, path in mapping.items():
        assert sha256(path.read_bytes()).hexdigest() == (
            report["artifact_sha256"][name]
        )
