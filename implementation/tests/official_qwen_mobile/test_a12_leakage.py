from __future__ import annotations

import numpy as np

from raven_m.official_qwen_mobile.a12_minimal_action_divergence import MinimalActionDivergenceMemory


def frame() -> np.ndarray:
    return np.zeros((25, 40, 3), dtype=np.uint8)


def test_hidden_metadata_cannot_change_transition_or_read() -> None:
    left = MinimalActionDivergenceMemory(); right = MinimalActionDivergenceMemory()
    hidden_left = {"evaluator_reward": 1, "task_success": True, "task_name": "secret-a", "episode_id": "a", "ui_tree": [1], "foreground": "x", "future_screenshot": "x"}
    hidden_right = {"evaluator_reward": 0, "task_success": False, "task_name": "secret-b", "episode_id": "b", "ui_tree": [2], "foreground": "y", "future_screenshot": "y"}
    for memory, hidden in ((left, hidden_left), (right, hidden_right)):
        text, audit = memory.read({"goal": "same", "before": {"pixels": frame(), **hidden}, **hidden})
        assert text == "" and audit["reason"] == "initial_context_bound"
    action = {"type": "tap", "x": .5, "y": .5}
    first_left = left.observe_step(source_step=0, before={"pixels": frame()}, after={"pixels": frame()}, canonical_action=action, action_summary="one", **hidden_left)
    first_right = right.observe_step(source_step=0, before={"pixels": frame()}, after={"pixels": frame()}, canonical_action=action, action_summary="different", **hidden_right)
    assert first_left == first_right
    assert left.decision_state() == right.decision_state()
    left.read({"goal": "same", "before": {"pixels": frame()}}); right.read({"goal": "same", "before": {"pixels": frame()}})
    second_left = left.observe_step(source_step=1, before={"pixels": frame()}, after={"pixels": frame()}, canonical_action=action, action_summary="alpha", **hidden_left)
    second_right = right.observe_step(source_step=1, before={"pixels": frame()}, after={"pixels": frame()}, canonical_action=action, action_summary="beta", **hidden_right)
    assert second_left == second_right
    text_left, audit_left = left.read({"goal": "same", "before": {"pixels": frame()}, **hidden_left})
    text_right, audit_right = right.read({"goal": "same", "before": {"pixels": frame()}, **hidden_right})
    assert text_left == text_right
    assert audit_left == audit_right
    assert left.decision_state() == right.decision_state()


def test_query_is_hash_only_not_trigger_or_render_input() -> None:
    outputs = []
    for goal in ("Delete private object A", "Completely unrelated query B"):
        memory = MinimalActionDivergenceMemory(); pixels = frame()
        memory.read({"goal": goal, "before": {"pixels": pixels}})
        action = {"type": "press_back"}
        memory.observe_step(source_step=0, before={"pixels": pixels}, after={"pixels": pixels}, canonical_action=action, action_summary="x")
        memory.read({"goal": goal, "before": {"pixels": pixels}})
        result = memory.observe_step(source_step=1, before={"pixels": pixels}, after={"pixels": pixels}, canonical_action=action, action_summary="y")
        text, audit = memory.read({"goal": goal, "before": {"pixels": pixels}})
        outputs.append((result["evidence_signature"], text, {k: v for k, v in audit.items() if k != "mechanism_id"}))
    assert outputs[0] == outputs[1]
