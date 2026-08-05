"""Freeze one-task manifests for the preregistered four-task Hard pulse."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = REPO_ROOT / "05_project"
SOURCE = PROJECT_ROOT / "configs/task_manifests/androidworld_hard_v2_instances.json"
DEST = PROJECT_ROOT / "configs/task_manifests/hard_pulse_v0_3"
PULSE_IDS = ("H01", "H06", "H09", "H17")
SEED = 20260806


def main() -> None:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    selected = {
        row["task_id"]: row
        for row in source["instances"]
        if row["task_id"] in PULSE_IDS and int(row["task_seed"]) == SEED
    }
    if tuple(sorted(selected)) != tuple(sorted(PULSE_IDS)):
        raise RuntimeError(f"Hard pulse selection incomplete: {sorted(selected)}")
    DEST.mkdir(parents=True, exist_ok=True)
    for task_id in PULSE_IDS:
        row = selected[task_id]
        payload = {
            "classification": "FROZEN_HARD_PULSE",
            "manifest_id": f"hard_pulse_v0_3_{task_id}",
            "maximum_actions_per_task": int(row["native_max_steps"]),
            "model_calls_before_hash_verification": 0,
            "nominal_seed": SEED,
            "protocol_id": "MULTI_FRAMEWORK_HARD_PULSE_V0_3",
            "scientific_failure_reruns": 0,
            "source_manifest": str(SOURCE.relative_to(REPO_ROOT)),
            "tasks": [row],
        }
        path = DEST / f"{task_id}.json"
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(path.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
