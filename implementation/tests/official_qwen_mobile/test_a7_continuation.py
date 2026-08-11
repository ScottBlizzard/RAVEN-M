from __future__ import annotations

import json
from pathlib import Path

import pytest

from raven_m.official_qwen_mobile.a7_continuation import (
    CONTINUATION_EXPERIMENT_ID,
    MISSING_GATE_TASKS,
    PARENT_EXPERIMENT_ID,
    PARENT_VALID_TASKS,
    build_plan,
    canonicalize_summaries,
    gate_report,
    validate_plan,
)
from raven_m.official_qwen_mobile.a678_contract import (
    A0_PRESERVATION_TASKS,
    TASK_SEED,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _summary(task_name: str, *, success: bool = False) -> dict:
    return {
        "task_name": task_name,
        "seed": TASK_SEED,
        "episode_id": f"{task_name}_{TASK_SEED}_fixture",
        "evaluator_reward": float(success),
        "success": success,
        "error": None,
        "lifecycle_errors": [],
        "steps": [
            {"model_call": {"raven_meta": {"transport_attempts": 1}}}
        ],
    }


def _parent(tmp_path: Path) -> Path:
    parent = tmp_path / "official_qwen_parent"
    summaries = [
        _summary(name, success=(name == "ExpenseDeleteMultiple2"))
        for name in PARENT_VALID_TASKS
    ]
    (parent / "episodes").mkdir(parents=True)
    for summary in summaries:
        episode_dir = parent / "episodes" / summary["episode_id"]
        episode_dir.mkdir()
        (episode_dir / "episode.json").write_text(
            json.dumps(summary), encoding="utf-8"
        )
    (parent / "run_signature.json").write_text(
        json.dumps(
            {
                "experiment_id": PARENT_EXPERIMENT_ID,
                "method": "a7_deterministic_active_goal_item_status_ledger_v1",
            }
        ),
        encoding="utf-8",
    )
    (parent / "checkpoint.json").write_text(
        json.dumps(
            {
                "status": "stopped_invalid_episode",
                "valid_summaries": summaries,
                "invalid_attempts": [
                    {
                        "task_name": "OsmAndMarker",
                        "reason": "controller_or_lifecycle_invalid",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return parent


def _specs() -> list[dict]:
    manifest = json.loads(
        (
            REPOSITORY_ROOT
            / "implementation/configs/androidworld_hard_v2_instances.json"
        ).read_text(encoding="utf-8")
    )
    return [
        item
        for item in manifest["instances"]
        if int(item["task_seed"]) == TASK_SEED
    ]


def test_plan_retains_seven_and_runs_three_missing_gate_tasks_first(
    tmp_path: Path,
) -> None:
    parent = _parent(tmp_path)
    manifest = (
        REPOSITORY_ROOT
        / "implementation/configs/androidworld_hard_v2_instances.json"
    )
    plan = build_plan(
        parent_suite_dir=parent,
        canonical_specs=_specs(),
        manifest_path=manifest,
    )
    assert plan["experiment_id"] == CONTINUATION_EXPERIMENT_ID
    assert plan["generation_calls"] == 0
    assert plan["already_valid_count"] == 7
    assert [row[0] for row in plan["execution_schedule"][:3]] == list(
        MISSING_GATE_TASKS
    )
    assert plan["remaining_after_gate_count"] == 9
    all_keys = plan["already_valid_keys"] + plan["execution_schedule"]
    assert len(all_keys) == 19
    assert len({tuple(key) for key in all_keys}) == 19


def test_plan_validation_detects_parent_mutation(tmp_path: Path) -> None:
    parent = _parent(tmp_path)
    manifest = (
        REPOSITORY_ROOT
        / "implementation/configs/androidworld_hard_v2_instances.json"
    )
    plan = build_plan(
        parent_suite_dir=parent,
        canonical_specs=_specs(),
        manifest_path=manifest,
    )
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    validate_plan(
        plan_path=plan_path,
        parent_suite_dir=parent,
        canonical_specs=_specs(),
        manifest_path=manifest,
    )
    checkpoint = json.loads((parent / "checkpoint.json").read_text(encoding="utf-8"))
    checkpoint["valid_summaries"][0]["evaluator_reward"] = 1.0
    (parent / "checkpoint.json").write_text(json.dumps(checkpoint), encoding="utf-8")
    with pytest.raises(RuntimeError, match="parent validation failed|plan drift"):
        validate_plan(
            plan_path=plan_path,
            parent_suite_dir=parent,
            canonical_specs=_specs(),
            manifest_path=manifest,
        )


def test_gate_is_blocking_until_all_four_succeed() -> None:
    summaries = [_summary("ExpenseDeleteMultiple2", success=True)]
    pending = gate_report(summaries)
    assert pending["status"] == "pending"
    assert pending["required_for_suite_continuation"] is True
    assert pending["missing_tasks"] == list(MISSING_GATE_TASKS)
    summaries.extend(_summary(name, success=True) for name in MISSING_GATE_TASKS)
    assert gate_report(summaries)["status"] == "passed"
    failed = summaries[:-1] + [_summary(MISSING_GATE_TASKS[-1], success=False)]
    assert gate_report(failed)["status"] == "failed"


def test_canonicalization_preserves_unique_results() -> None:
    expected = [(name, TASK_SEED) for name in A0_PRESERVATION_TASKS]
    summaries = [_summary(name, success=True) for name in reversed(A0_PRESERVATION_TASKS)]
    ordered = canonicalize_summaries(summaries, expected)
    assert [item["task_name"] for item in ordered] == list(A0_PRESERVATION_TASKS)
    with pytest.raises(RuntimeError, match="duplicate"):
        canonicalize_summaries(summaries + [summaries[0]], expected)


def test_runner_contains_blocking_a7_continuation_hooks() -> None:
    source = (
        REPOSITORY_ROOT / "implementation/scripts/run_official_qwen_mobile.py"
    ).read_text(encoding="utf-8")
    assert '"--a7-continuation-plan"' in source
    assert '"--a7-parent-suite-dir"' in source
    assert "validate_a7_continuation_plan" in source
    assert "stopped_capability_gate_failure" in source
    assert "canonicalize_a7_summaries" in source
