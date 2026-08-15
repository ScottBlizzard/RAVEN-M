from __future__ import annotations

from hashlib import sha256
import importlib.util
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from raven_m.official_qwen_mobile.sys_trrc_token_budget import (
    ExactQwenMultimodalTokenProjector,
    PROCESSOR_CLOSURE_FILES,
    PROJECTION_SCHEMA,
    SubprocessExactQwenMultimodalTokenProjector,
    _canonical_sha,
    _processor_file_hashes,
)


class _FakeProcessor:
    def __init__(self, *, padded: bool = False) -> None:
        self.padded = padded
        self.messages = None
        self.kwargs = None
        self.tokenizer = type(
            "FakeTokenizer", (),
            {"convert_tokens_to_ids": staticmethod(lambda _token: 0)},
        )()

    def apply_chat_template(self, messages, **kwargs):
        self.messages = messages
        self.kwargs = kwargs
        length = 8 if self.padded else 7
        return {
            "input_ids": np.zeros((1, length), dtype=np.int64),
            "attention_mask": np.ones((1, 7), dtype=np.int64),
            "image_grid_thw": np.asarray([[1, 2, 3]], dtype=np.int64),
        }


def _projector(processor: _FakeProcessor) -> ExactQwenMultimodalTokenProjector:
    value = ExactQwenMultimodalTokenProjector.__new__(
        ExactQwenMultimodalTokenProjector
    )
    value.expected_revision = "revision"
    value.processor_files_sha256 = {"tokenizer.json": "a" * 64}
    value.processor = processor
    return value


def test_exact_projector_uses_text_then_current_rgb_image(tmp_path) -> None:
    screenshot = tmp_path / "screen.png"
    Image.fromarray(np.full((12, 20, 3), 40, dtype=np.uint8)).save(screenshot)
    processor = _FakeProcessor()
    result = _projector(processor)("system", "user", str(screenshot))
    assert result["exact_multimodal_input_tokens"] == 7
    assert result["current_screenshot_sha256"] == sha256(
        screenshot.read_bytes()
    ).hexdigest()
    assert result["current_image_size"] == [20, 12]
    assert result["image_grid_thw"] == [[1, 2, 3]]
    assert result["expanded_image_token_count"] == 7
    assert result["content_order"] == [
        "system:text",
        "user:text",
        "user:image",
    ]
    assert processor.kwargs == {
        "tokenize": True,
        "add_generation_prompt": True,
        "return_dict": True,
        "return_tensors": "pt",
    }
    assert processor.messages[1]["content"][0] == {
        "type": "text",
        "text": "user",
    }
    assert processor.messages[1]["content"][1]["type"] == "image"


def test_projector_rejects_unexpected_padding(tmp_path) -> None:
    screenshot = tmp_path / "screen.png"
    Image.fromarray(np.zeros((8, 8, 3), dtype=np.uint8)).save(screenshot)
    with pytest.raises(RuntimeError, match="padded"):
        _projector(_FakeProcessor(padded=True))("system", "user", str(screenshot))


def test_processor_snapshot_requires_exact_complete_file_closure(tmp_path) -> None:
    for ordinal, name in enumerate(PROCESSOR_CLOSURE_FILES):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(f"fixture-{ordinal}".encode())
    hashes = _processor_file_hashes(tmp_path, require_exact=True)
    assert set(hashes) == set(PROCESSOR_CLOSURE_FILES)

    extra = tmp_path / "unbound.json"
    extra.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="unexpected=.*unbound.json"):
        _processor_file_hashes(tmp_path, require_exact=True)
    assert set(_processor_file_hashes(tmp_path, require_exact=False)) == set(
        PROCESSOR_CLOSURE_FILES
    )


def test_subprocess_projection_cache_is_bound_to_current_png_bytes(
    tmp_path, monkeypatch,
) -> None:
    screenshot = tmp_path / "screen.png"
    screenshot.write_bytes(b"first")
    projector = SubprocessExactQwenMultimodalTokenProjector.__new__(
        SubprocessExactQwenMultimodalTokenProjector
    )
    projector.python_executable = Path(__import__("sys").executable)
    projector.model_path = tmp_path
    projector.expected_revision = "revision"
    projector.processor_files_sha256 = {"tokenizer.json": "a" * 64}
    projector.runtime_identity = {"schema": "runtime"}
    projector._cache = {}
    calls = []

    def fake_run(*_args, **kwargs):
        requests = __import__("json").loads(kwargs["input"])
        calls.append(requests)
        projections = []
        for request in requests:
            screenshot_sha = sha256(Path(request["screenshot_path"]).read_bytes()).hexdigest()
            identity = {
                "content_order": ["system:text", "user:text", "user:image"],
                "system_prompt": request["system_prompt"],
                "user_prompt": request["user_prompt"],
                "current_screenshot_sha256": screenshot_sha,
            }
            projections.append({
                "schema": PROJECTION_SCHEMA,
                "model_revision": "revision",
                "processor_files_sha256": projector.processor_files_sha256,
                "messages_sha256": _canonical_sha(identity),
                "current_screenshot_sha256": screenshot_sha,
            })
        response = {"runtime_identity": projector.runtime_identity,
                    "projections": projections}
        return type("Completed", (), {
            "returncode": 0, "stdout": __import__("json").dumps(response),
            "stderr": "",
        })()

    monkeypatch.setattr("subprocess.run", fake_run)
    first = projector("system", "user", str(screenshot))
    screenshot.write_bytes(b"second")
    second = projector("system", "user", str(screenshot))
    assert len(calls) == 2
    assert first["current_screenshot_sha256"] != second["current_screenshot_sha256"]


def _qualifier_module():
    root = Path(__file__).resolve().parents[3]
    path = root / "implementation/scripts/qualify_sys_trrc_server.py"
    spec = importlib.util.spec_from_file_location("qualify_sys_trrc_server_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_model_manifest_hashes_every_file_and_rejects_unlisted_files(tmp_path) -> None:
    qualifier = _qualifier_module()
    model = tmp_path / "model"
    model.mkdir()
    first = model / "config.json"
    second = model / "weights.bin"
    first.write_bytes(b"config")
    second.write_bytes(b"weights")
    manifest = tmp_path / "model.sha256"
    manifest.write_text(
        f"{sha256(first.read_bytes()).hexdigest()}  config.json\n"
        f"{sha256(second.read_bytes()).hexdigest()}  weights.bin\n",
        encoding="utf-8",
    )
    report = qualifier.verify_model_manifest(model, manifest)
    assert report["directory_closed"] is True
    assert [row["path"] for row in report["files"]] == [
        "config.json", "weights.bin",
    ]

    (model / "adapter_config.json").write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="unmanifested=.*adapter_config.json"):
        qualifier.verify_model_manifest(model, manifest)
