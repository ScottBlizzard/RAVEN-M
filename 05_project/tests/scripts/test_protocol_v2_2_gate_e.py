from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = (
    ROOT / "05_project/configs/experiments/v2_2_capability_gate.json"
)
V2_1_MANIFEST = (
    ROOT / "05_project/configs/experiments/v2_1_capability_gate.json"
)
RUNNER = ROOT / "05_project/scripts/run_protocol_v2_gate_e.py"
WRAPPER = ROOT / "05_project/scripts/run_protocol_v2_2_gate_e.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v2_2_preserves_pairing_budgets_and_b3_baseline() -> None:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    prior = json.loads(V2_1_MANIFEST.read_text(encoding="utf-8"))
    assert value["protocol"] == "androidworld_protocol_v2_2_exploratory"
    assert value["instance_seed"] == prior["instance_seed"]
    assert value["blocked_order_seed"] == prior["blocked_order_seed"]
    assert value["schedule"] == prior["schedule"]
    assert value["prompts"]["summary"] == prior["prompts"]["summary"]
    assert value["schemas"] == prior["schemas"]
    assert value["limits"] == prior["limits"]
    source = value["source_commit"]
    assert source == "PENDING_PROTOCOL_V2_2_GATE_E_FREEZE" or re.fullmatch(
        r"[0-9a-f]{40}", source
    )


def test_v2_2_wrapper_and_manifest_share_source_freeze() -> None:
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    source = WRAPPER.read_text(encoding="utf-8")
    match = re.search(r'^SOURCE_COMMIT = "([^"]+)"$', source, re.MULTILINE)
    assert match
    assert match.group(1) == value["source_commit"]


def test_v2_2_aggregate_requires_readiness_accounting() -> None:
    runner = load_module(RUNNER, "protocol_v2_2_gate_e_runner")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    results = []
    for item in manifest["schedule"]:
        task_index = sorted(
            {entry["task"] for entry in manifest["schedule"]}
        ).index(item["task"])
        results.append(
            {
                **item,
                "goal_sha256": f"goal-{task_index}",
                "params_sha256": f"params-{task_index}",
                "success": item["sequence"] <= 4,
                "failure_code": None,
                "answer_cache_match_count": int(
                    item["task"] == "SimpleCalendarEventsOnDate"
                ),
                "completion_adjudication_count": 0,
                "valid_after_one_repair": True,
                "evaluator_prompt_leak_steps": [],
                "memory_audit_errors": [],
                "unhandled_third_identical_no_effect_action": False,
                "readiness_observation_count": 1,
                "semantic_progress_audit": {
                    "passed": True,
                    "executed_blocked_action_steps": [],
                    "unresolved_guard_repair": False,
                },
            }
        )
    health = {
        "backend": runner.EXPECTED_BACKEND,
        "revision": runner.EXPECTED_REVISION,
    }
    summary = runner.aggregate(
        manifest=manifest,
        health=health,
        results=results,
        infrastructure_attempts=[],
        started_at="2026-07-27T00:00:00+00:00",
        elapsed_seconds=1,
        stopped_early=False,
        stop_reason=None,
        startup_audit={"last_status": "clean"},
    )
    assert summary["criteria"]["readiness_accounting"]
    assert summary["gate_passed"]
    results[0]["readiness_observation_count"] = 0
    failed = runner.aggregate(
        manifest=manifest,
        health=health,
        results=results,
        infrastructure_attempts=[],
        started_at="2026-07-27T00:00:00+00:00",
        elapsed_seconds=1,
        stopped_early=False,
        stop_reason=None,
        startup_audit={"last_status": "clean"},
    )
    assert not failed["criteria"]["readiness_accounting"]
    assert not failed["gate_passed"]
