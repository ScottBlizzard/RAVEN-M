"""Run the frozen, zero-model B2.5 DEV infrastructure stability certificate."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from typing import Any

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.role_binding_timing.infrastructure_v0_2_5 import (  # noqa: E402
    derive_dev_locator,
    guarded_call,
    parse_foreground_witnesses,
    parse_ui_tree,
    resolve_locator,
    sha256_bytes,
    validate_foreground,
    validate_launch_result,
    validate_png,
)


DEV_FREEZE_TAG = "role-binding-timing-b2.5-dev-freeze-20260804"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_path(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _run_host(command: list[str], timeout: float = 15) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=timeout)
        return {
            "command": command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timed_out": False,
            "wall_time_seconds": time.monotonic() - started,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "returncode": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timed_out": True,
            "wall_time_seconds": time.monotonic() - started,
        }


def listener_pids(port: int) -> list[int]:
    result = _run_host(["netstat", "-ano", "-p", "tcp"], timeout=10)
    pids: list[int] = []
    for line in str(result["stdout"]).splitlines():
        fields = line.split()
        if (
            len(fields) >= 5
            and fields[0].upper() == "TCP"
            and fields[1].endswith(f":{port}")
            and fields[3].upper() == "LISTENING"
        ):
            pid = int(fields[4])
            if pid not in pids:
                pids.append(pid)
    return pids


def process_record(pid: int) -> dict[str, Any]:
    command = (
        f'$p=Get-CimInstance Win32_Process -Filter "ProcessId={pid}" -ErrorAction Stop; '
        '[pscustomobject]@{process_id=$p.ProcessId;executable_path=$p.ExecutablePath;'
        'creation_time=[string]$p.CreationDate;command_line=$p.CommandLine}|ConvertTo-Json -Compress'
    )
    result = _run_host(["powershell", "-NoProfile", "-Command", command], timeout=10)
    if result["returncode"] != 0 or result["timed_out"]:
        raise RuntimeError("ADB_PROCESS_RECORD_UNAVAILABLE")
    return json.loads(str(result["stdout"]))


class ManagedAdb:
    def __init__(self, *, binary: Path, expected_hash: str, port: int, serial: str) -> None:
        if port != 5038:
            raise ValueError("ADB_PORT_NOT_5038")
        self.binary = binary.resolve()
        self.expected_hash = expected_hash
        self.port = port
        self.serial = serial
        pids = listener_pids(port)
        if len(pids) != 1:
            raise RuntimeError(f"ADB_LISTENER_COUNT:{pids}")
        self.owner_pid = pids[0]
        process = process_record(self.owner_pid)
        executable = Path(process["executable_path"]).resolve()
        actual_hash = sha256_path(executable)
        if executable != self.binary or actual_hash != expected_hash:
            raise RuntimeError(f"ADB_OWNER_MISMATCH:{executable}:{actual_hash}")
        self.owner = {
            "listener_pid": self.owner_pid,
            "executable_path": str(executable),
            "binary_sha256": actual_hash,
            "process_creation_time": process["creation_time"],
            "command_line": process["command_line"],
            "port": port,
            "device_serial": serial,
            "fallback_to_5037": False,
        }

    def current_pid(self) -> int | None:
        pids = listener_pids(self.port)
        return pids[0] if len(pids) == 1 else None

    def _command(self, args: list[str]) -> list[str]:
        return [str(self.binary), "-P", str(self.port), "-s", self.serial, *args]

    def text(self, args: list[str], *, timeout: float = 20) -> dict[str, Any]:
        def operation() -> dict[str, Any]:
            result = _run_host(self._command(args), timeout=timeout)
            result["stdout_sha256"] = sha256_bytes(str(result["stdout"]).encode("utf-8"))
            result["stderr_sha256"] = sha256_bytes(str(result["stderr"]).encode("utf-8"))
            return result

        return guarded_call(expected_pid=self.owner_pid, witness=self.current_pid, operation=operation)

    def bytes(self, args: list[str], *, timeout: float = 20) -> tuple[dict[str, Any], bytes]:
        payload: bytes = b""

        def operation() -> dict[str, Any]:
            nonlocal payload
            started = time.monotonic()
            try:
                result = subprocess.run(
                    self._command(args), capture_output=True, text=False, check=False, timeout=timeout
                )
                payload = bytes(result.stdout)
                return {
                    "command": self._command(args),
                    "returncode": result.returncode,
                    "stdout_sha256": sha256_bytes(payload),
                    "stderr_sha256": sha256_bytes(bytes(result.stderr)),
                    "stderr": bytes(result.stderr).decode("utf-8", errors="replace"),
                    "timed_out": False,
                    "wall_time_seconds": time.monotonic() - started,
                }
            except subprocess.TimeoutExpired as exc:
                payload = bytes(exc.stdout or b"")
                return {
                    "command": self._command(args),
                    "returncode": None,
                    "stdout_sha256": sha256_bytes(payload),
                    "stderr_sha256": sha256_bytes(bytes(exc.stderr or b"")),
                    "stderr": bytes(exc.stderr or b"").decode("utf-8", errors="replace"),
                    "timed_out": True,
                    "wall_time_seconds": time.monotonic() - started,
                }

        record = guarded_call(expected_pid=self.owner_pid, witness=self.current_pid, operation=operation)
        return record, payload


def framework_check(adb: ManagedAdb, services: list[str]) -> dict[str, Any]:
    records = []
    for service in services:
        result = adb.text(["shell", "service", "check", service], timeout=10)
        present = (
            result["returncode"] == 0
            and not result["timed_out"]
            and "not found" not in str(result["stdout"]).casefold()
        )
        records.append({"service": service, "present": present, "result": result})
    return {"passed": all(item["present"] for item in records), "records": records}


def save_text(path: Path, value: str) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    return {
        "path": path.relative_to(REPOSITORY_ROOT).as_posix(),
        "sha256": sha256_path(path),
        "bytes": path.stat().st_size,
    }


def save_bytes(path: Path, value: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    return {
        "path": path.relative_to(REPOSITORY_ROOT).as_posix(),
        "sha256": sha256_path(path),
        "bytes": path.stat().st_size,
    }


def reset_app(adb: ManagedAdb, package: str, timeout: float) -> dict[str, Any]:
    home = adb.text(["shell", "input", "keyevent", "3"], timeout=timeout)
    stop = adb.text(["shell", "am", "force-stop", package], timeout=timeout)
    issues = []
    if home["returncode"] != 0 or home["timed_out"]:
        issues.append("HOME_FAILED")
    if stop["returncode"] != 0 or stop["timed_out"]:
        issues.append("FORCE_STOP_FAILED")
    return {"passed": not issues, "issues": issues, "home": home, "force_stop": stop}


def capture_sequence(
    *,
    adb: ManagedAdb,
    app: dict[str, Any],
    round_index: int,
    config: dict[str, Any],
    output_root: Path,
) -> dict[str, Any]:
    sequence_id = f"R{round_index:02d}-{app['dev_app_id']}"
    root = output_root / f"round_{round_index:02d}" / app["dev_app_id"]
    root.mkdir(parents=True, exist_ok=False)
    issues: list[str] = []
    artifacts: dict[str, Any] = {}
    events: list[dict[str, Any]] = []
    started = time.monotonic()
    try:
        before = framework_check(adb, config["runtime"]["framework_services"])
        events.append({"event": "framework_before", **before})
        if not before["passed"]:
            raise RuntimeError("FRAMEWORK_BEFORE_FAILED")
        reset_before = reset_app(adb, app["package"], config["sampling"]["command_timeout_seconds"])
        events.append({"event": "reset_before", **reset_before})
        if not reset_before["passed"]:
            raise RuntimeError("RESET_BEFORE_FAILED")

        launch = adb.text(
            ["shell", "am", "start", "-W", "-n", app["component"]],
            timeout=config["sampling"]["command_timeout_seconds"],
        )
        artifacts["launch_stdout"] = save_text(root / "launch_stdout.txt", str(launch["stdout"]))
        artifacts["launch_stderr"] = save_text(root / "launch_stderr.txt", str(launch["stderr"]))
        launch_issues = validate_launch_result(launch)
        events.append({"event": "launch", "result": launch, "issues": launch_issues})
        if launch_issues:
            raise RuntimeError(f"LAUNCH_FAILED:{launch_issues}")

        selected_tree = None
        selected_witnesses = None
        observation_attempts = []
        for attempt in range(1, config["sampling"]["foreground_attempts"] + 1):
            activity = adb.text(["shell", "dumpsys", "activity", "activities"], timeout=15)
            window = adb.text(["shell", "dumpsys", "window"], timeout=15)
            dump = adb.text(
                ["shell", "uiautomator", "dump", f"/sdcard/rbt_b25_{sequence_id}.xml"],
                timeout=15,
            )
            xml_record, raw_xml = adb.bytes(
                ["exec-out", "cat", f"/sdcard/rbt_b25_{sequence_id}.xml"], timeout=15
            )
            attempt_root = root / f"observation_{attempt:02d}"
            activity_artifact = save_text(attempt_root / "activity.txt", str(activity["stdout"]))
            window_artifact = save_text(attempt_root / "window.txt", str(window["stdout"]))
            xml_artifact = save_bytes(attempt_root / "ui.xml", raw_xml)
            attempt_issues: list[str] = []
            if dump["returncode"] != 0 or dump["timed_out"] or xml_record["returncode"] != 0:
                attempt_issues.append("UI_DUMP_COMMAND_FAILED")
                tree = None
                witnesses = parse_foreground_witnesses(str(activity["stdout"]), str(window["stdout"]))
            else:
                try:
                    tree = parse_ui_tree(raw_xml)
                except Exception as exc:
                    attempt_issues.append(f"UI_TREE_INVALID:{type(exc).__name__}")
                    tree = None
                witnesses = parse_foreground_witnesses(str(activity["stdout"]), str(window["stdout"]))
                if tree is not None:
                    attempt_issues.extend(
                        validate_foreground(
                            expected_package=app["package"], witnesses=witnesses, ui_tree=tree
                        )
                    )
            observation_attempts.append(
                {
                    "attempt": attempt,
                    "issues": attempt_issues,
                    "activity_result": activity,
                    "window_result": window,
                    "dump_result": dump,
                    "xml_result": xml_record,
                    "witnesses": witnesses,
                    "artifacts": {
                        "activity": activity_artifact,
                        "window": window_artifact,
                        "ui_tree": xml_artifact,
                    },
                }
            )
            if not attempt_issues and tree is not None:
                selected_tree = tree
                selected_witnesses = witnesses
                artifacts["selected_ui_tree"] = xml_artifact
                break
            if attempt < config["sampling"]["foreground_attempts"]:
                time.sleep(config["sampling"]["foreground_gap_seconds"])
        events.append({"event": "observation_attempts", "attempts": observation_attempts})
        if selected_tree is None:
            raise RuntimeError("FOREGROUND_UI_QUALIFICATION_FAILED")

        screenshot_result, screenshot = adb.bytes(["exec-out", "screencap", "-p"], timeout=20)
        if screenshot_result["returncode"] != 0 or screenshot_result["timed_out"]:
            raise RuntimeError("SCREENSHOT_COMMAND_FAILED")
        screenshot_validation = validate_png(screenshot, tuple(config["runtime"]["screen_size"]))
        artifacts["screenshot"] = save_bytes(root / "screenshot.png", screenshot)
        events.append(
            {"event": "screenshot", "result": screenshot_result, "validation": screenshot_validation}
        )

        locator = derive_dev_locator(selected_tree, package=app["package"])
        resolution = resolve_locator(selected_tree, package=app["package"], locator=locator)
        events.append(
            {
                "event": "locator_provenance",
                "dev_only": True,
                "locator": locator,
                "resolution": resolution,
                "foreground_witnesses": selected_witnesses,
            }
        )

        after_capture = framework_check(adb, config["runtime"]["framework_services"])
        events.append({"event": "framework_after_capture", **after_capture})
        if not after_capture["passed"]:
            raise RuntimeError("FRAMEWORK_AFTER_CAPTURE_FAILED")
        reset_after = reset_app(adb, app["package"], config["sampling"]["command_timeout_seconds"])
        events.append({"event": "reset_after", **reset_after})
        if not reset_after["passed"]:
            raise RuntimeError("RESET_AFTER_FAILED")
        after_reset = framework_check(adb, config["runtime"]["framework_services"])
        events.append({"event": "framework_after_reset", **after_reset})
        if not after_reset["passed"]:
            raise RuntimeError("FRAMEWORK_AFTER_RESET_FAILED")
    except Exception as exc:
        issues.append(f"{type(exc).__name__}:{exc}")
        events.append(
            {
                "event": "primary_error",
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback_sha256": sha256_bytes(traceback.format_exc().encode("utf-8")),
            }
        )
    trace = {
        "schema_version": "role_binding_timing.infrastructure_sequence.v0_2_5",
        "sequence_id": sequence_id,
        "dev_app_id": app["dev_app_id"],
        "round": round_index,
        "package": app["package"],
        "component": app["component"],
        "passed": not issues,
        "issues": issues,
        "events": events,
        "artifacts": artifacts,
        "wall_time_seconds": time.monotonic() - started,
        "generation_calls": 0,
        "dev_contaminated": True,
        "held_out_eligible": False,
    }
    trace_path = root / "sequence.json"
    write_json_atomic(trace_path, trace)
    trace["trace_path"] = trace_path.relative_to(REPOSITORY_ROOT).as_posix()
    trace["trace_sha256"] = sha256_path(trace_path)
    return trace


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "configs" / "role_binding_timing" / "phase_b2_5_infrastructure_dev.json",
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=PROJECT_ROOT / "contracts" / "role_binding_timing_collector_infrastructure.v0_2_5.json",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=PROJECT_ROOT / "schemas" / "role_binding_timing_infrastructure_certificate.v0_2_5.schema.json",
    )
    parser.add_argument("--implementation-commit", required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    contract_path = args.contract.resolve()
    schema_path = args.schema.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if config["generation_calls_authorized"] != 0 or config["generation_eligible"] is not False:
        raise RuntimeError("GENERATION_BOUNDARY")
    if contract["generation_calls_authorized"] != 0:
        raise RuntimeError("CONTRACT_GENERATION_BOUNDARY")
    tag_commit = subprocess.check_output(
        ["git", "rev-list", "-n", "1", DEV_FREEZE_TAG], cwd=REPOSITORY_ROOT, text=True
    ).strip()
    if args.implementation_commit != tag_commit:
        raise RuntimeError("DEV_FREEZE_TAG_MISMATCH")
    output_root = REPOSITORY_ROOT / config["output_root"]
    if output_root.exists():
        raise RuntimeError("DEV_OUTPUT_ROOT_NOT_FRESH")
    output_root.mkdir(parents=True)
    certificate_path = output_root / "infrastructure_certificate.v0_2_5.json"
    started = time.monotonic()
    sequences: list[dict[str, Any]] = []
    primary_error = None
    adb = None
    source_hashes = {
        "implementation_commit": args.implementation_commit,
        "config": sha256_path(config_path),
        "contract": sha256_path(contract_path),
        "schema": sha256_path(schema_path),
        "runner": sha256_path(Path(__file__)),
        "primitives": sha256_path(PROJECT_ROOT / "src" / "raven_m" / "role_binding_timing" / "infrastructure_v0_2_5.py"),
    }
    try:
        adb = ManagedAdb(
            binary=REPOSITORY_ROOT / config["runtime"]["adb_binary"],
            expected_hash=config["runtime"]["adb_binary_sha256"],
            port=config["runtime"]["adb_server_port"],
            serial=config["runtime"]["device_serial"],
        )
        state = adb.text(["get-state"], timeout=10)
        serial = adb.text(["get-serialno"], timeout=10)
        if state["returncode"] != 0 or state["stdout"].strip() != "device":
            raise RuntimeError("DEVICE_STATE_NOT_READY")
        if serial["returncode"] != 0 or serial["stdout"].strip() != adb.serial:
            raise RuntimeError("DEVICE_SERIAL_MISMATCH")
        for round_index in range(1, config["sampling"]["rounds"] + 1):
            for app in config["apps"]:
                sequence = capture_sequence(
                    adb=adb,
                    app=app,
                    round_index=round_index,
                    config=config,
                    output_root=output_root,
                )
                sequences.append(sequence)
                print(
                    json.dumps(
                        {
                            "batch": "B2.5_DEV",
                            "sequence": sequence["sequence_id"],
                            "passed": sequence["passed"],
                            "completed": len(sequences),
                            "planned": config["pass_rules"]["required_sequences"],
                        }
                    ),
                    flush=True,
                )
                if not sequence["passed"]:
                    raise RuntimeError(f"SEQUENCE_FAILED:{sequence['sequence_id']}")
    except Exception as exc:
        primary_error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback_sha256": sha256_bytes(traceback.format_exc().encode("utf-8")),
        }
    final_pids = listener_pids(config["runtime"]["adb_server_port"])
    planned = config["pass_rules"]["required_sequences"]
    passed = sum(item["passed"] for item in sequences)
    implicit_restarts = 0
    if adb is not None and final_pids != [adb.owner_pid]:
        implicit_restarts = 1
    verdict = "PASS" if primary_error is None and len(sequences) == planned and passed == planned and implicit_restarts == 0 else "NOT_ELIGIBLE"
    certificate = {
        "schema_version": "role_binding_timing.infrastructure_certificate.v0_2_5",
        "study_id": config["study_id"],
        "verdict": verdict,
        "generation_calls": 0,
        "generation_eligible": False,
        "dev_contaminated": True,
        "held_out_eligible": False,
        "source_hashes": source_hashes,
        "server_owner": adb.owner if adb is not None else {
            "listener_pid": final_pids[0] if len(final_pids) == 1 else 1,
            "binary_sha256": config["runtime"]["adb_binary_sha256"],
            "port": 5038,
            "device_serial": config["runtime"]["device_serial"],
            "adoption_failed": True,
        },
        "sequences": [
            {
                "sequence_id": item["sequence_id"],
                "dev_app_id": item["dev_app_id"],
                "round": item["round"],
                "passed": item["passed"],
                "issues": item["issues"],
                "artifacts": {
                    "trace_path": item["trace_path"],
                    "trace_sha256": item["trace_sha256"],
                },
                "wall_time_seconds": item["wall_time_seconds"],
            }
            for item in sequences
        ],
        "metrics": {
            "planned_sequences": planned,
            "completed_sequences": len(sequences),
            "passed_sequences": passed,
            "implicit_restarts": implicit_restarts,
            "framework_failures": sum(
                any("FRAMEWORK" in issue for issue in item["issues"]) for item in sequences
            ),
            "generation_calls": 0,
            "wall_time_seconds": time.monotonic() - started,
        },
        "terminal_audit": {
            "primary_error": primary_error,
            "final_listener_pids": final_pids,
            "certificate_write_policy": "atomic_exactly_once",
            "v0_3_freeze_authorized": verdict == "PASS",
        },
    }
    errors = sorted(Draft202012Validator(schema).iter_errors(certificate), key=lambda item: list(item.path))
    if errors:
        certificate["verdict"] = "NOT_ELIGIBLE"
        certificate["terminal_audit"]["schema_errors"] = [item.message for item in errors]
        certificate["terminal_audit"]["v0_3_freeze_authorized"] = False
    write_json_atomic(certificate_path, certificate)
    print(json.dumps({"certificate": str(certificate_path), "verdict": certificate["verdict"], "generation_calls": 0}, indent=2))
    return 0 if certificate["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
