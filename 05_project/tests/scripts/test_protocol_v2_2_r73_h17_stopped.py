from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/protocol_v2_2_r73_h17_candidate_stopped.json"
REPORT_SHA256 = (
    "cfa22bbcdafb400306690fe8b5e3c51b99628c9e88c561b2319d8f335af13ba0"
)
SUITE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r73_candidate_"
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


def steps() -> list[dict]:
    return [
        json.loads(line)
        for line in (EPISODE_DIR / "events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if json.loads(line).get("event") == "step"
    ]


def test_r73_stop_report_and_suite_lifecycle_are_frozen() -> None:
    report = payload()
    assert report["decision"] == (
        "r73_verified_inspection_and_native_popup_succeeded_but_nested_"
        "return_released_row_coordinates_early"
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


def test_r73_separates_one_infrastructure_attempt_from_method() -> None:
    report = payload()
    infra = report["infrastructure_accounting"]
    assert infra["excluded_episode_attempt_count"] == 1
    assert infra["excluded_failure_code"] == "INFRA_EMULATOR_LOST"
    assert infra["excluded_decision_attempt_count"] == 0
    assert infra["excluded_executed_action_count"] == 0
    assert infra["excluded_model_call_count"] == 0
    assert infra["automatic_recovery_commands_passed"] is True
    result = report["result"]
    assert result["valid_method_attempt_count"] == 1
    assert result["recorded_attempt_ordinal"] == 2
    assert result["executed_action_count"] == 8
    assert result["decision_attempt_count"] == 9


def test_r73_live_more_options_bypasses_only_false_generic_critic() -> None:
    report = payload()
    mechanism = report["r73_mechanism_validation"]
    step = steps()[4]
    assert mechanism["r72_failure_point_crossed"] is True
    assert mechanism["r73_fix_live_validated"] is True
    assert step["decision"]["action"] == {
        "type": "tap",
        "x": 0.405,
        "y": 0.925,
    }
    assessment = step["parse"]["requested_field_value_assessment"]
    assert assessment["inspection_control_hit"] is True
    assert assessment["mutation_control_hit"] is False
    assert assessment["requested_field_control_hit"] is False
    assert step["parse"]["action_adjudications"] == []
    assert step["executed"] is True


def test_r73_live_native_popup_routes_edit_but_not_delete() -> None:
    report = payload()
    mechanism = report["r72_native_mechanism_live_validation"]
    step = steps()[5]
    native = step["native_popup_menu_supplement"]
    assert step["before_semantic_ui"]["element_count"] == 5
    assert native["attempted"] is True
    assert native["status"] == "supplemented"
    assert native["native_row_count"] == 5
    assert native["native_inspection_candidate_count"] == 1
    assert step["decision"]["action"] == {
        "type": "tap",
        "x": 0.235,
        "y": 0.708,
    }
    assessment = step["parse"]["requested_field_value_assessment"]
    assert assessment["inspection_control_hit"] is True
    assert assessment["mutation_control_hit"] is False
    assert mechanism["r72_native_fix_live_validated"] is True
    assert mechanism["mutation_or_save_action_executed"] is False


def test_r73_captures_explicit_field_without_mutating_record() -> None:
    report = payload()
    step = steps()[6]
    assessment = step["parse"]["requested_field_value_assessment"]
    assert assessment["explicit_value_visible"] is True
    assert assessment["mutation_control_hit"] is False
    assert step["decision"]["action"] == {"type": "press_back"}
    assert step["executed"] is True
    progress = report["task_progress"]
    assert progress["captured_detail_frame_count"] == 1
    assert progress["captured_detail_frame_keys"] == ["target-row-y:0.747"]
    assert episode()["protocol_v2_guard"][
        "target_row_read_only_mutation_block_count"
    ] == 0


def test_r73_nested_return_released_row_coordinate_one_screen_early() -> None:
    report = payload()
    bottleneck = report["nested_return_bottleneck"]
    recorded = steps()
    field_back = recorded[6]
    stale = recorded[7]
    assert field_back["after_semantic_ui"]["sha256"] == (
        bottleneck["first_press_back_after_semantic_ui_sha256"]
    )
    assert stale["before_semantic_ui"]["sha256"] == (
        bottleneck["first_press_back_after_semantic_ui_sha256"]
    )
    assert stale["decision"]["action"] == (
        bottleneck["stale_deferred_row_action"]
    )
    assert stale["after_semantic_ui"]["sha256"] == (
        stale["before_semantic_ui"]["sha256"]
    )
    assert bottleneck["return_to_target_list_confirmed_before_release"] is False


def test_r73_terminal_loop_is_blocked_and_context_overage_recorded() -> None:
    report = payload()
    terminal = steps()[8]
    assert terminal["executed"] is False
    assert terminal["parse"]["initial_validation_error"].startswith(
        "LOOP_GUARD: UNVERIFIED_PROGRESS_REPEAT_REQUIRED:"
    )
    assert terminal["parse"]["repair_validation_error"].startswith(
        "LOOP_GUARD: UNVERIFIED_PROGRESS_REPEAT_REQUIRED:"
    )
    assert [call["usage"]["prompt_tokens"] for call in terminal["model_calls"]] == [
        6901,
        8200,
    ]
    assert report["result"]["context_cap_error_count"] == 1
    assert report["result"]["prompt_headroom_tokens"] == -8
    assert episode()["protocol_v2_guard"][
        "unverified_progress_repeat_block_count"
    ] == 2


def test_r73_stop_report_freezes_selected_raw_artifacts() -> None:
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
        "step_004_before.png": EPISODE_DIR / "step_004_before.png",
        "step_005_before.png": EPISODE_DIR / "step_005_before.png",
        "step_006_before.png": EPISODE_DIR / "step_006_before.png",
        "step_007_before.png": EPISODE_DIR / "step_007_before.png",
        "step_008_before.png": EPISODE_DIR / "step_008_before.png",
    }
    assert set(mapping) == set(report["artifact_sha256"])
    for name, path in mapping.items():
        assert sha256(path.read_bytes()).hexdigest() == (
            report["artifact_sha256"][name]
        )
