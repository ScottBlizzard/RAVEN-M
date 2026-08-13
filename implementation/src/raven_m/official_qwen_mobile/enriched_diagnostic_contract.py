"""Fail-closed contract for the post-hoc enriched six-task memory diagnostic."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
PROTOCOL_ID = "ENRICHED_MEMORY_DIAGNOSTIC6_V1"
PARENT_COMMIT = "6e16743fce8a4cab87201a112d2336e2d5ea9c69"
MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
MODEL_REALPATH = "/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope"
MODEL_MANIFEST_SHA256 = "18e0909c7d993853d6d0f62443461a74009754f90db026a1723cab80121c7872"
TASK_SEED = 20260806
GENERATION_SEED = 3407
PORT = 18000

TASKS = (
    "OsmAndTrack",
    "RecipeAddMultipleRecipesFromImage",
    "RecipeAddMultipleRecipesFromMarkor",
    "RecipeDeleteMultipleRecipesWithConstraint",
    "RetroSavePlaylist",
    "SaveCopyOfReceiptTaskEval",
)
ARM_ORDER = ("a10v2", "a11", "a12")
ARM_BINDINGS = {
    "a10v2": {
        "experiment_id": "A10V2_DIAG6_EMOBF_QWEN3VL32B_AW_HARD_T20260806_G3407_V1",
        "source_mechanism_id": "a10_v2_evidence_matured_obligation_branch_frontier_v2",
    },
    "a11": {
        "experiment_id": "A11_DIAG6_CRC_ECOBF_QWEN3VL32B_AW_HARD_T20260806_G3407_V1",
        "source_mechanism_id": "a11_confirmed_route_contraction_ecobf_v1",
    },
    "a12": {
        "experiment_id": "A12_DIAG6_MADM_QWEN3VL32B_AW_HARD_T20260806_G3407_V1",
        "source_mechanism_id": "a12_minimal_action_divergence_memory_v1",
    },
}

MANIFEST_PATH = REPOSITORY_ROOT / "implementation/configs/enriched_memory_diagnostic6_instances.json"
PREFLIGHT_PATH = REPOSITORY_ROOT / "evidence/diag6/ENRICHED_MEMORY_DIAGNOSTIC6_ZERO_GENERATION_PREFLIGHT.json"
PREFLIGHT_SCHEMA = "enriched_memory_diagnostic6_zero_generation_preflight_v1"
RECEIPT_SCHEMA = "enriched_memory_diagnostic6_live_server_receipt_v1"
INTENT_SCHEMA = "enriched_memory_diagnostic6_server_launch_intent_v1"

SOURCE_FILES = (
    "protocols/ENRICHED_MEMORY_DIAGNOSTIC6_PROTOCOL_2026-08-13.md",
    "implementation/configs/enriched_memory_diagnostic6_instances.json",
    "implementation/scripts/run_enriched_memory_diagnostic.py",
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/preflight_enriched_memory_diagnostic.py",
    "implementation/scripts/qualify_enriched_memory_diagnostic_server.py",
    "implementation/scripts/start_enriched_memory_diagnostic_server.sh",
    "implementation/src/raven_m/official_qwen_mobile/enriched_diagnostic_contract.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/official_qwen_mobile/a10_v2_obligation_branch_frontier.py",
    "implementation/src/raven_m/official_qwen_mobile/a11_confirmed_route_contraction.py",
    "implementation/src/raven_m/official_qwen_mobile/a12_minimal_action_divergence.py",
    "implementation/tests/official_qwen_mobile/test_enriched_memory_diagnostic.py",
    "implementation/tests/official_qwen_mobile/test_a10v2_a11_shared_integration.py",
    "implementation/tests/official_qwen_mobile/test_a12_controller_integration.py",
)

EVIDENCE_FILES = (
    "evidence/a10_v2/A10_V2_OFFLINE_REPLAY_REPORT.json",
    "evidence/a11/A11_OFFLINE_REPLAY_REPORT.json",
    "evidence/a12/A12_REFERENCE_SEGMENTS.json",
)


def file_sha256(path: Path) -> str:
    payload = path.read_bytes()
    if path.suffix.casefold() in {".json", ".md", ".py", ".sh"}:
        payload = payload.replace(b"\r\n", b"\n")
    return sha256(payload).hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(REPOSITORY_ROOT), *args], text=True
    ).strip()


def source_hashes() -> dict[str, str]:
    missing = [name for name in SOURCE_FILES if not (REPOSITORY_ROOT / name).is_file()]
    if missing:
        raise RuntimeError(f"diagnostic source closure incomplete: {missing}")
    return {name: file_sha256(REPOSITORY_ROOT / name) for name in SOURCE_FILES}


def evidence_hashes() -> dict[str, str]:
    missing = [name for name in EVIDENCE_FILES if not (REPOSITORY_ROOT / name).is_file()]
    if missing:
        raise RuntimeError(f"diagnostic evidence closure incomplete: {missing}")
    return {name: file_sha256(REPOSITORY_ROOT / name) for name in EVIDENCE_FILES}


def load_manifest() -> dict[str, Any]:
    value = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    instances = list(value.get("instances") or [])
    keys = tuple((str(item["task_class"]), int(item["task_seed"])) for item in instances)
    if keys != tuple((name, TASK_SEED) for name in TASKS):
        raise RuntimeError("enriched diagnostic manifest task identity/order drift")
    if any(int(item["native_max_steps"]) <= 0 for item in instances):
        raise RuntimeError("enriched diagnostic native task budget invalid")
    return value


def validate_preflight_report(path: Path = PREFLIGHT_PATH) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    expected = {
        "schema": PREFLIGHT_SCHEMA,
        "status": "pass",
        "protocol_id": PROTOCOL_ID,
        "parent_commit": PARENT_COMMIT,
        "generation_calls": 0,
        "diagnostic_live_authorized": True,
        "formal_arm_status_repaired": False,
        "manifest_sha256": file_sha256(MANIFEST_PATH),
        "source_sha256": source_hashes(),
        "evidence_sha256": evidence_hashes(),
        "task_order": list(TASKS),
        "arm_order": list(ARM_ORDER),
        "arm_bindings": ARM_BINDINGS,
        "errors": [],
    }
    for key, value in expected.items():
        if report.get(key) != value:
            errors.append(f"{key}_drift")
    commit = str(report.get("implementation_commit") or "")
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        errors.append("implementation_commit_invalid")
    else:
        try:
            if subprocess.run(
                ["git", "-C", str(REPOSITORY_ROOT), "merge-base", "--is-ancestor", commit, "HEAD"],
                capture_output=True,
                check=False,
            ).returncode:
                errors.append("implementation_commit_not_ancestor")
            if subprocess.run(
                ["git", "-C", str(REPOSITORY_ROOT), "merge-base", "--is-ancestor", PARENT_COMMIT, commit],
                capture_output=True,
                check=False,
            ).returncode:
                errors.append("parent_commit_not_ancestor")
            if _git("status", "--porcelain", "--untracked-files=all"):
                errors.append("worktree_not_clean")
        except (OSError, subprocess.SubprocessError):
            errors.append("git_provenance_validation_failed")
    checks = report.get("checks") or {}
    required_checks = {
        "six_task_manifest_exact",
        "a10v2_common_six_offline_reads",
        "a11_common_six_offline_reads",
        "a12_common_six_strict_opportunities",
        "source_mechanisms_unchanged",
        "single_transport_policy",
        "zero_extra_model_calls",
        "no_guard_or_action_override",
        "diagnostic_not_formal_repair",
        "targeted_tests_passed",
    }
    if set(checks) != required_checks or any(value is not True for value in checks.values()):
        errors.append("preflight_checks_not_exact_pass")
    if errors:
        raise RuntimeError(f"enriched diagnostic preflight invalid: {errors}")
    return report


def validate_launch_receipt(
    path: Path,
    *,
    preflight_path: Path = PREFLIGHT_PATH,
) -> dict[str, Any]:
    preflight = validate_preflight_report(preflight_path)
    receipt = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    expected = {
        "schema": RECEIPT_SCHEMA,
        "status": "pass",
        "protocol_id": PROTOCOL_ID,
        "generation_calls": 0,
        "preflight_sha256": file_sha256(preflight_path),
        "implementation_commit": preflight["implementation_commit"],
        "served_model_id": MODEL_ID,
        "model_realpath": MODEL_REALPATH,
        "model_manifest_sha256": MODEL_MANIFEST_SHA256,
        "port": PORT,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            errors.append(f"{key}_drift")
    pid = receipt.get("process_pid")
    command = receipt.get("process_cmdline")
    if not isinstance(pid, int) or pid <= 1:
        errors.append("process_pid_invalid")
    if not isinstance(command, list) or "serve" not in command or MODEL_REALPATH not in command:
        errors.append("process_cmdline_invalid")
    if receipt.get("observed_served_model_ids") != [MODEL_ID]:
        errors.append("observed_model_ids_invalid")
    if not isinstance(receipt.get("packages"), dict):
        errors.append("package_versions_missing")
    try:
        timestamp = datetime.fromisoformat(str(receipt.get("qualification_timestamp")))
        if timestamp.tzinfo is None or timestamp > datetime.now(timezone.utc):
            errors.append("qualification_timestamp_invalid")
    except ValueError:
        errors.append("qualification_timestamp_invalid")
    if os.name == "posix" and isinstance(pid, int):
        try:
            os.kill(pid, 0)
            live_command = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
            if [item.decode(errors="replace") for item in live_command if item] != command:
                errors.append("live_process_cmdline_drift")
        except (OSError, ValueError):
            errors.append("live_process_not_running")
    if errors:
        raise RuntimeError(f"enriched diagnostic live receipt invalid: {errors}")
    return receipt


__all__ = [
    "ARM_BINDINGS", "ARM_ORDER", "EVIDENCE_FILES", "GENERATION_SEED",
    "INTENT_SCHEMA", "MANIFEST_PATH", "MODEL_ID", "MODEL_MANIFEST_SHA256",
    "MODEL_REALPATH", "MODEL_REVISION", "PARENT_COMMIT", "PORT",
    "PREFLIGHT_PATH", "PREFLIGHT_SCHEMA", "PROTOCOL_ID", "RECEIPT_SCHEMA",
    "SOURCE_FILES", "TASKS", "TASK_SEED", "canonical_sha256", "evidence_hashes",
    "file_sha256", "load_manifest", "source_hashes", "validate_launch_receipt",
    "validate_preflight_report",
]
