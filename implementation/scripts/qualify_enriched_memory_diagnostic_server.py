#!/usr/bin/env python3
"""Issue one live receipt for the shared diagnostic-only model server."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))
from raven_m.official_qwen_mobile import enriched_diagnostic_contract as contract  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--launch-intent", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, default=contract.PREFLIGHT_PATH)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    preflight = contract.validate_preflight_report(args.preflight.resolve())
    intent = json.loads(args.launch_intent.read_text(encoding="utf-8"))
    expected_intent = {
        "schema": contract.INTENT_SCHEMA,
        "status": "launch_pending_live_qualification",
        "protocol_id": contract.PROTOCOL_ID,
        "preflight_sha256": contract.file_sha256(args.preflight),
        "implementation_commit": preflight["implementation_commit"],
        "served_model_id": contract.MODEL_ID,
        "model_realpath": contract.MODEL_REALPATH,
        "model_manifest_sha256": contract.MODEL_MANIFEST_SHA256,
        "port": contract.PORT,
    }
    drift = [key for key, value in expected_intent.items() if intent.get(key) != value]
    if drift:
        raise RuntimeError(f"diagnostic launch intent drift: {drift}")
    model_manifest = Path(contract.MODEL_REALPATH + ".sha256")
    if not model_manifest.is_file() or contract.file_sha256(model_manifest) != contract.MODEL_MANIFEST_SHA256:
        raise RuntimeError("diagnostic model manifest drift")
    pid = int(intent["process_pid"])
    command = [part.decode() for part in Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0") if part]
    if command != intent.get("process_cmdline"):
        raise RuntimeError("diagnostic live process command drift")
    with urllib.request.urlopen(f"http://127.0.0.1:{contract.PORT}/v1/models", timeout=30) as response:
        served = json.loads(response.read())
    ids = [item.get("id") for item in served.get("data") or []]
    if ids != [contract.MODEL_ID]:
        raise RuntimeError(f"diagnostic served model drift: {ids}")
    packages = {name: importlib.metadata.version(name) for name in ("vllm", "torch", "transformers")}
    if packages != intent.get("packages"):
        raise RuntimeError("diagnostic package versions drifted after launch")
    receipt = {
        "schema": contract.RECEIPT_SCHEMA,
        "status": "pass",
        "protocol_id": contract.PROTOCOL_ID,
        "generation_calls": 0,
        "preflight_sha256": contract.file_sha256(args.preflight),
        "implementation_commit": preflight["implementation_commit"],
        "launch_intent_sha256": contract.file_sha256(args.launch_intent),
        "served_model_id": contract.MODEL_ID,
        "model_realpath": contract.MODEL_REALPATH,
        "model_manifest_sha256": contract.MODEL_MANIFEST_SHA256,
        "process_pid": pid,
        "process_cmdline": command,
        "port": contract.PORT,
        "packages": packages,
        "observed_served_model_ids": ids,
        "qualification_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    contract.validate_launch_receipt(args.output, preflight_path=args.preflight)
    print(json.dumps({"status": "pass", "output": str(args.output), "sha256": contract.file_sha256(args.output)}, indent=2))


if __name__ == "__main__":
    main()
