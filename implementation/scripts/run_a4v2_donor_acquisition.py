#!/usr/bin/env python3
"""Run one immutable A4-v2 donor manifest with the screenshot-only A0 controller."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.request


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "evidence/a4v2/A4V2_DONOR_ACQUISITION_MANIFEST_V2.json")
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--runtime-root", type=Path, default=Path(os.environ.get("RAVEN_RUNTIME_ROOT", ROOT.parent / "RAVEN-M-Research/06_local_runtime")))
    parser.add_argument("--output-root", type=Path, default=ROOT / "runs/a4v2_donor_acquisition_plan_v2")
    parser.add_argument("--resume-suite-dir", type=Path)
    parser.add_argument("--server-receipt", type=Path, required=True)
    args = parser.parse_args()
    python = args.runtime_root / "envs/androidworld/Scripts/python.exe"
    adb = args.runtime_root / "android/sdk/platform-tools/adb.exe"
    for path in (python, adb, args.manifest):
        if not path.is_file():
            raise RuntimeError(f"required donor runtime artifact missing: {path}")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest.get("schema") != "a4v2.donor_acquisition_manifest.v1" or len(manifest.get("tasks") or []) < 1:
        raise RuntimeError("A4-v2 donor acquisition manifest is invalid")
    body = {key: value for key, value in manifest.items() if key != "content_sha256"}
    import hashlib
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if manifest.get("content_sha256") != hashlib.sha256(canonical).hexdigest():
        raise RuntimeError("A4-v2 donor acquisition manifest content drift")
    plan_path = ROOT / str(manifest["plan_path"])
    if not plan_path.is_file() or hashlib.sha256(plan_path.read_bytes()).hexdigest() != manifest.get("plan_file_sha256"):
        raise RuntimeError("A4-v2 donor acquisition plan drift")
    android_root = args.runtime_root.parent / "03_code/third_party/android_world"
    android_commit = subprocess.check_output(
        ["git", "-C", str(android_root), "rev-parse", "HEAD"], text=True
    ).strip()
    if android_commit != manifest.get("androidworld_commit"):
        raise RuntimeError("AndroidWorld runtime commit drift")
    expected_android = manifest.get("androidworld_worktree_identity") or {}
    tracked_diff = subprocess.check_output(
        ["git", "-C", str(android_root), "diff", "--no-ext-diff", "--binary", "HEAD"]
    )
    untracked = subprocess.check_output(
        ["git", "-C", str(android_root), "ls-files", "--others", "--exclude-standard"],
        text=True,
    ).splitlines()
    actual_android = {
        "head": android_commit,
        "tracked_diff_sha256": hashlib.sha256(tracked_diff).hexdigest(),
        "untracked_files": {
            relative.replace("\\", "/"): hashlib.sha256((android_root / relative).read_bytes()).hexdigest()
            for relative in sorted(untracked)
            if (android_root / relative).is_file()
        },
    }
    if actual_android != expected_android:
        raise RuntimeError("AndroidWorld runtime worktree identity drift")
    sys.path[:0] = [str(ROOT / "implementation/src"), str(android_root), str(args.runtime_root / "scripts")]
    from android_world import registry
    from raven_m.multi_framework_benchmark.task_instances import instantiate_verified
    from raven_m.official_qwen_mobile.a4v2_faithful_awm import validate_acquisition_receipt
    receipt = validate_acquisition_receipt(args.server_receipt.resolve())
    repository_commit = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
    ).strip()
    if receipt.get("repository_commit") != repository_commit:
        raise RuntimeError("A4-v2 acquisition receipt/repository commit drift")
    available = registry.TaskRegistry().get_registry(registry.TaskRegistry.ANDROID_WORLD_FAMILY)
    for spec in manifest["tasks"]:
        instantiate_verified(available, spec)
    with urllib.request.urlopen(args.url.rstrip("/") + "/v1/models", timeout=30) as response:
        models = json.loads(response.read().decode("utf-8"))
    if [row.get("id") for row in models.get("data", [])] != ["Qwen/Qwen3-VL-32B-Instruct"]:
        raise RuntimeError("frozen Qwen3-VL-32B service is unavailable or drifted")
    command = [
        str(python),
        str(ROOT / "implementation/scripts/run_official_qwen_mobile.py"),
        "--url", args.url,
        "--adb-path", str(adb),
        "--manifest", str(args.manifest.resolve()),
        "--run-stage", "a4v2_donor_acquisition_v1",
        "--diagnostic",
        "--held-out-ineligible-reason", "donor_acquisition_not_scored",
        "--single-transport-no-retry",
        "--a4v2-acquisition-receipt", str(args.server_receipt.resolve()),
        "--output-root", str(args.output_root.resolve()),
    ]
    if args.resume_suite_dir:
        command.extend(["--resume-suite-dir", str(args.resume_suite_dir.resolve())])
    before = set(args.output_root.glob("official_qwen_*"))
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode == 0:
        return
    suite = args.resume_suite_dir.resolve() if args.resume_suite_dir else None
    if suite is None:
        created = [path for path in args.output_root.glob("official_qwen_*") if path not in before]
        if len(created) == 1:
            suite = created[0]
    for _ in range(2):
        checkpoint_path = suite / "checkpoint.json" if suite else None
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8")) if checkpoint_path and checkpoint_path.is_file() else {}
        if checkpoint.get("status") != "stopped_invalid_episode":
            raise SystemExit(completed.returncode)
        resume = [item for item in command if item not in {"--resume-suite-dir", str(suite)}]
        resume.extend(["--resume-suite-dir", str(suite)])
        completed = subprocess.run(resume, cwd=ROOT, check=False)
        if completed.returncode == 0:
            return
    raise RuntimeError("donor acquisition exhausted two retained infrastructure replacements")


if __name__ == "__main__":
    main()
