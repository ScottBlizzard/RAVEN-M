"""Private, single-worker Qwen3-VL service for split-host experiments."""

from __future__ import annotations

import base64
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import threading
import time
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from PIL import Image


MODEL_ID = os.environ.get("RAVEN_MODEL_ID", "Qwen/Qwen3-VL-32B-Instruct")
MODEL_REVISION = os.environ.get(
    "RAVEN_MODEL_REVISION",
    "0cfaf48183f594c314753d30a4c4974bc75f3ccb",
)
BACKEND_ID = os.environ.get(
    "RAVEN_BACKEND_ID",
    "qwen3_vl_32b_transformers_bf16_4x4090_v1",
)
MODEL_MODE = os.environ.get("RAVEN_MODEL_MODE", "mock").lower()
MODEL_CACHE = os.environ.get("RAVEN_MODEL_CACHE")
LOCAL_FILES_ONLY = os.environ.get("RAVEN_LOCAL_FILES_ONLY", "1") == "1"
MAX_NEW_TOKENS = int(os.environ.get("RAVEN_MAX_NEW_TOKENS", "256"))
MAX_IMAGE_BYTES = int(os.environ.get("RAVEN_MAX_IMAGE_BYTES", str(12 * 1024 * 1024)))
LOG_PATH = Path(
    os.environ.get(
        "RAVEN_SERVER_LOG",
        str(Path(__file__).resolve().parents[3] / "outputs" / "model_server.jsonl"),
    )
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(record: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    with LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write(line + "\n")


def _parse_max_memory() -> dict[int, str] | None:
    raw = os.environ.get("RAVEN_GPU_MAX_MEMORY", "")
    if not raw:
        return None
    result: dict[int, str] = {}
    for item in raw.split(","):
        index, value = item.split(":", 1)
        result[int(index.strip())] = value.strip()
    return result


def _decode_data_image(url: str) -> tuple[Image.Image, str, int]:
    if not url.startswith("data:image/") or ";base64," not in url:
        raise ValueError("Only base64 data:image URLs are accepted.")
    _, payload = url.split(";base64,", 1)
    raw = base64.b64decode(payload, validate=True)
    if len(raw) > MAX_IMAGE_BYTES:
        raise ValueError(f"Image exceeds {MAX_IMAGE_BYTES} bytes.")
    digest = sha256(raw).hexdigest()
    image = Image.open(BytesIO(raw))
    image.load()
    return image.convert("RGB"), digest, len(raw)


def _normalise_messages(
    raw_messages: Any,
) -> tuple[list[dict[str, Any]], list[str], int]:
    if not isinstance(raw_messages, list) or not raw_messages:
        raise ValueError("messages must be a non-empty list.")

    messages: list[dict[str, Any]] = []
    image_hashes: list[str] = []
    image_bytes = 0
    for raw_message in raw_messages:
        if not isinstance(raw_message, dict):
            raise ValueError("Each message must be an object.")
        role = raw_message.get("role")
        if role not in {"system", "user", "assistant"}:
            raise ValueError(f"Unsupported role: {role!r}")
        raw_content = raw_message.get("content", "")
        if isinstance(raw_content, str):
            content: str | list[dict[str, Any]] = raw_content
        elif isinstance(raw_content, list):
            content = []
            for item in raw_content:
                if not isinstance(item, dict):
                    raise ValueError("Message content items must be objects.")
                item_type = item.get("type")
                if item_type == "text":
                    content.append({"type": "text", "text": str(item.get("text", ""))})
                elif item_type in {"image", "image_url"}:
                    image_value = item.get("image")
                    if item_type == "image_url":
                        image_url = item.get("image_url", {})
                        image_value = (
                            image_url.get("url")
                            if isinstance(image_url, dict)
                            else image_url
                        )
                    if not isinstance(image_value, str):
                        raise ValueError("Image content requires a data URL.")
                    image, digest, byte_count = _decode_data_image(image_value)
                    content.append({"type": "image", "image": image})
                    image_hashes.append(digest)
                    image_bytes += byte_count
                else:
                    raise ValueError(f"Unsupported content type: {item_type!r}")
        else:
            raise ValueError("Message content must be a string or list.")
        messages.append({"role": role, "content": content})
    return messages, image_hashes, image_bytes


@dataclass
class Engine:
    mode: str
    model: Any = None
    processor: Any = None
    loaded_at: str | None = None
    load_error: str | None = None
    generation_lock: threading.Lock = field(default_factory=threading.Lock)

    def load(self) -> None:
        if self.mode == "mock":
            self.loaded_at = _utc_now()
            return
        if self.mode != "transformers":
            raise RuntimeError(f"Unsupported RAVEN_MODEL_MODE={self.mode!r}")
        if self.model is not None:
            return

        try:
            import torch
            from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

            model_kwargs: dict[str, Any] = {
                "revision": MODEL_REVISION,
                "cache_dir": MODEL_CACHE,
                "dtype": torch.bfloat16,
                "device_map": "auto",
                "attn_implementation": os.environ.get(
                    "RAVEN_ATTN_IMPLEMENTATION", "sdpa"
                ),
                "low_cpu_mem_usage": True,
                "trust_remote_code": False,
                "local_files_only": LOCAL_FILES_ONLY,
            }
            max_memory = _parse_max_memory()
            if max_memory:
                model_kwargs["max_memory"] = max_memory
            self.model = Qwen3VLForConditionalGeneration.from_pretrained(
                MODEL_ID,
                **model_kwargs,
            ).eval()
            self.processor = AutoProcessor.from_pretrained(
                MODEL_ID,
                revision=MODEL_REVISION,
                cache_dir=MODEL_CACHE,
                trust_remote_code=False,
                local_files_only=LOCAL_FILES_ONLY,
            )
            self.loaded_at = _utc_now()
        except Exception as exc:
            self.load_error = f"{type(exc).__name__}: {exc}"
            raise

    def _mock_generate(self) -> tuple[str, dict[str, int]]:
        content = json.dumps(
            {
                "status": "done",
                "action": None,
                "reason": "mock_connectivity_only",
            },
            separators=(",", ":"),
        )
        return content, {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    def _transformers_generate(
        self,
        messages: list[dict[str, Any]],
        max_new_tokens: int,
    ) -> tuple[str, dict[str, int]]:
        import torch

        self.load()
        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
        input_device = next(self.model.parameters()).device
        inputs = inputs.to(input_device)
        prompt_tokens = int(inputs["input_ids"].shape[-1])
        with torch.inference_mode():
            generated = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                use_cache=True,
            )
        completion_ids = generated[:, prompt_tokens:]
        content = self.processor.batch_decode(
            completion_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]
        completion_tokens = int(completion_ids.shape[-1])
        return content, {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }

    def generate(
        self,
        messages: list[dict[str, Any]],
        max_new_tokens: int,
    ) -> tuple[str, dict[str, int], int | None]:
        with self.generation_lock:
            if self.mode == "mock":
                content, usage = self._mock_generate()
            else:
                content, usage = self._transformers_generate(
                    messages, max_new_tokens
                )
            peak_vram = None
            if self.mode == "transformers":
                import torch

                peak_vram = max(
                    (
                        int(torch.cuda.max_memory_allocated(index))
                        for index in range(torch.cuda.device_count())
                    ),
                    default=0,
                )
            return content, usage, peak_vram


engine = Engine(mode=MODEL_MODE)
idempotency_cache: OrderedDict[str, dict[str, Any]] = OrderedDict()
idempotency_lock = threading.Lock()

app = FastAPI(title="RAVEN-M model service", version="0.1.0")


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok" if not engine.load_error else "degraded",
        "mode": engine.mode,
        "model": MODEL_ID,
        "revision": MODEL_REVISION,
        "backend": BACKEND_ID,
        "loaded": engine.loaded_at is not None,
        "loaded_at": engine.loaded_at,
        "load_error": engine.load_error,
        "concurrent_generations": 1,
        "local_files_only": LOCAL_FILES_ONLY,
        "time": _utc_now(),
    }


@app.post("/load")
async def load_model() -> dict[str, Any]:
    try:
        await run_in_threadpool(engine.load)
    except Exception as exc:
        _append_jsonl(
            {
                "event": "load_error",
                "time": _utc_now(),
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
        raise HTTPException(status_code=500, detail=engine.load_error) from exc
    return health()


@app.post("/v1/chat/completions")
async def chat_completions(
    payload: dict[str, Any],
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    x_call_id: str | None = Header(default=None, alias="X-Call-ID"),
    x_episode_id: str | None = Header(default=None, alias="X-Episode-ID"),
) -> dict[str, Any]:
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key is required.")
    with idempotency_lock:
        cached = idempotency_cache.get(idempotency_key)
        if cached is not None:
            return cached

    call_id = x_call_id or str(uuid4())
    episode_id = x_episode_id or "unassigned"
    started = time.monotonic()
    try:
        messages, image_hashes, image_bytes = _normalise_messages(
            payload.get("messages")
        )
        requested_tokens = int(payload.get("max_tokens", MAX_NEW_TOKENS))
        max_new_tokens = max(1, min(requested_tokens, MAX_NEW_TOKENS))
        content, usage, peak_vram = await run_in_threadpool(
            engine.generate,
            messages,
            max_new_tokens,
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        latency = time.monotonic() - started
        _append_jsonl(
            {
                "event": "generation_error",
                "time": _utc_now(),
                "call_id": call_id,
                "episode_id": episode_id,
                "idempotency_key": idempotency_key,
                "latency_seconds": latency,
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    latency = time.monotonic() - started
    response = {
        "id": call_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": MODEL_ID,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": usage,
        "raven_meta": {
            "episode_id": episode_id,
            "call_id": call_id,
            "idempotency_key": idempotency_key,
            "model_revision": MODEL_REVISION,
            "backend_id": BACKEND_ID,
            "mode": engine.mode,
            "image_sha256": image_hashes,
            "image_bytes": image_bytes,
            "latency_seconds": latency,
            "peak_vram_bytes": peak_vram,
            "client": request.client.host if request.client else None,
        },
    }
    _append_jsonl(
        {
            "event": "generation_complete",
            "time": _utc_now(),
            **response["raven_meta"],
            "usage": usage,
            "response_sha256": sha256(content.encode("utf-8")).hexdigest(),
        }
    )
    with idempotency_lock:
        idempotency_cache[idempotency_key] = response
        idempotency_cache.move_to_end(idempotency_key)
        while len(idempotency_cache) > 512:
            idempotency_cache.popitem(last=False)
    return response
