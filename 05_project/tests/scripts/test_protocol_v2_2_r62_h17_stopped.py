from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/protocol_v2_2_r62_h17_candidate_stopped.json"
REPORT_SHA256 = (
    "2b0700dd933cf358ed77e66cd26e1df18dd036f4832546672a6194d409d7c95f"
)
SUITE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r62_candidate_"
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


def test_r62_stop_report_and_suite_lifecycle_are_frozen() -> None:
    report = payload()
    assert report["decision"] == (
        "r62_navigation_validated_but_answer_role_binding_failed"
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
    assert summary["finished"] is True
    assert summary["gate_passed"] is False


def test_r62_valid_method_result_and_infrastructure_accounting() -> None:
    report = payload()
    result = report["result"]
    assert result["attempt_count"] == 2
    assert result["valid_method_attempt"] == 2
    assert result["success"] is False
    assert result["failure_code"] == "INCORRECT_ANSWER"
    assert result["executed_action_count"] == 5
    assert result["model_call_count"] == 9
    assert result["reset_audit_passed"] is True
    infra = report["infrastructure_accounting"]
    assert infra["excluded_attempt_count"] == 1
    assert infra["excluded_attempt"]["code"] == "INFRA_EMULATOR_LOST"
    assert infra["cold_recovery_succeeded"] is True


def test_r62_reached_target_date_without_toolbar_detour() -> None:
    report = payload()
    mechanism = report["r62_mechanism_audit"]
    assert mechanism["status"] == "passed_live_navigation_mechanism"
    assert mechanism["markers_or_search_action_executed"] is False
    assert mechanism["chronological_swipe_count"] == 3
    assert mechanism["target_date_reached"] is True
    assert mechanism["chronology_observations"][-1]["target_visible"]
    assert not mechanism["chronology_observations"][-1][
        "scroll_toward_older_required"
    ]
    episode = json.loads(
        (EPISODE_DIR / "episode.json").read_text(encoding="utf-8")
    )
    actions = [step["decision"]["action"] for step in episode["steps"]]
    assert actions[0]["type"] == "open_app"
    assert [action["type"] for action in actions[1:4]] == [
        "swipe",
        "swipe",
        "swipe",
    ]
    assert not any(action["type"] == "tap" for action in actions)


def test_r62_terminal_answer_has_date_and_field_role_mismatches() -> None:
    report = payload()
    audit = report["downstream_failure_audit"]
    assert audit["target_date_visible_before_answer"] is True
    assert audit["requested_answer_role"] == "activity type"
    assert audit["candidate_answer"] == "Bicycle Adventure, Recovery day"
    assert audit["temporal_row_binding"]["Bicycle Adventure"].startswith(
        "visible row dated 2 Oct"
    )
    assert all(
        value == "activity name, not activity type"
        for value in audit["field_role_binding"].values()
    )
    assert audit["visual_source_adjudication"] == "proceed"
    assert audit["completion_adjudication"] == "proceed"
    assert audit["native_evaluator"] == "incorrect answer"


def test_r62_stop_report_freezes_all_selected_raw_artifacts() -> None:
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
        "step_000_after.png": EPISODE_DIR / "step_000_after.png",
        "step_001_after.png": EPISODE_DIR / "step_001_after.png",
        "step_002_after.png": EPISODE_DIR / "step_002_after.png",
        "step_003_after.png": EPISODE_DIR / "step_003_after.png",
        "step_004_before.png": EPISODE_DIR / "step_004_before.png",
        "invalid_attempt_01_episode.json": (
            SUITE
            / "invalid_infrastructure_attempts/02_H17_M0_"
            "SportsTrackerActivitiesOnDate_seed20260730_attempt_01/"
            "episode.json"
        ),
        "recovery_attempt_01_androidworld_smoke.json": (
            SUITE / "recoveries/02_attempt_01/androidworld_smoke.json"
        ),
    }
    assert set(mapping) == set(report["artifact_sha256"])
    for name, path in mapping.items():
        assert sha256(path.read_bytes()).hexdigest() == (
            report["artifact_sha256"][name]
        )
