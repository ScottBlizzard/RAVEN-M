from __future__ import annotations

import numpy as np
import pytest

from raven_m.official_qwen_mobile.a678_memory import (
    ExactVisualRevisitActionOutcomeCache,
    GoalItemStatusLedger,
    ShortTransitionEpisodicBuffer,
    extract_goal_items,
)


def _screen(pattern: int = 0, **hidden: object) -> dict:
    pixels = np.zeros((100, 80, 3), dtype=np.uint8)
    if pattern == 0:
        pixels[:, 40:] = 255
    elif pattern == 1:
        pixels[50:, :] = 255
    else:
        pixels[:, :] = 127
    return {"pixels": pixels, **hidden}


def _write_kwargs(step: int = 0, *, unchanged: bool = False) -> dict:
    return {
        "source_step": step,
        "action_summary": "Tap Bike Repairs and confirm deletion.",
        "canonical_action": {"type": "tap", "x": 0.4, "y": 0.6},
        "transition": {
            "exactly_unchanged": unchanged,
            "changed_pixel_fraction_gt_5": 0.0 if unchanged else 0.5,
            "ui_sha_changed": True,
            "activity_changed": True,
        },
        "before": _screen(0, evaluator_reward=1.0, ui_tree="hidden"),
        "after": _screen(1, evaluator_reward=0.0, ui_tree="different hidden"),
        "source_screenshot_sha256": "a" * 64,
        "source_response_sha256": "b" * 64,
    }


def test_a6_is_controller_written_bounded_and_preserves_action_prose() -> None:
    memory = ShortTransitionEpisodicBuffer(capacity=2, max_chars=240)
    original = _write_kwargs()["action_summary"]
    assert memory.read()[1]["nonempty"] is False
    assert memory.observe_step(**_write_kwargs())["written"] is True
    rendered, audit = memory.read()
    assert audit["nonempty"] is True
    assert "visible change" in rendered
    assert len(rendered) <= 240
    assert _write_kwargs()["action_summary"] == original
    assert not hasattr(memory, "history_summary")
    record = memory.audit_record()
    assert record["model_calls_added"] == 0
    assert record["evaluator_used_for_decision"] is False
    assert record["hidden_ui_used_for_decision"] is False
    assert record["action_override_count"] == 0


def test_a6_keeps_only_frozen_capacity() -> None:
    memory = ShortTransitionEpisodicBuffer(capacity=2)
    for step in range(4):
        memory.observe_step(**_write_kwargs(step))
    assert [entry["source_step"] for entry in memory.audit_record()["entries"]] == [2, 3]


def test_a7_extracts_only_explicit_goal_items() -> None:
    assert extract_goal_items(
        "Delete the following expenses: Bike Repairs, Tuition Fees, Public Transit."
    ) == ["Bike Repairs", "Tuition Fees", "Public Transit"]
    assert extract_goal_items('Create notes named "Alpha" and "Beta".') == ["Alpha", "Beta"]
    assert extract_goal_items("Open the browser and calculate the result.") == []


def test_a7_tracks_attempts_without_claiming_completion() -> None:
    goal = "Delete the following expenses: Bike Repairs, Tuition Fees, Public Transit."
    memory = GoalItemStatusLedger(max_chars=320)
    initial, initial_audit = memory.read({"goal": goal, "evaluator_reward": 1.0})
    assert initial_audit["goal_item_count"] == 3
    assert initial == ""
    assert initial_audit["withheld_until_observed_action"] is True
    update = memory.observe_step(**_write_kwargs())
    assert update["written"] is True
    rendered, _ = memory.read({"goal": goal, "hidden_ui": "must be ignored"})
    assert "Bike Repairs=attempted; visible change" in rendered
    assert "complete" not in rendered.casefold()
    record = memory.audit_record()
    assert record["claim_boundary"] == "attempt_status_only_never_completion"
    assert record["model_calls_added"] == 0


def test_a7_parse_inactive_is_valid_and_empty() -> None:
    memory = GoalItemStatusLedger()
    rendered, audit = memory.read({"goal": "Open the browser and calculate the result."})
    assert rendered == ""
    assert audit["parse_inactive"] is True
    assert memory.observe_step(**_write_kwargs())["written"] is False


def test_a7_rejects_cross_task_reuse() -> None:
    memory = GoalItemStatusLedger()
    memory.read({"goal": "Delete: A, B"})
    with pytest.raises(RuntimeError, match="episode-local"):
        memory.read({"goal": "Delete: C, D"})


def test_a8_exact_pixels_match_despite_hidden_metadata_changes() -> None:
    memory = ExactVisualRevisitActionOutcomeCache(max_entries=3, max_matches=2)
    memory.observe_step(**_write_kwargs())
    rendered, audit = memory.read(
        {"before": _screen(0, evaluator_reward=999, ui_tree="completely different")}
    )
    assert audit["exact_match"] is True
    assert audit["retrieved_count"] == 1
    assert "prior tap" in rendered
    assert len(rendered) <= 260
    record = memory.audit_record()
    assert record["near_match_enabled"] is False
    assert record["evaluator_used_for_decision"] is False
    assert record["hidden_ui_used_for_decision"] is False


def test_a8_visible_change_does_not_near_match() -> None:
    memory = ExactVisualRevisitActionOutcomeCache()
    memory.observe_step(**_write_kwargs())
    rendered, audit = memory.read({"before": _screen(1)})
    assert rendered == ""
    assert audit["exact_match"] is False


def test_a8_requires_visible_rgb_pixels() -> None:
    memory = ExactVisualRevisitActionOutcomeCache()
    with pytest.raises(RuntimeError, match="RGB screenshot"):
        memory.read({"before": {"pixels": np.zeros((4, 4, 3), dtype=np.uint8)}})

