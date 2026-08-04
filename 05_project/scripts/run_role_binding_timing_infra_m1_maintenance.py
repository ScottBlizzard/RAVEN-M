"""Run the frozen INFRA-M1 project-owned maintenance and burn-in batch."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from typing import Any

from jsonschema import Draft202012Validator
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.role_binding_timing.infra_m1_runtime import (  # noqa: E402
    listener_pids,
    parse_framework_service,
    parse_runtime_state,
    process_matches,
)


def digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def digest_path(path: Path) -> str:
    return digest(path.read_bytes())


def save_bytes(path: Path, value: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    return {"path": path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": len(value), "sha256": digest(value)}


def save_json(path: Path, value: Any) -> dict[str, Any]:
    raw = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return save_bytes(path, raw)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_raw(command: list[str], *, root: Path, name: str, timeout: float, env: dict[str, str] | None = None) -> tuple[dict[str, Any], bytes, bytes]:
    started = time.monotonic()
    try:
        result = subprocess.run(command, capture_output=True, text=False, check=False, timeout=timeout, env=env)
        stdout, stderr = bytes(result.stdout), bytes(result.stderr)
        returncode, timed_out = result.returncode, False
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = bytes(exc.stdout or b""), bytes(exc.stderr or b"")
        returncode, timed_out = None, True
    return {
        "command": command, "returncode": returncode, "timed_out": timed_out,
        "wall_time_seconds": time.monotonic() - started,
        "stdout": save_bytes(root / f"{name}.stdout.bin", stdout),
        "stderr": save_bytes(root / f"{name}.stderr.bin", stderr),
    }, stdout, stderr


def process_inventory() -> list[dict[str, Any]]:
    command = (
        "Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'adb|qemu|emulator|python'} | "
        "Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine,CreationDate | ConvertTo-Json -Depth 3"
    )
    result = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True, check=True, timeout=20)
    payload = json.loads(result.stdout or "[]")
    return payload if isinstance(payload, list) else [payload]


def netstat_text() -> str:
    return subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, check=True, timeout=20).stdout


def runtime_snapshot(config: dict[str, Any]) -> dict[str, Any]:
    runtime = config["runtime"]
    netstat = netstat_text()
    ports = (5037, 5038, 5554, 5555, 8554)
    listeners = {str(port): listener_pids(netstat, port) for port in ports}
    processes = process_inventory()
    by_pid = {int(item["ProcessId"]): item for item in processes}
    adb_pid = listeners["5038"][0] if len(listeners["5038"]) == 1 else None
    qemu_pid = listeners["8554"][0] if len(listeners["8554"]) == 1 else None
    launcher_pid = int(by_pid[qemu_pid]["ParentProcessId"]) if qemu_pid in by_pid else None
    all_runtime_pids = sorted(
        int(item["ProcessId"]) for item in processes
        if str(item.get("Name", "")).casefold() in {"adb.exe", "emulator.exe", "qemu-system-x86_64-headless.exe"}
    )
    owned = {pid for pid in (adb_pid, launcher_pid, qemu_pid) if pid is not None}
    return {
        "captured_at": utc_now(),
        "listeners": listeners,
        "adb_pid": adb_pid,
        "launcher_pid": launcher_pid,
        "qemu_pid": qemu_pid,
        "adb_process": by_pid.get(adb_pid),
        "launcher_process": by_pid.get(launcher_pid),
        "qemu_process": by_pid.get(qemu_pid),
        "excluded_runtime_pids": [pid for pid in all_runtime_pids if pid not in owned],
        "excluded_runtime_processes": {
            str(pid): by_pid[pid] for pid in all_runtime_pids if pid not in owned
        },
    }


def ownership_issues(snapshot: dict[str, Any], config: dict[str, Any]) -> list[str]:
    runtime = config["runtime"]
    issues: list[str] = []
    if snapshot["listeners"]["5037"]:
        issues.append("FORBIDDEN_5037")
    if snapshot["listeners"]["5038"] != [snapshot["adb_pid"]] or snapshot["adb_pid"] is None:
        issues.append("ADB_LISTENER")
    if any(snapshot["listeners"][str(port)] != [snapshot["qemu_pid"]] for port in (5554, 5555, 8554)) or snapshot["qemu_pid"] is None:
        issues.append("EMULATOR_LISTENERS")
    paths = {
        "adb": str((REPOSITORY_ROOT / runtime["adb_binary"]).resolve()),
        "launcher": str((REPOSITORY_ROOT / runtime["emulator_launcher"]).resolve()),
        "qemu": str((REPOSITORY_ROOT / runtime["qemu_binary"]).resolve()),
    }
    if not snapshot["adb_process"] or not process_matches(snapshot["adb_process"], expected_path=paths["adb"], required_command_parts=["tcp:5038", "fork-server"]):
        issues.append("ADB_PROCESS")
    required_emulator = ["-avd AndroidWorldAvd", "-port 5554", "-grpc 8554", "-no-window"]
    if not snapshot["launcher_process"] or not process_matches(snapshot["launcher_process"], expected_path=paths["launcher"], required_command_parts=required_emulator):
        issues.append("LAUNCHER_PROCESS")
    if not snapshot["qemu_process"] or not process_matches(snapshot["qemu_process"], expected_path=paths["qemu"], required_command_parts=required_emulator):
        issues.append("QEMU_PROCESS")
    for name, expected_hash in (("adb_binary", runtime["adb_binary_sha256"]), ("emulator_launcher", runtime["emulator_launcher_sha256"]), ("qemu_binary", runtime["qemu_binary_sha256"])):
        if digest_path(REPOSITORY_ROOT / runtime[name]) != expected_hash:
            issues.append(f"BINARY_HASH:{name}")
    return issues


def process_exists(pid: int | None) -> bool:
    if pid is None:
        return False
    result = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, check=False, timeout=10)
    return str(pid) in result.stdout


def wait_until(predicate: Any, *, attempts: int, interval: float) -> tuple[bool, int]:
    for index in range(1, attempts + 1):
        if predicate():
            return True, index
        if index < attempts:
            time.sleep(interval)
    return False, attempts


def command_ok(record: dict[str, Any], stderr: bytes = b"") -> bool:
    return record["returncode"] == 0 and not record["timed_out"] and not stderr.strip()


def command_completed(record: dict[str, Any]) -> bool:
    """Process completed successfully; stdout/stderr remain evidence for later audit."""
    return record["returncode"] == 0 and not record["timed_out"]


def adb_prefix(config: dict[str, Any], *, include_serial: bool = True) -> list[str]:
    runtime = config["runtime"]
    value = [str((REPOSITORY_ROOT / runtime["adb_binary"]).resolve()), "-P", str(runtime["adb_server_port"])]
    if include_serial:
        value += ["-s", runtime["device_serial"]]
    return value


def validate_png(raw: bytes, expected_size: list[int]) -> dict[str, Any]:
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("SCREENSHOT_PNG_SIGNATURE")
    with Image.open(io.BytesIO(raw)) as image:
        image.load()
        size = list(image.size)
        mode = image.mode
    if size != expected_size:
        raise ValueError(f"SCREENSHOT_SIZE:{size}:{expected_size}")
    return {"bytes": len(raw), "sha256": digest(raw), "size": size, "mode": mode}


def boot_and_framework_ready(config: dict[str, Any], root: Path, expected: dict[str, Any]) -> dict[str, Any]:
    prefix = adb_prefix(config)
    maintenance = config["maintenance"]
    attempts = []
    for index in range(1, maintenance["boot_wait_attempts"] + 1):
        attempt_root = root / "boot" / f"attempt_{index:02d}"
        state_record, state_raw, state_err = run_raw(prefix + ["get-state"], root=attempt_root, name="get_state", timeout=15)
        boot_record, boot_raw, boot_err = run_raw(prefix + ["shell", "getprop", "sys.boot_completed"], root=attempt_root, name="boot_completed", timeout=15)
        snapshot = runtime_snapshot(config)
        passed = (
            command_ok(state_record, state_err) and state_raw.strip() == b"device"
            and command_ok(boot_record, boot_err) and boot_raw.strip() == b"1"
            and not ownership_issues(snapshot, config)
            and snapshot["adb_pid"] == expected["adb_pid"]
            and snapshot["launcher_pid"] == expected["launcher_pid"]
            and snapshot["qemu_pid"] == expected["qemu_pid"]
        )
        attempt = {"index": index, "passed": passed, "snapshot": snapshot, "records": {"state": state_record, "boot": boot_record}}
        save_json(attempt_root / "attempt.json", attempt)
        attempts.append(attempt)
        if passed:
            break
        if index < maintenance["boot_wait_attempts"]:
            time.sleep(maintenance["boot_wait_interval_seconds"])
    if not attempts or not attempts[-1]["passed"]:
        return {"passed": False, "first_broken_edge": "BOOT_NOT_READY", "boot_attempts": attempts, "framework_attempts": []}

    for name, args in (
        ("wake", ["shell", "input", "keyevent", "224"]),
        ("dismiss_keyguard", ["shell", "wm", "dismiss-keyguard"]),
        ("home", ["shell", "input", "keyevent", "3"]),
    ):
        record, _, stderr = run_raw(prefix + args, root=root / "interactive_setup", name=name, timeout=15)
        if not command_ok(record, stderr):
            return {"passed": False, "first_broken_edge": f"INTERACTIVE_SETUP:{name}", "boot_attempts": attempts, "framework_attempts": []}

    framework_attempts = []
    consecutive = 0
    for index in range(1, maintenance["framework_stable_attempts"] + 1):
        attempt_root = root / "framework" / f"attempt_{index:02d}"
        records: dict[str, Any] = {}
        payloads: dict[str, bytes] = {}
        stderrs: dict[str, bytes] = {}
        commands = {
            "package": ["shell", "service", "check", "package"],
            "window": ["shell", "service", "check", "window"],
            "activity": ["shell", "service", "check", "activity"],
            "power": ["shell", "dumpsys", "power"],
            "displays": ["shell", "dumpsys", "window", "displays"],
            "policy": ["shell", "dumpsys", "window", "policy"],
            "activities": ["shell", "dumpsys", "activity", "activities"],
        }
        for name, args in commands.items():
            record, stdout, stderr = run_raw(prefix + args, root=attempt_root, name=name, timeout=15)
            records[name], payloads[name], stderrs[name] = record, stdout, stderr
        state = parse_runtime_state(
            payloads["power"].decode("utf-8", errors="replace"),
            payloads["displays"].decode("utf-8", errors="replace"),
            payloads["policy"].decode("utf-8", errors="replace"),
        )
        snapshot = runtime_snapshot(config)
        services = {name: parse_framework_service(payloads[name], name) for name in ("package", "window", "activity")}
        passed = (
            all(command_ok(records[name], stderrs[name]) for name in records)
            and all(services.values()) and all(state.values())
            and bool(payloads["activities"].strip())
            and not ownership_issues(snapshot, config)
            and all(snapshot[key] == expected[key] for key in ("adb_pid", "launcher_pid", "qemu_pid"))
        )
        consecutive = consecutive + 1 if passed else 0
        attempt = {"index": index, "passed": passed, "consecutive": consecutive, "services": services, "runtime_state": state, "snapshot": snapshot, "records": records}
        save_json(attempt_root / "attempt.json", attempt)
        framework_attempts.append(attempt)
        if consecutive >= maintenance["framework_stable_required_consecutive"]:
            return {"passed": True, "first_broken_edge": None, "boot_attempts": attempts, "framework_attempts": framework_attempts}
        if index < maintenance["framework_stable_attempts"]:
            time.sleep(maintenance["framework_stable_interval_seconds"])
    return {"passed": False, "first_broken_edge": "FRAMEWORK_NOT_STABLE", "boot_attempts": attempts, "framework_attempts": framework_attempts}


def run_burn_in(config: dict[str, Any], root: Path, expected: dict[str, Any]) -> dict[str, Any]:
    prefix = adb_prefix(config)
    burn = config["burn_in"]
    started = time.monotonic()
    records = []
    first_broken_edge = None
    for index in range(1, burn["cycles"] + 1):
        cycle_root = root / f"cycle_{index:02d}"
        before = runtime_snapshot(config)
        commands = {
            "get_state": ["get-state"],
            "boot_completed": ["shell", "getprop", "sys.boot_completed"],
            "service_package": ["shell", "service", "check", "package"],
            "service_window": ["shell", "service", "check", "window"],
            "service_activity": ["shell", "service", "check", "activity"],
            "wake": ["shell", "input", "keyevent", "224"],
            "dismiss_keyguard": ["shell", "wm", "dismiss-keyguard"],
            "home": ["shell", "input", "keyevent", "3"],
            "power": ["shell", "dumpsys", "power"],
            "displays": ["shell", "dumpsys", "window", "displays"],
            "policy": ["shell", "dumpsys", "window", "policy"],
            "activities": ["shell", "dumpsys", "activity", "activities"],
            "screenshot": ["exec-out", "screencap", "-p"],
        }
        command_records: dict[str, Any] = {}
        payloads: dict[str, bytes] = {}
        stderrs: dict[str, bytes] = {}
        for name, args in commands.items():
            record, stdout, stderr = run_raw(prefix + args, root=cycle_root / "raw", name=name, timeout=burn["command_timeout_seconds"])
            command_records[name], payloads[name], stderrs[name] = record, stdout, stderr
            if not command_ok(record, stderr):
                first_broken_edge = f"CYCLE_{index:02d}_COMMAND:{name}"
                break
        state = {}
        services = {}
        screenshot = None
        issues = []
        if first_broken_edge is None:
            services = {
                "package": parse_framework_service(payloads["service_package"], "package"),
                "window": parse_framework_service(payloads["service_window"], "window"),
                "activity": parse_framework_service(payloads["service_activity"], "activity"),
            }
            state = parse_runtime_state(
                payloads["power"].decode("utf-8", errors="replace"),
                payloads["displays"].decode("utf-8", errors="replace"),
                payloads["policy"].decode("utf-8", errors="replace"),
            )
            try:
                screenshot = validate_png(payloads["screenshot"], burn["expected_screenshot_size"])
            except Exception as exc:
                issues.append(f"SCREENSHOT:{type(exc).__name__}:{exc}")
            if payloads["get_state"].strip() != b"device":
                issues.append("DEVICE_STATE")
            if payloads["boot_completed"].strip() != b"1":
                issues.append("BOOT_STATE")
            if not all(services.values()):
                issues.append("FRAMEWORK_SERVICES")
            if not all(state.values()):
                issues.append("POWER_DISPLAY_KEYGUARD")
            if not payloads["activities"].strip():
                issues.append("ACTIVITY_DUMP_EMPTY")
        after = runtime_snapshot(config)
        for label, snapshot in (("before", before), ("after", after)):
            ownership = ownership_issues(snapshot, config)
            if ownership:
                issues.extend(f"{label}:{item}" for item in ownership)
            for key in ("adb_pid", "launcher_pid", "qemu_pid"):
                if snapshot[key] != expected[key]:
                    issues.append(f"{label}:{key.upper()}_DRIFT")
        passed = first_broken_edge is None and not issues
        if not passed and first_broken_edge is None:
            first_broken_edge = f"CYCLE_{index:02d}:{issues[0] if issues else 'UNKNOWN'}"
        cycle = {
            "index": index, "passed": passed, "before": before, "after": after,
            "services": services, "runtime_state": state, "screenshot": screenshot,
            "issues": issues, "records": command_records,
        }
        save_json(cycle_root / "cycle_result.json", cycle)
        records.append(cycle)
        if not passed:
            break
        if index < burn["cycles"]:
            time.sleep(burn["cycle_interval_seconds"])
    elapsed = time.monotonic() - started
    passed = (
        len(records) == burn["cycles"]
        and all(record["passed"] for record in records)
        and elapsed >= burn["minimum_elapsed_seconds"]
    )
    if len(records) == burn["cycles"] and all(record["passed"] for record in records) and elapsed < burn["minimum_elapsed_seconds"]:
        first_broken_edge = "MINIMUM_BURN_IN_DURATION"
    return {
        "passed": passed, "first_broken_edge": first_broken_edge,
        "required_cycles": burn["cycles"], "completed_cycles": len(records),
        "passed_cycles": sum(record["passed"] for record in records),
        "elapsed_seconds": elapsed, "records": records,
    }


def verify_freeze(config: dict[str, Any], lock: dict[str, Any]) -> None:
    if config["generation_calls_authorized"] != 0:
        raise RuntimeError("GENERATION_BOUNDARY")
    for relative, expected in lock["files"].items():
        if digest_path(REPOSITORY_ROOT / relative) != expected:
            raise RuntimeError(f"FREEZE_HASH:{relative}")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=True).stdout.strip()
    tag = subprocess.run(["git", "rev-list", "-n", "1", config["freeze_tag"]], cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=True).stdout.strip()
    if head != tag:
        raise RuntimeError(f"FREEZE_TAG:{head}:{tag}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = json.loads((REPOSITORY_ROOT / args.config).read_text(encoding="utf-8"))
    lock = json.loads((REPOSITORY_ROOT / config["lock"]).read_text(encoding="utf-8"))
    verify_freeze(config, lock)
    output_root = REPOSITORY_ROOT / config["output_root"]
    if output_root.exists():
        raise RuntimeError("INFRA_M1_OUTPUT_NOT_FRESH")
    output_root.mkdir(parents=True)
    (output_root / ".gitattributes").write_text("**/*.bin -text\n", encoding="ascii")
    protected_before = {name: digest_path(REPOSITORY_ROOT / name) for name in config["protected_wip"]}
    if protected_before != config["protected_wip"]:
        raise RuntimeError(f"PROTECTED_WIP:{protected_before}")
    pre_inventory = json.loads((REPOSITORY_ROOT / config["pre_inventory_root"] / "pre_maintenance_inventory.json").read_text(encoding="utf-8"))
    started = utc_now()
    status = "OWNERSHIP_NOT_QUALIFIED"
    first_broken_edge = None
    primary_error = None
    before = runtime_snapshot(config)
    maintenance: dict[str, Any] = {"before": before, "steps": {}}
    burn_in = {"passed": False, "first_broken_edge": "NOT_RUN", "required_cycles": 24, "completed_cycles": 0, "passed_cycles": 0, "elapsed_seconds": 0.0, "records": []}
    try:
        issues = ownership_issues(before, config)
        inventory_owned = pre_inventory["project_owned"]
        for key in ("adb_pid", "launcher_pid", "qemu_pid"):
            if before[key] != inventory_owned[key]:
                issues.append(f"PRE_INVENTORY_PID:{key}")
        if before["excluded_runtime_pids"] != pre_inventory["excluded_process_pids"]:
            issues.append("PRE_INVENTORY_EXCLUDED_PID_DRIFT")
        if issues:
            first_broken_edge = f"OWNERSHIP:{issues[0]}"
            maintenance["ownership_issues"] = issues
        else:
            status = "RUNTIME_UNSTABLE"
            old = {key: before[key] for key in ("adb_pid", "launcher_pid", "qemu_pid")}
            adb_no_serial = adb_prefix(config, include_serial=False)
            adb_device = adb_prefix(config)
            stop_record, _, stop_err = run_raw(
                adb_device + ["emu", "kill"], root=output_root / "maintenance" / "stop",
                name="emulator_clean_stop", timeout=config["maintenance"]["command_timeout_seconds"],
            )
            maintenance["steps"]["emulator_clean_stop"] = stop_record
            if not command_completed(stop_record):
                first_broken_edge = "EMULATOR_CLEAN_STOP_COMMAND"
            else:
                stopped, stop_attempts = wait_until(
                    lambda: not process_exists(old["qemu_pid"]) and not process_exists(old["launcher_pid"])
                    and not any(listener_pids(netstat_text(), port) for port in (5554, 5555, 8554)),
                    attempts=config["maintenance"]["stop_wait_attempts"],
                    interval=config["maintenance"]["stop_wait_interval_seconds"],
                )
                maintenance["steps"]["emulator_exit"] = {"passed": stopped, "attempts": stop_attempts}
                if not stopped:
                    first_broken_edge = "EMULATOR_DID_NOT_EXIT"
            if first_broken_edge is None:
                kill_record, _, kill_err = run_raw(
                    adb_no_serial + ["kill-server"], root=output_root / "maintenance" / "stop",
                    name="adb_5038_clean_stop", timeout=config["maintenance"]["command_timeout_seconds"],
                )
                maintenance["steps"]["adb_clean_stop"] = kill_record
                if not command_completed(kill_record):
                    first_broken_edge = "ADB_CLEAN_STOP_COMMAND"
                else:
                    stopped, stop_attempts = wait_until(
                        lambda: not process_exists(old["adb_pid"]) and not listener_pids(netstat_text(), 5038),
                        attempts=config["maintenance"]["stop_wait_attempts"],
                        interval=config["maintenance"]["stop_wait_interval_seconds"],
                    )
                    maintenance["steps"]["adb_exit"] = {"passed": stopped, "attempts": stop_attempts}
                    if not stopped or listener_pids(netstat_text(), 5037):
                        first_broken_edge = "ADB_DID_NOT_EXIT_OR_5037"
            if first_broken_edge is None:
                start_record, _, start_err = run_raw(
                    adb_no_serial + ["start-server"], root=output_root / "maintenance" / "start",
                    name="adb_5038_start", timeout=config["maintenance"]["command_timeout_seconds"],
                )
                maintenance["steps"]["adb_start"] = start_record
                if not command_completed(start_record):
                    first_broken_edge = "ADB_START_COMMAND"
                else:
                    ready, attempts = wait_until(lambda: len(listener_pids(netstat_text(), 5038)) == 1 and not listener_pids(netstat_text(), 5037), attempts=15, interval=1.0)
                    maintenance["steps"]["adb_ready"] = {"passed": ready, "attempts": attempts}
                    if not ready:
                        first_broken_edge = "ADB_START_IDENTITY"
            launcher_process = None
            if first_broken_edge is None:
                runtime = config["runtime"]
                launcher = (REPOSITORY_ROOT / runtime["emulator_launcher"]).resolve()
                child_env = os.environ.copy()
                child_env["ANDROID_AVD_HOME"] = str((REPOSITORY_ROOT / runtime["avd_home"]).resolve())
                child_env["ANDROID_SDK_ROOT"] = str((REPOSITORY_ROOT / "06_local_runtime/android/sdk").resolve())
                log_root = output_root / "maintenance" / "start"
                log_root.mkdir(parents=True, exist_ok=True)
                stdout_file = (log_root / "emulator.stdout.bin").open("wb")
                stderr_file = (log_root / "emulator.stderr.bin").open("wb")
                try:
                    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    launcher_process = subprocess.Popen(
                        [str(launcher), *runtime["emulator_args"]], cwd=launcher.parent,
                        env=child_env, stdout=stdout_file, stderr=stderr_file,
                        creationflags=flags,
                    )
                finally:
                    stdout_file.close()
                    stderr_file.close()
                maintenance["steps"]["emulator_start"] = {"command": [str(launcher), *runtime["emulator_args"]], "launcher_spawn_pid": launcher_process.pid, "android_avd_home": child_env["ANDROID_AVD_HOME"]}
                ready, attempts = wait_until(
                    lambda: len(listener_pids(netstat_text(), 8554)) == 1 and len(listener_pids(netstat_text(), 5554)) == 1 and len(listener_pids(netstat_text(), 5555)) == 1,
                    attempts=config["maintenance"]["boot_wait_attempts"],
                    interval=config["maintenance"]["boot_wait_interval_seconds"],
                )
                maintenance["steps"]["emulator_ports_ready"] = {"passed": ready, "attempts": attempts}
                if not ready:
                    first_broken_edge = "EMULATOR_PORTS_NOT_READY"
            if first_broken_edge is None:
                after_start = runtime_snapshot(config)
                start_issues = ownership_issues(after_start, config)
                if launcher_process is not None and after_start["launcher_pid"] != launcher_process.pid:
                    start_issues.append("LAUNCHER_SPAWN_PID_MISMATCH")
                if after_start["adb_pid"] == old["adb_pid"] or after_start["qemu_pid"] == old["qemu_pid"] or after_start["launcher_pid"] == old["launcher_pid"]:
                    start_issues.append("PID_NOT_FRESH")
                if after_start["excluded_runtime_pids"] != before["excluded_runtime_pids"]:
                    start_issues.append("EXCLUDED_PROCESS_PID_DRIFT")
                maintenance["after_start"] = after_start
                maintenance["start_issues"] = start_issues
                if start_issues:
                    first_broken_edge = f"RESTART_IDENTITY:{start_issues[0]}"
                else:
                    expected = {key: after_start[key] for key in ("adb_pid", "launcher_pid", "qemu_pid")}
                    boot = boot_and_framework_ready(config, output_root / "maintenance" / "qualification", expected)
                    maintenance["boot_and_framework"] = boot
                    if not boot["passed"]:
                        first_broken_edge = boot["first_broken_edge"]
                    else:
                        burn_in = run_burn_in(config, output_root / "burn_in", expected)
                        if burn_in["passed"]:
                            status = "RUNTIME_STABLE_24_OF_24"
                        else:
                            first_broken_edge = burn_in["first_broken_edge"]
    except Exception as exc:
        status = "RUNTIME_UNSTABLE" if status != "OWNERSHIP_NOT_QUALIFIED" else status
        first_broken_edge = first_broken_edge or f"EXCEPTION:{type(exc).__name__}:{exc}"
        primary_error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}

    final_snapshot = runtime_snapshot(config)
    maintenance["final_snapshot"] = final_snapshot
    protected_after = {name: digest_path(REPOSITORY_ROOT / name) for name in config["protected_wip"]}
    terminal_issues: list[str] = []
    if protected_after != protected_before:
        terminal_issues.append("PROTECTED_WIP_DRIFT")
    if final_snapshot["excluded_runtime_pids"] != before["excluded_runtime_pids"]:
        terminal_issues.append("EXCLUDED_PROCESS_PID_DRIFT")
    if status == "RUNTIME_STABLE_24_OF_24":
        terminal_issues.extend(ownership_issues(final_snapshot, config))
    if terminal_issues:
        status = "RUNTIME_UNSTABLE" if status != "OWNERSHIP_NOT_QUALIFIED" else status
        first_broken_edge = first_broken_edge or f"TERMINAL:{terminal_issues[0]}"
    maintenance["terminal_issues"] = terminal_issues
    completion = {
        "schema_version": "role_binding_timing.infra_m1.completion.v1",
        "status": status,
        "first_broken_edge": first_broken_edge,
        "started_at": started,
        "completed_at": utc_now(),
        "development_contaminated": True,
        "held_out_eligible": False,
        "generation_calls": 0,
        "model_tokens": 0,
        "primary_error": primary_error,
        "maintenance": maintenance,
        "burn_in": burn_in,
        "protected_wip_before": protected_before,
        "protected_wip_after": protected_after,
        "protected_wip_unchanged": protected_before == protected_after == config["protected_wip"],
        "claim_evidence": {
            "runtime_stable": status == "RUNTIME_STABLE_24_OF_24",
            "a11y_qualification_authorized": status == "RUNTIME_STABLE_24_OF_24",
            "a11y_tested": False,
            "held_out_tested": False,
            "role_binding_hypothesis_tested": False,
        },
    }
    schema = json.loads((REPOSITORY_ROOT / config["schema"]).read_text(encoding="utf-8"))
    completion["schema_errors"] = [error.message for error in Draft202012Validator(schema).iter_errors(completion)]
    completion_path = output_root / "maintenance_completion.json"
    if completion_path.exists():
        raise RuntimeError("DUPLICATE_COMPLETION")
    save_json(completion_path, completion)
    artifacts = []
    for path in sorted(output_root.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.json":
            artifacts.append({"path": path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": digest_path(path)})
    save_json(output_root / "artifact_manifest.json", {"schema_version": "role_binding_timing.infra_m1.manifest.v1", "artifacts": artifacts})
    print(json.dumps({"status": status, "first_broken_edge": first_broken_edge, "burn_in": f"{burn_in['passed_cycles']}/{burn_in['required_cycles']}", "elapsed_seconds": burn_in["elapsed_seconds"], "schema_errors": completion["schema_errors"]}, indent=2))
    return 0 if status == "RUNTIME_STABLE_24_OF_24" and not completion["schema_errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
