#!/usr/bin/env python3
"""Qualify an A1-R2 vLLM process without a generation request."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))
from raven_m.official_qwen_mobile import a1r2_contract as contract  # noqa: E402


def _version(name: str) -> str:
    from importlib.metadata import version
    return version(name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid", required=True, type=int)
    parser.add_argument("--port", type=int, default=18000)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    preflight = contract.validate_preflight_report()
    manifest = Path(contract.MODEL_REALPATH + ".sha256")
    if not manifest.is_file() or contract.file_sha256(manifest) != contract.MODEL_MANIFEST_SHA256:
        raise RuntimeError("A1-R2 live model manifest drift")
    cmdline = Path(f"/proc/{args.pid}/cmdline").read_bytes().replace(b"\0", b" ").decode()
    if "vllm" not in cmdline or contract.MODEL_REALPATH not in cmdline or str(args.port) not in cmdline:
        raise RuntimeError("A1-R2 live process cmdline drift")
    with urlopen(f"http://127.0.0.1:{args.port}/v1/models", timeout=10) as response:
        observed = [str(item.get("id")) for item in (json.load(response).get("data") or [])]
    payload = {
        "schema": contract.LIVE_RECEIPT_SCHEMA,
        "status": "PASS",
        "errors": [],
        "generation_calls": 0,
        "mechanism_id": contract.MECHANISM_ID,
        "experiment_id": contract.EXPERIMENT_ID,
        "implementation_commit": preflight["implementation_commit"],
        "preflight_content_sha256": preflight["content_sha256"],
        "config_content_sha256": contract.canonical_sha256(
            json.loads(contract.CONFIG_PATH.read_text(encoding="utf-8"))
        ),
        "served_model_id": contract.MODEL_ID,
        "served_model_ids_observed": observed,
        "model_realpath": contract.MODEL_REALPATH,
        "model_manifest_sha256": contract.MODEL_MANIFEST_SHA256,
        "process_pid": args.pid,
        "process_cmdline": cmdline,
        "port": args.port,
        "packages": {name: _version(name) for name in ("vllm", "torch", "transformers")},
        "qualified_at": datetime.now(timezone.utc).isoformat(),
    }
    receipt = {**payload, "content_sha256": contract.content_sha256(payload)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    contract.validate_launch_receipt(args.output)
    print(json.dumps({"status": "PASS", "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
