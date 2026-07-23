from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from PIL import Image
import requests

from raven_m.models import transformers_client
from raven_m.models.transformers_client import (
    BACKEND_ID,
    MODEL_REVISION,
    TransformersClient,
)


class Response:
    ok = True

    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class FlakySession:
    def __init__(self, image_sha: str) -> None:
        self.image_sha = image_sha
        self.posts: list[tuple[dict, dict]] = []

    def post(
        self,
        url: str,
        *,
        json: dict,
        headers: dict,
        timeout: float,
    ) -> Response:
        del url, timeout
        self.posts.append(
            (
                json_module_copy(json),
                dict(headers),
            )
        )
        if len(self.posts) == 1:
            raise requests.ConnectionError("tunnel temporarily absent")
        return Response(
            {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"status":"continue","action":'
                                '{"type":"wait","duration_ms":1000},'
                                '"expected_outcome":"wait",'
                                '"decision_summary":"wait"}'
                            )
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                    "total_tokens": 120,
                },
                "raven_meta": {
                    "call_id": headers["X-Call-ID"],
                    "episode_id": headers["X-Episode-ID"],
                    "idempotency_key": headers["Idempotency-Key"],
                    "image_sha256": [self.image_sha],
                    "model_revision": MODEL_REVISION,
                    "backend_id": BACKEND_ID,
                },
            }
        )


def json_module_copy(value: dict) -> dict:
    return json.loads(json.dumps(value))


def test_transport_retry_waits_and_reuses_identity(
    tmp_path: Path,
    monkeypatch,
) -> None:
    image = tmp_path / "screen.png"
    Image.new("RGB", (12, 12), "white").save(image)
    image_sha = sha256(image.read_bytes()).hexdigest()
    session = FlakySession(image_sha)
    sleeps = []
    monkeypatch.setattr(
        transformers_client.time,
        "sleep",
        lambda seconds: sleeps.append(seconds),
    )
    client = TransformersClient(
        "http://127.0.0.1:18000",
        retry_backoff_seconds=45,
        session=session,
    )
    result = client.generate(
        image_path=image,
        system_prompt="system",
        user_prompt="user",
        episode_id="episode_1",
        call_label="step_000_initial",
    )
    assert result.usage["total_tokens"] == 120
    assert sleeps == [45]
    assert len(session.posts) == 2
    assert session.posts[0][0] == session.posts[1][0]
    assert session.posts[0][1] == session.posts[1][1]
