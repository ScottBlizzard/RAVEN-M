from __future__ import annotations

from raven_m.official_qwen_mobile.a1r3_stale_resistant_pending import (
    StaleResistantPendingMemory,
    canonical_action_family,
    parse_memory_prefix,
)


def action(verified: str = "none", pending: str = "open app") -> str:
    return (
        f"MEMORY[observed=current; verified={verified}; pending={pending}] | "
        "Tap the visible control."
    )


def transition(changed: float) -> dict:
    return {
        "same_shape": True,
        "changed_pixel_fraction_gt_5": changed,
        "mean_absolute_difference": changed * 10,
    }


def observe(
    memory: StaleResistantPendingMemory,
    step: int,
    summary: str,
    *,
    changed: float = 0.5,
    canonical: dict | None = None,
) -> dict:
    return memory.observe_step(
        source_step=step,
        action_summary=summary,
        canonical_action=canonical or {"type": "tap", "x": 0.5, "y": 0.5},
        transition=transition(changed),
        source_call_id=f"call-{step}",
        source_response_sha256=f"response-{step}",
        source_screenshot_sha256=f"screen-{step}",
    )


def commit_read(memory: StaleResistantPendingMemory) -> str:
    text, audit = memory.read({})
    if text:
        memory.commit_injection(audit["ticket_id"], "prompt")
    return text


def test_parser_and_history_dedup_preserve_a1_contract() -> None:
    parsed = parse_memory_prefix(action("A deleted", "delete B"))
    assert parsed.valid
    assert parsed.history == "Tap the visible control."
    assert parsed.verified == "A deleted"
    assert parsed.pending == "delete B"


def test_identical_state_never_refreshes_source_step_or_provenance() -> None:
    memory = StaleResistantPendingMemory()
    first = observe(memory, 0, action("A found", "delete A"))
    second = observe(memory, 3, action("A found", "delete A"))
    audit = memory.audit_record()
    assert first["write_kind"] == "new_latest_state"
    assert second["write_kind"] == "same_state_not_refreshed"
    assert audit["active_ledger"]["source_step"] == 0
    assert audit["active_ledger"]["source_call_id"] == "call-0"
    assert audit["counters"]["same_state_nonrefresh_count"] == 1


def test_expiry_tombstone_prevents_immediate_stale_resurrection() -> None:
    memory = StaleResistantPendingMemory(ttl_requests=2)
    observe(memory, 0, action("none", "delete A"))
    assert commit_read(memory)
    observe(memory, 1, action("none", "delete A"))
    assert commit_read(memory)
    assert commit_read(memory) == ""
    event = observe(memory, 2, action("none", "delete A"))
    assert event["write_kind"] == "retired_state_rejected"
    assert memory.audit_record()["active_ledger"] is None


def test_distinct_state_can_replace_and_clears_tombstone() -> None:
    memory = StaleResistantPendingMemory(ttl_requests=2)
    observe(memory, 0, action("none", "delete A"))
    commit_read(memory)
    commit_read(memory)
    commit_read(memory)
    event = observe(memory, 2, action("A deleted", "delete B"))
    assert event["write_kind"] == "new_latest_state"
    assert memory.audit_record()["retired_state_key"] is None


def test_two_same_family_no_progress_actions_create_one_failure_fact() -> None:
    memory = StaleResistantPendingMemory()
    observe(memory, 0, action("none", "delete A"), changed=0.0)
    event = observe(
        memory,
        1,
        action("none", "delete A"),
        changed=0.0005,
        canonical={"type": "tap", "x": 0.51, "y": 0.49},
    )
    assert event["failure_evidence_created"] is True
    text = commit_read(memory)
    assert "AVOID REPEATING:" in text
    assert "produced no visible progress twice" in text
    assert memory.audit_record()["counters"]["failure_evidence_count"] == 1


def test_coordinate_jitter_is_same_bounded_action_family() -> None:
    left = canonical_action_family({"type": "tap", "x": 0.501, "y": 0.503})
    right = canonical_action_family({"type": "tap", "x": 0.512, "y": 0.491})
    assert left == right


def test_different_action_family_resets_support() -> None:
    memory = StaleResistantPendingMemory()
    observe(memory, 0, action(), changed=0.0)
    observe(
        memory,
        1,
        action(),
        changed=0.0,
        canonical={"type": "swipe", "x": 0.5, "y": 0.8, "x2": 0.5, "y2": 0.2},
    )
    assert memory.audit_record()["failed_attempt"] is None


def test_material_rgb_change_clears_failure_fact() -> None:
    memory = StaleResistantPendingMemory()
    observe(memory, 0, action(), changed=0.0)
    observe(memory, 1, action(), changed=0.0)
    assert memory.audit_record()["failed_attempt"] is not None
    observe(memory, 2, action(), changed=0.02)
    audit = memory.audit_record()
    assert audit["failed_attempt"] is None
    assert audit["counters"]["failure_clear_on_progress_count"] == 1


def test_atomic_prepare_commit_and_cancel() -> None:
    memory = StaleResistantPendingMemory()
    observe(memory, 0, action("A found", "delete A"))
    text, read = memory.read({})
    assert text and read["nonempty"]
    assert memory.audit_record()["counters"]["nonempty_read_count"] == 0
    committed = memory.commit_injection(read["ticket_id"], "prompt-hash")
    assert committed["exact_injected_text"] == text
    _, second = memory.read({})
    memory.cancel_injection(second["ticket_id"], "prompt_build_failed")
    assert memory.audit_record()["counters"]["cancelled_read_count"] == 1


def test_hidden_context_does_not_change_read_or_state() -> None:
    left = StaleResistantPendingMemory()
    right = StaleResistantPendingMemory()
    observe(left, 0, action("A found", "delete A"))
    observe(right, 0, action("A found", "delete A"))
    text_a, audit_a = left.read({"evaluator_reward": 1, "ui_tree": "secret"})
    text_b, audit_b = right.read({"evaluator_reward": 0, "ui_tree": "other"})
    assert text_a == text_b
    assert audit_a["rendered_sha256"] == audit_b["rendered_sha256"]


def test_capacity_and_decision_boundary_are_fixed() -> None:
    memory = StaleResistantPendingMemory()
    observe(memory, 0, action(), changed=0.0)
    observe(memory, 1, action(), changed=0.0)
    audit = memory.audit_record()
    assert audit["capacity"] == {
        "max_ledgers": 1,
        "max_tombstones": 1,
        "max_failed_attempts": 1,
        "max_pending_tickets": 1,
        "max_render_chars": 1100,
    }
    assert set(audit["decision_boundary"].values()) == {0, False}
