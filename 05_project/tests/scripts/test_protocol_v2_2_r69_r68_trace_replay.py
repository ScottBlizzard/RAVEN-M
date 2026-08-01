from __future__ import annotations

import json
from pathlib import Path

import pytest

from android_world.env import representation_utils

from raven_m.actions.schema import ActionValidationError
from raven_m.controller.episode_controller import EpisodeController
from raven_m.controller.protocol_v2_guard import (
    ProtocolV2DecisionGuard,
    requested_field_value_assessment,
)


ROOT = Path(__file__).resolve().parents[3]
DETAIL_XML = ROOT / "06_local_runtime/temp/r66_detail1.xml"
EPISODE_PATH = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r68_candidate_"
    "development_smoke_sequence_2/episodes/"
    "02_H17_M0_SportsTrackerActivitiesOnDate_seed20260730/episode.json"
)


def episode() -> dict:
    return json.loads(EPISODE_PATH.read_text(encoding="utf-8"))


def detail_elements():
    return representation_utils.xml_dump_to_ui_elements(
        DETAIL_XML.read_text(encoding="utf-8")
    )


def active_guard(recorded: dict) -> ProtocolV2DecisionGuard:
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


def assessment(recorded: dict, action: dict) -> dict:
    return requested_field_value_assessment(
        recorded["task_goal"],
        detail_elements(),
        {"status": "continue", "action": action},
        screen_width=1080,
        screen_height=2400,
    )


def test_r69_routes_only_sanitized_inspection_control_geometry() -> None:
    recorded = episode()
    action = {"type": "tap", "x": 0.405, "y": 0.925}
    result = assessment(recorded, action)

    assert result["visible_control_count"] == 7
    assert result["visible_control_hit"] is True
    assert result["inspection_control_hit"] is True
    assert result["inspection_control_candidates"] == [
        {
            "label": "More options",
            "bbox": {
                "x_min": 0.362037,
                "x_max": 0.459259,
                "y_min": 0.90375,
                "y_max": 0.95625,
            },
            "center": {"x": 0.410648, "y": 0.93},
        }
    ]
    rendered = json.dumps(result, ensure_ascii=False)
    assert "Skill work" not in rendered
    assert "Recovery day" not in rendered
    assert "swimming" not in rendered


def test_r69_r68_blank_tap_error_carries_verified_candidate() -> None:
    recorded = episode()
    initial = recorded["steps"][3]["model_calls"][0]
    decision = json.loads(initial["content"])
    result = assessment(recorded, decision["action"])
    guard = active_guard(recorded)

    with pytest.raises(ActionValidationError) as caught:
        guard.validate_active_target_detail_control(
            decision,
            page_sha256="r68-active-detail",
            dated_list_answer_assessment={
                "target_date_list_visible": False,
            },
            requested_field_value_assessment=result,
        )

    error = str(caught.value)
    assert "TARGET_ROW_DETAIL_CONTROL_GUARD" in error
    assert "VERIFIED_INSPECTION_CONTROL_CANDIDATES" in error
    assert '"label":"More options"' in error
    assert '"x":0.410648' in error
    assert "Skill work" not in error


def test_r69_repair_preserves_verified_center_without_stale_context() -> None:
    recorded = episode()
    terminal = recorded["steps"][3]
    initial = terminal["model_calls"][0]
    decision = json.loads(initial["content"])
    result = assessment(recorded, decision["action"])
    guard = active_guard(recorded)
    with pytest.raises(ActionValidationError) as caught:
        guard.validate_active_target_detail_control(
            decision,
            page_sha256="r68-active-detail",
            dated_list_answer_assessment={
                "target_date_list_visible": False,
            },
            requested_field_value_assessment=result,
        )
    repair = EpisodeController._repair_prompt(
        terminal["user_prompt"],
        initial["content"],
        str(caught.value),
        protocol_v2=True,
    )

    assert repair.startswith("TARGET_ROW_DETAIL_INSPECTION_REPAIR")
    assert "VERIFIED_INSPECTION_CONTROL_CANDIDATES" in repair
    assert '"center":{"x":0.410648,"y":0.93}' in repair
    assert "MEMORY_CONTEXT" not in repair
    assert "Skill work" not in repair
    assert len(repair) < 3000


def test_r69_recorded_repair_coordinate_is_verified_on_native_dump() -> None:
    recorded = episode()
    repair_content = recorded["steps"][3]["model_calls"][1]["content"]
    repair_action = json.loads(repair_content)["action"]
    result = assessment(recorded, repair_action)
    guard = active_guard(recorded)

    assert repair_action == {"type": "tap", "x": 0.405, "y": 0.925}
    assert result["inspection_control_hit"] is True
    guard.validate_active_target_detail_control(
        {"status": "continue", "action": repair_action},
        page_sha256="r68-active-detail",
        dated_list_answer_assessment={"target_date_list_visible": False},
        requested_field_value_assessment=result,
    )
