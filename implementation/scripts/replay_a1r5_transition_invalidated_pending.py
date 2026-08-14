#!/usr/bin/env python3
"""Zero-generation replay of frozen A1-R2 traces through A1-R5."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "implementation/src"))

from implementation.scripts import replay_a1r4_writer_resilient_pending as base  # noqa: E402
from raven_m.official_qwen_mobile.a1r5_transition_invalidated_pending import (  # noqa: E402
    MECHANISM_ID,
    TransitionInvalidatedPendingMemory,
)


def replay(suite_dir: Path) -> dict:
    original = base.WriterResilientPendingMemory
    try:
        base.WriterResilientPendingMemory = TransitionInvalidatedPendingMemory
        report = base.replay(suite_dir)
    finally:
        base.WriterResilientPendingMemory = original
    report["schema"] = "a1r5_transition_invalidated_pending_offline_replay_v1"
    report["mechanism_id"] = MECHANISM_ID
    report["content_sha256"] = base._content_sha(report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-dir", type=Path, default=base.DEFAULT_SUITE)
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/a1r5/A1R5_TIPL_OFFLINE_REPLAY_REPORT.json")
    args = parser.parse_args()
    report = replay(args.suite_dir.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "errors": report["errors"], "totals": report["totals"]}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
