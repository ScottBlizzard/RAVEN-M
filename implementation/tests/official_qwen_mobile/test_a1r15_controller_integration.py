from __future__ import annotations
import ast
from pathlib import Path
from raven_m.official_qwen_mobile.controller import OfficialQwenMobileController
from raven_m.official_qwen_mobile.a1r15_explicit_observation_value_register import ExplicitObservationValueRegisterMemory

ROOT = Path(__file__).resolve().parents[3]


def test_controller_uses_existing_post_execution_response_hook() -> None:
    controller = OfficialQwenMobileController(object(), working_memory=ExplicitObservationValueRegisterMemory())
    assert isinstance(controller.working_memory, ExplicitObservationValueRegisterMemory)
    source = (ROOT / "implementation/src/raven_m/official_qwen_mobile/controller.py").read_text(encoding="utf-8")
    assert source.index('record["executed"] = True') < source.index('hasattr(self.working_memory, "write_model_response")')


def test_runner_has_unique_a1r15_target_first_identity() -> None:
    source = (ROOT / "implementation/scripts/run_official_qwen_mobile.py").read_text(encoding="utf-8")
    ast.parse(source)
    for value in ('"a1r15": {', '"--a1r15-eovr"', '("a1r15", args.a1r15_eovr)', 'dual_arm_name == "a1r15"'):
        assert value in source


def test_target_gate_terminal_checkpoint_cannot_resume() -> None:
    source = (ROOT / "implementation/scripts/run_official_qwen_mobile.py").read_text(encoding="utf-8")
    assert 'dual_arm_name in {"a1r13d", "a1r14", "a1r15"}' in source
    assert '"stopped_target_gate_failure"' in source
    assert "target/capability gate terminal state cannot be resumed" in source
