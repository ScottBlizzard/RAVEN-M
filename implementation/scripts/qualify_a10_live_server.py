#!/usr/bin/env python3
"""Bind A10 to a live vLLM process and its frozen zero-generation preflight."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path
import urllib.request


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--launch-intent", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    intent = json.loads(args.launch_intent.read_text(encoding="utf-8"))
    preflight = json.loads(args.preflight.read_text(encoding="utf-8"))
    if (
        intent.get("schema") != "a10_server_launch_intent_v1"
        or intent.get("status") != "launch_pending_live_qualification"
    ):
        raise RuntimeError("unexpected launch intent status")
    if preflight.get("status") != "pass" or preflight.get("generation_calls") != 0:
        raise RuntimeError("A10 zero-generation preflight has not passed")
    if intent.get("a10_preflight_sha256") != digest(args.preflight):
        raise RuntimeError("launch intent is not bound to this A10 preflight")
    if intent.get("a10_source_freeze_sha256") != preflight.get("source_freeze_sha256"):
        raise RuntimeError("launch intent source freeze drift")

    pid = int(intent["pid_before_exec"])
    cmdline_path = Path(f"/proc/{pid}/cmdline")
    if not cmdline_path.is_file():
        raise RuntimeError(f"vLLM pid is not running: {pid}")
    cmdline = [part.decode() for part in cmdline_path.read_bytes().split(b"\0") if part]
    if cmdline != [str(item) for item in intent.get("command") or []]:
        raise RuntimeError("live process command differs from launch intent")
    with urllib.request.urlopen(f"http://127.0.0.1:{intent['port']}/v1/models", timeout=30) as response:
        served = json.loads(response.read().decode("utf-8"))
    ids = [item.get("id") for item in served.get("data", [])]
    if ids != [intent["served_model_id"]]:
        raise RuntimeError(f"served model drift: {ids}")
    packages = {name: importlib.metadata.version(name) for name in ("vllm", "torch", "transformers")}
    if packages != intent["packages"]:
        raise RuntimeError("runtime package drift")
    result = {
        "schema": "a10_live_server_receipt_v1",
        "status": "pass",
        "generation_calls": 0,
        "a10_preflight_sha256": digest(args.preflight),
        "a10_source_freeze_sha256": preflight["source_freeze_sha256"],
        "launch_intent_sha256": digest(args.launch_intent),
        "launch_intent_path": str(args.launch_intent.resolve()),
        "served_model_id": intent["served_model_id"],
        "model_realpath": intent["model_realpath"],
        "model_manifest_sha256": intent["model_manifest_sha256"],
        "remote_qualification_sha256": intent.get("remote_qualification_sha256"),
        "pid": pid,
        "process_pid": pid,
        "process_cmdline": cmdline,
        "host": intent["host"],
        "port": int(intent["port"]),
        "packages": packages,
        "vllm_version": packages["vllm"],
        "torch_version": packages["torch"],
        "transformers_version": packages["transformers"],
        "served_model_ids_observed": ids,
        "qualification_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "output": str(args.output), "sha256": digest(args.output)}, indent=2))


if __name__ == "__main__":
    main()
