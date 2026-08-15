#!/usr/bin/env python3
"""Execute one immutable next SYS-TRRC campaign stage with a hash ledger."""
from __future__ import annotations

import argparse
import atexit
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
PYTHON = ROOT / "06_local_runtime/envs/androidworld/Scripts/python.exe"
sys.path.insert(0, str(ROOT / "implementation/src"))
from raven_m.official_qwen_mobile import sys_trrc_contract as contract  # noqa: E402


def _file_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _content_sha(value: dict) -> str:
    payload = dict(value)
    payload.pop("content_sha256", None)
    return contract.canonical_sha256(payload)


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _load_ledger(path: Path) -> dict:
    if not path.is_file():
        payload = {
            "schema": "sys_trrc_campaign_ledger_v1",
            "protocol_id": contract.PROTOCOL_ID,
            "campaign_id": f"sys_trrc_campaign_{uuid4().hex}",
            "planned_order": [list(item) for item in contract.CAMPAIGN_INVOCATION_ORDER],
            "entries": [],
            "pending_attempt": None,
        }
        return {**payload, "content_sha256": _content_sha(payload)}
    return contract.validate_campaign_ledger(path)


def _replace_ledger(path: Path, ledger: dict, **updates: object) -> dict:
    payload = {key: value for key, value in ledger.items() if key != "content_sha256"}
    payload.update(updates)
    sealed = {**payload, "content_sha256": _content_sha(payload)}
    _write(path, sealed)
    return sealed


def _campaign_suite(output_root: Path, campaign_id: str, mode: str) -> Path | None:
    matches: list[Path] = []
    for suite in output_root.glob("official_qwen_*") if output_root.is_dir() else []:
        signature_path = suite / "run_signature.json"
        if not signature_path.is_file():
            continue
        try:
            signature = json.loads(signature_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if (
            signature.get("campaign_id") == campaign_id
            and signature.get("sys_trrc_mode") == mode
        ):
            matches.append(suite.resolve())
    if len(matches) > 1:
        raise RuntimeError("SYS-TRRC pending invocation resolved multiple suites")
    return matches[0] if matches else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=contract.MODE_BINDINGS, required=True)
    parser.add_argument("--stage", choices=("l1", "l2", "l3", "l4"), required=True)
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--launch-receipt", type=Path, required=True)
    parser.add_argument("--preflight", type=Path)
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument(
        "--campaign-ledger", type=Path,
        default=ROOT / "runs/sys_trrc_campaign/ledger.json",
    )
    parser.add_argument("--processor-path", type=Path)
    parser.add_argument("--processor-python", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    ledger_path = args.campaign_ledger.resolve()
    lock_path = ledger_path.with_suffix(ledger_path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(
            f"SYS-TRRC campaign ledger is locked: {lock_path}"
        ) from exc
    os.write(lock_fd, f"pid={os.getpid()}\n".encode("ascii"))

    def release_lock() -> None:
        try:
            os.close(lock_fd)
        except OSError:
            pass
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass

    atexit.register(release_lock)

    ledger = _load_ledger(ledger_path)
    if args.execute and not ledger_path.is_file():
        _write(ledger_path, ledger)
    entries = list(ledger.get("entries") or [])
    if len(entries) >= len(contract.CAMPAIGN_INVOCATION_ORDER):
        raise RuntimeError("SYS-TRRC campaign is already complete")
    expected = contract.CAMPAIGN_INVOCATION_ORDER[len(entries)]
    if (args.mode, args.stage) != expected:
        raise RuntimeError(
            f"SYS-TRRC next invocation is {expected}, not {(args.mode, args.stage)}"
        )
    if entries and entries[-1].get("advancement_authorized") is not True:
        raise RuntimeError("SYS-TRRC previous stage is terminal; campaign cannot advance")

    pending = ledger.get("pending_attempt")
    prior_mode_entries = [entry for entry in entries if entry["mode"] == args.mode]
    resume_suite = (
        Path(str(pending.get("suite_dir"))).resolve()
        if isinstance(pending, dict) and pending.get("suite_dir")
        else Path(prior_mode_entries[-1]["suite_dir"])
        if prior_mode_entries else None
    )
    preflight = args.preflight or ROOT / (
        f"evidence/sys_trrc/SYS_TRRC_{args.mode.upper()}_ZERO_GENERATION_PREFLIGHT.json"
    )
    output_root = ROOT / f"runs/sys_trrc_{args.mode}"
    if isinstance(pending, dict) and resume_suite is None:
        resume_suite = _campaign_suite(
            output_root, str(ledger["campaign_id"]), args.mode
        )
    if pending is None:
        pending = {
            "ordinal": len(entries) + 1,
            "mode": args.mode,
            "stage": args.stage,
            "suite_dir": str(resume_suite.resolve()) if resume_suite else None,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        if args.execute:
            ledger = _replace_ledger(ledger_path, ledger, pending_attempt=pending)
    elif resume_suite is not None and not pending.get("suite_dir"):
        pending = {**pending, "suite_dir": str(resume_suite.resolve())}
        if args.execute:
            ledger = _replace_ledger(ledger_path, ledger, pending_attempt=pending)
    before = set(output_root.glob("official_qwen_*")) if output_root.is_dir() else set()
    command = [
        str(PYTHON), str(ROOT / "implementation/scripts/run_official_qwen_mobile.py"),
        "--adb-path", args.adb_path,
        "--manifest", str(ROOT / "implementation/configs/androidworld_hard_v2_instances.json"),
        "--url", args.url,
        "--console-port", str(args.console_port), "--grpc-port", str(args.grpc_port),
        "--sys-trrc-mode", args.mode, "--sys-trrc-stage", args.stage,
        "--sys-trrc-preflight-report", str(preflight.resolve()),
        "--sys-trrc-launch-receipt", str(args.launch_receipt.resolve()),
        "--sys-trrc-campaign-ledger", str(args.campaign_ledger.resolve()),
        "--output-root", str(output_root),
    ]
    if resume_suite is not None:
        command += ["--resume-suite-dir", str(resume_suite.resolve())]
    processor = args.processor_path or ROOT / (
            "06_local_runtime/cache/qwen3_vl_32b_tokenizer/"
            "models--Qwen--Qwen3-VL-32B-Instruct/snapshots/"
            "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
    )
    processor_python = args.processor_python or Path(
        getattr(sys, "_base_executable", sys.executable)
    )
    command += [
        "--sys-trrc-processor-path", str(processor.resolve()),
        "--sys-trrc-processor-python", str(processor_python.resolve()),
    ]
    print(subprocess.list2cmdline(command))
    if not args.execute:
        return 0

    return_code = subprocess.call(command)
    suite_dir = resume_suite
    if suite_dir is None:
        created = sorted(set(output_root.glob("official_qwen_*")) - before)
        if len(created) != 1:
            raise RuntimeError("SYS-TRRC could not identify the fresh suite directory")
        suite_dir = created[0]
    pending = {**pending, "suite_dir": str(suite_dir.resolve())}
    ledger = _replace_ledger(ledger_path, ledger, pending_attempt=pending)
    checkpoint_path = suite_dir / "checkpoint.json"
    result_path = suite_dir / "sys_trrc_result.json"
    if not checkpoint_path.is_file() or not result_path.is_file():
        raise RuntimeError("SYS-TRRC stage produced no auditable checkpoint/result")
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    expected_completion = contract.stage_contract(args.mode, args.stage)["completion_status"]
    advancement = return_code == 0 and checkpoint.get("status") == expected_completion
    if checkpoint.get("status") == "stopped_invalid_episode":
        # A retained infrastructure-invalid attempt is resumable within this
        # same ordinal.  It is deliberately not appended to `entries`, so it
        # cannot consume or advance the scientific campaign stage.
        return return_code if return_code != 0 else 1
    allowed_terminal = {
        "infrastructure_incomplete",
        "stopped_preservation_gate_failure", "stopped_activation_gate_failure",
        "stopped_preservation_gate_incomplete", "stopped_activation_gate_incomplete",
    }
    if not advancement and checkpoint.get("status") not in allowed_terminal:
        raise RuntimeError(
            "SYS-TRRC invocation ended without a resumable infrastructure status, "
            "a frozen terminal status, or exact stage completion"
        )
    previous_sha = entries[-1]["entry_sha256"] if entries else None
    artifact_root = args.campaign_ledger.resolve().parent / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    ordinal = len(entries) + 1
    checkpoint_snapshot = artifact_root / f"{ordinal:02d}_{args.mode}_{args.stage}_checkpoint.json"
    result_snapshot = artifact_root / f"{ordinal:02d}_{args.mode}_{args.stage}_result.json"
    shutil.copy2(checkpoint_path, checkpoint_snapshot)
    shutil.copy2(result_path, result_snapshot)
    entry_payload = {
        "ordinal": ordinal,
        "mode": args.mode, "stage": args.stage,
        "suite_dir": str(suite_dir.resolve()),
        "checkpoint_status": checkpoint.get("status"),
        "result_status": result.get("status"),
        "checkpoint_path": str(checkpoint_snapshot.resolve()),
        "checkpoint_path_sha256": _file_sha(checkpoint_snapshot),
        "result_path": str(result_snapshot.resolve()),
        "result_path_sha256": _file_sha(result_snapshot),
        "preflight_path": str(preflight.resolve()),
        "preflight_path_sha256": _file_sha(preflight.resolve()),
        "run_signature_sha256": str(checkpoint.get("run_signature_sha256") or ""),
        "return_code": return_code,
        "advancement_authorized": advancement,
        "previous_entry_sha256": previous_sha,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    entry = {**entry_payload, "entry_sha256": contract.canonical_sha256(entry_payload)}
    _replace_ledger(
        ledger_path, ledger, entries=entries + [entry], pending_attempt=None,
    )
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
