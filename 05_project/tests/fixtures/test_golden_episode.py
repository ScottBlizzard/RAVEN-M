from __future__ import annotations

import json
from pathlib import Path

from raven_m.actions.schema import parse_action_response
from raven_m.env.androidworld_adapter import AndroidWorldAdapter


def test_golden_step_replays_exactly() -> None:
    fixture_path = (
        Path(__file__).resolve().parent
        / "golden_episode"
        / "golden_step.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    parsed = parse_action_response(fixture["raw_response"])
    assert parsed.first_pass
    assert parsed.decision == fixture["expected_decision"]
    width, height = fixture["screen_size"]
    mapped = AndroidWorldAdapter().map_action(
        parsed.decision["action"],
        screen_width=width,
        screen_height=height,
    )
    assert mapped.audit_record() == fixture["expected_mapping"]
