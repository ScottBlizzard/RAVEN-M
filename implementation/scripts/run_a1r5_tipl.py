#!/usr/bin/env python3
"""Build or execute the frozen A1-R5 command."""

from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / "06_local_runtime/envs/androidworld/Scripts/python.exe"


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--adb-path", required=True); parser.add_argument("--launch-receipt", type=Path, required=True); parser.add_argument("--url", default="http://127.0.0.1:18000"); parser.add_argument("--console-port", type=int, default=5554); parser.add_argument("--grpc-port", type=int, default=8554); parser.add_argument("--resume-suite-dir", type=Path); parser.add_argument("--execute", action="store_true"); args = parser.parse_args()
    command = [str(PYTHON), str(ROOT / "implementation/scripts/run_official_qwen_mobile.py"), "--adb-path", args.adb_path, "--manifest", str(ROOT / "implementation/configs/androidworld_hard_v2_instances.json"), "--url", args.url, "--console-port", str(args.console_port), "--grpc-port", str(args.grpc_port), "--a1r5-tipl", "--a1r5-preflight-report", str(ROOT / "evidence/a1r5/A1R5_TIPL_ZERO_GENERATION_PREFLIGHT.json"), "--a1r5-launch-receipt", str(args.launch_receipt.resolve()), "--output-root", str(ROOT / "runs/a1r5_tipl")]
    if args.resume_suite_dir is not None: command.extend(["--resume-suite-dir", str(args.resume_suite_dir.resolve())])
    print(subprocess.list2cmdline(command))
    if not args.execute: print("Dry run only. Use --execute only after the A1-R5 receipt passes."); return 0
    return subprocess.call(command)


if __name__ == "__main__": raise SystemExit(main())
