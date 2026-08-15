"""A1-R3-v3 one-shot controller-authored nonprogress receipt.

The mechanism is a direct A1-R2 descendant.  A1-R2's model-authored compact
ledger is preserved exactly.  The only new state is one transient fact: two
consecutive actions from the same task-agnostic action family both produced no
material RGB transition.  That fact can be injected once on the next request.

No task name, goal parse, UI tree, package/activity, reward, evaluator output,
future frame, extra model call, action override, or forced termination is used.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from typing import Any

from .a1r2_compact_verified_pending import CompactVerifiedPendingMemory


MECHANISM_ID = "a1r3v3_one_shot_controller_nonprogress_receipt_v1"
EXPERIMENT_ID = "A1R3V3_OSCNR_QWEN3VL32B_AW_HARD_T20260806_G3407_V1"

NO_PROGRESS_PIXEL_FRACTION = 0.001
MAX_RECEIPT_CREATIONS = 1
MAX_RECEIPT_READS = 1

_BASE_HEADER = (
    "Latest compact task ledger from your own previous Action:\n"
    "VERIFIED: {verified}\n"
    "PENDING: {pending}\n"
)
_BASE_FOOTER = (
    "The current screenshot is authoritative. Continue the pending task only "
    "when it remains consistent with what is visible."
)
_CNR_FACT = (
    "RECENT OBSERVATION: The last two {label} actions produced no detectable "
    "screen change."
)


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _bucket(value: Any) -> int | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    number = min(1.0, max(0.0, number))
    return min(20, max(0, math.floor(20 * number + 0.5)))


def canonical_action_family(
    action: dict[str, Any] | None,
) -> tuple[str, str] | None:
    """Return a bounded family key and a coordinate-free renderer label."""

    if not isinstance(action, dict):
        return None
    kind = str(action.get("type") or "")
    if kind in {"tap", "long_press"}:
        x, y = _bucket(action.get("x")), _bucket(action.get("y"))
        if x is None or y is None:
            return None
        label = "same tap area" if kind == "tap" else "same long-press area"
        return f"{kind}:{x}:{y}", label
    if kind == "swipe":
        try:
            dx = float(action.get("x2")) - float(action.get("x"))
            dy = float(action.get("y2")) - float(action.get("y"))
        except (TypeError, ValueError):
            return None
        if not math.isfinite(dx) or not math.isfinite(dy) or (dx == 0 and dy == 0):
            return None
        direction = (
            "right"
            if abs(dx) >= abs(dy) and dx > 0
            else "left"
            if abs(dx) >= abs(dy)
            else "down"
            if dy > 0
            else "up"
        )
        return f"swipe:{direction}", "same swipe direction"
    if kind == "type_text":
        text = " ".join(str(action.get("text") or "").split()).casefold()
        if not text:
            return None
        return f"type_text:{_digest(text)}", "same typed-text"
    labels = {
        "press_back": "Back",
        "press_home": "Home",
        "press_enter": "Enter",
        "press_recents": "Recents",
        "wait": "wait",
    }
    if kind in labels:
        return kind, labels[kind]
    return None


def is_no_rgb_progress(transition: dict[str, Any] | None) -> bool:
    if not isinstance(transition, dict) or transition.get("same_shape") is not True:
        return False
    value = transition.get("changed_pixel_fraction_gt_5")
    try:
        fraction = float(value)
    except (TypeError, ValueError):
        return False
    return (
        math.isfinite(fraction)
        and 0.0 <= fraction <= 1.0
        and fraction <= NO_PROGRESS_PIXEL_FRACTION
    )


@dataclass(frozen=True)
class NonprogressSupport:
    family_key: str
    renderer_label: str
    first_action_ordinal: int
    first_call_id: str
    first_response_sha256: str
    first_action_sha256: str
    first_before_screenshot_sha256: str
    first_after_screenshot_sha256: str
    first_changed_pixel_fraction_gt_5: float


@dataclass(frozen=True)
class NonprogressReceipt:
    receipt_id: str
    family_key: str
    renderer_label: str
    first_support_action_ordinal: int
    second_support_action_ordinal: int
    first_eligible_request_ordinal: int
    expires_after_request_ordinal: int


@dataclass(frozen=True)
class CombinedReadTicket:
    ticket_id: str
    request_step: int
    ledger_id: str | None
    receipt_id: str | None
    text: str
    text_sha256: str


class OneShotControllerNonprogressReceiptMemory(CompactVerifiedPendingMemory):
    """Exact A1-R2 ledger plus at most one controller-authored CNR."""

    mechanism_id = MECHANISM_ID

    def __init__(
        self,
        *,
        ttl_requests: int = 8,
        max_render_chars: int = 1200,
        receipt_render_mode: str = "enabled",
    ) -> None:
        super().__init__(ttl_requests=ttl_requests, max_render_chars=max_render_chars)
        if receipt_render_mode not in {"enabled", "neutralized"}:
            raise ValueError("A1-R3-v3 receipt_render_mode invalid")
        self.receipt_render_mode = receipt_render_mode
        self.support: NonprogressSupport | None = None
        self.receipt: NonprogressReceipt | None = None
        self.receipt_creation_count = 0
        self.receipt_committed_read_count = 0
        self.receipt_expiry_count = 0
        self.receipt_drop_count = 0
        self.receipt_suppressed_after_cap_count = 0
        self.read_events: list[dict[str, Any]] = []
        self.receipt_events: list[dict[str, Any]] = []
        self.lifecycle_events: list[dict[str, Any]] = []

    def _record_lifecycle(self, event: dict[str, Any]) -> None:
        self.lifecycle_events.append(dict(event))
        self.lifecycle_events = self.lifecycle_events[-12:]

    def observe_step(
        self,
        *,
        source_step: int,
        action_summary: str,
        canonical_action: dict[str, Any] | None,
        transition: dict[str, Any] | None,
        source_call_id: str,
        source_response_sha256: str,
        source_screenshot_sha256: str,
        source_after_screenshot_sha256: str = "",
        **_: Any,
    ) -> dict[str, Any]:
        ledger_event = super().write(
            source_step=source_step,
            action_summary=action_summary,
            source_call_id=source_call_id,
            source_response_sha256=source_response_sha256,
            source_screenshot_sha256=source_screenshot_sha256,
        )
        event: dict[str, Any] = {
            "mechanism_id": MECHANISM_ID,
            "source_step": int(source_step),
            "ledger_event": ledger_event,
            "cnr_support_created": False,
            "cnr_receipt_created": False,
        }
        if self.receipt is not None:
            self.support = None
            event["cnr_reason"] = "receipt_pending"
            return event
        if self.receipt_creation_count >= MAX_RECEIPT_CREATIONS:
            self.support = None
            self.receipt_suppressed_after_cap_count += 1
            event["cnr_reason"] = "episode_one_shot_cap_reached"
            return event
        family = canonical_action_family(canonical_action)
        if family is None or not is_no_rgb_progress(transition):
            self.support = None
            event["cnr_reason"] = "unsupported_or_material_transition"
            return event
        family_key, label = family
        fraction = float((transition or {})["changed_pixel_fraction_gt_5"])
        canonical_sha = sha256(
            json.dumps(
                canonical_action or {},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        if self.support is None or self.support.family_key != family_key:
            self.support = NonprogressSupport(
                family_key=family_key,
                renderer_label=label,
                first_action_ordinal=int(source_step),
                first_call_id=str(source_call_id),
                first_response_sha256=str(source_response_sha256),
                first_action_sha256=canonical_sha,
                first_before_screenshot_sha256=str(source_screenshot_sha256),
                first_after_screenshot_sha256=str(source_after_screenshot_sha256),
                first_changed_pixel_fraction_gt_5=fraction,
            )
            event.update(
                {
                    "cnr_support_created": True,
                    "cnr_reason": "first_no_progress_support",
                    "cnr_family_key": family_key,
                }
            )
            return event
        first = self.support
        receipt_id = (
            f"cnr_{int(source_step):03d}_"
            + _digest(
                first.first_call_id
                + "\n"
                + str(source_call_id)
                + "\n"
                + family_key
            )[:12]
        )
        self.receipt = NonprogressReceipt(
            receipt_id=receipt_id,
            family_key=family_key,
            renderer_label=label,
            first_support_action_ordinal=first.first_action_ordinal,
            second_support_action_ordinal=int(source_step),
            first_eligible_request_ordinal=int(source_step) + 1,
            expires_after_request_ordinal=int(source_step) + 2,
        )
        self.support = None
        self.receipt_creation_count += 1
        receipt_event = {
            "event": "cnr_receipt_created",
            **asdict(self.receipt),
            "second_call_id": str(source_call_id),
            "second_response_sha256": str(source_response_sha256),
            "second_action_sha256": canonical_sha,
            "second_before_screenshot_sha256": str(source_screenshot_sha256),
            "second_after_screenshot_sha256": str(source_after_screenshot_sha256),
            "second_changed_pixel_fraction_gt_5": fraction,
        }
        self.receipt_events.append(receipt_event)
        self._record_lifecycle(receipt_event)
        event.update(
            {
                "cnr_receipt_created": True,
                "cnr_reason": "second_consecutive_no_progress_support",
                "cnr_receipt_id": receipt_id,
                "cnr_family_key": family_key,
                "cnr_first_support_step": first.first_action_ordinal,
                "cnr_second_support_step": int(source_step),
            }
        )
        return event

    def _expire_parent_if_needed(self, request_step: int) -> str | None:
        if self.active is None:
            return None
        if request_step - self.active.source_step < self.ttl_requests:
            return None
        expired_id = self.active.ledger_id
        self.active = None
        self.expiry_count += 1
        return expired_id

    def _base_text(self) -> str:
        if self.active is None:
            return ""
        return _BASE_HEADER.format(
            verified=self.active.verified,
            pending=self.active.pending,
        ) + _BASE_FOOTER

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        del context
        if self.pending_ticket is not None:
            raise RuntimeError("A1-R3-v3 read ticket was not committed or cancelled")
        request_step = self.read_call_count
        self.read_call_count += 1
        expired_ledger_id = self._expire_parent_if_needed(request_step)
        audit: dict[str, Any] = {
            "mechanism_id": MECHANISM_ID,
            "request_step": request_step,
            "nonempty": False,
            "ticket_id": None,
            "cnr_receipt_eligible": False,
            "failure_evidence_injected": False,
        }
        if expired_ledger_id is not None:
            audit["expired_ledger_id"] = expired_ledger_id
        if self.receipt is not None and request_step > self.receipt.expires_after_request_ordinal:
            expired_receipt_id = self.receipt.receipt_id
            self.receipt = None
            self.receipt_expiry_count += 1
            audit["expired_cnr_receipt_id"] = expired_receipt_id
            self._record_lifecycle(
                {
                    "event": "cnr_receipt_expired",
                    "receipt_id": expired_receipt_id,
                    "request_step": request_step,
                }
            )
        receipt = self.receipt
        receipt_eligible = bool(
            receipt is not None
            and request_step >= receipt.first_eligible_request_ordinal
            and request_step <= receipt.expires_after_request_ordinal
        )
        audit["cnr_receipt_eligible"] = receipt_eligible
        base = self._base_text()
        if receipt_eligible:
            assert receipt is not None
            fact = _CNR_FACT.format(label=receipt.renderer_label)
            text = (
                base + "\n" + fact
                if self.receipt_render_mode == "enabled" and base
                else fact
                if self.receipt_render_mode == "enabled"
                else base
            )
            if not text:
                self.receipt = None
                self.receipt_committed_read_count += 1
                audit.update(
                    {
                        "reason": "cnr_shadow_consumed_without_prompt",
                        "cnr_receipt_id": receipt.receipt_id,
                        "cnr_shadow_consumed": True,
                    }
                )
                self._record_lifecycle(
                    {
                        "event": "cnr_shadow_consumed_without_prompt",
                        "receipt_id": receipt.receipt_id,
                        "request_step": request_step,
                    }
                )
                return "", audit
            if len(text) > self.max_render_chars:
                self.receipt = None
                self.receipt_drop_count += 1
                audit.update(
                    {
                        "reason": "cnr_render_boundary_fail_closed",
                        "dropped_cnr_receipt_id": receipt.receipt_id,
                    }
                )
                self._record_lifecycle(
                    {
                        "event": "cnr_receipt_dropped_render_boundary",
                        "receipt_id": receipt.receipt_id,
                        "request_step": request_step,
                    }
                )
                return self._prepare_base_ticket(base, request_step, audit)
            ticket = CombinedReadTicket(
                ticket_id=self._id("cnrread"),
                request_step=request_step,
                ledger_id=self.active.ledger_id if self.active is not None else None,
                receipt_id=receipt.receipt_id,
                text=text,
                text_sha256=_digest(text),
            )
            self.pending_ticket = ticket
            audit.update(
                {
                    "nonempty": True,
                    "reason": "cnr_prepared_not_consumed",
                    "ticket_id": ticket.ticket_id,
                    "ledger_id": ticket.ledger_id,
                    "cnr_receipt_id": receipt.receipt_id,
                    "rendered_chars": len(text),
                    "rendered_sha256": ticket.text_sha256,
                    "failure_evidence_prepared": True,
                    "failure_evidence_injected": False,
                    "failed_action_family": receipt.family_key,
                    "failure_second_support_step": receipt.second_support_action_ordinal,
                }
            )
            self._record_lifecycle(
                {
                    "event": "cnr_injection_prepared",
                    "receipt_id": receipt.receipt_id,
                    "ticket_id": ticket.ticket_id,
                    "request_step": request_step,
                    "text_sha256": ticket.text_sha256,
                }
            )
            return text, audit
        return self._prepare_base_ticket(base, request_step, audit)

    def _prepare_base_ticket(
        self, base: str, request_step: int, audit: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        if not base:
            audit["reason"] = (
                "expired"
                if audit.get("expired_ledger_id")
                else audit.get("reason") or "no_active_ledger"
            )
            return "", audit
        if len(base) > self.max_render_chars:
            audit["reason"] = "render_boundary_fail_closed"
            return "", audit
        assert self.active is not None
        ticket = CombinedReadTicket(
            ticket_id=self._id("cvpread"),
            request_step=request_step,
            ledger_id=self.active.ledger_id,
            receipt_id=None,
            text=base,
            text_sha256=_digest(base),
        )
        self.pending_ticket = ticket
        audit.update(
            {
                "nonempty": True,
                "reason": "prepared_not_consumed",
                "ticket_id": ticket.ticket_id,
                "ledger_id": ticket.ledger_id,
                "rendered_chars": len(base),
                "rendered_sha256": ticket.text_sha256,
            }
        )
        return base, audit

    def commit_injection(self, ticket_id: str, final_prompt_sha256: str) -> dict[str, Any]:
        ticket = self.pending_ticket
        if ticket is None or ticket.ticket_id != ticket_id:
            raise RuntimeError("A1-R3-v3 injection ticket mismatch")
        event = {
            "ticket_id": ticket.ticket_id,
            "request_step": ticket.request_step,
            "ledger_id": ticket.ledger_id,
            "cnr_receipt_id": ticket.receipt_id,
            "exact_injected_text": ticket.text,
            "exact_injected_text_sha256": ticket.text_sha256,
            "final_prompt_sha256": str(final_prompt_sha256),
            "chars": len(ticket.text),
            "failure_evidence_injected": (
                ticket.receipt_id is not None
                and self.receipt_render_mode == "enabled"
            ),
            "cnr_shadow_committed": (
                ticket.receipt_id is not None
                and self.receipt_render_mode == "neutralized"
            ),
        }
        if ticket.receipt_id is not None:
            if self.receipt is None or self.receipt.receipt_id != ticket.receipt_id:
                raise RuntimeError("A1-R3-v3 receipt ticket mismatch")
            self.receipt = None
            self.receipt_committed_read_count += 1
            self.read_events.append(event)
            self._record_lifecycle(
                {
                    "event": "cnr_injection_committed",
                    "receipt_id": ticket.receipt_id,
                    "ticket_id": ticket.ticket_id,
                    "request_step": ticket.request_step,
                    "text_sha256": ticket.text_sha256,
                    "final_prompt_sha256": str(final_prompt_sha256),
                }
            )
        self.pending_ticket = None
        self.nonempty_read_count += 1
        self.injected_chars += len(ticket.text)
        self._last_committed_read = event
        return event

    def cancel_injection(self, ticket_id: str, reason: str) -> dict[str, Any]:
        ticket = self.pending_ticket
        if ticket is None or ticket.ticket_id != ticket_id:
            raise RuntimeError("A1-R3-v3 cancellation ticket mismatch")
        self.pending_ticket = None
        self.cancelled_read_count += 1
        event = {
            "ticket_id": ticket_id,
            "cnr_receipt_id": ticket.receipt_id,
            "cancelled": True,
            "reason": str(reason),
        }
        if ticket.receipt_id is not None:
            self._record_lifecycle({"event": "cnr_injection_cancelled", **event})
        return event

    def audit_record(self) -> dict[str, Any]:
        parent = super().audit_record()
        counters = dict(parent["counters"])
        counters.update(
            {
                "cnr_receipt_creation_count": self.receipt_creation_count,
                "cnr_receipt_committed_read_count": self.receipt_committed_read_count,
                "cnr_receipt_expiry_count": self.receipt_expiry_count,
                "cnr_receipt_drop_count": self.receipt_drop_count,
                "cnr_suppressed_after_one_shot_cap_count": (
                    self.receipt_suppressed_after_cap_count
                ),
            }
        )
        return {
            "schema": "a1r3v3_one_shot_cnr_audit_v1",
            "mechanism_id": MECHANISM_ID,
            "receipt_render_mode": self.receipt_render_mode,
            "active": self.receipt_committed_read_count > 0,
            "active_ledger": parent["active_ledger"],
            "support": asdict(self.support) if self.support else None,
            "receipt": asdict(self.receipt) if self.receipt else None,
            "pending_ticket": asdict(self.pending_ticket) if self.pending_ticket else None,
            "last_committed_read": self._last_committed_read,
            "receipt_events": list(self.receipt_events),
            "lifecycle_events": list(self.lifecycle_events),
            "read_events": list(self.read_events),
            "counters": counters,
            "decision_boundary": {
                "extra_model_calls": 0,
                "extra_screenshots": 0,
                "action_override_count": 0,
                "forced_termination_count": 0,
                "hidden_ui_used_for_decision": False,
                "evaluator_used_for_decision": False,
                "task_name_used_for_decision": False,
                "goal_parser_used_for_decision": False,
            },
        }


__all__ = [
    "EXPERIMENT_ID",
    "MECHANISM_ID",
    "MAX_RECEIPT_CREATIONS",
    "MAX_RECEIPT_READS",
    "NO_PROGRESS_PIXEL_FRACTION",
    "OneShotControllerNonprogressReceiptMemory",
    "canonical_action_family",
    "is_no_rgb_progress",
]
