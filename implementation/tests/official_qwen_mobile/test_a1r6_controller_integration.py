from pathlib import Path
from raven_m.official_qwen_mobile.a1r6_goal_anchored_pending import GoalAnchoredPendingMemory
from raven_m.official_qwen_mobile.controller import OfficialQwenMobileController
ROOT=Path(__file__).resolve().parents[3]
def test_controller_and_runner_r6() -> None:
    m=GoalAnchoredPendingMemory(); assert OfficialQwenMobileController(object(),working_memory=m).working_memory is m
    source=(ROOT/"implementation/scripts/run_official_qwen_mobile.py").read_text(encoding="utf-8")
    for token in ('"a1r6": {','"--a1r6-gapl"','("a1r6", args.a1r6_gapl)','dual_arm_name == "a1r6"','"A1-R6 six-task capability gate failed on'): assert token in source
