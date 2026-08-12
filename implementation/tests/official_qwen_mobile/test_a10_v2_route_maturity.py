from __future__ import annotations

import numpy as np

from raven_m.official_qwen_mobile.a10_v2_obligation_branch_frontier import EvidenceMaturedObligationBranchFrontierMemory


def f(value: int) -> np.ndarray:
    return np.full((25, 8, 3), value, dtype=np.uint8)


def read(memory, goal, pixels):
    return memory.read({"goal": goal, "before": {"pixels": pixels}})


def obs(memory, step, before, after, action, summary):
    return memory.observe_step(source_step=step, before={"pixels": before}, after={"pixels": after}, canonical_action=action, action_summary=summary)


def test_t0_partial_obligation_escape() -> None:
    memory = EvidenceMaturedObligationBranchFrontierMemory(); goal = "Delete these: Alpha, Bravo"
    read(memory, goal, f(0))
    obs(memory, 0, f(0), f(64), {"type": "tap", "x": .5, "y": .5}, "delete Alpha")
    read(memory, goal, f(64)); obs(memory, 1, f(64), f(128), {"type": "press_back"}, "return")
    read(memory, goal, f(128)); obs(memory, 2, f(128), f(192), {"type": "press_back"}, "return")
    assert any(t.kind == "PARTIAL_OBLIGATION_ESCAPE" for t in memory.trigger_candidates)


def test_t3_requires_three_bad_two_branches_repeat_and_no_active_higher_trigger() -> None:
    memory = EvidenceMaturedObligationBranchFrontierMemory(); goal = "Open the app."; pixels = f(0)
    read(memory, goal, pixels)
    actions = [
        ({"type": "tap", "x": .1, "y": .1}, "tap A"),
        ({"type": "tap", "x": .1, "y": .1}, "tap A"),
        ({"type": "tap", "x": .8, "y": .8}, "tap B"),
        ({"type": "tap", "x": .8, "y": .8}, "tap B"),
        ({"type": "tap", "x": .5, "y": .2}, "tap C"),
        ({"type": "tap", "x": .3, "y": .7}, "tap D"),
        ({"type": "tap", "x": .6, "y": .4}, "tap E"),
    ]
    for step, (action, summary) in enumerate(actions):
        obs(memory, step, pixels, pixels, action, summary)
        read(memory, goal, pixels)
    assert any(t.kind == "MATURED_FRONTIER_EXHAUSTION" for t in memory.trigger_candidates)


def test_t4_same_value_reentry_after_bad_outcome() -> None:
    memory = EvidenceMaturedObligationBranchFrontierMemory(); goal = "Open the app."; pixels = f(0)
    read(memory, goal, pixels)
    action = {"type": "type_text", "text": "same value", "clear_text": False}
    obs(memory, 0, pixels, pixels, action, "type same value")
    read(memory, goal, pixels)
    obs(memory, 1, pixels, pixels, action, "type same value")
    assert any(t.kind == "VALUE_REENTRY_AFTER_BAD_OUTCOME" for t in memory.trigger_candidates)


def test_no_group_phase_watch_is_capacity_one_and_matures_after_four_actions() -> None:
    memory = EvidenceMaturedObligationBranchFrontierMemory(); goal = "Open the app."
    read(memory, goal, f(0))
    obs(memory, 0, f(0), f(8), {"type": "tap", "x": .5, "y": .5}, "save")
    assert memory._no_anchor_phase_watch is not None
    for step, (before, after) in enumerate(((f(8), f(32)), (f(32), f(64)), (f(64), f(96))), start=1):
        read(memory, goal, before)
        result = obs(memory, step, before, after, {"type": "press_back"}, "return")
    assert result["phase_switch"] is True
    assert memory.phase_id == 1
    assert memory._no_anchor_phase_watch is None


def test_late_return_removes_durable_branch_event_before_recording_late() -> None:
    memory = EvidenceMaturedObligationBranchFrontierMemory(); goal = "Open the app."
    read(memory, goal, f(0))
    obs(memory, 0, f(0), f(32), {"type": "tap", "x": .2, "y": .2}, "open")
    for step, (before, after) in enumerate(((f(32), f(64)), (f(64), f(96)), (f(96), f(128))), start=1):
        result = obs(memory, step, before, after, {"type": "tap", "x": .3, "y": .3}, "inspect")
    assert any(item["outcome"] == "DURABLE_DEPARTURE" for item in result["route_resolutions"])
    result = obs(memory, 4, f(128), f(0), {"type": "press_back"}, "return")
    assert any(item["outcome"] == "LATE_RETURN" for item in result["route_resolutions"])
    assert all(
        not (event_step == 3 and outcome == "DURABLE_DEPARTURE")
        for frontier in memory.frontiers.values()
        for branch in frontier.branches.values()
        for event_step, outcome in branch.events
    )
