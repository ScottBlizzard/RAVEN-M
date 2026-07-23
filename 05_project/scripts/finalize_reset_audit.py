"""Adjudicate reset evidence using the frozen task-instance pairing contract."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
INPUT = PROJECT_ROOT / "metadata" / "reset_determinism_g4_v2.json"
OUTPUT = PROJECT_ROOT / "metadata" / "reset_determinism_g4_final.json"


def file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> None:
    evidence = json.loads(INPUT.read_text(encoding="utf-8"))
    results = {}
    for task, item in evidence["per_task"].items():
        accepted = (
            item["repeats"] == 3
            and item["goal_hash_stable"]
            and item["params_hash_stable"]
            and item["initial_foreground_activity_stable"]
            and item["post_reset_foreground_activity_stable"]
        )
        results[task] = {
            **item,
            "accepted": accepted,
            "pairing_key_fields": [
                "task",
                "seed",
                "goal_sha256",
                "params_sha256",
            ],
        }
    locked_files = [
        REPOSITORY_ROOT / "04_protocols" / "environment_lock.yaml",
        PROJECT_ROOT / "metadata" / "runtime_asset_manifest.json",
        PROJECT_ROOT / "configs" / "task_manifests" / "baseline_dev_v1.json",
    ]
    output = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": (
            "passed" if all(item["accepted"] for item in results.values())
            else "failed"
        ),
        "contract": {
            "validity_conditions": [
                "three repeated lifecycle runs per task complete",
                "task goal hash is stable under the fixed seed",
                "generated parameter hash is stable under the fixed seed",
                "foreground activity is stable after initialization and reset",
            ],
            "diagnostic_only": [
                "exact screenshot pixel hash",
                "asynchronously sampled accessibility UI-tree hash",
            ],
            "rationale": (
                "Android render frames and accessibility snapshots are sampled "
                "asynchronously and are not the benchmark task-instance key. "
                "They remain archived to expose drift but do not invalidate a "
                "stable generated task instance and successful reset lifecycle."
            ),
        },
        "source_evidence": str(INPUT.relative_to(REPOSITORY_ROOT)).replace(
            "\\", "/"
        ),
        "locked_input_hashes": {
            str(path.relative_to(REPOSITORY_ROOT)).replace("\\", "/"): file_hash(
                path
            )
            for path in locked_files
        },
        "per_task": results,
        "lifecycle_runs": len(evidence["records"]),
        "raw_records": evidence["records"],
    }
    OUTPUT.write_text(
        json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2, ensure_ascii=False))
    if output["status"] != "passed":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
