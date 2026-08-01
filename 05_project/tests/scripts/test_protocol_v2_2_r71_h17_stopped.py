from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/protocol_v2_2_r71_h17_candidate_stopped.json"
REPORT_SHA256 = (
    "2cccf1bc8a9a4c1abde04759fa706d3dc335f0b345e3f43cd95bcda801df56d8"
)
SUITE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r71_candidate_"
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


def test_r71_stop_report_and_suite_lifecycle_are_frozen() -> None:
    report = payload()
    assert report["decision"] == (
        "r71_ordering_and_visual_ellipsis_validated_but_popup_"
        "edit_control_unverified"
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


def test_r71_has_one_clean_valid_method_attempt() -> None:
    report = payload()
    result = report["result"]
    assert result["valid_method_attempt_count"] == 1
    assert result["executed_action_count"] == 11
    assert result["decision_attempt_count"] == 12
    assert result["model_call_count"] == 22
    assert result["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    assert report["infrastructure_accounting"][
        "excluded_episode_attempt_count"
    ] == 0
    assert report["infrastructure_accounting"][
        "startup_environment_failure_count"
    ] == 0


def test_r71_crossed_r70_failure_and_executed_verified_ellipsis() -> None:
    report = payload()
    mechanism = report["r71_mechanism_validation"]
    assert mechanism["old_r70_failure_point_crossed"] is True
    assert mechanism["initial_row_title_answer_blocked"] is True
    assert mechanism["visual_ellipsis_repair_executed"] is True
    recorded_steps = steps()
    assert recorded_steps[5]["decision"]["action"] == {
        "type": "tap",
        "x": 0.405,
        "y": 0.925,
    }
    assert recorded_steps[5]["executed"] is True
    assert recorded_steps[6]["before_semantic_ui"]["element_count"] == 5


def test_r71_popup_edit_was_blocked_without_executing_delete() -> None:
    report = payload()
    bottleneck = report["popup_menu_bottleneck"]
    recorded_steps = steps()
    for index in bottleneck["open_menu_steps"]:
        step = recorded_steps[index]
        assert step["before_semantic_ui"]["sha256"] == (
            bottleneck["open_menu_semantic_ui_sha256"]
        )
        assert step["before_semantic_ui"]["element_count"] == 5
        assert "x\":0.25,\"y\":0.71" in step["model_calls"][0]["content"]
        assert "Tap 'Edit'" in step["model_calls"][0]["content"]
        assert step["parse"]["initial_validation_error"].startswith(
            "TARGET_ROW_DETAIL_CONTROL_GUARD:"
        )
        assert step["decision"]["action"]["x"] < 0.42
        assert step["decision"]["action"]["y"] > 0.92
    assert bottleneck["dangerous_adjacent_control"] == "Delete"
    assert report["result"]["blocked_actions_executed_in_application"] is False


def test_r71_terminal_failure_is_loop_guard_not_detector_regression() -> None:
    recorded_steps = steps()
    terminal = recorded_steps[11]
    assert terminal["executed"] is False
    assert terminal["parse"]["initial_validation_error"].startswith(
        "LOOP_GUARD:"
    )
    assert terminal["parse"]["repair_validation_error"].startswith(
        "LOOP_GUARD:"
    )
    assert payload()["r71_mechanism_validation"][
        "ordering_fix_regression_observed"
    ] is False


def test_r71_prompt_cap_progress_and_read_only_boundary_hold() -> None:
    report = payload()
    result = report["result"]
    assert result["observed_max_prompt_tokens"] == 7565
    assert result["prompt_headroom_tokens"] == 627
    assert result["answer_action_count"] == 0
    assert report["task_progress"]["target_row_count"] == 2
    assert report["task_progress"]["visited_row_count"] == 1
    assert episode()["protocol_v2_guard"][
        "target_row_non_control_tap_block_count"
    ] == 3


def test_r71_stop_report_freezes_selected_raw_artifacts() -> None:
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
        "step_006_before.png": EPISODE_DIR / "step_006_before.png",
        "step_008_before.png": EPISODE_DIR / "step_008_before.png",
        "step_010_before.png": EPISODE_DIR / "step_010_before.png",
        "step_011_before.png": EPISODE_DIR / "step_011_before.png",
    }
    assert set(mapping) == set(report["artifact_sha256"])
    for name, path in mapping.items():
        assert sha256(path.read_bytes()).hexdigest() == (
            report["artifact_sha256"][name]
        )
