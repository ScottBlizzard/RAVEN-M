#!/usr/bin/env python3
"""Build exact new-seed Markor instances for the external coverage-gate pilot."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import random
import sys
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
LOCAL_RUNTIME = REPOSITORY_ROOT / "06_local_runtime"
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(LOCAL_RUNTIME / "scripts"))

import androidworld_compat  # noqa: E402,F401
from android_world import registry  # noqa: E402


TASKS = [
    ("H03", "ExpenseAddMultipleFromMarkor"),
    ("H11", "RecipeAddMultipleRecipesFromMarkor"),
    ("H12", "RecipeAddMultipleRecipesFromMarkor2"),
]


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return {"__type__": type(value).__name__, "repr": repr(value)}


def digest(value: Any) -> str:
    payload = json.dumps(
        json_safe(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=20260809)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    available = registry.TaskRegistry().get_registry(
        registry.TaskRegistry.ANDROID_WORLD_FAMILY
    )
    instances = []
    for task_id, task_class in TASKS:
        random.seed(args.seed)
        np.random.seed(args.seed)
        task_type = available[task_class]
        task = task_type(task_type.generate_random_params())
        instances.append(
            {
                "task_id": task_id,
                "task_class": task_class,
                "task_seed": args.seed,
                "task_params_hash": digest(task.params),
                "goal_hash": sha256(str(task.goal).encode("utf-8")).hexdigest(),
                "native_max_steps": 60,
            }
        )
    result = {
        "manifest_id": "source_document_coverage_gate_markor_seed_20260809_v1",
        "claim_class": "new_instance_development_matched_source_stage_pilot_not_held_out",
        "androidworld_commit": "3e50888527ef9f29b9157ecd537e408008bb1c85",
        "instance_generation": "independent random.seed(seed) and numpy.random.seed(seed) per task class",
        "instances": instances,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
