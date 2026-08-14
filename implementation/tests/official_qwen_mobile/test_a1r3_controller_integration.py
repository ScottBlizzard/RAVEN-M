from __future__ import annotations

import ast
from pathlib import Path

from raven_m.official_qwen_mobile.a1r3_stale_resistant_pending import (
    StaleResistantPendingMemory,
)
from raven_m.official_qwen_mobile.controller import OfficialQwenMobileController
from raven_m.official_qwen_mobile.protocol import A1_WORKING_MEMORY_SYSTEM_PROMPT

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "implementation/scripts/run_official_qwen_mobile.py"
CONTROLLER = ROOT / "implementation/src/raven_m/official_qwen_mobile/controller.py"


def test_a1_contract_is_preserved_and_r3_is_a_distinct_arm() -> None:
    memory = StaleResistantPendingMemory()
    controller = OfficialQwenMobileController(object(), working_memory=memory)
    assert "MEMORY[observed=" in A1_WORKING_MEMORY_SYSTEM_PROMPT
    assert "PEND[op=" not in A1_WORKING_MEMORY_SYSTEM_PROMPT
    assert controller.working_memory is memory
    assert memory.mechanism_id == "a1r3_stale_resistant_pending_v1"


def test_controller_uses_atomic_prepare_append_commit_before_generate() -> None:
    source = CONTROLLER.read_text(encoding="utf-8")
    read = source.index("rendered_memory, memory_read = self.working_memory.read(")
    append = source.index("user_prompt = append_working_memory(", read)
    commit = source.index("self.working_memory.commit_injection(", append)
    generate = source.index("call = self.client.generate(", commit)
    assert read < append < commit < generate


def test_runner_has_unique_arm_six_task_gate_and_vertical_result() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    ast.parse(source)
    for required in (
        '"a1r3": {',
        '"--a1r3-srpl"',
        '("a1r3", args.a1r3_srpl)',
        'dual_arm_name == "a1r3"',
        'dual_arm_name in {"a1r2", "a1r3"}',
        'dual_arm_name not in {"bprv2", "a1r2", "a1r3"}',
        '"A1-R3 six-task capability gate failed on',
        '"productive_failure_divergence_count"',
        "require_single_transport=(a10_scored_arm or dual_memory_arm)",
    ):
        assert required in source

