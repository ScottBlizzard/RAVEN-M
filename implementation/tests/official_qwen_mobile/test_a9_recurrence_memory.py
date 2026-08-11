from __future__ import annotations

import numpy as np
import pytest

from raven_m.official_qwen_mobile.a9_recurrence_memory import SparseRecurrenceCanaryMemory


def _screen(pattern: int, **hidden: object) -> dict:
    pixels = np.zeros((100, 80, 3), dtype=np.uint8)
    if pattern == 1:
        pixels[:, 40:] = 255
    elif pattern == 2:
        pixels[50:, :] = 255
    elif pattern == 3:
        pixels[20:80, 20:60] = 127
    return {"pixels": pixels, **hidden}


def _step(
    step: int,
    before: int,
    after: int,
    *,
    action: dict | None = None,
    summary: str = "Tap the visible control.",
    hidden_before: dict | None = None,
    hidden_after: dict | None = None,
) -> dict:
    return {
        "source_step": step,
        "action_summary": summary,
        "canonical_action": action or {"type": "tap", "x": 0.5, "y": 0.5},
        "before": _screen(before, **(hidden_before or {})),
        "after": _screen(after, **(hidden_after or {})),
        "transition": {"exactly_unchanged": before == after},
        "source_response_sha256": "a" * 64,
        "source_screenshot_sha256": "b" * 64,
    }


def test_a9_is_dormant_without_frozen_canary() -> None:
    memory = SparseRecurrenceCanaryMemory()
    assert memory.read()[0] == ""
    result = memory.observe_step(**_step(0, 0, 1))
    assert result["written"] is False
    assert memory.read({"evaluator_reward": 1, "ui_tree": "hidden"})[0] == ""
    audit = memory.audit_record()
    assert audit["activation_count"] == 0
    assert audit["model_calls_added"] == 0
    assert audit["action_override_count"] == 0


def test_a9_same_text_reentry_is_one_shot_and_auditable() -> None:
    memory = SparseRecurrenceCanaryMemory(max_chars=280)
    action = {"type": "type_text", "text": "Oberplanken, Liechtenstein", "clear_text": False}
    assert memory.observe_step(**_step(0, 0, 1, action=action))["written"] is False
    result = memory.observe_step(**_step(3, 2, 3, action=action))
    assert result["query_canary_written"] is True
    rendered, read = memory.read()
    assert read["activation_canary"] is True
    assert read["canary_kind"] == "QUERY_REENTRY"
    assert "Oberplanken" in rendered
    assert "recurrence" in rendered.casefold()
    assert "completion" not in rendered.casefold()
    assert len(rendered) <= 280
    assert memory.read()[0] == ""
    assert memory.audit_record()["delivered_count"] == 1


def test_a9_clear_then_same_text_is_classified() -> None:
    memory = SparseRecurrenceCanaryMemory()
    typed = {"type": "type_text", "text": "same query", "clear_text": False}
    memory.observe_step(**_step(0, 0, 1, action=typed))
    memory.observe_step(
        **_step(1, 1, 2, summary="Clear the search field.")
    )
    memory.observe_step(**_step(2, 2, 3, action=typed))
    rendered, read = memory.read()
    assert read["canary_kind"] == "QUERY_CLEAR_REENTRY"
    assert "clearing/re-entry" in rendered


def test_a9_exact_stationary_screen_requires_two_transitions() -> None:
    memory = SparseRecurrenceCanaryMemory()
    assert memory.observe_step(**_step(0, 1, 1))["cycle_canary_written"] is False
    assert memory.observe_step(**_step(1, 1, 1))["cycle_canary_written"] is True
    rendered, read = memory.read()
    assert read["canary_kind"] == "STATIONARY_SCREEN"
    assert "exact same visible screen" in rendered


def test_a9_detects_exact_period_two_navigation_cycle() -> None:
    memory = SparseRecurrenceCanaryMemory()
    memory.observe_step(**_step(0, 1, 2))
    memory.observe_step(**_step(1, 2, 1))
    result = memory.observe_step(**_step(2, 1, 2))
    assert result["cycle_canary_written"] is True
    rendered, read = memory.read()
    assert read["canary_kind"] == "NAVIGATION_CYCLE_P2"
    assert "period 2" in rendered


def test_a9_distinct_queries_and_noncycle_remain_silent() -> None:
    memory = SparseRecurrenceCanaryMemory()
    for step, (before, after, text) in enumerate(
        [(0, 1, "alpha"), (1, 2, "beta"), (2, 3, "gamma")]
    ):
        memory.observe_step(
            **_step(step, before, after, action={"type": "type_text", "text": text})
        )
    assert memory.read()[0] == ""
    assert memory.audit_record()["activation_count"] == 0


def test_a9_hidden_metadata_and_evaluator_cannot_change_canary() -> None:
    left = SparseRecurrenceCanaryMemory()
    right = SparseRecurrenceCanaryMemory()
    action = {"type": "type_text", "text": "needle"}
    for step in (0, 1):
        left.observe_step(
            **_step(
                step,
                step,
                step + 1,
                action=action,
                hidden_before={"evaluator_reward": 1, "ui_tree": "secret A"},
                hidden_after={"activity": "hidden package A"},
            ),
            evaluator_result="success",
        )
        right.observe_step(
            **_step(
                step,
                step,
                step + 1,
                action=action,
                hidden_before={"evaluator_reward": 0, "ui_tree": "secret B"},
                hidden_after={"activity": "hidden package B"},
            ),
            evaluator_result="failure",
        )
    left_text, left_read = left.read({"evaluator_reward": 1, "hidden_ui": "A"})
    right_text, right_read = right.read({"evaluator_reward": 0, "hidden_ui": "B"})
    assert left_text == right_text
    assert left_read["canary_kind"] == right_read["canary_kind"]
    assert left_read["evidence_sha256"] == right_read["evidence_sha256"]
    assert left.audit_record()["evaluator_used_for_decision"] is False
    assert left.audit_record()["hidden_ui_used_for_decision"] is False


def test_a9_capacities_are_bounded() -> None:
    memory = SparseRecurrenceCanaryMemory(
        max_query_keys=2,
        max_occurrences_per_query=2,
        max_trace_screens=7,
        event_log_capacity=3,
    )
    for step in range(12):
        memory.observe_step(
            **_step(
                step,
                step % 4,
                (step + 1) % 4,
                action={"type": "type_text", "text": f"query {step % 3}"},
            )
        )
    audit = memory.audit_record()
    assert len(audit["screen_trace"]) <= 7
    assert len(audit["query_occurrences"]) <= 2
    assert all(len(items) <= 2 for items in audit["query_occurrences"].values())
    assert len(audit["events"]) <= 3
    assert audit["guard_enabled"] is False
    assert audit["claim_boundary"] == "recurrence_only_never_failure_correctness_or_completion"


def test_a9_rejects_non_rgb_pixels() -> None:
    memory = SparseRecurrenceCanaryMemory()
    with pytest.raises(RuntimeError, match="RGB screenshot"):
        memory.observe_step(
            source_step=0,
            action_summary="Tap.",
            canonical_action={"type": "tap", "x": 0.5, "y": 0.5},
            before={"pixels": np.zeros((100, 80, 1), dtype=np.uint8)},
            after={"pixels": np.zeros((100, 80, 1), dtype=np.uint8)},
            source_response_sha256="a" * 64,
        )
