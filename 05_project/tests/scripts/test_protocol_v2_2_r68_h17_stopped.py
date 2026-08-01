from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports/protocol_v2_2_r68_h17_candidate_stopped.json"
REPORT_SHA256 = (
    "d6d12ee99406bd674642c2ea4929971d8680ba61032a33896e9cf9656965dfc3"
)
SUITE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r68_candidate_"
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


def test_r68_stop_report_and_suite_lifecycle_are_frozen() -> None:
    report = payload()
    assert report["decision"] == (
        "r68_blank_tap_guard_and_prompt_cap_validated_but_overflow_"
        "control_geometry_not_grounded"
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


def test_r68_is_one_valid_method_attempt_after_audited_recovery() -> None:
    report = payload()
    result = report["result"]
    assert result["attempt_count"] == 1
    assert result["valid_method_attempt"] == 1
    assert result["executed_action_count"] == 3
    assert result["model_call_count"] == 7
    assert result["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    assert result["reset_audit_passed"] is True
    infra = report["infrastructure_accounting"]
    assert infra["startup_environment_failure_count"] == 1
    assert infra["startup_environment_recovery_count"] == 1
    assert infra["startup_environment_last_status"] == "recovered"


def test_r68_blocks_both_detail_taps_without_execution() -> None:
    report = payload()
    audit = report["r68_mechanism_audit"]
    assert audit["target_date_row_count"] == 2
    assert audit["target_row_non_control_tap_block_count"] == 2
    assert audit["blocked_detail_taps_executed_in_application"] is False
    assert audit["unsafe_application_mutation_executed"] is False
    terminal = episode()["steps"][3]
    assert terminal["decision"] is None
    assert "TARGET_ROW_DETAIL_CONTROL_GUARD" in (
        terminal["parse"]["initial_validation_error"]
    )
    assert terminal["model_calls"][1]["content"].find(
        '"x":0.405,"y":0.925'
    ) > 0


def test_r68_prompt_cap_is_respected() -> None:
    cap = payload()["prompt_budget_audit"]
    assert cap["configured_max_prompt_tokens"] == 8192
    assert cap["observed_max_prompt_tokens"] == 7329
    assert cap["headroom_tokens"] == 863
    assert cap["context_cap_error_count"] == 0


def test_r68_stop_report_freezes_selected_raw_artifacts() -> None:
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
        "step_002_before.png": EPISODE_DIR / "step_002_before.png",
        "step_002_after.png": EPISODE_DIR / "step_002_after.png",
        "step_003_before.png": EPISODE_DIR / "step_003_before.png",
    }
    assert set(mapping) == set(report["artifact_sha256"])
    for name, path in mapping.items():
        assert sha256(path.read_bytes()).hexdigest() == (
            report["artifact_sha256"][name]
        )
