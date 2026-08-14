from __future__ import annotations

from raven_m.official_qwen_mobile import a1r2_contract as contract


def test_identity_and_gate_order() -> None:
    assert contract.MECHANISM_ID == "a1r2_compact_verified_pending_v1"
    assert contract.GATE5_TASKS[:4] == contract.A0_PRESERVATION_TASKS
    assert contract.GATE5_TASKS[-1] == contract.RECIPE_TASK


def test_preservation_gate() -> None:
    summaries = [
        {"task_name": name, "success": True, "evaluator_reward": 1.0}
        for name in contract.A0_PRESERVATION_TASKS
    ]
    assert contract.preservation_report(summaries)["status"] == "pass"
    summaries[0]["success"] = False
    assert contract.preservation_report(summaries)["status"] == "fail"


def test_gate5_requires_recipe() -> None:
    summaries = [
        {"task_name": name, "success": True, "evaluator_reward": 1.0}
        for name in contract.A0_PRESERVATION_TASKS
    ]
    assert contract.gate5_report(summaries)["status"] == "fail"
    summaries.append({"task_name": contract.RECIPE_TASK, "success": True, "evaluator_reward": 1.0})
    assert contract.gate5_report(summaries)["status"] == "pass"
