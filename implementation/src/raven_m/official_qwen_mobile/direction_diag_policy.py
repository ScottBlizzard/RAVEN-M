"""Four minimal exploratory auxiliary-reasoning policies over frozen A1-R2.

The policies share one resource envelope and the controller integration used by
SYS-TRRC.  They never read evaluator state, execute actions, or persist their
advice in ordinary history/R2.  Each episode permits at most one auxiliary
model call and one subsequent normal-request injection.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
import re
from typing import Any, Callable

from .sys_trrc_recovery import OneShotTriggeredRecoveryPolicy


MODES = ("c0", "p1", "p2", "p3")
SYSTEM_IDS = {
    "c0": "diag_c0_late_evidence_consolidation_r2_v1",
    "p1": "diag_p1_tcra_r2_full_v1",
    "p2": "diag_p2_scope_r2_full_v1",
    "p3": "diag_p3_scer_r2_full_v1",
}
MAX_AUX_TOKENS = 192
MAX_AUX_TOTAL_TOKENS = 8192
MAX_AUX_LATENCY_SECONDS = 60.0

_PROMPTS = {
    "c0": (
        "You are a bounded evidence-consolidation assistant. Use only the supplied goal, current screenshot, model-authored history, and exact R2 ledger. Consolidate exact task-relevant facts already observed; check arithmetic, constraints, omissions, and whether the next result-bearing decision is supported. Do not act, terminate, use hidden UI/evaluator data, or invent facts. Return exactly three single-line fields:\nFACTS: <exact relevant facts supported by the supplied evidence>\nCHECK: <derivation, constraint, or missing-evidence check>\nRECOMMENDATION: <one concise evidence-grounded suggestion for the executor>",
        ("FACTS", "CHECK", "RECOMMENDATION"),
        "LATE EVIDENCE CONSOLIDATION",
    ),
    "p2": (
        "You are a bounded phase coordinator. Use only the supplied goal, current screenshot, model-authored history, and exact R2 ledger. Summarize what is confirmed, what remains open or uncertain, and the single most important next phase. Do not emit coordinates, actions, completion verdicts, hidden UI/evaluator facts, or a long plan. Return exactly three single-line fields:\nCONFIRMED: <brief confirmed state>\nOPEN: <brief open or uncertain state>\nNEXT_PHASE: <one concise next-phase objective>",
        ("CONFIRMED", "OPEN", "NEXT_PHASE"),
        "ONE-SHOT PHASE ENVELOPE",
    ),
    "p3": (
        "You are a bounded visible-outcome critic. Use only the supplied goal, current screenshot, model-authored history, exact R2 ledger, and deferred terminal proposal. Judge whether visible evidence supports completion, identify anything unconfirmed, and state one evidence check for reconsideration. Do not act, use hidden UI/evaluator data, or declare evaluator success. Return exactly three single-line fields:\nSUPPORTED: <yes, no, or uncertain with brief visible reason>\nUNCONFIRMED: <remaining uncertainty or none>\nVERIFY_NEXT: <one concise visible check>",
        ("SUPPORTED", "UNCONFIRMED", "VERIFY_NEXT"),
        "VISIBLE OUTCOME REVIEW",
    ),
}
_FORBIDDEN = re.compile(r"(?i)<\s*tool_call|\bAction\s*:|mobile_use|\bcoordinate2?\b")


class DirectionDiagIntegrityError(RuntimeError):
    pass


def _digest_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _clean(value: Any, limit: int) -> str:
    text = " ".join(str(value).split()).strip()
    if not text:
        return "none"
    return text[:limit]


def _ledger(audit: dict[str, Any]) -> tuple[str, str]:
    active = (audit or {}).get("active_ledger") or {}
    return _clean(active.get("verified", "none"), 500), _clean(active.get("pending", "none"), 500)


def _history(values: list[Any], limit: int = 8) -> str:
    selected = list(values or [])[-limit:]
    return "\n".join(f"{i + 1}. {_clean(value, 700)}" for i, value in enumerate(selected)) or "none"


@dataclass
class _AuxTicket:
    ticket_id: str
    request_step: int
    system_prompt: str
    user_prompt: str
    prompt_sha256: str
    screenshot_sha256: str
    token_projection: dict[str, Any]


@dataclass
class _InjectionTicket:
    ticket_id: str
    request_step: int
    text: str
    text_sha256: str
    aux_call_id: str


class MinimalDirectionDiagnosticPolicy:
    """C0/P2/P3 scheduler and P1 adapter with a common one-call envelope."""

    max_auxiliary_calls = 1

    def __init__(
        self,
        *,
        mode: str,
        token_projector: Callable[[str, str, str], dict[str, Any]] | None,
        text_delta_counter: Callable[[str, str], int] | None,
    ) -> None:
        if mode not in MODES:
            raise ValueError(mode)
        self.mode = mode
        self.system_id = SYSTEM_IDS[mode]
        self._projector = token_projector
        self._text_delta = text_delta_counter
        self._delegate = (
            OneShotTriggeredRecoveryPolicy(
                mode="full",
                max_aux_tokens=MAX_AUX_TOKENS,
                token_projector=token_projector,
                text_delta_counter=text_delta_counter,
            )
            if mode == "p1"
            else None
        )
        self._counter = 0
        self._used = False
        self._pending_trigger: dict[str, Any] | None = None
        self._pending_aux: _AuxTicket | None = None
        self._pending_injection: _InjectionTicket | None = None
        self._terminal_deferred = False
        self._events: list[dict[str, Any]] = []
        self._post_injection: list[dict[str, Any]] = []

    def _id(self, kind: str) -> str:
        self._counter += 1
        return f"{self.mode}_{kind}_{self._counter:04d}"

    def _event(self, event: dict[str, Any]) -> None:
        self._events.append(dict(event))
        self._events = self._events[-96:]

    def prepare_aux(self, context: dict[str, Any]) -> dict[str, Any] | None:
        if self._delegate is not None:
            return self._delegate.prepare_aux(context)
        if self._used or self._pending_aux is not None or self._pending_injection is not None:
            return None
        executed = int(context.get("executed_action_count") or 0)
        native_max = int(context.get("native_max_steps") or 0)
        request_step = int(context.get("request_step") or 0)
        trigger: dict[str, Any] | None = None
        if self.mode == "c0" and self._pending_trigger is not None:
            trigger = dict(self._pending_trigger)
        elif self.mode == "c0" and native_max > 0 and executed * 4 >= native_max * 3:
            trigger = {"kind": "late_fallback_fraction", "executed": executed, "native_max": native_max}
        elif self.mode == "p2" and native_max > 0 and executed * 2 >= native_max:
            trigger = {"kind": "midpoint", "executed": executed, "native_max": native_max}
        elif self.mode == "p3" and self._pending_trigger is not None:
            trigger = dict(self._pending_trigger)
        if trigger is None:
            return None
        system_prompt, _, _ = _PROMPTS[self.mode]
        verified, pending = _ledger(dict(context.get("r2_memory_audit") or {}))
        deferred = _clean(trigger.get("deferred_terminal", "none"), 300)
        user_prompt = (
            f"TASK GOAL:\n{_clean(context.get('goal'), 1200)}\n\n"
            f"CURRENT R2 LEDGER:\nVERIFIED: {verified}\nPENDING: {pending}\n\n"
            f"RECENT MODEL-AUTHORED EXECUTED HISTORY:\n{_history(list(context.get('history') or []))}\n\n"
            f"TRIGGER: {json.dumps(trigger, ensure_ascii=False, sort_keys=True)}\n"
            f"DEFERRED TERMINAL PROPOSAL: {deferred}\n\nReturn exactly the required three fields."
        )
        screenshot_path = str(context.get("current_screenshot_path") or "")
        screenshot_sha = str(context.get("current_screenshot_sha256") or "")
        if self._projector is None or not screenshot_path or len(screenshot_sha) != 64:
            raise DirectionDiagIntegrityError("projection_input_missing")
        projection = dict(self._projector(system_prompt, user_prompt, screenshot_path))
        input_tokens = int(projection.get("exact_multimodal_input_tokens") or 0)
        if projection.get("current_screenshot_sha256") != screenshot_sha or input_tokens < 1:
            raise DirectionDiagIntegrityError("projection_attestation")
        if input_tokens + MAX_AUX_TOKENS > MAX_AUX_TOTAL_TOKENS:
            raise DirectionDiagIntegrityError("projected_token_cap")
        projection.update({"reserved_output_tokens": MAX_AUX_TOKENS, "projected_total_tokens": input_tokens + MAX_AUX_TOKENS})
        prompt_sha = _digest_text(system_prompt + "\n\0\n" + user_prompt)
        ticket = _AuxTicket(self._id("aux"), request_step, system_prompt, user_prompt, prompt_sha, screenshot_sha, projection)
        self._pending_aux = ticket
        self._event({"event": "aux_prepared", "request_step": request_step, "trigger": trigger, "ticket_id": ticket.ticket_id, "token_projection": projection})
        return {"ticket_id": ticket.ticket_id, "system_prompt": system_prompt, "user_prompt": user_prompt, "max_tokens": MAX_AUX_TOKENS, "request_text_sha256": prompt_sha, "token_projection": projection}

    def _parse(self, content: str) -> str:
        if self.mode not in _PROMPTS or _FORBIDDEN.search(content):
            raise DirectionDiagIntegrityError("aux_forbidden")
        _, fields, title = _PROMPTS[self.mode]
        lines = [line.strip() for line in str(content).splitlines() if line.strip()]
        if len(lines) != 3:
            raise DirectionDiagIntegrityError("aux_schema")
        values: list[str] = []
        for line, field in zip(lines, fields, strict=True):
            prefix = field + ":"
            if not line.startswith(prefix):
                raise DirectionDiagIntegrityError("aux_schema")
            value = _clean(line[len(prefix):], 240)
            values.append(value)
        rendered = title + " (advisory; expires after this request):\n" + "\n".join(f"{field}: {value}" for field, value in zip(fields, values, strict=True)) + "\nThe current screenshot is authoritative; the executor chooses the action."
        if len(rendered) > 900:
            raise DirectionDiagIntegrityError("render_cap")
        return rendered

    def commit_aux(self, ticket_id: str, call: Any) -> dict[str, Any]:
        if self._delegate is not None:
            return self._delegate.commit_aux(ticket_id, call)
        ticket = self._pending_aux
        if ticket is None or ticket.ticket_id != str(ticket_id):
            raise DirectionDiagIntegrityError("aux_ticket")
        meta = dict(getattr(call, "raven_meta", {}) or {})
        if meta.get("transport_attempts") != 1:
            raise DirectionDiagIntegrityError("aux_transport")
        if str(getattr(call, "prompt_sha256", "")) != ticket.prompt_sha256 or str(getattr(call, "image_sha256", "")) != ticket.screenshot_sha256:
            raise DirectionDiagIntegrityError("aux_request_attestation")
        content = str(getattr(call, "content", ""))
        if str(getattr(call, "response_sha256", "")) != _digest_text(content):
            raise DirectionDiagIntegrityError("aux_response_attestation")
        latency = float(meta.get("latency_seconds"))
        if not math.isfinite(latency) or latency < 0 or latency > MAX_AUX_LATENCY_SECONDS:
            raise DirectionDiagIntegrityError("aux_latency")
        audit = call.audit_record()
        usage = dict(audit.get("usage") or {})
        prompt_tokens = int(usage.get("prompt_tokens"))
        completion_tokens = int(usage.get("completion_tokens"))
        total_tokens = int(usage.get("total_tokens"))
        if prompt_tokens != int(ticket.token_projection["exact_multimodal_input_tokens"]) or completion_tokens < 0 or completion_tokens > MAX_AUX_TOKENS or total_tokens != prompt_tokens + completion_tokens or total_tokens > MAX_AUX_TOTAL_TOKENS:
            raise DirectionDiagIntegrityError("aux_usage")
        self._pending_aux = None
        self._used = True
        try:
            text = self._parse(content)
        except DirectionDiagIntegrityError as exc:
            self._pending_trigger = None
            event = {"valid_output": False, "invalid_reason": str(exc), "injection_text": None, "injection_ticket_id": None}
            self._event({"event": "aux_output_invalid", **event})
            return event
        injection = _InjectionTicket(self._id("inject"), ticket.request_step, text, _digest_text(text), str(call.call_id))
        self._pending_injection = injection
        self._pending_trigger = None
        event = {"valid_output": True, "injection_text": text, "injection_ticket_id": injection.ticket_id, "injection_text_sha256": injection.text_sha256, "usage": usage, "latency_seconds": latency}
        self._event({"event": "aux_committed", **event})
        return event

    def commit_normal_injection(self, ticket_id: str, final_prompt_sha256: str, call: Any) -> dict[str, Any]:
        if self._delegate is not None:
            return self._delegate.commit_normal_injection(ticket_id, final_prompt_sha256, call)
        ticket = self._pending_injection
        if ticket is None or ticket.ticket_id != str(ticket_id):
            raise DirectionDiagIntegrityError("injection_ticket")
        if (getattr(call, "raven_meta", {}) or {}).get("transport_attempts") != 1:
            raise DirectionDiagIntegrityError("normal_transport")
        event = {"event": "normal_injection_committed", "ticket_id": ticket.ticket_id, "request_step": ticket.request_step, "text": ticket.text, "text_sha256": ticket.text_sha256, "final_prompt_sha256": str(final_prompt_sha256), "normal_call_id": str(call.call_id), "normal_response_sha256": str(call.response_sha256)}
        self._pending_injection = None
        self._post_injection.append(event)
        self._event(event)
        return event

    def count_advice_prompt_tokens(self, base_text: str, final_text: str) -> int:
        if self._delegate is not None:
            return self._delegate.count_advice_prompt_tokens(base_text, final_text)
        if self._text_delta is None:
            raise DirectionDiagIntegrityError("text_delta_counter_missing")
        value = int(self._text_delta(base_text, final_text))
        if value < 0:
            raise DirectionDiagIntegrityError("text_delta_negative")
        return value

    def cancel_aux(self, ticket_id: str, reason: str) -> dict[str, Any]:
        if self._delegate is not None:
            return self._delegate.cancel_aux(ticket_id, reason)
        if self._pending_aux is None or self._pending_aux.ticket_id != str(ticket_id):
            raise DirectionDiagIntegrityError("aux_cancel")
        self._pending_aux = None
        self._used = True
        event = {"event": "aux_cancelled", "reason": _clean(reason, 300)}
        self._event(event)
        return event

    def cancel_normal_injection(self, ticket_id: str, reason: str) -> dict[str, Any]:
        if self._delegate is not None:
            return self._delegate.cancel_normal_injection(ticket_id, reason)
        if self._pending_injection is None or self._pending_injection.ticket_id != str(ticket_id):
            raise DirectionDiagIntegrityError("injection_cancel")
        self._pending_injection = None
        event = {"event": "injection_cancelled", "reason": _clean(reason, 300)}
        self._event(event)
        return event

    def observe_transition(self, **kwargs: Any) -> dict[str, Any]:
        if self._delegate is not None:
            return self._delegate.observe_transition(**kwargs)
        event = {"event": "transition_observed", "source_step": int(kwargs.get("source_step") or 0), "changed_pixel_fraction_gt_5": (kwargs.get("transition") or {}).get("changed_pixel_fraction_gt_5")}
        self._event(event)
        return event

    @staticmethod
    def _pending_line(memory_read: dict[str, Any] | None) -> str | None:
        text = str((memory_read or {}).get("exact_injected_text") or "")
        for line in text.splitlines():
            if line.startswith("PENDING:"):
                value = line.partition(":")[2].strip()
                if value and value.casefold() not in {"none", "null", "no pending"}:
                    return value
        return None

    def review(self, *, proposed_action: dict[str, Any] | None, action_summary: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        return proposed_action, {"system_id": self.system_id, "eligible": False, "overridden": False, "reason": "advisory_only"}

    def review_terminal(self, *, terminal_status: str | None, memory_read: dict[str, Any] | None, previous_executed_action: dict[str, Any] | None, remaining_native_decision_slots: int) -> dict[str, Any]:
        if self.mode != "p3":
            return {"system_id": self.system_id, "eligible": False, "blocked": False, "reason": "not_outcome_mode"}
        eligible = terminal_status in {"answer", "success"} and not self._terminal_deferred and not self._used and int(remaining_native_decision_slots) >= 1
        event = {"system_id": self.system_id, "terminal_status": terminal_status, "pending_from_exact_r2_read": self._pending_line(memory_read), "remaining_native_decision_slots": int(remaining_native_decision_slots), "eligible": eligible, "blocked": False, "reason": "not_eligible"}
        if eligible:
            self._terminal_deferred = True
            self._pending_trigger = {"kind": "terminal_evidence_review", "deferred_terminal": str(terminal_status)}
            event.update({"blocked": True, "reason": "one_shot_visible_outcome_review", "history_message": "OUTCOME REVIEW QUEUED: The prior terminal proposal was deferred once. Reconsider completion from the current screenshot after the bounded visible-evidence advisory; the native action budget is unchanged.", "policy": self.system_id})
        self._event({"event": "terminal_review", **event})
        return event

    def review_route(self, **kwargs: Any) -> dict[str, Any]:
        if self.mode != "c0":
            return {"system_id": self.system_id, "eligible": False, "blocked": False, "reason": "no_route_guard"}
        action = kwargs.get("proposed_action")
        action_type = str(action.get("type") or "") if isinstance(action, dict) else ""
        executed = int(kwargs.get("executed_action_count") or 0)
        native_max = int(kwargs.get("native_max_steps") or 0)
        remaining = int(kwargs.get("remaining_native_decision_slots") or 0)
        eligible = (
            action_type in {"type_text", "answer"}
            and native_max > 0
            and executed * 5 >= native_max * 2
            and remaining >= 1
            and not self._used
            and self._pending_trigger is None
        )
        event = {"system_id": self.system_id, "eligible": eligible, "blocked": False, "reason": "not_eligible", "action_family": action_type or None, "executed_action_count": executed, "native_max_steps": native_max, "remaining_native_decision_slots": remaining}
        if eligible:
            self._pending_trigger = {"kind": "pre_result_action", "deferred_action_family": action_type, "executed": executed, "native_max": native_max}
            event.update({"blocked": True, "reason": "one_shot_late_evidence_consolidation", "history_message": "LATE EVIDENCE CONSOLIDATION QUEUED", "persist_history_message": False, "policy": self.system_id})
        self._event({"event": "result_action_review", **event})
        return event

    def close_episode(self, reason: str) -> dict[str, Any]:
        if self._delegate is not None:
            return self._delegate.close_episode(reason)
        event = {"event": "episode_closed", "reason": _clean(reason, 300), "pending_aux": self._pending_aux is not None, "pending_injection": self._pending_injection is not None}
        self._pending_aux = None
        self._pending_injection = None
        self._pending_trigger = None
        self._event(event)
        return event

    def audit_record(self) -> dict[str, Any]:
        if self._delegate is not None:
            audit = dict(self._delegate.audit_record())
            audit.update({"schema": "exploratory_direction_diag_policy_audit_v1", "system_id": self.system_id, "direction_mode": self.mode, "parent_delegate_schema": audit.get("schema")})
            return audit
        return {"schema": "exploratory_direction_diag_policy_audit_v1", "system_id": self.system_id, "direction_mode": self.mode, "state": {"used": self._used, "terminal_deferred": self._terminal_deferred, "pending_trigger": self._pending_trigger, "pending_aux": asdict(self._pending_aux) if self._pending_aux else None, "pending_injection": asdict(self._pending_injection) if self._pending_injection else None}, "counters": {"trigger_count": sum(1 for event in self._events if event.get("event") in {"aux_prepared", "terminal_review"} and (event.get("trigger") or event.get("blocked"))), "aux_call_count": sum(1 for event in self._events if event.get("event") in {"aux_committed", "aux_output_invalid"}), "injection_count": len(self._post_injection)}, "events": list(self._events), "post_injection": list(self._post_injection), "information_boundary": {"visible_rgb_only": True, "evaluator_visible": False, "hidden_ui_visible": False, "task_name_branching": False}}
