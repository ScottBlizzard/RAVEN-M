from __future__ import annotations

import json
import numpy as np

from raven_m.official_qwen_mobile.a10_v2_obligation_branch_frontier import (
    EvidenceMaturedObligationBranchFrontierMemory,
    MECHANISM_ID,
    describe_visual_state,
    visual_distance,
)


def frame(value: int) -> np.ndarray:
    return np.full((25, 8, 3), value, dtype=np.uint8)


def observe(memory, step, before, after, action=None, summary="tap option"):
    return memory.observe_step(source_step=step, before={"pixels": before}, after={"pixels": after}, canonical_action=action or {"type": "tap", "x": .5, "y": .5}, action_summary=summary)


def test_public_identity_and_rgb_descriptor() -> None:
    assert MECHANISM_ID == "a10_v2_evidence_matured_obligation_branch_frontier_v2"
    a = describe_visual_state(frame(0)); b = describe_visual_state(frame(0))
    assert a.exact_sha256 == b.exact_sha256
    assert visual_distance(a, b) == (0.0, 0.0, 0.0)


def test_two_no_progress_matures_t1_and_read_uses_frozen_score() -> None:
    memory = EvidenceMaturedObligationBranchFrontierMemory()
    pixels = frame(0); goal = "Open the app."
    memory.read({"goal": goal, "before": {"pixels": pixels}})
    assert not observe(memory, 0, pixels, pixels)["trigger_ids_enqueued"]
    memory.read({"goal": goal, "before": {"pixels": pixels}})
    result = observe(memory, 1, pixels, pixels)
    assert result["trigger_ids_enqueued"]
    text, audit = memory.read({"goal": goal, "before": {"pixels": pixels}})
    assert text and audit["trigger_kind"] == "BAD_BRANCH_REPEAT"
    assert audit["score"] >= .72


def test_one_closed_route_never_matures_t2_but_second_same_route_does() -> None:
    memory = EvidenceMaturedObligationBranchFrontierMemory(); goal = "Open the app."
    a, b = frame(0), frame(255)
    memory.read({"goal": goal, "before": {"pixels": a}})
    observe(memory, 0, a, b)
    memory.read({"goal": goal, "before": {"pixels": b}})
    first = observe(memory, 1, b, a, action={"type": "press_back"}, summary="return")
    assert not any("MATURED_CLOSED" in x for x in first["trigger_ids_enqueued"])
    assert memory.closed_route_watches and memory.closed_route_watches[0].stage != "MATURE_STAGNATION"
    memory.read({"goal": goal, "before": {"pixels": a}})
    observe(memory, 2, a, b)
    memory.read({"goal": goal, "before": {"pixels": b}})
    second = observe(memory, 3, b, a, action={"type": "press_back"}, summary="return")
    assert any(t.kind == "MATURED_CLOSED_ROUTE_STAGNATION" for t in memory.trigger_candidates)


def test_phase_switch_does_not_reset_global_cooldown() -> None:
    memory = EvidenceMaturedObligationBranchFrontierMemory(); pixels = frame(0); goal = "Open the app."
    memory.read({"goal": goal, "before": {"pixels": pixels}})
    observe(memory, 0, pixels, pixels); memory.read({"goal": goal, "before": {"pixels": pixels}})
    observe(memory, 1, pixels, pixels); text, _ = memory.read({"goal": goal, "before": {"pixels": pixels}})
    assert text
    previous = memory.last_nonempty_read_step
    memory.phase_id += 1; memory._current_phase_nonempty_reads = 0
    assert memory.last_nonempty_read_step == previous


def test_audit_is_bounded_and_exposes_required_sections() -> None:
    memory = EvidenceMaturedObligationBranchFrontierMemory(); pixels = frame(0)
    memory.read({"goal": "Open the app.", "before": {"pixels": pixels}})
    for step in range(20):
        observe(memory, step, pixels, pixels, action={"type": "tap", "x": (step % 12) / 12, "y": (step % 24) / 24})
        memory.read({"goal": "Open the app.", "before": {"pixels": pixels}})
    audit = memory.audit_record()
    assert {"goal", "reads", "triggers", "capacity", "causal_boundary"} <= audit.keys()
    assert audit["capacity"]["serialized_audit_bytes"] <= 131072
    assert len(json.dumps(audit, ensure_ascii=True).encode()) <= 131072


def test_true_frontier_branch_capacity_is_bounded() -> None:
    memory = EvidenceMaturedObligationBranchFrontierMemory()
    goal = "Delete these: Alpha, Bravo, Charlie, Delta, Echo, Foxtrot, Golf, Hotel."
    memory.read({"goal": goal, "before": {"pixels": frame(0)}})
    step = 0
    for screen_index in range(16):
        pixels = frame(screen_index * 16)
        for branch_index in range(6):
            observe(memory, step, pixels, pixels, action={"type": "tap", "x": (branch_index + .25) / 12, "y": (branch_index * 3 + .25) / 24}, summary="tap option")
            step += 1
    audit = memory.audit_record()
    assert len(memory.frontiers) == 16
    assert sum(len(frontier.branches) for frontier in memory.frontiers.values()) == 80
    assert len(memory.attempt_receipts) == 32
    assert audit["capacity"]["serialized_audit_bytes"] <= 131072
