"""Capture byte-exact, read-only pre-maintenance evidence for INFRA-M1."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent


def digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def digest_path(path: Path) -> str:
    return digest(path.read_bytes())


def save_bytes(path: Path, value: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    return {"path": path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": len(value), "sha256": digest(value)}


def run(command: list[str], *, root: Path, name: str, timeout: float = 30.0) -> tuple[dict[str, Any], bytes, bytes]:
    started = time.monotonic()
    try:
        result = subprocess.run(command, capture_output=True, text=False, check=False, timeout=timeout)
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


def listener_pids(netstat: str, port: int) -> list[int]:
    found = set()
    for line in netstat.splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[0].upper() == "TCP" and fields[3].upper() == "LISTENING" and fields[1].rsplit(":", 1)[-1] == str(port):
            found.add(int(fields[-1]))
    return sorted(found)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = json.loads((REPOSITORY_ROOT / args.config).read_text(encoding="utf-8"))
    if config["generation_calls_authorized"] != 0:
        raise RuntimeError("GENERATION_BOUNDARY")
    output_root = REPOSITORY_ROOT / config["pre_inventory_root"]
    if output_root.exists():
        raise RuntimeError("PRE_INVENTORY_NOT_FRESH")
    output_root.mkdir(parents=True)
    (output_root / ".gitattributes").write_text("**/*.bin -text\n", encoding="ascii")
    protected = {name: digest_path(REPOSITORY_ROOT / name) for name in config["protected_wip"]}
    if protected != config["protected_wip"]:
        raise RuntimeError(f"PROTECTED_WIP_DRIFT:{protected}")

    runtime = config["runtime"]
    adb = (REPOSITORY_ROOT / runtime["adb_binary"]).resolve()
    prefix = [str(adb), "-P", str(runtime["adb_server_port"]), "-s", runtime["device_serial"]]
    records: dict[str, Any] = {}
    payloads: dict[str, bytes] = {}
    host_commands = {
        "netstat": ["netstat", "-ano", "-p", "tcp"],
        "process_inventory": [
            "powershell", "-NoProfile", "-Command",
            "Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'adb|qemu|emulator|python'} | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine,CreationDate | ConvertTo-Json -Depth 3",
        ],
        "git_status": ["git", "status", "--porcelain=v1"],
    }
    for name, command in host_commands.items():
        record, stdout, _ = run(command, root=output_root / "raw", name=name)
        records[name], payloads[name] = record, stdout
    device_commands = {
        "adb_version": [str(adb), "version"],
        "adb_devices": [str(adb), "-P", "5038", "devices", "-l"],
        "get_state": prefix + ["get-state"],
        "boot_completed": prefix + ["shell", "getprop", "sys.boot_completed"],
        "build_fingerprint": prefix + ["shell", "getprop", "ro.build.fingerprint"],
        "product_model": prefix + ["shell", "getprop", "ro.product.model"],
        "service_package": prefix + ["shell", "service", "check", "package"],
        "service_window": prefix + ["shell", "service", "check", "window"],
        "service_activity": prefix + ["shell", "service", "check", "activity"],
        "power": prefix + ["shell", "dumpsys", "power"],
        "window_displays": prefix + ["shell", "dumpsys", "window", "displays"],
        "window_policy": prefix + ["shell", "dumpsys", "window", "policy"],
        "activity_activities": prefix + ["shell", "dumpsys", "activity", "activities"],
        "accessibility": prefix + ["shell", "dumpsys", "accessibility"],
        "screenshot": prefix + ["exec-out", "screencap", "-p"],
        "logcat": prefix + ["logcat", "-d", "-b", "all", "-v", "threadtime", "-t", "5000"],
    }
    for name, command in device_commands.items():
        record, stdout, _ = run(command, root=output_root / "raw", name=name, timeout=60.0 if name == "logcat" else 30.0)
        records[name], payloads[name] = record, stdout

    netstat = payloads["netstat"].decode("utf-8", errors="replace")
    listeners = {str(port): listener_pids(netstat, port) for port in (5037, 5038, 5554, 5555, 8554)}
    process_payload = json.loads(payloads["process_inventory"].decode("utf-8", errors="strict") or "[]")
    processes = process_payload if isinstance(process_payload, list) else [process_payload]
    by_pid = {int(item["ProcessId"]): item for item in processes}
    adb_pids = listeners["5038"]
    qemu_pids = listeners["8554"]
    adb_pid = adb_pids[0] if len(adb_pids) == 1 else None
    qemu_pid = qemu_pids[0] if len(qemu_pids) == 1 else None
    launcher_pid = int(by_pid[qemu_pid]["ParentProcessId"]) if qemu_pid in by_pid else None
    launcher = by_pid.get(launcher_pid)
    owned = {
        "adb_pid": adb_pid,
        "adb_process": by_pid.get(adb_pid),
        "launcher_pid": launcher_pid,
        "launcher_process": launcher,
        "qemu_pid": qemu_pid,
        "qemu_process": by_pid.get(qemu_pid),
        "listeners": listeners,
    }
    all_runtime_pids = sorted(
        int(item["ProcessId"]) for item in processes
        if str(item.get("Name", "")).casefold() in {"adb.exe", "emulator.exe", "qemu-system-x86_64-headless.exe"}
    )
    owned_pids = {pid for pid in (adb_pid, launcher_pid, qemu_pid) if pid is not None}
    excluded = [pid for pid in all_runtime_pids if pid not in owned_pids]

    avd_files = {}
    for name in ("avd_ini", "avd_config"):
        path = REPOSITORY_ROOT / runtime[name]
        avd_files[runtime[name]] = {"sha256": digest_path(path), "bytes": path.stat().st_size}
    for relative in (
        "06_local_runtime/android/avd/AndroidWorldAvd.avd/hardware-qemu.ini",
        "06_local_runtime/android/avd/AndroidWorldAvd.avd/emu-launch-params.txt",
    ):
        path = REPOSITORY_ROOT / relative
        if path.is_file():
            avd_files[relative] = {"sha256": digest_path(path), "bytes": path.stat().st_size}

    binary_files = {}
    for name in ("adb_binary", "emulator_launcher", "qemu_binary"):
        path = REPOSITORY_ROOT / runtime[name]
        binary_files[runtime[name]] = {"sha256": digest_path(path), "bytes": path.stat().st_size}

    degraded_markers = {}
    for name in ("power", "window_displays", "window_policy", "activity_activities"):
        stdout_text = payloads[name].decode("utf-8", errors="replace")
        stderr_path = REPOSITORY_ROOT / records[name]["stderr"]["path"]
        stderr_text = stderr_path.read_bytes().decode("utf-8", errors="replace")
        text = stdout_text + "\n" + stderr_text
        degraded_markers[name] = {
            "dead_object": "DEAD_OBJECT" in text,
            "service_error": "Error with service" in text,
            "service_missing": "Can't find service" in text,
            "stdout_empty": not bool(stdout_text.strip()),
            "stderr_nonempty": bool(stderr_text.strip()),
            "timed_out": records[name]["timed_out"],
            "returncode": records[name]["returncode"],
        }
    inventory = {
        "schema_version": "role_binding_timing.infra_m1.pre_inventory.v1",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=True).stdout.strip(),
        "development_contaminated": True,
        "generation_calls": 0,
        "device_mutations": 0,
        "project_owned": owned,
        "excluded_process_pids": excluded,
        "all_processes": processes,
        "avd_files": avd_files,
        "binary_files": binary_files,
        "degraded_markers": degraded_markers,
        "records": records,
        "protected_wip": protected,
    }
    inventory_path = output_root / "pre_maintenance_inventory.json"
    inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts = []
    for path in sorted(output_root.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.json":
            artifacts.append({"path": path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": digest_path(path)})
    (output_root / "artifact_manifest.json").write_text(json.dumps({"schema_version": "role_binding_timing.infra_m1.pre_inventory_manifest.v1", "artifacts": artifacts}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"owned": owned, "excluded": excluded, "degraded_markers": degraded_markers}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
