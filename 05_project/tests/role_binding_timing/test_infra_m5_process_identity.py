from __future__ import annotations

import json
from pathlib import Path

import pytest

from raven_m.role_binding_timing.infra_m5_process_identity import (
    allowed_bootstrap_adb_command,
    ExecutableHashCache,
    ProcessIdentityMonitor,
    StructuralIdentityPolicy,
    identity_key,
)


def config() -> dict:
    return {
        "runtime": {
            "device_serial": "emulator-5554",
            "emulator_args": ["-avd", "AndroidWorldAvd", "-port", "5554", "-grpc", "8554", "-no-window"],
        },
        "process_identity": {
            "continuous_sample_interval_seconds": 0.25,
            "max_parent_depth": 8,
            "bootstrap_helper_window_seconds": 300,
            "runtime_helper_window_seconds": 900,
            "binaries": {
                "adb": {"path": "C:/locked/adb.exe", "sha256": "adb-hash"},
                "emulator_launcher": {"path": "C:/locked/emulator.exe", "sha256": "launcher-hash"},
                "qemu": {"path": "C:/locked/qemu-system-x86_64-headless.exe", "sha256": "qemu-hash"},
                "crashpad": {"path": "C:/locked/crashpad_handler.exe", "sha256": "crash-hash"},
                "netsimd": {"path": "C:/locked/netsimd.exe", "sha256": "netsim-hash"},
                "command_wrapper": {"path": "C:/Windows/System32/cmd.exe", "sha256": "cmd-hash"},
            },
        },
    }


def record(
    pid: int, name: str, exe: str, digest: str, command: str, ppid: int,
    created: float,
) -> dict:
    return {
        "pid": pid, "ppid": ppid, "name": name, "exe": exe,
        "command_line": command, "cmdline_items": command.split(),
        "create_time": created, "identity_key": f"{pid}@{created:.6f}",
        "exe_sha256": digest, "access_error": None,
    }


RUNNER = record(10, "python.exe", "C:/Python/python.exe", "python-hash", "python frozen.py", 1, 10.0)
ADB = record(20, "adb.exe", "C:/locked/adb.exe", "adb-hash", "adb -L tcp:5038 fork-server server --reply-fd 7", 10, 20.0)
LAUNCHER = record(30, "emulator.exe", "C:/locked/emulator.exe", "launcher-hash", "emulator -avd AndroidWorldAvd -port 5554 -grpc 8554 -no-window", 10, 30.0)
QEMU = record(40, "qemu-system-x86_64-headless.exe", "C:/locked/qemu-system-x86_64-headless.exe", "qemu-hash", "qemu -avd AndroidWorldAvd -port 5554 -grpc 8554 -no-window", 30, 31.0)


def snapshot(
    structural: list[dict], *, listeners: dict[str, list[int]] | None = None,
    gate: str = "test", sequence: int = 1,
) -> dict:
    return {
        "schema_version": "role_binding_timing.infra_m5.process_snapshot.v1",
        "sequence": sequence, "captured_at": "2026-08-05T00:00:00+00:00",
        "captured_monotonic": 1.0, "gate": gate,
        "listeners": listeners or {"5037": [], "5038": [20], "5554": [40], "5555": [40], "8554": [40]},
        "all_processes": structural, "structural_processes": structural,
        "relevant_identity_keys": [identity_key(item) for item in structural],
        "raw_netstat_sha256": "0" * 64,
    }


def qualified_policy(*, baseline_records: list[dict] | None = None) -> StructuralIdentityPolicy:
    policy = StructuralIdentityPolicy(config(), runner_record=RUNNER)
    policy.freeze_baseline(snapshot(baseline_records or [], listeners={"5037": [], "5038": [], "5554": [], "5555": [], "8554": []}))
    policy.register_core("adb_server", ADB)
    policy.register_core("emulator_launcher", LAUNCHER)
    policy.register_core("qemu", QEMU)
    policy.add_history([RUNNER, ADB, LAUNCHER, QEMU])
    return policy


def core_snapshot(extra: list[dict] | None = None, **kwargs) -> dict:
    return snapshot([RUNNER, ADB, LAUNCHER, QEMU, *(extra or [])], **kwargs)


def test_allowed_short_lived_official_child_helper() -> None:
    helper = record(50, "crashpad_handler.exe", "C:/locked/crashpad_handler.exe", "crash-hash", "crashpad_handler --database=x", 40, 32.0)
    result = qualified_policy().evaluate(core_snapshot([helper]), phase="framework")
    assert result.passed, result.issues
    assert result.roles[identity_key(helper)] == "crashpad"
    assert result.helper_ancestry[identity_key(helper)] == [identity_key(QEMU)]


def test_allowed_runner_adb_client_is_not_adopted_as_server() -> None:
    client = record(51, "adb.exe", "C:/locked/adb.exe", "adb-hash", "C:/locked/adb.exe -P 5038 -s emulator-5554 shell getprop x", 10, 33.0)
    result = qualified_policy().evaluate(core_snapshot([client]), phase="burn_in")
    assert result.passed, result.issues
    assert result.roles[identity_key(client)] == "runner_adb_client"


def test_exact_frozen_multidisplay_helper_command_is_recognized() -> None:
    command = (
        "C:/locked/adb.exe -s emulator-5554 shell am broadcast "
        "-a com.android.emulator.multidisplay.START -n "
        "com.android.emulator.multidisplay/.MultiDisplayServiceReceiver \"--user 0\""
    )
    assert allowed_bootstrap_adb_command(
        command, adb_path="C:/locked/adb.exe", serial="emulator-5554",
    )


def test_exact_bootstrap_helper_through_locked_wrapper_is_admitted() -> None:
    wrapper = record(
        49, "cmd.exe", "C:/Windows/System32/cmd.exe", "cmd-hash",
        "cmd.exe /c C:/locked/adb.exe -s emulator-5554 shell cmd overlay enable-exclusive --user current --category com.android.internal.emulation.pixel_6",
        40, 31.5,
    )
    helper = record(
        50, "adb.exe", "C:/locked/adb.exe", "adb-hash",
        "C:/locked/adb.exe -s emulator-5554 shell cmd overlay enable-exclusive --user current --category com.android.internal.emulation.pixel_6",
        49, 32.0,
    )
    result = qualified_policy().evaluate(core_snapshot([wrapper, helper]), phase="framework")
    assert result.passed, result.issues
    assert result.roles[identity_key(helper)] == "emulator_bootstrap_adb"
    assert result.helper_ancestry[identity_key(helper)] == [identity_key(wrapper), identity_key(QEMU)]


def test_helper_outside_preregistered_time_window_is_rejected() -> None:
    helper = record(52, "crashpad_handler.exe", "C:/locked/crashpad_handler.exe", "crash-hash", "crashpad_handler --database=x", 40, 1000.0)
    result = qualified_policy().evaluate(core_snapshot([helper]), phase="framework")
    assert not result.passed
    assert any("HELPER_TIME_WINDOW" in issue for issue in result.issues)


@pytest.mark.parametrize(
    "bad,needle",
    [
        (record(60, "adb.exe", "C:/evil/adb.exe", "evil", "C:/evil/adb.exe -P 5038 devices", 10, 35.0), "UNKNOWN_NEW_PROCESS"),
        (record(61, "crashpad_handler.exe", "C:/locked/crashpad_handler.exe", "crash-hash", "crashpad_handler", 999, 35.0), "HELPER_PARENT_CHAIN"),
        (record(62, "netsimd.exe", "", "", "", 40, 35.0), "MISSING_IDENTITY_EVIDENCE"),
    ],
)
def test_forbidden_new_binary_parent_mismatch_and_missing_evidence(bad: dict, needle: str) -> None:
    result = qualified_policy().evaluate(core_snapshot([bad]), phase="framework")
    assert not result.passed
    assert any(needle in issue for issue in result.issues)


def test_pid_reuse_of_preexisting_unrelated_fails_closed() -> None:
    old = record(90, "adb.exe", "", "", "", 1, 1.0)
    new = record(90, "adb.exe", "C:/locked/adb.exe", "adb-hash", "C:/locked/adb.exe -P 5038 devices", 10, 50.0)
    result = qualified_policy(baseline_records=[old]).evaluate(core_snapshot([new]), phase="framework")
    assert not result.passed
    assert any(issue.startswith("PID_REUSE:90") for issue in result.issues)


def test_port_owner_change_fails_closed() -> None:
    listeners = {"5037": [], "5038": [999], "5554": [40], "5555": [40], "8554": [40]}
    result = qualified_policy().evaluate(core_snapshot(listeners=listeners), phase="framework")
    assert not result.passed
    assert any(issue.startswith("PORT_OWNER:5038") for issue in result.issues)


def test_5038_server_restart_same_binary_and_command_is_rejected() -> None:
    replacement = record(21, "adb.exe", "C:/locked/adb.exe", "adb-hash", "adb -L tcp:5038 fork-server server --reply-fd 8", 10, 60.0)
    listeners = {"5037": [], "5038": [21], "5554": [40], "5555": [40], "8554": [40]}
    result = qualified_policy().evaluate(snapshot([RUNNER, replacement, LAUNCHER, QEMU], listeners=listeners), phase="burn_in")
    assert not result.passed
    assert any("CORE_MISSING:adb_server" in issue for issue in result.issues)
    assert any(issue.startswith("PORT_OWNER:5038") for issue in result.issues)


def test_core_pid_reuse_same_pid_new_creation_time_is_rejected() -> None:
    reused = {**ADB, "create_time": 80.0, "identity_key": "20@80.000000"}
    result = qualified_policy().evaluate(snapshot([RUNNER, reused, LAUNCHER, QEMU]), phase="burn_in")
    assert not result.passed
    assert "CORE_PID_REUSE:adb_server:20" in result.issues


def test_preexisting_unrelated_has_no_authority_and_disappearance_is_allowed() -> None:
    old = record(90, "adb.exe", "", "", "", 1, 1.0)
    policy = qualified_policy(baseline_records=[old])
    present = policy.evaluate(core_snapshot([old]), phase="framework")
    absent = policy.evaluate(core_snapshot(), phase="burn_in")
    assert present.passed and absent.passed
    assert present.roles[identity_key(old)] == "preexisting_unrelated_no_authority"
    assert identity_key(old) not in {identity_key(value) for value in policy.core.values()}


def test_failure_snapshot_is_persisted_before_return(tmp_path: Path) -> None:
    baseline = snapshot([], listeners={"5037": [], "5038": [], "5554": [], "5555": [], "8554": []}, gate="baseline", sequence=1)
    bad = record(70, "adb.exe", "C:/evil/adb.exe", "evil", "C:/evil/adb.exe -P 5038 devices", 10, 70.0)
    failing = core_snapshot([bad], gate="framework", sequence=2)
    queue = [(baseline, b"baseline"), (failing, b"failing")]

    def provider(gate: str, sequence: int, cache: ExecutableHashCache):
        return queue.pop(0)

    monitor = ProcessIdentityMonitor(root=tmp_path / "monitor", config=config(), runner_record=RUNNER, snapshot_provider=provider)
    assert monitor.capture(gate="baseline", phase="launch", mode="baseline")["passed"]
    monitor.policy.register_core("adb_server", ADB)
    monitor.policy.register_core("emulator_launcher", LAUNCHER)
    monitor.policy.register_core("qemu", QEMU)
    result = monitor.capture(gate="framework", phase="framework")
    assert not result["passed"]
    failure = json.loads((tmp_path / "monitor/first_process_identity_failure.json").read_text(encoding="utf-8"))
    assert failure["gate"] == "framework"
    assert any("UNKNOWN_NEW_PROCESS" in issue for issue in failure["issues"])
    assert failure["triggering_snapshot"]["sequence"] == 2
    assert (tmp_path / "monitor/snapshots/0002_framework/process_snapshot.json").is_file()


def test_second_failure_cannot_replace_first_snapshot(tmp_path: Path) -> None:
    baseline = snapshot([], listeners={"5037": [], "5038": [], "5554": [], "5555": [], "8554": []}, sequence=1)
    first = core_snapshot([record(71, "adb.exe", "C:/evil/one.exe", "one", "one", 10, 71.0)], gate="one", sequence=2)
    second = core_snapshot([record(72, "adb.exe", "C:/evil/two.exe", "two", "two", 10, 72.0)], gate="two", sequence=3)
    queue = [(baseline, b"baseline"), (first, b"one"), (second, b"two")]
    monitor = ProcessIdentityMonitor(root=tmp_path / "monitor", config=config(), runner_record=RUNNER, snapshot_provider=lambda *args: queue.pop(0))
    monitor.capture(gate="baseline", phase="launch", mode="baseline")
    for role, value in (("adb_server", ADB), ("emulator_launcher", LAUNCHER), ("qemu", QEMU)):
        monitor.policy.register_core(role, value)
    monitor.capture(gate="one", phase="framework")
    original = (tmp_path / "monitor/first_process_identity_failure.json").read_bytes()
    monitor.capture(gate="two", phase="cleanup")
    assert (tmp_path / "monitor/first_process_identity_failure.json").read_bytes() == original
