"""Preflight or run one explicitly authorized r56 Gate-F batch."""

from __future__ import annotations

from pathlib import Path

from run_protocol_v2_gate_f import main


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_TAG = "protocol-v2-2-gate-e-r56"
SOURCE_COMMIT = "24ddb7a34c0e873218cbac6b081d7d24ecd7d61e"


if __name__ == "__main__":
    raise SystemExit(
        main(
            default_manifest=(
                PROJECT_ROOT
                / "configs/experiments/v2_2_hard_micro_gate_r56.json"
            ),
            expected_source_tag=SOURCE_TAG,
            expected_source_commit=SOURCE_COMMIT,
            diagnostic_pause=None,
        )
    )
