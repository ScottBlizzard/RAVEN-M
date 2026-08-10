#!/usr/bin/env python3
"""No-generation staging qualification for A6/A7/A8."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np


STAGING_ROOT = Path(__file__).resolve().parents[2]
STAGED_SOURCE = STAGING_ROOT / "implementation" / "src"
sys.path.insert(0, str(STAGED_SOURCE))

from raven_m.official_qwen_mobile.a678_contract import (  # noqa: E402
    A0_PRESERVATION_TASKS,
    A678_CONFIGS,
    A678_MECHANISMS,
    GENERATION_SEED,
    MODEL_ID,
    MODEL_REVISION,
    OFFICIAL_SYSTEM_PROMPT_SHA256,
    TASK_COUNT,
    TASK_SEED,
    current_source_freeze,
    json_sha256,
)
from raven_m.official_qwen_mobile.a678_memory import (  # noqa: E402
    ExactVisualRevisitActionOutcomeCache,
    GoalItemStatusLedger,
    ShortTransitionEpisodicBuffer,
)


FROZEN_DEPENDENCIES = (
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/official_qwen_mobile/protocol.py",
    "implementation/src/raven_m/models/vllm_client.py",
    "implementation/src/raven_m/env/androidworld_adapter.py",
    "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    "implementation/configs/androidworld_hard_v2_instances.json",
)


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _check_configs(errors: list[str], checks: dict[str, Any]) -> None:
    hashes: dict[str, str] = {}
    for arm, relative in A678_CONFIGS.items():
        path = STAGING_ROOT / relative
        config = _load(path)
        hashes[arm] = _sha(path)
        if config.get("schema") != "a678_memory_arm_v1":
            errors.append(f"{arm}_schema_drift")
        if config.get("arm") != arm or config.get("mechanism_id") != A678_MECHANISMS[arm]:
            errors.append(f"{arm}_identity_drift")
        model = config.get("model") or {}
        if model.get("id") != MODEL_ID or model.get("revision") != MODEL_REVISION:
            errors.append(f"{arm}_model_drift")
        if model.get("generation_seed") != GENERATION_SEED:
            errors.append(f"{arm}_generation_seed_drift")
        benchmark = config.get("benchmark") or {}
        if benchmark.get("task_seed") != TASK_SEED or benchmark.get("task_count") != TASK_COUNT:
            errors.append(f"{arm}_benchmark_drift")
        if not str(benchmark.get("order") or "").startswith("original frozen manifest order"):
            errors.append(f"{arm}_order_drift")
        intervention = config.get("intervention") or {}
        expected = {
            "writer": "controller deterministic",
            "response_prefix_required": False,
            "system_prompt": "exact OFFICIAL_SYSTEM_PROMPT",
            "extra_model_calls": 0,
            "guard": False,
            "action_override": False,
            "evaluator_input": False,
            "hidden_ui_input": False,
        }
        for key, value in expected.items():
            if intervention.get(key) != value:
                errors.append(f"{arm}_{key}_drift")
        stopping = config.get("stopping") or {}
        if stopping.get("full_19_required") is not True or stopping.get("reward_fail_fast") is not False:
            errors.append(f"{arm}_stopping_drift")
        if tuple(stopping.get("A0_preservation_tasks_nonblocking") or []) != A0_PRESERVATION_TASKS:
            errors.append(f"{arm}_preservation_monitor_drift")
    checks["config_sha256"] = hashes


def _check_frozen_repo(repo: Path, errors: list[str], checks: dict[str, Any]) -> None:
    missing = [relative for relative in FROZEN_DEPENDENCIES if not (repo / relative).is_file()]
    if missing:
        errors.append(f"frozen_dependency_missing:{missing}")
        return
    manifest = _load(repo / "implementation/configs/androidworld_hard_v2_instances.json")
    instances = [row for row in manifest.get("instances") or [] if row.get("task_seed") == TASK_SEED]
    if len(instances) != TASK_COUNT or len({row.get("task_class") for row in instances}) != TASK_COUNT:
        errors.append("hard_manifest_seed_not_19_unique")
    if any(not all(row.get(key) for key in ("task_params_hash", "goal_hash", "native_max_steps")) for row in instances):
        errors.append("hard_manifest_binding_incomplete")

    protocol_path = repo / "implementation/src/raven_m/official_qwen_mobile/protocol.py"
    specification = importlib.util.spec_from_file_location("a678_frozen_protocol", protocol_path)
    if specification is None or specification.loader is None:
        errors.append("official_protocol_import_spec_failed")
    else:
        module = importlib.util.module_from_spec(specification)
        sys.modules[specification.name] = module
        specification.loader.exec_module(module)
        observed = sha256(module.OFFICIAL_SYSTEM_PROMPT.encode("utf-8")).hexdigest()
        checks["official_system_prompt_sha256"] = observed
        if observed != OFFICIAL_SYSTEM_PROMPT_SHA256:
            errors.append("official_system_prompt_hash_drift")

    controller = (repo / "implementation/src/raven_m/official_qwen_mobile/controller.py").read_text(
        encoding="utf-8"
    )
    required_anchors = (
        'context={"before": before, "goal": effective_goal}',
        'hasattr(self.working_memory, "observe_step")',
        "canonical_action=canonical_action",
        "transition=transition",
        "before=before",
        "after=after",
    )
    for anchor in required_anchors:
        if anchor not in controller:
            errors.append(f"controller_interface_anchor_missing:{anchor}")
    checks["frozen_dependency_sha256"] = {
        relative: _sha(repo / relative) for relative in FROZEN_DEPENDENCIES
    }


def _canaries(errors: list[str], checks: dict[str, Any]) -> None:
    try:
        pixels = np.zeros((100, 80, 3), dtype=np.uint8)
        pixels[:, 40:] = 255
        kwargs = {
            "source_step": 0,
            "action_summary": "Tap Bike Repairs and confirm deletion.",
            "canonical_action": {"type": "tap", "x": 0.4, "y": 0.6},
            "transition": {"exactly_unchanged": False, "changed_pixel_fraction_gt_5": 0.5},
            "before": {"pixels": pixels, "evaluator_reward": 1.0, "ui_tree": "hidden"},
            "after": {"pixels": 255 - pixels, "evaluator_reward": 0.0},
            "source_screenshot_sha256": "a" * 64,
            "source_response_sha256": "b" * 64,
        }
        a6 = ShortTransitionEpisodicBuffer()
        assert a6.read()[0] == ""
        assert a6.observe_step(**kwargs)["written"]
        assert a6.read()[1]["nonempty"]

        a7 = GoalItemStatusLedger()
        goal = "Delete the following expenses: Bike Repairs, Tuition Fees, Public Transit."
        assert a7.read({"goal": goal})[0] == ""
        assert a7.observe_step(**kwargs)["written"]
        rendered7, audit7 = a7.read({"goal": goal})
        assert audit7["nonempty"] and "complete" not in rendered7.casefold()

        a8 = ExactVisualRevisitActionOutcomeCache()
        assert a8.read({"before": {"pixels": pixels}})[0] == ""
        assert a8.observe_step(**kwargs)["written"]
        assert a8.read({"before": {"pixels": pixels, "evaluator_reward": 999}})[1]["nonempty"]
        for memory in (a6, a7, a8):
            audit = memory.audit_record()
            assert audit["model_calls_added"] == 0
            assert audit["evaluator_used_for_decision"] is False
            assert audit["hidden_ui_used_for_decision"] is False
            assert audit["guard_enabled"] is False
            assert audit["action_override_count"] == 0
        checks["memory_canaries"] = "pass"
    except Exception as exc:
        errors.append(f"memory_canary_failed:{type(exc).__name__}:{exc}")


def _run_tests(errors: list[str], checks: dict[str, Any]) -> None:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = str(STAGING_ROOT / "implementation/src")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "implementation/tests/official_qwen_mobile/test_a678_memory.py",
            "implementation/tests/official_qwen_mobile/test_a678_contract.py",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=STAGING_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    checks["tests"] = {
        "returncode": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-2000:],
    }
    if result.returncode != 0:
        errors.append("staging_unit_tests_failed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--frozen-repo",
        type=Path,
        default=STAGING_ROOT,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=STAGING_ROOT / "evidence/a678/A678_ZERO_GENERATION_PREFLIGHT.json",
    )
    args = parser.parse_args()
    errors: list[str] = []
    checks: dict[str, Any] = {}
    _check_configs(errors, checks)
    _check_frozen_repo(args.frozen_repo.resolve(), errors, checks)
    _canaries(errors, checks)
    _run_tests(errors, checks)

    try:
        staged_freeze = current_source_freeze()
    except Exception as exc:
        errors.append(f"source_closure_failed:{type(exc).__name__}:{exc}")
        staged_freeze = {}
    report = {
        "schema": "a678_zero_generation_preflight_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "qualification_scope": "repository_static_zero_generation_ready_for_live_receipt",
        "status": "pass" if not errors else "fail",
        "generation_calls": 0,
        "errors": errors,
        "checks": checks,
        "source_freeze": staged_freeze,
        "source_freeze_sha256": json_sha256(staged_freeze) if staged_freeze else None,
    }
    _atomic_json(args.output.resolve(), report)
    print(json.dumps(report, indent=2, ensure_ascii=True, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
