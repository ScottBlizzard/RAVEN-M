#!/usr/bin/env python3
"""Create the zero-generation A7 continuation plan from frozen parent evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "implementation/src"))

from raven_m.multi_framework_benchmark.task_instances import load_frozen_instances  # noqa: E402
from raven_m.official_qwen_mobile.a7_continuation import build_plan  # noqa: E402


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-suite-dir", type=Path, required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=REPOSITORY_ROOT / "implementation/configs/androidworld_hard_v2_instances.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "evidence/a678/A7_GATED_CONTINUATION_PLAN.json",
    )
    args = parser.parse_args()
    specs = [
        item
        for item in load_frozen_instances(args.manifest.resolve())
        if int(item["task_seed"]) == 20260806
    ]
    plan = build_plan(
        parent_suite_dir=args.parent_suite_dir.resolve(),
        canonical_specs=specs,
        manifest_path=args.manifest.resolve(),
    )
    _atomic_json(args.output.resolve(), plan)
    print(json.dumps(plan, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
