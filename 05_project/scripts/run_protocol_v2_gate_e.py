"""Run the frozen eight-cell, non-Hard protocol-v2 capability gate."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time
from typing import Any

import numpy as np


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
from protocol_v2_runtime import (  # noqa: E402
    initialize_androidworld_environment,
    load_startup_audit,
)
from run_frozen_hard_suite import (  # noqa: E402
    EXPECTED_BACKEND,
    EXPECTED_REVISION,
    all_calls,
    classify_infrastructure,
    digest_json,
    recover_androidworld_env,
    wait_for_model_service,
)
from run_method_dev_suite import audit_memory_episode  # noqa: E402


HARD_MANIFEST = (
    PROJECT_ROOT / "configs/task_manifests/androidworld_hard_v1.json"
)
DEFAULT_GATE_E_MANIFEST = (
    PROJECT_ROOT / "configs/experiments/v2_capability_gate.json"
)
DEFAULT_GATE_E_SOURCE_COMMIT = (
    "de5278b6fc78ca01d4b530ef1442e5060dccbf10"
)
PROTOCOL_V2_1 = "androidworld_protocol_v2_1_exploratory"
PROTOCOL_V2_2 = "androidworld_protocol_v2_2_exploratory"
VERSIONED_PROTOCOLS = {PROTOCOL_V2_1, PROTOCOL_V2_2}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def instance_hash(task: Any) -> tuple[str, str]:
    return (
        sha256(str(task.goal).encode("utf-8")).hexdigest(),
        digest_json(_json_safe(task.params)),
    )


def generate_task(registered: dict[str, Any], name: str, seed: int) -> Any:
    random.seed(seed)
    np.random.seed(seed)
    task_type = registered[name]
    return task_type(task_type.generate_random_params())


def max_calls(variant: str, max_steps: int) -> int:
    if variant == "B3":
        return 2 * max_steps + 2 * math.ceil(max_steps / 5)
    if variant == "M0":
        return 3 * max_steps + 4
    raise ValueError(f"Unsupported Gate-E variant: {variant}")


def repeated_no_effect_audit(summary: dict[str, Any]) -> dict[str, Any]:
    maximum = 0
    current = 0
    previous = None
    for step in summary["steps"]:
        if not step.get("executed") or not step.get("decision"):
            current = 0
            previous = None
            continue
        action = step["decision"].get("action")
        fingerprint = (
            step.get("before_screenshot_sha256"),
            json.dumps(
                action,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
        no_effect = not step.get("screenshot_changed", True)
        if no_effect and fingerprint == previous:
            current += 1
        elif no_effect:
            current = 1
        else:
            current = 0
        previous = fingerprint if no_effect else None
        maximum = max(maximum, current)
    return {
        "maximum_consecutive_identical_no_effect_actions": maximum,
        "unhandled_third_identical_no_effect_action": maximum >= 3,
    }


def semantic_progress_audit(summary: dict[str, Any]) -> dict[str, Any]:
    """Audit protocol-v2.1 semantic evidence without evaluator state."""
    missing_steps: list[int] = []
    fallback_observation_count = 0
    visible_failure_count = 0
    maximum_no_progress_repeats = 0
    blocked_fingerprints: set[tuple[str, str]] = set()
    executed_blocked_steps: list[int] = []
    for step in summary.get("steps", []):
        if not step.get("executed") or not step.get("decision"):
            continue
        before = step.get("before_semantic_ui")
        after = step.get("after_semantic_ui")
        guard = step.get("protocol_v2_guard")
        if not all(isinstance(value, dict) for value in (before, after, guard)):
            missing_steps.append(int(step["step"]))
            continue
        fallback_observation_count += sum(
            value.get("source") == "screenshot_fallback"
            for value in (before, after)
        )
        action = step["decision"].get("action")
        fingerprint = (
            str(before.get("sha256")),
            json.dumps(
                action,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )
        if fingerprint in blocked_fingerprints:
            executed_blocked_steps.append(int(step["step"]))
        visible_failure_count += len(
            guard.get("new_visible_failures", [])
        )
        maximum_no_progress_repeats = max(
            maximum_no_progress_repeats,
            int(guard.get("semantic_no_progress_repeat_count", 0)),
        )
        if guard.get("fingerprint_blocked"):
            blocked_fingerprints.add(fingerprint)
    guard_summary = summary.get("protocol_v2_guard") or {}
    unresolved_guard_repair = bool(
        guard_summary.get("validation_block_count", 0)
        and summary.get("failure_code")
        == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    )
    return {
        "schema_version": "protocol_v2_1_semantic_episode_audit.v1",
        "executed_step_count": sum(
            bool(step.get("executed"))
            for step in summary.get("steps", [])
        ),
        "missing_semantic_audit_steps": missing_steps,
        "screenshot_fallback_observation_count": (
            fallback_observation_count
        ),
        "visible_failure_count": visible_failure_count,
        "maximum_semantic_no_progress_repeat_count": (
            maximum_no_progress_repeats
        ),
        "validation_block_count": int(
            guard_summary.get("validation_block_count", 0)
        ),
        "executed_blocked_action_steps": executed_blocked_steps,
        "unresolved_guard_repair": unresolved_guard_repair,
        "passed": (
            not missing_steps
            and not executed_blocked_steps
            and not unresolved_guard_repair
        ),
    }


def episode_result(
    *,
    item: dict[str, Any],
    summary: dict[str, Any],
    episode_dir: Path,
    attempts: int,
    memory_audit: dict[str, Any] | None,
) -> dict[str, Any]:
    calls = all_calls(summary)
    user_prompt_leaks = [
        step["step"]
        for step in summary["steps"]
        if "evaluator" in step.get("user_prompt", "").lower()
    ]
    answer_steps = []
    for step in summary["steps"]:
        decision = step.get("decision") or {}
        action = decision.get("action")
        if isinstance(action, dict) and action.get("type") == "answer":
            answer_steps.append(step)
    completion_adjudications = [
        record
        for step in summary["steps"]
        for record in step.get("parse", {}).get(
            "completion_adjudications", []
        )
    ]
    action_adjudications = [
        record
        for step in summary["steps"]
        for record in step.get("parse", {}).get(
            "action_adjudications", []
        )
    ]
    valid_decisions = all(
        step.get("parse", {}).get("valid_after_one_repair", True)
        for step in summary["steps"]
        if "parse" in step
    )
    loop_audit = repeated_no_effect_audit(summary)
    result = {
        "sequence": item["sequence"],
        "task": item["task"],
        "variant": item["variant"],
        "seed": item["seed"],
        "episode_id": summary["episode_id"],
        "episode_path": episode_dir.relative_to(
            REPOSITORY_ROOT
        ).as_posix(),
        "goal_sha256": sha256(
            summary["task_goal"].encode("utf-8")
        ).hexdigest(),
        "params_sha256": digest_json(_json_safe(summary["task_params"])),
        "success": summary["success"],
        "evaluator_reward": summary["evaluator_reward"],
        "failure_code": summary["failure_code"],
        "termination_reason": summary["termination_reason"],
        "attempt_count": attempts,
        "model_call_count": summary["model_call_count"],
        "executor_model_call_count": summary["executor_model_call_count"],
        "history_model_call_count": summary["history_model_call_count"],
        "prompt_tokens": sum(
            int(call.get("usage", {}).get("prompt_tokens", 0))
            for call in calls
        ),
        "completion_tokens": sum(
            int(call.get("usage", {}).get("completion_tokens", 0))
            for call in calls
        ),
        "max_prompt_tokens": max(
            (
                int(call.get("usage", {}).get("prompt_tokens", 0))
                for call in calls
            ),
            default=0,
        ),
        "valid_after_one_repair": valid_decisions,
        "answer_action_count": len(answer_steps),
        "answer_cache_match_count": sum(
            bool(
                step.get("answer_audit", {}).get(
                    "interaction_cache_matches_answer"
                )
            )
            for step in answer_steps
        ),
        "completion_adjudication_count": len(completion_adjudications),
        "completion_rejection_count": sum(
            record.get("output", {}).get("verdict") != "proceed"
            for record in completion_adjudications
            if record.get("output") is not None
        ),
        "action_adjudication_count": len(action_adjudications),
        "action_rejection_count": sum(
            record.get("output", {}).get("verdict") != "proceed"
            for record in action_adjudications
            if record.get("output") is not None
        ),
        "evaluator_prompt_leak_steps": user_prompt_leaks,
        "memory_audit_errors": (
            list(memory_audit.get("errors", [])) if memory_audit else []
        ),
        **loop_audit,
    }
    if summary.get("protocol") in VERSIONED_PROTOCOLS:
        result["semantic_progress_audit"] = semantic_progress_audit(summary)
        result["readiness_observation_count"] = int(
            summary.get("readiness_observation_count", 0)
        )
        result["readiness_retry_count"] = int(
            summary.get("readiness_retry_count", 0)
        )
    return result


def aggregate(
    *,
    manifest: dict[str, Any],
    health: dict[str, Any],
    results: list[dict[str, Any]],
    infrastructure_attempts: list[dict[str, Any]],
    started_at: str,
    elapsed_seconds: float,
    stopped_early: bool,
    stop_reason: str | None,
    startup_audit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pairing_errors = []
    for task in {item["task"] for item in manifest["schedule"]}:
        rows = [item for item in results if item["task"] == task]
        if len(rows) == 2 and len(
            {(item["goal_sha256"], item["params_sha256"]) for item in rows}
        ) != 1:
            pairing_errors.append(task)
    valid_count = len(results)
    successes = sum(item["success"] for item in results)
    variant_successes = {
        variant: sum(
            item["success"]
            for item in results
            if item["variant"] == variant
        )
        for variant in manifest["variants"]
    }
    ir = [
        item
        for item in results
        if item["task"] == "SimpleCalendarEventsOnDate"
    ]
    versioned_protocol = manifest["protocol"] in VERSIONED_PROTOCOLS
    protocol_v2_2 = manifest["protocol"] == PROTOCOL_V2_2
    semantic_audits = [
        item.get("semantic_progress_audit", {})
        for item in results
    ]
    criteria = {
        "valid_scored_cells": valid_count == 8,
        "pairing": not pairing_errors,
        "task_action_compatibility": all(
            not item["failure_code"]
            or item["failure_code"]
            not in {"INFRA_OR_CONTROLLER", "MODEL_OUTPUT_INVALID_AFTER_REPAIR"}
            for item in results
        ),
        "ir_cache_populated": (
            len(ir) == 2
            and all(item["answer_cache_match_count"] >= 1 for item in ir)
        ),
        "ir_correct": sum(item["success"] for item in ir) >= 1,
        "minimum_total_success": successes >= 4,
        "b3_success": variant_successes["B3"] >= 1,
        "m0_success": variant_successes["M0"] >= 1,
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
        "m0_completion": not any(
            item["variant"] == "M0"
            and item["failure_code"] == "MODEL_CALL_BUDGET_EXHAUSTED"
            and item["completion_adjudication_count"] > 0
            for item in results
        ),
        "valid_output": all(
            item["valid_after_one_repair"] for item in results
        ),
        "evaluator_leakage": not any(
            item["evaluator_prompt_leak_steps"] for item in results
        ),
        "memory_isolation": not any(
            item["memory_audit_errors"] for item in results
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
    finished = valid_count == len(manifest["schedule"]) and not stopped_early
    gate_passed = finished and all(criteria.values())
    result = {
        "schema_version": (
            "protocol_v2_2_gate_e_summary.v1"
            if protocol_v2_2
            else (
                "protocol_v2_1_gate_e_summary.v1"
                if versioned_protocol
                else "protocol_v2_gate_e_summary.v1"
            )
        ),
        "suite_id": manifest["suite_id"],
        "protocol": manifest["protocol"],
        "source_tag": manifest["source_tag"],
        "source_commit": manifest["source_commit"],
        "started_at": started_at,
        "updated_at": utc_now(),
        "elapsed_seconds": elapsed_seconds,
        "finished": finished,
        "stopped_early": stopped_early,
        "stop_reason": stop_reason,
        "gate_passed": gate_passed,
        "automatic_gate_f_transition": False,
        "model_health": health,
        "result_count": valid_count,
        "success_count": successes,
        "variant_successes": variant_successes,
        "pairing_errors": pairing_errors,
        "infrastructure_attempt_count": len(infrastructure_attempts),
        "infrastructure_attempts": infrastructure_attempts,
        "criteria": criteria,
        "results": results,
    }
    if versioned_protocol:
        result["startup_environment_audit"] = startup_audit
    return result


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


def validate_gate_e_manifest(
    manifest: dict[str, Any],
    *,
    expected_source_commit: str,
) -> dict[str, Any]:
    if manifest["source_commit"] != expected_source_commit:
        raise RuntimeError("Gate-E source commit is not frozen.")
    if len(manifest["schedule"]) != 8:
        raise RuntimeError("Gate E requires exactly eight frozen cells.")
    if {item["variant"] for item in manifest["schedule"]} != {"B3", "M0"}:
        raise RuntimeError("Gate E is restricted to B3 and M0.")
    paired: dict[str, set[str]] = {}
    for item in manifest["schedule"]:
        paired.setdefault(item["task"], set()).add(item["variant"])
    if len(paired) != 4 or any(
        variants != {"B3", "M0"} for variants in paired.values()
    ):
        raise RuntimeError("Gate E requires four paired B3/M0 tasks.")
    hard = json.loads(HARD_MANIFEST.read_text(encoding="utf-8"))
    hard_names = {item["class_name"] for item in hard["tasks"]}
    selected = set(paired)
    if selected & hard_names:
        raise RuntimeError("Gate E must not contain any Hard task.")
    coverage = capability_audit(REPOSITORY_ROOT)
    if not coverage["passed"]:
        raise RuntimeError("Protocol-v2 capability audit failed.")
    freeze_checks = []
    if manifest["protocol"] in VERSIONED_PROTOCOLS:
        if _git_output("rev-list", "-n", "1", manifest["source_tag"]) != (
            expected_source_commit
        ):
            raise RuntimeError("Gate-E source tag does not resolve to source.")
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
            raise RuntimeError("Gate-E source is not an ancestor of HEAD.")
        records = manifest.get("freeze_files", [])
        if not records:
            raise RuntimeError("Versioned protocol freeze file list is empty.")
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
            raise RuntimeError("Versioned protocol freeze file hash mismatch.")
    return {
        "selected_tasks": sorted(selected),
        "selected_task_count": len(selected),
        "schedule_cell_count": len(manifest["schedule"]),
        "paired": True,
        "hard_overlap": [],
        "capability_audit_passed": True,
        "freeze_file_checks": freeze_checks,
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
            "Fresh Gate-E suite directory already exists; refusing reuse."
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
        raise RuntimeError("Gate-E emulator is not connected.")
    client = TransformersClient(url)
    health = client.health()
    task_registry = registry.TaskRegistry()
    registered = task_registry.get_registry(
        task_registry.ANDROID_WORLD_FAMILY
    )
    seed = int(manifest["instance_seed"])
    instance_records = []
    for task_name in manifest_audit["selected_tasks"]:
        if task_name not in registered:
            raise RuntimeError(f"Unknown Gate-E task: {task_name}")
        task = generate_task(registered, task_name, seed)
        goal_hash, params_hash = instance_hash(task)
        instance_records.append(
            {
                "task": task_name,
                "seed": seed,
                "goal_sha256": goal_hash,
                "params_sha256": params_hash,
            }
        )
    result = {
        "schema_version": (
            "protocol_v2_2_gate_e_preflight.v1"
            if manifest["protocol"] == PROTOCOL_V2_2
            else "protocol_v2_1_gate_e_preflight.v1"
        ),
        "checked_at": utc_now(),
        "passed": True,
        "protocol": manifest["protocol"],
        "suite_id": manifest["suite_id"],
        "source_tag": manifest["source_tag"],
        "source_commit": manifest["source_commit"],
        "manifest_audit": manifest_audit,
        "instance_records": instance_records,
        "model_health": health,
        "emulator_connected": emulator_connected,
        "fresh_suite_directory_absent": True,
        "model_calls": 0,
        "gpu_experiment_cells": 0,
        "automatic_gate_e_launch": False,
        "automatic_gate_f_transition": False,
    }
    write_json(output, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def main(
    *,
    default_manifest: Path = DEFAULT_GATE_E_MANIFEST,
    expected_source_commit: str = DEFAULT_GATE_E_SOURCE_COMMIT,
) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=default_manifest,
    )
    parser.add_argument("--aggregate-only", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument(
        "--development-smoke-cells",
        type=int,
        default=0,
        help=(
            "Run the first N cells in a separate non-scored development "
            "directory; valid values are 1-7."
        ),
    )
    parser.add_argument(
        "--development-smoke-sequence",
        type=int,
        default=0,
        help=(
            "Run exactly one frozen sequence in a separate non-scored "
            "development directory; valid values are 1-8."
        ),
    )
    parser.add_argument(
        "--preflight-output",
        type=Path,
        default=None,
    )
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    preflight_output = args.preflight_output or (
        REPOSITORY_ROOT
        / (
            "reports/protocol_v2_2_gate_e_preflight.json"
            if manifest["protocol"] == PROTOCOL_V2_2
            else "reports/protocol_v2_1_gate_e_preflight.json"
        )
    )
    manifest_audit = validate_gate_e_manifest(
        manifest,
        expected_source_commit=expected_source_commit,
    )
    selected = set(manifest_audit["selected_tasks"])
    if args.development_smoke_cells and args.development_smoke_sequence:
        raise RuntimeError(
            "Choose only one development smoke selection mode."
        )
    if args.development_smoke_sequence:
        if not 1 <= args.development_smoke_sequence <= 8:
            raise RuntimeError(
                "--development-smoke-sequence must be between 1 and 8."
            )
        manifest = json.loads(json.dumps(manifest))
        manifest["schedule"] = [
            item
            for item in manifest["schedule"]
            if item["sequence"] == args.development_smoke_sequence
        ]
        if len(manifest["schedule"]) != 1:
            raise RuntimeError("Requested development sequence is absent.")
        manifest["suite_id"] = (
            manifest["suite_id"]
            + "_development_smoke_sequence_"
            + str(args.development_smoke_sequence)
        )
        manifest["output_root"] = "runs/protocol_v2_2_development"
    elif args.development_smoke_cells:
        if not 1 <= args.development_smoke_cells < 8:
            raise RuntimeError(
                "--development-smoke-cells must be between 1 and 7."
            )
        manifest = json.loads(json.dumps(manifest))
        manifest["schedule"] = manifest["schedule"][
            : args.development_smoke_cells
        ]
        manifest["suite_id"] = (
            manifest["suite_id"]
            + f"_development_smoke_{args.development_smoke_cells}"
        )
        manifest["output_root"] = "runs/protocol_v2_2_development"
    if args.preflight_only:
        return run_preflight(
            manifest=manifest,
            manifest_audit=manifest_audit,
            url=args.url,
            adb_path=args.adb_path,
            output=preflight_output,
        )

    suite_dir = (
        REPOSITORY_ROOT / manifest["output_root"] / manifest["suite_id"]
    )
    episode_root = suite_dir / "episodes"
    suite_dir.mkdir(parents=True, exist_ok=True)
    write_json(suite_dir / "manifest.snapshot.json", manifest)
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
        raise RuntimeError("Gate-E model identity mismatch.")

    prompts = {
        name: (PROJECT_ROOT / path).read_text(encoding="utf-8")
        for name, path in manifest["prompts"].items()
    }
    schemas = {
        name: PROJECT_ROOT / path
        for name, path in manifest["schemas"].items()
    }
    task_registry = registry.TaskRegistry()
    registered = task_registry.get_registry(task_registry.ANDROID_WORLD_FAMILY)
    seed = int(manifest["instance_seed"])
    instances = {}
    for task_name in sorted(selected):
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
    write_json(suite_dir / "instances.snapshot.json", {"instances": instances})

    existing_progress = suite_dir / "suite_progress.json"
    results: list[dict[str, Any]] = []
    infrastructure_attempts: list[dict[str, Any]] = []
    startup_audit_path = suite_dir / "startup_environment_audit.json"
    startup_audit: dict[str, Any] | None = None
    if existing_progress.is_file():
        prior = json.loads(existing_progress.read_text(encoding="utf-8"))
        results = list(prior.get("results", []))
        infrastructure_attempts = list(
            prior.get("infrastructure_attempts", [])
        )
    if startup_audit_path.is_file():
        startup_audit = load_startup_audit(startup_audit_path)
    started_at = utc_now()
    started_clock = time.monotonic()
    if args.aggregate_only:
        final = aggregate(
            manifest=manifest,
            health=health,
            results=results,
            infrastructure_attempts=infrastructure_attempts,
            started_at=started_at,
            elapsed_seconds=0.0,
            stopped_early=False,
            stop_reason=None,
            startup_audit=startup_audit,
        )
        write_json(suite_dir / "suite_summary.json", final)
        print(json.dumps(final, indent=2, ensure_ascii=False))
        return 0 if final["gate_passed"] else 3

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
            final = aggregate(
                manifest=manifest,
                health=health,
                results=results,
                infrastructure_attempts=infrastructure_attempts,
                started_at=started_at,
                elapsed_seconds=time.monotonic() - started_clock,
                stopped_early=True,
                stop_reason=(
                    "startup_environment_failed_twice:"
                    f"{type(exc).__name__}"
                ),
                startup_audit=startup_audit,
            )
            write_json(suite_dir / "suite_summary.json", final)
            write_json(suite_dir / "suite_progress.json", final)
            print(json.dumps(final, indent=2, ensure_ascii=False))
            return 3
    else:
        env = env_launcher.load_and_setup_env(
            console_port=args.console_port,
            emulator_setup=False,
            freeze_datetime=True,
            adb_path=args.adb_path,
            grpc_port=args.grpc_port,
        )
    stopped_early = False
    stop_reason = None
    consecutive_infra_codes: list[str] = []
    try:
        completed_sequences = {item["sequence"] for item in results}
        for frozen in manifest["schedule"]:
            if frozen["sequence"] in completed_sequences:
                continue
            elapsed = time.monotonic() - started_clock
            if elapsed >= manifest["limits"]["hard_wall_time_seconds"]:
                stopped_early = True
                stop_reason = "hard_wall_time_exceeded_before_next_cell"
                break
            item = {
                **frozen,
                "seed": seed,
            }
            expected = instances[item["task"]]
            episode_dir = episode_root / (
                f"{item['sequence']:02d}_{item['variant']}_{item['task']}_"
                f"seed{seed}"
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
                manifest["limits"]["max_infrastructure_attempts_per_cell"] + 1,
            ):
                attempts_used = attempt
                task = generate_task(registered, item["task"], seed)
                current_hash = instance_hash(task)
                if current_hash != (
                    expected["goal_sha256"],
                    expected["params_sha256"],
                ):
                    raise RuntimeError("Task instance hash drift detected.")
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
                )
                episode_id = (
                    f"{manifest['suite_id']}_{item['sequence']:02d}_"
                    f"{item['variant']}_{item['task']}_seed{seed}_a{attempt}"
                )
                summary = controller.run(
                    env=env,
                    task=task,
                    episode_id=episode_id,
                    episode_dir=episode_dir,
                    seed=seed,
                    protocol=manifest["protocol"],
                    variant=item["variant"],
                )
                if not summary.get("error"):
                    consecutive_infra_codes.clear()
                    break
                infra_code = classify_infrastructure(summary)
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
                record = {
                    "item": item,
                    "attempt": attempt,
                    "code": infra_code,
                    "archive": archived.relative_to(
                        REPOSITORY_ROOT
                    ).as_posix(),
                    "error": summary["error"],
                }
                infrastructure_attempts.append(record)
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
                            / (
                                f"{item['sequence']:02d}_after_attempt_"
                                f"{attempt:02d}"
                            )
                        ),
                    )
                elif infra_code == "INFRA_MODEL_UNAVAILABLE":
                    wait_for_model_service(
                        client,
                        recovery_dir=(
                            suite_dir
                            / "recoveries"
                            / (
                                f"{item['sequence']:02d}_model_attempt_"
                                f"{attempt:02d}"
                            )
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
            result = episode_result(
                item=item,
                summary=summary,
                episode_dir=episode_dir,
                attempts=attempts_used,
                memory_audit=memory_audit,
            )
            results.append(result)
            progress = aggregate(
                manifest=manifest,
                health=health,
                results=results,
                infrastructure_attempts=infrastructure_attempts,
                started_at=started_at,
                elapsed_seconds=time.monotonic() - started_clock,
                stopped_early=False,
                stop_reason=None,
                startup_audit=startup_audit,
            )
            write_json(suite_dir / "suite_progress.json", progress)
            print(
                json.dumps(
                    {
                        "completed": len(results),
                        "latest": result,
                        "successes": progress["success_count"],
                        "criteria_so_far": progress["criteria"],
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            if not result["valid_after_one_repair"]:
                stopped_early = True
                stop_reason = "model_output_invalid_after_one_bounded_repair"
                break
            semantic_audit = result.get("semantic_progress_audit")
            if semantic_audit and not semantic_audit["passed"]:
                stopped_early = True
                stop_reason = "semantic_progress_audit_failed"
                break
    finally:
        env.close()

    final = aggregate(
        manifest=manifest,
        health=health,
        results=results,
        infrastructure_attempts=infrastructure_attempts,
        started_at=started_at,
        elapsed_seconds=time.monotonic() - started_clock,
        stopped_early=stopped_early,
        stop_reason=stop_reason,
        startup_audit=startup_audit,
    )
    write_json(suite_dir / "suite_summary.json", final)
    write_json(suite_dir / "suite_progress.json", final)
    print(json.dumps(final, indent=2, ensure_ascii=False), flush=True)
    return 0 if final["gate_passed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
