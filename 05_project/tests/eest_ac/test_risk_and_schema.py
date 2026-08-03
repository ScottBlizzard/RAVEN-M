from __future__ import annotations

import json

import pytest

from raven_m.eest_ac.risk import RiskDetector
from raven_m.eest_ac.schema import EestDecisionValidationError, parse_eest_decision


def _decision(*, summary: str, action: dict, status: str = "continue") -> dict:
    return {
        "status": status,
        "action": action,
        "expected_outcome": "The requested screen appears.",
        "decision_summary": summary,
        "observed_evidence": [],
        "evidence_citations": [],
    }


@pytest.mark.parametrize(
    "summary,action",
    [
        ("Open the target app.", {"type": "open_app", "app_name": "camera"}),
        ("Open Morgan's conversation.", {"type": "tap", "x": 0.5, "y": 0.4}),
        ("Open the message Avery sent.", {"type": "tap", "x": 0.5, "y": 0.4}),
        ("Return to the conversation list.", {"type": "press_back"}),
        ("Scroll to find Morgan.", {"type": "swipe", "x": 0.5, "y": 0.8, "x2": 0.5, "y2": 0.2, "duration_ms": 500}),
    ],
)
def test_negative_control_and_navigation_do_not_trigger(summary, action) -> None:
    trigger = RiskDetector().detect(_decision(summary=summary, action=action))
    assert not trigger.eligible


@pytest.mark.parametrize("word", ["Save", "Send", "Delete"])
def test_consequential_tap_triggers(word: str) -> None:
    trigger = RiskDetector().detect(
        _decision(
            summary=f"Tap {word} to commit the requested change.",
            action={"type": "tap", "x": 0.9, "y": 0.1},
        )
    )
    assert trigger.eligible
    assert trigger.intent == word.casefold()


def test_answer_and_terminal_done_trigger() -> None:
    answer = RiskDetector().detect(
        _decision(summary="Return the result.", action={"type": "answer", "text": "x"})
    )
    done = RiskDetector().detect(
        _decision(summary="Task is complete.", action=None, status="done")
    )
    assert (answer.intent, done.intent) == ("answer", "done")


def test_shared_schema_accepts_valid_decision_and_rejects_extra_fields() -> None:
    raw = json.dumps(
        _decision(
            summary="Open the target app.",
            action={"type": "open_app", "app_name": "camera"},
        )
    )
    parsed = parse_eest_decision(raw)
    assert parsed.first_pass
    corrupt = json.loads(raw)
    corrupt["planner_state"] = {"subgoal": "not allowed"}
    with pytest.raises(EestDecisionValidationError):
        parse_eest_decision(json.dumps(corrupt))
