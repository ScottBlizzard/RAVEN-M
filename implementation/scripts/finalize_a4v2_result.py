#!/usr/bin/env python3
"""CPU-only, hash-bound A4-v2 seven/19-task result and diagnostic finalizer."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SEVEN = [
    "BrowserMultiply", "ExpenseDeleteMultiple2", "RetroSavePlaylist",
    "SimpleCalendarAddOneEvent", "SportsTrackerTotalDurationForCategoryThisWeek",
    "RecipeDeleteMultipleRecipesWithConstraint", "OsmAndMarker",
]


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _usage(episode: dict[str, Any]) -> dict[str, int]:
    values = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for step in episode.get("steps") or []:
        usage = (step.get("model_call") or {}).get("usage") or {}
        for key in values:
            values[key] += int(usage.get(key) or 0)
    return values


def _canonical_action(step: dict[str, Any]) -> Any:
    decision = step.get("decision") or {}
    return decision.get("canonical_action") or decision.get("action") or decision.get("terminal_status")


def _first_divergence(live: dict[str, Any], reference_path: Path | None) -> dict[str, Any]:
    if reference_path is None or not reference_path.is_file():
        return {"status": "NOT_COMPARABLE", "reason": "frozen_A0_raw_episode_unavailable"}
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    live_steps, ref_steps = live.get("steps") or [], reference.get("steps") or []
    for index in range(max(len(live_steps), len(ref_steps))):
        if index >= len(live_steps) or index >= len(ref_steps):
            return {"status": "COMPARABLE", "step": index, "basis": "trajectory_length"}
        live_step, ref_step = live_steps[index], ref_steps[index]
        live_response = (live_step.get("model_call") or {}).get("response_sha256")
        ref_response = (ref_step.get("model_call") or {}).get("response_sha256")
        if live_response != ref_response or _canonical_action(live_step) != _canonical_action(ref_step):
            return {
                "status": "COMPARABLE", "step": index,
                "basis": "model_response_or_canonical_action",
                "live_response_sha256": live_response,
                "a0_response_sha256": ref_response,
            }
    return {"status": "NO_MEANINGFUL_DIVERGENCE", "compared_steps": len(live_steps)}


def _load_episodes(suite: Path | None) -> tuple[dict[str, tuple[dict[str, Any], Path]], dict[str, Any]]:
    if suite is None:
        return {}, {}
    signature = suite / "run_signature.json"
    aggregate = suite / "aggregate.json"
    if not signature.is_file() or not aggregate.is_file():
        raise RuntimeError(f"A4-v2 suite closure missing: {suite}")
    signature_payload = json.loads(signature.read_text(encoding="utf-8"))
    aggregate_payload = json.loads(aggregate.read_text(encoding="utf-8"))
    signature_content_sha = _digest(signature_payload)
    if (
        signature_payload.get("experiment_id") != "A4V2_FAITHFUL_OFFLINE_AWM_QWEN3VL32B_AW_HARD_S20260806_V1"
        or signature_payload.get("method") != "a4v2_faithful_offline_awm_memory_v1"
    ):
        raise RuntimeError(f"A4-v2 suite identity drift: {suite}")
    per_task = aggregate_payload.get("per_task") or []
    if not per_task:
        raise RuntimeError(f"A4-v2 aggregate has no valid task rows: {suite}")
    episodes: dict[str, tuple[dict[str, Any], Path]] = {}
    for aggregate_row in per_task:
        episode_id = str(aggregate_row.get("episode_id") or "")
        path = suite / "episodes" / episode_id / "episode.json"
        if not episode_id or not path.is_file():
            raise RuntimeError(f"A4-v2 aggregate episode artifact missing: {episode_id}")
        episode = json.loads(path.read_text(encoding="utf-8"))
        task = str(episode.get("task_name"))
        if task in episodes:
            raise RuntimeError(f"duplicate valid A4-v2 task episode: {task}")
        metadata = episode.get("run_metadata") or {}
        events_path = path.with_name("events.jsonl")
        if (
            metadata.get("run_signature_sha256") != signature_content_sha
            or metadata.get("live_server_receipt_sha256")
            != signature_payload.get("a4v2_launch_receipt_sha256")
            or aggregate_row.get("task_name") != task
            or aggregate_row.get("reward") != episode.get("evaluator_reward")
            or aggregate_row.get("success") is not episode.get("success")
            or not events_path.is_file()
        ):
            raise RuntimeError(f"A4-v2 episode/signature/aggregate closure failed: {task}")
        episodes[task] = (episode, path)
    checkpoint = suite / "checkpoint.json"
    if not checkpoint.is_file():
        raise RuntimeError(f"A4-v2 checkpoint missing: {suite}")
    checkpoint_payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    checkpoint_body = {key: value for key, value in checkpoint_payload.items() if key != "content_sha256"}
    if (
        checkpoint_payload.get("schema") != "a4v2.scored_checkpoint.v1"
        or checkpoint_payload.get("run_signature_sha256") != signature_content_sha
        or checkpoint_payload.get("content_sha256") != _digest(checkpoint_body)
        or len(checkpoint_payload.get("a4v2_valid_entries") or []) != len(episodes)
    ):
        raise RuntimeError(f"A4-v2 checkpoint closure failed: {suite}")
    entries = {str(row.get("episode_id")): row for row in checkpoint_payload["a4v2_valid_entries"]}
    summaries = {str(row.get("episode_id")): row for row in checkpoint_payload.get("valid_summaries") or []}
    if set(entries) != {episode["episode_id"] for episode, _ in episodes.values()} or set(entries) != set(summaries):
        raise RuntimeError(f"A4-v2 checkpoint episode set drift: {suite}")
    for episode, path in episodes.values():
        episode_id = str(episode["episode_id"])
        entry = entries[episode_id]
        if (
            entry.get("episode_json_sha256") != _sha(path)
            or entry.get("summary_sha256") != _digest(episode)
            or entry.get("summary_sha256") != _digest(summaries[episode_id])
            or entry.get("run_signature_sha256") != signature_content_sha
        ):
            raise RuntimeError(f"A4-v2 checkpoint entry drift: {episode_id}")
    return episodes, {
        "run_signature_file_sha256": _sha(signature),
        "run_signature_content_sha256": signature_content_sha,
        "aggregate_file_sha256": _sha(aggregate),
        "checkpoint_file_sha256": _sha(checkpoint),
        "checkpoint_content_sha256": checkpoint_payload["content_sha256"],
        "preflight_file_sha256": signature_payload.get("a4v2_preflight_sha256"),
        "receipt_file_sha256": signature_payload.get("a4v2_launch_receipt_sha256"),
        "workflow_bank_file_sha256": signature_payload.get("a4v2_workflow_bank_sha256"),
    }


def build(seven_suite: Path, remaining_suite: Path | None = None) -> dict[str, Any]:
    manifest = json.loads((ROOT / "implementation/configs/androidworld_hard_v2_instances.json").read_text(encoding="utf-8"))
    original = [str(row["task_class"]) for row in manifest["instances"] if int(row["task_seed"]) == 20260806]
    remaining = [name for name in original if name not in SEVEN]
    if len(original) != 19 or len(remaining) != 12:
        raise RuntimeError("frozen Hard manifest closure failed")
    live, seven_hashes = _load_episodes(seven_suite)
    extra, remaining_hashes = _load_episodes(remaining_suite)
    if set(live) != set(SEVEN):
        raise RuntimeError("seven-task suite is incomplete or drifted")
    if extra and set(extra) != set(remaining):
        raise RuntimeError("remaining12 suite is incomplete or drifted")
    if set(live).intersection(extra):
        raise RuntimeError("A4-v2 seven tasks were rerun in remaining12")

    reference = json.loads((ROOT / "evidence/a2/A0_A1_PAIRED_REFERENCE_20260810.json").read_text(encoding="utf-8"))
    reference_rows = {str(row["A0"]["task_name"]): row["A0"] for row in reference["tasks"]}
    reference_root = Path(str(reference["source_roots"]["A0"]))
    rows = []
    for task in SEVEN + remaining:
        record = live.get(task) or extra.get(task)
        a0 = reference_rows.get(task) or {}
        if record is None:
            rows.append({
                "task_name": task, "execution_status": "NOT_RUN_BY_7_OF_7_GATE",
                "a0_success": a0.get("success"), "attribution": "NOT_RUN_BY_PROTOCOL",
                "opportunity": None, "match": None, "read": None,
                "first_divergence": {"status": "NOT_APPLICABLE"},
                "L0_L6": {"earliest_break": "NOT_RUN_BY_PROTOCOL"},
            })
            continue
        episode, path = record
        calls = episode.get("steps") or []
        if episode.get("error") is not None or episode.get("lifecycle_errors"):
            raise RuntimeError(f"infrastructure-invalid episode cannot enter formal result: {task}")
        if any(int((((step.get("model_call") or {}).get("raven_meta") or {}).get("transport_attempts") or 0)) != 1 for step in calls):
            raise RuntimeError(f"non-single transport episode cannot enter formal result: {task}")
        memory = episode.get("memory_mechanism") or {}
        retrievals = memory.get("retrievals") or []
        read_count = int(memory.get("nonempty_read_count") or 0)
        matched_ids = sorted({item for event in retrievals for item in (event.get("retrieved_ids") or [])})
        success = episode.get("evaluator_reward") == 1.0 and episode.get("success") is True
        a0_success = bool(a0.get("success"))
        if read_count == 0:
            attribution = "SILENT_SUCCESS_UNATTRIBUTED" if success else "NO_MATCH_NO_OPPORTUNITY"
        elif success and not a0_success:
            attribution = "EXPOSED_PAIRED_GAIN_PENDING_CONTROL"
        elif success and a0_success:
            attribution = "EXPOSED_A0_TIE_UNATTRIBUTED"
        elif not success and a0_success:
            attribution = "EXPOSED_REGRESSION_POSSIBLE_HARM"
        else:
            attribution = "EXPOSED_FAILURE_NO_BENEFIT"
        ref_path = reference_root / str(a0.get("episode_json")) if a0.get("episode_json") else None
        rows.append({
            "task_name": task, "execution_status": "VALID_SUCCESS" if success else "VALID_SCIENTIFIC_FAILURE",
            "episode_id": episode["episode_id"], "episode_sha256": _sha(path),
            "events_sha256": _sha(path.with_name("events.jsonl")),
            "reward": episode.get("evaluator_reward"), "success": success,
            "a0_success": a0_success, "a0_reward": a0.get("reward"),
            "opportunity": bool(retrievals), "match": bool(matched_ids),
            "retrieved_workflow_ids": matched_ids, "read": read_count > 0,
            "nonempty_read_count": read_count,
            "first_divergence": _first_divergence(episode, ref_path),
            "calls": int(episode.get("model_call_count") or 0),
            "actions": int(episode.get("executed_action_count") or 0),
            "token_usage": _usage(episode),
            "elapsed_seconds": (
                datetime.fromisoformat(episode["finished_at"]) - datetime.fromisoformat(episode["started_at"])
            ).total_seconds(),
            "attribution": attribution,
            "L0_L6": {
                "L0_runtime": "PASS", "L1_visible_grounding": "AUDIT_IN_RAW_TRACE",
                "L2_protocol_transform": "PASS", "L3_memory_match": "READ" if read_count else "SILENT",
                "L4_first_divergence": "RECORDED", "L5_decision_action": "AUDIT_IN_RAW_TRACE",
                "L6_evaluator": "SUCCESS" if success else "FAILURE",
                "earliest_break": None if success else ("L3_NO_MATCH" if read_count == 0 else "L4_TO_L5_EXPOSURE_WITHOUT_GAIN"),
            },
        })
    seven_rows = rows[:7]
    seven_success = sum(int(row.get("success") is True) for row in seven_rows)
    if seven_success == 7 and not extra:
        raise RuntimeError("A4-v2 7/7 must release and complete the frozen remaining12 before finalization")
    complete_19 = bool(extra) and all(row.get("execution_status", "").startswith("VALID_") for row in rows)
    performance = {
        "seven_success_count": seven_success,
        "seven_reward_sum": sum(float(row.get("reward") or 0.0) for row in seven_rows),
        "remaining12_released": seven_success == 7,
        "complete_19": complete_19,
        "success_count": sum(int(row.get("success") is True) for row in rows) if complete_19 else None,
        "reward_sum": sum(float(row.get("reward") or 0.0) for row in rows) if complete_19 else None,
    }
    result = {
        "schema": "a4v2.formal_result.v1",
        "experiment_id": "A4V2_FAITHFUL_OFFLINE_AWM_QWEN3VL32B_AW_HARD_S20260806_V1",
        "mechanism_id": "a4v2_faithful_offline_awm_memory_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "COMPLETE_19" if complete_19 else "SEALED_SEVEN_DIAGNOSTIC_NO_RELEASE",
        "held_out": False,
        "claim_boundary": "post_observed_setting_specific_transfer_diagnostic; single-arm gain requires shuffled-content control; no universal AWM claim",
        "suite_hashes": {"seven": seven_hashes, "remaining12": remaining_hashes or None},
        "performance": performance,
        "ablation_required_tasks": [row["task_name"] for row in rows if row.get("attribution") == "EXPOSED_PAIRED_GAIN_PENDING_CONTROL"],
        "tasks": rows,
    }
    result["content_sha256"] = _digest(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seven-suite", type=Path, required=True)
    parser.add_argument("--remaining-suite", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/a4v2/A4V2_FORMAL_RESULT.json")
    args = parser.parse_args()
    result = build(args.seven_suite.resolve(), args.remaining_suite.resolve() if args.remaining_suite else None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "output": str(args.output), "content_sha256": result["content_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
