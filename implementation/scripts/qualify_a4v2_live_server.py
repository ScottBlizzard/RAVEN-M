"""Bind A4-v2 scored execution to its frozen bank, preflight and live vLLM."""

from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path
import urllib.request


EXPERIMENT_ID = "A4V2_FAITHFUL_OFFLINE_AWM_QWEN3VL32B_AW_HARD_S20260806_V1"


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--launch-intent", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--bank", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    intent = json.loads(args.launch_intent.read_text(encoding="utf-8"))
    preflight = json.loads(args.preflight.read_text(encoding="utf-8"))
    if intent.get("status") != "launch_pending_live_qualification":
        raise RuntimeError("unexpected launch intent status")
    if (
        preflight.get("status") != "pass"
        or preflight.get("generation_calls") != 0
        or preflight.get("experiment_id") != EXPERIMENT_ID
        or preflight.get("workflow_bank_sha256") != _sha(args.bank)
    ):
        raise RuntimeError("A4-v2 preflight/bank has not qualified")
    pid = int(intent["pid_before_exec"])
    cmdline_path = Path(f"/proc/{pid}/cmdline")
    if not cmdline_path.is_file():
        raise RuntimeError(f"vLLM pid is not running: {pid}")
    cmdline = [part.decode() for part in cmdline_path.read_bytes().split(b"\0") if part]
    if intent["model_realpath"] not in cmdline or "serve" not in cmdline:
        raise RuntimeError("live process differs from launch intent")
    with urllib.request.urlopen(f"http://127.0.0.1:{intent['port']}/v1/models", timeout=30) as response:
        served = json.loads(response.read().decode("utf-8"))
    ids = [item.get("id") for item in served.get("data", [])]
    if ids != [intent["served_model_id"]]:
        raise RuntimeError(f"served model drift: {ids}")
    packages = {name: importlib.metadata.version(name) for name in ("vllm", "torch", "transformers")}
    if packages != intent["packages"]:
        raise RuntimeError("runtime package drift")
    result = {
        "schema": "a4v2.live_server_receipt.v1",
        "experiment_id": EXPERIMENT_ID,
        "status": "pass",
        "generation_calls": 0,
        "pid": pid,
        "process_cmdline": cmdline,
        "launch_intent_sha256": _sha(args.launch_intent),
        "preflight_sha256": _sha(args.preflight),
        "workflow_bank_sha256": _sha(args.bank),
        "model_realpath": intent["model_realpath"],
        "model_manifest_sha256": intent["model_manifest_sha256"],
        "remote_qualification_sha256": intent["remote_qualification_sha256"],
        "served_model_id": intent["served_model_id"],
        "served_model_ids_observed": ids,
        "host": intent["host"],
        "port": int(intent["port"]),
        "packages": packages,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "output": str(args.output), "sha256": _sha(args.output)}, indent=2))


if __name__ == "__main__":
    main()

