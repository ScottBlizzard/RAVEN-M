from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from raven_m.official_qwen_mobile import sys_r2_lrer_v2_contract as contract


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "implementation/scripts/run_official_qwen_mobile.py"
WRAPPER = ROOT / "implementation/scripts/run_sys_r2_lrer_v2.py"


def test_config_identity_and_source_closure_are_exact() -> None:
    assert json.loads(contract.CONFIG_PATH.read_text(encoding="utf-8")) == contract.EXPECTED_CONFIG
    assert contract.EXPECTED_CONFIG["post_action_settle_seconds"] == 1.0
    assert contract.EXPECTED_CONFIG["post_action_state_capture_count"] == 1
    assert contract.EXPECTED_CONFIG["native_budget_increase"] == 0
    assert len(contract.SEVEN_TASK_ORDER) == 7
    assert len(contract.FULL_TASK_ORDER) == 19
    for name in contract.SOURCE_FILES:
        assert (ROOT / name).is_file(), name
    assert not any("SOURCE_FREEZE" in name or "PREFLIGHT" in name for name in contract.SOURCE_FILES)


def test_runner_binds_independent_v2_identity_and_mature_seven_task_machine() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    assert '"sys_lrer_v2": {' in source
    assert '"--sys-r2-lrer-v2"' in source
    assert 'DUAL_ARM_SPECS["sys_lrer"] = dict(DUAL_ARM_SPECS["sys_lrer_v2"])' in source
    assert 'dual_arm["arm"] = "sys_lrer_v2"' in source
    assert "StabilizedLateRawEvidenceRehydrationPolicy" in source
    assert "post_action_settle_seconds=post_action_settle_seconds" in source
    assert 'dual_arm_name != "sys_lrer"' in source
    assert 'complete_seven_task_diagnostic_no_release' in source
    assert 'frame_settle_and_lrer_effects_not_separately_identifiable' in source
    assert 'post_observed_seed20260806_composite_system_comparison' in source
    sys_block = source[source.index('elif dual_arm_name == "sys_lrer":', source.index("run_signature.update")) :]
    sys_block = sys_block[: sys_block.index('elif dual_arm_name in {"a1r3v3"')]
    assert '"reward_fail_fast": False' in sys_block
    assert '"A0_preservation_tasks": []' in sys_block
    assert '"A0_preservation_required_for_continuation": False' in sys_block
    assert '"seven_task_diagnostic_non_fail_fast": True' in sys_block
    assert '"remaining_twelve_release_requires": "7/7"' in sys_block
    assert 'args.url.rstrip("/") != "http://127.0.0.1:18000"' in source


def test_exact_wrapper_uses_v2_flag_preflight_receipt_and_output_root() -> None:
    source = WRAPPER.read_text(encoding="utf-8")
    assert '"--runtime-python"' in source
    assert "args.runtime_python.resolve()" in source
    assert '"--sys-r2-lrer-v2"' in source
    assert "SYS_R2_LRER_V2_ZERO_GENERATION_PREFLIGHT.json" in source
    assert '"runs/sys_r2_lrer_v2"' in source
    assert '"http://127.0.0.1:18000"' in source
    assert "sys_r2_lrer_v2_result.json" in RUNNER.read_text(encoding="utf-8")


def _valid_summary(task_name: str) -> dict:
    return {
        "task_name": task_name,
        "evaluator_reward": 1.0,
        "success": True,
        "memory_mechanism": {"mechanism_id": contract.MECHANISM_ID},
        "recovery_mechanism": {
            "system_id": contract.SYSTEM_ID,
            "visible_frame_settle": {"seconds": 1.0},
            "counters": {
                "deferral_count": 0,
                "injection_commit_count": 0,
                "auxiliary_model_call_count": 0,
            },
        },
        "steps": [
            {
                "executed": True,
                "model_call": {"raven_meta": {"transport_attempts": 1}},
                "layers": {
                    "L3_execution": {
                        "post_action_settle": {
                            "policy": "fixed_visible_frame_settle_before_single_capture_v1",
                            "requested_seconds": 1.0,
                            "observed_seconds": 1.0,
                            "additional_model_calls": 0,
                            "additional_actions": 0,
                            "additional_state_captures": 0,
                        }
                    }
                },
            }
        ],
    }


def test_completion_contract_is_non_fail_fast_but_releases_only_exact_seven_of_seven() -> None:
    six_success_one_failure = [_valid_summary(name) for name in contract.SEVEN_TASK_ORDER]
    six_success_one_failure[0]["success"] = False
    six_success_one_failure[0]["evaluator_reward"] = 0.0
    gate = contract.seven_gate_report(six_success_one_failure)
    assert gate["status"] == "fail"
    assert gate["valid_observed_count"] == 7
    assert gate["success_count"] == 6
    assert contract.diagnostic_completion_errors(
        summaries=six_success_one_failure,
        invalid_attempts=[],
        lifecycle_errors=[],
    ) == []

    all_success = [_valid_summary(name) for name in contract.SEVEN_TASK_ORDER]
    assert contract.seven_gate_report(all_success)["status"] == "pass"
    assert contract.exact_completion_errors(
        summaries=all_success,
        invalid_attempts=[],
        lifecycle_errors=[],
    ) == ["task_closure"]


def test_episode_boundary_fails_closed_on_missing_or_drifted_settle_event() -> None:
    row = _valid_summary(contract.SEVEN_TASK_ORDER[0])
    assert contract._episode_boundary_errors(row) == []
    del row["steps"][0]["layers"]["L3_execution"]["post_action_settle"]
    assert "settle_execution_boundary" in contract._episode_boundary_errors(row)


def test_source_freeze_rejects_noncommit() -> None:
    with pytest.raises(RuntimeError, match="implementation commit invalid"):
        contract.source_freeze_payload("not-a-commit")


def test_frozen_r2_outcome_map_is_exact_complete_19() -> None:
    outcomes = contract.r2_outcome_map()
    assert set(outcomes) == set(contract.FULL_TASK_ORDER)
    assert sum(int(row["success"]) for row in outcomes.values()) == 6
    assert outcomes["BrowserMultiply"]["success"] is False
    assert all(outcomes[name]["success"] for name in contract.SEVEN_TASK_ORDER[1:])


def test_first_response_divergence_is_explicit_and_fail_closed() -> None:
    summary = {"steps": [{"model_call": {"response_sha256": "a" * 64}}]}
    reference = {"steps": [{"source_response_sha256": "b" * 64}]}
    observed = contract.first_response_divergence(summary, reference)
    assert observed["status"] == "DIVERGED"
    assert observed["first_step"] == 0
    assert contract.first_response_divergence(summary, None) == {
        "status": "NOT_COMPARABLE",
        "reason": "no_frozen_r2_step_reference_for_task",
        "first_step": None,
    }


def test_result_validator_rejects_semantic_drift() -> None:
    baseline = contract.r2_outcome_map()
    rows = [
        {
            "task_name": name,
            "execution_status": "NOT_RUN_BY_PROTOCOL",
            "attribution": "NOT_RUN_BY_PROTOCOL",
            "prior_r2_outcome": baseline[name],
            "comparative_outcome": "NOT_RUN_BY_PROTOCOL",
            "frame_settle_active": False,
        }
        for name in contract.FULL_TASK_ORDER
    ]
    payload = {
        "schema": contract.RESULT_SCHEMA,
        "status": "RUNNING_PARTIAL",
        "source_checkpoint_status": "running",
        "identity": {
            "mechanism_id": contract.MECHANISM_ID,
            "system_id": contract.SYSTEM_ID,
            "experiment_id": contract.EXPERIMENT_ID,
        },
        "closure": {"valid_episode_count": 0, "not_run_by_protocol_count": 19},
        "verdicts": {
            "accuracy": "NOT_YET_ADJUDICATED",
            "mechanism": "NOT_ESTABLISHED",
            "cost": "DESCRIPTIVE_ONLY_NO_MATCHED_RUNTIME_CONTROL",
        },
        "seven_task_gate": {
            "status": "pending",
            "success_count": 0,
            "required": 7,
            "valid_observed_count": 0,
            "tasks": [
                {"task_name": name, "reward": None, "pass": False}
                for name in contract.SEVEN_TASK_ORDER
            ],
        },
        "performance": {
            "success_count": 0,
            "reward_sum": 0,
            "normal_model_calls": 0,
            "executed_actions": 0,
            "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "elapsed_seconds": 0,
            "post_action_settle_seconds": 0,
        },
        "mechanism_funnel": {
            "eligible_count": 0,
            "deferral_count": 0,
            "injection_commit_count": 0,
            "auxiliary_model_call_count": 0,
        },
        "tasks": rows,
        "errors": [],
    }
    payload["content_sha256"] = contract.content_sha256(payload)
    assert contract.validate_result_payload(payload) == payload
    payload["tasks"][0]["attribution"] = "MECHANISM_CONSISTENT_CANDIDATE_SUPPORT"
    payload["content_sha256"] = contract.content_sha256(payload)
    with pytest.raises(RuntimeError, match="result_not_run_classification"):
        contract.validate_result_payload(payload)
    payload["tasks"][0]["attribution"] = "NOT_RUN_BY_PROTOCOL"
    payload["tasks"][0]["prior_r2_outcome"] = {
        "success": True,
        "reward": 999.0,
        "episode_id": "forged",
    }
    payload["content_sha256"] = contract.content_sha256(payload)
    with pytest.raises(RuntimeError, match="result_prior_r2_outcome"):
        contract.validate_result_payload(payload)
    payload["tasks"][0]["prior_r2_outcome"] = baseline[contract.FULL_TASK_ORDER[0]]
    payload["verdicts"]["mechanism"] = "FORGED"
    payload["content_sha256"] = contract.content_sha256(payload)
    with pytest.raises(RuntimeError, match="result_verdicts"):
        contract.validate_result_payload(payload)


def test_result_validator_rejects_forged_valid_episode_numbers() -> None:
    baseline = contract.r2_outcome_map()
    rows = [
        {
            "task_name": name,
            "execution_status": "NOT_RUN_BY_PROTOCOL",
            "attribution": "NOT_RUN_BY_PROTOCOL",
            "prior_r2_outcome": baseline[name],
            "comparative_outcome": "NOT_RUN_BY_PROTOCOL",
            "frame_settle_active": False,
        }
        for name in contract.FULL_TASK_ORDER
    ]
    rows[0] = {
        "task_name": "BrowserMultiply",
        "execution_status": "VALID_SUCCESS",
        "attribution": "MECHANISM_CONSISTENT_CANDIDATE_SUPPORT",
        "prior_r2_outcome": baseline["BrowserMultiply"],
        "comparative_outcome": "GAIN_CANDIDATE",
        "frame_settle_active": True,
        "success": True,
        "reward": 1.0,
        "normal_model_calls": 2,
        "executed_actions": 1,
        "token_usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4},
        "elapsed_seconds": 1.0,
        "lrer": {
            "state": "COMMITTED",
            "eligible_count": 1,
            "deferral_count": 1,
            "injection_commit_count": 1,
        },
        "committed_injections": [{"ticket_id": "x"}],
        "first_divergence_from_r2": {
            "status": "NOT_COMPARABLE",
            "reason": "synthetic_fixture",
            "first_step": None,
        },
        "post_action_settle": {
            "requested_seconds": 1.0,
            "event_count": 1,
            "observed_seconds": 1.0,
        },
    }
    payload = {
        "schema": contract.RESULT_SCHEMA,
        "status": "RUNNING_PARTIAL",
        "source_checkpoint_status": "running",
        "identity": {
            "mechanism_id": contract.MECHANISM_ID,
            "system_id": contract.SYSTEM_ID,
            "experiment_id": contract.EXPERIMENT_ID,
        },
        "closure": {"valid_episode_count": 1, "not_run_by_protocol_count": 18},
        "seven_task_gate": {
            "status": "pending",
            "success_count": 1,
            "required": 7,
            "valid_observed_count": 1,
            "tasks": [
                {"task_name": name, "reward": 1.0 if index == 0 else None, "pass": index == 0}
                for index, name in enumerate(contract.SEVEN_TASK_ORDER)
            ],
        },
        "performance": {
            "success_count": 1,
            "reward_sum": 1.0,
            "normal_model_calls": 2,
            "executed_actions": 1,
            "token_usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4},
            "elapsed_seconds": 1.0,
            "post_action_settle_seconds": 1.0,
        },
        "mechanism_funnel": {
            "eligible_count": 1,
            "deferral_count": 1,
            "injection_commit_count": 1,
            "auxiliary_model_call_count": 0,
        },
        "verdicts": {
            "accuracy": "NOT_YET_ADJUDICATED",
            "mechanism": "COMPOSITE_CANDIDATE_SUPPORT_ABLATION_UNRESOLVED",
            "cost": "DESCRIPTIVE_ONLY_NO_MATCHED_RUNTIME_CONTROL",
        },
        "tasks": rows,
        "errors": [],
    }
    payload["content_sha256"] = contract.content_sha256(payload)
    assert contract.validate_result_payload(payload) == payload

    checkpoint_summary = {
        "task_name": "BrowserMultiply",
        "episode_id": "episode-1",
        "evaluator_reward": 1.0,
        "success": True,
        "normal_decision_call_count": 2,
        "model_call_count": 2,
        "executed_action_count": 1,
        "started_at": "2026-08-18T00:00:00+00:00",
        "finished_at": "2026-08-18T00:00:01+00:00",
        "recovery_mechanism": {
            "counters": {
                "eligible_count": 1,
                "deferral_count": 1,
                "injection_commit_count": 1,
            },
            "committed_injections": [{"ticket_id": "x"}],
        },
        "steps": [
            {
                "executed": True,
                "model_call": {
                    "usage": {
                        "prompt_tokens": 3,
                        "completion_tokens": 1,
                        "total_tokens": 4,
                    }
                },
                "layers": {
                    "L3_execution": {
                        "post_action_settle": {"observed_seconds": 1.0}
                    }
                },
            }
        ],
    }
    checkpoint = {
        "schema": contract.CHECKPOINT_SCHEMA,
        "status": "running",
        "system_id": contract.SYSTEM_ID,
        "experiment_id": contract.EXPERIMENT_ID,
        "run_signature_sha256": "r" * 64,
        "valid_summaries": [checkpoint_summary],
        "invalid_attempts": [],
    }
    checkpoint["content_sha256"] = contract.content_sha256(checkpoint)
    payload["identity"]["run_signature_sha256"] = "r" * 64
    payload["tasks"][0]["episode_id"] = "episode-1"
    payload["closure"]["invalid_attempt_count"] = 0
    payload["closure"]["checkpoint_content_sha256"] = checkpoint["content_sha256"]
    payload["content_sha256"] = contract.content_sha256(payload)
    assert contract.validate_result_payload(
        payload, checkpoint_payload=checkpoint
    ) == payload

    forged_checkpoint_result = json.loads(json.dumps(payload))
    forged_checkpoint_result["tasks"][0]["episode_id"] = "forged-episode"
    forged_checkpoint_result["content_sha256"] = contract.content_sha256(
        forged_checkpoint_result
    )
    with pytest.raises(RuntimeError, match="result_checkpoint_task_binding"):
        contract.validate_result_payload(
            forged_checkpoint_result, checkpoint_payload=checkpoint
        )

    false_complete = json.loads(json.dumps(payload))
    false_complete["status"] = "COMPLETE_19"
    false_complete["source_checkpoint_status"] = "complete"
    false_complete["content_sha256"] = contract.content_sha256(false_complete)
    with pytest.raises(RuntimeError, match="result_complete_19_closure"):
        contract.validate_result_payload(false_complete)

    for field, forged in (
        ("reward", 999.0),
        ("normal_model_calls", -3),
        ("elapsed_seconds", float("nan")),
    ):
        candidate = json.loads(json.dumps(payload))
        candidate["tasks"][0][field] = forged
        candidate["content_sha256"] = contract.content_sha256(candidate)
        with pytest.raises(RuntimeError):
            contract.validate_result_payload(candidate)


def test_preflight_focused_suite_covers_all_v2_contract_layers() -> None:
    from implementation.scripts import preflight_sys_r2_lrer_v2 as preflight

    assert tuple(preflight.FOCUSED_TESTS) == (
        "implementation/tests/official_qwen_mobile/test_r15_derived_evidence_consolidation.py",
        "implementation/tests/official_qwen_mobile/test_sys_r2_lrer_v2_contract.py",
        "implementation/tests/official_qwen_mobile/test_sys_r2_lrer_v2_controller_integration.py",
        "implementation/tests/official_qwen_mobile/test_sys_r2_lrer_v2_offline_replay.py",
    )
    source = inspect.getsource(preflight.main)
    assert "generation_calls" in source
    assert "worktree_dirty" in source
    assert "offline_replay_drift" in source
    assert "local_processor_identity" in source


@pytest.mark.parametrize(
    ("summary", "audit", "task", "infra", "expected"),
    [
        ({"success": True}, {"committed_injections": [{"id": 1}]}, "BrowserMultiply", False, "MECHANISM_CONSISTENT_CANDIDATE_SUPPORT"),
        ({"success": True}, {}, "BrowserMultiply", False, "SUCCESS_COMPONENT_SILENT_OR_UNUSED"),
        ({"success": True}, {"committed_injections": [{"id": 1}]}, "ExpenseDeleteMultiple2", False, "SUCCESS_COMPONENT_USED_PRESERVED_ABLATION_UNRESOLVED"),
        ({"success": False}, {}, "ExpenseDeleteMultiple2", False, "REGRESSION"),
        ({"success": False}, {"counters": {"eligible_count": 1}}, "BrowserMultiply", False, "ACTIVATED_NO_GAIN"),
        ({"success": False}, {}, "BrowserMultiply", False, "NO_OPPORTUNITY"),
        (None, {}, "BrowserMultiply", True, "INFRA_INVALID"),
        (None, {}, "BrowserMultiply", False, "NOT_RUN_BY_PROTOCOL"),
    ],
)
def test_formal_attribution_taxonomy_is_exact(
    summary: dict | None,
    audit: dict,
    task: str,
    infra: bool,
    expected: str,
) -> None:
    assert contract.task_attribution(
        task_name=task,
        summary=summary,
        recovery_audit=audit,
        unresolved_infrastructure=infra,
    ) == expected
