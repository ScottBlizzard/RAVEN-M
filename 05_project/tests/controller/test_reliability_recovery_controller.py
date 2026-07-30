from __future__ import annotations

import json
from pathlib import Path

from raven_m.controller.episode_controller import EpisodeController
from raven_m.controller.protocol_v2_guard import ProtocolV2DecisionGuard
from raven_m.models.transformers_client import ModelCall


class RepairSequenceClient:
    def __init__(self, initial: dict, repair: dict) -> None:
        self.initial = initial
        self.repair = repair
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        is_repair = kwargs["call_label"].endswith("_repair")
        decision = self.repair if is_repair else self.initial
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


def controller_for(client: RepairSequenceClient) -> EpisodeController:
    root = Path(__file__).resolve().parents[2]
    return EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2",
        max_model_calls=2,
        action_schema_path=root / "schemas/action.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
    )


def call_and_parse(
    controller: EpisodeController,
    *,
    tmp_path: Path,
    task_goal: str,
    ui_elements: list[dict],
) -> tuple[dict, list[ModelCall], dict]:
    return controller._call_and_parse(
        image_path=tmp_path / "screen.png",
        page_semantic_sha256="same",
        destination_picker_is_active=False,
        ui_elements=ui_elements,
        screen_width=1080,
        screen_height=2400,
        task_goal=task_goal,
        user_prompt="ORIGINAL",
        episode_id="reliability-recovery-fixture",
        step=0,
        model_call_count=0,
    )


def test_controller_repairs_redundant_focused_empty_tap_to_type(
    tmp_path: Path,
) -> None:
    initial = {
        "status": "continue",
        "action": {"type": "tap", "x": 0.5, "y": 0.18},
        "expected_outcome": "The Name field is focused.",
        "decision_summary": "Tap the Name field again to ensure focus.",
        "state_delta": [],
        "memory_citations": [],
    }
    repair = {
        "status": "continue",
        "action": {
            "type": "type_text",
            "text": "Educational",
            "text_origin": "task_literal",
            "source_memory_ids": [],
            "clear_text": False,
        },
        "expected_outcome": "The Name field contains Educational.",
        "decision_summary": "Type Educational into the focused Name field.",
        "state_delta": [],
        "memory_citations": [],
    }
    client = RepairSequenceClient(initial, repair)
    controller = controller_for(client)
    decision, calls, meta = call_and_parse(
        controller,
        tmp_path=tmp_path,
        task_goal="Enter Educational in the Name field.",
        ui_elements=[
            {
                "text": "",
                "is_visible": True,
                "is_enabled": True,
                "is_editable": True,
                "is_focused": True,
                "bbox": {
                    "x_min": 0.1,
                    "x_max": 0.9,
                    "y_min": 0.1,
                    "y_max": 0.25,
                },
            }
        ],
    )
    assert len(calls) == 2
    assert meta["model_repair_used"]
    assert meta["initial_validation_error"].startswith(
        "FOCUSED_EMPTY_TAP_GUARD:"
    )
    assert decision["action"] == repair["action"]
    assert "action.type=type_text" in client.requests[1]["user_prompt"]


def test_controller_repairs_exact_repeat_after_unverified_progress(
    tmp_path: Path,
) -> None:
    repeated = {"type": "tap", "x": 0.5, "y": 0.34}
    initial = {
        "status": "continue",
        "action": repeated,
        "expected_outcome": "The control opens.",
        "decision_summary": "Tap the same control again.",
        "state_delta": [],
        "memory_citations": [],
    }
    repair = {
        "status": "continue",
        "action": {
            "type": "swipe",
            "x": 0.8,
            "y": 0.34,
            "x2": 0.2,
            "y2": 0.34,
            "duration_ms": 500,
        },
        "expected_outcome": "Additional options become visible.",
        "decision_summary": "Swipe left to reveal more options.",
        "state_delta": [],
        "memory_citations": [],
    }
    client = RepairSequenceClient(initial, repair)
    controller = controller_for(client)
    assert controller.decision_guard is not None
    controller.decision_guard.observe_transition(
        before_sha256="same",
        action=repeated,
        after_sha256="same",
        claimed_unverified_progress=True,
    )
    decision, calls, meta = call_and_parse(
        controller,
        tmp_path=tmp_path,
        task_goal="Reveal the requested option.",
        ui_elements=[],
    )
    assert len(calls) == 2
    assert meta["model_repair_used"]
    assert meta["initial_validation_error"].startswith("LOOP_GUARD:")
    assert decision["action"] == repair["action"]
    assert "materially different visible control" in (
        client.requests[1]["user_prompt"]
    )
