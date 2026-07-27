from __future__ import annotations

import pytest

from raven_m.actions.schema import ActionValidationError
from raven_m.controller.protocol_v2_guard import (
    ProtocolV2DecisionGuard,
    semantic_ui_snapshot,
)


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


def test_semantic_snapshot_ignores_clock_and_separates_failure() -> None:
    form = [
        {
            "package_name": "com.android.systemui",
            "text": "15:43",
            "class_name": "android.widget.TextView",
        },
        {
            "package_name": "calendar",
            "text": "Meeting with Marketing",
            "resource_id": "title",
            "is_editable": True,
        },
        {
            "package_name": "calendar",
            "text": "08:00",
            "resource_id": "start_time",
        },
        {
            "package_name": "calendar",
            "text": "00:30",
            "resource_id": "end_time",
        },
    ]
    before = semantic_ui_snapshot(form, fallback_sha256="pixel-a")
    after = semantic_ui_snapshot(
        [
            *form,
            {
                "package_name": "calendar",
                "text": "The event cannot end earlier than it starts",
                "class_name": "android.widget.Toast",
            },
            {
                "package_name": "com.android.systemui",
                "text": "15:48",
            },
        ],
        fallback_sha256="pixel-b",
    )
    assert before["source"] == "accessibility"
    assert before["sha256"] == after["sha256"]
    assert after["visible_failure_texts"] == [
        "The event cannot end earlier than it starts"
    ]
    assert after["infrastructure_failure_texts"] == []


def test_semantic_snapshot_separates_android_anr_from_validation() -> None:
    snapshot = semantic_ui_snapshot(
        [
            {
                "package_name": "android",
                "text": "Process system isn't responding",
                "class_name": "android.widget.TextView",
            },
            {
                "package_name": "android",
                "text": "Wait",
                "class_name": "android.widget.Button",
            },
        ],
        fallback_sha256="pixel-a",
    )
    assert snapshot["infrastructure_failure_texts"] == [
        "Process system isn't responding"
    ]
    assert snapshot["visible_failure_texts"] == []


def test_semantic_snapshot_changes_for_task_relevant_text() -> None:
    first = semantic_ui_snapshot(
        [{"package_name": "browser", "text": "7", "resource_id": "value"}],
        fallback_sha256="pixel-a",
    )
    second = semantic_ui_snapshot(
        [{"package_name": "browser", "text": "11", "resource_id": "value"}],
        fallback_sha256="pixel-b",
    )
    assert first["sha256"] != second["sha256"]


def test_semantic_snapshot_excludes_hidden_accessibility_nodes() -> None:
    first = semantic_ui_snapshot(
        [
            {
                "package_name": "app",
                "text": "Visible",
                "is_visible": True,
            },
            {
                "package_name": "app",
                "text": "Hidden secret A",
                "is_visible": False,
            },
        ],
        fallback_sha256="pixel-a",
    )
    second = semantic_ui_snapshot(
        [
            {
                "package_name": "app",
                "text": "Visible",
                "is_visible": True,
            },
            {
                "package_name": "app",
                "text": "Hidden secret B",
                "is_visible": False,
            },
        ],
        fallback_sha256="pixel-b",
    )
    assert first["sha256"] == second["sha256"]


def test_dynamic_pixels_do_not_mask_semantic_no_progress() -> None:
    guard = ProtocolV2DecisionGuard(max_no_effect_repeats=2)
    guard.reset(goal="Save the event")
    action = {"type": "tap", "x": 0.94, "y": 0.085}
    guard.observe_transition(
        before_sha256="same-ui",
        action=action,
        after_sha256="same-ui",
        before_pixel_sha256="clock-1543",
        after_pixel_sha256="toast-frame-1",
    )
    second = guard.observe_transition(
        before_sha256="same-ui",
        action=action,
        after_sha256="same-ui",
        before_pixel_sha256="toast-frame-2",
        after_pixel_sha256="clock-1544",
    )
    assert second["pixel_changed"]
    assert not second["semantic_changed"]
    with pytest.raises(ActionValidationError, match="LOOP_GUARD"):
        guard.validate_decision(decision(action), page_sha256="same-ui")


def test_visible_failure_blocks_same_action_before_repeat() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Save the event")
    action = {"type": "tap", "x": 0.94, "y": 0.085}
    outcome = guard.observe_transition(
        before_sha256="same-ui",
        action=action,
        after_sha256="same-ui",
        before_visible_failures=[],
        after_visible_failures=[
            "The event cannot end earlier than it starts"
        ],
    )
    assert outcome["new_visible_failures"]
    with pytest.raises(ActionValidationError, match="visible failure"):
        guard.validate_decision(decision(action), page_sha256="same-ui")


def test_repeated_action_is_allowed_when_semantic_content_changes() -> None:
    guard = ProtocolV2DecisionGuard(max_no_effect_repeats=1)
    guard.reset(goal="Click the button five times")
    action = {"type": "tap", "x": 0.5, "y": 0.5}
    guard.observe_transition(
        before_sha256="value-1",
        action=action,
        after_sha256="value-2",
    )
    guard.validate_decision(decision(action), page_sha256="value-2")


def test_guard_blocks_fourth_identical_coordinate_action_across_states() -> None:
    guard = ProtocolV2DecisionGuard(
        max_no_effect_repeats=10,
        max_identical_coordinate_actions=3,
    )
    guard.reset(goal="Open the toolbar menu")
    action = {"type": "tap", "x": 0.94, "y": 0.155}
    for index in range(3):
        guard.validate_decision(
            decision(action),
            page_sha256=f"state-{index}",
        )
        guard.observe_transition(
            before_sha256=f"state-{index}",
            action=action,
            after_sha256=f"state-{index + 1}",
        )
    with pytest.raises(
        ActionValidationError,
        match="same coordinate action",
    ):
        guard.validate_decision(decision(action), page_sha256="state-3")
    audit = guard.audit_record()
    assert audit["identical_coordinate_block_count"] == 1
    guard.validate_decision(
        decision({"type": "tap", "x": 0.94, "y": 0.08}),
        page_sha256="state-3",
    )
