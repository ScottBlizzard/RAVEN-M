"""Launch the isolated M0 development smoke for the r41 candidate."""

from __future__ import annotations

import json
from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
SOURCE_COMMIT = "84a587917dfd090d3d3c8dc92eef8c0e4dddd580"
SOURCE_TAG = "protocol-v2-2-r41-local-candidate"
BASE_MANIFEST = (
    PROJECT_ROOT / "configs/experiments/v2_2_capability_gate_r39.json"
)
GENERATED_MANIFEST = (
    REPOSITORY_ROOT
    / "runs/protocol_v2_2_development/manifests/"
    "v2_2_r41_candidate.generated.json"
)
UPDATED_FREEZE_HASHES = {
    "05_project/src/raven_m/controller/episode_controller.py": (
        "40a7af2fe6baf2eba526a188696808c6fa3de9aead503e980a2457099cb059a1"
    ),
    "05_project/src/raven_m/controller/protocol_v2_guard.py": (
        "47d7baefa9969e8f9a390a36bfc9e0a5b8cb6cc94e4b0cf83ef95d930a3c9d19"
    ),
    "05_project/src/raven_m/memory/manager.py": (
        "845c07991fc88709674ba80f7255b1302a25563b4d3140e4a4bc4b9d825437cf"
    ),
}


def build_candidate_manifest() -> Path:
    """Derive r41 without changing the immutable r39 manifest."""
    manifest = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
    manifest.update(
        {
            "schema_version": "protocol_v2_2_r41_candidate_smoke.v1",
            "manifest_id": "protocol_v2_2_seed20260729_r41_candidate",
            "source_tag": SOURCE_TAG,
            "source_commit": SOURCE_COMMIT,
            "suite_id": "nonhard_capability_v2_2_seed20260729_r41_candidate",
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
