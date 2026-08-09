"""Live GPU qualification for exact one-, two-, and three-image transport."""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
from typing import Any

from PIL import Image, ImageDraw
import requests
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.models.vllm_multi_image_client import VLLMMultiImageClient  # noqa: E402


BACKEND_ID = "qwen3_vl_32b_vllm_bf16_1xrtxpro6000_mobileuse_pf01_v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fixture(index: int) -> bytes:
    colors = ((196, 45, 52), (35, 139, 69), (37, 85, 191))
    image = Image.new("RGB", (336, 336), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((36, 36, 300, 300), fill=colors[index], outline="black", width=6)
    draw.rectangle((110, 110, 226, 226), fill="white", outline="black", width=4)
    draw.text((156, 155), str(index + 1), fill="black")
    buffer = BytesIO()
    image.save(buffer, format="PNG", compress_level=9)
    return buffer.getvalue()


def data_url(raw: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


def messages(raws: list[bytes]) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [{
        "type": "text",
        "text": (
            f"This is a transport qualification containing {len(raws)} image(s). "
            "Reply with only OK. Do not describe the images."
        ),
    }]
    for raw in raws:
        content.append({"type": "image_url", "image_url": {"url": data_url(raw)}})
    return [{"role": "user", "content": content}]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--request-timeout-seconds", type=float, default=3600.0)
    parser.add_argument(
        "--output", type=Path,
        default=REPOSITORY_ROOT / "evidence" / "public_framework" / "mobileuse" / "PF01_LIVE_MULTI_IMAGE_PREFLIGHT.json",
    )
    args = parser.parse_args()

    config_path = PROJECT_ROOT / "configs" / "mobileuse_multiagent_qwen3_vl_32b_hard_seed20260806.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    model = config["model"]
    if model["limit_mm_per_prompt"] != {"image": 3}:
        raise RuntimeError("Frozen server is not configured for three images")
    version_response = requests.get(
        args.url.rstrip("/") + "/version", timeout=30
    )
    version_response.raise_for_status()
    runtime_version = version_response.json().get("version")
    if runtime_version != model["vllm_version"]:
        raise RuntimeError(
            f"vLLM version drift: expected {model['vllm_version']}, got {runtime_version}"
        )
    client = VLLMMultiImageClient(
        args.url,
        model_id=model["id"], model_revision=model["revision"],
        backend_id=BACKEND_ID,
        temperature=model["temperature"], top_p=model["top_p"],
        top_k=model["top_k"], presence_penalty=model["presence_penalty"],
        repetition_penalty=model["repetition_penalty"],
        seed=int(config["generation_seed"]),
        timeout_seconds=args.request_timeout_seconds,
    )
    health = client.health()
    raws = [fixture(index) for index in range(3)]
    fixture_hashes = [sha256(raw).hexdigest() for raw in raws]
    calls = []
    roles = {1: "Operator", 2: "Reflector", 3: "GlobalReflector"}
    for count in (1, 2, 3):
        call = client.generate_messages(
            messages=messages(raws[:count]),
            episode_id="pf01_live_multi_image_preflight",
            call_label=f"transport_{count}_image",
            role=roles[count], expected_images=count,
            max_tokens=int(model["max_new_tokens"]),
        )
        observed = list(call.raven_meta["image_sha256"])
        if observed != fixture_hashes[:count]:
            raise RuntimeError(f"Image order/hash drift at count={count}")
        calls.append({
            "image_count": count,
            "role": roles[count],
            "image_sha256": observed,
            "request_sha256": call.request_sha256,
            "response_sha256": call.response_sha256,
            "response_length": len(call.content),
            "usage": call.usage,
            "latency_seconds": call.raven_meta["latency_seconds"],
            "transport_attempts": call.raven_meta["transport_attempts"],
        })
    report = {
        "schema": "raven_m.mobileuse.live_multi_image_preflight.v1",
        "status": "pass",
        "completed_at": utc_now(),
        "arm_id": config["arm_id"],
        "vllm_version": runtime_version,
        "health": health,
        "image_counts": [1, 2, 3],
        "fixture_sha256": fixture_hashes,
        "calls": calls,
        "emulator_mutations": 0,
        "scored_tasks": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
