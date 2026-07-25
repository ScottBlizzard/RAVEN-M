from pathlib import Path
import sys


SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import run_frozen_hard_suite_hotfix_004 as hotfix  # noqa: E402


def test_nullable_decision_is_normalized_on_a_copy() -> None:
    raw = {
        "steps": [
            {
                "decision": None,
                "history_update": {"details": None},
            },
            {
                "decision": {"memory_citations": ["m_1"]},
                "history_update": {"details": {}},
            },
        ]
    }
    normalized = hotfix.normalize_nullable_aggregation_fields(raw)
    assert raw["steps"][0]["decision"] is None
    assert raw["steps"][0]["history_update"]["details"] is None
    assert normalized["steps"][0]["decision"] == {}
    assert normalized["steps"][0]["history_update"]["details"] == {}
    assert normalized["steps"][1]["decision"] == {
        "memory_citations": ["m_1"]
    }


def test_record_result_receives_normalized_copy(monkeypatch) -> None:
    raw = {
        "steps": [
            {
                "decision": None,
                "history_update": {"details": None},
            }
        ]
    }
    captured = {}

    def fake_record_result(**kwargs):
        captured["summary"] = kwargs["summary"]
        return {"episode_id": "episode", "protocol_amendments": []}

    monkeypatch.setattr(
        hotfix,
        "ORIGINAL_HOTFIX002_RECORD_RESULT",
        fake_record_result,
    )
    monkeypatch.setattr(
        hotfix,
        "amendment_result_identity",
        lambda: {"amendment_id": hotfix.AMENDMENT_ID},
    )
    result = hotfix.record_result_hotfix_004(
        schedule_record={},
        summary=raw,
        attempt_count=1,
        infra_attempts=[],
        episode_dir=Path("."),
    )
    assert raw["steps"][0]["decision"] is None
    assert captured["summary"]["steps"][0]["decision"] == {}
    assert captured["summary"]["steps"][0]["history_update"]["details"] == {}
    assert result["protocol_amendments"][-1]["amendment_id"] == (
        hotfix.AMENDMENT_ID
    )
