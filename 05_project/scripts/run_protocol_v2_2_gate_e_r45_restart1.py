"""Launch or preflight the clean restart of frozen Gate E r45.

The initial r45 launch produced zero formal results before a six-hour VPN
session expiry. This wrapper changes only the evidence namespace so the
preserved infrastructure attempt cannot be mixed with the clean restart.
"""

from __future__ import annotations

import json
from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
SOURCE_COMMIT = "3d0d719bfccac5934c62d3ab8be902a0ef66d7e9"
BASE_MANIFEST = (
    PROJECT_ROOT / "configs/experiments/v2_2_capability_gate_r45.json"
)
GENERATED_MANIFEST = (
    REPOSITORY_ROOT
    / "runs/protocol_v2_2/manifests/"
    "v2_2_capability_gate_r45_restart1.generated.json"
)


def build_restart_manifest() -> Path:
    """Change only the run identity after the zero-result VPN interruption."""
    manifest = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
    manifest.update(
        {
            "schema_version": "protocol_v2_2_gate_e_r45_restart1.v1",
            "manifest_id": "protocol_v2_2_gate_e_seed20260729_r45_restart1",
            "suite_id": "nonhard_capability_v2_2_seed20260729_r45_restart1",
        }
    )
    GENERATED_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    GENERATED_MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return GENERATED_MANIFEST


if __name__ == "__main__":
    raise SystemExit(
        main(
            default_manifest=build_restart_manifest(),
            expected_source_commit=SOURCE_COMMIT,
        )
    )

