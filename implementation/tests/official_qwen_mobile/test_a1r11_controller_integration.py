from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def test_runner()->None:
 source=(ROOT/"implementation/scripts/run_official_qwen_mobile.py").read_text()
 for literal in ('"a1r11": {','"--a1r11-cscp"','("a1r11", args.a1r11_cscp)','dual_arm_name == "a1r11"','"A1-R11 six-task capability gate failed on'):assert literal in source
