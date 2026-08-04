"""Pure qualification helpers for INFRA-M1 maintenance and burn-in."""

from __future__ import annotations

import re
from typing import Any


def listener_pids(netstat: str, port: int) -> list[int]:
    result: set[int] = set()
    for line in netstat.splitlines():
        fields = line.split()
        if len(fields) < 5 or fields[0].upper() != "TCP" or fields[3].upper() != "LISTENING":
            continue
        if fields[1].rsplit(":", 1)[-1] == str(port):
            try:
                result.add(int(fields[-1]))
            except ValueError:
                pass
    return sorted(result)


def parse_framework_service(raw: bytes, expected: str) -> bool:
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return False
    normalized = " ".join(text.split()).casefold()
    return normalized == f"service {expected}: found".casefold()


def parse_runtime_state(power: str, displays: str, policy: str) -> dict[str, bool]:
    combined = "\n".join((power, displays, policy))
    dead = "DEAD_OBJECT" in combined or "Error with service" in combined
    awake = bool(re.search(r"(?:mWakefulness=|Wakefulness:\s*)Awake\b", power, flags=re.IGNORECASE))
    explicit_interactive = re.search(r"mInteractive\s*=\s*(true|false)\b", power, flags=re.IGNORECASE)
    interactive = (
        explicit_interactive.group(1).casefold() == "true"
        if explicit_interactive
        else awake
    )
    display_on = bool(re.search(r"(?:state|mState)\s*(?:=|\s)\s*ON\b", displays, flags=re.IGNORECASE))
    keyguard_block = re.search(
        r"KeyguardServiceDelegate\b(?P<body>[\s\S]{0,2048}?)(?=\n\s*\S[^\n]*:\s*$|\Z)",
        policy,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    keyguard_text = keyguard_block.group("body") if keyguard_block else policy
    showing_true = bool(
        re.search(
            r"(?:^|\s)(?:showing|isShowing|mShowing|keyguardShowing|mKeyguardShowing)\s*=\s*true\b",
            keyguard_text,
            flags=re.IGNORECASE,
        )
    )
    showing_false = bool(
        re.search(
            r"(?:^|\s)(?:showing|isShowing|mShowing|keyguardShowing|mKeyguardShowing)\s*=\s*false\b",
            keyguard_text,
            flags=re.IGNORECASE,
        )
    )
    return {
        "no_dead_object": not dead,
        "awake": awake,
        "interactive": interactive,
        "display_on": display_on,
        "keyguard_not_showing": showing_false and not showing_true,
    }


def process_matches(
    record: dict[str, Any], *, expected_path: str, required_command_parts: list[str],
) -> bool:
    path = str(record.get("executable_path") or record.get("ExecutablePath") or "").casefold()
    command = str(record.get("command_line") or record.get("CommandLine") or "").casefold()
    return path == expected_path.casefold() and all(part.casefold() in command for part in required_command_parts)


def continuity_issues(
    *, current: dict[str, Any], expected: dict[str, Any], required_ports: dict[str, int],
) -> list[str]:
    issues: list[str] = []
    if current.get("adb_pid") != expected.get("adb_pid"):
        issues.append("ADB_PID_DRIFT")
    if current.get("launcher_pid") != expected.get("launcher_pid"):
        issues.append("LAUNCHER_PID_DRIFT")
    if current.get("qemu_pid") != expected.get("qemu_pid"):
        issues.append("QEMU_PID_DRIFT")
    if current.get("fallback_5037_pids"):
        issues.append("FORBIDDEN_5037")
    listeners = current.get("listeners", {})
    for name, port in required_ports.items():
        owner = expected.get(f"{name}_pid")
        if listeners.get(str(port)) != [owner]:
            issues.append(f"PORT_OWNER:{port}")
    return issues
