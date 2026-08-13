#!/usr/bin/env python3
"""Strict zero-generation BPR-v2 source/replay/test qualification."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "implementation/src"))

from raven_m.official_qwen_mobile import a1r1_bpr_v2_contract as contract  # noqa: E402
from raven_m.official_qwen_mobile.a1r1_bpr_v2 import (  # noqa: E402
    BoundedPendingReceiptV2,
    MECHANISM_ID,
    RENDERER_TEMPLATE,
)
from replay_a1r1_bpr_v2_offline import reconstruct  # noqa: E402


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def runtime_canary() -> dict:
    samples: list[float] = []
    for index in range(1000):
        memory = BoundedPendingReceiptV2()
        start = time.perf_counter_ns()
        memory.observe_step(
            source_step=0,
            action_summary="PEND[op=delete zucchini;proof=zucchini absent] | Tap delete.",
            canonical_action={"type": "tap", "x": 0.5, "y": 0.5},
            transition={},
            source_call_id="c",
            source_response_sha256="r",
            source_screenshot_sha256="s",
        )
        text, audit = memory.read({"before": {"pixel_sha256": f"rgb-{index}"}})
        memory.commit_injection(audit["ticket_id"], "prompt")
        assert text == RENDERER_TEMPLATE.format(op="delete zucchini", proof="zucchini absent")
        samples.append((time.perf_counter_ns() - start) / 1_000_000)
    samples.sort()
    return {
        "iterations": len(samples),
        "p50_ms": samples[499],
        "p99_ms": samples[989],
        "max_ms": samples[-1],
        "pass": samples[989] < 2.0 and samples[-1] < 10.0,
    }


def build(implementation_commit: str) -> dict:
    errors: list[str] = []
    freeze = contract.source_freeze_payload(implementation_commit)
    write_json(contract.SOURCE_FREEZE_PATH, freeze)
    replay = reconstruct(ROOT / "runs/a1_working_memory/official_qwen_20260810T122419_26573d7c")
    write_json(contract.OFFLINE_REPLAY_PATH, replay)
    if replay["status"] != "PASS" or replay["errors"] != []:
        errors.append("offline_replay_fail")

    test_command = [
        sys.executable, "-m", "pytest", "-q",
        "implementation/tests/official_qwen_mobile/test_a1r1_bpr_v2.py",
        "implementation/tests/official_qwen_mobile/test_a1r1_bpr_v2_contract.py",
        "implementation/tests/official_qwen_mobile/test_a1r1_bpr_v2_controller_integration.py",
        "implementation/tests/official_qwen_mobile/test_a1r1_bpr_v2_offline_replay.py",
    ]
    test_env = dict(__import__("os").environ)
    test_env["PYTHONPATH"] = str(ROOT / "implementation/src") + __import__("os").pathsep + str(ROOT)
    test_run = subprocess.run(
        test_command, cwd=ROOT, text=True, capture_output=True, check=False, env=test_env
    )
    if test_run.returncode:
        errors.append("bpr_test_suite_fail")

    canary = runtime_canary()
    if not canary["pass"]:
        errors.append("runtime_canary_fail")
    manifest = json.loads((ROOT / "implementation/configs/androidworld_hard_v2_instances.json").read_text(encoding="utf-8"))
    instances = [item for item in manifest.get("instances") or [] if int(item.get("task_seed", -1)) == contract.TASK_SEED]
    if len(instances) != 19 or len({item["task_class"] for item in instances}) != 19:
        errors.append("task_manifest_not_exact_19")
    if any(not int(item.get("native_max_steps") or 0) for item in instances):
        errors.append("native_step_budget_missing")

    status = "PASS" if not errors else "FAIL"
    payload = {
        "schema": contract.PREFLIGHT_SCHEMA,
        "status": status,
        "errors": errors,
        "mechanism_id": MECHANISM_ID,
        "implementation_commit": implementation_commit,
        "source_freeze_content_sha256": freeze["content_sha256"],
        "source_freeze_file_sha256": contract.file_sha256(contract.SOURCE_FREEZE_PATH),
        "offline_replay_file_sha256": contract.file_sha256(contract.OFFLINE_REPLAY_PATH),
        "generation_calls": 0,
        "live_generation_authorized": status == "PASS",
        "R5_status": "PROSPECTIVE_UNKNOWN_PRELIVE",
        "task_manifest": {"task_seed": contract.TASK_SEED, "task_count": len(instances), "generation_seed": contract.GENERATION_SEED},
        "tests": {"command": test_command, "returncode": test_run.returncode, "stdout_tail": test_run.stdout[-4000:], "stderr_tail": test_run.stderr[-2000:]},
        "runtime_canary": canary,
        "token_bound": {
            "method": "UTF-8 byte upper bound retained as fail-closed model-token accounting",
            "max_chars_per_read": 340,
            "max_utf8_bytes_per_read": 396,
            "max_model_token_upper_bound_per_read": 396,
            "episode_model_token_upper_bound": 3168,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    report = {**payload, "content_sha256": contract.content_sha256(payload)}
    write_json(contract.PREFLIGHT_PATH, report)
    if status == "PASS":
        contract.validate_preflight_report()
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--implementation-commit")
    parser.add_argument("--validate-existing", action="store_true")
    args = parser.parse_args()
    if args.validate_existing:
        contract.validate_preflight_report()
        print(json.dumps({"status": "PASS", "preflight": str(contract.PREFLIGHT_PATH)}, indent=2))
        return 0
    if not args.implementation_commit:
        parser.error("--implementation-commit is required when generating")
    report = build(args.implementation_commit)
    print(json.dumps({"status": report["status"], "errors": report["errors"], "preflight": str(contract.PREFLIGHT_PATH)}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
