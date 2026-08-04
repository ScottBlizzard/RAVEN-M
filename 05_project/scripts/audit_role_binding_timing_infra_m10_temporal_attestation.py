"""Read-only closest-root-cause audit for INFRA-M10."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
OUTPUT_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m10_temporal_attestation_audit"
PROTECTED = (
    "05_project/src/raven_m/controller/episode_controller.py",
    "05_project/src/raven_m/controller/protocol_v2_guard.py",
    "05_project/tests/scripts/test_protocol_v2_2_r79_r78_trace_replay.py",
)
EXPECTED_PROTECTED = {
    PROTECTED[0]: "fc0e82e0fde90119365d4f685f080eb4519bf2f602e4bda58de5d4809a40fe33",
    PROTECTED[1]: "ff89d6b70be4b4738646d262beb67d7b7e932e9eb95956d940b1c5000a999d10",
    PROTECTED[2]: "5bb1f1e3de673a1072cfee62938b761a62fd69c187d5eadf54bc46b115a3fd0a",
}


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPOSITORY_ROOT, check=True, capture_output=True, text=True, timeout=30).stdout.strip()


def line_hits(path: Path, needles: list[str]) -> list[dict[str, object]]:
    return [
        {"line": number, "text": line.strip()}
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if any(needle in line for needle in needles)
    ]


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise RuntimeError("M10_AUDIT_ROOT_NOT_FRESH")
    OUTPUT_ROOT.mkdir(parents=True)
    m9_source = PROJECT_ROOT / "src/raven_m/role_binding_timing/infra_m9_authorization_views.py"
    m8_source = PROJECT_ROOT / "src/raven_m/role_binding_timing/infra_m8_full_snapshot_ancestry.py"
    completion_path = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m9_authorization_view_separation/qualification_completion.json"
    failure_path = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m9_authorization_view_separation/process_identity/first_process_identity_failure.json"
    manifest_path = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m9_authorization_view_separation/artifact_manifest.json"
    result_audit_path = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m9_result_audit/result_audit.json"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    failure = json.loads(failure_path.read_text(encoding="utf-8"))
    result_audit = json.loads(result_audit_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_failures = []
    for item in manifest["artifacts"]:
        path = REPOSITORY_ROOT / item["path"]
        actual = digest(path) if path.is_file() else None
        if actual != item["sha256"]:
            manifest_failures.append({"path": item["path"], "expected": item["sha256"], "actual": actual})
    freeze_tag = "role-binding-timing-infra-m9-freeze-20260805"
    result_tag = "role-binding-timing-infra-m9-result-20260805"
    tag_evidence = {
        "freeze": {"tag": freeze_tag, "commit": git("rev-list", "-n", "1", freeze_tag), "object": git("rev-parse", freeze_tag)},
        "result": {"tag": result_tag, "commit": git("rev-list", "-n", "1", result_tag), "object": git("rev-parse", result_tag)},
    }
    protected = {relative: digest(REPOSITORY_ROOT / relative) for relative in PROTECTED}
    mechanism = result_audit["failure_mechanism"]
    root_causes = [
        {
            "id": "RC1_SUPPORT_PROJECTION_HASH_LOSS",
            "direct_evidence": "The one current failed candidate had a current support parent. The frozen structural source contained the official cmd.exe hash, while the derived support row omitted exe_sha256.",
            "count": mechanism["current_support_hash_loss_count"],
            "closest_code_path": "derive_process_views builds candidates with rich overlay, then builds support from full_index without the rich overlay.",
        },
        {
            "id": "RC2_HISTORY_SUPPORT_PROOF_LOSS",
            "direct_evidence": "Continuous history serializes support through compact_identity_universe, which excludes exe_sha256 and command_line.",
            "count": mechanism["coobserved_parent_count"],
            "closest_code_path": "M9ContinuousProcessHistory stores compact support rows instead of lossless proof rows.",
        },
        {
            "id": "RC3_TEMPORAL_JOIN_DOMAIN_MISMATCH",
            "direct_evidence": "All 13 children and parents were co-observed in history; 12 children were absent at the later trigger, but recent candidates were evaluated against the later current universe.",
            "count": mechanism["exited_before_trigger_count"],
            "closest_code_path": "evaluate merges recent_records while inherited _ancestry_to_core traverses only current all_processes.",
        },
    ]
    required_contract = {
        "source_boundary": "M9 complete per-sample snapshot remains the only raw source; M10 stores derived attestations with source hashes rather than inventing evidence.",
        "support_row_required_fields": [
            "identity_key(pid+create_time)", "pid", "create_time", "ppid", "parent_identity_key",
            "exe", "exe_sha256", "command_line", "cmdline_items", "sample_sequence", "sample_time",
            "source_record_sha256", "snapshot_sha256", "partition_sha256", "access_error",
        ],
        "same_sample_only": True,
        "same_run_only": True,
        "cross_sample_join_forbidden": True,
        "cross_run_replay_forbidden": True,
        "pid_only_or_path_only_authority_forbidden": True,
        "exited_candidate_effect": "historical legality only; never current authority",
        "live_candidate_effect": "birth provenance only after exact current identity/hash/cmdline and complete same-sample chain",
        "current_evidence_priority": True,
        "current_history_conflict": "FAIL_CLOSED",
        "support_role_authority": False,
        "support_adopt_kill_cleanup_forbidden": True,
        "support_controlled_port_forbidden": True,
        "terminal_expiry_required": True,
    }
    value = {
        "schema_version": "role_binding_timing.infra_m10.closest_root_cause_audit.v1",
        "mode": "READ_ONLY_FROZEN_M9_EVIDENCE",
        "generation_calls": 0,
        "device_mutations": 0,
        "m9_immutable": {
            "status": completion["status"],
            "first_broken_edge": completion["first_broken_edge"],
            "completion_sha256": digest(completion_path),
            "failure_sha256": digest(failure_path),
            "result_audit_sha256": digest(result_audit_path),
            "manifest_sha256": digest(manifest_path),
            "manifest_artifacts": len(manifest["artifacts"]),
            "manifest_passed": not manifest_failures,
            "manifest_failures": manifest_failures,
            "tag_evidence": tag_evidence,
        },
        "direct_counts": {
            "failed_candidates": mechanism["failed_candidate_count"],
            "coobserved_parents": mechanism["coobserved_parent_count"],
            "exited_before_trigger": mechanism["exited_before_trigger_count"],
            "current_at_trigger": mechanism["current_issue_candidate_count"],
            "current_support_hash_loss": mechanism["current_support_hash_loss_count"],
            "all_exact_locked_adb": mechanism["all_exact_locked_adb_binary"],
        },
        "closest_root_causes": root_causes,
        "required_m10_contract": required_contract,
        "source_evidence": [
            {"path": m9_source.relative_to(REPOSITORY_ROOT).as_posix(), "sha256": digest(m9_source),
             "hits": line_hits(m9_source, ["source = {**full_index[pid]", "support = [dict(full_index[pid])", "compact_identity_universe(view[\"support_only_ancestry_nodes\"])", "recent_records=self.history.records()"])},
            {"path": m8_source.relative_to(REPOSITORY_ROOT).as_posix(), "sha256": digest(m8_source),
             "hits": line_hits(m8_source, ["def _ancestry_to_core", "stale history grants no ancestry", "MISSING_CURRENT_UNIVERSE"])},
        ],
        "protected_wip": {"observed": protected, "expected": EXPECTED_PROTECTED, "passed": protected == EXPECTED_PROTECTED},
        "claim_evidence": {
            "m9_failure_reinterpreted": False,
            "m10_root_cause_bounded": True,
            "m10_implementation_tested": False,
            "m10_runtime_tested": False,
            "held_out_tested": False,
            "role_binding_hypothesis_tested": False,
        },
        "decision": "ELIGIBLE_FOR_M10_OFFLINE_IMPLEMENTATION_ONLY",
    }
    required = [
        completion["status"] == "PROCESS_IDENTITY_FAILED",
        not manifest_failures,
        tag_evidence["freeze"]["commit"] == "d9e812b3bacd2d06da890086a106af94c95c5347",
        tag_evidence["result"]["commit"] == "613b338fce1eab5ecf8c29e6a95702dcfd04eca6",
        protected == EXPECTED_PROTECTED,
        mechanism["failed_candidate_count"] == 13,
        mechanism["coobserved_parent_count"] == 13,
        mechanism["exited_before_trigger_count"] == 12,
        mechanism["current_issue_candidate_count"] == 1,
        mechanism["current_support_hash_loss_count"] == 1,
    ]
    value["audit_passed"] = all(required)
    output = OUTPUT_ROOT / "closest_root_cause_audit.json"
    output.write_bytes((json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    payload = output.read_bytes()
    (OUTPUT_ROOT / "artifact_manifest.json").write_bytes((json.dumps({
        "schema_version": "role_binding_timing.infra_m10.audit_manifest.v1",
        "artifacts": [{"path": output.name, "bytes": len(payload), "sha256": sha256(payload).hexdigest()}],
    }, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({
        "audit_passed": value["audit_passed"],
        "decision": value["decision"],
        "root_causes": len(root_causes),
        "failed_candidates": value["direct_counts"]["failed_candidates"],
        "exited_current_split": [value["direct_counts"]["exited_before_trigger"], value["direct_counts"]["current_at_trigger"]],
    }, indent=2))
    return 0 if value["audit_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
