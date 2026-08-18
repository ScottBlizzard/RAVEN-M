#!/usr/bin/env python3
"""Qualify the exact Qwen service used for donor acquisition and induction."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path
import urllib.request


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _digest(value: dict) -> str:
    return sha256(
        json.dumps(
            {key: item for key, item in value.items() if key != "content_sha256"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--launch-intent", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    intent = json.loads(args.launch_intent.read_text(encoding="utf-8"))
    if (
        intent.get("schema") != "a4v2.acquisition_server_launch_intent.v1"
        or intent.get("status") != "launch_pending_live_qualification"
        or intent.get("served_model_id") != MODEL_ID
        or int(intent.get("port", -1)) != 18000
    ):
        raise RuntimeError("A4-v2 acquisition launch intent drift")
    pid = int(intent["pid_before_exec"])
    cmdline_path = Path(f"/proc/{pid}/cmdline")
    if not cmdline_path.is_file():
        raise RuntimeError(f"vLLM pid is not running: {pid}")
    cmdline = [part.decode() for part in cmdline_path.read_bytes().split(b"\0") if part]
    if intent["model_realpath"] not in cmdline or "serve" not in cmdline:
        raise RuntimeError("live process differs from launch intent")
    with urllib.request.urlopen("http://127.0.0.1:18000/v1/models", timeout=30) as response:
        served = json.loads(response.read().decode("utf-8"))
    ids = [item.get("id") for item in served.get("data", [])]
    if ids != [MODEL_ID]:
        raise RuntimeError(f"served model drift: {ids}")
    packages = {name: importlib.metadata.version(name) for name in ("vllm", "torch", "transformers")}
    if packages != intent.get("packages"):
        raise RuntimeError("runtime package drift")
    result = {
        "schema": "a4v2.acquisition_server_receipt.v1",
        "experiment_id": "A4V2_FAITHFUL_OFFLINE_AWM_QWEN3VL32B_AW_HARD_S20260806_V1",
        "status": "pass",
        "qualified_at": datetime.now(timezone.utc).isoformat(),
        "generation_calls": 0,
        "launch_intent_sha256": _sha(args.launch_intent),
        "repository_commit": intent["repository_commit"],
        "pid": pid,
        "process_cmdline": cmdline,
        "model_realpath": intent["model_realpath"],
        "model_manifest_sha256": intent["model_manifest_sha256"],
        "remote_qualification_sha256": intent["remote_qualification_sha256"],
        "served_model_id": MODEL_ID,
        "served_model_ids_observed": ids,
        "host": "127.0.0.1",
        "port": 18000,
        "packages": packages,
    }
    result["content_sha256"] = _digest(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "output": str(args.output), "sha256": _sha(args.output)}, indent=2))


if __name__ == "__main__":
    main()
