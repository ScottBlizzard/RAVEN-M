"""Build the immutable A0/A1/A2 ledger used by all A3/A4/A5 preregistrations."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
A01 = ROOT / "evidence" / "a2" / "A0_A1_PAIRED_REFERENCE_20260810.json"
A2_SUITE = ROOT / "runs" / "a2_verified_progress_memory" / "official_qwen_20260810T194249_54a44c76"
OUTPUT = ROOT / "evidence" / "a345" / "A0_A1_A2_FROZEN_REFERENCE_LEDGER.json"
A2_RECEIPT = ROOT / "evidence" / "a2" / "A2_SERVER_LIVE_RECEIPT_NEW_SERVER.json"
GATE = {
    "ExpenseDeleteMultiple2",
    "RecipeDeleteMultipleRecipesWithConstraint",
    "RetroSavePlaylist",
    "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
}


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> None:
    a01 = json.loads(A01.read_text(encoding="utf-8"))
    aggregate_path = A2_SUITE / "aggregate.json"
    validation_path = A2_SUITE / "A2_PAIRED_VALIDATION.json"
    signature_path = A2_SUITE / "run_signature.json"
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    a2_by_task = {str(item["task_name"]): item for item in aggregate["per_task"]}
    rows = []
    for prior in a01["tasks"]:
        task_name = str(prior["task_name"])
        a2 = dict(a2_by_task[task_name])
        episode_path = A2_SUITE / "episodes" / str(a2["episode_id"]) / "episode.json"
        a2["episode_json"] = str(episode_path.relative_to(ROOT)).replace("\\", "/")
        a2["episode_json_sha256"] = digest(episode_path)
        rows.append(
            {
                "task_name": task_name,
                "seed": int(prior["seed"]),
                "capability_gate_member": task_name in GATE,
                "A0": prior["A0"],
                "A1": prior["A1"],
                "A2": a2,
            }
        )
    if len(rows) != 19 or len({row["task_name"] for row in rows}) != 19:
        raise RuntimeError("reference ledger must contain exactly 19 unique tasks")
    if sum(int(row["A0"]["success"]) for row in rows) != 4:
        raise RuntimeError("A0 success invariant drift")
    if sum(int(row["A1"]["success"]) for row in rows) != 5:
        raise RuntimeError("A1 success invariant drift")
    if sum(int(row["A2"]["success"]) for row in rows) != 0:
        raise RuntimeError("A2 success invariant drift")
    payload = {
        "schema": "a345_a0_a1_a2_frozen_reference_v1",
        "seed": 20260806,
        "gate_tasks": [row["task_name"] for row in rows if row["capability_gate_member"]],
        "summaries": {
            "A0": a01["summaries"]["A0"],
            "A1": a01["summaries"]["A1"],
            "A2": {
                "episode_count": aggregate["episode_count"],
                "success_count": aggregate["success_count"],
                "model_calls": aggregate["total_model_calls"],
                "executed_actions": aggregate["total_executed_actions"],
                "total_tokens": aggregate["token_usage"]["total_tokens"],
                "valid_elapsed_seconds": aggregate["exact_valid_elapsed_seconds"],
                "invalid_episode_count": aggregate["invalid_episode_count"],
                "memory_active_episode_count": aggregate["memory_active_episode_count"],
            },
        },
        "source_hashes": {
            "A0_A1_reference": digest(A01),
            "A2_aggregate": digest(aggregate_path),
            "A2_validation": digest(validation_path),
            "A2_run_signature": digest(signature_path),
            "A2_live_server_receipt": digest(A2_RECEIPT),
        },
        "A2_validation_status": validation["status"],
        "tasks": rows,
        "claim_limit": "seed 20260806 has been repeatedly observed; this is a paired diagnostic reference, not fresh held-out evidence",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
