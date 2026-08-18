"""Fail-closed scheduling contract for the A1-R15 stitched continuation."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Any

from . import a1r15_contract as original

REPOSITORY_ROOT = original.REPOSITORY_ROOT
MECHANISM_ID = original.MECHANISM_ID
EXPERIMENT_ID = "A1R15_EOVR_QWEN3VL32B_AW_HARD_S20260806_G3407_V1_STITCHED_CONTINUATION"
PARENT_MECHANISM_COMMIT = "c21cad1d5456c37cf72fa677d5fa08d2d8f28665"
PARENT_MECHANISM_BLOB_SHA1 = "df561222a77328fc0370efb3dde78db8cbb8fbe9"
PARENT_EVIDENCE_COMMIT = "32bcca78cb91c220f6dfec7833e783f6f312a5e2"
TASK_SEED = original.TASK_SEED
GENERATION_SEED = original.GENERATION_SEED
MODEL_ID = original.MODEL_ID
MODEL_REVISION = original.MODEL_REVISION
MODEL_REALPATH = original.MODEL_REALPATH
MODEL_MANIFEST_SHA256 = original.MODEL_MANIFEST_SHA256
PORT = original.PORT
CONFIG_PATH = original.CONFIG_PATH
EXPECTED_CONFIG = original.EXPECTED_CONFIG
CHECKPOINT_SCHEMA = "a1r15_eovr_stitched_continuation_checkpoint_v1"
RESULT_SCHEMA = "a1r15_eovr_stitched_continuation_result_v1"
PREFLIGHT_SCHEMA = "a1r15_eovr_stitched_continuation_preflight_v1"
LIVE_RECEIPT_SCHEMA = "a1r15_eovr_stitched_continuation_receipt_v1"

PARENT_RESULT_PATH = REPOSITORY_ROOT / "evidence/a1r15/A1R15_EOVR_TERMINAL_RESULT_2026-08-18.json"
PARENT_SNAPSHOT_PATH = REPOSITORY_ROOT / "evidence/sys_r2_lrer/source_episodes/a1_r15_01_browsermultiply.json"
PARENT_FORENSIC_PATH = REPOSITORY_ROOT / "evidence/r15_browser_forensics/R15_BROWSER_FORENSIC_2026-08-18.json"
SOURCE_FREEZE_PATH = REPOSITORY_ROOT / "evidence/a1r15_stitched_continuation/A1R15_STITCHED_CONTINUATION_SOURCE_FREEZE.json"
PREFLIGHT_PATH = REPOSITORY_ROOT / "evidence/a1r15_stitched_continuation/A1R15_STITCHED_CONTINUATION_ZERO_GENERATION_PREFLIGHT.json"

TARGET_GATE_TASK = "BrowserMultiply"
CAPABILITY_GATE_TASKS = original.CAPABILITY_GATE_TASKS
REMAINING_TASKS = tuple(original.FULL_TASK_ORDER[7:])
FULL_TASK_ORDER = tuple(CAPABILITY_GATE_TASKS) + REMAINING_TASKS
STITCHED_TASK_ORDER = (TARGET_GATE_TASK,) + FULL_TASK_ORDER

SOURCE_FILES = (
    "protocols/A1R15_STITCHED_CONTINUATION_AMENDMENT_2026-08-18.md",
    "protocols/A1R15_EXPLICIT_OBSERVATION_VALUE_REGISTER_PREREG_2026-08-18.md",
    "implementation/configs/a1r15_eovr_hard_seed20260806.json",
    "implementation/configs/androidworld_hard_v2_instances.json",
    "implementation/src/raven_m/official_qwen_mobile/a1r15_explicit_observation_value_register.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r15_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r15_stitched_continuation_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r14_response_value_register.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r13_evidence_value_register.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r2_compact_verified_pending.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/official_qwen_mobile/protocol.py",
    "implementation/src/raven_m/official_qwen_mobile/working_memory.py",
    "implementation/src/raven_m/models/vllm_client.py",
    "implementation/src/raven_m/env/androidworld_adapter.py",
    "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/preflight_a1r15_stitched_continuation.py",
    "implementation/scripts/qualify_a1r15_stitched_continuation_server.py",
    "implementation/scripts/qualify_a1r5_tipl_server.py",
    "implementation/scripts/run_a1r15_stitched_continuation.py",
    "implementation/tests/official_qwen_mobile/test_a1r15_stitched_continuation.py",
    "evidence/a1r15/A1R15_EOVR_TERMINAL_RESULT_2026-08-18.json",
    "evidence/sys_r2_lrer/source_episodes/a1_r15_01_browsermultiply.json",
    "evidence/r15_browser_forensics/R15_BROWSER_FORENSIC_2026-08-18.json",
)

canonical_sha256 = original.canonical_sha256
content_sha256 = original.content_sha256
file_sha256 = original.file_sha256


def parent_browser_binding() -> dict[str, Any]:
    result = json.loads(PARENT_RESULT_PATH.read_text(encoding="utf-8"))
    snapshot = json.loads(PARENT_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    forensic = json.loads(PARENT_FORENSIC_PATH.read_text(encoding="utf-8"))
    raw_sha = "b7bfd75c644e20d52f7436a21799c9f2e3736af20a84e378de4334daa2158765"
    errors = []
    identity = result.get("identity") or {}
    outcome = result.get("outcome") or {}
    if result.get("classification") != "TARGET_SUCCESS_WITHOUT_MATURE_EVR_READ_UNATTRIBUTED": errors.append("classification")
    if identity.get("implementation_commit") != PARENT_MECHANISM_COMMIT: errors.append("implementation_commit")
    if identity.get("mechanism_id") != MECHANISM_ID: errors.append("mechanism_id")
    if outcome.get("task_name") != TARGET_GATE_TASK or outcome.get("reward") != 1.0: errors.append("outcome")
    if (result.get("closure") or {}).get("episode_json_sha256") != raw_sha: errors.append("result_raw_sha")
    if snapshot.get("source_episode_sha256") != raw_sha: errors.append("snapshot_raw_sha")
    forensic_text = json.dumps(forensic, ensure_ascii=False, sort_keys=True)
    if raw_sha not in forensic_text: errors.append("forensic_raw_sha")
    if errors: raise RuntimeError(f"A1-R15 parent Browser binding invalid: {errors}")
    return {
        "task_name": TARGET_GATE_TASK,
        "episode_id": outcome.get("episode_id"),
        "seed": TASK_SEED,
        "reward": 1.0,
        "success": True,
        "classification": result["classification"],
        "mechanism_id": MECHANISM_ID,
        "implementation_commit": PARENT_MECHANISM_COMMIT,
        "episode_json_sha256": raw_sha,
        "terminal_result_file_sha256": file_sha256(PARENT_RESULT_PATH),
        "terminal_result_content_sha256": result.get("content_sha256"),
        "snapshot_file_sha256": file_sha256(PARENT_SNAPSHOT_PATH),
        "forensic_file_sha256": file_sha256(PARENT_FORENSIC_PATH),
        "evr_rendered_value_read_count": 0,
        "success_attributed_to_evr": False,
    }


def preservation_report(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    observed = {str(row.get("task_name")): row for row in summaries}
    rows = []
    for name in CAPABILITY_GATE_TASKS:
        item = observed.get(name)
        passed = bool(item and item.get("evaluator_reward") == 1.0)
        rows.append({"task_name": name, "reward": item.get("evaluator_reward") if item else None, "pass": passed})
    count = sum(int(row["pass"]) for row in rows)
    return {"status": "pass" if count == 6 else "pending" if len(observed) < 6 else "fail", "success_count": count, "required": 6, "tasks": rows}


def stitched_seven_report(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    parent = parent_browser_binding()
    six = preservation_report(summaries)
    passed = parent["success"] and six["status"] == "pass"
    return {"status": "pass" if passed else "pending" if len(summaries) < 6 else "fail", "imported_browser": parent, "continuation_six": six, "success_count": 1 + int(six["success_count"]), "required": 7}


def target_gate_report(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    parent = parent_browser_binding()
    return {"status": "pass", "task_name": TARGET_GATE_TASK, "pass": True, "imported_parent": True, "historical_mechanism_gate_passed": False, "classification": parent["classification"]}


def exact_completion_errors(*, summaries: list[dict[str, Any]], invalid_attempts: list[dict[str, Any]], lifecycle_errors: list[dict[str, Any]]) -> list[str]:
    errors = []
    if len(summaries) != 18 or tuple(str(row.get("task_name")) for row in summaries) != FULL_TASK_ORDER: errors.append("task_closure")
    if lifecycle_errors or any(not row.get("resolved_by_episode_id") for row in invalid_attempts): errors.append("infrastructure_closure")
    try:
        if any(not math.isfinite(float(row.get("evaluator_reward"))) for row in summaries): errors.append("reward_invalid")
    except (TypeError, ValueError): errors.append("reward_invalid")
    if stitched_seven_report(summaries)["status"] != "pass": errors.append("stitched_seven_gate")
    return errors


def _git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(REPOSITORY_ROOT), *args], text=True).strip()


def source_freeze_payload(commit: str) -> dict[str, Any]:
    if len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit): raise RuntimeError("implementation commit invalid")
    files = {}
    for name in SOURCE_FILES:
        path = REPOSITORY_ROOT / name
        if not path.is_file(): raise RuntimeError(f"source missing: {name}")
        blob = subprocess.check_output(["git", "-C", str(REPOSITORY_ROOT), "show", f"{commit}:{name}"])
        if _git("hash-object", "--path", name, str(path)) != _git("rev-parse", f"{commit}:{name}"): raise RuntimeError(f"current source drift: {name}")
        files[name] = sha256(blob).hexdigest()
    current_blob = _git("rev-parse", f"{commit}:implementation/src/raven_m/official_qwen_mobile/a1r15_explicit_observation_value_register.py")
    if PARENT_MECHANISM_BLOB_SHA1 != current_blob: raise RuntimeError("A1-R15 mechanism source changed since frozen implementation")
    payload = {"schema": "a1r15_stitched_continuation_source_freeze_v1", "implementation_commit": commit, "parent_mechanism_commit": PARENT_MECHANISM_COMMIT, "mechanism_blob_sha1": current_blob, "files": files, "parent_browser": parent_browser_binding()}
    return {**payload, "content_sha256": content_sha256(payload)}


def validate_source_freeze(path: Path = SOURCE_FREEZE_PATH) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report != source_freeze_payload(str(report.get("implementation_commit") or "")): raise RuntimeError("source freeze mismatch")
    return report


def validate_preflight_report(path: Path = PREFLIGHT_PATH) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8")); freeze = validate_source_freeze()
    expected = {"schema": PREFLIGHT_SCHEMA, "status": "PASS", "errors": [], "generation_calls": 0, "live_generation_authorized": True, "mechanism_id": MECHANISM_ID, "experiment_id": EXPERIMENT_ID, "implementation_commit": freeze["implementation_commit"], "source_freeze_content_sha256": freeze["content_sha256"]}
    errors = [f"{k}_drift" for k,v in expected.items() if report.get(k) != v]
    if report.get("content_sha256") != content_sha256(report): errors.append("preflight_hash")
    if (report.get("checks") or {}).get("focused_tests") != {"returncode": 0, "passed": True}: errors.append("tests")
    if errors: raise RuntimeError(f"continuation preflight invalid: {errors}")
    return report


def validate_launch_receipt(path: Path, *, preflight_path: Path = PREFLIGHT_PATH) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8")); preflight = validate_preflight_report(preflight_path)
    expected = {"schema": LIVE_RECEIPT_SCHEMA, "status": "PASS", "errors": [], "generation_calls": 0, "mechanism_id": MECHANISM_ID, "experiment_id": EXPERIMENT_ID, "implementation_commit": preflight["implementation_commit"], "preflight_content_sha256": preflight["content_sha256"], "config_content_sha256": canonical_sha256(EXPECTED_CONFIG), "served_model_id": MODEL_ID, "served_model_ids_observed": [MODEL_ID], "model_realpath": MODEL_REALPATH, "model_manifest_sha256": MODEL_MANIFEST_SHA256, "port": PORT}
    errors=[f"{k}_drift" for k,v in expected.items() if receipt.get(k)!=v]
    if receipt.get("content_sha256") != content_sha256(receipt): errors.append("receipt_hash")
    try:
        qualified=datetime.fromisoformat(str(receipt.get("qualified_at"))); age=(datetime.now(timezone.utc)-qualified.astimezone(timezone.utc)).total_seconds()
        if qualified.tzinfo is None or age < -60 or age > 43200: raise ValueError
    except (TypeError, ValueError): errors.append("qualified_at")
    if errors: raise RuntimeError(f"continuation receipt invalid: {errors}")
    return receipt


__all__ = [n for n in globals() if n.isupper()] + ["content_sha256", "exact_completion_errors", "file_sha256", "parent_browser_binding", "preservation_report", "source_freeze_payload", "stitched_seven_report", "target_gate_report", "validate_launch_receipt", "validate_preflight_report", "validate_source_freeze"]
