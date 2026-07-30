"""Launch the isolated M0 Files smoke for the r53 candidate."""

from __future__ import annotations

import json
from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
SOURCE_COMMIT = "f3d7c9d3c33e54245138fc56336027f533b67f17"
SOURCE_TAG = "protocol-v2-2-r53-local-candidate"
BASE_MANIFEST = (
    PROJECT_ROOT / "configs/experiments/v2_2_capability_gate_r45.json"
)
GENERATED_MANIFEST = (
    REPOSITORY_ROOT
    / "runs/protocol_v2_2_development/manifests/"
    "v2_2_r53_candidate.generated.json"
)
UPDATED_FREEZE_HASHES = {
    "05_project/src/raven_m/controller/episode_controller.py": (
        "4cc2b086e75effc42c2ab56eb60d2576b6c9e089b98136aaf509ee8a264455b0"
    ),
    "05_project/src/raven_m/controller/protocol_v2_guard.py": (
        "9fbc6633919415279cc2e05b3a2babd4b5248b3c69556b0a5dd0c6c4906c49ac"
    ),
    "05_project/prompts/planner_v1.md": (
        "41539b48a656218f4c3f334ce88c5a51f568f550948c4b9ccafe782175949ea5"
    ),
}


def build_candidate_manifest() -> Path:
    """Derive r53 without changing an immutable formal manifest."""
    manifest = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
    manifest.update(
        {
            "schema_version": "protocol_v2_2_r53_candidate_smoke.v1",
            "manifest_id": "protocol_v2_2_seed20260729_r53_candidate",
            "source_tag": SOURCE_TAG,
            "source_commit": SOURCE_COMMIT,
            "suite_id": "nonhard_capability_v2_2_seed20260729_r53_candidate",
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
