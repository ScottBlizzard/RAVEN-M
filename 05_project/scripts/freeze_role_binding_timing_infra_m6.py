"""Create the one-time machine-readable INFRA-M6 input lock."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
LOCK_PATH = PROJECT_ROOT / "configs/role_binding_timing/infra_m6_display_observability.lock.json"
M5_LOCK_PATH = PROJECT_ROOT / "configs/role_binding_timing/infra_m5_process_identity_semantics.lock.json"


M6_FILES = [
    "04_protocols/role_binding_timing/INFRA_M6_DISPLAY_OBSERVABILITY_V1.md",
    "reports/role_binding_timing/INFRA_M6_FREEZE_2026-08-05.md",
    "05_project/configs/role_binding_timing/infra_m6_display_observability.json",
    "05_project/schemas/role_binding_timing_infra_m6_completion.v1.schema.json",
    "05_project/scripts/finalize_role_binding_timing_infra_m6.py",
    "05_project/scripts/freeze_role_binding_timing_infra_m6.py",
    "05_project/scripts/run_role_binding_timing_infra_m6.py",
    "05_project/scripts/run_role_binding_timing_infra_m6_offline_gates.py",
    "05_project/src/raven_m/role_binding_timing/infra_m6_display_observability.py",
    "05_project/src/raven_m/role_binding_timing/infra_m6_terminal.py",
    "05_project/tests/role_binding_timing/test_infra_m6_display_observability.py",
]


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if LOCK_PATH.exists():
        raise RuntimeError("M6_LOCK_ALREADY_EXISTS")
    m5_lock = json.loads(M5_LOCK_PATH.read_text(encoding="utf-8"))
    for relative, expected in m5_lock["files"].items():
        actual = digest(REPOSITORY_ROOT / relative)
        if actual != expected:
            raise RuntimeError(f"M5_DEPENDENCY_DRIFT:{relative}:{actual}:{expected}")
    files = list(M6_FILES) + sorted(m5_lock["files"])
    for root_name in ("infra_m6_offline_gates", "infra_m6_offline_gates_attempt_02"):
        root = PROJECT_ROOT / "artifacts/role_binding_timing" / root_name
        if not (root / "offline_gate_result.json").is_file():
            raise RuntimeError(f"OFFLINE_RESULT_MISSING:{root_name}")
        files.extend(path.relative_to(REPOSITORY_ROOT).as_posix() for path in sorted(root.rglob("*")) if path.is_file())
    if len(files) != len(set(files)):
        raise RuntimeError("DUPLICATE_LOCK_FILE")
    hashes = {relative: digest(REPOSITORY_ROOT / relative) for relative in files}
    attempt_01 = json.loads((PROJECT_ROOT / "artifacts/role_binding_timing/infra_m6_offline_gates/offline_gate_result.json").read_text(encoding="utf-8"))
    attempt_02 = json.loads((PROJECT_ROOT / "artifacts/role_binding_timing/infra_m6_offline_gates_attempt_02/offline_gate_result.json").read_text(encoding="utf-8"))
    if attempt_01["overall_pass"] is not False or attempt_02["overall_pass"] is not True:
        raise RuntimeError("OFFLINE_ATTEMPT_VERDICT_BOUNDARY")
    lock = {
        "schema_version": "role_binding_timing.infra_m6.lock.v1",
        "run_id": "infra-m6-display-observability-20260805",
        "predecessor_audit_commit": "5503317e8e990825db14c70db277e3d8f04c8f4c",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generation_calls": 0,
        "held_out_captures": 0,
        "runtime_logs_are_immutable_inputs": False,
        "offline_attempts": {
            "attempt_01": {"overall_pass": False, "first_broken_edge": "PSUTIL_HASH_TRANSCRIPTION", "result_sha256": digest(PROJECT_ROOT / "artifacts/role_binding_timing/infra_m6_offline_gates/offline_gate_result.json")},
            "attempt_02": {"overall_pass": True, "result_sha256": digest(PROJECT_ROOT / "artifacts/role_binding_timing/infra_m6_offline_gates_attempt_02/offline_gate_result.json")}
        },
        "files": hashes,
    }
    LOCK_PATH.write_bytes((json.dumps(lock, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({"lock": LOCK_PATH.relative_to(REPOSITORY_ROOT).as_posix(), "files": len(hashes), "sha256": digest(LOCK_PATH)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
