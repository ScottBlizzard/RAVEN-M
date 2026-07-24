from pathlib import Path
import sys


SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import run_frozen_hard_suite_hotfix_001 as hotfix  # noqa: E402


def test_nullable_history_details_are_normalized_on_a_copy() -> None:
    raw = {
        "steps": [
            {
                "history_update": {
                    "details": None,
                    "model_calls": [],
                    "summary_updated": False,
                }
            },
            {"history_update": {"details": {"loop_detected": True}}},
            {"event": "model_fail"},
        ]
    }
    normalized = hotfix.normalize_nullable_history_details(raw)
    assert raw["steps"][0]["history_update"]["details"] is None
    assert normalized["steps"][0]["history_update"]["details"] == {}
    assert normalized["steps"][1]["history_update"]["details"] == {
        "loop_detected": True
    }
    assert normalized["steps"][2] == {"event": "model_fail"}


def test_record_result_receives_normalized_copy(monkeypatch) -> None:
    raw = {"steps": [{"history_update": {"details": None}}]}
    captured = {}

    def fake_record_result(**kwargs):
        captured["summary"] = kwargs["summary"]
        return {"episode_id": "episode"}

    monkeypatch.setattr(hotfix, "ORIGINAL_RECORD_RESULT", fake_record_result)
    monkeypatch.setattr(
        hotfix,
        "amendment_result_identity",
        lambda: {"amendment_id": hotfix.AMENDMENT_ID},
    )
    result = hotfix.record_result_hotfix_001(
        schedule_record={},
        summary=raw,
        attempt_count=1,
        infra_attempts=[],
        episode_dir=Path("."),
    )
    assert raw["steps"][0]["history_update"]["details"] is None
    assert captured["summary"]["steps"][0]["history_update"]["details"] == {}
    assert result["protocol_amendment"]["amendment_id"] == hotfix.AMENDMENT_ID
