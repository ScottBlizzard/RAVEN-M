from __future__ import annotations

import ast
from pathlib import Path

from raven_m.official_qwen_mobile.a1r1_bpr_v2 import BoundedPendingReceiptV2
from raven_m.official_qwen_mobile.controller import OfficialQwenMobileController


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "implementation/scripts/run_official_qwen_mobile.py"
CONTROLLER = ROOT / "implementation/src/raven_m/official_qwen_mobile/controller.py"


def test_controller_binds_prepare_prompt_commit_before_generate() -> None:
    memory = BoundedPendingReceiptV2()
    controller = OfficialQwenMobileController(object(), working_memory=memory)
    assert controller.working_memory is memory
    source = CONTROLLER.read_text(encoding="utf-8")
    read = source.index("rendered_memory, memory_read = self.working_memory.read(")
    prompt = source.index("user_prompt = append_working_memory(", read)
    commit = source.index("self.working_memory.commit_injection(", prompt)
    generate = source.index("call = self.client.generate(", commit)
    assert read < prompt < commit < generate
    assert 'memory_read["resident_history_sha256"]' in source
    assert 'memory_read["base_user_prompt_sha256"]' in source
    assert 'memory_read["final_user_prompt_sha256"]' in source


def test_runner_has_separate_arms_five_gate_append_only_and_single_transport() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    ast.parse(source)
    for required in (
        '"--a1r1-bpr-v2-mode"',
        '("bprv2", args.a1r1_bpr_v2_mode)',
        '"blocking_A0_4_then_Recipe_1_then_frozen_manifest_remainder"',
        '"fixed_five_task_non_fail_fast_after_primary_complete"',
        "_append_bpr_checkpoint",
        '"MECHANISM_PENDING_ABLATION"',
        "require_single_transport=(a10_scored_arm or dual_memory_arm)",
        'read_enabled=dual_arm["read_enabled"]',
        "bpr_arm_invalid_count > 2",
    ):
        assert required in source
    assert "self.working_memory.cancel_injection(" in CONTROLLER.read_text(encoding="utf-8")
