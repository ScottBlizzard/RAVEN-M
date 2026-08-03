"""Zero-generation-call preflight for EEST-AC v0.2.1 qualification."""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
LOCAL_RUNTIME = REPOSITORY_ROOT / "06_local_runtime"
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(LOCAL_RUNTIME / "scripts"))

import androidworld_compat  # noqa: E402,F401
from android_world.env import env_launcher  # noqa: E402
from raven_m.eest_ac.action_adapter_v0_2_1 import EestActionAdapterV021  # noqa: E402
from raven_m.eest_ac.action_contract_v0_2_1 import (  # noqa: E402
    DEFAULT_CONTRACT_PATH,
    DEFAULT_PROMPT_PATH,
    DEFAULT_SCHEMA_PATH,
    build_decision_schema,
    load_contract,
    render_executor_prompt,
)
from raven_m.eest_ac.observation_v0_2 import ObservationStabilizer  # noqa: E402
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
PRODUCTION_PATHS = (
    PROJECT_ROOT / "src/raven_m/eest_ac/action_contract_v0_2_1.py",
    PROJECT_ROOT / "src/raven_m/eest_ac/action_adapter_v0_2_1.py",
    PROJECT_ROOT / "src/raven_m/eest_ac/qualification_v0_2_1.py",
)
FORBIDDEN = (
    "simplesms", "markor", "clock", "p2a", "p2b", "n2", "h17",
    "sports tracker", "phone_number", "m_risk",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git failed")
    return result.stdout.strip()


def _legacy() -> dict[str, str]:
    status = _git("status", "--short").replace("\\", "/")
    result = {}
    for relative, expected in EXPECTED_LEGACY_WIP.items():
        digest = _hash(REPOSITORY_ROOT / relative)
        if digest != expected or relative not in status:
            raise RuntimeError(f"Legacy WIP boundary changed: {relative}")
        result[relative] = digest
    return result


def _source_isolation() -> dict[str, Any]:
    hits = []
    imports = []
    for path in PRODUCTION_PATHS:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                rendered = ast.unparse(node)
                if "episode_controller" in rendered or "protocol_v2_guard" in rendered:
                    imports.append(f"{path.name}:{rendered}")
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                folded = node.value.casefold()
                for forbidden in FORBIDDEN:
                    if forbidden in folded:
                        hits.append({"path": path.name, "literal": forbidden})
    if hits or imports:
        raise RuntimeError(f"v0.2.1 isolation failed: literals={hits};imports={imports}")
    return {
        "production_paths": [str(path.relative_to(REPOSITORY_ROOT)).replace("\\", "/") for path in PRODUCTION_PATHS],
        "forbidden_imports": [],
        "forbidden_task_app_guard_literals": [],
        "qualification_probe_app_literal_lives_only_in_config": True,
        "m_risk_online": False,
    }


def _generated_exact() -> bool:
    contract = load_contract()
    return (
        json.loads(DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8")) == build_decision_schema(contract)
        and DEFAULT_PROMPT_PATH.read_text(encoding="utf-8") == render_executor_prompt(contract)
    )


def _verify_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "eest_ac_action_qualification.v0_2_1":
        raise RuntimeError("Wrong qualification config version.")
    if not config.get("qualification_only") or config.get("scored") or config.get("arms"):
        raise RuntimeError("Qualification config must be non-scoring and armless.")
    if config.get("m_risk_online") or config.get("auto_start_efficacy"):
        raise RuntimeError("M-RISK and automatic efficacy are forbidden.")
    if config.get("stop_after_cells") != 3 or not config.get("stop_on_first_hard_failure"):
        raise RuntimeError("Qualification must stop after at most three cells and on hard failure.")
    model = config["model"]
    if model != {
        **EXPECTED_MODEL,
        "temperature": 0,
        "do_sample": False,
        "seed": 2026080401,
        "max_new_tokens": 256,
        "max_calls_per_probe": 2,
    }:
        raise RuntimeError("Qualification model or budget drifted.")
    probes = config.get("probes", [])
    if len(probes) != 3 or [item["cell"] for item in probes] != [1, 2, 3]:
        raise RuntimeError("Exactly three indexed probes are required.")
    categories = {item["coverage_category"] for item in probes}
    if categories != {"swipe", "app_navigation", "navigation_press"}:
        raise RuntimeError("Frozen three-category coverage is incomplete.")
    if any(len(item["allowed_action_types"]) != 1 for item in probes):
        raise RuntimeError("Each probe must have one frozen action category.")
    serialized = json.dumps(config, ensure_ascii=False).casefold()
    if any(value in serialized for value in ("eest-p2a", "eest-p2b", "eest-n2")):
        raise RuntimeError("Development task IDs leaked into qualification config.")


def _verify_lock(lock_path: Path, config: dict[str, Any]) -> list[dict[str, str]]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("study_id") != config["study_id"] or lock.get("frozen_before_model_calls") is not True:
        raise RuntimeError("Invalid v0.2.1 lock.")
    records = []
    for item in lock["files"]:
        path = REPOSITORY_ROOT / item["path"]
        actual = _hash(path)
        if actual != item["sha256"]:
            raise RuntimeError(f"Locked file drifted: {item['path']}")
        records.append({"path": item["path"], "sha256": actual})
    return records


def _verify_offline_reports(contract_audit: Path, replay: Path) -> dict[str, Any]:
    audit = json.loads(contract_audit.read_text(encoding="utf-8"))
    replay_value = json.loads(replay.read_text(encoding="utf-8"))
    if (
        audit.get("status") != "pass"
        or audit.get("zero_model_generation_calls") != 0
        or audit.get("maximal_serialization", {}).get("maximum_qwen_tokens", 999) >= 256
    ):
        raise RuntimeError("Contract audit did not pass.")
    expected = {
        "original_invalid": 18,
        "safe_normalize": 8,
        "must_repair": 10,
        "canonical_direct": 0,
        "repair_outputs_identical_to_initial_invalid_action": 9,
    }
    if replay_value.get("confusion") != expected:
        raise RuntimeError("v0.2 18-output replay changed.")
    return {
        "contract_audit_sha256": _hash(contract_audit),
        "replay_sha256": _hash(replay),
        "maximum_qwen_tokens": audit["maximal_serialization"]["maximum_qwen_tokens"],
        "replay_confusion": expected,
    }


def _runtime(url: str, adb_path: str, console_port: int, grpc_port: int) -> dict[str, Any]:
    health = TransformersClient(url).health()
    if any(health.get(key) != EXPECTED_MODEL[value] for key, value in (("model", "id"), ("revision", "revision"), ("backend", "backend"))):
        raise RuntimeError("Real model runtime differs from the frozen revision/backend.")
    env = env_launcher.load_and_setup_env(
        console_port=console_port,
        emulator_setup=False,
        freeze_datetime=True,
        adb_path=adb_path,
        grpc_port=grpc_port,
    )
    try:
        state = env.get_state(wait_to_stabilize=True)
        observation = ObservationStabilizer.capture(state)
        matrix = EestActionAdapterV021().conformance_matrix(
            screen_width=int(state.pixels.shape[1]),
            screen_height=int(state.pixels.shape[0]),
        )
        return {
            "model": health,
            "emulator": {
                "screen_shape": list(state.pixels.shape),
                "a11y_available": observation.fingerprint.a11y_available,
                "state_signature": observation.fingerprint.state_signature,
            },
            "adapter_types": [row["type"] for row in matrix],
        }
    finally:
        env.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--contract-audit", type=Path, required=True)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check-runtime", action="store_true")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--adb-path", default="adb")
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    _verify_config(config)
    if not _generated_exact():
        raise RuntimeError("Generated prompt/schema drifted from contract.")
    offline = _verify_offline_reports(args.contract_audit, args.replay)
    lock_records = _verify_lock(args.lock, config)
    run_root = REPOSITORY_ROOT / config["run_root"]
    if run_root.exists() and any(run_root.iterdir()):
        raise RuntimeError("Qualification run root is not empty.")
    result = {
        "schema_version": "eest_ac_action_qualification_preflight.v0_2_1",
        "status": "pass",
        "checked_at_utc": _utc_now(),
        "study_id": config["study_id"],
        "zero_model_generation_calls": 0,
        "config_path": str(args.config.resolve()),
        "config_sha256": _hash(args.config),
        "lock_path": str(args.lock.resolve()),
        "lock_sha256": _hash(args.lock),
        "legacy_wip": _legacy(),
        "source_isolation": _source_isolation(),
        "generated_artifacts_exact": True,
        "offline_gates": offline,
        "locked_files": lock_records,
        "runtime": _runtime(args.url, args.adb_path, args.console_port, args.grpc_port) if args.check_runtime else {"status": "not_checked"},
        "run_root": str(run_root.resolve()),
        "run_root_empty": True,
    }
    _write(args.output, result)
    print(json.dumps({"status": "pass", "zero_model_generation_calls": 0, "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
