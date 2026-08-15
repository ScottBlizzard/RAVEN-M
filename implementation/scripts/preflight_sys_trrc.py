#!/usr/bin/env python3
"""Zero-generation source/config/replay preflight for one SYS-TRRC mode."""
from __future__ import annotations
import argparse, json, os, subprocess, sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))
from raven_m.official_qwen_mobile import sys_trrc_contract as contract  # noqa:E402
from raven_m.official_qwen_mobile.protocol import A1_WORKING_MEMORY_SYSTEM_PROMPT  # noqa:E402
from raven_m.official_qwen_mobile import sys_trrc_recovery as recovery  # noqa:E402
from raven_m.official_qwen_mobile.sys_trrc_token_budget import ExactQwenMultimodalTokenProjector  # noqa:E402

EXPECTED_COMMON_PROMPT = """You are a bounded auxiliary reasoner. You do not act, terminate, edit memory,
or decide whether the task is complete.

{role_instruction}

Use only the supplied task goal, current screenshot, exact R2 ledger, bounded
recent executed-action summaries, and detector evidence. The current screenshot
is authoritative. Do not use hidden UI, evaluator information, future state,
or outside task knowledge. Return exactly three single-line fields:

ASSESSMENT: <brief visible-evidence assessment>
RECOMMENDATION: <one concise suggestion for the executor's next decision>
VISIBLE_CHECK: <what visible evidence the executor should inspect next>"""
EXPECTED_GENERIC_ROLE = """Independently review the supplied visible evidence and provide one concise
next-decision suggestion."""
EXPECTED_FULL_ROLE = """Identify the currently recurring or visibly unsupported approach and provide
one materially different, screenshot-grounded recovery strategy for the next
decision."""
EXPECTED_WRAPPER = """AUXILIARY ADVICE (non-authoritative; expires after this request):
ASSESSMENT: {assessment}
RECOMMENDATION: {recommendation}
VISIBLE_CHECK: {visible_check}
The current screenshot is authoritative. The executor must decide the next action."""

SOURCE_FILES = contract.SOURCE_FILES

TOKEN_INPUT_DIR = ROOT / "evidence/sys_trrc/token_projection_inputs"


def _projection_evidence(replay: dict) -> dict:
    manifest_path=TOKEN_INPUT_DIR/"manifest.json"; manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("schema")!="sys_trrc_token_projection_inputs_v1" or manifest.get("status")!="PASS" or manifest.get("generation_calls")!=0 or manifest.get("errors")!=[] or manifest.get("content_sha256")!=contract.content_sha256(manifest)): raise RuntimeError("projection input manifest integrity")
    source=manifest.get("source") or {}
    if source.get("checkpoint_file_sha256")!=(replay.get("source") or {}).get("checkpoint_file_sha256") or source.get("detector_replay_content_sha256")!=replay.get("content_sha256") or source.get("suite_id")!=(replay.get("source") or {}).get("suite_id") or int(source.get("valid_episode_count") or 0)!=19: raise RuntimeError("projection input source binding")
    projector=ExactQwenMultimodalTokenProjector(Path(contract.MODEL_REALPATH),expected_revision=contract.MODEL_REVISION)
    manifest_rows=list(manifest.get("opportunities") or [])
    if len(manifest_rows)!=8 or int(manifest.get("opportunity_count") or 0)!=8: raise RuntimeError("projection input cardinality")
    expected=[]
    for episode in replay.get("episodes") or []:
        trigger_count=int(episode.get("trigger_count") or 0); triggers=list(episode.get("triggers") or [])
        if trigger_count!=len(triggers): raise RuntimeError("frozen detector replay trigger count drift")
        if trigger_count==0: continue
        if trigger_count!=1: raise RuntimeError("frozen detector replay trigger cap drift")
        trigger=triggers[0]
        expected.append({"task_name":str(episode.get("task_name") or ""),"episode_id":str(episode.get("episode_id") or ""),"eligible_request_step":int(trigger.get("eligible_request_step")),"receipt_id":str(trigger.get("receipt_id") or "")})
    if len(expected)!=8: raise RuntimeError("frozen detector replay must contain exact eight ordered triggers")
    opportunities=[]
    for ordinal,(row,frozen_trigger) in enumerate(zip(manifest_rows,expected,strict=True),start=1):
        if int(row.get("ordinal") or 0)!=ordinal: raise RuntimeError(f"projection ordinal drift: {ordinal}")
        for field in ("task_name","episode_id","eligible_request_step"):
            if row.get(field)!=frozen_trigger[field]: raise RuntimeError(f"projection replay binding drift: {ordinal}:{field}")
        episode_id=str(row["episode_id"]); screenshot=(TOKEN_INPUT_DIR/str(row["png_file"])).resolve()
        try: screenshot.relative_to(TOKEN_INPUT_DIR.resolve())
        except ValueError as exc: raise RuntimeError("projection PNG escapes package") from exc
        screenshot_sha=sha256(screenshot.read_bytes()).hexdigest()
        if screenshot_sha!=row.get("png_sha256"): raise RuntimeError(f"projection PNG drift: {episode_id}")
        mode_rows={}
        for mode,mode_input in (row.get("modes") or {}).items():
            if mode not in {"generic","full"}: raise RuntimeError(f"projection mode drift: {episode_id}")
            if mode_input.get("receipt_id")!=frozen_trigger["receipt_id"]: raise RuntimeError(f"projection receipt drift: {episode_id}:{mode}")
            system_prompt=str(mode_input["system_prompt"]); user_prompt=str(mode_input["user_prompt"])
            expected_system=recovery.COMMON_AUX_SYSTEM_TEMPLATE.format(role_instruction=recovery.GENERIC_ROLE if mode=="generic" else recovery.FULL_ROLE)
            if system_prompt!=expected_system or sha256((system_prompt+"\n\0\n"+user_prompt).encode()).hexdigest()!=mode_input.get("request_text_sha256"): raise RuntimeError(f"projection prompt drift: {episode_id}:{mode}")
            projection=projector(system_prompt,user_prompt,str(screenshot))
            projected=int(projection["exact_multimodal_input_tokens"])+recovery.MAX_AUX_TOKENS
            if projected>recovery.MAX_AUX_TOTAL_TOKENS: raise RuntimeError(f"projection budget exceeded: {episode_id}:{mode}")
            mode_rows[mode]={**projection,"request_text_sha256":mode_input["request_text_sha256"],"reserved_output_tokens":recovery.MAX_AUX_TOKENS,"projected_total_tokens":projected}
        if set(mode_rows)!={"generic","full"}: raise RuntimeError(f"projection mode closure: {episode_id}")
        opportunities.append({"task_name":row["task_name"],"episode_id":episode_id,"eligible_request_step":int(row["eligible_request_step"]),"receipt_ids":{mode:frozen_trigger["receipt_id"] for mode in ("generic","full")},"png_file":row["png_file"],"screenshot_sha256":screenshot_sha,"modes":mode_rows})
    if len(opportunities)!=8: raise RuntimeError("exact eight projection opportunities required")
    return {"schema":"sys_trrc_eight_opportunity_token_projection_v1","source_suite":str(source["suite_id"]),"opportunity_count":8,"processor_files_sha256":dict(projector.processor_files_sha256),"maximum_projected_total_tokens":max(row["projected_total_tokens"] for item in opportunities for row in item["modes"].values()),"opportunities":opportunities}

def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp"); tmp.write_text(json.dumps(value,sort_keys=True,indent=2)+"\n",encoding="utf-8"); tmp.replace(path)

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--mode",choices=contract.MODE_BINDINGS,required=True)
    p.add_argument("--implementation-commit"); p.add_argument("--validate-existing",action="store_true")
    p.add_argument("--output",type=Path); a=p.parse_args(); arm=contract.binding(a.mode)
    out=a.output or ROOT/f"evidence/sys_trrc/SYS_TRRC_{a.mode.upper()}_ZERO_GENERATION_PREFLIGHT.json"
    if a.validate_existing:
        print(json.dumps(contract.validate_preflight_report(out,expected_mode=a.mode),indent=2)); return 0
    if not a.implementation_commit: p.error("--implementation-commit required")
    errors=[]; checks={}; head=subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip()
    dirty=subprocess.check_output(["git","-C",str(ROOT),"status","--porcelain","--untracked-files=all"],text=True).splitlines()
    if head!=a.implementation_commit: errors.append("implementation_commit_not_head")
    if dirty: errors.append("worktree_dirty")
    files={}
    for name in SOURCE_FILES:
        path=ROOT/name
        try:
            frozen=subprocess.check_output(["git","-C",str(ROOT),"show",f"{a.implementation_commit}:{name}"])
            if sha256(path.read_bytes()).hexdigest()!=sha256(frozen).hexdigest(): errors.append(f"source_drift:{name}")
            files[name]=sha256(frozen).hexdigest()
        except Exception: errors.append(f"source_missing:{name}")
    replay=json.loads((ROOT/"evidence/sys_trrc/SYS_TRRC_R2_DETECTOR_REPLAY.json").read_text(encoding="utf-8"))
    replay_path=ROOT/"evidence/sys_trrc/SYS_TRRC_R2_DETECTOR_REPLAY.json"
    if (replay.get("status")!="PASS" or replay.get("generation_calls")!=0
        or replay.get("content_sha256")!="ed47170cdceb0ea4354ac04c3761a9ae1a5d5a03458c027aea871ce0c739c55b"
        or replay.get("content_sha256")!=contract.content_sha256(replay)
        or sha256(replay_path.read_bytes()).hexdigest()!="02a564601310c7c476b07553bd8ea6cd8f541abf573eeefd5996b92b1ce25777"):
        errors.append("detector_replay")
    if sha256(A1_WORKING_MEMORY_SYSTEM_PROMPT.encode()).hexdigest()!="653f727961a97d04176d3ddb9b1098355fe1fe8783473c2abc74967798f4a5b8": errors.append("r2_prompt_drift")
    exact_prompts = {
        "common": getattr(recovery, "COMMON_AUX_SYSTEM_TEMPLATE", None),
        "generic": getattr(recovery, "GENERIC_ROLE", None), "full": getattr(recovery, "FULL_ROLE", None),
        "wrapper": getattr(recovery, "ADVICE_TEMPLATE", None),
    }
    expected_prompts = {"common": EXPECTED_COMMON_PROMPT, "generic": EXPECTED_GENERIC_ROLE,
                        "full": EXPECTED_FULL_ROLE, "wrapper": EXPECTED_WRAPPER}
    if exact_prompts != expected_prompts: errors.append("protocol_section_6_exact_prompt_or_wrapper_drift")
    config=json.loads(arm["config_path"].read_text(encoding="utf-8")); recovery_cfg=config.get("recovery") or {}
    if config != contract.expected_config(a.mode): errors.append("config_semantic_closure")
    expected_task_order=("staged_L1_Expense_then_L3_Browser_control_complete_two" if a.mode in {"base","detector"} else "staged_L1_Expense_then_L2_R2_six_then_L3_Browser_then_L4_remaining_twelve")
    if config.get("task_order")!=expected_task_order: errors.append("staged_task_order_config")
    required_cfg={"max_aux_calls_per_episode":0 if a.mode in {"base","detector"} else 1,"max_aux_tokens":192,
                  "max_total_tokenizer_tokens":8192,"max_latency_seconds":60,
                  "transport_attempts_per_call":1,"retry":False,
                  "require_remaining_normal_decision_slot":True,"exact_protocol_prompts":True}
    if a.mode=="base" and recovery_cfg.get("enabled") is not False: errors.append("base_recovery_must_be_disabled")
    if any(recovery_cfg.get(k)!=v for k,v in required_cfg.items()): errors.append("recovery_config_boundary")
    core_text=(ROOT/"implementation/src/raven_m/official_qwen_mobile/sys_trrc_recovery.py").read_text(encoding="utf-8")
    controller_text=(ROOT/"implementation/src/raven_m/official_qwen_mobile/controller.py").read_text(encoding="utf-8")
    client_text=(ROOT/"implementation/src/raven_m/models/vllm_client.py").read_text(encoding="utf-8")
    runner_text=(ROOT/"implementation/scripts/run_official_qwen_mobile.py").read_text(encoding="utf-8")
    start_text=(ROOT/"implementation/scripts/start_sys_trrc_server.sh").read_text(encoding="utf-8")
    if "8192" not in core_text or "60" not in core_text: errors.append("core_token_or_latency_enforcement_missing")
    if "remaining_native_decision_slots" not in controller_text or "remaining_native_decision_slots" not in core_text: errors.append("remaining_native_slot_enforcement_missing")
    if "request_timeout_seconds=60.0" not in controller_text or "request_timeout_seconds: float | None" not in client_text:
        errors.append("aux_http_60_second_timeout_missing")
    if "export VLLM_USE_FLASHINFER_SAMPLER=0" not in start_text:
        errors.append("native_vllm_sampler_freeze_missing")
    if "retry_transient_errors=not" not in runner_text or "or dual_memory_arm" not in runner_text:
        errors.append("single_transport_no_retry_missing")
    try:
        token_projection=_projection_evidence(replay)
    except Exception as exc:
        token_projection={"error":f"{type(exc).__name__}:{exc}"}; errors.append("eight_opportunity_exact_token_projection")
    test_env=dict(os.environ); test_env["PYTHONPATH"]=os.pathsep.join([str(ROOT/"implementation/src"),test_env.get("PYTHONPATH","")])
    test_env["PYTHONDONTWRITEBYTECODE"]="1"
    tests=subprocess.run(
        [sys.executable,"-m","pytest",
         "implementation/tests/official_qwen_mobile/test_sys_trrc_recovery.py",
         "implementation/tests/official_qwen_mobile/test_sys_trrc_token_budget.py",
         "implementation/tests/official_qwen_mobile/test_recovery_policy_controller.py",
         "implementation/tests/official_qwen_mobile/test_sys_trrc_contract_runner.py",
         "implementation/tests/models/test_sys_trrc_aux_timeout.py",
         "-q","-p","no:cacheprovider"], cwd=ROOT, env=test_env, capture_output=True, text=True,
    )
    if tests.returncode: errors.append("focused_tests_failed")
    checks={"head":head,"dirty":dirty,"source_files":files,"detector_replay_content_sha256":replay.get("content_sha256"),"aux_max_tokens":contract.MAX_AUX_TOKENS,"exact_protocol_prompt_sha256s":{k:sha256(v.encode()).hexdigest() for k,v in expected_prompts.items()},"required_recovery_config":required_cfg,"eight_opportunity_token_projection":token_projection,"focused_tests":{"returncode":tests.returncode,"stdout_tail":tests.stdout[-1500:],"stderr_tail":tests.stderr[-800:]}}
    freeze_payload={"schema":"sys_trrc_source_freeze_v1","implementation_commit":a.implementation_commit,"files":files}
    freeze_sha=contract.content_sha256(freeze_payload)
    freeze_report={**freeze_payload,"content_sha256":freeze_sha}
    freeze_output=contract.source_freeze_path(a.mode)
    if not any(str(error).startswith(("implementation_commit", "worktree_dirty", "source_")) for error in errors):
        write(freeze_output,freeze_report)
    payload={"schema":contract.PREFLIGHT_SCHEMA,"status":"PASS" if not errors else "FAIL","errors":errors,
             "generation_calls":0,"live_generation_authorized":not errors,"protocol_id":contract.PROTOCOL_ID,
             "system_id":contract.SYSTEM_ID,"mode":a.mode,"arm_id":arm["arm_id"],"experiment_id":arm["experiment_id"],
             "implementation_commit":a.implementation_commit,"source_freeze_content_sha256":freeze_sha,
             "config_content_sha256":contract.canonical_sha256(json.loads(arm["config_path"].read_text(encoding="utf-8"))),
             "checks":checks,"created_at":datetime.now(timezone.utc).isoformat()}
    report={**payload,"content_sha256":contract.content_sha256(payload)}; write(out,report)
    print(json.dumps({"status":report["status"],"output":str(out),"errors":errors},indent=2)); return 0 if not errors else 1
if __name__=="__main__": raise SystemExit(main())
