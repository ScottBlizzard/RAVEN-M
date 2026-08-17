from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


DESIGN = (
    "design_reviews/pro_candidates/2026-08-15/"
    "GPT_PRO_OPEN_V2_LONG_HORIZON_COORDINATION_DESIGN_2026-08-15.md"
)
R2_RESULT = "evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.json"
R2_SUITE = "runs/a1r2_cvp/official_qwen_20260814T145307_50081981"
OUTPUT = "evidence/p2_long_horizon/P2_SCOPE_R2_ZERO_GENERATION_AUDIT.json"
FIXED_SEVEN = [
    "BrowserMultiply",
    "ExpenseDeleteMultiple2",
    "RetroSavePlaylist",
    "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
    "RecipeDeleteMultipleRecipesWithConstraint",
    "OsmAndMarker",
]


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def content_sha256(value: dict[str, Any]) -> str:
    return sha256_bytes(canonical_bytes({k: v for k, v in value.items() if k != "content_sha256"}))


def file_row(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    raw = path.read_bytes()
    return {"path": relative, "size_bytes": len(raw), "sha256": sha256_bytes(raw)}


def episode_row(root: Path, result_row: dict[str, Any]) -> dict[str, Any]:
    episode_id = str(result_row["episode_id"])
    relative = f"{R2_SUITE}/episodes/{episode_id}/episode.json"
    path = root / relative
    raw = path.read_bytes()
    observed_sha = sha256_bytes(raw)
    expected_sha = str(result_row["episode_json_sha256"])
    if observed_sha != expected_sha:
        raise RuntimeError(f"episode hash mismatch: {episode_id}")
    episode = json.loads(raw.decode("utf-8"))
    native_max = int(result_row["native_max_steps"])
    checkpoint_after_actions = int(math.ceil(native_max / 2.0))
    executed = int(episode["executed_action_count"])
    opportunity = executed >= checkpoint_after_actions
    eligible_request_step = checkpoint_after_actions if opportunity else None
    remaining_slots = native_max - checkpoint_after_actions if opportunity else None
    episode_dir = path.parent
    pngs = sorted(episode_dir.glob("step_*_before.png")) + sorted(
        episode_dir.glob("step_*_after.png")
    )
    png_rows = []
    for png in sorted(set(pngs)):
        payload = png.read_bytes()
        png_rows.append(
            {
                "path": png.relative_to(root).as_posix(),
                "size_bytes": len(payload),
                "sha256": sha256_bytes(payload),
            }
        )
    return {
        "task_name": result_row["task_name"],
        "episode_id": episode_id,
        "episode_json_sha256": observed_sha,
        "success": bool(result_row["success"]),
        "reward": float(result_row["reward"]),
        "native_max_steps": native_max,
        "executed_actions": executed,
        "model_calls": int(episode["model_call_count"]),
        "checkpoint_after_executed_actions": checkpoint_after_actions,
        "checkpoint_opportunity": opportunity,
        "eligible_request_step": eligible_request_step,
        "remaining_native_decision_slots_at_checkpoint": remaining_slots,
        "screenshot_file_count": len(png_rows),
        "screenshot_manifest_sha256": sha256_bytes(canonical_bytes(png_rows)),
    }


def build(root: Path) -> dict[str, Any]:
    design = file_row(root, DESIGN)
    result_file = file_row(root, R2_RESULT)
    result = json.loads((root / R2_RESULT).read_text(encoding="utf-8"))
    result_payload = result["a1r2_result"]
    rows = [episode_row(root, row) for row in result_payload["episodes"]]
    if len(rows) != 19 or len({row["task_name"] for row in rows}) != 19:
        raise RuntimeError("R2 result is not the exact 19-task suite")
    by_task = {row["task_name"]: row for row in rows}
    if set(FIXED_SEVEN) - set(by_task):
        raise RuntimeError("fixed seven missing from R2 result")

    successes = [row for row in rows if row["success"]]
    failures = [row for row in rows if not row["success"]]
    success_exposed = [row for row in successes if row["checkpoint_opportunity"]]
    failure_exposed = [row for row in failures if row["checkpoint_opportunity"]]
    enough_runway = [
        row
        for row in rows
        if row["checkpoint_opportunity"]
        and int(row["remaining_native_decision_slots_at_checkpoint"]) >= 8
    ]

    hard_gates = {
        "raw_trace_hash_binding": {
            "status": "PASS",
            "episode_count": len(rows),
            "screenshot_file_count": sum(row["screenshot_file_count"] for row in rows),
        },
        "dual_blind_semantic_annotation": {
            "status": "FAIL",
            "required_reviewers": 2,
            "available_reviewers": 0,
            "annotated_executed_steps": 0,
            "eligible_executed_steps": sum(row["executed_actions"] for row in rows),
            "coverage": 0.0,
            "required_coverage": 0.9,
            "required_cohens_kappa": 0.7,
            "reason": "No blinded human annotation artifact, reviewer identities, arbitration log, or annotation-manual version exists in the frozen repository evidence.",
        },
        "coordination_defect_prevalence": {
            "status": "NOT_EVALUABLE",
            "required_failed_tasks": 3,
            "reason": "The required requirement-loss/phase-loss/reentry labels are semantic human judgments and cannot be inferred from episode length or midpoint exposure without changing the Pro protocol.",
        },
        "family_dispersion": {
            "status": "NOT_EVALUABLE",
            "reason": "Depends on the missing semantic-positive set.",
        },
        "pre_or_near_midpoint_defect_with_runway": {
            "status": "NOT_EVALUABLE",
            "required_cases": 2,
            "observable_midpoint_opportunities_with_eight_slots": len(enough_runway),
            "reason": "Opportunity is observable, but a coordination defect before the checkpoint is not established without the frozen annotations.",
        },
        "success_composite_false_positive": {
            "status": "NOT_EVALUABLE",
            "required_maximum": 1,
            "successful_tasks_reaching_static_checkpoint": len(success_exposed),
            "successful_task_names": [row["task_name"] for row in success_exposed],
            "reason": "Reaching the fixed checkpoint is not itself a semantic composite defect; the missing annotations are required to determine false positives.",
        },
        "wrong_track_exclusion": {
            "status": "NOT_EVALUABLE",
            "reason": "Requires the same missing semantic labels to distinguish coordination from outcome/completion failure.",
        },
    }
    errors = [
        "dual_blind_semantic_annotation_missing",
        "coordination_defect_prevalence_not_evaluable",
        "family_dispersion_not_evaluable",
        "midpoint_defect_runway_not_evaluable",
        "success_false_positive_not_evaluable",
        "wrong_track_exclusion_not_evaluable",
    ]
    report: dict[str, Any] = {
        "schema": "p2_scope_r2_zero_generation_audit_v1",
        "status": "PREFLIGHT_INVALID_NO_LIVE",
        "generation_calls": 0,
        "live_authorized": False,
        "candidate": {
            "direction": "long_horizon_coordination",
            "pro_name": "SYS-SCOPE-R2",
            "design_status": "UNVALIDATED_PRO_BLUEPRINT",
            "parent": "A1-R2",
            "pro_frozen_state": "NO-GO-AUDIT",
        },
        "source": {
            "design": design,
            "r2_result": result_file,
            "r2_suite_id": result["suite_id"],
            "r2_result_content_sha256": result_payload["content_sha256"],
        },
        "observable_projection": {
            "checkpoint_rule": "after ceil(native_max_steps/2) executed actions, on the next normal decision",
            "all_tasks_reaching_checkpoint": sum(row["checkpoint_opportunity"] for row in rows),
            "failed_tasks_reaching_checkpoint": len(failure_exposed),
            "successful_tasks_reaching_checkpoint": len(success_exposed),
            "successful_task_names": [row["task_name"] for row in success_exposed],
            "failed_task_names": [row["task_name"] for row in failure_exposed],
            "fixed_seven": [by_task[name] for name in FIXED_SEVEN],
            "episodes": rows,
        },
        "hard_gates": hard_gates,
        "errors": errors,
        "adjudication": {
            "verdict": "PREFLIGHT_INVALID_NO_LIVE",
            "minimal_repair_attempted": "Materialize all task-independent observables (raw hashes, exact static checkpoint exposure, remaining slots, and success-risk projection) while preserving the Pro semantic gates.",
            "why_repair_is_insufficient": "Replacing two blinded semantic reviewers with deterministic length/RGB proxies would change the claimed construct from long-horizon coordination to a post-hoc observable heuristic and create a new, unsupported identity.",
            "seven_task_live_result": "NOT_RUN_G0_INVALID",
            "not_zero_of_seven": True,
            "next_action": "Seal this direction without GPU generation and proceed to P3 outcome/completion judgment.",
        },
    }
    report["content_sha256"] = content_sha256(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", default=OUTPUT)
    args = parser.parse_args()
    root = args.root.resolve()
    report = build(root)
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": report["status"], "content_sha256": report["content_sha256"], "output": output.as_posix()}))


if __name__ == "__main__":
    main()
