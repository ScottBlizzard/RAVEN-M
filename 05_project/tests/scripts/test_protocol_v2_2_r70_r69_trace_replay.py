from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest
from PIL import Image

from raven_m.actions.schema import ActionValidationError
from raven_m.controller.episode_controller import EpisodeController
from raven_m.controller.protocol_v2_guard import (
    ProtocolV2DecisionGuard,
    requested_field_value_assessment,
    vertical_ellipsis_visual_candidates,
)


ROOT = Path(__file__).resolve().parents[3]
EPISODE_DIR = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r69_candidate_"
    "development_smoke_sequence_2/episodes/"
    "02_H17_M0_SportsTrackerActivitiesOnDate_seed20260730"
)
EPISODE_PATH = EPISODE_DIR / "episode.json"
DETAIL_SCREENSHOT = EPISODE_DIR / "step_004_before.png"


def episode() -> dict:
    return json.loads(EPISODE_PATH.read_text(encoding="utf-8"))


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


def visual_assessment(recorded: dict, action: dict) -> dict:
    return requested_field_value_assessment(
        recorded["task_goal"],
        [],
        {"status": "continue", "action": action},
        screen_width=1080,
        screen_height=2400,
        image_path=DETAIL_SCREENSHOT,
        allow_visual_inspection_fallback=True,
    )


def test_r70_detects_only_generic_geometry_on_frozen_live_screen() -> None:
    assert sha256(DETAIL_SCREENSHOT.read_bytes()).hexdigest() == (
        "c4e4b6258f1928076a243ad6182c94a2b75ab7a17d1f89f21c3a8d3ffd528313"
    )
    assert vertical_ellipsis_visual_candidates(DETAIL_SCREENSHOT) == [
        {
            "label": "vertical ellipsis",
            "source": "current_screenshot_shape",
            "bbox": {
                "x_min": 0.400926,
                "x_max": 0.411111,
                "y_min": 0.921667,
                "y_max": 0.93875,
            },
            "center": {"x": 0.405536, "y": 0.929999},
        }
    ]


def test_r70_r69_initial_blank_tap_routes_visual_repair_candidate() -> None:
    recorded = episode()
    terminal = recorded["steps"][4]
    initial_decision = json.loads(terminal["model_calls"][0]["content"])
    result = visual_assessment(recorded, initial_decision["action"])
    guard = active_guard(recorded)

    assert result["visual_inspection_fallback_evaluated"] is True
    assert result["visual_inspection_candidate_count"] == 1
    assert result["inspection_control_hit"] is False
    with pytest.raises(ActionValidationError) as caught:
        guard.validate_active_target_detail_control(
            initial_decision,
            page_sha256="r69-live-active-detail",
            dated_list_answer_assessment={
                "target_date_list_visible": False,
            },
            requested_field_value_assessment=result,
        )

    error = str(caught.value)
    assert "TARGET_ROW_DETAIL_CONTROL_GUARD" in error
    assert '"label":"vertical ellipsis"' in error
    assert '"x":0.405536,"y":0.929999' in error
    assert "Skill work" not in error
    repair = EpisodeController._repair_prompt(
        terminal["user_prompt"],
        terminal["model_calls"][0]["content"],
        error,
        protocol_v2=True,
    )
    assert repair.startswith("TARGET_ROW_DETAIL_INSPECTION_REPAIR")
    assert '"source":"current_screenshot_shape"' in repair
    assert "Skill work" not in repair


def test_r70_r69_repair_tap_is_grounded_by_current_pixels() -> None:
    recorded = episode()
    repair_decision = json.loads(
        recorded["steps"][4]["model_calls"][1]["content"]
    )
    result = visual_assessment(recorded, repair_decision["action"])
    guard = active_guard(recorded)

    assert repair_decision["action"] == {
        "type": "tap",
        "x": 0.405,
        "y": 0.925,
    }
    assert result["inspection_control_hit"] is True
    guard.validate_active_target_detail_control(
        repair_decision,
        page_sha256="r69-live-active-detail",
        dated_list_answer_assessment={"target_date_list_visible": False},
        requested_field_value_assessment=result,
    )


def test_r70_accessibility_candidate_has_priority_over_visual_fallback() -> None:
    result = requested_field_value_assessment(
        "Return the activity type.",
        [
            {
                "content_description": "More options hidden-value",
                "is_visible": True,
                "is_clickable": True,
                "is_enabled": True,
                "bbox": {
                    "x_min": 0.90,
                    "x_max": 0.99,
                    "y_min": 0.06,
                    "y_max": 0.12,
                },
            }
        ],
        {"status": "continue", "action": {"type": "wait"}},
        screen_width=1080,
        screen_height=2400,
        image_path=DETAIL_SCREENSHOT,
        allow_visual_inspection_fallback=True,
    )

    assert result["visual_inspection_fallback_evaluated"] is False
    assert result["visual_inspection_candidate_count"] == 0
    assert len(result["inspection_control_candidates"]) == 1
    assert result["inspection_control_candidates"][0]["label"] == (
        "More options"
    )
    assert "hidden-value" not in repr(result)


def test_r70_visual_fallback_fails_closed_without_ellipsis(
    tmp_path: Path,
) -> None:
    blank = tmp_path / "blank.png"
    Image.new("RGB", (300, 600), color=(245, 245, 245)).save(blank)
    result = requested_field_value_assessment(
        "Return the activity type.",
        [],
        {"status": "continue", "action": {"type": "tap", "x": 0.5,
                                             "y": 0.9}},
        screen_width=300,
        screen_height=600,
        image_path=blank,
        allow_visual_inspection_fallback=True,
    )

    assert result["visual_inspection_fallback_evaluated"] is True
    assert result["visual_inspection_candidate_count"] == 0
    assert result["inspection_control_candidates"] == []
    assert result["inspection_control_hit"] is False
