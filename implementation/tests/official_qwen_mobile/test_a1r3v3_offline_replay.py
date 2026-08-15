import json

from raven_m.official_qwen_mobile import a1r3v3_contract as contract


def test_materialized_replay_is_exact_and_zero_generation() -> None:
    report = json.loads(contract.OFFLINE_REPLAY_PATH.read_text(encoding="utf-8"))
    assert contract._validate_replay(report) == []
    assert report["totals"]["projected_rendered_chars"] - report["totals"]["a1r2_actual_rendered_chars"] == 762
    assert report["totals"]["projected_rendered_tokens"] - report["totals"]["a1r2_actual_rendered_tokens"] == 160
    active = [item for item in report["episodes"] if item["cnr_receipt_creation_count"]]
    assert len(active) == 8
    assert all(item["cnr_receipt_creation_count"] == item["cnr_receipt_committed_read_count"] == 1 for item in active)
