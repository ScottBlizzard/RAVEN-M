"""Bounded Pending Receipt v2: one sparse, model-authored pending receipt."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
import unicodedata
from typing import Any


MECHANISM_ID = "a1r1_bounded_pending_receipt_v2"
PRIMARY_EXPERIMENT_ID = "A1R1_BPRV2_QWEN3VL32B_AW_HARD_T20260806_G3407_V1"
EMPTY_EXPERIMENT_ID = "A1R1_BPRV2_EMPTYREAD_QWEN3VL32B_AW_HARD_T20260806_G3407_V1"

ACTION_PREFIX_PATTERN = re.compile(
    r"^PEND\[op=(?P<op>[^\]\;\|\r\n]+);proof=(?P<proof>[^\]\;\|\r\n]+)\] \| "
    r"(?P<imperative>\S(?:.*\S)?)$"
)

RENDERER_TEMPLATE = (
    "PENDING, NOT PROOF: {op}\n"
    "VISIBLE PROOF NEEDED: {proof}\n"
    "Current screenshot overrides this. Check it first; do not repeat solely "
    "because this is pending."
)

A1R1_BPR_V2_SUFFIX = """

# A1-R1 bounded pending receipt v2

Begin every Action sentence, including answer or terminate steps, with exactly:
PEND[op=<one still-unconfirmed operation or none>;proof=<one visible fact that would confirm it or none>] | <one concise UI imperative>

Rules:
- Use non-none only for one task-state change attempted by this Action or still awaiting visible confirmation. Carry the same pair until confirmed; op=none;proof=none clears it.
- Each field: at most 100 characters and 128 UTF-8 bytes; no ], ;, |, or line break. Keep exact names and values.
- A click or page change is not proof.
- The current screenshot overrides the receipt. Never repeat solely because it says pending.
"""


def _digest_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _canonical_json_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _normalize_field(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = " ".join(normalized.split()).strip()
    if not normalized or len(normalized) > 100:
        raise ValueError("field_codepoint_boundary")
    if len(normalized.encode("utf-8")) > 128:
        raise ValueError("field_utf8_boundary")
    if any(char in normalized for char in "];|\r\n\0"):
        raise ValueError("field_forbidden_delimiter")
    if any(unicodedata.category(char) == "Cc" for char in normalized):
        raise ValueError("field_control_character")
    return normalized


def _op_key(value: str) -> str:
    return _digest_text(" ".join(value.split()).strip().casefold())


@dataclass
class ParsedPrefix:
    valid: bool
    history: str
    pair_valid: bool = False
    clear: bool = False
    op: str | None = None
    proof: str | None = None
    error: str | None = None


def parse_pend(action_summary: str) -> ParsedPrefix:
    match = ACTION_PREFIX_PATTERN.fullmatch(str(action_summary))
    if match is None:
        return ParsedPrefix(False, str(action_summary), error="invalid_prefix")
    imperative = match.group("imperative").strip()
    try:
        op = _normalize_field(match.group("op"))
        proof = _normalize_field(match.group("proof"))
    except ValueError as exc:
        return ParsedPrefix(False, str(action_summary), error=str(exc))
    op_none = op == "none"
    proof_none = proof == "none"
    if op_none != proof_none:
        return ParsedPrefix(
            True,
            imperative,
            pair_valid=False,
            op=op,
            proof=proof,
            error="exactly_one_none",
        )
    return ParsedPrefix(
        True,
        imperative,
        pair_valid=True,
        clear=op_none,
        op=op,
        proof=proof,
    )


@dataclass
class ActiveReceipt:
    receipt_id: str
    op: str
    proof: str
    op_key_sha256: str
    first_source_step: int
    expiry_before_read_step: int
    read_count: int = 0
    last_read_step: int | None = None
    last_read_pixel_sha256: str | None = None
    text_version_event_id: str = ""


@dataclass
class Tombstone:
    op_key_sha256: str
    retired_step: int
    reason: str


@dataclass
class PendingTicket:
    ticket_id: str
    request_step: int
    receipt_id: str
    text_version_event_id: str
    current_rgb_sha256: str
    text: str
    text_sha256: str
    chars: int
    utf8_bytes: int


COUNTER_NAMES = (
    "read_call_count",
    "nonempty_read_count",
    "injected_chars",
    "injected_utf8_bytes",
    "injected_model_token_upper_bound",
    "write_attempt_count",
    "write_accept_count",
    "same_op_no_refresh_count",
    "same_op_text_update_count",
    "explicit_clear_count",
    "replacement_count",
    "expiry_count",
    "same_rgb_suppression_count",
    "cooldown_suppression_count",
    "receipt_read_cap_count",
    "episode_budget_suppression_count",
    "refractory_reject_count",
    "invalid_prefix_count",
    "invalid_pair_count",
    "prepared_read_count",
    "cancelled_read_count",
)


class BoundedPendingReceiptV2:
    """The exact bounded BPR-v2 state machine.

    Resident state stays bounded. Detailed events are returned to the controller
    and written in the episode record rather than retained without bound.
    """

    def __init__(self, *, read_enabled: bool = True) -> None:
        self.read_enabled = bool(read_enabled)
        self.active: ActiveReceipt | None = None
        self.tombstone: Tombstone | None = None
        self.last_nonempty_read_step: int | None = None
        self.pending_ticket: PendingTicket | None = None
        self.counters = {name: 0 for name in COUNTER_NAMES}
        self._event_serial = 0
        self._last_committed_read: dict[str, Any] | None = None

    def _fresh_id(self, prefix: str) -> str:
        self._event_serial += 1
        return f"{prefix}_{self._event_serial:04d}"

    def _retire(self, step: int, reason: str) -> dict[str, Any] | None:
        if self.active is None:
            return None
        retired = self.active
        self.tombstone = Tombstone(retired.op_key_sha256, int(step), reason)
        self.active = None
        if reason == "expiry":
            self.counters["expiry_count"] += 1
        elif reason == "replacement":
            self.counters["replacement_count"] += 1
        elif reason == "explicit_clear":
            self.counters["explicit_clear_count"] += 1
        return {"receipt_id": retired.receipt_id, "reason": reason}

    def history_summary(self, action_summary: str) -> str:
        return parse_pend(action_summary).history

    def read(self, context: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        if self.pending_ticket is not None:
            raise RuntimeError("BPR read ticket was not committed or cancelled")
        request_step = self.counters["read_call_count"]
        self.counters["read_call_count"] += 1
        current_rgb = str((context.get("before") or {}).get("pixel_sha256") or "")
        audit: dict[str, Any] = {
            "mechanism_id": MECHANISM_ID,
            "request_step": request_step,
            "read_enabled": self.read_enabled,
            "nonempty": False,
            "reason": None,
            "ticket_id": None,
            "current_rgb_sha256": current_rgb,
        }
        if self.active is not None and request_step >= self.active.expiry_before_read_step:
            audit["retirement"] = self._retire(request_step, "expiry")
        if not self.read_enabled:
            audit["reason"] = "empty_read_ablation"
            return "", audit
        if self.active is None:
            audit["reason"] = "no_active_receipt"
            return "", audit
        if self.active.read_count >= 2:
            audit["reason"] = "receipt_read_cap"
            return "", audit
        if self.counters["nonempty_read_count"] >= 8:
            self.counters["episode_budget_suppression_count"] += 1
            audit["retirement"] = self._retire(request_step, "episode_budget")
            audit["reason"] = "episode_read_cap"
            return "", audit
        if (
            self.last_nonempty_read_step is not None
            and request_step - self.last_nonempty_read_step < 2
        ):
            self.counters["cooldown_suppression_count"] += 1
            audit["reason"] = "cooldown"
            return "", audit
        if self.active.last_read_pixel_sha256 == current_rgb:
            self.counters["same_rgb_suppression_count"] += 1
            audit["reason"] = "same_rgb"
            return "", audit
        text = RENDERER_TEMPLATE.format(op=self.active.op, proof=self.active.proof)
        chars = len(text)
        bytes_ = len(text.encode("utf-8"))
        if chars > 340 or bytes_ > 396:
            raise RuntimeError("BPR renderer boundary violation")
        if self.counters["injected_chars"] + chars > 2720:
            audit["reason"] = "episode_char_budget"
            return "", audit
        if self.counters["injected_utf8_bytes"] + bytes_ > 3168:
            audit["reason"] = "episode_byte_budget"
            return "", audit
        if self.counters["injected_model_token_upper_bound"] + bytes_ > 3168:
            audit["reason"] = "episode_token_budget"
            return "", audit
        ticket = PendingTicket(
            ticket_id=self._fresh_id("bpr2read"),
            request_step=request_step,
            receipt_id=self.active.receipt_id,
            text_version_event_id=self.active.text_version_event_id,
            current_rgb_sha256=current_rgb,
            text=text,
            text_sha256=_digest_text(text),
            chars=chars,
            utf8_bytes=bytes_,
        )
        self.pending_ticket = ticket
        self.counters["prepared_read_count"] += 1
        audit.update(
            {
                "nonempty": True,
                "reason": "prepared_not_consumed",
                "ticket_id": ticket.ticket_id,
                "receipt_id": ticket.receipt_id,
                "text_version_event_id": ticket.text_version_event_id,
                "rendered_sha256": ticket.text_sha256,
                "rendered_chars": chars,
                "rendered_utf8_bytes": bytes_,
            }
        )
        return text, audit

    def commit_injection(
        self, ticket_id: str, final_prompt_sha256: str
    ) -> dict[str, Any]:
        ticket = self.pending_ticket
        if ticket is None or ticket.ticket_id != ticket_id:
            raise RuntimeError("BPR injection ticket mismatch")
        if self.active is None or self.active.receipt_id != ticket.receipt_id:
            raise RuntimeError("BPR receipt changed before injection commit")
        self.active.read_count += 1
        self.active.last_read_step = ticket.request_step
        self.active.last_read_pixel_sha256 = ticket.current_rgb_sha256
        self.last_nonempty_read_step = ticket.request_step
        self.counters["nonempty_read_count"] += 1
        self.counters["injected_chars"] += ticket.chars
        self.counters["injected_utf8_bytes"] += ticket.utf8_bytes
        self.counters["injected_model_token_upper_bound"] += ticket.utf8_bytes
        episode_budget_triggered = self.counters["nonempty_read_count"] == 8
        read_cap_triggered = self.active.read_count == 2
        if read_cap_triggered:
            self.counters["receipt_read_cap_count"] += 1
        retirement = None
        if episode_budget_triggered:
            retirement = self._retire(ticket.request_step, "episode_budget")
        elif read_cap_triggered:
            retirement = self._retire(ticket.request_step, "read_cap")
        event = {
            "ticket_id": ticket.ticket_id,
            "request_step": ticket.request_step,
            "receipt_id": ticket.receipt_id,
            "text_version_event_id": ticket.text_version_event_id,
            "exact_injected_text": ticket.text,
            "exact_injected_text_sha256": ticket.text_sha256,
            "final_prompt_sha256": str(final_prompt_sha256),
            "current_rgb_sha256": ticket.current_rgb_sha256,
            "chars": ticket.chars,
            "utf8_bytes": ticket.utf8_bytes,
            "episode_budget_triggered": episode_budget_triggered,
            "read_cap_triggered": read_cap_triggered,
            "retirement": retirement,
        }
        self.pending_ticket = None
        self._last_committed_read = event
        return event

    def cancel_injection(self, ticket_id: str, reason: str) -> dict[str, Any]:
        ticket = self.pending_ticket
        if ticket is None or ticket.ticket_id != ticket_id:
            raise RuntimeError("BPR cancellation ticket mismatch")
        self.pending_ticket = None
        self.counters["cancelled_read_count"] += 1
        return {"ticket_id": ticket_id, "cancelled": True, "reason": str(reason)}

    def observe_step(
        self,
        *,
        source_step: int,
        action_summary: str,
        canonical_action: Any,
        transition: dict[str, Any],
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        source_call_id: str,
        source_response_sha256: str,
        source_screenshot_sha256: str,
        **_: Any,
    ) -> dict[str, Any]:
        del canonical_action, transition, before, after
        self.counters["write_attempt_count"] += 1
        parsed = parse_pend(action_summary)
        event: dict[str, Any] = {
            "mechanism_id": MECHANISM_ID,
            "source_step": int(source_step),
            "source_call_id": str(source_call_id),
            "source_response_sha256": str(source_response_sha256),
            "source_screenshot_sha256": str(source_screenshot_sha256),
            "prefix_valid": parsed.valid,
            "pair_valid": parsed.pair_valid,
            "write_kind": None,
        }
        if not parsed.valid:
            self.counters["invalid_prefix_count"] += 1
            event["write_kind"] = "invalid_prefix_state_unchanged"
            return event
        if not parsed.pair_valid:
            self.counters["invalid_pair_count"] += 1
            event["write_kind"] = "invalid_pair_state_unchanged"
            return event
        if parsed.clear:
            event["retirement"] = self._retire(source_step, "explicit_clear")
            event["write_kind"] = "explicit_clear"
            return event
        assert parsed.op is not None and parsed.proof is not None
        key = _op_key(parsed.op)
        event.update(
            {
                "normalized_op": parsed.op,
                "normalized_proof": parsed.proof,
                "op_key_sha256": key,
            }
        )
        if (
            self.tombstone is not None
            and key == self.tombstone.op_key_sha256
            and source_step - self.tombstone.retired_step < 4
        ):
            self.counters["refractory_reject_count"] += 1
            event["write_kind"] = "refractory_reject_state_unchanged"
            return event
        if self.active is not None and key == self.active.op_key_sha256:
            if parsed.op == self.active.op and parsed.proof == self.active.proof:
                self.counters["same_op_no_refresh_count"] += 1
                event["write_kind"] = "same_op_same_text_no_refresh"
                return event
            self.active.op = parsed.op
            self.active.proof = parsed.proof
            self.active.text_version_event_id = self._fresh_id("bpr2text")
            self.counters["same_op_text_update_count"] += 1
            event["write_kind"] = "same_op_text_update_no_refresh"
            event["receipt_id"] = self.active.receipt_id
            return event
        if self.active is not None:
            event["retirement"] = self._retire(source_step, "replacement")
        receipt_id = f"bpr2_{source_step}_{key[:12]}"
        self.active = ActiveReceipt(
            receipt_id=receipt_id,
            op=parsed.op,
            proof=parsed.proof,
            op_key_sha256=key,
            first_source_step=int(source_step),
            expiry_before_read_step=int(source_step) + 5,
            text_version_event_id=self._fresh_id("bpr2text"),
        )
        self.counters["write_accept_count"] += 1
        event["write_kind"] = "new_receipt"
        event["receipt_id"] = receipt_id
        event["expiry_before_read_step"] = int(source_step) + 5
        return event

    def causal_state_projection(self) -> dict[str, Any]:
        return {
            "active": asdict(self.active) if self.active else None,
            "tombstone": asdict(self.tombstone) if self.tombstone else None,
        }

    def audit_record(self) -> dict[str, Any]:
        record = {
            "schema": "a1r1_bpr_v2_audit_v1",
            "mechanism_id": MECHANISM_ID,
            "read_enabled": self.read_enabled,
            "active": asdict(self.active) if self.active else None,
            "tombstone": asdict(self.tombstone) if self.tombstone else None,
            "counters": dict(self.counters),
            "nonempty_read_count": self.counters["nonempty_read_count"],
            "write_attempt_count": self.counters["write_attempt_count"],
            "write_success_count": self.counters["write_accept_count"],
            "rendered_chars_total": self.counters["injected_chars"],
            "pending_ticket": asdict(self.pending_ticket) if self.pending_ticket else None,
            "last_committed_read": self._last_committed_read,
            "decision_boundary": {
                "model_calls_added": 0,
                "guard_enabled": False,
                "action_override_count": 0,
                "forced_termination_count": 0,
                "hidden_ui_used_for_decision": False,
                "evaluator_used_for_decision": False,
                "future_information_used": False,
            },
        }
        record["canonical_state_sha256"] = _canonical_json_digest(
            {
                "active": record["active"],
                "tombstone": record["tombstone"],
                "counters": record["counters"],
            }
        )
        return record


__all__ = [
    "A1R1_BPR_V2_SUFFIX",
    "ACTION_PREFIX_PATTERN",
    "BoundedPendingReceiptV2",
    "EMPTY_EXPERIMENT_ID",
    "MECHANISM_ID",
    "PRIMARY_EXPERIMENT_ID",
    "RENDERER_TEMPLATE",
    "parse_pend",
]
