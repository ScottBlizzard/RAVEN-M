"""Run frozen INFRA-M3 maintenance, burn-in, and post-gate DEV a11y qualification."""

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

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from raven_m.role_binding_timing.infra_m3_log_lifecycle import (  # noqa: E402
    create_live_root,
    seal_live_logs,
)


def load_script(name: str, filename: str) -> Any:
    path = PROJECT_ROOT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"SCRIPT_DEPENDENCY_LOAD_FAILURE:{filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M2 = load_script("frozen_infra_m2_runner", "run_role_binding_timing_infra_m2.py")
B210 = load_script("frozen_b210_runner", "qualify_role_binding_timing_b2_10_a11y_lifecycle.py")
M1 = M2.M1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def verify_freeze(config: dict[str, Any], lock: dict[str, Any]) -> None:
    if config["generation_calls_authorized"] != 0 or config["generation_eligible"] is not False:
        raise RuntimeError("GENERATION_BOUNDARY")
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


def residual_ownership_issues(snapshot: dict[str, Any], config: dict[str, Any]) -> list[str]:
    expected = config["pre_cleanup_identity"]
    runtime = config["runtime"]
    issues: list[str] = []
    if snapshot["listeners"]["5037"]:
        issues.append("FORBIDDEN_5037_PRESENT")
    if snapshot["listeners"]["5038"] != [expected["adb_5038_pid"]]:
        issues.append("RESIDUAL_5038_LISTENER")
    if any(snapshot["listeners"][str(port)] for port in (5554, 5555, 8554)):
        issues.append("UNEXPECTED_EMULATOR_LISTENER")
    if snapshot.get("launcher_pid") is not None or snapshot.get("qemu_pid") is not None:
        issues.append("UNEXPECTED_EMULATOR_PROCESS")
    if snapshot.get("excluded_runtime_pids") != expected["excluded_runtime_pids"]:
        issues.append("EXCLUDED_PID_DRIFT")
    process = snapshot.get("adb_process")
    expected_path = str((REPOSITORY_ROOT / runtime["adb_binary"]).resolve())
    if snapshot.get("adb_pid") != expected["adb_5038_pid"] or not process or not M1.process_matches(
        process, expected_path=expected_path, required_command_parts=["tcp:5038", "fork-server"],
    ):
        issues.append("RESIDUAL_5038_PROCESS_IDENTITY")
    for key, expected_hash in (
        ("adb_binary", runtime["adb_binary_sha256"]),
        ("emulator_launcher", runtime["emulator_launcher_sha256"]),
        ("qemu_binary", runtime["qemu_binary_sha256"]),
        ("avd_ini", runtime["avd_ini_sha256"]),
        ("avd_config", runtime["avd_config_sha256"]),
    ):
        if M1.digest_path(REPOSITORY_ROOT / runtime[key]) != expected_hash:
            issues.append(f"HASH:{key}")
    return issues


def wait_for_server_start(config: dict[str, Any]) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for index in range(1, 16):
        snapshot = M1.runtime_snapshot(config)
        forbidden = M2.forbidden_5037_evidence(snapshot)
        passed = len(snapshot["listeners"]["5038"]) == 1 and not forbidden
        attempts.append({"index": index, "passed": passed, "snapshot": snapshot, "forbidden": forbidden})
        if forbidden:
            return {"passed": False, "first_broken_edge": "FORBIDDEN_5037_AFTER_SERVER_START", "attempts": attempts}
        if passed:
            return {"passed": True, "first_broken_edge": None, "attempts": attempts}
        if index < 15:
            time.sleep(1)
    return {"passed": False, "first_broken_edge": "ADB_5038_NOT_READY", "attempts": attempts}


def run_a11y(config: dict[str, Any], output_root: Path) -> dict[str, Any]:
    root = output_root / "post_burn_in_a11y"
    result: dict[str, Any] = {
        "authorized": True,
        "passed": False,
        "first_broken_edge": None,
        "rebind": {"passed": False, "first_broken_edge": "NOT_RUN"},
        "settings": {"required": 3, "completed": 0, "passed": 0, "records": []},
        "grid": {"required": 12, "completed": 0, "passed": 0, "records": []},
        "cleanup": {},
    }
    raw_adb = None
    env = None
    sidecar_port = None
    adb_pid = None
    emulator_pid = None
    forwarder_pid = ""
    last_package = None
    try:
        managed = B210.ManagedAdb(
            binary=REPOSITORY_ROOT / config["runtime"]["adb_binary"],
            expected_hash=config["runtime"]["adb_binary_sha256"],
            port=config["runtime"]["adb_server_port"],
            serial=config["runtime"]["device_serial"],
        )
        raw_adb = B210.RawAdb(managed)
        adb_pid = managed.owner_pid
        emulator_pid, emulator_record = B210.emulator_identity(config)
        result["runtime_before"] = {
            "adb_pid": adb_pid,
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
            expected_adb_pid=adb_pid,
        )
        result["rebind"] = rebind
        if not rebind["passed"]:
            result["first_broken_edge"] = rebind["first_broken_edge"]
            return result
        forwarder_pid = rebind["forwarder_pid"]
        env = B210.load_explicit_guest_sidecar_env(
            adb_path=str((REPOSITORY_ROOT / config["runtime"]["adb_binary"]).resolve()),
            adb_server_port=config["runtime"]["adb_server_port"],
            console_port=config["runtime"]["console_port"],
            grpc_port=config["runtime"]["emulator_grpc_port"],
        )
        runtime_identity = B210.sidecar_runtime_identity(env)
        sidecar_port = runtime_identity["sidecar_host_port"]
        result["sidecar_runtime"] = runtime_identity
        if len(runtime_identity["broadcasts"]) != 3 or any(record["status"] != 1 for record in runtime_identity["broadcasts"]):
            raise RuntimeError(f"EXPLICIT_BROADCAST_AUDIT:{runtime_identity['broadcasts']}")
        if B210.listener_pids(sidecar_port) != [os.getpid()]:
            raise RuntimeError(f"SIDECAR_LISTENER_IDENTITY:{B210.listener_pids(sidecar_port)}:{os.getpid()}")

        settings_launch = B210.launch_and_wait(
            raw_adb=raw_adb, root=root / "settings_qualification" / "launch",
            app=config["settings_scene"], config=config,
        )
        last_package = config["settings_scene"]["package"]
        result["settings_launch"] = settings_launch
        if not settings_launch["passed"]:
            result["first_broken_edge"] = "SETTINGS_FOREGROUND"
            return result
        settings_records = []
        for index in range(1, config["sampling"]["settings_observations"] + 1):
            record = B210.capture_observation(
                env=env, raw_adb=raw_adb,
                root=root / "settings_qualification" / f"observation_{index:02d}",
                config=config, app=config["settings_scene"], foreground=settings_launch["witnesses"],
                expected_adb_pid=adb_pid, expected_emulator_grpc_pid=emulator_pid,
                expected_forwarder_pid=forwarder_pid,
            )
            settings_records.append(record)
            result["settings"] = {
                "required": 3,
                "completed": len(settings_records),
                "passed": sum(item["passed"] for item in settings_records),
                "records": settings_records,
            }
            if not record["passed"]:
                result["first_broken_edge"] = f"SETTINGS_OBSERVATION_{index:02d}:{record['issues'][0] if record['issues'] else 'UNKNOWN'}"
                return result

        grid_records = []
        for round_index in range(1, config["grid"]["rounds"] + 1):
            for app in config["grid"]["apps"]:
                cell_id = f"R{round_index:02d}-{app['dev_app_id']}"
                cell_root = root / "dev_grid" / cell_id
                launched = B210.launch_and_wait(raw_adb=raw_adb, root=cell_root / "launch", app=app, config=config)
                last_package = app["package"]
                if not launched["passed"]:
                    cell = {"cell_id": cell_id, "passed": False, "app": app, "launch": launched, "issues": ["FOREGROUND"]}
                else:
                    observation = B210.capture_observation(
                        env=env, raw_adb=raw_adb, root=cell_root / "observation",
                        config=config, app=app, foreground=launched["witnesses"],
                        expected_adb_pid=adb_pid, expected_emulator_grpc_pid=emulator_pid,
                        expected_forwarder_pid=forwarder_pid,
                    )
                    cell = {
                        "cell_id": cell_id, "passed": observation["passed"], "app": app,
                        "launch": launched, "observation": observation, "issues": observation["issues"],
                    }
                B210.save_json(cell_root / "cell_result.json", cell)
                grid_records.append(cell)
                result["grid"] = {
                    "required": 12,
                    "completed": len(grid_records),
                    "passed": sum(item["passed"] for item in grid_records),
                    "records": grid_records,
                }
                if not cell["passed"]:
                    result["first_broken_edge"] = f"GRID:{cell_id}:{cell['issues'][0] if cell['issues'] else 'UNKNOWN'}"
                    return result
        result["passed"] = len(grid_records) == 12 and all(item["passed"] for item in grid_records)
        if not result["passed"]:
            result["first_broken_edge"] = "GRID_CARDINALITY"
        return result
    except Exception as exc:
        result["first_broken_edge"] = result["first_broken_edge"] or f"EXCEPTION:{type(exc).__name__}:{exc}"
        result["primary_error"] = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        return result
    finally:
        result["cleanup"] = B210.cleanup(
            env=env, raw_adb=raw_adb, root=root / "cleanup", config=config,
            last_package=last_package, sidecar_port=sidecar_port,
            expected_adb_pid=adb_pid, expected_emulator_grpc_pid=emulator_pid,
        )
        if result.get("passed") and not result["cleanup"].get("passed"):
            result["passed"] = False
            result["first_broken_edge"] = result["first_broken_edge"] or f"A11Y_CLEANUP:{result['cleanup']['issues'][0]}"


def terminal_runtime_cleanup(
    config: dict[str, Any], output_root: Path, *, expected: dict[str, int] | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {"steps": {}, "issues": []}
    before = M1.runtime_snapshot(config)
    result["before"] = before
    if M2.forbidden_5037_evidence(before):
        result["issues"].append("FORBIDDEN_5037_BEFORE_TERMINAL_CLEANUP")
    qemu_pid = before.get("qemu_pid")
    launcher_pid = before.get("launcher_pid")
    if qemu_pid is not None or launcher_pid is not None:
        if expected is None or qemu_pid != expected.get("qemu_pid") or launcher_pid != expected.get("launcher_pid"):
            result["issues"].append("EMULATOR_IDENTITY_NOT_OWNED")
        elif len(before["listeners"]["5038"]) != 1 or before.get("adb_pid") != expected.get("adb_pid"):
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
                passed, attempts, snapshot = M2.wait_clean_exit(config, {"launcher_pid": launcher_pid, "qemu_pid": qemu_pid})
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
            elif adb_pid is not None:
                passed, attempts, snapshot = M2.wait_server_gone(config, port=5038, pid=adb_pid)
                result["steps"]["adb_exit"] = {"passed": passed, "attempts": attempts, "snapshot": snapshot}
                if not passed:
                    result["issues"].append("ADB_DID_NOT_EXIT")
    final = M1.runtime_snapshot(config)
    result["after"] = final
    baseline_issues = M2.clean_baseline_issues(final, excluded_pids=config["pre_cleanup_identity"]["excluded_runtime_pids"])
    result["issues"].extend(baseline_issues)
    result["passed"] = not result["issues"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config = json.loads((REPOSITORY_ROOT / args.config).read_text(encoding="utf-8"))
    lock = json.loads((REPOSITORY_ROOT / config["lock"]).read_text(encoding="utf-8"))
    verify_freeze(config, lock)
    output_root = REPOSITORY_ROOT / config["output_root"]
    if output_root.exists():
        raise RuntimeError("M3_OUTPUT_ROOT_NOT_FRESH")
    output_root.mkdir(parents=True)
    (output_root / ".gitattributes").write_text("**/*.bin -text\n", encoding="ascii")
    protected_before = {name: M1.digest_path(REPOSITORY_ROOT / name) for name in config["protected_wip"]}
    if protected_before != config["protected_wip"]:
        raise RuntimeError("PROTECTED_WIP_DRIFT")

    started = utc_now()
    status = "OWNERSHIP_NOT_QUALIFIED"
    first_broken_edge = None
    primary_error = None
    before = M1.runtime_snapshot(config)
    runtime_record: dict[str, Any] = {"before": before, "steps": {}}
    burn = {"passed": False, "first_broken_edge": "NOT_RUN", "required_cycles": 24, "completed_cycles": 0, "passed_cycles": 0, "elapsed_seconds": 0.0, "records": []}
    a11y = {"authorized": False, "passed": False, "first_broken_edge": "NOT_AUTHORIZED", "settings": {"required": 3, "completed": 0, "passed": 0, "records": []}, "grid": {"required": 12, "completed": 0, "passed": 0, "records": []}}
    live_root: Path | None = None
    expected: dict[str, int] | None = None
    parent_handles_closed = False
    runtime_cleanup: dict[str, Any] = {"passed": False, "issues": ["NOT_RUN"]}
    log_seal: dict[str, Any] = {"passed": False, "records": [], "temporary_root_removed": False, "issues": ["NOT_RUN"]}
    try:
        ownership = residual_ownership_issues(before, config)
        runtime_record["ownership_issues"] = ownership
        if ownership:
            first_broken_edge = f"OWNERSHIP:{ownership[0]}"
        else:
            status = "RUNTIME_UNSTABLE"
            residual_pid = config["pre_cleanup_identity"]["adb_5038_pid"]
            record, _, _ = M1.run_raw(
                M2.adb_prefix(config, 5038, include_serial=False) + ["kill-server"],
                root=output_root / "residual_cleanup", name="adb_5038_clean_stop",
                timeout=config["maintenance"]["command_timeout_seconds"],
            )
            runtime_record["steps"]["residual_adb_stop"] = record
            if not M2.completed(record):
                first_broken_edge = "RESIDUAL_ADB_STOP"
            else:
                passed, attempts, snapshot = M2.wait_server_gone(config, port=5038, pid=residual_pid)
                runtime_record["steps"]["residual_adb_exit"] = {"passed": passed, "attempts": attempts, "snapshot": snapshot}
                if not passed:
                    first_broken_edge = "RESIDUAL_ADB_DID_NOT_EXIT"
            if first_broken_edge is None:
                baseline = M1.runtime_snapshot(config)
                issues = M2.clean_baseline_issues(baseline, excluded_pids=config["pre_cleanup_identity"]["excluded_runtime_pids"])
                runtime_record["clean_baseline"] = {"passed": not issues, "issues": issues, "snapshot": baseline}
                if issues:
                    first_broken_edge = f"CLEAN_BASELINE:{issues[0]}"

            if first_broken_edge is None:
                logs = config["log_lifecycle"]
                live_root = create_live_root(
                    temp_parent=Path(logs["temp_parent"]),
                    repository_root=REPOSITORY_ROOT,
                    forbidden_roots=[Path(item) for item in logs["forbidden_roots"]],
                    prefix=logs["temp_prefix"],
                )
                runtime_record["live_log_root"] = {"path": str(live_root), "outside_repository": True, "immutable_input": False}
                record, _, _ = M1.run_raw(
                    M2.adb_prefix(config, 5038, include_serial=False) + ["start-server"],
                    root=output_root / "launch", name="adb_5038_start",
                    timeout=config["maintenance"]["command_timeout_seconds"],
                )
                runtime_record["steps"]["adb_start"] = record
                if not M2.completed(record):
                    first_broken_edge = "ADB_5038_START"
            if first_broken_edge is None:
                server = wait_for_server_start(config)
                runtime_record["steps"]["adb_ready"] = server
                if not server["passed"]:
                    first_broken_edge = server["first_broken_edge"]

            if first_broken_edge is None:
                runtime = config["runtime"]
                environment = M2.prepare_emulator_environment(
                    os.environ,
                    adb_port=runtime["adb_server_port"],
                    avd_home=str(REPOSITORY_ROOT / runtime["avd_home"]),
                    sdk_root=str(REPOSITORY_ROOT / "06_local_runtime/android/sdk"),
                )
                launcher = (REPOSITORY_ROOT / runtime["emulator_launcher"]).resolve()
                stdout_path = live_root / config["log_lifecycle"]["live_log_names"][0]
                stderr_path = live_root / config["log_lifecycle"]["live_log_names"][1]
                stdout_handle = stdout_path.open("xb")
                stderr_handle = stderr_path.open("xb")
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
                    "environment_evidence": {
                        name: environment.get(name)
                        for name in ("ANDROID_ADB_SERVER_PORT", "ANDROID_AVD_HOME", "ANDROID_SDK_ROOT", "ADB_SERVER_SOCKET", "ANDROID_ADB_SERVER_ADDRESS")
                    },
                    "live_log_paths_outside_repository": True,
                    "parent_handles_closed": parent_handles_closed,
                }
                launch = M2.launch_wait(config, launcher_process.pid)
                runtime_record["steps"]["emulator_port_wait"] = launch
                if not launch["passed"]:
                    first_broken_edge = launch["first_broken_edge"]

            if first_broken_edge is None:
                after_start = M1.runtime_snapshot(config)
                expected = {key: after_start[key] for key in ("adb_pid", "launcher_pid", "qemu_pid")}
                issues = M2.expected_runtime_issues(after_start, config, expected)
                if launcher_process.pid != after_start["launcher_pid"]:
                    issues.append("LAUNCHER_SPAWN_PID_MISMATCH")
                if after_start["adb_pid"] == config["pre_cleanup_identity"]["adb_5038_pid"]:
                    issues.append("ADB_PID_NOT_FRESH")
                runtime_record["after_start"] = after_start
                runtime_record["start_issues"] = issues
                if issues:
                    first_broken_edge = f"LAUNCH_IDENTITY:{issues[0]}"
            if first_broken_edge is None:
                boot = M2.boot_ready(config, output_root / "readiness" / "boot", expected)
                runtime_record["boot"] = boot
                if not boot["passed"]:
                    first_broken_edge = boot["first_broken_edge"]
            if first_broken_edge is None:
                framework = M2.framework_ready(config, output_root / "readiness" / "framework", expected)
                runtime_record["framework"] = framework
                if not framework["passed"]:
                    first_broken_edge = framework["first_broken_edge"]
            if first_broken_edge is None:
                burn = M2.burn_in(config, output_root / "burn_in", expected)
                if not burn["passed"]:
                    first_broken_edge = burn["first_broken_edge"]
            if first_broken_edge is None:
                a11y = run_a11y(config, output_root)
                if a11y["passed"]:
                    status = "PASS_12_OF_12_DEV"
                else:
                    status = "A11Y_QUALIFICATION_FAILED"
                    first_broken_edge = a11y["first_broken_edge"]
    except Exception as exc:
        if status == "PASS_12_OF_12_DEV":
            status = "RUNTIME_UNSTABLE"
        first_broken_edge = first_broken_edge or f"EXCEPTION:{type(exc).__name__}:{exc}"
        primary_error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}

    if status != "OWNERSHIP_NOT_QUALIFIED" or live_root is not None:
        runtime_cleanup = terminal_runtime_cleanup(config, output_root, expected=expected)
    if live_root is not None:
        try:
            if not runtime_cleanup.get("passed"):
                raise RuntimeError(f"RUNTIME_NOT_CLEAN_FOR_SEAL:{runtime_cleanup.get('issues')}")
            records = seal_live_logs(
                live_root=live_root,
                result_root=output_root / config["log_lifecycle"]["sealed_result_subdir"],
                names=config["log_lifecycle"]["live_log_names"],
                repository_root=REPOSITORY_ROOT,
                forbidden_roots=[Path(item) for item in config["log_lifecycle"]["forbidden_roots"]],
                required_temp_parent=Path(config["log_lifecycle"]["temp_parent"]),
                owners_gone=True,
                parent_handles_closed=parent_handles_closed,
            )
            shutil.rmtree(live_root)
            log_seal = {"passed": True, "records": records, "temporary_root_removed": not live_root.exists(), "issues": []}
        except Exception as exc:
            log_seal = {
                "passed": False, "records": [], "temporary_root_removed": False,
                "issues": [f"{type(exc).__name__}:{exc}"], "external_live_root": str(live_root),
            }
            if first_broken_edge is None:
                first_broken_edge = f"LOG_SEAL:{type(exc).__name__}:{exc}"
            status = "LOG_SEAL_FAILED"
    elif status != "OWNERSHIP_NOT_QUALIFIED":
        log_seal = {"passed": True, "records": [], "temporary_root_removed": True, "issues": [], "no_live_logs_created": True}

    if status == "PASS_12_OF_12_DEV" and (not runtime_cleanup.get("passed") or not log_seal.get("passed")):
        status = "LOG_SEAL_FAILED"
        first_broken_edge = first_broken_edge or "TERMINAL_LOG_LIFECYCLE"
    protected_after = {name: M1.digest_path(REPOSITORY_ROOT / name) for name in config["protected_wip"]}
    if protected_after != protected_before:
        status = "LOG_SEAL_FAILED"
        first_broken_edge = first_broken_edge or "PROTECTED_WIP_DRIFT"

    completion = {
        "schema_version": "role_binding_timing.infra_m3.completion.v1",
        "status": status,
        "first_broken_edge": first_broken_edge,
        "started_at": started,
        "completed_at": utc_now(),
        "development_contaminated": True,
        "held_out_eligible": False,
        "generation_calls": 0,
        "model_tokens": 0,
        "primary_error": primary_error,
        "runtime": runtime_record,
        "burn_in": burn,
        "a11y": a11y,
        "cleanup": runtime_cleanup,
        "log_seal": log_seal,
        "protected_wip_before": protected_before,
        "protected_wip_after": protected_after,
        "protected_wip_unchanged": protected_before == protected_after == config["protected_wip"],
        "claim_evidence": {
            "exclusive_5038_registration": expected is not None,
            "burn_in_qualified": burn["passed"],
            "a11y_tested": a11y["authorized"],
            "a11y_qualified": a11y["passed"],
            "v0_3_preparation_authorized": status == "PASS_12_OF_12_DEV",
            "held_out_tested": False,
            "role_binding_hypothesis_tested": False,
        },
    }
    schema = json.loads((REPOSITORY_ROOT / config["schema"]).read_text(encoding="utf-8"))
    completion["schema_errors"] = [item.message for item in Draft202012Validator(schema).iter_errors(completion)]
    M1.write_json_atomic(output_root / "qualification_completion.json", completion)
    artifacts = []
    for path in sorted(output_root.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.json":
            artifacts.append({"path": path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": M1.digest_path(path)})
    M1.write_json_atomic(output_root / "artifact_manifest.json", {"schema_version": "role_binding_timing.infra_m3.manifest.v1", "artifacts": artifacts})
    print(json.dumps({
        "status": status,
        "first_broken_edge": first_broken_edge,
        "burn_in": f"{burn['passed_cycles']}/{burn['required_cycles']}",
        "settings": f"{a11y['settings']['passed']}/{a11y['settings']['required']}",
        "grid": f"{a11y['grid']['passed']}/{a11y['grid']['required']}",
        "log_seal": log_seal.get("passed"),
        "schema_errors": completion["schema_errors"],
    }, indent=2))
    return 0 if status == "PASS_12_OF_12_DEV" and not completion["schema_errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
