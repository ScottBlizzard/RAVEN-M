"""Launch, preflight, or development-smoke protocol-v2.2 Gate E r4."""

from __future__ import annotations

from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "21d5da1d0404667a5b9404bf21e7d6fb220b5912"


if __name__ == "__main__":
    raise SystemExit(
        main(
            default_manifest=(
                PROJECT_ROOT
                / "configs/experiments/v2_2_capability_gate_r4.json"
            ),
            expected_source_commit=SOURCE_COMMIT,
        )
    )
