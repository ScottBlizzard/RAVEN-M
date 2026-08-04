from __future__ import annotations

from pathlib import Path
import json

import pytest

from raven_m.role_binding_timing.infra_m2_runtime import (
    clean_baseline_issues,
    forbidden_5037_evidence,
    pre_cleanup_ownership_issues,
    prepare_emulator_environment,
)


def test_prepare_environment_sets_the_single_verified_registration_control(tmp_path: Path) -> None:
    env = prepare_emulator_environment({}, adb_port=5038, avd_home=str(tmp_path / "avd"), sdk_root=str(tmp_path / "sdk"))
    assert env["ANDROID_ADB_SERVER_PORT"] == "5038"
    assert env["ANDROID_AVD_HOME"] == str((tmp_path / "avd").resolve())
    assert env["ANDROID_SDK_ROOT"] == str((tmp_path / "sdk").resolve())
    assert "ADB_SERVER_SOCKET" not in env
    assert "ANDROID_ADB_SERVER_ADDRESS" not in env


@pytest.mark.parametrize("port", [5037, 0, 5039])
def test_prepare_environment_rejects_nonfrozen_port(port: int, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="INFRA_M2_REQUIRES_ADB_5038"):
        prepare_emulator_environment({}, adb_port=port, avd_home=str(tmp_path), sdk_root=str(tmp_path))


@pytest.mark.parametrize("name", ["ADB_SERVER_SOCKET", "ANDROID_ADB_SERVER_ADDRESS"])
def test_prepare_environment_rejects_conflicting_socket_controls(name: str, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="CONFLICTING_ADB_ENVIRONMENT"):
        prepare_emulator_environment({name: "tcp:localhost:5037"}, adb_port=5038, avd_home=str(tmp_path), sdk_root=str(tmp_path))


def test_forbidden_5037_detects_listener_or_command_line() -> None:
    assert forbidden_5037_evidence({"listeners": {"5037": [7]}, "excluded_runtime_processes": {}}) == ["LISTENER:7"]
    evidence = forbidden_5037_evidence({
        "listeners": {"5037": []},
        "excluded_runtime_processes": {"8": {"CommandLine": "adb -L tcp:5037 fork-server server"}},
    })
    assert evidence == ["PROCESS:8:adb -L tcp:5037 fork-server server"]
    assert forbidden_5037_evidence({"listeners": {"5037": []}, "excluded_runtime_processes": {"9": {"CommandLine": None}}}) == []


def test_clean_baseline_requires_all_ports_absent_and_excluded_continuity() -> None:
    clean = {
        "listeners": {str(port): [] for port in (5037, 5038, 5554, 5555, 8554)},
        "adb_pid": None, "launcher_pid": None, "qemu_pid": None,
        "excluded_runtime_pids": [11, 12],
    }
    assert clean_baseline_issues(clean, excluded_pids=[11, 12]) == []
    clean["listeners"]["5037"] = [99]
    clean["excluded_runtime_pids"] = [11]
    assert clean_baseline_issues(clean, excluded_pids=[11, 12]) == ["PORT_RESIDUE", "EXCLUDED_PID_DRIFT"]


def test_precleanup_identity_accepts_exact_owned_scene(tmp_path: Path) -> None:
    adb = tmp_path / "adb.exe"
    config = {
        "runtime": {"adb_binary": "adb.exe"},
        "pre_cleanup_identity": {
            "adb_5037_pid": 7, "adb_5038_pid": 8, "launcher_pid": 9, "qemu_pid": 10,
            "excluded_runtime_pids": [11, 12],
        },
    }
    snapshot = {
        "listeners": {"5037": [7], "5038": [8], "5554": [10], "5555": [10], "8554": [10]},
        "adb_pid": 8, "launcher_pid": 9, "qemu_pid": 10,
        "excluded_runtime_pids": [7, 11, 12],
        "excluded_runtime_processes": {
            "7": {"ExecutablePath": str(adb), "CommandLine": "adb -L tcp:5037 fork-server server"},
            "11": {"ExecutablePath": None, "CommandLine": None},
            "12": {"ExecutablePath": None, "CommandLine": None},
        },
    }
    assert pre_cleanup_ownership_issues(snapshot, config=config, repository_root=tmp_path) == []
    snapshot["listeners"]["5037"] = []
    assert pre_cleanup_ownership_issues(snapshot, config=config, repository_root=tmp_path) == ["ADB_5037_LISTENER"]


def test_frozen_config_has_one_registration_correction_and_new_roots() -> None:
    project = Path(__file__).resolve().parents[2]
    config = json.loads((project / "configs/role_binding_timing/infra_m2_emulator_adb_port_burnin.json").read_text(encoding="utf-8"))
    assert config["runtime"]["registration_environment"] == {"ANDROID_ADB_SERVER_PORT": "5038"}
    assert config["runtime"]["forbidden_inherited_environment"] == ["ADB_SERVER_SOCKET", "ANDROID_ADB_SERVER_ADDRESS"]
    assert config["runtime"]["adb_server_port"] == 5038
    assert config["runtime"]["forbidden_adb_port"] == 5037
    assert config["runtime"]["fallback_to_5037"] is False
    assert config["burn_in"]["cycles"] == 24
    assert config["burn_in"]["minimum_elapsed_seconds"] >= 180
    assert "infra_m2" in config["output_root"] and "infra_m2" in config["runtime_log_root"]
    assert "infra_m1" not in config["output_root"] and "infra_m1" not in config["runtime_log_root"]


def test_runner_limits_5037_commands_to_two_legacy_cleanup_calls() -> None:
    project = Path(__file__).resolve().parents[2]
    source = (project / "scripts/run_role_binding_timing_infra_m2.py").read_text(encoding="utf-8")
    assert source.count("adb_prefix(config, 5037") == 2
    assert 'environment["ANDROID_ADB_SERVER_PORT"]' not in source
    assert "prepare_emulator_environment(" in source
    assert "FORBIDDEN_5037_DURING_LAUNCH" in source
    assert "LEGACY_FROZEN_LOG_DRIFT_ON_SHUTDOWN" in source
    for forbidden in ("com.android.settings", "com.google.android", "org.tasks", "broccoli", "H17", "r79"):
        assert forbidden.casefold() not in source.casefold()
