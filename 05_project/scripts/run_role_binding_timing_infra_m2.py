"""Run the frozen INFRA-M2 exclusive-5038 launch and burn-in qualification."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
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

from raven_m.role_binding_timing.infra_m1_runtime import parse_framework_service, parse_runtime_state  # noqa: E402
from raven_m.role_binding_timing.infra_m2_runtime import (  # noqa: E402
    clean_baseline_issues,
    forbidden_5037_evidence,
    pre_cleanup_ownership_issues,
    prepare_emulator_environment,
)


def load_m1_runner() -> Any:
    path = PROJECT_ROOT / "scripts/run_role_binding_timing_infra_m1_maintenance.py"
    spec = importlib.util.spec_from_file_location("frozen_infra_m1_runner", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("M1_DEPENDENCY_LOAD_FAILURE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M1 = load_m1_runner()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json_atomic(path: Path, value: Any) -> dict[str, Any]:
    raw = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    partial = path.with_suffix(path.suffix + ".partial")
    partial.parent.mkdir(parents=True, exist_ok=True)
    partial.write_bytes(raw)
    os.replace(partial, path)
    return {"path": path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": len(raw), "sha256": M1.digest(raw)}


def adb_prefix(config: dict[str, Any], port: int, *, include_serial: bool = True) -> list[str]:
    value = [str((REPOSITORY_ROOT / config["runtime"]["adb_binary"]).resolve()), "-P", str(port)]
    if include_serial:
        value += ["-s", config["runtime"]["device_serial"]]
    return value


def completed(record: dict[str, Any]) -> bool:
    return record["returncode"] == 0 and not record["timed_out"]


def strict_ok(record: dict[str, Any], stderr: bytes) -> bool:
    return completed(record) and not stderr.strip()


def expected_runtime_issues(snapshot: dict[str, Any], config: dict[str, Any], expected: dict[str, int]) -> list[str]:
    issues = M1.ownership_issues(snapshot, config)
    issues.extend(forbidden_5037_evidence(snapshot))
    for key in ("adb_pid", "launcher_pid", "qemu_pid"):
        if snapshot.get(key) != expected[key]:
            issues.append(f"{key.upper()}_DRIFT")
    if snapshot.get("excluded_runtime_pids") != config["pre_cleanup_identity"]["excluded_runtime_pids"]:
        issues.append("EXCLUDED_PID_DRIFT")
    return issues


def wait_clean_exit(config: dict[str, Any], old: dict[str, int]) -> tuple[bool, int, dict[str, Any]]:
    maintenance = config["maintenance"]
    last = M1.runtime_snapshot(config)
    for index in range(1, maintenance["stop_wait_attempts"] + 1):
        last = M1.runtime_snapshot(config)
        emulator_gone = (
            not M1.process_exists(old["launcher_pid"])
            and not M1.process_exists(old["qemu_pid"])
            and all(not last["listeners"][str(port)] for port in (5554, 5555, 8554))
        )
        if emulator_gone:
            return True, index, last
        if index < maintenance["stop_wait_attempts"]:
            time.sleep(maintenance["stop_wait_interval_seconds"])
    return False, maintenance["stop_wait_attempts"], last


def wait_server_gone(config: dict[str, Any], *, port: int, pid: int) -> tuple[bool, int, dict[str, Any]]:
    maintenance = config["maintenance"]
    last = M1.runtime_snapshot(config)
    for index in range(1, maintenance["stop_wait_attempts"] + 1):
        last = M1.runtime_snapshot(config)
        if not M1.process_exists(pid) and not last["listeners"][str(port)]:
            return True, index, last
        if index < maintenance["stop_wait_attempts"]:
            time.sleep(maintenance["stop_wait_interval_seconds"])
    return False, maintenance["stop_wait_attempts"], last


def launch_wait(config: dict[str, Any], launcher_pid: int) -> dict[str, Any]:
    maintenance = config["maintenance"]
    attempts = []
    for index in range(1, maintenance["launch_wait_attempts"] + 1):
        snapshot = M1.runtime_snapshot(config)
        forbidden = forbidden_5037_evidence(snapshot)
        ready = (
            not forbidden
            and len(snapshot["listeners"]["5038"]) == 1
            and len(snapshot["listeners"]["5554"]) == 1
            and len(snapshot["listeners"]["5555"]) == 1
            and len(snapshot["listeners"]["8554"]) == 1
            and snapshot.get("launcher_pid") == launcher_pid
        )
        attempt = {"index": index, "snapshot": snapshot, "forbidden_5037": forbidden, "ready": ready}
        attempts.append(attempt)
        if forbidden:
            return {"passed": False, "first_broken_edge": "FORBIDDEN_5037_DURING_LAUNCH", "attempts": attempts}
        if ready:
            return {"passed": True, "first_broken_edge": None, "attempts": attempts}
        if index < maintenance["launch_wait_attempts"]:
            time.sleep(maintenance["launch_wait_interval_seconds"])
    return {"passed": False, "first_broken_edge": "EMULATOR_PORTS_NOT_READY", "attempts": attempts}


def boot_ready(config: dict[str, Any], root: Path, expected: dict[str, int]) -> dict[str, Any]:
    prefix = adb_prefix(config, 5038)
    maintenance = config["maintenance"]
    attempts = []
    for index in range(1, maintenance["boot_wait_attempts"] + 1):
        attempt_root = root / f"attempt_{index:02d}"
        before = M1.runtime_snapshot(config)
        issues = expected_runtime_issues(before, config, expected)
        if issues:
            attempt = {"index": index, "passed": False, "before": before, "issues": issues, "records": {}}
            write_json_atomic(attempt_root / "attempt.json", attempt)
            attempts.append(attempt)
            edge = "FORBIDDEN_5037_DURING_BOOT" if forbidden_5037_evidence(before) else f"BOOT_RUNTIME:{issues[0]}"
            return {"passed": False, "first_broken_edge": edge, "attempts": attempts}
        records, payloads, errors = {}, {}, {}
        commands = {
            "devices": adb_prefix(config, 5038, include_serial=False) + ["devices", "-l"],
            "get_state": prefix + ["get-state"],
            "boot_completed": prefix + ["shell", "getprop", "sys.boot_completed"],
        }
        for name, command in commands.items():
            record, stdout, stderr = M1.run_raw(command, root=attempt_root, name=name, timeout=15)
            records[name], payloads[name], errors[name] = record, stdout, stderr
        after = M1.runtime_snapshot(config)
        issues = expected_runtime_issues(after, config, expected)
        passed = (
            not issues
            and all(strict_ok(records[name], errors[name]) for name in records)
            and config["runtime"]["device_serial"].encode("utf-8") in payloads["devices"]
            and payloads["get_state"].strip() == b"device"
            and payloads["boot_completed"].strip() == b"1"
        )
        attempt = {"index": index, "passed": passed, "before": before, "after": after, "issues": issues, "records": records}
        write_json_atomic(attempt_root / "attempt.json", attempt)
        attempts.append(attempt)
        if issues:
            edge = "FORBIDDEN_5037_DURING_BOOT" if forbidden_5037_evidence(after) else f"BOOT_RUNTIME:{issues[0]}"
            return {"passed": False, "first_broken_edge": edge, "attempts": attempts}
        if passed:
            return {"passed": True, "first_broken_edge": None, "attempts": attempts}
        if index < maintenance["boot_wait_attempts"]:
            time.sleep(maintenance["boot_wait_interval_seconds"])
    return {"passed": False, "first_broken_edge": "BOOT_NOT_READY_ON_5038", "attempts": attempts}


def framework_ready(config: dict[str, Any], root: Path, expected: dict[str, int]) -> dict[str, Any]:
    prefix = adb_prefix(config, 5038)
    maintenance = config["maintenance"]
    setup = {}
    for name, args in (
        ("wake", ["shell", "input", "keyevent", "224"]),
        ("dismiss_keyguard", ["shell", "wm", "dismiss-keyguard"]),
        ("home", ["shell", "input", "keyevent", "3"]),
    ):
        before = M1.runtime_snapshot(config)
        issues = expected_runtime_issues(before, config, expected)
        if issues:
            return {"passed": False, "first_broken_edge": f"FRAMEWORK_RUNTIME:{issues[0]}", "setup": setup, "attempts": []}
        record, _, stderr = M1.run_raw(prefix + args, root=root / "setup", name=name, timeout=15)
        after = M1.runtime_snapshot(config)
        issues = expected_runtime_issues(after, config, expected)
        setup[name] = {"record": record, "before": before, "after": after, "issues": issues}
        if not strict_ok(record, stderr) or issues:
            edge = "FORBIDDEN_5037_DURING_FRAMEWORK" if forbidden_5037_evidence(after) else f"FRAMEWORK_SETUP:{name}"
            return {"passed": False, "first_broken_edge": edge, "setup": setup, "attempts": []}

    attempts = []
    consecutive = 0
    commands = {
        "package": ["shell", "service", "check", "package"],
        "window": ["shell", "service", "check", "window"],
        "activity": ["shell", "service", "check", "activity"],
        "power": ["shell", "dumpsys", "power"],
        "displays": ["shell", "dumpsys", "window", "displays"],
        "policy": ["shell", "dumpsys", "window", "policy"],
        "activities": ["shell", "dumpsys", "activity", "activities"],
    }
    for index in range(1, maintenance["framework_stable_attempts"] + 1):
        attempt_root = root / f"attempt_{index:02d}"
        before = M1.runtime_snapshot(config)
        runtime_issues = expected_runtime_issues(before, config, expected)
        records, payloads, errors = {}, {}, {}
        if not runtime_issues:
            for name, args in commands.items():
                record, stdout, stderr = M1.run_raw(prefix + args, root=attempt_root, name=name, timeout=15)
                records[name], payloads[name], errors[name] = record, stdout, stderr
        after = M1.runtime_snapshot(config)
        runtime_issues.extend(expected_runtime_issues(after, config, expected))
        services = {
            name: parse_framework_service(payloads.get(name, b""), name)
            for name in ("package", "window", "activity")
        }
        state = parse_runtime_state(
            payloads.get("power", b"").decode("utf-8", errors="replace"),
            payloads.get("displays", b"").decode("utf-8", errors="replace"),
            payloads.get("policy", b"").decode("utf-8", errors="replace"),
        )
        passed = (
            not runtime_issues
            and len(records) == len(commands)
            and all(strict_ok(records[name], errors[name]) for name in records)
            and all(services.values()) and all(state.values())
            and bool(payloads.get("activities", b"").strip())
        )
        consecutive = consecutive + 1 if passed else 0
        attempt = {"index": index, "passed": passed, "consecutive": consecutive, "before": before, "after": after, "runtime_issues": runtime_issues, "services": services, "runtime_state": state, "records": records}
        write_json_atomic(attempt_root / "attempt.json", attempt)
        attempts.append(attempt)
        if runtime_issues:
            edge = "FORBIDDEN_5037_DURING_FRAMEWORK" if forbidden_5037_evidence(after) else f"FRAMEWORK_RUNTIME:{runtime_issues[0]}"
            return {"passed": False, "first_broken_edge": edge, "setup": setup, "attempts": attempts}
        if consecutive >= maintenance["framework_stable_required_consecutive"]:
            return {"passed": True, "first_broken_edge": None, "setup": setup, "attempts": attempts}
        if index < maintenance["framework_stable_attempts"]:
            time.sleep(maintenance["framework_stable_interval_seconds"])
    return {"passed": False, "first_broken_edge": "FRAMEWORK_NOT_STABLE", "setup": setup, "attempts": attempts}


def validate_png(raw: bytes, expected_size: list[int]) -> dict[str, Any]:
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("PNG_SIGNATURE")
    with Image.open(io.BytesIO(raw)) as image:
        image.load()
        size, mode = list(image.size), image.mode
    if size != expected_size:
        raise ValueError(f"PNG_SIZE:{size}")
    return {"bytes": len(raw), "sha256": M1.digest(raw), "size": size, "mode": mode}


def burn_in(config: dict[str, Any], root: Path, expected: dict[str, int]) -> dict[str, Any]:
    prefix = adb_prefix(config, 5038)
    burn = config["burn_in"]
    started = time.monotonic()
    records = []
    first_broken_edge = None
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
    for index in range(1, burn["cycles"] + 1):
        cycle_root = root / f"cycle_{index:02d}"
        before = M1.runtime_snapshot(config)
        issues = expected_runtime_issues(before, config, expected)
        command_records, payloads, errors = {}, {}, {}
        if not issues:
            for name, args in commands.items():
                record, stdout, stderr = M1.run_raw(prefix + args, root=cycle_root / "raw", name=name, timeout=burn["command_timeout_seconds"])
                command_records[name], payloads[name], errors[name] = record, stdout, stderr
                if not strict_ok(record, stderr):
                    issues.append(f"COMMAND:{name}")
                    break
        after = M1.runtime_snapshot(config)
        issues.extend(expected_runtime_issues(after, config, expected))
        services, state, screenshot = {}, {}, None
        if not issues and len(command_records) == len(commands):
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
            if payloads["get_state"].strip() != b"device": issues.append("DEVICE_STATE")
            if payloads["boot_completed"].strip() != b"1": issues.append("BOOT_STATE")
            if not all(services.values()): issues.append("FRAMEWORK_SERVICES")
            if not all(state.values()): issues.append("POWER_DISPLAY_KEYGUARD")
            if not payloads["activities"].strip(): issues.append("ACTIVITY_DUMP_EMPTY")
            try:
                screenshot = validate_png(payloads["screenshot"], burn["expected_screenshot_size"])
            except Exception as exc:
                issues.append(f"SCREENSHOT:{type(exc).__name__}:{exc}")
        passed = not issues
        if not passed:
            if forbidden_5037_evidence(after):
                first_broken_edge = f"CYCLE_{index:02d}:FORBIDDEN_5037"
            else:
                first_broken_edge = f"CYCLE_{index:02d}:{issues[0]}"
        cycle = {"index": index, "passed": passed, "before": before, "after": after, "issues": issues, "services": services, "runtime_state": state, "screenshot": screenshot, "records": command_records}
        write_json_atomic(cycle_root / "cycle_result.json", cycle)
        records.append(cycle)
        if not passed:
            break
        if index < burn["cycles"]:
            time.sleep(burn["cycle_interval_seconds"])
    elapsed = time.monotonic() - started
    passed = len(records) == burn["cycles"] and all(item["passed"] for item in records) and elapsed >= burn["minimum_elapsed_seconds"]
    if len(records) == burn["cycles"] and all(item["passed"] for item in records) and elapsed < burn["minimum_elapsed_seconds"]:
        first_broken_edge = "MINIMUM_BURN_IN_DURATION"
    return {"passed": passed, "first_broken_edge": first_broken_edge, "required_cycles": burn["cycles"], "completed_cycles": len(records), "passed_cycles": sum(item["passed"] for item in records), "elapsed_seconds": elapsed, "records": records}


def verify_freeze(config: dict[str, Any], lock: dict[str, Any]) -> None:
    if config["generation_calls_authorized"] != 0:
        raise RuntimeError("GENERATION_BOUNDARY")
    for relative, expected in lock["files"].items():
        if M1.digest_path(REPOSITORY_ROOT / relative) != expected:
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
    runtime_log_root = REPOSITORY_ROOT / config["runtime_log_root"]
    if output_root.exists() or runtime_log_root.exists():
        raise RuntimeError("M2_ROOT_NOT_FRESH")
    output_root.mkdir(parents=True)
    (output_root / ".gitattributes").write_text("*.bin binary\n", encoding="ascii")
    protected_before = {relative: M1.digest_path(REPOSITORY_ROOT / relative) for relative in config["protected_wip"]}
    if protected_before != config["protected_wip"]:
        raise RuntimeError("PROTECTED_WIP_DRIFT")

    started = utc_now()
    status = "OWNERSHIP_NOT_QUALIFIED"
    edge = None
    primary_error = None
    before = M1.runtime_snapshot(config)
    watched_log = REPOSITORY_ROOT / config["legacy_frozen_log_watch"]["path"]
    watched_before = {"path": config["legacy_frozen_log_watch"]["path"], "bytes": watched_log.stat().st_size, "sha256": M1.digest_path(watched_log)}
    cleanup: dict[str, Any] = {"before": before, "legacy_frozen_log_before": watched_before, "steps": {}}
    launch: dict[str, Any] = {"registration_environment": config["runtime"]["registration_environment"], "started": False}
    burn = {"passed": False, "first_broken_edge": "NOT_RUN", "required_cycles": 24, "completed_cycles": 0, "passed_cycles": 0, "elapsed_seconds": 0.0, "records": []}
    launcher_process = None
    try:
        ownership = pre_cleanup_ownership_issues(before, config=config, repository_root=REPOSITORY_ROOT)
        if watched_before["sha256"] != config["legacy_frozen_log_watch"]["sha256"] or watched_before["bytes"] != config["legacy_frozen_log_watch"]["bytes"]:
            ownership.append("LEGACY_FROZEN_LOG_PRE_DRIFT")
        m1_view = deepcopy(before)
        m1_view["listeners"]["5037"] = []
        ownership.extend(M1.ownership_issues(m1_view, config))
        cleanup["ownership_issues"] = ownership
        if ownership:
            edge = f"OWNERSHIP:{ownership[0]}"
        else:
            status = "RUNTIME_UNSTABLE"
            expected_pre = config["pre_cleanup_identity"]
            record, _, stderr = M1.run_raw(
                adb_prefix(config, 5037) + ["emu", "kill"],
                root=output_root / "legacy_cleanup", name="emulator_clean_stop_via_5037",
                timeout=config["maintenance"]["command_timeout_seconds"],
            )
            cleanup["steps"]["emulator_stop"] = record
            if not completed(record):
                edge = "LEGACY_EMULATOR_STOP"
            else:
                passed, attempts, snapshot = wait_clean_exit(config, {"launcher_pid": expected_pre["launcher_pid"], "qemu_pid": expected_pre["qemu_pid"]})
                cleanup["steps"]["emulator_exit"] = {"passed": passed, "attempts": attempts, "snapshot": snapshot}
                if not passed:
                    edge = "LEGACY_EMULATOR_DID_NOT_EXIT"
                else:
                    watched_after = {"path": config["legacy_frozen_log_watch"]["path"], "bytes": watched_log.stat().st_size, "sha256": M1.digest_path(watched_log)}
                    cleanup["legacy_frozen_log_after_emulator_exit"] = watched_after
                    if watched_after != watched_before:
                        edge = "LEGACY_FROZEN_LOG_DRIFT_ON_SHUTDOWN"
            if edge is None:
                record, _, stderr = M1.run_raw(
                    adb_prefix(config, 5037, include_serial=False) + ["kill-server"],
                    root=output_root / "legacy_cleanup", name="adb_5037_clean_stop",
                    timeout=config["maintenance"]["command_timeout_seconds"],
                )
                cleanup["steps"]["adb_5037_stop"] = record
                if not completed(record):
                    edge = "LEGACY_ADB_5037_STOP"
                else:
                    passed, attempts, snapshot = wait_server_gone(config, port=5037, pid=expected_pre["adb_5037_pid"])
                    cleanup["steps"]["adb_5037_exit"] = {"passed": passed, "attempts": attempts, "snapshot": snapshot}
                    if not passed:
                        edge = "LEGACY_ADB_5037_DID_NOT_EXIT"
            if edge is None:
                record, _, stderr = M1.run_raw(
                    adb_prefix(config, 5038, include_serial=False) + ["kill-server"],
                    root=output_root / "legacy_cleanup", name="adb_5038_clean_stop",
                    timeout=config["maintenance"]["command_timeout_seconds"],
                )
                cleanup["steps"]["adb_5038_stop"] = record
                if not completed(record):
                    edge = "LEGACY_ADB_5038_STOP"
                else:
                    passed, attempts, snapshot = wait_server_gone(config, port=5038, pid=expected_pre["adb_5038_pid"])
                    cleanup["steps"]["adb_5038_exit"] = {"passed": passed, "attempts": attempts, "snapshot": snapshot}
                    if not passed:
                        edge = "LEGACY_ADB_5038_DID_NOT_EXIT"
            if edge is None:
                baseline = M1.runtime_snapshot(config)
                baseline_issues = clean_baseline_issues(baseline, excluded_pids=expected_pre["excluded_runtime_pids"])
                cleanup["clean_baseline"] = {"snapshot": baseline, "issues": baseline_issues, "passed": not baseline_issues}
                if baseline_issues:
                    edge = f"CLEAN_BASELINE:{baseline_issues[0]}"

            if edge is None:
                record, _, stderr = M1.run_raw(
                    adb_prefix(config, 5038, include_serial=False) + ["start-server"],
                    root=output_root / "launch", name="adb_5038_start",
                    timeout=config["maintenance"]["command_timeout_seconds"],
                )
                launch["adb_start"] = record
                if not completed(record):
                    edge = "ADB_5038_START"
            if edge is None:
                for index in range(1, 16):
                    snapshot = M1.runtime_snapshot(config)
                    forbidden = forbidden_5037_evidence(snapshot)
                    if forbidden:
                        edge = "FORBIDDEN_5037_AFTER_ADB_START"
                        break
                    if len(snapshot["listeners"]["5038"]) == 1:
                        launch["adb_ready"] = {"passed": True, "attempts": index, "snapshot": snapshot}
                        break
                    if index < 15:
                        time.sleep(1)
                else:
                    launch["adb_ready"] = {"passed": False, "attempts": 15, "snapshot": snapshot}
                    edge = "ADB_5038_NOT_READY"

            if edge is None:
                runtime = config["runtime"]
                runtime_log_root.mkdir(parents=True)
                environment = prepare_emulator_environment(
                    os.environ,
                    adb_port=runtime["adb_server_port"],
                    avd_home=str(REPOSITORY_ROOT / runtime["avd_home"]),
                    sdk_root=str(REPOSITORY_ROOT / "06_local_runtime/android/sdk"),
                )
                environment_evidence = {
                    name: environment.get(name)
                    for name in ("ANDROID_ADB_SERVER_PORT", "ANDROID_AVD_HOME", "ANDROID_SDK_ROOT", "ADB_SERVER_SOCKET", "ANDROID_ADB_SERVER_ADDRESS")
                }
                launch["environment_evidence"] = environment_evidence
                launcher = (REPOSITORY_ROOT / runtime["emulator_launcher"]).resolve()
                stdout_path = runtime_log_root / "emulator.live.stdout.bin"
                stderr_path = runtime_log_root / "emulator.live.stderr.bin"
                stdout_handle, stderr_handle = stdout_path.open("wb"), stderr_path.open("wb")
                try:
                    launcher_process = subprocess.Popen(
                        [str(launcher), *runtime["emulator_args"]], cwd=launcher.parent, env=environment,
                        stdout=stdout_handle, stderr=stderr_handle,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                finally:
                    stdout_handle.close(); stderr_handle.close()
                launch.update({"started": True, "launcher_spawn_pid": launcher_process.pid, "command": [str(launcher), *runtime["emulator_args"]], "runtime_log_root": config["runtime_log_root"]})
                wait_result = launch_wait(config, launcher_process.pid)
                launch["port_wait"] = wait_result
                if not wait_result["passed"]:
                    edge = wait_result["first_broken_edge"]

            if edge is None:
                after_start = M1.runtime_snapshot(config)
                expected = {key: after_start[key] for key in ("adb_pid", "launcher_pid", "qemu_pid")}
                issues = expected_runtime_issues(after_start, config, expected)
                if after_start["adb_pid"] == expected_pre["adb_5038_pid"] or after_start["launcher_pid"] == expected_pre["launcher_pid"] or after_start["qemu_pid"] == expected_pre["qemu_pid"]:
                    issues.append("PID_NOT_FRESH")
                if launcher_process is not None and after_start["launcher_pid"] != launcher_process.pid:
                    issues.append("LAUNCHER_SPAWN_PID_MISMATCH")
                launch["after_start"] = after_start
                launch["identity_issues"] = issues
                if issues:
                    edge = f"LAUNCH_IDENTITY:{issues[0]}"
            if edge is None:
                boot = boot_ready(config, output_root / "readiness" / "boot", expected)
                launch["boot"] = boot
                if not boot["passed"]:
                    edge = boot["first_broken_edge"]
            if edge is None:
                framework = framework_ready(config, output_root / "readiness" / "framework", expected)
                launch["framework"] = framework
                if not framework["passed"]:
                    edge = framework["first_broken_edge"]
            if edge is None:
                burn = burn_in(config, output_root / "burn_in", expected)
                if burn["passed"]:
                    status = "RUNTIME_STABLE_24_OF_24"
                else:
                    edge = burn["first_broken_edge"]
    except Exception as exc:
        if status != "OWNERSHIP_NOT_QUALIFIED":
            status = "RUNTIME_UNSTABLE"
        edge = edge or f"EXCEPTION:{type(exc).__name__}:{exc}"
        primary_error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}

    live_log_snapshots = {}
    log_errors = []
    if runtime_log_root.exists():
        for name in ("emulator.live.stdout.bin", "emulator.live.stderr.bin"):
            source = runtime_log_root / name
            if source.is_file():
                try:
                    live_log_snapshots[name] = M1.save_bytes(output_root / "launch" / f"{name}.terminal_snapshot.bin", source.read_bytes())
                except Exception as exc:
                    log_errors.append(f"{name}:{type(exc).__name__}:{exc}")
    final_snapshot = M1.runtime_snapshot(config)
    protected_after = {relative: M1.digest_path(REPOSITORY_ROOT / relative) for relative in config["protected_wip"]}
    terminal_issues = list(log_errors)
    if protected_after != protected_before:
        terminal_issues.append("PROTECTED_WIP_DRIFT")
    if status == "RUNTIME_STABLE_24_OF_24" and "expected" in locals():
        terminal_issues.extend(expected_runtime_issues(final_snapshot, config, expected))
    if terminal_issues:
        status = "RUNTIME_UNSTABLE" if status != "OWNERSHIP_NOT_QUALIFIED" else status
        edge = edge or f"TERMINAL:{terminal_issues[0]}"
    launch["live_log_snapshots"] = live_log_snapshots
    completion = {
        "schema_version": "role_binding_timing.infra_m2.completion.v1",
        "status": status,
        "first_broken_edge": edge,
        "started_at": started,
        "completed_at": utc_now(),
        "development_contaminated": True,
        "held_out_eligible": False,
        "generation_calls": 0,
        "model_tokens": 0,
        "primary_error": primary_error,
        "legacy_cleanup": cleanup,
        "launch": launch,
        "burn_in": burn,
        "final_snapshot": final_snapshot,
        "terminal_issues": terminal_issues,
        "protected_wip_before": protected_before,
        "protected_wip_after": protected_after,
        "protected_wip_unchanged": protected_before == protected_after == config["protected_wip"],
        "claim_evidence": {
            "exclusive_5038_registration": status == "RUNTIME_STABLE_24_OF_24",
            "runtime_stable": status == "RUNTIME_STABLE_24_OF_24",
            "a11y_authorized": status == "RUNTIME_STABLE_24_OF_24",
            "a11y_tested": False,
            "held_out_tested": False,
            "role_binding_hypothesis_tested": False,
        },
    }
    schema = json.loads((REPOSITORY_ROOT / config["schema"]).read_text(encoding="utf-8"))
    completion["schema_errors"] = [item.message for item in Draft202012Validator(schema).iter_errors(completion)]
    write_json_atomic(output_root / "maintenance_completion.json", completion)
    artifacts = []
    for path in sorted(output_root.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.json":
            artifacts.append({"path": path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": M1.digest_path(path)})
    write_json_atomic(output_root / "artifact_manifest.json", {"schema_version": "role_binding_timing.infra_m2.manifest.v1", "artifacts": artifacts})
    print(json.dumps({"status": status, "first_broken_edge": edge, "burn_in": f"{burn['passed_cycles']}/{burn['required_cycles']}", "elapsed_seconds": burn["elapsed_seconds"], "schema_errors": completion["schema_errors"]}, indent=2))
    return 0 if status == "RUNTIME_STABLE_24_OF_24" and not completion["schema_errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
