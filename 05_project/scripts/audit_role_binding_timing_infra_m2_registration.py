"""Capture the read-only INFRA-M2 emulator-to-ADB registration audit."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
OUTPUT_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m2_registration_audit"
EMU = REPOSITORY_ROOT / "06_local_runtime/android/sdk/emulator/emulator.exe"
QEMU = REPOSITORY_ROOT / "06_local_runtime/android/sdk/emulator/qemu/windows-x86_64/qemu-system-x86_64-headless.exe"
ADB = REPOSITORY_ROOT / "06_local_runtime/android/sdk/platform-tools/adb.exe"
PROTECTED = {
    "05_project/src/raven_m/controller/episode_controller.py": "fc0e82e0fde90119365d4f685f080eb4519bf2f602e4bda58de5d4809a40fe33",
    "05_project/src/raven_m/controller/protocol_v2_guard.py": "ff89d6b70be4b4738646d262beb67d7b7e932e9eb95956d940b1c5000a999d10",
    "05_project/tests/scripts/test_protocol_v2_2_r79_r78_trace_replay.py": "5bb1f1e3de673a1072cfee62938b761a62fd69c187d5eadf54bc46b115a3fd0a",
}


def digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def digest_path(path: Path) -> str:
    return digest(path.read_bytes())


def save_bytes(path: Path, raw: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {"path": path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": len(raw), "sha256": digest(raw)}


def run_raw(name: str, command: list[str], timeout: float = 60.0) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=REPOSITORY_ROOT, capture_output=True, text=False, check=False, timeout=timeout)
        stdout, stderr = bytes(result.stdout), bytes(result.stderr)
        returncode, timed_out = result.returncode, False
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = bytes(exc.stdout or b""), bytes(exc.stderr or b"")
        returncode, timed_out = None, True
    return {
        "command": command,
        "returncode": returncode,
        "timed_out": timed_out,
        "wall_time_seconds": time.monotonic() - started,
        "stdout": save_bytes(OUTPUT_ROOT / "raw" / f"{name}.stdout.bin", stdout),
        "stderr": save_bytes(OUTPUT_ROOT / "raw" / f"{name}.stderr.bin", stderr),
    }


def printable_strings(raw: bytes, minimum: int = 4) -> list[str]:
    return [item.decode("ascii") for item in re.findall(rb"[\x20-\x7e]{%d,}" % minimum, raw)]


def binary_evidence(path: Path, needles: list[str]) -> dict[str, Any]:
    raw = path.read_bytes()
    strings = printable_strings(raw)
    hits: dict[str, list[dict[str, Any]]] = {}
    for needle in needles:
        values = []
        for index, value in enumerate(strings):
            if needle.casefold() in value.casefold():
                values.append({
                    "string_index": index,
                    "previous": strings[max(0, index - 2):index],
                    "value": value,
                    "next": strings[index + 1:index + 3],
                })
        hits[needle] = values
    return {
        "path": path.relative_to(REPOSITORY_ROOT).as_posix(),
        "bytes": len(raw),
        "sha256": digest(raw),
        "needles": hits,
    }


def source_evidence(path: Path, needles: list[str], radius: int = 5) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    hits = []
    for index, line in enumerate(lines):
        if any(needle.casefold() in line.casefold() for needle in needles):
            start, end = max(0, index - radius), min(len(lines), index + radius + 1)
            hits.append({
                "line": index + 1,
                "context": [{"line": cursor + 1, "text": lines[cursor]} for cursor in range(start, end)],
            })
    return {
        "path": path.relative_to(REPOSITORY_ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": digest_path(path),
        "hits": hits,
    }


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise RuntimeError("AUDIT_OUTPUT_NOT_FRESH")
    OUTPUT_ROOT.mkdir(parents=True)
    (OUTPUT_ROOT / ".gitattributes").write_text("*.bin binary\n", encoding="ascii")
    protected = {relative: digest_path(REPOSITORY_ROOT / relative) for relative in PROTECTED}
    if protected != PROTECTED:
        raise RuntimeError(f"PROTECTED_WIP_DRIFT:{protected}")

    commands = {
        "emulator_version": [str(EMU), "-version"],
        "emulator_help_environment": [str(EMU), "-help-environment"],
        "emulator_help_port": [str(EMU), "-help-port"],
        "emulator_help_ports": [str(EMU), "-help-ports"],
        "emulator_help_adb_path": [str(EMU), "-help-adb_path"],
        "emulator_help_no_direct_adb": [str(EMU), "-help-no_direct_adb"],
        "emulator_help_all": [str(EMU), "-help-all"],
        "adb_version": [str(ADB), "version"],
        "adb_help": [str(ADB), "help"],
        "netstat": ["netstat", "-ano", "-p", "tcp"],
        "process_inventory": [
            "powershell", "-NoProfile", "-Command",
            "Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'adb|qemu|emulator'} | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine,CreationDate | ConvertTo-Json -Depth 3",
        ],
        "git_status": ["git", "status", "--porcelain=v1"],
    }
    records = {name: run_raw(name, command, timeout=120.0 if name == "emulator_help_all" else 60.0) for name, command in commands.items()}

    binary = {
        "emulator_launcher": binary_evidence(EMU, ["ANDROID_ADB_SERVER_PORT", "adb-path", "no-direct-adb"]),
        "emulator_qemu": binary_evidence(QEMU, ["ANDROID_ADB_SERVER_PORT", "Unable to connect to adb daemon on port", "AdbHostServer.cpp", "1..65535"]),
        "adb": binary_evidence(ADB, ["ANDROID_ADB_SERVER_PORT", "ADB_SERVER_SOCKET", "ANDROID_ADB_SERVER_ADDRESS", "positive number less than 65535"]),
    }
    source = {
        "prior_project_cold_restart": source_evidence(
            PROJECT_ROOT / "scripts/collect_role_binding_timing_phase_b2_v0_2.py",
            ["ANDROID_ADB_SERVER_PORT", "subprocess.Popen"],
        ),
        "infra_m1_runner": source_evidence(
            PROJECT_ROOT / "scripts/run_role_binding_timing_infra_m1_maintenance.py",
            ["ANDROID_ADB_SERVER_PORT", "subprocess.Popen", "ANDROID_AVD_HOME"],
        ),
        "infra_m1_emulator_log": source_evidence(
            PROJECT_ROOT / "artifacts/role_binding_timing/infra_m1_maintenance_burnin/maintenance/start/emulator.stdout.bin",
            ["Unable to connect to adb daemon on port: 5037", "Boot completed in"],
            radius=1,
        ),
    }
    environment = {
        name: {"present": name in os.environ, "value": os.environ.get(name)}
        for name in ("ANDROID_ADB_SERVER_PORT", "ADB_SERVER_SOCKET", "ANDROID_ADB_SERVER_ADDRESS", "ANDROID_AVD_HOME", "ANDROID_SDK_ROOT")
    }
    audit = {
        "schema_version": "role_binding_timing.infra_m2.registration_audit.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=True).stdout.strip(),
        "development_contaminated": True,
        "generation_calls": 0,
        "held_out_captures": 0,
        "device_mutations": 0,
        "restart_attempts": 0,
        "protected_wip": protected,
        "environment": environment,
        "records": records,
        "binary_evidence": binary,
        "source_evidence": source,
        "claim_evidence": {
            "verified_registration_control": "ANDROID_ADB_SERVER_PORT",
            "verified_value_for_project_server": "5038",
            "correction_scope": "set inherited emulator-process environment before Popen",
            "launch_argument_not_selected": ["-ports", "-adb-path", "-no-direct-adb"],
            "eligible_for_m2_protocol_freeze": True,
        },
    }
    audit_path = OUTPUT_ROOT / "registration_audit.json"
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts = []
    for path in sorted(OUTPUT_ROOT.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.json":
            artifacts.append({"path": path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": digest_path(path)})
    manifest = {"schema_version": "role_binding_timing.infra_m2.registration_audit_manifest.v1", "artifacts": artifacts}
    (OUTPUT_ROOT / "artifact_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"eligible_for_m2_protocol_freeze": True, "generation_calls": 0, "device_mutations": 0, "artifact_count": len(artifacts)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
