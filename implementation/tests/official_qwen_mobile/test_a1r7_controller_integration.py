from pathlib import Path
from raven_m.official_qwen_mobile.a1r7_grounding_recovery_pending import GroundingRecoveryPendingMemory
from raven_m.official_qwen_mobile.controller import OfficialQwenMobileController
ROOT=Path(__file__).resolve().parents[3]
def test_controller_runner()->None:
 m=GroundingRecoveryPendingMemory();assert OfficialQwenMobileController(object(),working_memory=m).working_memory is m;s=(ROOT/"implementation/scripts/run_official_qwen_mobile.py").read_text();
 for x in ('"a1r7": {','"--a1r7-grpl"','("a1r7", args.a1r7_grpl)','dual_arm_name == "a1r7"','"A1-R7 six-task capability gate failed on'):assert x in s
