from __future__ import annotations

import ast
from pathlib import Path

from raven_m.official_qwen_mobile.a1r4_writer_resilient_pending import (
    WriterResilientPendingMemory,
)
from raven_m.official_qwen_mobile.controller import OfficialQwenMobileController

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "implementation/scripts/run_official_qwen_mobile.py"


def test_controller_accepts_r4_through_generic_atomic_interface() -> None:
    memory = WriterResilientPendingMemory()
    controller = OfficialQwenMobileController(object(), working_memory=memory)
    assert controller.working_memory is memory
    text, audit = memory.read({})
    assert text and audit["ticket_id"]


def test_runner_has_unique_r4_arm_gate_and_result_path() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    ast.parse(source)
    for required in (
        '"a1r4": {',
        '"--a1r4-wrpl"',
        '("a1r4", args.a1r4_wrpl)',
        'dual_arm_name in {"a1r3", "a1r4"}',
        '"A1-R4 six-task capability gate failed on',
        'dual_arm_name == "a1r4"',
        'and dual_arm_name != "a1r4"',
    ):
        assert required in source
