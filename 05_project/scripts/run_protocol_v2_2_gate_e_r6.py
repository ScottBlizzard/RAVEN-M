"""Launch, preflight, or development-smoke protocol-v2.2 Gate E r6."""

from __future__ import annotations

from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "d7d9ba87416090e8bdb2d99f9ba4ae772687cd7a"


if __name__ == "__main__":
    raise SystemExit(
        main(
            default_manifest=(
                PROJECT_ROOT
                / "configs/experiments/v2_2_capability_gate_r6.json"
            ),
            expected_source_commit=SOURCE_COMMIT,
        )
    )
