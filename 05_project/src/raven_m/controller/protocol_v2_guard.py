"""Generic protocol-v2 provenance and repeated-action guard."""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
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


def _box_value(box: Any, field: str) -> Any:
    if isinstance(box, dict):
        return box.get(field)
    return getattr(box, field, None)


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

    def reset(self, *, goal: str) -> None:
        self.goal = goal
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
    ) -> None:
        self._validate_text_provenance(decision)
        action = decision.get("action")
        if not isinstance(action, dict):
            return
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
    ) -> dict[str, Any]:
        action_key = canonical_action_key(action)
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
            "new_visible_failures": new_visible_failures,
        }

    def audit_record(self) -> dict[str, Any]:
        return {
            "schema_version": "protocol_v2_guard_audit.v1",
            "max_no_effect_repeats": self.max_no_effect_repeats,
            "max_identical_coordinate_actions": (
                self.max_identical_coordinate_actions
            ),
            "blocked_fingerprint_count": len(self.blocked_fingerprints),
            "validation_block_count": len(self.validation_blocks),
            "identical_coordinate_block_count": (
                self.identical_coordinate_block_count
            ),
            "destination_picker_back_block_count": (
                self.destination_picker_back_block_count
            ),
            "ab_ab_cycle_trigger_count": self.cycle_trigger_count,
            "visible_failure_trigger_count": (
                self.visible_failure_trigger_count
            ),
            "validation_blocks": self.validation_blocks,
            "recovery_obligation_count": self.recovery_obligations,
            "recovery_completion_count": self.recovery_completions,
        }
