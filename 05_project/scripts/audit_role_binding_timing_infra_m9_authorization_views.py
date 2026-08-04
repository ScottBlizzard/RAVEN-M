"""Read-only audit of the overloaded M8 structural_processes projection."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
OUTPUT_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m9_authorization_view_audit"
PROTECTED = (
    "05_project/src/raven_m/controller/episode_controller.py",
    "05_project/src/raven_m/controller/protocol_v2_guard.py",
    "05_project/tests/scripts/test_protocol_v2_2_r79_r78_trace_replay.py",
)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def line_hits(path: Path, needle: str) -> list[dict[str, object]]:
    return [
        {"line": number, "text": line.strip()}
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if needle in line
    ]


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise RuntimeError("M9_AUDIT_ROOT_NOT_FRESH")
    OUTPUT_ROOT.mkdir(parents=True)
    m8_source = PROJECT_ROOT / "src/raven_m/role_binding_timing/infra_m8_full_snapshot_ancestry.py"
    m5_source = PROJECT_ROOT / "src/raven_m/role_binding_timing/infra_m5_process_identity.py"
    failure_path = PROJECT_ROOT / (
        "artifacts/role_binding_timing/infra_m8_full_snapshot_ancestry/"
        "process_identity/first_process_identity_failure.json"
    )
    completion_path = PROJECT_ROOT / (
        "artifacts/role_binding_timing/infra_m8_full_snapshot_ancestry/qualification_completion.json"
    )
    failure = json.loads(failure_path.read_text(encoding="utf-8"))
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    trigger = failure["triggering_snapshot"]
    structural = trigger["structural_processes"]
    relevant_names = {
        "adb.exe", "emulator.exe", "qemu-system-x86_64-headless.exe",
        "crashpad_handler.exe", "netsimd.exe",
    }
    name_selected = [
        row for row in structural
        if str(row.get("name") or "").casefold() in relevant_names
    ]
    ancestry_selected = [row for row in structural if row not in name_selected]
    use_ledger = [
        {
            "use": "snapshot_view_contract",
            "classification": "OVERLOADED_DECLARATION",
            "effect": "Names all structural_processes as authorization candidates although the producer adds selected ancestors.",
        },
        {
            "use": "derive_authorization_view",
            "classification": "DIRECT_FALSE_REJECTION",
            "effect": "Requires candidate identity completeness for every structural row, including AccessDenied ancestry-only rows.",
        },
        {
            "use": "policy_evaluate_combined",
            "classification": "ROLE_LOOP_PARTIALLY_FILTERED",
            "effect": "The role loop filters by broad process name, but path/hash authority is evaluated only later; unrelated same-name binaries enter policy evaluation.",
        },
        {
            "use": "policy_history",
            "classification": "AUTHORITY_HISTORY_CONTAMINATION",
            "effect": "All structural rows are retained in the same history store used for role candidates.",
        },
        {
            "use": "monitor_baseline",
            "classification": "BASELINE_CANDIDATE_AMBIGUITY",
            "effect": "Inherited baseline reads structural_processes and broad relevant names rather than an explicit candidate view.",
        },
        {
            "use": "monitor_discovery",
            "classification": "AUTHORITY_HISTORY_CONTAMINATION",
            "effect": "Discovery adds the overloaded structural set to policy history.",
        },
        {
            "use": "continuous_history",
            "classification": "OVERLOADED_PERSISTENCE",
            "effect": "The history event calls an ancestry-enriched projection authorization_candidates.",
        },
        {
            "use": "register_core_from_snapshot",
            "classification": "CORE_ADOPTION_RISK",
            "effect": "Inherited core registration selects from structural_processes without a view-type assertion.",
        },
        {
            "use": "failure_persistence",
            "classification": "PROVENANCE_PRESENT_SEMANTICS_WRONG",
            "effect": "Full trigger and derived view are preserved, but the derived candidate semantics are the overloaded M8 semantics.",
        },
    ]
    view_contract = {
        "trusted_runner_root": {
            "membership": "exact frozen PID+creation_time+path+command identity",
            "authority": "ancestry root proof only",
            "role_policy_evaluated": False,
        },
        "project_authorization_candidates": {
            "membership": "locked project binary/path/hash, controlled-port owner, or descendant admitted under a frozen role policy",
            "authority": "only class eligible for project-role completeness and role assignment",
            "role_policy_evaluated": True,
        },
        "support_only_ancestry_nodes": {
            "membership": "current full-snapshot nodes needed only to connect a candidate chain",
            "authority": "parent existence, creation ordering and PID-reuse evidence only",
            "role_policy_evaluated": False,
        },
        "unrelated_observed_processes": {
            "membership": "all remaining full-snapshot rows",
            "authority": "observation only; never adopted, killed or role-assigned",
            "role_policy_evaluated": False,
        },
    }
    value = {
        "schema_version": "role_binding_timing.infra_m9.authorization_view_audit.v1",
        "mode": "READ_ONLY_FROZEN_M8_EVIDENCE",
        "generation_calls": 0,
        "device_mutations": 0,
        "m8_commits": ["960a818", "35a0d06", "7135029"],
        "m8_verdict_immutable": completion["status"],
        "m8_first_edge_immutable": completion["first_broken_edge"],
        "direct_evidence": {
            "failure_sha256": digest(failure_path),
            "completion_sha256": digest(completion_path),
            "full_observation_count": len(trigger["all_processes"]),
            "structural_projection_count": len(structural),
            "broad_name_selected_count": len(name_selected),
            "ancestry_only_count": len(ancestry_selected),
            "missing_identity_pids": [row.get("pid") for row in structural if not row.get("identity_key")],
            "broad_name_selected_paths": [row.get("exe") for row in name_selected],
            "controlled_ports_present": {
                port: trigger["listeners"].get(port) for port in ("5037", "5038", "5554", "5555", "8554")
            },
        },
        "structural_processes_use_ledger": use_ledger,
        "required_disjoint_views": view_contract,
        "global_vetoes_independent_of_membership": [
            "any 5037 listener",
            "controlled port owned by a support-only or unrelated row",
            "trusted runner PID/creation/path/command drift",
            "missing or ambiguous required direct ancestry segment",
            "candidate PID reuse or incomplete role evidence",
        ],
        "required_type_assertions": [
            "support-only and unrelated rows cannot be registered as core",
            "support-only and unrelated rows cannot be assigned a project role",
            "support-only and unrelated rows cannot be cleanup kill targets",
            "support-only and unrelated rows cannot own controlled ports",
            "every full-snapshot PID appears in exactly one non-root derived view, except the separately frozen runner root",
            "the full trigger snapshot and every derived view are persisted and hashed",
        ],
        "source_evidence": [
            {"path": m8_source.relative_to(REPOSITORY_ROOT).as_posix(), "sha256": digest(m8_source),
             "structural_processes_hits": line_hits(m8_source, "structural_processes")},
            {"path": m5_source.relative_to(REPOSITORY_ROOT).as_posix(), "sha256": digest(m5_source),
             "structural_processes_hits": line_hits(m5_source, "structural_processes")},
        ],
        "protected_wip": {path: digest(REPOSITORY_ROOT / path) for path in PROTECTED},
        "claim_evidence": {
            "m8_overloaded_view_verified": True,
            "m9_implementation_tested": False,
            "runtime_tested": False,
            "a11y_tested": False,
            "held_out_tested": False,
            "role_binding_hypothesis_tested": False,
        },
        "decision": "ELIGIBLE_FOR_M9_OFFLINE_IMPLEMENTATION_ONLY",
    }
    output = OUTPUT_ROOT / "authorization_view_audit.json"
    output.write_bytes((json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    payload = output.read_bytes()
    manifest = {
        "schema_version": "role_binding_timing.infra_m9.audit_manifest.v1",
        "artifacts": [{"path": output.name, "bytes": len(payload), "sha256": sha256(payload).hexdigest()}],
    }
    (OUTPUT_ROOT / "artifact_manifest.json").write_bytes(
        (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    )
    print(json.dumps({
        "decision": value["decision"],
        "structural_projection_count": len(structural),
        "broad_name_selected_count": len(name_selected),
        "ancestry_only_count": len(ancestry_selected),
        "uses_audited": len(use_ledger),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
