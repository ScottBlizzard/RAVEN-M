"""Fail-closed contract for prospective SYS-R2-LRER.

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
from .r15_derived_evidence_consolidation import EXPERIMENT_ID, SYSTEM_ID
from .sys_trrc_token_budget import PROCESSOR_RUNTIME_PACKAGES


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
MODEL_REALPATH = "/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope"
MODEL_MANIFEST_SHA256 = "18e0909c7d993853d6d0f62443461a74009754f90db026a1723cab80121c7872"
PARENT_EVIDENCE_COMMIT = "46d9248fdc96721862ba4d919381846d250d960c"
TASK_SEED = 20260806
GENERATION_SEED = 3407
PORT = 18000
CONFIG_SCHEMA = "sys_r2_lrer_config_v1"
OFFLINE_REPLAY_SCHEMA = "sys_r2_lrer_offline_replay_v1"
REPLAY_FIXTURE_SCHEMA = "sys_r2_lrer_replay_fixture_v1"
SOURCE_FREEZE_SCHEMA = "sys_r2_lrer_source_freeze_v1"
PREFLIGHT_SCHEMA = "sys_r2_lrer_zero_generation_preflight_v1"
LIVE_RECEIPT_SCHEMA = "sys_r2_lrer_live_server_receipt_v1"
CHECKPOINT_SCHEMA = "sys_r2_lrer_checkpoint_v1"
RESULT_SCHEMA = "sys_r2_lrer_result_v1"

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
CONFIG_PATH = REPOSITORY_ROOT / "implementation/configs/sys_r2_lrer_hard_seed20260806.json"
REPLAY_FIXTURE_PATH = REPOSITORY_ROOT / "evidence/sys_r2_lrer/SYS_R2_LRER_REPLAY_FIXTURE.json"
OFFLINE_REPLAY_PATH = REPOSITORY_ROOT / "evidence/sys_r2_lrer/SYS_R2_LRER_OFFLINE_REPLAY_REPORT.json"
SOURCE_FREEZE_PATH = REPOSITORY_ROOT / "evidence/sys_r2_lrer/SYS_R2_LRER_SOURCE_FREEZE.json"
PREFLIGHT_PATH = REPOSITORY_ROOT / "evidence/sys_r2_lrer/SYS_R2_LRER_ZERO_GENERATION_PREFLIGHT.json"

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
    "protocols/SYS_R2_LATE_RAW_EVIDENCE_REHYDRATION_PREREG_2026-08-18.md",
    "implementation/configs/sys_r2_lrer_hard_seed20260806.json",
    "implementation/configs/androidworld_hard_v2_instances.json",
    "implementation/src/raven_m/official_qwen_mobile/r15_derived_evidence_consolidation.py",
    "implementation/src/raven_m/official_qwen_mobile/sys_r2_lrer_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/a1r2_compact_verified_pending.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/official_qwen_mobile/protocol.py",
    "implementation/src/raven_m/official_qwen_mobile/working_memory.py",
    "implementation/src/raven_m/official_qwen_mobile/sys_trrc_token_budget.py",
    "implementation/src/raven_m/models/vllm_client.py",
    "implementation/src/raven_m/env/androidworld_adapter.py",
    "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/materialize_sys_r2_lrer_fixture.py",
    "implementation/scripts/replay_sys_r2_lrer.py",
    "implementation/scripts/preflight_sys_r2_lrer.py",
    "implementation/scripts/qualify_a1r5_tipl_server.py",
    "implementation/scripts/qualify_sys_r2_lrer_server.py",
    "implementation/scripts/start_sys_r2_lrer_server.sh",
    "implementation/scripts/run_sys_r2_lrer.py",
    "implementation/tests/official_qwen_mobile/test_r15_derived_evidence_consolidation.py",
    "implementation/tests/official_qwen_mobile/test_sys_r2_lrer_contract.py",
    "implementation/tests/official_qwen_mobile/test_sys_r2_lrer_controller_integration.py",
    "implementation/tests/official_qwen_mobile/test_sys_r2_lrer_offline_replay.py",
    "evidence/sys_r2_lrer/SYS_R2_LRER_REPLAY_FIXTURE.json",
    "evidence/sys_r2_lrer/SYS_R2_LRER_OFFLINE_REPLAY_REPORT.json",
    "evidence/sys_r2_lrer/source_episodes/a1_r15_01_browsermultiply.json",
    "evidence/sys_r2_lrer/source_episodes/a1_r2_01_browsermultiply.json",
    "evidence/sys_r2_lrer/source_episodes/a1_r2_02_expensedeletemultiple2.json",
    "evidence/sys_r2_lrer/source_episodes/a1_r2_03_retrosaveplaylist.json",
    "evidence/sys_r2_lrer/source_episodes/a1_r2_04_simplecalendaraddoneevent.json",
    "evidence/sys_r2_lrer/source_episodes/a1_r2_05_sportstrackertotaldurationforcategorythisweek.json",
    "evidence/sys_r2_lrer/source_episodes/a1_r2_06_recipedeletemultiplerecipeswithconstraint.json",
    "evidence/sys_r2_lrer/source_episodes/a1_r2_07_osmandmarker.json",
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
        and int(browser.get("r15_opportunity_count") or 0) == 1
        and int(browser.get("r2_opportunity_count") or 0) == 1
        and browser.get("r15_all_five_observations_present") is True
        and browser.get("deferred_response_excluded") is True
        and len(success_rows) == 6
        and [str(row.get("task_name")) for row in success_rows]
        == list(SEVEN_TASK_ORDER[1:])
        and all(int(row.get("opportunity_count") or 0) == 0 for row in success_rows)
    )


def local_processor_identity(projector: Any) -> dict[str, Any]:
    python_executable = Path(projector.python_executable).resolve()
    processor_path = Path(projector.model_path).resolve()
    payload = {
        "schema": "sys_r2_lrer_local_processor_identity_v1",
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
        identity.get("schema") == "sys_r2_lrer_local_processor_identity_v1"
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
        != canonical_sha256("SYS-R2-LRER base prompt")
        or processor_smoke.get("final_text_sha256")
        != canonical_sha256("SYS-R2-LRER base prompt\nLRER evidence")
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


def _episode_boundary_errors(summary: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    memory = summary.get("memory_mechanism") or {}
    recovery = summary.get("recovery_mechanism") or {}
    counters = recovery.get("counters") or {}
    if memory.get("mechanism_id") != MECHANISM_ID:
        errors.append("parent_memory_identity")
    if recovery.get("system_id") != SYSTEM_ID:
        errors.append("system_identity")
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


__all__ = [name for name in globals() if name.isupper()] + [
    "canonical_sha256",
    "content_sha256",
    "diagnostic_completion_errors",
    "exact_completion_errors",
    "file_sha256",
    "local_processor_identity",
    "preservation_report",
    "seven_gate_report",
    "source_freeze_payload",
    "validate_launch_receipt",
    "validate_preflight_report",
    "validate_source_freeze",
]
