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
