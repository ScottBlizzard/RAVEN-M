"""Run zero-device-mutation offline gates for INFRA-M3."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
PYTHON = REPOSITORY_ROOT / "06_local_runtime/envs/androidworld/Scripts/python.exe"
OUTPUT_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m3_offline_gates"
CONFIG_PATH = PROJECT_ROOT / "configs/role_binding_timing/infra_m3_external_log_maintenance_a11y.json"
KNOWN_FAILURE = "tests/scripts/test_protocol_v2_2_r78_h17_candidate.py::test_r78_candidate_static_manifest_validation_passes"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def save(path: Path, value: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    return {"path": path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": len(value), "sha256": digest(value)}


def run_gate(gate_id: str, command: list[str], cwd: Path) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(command, cwd=cwd, capture_output=True, timeout=900)
    root = OUTPUT_ROOT / gate_id
    return {
        "gate_id": gate_id,
        "command": command,
        "returncode": completed.returncode,
        "timed_out": False,
        "wall_time_seconds": time.monotonic() - started,
        "stdout": save(root / "stdout.bin", completed.stdout),
        "stderr": save(root / "stderr.bin", completed.stderr),
    }


def load_m1() -> Any:
    path = PROJECT_ROOT / "scripts/run_role_binding_timing_infra_m1_maintenance.py"
    spec = importlib.util.spec_from_file_location("m1_for_m3_gate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("M1_LOAD")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise RuntimeError("M3_OFFLINE_GATE_ROOT_NOT_FRESH")
    OUTPUT_ROOT.mkdir(parents=True)
    (OUTPUT_ROOT / ".gitattributes").write_text("*.bin binary\n", encoding="ascii")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    project = PROJECT_ROOT
    gates = [
        run_gate("compile", [str(PYTHON), "-m", "py_compile", "src/raven_m/role_binding_timing/infra_m3_log_lifecycle.py", "scripts/run_role_binding_timing_infra_m3.py"], project),
        run_gate("focused", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing/test_infra_m3_log_lifecycle.py", "-q", "--color=no"], project),
        run_gate("namespace", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing", "-q", "--color=no"], project),
        run_gate("full_regression", [str(PYTHON), "-m", "pytest", "tests", "-q", "--color=no"], project),
    ]
    full_text = (OUTPUT_ROOT / "full_regression/stdout.bin").read_text(encoding="utf-8", errors="replace")
    failed_nodes = sorted(set(line.split()[1] for line in full_text.splitlines() if line.startswith("FAILED ")))
    full_accepted = gates[3]["returncode"] == 1 and failed_nodes == [KNOWN_FAILURE]

    schema = json.loads((REPOSITORY_ROOT / config["schema"]).read_text(encoding="utf-8"))
    sample = {
        "schema_version": "role_binding_timing.infra_m3.completion.v1", "status": "RUNTIME_UNSTABLE",
        "first_broken_edge": "OFFLINE", "generation_calls": 0, "model_tokens": 0,
        "runtime": {}, "burn_in": {"passed": False, "required_cycles": 24, "completed_cycles": 0, "passed_cycles": 0, "elapsed_seconds": 0, "records": []},
        "a11y": {"authorized": False, "settings": {}, "grid": {}}, "cleanup": {},
        "log_seal": {"passed": False, "records": [], "temporary_root_removed": False},
        "protected_wip_unchanged": True,
        "claim_evidence": {"exclusive_5038_registration": False, "burn_in_qualified": False, "a11y_tested": False, "a11y_qualified": False, "v0_3_preparation_authorized": False, "held_out_tested": False, "role_binding_hypothesis_tested": False},
    }
    validator = Draft202012Validator(schema)
    schema_errors = [item.message for item in validator.iter_errors(sample)]
    corrupt = dict(sample); corrupt["generation_calls"] = 1
    corruption_detected = bool(list(validator.iter_errors(corrupt)))

    protected = {name: sha256((REPOSITORY_ROOT / name).read_bytes()).hexdigest() for name in config["protected_wip"]}
    source = (PROJECT_ROOT / "scripts/run_role_binding_timing_infra_m3.py").read_text(encoding="utf-8")
    lifecycle = (PROJECT_ROOT / "src/raven_m/role_binding_timing/infra_m3_log_lifecycle.py").read_text(encoding="utf-8")
    joined = source + "\n" + lifecycle + "\n" + CONFIG_PATH.read_text(encoding="utf-8")
    source_gate = {
        "no_prior_frozen_log_path": "infra_m1_maintenance_burnin/maintenance/start/emulator.stdout.bin" not in joined,
        "no_5037_adb_command": "adb_prefix(config, 5037" not in source,
        "external_temp_present": "temp_parent" in joined and "create_live_root" in source,
        "close_before_seal_present": "parent_handles_closed" in source and "seal_live_logs" in source,
        "no_generation_surface": "generation_calls_authorized" in joined,
    }
    source_gate["passed"] = all(source_gate.values())

    m1 = load_m1()
    snapshot = m1.runtime_snapshot(config)
    runtime = config["runtime"]
    expected = config["pre_cleanup_identity"]
    runtime_issues = []
    if snapshot["listeners"]["5037"]: runtime_issues.append("5037_PRESENT")
    if snapshot["listeners"]["5038"] != [expected["adb_5038_pid"]]: runtime_issues.append("5038_IDENTITY")
    if any(snapshot["listeners"][str(port)] for port in (5554, 5555, 8554)): runtime_issues.append("EMULATOR_PRESENT")
    if snapshot["excluded_runtime_pids"] != expected["excluded_runtime_pids"]: runtime_issues.append("EXCLUDED_PID_DRIFT")
    if (REPOSITORY_ROOT / config["output_root"]).exists(): runtime_issues.append("OUTPUT_ROOT_EXISTS")
    temp_parent = Path(config["log_lifecycle"]["temp_parent"])
    temp_residue = sorted(path.name for path in temp_parent.glob(f"{config['log_lifecycle']['temp_prefix']}*")) if temp_parent.exists() else []
    if temp_residue: runtime_issues.append("TEMP_RESIDUE")
    binary_hashes = {
        key: sha256((REPOSITORY_ROOT / runtime[key]).read_bytes()).hexdigest()
        for key in ("python", "adb_binary", "emulator_launcher", "qemu_binary", "avd_ini", "avd_config")
    }
    expected_hashes = {
        "python": runtime["python_sha256"], "adb_binary": runtime["adb_binary_sha256"],
        "emulator_launcher": runtime["emulator_launcher_sha256"], "qemu_binary": runtime["qemu_binary_sha256"],
        "avd_ini": runtime["avd_ini_sha256"], "avd_config": runtime["avd_config_sha256"],
    }
    binary_pass = binary_hashes == expected_hashes
    legacy_path = REPOSITORY_ROOT / "05_project/artifacts/role_binding_timing/infra_m1_maintenance_burnin/maintenance/start/emulator.stdout.bin"
    legacy_restore = {"bytes": legacy_path.stat().st_size, "sha256": sha256(legacy_path.read_bytes()).hexdigest()}
    legacy_restore["passed"] = legacy_restore == {"bytes": 9590, "sha256": "ffddf9d0862f8f3e58b424e1e8f774e546875634a0ba81f5e720333284b48b1c"}

    result = {
        "schema_version": "role_binding_timing.infra_m3.offline_gates.v1",
        "created_at": utc_now(), "generation_calls": 0, "device_mutations": 0, "restart_attempts": 0,
        "gates": gates,
        "compile_pass": gates[0]["returncode"] == 0,
        "focused_pass": gates[1]["returncode"] == 0,
        "namespace_pass": gates[2]["returncode"] == 0,
        "full_regression_accepted": full_accepted,
        "full_regression_observed_failed_nodes": failed_nodes,
        "full_regression_expected_only_failure": KNOWN_FAILURE,
        "schema_gate": {"passed": not schema_errors and corruption_detected, "errors": schema_errors, "corruption_detected": corruption_detected},
        "source_gate": source_gate,
        "protected_wip": protected, "protected_wip_pass": protected == config["protected_wip"],
        "runtime_preflight": {"passed": not runtime_issues, "issues": runtime_issues, "snapshot": snapshot, "temp_residue": temp_residue},
        "binary_hashes": binary_hashes, "binary_hashes_pass": binary_pass,
        "legacy_restore_observation": legacy_restore,
    }
    result["overall_pass"] = all((
        result["compile_pass"], result["focused_pass"], result["namespace_pass"],
        result["full_regression_accepted"], result["schema_gate"]["passed"], source_gate["passed"],
        result["protected_wip_pass"], result["runtime_preflight"]["passed"], binary_pass,
        legacy_restore["passed"],
    ))
    raw = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (OUTPUT_ROOT / "offline_gate_result.json").write_bytes(raw)
    print(json.dumps({"overall_pass": result["overall_pass"], "failed_nodes": failed_nodes, "runtime_issues": runtime_issues}, indent=2))
    return 0 if result["overall_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
