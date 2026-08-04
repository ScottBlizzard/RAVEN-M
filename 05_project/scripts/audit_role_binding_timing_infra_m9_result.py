"""Read-only/result-preservation audit for the frozen INFRA-M9 chain."""

from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

from jsonschema import Draft202012Validator
import psutil


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
RUN_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m9_authorization_view_separation"
OUTPUT_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m9_result_audit"
LOCK_PATH = PROJECT_ROOT / "configs/role_binding_timing/infra_m9_authorization_view_separation.lock.json"
SCHEMA_PATH = PROJECT_ROOT / "schemas/role_binding_timing_infra_m9_completion.v1.schema.json"
PROTECTED = (
    "05_project/src/raven_m/controller/episode_controller.py",
    "05_project/src/raven_m/controller/protocol_v2_guard.py",
    "05_project/tests/scripts/test_protocol_v2_2_r79_r78_trace_replay.py",
)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: Any) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def load_runner() -> Any:
    path = PROJECT_ROOT / "scripts/run_role_binding_timing_infra_m9.py"
    spec = importlib.util.spec_from_file_location("m9_result_audit_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("M9_RUNNER_LOAD_FAILURE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def manifest_audit() -> dict[str, Any]:
    path = RUN_ROOT / "artifact_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    records = []
    for item in manifest["artifacts"]:
        artifact = REPOSITORY_ROOT / item["path"]
        actual = digest(artifact) if artifact.is_file() else None
        records.append({"path": item["path"], "expected": item["sha256"], "actual": actual, "passed": actual == item["sha256"]})
    return {
        "path": path.relative_to(REPOSITORY_ROOT).as_posix(),
        "sha256": digest(path),
        "artifact_count": len(records),
        "passed": all(item["passed"] for item in records),
        "failures": [item for item in records if not item["passed"]],
    }


def lock_audit() -> dict[str, Any]:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    failures = []
    for relative, expected in lock["files"].items():
        path = REPOSITORY_ROOT / relative
        actual = digest(path) if path.is_file() else None
        if actual != expected:
            failures.append({"path": relative, "expected": expected, "actual": actual})
    return {"sha256": digest(LOCK_PATH), "files": len(lock["files"]), "passed": not failures, "failures": failures}


def host_residue(config: dict[str, Any]) -> dict[str, Any]:
    network = subprocess.run(["netstat", "-ano", "-p", "tcp"], check=True, capture_output=True, timeout=30).stdout
    text = network.decode("utf-8", errors="replace")
    listeners: dict[int, list[int]] = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[0].casefold() == "tcp" and fields[-2].casefold() == "listening":
            try:
                port = int(fields[1].rsplit(":", 1)[1])
                pid = int(fields[-1])
            except (IndexError, ValueError):
                continue
            if port in {5037, 5038, 5554, 5555, 8554}:
                listeners.setdefault(port, []).append(pid)
    binary_paths = {
        str(Path(spec["path"]).resolve()).casefold()
        for spec in config["process_identity"]["binaries"].values()
        if isinstance(spec, dict) and spec.get("path")
    }
    project_processes = []
    for process in psutil.process_iter():
        try:
            exe = str(Path(process.exe()).resolve()).casefold()
            if exe in binary_paths:
                project_processes.append({"pid": process.pid, "ppid": process.ppid(), "exe": process.exe(), "cmdline": process.cmdline()})
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
            continue
    return {
        "controlled_listeners": {str(port): sorted(pids) for port, pids in sorted(listeners.items())},
        "project_processes": project_processes,
        "passed": not listeners and not project_processes,
        "raw_netstat_sha256": sha256(network).hexdigest(),
    }


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise RuntimeError("M9_RESULT_AUDIT_ROOT_NOT_FRESH")
    OUTPUT_ROOT.mkdir(parents=True)
    completion_path = RUN_ROOT / "qualification_completion.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    failure = json.loads((RUN_ROOT / "process_identity/first_process_identity_failure.json").read_text(encoding="utf-8"))
    validation = json.loads((RUN_ROOT / "terminal_validation.json").read_text(encoding="utf-8"))
    receipt = json.loads((RUN_ROOT / "terminal_writer_receipt.json").read_text(encoding="utf-8"))
    history_path = RUN_ROOT / "process_identity/continuous_history/process_history.ndjson"
    history_events = [json.loads(line) for line in history_path.read_text(encoding="utf-8").splitlines() if line]
    issue_keys: dict[str, str] = {}
    for issue in failure["issues"]:
        if issue.startswith("PROCESS:"):
            _, key, reason = issue.split(":", 2)
            issue_keys[key] = reason
    first_observed: dict[str, dict[str, Any]] = {}
    for event in history_events:
        for candidate in event["project_authorization_candidates"]:
            key = candidate.get("identity_key")
            if key not in issue_keys or key in first_observed:
                continue
            parent_pid = candidate.get("ppid")
            parent_view = None
            parent_record = None
            for name in ("support_only_ancestry_nodes", "project_authorization_candidates", "unrelated_observed_processes"):
                matches = [row for row in event[name] if row.get("pid") == parent_pid]
                if matches:
                    parent_view, parent_record = name, matches[0]
                    break
            first_observed[key] = {
                "sample": event["sample"],
                "candidate": candidate,
                "parent_view": parent_view,
                "parent_record": parent_record,
                "view_type_assertions": event["view_type_assertions"],
            }
    trigger_current = {row.get("identity_key"): row for row in failure["triggering_snapshot"]["all_processes"]}
    trigger_candidates = {row.get("identity_key"): row for row in failure["derived_process_views"]["project_authorization_candidates"]}
    support_by_pid = {row.get("pid"): row for row in failure["derived_process_views"]["support_only_ancestry_nodes"]}
    structural_by_pid = {row.get("pid"): row for row in failure["triggering_snapshot"]["structural_processes"]}
    current_support_loss = []
    for key in issue_keys:
        candidate = trigger_candidates.get(key)
        if candidate is None:
            continue
        support = support_by_pid.get(candidate.get("ppid"))
        source = structural_by_pid.get(candidate.get("ppid"))
        if support and source and not support.get("exe_sha256") and source.get("exe_sha256"):
            current_support_loss.append({
                "candidate_identity": key,
                "parent_pid": candidate.get("ppid"),
                "support_hash": support.get("exe_sha256"),
                "structural_source_hash": source.get("exe_sha256"),
                "support_view_sha256": canonical_hash(support),
                "source_record_sha256": canonical_hash(source),
            })
    config = load_runner().resolve_overlay(PROJECT_ROOT / "configs/role_binding_timing/infra_m9_authorization_view_separation.json")
    expected_adb_path = str(Path(config["process_identity"]["binaries"]["adb"]["path"]).resolve()).casefold()
    expected_adb_hash = config["process_identity"]["binaries"]["adb"]["sha256"]
    issue_records = [first_observed[key]["candidate"] for key in sorted(first_observed)]
    all_locked_adb = len(issue_records) == len(issue_keys) and all(
        str(Path(record.get("exe", "")).resolve()).casefold() == expected_adb_path
        and record.get("exe_sha256") == expected_adb_hash
        for record in issue_records
    )
    coobserved_parents = sum(item["parent_record"] is not None for item in first_observed.values())
    current_issue_count = sum(key in trigger_current for key in issue_keys)
    journal = [json.loads(line) for line in (RUN_ROOT / "phase_journal/journal.ndjson").read_text(encoding="utf-8").splitlines() if line]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    schema_errors = [item.message for item in Draft202012Validator(schema).iter_errors(completion)]
    manifest = manifest_audit()
    lock = lock_audit()
    residue = host_residue(config)
    external_root = Path(completion["log_seal"]["external_live_root"])
    external_records = []
    preservation_root = OUTPUT_ROOT / "postmortem_external_logs"
    if residue["passed"] and external_root.is_dir():
        preservation_root.mkdir()
        for source in sorted(external_root.rglob("*")):
            if source.is_file():
                target = preservation_root / source.relative_to(external_root)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                external_records.append({
                    "source": str(source),
                    "source_sha256": digest(source),
                    "copy": target.relative_to(REPOSITORY_ROOT).as_posix(),
                    "copy_sha256": digest(target),
                    "bytes": target.stat().st_size,
                    "matched": digest(source) == digest(target),
                })
    protected = {relative: digest(REPOSITORY_ROOT / relative) for relative in PROTECTED}
    frozen_protected = config["protected_wip"]
    phase_rows = [{"sequence": row["sequence"], "phase": row["phase"], "event": row["event"], "status": row["status"], "first_broken_edge": row.get("first_broken_edge")} for row in journal]
    audit = {
        "schema_version": "role_binding_timing.infra_m9.result_audit.v1",
        "verdict": "FAIL_TEMPORAL_SUPPORT_ATTESTATION",
        "m9_status_immutable": completion["status"],
        "first_broken_edge_immutable": completion["first_broken_edge"],
        "prestart_orchestration_deviation": {
            "evidence_class": "RECONSTRUCTED_OPERATOR_RECORD_FROM_TOOL_OUTPUT",
            "command_interpreter": "system Python instead of locked venv Python",
            "error": "ModuleNotFoundError: android_env during import before M9 main",
            "run_root_created": False,
            "project_resources_started": False,
            "generation_calls": 0,
            "counted_as_frozen_chain": False,
            "note": "Recorded transparently; not raw runner evidence and not used to alter source/config.",
        },
        "phase_journal": phase_rows,
        "failure_mechanism": {
            "failed_candidate_count": len(issue_keys),
            "history_records_recovered": len(first_observed),
            "all_exact_locked_adb_binary": all_locked_adb,
            "coobserved_parent_count": coobserved_parents,
            "current_issue_candidate_count": current_issue_count,
            "exited_before_trigger_count": len(issue_keys) - current_issue_count,
            "current_support_hash_loss_count": len(current_support_loss),
            "current_support_hash_loss": current_support_loss,
            "issue_records": [
                {
                    "identity_key": key,
                    "reason": issue_keys[key],
                    "sample": first_observed[key]["sample"],
                    "pid": first_observed[key]["candidate"]["pid"],
                    "ppid": first_observed[key]["candidate"]["ppid"],
                    "command_line": first_observed[key]["candidate"]["command_line"],
                    "candidate_sha256": canonical_hash(first_observed[key]["candidate"]),
                    "parent_view": first_observed[key]["parent_view"],
                    "parent_identity_key": (first_observed[key]["parent_record"] or {}).get("identity_key"),
                    "views_disjoint": first_observed[key]["view_type_assertions"].get("views_disjoint"),
                }
                for key in sorted(first_observed)
            ],
            "direct_evidence_interpretation": "Every rejected transient ADB child had a co-observed parent in its history sample. Twelve child identities were absent at the trigger. The one current child had a current support parent whose hash existed in structural_processes but was omitted from the derived support view.",
            "inference": "M9 separated authority correctly but did not preserve a bounded co-observation attestation for later history evaluation, and it under-specified support evidence fields.",
        },
        "view_evidence": {
            "trigger_counts": failure["derived_process_views"]["counts"],
            "trigger_type_assertions": failure["derived_process_views"]["type_assertions"],
            "prelaunch_passed": any(row["phase"] == "launch" and row["event"] == "end" and row["status"] == "PASS" for row in journal),
            "boot_passed": any(row["phase"] == "boot" and row["event"] == "end" and row["status"] == "PASS" for row in journal),
        },
        "accounting": {
            "generation_calls": completion["generation_calls"],
            "model_tokens": completion["model_tokens"],
            "held_out_captures": completion["held_out_captures"],
            "process_snapshot_directories": len(list((RUN_ROOT / "process_identity/snapshots").iterdir())),
            "history_samples": len(history_events),
            "journal_entries": len(journal),
            "terminal_completion_files": len(list(RUN_ROOT.glob("qualification_completion.json"))),
            "terminal_schema_passed": validation["passed"] is True and not schema_errors,
            "terminal_receipt_matches": receipt["canonical_sha256"] == digest(completion_path),
            "artifact_manifest": manifest,
            "input_lock": lock,
        },
        "cleanup_and_logs": {
            "frozen_cleanup_passed": completion["cleanup"].get("passed"),
            "frozen_cleanup_issues": completion["cleanup"].get("issues", []),
            "frozen_log_seal_passed": completion["log_seal"].get("passed"),
            "frozen_log_seal_issues": completion["log_seal"].get("issues", []),
            "post_terminal_host_residue": residue,
            "external_root_still_exists": external_root.is_dir(),
            "postmortem_preservation_only": True,
            "postmortem_external_logs": external_records,
            "postmortem_copy_complete": bool(external_records) and all(item["matched"] for item in external_records),
            "note": "Postmortem copies preserve bytes after verified host cleanup; they do not change the immutable frozen cleanup/log_seal FAIL verdict.",
        },
        "protected_wip": {"observed": protected, "expected": frozen_protected, "passed": protected == frozen_protected},
        "claim_evidence": {
            "m8_prelaunch_false_rejection_reproduced": False,
            "authorization_view_separation_qualified": False,
            "temporal_support_attestation_qualified": False,
            "exclusive_5038_and_launch_tested": True,
            "boot_tested": True,
            "display_framework_completed": False,
            "burn_in_tested": False,
            "a11y_tested": False,
            "dev_grid_tested": False,
            "v0_3_preparation_authorized": False,
            "held_out_tested": False,
            "role_binding_hypothesis_tested": False,
        },
        "decision": "NOT_ELIGIBLE_FOR_V0_3_PREPARATION",
    }
    required = [
        completion["status"] == "PROCESS_IDENTITY_FAILED",
        len(issue_keys) == 13,
        len(first_observed) == 13,
        coobserved_parents == 13,
        current_issue_count == 1,
        len(current_support_loss) == 1,
        all_locked_adb,
        manifest["passed"],
        lock["passed"],
        validation["passed"] is True,
        not schema_errors,
        receipt["canonical_sha256"] == digest(completion_path),
        residue["passed"],
        protected == frozen_protected,
        completion["generation_calls"] == 0,
        completion["held_out_captures"] == 0,
    ]
    audit["audit_passed"] = all(required)
    output = OUTPUT_ROOT / "result_audit.json"
    output.write_bytes((json.dumps(audit, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    manifest_path = OUTPUT_ROOT / "artifact_manifest.json"
    artifacts = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path != manifest_path:
            artifacts.append({"path": path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)})
    manifest_path.write_bytes((json.dumps({
        "schema_version": "role_binding_timing.infra_m9.result_audit_manifest.v1",
        "artifacts": artifacts,
    }, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({
        "audit_passed": audit["audit_passed"],
        "verdict": audit["verdict"],
        "failed_candidates": len(issue_keys),
        "coobserved_parents": coobserved_parents,
        "current_candidates": current_issue_count,
        "support_hash_losses": len(current_support_loss),
        "host_clean": residue["passed"],
        "decision": audit["decision"],
    }, indent=2))
    return 0 if audit["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
