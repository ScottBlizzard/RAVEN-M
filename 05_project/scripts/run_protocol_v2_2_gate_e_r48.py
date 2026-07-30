"""Launch or preflight the frozen protocol-v2.2 Gate E r48 suite."""

from __future__ import annotations

from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "90916a46f678af38f3632d3d229e04bb5f23200d"


if __name__ == "__main__":
    raise SystemExit(
        main(
            default_manifest=(
                PROJECT_ROOT
                / "configs/experiments/v2_2_capability_gate_r48.json"
            ),
            expected_source_commit=SOURCE_COMMIT,
        )
    )
