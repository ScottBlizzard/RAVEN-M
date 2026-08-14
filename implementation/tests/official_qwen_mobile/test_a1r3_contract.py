from __future__ import annotations

from raven_m.official_qwen_mobile import a1r3_contract as contract


def test_identity_and_six_task_gate_order() -> None:
    assert contract.MECHANISM_ID == "a1r3_stale_resistant_pending_v1"
    assert contract.CAPABILITY_GATE_TASKS[:4] == contract.A0_PRESERVATION_TASKS
    assert contract.CAPABILITY_GATE_TASKS[-2:] == (
        contract.RECIPE_TASK,
        contract.A1R2_GAIN_TASK,
    )
    assert len(contract.CAPABILITY_GATE_TASKS) == 6


def test_preservation_gate_requires_all_six() -> None:
    summaries = [
        {"task_name": name, "success": True, "evaluator_reward": 1.0}
        for name in contract.CAPABILITY_GATE_TASKS
    ]
    assert contract.preservation_report(summaries)["status"] == "pass"
    summaries[-1]["evaluator_reward"] = 0.5
    assert contract.preservation_report(summaries)["status"] == "fail"


def test_exact_completion_is_fail_closed() -> None:
    summaries = [
        {
            "task_name": name,
            "seed": contract.TASK_SEED,
            "evaluator_reward": 0.0,
            "steps": [
                {"model_call": {"raven_meta": {"transport_attempts": 1}}}
            ],
            "memory_mechanism": {
                "decision_boundary": {
                    "extra_model_calls": 0,
                    "action_override_count": 0,
                    "forced_termination_count": 0,
                }
            },
        }
        for name in contract.FULL_TASK_ORDER
    ]
    assert contract.exact_completion_errors(
        summaries=summaries, invalid_attempts=[], lifecycle_errors=[]
    ) == []
    summaries[0]["steps"][0]["model_call"]["raven_meta"]["transport_attempts"] = 2
    assert "transport_attempt_not_one" in contract.exact_completion_errors(
        summaries=summaries, invalid_attempts=[], lifecycle_errors=[]
    )


def test_source_closure_names_every_generated_decision_dependency() -> None:
    expected = {
        "implementation/scripts/run_official_qwen_mobile.py",
        "implementation/scripts/run_a1r3_srpl.py",
        "implementation/scripts/replay_a1r3_stale_resistant_pending.py",
        "implementation/scripts/preflight_a1r3_srpl.py",
        "implementation/scripts/qualify_a1r3_srpl_server.py",
        "implementation/scripts/start_a1r3_srpl_server.sh",
        "implementation/tests/official_qwen_mobile/test_a1r3_stale_resistant_pending.py",
        "implementation/tests/official_qwen_mobile/test_a1r3_contract.py",
        "implementation/tests/official_qwen_mobile/test_a1r3_controller_integration.py",
        "implementation/tests/official_qwen_mobile/test_a1r3_offline_replay.py",
    }
    assert expected <= set(contract.SOURCE_FILES)
