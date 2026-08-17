from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


OUTPUT = "evidence/candidate_pipeline/CANDIDATE_PIPELINE_RESULT_2026-08-18.json"
SOURCES = {
    "r2": "evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.json",
    "v4": "evidence/sys_nag_v4/SYS_NAG_V4_COMPLETE_RESULT_2026-08-18.json",
    "r15": "evidence/a1r15/A1R15_EOVR_TERMINAL_RESULT_2026-08-18.json",
    "r15_forensic": "evidence/r15_browser_forensics/R15_BROWSER_FORENSIC_2026-08-18.json",
    "p1": "evidence/p1_failure_recovery/P1_TCRA_R2_ZERO_GENERATION_AUDIT.json",
    "p2": "evidence/p2_long_horizon/P2_SCOPE_R2_ZERO_GENERATION_AUDIT.json",
    "p3": "evidence/p3_outcome_judgment/P3_SCER_R2_ZERO_GENERATION_AUDIT.json",
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def content_sha(value: dict[str, Any]) -> str:
    return digest(canonical_bytes({k: v for k, v in value.items() if k != "content_sha256"}))


def load_bound(root: Path, relative: str) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = (root / relative).read_bytes()
    obj = json.loads(raw.decode("utf-8"))
    return obj, {"path": relative, "size_bytes": len(raw), "sha256": digest(raw)}


def build(root: Path) -> dict[str, Any]:
    loaded = {name: load_bound(root, path) for name, path in SOURCES.items()}
    r2 = loaded["r2"][0]["a1r2_result"]
    v4 = loaded["v4"][0]
    r15 = loaded["r15"][0]
    r15f = loaded["r15_forensic"][0]
    p1 = loaded["p1"][0]
    p2 = loaded["p2"][0]
    p3 = loaded["p3"][0]
    for name, obj in (("r2", r2), ("v4", v4), ("r15_forensic", r15f), ("p1", p1), ("p2", p2), ("p3", p3)):
        if obj.get("content_sha256") != content_sha(obj):
            raise RuntimeError(f"content hash mismatch: {name}")

    report: dict[str, Any] = {
        "schema": "candidate_pipeline_result_v1",
        "status": "COMPLETE",
        "date": "2026-08-18",
        "generation_calls_in_forensic_and_p1_p2_p3_g0": 0,
        "fixed_seven": [
            "BrowserMultiply",
            "ExpenseDeleteMultiple2",
            "RetroSavePlaylist",
            "SimpleCalendarAddOneEvent",
            "SportsTrackerTotalDurationForCategoryThisWeek",
            "RecipeDeleteMultipleRecipesWithConstraint",
            "OsmAndMarker",
        ],
        "systems": [
            {
                "name": "A1-R2",
                "class": "formal_19_task_reference",
                "tasks_run": 19,
                "success_count": int(r2["performance"]["success_count"]),
                "reward_sum": float(r2["performance"]["reward_sum"]),
                "model_calls": int(r2["performance"]["model_calls"]),
                "executed_actions": int(r2["performance"]["executed_actions"]),
                "total_tokens": int(r2["performance"]["token_usage"]["total_tokens"]),
                "conclusion": "best_complete_pure_memory_parent",
            },
            {
                "name": "SYS-NAG V4",
                "class": "formal_19_task_composite_reference",
                "tasks_run": 19,
                "success_count": int(v4["performance"]["success_count"]),
                "reward_sum": float(v4["performance"]["reward_sum"]),
                "model_calls": int(v4["performance"]["model_calls"]),
                "executed_actions": int(v4["performance"]["executed_actions"]),
                "total_tokens": int(v4["performance"]["token_usage"]["total_tokens"]),
                "activation": {"route_blocks": int(v4["interventions"]["route_block_count"]), "route_block_successes": int(v4["interventions"]["route_block_full_success_count"])},
                "conclusion": "preserved_r2_score_no_new_success",
            },
            {
                "name": "A1-R15 target-first",
                "class": "formal_single_target_diagnostic",
                "tasks_run": 1,
                "success_count": 1,
                "reward_sum": 1.0,
                "classification": r15["classification"],
                "evr_render_read_count": 0,
                "conclusion": r15f["go_no_go"]["decision"],
            },
        ],
        "candidate_directions": [
            {"name": "R15-derived seventh-task candidate", "direction": "pure_memory_parser_extension", "g0": "NO_GO", "seven_task_result": "NOT_RUN_NO_REUSABLE_PRIMITIVE", "live_generation_calls": 0},
            {"name": "P1 TCRA-R2", "direction": "failure_recovery", "g0": p1["status"], "seven_task_result": "NOT_RUN_G0_INVALID", "live_generation_calls": 0},
            {"name": "P2 SYS-SCOPE-R2", "direction": "long_horizon_coordination", "g0": p2["status"], "seven_task_result": p2["adjudication"]["seven_task_live_result"], "live_generation_calls": 0},
            {"name": "P3 R2-SCER v1", "direction": "outcome_completion_judgment", "g0": p3["status"], "seven_task_result": p3["adjudication"]["seven_task_live_result"], "live_generation_calls": 0},
        ],
        "pipeline_closure": {
            "r15_forensic_complete": True,
            "pro_documents_fully_read_and_audited": 3,
            "scientifically_valid_new_live_candidates": 0,
            "seven_task_runs_required": 0,
            "nineteen_task_expansions_required": 0,
            "invalid_candidates_not_mislabeled_zero_of_seven": True,
            "gpu_generation_not_used_without_g0": True,
        },
        "most_credible_conclusion": "The current evidence supports R2's compact pending ledger as the best complete pure-memory parent, but does not support a new reusable R15 parser primitive or any of the three Pro treatments under their own pre-generation evidence gates. P1 has a success-path detector false positive; P2 and P3 require independent semantic labels that do not exist. No illegal live result was manufactured.",
        "reporting_boundary": {
            "held_out": False,
            "r15_plus_r2_stitched_score_forbidden": True,
            "guard_silent_success_component_credit": False,
            "prose_is_not_evidence": True,
        },
        "source_files": {name: row for name, (_, row) in loaded.items()},
    }
    report["content_sha256"] = content_sha(report)
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
