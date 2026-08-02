from __future__ import annotations

import pytest

from raven_m.actions.schema import ActionValidationError
from raven_m.controller.protocol_v2_guard import (
    ProtocolV2DecisionGuard,
    bounded_task_repeated_tap_assessment,
    canonical_action_key,
    coordinate_type_text_target_assessment,
    dated_list_answer_assessment,
    declared_text_source_assessment,
    destination_picker_active,
    destination_picker_commit_action,
    destination_picker_empty_stall_assessment,
    destination_picker_navigation_drawer_action,
    exact_selection_long_press_assessment,
    files_view_mode_toggle_action_assessment,
    files_roots_drawer_action_assessment,
    focused_empty_editable_tap_assessment,
    focused_editable_input_assessment,
    post_destination_source_context_assessment,
    post_destination_verification_navigation_assessment,
    post_destination_transfer_command_action,
    requested_field_value_assessment,
    semantic_ui_snapshot,
    soft_keyboard_swipe_assessment,
    swipe_direction_consistency_assessment,
    task_literal_field_role_assessment,
    toolbar_affordance_claim_assessment,
    visible_control_activation_retry_assessment,
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


def chronological_toolbar_fixture(label: str) -> list[dict]:
    return [
        {
            "package_name": "org.example.history",
            "content_description": label,
            "is_visible": True,
            "is_enabled": True,
            "is_clickable": True,
            "bbox": {"x_min": 0.76, "x_max": 0.90,
                     "y_min": 0.05, "y_max": 0.12},
        },
        {
            "package_name": "org.example.history",
            "text": "Today",
            "is_visible": True,
            "bbox": {"x_min": 0.06, "x_max": 0.24,
                     "y_min": 0.20, "y_max": 0.24},
        },
        {
            "package_name": "org.example.history",
            "text": "Friday",
            "is_visible": True,
            "bbox": {"x_min": 0.06, "x_max": 0.24,
                     "y_min": 0.43, "y_max": 0.47},
        },
        {
            "package_name": "org.example.history",
            "text": "7 Oct",
            "is_visible": True,
            "bbox": {"x_min": 0.06, "x_max": 0.24,
                     "y_min": 0.72, "y_max": 0.76},
        },
    ]


def toolbar_decision(label: str) -> dict:
    return {
        "status": "continue",
        "action": {"type": "tap", "x": 0.83, "y": 0.085},
        "expected_outcome": label,
        "decision_summary": "Use the visible top toolbar control.",
        "state_delta": [],
        "memory_citations": [],
    }


def dated_activity_list_fixture(
    *,
    explicit_type: bool = False,
    clickable_rows: bool = True,
) -> list[dict]:
    rows = [
        ("Bicycle Adventure", "2 Oct", 0.60),
        ("Skill work", "24 Sep", 0.75),
        ("Recovery day", "24 Sep", 0.84),
    ]
    elements: list[dict] = []
    for name, date, center in rows:
        elements.extend(
            [
                {
                    "package_name": "org.example.history",
                    "text": name,
                    "is_visible": True,
                    "bbox": {
                        "x_min": 0.08,
                        "x_max": 0.70,
                        "y_min": center - 0.035,
                        "y_max": center + 0.035,
                    },
                },
                {
                    "package_name": "org.example.history",
                    "text": date,
                    "is_visible": True,
                    "bbox": {
                        "x_min": 0.88,
                        "x_max": 0.98,
                        "y_min": center - 0.035,
                        "y_max": center + 0.035,
                    },
                },
            ]
        )
        if clickable_rows:
            elements.append(
                {
                    "package_name": "org.example.history",
                    "is_visible": True,
                    "is_enabled": True,
                    "is_clickable": True,
                    "bbox": {
                        "x_min": 0.02,
                        "x_max": 0.98,
                        "y_min": center - 0.04,
                        "y_max": center + 0.04,
                    },
                }
            )
    if explicit_type:
        elements.extend(
            [
                {
                    "package_name": "org.example.history",
                    "text": "Activity type",
                    "is_visible": True,
                    "bbox": {"x_min": 0.08, "x_max": 0.30,
                             "y_min": 0.68, "y_max": 0.71},
                },
                {
                    "package_name": "org.example.history",
                    "text": "Cycling",
                    "is_visible": True,
                    "bbox": {"x_min": 0.32, "x_max": 0.55,
                             "y_min": 0.72, "y_max": 0.78},
                },
                {
                    "package_name": "org.example.history",
                    "text": "Inline skating",
                    "is_visible": True,
                    "bbox": {"x_min": 0.32, "x_max": 0.60,
                             "y_min": 0.81, "y_max": 0.87},
                },
            ]
        )
    return elements


def answer_decision(text: str) -> dict:
    return {
        "status": "done",
        "action": {
            "type": "answer",
            "text": text,
            "text_origin": "current_screen",
            "source_memory_ids": [],
        },
        "memory_citations": [],
    }


def test_dated_list_answer_replays_r62_date_and_field_mismatch() -> None:
    assessment = dated_list_answer_assessment(
        (
            "What activities did I do September 24 2023? "
            "Answer with the activity type only."
        ),
        dated_activity_list_fixture(),
        answer_decision("Bicycle Adventure, Recovery day"),
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["target_date_list_visible"]
    assert assessment["target_row_count"] == 2
    assert assessment["requested_answer_role"] == "activity type"
    assert assessment["requested_field_detail_required"]
    assert assessment["answer_item_count_matches_target_rows"]
    bindings = {item["item"]: item for item in assessment["item_bindings"]}
    assert not bindings["Bicycle Adventure"]["target_row_bound"]
    assert bindings["Recovery day"]["target_row_bound"]
    assert not assessment["all_answer_items_target_row_bound"]


def test_dated_list_accepts_target_bound_names_when_names_are_requested() -> None:
    assessment = dated_list_answer_assessment(
        (
            "What activities did I do September 24 2023? "
            "Answer with the activity name only."
        ),
        dated_activity_list_fixture(),
        answer_decision("Skill work, Recovery day"),
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["target_date_list_visible"]
    assert assessment["requested_answer_role"] == "activity name"
    assert not assessment["role_detail_required"]
    assert not assessment["requested_field_detail_required"]
    assert assessment["answer_item_count_matches_target_rows"]
    assert assessment["all_answer_items_target_row_bound"]


def test_dated_list_recognizes_plural_requested_field_role() -> None:
    assessment = dated_list_answer_assessment(
        (
            "What activities did I do September 24 2023? "
            "Answer with the activity types only."
        ),
        dated_activity_list_fixture(),
        answer_decision("Skill work, Recovery day"),
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["requested_answer_role"] == "activity types"
    assert assessment["role_detail_required"]
    assert assessment["requested_field_detail_required"]


def test_dated_list_accepts_explicit_target_bound_requested_field() -> None:
    assessment = dated_list_answer_assessment(
        (
            "What activities did I do September 24 2023? "
            "Answer with the activity type only."
        ),
        dated_activity_list_fixture(explicit_type=True),
        answer_decision("Cycling, Inline skating"),
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["field_role_explicitly_visible"]
    assert not assessment["requested_field_detail_required"]
    assert assessment["answer_item_count_matches_target_rows"]
    assert assessment["all_answer_items_target_row_bound"]


def test_dated_list_target_row_tap_is_coordinate_and_control_bound() -> None:
    goal = (
        "What activities did I do September 24 2023? "
        "Answer with the activity type only."
    )
    target = dated_list_answer_assessment(
        goal,
        dated_activity_list_fixture(),
        {"action": {"type": "tap", "x": 0.45, "y": 0.75}},
        screen_width=1080,
        screen_height=2400,
    )
    other = dated_list_answer_assessment(
        goal,
        dated_activity_list_fixture(),
        {"action": {"type": "tap", "x": 0.45, "y": 0.60}},
        screen_width=1080,
        screen_height=2400,
    )
    assert target["target_row_tap_permitted"]
    assert target["target_row_tap_authority"] == "accessibility_clickable"
    assert not other["target_row_tap_permitted"]


def test_dated_list_replays_r63_visual_row_tap_without_clickable_node() -> None:
    goal = (
        "What activities did I do September 24 2023? "
        "Answer with the activity type only."
    )
    assessment = dated_list_answer_assessment(
        goal,
        dated_activity_list_fixture(clickable_rows=False),
        {"action": {"type": "tap", "x": 0.5, "y": 0.75}},
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["row_aligned_tap"]
    assert assessment["tap_on_content_side"]
    assert not assessment["clickable_target_hit"]
    assert assessment["visible_content_target_hit"]
    assert assessment["target_row_tap_index"] == 0
    assert assessment["target_row_tap_permitted"]
    assert assessment["target_row_tap_authority"] == (
        "visible_content_row_geometry"
    )


def test_dated_list_visual_fallback_rejects_date_column_and_non_target() -> None:
    goal = (
        "What activities did I do September 24 2023? "
        "Answer with the activity type only."
    )
    elements = dated_activity_list_fixture(clickable_rows=False)
    date_column = dated_list_answer_assessment(
        goal,
        elements,
        {"action": {"type": "tap", "x": 0.93, "y": 0.75}},
        screen_width=1080,
        screen_height=2400,
    )
    non_target = dated_list_answer_assessment(
        goal,
        elements,
        {"action": {"type": "tap", "x": 0.5, "y": 0.60}},
        screen_width=1080,
        screen_height=2400,
    )
    assert not date_column["tap_on_content_side"]
    assert not date_column["target_row_tap_permitted"]
    assert not non_target["row_aligned_tap"]
    assert not non_target["target_row_tap_permitted"]


def test_dated_list_visual_fallback_requires_same_row_content() -> None:
    elements = [
        element
        for element in dated_activity_list_fixture(clickable_rows=False)
        if element.get("text")
        in {"Bicycle Adventure", "2 Oct", "24 Sep"}
    ]
    assessment = dated_list_answer_assessment(
        (
            "What activities did I do September 24 2023? "
            "Answer with the activity type only."
        ),
        elements,
        {"action": {"type": "tap", "x": 0.5, "y": 0.75}},
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["target_date_list_visible"]
    assert assessment["target_row_content_labels"] == [[], []]
    assert not assessment["visible_content_target_hit"]
    assert not assessment["target_row_tap_permitted"]


def test_dated_list_visual_fallback_supports_left_date_column() -> None:
    elements: list[dict] = []
    for name, date, center in (
        ("Recent item", "2 Oct", 0.60),
        ("First target", "24 Sep", 0.75),
        ("Second target", "24 Sep", 0.84),
    ):
        elements.extend(
            [
                {
                    "text": date,
                    "is_visible": True,
                    "bbox": {"x_min": 0.05, "x_max": 0.15,
                             "y_min": center - 0.03,
                             "y_max": center + 0.03},
                },
                {
                    "text": name,
                    "is_visible": True,
                    "bbox": {"x_min": 0.30, "x_max": 0.85,
                             "y_min": center - 0.03,
                             "y_max": center + 0.03},
                },
            ]
        )
    assessment = dated_list_answer_assessment(
        "Find September 24 2023. Answer with the item name only.",
        elements,
        {"action": {"type": "tap", "x": 0.5, "y": 0.75}},
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["target_row_date_sides"] == ["left", "left"]
    assert assessment["visible_content_target_hit"]
    assert assessment["target_row_tap_permitted"]


def test_dated_list_visual_fallback_fails_closed_for_center_date_column() -> None:
    elements: list[dict] = []
    for name, date, center in (
        ("Recent item", "2 Oct", 0.60),
        ("First target", "24 Sep", 0.75),
        ("Second target", "24 Sep", 0.84),
    ):
        elements.extend(
            [
                {
                    "text": date,
                    "is_visible": True,
                    "bbox": {"x_min": 0.45, "x_max": 0.55,
                             "y_min": center - 0.03,
                             "y_max": center + 0.03},
                },
                {
                    "text": name,
                    "is_visible": True,
                    "bbox": {"x_min": 0.65, "x_max": 0.90,
                             "y_min": center - 0.03,
                             "y_max": center + 0.03},
                },
            ]
        )
    assessment = dated_list_answer_assessment(
        "Find September 24 2023. Answer with the item name only.",
        elements,
        {"action": {"type": "tap", "x": 0.75, "y": 0.775}},
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["target_row_date_sides"] == [
        "ambiguous",
        "ambiguous",
    ]
    assert not assessment["visible_content_target_hit"]
    assert not assessment["target_row_tap_permitted"]


def test_guard_blocks_swipe_after_target_date_is_visible() -> None:
    goal = (
        "What activities did I do September 24 2023? "
        "Answer with the activity type only."
    )
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal=goal)
    proposed = decision(
        {"type": "swipe", "x": 0.5, "y": 0.8,
         "x2": 0.5, "y2": 0.2, "duration_ms": 500}
    )
    assessment = dated_list_answer_assessment(
        goal,
        dated_activity_list_fixture(),
        proposed,
        screen_width=1080,
        screen_height=2400,
    )
    with pytest.raises(ActionValidationError, match="TARGET_DATE_VISIBLE_GUARD"):
        guard.validate_decision(
            proposed,
            page_sha256="dated-list",
            dated_list_answer_assessment=assessment,
        )
    assert guard.audit_record()["target_date_visible_swipe_block_count"] == 1


def test_guard_blocks_r62_terminal_answer_association() -> None:
    goal = (
        "What activities did I do September 24 2023? "
        "Answer with the activity type only."
    )
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal=goal)
    proposed = answer_decision("Bicycle Adventure, Recovery day")
    assessment = dated_list_answer_assessment(
        goal,
        dated_activity_list_fixture(),
        proposed,
        screen_width=1080,
        screen_height=2400,
    )
    with pytest.raises(ActionValidationError, match="ANSWER_ASSOCIATION_GUARD"):
        guard.validate_decision(
            proposed,
            page_sha256="dated-list",
            dated_list_answer_assessment=assessment,
        )
    audit = guard.audit_record()
    assert audit["answer_association_block_count"] == 1
    assert audit["target_date_row_count"] == 2


def test_guard_requires_all_observed_target_rows_before_detail_answer() -> None:
    goal = (
        "What activities did I do September 24 2023? "
        "Answer with the activity type only."
    )
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal=goal)
    tap = decision({"type": "tap", "x": 0.45, "y": 0.75})
    list_assessment = dated_list_answer_assessment(
        goal,
        dated_activity_list_fixture(),
        tap,
        screen_width=1080,
        screen_height=2400,
    )
    guard.validate_decision(
        tap,
        page_sha256="dated-list",
        dated_list_answer_assessment=list_assessment,
    )
    one_item = answer_decision("Cycling")
    detail_assessment = dated_list_answer_assessment(
        goal,
        [
            {
                "text": "Cycling",
                "resource_id": "example/track_edit_activity_type",
                "is_visible": True,
                "bbox": {
                    "x_min": 0.05,
                    "x_max": 0.85,
                    "y_min": 0.15,
                    "y_max": 0.22,
                },
            },
        ],
        one_item,
        screen_width=1080,
        screen_height=2400,
    )
    with pytest.raises(
        ActionValidationError,
        match="TARGET_ROW_ENUMERATION_GUARD",
    ):
        guard.validate_decision(
            one_item,
            page_sha256="detail",
            dated_list_answer_assessment=detail_assessment,
            requested_field_value_assessment=(
                requested_field_value_assessment(
                    goal,
                    [
                        {
                            "text": "Cycling",
                            "resource_id": (
                                "example/track_edit_activity_type"
                            ),
                            "is_visible": True,
                            "bbox": {
                                "x_min": 0.05,
                                "x_max": 0.85,
                                "y_min": 0.15,
                                "y_max": 0.22,
                            },
                        }
                    ],
                    one_item,
                    screen_width=1080,
                    screen_height=2400,
                )
            ),
        )


def test_requested_field_value_assessment_withholds_value_and_binds_role() -> None:
    goal = (
        "What activities did I do September 24 2023? "
        "Answer with the activity type only."
    )
    elements = [
        {
            "text": "Visible row title",
            "resource_id": "example/track_edit_name",
            "is_visible": True,
            "bbox": {"x_min": 0.02, "x_max": 0.95,
                     "y_min": 0.06, "y_max": 0.13},
        },
        {
            "text": "Exact category value",
            "resource_id": "example/track_edit_activity_type",
            "is_visible": True,
            "bbox": {"x_min": 0.02, "x_max": 0.90,
                     "y_min": 0.15, "y_max": 0.22},
        },
        {
            "text": "Save",
            "is_visible": True,
            "is_clickable": True,
            "bbox": {"x_min": 0.50, "x_max": 1.00,
                     "y_min": 0.83, "y_max": 0.90},
        },
    ]
    back = decision({"type": "press_back"})
    assessment = requested_field_value_assessment(
        goal,
        elements,
        back,
        screen_width=1080,
        screen_height=2400,
    )

    assert assessment["explicit_value_visible"] is True
    assert assessment["explicit_value_control_count"] == 1
    assert assessment["matched_metadata_fields"] == ["resource_id"]
    assert assessment["read_only_inspection_safe"] is True
    serialized = str(assessment)
    assert "Exact category value" not in serialized
    assert "Visible row title" not in serialized

    save = decision({"type": "tap", "x": 0.75, "y": 0.86})
    save_assessment = requested_field_value_assessment(
        goal,
        elements,
        save,
        screen_width=1080,
        screen_height=2400,
    )
    assert save_assessment["mutation_control_hit"] is True
    assert save_assessment["mutation_control_hit_labels"] == ["Save"]
    assert save_assessment["visible_control_hit"] is True
    assert save_assessment["read_only_inspection_safe"] is False

    selector = decision({"type": "tap", "x": 0.50, "y": 0.18})
    selector_assessment = requested_field_value_assessment(
        goal,
        elements,
        selector,
        screen_width=1080,
        screen_height=2400,
    )
    assert selector_assessment["requested_field_control_hit"] is True
    assert selector_assessment["mutation_control_hit"] is False
    assert selector_assessment["read_only_inspection_safe"] is False

    overflow = elements + [
        {
            "content_description": "More options",
            "is_visible": True,
            "is_clickable": True,
            "is_enabled": True,
            "bbox": {
                "x_min": 0.35,
                "x_max": 0.45,
                "y_min": 0.92,
                "y_max": 0.98,
            },
        }
    ]
    overflow_assessment = requested_field_value_assessment(
        goal,
        overflow,
        decision({"type": "tap", "x": 0.40, "y": 0.95}),
        screen_width=1080,
        screen_height=2400,
    )
    assert overflow_assessment["visible_control_hit"] is True
    assert overflow_assessment["visible_control_count"] == 2
    assert overflow_assessment["inspection_control_hit"] is True
    assert overflow_assessment["inspection_control_candidates"] == [
        {
            "label": "More options",
            "bbox": {
                "x_min": 0.35,
                "x_max": 0.45,
                "y_min": 0.92,
                "y_max": 0.98,
            },
            "center": {"x": 0.4, "y": 0.95},
        }
    ]
    assert overflow_assessment["mutation_control_hit"] is False


def test_requested_field_inspection_route_withholds_label_suffix() -> None:
    assessment = requested_field_value_assessment(
        "Return the activity type.",
        [
            {
                "text": "",
                "content_description": (
                    "More options hidden-answer-text"
                ),
                "is_visible": True,
                "is_clickable": True,
                "is_enabled": True,
                "bbox": {
                    "x_min": 0.35,
                    "x_max": 0.45,
                    "y_min": 0.92,
                    "y_max": 0.98,
                },
            }
        ],
        decision({"type": "tap", "x": 0.4, "y": 0.95}),
        screen_width=1000,
        screen_height=2400,
    )

    assert assessment["inspection_control_candidates"][0]["label"] == (
        "More options"
    )
    assert "hidden-answer-text" not in repr(assessment)


def test_guard_requires_explicit_requested_field_before_back() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(
        goal=(
            "What activities did I do September 24 2023? "
            "Answer with the activity type only."
        )
    )
    guard.target_date_row_count = 2
    guard.target_row_detail_required = True
    guard.requested_answer_role = "activity type"
    guard.target_row_visit_keys = ["target-row-y:0.750"]
    guard.active_target_row_visit_key = "target-row-y:0.750"

    with pytest.raises(
        ActionValidationError,
        match="TARGET_ROW_EXPLICIT_FIELD_GUARD",
    ):
        guard.validate_decision(
            decision({"type": "press_back"}),
            page_sha256="icon-only-detail",
            requested_field_value_assessment={
                "explicit_value_visible": False,
            },
        )

    audit = guard.audit_record()
    assert audit["target_row_explicit_field_block_count"] == 1
    assert audit["target_row_detail_frames"] == []
    assert audit["active_target_row_visit_key"] == "target-row-y:0.750"


def test_guard_blocks_r66_deferred_list_coordinate_on_active_detail() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(
        goal=(
            "What activities did I do September 24 2023? "
            "Answer with the activity type only."
        )
    )
    guard.target_date_row_count = 2
    guard.target_row_detail_required = True
    guard.requested_answer_role = "activity type"
    guard.target_row_visit_keys = ["target-row-y:0.747"]
    guard.active_target_row_visit_key = "target-row-y:0.747"
    guard.target_date_row_observations = [
        {
            "semantic_state_sha256": "dated-list",
            "target_row_count": 2,
            "target_row_centers": [0.747292, 0.834375],
            "requested_answer_role": "activity type",
        }
    ]

    with pytest.raises(
        ActionValidationError,
        match="TARGET_ROW_LEDGER_SCOPE_GUARD",
    ):
        guard.validate_decision(
            decision({"type": "tap", "x": 0.5, "y": 0.834}),
            page_sha256="active-detail",
            dated_list_answer_assessment={
                "target_date_list_visible": False,
            },
            requested_field_value_assessment={
                "explicit_value_visible": False,
                "visible_control_hit": False,
            },
        )

    audit = guard.audit_record()
    assert audit["target_row_off_list_coordinate_block_count"] == 1
    assert audit["active_target_row_visit_key"] == "target-row-y:0.747"
    assert audit["target_row_detail_frames"] == []


def test_guard_allows_visible_non_commit_control_on_active_detail() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Answer with the activity type only.")
    guard.target_date_row_count = 2
    guard.target_row_detail_required = True
    guard.requested_answer_role = "activity type"
    guard.target_row_visit_keys = ["target-row-y:0.747"]
    guard.active_target_row_visit_key = "target-row-y:0.747"
    guard.target_date_row_observations = [
        {
            "target_row_count": 2,
            "target_row_centers": [0.747292, 0.834375],
        }
    ]

    guard.validate_decision(
        decision({"type": "tap", "x": 0.40, "y": 0.95}),
        page_sha256="active-detail",
        dated_list_answer_assessment={"target_date_list_visible": False},
        requested_field_value_assessment={
            "explicit_value_visible": False,
            "visible_control_hit": True,
            "inspection_control_hit": True,
        },
    )

    audit = guard.audit_record()
    assert audit["target_row_off_list_coordinate_block_count"] == 0
    assert audit["active_target_row_visit_key"] == "target-row-y:0.747"


def test_guard_blocks_blank_tap_on_active_detail() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Answer with the activity type only.")
    guard.target_date_row_count = 2
    guard.target_row_detail_required = True
    guard.requested_answer_role = "activity type"
    guard.target_row_visit_keys = ["target-row-y:0.747"]
    guard.active_target_row_visit_key = "target-row-y:0.747"
    guard.target_date_row_observations = [
        {
            "target_row_count": 2,
            "target_row_centers": [0.747292, 0.834375],
        }
    ]

    with pytest.raises(
        ActionValidationError,
        match="TARGET_ROW_DETAIL_CONTROL_GUARD",
    ):
        guard.validate_active_target_detail_control(
            decision({"type": "tap", "x": 0.5, "y": 0.15}),
            page_sha256="active-detail",
            dated_list_answer_assessment={
                "target_date_list_visible": False,
            },
            requested_field_value_assessment={
                "explicit_value_visible": False,
                "visible_control_hit": False,
            },
        )

    audit = guard.audit_record()
    assert audit["target_row_non_control_tap_block_count"] == 1
    assert audit["target_row_off_list_coordinate_block_count"] == 0
    assert audit["active_target_row_visit_key"] == "target-row-y:0.747"


def test_guard_blocks_mutation_during_read_only_field_inspection() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(
        goal=(
            "What activities did I do September 24 2023? "
            "Answer with the activity type only."
        )
    )
    guard.target_date_row_count = 2
    guard.target_row_detail_required = True
    guard.requested_answer_role = "activity type"
    guard.target_row_visit_keys = ["target-row-y:0.750"]
    guard.active_target_row_visit_key = "target-row-y:0.750"

    with pytest.raises(
        ActionValidationError,
        match="TARGET_ROW_READ_ONLY_GUARD",
    ):
        guard.validate_decision(
            decision({"type": "tap", "x": 0.75, "y": 0.86}),
            page_sha256="explicit-field-form",
            requested_field_value_assessment={
                "explicit_value_visible": True,
                "mutation_control_hit": True,
                "mutation_control_hit_labels": ["Save"],
            },
        )

    audit = guard.audit_record()
    assert audit["target_row_read_only_mutation_block_count"] == 1
    assert audit["target_row_detail_frames"] == []
    assert audit["active_target_row_visit_key"] == "target-row-y:0.750"


def test_guard_blocks_requested_field_selector_during_read_only_inspection(
) -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(
        goal=(
            "What activities did I do September 24 2023? "
            "Answer with the activity type only."
        )
    )
    guard.target_date_row_count = 2
    guard.target_row_detail_required = True
    guard.requested_answer_role = "activity type"
    guard.target_row_visit_keys = ["target-row-y:0.750"]
    guard.active_target_row_visit_key = "target-row-y:0.750"

    with pytest.raises(
        ActionValidationError,
        match="TARGET_ROW_READ_ONLY_GUARD",
    ):
        guard.validate_decision(
            decision({"type": "tap", "x": 0.50, "y": 0.18}),
            page_sha256="explicit-field-form",
            requested_field_value_assessment={
                "explicit_value_visible": True,
                "mutation_control_hit": False,
                "requested_field_control_hit": True,
            },
        )

    audit = guard.audit_record()
    assert audit["target_row_read_only_mutation_block_count"] == 1
    assert audit["target_row_detail_frames"] == []
    assert audit["active_target_row_visit_key"] == "target-row-y:0.750"


def test_guard_requires_distinct_target_rows_not_repeated_same_row() -> None:
    goal = (
        "What activities did I do September 24 2023? "
        "Answer with the activity types only."
    )
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal=goal)
    first_tap = decision({"type": "tap", "x": 0.45, "y": 0.75})
    first_assessment = dated_list_answer_assessment(
        goal,
        dated_activity_list_fixture(),
        first_tap,
        screen_width=1080,
        screen_height=2400,
    )
    guard.validate_decision(
        first_tap,
        page_sha256="dated-list",
        dated_list_answer_assessment=first_assessment,
    )
    with pytest.raises(
        ActionValidationError,
        match="TARGET_ROW_UNVISITED_GUARD",
    ):
        guard.validate_decision(
            first_tap,
            page_sha256="dated-list-returned",
            dated_list_answer_assessment=first_assessment,
        )
    audit = guard.audit_record()
    assert audit["target_row_tap_validation_count"] == 1
    assert audit["target_row_distinct_visit_count"] == 1
    assert audit["target_row_revisit_block_count"] == 1
    block = audit["validation_blocks"][-1]
    assert block["unvisited_target_row_centers"] == [0.84]


def test_guard_allows_visual_answer_after_distinct_rows_and_frames() -> None:
    goal = (
        "What activities did I do September 24 2023? "
        "Answer with the activity types only."
    )
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal=goal)
    for y, page in ((0.75, "dated-list"), (0.84, "dated-list-returned")):
        tap = decision({"type": "tap", "x": 0.45, "y": y})
        assessment = dated_list_answer_assessment(
            goal,
            dated_activity_list_fixture(),
            tap,
            screen_width=1080,
            screen_height=2400,
        )
        guard.validate_decision(
            tap,
            page_sha256=page,
            dated_list_answer_assessment=assessment,
        )
        back = decision({"type": "press_back"})
        guard.validate_decision(
            back,
            page_sha256=f"detail-{y}",
            dated_list_answer_assessment={},
            dated_row_detail_frame={
                "visit_key": guard.active_target_row_visit_key,
                "path": f"C:/evidence/detail-{y}.png",
                "sha256": ("a" if y == 0.75 else "b") * 64,
                "source_path": f"C:/evidence/source-{y}.png",
                "source_sha256": (
                    "c" if y == 0.75 else "d"
                ) * 64,
                "requested_field_evidence_explicit": True,
            },
            requested_field_value_assessment={
                "explicit_value_visible": True,
            },
        )
    two_items = answer_decision("Cycling, Inline skating")
    list_assessment = dated_list_answer_assessment(
        goal,
        dated_activity_list_fixture(),
        two_items,
        screen_width=1080,
        screen_height=2400,
    )
    guard.validate_decision(
        two_items,
        page_sha256="dated-list-final",
        dated_list_answer_assessment=list_assessment,
        dated_visual_answer_assessment={
            "eligible": True,
            "accepted": True,
            "adjudicated": True,
        },
    )
    audit = guard.audit_record()
    assert audit["target_row_distinct_visit_count"] == 2
    assert len(audit["target_row_detail_frames"]) == 2
    assert audit["target_row_visual_answer_accept_count"] == 1
    assert audit["target_row_enumeration_block_count"] == 0


def test_target_row_visit_is_not_committed_when_later_loop_guard_blocks() -> None:
    goal = (
        "What activities did I do September 24 2023? "
        "Answer with the activity types only."
    )
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal=goal)
    tap = decision({"type": "tap", "x": 0.45, "y": 0.75})
    assessment = dated_list_answer_assessment(
        goal,
        dated_activity_list_fixture(),
        tap,
        screen_width=1080,
        screen_height=2400,
    )
    guard.blocked_fingerprints.add(
        ("dated-list", canonical_action_key(tap["action"]))
    )

    with pytest.raises(ActionValidationError, match="LOOP_GUARD"):
        guard.validate_decision(
            tap,
            page_sha256="dated-list",
            dated_list_answer_assessment=assessment,
        )

    audit = guard.audit_record()
    assert audit["target_row_distinct_visit_count"] == 0
    assert audit["target_row_tap_validation_count"] == 0
    assert audit["active_target_row_visit_key"] is None


def test_detail_frame_is_not_committed_when_later_loop_guard_blocks() -> None:
    goal = (
        "What activities did I do September 24 2023? "
        "Answer with the activity types only."
    )
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal=goal)
    guard.target_date_row_count = 2
    guard.target_row_detail_required = True
    guard.target_row_visit_keys = ["target-row-y:0.750"]
    guard.active_target_row_visit_key = "target-row-y:0.750"
    back = decision({"type": "press_back"})
    guard.blocked_fingerprints.add(
        ("detail", canonical_action_key(back["action"]))
    )

    with pytest.raises(ActionValidationError, match="LOOP_GUARD"):
        guard.validate_decision(
            back,
            page_sha256="detail",
            dated_row_detail_frame={
                "visit_key": "target-row-y:0.750",
                "path": "C:/evidence/detail.png",
                "sha256": "a" * 64,
                "source_path": "C:/evidence/source.png",
                "source_sha256": "b" * 64,
                "requested_field_evidence_explicit": True,
            },
            requested_field_value_assessment={
                "explicit_value_visible": True,
            },
        )

    audit = guard.audit_record()
    assert audit["target_row_detail_frames"] == []
    assert audit["active_target_row_visit_key"] == "target-row-y:0.750"


@pytest.mark.parametrize("label", ["Markers", "Search"])
def test_toolbar_role_mismatch_requires_older_history_scroll(
    label: str,
) -> None:
    assessment = toolbar_affordance_claim_assessment(
        "What happened on September 24 2023?",
        chronological_toolbar_fixture(label),
        toolbar_decision("Open the date picker for September 24, 2023."),
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["adjudicable"]
    assert assessment["expected_roles"] == ["date"]
    assert assessment["target_roles"] == [label.casefold().rstrip("s")]
    assert assessment["matched"] is False
    chronology = assessment["chronological_list_navigation_assessment"]
    assert chronology["chronological_history_detected"]
    assert chronology["target_visible"] is False
    assert chronology["target_older_than_visible_history"]
    assert chronology["scroll_toward_older_required"]


@pytest.mark.parametrize(
    ("control", "outcome", "role"),
    [
        ("Calendar", "Open the date picker.", "date"),
        ("Markers", "Open the Markers map.", "marker"),
        ("Search", "Open the Search field.", "search"),
    ],
)
def test_toolbar_role_match_is_accepted(
    control: str,
    outcome: str,
    role: str,
) -> None:
    assessment = toolbar_affordance_claim_assessment(
        "What happened on September 24 2023?",
        chronological_toolbar_fixture(control),
        toolbar_decision(outcome),
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["adjudicable"]
    assert assessment["expected_roles"] == [role]
    assert assessment["target_roles"] == [role]
    assert assessment["matched"]


def test_unknown_toolbar_role_does_not_block() -> None:
    assessment = toolbar_affordance_claim_assessment(
        "What happened on September 24 2023?",
        chronological_toolbar_fixture("More options"),
        toolbar_decision("Open the date picker."),
        screen_width=1080,
        screen_height=2400,
    )
    assert not assessment["adjudicable"]
    assert assessment["matched"] is None


def test_nonchronological_toolbar_mismatch_does_not_force_scroll() -> None:
    elements = chronological_toolbar_fixture("Markers")[:1]
    assessment = toolbar_affordance_claim_assessment(
        "What happened on September 24 2023?",
        elements,
        toolbar_decision("Open the date picker."),
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["adjudicable"]
    assert assessment["matched"] is False
    chronology = assessment["chronological_list_navigation_assessment"]
    assert not chronology["chronological_history_detected"]
    assert not chronology["scroll_toward_older_required"]


def test_visible_target_date_does_not_force_older_scroll() -> None:
    elements = chronological_toolbar_fixture("Markers")
    elements[-1]["text"] = "September 24"
    assessment = toolbar_affordance_claim_assessment(
        "What happened on September 24 2023?",
        elements,
        toolbar_decision("Open the date picker."),
        screen_width=1080,
        screen_height=2400,
    )
    chronology = assessment["chronological_list_navigation_assessment"]
    assert chronology["chronological_history_detected"]
    assert chronology["target_visible"]
    assert not chronology["scroll_toward_older_required"]


def test_newer_absent_target_date_does_not_force_older_scroll() -> None:
    assessment = toolbar_affordance_claim_assessment(
        "What happened on December 24 2023?",
        chronological_toolbar_fixture("Markers"),
        toolbar_decision("Open the date picker."),
        screen_width=1080,
        screen_height=2400,
    )
    chronology = assessment["chronological_list_navigation_assessment"]
    assert chronology["chronological_history_detected"]
    assert chronology["target_visible"] is False
    assert not chronology["target_older_than_visible_history"]
    assert not chronology["scroll_toward_older_required"]


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
    focused = {
        "schema_version": "focused_editable_input_assessment.v2",
        "present": True,
        "focused_count": 1,
        "empty": True,
        "soft_keyboard_present": True,
        "soft_keyboard_packages": [
            "com.google.android.inputmethod.latin"
        ],
        "input_ready": True,
    }
    with pytest.raises(
        ActionValidationError,
        match="POST_ACTIVATION_INPUT_READY",
    ):
        guard.validate_decision(
            decision(coordinate_action),
            page_sha256="same",
            coordinate_text_target_assessment=target,
            focused_input_assessment=focused,
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
        focused_input_assessment=focused,
    )


def test_post_activation_clear_text_requires_actual_focused_editable() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(goal="Search for the exact file")
    guard.mark_input_activation_repair(
        {"type": "tap", "x": 0.5, "y": 0.08}
    )
    unsafe = {
        "type": "type_text",
        "text": "nature_sounds.mp3",
        "text_origin": "task_literal",
        "source_memory_ids": [],
        "clear_text": True,
    }
    keyboard_only = {
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
    with pytest.raises(
        ActionValidationError,
        match="POST_ACTIVATION_CLEAR_TEXT_GUARD",
    ):
        guard.validate_decision(
            decision(unsafe),
            page_sha256="keyboard-only",
            focused_input_assessment=keyboard_only,
        )
    guard.validate_decision(
        decision({**unsafe, "clear_text": False}),
        page_sha256="keyboard-only",
        focused_input_assessment=keyboard_only,
    )
    assert guard.audit_record()[
        "post_activation_clear_text_block_count"
    ] == 1

    focused_guard = ProtocolV2DecisionGuard()
    focused_guard.reset(goal="Replace text in a focused field")
    focused_guard.mark_input_activation_repair(
        {"type": "tap", "x": 0.5, "y": 0.08}
    )
    focused_guard.validate_decision(
        decision(unsafe),
        page_sha256="focused-editable",
        focused_input_assessment={
            **keyboard_only,
            "present": True,
            "focused_count": 1,
        },
    )
    assert focused_guard.audit_record()[
        "post_activation_clear_text_block_count"
    ] == 0


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


def test_visible_control_activation_retry_binds_named_safe_control() -> None:
    assessment = visible_control_activation_retry_assessment(
        [
            {
                "package_name": "com.google.android.contacts",
                "content_description": "Create contact",
                "is_visible": True,
                "is_enabled": True,
                "is_clickable": True,
                "is_editable": False,
                "bbox": {
                    "x_min": 0.80,
                    "x_max": 0.94,
                    "y_min": 0.78,
                    "y_max": 0.89,
                },
            }
        ],
        {"type": "tap", "x": 0.87, "y": 0.835},
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment == {
        "schema_version": (
            "visible_control_activation_retry_assessment.v1"
        ),
        "adjudicable": True,
        "action_type": "tap",
        "matched_control_count": 1,
        "matched_packages": ["com.google.android.contacts"],
        "matched_labels": ["Create contact"],
        "commit_like": False,
        "permitted": True,
    }


@pytest.mark.parametrize(
    ("element", "reason"),
    [
        (
            {
                "package_name": "com.google.android.calendar",
                "text": "SAVE",
                "is_visible": True,
                "is_enabled": True,
                "is_clickable": True,
                "is_editable": False,
                "bbox": {
                    "x_min": 0.80,
                    "x_max": 0.94,
                    "y_min": 0.78,
                    "y_max": 0.89,
                },
            },
            "commit",
        ),
        (
            {
                "package_name": "com.google.android.contacts",
                "is_visible": True,
                "is_enabled": True,
                "is_clickable": True,
                "is_editable": False,
                "bbox": {
                    "x_min": 0.80,
                    "x_max": 0.94,
                    "y_min": 0.78,
                    "y_max": 0.89,
                },
            },
            "unlabelled",
        ),
        (
            {
                "package_name": "com.google.android.documentsui",
                "hint_text": "Search",
                "is_visible": True,
                "is_enabled": True,
                "is_clickable": True,
                "is_editable": True,
                "bbox": {
                    "x_min": 0.80,
                    "x_max": 0.94,
                    "y_min": 0.78,
                    "y_max": 0.89,
                },
            },
            "editable",
        ),
        (
            {
                "package_name": "com.android.systemui",
                "content_description": "Open panel",
                "is_visible": True,
                "is_enabled": True,
                "is_clickable": True,
                "is_editable": False,
                "bbox": {
                    "x_min": 0.80,
                    "x_max": 0.94,
                    "y_min": 0.78,
                    "y_max": 0.89,
                },
            },
            "system",
        ),
        (
            {
                "package_name": "com.google.android.inputmethod.latin",
                "text": "Next",
                "is_visible": True,
                "is_enabled": True,
                "is_clickable": True,
                "is_editable": False,
                "bbox": {
                    "x_min": 0.80,
                    "x_max": 0.94,
                    "y_min": 0.78,
                    "y_max": 0.89,
                },
            },
            "keyboard",
        ),
    ],
)
def test_visible_control_activation_retry_rejects_unsafe_targets(
    element: dict,
    reason: str,
) -> None:
    assessment = visible_control_activation_retry_assessment(
        [element],
        {"type": "tap", "x": 0.87, "y": 0.835},
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["permitted"] is False, reason


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


def repeated_button() -> dict:
    return {
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


def numeric_result(value: str, *, clickable: bool = False) -> dict:
    return {
        "package_name": "com.android.chrome",
        "class_name": "android.view.View",
        "text": value,
        "is_visible": True,
        "is_enabled": True,
        "is_clickable": clickable,
        "is_editable": False,
        "bbox": {
            "x_min": 0.46,
            "x_max": 0.54,
            "y_min": 0.14,
            "y_max": 0.18,
        },
    }


def task_repeat_assessment(
    *,
    goal: str = (
        "Open the task with Chrome, then click the button 5 times and "
        "enter their product."
    ),
    prior: int,
    no_effect: int = 0,
    element: dict | None = None,
) -> dict:
    return bounded_task_repeated_tap_assessment(
        goal,
        [element or repeated_button()],
        {"type": "tap", "x": 0.5, "y": 0.208},
        prior_identical_coordinate_action_count=prior,
        identical_coordinate_no_effect_count=no_effect,
        screen_width=1080,
        screen_height=2400,
    )


def test_guard_allows_only_fourth_and_fifth_task_bounded_taps() -> None:
    guard = ProtocolV2DecisionGuard(
        max_no_effect_repeats=10,
        max_identical_coordinate_actions=3,
    )
    guard.reset(goal="Click the button 5 times and enter their product.")
    action = {"type": "tap", "x": 0.5, "y": 0.208}
    for index in range(3):
        guard.validate_decision(
            decision(action),
            page_sha256=f"value-{index}",
        )
        guard.observe_transition(
            before_sha256=f"value-{index}",
            action=action,
            after_sha256=f"value-{index + 1}",
        )
    fourth = task_repeat_assessment(prior=3)
    assert fourth["permitted"]
    assert fourth["requested_repetitions"] == 5
    assert fourth["proposed_ordinal"] == 4
    guard.validate_decision(
        decision(action),
        page_sha256="value-3",
        bounded_task_repeated_tap_assessment=fourth,
    )
    guard.observe_transition(
        before_sha256="value-3",
        action=action,
        after_sha256="value-4",
    )
    fifth = task_repeat_assessment(prior=4)
    assert fifth["permitted"]
    guard.validate_decision(
        decision(action),
        page_sha256="value-4",
        bounded_task_repeated_tap_assessment=fifth,
    )
    guard.observe_transition(
        before_sha256="value-4",
        action=action,
        after_sha256="value-5",
    )
    sixth = task_repeat_assessment(prior=5)
    assert not sixth["permitted"]
    with pytest.raises(
        ActionValidationError,
        match="same coordinate tap or long-press",
    ):
        guard.validate_decision(
            decision(action),
            page_sha256="value-5",
            bounded_task_repeated_tap_assessment=sixth,
        )
    audit = guard.audit_record()
    assert audit["bounded_task_repeated_tap_override_count"] == 2
    assert [
        row["assessment"]["proposed_ordinal"]
        for row in audit["bounded_task_repeated_tap_override_records"]
    ] == [4, 5]


def test_guard_reconciles_one_delayed_semantic_repeat_then_bounds_count() -> None:
    guard = ProtocolV2DecisionGuard(
        max_no_effect_repeats=10,
        max_identical_coordinate_actions=3,
    )
    goal = (
        "Open the task with Chrome, then click the button 5 times and "
        "enter their product."
    )
    guard.reset(goal=goal)
    action = {"type": "tap", "x": 0.5, "y": 0.208}

    guard.validate_decision(decision(action), page_sha256="value-0")
    guard.observe_transition(
        before_sha256="value-0",
        action=action,
        after_sha256="value-0",
    )
    context = guard.repeated_tap_transition_context(
        page_sha256="value-1-delayed",
        action=action,
    )
    second = bounded_task_repeated_tap_assessment(
        goal,
        [repeated_button()],
        action,
        prior_identical_coordinate_action_count=1,
        identical_coordinate_no_effect_count=1,
        screen_width=1080,
        screen_height=2400,
        transition_context=context,
    )
    assert second["permitted"]
    assert second["deferred_semantic_progress_observed"]
    assert second["effective_identical_coordinate_no_effect_count"] == 0
    guard.validate_decision(
        decision(action),
        page_sha256="value-1-delayed",
        bounded_task_repeated_tap_assessment=second,
    )
    guard.observe_transition(
        before_sha256="value-1-delayed",
        action=action,
        after_sha256="value-2",
    )

    for ordinal in (3, 4, 5):
        before = f"value-{ordinal - 1}"
        assessment = bounded_task_repeated_tap_assessment(
            goal,
            [repeated_button()],
            action,
            prior_identical_coordinate_action_count=(
                guard.identical_coordinate_action_count
            ),
            identical_coordinate_no_effect_count=(
                guard.identical_coordinate_no_effect_count
            ),
            screen_width=1080,
            screen_height=2400,
            transition_context=guard.repeated_tap_transition_context(
                page_sha256=before,
                action=action,
            ),
        )
        assert assessment["permitted"]
        assert assessment["proposed_ordinal"] == ordinal
        guard.validate_decision(
            decision(action),
            page_sha256=before,
            bounded_task_repeated_tap_assessment=assessment,
        )
        guard.observe_transition(
            before_sha256=before,
            action=action,
            after_sha256=f"value-{ordinal}",
        )

    sixth = bounded_task_repeated_tap_assessment(
        goal,
        [repeated_button()],
        action,
        prior_identical_coordinate_action_count=5,
        identical_coordinate_no_effect_count=0,
        screen_width=1080,
        screen_height=2400,
        transition_context=guard.repeated_tap_transition_context(
            page_sha256="value-5",
            action=action,
        ),
    )
    assert not sixth["permitted"]
    with pytest.raises(
        ActionValidationError,
        match="same coordinate tap or long-press",
    ):
        guard.validate_decision(
            decision(action),
            page_sha256="value-5",
            bounded_task_repeated_tap_assessment=sixth,
        )
    audit = guard.audit_record()
    assert audit["deferred_semantic_progress_reconciliation_count"] == 1
    assert audit["identical_coordinate_no_effect_count"] == 0
    assert audit["bounded_task_repeated_tap_override_count"] == 2


def test_guard_reconciles_inter_step_progress_without_unblocking() -> None:
    guard = ProtocolV2DecisionGuard(max_no_effect_repeats=1)
    action = {"type": "tap", "x": 0.72, "y": 0.085}
    transition = guard.observe_transition(
        before_sha256="a" * 64,
        action=action,
        after_sha256="a" * 64,
    )
    assert transition["fingerprint_blocked"] is True
    result = guard.reconcile_late_semantic_transition(
        completed_step=9,
        previous_after_sha256="a" * 64,
        current_before_sha256="b" * 64,
    )
    assert result["reconciled"] is True
    assert result["recorded_no_effect"] is True
    assert result["blocked_fingerprint_preserved"] is True
    assert guard.no_effect_counts == {}
    assert guard.transition_fingerprints[-1][2] == "b" * 64
    audit = guard.audit_record()
    assert audit["blocked_fingerprint_count"] == 1
    assert audit["deferred_semantic_progress_reconciliation_count"] == 1


def test_verified_repeat_ledger_overrides_stale_summary_and_calculates() -> None:
    guard = ProtocolV2DecisionGuard(
        max_no_effect_repeats=10,
        max_identical_coordinate_actions=3,
    )
    goal = (
        "Open the task with Chrome. Then click the button 5 times, "
        "remember the numbers displayed, and enter their product."
    )
    action = {"type": "tap", "x": 0.5, "y": 0.208}
    guard.reset(goal=goal)
    pre_action_results = ["6", "2", "3", "9", "10"]

    for ordinal, current_value in enumerate(
        pre_action_results,
        start=1,
    ):
        page = f"before-{ordinal}"
        assessment = bounded_task_repeated_tap_assessment(
            goal,
            [repeated_button(), numeric_result(current_value)],
            action,
            prior_identical_coordinate_action_count=(
                guard.identical_coordinate_action_count
            ),
            identical_coordinate_no_effect_count=(
                guard.identical_coordinate_no_effect_count
            ),
            screen_width=1080,
            screen_height=2400,
            transition_context=guard.repeated_tap_transition_context(
                page_sha256=page,
                action=action,
            ),
        )
        assert assessment["proposed_ordinal"] == ordinal
        assert assessment["task_target_bound"]
        assert assessment["numeric_result_collection_bound"]
        assert assessment["pre_action_numeric_operand_bound"]
        guard.validate_decision(
            decision(action),
            page_sha256=page,
            bounded_task_repeated_tap_assessment=assessment,
        )
        guard.observe_transition(
            before_sha256=page,
            action=action,
            after_sha256=f"after-{ordinal}",
            bounded_task_repeated_tap_assessment=assessment,
        )
        progress = guard.refresh_verified_task_repeat_progress(
            goal=goal,
            ui_elements=[],
            page_sha256=f"fresh-result-{ordinal}",
        )
        assert progress is not None
        assert progress["executed_count"] == ordinal
        assert progress["verified_operands"] == pre_action_results[:ordinal]

    progress = guard.verified_task_repeat_progress_record()
    assert progress is not None
    assert progress["complete"]
    assert progress["operands_complete"]
    assert progress["deterministic_calculation"] == {
        "operation": "product",
        "operands": ["6", "2", "3", "9", "10"],
        "result": "3240",
        "text_origin": "deterministic_calculation",
    }
    assert progress["ready_for_post_repeat"]

    sixth = bounded_task_repeated_tap_assessment(
        goal,
        [],
        action,
        prior_identical_coordinate_action_count=5,
        identical_coordinate_no_effect_count=0,
        screen_width=1080,
        screen_height=2400,
        transition_context=guard.repeated_tap_transition_context(
            page_sha256="fresh-result-5",
            action=action,
        ),
    )
    with pytest.raises(
        ActionValidationError,
        match="TASK_REPEAT_COUNT_COMPLETE",
    ):
        guard.validate_decision(
            decision(action),
            page_sha256="fresh-result-5",
            bounded_task_repeated_tap_assessment=sixth,
        )
    audit = guard.audit_record()
    assert audit["task_repeat_count_complete_block_count"] == 1
    assert audit["verified_task_repeat_progress"]["executed_count"] == 5


def test_verified_repeat_ledger_does_not_guess_ambiguous_result() -> None:
    guard = ProtocolV2DecisionGuard()
    goal = (
        "Open with Chrome, click the button 2 times, remember the numbers "
        "displayed, and enter their product."
    )
    action = {"type": "tap", "x": 0.5, "y": 0.208}
    guard.reset(goal=goal)
    first = bounded_task_repeated_tap_assessment(
        goal,
        [repeated_button(), numeric_result("6")],
        action,
        prior_identical_coordinate_action_count=0,
        identical_coordinate_no_effect_count=0,
        screen_width=1080,
        screen_height=2400,
    )
    guard.observe_transition(
        before_sha256="before",
        action=action,
        after_sha256="after",
        bounded_task_repeated_tap_assessment=first,
    )
    second = bounded_task_repeated_tap_assessment(
        goal,
        [
            repeated_button(),
            numeric_result("2"),
            numeric_result("3"),
        ],
        action,
        prior_identical_coordinate_action_count=1,
        identical_coordinate_no_effect_count=0,
        screen_width=1080,
        screen_height=2400,
    )
    assert not second["pre_action_numeric_operand_bound"]
    guard.observe_transition(
        before_sha256="after",
        action=action,
        after_sha256="form",
        bounded_task_repeated_tap_assessment=second,
    )
    progress = guard.refresh_verified_task_repeat_progress(
        goal=goal,
        ui_elements=[],
        page_sha256="ambiguous",
    )
    assert progress is not None
    assert progress["executed_count"] == 2
    assert progress["complete"]
    assert progress["verified_operands"] == ["6"]
    assert not progress["operands_complete"]
    assert progress["deterministic_calculation"] is None
    assert not progress["ready_for_post_repeat"]


def test_verified_repeat_ledger_rejects_chrome_setup_button_bootstrap() -> None:
    guard = ProtocolV2DecisionGuard()
    goal = (
        "Open the task with Chrome, click the button 5 times, remember "
        "the numbers displayed, and enter their product."
    )
    setup_action = {"type": "tap", "x": 0.5, "y": 0.915}
    setup_button = {
        **repeated_button(),
        "text": "Accept & continue",
        "bbox": {
            "x_min": 0.2,
            "x_max": 0.8,
            "y_min": 0.88,
            "y_max": 0.95,
        },
    }
    assessment = bounded_task_repeated_tap_assessment(
        goal,
        [setup_button],
        setup_action,
        prior_identical_coordinate_action_count=0,
        identical_coordinate_no_effect_count=0,
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["task_target_bound"]
    assert not assessment["pre_action_numeric_operand_bound"]
    guard.observe_transition(
        before_sha256="chrome-setup",
        action=setup_action,
        after_sha256="chrome-setup-after",
        bounded_task_repeated_tap_assessment=assessment,
    )
    assert guard.verified_task_repeat_progress_record() is None


def test_verified_repeat_ledger_retains_equal_pre_action_ordinals() -> None:
    guard = ProtocolV2DecisionGuard()
    goal = (
        "Open with Chrome, click the button 2 times, remember the numbers "
        "displayed, and enter their product."
    )
    action = {"type": "tap", "x": 0.5, "y": 0.208}
    guard.reset(goal=goal)
    for ordinal in (1, 2):
        assessment = bounded_task_repeated_tap_assessment(
            goal,
            [repeated_button(), numeric_result("4")],
            action,
            prior_identical_coordinate_action_count=ordinal - 1,
            identical_coordinate_no_effect_count=0,
            screen_width=1080,
            screen_height=2400,
        )
        guard.observe_transition(
            before_sha256=f"same-value-before-{ordinal}",
            action=action,
            after_sha256=f"same-value-after-{ordinal}",
            bounded_task_repeated_tap_assessment=assessment,
        )
    progress = guard.refresh_verified_task_repeat_progress(
        goal=goal,
        ui_elements=[],
        page_sha256="answer-form",
    )
    assert progress is not None
    assert progress["verified_operands"] == ["4", "4"]
    assert [
        record["result_ordinal"]
        for record in progress["operand_records"]
    ] == [1, 2]
    assert progress["deterministic_calculation"]["result"] == "16"
    assert progress["ready_for_post_repeat"]


def test_numeric_repeat_result_excludes_clickable_and_wrong_package() -> None:
    assessment = bounded_task_repeated_tap_assessment(
        (
            "Open with Chrome, click the button 5 times, remember the "
            "numbers displayed, and enter their product."
        ),
        [
            repeated_button(),
            numeric_result("2", clickable=True),
            {
                **numeric_result("3"),
                "package_name": "com.android.systemui",
            },
        ],
        {"type": "tap", "x": 0.5, "y": 0.208},
        prior_identical_coordinate_action_count=1,
        identical_coordinate_no_effect_count=0,
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["numeric_result_collection_bound"]
    assert assessment["visible_numeric_result_candidates"] == []
    assert assessment["unique_visible_numeric_result"] is None


@pytest.mark.parametrize(
    ("current_state", "visible_failures", "max_no_effect", "expected_reason"),
    [
        ("same", (), 10, "no fresh semantic change"),
        ("delayed", ("Chrome has stopped",), 10, "visible failure"),
        ("delayed", (), 1, "blocked prior fingerprint"),
    ],
)
def test_delayed_semantic_reconciliation_denies_unsafe_evidence(
    current_state: str,
    visible_failures: tuple[str, ...],
    max_no_effect: int,
    expected_reason: str,
) -> None:
    guard = ProtocolV2DecisionGuard(
        max_no_effect_repeats=max_no_effect,
        max_identical_coordinate_actions=3,
    )
    goal = "Open with Chrome, then click the button 5 times."
    action = {"type": "tap", "x": 0.5, "y": 0.208}
    guard.reset(goal=goal)
    guard.observe_transition(
        before_sha256="same",
        action=action,
        after_sha256="same",
    )
    assessment = bounded_task_repeated_tap_assessment(
        goal,
        [repeated_button()],
        action,
        prior_identical_coordinate_action_count=1,
        identical_coordinate_no_effect_count=1,
        screen_width=1080,
        screen_height=2400,
        transition_context=guard.repeated_tap_transition_context(
            page_sha256=current_state,
            action=action,
        ),
        current_visible_failures=visible_failures,
    )
    assert not assessment["permitted"], expected_reason
    assert not assessment["deferred_semantic_progress_observed"]
    assert assessment["effective_identical_coordinate_no_effect_count"] == 1


def test_task_repeat_target_binding_rejects_unrelated_android_button() -> None:
    assessment = bounded_task_repeated_tap_assessment(
        (
            "Open the file with Chrome, then click the button 5 times and "
            "enter the product."
        ),
        [
            {
                **repeated_button(),
                "package_name": "android",
                "text": "Just once",
            }
        ],
        {"type": "tap", "x": 0.5, "y": 0.208},
        prior_identical_coordinate_action_count=3,
        identical_coordinate_no_effect_count=0,
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["matched_labels"] == ["Just once"]
    assert not assessment["package_goal_bound"]
    assert not assessment["task_target_bound"]
    assert not assessment["permitted"]


def test_generic_repeat_without_label_or_app_anchor_is_denied() -> None:
    assessment = bounded_task_repeated_tap_assessment(
        "Click the button 5 times.",
        [repeated_button()],
        {"type": "tap", "x": 0.5, "y": 0.208},
        prior_identical_coordinate_action_count=3,
        identical_coordinate_no_effect_count=0,
        screen_width=1080,
        screen_height=2400,
    )
    assert not assessment["explicit_label_bound"]
    assert not assessment["package_goal_bound"]
    assert not assessment["task_target_bound"]
    assert not assessment["permitted"]


@pytest.mark.parametrize(
    ("assessment", "reason"),
    [
        (
            task_repeat_assessment(
                goal="Click the visible button and continue.",
                prior=3,
            ),
            "no finite task count",
        ),
        (
            task_repeat_assessment(prior=3, no_effect=1),
            "prior no-effect transition",
        ),
        (
            task_repeat_assessment(
                prior=3,
                element={**repeated_button(), "text": "Save"},
            ),
            "commit-like control",
        ),
        (
            task_repeat_assessment(prior=5),
            "requested count exceeded",
        ),
    ],
)
def test_task_bounded_repeat_assessment_denies_unsafe_shapes(
    assessment: dict,
    reason: str,
) -> None:
    assert not assessment["permitted"], reason


def test_task_bounded_repeat_rejects_ambiguous_control_hits() -> None:
    assessment = bounded_task_repeated_tap_assessment(
        "Click the button five times.",
        [
            repeated_button(),
            {
                **repeated_button(),
                "text": "Overlapping control",
            },
        ],
        {"type": "tap", "x": 0.5, "y": 0.208},
        prior_identical_coordinate_action_count=3,
        identical_coordinate_no_effect_count=0,
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["matched_control_count"] == 2
    assert not assessment["permitted"]


def test_task_bounded_repeat_cannot_bypass_ab_cycle_block() -> None:
    guard = ProtocolV2DecisionGuard(
        max_no_effect_repeats=10,
        max_identical_coordinate_actions=3,
    )
    guard.reset(goal="Click the button 5 times.")
    action = {"type": "tap", "x": 0.5, "y": 0.208}
    states = (("a", "b"), ("b", "a"), ("a", "b"), ("b", "a"))
    for before, after in states:
        guard.validate_decision(
            decision(action),
            page_sha256=before,
            bounded_task_repeated_tap_assessment=(
                task_repeat_assessment(
                    prior=guard.identical_coordinate_action_count
                )
            ),
        )
        guard.observe_transition(
            before_sha256=before,
            action=action,
            after_sha256=after,
        )
    with pytest.raises(
        ActionValidationError,
        match="blocked on the current semantic UI state",
    ):
        guard.validate_decision(
            decision(action),
            page_sha256="a",
            bounded_task_repeated_tap_assessment=(
                task_repeat_assessment(prior=4)
            ),
        )
    assert guard.audit_record()["ab_ab_cycle_trigger_count"] == 1


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


def test_visible_control_activation_repeat_is_bounded_to_one() -> None:
    guard = ProtocolV2DecisionGuard(
        max_no_effect_repeats=10,
        max_identical_coordinate_actions=10,
    )
    guard.reset(goal="Create a new contact")
    action = {"type": "tap", "x": 0.87, "y": 0.835}
    assessment = {
        "schema_version": (
            "visible_control_activation_retry_assessment.v1"
        ),
        "adjudicable": True,
        "action_type": "tap",
        "matched_control_count": 1,
        "matched_packages": ["com.google.android.contacts"],
        "matched_labels": ["Create contact"],
        "commit_like": False,
        "permitted": True,
    }
    guard.validate_decision(decision(action), page_sha256="contacts")
    guard.observe_transition(
        before_sha256="contacts",
        action=action,
        after_sha256="contacts",
        claimed_unverified_progress=True,
    )
    with pytest.raises(
        ActionValidationError,
        match="UNVERIFIED_PROGRESS_REPEAT_REQUIRED",
    ):
        guard.validate_decision(
            decision(action),
            page_sha256="contacts",
            visible_control_activation_retry_assessment=assessment,
        )
    guard.validate_decision(
        decision(action),
        page_sha256="contacts",
        visible_control_activation_retry_assessment=assessment,
        allow_visible_control_activation_repeat=True,
    )
    guard.observe_transition(
        before_sha256="contacts",
        action=action,
        after_sha256="contacts",
        claimed_unverified_progress=True,
    )
    with pytest.raises(
        ActionValidationError,
        match="UNVERIFIED_PROGRESS_REPEAT_REQUIRED",
    ):
        guard.validate_decision(
            decision(action),
            page_sha256="contacts",
            visible_control_activation_retry_assessment=assessment,
            allow_visible_control_activation_repeat=True,
        )
    audit = guard.audit_record()
    assert (
        audit["visible_control_activation_repeat_override_count"] == 1
    )
    assert len(
        audit["visible_control_activation_repeat_override_records"]
    ) == 1
    assert audit["unverified_progress_repeat_block_count"] == 2


def test_visible_control_activation_repeat_never_allows_commit_label() -> None:
    guard = ProtocolV2DecisionGuard(
        max_no_effect_repeats=10,
        max_identical_coordinate_actions=10,
    )
    guard.reset(goal="Save an event")
    action = {"type": "tap", "x": 0.94, "y": 0.085}
    guard.validate_decision(decision(action), page_sha256="event-form")
    guard.observe_transition(
        before_sha256="event-form",
        action=action,
        after_sha256="event-form",
        claimed_unverified_progress=True,
    )
    with pytest.raises(
        ActionValidationError,
        match="UNVERIFIED_PROGRESS_REPEAT_REQUIRED",
    ):
        guard.validate_decision(
            decision(action),
            page_sha256="event-form",
            visible_control_activation_retry_assessment={
                "schema_version": (
                    "visible_control_activation_retry_assessment.v1"
                ),
                "adjudicable": True,
                "action_type": "tap",
                "matched_control_count": 1,
                "matched_packages": ["com.google.android.calendar"],
                "matched_labels": ["Save"],
                "commit_like": True,
                "permitted": False,
            },
            allow_visible_control_activation_repeat=True,
        )
    assert (
        guard.audit_record()[
            "visible_control_activation_repeat_override_count"
        ]
        == 0
    )


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


def test_files_view_mode_toggle_assessment_binds_one_documentsui_control() -> None:
    elements = [
        {
            "package_name": "com.google.android.documentsui",
            "content_description": "List view",
            "resource_id": "com.google.android.documentsui:id/menu_list",
            "is_visible": True,
            "is_enabled": True,
            "is_clickable": True,
            "is_editable": False,
            "bbox": {
                "x_min": 0.84,
                "x_max": 0.92,
                "y_min": 0.13,
                "y_max": 0.19,
            },
        },
        {
            "package_name": "com.google.android.documentsui",
            "content_description": "Search",
            "resource_id": "com.google.android.documentsui:id/action_search",
            "is_visible": True,
            "is_enabled": True,
            "is_clickable": True,
            "is_editable": False,
            "bbox": {
                "x_min": 0.78,
                "x_max": 0.86,
                "y_min": 0.05,
                "y_max": 0.10,
            },
        },
    ]
    allowed = files_view_mode_toggle_action_assessment(
        elements,
        {"type": "tap", "x": 0.88, "y": 0.16},
        screen_width=1080,
        screen_height=2400,
    )
    assert allowed["adjudicable"]
    assert allowed["unambiguous"]
    assert allowed["control_count"] == 1
    assert allowed["action_hit_count"] == 1
    assert allowed["permitted"]
    assert allowed["matched_labels"] == ["List view"]

    search = files_view_mode_toggle_action_assessment(
        elements,
        {"type": "tap", "x": 0.82, "y": 0.075},
        screen_width=1080,
        screen_height=2400,
    )
    assert search["control_count"] == 1
    assert search["action_hit_count"] == 0
    assert not search["permitted"]


def test_files_view_mode_toggle_requires_files_package_and_one_control() -> None:
    controls = [
        {
            "package_name": "other.files",
            "content_description": "List view",
            "is_visible": True,
            "is_enabled": True,
            "is_clickable": True,
            "is_editable": False,
            "bbox": {
                "x_min": 0.70,
                "x_max": 0.78,
                "y_min": 0.13,
                "y_max": 0.19,
            },
        },
        {
            "package_name": "com.google.android.documentsui",
            "content_description": "List view",
            "is_visible": True,
            "is_enabled": True,
            "is_clickable": True,
            "is_editable": False,
            "bbox": {
                "x_min": 0.80,
                "x_max": 0.86,
                "y_min": 0.13,
                "y_max": 0.19,
            },
        },
        {
            "package_name": "com.google.android.documentsui",
            "content_description": "Grid view",
            "is_visible": True,
            "is_enabled": True,
            "is_clickable": True,
            "is_editable": False,
            "bbox": {
                "x_min": 0.88,
                "x_max": 0.94,
                "y_min": 0.13,
                "y_max": 0.19,
            },
        },
    ]
    assessment = files_view_mode_toggle_action_assessment(
        controls,
        {"type": "tap", "x": 0.83, "y": 0.16},
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["control_count"] == 2
    assert not assessment["unambiguous"]
    assert not assessment["permitted"]


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


def destination_navigation_elements(
    *,
    label: str = "Ringtones",
    package_name: str = "com.google.android.documentsui",
    center_y: float = 0.675,
    exact_label_editable: bool = False,
    include_clickable_container: bool = True,
) -> list[dict]:
    elements = [
        {
            "package_name": package_name,
            "text": label,
            "is_visible": True,
            "is_enabled": True,
            "is_clickable": False,
            "is_editable": exact_label_editable,
            "bbox": {
                "x_min": 0.06,
                "x_max": 0.49,
                "y_min": center_y - 0.045,
                "y_max": center_y + 0.045,
            },
        }
    ]
    if include_clickable_container:
        elements.append(
            {
                "package_name": package_name,
                "text": None,
                "is_visible": True,
                "is_enabled": True,
                "is_clickable": True,
                "is_editable": False,
                "bbox": {
                    "x_min": 0.06,
                    "x_max": 0.49,
                    "y_min": 0.63,
                    "y_max": 0.72,
                },
            }
        )
    return elements


def source_context_elements(
    *,
    label: str = "Music",
    package_name: str = "com.google.android.documentsui",
    center_y: float = 0.08,
) -> list[dict]:
    return [
        {
            "package_name": package_name,
            "text": label,
            "is_visible": True,
            "is_enabled": True,
            "is_clickable": False,
            "is_editable": False,
            "bbox": {
                "x_min": 0.15,
                "x_max": 0.55,
                "y_min": center_y - 0.03,
                "y_max": center_y + 0.03,
            },
        }
    ]


def test_post_destination_source_context_binds_top_files_directory() -> None:
    assessment = post_destination_source_context_assessment(
        source_context_elements(),
        required_source_text="Music",
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["adjudicable"] is True
    assert assessment["current_source_visible"] is True
    assert assessment["current_source_hit_count"] == 1
    assert assessment["matched_labels"] == ["Music"]
    assert assessment["matched_packages"] == [
        "com.google.android.documentsui"
    ]


@pytest.mark.parametrize(
    "elements",
    [
        source_context_elements(center_y=0.42),
        source_context_elements(label="Ringtones"),
        source_context_elements(package_name="files"),
        [],
    ],
)
def test_post_destination_source_context_denies_root_tile_or_unbound_state(
    elements: list[dict],
) -> None:
    assessment = post_destination_source_context_assessment(
        elements,
        required_source_text="Music",
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["current_source_visible"] is False


def test_post_destination_source_context_requires_back_only_after_commit() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(
        goal="Move a file",
        required_source_text="Music",
    )
    assessment = post_destination_source_context_assessment(
        source_context_elements(),
        required_source_text="Music",
        screen_width=1080,
        screen_height=2400,
    )
    swipe = {
        "type": "swipe",
        "x": 0.5,
        "y": 0.8,
        "x2": 0.5,
        "y2": 0.2,
        "duration_ms": 500,
    }
    guard.validate_decision(
        decision(swipe),
        page_sha256="source-pre-commit",
        post_destination_source_context_assessment=assessment,
    )
    guard.post_destination_commit_active = True
    with pytest.raises(
        ActionValidationError,
        match="POST_DESTINATION_SOURCE_EXIT_GUARD",
    ):
        guard.validate_decision(
            decision(swipe),
            page_sha256="source-post-commit",
            post_destination_source_context_assessment=assessment,
        )
    guard.validate_decision(
        decision({"type": "press_back"}),
        page_sha256="source-post-commit",
        post_destination_source_context_assessment=assessment,
    )
    guard.validate_decision(
        decision(swipe),
        page_sha256="source-picker-active",
        destination_picker_is_active=True,
        post_destination_source_context_assessment=assessment,
    )
    root_assessment = post_destination_source_context_assessment(
        source_context_elements(center_y=0.42),
        required_source_text="Music",
        screen_width=1080,
        screen_height=2400,
    )
    guard.validate_decision(
        decision(swipe),
        page_sha256="storage-root",
        post_destination_source_context_assessment=root_assessment,
    )
    audit = guard.audit_record()
    assert audit["required_source_text"] == "Music"
    assert audit["post_destination_source_exit_block_count"] == 1


def test_post_destination_navigation_binds_exact_files_folder() -> None:
    assessment = post_destination_verification_navigation_assessment(
        destination_navigation_elements(),
        {"type": "tap", "x": 0.25, "y": 0.678},
        required_destination_text="Ringtones",
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["adjudicable"] is True
    assert assessment["exact_label_hit_count"] == 1
    assert assessment["content_exact_label_hit_count"] == 1
    assert assessment["clickable_hit_count"] == 1
    assert assessment["matched_labels"] == ["Ringtones"]
    assert assessment["matched_packages"] == [
        "com.google.android.documentsui"
    ]
    assert assessment["commit_like"] is False
    assert assessment["permitted"] is True


def test_post_destination_navigation_accepts_real_files_label_without_clickable_container(
) -> None:
    assessment = post_destination_verification_navigation_assessment(
        destination_navigation_elements(include_clickable_container=False),
        {"type": "tap", "x": 0.25, "y": 0.678},
        required_destination_text="Ringtones",
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["schema_version"].endswith(".v2")
    assert assessment["exact_label_hit_count"] == 1
    assert assessment["content_exact_label_hit_count"] == 1
    assert assessment["clickable_hit_count"] == 0
    assert assessment["content_exact_label_hits"][0]["center_y"] == 0.675
    assert assessment["content_exact_label_hits"][0]["is_editable"] is False
    assert assessment["permitted"] is True


@pytest.mark.parametrize(
    ("elements", "required_destination"),
    [
        (destination_navigation_elements(label="Music"), "Ringtones"),
        (
            destination_navigation_elements(package_name="contacts"),
            "Ringtones",
        ),
        (destination_navigation_elements(label="Move"), "Move"),
        (
            destination_navigation_elements(
                center_y=0.10,
                include_clickable_container=False,
            ),
            "Ringtones",
        ),
        (
            destination_navigation_elements(
                exact_label_editable=True,
                include_clickable_container=False,
            ),
            "Ringtones",
        ),
        (
            [
                {
                    **destination_navigation_elements(
                        include_clickable_container=False
                    )[0],
                    "content_description": "Move",
                }
            ],
            "Ringtones",
        ),
        ([], "Ringtones"),
    ],
)
def test_post_destination_navigation_denies_unbound_or_commit_targets(
    elements: list[dict],
    required_destination: str,
) -> None:
    assessment = post_destination_verification_navigation_assessment(
        elements,
        {"type": "tap", "x": 0.25, "y": 0.678},
        required_destination_text=required_destination,
        screen_width=1080,
        screen_height=2400,
    )
    assert assessment["permitted"] is False


def test_post_destination_navigation_is_counted_only_after_commit() -> None:
    guard = ProtocolV2DecisionGuard()
    guard.reset(
        goal="Move a file",
        required_destination_text="Ringtones",
    )
    action = {"type": "tap", "x": 0.25, "y": 0.678}
    assessment = post_destination_verification_navigation_assessment(
        destination_navigation_elements(),
        action,
        required_destination_text="Ringtones",
        screen_width=1080,
        screen_height=2400,
    )
    before_commit = guard.observe_transition(
        before_sha256="root-before",
        action=action,
        after_sha256="folder-before",
        post_destination_verification_navigation_assessment=assessment,
    )
    assert not before_commit["post_destination_verification_navigation"]
    guard.observe_transition(
        before_sha256="picker",
        action={"type": "tap", "x": 0.38, "y": 0.945},
        after_sha256="root",
        destination_picker_commit_executed=True,
    )
    after_commit = guard.observe_transition(
        before_sha256="root",
        action=action,
        after_sha256="folder",
        post_destination_verification_navigation_assessment=assessment,
    )
    assert after_commit["post_destination_verification_navigation"]
    assert (
        after_commit["post_destination_verification_navigation_count"] == 1
    )
    audit = guard.audit_record()
    assert audit["required_destination_text"] == "Ringtones"
    assert audit["post_destination_verification_navigation_count"] == 1
    assert audit["post_destination_verification_navigation_records"][0][
        "assessment"
    ]["matched_labels"] == ["Ringtones"]
