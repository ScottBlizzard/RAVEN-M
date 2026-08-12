from __future__ import annotations

import ast
from pathlib import Path

from raven_m.official_qwen_mobile.a10_v2_contract import MECHANISM_ID as A10V2_ID
from raven_m.official_qwen_mobile.a10_v2_obligation_branch_frontier import (
    EvidenceMaturedObligationBranchFrontierMemory,
)
from raven_m.official_qwen_mobile.a11_confirmed_route_contraction import (
    ConfirmedRouteContractionECOBFMemory,
)
from raven_m.official_qwen_mobile.a11_contract import MECHANISM_ID as A11_ID


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "implementation/scripts/run_official_qwen_mobile.py"
WRAPPER = ROOT / "implementation/scripts/run_a678_arm.py"
CONTROLLER = ROOT / "implementation/src/raven_m/official_qwen_mobile/controller.py"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_shared_runner_is_syntactically_valid_and_exposes_mutually_exclusive_flags() -> None:
    source = _source(RUNNER)
    ast.parse(source)
    assert '"--a10-v2-emobf"' in source
    assert '"--a11-crc-ecobf"' in source
    assert "args.a10_v2_emobf" in source
    assert "args.a11_crc_ecobf" in source
    assert "if diagnostic_modes > 1:" in source


def test_registry_binds_independent_modules_contracts_and_result_namespaces() -> None:
    source = _source(RUNNER)
    for required in (
        "raven_m.official_qwen_mobile.a10_v2_obligation_branch_frontier",
        "EvidenceMaturedObligationBranchFrontierMemory",
        "raven_m.official_qwen_mobile.a10_v2_contract",
        "raven_m.official_qwen_mobile.a11_confirmed_route_contraction",
        "ConfirmedRouteContractionECOBFMemory",
        "raven_m.official_qwen_mobile.a11_contract",
        '"result_key": "a10v2_result"',
        '"result_key": "a11_result"',
        '"result_schema": "a10_v2_emobf_result_v1"',
        '"result_schema": "a11_crc_ecobf_result_v1"',
    ):
        assert required in source
    assert 'a678_memory = dual_arm["memory_class_object"]()' in source
    assert '"A10_V2_OVERALL_PASS"' in source
    assert '"A11_OVERALL_PASS"' in source


def test_arm_classes_match_contract_identity_and_instances_are_fresh() -> None:
    first_a10 = EvidenceMaturedObligationBranchFrontierMemory()
    second_a10 = EvidenceMaturedObligationBranchFrontierMemory()
    first_a11 = ConfirmedRouteContractionECOBFMemory()
    second_a11 = ConfirmedRouteContractionECOBFMemory()
    assert first_a10.mechanism_id == second_a10.mechanism_id == A10V2_ID
    assert first_a11.mechanism_id == second_a11.mechanism_id == A11_ID
    assert first_a10 is not second_a10
    assert first_a11 is not second_a11
    assert first_a10.mechanism_id != first_a11.mechanism_id


def test_new_arms_bind_own_preflight_receipt_and_cross_arm_resume_identity() -> None:
    source = _source(RUNNER)
    assert "dual_arm[\"validate_preflight\"]" in source
    assert "dual_arm[\"validate_receipt\"]" in source
    assert 'checkpoint.get("prospective_arm") != arm["arm"]' in source
    assert 'checkpoint.get("schema") != arm["checkpoint_schema"]' in source
    assert 'checkpoint.get("experiment_id") != arm["experiment_id"]' in source
    assert 'checkpoint.get("mechanism_id") != arm["mechanism_id"]' in source
    assert "cross-arm resume is forbidden" in source
    assert '"a10v2_valid_entries"' in source
    assert '"a11_valid_entries"' in source


def test_new_arms_use_single_transport_no_retry_and_blocking_four_task_gate() -> None:
    source = _source(RUNNER)
    assert "or dual_scored_arm\n        )," in source
    assert "require_single_transport=(a10_scored_arm or dual_scored_arm)" in source
    assert '"task_order": "blocking_A0_4_task_gate_then_frozen_manifest_remainder"' in source
    assert "if not _gate_passed(gate):" in source
    assert 'and task_name in A0_PRESERVATION_TASKS' in source
    assert '"scientific_failure_rerun": False' in source


def test_wrapper_keeps_output_and_receipt_namespaces_separate() -> None:
    source = _source(WRAPPER)
    ast.parse(source)
    assert '"a10v2", "a11"' in source
    assert '"a10v2": "runs/a10_v2_emobf"' in source
    assert '"a11": "runs/a11_crc_ecobf"' in source
    assert '"--a10-v2-launch-receipt"' in source
    assert '"--a11-launch-receipt"' in source


def test_controller_records_exact_text_for_any_actual_nonempty_memory_render() -> None:
    source = _source(CONTROLLER)
    assert "if memory_read is not None and rendered_memory:" in source
    assert 'memory_read["exact_injected_text"] = rendered_memory' in source
    exact_text_block = source[source.index("if memory_read is not None and rendered_memory:") : source.index("user_prompt =", source.index("if memory_read is not None and rendered_memory:"))]
    assert "a10_evidence_calibrated_obligation_branch_frontier_v1" not in exact_text_block
