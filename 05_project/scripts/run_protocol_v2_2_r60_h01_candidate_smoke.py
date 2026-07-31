"""Preflight or run the isolated non-scored r60 H01 B3 smoke."""

from __future__ import annotations

import json
from pathlib import Path

from run_protocol_v2_gate_f import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
SOURCE_COMMIT = "5ef66de358423f9940191d8dfde0e74002ccdcec"
SOURCE_TAG = "protocol-v2-2-r60-local-candidate"
PARENT_GATE_E_COMMIT = "24ddb7a34c0e873218cbac6b081d7d24ecd7d61e"
BASE_MANIFEST = (
    PROJECT_ROOT / "configs/experiments/v2_2_hard_micro_gate_r56.json"
)
GENERATED_MANIFEST = (
    REPOSITORY_ROOT
    / "runs/protocol_v2_2_development/manifests/"
    "v2_2_r60_h01_candidate.generated.json"
)
UPDATED_FREEZE_HASHES = {
    "05_project/scripts/run_protocol_v2_gate_f.py": (
        "c48d04d8892820771e81c0c65b451e7f09a5b074ec40c833f8ac74e99857ee7e"
    ),
    "05_project/src/raven_m/controller/episode_controller.py": (
        "cb5e0fb0323665e7887522d95de469cba60b2c1b942017c14096a6f0042ef18c"
    ),
    "05_project/src/raven_m/controller/protocol_v2_guard.py": (
        "e156470e6ce9c6fcdf1b5a2f13f5f0191f00b73cd2913abe042cd3cb1b87abf2"
    ),
}


def build_candidate_manifest() -> Path:
    """Derive r60 without changing an earlier formal or development result."""
    manifest = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
    manifest.update(
        {
            "schema_version": "protocol_v2_2_gate_f_r60_candidate.v1",
            "manifest_id": "protocol_v2_2_gate_f_r60_candidate",
            "source_tag": SOURCE_TAG,
            "source_commit": SOURCE_COMMIT,
            "suite_id": "hard_micro_v2_2_seed20260730_r60_candidate",
        }
    )
    records_by_path = {
        record["path"]: record for record in manifest["freeze_files"]
    }
    if not UPDATED_FREEZE_HASHES.keys() <= records_by_path.keys():
        raise RuntimeError("Candidate freeze override is absent from r56.")
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
            expected_source_tag=SOURCE_TAG,
            expected_source_commit=SOURCE_COMMIT,
            expected_prerequisite_commit=PARENT_GATE_E_COMMIT,
            diagnostic_pause=None,
        )
    )

