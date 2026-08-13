#!/usr/bin/env python3
"""Build or execute one frozen six-task enriched diagnostic arm."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))
from raven_m.official_qwen_mobile import enriched_diagnostic_contract as contract  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", required=True, choices=contract.ARM_ORDER)
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--launch-receipt", type=Path, required=True)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument("--resume-suite-dir", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    preflight = contract.validate_preflight_report()
    if args.execute:
        if not args.launch_receipt.is_file():
            raise RuntimeError("live diagnostic execution requires a qualified receipt")
        contract.validate_launch_receipt(args.launch_receipt.resolve())
    command = [
        str(Path(args.python)),
        str(ROOT / "implementation/scripts/run_official_qwen_mobile.py"),
        "--adb-path", args.adb_path,
        "--manifest", str(contract.MANIFEST_PATH),
        "--url", args.url,
        "--console-port", str(args.console_port),
        "--grpc-port", str(args.grpc_port),
        "--generation-seed", str(contract.GENERATION_SEED),
        "--max-tokens", "32768",
        "--observation-backend", "uiautomator",
        "--run-stage", "post_hoc_enriched_memory_diagnostic6",
        "--diagnostic",
        "--enriched-memory-diagnostic", args.arm,
        "--enriched-diagnostic-preflight-report", str(contract.PREFLIGHT_PATH),
        "--enriched-diagnostic-launch-receipt", str(args.launch_receipt.resolve()),
        "--output-root", str(ROOT / f"runs/enriched_diag6/{args.arm}"),
    ]
    if args.resume_suite_dir is not None:
        command.extend(["--resume-suite-dir", str(args.resume_suite_dir.resolve())])
    payload = {
        "protocol_id": contract.PROTOCOL_ID,
        "arm": args.arm,
        "experiment_id": contract.ARM_BINDINGS[args.arm]["experiment_id"],
        "preflight_implementation_commit": preflight["implementation_commit"],
        "execute": args.execute,
        "command": command,
    }
    print(json.dumps(payload, indent=2))
    if not args.execute:
        return 0
    return subprocess.run(command, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
