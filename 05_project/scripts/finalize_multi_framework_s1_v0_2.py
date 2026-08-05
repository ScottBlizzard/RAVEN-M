"""Mechanically qualify the frozen four-arm S1 smoke set.

This script never authorizes Hard calls.  It records whether the preregistered
minimum launch set survived S1 and emits a return-to-planner decision when it
did not.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = REPO_ROOT / "05_project"
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.multi_framework_benchmark.capability_manifest import (  # noqa: E402
    minimum_launch_set,
    sha256_file,
    verify_protected,
)


FIXED_TASKS = {"ContactsAddContact", "ClockStopWatchRunning"}
ARMS = ("CB-PX-B3", "CB-PX-M0", "NS-PX-GO15", "NS-PX-UIV4")
OUTPUTS = PROJECT_ROOT / "outputs/multi_framework_s1_v0_2"
S0 = PROJECT_ROOT / "metadata/multi_framework_s0_v0_2"
DEST = PROJECT_ROOT / "metadata/multi_framework_s1_v0_2/final"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def raven_arm(arm_id: str, directory: str) -> dict:
    root = OUTPUTS / directory
    report_path = root / "s1_report.json"
    report = load(report_path)
    tasks = []
    for item in report["results"]:
        summary = item["summary"]
        tasks.append(
            {
                "task": item["task_class"],
                "reward": summary["evaluator_reward"],
                "success": summary["success"],
                "failure_code": summary["failure_code"],
                "steps": summary["decision_count"],
                "parseable_decisions": item["parseable_decisions"],
                "nonterminal_actions": item["executed_nonterminal_actions"],
                "screen_changes": item["observed_state_changes"],
                "model_calls": summary["model_call_count"],
                "lifecycle": {
                    "initialize": item["task_initialization"],
                    "evaluator": item["evaluator_calls"],
                    "tear_down": item["task_teardown"],
                    "post_episode_reset": item["post_episode_reset"],
                },
                "unresolved_error": summary["error"],
            }
        )
    required_logs = [report_path]
    for task_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        required_logs.append(task_dir / "events.jsonl")
    return {
        "arm_id": arm_id,
        "source_report": str(report_path.relative_to(REPO_ROOT)),
        "source_report_sha256": sha256_file(report_path),
        "tasks": tasks,
        "required_logs_complete": all(path.is_file() for path in required_logs),
        "protected_hashes_verified": True,
        "task_rerun_count": report["rerun_count"],
    }


def external_arm(arm_id: str, directory: str) -> dict:
    root = OUTPUTS / directory
    report_path = root / "summary.json"
    report = load(report_path)
    call_path = root / "model_calls.json"
    calls = load(call_path)
    tasks = []
    for item in report["tasks"]:
        reward = item["reward"]
        if isinstance(reward, float) and math.isnan(reward):
            reward = None
        lifecycle = dict(item["lifecycle"])
        tasks.append(
            {
                "task": item["task"],
                "reward": reward,
                "success": reward == 1.0,
                "steps": item["steps"],
                "parseable_decisions": item["parseable_decisions"],
                "nonterminal_actions": item["nonterminal_actions"],
                "screen_changes": item["screen_changes"],
                "model_calls": item["model_calls"],
                "lifecycle": lifecycle,
                "unresolved_error": item["exception"],
            }
        )
    response_paths = [root / call["response_path"].replace("\\", "/") for call in calls if call.get("ok")]
    # response_path is repository-relative in the frozen transport log.
    response_paths = [REPO_ROOT / path.relative_to(root) if path.is_absolute() else REPO_ROOT / path for path in response_paths]
    required_logs = [report_path, call_path, root / "frozen_runtime_config.json"]
    required_logs_complete = all(path.is_file() for path in required_logs)
    required_logs_complete = required_logs_complete and all(path.is_file() for path in response_paths)
    return {
        "arm_id": arm_id,
        "source_report": str(report_path.relative_to(REPO_ROOT)),
        "source_report_sha256": sha256_file(report_path),
        "model_call_log": str(call_path.relative_to(REPO_ROOT)),
        "model_call_log_sha256": sha256_file(call_path),
        "successful_transport_calls": sum(bool(call.get("ok")) for call in calls),
        "failed_transport_calls": sum(not bool(call.get("ok")) for call in calls),
        "tasks": tasks,
        "required_logs_complete": required_logs_complete,
        "protected_hashes_verified": report["protected_hashes_verified"],
        "task_rerun_count": 0,
    }


def arm_gates(arm: dict, answer_ok: bool, protected_ok: bool, leakage_free: bool) -> dict:
    tasks = arm["tasks"]
    task_names = {task["task"] for task in tasks}
    lifecycle_ok = all(
        task["lifecycle"].get("initialize") == 1
        and task["lifecycle"].get("evaluator") == 1
        and task["lifecycle"].get("tear_down") == 1
        and task["lifecycle"].get("post_episode_reset", 1) == 1
        for task in tasks
    )
    unresolved = any(task["unresolved_error"] for task in tasks)
    gates = {
        "fixed_two_tasks": len(tasks) == 2 and task_names == FIXED_TASKS,
        "task_initialization_teardown_reset_2_of_2": lifecycle_ok,
        "parseable_decisions_at_least_2_total": sum(task["parseable_decisions"] for task in tasks) >= 2,
        "executed_nonterminal_action_at_least_1_per_task": all(task["nonterminal_actions"] >= 1 for task in tasks),
        "observed_state_change_at_least_1_total": sum(task["screen_changes"] for task in tasks) >= 1,
        "evaluator_exactly_1_per_task": all(task["lifecycle"].get("evaluator") == 1 for task in tasks),
        "required_logs_100_percent": arm["required_logs_complete"],
        "answer_fixtures_3_of_3": answer_ok,
        "hard_task_leakage_zero": leakage_free,
        "protected_hash_changes_zero": protected_ok and arm["protected_hashes_verified"],
        "unresolved_infrastructure_errors_zero": not unresolved,
        "task_reruns_zero": arm["task_rerun_count"] == 0,
    }
    return gates


def main() -> None:
    if DEST.exists():
        raise FileExistsError(f"Refusing to overwrite frozen S1 output: {DEST}")

    protocol = load(PROJECT_ROOT / "configs/experiments/multi_framework_hard_benchmark_v0_2.json")
    protected = verify_protected(REPO_ROOT, protocol["protected_paths"])
    answer = load(S0 / "answer_fixtures.json")
    answer_ok = answer.get("passed") is True and len(answer.get("tasks", [])) == 3

    arms = {
        "CB-PX-B3": raven_arm("CB-PX-B3", "01_b3"),
        "CB-PX-M0": raven_arm("CB-PX-M0", "02_m0"),
        "NS-PX-GO15": external_arm("NS-PX-GO15", "03_guiowl"),
        "NS-PX-UIV4": external_arm("NS-PX-UIV4", "04_uivoyager"),
    }

    hard_classes = {item["class_name"] for item in load(PROJECT_ROOT / "configs/task_manifests/androidworld_hard_v1.json")["tasks"]}
    request_logs = list(OUTPUTS.glob("**/*.request.json"))
    leaked_classes = sorted(
        task_class
        for task_class in hard_classes
        if any(task_class in path.read_text(encoding="utf-8", errors="replace") for path in request_logs)
    )
    leakage_free = not leaked_classes

    qualified = []
    normalized = {}
    for arm_id in ARMS:
        arm = arms[arm_id]
        gates = arm_gates(arm, answer_ok, bool(protected), leakage_free)
        arm["gates"] = gates
        arm["qualified"] = all(gates.values())
        if arm["qualified"]:
            qualified.append(arm_id)
        normalized[arm_id] = arm

    minimum_ok, minimum_reasons = minimum_launch_set(set(qualified))
    all_four_ok = len(qualified) == 4
    status = "PASS" if minimum_ok and all_four_ok else "FAIL"

    attempts = {
        "CB-PX-B3": {
            "discarded_infrastructure_attempts": 1,
            "reason": "outer_shell_timeout_120s",
            "preserved_path": "05_project/outputs/multi_framework_s1_v0_2/01_b3.infra_timeout_120s_20260805",
        },
        "CB-PX-M0": {"discarded_infrastructure_attempts": 0},
        "NS-PX-GO15": {
            "discarded_infrastructure_attempts": 1,
            "reason": "windows_named_temporary_apk_lifetime",
            "preserved_path": "05_project/outputs/multi_framework_s1_v0_2/03_guiowl.infra_temp_apk_windows_20260805",
            "final_failure": "image_url_transport_contract_rejected_before_generation",
        },
        "NS-PX-UIV4": {"discarded_infrastructure_attempts": 0},
    }

    qualification = {
        "schema_version": "multi_framework_s1_qualification.v0.2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "classification": "DEV_ONLY",
        "qualified_arms": qualified,
        "failed_arms": [arm for arm in ARMS if arm not in qualified],
        "minimum_launch_set_pass": minimum_ok,
        "minimum_launch_set_reasons": minimum_reasons,
        "all_four_preregistered_arms_pass": all_four_ok,
        "hard_model_calls_authorized": False,
        "next_action": "RETURN_TO_GPT_PRO_FOR_PREREGISTERED_REPLACEMENT_OR_NEW_DEV_ROUND",
        "hard_task_leaked_classes": leaked_classes,
        "attempt_accounting": attempts,
        "arms": normalized,
    }

    DEST.mkdir(parents=True)
    out = DEST / "s1_qualification.json"
    out.write_text(json.dumps(qualification, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    seal = {
        "schema_version": "multi_framework_s1_evidence_seal.v0.2",
        "s1_qualification": str(out.relative_to(REPO_ROOT)),
        "s1_qualification_sha256": sha256_file(out),
        "hard_model_calls_authorized": False,
        "status": status,
    }
    (DEST / "evidence_seal.json").write_text(
        json.dumps(seal, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(seal | {"qualified_arms": qualified}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
