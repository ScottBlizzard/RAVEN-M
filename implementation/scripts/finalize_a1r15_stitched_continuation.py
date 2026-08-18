"""CPU-only finalizer for the sealed A1-R15 stitched continuation.

This is a post-hoc evidence projection.  It never calls a model, an emulator,
or the network, and it does not alter the raw suite.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "implementation/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from raven_m.official_qwen_mobile import a1r15_stitched_continuation_contract as contract  # noqa: E402


OUTPUT_JSON = ROOT / "evidence/a1r15_stitched_continuation/A1R15_STITCHED_CONTINUATION_FINAL_RESULT_2026-08-18.json"
OUTPUT_MD = ROOT / "evidence/a1r15_stitched_continuation/A1R15_STITCHED_CONTINUATION_FINAL_RESULT_2026-08-18.md"

FAILURE_DIAGNOSES = {
    "SimpleCalendarAddOneEvent": {
        "earliest_breakpoint": "L4@step0",
        "first_meaningful_divergence": "L1/L2@step1",
        "root_cause": "The first launcher swipe produced almost no visible transition; the live route opened an October 9 day view and used 17 next-day actions instead of the R2 month-view date selection, exhausting the 34-step budget immediately before save.",
        "terminal_failure": "MAX_STEPS_BEFORE_SAVE",
        "alternative_explanation": "Visible launcher/calendar state and transition timing differed from the frozen R2 success; this is not evidence that EVR content caused the loss.",
    },
    "RecipeDeleteMultipleRecipesWithConstraint": {
        "earliest_breakpoint": "L1/L2@step1",
        "first_meaningful_divergence": "L1/L2@step1; L4 no-progress was clear by step3",
        "root_cause": "R2 saw and opened Broccoli at step1; the live drawer began lower in the list and the model kept swiping in the same direction despite near-zero progress, then terminated failure without entering the app.",
        "terminal_failure": "APP_NOT_REACHED_REPETITIVE_ROUTE",
        "alternative_explanation": "Launcher viewport/state nondeterminism plus absent no-progress recovery explains the route; EVR was ineligible and silent.",
    },
    "OsmAndMarker": {
        "earliest_breakpoint": "L4@step2",
        "first_meaningful_divergence": "L2@step3",
        "root_cause": "The first OsmAnd launch tap barely changed the screen, causing a repeated tap and an extra onboarding path; later the model treated the map zoom-plus as add-marker and selected the place-card Add/favorite action rather than Marker, then treated the orange favorite pin as proof and terminated success while the evaluator returned zero.",
        "terminal_failure": "VISIBLE_EVIDENCE_INSUFFICIENT_FALSE_SUCCESS",
        "alternative_explanation": "Early app-start/state divergence and weak completion grounding, not EVR, best explain the failure.",
    },
}

R2_REFERENCE = {
    "ExpenseDeleteMultiple2": {"reward": 1.0, "model_calls": 18, "executed_actions": 17, "total_tokens": 70990},
    "RetroSavePlaylist": {"reward": 1.0, "model_calls": 25, "executed_actions": 24, "total_tokens": 100657},
    "SimpleCalendarAddOneEvent": {"reward": 1.0, "model_calls": 23, "executed_actions": 22, "total_tokens": 93576},
    "SportsTrackerTotalDurationForCategoryThisWeek": {"reward": 1.0, "model_calls": 6, "executed_actions": 6, "total_tokens": 23103},
    "RecipeDeleteMultipleRecipesWithConstraint": {"reward": 1.0, "model_calls": 18, "executed_actions": 17, "total_tokens": 70389},
    "OsmAndMarker": {"reward": 1.0, "model_calls": 12, "executed_actions": 11, "total_tokens": 47113},
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_sha(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _seconds(start: str, finish: str) -> float:
    return (datetime.fromisoformat(finish) - datetime.fromisoformat(start)).total_seconds()


def _require(condition: bool, label: str) -> None:
    if not condition:
        raise RuntimeError(label)


def _episode_row(suite: Path, entry: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    episode_dir = suite / "episodes" / str(entry["episode_id"])
    episode_path = episode_dir / "episode.json"
    events_path = episode_dir / "events.jsonl"
    _require(episode_path.is_file(), f"episode missing: {entry['episode_id']}")
    _require(events_path.is_file(), f"events missing: {entry['episode_id']}")
    _require(_file_sha(episode_path) == entry["episode_json_sha256"], f"episode hash: {entry['episode_id']}")
    episode = _load(episode_path)
    _require(contract.canonical_sha256(episode) == entry["summary_sha256"], f"summary hash: {entry['episode_id']}")
    _require(episode == summary, f"checkpoint summary drift: {entry['episode_id']}")
    _require(episode.get("error") is None and not episode.get("lifecycle_errors"), f"episode errors: {entry['episode_id']}")

    prompt_tokens = completion_tokens = total_tokens = 0
    transport_attempts = 0
    usage_missing = 0
    screenshot_count = 0
    for step in episode["steps"]:
        call = step.get("model_call") or {}
        usage = call.get("usage") or {}
        if not all(isinstance(usage.get(k), int) and usage[k] >= 0 for k in ("prompt_tokens", "completion_tokens", "total_tokens")):
            usage_missing += 1
        else:
            _require(usage["prompt_tokens"] + usage["completion_tokens"] == usage["total_tokens"], f"usage sum: {entry['episode_id']}")
            prompt_tokens += usage["prompt_tokens"]
            completion_tokens += usage["completion_tokens"]
            total_tokens += usage["total_tokens"]
        attempts = (call.get("raven_meta") or {}).get("transport_attempts")
        _require(attempts == 1, f"transport attempts: {entry['episode_id']} step {step.get('step')}")
        transport_attempts += attempts
        for state_name in ("before", "after"):
            state = step.get(state_name)
            if not state:
                continue
            screenshot_name = state.get("screenshot")
            screenshot_sha = state.get("screenshot_sha256")
            if screenshot_name and screenshot_sha:
                screenshot_path = episode_dir / screenshot_name
                _require(screenshot_path.is_file(), f"screenshot missing: {screenshot_path}")
                _require(_file_sha(screenshot_path) == screenshot_sha, f"screenshot hash: {screenshot_path}")
                screenshot_count += 1

    _require(usage_missing == 0, f"usage missing: {entry['episode_id']}")
    _require(len(episode["steps"]) == episode["model_call_count"], f"call count: {entry['episode_id']}")
    _require(sum(bool(step.get("executed")) for step in episode["steps"]) == episode["executed_action_count"], f"action count: {entry['episode_id']}")

    memory = episode["memory_mechanism"]
    grounding = memory["response_grounding"]
    register = memory["evidence_register"]
    grounding_counters = grounding["counters"]
    register_counters = register["counters"]
    rendered_reads = sum(bool(row.get("rendered")) for row in register.get("read_events", []))
    _require(rendered_reads == register_counters["render_count"], f"render count: {entry['episode_id']}")
    _require(grounding_counters["append_count"] == 0 and register_counters["activation_count"] == 0, f"unexpected EVR activation: {entry['episode_id']}")
    _require(rendered_reads == 0 and not grounding.get("retained_values"), f"unexpected EVR read: {entry['episode_id']}")

    success = bool(episode["success"])
    diagnosis = FAILURE_DIAGNOSES.get(episode["task_name"])
    if success:
        attribution = "SUCCESS_COMPONENT_SILENT_OR_UNUSED_UNATTRIBUTED"
        breakpoint = "NO_FAILURE_BREAKPOINT"
    else:
        attribution = "REGRESSION_COMPONENT_SILENT_ZERO_OPPORTUNITY"
        breakpoint = diagnosis["earliest_breakpoint"] if diagnosis else "UNRESOLVED"

    r2 = R2_REFERENCE[episode["task_name"]]

    return {
        "task_name": episode["task_name"],
        "episode_id": episode["episode_id"],
        "seed": episode["seed"],
        "reward": episode["evaluator_reward"],
        "success": success,
        "execution_status": "VALID_SUCCESS" if success else "VALID_SCIENTIFIC_FAILURE",
        "termination_reason": episode["termination_reason"],
        "model_claimed_status": episode.get("model_claimed_status"),
        "cost": {
            "model_calls": episode["model_call_count"],
            "executed_actions": episode["executed_action_count"],
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "elapsed_seconds": _seconds(episode["started_at"], episode["finished_at"]),
        },
        "transport": {
            "single_transport_per_call": transport_attempts == episode["model_call_count"],
            "transport_attempts": transport_attempts,
            "usage_missing_count": usage_missing,
        },
        "evr": {
            "goal_eligible": grounding["goal_eligible"],
            "opportunity_count": 0,
            "activation_count": register_counters["activation_count"],
            "response_append_count": grounding_counters["append_count"],
            "retained_values": grounding["retained_values"],
            "render_count": register_counters["render_count"],
            "rendered_read_count": rendered_reads,
            "successful_use_count": 0,
        },
        "base_r2_memory": {
            "nonempty_read_count": memory["counters"]["nonempty_read_count"],
            "write_attempt_count": memory["counters"]["write_attempt_count"],
            "write_success_count": memory["counters"]["write_success_count"],
        },
        "l0_l6": {
            "earliest_failure_breakpoint": breakpoint,
            "failure_chain": diagnosis,
            "evaluator_visible_to_model": False,
        },
        "attribution": attribution,
        "historical_r2_reference": {
            **r2,
            "comparison": "TIE" if success else "REGRESSION",
            "not_a_matched_contemporaneous_ablation": True,
        },
        "artifacts": {
            "episode_json_sha256": entry["episode_json_sha256"],
            "canonical_summary_sha256": entry["summary_sha256"],
            "events_jsonl_sha256": _file_sha(events_path),
            "verified_screenshot_artifact_count": screenshot_count,
        },
    }


def finalize(suite: Path, output_json: Path = OUTPUT_JSON, output_md: Path = OUTPUT_MD) -> dict[str, Any]:
    suite = suite.resolve()
    checkpoint_path = suite / "checkpoint.json"
    result_path = suite / "a1r15_stitched_continuation_result.json"
    signature_path = suite / "run_signature.json"
    checkpoint = _load(checkpoint_path)
    runner_result = _load(result_path)
    signature = _load(signature_path)

    _require(checkpoint["status"] == "complete_six_task_diagnostic_no_release", "checkpoint status")
    _require(runner_result["status"] == "SEALED_SIX_TASK_DIAGNOSTIC_NO_RELEASE", "runner result status")
    _require(checkpoint["content_sha256"] == contract.content_sha256(checkpoint), "checkpoint content hash")
    _require(runner_result["content_sha256"] == contract.content_sha256(runner_result), "runner result content hash")
    signature_content_sha256 = contract.canonical_sha256(signature)
    _require(checkpoint["run_signature_sha256"] == signature_content_sha256, "checkpoint signature binding")
    _require(runner_result["identity"]["run_signature_sha256"] == signature_content_sha256, "result signature binding")
    _require(runner_result["closure"]["checkpoint_content_sha256"] == checkpoint["content_sha256"], "result checkpoint binding")
    _require(not checkpoint["invalid_attempts"] and not runner_result["invalid_attempts"], "invalid attempts present")
    _require(checkpoint["stitched_seven_gate"]["status"] == "fail", "seven gate")

    preflight = contract.validate_preflight_report()
    receipt_path = ROOT / "evidence/a1r15_stitched_continuation/A1R15_STITCHED_CONTINUATION_LIVE_RECEIPT.json"
    receipt = contract.validate_launch_receipt(receipt_path)
    freeze = contract.validate_source_freeze()
    _require(_file_sha(receipt_path) in checkpoint["live_server_receipt_sha256s"], "receipt file binding")

    entries = checkpoint["a1r15_stitched_valid_entries"]
    summaries = checkpoint["valid_summaries"]
    _require(len(entries) == len(summaries) == 6, "six-task closure")
    _require(tuple(row["task_name"] for row in entries) == contract.CAPABILITY_GATE_TASKS, "six-task order")
    rows = [_episode_row(suite, entry, summary) for entry, summary in zip(entries, summaries, strict=True)]

    live_cost = {
        key: sum(row["cost"][key] for row in rows)
        for key in ("model_calls", "executed_actions", "prompt_tokens", "completion_tokens", "total_tokens", "elapsed_seconds")
    }
    _require(live_cost["model_calls"] == 144 and live_cost["executed_actions"] == 140, "aggregate calls/actions")
    _require(live_cost["total_tokens"] == 586178, "aggregate tokens")
    live_successes = sum(int(row["success"]) for row in rows)
    _require(live_successes == 3, "live success count")
    r2_cost = {
        "model_calls": sum(row["model_calls"] for row in R2_REFERENCE.values()),
        "executed_actions": sum(row["executed_actions"] for row in R2_REFERENCE.values()),
        "total_tokens": sum(row["total_tokens"] for row in R2_REFERENCE.values()),
    }

    imported = contract.parent_browser_binding()
    imported_row = {
        "task_name": imported["task_name"],
        "episode_id": imported["episode_id"],
        "seed": imported["seed"],
        "reward": imported["reward"],
        "success": imported["success"],
        "execution_status": "IMPORTED_PARENT_VALID_SUCCESS",
        "attribution": "TARGET_SUCCESS_WITHOUT_MATURE_EVR_READ_UNATTRIBUTED",
        "evr": {
            "activation_count": 1,
            "response_append_count": 2,
            "retained_values": [8, 2],
            "render_count": 0,
            "rendered_read_count": 0,
            "successful_use_count": 0,
        },
        "cost": {
            "model_calls": 21,
            "executed_actions": 20,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "elapsed_seconds": None,
            "availability": "NOT_AVAILABLE_FROM_FROZEN_PARENT_BUNDLE",
        },
        "artifacts": imported,
    }
    not_run = [
        {
            "task_name": name,
            "execution_status": "NOT_RUN_BY_7_OF_7_GATE",
            "reward": None,
            "success": None,
        }
        for name in contract.REMAINING_TASKS
    ]

    payload: dict[str, Any] = {
        "schema": "a1r15_stitched_continuation_final_evidence_v1",
        "status": "SEALED_SIX_TASK_DIAGNOSTIC_NO_RELEASE",
        "evidence_class": "TRANSPARENT_POST_TERMINAL_STITCHED_BEHAVIORAL_DIAGNOSTIC",
        "generation_calls_by_finalizer": 0,
        "network_calls_by_finalizer": 0,
        "identity": {
            "mechanism_id": contract.MECHANISM_ID,
            "experiment_id": contract.EXPERIMENT_ID,
            "implementation_commit": runner_result["identity"]["implementation_commit"],
            "evidence_commit_at_launch": "8aab5d87460b4f93c3089531f8506e93d7681f6a",
            "parent_mechanism_commit": contract.PARENT_MECHANISM_COMMIT,
            "suite_id": runner_result["identity"]["suite_id"],
            "task_seed": contract.TASK_SEED,
            "generation_seed": contract.GENERATION_SEED,
        },
        "verdicts": {
            "accuracy": "FAIL_STITCHED_SEVEN_GATE_4_OF_7",
            "mechanism": "EVR_NOT_EVALUATED_IN_LIVE_SIX_ZERO_OPPORTUNITY_AND_ZERO_USE",
            "cost": "LIVE_SIX_REPORTED_PARENT_BROWSER_TOKEN_AND_TIME_UNAVAILABLE",
        },
        "performance": {
            "live_continuation_successes": live_successes,
            "live_continuation_total": 6,
            "imported_parent_successes": 1,
            "stitched_observed_successes": 1 + live_successes,
            "stitched_observed_total": 7,
            "remaining_twelve_released": False,
            "not_run_by_gate_count": 12,
            "live_continuation_cost": live_cost,
            "historical_r2_six_reference": {
                "successes": 6,
                "total": 6,
                **r2_cost,
                "descriptive_outcome_comparison": {"wins": 0, "ties": 3, "regressions": 3},
                "live_minus_r2": {
                    "model_calls": live_cost["model_calls"] - r2_cost["model_calls"],
                    "executed_actions": live_cost["executed_actions"] - r2_cost["executed_actions"],
                    "total_tokens": live_cost["total_tokens"] - r2_cost["total_tokens"],
                },
                "not_a_matched_contemporaneous_ablation": True,
            },
            "stitched_total_tokens": None,
            "stitched_total_elapsed_seconds": None,
        },
        "target_performance_gate": "PASS_IMPORTED_BROWSER_REWARD_1",
        "historical_target_mechanism_gate": "FAIL_NO_MATURE_EVR_READ",
        "imported_parent_browser": imported_row,
        "live_continuation_tasks": rows,
        "remaining_tasks": not_run,
        "closure": {
            "checkpoint_file_sha256": _file_sha(checkpoint_path),
            "checkpoint_content_sha256": checkpoint["content_sha256"],
            "runner_result_file_sha256": _file_sha(result_path),
            "runner_result_content_sha256": runner_result["content_sha256"],
            "run_signature_file_sha256": _file_sha(signature_path),
            "run_signature_content_sha256": signature_content_sha256,
            "source_freeze_file_sha256": _file_sha(contract.SOURCE_FREEZE_PATH),
            "source_freeze_content_sha256": freeze["content_sha256"],
            "preflight_file_sha256": _file_sha(contract.PREFLIGHT_PATH),
            "preflight_content_sha256": preflight["content_sha256"],
            "receipt_file_sha256": _file_sha(receipt_path),
            "receipt_content_sha256": receipt["content_sha256"],
            "valid_live_episode_count": 6,
            "imported_parent_count": 1,
            "invalid_attempt_count": 0,
            "suite_lifecycle_error_count": 0,
            "single_transport_per_call": True,
            "usage_missing_count": 0,
        },
        "claim_boundary": {
            "not_held_out": True,
            "post_terminal_schedule_amendment": True,
            "not_original_a1r15_prospective_full_suite": True,
            "browser_not_rerun": True,
            "browser_success_not_attributed_to_evr": True,
            "live_successes_not_attributed_to_evr": True,
            "cross_process_same_seed_not_exact_counterfactual": True,
            "remaining_twelve_prohibited": True,
        },
    }
    payload["content_sha256"] = contract.content_sha256(payload)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    task_lines = []
    for row in rows:
        evr = row["evr"]
        task_lines.append(
            f"| {row['task_name']} | {row['reward']:.0f} | {row['cost']['model_calls']} | {row['cost']['executed_actions']} | {row['cost']['total_tokens']:,} | "
            f"{evr['activation_count']}/{evr['response_append_count']}/{evr['rendered_read_count']} | {row['attribution']} |"
        )
    markdown = f"""# A1-R15 stitched continuation final result

Status: **SEALED_SIX_TASK_DIAGNOSTIC_NO_RELEASE**  
Evidence class: `TRANSPARENT_POST_TERMINAL_STITCHED_BEHAVIORAL_DIAGNOSTIC`

The six newly executed tasks scored **3/6**. Together with the immutable, previously sealed BrowserMultiply success, the descriptive stitched panel is **4/7**. The 7/7 release gate failed, so the remaining twelve tasks were not run.

This does not revise the original A1-R15 terminal result. Browser was not rerun, the seven tasks are not held out, and neither Browser nor the three new successes is attributed to EVR.

| Task | Reward | Calls | Actions | Tokens | EVR activation/append/read | Classification |
|---|---:|---:|---:|---:|---:|---|
{chr(10).join(task_lines)}

## Mechanism result

All six live continuation tasks were outside the collection-arithmetic goal grammar. Across all six, EVR had zero opportunity, zero activation, zero append, zero retained values, zero render/read, and zero use. Expense, Retro, and Sports are therefore component-silent successes. Calendar, Recipe, and Osm are regressions relative to frozen R2 successes, but the losses cannot be assigned to EVR content because it never entered a prompt.

Against the historical R2 six-task panel, the descriptive comparison is 0 wins, 3 ties, and 3 regressions. The continuation used 42 more calls, 43 more actions, and 180,350 more tokens. This is not a matched contemporaneous ablation: visible starting state and route differed, and generation used temperature 0.7, so these deltas do not establish an EVR causal effect.

Failure chains:

- **Calendar:** first physical warning `L4@step0`, first meaningful route divergence `L1/L2@step1`; repeated day-by-day navigation exhausted the budget before save.
- **Recipe:** first meaningful divergence `L1/L2@step1`, no-progress visible by `L4@step3`; the model never opened Broccoli and terminated failure.
- **Osm:** launch transition failed at `L4@step2`, route diverged at `L2@step3`; the model selected Add/favorite rather than Marker and then claimed completion from the orange favorite pin, while evaluator reward was zero.

## Cost and closure

The six live episodes used **144 calls**, **140 executed actions**, and **586,178 tokens** (568,732 prompt + 17,446 completion), with **144/144 single-transport calls** and no invalid or lifecycle-invalid attempt. Their summed episode elapsed time was **{live_cost['elapsed_seconds']:.6f} seconds**. Imported Browser token/time totals are unavailable from the frozen parent bundle, so no stitched token/time total is reported.

Checkpoint content SHA-256: `{checkpoint['content_sha256']}`  
Runner result content SHA-256: `{runner_result['content_sha256']}`  
Final evidence content SHA-256: `{payload['content_sha256']}`
"""
    output_md.write_text(markdown, encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, default=OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=OUTPUT_MD)
    args = parser.parse_args()
    payload = finalize(args.suite_dir, args.output_json, args.output_md)
    print(json.dumps({"status": payload["status"], "content_sha256": payload["content_sha256"], "output_json": str(args.output_json), "output_md": str(args.output_md)}, indent=2))


if __name__ == "__main__":
    main()
