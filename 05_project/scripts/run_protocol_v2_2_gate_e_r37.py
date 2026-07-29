"""Launch, preflight, or development-smoke protocol-v2.2 Gate E r37."""

from __future__ import annotations

from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "dc99511d71168c3b6900ac42c92b10052730ecd4"


if __name__ == "__main__":
    raise SystemExit(
        main(
            default_manifest=(
                PROJECT_ROOT
                / "configs/experiments/v2_2_capability_gate_r37.json"
            ),
            expected_source_commit=SOURCE_COMMIT,
        )
    )
