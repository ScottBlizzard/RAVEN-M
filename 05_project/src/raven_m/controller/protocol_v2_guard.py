"""Generic protocol-v2 provenance and repeated-action guard."""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
import math
import re
from typing import Any

from raven_m.actions.schema import ActionValidationError


ANSWER_GOAL_RE = re.compile(
    r"\b(answer|return|report|tell|give|list|find|calculate|compute|what|"
    r"which|how many|how much|total duration|total distance)\b",
    flags=re.IGNORECASE,
)
TEXT_ACTIONS = {"type_text", "answer"}
COORDINATE_STREAK_ACTIONS = {"tap", "long_press", "swipe"}
TEXT_ORIGINS = {
    "task_literal",
    "current_screen",
    "verified_memory",
    "deterministic_calculation",
}
FIELD_ROLE_ALIASES = {
    "search": {"search", "filter", "query", "find"},
    "person_name": {
        "contact",
        "name",
        "first",
        "last",
        "given",
        "family",
        "surname",
    },
    "phone": {"phone", "number", "mobile", "telephone", "tel"},
    "company": {
        "company",
        "organization",
        "organisation",
        "employer",
        "business",
    },
    "amount": {
        "amount",
        "dollar",
        "dollars",
        "price",
        "cost",
        "total",
        "value",
    },
    "category": {"category", "type", "classification"},
    "note": {
        "note",
        "memo",
        "description",
        "comment",
        "details",
        "body",
        "content",
    },
    "title": {"title", "subject", "event", "expense", "name"},
    "date": {"date", "day", "month", "year"},
    "time": {"time", "hour", "minute", "duration"},
    "file": {"file", "filename", "document"},
    "folder": {"folder", "directory", "destination"},
}
RECOVERY_CLASSES = (
    "change_target",
    "reverse_scroll_direction",
    "navigate_back",
    "reopen_app",
    "inspect_different_visible_control",
    "use_higher_level_visible_selector",
    "fail_safely",
)
VISIBLE_FAILURE_RE = re.compile(
    r"\b(cannot|can't|could not|invalid|error|failed|failure|must be|"
    r"not allowed|not found|required|unable to|ended? earlier|"
    r"already exists)\b",
    flags=re.IGNORECASE,
)
INFRASTRUCTURE_FAILURE_RE = re.compile(
    r"(?:\bis(?:n't| not)\s+responding\b|"
    r"\bnot\s+responding\b|"
    r"\bkeeps?\s+stopping\b|"
    r"\bhas\s+stopped\b|"
    r"\bprocess\s+system\b.*\bresponding\b|"
    r"\bsystem\s+ui\b.*\bresponding\b)",
    flags=re.IGNORECASE,
)
COMMIT_LIKE_CONTROL_RE = re.compile(
    r"\b(save|delete|remove|erase|send|submit|confirm|done|ok|yes|"
    r"purchase|buy|pay|install|uninstall|order|book|reserve|transfer|"
    r"upload|download|call|dial|message|email|copy|move|paste|share|"
    r"post|publish|apply|accept|agree|allow|authorize|sign\s*out|"
    r"log\s*out|factory\s+reset)\b",
    flags=re.IGNORECASE,
)
IGNORED_UI_PACKAGES = {"com.android.systemui"}
SOFT_KEYBOARD_PACKAGES = {
    "com.android.inputmethod.latin",
    "com.google.android.inputmethod.latin",
}
ANDROID_FILES_PACKAGES = {"com.google.android.documentsui"}
SEMANTIC_FIELDS = (
    "text",
    "content_description",
    "hint_text",
    "tooltip",
    "class_name",
    "package_name",
    "resource_name",
    "resource_id",
    "is_checked",
    "is_checkable",
    "is_clickable",
    "is_editable",
    "is_enabled",
    "is_focused",
    "is_scrollable",
    "is_selected",
)
SWIPE_FROM_TO_RE = re.compile(
    r"\bswip(?:e|es|ed|ing)\b[^.!?\n]{0,80}?"
    r"\bfrom\s+(left|right|up|down)\s+to\s+"
    r"(left|right|up|down)\b",
    flags=re.IGNORECASE,
)
SWIPE_DIRECTION_RE = re.compile(
    r"\bswip(?:e|es|ed|ing)\b[^.!?\n]{0,80}?"
    r"\b(left|right|up|down)\b",
    flags=re.IGNORECASE,
)


def canonical_action_key(action: dict[str, Any]) -> str:
    return json.dumps(
        action,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def swipe_direction_consistency_assessment(
    decision: dict[str, Any],
) -> dict[str, Any]:
    """Compare an explicitly stated swipe direction with its coordinates."""
    action = decision.get("action")
    summary = decision.get("decision_summary")
    if (
        not isinstance(action, dict)
        or action.get("type") != "swipe"
        or not isinstance(summary, str)
    ):
        return {
            "schema_version": "swipe_direction_consistency.v1",
            "adjudicable": False,
            "declared_direction": None,
            "actual_direction": None,
            "matched": None,
            "reason": "not_an_explicitly_directed_swipe",
        }
    from_to = SWIPE_FROM_TO_RE.search(summary)
    direct = SWIPE_DIRECTION_RE.search(summary)
    declared = (
        from_to.group(2).lower()
        if from_to is not None
        else direct.group(1).lower()
        if direct is not None
        else None
    )
    if declared is None:
        return {
            "schema_version": "swipe_direction_consistency.v1",
            "adjudicable": False,
            "declared_direction": None,
            "actual_direction": None,
            "matched": None,
            "reason": "no_explicit_swipe_direction",
        }
    try:
        dx = float(action["x2"]) - float(action["x"])
        dy = float(action["y2"]) - float(action["y"])
    except (KeyError, TypeError, ValueError):
        return {
            "schema_version": "swipe_direction_consistency.v1",
            "adjudicable": True,
            "declared_direction": declared,
            "actual_direction": None,
            "matched": False,
            "reason": "missing_or_non_numeric_swipe_coordinates",
        }
    dominant_ratio = 1.2
    minimum_displacement = 0.03
    if max(abs(dx), abs(dy)) < minimum_displacement:
        actual = None
        reason = "swipe_displacement_too_small"
    elif abs(dx) >= dominant_ratio * abs(dy):
        actual = "right" if dx > 0 else "left"
        reason = "horizontal_dominant"
    elif abs(dy) >= dominant_ratio * abs(dx):
        actual = "down" if dy > 0 else "up"
        reason = "vertical_dominant"
    else:
        actual = "diagonal"
        reason = "no_dominant_axis"
    return {
        "schema_version": "swipe_direction_consistency.v1",
        "adjudicable": True,
        "declared_direction": declared,
        "actual_direction": actual,
        "matched": actual == declared,
        "reason": reason,
        "delta": {
            "x": round(dx, 6),
            "y": round(dy, 6),
        },
    }


def _element_value(element: Any, field: str) -> Any:
    if isinstance(element, dict):
        return element.get(field)
    return getattr(element, field, None)


def _normalized_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.split())
    return normalized or None


def focused_editable_input_assessment(
    ui_elements: Any,
) -> dict[str, Any]:
    """Summarize visible evidence that text input is already active."""
    focused = []
    soft_keyboard_packages = set()
    for element in ui_elements or ():
        if _element_value(element, "is_visible") is False:
            continue
        package_name = _normalized_text(
            _element_value(element, "package_name")
        )
        if package_name in SOFT_KEYBOARD_PACKAGES:
            soft_keyboard_packages.add(package_name)
        if _element_value(element, "is_editable") is not True:
            continue
        if _element_value(element, "is_focused") is not True:
            continue
        focused.append(
            {
                "empty": _normalized_text(
                    _element_value(element, "text")
                )
                is None,
            }
        )
    return {
        "schema_version": "focused_editable_input_assessment.v2",
        "present": bool(focused),
        "focused_count": len(focused),
        "empty": bool(focused) and all(item["empty"] for item in focused),
        "soft_keyboard_present": bool(soft_keyboard_packages),
        "soft_keyboard_packages": sorted(soft_keyboard_packages),
        "input_ready": bool(focused or soft_keyboard_packages),
    }


def focused_empty_editable_tap_assessment(
    ui_elements: Any,
    action: dict[str, Any] | None,
    *,
    screen_width: int,
    screen_height: int,
) -> dict[str, Any]:
    """Detect a redundant tap inside an already-focused empty input."""
    action_type = (
        action.get("type") if isinstance(action, dict) else None
    )
    focused_empty = []
    for element in ui_elements or ():
        if _element_value(element, "is_visible") is False:
            continue
        if _element_value(element, "is_enabled") is False:
            continue
        if _element_value(element, "is_editable") is not True:
            continue
        if _element_value(element, "is_focused") is not True:
            continue
        if _normalized_text(_element_value(element, "text")) is not None:
            continue
        focused_empty.append(element)
    hit = bool(
        action_type == "tap"
        and any(
            _tap_hits_element(
                action,
                element,
                screen_width=screen_width,
                screen_height=screen_height,
            )
            for element in focused_empty
        )
    )
    return {
        "schema_version": "focused_empty_editable_tap_assessment.v1",
        "adjudicable": bool(focused_empty),
        "action_type": action_type,
        "focused_empty_count": len(focused_empty),
        "hits_focused_empty": hit,
    }


def visible_control_activation_retry_assessment(
    ui_elements: Any,
    action: dict[str, Any] | None,
    *,
    screen_width: int,
    screen_height: int,
) -> dict[str, Any]:
    """Bind one no-effect tap retry to a named, non-commit UI control."""
    action_type = (
        action.get("type") if isinstance(action, dict) else None
    )
    matched_controls: list[dict[str, Any]] = []
    for element in ui_elements or ():
        package_name = _normalized_text(
            _element_value(element, "package_name")
        )
        if (
            package_name is None
            or package_name in IGNORED_UI_PACKAGES
            or package_name in SOFT_KEYBOARD_PACKAGES
        ):
            continue
        if _element_value(element, "is_visible") is not True:
            continue
        if _element_value(element, "is_enabled") is not True:
            continue
        if _element_value(element, "is_clickable") is not True:
            continue
        if _element_value(element, "is_editable") is True:
            continue
        if not _tap_hits_element(
            action,
            element,
            screen_width=screen_width,
            screen_height=screen_height,
        ):
            continue
        labels = [
            label
            for field in (
                "text",
                "content_description",
                "hint_text",
                "tooltip",
            )
            if (
                label := _normalized_text(
                    _element_value(element, field)
                )
            )
            is not None
        ]
        if not labels:
            continue
        matched_controls.append(
            {
                "package_name": package_name,
                "labels": labels,
                "commit_like": any(
                    COMMIT_LIKE_CONTROL_RE.search(label)
                    for label in labels
                ),
            }
        )
    matched_labels = sorted(
        {
            label
            for control in matched_controls
            for label in control["labels"]
        }
    )
    commit_like = any(
        control["commit_like"] for control in matched_controls
    )
    return {
        "schema_version": "visible_control_activation_retry_assessment.v1",
        "adjudicable": bool(ui_elements),
        "action_type": action_type,
        "matched_control_count": len(matched_controls),
        "matched_packages": sorted(
            {
                control["package_name"]
                for control in matched_controls
            }
        ),
        "matched_labels": matched_labels,
        "commit_like": commit_like,
        "permitted": bool(
            action_type == "tap"
            and matched_controls
            and not commit_like
        ),
    }


def post_destination_verification_navigation_assessment(
    ui_elements: Any,
    action: dict[str, Any] | None,
    *,
    required_destination_text: str | None,
    screen_width: int,
    screen_height: int,
) -> dict[str, Any]:
    """Bind post-transfer verification to the exact task destination row."""
    action_type = (
        action.get("type") if isinstance(action, dict) else None
    )
    required_label = _normalized_text(required_destination_text)
    exact_label_hits: list[dict[str, Any]] = []
    clickable_hits: list[dict[str, Any]] = []
    for element in ui_elements or ():
        package_name = _normalized_text(
            _element_value(element, "package_name")
        )
        if package_name not in ANDROID_FILES_PACKAGES:
            continue
        if _element_value(element, "is_visible") is not True:
            continue
        if _element_value(element, "is_enabled") is not True:
            continue
        if not _tap_hits_element(
            action,
            element,
            screen_width=screen_width,
            screen_height=screen_height,
        ):
            continue
        labels = [
            label
            for field in (
                "text",
                "content_description",
                "hint_text",
                "tooltip",
            )
            if (
                label := _normalized_text(
                    _element_value(element, field)
                )
            )
            is not None
        ]
        if (
            required_label is not None
            and any(
                label.casefold() == required_label.casefold()
                for label in labels
            )
        ):
            exact_label_hits.append(
                {
                    "package_name": package_name,
                    "labels": labels,
                }
            )
        if (
            _element_value(element, "is_clickable") is True
            and _element_value(element, "is_editable") is not True
        ):
            clickable_hits.append(
                {
                    "package_name": package_name,
                    "labels": labels,
                    "commit_like": any(
                        COMMIT_LIKE_CONTROL_RE.search(label)
                        for label in labels
                    ),
                }
            )
    matched_labels = sorted(
        {
            label
            for hit in exact_label_hits
            for label in hit["labels"]
        }
    )
    commit_like = bool(
        required_label
        and COMMIT_LIKE_CONTROL_RE.search(required_label)
    ) or any(hit["commit_like"] for hit in clickable_hits)
    return {
        "schema_version": (
            "post_destination_verification_navigation_assessment.v1"
        ),
        "adjudicable": bool(ui_elements and required_label),
        "action_type": action_type,
        "required_destination_text": required_label,
        "exact_label_hit_count": len(exact_label_hits),
        "clickable_hit_count": len(clickable_hits),
        "matched_labels": matched_labels,
        "matched_packages": sorted(
            {
                hit["package_name"]
                for hit in [*exact_label_hits, *clickable_hits]
            }
        ),
        "commit_like": commit_like,
        "permitted": bool(
            action_type == "tap"
            and required_label
            and exact_label_hits
            and clickable_hits
            and not commit_like
        ),
    }


def post_destination_source_context_assessment(
    ui_elements: Any,
    *,
    required_source_text: str | None,
    screen_width: int,
    screen_height: int,
) -> dict[str, Any]:
    """Detect the exact task source as the current Android Files directory."""
    required_label = _normalized_text(required_source_text)
    current_directory_hits: list[dict[str, Any]] = []
    for element in ui_elements or ():
        package_name = _normalized_text(
            _element_value(element, "package_name")
        )
        if package_name not in ANDROID_FILES_PACKAGES:
            continue
        if _element_value(element, "is_visible") is not True:
            continue
        if _element_value(element, "is_enabled") is not True:
            continue
        labels = [
            label
            for field in (
                "text",
                "content_description",
                "hint_text",
                "tooltip",
            )
            if (
                label := _normalized_text(
                    _element_value(element, field)
                )
            )
            is not None
        ]
        if (
            required_label is None
            or not any(
                label.casefold() == required_label.casefold()
                for label in labels
            )
        ):
            continue
        bbox = _normalized_element_bbox(
            element,
            screen_width=screen_width,
            screen_height=screen_height,
        )
        if bbox is None:
            continue
        x_min, x_max, y_min, y_max = bbox
        center_y = (y_min + y_max) / 2.0
        # Android Files renders the current title and breadcrumb in its top
        # navigation region. A same-named folder tile at storage-root level
        # sits below this boundary and must remain navigable.
        if center_y > 0.20:
            continue
        current_directory_hits.append(
            {
                "package_name": package_name,
                "labels": labels,
                "normalized_bbox": {
                    "x_min": round(x_min, 6),
                    "x_max": round(x_max, 6),
                    "y_min": round(y_min, 6),
                    "y_max": round(y_max, 6),
                },
                "center_y": round(center_y, 6),
            }
        )
    return {
        "schema_version": "post_destination_source_context_assessment.v1",
        "adjudicable": bool(ui_elements and required_label),
        "required_source_text": required_label,
        "current_source_hit_count": len(current_directory_hits),
        "matched_labels": sorted(
            {
                label
                for hit in current_directory_hits
                for label in hit["labels"]
            }
        ),
        "matched_packages": sorted(
            {
                hit["package_name"]
                for hit in current_directory_hits
            }
        ),
        "current_directory_hits": current_directory_hits,
        "current_source_visible": bool(current_directory_hits),
    }


def declared_text_source_assessment(
    goal: str,
    ui_elements: Any,
    action: dict[str, Any] | None,
) -> dict[str, Any]:
    """Bind declared task/screen text provenance to current evidence."""
    is_text_action = (
        isinstance(action, dict) and action.get("type") in TEXT_ACTIONS
    )
    origin = action.get("text_origin") if is_text_action else None
    candidate = (
        _normalized_text(action.get("text")) if is_text_action else None
    )
    candidate_key = candidate.casefold() if candidate is not None else None
    source_values: list[str] = []
    if origin == "task_literal":
        goal_text = _normalized_text(goal)
        if goal_text is not None:
            source_values.append(goal_text)
    elif origin == "current_screen":
        for element in ui_elements or ():
            if _element_value(element, "is_visible") is False:
                continue
            for field in (
                "text",
                "content_description",
                "hint_text",
                "tooltip",
            ):
                value = _normalized_text(_element_value(element, field))
                if value is not None:
                    source_values.append(value)
    adjudicable = (
        is_text_action
        and origin in {"task_literal", "current_screen"}
        and candidate_key is not None
        and bool(source_values)
    )
    matched = bool(
        adjudicable
        and any(candidate_key in value.casefold() for value in source_values)
    )
    return {
        "schema_version": "declared_text_source_assessment.v1",
        "origin": origin,
        "adjudicable": adjudicable,
        "source_value_count": len(source_values),
        "matched": matched,
    }


def _role_groups(value: str | None) -> set[str]:
    if value is None:
        return set()
    tokens = set(re.findall(r"[a-z0-9]+", value.casefold()))
    return {
        role
        for role, aliases in FIELD_ROLE_ALIASES.items()
        if tokens.intersection(aliases)
    }


def task_literal_field_role_assessment(
    goal: str,
    ui_elements: Any,
    action: dict[str, Any] | None,
    *,
    screen_width: int,
    screen_height: int,
) -> dict[str, Any]:
    """Check a task literal against the semantic role of its target field."""
    is_task_literal_type = (
        isinstance(action, dict)
        and action.get("type") == "type_text"
        and action.get("text_origin") == "task_literal"
    )
    coordinate_bearing = (
        is_task_literal_type
        and isinstance(action.get("x"), (int, float))
        and isinstance(action.get("y"), (int, float))
    )
    candidate = (
        _normalized_text(action.get("text"))
        if is_task_literal_type
        else None
    )
    source_context = None
    if candidate is not None:
        for segment in re.split(
            r"(?:\r?\n)+|(?<=[.!?])\s+",
            goal,
        ):
            normalized_segment = _normalized_text(segment)
            if (
                normalized_segment is not None
                and candidate.casefold() in normalized_segment.casefold()
            ):
                source_context = normalized_segment
                break
    source_roles = _role_groups(source_context)
    target_roles: set[str] = set()
    matched_editable_count = 0
    tap_action = (
        {"type": "tap", "x": action["x"], "y": action["y"]}
        if coordinate_bearing
        else None
    )
    for element in ui_elements or ():
        if _element_value(element, "is_visible") is False:
            continue
        if _element_value(element, "is_enabled") is False:
            continue
        if _element_value(element, "is_editable") is not True:
            continue
        if not _tap_hits_element(
            tap_action,
            element,
            screen_width=screen_width,
            screen_height=screen_height,
        ):
            continue
        matched_editable_count += 1
        for field in (
            "text",
            "content_description",
            "hint_text",
            "tooltip",
            "resource_name",
            "resource_id",
        ):
            target_roles.update(
                _role_groups(_normalized_text(_element_value(element, field)))
            )
    adjudicable = bool(
        coordinate_bearing
        and source_roles
        and target_roles
        and matched_editable_count
    )
    matched = bool(
        adjudicable
        and (
            "search" in target_roles
            or source_roles.intersection(target_roles)
        )
    )
    return {
        "schema_version": "task_literal_field_role_assessment.v1",
        "adjudicable": adjudicable,
        "coordinate_bearing": coordinate_bearing,
        "matched_editable_count": matched_editable_count,
        "source_role_groups": sorted(source_roles),
        "target_role_groups": sorted(target_roles),
        "matched": matched,
    }


def _box_value(box: Any, field: str) -> Any:
    if isinstance(box, dict):
        return box.get(field)
    return getattr(box, field, None)


def _normalized_element_bbox(
    element: Any,
    *,
    screen_width: int,
    screen_height: int,
) -> tuple[float, float, float, float] | None:
    box = _element_value(element, "bbox")
    if box is None:
        box = _element_value(element, "bbox_pixels")
    x_min = _box_value(box, "x_min") if box is not None else None
    x_max = _box_value(box, "x_max") if box is not None else None
    y_min = _box_value(box, "y_min") if box is not None else None
    y_max = _box_value(box, "y_max") if box is not None else None
    values = (x_min, x_max, y_min, y_max)
    if not all(isinstance(value, (int, float)) for value in values):
        return None
    normalized = max(float(value) for value in values) <= 1.5
    if normalized:
        nx_min, nx_max = sorted((float(x_min), float(x_max)))
        ny_min, ny_max = sorted((float(y_min), float(y_max)))
    elif screen_width > 0 and screen_height > 0:
        nx_min, nx_max = sorted(
            (float(x_min) / screen_width, float(x_max) / screen_width)
        )
        ny_min, ny_max = sorted(
            (
                float(y_min) / screen_height,
                float(y_max) / screen_height,
            )
        )
    else:
        return None
    return nx_min, nx_max, ny_min, ny_max


def _tap_hits_element(
    action: dict[str, Any] | None,
    element: Any,
    *,
    screen_width: int,
    screen_height: int,
) -> bool:
    if not isinstance(action, dict) or action.get("type") != "tap":
        return False
    tap_x = action.get("x")
    tap_y = action.get("y")
    if not isinstance(tap_x, (int, float)) or not isinstance(
        tap_y, (int, float)
    ):
        return False
    bbox = _normalized_element_bbox(
        element,
        screen_width=screen_width,
        screen_height=screen_height,
    )
    if bbox is None:
        return False
    x_min, x_max, y_min, y_max = bbox
    return (
        x_min <= float(tap_x) <= x_max
        and y_min <= float(tap_y) <= y_max
    )


def soft_keyboard_swipe_assessment(
    ui_elements: Any,
    action: dict[str, Any] | None,
    *,
    screen_width: int,
    screen_height: int,
) -> dict[str, Any]:
    """Check whether a swipe begins inside the visible soft keyboard."""
    action_is_swipe = (
        isinstance(action, dict) and action.get("type") == "swipe"
    )
    coordinate_bearing = bool(
        action_is_swipe
        and all(
            isinstance(action.get(field), (int, float))
            for field in ("x", "y", "x2", "y2")
        )
    )
    keyboard_packages = set()
    visible_keyboard_element_count = 0
    boxed_keyboard_element_count = 0
    start_hit_count = 0
    start_action = (
        {
            "type": "tap",
            "x": action["x"],
            "y": action["y"],
        }
        if coordinate_bearing
        else None
    )
    for element in ui_elements or ():
        if _element_value(element, "is_visible") is False:
            continue
        package_name = _normalized_text(
            _element_value(element, "package_name")
        )
        if package_name not in SOFT_KEYBOARD_PACKAGES:
            continue
        keyboard_packages.add(package_name)
        visible_keyboard_element_count += 1
        if (
            _normalized_element_bbox(
                element,
                screen_width=screen_width,
                screen_height=screen_height,
            )
            is None
        ):
            continue
        boxed_keyboard_element_count += 1
        if _tap_hits_element(
            start_action,
            element,
            screen_width=screen_width,
            screen_height=screen_height,
        ):
            start_hit_count += 1
    adjudicable = bool(
        coordinate_bearing and boxed_keyboard_element_count
    )
    return {
        "schema_version": "soft_keyboard_swipe_assessment.v1",
        "adjudicable": adjudicable,
        "coordinate_bearing": coordinate_bearing,
        "soft_keyboard_present": bool(keyboard_packages),
        "soft_keyboard_packages": sorted(keyboard_packages),
        "visible_keyboard_element_count": visible_keyboard_element_count,
        "boxed_keyboard_element_count": boxed_keyboard_element_count,
        "start_hit_count": start_hit_count,
        "start_in_keyboard": bool(adjudicable and start_hit_count),
    }


def coordinate_type_text_target_assessment(
    ui_elements: Any,
    action: dict[str, Any] | None,
    *,
    screen_width: int,
    screen_height: int,
) -> dict[str, Any]:
    """Check whether a coordinate-bearing text action targets an editable."""
    action_is_type_text = (
        isinstance(action, dict) and action.get("type") == "type_text"
    )
    coordinate_bearing = (
        action_is_type_text
        and isinstance(action.get("x"), (int, float))
        and isinstance(action.get("y"), (int, float))
    )
    if not action_is_type_text:
        return {
            "schema_version": "coordinate_text_target_assessment.v2",
            "adjudicable": False,
            "coordinate_bearing": False,
            "visible_editable_count": 0,
            "boxed_editable_count": 0,
            "matched_editable_count": 0,
            "matched_empty": False,
            "matched": False,
        }
    elements = list(ui_elements or ())
    visible_editable = []
    boxed_editable_count = 0
    matched_editable = []
    tap_action = (
        {
            "type": "tap",
            "x": action["x"],
            "y": action["y"],
        }
        if coordinate_bearing
        else None
    )
    for element in elements:
        if _element_value(element, "is_visible") is False:
            continue
        if _element_value(element, "is_enabled") is False:
            continue
        if _element_value(element, "is_editable") is not True:
            continue
        visible_editable.append(element)
        if (
            _normalized_element_bbox(
                element,
                screen_width=screen_width,
                screen_height=screen_height,
            )
            is not None
        ):
            boxed_editable_count += 1
        if _tap_hits_element(
            tap_action,
            element,
            screen_width=screen_width,
            screen_height=screen_height,
        ):
            matched_editable.append(element)
    return {
        "schema_version": "coordinate_text_target_assessment.v2",
        "adjudicable": bool(elements),
        "coordinate_bearing": coordinate_bearing,
        "visible_editable_count": len(visible_editable),
        "boxed_editable_count": boxed_editable_count,
        "matched_editable_count": len(matched_editable),
        "matched_empty": bool(matched_editable)
        and all(
            _normalized_text(_element_value(element, "text")) is None
            for element in matched_editable
        ),
        "matched": bool(matched_editable),
    }


def destination_picker_active(
    ui_elements: Any,
    *,
    screen_height: int,
) -> bool:
    """Detect a bottom-anchored Android copy/move destination picker."""
    bottom_controls: set[str] = set()
    for element in ui_elements or []:
        if _element_value(element, "is_visible") is False:
            continue
        if _element_value(element, "is_enabled") is False:
            continue
        texts = {
            text.casefold()
            for field in ("text", "content_description")
            if (text := _normalized_text(_element_value(element, field)))
        }
        controls = texts & {"cancel", "copy", "move"}
        if not controls:
            continue
        box = _element_value(element, "bbox")
        y_min = _box_value(box, "y_min") if box is not None else None
        y_max = _box_value(box, "y_max") if box is not None else None
        if y_min is None or y_max is None:
            box = _element_value(element, "bbox_pixels")
            y_min = _box_value(box, "y_min") if box is not None else None
            y_max = _box_value(box, "y_max") if box is not None else None
        if not isinstance(y_min, (int, float)) or not isinstance(
            y_max, (int, float)
        ):
            continue
        center_y = (float(y_min) + float(y_max)) / 2.0
        if max(float(y_min), float(y_max)) <= 1.5:
            center_fraction = center_y
        elif screen_height > 0:
            center_fraction = center_y / float(screen_height)
        else:
            continue
        if center_fraction >= 0.8:
            bottom_controls.update(controls)
    return "cancel" in bottom_controls and bool(
        bottom_controls & {"copy", "move"}
    )


def destination_picker_empty_stall_assessment(
    ui_elements: Any,
    action: dict[str, Any] | None,
    *,
    screen_width: int | None = None,
    screen_height: int | None = None,
) -> dict[str, Any]:
    """Detect actions that cannot progress a rendered empty destination."""
    action_type = (
        action.get("type") if isinstance(action, dict) else None
    )
    visible_empty_marker_count = 0
    for element in ui_elements or ():
        if _element_value(element, "is_visible") is False:
            continue
        texts = {
            text.casefold()
            for field in ("text", "content_description")
            if (text := _normalized_text(_element_value(element, field)))
        }
        if texts & {"no items", "folder is empty", "empty folder"}:
            visible_empty_marker_count += 1
    empty_destination_state = visible_empty_marker_count > 0
    control_bound_tap: bool | None = None
    if (
        action_type == "tap"
        and isinstance(screen_width, int)
        and screen_width > 0
        and isinstance(screen_height, int)
        and screen_height > 0
    ):
        control_bound_tap = bool(
            destination_picker_commit_action(
                ui_elements,
                action,
                screen_width=screen_width,
                screen_height=screen_height,
            )
            or destination_picker_navigation_drawer_action(
                ui_elements,
                action,
                screen_width=screen_width,
                screen_height=screen_height,
            )
        )
    unsupported_tap = control_bound_tap is False
    stalling_action = action_type in {"wait", "swipe"} or unsupported_tap
    return {
        "schema_version": (
            "destination_picker_empty_stall_assessment.v2"
        ),
        "adjudicable": empty_destination_state,
        "action_type": action_type,
        "control_bound_tap": control_bound_tap,
        "empty_destination_state": empty_destination_state,
        "unsupported_tap": unsupported_tap,
        "visible_empty_marker_count": visible_empty_marker_count,
        "stalling_action": stalling_action,
    }


def destination_picker_commit_action(
    ui_elements: Any,
    action: dict[str, Any] | None,
    *,
    screen_width: int,
    screen_height: int,
) -> bool:
    """Return whether a tap hits the bottom Copy/Move picker control."""
    if not isinstance(action, dict) or action.get("type") != "tap":
        return False
    tap_x = action.get("x")
    tap_y = action.get("y")
    if not isinstance(tap_x, (int, float)) or not isinstance(
        tap_y, (int, float)
    ):
        return False
    for element in ui_elements or []:
        if _element_value(element, "is_visible") is False:
            continue
        if _element_value(element, "is_enabled") is False:
            continue
        texts = {
            text.casefold()
            for field in ("text", "content_description")
            if (text := _normalized_text(_element_value(element, field)))
        }
        if not texts & {"copy", "move"}:
            continue
        bbox = _normalized_element_bbox(
            element,
            screen_width=screen_width,
            screen_height=screen_height,
        )
        if bbox is None:
            continue
        _, _, ny_min, _ = bbox
        if ny_min < 0.8:
            continue
        if _tap_hits_element(
            action,
            element,
            screen_width=screen_width,
            screen_height=screen_height,
        ):
            return True
    return False


def destination_picker_navigation_drawer_action(
    ui_elements: Any,
    action: dict[str, Any] | None,
    *,
    screen_width: int,
    screen_height: int,
) -> bool:
    """Return whether a tap hits the picker's visible top-left roots control."""
    if not isinstance(action, dict) or action.get("type") != "tap":
        return False
    navigation_labels = {
        "show roots",
        "navigation drawer",
        "open navigation drawer",
        "navigation menu",
    }
    for element in ui_elements or ():
        if _element_value(element, "is_visible") is False:
            continue
        if _element_value(element, "is_enabled") is False:
            continue
        labels = {
            text.casefold()
            for field in (
                "text",
                "content_description",
                "hint_text",
                "tooltip",
            )
            if (text := _normalized_text(_element_value(element, field)))
        }
        if not labels.intersection(navigation_labels):
            continue
        bbox = _normalized_element_bbox(
            element,
            screen_width=screen_width,
            screen_height=screen_height,
        )
        if bbox is None:
            continue
        nx_min, nx_max, ny_min, ny_max = bbox
        center_x = (nx_min + nx_max) / 2.0
        center_y = (ny_min + ny_max) / 2.0
        if center_x > 0.2 or center_y > 0.15:
            continue
        if _tap_hits_element(
            action,
            element,
            screen_width=screen_width,
            screen_height=screen_height,
        ):
            return True
    return False


def files_roots_drawer_action_assessment(
    ui_elements: Any,
    action: dict[str, Any] | None,
    *,
    screen_width: int,
    screen_height: int,
) -> dict[str, Any]:
    """Detect whether an action uses a visible Android Files roots row."""
    standard_labels = {
        "recent",
        "images",
        "videos",
        "audio",
        "documents",
        "downloads",
    }
    storage_label_re = re.compile(
        r"(?:sdk[_\s-]*gphone|internal\s+storage|"
        r"phone\s+storage|device\s+storage)",
        flags=re.IGNORECASE,
    )
    observed_standard_labels: set[str] = set()
    standard_root_center_ys: list[float] = []
    root_controls: list[Any] = []
    storage_root_count = 0
    for element in ui_elements or ():
        if _element_value(element, "is_visible") is False:
            continue
        if _element_value(element, "is_enabled") is False:
            continue
        labels = {
            text.casefold()
            for field in (
                "text",
                "content_description",
                "hint_text",
                "tooltip",
            )
            if (text := _normalized_text(_element_value(element, field)))
        }
        standard_matches = labels.intersection(standard_labels)
        storage_match = any(storage_label_re.search(text) for text in labels)
        if not standard_matches and not storage_match:
            continue
        bbox = _normalized_element_bbox(
            element,
            screen_width=screen_width,
            screen_height=screen_height,
        )
        if bbox is None:
            continue
        nx_min, nx_max, ny_min, ny_max = bbox
        if nx_min > 0.65 or nx_max > 0.75:
            continue
        observed_standard_labels.update(standard_matches)
        if standard_matches:
            standard_root_center_ys.append((ny_min + ny_max) / 2.0)
        root_controls.append(element)
        if storage_match:
            storage_root_count += 1
    vertical_bands: list[float] = []
    for center_y in sorted(standard_root_center_ys):
        if (
            not vertical_bands
            or center_y - vertical_bands[-1] > 0.045
        ):
            vertical_bands.append(center_y)
    drawer_active = (
        len(observed_standard_labels) >= 3
        and len(root_controls) >= 4
        and len(vertical_bands) >= 4
    )
    action_type = (
        action.get("type") if isinstance(action, dict) else None
    )
    matched_root_control_count = 0
    if action_type == "tap":
        matched_root_control_count = sum(
            1
            for element in root_controls
            if _tap_hits_element(
                action,
                element,
                screen_width=screen_width,
                screen_height=screen_height,
            )
        )
    usable_storage_row_visible = storage_root_count > 0
    progress_action_required = bool(
        drawer_active
        and usable_storage_row_visible
        and (
            action_type != "tap"
            or matched_root_control_count == 0
        )
    )
    return {
        "schema_version": "files_roots_drawer_action_assessment.v1",
        "adjudicable": drawer_active,
        "action_type": action_type,
        "drawer_active": drawer_active,
        "matched_root_control_count": matched_root_control_count,
        "standard_root_label_count": len(observed_standard_labels),
        "standard_root_vertical_band_count": len(vertical_bands),
        "usable_root_control_count": len(root_controls),
        "usable_storage_row_visible": usable_storage_row_visible,
        "visible_storage_root_count": storage_root_count,
        "progress_action_required": progress_action_required,
    }


def post_destination_transfer_command_action(
    ui_elements: Any,
    action: dict[str, Any] | None,
    *,
    screen_width: int,
    screen_height: int,
) -> bool:
    """Detect a tap on a visible Move to/Copy to command."""
    for element in ui_elements or []:
        if _element_value(element, "is_visible") is False:
            continue
        if _element_value(element, "is_enabled") is False:
            continue
        texts = {
            text.casefold().replace("…", "...").rstrip(".")
            for field in ("text", "content_description")
            if (text := _normalized_text(_element_value(element, field)))
        }
        if not texts & {"move to", "copy to"}:
            continue
        if _tap_hits_element(
            action,
            element,
            screen_width=screen_width,
            screen_height=screen_height,
        ):
            return True
    return False


def exact_selection_long_press_assessment(
    ui_elements: Any,
    action: dict[str, Any] | None,
    *,
    required_text: str | None,
    screen_width: int,
    screen_height: int,
) -> dict[str, Any]:
    """Adjudicate a long-press against full accessibility filename text."""
    base = {
        "schema_version": "exact_selection_assessment.v1",
        "adjudicable": False,
        "matched": None,
        "required_text": required_text,
        "exact_text_visible": False,
        "candidate_count": 0,
        "nearest_text": None,
        "nearest_distance": None,
    }
    if (
        not required_text
        or not isinstance(action, dict)
        or action.get("type") != "long_press"
    ):
        return base
    press_x = action.get("x")
    press_y = action.get("y")
    if not isinstance(press_x, (int, float)) or not isinstance(
        press_y, (int, float)
    ):
        return base
    dot_index = required_text.rfind(".")
    if dot_index <= 0:
        return base
    extension = required_text[dot_index:].casefold()
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[float, float, float, float]]] = set()
    for element in ui_elements or []:
        if _element_value(element, "is_visible") is False:
            continue
        bbox = _normalized_element_bbox(
            element,
            screen_width=screen_width,
            screen_height=screen_height,
        )
        if bbox is None:
            continue
        for field in ("text", "content_description"):
            text = _normalized_text(_element_value(element, field))
            if not text or not text.casefold().endswith(extension):
                continue
            key = (text, bbox)
            if key in seen:
                continue
            seen.add(key)
            x_min, x_max, y_min, y_max = bbox
            dx = max(x_min - float(press_x), 0.0, float(press_x) - x_max)
            dy = max(y_min - float(press_y), 0.0, float(press_y) - y_max)
            candidates.append(
                {
                    "text": text,
                    "distance": math.sqrt(dx * dx + dy * dy),
                }
            )
    if not candidates:
        return base
    nearest = min(
        candidates,
        key=lambda item: (
            float(item["distance"]),
            str(item["text"]).casefold(),
        ),
    )
    exact_visible = any(
        str(item["text"]).casefold() == required_text.casefold()
        for item in candidates
    )
    distance = float(nearest["distance"])
    matched = (
        exact_visible
        and str(nearest["text"]).casefold() == required_text.casefold()
        and distance <= 0.25
    )
    return {
        **base,
        "adjudicable": True,
        "matched": matched,
        "exact_text_visible": exact_visible,
        "candidate_count": len(candidates),
        "nearest_text": nearest["text"],
        "nearest_distance": round(distance, 6),
    }


def semantic_ui_snapshot(
    ui_elements: Any,
    *,
    fallback_sha256: str,
) -> dict[str, Any]:
    """Build a stable UI digest and separate visible failure messages."""
    records: list[dict[str, Any]] = []
    visible_failures: set[str] = set()
    infrastructure_failures: set[str] = set()
    for element in ui_elements or []:
        if _element_value(element, "is_visible") is False:
            continue
        package = _normalized_text(_element_value(element, "package_name"))
        if package in IGNORED_UI_PACKAGES:
            continue
        texts = {
            text
            for field in (
                "text",
                "content_description",
                "hint_text",
                "tooltip",
            )
            if (text := _normalized_text(_element_value(element, field)))
        }
        infrastructure = {
            text
            for text in texts
            if INFRASTRUCTURE_FAILURE_RE.search(text)
        }
        if infrastructure:
            infrastructure_failures.update(infrastructure)
            # OS/app crash and ANR dialogs are environment evidence. They
            # must never be treated as ordinary task progress or as a
            # validation error that the policy should solve in-band.
            continue
        failures = {
            text for text in texts if VISIBLE_FAILURE_RE.search(text)
        }
        if failures:
            visible_failures.update(failures)
            # Treat transient validation overlays as evidence, not page
            # progress. The underlying form remains the semantic state.
            continue
        record: dict[str, Any] = {}
        for field in SEMANTIC_FIELDS:
            value = _element_value(element, field)
            if field in {
                "text",
                "content_description",
                "hint_text",
                "tooltip",
                "class_name",
                "package_name",
                "resource_name",
                "resource_id",
            }:
                value = _normalized_text(value)
            if value is not None:
                record[field] = value
        if record:
            records.append(record)
    if not records:
        return {
            "schema_version": "semantic_ui_snapshot.v1",
            "source": "screenshot_fallback",
            "sha256": fallback_sha256,
            "element_count": 0,
            "visible_failure_texts": sorted(visible_failures),
            "infrastructure_failure_texts": sorted(
                infrastructure_failures
            ),
        }
    encoded_records = sorted(
        (
            json.dumps(
                record,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            for record in records
        )
    )
    digest = sha256(
        json.dumps(
            encoded_records,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "semantic_ui_snapshot.v1",
        "source": "accessibility",
        "sha256": digest,
        "element_count": len(records),
        "visible_failure_texts": sorted(visible_failures),
        "infrastructure_failure_texts": sorted(
            infrastructure_failures
        ),
    }


class ProtocolV2DecisionGuard:
    """Fail closed on provenance errors and semantic no-progress loops."""

    def __init__(
        self,
        *,
        max_no_effect_repeats: int = 2,
        max_identical_coordinate_actions: int = 3,
    ) -> None:
        if max_no_effect_repeats < 1:
            raise ValueError("max_no_effect_repeats must be positive.")
        if max_identical_coordinate_actions < 1:
            raise ValueError(
                "max_identical_coordinate_actions must be positive."
            )
        self.max_no_effect_repeats = max_no_effect_repeats
        self.max_identical_coordinate_actions = (
            max_identical_coordinate_actions
        )
        self.reset(goal="")

    def reset(
        self,
        *,
        goal: str,
        required_selection_text: str | None = None,
        required_destination_text: str | None = None,
        required_source_text: str | None = None,
    ) -> None:
        self.goal = goal
        self.required_selection_text = required_selection_text
        self.required_destination_text = required_destination_text
        self.required_source_text = required_source_text
        self.no_effect_counts: dict[tuple[str, str], int] = defaultdict(int)
        self.blocked_fingerprints: set[tuple[str, str]] = set()
        self.transition_fingerprints: list[tuple[str, str, str]] = []
        self.validation_blocks: list[dict[str, Any]] = []
        self.cycle_trigger_count = 0
        self.visible_failure_trigger_count = 0
        self.recovery_obligations = 0
        self.recovery_completions = 0
        self.last_coordinate_action_key: str | None = None
        self.identical_coordinate_action_count = 0
        self.identical_coordinate_no_effect_count = 0
        self.identical_coordinate_block_count = 0
        self.destination_picker_back_block_count = 0
        self.destination_picker_empty_stall_block_count = 0
        self.files_roots_drawer_block_count = 0
        self.destination_picker_commit_count = 0
        self.post_destination_commit_block_count = 0
        self.post_destination_commit_active = False
        self.post_destination_source_exit_block_count = 0
        self.post_destination_verification_navigation_count = 0
        self.post_destination_verification_navigation_records: list[
            dict[str, Any]
        ] = []
        self.exact_target_long_press_block_count = 0
        self.focused_input_block_count = 0
        self.unfocused_clear_text_block_count = 0
        self.coordinate_text_target_block_count = 0
        self.declared_text_source_block_count = 0
        self.task_literal_field_role_block_count = 0
        self.soft_keyboard_swipe_block_count = 0
        self.focused_empty_tap_block_count = 0
        self.last_unverified_progress_no_effect_fingerprint: (
            tuple[str, str] | None
        ) = None
        self.unverified_progress_repeat_block_count = 0
        self.input_activation_repair_pending = False
        self.input_activation_action_key: str | None = None
        self.input_activation_proof_count = 0
        self.input_activation_proof_consumed_count = 0
        self.input_activation_repeat_override_count = 0
        self.visible_control_activation_repeat_override_fingerprints: set[
            tuple[str, str]
        ] = set()
        self.visible_control_activation_repeat_override_records: list[
            dict[str, Any]
        ] = []

    def mark_input_activation_repair(
        self,
        action: dict[str, Any],
    ) -> None:
        """Retain one-step proof that an editable activation tap executed."""
        if action.get("type") != "tap":
            raise ValueError("Input activation proof requires a tap.")
        self.input_activation_repair_pending = True
        self.input_activation_action_key = canonical_action_key(action)
        self.input_activation_proof_count += 1

    def _block_fingerprint(
        self,
        fingerprint: tuple[str, str],
    ) -> None:
        if fingerprint in self.blocked_fingerprints:
            return
        self.blocked_fingerprints.add(fingerprint)
        self.recovery_obligations += 1

    def _validate_text_provenance(
        self,
        decision: dict[str, Any],
        *,
        page_sha256: str,
        declared_source_assessment: dict[str, Any] | None = None,
        declared_source_soft_keyboard_present: bool = False,
    ) -> None:
        action = decision.get("action")
        if not isinstance(action, dict) or action.get("type") not in TEXT_ACTIONS:
            return
        action_type = action["type"]
        origin = action.get("text_origin")
        source_ids = action.get("source_memory_ids")
        if origin not in TEXT_ORIGINS:
            raise ActionValidationError(
                f"{action_type} requires a valid text_origin."
            )
        if not isinstance(source_ids, list):
            raise ActionValidationError(
                f"{action_type} requires source_memory_ids."
            )
        if origin == "verified_memory" and not source_ids:
            raise ActionValidationError(
                "verified_memory text requires at least one source memory ID."
            )
        if origin != "verified_memory" and source_ids:
            raise ActionValidationError(
                "source_memory_ids must be empty unless text_origin is "
                "verified_memory."
            )
        cited = set(decision.get("memory_citations", []))
        if not set(source_ids).issubset(cited):
            raise ActionValidationError(
                "source_memory_ids must also appear in memory_citations."
            )
        source_assessment = declared_source_assessment or {}
        if (
            origin in {"task_literal", "current_screen"}
            and source_assessment.get("adjudicable") is True
            and source_assessment.get("matched") is not True
        ):
            self.validation_blocks.append(
                {
                    "semantic_state_sha256": page_sha256,
                    "action": action,
                    "reason": "declared_text_source_not_matched",
                    "declared_text_source_assessment": source_assessment,
                    "soft_keyboard_present": (
                        declared_source_soft_keyboard_present
                    ),
                    "required_recovery_classes": [
                        "use_bound_declared_text_source",
                        "leave_unspecified_optional_field_untouched",
                    ],
                }
            )
            self.declared_text_source_block_count += 1
            visual_rejection = ""
            if source_assessment.get("visual_adjudication_required") is True:
                visual_rejection = (
                    " VISUAL_SOURCE_ADJUDICATION_REJECTED: the bounded "
                    "same-turn visual critic did not verify the exact answer "
                    "as fully readable and task-bound."
                )
            keyboard_recovery = ""
            if declared_source_soft_keyboard_present:
                keyboard_recovery = (
                    " SOFT_KEYBOARD_DISMISS_REQUIRED: the soft keyboard is "
                    "visible, so this bounded source repair must press back "
                    "once instead of swiping, typing, or changing a field."
                )
            raise ActionValidationError(
                "DECLARED_TEXT_SOURCE_GUARD: the proposed text declares "
                f"text_origin={origin}, but it is not present in that "
                "declared source on this turn."
                + visual_rejection
                + keyboard_recovery
                + " Do not relabel or invent the "
                "text. Use only a value visibly present in TASK or the "
                "current screen as declared, or leave an unspecified "
                "optional field untouched."
            )
        if action_type == "answer":
            if decision.get("status") != "done":
                raise ActionValidationError("answer must be terminal.")
            if not ANSWER_GOAL_RE.search(self.goal):
                raise ActionValidationError(
                    "answer is permitted only for an information-return goal."
                )

    def validate_decision(
        self,
        decision: dict[str, Any],
        *,
        page_sha256: str,
        destination_picker_is_active: bool = False,
        destination_picker_commit_is_action: bool = False,
        destination_picker_empty_stall_assessment: (
            dict[str, Any] | None
        ) = None,
        files_roots_drawer_action_assessment: (
            dict[str, Any] | None
        ) = None,
        post_destination_transfer_command_is_action: bool = False,
        exact_selection_assessment: dict[str, Any] | None = None,
        focused_input_assessment: dict[str, Any] | None = None,
        focused_empty_tap_assessment: dict[str, Any] | None = None,
        soft_keyboard_swipe_assessment: dict[str, Any] | None = None,
        coordinate_text_target_assessment: dict[str, Any] | None = None,
        declared_text_source_assessment: dict[str, Any] | None = None,
        declared_source_soft_keyboard_present: bool = False,
        task_literal_field_role_assessment: dict[str, Any] | None = None,
        allow_unfocused_input_activation_repeat: bool = False,
        visible_control_activation_retry_assessment: (
            dict[str, Any] | None
        ) = None,
        allow_visible_control_activation_repeat: bool = False,
        post_destination_source_context_assessment: (
            dict[str, Any] | None
        ) = None,
    ) -> None:
        self._validate_text_provenance(
            decision,
            page_sha256=page_sha256,
            declared_source_assessment=declared_text_source_assessment,
            declared_source_soft_keyboard_present=(
                declared_source_soft_keyboard_present
            ),
        )
        action = decision.get("action")
        if not isinstance(action, dict):
            return
        action_key = canonical_action_key(action)
        source_context_assessment = (
            post_destination_source_context_assessment or {}
        )
        if (
            self.post_destination_commit_active
            and not destination_picker_is_active
            and source_context_assessment.get("current_source_visible")
            is True
            and action.get("type") != "press_back"
        ):
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": "post_destination_source_exit_required",
                "post_destination_source_context_assessment": (
                    source_context_assessment
                ),
                "required_recovery_classes": ["navigate_back"],
            }
            self.validation_blocks.append(record)
            self.post_destination_source_exit_block_count += 1
            raise ActionValidationError(
                "POST_DESTINATION_SOURCE_EXIT_GUARD: one bottom Copy/Move "
                "commit already executed, and current Android Files "
                "accessibility still identifies the exact task source "
                "folder as the current top-level directory. Do not scroll, "
                "search, type, select, wait, or start another mutation here. "
                "Press Back exactly once, then observe the parent directory "
                "before navigating to the requested destination."
            )
        if (
            self.input_activation_repair_pending
            and action.get("type") == "tap"
            and action_key == self.input_activation_action_key
        ):
            self.validation_blocks.append(
                {
                    "semantic_state_sha256": page_sha256,
                    "action": action,
                    "reason": "post_activation_exact_tap_repeat_blocked",
                    "required_recovery_classes": [
                        "enter_task_bound_value",
                        "inspect_different_visible_control",
                    ],
                }
            )
            raise ActionValidationError(
                "POST_ACTIVATION_INPUT_GUARD: the immediately preceding "
                "bounded repair already executed this exact editable "
                "activation tap. Do not tap it again. If the activated input "
                "corresponds to a remaining TASK value, type that exact value "
                "now without x or y; otherwise choose a different non-commit "
                "action."
            )
        focused_assessment = focused_input_assessment or {}
        keyboard_swipe_assessment = (
            soft_keyboard_swipe_assessment or {}
        )
        field_role_assessment = task_literal_field_role_assessment or {}
        roots_drawer_assessment = (
            files_roots_drawer_action_assessment or {}
        )
        focused_tap_assessment = focused_empty_tap_assessment or {}
        if (
            focused_tap_assessment.get("adjudicable") is True
            and focused_tap_assessment.get("hits_focused_empty") is True
        ):
            self.validation_blocks.append(
                {
                    "semantic_state_sha256": page_sha256,
                    "action": action,
                    "reason": "focused_empty_editable_redundant_tap",
                    "focused_empty_tap_assessment": focused_tap_assessment,
                    "required_recovery_classes": [
                        "enter_task_bound_value",
                        "inspect_different_visible_control",
                    ],
                }
            )
            self.focused_empty_tap_block_count += 1
            raise ActionValidationError(
                "FOCUSED_EMPTY_TAP_GUARD: the proposed tap hits an "
                "already-focused empty editable control. Another tap cannot "
                "add cursor-position value to an empty field. Enter the "
                "remaining task-bound value without x,y and with "
                "clear_text=false, or choose a materially different "
                "non-commit action."
            )
        if (
            roots_drawer_assessment.get("adjudicable") is True
            and roots_drawer_assessment.get("drawer_active") is True
            and roots_drawer_assessment.get(
                "usable_storage_row_visible"
            )
            is True
            and roots_drawer_assessment.get(
                "progress_action_required"
            )
            is True
        ):
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": "files_roots_drawer_progress_action_required",
                "files_roots_drawer_action_assessment": (
                    roots_drawer_assessment
                ),
                "required_recovery_classes": [
                    "change_target",
                    "inspect_different_visible_control",
                ],
            }
            self.validation_blocks.append(record)
            self.files_roots_drawer_block_count += 1
            raise ActionValidationError(
                "FILES_ROOTS_DRAWER_GUARD: "
                "FILES_ROOTS_DRAWER_SELECTION_REQUIRED: the Android Files "
                "roots drawer is already open and a usable storage row is "
                "visible. Waiting, swiping, pressing back, or tapping an "
                "unbound title/menu area cannot select a root. Tap one "
                "visible enabled drawer row that advances toward the TASK "
                "storage or category. Do not reopen or scroll the drawer, "
                "and do not guess outside a visible row."
            )
        if (
            field_role_assessment.get("adjudicable") is True
            and field_role_assessment.get("matched") is not True
        ):
            self.validation_blocks.append(
                {
                    "semantic_state_sha256": page_sha256,
                    "action": action,
                    "reason": "task_literal_target_field_role_mismatch",
                    "task_literal_field_role_assessment": (
                        field_role_assessment
                    ),
                    "required_recovery_classes": [
                        "choose_role_matched_editable_field",
                        "leave_unrelated_optional_field_untouched",
                    ],
                }
            )
            self.task_literal_field_role_block_count += 1
            message = (
                "FIELD_VALUE_BINDING_GUARD: the task-literal value and the "
                "target editable field have conflicting semantic roles. "
                "Keep the same requested value and provenance, but choose a "
                "visible editable field whose label matches that value's "
                "role. Do not fill an unrelated optional field."
            )
            if keyboard_swipe_assessment.get(
                "soft_keyboard_present"
            ) is True:
                message += (
                    " SOFT_KEYBOARD_SWIPE_FORBIDDEN: the soft keyboard is "
                    "visible while the unrelated field is focused. Do not "
                    "swipe: a swipe beginning on the keyboard can be "
                    "interpreted as gesture text and pollute that field. "
                    "Choose a visibly supported role-matched field directly, "
                    "or press back once to dismiss only the keyboard and "
                    "observe the next screen."
                )
            raise ActionValidationError(message)
        if (
            keyboard_swipe_assessment.get("adjudicable") is True
            and keyboard_swipe_assessment.get("start_in_keyboard") is True
        ):
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": "soft_keyboard_swipe_start_blocked",
                "soft_keyboard_swipe_assessment": (
                    keyboard_swipe_assessment
                ),
                "required_recovery_classes": [
                    "dismiss_soft_keyboard",
                    "observe_next_screen",
                ],
            }
            self.validation_blocks.append(record)
            self.soft_keyboard_swipe_block_count += 1
            raise ActionValidationError(
                "SOFT_KEYBOARD_SWIPE_GUARD: "
                "SOFT_KEYBOARD_DISMISS_REQUIRED: the proposed swipe begins "
                "inside the visible soft keyboard and can be interpreted as "
                "gesture typing into the focused field. Do not execute the "
                "swipe. Press back once to dismiss only the keyboard, then "
                "observe the next screen before navigating or typing."
            )
        text_target_assessment = coordinate_text_target_assessment or {}
        coordinate_bearing_type_text = (
            action.get("type") == "type_text"
            and ("x" in action or "y" in action)
        )
        coordinate_targets_editable = (
            coordinate_bearing_type_text
            and text_target_assessment.get("adjudicable") is True
            and text_target_assessment.get("matched") is True
        )
        clears_focused_empty_field = (
            action.get("type") == "type_text"
            and action.get("clear_text") is True
            and focused_assessment.get("empty") is True
        )
        input_ready = focused_assessment.get(
            "input_ready",
            focused_assessment.get("present") is True,
        ) or self.input_activation_repair_pending
        redundant_unique_input_coordinate = (
            input_ready is True
            and coordinate_targets_editable
            and int(
                text_target_assessment.get(
                    "visible_editable_count",
                    0,
                )
            )
            == 1
        )
        if (
            self.input_activation_repair_pending
            and coordinate_bearing_type_text
            and coordinate_targets_editable
        ):
            post_activation_empty_directive = (
                " The visible target input was empty when activated, so set "
                "clear_text=false."
                if text_target_assessment.get("matched_empty") is True
                else " Preserve the proposed clear_text value."
            )
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": "post_activation_text_coordinate_blocked",
                "focused_input_assessment": focused_assessment,
                "coordinate_text_target_assessment": (
                    text_target_assessment
                ),
                "required_recovery_classes": [
                    "preserve_activated_input",
                ],
            }
            self.validation_blocks.append(record)
            self.focused_input_block_count += 1
            raise ActionValidationError(
                "FOCUSED_INPUT_GUARD: POST_ACTIVATION_INPUT_READY: the "
                "immediately preceding bounded repair already executed the "
                "visible editable activation tap. Keep the exact same "
                "type_text value and provenance, but omit x and y so "
                "AndroidWorld does not click away from that activated input."
                + post_activation_empty_directive
                + " No text or coordinate is supplied by the controller."
            )
        if (
            coordinate_targets_editable
            and input_ready is not True
            and action.get("clear_text") is True
        ):
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": "unfocused_clear_text_race_blocked",
                "focused_input_assessment": focused_assessment,
                "coordinate_text_target_assessment": (
                    text_target_assessment
                ),
                "required_recovery_classes": [
                    "activate_visible_input",
                    "observe_input_ready",
                ],
            }
            self.validation_blocks.append(record)
            self.unfocused_clear_text_block_count += 1
            raise ActionValidationError(
                "UNFOCUSED_CLEAR_TEXT_GUARD: the proposed coordinate hits a "
                "visible editable control, but text input is not yet active. "
                "AndroidWorld clicks x,y immediately before sending Ctrl+A "
                "for clear_text=true; focus activation can race and send "
                "Ctrl+A to the surrounding UI. Do not type on this screen. "
                "First tap the same visible input control, observe the next "
                "screen, and type only after input is visibly active."
            )
        if input_ready is True and (
            (
                coordinate_bearing_type_text
                and (
                    not coordinate_targets_editable
                    or redundant_unique_input_coordinate
                )
            )
            or (
                clears_focused_empty_field
                and not coordinate_targets_editable
            )
        ):
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": (
                    "focused_input_redundant_unique_coordinate_blocked"
                    if redundant_unique_input_coordinate
                    else "focused_input_click_before_type_blocked"
                ),
                "focused_input_assessment": focused_assessment,
                "coordinate_text_target_assessment": (
                    text_target_assessment
                ),
                "required_recovery_classes": [
                    "preserve_focused_input",
                ],
            }
            self.validation_blocks.append(record)
            self.focused_input_block_count += 1
            empty_directive = (
                " The target input is empty, so set clear_text=false."
                if (
                    focused_assessment.get("empty") is True
                    or (
                        redundant_unique_input_coordinate
                        and text_target_assessment.get("matched_empty")
                        is True
                    )
                )
                else ""
            )
            raise ActionValidationError(
                "FOCUSED_INPUT_GUARD: visible accessibility evidence shows "
                "that text input is already active through a focused "
                "editable field or the soft keyboard. AndroidWorld clicks "
                "supplied x,y before input, which can destroy that input "
                "target. Keep the same type_text text and provenance but "
                "omit x and y."
                + empty_directive
            )
        if (
            action.get("type") == "type_text"
            and input_ready is not True
            and text_target_assessment.get("adjudicable") is True
            and (
                text_target_assessment.get("coordinate_bearing") is not True
                or text_target_assessment.get("matched") is not True
            )
        ):
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": "coordinate_type_text_target_not_editable",
                "coordinate_text_target_assessment": (
                    text_target_assessment
                ),
                "required_recovery_classes": [
                    "activate_visible_input",
                    "inspect_different_visible_control",
                ],
            }
            self.validation_blocks.append(record)
            self.coordinate_text_target_block_count += 1
            visible_count = int(
                text_target_assessment.get(
                    "visible_editable_count",
                    0,
                )
            )
            binding_failure = (
                "no x,y was supplied"
                if text_target_assessment.get("coordinate_bearing") is not True
                else "the proposed x,y does not hit one"
            )
            raise ActionValidationError(
                "TEXT_TARGET_GUARD: text input is not already active, and "
                f"{binding_failure} of the visible enabled editable controls "
                f"({visible_count} visible editable controls). Do "
                "not type on this screen. First tap a visible input-opening "
                "control or navigate to an editable field, then observe the "
                "resulting screen before typing."
            )
        assessment = exact_selection_assessment or {}
        if (
            action.get("type") == "long_press"
            and assessment.get("adjudicable") is True
            and assessment.get("matched") is not True
        ):
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": "exact_selection_target_mismatch",
                "assessment": assessment,
                "required_recovery_classes": [
                    "change_target",
                    "inspect_different_visible_control",
                ],
            }
            self.validation_blocks.append(record)
            self.exact_target_long_press_block_count += 1
            required_text = str(
                assessment.get("required_text")
                or self.required_selection_text
                or ""
            )
            nearest_text = assessment.get("nearest_text")
            rendered_required = json.dumps(
                required_text,
                ensure_ascii=False,
            )
            rendered_nearest = json.dumps(
                nearest_text,
                ensure_ascii=False,
            )
            if assessment.get("exact_text_visible") is True:
                recovery = (
                    f"The exact task-literal filename {rendered_required} is "
                    "visible, but the proposed coordinate is nearest to "
                    f"{rendered_nearest}. Truncated grid labels make another "
                    "coordinate guess unsafe. Do not return any long_press "
                    "in this repair. Choose a non-long-press "
                    "information-gathering action such as tapping Search, "
                    "changing view mode, or scrolling; a later policy step "
                    "may select the file after observing the new screen."
                )
            else:
                recovery = (
                    f"The exact task-literal filename {rendered_required} is "
                    "not visible in current accessibility evidence; the "
                    "proposed coordinate is nearest to "
                    f"{rendered_nearest}. Do not return any long_press on "
                    "this screen. Choose a non-long-press navigation action "
                    "such as tapping Search, changing view mode, or scrolling "
                    "until the exact full filename is visible."
                )
            raise ActionValidationError(
                "EXACT_TARGET_GUARD: " + recovery
            )
        if self.post_destination_commit_active and (
            destination_picker_commit_is_action
            or post_destination_transfer_command_is_action
            or action.get("type") in {"long_press", "wait"}
        ):
            reason = (
                "post_destination_commit_stall_or_reselection_blocked"
                if action.get("type") in {"long_press", "wait"}
                else "post_destination_commit_mutation_blocked"
            )
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": reason,
                "required_recovery_classes": [
                    "inspect_different_visible_control",
                    "fail_safely",
                ],
            }
            self.validation_blocks.append(record)
            self.post_destination_commit_block_count += 1
            raise ActionValidationError(
                "POST_DESTINATION_COMMIT_GUARD: the bottom Copy/Move "
                "control was already executed in this task. Do not choose "
                "Move to/Copy to again, submit a second transaction, select "
                "or long-press an item, or wait on this stale screen. Use "
                "reversible navigation to inspect the requested destination "
                "or return a terminal status with current-screen evidence."
            )
        if (
            destination_picker_is_active
            and action.get("type") == "press_back"
            and not self.post_destination_commit_active
        ):
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": "destination_picker_back_blocked",
                "required_recovery_classes": [
                    "inspect_different_visible_control"
                ],
            }
            self.validation_blocks.append(record)
            self.destination_picker_back_block_count += 1
            raise ActionValidationError(
                "DESTINATION_PICKER_GUARD: bottom Cancel and Copy/Move "
                "controls prove that the destination picker is active. "
                "press_back would exit it and discard the pending operation. "
                "Keep the picker open and tap its top-left navigation drawer "
                "to change folders."
            )
        empty_picker_assessment = (
            destination_picker_empty_stall_assessment or {}
        )
        if (
            destination_picker_is_active
            and empty_picker_assessment.get("adjudicable") is True
            and empty_picker_assessment.get(
                "empty_destination_state"
            )
            is True
            and empty_picker_assessment.get("stalling_action") is True
        ):
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": "destination_picker_empty_stall_blocked",
                "destination_picker_empty_stall_assessment": (
                    empty_picker_assessment
                ),
                "required_recovery_classes": [
                    "inspect_different_visible_control",
                    "commit_current_destination_if_requested",
                ],
            }
            self.validation_blocks.append(record)
            self.destination_picker_empty_stall_block_count += 1
            raise ActionValidationError(
                "DESTINATION_PICKER_GUARD: "
                "DESTINATION_PICKER_EMPTY_STALL_REQUIRED: the destination "
                "picker has fully rendered an empty current directory. "
                "Waiting, swiping, or tapping an unbound title/content area "
                "cannot reveal sibling folders. If the visible current "
                "directory is the TASK destination, tap the visible bottom "
                "Copy/Move control; otherwise tap the visible top-left "
                "navigation drawer. Do not wait, swipe, press back, or guess "
                "a title/content-area coordinate."
            )
        fingerprint = (page_sha256, action_key)
        visible_control_retry = (
            visible_control_activation_retry_assessment or {}
        )
        bounded_input_activation_repeat = bool(
            allow_unfocused_input_activation_repeat
            and action.get("type") == "tap"
            and fingerprint
            == self.last_unverified_progress_no_effect_fingerprint
        )
        bounded_visible_control_activation_repeat = bool(
            allow_visible_control_activation_repeat
            and action.get("type") == "tap"
            and visible_control_retry.get("permitted") is True
            and fingerprint
            == self.last_unverified_progress_no_effect_fingerprint
            and fingerprint
            not in (
                self.visible_control_activation_repeat_override_fingerprints
            )
        )
        if bounded_input_activation_repeat:
            self.input_activation_repeat_override_count += 1
        elif bounded_visible_control_activation_repeat:
            self.visible_control_activation_repeat_override_fingerprints.add(
                fingerprint
            )
            self.visible_control_activation_repeat_override_records.append(
                {
                    "semantic_state_sha256": page_sha256,
                    "action": action,
                    "visible_control_activation_retry_assessment": (
                        visible_control_retry
                    ),
                }
            )
        elif (
            fingerprint
            == self.last_unverified_progress_no_effect_fingerprint
        ):
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": (
                    "unverified_progress_exact_repeat_blocked"
                ),
                "required_recovery_classes": list(RECOVERY_CLASSES),
                "visible_control_activation_retry_assessment": (
                    visible_control_retry
                ),
            }
            self.validation_blocks.append(record)
            self.unverified_progress_repeat_block_count += 1
            raise ActionValidationError(
                "LOOP_GUARD: UNVERIFIED_PROGRESS_REPEAT_REQUIRED: the "
                "immediately preceding identical action "
                "produced no semantic UI change while its state_delta only "
                "asserted unverified progress or a page hypothesis. Do not "
                "repeat that action. Choose a materially different recovery "
                "action based on the current screen."
            )
        if (
            action.get("type") in COORDINATE_STREAK_ACTIONS
            and action_key == self.last_coordinate_action_key
            and self.identical_coordinate_action_count
            >= self.max_identical_coordinate_actions
            and (
                action.get("type") != "swipe"
                or self.identical_coordinate_no_effect_count > 0
            )
        ):
            progress_conditioned_swipe_block = (
                action.get("type") == "swipe"
                and self.identical_coordinate_no_effect_count > 0
            )
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": (
                    "identical_coordinate_no_progress_streak_blocked"
                    if progress_conditioned_swipe_block
                    else "identical_coordinate_action_streak_blocked"
                ),
                "identical_coordinate_action_count": (
                    self.identical_coordinate_action_count
                ),
                "identical_coordinate_no_effect_count": (
                    self.identical_coordinate_no_effect_count
                ),
                "required_recovery_classes": list(RECOVERY_CLASSES),
            }
            self.validation_blocks.append(record)
            self.identical_coordinate_block_count += 1
            message = (
                "LOOP_GUARD: the current exact swipe streak already contains "
                "a transition with no semantic UI change. Do not execute "
                "another exact repeat. Re-read the current screen, tap the "
                "target directly if it is now visible, or use a different "
                "visible control or higher-level selector."
                if progress_conditioned_swipe_block
                else
                "LOOP_GUARD: the same coordinate tap or long-press has "
                "already been executed three consecutive times. Use a "
                "different visible control or a higher-level selector; do "
                "not perturb and retry the same coordinate."
            )
            raise ActionValidationError(message)
        if fingerprint in self.blocked_fingerprints:
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": "semantic_no_progress_action_blocked",
                "required_recovery_classes": list(RECOVERY_CLASSES),
            }
            self.validation_blocks.append(record)
            raise ActionValidationError(
                "LOOP_GUARD: this action is blocked on the current semantic "
                "UI state after no progress or a visible failure. Choose one "
                "recovery class: "
                + ", ".join(RECOVERY_CLASSES)
                + "."
            )

    def observe_transition(
        self,
        *,
        before_sha256: str,
        action: dict[str, Any],
        after_sha256: str,
        before_pixel_sha256: str | None = None,
        after_pixel_sha256: str | None = None,
        before_visible_failures: list[str] | tuple[str, ...] = (),
        after_visible_failures: list[str] | tuple[str, ...] = (),
        destination_picker_commit_executed: bool = False,
        post_destination_verification_navigation_assessment: (
            dict[str, Any] | None
        ) = None,
        claimed_unverified_progress: bool = False,
    ) -> dict[str, Any]:
        input_activation_proof_consumed = (
            self.input_activation_repair_pending
        )
        if input_activation_proof_consumed:
            self.input_activation_repair_pending = False
            self.input_activation_action_key = None
            self.input_activation_proof_consumed_count += 1
        action_key = canonical_action_key(action)
        fingerprint = (before_sha256, action_key)
        semantic_changed = before_sha256 != after_sha256
        pixel_changed = (
            before_pixel_sha256 != after_pixel_sha256
            if before_pixel_sha256 is not None
            and after_pixel_sha256 is not None
            else semantic_changed
        )
        new_visible_failures = sorted(
            set(after_visible_failures) - set(before_visible_failures)
        )
        if destination_picker_commit_executed:
            self.destination_picker_commit_count += 1
            self.post_destination_commit_active = True
        verification_navigation_assessment = (
            post_destination_verification_navigation_assessment or {}
        )
        post_destination_verification_navigation = bool(
            self.post_destination_commit_active
            and verification_navigation_assessment.get("permitted") is True
        )
        if post_destination_verification_navigation:
            self.post_destination_verification_navigation_count += 1
            self.post_destination_verification_navigation_records.append(
                {
                    "before_semantic_state_sha256": before_sha256,
                    "action": action,
                    "assessment": verification_navigation_assessment,
                }
            )
        if action.get("type") in COORDINATE_STREAK_ACTIONS:
            if action_key == self.last_coordinate_action_key:
                self.identical_coordinate_action_count += 1
                if not semantic_changed:
                    self.identical_coordinate_no_effect_count += 1
            else:
                self.last_coordinate_action_key = action_key
                self.identical_coordinate_action_count = 1
                self.identical_coordinate_no_effect_count = int(
                    not semantic_changed
                )
        else:
            self.last_coordinate_action_key = None
            self.identical_coordinate_action_count = 0
            self.identical_coordinate_no_effect_count = 0
        if semantic_changed:
            self.no_effect_counts.pop(fingerprint, None)
        else:
            self.no_effect_counts[fingerprint] += 1
            if (
                self.no_effect_counts[fingerprint]
                >= self.max_no_effect_repeats
            ):
                self._block_fingerprint(fingerprint)
        self.last_unverified_progress_no_effect_fingerprint = (
            fingerprint
            if not semantic_changed and claimed_unverified_progress
            else None
        )
        if new_visible_failures:
            self._block_fingerprint(fingerprint)
            self.visible_failure_trigger_count += 1
        self.transition_fingerprints.append(
            (before_sha256, action_key, after_sha256)
        )
        if len(self.transition_fingerprints) >= 4:
            a1, b1, a2, b2 = self.transition_fingerprints[-4:]
            if a1 == a2 and b1 == b2 and a1 != b1:
                self._block_fingerprint((a1[0], a1[1]))
                self._block_fingerprint((b1[0], b1[1]))
                self.cycle_trigger_count += 1
        if (
            self.recovery_obligations
            and fingerprint not in self.blocked_fingerprints
            and semantic_changed
            and not new_visible_failures
        ):
            self.recovery_completions += 1
            self.recovery_obligations -= 1
        return {
            "changed": pixel_changed,
            "pixel_changed": pixel_changed,
            "semantic_changed": semantic_changed,
            "semantic_no_progress_repeat_count": self.no_effect_counts.get(
                fingerprint, 0
            ),
            "no_effect_repeat_count": self.no_effect_counts.get(
                fingerprint, 0
            ),
            "fingerprint_blocked": fingerprint in self.blocked_fingerprints,
            "blocked_fingerprint_count": len(self.blocked_fingerprints),
            "identical_coordinate_action_count": (
                self.identical_coordinate_action_count
            ),
            "identical_coordinate_no_effect_count": (
                self.identical_coordinate_no_effect_count
            ),
            "destination_picker_commit_executed": (
                destination_picker_commit_executed
            ),
            "post_destination_commit_active": (
                self.post_destination_commit_active
            ),
            "post_destination_verification_navigation": (
                post_destination_verification_navigation
            ),
            "post_destination_verification_navigation_count": (
                self.post_destination_verification_navigation_count
            ),
            "unverified_progress_repeat_armed": (
                self.last_unverified_progress_no_effect_fingerprint
                == fingerprint
            ),
            "input_activation_proof_consumed": (
                input_activation_proof_consumed
            ),
            "visible_control_activation_repeat_override_count": len(
                self.visible_control_activation_repeat_override_fingerprints
            ),
            "new_visible_failures": new_visible_failures,
        }

    def audit_record(self) -> dict[str, Any]:
        return {
            "schema_version": "protocol_v2_guard_audit.v1",
            "max_no_effect_repeats": self.max_no_effect_repeats,
            "max_identical_coordinate_actions": (
                self.max_identical_coordinate_actions
            ),
            "identical_coordinate_action_count": (
                self.identical_coordinate_action_count
            ),
            "identical_coordinate_no_effect_count": (
                self.identical_coordinate_no_effect_count
            ),
            "required_selection_text": self.required_selection_text,
            "required_destination_text": self.required_destination_text,
            "required_source_text": self.required_source_text,
            "blocked_fingerprint_count": len(self.blocked_fingerprints),
            "validation_block_count": len(self.validation_blocks),
            "identical_coordinate_block_count": (
                self.identical_coordinate_block_count
            ),
            "destination_picker_back_block_count": (
                self.destination_picker_back_block_count
            ),
            "destination_picker_empty_stall_block_count": (
                self.destination_picker_empty_stall_block_count
            ),
            "files_roots_drawer_block_count": (
                self.files_roots_drawer_block_count
            ),
            "destination_picker_commit_count": (
                self.destination_picker_commit_count
            ),
            "post_destination_commit_block_count": (
                self.post_destination_commit_block_count
            ),
            "post_destination_commit_active": (
                self.post_destination_commit_active
            ),
            "post_destination_source_exit_block_count": (
                self.post_destination_source_exit_block_count
            ),
            "post_destination_verification_navigation_count": (
                self.post_destination_verification_navigation_count
            ),
            "post_destination_verification_navigation_records": list(
                self.post_destination_verification_navigation_records
            ),
            "exact_target_long_press_block_count": (
                self.exact_target_long_press_block_count
            ),
            "focused_input_block_count": self.focused_input_block_count,
            "unfocused_clear_text_block_count": (
                self.unfocused_clear_text_block_count
            ),
            "coordinate_text_target_block_count": (
                self.coordinate_text_target_block_count
            ),
            "declared_text_source_block_count": (
                self.declared_text_source_block_count
            ),
            "task_literal_field_role_block_count": (
                self.task_literal_field_role_block_count
            ),
            "soft_keyboard_swipe_block_count": (
                self.soft_keyboard_swipe_block_count
            ),
            "focused_empty_tap_block_count": (
                self.focused_empty_tap_block_count
            ),
            "unverified_progress_repeat_block_count": (
                self.unverified_progress_repeat_block_count
            ),
            "input_activation_repair_pending": (
                self.input_activation_repair_pending
            ),
            "input_activation_proof_count": (
                self.input_activation_proof_count
            ),
            "input_activation_proof_consumed_count": (
                self.input_activation_proof_consumed_count
            ),
            "input_activation_repeat_override_count": (
                self.input_activation_repeat_override_count
            ),
            "visible_control_activation_repeat_override_count": len(
                self.visible_control_activation_repeat_override_fingerprints
            ),
            "visible_control_activation_repeat_override_records": list(
                self.visible_control_activation_repeat_override_records
            ),
            "ab_ab_cycle_trigger_count": self.cycle_trigger_count,
            "visible_failure_trigger_count": (
                self.visible_failure_trigger_count
            ),
            "validation_blocks": self.validation_blocks,
            "recovery_obligation_count": self.recovery_obligations,
            "recovery_completion_count": self.recovery_completions,
        }
