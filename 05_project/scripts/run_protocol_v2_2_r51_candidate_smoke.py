"""Launch the isolated M0 Files smoke for the r51 candidate."""

from __future__ import annotations

import json
from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
SOURCE_COMMIT = "ee6f04a4624e964266836354e1e35a289f52aef9"
SOURCE_TAG = "protocol-v2-2-r51-local-candidate"
BASE_MANIFEST = (
    PROJECT_ROOT / "configs/experiments/v2_2_capability_gate_r45.json"
)
GENERATED_MANIFEST = (
    REPOSITORY_ROOT
    / "runs/protocol_v2_2_development/manifests/"
    "v2_2_r51_candidate.generated.json"
)
UPDATED_FREEZE_HASHES = {
    "05_project/src/raven_m/controller/episode_controller.py": (
        "10946b4511461cad0fde17ba8ba7de9634c53976076dd5c46fa5766ee29ba77b"
    ),
    "05_project/src/raven_m/controller/protocol_v2_guard.py": (
        "be6039ea3de40dffa51376fc5132a536d4f0e79f669e46d5bb1c65cbecd9c4ff"
    ),
    "05_project/prompts/planner_v1.md": (
        "41539b48a656218f4c3f334ce88c5a51f568f550948c4b9ccafe782175949ea5"
    ),
}


def build_candidate_manifest() -> Path:
    """Derive r51 without changing an immutable formal manifest."""
    manifest = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
    manifest.update(
        {
            "schema_version": "protocol_v2_2_r51_candidate_smoke.v1",
            "manifest_id": "protocol_v2_2_seed20260729_r51_candidate",
            "source_tag": SOURCE_TAG,
            "source_commit": SOURCE_COMMIT,
            "suite_id": "nonhard_capability_v2_2_seed20260729_r51_candidate",
            "output_root": "runs/protocol_v2_2_development",
        }
    )
    records_by_path = {
        record["path"]: record for record in manifest["freeze_files"]
    }
    if not UPDATED_FREEZE_HASHES.keys() <= records_by_path.keys():
        raise RuntimeError("Candidate freeze override is absent from r45.")
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

