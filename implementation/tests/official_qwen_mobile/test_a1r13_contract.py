from __future__ import annotations

import json

from raven_m.official_qwen_mobile import a1r13_contract as contract


def _silent_success(task_name: str) -> dict:
    return {
        "task_name": task_name,
        "seed": contract.TASK_SEED,
        "success": True,
        "evaluator_reward": 1.0,
        "memory_mechanism": {
            "evidence_register": {
                "counters": {"activation_count": 0, "render_count": 0},
                "read_events": [],
            }
        },
    }


def test_identity_config_and_order() -> None:
    assert contract.PARENT_EVIDENCE_COMMIT == "aa3176286a65c16becb59772cce1d742f13d441c"
    assert contract.FULL_TASK_ORDER[:6] == contract.CAPABILITY_GATE_TASKS
    assert contract.FULL_TASK_ORDER[6] == contract.TARGET_GATE_TASK
    assert json.loads(contract.CONFIG_PATH.read_text(encoding="utf-8")) == contract.EXPECTED_CONFIG


def test_preservation_requires_reward_and_silence() -> None:
    summaries = [_silent_success(name) for name in contract.CAPABILITY_GATE_TASKS]
    assert contract.preservation_report(summaries)["status"] == "pass"
    summaries[0]["memory_mechanism"]["evidence_register"]["counters"]["activation_count"] = 1
    assert contract.preservation_report(summaries)["status"] == "fail"


def test_target_gate_requires_exact_committed_five_value_read() -> None:
    exact = "TRANSIENT MODEL-AUTHORED EVIDENCE (unverified; current screenshot remains authoritative): observed integer sequence = [1, 8, 10, 7, 2]."
    summary = {
        "task_name": contract.TARGET_GATE_TASK,
        "evaluator_reward": 1.0,
        "memory_mechanism": {
            "evidence_register": {
                "counters": {"activation_count": 1, "append_count": 5, "render_count": 7},
                "read_events": [{"rendered": True, "exact_text": exact}],
            }
        },
    }
    assert contract.target_gate_report([summary])["status"] == "pass"
    summary["evaluator_reward"] = 0.0
    assert contract.target_gate_report([summary])["status"] == "fail"


def test_committed_replay_is_authorizing() -> None:
    replay = json.loads(contract.OFFLINE_REPLAY_PATH.read_text(encoding="utf-8"))
    assert contract._replay_valid(replay)
