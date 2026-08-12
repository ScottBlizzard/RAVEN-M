from __future__ import annotations

import numpy as np
import pytest

from raven_m.official_qwen_mobile.a12_minimal_action_divergence import (
    A12IntegrityError,
    MinimalActionDivergenceMemory,
    render_memory,
)


GOAL = "Open the app."


def frame(value: int = 0) -> np.ndarray:
    return np.full((25, 40, 3), value, dtype=np.uint8)


def read(memory: MinimalActionDivergenceMemory, pixels=None, goal: str = GOAL):
    return memory.read({"goal": goal, "before": {"pixels": frame() if pixels is None else pixels}})


def observe(memory, step, action, before=None, after=None, summary="audit text"):
    before = frame() if before is None else before
    after = before if after is None else after
    return memory.observe_step(source_step=step, before={"pixels": before}, after={"pixels": after}, canonical_action=action, action_summary=summary)


TAP_A = {"type": "tap", "x": .1, "y": .1}
TAP_B = {"type": "tap", "x": .8, "y": .8}


def mature(memory: MinimalActionDivergenceMemory, action=TAP_A, start=0):
    first = observe(memory, start, action)
    read(memory)
    second = observe(memory, start + 1, action)
    return first, second


def test_first_support_then_ready_and_immediate_actual_read() -> None:
    memory = MinimalActionDivergenceMemory(); read(memory)
    first, second = mature(memory)
    assert first["support_count"] == 1 and not first["candidate_matured"]
    assert second["support_count"] == 2 and second["candidate_matured"]
    assert second["eligible_read_step"] == 2
    text, audit = read(memory)
    assert text == render_memory("tap cell 2/12,3/24")
    assert audit["actual_nonempty"] and audit["read_step"] == 2


def test_material_progress_and_context_loss_clear_evidence() -> None:
    memory = MinimalActionDivergenceMemory(); read(memory)
    observe(memory, 0, TAP_A)
    read(memory)
    result = observe(memory, 1, TAP_B, before=frame(), after=frame(255))
    assert result["context_invalidated"] and not memory.failure_records
    text, audit = read(memory, frame(255))
    assert text == "" and audit["reason"] == "initial_context_bound"


def test_context_uses_representative_not_drifting_previous_frame() -> None:
    memory = MinimalActionDivergenceMemory(); base = frame(); read(memory, base)
    representative = memory.active_context.representative_descriptor
    # Directly prove a frame cannot be retained merely because a chain of other
    # frames might have matched: comparison is always to this frozen object.
    memory.active_context.representative_descriptor = representative
    text, audit = read(memory, frame(255))
    assert text == "" and audit["reason"] == "context_reset"
    assert memory.context_epoch == 2


def test_near_equivalent_screen_preserves_active_context() -> None:
    memory = MinimalActionDivergenceMemory(); base = frame(); near = base.copy(); near[5, 5, 0] = 5
    read(memory, base)
    original_id = memory.active_context.context_id
    observe(memory, 0, TAP_A, before=near, after=near)
    text, audit = read(memory, near)
    assert text == "" and audit["screen_match_kind"] == "NEAR"
    assert memory.active_context.context_id == original_id


def test_different_action_families_count_independently() -> None:
    memory = MinimalActionDivergenceMemory(); read(memory)
    observe(memory, 0, TAP_A); read(memory)
    observe(memory, 1, TAP_B); read(memory)
    result = observe(memory, 2, TAP_A)
    assert result["candidate_matured"]
    assert len(memory.failure_records) == 2


def test_old_first_support_is_replaced_after_twelve_action_gap() -> None:
    memory = MinimalActionDivergenceMemory(); read(memory); observe(memory, 0, TAP_A)
    memory.last_observed_step = 12  # deterministic boundary fixture
    result = observe(memory, 13, TAP_A)
    record = next(iter(memory.failure_records.values()))
    assert result["reason"] == "old_first_support_replaced"
    assert record.first_support_step == 13 and record.support_count == 1


def test_cooldown_suppresses_and_candidate_never_reappears() -> None:
    memory = MinimalActionDivergenceMemory(); read(memory); mature(memory)
    assert read(memory)[0]
    # New action becomes READY only two read steps after the first delivery.
    observe(memory, 2, TAP_B); read(memory)
    observe(memory, 3, TAP_B)
    text, audit = read(memory)
    assert text == "" and audit["reason"] == "gate_cooldown_failed"
    assert next(iter(memory.failure_records.values())).state == "SUPPRESSED"
    assert read(memory)[0] == ""


def test_cooldown_at_four_is_allowed() -> None:
    memory = MinimalActionDivergenceMemory(); read(memory); mature(memory); read(memory)
    # Two unrelated first supports consume reads 3 and 4.
    observe(memory, 2, {"type": "press_back"}); read(memory)
    observe(memory, 3, {"type": "press_home"}); read(memory)
    observe(memory, 4, TAP_B); read(memory)
    observe(memory, 5, TAP_B)
    text, audit = read(memory)
    assert audit["read_step"] - 2 == 4
    assert text and audit["actual_nonempty"]


def test_episode_cap_rejects_sixth_candidate() -> None:
    memory = MinimalActionDivergenceMemory(); read(memory)
    memory.nonempty_read_count = 5
    memory.last_nonempty_read_step = None
    mature(memory)
    text, audit = read(memory)
    assert text == "" and audit["reason"] == "gate_episode_cap_failed"


def test_one_shot_and_summary_do_not_change_identity() -> None:
    memory = MinimalActionDivergenceMemory(); read(memory)
    observe(memory, 0, TAP_A, summary="first wording"); read(memory)
    observe(memory, 1, TAP_A, summary="different wording"); read(memory)
    result = observe(memory, 2, TAP_A, summary="third wording")
    assert result["reason"] == "already_delivered_for_equivalent_screen_action"


def test_more_than_one_ready_and_goal_change_raise_integrity() -> None:
    memory = MinimalActionDivergenceMemory(); read(memory); mature(memory)
    existing = next(iter(memory.failure_records.values()))
    duplicate = type(existing)(**{**existing.__dict__, "record_id": "other", "action_key_sha256": "other"})
    memory.failure_records["other"] = duplicate
    with pytest.raises(A12IntegrityError, match="more than one READY"):
        read(memory)
    other = MinimalActionDivergenceMemory(); read(other, goal="one")
    with pytest.raises(A12IntegrityError, match="goal changed"):
        read(other, goal="two")


def test_reset_and_post_read_causal_watch_are_audit_only() -> None:
    memory = MinimalActionDivergenceMemory(); read(memory); mature(memory); read(memory)
    observe(memory, 2, TAP_B, before=frame(), after=frame(255))
    watch = memory.post_read_watches[0]
    assert watch.next_action_diverged is True
    assert watch.material_progress_within_2 is True
    assert memory.nonempty_read_count == 1
    memory.reset()
    assert memory.read_count == 0 and not memory.delivered_failures
    assert not memory.read_events and not memory.post_read_watches


def test_rendering_contains_only_frozen_non_directive_template() -> None:
    text = render_memory("submit the same answer")
    assert text == "A12 memory: On this screen, submit the same answer produced no material visible change twice. Try a different action family or target. Retry is allowed; nothing is blocked."
    forbidden = ("the task failed", "the task succeeded", "completed", "verified", "correct action", "must click", "do not click", "terminate", "evaluator", "reward")
    assert not any(term in text.casefold() for term in forbidden)
    assert len(text) <= 240 and len(text.encode()) <= 480
