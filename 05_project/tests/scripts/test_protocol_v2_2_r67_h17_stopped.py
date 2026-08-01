from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/protocol_v2_2_r67_h17_candidate_stopped.json"
REPORT_SHA256 = (
    "0b010630f3c807b01b723c3b4f03302d9f606f12fb0f307d979e4e093230b187"
)
SUITE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r67_candidate_"
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


def test_r67_stop_report_and_suite_lifecycle_are_frozen() -> None:
    report = payload()
    assert report["decision"] == (
        "r67_active_detail_precedence_and_context_cap_validated_but_"
        "blank_tap_and_repair_priority_failed"
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


def test_r67_is_one_valid_method_attempt_after_audited_recovery() -> None:
    report = payload()
    result = report["result"]
    assert result["attempt_count"] == 1
    assert result["valid_method_attempt"] == 1
    assert result["success"] is False
    assert result["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    assert result["executed_action_count"] == 6
    assert result["model_call_count"] == 12
    assert result["answer_action_count"] == 0
    assert result["reset_audit_passed"] is True
    infra = report["infrastructure_accounting"]
    assert infra["excluded_episode_attempt_count"] == 0
    assert infra["startup_environment_failure_count"] == 1
    assert infra["startup_environment_recovery_count"] == 1
    assert infra["startup_environment_last_status"] == "recovered"
    assert infra["cold_recovery_smoke_passed"] is True


def test_r67_validates_precedence_and_exposes_blank_tap_gap() -> None:
    report = payload()
    mechanism = report["r67_validated_mechanisms"]
    assert mechanism["target_date_row_count"] == 2
    assert mechanism["target_date_visible_swipe_block_count"] == 1
    assert mechanism["blocked_swipe_executed_in_application"] is False
    assert mechanism["compact_target_row_repair_succeeded"] is True
    assert mechanism["deferred_row_coordinate_exposed_on_active_detail"] is False
    assert mechanism["deferred_row_coordinate_executed_on_active_detail"] is False
    assert mechanism["unsafe_application_mutation_executed"] is False
    steps = episode()["steps"]
    assert steps[3]["decision"]["action"] == {
        "type": "tap",
        "x": 0.5,
        "y": 0.775,
    }
    assert steps[4]["decision"]["action"] == {
        "type": "tap",
        "x": 0.5,
        "y": 0.15,
    }
    assert steps[5]["decision"]["action"] == steps[4]["decision"]["action"]
    assert steps[6]["decision"] is None
    error = episode()["model_output_error"]
    assert "CRITIC_CONSTRAINT" in error["initial_validation_error"]
    assert "TARGET_ROW_EXPLICIT_FIELD_GUARD" in (
        error["repair_validation_error"]
    )


def test_r67_prompt_cap_is_respected() -> None:
    cap = payload()["prompt_budget_audit"]
    assert cap["configured_max_prompt_tokens"] == 8192
    assert cap["observed_max_prompt_tokens"] == 8050
    assert cap["headroom_tokens"] == 142
    assert cap["context_cap_error_count"] == 0
    assert cap["conclusion"].startswith("r67 eliminated every r66")


def test_r67_stop_report_freezes_selected_raw_artifacts() -> None:
    report = payload()
    mapping = {
        "gate_summary.json": SUITE / "gate_summary.json",
        "gate_progress.json": SUITE / "gate_progress.json",
        "manifest.snapshot.json": SUITE / "manifest.snapshot.json",
        "instances.snapshot.json": SUITE / "instances.snapshot.json",
        "startup_environment_audit.json": (
            SUITE / "startup_environment_audit.json"
        ),
        "androidworld_smoke.json": (
            SUITE
            / "recoveries/startup_environment/androidworld_smoke.json"
        ),
        "episode.json": EPISODE_DIR / "episode.json",
        "events.jsonl": EPISODE_DIR / "events.jsonl",
        "memory_events.jsonl": EPISODE_DIR / "memory_events.jsonl",
        "step_003_before.png": EPISODE_DIR / "step_003_before.png",
        "step_003_after.png": EPISODE_DIR / "step_003_after.png",
        "step_004_before.png": EPISODE_DIR / "step_004_before.png",
        "step_006_before.png": EPISODE_DIR / "step_006_before.png",
    }
    assert set(mapping) == set(report["artifact_sha256"])
    for name, path in mapping.items():
        assert sha256(path.read_bytes()).hexdigest() == (
            report["artifact_sha256"][name]
        )
