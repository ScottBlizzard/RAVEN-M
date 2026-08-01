from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/protocol_v2_2_r70_h17_candidate_stopped.json"
REPORT_SHA256 = (
    "95a187c4e31d62a1552c13678131df361f86f774df82cdd7d8ba1f1643d291fa"
)
SUITE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r70_candidate_"
    "development_smoke_sequence_2"
)
EPISODE_DIR = (
    SUITE
    / "episodes/02_H17_M0_"
    "SportsTrackerActivitiesOnDate_seed20260730"
)
INVALID_ROOT = SUITE / "invalid_infrastructure_attempts"


def payload() -> dict:
    assert sha256(REPORT.read_bytes()).hexdigest() == REPORT_SHA256
    return json.loads(REPORT.read_text(encoding="utf-8"))


def episode() -> dict:
    return json.loads(
        (EPISODE_DIR / "episode.json").read_text(encoding="utf-8")
    )


def test_r70_stop_report_and_suite_lifecycle_are_frozen() -> None:
    report = payload()
    assert report["decision"] == (
        "r70_visual_detector_validated_offline_but_pre_guard_order_"
        "bypassed_assessment"
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


def test_r70_has_one_valid_method_attempt_after_zero_call_infra() -> None:
    report = payload()
    result = report["result"]
    assert result["valid_method_attempt_count"] == 1
    assert result["executed_action_count"] == 4
    assert result["model_call_count"] == 8
    assert result["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    infra_path = (
        INVALID_ROOT
        / "02_H17_M0_SportsTrackerActivitiesOnDate_"
        "seed20260730_attempt_01/episode.json"
    )
    infra = json.loads(infra_path.read_text(encoding="utf-8"))
    assert infra["model_call_count"] == 0
    assert infra["executed_action_count"] == 0
    assert report["infrastructure_accounting"][
        "automatic_androidworld_recovery_completed"
    ] is True


def test_r70_runtime_blocks_received_uninitialized_assessment() -> None:
    recorded = episode()
    blocks = [
        item
        for item in recorded["protocol_v2_guard"]["validation_blocks"]
        if item["reason"] == "target_row_detail_non_control_tap"
    ]
    assert len(blocks) == 2
    assert all(
        item["requested_field_value_assessment"] == {} for item in blocks
    )
    order = payload()["integration_order_audit"]
    assert order["early_active_detail_guard_source_line"] < (
        order["requested_field_assessment_source_line"]
    )
    assert order["runtime_detector_was_reached_before_early_guard"] is False


def test_r70_same_terminal_artifact_has_verified_visual_candidate() -> None:
    report = payload()
    replay = report["offline_same_artifact_replay"]
    assert replay["candidate_count"] == 1
    assert replay["recorded_repair_tap_hits_candidate"] is True
    assert replay["detector_false_negative_on_frozen_artifact"] is False
    candidate = replay["verified_candidate"]
    assert candidate["label"] == "vertical ellipsis"
    assert candidate["center"] == {"x": 0.405536, "y": 0.929999}
    assert sha256(
        (EPISODE_DIR / "step_004_before.png").read_bytes()
    ).hexdigest() == replay["same_terminal_screenshot_sha256"]


def test_r70_prompt_cap_and_read_only_boundary_hold() -> None:
    report = payload()
    result = report["result"]
    assert result["observed_max_prompt_tokens"] == 7488
    assert result["prompt_headroom_tokens"] == 704
    assert result["blocked_actions_executed_in_application"] is False
    assert result["answer_action_count"] == 0
    assert report["task_progress"]["target_row_count"] == 2
    assert report["task_progress"]["visited_row_count"] == 1


def test_r70_stop_report_freezes_selected_raw_artifacts() -> None:
    report = payload()
    mapping = {
        "gate_summary.json": SUITE / "gate_summary.json",
        "gate_progress.json": SUITE / "gate_progress.json",
        "manifest.snapshot.json": SUITE / "manifest.snapshot.json",
        "instances.snapshot.json": SUITE / "instances.snapshot.json",
        "startup_environment_audit.json": (
            SUITE / "startup_environment_audit.json"
        ),
        "model_preflight_recovery.json": (
            SUITE / "recoveries/model_preflight/model_service_recovery.json"
        ),
        "invalid_attempt_01_episode.json": (
            INVALID_ROOT
            / "02_H17_M0_SportsTrackerActivitiesOnDate_"
            "seed20260730_attempt_01/episode.json"
        ),
        "androidworld_recovery_commands.json": (
            SUITE / "recoveries/02_attempt_01/commands.json"
        ),
        "androidworld_recovery_smoke.json": (
            SUITE / "recoveries/02_attempt_01/androidworld_smoke.json"
        ),
        "episode.json": EPISODE_DIR / "episode.json",
        "events.jsonl": EPISODE_DIR / "events.jsonl",
        "memory_events.jsonl": EPISODE_DIR / "memory_events.jsonl",
        "step_004_before.png": EPISODE_DIR / "step_004_before.png",
    }
    assert set(mapping) == set(report["artifact_sha256"])
    for name, path in mapping.items():
        assert sha256(path.read_bytes()).hexdigest() == (
            report["artifact_sha256"][name]
        )
