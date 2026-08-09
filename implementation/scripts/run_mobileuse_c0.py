"""Run the frozen C0 native-MobileUse control on all 19 Hard classes."""

from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
import math
from pathlib import Path
import shutil
import traceback
from typing import Any
from uuid import uuid4

import run_mobileuse_hard as pf01
from raven_m.models.vllm_multi_image_client import VLLMMultiImageClient
from raven_m.public_frameworks.mobileuse.c0_controller import (
    ARM_ID, C0NativeMobileUseController,
)
from raven_m.public_frameworks.mobileuse.c0_reset import (
    initialize_task_with_native_resets,
)
from raven_m.public_frameworks.mobileuse.logging import LayeredEventLog
from raven_m.public_frameworks.mobileuse.mechanism_metrics import (
    extract as extract_mechanism_metrics,
)


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
BACKEND_ID = "qwen3_vl_32b_vllm_bf16_1xrtxpro6000_mobileuse_c0_v1"
TASK_SEED = 20260806
BUDGET_MULTIPLIER = 1.2
TASK_ORDER = [
    "H08", "H12", "H05", "H14", "H04", "H16", "H19", "H13", "H18",
    "H06", "H03", "H11", "H02", "H10", "H15", "H09", "H17", "H01", "H07",
]
MASTER_MANIFEST = pf01.REPOSITORY_ROOT / "implementation/configs/androidworld_hard_v2_instances.json"
CONFIG_PATH = pf01.REPOSITORY_ROOT / "implementation/configs/c0_native_mobileuse_qwen3_vl_32b_hard_seed20260806.yaml"
PREREG_PATH = pf01.REPOSITORY_ROOT / "protocols/C0_NATIVE_MOBILEUSE_HARD_PREREG.md"
PREFLIGHT_PATH = pf01.REPOSITORY_ROOT / "evidence/public_framework/mobileuse_c0/C0_ZERO_GENERATION_PREFLIGHT.json"
FREEZE_FILES = [
    CONFIG_PATH,
    PREREG_PATH,
    Path(__file__).resolve(),
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/public_frameworks/mobileuse/c0_action_adapter.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/public_frameworks/mobileuse/c0_controller.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/public_frameworks/mobileuse/c0_reset.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/public_frameworks/mobileuse/controller.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/public_frameworks/mobileuse/logging.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/public_frameworks/mobileuse/mechanism_metrics.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/env/androidworld_adapter.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/models/vllm_multi_image_client.py",
    pf01.REPOSITORY_ROOT / "implementation/scripts/preflight_mobileuse_c0.py",
    MASTER_MANIFEST,
]


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def current_freeze() -> dict[str, str]:
    return {
        str(path.relative_to(pf01.REPOSITORY_ROOT)).replace("\\", "/"): digest(path)
        for path in FREEZE_FILES
    }


def model_client(url: str, timeout: float) -> VLLMMultiImageClient:
    return VLLMMultiImageClient(
        url, model_id=MODEL_ID, model_revision=MODEL_REVISION,
        backend_id=BACKEND_ID, temperature=0.7, top_p=0.8, top_k=20,
        presence_penalty=1.5, repetition_penalty=1.0, seed=3407,
        timeout_seconds=timeout,
    )


def load_specs() -> list[dict[str, Any]]:
    manifest = json.loads(MASTER_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("androidworld_commit") != "3e50888527ef9f29b9157ecd537e408008bb1c85":
        raise RuntimeError("AndroidWorld source-lock drift")
    selected = {
        item["task_id"]: dict(item)
        for item in manifest["instances"]
        if int(item["task_seed"]) == TASK_SEED
    }
    if set(selected) != set(TASK_ORDER):
        raise RuntimeError("C0 must contain exactly the 19 frozen Hard task classes")
    specs = []
    for task_id in TASK_ORDER:
        spec = selected[task_id]
        spec["base_native_max_steps"] = int(spec["native_max_steps"])
        spec["native_max_steps"] = int(math.ceil(BUDGET_MULTIPLIER * spec["native_max_steps"]))
        specs.append(spec)
    return specs


def _summary_write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_episode(
    *, env: Any, task: Any, spec: dict[str, Any], client: Any, suite_dir: Path,
) -> dict[str, Any]:
    episode_id = f"{spec['task_id']}_{task.__class__.__name__}_{TASK_SEED}_{uuid4().hex[:8]}"
    episode_dir = suite_dir / "episodes" / episode_id
    episode_dir.mkdir(parents=True, exist_ok=False)
    result = None
    controller = None
    reward = None
    error = None
    initialized = False
    reset_audit = None
    started = pf01.utc_now()
    try:
        env.reset(go_home=True)
        hide = getattr(env, "hide_automation_ui", None)
        if callable(hide):
            hide()
        reset_audit = initialize_task_with_native_resets(task, env)
        initialized = True
        _summary_write(episode_dir / "reset_audit.json", reset_audit)
        if not reset_audit["pass"]:
            raise RuntimeError("Required MobileUse app reset did not complete")
        controller = C0NativeMobileUseController(
            client, env=env, episode_id=episode_id, episode_dir=episode_dir,
            max_steps=int(spec["native_max_steps"]), max_tokens=32768,
        )
        result = controller.run(str(task.goal))
        reward = float(task.is_successful(env))
        controller.log.write(
            "L5", "androidworld_evaluator_result", reward=reward,
            visible_to_agent=False,
        )
        mechanism = extract_mechanism_metrics(
            result.log_path, task_name=task.__class__.__name__, reward=reward
        )
        _summary_write(episode_dir / "mechanism_metrics.json", mechanism)
        controller.log.write(
            "L4", "posthoc_mechanism_summary", agent_visible=False,
            metrics=mechanism,
        )
        chain_errors = LayeredEventLog.validate(result.log_path)
        if chain_errors:
            raise RuntimeError(f"Layered log hash-chain invalid: {chain_errors}")
    except Exception as exc:
        error = {
            "type": type(exc).__name__, "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        if initialized:
            try:
                task.tear_down(env)
            except Exception as exc:
                error = error or {
                    "type": type(exc).__name__, "message": str(exc),
                    "phase": "tear_down",
                }
        try:
            env.reset(go_home=True)
        except Exception as exc:
            error = error or {
                "type": type(exc).__name__, "message": str(exc),
                "phase": "post_reset",
            }
    summary = {
        "schema": "raven_m.c0.episode_summary.v1",
        "arm_id": ARM_ID, "episode_id": episode_id,
        "task_id": spec["task_id"], "task_name": task.__class__.__name__,
        "seed": TASK_SEED,
        "base_native_budget": int(spec["base_native_max_steps"]),
        "c0_budget": int(spec["native_max_steps"]),
        "budget_multiplier": BUDGET_MULTIPLIER,
        "goal_hash": spec.get("goal_hash"),
        "task_params_hash": spec.get("task_params_hash"),
        "started_at": started, "finished_at": pf01.utc_now(),
        "evaluator_reward": reward, "success": reward == 1.0,
        "scientifically_valid": error is None, "error": error,
        "reset_audit": reset_audit,
        "native_actions": result.native_actions if result else None,
        "operator_decisions": result.episode_data.num_steps if result else None,
        "controller_status": pf01.json_safe(result.episode_data.status) if result else None,
        "controller_message": result.episode_data.message if result else None,
        "answer": result.answer if result else None,
        "events_path": str(result.log_path if result else episode_dir / "events.jsonl"),
    }
    _summary_write(episode_dir / "summary.json", summary)
    return summary


def write_aggregate(suite_dir: Path, suite_id: str, health: Any, summaries: list[dict[str, Any]]) -> dict[str, Any]:
    invalid = [item["task_id"] for item in summaries if not item["scientifically_valid"]]
    value = {
        "schema": "raven_m.c0.suite_summary.v1",
        "arm_id": ARM_ID, "suite_id": suite_id,
        "model_health": health, "task_order": TASK_ORDER,
        "seed": TASK_SEED, "budget_multiplier": BUDGET_MULTIPLIER,
        "episode_count": len(summaries),
        "success_count": sum(int(item["success"]) for item in summaries),
        "total_reward": sum(float(item["evaluator_reward"] or 0.0) for item in summaries),
        "scientifically_valid_count": sum(int(item["scientifically_valid"]) for item in summaries),
        "invalid_task_ids": invalid,
        "suite_status": (
            "restart_required_from_h08" if invalid else
            "complete" if len(summaries) == 19 else "running"
        ),
        "episodes": summaries,
    }
    _summary_write(suite_dir / "aggregate.json", value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument("--request-timeout-seconds", type=float, default=3600.0)
    parser.add_argument(
        "--output-root", type=Path,
        default=pf01.REPOSITORY_ROOT / "runs/public_framework/mobileuse_c0",
    )
    args = parser.parse_args()

    if not PREFLIGHT_PATH.is_file():
        raise RuntimeError("C0 zero-generation preflight is missing")
    preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    if preflight.get("status") != "pass":
        raise RuntimeError("C0 zero-generation preflight did not pass")
    if preflight.get("file_sha256") != current_freeze():
        raise RuntimeError("C0 source/config drift after offline freeze")

    client = model_client(args.url, args.request_timeout_seconds)
    health = client.health()
    env = pf01.env_launcher.load_and_setup_env(
        console_port=args.console_port, emulator_setup=False, freeze_datetime=True,
        adb_path=args.adb_path, grpc_port=args.grpc_port,
        a11y_method=pf01.android_world_controller.A11yMethod.UIAUTOMATOR,
    )
    registry_value = pf01.registry.TaskRegistry().get_registry(
        pf01.registry.TaskRegistry.ANDROID_WORLD_FAMILY
    )
    specs = load_specs()
    tasks = [pf01.instantiate_verified(registry_value, spec) for spec in specs]
    suite_id = f"c0_scored_{datetime.now().strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}"
    suite_dir = args.output_root / suite_id
    suite_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(MASTER_MANIFEST, suite_dir / "master_manifest.snapshot.json")
    _summary_write(suite_dir / "source_freeze.snapshot.json", preflight)
    summaries: list[dict[str, Any]] = []
    try:
        for spec, task in zip(specs, tasks):
            summary = run_episode(
                env=env, task=task, spec=spec, client=client, suite_dir=suite_dir
            )
            summaries.append(summary)
            aggregate = write_aggregate(suite_dir, suite_id, health, summaries)
            if not summary["scientifically_valid"]:
                # Generic implementation/infrastructure invalidity is never
                # patched mid-suite. Fix offline, then restart the same order.
                raise RuntimeError(
                    f"C0 qualification invalid at {summary['task_id']}; restart from H08"
                )
    finally:
        env.close()
    print(json.dumps({"suite_dir": str(suite_dir), **aggregate}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
