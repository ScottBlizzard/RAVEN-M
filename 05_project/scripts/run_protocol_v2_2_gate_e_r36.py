"""Launch, preflight, or development-smoke protocol-v2.2 Gate E r36."""

from __future__ import annotations

from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "330cff00254a401a2c2f3ee8ed0a75cfad10e747"


if __name__ == "__main__":
    raise SystemExit(
        main(
            default_manifest=(
                PROJECT_ROOT
                / "configs/experiments/v2_2_capability_gate_r36.json"
            ),
            expected_source_commit=SOURCE_COMMIT,
        )
    )
