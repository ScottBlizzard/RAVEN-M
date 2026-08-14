from raven_m.official_qwen_mobile.a1r9_run_length_cycle_recovery import RunLengthCycleRecoveryMemory,MECHANISM_ID
def obs(m,s,x,y):return m.observe_step(source_step=s,action_summary=("MEMORY[observed=x; verified=none; pending=finish] | tap" if s==0 else "tap"),canonical_action={"type":"tap","x":x,"y":y},transition={"same_shape":True,"changed_pixel_fraction_gt_5":.8},source_call_id=str(s),source_response_sha256=str(s),source_screenshot_sha256=str(s))
def test_b_aaa_b_triggers_recovery()->None:
 m=RunLengthCycleRecoveryMemory();obs(m,0,.9,.7);obs(m,1,.35,.5);obs(m,2,.35,.5);obs(m,3,.35,.5);e=obs(m,4,.9,.7);assert e["run_length_cycle_created"] is True;t,a=m.read({"goal":"Delete A"});assert "ROUTE CYCLE RECOVERY" in t;assert m.commit_injection(a["ticket_id"],"p")["mechanism_id"]==MECHANISM_ID
def test_heterogeneous_middle_does_not_trigger()->None:
 m=RunLengthCycleRecoveryMemory();obs(m,0,.9,.7);obs(m,1,.35,.5);obs(m,2,.2,.2);obs(m,3,.9,.7);assert m._pending_cycle is None
