"""Launch or preflight the frozen protocol-v2.2 Gate E r45 suite."""

from __future__ import annotations

from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "3d0d719bfccac5934c62d3ab8be902a0ef66d7e9"


if __name__ == "__main__":
    raise SystemExit(
        main(
            default_manifest=(
                PROJECT_ROOT
                / "configs/experiments/v2_2_capability_gate_r45.json"
            ),
            expected_source_commit=SOURCE_COMMIT,
        )
    )

