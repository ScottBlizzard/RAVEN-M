from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/protocol_v2_2_r64_h17_candidate_stopped.json"
REPORT_SHA256 = (
    "bf3a984acb02f7e84f9bed4e65b3e76f5e74d0068621359bbeef9a968353da66"
)
SUITE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r64_candidate_"
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


def test_r64_stop_report_and_suite_lifecycle_are_frozen() -> None:
    report = payload()
    assert report["decision"] == (
        "r64_visual_row_tap_validated_but_unvisited_row_"
        "routing_and_icon_field_grounding_failed"
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


def test_r64_valid_method_result_has_no_infrastructure_exclusion() -> None:
    report = payload()
    result = report["result"]
    assert result["attempt_count"] == 1
    assert result["valid_method_attempt"] == 1
    assert result["success"] is False
    assert result["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    assert result["executed_action_count"] == 7
    assert result["model_call_count"] == 15
    assert result["answer_action_count"] == 0
    assert result["reset_audit_passed"] is True
    infra = report["infrastructure_accounting"]
    assert infra["excluded_attempt_count"] == 0
    assert infra["startup_environment_failure_count"] == 0


def test_r64_executes_exact_r63_visual_row_repair() -> None:
    mechanism = payload()["r64_mechanism_audit"]
    assert mechanism["r63_repair_coordinate"] == {"x": 0.5, "y": 0.775}
    assert mechanism["r63_repair_coordinate_executed"] is True
    assert mechanism["accessibility_clickable_target_required"] is False
    assert mechanism["visual_content_side_and_same_row_checks_passed"] is True
    episode = json.loads(
        (EPISODE_DIR / "episode.json").read_text(encoding="utf-8")
    )
    actions = [
        step["decision"]["action"]
        for step in episode["steps"]
        if step["executed"]
    ]
    assert actions[3] == {"type": "tap", "x": 0.5, "y": 0.775}
    assert episode["steps"][3]["screenshot_changed"] is True


def test_r64_isolates_unvisited_row_and_field_grounding_failures() -> None:
    audit = payload()["downstream_failure_audit"]
    assert audit["validation_block_count"] == 6
    assert audit["distinct_target_row_visit_count"] == 1
    assert audit["distinct_target_row_visit_keys"] == ["target-row-y:0.747"]
    assert audit["executed_target_row_tap_count"] == 2
    assert audit["requested_field_explicit_text_visible"] is False
    assert audit["requested_field_visual_representation"] == (
        "a large category icon rather than an explicit text label"
    )
    assert "already visited" in audit["routing_error"]
    assert "LOOP_GUARD" in audit["final_block"]
    episode = json.loads(
        (EPISODE_DIR / "episode.json").read_text(encoding="utf-8")
    )
    assert episode["steps"][-1]["executed"] is False
    assert "ANSWER_ASSOCIATION_GUARD" in (
        episode["steps"][-1]["parse"]["initial_validation_error"]
    )
    assert "LOOP_GUARD" in (
        episode["steps"][-1]["parse"]["repair_validation_error"]
    )


def test_r64_stop_report_freezes_selected_raw_artifacts() -> None:
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
        "step_003_before.png": EPISODE_DIR / "step_003_before.png",
        "step_003_after.png": EPISODE_DIR / "step_003_after.png",
        "step_004_before.png": EPISODE_DIR / "step_004_before.png",
        "step_005_after.png": EPISODE_DIR / "step_005_after.png",
        "step_006_before.png": EPISODE_DIR / "step_006_before.png",
        "step_007_before.png": EPISODE_DIR / "step_007_before.png",
    }
    assert set(mapping) == set(report["artifact_sha256"])
    for name, path in mapping.items():
        assert sha256(path.read_bytes()).hexdigest() == (
            report["artifact_sha256"][name]
        )

