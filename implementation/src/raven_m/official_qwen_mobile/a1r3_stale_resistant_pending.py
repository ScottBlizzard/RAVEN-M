"""A1-R3 stale-resistant verified/pending memory.

The mechanism preserves A1-R2's exact model-authored ledger contract and
default renderer.  It changes only memory lifecycle: identical state cannot
refresh its TTL, an expired state cannot immediately resurrect, and two
same-family actions with no visible RGB progress create one bounded negative
fact.  It never plans, judges completion, or controls an action.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import math
import re
from typing import Any


MECHANISM_ID = "a1r3_stale_resistant_pending_v1"
EXPERIMENT_ID = "A1R3_SRPL_QWEN3VL32B_AW_HARD_T20260806_G3407_V1"

_PREFIX = re.compile(
    r"^\s*MEMORY\[observed=(?P<observed>.*?);\s*"
    r"verified=(?P<verified>.*?);\s*pending=(?P<pending>.*?)\]\s*\|\s*"
    r"(?P<imperative>\S(?:.*\S)?)\s*$",
    re.DOTALL,
)
_BASE_RENDER = (
    "Latest compact task ledger from your own previous Action:\n"
    "VERIFIED: {verified}\n"
    "PENDING: {pending}\n"
    "The current screenshot is authoritative. Continue the pending task only "
    "when it remains consistent with what is visible."
)
_FAILURE_LINE = (
    "\nAVOID REPEATING: {label} produced no visible progress twice for this "
    "pending item. Use the current screenshot before choosing a different route."
)


def _clean(value: str, *, limit: int = 450) -> str:
    cleaned = " ".join(str(value).split()).strip()
    if not cleaned or len(cleaned) > limit or "\x00" in cleaned:
        raise ValueError("field_boundary")
    return cleaned


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _state_key(verified: str, pending: str) -> str:
    return _digest(f"{verified}\n{pending}")


def _bucket(value: Any, width: float = 0.05) -> str:
    try:
        number = min(1.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        number = 0.0
    bucket = math.floor(number / width + 0.5) * width
    return f"{min(1.0, bucket):.2f}"


def canonical_action_family(action: dict[str, Any] | None) -> tuple[str, str] | None:
    """Return a bounded task-agnostic action family and readable label."""

    if not isinstance(action, dict):
        return None
    kind = str(action.get("type") or "")
    if kind in {"tap", "long_press"}:
        x, y = _bucket(action.get("x")), _bucket(action.get("y"))
        return f"{kind}:{x}:{y}", f"{kind} near ({x}, {y})"
    if kind == "swipe":
        try:
            dx = float(action.get("x2")) - float(action.get("x"))
            dy = float(action.get("y2")) - float(action.get("y"))
        except (TypeError, ValueError):
            return None
        direction = (
            "right" if abs(dx) >= abs(dy) and dx >= 0
            else "left" if abs(dx) >= abs(dy)
            else "down" if dy >= 0
            else "up"
        )
        return f"swipe:{direction}", f"swipe {direction}"
    if kind == "type_text":
        text = " ".join(str(action.get("text") or "").split()).casefold()
        if not text:
            return None
        return f"type_text:{_digest(text)[:16]}", "typing the same text"
    if kind in {"press_back", "press_home", "press_enter", "press_recents", "wait"}:
        return kind, kind.replace("_", " ")
    return None


@dataclass(frozen=True)
class ParsedLedger:
    valid: bool
    history: str
    verified: str | None = None
    pending: str | None = None
    clear: bool = False
    error: str | None = None


def parse_memory_prefix(action_summary: str) -> ParsedLedger:
    match = _PREFIX.fullmatch(str(action_summary))
    if match is None:
        return ParsedLedger(False, str(action_summary), error="invalid_prefix")
    try:
        verified = _clean(match.group("verified"))
        pending = _clean(match.group("pending"))
        imperative = _clean(match.group("imperative"), limit=1000)
    except ValueError as exc:
        return ParsedLedger(False, str(action_summary), error=str(exc))
    return ParsedLedger(
        True,
        imperative,
        verified=verified,
        pending=pending,
        clear=pending.casefold() == "none",
    )


@dataclass
class PendingLedger:
    ledger_id: str
    state_key: str
    source_step: int
    verified: str
    pending: str
    source_call_id: str
    source_response_sha256: str
    source_screenshot_sha256: str


@dataclass
class FailedAttempt:
    state_key: str
    action_family: str
    label: str
    second_support_step: int


@dataclass
class ReadTicket:
    ticket_id: str
    request_step: int
    ledger_id: str
    text: str
    text_sha256: str


class StaleResistantPendingMemory:
    """One ledger, one tombstone, and one visible no-progress fact."""

    mechanism_id = MECHANISM_ID

    def __init__(
        self,
        *,
        ttl_requests: int = 8,
        no_progress_pixel_fraction: float = 0.001,
        repeat_support: int = 2,
        max_render_chars: int = 1100,
    ) -> None:
        self.ttl_requests = max(2, int(ttl_requests))
        self.no_progress_pixel_fraction = min(0.01, max(0.0, float(no_progress_pixel_fraction)))
        self.repeat_support = max(2, int(repeat_support))
        self.max_render_chars = max(128, int(max_render_chars))
        self.active: PendingLedger | None = None
        self.retired_state_key: str | None = None
        self.failed_attempt: FailedAttempt | None = None
        self.pending_ticket: ReadTicket | None = None
        self._last_attempt_key: tuple[str, str] | None = None
        self._last_attempt_streak = 0
        self._serial = 0
        self._last_committed_read: dict[str, Any] | None = None
        self.counters = {
            "read_call_count": 0,
            "nonempty_read_count": 0,
            "injected_chars": 0,
            "write_attempt_count": 0,
            "valid_prefix_count": 0,
            "invalid_prefix_count": 0,
            "new_state_count": 0,
            "replacement_count": 0,
            "same_state_nonrefresh_count": 0,
            "retired_state_rejection_count": 0,
            "clear_count": 0,
            "expiry_count": 0,
            "failure_support_count": 0,
            "failure_evidence_count": 0,
            "failure_clear_on_progress_count": 0,
            "cancelled_read_count": 0,
        }

    def _id(self, prefix: str) -> str:
        self._serial += 1
        return f"{prefix}_{self._serial:04d}"

    def history_summary(self, action_summary: str) -> str:
        return parse_memory_prefix(action_summary).history

    def _clear_attempt_tracking(self, *, clear_failure: bool) -> None:
        self._last_attempt_key = None
        self._last_attempt_streak = 0
        if clear_failure:
            self.failed_attempt = None

    def _retire_active(self) -> str | None:
        if self.active is None:
            return None
        ledger_id = self.active.ledger_id
        self.retired_state_key = self.active.state_key
        self.active = None
        self._clear_attempt_tracking(clear_failure=True)
        return ledger_id

    def _accept_state(
        self,
        *,
        source_step: int,
        verified: str,
        pending: str,
        source_call_id: str,
        source_response_sha256: str,
        source_screenshot_sha256: str,
    ) -> PendingLedger:
        key = _state_key(verified, pending)
        ledger = PendingLedger(
            ledger_id=f"srpl_{int(source_step):03d}_{key[:12]}",
            state_key=key,
            source_step=int(source_step),
            verified=verified,
            pending=pending,
            source_call_id=str(source_call_id),
            source_response_sha256=str(source_response_sha256),
            source_screenshot_sha256=str(source_screenshot_sha256),
        )
        self.active = ledger
        self.retired_state_key = None
        self._clear_attempt_tracking(clear_failure=True)
        return ledger

    def observe_step(
        self,
        *,
        source_step: int,
        action_summary: str,
        canonical_action: dict[str, Any] | None,
        transition: dict[str, Any],
        source_call_id: str,
        source_response_sha256: str,
        source_screenshot_sha256: str,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        del before, after
        self.counters["write_attempt_count"] += 1
        parsed = parse_memory_prefix(action_summary)
        event: dict[str, Any] = {
            "mechanism_id": MECHANISM_ID,
            "source_step": int(source_step),
            "prefix_valid": parsed.valid,
            "write_kind": None,
            "no_progress_support": False,
        }
        if parsed.valid:
            self.counters["valid_prefix_count"] += 1
            if parsed.clear:
                cleared = self.active.ledger_id if self.active else None
                self.active = None
                self.retired_state_key = None
                self._clear_attempt_tracking(clear_failure=True)
                self.counters["clear_count"] += 1
                event.update({"write_kind": "explicit_clear", "cleared_ledger_id": cleared})
                return event
            assert parsed.verified is not None and parsed.pending is not None
            key = _state_key(parsed.verified, parsed.pending)
            if self.active is not None and key == self.active.state_key:
                self.counters["same_state_nonrefresh_count"] += 1
                event.update({"write_kind": "same_state_not_refreshed", "ledger_id": self.active.ledger_id})
            elif self.active is None and key == self.retired_state_key:
                self.counters["retired_state_rejection_count"] += 1
                event["write_kind"] = "retired_state_rejected"
            else:
                replacement = self.active is not None
                ledger = self._accept_state(
                    source_step=source_step,
                    verified=parsed.verified,
                    pending=parsed.pending,
                    source_call_id=source_call_id,
                    source_response_sha256=source_response_sha256,
                    source_screenshot_sha256=source_screenshot_sha256,
                )
                counter = "replacement_count" if replacement else "new_state_count"
                self.counters[counter] += 1
                event.update({
                    "write_kind": "latest_state_replacement" if replacement else "new_latest_state",
                    "ledger_id": ledger.ledger_id,
                    "verified_sha256": _digest(ledger.verified),
                    "pending_sha256": _digest(ledger.pending),
                })
        else:
            self.counters["invalid_prefix_count"] += 1
            event["write_kind"] = "invalid_prefix_state_unchanged"

        if self.active is None:
            self._last_attempt_key = None
            self._last_attempt_streak = 0
            return event
        changed = transition.get("changed_pixel_fraction_gt_5")
        same_shape = transition.get("same_shape") is True
        try:
            fraction = float(changed)
        except (TypeError, ValueError):
            fraction = math.inf
        if same_shape and fraction > self.no_progress_pixel_fraction:
            if self.failed_attempt is not None:
                self.counters["failure_clear_on_progress_count"] += 1
            self._clear_attempt_tracking(clear_failure=True)
            event["visible_outcome"] = "material_rgb_change"
            return event
        if not same_shape or not math.isfinite(fraction):
            self._last_attempt_key = None
            self._last_attempt_streak = 0
            event["visible_outcome"] = "unknown_not_negative_evidence"
            return event
        family = canonical_action_family(canonical_action)
        if family is None:
            self._last_attempt_key = None
            self._last_attempt_streak = 0
            event["visible_outcome"] = "no_progress_unsupported_action"
            return event
        family_key, label = family
        attempt_key = (self.active.state_key, family_key)
        self._last_attempt_streak = self._last_attempt_streak + 1 if attempt_key == self._last_attempt_key else 1
        self._last_attempt_key = attempt_key
        self.counters["failure_support_count"] += 1
        event.update({
            "visible_outcome": "no_material_rgb_progress",
            "no_progress_support": True,
            "action_family": family_key,
            "support_count": self._last_attempt_streak,
        })
        if self._last_attempt_streak >= self.repeat_support:
            if self.failed_attempt is None or (
                self.failed_attempt.state_key,
                self.failed_attempt.action_family,
            ) != attempt_key:
                self.failed_attempt = FailedAttempt(
                    state_key=self.active.state_key,
                    action_family=family_key,
                    label=label[:96],
                    second_support_step=int(source_step),
                )
                self.counters["failure_evidence_count"] += 1
                event["failure_evidence_created"] = True
        return event

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        del context
        if self.pending_ticket is not None:
            raise RuntimeError("A1-R3 read ticket was not committed or cancelled")
        request_step = self.counters["read_call_count"]
        self.counters["read_call_count"] += 1
        audit: dict[str, Any] = {
            "mechanism_id": MECHANISM_ID,
            "request_step": request_step,
            "nonempty": False,
            "ticket_id": None,
        }
        if self.active is None:
            audit["reason"] = "no_active_ledger"
            return "", audit
        if request_step - self.active.source_step >= self.ttl_requests:
            expired_id = self._retire_active()
            self.counters["expiry_count"] += 1
            audit.update({"reason": "expired_and_tombstoned", "expired_ledger_id": expired_id})
            return "", audit
        text = _BASE_RENDER.format(verified=self.active.verified, pending=self.active.pending)
        if self.failed_attempt is not None and self.failed_attempt.state_key == self.active.state_key:
            text += _FAILURE_LINE.format(label=self.failed_attempt.label)
        if len(text) > self.max_render_chars:
            audit["reason"] = "render_boundary_fail_closed"
            return "", audit
        ticket = ReadTicket(
            ticket_id=self._id("srplread"),
            request_step=request_step,
            ledger_id=self.active.ledger_id,
            text=text,
            text_sha256=_digest(text),
        )
        self.pending_ticket = ticket
        audit.update({
            "nonempty": True,
            "reason": "prepared_not_consumed",
            "ticket_id": ticket.ticket_id,
            "ledger_id": ticket.ledger_id,
            "rendered_chars": len(text),
            "rendered_sha256": ticket.text_sha256,
            "failure_evidence_injected": (
                self.failed_attempt is not None
                and self.failed_attempt.state_key == self.active.state_key
            ),
            "failed_action_family": (
                self.failed_attempt.action_family if self.failed_attempt is not None else None
            ),
            "failure_second_support_step": (
                self.failed_attempt.second_support_step if self.failed_attempt is not None else None
            ),
        })
        return text, audit

    def commit_injection(self, ticket_id: str, final_prompt_sha256: str) -> dict[str, Any]:
        ticket = self.pending_ticket
        if ticket is None or ticket.ticket_id != ticket_id:
            raise RuntimeError("A1-R3 injection ticket mismatch")
        event = {
            "ticket_id": ticket.ticket_id,
            "request_step": ticket.request_step,
            "ledger_id": ticket.ledger_id,
            "exact_injected_text": ticket.text,
            "exact_injected_text_sha256": ticket.text_sha256,
            "final_prompt_sha256": str(final_prompt_sha256),
            "chars": len(ticket.text),
        }
        self.pending_ticket = None
        self.counters["nonempty_read_count"] += 1
        self.counters["injected_chars"] += len(ticket.text)
        self._last_committed_read = event
        return event

    def cancel_injection(self, ticket_id: str, reason: str) -> dict[str, Any]:
        ticket = self.pending_ticket
        if ticket is None or ticket.ticket_id != ticket_id:
            raise RuntimeError("A1-R3 cancellation ticket mismatch")
        self.pending_ticket = None
        self.counters["cancelled_read_count"] += 1
        return {"ticket_id": ticket_id, "cancelled": True, "reason": str(reason)}

    def audit_record(self) -> dict[str, Any]:
        return {
            "schema": "a1r3_stale_resistant_pending_audit_v1",
            "mechanism_id": MECHANISM_ID,
            "active": self.counters["nonempty_read_count"] > 0,
            "active_ledger": asdict(self.active) if self.active else None,
            "retired_state_key": self.retired_state_key,
            "failed_attempt": asdict(self.failed_attempt) if self.failed_attempt else None,
            "pending_ticket": asdict(self.pending_ticket) if self.pending_ticket else None,
            "last_committed_read": self._last_committed_read,
            "counters": dict(self.counters),
            "capacity": {
                "max_ledgers": 1,
                "max_tombstones": 1,
                "max_failed_attempts": 1,
                "max_pending_tickets": 1,
                "max_render_chars": self.max_render_chars,
            },
            "decision_boundary": {
                "extra_model_calls": 0,
                "action_override_count": 0,
                "forced_termination_count": 0,
                "hidden_ui_used_for_decision": False,
                "evaluator_used_for_decision": False,
            },
        }


__all__ = [
    "EXPERIMENT_ID",
    "MECHANISM_ID",
    "StaleResistantPendingMemory",
    "canonical_action_family",
    "parse_memory_prefix",
]
