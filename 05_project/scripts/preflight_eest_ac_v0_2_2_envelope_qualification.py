"""Zero-generation-call preflight for EEST-AC v0.2.2 qualification."""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
LOCAL_RUNTIME = REPOSITORY_ROOT / "06_local_runtime"
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(LOCAL_RUNTIME / "scripts"))

import androidworld_compat  # noqa: E402,F401
from raven_m.eest_ac.action_adapter_v0_2_2 import EestActionAdapterV022  # noqa: E402
from raven_m.eest_ac.action_contract_v0_2_2 import (  # noqa: E402
    DEFAULT_PROMPT_PATH,
    DEFAULT_SCHEMA_PATH,
    build_decision_schema,
    load_contract,
    render_executor_prompt,
)
from raven_m.eest_ac.observation_v0_2 import ObservationStabilizer  # noqa: E402
from raven_m.eest_ac.runtime_v0_2_2 import (  # noqa: E402
    assert_frozen_adb_server_port,
    load_and_setup_env,
)
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
    PROJECT_ROOT / "src/raven_m/eest_ac/action_contract_v0_2_2.py",
    PROJECT_ROOT / "src/raven_m/eest_ac/action_adapter_v0_2_2.py",
    PROJECT_ROOT / "src/raven_m/eest_ac/qualification_v0_2_2.py",
    PROJECT_ROOT / "src/raven_m/eest_ac/runtime_v0_2_2.py",
    PROJECT_ROOT / "src/raven_m/eest_ac/observation_policy_v0_2_2.py",
    PROJECT_ROOT / "scripts/run_eest_ac_v0_2_2_envelope_qualification.py",
)
FORBIDDEN_LITERALS = (
    "h17", "r79", "r80", "p2a", "p2b", "n2", "m_risk",
    "launcher", "app drawer", "settings", "contacts", "camera", "dialer", "files",
    "phone_number", "fixed coordinate",
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
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                rendered = ast.unparse(node)
                if "episode_controller" in rendered or "protocol_v2_guard" in rendered:
                    imports.append(f"{path.name}:{rendered}")
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                folded = node.value.casefold()
                for forbidden in FORBIDDEN_LITERALS:
                    pattern = rf"(?<![a-z0-9_]){re.escape(forbidden)}(?![a-z0-9_])"
                    if re.search(pattern, folded):
                        hits.append({"path": path.name, "literal": forbidden})
    if hits or imports:
        raise RuntimeError(f"v0.2.2 production isolation failed: literals={hits};imports={imports}")
    return {
        "production_paths": [str(path.relative_to(REPOSITORY_ROOT)).replace("\\", "/") for path in PRODUCTION_PATHS],
        "forbidden_imports": [],
        "forbidden_task_app_coordinate_branches": [],
        "probe_app_literals_live_only_in_frozen_config": True,
        "old_q_swipe_live_reuse": False,
        "m_risk_online": False,
    }


def _generated_exact() -> bool:
    contract = load_contract()
    return (
        json.loads(DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8")) == build_decision_schema(contract)
        and DEFAULT_PROMPT_PATH.read_text(encoding="utf-8") == render_executor_prompt(contract)
    )


def _verify_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != "eest_ac_envelope_qualification.v0_2_2":
        raise RuntimeError("Wrong qualification config version.")
    if not config.get("qualification_only") or config.get("scored") or config.get("arms"):
        raise RuntimeError("Qualification must remain non-scoring and armless.")
    if config.get("m_risk_online") or config.get("auto_start_efficacy"):
        raise RuntimeError("M-RISK and automatic efficacy are forbidden.")
    if config.get("stop_after_cells") != 3 or not config.get("stop_on_first_hard_failure"):
        raise RuntimeError("Qualification must stop after at most three cells and on first hard failure.")
    if config.get("observation") != {
        "delay_seconds": 1.0,
        "max_post_observations": 4,
        "terminal_window_observations": 2,
        "stable_change_policy": "last_two_pixel_a11y_package_agree_and_terminal_differs_from_pre",
        "require_state_change": True,
    }:
        raise RuntimeError("Frozen terminal settling-window policy drifted.")
    contract_observation = load_contract()["qualification_observation_contract"]
    if (
        contract_observation["delay_seconds"] != config["observation"]["delay_seconds"]
        or contract_observation["maximum_post_observations"]
        != config["observation"]["max_post_observations"]
        or contract_observation["terminal_window_observations"]
        != config["observation"]["terminal_window_observations"]
        or contract_observation["fallback_policy"] != "none"
    ):
        raise RuntimeError("Contract/config settling-window definitions diverged.")
    runtime = config.get("runtime", {})
    if runtime != {
        "adb_server_port": 5038,
        "device_serial": "emulator-5554",
        "fallback_to_default_port": False,
        "adb_binary_sha256": "957e46b8615f7af5b7292a2ddabe98d2e61940c3fb2b0545756507f080613e71",
    }:
        raise RuntimeError("Frozen explicit-ADB runtime policy drifted.")
    expected_model = {
        **EXPECTED_MODEL,
        "temperature": 0,
        "do_sample": False,
        "seed": 2026080420,
        "max_new_tokens": 256,
        "max_calls_per_probe": 2,
    }
    if config["model"] != expected_model:
        raise RuntimeError("Qualification model or call budget drifted.")
    probes = config.get("probes", [])
    if len(probes) != 3 or [item["cell"] for item in probes] != [1, 2, 3]:
        raise RuntimeError("Exactly three ordered probes are required.")
    if {item["coverage_category"] for item in probes} != {"swipe", "app_navigation", "navigation_press"}:
        raise RuntimeError("Frozen three-category coverage is incomplete.")
    if any(len(item["allowed_action_types"]) != 1 or not isinstance(item["setup_actions"], list) for item in probes):
        raise RuntimeError("Each probe needs one action type and generic setup action list.")
    serialized = json.dumps(config, ensure_ascii=False).casefold()
    contaminated = (
        "q-swipe", "app drawer", "reveal the app drawer", "swipe up to open app drawer",
        "2026080411", "eest_ac_v0_2_1_action_qualification",
    )
    if any(value in serialized for value in contaminated):
        raise RuntimeError("Executed v0.2.1 Q-SWIPE material leaked into live config.")


def _verify_lock(lock_path: Path, config: dict[str, Any]) -> list[dict[str, str]]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("study_id") != config["study_id"] or lock.get("frozen_before_model_calls") is not True:
        raise RuntimeError("Invalid v0.2.2 lock.")
    if lock.get("probe_order") != [item["probe_id"] for item in config["probes"]]:
        raise RuntimeError("Probe order differs from lock.")
    if _git("rev-list", "-n", "1", lock["source_tag"]) != lock["source_commit"]:
        raise RuntimeError("Source tag does not resolve to frozen source commit.")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", lock["source_commit"], "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        timeout=30,
    )
    if ancestor.returncode != 0:
        raise RuntimeError("Frozen source commit is not an ancestor of HEAD.")
    records = []
    for item in lock["files"]:
        actual = _hash(REPOSITORY_ROOT / item["path"])
        if actual != item["sha256"]:
            raise RuntimeError(f"Locked file drifted: {item['path']}")
        records.append({"path": item["path"], "sha256": actual})
    return records


def _verify_offline_reports(
    audit_path: Path,
    replay_path: Path,
    settling_path: Path,
    adb_stress_path: Path,
) -> dict[str, Any]:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    settling = json.loads(settling_path.read_text(encoding="utf-8"))
    adb_stress = json.loads(adb_stress_path.read_text(encoding="utf-8"))
    if (
        audit.get("status") != "pass"
        or audit.get("zero_model_generation_calls") != 0
        or audit.get("metadata_only_repair_calls") != 0
        or audit.get("token_certificate", {}).get("maximum_certified_total_qwen_tokens", 999) >= 256
    ):
        raise RuntimeError("Full-envelope audit did not pass.")
    expected = {
        "inputs": 2,
        "metadata_only_repair_calls": 0,
        "semantic_swipe": 2,
        "valid_complete_envelope": 2,
    }
    if replay.get("confusion") != expected or not replay.get("development_contaminated") or replay.get("live_evidence_eligible"):
        raise RuntimeError("Contaminated v0.2.1 replay boundary changed.")
    expected_settling_cases = {
        "stable_positive_settings_scroll": True,
        "dynamic_negative_camera": False,
        "a11y_missing_negative_notification_shade": False,
    }
    actual_settling_cases = {
        item["case_id"]: item["settling_audit"]["stable_change"]
        for item in settling.get("cases", [])
    }
    if (
        settling.get("status") != "pass"
        or settling.get("zero_model_generation_calls") != 0
        or settling.get("settings_precheck_counts_as_live_evidence") is not False
        or actual_settling_cases != expected_settling_cases
        or not all(item.get("passed") for item in settling.get("cases", []))
    ):
        raise RuntimeError("Terminal settling-window qualification did not pass.")
    if (
        adb_stress.get("status") != "pass"
        or adb_stress.get("zero_model_generation_calls") != 0
        or adb_stress.get("commands_planned") != 100
        or adb_stress.get("commands_completed") != 100
        or adb_stress.get("fallback_to_5037_rejected") is not True
        or adb_stress.get("server_before", {}).get("port") != 5038
        or adb_stress.get("server_after", {}).get("port") != 5038
        or adb_stress.get("server_before", {}).get("binary_sha256")
        != "957e46b8615f7af5b7292a2ddabe98d2e61940c3fb2b0545756507f080613e71"
        or adb_stress.get("server_after", {}).get("binary_sha256")
        != "957e46b8615f7af5b7292a2ddabe98d2e61940c3fb2b0545756507f080613e71"
        or any(item.get("explicit_port") != 5038 or not item.get("passed") for item in adb_stress.get("records", []))
    ):
        raise RuntimeError("Frozen ADB 5038 stress audit did not pass.")
    return {
        "full_envelope_audit_sha256": _hash(audit_path),
        "contaminated_replay_sha256": _hash(replay_path),
        "settling_window_qualification_sha256": _hash(settling_path),
        "adb_5038_stress_sha256": _hash(adb_stress_path),
        "maximum_certified_total_qwen_tokens": audit["token_certificate"]["maximum_certified_total_qwen_tokens"],
        "metadata_only_repair_calls": 0,
        "contaminated_replay_confusion": expected,
        "settling_window_cases": actual_settling_cases,
        "adb_5038_stress_commands": adb_stress["commands_completed"],
    }


def _powershell_server_binary(port: int) -> Path:
    command = (
        f"$owner=(Get-NetTCPConnection -LocalPort {port} -State Listen).OwningProcess;"
        "(Get-Process -Id $owner).Path"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
        timeout=35,
    )
    if result.returncode or not result.stdout.strip():
        raise RuntimeError(f"No ADB server is listening on frozen port {port}.")
    return Path(result.stdout.strip().splitlines()[-1])


def _adb_serial(adb_path: str, adb_server_port: int) -> str:
    result = subprocess.run(
        [adb_path, "-P", str(adb_server_port), "-s", "emulator-5554", "get-serialno"],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "ADB serial query failed.")
    return result.stdout.strip()


def _runtime(
    url: str,
    adb_path: str,
    adb_server_port: int,
    console_port: int,
    grpc_port: int,
    config: dict[str, Any],
) -> dict[str, Any]:
    health = TransformersClient(url).health()
    if any(health.get(key) != EXPECTED_MODEL[value] for key, value in (
        ("model", "id"), ("revision", "revision"), ("backend", "backend")
    )):
        raise RuntimeError("Real model runtime differs from frozen revision/backend.")
    assert_frozen_adb_server_port(
        configured=config["runtime"]["adb_server_port"],
        supplied=adb_server_port,
    )
    client_binary = Path(adb_path).resolve()
    client_hash = _hash(client_binary)
    server_binary = _powershell_server_binary(adb_server_port).resolve()
    server_hash = _hash(server_binary)
    serial = _adb_serial(adb_path, adb_server_port)
    if (
        client_hash != config["runtime"]["adb_binary_sha256"]
        or server_hash != client_hash
        or serial != config["runtime"]["device_serial"]
    ):
        raise RuntimeError("Frozen ADB binary/server/device identity drifted.")
    env = load_and_setup_env(
        console_port=console_port,
        emulator_setup=False,
        freeze_datetime=True,
        adb_path=adb_path,
        adb_server_port=adb_server_port,
        grpc_port=grpc_port,
    )
    try:
        state = env.get_state(wait_to_stabilize=True)
        observation = ObservationStabilizer.capture(state)
        matrix = EestActionAdapterV022().conformance_matrix(
            screen_width=int(state.pixels.shape[1]),
            screen_height=int(state.pixels.shape[0]),
        )
        return {
            "model": health,
            "adb": {
                "server_port": adb_server_port,
                "fallback_to_default_port": False,
                "client_binary": str(client_binary),
                "client_binary_sha256": client_hash,
                "server_binary": str(server_binary),
                "server_binary_sha256": server_hash,
                "same_official_binary": server_hash == client_hash,
                "device_serial": serial,
            },
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
    parser.add_argument("--contaminated-replay", type=Path, required=True)
    parser.add_argument("--settling-window-report", type=Path, required=True)
    parser.add_argument("--adb-stress-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check-runtime", action="store_true")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--adb-path", default="adb")
    parser.add_argument("--adb-server-port", type=int, required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    _verify_config(config)
    if not _generated_exact():
        raise RuntimeError("Generated prompt/schema drifted from full-envelope contract.")
    offline = _verify_offline_reports(
        args.contract_audit,
        args.contaminated_replay,
        args.settling_window_report,
        args.adb_stress_report,
    )
    lock_records = _verify_lock(args.lock, config)
    run_root = REPOSITORY_ROOT / config["run_root"]
    if run_root.exists() and any(run_root.iterdir()):
        raise RuntimeError("Qualification run root is not empty.")
    result = {
        "schema_version": "eest_ac_envelope_qualification_preflight.v0_2_2",
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
        "runtime": _runtime(
            args.url,
            args.adb_path,
            args.adb_server_port,
            args.console_port,
            args.grpc_port,
            config,
        ) if args.check_runtime else {"status": "not_checked"},
        "run_root": str(run_root.resolve()),
        "run_root_empty": True,
    }
    _write(args.output, result)
    print(json.dumps({"status": "pass", "zero_model_generation_calls": 0, "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
