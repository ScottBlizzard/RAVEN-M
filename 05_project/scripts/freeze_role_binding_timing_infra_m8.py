"""Create the one-time machine-readable INFRA-M8 input lock."""

from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

PROJECT_ROOT=Path(__file__).resolve().parents[1]; REPOSITORY_ROOT=PROJECT_ROOT.parent
LOCK_PATH=PROJECT_ROOT/"configs/role_binding_timing/infra_m8_full_snapshot_ancestry.lock.json"
M7_LOCK_PATH=PROJECT_ROOT/"configs/role_binding_timing/infra_m7_runner_adb_authority.lock.json"
M8_FILES=[
 "04_protocols/role_binding_timing/INFRA_M8_FULL_SNAPSHOT_ANCESTRY_V1.md",
 "reports/role_binding_timing/INFRA_M8_FULL_SNAPSHOT_ANCESTRY_AUDIT_2026-08-05.md",
 "reports/role_binding_timing/INFRA_M8_FREEZE_2026-08-05.md",
 "05_project/configs/role_binding_timing/infra_m8_full_snapshot_ancestry.json",
 "05_project/schemas/role_binding_timing_infra_m8_completion.v1.schema.json",
 "05_project/scripts/audit_role_binding_timing_infra_m8_full_snapshot_ancestry.py",
 "05_project/scripts/finalize_role_binding_timing_infra_m8.py",
 "05_project/scripts/freeze_role_binding_timing_infra_m8.py",
 "05_project/scripts/run_role_binding_timing_infra_m8.py",
 "05_project/scripts/run_role_binding_timing_infra_m8_offline_gates.py",
 "05_project/src/raven_m/role_binding_timing/infra_m8_full_snapshot_ancestry.py",
 "05_project/src/raven_m/role_binding_timing/infra_m8_terminal.py",
 "05_project/tests/role_binding_timing/test_infra_m8_full_snapshot_ancestry.py",
 "05_project/tests/role_binding_timing/test_infra_m8_runner_terminal.py",
 "05_project/artifacts/role_binding_timing/infra_m7_runner_adb_authority/qualification_completion.json",
 "05_project/artifacts/role_binding_timing/infra_m7_runner_adb_authority/process_identity/first_process_identity_failure.json",
 "05_project/artifacts/role_binding_timing/infra_m7_runner_adb_authority/process_identity/continuous_history/process_history.ndjson",
 "05_project/artifacts/role_binding_timing/infra_m7_runner_adb_authority_result_audit/result_audit.json",
 "reports/role_binding_timing/INFRA_M7_RESULT_2026-08-05.md",
]


def digest(path: Path)->str: return sha256(path.read_bytes()).hexdigest()


def main()->int:
    if LOCK_PATH.exists(): raise RuntimeError("M8_LOCK_ALREADY_EXISTS")
    m7=json.loads(M7_LOCK_PATH.read_text(encoding="utf-8"))
    for relative,expected in m7["files"].items():
        actual=digest(REPOSITORY_ROOT/relative)
        if actual!=expected: raise RuntimeError(f"M7_DEPENDENCY_DRIFT:{relative}:{actual}:{expected}")
    files=list(M8_FILES)+[M7_LOCK_PATH.relative_to(REPOSITORY_ROOT).as_posix()]+sorted(m7["files"])
    roots={"offline":PROJECT_ROOT/"artifacts/role_binding_timing/infra_m8_offline_gates",
           "audit":PROJECT_ROOT/"artifacts/role_binding_timing/infra_m8_full_snapshot_ancestry_audit"}
    for root in roots.values():
        if not root.is_dir(): raise RuntimeError(f"M8_EVIDENCE_ROOT_MISSING:{root}")
        files.extend(path.relative_to(REPOSITORY_ROOT).as_posix() for path in sorted(root.rglob("*")) if path.is_file())
    if len(files)!=len(set(files)): raise RuntimeError("DUPLICATE_LOCK_FILE")
    offline=json.loads((roots["offline"]/"offline_gate_result.json").read_text(encoding="utf-8"))
    audit=json.loads((roots["audit"]/"full_snapshot_ancestry_audit.json").read_text(encoding="utf-8"))
    if offline["overall_pass"] is not True or offline["generation_calls"]!=0 or offline["device_mutations"]!=0: raise RuntimeError("OFFLINE_GATE")
    if audit["decision"]!="ELIGIBLE_FOR_M8_OFFLINE_IMPLEMENTATION_ONLY": raise RuntimeError("AUDIT_BOUNDARY")
    hashes={relative:digest(REPOSITORY_ROOT/relative) for relative in files}
    lock={"schema_version":"role_binding_timing.infra_m8.lock.v1","run_id":"infra-m8-full-snapshot-ancestry-20260805",
      "predecessor_audit_commit":"960a81817ebdcc6de5bec8b306778a6b077ce8fc","created_at":datetime.now(timezone.utc).isoformat(),
      "generation_calls":0,"held_out_captures":0,"runtime_logs_are_immutable_inputs":False,
      "view_contract":{"observation_universe":"all_processes","authorization_candidates":"structural_processes","universe_grants_role":False,"truncated_behavior":"FAIL_CLOSED"},
      "offline":{"overall_pass":True,"result_sha256":digest(roots["offline"]/"offline_gate_result.json")},"files":hashes}
    LOCK_PATH.write_bytes((json.dumps(lock,indent=2,sort_keys=True)+"\n").encode("utf-8"))
    print(json.dumps({"lock":LOCK_PATH.relative_to(REPOSITORY_ROOT).as_posix(),"files":len(hashes),"sha256":digest(LOCK_PATH)},indent=2)); return 0


if __name__=="__main__": raise SystemExit(main())
