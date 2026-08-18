#!/usr/bin/env python3
"""Zero-generation preflight for stabilized SYS-R2-LRER V2."""

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

from implementation.scripts.replay_sys_r2_lrer_v2 import replay  # noqa: E402
from raven_m.official_qwen_mobile import sys_r2_lrer_v2_contract as contract  # noqa: E402
from raven_m.official_qwen_mobile.sys_trrc_token_budget import (  # noqa: E402
    SubprocessExactQwenMultimodalTokenProjector,
    SubprocessExactQwenTextDeltaCounter,
)


FOCUSED_TESTS = (
    "implementation/tests/official_qwen_mobile/test_r15_derived_evidence_consolidation.py",
    "implementation/tests/official_qwen_mobile/test_sys_r2_lrer_v2_contract.py",
    "implementation/tests/official_qwen_mobile/test_sys_r2_lrer_v2_controller_integration.py",
    "implementation/tests/official_qwen_mobile/test_sys_r2_lrer_v2_offline_replay.py",
)


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--implementation-commit")
    parser.add_argument("--validate-existing", action="store_true")
    parser.add_argument("--processor-python", type=Path)
    parser.add_argument("--processor-path", type=Path)
    args = parser.parse_args()
    if args.validate_existing:
        projector = None
        if args.processor_python is not None or args.processor_path is not None:
            if args.processor_python is None or args.processor_path is None:
                parser.error("--processor-python and --processor-path must be supplied together")
            projector = SubprocessExactQwenMultimodalTokenProjector(
                args.processor_python,
                args.processor_path,
                expected_revision=contract.MODEL_REVISION,
            )
        report = contract.validate_preflight_report(projector=projector)
        print(json.dumps({"status": report["status"]}, indent=2))
        return 0
    if not args.implementation_commit:
        parser.error("--implementation-commit is required")
    if args.processor_python is None or args.processor_path is None:
        parser.error("preflight generation requires --processor-python and --processor-path")

    projector = SubprocessExactQwenMultimodalTokenProjector(
        args.processor_python,
        args.processor_path,
        expected_revision=contract.MODEL_REVISION,
    )
    text_delta_counter = SubprocessExactQwenTextDeltaCounter(projector)

    errors: list[str] = []
    checks: dict = {}
    head = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    status = subprocess.check_output(
        [
            "git",
            "-C",
            str(ROOT),
            "status",
            "--porcelain",
            "--untracked-files=all",
        ],
        text=True,
    ).splitlines()
    checks["git"] = {"head": head, "worktree_status": status}
    if head != args.implementation_commit:
        errors.append("implementation_commit_not_head")
    if status:
        errors.append("worktree_dirty")
    if json.loads(contract.CONFIG_PATH.read_text(encoding="utf-8")) != contract.EXPECTED_CONFIG:
        errors.append("config_identity")

    replay_now = replay(contract.REPLAY_FIXTURE_PATH)
    replay_file = json.loads(contract.OFFLINE_REPLAY_PATH.read_text(encoding="utf-8"))
    checks["offline_replay"] = {
        "status": replay_now.get("status"),
        "content_sha256": replay_now.get("content_sha256"),
        "development_live_browser": replay_now.get("development_live_browser"),
    }
    checks["local_processor_identity"] = contract.local_processor_identity(projector)
    base_text = "SYS-R2-LRER-V2 base prompt"
    final_text = base_text + "\nLRER evidence"
    checks["exact_text_delta_smoke"] = {
        "base_text_sha256": contract.canonical_sha256(base_text),
        "final_text_sha256": contract.canonical_sha256(final_text),
        "exact_delta_tokens": int(text_delta_counter(base_text, final_text)),
    }
    if replay_now != replay_file or not contract._replay_valid(replay_now):
        errors.append("offline_replay_drift")

    environment = dict(
        os.environ,
        PYTHONPATH=os.pathsep.join([str(ROOT), str(ROOT / "implementation/src")]),
        PYTHONDONTWRITEBYTECODE="1",
    )
    tests = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *FOCUSED_TESTS],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )
    checks["focused_tests"] = {
        "returncode": tests.returncode,
        "passed": tests.returncode == 0,
    }
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

    fixture = json.loads(contract.REPLAY_FIXTURE_PATH.read_text(encoding="utf-8"))
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
        "fixture_content_sha256": fixture.get("content_sha256"),
        "checks": checks,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    report = {**payload, "content_sha256": contract.content_sha256(payload)}
    _write(contract.PREFLIGHT_PATH, report)
    print(json.dumps({"status": report["status"], "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
