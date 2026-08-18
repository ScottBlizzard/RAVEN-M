from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from raven_m.official_qwen_mobile.a4v2_induction import build_induction_packet
from implementation.scripts.freeze_a4v2_workflow_bank import _literal_leaks


def _episode(path: Path, *, seed: int, reward: float = 1.0) -> dict:
    payload = {
        "task_name": "ExpenseDeleteSingle",
        "seed": seed,
        "task_goal": 'Delete expense "Coffee" with amount: $12.50',
        "task_params": {"merchant": "Alice Cafe", "date": "2026-08-18"},
        "evaluator_reward": reward,
        "success": reward == 1.0,
        "error": None,
        "steps": [
            {
                "decision": {
                    "thought": 'Find Coffee from Alice Cafe on 2026-08-18, then open its menu.',
                    "action_summary": 'Tapped the Coffee row at x=0.5 y=0.4.',
                    "canonical_action": {"type": "tap", "x": 0.5, "y": 0.4},
                }
            },
            {
                "decision": {
                    "thought": "Confirm the deletion.",
                    "action_summary": "Tapped the visible delete confirmation.",
                    "canonical_action": {"type": "tap", "x": 0.7, "y": 0.8},
                }
            },
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return {
        "donor_id": f"d{seed}",
        "episode_path": path.name,
        "episode_sha256": sha256(path.read_bytes()).hexdigest(),
        "task_class": "ExpenseDeleteSingle",
        "task_seed": seed,
        "difficulty": "easy",
    }


def test_build_packet_masks_values_and_locks_sources(tmp_path: Path) -> None:
    donors = [_episode(tmp_path / "a.json", seed=11), _episode(tmp_path / "b.json", seed=12)]
    hard = tmp_path / "hard.json"
    hard.write_text(json.dumps({"instances": [{"task_class": "ScoredHard"}]}), encoding="utf-8")
    packet = build_induction_packet(
        route_id="expense_delete",
        route={"app": "pro_expense", "operation": "delete", "object_family": "expense_record", "constraint_family": "*"},
        donors=donors,
        repository_root=tmp_path,
        scored_hard_manifest=hard,
    )
    assert packet["ready_for_induction"] is True
    assert packet["generation_calls"] == 0
    assert "Coffee" not in packet["prompt"]
    assert "$12.50" not in packet["prompt"]
    assert "Alice Cafe" not in packet["prompt"]
    assert "2026-08-18" not in packet["prompt"]
    assert "x=0.5" not in packet["prompt"]
    assert {"Coffee", "$12.50", "Alice Cafe", "2026-08-18"}.issubset(packet["literal_denylist"])
    assert _literal_leaks("1. Open Alice Cafe. 2. Continue.", packet["literal_denylist"])
    assert not _literal_leaks("1. Open the matching record. 2. Continue.", packet["literal_denylist"])
    assert len(packet["source_lock"]) == 3


def test_packet_rejects_failed_or_same_seed_donors(tmp_path: Path) -> None:
    good = _episode(tmp_path / "a.json", seed=11)
    failed = _episode(tmp_path / "b.json", seed=12, reward=0.0)
    hard = tmp_path / "hard.json"
    hard.write_text(json.dumps({"instances": [{"task_class": "ScoredHard"}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="failed"):
        build_induction_packet(
            route_id="expense_delete", route={"app": "x"}, donors=[good, failed], repository_root=tmp_path,
            scored_hard_manifest=hard,
        )

    other = _episode(tmp_path / "c.json", seed=11)
    other["donor_id"] = "different"
    with pytest.raises(ValueError, match="two seeds"):
        build_induction_packet(
            route_id="expense_delete", route={"app": "x"}, donors=[good, other], repository_root=tmp_path,
            scored_hard_manifest=hard,
        )


def test_packet_rejects_any_scored_hard_task_class(tmp_path: Path) -> None:
    donors = [_episode(tmp_path / "a.json", seed=11), _episode(tmp_path / "b.json", seed=12)]
    hard = tmp_path / "hard.json"
    hard.write_text(json.dumps({"instances": [{"task_class": "ExpenseDeleteSingle"}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="class_absent_from_scored_hard"):
        build_induction_packet(
            route_id="expense_delete", route={"app": "x"}, donors=donors,
            repository_root=tmp_path, scored_hard_manifest=hard,
        )
