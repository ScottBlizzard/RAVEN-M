#!/usr/bin/env python3
"""Build the frozen A6/A7/A8 runner command; execute only with --execute."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ANDROIDWORLD_PYTHON = (
    REPOSITORY_ROOT / "06_local_runtime/envs/androidworld/Scripts/python.exe"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", required=True, choices=("a6", "a7", "a8"))
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--launch-receipt", type=Path, required=True)
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument("--resume-suite-dir", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not ANDROIDWORLD_PYTHON.is_file():
        raise RuntimeError(
            f"frozen AndroidWorld runtime Python is missing: {ANDROIDWORLD_PYTHON}"
        )
    command = [
        str(ANDROIDWORLD_PYTHON),
        str(REPOSITORY_ROOT / "implementation/scripts/run_official_qwen_mobile.py"),
        "--a678-arm", args.arm,
        "--adb-path", args.adb_path,
        "--manifest", str(REPOSITORY_ROOT / "implementation/configs/androidworld_hard_v2_instances.json"),
        "--a678-preflight-report", str(REPOSITORY_ROOT / "evidence/a678/A678_ZERO_GENERATION_PREFLIGHT.json"),
        "--a678-launch-receipt", str(args.launch_receipt.resolve()),
        "--url", args.url,
        "--console-port", str(args.console_port),
        "--grpc-port", str(args.grpc_port),
        "--output-root", str(REPOSITORY_ROOT / "runs/a678_memory"),
    ]
    if args.resume_suite_dir is not None:
        command.extend(["--resume-suite-dir", str(args.resume_suite_dir.resolve())])
    print(subprocess.list2cmdline(command))
    if not args.execute:
        print(
            "Dry run only. The displayed command is pinned to the frozen AndroidWorld "
            "runtime; reinvoke with --execute after final live-receipt qualification."
        )
        return 0
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
