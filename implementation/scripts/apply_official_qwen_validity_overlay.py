"""Create a non-destructive derived summary with eligibility overrides."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_summary", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--exclude-episode-id", action="append", default=[])
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()

    payload: dict[str, Any] = json.loads(
        args.source_summary.read_text(encoding="utf-8")
    )
    requested = set(args.exclude_episode_id)
    found: set[str] = set()
    episodes: list[dict[str, Any]] = []
    for raw in payload.get("episodes", []):
        item = dict(raw)
        episode_id = str(item.get("episode_id"))
        if episode_id in requested:
            if not item.get("scientifically_eligible", False):
                raise SystemExit(f"episode already excluded: {episode_id}")
            item["scientifically_eligible"] = False
            item["eligibility_reason"] = args.reason
            found.add(episode_id)
        episodes.append(item)
    if found != requested:
        raise SystemExit(
            f"episode id mismatch: requested={sorted(requested)}, found={sorted(found)}"
        )
    output = dict(payload)
    output["episodes"] = episodes
    output["validity_overlay"] = {
        "source_summary": str(args.source_summary.resolve()),
        "excluded_episode_ids": sorted(found),
        "reason": args.reason,
        "source_results_modified": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output["validity_overlay"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
