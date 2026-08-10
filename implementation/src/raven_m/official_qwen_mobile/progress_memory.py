"""A2 verified-progress memory and a separately audited cost guard.

The memory is a compact, episode-local replacement for A1's recency list.  It
stores only model-visible facts plus controller-observed *screen transition*
evidence.  A transition never proves task completion.  The deterministic guard
is deliberately a separate object: it can prevent repeated no-op actions, but
its interventions are never counted as memory successes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from typing import Any

import numpy as np
from PIL import Image


_PROGRESS_PAYLOAD = re.compile(r"^\s*PROGRESS\[(?P<payload>.*?)\]\s*\|", re.DOTALL)
_FIELDS = ("observed", "verified", "pending", "expected")


def _compact(value: Any) -> str:
    return " ".join(str(value).split()).strip()


def _observable_change(transition: dict[str, Any]) -> bool:
    fraction = transition.get("changed_pixel_fraction_gt_5")
    # Active A2 decisions use only the screenshot channel visible to the model.
    # Activity/UI-tree changes remain in the audit log but cannot influence the
    # memory state or the guard.
    return bool(isinstance(fraction, (int, float)) and float(fraction) >= 0.001)


def _state_signature(snapshot: dict[str, Any]) -> str:
    pixels = snapshot.get("pixels")
    if pixels is not None:
        array = np.asarray(pixels, dtype=np.uint8)
        image = Image.fromarray(array).convert("L").resize(
            (16, 16), Image.Resampling.BILINEAR
        )
        # Coarse quantization ignores tiny clock/caret/ripple differences while
        # retaining the layout visible to the model.
        quantized = (np.asarray(image, dtype=np.uint8) // 16).astype(np.uint8)
        return sha256(quantized.tobytes()).hexdigest()
    fallback = snapshot.get("pixel_sha256") or snapshot.get("screenshot_sha256")
    if fallback:
        return sha256(str(fallback).encode("utf-8")).hexdigest()
    # Unit/replay fixtures can provide a synthetic model-visible state id.
    return sha256(str(snapshot.get("visible_state", "missing")).encode("utf-8")).hexdigest()


def _coordinate_bucket(value: Any) -> int | None:
    if not isinstance(value, (int, float)):
        return None
    # Qwen commonly jitters a coordinate by a few pixels while targeting the
    # same control.  One-decimal normalized coordinates are deliberately
    # conservative because blocking also requires the same visible state
    # and two prior no-transition executions.
    return int(round(float(value) * 10.0))


def action_signature(action: dict[str, Any]) -> str:
    action_type = str(action.get("type"))
    if action_type in {"tap", "long_press", "swipe"}:
        record = {"type": action_type}
        for key in ("x", "y", "x2", "y2"):
            if key in action:
                record[key] = _coordinate_bucket(action.get(key))
        if action_type == "long_press":
            record["duration_ms"] = int(action.get("duration_ms") or 0)
    elif action_type == "type_text":
        record = {
            "type": action_type,
            "text_sha256": sha256(str(action.get("text", "")).encode("utf-8")).hexdigest(),
            "clear_text": bool(action.get("clear_text")),
        }
    else:
        record = {key: action.get(key) for key in sorted(action)}
    return sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


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
    """One compact progress state, grounded only in visible episode evidence."""

    mechanism_id = "a2_verified_progress_memory_v1"

    def __init__(self, *, max_chars: int = 1200) -> None:
        self.max_chars = max(256, int(max_chars))
        self._state: ProgressState | None = None
        self.write_attempt_count = 0
        self.write_success_count = 0
        self.read_count = 0
        self.nonempty_read_count = 0

    @staticmethod
    def extract_fields(action_summary: str) -> dict[str, str] | None:
        match = _PROGRESS_PAYLOAD.search(str(action_summary))
        if match is None:
            return None
        payload = _compact(match.group("payload"))
        fields: dict[str, str] = {}
        for part in payload.split(";"):
            key, separator, value = part.partition("=")
            key = key.strip().lower()
            if separator and key in _FIELDS:
                fields[key] = _compact(value) or "none"
        if set(fields) != set(_FIELDS):
            return None
        return fields

    @staticmethod
    def history_summary(action_summary: str) -> str:
        """Keep the official action history, but do not duplicate A2 state in it."""
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
        self.write_attempt_count += 1
        fields = self.extract_fields(action_summary)
        if fields is None:
            return {
                "written": False,
                "reason": "progress_prefix_missing_or_malformed",
                "source_step": int(source_step),
            }
        changed = _observable_change(transition)
        evidence = {
            "changed_pixel_fraction_gt_5": transition.get(
                "changed_pixel_fraction_gt_5"
            ),
            "activity_changed": bool(transition.get("activity_changed")),
            "ui_sha_changed": bool(transition.get("ui_sha_changed")),
        }
        self._state = ProgressState(
            source_step=int(source_step),
            observed=fields["observed"],
            verified=fields["verified"],
            pending=fields["pending"],
            expected=fields["expected"],
            executed_action=dict(canonical_action),
            observable_outcome="visible_change" if changed else "no_visible_change",
            transition_evidence=evidence,
            source_call_id=str(source_call_id),
            source_response_sha256=str(source_response_sha256),
            source_screenshot_sha256=str(source_screenshot_sha256),
        )
        self.write_success_count += 1
        return {"written": True, "state": self._state.audit_record()}

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        self.read_count += 1
        guard_notice = _compact((context or {}).get("guard_notice") or "")
        lines: list[str] = []
        if self._state is not None:
            state = self._state
            lines = [
                "Compact progress memory from your own prior visible evidence:",
                f"- observed: {state.observed}",
                f"- screenshot-attested requirements: {state.verified}",
                f"- pending: {state.pending}",
                f"- last expected visible effect: {state.expected}",
                f"- actual observable outcome: {state.observable_outcome}",
            ]
            if state.observable_outcome == "no_visible_change":
                lines.append(
                    "- the last action remains unverified; inspect or choose a different target"
                )
        if guard_notice:
            lines.append(f"- COST-GUARD NOTICE: {guard_notice}")
        if lines:
            lines.append(
                "The current screenshot overrides memory. A screen change alone does not prove task completion."
            )
        rendered = "\n".join(lines)
        if len(rendered) > self.max_chars:
            rendered = rendered[: self.max_chars]
        if rendered:
            self.nonempty_read_count += 1
        audit = {
            "mechanism_id": self.mechanism_id,
            "state_source_step": self._state.source_step if self._state else None,
            "rendered_chars": len(rendered),
            "rendered_sha256": sha256(rendered.encode("utf-8")).hexdigest(),
            "nonempty": bool(rendered),
            "guard_notice_present": bool(guard_notice),
        }
        return rendered, audit

    def audit_record(self) -> dict[str, Any]:
        return {
            "mechanism_id": self.mechanism_id,
            "max_chars": self.max_chars,
            "write_attempt_count": self.write_attempt_count,
            "write_success_count": self.write_success_count,
            "read_count": self.read_count,
            "nonempty_read_count": self.nonempty_read_count,
            "active": self.write_success_count > 0 and self.nonempty_read_count > 0,
            "state": self._state.audit_record() if self._state else None,
        }


class RepeatedNoProgressGuard:
    """Cost-only guard for equivalent actions on an observably unchanged state."""

    mechanism_id = "a2_repeated_no_progress_cost_guard_v1"

    def __init__(self, *, no_progress_threshold: int = 2, max_blocks: int = 2) -> None:
        self.no_progress_threshold = max(2, int(no_progress_threshold))
        self.max_blocks = max(1, int(max_blocks))
        self._counts: dict[tuple[str, str], int] = {}
        self._last_blocked_key: tuple[str, str] | None = None
        self._consecutive_blocks = 0
        self.trigger_count = 0
        self.block_count = 0
        self.cost_stop_count = 0

    def assess(self, *, before: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
        key = (_state_signature(before), action_signature(action))
        count = self._counts.get(key, 0)
        blocked = count >= self.no_progress_threshold
        if blocked:
            self.trigger_count += 1
        return {
            "mechanism_id": self.mechanism_id,
            "blocked": blocked,
            "state_signature": key[0],
            "action_signature": key[1],
            "prior_no_progress_executions": count,
            "threshold": self.no_progress_threshold,
        }

    def observe(
        self,
        *,
        before: dict[str, Any],
        after: dict[str, Any],
        action: dict[str, Any],
        transition: dict[str, Any],
    ) -> dict[str, Any]:
        before_key = _state_signature(before)
        after_key = _state_signature(after)
        key = (before_key, action_signature(action))
        if self._last_blocked_key is not None and key != self._last_blocked_key:
            # Trying a genuinely different action is compliance with the guard,
            # so a later block starts a new consecutive-block sequence.
            self._consecutive_blocks = 0
            self._last_blocked_key = None
        unchanged = not _observable_change(transition) and before_key == after_key
        if unchanged:
            self._counts[key] = self._counts.get(key, 0) + 1
        else:
            self._counts.pop(key, None)
            self._consecutive_blocks = 0
            self._last_blocked_key = None
        return {
            "mechanism_id": self.mechanism_id,
            "observable_no_progress": unchanged,
            "no_progress_count": self._counts.get(key, 0),
            "state_signature": before_key,
            "action_signature": key[1],
        }

    def record_block(self, assessment: dict[str, Any]) -> dict[str, Any]:
        key = (
            str(assessment["state_signature"]),
            str(assessment["action_signature"]),
        )
        self.block_count += 1
        if key == self._last_blocked_key:
            self._consecutive_blocks += 1
        else:
            self._last_blocked_key = key
            self._consecutive_blocks = 1
        stop = self._consecutive_blocks >= self.max_blocks
        if stop:
            self.cost_stop_count += 1
        return {
            **assessment,
            "block_index_for_same_state_action": self._consecutive_blocks,
            "cost_stop": stop,
            "message": (
                "This equivalent action has already produced no observable change twice on "
                "this same UI state. Do not repeat it; inspect the screen and choose a "
                "different target or route."
            ),
        }

    def notice(self, before: dict[str, Any]) -> str:
        state = _state_signature(before)
        candidates = [
            count for (state_signature, _), count in self._counts.items()
            if state_signature == state and count >= self.no_progress_threshold
        ]
        if not candidates:
            return ""
        return (
            "An action on this exact UI state has already caused no observable change "
            "twice. Do not repeat the same target/action; inspect and reroute."
        )

    def audit_record(self) -> dict[str, Any]:
        return {
            "mechanism_id": self.mechanism_id,
            "no_progress_threshold": self.no_progress_threshold,
            "max_blocks": self.max_blocks,
            "trigger_count": self.trigger_count,
            "block_count": self.block_count,
            "cost_stop_count": self.cost_stop_count,
            "tracked_no_progress_signature_count": len(self._counts),
        }
