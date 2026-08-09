import base64
from hashlib import sha256

import pytest

from raven_m.models.vllm_multi_image_client import VLLMMultiImageClient


def data_url(raw: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def messages(images):
    return [{
        "role": "user",
        "content": [
            item
            for index, image in enumerate(images)
            for item in (
                {"type": "text", "text": f"image-{index}"},
                {"type": "image_url", "image_url": {"url": data_url(image)}},
            )
        ],
    }]


def test_one_two_three_image_order_and_hashes_are_preserved():
    raws = [b"before", b"after", b"latest"]
    for count in (1, 2, 3):
        _, hashes = VLLMMultiImageClient._validate_messages(
            messages(raws[:count]), expected_images=count
        )
        assert hashes == tuple(sha256(raw).hexdigest() for raw in raws[:count])


def test_more_than_three_and_remote_images_rejected():
    with pytest.raises(ValueError, match="at most three"):
        VLLMMultiImageClient._validate_messages(messages([b"a", b"b", b"c", b"d"]), expected_images=None)
    with pytest.raises(ValueError, match="inline"):
        VLLMMultiImageClient._validate_messages([
            {"role": "user", "content": [{"type": "image_url", "image_url": {"url": "https://example.com/x.png"}}]}
        ], expected_images=1)


def test_expected_count_mismatch_rejected():
    with pytest.raises(ValueError, match="Expected 2"):
        VLLMMultiImageClient._validate_messages(messages([b"a"]), expected_images=2)
