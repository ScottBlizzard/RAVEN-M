"""Frozen source contract shared by the A1 preflight and scored runner."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
A1_PREFLIGHT_REPORT = (
    REPOSITORY_ROOT / "evidence/a1/A1_ZERO_GENERATION_PREFLIGHT.json"
)
A1_CONFIG = (
    REPOSITORY_ROOT
    / "implementation/configs/a1_action_working_memory_hard_seed20260806.json"
)
A1_MANIFEST = (
    REPOSITORY_ROOT / "implementation/configs/androidworld_hard_v2_instances.json"
)

A1_FREEZE_FILES = (
    "implementation/configs/a1_action_working_memory_hard_seed20260806.json",
    "implementation/configs/androidworld_hard_v2_instances.json",
    "implementation/runtime/androidworld_compat.py",
    "implementation/scripts/preflight_a1_working_memory.py",
    "implementation/scripts/run_a1_working_memory.ps1",
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/start_official_qwen_server.sh",
    "implementation/src/raven_m/env/androidworld_adapter.py",
    "implementation/src/raven_m/models/vllm_client.py",
    "implementation/src/raven_m/multi_framework_benchmark/__init__.py",
    "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    "implementation/src/raven_m/official_qwen_mobile/a1_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/official_qwen_mobile/protocol.py",
    "implementation/src/raven_m/official_qwen_mobile/working_memory.py",
    "implementation/tests/models/test_vllm_client.py",
    "implementation/tests/official_qwen_mobile/test_official_qwen_controller.py",
    "implementation/tests/official_qwen_mobile/test_protocol.py",
    "implementation/tests/official_qwen_mobile/test_working_memory.py",
    "protocols/A1_ACTION_WORKING_MEMORY_PREREG_2026-08-10.md",
    "protocols/A1_ACTION_WORKING_MEMORY_RUNBOOK.md",
)


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def current_source_freeze(
    repository_root: Path = REPOSITORY_ROOT,
) -> dict[str, str]:
    missing = [name for name in A1_FREEZE_FILES if not (repository_root / name).is_file()]
    if missing:
        raise RuntimeError(f"A1 freeze files missing: {missing}")
    return {
        name: file_sha256(repository_root / name)
        for name in A1_FREEZE_FILES
    }


def validate_preflight_report(path: Path = A1_PREFLIGHT_REPORT) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"A1 zero-generation preflight report is missing: {path}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("status") != "pass":
        raise RuntimeError("A1 zero-generation preflight did not pass")
    if int(report.get("generation_calls", -1)) != 0:
        raise RuntimeError("A1 preflight unexpectedly used model generation")
    if report.get("errors") != []:
        raise RuntimeError(f"A1 preflight contains errors: {report.get('errors')!r}")
    current = current_source_freeze()
    if report.get("source_freeze") != current:
        raise RuntimeError("A1 source freeze drifted after zero-generation preflight")
    return report
