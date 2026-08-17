from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


DESIGN = (
    "design_reviews/pro_candidates/2026-08-15/"
    "GPT_PRO_OPEN_V2_OUTCOME_JUDGMENT_DESIGN_2026-08-15.md"
)
R2_RESULT = "evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.json"
R2_SUITE = "runs/a1r2_cvp/official_qwen_20260814T145307_50081981"
V4_RESULT = "evidence/sys_nag_v4/SYS_NAG_V4_COMPLETE_RESULT_2026-08-18.json"
OUTPUT = "evidence/p3_outcome_judgment/P3_SCER_R2_ZERO_GENERATION_AUDIT.json"
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
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def content_sha256(value: dict[str, Any]) -> str:
    return sha256_bytes(canonical_bytes({k: v for k, v in value.items() if k != "content_sha256"}))


def file_row(root: Path, relative: str) -> dict[str, Any]:
    raw = (root / relative).read_bytes()
    return {"path": relative, "size_bytes": len(raw), "sha256": sha256_bytes(raw)}


def pending_from_injection(step: dict[str, Any]) -> str | None:
    text = str((step.get("memory_read") or {}).get("exact_injected_text") or "")
    for line in text.splitlines():
        if line.startswith("PENDING:"):
            value = line.split(":", 1)[1].strip()
            return None if value.casefold() in {"", "none"} else value
    return None


def episode_projection(root: Path, result_row: dict[str, Any]) -> dict[str, Any]:
    episode_id = str(result_row["episode_id"])
    rel = f"{R2_SUITE}/episodes/{episode_id}/episode.json"
    path = root / rel
    raw = path.read_bytes()
    observed_sha = sha256_bytes(raw)
    if observed_sha != result_row["episode_json_sha256"]:
        raise RuntimeError(f"episode hash mismatch: {episode_id}")
    episode = json.loads(raw.decode("utf-8"))
    terminal_rows = []
    for step in episode["steps"]:
        terminal = (step.get("decision") or {}).get("terminal_status")
        if terminal not in {"success", "answer"}:
            continue
        pending = pending_from_injection(step)
        terminal_rows.append(
            {
                "step": int(step["step"]),
                "terminal_status": terminal,
                "open_pending": pending,
                "t2_terminal_with_open_claim": pending is not None,
                "request_sha256": (step.get("model_call") or {}).get("request_sha256"),
                "response_sha256": (step.get("model_call") or {}).get("response_sha256"),
                "screenshot_sha256": step.get("before_screenshot_sha256"),
            }
        )
    pngs = sorted(path.parent.glob("step_*_before.png")) + sorted(path.parent.glob("step_*_after.png"))
    png_manifest = []
    for png in sorted(set(pngs)):
        payload = png.read_bytes()
        png_manifest.append(
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
        "termination_reason": result_row["termination_reason"],
        "executed_actions": int(result_row["executed_actions"]),
        "model_calls": int(result_row["model_calls"]),
        "same_state_refresh_count": int(result_row["same_state_refresh_count"]),
        "t3_exact_recurrence_proxy_opportunity": int(result_row["same_state_refresh_count"]) > 0,
        "terminal_proposals": terminal_rows,
        "t2_opportunity_count": sum(row["t2_terminal_with_open_claim"] for row in terminal_rows),
        "screenshot_file_count": len(png_manifest),
        "screenshot_manifest_sha256": sha256_bytes(canonical_bytes(png_manifest)),
    }


def build(root: Path) -> dict[str, Any]:
    result_file = file_row(root, R2_RESULT)
    design_file = file_row(root, DESIGN)
    v4_file = file_row(root, V4_RESULT)
    result = json.loads((root / R2_RESULT).read_text(encoding="utf-8"))
    payload = result["a1r2_result"]
    rows = [episode_projection(root, row) for row in payload["episodes"]]
    if len(rows) != 19 or len({row["task_name"] for row in rows}) != 19:
        raise RuntimeError("R2 result does not bind the exact 19-task suite")
    by_task = {row["task_name"]: row for row in rows}
    if set(FIXED_SEVEN) - set(by_task):
        raise RuntimeError("fixed seven incomplete")
    successes = [row for row in rows if row["success"]]
    failures = [row for row in rows if not row["success"]]
    t2_success = [row for row in successes if row["t2_opportunity_count"]]
    t2_failure = [row for row in failures if row["t2_opportunity_count"]]
    t3_success = [row for row in successes if row["t3_exact_recurrence_proxy_opportunity"]]
    t3_failure = [row for row in failures if row["t3_exact_recurrence_proxy_opportunity"]]
    v4 = json.loads((root / V4_RESULT).read_text(encoding="utf-8"))
    if v4.get("content_sha256") != content_sha256(v4):
        raise RuntimeError("SYS-NAG V4 result content hash mismatch")

    gates = {
        "raw_r2_materialization": {
            "status": "PASS",
            "episode_count": 19,
            "screenshot_file_count": sum(row["screenshot_file_count"] for row in rows),
            "note": "This closes the Pro document's historical raw-suite availability gap.",
        },
        "visible_only_annotation_packet": {
            "status": "FAIL",
            "required_independent_reviewers": 2,
            "available_human_reviewers": 0,
            "locked_event_annotations": 0,
            "required_labels": [
                "directly_visible_established",
                "directly_visible_contradicted",
                "visibility_limited",
                "unsupported_continuation",
                "forgotten_open_obligation",
                "repeated_ineffective_commitment",
            ],
            "reason": "No blinded visible-only human annotation, disagreement log, adjudication, or reviewer identity is present in the repository.",
        },
        "cross_task_target_event_coverage": {
            "status": "NOT_EVALUABLE",
            "required_distinct_tasks": 2,
            "observable_t2_failed_tasks": [row["task_name"] for row in t2_failure],
            "observable_t3_proxy_failed_tasks": [row["task_name"] for row in t3_failure],
            "reason": "Scheduler opportunities are observable, but whether they cover independently labeled outcome-judgment errors depends on missing annotations.",
        },
        "six_success_counterexamples": {
            "status": "RISK_OBSERVED_BUT_NOT_ADJUDICATED",
            "t2_success_task_count": len(t2_success),
            "t2_success_tasks": [row["task_name"] for row in t2_success],
            "t3_proxy_success_task_count": len(t3_success),
            "t3_proxy_success_tasks": [row["task_name"] for row in t3_success],
            "reason": "The proposed scheduler would expose historical successes; correctness/false-reject risk cannot be certified without the frozen visible-only audit.",
        },
        "expense_first_gate_intervention_opportunity": {
            "status": "OBSERVABLE_T2_OPPORTUNITY",
            "t2_opportunity_count": by_task["ExpenseDeleteMultiple2"]["t2_opportunity_count"],
            "not_sufficient_for_live": True,
        },
        "specialist_judgment_quality": {
            "status": "NOT_EVALUABLE_PREGENERATION",
            "reason": "The Pro contract requires comparison to locked visible-only labels before specialist output may authorize live.",
        },
    }
    errors = [
        "visible_only_independent_annotation_missing",
        "cross_task_target_event_coverage_not_evaluable",
        "success_false_reject_risk_not_adjudicated",
        "specialist_judgment_quality_reference_missing",
    ]
    report: dict[str, Any] = {
        "schema": "p3_scer_r2_zero_generation_audit_v1",
        "status": "PREFLIGHT_INVALID_NO_LIVE",
        "generation_calls": 0,
        "live_authorized": False,
        "candidate": {
            "direction": "outcome_completion_judgment",
            "pro_name": "R2-SCER v1",
            "design_status": "UNVALIDATED_PRO_BLUEPRINT",
            "parent": "A1-R2",
            "pro_live_state": "LIVE_NO_GO",
        },
        "source": {
            "design": design_file,
            "r2_result": result_file,
            "r2_suite_id": result["suite_id"],
            "r2_result_content_sha256": payload["content_sha256"],
            "sys_nag_v4_result": v4_file,
            "sys_nag_v4_result_content_sha256": v4["content_sha256"],
        },
        "observable_scheduler_projection": {
            "t2_terminal_open_claim_success_tasks": [row["task_name"] for row in t2_success],
            "t2_terminal_open_claim_failure_tasks": [row["task_name"] for row in t2_failure],
            "t3_refresh_proxy_success_tasks": [row["task_name"] for row in t3_success],
            "t3_refresh_proxy_failure_tasks": [row["task_name"] for row in t3_failure],
            "fixed_seven": [by_task[name] for name in FIXED_SEVEN],
            "episodes": rows,
        },
        "existing_direction_evidence": {
            "sys_nag_v4_success_count": int(v4["performance"]["success_count"]),
            "sys_nag_v4_reward_sum": float(v4["performance"]["reward_sum"]),
            "sys_nag_v4_terminal_block_count": int(v4["interventions"]["terminal_block_count"]),
            "sys_nag_v4_route_block_count": int(v4["interventions"]["route_block_count"]),
            "sys_nag_v4_route_block_full_success_count": int(v4["interventions"]["route_block_full_success_count"]),
            "interpretation": "Existing deterministic completion/recovery guards preserve the R2 score but do not establish a new win; they do not validate SCER and must not be relabeled as its control.",
        },
        "hard_gates": gates,
        "errors": errors,
        "adjudication": {
            "verdict": "PREFLIGHT_INVALID_NO_LIVE",
            "minimal_repair_attempted": "Close the obsolete raw-suite gap and compute exact task-independent T2 and T3-proxy exposure, including all six success counterexamples and the fixed seven.",
            "why_repair_is_insufficient": "Removing the independent visible-only reference would let the same model-defined claim and same-model accountant establish their own correctness. Replacing it with reward, UI tree, future frames, or SYS-NAG labels would violate the design's evidence boundary.",
            "why_not_reduce_to_another_guard": "A deterministic pending-terminal/route guard is a different treatment family already explored by SYS-NAG V3/V4; silently substituting it would neither test SCER nor create an independent P3 identity.",
            "seven_task_live_result": "NOT_RUN_G0_INVALID",
            "not_zero_of_seven": True,
            "next_action": "Seal P3, update the final matrix/HANDOFF, and stop the four-direction pipeline with no unauthorized live generation.",
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
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "content_sha256": report["content_sha256"], "output": output.as_posix()}))


if __name__ == "__main__":
    main()
