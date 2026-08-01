from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import pytest

from raven_m.actions.schema import ActionValidationError
from raven_m.controller.episode_controller import EpisodeController
from raven_m.controller.protocol_v2_guard import ProtocolV2DecisionGuard
from raven_m.models.transformers_client import ModelCall


ROOT = Path(__file__).resolve().parents[3]
R73_REPORT = ROOT / "reports/protocol_v2_2_r73_h17_candidate_stopped.json"
R73_REPORT_SHA256 = (
    "cfa22bbcdafb400306690fe8b5e3c51b99628c9e88c561b2319d8f335af13ba0"
)
R73_EPISODE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r73_candidate_"
    "development_smoke_sequence_2/episodes/"
    "02_H17_M0_SportsTrackerActivitiesOnDate_seed20260730"
)
INTERMEDIATE_SCREENSHOT = R73_EPISODE / "step_007_before.png"
FIELD_SOURCE = R73_EPISODE / "step_006_before.png"
FIELD_CROP = (
    R73_EPISODE
    / "step_006_before_target_row_y_0_747_requested_field.png"
)
ACTION_SCHEMA = ROOT / "05_project/schemas/action.raven.v2.schema.json"
GOAL = (
    "What activities did I do September 24 2023 in the OpenTracks app? "
    "Answer with the activity type only. If there are multiple types, "
    "format your answer in a comma separated list."
)
DETAIL_SEMANTIC_SHA256 = (
    "3bc67c3ee126f003b18e50095368b222d3534511a47f94e3277fc1257fdd546b"
)
TARGET_CENTERS = [0.747292, 0.834375]
MORE_OPTIONS = {
    "content_description": "More options",
    "is_visible": True,
    "is_clickable": True,
    "is_enabled": True,
    "bbox": {
        "x_min": 0.362037,
        "x_max": 0.459259,
        "y_min": 0.90375,
        "y_max": 0.95625,
    },
}


def decision(action: dict[str, Any], summary: str) -> dict[str, Any]:
    return {
        "status": "continue",
        "action": action,
        "expected_outcome": "The read-only inspection workflow advances.",
        "decision_summary": summary,
        "state_delta": [],
        "memory_citations": [],
        "completion_evidence": [],
    }


STALE_ROW_DECISION = {
    **decision(
        {"type": "tap", "x": 0.5, "y": 0.834},
        (
            "Tap the unvisited row center at y=0.834 to open its details "
            "and capture the activity type."
        ),
    ),
    "expected_outcome": (
        "The next unvisited row for September 24, 2023, is opened to reveal "
        "its activity type."
    ),
    "state_delta": [
        {
            "kind": "progress",
            "subject": "row_visit",
            "predicate": "completed",
            "object": "target-row-y:0.834",
            "natural_language": "The row at y=0.834 has been visited.",
            "evidence": "direct_screen",
            "confidence": 0.95,
        }
    ],
}
RETURN_DECISION = decision(
    {"type": "press_back"},
    "Return from the intermediate detail page to the target-date list.",
)


class NestedReturnReplayClient:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    def generate(self, **kwargs: Any) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        payload = RETURN_DECISION if label.endswith("_repair") else STALE_ROW_DECISION
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(payload),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


def active_guard() -> ProtocolV2DecisionGuard:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal=GOAL)
    guard.target_date_row_count = 2
    guard.target_row_detail_required = True
    guard.target_row_visit_keys = ["target-row-y:0.747"]
    guard.active_target_row_visit_key = "target-row-y:0.747"
    guard.requested_answer_role = "activity type"
    guard.target_date_row_observations = [
        {
            "semantic_state_sha256": (
                "8095b9ed6872f7192aebaebd86781114778bb6aa65fe5dafddc4295e9dd535cc"
            ),
            "target_row_count": 2,
            "target_row_centers": TARGET_CENTERS,
            "requested_answer_role": "activity type",
        }
    ]
    return guard


def captured_frame() -> dict[str, Any]:
    return {
        "visit_key": "target-row-y:0.747",
        "source_path": str(FIELD_SOURCE.resolve()),
        "source_sha256": sha256(FIELD_SOURCE.read_bytes()).hexdigest(),
        "path": str(FIELD_CROP.resolve()),
        "sha256": sha256(FIELD_CROP.read_bytes()).hexdigest(),
        "requested_field_evidence_explicit": True,
        "requested_answer_role": "activity type",
        "matched_value_control_count": 1,
    }


def explicit_field_assessment() -> dict[str, Any]:
    return {
        "schema_version": "requested_field_value_assessment.v1",
        "explicit_value_visible": True,
        "mutation_control_hit": False,
        "requested_field_control_hit": False,
        "inspection_control_hit": False,
        "type_text_attempted": False,
    }


def start_return(guard: ProtocolV2DecisionGuard) -> None:
    guard.validate_decision(
        RETURN_DECISION,
        page_sha256=(
            "781cb14f3c36e8443a350cf8562d8fcf6e7dbd8d85109500ea745934e15b4c5a"
        ),
        dated_list_answer_assessment={},
        dated_row_detail_frame=captured_frame(),
        requested_field_value_assessment=explicit_field_assessment(),
    )


def confirmed_list_assessment(*, row_count: int = 2) -> dict[str, Any]:
    return {
        "target_date_list_visible": True,
        "target_row_count": row_count,
        "target_row_centers": TARGET_CENTERS[:row_count],
    }


def test_r74_hides_deferred_coordinates_after_exact_r73_field_capture() -> None:
    assert sha256(R73_REPORT.read_bytes()).hexdigest() == R73_REPORT_SHA256
    assert sha256(INTERMEDIATE_SCREENSHOT.read_bytes()).hexdigest() == (
        "c498854e3e2262ba285f174922749f6a8a26847dd068f71f3895dbba78a69e3e"
    )
    guard = active_guard()
    start_return(guard)
    progress = guard.target_row_progress_record()
    assert progress["active_detail_row_key"] is None
    assert progress["return_to_target_list_pending"] is True
    assert progress["return_to_target_list_visit_key"] == "target-row-y:0.747"
    assert progress["return_to_target_list_back_count"] == 1
    prompt = EpisodeController._user_prompt(
        goal=GOAL,
        step=7,
        max_steps=20,
        model_calls=10,
        max_model_calls=64,
        screen_width=1080,
        screen_height=2400,
        previous_outcome="The explicit field was captured.",
        protocol_v2=True,
        protocol_v2_2=True,
        target_row_progress=progress,
    )
    assert '"phase":"return_to_target_date_list"' in prompt
    assert '"deferred_row_coordinates_executable":false' in prompt
    assert "0.834375" not in prompt
    assert "Press Back exactly once" in prompt


def test_r74_replays_r73_stale_row_as_one_exact_back_repair() -> None:
    guard = active_guard()
    start_return(guard)
    client = NestedReturnReplayClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_model_calls=2,
        action_schema_path=ACTION_SCHEMA,
        decision_guard=guard,
        protocol_v2=True,
        protocol_v2_2=True,
    )
    parsed, calls, meta = controller._call_and_parse(
        image_path=INTERMEDIATE_SCREENSHOT,
        page_semantic_sha256=DETAIL_SEMANTIC_SHA256,
        destination_picker_is_active=False,
        ui_elements=[MORE_OPTIONS],
        screen_width=1080,
        screen_height=2400,
        task_goal=GOAL,
        user_prompt="ORIGINAL",
        episode_id="r74-r73-nested-return-replay",
        step=7,
        model_call_count=0,
    )
    assert parsed == RETURN_DECISION
    assert len(calls) == 2
    assert len(client.requests) == 2
    assert meta["first_pass"] is False
    assert meta["model_repair_used"] is True
    assert meta["initial_validation_error"].startswith(
        "TARGET_ROW_LIST_RETURN_GUARD:"
    )
    assert "TARGET_ROW_ENUMERATION_BACK_REQUIRED:" in (
        meta["initial_validation_error"]
    )
    assert guard.target_row_return_pending_visit_key == "target-row-y:0.747"
    assert guard.target_row_return_back_count == 2
    assert guard.target_row_return_navigation_count == 1


def test_r74_releases_next_row_only_on_exact_target_list_confirmation() -> None:
    guard = active_guard()
    start_return(guard)
    awaiting = guard.reconcile_target_row_list_return(
        page_sha256=DETAIL_SEMANTIC_SHA256,
        dated_list_answer_assessment={},
    )
    assert awaiting["status"] == "awaiting_target_list"
    assert guard.target_row_return_pending_visit_key is not None

    wrong_count = guard.reconcile_target_row_list_return(
        page_sha256="1" * 64,
        dated_list_answer_assessment=confirmed_list_assessment(row_count=1),
    )
    assert wrong_count["status"] == "awaiting_target_list"
    assert guard.target_row_return_pending_visit_key is not None

    confirmed = guard.reconcile_target_row_list_return(
        page_sha256=(
            "8095b9ed6872f7192aebaebd86781114778bb6aa65fe5dafddc4295e9dd535cc"
        ),
        dated_list_answer_assessment=confirmed_list_assessment(),
    )
    assert confirmed["status"] == "confirmed"
    progress = guard.target_row_progress_record()
    assert progress["return_to_target_list_pending"] is False
    assert progress["unvisited_rows"] == [
        {"visit_key": "target-row-y:0.834", "y_center": 0.834375}
    ]
    assert guard.target_row_return_confirmation_count == 1


def test_r74_fails_closed_after_bounded_second_back_without_list() -> None:
    guard = active_guard()
    start_return(guard)
    guard.validate_decision(
        RETURN_DECISION,
        page_sha256=DETAIL_SEMANTIC_SHA256,
        dated_list_answer_assessment={},
        requested_field_value_assessment={},
    )
    assert guard.target_row_return_back_count == 2
    with pytest.raises(
        ActionValidationError,
        match="TARGET_ROW_LIST_RETURN_FAILED:",
    ):
        guard.validate_decision(
            RETURN_DECISION,
            page_sha256="2" * 64,
            dated_list_answer_assessment={},
            requested_field_value_assessment={},
        )


def test_r74_never_allows_a_row_tap_while_return_is_pending() -> None:
    guard = active_guard()
    start_return(guard)
    with pytest.raises(
        ActionValidationError,
        match="TARGET_ROW_LIST_RETURN_GUARD:",
    ):
        guard.validate_decision(
            STALE_ROW_DECISION,
            page_sha256=DETAIL_SEMANTIC_SHA256,
            dated_list_answer_assessment={},
            requested_field_value_assessment={},
        )
    assert guard.target_row_return_back_count == 1
    assert guard.target_row_return_block_count == 1


def test_r74_return_state_is_task_and_answer_agnostic() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            ROOT / "05_project/src/raven_m/controller/episode_controller.py",
            ROOT / "05_project/src/raven_m/controller/protocol_v2_guard.py",
        )
    )
    for forbidden in (
        "SportsTrackerActivitiesOnDate",
        "de.dennisguse.opentracks",
        "September 24 2023",
        "Skill work",
        "Recovery day",
        "swimming",
        "target-row-y:0.747",
        "target-row-y:0.834",
    ):
        assert forbidden not in source
