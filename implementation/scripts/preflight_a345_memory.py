#!/usr/bin/env python3
"""Zero-generation, fail-closed qualification for A3/A4/A5.

This script never imports a model client, opens AndroidWorld, or calls a
generation endpoint.  It validates the frozen comparison, public source
locks, donor-bank provenance, deterministic memory canaries, source closure,
and unit tests, then writes one machine-readable qualification report.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.official_qwen_mobile.a345_contract import (  # noqa: E402
    A345_GATE_TASKS,
    A345_REQUIRED_GATE_TASKS,
    A345_PREFLIGHT_REPORT,
    A345_REFERENCE_LEDGER,
    A4_WORKFLOW_BANK,
    MODEL_ID,
    current_source_freeze,
    file_sha256,
    source_freeze_sha256,
)
from raven_m.official_qwen_mobile.a345_memory import (  # noqa: E402
    FrozenWorkflowMemory,
    OnlinePageGraphMemory,
    ProactiveFoldedContextMemory,
)


CONFIGS = {
    "a3": REPOSITORY_ROOT / "implementation/configs/a3_conact_hard_seed20260806.json",
    "a4": REPOSITORY_ROOT / "implementation/configs/a4_awm_workflow_hard_seed20260806.json",
    "a5": REPOSITORY_ROOT / "implementation/configs/a5_visual_graph_hard_seed20260806.json",
}
MANIFEST = REPOSITORY_ROOT / "implementation/configs/androidworld_hard_v2_instances.json"
UPSTREAMS = {
    "a3": (
        REPOSITORY_ROOT / "references/public_memory_upstreams/MemGUI-Agent",
        "321734eaf9788c6a802f8f11e62651702d14af28",
    ),
    "a4": (
        REPOSITORY_ROOT / "references/public_memory_upstreams/agent-workflow-memory",
        "8c0ff8cd11d648c8fceb99e4e42f37e3b75381b1",
    ),
    "a5": (
        REPOSITORY_ROOT / "references/public_memory_upstreams/HyMEM-GUI-Agent",
        "911722c99c8c3fa0052cbb1f596e13d691610ed5",
    ),
}
EXPECTED_MECHANISMS = {
    "a3": "a3_memgui_conact_folded_context_v1",
    "a4": "a4_awm_frozen_donor_workflow_memory_v1",
    "a5": "a5_hymem_online_visual_symbolic_graph_v1",
}
EXPECTED_MODEL = {
    "id": MODEL_ID,
    "revision": "0cfaf48183f594c314753d30a4c4974bc75f3ccb",
    "generation_seed": 3407,
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 20,
    "presence_penalty": 1.5,
    "repetition_penalty": 1.0,
    "max_tokens": 32768,
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _check_configs(errors: list[str], checks: dict[str, Any]) -> None:
    configs: dict[str, dict[str, Any]] = {}
    for arm, path in CONFIGS.items():
        try:
            configs[arm] = _load(path)
        except Exception as exc:
            errors.append(f"{arm}_config_unreadable:{type(exc).__name__}:{exc}")
    if len(configs) != 3:
        return
    for arm, config in configs.items():
        if config.get("mechanism_id") != EXPECTED_MECHANISMS[arm]:
            errors.append(f"{arm}_mechanism_id_drift")
        if config.get("model") != EXPECTED_MODEL:
            errors.append(f"{arm}_model_or_sampling_drift")
        benchmark = config.get("benchmark") or {}
        if benchmark.get("task_seed") != 20260806 or benchmark.get("task_count") != 19:
            errors.append(f"{arm}_task_seed_or_count_drift")
        if tuple(benchmark.get("qualification_first") or []) != A345_GATE_TASKS:
            errors.append(f"{arm}_gate_order_drift")
        intervention = config.get("intervention") or {}
        if intervention.get("guard") is not False or intervention.get("extra_planner") is not False:
            errors.append(f"{arm}_non_memory_intervention_enabled")
        extra_calls = intervention.get(
            "extra_model_calls_during_scored_suite",
            intervention.get("extra_model_calls"),
        )
        if extra_calls != 0:
            errors.append(f"{arm}_extra_model_calls_not_zero")
    checks["config_sha256"] = {arm: file_sha256(path) for arm, path in CONFIGS.items()}


def _check_manifest_and_ledger(errors: list[str], checks: dict[str, Any]) -> set[str]:
    manifest = _load(MANIFEST)
    instances = [row for row in manifest.get("instances") or [] if row.get("task_seed") == 20260806]
    names = [str(row.get("task_class")) for row in instances]
    if len(instances) != 19 or len(set(names)) != 19:
        errors.append("manifest_seed20260806_not_19_unique")
    missing_fields = [
        row.get("task_class")
        for row in instances
        if not all(row.get(key) for key in ("task_params_hash", "goal_hash", "native_max_steps"))
    ]
    if missing_fields:
        errors.append(f"manifest_instance_binding_incomplete:{missing_fields}")
    if any(name not in names for name in A345_GATE_TASKS):
        errors.append("manifest_gate_task_missing")

    ledger = _load(A345_REFERENCE_LEDGER)
    rows = list(ledger.get("tasks") or [])
    if ledger.get("schema") != "a345_a0_a1_a2_frozen_reference_v1":
        errors.append("reference_ledger_schema_drift")
    if ledger.get("seed") != 20260806 or len(rows) != 19:
        errors.append("reference_ledger_seed_or_count_drift")
    if tuple(ledger.get("gate_tasks") or []) != A345_GATE_TASKS:
        errors.append("reference_ledger_gate_drift")
    ledger_names = {str(row.get("task_name")) for row in rows}
    if ledger_names != set(names):
        errors.append("reference_ledger_manifest_task_mismatch")
    success_sets = {
        arm: {str(row.get("task_name")) for row in rows if bool((row.get(arm) or {}).get("success"))}
        for arm in ("A0", "A1", "A2")
    }
    if success_sets["A1"] != set(A345_GATE_TASKS):
        errors.append("a1_success_set_not_exact_gate")
    if success_sets["A0"] != set(A345_REQUIRED_GATE_TASKS) or success_sets["A2"]:
        errors.append("frozen_reference_success_counts_drift")
    checks["manifest_sha256"] = file_sha256(MANIFEST)
    checks["reference_ledger_sha256"] = file_sha256(A345_REFERENCE_LEDGER)
    checks["reference_success_sets"] = {key: sorted(value) for key, value in success_sets.items()}
    return ledger_names


def _check_upstreams(errors: list[str], checks: dict[str, Any]) -> None:
    observed: dict[str, str] = {}
    for arm, (path, expected) in UPSTREAMS.items():
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        commit = result.stdout.strip()
        observed[arm] = commit
        if result.returncode != 0 or commit != expected:
            errors.append(f"{arm}_public_upstream_commit_drift")
    checks["public_upstream_commits"] = observed


def _check_workflow_bank(errors: list[str], checks: dict[str, Any], scored_tasks: set[str]) -> None:
    if not A4_WORKFLOW_BANK.is_file():
        errors.append("a4_frozen_donor_workflow_bank_missing")
        return
    payload = _load(A4_WORKFLOW_BANK)
    if not isinstance(payload, dict):
        errors.append("a4_workflow_bank_top_level_must_be_object")
        return
    if payload.get("schema") != "a4.frozen_donor_workflow_bank.v1" or payload.get("status") != "ready":
        errors.append("a4_workflow_bank_schema_or_status_invalid")
        return
    if payload.get("generation_calls") != 0 or payload.get("scored_hard_inputs_used") is not False:
        errors.append("a4_workflow_bank_provenance_invalid")
        return
    workflows = payload.get("workflows")
    if not isinstance(workflows, list):
        errors.append("a4_workflows_must_be_list")
        return
    workflow_sha = sha256(json.dumps(workflows, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    if payload.get("bank_sha256") != workflow_sha:
        errors.append("a4_workflow_payload_hash_drift")
    if not workflows:
        errors.append("a4_workflow_bank_empty")
        return
    ids: list[str] = []
    sha_pattern = re.compile(r"^[0-9a-f]{64}$")
    for index, record in enumerate(workflows):
        ids.append(str(record.get("workflow_id") or ""))
        required = (
            "workflow_id", "donor_task", "donor_seed", "donor_family", "provenance",
            "keywords", "workflow", "source_episode_sha256", "source_evaluator_reward",
        )
        if any(record.get(key) in (None, "", []) for key in required):
            errors.append(f"a4_workflow_{index}_provenance_incomplete")
            continue
        donor_split = str((record.get("provenance") or {}).get("difficulty") or "").lower()
        if donor_split not in ("easy", "medium"):
            errors.append(f"a4_workflow_{index}_donor_split_invalid")
        if str(record.get("donor_task")) in scored_tasks:
            errors.append(f"a4_workflow_{index}_scored_hard_task_leakage")
        if float(record.get("source_evaluator_reward")) != 1.0:
            errors.append(f"a4_workflow_{index}_donor_not_successful")
        if not sha_pattern.fullmatch(str(record.get("source_episode_sha256"))):
            errors.append(f"a4_workflow_{index}_episode_hash_invalid")
    if len(set(ids)) != len(ids):
        errors.append("a4_workflow_ids_not_unique")
    try:
        FrozenWorkflowMemory(bank=workflows)
    except Exception as exc:
        errors.append(f"a4_workflow_runtime_rejected:{type(exc).__name__}:{exc}")
    checks["a4_workflow_bank_sha256"] = file_sha256(A4_WORKFLOW_BANK)
    checks["a4_workflow_count"] = len(workflows)


def _memory_canaries(errors: list[str], checks: dict[str, Any]) -> None:
    try:
        a3 = ProactiveFoldedContextMemory()
        action = "CONTEXT[folded_history=open;ui_state=form;recent=typed] | tap save"
        a3.record_protocol(action)
        assert a3.observe_step(action_summary=action, source_step=0, transition={})["written"]
        assert a3.read()[1]["nonempty"]

        donor = [{
            "workflow_id": "canary",
            "donor_task": "IndependentEasyDonor",
            "donor_seed": 1,
            "donor_family": "calendar event",
            "keywords": ["calendar", "event"],
            "workflow": "open add form, fill fields, save, verify",
            "source_episode_sha256": "a" * 64,
            "source_evaluator_reward": 1.0,
        }]
        a4 = FrozenWorkflowMemory(bank=donor)
        assert a4.read({"goal": "create calendar event"})[1]["nonempty"]

        pixels = np.zeros((100, 80, 3), dtype=np.uint8)
        pixels[:, 40:] = 255
        a5 = OnlinePageGraphMemory(max_hamming=0)
        graph = "GRAPH[node=form;relation=save;facts=filled;avoid=repeat] | tap save"
        a5.record_protocol(graph)
        assert a5.observe_step(
            action_summary=graph,
            source_step=0,
            before={"pixels": pixels, "hidden": "ignored"},
            after={"pixels": 255 - pixels, "evaluator": 1},
            canonical_action={"type": "tap"},
            transition={},
        )["written"]
        assert a5.read({"before": {"pixels": pixels, "different_hidden": True}})[1]["nonempty"]
        for memory in (a3, a4, a5):
            audit = memory.audit_record()
            assert audit["model_calls_added"] == 0
        checks["memory_canaries"] = "pass"
    except Exception as exc:
        errors.append(f"memory_canary_failed:{type(exc).__name__}:{exc}")


def _run_tests(errors: list[str], checks: dict[str, Any]) -> None:
    paths = [
        "implementation/tests/official_qwen_mobile/test_a345_memory.py",
        "implementation/tests/official_qwen_mobile/test_a345_runner_contract.py",
        "implementation/tests/official_qwen_mobile/test_a4_donor.py",
    ]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *paths, "-q", "-p", "no:cacheprovider"],
        cwd=REPOSITORY_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    checks["unit_tests"] = {
        "command": [sys.executable, "-m", "pytest", *paths],
        "returncode": result.returncode,
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-2000:],
    }
    if result.returncode != 0:
        errors.append("a345_unit_tests_failed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=A345_PREFLIGHT_REPORT)
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    checks: dict[str, Any] = {}
    try:
        _check_configs(errors, checks)
        scored_tasks = _check_manifest_and_ledger(errors, checks)
        _check_upstreams(errors, checks)
        _check_workflow_bank(errors, checks, scored_tasks)
        _memory_canaries(errors, checks)
        if not args.skip_tests:
            _run_tests(errors, checks)
        freeze = current_source_freeze()
    except Exception as exc:
        errors.append(f"preflight_exception:{type(exc).__name__}:{exc}")
        freeze = {}

    report = {
        "schema": "a345_zero_generation_preflight_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not errors else "fail",
        "generation_calls": 0,
        "qualified_arms": ["a3", "a4", "a5"] if not errors else [],
        "errors": errors,
        "checks": checks,
        "source_freeze": freeze,
        "source_freeze_sha256": source_freeze_sha256(freeze) if freeze else None,
    }
    _atomic_json(args.output.resolve(), report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
