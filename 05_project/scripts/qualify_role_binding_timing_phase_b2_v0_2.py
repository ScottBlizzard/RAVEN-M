"""Run the single frozen Phase-B2 qualification after candidate-pool freeze."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.role_binding_timing.collection_v0_2 import (  # noqa: E402
    load_manifest,
    qualify_manifest,
    sha256_path,
    write_json,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "configs" / "role_binding_timing" / "phase_b2_collection_v0_2.json",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=PROJECT_ROOT / "schemas" / "role_binding_timing_snapshot_pool.v0_2.schema.json",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT / "artifacts" / "role_binding_timing" / "phase_b2_v0_2",
    )
    args = parser.parse_args()
    config = json.loads(args.config.resolve().read_text(encoding="utf-8"))
    output_root = args.output_root.resolve()
    manifest_path = output_root / config["capture"]["candidate_manifest"]
    pool_lock_path = output_root / config["capture"]["pool_lock"]
    qualification_path = output_root / config["capture"]["qualification_record"]
    if qualification_path.exists():
        raise RuntimeError("QUALIFICATION_ALREADY_EXECUTED")
    pool_lock = json.loads(pool_lock_path.read_text(encoding="utf-8"))
    if pool_lock["qualification_runs"] if "qualification_runs" in pool_lock else 0:
        raise RuntimeError("POOL_LOCK_ALREADY_QUALIFIED")
    if sha256_path(manifest_path) != pool_lock["candidate_manifest_sha256"]:
        raise RuntimeError("CANDIDATE_MANIFEST_CHANGED_AFTER_FREEZE")
    for item in pool_lock["files"]:
        path = REPOSITORY_ROOT / item["path"]
        if not path.is_file() or sha256_path(path) != item["sha256"]:
            raise RuntimeError(f"POOL_ARTIFACT_CHANGED:{item['path']}")
    manifest = load_manifest(manifest_path, args.schema.resolve())
    result = qualify_manifest(manifest, repository_root=REPOSITORY_ROOT, config=config)
    record = {
        "schema_version": "role_binding_timing.snapshot_qualification.v0_2",
        "study_id": "role_binding_timing_phase_b2_v0_2",
        "qualified_at": utc_now(),
        "qualification_run_index": 1,
        "pool_lock_path": pool_lock_path.relative_to(REPOSITORY_ROOT).as_posix(),
        "pool_lock_sha256": sha256_path(pool_lock_path),
        "candidate_manifest_path": manifest_path.relative_to(REPOSITORY_ROOT).as_posix(),
        "candidate_manifest_sha256": sha256_path(manifest_path),
        "generation_eligible": False,
        "generation_calls": 0,
        "model_endpoint_called": False,
        "candidate_replacements": 0,
        "same_version_recaptures": 0,
        "result": result,
    }
    write_json(qualification_path, record)
    print(json.dumps(record, ensure_ascii=False, indent=2))
    return 0 if result["verdict"] == "ELIGIBLE_FOR_PHASE_C_PREREGISTRATION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
