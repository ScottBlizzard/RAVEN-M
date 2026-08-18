from __future__ import annotations

import json

import pytest

from raven_m.official_qwen_mobile import sys_r2_lrer_contract as contract


def _summary(task_name: str, *, reward: float = 1.0) -> dict:
    return {
        "task_name": task_name,
        "seed": contract.TASK_SEED,
        "evaluator_reward": reward,
        "success": reward == 1.0,
        "memory_mechanism": {"mechanism_id": contract.MECHANISM_ID},
        "recovery_mechanism": {
            "system_id": contract.SYSTEM_ID,
            "counters": {
                "deferral_count": 0,
                "injection_commit_count": 0,
                "auxiliary_model_call_count": 0,
            },
        },
        "steps": [
            {"model_call": {"raven_meta": {"transport_attempts": 1}}}
        ],
    }


def test_identity_config_and_fixed_orders_are_exact() -> None:
    assert contract.SYSTEM_ID == "sys_r2_late_raw_evidence_rehydration_v1"
    assert contract.EXPERIMENT_ID == "SYS_R2_LRER_QWEN3VL32B_S20260806_G3407_V1"
    assert json.loads(contract.CONFIG_PATH.read_text(encoding="utf-8")) == contract.EXPECTED_CONFIG
    assert len(contract.SEVEN_TASK_ORDER) == len(set(contract.SEVEN_TASK_ORDER)) == 7
    assert len(contract.FULL_TASK_ORDER) == len(set(contract.FULL_TASK_ORDER)) == 19
    assert contract.FULL_TASK_ORDER[:7] == contract.SEVEN_TASK_ORDER


def test_source_plan_excludes_every_generated_self_reference() -> None:
    forbidden = {
        str(contract.SOURCE_FREEZE_PATH.relative_to(contract.REPOSITORY_ROOT)).replace("\\", "/"),
        str(contract.PREFLIGHT_PATH.relative_to(contract.REPOSITORY_ROOT)).replace("\\", "/"),
        "evidence/sys_r2_lrer/SYS_R2_LRER_LIVE_RECEIPT.json",
        "runs/sys_r2_lrer/checkpoint.json",
        "runs/sys_r2_lrer/sys_r2_lrer_result.json",
    }
    assert not forbidden.intersection(contract.SOURCE_FILES)
    assert len(contract.SOURCE_FILES) == len(set(contract.SOURCE_FILES))
    assert "implementation/src/raven_m/official_qwen_mobile/direction_diag_policy.py" not in contract.SOURCE_FILES
    assert "protocols/EXPLORATORY_DIRECTION_DIAG_PREREG_2026-08-18.md" not in contract.SOURCE_FILES


def test_replay_contract_requires_browser_evidence_and_six_silent_successes() -> None:
    payload = {
        "schema": contract.OFFLINE_REPLAY_SCHEMA,
        "status": "PASS",
        "errors": [],
        "generation_calls": 0,
        "system_id": contract.SYSTEM_ID,
        "experiment_id": contract.EXPERIMENT_ID,
        "fixed_seven": list(contract.SEVEN_TASK_ORDER),
        "browser": {
            "r15_opportunity_count": 1,
            "r2_opportunity_count": 1,
            "r15_all_five_observations_present": True,
            "deferred_response_excluded": True,
        },
        "historical_successes": [
            {"task_name": name, "opportunity_count": 0}
            for name in contract.SEVEN_TASK_ORDER[1:]
        ],
    }
    report = {**payload, "content_sha256": contract.content_sha256(payload)}
    assert contract._replay_valid(report)
    report["browser"]["deferred_response_excluded"] = False
    report["content_sha256"] = contract.content_sha256(report)
    assert not contract._replay_valid(report)


def test_seven_gate_is_non_fail_fast_and_only_passes_exact_seven_of_seven() -> None:
    partial = [_summary(name) for name in contract.SEVEN_TASK_ORDER[:3]]
    assert contract.seven_gate_report(partial)["status"] == "pending"
    failed = [_summary(name) for name in contract.SEVEN_TASK_ORDER]
    failed[0] = _summary(contract.SEVEN_TASK_ORDER[0], reward=0.0)
    report = contract.seven_gate_report(failed)
    assert report["status"] == "fail"
    assert report["valid_observed_count"] == 7
    assert report["success_count"] == 6
    assert contract.diagnostic_completion_errors(
        summaries=failed, invalid_attempts=[], lifecycle_errors=[]
    ) == []
    passed = [_summary(name) for name in contract.SEVEN_TASK_ORDER]
    assert contract.seven_gate_report(passed)["status"] == "pass"


def test_full_completion_requires_order_gate_and_system_boundaries() -> None:
    summaries = [_summary(name) for name in contract.FULL_TASK_ORDER]
    assert contract.exact_completion_errors(
        summaries=summaries, invalid_attempts=[], lifecycle_errors=[]
    ) == []
    summaries[0]["recovery_mechanism"]["counters"]["auxiliary_model_call_count"] = 1
    assert "system_boundary" in contract.exact_completion_errors(
        summaries=summaries, invalid_attempts=[], lifecycle_errors=[]
    )
    summaries = [_summary(name) for name in contract.FULL_TASK_ORDER]
    summaries[0]["steps"] = []
    assert "system_boundary" in contract.exact_completion_errors(
        summaries=summaries, invalid_attempts=[], lifecycle_errors=[]
    )


def test_source_freeze_rejects_non_commit_identity_before_touching_files() -> None:
    with pytest.raises(RuntimeError, match="implementation commit invalid"):
        contract.source_freeze_payload("not-a-commit")


def test_start_wrapper_disables_flashinfer_sampler_for_frozen_server_runtime() -> None:
    wrapper = (
        contract.REPOSITORY_ROOT
        / "implementation"
        / "scripts"
        / "start_sys_r2_lrer_server.sh"
    ).read_text(encoding="utf-8")
    assert (
        'export VLLM_USE_FLASHINFER_SAMPLER="${VLLM_USE_FLASHINFER_SAMPLER:-0}"'
        in wrapper
    )
