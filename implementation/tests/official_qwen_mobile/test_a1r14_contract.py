from __future__ import annotations
import json
from raven_m.official_qwen_mobile import a1r14_contract as contract


def test_config_replay_and_order_are_frozen() -> None:
    assert json.loads(contract.CONFIG_PATH.read_text(encoding="utf-8")) == contract.EXPECTED_CONFIG
    replay = json.loads(contract.OFFLINE_REPLAY_PATH.read_text(encoding="utf-8"))
    assert contract._replay_valid(replay)
    assert contract.FULL_TASK_ORDER[0] == "BrowserMultiply"
    assert len(contract.FULL_TASK_ORDER) == len(set(contract.FULL_TASK_ORDER)) == 19


def test_reports_start_pending_and_fail_closed() -> None:
    assert contract.target_gate_report([])["status"] == "pending"
    assert contract.preservation_report([])["status"] == "fail"
