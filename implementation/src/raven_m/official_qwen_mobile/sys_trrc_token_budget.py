"""Exact request-time multimodal token projection for SYS-TRRC."""

from __future__ import annotations

from hashlib import sha256
import argparse
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

from PIL import Image


PROJECTION_SCHEMA = "sys_trrc_exact_multimodal_token_projection_v1"
PROCESSOR_CLOSURE_FILES = (
    "chat_template.json", "tokenizer.json", "tokenizer_config.json",
    "merges.txt", "vocab.json", "config.json", "configuration.json",
    "generation_config.json", "preprocessor_config.json",
    "video_preprocessor_config.json",
)
PROCESSOR_RUNTIME_PACKAGES = (
    "Pillow", "huggingface-hub", "numpy", "safetensors", "tokenizers",
    "torch", "torchvision", "transformers",
)


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _canonical_sha(value: Any) -> str:
    return sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _processor_file_hashes(
    model_path: Path, *, require_exact: bool = False,
) -> dict[str, str]:
    """Hash all processor inputs; optionally require a processor-only snapshot."""
    root = Path(model_path).resolve()
    if not root.is_dir():
        raise RuntimeError(f"SYS-TRRC processor path is missing: {root}")
    observed = {
        path.relative_to(root).as_posix(): path
        for path in root.rglob("*") if path.is_file()
    }
    expected = set(PROCESSOR_CLOSURE_FILES)
    if not expected.issubset(observed) or (require_exact and set(observed) != expected):
        missing = sorted(expected - set(observed))
        unexpected = sorted(set(observed) - expected)
        raise RuntimeError(
            "SYS-TRRC processor closure drift: "
            f"missing={missing}, unexpected={unexpected}"
        )
    closure_names = set(observed) if require_exact else expected
    for relative in closure_names:
        path = observed[relative]
        try:
            path.resolve().relative_to(root)
        except ValueError as exc:
            raise RuntimeError(
                f"SYS-TRRC processor file escapes snapshot: {relative}"
            ) from exc
    return {name: _sha256(observed[name]) for name in sorted(expected)}


def _runtime_identity() -> dict[str, Any]:
    executable = Path(sys.executable).resolve()
    packages: dict[str, str] = {}
    for name in PROCESSOR_RUNTIME_PACKAGES:
        try:
            packages[name] = version(name)
        except PackageNotFoundError as exc:
            raise RuntimeError(
                f"SYS-TRRC processor runtime package is missing: {name}"
            ) from exc
    return {
        "schema": "sys_trrc_local_processor_runtime_v1",
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "python_executable": str(executable),
        "python_executable_sha256": _sha256(executable),
        "packages": packages,
    }


class ExactQwenMultimodalTokenProjector:
    """Count the exact chat-template and vision tokens before HTTP transport."""

    def __init__(self, model_path: Path, *, expected_revision: str) -> None:
        from transformers import AutoProcessor

        self.model_path = Path(model_path).resolve()
        if not self.model_path.is_dir():
            raise RuntimeError(f"SYS-TRRC processor path is missing: {self.model_path}")
        self.expected_revision = str(expected_revision)
        self.processor = AutoProcessor.from_pretrained(
            str(self.model_path), local_files_only=True, trust_remote_code=False
        )
        # A full remote model directory legitimately also contains weight shards.
        # Those bytes are qualified by the separate model manifest closure.
        self.processor_files_sha256 = _processor_file_hashes(
            self.model_path, require_exact=False
        )

    def __call__(
        self, system_prompt: str, user_prompt: str, screenshot_path: str
    ) -> dict[str, Any]:
        path = Path(screenshot_path).resolve()
        if not path.is_file():
            raise RuntimeError(f"SYS-TRRC current screenshot is missing: {path}")
        screenshot_sha256 = _sha256(path)
        with Image.open(path) as source:
            image = source.convert("RGB").copy()
        messages = [
            {
                "role": "system",
                "content": [{"type": "text", "text": str(system_prompt)}],
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": str(user_prompt)},
                    {"type": "image", "image": image},
                ],
            },
        ]
        encoded = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
        attention_mask = encoded.get("attention_mask")
        input_ids = encoded.get("input_ids")
        if attention_mask is None or input_ids is None:
            raise RuntimeError("SYS-TRRC processor omitted token tensors")
        exact_tokens = int(attention_mask[0].sum().item())
        if exact_tokens != int(input_ids.shape[-1]):
            raise RuntimeError("SYS-TRRC unexpected padded single-request projection")
        grid = encoded.get("image_grid_thw")
        grid_value = grid.tolist() if grid is not None else None
        identity = {
            "content_order": ["system:text", "user:text", "user:image"],
            "system_prompt": str(system_prompt),
            "user_prompt": str(user_prompt),
            "current_screenshot_sha256": screenshot_sha256,
        }
        return {
            "schema": PROJECTION_SCHEMA,
            "model_revision": self.expected_revision,
            "processor_files_sha256": dict(self.processor_files_sha256),
            "messages_sha256": _canonical_sha(identity),
            "current_screenshot_sha256": screenshot_sha256,
            "current_image_size": [int(image.width), int(image.height)],
            "content_order": identity["content_order"],
            "add_generation_prompt": True,
            "image_grid_thw": grid_value,
            "expanded_image_token_count": int(
                (input_ids[0] == int(
                    self.processor.tokenizer.convert_tokens_to_ids("<|image_pad|>")
                )).sum().item()
            ),
            "exact_multimodal_input_tokens": exact_tokens,
        }


class SubprocessExactQwenMultimodalTokenProjector:
    """Run the exact processor in an isolated Python with Torch/Torchvision.

    AndroidWorld's frozen controller environment intentionally does not carry
    those heavy packages.  Isolation avoids changing its dependency graph while
    retaining a pre-HTTP exact projection from the same processor snapshot.
    """

    def __init__(self, python_executable: Path, model_path: Path, *, expected_revision: str) -> None:
        self.python_executable = Path(python_executable).resolve()
        self.model_path = Path(model_path).resolve()
        self.expected_revision = str(expected_revision)
        if not self.python_executable.is_file():
            raise RuntimeError("SYS-TRRC processor Python is missing")
        # The Windows-side snapshot is intentionally processor-only, so any
        # additional file could alter AutoProcessor resolution and is rejected.
        self.processor_files_sha256 = _processor_file_hashes(
            self.model_path, require_exact=True
        )
        self._cache: dict[str, dict[str, Any]] = {}
        completed = subprocess.run(
            [str(self.python_executable), str(Path(__file__).resolve()),
             "--inspect-runtime"],
            text=True, capture_output=True, timeout=30,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "SYS-TRRC isolated processor runtime inspection failed: "
                + completed.stderr[-1000:]
            )
        try:
            self.runtime_identity = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "SYS-TRRC isolated processor returned invalid runtime identity"
            ) from exc
        expected_python_sha = _sha256(self.python_executable)
        if (
            self.runtime_identity.get("schema")
            != "sys_trrc_local_processor_runtime_v1"
            or self.runtime_identity.get("python_executable_sha256")
            != expected_python_sha
            or set(self.runtime_identity.get("packages") or {})
            != set(PROCESSOR_RUNTIME_PACKAGES)
        ):
            raise RuntimeError("SYS-TRRC isolated processor runtime identity drift")

    def __call__(self, system_prompt: str, user_prompt: str, screenshot_path: str) -> dict[str, Any]:
        return self.project_many([{
            "system_prompt": str(system_prompt),
            "user_prompt": str(user_prompt),
            "screenshot_path": str(Path(screenshot_path).resolve()),
        }])[0]

    def project_many(self, requests: list[dict[str, str]]) -> list[dict[str, Any]]:
        normalized = []
        for item in requests:
            screenshot = Path(item["screenshot_path"]).resolve()
            if not screenshot.is_file():
                raise RuntimeError(
                    f"SYS-TRRC current screenshot is missing: {screenshot}"
                )
            normalized.append({
                "system_prompt": str(item["system_prompt"]),
                "user_prompt": str(item["user_prompt"]),
                "screenshot_path": str(screenshot),
                "screenshot_sha256": _sha256(screenshot),
            })
        keys = [_canonical_sha(item) for item in normalized]
        missing_keys: list[str] = []
        missing_requests: list[dict[str, str]] = []
        for key, request in zip(keys, normalized, strict=True):
            if key not in self._cache and key not in missing_keys:
                missing_keys.append(key)
                missing_requests.append(request)
        if not missing_requests:
            if any(
                _sha256(Path(request["screenshot_path"]))
                != request["screenshot_sha256"]
                for request in normalized
            ):
                raise RuntimeError("SYS-TRRC screenshot changed during cache lookup")
            return [dict(self._cache[key]) for key in keys]
        completed = subprocess.run(
            [
                str(self.python_executable), str(Path(__file__).resolve()),
                "--worker", "--model-path", str(self.model_path),
                "--revision", self.expected_revision,
            ],
            input=json.dumps(missing_requests, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=600,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "SYS-TRRC isolated token projection failed: "
                + completed.stderr[-1000:]
            )
        try:
            response = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("SYS-TRRC isolated projector returned invalid JSON") from exc
        if (
            not isinstance(response, dict)
            or response.get("runtime_identity") != self.runtime_identity
            or not isinstance(response.get("projections"), list)
            or len(response["projections"]) != len(missing_requests)
        ):
            raise RuntimeError("SYS-TRRC isolated processor batch closure drift")
        for key, request, projection in zip(
            missing_keys, missing_requests, response["projections"], strict=True
        ):
            screenshot = Path(request["screenshot_path"])
            identity = {
                "content_order": ["system:text", "user:text", "user:image"],
                "system_prompt": request["system_prompt"],
                "user_prompt": request["user_prompt"],
                "current_screenshot_sha256": request["screenshot_sha256"],
            }
            if (
                projection.get("schema") != PROJECTION_SCHEMA
                or projection.get("model_revision") != self.expected_revision
                or projection.get("processor_files_sha256")
                != self.processor_files_sha256
                or projection.get("messages_sha256") != _canonical_sha(identity)
                or projection.get("current_screenshot_sha256")
                != identity["current_screenshot_sha256"]
                or _sha256(screenshot) != request["screenshot_sha256"]
            ):
                raise RuntimeError("SYS-TRRC isolated processor projection drift")
            self._cache[key] = dict(projection)
        if any(
            _sha256(Path(request["screenshot_path"]))
            != request["screenshot_sha256"]
            for request in normalized
        ):
            raise RuntimeError("SYS-TRRC screenshot changed during projection batch")
        return [dict(self._cache[key]) for key in keys]

    def text_delta(self, base_text: str, final_text: str) -> int:
        completed = subprocess.run(
            [
                str(self.python_executable), str(Path(__file__).resolve()),
                "--text-delta", "--model-path", str(self.model_path),
            ],
            input=json.dumps({
                "base_text": str(base_text), "final_text": str(final_text),
            }, ensure_ascii=False),
            text=True, capture_output=True, timeout=120,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "SYS-TRRC isolated text delta failed: " + completed.stderr[-1000:]
            )
        try:
            response = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("SYS-TRRC isolated text delta returned invalid JSON") from exc
        if (
            response.get("runtime_identity") != self.runtime_identity
            or response.get("processor_files_sha256")
            != self.processor_files_sha256
            or not isinstance(response.get("delta"), int)
            or int(response["delta"]) < 0
        ):
            raise RuntimeError("SYS-TRRC isolated text delta closure drift")
        return int(response["delta"])


class SubprocessExactQwenTextDeltaCounter:
    """Use the same frozen isolated runtime as the multimodal projector."""

    def __init__(self, projector: SubprocessExactQwenMultimodalTokenProjector) -> None:
        self.projector = projector

    def __call__(self, base_text: str, final_text: str) -> int:
        return self.projector.text_delta(base_text, final_text)


class ExactQwenTextDeltaCounter:
    """Count the exact tokenizer delta introduced by one advice block."""

    def __init__(self, model_path: Path) -> None:
        from transformers import AutoTokenizer

        self.model_path = Path(model_path).resolve()
        self.tokenizer = AutoTokenizer.from_pretrained(
            str(self.model_path), local_files_only=True, trust_remote_code=False
        )

    def __call__(self, base_text: str, final_text: str) -> int:
        base_count = len(self.tokenizer.encode(str(base_text), add_special_tokens=False))
        final_count = len(self.tokenizer.encode(str(final_text), add_special_tokens=False))
        delta = final_count - base_count
        if delta < 0:
            raise RuntimeError("SYS-TRRC advice token delta is negative")
        return delta


def _worker_main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--worker", action="store_true")
    group.add_argument("--inspect-runtime", action="store_true")
    group.add_argument("--text-delta", action="store_true")
    parser.add_argument("--model-path", type=Path)
    parser.add_argument("--revision")
    args = parser.parse_args()
    if args.inspect_runtime:
        sys.stdout.write(json.dumps(_runtime_identity(), sort_keys=True))
        return 0
    if args.text_delta:
        if args.model_path is None:
            parser.error("--text-delta requires --model-path")
        request = json.loads(sys.stdin.read())
        counter = ExactQwenTextDeltaCounter(args.model_path)
        response = {
            "runtime_identity": _runtime_identity(),
            "processor_files_sha256": _processor_file_hashes(
                args.model_path, require_exact=True
            ),
            "delta": counter(request["base_text"], request["final_text"]),
        }
        sys.stdout.write(json.dumps(response, ensure_ascii=False, sort_keys=True))
        return 0
    if args.model_path is None or not args.revision:
        parser.error("--worker requires --model-path and --revision")
    requests = json.loads(sys.stdin.read())
    if not isinstance(requests, list) or not requests:
        raise RuntimeError("SYS-TRRC worker requires a non-empty request list")
    projector = ExactQwenMultimodalTokenProjector(
        args.model_path, expected_revision=args.revision
    )
    results = [
        projector(
            request["system_prompt"], request["user_prompt"],
            request["screenshot_path"],
        )
        for request in requests
    ]
    response = {"runtime_identity": _runtime_identity(), "projections": results}
    sys.stdout.write(json.dumps(response, ensure_ascii=False, sort_keys=True))
    return 0


__all__ = [
    "ExactQwenMultimodalTokenProjector",
    "SubprocessExactQwenMultimodalTokenProjector",
    "SubprocessExactQwenTextDeltaCounter",
    "ExactQwenTextDeltaCounter",
    "PROJECTION_SCHEMA",
    "PROCESSOR_CLOSURE_FILES",
    "PROCESSOR_RUNTIME_PACKAGES",
]


if __name__ == "__main__":
    raise SystemExit(_worker_main())
