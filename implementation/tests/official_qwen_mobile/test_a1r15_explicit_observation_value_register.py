from __future__ import annotations

from raven_m.official_qwen_mobile.a1r15_explicit_observation_value_register import (
    ExplicitObservationValueRegisterMemory,
)


GOAL = "Click the button 5 times, remember the numbers displayed, and enter their product."
LIVE_RESPONSES = (
    "Thought: The page has loaded, showing a button with the number 1 displayed above it. I need to remember the numbers displayed each time.\nAction: Click.",
    "Thought: The current number displayed is 8, which I will record along with the next four numbers.\nAction: Click.",
    "Thought: The current number displayed is 10, which I will record along with the next four numbers.\nAction: Click.",
    "Thought: I need to record all five numbers displayed. So far, I've clicked it three times and seen the number 7.\nAction: Click.",
    "Thought: The current number displayed is 2, and I need to remember all five numbers.\nAction: Click.",
)


def _step(memory: ExplicitObservationValueRegisterMemory, step: int, response: str) -> dict:
    text, read = memory.read({"goal": GOAL})
    if text:
        memory.commit_injection(read["ticket_id"], f"prompt-{step}")
    action_summary = (
        "MEMORY[observed=number displayed; verified=none; pending=record each number and calculate product] | Click."
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


def test_sealed_r14_live_phrases_produce_exact_sequence() -> None:
    memory = ExplicitObservationValueRegisterMemory()
    for step, response in enumerate(LIVE_RESPONSES):
        assert _step(memory, step, response)["accepted"] is True
    text, audit = memory.read({"goal": GOAL})
    assert "observed integer sequence = [1, 8, 10, 7, 2]." in text
    assert audit["response_grounded_value_register"]["response_append_count"] == 5


def test_hallucinated_prime_list_is_rejected() -> None:
    memory = ExplicitObservationValueRegisterMemory()
    memory.read({"goal": GOAL})
    event = memory.write_model_response(
        source_step=0,
        model_response="Thought: Assuming the numbers were 2, 3, 5, 7, and 11, their product is 2310.\nAction: Type 2310.",
        action_summary="Type 2310.",
        source_call_id="c",
        source_response_sha256="r",
        source_screenshot_sha256="s",
    )
    assert event["accepted"] is False
    assert event["reason"] == "no_unique_explicit_observation_phrase"


def test_unrelated_count_is_not_accepted() -> None:
    memory = ExplicitObservationValueRegisterMemory()
    memory.read({"goal": GOAL})
    event = memory.write_model_response(
        source_step=0,
        model_response="Thought: I need to click the button 5 times and record 4 more numbers.\nAction: Click.",
        action_summary="Click.",
        source_call_id="c",
        source_response_sha256="r",
        source_screenshot_sha256="s",
    )
    assert event["accepted"] is False


def test_unobserved_number_shown_without_is_is_not_added() -> None:
    memory = ExplicitObservationValueRegisterMemory()
    memory.read({"goal": GOAL})
    event = memory.write_model_response(
        source_step=0,
        model_response="Thought: I need to remember the number 3 shown near the button.\nAction: Click.",
        action_summary="Click.",
        source_call_id="c",
        source_response_sha256="r",
        source_screenshot_sha256="s",
    )
    assert event["accepted"] is False


def test_multi_observation_response_is_fail_closed() -> None:
    memory = ExplicitObservationValueRegisterMemory()
    memory.read({"goal": GOAL})
    event = memory.write_model_response(
        source_step=0,
        model_response="Thought: The current number displayed is 8, but I have seen the number 1 and must record both.\nAction: Click.",
        action_summary="Click.",
        source_call_id="c",
        source_response_sha256="r",
        source_screenshot_sha256="s",
    )
    assert event["accepted"] is False
