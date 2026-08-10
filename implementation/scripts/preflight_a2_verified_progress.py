"""Zero-generation qualification for A2 Verified Progress Memory."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
LOCAL_RUNTIME = REPOSITORY_ROOT / "06_local_runtime"
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(LOCAL_RUNTIME / "scripts"))

from raven_m.official_qwen_mobile.a2_contract import (  # noqa: E402
    A2_CONFIG,
    A2_GUARD_REPLAY,
    A2_MANIFEST,
    A2_PREFLIGHT_REPORT,
    A2_REFERENCE_LEDGER,
    A2_RUNTIME_QUALIFICATION,
    current_source_freeze,
)
from raven_m.official_qwen_mobile.progress_memory import (  # noqa: E402
    RepeatedNoProgressGuard,
    VerifiedProgressMemory,
)
from raven_m.official_qwen_mobile.protocol import (  # noqa: E402
    A2_VERIFIED_PROGRESS_SYSTEM_PROMPT,
    OFFICIAL_SYSTEM_PROMPT,
    build_user_prompt,
)
from raven_m.official_qwen_mobile.working_memory import append_working_memory  # noqa: E402


EXPECTED_OFFICIAL_PROMPT_SHA256 = "9d060af15f62acb31b9fb197649ec001d4096491d7fb102de929316944b3e26d"


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=A2_PREFLIGHT_REPORT)
    args = parser.parse_args()
    errors: list[str] = []

    config = json.loads(A2_CONFIG.read_text(encoding="utf-8"))
    manifest = json.loads(A2_MANIFEST.read_text(encoding="utf-8"))
    instances = [
        item for item in (manifest.get("instances") or [])
        if int(item.get("task_seed", -1)) == 20260806
    ]
    if len(instances) != 19 or len({item.get("task_class") for item in instances}) != 19:
        errors.append("frozen_manifest_is_not_19_unique_seed_20260806_tasks")
    instantiated_tasks: list[str] = []
    try:
        import androidworld_compat  # noqa: F401
        from android_world import registry
        from raven_m.multi_framework_benchmark.task_instances import instantiate_verified

        task_registry = registry.TaskRegistry()
        available = task_registry.get_registry(task_registry.ANDROID_WORLD_FAMILY)
        for item in instances:
            task = instantiate_verified(available, item)
            instantiated_tasks.append(str(task.name))
    except Exception as exc:
        errors.append(f"androidworld_19_task_instantiation_failed:{type(exc).__name__}:{exc}")
    if config.get("benchmark", {}).get("task_count") != 19:
        errors.append("config_task_count_drift")
    if config.get("agent", {}).get("extra_model_calls") != 0:
        errors.append("a2_must_not_add_model_calls")
    memory_config = config.get("agent", {}).get("memory", {})
    if memory_config.get("state_count") != 1 or memory_config.get("max_chars") != 1200:
        errors.append("a2_memory_capacity_drift")
    guard_config = config.get("agent", {}).get("cost_guard", {})
    if (
        guard_config.get("no_progress_execution_threshold") != 2
        or guard_config.get("max_ignored_block_warnings") != 2
        or guard_config.get("success_credit") is not False
    ):
        errors.append("a2_cost_guard_contract_drift")

    official_prompt_sha = sha256(OFFICIAL_SYSTEM_PROMPT.encode("utf-8")).hexdigest()
    if official_prompt_sha != EXPECTED_OFFICIAL_PROMPT_SHA256:
        errors.append("official_prompt_drift")
    if not A2_VERIFIED_PROGRESS_SYSTEM_PROMPT.startswith(OFFICIAL_SYSTEM_PROMPT):
        errors.append("a2_prompt_not_additive")

    canary = "A2-CANARY-9157"
    memory = VerifiedProgressMemory(max_chars=1200)
    baseline_prompt = build_user_prompt("preflight", [])
    empty_block, empty_read = memory.read()
    if append_working_memory(baseline_prompt, empty_block) != baseline_prompt:
        errors.append("empty_a2_memory_changes_a0_prompt")
    action_summary = (
        f"PROGRESS[observed={canary}; verified=form visible; pending=save; "
        "expected=confirmation appears] | Tap Save."
    )
    write = memory.observe_step(
        source_step=0,
        action_summary=action_summary,
        canonical_action={"type": "tap", "x": 0.8, "y": 0.1},
        transition={
            "changed_pixel_fraction_gt_5": 0.0,
            "exactly_unchanged": True,
            "activity_changed": False,
            "ui_sha_changed": False,
        },
        source_call_id="preflight-call",
        source_response_sha256="preflight-response",
        source_screenshot_sha256="preflight-screen",
    )
    block, nonempty_read = memory.read()
    injected_prompt = append_working_memory(baseline_prompt, block)
    if not write.get("written") or canary not in injected_prompt:
        errors.append("a2_canary_write_read_injection_failed")
    if "no_visible_change" not in block:
        errors.append("a2_outcome_not_injected")
    if "PROGRESS[" in memory.history_summary(action_summary):
        errors.append("a2_progress_payload_duplicated_in_history")
    if not nonempty_read.get("nonempty") or not memory.audit_record().get("active"):
        errors.append("a2_memory_activation_audit_failed")
    if empty_read.get("nonempty"):
        errors.append("empty_a2_memory_read_marked_nonempty")

    memory.record_progress_parse(action_summary)
    guard = RepeatedNoProgressGuard(
        no_progress_threshold=2, max_ignored_block_warnings=2
    )
    snapshot = {
        "pixels": np.zeros((12, 8, 3), dtype=np.uint8),
        "ui_sha256": "audit-only-stable-ui",
        "foreground": {"activity": "audit-only-pkg/.Main"},
    }
    action = {
        "canonical": {"type": "tap", "x": 0.5, "y": 0.08},
        "screen_size": [100, 100],
        "actual_pixels": {"x": 50, "y": 8},
        "upstream_action": {"action_type": "click", "x": 50, "y": 8},
    }
    transition = {
        "changed_pixel_fraction_gt_5": 0.0,
        "exactly_unchanged": True,
        "activity_changed": False,
        "ui_sha_changed": False,
    }
    guard_sequence: list[dict] = []
    for _ in range(2):
        guard_sequence.append(guard.assess(before=snapshot, mapped_action=action))
        guard.observe(before=snapshot, after=snapshot, mapped_action=action, transition=transition)
    third = guard.assess(before=snapshot, mapped_action=action)
    guard_sequence.append(third)
    first_block = guard.record_block(third)
    second_block = guard.record_block(third)
    third_block = guard.record_block(third)
    if [item["blocked"] for item in guard_sequence] != [False, False, True]:
        errors.append("a2_guard_did_not_allow_two_then_block_third")
    if first_block["cost_stop"] or second_block["cost_stop"] or not third_block["cost_stop"]:
        errors.append("a2_guard_cost_stop_threshold_drift")

    evidence_checks = {}
    for path, label in (
        (A2_REFERENCE_LEDGER, "reference_ledger"),
        (A2_GUARD_REPLAY, "guard_replay"),
        (A2_RUNTIME_QUALIFICATION, "runtime_qualification"),
    ):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            evidence_checks[label] = {
                "path": str(path.relative_to(REPOSITORY_ROOT)),
                "sha256": sha256(path.read_bytes()).hexdigest(),
                "status": payload.get("status"),
                "generation_calls": payload.get("generation_calls"),
                "qualification_pass": payload.get("qualification_pass"),
            }
        except Exception as exc:
            errors.append(f"{label}_unreadable:{type(exc).__name__}:{exc}")
    ledger = json.loads(A2_REFERENCE_LEDGER.read_text(encoding="utf-8"))
    if (
        ledger.get("summaries", {}).get("A0", {}).get("success_count") != 4
        or ledger.get("summaries", {}).get("A1", {}).get("success_count") != 5
        or ledger.get("paired_outcome") != {"A1_losses": 0, "A1_wins": 1, "ties": 18}
    ):
        errors.append("a0_a1_reference_ledger_invariant_drift")
    replay = json.loads(A2_GUARD_REPLAY.read_text(encoding="utf-8"))
    if replay.get("generation_calls") != 0 or not replay.get("qualification_pass"):
        errors.append("a1_exact_guard_replay_failed")
    runtime = json.loads(A2_RUNTIME_QUALIFICATION.read_text(encoding="utf-8"))
    if runtime.get("status") != "pass" or runtime.get("generation_calls") != 0:
        errors.append("a2_runtime_qualification_failed")

    tests = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests",
            "-q",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src")},
    )
    if tests.returncode != 0:
        errors.append("targeted_tests_failed")

    report = {
        "status": "pass" if not errors else "fail",
        "generation_calls": 0,
        "errors": errors,
        "experiment_id": config.get("experiment_id"),
        "official_prompt_sha256": official_prompt_sha,
        "a2_prompt_sha256": sha256(A2_VERIFIED_PROGRESS_SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
        "manifest_sha256": sha256(A2_MANIFEST.read_bytes()).hexdigest(),
        "manifest_task_order": [item["task_class"] for item in instances],
        "task_seed": 20260806,
        "androidworld_instantiated_tasks": instantiated_tasks,
        "memory_canary": {
            "value": canary,
            "write": write,
            "empty_read": empty_read,
            "nonempty_read": nonempty_read,
            "present_in_next_prompt": canary in injected_prompt,
            "structured_prefix_removed_from_history": "PROGRESS[" not in memory.history_summary(action_summary),
        },
        "cost_guard_canary": {
            "assessments": guard_sequence,
            "first_block": first_block,
            "second_block": second_block,
            "third_block": third_block,
        },
        "evidence_checks": evidence_checks,
        "tests": {
            "returncode": tests.returncode,
            "stdout": tests.stdout,
            "stderr": tests.stderr,
        },
        "source_freeze": current_source_freeze(),
    }
    _atomic_json(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
