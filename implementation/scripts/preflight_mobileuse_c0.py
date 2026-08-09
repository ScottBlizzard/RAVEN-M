"""Zero-generation qualification and source freeze for C0."""

from __future__ import annotations

import ast
from datetime import datetime, timezone
import importlib.metadata
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
SOURCE_REPOSITORY = REPOSITORY_ROOT.parent / "RAVEN-M-Research"
sys.path[:0] = [
    str(PROJECT_ROOT / "src"), str(PROJECT_ROOT / "scripts"),
    str(PROJECT_ROOT / "third_party/mobile_use/upstream"),
    str(SOURCE_REPOSITORY / "06_local_runtime/scripts"),
    str(SOURCE_REPOSITORY / "03_code/third_party/android_world"),
]

import androidworld_compat  # noqa: E402,F401
import run_mobileuse_c0 as c0  # noqa: E402
from raven_m.public_frameworks.mobileuse.c0_action_adapter import (  # noqa: E402
    C0NativeActionAdapter, NATIVE_ACTIONS,
)
from raven_m.public_frameworks.mobileuse.c0_controller import (  # noqa: E402
    C0NativeMobileUseController,
)


OUTPUT = REPOSITORY_ROOT / "evidence/public_framework/mobileuse_c0/C0_ZERO_GENERATION_PREFLIGHT.json"


class _Client:
    model_id = c0.MODEL_ID
    model_revision = c0.MODEL_REVISION
    base_url = "http://127.0.0.1:9"

    def generate_messages(self, **kwargs):  # pragma: no cover
        raise RuntimeError("Zero-generation preflight must never call a model")


def main() -> None:
    errors: list[str] = []
    config = yaml.safe_load(c0.CONFIG_PATH.read_text(encoding="utf-8"))
    prereg = c0.PREREG_PATH.read_text(encoding="utf-8")
    if config.get("arm_id") != c0.ARM_ID:
        errors.append("arm_id_drift")
    if config.get("benchmark", {}).get("task_seed") != c0.TASK_SEED:
        errors.append("task_seed_drift")
    if config.get("benchmark", {}).get("task_order") != c0.TASK_ORDER:
        errors.append("task_order_drift")
    if config.get("benchmark", {}).get("budget_multiplier") != c0.BUDGET_MULTIPLIER:
        errors.append("budget_multiplier_drift")
    if config.get("memory_boundary", {}).get("new_raven_m_memory") is not False:
        errors.append("c0_must_not_add_raven_m_memory")
    expected_model = {
        "id": c0.MODEL_ID,
        "revision": c0.MODEL_REVISION,
        "dtype": "bfloat16",
        "tensor_parallel_size": 1,
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 20,
        "presence_penalty": 1.5,
        "repetition_penalty": 1.0,
        "generation_seed": 3407,
    }
    if config.get("model") != expected_model:
        errors.append("model_or_sampling_config_drift")
    if config.get("benchmark", {}).get("androidworld_commit") != "3e50888527ef9f29b9157ecd537e408008bb1c85":
        errors.append("androidworld_commit_config_drift")
    expected_roles = [
        "Operator", "Reflector", "Progressor", "TrajectoryReflector",
        "AnswerAgent", "GlobalReflector",
    ]
    if config.get("mobileuse", {}).get("roles") != expected_roles:
        errors.append("six_role_config_drift")
    expected_reset_apps = [
        "audio recorder", "camera", "tasks", "markor",
        "simple calendar pro", "chrome",
    ]
    if config.get("state_isolation", {}).get("reset_apps") != expected_reset_apps:
        errors.append("six_app_reset_config_drift")
    if "C1 must reuse this order" not in prereg:
        errors.append("paired_c1_order_not_frozen")

    specs = c0.load_specs()
    if len(specs) != 19 or [item["task_id"] for item in specs] != c0.TASK_ORDER:
        errors.append("nineteen_instance_freeze_failed")
    if any(int(item["task_seed"]) != c0.TASK_SEED for item in specs):
        errors.append("instance_seed_drift")
    if any(
        int(item["native_max_steps"])
        != int(math.ceil(c0.BUDGET_MULTIPLIER * item["base_native_max_steps"]))
        for item in specs
    ):
        errors.append("budget_scaling_failed")

    source_lock = json.loads(
        (PROJECT_ROOT / "third_party/mobile_use/SOURCE_LOCK.json").read_text(encoding="utf-8")
    )
    if "babec07fd0e5faa7e7bcc7d3d0ee2320f6b83347" not in json.dumps(source_lock):
        errors.append("mobileuse_source_lock_drift")
    locked_entries = (
        source_lock.get("selected_source_files", [])
        + source_lock.get("selected_prompt_files", [])
    )
    vendor_root = PROJECT_ROOT / "third_party/mobile_use/upstream"
    for entry in locked_entries:
        path = vendor_root / entry["path"]
        if not path.is_file():
            errors.append(f"locked_upstream_missing:{entry['path']}")
        elif c0.digest(path) != entry["sha256"]:
            errors.append(f"locked_upstream_hash_drift:{entry['path']}")
    dependency_lock = json.loads(
        (PROJECT_ROOT / "third_party/mobile_use/DEPENDENCY_LOCK.json").read_text(
            encoding="utf-8"
        )
    )
    if sys.version != dependency_lock.get("python"):
        errors.append("python_runtime_dependency_drift")
    for package in dependency_lock.get("packages", []):
        try:
            actual_version = importlib.metadata.version(package["name"])
        except importlib.metadata.PackageNotFoundError:
            errors.append(f"dependency_missing:{package['name']}")
            continue
        if actual_version != package["version"]:
            errors.append(
                f"dependency_version_drift:{package['name']}:{actual_version}"
            )
    reset_source = (
        SOURCE_REPOSITORY
        / "03_code/third_party/android_world/android_world/task_evals/utils/user_data_generation.py"
    ).read_text(encoding="utf-8")
    if '"find"' not in reset_source or '"-delete"' not in reset_source:
        errors.append("internal_storage_clear_is_not_effective")

    for path in c0.FREEZE_FILES:
        if not path.is_file():
            errors.append(f"missing:{path}")
            continue
        if path.suffix == ".py":
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as exc:
                errors.append(f"syntax:{path.name}:{exc}")

    adapter = C0NativeActionAdapter()
    expected = {
        "open", "click", "long_press", "type", "key", "swipe",
        "press_home", "press_back", "wait", "answer", "system_button",
        "clear_text", "take_note", "terminate",
    }
    if NATIVE_ACTIONS != expected:
        errors.append("native_action_space_drift")
    try:
        adapter.map(
            {"name": "long_press", "parameters": {"coordinate": [50, 25], "time": 1}},
            screen_width=100, screen_height=50,
        )
        adapter.map(
            {"name": "clear_text", "parameters": {}},
            screen_width=100, screen_height=50,
        )
    except Exception as exc:
        errors.append(f"native_action_fixture:{exc}")

    # Construction-only controller audit: no step(), health(), or model call.
    try:
        with tempfile.TemporaryDirectory(prefix="raven_c0_preflight_") as temp:
            controller = C0NativeMobileUseController(
                _Client(), env=object(), episode_id="ZERO_GENERATION",
                episode_dir=Path(temp), max_steps=3, max_tokens=64,
            )
            role_names = (
                "operator", "reflector", "progressor", "trajectory_reflector",
                "answer_agent", "global_reflector",
            )
            if any(getattr(controller.agent, role, None) is None for role in role_names):
                errors.append("six_role_construction_failed")
            prompt = controller.agent.operator.prompt.system_prompt
            for token in ("long_press", "clear_text", "open", "take_note", "wait"):
                if token not in prompt:
                    errors.append(f"native_prompt_missing:{token}")
            if controller.agent.reflect_on_demand is not False:
                errors.append("reflect_on_demand_drift")
            if controller.agent.planner is not None or controller.agent.note_taker is not None:
                errors.append("released_disabled_roles_drift")
            if controller.agent.max_action_retry != 3:
                errors.append("max_action_retry_drift")
            if controller.agent.enable_pre_reflection is not True:
                errors.append("pre_reflection_drift")
            trajectory_expected = {
                "evoke_every_steps": 5, "cold_steps": 3,
                "detect_error": True, "num_histories": 5,
                "num_latest_screenshots": 0, "max_repeat_action": 3,
                "max_repeat_action_series": 2, "max_repeat_screen": 3,
                "max_fail_count": 3,
            }
            for key, expected_value in trajectory_expected.items():
                if getattr(controller.agent.trajectory_reflector, key, None) != expected_value:
                    errors.append(f"trajectory_schedule_drift:{key}")
            if controller.agent.global_reflector.num_latest_screenshots != 3:
                errors.append("global_reflector_screenshot_schedule_drift")

            from mobile_use.default_prompts.prompt_type import load_prompt
            prompt_map = {
                "operator": "operator.yaml",
                "reflector": "reflector.yaml",
                "progressor": "progressor.yaml",
                "trajectory_reflector": "trajectory_reflector.yaml",
                "answer_agent": "answer_agent.yaml",
                "global_reflector": "global_reflector.yaml",
            }
            runtime_prompt_hashes = {}
            for role, filename in prompt_map.items():
                runtime_prompt = getattr(controller.agent, role).prompt
                released_prompt = load_prompt(role, filename)
                def stable_prompt(value):
                    return {
                        key: item for key, item in vars(value).items()
                        if key != "parse_response" and not callable(item)
                    }
                runtime_value = stable_prompt(runtime_prompt)
                released_value = stable_prompt(released_prompt)
                runtime_prompt_hashes[role] = c0.digest(
                    PROJECT_ROOT / "third_party/mobile_use/upstream/mobile_use/default_prompts" / filename
                )
                if runtime_value != released_value:
                    errors.append(f"runtime_prompt_drift:{role}")
    except Exception as exc:
        errors.append(f"controller_construction:{type(exc).__name__}:{exc}")

    env = dict(os.environ)
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"], cwd=PROJECT_ROOT,
        env=env, text=True, capture_output=True, timeout=300,
    )
    if completed.returncode != 0:
        errors.append("offline_tests_failed")

    report = {
        "schema": "raven_m.c0.zero_generation_preflight.v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "arm_id": c0.ARM_ID,
        "status": "pass" if not errors else "fail",
        "generation_calls": 0,
        "errors": errors,
        "task_order": c0.TASK_ORDER,
        "task_seed": c0.TASK_SEED,
        "task_count": len(specs),
        "budget_multiplier": c0.BUDGET_MULTIPLIER,
        "memory_intervention": False,
        "source_audit": {
            "mobileuse_commit": "babec07fd0e5faa7e7bcc7d3d0ee2320f6b83347",
            "androidworld_task_evaluator_commit": "3e50888527ef9f29b9157ecd537e408008bb1c85",
            "madeagents_reset_reference": "ea208c7",
            "madeagents_internal_storage_fix": "9a207d1a378bacbef0dbf3b81b79c63369e11f7e",
            "external_androidworld_runtime_is_content_hashed": True,
            "runtime_prompt_file_sha256": locals().get("runtime_prompt_hashes", {}),
        },
        "tests": {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        },
        "file_sha256": c0.current_freeze(),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
