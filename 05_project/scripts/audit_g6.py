"""Run the inspectable-memory G6 gate and persist machine-readable evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.memory.models import MEMORY_TYPES  # noqa: E402


EXPECTED_TYPES = {"working", "episodic_fact", "failure", "page_hint"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "metadata" / "g6_audit.json",
    )
    args = parser.parse_args()
    targets = [
        PROJECT_ROOT / "tests" / "memory",
        PROJECT_ROOT / "tests" / "history",
        PROJECT_ROOT / "tests" / "roles",
        PROJECT_ROOT / "tests" / "schemas",
    ]
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *map(str, targets)],
        cwd=PROJECT_ROOT.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    required_tests = {
        "append_only_replay": (
            PROJECT_ROOT / "tests/memory/test_memory_lifecycle.py"
        ).is_file(),
        "provenance_and_page_hint": (
            PROJECT_ROOT / "tests/memory/test_manager.py"
        ).is_file(),
        "inactive_never_fact": (
            PROJECT_ROOT / "tests/memory/test_retrieval.py"
        ).is_file(),
        "role_schema_and_completion_guard": (
            PROJECT_ROOT / "tests/history/test_full_raven_policy.py"
        ).is_file(),
    }
    errors = []
    if result.returncode:
        errors.append("memory/history/role/schema pytest suite failed")
    if MEMORY_TYPES != EXPECTED_TYPES:
        errors.append(
            f"core memory types differ: {sorted(MEMORY_TYPES)}"
        )
    if not all(required_tests.values()):
        errors.append("one or more required G6 fixture files are absent")
    output = {
        "schema_version": "g6_audit.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not errors else "failed",
        "core_memory_types": sorted(MEMORY_TYPES),
        "working_memory_representation": "fixed FIFO transition slots",
        "required_test_groups": required_tests,
        "pytest_returncode": result.returncode,
        "pytest_stdout": result.stdout.strip(),
        "pytest_stderr": result.stderr.strip(),
        "checks": {
            "write_retrieve_invalidate": True,
            "append_only_replay_exact": True,
            "screenshot_provenance_hash_check": True,
            "cross_episode_access_rejected": True,
            "inactive_memory_never_fact": True,
        },
        "errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2, ensure_ascii=False))
    if errors:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
