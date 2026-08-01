"""Generic protocol-v2 provenance and repeated-action guard."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import math
from pathlib import Path
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
INSPECTION_NAVIGATION_CONTROL_RE = re.compile(
    r"\b(more\s+options|overflow|information|info|details?|edit)\b",
    flags=re.IGNORECASE,
)
MAX_INSPECTION_CONTROL_CANDIDATES = 8
TOOLBAR_AFFORDANCE_ROLE_RES = {
    "date": re.compile(
        r"\b(calendar|date(?:\s+picker)?|day\s+picker|month\s+grid)\b",
        flags=re.IGNORECASE,
    ),
    "search": re.compile(
        r"\b(search|filter|query|find)(?:ing|ed|es)?\b",
        flags=re.IGNORECASE,
    ),
    "marker": re.compile(
        r"\b(marker|markers|map|maps|location|locations|place|places)\b",
        flags=re.IGNORECASE,
    ),
}
MONTH_NAME_TO_NUMBER = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}
MONTH_TOKEN = "(?:" + "|".join(
    sorted(MONTH_NAME_TO_NUMBER, key=len, reverse=True)
) + ")"
MONTH_FIRST_DATE_RE = re.compile(
    rf"\b(?P<month>{MONTH_TOKEN})\.?\s+(?P<day>\d{{1,2}})"
    r"(?:st|nd|rd|th)?(?:\s*,?\s*(?P<year>\d{4}))?\b",
    flags=re.IGNORECASE,
)
DAY_FIRST_DATE_RE = re.compile(
    rf"\b(?P<day>\d{{1,2}})(?:st|nd|rd|th)?\s+"
    rf"(?P<month>{MONTH_TOKEN})\.?(?:\s*,?\s*(?P<year>\d{{4}}))?\b",
    flags=re.IGNORECASE,
)
NUMERIC_DATE_RE = re.compile(
    r"\b(?P<year>20\d{2})[-/.](?P<month>0?[1-9]|1[0-2])"
    r"[-/.](?P<day>0?[1-9]|[12]\d|3[01])\b"
)
CHRONOLOGICAL_LABEL_RE = re.compile(
    rf"^(?:today|yesterday|monday|tuesday|wednesday|thursday|friday|"
    rf"saturday|sunday|mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun|"
    rf"{MONTH_TOKEN}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?|"
    rf"\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTH_TOKEN}\.?)$",
    flags=re.IGNORECASE,
)
ANSWER_FIELD_REQUEST_RE = re.compile(
    r"\banswer\s+with\s+(?:the\s+)?"
    r"(?P<role>[a-z][a-z0-9 /_-]{0,60}?)"
    r"(?=\s+only\b|[.;,\n]|$)",
    flags=re.IGNORECASE,
)
DETAIL_REQUIRED_ANSWER_ROLE_RE = re.compile(
    r"\b(types?|categories|category|kinds?|durations?|distances?|"
    r"times?|statuses|status|amounts?|locations?|descriptions?|"
    r"notes?|values?)\b",
    flags=re.IGNORECASE,
)
IGNORED_UI_PACKAGES = {"com.android.systemui"}
SOFT_KEYBOARD_PACKAGES = {
    "com.android.inputmethod.latin",
    "com.google.android.inputmethod.latin",
}
ANDROID_FILES_PACKAGES = {"com.google.android.documentsui"}
FILES_VIEW_MODE_LABEL_RE = re.compile(
    r"^(?:(?:show|display)\s+(?:as\s+)?)?"
    r"(?:list|grid)(?:\s+(?:view|layout|mode))?$",
    flags=re.IGNORECASE,
)
FILES_VIEW_MODE_RESOURCE_RE = re.compile(
    r"(?:^|[/.:_-])(?:action|menu|mode|view)[_-]?(?:list|grid)"
    r"(?:$|[/.:_-])",
    flags=re.IGNORECASE,
)
REPEATED_TAP_GOAL_RE = re.compile(
    r"\b(?P<verb>click|tap|press)\b"
    r"(?P<target>[^.;\n]{0,120}?)"
    r"\b(?P<count>[2-9]|1\d|20|two|three|four|five|six|seven|eight|"
    r"nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
    r"seventeen|eighteen|nineteen|twenty)\s+times\b",
    flags=re.IGNORECASE,
)
PACKAGE_GOAL_BINDING_STOPWORDS = {
    "android",
    "app",
    "apps",
    "com",
    "google",
    "org",
    "provider",
    "providers",
    "system",
    "ui",
}
REPEATED_TARGET_STOPWORDS = {
    "a",
    "an",
    "button",
    "control",
    "icon",
    "item",
    "once",
    "the",
    "this",
}
NUMERIC_REPEAT_RESULT_GOAL_RE = re.compile(
    r"\b(?:number|numbers|value|values)\b[^.;\n]{0,160}?"
    r"\b(?:product|multiply|sum|average|total)\b",
    flags=re.IGNORECASE,
)
EXACT_NUMERIC_LABEL_RE = re.compile(
    r"^[+-]?(?:\d+(?:\.\d+)?|\.\d+)$"
)
NUMBER_WORD_VALUES = {
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}
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


def bounded_task_repeated_tap_assessment(
    goal: str,
    ui_elements: Any,
    action: dict[str, Any] | None,
    *,
    prior_identical_coordinate_action_count: int,
    identical_coordinate_no_effect_count: int,
    screen_width: int,
    screen_height: int,
    transition_context: dict[str, Any] | None = None,
    current_visible_failures: tuple[str, ...] | list[str] = (),
) -> dict[str, Any]:
    """Authorize only finite task-literal repeats on a safe visible control."""
    match = REPEATED_TAP_GOAL_RE.search(goal or "")
    token = match.group("count").casefold() if match else None
    requested_repetitions = (
        int(token)
        if token is not None and token.isdigit()
        else NUMBER_WORD_VALUES.get(token or "")
    )
    control = visible_control_activation_retry_assessment(
        ui_elements,
        action,
        screen_width=screen_width,
        screen_height=screen_height,
    )
    numeric_result = visible_numeric_repeat_result_assessment(
        goal,
        ui_elements,
        allowed_packages=control["matched_packages"],
    )
    matched_class_names: set[str] = set()
    matched_resource_ids: set[str] = set()
    matched_button_like_count = 0
    for element in ui_elements or ():
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
        class_name = _normalized_text(
            _element_value(element, "class_name")
        )
        resource_id = _normalized_text(
            _element_value(element, "resource_id")
        )
        if class_name is not None:
            matched_class_names.add(class_name)
        if resource_id is not None:
            matched_resource_ids.add(resource_id)
        matched_button_like_count += int(
            bool(
                (
                    class_name
                    and class_name.casefold().endswith("button")
                )
                or (
                    resource_id
                    and re.search(
                        r"(?:^|[/.:_-])button(?:$|[/.:_-])",
                        resource_id,
                        flags=re.IGNORECASE,
                    )
                )
            )
        )
    target_fragment = (
        _normalized_text(match.group("target")) if match else None
    )
    target_tokens = {
        token
        for token in re.findall(
            r"[a-z0-9]+",
            (target_fragment or "").casefold(),
        )
        if token not in REPEATED_TARGET_STOPWORDS
    }
    label_tokens = {
        token
        for label in control["matched_labels"]
        for token in re.findall(r"[a-z0-9]+", label.casefold())
    }
    explicit_label_bound = bool(target_tokens & label_tokens)
    package_goal_tokens = {
        token
        for package_name in control["matched_packages"]
        for token in re.findall(r"[a-z0-9]+", package_name.casefold())
        if token not in PACKAGE_GOAL_BINDING_STOPWORDS
        and len(token) >= 3
    }
    goal_tokens = set(
        re.findall(r"[a-z0-9]+", (goal or "").casefold())
    )
    package_goal_bound = bool(package_goal_tokens & goal_tokens)
    generic_button_target = bool(
        target_fragment
        and re.search(
            r"\bbutton\b",
            target_fragment,
            flags=re.IGNORECASE,
        )
    )
    target_role_bound = bool(
        generic_button_target
        and matched_button_like_count == 1
    )
    task_target_bound = bool(
        control.get("matched_control_count") == 1
        and (
            explicit_label_bound
            or (target_role_bound and package_goal_bound)
        )
    )
    transition = transition_context or {}
    deferred_semantic_progress_observed = bool(
        task_target_bound
        and identical_coordinate_no_effect_count > 0
        and transition.get("proposed_action_matches_last_coordinate")
        is True
        and transition.get("last_transition_action_matches") is True
        and transition.get("last_transition_semantic_no_effect") is True
        and transition.get(
            "current_semantic_differs_from_last_recorded_after"
        )
        is True
        and transition.get("last_transition_fingerprint_blocked")
        is False
        and not current_visible_failures
    )
    effective_no_effect_count = max(
        0,
        identical_coordinate_no_effect_count
        - int(deferred_semantic_progress_observed),
    )
    proposed_ordinal = prior_identical_coordinate_action_count + 1
    permitted = bool(
        isinstance(action, dict)
        and action.get("type") == "tap"
        and requested_repetitions is not None
        and 2 <= proposed_ordinal <= requested_repetitions
        and effective_no_effect_count == 0
        and control.get("permitted") is True
        and control.get("matched_control_count") == 1
        and task_target_bound
    )
    pre_action_numeric_operand_bound = bool(
        task_target_bound
        and numeric_result["collection_bound"]
        and numeric_result["unique_visible_numeric_result"] is not None
    )
    return {
        "schema_version": "bounded_task_repeated_tap_assessment.v3",
        "adjudicable": bool(match and control.get("adjudicable")),
        "action_type": (
            action.get("type") if isinstance(action, dict) else None
        ),
        "requested_repetitions": requested_repetitions,
        "target_fragment": target_fragment,
        "target_tokens": sorted(target_tokens),
        "prior_identical_coordinate_action_count": (
            prior_identical_coordinate_action_count
        ),
        "proposed_ordinal": proposed_ordinal,
        "identical_coordinate_no_effect_count": (
            identical_coordinate_no_effect_count
        ),
        "effective_identical_coordinate_no_effect_count": (
            effective_no_effect_count
        ),
        "deferred_semantic_progress_observed": (
            deferred_semantic_progress_observed
        ),
        "matched_control_count": control["matched_control_count"],
        "matched_packages": control["matched_packages"],
        "matched_labels": control["matched_labels"],
        "matched_class_names": sorted(matched_class_names),
        "matched_resource_ids": sorted(matched_resource_ids),
        "matched_button_like_count": matched_button_like_count,
        "explicit_label_bound": explicit_label_bound,
        "package_goal_bound": package_goal_bound,
        "task_target_bound": task_target_bound,
        "numeric_result_collection_bound": numeric_result[
            "collection_bound"
        ],
        "visible_numeric_result_candidates": numeric_result[
            "visible_numeric_result_candidates"
        ],
        "unique_visible_numeric_result": numeric_result[
            "unique_visible_numeric_result"
        ],
        "pre_action_numeric_operand_bound": (
            pre_action_numeric_operand_bound
        ),
        "current_visible_failures": sorted(current_visible_failures),
        "commit_like": control["commit_like"],
        "permitted": permitted,
    }


def visible_numeric_repeat_result_assessment(
    goal: str,
    ui_elements: Any,
    *,
    allowed_packages: list[str] | tuple[str, ...] | set[str],
) -> dict[str, Any]:
    """Extract one exact numeric result from the task-bound application."""
    packages = set(allowed_packages)
    candidates: set[str] = set()
    for element in ui_elements or ():
        package_name = _normalized_text(
            _element_value(element, "package_name")
        )
        if package_name not in packages:
            continue
        if _element_value(element, "is_visible") is not True:
            continue
        if _element_value(element, "is_clickable") is True:
            continue
        if _element_value(element, "is_editable") is True:
            continue
        for field in (
            "text",
            "content_description",
            "hint_text",
            "tooltip",
        ):
            label = _normalized_text(_element_value(element, field))
            if label and EXACT_NUMERIC_LABEL_RE.fullmatch(label):
                candidates.add(label)
    ordered = sorted(candidates)
    collection_bound = bool(
        NUMERIC_REPEAT_RESULT_GOAL_RE.search(goal or "")
    )
    return {
        "schema_version": "visible_numeric_repeat_result_assessment.v1",
        "collection_bound": collection_bound,
        "allowed_packages": sorted(packages),
        "visible_numeric_result_candidates": ordered,
        "unique_visible_numeric_result": (
            ordered[0]
            if collection_bound and len(ordered) == 1
            else None
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
    """Bind post-transfer verification to an exact destination content label."""
    action_type = (
        action.get("type") if isinstance(action, dict) else None
    )
    required_label = _normalized_text(required_destination_text)
    exact_label_hits: list[dict[str, Any]] = []
    content_exact_label_hits: list[dict[str, Any]] = []
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
            bbox = _normalized_element_bbox(
                element,
                screen_width=screen_width,
                screen_height=screen_height,
            )
            if bbox is not None:
                x_min, x_max, y_min, y_max = bbox
                center_y = (y_min + y_max) / 2.0
                exact_hit = {
                    "package_name": package_name,
                    "labels": labels,
                    "commit_like": any(
                        COMMIT_LIKE_CONTROL_RE.search(label)
                        for label in labels
                    ),
                    "is_editable": (
                        _element_value(element, "is_editable") is True
                    ),
                    "normalized_bbox": {
                        "x_min": round(x_min, 6),
                        "x_max": round(x_max, 6),
                        "y_min": round(y_min, 6),
                        "y_max": round(y_max, 6),
                    },
                    "center_y": round(center_y, 6),
                }
                exact_label_hits.append(exact_hit)
                # Android Files folder rows/cards are sometimes exposed as
                # exact text nodes without a separately clickable ancestor.
                # Require the hit to be in the content region so a current
                # title or breadcrumb cannot qualify as destination
                # navigation.
                if (
                    _element_value(element, "is_editable") is not True
                    and center_y > 0.20
                ):
                    content_exact_label_hits.append(exact_hit)
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
    ) or any(
        hit["commit_like"]
        for hit in [*exact_label_hits, *clickable_hits]
    )
    return {
        "schema_version": (
            "post_destination_verification_navigation_assessment.v2"
        ),
        "adjudicable": bool(ui_elements and required_label),
        "action_type": action_type,
        "required_destination_text": required_label,
        "exact_label_hit_count": len(exact_label_hits),
        "content_exact_label_hit_count": len(content_exact_label_hits),
        "clickable_hit_count": len(clickable_hits),
        "exact_label_hits": exact_label_hits,
        "content_exact_label_hits": content_exact_label_hits,
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
            and content_exact_label_hits
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


def _affordance_roles(text: str | None) -> set[str]:
    if not text:
        return set()
    return {
        role
        for role, pattern in TOOLBAR_AFFORDANCE_ROLE_RES.items()
        if pattern.search(text)
    }


def _absolute_dates(text: str | None) -> set[tuple[int | None, int, int]]:
    """Extract only explicit calendar dates, never relative date language."""
    dates: set[tuple[int | None, int, int]] = set()
    value = text or ""
    for pattern in (MONTH_FIRST_DATE_RE, DAY_FIRST_DATE_RE):
        for match in pattern.finditer(value):
            month = MONTH_NAME_TO_NUMBER[match.group("month").casefold()]
            year_text = match.group("year")
            dates.add(
                (
                    int(year_text) if year_text else None,
                    month,
                    int(match.group("day")),
                )
            )
    for match in NUMERIC_DATE_RE.finditer(value):
        dates.add(
            (
                int(match.group("year")),
                int(match.group("month")),
                int(match.group("day")),
            )
        )
    return dates


def _dates_match(
    target: tuple[int | None, int, int],
    visible: tuple[int | None, int, int],
) -> bool:
    target_year, target_month, target_day = target
    visible_year, visible_month, visible_day = visible
    return bool(
        target_month == visible_month
        and target_day == visible_day
        and (
            target_year is None
            or visible_year is None
            or target_year == visible_year
        )
    )


def chronological_list_navigation_assessment(
    goal: str,
    ui_elements: Any,
    *,
    screen_width: int,
    screen_height: int,
) -> dict[str, Any]:
    """Detect a vertically arranged chronological history with an older target."""
    target_dates = _absolute_dates(goal)
    visible_dates: set[tuple[int | None, int, int]] = set()
    date_anchors: list[dict[str, Any]] = []
    visible_labels: list[str] = []
    for element in ui_elements or ():
        if _element_value(element, "is_visible") is False:
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
                label := _normalized_text(_element_value(element, field))
            )
            is not None
        ]
        for label in labels:
            visible_labels.append(label)
            visible_dates.update(_absolute_dates(label))
            if not CHRONOLOGICAL_LABEL_RE.fullmatch(label.strip()):
                continue
            bbox = _normalized_element_bbox(
                element,
                screen_width=screen_width,
                screen_height=screen_height,
            )
            if bbox is None:
                continue
            x_min, x_max, y_min, y_max = bbox
            anchor_dates = _absolute_dates(label)
            date_anchors.append(
                {
                    "label": label,
                    "x_center": round((x_min + x_max) / 2, 6),
                    "y_center": round((y_min + y_max) / 2, 6),
                    "dates": [
                        {"year": year, "month": month, "day": day}
                        for year, month, day in sorted(
                            anchor_dates,
                            key=lambda item: (
                                item[0] or 0,
                                item[1],
                                item[2],
                            ),
                        )
                    ],
                }
            )
    x_centers = [item["x_center"] for item in date_anchors]
    y_centers = [item["y_center"] for item in date_anchors]
    vertically_distributed = bool(
        len(date_anchors) >= 3
        and max(y_centers) - min(y_centers) >= 0.12
    )
    left_or_center_aligned = bool(
        len(date_anchors) >= 3
        and max(x_centers) - min(x_centers) <= 0.35
    )
    chronological_history_detected = bool(
        vertically_distributed and left_or_center_aligned
    )

    target_visible = any(
        _dates_match(target, visible)
        for target in target_dates
        for visible in visible_dates
    )
    dated_anchors = [
        anchor for anchor in date_anchors if anchor["dates"]
    ]
    bottom_visible_date = None
    if dated_anchors:
        bottom_anchor = max(
            dated_anchors,
            key=lambda anchor: anchor["y_center"],
        )
        bottom_visible_date = bottom_anchor["dates"][0]

    def target_is_older(
        target: tuple[int | None, int, int],
        visible: dict[str, int | None],
    ) -> bool:
        target_year, target_month, target_day = target
        visible_year = visible["year"]
        if target_year is not None and visible_year is not None:
            return (target_year, target_month, target_day) < (
                visible_year,
                visible["month"],
                visible["day"],
            )
        return (target_month, target_day) < (
            visible["month"],
            visible["day"],
        )

    target_older_than_visible_history = bool(
        bottom_visible_date is not None
        and any(
            target_is_older(target, bottom_visible_date)
            for target in target_dates
        )
    )
    scroll_toward_older_required = bool(
        target_dates
        and chronological_history_detected
        and not target_visible
        and target_older_than_visible_history
    )
    return {
        "schema_version": "chronological_list_navigation_assessment.v1",
        "target_dates": [
            {"year": year, "month": month, "day": day}
            for year, month, day in sorted(
                target_dates,
                key=lambda item: (item[0] or 0, item[1], item[2]),
            )
        ],
        "visible_dates": [
            {"year": year, "month": month, "day": day}
            for year, month, day in sorted(
                visible_dates,
                key=lambda item: (item[0] or 0, item[1], item[2]),
            )
        ],
        "visible_label_count": len(visible_labels),
        "date_anchor_count": len(date_anchors),
        "date_anchors": date_anchors,
        "vertically_distributed": vertically_distributed,
        "left_or_center_aligned": left_or_center_aligned,
        "chronological_history_detected": chronological_history_detected,
        "target_visible": target_visible,
        "bottom_visible_date": bottom_visible_date,
        "target_older_than_visible_history": (
            target_older_than_visible_history
        ),
        "scroll_toward_older_required": scroll_toward_older_required,
    }


def toolbar_affordance_claim_assessment(
    goal: str,
    ui_elements: Any,
    decision: dict[str, Any] | None,
    *,
    screen_width: int,
    screen_height: int,
) -> dict[str, Any]:
    """Bind a claimed toolbar outcome to the tapped control's visible role."""
    action = decision.get("action") if isinstance(decision, dict) else None
    expected_outcome = (
        _normalized_text(decision.get("expected_outcome"))
        if isinstance(decision, dict)
        else None
    )
    decision_summary = (
        _normalized_text(decision.get("decision_summary"))
        if isinstance(decision, dict)
        else None
    )
    expected_roles = _affordance_roles(expected_outcome)
    expected_role_source = "expected_outcome"
    if not expected_roles:
        expected_roles = _affordance_roles(decision_summary)
        expected_role_source = "decision_summary"
    matched_controls: list[dict[str, Any]] = []
    target_roles: set[str] = set()
    for element in ui_elements or ():
        package_name = _normalized_text(
            _element_value(element, "package_name")
        )
        if package_name in IGNORED_UI_PACKAGES:
            continue
        if _element_value(element, "is_visible") is not True:
            continue
        if _element_value(element, "is_enabled") is not True:
            continue
        if _element_value(element, "is_clickable") is not True:
            continue
        if not _tap_hits_element(
            action,
            element,
            screen_width=screen_width,
            screen_height=screen_height,
        ):
            continue
        bbox = _normalized_element_bbox(
            element,
            screen_width=screen_width,
            screen_height=screen_height,
        )
        if bbox is None or (bbox[2] + bbox[3]) / 2 > 0.16:
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
                label := _normalized_text(_element_value(element, field))
            )
            is not None
        ]
        control_roles = set().union(
            *(_affordance_roles(label) for label in labels)
        )
        if not labels:
            continue
        target_roles.update(control_roles)
        matched_controls.append(
            {
                "labels": labels,
                "roles": sorted(control_roles),
                "bbox": [round(value, 6) for value in bbox],
            }
        )
    role_match = bool(expected_roles.intersection(target_roles))
    adjudicable = bool(
        isinstance(action, dict)
        and action.get("type") == "tap"
        and matched_controls
        and expected_roles
        and target_roles
    )
    chronology = chronological_list_navigation_assessment(
        goal,
        ui_elements,
        screen_width=screen_width,
        screen_height=screen_height,
    )
    return {
        "schema_version": "toolbar_affordance_claim_assessment.v1",
        "action_type": action.get("type") if isinstance(action, dict) else None,
        "expected_role_source": expected_role_source,
        "expected_roles": sorted(expected_roles),
        "target_roles": sorted(target_roles),
        "matched_controls": matched_controls,
        "adjudicable": adjudicable,
        "matched": role_match if adjudicable else None,
        "chronological_list_navigation_assessment": chronology,
    }


def _requested_answer_role(goal: str) -> str | None:
    match = ANSWER_FIELD_REQUEST_RE.search(goal or "")
    if match is None:
        return None
    role = match.group("role").strip()
    return role or None


def requested_field_value_assessment(
    goal: str,
    ui_elements: Any,
    decision: dict[str, Any] | None,
    *,
    screen_width: int,
    screen_height: int,
) -> dict[str, Any]:
    """Detect a visible value control whose metadata names the asked field.

    This assessment deliberately withholds the value text.  It only proves
    that the pixels contain a readable value in a control whose accessible
    metadata matches the requested field role, and supplies geometry so the
    controller can retain a small screenshot crop as visual evidence.
    """
    requested_role = _requested_answer_role(goal)
    role_tokens = set(
        re.findall(r"[a-z]+", (requested_role or "").casefold())
    )
    singular_role_tokens = {
        {
            "categories": "category",
            "statuses": "status",
        }.get(token, token[:-1] if token.endswith("s") else token)
        for token in role_tokens
    }
    if singular_role_tokens.intersection({"type", "category", "kind"}):
        singular_role_tokens.update({"type", "category", "kind"})
    singular_role_tokens.difference_update(
        {"a", "an", "answer", "activity", "only", "the"}
    )

    matched_bboxes: list[dict[str, float]] = []
    matched_metadata_fields: set[str] = set()
    mutation_controls: list[dict[str, Any]] = []
    visible_control_bboxes: list[dict[str, float]] = []
    inspection_controls: list[dict[str, Any]] = []
    action = decision.get("action") if isinstance(decision, dict) else None
    tap_x = action.get("x") if isinstance(action, dict) else None
    tap_y = action.get("y") if isinstance(action, dict) else None

    for element in ui_elements or ():
        if _element_value(element, "is_visible") is False:
            continue
        bbox = _normalized_element_bbox(
            element,
            screen_width=screen_width,
            screen_height=screen_height,
        )
        if (
            bbox is not None
            and _element_value(element, "is_clickable") is True
            and _element_value(element, "is_enabled") is not False
        ):
            visible_control_bboxes.append(
                {
                    "x_min": round(float(bbox[0]), 6),
                    "x_max": round(float(bbox[1]), 6),
                    "y_min": round(float(bbox[2]), 6),
                    "y_max": round(float(bbox[3]), 6),
                }
            )
        text = _normalized_text(_element_value(element, "text"))
        metadata: dict[str, str] = {}
        for field in (
            "resource_id",
            "hint_text",
            "content_description",
            "tooltip",
        ):
            value = _normalized_text(_element_value(element, field))
            if value is not None:
                metadata[field] = value
        metadata_tokens = set(
            re.findall(
                r"[a-z]+",
                " ".join(metadata.values()).casefold(),
            )
        )
        role_matched = bool(
            singular_role_tokens
            and singular_role_tokens.intersection(metadata_tokens)
        )
        text_tokens = set(re.findall(r"[a-z]+", (text or "").casefold()))
        value_is_distinct = bool(
            text
            and not (
                text_tokens
                and text_tokens <= singular_role_tokens
            )
        )
        if role_matched and value_is_distinct and bbox is not None:
            matched_bboxes.append(
                {
                    "x_min": round(float(bbox[0]), 6),
                    "x_max": round(float(bbox[1]), 6),
                    "y_min": round(float(bbox[2]), 6),
                    "y_max": round(float(bbox[3]), 6),
                }
            )
            matched_metadata_fields.update(metadata)

        labels = [
            value
            for field in ("text", "content_description", "tooltip")
            if (
                value := _normalized_text(_element_value(element, field))
            )
            is not None
        ]
        mutation_label = next(
            (
                label
                for label in labels
                if re.search(
                    r"\b(save|submit|apply|confirm|delete|send|record)\b",
                    label,
                    flags=re.IGNORECASE,
                )
            ),
            None,
        )
        if mutation_label is not None and bbox is not None:
            mutation_controls.append(
                {
                    "label": mutation_label,
                    "bbox": {
                        "x_min": round(float(bbox[0]), 6),
                        "x_max": round(float(bbox[1]), 6),
                        "y_min": round(float(bbox[2]), 6),
                        "y_max": round(float(bbox[3]), 6),
                    },
                }
            )
        semantic_label = next(
            (
                label
                for label in (
                    _normalized_text(
                        _element_value(element, "content_description")
                    ),
                    text,
                    _normalized_text(_element_value(element, "tooltip")),
                )
                if label is not None
            ),
            None,
        )
        resource_label = _normalized_text(
            _element_value(element, "resource_id")
        )
        inspection_label = semantic_label
        if inspection_label is None and resource_label is not None:
            inspection_label = re.sub(
                r"[^a-z0-9]+",
                " ",
                resource_label.casefold(),
            ).strip()
        inspection_match = (
            INSPECTION_NAVIGATION_CONTROL_RE.search(inspection_label)
            if inspection_label and len(inspection_label) <= 80
            else None
        )
        inspection_navigation = bool(
            bbox is not None
            and _element_value(element, "is_clickable") is True
            and _element_value(element, "is_enabled") is not False
            and inspection_match is not None
            and mutation_label is None
            and not role_matched
        )
        if (
            inspection_navigation
            and inspection_match is not None
            and bbox is not None
            and len(inspection_controls)
            < MAX_INSPECTION_CONTROL_CANDIDATES
        ):
            inspection_controls.append(
                {
                    # Route only the matched navigation affordance, never the
                    # full accessible label, which could contain task data.
                    "label": inspection_match.group(0),
                    "bbox": {
                        "x_min": round(float(bbox[0]), 6),
                        "x_max": round(float(bbox[1]), 6),
                        "y_min": round(float(bbox[2]), 6),
                        "y_max": round(float(bbox[3]), 6),
                    },
                    "center": {
                        "x": round(float(bbox[0] + bbox[1]) / 2.0, 6),
                        "y": round(float(bbox[2] + bbox[3]) / 2.0, 6),
                    },
                }
            )

    mutation_control_hits = []
    requested_field_control_hit = False
    visible_control_hit = False
    inspection_control_hit = False
    if isinstance(tap_x, (int, float)) and isinstance(tap_y, (int, float)):
        mutation_control_hits = [
            item["label"]
            for item in mutation_controls
            if (
                item["bbox"]["x_min"] <= float(tap_x)
                <= item["bbox"]["x_max"]
                and item["bbox"]["y_min"] <= float(tap_y)
                <= item["bbox"]["y_max"]
            )
        ]
        requested_field_control_hit = any(
            item["x_min"] <= float(tap_x) <= item["x_max"]
            and item["y_min"] <= float(tap_y) <= item["y_max"]
            for item in matched_bboxes
        )
        visible_control_hit = any(
            item["x_min"] <= float(tap_x) <= item["x_max"]
            and item["y_min"] <= float(tap_y) <= item["y_max"]
            for item in visible_control_bboxes
        )
        inspection_control_hit = any(
            item["bbox"]["x_min"] <= float(tap_x)
            <= item["bbox"]["x_max"]
            and item["bbox"]["y_min"] <= float(tap_y)
            <= item["bbox"]["y_max"]
            for item in inspection_controls
        )
    type_text_attempted = bool(
        isinstance(action, dict) and action.get("type") == "type_text"
    )
    return {
        "schema_version": "requested_field_value_assessment.v1",
        "requested_answer_role": requested_role,
        "role_tokens": sorted(singular_role_tokens),
        "explicit_value_control_count": len(matched_bboxes),
        "explicit_value_visible": bool(matched_bboxes),
        "matched_metadata_fields": sorted(matched_metadata_fields),
        "matched_value_bboxes": matched_bboxes,
        "mutation_control_hit": bool(mutation_control_hits),
        "mutation_control_hit_labels": mutation_control_hits,
        "requested_field_control_hit": requested_field_control_hit,
        "visible_control_hit": visible_control_hit,
        "visible_control_count": len(visible_control_bboxes),
        "inspection_control_hit": inspection_control_hit,
        "inspection_control_candidates": inspection_controls,
        "type_text_attempted": type_text_attempted,
        "read_only_inspection_safe": bool(
            matched_bboxes
            and not mutation_control_hits
            and not requested_field_control_hit
            and not type_text_attempted
        ),
    }


def _cluster_row_centers(
    centers: list[float],
    *,
    tolerance: float = 0.025,
) -> list[float]:
    clusters: list[list[float]] = []
    for center in sorted(centers):
        if not clusters or center - clusters[-1][-1] > tolerance:
            clusters.append([center])
        else:
            clusters[-1].append(center)
    return [round(sum(cluster) / len(cluster), 6) for cluster in clusters]


def dated_list_answer_assessment(
    goal: str,
    ui_elements: Any,
    decision: dict[str, Any] | None,
    *,
    screen_width: int,
    screen_height: int,
) -> dict[str, Any]:
    """Bind answer items and navigation to rows carrying the target date."""
    chronology = chronological_list_navigation_assessment(
        goal,
        ui_elements,
        screen_width=screen_width,
        screen_height=screen_height,
    )
    target_dates = {
        (item["year"], item["month"], item["day"])
        for item in chronology["target_dates"]
    }
    target_anchor_centers: list[float] = []
    target_anchor_positions: list[tuple[float, float]] = []
    for anchor in chronology["date_anchors"]:
        anchor_dates = {
            (item["year"], item["month"], item["day"])
            for item in anchor["dates"]
        }
        if any(
            _dates_match(target, visible)
            for target in target_dates
            for visible in anchor_dates
        ):
            target_anchor_centers.append(anchor["y_center"])
            target_anchor_positions.append(
                (anchor["x_center"], anchor["y_center"])
            )
    target_row_centers = _cluster_row_centers(target_anchor_centers)
    target_row_date_x_centers = [
        round(
            sum(
                x_center
                for x_center, y_center in target_anchor_positions
                if abs(y_center - row_center) <= 0.025
            )
            / max(
                1,
                sum(
                    1
                    for _, y_center in target_anchor_positions
                    if abs(y_center - row_center) <= 0.025
                ),
            ),
            6,
        )
        for row_center in target_row_centers
    ]

    label_records: list[dict[str, Any]] = []
    explicit_labels: list[str] = []
    for element in ui_elements or ():
        if _element_value(element, "is_visible") is False:
            continue
        bbox = _normalized_element_bbox(
            element,
            screen_width=screen_width,
            screen_height=screen_height,
        )
        labels = [
            label
            for field in (
                "text",
                "content_description",
                "hint_text",
                "tooltip",
            )
            if (
                label := _normalized_text(_element_value(element, field))
            )
            is not None
        ]
        explicit_labels.extend(labels)
        if bbox is None:
            continue
        y_center = round((bbox[2] + bbox[3]) / 2, 6)
        x_center = round((bbox[0] + bbox[1]) / 2, 6)
        for label in labels:
            label_records.append(
                {
                    "label": label,
                    "normalized": " ".join(label.casefold().split()),
                    "x_center": x_center,
                    "y_center": y_center,
                    "is_date_label": bool(
                        CHRONOLOGICAL_LABEL_RE.fullmatch(label.strip())
                    ),
                }
            )

    target_row_content_labels: list[list[str]] = []
    target_row_date_sides: list[str] = []
    for row_center, date_x_center in zip(
        target_row_centers,
        target_row_date_x_centers,
        strict=True,
    ):
        date_side = (
            "right"
            if date_x_center >= 0.65
            else "left"
            if date_x_center <= 0.35
            else "ambiguous"
        )
        target_row_date_sides.append(date_side)
        content_labels = sorted(
            {
                record["label"]
                for record in label_records
                if not record["is_date_label"]
                and abs(record["y_center"] - row_center) <= 0.055
                and (
                    (
                        date_side == "right"
                        and record["x_center"] < date_x_center - 0.03
                    )
                    or (
                        date_side == "left"
                        and record["x_center"] > date_x_center + 0.03
                    )
                )
            }
        )
        target_row_content_labels.append(content_labels)

    action = decision.get("action") if isinstance(decision, dict) else None
    action_type = action.get("type") if isinstance(action, dict) else None
    answer_text = (
        _normalized_text(action.get("text"))
        if isinstance(action, dict) and action_type == "answer"
        else None
    )
    answer_items = [
        item.strip()
        for item in (answer_text or "").split(",")
        if item.strip()
    ]
    item_bindings: list[dict[str, Any]] = []
    for item in answer_items:
        normalized_item = " ".join(item.casefold().split())
        matched = [
            record
            for record in label_records
            if record["normalized"] == normalized_item
        ]
        nearest_distance = (
            min(
                abs(record["y_center"] - target_center)
                for record in matched
                for target_center in target_row_centers
            )
            if matched and target_row_centers
            else None
        )
        item_bindings.append(
            {
                "item": item,
                "visible_match_count": len(matched),
                "visible_y_centers": sorted(
                    {record["y_center"] for record in matched}
                ),
                "nearest_target_row_distance": (
                    round(nearest_distance, 6)
                    if nearest_distance is not None
                    else None
                ),
                "target_row_bound": bool(
                    nearest_distance is not None
                    and nearest_distance <= 0.055
                ),
            }
        )

    requested_role = _requested_answer_role(goal)
    role_detail_required = bool(
        requested_role
        and DETAIL_REQUIRED_ANSWER_ROLE_RE.search(requested_role)
    )
    role_tokens = set(
        re.findall(r"[a-z]+", (requested_role or "").casefold())
    )
    singular_role_tokens = {
        {
            "categories": "category",
            "statuses": "status",
        }.get(token, token[:-1] if token.endswith("s") else token)
        for token in role_tokens
    }
    if singular_role_tokens.intersection({"type", "category", "kind"}):
        singular_role_tokens.update({"type", "category", "kind"})
    singular_role_tokens.difference_update(
        {"a", "an", "answer", "activity", "only", "the"}
    )
    role_label_hits = sorted(
        {
            label
            for label in explicit_labels
            if singular_role_tokens
            and any(
                re.search(
                    rf"\b{re.escape(token)}\b",
                    label,
                    flags=re.IGNORECASE,
                )
                for token in singular_role_tokens
            )
        }
    )
    field_role_explicitly_visible = bool(role_label_hits)

    tap_x = action.get("x") if isinstance(action, dict) else None
    tap_y = action.get("y") if isinstance(action, dict) else None
    target_row_tap_center: float | None = None
    target_row_tap_index: int | None = None
    if (
        action_type == "tap"
        and isinstance(tap_y, (int, float))
        and target_row_centers
    ):
        nearest_index = min(
            range(len(target_row_centers)),
            key=lambda index: abs(tap_y - target_row_centers[index]),
        )
        if abs(tap_y - target_row_centers[nearest_index]) <= 0.055:
            target_row_tap_index = nearest_index
            target_row_tap_center = target_row_centers[nearest_index]
    target_row_tap_date_side = (
        target_row_date_sides[target_row_tap_index]
        if target_row_tap_index is not None
        else None
    )
    target_row_tap_date_x_center = (
        target_row_date_x_centers[target_row_tap_index]
        if target_row_tap_index is not None
        else None
    )
    tap_on_content_side = bool(
        action_type == "tap"
        and isinstance(tap_x, (int, float))
        and isinstance(tap_y, (int, float))
        and 0.03 <= tap_x <= 0.97
        and target_row_tap_index is not None
        and target_row_tap_date_x_center is not None
        and (
            (
                target_row_tap_date_side == "right"
                and tap_x < target_row_tap_date_x_center - 0.03
            )
            or (
                target_row_tap_date_side == "left"
                and tap_x > target_row_tap_date_x_center + 0.03
            )
        )
    )
    row_aligned_tap = bool(
        target_row_tap_index is not None and tap_on_content_side
    )
    clickable_target_hit = False
    if row_aligned_tap:
        for element in ui_elements or ():
            if _element_value(element, "is_visible") is not True:
                continue
            if _element_value(element, "is_enabled") is not True:
                continue
            if _element_value(element, "is_clickable") is not True:
                continue
            if not _tap_hits_element(
                action,
                element,
                screen_width=screen_width,
                screen_height=screen_height,
            ):
                continue
            bbox = _normalized_element_bbox(
                element,
                screen_width=screen_width,
                screen_height=screen_height,
            )
            if bbox is not None and any(
                bbox[2] - 0.02 <= center <= bbox[3] + 0.02
                for center in target_row_centers
            ):
                clickable_target_hit = True
                break

    visible_content_target_hit = bool(
        row_aligned_tap
        and target_row_tap_index is not None
        and target_row_content_labels[target_row_tap_index]
    )
    target_row_tap_authority = (
        "accessibility_clickable"
        if clickable_target_hit
        else "visible_content_row_geometry"
        if visible_content_target_hit
        else None
    )

    target_date_list_visible = bool(
        chronology["chronological_history_detected"]
        and chronology["target_visible"]
        and target_row_centers
    )
    return {
        "schema_version": "dated_list_answer_assessment.v1",
        "action_type": action_type,
        "chronological_history_detected": chronology[
            "chronological_history_detected"
        ],
        "target_visible": chronology["target_visible"],
        "target_date_list_visible": target_date_list_visible,
        "target_row_centers": target_row_centers,
        "target_row_date_x_centers": target_row_date_x_centers,
        "target_row_date_sides": target_row_date_sides,
        "target_row_content_labels": target_row_content_labels,
        "target_row_count": len(target_row_centers),
        "requested_answer_role": requested_role,
        "role_detail_required": role_detail_required,
        "field_role_explicitly_visible": field_role_explicitly_visible,
        "role_label_hits": role_label_hits,
        "answer_items": answer_items,
        "answer_item_count": len(answer_items),
        "answer_item_count_matches_target_rows": bool(
            target_row_centers
            and len(answer_items) == len(target_row_centers)
        ),
        "item_bindings": item_bindings,
        "all_answer_items_target_row_bound": bool(
            item_bindings
            and all(item["target_row_bound"] for item in item_bindings)
        ),
        "requested_field_detail_required": bool(
            target_date_list_visible
            and role_detail_required
            and not field_role_explicitly_visible
        ),
        "row_aligned_tap": row_aligned_tap,
        "tap_on_content_side": tap_on_content_side,
        "clickable_target_hit": clickable_target_hit,
        "visible_content_target_hit": visible_content_target_hit,
        "target_row_tap_permitted": bool(
            target_date_list_visible
            and row_aligned_tap
            and (clickable_target_hit or visible_content_target_hit)
        ),
        "target_row_tap_authority": target_row_tap_authority,
        "target_row_tap_index": target_row_tap_index,
        "target_row_tap_center": target_row_tap_center,
        "chronological_list_navigation_assessment": chronology,
    }


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


def files_view_mode_toggle_action_assessment(
    ui_elements: Any,
    action: dict[str, Any] | None,
    *,
    screen_width: int,
    screen_height: int,
) -> dict[str, Any]:
    """Bind a tap to one unambiguous Android Files list/grid toggle."""
    action_type = (
        action.get("type") if isinstance(action, dict) else None
    )
    controls: dict[
        tuple[float, float, float, float],
        dict[str, Any],
    ] = {}
    for element in ui_elements or ():
        if (
            _normalized_text(_element_value(element, "package_name"))
            not in ANDROID_FILES_PACKAGES
            or _element_value(element, "is_visible") is not True
            or _element_value(element, "is_enabled") is not True
            or _element_value(element, "is_clickable") is not True
            or _element_value(element, "is_editable") is True
        ):
            continue
        bbox = _normalized_element_bbox(
            element,
            screen_width=screen_width,
            screen_height=screen_height,
        )
        if bbox is None:
            continue
        labels = {
            label
            for field in (
                "text",
                "content_description",
                "tooltip",
            )
            if (
                label := _normalized_text(
                    _element_value(element, field)
                )
            )
            is not None
        }
        resource_ids = {
            resource_id
            for field in ("resource_id", "resource_name")
            if (
                resource_id := _normalized_text(
                    _element_value(element, field)
                )
            )
            is not None
        }
        if not (
            any(FILES_VIEW_MODE_LABEL_RE.fullmatch(label) for label in labels)
            or any(
                FILES_VIEW_MODE_RESOURCE_RE.search(resource_id)
                for resource_id in resource_ids
            )
        ):
            continue
        record = controls.setdefault(
            bbox,
            {
                "labels": set(),
                "resource_ids": set(),
                "elements": [],
            },
        )
        record["labels"].update(labels)
        record["resource_ids"].update(resource_ids)
        record["elements"].append(element)

    ordered_controls = [
        {
            "bbox": list(bbox),
            "labels": sorted(record["labels"]),
            "resource_ids": sorted(record["resource_ids"]),
            "hit": bool(
                action_type == "tap"
                and any(
                    _tap_hits_element(
                        action,
                        element,
                        screen_width=screen_width,
                        screen_height=screen_height,
                    )
                    for element in record["elements"]
                )
            ),
        }
        for bbox, record in sorted(controls.items())
    ]
    hit_count = sum(control["hit"] for control in ordered_controls)
    return {
        "schema_version": "files_view_mode_toggle_assessment.v1",
        "adjudicable": bool(ui_elements),
        "action_type": action_type,
        "control_count": len(ordered_controls),
        "matched_labels": sorted(
            {
                label
                for control in ordered_controls
                for label in control["labels"]
            }
        ),
        "matched_resource_ids": sorted(
            {
                resource_id
                for control in ordered_controls
                for resource_id in control["resource_ids"]
            }
        ),
        "action_hit_count": hit_count,
        "unambiguous": len(ordered_controls) == 1,
        "permitted": bool(
            action_type == "tap"
            and len(ordered_controls) == 1
            and hit_count == 1
        ),
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
        self.toolbar_affordance_block_count = 0
        self.target_date_visible_swipe_block_count = 0
        self.answer_association_block_count = 0
        self.target_row_enumeration_block_count = 0
        self.target_row_tap_validation_count = 0
        self.target_row_revisit_block_count = 0
        self.target_row_aggregation_block_count = 0
        self.target_row_visual_answer_accept_count = 0
        self.target_row_explicit_field_block_count = 0
        self.target_row_read_only_mutation_block_count = 0
        self.target_row_off_list_coordinate_block_count = 0
        self.target_row_non_control_tap_block_count = 0
        self.target_date_row_count = 0
        self.target_row_detail_required = False
        self.target_row_visit_keys: list[str] = []
        self.active_target_row_visit_key: str | None = None
        self.target_row_detail_frames: list[dict[str, Any]] = []
        self.requested_answer_role: str | None = None
        self.target_date_row_observations: list[dict[str, Any]] = []
        self.last_unverified_progress_no_effect_fingerprint: (
            tuple[str, str] | None
        ) = None
        self.unverified_progress_repeat_block_count = 0
        self.input_activation_repair_pending = False
        self.input_activation_action_key: str | None = None
        self.input_activation_proof_count = 0
        self.input_activation_proof_consumed_count = 0
        self.post_activation_clear_text_block_count = 0
        self.input_activation_repeat_override_count = 0
        self.visible_control_activation_repeat_override_fingerprints: set[
            tuple[str, str]
        ] = set()
        self.visible_control_activation_repeat_override_records: list[
            dict[str, Any]
        ] = []
        self.bounded_task_repeated_tap_override_count = 0
        self.bounded_task_repeated_tap_override_records: list[
            dict[str, Any]
        ] = []
        self.deferred_semantic_progress_reconciliation_count = 0
        self.deferred_semantic_progress_reconciliation_records: list[
            dict[str, Any]
        ] = []
        self._verified_task_repeat_progress: dict[str, Any] | None = None
        self.verified_task_repeat_observation_records: list[
            dict[str, Any]
        ] = []
        self.task_repeat_count_complete_block_count = 0

    def target_row_progress_record(self) -> dict[str, Any] | None:
        """Expose only controller-observed dated-row progress, never answers."""
        if self.target_date_row_count <= 0:
            return None
        latest_centers = (
            list(
                self.target_date_row_observations[-1].get(
                    "target_row_centers",
                    [],
                )
            )
            if self.target_date_row_observations
            else []
        )
        keyed_centers = [
            {
                "visit_key": f"target-row-y:{float(center):.3f}",
                "y_center": float(center),
            }
            for center in latest_centers
        ]
        visited = set(self.target_row_visit_keys)
        return {
            "schema_version": "dated_target_row_progress.v1",
            "target_row_count": self.target_date_row_count,
            "requested_answer_role": self.requested_answer_role,
            "detail_required": self.target_row_detail_required,
            "visited_row_keys": list(self.target_row_visit_keys),
            "active_detail_row_key": self.active_target_row_visit_key,
            "unvisited_rows": [
                item for item in keyed_centers
                if item["visit_key"] not in visited
            ],
            "captured_detail_frame_keys": [
                frame["visit_key"]
                for frame in sorted(
                    self.target_row_detail_frames,
                    key=lambda item: str(item["visit_key"]),
                )
            ],
            "all_rows_visited": bool(
                self.target_date_row_count > 0
                and len(visited) >= self.target_date_row_count
            ),
            "all_detail_frames_captured": bool(
                self.target_date_row_count > 0
                and len(self.target_row_detail_frames)
                >= self.target_date_row_count
            ),
        }

    def target_row_detail_context_images(self) -> list[tuple[str, str]]:
        """Return verified requested-field crops in target-row order."""
        context_images: list[tuple[str, str]] = []
        for frame in sorted(
            self.target_row_detail_frames,
            key=lambda item: str(item["visit_key"]),
        ):
            path = Path(str(frame["path"]))
            if not path.is_file():
                raise RuntimeError(
                    "Controller-bound target-row detail frame is missing: "
                    + str(path)
                )
            actual_sha256 = sha256(path.read_bytes()).hexdigest()
            if actual_sha256 != frame["sha256"]:
                raise RuntimeError(
                    "Controller-bound target-row detail frame hash mismatch: "
                    + str(path)
                )
            source_path = Path(str(frame["source_path"]))
            if not source_path.is_file():
                raise RuntimeError(
                    "Controller-bound target-row source frame is missing: "
                    + str(source_path)
                )
            source_sha256 = sha256(source_path.read_bytes()).hexdigest()
            if source_sha256 != frame["source_sha256"]:
                raise RuntimeError(
                    "Controller-bound target-row source frame hash mismatch: "
                    + str(source_path)
                )
            if frame.get("requested_field_evidence_explicit") is not True:
                raise RuntimeError(
                    "Controller-bound target-row crop lacks explicit "
                    "requested-field evidence."
                )
            context_images.append(
                (
                    f"DATED_TARGET_REQUESTED_FIELD {frame['visit_key']}",
                    str(path),
                )
            )
        return context_images

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

    def repeated_tap_transition_context(
        self,
        *,
        page_sha256: str,
        action: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Describe delayed semantic convergence without mutating the guard."""
        action_key = (
            canonical_action_key(action)
            if isinstance(action, dict)
            else None
        )
        last_transition = (
            self.transition_fingerprints[-1]
            if self.transition_fingerprints
            else None
        )
        last_before = (
            last_transition[0] if last_transition is not None else None
        )
        last_action_key = (
            last_transition[1] if last_transition is not None else None
        )
        last_after = (
            last_transition[2] if last_transition is not None else None
        )
        return {
            "schema_version": "repeated_tap_transition_context.v1",
            "proposed_action_matches_last_coordinate": bool(
                action_key is not None
                and action_key == self.last_coordinate_action_key
            ),
            "last_transition_action_matches": bool(
                action_key is not None
                and action_key == last_action_key
            ),
            "last_transition_semantic_no_effect": bool(
                last_transition is not None
                and last_before == last_after
            ),
            "current_semantic_differs_from_last_recorded_after": bool(
                last_after is not None and page_sha256 != last_after
            ),
            "last_transition_fingerprint_blocked": bool(
                last_before is not None
                and last_action_key is not None
                and (last_before, last_action_key)
                in self.blocked_fingerprints
            ),
            "last_before_semantic_sha256": last_before,
            "last_after_semantic_sha256": last_after,
            "current_semantic_sha256": page_sha256,
        }

    @staticmethod
    def _deterministic_repeat_calculation(
        *,
        goal: str,
        operands: list[str],
        requested_repetitions: int,
    ) -> dict[str, Any] | None:
        if (
            len(operands) != requested_repetitions
            or not re.search(r"\bproduct\b", goal or "", re.IGNORECASE)
        ):
            return None
        try:
            product = Decimal(1)
            for operand in operands:
                product *= Decimal(operand)
        except InvalidOperation:
            return None
        result = format(product, "f")
        if "." in result:
            result = result.rstrip("0").rstrip(".")
        return {
            "operation": "product",
            "operands": list(operands),
            "result": result,
            "text_origin": "deterministic_calculation",
        }

    def refresh_verified_task_repeat_progress(
        self,
        *,
        goal: str,
        ui_elements: Any,
        page_sha256: str,
    ) -> dict[str, Any] | None:
        """Recompute joint action/operand completion without inventing data."""
        progress = self._verified_task_repeat_progress
        if progress is None:
            return None
        del ui_elements, page_sha256
        records = sorted(
            progress["operand_records"],
            key=lambda record: record["result_ordinal"],
        )
        progress["verified_operands"] = [
            record["value"] for record in records
        ]
        progress["complete"] = bool(
            progress["executed_count"]
            == progress["requested_repetitions"]
        )
        progress["operands_complete"] = bool(
            [record["result_ordinal"] for record in records]
            == list(
                range(1, progress["requested_repetitions"] + 1)
            )
        )
        progress["deterministic_calculation"] = (
            self._deterministic_repeat_calculation(
                goal=goal,
                operands=progress["verified_operands"],
                requested_repetitions=progress[
                    "requested_repetitions"
                ],
            )
        )
        progress["ready_for_post_repeat"] = bool(
            progress["complete"]
            and progress["operands_complete"]
            and progress["deterministic_calculation"] is not None
        )
        return self.verified_task_repeat_progress_record()

    def verified_task_repeat_progress_record(
        self,
    ) -> dict[str, Any] | None:
        progress = self._verified_task_repeat_progress
        if progress is None:
            return None
        return json.loads(json.dumps(progress))

    def _record_executed_task_repeat(
        self,
        *,
        before_sha256: str,
        action: dict[str, Any],
        after_sha256: str,
        assessment: dict[str, Any] | None,
    ) -> None:
        value = assessment or {}
        requested = value.get("requested_repetitions")
        ordinal = value.get("proposed_ordinal")
        if (
            action.get("type") != "tap"
            or value.get("task_target_bound") is not True
            or not isinstance(requested, int)
            or not isinstance(ordinal, int)
            or not 1 <= ordinal <= requested
        ):
            return
        action_key = canonical_action_key(action)
        progress = self._verified_task_repeat_progress
        if progress is None:
            if (
                ordinal != 1
                or value.get("pre_action_numeric_operand_bound") is not True
            ):
                return
            progress = {
                "schema_version": "verified_task_repeat_progress.v2",
                "authority": (
                    "executed_target_action_and_pre_action_semantic_ui"
                ),
                "operand_sampling": "pre_action_at_executed_target",
                "action": action,
                "action_key": action_key,
                "requested_repetitions": requested,
                "executed_count": 0,
                "complete": False,
                "matched_labels": list(
                    value.get("matched_labels") or []
                ),
                "matched_packages": list(
                    value.get("matched_packages") or []
                ),
                "numeric_result_collection_bound": bool(
                    value.get("numeric_result_collection_bound")
                ),
                "verified_operands": [],
                "operand_records": [],
                "operands_complete": False,
                "deterministic_calculation": None,
                "ready_for_post_repeat": False,
                "last_before_semantic_sha256": None,
                "last_after_semantic_sha256": None,
            }
            self._verified_task_repeat_progress = progress
        if (
            progress["action_key"] != action_key
            or progress["requested_repetitions"] != requested
            or ordinal != progress["executed_count"] + 1
        ):
            return
        progress["executed_count"] = ordinal
        progress["complete"] = ordinal == requested
        progress["last_before_semantic_sha256"] = before_sha256
        progress["last_after_semantic_sha256"] = after_sha256
        candidate = value.get("unique_visible_numeric_result")
        recorded_ordinals = {
            record["result_ordinal"]
            for record in progress["operand_records"]
        }
        if (
            progress["numeric_result_collection_bound"]
            and value.get("pre_action_numeric_operand_bound") is True
            and isinstance(candidate, str)
            and ordinal not in recorded_ordinals
        ):
            numeric_assessment = {
                "schema_version": (
                    "visible_numeric_repeat_result_assessment.v1"
                ),
                "collection_bound": True,
                "allowed_packages": list(
                    value.get("matched_packages") or []
                ),
                "visible_numeric_result_candidates": list(
                    value.get("visible_numeric_result_candidates") or []
                ),
                "unique_visible_numeric_result": candidate,
            }
            record = {
                "result_ordinal": ordinal,
                "click_ordinal": ordinal,
                "value": candidate,
                "evidence_phase": "pre_action_at_executed_target",
                "semantic_state_sha256": before_sha256,
                "assessment": numeric_assessment,
            }
            progress["operand_records"].append(record)
            progress["verified_operands"] = [
                item["value"]
                for item in sorted(
                    progress["operand_records"],
                    key=lambda item: item["result_ordinal"],
                )
            ]
            self.verified_task_repeat_observation_records.append(record)
        recorded_ordinals = sorted(
            record["result_ordinal"]
            for record in progress["operand_records"]
        )
        progress["operands_complete"] = bool(
            recorded_ordinals == list(range(1, requested + 1))
        )
        progress["ready_for_post_repeat"] = bool(
            progress["complete"]
            and progress["operands_complete"]
            and progress["deterministic_calculation"] is not None
        )

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

    def validate_active_target_detail_control(
        self,
        decision: dict[str, Any],
        *,
        page_sha256: str,
        dated_list_answer_assessment: dict[str, Any] | None = None,
        requested_field_value_assessment: dict[str, Any] | None = None,
    ) -> None:
        """Reject detail exploration that is not bound to a visible control."""
        action = decision.get("action")
        dated_assessment = dated_list_answer_assessment or {}
        field_assessment = requested_field_value_assessment or {}
        if not (
            self.target_row_detail_required
            and self.active_target_row_visit_key is not None
            and isinstance(action, dict)
            and action.get("type") == "tap"
            and field_assessment.get("explicit_value_visible") is not True
            and field_assessment.get("inspection_control_hit") is not True
            and dated_assessment.get("target_date_list_visible") is not True
        ):
            return
        row_centers = (
            self.target_date_row_observations[-1].get(
                "target_row_centers",
                [],
            )
            if self.target_date_row_observations
            else []
        )
        y = action.get("y")
        row_coordinate_used = bool(
            isinstance(y, (int, float))
            and any(
                abs(float(y) - float(center)) <= 0.035
                for center in row_centers
            )
        )
        reason = (
            "target_row_coordinate_used_off_list"
            if row_coordinate_used
            else "target_row_detail_non_control_tap"
        )
        self.validation_blocks.append(
            {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": reason,
                "requested_field_value_assessment": field_assessment,
                "required_recovery_classes": [
                    "inspect_visible_non_commit_detail_control",
                ],
            }
        )
        if row_coordinate_used:
            self.target_row_off_list_coordinate_block_count += 1
            raise ActionValidationError(
                "TARGET_ROW_LEDGER_SCOPE_GUARD: target-date row "
                "coordinates are valid only while the target-date list is "
                "currently visible. An active detail is open, so do not tap "
                "a deferred or visited row y-center on this screen. Use one "
                "visible enabled non-commit information, overflow-menu, or "
                "edit-details control to expose the exact existing "
                "requested-field text. Do not press Back, answer, type, "
                "change a selector, or Save before that text is visible."
            )
        self.target_row_non_control_tap_block_count += 1
        candidates = field_assessment.get(
            "inspection_control_candidates",
            [],
        )
        candidate_directive = (
            " VERIFIED_INSPECTION_CONTROL_CANDIDATES: "
            + json.dumps(
                candidates,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + ". Tap the exact normalized center of one listed candidate."
            if candidates
            else " No verified inspection control is currently available."
        )
        raise ActionValidationError(
            "TARGET_ROW_DETAIL_CONTROL_GUARD: an active target-row detail "
            "requires exact requested-field text, but this tap does not hit "
            "a controller-verified inspection control. Do not explore blank "
            "content or guess a coordinate. Tap one visible enabled "
            "non-commit information, overflow-menu, or edit-details "
            "control. Do not "
            "press Back, answer, type, change a selector, or Save before "
            "the exact existing requested-field text is visible."
            + candidate_directive
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
        bounded_task_repeated_tap_assessment: (
            dict[str, Any] | None
        ) = None,
        toolbar_affordance_claim_assessment: (
            dict[str, Any] | None
        ) = None,
        dated_list_answer_assessment: dict[str, Any] | None = None,
        dated_visual_answer_assessment: dict[str, Any] | None = None,
        dated_row_detail_frame: dict[str, Any] | None = None,
        requested_field_value_assessment: dict[str, Any] | None = None,
    ) -> None:
        action = decision.get("action")
        if not isinstance(action, dict):
            return
        action_key = canonical_action_key(action)
        pending_target_visit_key: str | None = None
        pending_target_detail_frame: dict[str, Any] | None = None
        pending_visual_answer_accept = False
        field_value_assessment = requested_field_value_assessment or {}
        toolbar_assessment = toolbar_affordance_claim_assessment or {}
        if (
            toolbar_assessment.get("adjudicable") is True
            and toolbar_assessment.get("matched") is False
        ):
            chronology = toolbar_assessment.get(
                "chronological_list_navigation_assessment"
            ) or {}
            scroll_required = chronology.get(
                "scroll_toward_older_required"
            ) is True
            required_recovery_classes = [
                "inspect_different_visible_control",
            ]
            if scroll_required:
                required_recovery_classes.insert(
                    0,
                    "scroll_chronological_content_toward_older",
                )
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": "toolbar_affordance_claim_mismatch",
                "toolbar_affordance_claim_assessment": toolbar_assessment,
                "required_recovery_classes": required_recovery_classes,
            }
            self.validation_blocks.append(record)
            self.toolbar_affordance_block_count += 1
            expected_roles = ", ".join(
                toolbar_assessment.get("expected_roles") or []
            )
            target_roles = ", ".join(
                toolbar_assessment.get("target_roles") or []
            )
            chronology_directive = (
                " CHRONOLOGICAL_LIST_SCROLL_REQUIRED: the task contains an "
                "explicit date, the current screen exposes date headings "
                "as a vertically arranged chronological history, and the "
                "target date is not visible. Swipe upward inside the content "
                "list to reveal older entries; do not tap a toolbar control, "
                "open text search, type the date, wait, or answer in this "
                "bounded repair."
                if scroll_required
                else ""
            )
            raise ActionValidationError(
                "TOOLBAR_AFFORDANCE_GUARD: the proposed top-app-bar tap "
                f"claims an expected role ({expected_roles}) but hits a "
                f"visible control with a conflicting role ({target_roles}). "
                "Do not treat one named toolbar affordance as a different "
                "kind of control."
                + chronology_directive
            )
        dated_assessment = dated_list_answer_assessment or {}
        self.validate_active_target_detail_control(
            decision,
            page_sha256=page_sha256,
            dated_list_answer_assessment=dated_assessment,
            requested_field_value_assessment=field_value_assessment,
        )
        if dated_assessment.get("target_date_list_visible") is True:
            observed_row_count = int(
                dated_assessment.get("target_row_count") or 0
            )
            self.target_date_row_count = max(
                self.target_date_row_count,
                observed_row_count,
            )
            self.target_row_detail_required = bool(
                self.target_row_detail_required
                or dated_assessment.get("requested_field_detail_required")
                is True
            )
            requested_role = dated_assessment.get("requested_answer_role")
            if isinstance(requested_role, str):
                self.requested_answer_role = requested_role
            observation = {
                "semantic_state_sha256": page_sha256,
                "target_row_count": observed_row_count,
                "target_row_centers": list(
                    dated_assessment.get("target_row_centers") or []
                ),
                "requested_answer_role": requested_role,
            }
            if observation not in self.target_date_row_observations:
                self.target_date_row_observations.append(observation)
            if action.get("type") == "swipe":
                record = {
                    "semantic_state_sha256": page_sha256,
                    "action": action,
                    "reason": "target_date_visible_swipe_blocked",
                    "dated_list_answer_assessment": dated_assessment,
                    "required_recovery_classes": [
                        "open_visible_target_date_row",
                    ],
                }
                self.validation_blocks.append(record)
                self.target_date_visible_swipe_block_count += 1
                raise ActionValidationError(
                    "TARGET_DATE_VISIBLE_GUARD: the explicit task date is "
                    "already visible in this chronological list. Another "
                    "swipe can move target rows out of view and cannot reveal "
                    "the requested row field. TARGET_DATE_ROW_TAP_REQUIRED: "
                    "tap one visible enabled content row horizontally aligned "
                    "with the target date. Do not swipe, tap a toolbar icon, "
                    "wait, answer, or infer a row field from its title."
                )
            if action.get("type") == "answer":
                wrong_row_items = [
                    item["item"]
                    for item in dated_assessment.get("item_bindings") or []
                    if item.get("target_row_bound") is not True
                ]
                count_matches = dated_assessment.get(
                    "answer_item_count_matches_target_rows"
                ) is True
                detail_required = dated_assessment.get(
                    "requested_field_detail_required"
                ) is True
                visited_row_count = len(self.target_row_visit_keys)
                captured_frame_count = len(self.target_row_detail_frames)
                visual_answer = dated_visual_answer_assessment or {}
                visual_detail_bound = bool(
                    detail_required
                    and visual_answer.get("accepted") is True
                    and visited_row_count >= observed_row_count
                    and captured_frame_count >= observed_row_count
                )
                if (
                    not count_matches
                    or (
                        detail_required
                        and not visual_detail_bound
                    )
                    or (
                        not detail_required
                        and wrong_row_items
                    )
                ):
                    current_centers = list(
                        dated_assessment.get("target_row_centers") or []
                    )
                    unvisited = [
                        round(float(center), 6)
                        for center in current_centers
                        if (
                            f"target-row-y:{float(center):.3f}"
                            not in self.target_row_visit_keys
                        )
                    ]
                    record = {
                        "semantic_state_sha256": page_sha256,
                        "action": action,
                        "reason": "dated_list_answer_association_blocked",
                        "dated_list_answer_assessment": dated_assessment,
                        "dated_visual_answer_assessment": visual_answer,
                        "visited_row_count": visited_row_count,
                        "captured_detail_frame_count": (
                            captured_frame_count
                        ),
                        "unvisited_target_row_centers": unvisited,
                        "required_recovery_classes": [
                            "open_visible_target_date_row",
                            "inspect_requested_field_in_detail",
                        ],
                    }
                    self.validation_blocks.append(record)
                    self.answer_association_block_count += 1
                    rendered_wrong = json.dumps(
                        wrong_row_items,
                        ensure_ascii=False,
                    )
                    remaining_directive = (
                        " TARGET_DATE_UNVISITED_ROW_TAP_REQUIRED: tap one "
                        "unvisited visible target-date content row. Allowed "
                        "unvisited normalized y-centers: "
                        + json.dumps(unvisited)
                        + "."
                        if unvisited and visited_row_count > 0
                        else
                        (
                            " TARGET_DATE_ROW_TAP_REQUIRED: tap one visible "
                            "enabled target-date content row and inspect its "
                            "details."
                            if unvisited
                            else
                            " TARGET_ROW_VISUAL_ANSWER_REQUIRED: all target "
                            "rows were opened, but the answer still requires "
                            "a same-turn visual critic to bind every requested "
                            "field value to its row's current icon or explicit "
                            "field evidence. Do not substitute row titles."
                        )
                    )
                    raise ActionValidationError(
                        "ANSWER_ASSOCIATION_GUARD: terminal answer items must "
                        "each belong to a visible row carrying the explicit "
                        "task date, and the number of items must match the "
                        "visible target-date rows. Items not bound to a target "
                        f"row: {rendered_wrong}. The requested answer field "
                        f"is {self.requested_answer_role!r}; a visible row "
                        "title or name is not evidence for a different field. "
                        "Do not answer, swipe, wait, or use a non-target row."
                        + remaining_directive
                    )
                pending_visual_answer_accept = detail_required
            if dated_assessment.get("target_row_tap_permitted") is True:
                tap_center = dated_assessment.get("target_row_tap_center")
                if isinstance(tap_center, (int, float)):
                    visit_key = f"target-row-y:{float(tap_center):.3f}"
                    current_centers = list(
                        dated_assessment.get("target_row_centers") or []
                    )
                    unvisited = [
                        round(float(center), 6)
                        for center in current_centers
                        if (
                            f"target-row-y:{float(center):.3f}"
                            not in self.target_row_visit_keys
                        )
                    ]
                    if visit_key in self.target_row_visit_keys:
                        record = {
                            "semantic_state_sha256": page_sha256,
                            "action": action,
                            "reason": "visited_target_row_reopen_blocked",
                            "visited_row_keys": list(
                                self.target_row_visit_keys
                            ),
                            "unvisited_target_row_centers": unvisited,
                            "required_recovery_classes": [
                                "inspect_remaining_target_date_row",
                            ],
                        }
                        self.validation_blocks.append(record)
                        self.target_row_revisit_block_count += 1
                        raise ActionValidationError(
                            "TARGET_ROW_UNVISITED_GUARD: this target-date "
                            f"row ({visit_key}) was already opened. "
                            "TARGET_DATE_UNVISITED_ROW_TAP_REQUIRED: choose "
                            "one unvisited target-date content row. Allowed "
                            "unvisited normalized y-centers: "
                            + json.dumps(unvisited)
                            + ". Do not reopen a visited row or perturb its "
                            "coordinate."
                        )
                    pending_target_visit_key = visit_key
        elif (
            self.target_row_detail_required
            and self.active_target_row_visit_key is not None
            and (
                action.get("type") == "type_text"
                or field_value_assessment.get("mutation_control_hit")
                is True
                or field_value_assessment.get(
                    "requested_field_control_hit"
                )
                is True
            )
        ):
            self.validation_blocks.append(
                {
                    "semantic_state_sha256": page_sha256,
                    "action": action,
                    "reason": "target_row_read_only_inspection_mutation_blocked",
                    "requested_field_value_assessment": (
                        field_value_assessment
                    ),
                    "required_recovery_classes": [
                        "navigate_back_without_saving",
                    ],
                }
            )
            self.target_row_read_only_mutation_block_count += 1
            raise ActionValidationError(
                "TARGET_ROW_READ_ONLY_GUARD: this screen is being used only "
                "to inspect the existing requested-field value. Do not "
                "type, change a selector, Save, Submit, Apply, Confirm, "
                "Delete, Send, or Record. Preserve the current value and "
                "press Back without committing after it is visibly read."
            )
        elif (
            self.target_row_detail_required
            and self.active_target_row_visit_key is not None
            and action.get("type") in {"answer", "press_back"}
            and field_value_assessment.get("explicit_value_visible")
            is not True
        ):
            self.validation_blocks.append(
                {
                    "semantic_state_sha256": page_sha256,
                    "action": action,
                    "reason": "target_row_explicit_requested_field_missing",
                    "requested_field_value_assessment": (
                        field_value_assessment
                    ),
                    "required_recovery_classes": [
                        "inspect_non_commit_detail_metadata",
                    ],
                }
            )
            self.target_row_explicit_field_block_count += 1
            raise ActionValidationError(
                "TARGET_ROW_EXPLICIT_FIELD_GUARD: the current target-row "
                f"screen does not show an explicit readable value for "
                f"{self.requested_answer_role!r} in a control whose visible "
                "field metadata matches that role. Do not infer it from an "
                "icon or title and do not go Back yet. Inspect a visible "
                "non-commit information or edit-details path until the "
                "existing value is explicit. Treat any edit form as "
                "read-only: never type, change a selector, or Save."
            )
        elif (
            action.get("type") == "answer"
            and self.target_row_detail_required
            and self.target_date_row_count > 0
        ):
            answer_item_count = int(
                dated_assessment.get("answer_item_count") or 0
            )
            visited_row_count = len(self.target_row_visit_keys)
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": "target_row_answer_requires_list_aggregation",
                "dated_list_answer_assessment": dated_assessment,
                "visited_row_count": visited_row_count,
                "answer_item_count": answer_item_count,
                "required_recovery_classes": [
                    "navigate_back",
                    "inspect_remaining_target_date_row",
                    "aggregate_on_target_date_list",
                ],
            }
            self.validation_blocks.append(record)
            self.target_row_enumeration_block_count += 1
            self.target_row_aggregation_block_count += 1
            raise ActionValidationError(
                "TARGET_ROW_ENUMERATION_GUARD: the earlier target-date list "
                f"exposed {self.target_date_row_count} distinct rows, "
                f"{visited_row_count} distinct target rows were opened, and "
                f"this detail-page answer contains {answer_item_count} "
                "item(s). A single detail page cannot visually bind the "
                "complete multi-row answer. "
                "TARGET_ROW_AGGREGATION_BACK_REQUIRED: press Back once, "
                "inspect every remaining unvisited target row, and submit "
                "the complete answer only from the target-date list after "
                "all detail frames are controller-bound."
            )
        elif (
            action.get("type") == "press_back"
            and self.target_row_detail_required
            and self.active_target_row_visit_key is not None
        ):
            frame = dated_row_detail_frame or {}
            if (
                frame.get("visit_key") == self.active_target_row_visit_key
                and isinstance(frame.get("path"), str)
                and isinstance(frame.get("sha256"), str)
                and len(frame["sha256"]) == 64
                and isinstance(frame.get("source_path"), str)
                and isinstance(frame.get("source_sha256"), str)
                and len(frame["source_sha256"]) == 64
                and frame.get("requested_field_evidence_explicit") is True
            ):
                pending_target_detail_frame = dict(frame)
        self._validate_text_provenance(
            decision,
            page_sha256=page_sha256,
            declared_source_assessment=declared_text_source_assessment,
            declared_source_soft_keyboard_present=(
                declared_source_soft_keyboard_present
            ),
        )
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
        if (
            self.input_activation_repair_pending
            and action.get("type") == "type_text"
            and action.get("clear_text") is True
            and focused_assessment.get("present") is not True
        ):
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": "post_activation_clear_text_focus_unconfirmed",
                "focused_input_assessment": focused_assessment,
                "coordinate_text_target_assessment": (
                    text_target_assessment
                ),
                "required_recovery_classes": [
                    "preserve_activated_input_without_clear",
                ],
            }
            self.validation_blocks.append(record)
            self.post_activation_clear_text_block_count += 1
            raise ActionValidationError(
                "POST_ACTIVATION_CLEAR_TEXT_GUARD: the immediately "
                "preceding bounded repair executed an input-activation tap, "
                "but current accessibility does not expose an actually "
                "focused editable node. A visible soft keyboard alone does "
                "not prove that Ctrl+A will reach the input; it can select "
                "the surrounding UI. Keep the exact same task-bound text "
                "and provenance, omit x and y, and set clear_text=false."
            )
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
        task_repeat = bounded_task_repeated_tap_assessment or {}
        transition_context = self.repeated_tap_transition_context(
            page_sha256=page_sha256,
            action=action,
        )
        repeat_assessment_matches_raw_state = bool(
            task_repeat.get(
                "prior_identical_coordinate_action_count"
            )
            == self.identical_coordinate_action_count
            and task_repeat.get(
                "identical_coordinate_no_effect_count"
            )
            == self.identical_coordinate_no_effect_count
        )
        deferred_semantic_progress = bool(
            action.get("type") == "tap"
            and task_repeat.get("permitted") is True
            and task_repeat.get("task_target_bound") is True
            and task_repeat.get(
                "deferred_semantic_progress_observed"
            )
            is True
            and repeat_assessment_matches_raw_state
            and task_repeat.get(
                "effective_identical_coordinate_no_effect_count"
            )
            == self.identical_coordinate_no_effect_count - 1
            and transition_context[
                "proposed_action_matches_last_coordinate"
            ]
            is True
            and transition_context["last_transition_action_matches"]
            is True
            and transition_context[
                "last_transition_semantic_no_effect"
            ]
            is True
            and transition_context[
                "current_semantic_differs_from_last_recorded_after"
            ]
            is True
            and transition_context[
                "last_transition_fingerprint_blocked"
            ]
            is False
        )
        if deferred_semantic_progress:
            last_fingerprint = (
                transition_context["last_before_semantic_sha256"],
                action_key,
            )
            self.identical_coordinate_no_effect_count -= 1
            if self.no_effect_counts.get(last_fingerprint, 0) > 1:
                self.no_effect_counts[last_fingerprint] -= 1
            else:
                self.no_effect_counts.pop(last_fingerprint, None)
            if (
                self.last_unverified_progress_no_effect_fingerprint
                == last_fingerprint
            ):
                self.last_unverified_progress_no_effect_fingerprint = None
            self.deferred_semantic_progress_reconciliation_count += 1
            self.deferred_semantic_progress_reconciliation_records.append(
                {
                    "action": action,
                    "assessment": task_repeat,
                    "transition_context": transition_context,
                }
            )
        verified_repeat_progress = self._verified_task_repeat_progress
        task_repeat_count_complete = bool(
            action.get("type") == "tap"
            and verified_repeat_progress is not None
            and verified_repeat_progress.get("complete") is True
            and verified_repeat_progress.get("action_key") == action_key
            and task_repeat.get("requested_repetitions")
            == verified_repeat_progress.get("requested_repetitions")
            and task_repeat.get("proposed_ordinal", 0)
            > verified_repeat_progress.get(
                "requested_repetitions",
                0,
            )
        )
        if task_repeat_count_complete:
            progress_record = (
                self.verified_task_repeat_progress_record()
            )
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": "verified_task_repeat_count_complete",
                "verified_task_repeat_progress": progress_record,
                "required_recovery_classes": [
                    "perform_post_repeat_subtask",
                    "use_verified_deterministic_calculation",
                    "fail_safely_if_verified_operands_incomplete",
                ],
            }
            self.validation_blocks.append(record)
            self.task_repeat_count_complete_block_count += 1
            raise ActionValidationError(
                "TASK_REPEAT_COUNT_COMPLETE: the task-bound action has "
                "already executed the exact requested count. Another repeat "
                "is forbidden. Treat VERIFIED_TASK_REPEAT_PROGRESS as newer "
                "than conflicting summary memory and perform the pending "
                "post-repeat subtask. Verified ledger: "
                + json.dumps(
                    progress_record,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
        bounded_task_repeat = bool(
            action.get("type") == "tap"
            and task_repeat.get("permitted") is True
            and task_repeat.get(
                "prior_identical_coordinate_action_count"
            )
            == self.identical_coordinate_action_count
            and task_repeat.get("proposed_ordinal")
            == self.identical_coordinate_action_count + 1
            and task_repeat.get(
                "effective_identical_coordinate_no_effect_count"
            )
            == self.identical_coordinate_no_effect_count
        )
        coordinate_streak_at_limit = bool(
            action.get("type") in COORDINATE_STREAK_ACTIONS
            and action_key == self.last_coordinate_action_key
            and self.identical_coordinate_action_count
            >= self.max_identical_coordinate_actions
            and (
                action.get("type") != "swipe"
                or self.identical_coordinate_no_effect_count > 0
            )
        )
        if coordinate_streak_at_limit and bounded_task_repeat:
            self.bounded_task_repeated_tap_override_count += 1
            self.bounded_task_repeated_tap_override_records.append(
                {
                    "semantic_state_sha256": page_sha256,
                    "action": action,
                    "assessment": task_repeat,
                }
            )
        elif coordinate_streak_at_limit:
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
        if pending_target_visit_key is not None:
            self.target_row_tap_validation_count += 1
            self.target_row_visit_keys.append(pending_target_visit_key)
            self.active_target_row_visit_key = pending_target_visit_key
        if pending_target_detail_frame is not None:
            self.target_row_detail_frames = [
                frame for frame in self.target_row_detail_frames
                if frame.get("visit_key")
                != pending_target_detail_frame["visit_key"]
            ]
            self.target_row_detail_frames.append(
                pending_target_detail_frame
            )
            self.active_target_row_visit_key = None
        if pending_visual_answer_accept:
            self.target_row_visual_answer_accept_count += 1

    def reconcile_late_semantic_transition(
        self,
        *,
        completed_step: int,
        previous_after_sha256: str,
        current_before_sha256: str,
    ) -> dict[str, Any]:
        """Correct only the latest no-effect record when progress lands late."""
        if (
            not self.transition_fingerprints
            or not previous_after_sha256
            or not current_before_sha256
            or previous_after_sha256 == current_before_sha256
        ):
            return {
                "reconciled": False,
                "completed_step": completed_step,
            }
        before_sha256, action_key, recorded_after = (
            self.transition_fingerprints[-1]
        )
        if recorded_after != previous_after_sha256:
            return {
                "reconciled": False,
                "completed_step": completed_step,
                "reason": "latest_transition_does_not_match_previous_after",
            }
        fingerprint = (before_sha256, action_key)
        recorded_no_effect = before_sha256 == recorded_after
        if recorded_no_effect:
            if self.no_effect_counts.get(fingerprint, 0) > 1:
                self.no_effect_counts[fingerprint] -= 1
            else:
                self.no_effect_counts.pop(fingerprint, None)
            if (
                self.last_unverified_progress_no_effect_fingerprint
                == fingerprint
            ):
                self.last_unverified_progress_no_effect_fingerprint = None
            if (
                action_key == self.last_coordinate_action_key
                and self.identical_coordinate_no_effect_count > 0
            ):
                self.identical_coordinate_no_effect_count -= 1
        self.transition_fingerprints[-1] = (
            before_sha256,
            action_key,
            current_before_sha256,
        )
        record = {
            "source": "inter_step_readiness_reconciliation",
            "completed_step": completed_step,
            "before_semantic_sha256": before_sha256,
            "recorded_after_semantic_sha256": recorded_after,
            "current_before_semantic_sha256": current_before_sha256,
            "action_key": action_key,
            "recorded_no_effect": recorded_no_effect,
            "blocked_fingerprint_preserved": (
                fingerprint in self.blocked_fingerprints
            ),
        }
        self.deferred_semantic_progress_reconciliation_count += 1
        self.deferred_semantic_progress_reconciliation_records.append(record)
        return {"reconciled": True, **record}

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
        bounded_task_repeated_tap_assessment: (
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
        self._record_executed_task_repeat(
            before_sha256=before_sha256,
            action=action,
            after_sha256=after_sha256,
            assessment=bounded_task_repeated_tap_assessment,
        )
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
            "bounded_task_repeated_tap_override_count": (
                self.bounded_task_repeated_tap_override_count
            ),
            "verified_task_repeat_progress": (
                self.verified_task_repeat_progress_record()
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
            "toolbar_affordance_block_count": (
                self.toolbar_affordance_block_count
            ),
            "target_date_visible_swipe_block_count": (
                self.target_date_visible_swipe_block_count
            ),
            "answer_association_block_count": (
                self.answer_association_block_count
            ),
            "target_row_enumeration_block_count": (
                self.target_row_enumeration_block_count
            ),
            "target_row_tap_validation_count": (
                self.target_row_tap_validation_count
            ),
            "target_row_revisit_block_count": (
                self.target_row_revisit_block_count
            ),
            "target_row_aggregation_block_count": (
                self.target_row_aggregation_block_count
            ),
            "target_row_visual_answer_accept_count": (
                self.target_row_visual_answer_accept_count
            ),
            "target_row_explicit_field_block_count": (
                self.target_row_explicit_field_block_count
            ),
            "target_row_read_only_mutation_block_count": (
                self.target_row_read_only_mutation_block_count
            ),
            "target_row_off_list_coordinate_block_count": (
                self.target_row_off_list_coordinate_block_count
            ),
            "target_row_non_control_tap_block_count": (
                self.target_row_non_control_tap_block_count
            ),
            "target_date_row_count": self.target_date_row_count,
            "target_row_detail_required": self.target_row_detail_required,
            "target_row_distinct_visit_count": len(
                self.target_row_visit_keys
            ),
            "target_row_visit_keys": list(self.target_row_visit_keys),
            "active_target_row_visit_key": (
                self.active_target_row_visit_key
            ),
            "target_row_detail_frames": list(
                self.target_row_detail_frames
            ),
            "target_row_progress": self.target_row_progress_record(),
            "requested_answer_role": self.requested_answer_role,
            "target_date_row_observations": list(
                self.target_date_row_observations
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
            "post_activation_clear_text_block_count": (
                self.post_activation_clear_text_block_count
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
            "bounded_task_repeated_tap_override_count": (
                self.bounded_task_repeated_tap_override_count
            ),
            "bounded_task_repeated_tap_override_records": list(
                self.bounded_task_repeated_tap_override_records
            ),
            "deferred_semantic_progress_reconciliation_count": (
                self.deferred_semantic_progress_reconciliation_count
            ),
            "deferred_semantic_progress_reconciliation_records": list(
                self.deferred_semantic_progress_reconciliation_records
            ),
            "verified_task_repeat_progress": (
                self.verified_task_repeat_progress_record()
            ),
            "verified_task_repeat_observation_records": list(
                self.verified_task_repeat_observation_records
            ),
            "task_repeat_count_complete_block_count": (
                self.task_repeat_count_complete_block_count
            ),
            "ab_ab_cycle_trigger_count": self.cycle_trigger_count,
            "visible_failure_trigger_count": (
                self.visible_failure_trigger_count
            ),
            "validation_blocks": self.validation_blocks,
            "recovery_obligation_count": self.recovery_obligations,
            "recovery_completion_count": self.recovery_completions,
        }
