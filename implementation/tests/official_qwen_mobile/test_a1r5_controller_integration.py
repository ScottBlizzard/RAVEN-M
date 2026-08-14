from pathlib import Path
from raven_m.official_qwen_mobile.a1r5_transition_invalidated_pending import TransitionInvalidatedPendingMemory
from raven_m.official_qwen_mobile.controller import OfficialQwenMobileController

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "implementation/scripts/run_official_qwen_mobile.py"


def test_controller_accepts_r5_atomic_interface() -> None:
    memory = TransitionInvalidatedPendingMemory(); controller = OfficialQwenMobileController(object(), working_memory=memory)
    assert controller.working_memory is memory
    text, audit = memory.read({}); assert text and audit["ticket_id"]


def test_runner_has_unique_r5_path() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    for required in ('"a1r5": {', '"--a1r5-tipl"', '("a1r5", args.a1r5_tipl)', 'dual_arm_name == "a1r5"', '"A1-R5 six-task capability gate failed on'):
        assert required in source
