"""A1-R6 goal-anchored transition-invalidated pending memory."""

from __future__ import annotations

from typing import Any

from .a1r3_stale_resistant_pending import _digest
from .a1r5_transition_invalidated_pending import (
    TransitionInvalidatedPendingMemory,
    WRITER_REMINDER,
    canonical_action_family,
    parse_memory_prefix,
)

MECHANISM_ID = "a1r6_goal_anchored_pending_v1"
EXPERIMENT_ID = "A1R6_GAPL_QWEN3VL32B_AW_HARD_T20260806_G3407_V1"

GOAL_INVARIANT = (
    "ORIGINAL GOAL REQUIREMENTS: {goal}\n"
    "Keep every requirement pending until it is visibly confirmed complete. "
    "Locating or opening an item is not completion."
)


class GoalAnchoredPendingMemory(TransitionInvalidatedPendingMemory):
    """R5 plus a bounded goal invariant attached to every committed read."""

    mechanism_id = MECHANISM_ID

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.counters["goal_anchored_read_count"] = 0

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        context = context or {}
        text, audit = super().read(context)
        audit["mechanism_id"] = MECHANISM_ID
        goal = " ".join(str(context.get("goal") or "").split())[:320]
        if not text or not goal or self.pending_ticket is None:
            return text, audit
        anchored = text + "\n" + GOAL_INVARIANT.format(goal=goal)
        if len(anchored) > self.max_render_chars:
            self.cancel_injection(str(audit["ticket_id"]), "goal_anchor_render_boundary")
            audit.update({"nonempty": False, "reason": "goal_anchor_render_boundary_fail_closed"})
            return "", audit
        self.pending_ticket.text = anchored
        self.pending_ticket.text_sha256 = _digest(anchored)
        audit.update(
            {
                "rendered_chars": len(anchored),
                "rendered_sha256": self.pending_ticket.text_sha256,
                "goal_anchor_injected": True,
            }
        )
        return anchored, audit

    def commit_injection(self, ticket_id: str, final_prompt_sha256: str) -> dict[str, Any]:
        event = super().commit_injection(ticket_id, final_prompt_sha256)
        self.counters["goal_anchored_read_count"] += 1
        event.update({"mechanism_id": MECHANISM_ID, "goal_anchor_injected": True})
        return event

    def observe_step(self, **kwargs: Any) -> dict[str, Any]:
        event = super().observe_step(**kwargs); event["mechanism_id"] = MECHANISM_ID; return event

    def audit_record(self) -> dict[str, Any]:
        audit = super().audit_record()
        audit.update({"schema": "a1r6_goal_anchored_pending_audit_v1", "mechanism_id": MECHANISM_ID})
        if audit.get("last_committed_read"): audit["last_committed_read"]["mechanism_id"] = MECHANISM_ID
        return audit


__all__ = ["EXPERIMENT_ID", "GOAL_INVARIANT", "MECHANISM_ID", "GoalAnchoredPendingMemory", "WRITER_REMINDER", "canonical_action_family", "parse_memory_prefix"]
