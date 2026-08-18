from __future__ import annotations

from hashlib import sha256
from types import SimpleNamespace

import pytest

from raven_m.official_qwen_mobile.r15_derived_evidence_consolidation import (
    MAX_RAW_ACTIONS,
    EvidenceRehydrationIntegrityError,
    LateRawEvidenceRehydrationPolicy,
)


def _policy(counter=lambda base, final: len(final) - len(base)):
    return LateRawEvidenceRehydrationPolicy(text_delta_counter=counter)


def _review(
    policy: LateRawEvidenceRehydrationPolicy,
    *,
    step: int = 18,
    executed: int = 18,
    maximum: int = 22,
    remaining: int = 3,
    action: dict | None = None,
    terminal: str | None = None,
) -> dict:
    if action is None and terminal is None:
        action = {"type": "type_text", "text": "candidate-payload"}
    return policy.review_result_action(
        proposed_action=action,
        terminal_status=terminal,
        executed_action_count=executed,
        native_max_steps=maximum,
        remaining_native_decision_slots=remaining,
        request_step=step,
    )


def _row(step: int, *, action: str | None = None, thought: str | None = None) -> dict:
    return {
        "source_step": step,
        "thought": thought if thought is not None else f"I visibly observed value {step}.",
        "action_summary": action if action is not None else f"Record value {step} and continue.",
        "response_sha256": sha256(f"response-{step}".encode()).hexdigest(),
    }


def _prepare(
    policy: LateRawEvidenceRehydrationPolicy,
    *,
    trigger_step: int = 18,
    rows: list[dict] | None = None,
    extra: dict | None = None,
) -> dict:
    assert _review(policy, step=trigger_step)["blocked"] is True
    context = {
        "request_step": trigger_step + 1,
        "recent_prior_executed_responses": rows or [_row(i) for i in range(10, 18)],
    }
    context.update(extra or {})
    value = policy.prepare_direct_injection(context)
    assert value is not None
    return value


def _call(*, attempts: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        call_id="normal-call",
        request_sha256="1" * 64,
        response_sha256="2" * 64,
        raven_meta={"transport_attempts": attempts},
    )


def test_trigger_uses_exact_seven_tenths_integer_boundary() -> None:
    below = _review(_policy(), executed=6, maximum=10)
    exact = _review(_policy(), executed=7, maximum=10)
    above = _review(_policy(), executed=8, maximum=10)
    assert below["blocked"] is False
    assert exact["blocked"] is True
    assert above["blocked"] is True


def test_trigger_requires_result_family_remaining_slot_and_valid_budget() -> None:
    assert _review(_policy(), action={"type": "tap"})["blocked"] is False
    assert _review(_policy(), maximum=0)["blocked"] is False
    assert _review(_policy(), remaining=0)["blocked"] is False
    assert _review(_policy(), action={"type": "answer"})["blocked"] is True
    # A parsed terminal may still carry an empty canonical-action dictionary.
    assert _review(_policy(), action={}, terminal="success")["action_family"] == "terminate_success"


def test_direct_injection_uses_only_last_eight_complete_prior_responses() -> None:
    policy = _policy()
    rows = [_row(i) for i in range(10)]
    prepared = _prepare(policy, trigger_step=18, rows=rows)
    assert prepared["source_steps"] == list(range(2, 10))
    assert len(prepared["source_steps"]) == MAX_RAW_ACTIONS
    assert "source step 2" in prepared["injection_text"]
    assert "source step 9" in prepared["injection_text"]
    assert "source step 0" not in prepared["injection_text"]
    assert "THOUGHT: I visibly observed value 2." in prepared["injection_text"]
    assert "ACTION: Record value 2 and continue." in prepared["injection_text"]


def test_deferred_proposal_payload_is_never_stored_or_rendered() -> None:
    secret = "DEFERRED_WRONG_PAYLOAD_120_DO_NOT_RENDER"
    policy = _policy()
    review = _review(
        policy,
        action={"type": "type_text", "text": secret, "clear_text": False},
    )
    assert review["blocked"] is True
    assert review["proposal_payload_stored_or_rendered"] is False
    prepared = policy.prepare_direct_injection(
        {
            "request_step": 19,
            "recent_prior_executed_responses": [_row(i) for i in range(10, 18)],
        }
    )
    assert prepared is not None
    assert secret not in prepared["injection_text"]
    assert secret not in str(policy.audit_record())


def test_current_deferred_response_cannot_enter_prior_executed_window() -> None:
    policy = _policy()
    assert _review(policy, step=18)["blocked"] is True
    with pytest.raises(EvidenceRehydrationIntegrityError, match="source_not_prior_executed"):
        policy.prepare_direct_injection(
            {
                "request_step": 19,
                "recent_prior_executed_responses": [_row(18)],
            }
        )


def test_policy_is_zero_auxiliary_calls() -> None:
    policy = _policy()
    assert policy.max_auxiliary_calls == 0
    assert policy.prepare_aux({"request_step": 1}) is None
    assert policy.audit_record()["counters"]["auxiliary_model_call_count"] == 0


def test_commit_closes_exact_ticket_and_preserves_receipt_hashes() -> None:
    policy = _policy()
    prepared = _prepare(policy)
    committed = policy.commit_normal_injection(
        prepared["ticket_id"], "3" * 64, _call()
    )
    assert committed["ticket_id"] == prepared["ticket_id"]
    assert committed["text_sha256"] == sha256(
        prepared["injection_text"].encode()
    ).hexdigest()
    assert committed["source_steps"] == list(range(10, 18))
    audit = policy.audit_record()
    assert audit["state"]["pending_injection"] is None
    assert audit["counters"]["injection_commit_count"] == 1
    assert audit["counters"]["auxiliary_model_call_count"] == 0
    assert _review(policy, step=20, executed=20)["blocked"] is False


def test_commit_rejects_ticket_and_transport_drift() -> None:
    policy = _policy()
    prepared = _prepare(policy)
    with pytest.raises(EvidenceRehydrationIntegrityError, match="injection_ticket"):
        policy.commit_normal_injection("wrong-ticket", "3" * 64, _call())
    with pytest.raises(EvidenceRehydrationIntegrityError, match="normal_transport"):
        policy.commit_normal_injection(prepared["ticket_id"], "3" * 64, _call(attempts=2))


def test_cancel_is_audited_and_consumes_one_shot() -> None:
    policy = _policy()
    prepared = _prepare(policy)
    cancelled = policy.cancel_normal_injection(prepared["ticket_id"], "normal call failed")
    assert cancelled["ticket_id"] == prepared["ticket_id"]
    assert policy.audit_record()["state"]["pending_injection"] is None
    assert _review(policy, step=20, executed=20)["blocked"] is False
    with pytest.raises(EvidenceRehydrationIntegrityError, match="injection_ticket"):
        policy.commit_normal_injection(prepared["ticket_id"], "3" * 64, _call())


def test_hidden_evaluator_future_and_task_canaries_never_render() -> None:
    canaries = (
        "HIDDEN_UI_CANARY",
        "EVALUATOR_REWARD_CANARY",
        "FUTURE_ACTION_CANARY",
        "TASK_PACKAGE_CANARY",
    )
    rows = [_row(i) for i in range(10, 18)]
    rows[-1].update(
        {
            "hidden_ui": canaries[0],
            "evaluator_reward": canaries[1],
            "future_action": canaries[2],
            "package_name": canaries[3],
        }
    )
    prepared = _prepare(
        _policy(),
        rows=rows,
        extra={
            "hidden_ui": canaries[0],
            "evaluator_reward": canaries[1],
            "future_action": canaries[2],
            "task_package": canaries[3],
            "r2_memory_audit": {"evaluator": canaries[1]},
        },
    )
    assert all(canary not in prepared["injection_text"] for canary in canaries)


def test_next_request_and_source_hash_bindings_fail_closed() -> None:
    policy = _policy()
    assert _review(policy, step=18)["blocked"] is True
    with pytest.raises(EvidenceRehydrationIntegrityError, match="next_request_binding"):
        policy.prepare_direct_injection(
            {"request_step": 20, "recent_prior_executed_responses": [_row(17)]}
        )

    policy = _policy()
    assert _review(policy, step=18)["blocked"] is True
    bad = _row(17)
    bad["response_sha256"] = "not-a-sha"
    with pytest.raises(EvidenceRehydrationIntegrityError, match="source_response_hash"):
        policy.prepare_direct_injection(
            {"request_step": 19, "recent_prior_executed_responses": [bad]}
        )


def test_negative_exact_token_delta_is_rejected() -> None:
    policy = _policy(lambda base, final: -1)
    with pytest.raises(EvidenceRehydrationIntegrityError, match="negative_token_delta"):
        policy.count_advice_prompt_tokens("base", "final")
