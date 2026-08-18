#!/usr/bin/env python3
"""Zero-generation local readiness audit for the A4-v2 campaign."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[2]


def _digest(value: object) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, default=Path(os.environ.get("RAVEN_RUNTIME_ROOT", ROOT.parent / "RAVEN-M-Research/06_local_runtime")))
    parser.add_argument("--output", type=Path, default=ROOT / "evidence/a4v2/A4V2_CPU_READINESS_2026-08-19.json")
    args = parser.parse_args()
    python = args.runtime_root / "envs/androidworld/Scripts/python.exe"
    adb = args.runtime_root / "android/sdk/platform-tools/adb.exe"
    manifest = ROOT / "evidence/a4v2/A4V2_DONOR_ACQUISITION_MANIFEST_V2.json"
    required = [
        ROOT / "protocols/A4V2_FAITHFUL_OFFLINE_AWM_PREREG_2026-08-18.md",
        ROOT / "protocols/A4V2_EXECUTION_RUNBOOK_2026-08-18.md",
        ROOT / "protocols/A4V2_DONOR_ACQUISITION_PLAN_V2_AMENDMENT_2026-08-19.md",
        ROOT / "implementation/configs/a4v2_awm_donor_acquisition_plan.json",
        manifest, python, adb,
    ]
    errors = [f"missing:{path}" for path in required if not path.is_file()]
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all"], text=True).strip()
    if dirty:
        errors.append("worktree_dirty")
    tests_command = [
        sys.executable, "-m", "pytest",
        "implementation/tests/official_qwen_mobile/test_a4v2_faithful_awm.py",
        "implementation/tests/official_qwen_mobile/test_a4v2_induction.py",
        "implementation/tests/official_qwen_mobile/test_a4v2_runner_contract.py",
        "implementation/tests/official_qwen_mobile/test_a4v2_donor_pipeline.py",
        "implementation/tests/official_qwen_mobile/test_a4v2_finalizer.py",
        "-q", "-p", "no:cacheprovider",
    ]
    env = dict(os.environ); env["PYTHONPATH"] = os.pathsep.join([str(ROOT), str(ROOT / "implementation/src"), env.get("PYTHONPATH", "")])
    tests = subprocess.run(tests_command, cwd=ROOT, env=env, text=True, capture_output=True, check=False)
    if tests.returncode:
        errors.append("focused_tests_failed")
    adb_devices = subprocess.run([str(adb), "devices"], text=True, capture_output=True, check=False)
    boot = subprocess.run([str(adb), "-s", "emulator-5554", "shell", "getprop", "sys.boot_completed"], text=True, capture_output=True, check=False)
    wm = subprocess.run([str(adb), "-s", "emulator-5554", "shell", "wm", "size"], text=True, capture_output=True, check=False)
    if adb_devices.returncode or "emulator-5554\tdevice" not in adb_devices.stdout or boot.stdout.strip() != "1":
        errors.append("adb_emulator_not_ready")
    try:
        with urllib.request.urlopen("http://127.0.0.1:18000/v1/models", timeout=3) as response:
            model_payload = json.loads(response.read().decode("utf-8"))
        observed_models = [row.get("id") for row in model_payload.get("data", [])]
        gpu_service_ready = observed_models == ["Qwen/Qwen3-VL-32B-Instruct"]
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        observed_models = []
        gpu_service_ready = False
    cpu_errors = [error for error in errors if error != "gpu_service_unavailable"]
    status = "READY_FOR_GENERATION" if not cpu_errors and gpu_service_ready else "CPU_READY_EXTERNAL_MODEL_UNAVAILABLE" if not cpu_errors else "CPU_NOT_READY"
    result = {
        "schema": "a4v2.cpu_readiness.v1", "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status, "generation_calls": 0, "repository_head": head,
        "worktree_clean": not bool(dirty), "focused_tests": {"command": tests_command, "returncode": tests.returncode, "stdout": tests.stdout, "stderr": tests.stderr},
        "adb": {"devices": adb_devices.stdout, "boot_completed": boot.stdout.strip(), "wm_size": wm.stdout.strip()},
        "model_service": {"url": "http://127.0.0.1:18000", "ready": gpu_service_ready, "served_model_ids": observed_models},
        "required_files_present": not any(error.startswith("missing:") for error in errors),
        "errors": errors,
    }
    result["content_sha256"] = _digest(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "output": str(args.output), "content_sha256": result["content_sha256"]}, indent=2))
    if status == "CPU_NOT_READY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
