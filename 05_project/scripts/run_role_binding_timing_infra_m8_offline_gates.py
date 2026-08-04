"""Run zero-device-mutation offline gates for INFRA-M8."""

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

PROJECT_ROOT = Path(__file__).resolve().parents[1]; REPOSITORY_ROOT = PROJECT_ROOT.parent
PYTHON = REPOSITORY_ROOT / "06_local_runtime/envs/androidworld/Scripts/python.exe"
OUTPUT_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m8_offline_gates"
CONFIG_PATH = PROJECT_ROOT / "configs/role_binding_timing/infra_m8_full_snapshot_ancestry.json"
KNOWN_FAILURE = "tests/scripts/test_protocol_v2_2_r78_h17_candidate.py::test_r78_candidate_static_manifest_validation_passes"
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from raven_m.role_binding_timing import infra_m5_process_identity as M5  # noqa: E402
from raven_m.role_binding_timing.infra_m8_full_snapshot_ancestry import build_m8_snapshot  # noqa: E402
from raven_m.role_binding_timing.infra_m8_terminal import minimal_completion  # noqa: E402


def load_runner() -> Any:
    path = PROJECT_ROOT / "scripts/run_role_binding_timing_infra_m8.py"; spec = importlib.util.spec_from_file_location("m8_runner_gates", path)
    if spec is None or spec.loader is None: raise RuntimeError("M8_RUNNER_LOAD_FAILURE")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def save(path: Path, value: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(value)
    return {"path": path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": len(value), "sha256": sha256(value).hexdigest()}


def run_gate(name: str, command: list[str], *, timeout=1200) -> dict[str, Any]:
    started = time.monotonic()
    try:
        done = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, timeout=timeout)
        return {"gate_id": name, "command": command, "returncode": done.returncode, "timed_out": False,
                "wall_time_seconds": time.monotonic() - started, "stdout": save(OUTPUT_ROOT/name/"stdout.bin", done.stdout),
                "stderr": save(OUTPUT_ROOT/name/"stderr.bin", done.stderr)}
    except subprocess.TimeoutExpired as exc:
        return {"gate_id": name, "command": command, "returncode": None, "timed_out": True,
                "wall_time_seconds": time.monotonic() - started, "stdout": save(OUTPUT_ROOT/name/"stdout.bin", exc.stdout or b""),
                "stderr": save(OUTPUT_ROOT/name/"stderr.bin", exc.stderr or b"")}


def completion_sample() -> dict[str, Any]:
    value = minimal_completion(run_id="offline", status="RUNTIME_UNSTABLE", first_edge="OFFLINE")
    value.update(last_completed_phase="framework", journal_entry_count=4, journal_terminal_event_present=True); return value


def schema_gate(config: dict[str, Any]) -> dict[str, Any]:
    validator = Draft202012Validator(json.loads((REPOSITORY_ROOT/config["schema"]).read_text(encoding="utf-8"))); sample = completion_sample()
    errors = [item.message for item in validator.iter_errors(sample)]; corruptions = []
    for name, mutate in (
        ("generation", lambda x: x.update(generation_calls=1)), ("held_out", lambda x: x.update(held_out_captures=1)),
        ("protected", lambda x: x.update(protected_wip_unchanged=False)),
        ("claim_missing", lambda x: x["claim_evidence"].pop("full_snapshot_ancestry_qualified")),
        ("hypothesis", lambda x: x["claim_evidence"].update(role_binding_hypothesis_tested=True))):
        value = json.loads(json.dumps(sample)); mutate(value); corruptions.append({"name": name, "detected": bool(list(validator.iter_errors(value)))})
    false_pass = json.loads(json.dumps(sample)); false_pass.update(status="PASS_12_OF_12_DEV", first_broken_edge=None)
    corruptions.append({"name": "false_pass", "detected": bool(list(validator.iter_errors(false_pass)))})
    return {"passed": not errors and all(x["detected"] for x in corruptions), "errors": errors, "corruptions": corruptions}


def source_gate() -> dict[str, Any]:
    files = [PROJECT_ROOT/"src/raven_m/role_binding_timing/infra_m8_full_snapshot_ancestry.py",
             PROJECT_ROOT/"src/raven_m/role_binding_timing/infra_m8_terminal.py",
             PROJECT_ROOT/"scripts/run_role_binding_timing_infra_m8.py", PROJECT_ROOT/"scripts/finalize_role_binding_timing_infra_m8.py"]
    values = {p.name: p.read_text(encoding="utf-8") for p in files}; production = values[files[0].name] + values[files[2].name]; joined = "\n".join(values.values())
    checks = {
        "explicit_two_views": "observation_universe_complete" in production and "authorization_candidates" in production,
        "full_index_from_all_processes": 'snapshot.get("all_processes")' in production,
        "candidate_index_from_structural": 'snapshot.get("structural_processes")' in production,
        "candidate_universe_join": "AUTHORIZATION_VIEW_UNIVERSE_MISMATCH" in production,
        "runner_reuse_check": "OBSERVATION_UNIVERSE_RUNNER_PID_REUSE" in production,
        "current_only_ancestry": "MISSING_CURRENT_UNIVERSE" in production and "stale history grants no ancestry" in production,
        "both_views_persisted": "derived_authorization_view.json" in production and '"triggering_snapshot": snapshot' in production,
        "zero_5037_command": '"-P", "5037"' not in production and "adb_prefix(config, 5037" not in production,
        "no_pid_app_task_branch": all(x not in production for x in ("1912", "1464", "com.android.settings", "deskclock", "org.tasks", "broccoli", "H17", "r79")),
        "independent_terminal": "DUPLICATE_TERMINAL_COMPLETION" in values[files[1].name],
        "no_model": all(x not in joined for x in ("requests.post(", "openai.", "/generate", "model_client")),
    }
    checks["passed"] = all(checks.values()); return checks


def audit_gate() -> dict[str, Any]:
    path = PROJECT_ROOT/"artifacts/role_binding_timing/infra_m8_full_snapshot_ancestry_audit/full_snapshot_ancestry_audit.json"
    value = json.loads(path.read_text(encoding="utf-8")); joins = value["filter_join_ledger"]
    return {"passed": value["decision"] == "ELIGIBLE_FOR_M8_OFFLINE_IMPLEMENTATION_ONLY" and len(joins) == 10 and value["direct_trigger_evidence"]["runner_present_in_full_snapshot"] is True and value["direct_trigger_evidence"]["runner_present_in_structural_subset"] is False,
            "sha256": sha256(path.read_bytes()).hexdigest(), "joins": len(joins), "decision": value["decision"]}


def runtime_preflight(config: dict[str, Any]) -> dict[str, Any]:
    snap = build_m8_snapshot(gate="m8_offline_preflight", sequence=0, cache=M5.ExecutableHashCache(), raw_netstat=M5.netstat_bytes())
    project_paths = {M5.normalized_path(spec["path"]) for spec in config["process_identity"]["binaries"].values() if isinstance(spec, dict) and "path" in spec}
    owned = [r for r in snap["structural_processes"] if M5.normalized_path(r.get("exe")) in project_paths]; issues=[]
    if any(snap["listeners"][str(p)] for p in (5037,5038,5554,5555,8554)): issues.append("LISTENER_PRESENT")
    if owned: issues.append("PROJECT_RUNTIME_PROCESS_PRESENT")
    if (REPOSITORY_ROOT/config["output_root"]).exists(): issues.append("OUTPUT_ROOT_EXISTS")
    parent=Path(config["log_lifecycle"]["temp_parent"]); patterns=[f"{config['log_lifecycle']['temp_prefix']}*","infra_m8_resolved_config_*"]
    residue=sorted({str(p) for pattern in patterns for p in parent.glob(pattern)}) if parent.exists() else []
    if residue: issues.append("TEMP_RESIDUE")
    return {"passed": not issues, "issues": issues, "snapshot": snap, "project_owned_records": owned, "temp_residue": residue}


def main() -> int:
    if OUTPUT_ROOT.exists(): raise RuntimeError("M8_OFFLINE_ROOT_NOT_FRESH")
    OUTPUT_ROOT.mkdir(parents=True); (OUTPUT_ROOT/".gitattributes").write_text("*.bin binary\n", encoding="ascii")
    overlay=json.loads(CONFIG_PATH.read_text(encoding="utf-8")); config=load_runner().resolve_overlay(CONFIG_PATH)
    gates=[
      run_gate("compile",[str(PYTHON),"-m","py_compile","src/raven_m/role_binding_timing/infra_m8_full_snapshot_ancestry.py","src/raven_m/role_binding_timing/infra_m8_terminal.py","scripts/run_role_binding_timing_infra_m8.py","scripts/finalize_role_binding_timing_infra_m8.py","scripts/run_role_binding_timing_infra_m8_offline_gates.py"]),
      run_gate("focused_m8",[str(PYTHON),"-m","pytest","tests/role_binding_timing/test_infra_m8_full_snapshot_ancestry.py","tests/role_binding_timing/test_infra_m8_runner_terminal.py","-q","--color=no"]),
      run_gate("focused_m7",[str(PYTHON),"-m","pytest","tests/role_binding_timing/test_infra_m7_adb_authority.py","tests/role_binding_timing/test_infra_m7_runner_terminal.py","-q","--color=no"]),
      run_gate("focused_m6",[str(PYTHON),"-m","pytest","tests/role_binding_timing/test_infra_m6_display_observability.py","-q","--color=no"]),
      run_gate("m5_identity",[str(PYTHON),"-m","pytest","tests/role_binding_timing/test_infra_m5_process_identity.py","-q","--color=no"]),
      run_gate("terminal_accounting",[str(PYTHON),"-m","pytest","tests/role_binding_timing/test_infra_m4_terminal_accounting.py","-q","--color=no"]),
      run_gate("namespace",[str(PYTHON),"-m","pytest","tests/role_binding_timing","-q","--color=no"]),
      run_gate("full_regression",[str(PYTHON),"-m","pytest","tests","-q","--color=no"]),
    ]
    full=(OUTPUT_ROOT/"full_regression/stdout.bin").read_text(encoding="utf-8",errors="replace")
    failed=sorted(set(line.split()[1] for line in full.splitlines() if line.startswith("FAILED "))); full_ok=gates[7]["returncode"]==1 and failed==[KNOWN_FAILURE]
    protected={p:sha256((REPOSITORY_ROOT/p).read_bytes()).hexdigest() for p in config["protected_wip"]}; runtime=config["runtime"]
    hashes={k:sha256((REPOSITORY_ROOT/runtime[k]).read_bytes()).hexdigest() for k in ("python","adb_binary","emulator_launcher","qemu_binary","avd_ini","avd_config")}
    expected={k:runtime[f"{k}_sha256"] for k in hashes}; ps=REPOSITORY_ROOT/config["process_identity"]["psutil"]["module"]
    psutil={"version":M5.psutil.__version__,"sha256":sha256(ps.read_bytes()).hexdigest()}; psutil["passed"]=psutil["version"]==config["process_identity"]["psutil"]["version"] and psutil["sha256"]==config["process_identity"]["psutil"]["module_sha256"]
    result={"schema_version":"role_binding_timing.infra_m8.offline_gates.v1","created_at":datetime.now(timezone.utc).isoformat(),"generation_calls":0,"device_mutations":0,"restart_attempts":0,"gates":gates,
      "compile_pass":gates[0]["returncode"]==0,"focused_m8_pass":gates[1]["returncode"]==0,"focused_m7_pass":gates[2]["returncode"]==0,"focused_m6_pass":gates[3]["returncode"]==0,"m5_identity_pass":gates[4]["returncode"]==0,"terminal_accounting_pass":gates[5]["returncode"]==0,"namespace_pass":gates[6]["returncode"]==0,
      "full_regression_accepted":full_ok,"full_regression_observed_failed_nodes":failed,"full_regression_expected_only_failure":KNOWN_FAILURE,"schema_gate":schema_gate(config),"source_gate":source_gate(),"audit_gate":audit_gate(),
      "protected_wip":protected,"protected_wip_pass":protected==config["protected_wip"],"runtime_preflight":runtime_preflight(config),"binary_hashes":hashes,"binary_hashes_pass":hashes==expected,"psutil_gate":psutil,
      "base_config":{"path":overlay["base_config"],"expected_sha256":overlay["base_config_sha256"],"observed_sha256":sha256((REPOSITORY_ROOT/overlay["base_config"]).read_bytes()).hexdigest()}}
    result["overall_pass"]=all((result["compile_pass"],result["focused_m8_pass"],result["focused_m7_pass"],result["focused_m6_pass"],result["m5_identity_pass"],result["terminal_accounting_pass"],result["namespace_pass"],result["full_regression_accepted"],result["schema_gate"]["passed"],result["source_gate"]["passed"],result["audit_gate"]["passed"],result["protected_wip_pass"],result["runtime_preflight"]["passed"],result["binary_hashes_pass"],result["psutil_gate"]["passed"],result["base_config"]["expected_sha256"]==result["base_config"]["observed_sha256"]))
    (OUTPUT_ROOT/"offline_gate_result.json").write_bytes((json.dumps(result,indent=2,sort_keys=True)+"\n").encode("utf-8"))
    print(json.dumps({"overall_pass":result["overall_pass"],"failed_nodes":failed,"runtime_issues":result["runtime_preflight"]["issues"],"source_gate":result["source_gate"]},indent=2)); return 0 if result["overall_pass"] else 2


if __name__=="__main__": raise SystemExit(main())
