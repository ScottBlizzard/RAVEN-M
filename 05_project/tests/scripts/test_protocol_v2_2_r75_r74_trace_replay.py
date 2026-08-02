from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import pytest

from raven_m.actions.schema import ActionValidationError
from raven_m.controller.episode_controller import (
    EpisodeController,
    ModelOutputInvalid,
)
from raven_m.controller.protocol_v2_guard import (
    ProtocolV2DecisionGuard,
    dated_list_answer_assessment,
    target_row_detail_identity_assessment,
)
from raven_m.models.transformers_client import ModelCall


ROOT = Path(__file__).resolve().parents[3]
R74_REPORT = ROOT / "reports/protocol_v2_2_r74_h17_candidate_stopped.json"
R74_REPORT_SHA256 = (
    "129c8f7c34c0431b28c8c3aced6c7706944ff40cb75ccf44b91a4918ce48f775"
)
R74_EPISODE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r74_candidate_"
    "development_smoke_sequence_2/episodes/"
    "02_H17_M0_SportsTrackerActivitiesOnDate_seed20260730"
)
LIST_SCREENSHOT = R74_EPISODE / "step_006_before.png"
ACTION_SCHEMA = ROOT / "05_project/schemas/action.raven.v2.schema.json"
GOAL = (
    "What activities did I do September 24 2023 in the OpenTracks app? "
    "Answer with the activity type only. If there are multiple types, "
    "format your answer in a comma separated list."
)
TARGET_CENTERS = [0.747292, 0.834375]
R74_AMBIGUOUS_DECISION = {
    "status": "continue",
    "action": {"type": "tap", "x": 0.5, "y": 0.805},
    "expected_outcome": (
        "The lower target-date row opens for read-only inspection."
    ),
    "decision_summary": (
        "Tap the visible lower target-date content row to inspect it."
    ),
    "state_delta": [],
    "memory_citations": [],
    "completion_evidence": [],
}
ROUTED_LOWER_DECISION = {
    **R74_AMBIGUOUS_DECISION,
    "action": {"type": "tap", "x": 0.5, "y": 0.834375},
    "decision_summary": (
        "Use the exact controller-routed center for the intended row."
    ),
}
ROUTED_UPPER_DECISION = {
    **R74_AMBIGUOUS_DECISION,
    "action": {"type": "tap", "x": 0.5, "y": 0.747292},
    "decision_summary": "Use a different target row center.",
}
BACK_DECISION = {
    "status": "continue",
    "action": {"type": "press_back"},
    "expected_outcome": "The target-date list becomes visible again.",
    "decision_summary": "Return safely to the target-date list.",
    "state_delta": [],
    "memory_citations": [],
    "completion_evidence": [],
}


def list_elements() -> list[dict[str, Any]]:
    elements: list[dict[str, Any]] = []
    for title, date, center in (
        ("Earlier visible record", "1 Oct", 0.66),
        ("Upper target identity", "24 Sep", TARGET_CENTERS[0]),
        ("Lower target identity", "24 Sep", TARGET_CENTERS[1]),
    ):
        elements.extend(
            [
                {
                    "text": title,
                    "is_visible": True,
                    "bbox": {
                        "x_min": 0.08,
                        "x_max": 0.70,
                        "y_min": center - 0.025,
                        "y_max": center + 0.025,
                    },
                },
                {
                    "text": date,
                    "is_visible": True,
                    "bbox": {
                        "x_min": 0.88,
                        "x_max": 0.98,
                        "y_min": center - 0.025,
                        "y_max": center + 0.025,
                    },
                },
                {
                    "is_visible": True,
                    "is_enabled": True,
                    "is_clickable": True,
                    "bbox": {
                        "x_min": 0.02,
                        "x_max": 0.98,
                        "y_min": center - 0.04,
                        "y_max": center + 0.04,
                    },
                },
            ]
        )
    return elements


def model_call(label: str, decision: dict[str, Any]) -> ModelCall:
    return ModelCall(
        call_id=label,
        episode_id="r75-r74-row-identity-replay",
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


class PreciseRepairClient:
    def __init__(self, repair: dict[str, Any] = ROUTED_LOWER_DECISION) -> None:
        self.repair = repair
        self.requests: list[dict[str, Any]] = []

    def generate(self, **kwargs: Any) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        payload = self.repair if label.endswith("_repair") else R74_AMBIGUOUS_DECISION
        return model_call(label, payload)


def guard() -> ProtocolV2DecisionGuard:
    value = ProtocolV2DecisionGuard()
    value.reset(goal=GOAL)
    return value


def list_assessment(
    decision: dict[str, Any],
) -> dict[str, Any]:
    return dated_list_answer_assessment(
        GOAL,
        list_elements(),
        decision,
        screen_width=1080,
        screen_height=2400,
    )


def test_r75_replays_exact_r74_ambiguous_tap_as_not_precise() -> None:
    assert sha256(R74_REPORT.read_bytes()).hexdigest() == R74_REPORT_SHA256
    assert sha256(LIST_SCREENSHOT.read_bytes()).hexdigest() == (
        "f15f1ca098c9ba6c5c89a761e526d9e18b62de12c14602dcbeb57290bb662349"
    )
    report = json.loads(R74_REPORT.read_text(encoding="utf-8"))
    assert report["row_identity_bottleneck"]["first_row_action"] == (
        R74_AMBIGUOUS_DECISION["action"]
    )
    assessment = list_assessment(R74_AMBIGUOUS_DECISION)
    assert assessment["target_row_centers"] == TARGET_CENTERS
    assert assessment["target_row_tap_index"] == 1
    assert assessment["target_row_tap_center"] == 0.834375
    assert assessment["target_row_tap_offset"] == -0.029375
    assert assessment["tap_on_content_side"] is True
    assert assessment["target_row_tap_precisely_aligned"] is False
    assert assessment["target_row_tap_permitted"] is False
    assert assessment["target_row_tap_routed_action"] == (
        ROUTED_LOWER_DECISION["action"]
    )


def test_r75_exact_r74_tap_repairs_only_to_same_routed_row() -> None:
    value = guard()
    client = PreciseRepairClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_model_calls=2,
        action_schema_path=ACTION_SCHEMA,
        decision_guard=value,
        protocol_v2=True,
        protocol_v2_2=True,
    )
    parsed, calls, meta = controller._call_and_parse(
        image_path=LIST_SCREENSHOT,
        page_semantic_sha256=(
            "8095b9ed6872f7192aebaebd86781114778bb6aa65fe5dafddc4295e9dd535cc"
        ),
        destination_picker_is_active=False,
        ui_elements=list_elements(),
        screen_width=1080,
        screen_height=2400,
        task_goal=GOAL,
        user_prompt="ORIGINAL",
        episode_id="r75-r74-row-identity-replay",
        step=6,
        model_call_count=0,
    )
    assert parsed == ROUTED_LOWER_DECISION
    assert len(calls) == 2
    assert meta["initial_validation_error"].startswith(
        "TARGET_ROW_PRECISE_TAP_GUARD:"
    )
    assert "TARGET_DATE_ROW_EXACT_CENTER_TAP_REQUIRED:" in meta[
        "initial_validation_error"
    ]
    assert value.active_target_row_visit_key == "target-row-y:0.834"
    assert value.target_row_visit_keys == ["target-row-y:0.834"]
    assert value.active_target_row_expected_identity_labels() == [
        "Lower target identity"
    ]


def test_r75_repair_cannot_switch_to_a_different_target_row() -> None:
    value = guard()
    controller = EpisodeController(
        client=PreciseRepairClient(ROUTED_UPPER_DECISION),  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_model_calls=2,
        action_schema_path=ACTION_SCHEMA,
        decision_guard=value,
        protocol_v2=True,
        protocol_v2_2=True,
    )
    with pytest.raises(ModelOutputInvalid) as captured:
        controller._call_and_parse(
            image_path=LIST_SCREENSHOT,
            page_semantic_sha256="8" * 64,
            destination_picker_is_active=False,
            ui_elements=list_elements(),
            screen_width=1080,
            screen_height=2400,
            task_goal=GOAL,
            user_prompt="ORIGINAL",
            episode_id="r75-r74-wrong-row-repair",
            step=6,
            model_call_count=0,
        )
    assert captured.value.initial_error.startswith(
        "TARGET_ROW_PRECISE_TAP_GUARD:"
    )
    assert captured.value.repair_error.startswith(
        "REPAIR_CONTRACT_GUARD:"
    )
    assert value.target_row_visit_keys == []


def test_r75_wrong_detail_rolls_back_visit_and_requires_back() -> None:
    value = guard()
    value.validate_decision(
        ROUTED_LOWER_DECISION,
        page_sha256="list",
        dated_list_answer_assessment=list_assessment(
            ROUTED_LOWER_DECISION
        ),
    )
    expected = value.active_target_row_expected_identity_labels()
    mismatch = target_row_detail_identity_assessment(
        [{"text": "Upper target identity", "is_visible": True}],
        expected_identity_labels=expected,
    )
    with pytest.raises(
        ActionValidationError,
        match="TARGET_ROW_IDENTITY_MISMATCH_BACK_REQUIRED",
    ):
        value.validate_decision(
            {
                **ROUTED_LOWER_DECISION,
                "action": {"type": "tap", "x": 0.4, "y": 0.9},
            },
            page_sha256="wrong-detail",
            dated_list_answer_assessment={},
            requested_field_value_assessment={
                "explicit_value_visible": False,
                "inspection_control_hit": True,
            },
            target_row_detail_identity_assessment=mismatch,
        )
    assert value.target_row_visit_keys == []
    assert value.active_target_row_visit_key is None
    assert value.target_row_identity_mismatch_count == 1
    assert value.target_row_identity_mismatch_pending_visit_key == (
        "target-row-y:0.834"
    )
    value.validate_decision(
        BACK_DECISION,
        page_sha256="wrong-detail",
        dated_list_answer_assessment={},
        target_row_detail_identity_assessment=mismatch,
    )
    assert value.target_row_return_pending_visit_key == (
        "target-row-y:0.834"
    )
    assert value.target_row_return_back_count == 1
    assert value.target_row_visit_keys == []


def test_r75_correct_detail_confirms_identity_before_frame_capture() -> None:
    value = guard()
    value.validate_decision(
        ROUTED_LOWER_DECISION,
        page_sha256="list",
        dated_list_answer_assessment=list_assessment(
            ROUTED_LOWER_DECISION
        ),
    )
    expected = value.active_target_row_expected_identity_labels()
    matched = target_row_detail_identity_assessment(
        [{"text": "Lower target identity", "is_visible": True}],
        expected_identity_labels=expected,
    )
    inspect = {
        **ROUTED_LOWER_DECISION,
        "action": {"type": "tap", "x": 0.4, "y": 0.9},
    }
    value.validate_decision(
        inspect,
        page_sha256="correct-detail",
        dated_list_answer_assessment={},
        requested_field_value_assessment={
            "explicit_value_visible": False,
            "inspection_control_hit": True,
        },
        target_row_detail_identity_assessment=matched,
    )
    assert value.target_row_identity_confirmed_visit_keys == [
        "target-row-y:0.834"
    ]
    assert value.target_row_identity_confirmation_count == 1
    value.validate_decision(
        BACK_DECISION,
        page_sha256="explicit-field",
        dated_list_answer_assessment={},
        dated_row_detail_frame={
            "visit_key": "target-row-y:0.834",
            "path": "C:/evidence/lower.png",
            "sha256": "a" * 64,
            "source_path": "C:/evidence/lower-source.png",
            "source_sha256": "b" * 64,
            "requested_field_evidence_explicit": True,
        },
        requested_field_value_assessment={
            "explicit_value_visible": True,
        },
        target_row_detail_identity_assessment=matched,
    )
    assert [
        item["visit_key"] for item in value.target_row_detail_frames
    ] == ["target-row-y:0.834"]
    assert value.target_row_return_pending_visit_key == (
        "target-row-y:0.834"
    )


def test_r75_identity_sources_are_task_and_answer_agnostic() -> None:
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
        "cycling",
        "swimming",
        "target-row-y:0.747",
        "target-row-y:0.834",
    ):
        assert forbidden not in source
