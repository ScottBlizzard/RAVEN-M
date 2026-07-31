"""Preflight or run the isolated non-scored r57 H01 B3 smoke."""

from __future__ import annotations

import json
from pathlib import Path

from run_protocol_v2_gate_f import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
SOURCE_COMMIT = "4667166b60710f32348ace47243e41bcc041cd13"
SOURCE_TAG = "protocol-v2-2-r57-local-candidate"
PARENT_GATE_E_COMMIT = "24ddb7a34c0e873218cbac6b081d7d24ecd7d61e"
BASE_MANIFEST = (
    PROJECT_ROOT / "configs/experiments/v2_2_hard_micro_gate_r56.json"
)
GENERATED_MANIFEST = (
    REPOSITORY_ROOT
    / "runs/protocol_v2_2_development/manifests/"
    "v2_2_r57_h01_candidate.generated.json"
)
UPDATED_FREEZE_HASHES = {
    "05_project/scripts/run_protocol_v2_gate_f.py": (
        "c48d04d8892820771e81c0c65b451e7f09a5b074ec40c833f8ac74e99857ee7e"
    ),
    "05_project/src/raven_m/controller/episode_controller.py": (
        "d252243f5e9a2f697ce2edb99896728ba1ff308075146570c04be3f92bb7b67c"
    ),
    "05_project/src/raven_m/controller/protocol_v2_guard.py": (
        "b1edd9dc7762d92ff14c4d6074f686aa8fc58871e3c345effbb9e73a2d399dfc"
    ),
}


def build_candidate_manifest() -> Path:
    """Derive r57 without changing the immutable r56 formal manifest."""
    manifest = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
    manifest.update(
        {
            "schema_version": "protocol_v2_2_gate_f_r57_candidate.v1",
            "manifest_id": "protocol_v2_2_gate_f_r57_candidate",
            "source_tag": SOURCE_TAG,
            "source_commit": SOURCE_COMMIT,
            "suite_id": "hard_micro_v2_2_seed20260730_r57_candidate",
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
