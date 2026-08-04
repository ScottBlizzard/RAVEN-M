"""Create the one-time machine-readable INFRA-M7 input lock."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
LOCK_PATH = PROJECT_ROOT / "configs/role_binding_timing/infra_m7_runner_adb_authority.lock.json"
M6_LOCK_PATH = PROJECT_ROOT / "configs/role_binding_timing/infra_m6_display_observability.lock.json"

M7_FILES = [
    "04_protocols/role_binding_timing/INFRA_M7_RUNNER_ADB_CLIENT_AUTHORITY_V1.md",
    "reports/role_binding_timing/INFRA_M7_RUNNER_ADB_AUTHORITY_AUDIT_2026-08-05.md",
    "reports/role_binding_timing/INFRA_M7_FREEZE_2026-08-05.md",
    "05_project/configs/role_binding_timing/infra_m7_runner_adb_authority.json",
    "05_project/schemas/role_binding_timing_infra_m7_completion.v1.schema.json",
    "05_project/scripts/audit_role_binding_timing_infra_m7_adb_authority.py",
    "05_project/scripts/finalize_role_binding_timing_infra_m7.py",
    "05_project/scripts/freeze_role_binding_timing_infra_m7.py",
    "05_project/scripts/run_role_binding_timing_infra_m7.py",
    "05_project/scripts/run_role_binding_timing_infra_m7_offline_gates.py",
    "05_project/src/raven_m/role_binding_timing/infra_m7_adb_authority.py",
    "05_project/src/raven_m/role_binding_timing/infra_m7_terminal.py",
    "05_project/tests/role_binding_timing/test_infra_m7_adb_authority.py",
    "05_project/tests/role_binding_timing/test_infra_m7_runner_terminal.py",
]


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if LOCK_PATH.exists():
        raise RuntimeError("M7_LOCK_ALREADY_EXISTS")
    m6_lock = json.loads(M6_LOCK_PATH.read_text(encoding="utf-8"))
    for relative, expected in m6_lock["files"].items():
        actual = digest(REPOSITORY_ROOT / relative)
        if actual != expected:
            raise RuntimeError(f"M6_DEPENDENCY_DRIFT:{relative}:{actual}:{expected}")
    files = list(M7_FILES) + [M6_LOCK_PATH.relative_to(REPOSITORY_ROOT).as_posix()] + sorted(m6_lock["files"])
    roots = {
        "attempt_01": PROJECT_ROOT / "artifacts/role_binding_timing/infra_m7_offline_gates",
        "attempt_02": PROJECT_ROOT / "artifacts/role_binding_timing/infra_m7_offline_gates_attempt_02",
        "audit": PROJECT_ROOT / "artifacts/role_binding_timing/infra_m7_runner_adb_authority_audit",
    }
    for root in roots.values():
        if not root.is_dir():
            raise RuntimeError(f"M7_EVIDENCE_ROOT_MISSING:{root}")
        files.extend(path.relative_to(REPOSITORY_ROOT).as_posix() for path in sorted(root.rglob("*")) if path.is_file())
    if len(files) != len(set(files)):
        raise RuntimeError("DUPLICATE_LOCK_FILE")
    attempt_01 = json.loads((roots["attempt_01"] / "incomplete_gate_record.json").read_text(encoding="utf-8"))
    attempt_02 = json.loads((roots["attempt_02"] / "offline_gate_result.json").read_text(encoding="utf-8"))
    if attempt_01["overall_verdict"] != "INCOMPLETE_NOT_PASS_OR_FAIL" or attempt_01["terminal_result_written"] is not False:
        raise RuntimeError("ATTEMPT_01_BOUNDARY")
    if attempt_02["overall_pass"] is not True or attempt_02["generation_calls"] != 0 or attempt_02["device_mutations"] != 0:
        raise RuntimeError("ATTEMPT_02_GATE")
    hashes = {relative: digest(REPOSITORY_ROOT / relative) for relative in files}
    lock = {
        "schema_version": "role_binding_timing.infra_m7.lock.v1",
        "run_id": "infra-m7-runner-adb-authority-20260805",
        "predecessor_audit_commit": "d9276246402e23b2347bb69777d2a8782b58e895",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generation_calls": 0, "held_out_captures": 0,
        "runtime_logs_are_immutable_inputs": False,
        "ordinary_runner_client_authority": {
            "global_prefix": ["-P", "5038"], "max_active_lifetime_seconds": 45.0,
            "subcommand_allowlist": None, "listener_ownership_allowed": False,
            "direct_runner_parent_required": True,
        },
        "offline_attempts": {
            "attempt_01": {"verdict": "INCOMPLETE_NOT_PASS_OR_FAIL", "reason": "AUDIT_JSON_FIELD_NAME",
                           "record_sha256": digest(roots["attempt_01"] / "incomplete_gate_record.json")},
            "attempt_02": {"overall_pass": True,
                           "result_sha256": digest(roots["attempt_02"] / "offline_gate_result.json")},
        },
        "files": hashes,
    }
    LOCK_PATH.write_bytes((json.dumps(lock, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({"lock": LOCK_PATH.relative_to(REPOSITORY_ROOT).as_posix(),
                      "files": len(hashes), "sha256": digest(LOCK_PATH)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
