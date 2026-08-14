from __future__ import annotations

from raven_m.official_qwen_mobile.a1r5_transition_invalidated_pending import (
    MECHANISM_ID,
    TransitionInvalidatedPendingMemory,
    WRITER_REMINDER,
)


def _observe(memory: TransitionInvalidatedPendingMemory, step: int, summary: str, changed: float) -> dict:
    return memory.observe_step(
        source_step=step,
        action_summary=summary,
        canonical_action={"type": "tap", "x": 0.2, "y": 0.3},
        transition={"same_shape": True, "changed_pixel_fraction_gt_5": changed},
        source_call_id=f"c{step}",
        source_response_sha256=f"r{step}",
        source_screenshot_sha256=f"s{step}",
    )


def test_invalid_prefix_material_transition_retires_stale_ledger() -> None:
    memory = TransitionInvalidatedPendingMemory()
    _observe(memory, 0, "MEMORY[observed=page A; verified=none; pending=open item] | tap", 0.2)
    assert memory.active is not None
    event = _observe(memory, 1, "I opened the next page.", 0.4)
    assert event["write_kind"] == "invalid_prefix_transition_invalidated"
    assert memory.active is None
    text, audit = memory.read({})
    assert text == WRITER_REMINDER
    assert audit["writer_reminder_injected"] is True


def test_invalid_prefix_no_progress_keeps_ledger_for_failure_evidence() -> None:
    memory = TransitionInvalidatedPendingMemory()
    _observe(memory, 0, "MEMORY[observed=page A; verified=none; pending=open item] | tap", 0.2)
    event = _observe(memory, 1, "I tapped again.", 0.0)
    assert event["write_kind"] == "invalid_prefix_state_unchanged"
    assert memory.active is not None
    assert memory.counters["transition_invalidation_count"] == 0


def test_valid_prefix_material_transition_keeps_current_attestation() -> None:
    memory = TransitionInvalidatedPendingMemory()
    event = _observe(memory, 0, "MEMORY[observed=page B; verified=item opened; pending=delete item] | tap", 0.6)
    assert event["prefix_valid"] is True
    assert memory.active is not None
    text, audit = memory.read({})
    assert "PENDING: delete item" in text
    assert audit["mechanism_id"] == MECHANISM_ID


def test_audit_identity_and_boundary() -> None:
    memory = TransitionInvalidatedPendingMemory()
    audit = memory.audit_record()
    assert audit["mechanism_id"] == MECHANISM_ID
    assert audit["counters"]["transition_invalidation_count"] == 0
    assert audit["decision_boundary"]["extra_model_calls"] == 0
