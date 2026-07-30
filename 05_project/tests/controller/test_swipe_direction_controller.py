from __future__ import annotations

import json
from pathlib import Path

from raven_m.controller.episode_controller import EpisodeController
from raven_m.models.transformers_client import ModelCall


class DirectionRepairClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        repair = kwargs["call_label"].endswith("_repair")
        action = {
            "type": "swipe",
            "x": 0.8 if repair else 0.5,
            "y": 0.35 if repair else 0.34,
            "x2": 0.2 if repair else 0.5,
            "y2": 0.35 if repair else 0.15,
            "duration_ms": 500,
        }
        decision = {
            "status": "continue",
            "action": action,
            "expected_outcome": "More options become visible.",
            "decision_summary": "Swipe left to reveal more options.",
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


def call_and_parse(
    controller: EpisodeController,
    *,
    tmp_path: Path,
) -> tuple[dict, list[ModelCall], dict]:
    return controller._call_and_parse(
        image_path=tmp_path / "screen.png",
        page_semantic_sha256="0" * 64,
        destination_picker_is_active=False,
        ui_elements=[],
        screen_width=1080,
        screen_height=2400,
        task_goal="Reveal more options",
        user_prompt="ORIGINAL",
        episode_id="direction-fixture",
        step=0,
        model_call_count=0,
    )


def test_protocol_v2_repairs_declared_left_actual_up(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    client = DirectionRepairClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2",
        max_model_calls=2,
        action_schema_path=root / "schemas/action.v2.schema.json",
        protocol_v2=True,
    )
    decision, calls, meta = call_and_parse(controller, tmp_path=tmp_path)
    assert len(calls) == 2
    assert meta["model_repair_used"]
    assert meta["initial_validation_error"].startswith(
        "SWIPE_DIRECTION_GUARD:"
    )
    assert decision["action"] == {
        "type": "swipe",
        "x": 0.8,
        "y": 0.35,
        "x2": 0.2,
        "y2": 0.35,
        "duration_ms": 500,
    }
    repair_prompt = client.requests[1]["user_prompt"]
    assert "sentence and numeric coordinates declared different directions" in (
        repair_prompt
    )
    assert "left requires x2<x" in repair_prompt


def test_protocol_v1_does_not_apply_direction_guard(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    client = DirectionRepairClient()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v1",
        max_model_calls=2,
        action_schema_path=root / "schemas/action.v2.schema.json",
        protocol_v2=False,
    )
    decision, calls, meta = call_and_parse(controller, tmp_path=tmp_path)
    assert len(calls) == 1
    assert not meta["model_repair_used"]
    assert decision["action"] == {
        "type": "swipe",
        "x": 0.5,
        "y": 0.34,
        "x2": 0.5,
        "y2": 0.15,
        "duration_ms": 500,
    }
