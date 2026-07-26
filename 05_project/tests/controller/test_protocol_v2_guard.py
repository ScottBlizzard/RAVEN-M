from __future__ import annotations

import pytest

from raven_m.actions.schema import ActionValidationError
from raven_m.controller.protocol_v2_guard import ProtocolV2DecisionGuard


def decision(action: dict, *, citations: list[str] | None = None) -> dict:
    return {
        "status": "continue",
        "action": action,
        "memory_citations": citations or [],
    }


def test_guard_blocks_third_identical_no_effect_action() -> None:
    guard = ProtocolV2DecisionGuard(max_no_effect_repeats=2)
    guard.reset(goal="Create a note")
    action = {"type": "tap", "x": 0.5, "y": 0.5}
    guard.observe_transition(
        before_sha256="same", action=action, after_sha256="same"
    )
    guard.observe_transition(
        before_sha256="same", action=action, after_sha256="same"
    )
    with pytest.raises(ActionValidationError, match="LOOP_GUARD"):
        guard.validate_decision(decision(action), page_sha256="same")


def test_guard_allows_different_recovery_action() -> None:
    guard = ProtocolV2DecisionGuard(max_no_effect_repeats=1)
    guard.reset(goal="Create a note")
    old = {"type": "tap", "x": 0.5, "y": 0.5}
    guard.observe_transition(
        before_sha256="same", action=old, after_sha256="same"
    )
    guard.validate_decision(
        decision({"type": "press_back"}), page_sha256="same"
    )


def test_changed_page_does_not_block_same_action() -> None:
    guard = ProtocolV2DecisionGuard(max_no_effect_repeats=1)
    guard.reset(goal="Create a note")
    action = {"type": "tap", "x": 0.5, "y": 0.5}
    guard.observe_transition(
        before_sha256="old", action=action, after_sha256="new"
    )
    guard.validate_decision(decision(action), page_sha256="new")


def test_guard_blocks_repeated_ab_ab_cycle() -> None:
    guard = ProtocolV2DecisionGuard(max_no_effect_repeats=3)
    guard.reset(goal="Find the item")
    action_a = {"type": "tap", "x": 0.2, "y": 0.2}
    action_b = {"type": "press_back"}
    guard.observe_transition(
        before_sha256="page-a",
        action=action_a,
        after_sha256="page-b",
    )
    guard.observe_transition(
        before_sha256="page-b",
        action=action_b,
        after_sha256="page-a",
    )
    guard.observe_transition(
        before_sha256="page-a",
        action=action_a,
        after_sha256="page-b",
    )
    guard.observe_transition(
        before_sha256="page-b",
        action=action_b,
        after_sha256="page-a",
    )
    with pytest.raises(ActionValidationError, match="LOOP_GUARD"):
        guard.validate_decision(
            decision(action_a), page_sha256="page-a"
        )
    assert guard.audit_record()["ab_ab_cycle_trigger_count"] == 1


def test_guard_requires_verified_memory_source_and_citation() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Enter the result")
    action = {
        "type": "type_text",
        "text": "42",
        "text_origin": "verified_memory",
        "source_memory_ids": [],
    }
    with pytest.raises(ActionValidationError, match="at least one"):
        guard.validate_decision(decision(action), page_sha256="page")
    action["source_memory_ids"] = ["m_0001"]
    with pytest.raises(ActionValidationError, match="also appear"):
        guard.validate_decision(decision(action), page_sha256="page")


@pytest.mark.parametrize(
    "origin,source_ids,citations",
    [
        ("task_literal", [], []),
        ("current_screen", [], []),
        ("deterministic_calculation", [], []),
        ("verified_memory", ["m_0001"], ["m_0001"]),
    ],
)
def test_guard_accepts_all_valid_text_origins(
    origin: str,
    source_ids: list[str],
    citations: list[str],
) -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Enter the result")
    guard.validate_decision(
        decision(
            {
                "type": "type_text",
                "text": "42",
                "text_origin": origin,
                "source_memory_ids": source_ids,
            },
            citations=citations,
        ),
        page_sha256="page",
    )


def test_guard_rejects_false_memory_provenance() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Enter the result")
    action = {
        "type": "type_text",
        "text": "42",
        "text_origin": "current_screen",
        "source_memory_ids": ["m_0001"],
    }
    with pytest.raises(ActionValidationError, match="must be empty"):
        guard.validate_decision(
            decision(action, citations=["m_0001"]), page_sha256="page"
        )


def test_guard_limits_answer_to_terminal_information_goal() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Create a contact")
    action = {
        "type": "answer",
        "text": "Alice",
        "text_origin": "current_screen",
        "source_memory_ids": [],
    }
    nonterminal = decision(action)
    with pytest.raises(ActionValidationError, match="terminal"):
        guard.validate_decision(nonterminal, page_sha256="page")
    terminal = decision(action)
    terminal["status"] = "done"
    with pytest.raises(ActionValidationError, match="information-return"):
        guard.validate_decision(terminal, page_sha256="page")


def test_guard_audit_records_block_and_recovery() -> None:
    guard = ProtocolV2DecisionGuard(max_no_effect_repeats=1)
    guard.reset(goal="Find the total")
    action = {"type": "tap", "x": 0.5, "y": 0.5}
    guard.observe_transition(
        before_sha256="page", action=action, after_sha256="page"
    )
    with pytest.raises(ActionValidationError):
        guard.validate_decision(decision(action), page_sha256="page")
    recovery = {"type": "press_back"}
    guard.observe_transition(
        before_sha256="page", action=recovery, after_sha256="other"
    )
    audit = guard.audit_record()
    assert audit["validation_block_count"] == 1
    assert audit["recovery_completion_count"] == 1
    assert "navigate_back" in audit["validation_blocks"][0][
        "required_recovery_classes"
    ]
