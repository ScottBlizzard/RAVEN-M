"""Launch, preflight, or development-smoke protocol-v2.2 Gate E r35."""

from __future__ import annotations

from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "a8a8230a599ee2db8c7126d16670f4c96605ae63"


if __name__ == "__main__":
    raise SystemExit(
        main(
            default_manifest=(
                PROJECT_ROOT
                / "configs/experiments/v2_2_capability_gate_r35.json"
            ),
            expected_source_commit=SOURCE_COMMIT,
        )
    )
