#!/usr/bin/env python3
"""Build or validate A4's frozen workflow bank without model/GPU calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "implementation" / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from raven_m.official_qwen_mobile.a4_donor import (  # noqa: E402
    validate_frozen_bank,
    write_audit_and_bank,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=REPOSITORY_ROOT / "implementation" / "configs" / "a4_awm_donor_manifest_v1.json",
    )
    parser.add_argument(
        "--audit-output",
        type=Path,
        default=REPOSITORY_ROOT / "evidence" / "a345" / "A4_DONOR_SOURCE_AUDIT.json",
    )
    parser.add_argument(
        "--bank-output",
        type=Path,
        default=REPOSITORY_ROOT / "evidence" / "a345" / "A4_FROZEN_DONOR_WORKFLOW_BANK.json",
    )
    parser.add_argument("--validate", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.validate:
        report = validate_frozen_bank(
            args.manifest,
            repository_root=REPOSITORY_ROOT,
            audit_path=args.audit_output,
            bank_path=args.bank_output,
        )
    else:
        report = write_audit_and_bank(
            args.manifest,
            repository_root=REPOSITORY_ROOT,
            audit_path=args.audit_output,
            bank_path=args.bank_output,
        )
    print(
        json.dumps(
            {
                "status": report["status"],
                "generation_calls": report["generation_calls"],
                "eligible_donor_count": report["eligible_donor_count"],
                "eligible_donor_ids": report["eligible_donor_ids"],
                "missing_required_families": report["missing_required_families"],
                "errors": report["errors"],
                "audit_output": str(args.audit_output),
                "bank_output": str(args.bank_output) if report["status"] == "ready" else None,
            },
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if report["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
