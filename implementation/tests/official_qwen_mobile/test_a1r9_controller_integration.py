from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def test_runner()->None:
 s=(ROOT/"implementation/scripts/run_official_qwen_mobile.py").read_text();
 for x in ('"a1r9": {','"--a1r9-rlcr"','("a1r9", args.a1r9_rlcr)','dual_arm_name == "a1r9"','"A1-R9 six-task capability gate failed on'):assert x in s
