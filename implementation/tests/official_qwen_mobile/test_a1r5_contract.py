from raven_m.official_qwen_mobile import a1r5_contract as contract


def test_identity_gate_parent_and_source_closure() -> None:
    assert contract.MECHANISM_ID == "a1r5_transition_invalidated_pending_v1"
    assert contract.PARENT_EVIDENCE_COMMIT == "2b7e6b80d707682ac0f2d685b3dd293a53a4af78"
    assert len(contract.CAPABILITY_GATE_TASKS) == 6
    assert contract.FULL_TASK_ORDER[:6] == contract.CAPABILITY_GATE_TASKS
    assert "implementation/scripts/run_official_qwen_mobile.py" in contract.SOURCE_FILES
    assert "implementation/scripts/preflight_a1r5_tipl.py" in contract.SOURCE_FILES


def test_gate_requires_six_exact_rewards() -> None:
    rows = [{"task_name": n, "success": True, "evaluator_reward": 1.0} for n in contract.CAPABILITY_GATE_TASKS]
    assert contract.preservation_report(rows)["status"] == "pass"
    rows[-1]["evaluator_reward"] = 0.0
    assert contract.preservation_report(rows)["status"] == "fail"
