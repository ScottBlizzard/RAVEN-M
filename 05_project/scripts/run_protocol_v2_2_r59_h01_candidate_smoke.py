"""Preflight or run the isolated non-scored r59 H01 B3 smoke."""

from __future__ import annotations

import json
from pathlib import Path

from run_protocol_v2_gate_f import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
SOURCE_COMMIT = "868c1ffa39c6d1415f3b3831ed295e61672c87af"
SOURCE_TAG = "protocol-v2-2-r59-local-candidate"
PARENT_GATE_E_COMMIT = "24ddb7a34c0e873218cbac6b081d7d24ecd7d61e"
BASE_MANIFEST = (
    PROJECT_ROOT / "configs/experiments/v2_2_hard_micro_gate_r56.json"
)
GENERATED_MANIFEST = (
    REPOSITORY_ROOT
    / "runs/protocol_v2_2_development/manifests/"
    "v2_2_r59_h01_candidate.generated.json"
)
UPDATED_FREEZE_HASHES = {
    "05_project/scripts/run_protocol_v2_gate_f.py": (
        "c48d04d8892820771e81c0c65b451e7f09a5b074ec40c833f8ac74e99857ee7e"
    ),
    "05_project/src/raven_m/controller/episode_controller.py": (
        "9c5932603c7344e1e7b0ad8aed785bdaf015acf50b847293c97ab18ae4523099"
    ),
    "05_project/src/raven_m/controller/protocol_v2_guard.py": (
        "337e165e94172d093266cec981378879cad81ab3d58d7381037f0d78ac18319a"
    ),
}


def build_candidate_manifest() -> Path:
    """Derive r59 without changing an earlier formal or development result."""
    manifest = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
    manifest.update(
        {
            "schema_version": "protocol_v2_2_gate_f_r59_candidate.v1",
            "manifest_id": "protocol_v2_2_gate_f_r59_candidate",
            "source_tag": SOURCE_TAG,
            "source_commit": SOURCE_COMMIT,
            "suite_id": "hard_micro_v2_2_seed20260730_r59_candidate",
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

