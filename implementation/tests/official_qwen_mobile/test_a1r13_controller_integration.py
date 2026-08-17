from __future__ import annotations

import ast
from pathlib import Path

from raven_m.official_qwen_mobile.a1r13_evidence_value_register import (
    EvidenceValueRegisterMemory,
)
from raven_m.official_qwen_mobile.controller import OfficialQwenMobileController
from raven_m.official_qwen_mobile.protocol import A1_WORKING_MEMORY_SYSTEM_PROMPT


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "implementation/scripts/run_official_qwen_mobile.py"
CONTROLLER = ROOT / "implementation/src/raven_m/official_qwen_mobile/controller.py"


def test_memory_uses_existing_transport_confirmed_controller_path() -> None:
    memory = EvidenceValueRegisterMemory()
    controller = OfficialQwenMobileController(object(), working_memory=memory)
    assert controller.working_memory is memory
    assert "MEMORY[observed=" in A1_WORKING_MEMORY_SYSTEM_PROMPT
    source = CONTROLLER.read_text(encoding="utf-8")
    read = source.index("rendered_memory, memory_read = self.working_memory.read(")
    generate = source.index("call = self.client.generate(", read)
    commit = source.index("self.working_memory.commit_injection(", generate)
    assert read < generate < commit


def test_runner_has_unique_a1r13_identity_and_target_gate() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    ast.parse(source)
    for required in (
        '"a1r13": {',
        '"--a1r13-evr"',
        '("a1r13", args.a1r13_evr)',
        'dual_arm_name == "a1r13"',
        'target_gate_report(summaries)',
        'A1-R13 Browser target gate failed',
    ):
        assert required in source
