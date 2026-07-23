"""Audit repeated AndroidWorld task generation and reset determinism."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
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
from android_world.env import env_launcher  # noqa: E402
from raven_m.controller.episode_controller import _json_safe  # noqa: E402


TASKS = [
    ("ContactsAddContact", 20260723),
    ("ClockTimerEntry", 20260724),
    ("MarkorCreateNote", 20260726),
]


def digest_json(value: Any) -> str:
    return sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def pixel_digest(state: Any) -> str:
    return sha256(state.pixels.tobytes()).hexdigest()


def ui_semantic_digest(state: Any) -> str:
    """Hash UI semantics while excluding animation and geometry fields."""
    ignored_fragments = {
        "bound",
        "coordinate",
        "drawing_order",
        "timestamp",
    }

    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            if str(value.get("package_name", "")) == "com.android.systemui":
                return None
            return {
                key: clean(item)
                for key, item in sorted(value.items())
                if not any(
                    fragment in key.lower() for fragment in ignored_fragments
                )
            }
        if isinstance(value, list):
            return [item for item in (clean(part) for part in value) if item]
        return value

    return digest_json(clean(_json_safe(state.ui_elements)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "metadata" / "reset_determinism_g4_v2.json",
    )
    args = parser.parse_args()

    task_registry = registry.TaskRegistry()
    registered = task_registry.get_registry(task_registry.ANDROID_WORLD_FAMILY)
    env = env_launcher.load_and_setup_env(
        console_port=args.console_port,
        emulator_setup=False,
        freeze_datetime=True,
        adb_path=args.adb_path,
        grpc_port=args.grpc_port,
    )
    records = []
    try:
        for task_name, seed in TASKS:
            for repeat in range(args.repeats):
                random.seed(seed)
                np.random.seed(seed)
                task_type = registered[task_name]
                params = task_type.generate_random_params()
                task = task_type(params)
                env.reset(go_home=True)
                env.hide_automation_ui()
                task.initialize_task(env)
                initial = env.get_state(wait_to_stabilize=True)
                record = {
                    "task": task_name,
                    "seed": seed,
                    "repeat": repeat,
                    "goal": str(task.goal),
                    "goal_sha256": sha256(
                        str(task.goal).encode("utf-8")
                    ).hexdigest(),
                    "params": _json_safe(task.params),
                    "params_sha256": digest_json(_json_safe(task.params)),
                    "initial_screen_sha256": pixel_digest(initial),
                    "initial_ui_semantic_sha256": ui_semantic_digest(initial),
                    "initial_foreground_activity": env.foreground_activity_name,
                }
                task.tear_down(env)
                home = env.reset(go_home=True)
                record["post_reset_screen_sha256"] = pixel_digest(home)
                record["post_reset_ui_semantic_sha256"] = ui_semantic_digest(
                    home
                )
                record["post_reset_foreground_activity"] = (
                    env.foreground_activity_name
                )
                records.append(record)
    finally:
        env.close()

    per_task = {}
    for task_name, seed in TASKS:
        selected = [record for record in records if record["task"] == task_name]
        per_task[task_name] = {
            "seed": seed,
            "repeats": len(selected),
            "goal_hash_stable": len(
                {record["goal_sha256"] for record in selected}
            )
            == 1,
            "params_hash_stable": len(
                {record["params_sha256"] for record in selected}
            )
            == 1,
            "initial_screen_hash_stable": len(
                {record["initial_screen_sha256"] for record in selected}
            )
            == 1,
            "initial_ui_semantic_hash_stable": len(
                {
                    record["initial_ui_semantic_sha256"]
                    for record in selected
                }
            )
            == 1,
            "initial_foreground_activity_stable": len(
                {
                    record["initial_foreground_activity"]
                    for record in selected
                }
            )
            == 1,
            "post_reset_screen_hash_stable": len(
                {record["post_reset_screen_sha256"] for record in selected}
            )
            == 1,
            "post_reset_ui_semantic_hash_stable": len(
                {
                    record["post_reset_ui_semantic_sha256"]
                    for record in selected
                }
            )
            == 1,
            "post_reset_foreground_activity_stable": len(
                {
                    record["post_reset_foreground_activity"]
                    for record in selected
                }
            )
            == 1,
        }
    passed = all(
        result["goal_hash_stable"]
        and result["params_hash_stable"]
        and result["initial_ui_semantic_hash_stable"]
        and result["initial_foreground_activity_stable"]
        and result["post_reset_ui_semantic_hash_stable"]
        and result["post_reset_foreground_activity_stable"]
        for result in per_task.values()
    )
    output = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if passed else "failed",
        "acceptance": (
            "goal, generated parameters, foreground activity, and geometry/"
            "system-UI-insensitive semantic UI hashes must be stable for "
            "3 tasks x 3 repeats; exact pixel hashes are diagnostic only"
        ),
        "per_task": per_task,
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2, ensure_ascii=False))
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
