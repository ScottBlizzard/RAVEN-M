from __future__ import annotations

from raven_m.official_qwen_mobile import a10_v2_contract as contract


def test_identity_and_preflight_output_not_self_frozen() -> None:
    assert contract.TASK_SEED == 20260806 and contract.GENERATION_SEED == 3407
    assert contract.PREFLIGHT_SCHEMA == "a10_v2_zero_generation_preflight_v1"
    assert all("ZERO_GENERATION_PREFLIGHT" not in path for path in contract.SOURCE_FILES)


def test_exact_completion_rejects_nan_and_bad_transport() -> None:
    summaries = []
    for index, name in enumerate(contract.A0_PRESERVATION_TASKS + contract.REMAINING_TASKS):
        summaries.append({"task_name": name, "episode_id": str(index), "task_seed": 20260806, "evaluator_reward": 1.0, "error": None, "lifecycle_errors": [], "steps": [{"model_call": {"raven_meta": {"transport_attempts": 1}}}]})
    assert contract.exact_completion_errors(summaries, [], []) == []
    summaries[0]["evaluator_reward"] = float("nan")
    summaries[1]["steps"][0]["model_call"]["raven_meta"]["transport_attempts"] = 2
    errors = contract.exact_completion_errors(summaries, [], [])
    assert "infrastructure_invalid_summary" in errors
    assert "transport_attempt_count_not_one" in errors
