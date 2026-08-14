"""Fail-closed contract for prospective A1-R5 TIPL."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from . import a1r3_contract as base
from .a1r5_transition_invalidated_pending import EXPERIMENT_ID, MECHANISM_ID

MODEL_ID = base.MODEL_ID
MODEL_REVISION = base.MODEL_REVISION
MODEL_REALPATH = base.MODEL_REALPATH
MODEL_MANIFEST_SHA256 = base.MODEL_MANIFEST_SHA256
TASK_SEED = base.TASK_SEED
GENERATION_SEED = base.GENERATION_SEED
PORT = base.PORT
PARENT_EVIDENCE_COMMIT = "2b7e6b80d707682ac0f2d685b3dd293a53a4af78"
CONFIG_SCHEMA = "a1r5_transition_invalidated_pending_config_v1"
OFFLINE_REPLAY_SCHEMA = "a1r5_transition_invalidated_pending_offline_replay_v1"
PREFLIGHT_SCHEMA = "a1r5_tipl_zero_generation_preflight_v1"
LIVE_RECEIPT_SCHEMA = "a1r5_tipl_live_server_receipt_v1"
RESULT_SCHEMA = "a1r5_tipl_result_v1"
CHECKPOINT_SCHEMA = "a1r5_tipl_checkpoint_v1"

REPOSITORY_ROOT = base.REPOSITORY_ROOT
CONFIG_PATH = REPOSITORY_ROOT / "implementation/configs/a1r5_transition_invalidated_pending_hard_seed20260806.json"
OFFLINE_REPLAY_PATH = REPOSITORY_ROOT / "evidence/a1r5/A1R5_TIPL_OFFLINE_REPLAY_REPORT.json"
SOURCE_FREEZE_PATH = REPOSITORY_ROOT / "evidence/a1r5/A1R5_TIPL_SOURCE_FREEZE.json"
PREFLIGHT_PATH = REPOSITORY_ROOT / "evidence/a1r5/A1R5_TIPL_ZERO_GENERATION_PREFLIGHT.json"

A0_PRESERVATION_TASKS = base.A0_PRESERVATION_TASKS
RECIPE_TASK = base.RECIPE_TASK
A1R2_GAIN_TASK = base.A1R2_GAIN_TASK
CAPABILITY_GATE_TASKS = base.CAPABILITY_GATE_TASKS
FULL_TASK_ORDER = base.FULL_TASK_ORDER

SOURCE_FILES = (
    "protocols/A1R5_TRANSITION_INVALIDATED_PENDING_PREREG_2026-08-15.md",
    "implementation/configs/a1r5_transition_invalidated_pending_hard_seed20260806.json",
    "implementation/configs/androidworld_hard_v2_instances.json",
    "implementation/src/raven_m/official_qwen_mobile/a1r5_transition_invalidated_pending.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r4_writer_resilient_pending.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r3_stale_resistant_pending.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r5_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/official_qwen_mobile/protocol.py",
    "implementation/src/raven_m/official_qwen_mobile/working_memory.py",
    "implementation/src/raven_m/models/vllm_client.py",
    "implementation/src/raven_m/env/androidworld_adapter.py",
    "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/run_a1r5_tipl.py",
    "implementation/scripts/replay_a1r5_transition_invalidated_pending.py",
    "implementation/scripts/preflight_a1r5_tipl.py",
    "implementation/scripts/qualify_a1r5_tipl_server.py",
    "implementation/scripts/start_a1r5_tipl_server.sh",
    "implementation/tests/official_qwen_mobile/test_a1r5_transition_invalidated_pending.py",
    "implementation/tests/official_qwen_mobile/test_a1r5_contract.py",
    "implementation/tests/official_qwen_mobile/test_a1r5_controller_integration.py",
    "implementation/tests/official_qwen_mobile/test_a1r5_offline_replay.py",
    "evidence/a1r5/A1R5_TIPL_OFFLINE_REPLAY_REPORT.json",
    "evidence/a1r4/A1R4_WRPL_PRIMARY_GATE_RESULT_2026-08-15.json",
    "evidence/a1r4/A1R4_WRPL_PRIMARY_GATE_RESULT_2026-08-15.md",
)

file_sha256 = base.file_sha256
canonical_sha256 = base.canonical_sha256
content_sha256 = base.content_sha256


def _git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(REPOSITORY_ROOT), *args], text=True).strip()


def source_freeze_payload(implementation_commit: str) -> dict[str, Any]:
    if len(implementation_commit) != 40 or any(c not in "0123456789abcdef" for c in implementation_commit):
        raise RuntimeError("A1-R5 implementation commit invalid")
    if subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), "merge-base", "--is-ancestor", PARENT_EVIDENCE_COMMIT, implementation_commit],
        capture_output=True,
    ).returncode:
        raise RuntimeError("A1-R5 parent evidence is not an ancestor")
    files: dict[str, str] = {}
    for name in SOURCE_FILES:
        path = REPOSITORY_ROOT / name
        if not path.is_file():
            raise RuntimeError(f"A1-R5 source closure missing: {name}")
        try:
            frozen = subprocess.check_output(["git", "-C", str(REPOSITORY_ROOT), "show", f"{implementation_commit}:{name}"])
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"A1-R5 source absent from implementation commit: {name}") from exc
        if _git("hash-object", "--path", name, str(path)) != _git("rev-parse", f"{implementation_commit}:{name}"):
            raise RuntimeError(f"A1-R5 current source drift: {name}")
        files[name] = sha256(frozen).hexdigest()
    payload = {
        "schema": "a1r5_tipl_source_freeze_v1",
        "implementation_commit": implementation_commit,
        "parent_evidence_commit": PARENT_EVIDENCE_COMMIT,
        "files": files,
    }
    return {**payload, "content_sha256": content_sha256(payload)}


def validate_source_freeze(path: Path = SOURCE_FREEZE_PATH) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report != source_freeze_payload(str(report.get("implementation_commit") or "")):
        raise RuntimeError("A1-R5 source freeze mismatch")
    return report


def validate_preflight_report(path: Path = PREFLIGHT_PATH) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    freeze = validate_source_freeze()
    replay = json.loads(OFFLINE_REPLAY_PATH.read_text(encoding="utf-8"))
    expected = {
        "schema": PREFLIGHT_SCHEMA, "status": "PASS", "errors": [],
        "generation_calls": 0, "live_generation_authorized": True,
        "mechanism_id": MECHANISM_ID, "experiment_id": EXPERIMENT_ID,
        "implementation_commit": freeze["implementation_commit"],
        "source_freeze_content_sha256": freeze["content_sha256"],
        "offline_replay_content_sha256": replay.get("content_sha256"),
    }
    errors = [f"{k}_drift" for k, v in expected.items() if report.get(k) != v]
    if report.get("content_sha256") != content_sha256(report): errors.append("preflight_content_hash")
    if (
        replay.get("schema") != OFFLINE_REPLAY_SCHEMA or replay.get("status") != "PASS"
        or replay.get("errors") != [] or replay.get("generation_calls") != 0
        or replay.get("mechanism_id") != MECHANISM_ID
        or replay.get("content_sha256") != content_sha256(replay)
        or int((replay.get("totals") or {}).get("valid_episode_count") or 0) != 19
    ): errors.append("offline_replay_not_authorizing")
    if errors: raise RuntimeError(f"A1-R5 preflight invalid: {errors}")
    return report


def validate_launch_receipt(path: Path, *, preflight_path: Path = PREFLIGHT_PATH) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    preflight = validate_preflight_report(preflight_path)
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    expected = {
        "schema": LIVE_RECEIPT_SCHEMA, "status": "PASS", "errors": [], "generation_calls": 0,
        "mechanism_id": MECHANISM_ID, "experiment_id": EXPERIMENT_ID,
        "implementation_commit": preflight["implementation_commit"],
        "preflight_content_sha256": preflight["content_sha256"],
        "config_content_sha256": canonical_sha256(config), "served_model_id": MODEL_ID,
        "served_model_ids_observed": [MODEL_ID], "model_realpath": MODEL_REALPATH,
        "model_manifest_sha256": MODEL_MANIFEST_SHA256, "port": PORT,
    }
    errors = [f"{k}_drift" for k, v in expected.items() if receipt.get(k) != v]
    packages = receipt.get("packages") or {}
    if set(packages) != {"vllm", "torch", "transformers"} or any(not str(v) for v in packages.values()): errors.append("packages_missing")
    if receipt.get("content_sha256") != content_sha256(receipt): errors.append("receipt_content_hash")
    try:
        qualified = datetime.fromisoformat(str(receipt.get("qualified_at")))
        age = (datetime.now(timezone.utc) - qualified.astimezone(timezone.utc)).total_seconds()
        if qualified.tzinfo is None or age > 43200: raise ValueError
    except (TypeError, ValueError): errors.append("qualified_at_invalid")
    pid = int(receipt.get("process_pid") or -1); cmdline = str(receipt.get("process_cmdline") or "")
    if "vllm" not in cmdline or MODEL_REALPATH not in cmdline or str(PORT) not in cmdline: errors.append("process_cmdline_identity")
    if os.name != "nt":
        proc = Path(f"/proc/{pid}/cmdline")
        observed = proc.read_bytes().replace(b"\0", b" ").decode() if proc.is_file() else ""
        if observed != cmdline: errors.append("process_not_alive_or_drifted")
    if errors: raise RuntimeError(f"A1-R5 receipt invalid: {errors}")
    return receipt


def preservation_report(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    return base.preservation_report(summaries)


def exact_completion_errors(*, summaries: list[dict[str, Any]], invalid_attempts: list[dict[str, Any]], lifecycle_errors: list[dict[str, Any]]) -> list[str]:
    return base.exact_completion_errors(summaries=summaries, invalid_attempts=invalid_attempts, lifecycle_errors=lifecycle_errors)


__all__ = [name for name in globals() if name.isupper()] + [
    "canonical_sha256", "content_sha256", "exact_completion_errors", "file_sha256",
    "preservation_report", "source_freeze_payload", "validate_launch_receipt",
    "validate_preflight_report", "validate_source_freeze",
]
