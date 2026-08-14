from raven_m.official_qwen_mobile.a1r10_pre_action_calibrated_pending import PreActionCalibratedPendingMemory,MECHANISM_ID
def test_calibration_is_exact_and_committed_every_read()->None:
 m=PreActionCalibratedPendingMemory();t,a=m.read({"goal":"Delete A"});assert "SPATIAL CALIBRATION BEFORE ANY TAP" in t;assert "entire phone screenshot" in t;e=m.commit_injection(a["ticket_id"],"p");assert e["exact_injected_text"]==t and e["mechanism_id"]==MECHANISM_ID and e["pre_action_calibration_injected"] is True
