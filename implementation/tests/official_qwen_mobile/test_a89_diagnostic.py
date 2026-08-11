from __future__ import annotations

from raven_m.official_qwen_mobile.a678_contract import A0_PRESERVATION_TASKS, TASK_SEED
from raven_m.official_qwen_mobile.a89_diagnostic import (
    CLAIM_BOUNDARY,
    EXPERIMENT_IDS,
    completion_errors,
    report,
    select_four_task_specs,
)


def _summary(name: str, success: bool) -> dict:
    return {
        "task_name": name,
        "seed": TASK_SEED,
        "episode_id": f"{name}_{TASK_SEED}_test",
        "success": success,
        "evaluator_reward": float(success),
        "error": None,
        "lifecycle_errors": [],
        "steps": [{"model_call": {"raven_meta": {"transport_attempts": 1}}}],
    }


def test_selects_exact_four_in_gate_order() -> None:
    specs = [
        {"task_class": name, "task_seed": TASK_SEED}
        for name in reversed(A0_PRESERVATION_TASKS)
    ] + [{"task_class": "Ignored", "task_seed": TASK_SEED}]
    selected = select_four_task_specs(specs)
    assert [item["task_class"] for item in selected] == list(A0_PRESERVATION_TASKS)


def test_reward_failures_are_valid_diagnostic_data() -> None:
    summaries = [
        _summary(name, success=(index == 0))
        for index, name in enumerate(A0_PRESERVATION_TASKS)
    ]
    expected = [(name, TASK_SEED) for name in A0_PRESERVATION_TASKS]
    assert completion_errors(
        summaries=summaries,
        expected_keys=expected,
        invalid_attempts=[],
        lifecycle_errors=[],
    ) == []
    result = report(summaries)
    assert result["complete"] is True
    assert result["success_count"] == 1
    assert result["releases_remaining_15"] is False


def test_diagnostic_identity_forbids_gate_repair_claim() -> None:
    assert set(EXPERIMENT_IDS) == {"a8v2", "a9"}
    assert "not_gate_repair" in CLAIM_BOUNDARY
