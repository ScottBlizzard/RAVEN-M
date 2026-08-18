"""Fail-closed contract for prospective stabilized SYS-R2-LRER V2.

Generated artifacts (source freeze, preflight, receipt, checkpoint, and result)
are outputs of this contract and are intentionally absent from ``SOURCE_FILES``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Any

from .a1r2_compact_verified_pending import MECHANISM_ID
from .r15_derived_evidence_consolidation_v2 import (
    EXPERIMENT_ID,
    POST_ACTION_SETTLE_SECONDS,
    SYSTEM_ID,
)
from .sys_trrc_token_budget import PROCESSOR_RUNTIME_PACKAGES


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
MODEL_REALPATH = "/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope"
MODEL_MANIFEST_SHA256 = "18e0909c7d993853d6d0f62443461a74009754f90db026a1723cab80121c7872"
PARENT_EVIDENCE_COMMIT = "46d9248fdc96721862ba4d919381846d250d960c"
TASK_SEED = 20260806
GENERATION_SEED = 3407
PORT = 18000
CONFIG_SCHEMA = "sys_r2_lrer_v2_config_v1"
OFFLINE_REPLAY_SCHEMA = "sys_r2_lrer_v2_offline_replay_v1"
REPLAY_FIXTURE_SCHEMA = "sys_r2_lrer_v2_replay_fixture_v1"
SOURCE_FREEZE_SCHEMA = "sys_r2_lrer_v2_source_freeze_v1"
PREFLIGHT_SCHEMA = "sys_r2_lrer_v2_zero_generation_preflight_v1"
LIVE_RECEIPT_SCHEMA = "sys_r2_lrer_v2_live_server_receipt_v1"
CHECKPOINT_SCHEMA = "sys_r2_lrer_v2_checkpoint_v1"
RESULT_SCHEMA = "sys_r2_lrer_v2_result_v1"

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
CONFIG_PATH = REPOSITORY_ROOT / "implementation/configs/sys_r2_lrer_v2_hard_seed20260806.json"
REPLAY_FIXTURE_PATH = REPOSITORY_ROOT / "evidence/sys_r2_lrer_v2/SYS_R2_LRER_V2_REPLAY_FIXTURE.json"
OFFLINE_REPLAY_PATH = REPOSITORY_ROOT / "evidence/sys_r2_lrer_v2/SYS_R2_LRER_V2_OFFLINE_REPLAY_REPORT.json"
SOURCE_FREEZE_PATH = REPOSITORY_ROOT / "evidence/sys_r2_lrer_v2/SYS_R2_LRER_V2_SOURCE_FREEZE.json"
PREFLIGHT_PATH = REPOSITORY_ROOT / "evidence/sys_r2_lrer_v2/SYS_R2_LRER_V2_ZERO_GENERATION_PREFLIGHT.json"
R2_RESULT_PATH = REPOSITORY_ROOT / "evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.json"

SEVEN_TASK_ORDER = (
    "BrowserMultiply",
    "ExpenseDeleteMultiple2",
    "RetroSavePlaylist",
    "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
    "RecipeDeleteMultipleRecipesWithConstraint",
    "OsmAndMarker",
)
CAPABILITY_GATE_TASKS = SEVEN_TASK_ORDER
FULL_TASK_ORDER = SEVEN_TASK_ORDER + (
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

# Exact prospective source plan. Generated outputs are deliberately excluded.
SOURCE_FILES = (
    "protocols/SYS_R2_STABILIZED_LRER_V2_PREREG_2026-08-18.md",
    "implementation/configs/sys_r2_lrer_v2_hard_seed20260806.json",
    "implementation/configs/androidworld_hard_v2_instances.json",
    "implementation/src/raven_m/official_qwen_mobile/r15_derived_evidence_consolidation.py",
    "implementation/src/raven_m/official_qwen_mobile/r15_derived_evidence_consolidation_v2.py",
    "implementation/src/raven_m/official_qwen_mobile/sys_r2_lrer_v2_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r2_compact_verified_pending.py",
    "implementation/src/raven_m/androidworld_compat.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/official_qwen_mobile/protocol.py",
    "implementation/src/raven_m/official_qwen_mobile/working_memory.py",
    "implementation/src/raven_m/official_qwen_mobile/sys_trrc_token_budget.py",
    "implementation/src/raven_m/models/vllm_client.py",
    "implementation/src/raven_m/env/androidworld_adapter.py",
    "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/materialize_sys_r2_lrer_v2_fixture.py",
    "implementation/scripts/replay_sys_r2_lrer_v2.py",
    "implementation/scripts/materialize_sys_r2_lrer_fixture.py",
    "implementation/scripts/replay_sys_r2_lrer.py",
    "implementation/scripts/preflight_sys_r2_lrer_v2.py",
    "implementation/scripts/qualify_sys_r2_lrer_v2_server.py",
    "implementation/scripts/start_sys_r2_lrer_v2_server.sh",
    "implementation/scripts/run_sys_r2_lrer_v2.py",
    "implementation/tests/official_qwen_mobile/test_r15_derived_evidence_consolidation.py",
    "implementation/tests/official_qwen_mobile/test_sys_r2_lrer_v2_contract.py",
    "implementation/tests/official_qwen_mobile/test_sys_r2_lrer_v2_controller_integration.py",
    "implementation/tests/official_qwen_mobile/test_sys_r2_lrer_v2_offline_replay.py",
    "evidence/sys_r2_lrer_v2/SYS_R2_LRER_V2_REPLAY_FIXTURE.json",
    "evidence/sys_r2_lrer_v2/SYS_R2_LRER_V2_OFFLINE_REPLAY_REPORT.json",
    "evidence/sys_r2_lrer_v2/source_episodes/sys_r2_lrer_v1_browser_failure.json",
    "evidence/sys_r2_lrer/SYS_R2_LRER_REPLAY_FIXTURE.json",
    "evidence/r15_browser_forensics/R15_BROWSER_FORENSIC_2026-08-18.json",
    "evidence/a1r15/A1R15_EOVR_TERMINAL_RESULT_2026-08-18.json",
    "evidence/a1r2/A1R2_CVP_SCORED_RESULT_2026-08-14.json",
)

EXPECTED_CONFIG = {
    "schema": CONFIG_SCHEMA,
    "system_id": SYSTEM_ID,
    "experiment_id": EXPERIMENT_ID,
    "parent_mechanism_id": MECHANISM_ID,
    "task_seed": TASK_SEED,
    "generation_seed": GENERATION_SEED,
    "min_eligibility_fraction": [7, 10],
    "result_action_families": ["type_text", "answer", "terminate_success"],
    "max_raw_actions": 8,
    "max_action_chars": 700,
    "max_total_raw_chars": 4000,
    "max_render_chars": 5400,
    "max_deferrals_per_episode": 1,
    "post_action_settle_seconds": POST_ACTION_SETTLE_SECONDS,
    "post_action_state_capture_count": 1,
    "auxiliary_model_calls": 0,
    "native_budget_increase": 0,
    "non_fail_fast_seven": True,
    "seven_task_order": list(SEVEN_TASK_ORDER),
    "full_suite_release_requires": "7/7",
}


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def content_sha256(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("content_sha256", None)
    return canonical_sha256(payload)


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(REPOSITORY_ROOT), *args], text=True
    ).strip()


def source_freeze_payload(implementation_commit: str) -> dict[str, Any]:
    if len(implementation_commit) != 40 or any(
        character not in "0123456789abcdef" for character in implementation_commit
    ):
        raise RuntimeError("SYS-R2-LRER implementation commit invalid")
    if subprocess.run(
        [
            "git",
            "-C",
            str(REPOSITORY_ROOT),
            "merge-base",
            "--is-ancestor",
            PARENT_EVIDENCE_COMMIT,
            implementation_commit,
        ],
        capture_output=True,
    ).returncode:
        raise RuntimeError("SYS-R2-LRER parent evidence is not an ancestor")
    files: dict[str, str] = {}
    for name in SOURCE_FILES:
        path = REPOSITORY_ROOT / name
        if not path.is_file():
            raise RuntimeError(f"SYS-R2-LRER source closure missing: {name}")
        try:
            frozen = subprocess.check_output(
                ["git", "-C", str(REPOSITORY_ROOT), "show", f"{implementation_commit}:{name}"]
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"SYS-R2-LRER source absent from implementation commit: {name}"
            ) from exc
        if _git("hash-object", "--path", name, str(path)) != _git(
            "rev-parse", f"{implementation_commit}:{name}"
        ):
            raise RuntimeError(f"SYS-R2-LRER current source drift: {name}")
        files[name] = sha256(frozen).hexdigest()
    payload = {
        "schema": SOURCE_FREEZE_SCHEMA,
        "implementation_commit": implementation_commit,
        "parent_evidence_commit": PARENT_EVIDENCE_COMMIT,
        "files": files,
    }
    return {**payload, "content_sha256": content_sha256(payload)}


def validate_source_freeze(path: Path = SOURCE_FREEZE_PATH) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report != source_freeze_payload(str(report.get("implementation_commit") or "")):
        raise RuntimeError("SYS-R2-LRER source freeze mismatch")
    if subprocess.run(
        [
            "git",
            "-C",
            str(REPOSITORY_ROOT),
            "merge-base",
            "--is-ancestor",
            report["implementation_commit"],
            _git("rev-parse", "HEAD"),
        ],
        capture_output=True,
    ).returncode:
        raise RuntimeError("SYS-R2-LRER implementation is not an ancestor of HEAD")
    return report


def _replay_valid(report: dict[str, Any]) -> bool:
    browser = report.get("browser") or {}
    success_rows = report.get("historical_successes") or []
    return bool(
        report.get("schema") == OFFLINE_REPLAY_SCHEMA
        and report.get("status") == "PASS"
        and report.get("errors") == []
        and report.get("generation_calls") == 0
        and report.get("system_id") == SYSTEM_ID
        and report.get("experiment_id") == EXPERIMENT_ID
        and report.get("fixed_seven") == list(SEVEN_TASK_ORDER)
        and report.get("content_sha256") == content_sha256(report)
        and int((report.get("totals") or {}).get("r15_browser_lrer_opportunity_count") or 0) == 1
        and int((report.get("totals") or {}).get("r2_browser_lrer_opportunity_count") or 0) == 1
        and int((report.get("totals") or {}).get("sealed_live_browser_lrer_opportunity_count") or 0) == 0
        and (report.get("development_live_browser") or {}).get("cross_activity_stale_capture_steps") == [3, 7]
        and len(success_rows) == 6
        and [str(row.get("task_name")) for row in success_rows]
        == list(SEVEN_TASK_ORDER[1:])
        and all(int(row.get("lrer_opportunity_count") or 0) == 0 for row in success_rows)
    )


def local_processor_identity(projector: Any) -> dict[str, Any]:
    python_executable = Path(projector.python_executable).resolve()
    processor_path = Path(projector.model_path).resolve()
    payload = {
        "schema": "sys_r2_lrer_v2_local_processor_identity_v1",
        "python_executable": str(python_executable),
        "python_executable_sha256": file_sha256(python_executable),
        "processor_path": str(processor_path),
        "processor_files_sha256": dict(projector.processor_files_sha256),
        "runtime_identity": dict(projector.runtime_identity),
    }
    return {**payload, "content_sha256": content_sha256(payload)}


def _local_processor_identity_valid(identity: dict[str, Any]) -> bool:
    runtime = identity.get("runtime_identity") or {}
    processor_files = identity.get("processor_files_sha256") or {}
    return bool(
        identity.get("schema") == "sys_r2_lrer_v2_local_processor_identity_v1"
        and identity.get("content_sha256") == content_sha256(identity)
        and len(str(identity.get("python_executable_sha256") or "")) == 64
        and str(identity.get("python_executable") or "")
        and str(identity.get("processor_path") or "")
        and isinstance(processor_files, dict)
        and processor_files
        and all(
            str(name) and len(str(digest)) == 64
            for name, digest in processor_files.items()
        )
        and runtime.get("schema") == "sys_trrc_local_processor_runtime_v1"
        and runtime.get("python_executable_sha256")
        == identity.get("python_executable_sha256")
        and set(runtime.get("packages") or {}) == set(PROCESSOR_RUNTIME_PACKAGES)
    )


def validate_preflight_report(
    path: Path = PREFLIGHT_PATH, *, projector: Any | None = None
) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    freeze = validate_source_freeze()
    replay = json.loads(OFFLINE_REPLAY_PATH.read_text(encoding="utf-8"))
    fixture = json.loads(REPLAY_FIXTURE_PATH.read_text(encoding="utf-8"))
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
        "fixture_content_sha256": fixture.get("content_sha256"),
    }
    errors = [
        f"{key}_drift" for key, value in expected.items() if report.get(key) != value
    ]
    if report.get("content_sha256") != content_sha256(report):
        errors.append("preflight_content_hash")
    if json.loads(CONFIG_PATH.read_text(encoding="utf-8")) != EXPECTED_CONFIG:
        errors.append("config_drift")
    if (
        fixture.get("schema") != REPLAY_FIXTURE_SCHEMA
        or fixture.get("content_sha256") != content_sha256(fixture)
    ):
        errors.append("fixture_invalid")
    if replay.get("fixture_content_sha256") != fixture.get("content_sha256"):
        errors.append("offline_replay_fixture_drift")
    if not _replay_valid(replay):
        errors.append("offline_replay_not_authorizing")
    if (report.get("checks") or {}).get("focused_tests") != {
        "returncode": 0,
        "passed": True,
    }:
        errors.append("focused_tests_missing")
    processor_identity = (report.get("checks") or {}).get("local_processor_identity") or {}
    if not _local_processor_identity_valid(processor_identity):
        errors.append("local_processor_identity_invalid")
    elif projector is not None and processor_identity != local_processor_identity(projector):
        errors.append("local_processor_identity_runtime_drift")
    processor_smoke = (report.get("checks") or {}).get("exact_text_delta_smoke") or {}
    if (
        processor_smoke.get("base_text_sha256")
        != canonical_sha256("SYS-R2-LRER-V2 base prompt")
        or processor_smoke.get("final_text_sha256")
        != canonical_sha256("SYS-R2-LRER-V2 base prompt\nLRER evidence")
        or int(processor_smoke.get("exact_delta_tokens") or 0) < 1
    ):
        errors.append("exact_text_delta_smoke_invalid")
    if errors:
        raise RuntimeError(f"SYS-R2-LRER preflight invalid: {errors}")
    return report


def validate_launch_receipt(
    path: Path, *, preflight_path: Path = PREFLIGHT_PATH
) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    preflight = validate_preflight_report(preflight_path)
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
        "config_content_sha256": canonical_sha256(EXPECTED_CONFIG),
        "served_model_id": MODEL_ID,
        "served_model_ids_observed": [MODEL_ID],
        "model_realpath": MODEL_REALPATH,
        "model_manifest_sha256": MODEL_MANIFEST_SHA256,
        "port": PORT,
    }
    errors = [
        f"{key}_drift" for key, value in expected.items() if receipt.get(key) != value
    ]
    if receipt.get("content_sha256") != content_sha256(receipt):
        errors.append("receipt_content_hash")
    packages = receipt.get("packages") or {}
    if set(packages) != {"vllm", "torch", "transformers"} or any(
        not str(value) for value in packages.values()
    ):
        errors.append("packages_missing")
    try:
        qualified = datetime.fromisoformat(str(receipt.get("qualified_at")))
        if qualified.tzinfo is None:
            raise ValueError
        age = (
            datetime.now(timezone.utc) - qualified.astimezone(timezone.utc)
        ).total_seconds()
        if age < -60 or age > 43_200:
            raise ValueError
    except (TypeError, ValueError):
        errors.append("qualified_at_invalid")
    pid = int(receipt.get("process_pid") or -1)
    cmdline = str(receipt.get("process_cmdline") or "")
    if "vllm" not in cmdline or MODEL_REALPATH not in cmdline or str(PORT) not in cmdline:
        errors.append("process_cmdline_identity")
    if os.name != "nt":
        proc = Path(f"/proc/{pid}/cmdline")
        observed = (
            proc.read_bytes().replace(b"\0", b" ").decode() if proc.is_file() else ""
        )
        if observed != cmdline:
            errors.append("process_not_alive_or_drifted")
    if errors:
        raise RuntimeError(f"SYS-R2-LRER receipt invalid: {errors}")
    return receipt


def seven_gate_report(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    observed = {str(row.get("task_name")): row for row in summaries}
    tasks = []
    for name in SEVEN_TASK_ORDER:
        row = observed.get(name) or {}
        passed = row.get("evaluator_reward") == 1.0 and bool(row.get("success"))
        tasks.append(
            {
                "task_name": name,
                "reward": row.get("evaluator_reward"),
                "pass": passed,
            }
        )
    count = sum(int(row["pass"]) for row in tasks)
    return {
        "status": "pass" if count == 7 else "pending" if len(observed) < 7 else "fail",
        "success_count": count,
        "required": 7,
        "valid_observed_count": sum(int(name in observed) for name in SEVEN_TASK_ORDER),
        "tasks": tasks,
    }


def r2_outcome_map() -> dict[str, dict[str, Any]]:
    artifact = json.loads(R2_RESULT_PATH.read_text(encoding="utf-8"))
    if artifact.get("content_sha256") != content_sha256(artifact):
        raise RuntimeError("frozen A1-R2 result content hash drift")
    result = artifact.get("a1r2_result") or {}
    episodes = list(result.get("episodes") or [])
    mapped = {str(row.get("task_name")): row for row in episodes}
    if (
        result.get("status") != "COMPLETE"
        or len(episodes) != 19
        or len(mapped) != 19
        or set(mapped) != set(FULL_TASK_ORDER)
        or sum(int(bool(row.get("success"))) for row in episodes) != 6
    ):
        raise RuntimeError("frozen A1-R2 exact outcome closure drift")
    return {
        name: {
            "success": bool(row.get("success")),
            "reward": float(row.get("reward") or 0.0),
            "episode_id": str(row.get("episode_id") or ""),
        }
        for name, row in mapped.items()
    }


def task_attribution(
    *,
    task_name: str,
    summary: dict[str, Any] | None,
    recovery_audit: dict[str, Any],
    unresolved_infrastructure: bool,
) -> str:
    committed = list(recovery_audit.get("committed_injections") or [])
    counters = recovery_audit.get("counters") or {}
    activated = bool(
        int(counters.get("eligible_count") or 0)
        or int(counters.get("deferral_count") or 0)
        or committed
    )
    protection = bool(r2_outcome_map()[task_name]["success"])
    if summary and summary.get("success") and committed and not protection:
        return "MECHANISM_CONSISTENT_CANDIDATE_SUPPORT"
    if summary and summary.get("success") and committed:
        return "SUCCESS_COMPONENT_USED_PRESERVED_ABLATION_UNRESOLVED"
    if summary and summary.get("success"):
        return "SUCCESS_COMPONENT_SILENT_OR_UNUSED"
    if summary and protection:
        return "REGRESSION"
    if summary and activated:
        return "ACTIVATED_NO_GAIN"
    if summary:
        return "NO_OPPORTUNITY"
    if unresolved_infrastructure:
        return "INFRA_INVALID"
    return "NOT_RUN_BY_PROTOCOL"


def first_response_divergence(
    summary: dict[str, Any] | None,
    reference_episode: dict[str, Any] | None,
) -> dict[str, Any]:
    if summary is None:
        return {
            "status": "NOT_COMPARABLE",
            "reason": "no_valid_live_episode",
            "first_step": None,
        }
    if reference_episode is None:
        return {
            "status": "NOT_COMPARABLE",
            "reason": "no_frozen_r2_step_reference_for_task",
            "first_step": None,
        }
    live = list(summary.get("steps") or [])
    reference = list(reference_episode.get("steps") or [])
    for ordinal, (live_step, reference_step) in enumerate(zip(live, reference)):
        live_sha = str((live_step.get("model_call") or {}).get("response_sha256") or "")
        reference_sha = str(reference_step.get("source_response_sha256") or "")
        if not live_sha or not reference_sha:
            return {
                "status": "NOT_COMPARABLE",
                "reason": "response_hash_missing",
                "first_step": ordinal,
            }
        if live_sha != reference_sha:
            return {
                "status": "DIVERGED",
                "basis": "same_ordinal_model_response_sha256",
                "first_step": ordinal,
                "live_response_sha256": live_sha,
                "r2_response_sha256": reference_sha,
            }
    if len(live) != len(reference):
        return {
            "status": "DIVERGED",
            "basis": "response_sequence_length",
            "first_step": min(len(live), len(reference)),
            "live_step_count": len(live),
            "r2_step_count": len(reference),
        }
    return {
        "status": "EXACT_RESPONSE_SEQUENCE_MATCH",
        "basis": "same_ordinal_model_response_sha256",
        "first_step": None,
    }


def _episode_boundary_errors(summary: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    memory = summary.get("memory_mechanism") or {}
    recovery = summary.get("recovery_mechanism") or {}
    counters = recovery.get("counters") or {}
    if memory.get("mechanism_id") != MECHANISM_ID:
        errors.append("parent_memory_identity")
    if recovery.get("system_id") != SYSTEM_ID:
        errors.append("system_identity")
    settle = recovery.get("visible_frame_settle") or {}
    if settle.get("seconds") != POST_ACTION_SETTLE_SECONDS:
        errors.append("settle_identity")
    if int(counters.get("deferral_count") or 0) > 1:
        errors.append("deferral_cap")
    if int(counters.get("injection_commit_count") or 0) > 1:
        errors.append("injection_cap")
    if int(counters.get("auxiliary_model_call_count") or 0) != 0:
        errors.append("auxiliary_call_boundary")
    if summary.get("auxiliary_model_call_attempts") not in (None, []):
        errors.append("auxiliary_attempt_boundary")
    steps = summary.get("steps") or []
    if not steps or any(
        int(((step.get("model_call") or {}).get("raven_meta") or {}).get("transport_attempts") or 0)
        != 1
        for step in steps
    ):
        errors.append("transport_attempt_not_one")
    executed = [step for step in steps if bool(step.get("executed"))]
    for step in executed:
        settle_record = ((step.get("layers") or {}).get("L3_execution") or {}).get(
            "post_action_settle"
        ) or {}
        if (
            settle_record.get("policy")
            != "fixed_visible_frame_settle_before_single_capture_v1"
            or settle_record.get("requested_seconds")
            != POST_ACTION_SETTLE_SECONDS
            or not math.isfinite(float(settle_record.get("observed_seconds", -1)))
            or float(settle_record.get("observed_seconds", -1)) < 0.0
            or int(settle_record.get("additional_model_calls") or 0) != 0
            or int(settle_record.get("additional_actions") or 0) != 0
            or int(settle_record.get("additional_state_captures") or 0) != 0
        ):
            errors.append("settle_execution_boundary")
            break
    return errors


def diagnostic_completion_errors(
    *,
    summaries: list[dict[str, Any]],
    invalid_attempts: list[dict[str, Any]],
    lifecycle_errors: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    if tuple(str(row.get("task_name")) for row in summaries) != SEVEN_TASK_ORDER:
        errors.append("seven_task_closure")
    if lifecycle_errors or any(
        not row.get("resolved_by_episode_id") for row in invalid_attempts
    ):
        errors.append("infrastructure_closure")
    try:
        if any(
            not math.isfinite(float(row.get("evaluator_reward"))) for row in summaries
        ):
            errors.append("reward_invalid")
    except (TypeError, ValueError):
        errors.append("reward_invalid")
    if any(_episode_boundary_errors(row) for row in summaries):
        errors.append("system_boundary")
    return errors


def exact_completion_errors(
    *,
    summaries: list[dict[str, Any]],
    invalid_attempts: list[dict[str, Any]],
    lifecycle_errors: list[dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    if tuple(str(row.get("task_name")) for row in summaries) != FULL_TASK_ORDER:
        errors.append("task_closure")
    if seven_gate_report(summaries).get("status") != "pass":
        errors.append("seven_gate")
    if lifecycle_errors or any(
        not row.get("resolved_by_episode_id") for row in invalid_attempts
    ):
        errors.append("infrastructure_closure")
    try:
        if any(
            not math.isfinite(float(row.get("evaluator_reward"))) for row in summaries
        ):
            errors.append("reward_invalid")
    except (TypeError, ValueError):
        errors.append("reward_invalid")
    if any(_episode_boundary_errors(row) for row in summaries):
        errors.append("system_boundary")
    return errors


preservation_report = seven_gate_report


def validate_result_payload(
    payload: dict[str, Any], *, checkpoint_payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    errors: list[str] = []
    if payload.get("schema") != RESULT_SCHEMA:
        errors.append("result_schema")
    if payload.get("content_sha256") != content_sha256(payload):
        errors.append("result_content_hash")
    identity = payload.get("identity") or {}
    if (
        identity.get("mechanism_id") != MECHANISM_ID
        or identity.get("system_id") != SYSTEM_ID
        or identity.get("experiment_id") != EXPERIMENT_ID
    ):
        errors.append("result_identity")
    rows = list(payload.get("tasks") or [])
    if [str(row.get("task_name")) for row in rows] != list(FULL_TASK_ORDER):
        errors.append("result_task_order")
    allowed_attribution = {
        "MECHANISM_CONSISTENT_CANDIDATE_SUPPORT",
        "SUCCESS_COMPONENT_USED_PRESERVED_ABLATION_UNRESOLVED",
        "SUCCESS_COMPONENT_SILENT_OR_UNUSED",
        "ACTIVATED_NO_GAIN",
        "REGRESSION",
        "NO_OPPORTUNITY",
        "INFRA_INVALID",
        "NOT_RUN_BY_PROTOCOL",
    }
    valid_statuses = {"VALID_SUCCESS", "VALID_SCIENTIFIC_FAILURE"}
    valid_rows = [row for row in rows if row.get("execution_status") in valid_statuses]
    source_status = str(payload.get("source_checkpoint_status") or "")
    expected_result_status = (
        "COMPLETE_19"
        if source_status == "complete"
        else "TERMINAL_SEVEN_TASK_DIAGNOSTIC_FAIL"
        if source_status == "complete_seven_task_diagnostic_no_release"
        else "RESUMABLE_INFRASTRUCTURE_INVALID"
        if source_status == "stopped_invalid_episode"
        else "TERMINAL_INFRASTRUCTURE_INCOMPLETE"
        if source_status == "infrastructure_incomplete"
        else f"TERMINAL_{source_status.upper()}"
        if source_status.startswith("stopped_")
        else "RUNNING_PARTIAL"
    )
    if payload.get("status") != expected_result_status:
        errors.append("result_status_mapping")
    baseline = r2_outcome_map()
    for row in rows:
        task_name = str(row.get("task_name") or "")
        execution_status = row.get("execution_status")
        if row.get("attribution") not in allowed_attribution:
            errors.append("result_attribution")
            break
        expected_prior = baseline.get(task_name)
        if row.get("prior_r2_outcome") != expected_prior:
            errors.append("result_prior_r2_outcome")
            break
        if execution_status in valid_statuses:
            settle = row.get("post_action_settle") or {}
            lrer = row.get("lrer") or {}
            divergence = row.get("first_divergence_from_r2") or {}
            success = execution_status == "VALID_SUCCESS"
            try:
                reward = float(row.get("reward"))
                calls = int(row.get("normal_model_calls"))
                actions = int(row.get("executed_actions"))
                elapsed = float(row.get("elapsed_seconds"))
                usage = row.get("token_usage") or {}
                prompt_tokens = int(usage.get("prompt_tokens"))
                completion_tokens = int(usage.get("completion_tokens"))
                total_tokens = int(usage.get("total_tokens"))
                eligible_count = int(lrer.get("eligible_count"))
                deferral_count = int(lrer.get("deferral_count"))
                injection_count = int(lrer.get("injection_commit_count"))
            except (TypeError, ValueError):
                errors.append("result_task_numeric_type")
                break
            if (
                bool(row.get("success")) != success
                or not math.isfinite(reward)
                or success != (reward == 1.0)
                or calls < 1
                or actions < 0
                or not math.isfinite(elapsed)
                or elapsed < 0.0
                or min(prompt_tokens, completion_tokens, total_tokens) < 0
                or prompt_tokens + completion_tokens != total_tokens
                or not (0 <= injection_count <= deferral_count <= eligible_count <= 1)
            ):
                errors.append("result_success_status")
                break
            expected_comparative = (
                "PRESERVED"
                if success and expected_prior["success"]
                else "GAIN_CANDIDATE"
                if success
                else "REGRESSION"
                if expected_prior["success"]
                else "NO_GAIN"
            )
            committed = list(row.get("committed_injections") or [])
            expected_lrer_state = (
                "COMMITTED"
                if committed
                else "DEFERRED_NOT_COMMITTED"
                if int(lrer.get("deferral_count") or 0)
                else "ELIGIBLE_NOT_DEFERRED"
                if int(lrer.get("eligible_count") or 0)
                else "NO_OPPORTUNITY"
            )
            expected_attribution = task_attribution(
                task_name=task_name,
                summary={"success": success},
                recovery_audit={
                    "committed_injections": committed,
                    "counters": {
                        "eligible_count": lrer.get("eligible_count"),
                        "deferral_count": lrer.get("deferral_count"),
                    },
                },
                unresolved_infrastructure=False,
            )
            if (
                settle.get("requested_seconds") != POST_ACTION_SETTLE_SECONDS
                or not math.isfinite(float(settle.get("observed_seconds", -1)))
                or float(settle.get("observed_seconds", -1)) < 0.0
                or int(settle.get("event_count") or 0)
                != int(row.get("executed_actions") or 0)
                or lrer.get("state") is None
                or lrer.get("state") != expected_lrer_state
                or injection_count != len(committed)
                or row.get("comparative_outcome") != expected_comparative
                or row.get("attribution") != expected_attribution
                or row.get("frame_settle_active") is not True
                or any(
                    lrer.get(key) is None
                    for key in (
                        "eligible_count",
                        "deferral_count",
                        "injection_commit_count",
                    )
                )
                or divergence.get("status")
                not in {
                    "DIVERGED",
                    "EXACT_RESPONSE_SEQUENCE_MATCH",
                    "NOT_COMPARABLE",
                }
            ):
                errors.append("result_task_evidence")
                break
            if (
                divergence.get("status") == "NOT_COMPARABLE"
                and not str(divergence.get("reason") or "")
            ) or (
                divergence.get("status") == "DIVERGED"
                and not str(divergence.get("basis") or "")
            ) or (
                divergence.get("status") == "EXACT_RESPONSE_SEQUENCE_MATCH"
                and divergence.get("basis") != "same_ordinal_model_response_sha256"
            ):
                errors.append("result_divergence_evidence")
                break
        elif execution_status == "INFRA_INVALID":
            if (
                row.get("attribution") != "INFRA_INVALID"
                or row.get("comparative_outcome") != "INFRA_INVALID"
                or row.get("frame_settle_active") is not False
            ):
                errors.append("result_infra_classification")
                break
        elif execution_status == "NOT_RUN_BY_PROTOCOL":
            if (
                row.get("attribution") != "NOT_RUN_BY_PROTOCOL"
                or row.get("comparative_outcome") != "NOT_RUN_BY_PROTOCOL"
                or row.get("frame_settle_active") is not False
            ):
                errors.append("result_not_run_classification")
                break
        else:
            errors.append("result_execution_status")
            break
    closure = payload.get("closure") or {}
    if int(closure.get("valid_episode_count") or 0) != len(valid_rows):
        errors.append("result_valid_count")
    if int(closure.get("not_run_by_protocol_count") or 0) != sum(
        row.get("execution_status") == "NOT_RUN_BY_PROTOCOL" for row in rows
    ):
        errors.append("result_not_run_count")
    expected_performance = {
        "success_count": sum(row.get("execution_status") == "VALID_SUCCESS" for row in rows),
        "reward_sum": sum(float(row.get("reward") or 0.0) for row in valid_rows),
        "normal_model_calls": sum(int(row.get("normal_model_calls") or 0) for row in valid_rows),
        "executed_actions": sum(int(row.get("executed_actions") or 0) for row in valid_rows),
        "token_usage": {
            key: sum(int((row.get("token_usage") or {}).get(key) or 0) for row in valid_rows)
            for key in ("prompt_tokens", "completion_tokens", "total_tokens")
        },
        "elapsed_seconds": sum(float(row.get("elapsed_seconds") or 0.0) for row in valid_rows),
        "post_action_settle_seconds": sum(
            float((row.get("post_action_settle") or {}).get("observed_seconds") or 0.0)
            for row in valid_rows
        ),
    }
    if payload.get("performance") != expected_performance:
        errors.append("result_performance")
    expected_funnel = {
        "eligible_count": sum(int((row.get("lrer") or {}).get("eligible_count") or 0) for row in valid_rows),
        "deferral_count": sum(int((row.get("lrer") or {}).get("deferral_count") or 0) for row in valid_rows),
        "injection_commit_count": sum(int((row.get("lrer") or {}).get("injection_commit_count") or 0) for row in valid_rows),
        "auxiliary_model_call_count": 0,
    }
    if payload.get("mechanism_funnel") != expected_funnel:
        errors.append("result_mechanism_funnel")
    gate_rows = rows[: len(SEVEN_TASK_ORDER)]
    gate_tasks = [
        {
            "task_name": row.get("task_name"),
            "reward": row.get("reward")
            if row.get("execution_status") in valid_statuses
            else None,
            "pass": row.get("execution_status") == "VALID_SUCCESS"
            and row.get("reward") == 1.0,
        }
        for row in gate_rows
    ]
    gate_success = sum(int(row["pass"]) for row in gate_tasks)
    gate_observed = sum(
        int(row.get("execution_status") in valid_statuses) for row in gate_rows
    )
    expected_gate = {
        "status": "pass"
        if gate_success == 7
        else "pending"
        if gate_observed < 7
        else "fail",
        "success_count": gate_success,
        "required": 7,
        "valid_observed_count": gate_observed,
        "tasks": gate_tasks,
    }
    if payload.get("seven_task_gate") != expected_gate:
        errors.append("result_seven_gate")
    if source_status == "complete" and (
        len(valid_rows) != 19 or gate_success != 7
    ):
        errors.append("result_complete_19_closure")
    if source_status == "complete_seven_task_diagnostic_no_release" and (
        len(valid_rows) != 7
        or gate_success == 7
        or sum(row.get("execution_status") == "NOT_RUN_BY_PROTOCOL" for row in rows)
        != 12
    ):
        errors.append("result_seven_terminal_closure")
    verdicts = payload.get("verdicts") or {}
    expected_mechanism = (
        "COMPOSITE_CANDIDATE_SUPPORT_ABLATION_UNRESOLVED"
        if any(
            row.get("attribution") == "MECHANISM_CONSISTENT_CANDIDATE_SUPPORT"
            for row in rows
        )
        else "NOT_ESTABLISHED"
    )
    success_count = sum(row.get("execution_status") == "VALID_SUCCESS" for row in rows)
    expected_accuracy = (
        f"COMPLETE_19_{success_count}_SUCCESSES"
        if source_status == "complete"
        else f"SEVEN_TASK_{(payload.get('seven_task_gate') or {}).get('success_count', 0)}_OF_7"
        if source_status == "complete_seven_task_diagnostic_no_release"
        else "NOT_YET_ADJUDICATED"
    )
    if verdicts != {
        "accuracy": expected_accuracy,
        "mechanism": expected_mechanism,
        "cost": "DESCRIPTIVE_ONLY_NO_MATCHED_RUNTIME_CONTROL",
    }:
        errors.append("result_verdicts")
    if payload.get("errors") != []:
        errors.append("result_errors")
    if checkpoint_payload is not None:
        checkpoint_hash = content_sha256(checkpoint_payload)
        checkpoint_summaries = list(checkpoint_payload.get("valid_summaries") or [])
        if (
            checkpoint_payload.get("content_sha256") != checkpoint_hash
            or closure.get("checkpoint_content_sha256") != checkpoint_hash
            or checkpoint_payload.get("status") != source_status
            or checkpoint_payload.get("system_id") != SYSTEM_ID
            or checkpoint_payload.get("experiment_id") != EXPERIMENT_ID
            or checkpoint_payload.get("schema") != CHECKPOINT_SCHEMA
            or len(checkpoint_payload.get("valid_summaries") or []) != len(valid_rows)
            or int(closure.get("invalid_attempt_count") or 0)
            != len(checkpoint_payload.get("invalid_attempts") or [])
            or identity.get("run_signature_sha256")
            != checkpoint_payload.get("run_signature_sha256")
        ):
            errors.append("result_checkpoint_binding")
        checkpoint_by_task = {
            str(summary.get("task_name") or ""): summary
            for summary in checkpoint_summaries
        }
        if (
            len(checkpoint_by_task) != len(checkpoint_summaries)
            or tuple(checkpoint_by_task) != tuple(
                row.get("task_name") for row in valid_rows
            )
        ):
            errors.append("result_checkpoint_task_closure")
        else:
            for row in valid_rows:
                summary = checkpoint_by_task[str(row.get("task_name"))]
                calls = [
                    step.get("model_call") or {}
                    for step in (summary.get("steps") or [])
                ]
                calls.extend(
                    attempt.get("model_call") or {}
                    for attempt in (summary.get("auxiliary_model_call_attempts") or [])
                    if attempt.get("model_call") is not None
                )
                usage = {
                    key: sum(
                        int((call.get("usage") or {}).get(key) or 0)
                        for call in calls
                    )
                    for key in ("prompt_tokens", "completion_tokens", "total_tokens")
                }
                settle_events = [
                    (
                        ((step.get("layers") or {}).get("L3_execution") or {}).get(
                            "post_action_settle"
                        )
                        or {}
                    )
                    for step in (summary.get("steps") or [])
                    if bool(step.get("executed"))
                ]
                recovery = summary.get("recovery_mechanism") or {}
                counters = recovery.get("counters") or {}
                committed = list(recovery.get("committed_injections") or [])
                try:
                    elapsed = (
                        datetime.fromisoformat(str(summary["finished_at"])).timestamp()
                        - datetime.fromisoformat(str(summary["started_at"])).timestamp()
                    )
                except (KeyError, TypeError, ValueError):
                    errors.append("result_checkpoint_elapsed")
                    break
                expected_from_checkpoint = {
                    "episode_id": summary.get("episode_id"),
                    "reward": summary.get("evaluator_reward"),
                    "success": summary.get("success"),
                    "normal_model_calls": int(
                        summary.get("normal_decision_call_count")
                        or summary.get("model_call_count")
                        or 0
                    ),
                    "executed_actions": int(
                        summary.get("executed_action_count") or 0
                    ),
                    "token_usage": usage,
                    "elapsed_seconds": elapsed,
                    "committed_injections": committed,
                    "eligible_count": int(counters.get("eligible_count") or 0),
                    "deferral_count": int(counters.get("deferral_count") or 0),
                    "injection_commit_count": int(
                        counters.get("injection_commit_count") or 0
                    ),
                    "settle_event_count": len(settle_events),
                    "settle_observed_seconds": sum(
                        float(event.get("observed_seconds") or 0.0)
                        for event in settle_events
                    ),
                }
                observed_from_result = {
                    "episode_id": row.get("episode_id"),
                    "reward": row.get("reward"),
                    "success": row.get("success"),
                    "normal_model_calls": row.get("normal_model_calls"),
                    "executed_actions": row.get("executed_actions"),
                    "token_usage": row.get("token_usage"),
                    "elapsed_seconds": row.get("elapsed_seconds"),
                    "committed_injections": list(
                        row.get("committed_injections") or []
                    ),
                    "eligible_count": (row.get("lrer") or {}).get("eligible_count"),
                    "deferral_count": (row.get("lrer") or {}).get("deferral_count"),
                    "injection_commit_count": (row.get("lrer") or {}).get(
                        "injection_commit_count"
                    ),
                    "settle_event_count": (row.get("post_action_settle") or {}).get(
                        "event_count"
                    ),
                    "settle_observed_seconds": (
                        row.get("post_action_settle") or {}
                    ).get("observed_seconds"),
                }
                if observed_from_result != expected_from_checkpoint:
                    errors.append("result_checkpoint_task_binding")
                    break
    if errors:
        raise RuntimeError(f"SYS-R2-LRER V2 result invalid: {errors}")
    return payload


__all__ = [name for name in globals() if name.isupper()] + [
    "canonical_sha256",
    "content_sha256",
    "diagnostic_completion_errors",
    "exact_completion_errors",
    "file_sha256",
    "local_processor_identity",
    "preservation_report",
    "seven_gate_report",
    "task_attribution",
    "first_response_divergence",
    "r2_outcome_map",
    "source_freeze_payload",
    "validate_launch_receipt",
    "validate_preflight_report",
    "validate_source_freeze",
    "validate_result_payload",
]
