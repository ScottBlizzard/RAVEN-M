"""Pure runtime and registration guards for INFRA-M2."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from raven_m.role_binding_timing.infra_m1_runtime import process_matches


def prepare_emulator_environment(
    base: Mapping[str, str], *, adb_port: int, avd_home: str, sdk_root: str,
) -> dict[str, str]:
    if adb_port != 5038:
        raise ValueError("INFRA_M2_REQUIRES_ADB_5038")
    for name in ("ADB_SERVER_SOCKET", "ANDROID_ADB_SERVER_ADDRESS"):
        if base.get(name):
            raise ValueError(f"CONFLICTING_ADB_ENVIRONMENT:{name}")
    result = dict(base)
    result["ANDROID_ADB_SERVER_PORT"] = "5038"
    result["ANDROID_AVD_HOME"] = str(Path(avd_home).resolve())
    result["ANDROID_SDK_ROOT"] = str(Path(sdk_root).resolve())
    return result


def forbidden_5037_evidence(snapshot: dict[str, Any]) -> list[str]:
    evidence: list[str] = []
    for pid in snapshot.get("listeners", {}).get("5037", []):
        evidence.append(f"LISTENER:{pid}")
    for pid, record in snapshot.get("excluded_runtime_processes", {}).items():
        command = str(record.get("CommandLine") or record.get("command_line") or "")
        if "tcp:5037" in command.casefold():
            evidence.append(f"PROCESS:{pid}:{command}")
    return evidence


def pre_cleanup_ownership_issues(
    snapshot: dict[str, Any], *, config: dict[str, Any], repository_root: Path,
) -> list[str]:
    runtime = config["runtime"]
    expected = config["pre_cleanup_identity"]
    issues: list[str] = []
    listeners = snapshot["listeners"]
    if listeners["5037"] != [expected["adb_5037_pid"]]:
        issues.append("ADB_5037_LISTENER")
    if listeners["5038"] != [expected["adb_5038_pid"]]:
        issues.append("ADB_5038_LISTENER")
    if any(listeners[str(port)] != [expected["qemu_pid"]] for port in (5554, 5555, 8554)):
        issues.append("EMULATOR_LISTENERS")
    if snapshot.get("adb_pid") != expected["adb_5038_pid"]:
        issues.append("ADB_5038_PID")
    if snapshot.get("launcher_pid") != expected["launcher_pid"]:
        issues.append("LAUNCHER_PID")
    if snapshot.get("qemu_pid") != expected["qemu_pid"]:
        issues.append("QEMU_PID")
    if sorted(pid for pid in snapshot.get("excluded_runtime_pids", []) if pid != expected["adb_5037_pid"]) != expected["excluded_runtime_pids"]:
        issues.append("EXCLUDED_PID_SET")
    adb_5037 = snapshot.get("excluded_runtime_processes", {}).get(str(expected["adb_5037_pid"]))
    expected_adb = str((repository_root / runtime["adb_binary"]).resolve())
    if not adb_5037 or not process_matches(adb_5037, expected_path=expected_adb, required_command_parts=["tcp:5037", "fork-server"]):
        issues.append("ADB_5037_PROCESS")
    return issues

def clean_baseline_issues(snapshot: dict[str, Any], *, excluded_pids: list[int]) -> list[str]:
    issues: list[str] = []
    if any(snapshot.get("listeners", {}).get(str(port)) for port in (5037, 5038, 5554, 5555, 8554)):
        issues.append("PORT_RESIDUE")
    if snapshot.get("adb_pid") or snapshot.get("launcher_pid") or snapshot.get("qemu_pid"):
        issues.append("OWNED_PROCESS_RESIDUE")
    if snapshot.get("excluded_runtime_pids", []) != excluded_pids:
        issues.append("EXCLUDED_PID_DRIFT")
    return issues
