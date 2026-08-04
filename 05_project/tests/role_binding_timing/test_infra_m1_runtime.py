from __future__ import annotations

import pytest

from raven_m.role_binding_timing.infra_m1_runtime import (
    continuity_issues,
    listener_pids,
    parse_framework_service,
    parse_runtime_state,
    process_matches,
)


def test_listener_parser_deduplicates_and_requires_listening() -> None:
    raw = """
 TCP 127.0.0.1:5038 0.0.0.0:0 LISTENING 12
 TCP 127.0.0.1:5038 0.0.0.0:0 LISTENING 12
 TCP 127.0.0.1:5038 127.0.0.1:9 ESTABLISHED 99
    """
    assert listener_pids(raw, 5038) == [12]


@pytest.mark.parametrize("raw", [b"", b"Service package: not found\r\n", b"\xff", b"Service window: found\r\n"])
def test_framework_service_fails_closed(raw: bytes) -> None:
    assert parse_framework_service(raw, "package") is False


def test_framework_service_accepts_exact_normalized_form() -> None:
    assert parse_framework_service(b"Service package: found\r\n", "package") is True


def test_runtime_state_accepts_awake_interactive_display_and_unlocked() -> None:
    result = parse_runtime_state(
        "mWakefulness=Awake\nmInteractive=true",
        "DisplayInfo state=ON",
        "KeyguardServiceDelegate showing=false",
    )
    assert all(result.values())


def test_runtime_state_ignores_non_keyguard_showing_fields() -> None:
    result = parse_runtime_state(
        "mWakefulness=Awake\nmInteractive=true",
        "DisplayInfo state=ON",
        """Overlay showing=true
    KeyguardServiceDelegate
      showing=false
      showingAndNotOccluded=true
      interactiveState=INTERACTIVE_STATE_AWAKE
    OtherSection:
      mShowing=true
""",
    )
    assert result["keyguard_not_showing"] is True


@pytest.mark.parametrize("field", ["showing", "isShowing", "mShowing", "keyguardShowing", "mKeyguardShowing"])
def test_runtime_state_recognizes_keyguard_field_variants(field: str) -> None:
    common = ("mWakefulness=Awake\nmInteractive=true", "DisplayInfo state=ON")
    assert parse_runtime_state(*common, f"{field}=false")["keyguard_not_showing"] is True
    assert parse_runtime_state(*common, f"{field}=true")["keyguard_not_showing"] is False


@pytest.mark.parametrize(
    ("power", "display", "policy", "key"),
    [
        ("mWakefulness=Asleep\nmInteractive=false", "state=ON", "showing=false", "awake"),
        ("mWakefulness=Awake\nmInteractive=false", "state=ON", "showing=false", "interactive"),
        ("mWakefulness=Awake\nmInteractive=true", "state=OFF", "showing=false", "display_on"),
        ("mWakefulness=Awake\nmInteractive=true", "state=ON", "showing=true", "keyguard_not_showing"),
        ("Error with service 'power': DEAD_OBJECT", "state=ON", "showing=false", "no_dead_object"),
    ],
)
def test_runtime_state_corruption_fails(power: str, display: str, policy: str, key: str) -> None:
    assert parse_runtime_state(power, display, policy)[key] is False


def test_process_match_requires_path_and_all_command_parts() -> None:
    record = {"executable_path": "D:/sdk/adb.exe", "command_line": "adb -L tcp:5038 fork-server server"}
    assert process_matches(record, expected_path="D:/sdk/adb.exe", required_command_parts=["tcp:5038", "fork-server"])
    assert not process_matches(record, expected_path="D:/other/adb.exe", required_command_parts=["tcp:5038"])
    assert not process_matches(record, expected_path="D:/sdk/adb.exe", required_command_parts=["tcp:5037"])


def test_process_match_accepts_windows_cim_field_names() -> None:
    record = {"ExecutablePath": "D:/sdk/adb.exe", "CommandLine": "adb -L tcp:5038 fork-server server"}
    assert process_matches(record, expected_path="D:/sdk/adb.exe", required_command_parts=["tcp:5038", "fork-server"])


def test_continuity_detects_pid_port_and_fallback() -> None:
    expected = {"adb_pid": 1, "launcher_pid": 2, "qemu_pid": 3, "console_pid": 3, "device_pid": 3, "grpc_pid": 3}
    current = {
        "adb_pid": 1, "launcher_pid": 2, "qemu_pid": 3,
        "fallback_5037_pids": [],
        "listeners": {"5038": [1], "5554": [3], "5555": [3], "8554": [3]},
    }
    ports = {"adb": 5038, "console": 5554, "device": 5555, "grpc": 8554}
    assert continuity_issues(current=current, expected=expected, required_ports=ports) == []
    current["fallback_5037_pids"] = [9]
    current["listeners"]["8554"] = [8]
    assert set(continuity_issues(current=current, expected=expected, required_ports=ports)) == {"FORBIDDEN_5037", "PORT_OWNER:8554"}
