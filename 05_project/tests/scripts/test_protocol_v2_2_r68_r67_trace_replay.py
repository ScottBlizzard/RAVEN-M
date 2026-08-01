from __future__ import annotations

import json
from pathlib import Path

import pytest

from raven_m.actions.schema import ActionValidationError
from raven_m.controller.episode_controller import EpisodeController
from raven_m.controller.protocol_v2_guard import ProtocolV2DecisionGuard


ROOT = Path(__file__).resolve().parents[3]
EPISODE_PATH = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r67_candidate_"
    "development_smoke_sequence_2/episodes/"
    "02_H17_M0_SportsTrackerActivitiesOnDate_seed20260730/episode.json"
)


def episode() -> dict:
    return json.loads(EPISODE_PATH.read_text(encoding="utf-8"))


def guard_at_r67_active_detail(recorded: dict) -> ProtocolV2DecisionGuard:
    progress = recorded["protocol_v2_guard"]["target_row_progress"]
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal=recorded["task_goal"])
    guard.target_date_row_count = progress["target_row_count"]
    guard.target_row_detail_required = True
    guard.requested_answer_role = progress["requested_answer_role"]
    guard.target_row_visit_keys = list(progress["visited_row_keys"])
    guard.active_target_row_visit_key = progress["active_detail_row_key"]
    guard.target_date_row_observations = list(
        recorded["protocol_v2_guard"]["target_date_row_observations"]
    )
    return guard


def test_r68_blocks_r67_first_blank_detail_tap_before_history_policy() -> None:
    recorded = episode()
    step = recorded["steps"][4]
    assert step["decision"]["action"] == {
        "type": "tap",
        "x": 0.5,
        "y": 0.15,
    }
    guard = guard_at_r67_active_detail(recorded)

    with pytest.raises(
        ActionValidationError,
        match="TARGET_ROW_DETAIL_CONTROL_GUARD",
    ):
        guard.validate_active_target_detail_control(
            step["decision"],
            page_sha256=step["before_semantic_ui"]["sha256"],
            dated_list_answer_assessment=step["parse"][
                "dated_list_answer_assessment"
            ],
            requested_field_value_assessment=step["parse"][
                "requested_field_value_assessment"
            ],
        )

    assert guard.audit_record()[
        "target_row_non_control_tap_block_count"
    ] == 1


def test_r68_replaces_r67_terminal_critic_repair_with_priority_path() -> None:
    recorded = episode()
    terminal = recorded["steps"][6]
    error = terminal["parse"]["initial_validation_error"]
    assert error.startswith("CRITIC_CONSTRAINT:")
    assert "ACTIVE_DETAIL_PRECEDENCE" in terminal["user_prompt"]
    repair = EpisodeController._repair_prompt(
        terminal["user_prompt"],
        terminal["model_calls"][0]["content"],
        error,
        protocol_v2=True,
    )

    assert repair.startswith("TARGET_ROW_DETAIL_INSPECTION_REPAIR")
    assert "ACTIVE_DETAIL_PRIORITY_OVERRIDE" in repair
    assert "Skill work" not in repair
    assert "open the activity list" not in repair
    assert "MEMORY_CONTEXT" not in repair
    assert "Do not press Back" in repair
    assert len(repair) < 2500


def test_r68_controller_checks_detail_control_before_history_policy() -> None:
    source = (
        ROOT / "05_project/src/raven_m/controller/episode_controller.py"
    ).read_text(encoding="utf-8")
    precheck = source.index(
        "self.decision_guard.validate_active_target_detail_control("
    )
    history = source.index(
        "self.history_policy.validate_decision(parsed_candidate.decision)"
    )
    full_guard = source.index(
        "self.decision_guard.validate_decision(",
        precheck,
    )
    assert precheck < history < full_guard
