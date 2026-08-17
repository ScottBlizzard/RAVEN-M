from __future__ import annotations
import ast
from pathlib import Path
from raven_m.official_qwen_mobile.controller import OfficialQwenMobileController
from raven_m.official_qwen_mobile.a1r14_response_value_register import ResponseGroundedValueRegisterMemory

ROOT = Path(__file__).resolve().parents[3]


def test_controller_exposes_existing_model_response_only_after_execution() -> None:
    controller = OfficialQwenMobileController(object(), working_memory=ResponseGroundedValueRegisterMemory())
    assert isinstance(controller.working_memory, ResponseGroundedValueRegisterMemory)
    source = (ROOT / "implementation/src/raven_m/official_qwen_mobile/controller.py").read_text(encoding="utf-8")
    assert source.index('record["executed"] = True') < source.index('hasattr(self.working_memory, "write_model_response")')


def test_runner_has_unique_a1r14_target_first_identity() -> None:
    source = (ROOT / "implementation/scripts/run_official_qwen_mobile.py").read_text(encoding="utf-8")
    ast.parse(source)
    for value in ('"a1r14": {', '"--a1r14-rgvr"', '("a1r14", args.a1r14_rgvr)', 'dual_arm_name == "a1r14"'):
        assert value in source
