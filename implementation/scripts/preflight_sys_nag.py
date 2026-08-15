#!/usr/bin/env python3
"""Strict zero-generation preflight for SYS-NAG."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "implementation/src")]

from implementation.scripts.replay_sys_nag import replay  # noqa: E402
from raven_m.official_qwen_mobile import sys_nag_contract as contract  # noqa: E402
from raven_m.official_qwen_mobile.numeric_answer_guard import (  # noqa: E402
    NumericAnswerConsistencyGuard,
)


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--implementation-commit")
    parser.add_argument("--validate-existing", action="store_true")
    parser.add_argument("--output", type=Path, default=contract.PREFLIGHT_PATH)
    args = parser.parse_args()
    if args.validate_existing:
        report = contract.validate_preflight_report(args.output)
        print(json.dumps({"status": report["status"], "output": str(args.output)}, indent=2))
        return 0
    if not args.implementation_commit:
        parser.error("--implementation-commit is required")

    errors: list[str] = []
    checks: dict = {}
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    status = subprocess.check_output(
        ["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all"],
        text=True,
    ).splitlines()
    checks["git"] = {"head": head, "worktree_status": status}
    if head != args.implementation_commit:
        errors.append("implementation_commit_not_head")
    if status:
        errors.append("worktree_dirty")

    config = json.loads(contract.CONFIG_PATH.read_text(encoding="utf-8"))
    if (
        config.get("schema") != contract.CONFIG_SCHEMA
        or config.get("mechanism_id") != contract.MECHANISM_ID
        or config.get("experiment_id") != contract.EXPERIMENT_ID
        or config.get("system_id") != contract.SYSTEM_ID
    ):
        errors.append("config_identity")

    replay_now = replay()
    replay_file = json.loads(contract.OFFLINE_REPLAY_PATH.read_text(encoding="utf-8"))
    checks["offline_replay"] = {
        "status": replay_now["status"],
        "totals": replay_now["totals"],
        "v2_failure_regression": replay_now["v2_failure_regression"],
    }
    if replay_now != replay_file or replay_now["status"] != "PASS":
        errors.append("offline_replay_drift")

    guard = NumericAnswerConsistencyGuard()
    timings = []
    for _ in range(1000):
        started = time.perf_counter()
        corrected, event = guard.review(
            proposed_action={"type": "answer", "text": "165"},
            action_summary="Calculate total duration: 1 hour 45 minutes and 1 hour 15 minutes.",
        )
        timings.append((time.perf_counter() - started) * 1000)
        if corrected != {"type": "answer", "text": "180"} or not event["overridden"]:
            errors.append("runtime_canary_semantics")
            break
    timings.sort()
    checks["runtime_canary_ms"] = {"p99": timings[989], "maximum": timings[-1]}
    if timings[989] >= 2 or timings[-1] >= 10:
        errors.append("runtime_canary_cost")

    env = dict(
        os.environ,
        PYTHONPATH=os.pathsep.join([str(ROOT), str(ROOT / "implementation/src")]),
        PYTHONDONTWRITEBYTECODE="1",
    )
    tests = subprocess.run(
        [
            sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
            "implementation/tests/official_qwen_mobile/test_numeric_answer_guard.py",
            "implementation/tests/official_qwen_mobile/test_sys_nag_contract.py",
            "implementation/tests/official_qwen_mobile/test_sys_nag_controller_integration.py",
        ],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    checks["focused_tests"] = {
        "returncode": tests.returncode,
        "stdout_tail": tests.stdout[-2000:],
        "stderr_tail": tests.stderr[-1000:],
    }
    if tests.returncode:
        errors.append("focused_tests_failed")

    try:
        freeze = contract.source_freeze_payload(args.implementation_commit)
    except Exception as exc:
        freeze = {}
        errors.append(f"source_freeze:{type(exc).__name__}:{exc}")
    if freeze:
        _write(contract.SOURCE_FREEZE_PATH, freeze)
    payload = {
        "schema": contract.PREFLIGHT_SCHEMA,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "generation_calls": 0,
        "live_generation_authorized": not errors,
        "mechanism_id": contract.MECHANISM_ID,
        "system_id": contract.SYSTEM_ID,
        "experiment_id": contract.EXPERIMENT_ID,
        "implementation_commit": args.implementation_commit,
        "source_freeze_content_sha256": freeze.get("content_sha256"),
        "offline_replay_content_sha256": replay_file.get("content_sha256"),
        "checks": checks,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    report = {**payload, "content_sha256": contract.content_sha256(payload)}
    _write(args.output, report)
    print(json.dumps({"status": report["status"], "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
