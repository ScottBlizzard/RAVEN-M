"""Audited one-to-three image OpenAI transport for the MobileUse arm."""

from __future__ import annotations

import base64
import binascii
from copy import deepcopy
from hashlib import sha256
import json
import re
import time
from typing import Any, Sequence
from uuid import uuid4

import requests

from .transformers_client import ModelCall


_DATA_URL = re.compile(
    r"^data:(?P<media>image/(?:png|jpeg|jpg|webp));base64,(?P<data>[A-Za-z0-9+/=]+)$"
)


class VLLMMultiImageClient:
    """Send audited OpenAI chat requests without modifying image order.

    The client accepts only inline image data.  Remote URLs, local paths,
    montage construction, image re-encoding, and more than three images are
    rejected.  Thus the hash list is a direct audit of the exact serialized
    image byte sequence seen by vLLM.
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
            timeout=min(30.0, self.timeout_seconds),
        )
        response.raise_for_status()
        served = [
            item.get("id")
            for item in response.json().get("data", [])
            if isinstance(item, dict)
        ]
        if self.model_id not in served:
            raise RuntimeError(
                f"Expected served model {self.model_id!r}, received {served!r}"
            )
        return {
            "status": "ok",
            "loaded": True,
            "runtime": "vllm_openai_multi_image",
            "model": self.model_id,
            "revision": self.model_revision,
            "backend": self.backend_id,
            "sampling": self.sampling,
            "served_models": served,
        }

    @staticmethod
    def _validate_messages(
        messages: Sequence[dict[str, Any]],
        *,
        expected_images: int | None,
    ) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
        if not isinstance(messages, Sequence) or isinstance(messages, (str, bytes)):
            raise TypeError("messages must be a sequence of dictionaries")
        copied = deepcopy(list(messages))
        image_hashes: list[str] = []
        for message in copied:
            if not isinstance(message, dict) or message.get("role") not in {
                "system", "user", "assistant"
            }:
                raise ValueError("Invalid chat message or role")
            content = message.get("content")
            if isinstance(content, str):
                continue
            if not isinstance(content, list):
                raise ValueError("Message content must be text or a content list")
            for item in content:
                if not isinstance(item, dict):
                    raise ValueError("Content items must be dictionaries")
                item_type = item.get("type")
                if item_type == "text":
                    if not isinstance(item.get("text"), str):
                        raise ValueError("Text content must contain a string")
                    continue
                if item_type != "image_url":
                    raise ValueError(f"Unsupported content type: {item_type!r}")
                image_url = item.get("image_url")
                url = image_url.get("url") if isinstance(image_url, dict) else None
                if not isinstance(url, str):
                    raise ValueError("image_url.url must be a string")
                match = _DATA_URL.fullmatch(url)
                if match is None:
                    raise ValueError("Only inline image data URLs are permitted")
                try:
                    raw = base64.b64decode(match.group("data"), validate=True)
                except (ValueError, binascii.Error) as exc:
                    raise ValueError("Invalid base64 image payload") from exc
                if not raw:
                    raise ValueError("Empty image payload")
                image_hashes.append(sha256(raw).hexdigest())
        if len(image_hashes) > 3:
            raise ValueError("MobileUse transport permits at most three images")
        if expected_images is not None and len(image_hashes) != expected_images:
            raise ValueError(
                f"Expected {expected_images} image(s), found {len(image_hashes)}"
            )
        return copied, tuple(image_hashes)

    def generate_messages(
        self,
        *,
        messages: Sequence[dict[str, Any]],
        episode_id: str,
        call_label: str,
        role: str,
        expected_images: int | None,
        max_tokens: int = 32768,
    ) -> ModelCall:
        validated, image_hashes = self._validate_messages(
            messages, expected_images=expected_images
        )
        payload = {
            "model": self.model_id,
            "messages": validated,
            "max_tokens": int(max_tokens),
            **self.sampling,
        }
        serialized = json.dumps(
            payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        request_sha = sha256(serialized).hexdigest()
        prompt_only = deepcopy(validated)
        for message in prompt_only:
            if isinstance(message.get("content"), list):
                message["content"] = [
                    item for item in message["content"] if item.get("type") == "text"
                ]
        prompt_sha = sha256(
            json.dumps(prompt_only, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        idempotency_key = sha256(
            f"{episode_id}:{call_label}:{request_sha}".encode("utf-8")
        ).hexdigest()
        call_id = str(uuid4())
        started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        started = time.perf_counter()
        response: requests.Response | None = None
        last_error: Exception | None = None
        transport_attempts = 0
        for attempt in range(2):
            transport_attempts += 1
            try:
                response = self.session.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    headers={
                        "Idempotency-Key": idempotency_key,
                        "X-Call-ID": call_id,
                        "X-Episode-ID": episode_id,
                        "X-MobileUse-Role": role,
                    },
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                break
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = exc
                if attempt == 0:
                    time.sleep(self.retry_backoff_seconds)
        if response is None or not response.ok:
            if last_error is not None:
                raise last_error
            raise RuntimeError("vLLM did not return a valid response")
        result = response.json()
        choices = result.get("choices") or []
        if not choices:
            raise RuntimeError("vLLM returned no choices")
        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str):
            raise RuntimeError("vLLM returned non-text content")
        response_model = result.get("model")
        if response_model not in {None, self.model_id}:
            raise RuntimeError(f"vLLM response model drift: {response_model!r}")
        received_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        meta = {
            "runtime": "vllm_openai_multi_image",
            "call_id": call_id,
            "episode_id": episode_id,
            "call_label": call_label,
            "role": role,
            "idempotency_key": idempotency_key,
            "image_sha256": list(image_hashes),
            "image_count": len(image_hashes),
            "model_revision": self.model_revision,
            "backend_id": self.backend_id,
            "sampling": {**self.sampling, "max_tokens": int(max_tokens)},
            "response_model": response_model,
            "request_started_utc": started_utc,
            "response_received_utc": received_utc,
            "latency_seconds": time.perf_counter() - started,
            "transport_attempts": transport_attempts,
        }
        return ModelCall(
            call_id=call_id,
            episode_id=episode_id,
            idempotency_key=idempotency_key,
            image_sha256=image_hashes[-1] if image_hashes else "",
            image_sha256s=image_hashes,
            prompt_sha256=prompt_sha,
            request_sha256=request_sha,
            response_sha256=sha256(content.encode("utf-8")).hexdigest(),
            content=content,
            usage=result.get("usage") or {},
            raven_meta=meta,
        )
