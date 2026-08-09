"""Run the frozen C0 native-MobileUse control on all 19 Hard classes."""

from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
import math
from pathlib import Path
import shutil
import subprocess
import traceback
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import run_mobileuse_hard as pf01
from raven_m.models.vllm_multi_image_client import VLLMMultiImageClient
from raven_m.public_frameworks.mobileuse.c0_controller import (
    ARM_ID, C0NativeMobileUseController,
)
from raven_m.public_frameworks.mobileuse.c0_reset import (
    initialize_task_with_native_resets, tear_down_without_recents_hang,
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
LIVE_PREFLIGHT_PATH = pf01.REPOSITORY_ROOT / "evidence/public_framework/mobileuse_c0/C0_LIVE_EMULATOR_PREFLIGHT.json"
SNAPSHOT_PREFLIGHT_PATH = pf01.REPOSITORY_ROOT / "evidence/public_framework/mobileuse_c0/C0_SNAPSHOT_PREFLIGHT.json"
FREEZE_FILES = [
    CONFIG_PATH,
    PREREG_PATH,
    Path(__file__).resolve(),
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/public_frameworks/mobileuse/c0_action_adapter.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/public_frameworks/mobileuse/c0_controller.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/public_frameworks/mobileuse/c0_reset.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/public_frameworks/mobileuse/action_adapter.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/public_frameworks/mobileuse/prompt_adapter.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/public_frameworks/mobileuse/controller.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/public_frameworks/mobileuse/logging.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/public_frameworks/mobileuse/mechanism_metrics.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/env/androidworld_adapter.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/models/vllm_multi_image_client.py",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    pf01.REPOSITORY_ROOT / "implementation/scripts/preflight_mobileuse_c0.py",
    pf01.REPOSITORY_ROOT / "implementation/scripts/run_mobileuse_hard.py",
    pf01.REPOSITORY_ROOT / "implementation/scripts/live_preflight_mobileuse_c0.py",
    pf01.REPOSITORY_ROOT / "implementation/scripts/prepare_mobileuse_c0_snapshots.py",
    pf01.REPOSITORY_ROOT / "implementation/scripts/android_c0_set_chrome_prefs.sh",
    pf01.REPOSITORY_ROOT / "implementation/scripts/start_mobileuse_c0_server.sh",
    pf01.REPOSITORY_ROOT / "implementation/configs/c0_qwen3_vl_32b_model.sha256",
    pf01.REPOSITORY_ROOT / "implementation/src/raven_m/models/transformers_client.py",
    pf01.REPOSITORY_ROOT / "implementation/third_party/mobile_use/SOURCE_LOCK.json",
    pf01.REPOSITORY_ROOT / "implementation/third_party/mobile_use/DEPENDENCY_LOCK.json",
    pf01.REPOSITORY_ROOT / "implementation/third_party/adbkeyboard/keyboardservice-debug-v2.4.apk",
    pf01.REPOSITORY_ROOT / "implementation/third_party/mobile_use/upstream/mobile_use/agents/multi_agent.py",
    pf01.REPOSITORY_ROOT / "implementation/third_party/mobile_use/upstream/mobile_use/agents/sub_agent.py",
    pf01.REPOSITORY_ROOT / "implementation/third_party/mobile_use/upstream/mobile_use/environment/mobile_environ.py",
    pf01.REPOSITORY_ROOT / "implementation/third_party/mobile_use/upstream/mobile_use/schema/config.py",
    pf01.REPOSITORY_ROOT / "implementation/third_party/mobile_use/upstream/mobile_use/schema/schema.py",
    pf01.REPOSITORY_ROOT / "implementation/third_party/mobile_use/upstream/mobile_use/default_prompts/prompt_type.py",
    pf01.REPOSITORY_ROOT / "implementation/third_party/mobile_use/upstream/mobile_use/default_prompts/operator.yaml",
    pf01.REPOSITORY_ROOT / "implementation/third_party/mobile_use/upstream/mobile_use/default_prompts/answer_agent.yaml",
    pf01.REPOSITORY_ROOT / "implementation/third_party/mobile_use/upstream/mobile_use/default_prompts/reflector.yaml",
    pf01.REPOSITORY_ROOT / "implementation/third_party/mobile_use/upstream/mobile_use/default_prompts/progressor.yaml",
    pf01.REPOSITORY_ROOT / "implementation/third_party/mobile_use/upstream/mobile_use/default_prompts/trajectory_reflector.yaml",
    pf01.REPOSITORY_ROOT / "implementation/third_party/mobile_use/upstream/mobile_use/default_prompts/global_reflector.yaml",
    MASTER_MANIFEST,
]
EXTERNAL_ANDROIDWORLD_ROOT = (
    pf01.SOURCE_REPOSITORY / "03_code/third_party/android_world/android_world"
)
EXTERNAL_COMPAT = pf01.LOCAL_RUNTIME / "scripts/androidworld_compat.py"


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def current_freeze() -> dict[str, str]:
    value = {
        str(path.relative_to(pf01.REPOSITORY_ROOT)).replace("\\", "/"): digest(path)
        for path in FREEZE_FILES
    }
    hasher = sha256()
    external_files = sorted({
        path
        for pattern in ("*.py", "*.json", "*.proto", "*.textproto")
        for path in EXTERNAL_ANDROIDWORLD_ROOT.rglob(pattern)
        if "__pycache__" not in path.parts
    })
    for path in external_files:
        relative = path.relative_to(EXTERNAL_ANDROIDWORLD_ROOT).as_posix()
        hasher.update(relative.encode("utf-8") + b"\0")
        hasher.update(sha256(path.read_bytes()).digest())
    value["external:androidworld_runtime_tree"] = hasher.hexdigest()
    value["external:androidworld_compat.py"] = digest(EXTERNAL_COMPAT)
    value["external:androidworld_runtime_file_count"] = str(len(external_files))
    source_lock_path = pf01.REPOSITORY_ROOT / "implementation/third_party/mobile_use/SOURCE_LOCK.json"
    source_lock = json.loads(source_lock_path.read_text(encoding="utf-8"))
    vendor_root = pf01.REPOSITORY_ROOT / "implementation/third_party/mobile_use/upstream"
    for entry in source_lock.get("selected_source_files", []) + source_lock.get("selected_prompt_files", []):
        source_path = vendor_root / entry["path"]
        value[f"locked_upstream:{entry['path']}"] = digest(source_path)
    mobileuse_runtime_root = vendor_root / "mobile_use"
    mobileuse_runtime_files = sorted({
        path
        for pattern in ("*.py", "*.yaml", "*.json")
        for path in mobileuse_runtime_root.rglob(pattern)
        if "__pycache__" not in path.parts
    })
    runtime_hasher = sha256()
    for path in mobileuse_runtime_files:
        runtime_hasher.update(path.relative_to(mobileuse_runtime_root).as_posix().encode("utf-8") + b"\0")
        runtime_hasher.update(sha256(path.read_bytes()).digest())
    value["locked_upstream:mobile_use_runtime_tree"] = runtime_hasher.hexdigest()
    value["locked_upstream:mobile_use_runtime_file_count"] = str(len(mobileuse_runtime_files))
    return value


def device_identity(adb_path: str, console_port: int) -> dict[str, Any]:
    serial = f"emulator-{console_port}"

    def adb(*args: str) -> str:
        return subprocess.run(
            [adb_path, "-s", serial, *args], check=True, capture_output=True,
            text=True, timeout=60,
        ).stdout.strip()

    packages = {
        "audio recorder": "com.dimowner.audiorecorder",
        "camera": "com.android.camera2",
        "tasks": "org.tasks",
        "markor": "net.gsantner.markor",
        "simple calendar pro": "com.simplemobiletools.calendar.pro",
        "chrome": "com.android.chrome",
        "broccoli app": "com.flauschcode.broccoli",
        "open tracks sports tracker": "de.dennisguse.opentracks",
        "osmand": "net.osmand",
        "pro expense": "com.arduia.expense",
        "retro music": "code.name.monkey.retromusic",
        "simple gallery pro": "com.simplemobiletools.gallery.pro",
        "simple sms messenger": "com.simplemobiletools.smsmessenger",
        "vlc": "org.videolan.vlc",
        "adb keyboard": "com.android.adbkeyboard",
    }
    versions = {}
    for name, package in packages.items():
        dump = adb("shell", "dumpsys", "package", package)
        version_lines = [
            line.strip() for line in dump.splitlines()
            if "versionCode=" in line or "versionName=" in line
        ]
        if not version_lines:
            raise RuntimeError(f"Required C0 device package is missing: {name} ({package})")
        versions[name] = {"package": package, "version_lines": version_lines[:2]}
    return {
        "serial": serial,
        "build_fingerprint": adb("shell", "getprop", "ro.build.fingerprint"),
        "packages": versions,
    }


def validate_launch_manifest(path: Path, url: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "arm": ARM_ID,
        "environment": "/root/autodl-tmp/envs/qwen_vllm",
        "model_source": "/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope",
        "model_manifest_sha256": digest(
            pf01.REPOSITORY_ROOT / "implementation/configs/c0_qwen3_vl_32b_model.sha256"
        ),
        "served_model": MODEL_ID,
        "tensor_parallel_size": 1,
        "dtype": "bfloat16",
        "gpu_memory_utilization": 0.92,
        "max_model_len": 65536,
        "max_num_seqs": 1,
        "limit_images_per_prompt": 3,
        "vllm": "0.26.0",
        "torch": "2.11.0",
        "transformers": "5.14.1",
    }
    drift = {key: (value.get(key), expected_value) for key, expected_value in expected.items() if value.get(key) != expected_value}
    url_port = urlparse(url).port or 80
    if int(value.get("port", -1)) != int(url_port):
        drift["port"] = (value.get("port"), url_port)
    for field in ("gpu_name", "driver_version", "cuda_version"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            drift[field] = (value.get(field), "non-empty runtime value")
    if drift:
        raise RuntimeError(f"C0 server launch-manifest drift: {drift}")
    return value


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


def event_metrics(path: Path) -> dict[str, Any]:
    """Summarize model cost and action-chain integrity from the audit log."""
    metrics: dict[str, Any] = {
        "model_requests": 0,
        "model_responses": 0,
        "requests_by_role": {},
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "model_latency_seconds": 0.0,
        "environment_actions_started": 0,
        "environment_actions_completed": 0,
        "environment_action_start_indexes": [],
        "environment_action_complete_indexes": [],
    }
    if not path.is_file():
        return metrics
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        event_type = event.get("event")
        if event_type == "model_request":
            metrics["model_requests"] += 1
            role = str(event.get("role", "unknown"))
            roles = metrics["requests_by_role"]
            roles[role] = int(roles.get(role, 0)) + 1
        elif event_type == "model_response":
            metrics["model_responses"] += 1
            usage = event.get("usage") or {}
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                metrics[key] += int(usage.get(key) or 0)
            meta = event.get("raven_meta") or {}
            metrics["model_latency_seconds"] += float(meta.get("latency_seconds") or 0.0)
        elif event_type == "environment_action_start":
            metrics["environment_actions_started"] += 1
            metrics["environment_action_start_indexes"].append(
                event.get("native_action_index")
            )
        elif event_type == "environment_action_complete":
            metrics["environment_actions_completed"] += 1
            metrics["environment_action_complete_indexes"].append(
                event.get("native_action_index")
            )
    metrics["model_latency_seconds"] = round(metrics["model_latency_seconds"], 3)
    metrics["action_chain_balanced"] = (
        metrics["environment_action_start_indexes"]
        == metrics["environment_action_complete_indexes"]
    )
    metrics["model_call_chain_balanced"] = (
        metrics["model_requests"] == metrics["model_responses"]
    )
    return metrics


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
        # App setup may leave Markor/Chrome/onboarding in the foreground. The
        # official AndroidWorld episode harness resets the agent to Home after
        # task initialization when start_on_home_screen is true.
        go_home = bool(getattr(task, "start_on_home_screen", True))
        env.reset(go_home=go_home)
        automation_hidden = False
        if callable(hide):
            hide()
            automation_hidden = True
        reset_audit["post_initialize_go_home"] = go_home
        reset_audit["post_initialize_automation_ui_hidden"] = automation_hidden
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
                tear_down_without_recents_hang(task, env)
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
    events_path = result.log_path if result else episode_dir / "events.jsonl"
    summary["event_metrics"] = event_metrics(events_path)
    if error is None and (
        not summary["event_metrics"]["action_chain_balanced"]
        or not summary["event_metrics"]["model_call_chain_balanced"]
    ):
        summary["scientifically_valid"] = False
        summary["error"] = {
            "type": "EnvironmentActionChainError",
            "message": "A model call or environment action lacks a matching completion",
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
        "model_requests": sum(item["event_metrics"]["model_requests"] for item in summaries),
        "model_responses": sum(item["event_metrics"]["model_responses"] for item in summaries),
        "requests_by_role": {
            role: sum(
                item["event_metrics"]["requests_by_role"].get(role, 0)
                for item in summaries
            )
            for role in (
                "Operator", "Reflector", "Progressor", "TrajectoryReflector",
                "AnswerAgent", "GlobalReflector",
            )
        },
        "prompt_tokens": sum(item["event_metrics"]["prompt_tokens"] for item in summaries),
        "completion_tokens": sum(item["event_metrics"]["completion_tokens"] for item in summaries),
        "total_tokens": sum(item["event_metrics"]["total_tokens"] for item in summaries),
        "model_latency_seconds": round(sum(
            item["event_metrics"]["model_latency_seconds"] for item in summaries
        ), 3),
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
    parser.add_argument("--server-launch-manifest", type=Path, required=True)
    parser.add_argument("--request-timeout-seconds", type=float, default=3600.0)
    parser.add_argument(
        "--output-root", type=Path,
        default=pf01.REPOSITORY_ROOT / "runs/public_framework/mobileuse_c0",
    )
    args = parser.parse_args()

    if not PREFLIGHT_PATH.is_file():
        raise RuntimeError("C0 zero-generation preflight is missing")
    preflight = json.loads(PREFLIGHT_PATH.read_text(encoding="utf-8"))
    if (
        preflight.get("schema") != "raven_m.c0.zero_generation_preflight.v1"
        or preflight.get("arm_id") != ARM_ID
        or preflight.get("status") != "pass"
        or preflight.get("generation_calls") != 0
        or preflight.get("errors") != []
        or (preflight.get("tests") or {}).get("returncode") != 0
    ):
        raise RuntimeError("C0 zero-generation preflight did not pass")
    if preflight.get("file_sha256") != current_freeze():
        raise RuntimeError("C0 source/config drift after offline freeze")
    if not LIVE_PREFLIGHT_PATH.is_file():
        raise RuntimeError("C0 live-emulator preflight is missing")
    live_preflight = json.loads(LIVE_PREFLIGHT_PATH.read_text(encoding="utf-8"))
    required_live_checks = {
        "scored_relevant_app_resets", "markor_last_used_extension_is_clean",
        "open_app_name", "type_without_enter", "long_press_and_wait",
        "clear_text", "enter", "back", "swipe", "key_and_menu", "home",
    }
    live_checks = live_preflight.get("checks") or {}
    if (
        live_preflight.get("schema") != "raven_m.c0.live_emulator_preflight.v1"
        or live_preflight.get("status") != "pass"
        or live_preflight.get("generation_calls") != 0
        or live_preflight.get("errors") != []
        or not required_live_checks.issubset(live_checks)
        or any(not bool(live_checks[name].get("pass")) for name in required_live_checks)
    ):
        raise RuntimeError("C0 live-emulator preflight did not pass")
    if live_preflight.get("source_freeze") != current_freeze():
        raise RuntimeError("C0 source/config drift after live-emulator qualification")
    if not SNAPSHOT_PREFLIGHT_PATH.is_file():
        raise RuntimeError("C0 scored-app snapshot preflight is missing")
    snapshot_preflight = json.loads(
        SNAPSHOT_PREFLIGHT_PATH.read_text(encoding="utf-8")
    )
    if (
        snapshot_preflight.get("schema") != "raven_m.c0.snapshot_preflight.v1"
        or snapshot_preflight.get("status") != "pass"
        or snapshot_preflight.get("generation_calls") != 0
        or snapshot_preflight.get("errors") != []
        or len(snapshot_preflight.get("apps") or []) != 11
        or any(not bool(item.get("pass")) for item in snapshot_preflight.get("apps") or [])
        or snapshot_preflight.get("source_freeze") != current_freeze()
    ):
        raise RuntimeError("C0 scored-app snapshot preflight did not pass")
    current_device = device_identity(args.adb_path, args.console_port)
    if live_preflight.get("device_identity") != current_device:
        raise RuntimeError("C0 emulator/APK identity drift after live qualification")
    if snapshot_preflight.get("device_identity") != current_device:
        raise RuntimeError("C0 emulator/APK identity drift after snapshot qualification")
    launch_manifest = validate_launch_manifest(args.server_launch_manifest, args.url)

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
    shutil.copy2(args.server_launch_manifest, suite_dir / "server_launch_manifest.snapshot.json")
    shutil.copy2(LIVE_PREFLIGHT_PATH, suite_dir / "live_preflight.snapshot.json")
    shutil.copy2(SNAPSHOT_PREFLIGHT_PATH, suite_dir / "snapshot_preflight.snapshot.json")
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
