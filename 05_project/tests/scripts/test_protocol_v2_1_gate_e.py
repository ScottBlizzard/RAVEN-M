from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = (
    ROOT / "05_project/configs/experiments/v2_1_capability_gate.json"
)
OLD_MANIFEST = (
    ROOT / "05_project/configs/experiments/v2_capability_gate.json"
)
RUNNER = ROOT / "05_project/scripts/run_protocol_v2_gate_e.py"
WRAPPER = ROOT / "05_project/scripts/run_protocol_v2_1_gate_e.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v2_1_gate_e_preserves_the_frozen_paired_design() -> None:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    old = json.loads(OLD_MANIFEST.read_text(encoding="utf-8"))
    assert value["protocol"] == "androidworld_protocol_v2_1_exploratory"
    assert value["suite_id"] == "nonhard_capability_v2_1_seed20260729_r1"
    assert value["output_root"] == "runs/protocol_v2_1"
    assert value["instance_seed"] == old["instance_seed"]
    assert value["blocked_order_seed"] == old["blocked_order_seed"]
    assert value["schedule"] == old["schedule"]
    assert value["limits"]["max_valid_cells"] == 8
    assert value["limits"]["max_infrastructure_attempts_per_cell"] == 2
    assert not value["stop_policy"]["automatic_gate_f_transition"]
    assert value["stop_policy"]["stop_on_semantic_progress_audit_error"]
    source = value["source_commit"]
    assert source == "PENDING_PROTOCOL_V2_1_GATE_E_FREEZE" or re.fullmatch(
        r"[0-9a-f]{40}", source
    )


def test_v2_1_wrapper_and_manifest_share_the_source_freeze() -> None:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source = WRAPPER.read_text(encoding="utf-8")
    match = re.search(r'^SOURCE_COMMIT = "([^"]+)"$', source, re.MULTILINE)
    assert match
    assert match.group(1) == value["source_commit"]


def semantic_step(
    *,
    step: int,
    action: dict,
    state: str,
    after: str,
    blocked: bool,
    failures: list[str] | None = None,
) -> dict:
    return {
        "step": step,
        "executed": True,
        "decision": {"action": action},
        "before_semantic_ui": {
            "source": "accessibility",
            "sha256": state,
        },
        "after_semantic_ui": {
            "source": "accessibility",
            "sha256": after,
        },
        "protocol_v2_guard": {
            "semantic_no_progress_repeat_count": int(state == after),
            "fingerprint_blocked": blocked,
            "new_visible_failures": failures or [],
        },
    }


def test_semantic_audit_detects_executed_blocked_action() -> None:
    runner = load_module(RUNNER, "protocol_v2_1_gate_e_runner_blocked")
    action = {"type": "tap", "x": 0.9, "y": 0.1}
    summary = {
        "failure_code": "TASK_UNSUCCESSFUL_AT_BUDGET",
        "protocol_v2_guard": {"validation_block_count": 0},
        "steps": [
            semantic_step(
                step=0,
                action=action,
                state="form",
                after="form",
                blocked=True,
                failures=["The event cannot end earlier than it starts"],
            ),
            semantic_step(
                step=1,
                action=action,
                state="form",
                after="form",
                blocked=True,
            ),
        ],
    }
    audit = runner.semantic_progress_audit(summary)
    assert not audit["passed"]
    assert audit["executed_blocked_action_steps"] == [1]
    assert audit["visible_failure_count"] == 1


def test_semantic_audit_accepts_different_successful_recovery() -> None:
    runner = load_module(RUNNER, "protocol_v2_1_gate_e_runner_recovery")
    summary = {
        "failure_code": None,
        "protocol_v2_guard": {"validation_block_count": 1},
        "steps": [
            semantic_step(
                step=0,
                action={"type": "tap", "x": 0.9, "y": 0.1},
                state="invalid-form",
                after="invalid-form",
                blocked=True,
                failures=["Invalid end time"],
            ),
            semantic_step(
                step=1,
                action={
                    "type": "tap",
                    "x": 0.5,
                    "y": 0.5,
                },
                state="invalid-form",
                after="editing-form",
                blocked=False,
            ),
        ],
    }
    audit = runner.semantic_progress_audit(summary)
    assert audit["passed"]
    assert audit["executed_blocked_action_steps"] == []
    assert not audit["unresolved_guard_repair"]


def test_semantic_audit_requires_every_executed_step_record() -> None:
    runner = load_module(RUNNER, "protocol_v2_1_gate_e_runner_missing")
    summary = {
        "failure_code": None,
        "protocol_v2_guard": {},
        "steps": [
            {
                "step": 3,
                "executed": True,
                "decision": {"action": {"type": "press_back"}},
            }
        ],
    }
    audit = runner.semantic_progress_audit(summary)
    assert not audit["passed"]
    assert audit["missing_semantic_audit_steps"] == [3]


def test_v2_1_aggregate_requires_startup_and_semantic_audits() -> None:
    runner = load_module(RUNNER, "protocol_v2_1_gate_e_aggregate")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    results = []
    for item in manifest["schedule"]:
        task_index = sorted(
            {entry["task"] for entry in manifest["schedule"]}
        ).index(item["task"])
        result = {
            **item,
            "goal_sha256": f"goal-{task_index}",
            "params_sha256": f"params-{task_index}",
            "success": item["sequence"] <= 4,
            "failure_code": (
                None
                if item["sequence"] <= 4
                else "TASK_UNSUCCESSFUL_AT_BUDGET"
            ),
            "answer_cache_match_count": int(
                item["task"] == "SimpleCalendarEventsOnDate"
            ),
            "completion_adjudication_count": 0,
            "valid_after_one_repair": True,
            "evaluator_prompt_leak_steps": [],
            "memory_audit_errors": [],
            "unhandled_third_identical_no_effect_action": False,
            "semantic_progress_audit": {
                "passed": True,
                "executed_blocked_action_steps": [],
                "unresolved_guard_repair": False,
            },
        }
        results.append(result)
    health = {
        "backend": runner.EXPECTED_BACKEND,
        "revision": runner.EXPECTED_REVISION,
    }
    passed = runner.aggregate(
        manifest=manifest,
        health=health,
        results=results,
        infrastructure_attempts=[],
        started_at="2026-07-27T00:00:00+00:00",
        elapsed_seconds=1.0,
        stopped_early=False,
        stop_reason=None,
        startup_audit={"last_status": "clean"},
    )
    assert passed["gate_passed"]
    assert passed["criteria"]["semantic_progress_audit"]
    assert passed["criteria"]["startup_environment_accounting"]
    missing_startup = runner.aggregate(
        manifest=manifest,
        health=health,
        results=results,
        infrastructure_attempts=[],
        started_at="2026-07-27T00:00:00+00:00",
        elapsed_seconds=1.0,
        stopped_early=False,
        stop_reason=None,
        startup_audit=None,
    )
    assert not missing_startup["gate_passed"]
    assert not missing_startup["criteria"]["startup_environment_accounting"]
