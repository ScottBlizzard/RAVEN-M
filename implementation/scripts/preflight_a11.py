#!/usr/bin/env python3
"""Strict zero-generation preflight for the prospective A11 arm."""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))

from raven_m.official_qwen_mobile.a11_contract import (  # noqa: E402
    EXPERIMENT_ID, MECHANISM_ID, MODEL_ID, MODEL_REVISION, OFFICIAL_SYSTEM_PROMPT_SHA256,
    PARENT_EVIDENCE_COMMIT, PREFLIGHT_SCHEMA, CONFIG_PATH, current_source_freeze, json_sha256,
)
from raven_m.official_qwen_mobile.protocol import OFFICIAL_SYSTEM_PROMPT  # noqa: E402
from replay_a11_offline_traces import verify_and_replay  # noqa: E402


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--implementation-commit", required=True)
    parser.add_argument("--trace-root", type=Path, default=ROOT / "runs/a10_offline_replay_materialized")
    parser.add_argument("--tokenizer-path", type=Path, default=Path("/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope"))
    parser.add_argument("--allow-missing-tokenizer-for-local-review", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/a11/A11_ZERO_GENERATION_PREFLIGHT.json")
    args = parser.parse_args()
    errors: list[str] = []
    checks: dict[str, Any] = {}
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    if head != args.implementation_commit:
        errors.append("implementation_commit_not_current_head")
    if subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", PARENT_EVIDENCE_COMMIT, args.implementation_commit], check=False).returncode:
        errors.append("parent_not_ancestor")
    status = subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all"], text=True).splitlines()
    checks["worktree_status"] = status
    if status:
        errors.append("worktree_dirty")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if config.get("schema") != "a11_crc_ecobf_arm_v1" or config.get("experiment_id") != EXPERIMENT_ID or config.get("mechanism_id") != MECHANISM_ID:
        errors.append("config_identity_drift")
    model = config.get("model") or {}
    if model.get("id") != MODEL_ID or model.get("revision") != MODEL_REVISION or model.get("generation_seed") != 3407:
        errors.append("model_identity_drift")
    if sha256(OFFICIAL_SYSTEM_PROMPT.encode()).hexdigest() != OFFICIAL_SYSTEM_PROMPT_SHA256:
        errors.append("system_prompt_drift")
    replay = verify_and_replay(args.trace_root.resolve())
    checks["real_offline_replay"] = {key: value for key, value in replay.items() if key != "episodes"}
    if replay.get("status") != "pass" or replay.get("generation_calls") != 0:
        errors.append("real_offline_replay_failed")
    core = ROOT / "implementation/src/raven_m/official_qwen_mobile/a11_confirmed_route_contraction.py"
    tree = ast.parse(core.read_text(encoding="utf-8"))
    imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imports |= {str(node.module).split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    if imports & {"requests", "urllib", "httpx", "openai", "transformers", "vllm", "socket"}:
        errors.append("banned_core_import")
    env = dict(os.environ, PYTHONPATH=str(ROOT / "implementation/src"), PYTHONDONTWRITEBYTECODE="1")
    tests = subprocess.run([sys.executable, "-m", "pytest", "implementation/tests/official_qwen_mobile", "-q", "-p", "no:cacheprovider"], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    checks["tests"] = {"returncode": tests.returncode, "stdout": tests.stdout[-2000:], "stderr": tests.stderr[-1000:]}
    if tests.returncode:
        errors.append("tests_failed")
    if not args.tokenizer_path.is_dir():
        checks["tokenizer"] = {"status": "missing_local_review_only" if args.allow_missing_tokenizer_for_local_review else "missing", "path": str(args.tokenizer_path)}
        errors.append("frozen_tokenizer_missing")
    else:
        try:
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(str(args.tokenizer_path), local_files_only=True, trust_remote_code=True)
            maximum = len(tokenizer.encode('Open: "zucchini in directions". Evidence: confirmed repeated route contraction; reassess another branch.', add_special_tokens=False))
            checks["tokenizer"] = {"status": "pass", "max_added_tokens_per_read": maximum}
            if maximum > 192:
                errors.append("tokenizer_budget_exceeded")
        except Exception as exc:
            errors.append(f"tokenizer_check_failed:{type(exc).__name__}")
    try:
        freeze = current_source_freeze()
    except Exception as exc:
        freeze = {}
        errors.append(f"source_freeze_failed:{type(exc).__name__}:{exc}")
    report = {"schema": PREFLIGHT_SCHEMA, "status": "pass" if not errors else "fail", "generation_calls": 0, "created_at": datetime.now(timezone.utc).isoformat(), "parent_evidence_commit": PARENT_EVIDENCE_COMMIT, "a11_implementation_commit": args.implementation_commit, "mechanism_id": MECHANISM_ID, "experiment_id": EXPERIMENT_ID, "source_freeze": freeze, "source_freeze_sha256": json_sha256(freeze), "checks": checks, "errors": errors}
    _atomic(args.output, report)
    print(json.dumps({"status": report["status"], "output": str(args.output), "sha256": _sha(args.output), "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
