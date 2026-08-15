from __future__ import annotations

import math

import pytest

from raven_m.official_qwen_mobile.a1r2_compact_verified_pending import (
    CompactVerifiedPendingMemory,
)
from raven_m.official_qwen_mobile.a1r3v3_one_shot_cnr import (
    OneShotControllerNonprogressReceiptMemory,
    canonical_action_family,
    is_no_rgb_progress,
)


def _summary(pending: str = "delete the remaining item") -> str:
    return f"MEMORY[observed=screen; verified=first item deleted; pending={pending}] | Tap the next visible item."


def _observe(
    memory: OneShotControllerNonprogressReceiptMemory,
    step: int,
    action: dict,
    fraction: float = 0.0,
):
    return memory.observe_step(
        source_step=step,
        action_summary=_summary(),
        canonical_action=action,
        transition={
            "same_shape": True,
            "changed_pixel_fraction_gt_5": fraction,
        },
        source_call_id=f"call-{step}",
        source_response_sha256=f"response-{step}",
        source_screenshot_sha256=f"before-{step}",
        before={"screenshot_sha256": f"before-{step}"},
        after={"screenshot_sha256": f"after-{step}"},
    )


def _commit(memory: OneShotControllerNonprogressReceiptMemory):
    text, audit = memory.read({})
    if text:
        memory.commit_injection(audit["ticket_id"], f"prompt-{audit['request_step']}")
    return text, audit


def test_no_trigger_path_is_byte_equivalent_to_a1r2():
    parent = CompactVerifiedPendingMemory()
    child = OneShotControllerNonprogressReceiptMemory()
    kwargs = dict(
        source_step=0,
        action_summary=_summary(),
        source_call_id="call-0",
        source_response_sha256="response-0",
        source_screenshot_sha256="screen-0",
    )
    parent.write(**kwargs)
    child.observe_step(
        **kwargs,
        canonical_action={"type": "tap", "x": 0.5, "y": 0.5},
        transition={"same_shape": True, "changed_pixel_fraction_gt_5": 0.5},
    )
    parent_text, parent_read = parent.read({})
    child_text, child_read = child.read({})
    assert child_text == parent_text
    assert child_read["rendered_sha256"] == parent_read["rendered_sha256"]


def test_two_consecutive_same_family_no_progress_create_one_receipt():
    memory = OneShotControllerNonprogressReceiptMemory()
    action1 = {"type": "tap", "x": 0.501, "y": 0.201}
    action2 = {"type": "tap", "x": 0.519, "y": 0.219}
    _observe(memory, 0, action1)
    _commit(memory)
    event = _observe(memory, 1, action2, 0.001)
    assert event["cnr_receipt_created"] is True
    _commit(memory)
    text, read = _commit(memory)
    assert "RECENT OBSERVATION: The last two same tap area actions" in text
    assert read["failure_evidence_prepared"] is True
    assert memory.audit_record()["counters"]["cnr_receipt_committed_read_count"] == 1


def test_material_change_and_family_change_reset_support():
    memory = OneShotControllerNonprogressReceiptMemory()
    tap = {"type": "tap", "x": 0.5, "y": 0.2}
    _observe(memory, 0, tap)
    _commit(memory)
    _observe(memory, 1, tap, 0.0010001)
    _commit(memory)
    _observe(memory, 2, tap)
    _commit(memory)
    event = _observe(memory, 3, {"type": "tap", "x": 0.8, "y": 0.2})
    assert event["cnr_receipt_created"] is False


def test_episode_is_strictly_one_shot():
    memory = OneShotControllerNonprogressReceiptMemory()
    tap = {"type": "tap", "x": 0.5, "y": 0.2}
    _observe(memory, 0, tap)
    _commit(memory)
    _observe(memory, 1, tap)
    _commit(memory)
    for step in range(2, 8):
        _observe(memory, step, tap)
        _commit(memory)
    counters = memory.audit_record()["counters"]
    assert counters["cnr_receipt_creation_count"] == 1
    assert counters["cnr_receipt_committed_read_count"] == 1
    assert counters["cnr_suppressed_after_one_shot_cap_count"] > 0


def test_receipt_only_read_and_cancel_retry_window():
    memory = OneShotControllerNonprogressReceiptMemory()
    tap = {"type": "tap", "x": 0.5, "y": 0.2}
    _observe(memory, 0, tap)
    memory.active = None
    _commit(memory)
    _observe(memory, 1, tap)
    memory.active = None
    _commit(memory)
    text, read = memory.read({})
    assert text.startswith("RECENT OBSERVATION")
    memory.cancel_injection(read["ticket_id"], "synthetic")
    text2, read2 = memory.read({})
    assert text2 == text
    memory.commit_injection(read2["ticket_id"], "prompt")


def test_receipt_expires_fail_closed():
    memory = OneShotControllerNonprogressReceiptMemory()
    tap = {"type": "tap", "x": 0.5, "y": 0.2}
    _observe(memory, 0, tap)
    _commit(memory)
    _observe(memory, 1, tap)
    memory.read_call_count = 4
    text, read = memory.read({})
    assert read["failure_evidence_injected"] is False
    assert memory.audit_record()["counters"]["cnr_receipt_expiry_count"] == 1


@pytest.mark.parametrize(
    ("fraction", "expected"),
    [(0.000999, True), (0.001, True), (0.001001, False), (math.nan, False)],
)
def test_no_progress_boundaries(fraction, expected):
    assert (
        is_no_rgb_progress(
            {"same_shape": True, "changed_pixel_fraction_gt_5": fraction}
        )
        is expected
    )
    assert is_no_rgb_progress(
        {"same_shape": False, "changed_pixel_fraction_gt_5": fraction}
    ) is False


def test_action_family_boundaries_and_no_coordinate_leak():
    assert canonical_action_family({"type": "tap", "x": 0.5249, "y": 0.2})[0] == "tap:10:4"
    assert canonical_action_family({"type": "tap", "x": 0.525, "y": 0.2})[0] == "tap:11:4"
    assert canonical_action_family({"type": "long_press", "x": 0.5, "y": 0.2})[0].startswith("long_press:")
    assert canonical_action_family({"type": "swipe", "x": 0.5, "y": 0.5, "x2": 0.6, "y2": 0.6})[0] == "swipe:right"
    assert canonical_action_family({"type": "type_text", "text": "  Hello   WORLD "}) == canonical_action_family({"type": "type_text", "text": "hello world"})
    assert canonical_action_family({"type": "tap", "x": float("nan"), "y": 0.2}) is None


def test_audit_only_inputs_cannot_change_decision_state():
    left = OneShotControllerNonprogressReceiptMemory()
    right = OneShotControllerNonprogressReceiptMemory()
    action = {"type": "tap", "x": 0.5, "y": 0.2}
    for step in range(2):
        _observe(left, step, action)
        right.observe_step(
            source_step=step,
            action_summary=_summary(),
            canonical_action=action,
            transition={"same_shape": True, "changed_pixel_fraction_gt_5": 0.0},
            source_call_id=f"call-{step}",
            source_response_sha256=f"response-{step}",
            source_screenshot_sha256=f"before-{step}",
            before={
                "screenshot_sha256": f"other-before-{step}",
                "foreground": {"activity": "secret"},
                "task_name": "changed",
                "reward": 1,
            },
            after={"screenshot_sha256": f"other-after-{step}"},
        )
        _commit(left)
        _commit(right)
    left_audit = left.audit_record()
    right_audit = right.audit_record()
    assert left_audit["counters"] == right_audit["counters"]
    assert left_audit["last_committed_read"]["exact_injected_text"] == right_audit["last_committed_read"]["exact_injected_text"]


def test_state_and_audit_are_bounded():
    memory = OneShotControllerNonprogressReceiptMemory()
    tap = {"type": "tap", "x": 0.5, "y": 0.2}
    for step in range(200):
        _observe(memory, step, tap)
        _commit(memory)
    audit = memory.audit_record()
    assert len(audit["receipt_events"]) <= 1
    assert len(audit["read_events"]) <= 1
    assert len(audit["lifecycle_events"]) <= 12
    assert len(str(audit).encode("utf-8")) < 16_384
