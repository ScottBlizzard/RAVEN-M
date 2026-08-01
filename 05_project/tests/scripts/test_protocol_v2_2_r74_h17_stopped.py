from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/protocol_v2_2_r74_h17_candidate_stopped.json"
REPORT_SHA256 = (
    "129c8f7c34c0431b28c8c3aced6c7706944ff40cb75ccf44b91a4918ce48f775"
)
SUITE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r74_candidate_"
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


def events() -> list[dict]:
    return [
        json.loads(line)
        for line in (EPISODE_DIR / "events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]


def steps() -> dict[int, dict]:
    return {
        item["step"]: item
        for item in events()
        if item.get("event") == "step"
    }


def test_r74_stop_report_and_suite_lifecycle_are_frozen() -> None:
    report = payload()
    assert report["decision"] == (
        "r74_nested_return_succeeded_but_tolerant_row_hit_assigned_"
        "the_same_detail_to_two_rows"
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


def test_r74_records_one_valid_method_attempt_and_no_infra_retry() -> None:
    report = payload()
    result = report["result"]
    assert result["valid_method_attempt_count"] == 1
    assert result["total_attempt_count"] == 1
    assert result["executed_action_count"] == 18
    assert result["decision_attempt_count"] == 19
    assert result["model_call_count"] == 35
    assert report["infrastructure_accounting"][
        "excluded_episode_attempt_count"
    ] == 0
    assert result["reset_audit_passed"] is True


def test_r74_nested_return_is_confirmed_before_each_release() -> None:
    report = payload()
    mechanism = report["r74_mechanism_live_validation"]
    recorded = steps()
    assert mechanism["r74_nested_return_fix_live_validated"] is True
    assert recorded[9]["decision"]["action"] == {"type": "press_back"}
    assert recorded[10]["decision"]["action"] == {"type": "press_back"}
    assert recorded[10]["parse"]["dated_list_answer_assessment"][
        "target_date_list_visible"
    ] is False
    assert recorded[11]["before_semantic_ui"]["sha256"] == (
        "8095b9ed6872f7192aebaebd86781114778bb6aa65fe5dafddc4295e9dd535cc"
    )
    assert recorded[14]["decision"]["action"] == {"type": "press_back"}
    assert recorded[15]["decision"]["action"] == {"type": "press_back"}
    guard = episode()["protocol_v2_guard"]
    assert guard["target_row_return_start_count"] == 2
    assert guard["target_row_return_navigation_count"] == 2
    assert guard["target_row_return_confirmation_count"] == 2
    assert guard["target_row_return_block_count"] == 0


def test_r74_first_tap_is_tolerantly_misattributed() -> None:
    report = payload()
    bottleneck = report["row_identity_bottleneck"]
    recorded = steps()
    first = recorded[6]
    assessment = first["parse"]["dated_list_answer_assessment"]
    assert first["decision"]["action"] == bottleneck["first_row_action"]
    assert assessment["target_row_centers"] == [0.747292, 0.834375]
    assert assessment["target_row_tap_center"] == 0.834375
    assert assessment["target_row_tap_index"] == 1
    assert assessment["target_row_tap_permitted"] is True
    assert bottleneck["first_row_y_offset_from_ledger_center"] == -0.029375
    assert recorded[11]["decision"]["action"] == (
        bottleneck["second_row_action"]
    )


def test_r74_two_ledger_rows_capture_the_same_detail_semantics() -> None:
    report = payload()
    recorded = steps()
    assert recorded[9]["before_semantic_ui"]["sha256"] == (
        recorded[14]["before_semantic_ui"]["sha256"]
    )
    assert recorded[9]["before_semantic_ui"]["sha256"] == report[
        "row_identity_bottleneck"
    ]["first_explicit_field_semantic_ui_sha256"]
    guard = episode()["protocol_v2_guard"]
    frames = guard["target_row_detail_frames"]
    assert {item["visit_key"] for item in frames} == {
        "target-row-y:0.747",
        "target-row-y:0.834",
    }
    assert len(frames) == 2


def test_r74_requested_field_crops_are_pixel_identical_below_clock() -> None:
    upper = Image.open(
        EPISODE_DIR
        / "step_009_before_target_row_y_0_834_requested_field.png"
    ).convert("RGB")
    lower = Image.open(
        EPISODE_DIR
        / "step_014_before_target_row_y_0_747_requested_field.png"
    ).convert("RGB")
    upper_region = upper.crop((0, 120, upper.width, upper.height))
    lower_region = lower.crop((0, 120, lower.width, lower.height))
    assert upper_region.tobytes() == lower_region.tobytes()
    assert sha256(upper_region.tobytes()).hexdigest() == (
        "f48ddf673c8831e1acab7ace4d460c19a23fcbff6190b41d7040e7718c3710ab"
    )


def test_r74_answer_guard_prevents_duplicate_evidence_completion() -> None:
    report = payload()
    recorded = steps()
    for number in (16, 17):
        assert recorded[number]["parse"]["initial_validation_error"].startswith(
            "ANSWER_ASSOCIATION_GUARD:"
        )
        assert recorded[number]["decision"]["action"] == {
            "type": "wait",
            "duration_ms": 1000,
        }
    terminal = next(
        item
        for item in events()
        if item.get("event") == "model_output_invalid_after_repair"
    )
    assert terminal["error"]["initial_validation_error"].startswith(
        "ANSWER_ASSOCIATION_GUARD:"
    )
    assert terminal["error"]["repair_validation_error"].startswith(
        "CRITIC_CONSTRAINT:"
    )
    assert report["terminal_safety_behavior"][
        "incorrect_or_incomplete_answer_executed"
    ] is False
    assert report["terminal_safety_behavior"][
        "mutation_or_save_action_executed"
    ] is False


def test_r74_context_overage_is_recorded_not_hidden() -> None:
    report = payload()
    assert report["result"]["configured_max_prompt_tokens"] == 8192
    assert report["result"]["observed_max_prompt_tokens"] == 9746
    assert report["result"]["prompt_headroom_tokens"] == -1554
    assert report["result"]["context_cap_error_count"] == 1


def test_r74_stop_report_freezes_selected_raw_artifacts() -> None:
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
        "step_006_before.png": EPISODE_DIR / "step_006_before.png",
        "step_009_before.png": EPISODE_DIR / "step_009_before.png",
        "step_009_field.png": (
            EPISODE_DIR
            / "step_009_before_target_row_y_0_834_requested_field.png"
        ),
        "step_010_after.png": EPISODE_DIR / "step_010_after.png",
        "step_011_before.png": EPISODE_DIR / "step_011_before.png",
        "step_011_after.png": EPISODE_DIR / "step_011_after.png",
        "step_014_before.png": EPISODE_DIR / "step_014_before.png",
        "step_014_field.png": (
            EPISODE_DIR
            / "step_014_before_target_row_y_0_747_requested_field.png"
        ),
        "step_015_after.png": EPISODE_DIR / "step_015_after.png",
        "step_016_before.png": EPISODE_DIR / "step_016_before.png",
        "step_017_before.png": EPISODE_DIR / "step_017_before.png",
        "step_018_before.png": EPISODE_DIR / "step_018_before.png",
    }
    assert set(mapping) == set(report["artifact_sha256"])
    for name, path in mapping.items():
        assert sha256(path.read_bytes()).hexdigest() == (
            report["artifact_sha256"][name]
        )
