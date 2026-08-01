from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from raven_m.controller.episode_controller import (
    EpisodeController,
    _verified_active_detail_inspection_action,
)
from raven_m.controller.protocol_v2_guard import (
    ProtocolV2DecisionGuard,
    requested_field_value_assessment,
)
from raven_m.history.policies import (
    CompletionAdjudication,
    FullRavenMemoryPolicyV2,
    HistoryPolicy,
)
from raven_m.models.transformers_client import ModelCall


ROOT = Path(__file__).resolve().parents[3]
R72_REPORT = ROOT / "reports/protocol_v2_2_r72_h17_candidate_stopped.json"
R72_REPORT_SHA256 = (
    "f0750a053f9f8d8e5b48ad1ef11446fb7541d9c6905bc909486ab802d0286fe0"
)
R72_DETAIL_SCREENSHOT = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r72_candidate_"
    "development_smoke_sequence_2/episodes/"
    "02_H17_M0_SportsTrackerActivitiesOnDate_seed20260730/"
    "step_005_before.png"
)
ACTION_SCHEMA = ROOT / "05_project/schemas/action.raven.v2.schema.json"
GOAL = (
    "What activities did I do September 24 2023 in the OpenTracks app? "
    "Answer with the activity type only. If there are multiple types, "
    "format your answer in a comma separated list."
)
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
        "expected_outcome": (
            "The overflow menu opens to reveal inspection or edit options "
            "for the activity."
        ),
        "decision_summary": summary,
        "state_delta": [],
        "memory_citations": [],
        "completion_evidence": [],
    }


R72_INITIAL = decision(
    {"type": "tap", "x": 0.5, "y": 0.15},
    (
        "Tap the activity title to open its details and expose the activity "
        "type as readable text."
    ),
)
R72_REPAIR = decision(
    {"type": "tap", "x": 0.410648, "y": 0.93},
    (
        "Tap the verified more options control to access non-commit details "
        "and expose the activity type."
    ),
)


class R72ReplayClient:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []

    def generate(self, **kwargs: Any) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        payload = R72_REPAIR if label.endswith("_repair") else R72_INITIAL
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


class RejectingM0CriticProbe(HistoryPolicy):
    variant = "M0"

    def __init__(self) -> None:
        self.controller_candidates: list[bool | None] = []
        self.critic_call_count = 0

    def adjudicate_action(
        self,
        decision: dict[str, Any],
        **kwargs: Any,
    ) -> CompletionAdjudication:
        del decision
        candidate = kwargs["consequential_action_candidate"]
        self.controller_candidates.append(candidate)
        if candidate is False:
            return CompletionAdjudication()
        self.critic_call_count += 1
        return CompletionAdjudication(
            accepted=False,
            error="Action critic rejected commit: synthetic rejection",
        )


def active_guard() -> ProtocolV2DecisionGuard:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal=GOAL)
    guard.target_date_row_count = 2
    guard.target_row_detail_required = True
    guard.target_row_visit_keys = ["target-row-y:0.834"]
    guard.active_target_row_visit_key = "target-row-y:0.834"
    guard.requested_answer_role = "activity type"
    return guard


def assessment_for(action: dict[str, Any], elements: list[dict]) -> dict:
    return requested_field_value_assessment(
        GOAL,
        elements,
        decision(action, "Inspect the current detail."),
        screen_width=1080,
        screen_height=2400,
    )


def test_r73_replays_exact_r72_repair_without_launching_false_critic() -> None:
    assert sha256(R72_REPORT.read_bytes()).hexdigest() == R72_REPORT_SHA256
    assert sha256(R72_DETAIL_SCREENSHOT.read_bytes()).hexdigest() == (
        "999c61e1b4ff6c414de1b7090803de4532c9e8d6db3809914f9aaf03660730cf"
    )
    client = R72ReplayClient()
    policy = RejectingM0CriticProbe()
    assert FullRavenMemoryPolicyV2._is_consequential_action(R72_REPAIR)
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_model_calls=3,
        history_policy=policy,
        action_schema_path=ACTION_SCHEMA,
        decision_guard=active_guard(),
        protocol_v2=True,
        protocol_v2_2=True,
    )

    parsed, calls, meta = controller._call_and_parse(
        image_path=R72_DETAIL_SCREENSHOT,
        page_semantic_sha256=(
            "3bc67c3ee126f003b18e50095368b222d3534511a47f94e3277fc1257fdd546b"
        ),
        destination_picker_is_active=False,
        ui_elements=[MORE_OPTIONS],
        screen_width=1080,
        screen_height=2400,
        task_goal=GOAL,
        user_prompt="ORIGINAL",
        episode_id="r73-r72-detail-replay",
        step=5,
        model_call_count=0,
    )

    assert len(calls) == 2
    assert len(client.requests) == 2
    assert parsed == R72_REPAIR
    assert meta["first_pass"] is False
    assert meta["model_repair_used"] is True
    assert meta["action_adjudications"] == []
    assert policy.controller_candidates == [False]
    assert policy.critic_call_count == 0
    field = meta["requested_field_value_assessment"]
    assert field["inspection_control_hit"] is True
    assert field["mutation_control_hit"] is False
    assert field["requested_field_control_hit"] is False


def test_r73_override_requires_exact_active_detail_inspection_hit() -> None:
    guard = active_guard()
    unverified = assessment_for(
        {"type": "tap", "x": 0.5, "y": 0.15},
        [MORE_OPTIONS],
    )
    assert _verified_active_detail_inspection_action(
        protocol_v2_2=True,
        decision_guard=guard,
        decision=R72_INITIAL,
        requested_field_assessment=unverified,
    ) is False

    verified = assessment_for(R72_REPAIR["action"], [MORE_OPTIONS])
    assert _verified_active_detail_inspection_action(
        protocol_v2_2=True,
        decision_guard=guard,
        decision=R72_REPAIR,
        requested_field_assessment=verified,
    ) is True

    guard.active_target_row_visit_key = None
    assert _verified_active_detail_inspection_action(
        protocol_v2_2=True,
        decision_guard=guard,
        decision=R72_REPAIR,
        requested_field_assessment=verified,
    ) is False


def test_r73_override_never_applies_to_delete_or_field_selector() -> None:
    guard = active_guard()
    delete = {
        "text": "Delete",
        "is_visible": True,
        "is_clickable": True,
        "is_enabled": True,
        "bbox": {
            "x_min": 0.0,
            "x_max": 0.476852,
            "y_min": 0.737917,
            "y_max": 0.790417,
        },
    }
    delete_action = {"type": "tap", "x": 0.238426, "y": 0.764167}
    delete_assessment = assessment_for(delete_action, [MORE_OPTIONS, delete])
    assert delete_assessment["mutation_control_hit"] is True
    assert _verified_active_detail_inspection_action(
        protocol_v2_2=True,
        decision_guard=guard,
        decision=decision(delete_action, "Delete the activity."),
        requested_field_assessment=delete_assessment,
    ) is False

    overlapping_selector = dict(assessment_for(R72_REPAIR["action"], [MORE_OPTIONS]))
    overlapping_selector["requested_field_control_hit"] = True
    assert _verified_active_detail_inspection_action(
        protocol_v2_2=True,
        decision_guard=guard,
        decision=R72_REPAIR,
        requested_field_assessment=overlapping_selector,
    ) is False


def test_r73_override_is_protocol_v2_2_only() -> None:
    verified = assessment_for(R72_REPAIR["action"], [MORE_OPTIONS])
    assert _verified_active_detail_inspection_action(
        protocol_v2_2=False,
        decision_guard=active_guard(),
        decision=R72_REPAIR,
        requested_field_assessment=verified,
    ) is False
