"""Fail-closed contract for prospective A1-R14 RGVR."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Any

from . import a1r13d_contract as prior
from .a1r14_response_value_register import EXPERIMENT_ID, MECHANISM_ID

MODEL_ID = prior.MODEL_ID
MODEL_REVISION = prior.MODEL_REVISION
MODEL_REALPATH = prior.MODEL_REALPATH
MODEL_MANIFEST_SHA256 = prior.MODEL_MANIFEST_SHA256
TASK_SEED = prior.TASK_SEED
GENERATION_SEED = prior.GENERATION_SEED
PORT = prior.PORT
PARENT_EVIDENCE_COMMIT = "b1523abcad250d6193c75fdde02ad92cd8e9ff10"
CONFIG_SCHEMA = "a1r14_rgvr_config_v1"
PREFLIGHT_SCHEMA = "a1r14_rgvr_preflight_v1"
LIVE_RECEIPT_SCHEMA = "a1r14_rgvr_receipt_v1"
CHECKPOINT_SCHEMA = "a1r14_rgvr_checkpoint_v1"
RESULT_SCHEMA = "a1r14_rgvr_result_v1"
REPOSITORY_ROOT = prior.REPOSITORY_ROOT
CONFIG_PATH = REPOSITORY_ROOT / "implementation/configs/a1r14_rgvr_hard_seed20260806.json"
FIXTURE_PATH = REPOSITORY_ROOT / "evidence/a1r14/A1R14_RGVR_REPLAY_FIXTURE.json"
OFFLINE_REPLAY_PATH = REPOSITORY_ROOT / "evidence/a1r14/A1R14_RGVR_OFFLINE_REPLAY_REPORT.json"
SOURCE_FREEZE_PATH = REPOSITORY_ROOT / "evidence/a1r14/A1R14_RGVR_SOURCE_FREEZE.json"
PREFLIGHT_PATH = REPOSITORY_ROOT / "evidence/a1r14/A1R14_RGVR_ZERO_GENERATION_PREFLIGHT.json"
TARGET_GATE_TASK = prior.TARGET_GATE_TASK
CAPABILITY_GATE_TASKS = prior.CAPABILITY_GATE_TASKS
FULL_TASK_ORDER = prior.FULL_TASK_ORDER

SOURCE_FILES = (
    "protocols/A1R14_RESPONSE_GROUNDED_VALUE_REGISTER_PREREG_2026-08-18.md",
    "implementation/configs/a1r14_rgvr_hard_seed20260806.json",
    "implementation/configs/androidworld_hard_v2_instances.json",
    "implementation/src/raven_m/official_qwen_mobile/a1r14_response_value_register.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r14_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r13_evidence_value_register.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r2_compact_verified_pending.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/official_qwen_mobile/protocol.py",
    "implementation/src/raven_m/official_qwen_mobile/working_memory.py",
    "implementation/src/raven_m/models/vllm_client.py",
    "implementation/src/raven_m/env/androidworld_adapter.py",
    "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/materialize_a1r14_rgvr_fixture.py",
    "implementation/scripts/replay_a1r14_response_value_register.py",
    "implementation/scripts/preflight_a1r14_rgvr.py",
    "implementation/scripts/qualify_a1r14_rgvr_server.py",
    "implementation/scripts/start_a1r14_rgvr_server.sh",
    "implementation/scripts/run_a1r14_rgvr.py",
    "implementation/tests/official_qwen_mobile/test_a1r14_response_value_register.py",
    "implementation/tests/official_qwen_mobile/test_a1r14_contract.py",
    "implementation/tests/official_qwen_mobile/test_a1r14_controller_integration.py",
    "evidence/a1r14/A1R14_RGVR_REPLAY_FIXTURE.json",
    "evidence/a1r14/A1R14_RGVR_OFFLINE_REPLAY_REPORT.json",
    "evidence/a1r13d/A1R13D_EVR_TERMINAL_RESULT_2026-08-18.json",
)

EXPECTED_CONFIG = {
    "schema": CONFIG_SCHEMA,
    "mechanism_id": MECHANISM_ID,
    "experiment_id": EXPERIMENT_ID,
    "task_seed": TASK_SEED,
    "generation_seed": GENERATION_SEED,
    "model_id": MODEL_ID,
    "model_revision": MODEL_REVISION,
    "memory": {
        "base": "exact_a1r2_compact_verified_pending",
        "ttl_requests": 8,
        "max_render_chars": 1100,
        "evidence_ttl_requests": 8,
        "max_evidence_values": 6,
        "min_values_to_render": 2,
        "response_observation_fallback": True,
    },
    "decision_boundary": {
        "extra_model_calls": 0,
        "action_override_count": 0,
        "forced_termination_count": 0,
        "task_name_rules": False,
        "screen_text_or_ocr_used": False,
        "hidden_ui_used": False,
        "evaluator_used": False,
        "full_model_response_used": True,
        "model_authored_text_only": True,
    },
    "orchestration": {
        "capability_gate_tasks": 6,
        "target_gate_task": TARGET_GATE_TASK,
        "target_first": True,
        "release_remaining_after": 7,
    },
}

canonical_sha256 = prior.canonical_sha256
content_sha256 = prior.content_sha256
file_sha256 = prior.file_sha256


def _git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(REPOSITORY_ROOT), *args], text=True).strip()


def source_freeze_payload(commit: str) -> dict[str, Any]:
    if len(commit) != 40 or any(ch not in "0123456789abcdef" for ch in commit):
        raise RuntimeError("A1-R14 implementation commit invalid")
    if subprocess.run(["git", "-C", str(REPOSITORY_ROOT), "merge-base", "--is-ancestor", PARENT_EVIDENCE_COMMIT, commit], capture_output=True).returncode:
        raise RuntimeError("A1-R14 parent evidence is not an ancestor")
    files: dict[str, str] = {}
    for name in SOURCE_FILES:
        path = REPOSITORY_ROOT / name
        if not path.is_file():
            raise RuntimeError(f"A1-R14 source missing: {name}")
        try:
            blob = subprocess.check_output(["git", "-C", str(REPOSITORY_ROOT), "show", f"{commit}:{name}"])
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"A1-R14 source absent from commit: {name}") from exc
        if _git("hash-object", "--path", name, str(path)) != _git("rev-parse", f"{commit}:{name}"):
            raise RuntimeError(f"A1-R14 current source drift: {name}")
        files[name] = sha256(blob).hexdigest()
    payload = {"schema": "a1r14_rgvr_source_freeze_v1", "implementation_commit": commit, "parent_evidence_commit": PARENT_EVIDENCE_COMMIT, "files": files}
    return {**payload, "content_sha256": content_sha256(payload)}


def validate_source_freeze(path: Path = SOURCE_FREEZE_PATH) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report != source_freeze_payload(str(report.get("implementation_commit") or "")):
        raise RuntimeError("A1-R14 source freeze mismatch")
    return report


def _replay_valid(replay: dict[str, Any]) -> bool:
    totals = replay.get("totals") or {}
    target = replay.get("target") or {}
    return bool(
        replay.get("schema") == "a1r14_rgvr_offline_replay_v1"
        and replay.get("status") == "PASS"
        and replay.get("errors") == []
        and replay.get("generation_calls") == 0
        and replay.get("mechanism_id") == MECHANISM_ID
        and replay.get("experiment_id") == EXPERIMENT_ID
        and replay.get("content_sha256") == content_sha256(replay)
        and int(totals.get("episode_count") or 0) == 19
        and int(totals.get("active_episode_count") or 0) == 1
        and int(totals.get("six_success_active_count", -1)) == 0
        and int(totals.get("target_response_append_count") or 0) == 5
        and int(totals.get("max_serialized_audit_bytes") or 10**9) <= 131_072
        and target.get("final_values") == ["1", "8", "10", "7", "2"]
    )


def validate_preflight_report(path: Path = PREFLIGHT_PATH) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    freeze = validate_source_freeze()
    replay = json.loads(OFFLINE_REPLAY_PATH.read_text(encoding="utf-8"))
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    expected = {"schema": PREFLIGHT_SCHEMA, "status": "PASS", "errors": [], "generation_calls": 0, "live_generation_authorized": True, "mechanism_id": MECHANISM_ID, "experiment_id": EXPERIMENT_ID, "implementation_commit": freeze["implementation_commit"], "source_freeze_content_sha256": freeze["content_sha256"], "offline_replay_content_sha256": replay.get("content_sha256"), "fixture_content_sha256": fixture.get("content_sha256")}
    errors = [f"{key}_drift" for key, value in expected.items() if report.get(key) != value]
    if report.get("content_sha256") != content_sha256(report):
        errors.append("preflight_hash")
    if json.loads(CONFIG_PATH.read_text(encoding="utf-8")) != EXPECTED_CONFIG:
        errors.append("config_drift")
    if fixture.get("schema") != "a1r14_rgvr_replay_fixture_v1" or fixture.get("content_sha256") != content_sha256(fixture):
        errors.append("fixture_invalid")
    if not _replay_valid(replay):
        errors.append("replay_invalid")
    if (report.get("checks") or {}).get("focused_tests") != {"returncode": 0, "passed": True}:
        errors.append("focused_tests_missing")
    if errors:
        raise RuntimeError(f"A1-R14 preflight invalid: {errors}")
    return report


def validate_launch_receipt(path: Path, *, preflight_path: Path = PREFLIGHT_PATH) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    preflight = validate_preflight_report(preflight_path)
    expected = {"schema": LIVE_RECEIPT_SCHEMA, "status": "PASS", "errors": [], "generation_calls": 0, "mechanism_id": MECHANISM_ID, "experiment_id": EXPERIMENT_ID, "implementation_commit": preflight["implementation_commit"], "preflight_content_sha256": preflight["content_sha256"], "config_content_sha256": canonical_sha256(EXPECTED_CONFIG), "served_model_id": MODEL_ID, "served_model_ids_observed": [MODEL_ID], "model_realpath": MODEL_REALPATH, "model_manifest_sha256": MODEL_MANIFEST_SHA256, "port": PORT}
    errors = [f"{key}_drift" for key, value in expected.items() if receipt.get(key) != value]
    if receipt.get("content_sha256") != content_sha256(receipt):
        errors.append("receipt_hash")
    try:
        qualified = datetime.fromisoformat(str(receipt.get("qualified_at")))
        age = (datetime.now(timezone.utc) - qualified.astimezone(timezone.utc)).total_seconds()
        if qualified.tzinfo is None or age < -60 or age > 43_200:
            raise ValueError
    except (TypeError, ValueError):
        errors.append("qualified_at_invalid")
    pid = int(receipt.get("process_pid") or -1)
    cmdline = str(receipt.get("process_cmdline") or "")
    if set(receipt.get("packages") or {}) != {"vllm", "torch", "transformers"}:
        errors.append("packages_missing")
    if "vllm" not in cmdline or MODEL_REALPATH not in cmdline or str(PORT) not in cmdline:
        errors.append("cmdline_identity")
    if os.name != "nt":
        proc = Path(f"/proc/{pid}/cmdline")
        observed = proc.read_bytes().replace(b"\0", b" ").decode() if proc.is_file() else ""
        if observed != cmdline:
            errors.append("process_drift")
    if errors:
        raise RuntimeError(f"A1-R14 receipt invalid: {errors}")
    return receipt


def preservation_report(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    observed = {str(row.get("task_name")): row for row in summaries}
    tasks = []
    for name in CAPABILITY_GATE_TASKS:
        row = observed.get(name) or {}
        counters = (((row.get("memory_mechanism") or {}).get("evidence_register") or {}).get("counters") or {})
        silent = int(counters.get("activation_count") or 0) == 0 and int(counters.get("render_count") or 0) == 0
        tasks.append({"task_name": name, "reward": row.get("evaluator_reward"), "rgvr_silent": silent, "pass": row.get("evaluator_reward") == 1.0 and silent})
    count = sum(int(row["pass"]) for row in tasks)
    return {"status": "pass" if count == 6 else "fail", "success_count": count, "required": 6, "tasks": tasks}


def target_gate_report(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    row = next((item for item in summaries if item.get("task_name") == TARGET_GATE_TASK), None)
    if row is None:
        return {"status": "pending", "task_name": TARGET_GATE_TASK, "pass": False}
    memory = row.get("memory_mechanism") or {}
    evidence = memory.get("evidence_register") or {}
    counters = evidence.get("counters") or {}
    response = memory.get("response_grounding") or {}
    response_counters = response.get("counters") or {}
    exact = any(read.get("rendered") and read.get("exact_text") == "TRANSIENT MODEL-AUTHORED EVIDENCE (unverified; current screenshot remains authoritative): observed integer sequence = [1, 8, 10, 7, 2]." for read in evidence.get("read_events") or [])
    passed = bool(row.get("evaluator_reward") == 1.0 and int(counters.get("activation_count") or 0) == 1 and int(counters.get("append_count") or 0) == 5 and int(response_counters.get("append_count") or 0) == 5 and exact)
    return {"status": "pass" if passed else "fail", "task_name": TARGET_GATE_TASK, "pass": passed, "reward": row.get("evaluator_reward"), "activation_count": int(counters.get("activation_count") or 0), "append_count": int(counters.get("append_count") or 0), "response_append_count": int(response_counters.get("append_count") or 0), "exact_five_value_read": exact}


def exact_completion_errors(*, summaries: list[dict[str, Any]], invalid_attempts: list[dict[str, Any]], lifecycle_errors: list[dict[str, Any]]) -> list[str]:
    errors = []
    if len(summaries) != 19 or tuple(str(row.get("task_name")) for row in summaries) != FULL_TASK_ORDER:
        errors.append("task_closure")
    if lifecycle_errors or any(not row.get("resolved_by_episode_id") for row in invalid_attempts):
        errors.append("infrastructure_closure")
    try:
        if any(not math.isfinite(float(row.get("evaluator_reward"))) for row in summaries):
            errors.append("reward_invalid")
    except (TypeError, ValueError):
        errors.append("reward_invalid")
    if preservation_report(summaries)["status"] != "pass":
        errors.append("preservation_gate")
    if target_gate_report(summaries)["status"] != "pass":
        errors.append("target_gate")
    return errors


__all__ = [name for name in globals() if name.isupper()] + ["canonical_sha256", "content_sha256", "exact_completion_errors", "file_sha256", "preservation_report", "source_freeze_payload", "target_gate_report", "validate_launch_receipt", "validate_preflight_report", "validate_source_freeze"]
