"""Run zero-device-mutation offline gates for INFRA-M9."""

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
OUTPUT_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m9_offline_gates"
CONFIG_PATH = PROJECT_ROOT / "configs/role_binding_timing/infra_m9_authorization_view_separation.json"
KNOWN_FAILURE = "tests/scripts/test_protocol_v2_2_r78_h17_candidate.py::test_r78_candidate_static_manifest_validation_passes"
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.role_binding_timing import infra_m5_process_identity as M5  # noqa: E402
from raven_m.role_binding_timing.infra_m9_authorization_views import build_m9_snapshot, derive_process_views  # noqa: E402
from raven_m.role_binding_timing.infra_m9_terminal import minimal_completion  # noqa: E402


def load_runner() -> Any:
    path = PROJECT_ROOT / "scripts/run_role_binding_timing_infra_m9.py"
    spec = importlib.util.spec_from_file_location("m9_runner_gates", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("M9_RUNNER_LOAD_FAILURE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save(path: Path, value: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    return {
        "path": path.relative_to(REPOSITORY_ROOT).as_posix(),
        "bytes": len(value),
        "sha256": sha256(value).hexdigest(),
    }


def run_gate(name: str, command: list[str], *, timeout: int = 1200) -> dict[str, Any]:
    started = time.monotonic()
    try:
        done = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, timeout=timeout)
        return {
            "gate_id": name,
            "command": command,
            "returncode": done.returncode,
            "timed_out": False,
            "wall_time_seconds": time.monotonic() - started,
            "stdout": save(OUTPUT_ROOT / name / "stdout.bin", done.stdout),
            "stderr": save(OUTPUT_ROOT / name / "stderr.bin", done.stderr),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "gate_id": name,
            "command": command,
            "returncode": None,
            "timed_out": True,
            "wall_time_seconds": time.monotonic() - started,
            "stdout": save(OUTPUT_ROOT / name / "stdout.bin", exc.stdout or b""),
            "stderr": save(OUTPUT_ROOT / name / "stderr.bin", exc.stderr or b""),
        }


def completion_sample() -> dict[str, Any]:
    value = minimal_completion(run_id="offline", status="RUNTIME_UNSTABLE", first_edge="OFFLINE")
    value.update(last_completed_phase="framework", journal_entry_count=4, journal_terminal_event_present=True)
    return value


def schema_gate(config: dict[str, Any]) -> dict[str, Any]:
    schema = json.loads((REPOSITORY_ROOT / config["schema"]).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    sample = completion_sample()
    errors = [item.message for item in validator.iter_errors(sample)]
    corruptions = []
    for name, mutate in (
        ("generation", lambda value: value.update(generation_calls=1)),
        ("held_out", lambda value: value.update(held_out_captures=1)),
        ("protected", lambda value: value.update(protected_wip_unchanged=False)),
        ("view_claim_missing", lambda value: value["claim_evidence"].pop("authorization_view_separation_qualified")),
        ("hypothesis", lambda value: value["claim_evidence"].update(role_binding_hypothesis_tested=True)),
    ):
        value = json.loads(json.dumps(sample))
        mutate(value)
        corruptions.append({"name": name, "detected": bool(list(validator.iter_errors(value)))})
    false_pass = json.loads(json.dumps(sample))
    false_pass.update(status="PASS_12_OF_12_DEV", first_broken_edge=None)
    corruptions.append({"name": "false_pass", "detected": bool(list(validator.iter_errors(false_pass)))})
    return {"passed": not errors and all(item["detected"] for item in corruptions), "errors": errors, "corruptions": corruptions}


def source_gate() -> dict[str, Any]:
    files = [
        PROJECT_ROOT / "src/raven_m/role_binding_timing/infra_m9_authorization_views.py",
        PROJECT_ROOT / "src/raven_m/role_binding_timing/infra_m9_terminal.py",
        PROJECT_ROOT / "scripts/run_role_binding_timing_infra_m9.py",
        PROJECT_ROOT / "scripts/finalize_role_binding_timing_infra_m9.py",
    ]
    values = {path.name: path.read_text(encoding="utf-8") for path in files}
    production = values[files[0].name] + values[files[2].name]
    joined = "\n".join(values.values())
    checks = {
        "four_explicit_views": all(name in production for name in (
            "trusted_runner_root", "project_authorization_candidates",
            "support_only_ancestry_nodes", "unrelated_observed_processes",
        )),
        "full_universe_source": 'snapshot.get("all_processes")' in production,
        "candidate_only_policy": "project_authorization_candidates_only" in production,
        "attached_view_recomputed": "validate_attached_views" in production and "ATTACHED_VIEW_MISMATCH" in production,
        "support_port_veto": "SUPPORT_NODE_OWNS_CONTROLLED_PORT" in production,
        "support_role_veto": "SUPPORT_OR_UNRELATED_GRANTED_ROLE" in production,
        "candidate_only_core_registration": "CORE_PID_IS_SUPPORT_ONLY" in production and "CORE_PID_IS_UNRELATED" in production,
        "runner_exact_identity": all(item in production for item in (
            "TRUSTED_RUNNER_ROOT_PID_REUSE", "TRUSTED_RUNNER_ROOT_PATH_DRIFT", "TRUSTED_RUNNER_ROOT_COMMAND_DRIFT",
        )),
        "all_views_persisted": "derived_process_views.json" in production and '"triggering_snapshot": saved["snapshot"]' in production,
        "zero_5037_command": '"-P", "5037"' not in production and "adb_prefix(config, 5037" not in production,
        "no_pid_app_task_branch": all(token not in production for token in (
            "1912", "1464", "5848", "com.android.settings", "deskclock", "org.tasks", "broccoli", "H17", "r79",
        )),
        "independent_terminal": "DUPLICATE_TERMINAL_COMPLETION" in values[files[1].name],
        "no_model": all(token not in joined for token in ("requests.post(", "openai.", "/generate", "model_client")),
    }
    checks["passed"] = all(checks.values())
    return checks


def audit_gate() -> dict[str, Any]:
    path = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m9_authorization_view_audit/authorization_view_audit.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    return {
        "passed": value["decision"] == "ELIGIBLE_FOR_M9_OFFLINE_IMPLEMENTATION_ONLY"
        and len(value["structural_processes_use_ledger"]) == 9
        and value["direct_evidence"]["structural_projection_count"] == 11
        and value["direct_evidence"]["ancestry_only_count"] == 7,
        "sha256": sha256(path.read_bytes()).hexdigest(),
        "uses": len(value["structural_processes_use_ledger"]),
        "decision": value["decision"],
    }


def runtime_preflight(config: dict[str, Any]) -> dict[str, Any]:
    runner = M5.runner_identity(M5.ExecutableHashCache())
    snap = build_m9_snapshot(
        gate="m9_offline_preflight", sequence=0, cache=M5.ExecutableHashCache(),
        config=config, runner_record=runner, raw_netstat=M5.netstat_bytes(),
    )
    view, _, candidates, view_issues = derive_process_views(snap, config=config, runner_record=runner)
    issues = list(view_issues)
    if any(snap["listeners"][str(port)] for port in (5037, 5038, 5554, 5555, 8554)):
        issues.append("LISTENER_PRESENT")
    if candidates:
        issues.append("PROJECT_AUTHORIZATION_CANDIDATE_PRESENT")
    if (REPOSITORY_ROOT / config["output_root"]).exists():
        issues.append("OUTPUT_ROOT_EXISTS")
    parent = Path(config["log_lifecycle"]["temp_parent"])
    patterns = [f"{config['log_lifecycle']['temp_prefix']}*", "infra_m9_resolved_config_*"]
    residue = sorted({str(path) for pattern in patterns for path in parent.glob(pattern)}) if parent.exists() else []
    if residue:
        issues.append("TEMP_RESIDUE")
    return {
        "passed": not issues,
        "issues": issues,
        "snapshot": snap,
        "derived_view_hashes": view["view_hashes"],
        "candidate_records": list(candidates.values()),
        "temp_residue": residue,
    }


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise RuntimeError("M9_OFFLINE_ROOT_NOT_FRESH")
    OUTPUT_ROOT.mkdir(parents=True)
    (OUTPUT_ROOT / ".gitattributes").write_text("*.bin binary\n", encoding="ascii")
    overlay = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config = load_runner().resolve_overlay(CONFIG_PATH)
    gates = [
        run_gate("compile", [str(PYTHON), "-m", "py_compile", "src/raven_m/role_binding_timing/infra_m9_authorization_views.py", "src/raven_m/role_binding_timing/infra_m9_terminal.py", "scripts/run_role_binding_timing_infra_m9.py", "scripts/finalize_role_binding_timing_infra_m9.py", "scripts/run_role_binding_timing_infra_m9_offline_gates.py"]),
        run_gate("focused_m9", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing/test_infra_m9_authorization_views.py", "tests/role_binding_timing/test_infra_m9_runner_terminal.py", "-q", "--color=no"]),
        run_gate("focused_m8", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing/test_infra_m8_full_snapshot_ancestry.py", "tests/role_binding_timing/test_infra_m8_runner_terminal.py", "-q", "--color=no"]),
        run_gate("focused_m7", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing/test_infra_m7_adb_authority.py", "tests/role_binding_timing/test_infra_m7_runner_terminal.py", "-q", "--color=no"]),
        run_gate("focused_m6", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing/test_infra_m6_display_observability.py", "-q", "--color=no"]),
        run_gate("m5_identity", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing/test_infra_m5_process_identity.py", "-q", "--color=no"]),
        run_gate("terminal_accounting", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing/test_infra_m4_terminal_accounting.py", "-q", "--color=no"]),
        run_gate("namespace", [str(PYTHON), "-m", "pytest", "tests/role_binding_timing", "-q", "--color=no"]),
        run_gate("full_regression", [str(PYTHON), "-m", "pytest", "tests", "-q", "--color=no"]),
    ]
    full = (OUTPUT_ROOT / "full_regression/stdout.bin").read_text(encoding="utf-8", errors="replace")
    failed = sorted(set(line.split()[1] for line in full.splitlines() if line.startswith("FAILED ")))
    full_ok = gates[8]["returncode"] == 1 and failed == [KNOWN_FAILURE]
    protected = {path: sha256((REPOSITORY_ROOT / path).read_bytes()).hexdigest() for path in config["protected_wip"]}
    runtime = config["runtime"]
    hashes = {key: sha256((REPOSITORY_ROOT / runtime[key]).read_bytes()).hexdigest() for key in ("python", "adb_binary", "emulator_launcher", "qemu_binary", "avd_ini", "avd_config")}
    expected = {key: runtime[f"{key}_sha256"] for key in hashes}
    psutil_path = REPOSITORY_ROOT / config["process_identity"]["psutil"]["module"]
    psutil_gate = {"version": M5.psutil.__version__, "sha256": sha256(psutil_path.read_bytes()).hexdigest()}
    psutil_gate["passed"] = psutil_gate["version"] == config["process_identity"]["psutil"]["version"] and psutil_gate["sha256"] == config["process_identity"]["psutil"]["module_sha256"]
    result = {
        "schema_version": "role_binding_timing.infra_m9.offline_gates.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generation_calls": 0,
        "device_mutations": 0,
        "restart_attempts": 0,
        "gates": gates,
        "compile_pass": gates[0]["returncode"] == 0,
        "focused_m9_pass": gates[1]["returncode"] == 0,
        "focused_m8_pass": gates[2]["returncode"] == 0,
        "focused_m7_pass": gates[3]["returncode"] == 0,
        "focused_m6_pass": gates[4]["returncode"] == 0,
        "m5_identity_pass": gates[5]["returncode"] == 0,
        "terminal_accounting_pass": gates[6]["returncode"] == 0,
        "namespace_pass": gates[7]["returncode"] == 0,
        "full_regression_accepted": full_ok,
        "full_regression_observed_failed_nodes": failed,
        "full_regression_expected_only_failure": KNOWN_FAILURE,
        "schema_gate": schema_gate(config),
        "source_gate": source_gate(),
        "audit_gate": audit_gate(),
        "protected_wip": protected,
        "protected_wip_pass": protected == config["protected_wip"],
        "runtime_preflight": runtime_preflight(config),
        "binary_hashes": hashes,
        "binary_hashes_pass": hashes == expected,
        "psutil_gate": psutil_gate,
        "base_config": {
            "path": overlay["base_config"],
            "expected_sha256": overlay["base_config_sha256"],
            "observed_sha256": sha256((REPOSITORY_ROOT / overlay["base_config"]).read_bytes()).hexdigest(),
        },
    }
    result["overall_pass"] = all((
        result["compile_pass"], result["focused_m9_pass"], result["focused_m8_pass"],
        result["focused_m7_pass"], result["focused_m6_pass"], result["m5_identity_pass"],
        result["terminal_accounting_pass"], result["namespace_pass"], result["full_regression_accepted"],
        result["schema_gate"]["passed"], result["source_gate"]["passed"], result["audit_gate"]["passed"],
        result["protected_wip_pass"], result["runtime_preflight"]["passed"], result["binary_hashes_pass"],
        result["psutil_gate"]["passed"], result["base_config"]["expected_sha256"] == result["base_config"]["observed_sha256"],
    ))
    (OUTPUT_ROOT / "offline_gate_result.json").write_bytes((json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({
        "overall_pass": result["overall_pass"],
        "failed_nodes": failed,
        "runtime_issues": result["runtime_preflight"]["issues"],
        "source_gate": result["source_gate"],
    }, indent=2))
    return 0 if result["overall_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
