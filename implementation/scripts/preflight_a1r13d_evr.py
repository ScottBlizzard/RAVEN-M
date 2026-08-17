#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "implementation/src")]
from raven_m.official_qwen_mobile import a1r13_contract as parent  # noqa: E402
from raven_m.official_qwen_mobile import a1r13d_contract as contract  # noqa: E402


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--implementation-commit")
    parser.add_argument("--validate-existing", action="store_true")
    args = parser.parse_args()
    if args.validate_existing:
        report = contract.validate_preflight_report()
        print(json.dumps({"status": report["status"]}, indent=2))
        return 0
    if not args.implementation_commit:
        parser.error("--implementation-commit is required")
    errors: list[str] = []
    checks: dict = {}
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    status = subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all"], text=True).splitlines()
    checks["git"] = {"head": head, "worktree_status": status}
    if head != args.implementation_commit:
        errors.append("implementation_commit_not_head")
    if status:
        errors.append("worktree_dirty")
    config = json.loads(contract.CONFIG_PATH.read_text(encoding="utf-8"))
    if config != contract.EXPECTED_CONFIG:
        errors.append("config_identity")
    replay = json.loads(parent.OFFLINE_REPLAY_PATH.read_text(encoding="utf-8"))
    checks["parent_replay"] = {"status": replay.get("status"), "content_sha256": replay.get("content_sha256"), "totals": replay.get("totals")}
    if not parent._replay_valid(replay):
        errors.append("parent_replay_invalid")
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(ROOT), str(ROOT / "implementation/src")]), PYTHONDONTWRITEBYTECODE="1")
    tests = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         "implementation/tests/official_qwen_mobile/test_a1r13_evidence_value_register.py",
         "implementation/tests/official_qwen_mobile/test_a1r13d_contract.py",
         "implementation/tests/official_qwen_mobile/test_a1r13d_controller_integration.py"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    checks["focused_tests"] = {"returncode": tests.returncode, "passed": tests.returncode == 0}
    checks["focused_tests_output_tail"] = (tests.stdout + tests.stderr)[-3000:]
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
        "experiment_id": contract.EXPERIMENT_ID,
        "implementation_commit": args.implementation_commit,
        "source_freeze_content_sha256": freeze.get("content_sha256"),
        "parent_replay_content_sha256": replay.get("content_sha256"),
        "checks": checks,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    report = {**payload, "content_sha256": contract.content_sha256(payload)}
    _write(contract.PREFLIGHT_PATH, report)
    print(json.dumps({"status": report["status"], "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
