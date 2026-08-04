from __future__ import annotations

import json
from pathlib import Path
import time

import pytest

from raven_m.role_binding_timing.infra_m5_process_identity import identity_key
from raven_m.role_binding_timing.infra_m9_authorization_views import (
    M9ProcessIdentityMonitor,
    M9StructuralIdentityPolicy,
    derive_process_views,
    validate_attached_views,
)


NOW = time.time()


def config() -> dict:
    return {
        "runtime": {
            "device_serial": "emulator-5554",
            "emulator_args": ["-avd", "AndroidWorldAvd", "-port", "5554", "-grpc", "8554", "-no-window"],
        },
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


def record(
    pid: int, name: str | None, exe: str | None, digest: str | None,
    argv: list[str] | None, ppid: int | None, created: float | None,
    *, listeners: list[int] | None = None, error: str | None = None,
) -> dict:
    value = {
        "pid": pid,
        "ppid": ppid,
        "name": name,
        "exe": exe,
        "command_line": " ".join(argv) if argv else None,
        "cmdline_items": argv,
        "create_time": created,
        "identity_key": f"{pid}@{created:.6f}" if created is not None else None,
        "access_error": error,
    }
    if digest is not None:
        value.update(
            exe_sha256=digest,
            listener_evidence_complete=True,
            listener_ports=list(listeners or []),
        )
    return value


RUNNER = record(10, "python.exe", "C:/Python/python.exe", "python-hash", ["python", "frozen.py"], 1, NOW - 100)


def adb(*, pid: int = 50, ppid: int = 10, created: float | None = None,
        digest: str = "adb-hash", port: str = "5038") -> dict:
    return record(
        pid, "adb.exe", "C:/locked/adb.exe", digest,
        ["C:/locked/adb.exe", "-P", port, "devices", "-l"],
        ppid, created or NOW - 1,
    )


def raw(value: dict) -> dict:
    return {
        key: value.get(key)
        for key in (
            "pid", "ppid", "name", "exe", "command_line", "cmdline_items",
            "create_time", "identity_key", "access_error",
        )
    }


def snapshot(full: list[dict], structural: list[dict], *, ports: dict[int, list[int]] | None = None,
             complete: bool = True, sequence: int = 1, gate: str = "test") -> dict:
    port_map = ports or {}
    listeners = {
        str(port): sorted(pid for pid, owned in port_map.items() if port in owned)
        for port in (5037, 5038, 5554, 5555, 8554)
    }
    enriched = []
    for source in structural:
        value = dict(source)
        value["listener_evidence_complete"] = True
        value["listener_ports"] = list(port_map.get(int(value["pid"]), []))
        enriched.append(value)
    return {
        "schema_version": "role_binding_timing.infra_m8.process_snapshot.v1",
        "sequence": sequence,
        "captured_at": "2026-08-05T00:00:00+00:00",
        "captured_monotonic": 1.0,
        "captured_epoch": NOW,
        "gate": gate,
        "listeners": listeners,
        "all_processes": full,
        "structural_processes": enriched,
        "observation_universe_complete": complete,
        "observation_universe_capture_errors": [],
        "raw_netstat_sha256": "0" * 64,
        "listener_evidence_complete": True,
        "all_tcp_listener_ports_by_pid": {str(pid): owned for pid, owned in port_map.items()},
    }


def policy() -> M9StructuralIdentityPolicy:
    value = M9StructuralIdentityPolicy(config(), runner_record=RUNNER)
    value.freeze_baseline(snapshot([raw(RUNNER)], []))
    return value


def test_views_are_disjoint_and_broad_same_name_binary_is_unrelated() -> None:
    candidate = adb()
    unrelated_crashpad = record(
        70, "crashpad_handler.exe", "C:/vendor/crashpad.exe", "vendor-hash",
        ["C:/vendor/crashpad.exe"], 1, NOW - 50,
    )
    snap = snapshot(
        [raw(RUNNER), raw(candidate), raw(unrelated_crashpad)],
        [candidate, unrelated_crashpad],
    )
    view, _, candidates, issues = derive_process_views(snap, config=config(), runner_record=RUNNER)
    assert not issues
    assert set(candidates) == {50}
    assert {row["pid"] for row in view["unrelated_observed_processes"]} == {70}
    assert view["type_assertions"]["views_disjoint"] is True


def test_access_denied_support_ancestor_is_evidence_only_and_gets_no_role() -> None:
    candidate = adb(ppid=99)
    denied = record(99, None, None, None, None, None, None, error="AccessDenied")
    snap = snapshot([raw(RUNNER), denied, raw(candidate)], [candidate, denied])
    view, _, _, issues = derive_process_views(snap, config=config(), runner_record=RUNNER)
    assert not issues
    assert [row["pid"] for row in view["support_only_ancestry_nodes"]] == [99]
    assert view["support_only_ancestry_nodes"][0]["access_error"] == "AccessDenied"
    result = policy().evaluate(snap, phase="boot")
    assert not result.passed
    assert identity_key(candidate) not in result.roles
    assert all("99@" not in key for key in result.roles)


def test_unrelated_ancestry_nodes_never_enter_candidate_role_loop() -> None:
    unrelated_parent = record(80, "vendor.exe", "C:/vendor.exe", None, ["vendor"], 1, NOW - 60)
    unrelated_child = record(81, "crashpad_handler.exe", "C:/vendor/crashpad.exe", "vendor", ["crashpad"], 80, NOW - 50)
    snap = snapshot([raw(RUNNER), raw(unrelated_parent), raw(unrelated_child)], [unrelated_parent, unrelated_child])
    view, _, candidates, issues = derive_process_views(snap, config=config(), runner_record=RUNNER)
    assert not issues
    assert not candidates
    assert {row["pid"] for row in view["unrelated_observed_processes"]} == {80, 81}
    result = policy().evaluate(snap, phase="boot")
    assert result.passed, result.issues
    assert not result.roles


def test_support_node_owning_controlled_port_is_rejected_if_view_is_corrupted() -> None:
    candidate = adb(ppid=99)
    parent = record(99, "parent.exe", "C:/parent.exe", None, ["parent"], 1, NOW - 20)
    snap = snapshot([raw(RUNNER), raw(parent), raw(candidate)], [candidate, parent], ports={})
    expected, _, _, issues = derive_process_views(snap, config=config(), runner_record=RUNNER)
    assert not issues
    corrupt = json.loads(json.dumps(expected))
    corrupt["support_only_ancestry_nodes"][0]["listener_ports"] = [5038]
    snap["all_tcp_listener_ports_by_pid"] = {"99": [5038]}
    snap["listeners"]["5038"] = [99]
    snap["process_views"] = corrupt
    fresh, _, _, _ = derive_process_views(snap, config=config(), runner_record=RUNNER)
    errors = validate_attached_views(snap, fresh)
    assert "ATTACHED_SUPPORT_OWNS_CONTROLLED_PORT:99" in errors
    assert "ATTACHED_VIEW_MISMATCH:support_only_ancestry_nodes" in errors


def test_candidate_mislabeled_support_is_detected_without_trusting_attached_view() -> None:
    candidate = adb()
    snap = snapshot([raw(RUNNER), raw(candidate)], [candidate])
    expected, _, _, issues = derive_process_views(snap, config=config(), runner_record=RUNNER)
    assert not issues
    corrupt = json.loads(json.dumps(expected))
    moved = corrupt["project_authorization_candidates"].pop()
    corrupt["support_only_ancestry_nodes"].append(moved)
    snap["process_views"] = corrupt
    errors = validate_attached_views(snap, expected)
    assert "ATTACHED_VIEW_MISMATCH:project_authorization_candidates" in errors
    assert "ATTACHED_VIEW_MISMATCH:support_only_ancestry_nodes" in errors


def test_missing_direct_runner_chain_fails_closed() -> None:
    candidate = adb(ppid=99)
    snap = snapshot([raw(RUNNER), raw(candidate)], [candidate])
    view, _, _, issues = derive_process_views(snap, config=config(), runner_record=RUNNER)
    assert not issues
    assert view["candidate_ancestry"][0]["complete_within_bound"] is False
    assert view["candidate_ancestry"][0]["chain"][-1] == {"pid": 99, "status": "MISSING"}
    result = policy().evaluate(snap, phase="boot")
    assert not result.passed
    assert any("RUNNER_CLIENT_PARENT" in issue for issue in result.issues)


def test_runner_pid_reuse_checks_creation_path_and_command() -> None:
    candidate = adb()
    reused = raw(RUNNER)
    reused["create_time"] = NOW
    reused["identity_key"] = f"10@{NOW:.6f}"
    result = policy().evaluate(snapshot([reused, raw(candidate)], [candidate]), phase="boot")
    assert not result.passed
    assert "TRUSTED_RUNNER_ROOT_PID_REUSE" in result.issues

    command_drift = raw(RUNNER)
    command_drift["command_line"] = "python other.py"
    command_drift["cmdline_items"] = ["python", "other.py"]
    result = policy().evaluate(snapshot([command_drift, raw(candidate)], [candidate]), phase="boot")
    assert not result.passed
    assert "TRUSTED_RUNNER_ROOT_COMMAND_DRIFT" in result.issues


def test_support_cannot_be_registered_as_core(tmp_path: Path) -> None:
    candidate = adb(ppid=99)
    support = record(99, "emulator-parent.exe", "C:/parent.exe", None, ["parent"], 10, NOW - 20)
    snap = snapshot([raw(RUNNER), raw(support), raw(candidate)], [support, candidate], gate="baseline")
    def provider(gate, sequence, cache):
        return snap, b"netstat fixture"
    monitor = M9ProcessIdentityMonitor(
        root=tmp_path / "monitor", config=config(), runner_record=RUNNER, snapshot_provider=provider,
    )
    result = monitor.capture(gate="baseline", phase="launch", mode="baseline")
    assert result["passed"]
    path = tmp_path / "monitor/snapshots/0001_baseline/process_snapshot.json"
    with pytest.raises(RuntimeError, match="CORE_PID_IS_SUPPORT_ONLY"):
        monitor.register_core_from_snapshot(role="emulator_launcher", snapshot_path=path, pid=99)


def test_full_trigger_and_all_derived_views_are_persisted_exactly(tmp_path: Path) -> None:
    candidate = adb(digest="wrong")
    baseline = snapshot([raw(RUNNER)], [], gate="baseline")
    trigger = snapshot([raw(RUNNER), raw(candidate)], [candidate], sequence=2, gate="trigger")
    calls = iter([baseline, trigger])
    def provider(gate, sequence, cache):
        return next(calls), b"netstat fixture"
    monitor = M9ProcessIdentityMonitor(
        root=tmp_path / "monitor", config=config(), runner_record=RUNNER, snapshot_provider=provider,
    )
    assert monitor.capture(gate="baseline", phase="launch", mode="baseline")["passed"]
    result = monitor.capture(gate="trigger", phase="launch")
    assert not result["passed"]
    root = tmp_path / "monitor/snapshots/0002_trigger"
    persisted_snapshot = json.loads((root / "process_snapshot.json").read_text(encoding="utf-8"))
    persisted_views = json.loads((root / "derived_process_views.json").read_text(encoding="utf-8"))
    failure = json.loads((tmp_path / "monitor/first_process_identity_failure.json").read_text(encoding="utf-8"))
    assert persisted_snapshot["process_views"] == persisted_views
    assert failure["triggering_snapshot"] == persisted_snapshot
    assert failure["derived_process_views"] == persisted_views
    for name in ("trusted_runner_root", "project_authorization_candidates", "support_only_ancestry_nodes", "unrelated_observed_processes"):
        assert name in persisted_views
    assert failure["derived_process_views_record"]["sha256"]


def test_corrupt_attached_view_fails_monitor_and_preserves_full_trigger(tmp_path: Path) -> None:
    candidate = adb()
    snap = snapshot([raw(RUNNER), raw(candidate)], [candidate], gate="corrupt")
    expected, _, _, _ = derive_process_views(snap, config=config(), runner_record=RUNNER)
    corrupt = json.loads(json.dumps(expected))
    corrupt["unrelated_observed_processes"].append(corrupt["project_authorization_candidates"].pop())
    snap["process_views"] = corrupt
    def provider(gate, sequence, cache):
        return snap, b"netstat fixture"
    monitor = M9ProcessIdentityMonitor(
        root=tmp_path / "monitor", config=config(), runner_record=RUNNER, snapshot_provider=provider,
    )
    result = monitor.capture(gate="corrupt", phase="launch", mode="baseline")
    assert not result["passed"]
    assert any(item.startswith("ATTACHED_VIEW_MISMATCH") for item in result["issues"])
    failure = json.loads((tmp_path / "monitor/first_process_identity_failure.json").read_text(encoding="utf-8"))
    assert failure["triggering_snapshot"]["process_view_input_validation_issues"]
    assert failure["triggering_snapshot"]["all_processes"]
