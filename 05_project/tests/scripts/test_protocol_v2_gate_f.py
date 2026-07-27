from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import random

from android_world import registry
from PIL import Image


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = (
    ROOT / "05_project/configs/experiments/v2_hard_micro_gate.json"
)
RUNNER = ROOT / "05_project/scripts/run_protocol_v2_gate_f.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("gate_f_runner", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frozen_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_gate_f_manifest_is_exactly_six_paired_hard_tasks() -> None:
    value = frozen_manifest()
    assert value["source_tag"] == "protocol-v2-gate-e-pass"
    assert (
        value["source_commit"]
        == "0ddf83cad60647409b16a0c60c16b528a9cb19e6"
    )
    assert value["instance_seed"] == 20260730
    assert value["blocked_order_seed"] == 2026073001
    assert len(value["schedule"]) == 12
    assert [row["sequence"] for row in value["schedule"]] == list(
        range(1, 13)
    )
    assert {row["variant"] for row in value["schedule"]} == {"B3", "M0"}

    pairs: dict[str, list[dict]] = {}
    for row in value["schedule"]:
        pairs.setdefault(row["task_id"], []).append(row)
    assert set(pairs) == {"H01", "H03", "H05", "H15", "H16", "H17"}
    assert all(len(rows) == 2 for rows in pairs.values())
    assert all(
        {row["variant"] for row in rows} == {"B3", "M0"}
        for rows in pairs.values()
    )

    hard = json.loads(
        (
            ROOT
            / "05_project/configs/task_manifests/androidworld_hard_v1.json"
        ).read_text(encoding="utf-8")
    )
    hard_rows = {
        row["id"]: (row["class_name"], row["native_max_steps"])
        for row in hard["tasks"]
    }
    for task_id, rows in pairs.items():
        assert {
            (row["task"], row["max_steps"]) for row in rows
        } == {hard_rows[task_id]}


def test_gate_f_batches_are_isolated_and_balanced() -> None:
    value = frozen_manifest()
    schedule = value["schedule"]
    for batch in (1, 2, 3):
        rows = [row for row in schedule if row["batch"] == batch]
        assert len(rows) == 4
        assert sum(row["variant"] == "B3" for row in rows) == 2
        assert len({row["task_id"] for row in rows}) == 4
    pair_batches: dict[str, set[int]] = {}
    for row in schedule:
        pair_batches.setdefault(row["task_id"], set()).add(row["batch"])
    assert all(len(batches) == 2 for batches in pair_batches.values())
    assert all(
        left["task_id"] != right["task_id"]
        for left, right in zip(schedule, schedule[1:])
    )
    assert not value["stop_policy"]["automatic_next_batch"]
    assert not value["stop_policy"]["automatic_gate_g_transition"]


def test_gate_f_blocked_order_reproduces_candidate_21() -> None:
    value = frozen_manifest()
    cells = [
        {
            "task_id": task["task_id"],
            "task": task["task"],
            "variant": variant,
            "max_steps": task["max_steps"],
        }
        for task in value["task_families"]
        for variant in value["variants"]
    ]
    generator = random.Random(value["blocked_order_seed"])
    selected = None
    selected_index = None
    for candidate_index in range(100_000):
        order = cells[:]
        generator.shuffle(order)
        batches = [order[index : index + 4] for index in range(0, 12, 4)]
        valid = all(
            len({row["task_id"] for row in batch}) == 4
            and sum(row["variant"] == "B3" for row in batch) == 2
            for batch in batches
        ) and all(
            left["task_id"] != right["task_id"]
            for left, right in zip(order, order[1:])
        )
        if valid:
            selected = order
            selected_index = candidate_index
            break
    assert selected_index == value["blocked_order_candidate_index"] == 21
    assert selected is not None
    frozen = [
        {
            key: row[key]
            for key in ("task_id", "task", "variant", "max_steps")
        }
        for row in value["schedule"]
    ]
    assert selected == frozen


def test_gate_f_runner_validates_manifest_and_tasks_exist() -> None:
    module = load_runner()
    value = frozen_manifest()
    module.validate_manifest(value)
    task_registry = registry.TaskRegistry()
    registered = task_registry.get_registry(
        task_registry.ANDROID_WORLD_FAMILY
    )
    assert all(row["task"] in registered for row in value["schedule"])


def test_gate_f_runner_rejects_order_drift() -> None:
    module = load_runner()
    value = frozen_manifest()
    value["schedule"][0]["sequence"] = 2
    try:
        module.validate_manifest(value)
    except RuntimeError as exc:
        assert "sequence" in str(exc)
    else:
        raise AssertionError("sequence drift must be rejected")


def test_gate_f_instance_hashes_and_snapshots_are_restart_stable() -> None:
    module = load_runner()
    value = frozen_manifest()
    task_registry = registry.TaskRegistry()
    registered = task_registry.get_registry(
        task_registry.ANDROID_WORLD_FAMILY
    )
    for task_name in sorted({row["task"] for row in value["schedule"]}):
        first = module.generate_task(
            registered, task_name, value["instance_seed"]
        )
        second = module.generate_task(
            registered, task_name, value["instance_seed"]
        )
        assert module.instance_hash(first) == module.instance_hash(second)
        snapshot = {
            "goal": str(first.goal),
            "params": module._json_safe(first.params),
        }
        assert json.loads(json.dumps(snapshot)) == snapshot


def test_gate_f_image_parameter_hash_uses_pixels_not_object_address() -> None:
    module = load_runner()
    first = Image.new("RGB", (3, 2), (12, 34, 56))
    second = Image.new("RGB", (3, 2), (12, 34, 56))
    third = Image.new("RGB", (3, 2), (12, 34, 57))
    first_safe = module._json_safe(first)
    second_safe = module._json_safe(second)
    third_safe = module._json_safe(third)
    assert first_safe == second_safe
    assert first_safe != third_safe
    assert set(first_safe) == {
        "__type__",
        "mode",
        "size",
        "pixel_sha256",
    }


def test_gate_f_reset_audit_requires_both_isolation_events(
    tmp_path: Path,
) -> None:
    module = load_runner()
    events = tmp_path / "events.jsonl"
    events.write_text(
        "\n".join(
            [
                json.dumps({"event": "task_torn_down"}),
                json.dumps({"event": "post_episode_reset"}),
            ]
        ),
        encoding="utf-8",
    )
    assert module.event_reset_audit(tmp_path)["passed"]
    events.write_text(
        json.dumps({"event": "task_torn_down"}), encoding="utf-8"
    )
    assert not module.event_reset_audit(tmp_path)["passed"]


def test_gate_f_aggregate_accepts_only_complete_balanced_evidence() -> None:
    module = load_runner()
    value = frozen_manifest()
    results = []
    for row in value["schedule"]:
        results.append(
            {
                **row,
                "seed": value["instance_seed"],
                "goal_sha256": f"goal-{row['task_id']}",
                "params_sha256": f"params-{row['task_id']}",
                "success": True,
                "failure_code": None,
                "termination_reason": "model_done",
                "model_call_count": 10,
                "wall_time_seconds": 10.0,
                "answer_action_count": (
                    1 if row["task_id"] == "H17" else 0
                ),
                "answer_cache_match_count": (
                    1 if row["task_id"] == "H17" else 0
                ),
                "completion_adjudication_count": 0,
                "memory_audit_errors": [],
                "max_prompt_tokens": 1024,
                "reset_audit": {"passed": True},
                "evaluator_prompt_leak_steps": [],
                "valid_after_one_repair": True,
                "unhandled_third_identical_no_effect_action": False,
                "loop_recovery_obligation_count": 0,
                "loop_recovery_completion_count": 0,
                "loop_recovery_validation_block_count": 0,
            }
        )
    summary = module.aggregate(
        manifest=value,
        health={
            "backend": module.EXPECTED_BACKEND,
            "revision": module.EXPECTED_REVISION,
        },
        results=results,
        infrastructure_attempts=[],
        gate_started_at="2026-07-27T00:00:00+00:00",
        active_seconds=120.0,
        batch_runs=[],
        current_batch=3,
        stopped_early=False,
        stop_reason=None,
    )
    assert summary["gate_passed"]
    assert all(summary["criteria"].values())

    for result in results:
        if result["variant"] == "M0":
            result["wall_time_seconds"] = 20.0
    summary = module.aggregate(
        manifest=value,
        health={
            "backend": module.EXPECTED_BACKEND,
            "revision": module.EXPECTED_REVISION,
        },
        results=results,
        infrastructure_attempts=[],
        gate_started_at="2026-07-27T00:00:00+00:00",
        active_seconds=180.0,
        batch_runs=[],
        current_batch=3,
        stopped_early=False,
        stop_reason=None,
    )
    assert not summary["gate_passed"]
    assert not summary["criteria"]["wall_time_ratio"]
