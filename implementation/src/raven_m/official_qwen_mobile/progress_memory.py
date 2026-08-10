"""A2-v1r1 episode-local progress memory and separately audited cost guard.

The memory stores the model's own structured description of screenshot-visible
progress.  ``verified`` is therefore a model-authored assertion, never an
evaluator or controller confirmation.  The guard uses only exact model-visible
pixels and the exact mapped physical action; hidden Android state is audit-only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from typing import Any

import numpy as np


_PROGRESS_PAYLOAD = re.compile(r"^\s*PROGRESS\[(?P<payload>.*?)\]\s*\|", re.DOTALL)
_FIELDS = ("observed", "verified", "pending", "expected")
_GUARD_ELIGIBLE_ACTIONS = frozenset({"tap", "long_press", "swipe"})


def _compact(value: Any) -> str:
    return " ".join(str(value).split()).strip()


def progress_parse(action_summary: str) -> dict[str, Any]:
    """Return a complete compliance record for one protocol-valid response."""
    text = str(action_summary)
    match = _PROGRESS_PAYLOAD.search(text)
    prefix_present = match is not None
    fields: dict[str, str] = {}
    payload = ""
    if match is not None:
        payload = _compact(match.group("payload"))
        for part in payload.split(";"):
            key, separator, value = part.partition("=")
            key = key.strip().lower()
            if separator and key in _FIELDS and key not in fields:
                fields[key] = _compact(value) or "none"
    fields_complete = set(fields) == set(_FIELDS)
    if not prefix_present:
        reason = "progress_prefix_missing"
    elif not fields_complete:
        reason = "progress_fields_missing_or_duplicate"
    else:
        reason = "valid"
    return {
        "prefix_present": prefix_present,
        "fields_complete": fields_complete,
        "payload_chars": len(payload),
        "observed_present": bool(fields.get("observed")),
        "verified_present": bool(fields.get("verified")),
        "pending_present": bool(fields.get("pending")),
        "expected_present": bool(fields.get("expected")),
        "parse_reason": reason,
        "fields": fields if fields_complete else None,
    }


def transition_outcome(transition: dict[str, Any]) -> str:
    """Classify screenshot evidence without using hidden UI/activity signals."""
    if transition.get("exactly_unchanged") is True:
        return "no_visible_change_exact"
    fraction = transition.get("changed_pixel_fraction_gt_5")
    if isinstance(fraction, (int, float)) and float(fraction) >= 0.001:
        return "material_visible_change"
    return "minor_or_ambiguous_visible_change"


def exact_state_signature(
    snapshot: dict[str, Any], *, allow_synthetic_visible_state: bool = False
) -> str:
    """Hash exactly the model-visible pixels, including their representation."""
    pixels = snapshot.get("pixels")
    if pixels is not None:
        array = np.ascontiguousarray(np.asarray(pixels))
        header = json.dumps(
            {
                "domain": "a2-v1r1-model-visible-pixels",
                "shape": list(array.shape),
                "dtype": array.dtype.str,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return sha256(header + b"\0" + array.tobytes(order="C")).hexdigest()
    pixel_hash = snapshot.get("pixel_sha256")
    shape = snapshot.get("pixel_shape")
    dtype = snapshot.get("pixel_dtype")
    if pixel_hash and shape and dtype:
        payload = {
            "domain": "a2-v1r1-model-visible-pixel-hash",
            "pixel_sha256": str(pixel_hash),
            "shape": list(shape),
            "dtype": str(dtype),
        }
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    if allow_synthetic_visible_state and "visible_state" in snapshot:
        return sha256(
            ("a2-v1r1-explicit-test-state\0" + str(snapshot["visible_state"])).encode(
                "utf-8"
            )
        ).hexdigest()
    raise RuntimeError("A2 scored guard requires exact model-visible pixels or exact pixel metadata.")


def mapped_action_signature(mapped_action: dict[str, Any]) -> tuple[bool, str | None]:
    """Hash only guard-eligible, exact mapped physical actions."""
    canonical = dict(mapped_action.get("canonical") or {})
    action_type = str(canonical.get("type") or "")
    if action_type not in _GUARD_ELIGIBLE_ACTIONS:
        return False, None
    actual = dict(mapped_action.get("actual_pixels") or {})
    required = ("x", "y", "x2", "y2") if action_type == "swipe" else ("x", "y")
    if any(isinstance(actual.get(key), bool) or not isinstance(actual.get(key), int) for key in required):
        raise RuntimeError(f"A2 guard requires exact integer pixels for {action_type}.")
    record: dict[str, Any] = {
        "domain": "a2-v1r1-mapped-physical-action",
        "type": action_type,
        "actual_pixels": {key: int(actual[key]) for key in required},
    }
    if action_type in {"long_press", "swipe"}:
        record["duration_ms"] = int(canonical.get("duration_ms") or 0)
    digest = sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return True, digest


@dataclass(frozen=True)
class ProgressState:
    source_step: int
    observed: str
    verified: str
    pending: str
    expected: str
    executed_action: dict[str, Any]
    observable_outcome: str
    transition_evidence: dict[str, Any]
    source_call_id: str
    source_response_sha256: str
    source_screenshot_sha256: str

    def audit_record(self) -> dict[str, Any]:
        return asdict(self)


class VerifiedProgressMemory:
    """One compact state containing the model's prior screenshot assertions."""

    mechanism_id = "a2_verified_progress_memory_v1r1"

    def __init__(self, *, max_chars: int = 1200) -> None:
        self.max_chars = max(256, int(max_chars))
        self._state: ProgressState | None = None
        self.progress_prefix_attempt_count = 0
        self.progress_prefix_valid_count = 0
        self.memory_write_success_count = 0
        self.read_count = 0
        self.nonempty_read_count = 0

    @staticmethod
    def extract_fields(action_summary: str) -> dict[str, str] | None:
        return progress_parse(action_summary)["fields"]

    def record_progress_parse(self, action_summary: str) -> dict[str, Any]:
        parsed = progress_parse(action_summary)
        self.progress_prefix_attempt_count += 1
        if parsed["fields_complete"]:
            self.progress_prefix_valid_count += 1
        return {key: value for key, value in parsed.items() if key != "fields"}

    @staticmethod
    def history_summary(action_summary: str) -> str:
        match = _PROGRESS_PAYLOAD.search(str(action_summary))
        if match is None:
            return _compact(action_summary)
        return _compact(str(action_summary)[match.end() :])

    def observe_step(
        self,
        *,
        source_step: int,
        action_summary: str,
        canonical_action: dict[str, Any],
        transition: dict[str, Any],
        source_call_id: str,
        source_response_sha256: str,
        source_screenshot_sha256: str,
    ) -> dict[str, Any]:
        fields = self.extract_fields(action_summary)
        if fields is None:
            return {
                "written": False,
                "reason": "progress_prefix_missing_or_malformed",
                "source_step": int(source_step),
            }
        evidence = {
            "exactly_unchanged": transition.get("exactly_unchanged"),
            "changed_pixel_fraction_gt_5": transition.get("changed_pixel_fraction_gt_5"),
            "activity_changed": bool(transition.get("activity_changed")),
            "ui_sha_changed": bool(transition.get("ui_sha_changed")),
            "active_memory_input": False,
            "active_guard_input": False,
            "model_visible": False,
        }
        self._state = ProgressState(
            source_step=int(source_step),
            observed=fields["observed"],
            verified=fields["verified"],
            pending=fields["pending"],
            expected=fields["expected"],
            executed_action=dict(canonical_action),
            observable_outcome=transition_outcome(transition),
            transition_evidence=evidence,
            source_call_id=str(source_call_id),
            source_response_sha256=str(source_response_sha256),
            source_screenshot_sha256=str(source_screenshot_sha256),
        )
        self.memory_write_success_count += 1
        return {"written": True, "state": self._state.audit_record()}

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        del context  # Guard warnings belong only in ordinary action history.
        self.read_count += 1
        lines: list[str] = []
        if self._state is not None:
            state = self._state
            lines = [
                "Compact progress memory from your own prior screenshot-visible assertions:",
                f"- observed: {state.observed}",
                f"- model-asserted screenshot-visible requirements: {state.verified}",
                f"- pending: {state.pending}",
                f"- last expected visible effect: {state.expected}",
                f"- actual screenshot outcome: {state.observable_outcome}",
                "These are your prior assertions, not controller or evaluator confirmations.",
            ]
            if state.observable_outcome == "no_visible_change_exact":
                lines.append("- the last action produced an exactly identical screenshot; inspect or reroute")
        if lines:
            lines.append(
                "The current screenshot overrides memory. Screenshot change alone does not prove task completion."
            )
        rendered = "\n".join(lines)[: self.max_chars]
        if rendered:
            self.nonempty_read_count += 1
        return rendered, {
            "mechanism_id": self.mechanism_id,
            "state_source_step": self._state.source_step if self._state else None,
            "rendered_chars": len(rendered),
            "rendered_sha256": sha256(rendered.encode("utf-8")).hexdigest(),
            "nonempty": bool(rendered),
            "guard_notice_present": False,
        }

    def audit_record(self) -> dict[str, Any]:
        return {
            "mechanism_id": self.mechanism_id,
            "max_chars": self.max_chars,
            "progress_prefix_attempt_count": self.progress_prefix_attempt_count,
            "progress_prefix_valid_count": self.progress_prefix_valid_count,
            "memory_write_success_count": self.memory_write_success_count,
            # Backwards-readable aliases; v1r1 reports use the explicit names above.
            "write_attempt_count": self.progress_prefix_attempt_count,
            "write_success_count": self.memory_write_success_count,
            "read_count": self.read_count,
            "nonempty_read_count": self.nonempty_read_count,
            "active": self.memory_write_success_count > 0 and self.nonempty_read_count > 0,
            "verified_semantics": "model_authored_screenshot_visible_assertion_not_objective_confirmation",
            "state": self._state.audit_record() if self._state else None,
        }


class RepeatedNoProgressGuard:
    """Block a third exact repeat after two exact screenshot no-change executions."""

    mechanism_id = "a2_repeated_no_progress_cost_guard_v1r1"

    def __init__(
        self,
        *,
        no_progress_threshold: int = 2,
        max_ignored_block_warnings: int = 2,
        allow_synthetic_visible_state: bool = False,
    ) -> None:
        self.no_progress_threshold = max(2, int(no_progress_threshold))
        self.max_ignored_block_warnings = max(1, int(max_ignored_block_warnings))
        self.allow_synthetic_visible_state = bool(allow_synthetic_visible_state)
        self._counts: dict[tuple[str, str], int] = {}
        self._warnings_delivered: dict[tuple[str, str], int] = {}
        self._last_blocked_key: tuple[str, str] | None = None
        self.trigger_count = 0
        self.block_count = 0
        self.warning_count = 0
        self.cost_stop_count = 0

    def _state(self, snapshot: dict[str, Any]) -> str:
        return exact_state_signature(
            snapshot, allow_synthetic_visible_state=self.allow_synthetic_visible_state
        )

    def assess(self, *, before: dict[str, Any], mapped_action: dict[str, Any]) -> dict[str, Any]:
        eligible, action_sig = mapped_action_signature(mapped_action)
        state_sig = self._state(before)
        proposed_key = (state_sig, str(action_sig)) if eligible else None
        if self._last_blocked_key is not None and proposed_key != self._last_blocked_key:
            self._warnings_delivered.pop(self._last_blocked_key, None)
            self._last_blocked_key = None
        if not eligible:
            return {
                "mechanism_id": self.mechanism_id,
                "eligible": False,
                "blocked": False,
                "state_signature": state_sig,
                "mapped_action_signature": None,
                "prior_no_progress_executions": 0,
                "threshold": self.no_progress_threshold,
            }
        key = proposed_key
        assert key is not None
        count = self._counts.get(key, 0)
        blocked = count >= self.no_progress_threshold
        if blocked:
            self.trigger_count += 1
        return {
            "mechanism_id": self.mechanism_id,
            "eligible": True,
            "blocked": blocked,
            "state_signature": state_sig,
            "mapped_action_signature": action_sig,
            "prior_no_progress_executions": count,
            "threshold": self.no_progress_threshold,
            "warnings_previously_delivered": self._warnings_delivered.get(key, 0),
        }

    def observe(
        self,
        *,
        before: dict[str, Any],
        after: dict[str, Any],
        mapped_action: dict[str, Any],
        transition: dict[str, Any],
    ) -> dict[str, Any]:
        eligible, action_sig = mapped_action_signature(mapped_action)
        before_sig = self._state(before)
        after_sig = self._state(after)
        outcome = transition_outcome(transition)
        if before_sig != after_sig:
            self._counts.clear()
            self._warnings_delivered.clear()
            self._last_blocked_key = None
        if not eligible:
            return {
                "mechanism_id": self.mechanism_id,
                "eligible": False,
                "outcome": outcome,
                "observable_no_progress": False,
                "state_signature": before_sig,
                "mapped_action_signature": None,
            }
        key = (before_sig, str(action_sig))
        exact_no_change = outcome == "no_visible_change_exact" and before_sig == after_sig
        if exact_no_change:
            self._counts[key] = self._counts.get(key, 0) + 1
        else:
            self._counts.pop(key, None)
            self._warnings_delivered.pop(key, None)
            self._last_blocked_key = None
        return {
            "mechanism_id": self.mechanism_id,
            "eligible": True,
            "outcome": outcome,
            "observable_no_progress": exact_no_change,
            "no_progress_count": self._counts.get(key, 0),
            "state_signature": before_sig,
            "mapped_action_signature": action_sig,
        }

    def record_block(self, assessment: dict[str, Any]) -> dict[str, Any]:
        key = (
            str(assessment["state_signature"]),
            str(assessment["mapped_action_signature"]),
        )
        previous = self._warnings_delivered.get(key, 0)
        block_index = previous + 1
        stop = previous >= self.max_ignored_block_warnings
        warning_emitted = not stop
        warning = (
            "This exact mapped action has already produced an exactly identical screenshot "
            "twice on this same visible state. Do not repeat it; inspect the current "
            "screenshot and choose a different target or route."
            if warning_emitted
            else ""
        )
        self.block_count += 1
        self._last_blocked_key = key
        if warning_emitted:
            self.warning_count += 1
            self._warnings_delivered[key] = previous + 1
        if stop:
            self.cost_stop_count += 1
        return {
            **assessment,
            "block_index": block_index,
            "warnings_previously_delivered": previous,
            "warning_emitted": warning_emitted,
            "warning_text_sha256": sha256(warning.encode("utf-8")).hexdigest() if warning else None,
            "cost_stop": stop,
            "message": warning,
        }

    def audit_record(self) -> dict[str, Any]:
        return {
            "mechanism_id": self.mechanism_id,
            "no_progress_threshold": self.no_progress_threshold,
            "max_ignored_block_warnings": self.max_ignored_block_warnings,
            "trigger_count": self.trigger_count,
            "block_count": self.block_count,
            "warning_count": self.warning_count,
            "cost_stop_count": self.cost_stop_count,
            "tracked_no_progress_signature_count": len(self._counts),
        }
