from __future__ import annotations

import json
from pathlib import Path

from raven_m.controller.episode_controller import EpisodeController
from raven_m.controller.protocol_v2_guard import ProtocolV2DecisionGuard
from raven_m.models.transformers_client import ModelCall


ROOT = Path(__file__).resolve().parents[3]
DETAIL_SCREENSHOT = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r70_candidate_"
    "development_smoke_sequence_2/episodes/"
    "02_H17_M0_SportsTrackerActivitiesOnDate_seed20260730/"
    "step_004_before.png"
)
ACTION_SCHEMA = ROOT / "05_project/schemas/action.v2.schema.json"


class RecordedRepairClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        repair = kwargs["call_label"].endswith("_repair")
        action = (
            {"type": "tap", "x": 0.405, "y": 0.925}
            if repair
            else {"type": "tap", "x": 0.5, "y": 0.15}
        )
        decision = {
            "status": "continue",
            "action": action,
            "expected_outcome": (
                "The overflow menu opens for read-only inspection."
                if repair
                else "The requested activity field becomes visible."
            ),
            "decision_summary": (
                "Tap the verified vertical ellipsis."
                if repair
                else "Inspect the activity detail."
            ),
            "state_delta": [],
            "memory_citations": [],
        }
        label = kwargs["call_label"]
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


def test_r71_computes_visual_assessment_before_pre_history_guard() -> None:
    goal = (
        "What activities did I do September 24 2023? "
        "Answer with the activity type only."
    )
    client = RecordedRepairClient()
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal=goal)
    guard.target_date_row_count = 2
    guard.target_row_detail_required = True
    guard.target_row_visit_keys = ["target-row-y:0.747"]
    guard.active_target_row_visit_key = "target-row-y:0.747"
    guard.requested_answer_role = "activity type"
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2",
        max_model_calls=2,
        action_schema_path=ACTION_SCHEMA,
        decision_guard=guard,
        protocol_v2=True,
        protocol_v2_2=True,
    )

    parsed, calls, meta = controller._call_and_parse(
        image_path=DETAIL_SCREENSHOT,
        page_semantic_sha256=(
            "3bc67c3ee126f003b18e50095368b222d3534511a47f94e3277fc1257fdd546b"
        ),
        destination_picker_is_active=False,
        ui_elements=[],
        screen_width=1080,
        screen_height=2400,
        task_goal=goal,
        user_prompt="ORIGINAL",
        episode_id="r71-r70-order-replay",
        step=4,
        model_call_count=0,
    )

    assert len(calls) == 2
    assert parsed["action"] == {"type": "tap", "x": 0.405,
                                 "y": 0.925}
    assert "VERIFIED_INSPECTION_CONTROL_CANDIDATES" in (
        meta["initial_validation_error"]
    )
    assessment = meta["requested_field_value_assessment"]
    assert assessment["visual_inspection_fallback_evaluated"] is True
    assert assessment["visual_inspection_candidate_count"] == 1
    assert assessment["inspection_control_hit"] is True
    assert assessment["inspection_control_candidates"][0]["center"] == {
        "x": 0.405536,
        "y": 0.929999,
    }
    detail_blocks = [
        item
        for item in guard.validation_blocks
        if item["reason"] == "target_row_detail_non_control_tap"
    ]
    assert len(detail_blocks) == 1
    blocked_assessment = detail_blocks[0][
        "requested_field_value_assessment"
    ]
    assert blocked_assessment["visual_inspection_candidate_count"] == 1
    assert blocked_assessment["inspection_control_candidates"]
    assert "current_screenshot_shape" in client.requests[1]["user_prompt"]
