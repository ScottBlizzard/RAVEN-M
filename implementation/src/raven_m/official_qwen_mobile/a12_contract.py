"""Frozen scientific and infrastructure contract for A12 MADM.

The source freeze deliberately excludes every artifact produced after the
implementation commit.  Its digest covers only the implementation commit and
an exact path-to-SHA256 mapping, so neither the freeze file nor replay,
preflight, receipt, and result artifacts can create a hash cycle.
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


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
OFFICIAL_SYSTEM_PROMPT_SHA256 = "9d060af15f62acb31b9fb197649ec001d4096491d7fb102de929316944b3e26d"
MODEL_REALPATH = "/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope"
MODEL_MANIFEST_SHA256 = "18e0909c7d993853d6d0f62443461a74009754f90db026a1723cab80121c7872"

REVIEW_COMMIT = "ee30db3692bd7797722b3ea29a70266eb6256c7e"
PARENT_EVIDENCE_COMMIT = "5009034fa050d2f065e4eb08ff1c8c394a0ac586"
MECHANISM_ID = "a12_minimal_action_divergence_memory_v1"
EXPERIMENT_ID = "A12_MADM_QWEN3VL32B_AW_HARD_T20260806_G3407_V1"
CONFIG_SCHEMA = "a12_madm_arm_v1"
AUDIT_SCHEMA = "a12_madm_audit_v1"
REFERENCE_SEGMENT_SCHEMA = "a12_reference_segments_v1"
OFFLINE_REPLAY_SCHEMA = "a12_offline_replay_report_v1"
PREFLIGHT_SCHEMA = "a12_zero_generation_preflight_v1"
LIVE_RECEIPT_SCHEMA = "a12_live_server_receipt_v1"
CHECKPOINT_SCHEMA = "a12_suite_checkpoint_v1"
RESULT_SCHEMA = "a12_madm_result_v1"

TASK_SEED = 20260806
GENERATION_SEED = 3407
TASK_COUNT = 19
PORT = 18000

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
CONFIG_PATH = REPOSITORY_ROOT / "implementation/configs/a12_minimal_action_divergence_hard_seed20260806.json"
SOURCE_FREEZE_PATH = REPOSITORY_ROOT / "evidence/a12/A12_STATIC_SOURCE_FREEZE.json"
OFFLINE_REPLAY_PATH = REPOSITORY_ROOT / "evidence/a12/A12_OFFLINE_REPLAY_REPORT.json"
PREFLIGHT_PATH = REPOSITORY_ROOT / "evidence/a12/A12_ZERO_GENERATION_PREFLIGHT.json"
LIVE_RECEIPT_PATH = REPOSITORY_ROOT / "evidence/a12/A12_LIVE_SERVER_RECEIPT.json"
LAUNCH_INTENT_PATH = REPOSITORY_ROOT / "evidence/a12/A12_SERVER_LAUNCH_INTENT.json"

GATE_TASKS = (
    "ExpenseDeleteMultiple2",
    "RetroSavePlaylist",
    "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
)
REMAINING_TASKS = (
    "BrowserMultiply",
    "ExpenseAddMultipleFromGallery",
    "ExpenseAddMultipleFromMarkor",
    "MarkorCreateNoteAndSms",
    "MarkorMergeNotes",
    "MarkorTranscribeVideo",
    "OsmAndMarker",
    "OsmAndTrack",
    "RecipeAddMultipleRecipesFromImage",
    "RecipeAddMultipleRecipesFromMarkor",
    "RecipeAddMultipleRecipesFromMarkor2",
    "RecipeDeleteMultipleRecipesWithConstraint",
    "SaveCopyOfReceiptTaskEval",
    "SportsTrackerActivitiesOnDate",
    "SportsTrackerTotalDistanceForCategoryOverInterval",
)
TASK_ORDER = GATE_TASKS + REMAINING_TASKS

FORMAL_REPLAY_GATE_NAMES = frozenset({
    "exact_mechanism_id", "exact_experiment_id", "episodes_27_complete",
    "file_hashes_1668_pass", "bytes_442138413_pass", "generation_calls_zero",
    "reference_segment_count_exact", "a6_qualified_at_least_20_of_23",
    "a6_actual_read_recall_pass", "failure_role_read_precision_at_least_0_80",
    "unbound_failure_reads_at_most_5", "a0_competent_total_reads_at_most_2",
    "each_competent_episode_reads_at_most_1", "competent_read_density_at_most_0_03",
    "no_broad_navigation_read", "a8_earliest_segment_qualified",
    "a9_earliest_segment_qualified", "a9_total_at_least_2_of_3",
    "a1_recipe_auxiliary_sparse_gate_pass",
    "every_qualified_segment_has_actual_nonempty_read",
    "candidate_only_qualification_count_zero", "every_read_chars_at_most_240",
    "every_read_bytes_at_most_480", "every_read_tokens_at_most_100",
    "every_episode_reads_at_most_5", "every_episode_memory_tokens_at_most_500",
    "all_cooldown_gaps_at_least_4", "one_shot_violations_zero",
    "audit_bytes_at_most_128_kib", "resident_state_at_most_2_mib",
    "hidden_evaluator_future_violations_zero", "source_hashes_exact", "errors_empty",
})

# Exact layer-1 closure from design section 41.  Generated layer-2 artifacts
# A12_STATIC_SOURCE_FREEZE, replay, preflight, receipt and final result are
# intentionally absent.
SOURCE_FILES = (
    "GPT_PRO_A12_MINIMAL_ACTION_DIVERGENCE_MEMORY_DESIGN_2026-08-13.md",
    "protocols/A12_MADM_IMPLEMENTATION_BINDING_2026-08-13.md",
    "implementation/src/raven_m/official_qwen_mobile/a12_minimal_action_divergence.py",
    "implementation/src/raven_m/official_qwen_mobile/a12_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/official_qwen_mobile/protocol.py",
    "implementation/src/raven_m/official_qwen_mobile/__init__.py",
    "implementation/configs/androidworld_hard_v2_instances.json",
    "implementation/configs/a12_minimal_action_divergence_hard_seed20260806.json",
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/run_a678_arm.py",
    "implementation/scripts/build_a12_reference_segments.py",
    "implementation/scripts/replay_a12_offline_traces.py",
    "implementation/scripts/preflight_a12.py",
    "implementation/scripts/qualify_a12_live_server.py",
    "implementation/scripts/start_a12_server.sh",
    "implementation/src/raven_m/models/vllm_client.py",
    "implementation/src/raven_m/env/androidworld_adapter.py",
    "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    "implementation/tests/official_qwen_mobile/test_a12_visual.py",
    "implementation/tests/official_qwen_mobile/test_a12_action_family.py",
    "implementation/tests/official_qwen_mobile/test_a12_state_machine.py",
    "implementation/tests/official_qwen_mobile/test_a12_replay_binding.py",
    "implementation/tests/official_qwen_mobile/test_a12_controller_integration.py",
    "implementation/tests/official_qwen_mobile/test_a12_contract.py",
    "implementation/tests/official_qwen_mobile/test_a12_capacity.py",
    "implementation/tests/official_qwen_mobile/test_a12_leakage.py",
    "evidence/a12/A12_REFERENCE_SEGMENTS.json",
    "evidence/a12/A12_OFFLINE_TRACE_SOURCE_SPEC.json",
    "evidence/a12/A12_TEST_MANIFEST.json",
    "evidence/a10/A10_OFFLINE_TRACE_MANIFEST.json",
    "evidence/a10/A10_OFFLINE_REPLAY_REPORT.json",
    "evidence/a10_v2/A10_V2_OFFLINE_REPLAY_REPORT.json",
    "evidence/a11/A11_OFFLINE_REPLAY_REPORT.json",
    "evidence/a2/A0_A1_PAIRED_REFERENCE_20260810.json",
    "evidence/a678/A8_V2_OFFLINE_TRACE_AUDIT_2026-08-11.json",
    "evidence/a678/A89_INITIAL_GATE_RESULTS_2026-08-12.json",
)

LIVE_BINDING_FIELDS = (
    "implementation_commit",
    "source_freeze_payload_sha256",
    "offline_replay_sha256",
    "preflight_sha256",
    "launch_intent_sha256",
    "served_model_id",
    "model_realpath",
    "model_manifest_sha256",
)
LAUNCH_INTENT_BINDING_FIELDS = tuple(
    key for key in LIVE_BINDING_FIELDS if key != "launch_intent_sha256"
)
LIVE_RECEIPT_FIELDS = {
    "schema", "status", "mechanism_id", "experiment_id",
    *LIVE_BINDING_FIELDS,
    "process_pid", "process_cmdline", "host", "port",
    "vllm_version", "torch_version", "transformers_version",
    "observed_served_model_ids", "qualification_timestamp", "generation_calls",
}


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def is_commit_sha(value: Any) -> bool:
    text = str(value or "").casefold()
    return len(text) == 40 and all(char in "0123456789abcdef" for char in text)


def source_freeze_payload(implementation_commit: str) -> dict[str, Any]:
    """Return the exact layer-1 payload, failing on missing closure files."""
    if not is_commit_sha(implementation_commit):
        raise RuntimeError("A12 implementation commit must be exact 40-hex")
    missing = [name for name in SOURCE_FILES if not (REPOSITORY_ROOT / name).is_file()]
    if missing:
        raise RuntimeError(f"A12 source closure incomplete: {missing}")
    files = {name: file_sha256(REPOSITORY_ROOT / name) for name in SOURCE_FILES}
    payload = {"implementation_commit": implementation_commit.casefold(), "files": files}
    return {**payload, "payload_sha256": canonical_json_sha256(payload)}


def validate_source_freeze(path: Path = SOURCE_FREEZE_PATH) -> dict[str, Any]:
    freeze = json.loads(path.read_text(encoding="utf-8"))
    expected = source_freeze_payload(str(freeze.get("implementation_commit") or ""))
    errors: list[str] = []
    if set(freeze) != {"implementation_commit", "files", "payload_sha256"}:
        errors.append("source_freeze_schema_or_self_hash_field_invalid")
    if freeze != expected:
        errors.append("source_freeze_payload_drift")
    try:
        head = subprocess.check_output(
            ["git", "-C", str(REPOSITORY_ROOT), "rev-parse", "HEAD"], text=True
        ).strip()
        if head != freeze.get("implementation_commit"):
            errors.append("implementation_commit_not_current_head")
        if subprocess.run(
            [
                "git", "-C", str(REPOSITORY_ROOT), "merge-base", "--is-ancestor",
                REVIEW_COMMIT, str(freeze.get("implementation_commit") or ""),
            ],
            check=False,
            capture_output=True,
        ).returncode:
            errors.append("review_commit_not_ancestor")
        if subprocess.check_output(
            ["git", "-C", str(REPOSITORY_ROOT), "status", "--porcelain", "--untracked-files=all"],
            text=True,
        ).strip():
            errors.append("worktree_not_clean")
    except (OSError, subprocess.SubprocessError):
        errors.append("git_identity_validation_failed")
    if errors:
        raise RuntimeError(f"A12 source freeze invalid: {errors}")
    return freeze


def validate_preflight_report(
    path: Path = PREFLIGHT_PATH,
    *,
    source_freeze_path: Path = SOURCE_FREEZE_PATH,
    offline_replay_path: Path = OFFLINE_REPLAY_PATH,
) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    freeze = validate_source_freeze(source_freeze_path)
    replay = json.loads(offline_replay_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    expected = {
        "schema": PREFLIGHT_SCHEMA,
        "status": "PASS",
        "mechanism_id": MECHANISM_ID,
        "experiment_id": EXPERIMENT_ID,
        "implementation_commit": freeze["implementation_commit"],
        "source_freeze_payload_sha256": freeze["payload_sha256"],
        "offline_replay_sha256": file_sha256(offline_replay_path),
        "generation_calls": 0,
    }
    for key, value in expected.items():
        if report.get(key) != value:
            errors.append(f"{key}_drift")
    if report.get("errors") != []:
        errors.append("preflight_errors_nonempty")
    if report.get("verdict") != "A12_ZERO_GENERATION_PREFLIGHT_PASS":
        errors.append("preflight_verdict_not_pass")
    required_report_fields = {
        "schema", "status", "mechanism_id", "experiment_id",
        "implementation_commit", "source_freeze_payload_sha256",
        "offline_replay_sha256", "generation_calls", "errors",
    }
    if not required_report_fields.issubset(report):
        errors.append("preflight_required_fields_missing")
    if replay.get("schema") != OFFLINE_REPLAY_SCHEMA:
        errors.append("offline_replay_schema_drift")
    if replay.get("status") != "pass":
        errors.append("offline_replay_not_pass")
    if int(replay.get("generation_calls", -1)) != 0:
        errors.append("offline_replay_generation_calls_nonzero")
    if replay.get("errors") != []:
        errors.append("offline_replay_errors_nonempty")
    if replay.get("live_generation_authorized") is not True:
        errors.append("offline_replay_live_authorization_missing")
    if replay.get("formal_replay_executed") is not True:
        errors.append("offline_replay_not_formal")
    if replay.get("verdict") != "A12_OFFLINE_REPLAY_PASS":
        errors.append("offline_replay_verdict_not_pass")
    if replay.get("mechanism_id") != MECHANISM_ID:
        errors.append("offline_replay_mechanism_id_drift")
    if replay.get("experiment_id") != EXPERIMENT_ID:
        errors.append("offline_replay_experiment_id_drift")
    # Section 38 is represented as an exact, closed 33-gate vector.  A short
    # self-asserted pass record must never authorize a live server.
    replay_gates = replay.get("formal_replay_gates")
    if not isinstance(replay_gates, dict) or set(replay_gates) != FORMAL_REPLAY_GATE_NAMES:
        errors.append("offline_replay_gate_vector_not_exact")
    elif any(value is not True for value in replay_gates.values()):
        errors.append("offline_replay_gate_failure")
    exact_replay_metrics = {
        "episode_count": 27,
        "file_count": 1668,
        "total_bytes": 442138413,
        "reference_segment_count": 23,
    }
    for key, value in exact_replay_metrics.items():
        if replay.get(key) != value:
            errors.append(f"offline_replay_{key}_drift")
    if not isinstance(replay.get("a6_qualified_segment_count"), int) or not 20 <= replay["a6_qualified_segment_count"] <= 23:
        errors.append("offline_replay_a6_qualified_count_invalid")
    if report.get("live_generation_authorized") is not True:
        errors.append("preflight_live_authorization_missing")
    if report.get("formal_replay_executed") is not True:
        errors.append("formal_replay_not_executed")
    if errors:
        raise RuntimeError(f"A12 preflight invalid: {errors}")
    return report


def validate_launch_receipt(
    path: Path = LIVE_RECEIPT_PATH,
    *,
    preflight_path: Path = PREFLIGHT_PATH,
    source_freeze_path: Path = SOURCE_FREEZE_PATH,
    offline_replay_path: Path = OFFLINE_REPLAY_PATH,
    launch_intent_path: Path = LAUNCH_INTENT_PATH,
) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    preflight = validate_preflight_report(
        preflight_path,
        source_freeze_path=source_freeze_path,
        offline_replay_path=offline_replay_path,
    )
    intent = json.loads(launch_intent_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    expected = {
        "schema": LIVE_RECEIPT_SCHEMA,
        "status": "PASS",
        "mechanism_id": MECHANISM_ID,
        "experiment_id": EXPERIMENT_ID,
        "implementation_commit": preflight["implementation_commit"],
        "source_freeze_payload_sha256": preflight["source_freeze_payload_sha256"],
        "offline_replay_sha256": preflight["offline_replay_sha256"],
        "preflight_sha256": file_sha256(preflight_path),
        "launch_intent_sha256": file_sha256(launch_intent_path),
        "served_model_id": MODEL_ID,
        "model_realpath": MODEL_REALPATH,
        "model_manifest_sha256": MODEL_MANIFEST_SHA256,
        "port": PORT,
        "observed_served_model_ids": [MODEL_ID],
        "generation_calls": 0,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            errors.append(f"{key}_drift")
    if set(receipt) != LIVE_RECEIPT_FIELDS:
        errors.append("live_receipt_exact_field_set_invalid")
    for key in LAUNCH_INTENT_BINDING_FIELDS:
        if key not in intent:
            errors.append(f"launch_intent_{key}_missing")
        elif intent.get(key) != receipt.get(key):
            errors.append(f"launch_intent_{key}_drift")
    cmdline = [str(item) for item in receipt.get("process_cmdline") or []]
    if cmdline != [str(item) for item in intent.get("process_cmdline") or []]:
        errors.append("process_cmdline_intent_drift")
    if MODEL_REALPATH not in cmdline or MODEL_ID not in cmdline or "serve" not in cmdline:
        errors.append("process_cmdline_model_binding_missing")
    if not all(str(receipt.get(key) or "") for key in ("vllm_version", "torch_version", "transformers_version", "host")):
        errors.append("runtime_identity_incomplete")
    try:
        process_pid = int(receipt.get("process_pid"))
        if process_pid <= 0:
            raise ValueError
    except (TypeError, ValueError):
        process_pid = -1
        errors.append("process_pid_invalid")
    try:
        qualified = datetime.fromisoformat(str(receipt.get("qualification_timestamp")))
        if qualified.tzinfo is None:
            raise ValueError
        age = (datetime.now(timezone.utc) - qualified.astimezone(timezone.utc)).total_seconds()
        if age < -60 or age > 12 * 3600:
            errors.append("qualification_timestamp_not_fresh")
    except (TypeError, ValueError):
        errors.append("qualification_timestamp_invalid")
    if os.name == "posix" and process_pid > 0:
        proc = Path(f"/proc/{process_pid}/cmdline")
        if not proc.is_file():
            errors.append("qualified_process_not_alive")
        elif [part.decode() for part in proc.read_bytes().split(b"\0") if part] != cmdline:
            errors.append("qualified_process_cmdline_changed")
    if errors:
        raise RuntimeError(f"A12 live receipt invalid: {errors}")
    return receipt


def preservation_report(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    observed = {str(item.get("task_name")): item for item in summaries}
    tasks: list[dict[str, Any]] = []
    for name in GATE_TASKS:
        summary = observed.get(name) or {}
        reward = summary.get("evaluator_reward", summary.get("reward"))
        transport = summary.get("transport_attempt_max")
        if transport is None:
            transport = max(
                (
                    int(((step.get("model_call") or {}).get("raven_meta") or {}).get("transport_attempts") or 0)
                    for step in summary.get("steps", [])
                ),
                default=1,
            )
        passed = bool(
            reward == 1.0
            and int(transport) == 1
            and int(summary.get("memory_added_model_calls", 0)) == 0
            and summary.get("guard_enabled", summary.get("guard", False)) is False
            and int(summary.get("action_override_count", 0)) == 0
            and int(summary.get("forced_termination_count", 0)) == 0
        )
        tasks.append({"task_name": name, "reward": reward, "transport_attempt_max": transport, "pass": passed})
    success_count = sum(bool(item["pass"]) for item in tasks)
    return {"status": "pass" if success_count == 4 else "fail", "success_count": success_count, "required": 4, "tasks": tasks}


def _finite_reward(summary: dict[str, Any]) -> bool:
    try:
        return math.isfinite(float(summary.get("evaluator_reward", summary.get("reward"))))
    except (TypeError, ValueError):
        return False


def _transport_attempt_max(summary: dict[str, Any]) -> int:
    if summary.get("transport_attempt_max") is not None:
        try:
            return int(summary["transport_attempt_max"])
        except (TypeError, ValueError):
            return -1
    values = [
        int(((step.get("model_call") or {}).get("raven_meta") or {}).get("transport_attempts") or 0)
        for step in summary.get("steps", [])
    ]
    return max(values, default=1)


def exact_completion_errors(
    summaries: list[dict[str, Any]],
    invalid_attempts: list[dict[str, Any]],
    lifecycle_errors: list[dict[str, Any]],
) -> list[str]:
    """Validate exact closure while permitting correctly replaced infra failures."""
    errors: list[str] = []
    observed_order = [str(item.get("task_name")) for item in summaries]
    if len(summaries) != TASK_COUNT or observed_order != list(TASK_ORDER):
        errors.append("exact_19_ordered_task_closure_failed")
    if len(set(observed_order)) != len(observed_order):
        errors.append("duplicated_or_omitted_task")
    valid_ids = [str(item.get("episode_id") or "") for item in summaries]
    if any(not value for value in valid_ids) or len(set(valid_ids)) != len(valid_ids):
        errors.append("invalid_or_duplicate_valid_episode_id")
    if any(int(item.get("task_seed", item.get("seed", -1))) != TASK_SEED for item in summaries):
        errors.append("task_seed_drift")
    if any(item.get("error") is not None or item.get("lifecycle_errors") or not _finite_reward(item) for item in summaries):
        errors.append("invalid_valid_episode_summary")
    if any(_transport_attempt_max(item) != 1 for item in summaries):
        errors.append("transport_attempt_max_not_one")

    invalid_ids = [str(item.get("episode_id") or "") for item in invalid_attempts]
    if any(not value for value in invalid_ids) or len(set(invalid_ids)) != len(invalid_ids):
        errors.append("invalid_or_duplicate_invalid_episode_id")
    invalid_to_valid: dict[str, str] = {}
    invalid_counts_by_valid_episode: dict[str, int] = {}
    for item in invalid_attempts:
        invalid_id = str(item.get("episode_id") or "")
        valid_id = str(item.get("resolved_by_episode_id") or "")
        if not valid_id:
            errors.append("unresolved_infrastructure_invalid_attempt")
        invalid_to_valid[invalid_id] = valid_id
        invalid_counts_by_valid_episode[valid_id] = invalid_counts_by_valid_episode.get(valid_id, 0) + 1
    if any(count > 2 for count in invalid_counts_by_valid_episode.values()):
        errors.append("infrastructure_invalid_attempt_limit_exceeded")

    valid_to_invalid: dict[str, set[str]] = {}
    for item in summaries:
        links = {str(value) for value in item.get("resolves_invalid_episode_ids") or []}
        valid_to_invalid[str(item.get("episode_id") or "")] = links
    valid_id_set = set(valid_ids)
    invalid_id_set = set(invalid_ids)
    if any(
        valid_id not in valid_id_set
        or invalid_id not in valid_to_invalid.get(valid_id, set())
        for invalid_id, valid_id in invalid_to_valid.items()
    ) or {value for values in valid_to_invalid.values() for value in values} != invalid_id_set:
        errors.append("invalid_replacement_bidirectional_link_mismatch")
    valid_task_by_id = {str(item.get("episode_id")): str(item.get("task_name")) for item in summaries}
    if any(valid_task_by_id.get(valid_id) != str(item.get("task_name")) for item, valid_id in ((item, invalid_to_valid.get(str(item.get("episode_id") or ""), "")) for item in invalid_attempts)):
        errors.append("invalid_replacement_task_mismatch")
    if lifecycle_errors:
        errors.append("suite_lifecycle_error")
    return list(dict.fromkeys(errors))


__all__ = [
    "AUDIT_SCHEMA", "CHECKPOINT_SCHEMA", "CONFIG_PATH", "CONFIG_SCHEMA",
    "EXPERIMENT_ID", "GATE_TASKS", "GENERATION_SEED", "LIVE_RECEIPT_PATH",
    "LIVE_RECEIPT_FIELDS", "LIVE_RECEIPT_SCHEMA", "MECHANISM_ID", "MODEL_ID", "MODEL_MANIFEST_SHA256",
    "MODEL_REALPATH", "MODEL_REVISION", "OFFICIAL_SYSTEM_PROMPT_SHA256",
    "OFFLINE_REPLAY_SCHEMA", "PARENT_EVIDENCE_COMMIT", "PREFLIGHT_PATH",
    "PREFLIGHT_SCHEMA", "REFERENCE_SEGMENT_SCHEMA", "REMAINING_TASKS",
    "RESULT_SCHEMA", "REVIEW_COMMIT", "SOURCE_FILES", "TASK_COUNT", "TASK_ORDER",
    "TASK_SEED", "canonical_json_sha256", "exact_completion_errors", "file_sha256",
    "preservation_report", "source_freeze_payload", "validate_launch_receipt",
    "validate_preflight_report", "validate_source_freeze",
]
