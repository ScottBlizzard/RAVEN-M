from __future__ import annotations

import base64
from hashlib import sha256
from io import BytesIO
import os

from PIL import Image


os.environ["RAVEN_MODEL_MODE"] = "mock"

from raven_m.models.server import Engine, _normalise_messages  # noqa: E402


def _one_pixel_png() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (1, 1), color=(12, 34, 56)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_mock_engine_hashes_image_and_returns_schema() -> None:
    image = _one_pixel_png()
    encoded = base64.b64encode(image).decode("ascii")
    raw_messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{encoded}"
                    },
                },
                {"type": "text", "text": "Return one action."},
            ],
        }
    ]

    messages, image_hashes, image_bytes = _normalise_messages(raw_messages)
    content, usage, peak_vram = Engine(mode="mock").generate(messages, 32)

    assert image_hashes == [sha256(image).hexdigest()]
    assert image_bytes == len(image)
    assert '"reason":"mock_connectivity_only"' in content
    assert usage["total_tokens"] == 0
    assert peak_vram is None
