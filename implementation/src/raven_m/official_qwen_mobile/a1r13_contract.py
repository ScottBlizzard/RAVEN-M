"""Fail-closed contract for prospective A1-R13 EVR."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Any

from .a1r13_evidence_value_register import EXPERIMENT_ID, MECHANISM_ID
from . import a1r3_contract as base


MODEL_ID = base.MODEL_ID
MODEL_REVISION = base.MODEL_REVISION
MODEL_REALPATH = base.MODEL_REALPATH
MODEL_MANIFEST_SHA256 = base.MODEL_MANIFEST_SHA256
TASK_SEED = base.TASK_SEED
GENERATION_SEED = base.GENERATION_SEED
PORT = base.PORT
PARENT_EVIDENCE_COMMIT = "aa3176286a65c16becb59772cce1d742f13d441c"
CONFIG_SCHEMA = "a1r13_evr_config_v1"
OFFLINE_REPLAY_SCHEMA = "a1r13_evr_offline_replay_v1"
PREFLIGHT_SCHEMA = "a1r13_evr_zero_generation_preflight_v1"
LIVE_RECEIPT_SCHEMA = "a1r13_evr_live_server_receipt_v1"
CHECKPOINT_SCHEMA = "a1r13_evr_checkpoint_v1"
RESULT_SCHEMA = "a1r13_evr_result_v1"
REPOSITORY_ROOT = base.REPOSITORY_ROOT
CONFIG_PATH = REPOSITORY_ROOT / "implementation/configs/a1r13_evr_hard_seed20260806.json"
FIXTURE_PATH = REPOSITORY_ROOT / "evidence/a1r13/A1R13_EVR_REPLAY_FIXTURE.json"
OFFLINE_REPLAY_PATH = REPOSITORY_ROOT / "evidence/a1r13/A1R13_EVR_OFFLINE_REPLAY_REPORT.json"
SOURCE_FREEZE_PATH = REPOSITORY_ROOT / "evidence/a1r13/A1R13_EVR_SOURCE_FREEZE.json"
PREFLIGHT_PATH = REPOSITORY_ROOT / "evidence/a1r13/A1R13_EVR_ZERO_GENERATION_PREFLIGHT.json"
A0_PRESERVATION_TASKS = base.A0_PRESERVATION_TASKS
RECIPE_TASK = base.RECIPE_TASK
A1R2_GAIN_TASK = base.A1R2_GAIN_TASK
CAPABILITY_GATE_TASKS = base.CAPABILITY_GATE_TASKS
TARGET_GATE_TASK = "BrowserMultiply"
FULL_TASK_ORDER = base.FULL_TASK_ORDER

SOURCE_FILES = (
    "protocols/A1R13_EVIDENCE_VALUE_REGISTER_PREREG_2026-08-18.md",
    "implementation/configs/a1r13_evr_hard_seed20260806.json",
    "implementation/configs/androidworld_hard_v2_instances.json",
    "implementation/src/raven_m/official_qwen_mobile/a1r13_evidence_value_register.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r13_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r2_compact_verified_pending.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/official_qwen_mobile/protocol.py",
    "implementation/src/raven_m/official_qwen_mobile/working_memory.py",
    "implementation/src/raven_m/models/vllm_client.py",
    "implementation/src/raven_m/env/androidworld_adapter.py",
    "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/run_a1r13_evr.py",
    "implementation/scripts/materialize_a1r13_evr_fixture.py",
    "implementation/scripts/replay_a1r13_evidence_value_register.py",
    "implementation/scripts/preflight_a1r13_evr.py",
    "implementation/scripts/qualify_a1r13_evr_server.py",
    "implementation/scripts/start_a1r13_evr_server.sh",
    "implementation/tests/official_qwen_mobile/test_a1r13_evidence_value_register.py",
    "implementation/tests/official_qwen_mobile/test_a1r13_contract.py",
    "implementation/tests/official_qwen_mobile/test_a1r13_controller_integration.py",
    "implementation/tests/official_qwen_mobile/test_a1r13_offline_replay.py",
    "evidence/a1r13/A1R13_EVR_REPLAY_FIXTURE.json",
    "evidence/a1r13/A1R13_EVR_OFFLINE_REPLAY_REPORT.json",
    "evidence/sys_nag_v4/SYS_NAG_V4_COMPLETE_RESULT_2026-08-18.json",
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
    },
    "decision_boundary": {
        "extra_model_calls": 0,
        "action_override_count": 0,
        "forced_termination_count": 0,
        "task_name_rules": False,
        "screen_text_or_ocr_used": False,
        "hidden_ui_used": False,
        "evaluator_used": False,
    },
    "orchestration": {
        "capability_gate_tasks": 6,
        "target_gate_task": TARGET_GATE_TASK,
        "release_remaining_after": 7,
    },
}


def canonical_sha256(value: Any) -> str:
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def content_sha256(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("content_sha256", None)
    return canonical_sha256(payload)


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(REPOSITORY_ROOT), *args], text=True
    ).strip()


def source_freeze_payload(implementation_commit: str) -> dict[str, Any]:
    if len(implementation_commit) != 40 or any(ch not in "0123456789abcdef" for ch in implementation_commit):
        raise RuntimeError("A1-R13 implementation commit invalid")
    if subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), "merge-base", "--is-ancestor", PARENT_EVIDENCE_COMMIT, implementation_commit],
        capture_output=True,
    ).returncode:
        raise RuntimeError("A1-R13 parent evidence is not an ancestor")
    files: dict[str, str] = {}
    for name in SOURCE_FILES:
        path = REPOSITORY_ROOT / name
        if not path.is_file():
            raise RuntimeError(f"A1-R13 source closure missing: {name}")
        try:
            blob = subprocess.check_output(
                ["git", "-C", str(REPOSITORY_ROOT), "show", f"{implementation_commit}:{name}"]
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"A1-R13 source absent from implementation commit: {name}") from exc
        if _git("hash-object", "--path", name, str(path)) != _git("rev-parse", f"{implementation_commit}:{name}"):
            raise RuntimeError(f"A1-R13 current source drift: {name}")
        files[name] = sha256(blob).hexdigest()
    payload = {
        "schema": "a1r13_evr_source_freeze_v1",
        "implementation_commit": implementation_commit,
        "parent_evidence_commit": PARENT_EVIDENCE_COMMIT,
        "files": files,
    }
    return {**payload, "content_sha256": content_sha256(payload)}


def validate_source_freeze(path: Path = SOURCE_FREEZE_PATH) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    expected = source_freeze_payload(str(report.get("implementation_commit") or ""))
    if report != expected:
        raise RuntimeError("A1-R13 source freeze mismatch")
    return report


def _replay_valid(replay: dict[str, Any]) -> bool:
    totals = replay.get("totals") or {}
    target = replay.get("browser_target") or {}
    return bool(
        replay.get("schema") == OFFLINE_REPLAY_SCHEMA
        and replay.get("status") == "PASS"
        and replay.get("errors") == []
        and replay.get("generation_calls") == 0
        and replay.get("mechanism_id") == MECHANISM_ID
        and replay.get("experiment_id") == EXPERIMENT_ID
        and replay.get("content_sha256") == content_sha256(replay)
        and int(totals.get("episode_count") or 0) == 19
        and int(totals.get("step_count") or 0) == 558
        and int(totals.get("active_episode_count") or 0) == 1
        and int(totals.get("activation_count") or 0) == 1
        and int(totals.get("append_count") or 0) == 5
        and int(totals.get("six_success_active_count", -1)) == 0
        and int(totals.get("max_v5_render_chars") or 10**9) <= 1100
        and int(totals.get("max_serialized_audit_bytes") or 10**9) <= 131_072
        and target.get("expected_model_authored_values") == ["1", "8", "10", "7", "2"]
        and int(target.get("pre_product_request_step") or -1) == 18
    )


def validate_preflight_report(path: Path = PREFLIGHT_PATH) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    freeze = validate_source_freeze(SOURCE_FREEZE_PATH)
    replay = json.loads(OFFLINE_REPLAY_PATH.read_text(encoding="utf-8"))
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
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
        "offline_replay_content_sha256": replay.get("content_sha256"),
        "fixture_content_sha256": fixture.get("content_sha256"),
    }
    errors = [key + "_drift" for key, value in expected.items() if report.get(key) != value]
    if report.get("content_sha256") != content_sha256(report):
        errors.append("preflight_content_hash")
    if config != EXPECTED_CONFIG:
        errors.append("config_semantic_drift")
    if fixture.get("schema") != "a1r13_evr_replay_fixture_v1" or fixture.get("content_sha256") != content_sha256(fixture):
        errors.append("fixture_invalid")
    if not _replay_valid(replay):
        errors.append("offline_replay_not_authorizing")
    checks = report.get("checks") or {}
    if checks.get("focused_tests") != {"returncode": 0, "passed": True}:
        errors.append("focused_tests_missing")
    if errors:
        raise RuntimeError(f"A1-R13 preflight invalid: {errors}")
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
        "preflight_content_sha256": preflight["content_sha256"],
        "config_content_sha256": canonical_sha256(config),
        "served_model_id": MODEL_ID,
        "served_model_ids_observed": [MODEL_ID],
        "model_realpath": MODEL_REALPATH,
        "model_manifest_sha256": MODEL_MANIFEST_SHA256,
        "port": PORT,
    }
    errors = [key + "_drift" for key, value in expected.items() if receipt.get(key) != value]
    if receipt.get("content_sha256") != content_sha256(receipt):
        errors.append("receipt_content_hash")
    packages = receipt.get("packages") or {}
    if set(packages) != {"vllm", "torch", "transformers"} or any(not str(v) for v in packages.values()):
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
        raise RuntimeError(f"A1-R13 receipt invalid: {errors}")
    return receipt


def preservation_report(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    observed = {str(item.get("task_name")): item for item in summaries}
    tasks = []
    for name in CAPABILITY_GATE_TASKS:
        summary = observed.get(name) or {}
        evidence = ((summary.get("memory_mechanism") or {}).get("evidence_register") or {})
        counters = evidence.get("counters") or {}
        silent = int(counters.get("activation_count") or 0) == 0 and int(counters.get("render_count") or 0) == 0
        tasks.append({
            "task_name": name,
            "reward": summary.get("evaluator_reward"),
            "evr_silent": silent,
            "pass": summary.get("evaluator_reward") == 1.0 and silent,
        })
    count = sum(int(row["pass"]) for row in tasks)
    return {"status": "pass" if count == 6 else "fail", "success_count": count, "required": 6, "tasks": tasks}


def target_gate_report(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    summary = next((item for item in summaries if item.get("task_name") == TARGET_GATE_TASK), None)
    if summary is None:
        return {"status": "pending", "task_name": TARGET_GATE_TASK, "pass": False}
    evidence = ((summary.get("memory_mechanism") or {}).get("evidence_register") or {})
    counters = evidence.get("counters") or {}
    expected = "TRANSIENT MODEL-AUTHORED EVIDENCE (unverified; current screenshot remains authoritative): observed integer sequence = [1, 8, 10, 7, 2]."
    exact_read = any(
        row.get("rendered") and row.get("exact_text") == expected
        for row in evidence.get("read_events") or []
    )
    passed = bool(
        summary.get("evaluator_reward") == 1.0
        and int(counters.get("activation_count") or 0) == 1
        and int(counters.get("append_count") or 0) == 5
        and int(counters.get("render_count") or 0) >= 1
        and exact_read
    )
    return {
        "status": "pass" if passed else "fail",
        "task_name": TARGET_GATE_TASK,
        "pass": passed,
        "reward": summary.get("evaluator_reward"),
        "activation_count": int(counters.get("activation_count") or 0),
        "append_count": int(counters.get("append_count") or 0),
        "render_count": int(counters.get("render_count") or 0),
        "exact_five_value_read": exact_read,
    }


def exact_completion_errors(*, summaries: list[dict[str, Any]], invalid_attempts: list[dict[str, Any]], lifecycle_errors: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if len(summaries) != 19:
        errors.append("valid_episode_count")
    if tuple(str(item.get("task_name")) for item in summaries) != FULL_TASK_ORDER:
        errors.append("task_order")
    if any(int(item.get("seed") or -1) != TASK_SEED for item in summaries):
        errors.append("task_seed")
    if lifecycle_errors or any(not row.get("resolved_by_episode_id") for row in invalid_attempts):
        errors.append("unresolved_infrastructure")
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
        boundary = (item.get("memory_mechanism") or {}).get("decision_boundary") or {}
        if (
            int(boundary.get("extra_model_calls") or 0)
            or int(boundary.get("action_override_count") or 0)
            or int(boundary.get("forced_termination_count") or 0)
            or bool(boundary.get("hidden_ui_used_for_decision"))
            or bool(boundary.get("evaluator_used_for_decision"))
        ):
            errors.append(f"intervention_boundary:{item.get('task_name')}")
    if preservation_report(summaries).get("status") != "pass":
        errors.append("preservation_gate")
    if target_gate_report(summaries).get("status") != "pass":
        errors.append("target_gate")
    return errors


__all__ = [name for name in globals() if name.isupper()] + [
    "canonical_sha256", "content_sha256", "exact_completion_errors",
    "file_sha256", "preservation_report", "source_freeze_payload",
    "target_gate_report", "validate_launch_receipt",
    "validate_preflight_report", "validate_source_freeze",
]
