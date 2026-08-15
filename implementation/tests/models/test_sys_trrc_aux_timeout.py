from pathlib import Path

from PIL import Image

from raven_m.models.vllm_client import VLLMClient


class _Response:
    ok = True
    def raise_for_status(self) -> None: pass
    def json(self) -> dict:
        return {"model": "Qwen/Qwen3-VL-32B-Instruct", "choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}


class _Session:
    def __init__(self) -> None: self.timeout = None
    def post(self, _url: str, *, json: dict, headers: dict, timeout: float) -> _Response:
        del json, headers; self.timeout = timeout; return _Response()


def test_per_call_timeout_overrides_executor_default_only_for_aux(tmp_path: Path) -> None:
    image = tmp_path / "screen.png"; Image.new("RGB", (2, 2), "white").save(image)
    session = _Session()
    client = VLLMClient("http://127.0.0.1:18000", model_id="Qwen/Qwen3-VL-32B-Instruct",
                        model_revision="revision", backend_id="backend",
                        timeout_seconds=3600.0, retry_transient_errors=False, session=session)
    call = client.generate(image_path=image, system_prompt="system", user_prompt="user",
                           episode_id="episode", call_label="aux_recovery_001",
                           max_tokens=192, request_timeout_seconds=60.0)
    assert session.timeout == 60.0
    assert call.raven_meta["request_timeout_seconds"] == 60.0
    assert call.raven_meta["transport_attempts"] == 1
