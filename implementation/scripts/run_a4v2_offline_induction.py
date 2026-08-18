#!/usr/bin/env python3
"""Run the seven preregistered text-only AWM induction calls, exactly once each."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import urllib.request


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--induction-index", type=Path, required=True)
    parser.add_argument("--model-id", default="Qwen/Qwen3-VL-32B-Instruct")
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--responses-dir", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    args = parser.parse_args()
    index = json.loads(args.induction_index.read_text(encoding="utf-8"))
    rows = index.get("packets") or []
    if index.get("schema") != "a4v2.awm_induction_index.v1" or len(rows) != 7:
        raise RuntimeError("induction index is incomplete")
    index_sha = _sha(args.induction_index)
    if args.checkpoint.is_file():
        checkpoint = json.loads(args.checkpoint.read_text(encoding="utf-8"))
        if (
            checkpoint.get("schema") != "a4v2.awm_induction_checkpoint.v1"
            or checkpoint.get("induction_index_sha256") != index_sha
            or checkpoint.get("model_id") != args.model_id
            or checkpoint.get("url") != args.url
        ):
            raise RuntimeError("induction checkpoint identity drift")
    else:
        checkpoint = {
            "schema": "a4v2.awm_induction_checkpoint.v1",
            "status": "running",
            "induction_index_sha256": index_sha,
            "model_id": args.model_id,
            "url": args.url,
            "temperature": 0.0,
            "seed": 3407,
            "max_tokens": 2048,
            "transport_policy": "single_attempt_no_retry",
            "calls": [],
        }
    completed = {str(item["route_id"]): item for item in checkpoint["calls"]}
    args.responses_dir.mkdir(parents=True, exist_ok=True)
    for row in rows:
        route_id = str(row["route_id"])
        if route_id in completed:
            response_path = args.responses_dir / f"{route_id}.txt"
            if not response_path.is_file() or _sha(response_path) != completed[route_id]["content_sha256"]:
                raise RuntimeError(f"completed induction response drift: {route_id}")
            continue
        packet_path = args.induction_index.parent / f"{route_id}.json"
        if not packet_path.is_file() or _sha(packet_path) != row["packet_sha256"]:
            raise RuntimeError(f"induction packet drift: {route_id}")
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        request_payload = {
            "model": args.model_id,
            "messages": [{"role": "user", "content": packet["prompt"]}],
            "temperature": 0.0,
            "seed": 3407,
            "max_tokens": 2048,
        }
        request_bytes = json.dumps(request_payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            args.url.rstrip("/") + "/v1/chat/completions",
            data=request_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = datetime.now(timezone.utc).isoformat()
        with urllib.request.urlopen(request, timeout=3600) as response:
            response_bytes = response.read()
        received = json.loads(response_bytes.decode("utf-8"))
        choices = received.get("choices") or []
        content = str(((choices[0].get("message") or {}).get("content") if choices else "") or "").strip()
        if not content:
            raise RuntimeError(f"empty induction response: {route_id}")
        response_path = args.responses_dir / f"{route_id}.txt"
        response_path.write_text(content + "\n", encoding="utf-8")
        checkpoint["calls"].append(
            {
                "route_id": route_id,
                "started_at": started,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "prompt_sha256": packet["prompt_sha256"],
                "request_sha256": sha256(request_bytes).hexdigest(),
                "raw_response_sha256": sha256(response_bytes).hexdigest(),
                "content_path": str(response_path.resolve()),
                "content_sha256": _sha(response_path),
                "usage": received.get("usage"),
                "transport_attempts": 1,
            }
        )
        _atomic_json(args.checkpoint, checkpoint)
    checkpoint["status"] = "complete"
    checkpoint["generation_calls"] = len(checkpoint["calls"])
    if checkpoint["generation_calls"] != 7:
        raise RuntimeError("induction did not close exactly seven calls")
    _atomic_json(args.checkpoint, checkpoint)
    print(json.dumps({"status": "complete", "generation_calls": 7, "checkpoint": str(args.checkpoint)}, indent=2))


if __name__ == "__main__":
    main()

