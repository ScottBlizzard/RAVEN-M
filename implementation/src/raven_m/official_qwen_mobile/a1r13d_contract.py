"""Fail-closed contract for the A1-R13D target-first EVR diagnostic."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Any

from . import a1r13_contract as base


MECHANISM_ID = base.MECHANISM_ID
EXPERIMENT_ID = "A1R13D_EVR_TARGET_FIRST_QWEN3VL32B_AW_HARD_S20260806_G3407_V1"
MODEL_ID = base.MODEL_ID
MODEL_REVISION = base.MODEL_REVISION
MODEL_REALPATH = base.MODEL_REALPATH
MODEL_MANIFEST_SHA256 = base.MODEL_MANIFEST_SHA256
TASK_SEED = base.TASK_SEED
GENERATION_SEED = base.GENERATION_SEED
PORT = base.PORT
PARENT_EVIDENCE_COMMIT = "c3deaf9d2082be92e1e3842d3c4192f3080098f8"
CONFIG_SCHEMA = "a1r13d_evr_target_first_config_v1"
PREFLIGHT_SCHEMA = "a1r13d_evr_target_first_preflight_v1"
LIVE_RECEIPT_SCHEMA = "a1r13d_evr_target_first_receipt_v1"
CHECKPOINT_SCHEMA = "a1r13d_evr_target_first_checkpoint_v1"
RESULT_SCHEMA = "a1r13d_evr_target_first_result_v1"
REPOSITORY_ROOT = base.REPOSITORY_ROOT
CONFIG_PATH = REPOSITORY_ROOT / "implementation/configs/a1r13d_evr_target_first_hard_seed20260806.json"
SOURCE_FREEZE_PATH = REPOSITORY_ROOT / "evidence/a1r13d/A1R13D_EVR_SOURCE_FREEZE.json"
PREFLIGHT_PATH = REPOSITORY_ROOT / "evidence/a1r13d/A1R13D_EVR_ZERO_GENERATION_PREFLIGHT.json"
TARGET_GATE_TASK = base.TARGET_GATE_TASK
CAPABILITY_GATE_TASKS = base.CAPABILITY_GATE_TASKS
_REMAINING = tuple(
    name for name in base.FULL_TASK_ORDER
    if name != TARGET_GATE_TASK and name not in CAPABILITY_GATE_TASKS
)
FULL_TASK_ORDER = (TARGET_GATE_TASK,) + CAPABILITY_GATE_TASKS + _REMAINING

SOURCE_FILES = (
    "protocols/A1R13D_EVR_TARGET_FIRST_DIAGNOSTIC_PREREG_2026-08-18.md",
    "implementation/configs/a1r13d_evr_target_first_hard_seed20260806.json",
    "implementation/configs/androidworld_hard_v2_instances.json",
    "implementation/src/raven_m/official_qwen_mobile/a1r13_evidence_value_register.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r13d_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r13_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r2_compact_verified_pending.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/official_qwen_mobile/protocol.py",
    "implementation/src/raven_m/official_qwen_mobile/working_memory.py",
    "implementation/src/raven_m/models/vllm_client.py",
    "implementation/src/raven_m/env/androidworld_adapter.py",
    "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/finalize_a1r13_evr_terminal.py",
    "implementation/scripts/run_a1r13d_evr.py",
    "implementation/scripts/preflight_a1r13d_evr.py",
    "implementation/scripts/qualify_a1r13d_evr_server.py",
    "implementation/scripts/start_a1r13d_evr_server.sh",
    "implementation/tests/official_qwen_mobile/test_a1r13d_contract.py",
    "implementation/tests/official_qwen_mobile/test_a1r13d_controller_integration.py",
    "implementation/tests/official_qwen_mobile/test_a1r13_terminal_finalizer.py",
    "evidence/a1r13/A1R13_EVR_REPLAY_FIXTURE.json",
    "evidence/a1r13/A1R13_EVR_OFFLINE_REPLAY_REPORT.json",
    "evidence/a1r13/A1R13_EVR_TERMINAL_RESULT_2026-08-18.json",
)

EXPECTED_CONFIG = {
    **base.EXPECTED_CONFIG,
    "schema": CONFIG_SCHEMA,
    "experiment_id": EXPERIMENT_ID,
    "orchestration": {
        "capability_gate_tasks": 6,
        "target_gate_task": TARGET_GATE_TASK,
        "target_first": True,
        "release_remaining_after": 7,
    },
}


canonical_sha256 = base.canonical_sha256
content_sha256 = base.content_sha256
file_sha256 = base.file_sha256
preservation_report = base.preservation_report
target_gate_report = base.target_gate_report


def _git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(REPOSITORY_ROOT), *args], text=True).strip()


def source_freeze_payload(implementation_commit: str) -> dict[str, Any]:
    if len(implementation_commit) != 40 or any(ch not in "0123456789abcdef" for ch in implementation_commit):
        raise RuntimeError("A1-R13D implementation commit invalid")
    if subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), "merge-base", "--is-ancestor", PARENT_EVIDENCE_COMMIT, implementation_commit],
        capture_output=True,
    ).returncode:
        raise RuntimeError("A1-R13D parent evidence is not an ancestor")
    files: dict[str, str] = {}
    for name in SOURCE_FILES:
        path = REPOSITORY_ROOT / name
        if not path.is_file():
            raise RuntimeError(f"A1-R13D source closure missing: {name}")
        try:
            blob = subprocess.check_output(["git", "-C", str(REPOSITORY_ROOT), "show", f"{implementation_commit}:{name}"])
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"A1-R13D source absent from implementation commit: {name}") from exc
        if _git("hash-object", "--path", name, str(path)) != _git("rev-parse", f"{implementation_commit}:{name}"):
            raise RuntimeError(f"A1-R13D current source drift: {name}")
        files[name] = sha256(blob).hexdigest()
    payload = {
        "schema": "a1r13d_evr_source_freeze_v1",
        "implementation_commit": implementation_commit,
        "parent_evidence_commit": PARENT_EVIDENCE_COMMIT,
        "files": files,
    }
    return {**payload, "content_sha256": content_sha256(payload)}


def validate_source_freeze(path: Path = SOURCE_FREEZE_PATH) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report != source_freeze_payload(str(report.get("implementation_commit") or "")):
        raise RuntimeError("A1-R13D source freeze mismatch")
    return report


def validate_preflight_report(path: Path = PREFLIGHT_PATH) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    freeze = validate_source_freeze()
    replay = json.loads(base.OFFLINE_REPLAY_PATH.read_text(encoding="utf-8"))
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    expected = {
        "schema": PREFLIGHT_SCHEMA,
        "status": "PASS",
        "errors": [],
        "generation_calls": 0,
        "live_generation_authorized": True,
        "mechanism_id": MECHANISM_ID,
        "experiment_id": EXPERIMENT_ID,
        "implementation_commit": freeze["implementation_commit"],
        "source_freeze_content_sha256": freeze["content_sha256"],
        "parent_replay_content_sha256": replay.get("content_sha256"),
    }
    errors = [f"{key}_drift" for key, value in expected.items() if report.get(key) != value]
    if report.get("content_sha256") != content_sha256(report):
        errors.append("preflight_content_hash")
    if config != EXPECTED_CONFIG:
        errors.append("config_semantic_drift")
    if not base._replay_valid(replay):
        errors.append("parent_replay_invalid")
    if (report.get("checks") or {}).get("focused_tests") != {"returncode": 0, "passed": True}:
        errors.append("focused_tests_missing")
    if errors:
        raise RuntimeError(f"A1-R13D preflight invalid: {errors}")
    return report


def validate_launch_receipt(path: Path, *, preflight_path: Path = PREFLIGHT_PATH) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    preflight = validate_preflight_report(preflight_path)
    expected = {
        "schema": LIVE_RECEIPT_SCHEMA,
        "status": "PASS",
        "errors": [],
        "generation_calls": 0,
        "mechanism_id": MECHANISM_ID,
        "experiment_id": EXPERIMENT_ID,
        "implementation_commit": preflight["implementation_commit"],
        "preflight_content_sha256": preflight["content_sha256"],
        "config_content_sha256": canonical_sha256(EXPECTED_CONFIG),
        "served_model_id": MODEL_ID,
        "served_model_ids_observed": [MODEL_ID],
        "model_realpath": MODEL_REALPATH,
        "model_manifest_sha256": MODEL_MANIFEST_SHA256,
        "port": PORT,
    }
    errors = [f"{key}_drift" for key, value in expected.items() if receipt.get(key) != value]
    if receipt.get("content_sha256") != content_sha256(receipt):
        errors.append("receipt_content_hash")
    if set(receipt.get("packages") or {}) != {"vllm", "torch", "transformers"}:
        errors.append("packages_missing")
    try:
        qualified = datetime.fromisoformat(str(receipt.get("qualified_at")))
        age = (datetime.now(timezone.utc) - qualified.astimezone(timezone.utc)).total_seconds()
        if qualified.tzinfo is None or age < -60 or age > 43_200:
            raise ValueError
    except (TypeError, ValueError):
        errors.append("qualified_at_invalid")
    pid = int(receipt.get("process_pid") or -1)
    cmdline = str(receipt.get("process_cmdline") or "")
    if "vllm" not in cmdline or MODEL_REALPATH not in cmdline or str(PORT) not in cmdline:
        errors.append("process_cmdline_identity")
    if os.name != "nt":
        proc = Path(f"/proc/{pid}/cmdline")
        observed = proc.read_bytes().replace(b"\0", b" ").decode() if proc.is_file() else ""
        if observed != cmdline:
            errors.append("process_not_alive_or_drifted")
    if errors:
        raise RuntimeError(f"A1-R13D receipt invalid: {errors}")
    return receipt


def exact_completion_errors(*, summaries: list[dict[str, Any]], invalid_attempts: list[dict[str, Any]], lifecycle_errors: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if len(summaries) != 19:
        errors.append("valid_episode_count")
    if tuple(str(row.get("task_name")) for row in summaries) != FULL_TASK_ORDER:
        errors.append("task_order")
    if any(int(row.get("seed") or -1) != TASK_SEED for row in summaries):
        errors.append("task_seed")
    if lifecycle_errors or any(not row.get("resolved_by_episode_id") for row in invalid_attempts):
        errors.append("unresolved_infrastructure")
    try:
        if any(not math.isfinite(float(row.get("evaluator_reward"))) for row in summaries):
            errors.append("reward_invalid")
    except (TypeError, ValueError):
        errors.append("reward_invalid")
    if any(
        int((((step.get("model_call") or {}).get("raven_meta") or {}).get("transport_attempts") or 0)) != 1
        for row in summaries for step in row.get("steps", [])
    ):
        errors.append("transport_attempt_not_one")
    for row in summaries:
        boundary = (row.get("memory_mechanism") or {}).get("decision_boundary") or {}
        if (
            int(boundary.get("extra_model_calls") or 0)
            or int(boundary.get("action_override_count") or 0)
            or int(boundary.get("forced_termination_count") or 0)
            or bool(boundary.get("hidden_ui_used_for_decision"))
            or bool(boundary.get("evaluator_used_for_decision"))
        ):
            errors.append(f"intervention_boundary:{row.get('task_name')}")
    if preservation_report(summaries).get("status") != "pass":
        errors.append("preservation_gate")
    if target_gate_report(summaries).get("status") != "pass":
        errors.append("target_gate")
    return errors


__all__ = [name for name in globals() if name.isupper()] + [
    "canonical_sha256", "content_sha256", "exact_completion_errors", "file_sha256",
    "preservation_report", "source_freeze_payload", "target_gate_report",
    "validate_launch_receipt", "validate_preflight_report", "validate_source_freeze",
]
