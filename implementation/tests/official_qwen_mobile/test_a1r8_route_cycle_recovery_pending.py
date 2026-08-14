from raven_m.official_qwen_mobile.a1r8_route_cycle_recovery_pending import RouteCycleRecoveryPendingMemory,MECHANISM_ID
def obs(m,s,x,y):return m.observe_step(source_step=s,action_summary=("MEMORY[observed=x; verified=none; pending=finish] | tap" if s==0 else "tap"),canonical_action={"type":"tap","x":x,"y":y},transition={"same_shape":True,"changed_pixel_fraction_gt_5":.8},source_call_id=str(s),source_response_sha256=str(s),source_screenshot_sha256=str(s))
def test_abab_material_route_creates_one_shot_recovery()->None:
 m=RouteCycleRecoveryPendingMemory();obs(m,0,.35,.4);obs(m,1,.9,.7);obs(m,2,.35,.4);e=obs(m,3,.9,.7);assert e["route_cycle_created"] is True;text,a=m.read({"goal":"Delete A"});assert "ROUTE CYCLE RECOVERY" in text;event=m.commit_injection(a["ticket_id"],"p");assert event["route_cycle_recovery_injected"] is True;assert event["mechanism_id"]==MECHANISM_ID
def test_non_abab_does_not_trigger()->None:
 m=RouteCycleRecoveryPendingMemory();obs(m,0,.1,.1);obs(m,1,.2,.2);obs(m,2,.3,.3);obs(m,3,.2,.2);text,a=m.read({"goal":"Delete A"});assert "ROUTE CYCLE RECOVERY" not in text
