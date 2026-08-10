"""Bind the scored A2 receipt to the actually running vLLM process (zero generation)."""

from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path
import urllib.request


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--launch-intent", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    intent_path = args.launch_intent.resolve()
    intent = json.loads(intent_path.read_text(encoding="utf-8"))
    if intent.get("status") != "launch_pending_live_qualification":
        raise RuntimeError("unexpected A2 launch intent status")
    pid = int(intent["pid_before_exec"])
    cmdline_path = Path(f"/proc/{pid}/cmdline")
    if not cmdline_path.is_file():
        raise RuntimeError(f"qualified vLLM pid is not running: {pid}")
    cmdline = [item.decode("utf-8") for item in cmdline_path.read_bytes().split(b"\0") if item]
    if intent["model_realpath"] not in cmdline or "serve" not in cmdline:
        raise RuntimeError(f"live process command is not the frozen vLLM launch: {cmdline!r}")
    with urllib.request.urlopen(
        f"http://127.0.0.1:{int(intent['port'])}/v1/models", timeout=30
    ) as response:
        models = json.loads(response.read().decode("utf-8"))
    served_ids = [item.get("id") for item in models.get("data", []) if isinstance(item, dict)]
    if served_ids != [intent["served_model_id"]]:
        raise RuntimeError(f"served model identity drift: {served_ids!r}")
    packages = {name: importlib.metadata.version(name) for name in ("vllm", "torch", "transformers")}
    if packages != intent["packages"]:
        raise RuntimeError("live process package identity drift")
    result = {
        "schema": "a2_v1r1_live_server_receipt_v1",
        "status": "pass",
        "generation_calls": 0,
        "pid": pid,
        "process_cmdline": cmdline,
        "launch_intent_sha256": _hash(intent_path),
        "model_realpath": intent["model_realpath"],
        "model_manifest_sha256": intent["model_manifest_sha256"],
        "remote_qualification_sha256": intent["remote_qualification_sha256"],
        "served_model_id": intent["served_model_id"],
        "served_model_ids_observed": served_ids,
        "host": intent["host"],
        "port": int(intent["port"]),
        "packages": packages,
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "output": str(args.output.resolve()), "sha256": _hash(args.output)}, indent=2))


if __name__ == "__main__":
    main()
