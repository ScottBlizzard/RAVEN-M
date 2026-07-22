"""No-LLM end-to-end smoke test for the local AndroidWorld runtime."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

import androidworld_compat  # noqa: F401  # Applies pinned-runtime fixes.
from android_world import registry
from android_world.env import env_launcher


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument("--setup-apps", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    env = env_launcher.load_and_setup_env(
        console_port=args.console_port,
        emulator_setup=args.setup_apps,
        freeze_datetime=True,
        adb_path=args.adb_path,
        grpc_port=args.grpc_port,
    )
    try:
        state = env.reset(go_home=True)
        task_registry = registry.TaskRegistry()
        tasks = task_registry.get_registry(task_registry.ANDROID_WORLD_FAMILY)
        task_type = tasks["ContactsAddContact"]
        task = task_type(task_type.generate_random_params())
        task.initialize_task(env)
        state = env.get_state(wait_to_stabilize=True)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        screenshot = args.output.with_suffix(".png")
        Image.fromarray(state.pixels).save(screenshot)
        result = {
            "status": "ok",
            "task": "ContactsAddContact",
            "goal": str(task.goal),
            "registered_android_world_tasks": len(tasks),
            "screen_shape": list(state.pixels.shape),
            "ui_elements": len(state.ui_elements),
            "foreground_activity": env.foreground_activity_name,
            "screenshot": str(screenshot),
        }
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
    finally:
        env.close()


if __name__ == "__main__":
    main()
