"""One-shot triggered recovery reasoning layered beside frozen A1-R2.

SYS-TRRC is a composite system, not a memory arm.  A frozen A1-R2 instance
continues to own the complete memory path.  This policy only observes executed
visible transitions, schedules at most one same-model auxiliary call, and
offers its bounded output to exactly one later executor request.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import re
from typing import Any, Callable

import numpy as np

from .a1r3v3_one_shot_cnr import (
    NO_PROGRESS_PIXEL_FRACTION,
    canonical_action_family,
    is_no_rgb_progress,
)


SYSTEM_ID = "sys_trrc_r2_one_shot_triggered_recovery_v1"
AUDIT_SCHEMA = "sys_trrc_r2_one_shot_triggered_recovery_audit_v1"
MODES = ("detector", "generic", "full")
MAX_AUX_TOKENS = 192
MAX_AUX_TOTAL_TOKENS = 8192
MAX_AUX_LATENCY_SECONDS = 60.0
MAX_RECENT_ACTIONS = 4

COMMON_AUX_SYSTEM_TEMPLATE = """You are a bounded auxiliary reasoner. You do not act, terminate, edit memory,
or decide whether the task is complete.

{role_instruction}

Use only the supplied task goal, current screenshot, exact R2 ledger, bounded
recent executed-action summaries, and detector evidence. The current screenshot
is authoritative. Do not use hidden UI, evaluator information, future state,
or outside task knowledge. Return exactly three single-line fields:

ASSESSMENT: <brief visible-evidence assessment>
RECOMMENDATION: <one concise suggestion for the executor's next decision>
VISIBLE_CHECK: <what visible evidence the executor should inspect next>"""

GENERIC_ROLE = (
    "Independently review the supplied visible evidence and provide one concise\n"
    "next-decision suggestion."
)
FULL_ROLE = (
    "Identify the currently recurring or visibly unsupported approach and provide\n"
    "one materially different, screenshot-grounded recovery strategy for the next\n"
    "decision."
)
COMMON_USER_TEMPLATE = """TASK GOAL:
{goal}

CURRENT COMPACT R2 LEDGER:
VERIFIED: {verified}
PENDING: {pending}

RECENT EXECUTED ACTION SUMMARIES:
{recent_actions}

DETERMINISTIC DETECTOR EVIDENCE:
The same canonical action family was executed twice consecutively. Each transition had the same RGB shape and at most 0.001 of pixels changed by more than five intensity levels. Family: {family_label}.

Return exactly the required three fields."""

ADVICE_TEMPLATE = """AUXILIARY ADVICE (non-authoritative; expires after this request):
ASSESSMENT: {assessment}
RECOMMENDATION: {recommendation}
VISIBLE_CHECK: {visible_check}
The current screenshot is authoritative. The executor must decide the next action."""

_AUX_RESPONSE = re.compile(
    r"\AASSESSMENT: (?P<assessment>[^\r\n]+)\r?\n"
    r"RECOMMENDATION: (?P<recommendation>[^\r\n]+)\r?\n"
    r"VISIBLE_CHECK: (?P<visible_check>[^\r\n]+)\Z"
)
_FORBIDDEN_AUX = re.compile(
    r"(?i)<\s*tool_call|\bAction\s*:|mobile_use|\bcoordinate2?\b|"
    r"\btask (?:is )?(?:complete|completed|successful|failed)\b"
)


class RecoveryIntegrityError(RuntimeError):
    """The visible-only recovery contract was violated."""


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _clean_line(value: Any, *, limit: int) -> str:
    text = " ".join(str(value).split()).strip()
    if not text or len(text) > limit or "\x00" in text:
        raise RecoveryIntegrityError("text_boundary")
    return text


def _visible_changed_fraction(before_pixels: Any, after_pixels: Any) -> float:
    before = np.asarray(before_pixels)
    after = np.asarray(after_pixels)
    for pixels in (before, after):
        if (
            pixels.ndim != 3
            or pixels.shape[2] < 3
            or not np.issubdtype(pixels.dtype, np.integer)
        ):
            raise RecoveryIntegrityError("visible_rgb_boundary")
    if before.shape != after.shape:
        return 1.0
    difference = np.max(
        np.abs(
            before[:, :, :3].astype(np.int16)
            - after[:, :, :3].astype(np.int16)
        ),
        axis=2,
    )
    return float(np.mean(difference > 5))


def parse_auxiliary_response(content: str) -> dict[str, str]:
    text = str(content).strip()
    if _FORBIDDEN_AUX.search(text):
        raise RecoveryIntegrityError("aux_forbidden_content")
    match = _AUX_RESPONSE.fullmatch(text)
    if match is None:
        raise RecoveryIntegrityError("aux_schema")
    fields = {
        key: _clean_line(match.group(key), limit=240)
        for key in ("assessment", "recommendation", "visible_check")
    }
    rendered = ADVICE_TEMPLATE.format(**fields)
    if len(rendered) > 900 or len(rendered.encode("utf-8")) > 1800:
        raise RecoveryIntegrityError("aux_render_boundary")
    return {**fields, "rendered": rendered}


@dataclass
class NonprogressSupport:
    family_key: str
    renderer_label: str
    source_step: int
    source_call_id: str
    source_response_sha256: str
    action_sha256: str
    before_screenshot_sha256: str
    after_screenshot_sha256: str
    changed_pixel_fraction_gt_5: float


@dataclass
class TriggerReceipt:
    receipt_id: str
    family_key: str
    renderer_label: str
    first_support_step: int
    second_support_step: int
    eligible_request_step: int
    first_before_screenshot_sha256: str
    first_after_screenshot_sha256: str
    second_before_screenshot_sha256: str
    second_after_screenshot_sha256: str
    evidence_sha256: str


@dataclass
class AuxTicket:
    ticket_id: str
    receipt_id: str
    request_step: int
    system_prompt: str
    user_prompt: str
    request_text_sha256: str
    current_screenshot_sha256: str
    token_projection: dict[str, Any]


@dataclass
class InjectionTicket:
    ticket_id: str
    receipt_id: str
    request_step: int
    text: str
    text_sha256: str
    aux_call_id: str
    aux_request_sha256: str
    aux_response_sha256: str


class OneShotTriggeredRecoveryPolicy:
    """First two-support no-progress event schedules at most one aux call."""

    system_id = SYSTEM_ID

    def __init__(
        self,
        *,
        mode: str,
        max_aux_tokens: int = MAX_AUX_TOKENS,
        max_recent_actions: int = MAX_RECENT_ACTIONS,
        token_projector: Callable[[str, str, str], dict[str, Any]] | None = None,
        text_delta_counter: Callable[[str, str], int] | None = None,
    ) -> None:
        if mode not in MODES:
            raise ValueError(f"unsupported SYS-TRRC mode: {mode!r}")
        if max_aux_tokens != MAX_AUX_TOKENS or max_recent_actions != MAX_RECENT_ACTIONS:
            raise ValueError("SYS-TRRC v1 boundary drift")
        self.mode = mode
        self.max_aux_tokens = max_aux_tokens
        self.max_recent_actions = max_recent_actions
        self._token_projector = token_projector
        self._text_delta_counter = text_delta_counter
        self.support: NonprogressSupport | None = None
        self.pending_receipt: TriggerReceipt | None = None
        self.pending_aux: AuxTicket | None = None
        self.pending_injection: InjectionTicket | None = None
        self.last_receipt: TriggerReceipt | None = None
        self.aux_used = False
        self._serial = 0
        self.trigger_count = 0
        self.aux_prepared_count = 0
        self.aux_committed_count = 0
        self.aux_output_invalid_count = 0
        self.injection_committed_count = 0
        self.cancelled_aux_count = 0
        self.cancelled_injection_count = 0
        self.support_reset_count = 0
        self.events: list[dict[str, Any]] = []
        self.post_injection_watches: list[dict[str, Any]] = []

    def count_advice_prompt_tokens(self, base_text: str, final_text: str) -> int:
        if self._text_delta_counter is None:
            raise RecoveryIntegrityError("advice_text_token_counter_missing")
        value = int(self._text_delta_counter(base_text, final_text))
        if value < 1:
            raise RecoveryIntegrityError("advice_text_token_delta_boundary")
        return value

    def _id(self, prefix: str) -> str:
        self._serial += 1
        return f"{prefix}_{self._serial:04d}"

    def _event(self, value: dict[str, Any]) -> None:
        self.events.append(value)
        self.events = self.events[-24:]

    def observe_transition(
        self,
        *,
        source_step: int,
        action_summary: str,
        canonical_action: dict[str, Any],
        before_pixels: Any,
        after_pixels: Any,
        transition: dict[str, Any],
        source_call_id: str,
        source_response_sha256: str,
        source_before_screenshot_sha256: str,
        source_after_screenshot_sha256: str,
    ) -> dict[str, Any]:
        recomputed_fraction = _visible_changed_fraction(before_pixels, after_pixels)
        recorded_fraction = transition.get("changed_pixel_fraction_gt_5")
        try:
            recorded = float(recorded_fraction)
        except (TypeError, ValueError) as exc:
            raise RecoveryIntegrityError("transition_fraction") from exc
        if not math.isfinite(recorded) or abs(recorded - recomputed_fraction) > 1e-12:
            raise RecoveryIntegrityError("transition_fraction_mismatch")
        family = canonical_action_family(canonical_action)
        no_progress = is_no_rgb_progress(transition)
        event: dict[str, Any] = {
            "event": "transition_observed",
            "source_step": int(source_step),
            "family_key": family[0] if family else None,
            "no_rgb_progress": no_progress,
            "changed_pixel_fraction_gt_5": recorded,
            "trigger_created": False,
        }

        for watch in self.post_injection_watches:
            if watch.get("closed"):
                continue
            watch["observed_actions"] += 1
            watch["post_action_sha256s"].append(
                _digest(_canonical_json(canonical_action))
            )
            watch["visible_change_seen"] = bool(
                watch["visible_change_seen"] or recorded > NO_PROGRESS_PIXEL_FRACTION
            )
            if source_after_screenshot_sha256 in watch["anchor_screenshot_sha256s"]:
                watch["anchor_relapse_seen"] = True
            if watch["observed_actions"] >= 4:
                watch["closed"] = True

        if self.trigger_count or self.aux_used or self.pending_receipt is not None:
            self.support = None
            event["reason"] = "one_shot_or_pending"
            self._event(event)
            return event
        remaining_slots = transition.get("remaining_native_decision_slots")
        if remaining_slots is None:
            raise RecoveryIntegrityError("remaining_native_decision_slots_missing")
        try:
            remaining_slots = int(remaining_slots)
        except (TypeError, ValueError) as exc:
            raise RecoveryIntegrityError("remaining_native_decision_slots") from exc
        if remaining_slots < 0:
            raise RecoveryIntegrityError("remaining_native_decision_slots")
        if remaining_slots == 0:
            self.support = None
            event["reason"] = "no_remaining_native_decision_slot"
            self._event(event)
            return event
        if family is None or not no_progress:
            if self.support is not None:
                self.support_reset_count += 1
            self.support = None
            event["reason"] = "unsupported_or_material_transition"
            self._event(event)
            return event
        family_key, renderer_label = family
        action_sha = _digest(_canonical_json(canonical_action))
        if self.support is None or self.support.family_key != family_key:
            if self.support is not None:
                self.support_reset_count += 1
            self.support = NonprogressSupport(
                family_key=family_key,
                renderer_label=renderer_label,
                source_step=int(source_step),
                source_call_id=str(source_call_id),
                source_response_sha256=str(source_response_sha256),
                action_sha256=action_sha,
                before_screenshot_sha256=str(source_before_screenshot_sha256),
                after_screenshot_sha256=str(source_after_screenshot_sha256),
                changed_pixel_fraction_gt_5=recorded,
            )
            event.update({"reason": "first_support", "support_created": True})
            self._event(event)
            return event

        first = self.support
        evidence = {
            "family_key": family_key,
            "first_step": first.source_step,
            "second_step": int(source_step),
            "first_action_sha256": first.action_sha256,
            "second_action_sha256": action_sha,
            "threshold": NO_PROGRESS_PIXEL_FRACTION,
        }
        evidence_sha = _digest(_canonical_json(evidence))
        receipt = TriggerReceipt(
            receipt_id=f"trrc_{int(source_step):03d}_{evidence_sha[:12]}",
            family_key=family_key,
            renderer_label=renderer_label,
            first_support_step=first.source_step,
            second_support_step=int(source_step),
            eligible_request_step=int(source_step) + 1,
            first_before_screenshot_sha256=first.before_screenshot_sha256,
            first_after_screenshot_sha256=first.after_screenshot_sha256,
            second_before_screenshot_sha256=str(source_before_screenshot_sha256),
            second_after_screenshot_sha256=str(source_after_screenshot_sha256),
            evidence_sha256=evidence_sha,
        )
        self.support = None
        self.pending_receipt = receipt
        self.last_receipt = receipt
        self.trigger_count = 1
        event.update(
            {
                "reason": "second_consecutive_support",
                "trigger_created": True,
                "receipt_id": receipt.receipt_id,
                "eligible_request_step": receipt.eligible_request_step,
                "evidence_sha256": evidence_sha,
            }
        )
        self._event(event)
        return event

    def prepare_aux(self, context: dict[str, Any]) -> dict[str, Any] | None:
        receipt = self.pending_receipt
        if receipt is None:
            return None
        request_step = int(context.get("request_step"))
        if request_step != receipt.eligible_request_step:
            raise RecoveryIntegrityError("aux_request_step")
        if self.mode == "detector":
            self.pending_receipt = None
            self.aux_used = True
            self._event(
                {
                    "event": "detector_only_trigger_closed",
                    "receipt_id": receipt.receipt_id,
                    "request_step": request_step,
                }
            )
            return None
        if self.pending_aux is not None or self.pending_injection is not None or self.aux_used:
            raise RecoveryIntegrityError("aux_one_shot_state")
        goal = _clean_line(context.get("goal"), limit=1200)
        active = ((context.get("r2_memory_audit") or {}).get("active_ledger") or {})
        verified = _clean_line(active.get("verified", "none"), limit=450)
        pending = _clean_line(active.get("pending", "none"), limit=450)
        recent = list(context.get("recent_action_summaries") or [])[-self.max_recent_actions:]
        recent_text = "\n".join(
            f"{index + 1}. {_clean_line(value, limit=700)}"
            for index, value in enumerate(recent)
        ) or "none"
        role = FULL_ROLE if self.mode == "full" else GENERIC_ROLE
        system_prompt = COMMON_AUX_SYSTEM_TEMPLATE.format(role_instruction=role)
        user_prompt = COMMON_USER_TEMPLATE.format(
            goal=goal,
            verified=verified,
            pending=pending,
            recent_actions=recent_text,
            family_label=receipt.renderer_label,
        )
        if len(user_prompt) > 5000 or len(user_prompt.encode("utf-8")) > 9000:
            raise RecoveryIntegrityError("aux_input_boundary")
        if self._token_projector is None:
            raise RecoveryIntegrityError("aux_token_projector_missing")
        screenshot_path = str(context.get("current_screenshot_path") or "")
        screenshot_sha256 = str(context.get("current_screenshot_sha256") or "")
        if not screenshot_path or len(screenshot_sha256) != 64:
            raise RecoveryIntegrityError("aux_current_screenshot_missing")
        request_text = system_prompt + "\n\0\n" + user_prompt
        try:
            token_projection = self._token_projector(
                system_prompt, user_prompt, screenshot_path
            )
        except Exception as exc:
            raise RecoveryIntegrityError("aux_token_projection_failed") from exc
        if not isinstance(token_projection, dict):
            raise RecoveryIntegrityError("aux_token_projection_invalid")
        if token_projection.get("current_screenshot_sha256") != screenshot_sha256:
            raise RecoveryIntegrityError("aux_token_projection_image_mismatch")
        try:
            exact_multimodal_input_tokens = int(
                token_projection.get("exact_multimodal_input_tokens")
            )
        except (TypeError, ValueError) as exc:
            raise RecoveryIntegrityError("aux_token_projection_invalid") from exc
        if (
            exact_multimodal_input_tokens < 1
            or exact_multimodal_input_tokens + self.max_aux_tokens
            > MAX_AUX_TOTAL_TOKENS
        ):
            raise RecoveryIntegrityError("aux_projected_total_token_boundary")
        token_projection = dict(token_projection)
        token_projection.update(
            {
                "reserved_output_tokens": self.max_aux_tokens,
                "projected_total_tokens": (
                    exact_multimodal_input_tokens + self.max_aux_tokens
                ),
            }
        )
        ticket = AuxTicket(
            ticket_id=self._id("aux"),
            receipt_id=receipt.receipt_id,
            request_step=request_step,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            request_text_sha256=_digest(request_text),
            current_screenshot_sha256=screenshot_sha256,
            token_projection=token_projection,
        )
        self.pending_aux = ticket
        self.aux_prepared_count += 1
        self._event(
            {
                "event": "aux_prepared",
                "mode": self.mode,
                "ticket_id": ticket.ticket_id,
                "receipt_id": ticket.receipt_id,
                "request_step": request_step,
                "request_text_sha256": ticket.request_text_sha256,
                "token_projection": ticket.token_projection,
            }
        )
        return {
            "ticket_id": ticket.ticket_id,
            "receipt_id": ticket.receipt_id,
            "system_prompt": ticket.system_prompt,
            "user_prompt": ticket.user_prompt,
            "max_tokens": self.max_aux_tokens,
            "request_text_sha256": ticket.request_text_sha256,
            "token_projection": ticket.token_projection,
        }

    def commit_aux(self, ticket_id: str, call: Any) -> dict[str, Any]:
        ticket = self.pending_aux
        if ticket is None or ticket.ticket_id != str(ticket_id):
            raise RecoveryIntegrityError("aux_ticket_mismatch")
        attempts = (getattr(call, "raven_meta", {}) or {}).get("transport_attempts")
        if attempts != 1:
            raise RecoveryIntegrityError("aux_transport_attempts")
        if str(getattr(call, "prompt_sha256", "")) != ticket.request_text_sha256:
            raise RecoveryIntegrityError("aux_prompt_sha256_mismatch")
        if str(getattr(call, "image_sha256", "")) != ticket.current_screenshot_sha256:
            raise RecoveryIntegrityError("aux_image_sha256_mismatch")
        content = str(getattr(call, "content", ""))
        if str(getattr(call, "response_sha256", "")) != _digest(content):
            raise RecoveryIntegrityError("aux_response_sha256_mismatch")
        latency = (getattr(call, "raven_meta", {}) or {}).get("latency_seconds")
        try:
            latency_seconds = float(latency)
        except (TypeError, ValueError) as exc:
            raise RecoveryIntegrityError("aux_latency_missing") from exc
        if not math.isfinite(latency_seconds) or latency_seconds > MAX_AUX_LATENCY_SECONDS:
            raise RecoveryIntegrityError("aux_latency_boundary")
        usage = getattr(call, "usage", None)
        if usage is None:
            usage = getattr(call, "audit_record", lambda: {})().get("usage")
        if not isinstance(usage, dict):
            raise RecoveryIntegrityError("aux_usage_missing")
        try:
            prompt_tokens = int(usage.get("prompt_tokens"))
            completion_tokens = int(usage.get("completion_tokens"))
            total_tokens = int(usage.get("total_tokens"))
        except (TypeError, ValueError) as exc:
            raise RecoveryIntegrityError("aux_usage_missing") from exc
        expected_prompt_tokens = int(
            ticket.token_projection["exact_multimodal_input_tokens"]
        )
        if prompt_tokens != expected_prompt_tokens:
            raise RecoveryIntegrityError("aux_prompt_token_attestation_mismatch")
        if (
            completion_tokens < 0
            or completion_tokens > self.max_aux_tokens
            or total_tokens != prompt_tokens + completion_tokens
            or total_tokens > MAX_AUX_TOTAL_TOKENS
        ):
            raise RecoveryIntegrityError("aux_total_token_boundary")
        self.pending_aux = None
        self.pending_receipt = None
        self.aux_used = True
        self.aux_committed_count += 1
        event: dict[str, Any] = {
            "ticket_id": ticket.ticket_id,
            "receipt_id": ticket.receipt_id,
            "request_step": ticket.request_step,
            "call_id": str(call.call_id),
            "request_sha256": str(call.request_sha256),
            "response_sha256": str(call.response_sha256),
            "transport_attempts": attempts,
            "latency_seconds": latency_seconds,
            "usage": dict(usage),
            "injection_text": None,
            "injection_ticket_id": None,
        }
        try:
            parsed = parse_auxiliary_response(content)
        except RecoveryIntegrityError as exc:
            self.aux_output_invalid_count += 1
            event.update({"valid_output": False, "invalid_reason": str(exc)})
            self._event({"event": "aux_output_invalid", **event})
            return event
        injection = InjectionTicket(
            ticket_id=self._id("inject"),
            receipt_id=ticket.receipt_id,
            request_step=ticket.request_step,
            text=parsed["rendered"],
            text_sha256=_digest(parsed["rendered"]),
            aux_call_id=str(call.call_id),
            aux_request_sha256=str(call.request_sha256),
            aux_response_sha256=str(call.response_sha256),
        )
        self.pending_injection = injection
        event.update(
            {
                "valid_output": True,
                "parsed": {key: parsed[key] for key in ("assessment", "recommendation", "visible_check")},
                "injection_text": injection.text,
                "injection_text_sha256": injection.text_sha256,
                "injection_ticket_id": injection.ticket_id,
            }
        )
        self._event({"event": "aux_committed_valid", **event})
        return event

    def commit_normal_injection(
        self, ticket_id: str, final_prompt_sha256: str, call: Any
    ) -> dict[str, Any]:
        ticket = self.pending_injection
        if ticket is None or ticket.ticket_id != str(ticket_id):
            raise RecoveryIntegrityError("normal_injection_ticket_mismatch")
        attempts = (getattr(call, "raven_meta", {}) or {}).get("transport_attempts")
        if attempts != 1:
            raise RecoveryIntegrityError("normal_injection_transport_attempts")
        event = {
            "event": "normal_injection_committed",
            "ticket_id": ticket.ticket_id,
            "receipt_id": ticket.receipt_id,
            "request_step": ticket.request_step,
            "text": ticket.text,
            "text_sha256": ticket.text_sha256,
            "final_prompt_sha256": str(final_prompt_sha256),
            "normal_call_id": str(call.call_id),
            "normal_request_sha256": str(call.request_sha256),
            "normal_response_sha256": str(call.response_sha256),
            "transport_attempts": attempts,
        }
        receipt = self.last_receipt
        anchors = [] if receipt is None else [
            receipt.first_before_screenshot_sha256,
            receipt.first_after_screenshot_sha256,
            receipt.second_before_screenshot_sha256,
            receipt.second_after_screenshot_sha256,
        ]
        self.post_injection_watches.append(
            {
                "receipt_id": ticket.receipt_id,
                "request_step": ticket.request_step,
                "observed_actions": 0,
                "post_action_sha256s": [],
                "visible_change_seen": False,
                "anchor_relapse_seen": False,
                "anchor_screenshot_sha256s": anchors,
                "closed": False,
            }
        )
        self.post_injection_watches = self.post_injection_watches[-1:]
        self.pending_injection = None
        self.injection_committed_count += 1
        self._event(event)
        return event

    def cancel_aux(self, ticket_id: str, reason: str) -> dict[str, Any]:
        ticket = self.pending_aux
        if ticket is None or ticket.ticket_id != str(ticket_id):
            raise RecoveryIntegrityError("aux_cancel_ticket")
        self.pending_aux = None
        self.aux_used = True
        self.cancelled_aux_count += 1
        event = {
            "event": "aux_cancelled",
            "ticket_id": ticket.ticket_id,
            "receipt_id": ticket.receipt_id,
            "reason": _clean_line(reason, limit=300),
        }
        self._event(event)
        return event

    def cancel_normal_injection(self, ticket_id: str, reason: str) -> dict[str, Any]:
        ticket = self.pending_injection
        if ticket is None or ticket.ticket_id != str(ticket_id):
            raise RecoveryIntegrityError("injection_cancel_ticket")
        self.pending_injection = None
        self.cancelled_injection_count += 1
        event = {
            "event": "normal_injection_cancelled",
            "ticket_id": ticket.ticket_id,
            "receipt_id": ticket.receipt_id,
            "reason": _clean_line(reason, limit=300),
        }
        self._event(event)
        return event

    def close_episode(self, reason: str) -> dict[str, Any]:
        closure = {
            "event": "episode_closed",
            "reason": _clean_line(reason, limit=300),
            "pending_receipt_closed": self.pending_receipt is not None,
            "pending_aux_closed": self.pending_aux is not None,
            "pending_injection_closed": self.pending_injection is not None,
        }
        self.support = None
        self.pending_receipt = None
        self.pending_aux = None
        self.pending_injection = None
        for watch in self.post_injection_watches:
            if not watch["closed"]:
                watch["closed"] = True
                watch["closure_reason"] = "episode_end"
        self._event(closure)
        return closure

    def audit_record(self) -> dict[str, Any]:
        return {
            "schema": AUDIT_SCHEMA,
            "system_id": SYSTEM_ID,
            "mode": self.mode,
            "detector": {
                "kind": "two_consecutive_same_family_no_rgb_progress",
                "no_progress_pixel_fraction": NO_PROGRESS_PIXEL_FRACTION,
                "required_supports": 2,
                "one_shot": True,
            },
            "state": {
                "support": asdict(self.support) if self.support else None,
                "pending_receipt": asdict(self.pending_receipt) if self.pending_receipt else None,
                "pending_aux": asdict(self.pending_aux) if self.pending_aux else None,
                "pending_injection": asdict(self.pending_injection) if self.pending_injection else None,
                "aux_used": self.aux_used,
            },
            "counters": {
                "trigger_count": self.trigger_count,
                "aux_prepared_count": self.aux_prepared_count,
                "aux_committed_count": self.aux_committed_count,
                "aux_output_invalid_count": self.aux_output_invalid_count,
                "injection_committed_count": self.injection_committed_count,
                "cancelled_aux_count": self.cancelled_aux_count,
                "cancelled_injection_count": self.cancelled_injection_count,
                "support_reset_count": self.support_reset_count,
            },
            "post_injection_watches": list(self.post_injection_watches),
            "events": list(self.events),
            "decision_boundary": {
                "aux_model_call_budget_per_episode": 0 if self.mode == "detector" else 1,
                "aux_model_calls": self.aux_committed_count + self.cancelled_aux_count,
                "action_override_count": 0,
                "forced_termination_count": 0,
                "extra_screenshot_count": 0,
                "hidden_ui_used_for_decision": False,
                "evaluator_used_for_decision": False,
                "task_name_used_for_decision": False,
            },
        }


__all__ = [
    "ADVICE_TEMPLATE",
    "AUDIT_SCHEMA",
    "COMMON_AUX_SYSTEM_TEMPLATE",
    "COMMON_USER_TEMPLATE",
    "FULL_ROLE",
    "GENERIC_ROLE",
    "MAX_AUX_TOKENS",
    "MAX_AUX_TOTAL_TOKENS",
    "MAX_AUX_LATENCY_SECONDS",
    "MODES",
    "OneShotTriggeredRecoveryPolicy",
    "RecoveryIntegrityError",
    "SYSTEM_ID",
    "parse_auxiliary_response",
]
