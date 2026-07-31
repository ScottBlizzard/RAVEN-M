"""Launch the isolated M0 Files smoke for the r55 candidate."""

from __future__ import annotations

import json
from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
SOURCE_COMMIT = "66370821e2fd7577d8c7a508f80297ae1a4b1513"
SOURCE_TAG = "protocol-v2-2-r55-local-candidate"
BASE_MANIFEST = (
    PROJECT_ROOT / "configs/experiments/v2_2_capability_gate_r54.json"
)
GENERATED_MANIFEST = (
    REPOSITORY_ROOT
    / "runs/protocol_v2_2_development/manifests/"
    "v2_2_r55_candidate.generated.json"
)
UPDATED_FREEZE_HASHES = {
    "05_project/src/raven_m/controller/episode_controller.py": (
        "178f5a2f36a24fff6c3e2ffa33274c0d7fe1d7005b86144dee0b73babc603ef8"
    ),
}


def build_candidate_manifest() -> Path:
    """Derive r55 without changing the immutable formal r54 manifest."""
    manifest = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
    manifest.update(
        {
            "schema_version": "protocol_v2_2_r55_candidate_smoke.v1",
            "manifest_id": "protocol_v2_2_seed20260729_r55_candidate",
            "source_tag": SOURCE_TAG,
            "source_commit": SOURCE_COMMIT,
            "suite_id": "nonhard_capability_v2_2_seed20260729_r55_candidate",
            "output_root": "runs/protocol_v2_2_development",
        }
    )
    records_by_path = {
        record["path"]: record for record in manifest["freeze_files"]
    }
    if not UPDATED_FREEZE_HASHES.keys() <= records_by_path.keys():
        raise RuntimeError("Candidate freeze override is absent from r54.")
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

