"""Preflight or run one explicitly authorized formal r60 Gate-F batch."""

from __future__ import annotations

import json
from pathlib import Path

from run_protocol_v2_gate_f import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
OVERLAY = (
    PROJECT_ROOT / "configs/experiments/v2_2_hard_micro_gate_r60.json"
)
GENERATED_MANIFEST = (
    REPOSITORY_ROOT
    / "runs/protocol_v2_2_manifests/"
    "v2_2_hard_micro_gate_r60.generated.json"
)
SOURCE_COMMIT = "5ef66de358423f9940191d8dfde0e74002ccdcec"
SOURCE_TAG = "protocol-v2-2-r60-local-candidate"
PARENT_GATE_E_COMMIT = "24ddb7a34c0e873218cbac6b081d7d24ecd7d61e"


def build_formal_manifest() -> Path:
    """Build r60 from the immutable r56 controls plus audited overrides."""
    overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
    base_path = REPOSITORY_ROOT / overlay["base_manifest"]
    manifest = json.loads(base_path.read_text(encoding="utf-8"))
    manifest.update(
        {
            "schema_version": "protocol_v2_2_gate_f_r60.v1",
            "manifest_id": overlay["manifest_id"],
            "source_tag": overlay["source_tag"],
            "source_commit": overlay["source_commit"],
            "suite_id": overlay["suite_id"],
            "output_root": overlay["output_root"],
            "prerequisite_candidate_report": overlay[
                "prerequisite_candidate_report"
            ],
        }
    )
    if manifest["source_tag"] != SOURCE_TAG:
        raise RuntimeError("r60 formal source tag drifted.")
    if manifest["source_commit"] != SOURCE_COMMIT:
        raise RuntimeError("r60 formal source commit drifted.")
    records_by_path = {
        record["path"]: record for record in manifest["freeze_files"]
    }
    overrides = overlay["updated_freeze_hashes"]
    if not overrides.keys() <= records_by_path.keys():
        raise RuntimeError("r60 formal freeze override is absent from r56.")
    for path, digest in overrides.items():
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
            default_manifest=build_formal_manifest(),
            expected_source_tag=SOURCE_TAG,
            expected_source_commit=SOURCE_COMMIT,
            expected_prerequisite_commit=PARENT_GATE_E_COMMIT,
            diagnostic_pause=None,
            allow_development_smoke=False,
        )
    )
