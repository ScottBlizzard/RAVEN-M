"""Run exactly one frozen four-cell batch of protocol-v2 Gate F."""

from __future__ import annotations

import argparse
from datetime import datetime
from hashlib import sha256
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
LOCAL_RUNTIME = REPOSITORY_ROOT / "06_local_runtime"
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(LOCAL_RUNTIME / "scripts"))

import androidworld_compat  # noqa: E402,F401
from android_world import registry  # noqa: E402
from android_world.env import env_launcher  # noqa: E402
from audit_task_action_coverage import audit as capability_audit  # noqa: E402
from raven_m.controller.episode_controller import (  # noqa: E402
    EpisodeController,
    _json_safe,
)
from raven_m.controller.protocol_v2_guard import (  # noqa: E402
    ProtocolV2DecisionGuard,
)
from raven_m.history.policies import (  # noqa: E402
    make_history_policy,
    make_history_policy_v2,
)
from raven_m.models.transformers_client import TransformersClient  # noqa: E402
from run_frozen_hard_suite import (  # noqa: E402
    EXPECTED_BACKEND,
    EXPECTED_REVISION,
    classify_infrastructure,
    recover_androidworld_env,
    wait_for_model_service,
)
from run_method_dev_suite import audit_memory_episode  # noqa: E402
from seal_protocol_v1_breadth import verify_existing_seal  # noqa: E402
from run_protocol_v2_gate_e import (  # noqa: E402
    PROTOCOL_V2_2,
    VERSIONED_PROTOCOLS,
    classify_gate_e_infrastructure,
    episode_result,
    generate_task,
    instance_hash,
    max_calls,
    utc_now,
    write_json,
)
from protocol_v2_runtime import (  # noqa: E402
    initialize_androidworld_environment,
    load_startup_audit,
)


EXPECTED_SOURCE_COMMIT = "0ddf83cad60647409b16a0c60c16b528a9cb19e6"
EXPECTED_SOURCE_TAG = "protocol-v2-gate-e-pass"
DEFAULT_MANIFEST = (
    PROJECT_ROOT / "configs/experiments/v2_hard_micro_gate.json"
)
DIAGNOSTIC_PAUSE = (
    PROJECT_ROOT
    / "metadata/protocol_v2_gate_f_batch1_checkpoint.json"
)
HARD_MANIFEST = (
    PROJECT_ROOT / "configs/task_manifests/androidworld_hard_v1.json"
)


def _git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return completed.stdout.strip()


def wall_seconds(summary: dict[str, Any]) -> float:
    started = datetime.fromisoformat(summary["started_at"])
    finished = datetime.fromisoformat(summary["finished_at"])
    return max(0.0, (finished - started).total_seconds())


def event_reset_audit(episode_dir: Path) -> dict[str, Any]:
    events_path = episode_dir / "events.jsonl"
    events = [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    torn_down = sum(item.get("event") == "task_torn_down" for item in events)
    reset = sum(item.get("event") == "post_episode_reset" for item in events)
    return {
        "task_torn_down_event_count": torn_down,
        "post_episode_reset_event_count": reset,
        "passed": torn_down == 1 and reset == 1,
    }


def gate_f_result(
    *,
    item: dict[str, Any],
    summary: dict[str, Any],
    episode_dir: Path,
    attempts: int,
    memory_audit: dict[str, Any] | None,
) -> dict[str, Any]:
    result = episode_result(
        item=item,
        summary=summary,
        episode_dir=episode_dir,
        attempts=attempts,
        memory_audit=memory_audit,
    )
    guard = summary.get("protocol_v2_guard") or {}
    reset_audit = event_reset_audit(episode_dir)
    result.update(
        {
            "batch": item["batch"],
            "task_id": item["task_id"],
            "pair_id": f"{item['task_id']}_seed{item['seed']}",
            "max_steps": item["max_steps"],
            "wall_time_seconds": wall_seconds(summary),
            "loop_recovery_validation_block_count": int(
                guard.get("validation_block_count", 0)
            ),
            "loop_recovery_completion_count": int(
                guard.get("recovery_completion_count", 0)
            ),
            "loop_recovery_obligation_count": int(
                guard.get("recovery_obligation_count", 0)
            ),
            "reset_audit": reset_audit,
        }
    )
    return result


def ratio(numerator: list[float], denominator: list[float]) -> float | None:
    if not numerator or not denominator:
        return None
    denominator_mean = sum(denominator) / len(denominator)
    if denominator_mean <= 0:
        return None
    return (sum(numerator) / len(numerator)) / denominator_mean


def projected_active_seconds(
    manifest: dict[str, Any],
    results: list[dict[str, Any]],
    active_seconds: float,
) -> float:
    baseline = {
        item["task"]: float(item["v1_pair_minutes"]) * 30.0
        for item in manifest["task_families"]
    }
    completed_baseline = sum(baseline[item["task"]] for item in results)
    observed_wall = sum(float(item["wall_time_seconds"]) for item in results)
    scale = (
        observed_wall / completed_baseline
        if completed_baseline > 0
        else 1.0
    )
    completed_sequences = {item["sequence"] for item in results}
    remaining_baseline = sum(
        baseline[item["task"]]
        for item in manifest["schedule"]
        if item["sequence"] not in completed_sequences
    )
    return active_seconds + scale * remaining_baseline


def aggregate(
    *,
    manifest: dict[str, Any],
    health: dict[str, Any],
    results: list[dict[str, Any]],
    infrastructure_attempts: list[dict[str, Any]],
    gate_started_at: str,
    active_seconds: float,
    batch_runs: list[dict[str, Any]],
    current_batch: int,
    stopped_early: bool,
    stop_reason: str | None,
    startup_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pairing_errors = []
    for task in {item["task"] for item in manifest["schedule"]}:
        rows = [item for item in results if item["task"] == task]
        hashes = {
            (item["goal_sha256"], item["params_sha256"]) for item in rows
        }
        if len(rows) == 2 and len(hashes) != 1:
            pairing_errors.append(task)
    successes = sum(bool(item["success"]) for item in results)
    variant_successes = {
        variant: sum(
            bool(item["success"])
            for item in results
            if item["variant"] == variant
        )
        for variant in manifest["variants"]
    }
    solved_tasks = {
        item["task"] for item in results if bool(item["success"])
    }
    h17 = [item for item in results if item["task_id"] == "H17"]
    m0 = [item for item in results if item["variant"] == "M0"]
    b3 = [item for item in results if item["variant"] == "B3"]
    call_ratio = ratio(
        [float(item["model_call_count"]) for item in m0],
        [float(item["model_call_count"]) for item in b3],
    )
    wall_ratio = ratio(
        [float(item["wall_time_seconds"]) for item in m0],
        [float(item["wall_time_seconds"]) for item in b3],
    )
    delayed_fact_deadlocks = sum(
        item["variant"] == "M0"
        and item["failure_code"] == "MODEL_CALL_BUDGET_EXHAUSTED"
        and item["completion_adjudication_count"] > 0
        for item in results
    )
    provenance_errors = sum(
        len(item["memory_audit_errors"]) for item in results
    )
    context_errors = sum(
        item["max_prompt_tokens"]
        > manifest["limits"]["context_cap_tokens"]
        for item in results
    )
    reset_errors = sum(not item["reset_audit"]["passed"] for item in results)
    versioned_protocol = manifest["protocol"] in VERSIONED_PROTOCOLS
    protocol_v2_2 = manifest["protocol"] == PROTOCOL_V2_2
    semantic_audits = [
        item.get("semantic_progress_audit", {}) for item in results
    ]
    criteria = {
        "valid_scored_cells": len(results) == 12,
        "pairing": not pairing_errors,
        "task_action_compatibility": all(
            item["failure_code"]
            not in {
                "INFRA_OR_CONTROLLER",
                "MODEL_OUTPUT_INVALID_AFTER_REPAIR",
            }
            for item in results
        ),
        "h17_answer_channel": (
            len(h17) == 2
            and all(item["answer_action_count"] >= 1 for item in h17)
            and all(item["answer_cache_match_count"] >= 1 for item in h17)
        ),
        "minimum_solved_task_instances": len(solved_tasks) >= 3,
        "minimum_total_success": successes >= 3,
        "b3_success": variant_successes["B3"] >= 1,
        "m0_success": variant_successes["M0"] >= 1,
        "normal_m0_termination": any(
            item["termination_reason"] in {"model_done", "model_answer"}
            for item in m0
        ),
        "loop_guard": not any(
            (
                not item.get("semantic_progress_audit", {}).get(
                    "passed", False
                )
                if versioned_protocol
                else item["unhandled_third_identical_no_effect_action"]
            )
            for item in results
        ),
        "loop_recovery": all(
            (
                item.get("semantic_progress_audit", {}).get("passed", False)
                if versioned_protocol
                else (
                    item["loop_recovery_obligation_count"] == 0
                    and item["loop_recovery_completion_count"]
                    >= item["loop_recovery_validation_block_count"]
                )
            )
            for item in results
        ),
        "delayed_fact_completion": delayed_fact_deadlocks == 0,
        "provenance": provenance_errors == 0,
        "model_call_ratio": (
            call_ratio is not None
            and call_ratio
            <= manifest["acceptance"][
                "maximum_m0_b3_mean_model_call_ratio"
            ]
        ),
        "wall_time_ratio": (
            wall_ratio is not None
            and wall_ratio
            <= manifest["acceptance"][
                "maximum_m0_b3_mean_wall_time_ratio"
            ]
        ),
        "context_cap": context_errors == 0,
        "memory_isolation": not any(
            item["memory_audit_errors"] for item in results
        ),
        "reset_isolation": reset_errors == 0,
        "evaluator_leakage": not any(
            item["evaluator_prompt_leak_steps"] for item in results
        ),
        "valid_output": all(
            item["valid_after_one_repair"] for item in results
        ),
        "model_identity": (
            health.get("backend") == EXPECTED_BACKEND
            and health.get("revision") == EXPECTED_REVISION
        ),
    }
    if versioned_protocol:
        criteria.update(
            {
                "semantic_progress_audit": all(
                    audit.get("passed", False)
                    for audit in semantic_audits
                ),
                "visible_failure_enforcement": not any(
                    audit.get("executed_blocked_action_steps")
                    or audit.get("unresolved_guard_repair")
                    for audit in semantic_audits
                ),
                "startup_environment_accounting": bool(
                    startup_audit
                    and startup_audit.get("last_status")
                    in {"clean", "recovered"}
                ),
            }
        )
    if protocol_v2_2:
        criteria["readiness_accounting"] = all(
            item.get("readiness_observation_count", 0) >= 1
            for item in results
        )
        if manifest["acceptance"].get(
            "consequential_action_adjudication_accounting"
        ):
            criteria["consequential_action_adjudication_accounting"] = all(
                "action_adjudication_count" in item for item in results
            )
    batch_sequences = {
        item["sequence"]
        for item in manifest["schedule"]
        if item["batch"] == current_batch
    }
    completed_sequences = {item["sequence"] for item in results}
    batch_completed = batch_sequences.issubset(completed_sequences)
    finished = len(results) == len(manifest["schedule"]) and not stopped_early
    projected = projected_active_seconds(manifest, results, active_seconds)
    gate_passed = finished and all(criteria.values())
    result = {
        "schema_version": (
            "protocol_v2_2_gate_f_summary.v1"
            if protocol_v2_2
            else (
                "protocol_v2_1_gate_f_summary.v1"
                if versioned_protocol
                else "protocol_v2_gate_f_summary.v1"
            )
        ),
        "suite_id": manifest["suite_id"],
        "protocol": manifest["protocol"],
        "source_tag": manifest["source_tag"],
        "source_commit": manifest["source_commit"],
        "gate_started_at": gate_started_at,
        "updated_at": utc_now(),
        "cumulative_active_seconds": active_seconds,
        "projected_total_active_seconds": projected,
        "hard_wall_time_seconds": manifest["limits"][
            "hard_wall_time_seconds"
        ],
        "current_batch": current_batch,
        "batch_completed": batch_completed,
        "batch_runs": batch_runs,
        "finished": finished,
        "stopped_early": stopped_early,
        "stop_reason": stop_reason,
        "gate_passed": gate_passed,
        "development_smoke": bool(
            manifest.get("development_smoke", False)
        ),
        "formal_scoring": bool(manifest.get("formal_scoring", True)),
        "automatic_next_batch": False,
        "automatic_gate_g_transition": False,
        "model_health": health,
        "result_count": len(results),
        "success_count": successes,
        "variant_successes": variant_successes,
        "solved_task_instance_count": len(solved_tasks),
        "solved_tasks": sorted(solved_tasks),
        "pairing_errors": pairing_errors,
        "h17_result_count": len(h17),
        "m0_b3_mean_model_call_ratio": call_ratio,
        "m0_b3_mean_wall_time_ratio": wall_ratio,
        "delayed_fact_completion_deadlock_count": delayed_fact_deadlocks,
        "provenance_audit_error_count": provenance_errors,
        "context_cap_error_count": context_errors,
        "reset_error_count": reset_errors,
        "infrastructure_attempt_count": len(infrastructure_attempts),
        "infrastructure_attempts": infrastructure_attempts,
        "criteria": criteria,
        "results": results,
    }
    if versioned_protocol:
        result["startup_environment_audit"] = startup_audit
    return result


def validate_manifest(
    manifest: dict[str, Any],
    *,
    expected_source_tag: str = EXPECTED_SOURCE_TAG,
    expected_source_commit: str = EXPECTED_SOURCE_COMMIT,
    expected_prerequisite_commit: str | None = None,
) -> dict[str, Any]:
    if manifest["source_tag"] != expected_source_tag:
        raise RuntimeError("Gate-F source tag is not the Gate-E pass.")
    if manifest["source_commit"] != expected_source_commit:
        raise RuntimeError("Gate-F source commit is not the Gate-E pass.")
    if manifest["instance_seed"] != 20260730:
        raise RuntimeError("Gate-F instance seed drifted.")
    if manifest["blocked_order_seed"] != 2026073001:
        raise RuntimeError("Gate-F blocked-order seed drifted.")
    if len(manifest["schedule"]) != 12:
        raise RuntimeError("Gate F requires exactly twelve frozen cells.")
    if [item["sequence"] for item in manifest["schedule"]] != list(
        range(1, 13)
    ):
        raise RuntimeError("Gate-F sequence must be exactly 1 through 12.")
    if set(manifest["variants"]) != {"B3", "M0"}:
        raise RuntimeError("Gate F is restricted to B3 and M0.")
    batches = {item["batch"] for item in manifest["schedule"]}
    if batches != {1, 2, 3}:
        raise RuntimeError("Gate F requires exactly three batches.")
    for batch in batches:
        rows = [
            item for item in manifest["schedule"] if item["batch"] == batch
        ]
        if len(rows) != 4:
            raise RuntimeError("Every Gate-F batch must contain four cells.")
        if sum(item["variant"] == "B3" for item in rows) != 2:
            raise RuntimeError("Every Gate-F batch must contain two B3 cells.")
        if len({item["task"] for item in rows}) != 4:
            raise RuntimeError("Paired variants may not share a batch.")
    schedule = manifest["schedule"]
    if any(
        left["task"] == right["task"]
        for left, right in zip(schedule, schedule[1:])
    ):
        raise RuntimeError("Paired variants may not be adjacent.")
    expected = {
        "H01": ("BrowserMultiply", 22),
        "H03": ("ExpenseAddMultipleFromMarkor", 60),
        "H05": ("MarkorCreateNoteAndSms", 18),
        "H15": ("SaveCopyOfReceiptTaskEval", 16),
        "H16": ("SimpleCalendarAddOneEvent", 34),
        "H17": ("SportsTrackerActivitiesOnDate", 20),
    }
    hard = json.loads(HARD_MANIFEST.read_text(encoding="utf-8"))
    frozen_hard = {
        item["id"]: (item["class_name"], item["native_max_steps"])
        for item in hard["tasks"]
    }
    if any(frozen_hard.get(key) != value for key, value in expected.items()):
        raise RuntimeError("Gate-F task subset drifted from the Hard manifest.")
    for task_id, (task, max_steps) in expected.items():
        rows = [
            item for item in manifest["schedule"]
            if item["task_id"] == task_id
        ]
        if (
            len(rows) != 2
            or {item["variant"] for item in rows} != {"B3", "M0"}
            or any(item["task"] != task for item in rows)
            or any(item["max_steps"] != max_steps for item in rows)
        ):
            raise RuntimeError(f"Gate-F pair mismatch for {task_id}.")
    freeze_checks = []
    prerequisite_checks = []
    if manifest["protocol"] in VERSIONED_PROTOCOLS:
        if _git_output("rev-list", "-n", "1", manifest["source_tag"]) != (
            expected_source_commit
        ):
            raise RuntimeError("Gate-F source tag does not resolve to source.")
        ancestor = subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                expected_source_commit,
                "HEAD",
            ],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            timeout=30,
        )
        if ancestor.returncode != 0:
            raise RuntimeError("Gate-F source is not an ancestor of HEAD.")
        records = manifest.get("freeze_files", [])
        if not records:
            raise RuntimeError("Versioned Gate-F freeze file list is empty.")
        for record in records:
            path = REPOSITORY_ROOT / record["path"]
            actual = (
                sha256(path.read_bytes()).hexdigest()
                if path.is_file()
                else None
            )
            passed = actual == record["sha256"]
            freeze_checks.append(
                {
                    "path": record["path"],
                    "expected_sha256": record["sha256"],
                    "actual_sha256": actual,
                    "passed": passed,
                }
            )
        if not all(item["passed"] for item in freeze_checks):
            raise RuntimeError("Versioned Gate-F freeze file hash mismatch.")
        prerequisite = manifest.get("prerequisite_gate_e_report")
        if not prerequisite:
            raise RuntimeError("Versioned Gate-F prerequisite is missing.")
        path = REPOSITORY_ROOT / prerequisite["path"]
        actual = (
            sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        )
        report = (
            json.loads(path.read_text(encoding="utf-8"))
            if path.is_file()
            else {}
        )
        report_gate_passed = report.get("suite", {}).get("gate_passed")
        report_source_commit = report.get("suite", {}).get("source_commit")
        prerequisite_source_commit = (
            expected_prerequisite_commit or expected_source_commit
        )
        passed = (
            actual == prerequisite["sha256"]
            and report.get("decision", {}).get("gate_e") == "pass"
            and report_gate_passed is True
            and report_source_commit == prerequisite_source_commit
        )
        prerequisite_checks.append(
            {
                "path": prerequisite["path"],
                "expected_sha256": prerequisite["sha256"],
                "actual_sha256": actual,
                "decision": report.get("decision", {}).get("gate_e"),
                "gate_passed": report_gate_passed,
                "source_commit": report_source_commit,
                "passed": passed,
            }
        )
        if not passed:
            raise RuntimeError("Versioned Gate-F prerequisite mismatch.")
    return {
        "schedule_cell_count": len(manifest["schedule"]),
        "task_pair_count": len(expected),
        "batch_count": len(batches),
        "freeze_file_checks": freeze_checks,
        "prerequisite_checks": prerequisite_checks,
    }


def run_preflight(
    *,
    manifest: dict[str, Any],
    manifest_audit: dict[str, Any],
    url: str,
    adb_path: str,
    output: Path,
) -> int:
    suite_dir = (
        REPOSITORY_ROOT / manifest["output_root"] / manifest["suite_id"]
    )
    if suite_dir.exists():
        raise RuntimeError(
            "Fresh Gate-F suite directory already exists; refusing reuse."
        )
    adb = subprocess.run(
        [adb_path, "devices"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    emulator_connected = any(
        line.startswith("emulator-5554") and line.rstrip().endswith("device")
        for line in adb.stdout.splitlines()
    )
    if not emulator_connected:
        raise RuntimeError("Gate-F emulator is not connected.")
    health = TransformersClient(url).health()
    if (
        health.get("backend") != EXPECTED_BACKEND
        or health.get("revision") != EXPECTED_REVISION
    ):
        raise RuntimeError("Gate-F model identity mismatch.")
    task_registry = registry.TaskRegistry()
    registered = task_registry.get_registry(
        task_registry.ANDROID_WORLD_FAMILY
    )
    seed = int(manifest["instance_seed"])
    instance_records = []
    by_task: dict[str, tuple[str, str]] = {}
    for task_name in sorted({item["task"] for item in manifest["schedule"]}):
        if task_name not in registered:
            raise RuntimeError(f"Unknown Gate-F task: {task_name}")
        first = generate_task(registered, task_name, seed)
        second = generate_task(registered, task_name, seed)
        first_hash = instance_hash(first)
        if first_hash != instance_hash(second):
            raise RuntimeError("Gate-F instance generation is not stable.")
        by_task[task_name] = first_hash
        instance_records.append(
            {
                "task": task_name,
                "seed": seed,
                "goal_sha256": first_hash[0],
                "params_sha256": first_hash[1],
                "restart_stable": True,
            }
        )
    pair_hash_checks = []
    for task_id in sorted({item["task_id"] for item in manifest["schedule"]}):
        rows = [
            item for item in manifest["schedule"]
            if item["task_id"] == task_id
        ]
        hashes = {by_task[item["task"]] for item in rows}
        pair_hash_checks.append(
            {
                "task_id": task_id,
                "variants": sorted(item["variant"] for item in rows),
                "goal_params_pair_count": len(hashes),
                "passed": (
                    len(rows) == 2
                    and {item["variant"] for item in rows} == {"B3", "M0"}
                    and len(hashes) == 1
                ),
            }
        )
    if not all(item["passed"] for item in pair_hash_checks):
        raise RuntimeError("Gate-F paired instance preflight failed.")
    protocol_v1_seal = verify_existing_seal()
    if (
        not protocol_v1_seal["passed"]
        or protocol_v1_seal["file_count"] != 197
    ):
        raise RuntimeError("Protocol-v1 breadth seal verification failed.")
    result = {
        "schema_version": (
            "protocol_v2_2_gate_f_preflight.v1"
            if manifest["protocol"] == PROTOCOL_V2_2
            else "protocol_v2_gate_f_preflight.v1"
        ),
        "checked_at": utc_now(),
        "passed": True,
        "protocol": manifest["protocol"],
        "suite_id": manifest["suite_id"],
        "source_tag": manifest["source_tag"],
        "source_commit": manifest["source_commit"],
        "execution_commit": _git_output("rev-parse", "HEAD"),
        "manifest_audit": manifest_audit,
        "protocol_v1_seal": protocol_v1_seal,
        "instance_records": instance_records,
        "pair_hash_checks": pair_hash_checks,
        "model_health": health,
        "emulator_connected": emulator_connected,
        "fresh_suite_directory_absent": True,
        "batch_isolation": {
            "batch_size": 4,
            "automatic_next_batch": False,
            "automatic_gate_g_transition": False,
        },
        "model_calls": 0,
        "gpu_experiment_cells": 0,
        "automatic_batch_1_launch": False,
        "automatic_next_batch": False,
        "automatic_gate_g_transition": False,
    }
    write_json(output, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def main(
    *,
    default_manifest: Path = DEFAULT_MANIFEST,
    expected_source_tag: str = EXPECTED_SOURCE_TAG,
    expected_source_commit: str = EXPECTED_SOURCE_COMMIT,
    expected_prerequisite_commit: str | None = None,
    diagnostic_pause: Path | None = DIAGNOSTIC_PAUSE,
) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument("--batch", type=int, choices=(1, 2, 3))
    parser.add_argument(
        "--manifest",
        type=Path,
        default=default_manifest,
    )
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--preflight-output", type=Path, default=None)
    parser.add_argument(
        "--development-smoke-sequence",
        type=int,
        default=0,
        help=(
            "Run one frozen sequence in a separate non-scored development "
            "namespace; valid values are 1-12."
        ),
    )
    args = parser.parse_args()

    if diagnostic_pause is not None and diagnostic_pause.exists():
        pause = json.loads(diagnostic_pause.read_text(encoding="utf-8"))
        if (
            pause.get("status") == "diagnostic_pause"
            and not pause.get("batch_2_authorized", False)
        ):
            raise RuntimeError(
                "The frozen Gate-F v2 run is diagnostically paused. "
                "Continuation would mix known-invalid semantic-progress "
                "enforcement with revised cells."
            )
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    manifest_audit = validate_manifest(
        manifest,
        expected_source_tag=expected_source_tag,
        expected_source_commit=expected_source_commit,
        expected_prerequisite_commit=expected_prerequisite_commit,
    )
    coverage = capability_audit(REPOSITORY_ROOT)
    if not coverage["passed"]:
        raise RuntimeError("Protocol-v2 capability audit failed.")
    if args.preflight_only:
        if args.development_smoke_sequence:
            raise RuntimeError(
                "--preflight-only cannot be combined with a live "
                "development smoke."
            )
        output = args.preflight_output or (
            REPOSITORY_ROOT
            / (
                "reports/protocol_v2_2_gate_f_preflight.json"
                if manifest["protocol"] == PROTOCOL_V2_2
                else "reports/protocol_v2_gate_f_preflight.json"
            )
        )
        return run_preflight(
            manifest=manifest,
            manifest_audit=manifest_audit,
            url=args.url,
            adb_path=args.adb_path,
            output=output,
        )
    if args.development_smoke_sequence:
        if args.batch is not None:
            raise RuntimeError(
                "--batch cannot be combined with a development smoke."
            )
        if not 1 <= args.development_smoke_sequence <= 12:
            raise RuntimeError(
                "--development-smoke-sequence must be between 1 and 12."
            )
        selected_smoke = [
            item
            for item in manifest["schedule"]
            if item["sequence"] == args.development_smoke_sequence
        ]
        if len(selected_smoke) != 1:
            raise RuntimeError("Requested development sequence is absent.")
        manifest = json.loads(json.dumps(manifest))
        manifest["schedule"] = selected_smoke
        manifest["suite_id"] = (
            manifest["suite_id"]
            + "_development_smoke_sequence_"
            + str(args.development_smoke_sequence)
        )
        manifest["output_root"] = "runs/protocol_v2_2_development"
        manifest["development_smoke"] = True
        manifest["formal_scoring"] = False
        args.batch = int(selected_smoke[0]["batch"])
    if args.batch is None:
        raise RuntimeError("--batch is required unless --preflight-only is set.")

    suite_dir = (
        REPOSITORY_ROOT / manifest["output_root"] / manifest["suite_id"]
    )
    episode_root = suite_dir / "episodes"
    suite_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = suite_dir / "manifest.snapshot.json"
    if snapshot_path.exists():
        if json.loads(snapshot_path.read_text(encoding="utf-8")) != manifest:
            raise RuntimeError("Gate-F manifest snapshot mismatch.")
    else:
        write_json(snapshot_path, manifest)

    progress_path = suite_dir / "gate_progress.json"
    results: list[dict[str, Any]] = []
    infrastructure_attempts: list[dict[str, Any]] = []
    batch_runs: list[dict[str, Any]] = []
    prior_active_seconds = 0.0
    gate_started_at = utc_now()
    startup_audit_path = suite_dir / "startup_environment_audit.json"
    startup_audit: dict[str, Any] | None = None
    if progress_path.exists():
        prior = json.loads(progress_path.read_text(encoding="utf-8"))
        if prior.get("stopped_early"):
            raise RuntimeError(
                "Gate F is stopped diagnostically; continuation is forbidden."
            )
        results = list(prior.get("results", []))
        infrastructure_attempts = list(
            prior.get("infrastructure_attempts", [])
        )
        batch_runs = list(prior.get("batch_runs", []))
        prior_active_seconds = float(
            prior.get("cumulative_active_seconds", 0.0)
        )
        gate_started_at = prior.get("gate_started_at", gate_started_at)
    if startup_audit_path.is_file():
        startup_audit = load_startup_audit(startup_audit_path)

    completed_sequences = {item["sequence"] for item in results}
    required_prior = {
        item["sequence"]
        for item in manifest["schedule"]
        if item["batch"] < args.batch
    }
    if not required_prior.issubset(completed_sequences):
        raise RuntimeError("A prior Gate-F batch is incomplete.")
    selected = [
        item for item in manifest["schedule"] if item["batch"] == args.batch
    ]
    if all(item["sequence"] in completed_sequences for item in selected):
        raise RuntimeError("Requested Gate-F batch is already complete.")

    client = TransformersClient(args.url)
    health = wait_for_model_service(
        client,
        recovery_dir=suite_dir / "recoveries/model_preflight",
        max_wait_seconds=1800,
    )
    if (
        health.get("backend") != EXPECTED_BACKEND
        or health.get("revision") != EXPECTED_REVISION
    ):
        raise RuntimeError("Gate-F model identity mismatch.")

    prompts = {
        name: (PROJECT_ROOT / path).read_text(encoding="utf-8")
        for name, path in manifest["prompts"].items()
    }
    schemas = {
        name: PROJECT_ROOT / path for name, path in manifest["schemas"].items()
    }
    task_registry = registry.TaskRegistry()
    registered = task_registry.get_registry(
        task_registry.ANDROID_WORLD_FAMILY
    )
    seed = int(manifest["instance_seed"])
    selected_tasks = sorted({item["task"] for item in manifest["schedule"]})
    instances = {}
    for task_name in selected_tasks:
        task = generate_task(registered, task_name, seed)
        goal_hash, params_hash = instance_hash(task)
        instances[task_name] = {
            "task": task_name,
            "seed": seed,
            "goal": str(task.goal),
            "goal_sha256": goal_hash,
            "params": _json_safe(task.params),
            "params_sha256": params_hash,
        }
    instances_path = suite_dir / "instances.snapshot.json"
    serializable_instances = {"instances": instances}
    if instances_path.exists():
        prior_instances = json.loads(
            instances_path.read_text(encoding="utf-8")
        )
        if prior_instances != serializable_instances:
            raise RuntimeError("Gate-F task instance snapshot drifted.")
    else:
        write_json(instances_path, serializable_instances)

    batch_started_at = utc_now()
    batch_clock = time.monotonic()
    stopped_early = False
    stop_reason = None
    consecutive_infra_codes: list[str] = []
    if manifest["protocol"] in VERSIONED_PROTOCOLS:
        try:
            env, startup_audit = initialize_androidworld_environment(
                audit_path=startup_audit_path,
                load_fn=lambda: env_launcher.load_and_setup_env(
                    console_port=args.console_port,
                    emulator_setup=False,
                    freeze_datetime=True,
                    adb_path=args.adb_path,
                    grpc_port=args.grpc_port,
                ),
                recover_fn=lambda: recover_androidworld_env(
                    adb_path=args.adb_path,
                    console_port=args.console_port,
                    grpc_port=args.grpc_port,
                    recovery_dir=(
                        suite_dir / "recoveries/startup_environment"
                    ),
                ),
            )
        except Exception as exc:
            startup_audit = load_startup_audit(startup_audit_path)
            batch_elapsed = time.monotonic() - batch_clock
            final = aggregate(
                manifest=manifest,
                health=health,
                results=results,
                infrastructure_attempts=infrastructure_attempts,
                gate_started_at=gate_started_at,
                active_seconds=prior_active_seconds + batch_elapsed,
                batch_runs=batch_runs,
                current_batch=args.batch,
                stopped_early=True,
                stop_reason=(
                    "startup_environment_failed_twice:"
                    f"{type(exc).__name__}"
                ),
                startup_audit=startup_audit,
            )
            write_json(progress_path, final)
            write_json(suite_dir / "gate_summary.json", final)
            print(json.dumps(final, indent=2, ensure_ascii=False), flush=True)
            return 3
    else:
        env = env_launcher.load_and_setup_env(
            console_port=args.console_port,
            emulator_setup=False,
            freeze_datetime=True,
            adb_path=args.adb_path,
            grpc_port=args.grpc_port,
        )
    try:
        for frozen in selected:
            if frozen["sequence"] in completed_sequences:
                continue
            active_seconds = (
                prior_active_seconds + time.monotonic() - batch_clock
            )
            if active_seconds >= manifest["limits"]["hard_wall_time_seconds"]:
                stopped_early = True
                stop_reason = "hard_wall_time_exceeded_before_next_cell"
                break
            item = {**frozen, "seed": seed}
            expected = instances[item["task"]]
            episode_dir = episode_root / (
                f"{item['sequence']:02d}_{item['task_id']}_"
                f"{item['variant']}_{item['task']}_seed{seed}"
            )
            if episode_dir.exists():
                interrupted = episode_dir.with_name(
                    episode_dir.name
                    + "_interrupted_"
                    + datetime.now().strftime("%Y%m%dT%H%M%S")
                )
                shutil.move(str(episode_dir), str(interrupted))
            summary = None
            attempts_used = 0
            for attempt in range(
                1,
                manifest["limits"][
                    "max_infrastructure_attempts_per_cell"
                ]
                + 1,
            ):
                attempts_used = attempt
                task = generate_task(registered, item["task"], seed)
                if instance_hash(task) != (
                    expected["goal_sha256"],
                    expected["params_sha256"],
                ):
                    stopped_early = True
                    stop_reason = "pairing_hash_drift"
                    break
                if item["variant"] == "B3":
                    policy = make_history_policy(
                        "B3",
                        client=client,
                        summary_system_prompt=prompts["summary"],
                    )
                    executor_prompt = prompts["executor"]
                else:
                    policy = make_history_policy_v2(
                        "M0",
                        client=client,
                        summary_system_prompt="",
                        planner_system_prompt=prompts["planner"],
                        critic_system_prompt=prompts["critic"],
                    )
                    executor_prompt = prompts["executor_raven"]
                controller = EpisodeController(
                    client=client,
                    system_prompt=executor_prompt,
                    max_steps=item["max_steps"],
                    max_model_calls=max_calls(
                        item["variant"], item["max_steps"]
                    ),
                    history_policy=policy,
                    action_schema_path=schemas[item["variant"]],
                    decision_guard=ProtocolV2DecisionGuard(),
                    protocol_v2=True,
                    protocol_v2_2=(
                        manifest["protocol"] == PROTOCOL_V2_2
                    ),
                    visual_source_critic_prompt=prompts["critic"],
                )
                summary = controller.run(
                    env=env,
                    task=task,
                    episode_id=(
                        f"{manifest['suite_id']}_{item['sequence']:02d}_"
                        f"{item['task_id']}_{item['variant']}_a{attempt}"
                    ),
                    episode_dir=episode_dir,
                    seed=seed,
                    protocol=manifest["protocol"],
                    variant=item["variant"],
                )
                if not summary.get("error"):
                    consecutive_infra_codes.clear()
                    break
                infra_code = (
                    classify_gate_e_infrastructure(summary)
                    if manifest["protocol"] in VERSIONED_PROTOCOLS
                    else classify_infrastructure(summary)
                )
                if infra_code is None:
                    stopped_early = True
                    stop_reason = "semantic_or_unclassified_controller_error"
                    write_json(
                        suite_dir / "semantic_stop.json",
                        {"item": item, "summary": summary},
                    )
                    break
                archive_root = (
                    suite_dir / "invalid_infrastructure_attempts"
                )
                archive_root.mkdir(parents=True, exist_ok=True)
                archived = archive_root / (
                    episode_dir.name + f"_attempt_{attempt:02d}"
                )
                shutil.move(str(episode_dir), str(archived))
                infrastructure_attempts.append(
                    {
                        "item": item,
                        "attempt": attempt,
                        "code": infra_code,
                        "archive": archived.relative_to(
                            REPOSITORY_ROOT
                        ).as_posix(),
                        "error": summary["error"],
                    }
                )
                consecutive_infra_codes.append(infra_code)
                consecutive_infra_codes = consecutive_infra_codes[-2:]
                if (
                    len(consecutive_infra_codes) == 2
                    and len(set(consecutive_infra_codes)) == 1
                ):
                    stopped_early = True
                    stop_reason = (
                        "two_consecutive_same_infrastructure_failures:"
                        + infra_code
                    )
                    break
                if infra_code in {
                    "INFRA_EMULATOR_LOST",
                    "INFRA_EMULATOR_ANR",
                }:
                    env.close()
                    env = recover_androidworld_env(
                        adb_path=args.adb_path,
                        console_port=args.console_port,
                        grpc_port=args.grpc_port,
                        recovery_dir=(
                            suite_dir
                            / "recoveries"
                            / f"{item['sequence']:02d}_attempt_{attempt:02d}"
                        ),
                    )
                elif infra_code == "INFRA_MODEL_UNAVAILABLE":
                    wait_for_model_service(
                        client,
                        recovery_dir=(
                            suite_dir
                            / "recoveries"
                            / f"{item['sequence']:02d}_model_{attempt:02d}"
                        ),
                        max_wait_seconds=1800,
                    )
            if stopped_early:
                break
            if summary is None or summary.get("error"):
                stopped_early = True
                stop_reason = "valid_cell_not_obtained"
                break
            memory_audit = (
                audit_memory_episode(episode_dir, summary["episode_id"])
                if item["variant"] == "M0"
                else None
            )
            result = gate_f_result(
                item=item,
                summary=summary,
                episode_dir=episode_dir,
                attempts=attempts_used,
                memory_audit=memory_audit,
            )
            results.append(result)
            completed_sequences.add(item["sequence"])
            active_seconds = (
                prior_active_seconds + time.monotonic() - batch_clock
            )
            progress = aggregate(
                manifest=manifest,
                health=health,
                results=results,
                infrastructure_attempts=infrastructure_attempts,
                gate_started_at=gate_started_at,
                active_seconds=active_seconds,
                batch_runs=batch_runs,
                current_batch=args.batch,
                stopped_early=False,
                stop_reason=None,
                startup_audit=startup_audit,
            )
            write_json(progress_path, progress)
            print(
                json.dumps(
                    {
                        "completed": len(results),
                        "latest": result,
                        "successes": progress["success_count"],
                        "projected_total_active_seconds": progress[
                            "projected_total_active_seconds"
                        ],
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            if not result["valid_after_one_repair"]:
                stopped_early = True
                stop_reason = "model_output_invalid_after_one_bounded_repair"
            elif (
                manifest["protocol"] in VERSIONED_PROTOCOLS
                and not result.get("semantic_progress_audit", {}).get(
                    "passed", False
                )
            ):
                stopped_early = True
                stop_reason = "semantic_progress_audit_failed"
            elif (
                manifest["protocol"] not in VERSIONED_PROTOCOLS
                and result["unhandled_third_identical_no_effect_action"]
            ):
                stopped_early = True
                stop_reason = "unhandled_third_identical_no_effect_action"
            elif (
                result["answer_action_count"]
                > result["answer_cache_match_count"]
            ):
                stopped_early = True
                stop_reason = "answer_action_without_cache_match"
            elif result["memory_audit_errors"]:
                stopped_early = True
                stop_reason = "provenance_or_memory_audit_error"
            elif not result["reset_audit"]["passed"]:
                stopped_early = True
                stop_reason = "post_episode_reset_audit_error"
            elif (
                result["max_prompt_tokens"]
                > manifest["limits"]["context_cap_tokens"]
            ):
                stopped_early = True
                stop_reason = "context_cap_exceeded"
            elif (
                progress["projected_total_active_seconds"]
                > manifest["limits"]["hard_wall_time_seconds"]
            ):
                stopped_early = True
                stop_reason = "projected_active_time_exceeds_hard_cap"
            if stopped_early:
                break
    finally:
        env.close()

    batch_elapsed = time.monotonic() - batch_clock
    active_seconds = prior_active_seconds + batch_elapsed
    batch_sequences = {item["sequence"] for item in selected}
    batch_completed = batch_sequences.issubset(
        {item["sequence"] for item in results}
    )
    batch_runs = [
        *batch_runs,
        {
            "batch": args.batch,
            "started_at": batch_started_at,
            "finished_at": utc_now(),
            "active_seconds": batch_elapsed,
            "completed": batch_completed,
            "stopped_early": stopped_early,
            "stop_reason": stop_reason,
        },
    ]
    final = aggregate(
        manifest=manifest,
        health=health,
        results=results,
        infrastructure_attempts=infrastructure_attempts,
        gate_started_at=gate_started_at,
        active_seconds=active_seconds,
        batch_runs=batch_runs,
        current_batch=args.batch,
        stopped_early=stopped_early,
        stop_reason=stop_reason,
        startup_audit=startup_audit,
    )
    write_json(progress_path, final)
    write_json(suite_dir / "gate_summary.json", final)
    write_json(
        suite_dir / f"batch_{args.batch:02d}_checkpoint.json",
        final,
    )
    print(json.dumps(final, indent=2, ensure_ascii=False), flush=True)
    return 0 if batch_completed and not stopped_early else 3


if __name__ == "__main__":
    raise SystemExit(main())
