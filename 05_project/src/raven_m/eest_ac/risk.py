"""Shared deterministic trigger for action-conditioned verification."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


_HIGH_RISK_ACTION_INTENT_RE = re.compile(
    r"(?:^|[.;]\s*)"
    r"(?:tap|press|click|choose|select|activate)\s+(?:the\s+)?"
    r"(?P<control>save|send|delete|answer|done|submit)\b|"
    r"^\s*(?P<direct>save|send|delete|answer|finish|submit)\b",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class RiskTrigger:
    eligible: bool
    intent: str | None
    reason: str


class RiskDetector:
    """Gate consequences, not generic taps or reversible navigation."""

    ELIGIBLE_INTENTS = frozenset({"save", "send", "delete", "answer", "done"})

    def detect(self, decision: dict[str, Any]) -> RiskTrigger:
        status = str(decision.get("status", "")).casefold()
        action = decision.get("action")
        if status == "done":
            return RiskTrigger(True, "done", "terminal completion candidate")
        if isinstance(action, dict) and action.get("type") == "answer":
            return RiskTrigger(True, "answer", "benchmark answer candidate")
        # Detect the proposed action intent, not incidental past-tense wording
        # such as "open the message Avery sent" in an expected outcome.
        text = str(decision.get("decision_summary", ""))
        match = _HIGH_RISK_ACTION_INTENT_RE.search(text)
        if not match:
            return RiskTrigger(False, None, "reversible_or_nonconsequential")
        token = (match.group("control") or match.group("direct")).casefold()
        intent = {
            "submit": "done",
            "finish": "done",
        }.get(token, token)
        if intent not in self.ELIGIBLE_INTENTS:
            return RiskTrigger(False, None, "not_in_preregistered_intents")
        return RiskTrigger(True, intent, f"lexical_{intent}_candidate")
