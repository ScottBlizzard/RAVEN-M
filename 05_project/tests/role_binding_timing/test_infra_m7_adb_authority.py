from __future__ import annotations

import json
from pathlib import Path
import time

import pytest

from raven_m.role_binding_timing.infra_m5_process_identity import identity_key
from raven_m.role_binding_timing.infra_m7_adb_authority import (
    M7ProcessIdentityMonitor,
    M7StructuralIdentityPolicy,
    annotate_listener_evidence,
    listener_ports_by_pid,
)


NOW = time.time()


def config() -> dict:
    return {
        "runtime": {"device_serial": "emulator-5554", "emulator_args": ["-avd", "AndroidWorldAvd", "-port", "5554", "-grpc", "8554", "-no-window"]},
        "runner_adb_client": {"max_active_lifetime_seconds": 45.0},
        "process_identity": {
            "continuous_sample_interval_seconds": 0.25,
            "max_parent_depth": 8,
            "bootstrap_helper_window_seconds": 300,
            "runtime_helper_window_seconds": 900,
            "shutdown_helper": {"command_executable": "C:/locked/emulator", "sleep_seconds": 20},
            "binaries": {
                "adb": {"path": "C:/locked/adb.exe", "sha256": "adb-hash"},
                "emulator_launcher": {"path": "C:/locked/emulator.exe", "sha256": "launcher-hash"},
                "qemu": {"path": "C:/locked/qemu.exe", "sha256": "qemu-hash"},
                "crashpad": {"path": "C:/locked/crashpad.exe", "sha256": "crash-hash"},
                "netsimd": {"path": "C:/locked/netsimd.exe", "sha256": "netsim-hash"},
                "command_wrapper": {"path": "C:/Windows/System32/cmd.exe", "sha256": "cmd-hash"},
            },
        },
    }


def record(pid: int, name: str, exe: str, digest: str, argv: list[str], ppid: int, created: float, *, listeners=None) -> dict:
    return {
        "pid": pid, "ppid": ppid, "name": name, "exe": exe,
        "command_line": " ".join(argv), "cmdline_items": argv,
        "create_time": created, "identity_key": f"{pid}@{created:.6f}",
        "exe_sha256": digest, "access_error": None,
        "listener_evidence_complete": True, "listener_ports": list(listeners or []),
    }


RUNNER = record(10, "python.exe", "C:/Python/python.exe", "python-hash", ["python", "frozen.py"], 1, NOW - 100)


def adb(pid: int = 50, args=None, *, ppid=10, created=None, path="C:/locked/adb.exe", digest="adb-hash", listeners=None):
    return record(pid, "adb.exe", path, digest, [path, "-P", "5038", *(args or ["devices", "-l"])], ppid, created or time.time() - 1, listeners=listeners)


def snapshot(records, *, sequence=1, gate="test", selected_listeners=None):
    return {
        "schema_version": "role_binding_timing.infra_m7.process_snapshot.v1",
        "sequence": sequence, "captured_at": "2026-08-05T00:00:00+00:00",
        "captured_monotonic": 1.0, "captured_epoch": NOW, "gate": gate,
        "listeners": selected_listeners or {"5037": [], "5038": [], "5554": [], "5555": [], "8554": []},
        "all_processes": records, "structural_processes": records,
        "relevant_identity_keys": [identity_key(item) for item in records],
        "raw_netstat_sha256": "0" * 64, "listener_evidence_complete": True,
        "all_tcp_listener_ports_by_pid": {str(item["pid"]): item["listener_ports"] for item in records if item["listener_ports"]},
    }


def policy(*, baseline=None):
    value = M7StructuralIdentityPolicy(config(), runner_record=RUNNER)
    value.freeze_baseline(snapshot(baseline or [], sequence=0, gate="baseline"))
    value.add_history([RUNNER])
    return value


@pytest.mark.parametrize("args", [
    ["devices", "-l"],
    ["-s", "emulator-5554", "get-state"],
    ["-s", "emulator-5554", "shell", "dumpsys", "power"],
    ["-s", "emulator-5554", "shell", "getprop", "sys.boot_completed"],
    ["-s", "emulator-5554", "exec-out", "screencap", "-p"],
])
def test_generic_direct_runner_clients_do_not_enumerate_harmless_subcommands(args) -> None:
    client = adb(args=args)
    result = policy().evaluate(snapshot([RUNNER, client]), phase="boot")
    assert result.passed, result.issues
    assert result.roles[identity_key(client)] == "runner_adb_client"


@pytest.mark.parametrize(("mutate", "needle"), [
    (lambda value: value.update(ppid=99), "PARENT"),
    (lambda value: value.update(exe="C:/other/adb.exe"), "UNKNOWN_NEW_PROCESS"),
    (lambda value: value.update(exe_sha256="wrong"), "HASH"),
    (lambda value: value.update(cmdline_items=["C:/locked/adb.exe", "-P", "5037", "devices"], command_line="C:/locked/adb.exe -P 5037 devices"), "PORT_NOT_5038"),
    (lambda value: value.update(cmdline_items=["C:/locked/adb.exe", "devices"], command_line="C:/locked/adb.exe devices"), "PORT_AMBIGUOUS_OR_MISSING"),
    (lambda value: value.update(cmdline_items=["C:/locked/adb.exe", "-s", "emulator-5554", "-P", "5038", "devices"], command_line="late global port"), "PORT_AMBIGUOUS_OR_MISSING"),
    (lambda value: value.update(listener_evidence_complete=False), "LISTENER_EVIDENCE_MISSING"),
])
def test_wrong_parent_path_hash_port_and_missing_evidence_fail_closed(mutate, needle) -> None:
    client = adb(); mutate(client)
    result = policy().evaluate(snapshot([RUNNER, client]), phase="boot")
    assert not result.passed
    assert any(needle in issue for issue in result.issues), result.issues


def test_pid_reuse_of_preexisting_identity_fails_closed() -> None:
    old = adb(pid=50, created=NOW - 500)
    new = adb(pid=50, created=NOW - 1)
    result = policy(baseline=[old]).evaluate(snapshot([RUNNER, new]), phase="boot")
    assert not result.passed
    assert any("PID_REUSE" in issue for issue in result.issues)


def test_long_lived_and_any_listening_client_fail_closed() -> None:
    long_lived = adb(created=NOW - 60)
    listening = adb(pid=51, listeners=[9999])
    for client, needle in ((long_lived, "LIFETIME_EXCEEDED"), (listening, "OWNS_LISTENER")):
        result = policy().evaluate(snapshot([RUNNER, client]), phase="boot")
        assert not result.passed
        assert any(needle in issue for issue in result.issues), result.issues


def test_completed_authorized_client_does_not_age_into_cleanup_failure(monkeypatch) -> None:
    client = adb()
    value = policy()
    initial = value.evaluate(snapshot([RUNNER, client]), phase="boot")
    assert initial.passed
    monkeypatch.setattr("raven_m.role_binding_timing.infra_m7_adb_authority.time.time", lambda: NOW + 1000)
    completed = value.evaluate(snapshot([RUNNER]), phase="cleanup", recent_records=[client])
    assert completed.passed, completed.issues
    assert completed.roles[identity_key(client)] == "runner_adb_client"


def test_authorized_client_still_active_past_bound_or_later_listening_is_rejected(monkeypatch) -> None:
    client = adb()
    value = policy()
    assert value.evaluate(snapshot([RUNNER, client]), phase="boot").passed
    with monkeypatch.context() as scoped:
        scoped.setattr("raven_m.role_binding_timing.infra_m7_adb_authority.time.time", lambda: NOW + 1000)
        later = value.evaluate(snapshot([RUNNER, client]), phase="boot")
        assert not later.passed

    client = adb()
    value = policy()
    assert value.evaluate(snapshot([RUNNER, client]), phase="boot").passed
    client["listener_ports"] = [7777]
    later = value.evaluate(snapshot([RUNNER, client]), phase="boot")
    assert not later.passed


def test_server_lifecycle_is_separate_and_phase_authorized() -> None:
    start = adb(args=["start-server"])
    kill = adb(pid=51, args=["kill-server"])
    nodaemon = adb(pid=52, args=["nodaemon", "server"])
    assert policy().evaluate(snapshot([RUNNER, start]), phase="launch").passed
    assert not policy().evaluate(snapshot([RUNNER, start]), phase="boot").passed
    assert policy().evaluate(snapshot([RUNNER, kill]), phase="cleanup").passed
    assert not policy().evaluate(snapshot([RUNNER, kill]), phase="framework").passed
    assert not policy().evaluate(snapshot([RUNNER, nodaemon]), phase="launch").passed


@pytest.mark.parametrize("wrapper", ["cmd.exe", "powershell.exe"])
def test_cmd_and_powershell_wrapper_ambiguity_is_rejected(wrapper) -> None:
    wrapped = adb(ppid=80)
    wrapper_record = record(80, wrapper, f"C:/Windows/{wrapper}", "wrapper-hash", [wrapper, "adb", "devices"], 10, NOW - 2)
    result = policy().evaluate(snapshot([RUNNER, wrapper_record, wrapped]), phase="boot")
    assert not result.passed
    assert any("ADB_COMMAND_ROLE" in issue or "PARENT" in issue for issue in result.issues)


def test_netstat_listener_parser_and_record_annotation() -> None:
    raw = b"  TCP    0.0.0.0:5038     0.0.0.0:0     LISTENING       50\r\n  TCP    [::1]:9999       [::]:0        LISTENING       50\r\n"
    assert listener_ports_by_pid(raw) == {50: [5038, 9999]}
    annotated = annotate_listener_evidence([adb()], raw)
    assert annotated[0]["listener_evidence_complete"] is True
    assert annotated[0]["listener_ports"] == [5038, 9999]


@pytest.mark.parametrize("raw", [b"", b"garbage", b"TCP malformed LISTENING pid"])
def test_malformed_netstat_never_invents_listener_authority(raw: bytes) -> None:
    assert listener_ports_by_pid(raw) == {}


def test_full_trigger_snapshot_is_persisted_before_failure_return(tmp_path: Path) -> None:
    bad = adb(args=["nodaemon", "server"], listeners=[5038])
    snapshots = [snapshot([], sequence=1, gate="baseline"), snapshot([RUNNER, bad], sequence=2, gate="trigger")]
    calls = iter(snapshots)

    def provider(gate, sequence, cache):
        value = next(calls)
        return value, b"TCP listener fixture"

    monitor = M7ProcessIdentityMonitor(root=tmp_path / "monitor", config=config(), runner_record=RUNNER, snapshot_provider=provider)
    assert monitor.capture(gate="baseline", phase="launch", mode="baseline")["passed"]
    result = monitor.capture(gate="trigger", phase="launch")
    assert not result["passed"]
    failure = json.loads((tmp_path / "monitor/first_process_identity_failure.json").read_text(encoding="utf-8"))
    assert failure["gate"] == "trigger"
    assert failure["triggering_snapshot"]["listener_evidence_complete"] is True
    assert failure["triggering_snapshot"]["all_tcp_listener_ports_by_pid"] == {"50": [5038]}
    assert (tmp_path / "monitor/snapshots/0002_trigger/process_snapshot.json").is_file()


def test_frozen_m6_invocation_audit_has_complete_generic_coverage() -> None:
    root = Path(__file__).resolve().parents[3]
    audit = json.loads((root / "05_project/artifacts/role_binding_timing/infra_m7_runner_adb_authority_audit/adb_authority_audit.json").read_text(encoding="utf-8"))
    assert audit["observed_summary"] == {
        "all_explicit_single_5038": True,
        "all_locked_binary_path": True,
        "forbidden_server_mode": 0,
        "generic_clients": 4,
        "server_lifecycle": 2,
        "unique_argv": 6,
    }
