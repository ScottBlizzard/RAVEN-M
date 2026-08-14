"""A1-R5 transition-invalidated writer-resilient pending memory.

R5 makes one prospective change to R4: an invalid writer prefix may not carry
semantic memory across a material visible transition.  The old ledger is
retired after that transition, so the next request receives only the frozen
writer reminder and must author a current-screen ledger.
"""

from __future__ import annotations

from typing import Any

from .a1r4_writer_resilient_pending import (
    WRITER_REMINDER,
    WriterResilientPendingMemory,
    canonical_action_family,
    parse_memory_prefix,
)


MECHANISM_ID = "a1r5_transition_invalidated_pending_v1"
EXPERIMENT_ID = "A1R5_TIPL_QWEN3VL32B_AW_HARD_T20260806_G3407_V1"


class TransitionInvalidatedPendingMemory(WriterResilientPendingMemory):
    """R4 plus deterministic stale-ledger retirement on visible navigation."""

    mechanism_id = MECHANISM_ID

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.counters["transition_invalidation_count"] = 0

    def observe_step(self, **kwargs: Any) -> dict[str, Any]:
        event = super().observe_step(**kwargs)
        event["mechanism_id"] = MECHANISM_ID
        if (
            event.get("prefix_valid") is False
            and event.get("visible_outcome") == "material_rgb_change"
            and self.active is not None
        ):
            retired_id = self._retire_active()
            self.counters["transition_invalidation_count"] += 1
            event.update(
                {
                    "write_kind": "invalid_prefix_transition_invalidated",
                    "transition_invalidated_ledger_id": retired_id,
                }
            )
        return event

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        text, audit = super().read(context)
        audit["mechanism_id"] = MECHANISM_ID
        return text, audit

    def commit_injection(self, ticket_id: str, final_prompt_sha256: str) -> dict[str, Any]:
        event = super().commit_injection(ticket_id, final_prompt_sha256)
        event["mechanism_id"] = MECHANISM_ID
        return event

    def audit_record(self) -> dict[str, Any]:
        audit = super().audit_record()
        audit.update(
            {
                "schema": "a1r5_transition_invalidated_pending_audit_v1",
                "mechanism_id": MECHANISM_ID,
            }
        )
        if audit.get("last_committed_read"):
            audit["last_committed_read"]["mechanism_id"] = MECHANISM_ID
        return audit


__all__ = [
    "EXPERIMENT_ID",
    "MECHANISM_ID",
    "WRITER_REMINDER",
    "TransitionInvalidatedPendingMemory",
    "canonical_action_family",
    "parse_memory_prefix",
]
