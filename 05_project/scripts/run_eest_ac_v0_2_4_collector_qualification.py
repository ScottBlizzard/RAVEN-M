"""Run the single frozen zero-model v0.2.4 collector-lifecycle batch."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
LOCAL_RUNTIME = REPOSITORY_ROOT / "06_local_runtime"
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(LOCAL_RUNTIME / "scripts"))

import androidworld_compat  # noqa: E402,F401
from raven_m.eest_ac.action_adapter_v0_2_2 import EestActionAdapterV022  # noqa: E402
from raven_m.eest_ac.collector_lifecycle_v0_2_4 import (  # noqa: E402
    AtomicCompletionWriter,
    CollectorLifecycleError,
    acquire_pre_action_readiness,
    audit_owned_helpers,
    cleanup_reverse_listener,
    file_sha256,
    load_contract,
    preserve_primary_error,
    validate_completion,
)
from raven_m.eest_ac.runtime_v0_2_2 import assert_frozen_adb_server_port, load_and_setup_env  # noqa: E402
from raven_m.eest_ac.trace_harness_v0_2_3 import capture_post_sequence, capture_snapshot  # noqa: E402


PROTOCOL_FREEZE_TAG = "eest-ac-v0.2.4-collector-lifecycle-protocol-freeze-20260804"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run(command: list[str], timeout: int = 12) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=timeout)
        return {
            "command": command[1:],
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "timed_out": False,
            "wall_time_seconds": time.monotonic() - started,
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return {
            "command": command[1:],
            "returncode": None,
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
            "timed_out": True,
            "wall_time_seconds": time.monotonic() - started,
        }


def _netstat_listeners(port: int) -> list[dict[str, Any]]:
    result = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, check=False, timeout=10)
    records = []
    pattern = re.compile(r"^\s*TCP\s+(\S+):(\d+)\s+(\S+)\s+(LISTENING)\s+(\d+)\s*$", re.IGNORECASE)
    for line in result.stdout.splitlines():
        match = pattern.match(line)
        if match and int(match.group(2)) == port:
            records.append({"local_address": match.group(1), "port": port, "state": match.group(4), "pid": int(match.group(5))})
    return records


def _process_identity(pid: int) -> dict[str, Any]:
    command = [
        "powershell", "-NoProfile", "-Command",
        f"$p=Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\" -ErrorAction SilentlyContinue;"
        "if($p){[pscustomobject]@{pid=$p.ProcessId;path=$p.ExecutablePath;command_line=$p.CommandLine;working_set_bytes=$p.WorkingSetSize}|ConvertTo-Json -Compress}",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=10)
    lines = [line for line in result.stdout.splitlines() if line.strip().startswith("{")]
    if not lines:
        return {"pid": pid, "path": None, "command_line": None, "working_set_bytes": None}
    return json.loads(lines[-1])


def diagnose_host(adb_path: Path, port: int) -> dict[str, Any]:
    listeners = _netstat_listeners(port)
    identities = [_process_identity(item["pid"]) for item in listeners]
    abnormal = _process_identity(17716)
    return {
        "port": port,
        "listeners": listeners,
        "listener_processes": identities,
        "abnormal_pid_17716": abnormal,
        "abnormal_pid_owned": False,
        "client_binary": str(adb_path),
        "client_binary_sha256": file_sha256(adb_path),
    }


def _isolation_audit(adb_path: Path, port: int, serial: str, expected_hash: str) -> dict[str, Any]:
    host = diagnose_host(adb_path, port)
    server_hash = None
    server_path = None
    if len(host["listener_processes"]) == 1 and host["listener_processes"][0].get("path"):
        server_path = str(Path(host["listener_processes"][0]["path"]).resolve())
        candidate = Path(server_path)
        if candidate.is_file():
            server_hash = file_sha256(candidate)
    state = _run([str(adb_path), "-P", str(port), "-s", serial, "get-state"], 10)
    serial_check = _run([str(adb_path), "-P", str(port), "-s", serial, "get-serialno"], 10)
    passed = bool(
        host["client_binary_sha256"] == expected_hash
        and len(host["listeners"]) == 1
        and server_hash == expected_hash
        and state["returncode"] == 0 and state["stdout"] == "device"
        and serial_check["returncode"] == 0 and serial_check["stdout"] == serial
    )
    return {
        "adb_server_port": port,
        "device_serial": serial,
        "client_binary_sha256": host["client_binary_sha256"],
        "server_binary_sha256": server_hash,
        "server_binary": server_path,
        "fallback_to_5037": False,
        "passed": passed,
        "host_diagnosis": host,
        "device_state": state,
        "serial_check": serial_check,
    }


def frozen_bootstrap(adb_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    runtime = config["runtime"]
    port = int(runtime["adb_server_port"])
    before = diagnose_host(adb_path, port)
    start = None
    if not before["listeners"]:
        start = _run([str(adb_path), "-P", str(port), "start-server"], int(runtime["bootstrap"]["timeout_seconds"]))
    after = _isolation_audit(
        adb_path, port, runtime["device_serial"], runtime["adb_binary_sha256"],
    )
    return {
        "before": before,
        "official_start_server_attempted": start is not None,
        "official_start_server_attempt_count": 1 if start is not None else 0,
        "start_server": start,
        "killed_or_restarted_process": False,
        "fallback_to_5037": False,
        "after": after,
        "passed": after["passed"],
    }


def _execute(env: Any, adapter: EestActionAdapterV022, action: dict[str, Any]) -> dict[str, Any]:
    state = env.get_state(wait_to_stabilize=True)
    height, width = state.pixels.shape[:2]
    mapped = adapter.map_action(action, screen_width=int(width), screen_height=int(height))
    adapter.execute(env, mapped)
    return mapped.audit_record()


def _error_record(exc: BaseException, *, default_layer: str) -> dict[str, str]:
    if isinstance(exc, CollectorLifecycleError):
        return exc.record()
    return {"code": type(exc).__name__.upper(), "message": str(exc), "layer": default_layer}


def _artifact_hashes(root: Path) -> list[dict[str, Any]]:
    result = []
    for path in sorted(item for item in root.rglob("*") if item.is_file() and item.name != "collection_complete.json" and ".tmp" not in item.name):
        result.append({
            "path": str(path.relative_to(root)).replace("\\", "/"),
            "sha256": file_sha256(path),
            "bytes": path.stat().st_size,
        })
    return result


def _process_alive(pid: int) -> bool:
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", f"if(Get-Process -Id {pid} -ErrorAction SilentlyContinue){{exit 0}}else{{exit 1}}"],
        capture_output=True, check=False, timeout=10,
    )
    return result.returncode == 0


def run_single(
    *,
    run_id: str,
    run_root: Path,
    config: dict[str, Any],
    adb_path: Path,
    bootstrap: dict[str, Any],
    console_port: int,
    grpc_port: int,
) -> dict[str, Any]:
    if run_root.exists() and any(run_root.iterdir()):
        raise CollectorLifecycleError("RUN_ROOT_NOT_FRESH", str(run_root), "preflight")
    run_root.mkdir(parents=True, exist_ok=True)
    writer = AtomicCompletionWriter(run_root / "collection_complete.json")
    started = _utc_now()
    env = None
    adapter = EestActionAdapterV022()
    readiness_audit = {
        "qualified": False, "attempt_count": 0, "max_attempts": 5,
        "delay_seconds": 1.0, "stable_consecutive_required": 2, "attempts": [],
    }
    action_execution_count = 0
    post_count = 0
    collection_record_valid = False
    primary_error: dict[str, Any] | None = None
    cleanup_errors: list[dict[str, Any]] = []
    reset_audit: dict[str, Any] = {"attempted": False, "passed": False, "record": None}
    close_audit: dict[str, Any] = {"attempted": False, "passed": False}
    isolation = bootstrap["after"]
    try:
        _write_json(run_root / "bootstrap_audit.json", bootstrap)
        if not bootstrap["passed"]:
            raise CollectorLifecycleError("ADB_ISOLATION_NOT_READY", "Frozen 5038 bootstrap/isolation did not pass.", "isolation")
        isolation = _isolation_audit(
            adb_path, config["runtime"]["adb_server_port"], config["runtime"]["device_serial"],
            config["runtime"]["adb_binary_sha256"],
        )
        _write_json(run_root / "isolation_pre.json", isolation)
        if not isolation["passed"]:
            raise CollectorLifecycleError("ADB_ISOLATION_DRIFT", "Per-run 5038 isolation check failed.", "isolation")
        env = load_and_setup_env(
            console_port=console_port, emulator_setup=False, freeze_datetime=True,
            adb_path=str(adb_path), adb_server_port=config["runtime"]["adb_server_port"], grpc_port=grpc_port,
        )
        setup_audit = []
        for action in config["scene"]["setup_actions"]:
            setup_audit.append(_execute(env, adapter, action))
            time.sleep(2.0)
        _write_json(run_root / "setup_audit.json", setup_audit)
        raw_dir = run_root / "raw"

        def capture(attempt: int) -> Any:
            return capture_snapshot(
                env=env, output_dir=raw_dir, sample_id=f"pre_readiness_{attempt:02d}",
                adb_path=str(adb_path), adb_server_port=config["runtime"]["adb_server_port"],
                serial=config["runtime"]["device_serial"],
            )

        readiness = acquire_pre_action_readiness(capture, contract=load_contract())
        readiness_audit = readiness.audit
        _write_json(run_root / "pre_readiness_audit.json", readiness_audit)
        if not readiness.qualified or readiness.snapshot is None:
            raise CollectorLifecycleError("PRE_READINESS_TIMEOUT", "Critical pre evidence did not become stably ready.", "readiness")
        action_audit = _execute(env, adapter, config["scene"]["test_action"])
        action_execution_count = 1
        posts = capture_post_sequence(
            env=env, output_dir=raw_dir, count=config["sampling"]["post_observations"],
            delay_seconds=config["sampling"]["delay_seconds"], adb_path=str(adb_path),
            adb_server_port=config["runtime"]["adb_server_port"], serial=config["runtime"]["device_serial"],
        )
        post_count = len(posts)
        collection_record = {
            "schema_version": "eest_ac_collector_record.v0_2_4",
            "run_id": run_id,
            "development_contaminated": True,
            "held_out_eligible": False,
            "pre_readiness": readiness_audit,
            "pre": readiness.snapshot.raw_record,
            "action": action_audit,
            "action_execution_count": action_execution_count,
            "post": [item.raw_record for item in posts],
            "post_observation_count": post_count,
            "generation_calls": 0,
            "oracle_efficacy_evaluations": 0,
        }
        collection_record_valid = bool(
            readiness_audit["qualified"]
            and action_execution_count == 1
            and post_count == config["sampling"]["post_observations"]
            and collection_record["pre"]["semantic_element_count"] > 0
            and collection_record["pre"]["package_names"]
            and collection_record["pre"]["activity"]
            and collection_record["pre"]["route_signature"]
        )
        if not collection_record_valid:
            raise CollectorLifecycleError("COLLECTION_RECORD_INVALID", "Collection record invariant failed.", "collection")
        _write_json(run_root / "collection_record.json", collection_record)
    except BaseException as exc:  # terminal accounting must include infrastructure exceptions
        primary_error = _error_record(exc, default_layer="collection")
    finally:
        if env is not None:
            reset_audit["attempted"] = True
            try:
                reset_audit["record"] = _execute(env, adapter, config["scene"]["reset_action"])
                reset_audit["passed"] = True
            except BaseException as exc:
                cleanup_errors.append(_error_record(exc, default_layer="reset"))
            close_audit["attempted"] = True
            try:
                env.close()
                close_audit["passed"] = True
            except BaseException as exc:
                cleanup_errors.append(_error_record(exc, default_layer="environment_close"))
        reverse = cleanup_reverse_listener(
            adb_path=str(adb_path), port=config["runtime"]["adb_server_port"],
            serial=config["runtime"]["device_serial"], listener=config["cleanup"]["reverse_listener"],
        )
        if not reverse.get("verified_absent"):
            cleanup_errors.append({"code": "REVERSE_CLEANUP_FAILED", "message": reverse.get("error", "unknown"), "layer": "cleanup"})
        helpers = audit_owned_helpers(config["cleanup"]["owned_helper_pids"], _process_alive)
        if not helpers["passed"]:
            cleanup_errors.append({"code": "HELPER_RESIDUE", "message": str(helpers["residual_pids"]), "layer": "cleanup"})
        primary_error, cleanup_errors = preserve_primary_error(primary_error, cleanup_errors)
        residue_free = bool(reverse.get("verified_absent") and helpers["passed"])
        cleanup = {
            "reverse": reverse,
            "reset": reset_audit,
            "environment_close": close_audit,
            "owned_helpers": helpers,
            "secondary_errors": cleanup_errors,
            "residue_free": residue_free,
        }
        success = bool(
            primary_error is None and not cleanup_errors and isolation["passed"]
            and readiness_audit["qualified"] and action_execution_count == 1
            and post_count == config["sampling"]["post_observations"]
            and collection_record_valid and reset_audit["passed"] and close_audit["passed"] and residue_free
        )
        record = {
            "schema_version": "eest_ac_collector_completion.v0_2_4",
            "run_id": run_id,
            "status": "pass" if success else "fail",
            "started_at_utc": started,
            "completed_at_utc": _utc_now(),
            "generation_calls": 0,
            "held_out_traces": 0,
            "oracle_efficacy_evaluations": 0,
            "readiness": readiness_audit,
            "action_executed": action_execution_count == 1,
            "action_execution_count": action_execution_count,
            "post_observation_count": post_count,
            "collection_record_valid": collection_record_valid,
            "primary_error": primary_error,
            "cleanup": cleanup,
            "isolation": {
                key: isolation.get(key) for key in (
                    "adb_server_port", "device_serial", "client_binary_sha256",
                    "server_binary_sha256", "fallback_to_5037", "passed",
                )
            },
            "artifact_hashes": _artifact_hashes(run_root),
            "terminal_record_ordinal": 1,
        }
        completion_sha = writer.write_once(record)
        validate_completion(json.loads((run_root / "collection_complete.json").read_text(encoding="utf-8")))
        terminal_count = len(list(run_root.glob("collection_complete.json")))
        if terminal_count != 1:
            raise CollectorLifecycleError("TERMINAL_RECORD_COUNT", str(terminal_count), "completion")
        return {"record": record, "completion_sha256": completion_sha, "terminal_record_count": terminal_count}


def _verify_lock(lock_path: Path) -> dict[str, Any]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    checks = []
    for relative, expected in lock["frozen_artifacts"].items():
        path = REPOSITORY_ROOT / relative
        actual = file_sha256(path) if path.is_file() else None
        checks.append({"path": relative, "expected": expected, "actual": actual, "passed": actual == expected})
    if not all(item["passed"] for item in checks):
        raise CollectorLifecycleError("LOCK_HASH_MISMATCH", canonical_json(checks), "lock")
    tag_commit = subprocess.run(
        ["git", "rev-list", "-n", "1", lock["protocol_freeze_tag"]], cwd=REPOSITORY_ROOT,
        capture_output=True, text=True, check=False, timeout=10,
    ).stdout.strip()
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT,
        capture_output=True, text=True, check=True, timeout=10,
    ).stdout.strip()
    if tag_commit != head:
        raise CollectorLifecycleError("PROTOCOL_TAG_HEAD_MISMATCH", f"tag={tag_commit};head={head}", "lock")
    return {"checks": checks, "protocol_freeze_tag": lock["protocol_freeze_tag"], "commit": head, "passed": True}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--adb-path", type=Path, required=True)
    parser.add_argument("--adb-server-port", type=int, required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    assert_frozen_adb_server_port(configured=config["runtime"]["adb_server_port"], supplied=args.adb_server_port)
    if args.adb_server_port == 5037:
        raise CollectorLifecycleError("ADB_FALLBACK_FORBIDDEN", "5037 may not be used.", "isolation")
    lock_audit = _verify_lock(args.lock)
    batch_root = REPOSITORY_ROOT / Path(config["run_roots"][0]).parent
    if batch_root.exists() and any(batch_root.iterdir()):
        raise CollectorLifecycleError("BATCH_ROOT_NOT_FRESH", str(batch_root), "preflight")
    batch_root.mkdir(parents=True, exist_ok=True)
    _write_json(batch_root / "lock_audit.json", lock_audit)
    bootstrap = frozen_bootstrap(args.adb_path.resolve(), config)
    _write_json(batch_root / "bootstrap_audit.json", bootstrap)
    results = []
    stopped_early = False
    for run_id, relative_root in zip(config["run_order"], config["run_roots"], strict=True):
        result = run_single(
            run_id=run_id, run_root=REPOSITORY_ROOT / relative_root, config=config,
            adb_path=args.adb_path.resolve(), bootstrap=bootstrap,
            console_port=args.console_port, grpc_port=args.grpc_port,
        )
        results.append({
            "run_id": run_id,
            "status": result["record"]["status"],
            "completion_sha256": result["completion_sha256"],
            "terminal_record_count": result["terminal_record_count"],
        })
        if result["record"]["status"] != "pass":
            stopped_early = True
            break
    batch_pass = len(results) == 2 and all(item["status"] == "pass" for item in results)
    batch = {
        "schema_version": "eest_ac_collector_lifecycle_batch.v0_2_4",
        "batch_id": config["batch_id"],
        "status": "pass" if batch_pass else "fail",
        "development_contaminated": True,
        "held_out_eligible": False,
        "generation_calls": 0,
        "held_out_traces": 0,
        "oracle_efficacy_evaluations": 0,
        "planned_runs": config["run_order"],
        "completed_runs": results,
        "not_run": config["run_order"][len(results):],
        "stopped_early": stopped_early,
        "bootstrap_passed": bootstrap["passed"],
        "completed_at_utc": _utc_now(),
    }
    _write_json(batch_root / "batch_complete.json", batch)
    print(json.dumps(batch, ensure_ascii=False, indent=2))
    if not batch_pass:
        raise CollectorLifecycleError("QUALIFICATION_BATCH_FAILED", "v0.2.4 batch did not pass.", "batch")


if __name__ == "__main__":
    main()
