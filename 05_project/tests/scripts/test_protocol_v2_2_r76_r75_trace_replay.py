from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import pytest

from raven_m.controller.episode_controller import (
    EpisodeController,
    ModelOutputInvalid,
)
from raven_m.controller.protocol_v2_guard import (
    ProtocolV2DecisionGuard,
    dated_list_answer_assessment,
)
from raven_m.models.transformers_client import ModelCall


ROOT = Path(__file__).resolve().parents[3]
R75_REPORT = ROOT / "reports/protocol_v2_2_r75_h17_candidate_stopped.json"
R75_REPORT_SHA256 = (
    "ca688dfa080968300d2aff9b7d4361ab8634de7589ee88da87f47fb108d39c01"
)
R75_EPISODE = (
    ROOT
    / "runs/protocol_v2_2_development/"
    "hard_micro_v2_2_seed20260730_r75_candidate_"
    "development_smoke_sequence_2/episodes/"
    "02_H17_M0_SportsTrackerActivitiesOnDate_seed20260730"
)
LIST_SCREENSHOT = R75_EPISODE / "step_003_before.png"
ACTION_SCHEMA = ROOT / "05_project/schemas/action.raven.v2.schema.json"
GOAL = (
    "What activities did I do September 24 2023 in the OpenTracks app? "
    "Answer with the activity type only. If there are multiple types, "
    "format your answer in a comma separated list."
)
TARGET_CENTERS = [0.747292, 0.834375]
SWIPE_DECISION = {
    "status": "continue",
    "action": {
        "type": "swipe",
        "x": 0.5,
        "y": 0.8,
        "x2": 0.5,
        "y2": 0.2,
        "duration_ms": 500,
    },
    "expected_outcome": "Older activity rows become visible.",
    "decision_summary": "Continue scrolling toward older activities.",
    "state_delta": [],
    "memory_citations": [],
    "completion_evidence": [],
}


def tap_decision(y: float, *, x: float = 0.5) -> dict[str, Any]:
    return {
        "status": "continue",
        "action": {"type": "tap", "x": x, "y": y},
        "expected_outcome": "The selected target row detail opens.",
        "decision_summary": "Open one visible target-date row.",
        "state_delta": [],
        "memory_citations": [],
        "completion_evidence": [],
    }


def list_elements(*, distinct_identity: bool = True) -> list[dict[str, Any]]:
    first = "Upper target identity" if distinct_identity else "Shared target"
    second = "Lower target identity" if distinct_identity else "Shared target"
    elements: list[dict[str, Any]] = []
    for title, date, center in (
        ("Earlier visible record", "1 Oct", 0.66),
        (first, "24 Sep", TARGET_CENTERS[0]),
        (second, "24 Sep", TARGET_CENTERS[1]),
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
        episode_id="r76-r75-repair-replay",
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


class RepairClient:
    def __init__(
        self,
        repair: dict[str, Any],
        *,
        initial: dict[str, Any] = SWIPE_DECISION,
    ) -> None:
        self.initial = initial
        self.repair = repair
        self.requests: list[dict[str, Any]] = []

    def generate(self, **kwargs: Any) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        payload = self.repair if label.endswith("_repair") else self.initial
        return model_call(label, payload)


def controller(
    client: RepairClient,
    *,
    guard: ProtocolV2DecisionGuard | None = None,
) -> EpisodeController:
    value = guard or ProtocolV2DecisionGuard()
    if guard is None:
        value.reset(goal=GOAL)
    return EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2.2",
        max_model_calls=2,
        action_schema_path=ACTION_SCHEMA,
        decision_guard=value,
        protocol_v2=True,
        protocol_v2_2=True,
    )


def call(
    value: EpisodeController,
    *,
    elements: list[dict[str, Any]] | None = None,
) -> tuple[dict, list[ModelCall], dict]:
    return value._call_and_parse(
        image_path=LIST_SCREENSHOT,
        page_semantic_sha256=(
            "8095b9ed6872f7192aebaebd86781114778bb6aa65fe5dafddc4295e9dd535cc"
        ),
        destination_picker_is_active=False,
        ui_elements=elements or list_elements(),
        screen_width=1080,
        screen_height=2400,
        task_goal=GOAL,
        user_prompt="ORIGINAL",
        episode_id="r76-r75-repair-replay",
        step=3,
        model_call_count=0,
    )


def test_r76_replays_exact_r75_midpoint_as_one_unique_candidate() -> None:
    assert sha256(R75_REPORT.read_bytes()).hexdigest() == R75_REPORT_SHA256
    assert sha256(LIST_SCREENSHOT.read_bytes()).hexdigest() == (
        "f8084ee085fd3e30f0f68412f9d7b6a4fb1f71186d5fb6a550fb37dec1d6258a"
    )
    report = json.loads(R75_REPORT.read_text(encoding="utf-8"))
    repair = tap_decision(0.775)
    assert report["repair_contract_bottleneck"]["repair_model_action"] == (
        repair["action"]
    )
    assessment = dated_list_answer_assessment(
        GOAL,
        list_elements(),
        repair,
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["target_row_tap_candidate_indices"] == [0]
    assert assessment["target_row_tap_index"] == 0
    assert assessment["target_row_tap_center"] == TARGET_CENTERS[0]
    assert assessment["target_row_tap_offset"] == 0.027708
    assert assessment["target_row_tap_precisely_aligned"] is False


def test_r76_normalizes_exact_r75_repair_without_another_model_call() -> None:
    client = RepairClient(tap_decision(0.775))
    value = controller(client)
    parsed, calls, meta = call(value)
    assert len(calls) == 2
    assert json.loads(calls[1].content)["action"] == {
        "type": "tap",
        "x": 0.5,
        "y": 0.775,
    }
    assert parsed["action"] == {
        "type": "tap",
        "x": 0.5,
        "y": TARGET_CENTERS[0],
    }
    normalization = meta["target_row_repair_normalization"]
    assert normalization["original_action"] == {
        "type": "tap",
        "x": 0.5,
        "y": 0.775,
    }
    assert normalization["routed_action"] == parsed["action"]
    assert normalization["target_row_tap_candidate_indices"] == [0]
    assert normalization["additional_model_calls"] == 0
    assert value.decision_guard is not None
    assert value.decision_guard.target_row_visit_keys == [
        "target-row-y:0.747"
    ]


def test_r76_does_not_normalize_a_two_row_overlap() -> None:
    midpoint = sum(TARGET_CENTERS) / 2
    repair = tap_decision(midpoint)
    assessment = dated_list_answer_assessment(
        GOAL,
        list_elements(),
        repair,
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["target_row_tap_candidate_indices"] == [0, 1]
    value = controller(RepairClient(repair))
    with pytest.raises(ModelOutputInvalid) as captured:
        call(value)
    assert captured.value.repair_error.startswith(
        "REPAIR_CONTRACT_GUARD:"
    )
    assert captured.value.target_row_repair_normalization is None


def test_r76_does_not_normalize_an_off_content_side_tap() -> None:
    value = controller(RepairClient(tap_decision(0.775, x=0.95)))
    with pytest.raises(ModelOutputInvalid) as captured:
        call(value)
    assert captured.value.repair_error.startswith(
        "REPAIR_CONTRACT_GUARD:"
    )
    assert captured.value.target_row_repair_normalization is None


def test_r76_does_not_normalize_without_row_specific_identity() -> None:
    value = controller(RepairClient(tap_decision(0.775)))
    with pytest.raises(ModelOutputInvalid) as captured:
        call(value, elements=list_elements(distinct_identity=False))
    assert captured.value.repair_error.startswith(
        "REPAIR_CONTRACT_GUARD:"
    )
    assert captured.value.target_row_repair_normalization is None


def test_r76_exact_repair_passes_without_normalization() -> None:
    client = RepairClient(tap_decision(TARGET_CENTERS[0]))
    value = controller(client)
    parsed, calls, meta = call(value)
    assert len(calls) == 2
    assert parsed["action"]["y"] == TARGET_CENTERS[0]
    assert "target_row_repair_normalization" not in meta


def test_r76_normalized_unvisited_repair_cannot_reopen_visited_row() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal=GOAL)
    guard.target_date_row_count = 2
    guard.target_row_detail_required = True
    guard.target_row_visit_keys = ["target-row-y:0.747"]
    initial = tap_decision(TARGET_CENTERS[0])
    value = controller(
        RepairClient(tap_decision(0.775), initial=initial),
        guard=guard,
    )
    with pytest.raises(ModelOutputInvalid) as captured:
        call(value)
    assert captured.value.initial_error.startswith(
        "TARGET_ROW_UNVISITED_GUARD:"
    )
    assert captured.value.repair_error.startswith(
        "REPAIR_CONTRACT_GUARD:"
    )
    normalization = captured.value.target_row_repair_normalization
    assert normalization["routed_action"]["y"] == TARGET_CENTERS[0]
    assert guard.target_row_visit_keys == ["target-row-y:0.747"]


def test_r76_normalization_sources_are_task_and_answer_agnostic() -> None:
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
