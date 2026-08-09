"""Validate hash-chained logs and aggregate a completed PF01 suite."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.public_frameworks.mobileuse.logging import LayeredEventLog  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("suite_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    aggregate = json.loads((args.suite_dir / "aggregate.json").read_text(encoding="utf-8"))
    errors = []
    role_calls: Counter[str] = Counter()
    level_counts: Counter[str] = Counter()
    false_success = 0
    for summary in aggregate["episodes"]:
        path = Path(summary["events_path"])
        errors.extend(f"{summary['episode_id']}:{item}" for item in LayeredEventLog.validate(path))
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        for record in records:
            level_counts[record["level"]] += 1
            if record["event"] == "model_request":
                role_calls[record["role"]] += 1
        claimed = summary.get("controller_status") == "FINISHED"
        false_success += int(claimed and not summary["success"])
    report = {
        "schema": "raven_m.mobileuse.arm_validation.v1",
        "suite_dir": str(args.suite_dir),
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "episode_count": aggregate["episode_count"],
        "success_count": aggregate["success_count"],
        "total_reward": aggregate["total_reward"],
        "false_success_count": false_success,
        "role_model_calls": dict(sorted(role_calls.items())),
        "layer_event_counts": dict(sorted(level_counts.items())),
    }
    output = args.output or args.suite_dir / "validation.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
