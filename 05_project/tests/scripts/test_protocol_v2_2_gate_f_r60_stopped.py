from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SUITE = ROOT / "runs/protocol_v2_2/hard_micro_v2_2_seed20260730_r60"
H01 = SUITE / "episodes/01_H01_B3_BrowserMultiply_seed20260730"
H17 = (
    SUITE
    / "episodes/02_H17_M0_SportsTrackerActivitiesOnDate_seed20260730"
)
CHECKPOINT_SHA256 = (
    "f39cf0e02268d67329a37276edbb21aecae0bcabafa2446edd353b2b3ed2002b"
)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_r60_formal_stop_checkpoint_is_byte_frozen() -> None:
    for name in (
        "gate_summary.json",
        "gate_progress.json",
        "batch_01_checkpoint.json",
    ):
        assert digest(SUITE / name) == CHECKPOINT_SHA256
    assert digest(SUITE / "manifest.snapshot.json") == (
        "bdc9f8cfbf38e6c92d245ec73912e7b3bc8ff3b25bd3c926eca5706873a0b298"
    )
    assert digest(SUITE / "instances.snapshot.json") == (
        "87d5ed0c734d97be6617fbe817caece832316fd86e5308ba1520397102596c84"
    )


def test_r60_stopped_after_one_success_and_one_valid_failure() -> None:
    summary = json.loads(
        (SUITE / "gate_summary.json").read_text(encoding="utf-8")
    )
    assert summary["formal_scoring"] is True
    assert summary["result_count"] == 2
    assert summary["success_count"] == 1
    assert summary["stopped_early"] is True
    assert summary["batch_completed"] is False
    assert summary["stop_reason"] == (
        "model_output_invalid_after_one_bounded_repair"
    )
    assert summary["automatic_next_batch"] is False
    assert summary["automatic_gate_g_transition"] is False
    h01, h17 = summary["results"]
    assert (h01["task_id"], h01["variant"], h01["success"]) == (
        "H01",
        "B3",
        True,
    )
    assert h01["evaluator_reward"] == 1.0
    assert h01["semantic_progress_audit"]["passed"] is True
    assert (h17["task_id"], h17["variant"], h17["success"]) == (
        "H17",
        "M0",
        False,
    )
    assert h17["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    assert h17["evaluator_reward"] == 0.0
    assert h17["semantic_progress_audit"]["passed"] is False
    assert h17["semantic_progress_audit"]["unresolved_guard_repair"]
    assert h01["reset_audit"]["passed"] is True
    assert h17["reset_audit"]["passed"] is True


def test_r60_did_not_execute_remaining_formal_cells() -> None:
    episode_names = sorted(path.name for path in (SUITE / "episodes").iterdir())
    assert episode_names == [
        "01_H01_B3_BrowserMultiply_seed20260730",
        "02_H17_M0_SportsTrackerActivitiesOnDate_seed20260730",
    ]
    assert not (SUITE / "batch_02_checkpoint.json").exists()
    assert not (SUITE / "batch_03_checkpoint.json").exists()


def test_r60_h01_success_and_h17_failure_episodes_are_byte_frozen() -> None:
    assert digest(H01 / "episode.json") == (
        "19690842eab0a3e9a432ee72074140e6b5e760cf1d9c2c27d309bea013c4655c"
    )
    assert digest(H17 / "episode.json") == (
        "50f7a0453a9e2962f0cb4a5a738ab1212d27dc58a671d301afffc4d47d6a9351"
    )
    h01 = json.loads((H01 / "episode.json").read_text(encoding="utf-8"))
    h17 = json.loads((H17 / "episode.json").read_text(encoding="utf-8"))
    assert h01["success"] is True and h01["evaluator_reward"] == 1.0
    assert h17["success"] is False and h17["evaluator_reward"] == 0.0
    assert h17["executed_action_count"] == 11
    assert h17["model_output_error"]["initial_validation_error"].startswith(
        "LOOP_GUARD:"
    )
    assert h17["model_output_error"]["repair_validation_error"].startswith(
        "LOOP_GUARD:"
    )


def test_r60_h17_records_two_late_semantic_transitions() -> None:
    episode = json.loads(
        (H17 / "episode.json").read_text(encoding="utf-8")
    )
    steps = episode["steps"]
    assert steps[9]["after_semantic_ui"]["sha256"] != (
        steps[10]["before_semantic_ui"]["sha256"]
    )
    assert steps[10]["after_semantic_ui"]["sha256"] != (
        steps[11]["before_semantic_ui"]["sha256"]
    )
    assert len(steps[9]["after_readiness_observations"]) == 1
    assert len(steps[10]["after_readiness_observations"]) == 1
    assert steps[9]["after_readiness_observations"][0][
        "pixel_change_ratio_from_prior"
    ] < 0.01
    assert steps[10]["after_readiness_observations"][0][
        "pixel_change_ratio_from_prior"
    ] < 0.01
    assert steps[10]["before_semantic_ui"]["element_count"] == 85
    assert steps[11]["before_semantic_ui"]["element_count"] == 5


def test_r60_h17_terminal_repair_repeated_the_same_blocked_action() -> None:
    episode = json.loads(
        (H17 / "episode.json").read_text(encoding="utf-8")
    )
    terminal = episode["steps"][11]
    assert terminal["executed"] is False
    assert terminal["decision"] is None
    assert terminal["parse"]["valid_after_one_repair"] is False
    assert len(terminal["model_calls"]) == 2
    assert terminal["model_calls"][0]["content"] == (
        terminal["model_calls"][1]["content"]
    )
    assert terminal["model_calls"][0]["response_sha256"] == (
        "7cb5211102325b5d35bd09924d371dc2a487ecce2e6c5721ce4b7bda250b5d43"
    )
    assert '"type":"press_back"' in terminal["model_calls"][0]["content"]
