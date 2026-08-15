"""Deterministic consistency guard for explicit additive duration answers.

The guard is deliberately narrow.  It never reads AndroidWorld state, task
identity, evaluator output, or future observations.  It only checks a proposed
integer ``answer`` against durations that the executor itself wrote in the
human-readable Action summary for the same request.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


SYSTEM_ID = "sys_r2_numeric_and_pending_terminal_guard_v3"
_INTEGER_RE = re.compile(r"^[+-]?\d+$")
_WORD_DURATION_RE = re.compile(
    r"(?<!\w)(\d{1,3})\s*hours?\s*(?:and\s*)?(\d{1,2})\s*minutes?(?!\w)",
    re.IGNORECASE,
)
_COLON_DURATION_RE = re.compile(
    r"(?<!\d)(\d{1,3}):(\d{2})(?::\d{2})?(?!\d)"
)
_ADDITIVE_CUE_RE = re.compile(r"\b(total|sum|calculate|combined|altogether)\b", re.IGNORECASE)


@dataclass(frozen=True)
class DurationEvidence:
    hours: int
    minutes: int

    @property
    def total_minutes(self) -> int:
        return self.hours * 60 + self.minutes


class NumericAnswerConsistencyGuard:
    """Two narrow, auditable checks layered on the frozen A1-R2 memory.

    The arithmetic rule is unchanged from SYS-NAG V2.  V3 additionally blocks
    at most one success termination when the exact R2 text injected into that
    request still contains a non-empty PENDING item and the immediately prior
    executed action was ``wait``.  Blocking does not invent or execute an
    Android action; it consumes the current decision slot and gives the normal
    executor one transparent request to inspect the authoritative screenshot.
    """

    def __init__(self) -> None:
        self.review_count = 0
        self.eligible_count = 0
        self.override_count = 0
        self.terminal_review_count = 0
        self.terminal_block_count = 0
        self.events: list[dict[str, Any]] = []
        self.terminal_events: list[dict[str, Any]] = []

    @staticmethod
    def _decision_clause(action_summary: str) -> str:
        # A1-R2 summaries may begin with ``MEMORY[...] |``.  The controller's
        # actual proposed operation is the final clause, which prevents the
        # same durations in the memory prefix from being counted twice.
        return str(action_summary).rsplit("|", 1)[-1].strip()

    @staticmethod
    def _durations(text: str) -> list[DurationEvidence]:
        word = [
            DurationEvidence(int(match.group(1)), int(match.group(2)))
            for match in _WORD_DURATION_RE.finditer(text)
            if 0 <= int(match.group(2)) < 60
        ]
        if word:
            return word
        return [
            DurationEvidence(int(match.group(1)), int(match.group(2)))
            for match in _COLON_DURATION_RE.finditer(text)
            if 0 <= int(match.group(2)) < 60
        ]

    def review(
        self,
        *,
        proposed_action: dict[str, Any] | None,
        action_summary: str,
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        self.review_count += 1
        proposed = dict(proposed_action) if isinstance(proposed_action, dict) else None
        clause = self._decision_clause(action_summary)
        model_proposed = dict(proposed) if proposed is not None else None
        event: dict[str, Any] = {
            "system_id": SYSTEM_ID,
            "review_index": self.review_count - 1,
            "eligible": False,
            "overridden": False,
            "reason": "not_integer_answer",
            "proposed_action": model_proposed,
            "decision_clause": clause,
        }
        if not proposed or proposed.get("type") != "answer":
            self.events.append(event)
            return proposed, event
        answer_text = str(proposed.get("text") or "").strip()
        if not _INTEGER_RE.fullmatch(answer_text):
            self.events.append(event)
            return proposed, event
        if not _ADDITIVE_CUE_RE.search(clause):
            event["reason"] = "no_additive_duration_cue"
            self.events.append(event)
            return proposed, event
        durations = self._durations(clause)
        if len(durations) < 2:
            event["reason"] = "fewer_than_two_explicit_durations"
            self.events.append(event)
            return proposed, event
        computed = sum(item.total_minutes for item in durations)
        if computed < 0 or computed > 1_000_000:
            event["reason"] = "computed_total_out_of_bounds"
            self.events.append(event)
            return proposed, event
        self.eligible_count += 1
        event.update(
            {
                "eligible": True,
                "reason": "already_consistent",
                "duration_minutes": [item.total_minutes for item in durations],
                "computed_total_minutes": computed,
                "proposed_integer": int(answer_text),
            }
        )
        if int(answer_text) != computed:
            proposed["text"] = str(computed)
            self.override_count += 1
            event.update(
                {
                    "overridden": True,
                    "reason": "explicit_duration_sum_mismatch",
                    "executed_action": dict(proposed),
                }
            )
        self.events.append(event)
        return proposed, event

    @staticmethod
    def _pending_line(memory_read: dict[str, Any] | None) -> str | None:
        if not isinstance(memory_read, dict):
            return None
        text = str(memory_read.get("exact_injected_text") or "")
        for line in text.splitlines():
            if line.startswith("PENDING:"):
                value = line.partition(":")[2].strip()
                if value and value.casefold() not in {"none", "null", "no pending"}:
                    return value
        return None

    def review_terminal(
        self,
        *,
        terminal_status: str | None,
        memory_read: dict[str, Any] | None,
        previous_executed_action: dict[str, Any] | None,
        remaining_native_decision_slots: int,
    ) -> dict[str, Any]:
        """Return a one-shot transparent block decision for a terminal claim."""

        self.terminal_review_count += 1
        pending = self._pending_line(memory_read)
        previous_type = (
            str(previous_executed_action.get("type") or "")
            if isinstance(previous_executed_action, dict)
            else ""
        )
        eligible = (
            terminal_status == "success"
            and pending is not None
            and previous_type == "wait"
            and self.terminal_block_count == 0
            and int(remaining_native_decision_slots) >= 1
        )
        event: dict[str, Any] = {
            "system_id": SYSTEM_ID,
            "terminal_review_index": self.terminal_review_count - 1,
            "terminal_status": terminal_status,
            "pending_from_exact_r2_read": pending,
            "previous_executed_action_type": previous_type or None,
            "remaining_native_decision_slots": int(remaining_native_decision_slots),
            "eligible": eligible,
            "blocked": False,
            "reason": "not_eligible",
        }
        if eligible:
            self.terminal_block_count += 1
            event.update(
                {
                    "blocked": True,
                    "reason": "pending_survived_wait_before_success_termination",
                    "history_message": (
                        "TERMINAL CONSISTENCY CHECK: The exact task ledger injected "
                        "for the rejected request still had a pending item, and the "
                        "last executed action was only wait. Inspect the current "
                        "screenshot and complete any visible confirmation before "
                        "terminating."
                    ),
                }
            )
        self.terminal_events.append(event)
        return event

    def audit_record(self) -> dict[str, Any]:
        return {
            "schema": "sys_nag_v3_composite_guard_audit_v1",
            "system_id": SYSTEM_ID,
            "counters": {
                "review_count": self.review_count,
                "eligible_count": self.eligible_count,
                "action_override_count": self.override_count,
                "terminal_review_count": self.terminal_review_count,
                "terminal_block_count": self.terminal_block_count,
                "auxiliary_model_call_count": 0,
                "guard_induced_continuation_request_upper_bound": (
                    self.terminal_block_count
                ),
                "forced_termination_count": 0,
                "hidden_ui_used_for_decision": False,
                "evaluator_used_for_decision": False,
            },
            "events": list(self.events),
            "terminal_events": list(self.terminal_events),
        }


__all__ = ["DurationEvidence", "NumericAnswerConsistencyGuard", "SYSTEM_ID"]
