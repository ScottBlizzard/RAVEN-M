from __future__ import annotations

import json
from pathlib import Path
import importlib.util

from android_world import registry


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = (
    ROOT / "05_project/configs/experiments/v2_capability_gate.json"
)


def test_gate_e_is_exactly_four_paired_nonhard_tasks() -> None:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert value["source_tag"] == "protocol-v2-dev-r4"
    assert (
        value["source_commit"]
        == "de5278b6fc78ca01d4b530ef1442e5060dccbf10"
    )
    assert len(value["schedule"]) == 8
    assert {item["variant"] for item in value["schedule"]} == {"B3", "M0"}
    counts = {}
    for item in value["schedule"]:
        counts.setdefault(item["task"], set()).add(item["variant"])
    assert len(counts) == 4
    assert all(variants == {"B3", "M0"} for variants in counts.values())
    hard = json.loads(
        (
            ROOT
            / "05_project/configs/task_manifests/androidworld_hard_v1.json"
        ).read_text(encoding="utf-8")
    )
    hard_names = {item["class_name"] for item in hard["tasks"]}
    assert not (set(counts) & hard_names)


def test_gate_e_tasks_exist_and_automatic_gate_f_is_disabled() -> None:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    task_registry = registry.TaskRegistry()
    registered = task_registry.get_registry(
        task_registry.ANDROID_WORLD_FAMILY
    )
    assert all(item["task"] in registered for item in value["schedule"])
    assert not value["stop_policy"]["automatic_gate_f_transition"]
    assert value["limits"]["max_valid_cells"] == 8
    assert value["limits"]["hard_wall_time_seconds"] == 7200


def test_gate_e_aggregator_handles_invalid_decision_record(
    tmp_path: Path,
) -> None:
    script = ROOT / "05_project/scripts/run_protocol_v2_gate_e.py"
    spec = importlib.util.spec_from_file_location("gate_e_runner", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    episode_dir = ROOT / "runs/protocol_v2/test_null_decision_fixture"
    summary = {
        "steps": [
            {
                "step": 0,
                "decision": None,
                "parse": {"valid_after_one_repair": False},
                "executed": False,
                "user_prompt": "no hidden state",
            }
        ],
        "episode_id": "fixture",
        "task_goal": "Create a contact",
        "task_params": {},
        "success": False,
        "evaluator_reward": 0.0,
        "failure_code": "MODEL_OUTPUT_INVALID_AFTER_REPAIR",
        "termination_reason": "model_output_invalid_after_repair",
        "model_call_count": 2,
        "executor_model_call_count": 2,
        "history_model_call_count": 0,
    }
    result = module.episode_result(
        item={
            "sequence": 1,
            "task": "ContactsAddContact",
            "variant": "B3",
            "seed": 1,
        },
        summary=summary,
        episode_dir=episode_dir,
        attempts=1,
        memory_audit=None,
    )
    assert not result["valid_after_one_repair"]
    assert result["answer_action_count"] == 0
