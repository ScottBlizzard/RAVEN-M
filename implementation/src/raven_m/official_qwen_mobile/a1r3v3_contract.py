"""Fail-closed contract for A1-R3-v3 one-shot CNR."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Any

from .a1r3v3_one_shot_cnr import EXPERIMENT_ID, MECHANISM_ID


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
MODEL_REALPATH = "/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope"
MODEL_MANIFEST_SHA256 = "18e0909c7d993853d6d0f62443461a74009754f90db026a1723cab80121c7872"
PARENT_EVIDENCE_COMMIT = "83c0de5bed18740719b46b5bdd1fccf7904ba0cb"
TASK_SEED = 20260806
GENERATION_SEED = 3407
PORT = 18000
CONFIG_SCHEMA = "a1r3v3_one_shot_cnr_config_v1"
OFFLINE_REPLAY_SCHEMA = "a1r3v3_one_shot_cnr_offline_replay_v1"
PREFLIGHT_SCHEMA = "a1r3v3_oscnr_zero_generation_preflight_v1"
LIVE_RECEIPT_SCHEMA = "a1r3v3_oscnr_live_server_receipt_v1"
RESULT_SCHEMA = "a1r3v3_oscnr_result_v1"
CHECKPOINT_SCHEMA = "a1r3v3_oscnr_checkpoint_v1"

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
CONFIG_PATH = REPOSITORY_ROOT / "implementation/configs/a1r3v3_one_shot_cnr_hard_seed20260806.json"
OFFLINE_REPLAY_PATH = REPOSITORY_ROOT / "evidence/a1r3_v3/A1R3V3_ONE_SHOT_CNR_OFFLINE_REPLAY_REPORT.json"
SOURCE_FREEZE_PATH = REPOSITORY_ROOT / "evidence/a1r3_v3/A1R3V3_OSCNR_SOURCE_FREEZE.json"
PREFLIGHT_PATH = REPOSITORY_ROOT / "evidence/a1r3_v3/A1R3V3_OSCNR_ZERO_GENERATION_PREFLIGHT.json"

A0_PRESERVATION_TASKS = (
    "ExpenseDeleteMultiple2",
    "RetroSavePlaylist",
    "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
)
RECIPE_TASK = "RecipeDeleteMultipleRecipesWithConstraint"
A1R2_GAIN_TASK = "OsmAndMarker"
CAPABILITY_GATE_TASKS = A0_PRESERVATION_TASKS + (RECIPE_TASK, A1R2_GAIN_TASK)
FULL_TASK_ORDER = CAPABILITY_GATE_TASKS + (
    "BrowserMultiply",
    "ExpenseAddMultipleFromGallery",
    "ExpenseAddMultipleFromMarkor",
    "MarkorCreateNoteAndSms",
    "MarkorMergeNotes",
    "MarkorTranscribeVideo",
    "OsmAndTrack",
    "RecipeAddMultipleRecipesFromImage",
    "RecipeAddMultipleRecipesFromMarkor",
    "RecipeAddMultipleRecipesFromMarkor2",
    "SaveCopyOfReceiptTaskEval",
    "SportsTrackerActivitiesOnDate",
    "SportsTrackerTotalDistanceForCategoryOverInterval",
)

SOURCE_FILES = (
    "protocols/A1R3V3_ONE_SHOT_CNR_PREREG_2026-08-15.md",
    "implementation/configs/a1r3v3_one_shot_cnr_hard_seed20260806.json",
    "implementation/configs/a1r3v3_one_shot_cnr_neutralized_hard_seed20260806.json",
    "implementation/configs/androidworld_hard_v2_instances.json",
    "implementation/src/raven_m/official_qwen_mobile/a1r2_compact_verified_pending.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r3v3_one_shot_cnr.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r3v3_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/__init__.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/official_qwen_mobile/protocol.py",
    "implementation/src/raven_m/models/vllm_client.py",
    "implementation/src/raven_m/env/androidworld_adapter.py",
    "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/run_a1r3v3_oscnr.py",
    "implementation/scripts/replay_a1r3v3_one_shot_cnr.py",
    "implementation/scripts/preflight_a1r3v3_oscnr.py",
    "implementation/scripts/qualify_a1r3v3_oscnr_server.py",
    "implementation/scripts/start_a1r3v3_oscnr_server.sh",
    "implementation/tests/official_qwen_mobile/test_a1r3v3_one_shot_cnr.py",
    "implementation/tests/official_qwen_mobile/test_a1r3v3_contract.py",
    "implementation/tests/official_qwen_mobile/test_a1r3v3_controller_integration.py",
    "implementation/tests/official_qwen_mobile/test_a1r3v3_offline_replay.py",
    "evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.json",
)


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return sha256(raw).hexdigest()


def content_sha256(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("content_sha256", None)
    return canonical_sha256(payload)


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(REPOSITORY_ROOT), *args], text=True
    ).strip()


def source_freeze_payload(implementation_commit: str) -> dict[str, Any]:
    if len(implementation_commit) != 40 or any(c not in "0123456789abcdef" for c in implementation_commit):
        raise RuntimeError("A1-R3-v3 implementation commit invalid")
    if subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), "merge-base", "--is-ancestor", PARENT_EVIDENCE_COMMIT, implementation_commit],
        capture_output=True,
    ).returncode:
        raise RuntimeError("A1-R3-v3 parent evidence is not an ancestor")
    files: dict[str, str] = {}
    for name in SOURCE_FILES:
        path = REPOSITORY_ROOT / name
        if not path.is_file():
            raise RuntimeError(f"A1-R3-v3 source closure missing: {name}")
        try:
            frozen = subprocess.check_output(
                ["git", "-C", str(REPOSITORY_ROOT), "show", f"{implementation_commit}:{name}"]
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"A1-R3-v3 source absent from implementation commit: {name}") from exc
        if _git("hash-object", "--path", name, str(path)) != _git("rev-parse", f"{implementation_commit}:{name}"):
            raise RuntimeError(f"A1-R3-v3 current source drift: {name}")
        files[name] = sha256(frozen).hexdigest()
    payload = {
        "schema": "a1r3v3_oscnr_source_freeze_v1",
        "implementation_commit": implementation_commit,
        "parent_evidence_commit": PARENT_EVIDENCE_COMMIT,
        "files": files,
    }
    return {**payload, "content_sha256": content_sha256(payload)}


def validate_source_freeze(path: Path = SOURCE_FREEZE_PATH) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report != source_freeze_payload(str(report.get("implementation_commit") or "")):
        raise RuntimeError("A1-R3-v3 source freeze mismatch")
    return report


def _validate_replay(replay: dict[str, Any]) -> list[str]:
    totals = replay.get("totals") or {}
    expected = {
        "valid_episode_count": 19,
        "invalid_attempt_count": 1,
        "model_calls": 603,
        "executed_actions": 595,
        "a1r2_actual_rendered_chars": 108423,
        "a1r2_actual_rendered_tokens": 21710,
        "projected_nonempty_reads": 436,
        "projected_rendered_chars": 109185,
        "projected_rendered_tokens": 21870,
        "cnr_receipt_creation_count": 8,
        "cnr_receipt_committed_read_count": 8,
        "success_task_receipt_creation_count": 0,
        "success_task_receipt_read_count": 0,
        "failure_tasks_with_receipt": 8,
    }
    errors = [f"replay_total_{key}" for key, value in expected.items() if totals.get(key) != value]
    if (
        replay.get("schema") != OFFLINE_REPLAY_SCHEMA
        or replay.get("status") != "PASS"
        or replay.get("errors") != []
        or replay.get("generation_calls") != 0
        or replay.get("mechanism_id") != MECHANISM_ID
        or replay.get("development_calibration_not_confirmation") is not True
        or replay.get("content_sha256") != content_sha256(replay)
    ):
        errors.append("replay_identity_or_status")
    return errors


def validate_preflight_report(path: Path = PREFLIGHT_PATH) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    freeze = validate_source_freeze(SOURCE_FREEZE_PATH)
    replay = json.loads(OFFLINE_REPLAY_PATH.read_text(encoding="utf-8"))
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
        "offline_replay_content_sha256": replay.get("content_sha256"),
    }
    errors = [f"{key}_drift" for key, value in expected.items() if report.get(key) != value]
    errors += _validate_replay(replay)
    if report.get("content_sha256") != content_sha256(report):
        errors.append("preflight_content_hash")
    if errors:
        raise RuntimeError(f"A1-R3-v3 preflight invalid: {errors}")
    return report


def validate_launch_receipt(path: Path, *, preflight_path: Path = PREFLIGHT_PATH) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    preflight = validate_preflight_report(preflight_path)
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    expected = {
        "schema": LIVE_RECEIPT_SCHEMA,
        "status": "PASS",
        "errors": [],
        "generation_calls": 0,
        "mechanism_id": MECHANISM_ID,
        "experiment_id": EXPERIMENT_ID,
        "implementation_commit": preflight["implementation_commit"],
        "preflight_content_sha256": preflight.get("content_sha256"),
        "config_content_sha256": canonical_sha256(config),
        "served_model_id": MODEL_ID,
        "served_model_ids_observed": [MODEL_ID],
        "model_realpath": MODEL_REALPATH,
        "model_manifest_sha256": MODEL_MANIFEST_SHA256,
        "port": PORT,
    }
    errors = [f"{key}_drift" for key, value in expected.items() if receipt.get(key) != value]
    packages = receipt.get("packages") or {}
    if set(packages) != {"vllm", "torch", "transformers"} or any(not str(v) for v in packages.values()):
        errors.append("packages_missing")
    if receipt.get("content_sha256") != content_sha256(receipt):
        errors.append("receipt_content_hash")
    try:
        qualified = datetime.fromisoformat(str(receipt.get("qualified_at")))
        age = (datetime.now(timezone.utc) - qualified.astimezone(timezone.utc)).total_seconds()
        if qualified.tzinfo is None or age > 43200:
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
        raise RuntimeError(f"A1-R3-v3 receipt invalid: {errors}")
    return receipt


def preservation_report(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    observed = {str(item.get("task_name")): item for item in summaries}
    tasks = [
        {"task_name": name, "reward": (observed.get(name) or {}).get("evaluator_reward"), "pass": (observed.get(name) or {}).get("evaluator_reward") == 1.0}
        for name in CAPABILITY_GATE_TASKS
    ]
    count = sum(int(item["pass"]) for item in tasks)
    return {"status": "pass" if count == 6 else "fail", "success_count": count, "required": 6, "tasks": tasks}


def exact_completion_errors(*, summaries: list[dict[str, Any]], invalid_attempts: list[dict[str, Any]], lifecycle_errors: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if len(summaries) != 19:
        errors.append("valid_episode_count")
    if tuple(str(item.get("task_name")) for item in summaries) != FULL_TASK_ORDER:
        errors.append("task_order")
    if any(int(item.get("seed") or -1) != TASK_SEED for item in summaries):
        errors.append("task_seed")
    if lifecycle_errors or any(not item.get("resolved_by_episode_id") for item in invalid_attempts):
        errors.append("unresolved_infrastructure")
    if len(invalid_attempts) > 2:
        errors.append("infrastructure_replacement_cap")
    try:
        if any(not math.isfinite(float(item.get("evaluator_reward"))) for item in summaries):
            errors.append("reward_invalid")
    except (TypeError, ValueError):
        errors.append("reward_invalid")
    if any(
        int(((step.get("model_call") or {}).get("raven_meta") or {}).get("transport_attempts") or 0) != 1
        for item in summaries for step in item.get("steps", [])
    ):
        errors.append("transport_attempt_not_one")
    for item in summaries:
        audit = item.get("memory_mechanism") or {}
        boundary = audit.get("decision_boundary") or {}
        if any(int(boundary.get(key) or 0) for key in ("extra_model_calls", "action_override_count", "forced_termination_count")):
            errors.append("intervention_boundary")
            break
        if audit.get("pending_ticket") is not None:
            errors.append("unclosed_read_ticket")
            break
    return errors


__all__ = [name for name in globals() if name.isupper()] + [
    "canonical_sha256", "content_sha256", "exact_completion_errors", "file_sha256",
    "preservation_report", "source_freeze_payload", "validate_launch_receipt",
    "validate_preflight_report", "validate_source_freeze",
]
