from raven_m.official_qwen_mobile.numeric_answer_guard import (
    NumericAnswerConsistencyGuard,
)


def test_corrects_observed_v2_duration_sum_failure() -> None:
    guard = NumericAnswerConsistencyGuard()
    action, event = guard.review(
        proposed_action={"type": "answer", "text": "165"},
        action_summary=(
            'MEMORY[observed="Intense day" (1:45:00) and "Quick Sweat" '
            '(1:15:00); verified=two; pending=calculate] | Calculate the total '
            'duration of "Intense day" (1 hour 45 minutes) and "Quick Sweat" '
            '(1 hour 15 minutes) in minutes.'
        ),
    )
    assert action == {"type": "answer", "text": "180"}
    assert event["duration_minutes"] == [105, 75]
    assert event["overridden"] is True
    assert guard.audit_record()["counters"]["action_override_count"] == 1


def test_leaves_consistent_answer_unchanged() -> None:
    guard = NumericAnswerConsistencyGuard()
    action, event = guard.review(
        proposed_action={"type": "answer", "text": "180"},
        action_summary="Calculate the total: 1:45:00 and 1:15:00.",
    )
    assert action == {"type": "answer", "text": "180"}
    assert event["eligible"] is True
    assert event["overridden"] is False


def test_fail_closed_outside_explicit_additive_integer_duration() -> None:
    guard = NumericAnswerConsistencyGuard()
    cases = [
        ({"type": "click", "x": 0.5, "y": 0.5}, "total 1:00 and 2:00"),
        ({"type": "answer", "text": "three"}, "total 1:00 and 2:00"),
        ({"type": "answer", "text": "60"}, "duration 1:00 and 2:00"),
        ({"type": "answer", "text": "60"}, "calculate total duration 1:00"),
    ]
    for proposed, summary in cases:
        reviewed, event = guard.review(
            proposed_action=proposed, action_summary=summary
        )
        assert reviewed == proposed
        assert event["overridden"] is False
    assert guard.audit_record()["counters"]["action_override_count"] == 0


def test_memory_prefix_durations_are_not_double_counted() -> None:
    guard = NumericAnswerConsistencyGuard()
    action, event = guard.review(
        proposed_action={"type": "answer", "text": "180"},
        action_summary=(
            "MEMORY[observed=1:45 and 1:15; pending=sum] | "
            "Calculate total duration: 1:45 and 1:15."
        ),
    )
    assert action["text"] == "180"
    assert event["duration_minutes"] == [105, 75]


def test_one_shot_terminal_block_requires_pending_r2_read_after_wait() -> None:
    guard = NumericAnswerConsistencyGuard()
    memory_read = {
        "exact_injected_text": (
            "Latest compact task ledger from your own previous Action:\n"
            "VERIFIED: playlist and songs created\n"
            "PENDING: export the playlist to Downloads"
        )
    }
    first = guard.review_terminal(
        terminal_status="success",
        memory_read=memory_read,
        previous_executed_action={"type": "wait", "duration_ms": 2000},
        remaining_native_decision_slots=1,
    )
    assert first["blocked"] is True
    assert "current screenshot" in first["history_message"]
    second = guard.review_terminal(
        terminal_status="success",
        memory_read=memory_read,
        previous_executed_action={"type": "wait", "duration_ms": 2000},
        remaining_native_decision_slots=1,
    )
    assert second["blocked"] is False
    assert guard.audit_record()["counters"]["terminal_block_count"] == 1


def test_terminal_block_fails_closed_without_all_three_conditions() -> None:
    cases = [
        ("failure", "PENDING: export", {"type": "wait"}),
        ("success", "PENDING: none", {"type": "wait"}),
        ("success", "PENDING: export", {"type": "tap"}),
    ]
    for terminal, text, previous in cases:
        guard = NumericAnswerConsistencyGuard()
        event = guard.review_terminal(
            terminal_status=terminal,
            memory_read={"exact_injected_text": text},
            previous_executed_action=previous,
            remaining_native_decision_slots=1,
        )
        assert event["blocked"] is False

    final_slot = NumericAnswerConsistencyGuard().review_terminal(
        terminal_status="success",
        memory_read={"exact_injected_text": "PENDING: save"},
        previous_executed_action={"type": "wait"},
        remaining_native_decision_slots=0,
    )
    assert final_slot["blocked"] is False
