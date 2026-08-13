from __future__ import annotations

from hashlib import sha256

import pytest

from raven_m.official_qwen_mobile.a1r1_bpr_v2 import (
    A1R1_BPR_V2_SUFFIX,
    BoundedPendingReceiptV2,
    parse_pend,
)


def _observe(memory: BoundedPendingReceiptV2, step: int, summary: str) -> dict:
    return memory.observe_step(
        source_step=step,
        action_summary=summary,
        canonical_action={"type": "tap", "x": 0.5, "y": 0.5},
        transition={},
        source_call_id=f"call-{step}",
        source_response_sha256=f"response-{step}",
        source_screenshot_sha256=f"screen-{step}",
    )


def _read(memory: BoundedPendingReceiptV2, screen: str) -> tuple[str, dict]:
    return memory.read({"before": {"pixel_sha256": screen}, "goal": "g"})


def test_frozen_suffix_exact_bytes() -> None:
    raw = A1R1_BPR_V2_SUFFIX.encode("utf-8")
    assert len(raw) == 686
    assert sha256(raw).hexdigest() == "6d399443083139e0aad8241cc0e4a949e311348a09d68c032397104e163d610b"


@pytest.mark.parametrize(
    ("summary", "valid", "pair", "clear", "history"),
    [
        ("PEND[op=delete zucchini;proof=zucchini absent] | Tap delete.", True, True, False, "Tap delete."),
        ("PEND[op=none;proof=none] | Continue.", True, True, True, "Continue."),
        ("PEND[op=none;proof=visible] | Continue.", True, False, False, "Continue."),
        ("PEND[op=None;proof=None] | Continue.", True, True, False, "Continue."),
        ("Thought PEND[op=x;proof=y] | Tap.", False, False, False, "Thought PEND[op=x;proof=y] | Tap."),
    ],
)
def test_parser_and_history_dedup(summary: str, valid: bool, pair: bool, clear: bool, history: str) -> None:
    parsed = parse_pend(summary)
    assert (parsed.valid, parsed.pair_valid, parsed.clear, parsed.history) == (valid, pair, clear, history)


def test_read_prepare_is_atomic_until_commit_and_cancel() -> None:
    memory = BoundedPendingReceiptV2()
    _observe(memory, 0, "PEND[op=save playlist;proof=playlist visible in Downloads] | Tap Save.")
    text, audit = _read(memory, "rgb-1")
    assert text and audit["reason"] == "prepared_not_consumed"
    assert memory.counters["nonempty_read_count"] == 0
    memory.cancel_injection(audit["ticket_id"], "prompt_build_failure")
    assert memory.counters["nonempty_read_count"] == 0
    text, audit = _read(memory, "rgb-1")
    committed = memory.commit_injection(audit["ticket_id"], "prompt-sha")
    assert committed["exact_injected_text"] == text
    assert memory.counters["nonempty_read_count"] == 1


def test_cooldown_same_rgb_second_read_and_tombstone() -> None:
    memory = BoundedPendingReceiptV2()
    _observe(memory, 0, "PEND[op=delete item;proof=item absent] | Tap delete.")
    _, first = _read(memory, "rgb-a")
    memory.commit_injection(first["ticket_id"], "p1")
    assert _read(memory, "rgb-b")[1]["reason"] == "cooldown"
    assert _read(memory, "rgb-a")[1]["reason"] == "same_rgb"
    _, second = _read(memory, "rgb-b")
    committed = memory.commit_injection(second["ticket_id"], "p2")
    assert committed["read_cap_triggered"] is True
    assert committed["retirement"]["reason"] == "read_cap"
    assert memory.active is None and memory.tombstone is not None
    rejected = _observe(memory, 4, "PEND[op=delete item;proof=item absent] | Tap delete.")
    assert rejected["write_kind"] == "refractory_reject_state_unchanged"


def test_ttl_same_op_no_refresh_and_semantic_paraphrase_replaces() -> None:
    memory = BoundedPendingReceiptV2()
    _observe(memory, 0, "PEND[op=confirm deletion;proof=item absent] | Tap delete.")
    expiry = memory.active.expiry_before_read_step
    same = _observe(memory, 2, "PEND[op=CONFIRM   DELETION;proof=new proof] | Inspect.")
    assert same["write_kind"] == "same_op_text_update_no_refresh"
    assert memory.active.expiry_before_read_step == expiry
    different = _observe(memory, 3, "PEND[op=verify item removed;proof=item absent] | Inspect.")
    assert different["write_kind"] == "new_receipt"
    assert memory.active.expiry_before_read_step == 8


def test_expiry_occurs_before_source_plus_five_read() -> None:
    memory = BoundedPendingReceiptV2()
    _observe(memory, 0, "PEND[op=save;proof=saved] | Tap.")
    for screen in ("0", "1", "2", "3", "4"):
        text, audit = _read(memory, screen)
        if text:
            memory.cancel_injection(audit["ticket_id"], "test")
    text, audit = _read(memory, "5")
    assert text == ""
    assert audit["retirement"]["reason"] == "expiry"


def test_empty_read_arm_keeps_write_lifecycle_but_never_injects() -> None:
    memory = BoundedPendingReceiptV2(read_enabled=False)
    _observe(memory, 0, "PEND[op=save;proof=saved] | Tap.")
    text, audit = _read(memory, "rgb")
    assert text == "" and audit["reason"] == "empty_read_ablation"
    assert memory.active is not None
    assert memory.counters["nonempty_read_count"] == 0


def test_bounded_audit_and_forbidden_decision_inputs() -> None:
    memory = BoundedPendingReceiptV2()
    _observe(memory, 0, "PEND[op=save;proof=saved] | Tap.")
    audit = memory.audit_record()
    assert len(str(audit).encode("utf-8")) < 16_384
    assert audit["decision_boundary"] == {
        "model_calls_added": 0,
        "guard_enabled": False,
        "action_override_count": 0,
        "forced_termination_count": 0,
        "hidden_ui_used_for_decision": False,
        "evaluator_used_for_decision": False,
        "future_information_used": False,
    }
