"""Run zero-device-mutation offline gates for INFRA-M6."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
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
OUTPUT_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m6_offline_gates_attempt_02"
CONFIG_PATH = PROJECT_ROOT / "configs/role_binding_timing/infra_m6_display_observability.json"
KNOWN_FAILURE = "tests/scripts/test_protocol_v2_2_r78_h17_candidate.py::test_r78_candidate_static_manifest_validation_passes"
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.role_binding_timing import infra_m5_process_identity as M5  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save(path: Path, value: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    return {"path": path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": len(value), "sha256": sha256(value).hexdigest()}


def run_gate(gate_id: str, command: list[str], cwd: Path, *, timeout: float = 1200) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(command, cwd=cwd, capture_output=True, timeout=timeout)
        return {
            "gate_id": gate_id, "command": command, "returncode": completed.returncode,
            "timed_out": False, "wall_time_seconds": time.monotonic() - started,
            "stdout": save(OUTPUT_ROOT / gate_id / "stdout.bin", completed.stdout),
            "stderr": save(OUTPUT_ROOT / gate_id / "stderr.bin", completed.stderr),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "gate_id": gate_id, "command": command, "returncode": None,
            "timed_out": True, "wall_time_seconds": time.monotonic() - started,
            "stdout": save(OUTPUT_ROOT / gate_id / "stdout.bin", exc.stdout or b""),
            "stderr": save(OUTPUT_ROOT / gate_id / "stderr.bin", exc.stderr or b""),
        }


def completion_sample() -> dict[str, Any]:
    return {
        "schema_version": "role_binding_timing.infra_m6.completion.v1",
        "terminal_mode": "rich", "status": "RUNTIME_UNSTABLE", "run_id": "offline",
        "first_broken_edge": "OFFLINE", "last_completed_phase": "framework",
        "journal_entry_count": 4, "journal_terminal_event_present": True,
        "generation_calls": 0, "model_tokens": 0, "held_out_captures": 0,
        "process_identity": {}, "runtime": {"framework": {"passed": False}},
        "burn_in": {"passed": False, "required_cycles": 24, "completed_cycles": 0, "passed_cycles": 0, "elapsed_seconds": 0, "records": []},
        "a11y": {"authorized": False, "passed": False, "settings": {"required": 3, "completed": 0, "passed": 0}, "grid": {"required": 12, "completed": 0, "passed": 0}},
        "cleanup": {"passed": False}, "log_seal": {"passed": False},
        "protected_wip_unchanged": True,
        "claim_evidence": {
            "display_quorum_qualified": False, "process_identity_qualified": False,
            "exclusive_5038_registration": False, "burn_in_qualified": False,
            "a11y_tested": False, "a11y_qualified": False,
            "v0_3_preparation_authorized": False, "held_out_tested": False,
            "role_binding_hypothesis_tested": False,
        },
    }


def schema_gate(config: dict[str, Any]) -> dict[str, Any]:
    schema = json.loads((REPOSITORY_ROOT / config["schema"]).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    sample = completion_sample()
    errors = [item.message for item in validator.iter_errors(sample)]
    corruptions = []
    for name, mutate in (
        ("generation_call", lambda value: value.update(generation_calls=1)),
        ("held_out_capture", lambda value: value.update(held_out_captures=1)),
        ("protected_drift", lambda value: value.update(protected_wip_unchanged=False)),
        ("display_claim_missing", lambda value: value["claim_evidence"].pop("display_quorum_qualified")),
        ("hypothesis_claim", lambda value: value["claim_evidence"].update(role_binding_hypothesis_tested=True)),
    ):
        corrupt = json.loads(json.dumps(sample)); mutate(corrupt)
        corruptions.append({"name": name, "detected": bool(list(validator.iter_errors(corrupt)))})
    false_pass = json.loads(json.dumps(sample))
    false_pass.update(status="PASS_12_OF_12_DEV", first_broken_edge=None)
    corruptions.append({"name": "false_pass", "detected": bool(list(validator.iter_errors(false_pass)))})
    return {"passed": not errors and all(item["detected"] for item in corruptions), "errors": errors, "corruptions": corruptions}


def source_gate() -> dict[str, Any]:
    paths = [
        PROJECT_ROOT / "src/raven_m/role_binding_timing/infra_m6_display_observability.py",
        PROJECT_ROOT / "src/raven_m/role_binding_timing/infra_m6_terminal.py",
        PROJECT_ROOT / "scripts/run_role_binding_timing_infra_m6.py",
        PROJECT_ROOT / "scripts/finalize_role_binding_timing_infra_m6.py",
    ]
    values = {path.name: path.read_text(encoding="utf-8") for path in paths}
    joined = "\n".join(values.values())
    production = values["infra_m6_display_observability.py"] + values["run_role_binding_timing_infra_m6.py"]
    checks = {
        "single_display_quorum": "def evaluate_display_quorum" in values["infra_m6_display_observability.py"],
        "required_planes_conjunctive": 'required = ("display_service", "power", "window", "screencap")' in values["infra_m6_display_observability.py"],
        "missing_legacy_marker_not_authority": '"legacy_marker_authoritative": False' in values["infra_m6_display_observability.py"],
        "screenshot_not_solo_authority": '"screenshot_alone_authoritative": False' in values["infra_m6_display_observability.py"],
        "cleanup_phase_only": 'if phase == "cleanup"' in values["infra_m6_display_observability.py"],
        "exact_shutdown_parent": '"SHUTDOWN_CMD_PARENT"' in values["infra_m6_display_observability.py"],
        "zero_5037_command": "adb_prefix(config, 5037" not in production and '"-P", "5037"' not in production,
        "no_app_or_task_branch_in_m6_source": all(token not in production for token in ("com.android.settings", "deskclock", "org.tasks", "broccoli", "H17", "r79")),
        "independent_terminal": "finalize_completion" in values["infra_m6_terminal.py"] and "DUPLICATE_TERMINAL_COMPLETION" in values["infra_m6_terminal.py"],
        "no_model_client": all(token not in joined for token in ("requests.post(", "openai.", "/generate", "model_client")),
    }
    checks["passed"] = all(checks.values())
    return checks


def runtime_preflight(config: dict[str, Any]) -> dict[str, Any]:
    cache = M5.ExecutableHashCache()
    snapshot = M5.build_snapshot(gate="m6_offline_preflight", sequence=0, cache=cache, raw_netstat=M5.netstat_bytes())
    project_paths = {
        M5.normalized_path(spec["path"])
        for spec in config["process_identity"]["binaries"].values()
        if isinstance(spec, dict) and "path" in spec and Path(spec["path"]).name.casefold() in M5.RELEVANT_NAMES
    }
    owned = [record for record in snapshot["structural_processes"] if M5.normalized_path(record.get("exe")) in project_paths]
    issues = []
    if any(snapshot["listeners"][str(port)] for port in (5037, 5038, 5554, 5555, 8554)):
        issues.append("LISTENER_PRESENT")
    if owned:
        issues.append("PROJECT_RUNTIME_PROCESS_PRESENT")
    if (REPOSITORY_ROOT / config["output_root"]).exists():
        issues.append("OUTPUT_ROOT_EXISTS")
    temp_parent = Path(config["log_lifecycle"]["temp_parent"])
    residue = sorted(path.name for path in temp_parent.glob(f"{config['log_lifecycle']['temp_prefix']}*")) if temp_parent.exists() else []
    if residue:
        issues.append("TEMP_RESIDUE")
    return {"passed": not issues, "issues": issues, "snapshot": snapshot, "project_owned_records": owned, "temp_residue": residue}


def main() -> int:
    resumed_incomplete_root = OUTPUT_ROOT.exists()
    if (OUTPUT_ROOT / "offline_gate_result.json").exists():
        raise RuntimeError("M6_OFFLINE_GATE_ALREADY_COMPLETED")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / ".gitattributes").write_text("*.bin binary\n", encoding="ascii")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    gates = [
        run_gate("compile", [str(PYTHON), "-m", "py_compile", "src/raven_m/role_binding_timing/infra_m6_display_observability.py", "src/raven_m/role_binding_timing/infra_m6_terminal.py", "scripts/run_role_binding_timing_infra_m6.py", "scripts/finalize_role_binding_timing_infra_m6.py", "scripts/run_role_binding_timing_infra_m6_offline_gates.py"], PROJECT_ROOT),
        run_gate("focused_m6", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing/test_infra_m6_display_observability.py", "-q", "--color=no"], PROJECT_ROOT),
        run_gate("m5_identity", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing/test_infra_m5_process_identity.py", "-q", "--color=no"], PROJECT_ROOT),
        run_gate("terminal_accounting", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing/test_infra_m4_terminal_accounting.py", "-q", "--color=no"], PROJECT_ROOT),
        run_gate("namespace", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing", "-q", "--color=no"], PROJECT_ROOT),
        run_gate("full_regression", [str(PYTHON), "-m", "pytest", "tests", "-q", "--color=no"], PROJECT_ROOT),
    ]
    full_text = (OUTPUT_ROOT / "full_regression/stdout.bin").read_text(encoding="utf-8", errors="replace")
    failed_nodes = sorted(set(line.split()[1] for line in full_text.splitlines() if line.startswith("FAILED ")))
    full_accepted = gates[5]["returncode"] == 1 and failed_nodes == [KNOWN_FAILURE]
    protected = {name: sha256((REPOSITORY_ROOT / name).read_bytes()).hexdigest() for name in config["protected_wip"]}
    runtime = config["runtime"]
    binary_hashes = {key: sha256((REPOSITORY_ROOT / runtime[key]).read_bytes()).hexdigest() for key in ("python", "adb_binary", "emulator_launcher", "qemu_binary", "avd_ini", "avd_config")}
    expected_hashes = {key: runtime[f"{key}_sha256"] for key in binary_hashes}
    psutil_path = REPOSITORY_ROOT / config["process_identity"]["psutil"]["module"]
    psutil_gate = {
        "version": M5.psutil.__version__, "sha256": sha256(psutil_path.read_bytes()).hexdigest(),
        "passed": M5.psutil.__version__ == config["process_identity"]["psutil"]["version"] and sha256(psutil_path.read_bytes()).hexdigest() == config["process_identity"]["psutil"]["module_sha256"],
    }
    predecessor_paths = [
        "05_project/src/raven_m/role_binding_timing/infra_m5_process_identity.py",
        "05_project/scripts/run_role_binding_timing_infra_m5.py",
        "05_project/artifacts/role_binding_timing/infra_m5_process_identity_semantics/qualification_completion.json",
    ]
    predecessor = {path: sha256((REPOSITORY_ROOT / path).read_bytes()).hexdigest() for path in predecessor_paths}
    result = {
        "schema_version": "role_binding_timing.infra_m6.offline_gates.v1",
        "created_at": utc_now(), "generation_calls": 0, "device_mutations": 0, "restart_attempts": 0,
        "resumed_incomplete_root": resumed_incomplete_root,
        "gates": gates,
        "compile_pass": gates[0]["returncode"] == 0,
        "focused_m6_pass": gates[1]["returncode"] == 0,
        "m5_identity_pass": gates[2]["returncode"] == 0,
        "terminal_accounting_pass": gates[3]["returncode"] == 0,
        "namespace_pass": gates[4]["returncode"] == 0,
        "full_regression_accepted": full_accepted,
        "full_regression_observed_failed_nodes": failed_nodes,
        "full_regression_expected_only_failure": KNOWN_FAILURE,
        "schema_gate": schema_gate(config), "source_gate": source_gate(),
        "protected_wip": protected, "protected_wip_pass": protected == config["protected_wip"],
        "runtime_preflight": runtime_preflight(config),
        "binary_hashes": binary_hashes, "binary_hashes_pass": binary_hashes == expected_hashes,
        "psutil_gate": psutil_gate, "immutable_m5_predecessor_hashes": predecessor,
    }
    result["overall_pass"] = all((
        result["compile_pass"], result["focused_m6_pass"], result["m5_identity_pass"],
        result["terminal_accounting_pass"], result["namespace_pass"], result["full_regression_accepted"],
        result["schema_gate"]["passed"], result["source_gate"]["passed"],
        result["protected_wip_pass"], result["runtime_preflight"]["passed"],
        result["binary_hashes_pass"], result["psutil_gate"]["passed"],
    ))
    (OUTPUT_ROOT / "offline_gate_result.json").write_bytes((json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({"overall_pass": result["overall_pass"], "failed_nodes": failed_nodes, "runtime_issues": result["runtime_preflight"]["issues"], "source_gate": result["source_gate"]}, indent=2))
    return 0 if result["overall_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
