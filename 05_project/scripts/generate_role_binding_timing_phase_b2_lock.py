"""Generate the pre-capture Phase-B2 source/config lock."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
OUTPUT = REPOSITORY_ROOT / "05_project" / "configs" / "role_binding_timing" / "phase_b2_collection_v0_2.lock.json"
PARENT_COMMIT = "99b342563061c9bb4bebbb72aa80ba91f4fa7a23"
FILES = (
    "04_protocols/role_binding_timing/phase_b2_snapshot_collection_v0_2.md",
    "05_project/contracts/role_binding_timing_snapshot_collection.v0_2.json",
    "05_project/schemas/role_binding_timing_snapshot_pool.v0_2.schema.json",
    "05_project/configs/role_binding_timing/phase_b2_collection_v0_2.json",
    "05_project/src/raven_m/role_binding_timing/collection_v0_2.py",
    "05_project/scripts/collect_role_binding_timing_phase_b2_v0_2.py",
    "05_project/scripts/qualify_role_binding_timing_phase_b2_v0_2.py",
    "05_project/scripts/generate_role_binding_timing_phase_b2_lock.py",
    "05_project/tests/role_binding_timing/test_phase_b2_collection.py",
)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> int:
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, text=True
    ).strip()
    if head != PARENT_COMMIT:
        raise RuntimeError(f"UNEXPECTED_PARENT_HEAD:{head}")
    records = []
    for relative in FILES:
        path = REPOSITORY_ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        records.append({"path": relative, "sha256": digest(path)})
    value = {
        "schema_version": "role_binding_timing.phase_b2_collection_lock.v0_2",
        "study_id": "role_binding_timing_phase_b2_v0_2",
        "phase": "B2",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "frozen_source_parent_commit": PARENT_COMMIT,
        "frozen_before_any_candidate_capture": True,
        "generation_calls_before_freeze": 0,
        "generation_eligible": False,
        "generation_calls_authorized": 0,
        "candidate_pool_version": "v0.2",
        "candidate_replacement_after_freeze": False,
        "files": records,
        "stop_rules": {
            "required_complete_families": 8,
            "minimum_apps": 4,
            "minimum_widget_families": 4,
            "maximum_families_per_app": 2,
            "minimum_family_qualification_rate": 0.95,
            "failed_pool_repair_requires_new_version": True,
            "launch_phase_c": False,
            "launch_generation": False
        }
    }
    OUTPUT.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT)
    print(digest(OUTPUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
