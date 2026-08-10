from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from raven_m.official_qwen_mobile.a345_memory import (
    FrozenWorkflowMemory,
    OnlinePageGraphMemory,
    ProactiveFoldedContextMemory,
)


def _screen(inverted: bool = False, **hidden: object) -> dict:
    pixels = np.zeros((100, 80, 3), dtype=np.uint8)
    pixels[:, 40:] = 255
    if inverted:
        pixels = 255 - pixels
    return {"pixels": pixels, **hidden}


def _workflow(workflow_id: str = "wf_calendar", **updates: object) -> dict:
    value = {
        "workflow_id": workflow_id,
        "donor_task": "EasyCalendarDonor",
        "donor_seed": 17,
        "donor_family": "calendar event",
        "keywords": ["calendar", "event", "create"],
        "workflow": "Open the add form, fill every requested field, save, then verify the list.",
        "source_episode_sha256": "a" * 64,
        "source_evaluator_reward": 1.0,
    }
    value.update(updates)
    return value


def test_a3_requires_complete_prefix_then_exposes_later_read() -> None:
    memory = ProactiveFoldedContextMemory(max_chars=400)
    malformed = "CONTEXT[folded_history=open;ui_state=form] | tap save"
    assert memory.record_protocol(malformed)["fields_complete"] is False
    assert memory.observe_step(action_summary=malformed, source_step=0)["written"] is False

    action = (
        "CONTEXT[folded_history=open form;ui_state=name filled;recent=tapped name] "
        "| tap save"
    )
    assert memory.record_protocol(action)["fields_complete"] is True
    write = memory.observe_step(
        action_summary=action,
        source_step=1,
        transition={"exactly_unchanged": False},
    )
    assert write["written"] is True
    rendered, audit = memory.read()
    assert audit["nonempty"] is True
    assert "name filled" in rendered
    assert "CONTEXT[" not in memory.history_summary(action)
    assert memory.history_summary(action) == "tap save"
    record = memory.audit_record()
    assert record["model_calls_added"] == 0
    assert record["hidden_state_used_for_decision"] is False
    assert record["action_override_count"] == 0


def test_a4_rejects_unsuccessful_or_duplicate_donors() -> None:
    with pytest.raises(ValueError, match="successes only"):
        FrozenWorkflowMemory(bank=[_workflow(source_evaluator_reward=0.0)])
    with pytest.raises(ValueError, match="unique"):
        FrozenWorkflowMemory(bank=[_workflow(), _workflow()])


def test_a4_is_frozen_deterministic_and_does_not_inject_zero_overlap() -> None:
    bank = [
        _workflow("wf_b"),
        _workflow("wf_a", source_episode_sha256="b" * 64),
    ]
    frozen_input = deepcopy(bank)
    memory = FrozenWorkflowMemory(bank=bank, max_chars=500)
    rendered, audit = memory.read({"goal": "Create a calendar event"})
    assert audit["retrieved_ids"] == ["wf_a"]
    assert "wf_a" in rendered
    empty, empty_audit = memory.read({"goal": "multiply two browser numbers"})
    assert empty == ""
    assert empty_audit["nonempty"] is False
    assert bank == frozen_input
    record = memory.audit_record()
    assert record["write_attempt_count"] == 0
    assert record["scored_suite_updates_bank"] is False
    assert record["model_calls_added"] == 0
    assert not hasattr(memory, "observe_step")


def test_a5_uses_only_visible_pixels_and_exposes_written_edge_later() -> None:
    before = _screen(secret_ui_tree="must not be used")
    after = _screen(inverted=True, evaluator_reward=1.0)
    memory = OnlinePageGraphMemory(max_edges=2, max_chars=600, max_hamming=0)
    action = "GRAPH[node=form;relation=save opens list;facts=name filled;avoid=repeat save] | tap save"
    assert memory.record_protocol(action)["fields_complete"] is True
    write = memory.observe_step(
        action_summary=action,
        source_step=0,
        before=before,
        after=after,
        canonical_action={"type": "tap", "x": 0.5, "y": 0.5},
        transition={"exactly_unchanged": False},
    )
    assert write["written"] is True
    rendered, audit = memory.read({"before": _screen(different_hidden_metadata=True)})
    assert audit["nonempty"] is True
    assert audit["retrieved_count"] == 1
    assert "repeat save" in rendered
    assert "GRAPH[" not in memory.history_summary(action)
    record = memory.audit_record()
    assert record["model_calls_added"] == 0
    assert record["hidden_state_used_for_decision"] is False
    assert record["action_override_count"] == 0


def test_a5_rejects_missing_pixels_and_malformed_prefix() -> None:
    memory = OnlinePageGraphMemory()
    with pytest.raises(RuntimeError, match="RGB screenshot"):
        memory.read({"before": {"pixels": np.zeros((4, 4, 3), dtype=np.uint8)}})
    result = memory.observe_step(
        action_summary="GRAPH[node=form;facts=x] | tap",
        source_step=0,
        before=_screen(),
        after=_screen(inverted=True),
        canonical_action={"type": "tap"},
        transition={},
    )
    assert result["written"] is False

