"""Zero-generation-call preflight for the frozen EEST-AC paired smoke."""

from __future__ import annotations

import argparse
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
from raven_m.eest_ac.controller import ARMS, _json_safe  # noqa: E402
from raven_m.models.transformers_client import TransformersClient  # noqa: E402


EXPECTED_LEGACY_WIP = {
    "05_project/src/raven_m/controller/episode_controller.py": (
        "fc0e82e0fde90119365d4f685f080eb4519bf2f602e4bda58de5d4809a40fe33"
    ),
    "05_project/src/raven_m/controller/protocol_v2_guard.py": (
        "ff89d6b70be4b4738646d262beb67d7b7e932e9eb95956d940b1c5000a999d10"
    ),
    "05_project/tests/scripts/test_protocol_v2_2_r79_r78_trace_replay.py": (
        "5bb1f1e3de673a1072cfee62938b761a62fd69c187d5eadf54bc46b115a3fd0a"
    ),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest_json(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def _verify_lock(lock_path: Path, study_id: str) -> list[dict[str, str]]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("study_id") != study_id or not lock.get("frozen_before_model_calls"):
        raise RuntimeError("Protocol lock is not the active pre-model-call lock.")
    records = []
    for item in lock["files"]:
        path = REPOSITORY_ROOT / item["path"]
        actual = sha256(path.read_bytes()).hexdigest()
        if actual != item["sha256"]:
            raise RuntimeError(f"Protocol hash mismatch: {item['path']}")
        records.append({"path": item["path"], "sha256": actual})
    return records


def _verify_config(config: dict[str, Any]) -> None:
    if config.get("formal_scoring") is not False or config.get("development_smoke") is not True:
        raise RuntimeError("This launcher is restricted to the development smoke.")
    if set(config["arms"]) != ARMS:
        raise RuntimeError("The smoke must contain exactly four preregistered arms.")
    tasks = {item["task_key"]: item for item in config["tasks"]}
    if len(config["schedule"]) != 8 or len(tasks) != 2:
        raise RuntimeError("The minimal smoke must contain two tasks and eight cells.")
    seen = set()
    by_task: dict[str, set[str]] = {key: set() for key in tasks}
    for index, item in enumerate(config["schedule"], start=1):
        if item["cell"] != index or item["task_key"] not in tasks:
            raise RuntimeError("Schedule indices or task keys are invalid.")
        pair = (item["task_key"], item["arm"])
        if pair in seen:
            raise RuntimeError("Duplicate task/arm cell.")
        seen.add(pair)
        by_task[item["task_key"]].add(item["arm"])
    if any(arms != ARMS for arms in by_task.values()):
        raise RuntimeError("Every task must be paired across all four arms.")
    selected_names = {item["task_class"] for item in tasks.values()}
    if selected_names & set(config["forbidden_task_classes"]):
        raise RuntimeError("A forbidden task class entered the smoke.")
    if any(
        "sports" in name.casefold() or "date" in name.casefold()
        for name in selected_names
    ):
        raise RuntimeError("A forbidden Sports/date task pattern entered the smoke.")
    if config["model"]["context_cap_tokens"] != 8192:
        raise RuntimeError("Context cap drifted from 8192.")
    if config["model"]["max_new_tokens"] != 256:
        raise RuntimeError("Maximum new tokens drifted from 256.")


def _task_hashes(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    task_registry = registry.TaskRegistry()
    registered = task_registry.get_registry(task_registry.ANDROID_WORLD_FAMILY)
    result = {}
    for item in config["tasks"]:
        task_class = item["task_class"]
        if task_class not in registered:
            raise RuntimeError(f"Task is absent from AndroidWorld: {task_class}")
        generated = []
        for _ in range(4):
            random.seed(config["parameter_seed"])
            np.random.seed(config["parameter_seed"])
            task_type = registered[task_class]
            task = task_type(task_type.generate_random_params())
            generated.append(
                (
                    sha256(str(task.goal).encode("utf-8")).hexdigest(),
                    _digest_json(_json_safe(task.params)),
                )
            )
        if len(set(generated)) != 1:
            raise RuntimeError(f"Task generation is not deterministic: {task_class}")
        result[item["task_key"]] = {
            "task_class": task_class,
            "goal_sha256": generated[0][0],
            "params_sha256": generated[0][1],
        }
    return result


def _source_isolation() -> dict[str, Any]:
    source_root = PROJECT_ROOT / "src/raven_m/eest_ac"
    source_files = sorted(source_root.glob("*.py"))
    forbidden_imports = []
    neutral_padding_hits = []
    for path in source_files:
        text = path.read_text(encoding="utf-8")
        if "protocol_v2_guard" in text or "episode_controller" in text:
            forbidden_imports.append(str(path.relative_to(REPOSITORY_ROOT)))
        if "neutral_padding" in text:
            neutral_padding_hits.append(str(path.relative_to(REPOSITORY_ROOT)))
    if forbidden_imports:
        raise RuntimeError(f"Legacy controller import found: {forbidden_imports}")
    if neutral_padding_hits:
        raise RuntimeError(f"Neutral padding found: {neutral_padding_hits}")
    return {
        "python_files": [str(path.relative_to(REPOSITORY_ROOT)) for path in source_files],
        "forbidden_imports": forbidden_imports,
        "neutral_padding_hits": neutral_padding_hits,
    }


def _verify_legacy_wip() -> dict[str, str]:
    actual = {}
    for relative, expected in EXPECTED_LEGACY_WIP.items():
        path = REPOSITORY_ROOT / relative
        digest = sha256(path.read_bytes()).hexdigest()
        if digest != expected:
            raise RuntimeError(f"Legacy r79 WIP changed during pivot: {relative}")
        actual[relative] = digest
    status = _git("status", "--short")
    for relative in EXPECTED_LEGACY_WIP:
        if relative not in status.replace("\\", "/"):
            raise RuntimeError(f"Legacy r79 WIP is no longer visible in status: {relative}")
    return actual


def _runtime_health(
    *,
    url: str,
    adb_path: str,
    console_port: int,
    grpc_port: int,
) -> dict[str, Any]:
    health = TransformersClient(url).health()
    env = env_launcher.load_and_setup_env(
        console_port=console_port,
        emulator_setup=False,
        freeze_datetime=True,
        adb_path=adb_path,
        grpc_port=grpc_port,
    )
    try:
        state = env.get_state(wait_to_stabilize=True)
        emulator = {
            "screen_shape": list(state.pixels.shape),
            "ui_element_count": len(getattr(state, "ui_elements", ()) or ()),
        }
    finally:
        env.close()
    return {"model": health, "emulator": emulator}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "configs/eest_ac/eest_ac_smoke_v0_1_1.json",
    )
    parser.add_argument(
        "--lock",
        type=Path,
        default=PROJECT_ROOT / "configs/eest_ac/protocol_lock_v0_1_1.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check-runtime", action="store_true")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--adb-path", default="adb")
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    _verify_config(config)
    locked_files = _verify_lock(args.lock, config["study_id"])
    tag_commit = _git("rev-list", "-n", "1", "eest-ac-smoke-v0.1.1-protocol-freeze-20260803")
    _git("merge-base", "--is-ancestor", tag_commit, "HEAD")
    run_root = REPOSITORY_ROOT / config["run_root"]
    if run_root.exists() and any(run_root.iterdir()):
        raise RuntimeError(f"Isolated run root is not empty: {run_root}")
    result = {
        "schema_version": "eest_ac_preflight.v0_1_1",
        "study_id": config["study_id"],
        "status": "pass",
        "checked_at_utc": _utc_now(),
        "zero_model_generation_calls": 0,
        "config_path": str(args.config.resolve()),
        "config_sha256": sha256(args.config.read_bytes()).hexdigest(),
        "lock_path": str(args.lock.resolve()),
        "lock_sha256": sha256(args.lock.read_bytes()).hexdigest(),
        "locked_files": locked_files,
        "protocol_tag_commit": tag_commit,
        "task_instance_hashes": _task_hashes(config),
        "source_isolation": _source_isolation(),
        "legacy_wip": _verify_legacy_wip(),
        "run_root": str(run_root.resolve()),
        "run_root_empty": True,
        "runtime_health": (
            _runtime_health(
                url=args.url,
                adb_path=args.adb_path,
                console_port=args.console_port,
                grpc_port=args.grpc_port,
            )
            if args.check_runtime
            else {"status": "not_checked"}
        ),
    }
    _write_json(args.output, result)
    print(json.dumps({"status": "pass", "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
