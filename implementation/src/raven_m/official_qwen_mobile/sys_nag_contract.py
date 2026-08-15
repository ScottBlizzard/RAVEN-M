"""Fail-closed contract for R2 plus the SYS-NAG V3 composite guards."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Iterator

from . import a1r3_contract as engine
from .a1r2_compact_verified_pending import MECHANISM_ID


SYSTEM_ID = "sys_r2_numeric_terminal_and_route_guard_v4"
EXPERIMENT_ID = "SYS_NAG_V4_R2_QWEN3VL32B_AW_HARD_S20260806_G3407_V1"
MODEL_ID = engine.MODEL_ID
MODEL_REVISION = engine.MODEL_REVISION
MODEL_REALPATH = engine.MODEL_REALPATH
MODEL_MANIFEST_SHA256 = engine.MODEL_MANIFEST_SHA256
TASK_SEED = engine.TASK_SEED
GENERATION_SEED = engine.GENERATION_SEED
PORT = engine.PORT
PARENT_EVIDENCE_COMMIT = "a81d949c12726c965123f07b6c081f8aafdcbafe"
CONFIG_SCHEMA = "sys_nag_v4_r2_composite_guard_config_v1"
OFFLINE_REPLAY_SCHEMA = "sys_nag_v4_offline_replay_v1"
PREFLIGHT_SCHEMA = "sys_nag_v4_zero_generation_preflight_v1"
LIVE_RECEIPT_SCHEMA = "sys_nag_v4_live_server_receipt_v1"
RESULT_SCHEMA = "sys_nag_v4_result_v1"
CHECKPOINT_SCHEMA = "sys_nag_v4_checkpoint_v1"
REPOSITORY_ROOT = engine.REPOSITORY_ROOT
CONFIG_PATH = REPOSITORY_ROOT / "implementation/configs/sys_nag_v4_r2_hard_seed20260806.json"
OFFLINE_REPLAY_PATH = REPOSITORY_ROOT / "evidence/sys_nag_v4/SYS_NAG_V4_OFFLINE_REPLAY_REPORT.json"
REPLAY_FIXTURE_PATH = REPOSITORY_ROOT / "evidence/sys_nag_v4/SYS_NAG_V4_REPLAY_FIXTURE.json"
SOURCE_FREEZE_PATH = REPOSITORY_ROOT / "evidence/sys_nag_v4/SYS_NAG_V4_SOURCE_FREEZE.json"
PREFLIGHT_PATH = REPOSITORY_ROOT / "evidence/sys_nag_v4/SYS_NAG_V4_ZERO_GENERATION_PREFLIGHT.json"

A0_PRESERVATION_TASKS = engine.A0_PRESERVATION_TASKS
RECIPE_TASK = engine.RECIPE_TASK
A1R2_GAIN_TASK = engine.A1R2_GAIN_TASK
CAPABILITY_GATE_TASKS = engine.CAPABILITY_GATE_TASKS
FULL_TASK_ORDER = engine.FULL_TASK_ORDER

SOURCE_FILES = (
    "protocols/SYS_NAG_V4_R2_ROUTE_RECURRENCE_GUARD_PREREG_2026-08-16.md",
    "implementation/configs/sys_nag_v4_r2_hard_seed20260806.json",
    "implementation/configs/androidworld_hard_v2_instances.json",
    "implementation/src/raven_m/official_qwen_mobile/numeric_answer_guard.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r2_compact_verified_pending.py",
    "implementation/src/raven_m/official_qwen_mobile/sys_nag_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r3_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/official_qwen_mobile/protocol.py",
    "implementation/src/raven_m/official_qwen_mobile/working_memory.py",
    "implementation/src/raven_m/models/vllm_client.py",
    "implementation/src/raven_m/env/androidworld_adapter.py",
    "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/run_sys_nag.py",
    "implementation/scripts/replay_sys_nag.py",
    "implementation/scripts/preflight_sys_nag.py",
    "implementation/scripts/qualify_sys_nag_server.py",
    "implementation/scripts/qualify_a1r5_tipl_server.py",
    "implementation/scripts/start_sys_nag_server.sh",
    "implementation/scripts/finalize_sys_nag_v2_terminal.py",
    "implementation/tests/official_qwen_mobile/test_numeric_answer_guard.py",
    "implementation/tests/official_qwen_mobile/test_sys_nag_contract.py",
    "implementation/tests/official_qwen_mobile/test_sys_nag_controller_integration.py",
    "implementation/tests/official_qwen_mobile/test_sys_nag_v2_terminal_finalizer.py",
    "evidence/sys_nag_v4/SYS_NAG_V4_REPLAY_FIXTURE.json",
    "evidence/sys_nag_v4/SYS_NAG_V4_OFFLINE_REPLAY_REPORT.json",
    "evidence/sys_nag_v3/SYS_NAG_V3_TERMINAL_SUMMARY_2026-08-16.json",
)

EXPECTED_CONFIG = {
    "schema": CONFIG_SCHEMA,
    "mechanism_id": MECHANISM_ID,
    "system_id": SYSTEM_ID,
    "experiment_id": EXPERIMENT_ID,
    "task_seed": TASK_SEED,
    "generation_seed": GENERATION_SEED,
    "model_id": MODEL_ID,
    "model_revision": MODEL_REVISION,
    "memory": {
        "kind": "exact_a1r2_compact_verified_pending",
        "ttl_requests": 8,
        "max_render_chars": 1100,
    },
    "numeric_answer_guard": {
        "enabled": True,
        "answer_type": "single_integer_only",
        "evidence_source": "current_model_action_summary_only",
        "operation": "sum_two_or_more_explicit_durations",
    },
    "pending_terminal_guard": {
        "enabled": True,
        "terminal_status": "success_only",
        "pending_source": "exact_r2_text_injected_into_same_request",
        "previous_executed_action_type": "wait",
        "minimum_remaining_native_decision_slots": 1,
        "max_blocks_per_episode": 1,
        "effect": "reject_terminal_without_executing_android_action",
    },
    "route_recurrence_guard": {
        "enabled": True,
        "pending_source": "exact_r2_text_injected_into_same_request",
        "exploratory_cues": ["explore", "look for", "alternative", "try", "search for"],
        "same_pending_screen_action_supports": 3,
        "screen_match": "a12_exact_or_near",
        "max_route_groups": 8,
        "shared_max_blocks_with_terminal_guard": 1,
        "minimum_remaining_native_decision_slots": 1,
    },
    "decision_boundary": {
        "auxiliary_model_calls": 0,
        "max_guard_induced_continuation_normal_requests": 1,
        "task_name_rules": False,
        "evaluator_access": False,
        "hidden_ui_access": False,
    },
    "orchestration": {
        "a0_gate_tasks": 4,
        "capability_gate_tasks": 6,
        "release_remaining_after": 6,
    },
}

file_sha256 = engine.file_sha256
canonical_sha256 = engine.canonical_sha256
content_sha256 = engine.content_sha256

_PATCH = {
    name: globals()[name]
    for name in (
        "MECHANISM_ID", "EXPERIMENT_ID", "PARENT_EVIDENCE_COMMIT",
        "CONFIG_SCHEMA", "OFFLINE_REPLAY_SCHEMA", "PREFLIGHT_SCHEMA",
        "LIVE_RECEIPT_SCHEMA", "RESULT_SCHEMA", "CHECKPOINT_SCHEMA",
        "CONFIG_PATH", "OFFLINE_REPLAY_PATH", "SOURCE_FREEZE_PATH",
        "PREFLIGHT_PATH", "SOURCE_FILES",
    )
}


@contextmanager
def _patched() -> Iterator[None]:
    old = {key: getattr(engine, key) for key in _PATCH}
    try:
        for key, value in _PATCH.items():
            setattr(engine, key, value)
        yield
    finally:
        for key, value in old.items():
            setattr(engine, key, value)


def source_freeze_payload(implementation_commit: str) -> dict[str, Any]:
    with _patched():
        return engine.source_freeze_payload(implementation_commit)


def validate_source_freeze(path: Path = SOURCE_FREEZE_PATH) -> dict[str, Any]:
    with _patched():
        return engine.validate_source_freeze(path)


def validate_preflight_report(path: Path = PREFLIGHT_PATH) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    freeze = validate_source_freeze(SOURCE_FREEZE_PATH)
    replay = json.loads(OFFLINE_REPLAY_PATH.read_text(encoding="utf-8"))
    fixture = json.loads(REPLAY_FIXTURE_PATH.read_text(encoding="utf-8"))
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    expected = {
        "schema": PREFLIGHT_SCHEMA,
        "status": "PASS",
        "errors": [],
        "generation_calls": 0,
        "live_generation_authorized": True,
        "mechanism_id": MECHANISM_ID,
        "system_id": SYSTEM_ID,
        "experiment_id": EXPERIMENT_ID,
        "implementation_commit": freeze["implementation_commit"],
        "source_freeze_content_sha256": freeze["content_sha256"],
        "offline_replay_content_sha256": replay.get("content_sha256"),
    }
    errors = [key + "_drift" for key, value in expected.items() if report.get(key) != value]
    if config != EXPECTED_CONFIG:
        errors.append("config_semantic_drift")
    if report.get("content_sha256") != content_sha256(report):
        errors.append("preflight_content_hash")
    regression = replay.get("numeric_failure_regression") or {}
    terminal_regression = replay.get("terminal_failure_regression") or {}
    route_regression = replay.get("route_failure_regression") or {}
    if (
        replay.get("schema") != OFFLINE_REPLAY_SCHEMA
        or replay.get("status") != "PASS"
        or replay.get("errors") != []
        or replay.get("generation_calls") != 0
        or replay.get("mechanism_id") != MECHANISM_ID
        or replay.get("system_id") != SYSTEM_ID
        or replay.get("content_sha256") != content_sha256(replay)
        or int((replay.get("totals") or {}).get("valid_episode_count") or 0) != 19
        or regression.get("corrected_action") != {"type": "answer", "text": "180"}
        or not bool((regression.get("event") or {}).get("overridden"))
        or not bool((terminal_regression.get("event") or {}).get("blocked"))
        or len(route_regression.get("blocked_events") or []) != 1
        or int(((route_regression.get("blocked_events") or [{}])[0]).get("step") or -1) != 39
        or int((replay.get("totals") or {}).get("historical_success_route_block_count", -1)) != 0
        or int(
            (replay.get("totals") or {}).get(
                "historical_terminal_block_count", -1
            )
        )
        != 0
        or fixture.get("schema") != "sys_nag_v4_replay_fixture_v1"
        or fixture.get("generation_calls") != 0
        or fixture.get("content_sha256") != content_sha256(fixture)
        or (replay.get("source") or {}).get("fixture_content_sha256")
        != fixture.get("content_sha256")
    ):
        errors.append("offline_replay_not_authorizing")
    if errors:
        raise RuntimeError(f"SYS-NAG V4 preflight invalid: {errors}")
    return report


def validate_launch_receipt(
    path: Path, *, preflight_path: Path = PREFLIGHT_PATH
) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    preflight = validate_preflight_report(preflight_path)
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    expected = {
        "schema": LIVE_RECEIPT_SCHEMA,
        "status": "PASS",
        "errors": [],
        "generation_calls": 0,
        "mechanism_id": MECHANISM_ID,
        "system_id": SYSTEM_ID,
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
    packages = receipt.get("packages") or {}
    if set(packages) != {"vllm", "torch", "transformers"} or any(
        not str(value) for value in packages.values()
    ):
        errors.append("packages_missing")
    if receipt.get("content_sha256") != content_sha256(receipt):
        errors.append("receipt_content_hash")
    try:
        qualified = datetime.fromisoformat(str(receipt.get("qualified_at")))
        age = (datetime.now(timezone.utc) - qualified.astimezone(timezone.utc)).total_seconds()
        if qualified.tzinfo is None or age < -60 or age > 43200:
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
        raise RuntimeError(f"SYS-NAG V4 launch receipt invalid: {errors}")
    return receipt


def preservation_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    return engine.preservation_report(items)


def exact_completion_errors(**kwargs: Any) -> list[str]:
    errors = engine.exact_completion_errors(**kwargs)
    for summary in kwargs.get("summaries") or []:
        guard = summary.get("answer_consistency_guard")
        counters = (guard or {}).get("counters") if isinstance(guard, dict) else {}
        if (
            not isinstance(guard, dict)
            or guard.get("schema") != "sys_nag_v4_composite_guard_audit_v1"
            or guard.get("system_id") != SYSTEM_ID
        ):
            errors.append(f"answer_guard_missing:{summary.get('task_name')}")
            continue
        if (
            int((counters or {}).get("terminal_block_count") or 0) not in {0, 1}
            or int((counters or {}).get("route_block_count") or 0) not in {0, 1}
            or int((counters or {}).get("terminal_block_count") or 0)
            + int((counters or {}).get("route_block_count") or 0)
            > 1
            or int((counters or {}).get("auxiliary_model_call_count") or 0) != 0
            or int(
                (counters or {}).get(
                    "guard_induced_continuation_request_upper_bound"
                )
                or 0
            )
            not in {0, 1}
            or int((counters or {}).get("forced_termination_count") or 0) != 0
            or bool((counters or {}).get("hidden_ui_used_for_decision"))
            or bool((counters or {}).get("evaluator_used_for_decision"))
        ):
            errors.append(f"composite_guard_boundary:{summary.get('task_name')}")
    return errors


__all__ = [name for name in globals() if name.isupper()] + [
    "canonical_sha256", "content_sha256", "exact_completion_errors",
    "file_sha256", "preservation_report", "source_freeze_payload",
    "validate_launch_receipt", "validate_preflight_report",
    "validate_source_freeze",
]
