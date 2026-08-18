#!/usr/bin/env python3
"""Run A4-v2 fixed seven, conditionally release remaining12, then finalize."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]


def _new_suite(output_root: Path, before: set[Path]) -> Path:
    candidates = [path for path in output_root.glob("official_qwen_*") if path.is_dir() and path not in before]
    if len(candidates) != 1:
        raise RuntimeError(f"expected exactly one new suite, found {len(candidates)}")
    return candidates[0]


def _run(command: list[str], *, output_root: Path) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    before = set(output_root.glob("official_qwen_*"))
    completed = subprocess.run(command, cwd=ROOT, check=False)
    suite = _new_suite(output_root, before)
    if completed.returncode == 0:
        return suite
    for _ in range(2):
        checkpoint_path = suite / "checkpoint.json"
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8")) if checkpoint_path.is_file() else {}
        if checkpoint.get("status") != "stopped_invalid_episode":
            raise RuntimeError(f"A4-v2 runner exited {completed.returncode} outside an infrastructure-invalid boundary")
        resume = list(command) + ["--resume-suite-dir", str(suite)]
        completed = subprocess.run(resume, cwd=ROOT, check=False)
        if completed.returncode == 0:
            return suite
    raise RuntimeError("A4-v2 exhausted its two retained infrastructure replacement attempts")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, default=Path(os.environ.get("RAVEN_RUNTIME_ROOT", ROOT.parent / "RAVEN-M-Research/06_local_runtime")))
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--bank", type=Path, default=ROOT / "evidence/a4v2/A4V2_FROZEN_WORKFLOW_BANK.json")
    parser.add_argument("--preflight", type=Path, default=ROOT / "evidence/a4v2/A4V2_ZERO_GENERATION_PREFLIGHT.json")
    parser.add_argument("--receipt", type=Path, default=ROOT / "evidence/a4v2/A4V2_LIVE_SERVER_RECEIPT.json")
    parser.add_argument("--manifest", type=Path, default=ROOT / "implementation/configs/androidworld_hard_v2_instances.json")
    parser.add_argument("--output-root", type=Path, default=ROOT / "runs/a4v2_faithful_offline_awm")
    parser.add_argument("--result-output", type=Path, default=ROOT / "evidence/a4v2/A4V2_FORMAL_RESULT.json")
    parser.add_argument("--launch-intent", type=Path, default=ROOT / "evidence/a4v2/A4V2_ACQUISITION_SERVER_LAUNCH_INTENT.json")
    parser.add_argument("--ablation-bank", type=Path, default=ROOT / "evidence/a4v2/A4V2_SHUFFLED_ABLATION_BANK.json")
    parser.add_argument("--ablation-preflight", type=Path, default=ROOT / "evidence/a4v2/A4V2_SHUFFLED_ABLATION_PREFLIGHT.json")
    parser.add_argument("--ablation-receipt", type=Path, default=ROOT / "evidence/a4v2/A4V2_SHUFFLED_ABLATION_LIVE_RECEIPT.json")
    parser.add_argument("--ablation-output-root", type=Path, default=ROOT / "runs/a4v2_shuffled_active_control")
    args = parser.parse_args()
    python = args.runtime_root / "envs/androidworld/Scripts/python.exe"
    adb = args.runtime_root / "android/sdk/platform-tools/adb.exe"
    for path in (python, adb, args.bank, args.preflight, args.receipt, args.manifest):
        if not path.is_file():
            raise RuntimeError(f"required A4-v2 campaign artifact missing: {path}")
    base = [
        str(python), str(ROOT / "implementation/scripts/run_official_qwen_mobile.py"),
        "--url", args.url, "--adb-path", str(adb), "--manifest", str(args.manifest.resolve()),
        "--a345-arm", "a4v2", "--a4v2-workflow-bank", str(args.bank.resolve()),
        "--a4v2-preflight-report", str(args.preflight.resolve()),
        "--a4v2-launch-receipt", str(args.receipt.resolve()),
        "--output-root", str(args.output_root.resolve()),
        "--run-stage", "a4v2_fixed_seven",
    ]
    seven_suite = _run(base, output_root=args.output_root.resolve())
    aggregate_path = seven_suite / "aggregate.json"
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    per_task = aggregate.get("per_task") or []
    seven_pass = len(per_task) == 7 and all(row.get("success") is True and row.get("reward") == 1.0 for row in per_task)
    remaining_suite: Path | None = None
    if seven_pass:
        remaining_command = list(base)
        stage_index = remaining_command.index("a4v2_fixed_seven")
        remaining_command[stage_index] = "a4v2_remaining12"
        remaining_command.extend(["--a4v2-remaining12", "--a4v2-seven-aggregate", str(aggregate_path.resolve())])
        remaining_suite = _run(remaining_command, output_root=args.output_root.resolve())
    finalize = [
        str(python), str(ROOT / "implementation/scripts/finalize_a4v2_result.py"),
        "--seven-suite", str(seven_suite),
        "--output", str(args.result_output.resolve()),
    ]
    if remaining_suite is not None:
        finalize.extend(["--remaining-suite", str(remaining_suite)])
    completed = subprocess.run(finalize, cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise RuntimeError("A4-v2 formal result finalization failed")
    primary_result = json.loads(args.result_output.read_text(encoding="utf-8"))
    ablation_tasks = list(primary_result.get("ablation_required_tasks") or [])
    ablation_suite: Path | None = None
    if ablation_tasks:
        for path in (args.launch_intent, args.ablation_bank, args.ablation_preflight):
            if not path.is_file():
                raise RuntimeError(f"paired gain requires the pre-frozen active-control artifact: {path}")
        qualify = [
            str(python), str(ROOT / "implementation/scripts/qualify_a4v2_live_server.py"),
            "--launch-intent", str(args.launch_intent.resolve()),
            "--preflight", str(args.ablation_preflight.resolve()),
            "--bank", str(args.ablation_bank.resolve()),
            "--output", str(args.ablation_receipt.resolve()),
        ]
        subprocess.run(qualify, cwd=ROOT, check=True)
        control = [
            str(python), str(ROOT / "implementation/scripts/run_official_qwen_mobile.py"),
            "--url", args.url, "--adb-path", str(adb), "--manifest", str(args.manifest.resolve()),
            "--a345-arm", "a4v2", "--a4v2-workflow-bank", str(args.ablation_bank.resolve()),
            "--a4v2-preflight-report", str(args.ablation_preflight.resolve()),
            "--a4v2-launch-receipt", str(args.ablation_receipt.resolve()),
            "--a4v2-shuffled-control-primary-result", str(args.result_output.resolve()),
            "--output-root", str(args.ablation_output_root.resolve()),
            "--run-stage", "a4v2_shuffled_active_control",
        ]
        ablation_suite = _run(control, output_root=args.ablation_output_root.resolve())
        seal_control = [
            str(python), str(ROOT / "implementation/scripts/finalize_a4v2_ablation.py"),
            "--primary-result", str(args.result_output.resolve()),
            "--suite-dir", str(ablation_suite),
            "--bank", str(args.ablation_bank.resolve()),
        ]
        subprocess.run(seal_control, cwd=ROOT, check=True)
    print(json.dumps({
        "status": "COMPLETE_19" if remaining_suite else "SEALED_SEVEN_DIAGNOSTIC_NO_RELEASE",
        "seven_suite": str(seven_suite), "remaining_suite": str(remaining_suite) if remaining_suite else None,
        "ablation_suite": str(ablation_suite) if ablation_suite else None,
    }, indent=2))


if __name__ == "__main__":
    main()
