from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from raven_m.official_qwen_mobile.a10_contract import (
    A0_PRESERVATION_TASKS,
    EXPERIMENT_ID,
    MECHANISM_ID,
    PARENT_EVIDENCE_COMMIT,
    REMAINING_TASKS,
    TASK_COUNT,
    TASK_SEED,
    exact_completion_errors,
    preservation_report,
)


ROOT = Path(__file__).resolve().parents[3]


def test_config_identity_boundary_and_frozen_schedule() -> None:
    config = json.loads((ROOT / "implementation/configs/a10_evidence_calibrated_obligation_branch_frontier_hard_seed20260806.json").read_text(encoding="utf-8"))
    assert config["schema"] == "a10_ecobf_arm_v1"
    assert config["experiment_id"] == EXPERIMENT_ID
    assert config["mechanism_id"] == MECHANISM_ID
    assert config["parent_evidence_commit"] == PARENT_EVIDENCE_COMMIT
    assert config["benchmark"]["task_seed"] == TASK_SEED
    assert config["benchmark"]["task_count"] == TASK_COUNT
    boundary = config["intervention"]
    assert boundary["extra_model_calls"] == 0
    assert boundary["guard"] is boundary["action_override"] is boundary["forced_termination"] is False
    assert boundary["evaluator_input"] is boundary["hidden_ui_input"] is boundary["future_input"] is False


def test_preservation_gate_requires_exact_four_rewards() -> None:
    passing = [{"task_name": name, "evaluator_reward": 1.0} for name in A0_PRESERVATION_TASKS]
    assert preservation_report(passing)["status"] == "pass"
    passing[-1]["evaluator_reward"] = 0.0
    assert preservation_report(passing)["status"] == "fail"


def test_exact_19_closure_order_and_seed() -> None:
    names = A0_PRESERVATION_TASKS + REMAINING_TASKS
    summaries = [
        {
            "task_name": name,
            "seed": TASK_SEED,
            "episode_id": f"episode_{index}",
            "evaluator_reward": 0.0,
            "error": None,
            "lifecycle_errors": [],
            "steps": [],
        }
        for index, name in enumerate(names)
    ]
    assert exact_completion_errors(summaries, [], []) == []
    assert exact_completion_errors(list(reversed(summaries)), [], [])
    assert exact_completion_errors(summaries[:-1], [], [])


def test_completion_rejects_nonfinite_reward_and_multi_attempt_transport() -> None:
    names = A0_PRESERVATION_TASKS + REMAINING_TASKS
    summaries = [
        {
            "task_name": name,
            "seed": TASK_SEED,
            "episode_id": f"episode_{index}",
            "evaluator_reward": 0.0,
            "error": None,
            "lifecycle_errors": [],
            "steps": [{"model_call": {"raven_meta": {"transport_attempts": 1}}}],
        }
        for index, name in enumerate(names)
    ]
    summaries[0]["evaluator_reward"] = float("nan")
    assert "infrastructure_invalid_summary" in exact_completion_errors(summaries, [], [])
    summaries[0]["evaluator_reward"] = 0.0
    summaries[0]["steps"][0]["model_call"]["raven_meta"]["transport_attempts"] = 2
    assert "transport_attempt_count_not_one" in exact_completion_errors(summaries, [], [])


def test_invalid_attempt_resolution_links_old_and_new_episode_ids() -> None:
    names = A0_PRESERVATION_TASKS + REMAINING_TASKS
    summaries = [
        {
            "task_name": name,
            "seed": TASK_SEED,
            "episode_id": f"valid_{index}",
            "evaluator_reward": 0.0,
            "error": None,
            "lifecycle_errors": [],
            "steps": [],
            **(
                {"resolves_invalid_episode_id": "invalid_0"}
                if index == 0
                else {}
            ),
        }
        for index, name in enumerate(names)
    ]
    invalid = [
        {"episode_id": "invalid_0", "resolved_by_episode_id": "valid_0"}
    ]
    assert exact_completion_errors(summaries, invalid, []) == []
    invalid[0]["resolved_by_episode_id"] = "valid_1"
    assert "invalid_resolution_link_mismatch" in exact_completion_errors(
        summaries, invalid, []
    )


def test_frozen_query_set_has_19_hash_bound_goals() -> None:
    query_set = json.loads(
        (ROOT / "evidence/a10/A10_FROZEN_QUERY_SET.json").read_text(encoding="utf-8")
    )
    assert query_set["task_count"] == 19
    assert len({item["task_name"] for item in query_set["records"]}) == 19
    assert all(
        sha256(item["goal"].encode("utf-8")).hexdigest() == item["goal_sha256"]
        for item in query_set["records"]
    )
