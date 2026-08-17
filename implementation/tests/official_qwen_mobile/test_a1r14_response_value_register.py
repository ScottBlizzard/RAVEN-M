from __future__ import annotations

from raven_m.official_qwen_mobile.a1r14_response_value_register import (
    ResponseGroundedValueRegisterMemory,
)


GOAL = "Click the button 5 times, remember the numbers displayed, and enter their product."
RESPONSES = (
    "Thought: The current number '1' is shown and I need to collect all five numbers.\nAction: Click.",
    "Thought: The current number shown is 8, which I need to record.\nAction: Click.",
    "Thought: I have seen the number 10 and should record all five numbers.\nAction: Click.",
    "Thought: The current screen shows the number 7, one of the numbers I need to record.\nAction: Click.",
    "Thought: The current screen shows the number 2; I will have all five numbers needed.\nAction: Click.",
)


def _write(memory: ResponseGroundedValueRegisterMemory, step: int, response: str) -> dict:
    text, read = memory.read({"goal": GOAL})
    if text:
        memory.commit_injection(read["ticket_id"], f"prompt-{step}")
    action_summary = (
        "MEMORY[observed=number displayed; verified=none; pending=record each number] | Click."
        if step == 0
        else "Click the button."
    )
    memory.write(
        source_step=step,
        action_summary=action_summary,
        source_call_id=f"c{step}",
        source_response_sha256=f"r{step}",
        source_screenshot_sha256=f"s{step}",
    )
    return memory.write_model_response(
        source_step=step,
        model_response=response,
        action_summary=action_summary,
        source_call_id=f"c{step}",
        source_response_sha256=f"r{step}",
        source_screenshot_sha256=f"s{step}",
    )


def test_exact_five_live_response_phrases_are_retained_in_order() -> None:
    memory = ResponseGroundedValueRegisterMemory()
    for step, response in enumerate(RESPONSES):
        assert _write(memory, step, response)["accepted"] is True
    text, audit = memory.read({"goal": GOAL})
    assert "observed integer sequence = [1, 8, 10, 7, 2]." in text
    assert audit["response_grounded_value_register"]["response_append_count"] == 5


def test_goal_must_contain_collection_and_arithmetic_intent() -> None:
    memory = ResponseGroundedValueRegisterMemory()
    memory.read({"goal": "Click a button and open the next page."})
    event = memory.write_model_response(
        source_step=0,
        model_response=RESPONSES[0],
        action_summary="Click.",
        source_call_id="c",
        source_response_sha256="r",
        source_screenshot_sha256="s",
    )
    assert event["accepted"] is False
    assert event["reason"] == "goal_not_collection_arithmetic"


def test_counts_and_unrelated_numbers_are_not_observation_values() -> None:
    memory = ResponseGroundedValueRegisterMemory()
    memory.read({"goal": GOAL})
    event = memory.write_model_response(
        source_step=0,
        model_response="Thought: Click 5 times and record 4 more numbers.\nAction: Click.",
        action_summary="Click.",
        source_call_id="c",
        source_response_sha256="r",
        source_screenshot_sha256="s",
    )
    assert event["accepted"] is False


def test_same_response_is_not_double_counted_when_action_prefix_already_accepted() -> None:
    memory = ResponseGroundedValueRegisterMemory()
    memory.read({"goal": GOAL})
    action = "MEMORY[observed=number 3 displayed; verified=none; pending=record values and calculate product] | Click."
    memory.write(
        source_step=0,
        action_summary=action,
        source_call_id="c",
        source_response_sha256="r",
        source_screenshot_sha256="s",
    )
    event = memory.write_model_response(
        source_step=0,
        model_response="Thought: The current screen shows the number 3 and I must record it.\nAction: " + action,
        action_summary=action,
        source_call_id="c",
        source_response_sha256="r",
        source_screenshot_sha256="s",
    )
    assert event["reason"] == "same_response_already_accepted_from_action_prefix"
    assert [atom.value for atom in memory.evidence_values] == ["3"]
