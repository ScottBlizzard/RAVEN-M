from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/protocol_v2_2_r72_h17_candidate_stopped.json"
REPORT_SHA256 = (
    "f0750a053f9f8d8e5b48ad1ef11446fb7541d9c6905bc909486ab802d0286fe0"
)
SUITE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r72_candidate_"
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


def test_r72_stop_report_and_suite_lifecycle_are_frozen() -> None:
    report = payload()
    assert report["decision"] == (
        "r72_live_accessibility_sufficient_but_verified_inspection_"
        "repair_overridden_by_generic_critic"
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


def test_r72_has_one_clean_valid_method_attempt() -> None:
    report = payload()
    result = report["result"]
    assert result["valid_method_attempt_count"] == 1
    assert result["executed_action_count"] == 5
    assert result["decision_attempt_count"] == 6
    assert result["model_call_count"] == 12
    assert result["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    assert report["infrastructure_accounting"][
        "excluded_episode_attempt_count"
    ] == 0
    assert report["infrastructure_accounting"][
        "startup_environment_failure_count"
    ] == 0


def test_r72_reached_target_detail_and_verified_more_options() -> None:
    report = payload()
    progress = report["task_progress"]
    assert progress["target_row_count"] == 2
    assert progress["visited_row_count"] == 1
    assert progress["active_detail_row_key"] == "target-row-y:0.834"
    terminal = steps()[5]
    assert terminal["before_semantic_ui"]["sha256"] == (
        "3bc67c3ee126f003b18e50095368b222d3534511a47f94e3277fc1257fdd546b"
    )
    assert terminal["before_semantic_ui"]["element_count"] == 38
    initial_error = terminal["parse"]["initial_validation_error"]
    assert "VERIFIED_INSPECTION_CONTROL_CANDIDATES" in initial_error
    assert '"label":"More options"' in initial_error
    assert '"x":0.410648,"y":0.93' in initial_error


def test_r72_native_supplement_correctly_did_not_run() -> None:
    report = payload()
    mechanism = report["r72_mechanism_validation"]
    assert mechanism["native_popup_supplement_configured"] is True
    assert mechanism["native_popup_supplement_attempted_live"] is False
    assert mechanism["native_popup_supplement_status"] == (
        "live_accessibility_sufficient"
    )
    assert mechanism["live_accessibility_inspection_candidate_count"] == 1
    terminal_audit = steps()[5]["native_popup_menu_supplement"]
    assert terminal_audit["configured"] is True
    assert terminal_audit["attempted"] is False
    assert terminal_audit["status"] == "live_accessibility_sufficient"
    assert terminal_audit["live_inspection_candidate_count"] == 1
    assert terminal_audit["native_row_count"] == 0


def test_r72_verified_repair_was_rejected_only_by_generic_critic() -> None:
    terminal = steps()[5]
    assert terminal["executed"] is False
    calls = terminal["model_calls"]
    repair = json.loads(calls[-2]["content"])
    assert repair["action"] == {
        "type": "tap",
        "x": 0.410648,
        "y": 0.93,
    }
    assert "non-commit details" in repair["decision_summary"]
    critic = json.loads(calls[-1]["content"])
    assert critic["verdict"] == "reobserve"
    assert "does not show any visible overflow" in critic["issue"]
    assert terminal["parse"]["repair_validation_error"].startswith(
        "Action critic rejected commit:"
    )
    adjudications = terminal["parse"]["action_adjudications"]
    assert len(adjudications) == 1
    assert adjudications[0]["trigger"] == "consequential_action_candidate"


def test_r72_failure_did_not_execute_blocked_or_mutating_action() -> None:
    report = payload()
    assert report["result"]["answer_action_count"] == 0
    assert report["result"]["blocked_actions_executed_in_application"] is False
    audit = episode()["protocol_v2_guard"]
    assert audit["target_row_non_control_tap_block_count"] == 1
    assert audit["target_row_read_only_mutation_block_count"] == 0
    assert audit["target_row_explicit_field_block_count"] == 0


def test_r72_stop_report_freezes_selected_raw_artifacts() -> None:
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
    }
    assert set(mapping) == set(report["artifact_sha256"])
    for name, path in mapping.items():
        assert sha256(path.read_bytes()).hexdigest() == (
            report["artifact_sha256"][name]
        )
