from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

import numpy as np
import pytest

from raven_m.official_qwen_mobile.sys_trrc_recovery import (
    OneShotTriggeredRecoveryPolicy,
    RecoveryIntegrityError,
    parse_auxiliary_response,
)


def _screen(value: int = 30) -> np.ndarray:
    return np.full((90, 160, 3), value, dtype=np.uint8)


def _tap() -> dict:
    return {"type": "tap", "x": 0.25, "y": 0.5}


SCREEN_SHA = "c" * 64


def _project_tokens(system_prompt: str, user_prompt: str, screenshot_path: str) -> dict:
    assert system_prompt and user_prompt and screenshot_path == "screen.png"
    return {
        "schema": "test_projection",
        "current_screenshot_sha256": SCREEN_SHA,
        "exact_multimodal_input_tokens": 500,
    }


def _policy(mode: str) -> OneShotTriggeredRecoveryPolicy:
    return OneShotTriggeredRecoveryPolicy(
        mode=mode, token_projector=_project_tokens
    )


def _context(**values) -> dict:
    return {
        "request_step": 2,
        "goal": "goal",
        "r2_memory_audit": {},
        "recent_action_summaries": [],
        "current_screenshot_path": "screen.png",
        "current_screenshot_sha256": SCREEN_SHA,
        **values,
    }


def _observe(
    policy: OneShotTriggeredRecoveryPolicy,
    step: int,
    *,
    changed: bool = False,
    x: float = 0.25,
) -> dict:
    before = _screen(30)
    after = _screen(180) if changed else before.copy()
    fraction = 1.0 if changed else 0.0
    return policy.observe_transition(
        source_step=step,
        action_summary=f"action {step}",
        canonical_action={"type": "tap", "x": x, "y": 0.5},
        before_pixels=before,
        after_pixels=after,
        transition={
            "same_shape": True,
            "changed_pixel_fraction_gt_5": fraction,
            "remaining_native_decision_slots": 99,
        },
        source_call_id=f"call-{step}",
        source_response_sha256=sha256(f"response-{step}".encode()).hexdigest(),
        source_before_screenshot_sha256=sha256(f"before-{step}".encode()).hexdigest(),
        source_after_screenshot_sha256=sha256(f"after-{step}".encode()).hexdigest(),
    )


def _trigger(policy: OneShotTriggeredRecoveryPolicy) -> None:
    assert _observe(policy, 0)["trigger_created"] is False
    assert _observe(policy, 1)["trigger_created"] is True


@dataclass
class FakeCall:
    content: str
    call_id: str = "aux-call"
    request_sha256: str = "a" * 64
    prompt_sha256: str = ""
    image_sha256: str = SCREEN_SHA
    response_sha256: str = ""
    usage: dict = None  # type: ignore[assignment]
    raven_meta: dict = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.usage = {"prompt_tokens": 500, "completion_tokens": 50, "total_tokens": 550}
        self.raven_meta = {"transport_attempts": 1, "latency_seconds": 2.0}
        self.response_sha256 = sha256(self.content.encode("utf-8")).hexdigest()


def _aux_call(prepared: dict, content: str) -> FakeCall:
    return FakeCall(content, prompt_sha256=prepared["request_text_sha256"])


def test_two_consecutive_same_family_no_progress_triggers_once() -> None:
    policy = _policy("full")
    _trigger(policy)
    assert policy.audit_record()["counters"]["trigger_count"] == 1
    for step in range(2, 8):
        _observe(policy, step)
    assert policy.audit_record()["counters"]["trigger_count"] == 1


def test_material_change_or_family_change_resets_support() -> None:
    policy = _policy("full")
    _observe(policy, 0)
    assert _observe(policy, 1, changed=True)["trigger_created"] is False
    _observe(policy, 2)
    assert _observe(policy, 3, x=0.8)["trigger_created"] is False
    assert policy.audit_record()["counters"]["trigger_count"] == 0


def test_detector_mode_never_calls_aux() -> None:
    policy = OneShotTriggeredRecoveryPolicy(mode="detector")
    _trigger(policy)
    assert policy.prepare_aux(
        {"request_step": 2, "goal": "goal", "r2_memory_audit": {}, "recent_action_summaries": []}
    ) is None
    audit = policy.audit_record()
    assert audit["state"]["aux_used"] is True
    assert audit["counters"]["aux_prepared_count"] == 0


def test_full_aux_and_normal_injection_are_two_phase() -> None:
    policy = _policy("full")
    _trigger(policy)
    prepared = policy.prepare_aux(
        _context(
            goal="Delete the target records",
            r2_memory_audit={
                "active_ledger": {"verified": "none", "pending": "delete records"}
            },
            recent_action_summaries=["open menu", "tap item"],
        )
    )
    assert prepared is not None and prepared["max_tokens"] == 192
    response = (
        "ASSESSMENT: The repeated action has not changed the visible screen.\n"
        "RECOMMENDATION: Reassess which visible control addresses the pending requirement.\n"
        "VISIBLE_CHECK: The next screen should expose a different relevant state."
    )
    committed = policy.commit_aux(prepared["ticket_id"], _aux_call(prepared, response))
    assert committed["valid_output"] is True
    normal = FakeCall("normal", call_id="normal-call")
    event = policy.commit_normal_injection(
        committed["injection_ticket_id"], "f" * 64, normal
    )
    assert event["normal_call_id"] == "normal-call"
    audit = policy.audit_record()
    assert audit["counters"]["aux_committed_count"] == 1
    assert audit["counters"]["injection_committed_count"] == 1


def test_invalid_aux_output_is_charged_but_not_injected() -> None:
    policy = _policy("generic")
    _trigger(policy)
    prepared = policy.prepare_aux(_context())
    assert prepared is not None
    event = policy.commit_aux(
        prepared["ticket_id"],
        _aux_call(
            prepared,
            'Action: click here\n<tool_call>{"name":"mobile_use"}</tool_call>',
        ),
    )
    assert event["valid_output"] is False
    assert event["injection_text"] is None
    assert policy.audit_record()["counters"]["aux_output_invalid_count"] == 1


def test_parser_and_transition_scalar_fail_closed() -> None:
    parsed = parse_auxiliary_response(
        "ASSESSMENT: The screen is unchanged.\n"
        "RECOMMENDATION: Reconsider the unresolved requirement.\n"
        "VISIBLE_CHECK: Look for a different relevant state."
    )
    assert parsed["rendered"].startswith(
        "AUXILIARY ADVICE (non-authoritative; expires after this request):"
    )
    with pytest.raises(RecoveryIntegrityError, match="aux_forbidden_content"):
        parse_auxiliary_response(
            "ASSESSMENT: x\nRECOMMENDATION: Action: tap 1,2\nVISIBLE_CHECK: y"
        )
    policy = _policy("full")
    with pytest.raises(RecoveryIntegrityError, match="transition_fraction_mismatch"):
        policy.observe_transition(
            source_step=0,
            action_summary="x",
            canonical_action=_tap(),
            before_pixels=_screen(30),
            after_pixels=_screen(180),
            transition={
                "same_shape": True,
                "changed_pixel_fraction_gt_5": 0.0,
                "remaining_native_decision_slots": 99,
            },
            source_call_id="c",
            source_response_sha256="r" * 64,
            source_before_screenshot_sha256="b" * 64,
            source_after_screenshot_sha256="a" * 64,
        )


def test_each_episode_has_fresh_state() -> None:
    left = _policy("full")
    right = _policy("full")
    _trigger(left)
    assert left.audit_record()["counters"]["trigger_count"] == 1
    assert right.audit_record()["counters"]["trigger_count"] == 0


def test_last_native_slot_cannot_create_an_unread_trigger() -> None:
    policy = _policy("full")
    _observe(policy, 0)
    before = _screen(30)
    event = policy.observe_transition(
        source_step=1,
        action_summary="last action",
        canonical_action=_tap(),
        before_pixels=before,
        after_pixels=before.copy(),
        transition={
            "same_shape": True,
            "changed_pixel_fraction_gt_5": 0.0,
            "remaining_native_decision_slots": 0,
        },
        source_call_id="last-call",
        source_response_sha256="r" * 64,
        source_before_screenshot_sha256="b" * 64,
        source_after_screenshot_sha256="a" * 64,
    )
    assert event["reason"] == "no_remaining_native_decision_slot"
    assert policy.audit_record()["counters"]["trigger_count"] == 0


@pytest.mark.parametrize(
    ("usage", "latency", "expected"),
    [
        (
            {"prompt_tokens": 500, "completion_tokens": 7693, "total_tokens": 8193},
            1.0,
            "aux_total_token_boundary",
        ),
        (
            {"prompt_tokens": 500, "completion_tokens": 50, "total_tokens": 550},
            60.0001,
            "aux_latency_boundary",
        ),
    ],
)
def test_aux_resource_boundaries_fail_closed(usage, latency, expected) -> None:
    policy = _policy("full")
    _trigger(policy)
    prepared = policy.prepare_aux(_context())
    call = _aux_call(
        prepared, "ASSESSMENT: x\nRECOMMENDATION: y\nVISIBLE_CHECK: z"
    )
    call.usage = usage
    call.raven_meta["latency_seconds"] = latency
    with pytest.raises(RecoveryIntegrityError, match=expected):
        policy.commit_aux(prepared["ticket_id"], call)


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("prompt_sha256", "0" * 64, "aux_prompt_sha256_mismatch"),
        ("image_sha256", "1" * 64, "aux_image_sha256_mismatch"),
        ("response_sha256", "2" * 64, "aux_response_sha256_mismatch"),
    ],
)
def test_aux_transport_hash_chain_fails_closed(field, value, expected) -> None:
    policy = _policy("full")
    _trigger(policy)
    prepared = policy.prepare_aux(_context())
    call = _aux_call(
        prepared, "ASSESSMENT: x\nRECOMMENDATION: y\nVISIBLE_CHECK: z"
    )
    setattr(call, field, value)
    with pytest.raises(RecoveryIntegrityError, match=expected):
        policy.commit_aux(prepared["ticket_id"], call)


def test_projected_multimodal_budget_is_checked_before_aux_ticket() -> None:
    def oversized(system_prompt: str, user_prompt: str, screenshot_path: str) -> dict:
        return {
            "current_screenshot_sha256": SCREEN_SHA,
            "exact_multimodal_input_tokens": 8001,
        }

    policy = OneShotTriggeredRecoveryPolicy(
        mode="full", token_projector=oversized
    )
    _trigger(policy)
    with pytest.raises(
        RecoveryIntegrityError, match="aux_projected_total_token_boundary"
    ):
        policy.prepare_aux(_context())
    assert policy.audit_record()["counters"]["aux_prepared_count"] == 0


def test_server_prompt_token_attestation_must_match_projection() -> None:
    policy = _policy("full")
    _trigger(policy)
    prepared = policy.prepare_aux(_context())
    call = _aux_call(
        prepared, "ASSESSMENT: x\nRECOMMENDATION: y\nVISIBLE_CHECK: z"
    )
    call.usage = {
        "prompt_tokens": 501,
        "completion_tokens": 50,
        "total_tokens": 551,
    }
    with pytest.raises(
        RecoveryIntegrityError, match="aux_prompt_token_attestation_mismatch"
    ):
        policy.commit_aux(prepared["ticket_id"], call)
