from __future__ import annotations

from raven_m.official_qwen_mobile.a1r2_compact_verified_pending import (
    CompactVerifiedPendingMemory,
    parse_memory_prefix,
)


def action(verified: str = "none", pending: str = "open app") -> str:
    return (
        f"MEMORY[observed=current screen; verified={verified}; pending={pending}] "
        "| Tap the visible control."
    )


def write(memory: CompactVerifiedPendingMemory, step: int, text: str) -> dict:
    return memory.write(
        source_step=step,
        action_summary=text,
        source_call_id=f"call-{step}",
        source_response_sha256=f"response-{step}",
        source_screenshot_sha256=f"screen-{step}",
    )


def test_parse_and_history_dedup() -> None:
    parsed = parse_memory_prefix(action("item A deleted", "delete item B"))
    assert parsed.valid
    assert parsed.history == "Tap the visible control."
    assert parsed.verified == "item A deleted"
    assert parsed.pending == "delete item B"


def test_invalid_prefix_does_not_mutate() -> None:
    memory = CompactVerifiedPendingMemory()
    event = write(memory, 0, "Tap the visible control.")
    assert event["write_kind"] == "invalid_prefix_state_unchanged"
    assert memory.audit_record()["active_ledger"] is None


def test_only_latest_verified_pending_pair_survives() -> None:
    memory = CompactVerifiedPendingMemory()
    write(memory, 0, action("none", "delete A"))
    write(memory, 1, action("A deleted", "delete B"))
    audit = memory.audit_record()
    assert audit["active_ledger"]["verified"] == "A deleted"
    assert audit["active_ledger"]["pending"] == "delete B"
    assert audit["counters"]["replacement_count"] == 1


def test_explicit_none_clears() -> None:
    memory = CompactVerifiedPendingMemory()
    write(memory, 0, action("none", "delete A"))
    event = write(memory, 1, action("A deleted", "none"))
    assert event["write_kind"] == "explicit_clear"
    assert memory.read({})[0] == ""


def test_prepare_commit_is_atomic() -> None:
    memory = CompactVerifiedPendingMemory()
    write(memory, 0, action("A located", "delete A"))
    text, read = memory.read({})
    assert read["nonempty"] and "VERIFIED: A located" in text
    assert memory.audit_record()["counters"]["nonempty_read_count"] == 0
    committed = memory.commit_injection(read["ticket_id"], "final-prompt")
    assert committed["exact_injected_text"] == text
    assert memory.audit_record()["counters"]["nonempty_read_count"] == 1


def test_cancel_does_not_consume_read() -> None:
    memory = CompactVerifiedPendingMemory()
    write(memory, 0, action("none", "delete A"))
    _, read = memory.read({})
    memory.cancel_injection(read["ticket_id"], "prompt_build_failed")
    assert memory.audit_record()["counters"]["nonempty_read_count"] == 0


def test_ttl_fails_closed() -> None:
    memory = CompactVerifiedPendingMemory(ttl_requests=2)
    write(memory, 0, action("none", "delete A"))
    text, read = memory.read({})
    memory.commit_injection(read["ticket_id"], "p1")
    assert text
    text2, read2 = memory.read({})
    assert text2
    memory.commit_injection(read2["ticket_id"], "p2")
    assert memory.read({})[0] == ""
    assert memory.audit_record()["counters"]["expiry_count"] == 1


def test_hidden_context_does_not_change_read() -> None:
    left = CompactVerifiedPendingMemory()
    right = CompactVerifiedPendingMemory()
    write(left, 0, action("A deleted", "delete B"))
    write(right, 0, action("A deleted", "delete B"))
    text_a, audit_a = left.read({"evaluator_reward": 1, "ui_tree": "secret"})
    text_b, audit_b = right.read({"evaluator_reward": 0, "ui_tree": "other"})
    assert text_a == text_b
    assert audit_a["rendered_sha256"] == audit_b["rendered_sha256"]
