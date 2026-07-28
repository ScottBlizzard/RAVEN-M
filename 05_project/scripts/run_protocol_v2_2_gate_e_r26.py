"""Launch, preflight, or development-smoke protocol-v2.2 Gate E r26."""

from __future__ import annotations

from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "56270abc21a06a4eaf59102cd6b945af2fdc71fe"


if __name__ == "__main__":
    raise SystemExit(
        main(
            default_manifest=(
                PROJECT_ROOT
                / "configs/experiments/v2_2_capability_gate_r26.json"
            ),
            expected_source_commit=SOURCE_COMMIT,
        )
    )
