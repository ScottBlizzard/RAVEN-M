from raven_m.official_qwen_mobile.a1r7_grounding_recovery_pending import GroundingRecoveryPendingMemory,MECHANISM_ID
def obs(m,s,changed):
    return m.observe_step(source_step=s,action_summary=("MEMORY[observed=list; verified=none; pending=delete item] | tap" if s==0 else "tap item"),canonical_action={"type":"tap","x":.35,"y":.40},transition={"same_shape":True,"changed_pixel_fraction_gt_5":changed},source_call_id=str(s),source_response_sha256=str(s),source_screenshot_sha256=str(s))
def test_strong_recovery_is_one_read_after_two_no_progress_supports() -> None:
    m=GroundingRecoveryPendingMemory();obs(m,0,.2);obs(m,1,0);obs(m,2,0);text,a=m.read({"goal":"Delete item"});assert "RECOVERY REQUIRED FOR THE NEXT ACTION" in text;assert "entire phone screenshot" in text;e=m.commit_injection(a["ticket_id"],"p");assert e["strong_recovery_injected"] is True;assert e["mechanism_id"]==MECHANISM_ID
def test_no_strong_recovery_before_second_support() -> None:
    m=GroundingRecoveryPendingMemory();obs(m,0,.2);obs(m,1,0);text,a=m.read({"goal":"Delete item"});assert "RECOVERY REQUIRED" not in text
