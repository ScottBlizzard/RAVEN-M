"""Post-run, zero-device-mutation evidence audit for the single INFRA-M6 chain."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
from typing import Any

from jsonschema import Draft202012Validator
import psutil


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.role_binding_timing.infra_m3_log_lifecycle import seal_live_logs  # noqa: E402
from raven_m.role_binding_timing.infra_m4_terminal_accounting import atomic_write_json  # noqa: E402
from raven_m.role_binding_timing.infra_m5_process_identity import (  # noqa: E402
    ExecutableHashCache, build_snapshot, identity_key, netstat_bytes, normalized_path,
)


RESULT_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m6_display_observability"
CONFIG_PATH = PROJECT_ROOT / "configs/role_binding_timing/infra_m6_display_observability.json"
LOCK_PATH = PROJECT_ROOT / "configs/role_binding_timing/infra_m6_display_observability.lock.json"
POSTMORTEM = RESULT_ROOT / "postmortem_audit.json"
POSTMORTEM_MANIFEST = RESULT_ROOT / "postmortem_artifact_manifest.json"


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def same_process(record: dict[str, Any]) -> bool:
    try:
        process = psutil.Process(int(record["pid"]))
        return abs(process.create_time() - float(record["create_time"])) < 0.0005
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False


def validate_original_manifest() -> dict[str, Any]:
    path = RESULT_ROOT / "artifact_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    missing = []
    bad = []
    for record in manifest["artifacts"]:
        artifact = REPOSITORY_ROOT / record["path"]
        if not artifact.is_file():
            missing.append(record["path"])
        else:
            payload = artifact.read_bytes()
            if len(payload) != record["bytes"] or sha256(payload).hexdigest() != record["sha256"]:
                bad.append(record["path"])
    return {"path": path.relative_to(REPOSITORY_ROOT).as_posix(), "sha256": digest(path), "entries": len(manifest["artifacts"]), "missing": missing, "hash_mismatch": bad, "passed": not missing and not bad}


def current_runtime(config: dict[str, Any]) -> dict[str, Any]:
    snapshot = build_snapshot(gate="m6_postmortem", sequence=0, cache=ExecutableHashCache(), raw_netstat=netstat_bytes())
    controlled_paths = {
        normalized_path(config["process_identity"]["binaries"][key]["path"])
        for key in ("adb", "emulator_launcher", "qemu", "crashpad", "netsimd")
    }
    project_owned = [record for record in snapshot["structural_processes"] if normalized_path(record.get("exe")) in controlled_paths]
    listeners = {str(port): snapshot["listeners"][str(port)] for port in (5037, 5038, 5554, 5555, 8554)}
    return {"listeners": listeners, "project_owned_processes": project_owned, "passed": not project_owned and not any(listeners.values()), "snapshot": snapshot}


def build_postmortem_manifest() -> dict[str, Any]:
    artifacts = []
    for path in sorted(RESULT_ROOT.rglob("*")):
        if path.is_file() and path != POSTMORTEM_MANIFEST:
            payload = path.read_bytes()
            artifacts.append({"path": path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": len(payload), "sha256": sha256(payload).hexdigest()})
    value = {"schema_version": "role_binding_timing.infra_m6.postmortem_manifest.v1", "artifacts": artifacts}
    atomic_write_json(POSTMORTEM_MANIFEST, value, replace=False)
    return value


def main() -> int:
    if POSTMORTEM.exists() or POSTMORTEM_MANIFEST.exists():
        raise RuntimeError("M6_POSTMORTEM_ALREADY_EXISTS")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    completion_path = RESULT_ROOT / "qualification_completion.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    validation = json.loads((RESULT_ROOT / "terminal_validation.json").read_text(encoding="utf-8"))
    schema = json.loads((REPOSITORY_ROOT / config["schema"]).read_text(encoding="utf-8"))
    schema_errors = [item.message for item in Draft202012Validator(schema).iter_errors(completion)]
    if completion["first_broken_edge"] != "PROCESS_IDENTITY:PROCESS:496@1785880048.227501:ADB_COMMAND_ROLE":
        raise RuntimeError("UNEXPECTED_M6_EDGE")
    if completion["generation_calls"] != 0 or completion["held_out_captures"] != 0:
        raise RuntimeError("SCOPE_BOUNDARY_BROKEN")
    first = json.loads((RESULT_ROOT / "process_identity/first_process_identity_failure.json").read_text(encoding="utf-8"))
    offending = None
    for line in (RESULT_ROOT / "process_identity/continuous_history/process_history.ndjson").read_text(encoding="utf-8").splitlines():
        for record in json.loads(line)["structural_processes"]:
            if identity_key(record) == "496@1785880048.227501":
                offending = record
    if offending is None:
        raise RuntimeError("OFFENDING_PROCESS_RECORD_MISSING")
    expected_command = str((REPOSITORY_ROOT / config["runtime"]["adb_binary"]).resolve()) + " -P 5038 devices -l"
    runner_pid = completion["runtime"]["runner_identity"]["pid"]
    command_evidence = {
        "identity": identity_key(offending),
        "record": offending,
        "exact_expected_command": expected_command,
        "command_matches_runner_boot_probe": offending["command_line"].casefold() == expected_command.casefold(),
        "parent_is_runner": offending["ppid"] == runner_pid,
        "binary_hash_matches_lock": offending["exe_sha256"] == config["runtime"]["adb_binary_sha256"],
        "classification": "FROZEN_POLICY_FALSE_REJECTION_OF_RUNNER_ADB_DEVICES_CLIENT",
    }
    runtime_before_seal = current_runtime(config)
    if not runtime_before_seal["passed"]:
        raise RuntimeError("POSTMORTEM_RUNTIME_RESIDUE")
    core_gone = all(not same_process(record) for record in completion["process_identity"]["core"].values())
    if not core_gone:
        raise RuntimeError("CORE_PROCESS_STILL_RUNNING")
    external_root = Path(completion["log_seal"]["external_live_root"]).resolve()
    sealed = seal_live_logs(
        live_root=external_root,
        result_root=RESULT_ROOT / "postmortem_sealed_logs",
        names=config["log_lifecycle"]["live_log_names"],
        repository_root=REPOSITORY_ROOT,
        forbidden_roots=[Path(item) for item in config["log_lifecycle"]["forbidden_roots"]],
        required_temp_parent=Path(config["log_lifecycle"]["temp_parent"]),
        owners_gone=True,
        parent_handles_closed=bool(completion["runtime"]["steps"]["emulator_start"]["parent_handles_closed"]),
    )
    shutil.rmtree(external_root)
    protected = {name: digest(REPOSITORY_ROOT / name) for name in config["protected_wip"]}
    lock_bad = [name for name, expected in lock["files"].items() if not (REPOSITORY_ROOT / name).is_file() or digest(REPOSITORY_ROOT / name) != expected]
    audit = {
        "schema_version": "role_binding_timing.infra_m6.postmortem.v1",
        "generation_calls": 0,
        "model_tokens": 0,
        "held_out_captures": 0,
        "development_contaminated": True,
        "held_out_eligible": False,
        "original_completion": {"path": completion_path.relative_to(REPOSITORY_ROOT).as_posix(), "sha256": digest(completion_path), "status": completion["status"], "first_broken_edge": completion["first_broken_edge"], "terminal_mode": completion["terminal_mode"], "schema_validation_file_passed": validation["passed"], "independent_schema_errors": schema_errors},
        "exactly_once_terminal": len(list(RESULT_ROOT.glob("qualification_completion.json"))) == 1,
        "original_manifest": validate_original_manifest(),
        "first_failure": {"gate": first["gate"], "phase": first["phase"], "issues": first["issues"], "continuous_history_status": first["continuous_history_status"]},
        "offending_process": command_evidence,
        "gate_counts": {"launch_passed": True, "boot_attempts": len(completion["runtime"]["boot"]["attempts"]), "framework_run": False, "burn_in": "0/24", "settings": "0/3", "grid": "0/12"},
        "cleanup_boundary": {"canonical_cleanup_passed": completion["cleanup"]["passed"], "canonical_log_seal_passed": completion["log_seal"]["passed"], "canonical_values_immutable": True, "emulator_and_adb_stop_commands_succeeded": True, "current_runtime_clean": runtime_before_seal, "registered_core_gone": core_gone, "postmortem_log_copy": sealed, "external_temp_removed_after_closed-handle_copy": not external_root.exists()},
        "lock": {"sha256": digest(LOCK_PATH), "files": len(lock["files"]), "hash_mismatch_or_missing": lock_bad, "passed": not lock_bad},
        "protected_wip": {"observed": protected, "passed": protected == config["protected_wip"]},
        "claim_evidence": {
            "process_policy_false_rejection_supported": bool(command_evidence["command_matches_runner_boot_probe"] and command_evidence["parent_is_runner"] and command_evidence["binary_hash_matches_lock"]),
            "display_quorum_evaluated": False,
            "display_quorum_qualified": False,
            "burn_in_qualified": False,
            "a11y_tested": False,
            "a11y_qualified": False,
            "v0_3_preparation_authorized": False,
            "role_binding_hypothesis_tested": False,
        },
        "verdict": "PROCESS_IDENTITY_FAILED_BEFORE_DISPLAY_QUORUM",
    }
    atomic_write_json(POSTMORTEM, audit, replace=False)
    manifest = build_postmortem_manifest()
    print(json.dumps({"verdict": audit["verdict"], "first_gate": first["gate"], "command": offending["command_line"], "postmortem_logs": sealed, "artifacts": len(manifest["artifacts"]), "protected": audit["protected_wip"]["passed"], "lock": audit["lock"]["passed"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
