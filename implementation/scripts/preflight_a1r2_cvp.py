#!/usr/bin/env python3
"""Strict zero-generation preflight for A1-R2 CVP."""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))
sys.path.insert(0, str(ROOT / "implementation/scripts"))

from raven_m.official_qwen_mobile import a1r2_contract as contract  # noqa: E402
from raven_m.official_qwen_mobile.a1r2_compact_verified_pending import (  # noqa: E402
    CompactVerifiedPendingMemory,
)
from raven_m.official_qwen_mobile.protocol import A1_WORKING_MEMORY_SYSTEM_PROMPT  # noqa: E402
from replay_a1r2_compact_verified_pending import replay  # noqa: E402


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")
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
        parser.error("--implementation-commit is required when generating preflight")
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
    if config.get("schema") != contract.CONFIG_SCHEMA or config.get("mechanism_id") != contract.MECHANISM_ID or config.get("experiment_id") != contract.EXPERIMENT_ID:
        errors.append("config_identity")
    from hashlib import sha256
    prompt_sha = sha256(A1_WORKING_MEMORY_SYSTEM_PROMPT.encode()).hexdigest()
    checks["a1_system_prompt_sha256"] = prompt_sha
    if prompt_sha != "653f727961a97d04176d3ddb9b1098355fe1fe8783473c2abc74967798f4a5b8":
        errors.append("a1_prompt_drift")
    trace_root = ROOT / "runs/a1_working_memory/official_qwen_20260810T122419_26573d7c/episodes"
    replay_now = replay(trace_root)
    replay_file = json.loads(contract.OFFLINE_REPLAY_PATH.read_text(encoding="utf-8"))
    checks["offline_replay"] = {"status": replay_now["status"], "content_sha256": replay_now["content_sha256"]}
    replay_projection = dict(replay_now)
    replay_projection["created_at"] = replay_file.get("created_at")
    replay_projection["content_sha256"] = replay_file.get("content_sha256")
    if replay_now["status"] != "PASS" or any(replay_now.get(key) != replay_file.get(key) for key in ("schema", "status", "errors", "generation_calls", "mechanism_id", "source", "totals", "sentinel_tasks", "episodes")):
        errors.append("offline_replay_drift")
    core = ROOT / "implementation/src/raven_m/official_qwen_mobile/a1r2_compact_verified_pending.py"
    tree = ast.parse(core.read_text(encoding="utf-8"))
    imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imports |= {str(node.module).split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    banned = sorted(imports & {"requests", "urllib", "httpx", "openai", "transformers", "vllm", "socket"})
    checks["banned_core_imports"] = banned
    if banned:
        errors.append("banned_core_import")
    samples: list[float] = []
    for _ in range(1000):
        memory = CompactVerifiedPendingMemory()
        start = time.perf_counter()
        memory.write(source_step=0, action_summary="MEMORY[observed=x; verified=A deleted; pending=delete B] | Tap B.", source_call_id="x", source_response_sha256="x", source_screenshot_sha256="x")
        text, audit = memory.read({})
        memory.commit_injection(audit["ticket_id"], "x")
        assert text
        samples.append((time.perf_counter() - start) * 1000)
    samples.sort()
    checks["runtime_canary_ms"] = {"p99": samples[989], "maximum": samples[-1]}
    if samples[989] >= 2 or samples[-1] >= 10:
        errors.append("runtime_canary")
    env = dict(os.environ, PYTHONPATH=str(ROOT / "implementation/src"), PYTHONDONTWRITEBYTECODE="1")
    tests = subprocess.run([sys.executable, "-m", "pytest", "implementation/tests/official_qwen_mobile", "-q", "-p", "no:cacheprovider"], cwd=ROOT, env=env, capture_output=True, text=True)
    checks["tests"] = {"returncode": tests.returncode, "stdout_tail": tests.stdout[-1500:], "stderr_tail": tests.stderr[-800:]}
    if tests.returncode:
        errors.append("tests_failed")
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
        "offline_replay_file_sha256": contract.file_sha256(contract.OFFLINE_REPLAY_PATH),
        "checks": checks,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    report = {**payload, "content_sha256": contract.content_sha256(payload)}
    _write(args.output, report)
    print(json.dumps({"status": report["status"], "output": str(args.output), "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
