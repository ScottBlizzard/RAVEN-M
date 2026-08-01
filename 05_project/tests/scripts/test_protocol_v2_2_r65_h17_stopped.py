from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/protocol_v2_2_r65_h17_candidate_stopped.json"
REPORT_SHA256 = (
    "28a0e45affd6216a82959aa15806976d7b0d93276a9a81b490877bbd35a706e3"
)
SUITE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r65_candidate_"
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


def test_r65_stop_report_and_suite_lifecycle_are_frozen() -> None:
    report = payload()
    assert report["decision"] == (
        "r65_distinct_row_visual_evidence_validated_but_canonical_"
        "icon_category_grounding_and_context_cap_failed"
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
    assert summary["stop_reason"] == "context_cap_exceeded"
    assert summary["gate_passed"] is False


def test_r65_is_one_valid_method_attempt_after_startup_recovery() -> None:
    report = payload()
    result = report["result"]
    assert result["attempt_count"] == 1
    assert result["valid_method_attempt"] == 1
    assert result["success"] is False
    assert result["failure_code"] == "INCORRECT_ANSWER"
    assert result["termination_reason"] == "model_answer"
    assert result["executed_action_count"] == 8
    assert result["model_call_count"] == 13
    assert result["answer_action_count"] == 1
    assert result["answer_cache_match_count"] == 1
    assert result["reset_audit_passed"] is True
    infra = report["infrastructure_accounting"]
    assert infra["excluded_episode_attempt_count"] == 0
    assert infra["startup_environment_failure_count"] == 1
    assert infra["startup_environment_recovery_count"] == 1
    assert infra["startup_environment_last_status"] == "recovered"


def test_r65_executes_distinct_row_and_bound_detail_mechanism() -> None:
    mechanism = payload()["r65_mechanism_audit"]
    assert mechanism["distinct_target_row_visit_count"] == 2
    assert mechanism["distinct_target_row_visit_keys"] == [
        "target-row-y:0.747",
        "target-row-y:0.834",
    ]
    assert mechanism["detail_frame_count"] == 2
    assert mechanism["detail_frames_rehashed_before_review"] is True
    assert mechanism["answer_deferred_until_all_rows_visited"] is True
    assert mechanism["joint_visual_review_executed"] is True
    assert mechanism["joint_visual_review_image_count"] == 3
    actions = [step["decision"]["action"] for step in episode()["steps"]]
    assert actions[3] == {"type": "tap", "x": 0.5, "y": 0.775}
    assert actions[4] == {"type": "press_back"}
    assert actions[5] == {"type": "tap", "x": 0.5, "y": 0.834}
    assert actions[6] == {"type": "press_back"}


def test_r65_isolates_canonical_category_and_context_failures() -> None:
    report = payload()
    category = report["canonical_category_failure_audit"]
    assert category["deterministically_reconstructed_expected_categories"] == [
        "inline skating",
        "cycling",
    ]
    assert category["submitted_categories"] == ["Bicycling", "Walking"]
    final = episode()["steps"][-1]
    assert final["decision"]["action"]["text"] == "Bicycling, Walking"
    visual = final["parse"]["dated_visual_answer_assessment"]
    assert visual["eligible"] is True
    assert visual["adjudicated"] is True
    assert visual["accepted"] is True
    assert visual["detail_frame_count"] == 2
    assert len(visual["model_call_ids"]) == 2
    cap = report["context_cap_audit"]
    assert cap["configured_max_prompt_tokens"] == 12000
    assert cap["observed_max_prompt_tokens"] == 12334
    assert cap["excess_tokens"] == 334
    assert cap["offending_step"] == 7


def test_r65_stop_report_freezes_selected_raw_artifacts() -> None:
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
        "model_service_recovery.json": (
            SUITE
            / "recoveries/model_preflight/model_service_recovery.json"
        ),
        "episode.json": EPISODE_DIR / "episode.json",
        "events.jsonl": EPISODE_DIR / "events.jsonl",
        "memory_events.jsonl": EPISODE_DIR / "memory_events.jsonl",
        "step_002_after.png": EPISODE_DIR / "step_002_after.png",
        "step_003_after.png": EPISODE_DIR / "step_003_after.png",
        "step_005_after.png": EPISODE_DIR / "step_005_after.png",
        "step_006_after.png": EPISODE_DIR / "step_006_after.png",
        "step_007_before.png": EPISODE_DIR / "step_007_before.png",
    }
    assert set(mapping) == set(report["artifact_sha256"])
    for name, path in mapping.items():
        assert sha256(path.read_bytes()).hexdigest() == (
            report["artifact_sha256"][name]
        )
