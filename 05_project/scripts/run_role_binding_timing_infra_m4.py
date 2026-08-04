"""Run the frozen INFRA-M4 chain with crash-surviving terminal accounting."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from raven_m.role_binding_timing.infra_m3_log_lifecycle import (  # noqa: E402
    create_live_root,
    seal_live_logs,
)
from raven_m.role_binding_timing.infra_m4_terminal_accounting import (  # noqa: E402
    PhaseJournal,
    atomic_write_json,
    safe_jsonable,
)


def load_script(name: str, filename: str) -> Any:
    path = PROJECT_ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"SCRIPT_DEPENDENCY_LOAD_FAILURE:{filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M3 = load_script("frozen_infra_m3_runner_for_m4", "run_role_binding_timing_infra_m3.py")
M2 = M3.M2
B210 = M3.B210
M1 = M2.M1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def verify_freeze(config: dict[str, Any], lock: dict[str, Any]) -> None:
    if config["generation_calls_authorized"] != 0 or config["generation_eligible"] is not False:
        raise RuntimeError("GENERATION_BOUNDARY")
    if lock.get("run_id") != config["run_id"]:
        raise RuntimeError("LOCK_RUN_ID")
    for relative, expected in lock["files"].items():
        actual = M1.digest_path(REPOSITORY_ROOT / relative)
        if actual != expected:
            raise RuntimeError(f"FREEZE_HASH:{relative}:{actual}:{expected}")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    tag = subprocess.run(
        ["git", "rev-list", "-n", "1", config["freeze_tag"]], cwd=REPOSITORY_ROOT,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    if head != tag:
        raise RuntimeError(f"FREEZE_TAG:{head}:{tag}")


def journal_start(journal: PhaseJournal, phase: str, details: Any = None) -> None:
    journal.record(phase=phase, event="start", status="RUNNING", details=details)


def journal_pass(journal: PhaseJournal, phase: str, details: Any = None) -> None:
    journal.record(phase=phase, event="end", status="PASS", details=details)


def journal_fail(journal: PhaseJournal, phase: str, edge: str, details: Any = None) -> None:
    if journal.first_edge() is None:
        journal.record(
            phase=phase, event="end", status="FAIL",
            first_broken_edge=edge, details=details,
        )
    else:
        journal.record(phase=phase, event="end", status="SECONDARY_FAIL", details={"edge": edge, "evidence": details})


def clean_baseline(config: dict[str, Any]) -> dict[str, Any]:
    snapshot = M1.runtime_snapshot(config)
    issues = M2.clean_baseline_issues(
        snapshot,
        excluded_pids=config["pre_cleanup_identity"]["excluded_runtime_pids"],
    )
    return {"passed": not issues, "issues": issues, "snapshot": snapshot}


def run_a11y_stages(
    config: dict[str, Any], output_root: Path, journal: PhaseJournal,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run frozen B2.10 acquisition while exposing Settings and grid checkpoints."""
    root = output_root / "post_burn_in_a11y"
    result: dict[str, Any] = {
        "authorized": True,
        "passed": False,
        "first_broken_edge": None,
        "rebind": {"passed": False, "first_broken_edge": "NOT_RUN"},
        "settings": {"required": 3, "completed": 0, "passed": 0, "records": []},
        "grid": {"required": 12, "completed": 0, "passed": 0, "records": []},
    }
    session: dict[str, Any] = {
        "env": None, "raw_adb": None, "sidecar_port": None,
        "adb_pid": None, "emulator_pid": None, "last_package": None,
    }
    managed = B210.ManagedAdb(
        binary=REPOSITORY_ROOT / config["runtime"]["adb_binary"],
        expected_hash=config["runtime"]["adb_binary_sha256"],
        port=config["runtime"]["adb_server_port"],
        serial=config["runtime"]["device_serial"],
    )
    raw_adb = B210.RawAdb(managed)
    session["raw_adb"] = raw_adb
    session["adb_pid"] = managed.owner_pid
    emulator_pid, emulator_record = B210.emulator_identity(config)
    session["emulator_pid"] = emulator_pid
    result["runtime_before"] = {
        "adb_pid": managed.owner_pid,
        "emulator_grpc_pid": emulator_pid,
        "emulator_process": emulator_record,
    }
    if B210.listener_pids(5037):
        raise RuntimeError(f"FORBIDDEN_5037_LISTENER:{B210.listener_pids(5037)}")

    apk_record, apk_raw, _ = raw_adb.run(
        ["shell", "pm", "path", config["accessibility_service"]["package"]],
        root=root / "preflight", name="forwarder_pm_path",
        timeout=config["sampling"]["command_timeout_seconds"],
    )
    apk_path = apk_raw.decode("utf-8", errors="replace").strip().split("package:", 1)[-1]
    hash_record, hash_raw, _ = raw_adb.run(
        ["shell", "sha256sum", apk_path], root=root / "preflight",
        name="forwarder_apk_sha256sum", timeout=config["sampling"]["command_timeout_seconds"],
    )
    apk_hash = hash_raw.decode("ascii", errors="replace").strip().split()[0] if hash_raw.strip() else ""
    if apk_record["returncode"] != 0 or hash_record["returncode"] != 0 or apk_hash != config["accessibility_service"]["installed_apk_sha256"]:
        raise RuntimeError(f"FORWARDER_APK_IDENTITY:{apk_hash}")

    rebind = B210.rebind_forwarder(
        raw_adb=raw_adb, root=root / "lifecycle_rebind", config=config,
        expected_adb_pid=managed.owner_pid,
    )
    result["rebind"] = rebind
    if not rebind["passed"]:
        raise RuntimeError(rebind["first_broken_edge"])
    session["forwarder_pid"] = rebind["forwarder_pid"]
    env = B210.load_explicit_guest_sidecar_env(
        adb_path=str((REPOSITORY_ROOT / config["runtime"]["adb_binary"]).resolve()),
        adb_server_port=config["runtime"]["adb_server_port"],
        console_port=config["runtime"]["console_port"],
        grpc_port=config["runtime"]["emulator_grpc_port"],
    )
    session["env"] = env
    runtime_identity = B210.sidecar_runtime_identity(env)
    session["sidecar_port"] = runtime_identity["sidecar_host_port"]
    result["sidecar_runtime"] = runtime_identity
    if len(runtime_identity["broadcasts"]) != 3 or any(record["status"] != 1 for record in runtime_identity["broadcasts"]):
        raise RuntimeError(f"EXPLICIT_BROADCAST_AUDIT:{runtime_identity['broadcasts']}")
    if B210.listener_pids(session["sidecar_port"]) != [os.getpid()]:
        raise RuntimeError(f"SIDECAR_LISTENER_IDENTITY:{B210.listener_pids(session['sidecar_port'])}:{os.getpid()}")

    journal_start(journal, "settings")
    try:
        settings_launch = B210.launch_and_wait(
            raw_adb=raw_adb, root=root / "settings_qualification" / "launch",
            app=config["settings_scene"], config=config,
        )
        session["last_package"] = config["settings_scene"]["package"]
        result["settings_launch"] = settings_launch
        if not settings_launch["passed"]:
            raise RuntimeError("SETTINGS_FOREGROUND")
        settings_records = []
        for index in range(1, config["sampling"]["settings_observations"] + 1):
            record = B210.capture_observation(
                env=env, raw_adb=raw_adb,
                root=root / "settings_qualification" / f"observation_{index:02d}",
                config=config, app=config["settings_scene"], foreground=settings_launch["witnesses"],
                expected_adb_pid=managed.owner_pid, expected_emulator_grpc_pid=emulator_pid,
                expected_forwarder_pid=rebind["forwarder_pid"],
            )
            settings_records.append(record)
            result["settings"] = {
                "required": 3, "completed": len(settings_records),
                "passed": sum(bool(item["passed"]) for item in settings_records),
                "records": settings_records,
            }
            if not record["passed"]:
                issue = record["issues"][0] if record["issues"] else "UNKNOWN"
                raise RuntimeError(f"SETTINGS_OBSERVATION_{index:02d}:{issue}")
        journal_pass(journal, "settings", {"passed": result["settings"]["passed"], "required": 3})
    except Exception as exc:
        edge = str(exc)
        result["first_broken_edge"] = edge
        journal_fail(journal, "settings", edge, exc)
        return result, session

    journal_start(journal, "grid")
    try:
        grid_records = []
        for round_index in range(1, config["grid"]["rounds"] + 1):
            for app in config["grid"]["apps"]:
                cell_id = f"R{round_index:02d}-{app['dev_app_id']}"
                cell_root = root / "dev_grid" / cell_id
                launched = B210.launch_and_wait(raw_adb=raw_adb, root=cell_root / "launch", app=app, config=config)
                session["last_package"] = app["package"]
                if not launched["passed"]:
                    cell = {"cell_id": cell_id, "passed": False, "app": app, "launch": launched, "issues": ["FOREGROUND"]}
                else:
                    observation = B210.capture_observation(
                        env=env, raw_adb=raw_adb, root=cell_root / "observation",
                        config=config, app=app, foreground=launched["witnesses"],
                        expected_adb_pid=managed.owner_pid, expected_emulator_grpc_pid=emulator_pid,
                        expected_forwarder_pid=rebind["forwarder_pid"],
                    )
                    cell = {
                        "cell_id": cell_id, "passed": observation["passed"], "app": app,
                        "launch": launched, "observation": observation, "issues": observation["issues"],
                    }
                B210.save_json(cell_root / "cell_result.json", cell)
                grid_records.append(cell)
                result["grid"] = {
                    "required": 12, "completed": len(grid_records),
                    "passed": sum(bool(item["passed"]) for item in grid_records),
                    "records": grid_records,
                }
                if not cell["passed"]:
                    issue = cell["issues"][0] if cell["issues"] else "UNKNOWN"
                    raise RuntimeError(f"GRID:{cell_id}:{issue}")
        if len(grid_records) != config["grid"]["required_cells"]:
            raise RuntimeError(f"GRID_CARDINALITY:{len(grid_records)}")
        result["passed"] = all(bool(item["passed"]) for item in grid_records)
        journal_pass(journal, "grid", {"passed": result["grid"]["passed"], "required": 12})
    except Exception as exc:
        edge = str(exc)
        result["first_broken_edge"] = edge
        journal_fail(journal, "grid", edge, exc)
    return result, session


def cleanup_a11y(config: dict[str, Any], output_root: Path, session: dict[str, Any]) -> dict[str, Any]:
    return B210.cleanup(
        env=session.get("env"), raw_adb=session.get("raw_adb"),
        root=output_root / "terminal_cleanup" / "a11y", config=config,
        last_package=session.get("last_package"), sidecar_port=session.get("sidecar_port"),
        expected_adb_pid=session.get("adb_pid"), expected_emulator_grpc_pid=session.get("emulator_pid"),
    )


def terminal_runtime_cleanup(
    config: dict[str, Any], output_root: Path, *, expected: dict[str, int] | None,
) -> dict[str, Any]:
    """Stop only frozen-owned processes and wait through transient shutdown helpers."""
    result: dict[str, Any] = {"steps": {}, "issues": []}
    before = M1.runtime_snapshot(config)
    result["before"] = before
    if M2.forbidden_5037_evidence(before):
        result["issues"].append("FORBIDDEN_5037_BEFORE_TERMINAL_CLEANUP")
    qemu_pid, launcher_pid = before.get("qemu_pid"), before.get("launcher_pid")
    if qemu_pid is not None or launcher_pid is not None:
        launcher_owned = launcher_pid is None or (expected is not None and launcher_pid == expected.get("launcher_pid"))
        qemu_expected = expected.get("qemu_pid") if expected is not None else None
        qemu_process = before.get("qemu_process")
        qemu_path = str((REPOSITORY_ROOT / config["runtime"]["qemu_binary"]).resolve())
        qemu_owned = (
            qemu_pid is None
            or (qemu_expected is not None and qemu_pid == qemu_expected)
            or (
                qemu_expected is None and qemu_process is not None
                and M1.process_matches(
                    qemu_process, expected_path=qemu_path,
                    required_command_parts=[config["runtime"]["avd_name"]],
                )
            )
        )
        if not launcher_owned or not qemu_owned:
            result["issues"].append("EMULATOR_IDENTITY_NOT_OWNED")
        elif before.get("adb_pid") != expected.get("adb_pid") or before["listeners"]["5038"] != [expected.get("adb_pid")]:
            result["issues"].append("ADB_IDENTITY_NOT_OWNED")
        else:
            record, _, _ = M1.run_raw(
                M2.adb_prefix(config, 5038) + ["emu", "kill"],
                root=output_root / "terminal_cleanup", name="emulator_clean_stop",
                timeout=config["maintenance"]["command_timeout_seconds"],
            )
            result["steps"]["emulator_stop"] = record
            if not M2.completed(record):
                result["issues"].append("EMULATOR_CLEAN_STOP_COMMAND")
            else:
                passed, attempts, snapshot = M2.wait_clean_exit(
                    config, {"launcher_pid": launcher_pid, "qemu_pid": qemu_pid},
                )
                result["steps"]["emulator_exit"] = {"passed": passed, "attempts": attempts, "snapshot": snapshot}
                if not passed:
                    result["issues"].append("EMULATOR_DID_NOT_EXIT")

    mid = M1.runtime_snapshot(config)
    adb_pid = mid.get("adb_pid")
    if mid["listeners"]["5038"]:
        if expected is not None and adb_pid != expected.get("adb_pid"):
            result["issues"].append("ADB_5038_IDENTITY_NOT_OWNED")
        else:
            record, _, _ = M1.run_raw(
                M2.adb_prefix(config, 5038, include_serial=False) + ["kill-server"],
                root=output_root / "terminal_cleanup", name="adb_5038_clean_stop",
                timeout=config["maintenance"]["command_timeout_seconds"],
            )
            result["steps"]["adb_stop"] = record
            if not M2.completed(record):
                result["issues"].append("ADB_CLEAN_STOP_COMMAND")

    attempts: list[dict[str, Any]] = []
    final: dict[str, Any] = {}
    for index in range(1, config["maintenance"]["terminal_clean_attempts"] + 1):
        final = M1.runtime_snapshot(config)
        issues = M2.clean_baseline_issues(
            final, excluded_pids=config["pre_cleanup_identity"]["excluded_runtime_pids"],
        )
        attempts.append({"index": index, "issues": issues, "snapshot": final})
        if not issues:
            break
        if index < config["maintenance"]["terminal_clean_attempts"]:
            time.sleep(config["maintenance"]["terminal_clean_interval_seconds"])
    result["steps"]["clean_baseline_wait"] = attempts
    result["after"] = final
    final_issues = M2.clean_baseline_issues(
        final, excluded_pids=config["pre_cleanup_identity"]["excluded_runtime_pids"],
    )
    result["issues"].extend(final_issues)
    result["issues"] = list(dict.fromkeys(result["issues"]))
    result["passed"] = not result["issues"]
    return result


def status_from_edge(edge: str | None, *, a11y_authorized: bool) -> str:
    if edge is None:
        return "PASS_12_OF_12_DEV"
    if edge.startswith("OWNERSHIP") or edge.startswith("CLEAN_BASELINE"):
        return "OWNERSHIP_NOT_QUALIFIED"
    if a11y_authorized and ("SETTINGS" in edge or "GRID" in edge or "FORWARDER" in edge or "SIDECAR" in edge):
        return "A11Y_QUALIFICATION_FAILED"
    if edge.startswith("LOG_SEAL") or edge.startswith("CLEANUP"):
        return "LOG_SEAL_FAILED"
    return "RUNTIME_UNSTABLE"


def invoke_independent_finalizer(config: dict[str, Any], output_root: Path, status: str) -> dict[str, Any]:
    command = [
        str((REPOSITORY_ROOT / config["runtime"]["python"]).resolve()),
        str((REPOSITORY_ROOT / config["terminal_accounting"]["independent_finalizer"]).resolve()),
        "--output-root", str(output_root.resolve()),
        "--schema", str((REPOSITORY_ROOT / config["schema"]).resolve()),
        "--run-id", config["run_id"], "--status", status,
    ]
    completed = subprocess.run(command, cwd=REPOSITORY_ROOT, capture_output=True, timeout=60)
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.decode("utf-8", errors="replace"),
        "stderr": completed.stderr.decode("utf-8", errors="replace"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = json.loads((REPOSITORY_ROOT / args.config).read_text(encoding="utf-8"))
    lock = json.loads((REPOSITORY_ROOT / config["lock"]).read_text(encoding="utf-8"))
    verify_freeze(config, lock)
    output_root = REPOSITORY_ROOT / config["output_root"]
    if output_root.exists():
        raise RuntimeError(f"M4_OUTPUT_ROOT_NOT_FRESH:{output_root}")
    output_root.mkdir(parents=True)
    (output_root / ".gitattributes").write_text("**/*.bin -text\n", encoding="ascii")
    journal = PhaseJournal(output_root / config["terminal_accounting"]["journal_subdir"])
    protected_before = {name: M1.digest_path(REPOSITORY_ROOT / name) for name in config["protected_wip"]}
    if protected_before != config["protected_wip"]:
        raise RuntimeError(f"PROTECTED_WIP_DRIFT:{protected_before}")

    started = utc_now()
    runtime_record: dict[str, Any] = {"before": None, "steps": {}}
    burn = {"passed": False, "first_broken_edge": "NOT_RUN", "required_cycles": 24, "completed_cycles": 0, "passed_cycles": 0, "elapsed_seconds": 0.0, "records": []}
    a11y = {"authorized": False, "passed": False, "first_broken_edge": "NOT_AUTHORIZED", "settings": {"required": 3, "completed": 0, "passed": 0, "records": []}, "grid": {"required": 12, "completed": 0, "passed": 0, "records": []}}
    a11y_session: dict[str, Any] = {}
    live_root: Path | None = None
    expected: dict[str, int] | None = None
    parent_handles_closed = False
    cleanup_result: dict[str, Any] = {"passed": False, "issues": ["NOT_RUN"]}
    log_seal: dict[str, Any] = {"passed": False, "records": [], "temporary_root_removed": False, "issues": ["NOT_RUN"]}
    primary_error: dict[str, Any] | None = None
    current_phase = "launch"

    try:
        journal_start(journal, "launch")
        runtime_record["before"] = M1.runtime_snapshot(config)
        baseline = clean_baseline(config)
        runtime_record["clean_baseline"] = baseline
        if not baseline["passed"]:
            raise RuntimeError(f"CLEAN_BASELINE:{baseline['issues'][0]}")
        for key, expected_hash in (
            ("adb_binary", "adb_binary_sha256"), ("emulator_launcher", "emulator_launcher_sha256"),
            ("qemu_binary", "qemu_binary_sha256"), ("avd_ini", "avd_ini_sha256"),
            ("avd_config", "avd_config_sha256"), ("python", "python_sha256"),
        ):
            actual = M1.digest_path(REPOSITORY_ROOT / config["runtime"][key])
            if actual != config["runtime"][expected_hash]:
                raise RuntimeError(f"RUNTIME_HASH:{key}:{actual}")

        logs = config["log_lifecycle"]
        live_root = create_live_root(
            temp_parent=Path(logs["temp_parent"]), repository_root=REPOSITORY_ROOT,
            forbidden_roots=[Path(item) for item in logs["forbidden_roots"]], prefix=logs["temp_prefix"],
        )
        runtime_record["live_log_root"] = {"path": str(live_root), "outside_repository": True, "immutable_input": False}
        record, _, _ = M1.run_raw(
            M2.adb_prefix(config, 5038, include_serial=False) + ["start-server"],
            root=output_root / "launch", name="adb_5038_start",
            timeout=config["maintenance"]["command_timeout_seconds"],
        )
        runtime_record["steps"]["adb_start"] = record
        if not M2.completed(record):
            raise RuntimeError("ADB_5038_START")
        server = M3.wait_for_server_start(config)
        runtime_record["steps"]["adb_ready"] = server
        if not server["passed"]:
            raise RuntimeError(server["first_broken_edge"])
        server_snapshot = M1.runtime_snapshot(config)
        server_process = server_snapshot.get("adb_process")
        expected_adb_path = str((REPOSITORY_ROOT / config["runtime"]["adb_binary"]).resolve())
        if (
            len(server_snapshot["listeners"]["5038"]) != 1
            or not server_process
            or not M1.process_matches(
                server_process, expected_path=expected_adb_path,
                required_command_parts=["tcp:5038", "fork-server"],
            )
        ):
            raise RuntimeError("ADB_5038_PROCESS_IDENTITY")
        expected = {"adb_pid": server_snapshot["adb_pid"], "launcher_pid": None, "qemu_pid": None}

        runtime = config["runtime"]
        environment = M2.prepare_emulator_environment(
            os.environ, adb_port=runtime["adb_server_port"],
            avd_home=str(REPOSITORY_ROOT / runtime["avd_home"]),
            sdk_root=str(REPOSITORY_ROOT / "06_local_runtime/android/sdk"),
        )
        launcher = (REPOSITORY_ROOT / runtime["emulator_launcher"]).resolve()
        stdout_handle = (live_root / logs["live_log_names"][0]).open("xb")
        stderr_handle = (live_root / logs["live_log_names"][1]).open("xb")
        try:
            launcher_process = subprocess.Popen(
                [str(launcher), *runtime["emulator_args"]], cwd=launcher.parent,
                env=environment, stdout=stdout_handle, stderr=stderr_handle,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        finally:
            stdout_handle.close()
            stderr_handle.close()
            parent_handles_closed = True
        runtime_record["steps"]["emulator_start"] = {
            "command": [str(launcher), *runtime["emulator_args"]],
            "launcher_spawn_pid": launcher_process.pid,
            "environment_evidence": {name: environment.get(name) for name in ("ANDROID_ADB_SERVER_PORT", "ANDROID_AVD_HOME", "ANDROID_SDK_ROOT", "ADB_SERVER_SOCKET", "ANDROID_ADB_SERVER_ADDRESS")},
            "live_log_paths_outside_repository": True,
            "parent_handles_closed": parent_handles_closed,
        }
        expected["launcher_pid"] = launcher_process.pid
        launch = M2.launch_wait(config, launcher_process.pid)
        runtime_record["steps"]["emulator_port_wait"] = launch
        if not launch["passed"]:
            raise RuntimeError(launch["first_broken_edge"])
        after_start = M1.runtime_snapshot(config)
        expected = {key: after_start[key] for key in ("adb_pid", "launcher_pid", "qemu_pid")}
        launch_issues = M2.expected_runtime_issues(after_start, config, expected)
        if launcher_process.pid != after_start["launcher_pid"]:
            launch_issues.append("LAUNCHER_SPAWN_PID_MISMATCH")
        runtime_record["after_start"] = after_start
        runtime_record["start_issues"] = launch_issues
        if launch_issues:
            raise RuntimeError(f"LAUNCH_IDENTITY:{launch_issues[0]}")
        journal_pass(journal, "launch", {"expected": expected})

        current_phase = "boot"
        journal_start(journal, "boot")
        boot = M2.boot_ready(config, output_root / "readiness" / "boot", expected)
        runtime_record["boot"] = boot
        if not boot["passed"]:
            raise RuntimeError(boot["first_broken_edge"])
        journal_pass(journal, "boot")

        current_phase = "framework"
        journal_start(journal, "framework")
        framework = M2.framework_ready(config, output_root / "readiness" / "framework", expected)
        runtime_record["framework"] = framework
        if not framework["passed"]:
            raise RuntimeError(framework["first_broken_edge"])
        journal_pass(journal, "framework")

        current_phase = "burn_in"
        journal_start(journal, "burn_in")
        burn = M2.burn_in(config, output_root / "burn_in", expected)
        if not burn["passed"]:
            raise RuntimeError(burn["first_broken_edge"])
        journal_pass(journal, "burn_in", {"cycles": burn["passed_cycles"], "elapsed_seconds": burn["elapsed_seconds"]})

        current_phase = "settings"
        a11y, a11y_session = run_a11y_stages(config, output_root, journal)
        if not a11y["passed"]:
            raise RuntimeError(a11y["first_broken_edge"] or "A11Y_UNKNOWN")
    except Exception as exc:
        primary_error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        if journal.first_edge() is None:
            journal_fail(journal, current_phase, str(exc), primary_error)

    current_phase = "cleanup"
    journal_start(journal, "cleanup")
    a11y_cleanup: dict[str, Any] = {"passed": True, "not_created": True}
    try:
        if a11y_session:
            a11y_cleanup = cleanup_a11y(config, output_root, a11y_session)
        runtime_cleanup = terminal_runtime_cleanup(config, output_root, expected=expected)
        cleanup_issues = []
        if not a11y_cleanup.get("passed"):
            cleanup_issues.append(f"A11Y_CLEANUP:{a11y_cleanup.get('issues')}")
        if not runtime_cleanup.get("passed"):
            cleanup_issues.append(f"RUNTIME_CLEANUP:{runtime_cleanup.get('issues')}")
        cleanup_result = {
            "passed": not cleanup_issues,
            "runtime_owners_gone": bool(runtime_cleanup.get("passed")),
            "issues": cleanup_issues,
            "a11y": a11y_cleanup,
            "runtime": runtime_cleanup,
        }
        if cleanup_issues:
            raise RuntimeError(cleanup_issues[0])
        journal_pass(journal, "cleanup")
    except Exception as exc:
        cleanup_result = {**cleanup_result, "passed": False, "a11y": a11y_cleanup, "exception": safe_jsonable(exc)}
        journal_fail(journal, "cleanup", f"CLEANUP:{type(exc).__name__}:{exc}", exc)

    current_phase = "seal"
    journal_start(journal, "seal")
    try:
        if live_root is None:
            log_seal = {"passed": True, "records": [], "temporary_root_removed": True, "issues": [], "no_live_logs_created": True}
        else:
            if not cleanup_result.get("runtime_owners_gone"):
                raise RuntimeError("RUNTIME_NOT_CLEAN_FOR_SEAL")
            records = seal_live_logs(
                live_root=live_root,
                result_root=output_root / config["log_lifecycle"]["sealed_result_subdir"],
                names=config["log_lifecycle"]["live_log_names"], repository_root=REPOSITORY_ROOT,
                forbidden_roots=[Path(item) for item in config["log_lifecycle"]["forbidden_roots"]],
                required_temp_parent=Path(config["log_lifecycle"]["temp_parent"]),
                owners_gone=True, parent_handles_closed=parent_handles_closed,
            )
            shutil.rmtree(live_root)
            log_seal = {"passed": True, "records": records, "temporary_root_removed": not live_root.exists(), "issues": []}
        journal_pass(journal, "seal")
    except Exception as exc:
        log_seal = {"passed": False, "records": [], "temporary_root_removed": False, "issues": [f"{type(exc).__name__}:{exc}"], "external_live_root": str(live_root) if live_root else None}
        journal_fail(journal, "seal", f"LOG_SEAL:{type(exc).__name__}:{exc}", exc)

    protected_after = {name: M1.digest_path(REPOSITORY_ROOT / name) for name in config["protected_wip"]}
    if protected_after != protected_before:
        journal_fail(journal, "seal", "PROTECTED_WIP_DRIFT", {"before": protected_before, "after": protected_after})
    first_edge = journal.first_edge()
    status = status_from_edge(first_edge, a11y_authorized=a11y["authorized"])
    rich = {
        "started_at": started,
        "development_contaminated": True,
        "held_out_eligible": False,
        "primary_error": primary_error,
        "runtime": runtime_record,
        "burn_in": burn,
        "a11y": a11y,
        "cleanup": cleanup_result,
        "log_seal": log_seal,
        "protected_wip_before": protected_before,
        "protected_wip_after": protected_after,
        "protected_wip_unchanged": protected_before == protected_after == config["protected_wip"],
        "claim_evidence": {
            "exclusive_5038_registration": expected is not None,
            "burn_in_qualified": bool(burn["passed"]),
            "a11y_tested": bool(a11y["authorized"]),
            "a11y_qualified": bool(a11y["passed"]),
            "v0_3_preparation_authorized": status == "PASS_12_OF_12_DEV",
            "held_out_tested": False,
            "role_binding_hypothesis_tested": False,
        },
    }
    atomic_write_json(output_root / "terminal_input.json", safe_jsonable(rich), replace=False)
    finalizer = invoke_independent_finalizer(config, output_root, status)
    print(json.dumps(finalizer, ensure_ascii=False, indent=2))
    completion_path = output_root / "qualification_completion.json"
    validation_path = output_root / "terminal_validation.json"
    if not completion_path.is_file() or not validation_path.is_file():
        raise RuntimeError(f"TERMINAL_FINALIZER_DID_NOT_COMPLETE:{finalizer}")
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    print(json.dumps({
        "status": completion["status"], "first_broken_edge": completion["first_broken_edge"],
        "last_completed_phase": completion["last_completed_phase"],
        "burn_in": f"{burn['passed_cycles']}/{burn['required_cycles']}",
        "settings": f"{a11y['settings']['passed']}/{a11y['settings']['required']}",
        "grid": f"{a11y['grid']['passed']}/{a11y['grid']['required']}",
        "log_seal": log_seal.get("passed"), "terminal_valid": validation["passed"],
    }, indent=2))
    return 0 if completion["status"] == "PASS_12_OF_12_DEV" and validation["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
