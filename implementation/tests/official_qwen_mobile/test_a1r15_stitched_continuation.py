from raven_m.official_qwen_mobile import a1r15_stitched_continuation_contract as c

def test_parent_and_schedule():
    p=c.parent_browser_binding()
    assert p["success"] and p["success_attributed_to_evr"] is False
    assert p["episode_json_sha256"]=="b7bfd75c644e20d52f7436a21799c9f2e3736af20a84e378de4334daa2158765"
    assert len(c.CAPABILITY_GATE_TASKS)==6 and len(c.FULL_TASK_ORDER)==18
    assert "BrowserMultiply" not in c.FULL_TASK_ORDER

def test_six_is_non_fail_fast_and_release_requires_six_of_six():
    rows=[{"task_name":n,"evaluator_reward":0.0,"success":False} for n in c.CAPABILITY_GATE_TASKS]
    assert c.preservation_report(rows)["status"]=="fail"
    assert c.stitched_seven_report(rows)["status"]=="fail"
    rows=[{"task_name":n,"evaluator_reward":1.0,"success":True} for n in c.CAPABILITY_GATE_TASKS]
    assert c.stitched_seven_report(rows)["status"]=="pass"

def test_original_mechanism_identity_is_unchanged():
    assert c.MECHANISM_ID=="a1r15_explicit_observation_value_register_v1"
    assert c.EXPECTED_CONFIG["mechanism_id"]==c.MECHANISM_ID

def test_runner_has_separate_non_fail_fast_schedule():
    source=(c.REPOSITORY_ROOT/"implementation/scripts/run_official_qwen_mobile.py").read_text(encoding="utf-8")
    assert '"a1r15c": {' in source
    assert '"reward_fail_fast": False' in source
    assert 'task_name not in dual_arm["contract"].CAPABILITY_GATE_TASKS' in source
    assert 'complete_six_task_diagnostic_no_release' in source
    assert '"a1r15c", "sys_nag", "sys_lrer"' in source
