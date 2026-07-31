from __future__ import annotations

import json
from pathlib import Path

from raven_m.controller.episode_controller import EpisodeController
from raven_m.controller.protocol_v2_guard import (
    ProtocolV2DecisionGuard,
    bounded_task_repeated_tap_assessment,
)
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


def controller_for(
    client: RepairSequenceClient,
    *,
    protocol_v2_2: bool = False,
) -> EpisodeController:
    root = Path(__file__).resolve().parents[2]
    return EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2",
        max_model_calls=2,
        action_schema_path=root / "schemas/action.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=protocol_v2_2,
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


def test_controller_replays_r61_markers_claim_as_older_history_swipe(
    tmp_path: Path,
) -> None:
    initial = {
        "status": "continue",
        "action": {"type": "tap", "x": 0.84, "y": 0.085},
        "expected_outcome": "Open the date picker for September 24, 2023.",
        "decision_summary": (
            "Tap the location icon in the top app bar to open the date "
            "picker for selecting a specific date."
        ),
        "state_delta": [],
        "memory_citations": [],
    }
    repair = {
        "status": "continue",
        "action": {
            "type": "swipe",
            "x": 0.5,
            "y": 0.8,
            "x2": 0.5,
            "y2": 0.2,
            "duration_ms": 500,
        },
        "expected_outcome": "Older history rows become visible.",
        "decision_summary": "Swipe up through the history toward older rows.",
        "state_delta": [],
        "memory_citations": [],
    }
    client = RepairSequenceClient(initial, repair)
    controller = controller_for(client, protocol_v2_2=True)
    elements = [
        {
            "package_name": "org.example.history",
            "content_description": "Markers",
            "is_visible": True,
            "is_enabled": True,
            "is_clickable": True,
            "bbox": {"x_min": 0.76, "x_max": 0.90,
                     "y_min": 0.05, "y_max": 0.12},
        },
        *[
            {
                "package_name": "org.example.history",
                "text": label,
                "is_visible": True,
                "bbox": {"x_min": 0.05, "x_max": 0.22,
                         "y_min": y, "y_max": y + 0.04},
            }
            for label, y in (("Today", 0.20), ("Friday", 0.44),
                             ("7 Oct", 0.72))
        ],
    ]
    parsed, calls, _ = call_and_parse(
        controller,
        tmp_path=tmp_path,
        task_goal="What happened on September 24 2023?",
        ui_elements=elements,
    )
    assert len(calls) == 2
    assert parsed["action"]["type"] == "swipe"
    assert parsed["action"]["y2"] < parsed["action"]["y"]
    repair_prompt = client.requests[1]["user_prompt"]
    assert "CHRONOLOGICAL_LIST_SCROLL_REPAIR" in repair_prompt
    assert repair_prompt.index("CHRONOLOGICAL_LIST_SCROLL_REPAIR") < (
        repair_prompt.index("ORIGINAL")
    )
    audit = controller.decision_guard.audit_record()
    assert audit["toolbar_affordance_block_count"] == 1
    block = audit["validation_blocks"][0]
    assert block["reason"] == "toolbar_affordance_claim_mismatch"
    assert block["action"]["type"] == "tap"


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
    assert "side by side in a horizontal row or carousel" in (
        client.requests[1]["user_prompt"]
    )


def test_controller_allows_fourth_exact_swipe_after_verified_progress(
    tmp_path: Path,
) -> None:
    swipe = {
        "type": "swipe",
        "x": 0.8,
        "y": 0.34,
        "x2": 0.2,
        "y2": 0.34,
        "duration_ms": 500,
    }
    initial = {
        "status": "continue",
        "action": swipe,
        "expected_outcome": "More categories become visible.",
        "decision_summary": "Continue left through the category row.",
        "state_delta": [],
        "memory_citations": [],
    }
    client = RepairSequenceClient(initial, initial)
    controller = controller_for(client)
    assert controller.decision_guard is not None
    for before, after in (
        ("state-0", "state-1"),
        ("state-1", "state-2"),
        ("state-2", "same"),
    ):
        controller.decision_guard.observe_transition(
            before_sha256=before,
            action=swipe,
            after_sha256=after,
        )
    decision, calls, meta = call_and_parse(
        controller,
        tmp_path=tmp_path,
        task_goal="Select Donation from the horizontal category row.",
        ui_elements=[],
    )
    assert len(calls) == 1
    assert not meta["model_repair_used"]
    assert decision["action"] == swipe
    audit = controller.decision_guard.audit_record()
    assert audit["identical_coordinate_action_count"] == 3
    assert audit["identical_coordinate_no_effect_count"] == 0


def test_controller_allows_fourth_task_bounded_progress_tap(
    tmp_path: Path,
) -> None:
    tap = {"type": "tap", "x": 0.5, "y": 0.208}
    response = {
        "status": "continue",
        "action": tap,
        "expected_outcome": "The next number appears.",
        "decision_summary": "Tap Click Me for the fourth requested value.",
        "state_delta": [],
        "memory_citations": [],
    }
    client = RepairSequenceClient(response, response)
    controller = controller_for(client, protocol_v2_2=True)
    assert controller.decision_guard is not None
    for index in range(3):
        controller.decision_guard.observe_transition(
            before_sha256=f"value-{index}",
            action=tap,
            after_sha256=f"value-{index + 1}",
        )
    decision, calls, meta = call_and_parse(
        controller,
        tmp_path=tmp_path,
        task_goal=(
            "Open the task with Chrome, then click the button 5 times, "
            "remember the numbers displayed, and enter their product."
        ),
        ui_elements=[
            {
                "package_name": "com.android.chrome",
                "class_name": "android.widget.Button",
                "text": "Click Me",
                "is_visible": True,
                "is_enabled": True,
                "is_clickable": True,
                "is_editable": False,
                "bbox": {
                    "x_min": 0.43,
                    "x_max": 0.57,
                    "y_min": 0.18,
                    "y_max": 0.23,
                },
            }
        ],
    )
    assert len(calls) == 1
    assert not meta["model_repair_used"]
    assert decision["action"] == tap
    assessment = meta["bounded_task_repeated_tap_assessment"]
    assert assessment["permitted"]
    assert assessment["proposed_ordinal"] == 4
    assert (
        controller.decision_guard.audit_record()[
            "bounded_task_repeated_tap_override_count"
        ]
        == 1
    )


def test_controller_reconciles_delayed_task_button_progress(
    tmp_path: Path,
) -> None:
    tap = {"type": "tap", "x": 0.5, "y": 0.208}
    response = {
        "status": "continue",
        "action": tap,
        "expected_outcome": "The next number appears.",
        "decision_summary": "Tap Click Me for the next requested value.",
        "state_delta": [],
        "memory_citations": [],
    }
    client = RepairSequenceClient(response, response)
    controller = controller_for(client, protocol_v2_2=True)
    assert controller.decision_guard is not None
    controller.decision_guard.observe_transition(
        before_sha256="immediate-same",
        action=tap,
        after_sha256="immediate-same",
    )
    decision, calls, meta = call_and_parse(
        controller,
        tmp_path=tmp_path,
        task_goal=(
            "Open the task with Chrome, then click the button 5 times, "
            "remember the numbers displayed, and enter their product."
        ),
        ui_elements=[
            {
                "package_name": "com.android.chrome",
                "class_name": "android.widget.Button",
                "text": "Click Me",
                "is_visible": True,
                "is_enabled": True,
                "is_clickable": True,
                "is_editable": False,
                "bbox": {
                    "x_min": 0.43,
                    "x_max": 0.57,
                    "y_min": 0.18,
                    "y_max": 0.23,
                },
            }
        ],
    )
    assert len(calls) == 1
    assert decision["action"] == tap
    assessment = meta["bounded_task_repeated_tap_assessment"]
    assert assessment["deferred_semantic_progress_observed"]
    assert assessment["effective_identical_coordinate_no_effect_count"] == 0
    audit = controller.decision_guard.audit_record()
    assert audit["deferred_semantic_progress_reconciliation_count"] == 1
    assert audit["identical_coordinate_no_effect_count"] == 0


def test_controller_repairs_sixth_tap_to_post_repeat_action(
    tmp_path: Path,
) -> None:
    tap = {"type": "tap", "x": 0.5, "y": 0.208}
    initial = {
        "status": "continue",
        "action": tap,
        "expected_outcome": "The next number appears.",
        "decision_summary": "Tap Click Me for another number.",
        "state_delta": [],
        "memory_citations": [],
    }
    repair = {
        "status": "continue",
        "action": {
            "type": "swipe",
            "x": 0.5,
            "y": 0.8,
            "x2": 0.5,
            "y2": 0.3,
            "duration_ms": 500,
        },
        "expected_outcome": "The result form becomes visible.",
        "decision_summary": "Scroll toward the pending product form.",
        "state_delta": [],
        "memory_citations": [],
    }
    client = RepairSequenceClient(initial, repair)
    controller = controller_for(client, protocol_v2_2=True)
    guard = controller.decision_guard
    assert guard is not None
    goal = (
        "Open the task with Chrome, then click the button 5 times, "
        "remember the numbers displayed, and enter their product."
    )
    values = ["6", "2", "3", "9", "10"]
    button = {
        "package_name": "com.android.chrome",
        "class_name": "android.widget.Button",
        "text": "Click Me",
        "is_visible": True,
        "is_enabled": True,
        "is_clickable": True,
        "is_editable": False,
        "bbox": {
            "x_min": 0.43,
            "x_max": 0.57,
            "y_min": 0.18,
            "y_max": 0.23,
        },
    }
    for ordinal, value in enumerate(values, start=1):
        assessment = bounded_task_repeated_tap_assessment(
            goal,
            [
                button,
                {
                    "package_name": "com.android.chrome",
                    "text": value,
                    "is_visible": True,
                    "is_clickable": False,
                    "is_editable": False,
                },
            ],
            tap,
            prior_identical_coordinate_action_count=(
                guard.identical_coordinate_action_count
            ),
            identical_coordinate_no_effect_count=(
                guard.identical_coordinate_no_effect_count
            ),
            screen_width=1080,
            screen_height=2400,
            transition_context=guard.repeated_tap_transition_context(
                page_sha256=f"before-{ordinal}",
                action=tap,
            ),
        )
        guard.validate_decision(
            {
                "status": "continue",
                "action": tap,
                "memory_citations": [],
            },
            page_sha256=f"before-{ordinal}",
            bounded_task_repeated_tap_assessment=assessment,
        )
        guard.observe_transition(
            before_sha256=f"before-{ordinal}",
            action=tap,
            after_sha256=f"after-{ordinal}",
            bounded_task_repeated_tap_assessment=assessment,
        )
        guard.refresh_verified_task_repeat_progress(
            goal=goal,
            ui_elements=[],
            page_sha256=f"result-{ordinal}",
        )

    decision_value, calls, meta = call_and_parse(
        controller,
        tmp_path=tmp_path,
        task_goal=goal,
        ui_elements=[],
    )
    assert len(calls) == 2
    assert meta["model_repair_used"]
    assert meta["initial_validation_error"].startswith(
        "TASK_REPEAT_COUNT_COMPLETE:"
    )
    assert decision_value["action"] == repair["action"]
    repair_prompt = client.requests[1]["user_prompt"]
    assert "VERIFIED_REPEAT_COMPLETION_REPAIR" in repair_prompt
    assert '"result":"3240"' in repair_prompt
    assert guard.audit_record()[
        "task_repeat_count_complete_block_count"
    ] == 1


def test_user_prompt_marks_verified_repeat_progress_authoritative() -> None:
    progress = {
        "executed_count": 5,
        "requested_repetitions": 5,
        "complete": True,
        "verified_operands": ["6", "2", "3", "9", "10"],
        "operands_complete": True,
        "deterministic_calculation": {
            "operation": "product",
            "result": "3240",
        },
    }
    prompt = EpisodeController._user_prompt(
        goal="Click the button 5 times and enter their product.",
        step=14,
        max_steps=22,
        model_calls=17,
        max_model_calls=54,
        screen_width=1080,
        screen_height=2400,
        previous_outcome="The fifth tap changed the semantic UI.",
        memory_context=(
            '{"summary":"Clicked once; click four more times."}'
        ),
        protocol_v2=True,
        protocol_v2_2=True,
        verified_task_repeat_progress=progress,
    )
    assert "VERIFIED_TASK_REPEAT_PROGRESS" in prompt
    assert "newer and more authoritative" in prompt
    assert '"executed_count":5' in prompt
    assert '"result":"3240"' in prompt
    assert "Never repeat" in prompt


def test_controller_uses_one_step_activation_proof_for_text_repair(
    tmp_path: Path,
) -> None:
    initial_action = {
        "type": "type_text",
        "text": "Educational",
        "text_origin": "task_literal",
        "source_memory_ids": [],
        "x": 0.5,
        "y": 0.18,
        "clear_text": True,
    }
    repaired_action = {
        **initial_action,
        "clear_text": False,
    }
    repaired_action.pop("x")
    repaired_action.pop("y")
    initial = {
        "status": "continue",
        "action": initial_action,
        "expected_outcome": "The Name field contains Educational.",
        "decision_summary": "Type Educational into the Name field.",
        "state_delta": [],
        "memory_citations": [],
    }
    repair = {
        **initial,
        "action": repaired_action,
        "decision_summary": (
            "Type Educational into the previously activated Name field."
        ),
    }
    client = RepairSequenceClient(initial, repair)
    controller = controller_for(client)
    assert controller.decision_guard is not None
    controller.decision_guard.mark_input_activation_repair(
        {"type": "tap", "x": 0.5, "y": 0.18}
    )
    decision, calls, meta = call_and_parse(
        controller,
        tmp_path=tmp_path,
        task_goal="Enter Educational in the Name field.",
        ui_elements=[
            {
                "text": "Name",
                "is_visible": True,
                "is_enabled": True,
                "is_editable": True,
                "is_focused": False,
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
    assert "POST_ACTIVATION_CLEAR_TEXT_GUARD" in (
        meta["initial_validation_error"]
    )
    assert decision["action"] == repaired_action
    repair_prompt = client.requests[1]["user_prompt"]
    assert "keep action.type=type_text" in repair_prompt
    assert "Omit x and y" in repair_prompt
    assert "set clear_text=false" in repair_prompt
    assert "Educational" not in repair_prompt.split(
        "VALIDATION_ERROR:",
        maxsplit=1,
    )[0]
