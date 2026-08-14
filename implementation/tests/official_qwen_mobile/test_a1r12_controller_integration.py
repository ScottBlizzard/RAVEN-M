from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def test_runner()->None:
 source=(ROOT/"implementation/scripts/run_official_qwen_mobile.py").read_text()
 for literal in ('"a1r12": {','"--a1r12-chp"','("a1r12", args.a1r12_chp)','dual_arm_name == "a1r12"','"A1-R12 six-task capability gate failed on'):assert literal in source
def test_controller_has_generic_prompt_history_hook()->None:assert 'self.working_memory.prompt_history(history)' in (ROOT/"implementation/src/raven_m/official_qwen_mobile/controller.py").read_text()
