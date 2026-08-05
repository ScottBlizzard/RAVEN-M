"""Freeze the four-framework H01/H06/H09/H17 Hard-pulse evidence ledger."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = REPO_ROOT / "05_project"
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.multi_framework_benchmark.capability_manifest import (  # noqa: E402
    sha256_file,
    verify_protected,
)


PULSE_IDS = ("H01", "H06", "H09", "H17")
ARMS = {
    "CB-PX-B3": ("01_b3", "raven"),
    "CB-PX-M0": ("02_m0", "raven"),
    "NS-PX-GO15": ("03_guiowl", "external"),
    "NS-PX-UIV4": ("04_uivoyager", "external"),
}
OUTPUTS = PROJECT_ROOT / "outputs/multi_framework_hard_pulse_v0_3"
MANIFESTS = PROJECT_ROOT / "configs/task_manifests/hard_pulse_v0_3"
DEST = PROJECT_ROOT / "metadata/multi_framework_hard_pulse_v0_3/final"
AUTHORIZATION = (
    PROJECT_ROOT
    / "metadata/multi_framework_s1b_v0_3/final/hard_pulse_authorization.json"
)
PROTOCOL = PROJECT_ROOT / "configs/experiments/multi_framework_hard_benchmark_v0_2.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def finite_reward(value):
    if isinstance(value, (int, float)) and math.isfinite(value):
        return float(value)
    return None


def relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def raven_cell(root: Path, expected_task: str) -> dict:
    report_path = root / "s1_report.json"
    report = load(report_path)
    rows = report.get("results", [])
    if len(rows) != 1 or rows[0].get("task_class") != expected_task:
        raise ValueError(f"Unexpected Raven result rows in {report_path}")
    row = rows[0]
    summary = row["summary"]
    evaluator_calls = int(row.get("evaluator_calls", 0))
    error = summary.get("error")
    reward = finite_reward(summary.get("evaluator_reward")) if evaluator_calls == 1 else None
    if evaluator_calls == 1 and error is None:
        outcome_class = "SUCCESS" if reward == 1.0 else "EVALUATED_FAILURE"
    else:
        outcome_class = "SCIENTIFIC_CONTROLLER_FAILURE"
    return {
        "outcome_class": outcome_class,
        "reward": reward,
        "steps": summary.get("decision_count"),
        "model_calls": summary.get("model_call_count"),
        "failure_code": summary.get("failure_code"),
        "error": error,
        "lifecycle": {
            "initialize": row.get("task_initialization", 0),
            "evaluator": evaluator_calls,
            "tear_down": row.get("task_teardown", 0),
            "post_episode_reset": row.get("post_episode_reset", 0),
        },
        "report": relative(report_path),
        "report_sha256": sha256_file(report_path),
        "run_id": report.get("run_id"),
        "task_manifest_sha256": report.get("task_manifest_sha256"),
    }


def external_cell(root: Path, expected_task: str) -> dict:
    report_path = root / "summary.json"
    report = load(report_path)
    rows = report.get("tasks", [])
    if len(rows) != 1 or rows[0].get("task") != expected_task:
        raise ValueError(f"Unexpected external result rows in {report_path}")
    row = rows[0]
    lifecycle = row.get("lifecycle", {})
    evaluator_calls = int(lifecycle.get("evaluator", 0))
    error = row.get("exception")
    reward = finite_reward(row.get("reward")) if evaluator_calls == 1 else None
    if evaluator_calls == 1 and error is None:
        outcome_class = "SUCCESS" if reward == 1.0 else "EVALUATED_FAILURE"
    else:
        outcome_class = "SCIENTIFIC_CONTROLLER_FAILURE"
    model_calls_path = root / "model_calls.json"
    return {
        "outcome_class": outcome_class,
        "reward": reward,
        "steps": row.get("steps"),
        "model_calls": row.get("model_calls", report.get("generation_calls")),
        "failure_code": None,
        "error": error,
        "lifecycle": {
            "initialize": lifecycle.get("initialize", 0),
            "evaluator": evaluator_calls,
            "tear_down": lifecycle.get("tear_down", 0),
            "post_episode_reset": None,
        },
        "report": relative(report_path),
        "report_sha256": sha256_file(report_path),
        "model_calls_report": relative(model_calls_path),
        "model_calls_report_sha256": sha256_file(model_calls_path),
        "run_id": report.get("run_id"),
        "task_manifest_sha256": report.get("task_manifest_sha256"),
    }


def invalid_attempts(task_root: Path, canonical: str) -> list[dict]:
    rows = []
    for path in sorted(task_root.glob(f"{canonical}.infra_*")):
        files = [item for item in path.rglob("*") if item.is_file()]
        rows.append(
            {
                "path": relative(path),
                "classification": "INFRASTRUCTURE_INVALID_PRESERVED",
                "file_count": len(files),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Write a non-frozen partial audit outside the final directory.",
    )
    args = parser.parse_args()

    protocol = load(PROTOCOL)
    verify_protected(REPO_ROOT, protocol["protected_paths"])
    authorization = load(AUTHORIZATION)
    if not authorization.get("hard_model_calls_authorized"):
        raise RuntimeError("Hard-pulse model calls were not authorized")

    cells = []
    missing = []
    for pulse_id in PULSE_IDS:
        manifest_path = MANIFESTS / f"{pulse_id}.json"
        manifest = load(manifest_path)
        tasks = manifest.get("tasks", [])
        if len(tasks) != 1:
            raise ValueError(f"Expected one task in {manifest_path}")
        expected_task = tasks[0]["task_class"]
        expected_manifest_sha256 = sha256_file(manifest_path)
        task_root = OUTPUTS / pulse_id
        for arm_id, (directory, family) in ARMS.items():
            root = task_root / directory
            report_path = root / ("s1_report.json" if family == "raven" else "summary.json")
            row = {
                "pulse_id": pulse_id,
                "task": expected_task,
                "arm_id": arm_id,
                "family": family,
                "invalid_infrastructure_attempts": invalid_attempts(task_root, directory),
            }
            if not report_path.is_file():
                row["outcome_class"] = "MISSING"
                missing.append(f"{pulse_id}/{arm_id}")
            else:
                parsed = (
                    raven_cell(root, expected_task)
                    if family == "raven"
                    else external_cell(root, expected_task)
                )
                row.update(parsed)
                observed_hash = row.get("task_manifest_sha256")
                row["task_manifest_hash_ok"] = (
                    observed_hash is None or observed_hash == expected_manifest_sha256
                )
            cells.append(row)

    scoreable = [row for row in cells if row.get("reward") is not None]
    successes = [row for row in scoreable if row["reward"] == 1.0]
    complete = not missing and len(cells) == len(PULSE_IDS) * len(ARMS)
    ledger = {
        "schema_version": "multi_framework_hard_pulse_ledger.v0.3",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "COMPLETE" if complete else "PARTIAL",
        "classification": "FROZEN_DEV_HARD_PULSE" if complete else "NON_FROZEN_PARTIAL_AUDIT",
        "authorization": relative(AUTHORIZATION),
        "authorization_sha256": sha256_file(AUTHORIZATION),
        "pulse_ids": list(PULSE_IDS),
        "arms": list(ARMS),
        "cell_count": len(cells),
        "completed_cell_count": len(cells) - len(missing),
        "scoreable_cell_count": len(scoreable),
        "success_count": len(successes),
        "scoreable_success_rate": len(successes) / len(scoreable) if scoreable else None,
        "missing_cells": missing,
        "cells": cells,
    }

    if complete:
        if DEST.exists():
            raise FileExistsError(f"Refusing to overwrite frozen ledger: {DEST}")
        DEST.mkdir(parents=True)
        destination = DEST / "hard_pulse_ledger.json"
    elif args.allow_partial:
        destination = PROJECT_ROOT / "metadata/multi_framework_hard_pulse_v0_3/partial_audit.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
    else:
        print(json.dumps({"status": "PARTIAL", "missing_cells": missing}, indent=2))
        raise SystemExit(2)
    destination.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": ledger["status"],
                "completed_cell_count": ledger["completed_cell_count"],
                "scoreable_cell_count": ledger["scoreable_cell_count"],
                "success_count": ledger["success_count"],
                "destination": relative(destination),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
