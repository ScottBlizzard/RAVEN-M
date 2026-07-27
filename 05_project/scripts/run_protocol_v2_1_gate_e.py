"""Launch or preflight the frozen protocol-v2.1 Gate E."""

from __future__ import annotations

from pathlib import Path

from run_protocol_v2_gate_e import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = "9c39b75f7eea3952da738a092deb7eb02c506468"


if __name__ == "__main__":
    raise SystemExit(
        main(
            default_manifest=(
                PROJECT_ROOT
                / "configs/experiments/v2_1_capability_gate.json"
            ),
            expected_source_commit=SOURCE_COMMIT,
        )
    )
