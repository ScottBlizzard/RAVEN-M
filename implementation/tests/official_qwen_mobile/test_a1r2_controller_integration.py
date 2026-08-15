from __future__ import annotations

import ast
from pathlib import Path

from raven_m.official_qwen_mobile.a1r2_compact_verified_pending import CompactVerifiedPendingMemory
from raven_m.official_qwen_mobile.controller import OfficialQwenMobileController
from raven_m.official_qwen_mobile.protocol import A1_WORKING_MEMORY_SYSTEM_PROMPT

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "implementation/scripts/run_official_qwen_mobile.py"
CONTROLLER = ROOT / "implementation/src/raven_m/official_qwen_mobile/controller.py"


def test_a1_prompt_and_memory_remain_separate() -> None:
    memory = CompactVerifiedPendingMemory()
    assert "MEMORY[observed=" in A1_WORKING_MEMORY_SYSTEM_PROMPT
    assert "PEND[op=" not in A1_WORKING_MEMORY_SYSTEM_PROMPT
    assert memory.mechanism_id == "a1r2_compact_verified_pending_v1"


def test_controller_uses_transport_confirmed_commit_order() -> None:
    memory = CompactVerifiedPendingMemory()
    controller = OfficialQwenMobileController(object(), working_memory=memory)
    assert controller.working_memory is memory
    source = CONTROLLER.read_text(encoding="utf-8")
    read = source.index("rendered_memory, memory_read = self.working_memory.read(")
    append = source.index("user_prompt = append_working_memory(", read)
    generate = source.index("call = self.client.generate(", append)
    commit = source.index("self.working_memory.commit_injection(", generate)
    assert read < append < generate < commit


def test_runner_has_unique_arm_gate_and_prompt_binding() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    ast.parse(source)
    for required in (
        '"a1r2": {',
        '"--a1r2-cvp"',
        '("a1r2", args.a1r2_cvp)',
        'if dual_arm_name == "a1r2"',
        'dual_arm_name in {"bprv2", "a1r2", "a1r3v3"}',
        '"A1-R2 Recipe gain-preservation gate failed; scientific failure is terminal"',
        "require_single_transport=(a10_scored_arm or dual_memory_arm)",
    ):
        assert required in source
