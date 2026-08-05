"""Download and hash one exact protocol-v0.2 checkpoint without loading it."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path

from huggingface_hub import HfApi, snapshot_download


ALLOWED = {
    ("mPLUG/GUI-Owl-1.5-8B-Think", "afe3707fc84caebc4d7046118b34493ecf8bb060"),
    ("OpenGVLab/ScaleCUA-32B", "9a91c80690b34f2a962203c5ed896ef845b6149c"),
    ("MarsXL/UI-Voyager", "c262b85f18f1c669b19bca544e0ee2eb71225ff3"),
}


def file_sha256(path: Path) -> str:
    value = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-id", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    identity = (args.repo_id, args.revision)
    if identity not in ALLOWED:
        raise SystemExit(f"Checkpoint is not in frozen v0.2 allowlist: {identity}")

    info = HfApi().model_info(args.repo_id, revision=args.revision, files_metadata=True)
    if info.sha != args.revision:
        raise RuntimeError(f"Revision resolution drift: {info.sha}")
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    snapshot = Path(snapshot_download(repo_id=args.repo_id,
                                      revision=args.revision,
                                      cache_dir=args.cache_dir,
                                      max_workers=args.workers))
    if snapshot.name != args.revision:
        raise RuntimeError(f"Snapshot path revision drift: {snapshot}")

    records = []
    for path in sorted((item for item in snapshot.rglob("*") if item.is_file()),
                       key=lambda item: item.as_posix()):
        resolved = path.resolve(strict=True)
        records.append({
            "path": path.relative_to(snapshot).as_posix(),
            "bytes": resolved.stat().st_size,
            "sha256": file_sha256(resolved),
            "symlink": path.is_symlink(),
        })
    if not records:
        raise RuntimeError("Downloaded snapshot contains no files")
    license_paths = [row["path"] for row in records
                     if Path(row["path"]).name.casefold().startswith("license")]
    manifest = {
        "schema_version": "multi_framework_checkpoint.v0.2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "repo_id": args.repo_id,
        "revision": args.revision,
        "resolved_hub_sha": info.sha,
        "snapshot_path": str(snapshot),
        "file_count": len(records),
        "total_bytes": sum(row["bytes"] for row in records),
        "license_paths": license_paths,
        "files": records,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.manifest.with_suffix(args.manifest.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
    os.replace(temporary, args.manifest)
    print(json.dumps({key: manifest[key] for key in ("repo_id", "revision", "file_count", "total_bytes", "license_paths")}, sort_keys=True))


if __name__ == "__main__":
    main()
