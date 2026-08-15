#!/usr/bin/env python3
import argparse
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / "06_local_runtime/envs/androidworld/Scripts/python.exe"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--launch-receipt", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    command = [
        str(PYTHON), str(ROOT / "implementation/scripts/run_official_qwen_mobile.py"),
        "--adb-path", args.adb_path,
        "--manifest", str(ROOT / "implementation/configs/androidworld_hard_v2_instances.json"),
        "--url", "http://127.0.0.1:18000", "--console-port", "5554", "--grpc-port", "8554",
        "--sys-nag",
        "--sys-nag-preflight-report", str(ROOT / "evidence/sys_nag_v2/SYS_NAG_V2_ZERO_GENERATION_PREFLIGHT.json"),
        "--sys-nag-launch-receipt", str(args.launch_receipt.resolve()),
        "--output-root", str(ROOT / "runs/sys_nag_v2"),
    ]
    print(subprocess.list2cmdline(command))
    return subprocess.call(command) if args.execute else 0


if __name__ == "__main__":
    raise SystemExit(main())
