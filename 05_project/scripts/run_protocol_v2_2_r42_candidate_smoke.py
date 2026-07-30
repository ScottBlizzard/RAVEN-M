"""Launch the isolated M0 development smoke for the r42 candidate."""

from __future__ import annotations

import json
from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
SOURCE_COMMIT = "cb6cda50a6423c1e5292e9beb75958880f9e819e"
SOURCE_TAG = "protocol-v2-2-r42-local-candidate"
BASE_MANIFEST = (
    PROJECT_ROOT / "configs/experiments/v2_2_capability_gate_r39.json"
)
GENERATED_MANIFEST = (
    REPOSITORY_ROOT
    / "runs/protocol_v2_2_development/manifests/"
    "v2_2_r42_candidate.generated.json"
)
UPDATED_FREEZE_HASHES = {
    "05_project/src/raven_m/controller/episode_controller.py": (
        "07b256dccbaf57bb26a530facde4a29f157d5feb32a73a75b06571367bf8f492"
    ),
    "05_project/src/raven_m/controller/protocol_v2_guard.py": (
        "7fbb1b52c6193190bcaeca15976cc7e44f5794d095e5a81fc92c95fb4effe9ff"
    ),
    "05_project/src/raven_m/memory/manager.py": (
        "845c07991fc88709674ba80f7255b1302a25563b4d3140e4a4bc4b9d825437cf"
    ),
}


def build_candidate_manifest() -> Path:
    """Derive r42 without changing the immutable r39 manifest."""
    manifest = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
    manifest.update(
        {
            "schema_version": "protocol_v2_2_r42_candidate_smoke.v1",
            "manifest_id": "protocol_v2_2_seed20260729_r42_candidate",
            "source_tag": SOURCE_TAG,
            "source_commit": SOURCE_COMMIT,
            "suite_id": "nonhard_capability_v2_2_seed20260729_r42_candidate",
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
