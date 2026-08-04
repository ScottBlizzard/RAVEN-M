"""Create the one-time machine-readable INFRA-M9 input lock."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
LOCK_PATH = PROJECT_ROOT / "configs/role_binding_timing/infra_m9_authorization_view_separation.lock.json"
M8_LOCK_PATH = PROJECT_ROOT / "configs/role_binding_timing/infra_m8_full_snapshot_ancestry.lock.json"
M9_FILES = [
    "04_protocols/role_binding_timing/INFRA_M9_AUTHORIZATION_VIEW_SEPARATION_V1.md",
    "reports/role_binding_timing/INFRA_M9_AUTHORIZATION_VIEW_AUDIT_2026-08-05.md",
    "reports/role_binding_timing/INFRA_M9_FREEZE_2026-08-05.md",
    "05_project/configs/role_binding_timing/infra_m9_authorization_view_separation.json",
    "05_project/schemas/role_binding_timing_infra_m9_completion.v1.schema.json",
    "05_project/scripts/audit_role_binding_timing_infra_m9_authorization_views.py",
    "05_project/scripts/finalize_role_binding_timing_infra_m9.py",
    "05_project/scripts/freeze_role_binding_timing_infra_m9.py",
    "05_project/scripts/run_role_binding_timing_infra_m9.py",
    "05_project/scripts/run_role_binding_timing_infra_m9_offline_gates.py",
    "05_project/src/raven_m/role_binding_timing/infra_m9_authorization_views.py",
    "05_project/src/raven_m/role_binding_timing/infra_m9_terminal.py",
    "05_project/tests/role_binding_timing/test_infra_m9_authorization_views.py",
    "05_project/tests/role_binding_timing/test_infra_m9_runner_terminal.py",
    "05_project/artifacts/role_binding_timing/infra_m8_full_snapshot_ancestry/qualification_completion.json",
    "05_project/artifacts/role_binding_timing/infra_m8_full_snapshot_ancestry/process_identity/first_process_identity_failure.json",
    "reports/role_binding_timing/INFRA_M8_RESULT_2026-08-05.md",
]


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if LOCK_PATH.exists():
        raise RuntimeError("M9_LOCK_ALREADY_EXISTS")
    m8 = json.loads(M8_LOCK_PATH.read_text(encoding="utf-8"))
    for relative, expected in m8["files"].items():
        actual = digest(REPOSITORY_ROOT / relative)
        if actual != expected:
            raise RuntimeError(f"M8_DEPENDENCY_DRIFT:{relative}:{actual}:{expected}")
    files = list(M9_FILES) + [M8_LOCK_PATH.relative_to(REPOSITORY_ROOT).as_posix()] + sorted(m8["files"])
    roots = {
        "offline": PROJECT_ROOT / "artifacts/role_binding_timing/infra_m9_offline_gates",
        "audit": PROJECT_ROOT / "artifacts/role_binding_timing/infra_m9_authorization_view_audit",
    }
    for root in roots.values():
        if not root.is_dir():
            raise RuntimeError(f"M9_EVIDENCE_ROOT_MISSING:{root}")
        files.extend(path.relative_to(REPOSITORY_ROOT).as_posix() for path in sorted(root.rglob("*")) if path.is_file())
    if len(files) != len(set(files)):
        raise RuntimeError("DUPLICATE_LOCK_FILE")
    offline = json.loads((roots["offline"] / "offline_gate_result.json").read_text(encoding="utf-8"))
    audit = json.loads((roots["audit"] / "authorization_view_audit.json").read_text(encoding="utf-8"))
    if offline["overall_pass"] is not True or offline["generation_calls"] != 0 or offline["device_mutations"] != 0:
        raise RuntimeError("OFFLINE_GATE")
    if audit["decision"] != "ELIGIBLE_FOR_M9_OFFLINE_IMPLEMENTATION_ONLY":
        raise RuntimeError("AUDIT_BOUNDARY")
    hashes = {relative: digest(REPOSITORY_ROOT / relative) for relative in files}
    lock = {
        "schema_version": "role_binding_timing.infra_m9.lock.v1",
        "run_id": "infra-m9-authorization-view-separation-20260805",
        "predecessor_audit_commit": "1c7aeea",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generation_calls": 0,
        "held_out_captures": 0,
        "runtime_logs_are_immutable_inputs": False,
        "view_contract": {
            "trusted_runner_root": "exact frozen PID+creation_time+path+command",
            "role_policy_input": "project_authorization_candidates_only",
            "support_role_authority": False,
            "unrelated_role_authority": False,
            "views_disjoint": True,
            "missing_or_ambiguous_chain_behavior": "FAIL_CLOSED",
        },
        "offline": {"overall_pass": True, "result_sha256": digest(roots["offline"] / "offline_gate_result.json")},
        "files": hashes,
    }
    LOCK_PATH.write_bytes((json.dumps(lock, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({
        "lock": LOCK_PATH.relative_to(REPOSITORY_ROOT).as_posix(),
        "files": len(hashes),
        "sha256": digest(LOCK_PATH),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
