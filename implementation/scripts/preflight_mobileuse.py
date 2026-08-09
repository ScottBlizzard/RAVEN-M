"""Zero-generation qualification for the frozen MobileUse PF01 arm."""

from __future__ import annotations

import argparse
import base64
from hashlib import sha256
from importlib import metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
VENDOR = PROJECT_ROOT / "third_party" / "mobile_use"
UPSTREAM = VENDOR / "upstream"
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(UPSTREAM))

from raven_m.models.vllm_multi_image_client import VLLMMultiImageClient  # noqa: E402
from raven_m.public_frameworks.mobileuse.action_adapter import MobileUseActionAdapter  # noqa: E402
from raven_m.public_frameworks.mobileuse.controller import EXPECTED_ROLES, MobileUseController  # noqa: E402


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def check_source_lock() -> dict[str, Any]:
    lock = json.loads((VENDOR / "SOURCE_LOCK.json").read_text(encoding="utf-8"))
    if lock["resolved_commit_sha"] != "babec07fd0e5faa7e7bcc7d3d0ee2320f6b83347":
        raise RuntimeError("MobileUse commit drift")
    if lock["resolved_tree_sha"] != "f431837762d69ddc26022d5c6d2e51ff3ca3690e":
        raise RuntimeError("MobileUse tree drift")
    if digest(VENDOR / "LICENSE") != lock["license_sha256"]:
        raise RuntimeError("MobileUse license hash drift")
    checked = []
    for group in ("selected_source_files", "selected_prompt_files"):
        for item in lock[group]:
            path = UPSTREAM / item["path"]
            actual = digest(path)
            if actual != item["sha256"]:
                raise RuntimeError(f"Locked source drift: {item['path']}")
            checked.append({"path": item["path"], "sha256": actual})
    return {
        "commit": lock["resolved_commit_sha"],
        "tree": lock["resolved_tree_sha"],
        "license": lock["license"],
        "checked_file_count": len(checked),
        "files": checked,
    }


def check_config() -> dict[str, Any]:
    config_path = PROJECT_ROOT / "configs" / "mobileuse_multiagent_qwen3_vl_32b_hard_seed20260806.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    expected = {
        "id": "Qwen/Qwen3-VL-32B-Instruct",
        "revision": "0cfaf48183f594c314753d30a4c4974bc75f3ccb",
        "vllm_version": "0.26.0",
        "dtype": "bfloat16",
        "tensor_parallel_size": 1,
        "gpu_memory_utilization": 0.92,
        "max_model_len": 65536,
        "max_new_tokens": 32768,
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 20,
        "presence_penalty": 1.5,
        "repetition_penalty": 1.0,
        "max_concurrency": 1,
    }
    for key, value in expected.items():
        if config["model"].get(key) != value:
            raise RuntimeError(f"Frozen model field drift: {key}")
    if config["model"]["limit_mm_per_prompt"] != {"image": 3}:
        raise RuntimeError("Multi-image transport drift")
    if tuple(config["roles"]["enabled"]) != EXPECTED_ROLES:
        raise RuntimeError("Enabled role config drift")
    if config["environment"]["coordinate_range"] != [0, 999]:
        raise RuntimeError("Coordinate convention drift")
    template = yaml.safe_load(
        (UPSTREAM / "benchmark" / "android_world" / "configs" / "mobileuse_template.yaml").read_text(encoding="utf-8")
    )
    template_roles = {
        "Operator": template["operator"]["enabled"],
        "AnswerAgent": template["answer_agent"]["enabled"],
        "Reflector": template["reflector"]["enabled"],
        "TrajectoryReflector": template["trajectory_reflector"]["enabled"],
        "GlobalReflector": template["global_reflector"]["enabled"],
        "Progressor": template["progressor"]["enabled"],
    }
    if not all(template_roles.values()):
        raise RuntimeError("Locked official template role disabled")
    return {"path": str(config_path), "sha256": digest(config_path), "model": expected}


def check_image_transport() -> dict[str, Any]:
    raws = [b"operator", b"before", b"after"]
    content = []
    for raw in raws:
        content.append({
            "type": "image_url",
            "image_url": {"url": "data:image/png;base64," + base64.b64encode(raw).decode("ascii")},
        })
    hashes_by_count = {}
    for count in (1, 2, 3):
        _, hashes = VLLMMultiImageClient._validate_messages(
            [{"role": "user", "content": content[:count]}],
            expected_images=count,
        )
        expected = tuple(sha256(raw).hexdigest() for raw in raws[:count])
        if hashes != expected:
            raise RuntimeError("Image order/hash drift")
        hashes_by_count[str(count)] = list(hashes)
    return {"one_two_three_image_serialization": "pass", "hashes": hashes_by_count}


class NoGenerationClient:
    model_id = "Qwen/Qwen3-VL-32B-Instruct"
    model_revision = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
    backend_id = "preflight_no_generation"
    base_url = "http://127.0.0.1:18000"

    def generate_messages(self, **kwargs: Any) -> Any:
        raise AssertionError("Preflight must not perform generation")


def check_controller() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="pf01_preflight_") as directory:
        controller = MobileUseController(
            NoGenerationClient(), env=object(), episode_id="preflight_no_generation",
            episode_dir=Path(directory), max_steps=1,
        )
        roles = {
            "Operator": controller.agent.operator,
            "Reflector": controller.agent.reflector,
            "Progressor": controller.agent.progressor,
            "TrajectoryReflector": controller.agent.trajectory_reflector,
            "AnswerAgent": controller.agent.answer_agent,
            "GlobalReflector": controller.agent.global_reflector,
        }
        if tuple(name for name, value in roles.items() if value is not None) != EXPECTED_ROLES:
            raise RuntimeError("Controller role reachability drift")
        if controller.agent.planner is not None or controller.agent.note_taker is not None:
            raise RuntimeError("Prohibited role reachable")
        if controller.agent.vlm is not None:
            raise RuntimeError("Unselected root VLM remains reachable")
        if set(controller.agent.subagent_map) != {"Operator", "AnswerAgent"}:
            raise RuntimeError("Alternative operator class remains reachable")
        if controller.agent.operator.include_a11y_tree:
            raise RuntimeError("Accessibility tree exposed to Operator")
        changes = json.loads((Path(directory) / "prompt_changes.json").read_text(encoding="utf-8"))
        allowed_labels = {
            "ACTION_NAME", "ACTION_SCHEMA", "COORDINATE_RANGE",
            "UNSUPPORTED_TOOL_REMOVAL", "ENDPOINT_IDENTIFIER",
        }
        if any(not item["labels"] or not set(item["labels"]) <= allowed_labels for item in changes):
            raise RuntimeError("Unclassified prompt change")
        active_prompt = controller.agent.operator.prompt.system_prompt + controller.agent.operator.prompt.init_tips
        for token in ('"open"', "long_press", "clear_text", "take_note", '"key"', '"wait"'):
            if token in active_prompt:
                raise RuntimeError(f"Prohibited active prompt token: {token}")
        return {
            "roles": list(roles),
            "prohibited_roles_reachable": False,
            "root_vlm_reachable": False,
            "accessibility_visible_to_model": False,
            "prompt_change_count": len(changes),
        }


def check_actions() -> dict[str, Any]:
    adapter = MobileUseActionAdapter()
    adapter.map({"name": "click", "parameters": {"coordinate": [0, 999]}})
    adapter.map({"name": "swipe", "parameters": {"coordinate": [999, 0], "coordinate2": [0, 999]}})
    adapter.map({"name": "type", "parameters": {"text": "中文 Unicode"}})
    adapter.map({"name": "system_button", "parameters": {"button": "Back"}})
    adapter.map({"name": "system_button", "parameters": {"button": "Home"}})
    adapter.map({"name": "answer", "parameters": {"text": "42"}})
    adapter.map({"name": "terminate", "parameters": {"status": "success"}})
    rejected = []
    for name in ("open", "long_press", "wait", "clear_text", "take_note", "key"):
        try:
            adapter.map({"name": name, "parameters": {}})
        except ValueError:
            rejected.append(name)
        else:
            raise RuntimeError(f"Prohibited action accepted: {name}")
    return {"boundaries": "pass", "unicode": "pass", "rejected": rejected}


def dependency_inventory() -> dict[str, Any]:
    distributions = [
        "adbutils", "jsonlines", "openai", "pyregister", "scikit-image",
        "PyYAML", "pydantic", "Pillow", "numpy", "opencv-python", "requests",
    ]
    items = []
    for name in distributions:
        dist = metadata.distribution(name)
        items.append({
            "name": dist.metadata.get("Name", name),
            "version": dist.version,
            "license": dist.metadata.get("License") or dist.metadata.get("License-Expression") or "metadata-not-declared",
        })
    return {"python": sys.version, "packages": sorted(items, key=lambda item: item["name"].lower())}


def run_tests() -> dict[str, Any]:
    test_dir = PROJECT_ROOT / "tests" / "public_frameworks" / "mobileuse"
    python_path = [str(PROJECT_ROOT / "src"), str(UPSTREAM)]
    if os.environ.get("PYTHONPATH"):
        python_path.append(os.environ["PYTHONPATH"])
    child_env = dict(os.environ)
    child_env["PYTHONPATH"] = os.pathsep.join(python_path)
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_dir), "-q"],
        cwd=PROJECT_ROOT,
        env=child_env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(completed.stdout + "\n" + completed.stderr)
    return {"status": "pass", "stdout": completed.stdout.strip()}


def check_runner_entrypoint() -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "run_mobileuse_hard.py"), "--help"],
        cwd=REPOSITORY_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(completed.stdout + "\n" + completed.stderr)
    if "--mode {smoke,scored}" not in completed.stdout:
        raise RuntimeError("MobileUse runner help did not expose the frozen modes")
    return {"status": "pass", "generation_calls": 0, "emulator_mutations": 0}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path,
        default=REPOSITORY_ROOT / "evidence" / "public_framework" / "mobileuse" / "PF01_ZERO_GENERATION_PREFLIGHT.json",
    )
    args = parser.parse_args()
    report = {
        "schema": "raven_m.mobileuse.preflight.v1",
        "generation_calls": 0,
        "emulator_mutations": 0,
        "source_lock": check_source_lock(),
        "config": check_config(),
        "multi_image": check_image_transport(),
        "controller": check_controller(),
        "actions": check_actions(),
        "dependencies": dependency_inventory(),
        "tests": run_tests(),
        "runner_entrypoint": check_runner_entrypoint(),
        "status": "pass",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    dependency_path = VENDOR / "DEPENDENCY_LOCK.json"
    dependency_path.write_text(
        json.dumps(report["dependencies"], indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "pass", "output": str(args.output),
        "generation_calls": 0, "emulator_mutations": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
