"""Send one hashed AndroidWorld screenshot to the private model service."""

from __future__ import annotations

import argparse
import base64
from hashlib import sha256
import json
from pathlib import Path
import time
from uuid import uuid4

import requests


DEFAULT_PROMPT = """You are controlling an Android phone.
Inspect the screenshot and return exactly one compact JSON object:
{"status":"continue|done|fail","action":{"type":"tap","x":0,"y":0},"reason":"short"}
Coordinates are screenshot pixels. This is a connectivity smoke test; do not
claim task completion unless it is visually supported."""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    raw = args.image.read_bytes()
    image_hash = sha256(raw).hexdigest()
    media_type = "image/png" if args.image.suffix.lower() == ".png" else "image/jpeg"
    encoded = base64.b64encode(raw).decode("ascii")
    call_id = str(uuid4())
    episode_id = f"connectivity_smoke_{int(time.time())}"
    idempotency_key = sha256(
        f"{episode_id}:{call_id}:{image_hash}".encode("utf-8")
    ).hexdigest()
    payload = {
        "model": "Qwen/Qwen3-VL-32B-Instruct",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{encoded}"
                        },
                    },
                    {"type": "text", "text": args.prompt},
                ],
            }
        ],
        "max_tokens": 256,
        "temperature": 0,
    }
    response = requests.post(
        f"{args.url.rstrip('/')}/v1/chat/completions",
        json=payload,
        headers={
            "Idempotency-Key": idempotency_key,
            "X-Call-ID": call_id,
            "X-Episode-ID": episode_id,
        },
        timeout=args.timeout,
    )
    response.raise_for_status()
    result = response.json()
    meta = result.get("raven_meta", {})
    if meta.get("call_id") != call_id:
        raise RuntimeError("Server did not echo the call ID.")
    if meta.get("image_sha256") != [image_hash]:
        raise RuntimeError("Server image hash does not match the transmitted image.")
    if not result.get("choices"):
        raise RuntimeError("Server returned no choices.")

    record = {
        "status": "ok",
        "url": args.url,
        "image": str(args.image.resolve()),
        "image_sha256": image_hash,
        "request_call_id": call_id,
        "request_episode_id": episode_id,
        "response": result,
    }
    rendered = json.dumps(record, indent=2, ensure_ascii=False)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
