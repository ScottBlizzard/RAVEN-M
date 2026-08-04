from __future__ import annotations

import json

import pytest

from raven_m.role_binding_timing.metrics import score_cell
from raven_m.role_binding_timing.parser import (
    DecisionParseError,
    parse_action,
    parse_grounding,
)


def grounding(target: str = "B") -> dict[str, object]:
    return {
        "phase": "grounding",
        "destination_target_id": target,
        "source_entity_id": "E1",
        "destination_entity_id": "E2",
        "confidence": 0.9,
    }


def action(target: str = "B", grounded: str = "B") -> dict[str, object]:
    return {
        "phase": "action",
        "grounded_destination_target_id": grounded,
        "recalled_value": "PX-4917",
        "action": {"type": "type_text", "target_id": target, "text": "PX-4917"},
        "confidence": 0.7,
    }


def variant() -> dict[str, object]:
    return {
        "source_entity_id": "E1",
        "destination_entity_id": "E2",
        "source_target_id": "A",
        "destination_target_id": "B",
        "destination_widget_role": "input",
        "candidate_targets": [
            {"target_id": "A", "entity_id": "E1", "widget_role": "input"},
            {"target_id": "B", "entity_id": "E2", "widget_role": "input"},
            {"target_id": "C", "entity_id": "E2", "widget_role": "button"},
            {"target_id": "D", "entity_id": "E3", "widget_role": "input"},
        ],
    }


def test_strict_parsers_accept_valid_outputs() -> None:
    parsed_grounding = parse_grounding(
        json.dumps(grounding(), separators=(",", ":")),
        allowed_target_ids={"A", "B", "C", "D"},
    )
    parsed_action = parse_action(
        json.dumps(action(), separators=(",", ":")),
        allowed_target_ids={"A", "B", "C", "D"},
    )
    assert parsed_grounding.value["destination_target_id"] == "B"
    assert parsed_action.value["action"]["target_id"] == "B"


@pytest.mark.parametrize(
    "raw",
    [
        "```json\n{}\n```",
        " {}",
        json.dumps({**grounding(), "extra": 1}),
        json.dumps({**grounding(), "destination_target_id": "Z"}),
    ],
)
def test_grounding_corruptions_fail_closed(raw: str) -> None:
    with pytest.raises(DecisionParseError):
        parse_grounding(raw, allowed_target_ids={"A", "B"})


def test_action_type_text_requires_text_and_known_target() -> None:
    missing = action()
    missing["action"] = {"type": "type_text", "target_id": "B", "text": None}
    with pytest.raises(DecisionParseError):
        parse_action(json.dumps(missing), allowed_target_ids={"A", "B"})
    unknown = action(target="C")
    with pytest.raises(DecisionParseError, match="Unknown action target"):
        parse_action(json.dumps(unknown), allowed_target_ids={"A", "B"})


def test_metric_layers_separate_source_wrong_widget_and_other_entity() -> None:
    correct = score_cell(
        grounding=grounding(),
        action=action(),
        variant=variant(),
        expected_value="PX-4917",
    )
    assert correct.action_target_correct
    assert not correct.wrong_target_first_targeting_action

    source = score_cell(
        grounding=grounding(),
        action=action(target="A"),
        variant=variant(),
        expected_value="PX-4917",
    )
    assert source.source_as_target
    assert source.wrong_target_first_targeting_action

    wrong_widget = score_cell(
        grounding=grounding(),
        action=action(target="C"),
        variant=variant(),
        expected_value="PX-4917",
    )
    assert wrong_widget.correct_target_wrong_widget
    assert not wrong_widget.other_wrong_entity

    other = score_cell(
        grounding=grounding(),
        action=action(target="D", grounded="D"),
        variant=variant(),
        expected_value="PX-4917",
    )
    assert other.other_wrong_entity
    assert other.post_grounding_drift
