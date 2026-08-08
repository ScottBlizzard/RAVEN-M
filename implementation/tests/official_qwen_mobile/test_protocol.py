import json
from hashlib import sha256

import pytest

from raven_m.official_qwen_mobile.protocol import (
    EVIDENCE_QUALIFIED_PROGRESS_SYSTEM_PROMPT,
    OFFICIAL_QWEN_COMMIT,
    OFFICIAL_SYSTEM_PROMPT,
    SOURCE_DOCUMENT_COVERAGE_SYSTEM_PROMPT,
    TRANSIENT_OBSERVATION_CARRY_SYSTEM_PROMPT,
    OfficialProtocolError,
    build_user_prompt,
    parse_official_response,
)


def response(arguments: dict) -> str:
    call = json.dumps(
        {"name": "mobile_use", "arguments": arguments},
        ensure_ascii=False,
    )
    return f"Thought: inspect the target.\nAction: Tap the target.\n<tool_call>\n{call}\n</tool_call>"


def test_prompt_is_provenanced_and_uses_official_grid() -> None:
    assert OFFICIAL_QWEN_COMMIT == "96588727e44c78b25ba03ea03b8e12f7e64fd0da"
    assert "The screen's resolution is 999x999." in OFFICIAL_SYSTEM_PROMPT
    assert "Output exactly in the order: Thought, Action, <tool_call>." in OFFICIAL_SYSTEM_PROMPT
    assert sha256(OFFICIAL_SYSTEM_PROMPT.encode("utf-8")).hexdigest() == (
        "9d060af15f62acb31b9fb197649ec001d4096491d7fb102de929316944b3e26d"
    )


def test_transient_carry_is_opt_in_and_does_not_mutate_official_prompt() -> None:
    assert sha256(OFFICIAL_SYSTEM_PROMPT.encode("utf-8")).hexdigest() == (
        "9d060af15f62acb31b9fb197649ec001d4096491d7fb102de929316944b3e26d"
    )
    assert TRANSIENT_OBSERVATION_CARRY_SYSTEM_PROMPT.startswith(
        OFFICIAL_SYSTEM_PROMPT
    )
    assert "Remember: <exact observation>" in (
        TRANSIENT_OBSERVATION_CARRY_SYSTEM_PROMPT
    )


def test_evidence_qualified_progress_is_opt_in_and_exactly_scoped() -> None:
    assert sha256(OFFICIAL_SYSTEM_PROMPT.encode("utf-8")).hexdigest() == (
        "9d060af15f62acb31b9fb197649ec001d4096491d7fb102de929316944b3e26d"
    )


def test_source_document_coverage_is_opt_in_and_does_not_mutate_official_prompt() -> None:
    assert sha256(OFFICIAL_SYSTEM_PROMPT.encode("utf-8")).hexdigest() == (
        "9d060af15f62acb31b9fb197649ec001d4096491d7fb102de929316944b3e26d"
    )
    assert SOURCE_DOCUMENT_COVERAGE_SYSTEM_PROMPT.startswith(OFFICIAL_SYSTEM_PROMPT)
    assert "Coverage scan; bottom anchor:" in SOURCE_DOCUMENT_COVERAGE_SYSTEM_PROMPT
    assert "Do not leave after the first page." in SOURCE_DOCUMENT_COVERAGE_SYSTEM_PROMPT
    assert EVIDENCE_QUALIFIED_PROGRESS_SYSTEM_PROMPT.startswith(
        OFFICIAL_SYSTEM_PROMPT
    )
    assert "Treat every action as ATTEMPTED" in (
        EVIDENCE_QUALIFIED_PROGRESS_SYSTEM_PROMPT
    )
    assert "object type, parent hierarchy, field, container, or operation" in (
        EVIDENCE_QUALIFIED_PROGRESS_SYSTEM_PROMPT
    )
    assert "Apply the same standard before terminate(success)." in (
        EVIDENCE_QUALIFIED_PROGRESS_SYSTEM_PROMPT
    )


def test_user_prompt_matches_notebook_history_template() -> None:
    rendered = build_user_prompt("Create a contact", ['Tap the "+" button.'])
    assert rendered == (
        "The user query: Create a contact.\n"
        "Task progress (You have done the following operation on the current "
        "device): Step 1: Tap the + button.; .\n"
    )


def test_harmless_blank_line_matches_official_notebook_tool_extraction() -> None:
    raw = (
        "Thought: The Files app is visible and should be opened.\n\n"
        "Action: \"Tap on the Files app icon to open the file manager.\\n\"\n"
        "<tool_call>\n"
        '{"name": "mobile_use", "arguments": '
        '{"action": "click", "coordinate": [166, 727]}}\n'
        "</tool_call>"
    )
    decision = parse_official_response(raw)
    assert decision.canonical_action == {
        "type": "tap",
        "x": 166 / 999,
        "y": 727 / 999,
    }


def test_multiline_thought_matches_official_notebook_tool_extraction() -> None:
    raw = (
        "Thought: I inspected the current screen.\n\n"
        "The next click should open the visible target.\n"
        "Action: Open the visible target.\n"
        "<tool_call>\n"
        '{"name": "mobile_use", "arguments": '
        '{"action": "click", "coordinate": [250, 143]}}\n'
        "</tool_call>"
    )
    decision = parse_official_response(raw)
    assert decision.action_summary == "Open the visible target."
    assert "next click" in decision.thought
    assert decision.canonical_action == {
        "type": "tap",
        "x": 250 / 999,
        "y": 143 / 999,
    }


def test_missing_action_prose_does_not_discard_valid_official_tool_call() -> None:
    raw = (
        "Some non-canonical prose from the model.\n"
        "<tool_call>\n"
        '{"name": "mobile_use", "arguments": {"action": "wait", "time": 2}}\n'
        "</tool_call>"
    )
    decision = parse_official_response(raw)
    assert decision.canonical_action == {"type": "wait", "duration_ms": 2000}
    assert decision.action_summary.startswith("Execute mobile_use action")


def test_multiple_tool_calls_remain_ambiguous_and_fail_closed() -> None:
    raw = response({"action": "wait", "time": 1}) + "\n" + response(
        {"action": "wait", "time": 2}
    )
    with pytest.raises(OfficialProtocolError, match="exactly one tool_call"):
        parse_official_response(raw)


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ({"action": "click", "coordinate": [0, 999]}, {"type": "tap", "x": 0.0, "y": 1.0}),
        (
            {"action": "swipe", "coordinate": [999, 0], "coordinate2": [0, 999]},
            {"type": "swipe", "x": 1.0, "y": 0.0, "x2": 0.0, "y2": 1.0, "duration_ms": 400},
        ),
        ({"action": "long_press", "coordinate": [499.5, 499.5], "time": 1.2}, {"type": "long_press", "x": 0.5, "y": 0.5, "duration_ms": 1200}),
        ({"action": "type", "text": "Ada"}, {"type": "type_text", "text": "Ada", "clear_text": False}),
        ({"action": "system_button", "button": "Back"}, {"type": "press_back"}),
        ({"action": "system_button", "button": "Menu"}, {"type": "press_recents"}),
        ({"action": "wait", "time": 2}, {"type": "wait", "duration_ms": 2000}),
    ],
)
def test_actions_convert_from_official_schema(arguments: dict, expected: dict) -> None:
    decision = parse_official_response(response(arguments))
    assert decision.canonical_action == expected
    assert decision.terminal_status is None


def test_answer_executes_and_then_allows_evaluation() -> None:
    decision = parse_official_response(response({"action": "answer", "text": "12.50"}))
    assert decision.canonical_action == {"type": "answer", "text": "12.50"}
    assert decision.terminal_status == "answer"


@pytest.mark.parametrize("status", ["success", "failure"])
def test_terminate_is_only_a_model_claim(status: str) -> None:
    decision = parse_official_response(response({"action": "terminate", "status": status}))
    assert decision.canonical_action is None
    assert decision.terminal_status == status


@pytest.mark.parametrize(
    "raw",
    [
        "not a tool call",
        response({"action": "click", "coordinate": [1000, 5]}),
        response({"action": "click", "coordinate": [5, 5], "text": "extra"}),
        response({"action": "terminate", "status": "done"}),
    ],
)
def test_invalid_outputs_fail_closed_without_repair(raw: str) -> None:
    with pytest.raises(OfficialProtocolError):
        parse_official_response(raw)
