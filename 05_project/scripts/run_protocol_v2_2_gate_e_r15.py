"""Launch, preflight, or development-smoke protocol-v2.2 Gate E r15."""

from __future__ import annotations

from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "c690fb9bb2be9b1e2d493cc3694bd0f2d4e6a365"


if __name__ == "__main__":
    raise SystemExit(
        main(
            default_manifest=(
                PROJECT_ROOT
                / "configs/experiments/v2_2_capability_gate_r15.json"
            ),
            expected_source_commit=SOURCE_COMMIT,
        )
    )
