"""Zero-generation-call implementation/runtime and frozen-study preflight for v0.2."""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import random
import subprocess
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
from raven_m.eest_ac.controller_v0_2 import ONLINE_ARMS_V02, _json_safe  # noqa: E402
from raven_m.eest_ac.task_roles import TaskRoleParser, verify_exact_spans  # noqa: E402
from raven_m.models.transformers_client import TransformersClient  # noqa: E402


EXPECTED_LEGACY_WIP = {
    "05_project/src/raven_m/controller/episode_controller.py": "fc0e82e0fde90119365d4f685f080eb4519bf2f602e4bda58de5d4809a40fe33",
    "05_project/src/raven_m/controller/protocol_v2_guard.py": "ff89d6b70be4b4738646d262beb67d7b7e932e9eb95956d940b1c5000a999d10",
    "05_project/tests/scripts/test_protocol_v2_2_r79_r78_trace_replay.py": "5bb1f1e3de673a1072cfee62938b761a62fd69c187d5eadf54bc46b115a3fd0a",
}
EXPECTED_MODEL = {
    "id": "Qwen/Qwen3-VL-32B-Instruct",
    "revision": "0cfaf48183f594c314753d30a4c4974bc75f3ccb",
    "backend": "qwen3_vl_32b_transformers_bf16_4x4090_v1",
}
FORBIDDEN_PRODUCTION_LITERALS = (
    "simplesmssendreceivedaddress",
    "openapptaskeval",
    "petar muller",
    "gabriel fernandez",
    "968 spruce",
    "sports tracker",
    "h17",
)


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


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _legacy_wip() -> dict[str, str]:
    status = _git("status", "--short").replace("\\", "/")
    actual: dict[str, str] = {}
    for relative, expected in EXPECTED_LEGACY_WIP.items():
        digest = sha256((REPOSITORY_ROOT / relative).read_bytes()).hexdigest()
        if digest != expected:
            raise RuntimeError(f"Legacy r79 WIP changed: {relative}")
        if relative not in status:
            raise RuntimeError(f"Legacy r79 WIP disappeared from git status: {relative}")
        actual[relative] = digest
    return actual


def _production_paths() -> list[Path]:
    names = (
        "binding_metrics_v0_2.py",
        "compiler_v0_2.py",
        "completion_v0_2.py",
        "controller_v0_2.py",
        "observation_v0_2.py",
        "recovery_v0_2.py",
        "task_roles.py",
    )
    return [PROJECT_ROOT / "src/raven_m/eest_ac" / name for name in names]


def _source_isolation() -> dict[str, Any]:
    forbidden_imports: list[str] = []
    forbidden_literals: list[dict[str, str]] = []
    for path in _production_paths():
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                rendered = ast.unparse(node)
                if "episode_controller" in rendered or "protocol_v2_guard" in rendered:
                    forbidden_imports.append(f"{path.name}:{rendered}")
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                folded = node.value.casefold()
                for literal in FORBIDDEN_PRODUCTION_LITERALS:
                    if literal in folded:
                        forbidden_literals.append({"path": path.name, "literal": literal})
    if forbidden_imports or forbidden_literals:
        raise RuntimeError(f"EEST v0.2 source isolation failed: imports={forbidden_imports}, literals={forbidden_literals}")
    return {
        "paths": [str(path.relative_to(REPOSITORY_ROOT)).replace("\\", "/") for path in _production_paths()],
        "forbidden_imports": [],
        "forbidden_task_or_instance_literals": [],
        "m_risk_online": False,
    }


def _implementation_hashes() -> dict[str, str]:
    paths = [
        *_production_paths(),
        PROJECT_ROOT / "src/raven_m/eest_ac/models.py",
        PROJECT_ROOT / "src/raven_m/eest_ac/risk.py",
        PROJECT_ROOT / "src/raven_m/eest_ac/schema.py",
        PROJECT_ROOT / "src/raven_m/eest_ac/state.py",
        PROJECT_ROOT / "src/raven_m/env/androidworld_adapter.py",
        PROJECT_ROOT / "src/raven_m/models/transformers_client.py",
        PROJECT_ROOT / "schemas/eest_ac_decision.v0_2.schema.json",
        PROJECT_ROOT / "prompts/eest_ac/executor_v0_2.md",
        PROJECT_ROOT / "prompts/eest_ac/summary_v0_1.md",
        PROJECT_ROOT / "scripts/preflight_eest_ac_v0_2.py",
        PROJECT_ROOT / "scripts/run_eest_ac_v0_2.py",
        LOCAL_RUNTIME / "scripts/androidworld_compat.py",
    ]
    return {
        str(path.relative_to(REPOSITORY_ROOT)).replace("\\", "/"): sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def _runtime_health(*, url: str, adb_path: str, console_port: int, grpc_port: int) -> dict[str, Any]:
    health = TransformersClient(url).health()
    if (
        health.get("model") != EXPECTED_MODEL["id"]
        or health.get("revision") != EXPECTED_MODEL["revision"]
        or health.get("backend") != EXPECTED_MODEL["backend"]
    ):
        raise RuntimeError("Runtime model health differs from the frozen v0.2 model.")
    env = env_launcher.load_and_setup_env(
        console_port=console_port,
        emulator_setup=False,
        freeze_datetime=True,
        adb_path=adb_path,
        grpc_port=grpc_port,
    )
    try:
        state = env.get_state(wait_to_stabilize=True)
        emulator = {"screen_shape": list(state.pixels.shape), "ui_element_count": len(getattr(state, "ui_elements", ()) or ())}
    finally:
        env.close()
    return {"model": health, "emulator": emulator}


def _verify_lock(lock_path: Path, study_id: str) -> list[dict[str, str]]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("study_id") != study_id or lock.get("frozen_before_model_calls") is not True:
        raise RuntimeError("Invalid v0.2 protocol lock.")
    records = []
    for item in lock["files"]:
        path = REPOSITORY_ROOT / item["path"]
        digest = sha256(path.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            raise RuntimeError(f"Locked file changed: {item['path']}")
        records.append({"path": item["path"], "sha256": digest})
    return records


def _verify_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "eest_ac_experiment.v0_2":
        raise RuntimeError("Wrong v0.2 config schema.")
    if set(config.get("arms", [])) != ONLINE_ARMS_V02 or "M_RISK" in config.get("arms", []):
        raise RuntimeError("v0.2 online arms must be B3, B3_MATCH, and M_SLOTS only.")
    tasks = {item["task_key"]: item for item in config["tasks"]}
    if len(tasks) != 3 or len(config["schedule"]) != 9:
        raise RuntimeError("v0.2 blind smoke requires three tasks and nine cells.")
    if sum(item["role"] == "cross_page_positive" for item in tasks.values()) != 2:
        raise RuntimeError("Exactly two cross-page positives are required.")
    if sum(item["role"] == "negative_control" for item in tasks.values()) != 1:
        raise RuntimeError("Exactly one negative control is required.")
    pairs = {(item["task_key"], item["arm"]) for item in config["schedule"]}
    expected = {(task, arm) for task in tasks for arm in ONLINE_ARMS_V02}
    if pairs != expected or [item["cell"] for item in config["schedule"]] != list(range(1, 10)):
        raise RuntimeError("Schedule is not a complete indexed 3x3 pairing.")
    if config["model"] != {**EXPECTED_MODEL, "temperature": 0, "context_cap_tokens": 8192, "max_new_tokens": 256}:
        raise RuntimeError("Model or budget drifted from v0.2 protocol.")
    if not config.get("blind_until_batch_complete") or config.get("auto_expand") is not False:
        raise RuntimeError("Blind lock and no-expansion policy are required.")


def _task_records(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    registered = registry.TaskRegistry().get_registry(registry.TaskRegistry.ANDROID_WORLD_FAMILY)
    parser = TaskRoleParser()
    result: dict[str, dict[str, Any]] = {}
    for spec in config["tasks"]:
        task_class = spec["task_class"]
        if task_class not in registered:
            raise RuntimeError(f"Task is absent from AndroidWorld: {task_class}")
        generated = []
        frame = None
        for _ in range(4):
            random.seed(spec["parameter_seed"])
            np.random.seed(spec["parameter_seed"])
            task_type = registered[task_class]
            task = task_type(task_type.generate_random_params())
            goal = str(task.goal)
            frame = parser.parse(goal, require_transfer=spec["role"] == "cross_page_positive")
            if not verify_exact_spans(goal, frame):
                raise RuntimeError(f"Role spans failed verification: {task_class}")
            generated.append(
                {
                    "goal": goal,
                    "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
                    "params_sha256": _digest_json(_json_safe(task.params)),
                    "role_frame": frame.record(),
                }
            )
        if len({_digest_json(item) for item in generated}) != 1:
            raise RuntimeError(f"Task generation is not deterministic: {task_class}")
        result[spec["task_key"]] = {"task_class": task_class, **generated[0]}
    positives = [value["task_class"] for key, value in result.items() if next(item for item in config["tasks"] if item["task_key"] == key)["role"] == "cross_page_positive"]
    if len(set(positives)) != 2:
        raise RuntimeError("Positive templates must be distinct classes.")
    return result


def _novelty_audit(config_path: Path, lock_path: Path, config: dict[str, Any], tasks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    excluded = {config_path.resolve(), lock_path.resolve()}
    for relative in config.get("novelty_scan_exclusions", []):
        excluded.add((REPOSITORY_ROOT / relative).resolve())
    run_root = (REPOSITORY_ROOT / config["run_root"]).resolve()
    hits: list[dict[str, str]] = []
    needles = {
        key: (value["task_class"], value["goal_sha256"], value["params_sha256"], value["goal"])
        for key, value in tasks.items()
    }
    for root in (REPOSITORY_ROOT / "runs", PROJECT_ROOT / "configs", REPOSITORY_ROOT / "reports"):
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.resolve() in excluded or run_root in path.resolve().parents:
                continue
            if path.suffix.casefold() not in {".json", ".jsonl", ".md", ".txt", ".yaml", ".yml"} or path.stat().st_size > 8_000_000:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for task_key, values in needles.items():
                for kind, needle in zip(("task_class", "goal_sha256", "params_sha256", "exact_goal"), values):
                    if needle and needle in text:
                        hits.append({"task_key": task_key, "kind": kind, "path": str(path.relative_to(REPOSITORY_ROOT)).replace("\\", "/")})
    if hits:
        raise RuntimeError(f"Selected task is not novel against prior artifacts: {hits[:20]}")
    return {"roots": ["runs", "05_project/configs", "reports"], "hits": []}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--check-runtime", action="store_true")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--adb-path", default="adb")
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    args = parser.parse_args()

    if (args.config is None) != (args.lock is None):
        raise RuntimeError("Config and lock must be supplied together.")
    result: dict[str, Any] = {
        "schema_version": "eest_ac_preflight.v0_2",
        "status": "pass",
        "checked_at_utc": _utc_now(),
        "zero_model_generation_calls": 0,
        "source_isolation": _source_isolation(),
        "implementation_hashes": _implementation_hashes(),
        "legacy_wip": _legacy_wip(),
        "runtime_health": _runtime_health(url=args.url, adb_path=args.adb_path, console_port=args.console_port, grpc_port=args.grpc_port) if args.check_runtime else {"status": "not_checked"},
    }
    if args.config is not None and args.lock is not None:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        _verify_config(config)
        tasks = _task_records(config)
        locked = _verify_lock(args.lock, config["study_id"])
        run_root = REPOSITORY_ROOT / config["run_root"]
        if run_root.exists() and any(run_root.iterdir()):
            raise RuntimeError(f"Frozen run root is not empty: {run_root}")
        result.update(
            {
                "study_id": config["study_id"],
                "config_path": str(args.config.resolve()),
                "config_sha256": sha256(args.config.read_bytes()).hexdigest(),
                "lock_path": str(args.lock.resolve()),
                "lock_sha256": sha256(args.lock.read_bytes()).hexdigest(),
                "locked_files": locked,
                "task_instance_records": tasks,
                "novelty_audit": _novelty_audit(args.config, args.lock, config, tasks),
                "run_root": str(run_root.resolve()),
                "run_root_empty": True,
            }
        )
    else:
        result["study_id"] = "eest_ac_v0_2_implementation_gate_20260803"
    _write_json(args.output, result)
    print(json.dumps({"status": "pass", "study_id": result["study_id"], "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
