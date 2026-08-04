"""Collect the frozen zero-model Phase-B2 snapshot candidate pool once."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
LOCAL_RUNTIME = REPOSITORY_ROOT / "06_local_runtime"
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(LOCAL_RUNTIME / "scripts"))
sys.path.insert(0, str(REPOSITORY_ROOT / "03_code" / "third_party" / "android_world"))

import androidworld_compat  # noqa: E402,F401
from android_world.env import adb_utils, device_constants  # noqa: E402
from android_world.task_evals.information_retrieval import task_app_utils  # noqa: E402
from android_world.task_evals.common_validators import sms_validators  # noqa: E402
from android_world.task_evals.single.calendar import calendar_utils  # noqa: E402
from android_world.task_evals.utils import sqlite_schema_utils, sqlite_utils  # noqa: E402
from android_world.utils import contacts_utils, file_utils  # noqa: E402
from raven_m.eest_ac.runtime_v0_2_2 import load_and_setup_env  # noqa: E402
from raven_m.role_binding_timing.collection_v0_2 import (  # noqa: E402
    build_oracle,
    parse_ui_tree,
    resolve_exact_item,
    sha256_bytes,
    sha256_path,
    validate_collection_config,
    write_json,
)


PROTOCOL_FREEZE_TAG = "role-binding-timing-phase-b2-v0.2-protocol-freeze-20260804"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run(command: list[str], *, timeout: float = 30, binary: bool = False) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=not binary,
            check=False,
            timeout=timeout,
        )
        stdout = result.stdout if binary else result.stdout.strip()
        stderr = result.stderr if binary else result.stderr.strip()
        return {
            "command": command,
            "returncode": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": False,
            "wall_time_seconds": time.monotonic() - started,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "returncode": None,
            "stdout": exc.stdout or (b"" if binary else ""),
            "stderr": exc.stderr or (b"" if binary else ""),
            "timed_out": True,
            "wall_time_seconds": time.monotonic() - started,
        }


class ExplicitAdb:
    def __init__(self, path: Path, port: int, serial: str) -> None:
        if port != 5038:
            raise ValueError("Phase B2 forbids any ADB port except 5038.")
        self.path = path.resolve()
        self.port = port
        self.serial = serial

    def host(self, args: list[str], timeout: float = 30) -> dict[str, Any]:
        return _run([str(self.path), "-P", str(self.port), *args], timeout=timeout)

    def device(self, args: list[str], timeout: float = 30) -> dict[str, Any]:
        return _run(
            [str(self.path), "-P", str(self.port), "-s", self.serial, *args],
            timeout=timeout,
        )

    def device_bytes(self, args: list[str], timeout: float = 30) -> bytes:
        result = _run(
            [str(self.path), "-P", str(self.port), "-s", self.serial, *args],
            timeout=timeout,
            binary=True,
        )
        if result["returncode"] != 0 or result["timed_out"]:
            raise RuntimeError(
                f"ADB_BYTES_FAILED:{args}:{result['returncode']}:{result['stderr']!r}"
            )
        return bytes(result["stdout"])

    def shell_text(self, args: list[str], timeout: float = 30) -> str:
        result = self.device(["shell", *args], timeout=timeout)
        if result["returncode"] != 0 or result["timed_out"]:
            raise RuntimeError(
                f"ADB_SHELL_FAILED:{args}:{result['returncode']}:{result['stderr']}"
            )
        return str(result["stdout"])


def _framework_ready(adb: ExplicitAdb, services: list[str]) -> tuple[bool, list[dict[str, Any]]]:
    records = []
    for service in services:
        result = adb.device(["shell", "service", "check", service], timeout=10)
        records.append(
            {
                "service": service,
                "returncode": result["returncode"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "present": result["returncode"] == 0 and "not found" not in str(result["stdout"]).casefold(),
            }
        )
    return all(item["present"] for item in records), records


def _listener_process(port: int) -> list[dict[str, Any]]:
    result = _run(["netstat", "-ano", "-p", "tcp"], timeout=10)
    records = []
    for line in str(result["stdout"]).splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[0].upper() == "TCP" and fields[1].endswith(f":{port}") and fields[3].upper() == "LISTENING":
            records.append({"line": line.strip(), "pid": int(fields[4])})
    return records


def _process_path(pid: int) -> str | None:
    result = _run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"$p=Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\" -ErrorAction SilentlyContinue; if($p){{$p.ExecutablePath}}",
        ],
        timeout=10,
    )
    value = str(result["stdout"]).strip()
    return value or None


def _adb_isolation(adb: ExplicitAdb, expected_hash: str) -> dict[str, Any]:
    listeners = _listener_process(adb.port)
    server_path = _process_path(listeners[0]["pid"]) if len(listeners) == 1 else None
    server_hash = sha256_path(Path(server_path)) if server_path and Path(server_path).is_file() else None
    state = adb.device(["get-state"], timeout=10)
    serial = adb.device(["get-serialno"], timeout=10)
    client_hash = sha256_path(adb.path)
    passed = bool(
        client_hash == expected_hash
        and len(listeners) == 1
        and server_hash == expected_hash
        and state["returncode"] == 0
        and state["stdout"] == "device"
        and serial["returncode"] == 0
        and serial["stdout"] == adb.serial
    )
    return {
        "adb_server_port": adb.port,
        "device_serial": adb.serial,
        "fallback_to_5037": False,
        "client_binary": str(adb.path),
        "client_binary_sha256": client_hash,
        "server_binary": server_path,
        "server_binary_sha256": server_hash,
        "listeners": listeners,
        "state": state,
        "serial_check": serial,
        "passed": passed,
    }


def _cold_restart_once(adb: ExplicitAdb, config: dict[str, Any], output_root: Path) -> dict[str, Any]:
    runtime = config["runtime"]
    before_ready, before_services = _framework_ready(adb, runtime["framework_services"])
    record: dict[str, Any] = {
        "permitted": runtime["cold_restart_if_framework_unready"],
        "maximum": runtime["maximum_cold_restarts"],
        "attempted": False,
        "before_ready": before_ready,
        "before_services": before_services,
    }
    if before_ready:
        record["after_ready"] = True
        record["after_services"] = before_services
        record["passed"] = True
        return record
    if not runtime["cold_restart_if_framework_unready"] or runtime["maximum_cold_restarts"] != 1:
        record["passed"] = False
        return record
    record["attempted"] = True
    kill = adb.device(["emu", "kill"], timeout=15)
    record["kill"] = kill
    deadline = time.monotonic() + 75
    while time.monotonic() < deadline:
        if adb.host(["devices"], timeout=5)["stdout"].find(adb.serial) < 0:
            break
        time.sleep(2)
    emulator = REPOSITORY_ROOT / "06_local_runtime" / "android" / "sdk" / "emulator" / "emulator.exe"
    stdout_path = output_root / "infrastructure" / "emulator_stdout.log"
    stderr_path = output_root / "infrastructure" / "emulator_stderr.log"
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["ANDROID_ADB_SERVER_PORT"] = str(adb.port)
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    stdout_handle = stdout_path.open("wb")
    stderr_handle = stderr_path.open("wb")
    process = subprocess.Popen(
        [
            str(emulator),
            "-avd",
            runtime["avd_name"],
            "-port",
            str(runtime["emulator_port"]),
            "-no-snapshot",
            "-no-boot-anim",
            "-no-audio",
            "-grpc",
            str(runtime["grpc_port"]),
            "-no-window",
        ],
        stdout=stdout_handle,
        stderr=stderr_handle,
        env=environment,
        creationflags=creation_flags,
    )
    stdout_handle.close()
    stderr_handle.close()
    record["launch_pid"] = process.pid
    record["launch_command"] = [
        "emulator.exe",
        "-avd",
        runtime["avd_name"],
        "-port",
        str(runtime["emulator_port"]),
        "-no-snapshot",
        "-grpc",
        str(runtime["grpc_port"]),
        "-no-window",
    ]
    deadline = time.monotonic() + runtime["boot_timeout_seconds"]
    observations = []
    after_ready = False
    after_services: list[dict[str, Any]] = []
    while time.monotonic() < deadline:
        boot = adb.device(["shell", "getprop", "sys.boot_completed"], timeout=8)
        ready, services = _framework_ready(adb, runtime["framework_services"])
        observations.append(
            {
                "boot": boot["stdout"],
                "transport_returncode": boot["returncode"],
                "services_ready": ready,
            }
        )
        if boot["returncode"] == 0 and boot["stdout"] == "1" and ready:
            after_ready = True
            after_services = services
            adb.device(["shell", "input", "keyevent", "82"], timeout=10)
            break
        time.sleep(3)
    record["boot_observations"] = observations
    record["after_ready"] = after_ready
    record["after_services"] = after_services
    record["stdout_path"] = stdout_path.relative_to(REPOSITORY_ROOT).as_posix()
    record["stderr_path"] = stderr_path.relative_to(REPOSITORY_ROOT).as_posix()
    record["passed"] = after_ready
    return record


def _foreground(adb: ExplicitAdb) -> dict[str, str | None]:
    output = adb.shell_text(["dumpsys", "activity", "activities"], timeout=15)
    line = next((item for item in output.splitlines() if "mResumedActivity" in item), "")
    component = None
    for field in line.split():
        if "/" in field:
            component = field.rstrip("}")
    if component is None:
        return {"component": None, "package": None, "activity": None}
    package, activity = component.split("/", 1)
    return {"component": component, "package": package, "activity": activity}


def _device_provenance(adb: ExplicitAdb, package: str) -> dict[str, Any]:
    size = adb.shell_text(["wm", "size"])
    density = adb.shell_text(["wm", "density"])
    rotation = adb.shell_text(["settings", "get", "system", "user_rotation"])
    version = adb.shell_text(["dumpsys", "package", package], timeout=20)
    version_lines = [line.strip() for line in version.splitlines() if "versionName=" in line or "versionCode=" in line]
    foreground = _foreground(adb)
    return {
        "build_fingerprint": adb.shell_text(["getprop", "ro.build.fingerprint"]),
        "android_release": adb.shell_text(["getprop", "ro.build.version.release"]),
        "screen_size_raw": size,
        "screen_density_raw": density,
        "orientation": "portrait" if rotation in {"0", "2"} else "landscape",
        "rotation": rotation,
        "app_version_lines": version_lines,
        "foreground_package": foreground["package"],
        "foreground_activity": foreground["activity"],
        "foreground_component": foreground["component"],
    }


def _capture_xml(adb: ExplicitAdb, timeout: int) -> bytes:
    dump = adb.device(
        ["shell", "uiautomator", "dump", "/sdcard/phase_b2_window.xml"],
        timeout=timeout,
    )
    if dump["returncode"] != 0 or dump["timed_out"]:
        raise RuntimeError(f"UIAUTOMATOR_DUMP_FAILED:{dump['stderr']}")
    raw = adb.device_bytes(["exec-out", "cat", "/sdcard/phase_b2_window.xml"], timeout=timeout)
    if not raw.strip().startswith(b"<?xml"):
        raise RuntimeError("UIAUTOMATOR_XML_INVALID")
    return raw


def _capture_stable(
    adb: ExplicitAdb,
    *,
    variant_root: Path,
    samples: int,
    gap_seconds: float,
    xml_timeout: int,
) -> tuple[list[dict[str, Any]], bytes, bytes, dict[str, bool]]:
    records = []
    chosen_png = b""
    chosen_xml = b""
    for index in range(1, samples + 1):
        before = adb.device_bytes(["exec-out", "screencap", "-p"], timeout=20)
        raw_xml = _capture_xml(adb, xml_timeout)
        after = adb.device_bytes(["exec-out", "screencap", "-p"], timeout=20)
        parsed = parse_ui_tree(raw_xml)
        foreground = _foreground(adb)
        sample_root = variant_root / "samples"
        sample_root.mkdir(parents=True, exist_ok=True)
        before_path = sample_root / f"sample_{index:02d}_before.png"
        xml_path = sample_root / f"sample_{index:02d}_ui.xml"
        after_path = sample_root / f"sample_{index:02d}_after.png"
        before_path.write_bytes(before)
        xml_path.write_bytes(raw_xml)
        after_path.write_bytes(after)
        record = {
            "sample": index,
            "before_path": before_path.relative_to(REPOSITORY_ROOT).as_posix(),
            "before_sha256": sha256_bytes(before),
            "ui_tree_path": xml_path.relative_to(REPOSITORY_ROOT).as_posix(),
            "ui_tree_sha256": sha256_bytes(raw_xml),
            "semantic_sha256": parsed.semantic_sha256,
            "after_path": after_path.relative_to(REPOSITORY_ROOT).as_posix(),
            "after_sha256": sha256_bytes(after),
            "foreground": foreground,
        }
        records.append(record)
        chosen_png = before
        chosen_xml = raw_xml
        if index < samples:
            time.sleep(gap_seconds)
    screenshot_hashes = [item["before_sha256"] for item in records]
    semantic_hashes = [item["semantic_sha256"] for item in records]
    packages = [item["foreground"]["package"] for item in records]
    activities = [item["foreground"]["activity"] for item in records]
    stability = {
        "three_samples_present": len(records) == 3,
        "all_brackets_pixel_equal": all(item["before_sha256"] == item["after_sha256"] for item in records),
        "cross_sample_pixel_equal": len(set(screenshot_hashes)) == 1,
        "cross_sample_semantic_equal": len(set(semantic_hashes)) == 1,
        "package_activity_stable": len(set(packages)) == 1 and len(set(activities)) == 1,
        "geometry_orientation_stable": True,
    }
    return records, chosen_png, chosen_xml, stability


def _tap_selector(adb: ExplicitAdb, selector: dict[str, Any]) -> None:
    left, top, right, bottom = selector["bounds"]
    x = (left + right) // 2
    y = (top + bottom) // 2
    result = adb.device(["shell", "input", "tap", str(x), str(y)], timeout=10)
    if result["returncode"] != 0:
        raise RuntimeError(f"SELECTOR_TAP_FAILED:{selector}")
    time.sleep(1.5)


def _tap_exact_if_present(adb: ExplicitAdb, text: str) -> bool:
    raw = _capture_xml(adb, 15)
    tree = parse_ui_tree(raw)
    try:
        selector = resolve_exact_item(tree, text)
    except ValueError:
        return False
    _tap_selector(adb, selector)
    return True


def _dismiss_onboarding(adb: ExplicitAdb, app_name: str, launch: Callable[[], None]) -> list[dict[str, Any]]:
    launch()
    records = []
    for label in ("Skip", "Don't allow", "Continue", "OK", "Got it"):
        try:
            clicked = _tap_exact_if_present(adb, label)
        except Exception as exc:  # qualification inventory records, never hides later failures
            records.append({"label": label, "clicked": False, "error": str(exc)})
        else:
            records.append({"label": label, "clicked": clicked})
    adb.device(["shell", "input", "keyevent", "3"], timeout=10)
    return records


def _launch_app(env: Any, app_name: str) -> None:
    adb_utils.launch_app(app_name, env.controller)
    time.sleep(3)


def _query_count(env: Any, adb: ExplicitAdb, driver: str) -> int:
    if driver == "contacts_rows":
        output = adb.shell_text(["content", "query", "--uri", "content://contacts/phones/", "--projection", "display_name:number"])
        return sum(line.startswith("Row:") for line in output.splitlines())
    if driver == "markor_note_rows":
        output = adb.shell_text(["sh", "-c", f"find {device_constants.MARKOR_DATA} -maxdepth 1 -type f | wc -l"])
        return int(output.strip() or 0)
    if driver == "download_file_rows":
        output = adb.shell_text(["sh", "-c", f"find {device_constants.DOWNLOAD_DATA} -maxdepth 1 -type f | wc -l"])
        return int(output.strip() or 0)
    if driver == "sms_conversation_rows":
        output = adb.shell_text(["content", "query", "--uri", "content://sms"])
        return 0 if output.startswith("No result") else sum(line.startswith("Row:") for line in output.splitlines())
    if driver == "tasks_rows":
        return len(task_app_utils.list_rows(env))
    if driver == "calendar_event_blocks":
        return len(
            sqlite_utils.get_rows_from_remote_device(
                "events",
                "/data/data/com.simplemobiletools.calendar.pro/databases/events.db",
                sqlite_schema_utils.CalendarEvent,
                env,
            )
        )
    if driver == "expense_rows":
        return len(
            sqlite_utils.get_rows_from_remote_device(
                "expense",
                "/data/data/com.arduia.expense/databases/accounting.db",
                sqlite_schema_utils.Expense,
                env,
            )
        )
    if driver == "recipe_cards":
        return len(
            sqlite_utils.get_rows_from_remote_device(
                "recipes",
                "/data/data/com.flauschcode.broccoli/databases/broccoli",
                sqlite_schema_utils.Recipe,
                env,
            )
        )
    raise ValueError(f"UNKNOWN_DRIVER_COUNT:{driver}")


def _clear_scene(env: Any, adb: ExplicitAdb, family: dict[str, Any]) -> dict[str, Any]:
    driver = family["driver"]
    started = time.monotonic()
    if driver == "contacts_rows":
        contacts_utils.clear_contacts(env.controller)
    elif driver == "markor_note_rows":
        file_utils.clear_directory(device_constants.MARKOR_DATA, env.controller)
    elif driver == "download_file_rows":
        file_utils.clear_directory(device_constants.DOWNLOAD_DATA, env.controller)
    elif driver == "tasks_rows":
        task_app_utils.clear_task_db(env)
    elif driver == "calendar_event_blocks":
        calendar_utils.clear_calendar_db(env)
    elif driver == "expense_rows":
        sqlite_utils.delete_all_rows_from_table(
            "expense", "/data/data/com.arduia.expense/databases/accounting.db", env, "pro expense"
        )
    elif driver == "recipe_cards":
        sqlite_utils.delete_all_rows_from_table(
            "recipes", "/data/data/com.flauschcode.broccoli/databases/broccoli", env, "broccoli app"
        )
    elif driver == "sms_conversation_rows":
        sms_validators.clear_sms_and_threads(env.controller)
        contacts_utils.clear_contacts(env.controller)
    else:
        raise ValueError(f"UNKNOWN_DRIVER:{driver}")
    adb.device(["shell", "am", "force-stop", family["expected_package"]], timeout=15)
    count = _query_count(env, adb, driver)
    passed = count == 0
    return {
        "passed": passed,
        "driver": driver,
        "observable_item_count": count,
        "wall_time_seconds": time.monotonic() - started,
    }


def _seed_scene(env: Any, adb: ExplicitAdb, family: dict[str, Any], ambiguity: str) -> list[dict[str, Any]]:
    items = [(family["destination_label"], family["destination_payload"])]
    if ambiguity == "high":
        items.insert(0, (family["source_label"], family["source_payload"]))
    trace: list[dict[str, Any]] = []
    driver = family["driver"]
    if driver == "contacts_rows":
        for label, payload in items:
            contacts_utils.add_contact(label, payload["phone"], env.controller, ui_delay_sec=1.5)
            trace.append({"operation": "contacts_utils.add_contact", "label": label, "payload_sha256": sha256_bytes(json.dumps(payload, sort_keys=True).encode())})
    elif driver in {"markor_note_rows", "download_file_rows"}:
        directory = device_constants.MARKOR_DATA if driver == "markor_note_rows" else device_constants.DOWNLOAD_DATA
        for label, payload in items:
            file_utils.create_file(label, directory, env.controller, payload["content"])
            trace.append({"operation": "file_utils.create_file", "directory": directory, "label": label, "payload_sha256": sha256_bytes(payload["content"].encode())})
    elif driver == "tasks_rows":
        rows = [
            sqlite_schema_utils.Task(
                title=label,
                importance=2,
                created=1697300000000 + index,
                modified=1697300000000 + index,
                notes=payload["notes"],
                remoteId=f"b2-{family['base_family_id']}-{index}",
            )
            for index, (label, payload) in enumerate(items)
        ]
        task_app_utils.add_tasks(rows, env)
        trace.append({"operation": "task_app_utils.add_tasks", "labels": [item[0] for item in items]})
    elif driver == "calendar_event_blocks":
        rows = [
            sqlite_schema_utils.CalendarEvent(
                start_ts=payload["start_ts"],
                end_ts=payload["end_ts"],
                title=label,
                location=payload["location"],
            )
            for label, payload in items
        ]
        calendar_utils.add_events(rows, env)
        trace.append({"operation": "calendar_utils.add_events", "labels": [item[0] for item in items]})
    elif driver == "expense_rows":
        rows = [
            sqlite_schema_utils.Expense(
                name=label,
                amount=payload["amount"],
                category=payload["category"],
                note=payload["note"],
                created_date=1697300000 + index,
                modified_date=1697300000 + index,
            )
            for index, (label, payload) in enumerate(items)
        ]
        sqlite_utils.insert_rows_to_remote_db(
            rows, "expense_id", "expense", "/data/data/com.arduia.expense/databases/accounting.db", "pro expense", env
        )
        trace.append({"operation": "sqlite_utils.insert_expenses", "labels": [item[0] for item in items]})
    elif driver == "recipe_cards":
        rows = [
            sqlite_schema_utils.Recipe(
                title=label,
                description=payload["description"],
                ingredients=payload["ingredients"],
                directions="Mix and serve",
                servings="2",
            )
            for label, payload in items
        ]
        sqlite_utils.insert_rows_to_remote_db(
            rows, "recipeId", "recipes", "/data/data/com.flauschcode.broccoli/databases/broccoli", "broccoli app", env
        )
        trace.append({"operation": "sqlite_utils.insert_recipes", "labels": [item[0] for item in items]})
    elif driver == "sms_conversation_rows":
        for label, payload in items:
            contacts_utils.add_contact(label, payload["phone"], env.controller, ui_delay_sec=1.5)
            adb_utils.text_emulator(env.controller, payload["phone"], payload["message"])
            trace.append({"operation": "contacts_plus_inbound_sms", "label": label, "phone_hash": sha256_bytes(payload["phone"].encode()), "message_hash": sha256_bytes(payload["message"].encode())})
    else:
        raise ValueError(f"UNKNOWN_DRIVER:{driver}")
    return trace


def _navigate_scene(env: Any, adb: ExplicitAdb, family: dict[str, Any]) -> list[dict[str, Any]]:
    _launch_app(env, family["app_name"])
    trace = [{"operation": "launch_app", "app_name": family["app_name"]}]
    if family["driver"] == "download_file_rows":
        if not _tap_exact_if_present(adb, "Downloads"):
            raise RuntimeError("FILES_DOWNLOADS_NAVIGATION_NOT_AVAILABLE")
        trace.append({"operation": "tap_exact_text", "text": "Downloads"})
    time.sleep(2)
    return trace


def _error(exc: BaseException) -> dict[str, Any]:
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback_sha256": sha256_bytes(traceback.format_exc().encode("utf-8")),
    }


def _capture_variant(
    env: Any,
    adb: ExplicitAdb,
    *,
    family: dict[str, Any],
    ambiguity: str,
    config: dict[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    variant_root = output_root / "families" / family["base_family_id"] / ambiguity
    variant_root.mkdir(parents=True, exist_ok=False)
    trace: dict[str, Any] = {"started_at": utc_now(), "operations": []}
    reset_before: dict[str, Any] = {"passed": False}
    reset_after: dict[str, Any] = {"passed": False}
    error = None
    sample_records: list[dict[str, Any]] = []
    stability: dict[str, bool] = {}
    screenshot_path = None
    screenshot_hash = None
    ui_path = None
    ui_hash = None
    targets: list[dict[str, Any]] = []
    rationale: dict[str, Any] = {}
    provenance: dict[str, Any] = {}
    try:
        adb.device(["shell", "input", "keyevent", "3"], timeout=10)
        reset_before = _clear_scene(env, adb, family)
        trace["operations"].append({"operation": "reset_before", "record": reset_before})
        if not reset_before["passed"]:
            raise RuntimeError("RESET_BEFORE_FAILED")
        trace["operations"].extend(_seed_scene(env, adb, family, ambiguity))
        trace["operations"].extend(_navigate_scene(env, adb, family))
        provenance = _device_provenance(adb, family["expected_package"])
        if provenance["foreground_package"] != family["expected_package"]:
            raise RuntimeError(
                f"FOREGROUND_PACKAGE:{provenance['foreground_package']}:{family['expected_package']}"
            )
        sample_records, selected_png, selected_xml, stability = _capture_stable(
            adb,
            variant_root=variant_root,
            samples=config["capture"]["samples"],
            gap_seconds=config["capture"]["gap_seconds"],
            xml_timeout=config["capture"]["uiautomator_timeout_seconds"],
        )
        selected_png_path = variant_root / "selected_frame.png"
        selected_xml_path = variant_root / "selected_ui.xml"
        selected_png_path.write_bytes(selected_png)
        selected_xml_path.write_bytes(selected_xml)
        screenshot_path = selected_png_path.relative_to(REPOSITORY_ROOT).as_posix()
        screenshot_hash = sha256_bytes(selected_png)
        ui_path = selected_xml_path.relative_to(REPOSITORY_ROOT).as_posix()
        ui_hash = sha256_bytes(selected_xml)
        targets, rationale = build_oracle(
            raw_xml=selected_xml,
            family=family,
            ambiguity=ambiguity,
        )
    except Exception as exc:
        error = _error(exc)
    finally:
        try:
            adb.device(["shell", "input", "keyevent", "3"], timeout=10)
            reset_after = _clear_scene(env, adb, family)
        except Exception as cleanup_exc:
            reset_after = {"passed": False, "error": _error(cleanup_exc)}
        trace["operations"].append({"operation": "reset_after", "record": reset_after})
        trace["finished_at"] = utc_now()
        trace["primary_error"] = error
        trace_path = variant_root / "setup_trace.json"
        write_json(trace_path, trace)
    captured = error is None
    return {
        "role_ambiguity": ambiguity,
        "capture_status": "captured" if captured else "failed",
        "error": error,
        "development_contaminated": False,
        "held_out_eligible": False,
        "artifact_root": variant_root.relative_to(REPOSITORY_ROOT).as_posix(),
        "screenshot_path": screenshot_path,
        "screenshot_sha256": screenshot_hash,
        "raw_ui_tree_path": ui_path,
        "raw_ui_tree_sha256": ui_hash,
        "setup_trace_path": trace_path.relative_to(REPOSITORY_ROOT).as_posix(),
        "setup_trace_sha256": sha256_path(trace_path),
        "sample_records": sample_records,
        "stability": stability,
        "provenance": provenance,
        "reset_before": reset_before,
        "reset_after": reset_after,
        "source_target_id": family["source_target_id"] if ambiguity == "high" and captured else None,
        "destination_target_id": family["destination_target_id"],
        "destination_widget_id": family["destination_target_id"],
        "candidate_targets": targets,
        "oracle_rationale": rationale,
    }


def _lock_pool(
    *,
    output_root: Path,
    manifest_path: Path,
    protocol_freeze_commit: str,
    config_path: Path,
) -> dict[str, Any]:
    files = []
    for path in sorted(output_root.rglob("*")):
        if path.is_file() and path.name != "candidate_pool_frozen.v0_2.lock.json":
            files.append(
                {
                    "path": path.relative_to(REPOSITORY_ROOT).as_posix(),
                    "sha256": sha256_path(path),
                    "bytes": path.stat().st_size,
                }
            )
    return {
        "schema_version": "role_binding_timing.snapshot_pool_lock.v0_2",
        "study_id": "role_binding_timing_phase_b2_v0_2",
        "frozen_at": utc_now(),
        "frozen_before_qualification": True,
        "protocol_freeze_commit": protocol_freeze_commit,
        "config_path": config_path.relative_to(REPOSITORY_ROOT).as_posix(),
        "config_sha256": sha256_path(config_path),
        "candidate_manifest_path": manifest_path.relative_to(REPOSITORY_ROOT).as_posix(),
        "candidate_manifest_sha256": sha256_path(manifest_path),
        "generation_calls": 0,
        "candidate_replacements": 0,
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "configs" / "role_binding_timing" / "phase_b2_collection_v0_2.json",
    )
    parser.add_argument(
        "--lock",
        type=Path,
        default=PROJECT_ROOT / "configs" / "role_binding_timing" / "phase_b2_collection_v0_2.lock.json",
    )
    parser.add_argument("--protocol-freeze-commit", required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    lock_path = args.lock.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    issues = validate_collection_config(config)
    if issues:
        raise RuntimeError(f"CONFIG_INVALID:{issues}")
    if lock["generation_calls_before_freeze"] != 0 or lock["generation_eligible"] is not False:
        raise RuntimeError("LOCK_GENERATION_BOUNDARY")
    for item in lock["files"]:
        path = REPOSITORY_ROOT / item["path"]
        if sha256_path(path) != item["sha256"]:
            raise RuntimeError(f"LOCK_HASH_MISMATCH:{item['path']}")
    if args.protocol_freeze_commit != subprocess.check_output(
        ["git", "rev-list", "-n", "1", PROTOCOL_FREEZE_TAG],
        cwd=REPOSITORY_ROOT,
        text=True,
    ).strip():
        raise RuntimeError("PROTOCOL_FREEZE_COMMIT_TAG_MISMATCH")
    output_root = REPOSITORY_ROOT / config["capture"]["output_root"]
    if output_root.exists():
        raise RuntimeError(f"OUTPUT_ROOT_NOT_FRESH:{output_root}")
    output_root.mkdir(parents=True)
    started = time.monotonic()
    started_at = utc_now()
    adb_path = REPOSITORY_ROOT / config["runtime"]["adb_binary"]
    adb = ExplicitAdb(adb_path, config["runtime"]["adb_server_port"], config["runtime"]["device_serial"])
    infrastructure: dict[str, Any] = {
        "pre_isolation": _adb_isolation(adb, config["runtime"]["adb_binary_sha256"]),
    }
    if not infrastructure["pre_isolation"]["passed"]:
        raise RuntimeError("ADB_ISOLATION_FAILED_BEFORE_COLLECTION")
    infrastructure["cold_restart"] = _cold_restart_once(adb, config, output_root)
    if not infrastructure["cold_restart"]["passed"]:
        write_json(output_root / "infrastructure" / "pre_capture_failure.json", infrastructure)
        raise RuntimeError("FRAMEWORK_SERVICES_UNREADY_AFTER_FROZEN_RESTART")
    infrastructure["post_restart_isolation"] = _adb_isolation(adb, config["runtime"]["adb_binary_sha256"])
    if not infrastructure["post_restart_isolation"]["passed"]:
        raise RuntimeError("ADB_ISOLATION_FAILED_AFTER_RESTART")
    env = load_and_setup_env(
        console_port=config["runtime"]["emulator_port"],
        emulator_setup=False,
        freeze_datetime=True,
        adb_path=str(adb_path),
        adb_server_port=config["runtime"]["adb_server_port"],
        grpc_port=config["runtime"]["grpc_port"],
    )
    onboarding = []
    try:
        env.reset(go_home=True)
        for family in config["families"]:
            onboarding.append(
                {
                    "app_id": family["app_id"],
                    "records": _dismiss_onboarding(
                        adb,
                        family["app_name"],
                        lambda name=family["app_name"]: _launch_app(env, name),
                    ),
                }
            )
        families = []
        attempts = 0
        for family in config["families"]:
            variants = {}
            for ambiguity in family["variant_order"]:
                attempts += 1
                variants[ambiguity] = _capture_variant(
                    env,
                    adb,
                    family=family,
                    ambiguity=ambiguity,
                    config=config,
                    output_root=output_root,
                )
            families.append(
                {
                    "base_family_id": family["base_family_id"],
                    "app_id": family["app_id"],
                    "app_name": family["app_name"],
                    "expected_package": family["expected_package"],
                    "driver": family["driver"],
                    "task_semantics_id": family["task_semantics_id"],
                    "destination_widget_family": family["destination_widget_family"],
                    "task_without_value": family["task_without_value"],
                    "fact": {
                        "field": family["field"],
                        "value": family["fact_value"],
                        "source_entity_id": family["source_entity_id"],
                        "destination_entity_id": family["destination_entity_id"],
                        "source_label": family["source_label"],
                        "destination_label": family["destination_label"],
                    },
                    "collection_order": family["variant_order"],
                    "variants": variants,
                }
            )
        final_reset_records = []
        for family in config["families"]:
            try:
                final_reset_records.append({"base_family_id": family["base_family_id"], **_clear_scene(env, adb, family)})
            except Exception as exc:
                final_reset_records.append({"base_family_id": family["base_family_id"], "passed": False, "error": _error(exc)})
        adb.device(["shell", "input", "keyevent", "3"], timeout=10)
        runtime = {
            "adb": infrastructure,
            "framework_services": _framework_ready(adb, config["runtime"]["framework_services"])[1],
            "device": _device_provenance(adb, config["families"][0]["expected_package"]),
            "onboarding": onboarding,
            "final_reset_records": final_reset_records,
            "generation_endpoint_called": False,
            "generation_calls": 0,
            "model_service_contacted": False,
        }
        manifest = {
            "schema_version": "role_binding_timing.snapshot_pool.v0_2",
            "study_id": "role_binding_timing_phase_b2_v0_2",
            "generation_calls": 0,
            "frozen_before_qualification": True,
            "protocol_freeze_commit": args.protocol_freeze_commit,
            "collection": {
                "started_at": started_at,
                "finished_at": utc_now(),
                "wall_time_seconds": time.monotonic() - started,
                "capture_attempts": attempts,
                "model_endpoint_called": False,
                "candidate_replacements": 0,
            },
            "runtime": runtime,
            "families": families,
        }
        manifest_path = output_root / config["capture"]["candidate_manifest"]
        write_json(manifest_path, manifest)
        pool_lock = _lock_pool(
            output_root=output_root,
            manifest_path=manifest_path,
            protocol_freeze_commit=args.protocol_freeze_commit,
            config_path=config_path,
        )
        pool_lock_path = output_root / config["capture"]["pool_lock"]
        write_json(pool_lock_path, pool_lock)
        print(json.dumps({"manifest": str(manifest_path), "lock": str(pool_lock_path), "capture_attempts": attempts, "generation_calls": 0}, indent=2))
        return 0
    finally:
        env.close()


if __name__ == "__main__":
    raise SystemExit(main())
