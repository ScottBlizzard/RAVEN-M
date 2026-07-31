"""Launch or preflight the frozen protocol-v2.2 Gate E r54 suite."""

from __future__ import annotations

from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "54adaf031abd87dc5c420bd1d8d07acc8c0a4b94"


if __name__ == "__main__":
    raise SystemExit(
        main(
            default_manifest=(
                PROJECT_ROOT
                / "configs/experiments/v2_2_capability_gate_r54.json"
            ),
            expected_source_commit=SOURCE_COMMIT,
        )
    )
