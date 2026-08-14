from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def test_runner()->None:
 s=(ROOT/"implementation/scripts/run_official_qwen_mobile.py").read_text();
 for x in ('"a1r8": {','"--a1r8-rcrp"','("a1r8", args.a1r8_rcrp)','dual_arm_name == "a1r8"','"A1-R8 six-task capability gate failed on'):assert x in s
