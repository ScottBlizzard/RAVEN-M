from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def test_runner()->None:
 s=(ROOT/"implementation/scripts/run_official_qwen_mobile.py").read_text();
 for x in ('"a1r10": {','"--a1r10-pacp"','("a1r10", args.a1r10_pacp)','dual_arm_name == "a1r10"','"A1-R10 six-task capability gate failed on'):assert x in s
