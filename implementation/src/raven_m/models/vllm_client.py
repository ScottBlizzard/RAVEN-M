"""Audited OpenAI client for the official-public Qwen vLLM arm."""

from __future__ import annotations

import base64
from hashlib import sha256
import json
from pathlib import Path
import time
from typing import Any
from uuid import uuid4

import requests

from .transformers_client import ModelCall


class VLLMClient:
    """Call a stock vLLM OpenAI server while preserving local audit hashes.

    Unlike :class:`TransformersClient`, this client deliberately does not
    require RAVEN-specific response metadata.  That keeps the baseline server
    identical to Qwen's recommended public serving runtime.
    """

    def __init__(
        self,
        base_url: str,
        *,
        model_id: str,
        model_revision: str,
        backend_id: str,
        temperature: float = 0.7,
        top_p: float = 0.8,
        top_k: int = 20,
        presence_penalty: float = 1.5,
        repetition_penalty: float = 1.0,
        seed: int = 3407,
        timeout_seconds: float = 3600.0,
        retry_backoff_seconds: float = 5.0,
        retry_transient_errors: bool = True,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id
        self.model_revision = model_revision
        self.backend_id = backend_id
        self.temperature = float(temperature)
        self.top_p = float(top_p)
        self.top_k = int(top_k)
        self.presence_penalty = float(presence_penalty)
        self.repetition_penalty = float(repetition_penalty)
        self.seed = int(seed)
        self.timeout_seconds = float(timeout_seconds)
        self.retry_backoff_seconds = float(retry_backoff_seconds)
        self.retry_transient_errors = bool(retry_transient_errors)
        self.session = session or requests.Session()

    @property
    def sampling(self) -> dict[str, Any]:
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "presence_penalty": self.presence_penalty,
            "repetition_penalty": self.repetition_penalty,
            "seed": self.seed,
        }

    def health(self) -> dict[str, Any]:
        response = self.session.get(
            f"{self.base_url}/v1/models",
            timeout=min(self.timeout_seconds, 30.0),
        )
        response.raise_for_status()
        result = response.json()
        served_ids = [
            item.get("id")
            for item in result.get("data", [])
            if isinstance(item, dict)
        ]
        if self.model_id not in served_ids:
            raise RuntimeError(
                f"Expected served model {self.model_id!r}, received {served_ids!r}"
            )
        return {
            "status": "ok",
            "loaded": True,
            "runtime": "vllm_openai",
            "model": self.model_id,
            "revision": self.model_revision,
            "backend": self.backend_id,
            "sampling": self.sampling,
            "served_models": served_ids,
        }

    @staticmethod
    def _encoded_image(path: Path) -> tuple[str, str, str]:
        raw = path.read_bytes()
        media_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        return (
            sha256(raw).hexdigest(),
            media_type,
            base64.b64encode(raw).decode("ascii"),
        )

    def generate(
        self,
        *,
        image_path: Path,
        system_prompt: str,
        user_prompt: str,
        episode_id: str,
        call_label: str,
        max_tokens: int = 32768,
        context_images: list[tuple[str, Path]] | None = None,
        user_prompt_before_image: bool = True,
        current_image_label: str | None = None,
    ) -> ModelCall:
        if context_images:
            raise ValueError("The official-public mobile arm accepts one current image only.")
        if not user_prompt_before_image or current_image_label is not None:
            raise ValueError("Official Qwen mobile messages require text followed by the image.")

        image_sha, media_type, encoded = self._encoded_image(image_path)
        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": system_prompt}],
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{encoded}"
                        },
                    },
                ],
            },
        ]
        payload = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": int(max_tokens),
            **self.sampling,
        }
        request_sha = sha256(
            json.dumps(
                payload,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        prompt_sha = sha256(
            (system_prompt + "\n\0\n" + user_prompt).encode("utf-8")
        ).hexdigest()
        idempotency_key = sha256(
            f"{episode_id}:{call_label}:{request_sha}".encode("utf-8")
        ).hexdigest()
        call_id = str(uuid4())
        request_started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        request_started_monotonic = time.perf_counter()
        transport_attempts = 0

        response: requests.Response | None = None
        last_error: Exception | None = None
        maximum_attempts = 2 if self.retry_transient_errors else 1
        for attempt in range(maximum_attempts):
            transport_attempts += 1
            try:
                response = self.session.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    headers={
                        "Idempotency-Key": idempotency_key,
                        "X-Call-ID": call_id,
                        "X-Episode-ID": episode_id,
                    },
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                break
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = exc
                if attempt + 1 < maximum_attempts:
                    time.sleep(self.retry_backoff_seconds)
        if response is None or not response.ok:
            if last_error is not None:
                raise last_error
            raise RuntimeError("vLLM did not return a valid response.")
        response_received_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        latency_seconds = time.perf_counter() - request_started_monotonic

        result = response.json()
        choices = result.get("choices") or []
        if not choices:
            raise RuntimeError("vLLM returned no choices.")
        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str):
            raise RuntimeError("vLLM returned non-text content.")
        response_model = result.get("model")
        if response_model not in {None, self.model_id}:
            raise RuntimeError(f"vLLM response model drift: {response_model!r}")

        meta = {
            "runtime": "vllm_openai",
            "call_id": call_id,
            "episode_id": episode_id,
            "idempotency_key": idempotency_key,
            "image_sha256": [image_sha],
            "model_revision": self.model_revision,
            "backend_id": self.backend_id,
            "sampling": {**self.sampling, "max_tokens": int(max_tokens)},
            "response_model": response_model,
            "request_started_utc": request_started_utc,
            "response_received_utc": response_received_utc,
            "latency_seconds": latency_seconds,
            "transport_attempts": transport_attempts,
        }
        return ModelCall(
            call_id=call_id,
            episode_id=episode_id,
            idempotency_key=idempotency_key,
            image_sha256=image_sha,
            image_sha256s=(image_sha,),
            prompt_sha256=prompt_sha,
            request_sha256=request_sha,
            response_sha256=sha256(content.encode("utf-8")).hexdigest(),
            content=content,
            usage=result.get("usage") or {},
            raven_meta=meta,
        )
