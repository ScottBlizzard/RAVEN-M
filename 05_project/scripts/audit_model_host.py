"""Write a credential-free model-host environment snapshot."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
from urllib.request import urlopen


PACKAGES = (
    "torch",
    "transformers",
    "accelerate",
    "qwen-vl-utils",
    "huggingface-hub",
    "fastapi",
    "uvicorn",
)


def _command(*args: str) -> str | None:
    try:
        return subprocess.run(
            args,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--service-url", default="http://127.0.0.1:8000/health")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    disk = shutil.disk_usage(project_root)
    package_versions = {}
    for package in PACKAGES:
        try:
            package_versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            package_versions[package] = None

    try:
        import torch

        torch_state = {
            "cuda_available": torch.cuda.is_available(),
            "cuda_runtime": torch.version.cuda,
            "cudnn": torch.backends.cudnn.version(),
            "visible_device_count": torch.cuda.device_count(),
            "visible_devices": [
                {
                    "index": index,
                    "name": torch.cuda.get_device_name(index),
                    "total_memory_bytes": torch.cuda.get_device_properties(
                        index
                    ).total_memory,
                }
                for index in range(torch.cuda.device_count())
            ],
        }
    except Exception as exc:
        torch_state = {"error": f"{type(exc).__name__}: {exc}"}

    try:
        with urlopen(args.service_url, timeout=5) as response:
            service_health = json.load(response)
    except Exception as exc:
        service_health = {"error": f"{type(exc).__name__}: {exc}"}

    tracked_files = {}
    for relative in (
        "configs/backend/qwen3_vl_32b_transformers.yaml",
        "requirements/model_server_overlay.txt",
        "src/raven_m/models/server.py",
        "scripts/launch_model_server.sh",
    ):
        path = project_root / "05_project" / relative
        if path.is_file():
            tracked_files[relative] = _sha256(path)

    record = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "project_root": str(project_root),
        "model_cache": str(project_root / "05_project/model_cache/huggingface"),
        "disk": {
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
        },
        "packages": package_versions,
        "torch": torch_state,
        "nvidia_smi": _command(
            "nvidia-smi",
            "--query-gpu=index,name,memory.total,driver_version",
            "--format=csv,noheader",
        ),
        "service_health": service_health,
        "tracked_file_sha256": tracked_files,
        "model_snapshot_manifest_present": (
            project_root
            / "05_project/metadata/model_snapshot_manifest.json"
        ).is_file(),
        "environment": {
            "CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "RAVEN_MODEL_MODE": os.environ.get("RAVEN_MODEL_MODE"),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(record, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
