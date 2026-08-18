"""One-shot late raw-evidence rehydration over frozen A1-R2."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Callable

SYSTEM_ID = "sys_r2_late_raw_evidence_rehydration_v1"
EXPERIMENT_ID = "SYS_R2_LRER_QWEN3VL32B_S20260806_G3407_V1"
AUDIT_SCHEMA = "sys_r2_late_raw_evidence_rehydration_audit_v1"
MIN_ELIGIBILITY_NUMERATOR = 7
MIN_ELIGIBILITY_DENOMINATOR = 10
RESULT_ACTION_FAMILIES = ("type_text", "answer", "terminate_success")
MAX_RAW_ACTIONS = 8
MAX_ACTION_CHARS = 700
MAX_TOTAL_RAW_CHARS = 4000
MAX_RENDER_CHARS = 5400


class EvidenceRehydrationIntegrityError(RuntimeError):
    pass


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _clean(value: Any, limit: int) -> str:
    if value is None:
        return ""
    text = " ".join(str(value).split()).strip()
    if "\x00" in text:
        raise EvidenceRehydrationIntegrityError("nul_text")
    return text[:limit]


@dataclass
class InjectionTicket:
    ticket_id: str
    trigger_request_step: int
    delivery_request_step: int
    text: str
    text_sha256: str
    source_steps: list[int]
    source_response_sha256s: list[str]


class LateRawEvidenceRehydrationPolicy:
    """Defer one late result proposal and rehydrate prior raw evidence once."""

    system_id = SYSTEM_ID
    max_auxiliary_calls = 0

    def __init__(self, *, text_delta_counter: Callable[[str, str], int]) -> None:
        self._text_delta_counter = text_delta_counter
        self._sequence = 0
        self._used = False
        self._pending_trigger: dict[str, Any] | None = None
        self._pending_injection: InjectionTicket | None = None
        self._events: list[dict[str, Any]] = []
        self._committed_injections: list[dict[str, Any]] = []

    def _id(self) -> str:
        self._sequence += 1
        return f"lrer_inject_{self._sequence:04d}"

    def _event(self, value: dict[str, Any]) -> None:
        self._events.append(dict(value))
        self._events = self._events[-96:]

    def prepare_aux(self, context: dict[str, Any]) -> None:
        return None

    def review_result_action(
        self,
        *,
        proposed_action: dict[str, Any] | None,
        terminal_status: str | None,
        executed_action_count: int,
        native_max_steps: int,
        remaining_native_decision_slots: int,
        request_step: int,
    ) -> dict[str, Any]:
        if isinstance(proposed_action, dict):
            family = str(proposed_action.get("type") or "")
        else:
            family = ""
        if not family and terminal_status == "success":
            family = "terminate_success"
        eligible = bool(
            family in RESULT_ACTION_FAMILIES
            and int(native_max_steps) > 0
            and int(executed_action_count) * MIN_ELIGIBILITY_DENOMINATOR
            >= int(native_max_steps) * MIN_ELIGIBILITY_NUMERATOR
            and int(remaining_native_decision_slots) >= 1
            and not self._used
            and self._pending_trigger is None
            and self._pending_injection is None
        )
        event = {
            "event": "result_action_review",
            "request_step": int(request_step),
            "action_family": family or None,
            "executed_action_count": int(executed_action_count),
            "native_max_steps": int(native_max_steps),
            "remaining_native_decision_slots": int(remaining_native_decision_slots),
            "eligible": eligible,
            "blocked": False,
            "proposal_payload_stored_or_rendered": False,
        }
        if eligible:
            self._pending_trigger = {
                "request_step": int(request_step),
                "action_family": family,
                "executed_action_count": int(executed_action_count),
                "native_max_steps": int(native_max_steps),
            }
            event.update(blocked=True, reason="one_shot_late_raw_evidence_rehydration")
        else:
            event["reason"] = "not_eligible"
        self._event(event)
        return event

    def prepare_direct_injection(self, context: dict[str, Any]) -> dict[str, Any] | None:
        trigger = self._pending_trigger
        if trigger is None:
            return None
        request_step = int(context.get("request_step") or 0)
        if request_step != int(trigger["request_step"]) + 1:
            raise EvidenceRehydrationIntegrityError("next_request_binding")
        rows = list(context.get("recent_prior_executed_responses") or [])[-MAX_RAW_ACTIONS:]
        rendered_rows, source_steps, source_hashes = [], [], []
        total_chars = 0
        for row in rows:
            if not isinstance(row, dict):
                raise EvidenceRehydrationIntegrityError("source_schema")
            source_step = int(row.get("source_step"))
            if source_step < 0 or source_step >= int(trigger["request_step"]):
                raise EvidenceRehydrationIntegrityError("source_not_prior_executed")
            response_sha = str(row.get("response_sha256") or "")
            if len(response_sha) != 64 or any(c not in "0123456789abcdef" for c in response_sha.lower()):
                raise EvidenceRehydrationIntegrityError("source_response_hash")
            raw_thought = _clean(row.get("thought"), MAX_ACTION_CHARS)
            raw_action = _clean(row.get("action_summary"), MAX_ACTION_CHARS)
            raw_response = _clean(
                " ".join(
                    part
                    for part in (
                        f"THOUGHT: {raw_thought}" if raw_thought else "",
                        f"ACTION: {raw_action}" if raw_action else "",
                    )
                    if part
                ),
                MAX_ACTION_CHARS,
            )
            if not raw_response:
                continue
            available = MAX_TOTAL_RAW_CHARS - total_chars
            if available <= 0:
                break
            raw_response = raw_response[:available]
            total_chars += len(raw_response)
            rendered_rows.append(f"- source step {source_step} (response {response_sha}): {raw_response}")
            source_steps.append(source_step)
            source_hashes.append(response_sha)
        if not rendered_rows:
            raise EvidenceRehydrationIntegrityError("empty_source_window")
        text = (
            "LATE MODEL-AUTHORED EVIDENCE (unverified; expires after this request):\n"
            + "\n".join(rendered_rows)
            + "\nBefore choosing any result action, reconstruct the exact task-relevant facts "
            "in step order, check that all required observations are covered, and "
            "independently recompute every arithmetic or logical constraint. Do not "
            "assume common, default, or example values. If evidence is insufficient "
            "or contradictory, gather visible evidence instead of guessing. The current "
            "screenshot is authoritative; decide the action yourself."
        )
        if len(text) > MAX_RENDER_CHARS:
            raise EvidenceRehydrationIntegrityError("render_cap")
        ticket = InjectionTicket(self._id(), int(trigger["request_step"]), request_step, text, _digest(text), source_steps, source_hashes)
        self._pending_trigger = None
        self._pending_injection = ticket
        self._used = True
        event = {"event": "direct_injection_prepared", "ticket_id": ticket.ticket_id, "trigger_request_step": ticket.trigger_request_step, "delivery_request_step": request_step, "text_sha256": ticket.text_sha256, "rendered_chars": len(text), "source_steps": source_steps, "source_response_sha256s": source_hashes}
        self._event(event)
        return {"ticket_id": ticket.ticket_id, "injection_text": ticket.text, "exact_injected_text_sha256": ticket.text_sha256, "source": "prior_executed_model_responses", "source_steps": source_steps, "source_response_sha256s": source_hashes}

    def commit_normal_injection(self, ticket_id: str, final_prompt_sha256: str, call: Any) -> dict[str, Any]:
        ticket = self._pending_injection
        if ticket is None or ticket.ticket_id != str(ticket_id):
            raise EvidenceRehydrationIntegrityError("injection_ticket")
        if (getattr(call, "raven_meta", {}) or {}).get("transport_attempts") != 1:
            raise EvidenceRehydrationIntegrityError("normal_transport")
        event = {"event": "normal_injection_committed", "ticket_id": ticket.ticket_id, "trigger_request_step": ticket.trigger_request_step, "delivery_request_step": ticket.delivery_request_step, "text": ticket.text, "text_sha256": ticket.text_sha256, "final_prompt_sha256": str(final_prompt_sha256), "normal_call_id": str(call.call_id), "normal_request_sha256": str(call.request_sha256), "normal_response_sha256": str(call.response_sha256), "transport_attempts": 1, "source_steps": list(ticket.source_steps), "source_response_sha256s": list(ticket.source_response_sha256s)}
        self._pending_injection = None
        self._committed_injections.append(event)
        self._event(event)
        return event

    def count_advice_prompt_tokens(self, base_text: str, final_text: str) -> int:
        value = int(self._text_delta_counter(base_text, final_text))
        if value < 0:
            raise EvidenceRehydrationIntegrityError("negative_token_delta")
        return value

    def cancel_normal_injection(self, ticket_id: str, reason: str) -> dict[str, Any]:
        if self._pending_injection is None or self._pending_injection.ticket_id != str(ticket_id):
            raise EvidenceRehydrationIntegrityError("injection_cancel")
        self._pending_injection = None
        event = {"event": "injection_cancelled", "ticket_id": str(ticket_id), "reason": _clean(reason, 300)}
        self._event(event)
        return event

    def observe_transition(self, **kwargs: Any) -> dict[str, Any]:
        event = {"event": "transition_observed", "source_step": int(kwargs.get("source_step") or 0), "changed_pixel_fraction_gt_5": (kwargs.get("transition") or {}).get("changed_pixel_fraction_gt_5")}
        self._event(event)
        return event

    def close_episode(self, reason: str) -> dict[str, Any]:
        event = {"event": "episode_closed", "reason": _clean(reason, 300), "pending_trigger": self._pending_trigger is not None, "pending_injection": self._pending_injection is not None}
        self._pending_trigger = None
        self._pending_injection = None
        self._event(event)
        return event

    def audit_record(self) -> dict[str, Any]:
        return {
            "schema": AUDIT_SCHEMA, "system_id": SYSTEM_ID, "experiment_id": EXPERIMENT_ID,
            "trigger": {"min_fraction": [MIN_ELIGIBILITY_NUMERATOR, MIN_ELIGIBILITY_DENOMINATOR], "result_action_families": list(RESULT_ACTION_FAMILIES), "one_shot": True, "fallback": False},
            "state": {"used": self._used, "pending_trigger": self._pending_trigger, "pending_injection": asdict(self._pending_injection) if self._pending_injection else None},
            "counters": {
                "eligible_count": sum(int(bool(e.get("eligible"))) for e in self._events if e.get("event") == "result_action_review"),
                "deferral_count": sum(int(bool(e.get("blocked"))) for e in self._events if e.get("event") == "result_action_review"),
                "direct_injection_prepare_count": sum(int(e.get("event") == "direct_injection_prepared") for e in self._events),
                "injection_commit_count": len(self._committed_injections), "auxiliary_model_call_count": 0,
            },
            "events": list(self._events), "committed_injections": list(self._committed_injections),
            "information_boundary": {"goal_used_for_trigger": False, "prior_executed_raw_model_thought_and_action": True, "current_visible_rgb": True, "r2_parent_unchanged": True, "deferred_proposal_payload_rendered": False, "hidden_ui": False, "evaluator_or_reward": False, "future_information": False, "task_or_app_branch": False},
        }
