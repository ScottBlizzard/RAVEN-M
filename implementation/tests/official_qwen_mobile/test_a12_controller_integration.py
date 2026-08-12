from __future__ import annotations

import ast
from pathlib import Path

from raven_m.official_qwen_mobile.a10_v2_obligation_branch_frontier import (
    EvidenceMaturedObligationBranchFrontierMemory,
)
from raven_m.official_qwen_mobile.a11_confirmed_route_contraction import (
    ConfirmedRouteContractionECOBFMemory,
)
from raven_m.official_qwen_mobile.a12_contract import MECHANISM_ID
from raven_m.official_qwen_mobile.a12_minimal_action_divergence import (
    MinimalActionDivergenceMemory,
)
from raven_m.official_qwen_mobile.controller import OfficialQwenMobileController


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "implementation/scripts/run_official_qwen_mobile.py"
WRAPPER = ROOT / "implementation/scripts/run_a678_arm.py"
CONTROLLER = ROOT / "implementation/src/raven_m/official_qwen_mobile/controller.py"


class _UnusedClient:
    pass


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_a12_controller_uses_only_the_existing_prompt_memory_interface() -> None:
    memory = MinimalActionDivergenceMemory()
    controller = OfficialQwenMobileController(_UnusedClient(), working_memory=memory)
    assert controller.working_memory is memory
    assert controller.cost_guard is None
    assert controller.source_document_coverage_gate is None
    assert controller.stop_after_markor_source_exit is False

    source = _source(CONTROLLER)
    read_index = source.index("rendered_memory, memory_read = self.working_memory.read(")
    prompt_index = source.index("user_prompt = append_working_memory(", read_index)
    generate_index = source.index("call = self.client.generate(", prompt_index)
    observe_index = source.index("record[\"memory_write\"] = self.working_memory.observe_step(", generate_index)
    evaluator_index = source.index("evaluator_reward = float(task.is_successful(env))", observe_index)
    assert read_index < prompt_index < generate_index < observe_index < evaluator_index
    assert 'memory_read["exact_injected_text"] = rendered_memory' in source
    assert '"model_canonical_action": decision.canonical_action' in source
    assert '"executed_canonical_action": canonical_action' in source


def test_a12_instances_are_fresh_and_cannot_compose_with_other_arms() -> None:
    first = MinimalActionDivergenceMemory()
    second = MinimalActionDivergenceMemory()
    assert first is not second
    assert first.mechanism_id == second.mechanism_id == MECHANISM_ID
    assert first.mechanism_id != EvidenceMaturedObligationBranchFrontierMemory().mechanism_id
    assert first.mechanism_id != ConfirmedRouteContractionECOBFMemory().mechanism_id

    runner = _source(RUNNER)
    assert 'a678_memory = dual_arm["memory_class_object"]()' in runner
    assert '("a10v2", args.a10_v2_emobf)' in runner
    assert '("a11", args.a11_crc_ecobf)' in runner
    assert '("a12", args.a12_madm)' in runner
    assert "if diagnostic_modes > 1:" in runner


def test_a12_runner_freezes_gate_resume_and_result_namespaces() -> None:
    runner = _source(RUNNER)
    ast.parse(runner)
    for required in (
        '"--a12-madm"',
        '"result_key": "a12_result"',
        '"checkpoint_schema": "a12_suite_checkpoint_v1"',
        '"entry_key": "a12_valid_entries"',
        '"result_schema": "a12_madm_result_v1"',
        'checkpoint.get("prospective_arm") != arm["arm"]',
        "cross-arm resume is forbidden",
        '"infrastructure_incomplete"',
        '"A12_PROTOCOL_INVALID"',
        '"A12_OVERALL_PASS"',
        '"read_causal_records": causal_read_analysis',
        '"vllm": dual_launch.get("vllm_version")',
    ):
        assert required in runner
    assert '"task_order": "blocking_A0_4_task_gate_then_frozen_manifest_remainder"' in runner
    assert '"scientific_failure_rerun": False' in runner
    assert "require_single_transport=(a10_scored_arm or dual_scored_arm)" in runner
    assert "same_task_invalid_count > 2" in runner


def test_a12_wrapper_uses_its_own_output_and_evidence_paths() -> None:
    wrapper = _source(WRAPPER)
    ast.parse(wrapper)
    assert '"a12"' in wrapper
    assert '"a12": "runs/a12_madm"' in wrapper
    assert '"--a12-madm"' in wrapper
    assert '"evidence/a12/A12_ZERO_GENERATION_PREFLIGHT.json"' in wrapper
    assert '"--a12-launch-receipt"' in wrapper
    assert 'preflight.get("status") != "PASS"' in wrapper
    assert "A12 live execution is forbidden" in wrapper
