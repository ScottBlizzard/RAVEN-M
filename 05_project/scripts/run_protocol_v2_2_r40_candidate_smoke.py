"""Launch auditable development smokes for the protocol-v2.2 r40 candidate."""

from __future__ import annotations

import json
from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
SOURCE_COMMIT = "16f8ff8084774e12205d28e7ece5f272b697b0b1"
SOURCE_TAG = "protocol-v2-2-r40-local-candidate"
BASE_MANIFEST = (
    PROJECT_ROOT / "configs/experiments/v2_2_capability_gate_r39.json"
)
GENERATED_MANIFEST = (
    REPOSITORY_ROOT
    / "runs/protocol_v2_2_development/manifests/"
    "v2_2_r40_candidate.generated.json"
)
UPDATED_FREEZE_HASHES = {
    "05_project/src/raven_m/controller/episode_controller.py": (
        "977776dd203f62b06271323a74ac6dd483777ad3eda4da974f5eb72817ae4271"
    ),
    "05_project/src/raven_m/controller/protocol_v2_guard.py": (
        "19a57a0c97ed47019efbdc7cdd2c570663350259ead32561885e0e34e3fbe9a3"
    ),
    "05_project/src/raven_m/memory/manager.py": (
        "dbb7f5c8c0322c42035000e43896071f2a0e11195f66b3e040067b3e29c7f0b4"
    ),
}


def build_candidate_manifest() -> Path:
    """Derive a candidate manifest without modifying the frozen r39 file."""
    manifest = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
    manifest.update(
        {
            "schema_version": "protocol_v2_2_r40_candidate_smoke.v1",
            "manifest_id": "protocol_v2_2_seed20260729_r40_candidate",
            "source_tag": SOURCE_TAG,
            "source_commit": SOURCE_COMMIT,
            "suite_id": "nonhard_capability_v2_2_seed20260729_r40_candidate",
            "output_root": "runs/protocol_v2_2_development",
        }
    )
    records_by_path = {
        record["path"]: record for record in manifest["freeze_files"]
    }
    if not UPDATED_FREEZE_HASHES.keys() <= records_by_path.keys():
        raise RuntimeError("Candidate freeze override is absent from r39.")
    for path, digest in UPDATED_FREEZE_HASHES.items():
        records_by_path[path]["sha256"] = digest
    GENERATED_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    GENERATED_MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return GENERATED_MANIFEST


if __name__ == "__main__":
    raise SystemExit(
        main(
            default_manifest=build_candidate_manifest(),
            expected_source_commit=SOURCE_COMMIT,
        )
    )
