from __future__ import annotations

import json
from pathlib import Path

from android_world import registry


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = (
    ROOT / "05_project/configs/experiments/v2_capability_gate.json"
)


def test_gate_e_is_exactly_four_paired_nonhard_tasks() -> None:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert value["source_tag"] == "protocol-v2-dev"
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
