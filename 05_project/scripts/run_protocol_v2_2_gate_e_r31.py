"""Launch, preflight, or development-smoke protocol-v2.2 Gate E r31."""

from __future__ import annotations

from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "4e695b5115ad1d17c3e9d333ff55f44533855f46"


if __name__ == "__main__":
    raise SystemExit(
        main(
            default_manifest=(
                PROJECT_ROOT
                / "configs/experiments/v2_2_capability_gate_r31.json"
            ),
            expected_source_commit=SOURCE_COMMIT,
        )
    )
