#!/usr/bin/env python3
"""Issue an A10-v2 receipt only for a matching live process and passed preflight."""

from __future__ import annotations
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))
from raven_m.official_qwen_mobile.a10_v2_contract import validate_preflight_report  # noqa: E402

def digest(path: Path) -> str: return sha256(path.read_bytes()).hexdigest()

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--launch-intent", type=Path, required=True); parser.add_argument("--preflight", type=Path, required=True); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    intent = json.loads(args.launch_intent.read_text(encoding="utf-8")); preflight = validate_preflight_report(args.preflight)
    if intent.get("schema") != "a10_v2_server_launch_intent_v1" or intent.get("arm") != "a10v2": raise RuntimeError("A10-v2 intent identity mismatch")
    if intent.get("preflight_sha256") != digest(args.preflight) or intent.get("source_freeze_sha256") != preflight["source_freeze_sha256"]: raise RuntimeError("A10-v2 intent provenance mismatch")
    pid = int(intent["pid_before_exec"]); cmdline = [part.decode() for part in Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0") if part]
    if cmdline != [str(item) for item in intent["command"]]: raise RuntimeError("process command drift")
    with urllib.request.urlopen(f"http://127.0.0.1:{intent['port']}/v1/models", timeout=30) as response: served = json.loads(response.read())
    ids = [item.get("id") for item in served.get("data", [])]
    if ids != [intent["served_model_id"]]: raise RuntimeError("served model drift")
    packages = {name: importlib.metadata.version(name) for name in ("vllm", "torch", "transformers")}
    if packages != intent["packages"]: raise RuntimeError("package drift")
    result = {"schema": "a10_v2_live_server_receipt_v1", "status": "pass", "generation_calls": 0, "a10_v2_preflight_sha256": digest(args.preflight), "a10_v2_source_freeze_sha256": preflight["source_freeze_sha256"], "launch_intent_sha256": digest(args.launch_intent), "launch_intent_path": str(args.launch_intent.resolve()), "served_model_id": intent["served_model_id"], "model_realpath": intent["model_realpath"], "model_manifest_sha256": intent["model_manifest_sha256"], "pid": pid, "process_pid": pid, "process_cmdline": cmdline, "port": int(intent["port"]), "packages": packages, "served_model_ids_observed": ids, "qualification_timestamp": datetime.now(timezone.utc).isoformat()}
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "output": str(args.output), "sha256": digest(args.output)}, indent=2))

if __name__ == "__main__": main()
