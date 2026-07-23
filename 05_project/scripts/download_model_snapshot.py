"""Download the exact model revision into an explicitly selected cache."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from huggingface_hub import snapshot_download


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()

    args.cache_dir.mkdir(parents=True, exist_ok=True)
    snapshot = Path(
        snapshot_download(
            repo_id=MODEL_ID,
            revision=MODEL_REVISION,
            cache_dir=args.cache_dir,
            max_workers=args.workers,
        )
    )
    files = []
    for path in sorted(snapshot.rglob("*")):
        if path.is_file():
            files.append(
                {
                    "path": path.relative_to(snapshot).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path.read_bytes()).hexdigest()
                    if path.stat().st_size < 32 * 1024 * 1024
                    else None,
                }
            )
    manifest = {
        "model_id": MODEL_ID,
        "revision": MODEL_REVISION,
        "snapshot_path": str(snapshot),
        "files": files,
        "total_bytes": sum(item["bytes"] for item in files),
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
