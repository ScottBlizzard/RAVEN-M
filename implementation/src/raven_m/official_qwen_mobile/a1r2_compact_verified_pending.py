"""A1-R2 compact verified/pending ledger.

This arm deliberately keeps A1's already-scored model-authored ``MEMORY[...]``
contract.  It changes only storage: the prefix is removed from ordinary action
history, ``observed`` is discarded because the current screenshot is
authoritative, and only the latest ``verified``/``pending`` pair is injected.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import re
from typing import Any


MECHANISM_ID = "a1r2_compact_verified_pending_v1"
EXPERIMENT_ID = "A1R2_CVP_QWEN3VL32B_AW_HARD_T20260806_G3407_V1"

_PREFIX = re.compile(
    r"^\s*MEMORY\[observed=(?P<observed>.*?);\s*"
    r"verified=(?P<verified>.*?);\s*pending=(?P<pending>.*?)\]\s*\|\s*"
    r"(?P<imperative>\S(?:.*\S)?)\s*$",
    re.DOTALL,
)

_RENDER = (
    "Latest compact task ledger from your own previous Action:\n"
    "VERIFIED: {verified}\n"
    "PENDING: {pending}\n"
    "The current screenshot is authoritative. Continue the pending task only "
    "when it remains consistent with what is visible."
)


def _clean(value: str, *, limit: int = 450) -> str:
    cleaned = " ".join(str(value).split()).strip()
    if not cleaned or len(cleaned) > limit or "\x00" in cleaned:
        raise ValueError("field_boundary")
    return cleaned


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


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
class CompactLedger:
    ledger_id: str
    source_step: int
    verified: str
    pending: str
    source_call_id: str
    source_response_sha256: str
    source_screenshot_sha256: str


@dataclass
class ReadTicket:
    ticket_id: str
    request_step: int
    ledger_id: str
    text: str
    text_sha256: str


class CompactVerifiedPendingMemory:
    """Single-snapshot A1 ledger with exact history de-duplication."""

    mechanism_id = MECHANISM_ID

    def __init__(self, *, ttl_requests: int = 8, max_render_chars: int = 1100) -> None:
        self.ttl_requests = max(2, int(ttl_requests))
        self.max_render_chars = max(128, int(max_render_chars))
        self.active: CompactLedger | None = None
        self.pending_ticket: ReadTicket | None = None
        self.read_call_count = 0
        self.write_attempt_count = 0
        self.write_success_count = 0
        self.clear_count = 0
        self.expiry_count = 0
        self.invalid_prefix_count = 0
        self.nonempty_read_count = 0
        self.injected_chars = 0
        self.replacement_count = 0
        self.same_state_refresh_count = 0
        self.cancelled_read_count = 0
        self._serial = 0
        self._last_committed_read: dict[str, Any] | None = None

    def _id(self, prefix: str) -> str:
        self._serial += 1
        return f"{prefix}_{self._serial:04d}"

    def history_summary(self, action_summary: str) -> str:
        return parse_memory_prefix(action_summary).history

    def write(
        self,
        *,
        source_step: int,
        action_summary: str,
        source_call_id: str,
        source_response_sha256: str,
        source_screenshot_sha256: str,
    ) -> dict[str, Any]:
        self.write_attempt_count += 1
        parsed = parse_memory_prefix(action_summary)
        event: dict[str, Any] = {
            "mechanism_id": MECHANISM_ID,
            "source_step": int(source_step),
            "prefix_valid": parsed.valid,
            "write_kind": None,
        }
        if not parsed.valid:
            self.invalid_prefix_count += 1
            event["write_kind"] = "invalid_prefix_state_unchanged"
            return event
        if parsed.clear:
            previous = self.active.ledger_id if self.active else None
            self.active = None
            self.clear_count += 1
            event.update({"write_kind": "explicit_clear", "cleared_ledger_id": previous})
            return event
        assert parsed.verified is not None and parsed.pending is not None
        state_key = _digest(f"{parsed.verified}\n{parsed.pending}")
        if self.active is not None:
            old_key = _digest(f"{self.active.verified}\n{self.active.pending}")
            if old_key == state_key:
                self.same_state_refresh_count += 1
                kind = "same_state_refresh"
            else:
                self.replacement_count += 1
                kind = "latest_state_replacement"
        else:
            kind = "new_latest_state"
        self.active = CompactLedger(
            ledger_id=f"cvp_{int(source_step):03d}_{state_key[:12]}",
            source_step=int(source_step),
            verified=parsed.verified,
            pending=parsed.pending,
            source_call_id=str(source_call_id),
            source_response_sha256=str(source_response_sha256),
            source_screenshot_sha256=str(source_screenshot_sha256),
        )
        self.write_success_count += 1
        event.update(
            {
                "write_kind": kind,
                "ledger_id": self.active.ledger_id,
                "verified_sha256": _digest(parsed.verified),
                "pending_sha256": _digest(parsed.pending),
            }
        )
        return event

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        del context
        if self.pending_ticket is not None:
            raise RuntimeError("A1-R2 read ticket was not committed or cancelled")
        request_step = self.read_call_count
        self.read_call_count += 1
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
            expired_id = self.active.ledger_id
            self.active = None
            self.expiry_count += 1
            audit.update({"reason": "expired", "expired_ledger_id": expired_id})
            return "", audit
        text = _RENDER.format(
            verified=self.active.verified,
            pending=self.active.pending,
        )
        if len(text) > self.max_render_chars:
            audit["reason"] = "render_boundary_fail_closed"
            return "", audit
        ticket = ReadTicket(
            ticket_id=self._id("cvpread"),
            request_step=request_step,
            ledger_id=self.active.ledger_id,
            text=text,
            text_sha256=_digest(text),
        )
        self.pending_ticket = ticket
        audit.update(
            {
                "nonempty": True,
                "reason": "prepared_not_consumed",
                "ticket_id": ticket.ticket_id,
                "ledger_id": ticket.ledger_id,
                "rendered_chars": len(text),
                "rendered_sha256": ticket.text_sha256,
            }
        )
        return text, audit

    def commit_injection(self, ticket_id: str, final_prompt_sha256: str) -> dict[str, Any]:
        ticket = self.pending_ticket
        if ticket is None or ticket.ticket_id != ticket_id:
            raise RuntimeError("A1-R2 injection ticket mismatch")
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
        self.nonempty_read_count += 1
        self.injected_chars += len(ticket.text)
        self._last_committed_read = event
        return event

    def cancel_injection(self, ticket_id: str, reason: str) -> dict[str, Any]:
        ticket = self.pending_ticket
        if ticket is None or ticket.ticket_id != ticket_id:
            raise RuntimeError("A1-R2 cancellation ticket mismatch")
        self.pending_ticket = None
        self.cancelled_read_count += 1
        return {"ticket_id": ticket_id, "cancelled": True, "reason": str(reason)}

    def audit_record(self) -> dict[str, Any]:
        return {
            "schema": "a1r2_compact_verified_pending_audit_v1",
            "mechanism_id": MECHANISM_ID,
            "active": self.active is not None and self.nonempty_read_count > 0,
            "active_ledger": asdict(self.active) if self.active else None,
            "pending_ticket": asdict(self.pending_ticket) if self.pending_ticket else None,
            "last_committed_read": self._last_committed_read,
            "counters": {
                "read_call_count": self.read_call_count,
                "nonempty_read_count": self.nonempty_read_count,
                "injected_chars": self.injected_chars,
                "write_attempt_count": self.write_attempt_count,
                "write_success_count": self.write_success_count,
                "invalid_prefix_count": self.invalid_prefix_count,
                "clear_count": self.clear_count,
                "expiry_count": self.expiry_count,
                "replacement_count": self.replacement_count,
                "same_state_refresh_count": self.same_state_refresh_count,
                "cancelled_read_count": self.cancelled_read_count,
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
    "CompactVerifiedPendingMemory",
    "parse_memory_prefix",
]
