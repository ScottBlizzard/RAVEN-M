#!/usr/bin/env python3
"""Zero-generation replay for SYS-TRRC's frozen detector and exact R2 path."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
from typing import Any

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))

from raven_m.official_qwen_mobile.a1r2_compact_verified_pending import (  # noqa: E402
    CompactVerifiedPendingMemory,
)
from raven_m.official_qwen_mobile.protocol import build_user_prompt  # noqa: E402
from raven_m.official_qwen_mobile.sys_trrc_recovery import (  # noqa: E402
    OneShotTriggeredRecoveryPolicy,
)
from raven_m.official_qwen_mobile.working_memory import append_working_memory  # noqa: E402


DEFAULT_SUITE = ROOT / "runs/a1r2_cvp/official_qwen_20260814T145307_50081981"
DEFAULT_OUTPUT = ROOT / "evidence/sys_trrc/SYS_TRRC_R2_DETECTOR_REPLAY.json"
SUCCESS_TASKS = (
    "ExpenseDeleteMultiple2", "RetroSavePlaylist", "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
    "RecipeDeleteMultipleRecipesWithConstraint", "OsmAndMarker",
)
EXPECTED_TASK_ORDER = (
    "ExpenseDeleteMultiple2", "RetroSavePlaylist", "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
    "RecipeDeleteMultipleRecipesWithConstraint", "BrowserMultiply",
    "ExpenseAddMultipleFromGallery", "ExpenseAddMultipleFromMarkor",
    "MarkorCreateNoteAndSms", "MarkorMergeNotes", "MarkorTranscribeVideo",
    "OsmAndMarker", "OsmAndTrack", "RecipeAddMultipleRecipesFromImage",
    "RecipeAddMultipleRecipesFromMarkor", "RecipeAddMultipleRecipesFromMarkor2",
    "SaveCopyOfReceiptTaskEval", "SportsTrackerActivitiesOnDate",
    "SportsTrackerTotalDistanceForCategoryOverInterval",
)
EXPECTED_TRIGGER_MANIFEST = {
    "BrowserMultiply": (13, 14, "trrc_013_99fe3b903d12", "99fe3b903d12f2d076a727a70b0d9a569b9e955ce5a55d208752d909124a5254"),
    "ExpenseAddMultipleFromMarkor": (13, 14, "trrc_013_9c5b58571078", "9c5b585710780f6b3773e0775e426041604fa5b8ea861e472bac2c2c92813628"),
    "MarkorCreateNoteAndSms": (12, 13, "trrc_012_70e4e2057e63", "70e4e2057e6356c84848e27994ae7f1fdc6b207dd0501bb5c6ea3341eacad7e9"),
    "MarkorMergeNotes": (12, 13, "trrc_012_50ba4d761341", "50ba4d761341d59e76e710c87538f38abd5dd893fde08b63ba778a848a28d913"),
    "OsmAndTrack": (14, 15, "trrc_014_4a741530f182", "4a741530f18204f6aabadc787634df5b7eb328055800b52ee7bec73faa334257"),
    "RecipeAddMultipleRecipesFromImage": (5, 6, "trrc_005_34b40e47f3e0", "34b40e47f3e02edca8847f26358410a5944b7000be9cf09ff6ddb2acded30ca3"),
    "RecipeAddMultipleRecipesFromMarkor": (14, 15, "trrc_014_ed73d71a395d", "ed73d71a395d230273f8ca8dd33146ee4d92f17df5ae090039074a0c92c1c5dd"),
    "RecipeAddMultipleRecipesFromMarkor2": (19, 20, "trrc_019_d354af31072b", "d354af31072b4b52fab4dd17ded97ecd790d980c75f3badce28cb951ffec2006"),
}
EXPECTED_SILENT_FAILURES = {
    "ExpenseAddMultipleFromGallery", "MarkorTranscribeVideo",
    "SaveCopyOfReceiptTaskEval", "SportsTrackerActivitiesOnDate",
    "SportsTrackerTotalDistanceForCategoryOverInterval",
}


def _file_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _canonical_sha(value: Any) -> str:
    return sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",", ":")).encode("utf-8")).hexdigest()


def _pixels(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.uint8)


def _verified_screenshot(
    *, episode_dir: Path, relative_path: str, expected_sha256: str
) -> np.ndarray:
    path = (episode_dir / relative_path).resolve()
    try:
        path.relative_to(episode_dir.resolve())
    except ValueError as exc:
        raise RuntimeError(f"screenshot escapes episode directory: {relative_path}") from exc
    if not path.is_file():
        raise RuntimeError(f"missing replay screenshot: {relative_path}")
    observed = _file_sha(path)
    if observed != expected_sha256:
        raise RuntimeError(
            f"screenshot hash mismatch: {relative_path}: {observed} != {expected_sha256}"
        )
    return _pixels(path)


def _replay_episode(suite: Path, summary: dict[str, Any]) -> dict[str, Any]:
    episode_id = str(summary["episode_id"]); episode_dir=suite/"episodes"/episode_id
    memory=CompactVerifiedPendingMemory(); detector=OneShotTriggeredRecoveryPolicy(mode="detector"); history=[]
    triggers=[]; prompt_mismatch=[]; memory_mismatch=[]; history_mismatch=[]
    for index,step in enumerate(summary["steps"]):
        detector.prepare_aux({"request_step":index,"goal":summary["task_goal"],"recent_action_summaries":history[-4:],"r2_memory_audit":memory.audit_record()})
        rendered,read=memory.read(context={"goal":summary["task_goal"]})
        if rendered != str((step.get("memory_read") or {}).get("exact_injected_text") or ""): memory_mismatch.append(index)
        prompt=append_working_memory(build_user_prompt(summary["task_goal"],history),rendered)
        if prompt != step.get("user_prompt"): prompt_mismatch.append(index)
        if rendered: memory.commit_injection(str(read["ticket_id"]),sha256(prompt.encode()).hexdigest())
        if not step.get("executed"): continue
        decision=step["decision"]; action_summary=str(decision["action_summary"]); committed=memory.history_summary(action_summary)
        if committed != (step.get("history_commit") or {}).get("committed_history_summary"): history_mismatch.append(index)
        history.append(committed); call=step["model_call"]
        memory.write(source_step=index,action_summary=action_summary,source_call_id=str(call["call_id"]),source_response_sha256=str(call["response_sha256"]),source_screenshot_sha256=str(step["before_screenshot_sha256"]))
        after_record = step.get("after") or {}
        before_pixels = _verified_screenshot(
            episode_dir=episode_dir,
            relative_path=str(step["before_screenshot"]),
            expected_sha256=str(step["before_screenshot_sha256"]),
        )
        after_pixels = _verified_screenshot(
            episode_dir=episode_dir,
            relative_path=str(after_record["screenshot"]),
            expected_sha256=str(after_record["screenshot_sha256"]),
        )
        transition = dict(step["transition"])
        transition["remaining_native_decision_slots"] = max(
            0, int(summary["run_metadata"]["native_max_steps"]) - index - 1
        )
        event=detector.observe_transition(source_step=index,action_summary=action_summary,canonical_action=decision["canonical_action"],before_pixels=before_pixels,after_pixels=after_pixels,transition=transition,source_call_id=str(call["call_id"]),source_response_sha256=str(call["response_sha256"]),source_before_screenshot_sha256=str(step["before_screenshot_sha256"]),source_after_screenshot_sha256=str(after_record["screenshot_sha256"]))
        if event.get("trigger_created"): triggers.append({key:event[key] for key in ("receipt_id","eligible_request_step","evidence_sha256")}|{"source_step":index})
    detector.close_episode(str(summary["termination_reason"])); equivalent=not(prompt_mismatch or memory_mismatch or history_mismatch)
    return {"task_name":summary["task_name"],"episode_id":episode_id,"success":bool(summary["success"]),"reward":summary["evaluator_reward"],"trigger_count":len(triggers),"triggers":triggers,"prompt_mismatch_steps":prompt_mismatch,"memory_mismatch_steps":memory_mismatch,"history_mismatch_steps":history_mismatch,"base_detector_byte_equivalent":equivalent,"detector_audit_sha256":_canonical_sha(detector.audit_record())}


class _PromptCaptureProjector:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, system_prompt: str, user_prompt: str, screenshot_path: str) -> dict[str, Any]:
        path=Path(screenshot_path).resolve(); screenshot_sha=_file_sha(path)
        captured={"system_prompt":system_prompt,"user_prompt":user_prompt,"screenshot_path":str(path),"screenshot_sha256":screenshot_sha}
        self.calls.append(captured)
        return {"schema":"sys_trrc_prompt_capture_projection_v1","current_screenshot_sha256":screenshot_sha,"exact_multimodal_input_tokens":1}


def _collect_episode_projection_input(suite: Path, summary: dict[str, Any], mode: str) -> dict[str, Any] | None:
    episode_id=str(summary["episode_id"]); episode_dir=suite/"episodes"/episode_id
    memory=CompactVerifiedPendingMemory(); capture=_PromptCaptureProjector()
    policy=OneShotTriggeredRecoveryPolicy(mode=mode,token_projector=capture); history=[]
    for index,step in enumerate(summary["steps"]):
        screenshot=(episode_dir/str(step["before_screenshot"])).resolve()
        if _file_sha(screenshot)!=str(step["before_screenshot_sha256"]): raise RuntimeError(f"projection screenshot hash mismatch: {episode_id}:{index}")
        prepared=policy.prepare_aux({"request_step":index,"goal":summary["task_goal"],"recent_action_summaries":history[-4:],"r2_memory_audit":memory.audit_record(),"current_screenshot_path":str(screenshot),"current_screenshot_sha256":str(step["before_screenshot_sha256"])})
        if prepared is not None:
            if len(capture.calls)!=1: raise RuntimeError(f"projection capture cardinality: {episode_id}")
            return {"task_name":summary["task_name"],"episode_id":episode_id,"eligible_request_step":index,"receipt_id":prepared["receipt_id"],"request_text_sha256":prepared["request_text_sha256"],**capture.calls[0]}
        rendered,read=memory.read(context={"goal":summary["task_goal"]})
        if rendered!=str((step.get("memory_read") or {}).get("exact_injected_text") or ""): raise RuntimeError(f"projection R2 memory drift: {episode_id}:{index}")
        prompt=append_working_memory(build_user_prompt(summary["task_goal"],history),rendered)
        if prompt!=step.get("user_prompt"): raise RuntimeError(f"projection executor prompt drift: {episode_id}:{index}")
        if rendered: memory.commit_injection(str(read["ticket_id"]),sha256(prompt.encode()).hexdigest())
        if not step.get("executed"): continue
        decision=step["decision"]; action_summary=str(decision["action_summary"]); committed=memory.history_summary(action_summary)
        if committed!=(step.get("history_commit") or {}).get("committed_history_summary"): raise RuntimeError(f"projection history drift: {episode_id}:{index}")
        history.append(committed); call=step["model_call"]; memory.write(source_step=index,action_summary=action_summary,source_call_id=str(call["call_id"]),source_response_sha256=str(call["response_sha256"]),source_screenshot_sha256=str(step["before_screenshot_sha256"]))
        after_record=step.get("after") or {}; before_pixels=_verified_screenshot(episode_dir=episode_dir,relative_path=str(step["before_screenshot"]),expected_sha256=str(step["before_screenshot_sha256"])); after_pixels=_verified_screenshot(episode_dir=episode_dir,relative_path=str(after_record["screenshot"]),expected_sha256=str(after_record["screenshot_sha256"])); transition=dict(step["transition"]); transition["remaining_native_decision_slots"]=max(0,int(summary["run_metadata"]["native_max_steps"])-index-1)
        policy.observe_transition(source_step=index,action_summary=action_summary,canonical_action=decision["canonical_action"],before_pixels=before_pixels,after_pixels=after_pixels,transition=transition,source_call_id=str(call["call_id"]),source_response_sha256=str(call["response_sha256"]),source_before_screenshot_sha256=str(step["before_screenshot_sha256"]),source_after_screenshot_sha256=str(after_record["screenshot_sha256"]))
    policy.close_episode(str(summary["termination_reason"])); return None


def collect_projection_inputs(suite: Path, mode: str) -> list[dict[str, Any]]:
    if mode not in {"generic","full"}: raise ValueError("projection mode must be generic or full")
    suite=suite.resolve(); checkpoint_path=suite/"checkpoint.json"; checkpoint=json.loads(checkpoint_path.read_text(encoding="utf-8")); entries=list(checkpoint.get("a1r2_valid_entries") or []); summaries={str(x["episode_id"]):x for x in checkpoint.get("valid_summaries") or []}
    if len(entries)!=19 or len(summaries)!=19: raise RuntimeError("exact 19 A1-R2 episodes required")
    rows=[]
    for entry in entries:
        episode_id=str(entry["episode_id"]); episode_path=suite/"episodes"/episode_id/"episode.json"
        if _file_sha(episode_path)!=entry["episode_json_sha256"]: raise RuntimeError(f"projection episode hash mismatch: {episode_id}")
        summary=json.loads(episode_path.read_text(encoding="utf-8"))
        if summary!=summaries[episode_id]: raise RuntimeError(f"projection checkpoint mismatch: {episode_id}")
        row=_collect_episode_projection_input(suite,summary,mode)
        if row is not None: rows.append(row)
    if len(rows)!=8: raise RuntimeError("exact eight frozen projection opportunities required")
    return rows


def materialize_projection_inputs(suite: Path, output_dir: Path) -> dict[str, Any]:
    suite=suite.resolve(); output_dir=output_dir.resolve(); output_dir.mkdir(parents=True,exist_ok=True)
    if any(output_dir.iterdir()): raise RuntimeError(f"projection output directory must be empty: {output_dir}")
    generic=collect_projection_inputs(suite,"generic"); full=collect_projection_inputs(suite,"full")
    if [x["episode_id"] for x in generic]!=[x["episode_id"] for x in full]: raise RuntimeError("generic/full projection order mismatch")
    rows=[]
    for ordinal,(g,f) in enumerate(zip(generic,full,strict=True),start=1):
        if g["screenshot_sha256"]!=f["screenshot_sha256"] or g["eligible_request_step"]!=f["eligible_request_step"]: raise RuntimeError(f"generic/full projection source mismatch: {g['episode_id']}")
        source=Path(g["screenshot_path"]); filename=f"{ordinal:02d}_{g['task_name']}_step_{int(g['eligible_request_step']):03d}.png"; target=output_dir/filename; shutil.copy2(source,target)
        if _file_sha(target)!=g["screenshot_sha256"]: raise RuntimeError(f"materialized PNG hash mismatch: {filename}")
        rows.append({"ordinal":ordinal,"task_name":g["task_name"],"episode_id":g["episode_id"],"eligible_request_step":g["eligible_request_step"],"png_file":filename,"png_sha256":g["screenshot_sha256"],"modes":{"generic":{"receipt_id":g["receipt_id"],"system_prompt":g["system_prompt"],"user_prompt":g["user_prompt"],"request_text_sha256":g["request_text_sha256"]},"full":{"receipt_id":f["receipt_id"],"system_prompt":f["system_prompt"],"user_prompt":f["user_prompt"],"request_text_sha256":f["request_text_sha256"]}}})
    replay_report=replay(suite)
    payload={"schema":"sys_trrc_token_projection_inputs_v1","status":"PASS","generation_calls":0,"source":{"suite_id":suite.name,"checkpoint_file_sha256":_file_sha(suite/"checkpoint.json"),"detector_replay_content_sha256":replay_report["content_sha256"],"valid_episode_count":19},"opportunity_count":len(rows),"opportunities":rows,"errors":[]}
    manifest={**payload,"content_sha256":_canonical_sha(payload)}; manifest_path=output_dir/"manifest.json"; manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","output_dir":str(output_dir),"manifest":str(manifest_path),"opportunity_count":len(rows)},indent=2)); return manifest


def replay(suite: Path) -> dict[str, Any]:
    checkpoint_path=suite/"checkpoint.json"; checkpoint=json.loads(checkpoint_path.read_text(encoding="utf-8")); entries=list(checkpoint.get("a1r2_valid_entries") or []); summaries={str(x["episode_id"]):x for x in checkpoint.get("valid_summaries") or []}
    if len(entries)!=19 or len(summaries)!=19: raise RuntimeError("exact 19 A1-R2 episodes required")
    ordered_names = tuple(str(item.get("task_name")) for item in checkpoint.get("valid_summaries") or [])
    if ordered_names != EXPECTED_TASK_ORDER:
        raise RuntimeError("A1-R2 task order drift")
    episodes=[]
    for entry in entries:
        eid=str(entry["episode_id"]); path=suite/"episodes"/eid/"episode.json"
        if _file_sha(path)!=entry["episode_json_sha256"]: raise RuntimeError(f"episode hash mismatch: {eid}")
        episode=json.loads(path.read_text(encoding="utf-8"))
        if episode!=summaries[eid]: raise RuntimeError(f"checkpoint mismatch: {eid}")
        episodes.append(_replay_episode(suite,episode))
    actual_success_tasks = {x["task_name"] for x in episodes if x["success"]}
    if actual_success_tasks != set(SUCCESS_TASKS):
        raise RuntimeError("A1-R2 success set drift")
    positives=[x for x in episodes if x["trigger_count"]]; failed=[x for x in positives if not x["success"]]; success=[x for x in positives if x["success"]]
    remaining=[x["task_name"] for x in checkpoint["valid_summaries"] if x["task_name"] not in SUCCESS_TASKS]
    activation=next((name for name in remaining if any(x["task_name"]==name for x in failed)),None); errors=[]
    if any(not x["base_detector_byte_equivalent"] for x in episodes): errors.append("base_detector_not_byte_equivalent")
    actual_manifest = {}
    for episode in positives:
        if episode["trigger_count"] != 1 or len(episode["triggers"]) != 1:
            errors.append(f"trigger_cardinality_drift:{episode['task_name']}")
            continue
        trigger = episode["triggers"][0]
        actual_manifest[episode["task_name"]] = (
            int(trigger["source_step"]), int(trigger["eligible_request_step"]),
            str(trigger["receipt_id"]), str(trigger["evidence_sha256"]),
        )
    if actual_manifest != EXPECTED_TRIGGER_MANIFEST:
        errors.append("exact_trigger_manifest_drift")
    silent_failures = {x["task_name"] for x in episodes if not x["success"] and not x["trigger_count"]}
    if silent_failures != EXPECTED_SILENT_FAILURES:
        errors.append("exact_silent_failure_set_drift")
    if len(failed) != 8: errors.append("exact_failed_trigger_count_drift")
    if success: errors.append("success_task_exposure")
    if activation is None: errors.append("no_activation_task")
    report={"schema":"sys_trrc_r2_detector_replay_v1","status":"PASS" if not errors else "FAIL","generation_calls":0,"source":{"suite_id":suite.name,"checkpoint_file_sha256":_file_sha(checkpoint_path),"valid_episode_count":19},"detector":{"kind":"two_consecutive_same_family_no_rgb_progress","required_supports":2,"threshold":0.001,"one_shot":True},"summary":{"positive_episode_count":len(positives),"failed_positive_task_count":len({x["task_name"] for x in failed}),"success_positive_task_count":len({x["task_name"] for x in success}),"activation_task":activation,"all_base_detector_byte_equivalent":all(x["base_detector_byte_equivalent"] for x in episodes)},"success_preservation_risks":[x["task_name"] for x in success],"episodes":episodes,"errors":errors}
    report["content_sha256"]=_canonical_sha(report); return report


def main()->None:
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--suite",type=Path,default=DEFAULT_SUITE);parser.add_argument("--output",type=Path,default=DEFAULT_OUTPUT);parser.add_argument("--materialize-token-projection-inputs",type=Path);args=parser.parse_args()
    if args.materialize_token_projection_inputs is not None: materialize_projection_inputs(args.suite,args.materialize_token_projection_inputs); return
    report=replay(args.suite.resolve());args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8");print(json.dumps(report["summary"],ensure_ascii=False,indent=2));raise SystemExit(0 if report["status"]=="PASS" else 1)


if __name__=="__main__": main()
