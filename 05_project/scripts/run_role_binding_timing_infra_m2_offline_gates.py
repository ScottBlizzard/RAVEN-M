"""Capture byte-exact offline gates for INFRA-M2 before protocol freeze."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
OUTPUT_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m2_emulator_adb_offline_gates"
PYTHON = REPOSITORY_ROOT / "06_local_runtime/envs/androidworld/Scripts/python.exe"
CONFIG_PATH = PROJECT_ROOT / "configs/role_binding_timing/infra_m2_emulator_adb_port_burnin.json"
EXPECTED_FULL_FAILURE = "tests/scripts/test_protocol_v2_2_r78_h17_candidate.py::test_r78_candidate_static_manifest_validation_passes"


def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def digest_path(path: Path) -> str:
    return digest(path.read_bytes())


def run_gate(gate_id: str, command: list[str], *, timeout: float) -> dict[str, Any]:
    root = OUTPUT_ROOT / gate_id
    root.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=PROJECT_ROOT, env=env, capture_output=True, text=False, check=False, timeout=timeout)
        stdout, stderr = bytes(result.stdout), bytes(result.stderr)
        returncode, timed_out = result.returncode, False
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = bytes(exc.stdout or b""), bytes(exc.stderr or b"")
        returncode, timed_out = None, True
    stdout_path, stderr_path = root / "stdout.bin", root / "stderr.bin"
    stdout_path.write_bytes(stdout); stderr_path.write_bytes(stderr)
    return {
        "gate_id": gate_id, "command": command, "returncode": returncode, "timed_out": timed_out,
        "wall_time_seconds": time.monotonic() - started,
        "stdout": {"path": stdout_path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": len(stdout), "sha256": digest(stdout)},
        "stderr": {"path": stderr_path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": len(stderr), "sha256": digest(stderr)},
        "stdout_text": stdout.decode("utf-8", errors="replace"),
    }


def listener_pids(netstat: str, port: int) -> list[int]:
    found = set()
    for line in netstat.splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[0].upper() == "TCP" and fields[3].upper() == "LISTENING" and fields[1].rsplit(":", 1)[-1] == str(port):
            found.add(int(fields[-1]))
    return sorted(found)


def process_record(pid: int) -> dict[str, Any] | None:
    command = f'Get-CimInstance Win32_Process -Filter "ProcessId={pid}" | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Depth 3'
    result = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True, check=False, timeout=20)
    return json.loads(result.stdout) if result.stdout.strip() else None


def manifest_errors(root: Path) -> list[str]:
    manifest = json.loads((root / "artifact_manifest.json").read_text(encoding="utf-8"))
    errors = []
    for item in manifest["artifacts"]:
        path = REPOSITORY_ROOT / item["path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or digest_path(path) != item["sha256"]:
            errors.append(item["path"])
    return errors


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise RuntimeError("OFFLINE_GATE_OUTPUT_NOT_FRESH")
    OUTPUT_ROOT.mkdir(parents=True)
    (OUTPUT_ROOT / ".gitattributes").write_text("*.bin binary\n", encoding="ascii")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    gates = [
        run_gate("compile", [str(PYTHON), "-m", "py_compile", "src/raven_m/role_binding_timing/infra_m2_runtime.py", "scripts/run_role_binding_timing_infra_m2.py"], timeout=120),
        run_gate("focused", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing/test_infra_m2_runtime.py", "-q", "--color=no"], timeout=180),
        run_gate("namespace", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing", "-q", "--color=no"], timeout=600),
        run_gate("full_regression", [str(PYTHON), "-m", "pytest", "tests", "-q", "--color=no"], timeout=1500),
    ]
    compile_pass = gates[0]["returncode"] == 0 and not gates[0]["timed_out"]
    focused_pass = gates[1]["returncode"] == 0 and not gates[1]["timed_out"]
    namespace_pass = gates[2]["returncode"] == 0 and not gates[2]["timed_out"]
    failed_nodes = [item.replace("\\", "/") for item in re.findall(r"^FAILED\s+([^\s]+)", gates[3]["stdout_text"], flags=re.MULTILINE)]
    full_accepted = gates[3]["returncode"] == 1 and not gates[3]["timed_out"] and failed_nodes == [EXPECTED_FULL_FAILURE]

    runner = (PROJECT_ROOT / "scripts/run_role_binding_timing_infra_m2.py").read_text(encoding="utf-8")
    runtime_source = (PROJECT_ROOT / "src/raven_m/role_binding_timing/infra_m2_runtime.py").read_text(encoding="utf-8")
    source_gate = {
        "legacy_5037_command_sites": runner.count("adb_prefix(config, 5037"),
        "uses_verified_environment_builder": "prepare_emulator_environment(" in runner,
        "has_launch_5037_stop": "FORBIDDEN_5037_DURING_LAUNCH" in runner,
        "has_legacy_log_guard": "LEGACY_FROZEN_LOG_DRIFT_ON_SHUTDOWN" in runner,
        "forbidden_app_hits": [name for name in ("com.android.settings", "com.google.android", "org.tasks", "broccoli", "H17", "r79") if name.casefold() in (runner + runtime_source).casefold()],
    }
    source_gate["passed"] = (
        source_gate["legacy_5037_command_sites"] == 2
        and source_gate["uses_verified_environment_builder"]
        and source_gate["has_launch_5037_stop"]
        and source_gate["has_legacy_log_guard"]
        and not source_gate["forbidden_app_hits"]
    )

    schema = json.loads((REPOSITORY_ROOT / config["schema"]).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    stable = {
        "schema_version": "role_binding_timing.infra_m2.completion.v1", "status": "RUNTIME_STABLE_24_OF_24", "first_broken_edge": None,
        "generation_calls": 0, "model_tokens": 0, "legacy_cleanup": {}, "launch": {},
        "burn_in": {"passed": True, "required_cycles": 24, "completed_cycles": 24, "passed_cycles": 24, "elapsed_seconds": 180, "records": [{} for _ in range(24)]},
        "protected_wip_unchanged": True,
        "claim_evidence": {"exclusive_5038_registration": True, "runtime_stable": True, "a11y_authorized": True, "a11y_tested": False, "held_out_tested": False, "role_binding_hypothesis_tested": False},
    }
    stable_errors = [item.message for item in Draft202012Validator(schema).iter_errors(stable)]
    corrupt = json.loads(json.dumps(stable)); corrupt["burn_in"]["completed_cycles"] = 23
    schema_gate = {"stable_errors": stable_errors, "corruption_detected": bool(list(Draft202012Validator(schema).iter_errors(corrupt)))}
    schema_gate["passed"] = not stable_errors and schema_gate["corruption_detected"]

    expected = config["pre_cleanup_identity"]
    netstat = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, check=True, timeout=20).stdout
    listeners = {str(port): listener_pids(netstat, port) for port in (5037, 5038, 5554, 5555, 8554)}
    processes = {str(pid): process_record(pid) for pid in (expected["adb_5037_pid"], expected["adb_5038_pid"], expected["launcher_pid"], expected["qemu_pid"], *expected["excluded_runtime_pids"])}
    runtime_preflight = {
        "listeners": listeners, "processes": processes,
        "output_root_exists": (REPOSITORY_ROOT / config["output_root"]).exists(),
        "runtime_log_root_exists": (REPOSITORY_ROOT / config["runtime_log_root"]).exists(),
        "generation_calls": 0, "device_mutations": 0, "restart_attempts": 0,
    }
    runtime_preflight["passed"] = (
        listeners["5037"] == [expected["adb_5037_pid"]]
        and listeners["5038"] == [expected["adb_5038_pid"]]
        and all(listeners[str(port)] == [expected["qemu_pid"]] for port in (5554, 5555, 8554))
        and all(processes.values())
        and not runtime_preflight["output_root_exists"]
        and not runtime_preflight["runtime_log_root_exists"]
    )
    watched = config["legacy_frozen_log_watch"]
    watch_path = REPOSITORY_ROOT / watched["path"]
    legacy_log_gate = {"path": watched["path"], "bytes": watch_path.stat().st_size, "sha256": digest_path(watch_path)}
    legacy_log_gate["passed"] = legacy_log_gate["bytes"] == watched["bytes"] and legacy_log_gate["sha256"] == watched["sha256"]
    audit_errors = manifest_errors(REPOSITORY_ROOT / config["audit_root"])
    protected = {relative: digest_path(REPOSITORY_ROOT / relative) for relative in config["protected_wip"]}
    protected_pass = protected == config["protected_wip"]
    binary_hashes = {config["runtime"][name]: digest_path(REPOSITORY_ROOT / config["runtime"][name]) for name in ("adb_binary", "emulator_launcher", "qemu_binary", "avd_ini", "avd_config")}
    expected_hashes = {config["runtime"][name]: config["runtime"][f"{name}_sha256"] for name in ("adb_binary", "emulator_launcher", "qemu_binary", "avd_ini", "avd_config")}

    result = {
        "schema_version": "role_binding_timing.infra_m2.offline_gates.v1", "created_at": datetime.now(timezone.utc).isoformat(),
        "generation_calls": 0, "held_out_captures": 0, "device_mutations": 0, "restart_attempts": 0,
        "compile_pass": compile_pass, "focused_pass": focused_pass, "namespace_pass": namespace_pass,
        "full_regression_accepted": full_accepted, "full_regression_expected_only_failure": EXPECTED_FULL_FAILURE, "full_regression_observed_failed_nodes": failed_nodes,
        "source_gate": source_gate, "schema_gate": schema_gate, "runtime_preflight": runtime_preflight,
        "legacy_frozen_log_gate": legacy_log_gate, "audit_manifest_errors": audit_errors,
        "binary_hashes": binary_hashes, "binary_hashes_pass": binary_hashes == expected_hashes,
        "protected_wip": protected, "protected_wip_pass": protected_pass,
        "gates": [{key: value for key, value in gate.items() if key != "stdout_text"} for gate in gates],
    }
    result["overall_pass"] = all((compile_pass, focused_pass, namespace_pass, full_accepted, source_gate["passed"], schema_gate["passed"], runtime_preflight["passed"], legacy_log_gate["passed"], not audit_errors, result["binary_hashes_pass"], protected_pass))
    partial, final = OUTPUT_ROOT / "offline_gate_result.json.partial", OUTPUT_ROOT / "offline_gate_result.json"
    partial.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, final)
    print(json.dumps({"overall_pass": result["overall_pass"], "failed_nodes": failed_nodes, "runtime_preflight": runtime_preflight, "legacy_frozen_log_gate": legacy_log_gate}, sort_keys=True))
    return 0 if result["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
