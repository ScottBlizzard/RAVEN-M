from __future__ import annotations

import json

import pytest

from raven_m.actions.schema import ActionValidationError, parse_action_response


def decision(action: dict | None, status: str = "continue") -> dict:
    return {
        "status": status,
        "action": action,
        "expected_outcome": "A visible screen change.",
        "decision_summary": "The target is visible.",
        "state_delta": [],
        "memory_citations": [],
    }


@pytest.mark.parametrize(
    "action",
    [
        {"type": "tap", "x": 0.5, "y": 0.25},
        {
            "type": "swipe",
            "x": 0.5,
            "y": 0.8,
            "x2": 0.5,
            "y2": 0.2,
            "duration_ms": 500,
        },
        {
            "type": "type_text",
            "text": "Alice",
            "x": 0.4,
            "y": 0.3,
            "clear_text": True,
        },
        {"type": "press_back"},
        {"type": "open_app", "app_name": "Contacts"},
        {"type": "wait", "duration_ms": 1000},
    ],
)
def test_valid_actions(action: dict) -> None:
    parsed = parse_action_response(json.dumps(decision(action)))
    assert parsed.first_pass
    assert parsed.decision["action"] == action


def test_done_requires_null_action() -> None:
    parsed = parse_action_response(json.dumps(decision(None, status="done")))
    assert parsed.decision["status"] == "done"
    with pytest.raises(ActionValidationError):
        parse_action_response(
            json.dumps(decision({"type": "press_home"}, status="done"))
        )


def test_out_of_bounds_coordinate_is_rejected() -> None:
    with pytest.raises(ActionValidationError):
        parse_action_response(
            json.dumps(decision({"type": "tap", "x": 1.01, "y": 0.5}))
        )


def test_wrapped_json_is_not_counted_as_first_pass() -> None:
    raw = "```json\n" + json.dumps(decision({"type": "press_back"})) + "\n```"
    parsed = parse_action_response(raw)
    assert not parsed.first_pass
    assert parsed.extraction_used


def test_b0_memory_fields_must_be_empty() -> None:
    value = decision({"type": "press_back"})
    value["memory_citations"] = ["m1"]
    with pytest.raises(ActionValidationError):
        parse_action_response(json.dumps(value))
