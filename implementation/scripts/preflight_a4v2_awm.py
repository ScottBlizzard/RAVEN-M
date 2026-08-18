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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.official_qwen_mobile.a4v2_faithful_awm import (  # noqa: E402
    MECHANISM_ID,
    validate_bank,
)


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
    "implementation/scripts/run_official_qwen_mobile.py",
    "implementation/scripts/preflight_a4v2_awm.py",
    "implementation/scripts/qualify_a4v2_live_server.py",
    "implementation/scripts/build_a4v2_induction_packets.py",
    "implementation/scripts/freeze_a4v2_workflow_bank.py",
    "implementation/scripts/run_a4v2_offline_induction.py",
    "implementation/src/raven_m/official_qwen_mobile/a4v2_faithful_awm.py",
    "implementation/src/raven_m/official_qwen_mobile/a4v2_induction.py",
    "implementation/tests/official_qwen_mobile/test_a4v2_faithful_awm.py",
    "implementation/tests/official_qwen_mobile/test_a4v2_induction.py",
    "implementation/tests/official_qwen_mobile/test_a4v2_runner_contract.py",
    "implementation/configs/a4v2_awm_donor_acquisition_plan.json",
    "implementation/configs/androidworld_hard_v2_instances.json",
    "protocols/A4V2_FAITHFUL_OFFLINE_AWM_PREREG_2026-08-18.md",
    "protocols/A4V2_EXECUTION_RUNBOOK_2026-08-18.md",
]


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bank",
        type=Path,
        default=REPOSITORY_ROOT / "evidence/a4v2/A4V2_FROZEN_WORKFLOW_BANK.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "evidence/a4v2/A4V2_ZERO_GENERATION_PREFLIGHT.json",
    )
    args = parser.parse_args()
    errors: list[str] = []
    bank_count = 0
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
        "-q",
    ]
    tests = subprocess.run(command, cwd=REPOSITORY_ROOT, env=env, capture_output=True, text=True, check=False)
    if tests.returncode != 0:
        errors.append("focused_tests_failed")

    hard = json.loads((REPOSITORY_ROOT / "implementation/configs/androidworld_hard_v2_instances.json").read_text(encoding="utf-8"))
    names = {
        str(item["task_class"])
        for item in hard.get("instances") or []
        if int(item.get("task_seed", -1)) == 20260806
    }
    if not set(SEVEN).issubset(names):
        errors.append("fixed_seven_missing_from_hard_manifest")

    freeze_digest = sha256(
        json.dumps(source_freeze, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    result = {
        "schema": "a4v2.zero_generation_preflight.v1",
        "experiment_id": EXPERIMENT_ID,
        "mechanism_id": MECHANISM_ID,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not errors else "fail",
        "generation_calls": 0,
        "workflow_bank_sha256": _sha(args.bank) if args.bank.is_file() else None,
        "workflow_count": bank_count,
        "seven_task_order": SEVEN,
        "source_freeze": source_freeze,
        "source_freeze_sha256": freeze_digest,
        "unit_tests": {
            "command": command,
            "returncode": tests.returncode,
            "stdout": tests.stdout,
            "stderr": tests.stderr,
        },
        "errors": errors,
    }
    _atomic_json(args.output, result)
    print(json.dumps({"status": result["status"], "output": str(args.output), "errors": errors}, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
