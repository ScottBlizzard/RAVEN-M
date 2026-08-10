"""Frozen qualification contract shared by A3/A4/A5."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
IMPLEMENTATION_ROOT = REPOSITORY_ROOT / "implementation"
A345_PREFLIGHT_REPORT = REPOSITORY_ROOT / "evidence" / "a345" / "A345_ZERO_GENERATION_PREFLIGHT.json"
A345_REFERENCE_LEDGER = REPOSITORY_ROOT / "evidence" / "a345" / "A0_A1_A2_FROZEN_REFERENCE_LEDGER.json"
A4_WORKFLOW_BANK = REPOSITORY_ROOT / "evidence" / "a345" / "A4_FROZEN_DONOR_WORKFLOW_BANK.json"
MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REALPATH = "/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope"
MODEL_MANIFEST_SHA256 = "18e0909c7d993853d6d0f62443461a74009754f90db026a1723cab80121c7872"

A345_GATE_TASKS = (
    "ExpenseDeleteMultiple2",
    "RecipeDeleteMultipleRecipesWithConstraint",
    "RetroSavePlaylist",
    "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
)
A345_TERMINAL_CHECKPOINT_STATUSES = frozenset(
    {"stopped_capability_gate_failure", "stopped_memory_activation_failure"}
)

SOURCE_FILES = (
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/preflight_a345_memory.py",
    "implementation/scripts/build_a345_reference_ledger.py",
    "implementation/scripts/build_a4_donor_bank.py",
    "implementation/src/raven_m/__init__.py",
    "implementation/src/raven_m/env/__init__.py",
    "implementation/src/raven_m/env/androidworld_adapter.py",
    "implementation/src/raven_m/models/__init__.py",
    "implementation/src/raven_m/models/transformers_client.py",
    "implementation/src/raven_m/models/vllm_client.py",
    "implementation/src/raven_m/multi_framework_benchmark/__init__.py",
    "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    "implementation/src/raven_m/official_qwen_mobile/__init__.py",
    "implementation/src/raven_m/official_qwen_mobile/a345_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/a345_memory.py",
    "implementation/src/raven_m/official_qwen_mobile/a4_donor.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/official_qwen_mobile/protocol.py",
    "implementation/src/raven_m/official_qwen_mobile/working_memory.py",
    "implementation/src/raven_m/official_qwen_mobile/progress_memory.py",
    "implementation/configs/a3_conact_hard_seed20260806.json",
    "implementation/configs/a4_awm_workflow_hard_seed20260806.json",
    "implementation/configs/a4_awm_donor_manifest_v1.json",
    "implementation/configs/a5_visual_graph_hard_seed20260806.json",
    "implementation/configs/androidworld_hard_v2_instances.json",
    "implementation/tests/official_qwen_mobile/test_a345_memory.py",
    "implementation/tests/official_qwen_mobile/test_a345_runner_contract.py",
    "implementation/tests/official_qwen_mobile/test_a4_donor.py",
    "protocols/A345_PUBLIC_MEMORY_KERNELS_PREREG_2026-08-11.md",
    "protocols/A345_RUNBOOK.md",
    "protocols/A4_AWM_DONOR_ACQUISITION_RUNBOOK.md",
)


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def current_source_freeze() -> dict[str, str]:
    missing = [name for name in SOURCE_FILES if not (REPOSITORY_ROOT / name).is_file()]
    if missing:
        raise RuntimeError(f"A3/A4/A5 source closure is incomplete: {missing}")
    return {name: file_sha256(REPOSITORY_ROOT / name) for name in SOURCE_FILES}


def source_freeze_sha256(freeze: dict[str, str]) -> str:
    return sha256(
        json.dumps(freeze, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def validate_preflight_report(path: Path = A345_PREFLIGHT_REPORT) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    current = current_source_freeze()
    errors: list[str] = []
    if report.get("status") != "pass":
        errors.append("status_not_pass")
    if report.get("generation_calls") != 0:
        errors.append("generation_calls_not_zero")
    if report.get("errors"):
        errors.append("preflight_errors_nonempty")
    if sorted(report.get("qualified_arms") or []) != ["a3", "a4", "a5"]:
        errors.append("qualified_arms_drift")
    if report.get("source_freeze") != current:
        errors.append("source_freeze_drift")
    if report.get("source_freeze_sha256") != source_freeze_sha256(current):
        errors.append("source_freeze_digest_drift")
    expected_bank_sha = (report.get("checks") or {}).get("a4_workflow_bank_sha256")
    if not A4_WORKFLOW_BANK.is_file():
        errors.append("a4_workflow_bank_missing")
    elif expected_bank_sha != file_sha256(A4_WORKFLOW_BANK):
        errors.append("a4_workflow_bank_drift")
    if errors:
        raise RuntimeError(f"A3/A4/A5 preflight validation failed: {errors}")
    return report


def activation_valid(summary: dict[str, Any], arm: str) -> bool:
    """Prove that memory reached a scored model request, without task reward."""
    steps = list(summary.get("steps") or [])
    if arm == "a4":
        return any(bool((step.get("memory_read") or {}).get("nonempty")) for step in steps)
    first_write: int | None = None
    for index, step in enumerate(steps):
        if bool((step.get("memory_write") or {}).get("written")):
            first_write = index
            break
    return first_write is not None and any(
        index > first_write and bool((step.get("memory_read") or {}).get("nonempty"))
        for index, step in enumerate(steps)
    )


def validate_launch_receipt(
    path: Path, *, preflight_path: Path = A345_PREFLIGHT_REPORT
) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    expected = {"status": "pass", "generation_calls": 0, "served_model_id": MODEL_ID,
                "model_realpath": MODEL_REALPATH, "model_manifest_sha256": MODEL_MANIFEST_SHA256,
                "port": 18000}
    errors = [f"{key}_drift" for key, value in expected.items() if receipt.get(key) != value]
    cmdline = [str(item) for item in receipt.get("process_cmdline") or []]
    if MODEL_REALPATH not in cmdline or MODEL_ID not in cmdline:
        errors.append("process_cmdline_model_binding_missing")
    packages = receipt.get("packages") or {}
    if not all(str(packages.get(name) or "") for name in ("vllm", "torch", "transformers")):
        errors.append("runtime_packages_missing")
    if receipt.get("a345_preflight_sha256") != file_sha256(preflight_path):
        errors.append("preflight_receipt_binding_drift")
    if errors:
        raise RuntimeError(f"A3/A4/A5 live launch receipt invalid: {errors}")
    return receipt
