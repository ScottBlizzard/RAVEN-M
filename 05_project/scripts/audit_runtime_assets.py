"""Create a deterministic manifest for benchmark runtime assets."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
RUNTIME_ROOT = REPOSITORY_ROOT / "06_local_runtime"
DEFAULT_OUTPUT = PROJECT_ROOT / "metadata" / "runtime_asset_manifest.json"


def file_record(path: Path) -> dict[str, object]:
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return {
        "path": path.relative_to(REPOSITORY_ROOT).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    app_data = RUNTIME_ROOT / "cache" / "android_world" / "app_data"
    accessibility_apk = (
        RUNTIME_ROOT
        / "cache"
        / "android_env"
        / "2024.05.13-accessibility_forwarder.apk"
    )
    assets = sorted(
        [
            *app_data.glob("*.apk"),
            *app_data.glob("*.obf"),
            accessibility_apk,
        ],
        key=lambda item: item.as_posix().lower(),
    )
    missing = [str(path) for path in assets if not path.is_file()]
    if missing or not assets:
        raise FileNotFoundError(
            "Runtime asset set is incomplete: " + ", ".join(missing)
        )

    records = [file_record(path) for path in assets]
    canonical_records = json.dumps(
        records,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "asset_count": len(records),
        "total_size_bytes": sum(int(record["size_bytes"]) for record in records),
        "records_sha256": sha256(canonical_records).hexdigest(),
        "assets": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
