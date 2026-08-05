"""Run the frozen two-task S1 smoke for RAVEN B3 or M0."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import random
import sys
from typing import Any
import uuid

import numpy as np


TASKS = ("ContactsAddContact", "ClockStopWatchRunning")
TASK_SEED = 20260805
MAX_ACTIONS = 8
ARM_TO_VARIANT = {"CB-PX-B3": "B3", "CB-PX-M0": "M0"}
REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = REPO_ROOT / "05_project"


def digest_file(path: Path) -> str:
    value = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def digest_json(value: Any) -> str:
    return sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def instantiate_frozen_task(registered: dict[str, Any], spec: dict[str, Any]) -> Any:
    """Build the exact JSON-native S1b instance before any model call."""
    task_type = registered[str(spec["task_class"])]
    task = task_type(spec["params"])
    actual_params = digest_json(task.params)
    actual_goal = sha256(str(task.goal).encode("utf-8")).hexdigest()
    if actual_params != str(spec["task_params_hash"]):
        raise RuntimeError(f"Frozen params drift for {spec['task_class']}")
    if actual_goal != str(spec["goal_hash"]):
        raise RuntimeError(f"Frozen goal drift for {spec['task_class']}")
    return task


def read_events(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def require_authorization(path: Path, arm_id: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    for key in (
        "s0_all_global_gates_pass",
        "minimum_potential_launch_set_pass",
        "s1_first_call_manifest_frozen",
        "s1_generation_authorized",
    ):
        if value.get(key) is not True:
            raise RuntimeError(f"S1 authorization denied: {key}")
    if arm_id not in value.get("qualified_arms", []):
        raise RuntimeError(f"S1 authorization does not qualify {arm_id}")
    return value


def verify_protected(protocol: dict[str, Any]) -> None:
    for relative, expected in protocol["protected_paths"].items():
        if digest_file(REPO_ROOT / relative).casefold() != expected.casefold():
            raise RuntimeError(f"Protected path drift: {relative}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm-id", choices=tuple(ARM_TO_VARIANT), required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--task-manifest", type=Path)
    parser.add_argument("--stage-label", default="multi_framework_s1_v0_2_dev_only")
    args = parser.parse_args()

    authorization = require_authorization(args.authorization, args.arm_id)
    protocol = json.loads((PROJECT_ROOT / "configs/experiments/multi_framework_hard_benchmark_v0_2.json").read_text(encoding="utf-8"))
    verify_protected(protocol)
    output = args.output_root.resolve()
    if output.exists():
        raise RuntimeError("S1 output root must not pre-exist")
    for frozen in protocol["old_frozen_roots"]:
        frozen_path = (REPO_ROOT / frozen).resolve()
        if output == frozen_path or frozen_path in output.parents or output in frozen_path.parents:
            raise RuntimeError("S1 output overlaps a frozen output root")
    output.mkdir(parents=True)

    source = args.source_root.resolve()
    source_project = source / "05_project"
    sys.path[:0] = [
        str(source_project / "src"),
        str(source_project / "scripts"),
        str(REPO_ROOT / "03_code" / "third_party" / "android_world"),
        str(REPO_ROOT / "06_local_runtime" / "scripts"),
    ]
    import androidworld_compat  # noqa: F401
    from android_world import registry
    from android_world.env import env_launcher
    from raven_m.controller.episode_controller import EpisodeController
    from raven_m.history.policies import make_history_policy
    from raven_m.models.transformers_client import TransformersClient

    manifest = json.loads(args.task_manifest.read_text(encoding="utf-8")) if args.task_manifest else None
    task_specs = manifest["tasks"] if manifest else [
        {"task_class": task, "task_seed": TASK_SEED} for task in TASKS
    ]
    max_actions = int(manifest.get("maximum_actions_per_task", MAX_ACTIONS)) if manifest else MAX_ACTIONS

    variant = ARM_TO_VARIANT[args.arm_id]
    client = TransformersClient(args.url)
    health = client.health()
    prompts = {
        key: (source_project / relative).read_text(encoding="utf-8")
        for key, relative in {
            "executor": "prompts/executor_v1.md",
            "executor_raven": "prompts/executor_raven_v1.md",
            "summary": "prompts/summary_v1.md",
            "planner": "prompts/planner_v1.md",
            "critic": "prompts/critic_v1.md",
        }.items()
    }
    if variant == "B3":
        policy = make_history_policy("B3", client=client, summary_system_prompt=prompts["summary"])
        system_prompt = prompts["executor"]
        schema_path = None
        max_calls = 2 * max_actions + 2 * math.ceil(max_actions / 5)
    else:
        policy = make_history_policy(
            "M0", client=client, summary_system_prompt="",
            planner_system_prompt=prompts["planner"], critic_system_prompt=prompts["critic"],
        )
        system_prompt = prompts["executor_raven"]
        schema_path = source_project / "schemas/action.raven.v1.schema.json"
        max_calls = 3 * max_actions + 4

    registered = registry.TaskRegistry().get_registry(registry.TaskRegistry.ANDROID_WORLD_FAMILY)
    env = env_launcher.load_and_setup_env(
        console_port=args.console_port, emulator_setup=False, freeze_datetime=True,
        adb_path=args.adb_path, grpc_port=args.grpc_port,
    )
    results = []
    run_id = f"s1-{args.arm_id.casefold()}-{uuid.uuid4().hex[:12]}"
    arm_capability = authorization["capabilities"][args.arm_id]
    try:
        for task_index, task_spec in enumerate(task_specs):
            task_class = task_spec["task_class"]
            task_seed = int(task_spec["task_seed"])
            if args.task_manifest:
                task = instantiate_frozen_task(registered, task_spec)
            else:
                random.seed(task_seed)
                np.random.seed(task_seed)
                task_type = registered[task_class]
                task = task_type(task_type.generate_random_params())
            episode_dir = output / f"{task_index + 1:02d}_{task_class}"
            controller = EpisodeController(
                client=client,
                system_prompt=system_prompt,
                max_steps=max_actions,
                max_model_calls=max_calls,
                history_policy=policy,
                action_schema_path=schema_path,
            )
            summary = controller.run(
                env=env, task=task,
                episode_id=f"{run_id}-{task_index + 1}",
                episode_dir=episode_dir,
                seed=task_seed,
                protocol=args.stage_label,
                variant=variant,
            )
            raw_events = read_events(episode_dir / "events.jsonl")
            evaluator_events = [row for row in raw_events if row.get("event") == "evaluator_result"]
            initialized = sum(row.get("event") == "task_initialized" for row in raw_events)
            torn_down = sum(row.get("event") == "task_torn_down" for row in raw_events)
            reset = sum(row.get("event") == "post_episode_reset" for row in raw_events)
            normalized_path = episode_dir / "normalized_events.jsonl"
            step_rows = [row for row in raw_events if row.get("event") == "step"]
            for row_index, row in enumerate(step_rows):
                prompt_dir = episode_dir / "normalized_raw"
                prompt_dir.mkdir(exist_ok=True)
                prompt_path = prompt_dir / f"step_{row_index:03d}.prompt.txt"
                action_path = prompt_dir / f"step_{row_index:03d}.action.json"
                response_path = prompt_dir / f"step_{row_index:03d}.responses.json"
                prompt_path.write_text(row.get("user_prompt", ""), encoding="utf-8")
                action_path.write_text(json.dumps(row.get("decision"), ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
                calls = list(row.get("model_calls", [])) + list(row.get("history_update", {}).get("model_calls", []))
                response_path.write_text(json.dumps(calls, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
                usage = [call.get("usage", {}) for call in calls]
                meta = [call.get("raven_meta", {}) for call in calls]
                decision = row.get("decision") or {}
                event = {
                    "schema_version": "multi_framework_event.v0.2",
                    "run_id": run_id,
                    "arm_id": args.arm_id,
                    "lane": "CB-PX",
                    "reproduction_label": "COMMON_BACKBONE_ADAPTER_COMPARISON",
                    "source_repo": "https://github.com/ScottBlizzard/RAVEN-M",
                    "source_commit": "08b21d06db165d1fb6908c457f955988061b10ca",
                    "checkpoint_id": "Qwen/Qwen3-VL-32B-Instruct",
                    "checkpoint_revision": health["revision"],
                    "code_license": "internal_project_source_no_public_license_claim",
                    "model_license": "apache-2.0",
                    "runtime_hash": arm_capability["runtime_hash"],
                    "dependency_lock_hash": arm_capability["dependency_lock_hash"],
                    "prompt_hash": sha256((system_prompt + "\n\0\n" + row.get("user_prompt", "")).encode("utf-8")).hexdigest(),
                    "task_id": task_spec.get("task_id", f"S1-{task_index + 1:02d}"),
                    "task_class": task_class,
                    "task_seed": task_seed,
                    "task_params_hash": digest_json(summary.get("task_params")),
                    "attempt_id": "a1",
                    "rerun_of": None,
                    "step_index": int(row.get("step", row_index)),
                    "timestamp_utc": row.get("time", datetime.now(timezone.utc).isoformat()),
                    "observation_privileges": ["screenshot"],
                    "screenshot_hash_before": row.get("before_screenshot_sha256"),
                    "screenshot_hash_after_2s": None,
                    "screenshot_hash_after_5s": None,
                    "ui_tree_hash_before": None,
                    "ui_tree_hash_after": None,
                    "model_role": "executor",
                    "call_id": calls[-1].get("call_id") if calls else None,
                    "input_tokens": sum(int(item.get("prompt_tokens", 0)) for item in usage),
                    "output_tokens": sum(int(item.get("completion_tokens", 0)) for item in usage),
                    "latency_seconds": sum(float(item.get("latency_seconds", 0.0)) for item in meta),
                    "raw_prompt_path": str(prompt_path),
                    "raw_response_path": str(response_path),
                    "raw_response_hash": digest_file(response_path),
                    "parse_status": "PASS" if row.get("parse", {}).get("valid_after_one_repair") else "FAIL",
                    "feedback_event": row_index > 0,
                    "feedback_type": "previous_action_observation" if row_index > 0 else None,
                    "action_raw_path": str(action_path),
                    "action_canonical": (decision.get("action") if isinstance(decision, dict) else None),
                    "action_execute_status": "EXECUTED" if row.get("executed") else "NOT_EXECUTED",
                    "pixel_effect_class": "CHANGED" if row.get("screenshot_changed") else "STRICT_NO_EFFECT",
                    "tree_effect_class": None,
                    "finish_claim": decision.get("status") in {"complete", "infeasible"},
                    "evaluator_reward": summary.get("evaluator_reward") if row_index == len(step_rows) - 1 else None,
                    "validity_class": "PENDING",
                    "failure_edge": None,
                }
                with normalized_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            results.append({
                "task_class": task_class,
                "summary": summary,
                "task_initialization": initialized,
                "task_teardown": torn_down,
                "post_episode_reset": reset,
                "evaluator_calls": len(evaluator_events),
                "parseable_decisions": sum(row.get("parse", {}).get("valid_after_one_repair", False) for row in step_rows),
                "executed_nonterminal_actions": sum(bool(row.get("executed")) for row in step_rows),
                "observed_state_changes": sum(bool(row.get("screenshot_changed")) for row in step_rows),
                "normalized_event_count": len(step_rows),
            })
    finally:
        env.close()

    report = {
        "schema_version": "multi_framework_s1_arm_smoke.v0.2",
        "classification": "DEV_ONLY",
        "run_id": run_id,
        "arm_id": args.arm_id,
        "variant": variant,
        "task_seed": manifest.get("nominal_seed", TASK_SEED) if manifest else TASK_SEED,
        "task_manifest": str(args.task_manifest) if args.task_manifest else None,
        "task_manifest_sha256": digest_file(args.task_manifest) if args.task_manifest else None,
        "max_actions_per_task": max_actions,
        "rerun_count": 0,
        "results": results,
    }
    (output / "s1_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"arm_id": args.arm_id, "tasks": len(results), "output": str(output)}))


if __name__ == "__main__":
    main()
