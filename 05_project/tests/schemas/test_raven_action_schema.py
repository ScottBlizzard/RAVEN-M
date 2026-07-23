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


def test_raven_schema_bounds_delta_and_forces_empty_on_done() -> None:
    import json

    decision = valid_decision()
    decision["state_delta"] = decision["state_delta"] * 3
    with pytest.raises(ActionValidationError, match="too long"):
        parse_action_response(json.dumps(decision), schema_path=SCHEMA)
    decision = valid_decision()
    decision["status"] = "done"
    decision["action"] = None
    # jsonschema 4.17 reports maxItems=0 as "too long", while newer
    # releases render the equivalent const=[] branch as "expected to be
    # empty". Both prove the same protocol invariant.
    with pytest.raises(
        ActionValidationError,
        match="too long|expected to be empty",
    ):
        parse_action_response(json.dumps(decision), schema_path=SCHEMA)
