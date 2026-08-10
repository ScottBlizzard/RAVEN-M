from __future__ import annotations

import json
from pathlib import Path

from raven_m.official_qwen_mobile.a678_contract import (
    A0_PRESERVATION_TASKS,
    A678_CONFIGS,
    A678_MECHANISMS,
    GENERATION_SEED,
    MODEL_ID,
    MODEL_REVISION,
    TASK_COUNT,
    TASK_SEED,
    exact_completion_errors,
    preservation_report,
)


STAGING_ROOT = Path(__file__).resolve().parents[3]


def test_configs_freeze_only_memory_side_interventions() -> None:
    for arm, relative_path in A678_CONFIGS.items():
        config = json.loads((STAGING_ROOT / relative_path).read_text(encoding="utf-8"))
        assert config["arm"] == arm
        assert config["mechanism_id"] == A678_MECHANISMS[arm]
        assert config["model"]["id"] == MODEL_ID
        assert config["model"]["revision"] == MODEL_REVISION
        assert config["model"]["generation_seed"] == GENERATION_SEED
        assert config["benchmark"]["task_seed"] == TASK_SEED
        assert config["benchmark"]["task_count"] == TASK_COUNT
        assert config["benchmark"]["order"].startswith("original frozen manifest order")
        assert config["intervention"]["writer"] == "controller deterministic"
        assert config["intervention"]["response_prefix_required"] is False
        assert config["intervention"]["system_prompt"] == "exact OFFICIAL_SYSTEM_PROMPT"
        assert config["intervention"]["extra_model_calls"] == 0
        assert config["intervention"]["guard"] is False
        assert config["intervention"]["action_override"] is False
        assert config["intervention"]["evaluator_input"] is False
        assert config["intervention"]["hidden_ui_input"] is False
        assert config["stopping"]["full_19_required"] is True
        assert config["stopping"]["reward_fail_fast"] is False
        assert tuple(config["stopping"]["A0_preservation_tasks_nonblocking"]) == A0_PRESERVATION_TASKS


def _summary(task_name: str, seed: int = TASK_SEED, success: bool = False) -> dict:
    return {
        "task_name": task_name,
        "seed": seed,
        "success": success,
        "evaluator_reward": float(success),
        "error": None,
        "lifecycle_errors": [],
        "steps": [{"model_call": {"raven_meta": {"transport_attempts": 1}}}],
    }


def test_exact_completion_accepts_scientific_reward_failures() -> None:
    summaries = [_summary(f"Task{i:02d}") for i in range(TASK_COUNT)]
    expected = [(item["task_name"], TASK_SEED) for item in summaries]
    assert exact_completion_errors(
        summaries=summaries,
        expected_keys=expected,
        invalid_attempts=[],
        lifecycle_errors=[],
    ) == []


def test_exact_completion_rejects_infrastructure_not_task_failure() -> None:
    summaries = [_summary(f"Task{i:02d}") for i in range(TASK_COUNT)]
    summaries[3]["evaluator_reward"] = None
    expected = [(item["task_name"], TASK_SEED) for item in summaries]
    errors = exact_completion_errors(
        summaries=summaries,
        expected_keys=expected,
        invalid_attempts=[],
        lifecycle_errors=[],
    )
    assert "episode_3_infrastructure_invalid" in errors


def test_preservation_monitor_is_nonblocking() -> None:
    summaries = [_summary(name, success=(index % 2 == 0)) for index, name in enumerate(A0_PRESERVATION_TASKS)]
    report = preservation_report(summaries)
    assert report["required_for_suite_continuation"] is False
    assert report["success_count"] == 2


def test_runner_integrates_a678_without_reward_fail_fast_or_prompt_suffix() -> None:
    source = (STAGING_ROOT / "implementation/scripts/run_official_qwen_mobile.py").read_text(
        encoding="utf-8"
    )
    assert '"--a678-arm"' in source
    assert "validate_a678_preflight_report" in source
    assert "validate_a678_launch_receipt" in source
    assert "a678_completion_errors" in source
    assert "a678_preservation_report" in source
    assert "ShortTransitionEpisodicBuffer(capacity=2, max_chars=240)" in source
    assert "GoalItemStatusLedger(" in source
    assert "ExactVisualRevisitActionOutcomeCache(" in source
    assert "args.a2_verified_progress_memory or a345_scored_arm or a678_scored_arm" in source
    assert "if a345_scored_arm and task_name in A345_REQUIRED_GATE_TASKS" in source
    assert "if a678_scored_arm and task_name" not in source
    assert '"reward_fail_fast": False' in source
    assert '"official_system_prompt_unchanged": True' in source


def test_wrapper_is_dry_run_by_default() -> None:
    source = (STAGING_ROOT / "implementation/scripts/run_a678_arm.py").read_text(
        encoding="utf-8"
    )
    assert 'parser.add_argument("--execute", action="store_true")' in source
    assert "if not args.execute:" in source
    assert '"--a678-arm", args.arm' in source
    assert 'REPOSITORY_ROOT / "06_local_runtime/envs/androidworld/Scripts/python.exe"' in source
    assert "str(ANDROIDWORLD_PYTHON)" in source
    assert "sys.executable" not in source


def test_a678_live_qualifier_binds_new_preflight_receipt() -> None:
    source = (
        STAGING_ROOT / "implementation/scripts/qualify_a678_live_server.py"
    ).read_text(encoding="utf-8")
    assert '"schema": "a678_live_server_receipt_v1"' in source
    assert '"a678_preflight_sha256": _hash(args.preflight)' in source
    assert '"generation_calls": 0' in source
    assert 'intent["served_model_id"] not in cmdline' in source
