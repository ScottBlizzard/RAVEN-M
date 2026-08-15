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


SYSTEM_ID = "sys_r2_numeric_answer_consistency_guard_v1"
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
    """One-way, auditable correction of explicit duration-sum arithmetic."""

    def __init__(self) -> None:
        self.review_count = 0
        self.eligible_count = 0
        self.override_count = 0
        self.events: list[dict[str, Any]] = []

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
        event: dict[str, Any] = {
            "system_id": SYSTEM_ID,
            "review_index": self.review_count - 1,
            "eligible": False,
            "overridden": False,
            "reason": "not_integer_answer",
            "proposed_action": proposed,
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

    def audit_record(self) -> dict[str, Any]:
        return {
            "schema": "sys_r2_numeric_answer_guard_audit_v1",
            "system_id": SYSTEM_ID,
            "counters": {
                "review_count": self.review_count,
                "eligible_count": self.eligible_count,
                "action_override_count": self.override_count,
                "extra_model_calls": 0,
                "forced_termination_count": 0,
                "hidden_ui_used_for_decision": False,
                "evaluator_used_for_decision": False,
            },
            "events": list(self.events),
        }


__all__ = ["DurationEvidence", "NumericAnswerConsistencyGuard", "SYSTEM_ID"]
