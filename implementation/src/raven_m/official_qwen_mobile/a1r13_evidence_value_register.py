"""A1-R13: R2 plus a bounded model-authored integer evidence register.

The R2 ledger remains the sole pending/verified memory.  This extension keeps
only explicit integer atoms from the model's own valid ``observed=`` field
when that same response says the pending work is both collecting/recording and
performing an arithmetic aggregation.  It never reads OCR, UI metadata,
evaluator state, or task identity and never computes or overrides an action.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import re
from typing import Any

from .a1r2_compact_verified_pending import (
    CompactVerifiedPendingMemory,
    MECHANISM_ID as R2_MECHANISM_ID,
    parse_memory_prefix,
)


MECHANISM_ID = "a1r13_evidence_value_register_v1"
EXPERIMENT_ID = "A1R13_EVR_QWEN3VL32B_AW_HARD_S20260806_G3407_V1"

_PREFIX = re.compile(
    r"^\s*MEMORY\[observed=(?P<observed>.*?);\s*"
    r"verified=(?P<verified>.*?);\s*pending=(?P<pending>.*?)\]\s*\|\s*"
    r"(?P<imperative>\S(?:.*\S)?)\s*$",
    re.DOTALL,
)
_INTEGER = re.compile(r"(?<![\w.])[-+]?\d{1,6}(?![\w.])")
_COLLECTION_CUES = ("record", "collect", "remember", "display")
_ARITHMETIC_CUES = ("product", "multiply", "sum", "total", "calculate")
_EVIDENCE_RENDER = (
    "TRANSIENT MODEL-AUTHORED EVIDENCE (unverified; current screenshot remains "
    "authoritative): observed integer sequence = [{values}]."
)


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _clean(value: str) -> str:
    return " ".join(str(value).split()).strip()


@dataclass(frozen=True)
class EvidenceAtom:
    value: str
    source_step: int
    source_call_id: str
    source_response_sha256: str
    source_screenshot_sha256: str
    observed_sha256: str
    pending_sha256: str


class EvidenceValueRegisterMemory(CompactVerifiedPendingMemory):
    """Exact R2 behavior plus one tiny, factual, episode-local value list."""

    mechanism_id = MECHANISM_ID

    def __init__(
        self,
        *,
        ttl_requests: int = 8,
        max_render_chars: int = 1100,
        evidence_ttl_requests: int = 8,
        max_evidence_values: int = 6,
        min_values_to_render: int = 2,
    ) -> None:
        super().__init__(
            ttl_requests=ttl_requests,
            max_render_chars=max_render_chars,
        )
        self.evidence_ttl_requests = max(2, int(evidence_ttl_requests))
        self.max_evidence_values = max(2, min(8, int(max_evidence_values)))
        self.min_values_to_render = max(2, int(min_values_to_render))
        self.evidence_values: list[EvidenceAtom] = []
        self.evidence_last_source_step: int | None = None
        self.evidence_activation_count = 0
        self.evidence_append_count = 0
        self.evidence_render_count = 0
        self.evidence_expiry_count = 0
        self.evidence_clear_count = 0
        self.evidence_capacity_suppression_count = 0
        self.evidence_rejection_count = 0
        self.evidence_write_events: list[dict[str, Any]] = []
        self.evidence_read_events: list[dict[str, Any]] = []

    @staticmethod
    def _candidate(action_summary: str) -> tuple[str, str] | None:
        match = _PREFIX.fullmatch(str(action_summary))
        if match is None:
            return None
        observed = _clean(match.group("observed"))
        pending = _clean(match.group("pending"))
        normalized_pending = pending.casefold()
        values = _INTEGER.findall(observed)
        if (
            len(values) != 1
            or not any(cue in normalized_pending for cue in _COLLECTION_CUES)
            or not any(cue in normalized_pending for cue in _ARITHMETIC_CUES)
        ):
            return None
        return values[0], observed

    def _clear_evidence(self, reason: str, source_step: int) -> None:
        if self.evidence_values:
            self.evidence_clear_count += 1
            self.evidence_write_events.append(
                {
                    "kind": "evidence_clear",
                    "reason": reason,
                    "source_step": int(source_step),
                    "cleared_value_count": len(self.evidence_values),
                }
            )
        self.evidence_values = []
        self.evidence_last_source_step = None

    def write(
        self,
        *,
        source_step: int,
        action_summary: str,
        source_call_id: str,
        source_response_sha256: str,
        source_screenshot_sha256: str,
    ) -> dict[str, Any]:
        base_event = super().write(
            source_step=source_step,
            action_summary=action_summary,
            source_call_id=source_call_id,
            source_response_sha256=source_response_sha256,
            source_screenshot_sha256=source_screenshot_sha256,
        )
        parsed = parse_memory_prefix(action_summary)
        evidence_event: dict[str, Any] = {
            "mechanism_id": MECHANISM_ID,
            "source_step": int(source_step),
            "accepted": False,
            "reason": None,
        }
        if parsed.valid and parsed.clear:
            self._clear_evidence("explicit_pending_clear", int(source_step))
            evidence_event["reason"] = "explicit_pending_clear"
        else:
            candidate = self._candidate(action_summary) if parsed.valid else None
            if candidate is None:
                self.evidence_rejection_count += 1
                evidence_event["reason"] = (
                    "invalid_prefix" if not parsed.valid else "not_single_integer_collection_arithmetic"
                )
            elif len(self.evidence_values) >= self.max_evidence_values:
                self.evidence_capacity_suppression_count += 1
                evidence_event["reason"] = "capacity_suppressed"
            else:
                value, observed = candidate
                if not self.evidence_values:
                    self.evidence_activation_count += 1
                atom = EvidenceAtom(
                    value=value,
                    source_step=int(source_step),
                    source_call_id=str(source_call_id),
                    source_response_sha256=str(source_response_sha256),
                    source_screenshot_sha256=str(source_screenshot_sha256),
                    observed_sha256=_digest(observed),
                    pending_sha256=_digest(str(parsed.pending)),
                )
                self.evidence_values.append(atom)
                self.evidence_last_source_step = int(source_step)
                self.evidence_append_count += 1
                evidence_event.update(
                    {
                        "accepted": True,
                        "reason": "model_authored_single_integer_appended",
                        "value": value,
                        "value_index": len(self.evidence_values) - 1,
                        "observed_sha256": atom.observed_sha256,
                        "pending_sha256": atom.pending_sha256,
                    }
                )
        self.evidence_write_events.append(evidence_event)
        event = dict(base_event)
        event["mechanism_id"] = MECHANISM_ID
        event["base_mechanism_id"] = base_event.get("mechanism_id")
        event["evidence_value_register"] = evidence_event
        return event

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        request_step = self.read_call_count
        if (
            self.evidence_values
            and self.evidence_last_source_step is not None
            and request_step - self.evidence_last_source_step >= self.evidence_ttl_requests
        ):
            self.evidence_expiry_count += 1
            self._clear_evidence("evidence_ttl_expired", request_step)
        text, audit = super().read(context=context)
        audit = dict(audit)
        audit["mechanism_id"] = MECHANISM_ID
        audit["base_mechanism_id"] = R2_MECHANISM_ID
        evidence_audit: dict[str, Any] = {
            "request_step": request_step,
            "value_count": len(self.evidence_values),
            "rendered": False,
            "values_sha256": canonical_values_sha256(self.evidence_values),
        }
        if text and len(self.evidence_values) >= self.min_values_to_render:
            suffix = _EVIDENCE_RENDER.format(
                values=", ".join(atom.value for atom in self.evidence_values)
            )
            candidate = text + "\n" + suffix
            if len(candidate) <= self.max_render_chars:
                text = candidate
                ticket = self.pending_ticket
                if ticket is None:
                    raise RuntimeError("A1-R13 evidence render missing R2 ticket")
                ticket.text = text
                ticket.text_sha256 = _digest(text)
                audit["rendered_chars"] = len(text)
                audit["rendered_sha256"] = ticket.text_sha256
                audit["exact_injected_text"] = text
                self.evidence_render_count += 1
                evidence_audit.update(
                    {
                        "rendered": True,
                        "exact_text": suffix,
                        "exact_text_sha256": _digest(suffix),
                        "rendered_value_count": len(self.evidence_values),
                    }
                )
            else:
                evidence_audit["reason"] = "combined_render_boundary_fail_closed"
        else:
            evidence_audit["reason"] = (
                "base_memory_empty" if not text else "insufficient_values"
            )
        self.evidence_read_events.append(evidence_audit)
        audit["evidence_value_register"] = evidence_audit
        return text, audit

    def audit_record(self) -> dict[str, Any]:
        audit = super().audit_record()
        audit["schema"] = "a1r13_evidence_value_register_audit_v1"
        audit["mechanism_id"] = MECHANISM_ID
        audit["base_mechanism_id"] = R2_MECHANISM_ID
        audit["evidence_register"] = {
            "values": [asdict(atom) for atom in self.evidence_values],
            "last_source_step": self.evidence_last_source_step,
            "write_events": list(self.evidence_write_events),
            "read_events": list(self.evidence_read_events),
            "counters": {
                "activation_count": self.evidence_activation_count,
                "append_count": self.evidence_append_count,
                "render_count": self.evidence_render_count,
                "expiry_count": self.evidence_expiry_count,
                "clear_count": self.evidence_clear_count,
                "capacity_suppression_count": self.evidence_capacity_suppression_count,
                "rejection_count": self.evidence_rejection_count,
            },
            "limits": {
                "max_values": self.max_evidence_values,
                "min_values_to_render": self.min_values_to_render,
                "ttl_requests": self.evidence_ttl_requests,
            },
        }
        audit["decision_boundary"] = {
            "extra_model_calls": 0,
            "action_override_count": 0,
            "forced_termination_count": 0,
            "hidden_ui_used_for_decision": False,
            "evaluator_used_for_decision": False,
            "task_name_rules": False,
            "screen_text_or_ocr_used": False,
            "values_are_model_authored_only": True,
        }
        return audit


def canonical_values_sha256(values: list[EvidenceAtom]) -> str:
    return _digest("\n".join(atom.value for atom in values))


__all__ = [
    "EXPERIMENT_ID",
    "MECHANISM_ID",
    "EvidenceAtom",
    "EvidenceValueRegisterMemory",
    "canonical_values_sha256",
]
