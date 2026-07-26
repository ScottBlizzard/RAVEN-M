from __future__ import annotations

import json
from pathlib import Path

import pytest

from raven_m.actions.schema import ActionValidationError, parse_action_response


ROOT = Path(__file__).resolve().parents[2]
B0_SCHEMA = ROOT / "schemas/action.v2.schema.json"
RAVEN_SCHEMA = ROOT / "schemas/action.raven.v2.schema.json"


def b0(action: dict | None, status: str) -> dict:
    return {
        "status": status,
        "action": action,
        "expected_outcome": "The requested result is submitted.",
        "decision_summary": "Submit the visible result.",
        "state_delta": [],
        "memory_citations": [],
    }


def raven(action: dict | None, status: str) -> dict:
    value = b0(action, status)
    value["completion_evidence"] = (
        [
            {
                "claim": "The requested value is visible.",
                "evidence": "direct_screen",
                "memory_ids": [],
            }
        ]
        if status == "done"
        else []
    )
    return value


def test_b0_v2_accepts_terminal_answer() -> None:
    action = {
        "type": "answer",
        "text": "42 km",
        "text_origin": "deterministic_calculation",
        "source_memory_ids": [],
    }
    parsed = parse_action_response(
        json.dumps(b0(action, "done")), schema_path=B0_SCHEMA
    )
    assert parsed.decision["action"]["type"] == "answer"


def test_b0_v2_rejects_answer_as_continue() -> None:
    action = {
        "type": "answer",
        "text": "42",
        "text_origin": "current_screen",
        "source_memory_ids": [],
    }
    with pytest.raises(ActionValidationError):
        parse_action_response(
            json.dumps(b0(action, "continue")), schema_path=B0_SCHEMA
        )


def test_b0_v2_requires_text_provenance() -> None:
    with pytest.raises(ActionValidationError):
        parse_action_response(
            json.dumps(
                b0(
                    {"type": "type_text", "text": "42"},
                    "continue",
                )
            ),
            schema_path=B0_SCHEMA,
        )


def test_raven_v2_accepts_verified_memory_text() -> None:
    value = raven(
        {
            "type": "answer",
            "text": "Running",
            "text_origin": "verified_memory",
            "source_memory_ids": ["m_0001"],
        },
        "done",
    )
    value["memory_citations"] = ["m_0001"]
    value["completion_evidence"][0] = {
        "claim": "The activity is Running.",
        "evidence": "verified_memory",
        "memory_ids": ["m_0001"],
    }
    parsed = parse_action_response(
        json.dumps(value), schema_path=RAVEN_SCHEMA
    )
    assert parsed.decision["completion_evidence"][0]["memory_ids"] == [
        "m_0001"
    ]


def test_raven_v2_requires_completion_evidence_only_on_done() -> None:
    done = raven(None, "done")
    done["completion_evidence"] = []
    with pytest.raises(ActionValidationError):
        parse_action_response(json.dumps(done), schema_path=RAVEN_SCHEMA)
    continued = raven({"type": "press_back"}, "continue")
    continued["completion_evidence"] = [
        {
            "claim": "Done",
            "evidence": "direct_screen",
            "memory_ids": [],
        }
    ]
    with pytest.raises(ActionValidationError):
        parse_action_response(json.dumps(continued), schema_path=RAVEN_SCHEMA)
