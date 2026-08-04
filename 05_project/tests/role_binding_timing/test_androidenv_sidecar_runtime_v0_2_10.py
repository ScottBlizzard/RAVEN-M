from __future__ import annotations

import pytest

from raven_m.role_binding_timing.androidenv_sidecar_runtime_v0_2_10 import (
    ENABLE_GRPC,
    ENABLE_TREE,
    FORWARDER_COMPONENT,
    FORWARDER_RECEIVER,
    SET_GRPC,
    explicit_forwarder_broadcast_args,
    lifecycle_identity_issues,
    parse_accessibility_service_state,
)


def test_explicit_broadcasts_keep_flags_out_of_action() -> None:
    records = explicit_forwarder_broadcast_args(50069)
    assert records[0] == (
        "shell", "am", "broadcast", "-a", SET_GRPC,
        "--ei", "port", "50069", "-n", FORWARDER_RECEIVER,
    )
    assert records[1][4] == ENABLE_GRPC
    assert records[2][4] == ENABLE_TREE
    assert " " not in records[0][4]


@pytest.mark.parametrize("value", [0, -1, 65536, True, "50069", None])
def test_explicit_broadcast_port_fails_closed(value: object) -> None:
    with pytest.raises(ValueError, match="INVALID_SIDECAR_PORT"):
        explicit_forwarder_broadcast_args(value)  # type: ignore[arg-type]


def test_service_state_requires_bound_not_merely_binding() -> None:
    raw = f"""
     Bound services:{{}}
     Enabled services:{{{{{FORWARDER_COMPONENT}}}}}
     Binding services:{{{{{FORWARDER_COMPONENT}}}}}
     Crashed services:{{}}
    """
    assert parse_accessibility_service_state(raw) == {
        "enabled": True, "binding": True, "bound": False,
        "crashed": False, "qualified_bound": False,
    }


def test_service_state_accepts_bound_and_enabled() -> None:
    raw = f"""
     Bound services:{{{{{FORWARDER_COMPONENT}}}}}
     Enabled services:{{{{{FORWARDER_COMPONENT}}}}}
     Binding services:{{}}
     Crashed services:{{}}
    """
    assert parse_accessibility_service_state(raw)["qualified_bound"] is True


def test_service_state_crash_vetoes() -> None:
    raw = f"""
     Bound services:{{{{{FORWARDER_COMPONENT}}}}}
     Enabled services:{{{{{FORWARDER_COMPONENT}}}}}
     Binding services:{{}}
     Crashed services:{{{{{FORWARDER_COMPONENT}}}}}
    """
    assert parse_accessibility_service_state(raw)["qualified_bound"] is False


def _identity(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "adb_pid": 10,
        "emulator_grpc_pid": 20,
        "forwarder_pid": "30",
        "fallback_5037_listener_pids": [],
        "sidecar_host_listener_owned": True,
        "service_state": {"qualified_bound": True},
    }
    value.update(overrides)
    return value


def test_lifecycle_identity_accepts_exact_continuity() -> None:
    assert lifecycle_identity_issues(
        before=_identity(), after=_identity(), expected_adb_pid=10,
        expected_emulator_grpc_pid=20, expected_forwarder_pid="30",
    ) == []


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ({"adb_pid": 11}, "after:ADB_PID"),
        ({"emulator_grpc_pid": 21}, "after:EMULATOR_GRPC_PID"),
        ({"forwarder_pid": "31"}, "after:FORWARDER_PID"),
        ({"fallback_5037_listener_pids": [99]}, "after:FORBIDDEN_5037"),
        ({"sidecar_host_listener_owned": False}, "after:SIDECAR_LISTENER"),
        ({"service_state": {"qualified_bound": False}}, "after:SERVICE_NOT_BOUND"),
    ],
)
def test_lifecycle_identity_corruption_fails(override: dict[str, object], expected: str) -> None:
    issues = lifecycle_identity_issues(
        before=_identity(), after=_identity(**override), expected_adb_pid=10,
        expected_emulator_grpc_pid=20, expected_forwarder_pid="30",
    )
    assert expected in issues
