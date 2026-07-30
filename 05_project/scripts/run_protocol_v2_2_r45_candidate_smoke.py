"""Launch the isolated M0 development smoke for the r45 candidate."""

from __future__ import annotations

import json
from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
SOURCE_COMMIT = "3d0d719bfccac5934c62d3ab8be902a0ef66d7e9"
SOURCE_TAG = "protocol-v2-2-r45-local-candidate"
BASE_MANIFEST = (
    PROJECT_ROOT / "configs/experiments/v2_2_capability_gate_r39.json"
)
GENERATED_MANIFEST = (
    REPOSITORY_ROOT
    / "runs/protocol_v2_2_development/manifests/"
    "v2_2_r45_candidate.generated.json"
)
UPDATED_FREEZE_HASHES = {
    "05_project/src/raven_m/controller/episode_controller.py": (
        "7c86976d091fa87c4584b42709405e4bf62444d59074a0c02068aab91d505df4"
    ),
    "05_project/src/raven_m/controller/protocol_v2_guard.py": (
        "66a5943aa9582b1a88c18060712824e4d890a3c211b9243985d16df765dea45c"
    ),
    "05_project/src/raven_m/env/androidworld_adapter.py": (
        "08ebcf0b03a9e9b572d5fc866bf142667b78d1bfecd139b330ad745382476a04"
    ),
    "05_project/src/raven_m/memory/manager.py": (
        "845c07991fc88709674ba80f7255b1302a25563b4d3140e4a4bc4b9d825437cf"
    ),
    "05_project/prompts/executor_v2.md": (
        "ca1b74e992870afbb837f331755492e9a77c1d16340feed11a6445891dc660c8"
    ),
    "05_project/prompts/executor_raven_v2.md": (
        "adb9671ce327ed96de91a6f8f6ea68fd1c0d131c7b997237b7fca39ae6c15b46"
    ),
}


def build_candidate_manifest() -> Path:
    """Derive r45 without changing the immutable r39 manifest."""
    manifest = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
    manifest.update(
        {
            "schema_version": "protocol_v2_2_r45_candidate_smoke.v1",
            "manifest_id": "protocol_v2_2_seed20260729_r45_candidate",
            "source_tag": SOURCE_TAG,
            "source_commit": SOURCE_COMMIT,
            "suite_id": "nonhard_capability_v2_2_seed20260729_r45_candidate",
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
