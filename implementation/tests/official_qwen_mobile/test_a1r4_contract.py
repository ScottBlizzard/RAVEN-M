from __future__ import annotations

from raven_m.official_qwen_mobile import a1r4_contract as contract


def test_identity_gate_and_parent() -> None:
    assert contract.MECHANISM_ID == "a1r4_writer_resilient_pending_v1"
    assert len(contract.CAPABILITY_GATE_TASKS) == 6
    assert contract.FULL_TASK_ORDER[:6] == contract.CAPABILITY_GATE_TASKS
    assert contract.PARENT_EVIDENCE_COMMIT == "4a28f757d7312f9ee87c84f4d750a3c43740de28"


def test_gate_requires_six_exact_rewards() -> None:
    summaries = [
        {"task_name": name, "success": True, "evaluator_reward": 1.0}
        for name in contract.CAPABILITY_GATE_TASKS
    ]
    assert contract.preservation_report(summaries)["status"] == "pass"
    summaries[-1]["evaluator_reward"] = 0.0
    assert contract.preservation_report(summaries)["status"] == "fail"


def test_source_closure_contains_all_r4_decision_files() -> None:
    required = {
        "implementation/src/raven_m/official_qwen_mobile/a1r4_writer_resilient_pending.py",
        "implementation/src/raven_m/official_qwen_mobile/a1r3_stale_resistant_pending.py",
        "implementation/scripts/run_official_qwen_mobile.py",
        "implementation/scripts/preflight_a1r4_wrpl.py",
        "implementation/scripts/qualify_a1r4_wrpl_server.py",
        "implementation/scripts/start_a1r4_wrpl_server.sh",
        "implementation/tests/official_qwen_mobile/test_a1r4_offline_replay.py",
    }
    assert required <= set(contract.SOURCE_FILES)

