from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/protocol_v2_2_r66_h17_candidate_stopped.json"
REPORT_SHA256 = (
    "2996dacb59dd0641285d15fb226adeae149633cf330897a8c305af1fea0eedac"
)
SUITE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r66_candidate_"
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


def test_r66_stop_report_and_suite_lifecycle_are_frozen() -> None:
    report = payload()
    assert report["decision"] == (
        "r66_explicit_field_guard_validated_but_active_detail_"
        "ledger_precedence_and_context_cap_failed"
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


def test_r66_is_one_valid_method_attempt_with_clean_startup() -> None:
    report = payload()
    result = report["result"]
    assert result["attempt_count"] == 1
    assert result["valid_method_attempt"] == 1
    assert result["success"] is False
    assert result["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    assert result["termination_reason"] == (
        "model_output_invalid_after_repair"
    )
    assert result["executed_action_count"] == 9
    assert result["model_call_count"] == 16
    assert result["answer_action_count"] == 0
    assert result["reset_audit_passed"] is True
    infra = report["infrastructure_accounting"]
    assert infra["excluded_episode_attempt_count"] == 0
    assert infra["startup_environment_failure_count"] == 0
    assert infra["startup_environment_last_status"] == "clean"


def test_r66_validates_guard_but_exposes_active_detail_precedence_gap() -> None:
    report = payload()
    mechanism = report["r66_mechanism_audit"]
    assert mechanism["target_date_row_count"] == 2
    assert mechanism["distinct_target_row_visit_count"] == 1
    assert mechanism["requested_field_crop_count"] == 0
    assert mechanism["target_row_explicit_field_block_count"] == 2
    assert mechanism["unsafe_application_mutation_executed"] is False
    assert mechanism["answer_submitted"] is False
    steps = episode()["steps"]
    assert steps[6]["decision"]["action"] == {
        "type": "tap",
        "x": 0.5,
        "y": 0.775,
    }
    assert steps[7]["decision"]["action"] == {
        "type": "tap",
        "x": 0.5,
        "y": 0.834,
    }
    assert steps[8]["decision"]["action"] == steps[7]["decision"]["action"]
    assert steps[9]["decision"] is None
    error = episode()["model_output_error"]
    assert "TARGET_ROW_EXPLICIT_FIELD_GUARD" in (
        error["initial_validation_error"]
    )
    assert error["repair_validation_error"] == (
        error["initial_validation_error"]
    )


def test_r66_prompt_cap_improves_but_still_exceeds_frozen_limit() -> None:
    cap = payload()["context_cap_audit"]
    assert cap["configured_max_prompt_tokens"] == 8192
    assert cap["observed_max_prompt_tokens"] == 9282
    assert cap["excess_tokens"] == 1090
    assert cap["improvement_from_r65_peak_tokens"] == 3052
    assert len(cap["over_cap_calls"]) == 3


def test_r66_stop_report_freezes_selected_raw_artifacts() -> None:
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
        "step_006_after.png": EPISODE_DIR / "step_006_after.png",
        "step_009_before.png": EPISODE_DIR / "step_009_before.png",
    }
    assert set(mapping) == set(report["artifact_sha256"])
    for name, path in mapping.items():
        assert sha256(path.read_bytes()).hexdigest() == (
            report["artifact_sha256"][name]
        )
