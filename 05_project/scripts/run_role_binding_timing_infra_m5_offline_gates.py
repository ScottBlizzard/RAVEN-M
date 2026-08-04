"""Run zero-device-mutation offline gates for INFRA-M5."""

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
OUTPUT_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m5_offline_gates"
CONFIG_PATH = PROJECT_ROOT / "configs/role_binding_timing/infra_m5_process_identity_semantics.json"
KNOWN_FAILURE = "tests/scripts/test_protocol_v2_2_r78_h17_candidate.py::test_r78_candidate_static_manifest_validation_passes"
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.role_binding_timing import infra_m5_process_identity as M5  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def save(path: Path, value: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    return {
        "path": path.relative_to(REPOSITORY_ROOT).as_posix(),
        "bytes": len(value), "sha256": digest(value),
    }


def run_gate(gate_id: str, command: list[str], cwd: Path) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(command, cwd=cwd, capture_output=True, timeout=900)
        return {
            "gate_id": gate_id, "command": command,
            "returncode": completed.returncode, "timed_out": False,
            "wall_time_seconds": time.monotonic() - started,
            "stdout": save(OUTPUT_ROOT / gate_id / "stdout.bin", completed.stdout),
            "stderr": save(OUTPUT_ROOT / gate_id / "stderr.bin", completed.stderr),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "gate_id": gate_id, "command": command,
            "returncode": None, "timed_out": True,
            "wall_time_seconds": time.monotonic() - started,
            "stdout": save(OUTPUT_ROOT / gate_id / "stdout.bin", exc.stdout or b""),
            "stderr": save(OUTPUT_ROOT / gate_id / "stderr.bin", exc.stderr or b""),
        }


def schema_gate(config: dict[str, Any]) -> dict[str, Any]:
    schema = json.loads((REPOSITORY_ROOT / config["schema"]).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    sample = {
        "schema_version": "role_binding_timing.infra_m5.completion.v1",
        "terminal_mode": "rich", "status": "PROCESS_IDENTITY_FAILED",
        "run_id": "offline", "first_broken_edge": "OFFLINE",
        "last_completed_phase": "launch", "journal_entry_count": 4,
        "journal_terminal_event_present": True,
        "generation_calls": 0, "model_tokens": 0, "held_out_captures": 0,
        "process_identity": {}, "runtime": {},
        "burn_in": {"passed": False, "required_cycles": 24, "completed_cycles": 0, "passed_cycles": 0, "elapsed_seconds": 0, "records": []},
        "a11y": {"authorized": False, "passed": False, "settings": {"required": 3, "completed": 0, "passed": 0}, "grid": {"required": 12, "completed": 0, "passed": 0}},
        "cleanup": {"passed": False},
        "log_seal": {"passed": False, "records": [], "temporary_root_removed": False},
        "protected_wip_unchanged": True,
        "claim_evidence": {"process_identity_qualified": False, "exclusive_5038_registration": False, "burn_in_qualified": False, "a11y_tested": False, "a11y_qualified": False, "v0_3_preparation_authorized": False, "held_out_tested": False, "role_binding_hypothesis_tested": False},
    }
    errors = [item.message for item in validator.iter_errors(sample)]
    corruptions = []
    for name, mutate in (
        ("generation_call", lambda value: value.update(generation_calls=1)),
        ("held_out_capture", lambda value: value.update(held_out_captures=1)),
        ("protected_drift", lambda value: value.update(protected_wip_unchanged=False)),
        ("terminal_missing", lambda value: value.update(journal_terminal_event_present=False)),
        ("held_out_claim", lambda value: value["claim_evidence"].update(held_out_tested=True)),
    ):
        corrupt = json.loads(json.dumps(sample)); mutate(corrupt)
        corruptions.append({"name": name, "detected": bool(list(validator.iter_errors(corrupt)))})
    false_pass = json.loads(json.dumps(sample))
    false_pass.update(status="PASS_12_OF_12_DEV", first_broken_edge=None)
    corruptions.append({"name": "false_pass", "detected": bool(list(validator.iter_errors(false_pass)))})
    return {"passed": not errors and all(item["detected"] for item in corruptions), "errors": errors, "corruptions": corruptions}


def source_gate(config: dict[str, Any]) -> dict[str, Any]:
    names = [
        "scripts/run_role_binding_timing_infra_m5.py",
        "scripts/finalize_role_binding_timing_infra_m5.py",
        "scripts/run_role_binding_timing_infra_m5_offline_gates.py",
        "src/raven_m/role_binding_timing/infra_m5_process_identity.py",
    ]
    sources = {name: (PROJECT_ROOT / name).read_text(encoding="utf-8") for name in names}
    runner = sources[names[0]]
    production_joined = "\n".join(
        sources[name] for name in names if not name.endswith("_offline_gates.py")
    ) + "\n" + CONFIG_PATH.read_text(encoding="utf-8")
    checks = {
        "single_local_identity_policy": "class StructuralIdentityPolicy" in sources[names[3]],
        "continuous_history": "class ContinuousProcessHistory" in sources[names[3]],
        "trigger_snapshot_write_once": "first_process_identity_failure.json" in sources[names[3]] and "if not self.first_failure.exists()" in sources[names[3]],
        "pid_plus_start_identity": "pid@create_time" in (REPOSITORY_ROOT / "04_protocols/role_binding_timing/INFRA_M5_PROCESS_IDENTITY_SEMANTICS_V1.md").read_text(encoding="utf-8"),
        "no_static_excluded_equality": "excluded_runtime_pids] !=" not in production_joined and "excluded_runtime_pids\"] !=" not in production_joined,
        "no_pid_exception": "11316" not in runner and "17716" not in runner,
        "no_5037_adb_command": "adb_prefix(config, 5037" not in runner and "-P\", \"5037" not in runner,
        "zero_generation_boundary": '"generation_calls_authorized": 0' in production_joined,
        "external_log_lifecycle": "create_live_root" in runner and "seal_live_logs" in runner,
        "independent_finalizer": "invoke_finalizer" in runner and "finalize_m5_completion" in sources[names[1]],
        "partial_core_cleanup_safe": "EMULATOR_PRESENT_WITHOUT_QUALIFIED_IDENTITY" in runner and "ADB_PRESENT_WITHOUT_QUALIFIED_IDENTITY" in runner,
        "no_prior_frozen_log_append": "infra_m1_maintenance_burnin/maintenance/start/emulator.stdout.bin" not in runner,
        "no_model_client": all(token not in production_joined for token in ("requests.post(", "openai.", "/generate", "model_client")),
    }
    checks["passed"] = all(checks.values())
    return checks


def runtime_preflight(config: dict[str, Any]) -> dict[str, Any]:
    cache = M5.ExecutableHashCache()
    raw_netstat = M5.netstat_bytes()
    snapshot = M5.build_snapshot(gate="offline_preflight", sequence=0, cache=cache, raw_netstat=raw_netstat)
    project_paths = {
        M5.normalized_path(spec["path"])
        for spec in config["process_identity"]["binaries"].values()
        if isinstance(spec, dict) and "path" in spec and Path(spec["path"]).name.casefold() in M5.RELEVANT_NAMES
    }
    owned = [
        record for record in snapshot["structural_processes"]
        if M5.normalized_path(record.get("exe")) in project_paths
    ]
    issues = []
    if any(snapshot["listeners"][str(port)] for port in (5037, 5038, 5554, 5555, 8554)):
        issues.append("LISTENER_PRESENT")
    if owned:
        issues.append("PROJECT_RUNTIME_PROCESS_PRESENT")
    output = REPOSITORY_ROOT / config["output_root"]
    if output.exists():
        issues.append("OUTPUT_ROOT_EXISTS")
    temp_parent = Path(config["log_lifecycle"]["temp_parent"])
    residue = sorted(path.name for path in temp_parent.glob(f"{config['log_lifecycle']['temp_prefix']}*")) if temp_parent.exists() else []
    if residue:
        issues.append("TEMP_RESIDUE")
    return {"passed": not issues, "issues": issues, "snapshot": snapshot, "project_owned_records": owned, "temp_residue": residue}


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise RuntimeError("M5_OFFLINE_GATE_ROOT_NOT_FRESH")
    OUTPUT_ROOT.mkdir(parents=True)
    (OUTPUT_ROOT / ".gitattributes").write_text("*.bin binary\n", encoding="ascii")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    gates = [
        run_gate("compile", [str(PYTHON), "-m", "py_compile", "src/raven_m/role_binding_timing/infra_m5_process_identity.py", "scripts/finalize_role_binding_timing_infra_m5.py", "scripts/run_role_binding_timing_infra_m5.py", "scripts/run_role_binding_timing_infra_m5_offline_gates.py"], PROJECT_ROOT),
        run_gate("focused_m5", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing/test_infra_m5_process_identity.py", "-q", "--color=no"], PROJECT_ROOT),
        run_gate("terminal_accounting", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing/test_infra_m4_terminal_accounting.py", "-q", "--color=no"], PROJECT_ROOT),
        run_gate("namespace", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing", "-q", "--color=no"], PROJECT_ROOT),
        run_gate("full_regression", [str(PYTHON), "-m", "pytest", "tests", "-q", "--color=no"], PROJECT_ROOT),
    ]
    full_text = (OUTPUT_ROOT / "full_regression/stdout.bin").read_text(encoding="utf-8", errors="replace")
    failed_nodes = sorted(set(line.split()[1] for line in full_text.splitlines() if line.startswith("FAILED ")))
    full_accepted = gates[4]["returncode"] == 1 and failed_nodes == [KNOWN_FAILURE]
    protected = {name: sha256((REPOSITORY_ROOT / name).read_bytes()).hexdigest() for name in config["protected_wip"]}
    runtime = config["runtime"]
    binary_hashes = {
        key: sha256((REPOSITORY_ROOT / runtime[key]).read_bytes()).hexdigest()
        for key in ("python", "adb_binary", "emulator_launcher", "qemu_binary", "avd_ini", "avd_config")
    }
    expected_hashes = {key: runtime[f"{key}_sha256"] for key in binary_hashes}
    psutil_path = REPOSITORY_ROOT / config["process_identity"]["psutil"]["module"]
    psutil_gate = {
        "version": M5.psutil.__version__, "sha256": sha256(psutil_path.read_bytes()).hexdigest(),
        "passed": M5.psutil.__version__ == config["process_identity"]["psutil"]["version"] and sha256(psutil_path.read_bytes()).hexdigest() == config["process_identity"]["psutil"]["module_sha256"],
    }
    legacy_path = REPOSITORY_ROOT / "05_project/artifacts/role_binding_timing/infra_m1_maintenance_burnin/maintenance/start/emulator.stdout.bin"
    legacy = {"bytes": legacy_path.stat().st_size, "sha256": sha256(legacy_path.read_bytes()).hexdigest()}
    legacy["passed"] = legacy == {"bytes": 9590, "sha256": "ffddf9d0862f8f3e58b424e1e8f774e546875634a0ba81f5e720333284b48b1c"}
    result = {
        "schema_version": "role_binding_timing.infra_m5.offline_gates.v1",
        "created_at": utc_now(), "generation_calls": 0, "device_mutations": 0, "restart_attempts": 0,
        "gates": gates,
        "compile_pass": gates[0]["returncode"] == 0,
        "focused_m5_pass": gates[1]["returncode"] == 0,
        "terminal_accounting_pass": gates[2]["returncode"] == 0,
        "namespace_pass": gates[3]["returncode"] == 0,
        "full_regression_accepted": full_accepted,
        "full_regression_observed_failed_nodes": failed_nodes,
        "full_regression_expected_only_failure": KNOWN_FAILURE,
        "schema_gate": schema_gate(config), "source_gate": source_gate(config),
        "protected_wip": protected, "protected_wip_pass": protected == config["protected_wip"],
        "runtime_preflight": runtime_preflight(config),
        "binary_hashes": binary_hashes, "binary_hashes_pass": binary_hashes == expected_hashes,
        "psutil_gate": psutil_gate, "legacy_restore_observation": legacy,
    }
    result["overall_pass"] = all((
        result["compile_pass"], result["focused_m5_pass"], result["terminal_accounting_pass"],
        result["namespace_pass"], result["full_regression_accepted"],
        result["schema_gate"]["passed"], result["source_gate"]["passed"],
        result["protected_wip_pass"], result["runtime_preflight"]["passed"],
        result["binary_hashes_pass"], result["psutil_gate"]["passed"], legacy["passed"],
    ))
    (OUTPUT_ROOT / "offline_gate_result.json").write_bytes((json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({"overall_pass": result["overall_pass"], "failed_nodes": failed_nodes, "runtime_issues": result["runtime_preflight"]["issues"], "source_gate": result["source_gate"]}, indent=2))
    return 0 if result["overall_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
