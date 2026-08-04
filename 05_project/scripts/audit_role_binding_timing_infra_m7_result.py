"""Read-only result audit plus safe removal of the empty M7 external temp root."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
RESULT_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m7_runner_adb_authority"
AUDIT_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m7_runner_adb_authority_result_audit"
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.role_binding_timing.infra_m4_terminal_accounting import atomic_write_json, utc_now  # noqa: E402
from raven_m.role_binding_timing.infra_m5_process_identity import ExecutableHashCache, normalized_path  # noqa: E402
from raven_m.role_binding_timing.infra_m7_adb_authority import build_m7_snapshot  # noqa: E402


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def manifest_check() -> dict[str, Any]:
    manifest = load(RESULT_ROOT / "artifact_manifest.json")
    issues = []
    for item in manifest["artifacts"]:
        path = REPOSITORY_ROOT / item["path"]
        if not path.is_file():
            issues.append(f"MISSING:{item['path']}"); continue
        if path.stat().st_size != item["bytes"]:
            issues.append(f"SIZE:{item['path']}")
        if digest(path) != item["sha256"]:
            issues.append(f"HASH:{item['path']}")
    return {"passed": not issues, "entries": len(manifest["artifacts"]),
            "manifest_sha256": digest(RESULT_ROOT / "artifact_manifest.json"), "issues": issues}


def history_evidence(key: str, runner_pid: int) -> dict[str, Any]:
    samples = []
    history = RESULT_ROOT / "process_identity/continuous_history/process_history.ndjson"
    for line in history.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        selected = [record for record in event["structural_processes"]
                    if record.get("identity_key") == key or record.get("pid") == runner_pid]
        if selected:
            samples.append({"sample": event["sample"], "records": selected,
                            "raw_netstat_sha256": event["raw_netstat_sha256"]})
    return {"path": history.relative_to(REPOSITORY_ROOT).as_posix(), "sha256": digest(history), "samples": samples}


def cleanup_empty_external_root(completion: dict[str, Any]) -> dict[str, Any]:
    raw = completion["log_seal"].get("external_live_root")
    parent = Path("C:/Users/lenovo/AppData/Local/Temp/raven_m_role_binding_timing").resolve()
    path = Path(raw).resolve() if raw else None
    if path is None or path.parent != parent or not path.name.startswith("infra_m7_live_"):
        return {"passed": False, "path": raw, "issue": "UNQUALIFIED_EXTERNAL_ROOT"}
    existed = path.exists(); entries = sorted(item.name for item in path.iterdir()) if existed else []
    if entries:
        return {"passed": False, "path": str(path), "existed_before": existed,
                "entries_before": entries, "issue": "NONEMPTY_EXTERNAL_ROOT_NOT_REMOVED"}
    if existed:
        path.rmdir()
    return {"passed": not path.exists(), "path": str(path), "existed_before": existed,
            "entries_before": entries, "removed_as_empty_directory": existed, "exists_after": path.exists()}


def main() -> int:
    if AUDIT_ROOT.exists():
        raise RuntimeError("M7_RESULT_AUDIT_ROOT_NOT_FRESH")
    AUDIT_ROOT.mkdir(parents=True)
    completion = load(RESULT_ROOT / "qualification_completion.json")
    validation = load(RESULT_ROOT / "terminal_validation.json")
    failure = load(RESULT_ROOT / "process_identity/first_process_identity_failure.json")
    first_edge = load(RESULT_ROOT / "phase_journal/first_broken_edge.json")
    trigger = failure["triggering_snapshot"]
    client_key = "1464@1785882456.172884"
    runner = completion["runtime"]["runner_identity"]
    history = history_evidence(client_key, int(runner["pid"]))
    client_records = [record for sample in history["samples"] for record in sample["records"]
                      if record.get("identity_key") == client_key]
    runner_records = [record for sample in history["samples"] for record in sample["records"]
                      if record.get("pid") == runner["pid"]]
    trigger_all = {record.get("pid"): record for record in trigger["all_processes"]}
    trigger_structural = {record.get("pid"): record for record in trigger["structural_processes"]}
    runtime_snapshot = build_m7_snapshot(gate="m7_post_run_audit", sequence=0, cache=ExecutableHashCache())
    overlay = load(PROJECT_ROOT / "configs/role_binding_timing/infra_m7_runner_adb_authority.json")
    base = load(REPOSITORY_ROOT / overlay["base_config"])
    project_paths = {normalized_path(spec["path"]) for spec in base["process_identity"]["binaries"].values()
                     if isinstance(spec, dict) and "path" in spec}
    project_runtime = [record for record in runtime_snapshot["structural_processes"]
                       if normalized_path(record.get("exe")) in project_paths]
    external_cleanup = cleanup_empty_external_root(completion)
    protected_expected = base["protected_wip"]
    protected_after = {name: digest(REPOSITORY_ROOT / name) for name in protected_expected}
    canonical_count = len(list(RESULT_ROOT.rglob("qualification_completion.json")))
    journal_entries = sorted((RESULT_ROOT / "phase_journal/entries").glob("*.json"))
    direct_checks = {
        "terminal_schema_valid": validation["passed"] is True,
        "exactly_one_completion": canonical_count == 1,
        "journal_entries_eight": len(journal_entries) == 8,
        "first_edge_consistent": completion["first_broken_edge"] == failure["issues"][0].join(["PROCESS_IDENTITY:adb_server_registered:", ""]) == first_edge["first_broken_edge"],
        "status_process_identity_failed": completion["status"] == "PROCESS_IDENTITY_FAILED",
        "zero_generation": completion["generation_calls"] == 0 and completion["model_tokens"] == 0,
        "zero_held_out": completion["held_out_captures"] == 0,
        "no_boot_or_later_stage": completion["burn_in"]["completed_cycles"] == 0 and completion["a11y"]["settings"]["completed"] == 0 and completion["a11y"]["grid"]["completed"] == 0,
        "client_exact_path_hash": bool(client_records) and all(record["exe_sha256"] == base["runtime"]["adb_binary_sha256"] for record in client_records),
        "client_explicit_5038": bool(client_records) and all(record["cmdline_items"][1:3] == ["-P", "5038"] for record in client_records),
        "client_direct_runner_parent": bool(client_records) and all(record["ppid"] == runner["pid"] for record in client_records),
        "client_never_listened": bool(client_records) and all(record["listener_ports"] == [] for record in client_records),
        "runner_present_in_history": bool(runner_records),
        "runner_present_in_trigger_all_processes": runner["pid"] in trigger_all,
        "runner_absent_from_trigger_structural_subset": runner["pid"] not in trigger_structural,
        "controlled_ports_empty_after": all(runtime_snapshot["listeners"][str(port)] == [] for port in (5037, 5038, 5554, 5555, 8554)),
        "project_runtime_absent_after": not project_runtime,
        "protected_wip_unchanged": protected_after == protected_expected == completion["protected_wip_after"],
        "external_empty_root_removed": external_cleanup["passed"],
        "manifest_integrity": manifest_check()["passed"],
    }
    result = {
        "schema_version": "role_binding_timing.infra_m7.result_audit.v1", "created_at": utc_now(),
        "verdict": "FAIL_PROCESS_IDENTITY_FALSE_REJECTION", "generation_calls": 0,
        "held_out_captures": 0, "model_or_emulator_batch_started": False,
        "immutable_completion_status": completion["status"], "immutable_first_broken_edge": completion["first_broken_edge"],
        "root_cause_classification": "RUNNER_CURRENTNESS_EVIDENCE_SCOPE_MISMATCH",
        "direct_evidence": {
            "runner_identity": runner, "transient_client_identity": client_key,
            "history": history, "runner_in_trigger_all_processes": runner["pid"] in trigger_all,
            "runner_in_trigger_structural_processes": runner["pid"] in trigger_structural,
            "trigger_snapshot_sha256": digest(RESULT_ROOT / "process_identity/first_process_identity_failure.json"),
            "adb_server_identity": completion["process_identity"]["core"].get("adb_server"),
        },
        "inference": "The policy tested runner currentness against the structural subset. After the transient start-server client exited, the still-live runner was no longer an ancestor selected into that subset, although it remained in all_processes and in listener-bearing history. This created the false rejection and prevented the client ledger from being populated.",
        "secondary_failures": {
            "cleanup": completion["cleanup"],
            "interpretation": "Because the launch client was never ledgered, cleanup reclassified its history record under the cleanup phase and added START_SERVER_PHASE:cleanup. The registered 5038 server was nevertheless killed; no controlled port remains.",
            "external_temp_cleanup": external_cleanup,
        },
        "terminal_accounting": {"canonical_count": canonical_count, "journal_entries": len(journal_entries),
                                "terminal_validation": validation, "manifest": manifest_check()},
        "post_run_runtime": {"listeners": runtime_snapshot["listeners"], "project_runtime_records": project_runtime},
        "protected_wip": protected_after, "checks": direct_checks,
        "overall_audit_pass": all(direct_checks.values()),
        "claim_evidence": {
            "runner_adb_authority_qualified": False, "exclusive_5038_start_observed": True,
            "exclusive_5038_cleanup_observed": True, "boot_tested": False, "display_quorum_tested": False,
            "burn_in_tested": False, "a11y_tested": False, "dev_grid_tested": False,
            "v0_3_preparation_authorized": False, "held_out_tested": False,
            "role_binding_hypothesis_tested": False,
        },
        "stop_decision": "STOP_INFRA_M7_NO_RETRY",
    }
    atomic_write_json(AUDIT_ROOT / "result_audit.json", result, replace=False)
    payload = (AUDIT_ROOT / "result_audit.json").read_bytes()
    atomic_write_json(AUDIT_ROOT / "artifact_manifest.json", {
        "schema_version": "role_binding_timing.infra_m7.result_audit_manifest.v1",
        "artifacts": [{"path": "result_audit.json", "bytes": len(payload), "sha256": sha256(payload).hexdigest()}],
    }, replace=False)
    print(json.dumps({"verdict": result["verdict"], "overall_audit_pass": result["overall_audit_pass"],
                      "first_broken_edge": result["immutable_first_broken_edge"],
                      "post_run_listeners": result["post_run_runtime"]["listeners"],
                      "external_cleanup": external_cleanup}, indent=2))
    return 0 if result["overall_audit_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
