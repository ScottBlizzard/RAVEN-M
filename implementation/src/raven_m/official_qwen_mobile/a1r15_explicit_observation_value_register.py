"""A1-R15: narrow live-grounded expansion of the R14 observation grammar."""

from __future__ import annotations

import re

from .a1r14_response_value_register import ResponseGroundedValueRegisterMemory


MECHANISM_ID = "a1r15_explicit_observation_value_register_v1"
EXPERIMENT_ID = "A1R15_EOVR_QWEN3VL32B_AW_HARD_S20260806_G3407_V1"

_INTEGER = r"([-+]?\d{1,6})"
_OBSERVATION_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        rf"\bnumber\s+['\"]?{_INTEGER}['\"]?\s+is\s+(?:shown|displayed)\b",
        rf"\bcurrent\s+number(?:\s+shown)?\s+is\s+['\"]?{_INTEGER}['\"]?",
        rf"\bseen\s+the\s+number\s+['\"]?{_INTEGER}['\"]?",
        rf"\bcurrent\s+screen\s+shows\s+the\s+number\s+['\"]?{_INTEGER}['\"]?",
        rf"\bnumber\s+['\"]?{_INTEGER}['\"]?\s+displayed\b",
        rf"\bcurrent\s+number\s+displayed\s+is\s+['\"]?{_INTEGER}['\"]?",
    )
)
_RESPONSE_COLLECTION = ("remember", "record", "collect", "all five numbers", "numbers needed")


class ExplicitObservationValueRegisterMemory(ResponseGroundedValueRegisterMemory):
    """R14 with only the two phrase shapes observed in its sealed live failure."""

    mechanism_id = MECHANISM_ID

    def read(self, context: dict | None = None) -> tuple[str, dict]:
        text, audit = super().read(context=context)
        audit = dict(audit)
        audit["mechanism_id"] = MECHANISM_ID
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

    def write_model_response(self, **kwargs) -> dict:
        event = super().write_model_response(**kwargs)
        event["mechanism_id"] = MECHANISM_ID
        return event

    def audit_record(self) -> dict:
        audit = super().audit_record()
        audit["schema"] = "a1r15_explicit_observation_value_register_audit_v1"
        audit["mechanism_id"] = MECHANISM_ID
        audit["decision_boundary"]["grammar_delta"] = "sealed_a1r14_live_phrase_shapes_only"
        return audit


__all__ = ["EXPERIMENT_ID", "MECHANISM_ID", "ExplicitObservationValueRegisterMemory"]
