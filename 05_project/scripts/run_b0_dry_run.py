"""Run one real, non-scored AndroidWorld B0 trajectory."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import random
import sys
from uuid import uuid4

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
LOCAL_RUNTIME = REPOSITORY_ROOT / "06_local_runtime"
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(LOCAL_RUNTIME / "scripts"))

import androidworld_compat  # noqa: E402,F401
from android_world import registry  # noqa: E402
from android_world.env import env_launcher  # noqa: E402
from raven_m.controller.episode_controller import EpisodeController  # noqa: E402
from raven_m.models.transformers_client import TransformersClient  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument("--task", default="ContactsAddContact")
    parser.add_argument("--seed", type=int, default=20260723)
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--max-model-calls", type=int, default=16)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=REPOSITORY_ROOT / "runs" / "excluded_protocol_dry_run",
    )
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    task_registry = registry.TaskRegistry()
    tasks = task_registry.get_registry(task_registry.ANDROID_WORLD_FAMILY)
    if args.task not in tasks:
        raise KeyError(f"Unknown AndroidWorld task: {args.task}")
    task_type = tasks[args.task]
    task = task_type(task_type.generate_random_params())

    episode_id = (
        f"b0_{args.task}_{datetime.now().strftime('%Y%m%dT%H%M%S')}_"
        f"{uuid4().hex[:8]}"
    )
    episode_dir = args.output_root / episode_id
    system_prompt = (
        PROJECT_ROOT / "prompts" / "executor_v0.md"
    ).read_text(encoding="utf-8")
    client = TransformersClient(args.url)
    health = client.health()

    env = env_launcher.load_and_setup_env(
        console_port=args.console_port,
        emulator_setup=False,
        freeze_datetime=True,
        adb_path=args.adb_path,
        grpc_port=args.grpc_port,
    )
    try:
        controller = EpisodeController(
            client=client,
            system_prompt=system_prompt,
            max_steps=args.max_steps,
            max_model_calls=args.max_model_calls,
        )
        summary = controller.run(
            env=env,
            task=task,
            episode_id=episode_id,
            episode_dir=episode_dir,
            seed=args.seed,
        )
        print(
            json.dumps(
                {
                    "episode_dir": str(episode_dir),
                    "episode_id": summary["episode_id"],
                    "task_name": summary["task_name"],
                    "task_goal": summary["task_goal"],
                    "success": summary["success"],
                    "evaluator_reward": summary["evaluator_reward"],
                    "termination_reason": summary["termination_reason"],
                    "failure_code": summary["failure_code"],
                    "decision_count": summary["decision_count"],
                    "executed_action_count": summary["executed_action_count"],
                    "model_call_count": summary["model_call_count"],
                    "first_pass_parse_rate": summary["first_pass_parse_rate"],
                    "model_backend": health["backend"],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        if summary["error"]:
            raise SystemExit(2)
    finally:
        env.close()


if __name__ == "__main__":
    main()
