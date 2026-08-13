#!/usr/bin/env python3
"""Qualify a live BPR-v2 vLLM process without making a generation call."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))
from raven_m.official_qwen_mobile import a1r1_bpr_v2_contract as contract  # noqa: E402


def package_version(name: str) -> str:
    from importlib.metadata import version
    return version(name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("primary", "empty_read"))
    parser.add_argument("--pid", required=True, type=int)
    parser.add_argument("--port", type=int, default=18000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    preflight = contract.validate_preflight_report()
    read_enabled = args.mode == "primary"
    experiment = contract.PRIMARY_EXPERIMENT_ID if read_enabled else contract.EMPTY_EXPERIMENT_ID
    config = contract.PRIMARY_CONFIG_PATH if read_enabled else contract.EMPTY_CONFIG_PATH
    cmdline = Path(f"/proc/{args.pid}/cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8")
    if "vllm" not in cmdline or contract.MODEL_REALPATH not in cmdline or str(args.port) not in cmdline:
        raise RuntimeError("live process cmdline does not match frozen BPR-v2 server")
    with urlopen(f"http://127.0.0.1:{args.port}/v1/models", timeout=10) as response:
        models = json.load(response)
    observed = [str(item.get("id")) for item in models.get("data") or []]
    if observed != [contract.MODEL_ID]:
        raise RuntimeError(f"served model identity mismatch: {observed}")
    payload = {
        "schema": contract.LIVE_RECEIPT_SCHEMA,
        "status": "PASS",
        "errors": [],
        "generation_calls": 0,
        "mechanism_id": contract.MECHANISM_ID,
        "experiment_id": experiment,
        "read_enabled": read_enabled,
        "implementation_commit": preflight["implementation_commit"],
        "preflight_file_sha256": contract.file_sha256(contract.PREFLIGHT_PATH),
        "config_file_sha256": contract.file_sha256(config),
        "served_model_id": contract.MODEL_ID,
        "served_model_ids_observed": observed,
        "model_realpath": contract.MODEL_REALPATH,
        "model_manifest_sha256": contract.MODEL_MANIFEST_SHA256,
        "process_pid": args.pid,
        "process_cmdline": cmdline,
        "port": args.port,
        "packages": {
            "vllm": package_version("vllm"),
            "torch": package_version("torch"),
            "transformers": package_version("transformers"),
        },
        "qualified_at": datetime.now(timezone.utc).isoformat(),
    }
    receipt = {**payload, "content_sha256": contract.content_sha256(payload)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    contract.validate_launch_receipt(
        args.output, expected_read_enabled=read_enabled, expected_experiment_id=experiment
    )
    print(json.dumps({"status": "PASS", "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
