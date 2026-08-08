"""Select exact task/seed records from an audited suite summary.

This utility never edits the source summary.  It exists for interrupted suites
where only a frozen subset is scientifically usable and unfinished or
infrastructure-contaminated siblings must not leak into a later merge.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _parse_key(value: str) -> tuple[str, int]:
    try:
        task, raw_seed = value.rsplit(":", 1)
        return task, int(raw_seed)
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError(
            "key must be TASK_CLASS:INTEGER_SEED"
        ) from exc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--key", type=_parse_key, action="append", required=True)
    parser.add_argument("--selection-reason", required=True)
    args = parser.parse_args()

    payload = json.loads(args.source.read_text(encoding="utf-8"))
    requested = set(args.key)
    selected = [
        item
        for item in payload.get("episodes", [])
        if (str(item.get("task_name")), int(item.get("seed"))) in requested
    ]
    found = {(str(item["task_name"]), int(item["seed"])) for item in selected}
    if found != requested:
        raise SystemExit(
            f"selection mismatch: requested={sorted(requested)}, found={sorted(found)}"
        )
    if len(selected) != len(requested):
        raise SystemExit("source contains duplicate selected task/seed keys")

    result = {
        "suite_dir": f"SELECTED:{args.source.resolve()}",
        "source_summary": str(args.source.resolve()),
        "selection_reason": args.selection_reason,
        "selected_keys": [f"{task}:{seed}" for task, seed in sorted(requested)],
        "complete": True,
        "completed_episode_count": len(selected),
        "scientifically_eligible_episode_count": len(selected),
        "excluded_episode_count": 0,
        "in_progress_episode_ids": [],
        "episodes": selected,
    }
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
