"""A1-R14: retain explicit value observations from the model's full response."""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import re
from typing import Any

from .a1r13_evidence_value_register import (
    EvidenceAtom,
    EvidenceValueRegisterMemory,
)


MECHANISM_ID = "a1r14_response_grounded_value_register_v1"
EXPERIMENT_ID = "A1R14_RGVR_QWEN3VL32B_AW_HARD_S20260806_G3407_V1"

_INTEGER = r"([-+]?\d{1,6})"
_OBSERVATION_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        rf"\bnumber\s+['\"]?{_INTEGER}['\"]?\s+is\s+(?:shown|displayed)\b",
        rf"\bcurrent\s+number(?:\s+shown)?\s+is\s+['\"]?{_INTEGER}['\"]?",
        rf"\bseen\s+the\s+number\s+['\"]?{_INTEGER}['\"]?",
        rf"\bcurrent\s+screen\s+shows\s+the\s+number\s+['\"]?{_INTEGER}['\"]?",
    )
)
_GOAL_COLLECTION = ("remember", "record", "collect")
_GOAL_ARITHMETIC = ("product", "multiply", "sum", "total", "calculate")
_RESPONSE_COLLECTION = ("remember", "record", "collect", "all five numbers", "numbers needed")


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


class ResponseGroundedValueRegisterMemory(EvidenceValueRegisterMemory):
    """R13 EVR with a bounded model-response observation fallback."""

    mechanism_id = MECHANISM_ID

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.goal_eligible = False
        self.goal_sha256: str | None = None
        self.response_write_attempt_count = 0
        self.response_append_count = 0
        self.response_duplicate_suppression_count = 0
        self.response_rejection_count = 0
        self.response_write_events: list[dict[str, Any]] = []

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        goal = " ".join(str((context or {}).get("goal") or "").split()).casefold()
        self.goal_sha256 = _digest(goal) if goal else None
        self.goal_eligible = bool(
            goal
            and any(cue in goal for cue in _GOAL_COLLECTION)
            and any(cue in goal for cue in _GOAL_ARITHMETIC)
        )
        text, audit = super().read(context=context)
        audit = dict(audit)
        audit["mechanism_id"] = MECHANISM_ID
        audit["response_grounded_value_register"] = {
            "goal_eligible": self.goal_eligible,
            "goal_sha256": self.goal_sha256,
            "response_append_count": self.response_append_count,
        }
        return text, audit

    @staticmethod
    def _response_candidate(model_response: str) -> tuple[str, str] | None:
        thought = str(model_response).split("\nAction:", 1)[0]
        normalized = " ".join(thought.split())
        lowered = normalized.casefold()
        if not any(cue in lowered for cue in _RESPONSE_COLLECTION):
            return None
        matches: list[tuple[str, str]] = []
        for pattern in _OBSERVATION_PATTERNS:
            for match in pattern.finditer(normalized):
                matches.append((match.group(1), match.group(0)))
        unique_values = list(dict.fromkeys(value for value, _ in matches))
        if len(unique_values) != 1:
            return None
        value = unique_values[0]
        phrase = next(phrase for candidate, phrase in matches if candidate == value)
        return value, phrase

    def write_model_response(
        self,
        *,
        source_step: int,
        model_response: str,
        action_summary: str,
        source_call_id: str,
        source_response_sha256: str,
        source_screenshot_sha256: str,
    ) -> dict[str, Any]:
        self.response_write_attempt_count += 1
        event: dict[str, Any] = {
            "mechanism_id": MECHANISM_ID,
            "source_step": int(source_step),
            "accepted": False,
            "source_channel": "model_response_thought",
        }
        if any(atom.source_step == int(source_step) for atom in self.evidence_values):
            self.response_duplicate_suppression_count += 1
            event["reason"] = "same_response_already_accepted_from_action_prefix"
        elif not self.goal_eligible:
            self.response_rejection_count += 1
            event["reason"] = "goal_not_collection_arithmetic"
        else:
            candidate = self._response_candidate(model_response)
            if candidate is None:
                self.response_rejection_count += 1
                event["reason"] = "no_unique_explicit_observation_phrase"
            elif len(self.evidence_values) >= self.max_evidence_values:
                self.evidence_capacity_suppression_count += 1
                event["reason"] = "capacity_suppressed"
            else:
                value, phrase = candidate
                if not self.evidence_values:
                    self.evidence_activation_count += 1
                atom = EvidenceAtom(
                    value=value,
                    source_step=int(source_step),
                    source_call_id=str(source_call_id),
                    source_response_sha256=str(source_response_sha256),
                    source_screenshot_sha256=str(source_screenshot_sha256),
                    observed_sha256=_digest(phrase),
                    pending_sha256=str(self.goal_sha256 or ""),
                )
                self.evidence_values.append(atom)
                self.evidence_last_source_step = int(source_step)
                self.evidence_append_count += 1
                self.response_append_count += 1
                event.update(
                    {
                        "accepted": True,
                        "reason": "model_response_explicit_observation_appended",
                        "value": value,
                        "value_index": len(self.evidence_values) - 1,
                        "observation_phrase_sha256": atom.observed_sha256,
                        "goal_sha256": self.goal_sha256,
                    }
                )
        self.response_write_events.append(event)
        return event

    def audit_record(self) -> dict[str, Any]:
        audit = super().audit_record()
        audit["schema"] = "a1r14_response_grounded_value_register_audit_v1"
        audit["mechanism_id"] = MECHANISM_ID
        audit["response_grounding"] = {
            "goal_eligible": self.goal_eligible,
            "goal_sha256": self.goal_sha256,
            "write_events": list(self.response_write_events),
            "counters": {
                "write_attempt_count": self.response_write_attempt_count,
                "append_count": self.response_append_count,
                "duplicate_suppression_count": self.response_duplicate_suppression_count,
                "rejection_count": self.response_rejection_count,
            },
            "retained_values": [asdict(atom) for atom in self.evidence_values],
        }
        audit["decision_boundary"]["full_model_response_used"] = True
        audit["decision_boundary"]["model_authored_text_only"] = True
        return audit


__all__ = ["EXPERIMENT_ID", "MECHANISM_ID", "ResponseGroundedValueRegisterMemory"]
