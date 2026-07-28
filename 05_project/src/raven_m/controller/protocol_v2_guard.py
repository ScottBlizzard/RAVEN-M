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
COORDINATE_STREAK_ACTIONS = {"tap", "long_press"}
TEXT_ORIGINS = {
    "task_literal",
    "current_screen",
    "verified_memory",
    "deterministic_calculation",
}
RECOVERY_CLASSES = (
    "change_target",
    "reverse_scroll_direction",
    "navigate_back",
    "reopen_app",
    "inspect_different_visible_control",
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
IGNORED_UI_PACKAGES = {"com.android.systemui"}
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


def canonical_action_key(action: dict[str, Any]) -> str:
    return json.dumps(
        action,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


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
    """Summarize visible focused editable state without exposing a bbox."""
    focused = []
    for element in ui_elements or ():
        if _element_value(element, "is_visible") is False:
            continue
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
        "schema_version": "focused_editable_input_assessment.v1",
        "present": bool(focused),
        "focused_count": len(focused),
        "empty": bool(focused) and all(item["empty"] for item in focused),
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
    ) -> None:
        self.goal = goal
        self.required_selection_text = required_selection_text
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
        self.identical_coordinate_block_count = 0
        self.destination_picker_back_block_count = 0
        self.destination_picker_commit_count = 0
        self.post_destination_commit_block_count = 0
        self.post_destination_commit_active = False
        self.exact_target_long_press_block_count = 0
        self.focused_input_block_count = 0

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
        post_destination_transfer_command_is_action: bool = False,
        exact_selection_assessment: dict[str, Any] | None = None,
        focused_input_assessment: dict[str, Any] | None = None,
    ) -> None:
        self._validate_text_provenance(decision)
        action = decision.get("action")
        if not isinstance(action, dict):
            return
        focused_assessment = focused_input_assessment or {}
        coordinate_bearing_type_text = (
            action.get("type") == "type_text"
            and ("x" in action or "y" in action)
        )
        clears_focused_empty_field = (
            action.get("type") == "type_text"
            and action.get("clear_text") is True
            and focused_assessment.get("empty") is True
        )
        if focused_assessment.get("present") is True and (
            coordinate_bearing_type_text or clears_focused_empty_field
        ):
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": "focused_input_click_before_type_blocked",
                "focused_input_assessment": focused_assessment,
                "required_recovery_classes": [
                    "preserve_focused_input",
                ],
            }
            self.validation_blocks.append(record)
            self.focused_input_block_count += 1
            empty_directive = (
                " The focused field is empty, so set clear_text=false."
                if focused_assessment.get("empty") is True
                else ""
            )
            raise ActionValidationError(
                "FOCUSED_INPUT_GUARD: a visible editable field is already "
                "focused. AndroidWorld clicks supplied x,y before input, "
                "which can destroy that focus. Keep the same type_text text "
                "and provenance but omit x and y."
                + empty_directive
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
        ):
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": "post_destination_commit_mutation_blocked",
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
                "Move to/Copy to again or submit a second transaction. "
                "Reversible inspection of the exact task item is allowed; "
                "otherwise navigate for evidence or return a terminal status."
            )
        if (
            destination_picker_is_active
            and action.get("type") == "press_back"
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
        action_key = canonical_action_key(action)
        if (
            action.get("type") in COORDINATE_STREAK_ACTIONS
            and action_key == self.last_coordinate_action_key
            and self.identical_coordinate_action_count
            >= self.max_identical_coordinate_actions
        ):
            record = {
                "semantic_state_sha256": page_sha256,
                "action": action,
                "reason": "identical_coordinate_action_streak_blocked",
                "required_recovery_classes": list(RECOVERY_CLASSES),
            }
            self.validation_blocks.append(record)
            self.identical_coordinate_block_count += 1
            raise ActionValidationError(
                "LOOP_GUARD: the same coordinate action has already been "
                "executed three consecutive times. Recalculate the target "
                "coordinate or choose a different recovery action."
            )
        fingerprint = (page_sha256, action_key)
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
    ) -> dict[str, Any]:
        action_key = canonical_action_key(action)
        if destination_picker_commit_executed:
            self.destination_picker_commit_count += 1
            self.post_destination_commit_active = True
        if action.get("type") in COORDINATE_STREAK_ACTIONS:
            if action_key == self.last_coordinate_action_key:
                self.identical_coordinate_action_count += 1
            else:
                self.last_coordinate_action_key = action_key
                self.identical_coordinate_action_count = 1
        else:
            self.last_coordinate_action_key = None
            self.identical_coordinate_action_count = 0
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
        if semantic_changed:
            self.no_effect_counts.pop(fingerprint, None)
        else:
            self.no_effect_counts[fingerprint] += 1
            if (
                self.no_effect_counts[fingerprint]
                >= self.max_no_effect_repeats
            ):
                self._block_fingerprint(fingerprint)
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
            "destination_picker_commit_executed": (
                destination_picker_commit_executed
            ),
            "post_destination_commit_active": (
                self.post_destination_commit_active
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
            "required_selection_text": self.required_selection_text,
            "blocked_fingerprint_count": len(self.blocked_fingerprints),
            "validation_block_count": len(self.validation_blocks),
            "identical_coordinate_block_count": (
                self.identical_coordinate_block_count
            ),
            "destination_picker_back_block_count": (
                self.destination_picker_back_block_count
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
            "exact_target_long_press_block_count": (
                self.exact_target_long_press_block_count
            ),
            "focused_input_block_count": self.focused_input_block_count,
            "ab_ab_cycle_trigger_count": self.cycle_trigger_count,
            "visible_failure_trigger_count": (
                self.visible_failure_trigger_count
            ),
            "validation_blocks": self.validation_blocks,
            "recovery_obligation_count": self.recovery_obligations,
            "recovery_completion_count": self.recovery_completions,
        }
