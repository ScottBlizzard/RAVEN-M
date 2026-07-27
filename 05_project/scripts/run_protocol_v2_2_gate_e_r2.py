"""Launch, preflight, or development-smoke protocol-v2.2 Gate E r2."""

from __future__ import annotations

from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "ae7575597cc3f548d960cf29045577a6ddda714e"


if __name__ == "__main__":
    raise SystemExit(
        main(
            default_manifest=(
                PROJECT_ROOT
                / "configs/experiments/v2_2_capability_gate_r2.json"
            ),
            expected_source_commit=SOURCE_COMMIT,
        )
    )
