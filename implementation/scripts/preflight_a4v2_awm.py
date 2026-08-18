#!/usr/bin/env python3
"""Fail-closed, zero-generation preflight for faithful offline AWM."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.official_qwen_mobile.a4v2_faithful_awm import (  # noqa: E402
    MECHANISM_ID,
    validate_bank,
    validate_acquisition_receipt,
)
from raven_m.official_qwen_mobile.protocol import A4V2_WORKFLOW_SYSTEM_PROMPT  # noqa: E402


EXPERIMENT_ID = "A4V2_FAITHFUL_OFFLINE_AWM_QWEN3VL32B_AW_HARD_S20260806_V1"
SEVEN = [
    "BrowserMultiply",
    "ExpenseDeleteMultiple2",
    "RetroSavePlaylist",
    "SimpleCalendarAddOneEvent",
    "SportsTrackerTotalDurationForCategoryThisWeek",
    "RecipeDeleteMultipleRecipesWithConstraint",
    "OsmAndMarker",
]
SOURCE_PATHS = [
    "implementation/scripts/materialize_a4v2_donor_manifest.py",
    "implementation/scripts/run_a4v2_donor_acquisition.py",
    "implementation/scripts/build_a4v2_donor_source_lock.py",
    "implementation/scripts/qualify_a4v2_acquisition_server.py",
    "implementation/scripts/start_a4v2_acquisition_server.sh",
    "implementation/scripts/run_a4v2_campaign.py",
    "implementation/scripts/finalize_a4v2_result.py",
    "implementation/scripts/finalize_a4v2_ablation.py",
    "implementation/scripts/build_a4v2_shuffled_ablation_bank.py",
    "implementation/scripts/audit_a4v2_cpu_readiness.py",
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/preflight_a4v2_awm.py",
    "implementation/scripts/qualify_a4v2_live_server.py",
    "implementation/scripts/build_a4v2_induction_packets.py",
    "implementation/scripts/freeze_a4v2_workflow_bank.py",
    "implementation/scripts/run_a4v2_offline_induction.py",
    "implementation/src/raven_m/official_qwen_mobile/a4v2_faithful_awm.py",
    "implementation/src/raven_m/official_qwen_mobile/a4v2_induction.py",
    "implementation/src/raven_m/official_qwen_mobile/controller.py",
    "implementation/src/raven_m/official_qwen_mobile/protocol.py",
    "implementation/src/raven_m/official_qwen_mobile/working_memory.py",
    "implementation/src/raven_m/models/vllm_client.py",
    "implementation/src/raven_m/env/androidworld_adapter.py",
    "implementation/src/raven_m/multi_framework_benchmark/task_instances.py",
    "implementation/tests/official_qwen_mobile/test_a4v2_faithful_awm.py",
    "implementation/tests/official_qwen_mobile/test_a4v2_induction.py",
    "implementation/tests/official_qwen_mobile/test_a4v2_runner_contract.py",
    "implementation/tests/official_qwen_mobile/test_a4v2_donor_pipeline.py",
    "implementation/tests/official_qwen_mobile/test_a4v2_finalizer.py",
    "implementation/configs/a4v2_awm_donor_acquisition_plan.json",
    "implementation/configs/androidworld_hard_v2_instances.json",
    "protocols/A4V2_FAITHFUL_OFFLINE_AWM_PREREG_2026-08-18.md",
    "protocols/A4V2_EXECUTION_RUNBOOK_2026-08-18.md",
    "protocols/A4V2_DONOR_ACQUISITION_PLAN_V2_AMENDMENT_2026-08-19.md",
]


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _json_digest(value: Any) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _content_valid(value: dict[str, Any]) -> bool:
    return value.get("content_sha256") == _json_digest(
        {key: item for key, item in value.items() if key != "content_sha256"}
    )


def _load_content(path: Path, schema: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != schema or not _content_valid(value):
        raise RuntimeError(f"invalid or drifted {schema}: {path}")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bank",
        type=Path,
        default=REPOSITORY_ROOT / "evidence/a4v2/A4V2_FROZEN_WORKFLOW_BANK.json",
    )
    parser.add_argument("--source-lock", type=Path, default=REPOSITORY_ROOT / "evidence/a4v2/A4V2_DONOR_SOURCE_LOCK.json")
    parser.add_argument("--induction-index", type=Path, default=REPOSITORY_ROOT / "evidence/a4v2/induction_packets/index.json")
    parser.add_argument("--induction-checkpoint", type=Path, default=REPOSITORY_ROOT / "evidence/a4v2/induction_responses/checkpoint.json")
    parser.add_argument("--responses-dir", type=Path, default=REPOSITORY_ROOT / "evidence/a4v2/induction_responses")
    parser.add_argument("--acquisition-receipt", type=Path, required=True)
    parser.add_argument("--source-freeze-output", type=Path, default=REPOSITORY_ROOT / "evidence/a4v2/A4V2_SOURCE_FREEZE.json")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "evidence/a4v2/A4V2_ZERO_GENERATION_PREFLIGHT.json",
    )
    args = parser.parse_args()
    errors: list[str] = []
    try:
        implementation_commit = subprocess.check_output(
            ["git", "-C", str(REPOSITORY_ROOT), "rev-parse", "HEAD"], text=True
        ).strip()
        dirty = subprocess.check_output(
            ["git", "-C", str(REPOSITORY_ROOT), "status", "--porcelain", "--untracked-files=all"], text=True
        ).strip()
        if dirty:
            errors.append("worktree_dirty")
    except Exception as exc:
        implementation_commit = None
        errors.append(f"git_identity_failed:{type(exc).__name__}:{exc}")
    bank_count = 0
    bank: dict[str, Any] = {}
    if not args.bank.is_file():
        errors.append("frozen_workflow_bank_missing")
    else:
        try:
            bank = json.loads(args.bank.read_text(encoding="utf-8"))
            bank_count = len(validate_bank(bank))
        except Exception as exc:
            errors.append(f"workflow_bank_invalid:{type(exc).__name__}:{exc}")

    source_freeze: dict[str, str] = {}
    for relative in SOURCE_PATHS:
        path = REPOSITORY_ROOT / relative
        if not path.is_file():
            errors.append(f"source_missing:{relative}")
        else:
            source_freeze[relative] = _sha(path)

    evidence_freeze: dict[str, str] = {}
    try:
        source_lock = _load_content(args.source_lock.resolve(), "a4v2.donor_source_lock.v1")
        routes = source_lock.get("route_groups") or []
        if source_lock.get("status") != "ready" or source_lock.get("scored_hard_inputs_used") is not False or len(routes) != 7:
            raise RuntimeError("source lock route/status closure failed")
        if any(len(group.get("donors") or []) < 2 for group in routes):
            raise RuntimeError("source lock donor coverage failed")
        evidence_freeze[str(args.source_lock.resolve().relative_to(REPOSITORY_ROOT.resolve())).replace("\\", "/")] = _sha(args.source_lock)
        manifest_hashes = list(source_lock.get("manifest_file_sha256s") or [])
        donor_manifests = sorted((REPOSITORY_ROOT / "evidence/a4v2").glob("A4V2_DONOR_ACQUISITION_MANIFEST_*.json"))
        matched = [path for path in donor_manifests if _sha(path) in manifest_hashes]
        if len(matched) != len(manifest_hashes) or set(map(_sha, matched)) != set(manifest_hashes):
            raise RuntimeError("source lock/donor manifest drift")
        for donor_manifest in matched:
            key = str(donor_manifest.resolve().relative_to(REPOSITORY_ROOT.resolve())).replace("\\", "/")
            evidence_freeze[key] = _sha(donor_manifest)
    except Exception as exc:
        errors.append(f"source_lock_invalid:{type(exc).__name__}:{exc}")
        source_lock = {}
    try:
        index = json.loads(args.induction_index.read_text(encoding="utf-8"))
        if index.get("schema") != "a4v2.awm_induction_index.v1" or len(index.get("packets") or []) != 7:
            raise RuntimeError("induction index closure failed")
        if index.get("source_lock_sha256") != _sha(args.source_lock):
            raise RuntimeError("induction index/source lock drift")
        evidence_freeze[str(args.induction_index.resolve().relative_to(REPOSITORY_ROOT.resolve())).replace("\\", "/")] = _sha(args.induction_index)
        for row in index["packets"]:
            packet_path = REPOSITORY_ROOT / row["packet_path"]
            if not packet_path.is_file() or _sha(packet_path) != row["packet_sha256"]:
                raise RuntimeError(f"induction packet drift:{row['route_id']}")
            evidence_freeze[row["packet_path"]] = _sha(packet_path)
    except Exception as exc:
        errors.append(f"induction_index_invalid:{type(exc).__name__}:{exc}")
        index = {}
    try:
        checkpoint = _load_content(args.induction_checkpoint.resolve(), "a4v2.awm_induction_checkpoint.v1")
        acquisition_receipt = validate_acquisition_receipt(args.acquisition_receipt.resolve())
        calls = checkpoint.get("calls") or []
        if (
            checkpoint.get("status") != "complete"
            or checkpoint.get("generation_calls") != 7
            or checkpoint.get("induction_index_sha256") != _sha(args.induction_index)
            or len(calls) != 7
            or len({str(call.get("route_id")) for call in calls}) != 7
            or any(call.get("transport_attempts") != 1 for call in calls)
            or checkpoint.get("server_receipt_sha256") != _sha(args.acquisition_receipt)
            or checkpoint.get("server_receipt_content_sha256") != acquisition_receipt.get("content_sha256")
        ):
            raise RuntimeError("induction checkpoint closure failed")
        provenance = bank.get("induction") if isinstance(bank, dict) else {}
        if (
            provenance.get("packet_index_sha256") != _sha(args.induction_index)
            or provenance.get("checkpoint_sha256") != _sha(args.induction_checkpoint)
            or provenance.get("checkpoint_content_sha256") != checkpoint.get("content_sha256")
        ):
            raise RuntimeError("workflow bank/induction evidence drift")
        evidence_freeze[str(args.induction_checkpoint.resolve().relative_to(REPOSITORY_ROOT.resolve())).replace("\\", "/")] = _sha(args.induction_checkpoint)
        evidence_freeze[str(args.acquisition_receipt.resolve().relative_to(REPOSITORY_ROOT.resolve())).replace("\\", "/")] = _sha(args.acquisition_receipt)
        for call in calls:
            response_path = args.responses_dir / f"{call['route_id']}.txt"
            if not response_path.is_file() or _sha(response_path) != call.get("content_sha256"):
                raise RuntimeError(f"induction response drift:{call['route_id']}")
            evidence_freeze[str(response_path.resolve().relative_to(REPOSITORY_ROOT.resolve())).replace("\\", "/")] = _sha(response_path)
    except Exception as exc:
        errors.append(f"induction_checkpoint_invalid:{type(exc).__name__}:{exc}")
        checkpoint = {}

    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPOSITORY_ROOT), str(PROJECT_ROOT / "src"), env.get("PYTHONPATH", "")]
    )
    command = [
        sys.executable,
        "-m",
        "pytest",
        "implementation/tests/official_qwen_mobile/test_a4v2_faithful_awm.py",
        "implementation/tests/official_qwen_mobile/test_a4v2_induction.py",
        "implementation/tests/official_qwen_mobile/test_a4v2_runner_contract.py",
        "implementation/tests/official_qwen_mobile/test_a4v2_donor_pipeline.py",
        "implementation/tests/official_qwen_mobile/test_a4v2_finalizer.py",
        "-q",
        "-p",
        "no:cacheprovider",
    ]
    tests = subprocess.run(command, cwd=REPOSITORY_ROOT, env=env, capture_output=True, text=True, check=False)
    if tests.returncode != 0:
        errors.append("focused_tests_failed")

    hard = json.loads((REPOSITORY_ROOT / "implementation/configs/androidworld_hard_v2_instances.json").read_text(encoding="utf-8"))
    hard_order = [
        str(item["task_class"])
        for item in hard.get("instances") or []
        if int(item.get("task_seed", -1)) == 20260806
    ]
    names = {
        str(item["task_class"])
        for item in hard.get("instances") or []
        if int(item.get("task_seed", -1)) == 20260806
    }
    if not set(SEVEN).issubset(names):
        errors.append("fixed_seven_missing_from_hard_manifest")
    remaining_twelve = [name for name in hard_order if name not in SEVEN]
    if len(hard_order) != 19 or len(remaining_twelve) != 12:
        errors.append("remaining_twelve_manifest_closure_failed")

    freeze_digest = sha256(
        json.dumps(source_freeze, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    result = {
        "schema": "a4v2.zero_generation_preflight.v1",
        "experiment_id": EXPERIMENT_ID,
        "mechanism_id": MECHANISM_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "implementation_commit": implementation_commit,
        "status": "pass" if not errors else "fail",
        "generation_calls": 0,
        "workflow_bank_sha256": _sha(args.bank) if args.bank.is_file() else None,
        "workflow_count": bank_count,
        "bank_mode": (
            "shuffled_incompatible_active_control"
            if (bank.get("ablation") or {}).get("identity")
            == "A4V2_SHUFFLED_INCOMPATIBLE_CONTENT_ACTIVE_CONTROL_V1"
            else "primary_faithful_offline_awm"
        ),
        "system_prompt_sha256": sha256(A4V2_WORKFLOW_SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
        "seven_task_order": SEVEN,
        "remaining_twelve_order": remaining_twelve,
        "campaign_task_order_sha256": _json_digest(SEVEN + remaining_twelve),
        "source_freeze": source_freeze,
        "source_freeze_sha256": freeze_digest,
        "evidence_freeze": evidence_freeze,
        "evidence_freeze_sha256": _json_digest(evidence_freeze),
        "unit_tests": {
            "command": command,
            "returncode": tests.returncode,
            "stdout": tests.stdout,
            "stderr": tests.stderr,
        },
        "errors": errors,
    }
    result["content_sha256"] = _json_digest(result)
    source_payload = {
        "schema": "a4v2.source_freeze.v1",
        "experiment_id": EXPERIMENT_ID,
        "implementation_commit": implementation_commit,
        "source_files": source_freeze,
        "source_files_sha256": freeze_digest,
    }
    source_payload["content_sha256"] = _json_digest(source_payload)
    _atomic_json(args.source_freeze_output, source_payload)
    _atomic_json(args.output, result)
    print(json.dumps({"status": result["status"], "output": str(args.output), "errors": errors}, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
