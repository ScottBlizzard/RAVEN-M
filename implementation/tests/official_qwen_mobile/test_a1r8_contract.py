from raven_m.official_qwen_mobile import a1r8_contract as c
def test_contract()->None:assert c.PARENT_EVIDENCE_COMMIT=="721af9efb1cba52cfa3db210a90eb9152e9e3699" and len(c.CAPABILITY_GATE_TASKS)==6 and "implementation/scripts/run_official_qwen_mobile.py" in c.SOURCE_FILES
