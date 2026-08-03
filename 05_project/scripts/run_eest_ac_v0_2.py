"""Run one frozen nine-cell EEST-AC v0.2 blind smoke and stop."""

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
from raven_m.eest_ac.controller_v0_2 import EestAcV02Controller, _json_safe  # noqa: E402
from raven_m.eest_ac.observation_v0_2 import ObservationStabilizer  # noqa: E402
from raven_m.eest_ac.task_roles import ExactSpan, TaskRoleFrame  # noqa: E402
from raven_m.models.transformers_client import TransformersClient  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest_json(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _frame(record: dict[str, Any]) -> TaskRoleFrame:
    def span(value: dict[str, Any] | None) -> ExactSpan | None:
        return ExactSpan(**value) if value else None
    return TaskRoleFrame(
        goal_sha256=record["goal_sha256"],
        intent=record["intent"],
        source=span(record["source"]),
        requested_field=span(record["requested_field"]),
        destination=span(record["destination"]),
        parse_rule=record["parse_rule"],
        frame_sha256=record["frame_sha256"],
    )


def _load_preflight(path: Path, config_path: Path, study_id: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("status") != "pass" or value.get("study_id") != study_id or value.get("zero_model_generation_calls") != 0:
        raise RuntimeError("Passing zero-call study preflight is required.")
    if value.get("runtime_health", {}).get("status") == "not_checked":
        raise RuntimeError("Study preflight did not check the real runtime.")
    if value.get("config_sha256") != sha256(config_path.read_bytes()).hexdigest():
        raise RuntimeError("Config changed after preflight.")
    for relative, expected in value["implementation_hashes"].items():
        if sha256((REPOSITORY_ROOT / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Implementation changed after preflight: {relative}")
    return value


def _task_instance(registered: dict[str, Any], task_class: str, seed: int) -> Any:
    random.seed(seed)
    np.random.seed(seed)
    task_type = registered[task_class]
    return task_type(task_type.generate_random_params())


def _instance_hash(task: Any) -> tuple[str, str]:
    return sha256(str(task.goal).encode("utf-8")).hexdigest(), _digest_json(_json_safe(task.params))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--adb-path", default="adb")
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    preflight = _load_preflight(args.preflight, args.config, config["study_id"])
    suite_dir = REPOSITORY_ROOT / config["run_root"]
    suite_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        suite_dir / "batch_start.json",
        {
            "schema_version": "eest_ac_batch_start.v0_2",
            "study_id": config["study_id"],
            "started_at_utc": _utc_now(),
            "config_sha256": sha256(args.config.read_bytes()).hexdigest(),
            "preflight_sha256": sha256(args.preflight.read_bytes()).hexdigest(),
            "blind_until_batch_complete": True,
            "cell_count": 9,
        },
    )
    prompts = {
        "executor": (PROJECT_ROOT / "prompts/eest_ac/executor_v0_2.md").read_text(encoding="utf-8"),
        "summary": (PROJECT_ROOT / "prompts/eest_ac/summary_v0_1.md").read_text(encoding="utf-8"),
    }
    client = TransformersClient(args.url)
    health = client.health()
    if any(health.get(key) != config["model"][config_key] for key, config_key in (("model", "id"), ("revision", "revision"), ("backend", "backend"))):
        raise RuntimeError("Model health differs from frozen config.")
    registered = registry.TaskRegistry().get_registry(registry.TaskRegistry.ANDROID_WORLD_FAMILY)
    task_specs = {item["task_key"]: item for item in config["tasks"]}
    task_records = preflight["task_instance_records"]
    role_frames = {key: _frame(value["role_frame"]) for key, value in task_records.items()}
    env = env_launcher.load_and_setup_env(
        console_port=args.console_port,
        emulator_setup=False,
        freeze_datetime=True,
        adb_path=args.adb_path,
        grpc_port=args.grpc_port,
    )
    results: list[dict[str, Any]] = []
    try:
        for cell in config["schedule"]:
            spec = task_specs[cell["task_key"]]
            cell_dir = suite_dir / "cells" / f"{cell['cell']:02d}_{cell['task_key']}_{cell['arm']}"
            result_path = cell_dir / "cell_result.json"
            if result_path.is_file():
                results.append(json.loads(result_path.read_text(encoding="utf-8")))
                continue
            cell_dir.mkdir(parents=True, exist_ok=True)
            _write_json(cell_dir / "schedule_record.json", cell)
            attempt_number = len(list(cell_dir.glob("attempt_*"))) + 1
            final = None
            while attempt_number <= 3:
                task = _task_instance(registered, spec["task_class"], spec["parameter_seed"])
                goal_hash, params_hash = _instance_hash(task)
                expected = task_records[cell["task_key"]]
                if goal_hash != expected["goal_sha256"] or params_hash != expected["params_sha256"]:
                    raise RuntimeError("Paired task instance hash drifted after preflight.")
                attempt_dir = cell_dir / f"attempt_{attempt_number:02d}"
                if attempt_dir.exists() and any(attempt_dir.iterdir()):
                    _write_json(cell_dir / f"abandoned_attempt_{attempt_number:02d}.json", {"classified_as": "infrastructure_interruption", "reason": "attempt directory existed without cell result", "goal_sha256": goal_hash, "params_sha256": params_hash})
                    attempt_number += 1
                    continue
                controller = EestAcV02Controller(
                    client=client,
                    executor_prompt=prompts["executor"],
                    summary_prompt=prompts["summary"],
                    arm=cell["arm"],
                    max_environment_actions=spec["max_environment_actions"],
                    max_model_calls=spec["max_model_calls"],
                    max_new_tokens=config["model"]["max_new_tokens"],
                    context_cap_tokens=config["model"]["context_cap_tokens"],
                    task_role_frame=role_frames[cell["task_key"]],
                    stabilizer=ObservationStabilizer(
                        delay_seconds=config["observation_stabilization"]["delay_seconds"],
                        max_post_observations=config["observation_stabilization"]["max_post_observations"],
                    ),
                )
                summary = controller.run(
                    env=env,
                    task=task,
                    episode_id=f"{config['study_id']}_c{cell['cell']:02d}_{cell['task_key']}_{cell['arm']}_a{attempt_number}",
                    episode_dir=attempt_dir,
                    seed=spec["parameter_seed"],
                    study_id=config["study_id"],
                )
                if summary.get("failure_class") == "infrastructure":
                    _write_json(cell_dir / f"infrastructure_attempt_{attempt_number:02d}.json", {"attempt": attempt_number, "goal_sha256": goal_hash, "params_sha256": params_hash, "error": summary["error"]})
                    attempt_number += 1
                    continue
                final = {
                    "cell": cell["cell"],
                    "task_key": cell["task_key"],
                    "task_class": spec["task_class"],
                    "role": spec["role"],
                    "arm": cell["arm"],
                    "attempt": attempt_number,
                    "goal_sha256": goal_hash,
                    "params_sha256": params_hash,
                    "episode_summary_path": str((attempt_dir / "episode_summary.json").relative_to(REPOSITORY_ROOT)).replace("\\", "/"),
                    "task_success": summary["task_success"],
                    "evaluator_reward": summary["evaluator_reward"],
                    "evaluator_status": summary["evaluator_status"],
                    "termination_reason": summary["termination_reason"],
                    "failure_class": summary["failure_class"],
                    "environment_actions": summary["environment_actions"],
                    "model_calls": summary["model_calls"],
                    "model_call_record_count": summary["model_call_record_count"],
                    "model_call_accounting_valid": summary["model_call_accounting_valid"],
                    "auxiliary_calls": summary["auxiliary_calls"],
                    "eligible_opportunities": summary["eligible_opportunities"],
                    "planned_auxiliary_calls": summary["planned_auxiliary_calls"],
                    "realized_auxiliary_calls": summary["realized_auxiliary_calls"],
                    "prompt_tokens": summary["prompt_tokens"],
                    "completion_tokens": summary["completion_tokens"],
                    "total_tokens": summary["total_tokens"],
                    "wall_time_seconds": summary["wall_time_seconds"],
                    "schema_truncation_count": summary["schema_truncation_count"],
                    "completion_tp": summary["completion_tp"],
                    "completion_fp": summary["completion_fp"],
                    "completion_fn": summary["completion_fn"],
                    "repeated_action_blocks": summary["repeated_action_blocks"],
                    "different_class_after_recovery": summary["different_class_after_recovery"],
                    "error": summary["error"],
                }
                _write_json(result_path, final)
                results.append(final)
                break
            if final is None:
                raise RuntimeError(f"Cell {cell['cell']} exhausted infrastructure retries.")
        if len(results) != 9:
            raise RuntimeError("Blind runner stopped before nine final cells.")
        unblinded = {}
        for task_key, spec in task_specs.items():
            task = _task_instance(registered, spec["task_class"], spec["parameter_seed"])
            unblinded[task_key] = {"task_class": spec["task_class"], "goal": str(task.goal), "params": _json_safe(task.params), "goal_sha256": _instance_hash(task)[0], "params_sha256": _instance_hash(task)[1], "task_role_frame": role_frames[task_key].record()}
        _write_json(suite_dir / "instances_unblinded_after_batch.json", unblinded)
        _write_json(
            suite_dir / "batch_complete.json",
            {
                "schema_version": "eest_ac_batch_complete.v0_2",
                "study_id": config["study_id"],
                "completed_at_utc": _utc_now(),
                "cell_count": 9,
                "trajectory_blind_lock_released": True,
                "results": sorted(results, key=lambda item: item["cell"]),
                "runner_stop_reason": "preregistered_nine_cell_batch_complete_no_auto_expand",
            },
        )
        print(json.dumps({"status": "complete", "study_id": config["study_id"], "cells": 9, "output": str(suite_dir), "next": "stop_and_analyze"}, indent=2))
    finally:
        env.close()


if __name__ == "__main__":
    main()
