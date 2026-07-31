from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_planner_prompt_forbids_optional_payload_invention() -> None:
    prompt = (ROOT / "prompts" / "planner_v1.md").read_text(encoding="utf-8")
    assert "Ground every user-entered value" in prompt
    assert "visible blank optional field is not a new requirement" in prompt
    assert "Never add a company, email, note, label, placeholder" in prompt
    assert "remove it on the next refresh" in prompt
    assert "distinguish a chronological history" in prompt
    assert "scrolling the content toward older rows" in prompt
    assert "`Markers`/map control as a calendar" in prompt
    assert "empty text-search results" in prompt
