from raven_m.official_qwen_mobile import a1r6_contract as contract

def test_identity_parent_gate_and_closure() -> None:
    assert contract.MECHANISM_ID == "a1r6_goal_anchored_pending_v1"
    assert contract.PARENT_EVIDENCE_COMMIT == "87d665a1021c6a1479bcbd80ff6a1716dd8f6cd8"
    assert len(contract.CAPABILITY_GATE_TASKS) == 6
    assert "implementation/scripts/run_official_qwen_mobile.py" in contract.SOURCE_FILES

def test_gate_is_six_of_six() -> None:
    rows=[{"task_name":n,"success":True,"evaluator_reward":1.0} for n in contract.CAPABILITY_GATE_TASKS]
    assert contract.preservation_report(rows)["status"] == "pass"
    rows[0]["success"]=False; rows[0]["evaluator_reward"]=0.0
    assert contract.preservation_report(rows)["status"] == "fail"
