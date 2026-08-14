"""A1-R4 writer-resilient stale-resistant pending memory.

R4 retains the complete A1-R3 semantic lifecycle but keeps one short output-
format reminder in the prompt.  The reminder is an interface intervention,
not a semantic memory fact, and is audited separately from ledger exposure.
"""

from __future__ import annotations

from typing import Any

from .a1r3_stale_resistant_pending import (
    _BASE_RENDER,
    _FAILURE_LINE,
    _digest,
    ReadTicket,
    StaleResistantPendingMemory,
    canonical_action_family,
    parse_memory_prefix,
)


MECHANISM_ID = "a1r4_writer_resilient_pending_v1"
EXPERIMENT_ID = "A1R4_WRPL_QWEN3VL32B_AW_HARD_T20260806_G3407_V1"

WRITER_REMINDER = (
    "OUTPUT FORMAT REMINDER: Begin the Action sentence exactly with "
    "MEMORY[observed=<visible facts or none>; verified=<visibly confirmed "
    "requirements or none>; pending=<most important unmet requirement>] | "
    "before the UI imperative."
)


class WriterResilientPendingMemory(StaleResistantPendingMemory):
    """R3 lifecycle plus an always-near-output writer-format reminder."""

    mechanism_id = MECHANISM_ID

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.counters["writer_reminder_read_count"] = 0
        self.counters["semantic_memory_read_count"] = 0

    def observe_step(self, **kwargs: Any) -> dict[str, Any]:
        event = super().observe_step(**kwargs)
        event["mechanism_id"] = MECHANISM_ID
        return event

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        del context
        if self.pending_ticket is not None:
            raise RuntimeError("A1-R4 read ticket was not committed or cancelled")
        request_step = self.counters["read_call_count"]
        self.counters["read_call_count"] += 1
        expired_id = None
        if self.active is not None and request_step - self.active.source_step >= self.ttl_requests:
            expired_id = self._retire_active()
            self.counters["expiry_count"] += 1

        semantic = self.active is not None
        pieces: list[str] = []
        if semantic:
            pieces.append(
                _BASE_RENDER.format(
                    verified=self.active.verified,
                    pending=self.active.pending,
                )
            )
            if (
                self.failed_attempt is not None
                and self.failed_attempt.state_key == self.active.state_key
            ):
                pieces.append(_FAILURE_LINE.strip().format(label=self.failed_attempt.label))
        if not semantic:
            pieces.append(WRITER_REMINDER)
        text = "\n".join(pieces)
        audit: dict[str, Any] = {
            "mechanism_id": MECHANISM_ID,
            "request_step": request_step,
            "nonempty": True,
            "reason": "prepared_writer_reminder_with_semantic_memory"
            if semantic
            else "prepared_writer_reminder_only",
            "writer_reminder_injected": not semantic,
            "semantic_memory_injected": semantic,
            "expired_ledger_id": expired_id,
        }
        if len(text) > self.max_render_chars:
            audit.update({"nonempty": False, "reason": "render_boundary_fail_closed"})
            return "", audit
        ledger_id = self.active.ledger_id if self.active is not None else "writer_protocol"
        ticket = ReadTicket(
            ticket_id=self._id("wrplread"),
            request_step=request_step,
            ledger_id=ledger_id,
            text=text,
            text_sha256=_digest(text),
        )
        self.pending_ticket = ticket
        failure = bool(
            semantic
            and self.failed_attempt is not None
            and self.failed_attempt.state_key == self.active.state_key
        )
        audit.update(
            {
                "ticket_id": ticket.ticket_id,
                "ledger_id": ticket.ledger_id,
                "rendered_chars": len(text),
                "rendered_sha256": ticket.text_sha256,
                "failure_evidence_injected": failure,
                "failed_action_family": self.failed_attempt.action_family if failure else None,
                "failure_second_support_step": (
                    self.failed_attempt.second_support_step if failure else None
                ),
            }
        )
        return text, audit

    def commit_injection(self, ticket_id: str, final_prompt_sha256: str) -> dict[str, Any]:
        semantic = bool(self.pending_ticket and self.pending_ticket.ledger_id != "writer_protocol")
        event = super().commit_injection(ticket_id, final_prompt_sha256)
        self.counters["writer_reminder_read_count"] += int(not semantic)
        self.counters["semantic_memory_read_count"] += int(semantic)
        event.update(
            {
                "mechanism_id": MECHANISM_ID,
                "writer_reminder_injected": not semantic,
                "semantic_memory_injected": semantic,
            }
        )
        return event

    def audit_record(self) -> dict[str, Any]:
        audit = super().audit_record()
        audit.update(
            {
                "schema": "a1r4_writer_resilient_pending_audit_v1",
                "mechanism_id": MECHANISM_ID,
                "active": self.counters["semantic_memory_read_count"] > 0,
                "writer_interface_active": self.counters["writer_reminder_read_count"] > 0,
            }
        )
        return audit


__all__ = [
    "EXPERIMENT_ID",
    "MECHANISM_ID",
    "WRITER_REMINDER",
    "WriterResilientPendingMemory",
    "canonical_action_family",
    "parse_memory_prefix",
]
