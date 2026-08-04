from __future__ import annotations

import json
from pathlib import Path
import time

import pytest

from raven_m.role_binding_timing.infra_m5_process_identity import identity_key
from raven_m.role_binding_timing.infra_m8_full_snapshot_ancestry import (
    M8ProcessIdentityMonitor,
    M8StructuralIdentityPolicy,
    derive_authorization_view,
)


NOW = time.time()


def config() -> dict:
    return {
        "runtime": {"device_serial": "emulator-5554", "emulator_args": ["-avd", "AndroidWorldAvd", "-port", "5554", "-grpc", "8554", "-no-window"]},
        "runner_adb_client": {"max_active_lifetime_seconds": 45.0},
        "process_identity": {
            "continuous_sample_interval_seconds": 0.25, "max_parent_depth": 8,
            "bootstrap_helper_window_seconds": 300, "runtime_helper_window_seconds": 900,
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


def record(pid: int, name: str, exe: str, digest: str | None, argv: list[str], ppid: int, created: float, *, listeners=None) -> dict:
    value = {"pid": pid, "ppid": ppid, "name": name, "exe": exe, "command_line": " ".join(argv),
             "cmdline_items": argv, "create_time": created, "identity_key": f"{pid}@{created:.6f}", "access_error": None}
    if digest is not None:
        value.update(exe_sha256=digest, listener_evidence_complete=True, listener_ports=list(listeners or []))
    return value


RUNNER = record(10, "python.exe", "C:/Python/python.exe", "python-hash", ["python", "frozen.py"], 1, NOW - 100)


def adb(*, pid=50, ppid=10, created=None, digest="adb-hash", args=None, listeners=None) -> dict:
    return record(pid, "adb.exe", "C:/locked/adb.exe", digest,
                  ["C:/locked/adb.exe", "-P", "5038", *(args or ["devices", "-l"])],
                  ppid, created or time.time() - 1, listeners=listeners)


def raw(record_value: dict) -> dict:
    return {key: record_value.get(key) for key in ("pid", "ppid", "name", "exe", "command_line", "cmdline_items", "create_time", "identity_key", "access_error")}


def snapshot(full, candidates, *, complete=True, sequence=1, gate="test") -> dict:
    return {"schema_version": "role_binding_timing.infra_m8.process_snapshot.v1", "sequence": sequence,
            "captured_at": "2026-08-05T00:00:00+00:00", "captured_monotonic": 1.0, "captured_epoch": NOW,
            "gate": gate, "listeners": {"5037": [], "5038": [], "5554": [], "5555": [], "8554": []},
            "all_processes": full, "structural_processes": candidates,
            "observation_universe_complete": complete, "observation_universe_capture_errors": [],
            "raw_netstat_sha256": "0" * 64, "listener_evidence_complete": True,
            "all_tcp_listener_ports_by_pid": {str(item["pid"]): item.get("listener_ports", []) for item in candidates if item.get("listener_ports")}}


def policy() -> M8StructuralIdentityPolicy:
    value = M8StructuralIdentityPolicy(config(), runner_record=RUNNER)
    value.freeze_baseline(snapshot([raw(RUNNER)], []))
    return value


def test_valid_parent_only_in_full_snapshot_authorizes_child() -> None:
    child = adb()
    snap = snapshot([raw(RUNNER), raw(child)], [child])
    result = policy().evaluate(snap, phase="boot")
    assert result.passed, result.issues
    assert result.roles[identity_key(child)] == "runner_adb_client"


def test_unrelated_access_denied_row_does_not_poison_complete_universe() -> None:
    child = adb(); denied = {"pid": 99, "ppid": None, "name": None, "exe": None,
                             "command_line": None, "cmdline_items": None, "create_time": None,
                             "identity_key": None, "access_error": "AccessDenied"}
    result = policy().evaluate(snapshot([raw(RUNNER), raw(child), denied], [child]), phase="boot")
    assert result.passed, result.issues


def test_exited_client_from_history_uses_current_full_runner_identity() -> None:
    child = adb()
    snap = snapshot([raw(RUNNER)], [])
    result = policy().evaluate(snap, phase="launch", recent_records=[child])
    assert result.passed, result.issues
    assert result.roles[identity_key(child)] == "runner_adb_client"


def test_missing_runner_parent_fails_closed() -> None:
    child = adb()
    result = policy().evaluate(snapshot([raw(child)], [child]), phase="boot")
    assert not result.passed
    assert "OBSERVATION_UNIVERSE_RUNNER_MISSING" in result.issues


def test_runner_pid_reuse_and_creation_time_mismatch_fail_closed() -> None:
    child = adb(); reused = dict(raw(RUNNER)); reused["create_time"] = NOW; reused["identity_key"] = f"10@{NOW:.6f}"
    result = policy().evaluate(snapshot([reused, raw(child)], [child]), phase="boot")
    assert not result.passed
    assert "OBSERVATION_UNIVERSE_RUNNER_PID_REUSE" in result.issues


def test_unrelated_parent_does_not_gain_authority_from_full_universe() -> None:
    other = record(11, "other.exe", "C:/other.exe", None, ["other"], 1, NOW - 50)
    child = adb(ppid=11)
    result = policy().evaluate(snapshot([raw(RUNNER), raw(other), raw(child)], [child]), phase="boot")
    assert not result.passed
    assert any("RUNNER_CLIENT_PARENT" in issue for issue in result.issues)


def test_truncated_snapshot_fails_before_authorization() -> None:
    child = adb()
    result = policy().evaluate(snapshot([raw(RUNNER), raw(child)], [child], complete=False), phase="boot")
    assert not result.passed
    assert "OBSERVATION_UNIVERSE_TRUNCATED" in result.issues
    assert identity_key(child) not in result.roles


def test_candidate_must_join_exactly_to_full_universe_identity() -> None:
    child = adb(); different = raw(child); different["create_time"] = NOW - 2; different["identity_key"] = f"50@{NOW - 2:.6f}"
    view, _, _, issues = derive_authorization_view(snapshot([raw(RUNNER), different], [child]), runner_record=RUNNER)
    assert not view["passed"]
    assert "AUTHORIZATION_VIEW_UNIVERSE_MISMATCH:50" in issues


@pytest.mark.parametrize(("field", "value", "needle"), [
    ("exe_sha256", "wrong", "RUNNER_CLIENT_HASH"),
    ("listener_ports", [9999], "RUNNER_CLIENT_OWNS_LISTENER"),
    ("cmdline_items", ["C:/locked/adb.exe", "-P", "5037", "devices"], "RUNNER_CLIENT_PORT_NOT_5038"),
])
def test_child_authorization_still_fails_for_hash_listener_or_port(field, value, needle) -> None:
    child = adb(); child[field] = value
    if field == "cmdline_items": child["command_line"] = " ".join(value)
    result = policy().evaluate(snapshot([raw(RUNNER), raw(child)], [child]), phase="boot")
    assert not result.passed
    assert any(needle in issue for issue in result.issues), result.issues


def test_full_trigger_snapshot_and_derived_authorization_view_are_both_persisted(tmp_path: Path) -> None:
    child = adb(digest="wrong")
    snapshots = [snapshot([raw(RUNNER)], [], gate="baseline"), snapshot([raw(RUNNER), raw(child)], [child], sequence=2, gate="trigger")]
    calls = iter(snapshots)
    def provider(gate, sequence, cache):
        return next(calls), b"netstat fixture"
    monitor = M8ProcessIdentityMonitor(root=tmp_path / "monitor", config=config(), runner_record=RUNNER, snapshot_provider=provider)
    assert monitor.capture(gate="baseline", phase="launch", mode="baseline")["passed"]
    result = monitor.capture(gate="trigger", phase="launch")
    assert not result["passed"]
    base = tmp_path / "monitor/snapshots/0002_trigger"
    assert (base / "process_snapshot.json").is_file()
    assert (base / "derived_authorization_view.json").is_file()
    failure = json.loads((tmp_path / "monitor/first_process_identity_failure.json").read_text(encoding="utf-8"))
    assert failure["triggering_snapshot"]["all_processes"]
    assert failure["derived_authorization_view"]["authorization_candidates"]
    assert failure["derived_authorization_view_record"]["sha256"]


def test_pid_ambiguity_in_full_universe_fails_closed() -> None:
    child = adb(); duplicate = raw(child); duplicate["create_time"] -= 2; duplicate["identity_key"] = f"50@{duplicate['create_time']:.6f}"
    result = policy().evaluate(snapshot([raw(RUNNER), raw(child), duplicate], [child]), phase="boot")
    assert not result.passed
    assert "OBSERVATION_UNIVERSE_PID_AMBIGUITY:50" in result.issues


def test_current_parent_creation_after_child_cannot_be_replaced_by_stale_history() -> None:
    value = policy()
    qemu = record(70, "qemu-system-x86_64-headless.exe", "C:/locked/qemu.exe", "qemu-hash",
                  ["C:/locked/qemu.exe", "-avd", "AndroidWorldAvd", "-port", "5554", "-grpc", "8554", "-no-window"],
                  10, NOW - 20)
    value.core["qemu"] = qemu
    child = record(71, "crashpad_handler.exe", "C:/locked/crashpad.exe", "crash-hash", ["crashpad"], 70, NOW - 10)
    reused_parent = raw(qemu); reused_parent["create_time"] = NOW; reused_parent["identity_key"] = f"70@{NOW:.6f}"
    value.add_history([qemu])
    ok, chain = value._ancestry_to_core(child, {70: reused_parent})
    assert not ok
    assert chain == ["70@CREATION_MISMATCH"]


def test_authorized_client_rechecks_real_full_runner_instead_of_synthetic_map() -> None:
    child = adb(); value = policy()
    first = value.evaluate(snapshot([raw(RUNNER), raw(child)], [child]), phase="boot")
    assert first.passed
    reused = raw(RUNNER); reused["create_time"] = NOW; reused["identity_key"] = f"10@{NOW:.6f}"
    later = value.evaluate(snapshot([reused, raw(child)], [child]), phase="boot")
    assert not later.passed
    assert "OBSERVATION_UNIVERSE_RUNNER_PID_REUSE" in later.issues
