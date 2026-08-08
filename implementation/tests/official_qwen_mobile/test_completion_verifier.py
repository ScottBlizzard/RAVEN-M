import json

import pytest

from raven_m.official_qwen_mobile.completion_verifier import (
    COMPLETION_VERIFIER_SYSTEM_PROMPT,
    build_completion_verifier_user_prompt,
    parse_completion_verdict,
)


def test_prompt_is_strict_and_task_independent() -> None:
    assert "CONFIRMED requires visible evidence" in COMPLETION_VERIFIER_SYSTEM_PROMPT
    assert "generic success toast" in COMPLETION_VERIFIER_SYSTEM_PROMPT
    assert "If any required fact is hidden" in COMPLETION_VERIFIER_SYSTEM_PROMPT
    assert "zucchini" not in COMPLETION_VERIFIER_SYSTEM_PROMPT


def test_user_prompt_contains_only_goal_and_question() -> None:
    prompt = build_completion_verifier_user_prompt("Create a contact")
    assert prompt == (
        "Task: Create a contact\n"
        "Does the attached current screenshot provide sufficient visible "
        "evidence to allow a success claim?"
    )


@pytest.mark.parametrize("verdict", ["CONFIRMED", "INSUFFICIENT"])
def test_exact_verdict_parses(verdict: str) -> None:
    raw = json.dumps(
        {
            "verdict": verdict,
            "reason": "The exact state is visible.",
            "visible_evidence": ["A required value is visible."],
        }
    )
    parsed = parse_completion_verdict(raw)
    assert parsed.verdict == verdict


@pytest.mark.parametrize(
    "raw",
    [
        "```json\n{}\n```",
        '{"verdict":"YES","reason":"x","visible_evidence":[]}',
        '{"verdict":"CONFIRMED","reason":"","visible_evidence":[]}',
        '{"verdict":"CONFIRMED","reason":"x","visible_evidence":[],"extra":1}',
    ],
)
def test_noncanonical_output_fails_closed(raw: str) -> None:
    with pytest.raises(ValueError):
        parse_completion_verdict(raw)
