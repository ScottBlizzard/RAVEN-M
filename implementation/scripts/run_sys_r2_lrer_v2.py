#!/usr/bin/env python3
"""Print or execute the exact stabilized SYS-R2-LRER V2 invocation."""

import argparse
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--runtime-python", type=Path, required=True)
    parser.add_argument("--launch-receipt", type=Path, required=True)
    parser.add_argument("--processor-path", type=Path, required=True)
    parser.add_argument("--processor-python", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--resume-suite-dir", type=Path)
    args = parser.parse_args()
    command = [
        str(args.runtime_python.resolve()),
        str(ROOT / "implementation/scripts/run_official_qwen_mobile.py"),
        "--adb-path",
        args.adb_path,
        "--manifest",
        str(ROOT / "implementation/configs/androidworld_hard_v2_instances.json"),
        "--url",
        "http://127.0.0.1:18000",
        "--console-port",
        "5554",
        "--grpc-port",
        "8554",
        "--sys-r2-lrer-v2",
        "--sys-r2-lrer-preflight-report",
        str(ROOT / "evidence/sys_r2_lrer_v2/SYS_R2_LRER_V2_ZERO_GENERATION_PREFLIGHT.json"),
        "--sys-r2-lrer-launch-receipt",
        str(args.launch_receipt.resolve()),
        "--sys-r2-lrer-processor-path",
        str(args.processor_path.resolve()),
        "--sys-r2-lrer-processor-python",
        str(args.processor_python.resolve()),
        "--output-root",
        str(ROOT / "runs/sys_r2_lrer_v2"),
    ]
    if args.resume_suite_dir is not None:
        command.extend(["--resume-suite-dir", str(args.resume_suite_dir.resolve())])
    print(subprocess.list2cmdline(command))
    if not args.execute:
        return 0
    runtime_root = args.runtime_python.resolve().parents[3]
    environment = dict(os.environ, RAVEN_LOCAL_RUNTIME_ROOT=str(runtime_root))
    return subprocess.call(command, env=environment)


if __name__ == "__main__":
    raise SystemExit(main())
