"""Read-only M7 filter/join audit for the INFRA-M8 boundary."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
OUTPUT_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m8_full_snapshot_ancestry_audit"


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def line_hits(path: Path, needles: list[str]) -> list[dict[str, object]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [{"line": index, "text": text.strip()} for index, text in enumerate(lines, 1)
            if any(needle in text for needle in needles)]


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise RuntimeError("M8_AUDIT_ROOT_NOT_FRESH")
    OUTPUT_ROOT.mkdir(parents=True)
    m5 = PROJECT_ROOT / "src/raven_m/role_binding_timing/infra_m5_process_identity.py"
    m7 = PROJECT_ROOT / "src/raven_m/role_binding_timing/infra_m7_adb_authority.py"
    completion_path = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m7_runner_adb_authority/qualification_completion.json"
    failure_path = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m7_runner_adb_authority/process_identity/first_process_identity_failure.json"
    history_path = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m7_runner_adb_authority/process_identity/continuous_history/process_history.ndjson"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    failure = json.loads(failure_path.read_text(encoding="utf-8"))
    runner = completion["runtime"]["runner_identity"]
    trigger = failure["triggering_snapshot"]
    all_by_pid = {record.get("pid"): record for record in trigger["all_processes"]}
    structural_by_pid = {record.get("pid"): record for record in trigger["structural_processes"]}
    joins = [
        {"join_id": "J1_snapshot_derivation", "location": "build_snapshot/build_m7_snapshot",
         "observed": "all_processes is complete raw enumeration; structural_processes is a filtered relevant+ancestry projection.",
         "classification": "CORRECT_DUAL_DATA_EXISTS_BUT_AUTHORITY_NOT_EXPLICIT"},
        {"join_id": "J2_current_index", "location": "StructuralIdentityPolicy.evaluate",
         "observed": "current = process_index(snapshot['structural_processes']) is used for both core-role state and parent existence.",
         "classification": "DOMAIN_MISMATCH"},
        {"join_id": "J3_candidate_union", "location": "StructuralIdentityPolicy.evaluate",
         "observed": "combined includes current structural candidates plus relevant recent records; this is appropriate for role-policy candidates only.",
         "classification": "CORRECT_AUTHORIZATION_VIEW"},
        {"join_id": "J4_core_presence", "location": "StructuralIdentityPolicy.evaluate",
         "observed": "Core processes are checked in structural_processes, where exact hash-bearing project roles belong.",
         "classification": "CORRECT_AUTHORIZATION_VIEW"},
        {"join_id": "J5_baseline_pid_reuse", "location": "StructuralIdentityPolicy.freeze_baseline/evaluate",
         "observed": "Baseline role-candidate PID reuse is checked only for project-relevant candidates; parent/runner PID reuse is not separately checked in the full universe.",
         "classification": "PARTIAL_DOMAIN_MISMATCH"},
        {"join_id": "J6_helper_ancestry", "location": "_ancestry_to_core(record, current)",
         "observed": "Parent-chain traversal receives the filtered current index. It can lose a legitimate non-role parent after a transient descendant exits.",
         "classification": "DOMAIN_MISMATCH"},
        {"join_id": "J7_runner_currentness", "location": "M7 _common_client_issues",
         "observed": "runner_current is looked up in the same filtered current map, causing the frozen M7 false rejection.",
         "classification": "DOMAIN_MISMATCH_DIRECT_CAUSE"},
        {"join_id": "J8_continuing_client", "location": "M7 _continuing_client_issues",
         "observed": "A synthetic map containing only self.runner_record bypasses live full-snapshot currentness for already-ledgered clients.",
         "classification": "DOMAIN_MISMATCH_FALSE_ACCEPT_RISK"},
        {"join_id": "J9_continuous_history", "location": "M7ContinuousProcessHistory",
         "observed": "History persists authorization candidates and their selected ancestry, but not a complete identity universe for every sample.",
         "classification": "OBSERVABILITY_GAP"},
        {"join_id": "J10_failure_persistence", "location": "M7ProcessIdentityMonitor.capture",
         "observed": "The complete trigger snapshot is persisted, but the derived authorization view is not separately named/hashed in the failure record.",
         "classification": "PROVENANCE_GAP"},
    ]
    required_m8 = {
        "observation_universe": "Complete current all_processes identity view; used only for PID existence, identity equality, PID reuse and ancestry traversal.",
        "authorization_candidates": "Hash-enriched structural_processes plus bounded relevant history; role policies apply only here.",
        "view_conformance": ["universe_complete flag", "unique PID identity", "each current candidate maps to exactly one equal universe identity", "runner identity present and current"],
        "failure_persistence": ["full triggering process_snapshot.json", "separate derived_authorization_view.json", "hash/provenance link between them"],
        "history": "Retain every sampled PID/PPID/create-time identity in a compact complete identity universe plus hash/listener-bearing authorization candidates.",
    }
    protected = [
        "05_project/src/raven_m/controller/episode_controller.py",
        "05_project/src/raven_m/controller/protocol_v2_guard.py",
        "05_project/tests/scripts/test_protocol_v2_2_r79_r78_trace_replay.py",
    ]
    value = {
        "schema_version": "role_binding_timing.infra_m8.full_snapshot_ancestry_audit.v1",
        "mode": "read_only_frozen_m7_evidence", "generation_calls": 0, "device_mutations": 0,
        "m7_commits": ["d927624", "8a8ddb0", "d5d0247"],
        "m7_verdict_immutable": completion["status"], "m7_first_edge_immutable": completion["first_broken_edge"],
        "direct_trigger_evidence": {
            "runner_pid": runner["pid"], "runner_identity_key": runner["identity_key"],
            "runner_present_in_full_snapshot": runner["pid"] in all_by_pid,
            "runner_full_identity_matches": all_by_pid.get(runner["pid"], {}).get("identity_key") == runner["identity_key"],
            "runner_present_in_structural_subset": runner["pid"] in structural_by_pid,
            "full_process_count": len(trigger["all_processes"]),
            "authorization_candidate_count": len(trigger["structural_processes"]),
            "failure_sha256": digest(failure_path), "history_sha256": digest(history_path),
        },
        "filter_join_ledger": joins, "required_m8_contract": required_m8,
        "source_evidence": [
            {"path": m5.relative_to(REPOSITORY_ROOT).as_posix(), "sha256": digest(m5),
             "hits": line_hits(m5, ["all_processes", "structural_processes", "current = process_index", "combined:", "baseline_by_pid", "_ancestry_to_core"])},
            {"path": m7.relative_to(REPOSITORY_ROOT).as_posix(), "sha256": digest(m7),
             "hits": line_hits(m7, ["current.get", "_continuing_client_issues", "enrich_structural_records", "triggering_snapshot", "history.records()"])}
        ],
        "protected_wip": {path: digest(REPOSITORY_ROOT / path) for path in protected},
        "claim_evidence": {
            "domain_mismatch_verified": True, "m8_implementation_tested": False,
            "m8_runtime_tested": False, "held_out_tested": False,
            "role_binding_hypothesis_tested": False,
        },
        "decision": "ELIGIBLE_FOR_M8_OFFLINE_IMPLEMENTATION_ONLY",
    }
    output = OUTPUT_ROOT / "full_snapshot_ancestry_audit.json"
    output.write_bytes((json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    payload = output.read_bytes()
    (OUTPUT_ROOT / "artifact_manifest.json").write_bytes((json.dumps({
        "schema_version": "role_binding_timing.infra_m8.audit_manifest.v1",
        "artifacts": [{"path": output.name, "bytes": len(payload), "sha256": sha256(payload).hexdigest()}]
    }, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({"decision": value["decision"], "joins": len(joins),
                      "domain_mismatches": sum("MISMATCH" in item["classification"] for item in joins),
                      "runner_full": value["direct_trigger_evidence"]["runner_present_in_full_snapshot"],
                      "runner_structural": value["direct_trigger_evidence"]["runner_present_in_structural_subset"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
