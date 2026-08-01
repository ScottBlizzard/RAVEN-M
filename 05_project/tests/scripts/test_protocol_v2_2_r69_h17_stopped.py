from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/protocol_v2_2_r69_h17_candidate_stopped.json"
REPORT_SHA256 = (
    "a05cac6f4fada2f63756487c92834213ce99552ccea2a9961aca2db97f367741"
)
SUITE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r69_candidate_"
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


def test_r69_stop_report_and_suite_lifecycle_are_frozen() -> None:
    report = payload()
    assert report["decision"] == (
        "r69_accessibility_candidate_routing_validated_but_live_"
        "detail_tree_omitted_overflow_control"
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


def test_r69_has_one_valid_method_attempt() -> None:
    result = payload()["result"]
    assert result["attempt_count"] == 1
    assert result["valid_method_attempt"] == 1
    assert result["executed_action_count"] == 4
    assert result["model_call_count"] == 8
    assert result["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    assert result["reset_audit_passed"] is True


def test_r69_preserves_zero_call_infrastructure_archives() -> None:
    report = payload()
    infra = report["infrastructure_accounting"]
    assert infra["excluded_episode_attempt_count"] == 2
    assert infra["excluded_model_call_count"] == 0
    assert infra["excluded_executed_action_count"] == 0
    assert infra["model_recovery_status"] == "timed_out"
    assert infra["resumed_same_suite_after_user_restored_network"] is True
    for attempt in (1, 2):
        path = (
            INVALID_ROOT
            / (
                "02_H17_M0_SportsTrackerActivitiesOnDate_"
                f"seed20260730_attempt_{attempt:02d}/episode.json"
            )
        )
        archived = json.loads(path.read_text(encoding="utf-8"))
        assert archived["model_call_count"] == 0
        assert archived["executed_action_count"] == 0


def test_r69_live_detail_omits_accessibility_candidate() -> None:
    report = payload()
    audit = report["r69_mechanism_audit"]
    assert audit["list_screen_accessibility_candidate_count"] == 1
    assert audit["active_detail_accessibility_candidate_count"] == 0
    assert audit["target_row_non_control_tap_block_count"] == 2
    assert audit["blocked_detail_taps_executed_in_application"] is False
    terminal = episode()["steps"][4]
    assert terminal["decision"] is None
    assert terminal["before_semantic_ui"]["element_count"] == 38
    assert "No verified inspection control is currently available" in (
        terminal["parse"]["repair_validation_error"]
    )
    assert '"x":0.405,"y":0.925' in (
        terminal["model_calls"][1]["content"]
    )


def test_r69_records_native_to_live_representation_gap() -> None:
    gap = payload()["live_representation_gap_audit"]
    assert gap["visible_vertical_ellipsis_present_in_screenshot"] is True
    assert gap["live_detail_semantic_element_count"] == 38
    assert gap["native_xml_parsed_element_count"] == 61
    assert gap["live_detail_semantic_ui_sha256"] != (
        gap["native_xml_semantic_ui_sha256"]
    )
    assert gap["repair_action_executed"] is False
    assert "screenshot fallback" in gap["required_change"]


def test_r69_prompt_cap_is_respected() -> None:
    cap = payload()["prompt_budget_audit"]
    assert cap["configured_max_prompt_tokens"] == 8192
    assert cap["observed_max_prompt_tokens"] == 7205
    assert cap["headroom_tokens"] == 987
    assert cap["context_cap_error_count"] == 0


def test_r69_stop_report_freezes_selected_raw_artifacts() -> None:
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
        "interrupted_model_recovery.json": (
            SUITE / "recoveries/02_model_02/model_service_recovery.json"
        ),
        "invalid_attempt_01_episode.json": (
            INVALID_ROOT
            / "02_H17_M0_SportsTrackerActivitiesOnDate_"
            "seed20260730_attempt_01/episode.json"
        ),
        "invalid_attempt_02_episode.json": (
            INVALID_ROOT
            / "02_H17_M0_SportsTrackerActivitiesOnDate_"
            "seed20260730_attempt_02/episode.json"
        ),
        "episode.json": EPISODE_DIR / "episode.json",
        "events.jsonl": EPISODE_DIR / "events.jsonl",
        "memory_events.jsonl": EPISODE_DIR / "memory_events.jsonl",
        "step_003_before.png": EPISODE_DIR / "step_003_before.png",
        "step_003_after.png": EPISODE_DIR / "step_003_after.png",
        "step_004_before.png": EPISODE_DIR / "step_004_before.png",
    }
    assert set(mapping) == set(report["artifact_sha256"])
    for name, path in mapping.items():
        assert sha256(path.read_bytes()).hexdigest() == (
            report["artifact_sha256"][name]
        )
