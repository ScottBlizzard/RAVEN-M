#!/usr/bin/env python3
"""Build a frozen A6-A11 runner command; execute only with --execute."""

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
    parser.add_argument(
        "--arm", required=True, choices=("a6", "a7", "a8", "a8v2", "a9", "a10", "a10v2", "a11")
    )
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--launch-receipt", type=Path, required=True)
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument("--resume-suite-dir", type=Path)
    parser.add_argument("--a7-continuation-plan", type=Path)
    parser.add_argument("--a7-parent-suite-dir", type=Path)
    parser.add_argument(
        "--four-task-diagnostic-replication",
        action="store_true",
        help="Fresh non-fail-fast A8-v2/A9 diagnostic over the four A0-success tasks.",
    )
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if bool(args.a7_continuation_plan) != bool(args.a7_parent_suite_dir):
        parser.error(
            "--a7-continuation-plan and --a7-parent-suite-dir must be supplied together"
        )
    if args.a7_continuation_plan is not None and args.arm != "a7":
        parser.error("A7 continuation arguments require --arm a7")
    if args.four_task_diagnostic_replication:
        if args.arm not in {"a8v2", "a9"}:
            parser.error("four-task diagnostic replication requires a8v2 or a9")
        if args.resume_suite_dir is not None or args.a7_continuation_plan is not None:
            parser.error("four-task diagnostic replication requires a fresh suite")
    if not ANDROIDWORLD_PYTHON.is_file():
        raise RuntimeError(
            f"frozen AndroidWorld runtime Python is missing: {ANDROIDWORLD_PYTHON}"
        )
    command = [
        str(ANDROIDWORLD_PYTHON),
        str(REPOSITORY_ROOT / "implementation/scripts/run_official_qwen_mobile.py"),
        "--adb-path", args.adb_path,
        "--manifest", str(REPOSITORY_ROOT / "implementation/configs/androidworld_hard_v2_instances.json"),
        "--url", args.url,
        "--console-port", str(args.console_port),
        "--grpc-port", str(args.grpc_port),
        "--output-root",
        str(
            REPOSITORY_ROOT
            / {
                "a10": "runs/a10_ecobf",
                "a10v2": "runs/a10_v2_emobf",
                "a11": "runs/a11_crc_ecobf",
            }.get(args.arm, "runs/a678_memory")
        ),
    ]
    if args.arm == "a10":
        command.extend(
            [
                "--a10-ecobf",
                "--a10-preflight-report",
                str(REPOSITORY_ROOT / "evidence/a10/A10_ZERO_GENERATION_PREFLIGHT.json"),
                "--a10-launch-receipt",
                str(args.launch_receipt.resolve()),
            ]
        )
    elif args.arm == "a10v2":
        command.extend(
            [
                "--a10-v2-emobf",
                "--a10-v2-preflight-report",
                str(REPOSITORY_ROOT / "evidence/a10_v2/A10_V2_ZERO_GENERATION_PREFLIGHT.json"),
                "--a10-v2-launch-receipt",
                str(args.launch_receipt.resolve()),
            ]
        )
    elif args.arm == "a11":
        command.extend(
            [
                "--a11-crc-ecobf",
                "--a11-preflight-report",
                str(REPOSITORY_ROOT / "evidence/a11/A11_ZERO_GENERATION_PREFLIGHT.json"),
                "--a11-launch-receipt",
                str(args.launch_receipt.resolve()),
            ]
        )
    else:
        command.extend(
            [
                "--a678-arm", args.arm,
                "--a678-preflight-report",
                str(REPOSITORY_ROOT / "evidence/a678/A678_ZERO_GENERATION_PREFLIGHT.json"),
                "--a678-launch-receipt",
                str(args.launch_receipt.resolve()),
            ]
        )
    if args.resume_suite_dir is not None:
        command.extend(["--resume-suite-dir", str(args.resume_suite_dir.resolve())])
    if args.a7_continuation_plan is not None:
        command.extend(
            [
                "--a7-continuation-plan",
                str(args.a7_continuation_plan.resolve()),
                "--a7-parent-suite-dir",
                str(args.a7_parent_suite_dir.resolve()),
            ]
        )
    if args.four_task_diagnostic_replication:
        command.extend(
            [
                "--diagnostic",
                "--a89-four-task-diagnostic-replication",
            ]
        )
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
