from __future__ import annotations

import json
from pathlib import Path

from raven_m.official_qwen_mobile.a11_contract import (
    A0_GATE_TASKS,
    EXPERIMENT_ID,
    MECHANISM_ID,
    PARENT_EVIDENCE_COMMIT,
    REMAINING_TASKS,
    TASK_SEED,
    competent_sparse_gate,
    exact_completion_errors,
    replay_metric_counts,
)


ROOT = Path(__file__).resolve().parents[3]


def test_config_freezes_identity_boundary_and_thresholds() -> None:
    config = json.loads((ROOT / "implementation/configs/a11_confirmed_route_contraction_hard_seed20260806.json").read_text(encoding="utf-8"))
    assert config["schema"] == "a11_crc_ecobf_arm_v1"
    assert config["mechanism_id"] == MECHANISM_ID
    assert config["experiment_id"] == EXPERIMENT_ID
    assert config["parent_evidence_commit"] == PARENT_EVIDENCE_COMMIT
    assert config["benchmark"]["task_seed"] == TASK_SEED
    assert config["intervention"]["retrieval_score_threshold"] == .70
    assert config["intervention"]["read_cooldown_steps"] == 4
    assert config["intervention"]["extra_model_calls"] == 0
    assert config["intervention"]["guard"] is config["intervention"]["action_override"] is False


def test_competent_sparse_gate_exact_boundary() -> None:
    episodes = [
        {"replayed_actions": 17, "nonempty_read_count": 1, "rendered_chars": 300, "read_events": [{"candidate_state_before_read": "MATURE", "support_count": 2, "evidence_signature": "a", "trigger_kind": "BAD_BRANCH_REPEAT"}]},
        {"replayed_actions": 31, "nonempty_read_count": 1, "rendered_chars": 300, "read_events": [{"candidate_state_before_read": "MATURE", "support_count": 2, "evidence_signature": "b", "trigger_kind": "CONTRACTED_FRONTIER"}]},
        {"replayed_actions": 16, "nonempty_read_count": 0, "rendered_chars": 0, "read_events": []},
        {"replayed_actions": 3, "nonempty_read_count": 0, "rendered_chars": 0, "read_events": []},
    ]
    report = competent_sparse_gate(episodes)
    assert report["status"] == "pass"
    assert report["total_read_density"] < .04
    episodes[2]["nonempty_read_count"] = 1
    assert competent_sparse_gate(episodes)["status"] == "fail"


def test_replay_metrics_accept_post_return_as_independent_support() -> None:
    post_return = {"candidate_state_before_read": "MATURE", "support_count": 2, "evidence_signature": "x", "trigger_kind": "CONFIRMED_ROUTE_TRAP", "confirmation_path": "post_return_reversion", "retrieved_route_ids": ["route"], "support_receipt_ids": ["route_receipt", "branch_receipt"]}
    assert not any(replay_metric_counts([post_return]).values())
    bad = dict(post_return, confirmation_path="", support_receipt_ids=["route_receipt"])
    assert replay_metric_counts([bad])["single_closed_route_delivery_count"] == 1


def test_exact_completion_and_resolution_links() -> None:
    summaries = [
        {"task_name": name, "seed": TASK_SEED, "episode_id": f"valid_{index}", "evaluator_reward": 0.0, "error": None, "lifecycle_errors": [], "steps": [], **({"resolves_invalid_episode_id": "invalid_0"} if index == 0 else {})}
        for index, name in enumerate(A0_GATE_TASKS + REMAINING_TASKS)
    ]
    invalid = [{"episode_id": "invalid_0", "resolved_by_episode_id": "valid_0"}]
    assert exact_completion_errors(summaries, invalid, []) == []
    summaries[0]["evaluator_reward"] = float("nan")
    assert "infrastructure_invalid_summary" in exact_completion_errors(summaries, invalid, [])
