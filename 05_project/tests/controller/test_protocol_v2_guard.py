from __future__ import annotations

import pytest

from raven_m.actions.schema import ActionValidationError
from raven_m.controller.protocol_v2_guard import (
    ProtocolV2DecisionGuard,
    coordinate_type_text_target_assessment,
    declared_text_source_assessment,
    destination_picker_active,
    destination_picker_commit_action,
    destination_picker_empty_stall_assessment,
    destination_picker_navigation_drawer_action,
    exact_selection_long_press_assessment,
    files_roots_drawer_action_assessment,
    focused_empty_editable_tap_assessment,
    focused_editable_input_assessment,
    post_destination_transfer_command_action,
    semantic_ui_snapshot,
    soft_keyboard_swipe_assessment,
    swipe_direction_consistency_assessment,
    task_literal_field_role_assessment,
)


def text_action(
    *,
    x: float | None = None,
    y: float | None = None,
    clear_text: bool = False,
) -> dict:
    action = {
        "type": "type_text",
        "text": "nature_sounds.mp3",
        "text_origin": "task_literal",
        "source_memory_ids": [],
        "clear_text": clear_text,
    }
    if x is not None and y is not None:
        action.update(x=x, y=y)
    return action


def decision(action: dict, *, citations: list[str] | None = None) -> dict:
    return {
        "status": "continue",
        "action": action,
        "memory_citations": citations or [],
    }


@pytest.mark.parametrize(
    ("summary", "action", "declared", "actual", "matched"),
    [
        (
            "Swipe left to reveal more categories.",
            {
                "type": "swipe",
                "x": 0.8,
                "y": 0.35,
                "x2": 0.2,
                "y2": 0.35,
                "duration_ms": 500,
            },
            "left",
            "left",
            True,
        ),
        (
            "Swiping left may reveal the requested category.",
            {
                "type": "swipe",
                "x": 0.5,
                "y": 0.34,
                "x2": 0.5,
                "y2": 0.15,
                "duration_ms": 500,
            },
            "left",
            "up",
            False,
        ),
        (
            "Swipe from right to left across the row.",
            {
                "type": "swipe",
                "x": 0.9,
                "y": 0.5,
                "x2": 0.1,
                "y2": 0.5,
                "duration_ms": 500,
            },
            "left",
            "left",
            True,
        ),
        (
            "Swipe up to scroll down the list.",
            {
                "type": "swipe",
                "x": 0.5,
                "y": 0.8,
                "x2": 0.5,
                "y2": 0.2,
                "duration_ms": 500,
            },
            "up",
            "up",
            True,
        ),
    ],
)
def test_swipe_direction_consistency_assessment(
    summary: str,
    action: dict,
    declared: str,
    actual: str,
    matched: bool,
) -> None:
    assessment = swipe_direction_consistency_assessment(
        {
            "status": "continue",
            "action": action,
            "decision_summary": summary,
        }
    )
    assert assessment["adjudicable"]
    assert assessment["declared_direction"] == declared
    assert assessment["actual_direction"] == actual
    assert assessment["matched"] is matched


def test_swipe_without_explicit_direction_is_not_adjudicable() -> None:
    assessment = swipe_direction_consistency_assessment(
        {
            "status": "continue",
            "action": {
                "type": "swipe",
                "x": 0.8,
                "y": 0.35,
                "x2": 0.2,
                "y2": 0.35,
                "duration_ms": 500,
            },
            "decision_summary": "Scroll the category row.",
        }
    )
    assert not assessment["adjudicable"]
    assert assessment["matched"] is None


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


def test_unverified_progress_blocks_only_immediate_exact_repeat() -> None:
    guard = ProtocolV2DecisionGuard(max_no_effect_repeats=2)
    guard.reset(goal="Open a control")
    action = {"type": "tap", "x": 0.5, "y": 0.34}
    outcome = guard.observe_transition(
        before_sha256="same",
        action=action,
        after_sha256="same",
        claimed_unverified_progress=True,
    )
    assert outcome["unverified_progress_repeat_armed"]
    with pytest.raises(
        ActionValidationError,
        match="asserted unverified progress",
    ):
        guard.validate_decision(decision(action), page_sha256="same")
    guard.validate_decision(
        decision(
            {
                "type": "swipe",
                "x": 0.8,
                "y": 0.34,
                "x2": 0.2,
                "y2": 0.34,
                "duration_ms": 500,
            }
        ),
        page_sha256="same",
    )


def test_no_effect_without_progress_claim_keeps_existing_threshold() -> None:
    guard = ProtocolV2DecisionGuard(max_no_effect_repeats=2)
    guard.reset(goal="Open a delayed control")
    action = {"type": "tap", "x": 0.5, "y": 0.34}
    outcome = guard.observe_transition(
        before_sha256="same",
        action=action,
        after_sha256="same",
        claimed_unverified_progress=False,
    )
    assert not outcome["unverified_progress_repeat_armed"]
    guard.validate_decision(decision(action), page_sha256="same")


def test_input_activation_proof_is_one_executed_action_only() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Enter the requested value")
    activation = {"type": "tap", "x": 0.5, "y": 0.18}
    guard.mark_input_activation_repair(activation)
    assert guard.input_activation_repair_pending
    with pytest.raises(
        ActionValidationError,
        match="POST_ACTIVATION_INPUT_GUARD",
    ):
        guard.validate_decision(
            decision(activation),
            page_sha256="same",
        )
    outcome = guard.observe_transition(
        before_sha256="same",
        action={
            "type": "type_text",
            "text": "value",
            "text_origin": "task_literal",
            "source_memory_ids": [],
            "clear_text": True,
        },
        after_sha256="changed",
    )
    assert outcome["input_activation_proof_consumed"]
    assert not guard.input_activation_repair_pending
    assert guard.input_activation_proof_consumed_count == 1


def test_input_activation_proof_rejects_coordinate_text_only() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Enter the requested value")
    guard.mark_input_activation_repair(
        {"type": "tap", "x": 0.5, "y": 0.18}
    )
    coordinate_action = {
        "type": "type_text",
        "text": "value",
        "text_origin": "task_literal",
        "source_memory_ids": [],
        "x": 0.5,
        "y": 0.18,
        "clear_text": True,
    }
    target = {
        "schema_version": "coordinate_text_target_assessment.v2",
        "adjudicable": True,
        "coordinate_bearing": True,
        "matched": True,
        "matched_editable_count": 1,
        "matched_empty": True,
        "visible_editable_count": 3,
        "boxed_editable_count": 3,
    }
    with pytest.raises(
        ActionValidationError,
        match="POST_ACTIVATION_INPUT_READY",
    ):
        guard.validate_decision(
            decision(coordinate_action),
            page_sha256="same",
            coordinate_text_target_assessment=target,
        )
    repaired = {
        **coordinate_action,
    }
    repaired.pop("x")
    repaired.pop("y")
    repaired["clear_text"] = False
    guard.validate_decision(
        decision(repaired),
        page_sha256="same",
        coordinate_text_target_assessment={
            **target,
            "coordinate_bearing": False,
            "matched": False,
            "matched_editable_count": 0,
        },
    )


def test_focused_editable_input_assessment_uses_visible_state_only() -> None:
    assessment = focused_editable_input_assessment(
        [
            {
                "text": "",
                "hint_text": "Search",
                "is_visible": True,
                "is_editable": True,
                "is_focused": True,
                "bbox": {
                    "x_min": 0.2,
                    "x_max": 0.9,
                    "y_min": 0.05,
                    "y_max": 0.1,
                },
            },
            {
                "text": "hidden",
                "is_visible": False,
                "is_editable": True,
                "is_focused": True,
            },
        ]
    )
    assert assessment == {
        "schema_version": "focused_editable_input_assessment.v2",
        "present": True,
        "focused_count": 1,
        "empty": True,
        "soft_keyboard_present": False,
        "soft_keyboard_packages": [],
        "input_ready": True,
    }
    assert "bbox" not in assessment


def test_focused_empty_editable_tap_assessment_hits_only_same_input() -> None:
    elements = [
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
    ]
    hit = focused_empty_editable_tap_assessment(
        elements,
        {"type": "tap", "x": 0.5, "y": 0.18},
        screen_width=1080,
        screen_height=2400,
    )
    assert hit == {
        "schema_version": "focused_empty_editable_tap_assessment.v1",
        "adjudicable": True,
        "action_type": "tap",
        "focused_empty_count": 1,
        "hits_focused_empty": True,
    }
    miss = focused_empty_editable_tap_assessment(
        elements,
        {"type": "tap", "x": 0.5, "y": 0.5},
        screen_width=1080,
        screen_height=2400,
    )
    assert miss["adjudicable"]
    assert not miss["hits_focused_empty"]


def test_guard_rejects_tap_on_focused_empty_editable() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Fill the requested field")
    assessment = {
        "schema_version": "focused_empty_editable_tap_assessment.v1",
        "adjudicable": True,
        "action_type": "tap",
        "focused_empty_count": 1,
        "hits_focused_empty": True,
    }
    with pytest.raises(
        ActionValidationError,
        match="FOCUSED_EMPTY_TAP_GUARD",
    ):
        guard.validate_decision(
            decision({"type": "tap", "x": 0.5, "y": 0.18}),
            page_sha256="same",
            focused_empty_tap_assessment=assessment,
        )


def test_focused_input_assessment_uses_visible_soft_keyboard_fallback() -> None:
    assessment = focused_editable_input_assessment(
        [
            {
                "package_name": "com.google.android.documentsui",
                "text": "Search",
                "is_visible": True,
                "is_editable": False,
                "is_focused": False,
            },
            {
                "package_name": "com.google.android.inputmethod.latin",
                "text": "q",
                "is_visible": True,
                "is_editable": False,
                "is_focused": False,
            },
        ]
    )
    assert assessment == {
        "schema_version": "focused_editable_input_assessment.v2",
        "present": False,
        "focused_count": 0,
        "empty": False,
        "soft_keyboard_present": True,
        "soft_keyboard_packages": [
            "com.google.android.inputmethod.latin"
        ],
        "input_ready": True,
    }


def test_soft_keyboard_swipe_assessment_checks_start_without_leaking_bbox() -> None:
    elements = [
        {
            "package_name": "com.google.android.inputmethod.latin",
            "is_visible": True,
            "bbox": {
                "x_min": 0.0,
                "x_max": 1.0,
                "y_min": 0.63,
                "y_max": 1.0,
            },
        }
    ]
    inside = soft_keyboard_swipe_assessment(
        elements,
        {
            "type": "swipe",
            "x": 0.5,
            "y": 0.75,
            "x2": 0.5,
            "y2": 0.3,
            "duration_ms": 500,
        },
        screen_width=1080,
        screen_height=2400,
    )
    assert inside == {
        "schema_version": "soft_keyboard_swipe_assessment.v1",
        "adjudicable": True,
        "coordinate_bearing": True,
        "soft_keyboard_present": True,
        "soft_keyboard_packages": [
            "com.google.android.inputmethod.latin"
        ],
        "visible_keyboard_element_count": 1,
        "boxed_keyboard_element_count": 1,
        "start_hit_count": 1,
        "start_in_keyboard": True,
    }
    assert "bbox" not in inside
    assert "x" not in inside
    assert "y" not in inside

    outside = soft_keyboard_swipe_assessment(
        elements,
        {
            "type": "swipe",
            "x": 0.5,
            "y": 0.5,
            "x2": 0.5,
            "y2": 0.2,
            "duration_ms": 500,
        },
        screen_width=1080,
        screen_height=2400,
    )
    assert outside["adjudicable"] is True
    assert outside["start_in_keyboard"] is False
    assert outside["start_hit_count"] == 0


def test_guard_blocks_swipe_that_begins_in_soft_keyboard() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Create a contact")
    action = {
        "type": "swipe",
        "x": 0.5,
        "y": 0.75,
        "x2": 0.5,
        "y2": 0.3,
        "duration_ms": 500,
    }
    assessment = {
        "schema_version": "soft_keyboard_swipe_assessment.v1",
        "adjudicable": True,
        "coordinate_bearing": True,
        "soft_keyboard_present": True,
        "soft_keyboard_packages": [
            "com.google.android.inputmethod.latin"
        ],
        "visible_keyboard_element_count": 1,
        "boxed_keyboard_element_count": 1,
        "start_hit_count": 1,
        "start_in_keyboard": True,
    }
    with pytest.raises(
        ActionValidationError,
        match="SOFT_KEYBOARD_DISMISS_REQUIRED",
    ):
        guard.validate_decision(
            decision(action),
            page_sha256="keyboard",
            soft_keyboard_swipe_assessment=assessment,
        )
    audit = guard.audit_record()
    assert audit["soft_keyboard_swipe_block_count"] == 1
    assert audit["validation_blocks"][-1]["reason"] == (
        "soft_keyboard_swipe_start_blocked"
    )
    assert audit["validation_blocks"][-1][
        "soft_keyboard_swipe_assessment"
    ]["start_in_keyboard"] is True


def test_field_role_mismatch_requires_keyboard_dismissal_before_repair() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Create a contact for Sofija. Their number is +123.")
    with pytest.raises(
        ActionValidationError,
        match="SOFT_KEYBOARD_SWIPE_FORBIDDEN",
    ):
        guard.validate_decision(
            decision(
                {
                    "type": "type_text",
                    "text": "+123",
                    "text_origin": "task_literal",
                    "source_memory_ids": [],
                    "x": 0.5,
                    "y": 0.55,
                    "clear_text": True,
                }
            ),
            page_sha256="company-focused",
            soft_keyboard_swipe_assessment={
                "schema_version": "soft_keyboard_swipe_assessment.v1",
                "soft_keyboard_present": True,
            },
            task_literal_field_role_assessment={
                "schema_version": "task_literal_field_role_assessment.v1",
                "adjudicable": True,
                "matched": False,
                "source_role_groups": ["phone"],
                "target_role_groups": ["company"],
            },
        )
    assert guard.audit_record()[
        "task_literal_field_role_block_count"
    ] == 1


def test_declared_text_source_assessment_binds_task_and_screen_text() -> None:
    elements = [
        {
            "text": "Visible account name",
            "content_description": "Search",
            "is_visible": True,
        },
        {
            "text": "Hidden value",
            "is_visible": False,
        },
    ]
    task_match = declared_text_source_assessment(
        "Create a contact for Sofija Martin.",
        elements,
        {
            **text_action(),
            "text": "Sofija",
            "text_origin": "task_literal",
        },
    )
    task_miss = declared_text_source_assessment(
        "Create a contact for Sofija Martin.",
        elements,
        {
            **text_action(),
            "text": "Tech Solutions",
            "text_origin": "task_literal",
        },
    )
    screen_match = declared_text_source_assessment(
        "Open the current account.",
        elements,
        {
            **text_action(),
            "text": "Search",
            "text_origin": "current_screen",
        },
    )
    screen_miss = declared_text_source_assessment(
        "Open the current account.",
        elements,
        {
            **text_action(),
            "text": "Hidden value",
            "text_origin": "current_screen",
        },
    )
    assert task_match["matched"] is True
    assert task_miss["matched"] is False
    assert screen_match["matched"] is True
    assert screen_miss["matched"] is False
    assert task_match["source_value_count"] == 1
    assert screen_match["source_value_count"] == 2
    assert "source_values" not in screen_match


@pytest.mark.parametrize("origin", ["task_literal", "current_screen"])
def test_guard_blocks_text_not_bound_to_declared_source(origin: str) -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Create a contact for Sofija Martin")
    action = {
        **text_action(),
        "text": "Tech Solutions",
        "text_origin": origin,
    }
    with pytest.raises(
        ActionValidationError,
        match="DECLARED_TEXT_SOURCE_GUARD",
    ):
        guard.validate_decision(
            decision(action),
            page_sha256="contact-form",
            declared_text_source_assessment={
                "schema_version": "declared_text_source_assessment.v1",
                "origin": origin,
                "adjudicable": True,
                "source_value_count": 1,
                "matched": False,
            },
        )
    audit = guard.audit_record()
    assert audit["declared_text_source_block_count"] == 1
    assert audit["validation_blocks"][0][
        "declared_text_source_assessment"
    ]["matched"] is False


def test_guard_marks_rejected_visual_source_answer() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="What events are visible? Answer with titles only.")
    answer_decision = decision(
        {
            "type": "answer",
            "text": "Board meeting",
            "text_origin": "current_screen",
            "source_memory_ids": [],
        }
    )
    answer_decision["status"] = "done"
    with pytest.raises(
        ActionValidationError,
        match="VISUAL_SOURCE_ADJUDICATION_REJECTED",
    ):
        guard.validate_decision(
            answer_decision,
            page_sha256="calendar-detail",
            declared_text_source_assessment={
                "schema_version": "declared_text_source_assessment.v1",
                "origin": "current_screen",
                "adjudicable": True,
                "source_value_count": 0,
                "matched": False,
                "visual_adjudication_required": True,
                "visual_adjudicated": True,
                "visual_adjudication_accepted": False,
            },
        )
    assert guard.audit_record()["declared_text_source_block_count"] == 1


def test_task_literal_field_role_assessment_rejects_phone_in_company() -> None:
    elements = [
        {
            "hint_text": "Company",
            "is_visible": True,
            "is_enabled": True,
            "is_editable": True,
            "bbox": {
                "x_min": 0.1,
                "x_max": 0.8,
                "y_min": 0.50,
                "y_max": 0.57,
            },
        },
        {
            "hint_text": "Phone",
            "is_visible": True,
            "is_enabled": True,
            "is_editable": True,
            "bbox": {
                "x_min": 0.1,
                "x_max": 0.8,
                "y_min": 0.58,
                "y_max": 0.65,
            },
        },
    ]
    action = {
        **text_action(x=0.45, y=0.55, clear_text=True),
        "text": "+17634322348",
    }
    wrong = task_literal_field_role_assessment(
        "Create a contact. Their number is +17634322348.",
        elements,
        action,
        screen_width=100,
        screen_height=100,
    )
    action.update(y=0.60)
    right = task_literal_field_role_assessment(
        "Create a contact. Their number is +17634322348.",
        elements,
        action,
        screen_width=100,
        screen_height=100,
    )
    assert wrong["adjudicable"] is True
    assert wrong["source_role_groups"] == ["phone"]
    assert wrong["target_role_groups"] == ["company"]
    assert wrong["matched"] is False
    assert right["target_role_groups"] == ["phone"]
    assert right["matched"] is True


def test_task_literal_field_role_allows_name_and_search_targets() -> None:
    name = task_literal_field_role_assessment(
        "Create a new contact for Sofija Martin.",
        [
            {
                "hint_text": "First name",
                "is_visible": True,
                "is_enabled": True,
                "is_editable": True,
                "bbox": {
                    "x_min": 0.1,
                    "x_max": 0.8,
                    "y_min": 0.30,
                    "y_max": 0.40,
                },
            }
        ],
        {
            **text_action(x=0.45, y=0.35, clear_text=True),
            "text": "Sofija",
        },
        screen_width=100,
        screen_height=100,
    )
    search = task_literal_field_role_assessment(
        "Move the file nature_sounds.mp3 to Ringtones.",
        [
            {
                "hint_text": "Search",
                "is_visible": True,
                "is_enabled": True,
                "is_editable": True,
                "bbox": {
                    "x_min": 0.1,
                    "x_max": 0.9,
                    "y_min": 0.05,
                    "y_max": 0.10,
                },
            }
        ],
        text_action(x=0.5, y=0.075, clear_text=True),
        screen_width=100,
        screen_height=100,
    )
    assert name["matched"] is True
    assert search["matched"] is True


def test_task_literal_field_role_uses_local_task_line_for_expense() -> None:
    elements = [
        {
            "hint_text": "Amount",
            "is_visible": True,
            "is_enabled": True,
            "is_editable": True,
            "bbox": {
                "x_min": 0.1,
                "x_max": 0.8,
                "y_min": 0.30,
                "y_max": 0.40,
            },
        },
        {
            "hint_text": "Category",
            "is_visible": True,
            "is_enabled": True,
            "is_editable": True,
            "bbox": {
                "x_min": 0.1,
                "x_max": 0.8,
                "y_min": 0.42,
                "y_max": 0.52,
            },
        },
    ]
    action = {
        **text_action(x=0.45, y=0.47, clear_text=True),
        "text": "259.57",
    }
    wrong = task_literal_field_role_assessment(
        "Expense: Educational\namount_dollars: $259.57\n"
        "category_name: Donation",
        elements,
        action,
        screen_width=100,
        screen_height=100,
    )
    action.update(y=0.35)
    right = task_literal_field_role_assessment(
        "Expense: Educational\namount_dollars: $259.57\n"
        "category_name: Donation",
        elements,
        action,
        screen_width=100,
        screen_height=100,
    )
    assert wrong["source_role_groups"] == ["amount"]
    assert wrong["target_role_groups"] == ["category"]
    assert wrong["matched"] is False
    assert right["target_role_groups"] == ["amount"]
    assert right["matched"] is True


def test_guard_blocks_task_literal_target_field_role_mismatch() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Create a contact")
    with pytest.raises(
        ActionValidationError,
        match="FIELD_VALUE_BINDING_GUARD",
    ):
        guard.validate_decision(
            decision(
                {
                    **text_action(x=0.45, y=0.55, clear_text=True),
                    "text": "+17634322348",
                }
            ),
            page_sha256="contact-form",
            task_literal_field_role_assessment={
                "schema_version": "task_literal_field_role_assessment.v1",
                "adjudicable": True,
                "coordinate_bearing": True,
                "matched_editable_count": 1,
                "source_role_groups": ["phone"],
                "target_role_groups": ["company"],
                "matched": False,
            },
        )
    assert guard.audit_record()[
        "task_literal_field_role_block_count"
    ] == 1


def test_focused_input_guard_blocks_click_before_type_and_allows_repair() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Search for nature_sounds.mp3")
    assessment = {
        "schema_version": "focused_editable_input_assessment.v1",
        "present": True,
        "focused_count": 1,
        "empty": True,
    }
    with pytest.raises(ActionValidationError, match="FOCUSED_INPUT_GUARD") as caught:
        guard.validate_decision(
            decision(text_action(x=0.5, y=0.5, clear_text=True)),
            page_sha256="focused-search",
            focused_input_assessment=assessment,
        )
    message = str(caught.value)
    assert "omit x and y" in message
    assert "clear_text=false" in message
    guard.validate_decision(
        decision(text_action(clear_text=False)),
        page_sha256="focused-search",
        focused_input_assessment=assessment,
    )
    assert guard.audit_record()["focused_input_block_count"] == 1


def test_focused_input_guard_blocks_coordinate_type_with_keyboard_only() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Search for nature_sounds.mp3")
    assessment = {
        "schema_version": "focused_editable_input_assessment.v2",
        "present": False,
        "focused_count": 0,
        "empty": False,
        "soft_keyboard_present": True,
        "soft_keyboard_packages": [
            "com.google.android.inputmethod.latin"
        ],
        "input_ready": True,
    }
    with pytest.raises(ActionValidationError, match="FOCUSED_INPUT_GUARD"):
        guard.validate_decision(
            decision(text_action(x=0.5, y=0.5, clear_text=True)),
            page_sha256="search-with-keyboard",
            focused_input_assessment=assessment,
        )
    guard.validate_decision(
        decision(text_action(clear_text=True)),
        page_sha256="search-with-keyboard",
        focused_input_assessment=assessment,
    )
    assert guard.audit_record()["focused_input_block_count"] == 1


def test_focused_input_guard_allows_switch_to_visible_editable_target() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Create a contact")
    guard.validate_decision(
        decision(text_action(x=0.45, y=0.465, clear_text=True)),
        page_sha256="contact-form-with-keyboard",
        focused_input_assessment={
            "schema_version": "focused_editable_input_assessment.v2",
            "present": False,
            "focused_count": 0,
            "empty": False,
            "soft_keyboard_present": True,
            "input_ready": True,
        },
        coordinate_text_target_assessment={
            "schema_version": "coordinate_text_target_assessment.v1",
            "adjudicable": True,
            "coordinate_bearing": True,
            "visible_editable_count": 4,
            "boxed_editable_count": 4,
            "matched": True,
        },
    )
    assert guard.audit_record()["focused_input_block_count"] == 0


def test_focused_empty_input_allows_explicit_editable_target_switch() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Create a contact")
    guard.validate_decision(
        decision(text_action(x=0.45, y=0.465, clear_text=True)),
        page_sha256="contact-form-focused-empty-field",
        focused_input_assessment={
            "schema_version": "focused_editable_input_assessment.v2",
            "present": True,
            "focused_count": 1,
            "empty": True,
            "soft_keyboard_present": True,
            "input_ready": True,
        },
        coordinate_text_target_assessment={
            "schema_version": "coordinate_text_target_assessment.v1",
            "adjudicable": True,
            "coordinate_bearing": True,
            "visible_editable_count": 4,
            "boxed_editable_count": 4,
            "matched": True,
        },
    )
    assert guard.audit_record()["focused_input_block_count"] == 0


def test_focused_input_guard_does_not_block_an_unfocused_target() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Enter a contact name")
    guard.validate_decision(
        decision(text_action(x=0.5, y=0.5, clear_text=True)),
        page_sha256="contact-form",
        focused_input_assessment={
            "schema_version": "focused_editable_input_assessment.v1",
            "present": False,
            "focused_count": 0,
            "empty": False,
        },
    )


def test_coordinate_text_target_assessment_matches_editable_only() -> None:
    elements = [
        {
            "text": "Search",
            "is_visible": True,
            "is_enabled": True,
            "is_editable": True,
            "bbox": {
                "x_min": 0.2,
                "x_max": 0.9,
                "y_min": 0.05,
                "y_max": 0.1,
            },
        },
        {
            "text": "ordinary card",
            "is_visible": True,
            "is_enabled": True,
            "is_editable": False,
            "bbox": {
                "x_min": 0.2,
                "x_max": 0.9,
                "y_min": 0.4,
                "y_max": 0.6,
            },
        },
    ]
    matched = coordinate_type_text_target_assessment(
        elements,
        text_action(x=0.5, y=0.075),
        screen_width=100,
        screen_height=100,
    )
    missed = coordinate_type_text_target_assessment(
        elements,
        text_action(x=0.5, y=0.5),
        screen_width=100,
        screen_height=100,
    )
    assert matched["adjudicable"] is True
    assert matched["coordinate_bearing"] is True
    assert matched["visible_editable_count"] == 1
    assert matched["boxed_editable_count"] == 1
    assert matched["matched_editable_count"] == 1
    assert matched["matched_empty"] is False
    assert matched["matched"] is True
    assert missed["matched"] is False
    assert "bbox" not in matched


def test_guard_blocks_coordinate_text_not_bound_to_editable() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Search for nature_sounds.mp3")
    assessment = {
        "schema_version": "coordinate_text_target_assessment.v1",
        "adjudicable": True,
        "coordinate_bearing": True,
        "visible_editable_count": 0,
        "boxed_editable_count": 0,
        "matched": False,
    }
    with pytest.raises(ActionValidationError, match="TEXT_TARGET_GUARD"):
        guard.validate_decision(
            decision(text_action(x=0.5, y=0.075, clear_text=True)),
            page_sha256="files-grid",
            focused_input_assessment={
                "input_ready": False,
                "present": False,
            },
            coordinate_text_target_assessment=assessment,
        )
    assert guard.audit_record()["coordinate_text_target_block_count"] == 1


def test_guard_blocks_coordinate_free_text_without_active_input() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Search for nature_sounds.mp3")
    with pytest.raises(ActionValidationError, match="TEXT_TARGET_GUARD"):
        guard.validate_decision(
            decision(text_action(clear_text=False)),
            page_sha256="files-grid",
            focused_input_assessment={
                "input_ready": False,
                "present": False,
            },
            coordinate_text_target_assessment={
                "schema_version": "coordinate_text_target_assessment.v1",
                "adjudicable": True,
                "coordinate_bearing": False,
                "visible_editable_count": 0,
                "boxed_editable_count": 0,
                "matched": False,
            },
        )


def test_guard_allows_nonclearing_coordinate_text_bound_to_editable() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Enter a contact name")
    guard.validate_decision(
        decision(text_action(x=0.5, y=0.2, clear_text=False)),
        page_sha256="contact-form",
        focused_input_assessment={
            "input_ready": False,
            "present": False,
        },
        coordinate_text_target_assessment={
            "schema_version": "coordinate_text_target_assessment.v1",
            "adjudicable": True,
            "coordinate_bearing": True,
            "visible_editable_count": 3,
            "boxed_editable_count": 3,
            "matched": True,
        },
    )


def test_guard_blocks_clearing_coordinate_text_until_input_is_active() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Search for nature_sounds.mp3")
    with pytest.raises(
        ActionValidationError,
        match="UNFOCUSED_CLEAR_TEXT_GUARD",
    ) as caught:
        guard.validate_decision(
            decision(text_action(x=0.5, y=0.075, clear_text=True)),
            page_sha256="search-open-without-keyboard",
            focused_input_assessment={
                "input_ready": False,
                "present": False,
                "soft_keyboard_present": False,
            },
            coordinate_text_target_assessment={
                "schema_version": "coordinate_text_target_assessment.v1",
                "adjudicable": True,
                "coordinate_bearing": True,
                "visible_editable_count": 1,
                "boxed_editable_count": 1,
                "matched": True,
            },
        )
    assert "sending Ctrl+A" in str(caught.value)
    audit = guard.audit_record()
    assert audit["unfocused_clear_text_block_count"] == 1
    assert audit["validation_blocks"][0]["reason"] == (
        "unfocused_clear_text_race_blocked"
    )


def test_guard_blocks_redundant_coordinate_for_unique_active_input() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Search for nature_sounds.mp3")
    with pytest.raises(ActionValidationError, match="FOCUSED_INPUT_GUARD") as caught:
        guard.validate_decision(
            decision(text_action(x=0.5, y=0.075, clear_text=True)),
            page_sha256="unique-search-with-keyboard",
            focused_input_assessment={
                "input_ready": True,
                "present": False,
                "empty": False,
                "soft_keyboard_present": True,
            },
            coordinate_text_target_assessment={
                "schema_version": "coordinate_text_target_assessment.v2",
                "adjudicable": True,
                "coordinate_bearing": True,
                "visible_editable_count": 1,
                "boxed_editable_count": 1,
                "matched_editable_count": 1,
                "matched_empty": True,
                "matched": True,
            },
        )
    assert "omit x and y" in str(caught.value)
    assert "target input is empty" in str(caught.value)
    audit = guard.audit_record()
    assert audit["focused_input_block_count"] == 1
    assert audit["validation_blocks"][0]["reason"] == (
        "focused_input_redundant_unique_coordinate_blocked"
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


def test_guard_allows_fourth_identical_coordinate_action_with_progress() -> None:
    guard = ProtocolV2DecisionGuard(
        max_no_effect_repeats=10,
        max_identical_coordinate_actions=3,
    )
    guard.reset(goal="Open the toolbar menu")
    action = {
        "type": "swipe",
        "x": 0.8,
        "y": 0.34,
        "x2": 0.2,
        "y2": 0.34,
        "duration_ms": 500,
    }
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
    guard.validate_decision(decision(action), page_sha256="state-3")
    audit = guard.audit_record()
    assert audit["identical_coordinate_block_count"] == 0
    assert audit["identical_coordinate_no_effect_count"] == 0
    guard.validate_decision(
        decision({"type": "tap", "x": 0.94, "y": 0.08}),
        page_sha256="state-3",
    )


def test_guard_still_blocks_fourth_semantic_changing_tap() -> None:
    guard = ProtocolV2DecisionGuard(
        max_no_effect_repeats=10,
        max_identical_coordinate_actions=3,
    )
    guard.reset(goal="Open the requested item")
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
        match="same coordinate tap or long-press",
    ):
        guard.validate_decision(decision(action), page_sha256="state-3")
    assert guard.audit_record()["identical_coordinate_block_count"] == 1


def test_guard_blocks_fourth_identical_action_after_no_effect() -> None:
    guard = ProtocolV2DecisionGuard(
        max_no_effect_repeats=10,
        max_identical_coordinate_actions=3,
    )
    guard.reset(goal="Complete a contact form")
    action = {
        "type": "swipe",
        "x": 0.5,
        "y": 0.75,
        "x2": 0.5,
        "y2": 0.30,
        "duration_ms": 500,
    }
    for index in range(3):
        guard.validate_decision(
            decision(action),
            page_sha256=f"state-{index}",
        )
        guard.observe_transition(
            before_sha256=f"state-{index}",
            action=action,
            after_sha256=(
                f"state-{index}"
                if index == 2
                else f"state-{index + 1}"
            ),
        )
    with pytest.raises(
        ActionValidationError,
        match="contains a transition with no semantic UI change",
    ):
        guard.validate_decision(decision(action), page_sha256="state-2")
    audit = guard.audit_record()
    assert audit["identical_coordinate_block_count"] == 1
    assert audit["identical_coordinate_no_effect_count"] == 1
    assert (
        "use_higher_level_visible_selector"
        in audit["validation_blocks"][-1]["required_recovery_classes"]
    )


def test_unverified_no_effect_precedes_coordinate_streak_guard() -> None:
    guard = ProtocolV2DecisionGuard(
        max_no_effect_repeats=10,
        max_identical_coordinate_actions=3,
    )
    guard.reset(goal="Find Donation in the horizontal category row")
    action = {
        "type": "swipe",
        "x": 0.8,
        "y": 0.34,
        "x2": 0.2,
        "y2": 0.34,
        "duration_ms": 500,
    }
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
    guard.validate_decision(decision(action), page_sha256="state-3")
    guard.observe_transition(
        before_sha256="state-3",
        action=action,
        after_sha256="state-3",
        claimed_unverified_progress=True,
    )
    with pytest.raises(
        ActionValidationError,
        match="UNVERIFIED_PROGRESS_REPEAT_REQUIRED",
    ):
        guard.validate_decision(decision(action), page_sha256="state-3")
    audit = guard.audit_record()
    assert audit["unverified_progress_repeat_block_count"] == 1
    assert audit["identical_coordinate_block_count"] == 0


def test_destination_picker_requires_bottom_cancel_and_commit_controls() -> None:
    controls = [
        {
            "text": "CANCEL",
            "is_visible": True,
            "is_enabled": True,
            "bbox": {"y_min": 0.91, "y_max": 0.98},
        },
        {
            "text": "MOVE",
            "is_visible": True,
            "is_enabled": True,
            "bbox": {"y_min": 0.91, "y_max": 0.98},
        },
    ]
    assert destination_picker_active(controls, screen_height=2400)
    controls[1]["bbox"] = {"y_min": 0.2, "y_max": 0.3}
    assert not destination_picker_active(controls, screen_height=2400)


def test_destination_picker_commit_action_requires_enabled_bottom_hit() -> None:
    controls = [
        {
            "text": "MOVE",
            "is_visible": True,
            "is_enabled": True,
            "bbox": {
                "x_min": 0.28,
                "x_max": 0.50,
                "y_min": 0.91,
                "y_max": 0.98,
            },
        }
    ]
    assert destination_picker_commit_action(
        controls,
        {"type": "tap", "x": 0.385, "y": 0.945},
        screen_width=1080,
        screen_height=2400,
    )
    assert not destination_picker_commit_action(
        controls,
        {"type": "tap", "x": 0.08, "y": 0.08},
        screen_width=1080,
        screen_height=2400,
    )
    controls[0]["is_enabled"] = False
    assert not destination_picker_commit_action(
        controls,
        {"type": "tap", "x": 0.385, "y": 0.945},
        screen_width=1080,
        screen_height=2400,
    )


def test_destination_picker_navigation_requires_enabled_top_left_roots_hit() -> None:
    controls = [
        {
            "content_description": "Show roots",
            "is_visible": True,
            "is_enabled": True,
            "bbox": {
                "x_min": 0.03,
                "x_max": 0.10,
                "y_min": 0.05,
                "y_max": 0.11,
            },
        }
    ]
    assert destination_picker_navigation_drawer_action(
        controls,
        {"type": "tap", "x": 0.065, "y": 0.08},
        screen_width=1080,
        screen_height=2400,
    )
    assert not destination_picker_navigation_drawer_action(
        controls,
        {"type": "tap", "x": 0.385, "y": 0.945},
        screen_width=1080,
        screen_height=2400,
    )
    assert not destination_picker_navigation_drawer_action(
        controls,
        {"type": "press_back"},
        screen_width=1080,
        screen_height=2400,
    )
    controls[0]["is_enabled"] = False
    assert not destination_picker_navigation_drawer_action(
        controls,
        {"type": "tap", "x": 0.065, "y": 0.08},
        screen_width=1080,
        screen_height=2400,
    )


def test_destination_picker_empty_stall_assessment_exposes_no_ui_text() -> None:
    elements = [
        {
            "text": "No items",
            "is_visible": True,
            "is_enabled": True,
        },
        {
            "content_description": "Show roots",
            "is_visible": True,
            "is_enabled": True,
        },
    ]
    assessment = destination_picker_empty_stall_assessment(
        elements,
        {
            "type": "swipe",
            "x": 0.5,
            "y": 0.8,
            "x2": 0.5,
            "y2": 0.2,
            "duration_ms": 500,
        },
    )
    assert assessment == {
        "schema_version": (
            "destination_picker_empty_stall_assessment.v2"
        ),
        "adjudicable": True,
        "action_type": "swipe",
        "control_bound_tap": None,
        "empty_destination_state": True,
        "unsupported_tap": False,
        "visible_empty_marker_count": 1,
        "stalling_action": True,
    }
    assert not any(
        key in assessment
        for key in ("text", "directory", "bbox", "coordinate")
    )
    no_marker = destination_picker_empty_stall_assessment(
        [{"text": "Ringtones", "is_visible": True}],
        {"type": "wait", "duration_ms": 1000},
    )
    assert not no_marker["adjudicable"]
    assert not no_marker["empty_destination_state"]


def test_destination_picker_empty_stall_rejects_only_unbound_taps() -> None:
    elements = [
        {
            "text": "No items",
            "is_visible": True,
            "is_enabled": True,
        },
        {
            "content_description": "Show roots",
            "is_visible": True,
            "is_enabled": True,
            "bbox": {
                "x_min": 0.03,
                "x_max": 0.10,
                "y_min": 0.05,
                "y_max": 0.11,
            },
        },
        {
            "text": "MOVE",
            "is_visible": True,
            "is_enabled": True,
            "bbox": {
                "x_min": 0.28,
                "x_max": 0.50,
                "y_min": 0.91,
                "y_max": 0.98,
            },
        },
    ]
    unbound = destination_picker_empty_stall_assessment(
        elements,
        {"type": "tap", "x": 0.385, "y": 0.075},
        screen_width=1080,
        screen_height=2400,
    )
    assert unbound["control_bound_tap"] is False
    assert unbound["unsupported_tap"]
    assert unbound["stalling_action"]

    drawer = destination_picker_empty_stall_assessment(
        elements,
        {"type": "tap", "x": 0.065, "y": 0.08},
        screen_width=1080,
        screen_height=2400,
    )
    assert drawer["control_bound_tap"] is True
    assert not drawer["unsupported_tap"]
    assert not drawer["stalling_action"]

    commit = destination_picker_empty_stall_assessment(
        elements,
        {"type": "tap", "x": 0.385, "y": 0.945},
        screen_width=1080,
        screen_height=2400,
    )
    assert commit["control_bound_tap"] is True
    assert not commit["unsupported_tap"]
    assert not commit["stalling_action"]


def test_destination_picker_guard_blocks_empty_wait_or_swipe() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Move a file")
    elements = [{"text": "No items", "is_visible": True}]
    wait_action = {"type": "wait", "duration_ms": 1000}
    assessment = destination_picker_empty_stall_assessment(
        elements,
        wait_action,
    )
    with pytest.raises(
        ActionValidationError,
        match="DESTINATION_PICKER_EMPTY_STALL_REQUIRED",
    ):
        guard.validate_decision(
            decision(wait_action),
            page_sha256="empty-picker",
            destination_picker_is_active=True,
            destination_picker_empty_stall_assessment=assessment,
        )
    guard.validate_decision(
        decision({"type": "tap", "x": 0.07, "y": 0.08}),
        page_sha256="empty-picker",
        destination_picker_is_active=True,
        destination_picker_empty_stall_assessment=(
            destination_picker_empty_stall_assessment(
                elements,
                {"type": "tap", "x": 0.07, "y": 0.08},
            )
        ),
    )
    audit = guard.audit_record()
    assert audit["destination_picker_empty_stall_block_count"] == 1
    assert audit["validation_blocks"][-1]["reason"] == (
        "destination_picker_empty_stall_blocked"
    )


def test_destination_picker_guard_blocks_empty_unbound_tap() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Move a file")
    elements = [
        {"text": "No items", "is_visible": True},
        {
            "content_description": "Show roots",
            "is_visible": True,
            "is_enabled": True,
            "bbox": {
                "x_min": 0.03,
                "x_max": 0.10,
                "y_min": 0.05,
                "y_max": 0.11,
            },
        },
    ]
    action = {"type": "tap", "x": 0.385, "y": 0.075}
    assessment = destination_picker_empty_stall_assessment(
        elements,
        action,
        screen_width=1080,
        screen_height=2400,
    )
    with pytest.raises(
        ActionValidationError,
        match="DESTINATION_PICKER_EMPTY_STALL_REQUIRED",
    ):
        guard.validate_decision(
            decision(action),
            page_sha256="empty-picker",
            destination_picker_is_active=True,
            destination_picker_empty_stall_assessment=assessment,
        )
    assert (
        guard.audit_record()["destination_picker_empty_stall_block_count"]
        == 1
    )


def files_roots_drawer_elements() -> list[dict]:
    labels = [
        "Recent",
        "Images",
        "Videos",
        "Audio",
        "Documents",
        "Downloads",
        "sdk_gphone64_x86_64",
    ]
    return [
        {
            "text": label,
            "is_visible": True,
            "is_enabled": True,
            "bbox": {
                "x_min": 0.02,
                "x_max": 0.58,
                "y_min": 0.12 + index * 0.10,
                "y_max": 0.20 + index * 0.10,
            },
        }
        for index, label in enumerate(labels)
    ]


def test_files_roots_drawer_assessment_requires_visible_row_hit() -> None:
    elements = files_roots_drawer_elements()
    unbound = files_roots_drawer_action_assessment(
        elements,
        {"type": "tap", "x": 0.08, "y": 0.08},
        screen_width=1080,
        screen_height=2400,
    )
    assert unbound == {
        "schema_version": "files_roots_drawer_action_assessment.v1",
        "adjudicable": True,
        "action_type": "tap",
        "drawer_active": True,
        "matched_root_control_count": 0,
        "standard_root_label_count": 6,
        "standard_root_vertical_band_count": 6,
        "usable_root_control_count": 7,
        "usable_storage_row_visible": True,
        "visible_storage_root_count": 1,
        "progress_action_required": True,
    }
    assert not any(
        key in unbound
        for key in ("text", "label", "bbox", "coordinate", "target")
    )

    swipe = files_roots_drawer_action_assessment(
        elements,
        {
            "type": "swipe",
            "x": 0.5,
            "y": 0.8,
            "x2": 0.5,
            "y2": 0.2,
            "duration_ms": 500,
        },
        screen_width=1080,
        screen_height=2400,
    )
    assert swipe["progress_action_required"]

    root_tap = files_roots_drawer_action_assessment(
        elements,
        {"type": "tap", "x": 0.30, "y": 0.76},
        screen_width=1080,
        screen_height=2400,
    )
    assert root_tap["matched_root_control_count"] == 1
    assert not root_tap["progress_action_required"]


def test_files_roots_drawer_rejects_main_storage_grid_false_positive() -> None:
    elements = [
        {
            "text": "sdk_gphone64_x86_64",
            "is_visible": True,
            "is_enabled": True,
            "bbox": {
                "x_min": 0.05,
                "x_max": 0.40,
                "y_min": 0.08,
                "y_max": 0.12,
            },
        },
    ]
    for index, label in enumerate(
        ["Images", "Audio", "Videos", "Documents"]
    ):
        elements.append(
            {
                "text": label,
                "is_visible": True,
                "is_enabled": True,
                "bbox": {
                    "x_min": 0.02 + index * 0.18,
                    "x_max": 0.16 + index * 0.18,
                    "y_min": 0.14,
                    "y_max": 0.19,
                },
            }
        )
    elements.extend(
        [
            {
                "text": "Documents",
                "is_visible": True,
                "is_enabled": True,
                "bbox": {
                    "x_min": 0.06,
                    "x_max": 0.48,
                    "y_min": 0.35,
                    "y_max": 0.43,
                },
            },
            {
                "text": "Downloads",
                "is_visible": True,
                "is_enabled": True,
                "bbox": {
                    "x_min": 0.51,
                    "x_max": 0.73,
                    "y_min": 0.35,
                    "y_max": 0.43,
                },
            },
        ]
    )
    assessment = files_roots_drawer_action_assessment(
        elements,
        {"type": "tap", "x": 0.75, "y": 0.52},
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["standard_root_label_count"] == 5
    assert assessment["standard_root_vertical_band_count"] == 2
    assert not assessment["drawer_active"]
    assert not assessment["adjudicable"]
    assert not assessment["progress_action_required"]


def test_files_roots_drawer_guard_blocks_unbound_navigation() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Move a file")
    action = {"type": "tap", "x": 0.08, "y": 0.08}
    assessment = files_roots_drawer_action_assessment(
        files_roots_drawer_elements(),
        action,
        screen_width=1080,
        screen_height=2400,
    )
    with pytest.raises(
        ActionValidationError,
        match="FILES_ROOTS_DRAWER_SELECTION_REQUIRED",
    ):
        guard.validate_decision(
            decision(action),
            page_sha256="open-roots-drawer",
            files_roots_drawer_action_assessment=assessment,
        )
    audit = guard.audit_record()
    assert audit["files_roots_drawer_block_count"] == 1
    assert audit["validation_blocks"][-1]["reason"] == (
        "files_roots_drawer_progress_action_required"
    )


def test_exact_selection_assessment_uses_full_text_and_nearest_tile() -> None:
    files = [
        {
            "text": "nature_sounds_backup.mp3",
            "is_visible": True,
            "bbox": {
                "x_min": 0.62,
                "x_max": 0.91,
                "y_min": 0.55,
                "y_max": 0.60,
            },
        },
        {
            "text": "nature_sounds.mp3",
            "is_visible": True,
            "bbox": {
                "x_min": 0.62,
                "x_max": 0.91,
                "y_min": 0.80,
                "y_max": 0.85,
            },
        },
    ]
    wrong = exact_selection_long_press_assessment(
        files,
        {
            "type": "long_press",
            "x": 0.75,
            "y": 0.51,
            "duration_ms": 800,
        },
        required_text="nature_sounds.mp3",
        screen_width=1080,
        screen_height=2400,
    )
    assert wrong["adjudicable"]
    assert not wrong["matched"]
    assert wrong["exact_text_visible"]
    assert wrong["nearest_text"] == "nature_sounds_backup.mp3"
    correct = exact_selection_long_press_assessment(
        files,
        {
            "type": "long_press",
            "x": 0.75,
            "y": 0.76,
            "duration_ms": 800,
        },
        required_text="nature_sounds.mp3",
        screen_width=1080,
        screen_height=2400,
    )
    assert correct["matched"]
    assert correct["nearest_text"] == "nature_sounds.mp3"


def test_exact_selection_guard_blocks_wrong_full_filename() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(
        goal="Move nature_sounds.mp3",
        required_selection_text="nature_sounds.mp3",
    )
    assessment = {
        "schema_version": "exact_selection_assessment.v1",
        "adjudicable": True,
        "matched": False,
        "required_text": "nature_sounds.mp3",
        "exact_text_visible": True,
        "candidate_count": 3,
        "nearest_text": "nature_sounds_backup.mp3",
        "nearest_distance": 0.03,
    }
    with pytest.raises(ActionValidationError, match="EXACT_TARGET_GUARD"):
        try:
            guard.validate_decision(
                decision(
                    {
                        "type": "long_press",
                        "x": 0.75,
                        "y": 0.51,
                        "duration_ms": 800,
                    }
                ),
                page_sha256="music-grid",
                exact_selection_assessment=assessment,
            )
        except ActionValidationError as error:
            assert "Do not return any long_press in this repair" in str(error)
            assert "non-long-press information-gathering action" in str(error)
            raise
    assessment["matched"] = True
    assessment["nearest_text"] = "nature_sounds.mp3"
    guard.validate_decision(
        decision(
            {
                "type": "long_press",
                "x": 0.75,
                "y": 0.76,
                "duration_ms": 800,
            }
        ),
        page_sha256="music-grid",
        exact_selection_assessment=assessment,
    )
    assert guard.audit_record()["exact_target_long_press_block_count"] == 1


def test_exact_selection_guard_names_offscreen_target_and_nearest_file() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(
        goal="Move nature_sounds.mp3",
        required_selection_text="nature_sounds.mp3",
    )
    assessment = {
        "schema_version": "exact_selection_assessment.v1",
        "adjudicable": True,
        "matched": False,
        "required_text": "nature_sounds.mp3",
        "exact_text_visible": False,
        "candidate_count": 8,
        "nearest_text": "nature_sounds_2023_02_11.mp3",
        "nearest_distance": 0.11375,
    }
    with pytest.raises(ActionValidationError) as caught:
        guard.validate_decision(
            decision(
                {
                    "type": "long_press",
                    "x": 0.75,
                    "y": 0.75,
                    "duration_ms": 800,
                }
            ),
            page_sha256="music-grid",
            exact_selection_assessment=assessment,
        )
    message = str(caught.value)
    assert "EXACT_TARGET_GUARD" in message
    assert '"nature_sounds.mp3" is not visible' in message
    assert '"nature_sounds_2023_02_11.mp3"' in message
    assert "Do not return any long_press on this screen" in message
    assert "non-long-press navigation action" in message


def test_post_destination_transfer_command_detects_text_control_hit() -> None:
    controls = [
        {
            "text": "Move to…",
            "is_visible": True,
            "is_enabled": True,
            "bbox": {
                "x_min": 0.55,
                "x_max": 0.95,
                "y_min": 0.31,
                "y_max": 0.37,
            },
        }
    ]
    assert post_destination_transfer_command_action(
        controls,
        {"type": "tap", "x": 0.67, "y": 0.344},
        screen_width=1080,
        screen_height=2400,
    )
    assert not post_destination_transfer_command_action(
        controls,
        {"type": "tap", "x": 0.08, "y": 0.08},
        screen_width=1080,
        screen_height=2400,
    )


def test_destination_picker_guard_blocks_back_but_allows_drawer() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Move a file")
    with pytest.raises(
        ActionValidationError,
        match="DESTINATION_PICKER_GUARD",
    ):
        guard.validate_decision(
            decision({"type": "press_back"}),
            page_sha256="picker",
            destination_picker_is_active=True,
        )
    guard.validate_decision(
        decision({"type": "tap", "x": 0.07, "y": 0.08}),
        page_sha256="picker",
        destination_picker_is_active=True,
    )
    guard.validate_decision(
        decision({"type": "press_back"}),
        page_sha256="ordinary-folder",
        destination_picker_is_active=False,
    )
    audit = guard.audit_record()
    assert audit["destination_picker_back_block_count"] == 1
    assert audit["validation_blocks"][-1]["reason"] == (
        "destination_picker_back_blocked"
    )


def test_destination_picker_allows_back_to_cancel_post_commit_repeat() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Move a file")
    guard.post_destination_commit_active = True
    guard.validate_decision(
        decision({"type": "press_back"}),
        page_sha256="second-picker",
        destination_picker_is_active=True,
    )
    assert (
        guard.audit_record()["destination_picker_back_block_count"] == 0
    )


def test_post_destination_commit_blocks_transfer_wait_and_reselection() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Move a file")
    guard.observe_transition(
        before_sha256="picker",
        action={"type": "tap", "x": 0.385, "y": 0.945},
        after_sha256="source",
        destination_picker_commit_executed=True,
    )
    guard.validate_decision(
        decision({"type": "tap", "x": 0.07, "y": 0.08}),
        page_sha256="source",
    )
    with pytest.raises(
        ActionValidationError,
        match="POST_DESTINATION_COMMIT_GUARD",
    ):
        guard.validate_decision(
            decision({"duration_ms": 1000, "type": "wait"}),
            page_sha256="source",
        )
    with pytest.raises(
        ActionValidationError,
        match="POST_DESTINATION_COMMIT_GUARD",
    ):
        guard.validate_decision(
            decision(
                {
                    "duration_ms": 800,
                    "type": "long_press",
                    "x": 0.25,
                    "y": 0.625,
                }
            ),
            page_sha256="destination",
            exact_selection_assessment={
                "adjudicable": True,
                "matched": True,
            },
        )
    with pytest.raises(
        ActionValidationError,
        match="POST_DESTINATION_COMMIT_GUARD",
    ):
        guard.validate_decision(
            decision({"type": "tap", "x": 0.67, "y": 0.344}),
            page_sha256="selection-menu",
            post_destination_transfer_command_is_action=True,
        )
    with pytest.raises(
        ActionValidationError,
        match="POST_DESTINATION_COMMIT_GUARD",
    ):
        guard.validate_decision(
            decision({"type": "tap", "x": 0.385, "y": 0.945}),
            page_sha256="picker-again",
            destination_picker_is_active=True,
            destination_picker_commit_is_action=True,
        )
    audit = guard.audit_record()
    assert audit["destination_picker_commit_count"] == 1
    assert audit["post_destination_commit_block_count"] == 4
    assert audit["post_destination_commit_active"]
