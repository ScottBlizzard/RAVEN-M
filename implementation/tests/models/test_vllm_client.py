from __future__ import annotations

from pathlib import Path

from PIL import Image

from raven_m.models.vllm_client import VLLMClient


class Response:
    ok = True

    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class Session:
    def __init__(self) -> None:
        self.posted: dict | None = None

    def get(self, url: str, *, timeout: float) -> Response:
        assert url.endswith("/v1/models")
        assert timeout == 30.0
        return Response({"data": [{"id": "Qwen/Qwen3-VL-32B-Instruct"}]})

    def post(
        self,
        url: str,
        *,
        json: dict,
        headers: dict,
        timeout: float,
    ) -> Response:
        assert url.endswith("/v1/chat/completions")
        assert headers["X-Episode-ID"] == "episode"
        assert timeout == 3600.0
        self.posted = json
        return Response(
            {
                "model": "Qwen/Qwen3-VL-32B-Instruct",
                "choices": [
                    {
                        "message": {
                            "content": (
                                "Thought: inspect.\nAction: tap.\n<tool_call>\n"
                                '{"name":"mobile_use","arguments":'
                                '{"action":"click","coordinate":[1,2]}}'
                                "\n</tool_call>"
                            )
                        }
                    }
                ],
                "usage": {"total_tokens": 12},
            }
        )


def test_vllm_client_locks_official_public_sampling_and_message_order(
    tmp_path: Path,
) -> None:
    image = tmp_path / "screen.png"
    Image.new("RGB", (8, 8), "white").save(image)
    session = Session()
    client = VLLMClient(
        "http://127.0.0.1:18000",
        model_id="Qwen/Qwen3-VL-32B-Instruct",
        model_revision="revision",
        backend_id="backend",
        session=session,
    )

    assert client.health()["runtime"] == "vllm_openai"
    result = client.generate(
        image_path=image,
        system_prompt="system",
        user_prompt="user",
        episode_id="episode",
        call_label="step_000",
    )

    payload = session.posted
    assert payload is not None
    assert payload["temperature"] == 0.7
    assert payload["top_p"] == 0.8
    assert payload["top_k"] == 20
    assert payload["presence_penalty"] == 1.5
    assert payload["repetition_penalty"] == 1.0
    assert payload["seed"] == 3407
    assert payload["max_tokens"] == 32768
    assert payload["messages"][0]["content"] == [
        {"type": "text", "text": "system"}
    ]
    assert [
        item["type"] for item in payload["messages"][1]["content"]
    ] == ["text", "image_url"]
    assert result.raven_meta["runtime"] == "vllm_openai"
