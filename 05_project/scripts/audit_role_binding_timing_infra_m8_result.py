"""Evidence-only audit of the frozen INFRA-M8 live result."""

from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT=Path(__file__).resolve().parents[1]; REPOSITORY_ROOT=PROJECT_ROOT.parent
RESULT_ROOT=PROJECT_ROOT/"artifacts/role_binding_timing/infra_m8_full_snapshot_ancestry"
AUDIT_ROOT=PROJECT_ROOT/"artifacts/role_binding_timing/infra_m8_full_snapshot_ancestry_result_audit"
sys.path.insert(0,str(PROJECT_ROOT/"src"))
from raven_m.role_binding_timing.infra_m4_terminal_accounting import atomic_write_json, utc_now  # noqa: E402
from raven_m.role_binding_timing.infra_m5_process_identity import ExecutableHashCache, RELEVANT_NAMES, normalized_path  # noqa: E402
from raven_m.role_binding_timing.infra_m8_full_snapshot_ancestry import build_m8_snapshot  # noqa: E402


def load(path:Path)->Any:return json.loads(path.read_text(encoding="utf-8"))
def digest(path:Path)->str:return sha256(path.read_bytes()).hexdigest()


def manifest_check()->dict[str,Any]:
    path=RESULT_ROOT/"artifact_manifest.json"; manifest=load(path); issues=[]
    for item in manifest["artifacts"]:
        target=REPOSITORY_ROOT/item["path"]
        if not target.is_file():issues.append(f"MISSING:{item['path']}");continue
        if target.stat().st_size!=item["bytes"]:issues.append(f"SIZE:{item['path']}")
        if digest(target)!=item["sha256"]:issues.append(f"HASH:{item['path']}")
    return {"passed":not issues,"entries":len(manifest["artifacts"]),"sha256":digest(path),"issues":issues}


def main()->int:
    if AUDIT_ROOT.exists():raise RuntimeError("M8_RESULT_AUDIT_ROOT_NOT_FRESH")
    AUDIT_ROOT.mkdir(parents=True)
    completion=load(RESULT_ROOT/"qualification_completion.json"); validation=load(RESULT_ROOT/"terminal_validation.json")
    failure=load(RESULT_ROOT/"process_identity/first_process_identity_failure.json")
    snapshot=failure["triggering_snapshot"]; view=failure["derived_authorization_view"]
    missing=[r for r in view["authorization_candidates"] if r.get("identity_key") is None]
    relevant=[r for r in view["authorization_candidates"] if str(r.get("name") or "").casefold() in RELEVANT_NAMES]
    ancestry_only=[r for r in view["authorization_candidates"] if str(r.get("name") or "").casefold() not in RELEVANT_NAMES]
    missing_pids={r.get("pid") for r in missing}; children=[r for r in snapshot["all_processes"] if r.get("ppid") in missing_pids]
    current=build_m8_snapshot(gate="m8_post_run_audit",sequence=0,cache=ExecutableHashCache())
    overlay=load(PROJECT_ROOT/"configs/role_binding_timing/infra_m8_full_snapshot_ancestry.json")
    m7=load(REPOSITORY_ROOT/overlay["base_config"]); m6=load(REPOSITORY_ROOT/m7["base_config"])
    project_paths={normalized_path(spec["path"]) for spec in m6["process_identity"]["binaries"].values() if isinstance(spec,dict) and "path" in spec}
    owned=[r for r in current["structural_processes"] if normalized_path(r.get("exe")) in project_paths]
    protected={p:digest(REPOSITORY_ROOT/p) for p in m6["protected_wip"]}
    source=PROJECT_ROOT/"src/raven_m/role_binding_timing/infra_m5_process_identity.py"; source_text=source.read_text(encoding="utf-8")
    checks={
      "immutable_status":completion["status"]=="PROCESS_IDENTITY_FAILED",
      "exact_first_edge":completion["first_broken_edge"]=="PROCESS_IDENTITY:prelaunch_baseline:AUTHORIZATION_CANDIDATE_IDENTITY_MISSING",
      "terminal_schema":validation["passed"] is True,
      "one_completion":len(list(RESULT_ROOT.rglob("qualification_completion.json")))==1,
      "eight_journal_entries":len(list((RESULT_ROOT/"phase_journal/entries").glob("*.json")))==8,
      "full_and_derived_views_persisted":bool(snapshot.get("all_processes")) and bool(view.get("authorization_candidates")),
      "missing_identity_observed":len(missing)>=1,
      "missing_rows_are_not_relevant_roles":all(str(r.get("name") or "").casefold() not in RELEVANT_NAMES for r in missing),
      "missing_row_has_external_child":bool(children),
      "source_adds_ancestry_to_structural":"for parent in ancestry_records(record, by_pid):" in source_text,
      "no_runtime_stage":completion["process_identity"]["core"]=={} and completion["burn_in"]["completed_cycles"]==0 and completion["a11y"]["settings"]["completed"]==0,
      "zero_generation_heldout":completion["generation_calls"]==0 and completion["model_tokens"]==0 and completion["held_out_captures"]==0,
      "controlled_ports_empty":all(current["listeners"][str(p)]==[] for p in (5037,5038,5554,5555,8554)),
      "project_runtime_absent":not owned,"log_seal_passed":completion["log_seal"]["passed"] is True and completion["log_seal"].get("no_live_logs_created") is True,
      "protected_unchanged":protected==m6["protected_wip"]==completion["protected_wip_after"],"manifest":manifest_check()["passed"]}
    result={"schema_version":"role_binding_timing.infra_m8.result_audit.v1","created_at":utc_now(),
      "verdict":"FAIL_AUTHORIZATION_VIEW_DERIVATION","immutable_completion_status":completion["status"],"immutable_first_broken_edge":completion["first_broken_edge"],
      "generation_calls":0,"held_out_captures":0,"root_cause_classification":"STRUCTURAL_VIEW_CONFLATES_ROLE_CANDIDATES_WITH_ANCESTRY_SUPPORT",
      "direct_evidence":{"snapshot_sha256":digest(RESULT_ROOT/"process_identity/snapshots/0001_prelaunch_baseline/process_snapshot.json"),
        "derived_view_sha256":digest(RESULT_ROOT/"process_identity/snapshots/0001_prelaunch_baseline/derived_authorization_view.json"),
        "structural_count":len(view["authorization_candidates"]),"relevant_role_candidate_count":len(relevant),"ancestry_support_count":len(ancestry_only),
        "missing_identity_rows":missing,"children_of_missing_rows":children,"m5_source_sha256":digest(source)},
      "inference":"M5 structural_processes contains relevant processes and selected ancestors. M8 treated every structural row as an authorization candidate, so an AccessDenied external ancestor with no identity failed candidate completeness even though it had no project role. The two-view contract was therefore not correctly derived.",
      "terminal":{"validation":validation,"manifest":manifest_check(),"snapshots":completion["process_identity"]["snapshot_count"]},
      "post_run_runtime":{"listeners":current["listeners"],"project_runtime_records":owned},"protected_wip":protected,"checks":checks,"overall_audit_pass":all(checks.values()),
      "claim_evidence":{"full_snapshot_ancestry_qualified":False,"authorization_view_qualified":False,"exclusive_5038_tested":False,"emulator_launch_tested":False,"boot_tested":False,"display_tested":False,"burn_in_tested":False,"a11y_tested":False,"dev_grid_tested":False,"v0_3_preparation_authorized":False,"held_out_tested":False,"role_binding_hypothesis_tested":False},
      "stop_decision":"STOP_INFRA_M8_NO_RETRY"}
    atomic_write_json(AUDIT_ROOT/"result_audit.json",result,replace=False); payload=(AUDIT_ROOT/"result_audit.json").read_bytes()
    atomic_write_json(AUDIT_ROOT/"artifact_manifest.json",{"schema_version":"role_binding_timing.infra_m8.result_audit_manifest.v1","artifacts":[{"path":"result_audit.json","bytes":len(payload),"sha256":sha256(payload).hexdigest()}]},replace=False)
    print(json.dumps({"verdict":result["verdict"],"overall_audit_pass":result["overall_audit_pass"],"missing_rows":len(missing),"relevant":len(relevant),"ancestry_support":len(ancestry_only),"listeners":current["listeners"]},indent=2));return 0 if result["overall_audit_pass"] else 2


if __name__=="__main__":raise SystemExit(main())
