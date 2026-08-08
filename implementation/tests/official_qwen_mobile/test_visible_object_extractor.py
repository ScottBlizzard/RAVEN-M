import pytest

from raven_m.official_qwen_mobile.visible_object_extractor import (
    build_visible_object_extractor_user_prompt,
    parse_visible_object_extraction,
)


def test_prompt_contains_task_and_rule() -> None:
    prompt = build_visible_object_extractor_user_prompt("Add records", "Only reimbursable")
    assert "Add records" in prompt
    assert "Only reimbursable" in prompt


def test_parse_empty() -> None:
    assert parse_visible_object_extraction('{"objects":[]}').identifiers == ()


def test_parse_identifiers() -> None:
    result = parse_visible_object_extraction(
        '{"objects":[{"identifier":"Alpha"},{"identifier":"Beta"}]}'
    )
    assert result.identifiers == ("Alpha", "Beta")


@pytest.mark.parametrize(
    "content",
    [
        '```json\n{"objects":[]}\n```',
        '{"objects":[],"reason":"none"}',
        '{"objects":[{"identifier":""}]}',
        '{"objects":[{"identifier":"Alpha"},{"identifier":"Alpha"}]}',
        '[]',
    ],
)
def test_rejects_non_exact_schema(content: str) -> None:
    with pytest.raises(ValueError):
        parse_visible_object_extraction(content)
