#!/usr/bin/env python3
"""Build the frozen BPR-v2 live command; execute only after receipt qualification."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
ANDROIDWORLD_PYTHON = ROOT / "06_local_runtime/envs/androidworld/Scripts/python.exe"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("primary", "empty_read"))
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--launch-receipt", type=Path, required=True)
    parser.add_argument("--primary-result", type=Path)
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument("--resume-suite-dir", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.mode == "empty_read" and args.primary_result is None:
        parser.error("empty_read requires --primary-result")
    if args.mode == "primary" and args.primary_result is not None:
        parser.error("primary forbids --primary-result")
    command = [
        str(ANDROIDWORLD_PYTHON),
        str(ROOT / "implementation/scripts/run_official_qwen_mobile.py"),
        "--adb-path", args.adb_path,
        "--manifest", str(ROOT / "implementation/configs/androidworld_hard_v2_instances.json"),
        "--url", args.url,
        "--console-port", str(args.console_port),
        "--grpc-port", str(args.grpc_port),
        "--a1r1-bpr-v2-mode", args.mode,
        "--a1r1-bpr-v2-preflight-report", str(ROOT / "evidence/a1r1_v2/A1R1_BPR_V2_ZERO_GENERATION_PREFLIGHT.json"),
        "--a1r1-bpr-v2-launch-receipt", str(args.launch_receipt.resolve()),
        "--output-root", str(ROOT / f"runs/a1r1_bpr_v2_{args.mode}"),
    ]
    if args.primary_result is not None:
        command.extend(["--a1r1-bpr-v2-primary-result", str(args.primary_result.resolve())])
    if args.resume_suite_dir is not None:
        command.extend(["--resume-suite-dir", str(args.resume_suite_dir.resolve())])
    print(subprocess.list2cmdline(command))
    if not args.execute:
        print("Dry run only. Use --execute only after the arm-specific live receipt is qualified.")
        return 0
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
