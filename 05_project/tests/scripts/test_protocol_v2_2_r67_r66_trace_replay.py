from __future__ import annotations

import json
from pathlib import Path

import pytest

from raven_m.actions.schema import ActionValidationError
from raven_m.controller.episode_controller import (
    EpisodeController,
    _target_row_executor_memory_context,
)
from raven_m.controller.protocol_v2_guard import ProtocolV2DecisionGuard


ROOT = Path(__file__).resolve().parents[3]
EPISODE_PATH = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r66_candidate_"
    "development_smoke_sequence_2/episodes/"
    "02_H17_M0_SportsTrackerActivitiesOnDate_seed20260730/episode.json"
)


def episode() -> dict:
    return json.loads(EPISODE_PATH.read_text(encoding="utf-8"))


def test_r67_projects_r66_terminal_context_below_recorded_growth() -> None:
    recorded = episode()
    terminal = recorded["steps"][9]
    progress = recorded["protocol_v2_guard"]["target_row_progress"]
    projected_memory = _target_row_executor_memory_context(
        terminal["history_context"]["rendered"],
        progress,
    )
    prompt = EpisodeController._user_prompt(
        goal=recorded["task_goal"],
        step=9,
        max_steps=20,
        model_calls=14,
        max_model_calls=64,
        screen_width=1080,
        screen_height=2400,
        previous_outcome=(
            "Executed deferred row coordinate; semantic UI did not change."
        ),
        memory_context=projected_memory,
        protocol_v2=True,
        protocol_v2_2=True,
        target_row_progress=progress,
    )

    assert len(terminal["user_prompt"]) == 11395
    assert len(terminal["history_context"]["rendered"]) == 4064
    assert len(projected_memory) < 600
    assert len(prompt) < 8000
    assert len(terminal["user_prompt"]) - len(prompt) > 3500
    assert "0.834375" not in prompt
    assert "ACTIVE_DETAIL_PRECEDENCE" in prompt
    assert "Press Back." not in prompt


def test_r67_compacts_r66_target_date_row_repair_before_ledger_exists(
) -> None:
    recorded = episode()
    target_date_step = recorded["steps"][6]
    assert target_date_step["model_calls"][0]["usage"][
        "prompt_tokens"
    ] == 7806
    assert target_date_step["model_calls"][1]["usage"][
        "prompt_tokens"
    ] == 8991
    repair = EpisodeController._repair_prompt(
        target_date_step["user_prompt"],
        target_date_step["model_calls"][0]["content"],
        target_date_step["parse"]["initial_validation_error"],
        protocol_v2=True,
    )

    assert repair.lstrip().startswith("TARGET_DATE_ROW_DETAIL_REPAIR")
    assert len(repair) < 2500
    assert "MEMORY_CONTEXT" not in repair
    assert "exactly one pure tap" in repair


def test_r67_replays_r66_deferred_coordinate_as_preexecution_block() -> None:
    recorded = episode()
    action = recorded["steps"][7]["decision"]["action"]
    assert action == {"type": "tap", "x": 0.5, "y": 0.834}
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal=recorded["task_goal"])
    guard.target_date_row_count = 2
    guard.target_row_detail_required = True
    guard.requested_answer_role = "activity type"
    guard.target_row_visit_keys = ["target-row-y:0.747"]
    guard.active_target_row_visit_key = "target-row-y:0.747"
    guard.target_date_row_observations = [
        {
            "target_row_count": 2,
            "target_row_centers": [0.747292, 0.834375],
        }
    ]

    with pytest.raises(
        ActionValidationError,
        match="TARGET_ROW_LEDGER_SCOPE_GUARD",
    ):
        guard.validate_decision(
            {
                "status": "continue",
                "action": action,
                "memory_citations": [],
            },
            page_sha256="r66-active-detail",
            dated_list_answer_assessment={
                "target_date_list_visible": False,
            },
            requested_field_value_assessment={
                "explicit_value_visible": False,
                "visible_control_hit": False,
            },
        )

    assert guard.audit_record()[
        "target_row_off_list_coordinate_block_count"
    ] == 1


def test_r67_replaces_r66_identical_back_repair_with_compact_contract() -> None:
    recorded = episode()
    terminal = recorded["steps"][9]
    progress = recorded["protocol_v2_guard"]["target_row_progress"]
    projected_memory = _target_row_executor_memory_context(
        terminal["history_context"]["rendered"],
        progress,
    )
    prompt = EpisodeController._user_prompt(
        goal=recorded["task_goal"],
        step=9,
        max_steps=20,
        model_calls=14,
        max_model_calls=64,
        screen_width=1080,
        screen_height=2400,
        previous_outcome="The active detail is unchanged.",
        memory_context=projected_memory,
        protocol_v2=True,
        protocol_v2_2=True,
        target_row_progress=progress,
    )
    error = recorded["model_output_error"]["initial_validation_error"]
    invalid = terminal["model_calls"][0]["content"]
    repair = EpisodeController._repair_prompt(
        prompt,
        invalid,
        error,
        protocol_v2=True,
    )

    assert repair.startswith("TARGET_ROW_DETAIL_INSPECTION_REPAIR")
    assert len(repair) < 2500
    assert "MEMORY_CONTEXT" not in repair
    assert "Do not press Back" in repair
    assert "overflow-menu" in repair
    assert "0.834375" not in repair
