"""Run the frozen INFRA-M5 structural process-identity qualification chain."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from raven_m.role_binding_timing.infra_m3_log_lifecycle import create_live_root, seal_live_logs  # noqa: E402
from raven_m.role_binding_timing.infra_m4_terminal_accounting import PhaseJournal, atomic_write_json, safe_jsonable  # noqa: E402
from raven_m.role_binding_timing.infra_m5_process_identity import (  # noqa: E402
    ExecutableHashCache,
    ProcessIdentityMonitor,
    identity_key,
    process_index,
    runner_identity,
)


def load_script(name: str, filename: str) -> Any:
    path = PROJECT_ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"SCRIPT_DEPENDENCY_LOAD_FAILURE:{filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M4 = load_script("frozen_infra_m4_runner_for_m5", "run_role_binding_timing_infra_m4.py")
M2, B210, M1 = M4.M2, M4.B210, M4.M1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def verify_freeze(config: dict[str, Any], lock: dict[str, Any]) -> None:
    if config["generation_calls_authorized"] != 0 or config["generation_eligible"] is not False:
        raise RuntimeError("GENERATION_BOUNDARY")
    if lock.get("run_id") != config["run_id"] or lock.get("predecessor_audit_commit") != config["audit_commit"]:
        raise RuntimeError("LOCK_IDENTITY")
    for relative, expected in lock["files"].items():
        actual = M1.digest_path(REPOSITORY_ROOT / relative)
        if actual != expected:
            raise RuntimeError(f"FREEZE_HASH:{relative}:{actual}:{expected}")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=True).stdout.strip()
    tag = subprocess.run(["git", "rev-list", "-n", "1", config["freeze_tag"]], cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=True).stdout.strip()
    if head != tag:
        raise RuntimeError(f"FREEZE_TAG:{head}:{tag}")


def journal_start(journal: PhaseJournal, phase: str, details: Any = None) -> None:
    journal.record(phase=phase, event="start", status="RUNNING", details=details)


def journal_pass(journal: PhaseJournal, phase: str, details: Any = None) -> None:
    journal.record(phase=phase, event="end", status="PASS", details=details)


def journal_fail(journal: PhaseJournal, phase: str, edge: str, details: Any = None) -> None:
    if journal.first_edge() is None:
        journal.record(phase=phase, event="end", status="FAIL", first_broken_edge=edge, details=details)
    else:
        journal.record(phase=phase, event="end", status="SECONDARY_FAIL", details={"edge": edge, "evidence": details})


def check_identity(result: dict[str, Any]) -> None:
    if not result["passed"]:
        raise RuntimeError(f"PROCESS_IDENTITY:{result['gate']}:{result['issues'][0]}")


def snapshot_value(result: dict[str, Any]) -> dict[str, Any]:
    return json.loads(Path(result["snapshot"]["path"]).read_text(encoding="utf-8"))


def save(path: Path, value: Any) -> None:
    atomic_write_json(path, safe_jsonable(value), replace=False)


def run_commands(
    *, commands: dict[str, list[str]], root: Path, timeout: float,
) -> tuple[dict[str, Any], dict[str, bytes], dict[str, bytes]]:
    records, payloads, errors = {}, {}, {}
    for name, command in commands.items():
        record, stdout, stderr = M1.run_raw(command, root=root, name=name, timeout=timeout)
        records[name], payloads[name], errors[name] = record, stdout, stderr
    return records, payloads, errors


def boot_ready(
    config: dict[str, Any], root: Path, monitor: ProcessIdentityMonitor,
) -> dict[str, Any]:
    prefix = M2.adb_prefix(config, 5038)
    attempts = []
    edge = None
    for index in range(1, config["maintenance"]["boot_wait_attempts"] + 1):
        attempt_root = root / f"attempt_{index:02d}"
        before = monitor.capture(gate=f"boot_{index:02d}_before", phase="boot")
        if not before["passed"]:
            edge = f"PROCESS_IDENTITY:{before['issues'][0]}"
            attempt = {"index": index, "passed": False, "before_identity": before, "records": {}, "issues": [edge]}
            save(attempt_root / "attempt.json", attempt); attempts.append(attempt); break
        commands = {
            "devices": M2.adb_prefix(config, 5038, include_serial=False) + ["devices", "-l"],
            "get_state": prefix + ["get-state"],
            "boot_completed": prefix + ["shell", "getprop", "sys.boot_completed"],
        }
        records, payloads, errors = run_commands(commands=commands, root=attempt_root / "raw", timeout=15)
        after = monitor.capture(gate=f"boot_{index:02d}_after", phase="boot")
        issues = list(after["issues"])
        passed = (
            not issues and all(M2.strict_ok(records[name], errors[name]) for name in records)
            and config["runtime"]["device_serial"].encode() in payloads["devices"]
            and payloads["get_state"].strip() == b"device"
            and payloads["boot_completed"].strip() == b"1"
        )
        attempt = {"index": index, "passed": passed, "before_identity": before, "after_identity": after, "issues": issues, "records": records}
        save(attempt_root / "attempt.json", attempt); attempts.append(attempt)
        if issues:
            edge = f"PROCESS_IDENTITY:{issues[0]}"; break
        if passed:
            return {"passed": True, "first_broken_edge": None, "attempts": attempts}
        if index < config["maintenance"]["boot_wait_attempts"]:
            time.sleep(config["maintenance"]["boot_wait_interval_seconds"])
    return {"passed": False, "first_broken_edge": edge or "BOOT_NOT_READY_ON_5038", "attempts": attempts}


def framework_ready(
    config: dict[str, Any], root: Path, monitor: ProcessIdentityMonitor,
) -> dict[str, Any]:
    prefix = M2.adb_prefix(config, 5038)
    setup: dict[str, Any] = {}
    for name, args in (
        ("wake", ["shell", "input", "keyevent", "224"]),
        ("dismiss_keyguard", ["shell", "wm", "dismiss-keyguard"]),
        ("home", ["shell", "input", "keyevent", "3"]),
    ):
        before = monitor.capture(gate=f"framework_setup_{name}_before", phase="framework")
        if not before["passed"]:
            return {"passed": False, "first_broken_edge": f"PROCESS_IDENTITY:{before['issues'][0]}", "setup": setup, "attempts": []}
        record, _, stderr = M1.run_raw(prefix + args, root=root / "setup", name=name, timeout=15)
        after = monitor.capture(gate=f"framework_setup_{name}_after", phase="framework")
        setup[name] = {"record": record, "before_identity": before, "after_identity": after}
        if not after["passed"]:
            return {"passed": False, "first_broken_edge": f"PROCESS_IDENTITY:{after['issues'][0]}", "setup": setup, "attempts": []}
        if not M2.strict_ok(record, stderr):
            return {"passed": False, "first_broken_edge": f"FRAMEWORK_SETUP:{name}", "setup": setup, "attempts": []}

    attempts, consecutive = [], 0
    commands = {
        "package": ["shell", "service", "check", "package"],
        "window": ["shell", "service", "check", "window"],
        "activity": ["shell", "service", "check", "activity"],
        "power": ["shell", "dumpsys", "power"],
        "displays": ["shell", "dumpsys", "window", "displays"],
        "policy": ["shell", "dumpsys", "window", "policy"],
        "activities": ["shell", "dumpsys", "activity", "activities"],
    }
    for index in range(1, config["maintenance"]["framework_stable_attempts"] + 1):
        attempt_root = root / f"attempt_{index:02d}"
        before = monitor.capture(gate=f"framework_{index:02d}_before", phase="framework")
        if not before["passed"]:
            return {"passed": False, "first_broken_edge": f"PROCESS_IDENTITY:{before['issues'][0]}", "setup": setup, "attempts": attempts}
        command_map = {name: prefix + args for name, args in commands.items()}
        records, payloads, errors = run_commands(commands=command_map, root=attempt_root / "raw", timeout=15)
        after = monitor.capture(gate=f"framework_{index:02d}_after", phase="framework")
        identity_issues = list(after["issues"])
        services = {name: M2.parse_framework_service(payloads[name], name) for name in ("package", "window", "activity")}
        state = M2.parse_runtime_state(
            payloads["power"].decode("utf-8", errors="replace"),
            payloads["displays"].decode("utf-8", errors="replace"),
            payloads["policy"].decode("utf-8", errors="replace"),
        )
        passed = (
            not identity_issues and all(M2.strict_ok(records[name], errors[name]) for name in records)
            and all(services.values()) and all(state.values()) and bool(payloads["activities"].strip())
        )
        consecutive = consecutive + 1 if passed else 0
        attempt = {"index": index, "passed": passed, "consecutive": consecutive, "before_identity": before, "after_identity": after, "identity_issues": identity_issues, "services": services, "runtime_state": state, "records": records}
        save(attempt_root / "attempt.json", attempt); attempts.append(attempt)
        if identity_issues:
            return {"passed": False, "first_broken_edge": f"PROCESS_IDENTITY:{identity_issues[0]}", "setup": setup, "attempts": attempts}
        if consecutive >= config["maintenance"]["framework_stable_required_consecutive"]:
            return {"passed": True, "first_broken_edge": None, "setup": setup, "attempts": attempts}
        if index < config["maintenance"]["framework_stable_attempts"]:
            time.sleep(config["maintenance"]["framework_stable_interval_seconds"])
    return {"passed": False, "first_broken_edge": "FRAMEWORK_NOT_STABLE", "setup": setup, "attempts": attempts}


def burn_in(config: dict[str, Any], root: Path, monitor: ProcessIdentityMonitor) -> dict[str, Any]:
    prefix = M2.adb_prefix(config, 5038)
    burn = config["burn_in"]
    started = time.monotonic()
    records_out, edge = [], None
    commands = {
        "get_state": ["get-state"], "boot_completed": ["shell", "getprop", "sys.boot_completed"],
        "service_package": ["shell", "service", "check", "package"],
        "service_window": ["shell", "service", "check", "window"],
        "service_activity": ["shell", "service", "check", "activity"],
        "wake": ["shell", "input", "keyevent", "224"], "dismiss_keyguard": ["shell", "wm", "dismiss-keyguard"],
        "home": ["shell", "input", "keyevent", "3"], "power": ["shell", "dumpsys", "power"],
        "displays": ["shell", "dumpsys", "window", "displays"], "policy": ["shell", "dumpsys", "window", "policy"],
        "activities": ["shell", "dumpsys", "activity", "activities"], "screenshot": ["exec-out", "screencap", "-p"],
    }
    for index in range(1, burn["cycles"] + 1):
        cell_root = root / f"cycle_{index:02d}"
        before = monitor.capture(gate=f"burn_{index:02d}_before", phase="burn_in")
        issues = list(before["issues"])
        command_records, payloads, errors = {}, {}, {}
        if not issues:
            command_records, payloads, errors = run_commands(
                commands={name: prefix + args for name, args in commands.items()},
                root=cell_root / "raw", timeout=burn["command_timeout_seconds"],
            )
        after = monitor.capture(gate=f"burn_{index:02d}_after", phase="burn_in")
        issues.extend(after["issues"])
        services, state, screenshot = {}, {}, None
        if not issues and len(command_records) == len(commands):
            for name in command_records:
                if not M2.strict_ok(command_records[name], errors[name]):
                    issues.append(f"COMMAND:{name}"); break
        if not issues:
            services = {name: M2.parse_framework_service(payloads[f"service_{name}"], name) for name in ("package", "window", "activity")}
            state = M2.parse_runtime_state(payloads["power"].decode("utf-8", errors="replace"), payloads["displays"].decode("utf-8", errors="replace"), payloads["policy"].decode("utf-8", errors="replace"))
            if payloads["get_state"].strip() != b"device": issues.append("DEVICE_STATE")
            if payloads["boot_completed"].strip() != b"1": issues.append("BOOT_STATE")
            if not all(services.values()): issues.append("FRAMEWORK_SERVICES")
            if not all(state.values()): issues.append("POWER_DISPLAY_KEYGUARD")
            if not payloads["activities"].strip(): issues.append("ACTIVITY_DUMP_EMPTY")
            try:
                screenshot = M2.validate_png(payloads["screenshot"], burn["expected_screenshot_size"])
            except Exception as exc:
                issues.append(f"SCREENSHOT:{type(exc).__name__}:{exc}")
        passed = not issues
        if not passed:
            edge = f"CYCLE_{index:02d}:{issues[0]}"
        cell = {"index": index, "passed": passed, "before_identity": before, "after_identity": after, "issues": issues, "services": services, "runtime_state": state, "screenshot": screenshot, "records": command_records}
        save(cell_root / "cycle_result.json", cell); records_out.append(cell)
        if not passed: break
        if index < burn["cycles"]: time.sleep(burn["cycle_interval_seconds"])
    elapsed = time.monotonic() - started
    passed = len(records_out) == burn["cycles"] and all(item["passed"] for item in records_out) and elapsed >= burn["minimum_elapsed_seconds"]
    if len(records_out) == burn["cycles"] and all(item["passed"] for item in records_out) and elapsed < burn["minimum_elapsed_seconds"]:
        edge = "MINIMUM_BURN_IN_DURATION"
    return {"passed": passed, "first_broken_edge": edge, "required_cycles": burn["cycles"], "completed_cycles": len(records_out), "passed_cycles": sum(bool(item["passed"]) for item in records_out), "elapsed_seconds": elapsed, "records": records_out}


def a11y_stages(
    config: dict[str, Any], root: Path, monitor: ProcessIdentityMonitor, journal: PhaseJournal,
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = {"authorized": True, "passed": False, "first_broken_edge": None, "settings": {"required": 3, "completed": 0, "passed": 0, "records": []}, "grid": {"required": 12, "completed": 0, "passed": 0, "records": []}, "rebind": {"passed": False}}
    session = {"env": None, "raw_adb": None, "sidecar_port": None, "adb_pid": None, "emulator_pid": None, "last_package": None}
    try:
        check_identity(monitor.capture(gate="a11y_initialize_before", phase="settings"))
        managed = B210.ManagedAdb(binary=REPOSITORY_ROOT / config["runtime"]["adb_binary"], expected_hash=config["runtime"]["adb_binary_sha256"], port=5038, serial=config["runtime"]["device_serial"])
        raw_adb = B210.RawAdb(managed); session["raw_adb"] = raw_adb; session["adb_pid"] = managed.owner_pid
        emulator_pid, emulator_record = B210.emulator_identity(config); session["emulator_pid"] = emulator_pid
        result["runtime_before"] = {"adb_pid": managed.owner_pid, "emulator_grpc_pid": emulator_pid, "emulator_process": emulator_record}
        apk_record, apk_raw, _ = raw_adb.run(["shell", "pm", "path", config["accessibility_service"]["package"]], root=root / "preflight", name="forwarder_pm_path", timeout=config["sampling"]["command_timeout_seconds"])
        apk_path = apk_raw.decode("utf-8", errors="replace").strip().split("package:", 1)[-1]
        hash_record, hash_raw, _ = raw_adb.run(["shell", "sha256sum", apk_path], root=root / "preflight", name="forwarder_apk_sha256sum", timeout=config["sampling"]["command_timeout_seconds"])
        apk_hash = hash_raw.decode("ascii", errors="replace").strip().split()[0] if hash_raw.strip() else ""
        if apk_record["returncode"] != 0 or hash_record["returncode"] != 0 or apk_hash != config["accessibility_service"]["installed_apk_sha256"]:
            raise RuntimeError(f"FORWARDER_APK_IDENTITY:{apk_hash}")
        rebind = B210.rebind_forwarder(raw_adb=raw_adb, root=root / "lifecycle_rebind", config=config, expected_adb_pid=managed.owner_pid)
        result["rebind"] = rebind
        if not rebind["passed"]: raise RuntimeError(rebind["first_broken_edge"])
        check_identity(monitor.capture(gate="a11y_rebind_after", phase="settings"))
        env = B210.load_explicit_guest_sidecar_env(adb_path=str((REPOSITORY_ROOT / config["runtime"]["adb_binary"]).resolve()), adb_server_port=5038, console_port=5554, grpc_port=8554)
        session["env"] = env
        runtime_identity = B210.sidecar_runtime_identity(env); session["sidecar_port"] = runtime_identity["sidecar_host_port"]
        result["sidecar_runtime"] = runtime_identity
        if len(runtime_identity["broadcasts"]) != 3 or any(item["status"] != 1 for item in runtime_identity["broadcasts"]): raise RuntimeError("EXPLICIT_BROADCAST_AUDIT")
        if B210.listener_pids(session["sidecar_port"]) != [os.getpid()]: raise RuntimeError("SIDECAR_LISTENER_IDENTITY")
        check_identity(monitor.capture(gate="a11y_env_after", phase="settings"))

        journal_start(journal, "settings")
        check_identity(monitor.capture(gate="settings_launch_before", phase="settings"))
        launch = B210.launch_and_wait(raw_adb=raw_adb, root=root / "settings_qualification/launch", app=config["settings_scene"], config=config)
        session["last_package"] = config["settings_scene"]["package"]; result["settings_launch"] = launch
        check_identity(monitor.capture(gate="settings_launch_after", phase="settings"))
        if not launch["passed"]: raise RuntimeError("SETTINGS_FOREGROUND")
        settings_records = []
        for index in range(1, 4):
            check_identity(monitor.capture(gate=f"settings_observation_{index:02d}_before", phase="settings"))
            observation = B210.capture_observation(env=env, raw_adb=raw_adb, root=root / f"settings_qualification/observation_{index:02d}", config=config, app=config["settings_scene"], foreground=launch["witnesses"], expected_adb_pid=managed.owner_pid, expected_emulator_grpc_pid=emulator_pid, expected_forwarder_pid=rebind["forwarder_pid"])
            check_identity(monitor.capture(gate=f"settings_observation_{index:02d}_after", phase="settings"))
            settings_records.append(observation)
            result["settings"] = {"required": 3, "completed": len(settings_records), "passed": sum(bool(item["passed"]) for item in settings_records), "records": settings_records}
            if not observation["passed"]: raise RuntimeError(f"SETTINGS_OBSERVATION_{index:02d}:{observation['issues'][0] if observation['issues'] else 'UNKNOWN'}")
        journal_pass(journal, "settings", {"passed": 3, "required": 3})

        journal_start(journal, "grid")
        grid_records = []
        for round_index in range(1, config["grid"]["rounds"] + 1):
            for app in config["grid"]["apps"]:
                cell_id = f"R{round_index:02d}-{app['dev_app_id']}"; cell_root = root / "dev_grid" / cell_id
                check_identity(monitor.capture(gate=f"grid_{cell_id}_before", phase="grid"))
                launched = B210.launch_and_wait(raw_adb=raw_adb, root=cell_root / "launch", app=app, config=config)
                session["last_package"] = app["package"]
                if not launched["passed"]:
                    cell = {"cell_id": cell_id, "passed": False, "app": app, "launch": launched, "issues": ["FOREGROUND"]}
                else:
                    observation = B210.capture_observation(env=env, raw_adb=raw_adb, root=cell_root / "observation", config=config, app=app, foreground=launched["witnesses"], expected_adb_pid=managed.owner_pid, expected_emulator_grpc_pid=emulator_pid, expected_forwarder_pid=rebind["forwarder_pid"])
                    cell = {"cell_id": cell_id, "passed": observation["passed"], "app": app, "launch": launched, "observation": observation, "issues": observation["issues"]}
                identity_after = monitor.capture(gate=f"grid_{cell_id}_after", phase="grid"); check_identity(identity_after)
                cell["identity_after"] = identity_after; save(cell_root / "cell_result.json", cell)
                grid_records.append(cell); result["grid"] = {"required": 12, "completed": len(grid_records), "passed": sum(bool(item["passed"]) for item in grid_records), "records": grid_records}
                if not cell["passed"]: raise RuntimeError(f"GRID:{cell_id}:{cell['issues'][0] if cell['issues'] else 'UNKNOWN'}")
        result["passed"] = len(grid_records) == 12 and all(item["passed"] for item in grid_records)
        if not result["passed"]: raise RuntimeError("GRID_CARDINALITY")
        journal_pass(journal, "grid", {"passed": 12, "required": 12})
        return result, session
    except Exception as exc:
        result["first_broken_edge"] = str(exc)
        phase = "grid" if any(item["event"] == "start" and item["phase"] == "grid" for item in journal.read_entries()) else "settings"
        journal_fail(journal, phase, str(exc), exc)
        return result, session


def a11y_cleanup(config: dict[str, Any], root: Path, session: dict[str, Any]) -> dict[str, Any]:
    return B210.cleanup(env=session.get("env"), raw_adb=session.get("raw_adb"), root=root / "a11y", config=config, last_package=session.get("last_package"), sidecar_port=session.get("sidecar_port"), expected_adb_pid=session.get("adb_pid"), expected_emulator_grpc_pid=session.get("emulator_pid"))


def process_is_same(record: dict[str, Any]) -> bool:
    pid = int(record["pid"])
    try:
        import psutil
        process = psutil.Process(pid)
        return abs(process.create_time() - float(record["create_time"])) < 0.0005
    except Exception:
        return False


def terminal_cleanup(
    config: dict[str, Any], root: Path, monitor: ProcessIdentityMonitor,
) -> tuple[dict[str, Any], dict[str, Any]]:
    result: dict[str, Any] = {"steps": {}, "issues": []}
    pre = monitor.capture(gate="cleanup_before_stop", phase="cleanup"); result["pre_identity"] = pre
    if not pre["passed"]: result["issues"].append(f"PRE_CLEANUP_IDENTITY:{pre['issues'][0]}")
    core = monitor.policy.core
    pre_snapshot = snapshot_value(pre)
    emulator_registered = all(role in core for role in ("emulator_launcher", "qemu"))
    emulator_ports = any(pre_snapshot["listeners"][str(port)] for port in (5554, 5555, 8554))
    emulator_owned = (
        emulator_registered
        and all(process_is_same(core[role]) for role in ("emulator_launcher", "qemu"))
        and all(pre_snapshot["listeners"][str(port)] == [core["qemu"]["pid"]] for port in (5554, 5555, 8554))
    )
    if emulator_ports and not emulator_owned:
        result["issues"].append("EMULATOR_PRESENT_WITHOUT_QUALIFIED_IDENTITY")
    if emulator_owned:
        record, _, _ = M1.run_raw(M2.adb_prefix(config, 5038) + ["emu", "kill"], root=root, name="emulator_clean_stop", timeout=config["maintenance"]["command_timeout_seconds"])
        result["steps"]["emulator_stop"] = record
        if not M2.completed(record): result["issues"].append("EMULATOR_CLEAN_STOP_COMMAND")
    else:
        result["steps"]["emulator_stop"] = {"not_run": True, "reason": "not_present" if not emulator_ports else "identity_not_qualified"}
    attempts = []
    if emulator_owned and M2.completed(result["steps"]["emulator_stop"]):
        for index in range(1, config["maintenance"]["stop_wait_attempts"] + 1):
            observed = monitor.capture(gate=f"cleanup_emulator_wait_{index:02d}", phase="cleanup", mode="discovery")
            snapshot = snapshot_value(observed)
            gone = (
                not process_is_same(core["emulator_launcher"]) and not process_is_same(core["qemu"])
                and all(not snapshot["listeners"][str(port)] for port in (5554, 5555, 8554))
            )
            attempts.append({"index": index, "gone": gone, "identity": observed})
            if gone: break
            if index < config["maintenance"]["stop_wait_attempts"]: time.sleep(config["maintenance"]["stop_wait_interval_seconds"])
        if not attempts[-1]["gone"]: result["issues"].append("EMULATOR_DID_NOT_EXIT")
    result["steps"]["emulator_wait"] = attempts
    current = monitor.capture(gate="cleanup_before_adb_stop", phase="cleanup", mode="discovery")
    snapshot = snapshot_value(current)
    adb_registered = "adb_server" in core
    adb_present = bool(snapshot["listeners"]["5038"])
    adb_owned = (
        adb_registered
        and process_is_same(core["adb_server"])
        and snapshot["listeners"]["5038"] == [core["adb_server"]["pid"]]
    )
    remaining_emulator_ports = any(snapshot["listeners"][str(port)] for port in (5554, 5555, 8554))
    if adb_present and not adb_owned:
        result["issues"].append("ADB_PRESENT_WITHOUT_QUALIFIED_IDENTITY")
    if adb_owned and not remaining_emulator_ports:
        record, _, _ = M1.run_raw(M2.adb_prefix(config, 5038, include_serial=False) + ["kill-server"], root=root, name="adb_5038_clean_stop", timeout=config["maintenance"]["command_timeout_seconds"])
        result["steps"]["adb_stop"] = record
        if not M2.completed(record): result["issues"].append("ADB_CLEAN_STOP_COMMAND")
    elif adb_owned:
        result["issues"].append("ADB_STOP_BLOCKED_BY_EMULATOR_RESIDUE")
        result["steps"]["adb_stop"] = {"not_run": True, "reason": "emulator_residue"}
    else:
        result["steps"]["adb_stop"] = {"not_run": True, "reason": "not_present" if not adb_present else "identity_not_qualified"}
    adb_attempts = []
    if adb_owned and not remaining_emulator_ports and M2.completed(result["steps"]["adb_stop"]):
        for index in range(1, config["maintenance"]["stop_wait_attempts"] + 1):
            observed = monitor.capture(gate=f"cleanup_adb_wait_{index:02d}", phase="cleanup", mode="discovery")
            snapshot = snapshot_value(observed)
            gone = not process_is_same(core["adb_server"]) and not snapshot["listeners"]["5038"]
            adb_attempts.append({"index": index, "gone": gone, "identity": observed})
            if gone: break
            if index < config["maintenance"]["stop_wait_attempts"]: time.sleep(config["maintenance"]["stop_wait_interval_seconds"])
        if not adb_attempts[-1]["gone"]: result["issues"].append("ADB_DID_NOT_EXIT")
    result["steps"]["adb_wait"] = adb_attempts
    history = monitor.stop_history()
    result["history_completion"] = history
    final = monitor.capture(gate="cleanup_final", phase="cleanup", mode="cleanup_after_exit")
    result["final_identity"] = final
    if not final["passed"]: result["issues"].append(f"FINAL_PROCESS_IDENTITY:{final['issues'][0]}")
    snapshot = snapshot_value(final)
    if any(snapshot["listeners"][str(port)] for port in (5037, 5038, 5554, 5555, 8554)):
        result["issues"].append("FINAL_PORT_RESIDUE")
    result["issues"] = list(dict.fromkeys(result["issues"])); result["passed"] = not result["issues"]
    return result, history


def status_from_edge(edge: str | None, *, a11y_authorized: bool) -> str:
    if edge is None: return "PASS_12_OF_12_DEV"
    if edge.startswith("PROCESS_IDENTITY") or "PROCESS_IDENTITY" in edge: return "PROCESS_IDENTITY_FAILED"
    if edge.startswith("BASELINE") or edge.startswith("OWNERSHIP"): return "OWNERSHIP_NOT_QUALIFIED"
    if a11y_authorized and any(word in edge for word in ("SETTINGS", "GRID", "FORWARDER", "SIDECAR")): return "A11Y_QUALIFICATION_FAILED"
    if edge.startswith("LOG_SEAL") or edge.startswith("CLEANUP"): return "LOG_SEAL_FAILED"
    return "RUNTIME_UNSTABLE"


def invoke_finalizer(config: dict[str, Any], output_root: Path, status: str) -> dict[str, Any]:
    command = [str((REPOSITORY_ROOT / config["runtime"]["python"]).resolve()), str((REPOSITORY_ROOT / config["terminal_accounting"]["independent_finalizer"]).resolve()), "--output-root", str(output_root.resolve()), "--schema", str((REPOSITORY_ROOT / config["schema"]).resolve()), "--run-id", config["run_id"], "--status", status]
    completed = subprocess.run(command, cwd=REPOSITORY_ROOT, capture_output=True, timeout=60)
    return {"command": command, "returncode": completed.returncode, "stdout": completed.stdout.decode("utf-8", errors="replace"), "stderr": completed.stderr.decode("utf-8", errors="replace")}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--config", required=True); args = parser.parse_args()
    config = json.loads((REPOSITORY_ROOT / args.config).read_text(encoding="utf-8")); lock = json.loads((REPOSITORY_ROOT / config["lock"]).read_text(encoding="utf-8")); verify_freeze(config, lock)
    output_root = REPOSITORY_ROOT / config["output_root"]
    if output_root.exists(): raise RuntimeError("M5_OUTPUT_ROOT_NOT_FRESH")
    output_root.mkdir(parents=True); (output_root / ".gitattributes").write_text("**/*.bin -text\n", encoding="ascii")
    journal = PhaseJournal(output_root / "phase_journal")
    protected_before = {name: M1.digest_path(REPOSITORY_ROOT / name) for name in config["protected_wip"]}
    if protected_before != config["protected_wip"]: raise RuntimeError("PROTECTED_WIP_DRIFT")
    run_identity = runner_identity(ExecutableHashCache())
    if Path(run_identity["exe"]).resolve() != Path(config["runtime"]["runner_process_executable"]).resolve() or run_identity["exe_sha256"] != config["runtime"]["runner_process_executable_sha256"]: raise RuntimeError(f"RUNNER_PROCESS_IDENTITY:{run_identity}")
    monitor = ProcessIdentityMonitor(root=output_root / "process_identity", config=config, runner_record=run_identity)
    started = utc_now(); current_phase = "launch"; live_root = None; parent_handles_closed = False
    runtime_record: dict[str, Any] = {"runner_identity": run_identity, "steps": {}}
    burn = {"passed": False, "first_broken_edge": "NOT_RUN", "required_cycles": 24, "completed_cycles": 0, "passed_cycles": 0, "elapsed_seconds": 0.0, "records": []}
    a11y = {"authorized": False, "passed": False, "first_broken_edge": "NOT_AUTHORIZED", "settings": {"required": 3, "completed": 0, "passed": 0, "records": []}, "grid": {"required": 12, "completed": 0, "passed": 0, "records": []}}
    session: dict[str, Any] = {}; primary_error = None; cleanup_result = {"passed": False, "issues": ["NOT_RUN"]}; history_result = {}; log_seal = {"passed": False, "records": [], "temporary_root_removed": False, "issues": ["NOT_RUN"]}
    try:
        journal_start(journal, "launch")
        baseline = monitor.capture(gate="prelaunch_baseline", phase="launch", mode="baseline"); runtime_record["baseline"] = baseline; check_identity(baseline)
        monitor.start_history()
        logs = config["log_lifecycle"]; live_root = create_live_root(temp_parent=Path(logs["temp_parent"]), repository_root=REPOSITORY_ROOT, forbidden_roots=[Path(item) for item in logs["forbidden_roots"]], prefix=logs["temp_prefix"])
        runtime_record["live_log_root"] = {"path": str(live_root), "outside_repository": True, "immutable_input": False}
        record, _, _ = M1.run_raw(M2.adb_prefix(config, 5038, include_serial=False) + ["start-server"], root=output_root / "launch", name="adb_5038_start", timeout=config["maintenance"]["command_timeout_seconds"]); runtime_record["steps"]["adb_start"] = record
        if not M2.completed(record): raise RuntimeError("ADB_5038_START")
        adb_discovery = monitor.capture(gate="adb_server_discovery", phase="launch", mode="discovery"); check_identity(adb_discovery)
        adb_snapshot = snapshot_value(adb_discovery)
        if len(adb_snapshot["listeners"]["5038"]) != 1: raise RuntimeError("ADB_5038_NOT_READY")
        adb_pid = adb_snapshot["listeners"]["5038"][0]
        monitor.register_core_from_snapshot(role="adb_server", snapshot_path=Path(adb_discovery["snapshot"]["path"]), pid=adb_pid)
        check_identity(monitor.capture(gate="adb_server_registered", phase="launch"))
        runtime = config["runtime"]; environment = M2.prepare_emulator_environment(os.environ, adb_port=5038, avd_home=str(REPOSITORY_ROOT / runtime["avd_home"]), sdk_root=str(REPOSITORY_ROOT / "06_local_runtime/android/sdk")); launcher = (REPOSITORY_ROOT / runtime["emulator_launcher"]).resolve()
        stdout_handle = (live_root / logs["live_log_names"][0]).open("xb"); stderr_handle = (live_root / logs["live_log_names"][1]).open("xb")
        try:
            launcher_process = subprocess.Popen([str(launcher), *runtime["emulator_args"]], cwd=launcher.parent, env=environment, stdout=stdout_handle, stderr=stderr_handle, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        finally:
            stdout_handle.close(); stderr_handle.close(); parent_handles_closed = True
        runtime_record["steps"]["emulator_start"] = {"command": [str(launcher), *runtime["emulator_args"]], "pid": launcher_process.pid, "environment": {name: environment.get(name) for name in ("ANDROID_ADB_SERVER_PORT", "ADB_SERVER_SOCKET", "ANDROID_ADB_SERVER_ADDRESS")}, "parent_handles_closed": True}
        launcher_registered = qemu_registered = False; launch_attempts = []
        for index in range(1, config["maintenance"]["launch_wait_attempts"] + 1):
            observed = monitor.capture(gate=f"launch_discovery_{index:03d}", phase="launch", mode="discovery"); check_identity(observed); snap = snapshot_value(observed); by_pid = process_index(snap["structural_processes"])
            if not launcher_registered and launcher_process.pid in by_pid:
                monitor.register_core_from_snapshot(role="emulator_launcher", snapshot_path=Path(observed["snapshot"]["path"]), pid=launcher_process.pid); launcher_registered = True
            if not qemu_registered and len(snap["listeners"]["8554"]) == 1:
                monitor.register_core_from_snapshot(role="qemu", snapshot_path=Path(observed["snapshot"]["path"]), pid=snap["listeners"]["8554"][0]); qemu_registered = True
            ready = launcher_registered and qemu_registered and snap["listeners"]["5038"] == [adb_pid] and all(len(snap["listeners"][str(port)]) == 1 for port in (5554, 5555, 8554))
            launch_attempts.append({"index": index, "ready": ready, "identity": observed})
            if ready: break
            if index < config["maintenance"]["launch_wait_attempts"]: time.sleep(config["maintenance"]["launch_wait_interval_seconds"])
        runtime_record["steps"]["launch_discovery"] = launch_attempts
        if not launch_attempts[-1]["ready"]: raise RuntimeError("EMULATOR_PORTS_NOT_READY")
        launch_final = monitor.capture(gate="launch_qualified", phase="launch"); runtime_record["launch_identity"] = launch_final; check_identity(launch_final)
        journal_pass(journal, "launch", {"core": {role: identity_key(value) for role, value in monitor.policy.core.items()}})

        current_phase = "boot"; journal_start(journal, "boot"); boot = boot_ready(config, output_root / "readiness/boot", monitor); runtime_record["boot"] = boot
        if not boot["passed"]: raise RuntimeError(boot["first_broken_edge"])
        journal_pass(journal, "boot")
        current_phase = "framework"; journal_start(journal, "framework"); framework = framework_ready(config, output_root / "readiness/framework", monitor); runtime_record["framework"] = framework
        if not framework["passed"]: raise RuntimeError(framework["first_broken_edge"])
        journal_pass(journal, "framework")
        current_phase = "burn_in"; journal_start(journal, "burn_in"); burn = burn_in(config, output_root / "burn_in", monitor)
        if not burn["passed"]: raise RuntimeError(burn["first_broken_edge"])
        journal_pass(journal, "burn_in", {"cycles": burn["passed_cycles"], "elapsed_seconds": burn["elapsed_seconds"]})
        current_phase = "settings"; a11y, session = a11y_stages(config, output_root / "post_burn_in_a11y", monitor, journal)
        if not a11y["passed"]: raise RuntimeError(a11y["first_broken_edge"] or "A11Y_UNKNOWN")
    except Exception as exc:
        primary_error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        if journal.first_edge() is None: journal_fail(journal, current_phase, str(exc), primary_error)

    journal_start(journal, "cleanup"); a11y_clean = {"passed": True, "not_created": True}
    try:
        if session: a11y_clean = a11y_cleanup(config, output_root / "terminal_cleanup", session)
        cleanup_result, history_result = terminal_cleanup(config, output_root / "terminal_cleanup", monitor); cleanup_result["a11y"] = a11y_clean
        if not a11y_clean.get("passed"): cleanup_result["issues"].append(f"A11Y_CLEANUP:{a11y_clean.get('issues')}"); cleanup_result["passed"] = False
        if not cleanup_result["passed"]: raise RuntimeError(cleanup_result["issues"][0])
        journal_pass(journal, "cleanup")
    except Exception as exc:
        if monitor._history_started:
            try: history_result = monitor.stop_history()
            except Exception as history_exc: history_result = {"error": f"{type(history_exc).__name__}:{history_exc}"}
        cleanup_result = {**cleanup_result, "passed": False, "a11y": a11y_clean, "exception": safe_jsonable(exc), "history": history_result}
        journal_fail(journal, "cleanup", f"CLEANUP:{type(exc).__name__}:{exc}", exc)

    journal_start(journal, "seal")
    try:
        if live_root is None:
            log_seal = {"passed": True, "records": [], "temporary_root_removed": True, "issues": [], "no_live_logs_created": True}
        else:
            if not cleanup_result.get("passed"): raise RuntimeError("RUNTIME_NOT_CLEAN_FOR_SEAL")
            records = seal_live_logs(live_root=live_root, result_root=output_root / config["log_lifecycle"]["sealed_result_subdir"], names=config["log_lifecycle"]["live_log_names"], repository_root=REPOSITORY_ROOT, forbidden_roots=[Path(item) for item in config["log_lifecycle"]["forbidden_roots"]], required_temp_parent=Path(config["log_lifecycle"]["temp_parent"]), owners_gone=True, parent_handles_closed=parent_handles_closed)
            shutil.rmtree(live_root); log_seal = {"passed": True, "records": records, "temporary_root_removed": not live_root.exists(), "issues": []}
        journal_pass(journal, "seal")
    except Exception as exc:
        log_seal = {"passed": False, "records": [], "temporary_root_removed": False, "issues": [f"{type(exc).__name__}:{exc}"], "external_live_root": str(live_root) if live_root else None}; journal_fail(journal, "seal", f"LOG_SEAL:{type(exc).__name__}:{exc}", exc)

    protected_after = {name: M1.digest_path(REPOSITORY_ROOT / name) for name in config["protected_wip"]}
    if protected_after != protected_before: journal_fail(journal, "seal", "PROTECTED_WIP_DRIFT", {"before": protected_before, "after": protected_after})
    edge = journal.first_edge(); status = status_from_edge(edge, a11y_authorized=a11y["authorized"])
    process_identity = {"baseline_count": len(monitor.policy.baseline), "core": {role: value for role, value in monitor.policy.core.items()}, "history": history_result, "snapshot_count": monitor.sequence, "first_failure_path": str(monitor.first_failure) if monitor.first_failure.exists() else None, "qualified": edge is None and cleanup_result.get("passed")}
    rich = {"started_at": started, "development_contaminated": True, "held_out_eligible": False, "primary_error": primary_error, "process_identity": process_identity, "runtime": runtime_record, "burn_in": burn, "a11y": a11y, "cleanup": cleanup_result, "log_seal": log_seal, "protected_wip_before": protected_before, "protected_wip_after": protected_after, "protected_wip_unchanged": protected_before == protected_after == config["protected_wip"], "claim_evidence": {"process_identity_qualified": process_identity["qualified"], "exclusive_5038_registration": all(role in monitor.policy.core for role in ("adb_server", "emulator_launcher", "qemu")), "burn_in_qualified": bool(burn["passed"]), "a11y_tested": bool(a11y["authorized"]), "a11y_qualified": bool(a11y["passed"]), "v0_3_preparation_authorized": status == "PASS_12_OF_12_DEV", "held_out_tested": False, "role_binding_hypothesis_tested": False}}
    atomic_write_json(output_root / "terminal_input.json", safe_jsonable(rich), replace=False)
    finalizer = invoke_finalizer(config, output_root, status); print(json.dumps(finalizer, ensure_ascii=False, indent=2))
    completion = json.loads((output_root / "qualification_completion.json").read_text(encoding="utf-8")); validation = json.loads((output_root / "terminal_validation.json").read_text(encoding="utf-8"))
    print(json.dumps({"status": completion["status"], "first_broken_edge": completion["first_broken_edge"], "process_snapshots": monitor.sequence, "burn_in": f"{burn['passed_cycles']}/24", "settings": f"{a11y['settings']['passed']}/3", "grid": f"{a11y['grid']['passed']}/12", "cleanup": cleanup_result.get("passed"), "log_seal": log_seal.get("passed"), "terminal_valid": validation["passed"]}, indent=2))
    return 0 if completion["status"] == "PASS_12_OF_12_DEV" and validation["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
