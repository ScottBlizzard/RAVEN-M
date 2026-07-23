"""Audited client for the private Qwen3-VL Transformers service."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import requests


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
BACKEND_ID = "qwen3_vl_32b_transformers_bf16_4x4090_v1"


@dataclass(frozen=True)
class ModelCall:
    call_id: str
    episode_id: str
    idempotency_key: str
    image_sha256: str
    prompt_sha256: str
    request_sha256: str
    response_sha256: str
    content: str
    usage: dict[str, int]
    raven_meta: dict[str, Any]

    def audit_record(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "episode_id": self.episode_id,
            "idempotency_key": self.idempotency_key,
            "image_sha256": self.image_sha256,
            "prompt_sha256": self.prompt_sha256,
            "request_sha256": self.request_sha256,
            "response_sha256": self.response_sha256,
            "content": self.content,
            "usage": self.usage,
            "raven_meta": self.raven_meta,
        }


class TransformersClient:
    """OpenAI-compatible HTTP client with hash and idempotency checks."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 600.0,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def health(self) -> dict[str, Any]:
        response = self.session.get(
            f"{self.base_url}/health",
            timeout=min(self.timeout_seconds, 30.0),
        )
        response.raise_for_status()
        health = response.json()
        if health.get("model") != MODEL_ID:
            raise RuntimeError(f"Unexpected model service: {health!r}")
        if health.get("revision") != MODEL_REVISION:
            raise RuntimeError(f"Unexpected model revision: {health!r}")
        if health.get("backend") != BACKEND_ID:
            raise RuntimeError(f"Unexpected model backend: {health!r}")
        if not health.get("loaded"):
            raise RuntimeError(f"Model service is not loaded: {health!r}")
        return health

    def generate(
        self,
        *,
        image_path: Path,
        system_prompt: str,
        user_prompt: str,
        episode_id: str,
        call_label: str,
        max_tokens: int = 256,
    ) -> ModelCall:
        raw_image = image_path.read_bytes()
        image_sha = sha256(raw_image).hexdigest()
        media_type = (
            "image/png"
            if image_path.suffix.lower() == ".png"
            else "image/jpeg"
        )
        encoded = base64.b64encode(raw_image).decode("ascii")
        prompt_sha = sha256(
            (system_prompt + "\n\0\n" + user_prompt).encode("utf-8")
        ).hexdigest()
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{encoded}"
                        },
                    },
                    {"type": "text", "text": user_prompt},
                ],
            },
        ]
        payload = {
            "model": MODEL_ID,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0,
        }
        request_sha = sha256(
            json.dumps(
                {
                    "model": MODEL_ID,
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "image_sha256": image_sha,
                    "max_tokens": max_tokens,
                    "temperature": 0,
                },
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        idempotency_key = sha256(
            f"{episode_id}:{call_label}:{request_sha}".encode("utf-8")
        ).hexdigest()
        call_id = str(uuid4())
        headers = {
            "Idempotency-Key": idempotency_key,
            "X-Call-ID": call_id,
            "X-Episode-ID": episode_id,
        }

        last_error: Exception | None = None
        response: requests.Response | None = None
        for _ in range(2):
            try:
                response = self.session.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                break
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = exc
        if response is None or not response.ok:
            if last_error:
                raise last_error
            raise RuntimeError("Model service did not return a valid response.")

        result = response.json()
        choices = result.get("choices") or []
        if not choices:
            raise RuntimeError("Model service returned no choices.")
        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str):
            raise RuntimeError("Model service returned non-text content.")
        meta = result.get("raven_meta") or {}
        if meta.get("call_id") != call_id:
            raise RuntimeError("Model service did not echo the call ID.")
        if meta.get("episode_id") != episode_id:
            raise RuntimeError("Model service did not echo the episode ID.")
        if meta.get("idempotency_key") != idempotency_key:
            raise RuntimeError("Model service did not echo the idempotency key.")
        if meta.get("image_sha256") != [image_sha]:
            raise RuntimeError("Model service image hash mismatch.")
        if meta.get("model_revision") != MODEL_REVISION:
            raise RuntimeError("Model service revision drift detected.")
        if meta.get("backend_id") != BACKEND_ID:
            raise RuntimeError("Model service backend drift detected.")

        return ModelCall(
            call_id=call_id,
            episode_id=episode_id,
            idempotency_key=idempotency_key,
            image_sha256=image_sha,
            prompt_sha256=prompt_sha,
            request_sha256=request_sha,
            response_sha256=sha256(content.encode("utf-8")).hexdigest(),
            content=content,
            usage=result.get("usage") or {},
            raven_meta=meta,
        )
