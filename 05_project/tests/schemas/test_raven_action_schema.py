from pathlib import Path

import pytest

from raven_m.actions.schema import ActionValidationError, parse_action_response


SCHEMA = (
    Path(__file__).resolve().parents[2]
    / "schemas"
    / "action.raven.v1.schema.json"
)


def valid_decision() -> dict:
    return {
        "status": "continue",
        "action": {"type": "tap", "x": 0.5, "y": 0.5},
        "expected_outcome": "The note opens.",
        "decision_summary": "Open the visible note.",
        "state_delta": [
            {
                "kind": "fact",
                "subject": "note_title",
                "predicate": "equals",
                "object": "Alpha",
                "natural_language": "The visible note title is Alpha.",
                "evidence": "direct_screen",
                "confidence": 0.98,
            }
        ],
        "memory_citations": ["m_0001"],
    }


def test_raven_schema_accepts_typed_delta_and_citation() -> None:
    import json

    parsed = parse_action_response(
        json.dumps(valid_decision()),
        schema_path=SCHEMA,
    )
    assert parsed.decision["state_delta"][0]["kind"] == "fact"


def test_raven_schema_rejects_unknown_evidence() -> None:
    import json

    decision = valid_decision()
    decision["state_delta"][0]["evidence"] = "hidden_state"
    with pytest.raises(ActionValidationError, match="evidence"):
        parse_action_response(json.dumps(decision), schema_path=SCHEMA)
