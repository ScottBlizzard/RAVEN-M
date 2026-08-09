"""Run the frozen PF01 MobileUse smoke or scored AndroidWorld arm."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import random
import shutil
import sys
import traceback
from typing import Any
from uuid import uuid4

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
SOURCE_REPOSITORY = REPOSITORY_ROOT.parent / "RAVEN-M-Research"
LOCAL_RUNTIME = SOURCE_REPOSITORY / "06_local_runtime"
VENDOR_ROOT = PROJECT_ROOT / "third_party" / "mobile_use" / "upstream"
sys.path[:0] = [
    str(PROJECT_ROOT / "src"),
    str(PROJECT_ROOT / "src" / "raven_m" / "multi_framework_benchmark"),
    str(VENDOR_ROOT),
    str(LOCAL_RUNTIME / "scripts"),
    str(SOURCE_REPOSITORY / "03_code" / "third_party" / "android_world"),
]

import androidworld_compat  # noqa: E402,F401
from android_world import registry  # noqa: E402
from android_world.env import android_world_controller, env_launcher  # noqa: E402
from raven_m.models.vllm_multi_image_client import VLLMMultiImageClient  # noqa: E402
from task_instances import instantiate_verified  # type: ignore  # noqa: E402
from raven_m.public_frameworks.mobileuse.controller import ARM_ID, MobileUseController  # noqa: E402
from raven_m.public_frameworks.mobileuse.mechanism_metrics import extract as extract_mechanism_metrics  # noqa: E402


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
BACKEND_ID = "qwen3_vl_32b_vllm_bf16_1xrtxpro6000_mobileuse_pf01_v1"
FROZEN_ORDER = [
    "H06", "H04", "H03", "H15", "H11", "H13", "H02", "H05", "H10",
    "H12", "H08", "H16", "H14", "H19", "H09", "H18", "H17", "H01", "H07",
]
FREEZE_FILES = [
    "implementation/configs/mobileuse_multiagent_qwen3_vl_32b_hard_seed20260806.yaml",
    "implementation/third_party/mobile_use/SOURCE_LOCK.json",
    "implementation/third_party/mobile_use/DEPENDENCY_LOCK.json",
    "implementation/src/raven_m/models/vllm_multi_image_client.py",
    "implementation/src/raven_m/public_frameworks/mobileuse/action_adapter.py",
    "implementation/src/raven_m/public_frameworks/mobileuse/controller.py",
    "implementation/src/raven_m/public_frameworks/mobileuse/logging.py",
    "implementation/src/raven_m/public_frameworks/mobileuse/mechanism_metrics.py",
    "implementation/src/raven_m/public_frameworks/mobileuse/prompt_adapter.py",
    "implementation/scripts/live_preflight_mobileuse.py",
    "implementation/scripts/preflight_mobileuse.py",
    "implementation/scripts/run_mobileuse_hard.py",
    "implementation/scripts/start_mobileuse_server.sh",
    "protocols/MOBILEUSE_QWEN3VL32B_HARD_SEED20260806_PREREG.json",
    "protocols/MOBILEUSE_QWEN3VL32B_HARD_SEED20260806_PREREG.md",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if hasattr(value, "value"):
        return json_safe(value.value)
    if hasattr(value, "__dict__"):
        return json_safe(vars(value))
    return repr(value)


def current_freeze() -> dict[str, str]:
    return {
        name: digest(REPOSITORY_ROOT / name)
        for name in FREEZE_FILES
    }


def load_scored_specs(manifest_path: Path) -> list[dict[str, Any]]:
    value = json.loads(manifest_path.read_text(encoding="utf-8"))
    if value.get("androidworld_commit") != "3e50888527ef9f29b9157ecd537e408008bb1c85":
        raise RuntimeError("AndroidWorld source-lock drift")
    candidates = [
        item for item in value["instances"] if int(item["task_seed"]) == 20260806
    ]
    by_id = {item["task_id"]: item for item in candidates}
    if set(by_id) != set(FROZEN_ORDER):
        raise RuntimeError("Hard first-seed manifest drift")
    return [by_id[task_id] for task_id in FROZEN_ORDER]


def model_client(url: str, timeout: float) -> VLLMMultiImageClient:
    return VLLMMultiImageClient(
        url,
        model_id=MODEL_ID,
        model_revision=MODEL_REVISION,
        backend_id=BACKEND_ID,
        temperature=0.7,
        top_p=0.8,
        top_k=20,
        presence_penalty=1.5,
        repetition_penalty=1.0,
        seed=3407,
        timeout_seconds=timeout,
    )


def run_episode(
    *, env: Any, task: Any, spec: dict[str, Any], client: VLLMMultiImageClient,
    suite_dir: Path, mode: str,
) -> dict[str, Any]:
    task_name = str(spec["task_class"])
    seed = int(spec["task_seed"])
    episode_id = f"{task_name}_{seed}_{uuid4().hex[:8]}"
    episode_dir = suite_dir / "episodes" / episode_id
    episode_dir.mkdir(parents=True, exist_ok=False)
    task_initialized = False
    result = None
    evaluator_reward = None
    error = None
    started = utc_now()
    try:
        env.reset(go_home=True)
        hide = getattr(env, "hide_automation_ui", None)
        if callable(hide):
            hide()
        task.initialize_task(env)
        task_initialized = True
        goal = str(task.goal)
        controller = MobileUseController(
            client,
            env=env,
            episode_id=episode_id,
            episode_dir=episode_dir,
            max_steps=int(spec["native_max_steps"]),
            max_tokens=32768,
        )
        result = controller.run(goal)
        evaluator_reward = float(task.is_successful(env))
        controller.log.write(
            "L5", "androidworld_evaluator_result", reward=evaluator_reward,
            visible_to_agent=False,
        )
        mechanism = extract_mechanism_metrics(
            result.log_path, task_name=task_name, reward=evaluator_reward
        )
        (episode_dir / "mechanism_metrics.json").write_text(
            json.dumps(mechanism, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        controller.log.write(
            "L4", "posthoc_mechanism_summary",
            agent_visible=False, metrics=mechanism,
        )
    except Exception as exc:
        error = {
            "type": type(exc).__name__, "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        if task_initialized:
            try:
                task.tear_down(env)
            except Exception as exc:
                error = error or {"type": type(exc).__name__, "message": str(exc), "phase": "tear_down"}
        try:
            env.reset(go_home=True)
        except Exception as exc:
            error = error or {"type": type(exc).__name__, "message": str(exc), "phase": "post_reset"}
    summary = {
        "schema": "raven_m.mobileuse.episode_summary.v1",
        "arm_id": ARM_ID,
        "mode": mode,
        "episode_id": episode_id,
        "task_id": spec.get("task_id"),
        "task_name": task_name,
        "seed": seed,
        "native_budget": int(spec["native_max_steps"]),
        "goal_hash": spec.get("goal_hash"),
        "task_params_hash": spec.get("task_params_hash"),
        "started_at": started,
        "finished_at": utc_now(),
        "evaluator_reward": evaluator_reward,
        "success": evaluator_reward == 1.0,
        "scientifically_valid": error is None,
        "error": error,
        "native_actions": result.native_actions if result else None,
        "operator_decisions": (
            result.episode_data.num_steps if result else None
        ),
        "controller_status": json_safe(result.episode_data.status) if result else None,
        "controller_message": result.episode_data.message if result else None,
        "answer": result.answer if result else None,
        "events_path": str(result.log_path) if result else str(episode_dir / "events.jsonl"),
    }
    (episode_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if error is not None:
        raise RuntimeError(f"Invalid episode {episode_id}: {error}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("smoke", "scored"), required=True)
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument("--request-timeout-seconds", type=float, default=3600.0)
    parser.add_argument(
        "--manifest", type=Path,
        default=SOURCE_REPOSITORY / "05_project" / "configs" / "task_manifests" / "androidworld_hard_v2_instances.json",
    )
    parser.add_argument(
        "--output-root", type=Path,
        default=REPOSITORY_ROOT / "runs" / "public_framework" / "mobileuse",
    )
    args = parser.parse_args()

    preflight = REPOSITORY_ROOT / "evidence" / "public_framework" / "mobileuse" / "PF01_ZERO_GENERATION_PREFLIGHT.json"
    replay = REPOSITORY_ROOT / "evidence" / "public_framework" / "mobileuse" / "PF01_BASELINE_FIRST_SEED_REPLAY_REFERENCE.json"
    if not preflight.is_file() or json.loads(preflight.read_text())["status"] != "pass":
        raise RuntimeError("Zero-generation preflight has not passed")
    if not replay.is_file() or json.loads(replay.read_text())["episode_count"] != 19:
        raise RuntimeError("Baseline first-seed replay has not passed")
    live_preflight = REPOSITORY_ROOT / "evidence" / "public_framework" / "mobileuse" / "PF01_LIVE_MULTI_IMAGE_PREFLIGHT.json"
    if not live_preflight.is_file():
        raise RuntimeError("Live one/two/three-image preflight has not run")
    live_report = json.loads(live_preflight.read_text(encoding="utf-8"))
    if live_report.get("status") != "pass" or live_report.get("image_counts") != [1, 2, 3]:
        raise RuntimeError("Live one/two/three-image preflight has not passed")
    freeze_path = REPOSITORY_ROOT / "evidence" / "public_framework" / "mobileuse" / "PF01_FREEZE_AFTER_SMOKE.json"
    if args.mode == "scored":
        if not freeze_path.is_file():
            raise RuntimeError("Authorized smoke has not produced a freeze manifest")
        frozen = json.loads(freeze_path.read_text(encoding="utf-8"))
        if frozen["file_sha256"] != current_freeze():
            raise RuntimeError("Source/config changed after smoke")

    client = model_client(args.url, args.request_timeout_seconds)
    health = client.health()
    env = env_launcher.load_and_setup_env(
        console_port=args.console_port,
        emulator_setup=False,
        freeze_datetime=True,
        adb_path=args.adb_path,
        grpc_port=args.grpc_port,
        a11y_method=android_world_controller.A11yMethod.UIAUTOMATOR,
    )
    registry_value = registry.TaskRegistry().get_registry(registry.TaskRegistry.ANDROID_WORLD_FAMILY)
    if args.mode == "smoke":
        task_name = "ContactsAddContact"
        if task_name not in registry_value:
            raise RuntimeError("Authorized smoke task missing")
        random.seed(20260805)
        np.random.seed(20260805)
        task_type = registry_value[task_name]
        task = task_type(task_type.generate_random_params())
        specs = [{
            "task_id": "SMOKE", "task_class": task_name,
            "task_seed": 20260805, "native_max_steps": 3,
        }]
        tasks = [task]
    else:
        specs = load_scored_specs(args.manifest)
        tasks = [instantiate_verified(registry_value, spec) for spec in specs]

    suite_id = f"pf01_{args.mode}_{datetime.now().strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}"
    suite_dir = args.output_root / suite_id
    suite_dir.mkdir(parents=True, exist_ok=False)
    if args.mode == "scored":
        shutil.copy2(args.manifest, suite_dir / "manifest.snapshot.json")
    summaries = []
    try:
        for spec, task in zip(specs, tasks):
            summaries.append(run_episode(
                env=env, task=task, spec=spec, client=client,
                suite_dir=suite_dir, mode=args.mode,
            ))
    finally:
        env.close()

    aggregate = {
        "schema": "raven_m.mobileuse.suite_summary.v1",
        "arm_id": ARM_ID,
        "suite_id": suite_id,
        "mode": args.mode,
        "model_health": health,
        "episode_count": len(summaries),
        "success_count": sum(int(item["success"]) for item in summaries),
        "total_reward": sum(float(item["evaluator_reward"]) for item in summaries),
        "scientifically_valid_count": sum(int(item["scientifically_valid"]) for item in summaries),
        "episodes": summaries,
    }
    (suite_dir / "aggregate.json").write_text(
        json.dumps(aggregate, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.mode == "smoke":
        events = Path(summaries[0]["events_path"]).read_text(encoding="utf-8")
        required = ('"role": "Operator"', '"role": "Reflector"', '"role": "Progressor"', '"event": "environment_action_complete"')
        missing = [token for token in required if token not in events]
        if missing:
            raise RuntimeError(f"Smoke did not exercise required path: {missing}")
        freeze = {
            "schema": "raven_m.mobileuse.freeze_after_smoke.v1",
            "smoke_suite": str(suite_dir),
            "smoke_aggregate_sha256": digest(suite_dir / "aggregate.json"),
            "file_sha256": current_freeze(),
        }
        freeze_path.write_text(
            json.dumps(freeze, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({"suite_dir": str(suite_dir), **aggregate}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
