#!/usr/bin/env python3
"""Strict zero-generation qualification for A10 ECOBF."""

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

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))

from raven_m.official_qwen_mobile.a10_contract import (  # noqa: E402
    CONFIG_PATH,
    EXPERIMENT_ID,
    GENERATION_SEED,
    MECHANISM_ID,
    MODEL_ID,
    MODEL_REVISION,
    OFFICIAL_SYSTEM_PROMPT_SHA256,
    PARENT_EVIDENCE_COMMIT,
    TASK_COUNT,
    TASK_SEED,
    current_source_freeze,
    json_sha256,
)
from raven_m.official_qwen_mobile.a10_obligation_branch_frontier import (  # noqa: E402
    EvidenceCalibratedObligationBranchFrontierMemory,
)
from raven_m.official_qwen_mobile.protocol import OFFICIAL_SYSTEM_PROMPT  # noqa: E402
from replay_a10_offline_traces import verify_and_replay  # noqa: E402


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def check_identity(errors: list[str], checks: dict[str, Any], implementation_commit: str) -> None:
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    checks["repository_head"] = head
    if head != implementation_commit:
        errors.append("implementation_commit_not_current_head")
    ancestry = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "merge-base",
            "--is-ancestor",
            PARENT_EVIDENCE_COMMIT,
            implementation_commit,
        ],
        check=False,
    )
    checks["parent_evidence_is_ancestor"] = ancestry.returncode == 0
    if ancestry.returncode != 0:
        errors.append("parent_evidence_commit_not_ancestor")
    porcelain = subprocess.check_output(
        ["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all"],
        text=True,
    ).splitlines()
    checks["worktree_clean"] = not porcelain
    checks["worktree_status"] = porcelain
    if porcelain:
        errors.append("worktree_dirty_staged_unstaged_or_untracked")
    if sha256(OFFICIAL_SYSTEM_PROMPT.encode()).hexdigest() != OFFICIAL_SYSTEM_PROMPT_SHA256:
        errors.append("official_system_prompt_hash_drift")


def check_config(errors: list[str], checks: dict[str, Any]) -> None:
    config = load(CONFIG_PATH)
    checks["config_sha256"] = file_sha(CONFIG_PATH)
    if config.get("schema") != "a10_ecobf_arm_v1" or config.get("experiment_id") != EXPERIMENT_ID or config.get("mechanism_id") != MECHANISM_ID:
        errors.append("config_identity_drift")
    model = config.get("model") or {}
    expected_model = {"id": MODEL_ID, "revision": MODEL_REVISION, "generation_seed": GENERATION_SEED, "temperature": .7, "top_p": .8, "top_k": 20, "presence_penalty": 1.5, "repetition_penalty": 1.0, "max_tokens": 32768}
    if any(model.get(key) != value for key, value in expected_model.items()):
        errors.append("model_or_sampling_drift")
    benchmark = config.get("benchmark") or {}
    if benchmark.get("task_seed") != TASK_SEED or benchmark.get("task_count") != TASK_COUNT:
        errors.append("benchmark_drift")
    boundary = config.get("intervention") or {}
    expected_boundary = {"extra_model_calls": 0, "guard": False, "action_override": False, "forced_termination": False, "evaluator_input": False, "hidden_ui_input": False, "future_input": False, "system_prompt": "exact OFFICIAL_SYSTEM_PROMPT"}
    if any(boundary.get(key) != value for key, value in expected_boundary.items()):
        errors.append("causal_boundary_drift")


def check_task_and_trace_manifests(errors: list[str], checks: dict[str, Any]) -> None:
    manifest = load(ROOT / "implementation/configs/androidworld_hard_v2_instances.json")
    instances = [item for item in manifest.get("instances") or [] if item.get("task_seed") == TASK_SEED]
    if len(instances) != TASK_COUNT or len({item.get("task_class") for item in instances}) != TASK_COUNT:
        errors.append("hard_manifest_seed_not_19_unique")
    if any(not item.get("native_max_steps") for item in instances):
        errors.append("native_max_steps_missing")
    trace_manifest_path = ROOT / "evidence/a10/A10_OFFLINE_TRACE_MANIFEST.json"
    trace_manifest = load(trace_manifest_path)
    records = trace_manifest.get("records") or []
    roles = {str(item.get("role")) for item in records}
    expected_roles = {"a0", "a1_recipe", "a6", "a8v2_expense", "a9_retro"}
    checks["offline_trace_manifest_sha256"] = file_sha(trace_manifest_path)
    checks["offline_trace_episode_count"] = len(records)
    if (
        trace_manifest.get("schema") != "a10_offline_trace_manifest_v1"
        or trace_manifest.get("generation_calls") != 0
        or len(records) != 27
        or roles != expected_roles
    ):
        errors.append("offline_trace_manifest_invalid")


def check_real_offline_replay(
    errors: list[str], checks: dict[str, Any], trace_root: Path
) -> None:
    report = verify_and_replay(trace_root.resolve())
    checks["real_offline_replay"] = report
    if report.get("status") != "pass" or report.get("generation_calls") != 0:
        errors.append("real_offline_trace_replay_failed")


def check_ast_and_runtime(errors: list[str], checks: dict[str, Any]) -> None:
    module_path = ROOT / "implementation/src/raven_m/official_qwen_mobile/a10_obligation_branch_frontier.py"
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    banned = {"requests", "urllib", "httpx", "openai", "transformers", "vllm", "socket"}
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    checks["a10_import_roots"] = sorted(imports)
    if imports & banned:
        errors.append(f"a10_banned_imports:{sorted(imports & banned)}")
    pixels = np.zeros((96, 64, 3), dtype=np.uint8)
    goal = "Delete the following: Bike Repairs, Tuition Fees"
    memory = EvidenceCalibratedObligationBranchFrontierMemory()
    assert memory.read({"goal": goal, "before": {"pixels": pixels, "evaluator_reward": 1}})[0] == ""
    for step in range(2):
        memory.observe_step(source_step=step, action_summary="Tap the lower-middle delete control", canonical_action={"type": "tap", "x": .5, "y": .6}, before={"pixels": pixels, "ui_tree": "ignored"}, after={"pixels": pixels, "task_success": True})
        rendered, _ = memory.read({"goal": goal, "before": {"pixels": pixels, "database_state": "ignored"}})
    audit = memory.audit_record()
    if not rendered or audit["model_calls_added"] != 0 or audit["guard_enabled"] or audit["action_override_count"] or audit["forced_termination_count"]:
        errors.append("runtime_causal_canary_failed")
    if len(rendered) > 420 or len(rendered.encode()) > 720 or audit["capacity"]["serialized_audit_bytes"] > 131072:
        errors.append("runtime_capacity_canary_failed")
    checks["runtime_canary"] = {"triggered": bool(rendered), "rendered_chars": len(rendered), "rendered_utf8_bytes": len(rendered.encode()), "audit_bytes": audit["capacity"]["serialized_audit_bytes"]}


def run_tests(errors: list[str], checks: dict[str, Any]) -> None:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(ROOT / "implementation/src")
    result = subprocess.run([sys.executable, "-m", "pytest", "implementation/tests/official_qwen_mobile/test_a10_obligation_branch_frontier.py", "implementation/tests/official_qwen_mobile/test_a10_controller_integration.py", "implementation/tests/official_qwen_mobile/test_a10_contract.py", "implementation/tests/official_qwen_mobile/test_a10_offline_replay.py", "-q", "-p", "no:cacheprovider"], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    checks["tests"] = {"returncode": result.returncode, "stdout": result.stdout[-4000:], "stderr": result.stderr[-2000:]}
    if result.returncode:
        errors.append("a10_tests_failed")


def check_tokenizer(errors: list[str], checks: dict[str, Any], tokenizer_path: Path, allow_missing: bool) -> None:
    query_set = load(ROOT / "evidence/a10/A10_FROZEN_QUERY_SET.json")
    if query_set.get("task_count") != 19:
        errors.append("frozen_query_set_invalid")
        return
    if not tokenizer_path.is_dir():
        checks["tokenizer"] = {
            "status": "missing_local_review_only" if allow_missing else "missing",
            "path": str(tokenizer_path),
        }
        # The flag makes local diagnosis explicit; it never converts a missing
        # frozen tokenizer into a formal pass.
        errors.append("frozen_tokenizer_missing")
        return
    try:
        from transformers import AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_path), local_files_only=True, trust_remote_code=True)
        suffix = "Retry only if pixels/open items changed; otherwise reassess a different action family or target. Nothing is blocked or selected."
        templates = [
            f'A10 frontier; past visible evidence only, current screen wins.\nOpen: "{label}" (+6 more). Supported locally: none. Evidence: this decision screen appeared 8x in 7 steps with no durable open-item advance.\n{suffix}'
            for label in ("W" * 24, "记" * 24, "é" * 24, "🙂" * 24)
        ]
        templates.extend(item["goal"] for item in query_set["records"])
        counts = [len(tokenizer.encode(text, add_special_tokens=False)) for text in templates]
        checks["tokenizer"] = {"status": "pass", "path": str(tokenizer_path), "max_added_tokens_per_nonempty_read": max(counts[:4]), "max_query_tokens": max(counts[4:]), "max_added_memory_tokens_per_episode": max(counts[:4]) * 5}
        if max(counts[:4]) > 192 or max(counts[:4]) * 5 > 960:
            errors.append("tokenizer_budget_exceeded")
    except Exception as exc:
        errors.append(f"tokenizer_check_failed:{type(exc).__name__}:{exc}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--implementation-commit", required=True)
    parser.add_argument("--tokenizer-path", type=Path, default=Path("/root/autodl-tmp/models/Qwen3-VL-32B-Instruct-modelscope"))
    parser.add_argument("--allow-missing-tokenizer-for-local-review", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/a10/A10_ZERO_GENERATION_PREFLIGHT.json")
    parser.add_argument(
        "--offline-trace-root",
        type=Path,
        default=ROOT / "runs/a10_offline_replay_materialized",
    )
    args = parser.parse_args()
    errors: list[str] = []
    checks: dict[str, Any] = {}
    check_identity(errors, checks, args.implementation_commit)
    check_config(errors, checks)
    check_task_and_trace_manifests(errors, checks)
    check_real_offline_replay(errors, checks, args.offline_trace_root)
    check_ast_and_runtime(errors, checks)
    run_tests(errors, checks)
    check_tokenizer(errors, checks, args.tokenizer_path, args.allow_missing_tokenizer_for_local_review)
    try:
        source_freeze = current_source_freeze()
    except Exception as exc:
        source_freeze = {}
        errors.append(f"source_freeze_failed:{type(exc).__name__}:{exc}")
    report = {"schema": "a10_zero_generation_preflight_v1", "status": "pass" if not errors else "fail", "generation_calls": 0, "created_at": datetime.now(timezone.utc).isoformat(), "parent_evidence_commit": PARENT_EVIDENCE_COMMIT, "a10_implementation_commit": args.implementation_commit, "source_freeze": source_freeze, "source_freeze_sha256": json_sha256(source_freeze), "checks": checks, "errors": errors}
    atomic_json(args.output, report)
    print(json.dumps({"status": report["status"], "output": str(args.output), "sha256": file_sha(args.output), "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
