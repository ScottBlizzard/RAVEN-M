"""Run zero-device-mutation offline gates for INFRA-M7."""

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
OUTPUT_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m7_offline_gates_attempt_02"
CONFIG_PATH = PROJECT_ROOT / "configs/role_binding_timing/infra_m7_runner_adb_authority.json"
KNOWN_FAILURE = "tests/scripts/test_protocol_v2_2_r78_h17_candidate.py::test_r78_candidate_static_manifest_validation_passes"
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.role_binding_timing import infra_m5_process_identity as M5  # noqa: E402
from raven_m.role_binding_timing.infra_m7_adb_authority import build_m7_snapshot  # noqa: E402
from raven_m.role_binding_timing.infra_m7_terminal import minimal_completion  # noqa: E402


def load_runner() -> Any:
    path = PROJECT_ROOT / "scripts/run_role_binding_timing_infra_m7.py"
    spec = importlib.util.spec_from_file_location("m7_runner_for_offline_gates", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("M7_RUNNER_LOAD_FAILURE")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save(path: Path, value: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(value)
    return {"path": path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": len(value), "sha256": sha256(value).hexdigest()}


def run_gate(gate_id: str, command: list[str], cwd: Path, *, timeout: float = 1200) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(command, cwd=cwd, capture_output=True, timeout=timeout)
        return {"gate_id": gate_id, "command": command, "returncode": completed.returncode,
                "timed_out": False, "wall_time_seconds": time.monotonic() - started,
                "stdout": save(OUTPUT_ROOT / gate_id / "stdout.bin", completed.stdout),
                "stderr": save(OUTPUT_ROOT / gate_id / "stderr.bin", completed.stderr)}
    except subprocess.TimeoutExpired as exc:
        return {"gate_id": gate_id, "command": command, "returncode": None,
                "timed_out": True, "wall_time_seconds": time.monotonic() - started,
                "stdout": save(OUTPUT_ROOT / gate_id / "stdout.bin", exc.stdout or b""),
                "stderr": save(OUTPUT_ROOT / gate_id / "stderr.bin", exc.stderr or b"")}


def completion_sample() -> dict[str, Any]:
    value = minimal_completion(run_id="offline", status="RUNTIME_UNSTABLE", first_edge="OFFLINE")
    value.update(last_completed_phase="framework", journal_entry_count=4, journal_terminal_event_present=True)
    return value


def schema_gate(config: dict[str, Any]) -> dict[str, Any]:
    schema = json.loads((REPOSITORY_ROOT / config["schema"]).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema); sample = completion_sample()
    errors = [item.message for item in validator.iter_errors(sample)]
    corruptions = []
    for name, mutate in (
        ("generation_call", lambda value: value.update(generation_calls=1)),
        ("held_out_capture", lambda value: value.update(held_out_captures=1)),
        ("protected_drift", lambda value: value.update(protected_wip_unchanged=False)),
        ("runner_claim_missing", lambda value: value["claim_evidence"].pop("runner_adb_authority_qualified")),
        ("hypothesis_claim", lambda value: value["claim_evidence"].update(role_binding_hypothesis_tested=True)),
    ):
        corrupt = json.loads(json.dumps(sample)); mutate(corrupt)
        corruptions.append({"name": name, "detected": bool(list(validator.iter_errors(corrupt)))})
    false_pass = json.loads(json.dumps(sample)); false_pass.update(status="PASS_12_OF_12_DEV", first_broken_edge=None)
    corruptions.append({"name": "false_pass", "detected": bool(list(validator.iter_errors(false_pass)))})
    return {"passed": not errors and all(item["detected"] for item in corruptions), "errors": errors, "corruptions": corruptions}


def source_gate() -> dict[str, Any]:
    paths = [
        PROJECT_ROOT / "src/raven_m/role_binding_timing/infra_m7_adb_authority.py",
        PROJECT_ROOT / "src/raven_m/role_binding_timing/infra_m7_terminal.py",
        PROJECT_ROOT / "scripts/run_role_binding_timing_infra_m7.py",
        PROJECT_ROOT / "scripts/finalize_role_binding_timing_infra_m7.py",
    ]
    values = {path.name: path.read_text(encoding="utf-8") for path in paths}
    joined = "\n".join(values.values())
    production = values["infra_m7_adb_authority.py"] + values["run_role_binding_timing_infra_m7.py"]
    checks = {
        "generic_no_subcommand_allowlist": "ordinary_subcommand_allowlist" not in production,
        "exact_global_port_prefix": 'argv[1].casefold() == "-p"' in production and 'argv[2] != "5038"' in production,
        "direct_runner_parent": 'record.get("ppid") != self.runner_record.get("pid")' in production,
        "bounded_active_lifetime": "RUNNER_CLIENT_LIFETIME_EXCEEDED" in production,
        "all_listener_evidence": "all_tcp_listener_ports_by_pid" in production and "history_max_listener_ports" in production,
        "server_phase_separate": "RUNNER_CLIENT_START_SERVER_PHASE" in production and "RUNNER_CLIENT_KILL_SERVER_PHASE" in production,
        "server_mode_forbidden": "RUNNER_CLIENT_SERVER_MODE_FORBIDDEN" in production,
        "zero_5037_command": '"-P", "5037"' not in production and "adb_prefix(config, 5037" not in production,
        "no_app_task_or_pid_branch": all(token not in production for token in ("com.android.settings", "deskclock", "org.tasks", "broccoli", "H17", "r79", "11316", "17716")),
        "independent_terminal": "DUPLICATE_TERMINAL_COMPLETION" in values["infra_m7_terminal.py"],
        "no_model_client": all(token not in joined for token in ("requests.post(", "openai.", "/generate", "model_client")),
    }
    checks["passed"] = all(checks.values()); return checks


def invocation_audit_gate() -> dict[str, Any]:
    path = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m7_runner_adb_authority_audit/adb_authority_audit.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    expected = {"all_explicit_single_5038": True, "all_locked_binary_path": True,
                "forbidden_server_mode": 0, "generic_clients": 4, "server_lifecycle": 2, "unique_argv": 6}
    observed = value.get("observed_summary")
    classes = {item["classification"] for item in value["observed_m6_adb_argv"]}
    expected_classes = {"GENERIC_RUNNER_OWNED_CLIENT", "SERVER_LIFECYCLE_START_LAUNCH_ONLY", "SERVER_LIFECYCLE_STOP_CLEANUP_ONLY"}
    return {"passed": observed == expected and classes == expected_classes,
            "source_sha256": sha256(path.read_bytes()).hexdigest(), "observed": observed,
            "classifications": sorted(classes)}


def runtime_preflight(config: dict[str, Any]) -> dict[str, Any]:
    snapshot = build_m7_snapshot(gate="m7_offline_preflight", sequence=0, cache=M5.ExecutableHashCache(), raw_netstat=M5.netstat_bytes())
    project_paths = {M5.normalized_path(spec["path"]) for spec in config["process_identity"]["binaries"].values()
                     if isinstance(spec, dict) and "path" in spec and Path(spec["path"]).name.casefold() in M5.RELEVANT_NAMES}
    owned = [record for record in snapshot["structural_processes"] if M5.normalized_path(record.get("exe")) in project_paths]
    issues = []
    if any(snapshot["listeners"][str(port)] for port in (5037, 5038, 5554, 5555, 8554)): issues.append("LISTENER_PRESENT")
    if owned: issues.append("PROJECT_RUNTIME_PROCESS_PRESENT")
    if (REPOSITORY_ROOT / config["output_root"]).exists(): issues.append("OUTPUT_ROOT_EXISTS")
    temp_parent = Path(config["log_lifecycle"]["temp_parent"])
    patterns = [f"{config['log_lifecycle']['temp_prefix']}*", "infra_m7_resolved_config_*"]
    residue = sorted({str(path) for pattern in patterns for path in temp_parent.glob(pattern)}) if temp_parent.exists() else []
    if residue: issues.append("TEMP_RESIDUE")
    return {"passed": not issues, "issues": issues, "snapshot": snapshot, "project_owned_records": owned, "temp_residue": residue}


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise RuntimeError("M7_OFFLINE_ATTEMPT_02_ROOT_NOT_FRESH")
    OUTPUT_ROOT.mkdir(parents=True); (OUTPUT_ROOT / ".gitattributes").write_text("*.bin binary\n", encoding="ascii")
    overlay = json.loads(CONFIG_PATH.read_text(encoding="utf-8")); config = load_runner().resolve_overlay(CONFIG_PATH)
    gates = [
        run_gate("compile", [str(PYTHON), "-m", "py_compile", "src/raven_m/role_binding_timing/infra_m7_adb_authority.py", "src/raven_m/role_binding_timing/infra_m7_terminal.py", "scripts/run_role_binding_timing_infra_m7.py", "scripts/finalize_role_binding_timing_infra_m7.py", "scripts/run_role_binding_timing_infra_m7_offline_gates.py"], PROJECT_ROOT),
        run_gate("focused_m7", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing/test_infra_m7_adb_authority.py", "tests/role_binding_timing/test_infra_m7_runner_terminal.py", "-q", "--color=no"], PROJECT_ROOT),
        run_gate("focused_m6", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing/test_infra_m6_display_observability.py", "-q", "--color=no"], PROJECT_ROOT),
        run_gate("m5_identity", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing/test_infra_m5_process_identity.py", "-q", "--color=no"], PROJECT_ROOT),
        run_gate("terminal_accounting", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing/test_infra_m4_terminal_accounting.py", "-q", "--color=no"], PROJECT_ROOT),
        run_gate("namespace", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing", "-q", "--color=no"], PROJECT_ROOT),
        run_gate("full_regression", [str(PYTHON), "-m", "pytest", "tests", "-q", "--color=no"], PROJECT_ROOT),
    ]
    full_text = (OUTPUT_ROOT / "full_regression/stdout.bin").read_text(encoding="utf-8", errors="replace")
    failed_nodes = sorted(set(line.split()[1] for line in full_text.splitlines() if line.startswith("FAILED ")))
    full_accepted = gates[6]["returncode"] == 1 and failed_nodes == [KNOWN_FAILURE]
    protected = {name: sha256((REPOSITORY_ROOT / name).read_bytes()).hexdigest() for name in config["protected_wip"]}
    runtime = config["runtime"]
    binary_hashes = {key: sha256((REPOSITORY_ROOT / runtime[key]).read_bytes()).hexdigest()
                     for key in ("python", "adb_binary", "emulator_launcher", "qemu_binary", "avd_ini", "avd_config")}
    expected_hashes = {key: runtime[f"{key}_sha256"] for key in binary_hashes}
    psutil_path = REPOSITORY_ROOT / config["process_identity"]["psutil"]["module"]
    psutil_gate = {"version": M5.psutil.__version__, "sha256": sha256(psutil_path.read_bytes()).hexdigest()}
    psutil_gate["passed"] = (psutil_gate["version"] == config["process_identity"]["psutil"]["version"] and
                             psutil_gate["sha256"] == config["process_identity"]["psutil"]["module_sha256"])
    result = {
        "schema_version": "role_binding_timing.infra_m7.offline_gates.v1", "created_at": utc_now(),
        "generation_calls": 0, "device_mutations": 0, "restart_attempts": 0, "gates": gates,
        "compile_pass": gates[0]["returncode"] == 0, "focused_m7_pass": gates[1]["returncode"] == 0,
        "focused_m6_pass": gates[2]["returncode"] == 0, "m5_identity_pass": gates[3]["returncode"] == 0,
        "terminal_accounting_pass": gates[4]["returncode"] == 0, "namespace_pass": gates[5]["returncode"] == 0,
        "full_regression_accepted": full_accepted, "full_regression_observed_failed_nodes": failed_nodes,
        "full_regression_expected_only_failure": KNOWN_FAILURE, "schema_gate": schema_gate(config),
        "source_gate": source_gate(), "invocation_audit_gate": invocation_audit_gate(),
        "protected_wip": protected, "protected_wip_pass": protected == config["protected_wip"],
        "runtime_preflight": runtime_preflight(config), "binary_hashes": binary_hashes,
        "binary_hashes_pass": binary_hashes == expected_hashes, "psutil_gate": psutil_gate,
        "base_config": {"path": overlay["base_config"], "expected_sha256": overlay["base_config_sha256"],
                        "observed_sha256": sha256((REPOSITORY_ROOT / overlay["base_config"]).read_bytes()).hexdigest()},
    }
    result["overall_pass"] = all((result["compile_pass"], result["focused_m7_pass"], result["focused_m6_pass"],
        result["m5_identity_pass"], result["terminal_accounting_pass"], result["namespace_pass"],
        result["full_regression_accepted"], result["schema_gate"]["passed"], result["source_gate"]["passed"],
        result["invocation_audit_gate"]["passed"], result["protected_wip_pass"], result["runtime_preflight"]["passed"],
        result["binary_hashes_pass"], result["psutil_gate"]["passed"],
        result["base_config"]["expected_sha256"] == result["base_config"]["observed_sha256"]))
    (OUTPUT_ROOT / "offline_gate_result.json").write_bytes((json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({"overall_pass": result["overall_pass"], "failed_nodes": failed_nodes,
                      "runtime_issues": result["runtime_preflight"]["issues"], "source_gate": result["source_gate"]}, indent=2))
    return 0 if result["overall_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
