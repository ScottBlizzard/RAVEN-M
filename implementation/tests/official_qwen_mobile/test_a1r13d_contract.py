from __future__ import annotations

import json

from raven_m.official_qwen_mobile import a1r13_contract as parent
from raven_m.official_qwen_mobile import a1r13d_contract as contract


def test_identity_and_target_first_order_are_unique() -> None:
    assert contract.EXPERIMENT_ID != parent.EXPERIMENT_ID
    assert contract.MECHANISM_ID == parent.MECHANISM_ID
    assert contract.FULL_TASK_ORDER[0] == contract.TARGET_GATE_TASK == "BrowserMultiply"
    assert contract.FULL_TASK_ORDER[1:7] == contract.CAPABILITY_GATE_TASKS
    assert len(contract.FULL_TASK_ORDER) == len(set(contract.FULL_TASK_ORDER)) == 19


def test_config_is_exact_and_parent_replay_remains_authorizing() -> None:
    assert json.loads(contract.CONFIG_PATH.read_text(encoding="utf-8")) == contract.EXPECTED_CONFIG
    replay = json.loads(parent.OFFLINE_REPLAY_PATH.read_text(encoding="utf-8"))
    assert parent._replay_valid(replay)


def test_target_and_preservation_reports_are_independent() -> None:
    assert contract.target_gate_report([])["status"] == "pending"
    assert contract.preservation_report([])["status"] == "fail"
