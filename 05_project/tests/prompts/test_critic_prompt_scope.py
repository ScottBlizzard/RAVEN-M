from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_critic_prompt_requires_dated_row_and_requested_field_binding() -> None:
    prompt = (ROOT / "prompts" / "critic_v1.md").read_text(
        encoding="utf-8"
    )
    normalized = " ".join(prompt.split())
    assert "verify each comma-separated item" in normalized
    assert "same horizontal line" in normalized
    assert "text visible in another date's row is wrong-context" in normalized
    assert "row title/name is not an activity type" in normalized
    assert "opening every target-date row detail" in normalized
    assert "controller-bound requested-field crop" in normalized
    assert "same exact category granularity and wording" in normalized
    assert "synonym is not exact text evidence" in normalized
    assert "dated-row visit keys in the payload are not memory IDs" in normalized
