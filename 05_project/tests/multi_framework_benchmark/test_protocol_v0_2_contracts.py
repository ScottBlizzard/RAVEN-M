"""The 20 mandatory pre-S1 fixtures from GPT Pro protocol section 14.7."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import validate

from raven_m.multi_framework_benchmark.action_normalizer import ScreenTransform, maximum_run, normalize_action
from raven_m.multi_framework_benchmark.androidworld_adapter import ActionBudget, ActionBudgetExceeded, BudgetedAndroidWorldAdapter, write_answer_contract
from raven_m.multi_framework_benchmark.arm_registry import ARM_REGISTRY
from raven_m.multi_framework_benchmark.capability_manifest import S0_GATES, validate_capability, verify_protected
from raven_m.multi_framework_benchmark.evaluator_bridge import EvaluatorBridge
from raven_m.multi_framework_benchmark.event_schema import REQUIRED_EVENT_FIELDS, SCHEMA_VERSION, validate_event
from raven_m.multi_framework_benchmark.model_usage_logger import BudgetExceeded, UsageBudget
from raven_m.multi_framework_benchmark.observation_audit import audit_observation, pixel_effect_class
from raven_m.multi_framework_benchmark.reset_guard import LIFECYCLE, ResetGuard
from raven_m.multi_framework_benchmark.runner import CellLimits, HashFreezeGuard, assert_output_root_is_new, validate_rerun, validate_task_hash_equality


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent


def event_fixture() -> dict:
    event = {field: None for field in REQUIRED_EVENT_FIELDS}
    event.update(schema_version=SCHEMA_VERSION, run_id="r", arm_id="CB-PX-B3", lane="CB-PX", reproduction_label="COMMON_BACKBONE_ADAPTER_COMPARISON", source_repo="repo", source_commit="a" * 40, checkpoint_id="model", checkpoint_revision="b" * 40, code_license="internal", model_license="apache", runtime_hash="c" * 64, dependency_lock_hash="d" * 64, prompt_hash="e" * 64, task_id="D01", task_class="ContactsAddContact", task_seed=20260805, task_params_hash="f" * 64, attempt_id="a1", step_index=0, timestamp_utc="2026-08-05T00:00:00+00:00", observation_privileges=["screenshot"], input_tokens=0, output_tokens=0, latency_seconds=0.0, parse_status="NOT_CALLED", feedback_event=False, action_execute_status="NOT_EXECUTED", finish_claim=False, validity_class="PENDING")
    return event


# 1. action canonicalization fixtures
def test_01_action_canonicalization() -> None:
    assert normalize_action({"type": "click", "x": 11.8, "y": 20}) == {"action": "tap", "x": 11, "y": 20}
    assert normalize_action({"action": "input_text", "text": "x"}) == {"action": "type", "text": "x"}


# 2. coordinate scaling fixtures
def test_02_coordinate_scaling() -> None:
    assert ScreenTransform(100, 200, 200, 400).point(25, 50) == (50, 100)
    with pytest.raises(ValueError):
        ScreenTransform(100, 200, 200, 400).point(101, 50)


# 3. answer -> interaction_cache fixtures
@pytest.mark.parametrize("answer", ["one", "12.5", "Monday"])
def test_03_answer_contract(answer: str) -> None:
    cache: dict[str, str] = {}
    write_answer_contract(cache, answer)
    assert cache["answer"] == answer


# 4. finish claim cannot override evaluator
def test_04_finish_does_not_override_evaluator() -> None:
    outcome = EvaluatorBridge(lambda: {"reward": 0}).evaluate_once(finish_claim=True)
    assert outcome.finish_claim and not outcome.success


# 5. evaluator state excluded from prompt
def test_05_evaluator_leakage_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="Evaluator state leakage"):
        audit_observation({"screenshot": b"x", "reward": 1}, ARM_REGISTRY["CB-PX-B3"])


# 6. UI tree excluded from screenshot-only arms
def test_06_ui_tree_excluded_from_pixel_arm() -> None:
    with pytest.raises(RuntimeError, match="Structured observation"):
        audit_observation({"screenshot": b"x", "ui_tree": "secret"}, ARM_REGISTRY["NS-PX-UIV4"])
    audit_observation({"screenshot": b"x", "ui_elements": []}, ARM_REGISTRY["CB-ST-M3A"])


# 7. action-budget ceiling
def test_07_action_budget_ceiling() -> None:
    seen = []
    bridge = BudgetedAndroidWorldAdapter(seen.append, 1)
    bridge.execute({"action": "back"})
    with pytest.raises(ActionBudgetExceeded):
        bridge.execute({"action": "home"})
    assert seen == [{"action": "back"}]


# 8. model-call ceiling
def test_08_model_call_ceiling() -> None:
    budget = UsageBudget(1)
    for _ in range(4):
        budget.add_call(0, 0)
    with pytest.raises(BudgetExceeded, match="model_call"):
        budget.add_call(0, 0)


# 9. token ceiling
def test_09_token_ceiling() -> None:
    with pytest.raises(BudgetExceeded, match="input_token"):
        UsageBudget(1).add_call(20_001, 0)
    with pytest.raises(BudgetExceeded, match="output_token"):
        UsageBudget(1).add_call(0, 2_049)


# 10. wall-clock ceiling
def test_10_wall_clock_formula() -> None:
    assert CellLimits(16).wall_seconds == 1800
    assert CellLimits(120).wall_seconds == 7200


# 11. reset/teardown lifecycle
def test_11_reset_lifecycle() -> None:
    guard = ResetGuard()
    for event in LIFECYCLE:
        guard.mark(event)
    assert guard.complete
    with pytest.raises(RuntimeError):
        ResetGuard().mark("initialized")


# 12. task-parameter hash equality across arms
def test_12_task_parameter_hash_equality() -> None:
    validate_task_hash_equality([{"arm_id": "a", "task_id": "H01", "task_seed": "1", "task_params_hash": "x"}, {"arm_id": "b", "task_id": "H01", "task_seed": "1", "task_params_hash": "x"}])
    with pytest.raises(RuntimeError):
        validate_task_hash_equality([{"arm_id": "a", "task_id": "H01", "task_seed": "1", "task_params_hash": "x"}, {"arm_id": "b", "task_id": "H01", "task_seed": "1", "task_params_hash": "y"}])


# 13. prompt/model/runtime hash freeze
def test_13_hash_freeze() -> None:
    guard = HashFreezeGuard({"prompt": "a", "model": "b", "runtime": "c"})
    guard.verify({"prompt": "a", "model": "b", "runtime": "c"})
    with pytest.raises(RuntimeError, match="drift"):
        guard.verify({"prompt": "a", "model": "b", "runtime": "changed"})


# 14. protected-file hash guard
def test_14_protected_hash_guard() -> None:
    config = json.loads((PROJECT_ROOT / "configs/experiments/multi_framework_hard_benchmark_v0_2.json").read_text(encoding="utf-8"))
    actual = verify_protected(REPO_ROOT, config["protected_paths"])
    assert set(actual) == set(config["protected_paths"])


# 15. rerun linkage
def test_15_rerun_linkage() -> None:
    validate_rerun("a1", "INFRA_INVALID", "a1", 0)
    with pytest.raises(RuntimeError):
        validate_rerun("a1", "VALID_TASK_FAILURE", "a1", 0)
    with pytest.raises(RuntimeError):
        validate_rerun("a1", "INFRA_INVALID", None, 0)


# 16. required-log-field completeness
def test_16_event_schema_completeness() -> None:
    event = event_fixture()
    validate_event(event)
    schema = json.loads((PROJECT_ROOT / "configs/schemas/multi_framework_event_v0_2.schema.json").read_text(encoding="utf-8"))
    validate(event, schema)
    event.pop("prompt_hash")
    with pytest.raises(ValueError, match="Missing"):
        validate_event(event)


# 17. exact/semantic loop detector fixtures
def test_17_loop_detector() -> None:
    actions = [{"action": "tap", "x": 10, "y": 10}] * 3 + [{"action": "back"}]
    assert maximum_run(actions) == 3
    assert maximum_run([{"action": "tap", "x": 10, "y": 10}, {"action": "tap", "x": 20, "y": 20}], semantic=True) == 2


# 18. no-effect screenshot fixtures
def test_18_no_effect_screenshot() -> None:
    assert pixel_effect_class(b"same", b"same", b"same") == "STRICT_NO_EFFECT"
    assert pixel_effect_class(b"a", b"b", b"a") == "TRANSIENT_EFFECT"


# 19. step multiplier exactly 1.0
def test_19_step_multiplier() -> None:
    assert ActionBudget(1, step_multiplier=1.0).step_multiplier == 1.0
    with pytest.raises(ValueError, match="exactly 1.0"):
        ActionBudget(1, step_multiplier=1.2)


# 20. old frozen output paths are read-only
def test_20_frozen_outputs_rejected(tmp_path: Path) -> None:
    new_root = tmp_path / "new"
    assert_output_root_is_new(new_root, (REPO_ROOT / "runs/frozen_hard_v1", PROJECT_ROOT / "artifacts/role_binding_timing"))
    with pytest.raises(RuntimeError, match="overlaps frozen"):
        assert_output_root_is_new(REPO_ROOT / "runs/frozen_hard_v1/new", (REPO_ROOT / "runs/frozen_hard_v1",))


def test_capability_schema_and_conjunction() -> None:
    value = {"schema_version": "multi_framework_capability.v0.2", "arm_id": "CB-PX-B3", "source_commit": "a" * 40, "checkpoint_revision": "b" * 40, "external_family": None, "observation_privileges": ["screenshot"], "gates": {name: True for name in S0_GATES}, "qualified": True}
    validate_capability(value)
    schema = json.loads((PROJECT_ROOT / "configs/schemas/multi_framework_capability_v0_2.schema.json").read_text(encoding="utf-8"))
    validate(value, schema)
