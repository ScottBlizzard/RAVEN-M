from __future__ import annotations

from raven_m.official_qwen_mobile.a1r4_writer_resilient_pending import (
    MECHANISM_ID,
    WRITER_REMINDER,
    WriterResilientPendingMemory,
)


def _observe(memory: WriterResilientPendingMemory, step: int, summary: str) -> dict:
    return memory.observe_step(
        source_step=step,
        action_summary=summary,
        canonical_action={"type": "tap", "x": 0.5, "y": 0.5},
        transition={"same_shape": True, "changed_pixel_fraction_gt_5": 0.0},
        source_call_id=str(step),
        source_response_sha256=str(step),
        source_screenshot_sha256=str(step),
    )


def test_reminder_is_present_before_any_valid_writer_output() -> None:
    memory = WriterResilientPendingMemory()
    text, audit = memory.read({})
    assert text == WRITER_REMINDER
    assert audit["writer_reminder_injected"] is True
    assert audit["semantic_memory_injected"] is False
    memory.commit_injection(audit["ticket_id"], "prompt")
    record = memory.audit_record()
    assert record["mechanism_id"] == MECHANISM_ID
    assert record["writer_interface_active"] is True
    assert record["active"] is False


def test_valid_ledger_replaces_bootstrap_reminder() -> None:
    memory = WriterResilientPendingMemory()
    _observe(
        memory,
        0,
        "MEMORY[observed=x; verified=A deleted; pending=delete B] | Tap B.",
    )
    text, audit = memory.read({})
    assert "VERIFIED: A deleted" in text
    assert "PENDING: delete B" in text
    assert WRITER_REMINDER not in text
    assert audit["semantic_memory_injected"] is True
    memory.commit_injection(audit["ticket_id"], "prompt")
    assert memory.audit_record()["active"] is True


def test_invalid_output_does_not_erase_accepted_ledger() -> None:
    memory = WriterResilientPendingMemory()
    _observe(
        memory,
        0,
        "MEMORY[observed=x; verified=A deleted; pending=delete B] | Tap B.",
    )
    event = _observe(memory, 1, "Tap the visible row.")
    assert event["write_kind"] == "invalid_prefix_state_unchanged"
    text, _ = memory.read({})
    assert "PENDING: delete B" in text


def test_identity_is_not_inherited_as_r3() -> None:
    memory = WriterResilientPendingMemory()
    event = _observe(memory, 0, "Tap the app.")
    assert event["mechanism_id"] == MECHANISM_ID
    _, audit = memory.read({})
    assert audit["mechanism_id"] == MECHANISM_ID
