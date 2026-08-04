"""Run the frozen B2.10 DEV-only accessibility lifecycle qualification."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from typing import Any

from jsonschema import Draft202012Validator
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from qualify_role_binding_timing_b2_5_infrastructure import (  # noqa: E402
    ManagedAdb,
    listener_pids,
    process_record,
    sha256_path,
    write_json_atomic,
)
from diagnose_role_binding_timing_b2_9_androidenv_sidecar import (  # noqa: E402
    RawAdb,
    collect_foreground_sample,
    reset_scene,
)
from raven_m.role_binding_timing.androidenv_sidecar_runtime_v0_2_10 import (  # noqa: E402
    FORWARDER_COMPONENT,
    FORWARDER_RECEIVER,
    load_explicit_guest_sidecar_env,
    lifecycle_identity_issues,
    parse_accessibility_service_state,
    sidecar_runtime_identity,
)
from raven_m.role_binding_timing.androidenv_sidecar_v0_2_8 import (  # noqa: E402
    canonical_json_bytes,
    derive_stable_oracle_candidates,
    deterministic_forest_bytes,
    protobuf_field_manifest,
    qualify_observation,
    serialize_ui_elements,
    validate_pixels,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_bytes(path: Path, value: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    return {
        "path": path.relative_to(REPOSITORY_ROOT).as_posix(),
        "bytes": len(value),
        "sha256": sha256(value).hexdigest(),
    }


def save_json(path: Path, value: Any) -> dict[str, Any]:
    return save_bytes(path, canonical_json_bytes(value))


def verify_hashes(records: dict[str, str]) -> list[str]:
    issues = []
    for relative, expected in records.items():
        path = REPOSITORY_ROOT / relative
        actual = sha256_path(path) if path.exists() else None
        if actual != expected:
            issues.append(f"HASH_MISMATCH:{relative}:{actual}:{expected}")
    return issues


def verify_freeze(config: dict[str, Any], lock: dict[str, Any]) -> None:
    if config["generation_calls_authorized"] != 0 or config["generation_eligible"] is not False:
        raise RuntimeError("GENERATION_BOUNDARY_INVALID")
    issues = verify_hashes(lock["files"])
    if issues:
        raise RuntimeError(f"FREEZE_HASH_DRIFT:{issues}")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    tag = subprocess.run(
        ["git", "rev-list", "-n", "1", config["freeze_tag"]], cwd=REPOSITORY_ROOT,
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    if tag != head:
        raise RuntimeError(f"FREEZE_TAG_DRIFT:{tag}:{head}")
    if lock["predecessor_audit_commit"] != config["audit_commit"]:
        raise RuntimeError("AUDIT_COMMIT_LOCK_DRIFT")


def emulator_identity(config: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    runtime = config["runtime"]
    pids = listener_pids(runtime["emulator_grpc_port"])
    if len(pids) != 1:
        raise RuntimeError(f"EMULATOR_GRPC_LISTENER:{pids}")
    record = process_record(pids[0])
    actual_path = Path(record["executable_path"]).resolve()
    expected_path = (REPOSITORY_ROOT / runtime["emulator_binary"]).resolve()
    actual_hash = sha256_path(actual_path)
    if actual_path != expected_path or actual_hash != runtime["emulator_binary_sha256"]:
        raise RuntimeError(f"EMULATOR_PROCESS_IDENTITY:{actual_path}:{actual_hash}")
    record["binary_sha256"] = actual_hash
    return pids[0], record


def rebind_forwarder(
    *, raw_adb: RawAdb, root: Path, config: dict[str, Any], expected_adb_pid: int,
) -> dict[str, Any]:
    service = config["accessibility_service"]
    timeout = config["sampling"]["command_timeout_seconds"]
    records: dict[str, Any] = {}
    commands = (
        ("wake", ["shell", "input", "keyevent", "224"]),
        ("dismiss_keyguard", ["shell", "wm", "dismiss-keyguard"]),
        ("disable_accessibility", ["shell", "settings", "put", "secure", "accessibility_enabled", "0"]),
        ("clear_enabled_service", ["shell", "settings", "delete", "secure", "enabled_accessibility_services"]),
        ("force_stop_forwarder", ["shell", "am", "force-stop", service["package"]]),
        ("restore_enabled_service", ["shell", "settings", "put", "secure", "enabled_accessibility_services", service["component"]]),
        ("enable_accessibility", ["shell", "settings", "put", "secure", "accessibility_enabled", "1"]),
    )
    for name, command in commands:
        record, _, _ = raw_adb.run(command, root=root / "commands", name=name, timeout=timeout)
        records[name] = record
        if record["returncode"] != 0 or record["timed_out"] or not record["adb_identity_continuous"]:
            return {"passed": False, "first_broken_edge": f"REBIND_COMMAND:{name}", "records": records, "attempts": []}
        if listener_pids(5037) or raw_adb.managed.current_pid() != expected_adb_pid:
            return {"passed": False, "first_broken_edge": f"REBIND_IDENTITY:{name}", "records": records, "attempts": []}

    attempts = []
    for index in range(1, service["rebind_attempts"] + 1):
        attempt_root = root / "readiness" / f"attempt_{index:02d}"
        dump_record, dump_raw, _ = raw_adb.run(
            ["shell", "dumpsys", "accessibility"], root=attempt_root,
            name="accessibility_dump", timeout=timeout,
        )
        pid_record, pid_raw, _ = raw_adb.run(
            ["shell", "pidof", service["package"]], root=attempt_root,
            name="forwarder_pid", timeout=timeout,
        )
        state = parse_accessibility_service_state(dump_raw.decode("utf-8", errors="replace"))
        forwarder_pid = pid_raw.decode("ascii", errors="replace").strip()
        passed = (
            state["qualified_bound"] and bool(forwarder_pid)
            and dump_record["returncode"] == 0 and pid_record["returncode"] == 0
            and dump_record["adb_identity_continuous"] and pid_record["adb_identity_continuous"]
            and not listener_pids(5037) and raw_adb.managed.current_pid() == expected_adb_pid
        )
        attempt = {
            "index": index, "passed": passed, "service_state": state,
            "forwarder_pid": forwarder_pid,
            "records": {"dump": dump_record, "pid": pid_record},
        }
        write_json_atomic(attempt_root / "attempt.json", attempt)
        attempts.append(attempt)
        if passed:
            return {"passed": True, "first_broken_edge": None, "forwarder_pid": forwarder_pid, "records": records, "attempts": attempts}
        if index < service["rebind_attempts"]:
            time.sleep(service["rebind_interval_seconds"])
    return {"passed": False, "first_broken_edge": "FORWARDER_NOT_BOUND", "records": records, "attempts": attempts}


def launch_and_wait(
    *, raw_adb: RawAdb, root: Path, app: dict[str, Any], config: dict[str, Any],
) -> dict[str, Any]:
    timeout = config["sampling"]["command_timeout_seconds"]
    reset = reset_scene(raw_adb, root / "reset", app["package"], timeout)
    launch, _, _ = raw_adb.run(
        ["shell", "am", "start", "-n", app["component"]], root=root,
        name="launch_nonwait", timeout=timeout,
    )
    samples = []
    consecutive = 0
    for index in range(1, config["sampling"]["foreground_attempts"] + 1):
        sample = collect_foreground_sample(
            raw_adb=raw_adb, root=root / "foreground", index=index,
            expected_package=app["package"], timeout=timeout,
        )
        samples.append(sample)
        consecutive = consecutive + 1 if sample["passed"] else 0
        if consecutive >= config["sampling"]["foreground_required_consecutive"]:
            time.sleep(config["sampling"]["post_foreground_settle_seconds"])
            return {"passed": True, "reset": reset, "launch": launch, "samples": samples, "witnesses": sample["witnesses"]}
        if index < config["sampling"]["foreground_attempts"]:
            time.sleep(config["sampling"]["foreground_interval_seconds"])
    return {"passed": False, "reset": reset, "launch": launch, "samples": samples, "witnesses": samples[-1]["witnesses"] if samples else {}}


def lifecycle_identity(
    *, env: Any, raw_adb: RawAdb, root: Path, config: dict[str, Any],
    expected_adb_pid: int, expected_emulator_grpc_pid: int,
) -> dict[str, Any]:
    runtime_sidecar = sidecar_runtime_identity(env)
    timeout = config["sampling"]["command_timeout_seconds"]
    dump_record, dump_raw, _ = raw_adb.run(
        ["shell", "dumpsys", "accessibility"], root=root,
        name="accessibility_dump", timeout=timeout,
    )
    pid_record, pid_raw, _ = raw_adb.run(
        ["shell", "pidof", config["accessibility_service"]["package"]], root=root,
        name="forwarder_pid", timeout=timeout,
    )
    activity_record, activity_raw, _ = raw_adb.run(
        ["shell", "dumpsys", "activity", "activities"], root=root,
        name="activity_activities", timeout=timeout,
    )
    window_record, window_raw, _ = raw_adb.run(
        ["shell", "dumpsys", "window", "displays"], root=root,
        name="window_displays", timeout=timeout,
    )
    from raven_m.role_binding_timing.infrastructure_v0_2_5 import parse_foreground_witnesses
    witnesses = parse_foreground_witnesses(
        activity_raw.decode("utf-8", errors="replace"),
        window_raw.decode("utf-8", errors="replace"),
    )
    host_pids = listener_pids(runtime_sidecar["sidecar_host_port"])
    state = parse_accessibility_service_state(dump_raw.decode("utf-8", errors="replace"))
    records = {"dump": dump_record, "pid": pid_record, "activity": activity_record, "window": window_record}
    return {
        "qualified": (
            all(record["returncode"] == 0 and not record["timed_out"] and record["adb_identity_continuous"] for record in records.values())
            and raw_adb.managed.current_pid() == expected_adb_pid
            and listener_pids(config["runtime"]["emulator_grpc_port"]) == [expected_emulator_grpc_pid]
            and not listener_pids(5037) and state["qualified_bound"]
            and host_pids == [os.getpid()]
        ),
        "adb_pid": raw_adb.managed.current_pid(),
        "emulator_grpc_pid": listener_pids(config["runtime"]["emulator_grpc_port"])[0] if len(listener_pids(config["runtime"]["emulator_grpc_port"])) == 1 else None,
        "forwarder_pid": pid_raw.decode("ascii", errors="replace").strip(),
        "fallback_5037_listener_pids": listener_pids(5037),
        "sidecar_host_listener_pids": host_pids,
        "sidecar_host_listener_owned": host_pids == [os.getpid()],
        "service_state": state,
        "a11y_component": FORWARDER_COMPONENT,
        "a11y_apk_sha256": config["accessibility_service"]["installed_apk_sha256"],
        "activity_packages": witnesses["activity_packages"],
        "window_packages": witnesses["window_packages"],
        "records": records,
        **runtime_sidecar,
    }


def capture_observation(
    *, env: Any, raw_adb: RawAdb, root: Path, config: dict[str, Any], app: dict[str, Any],
    foreground: dict[str, Any], expected_adb_pid: int, expected_emulator_grpc_pid: int,
    expected_forwarder_pid: str,
) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    before = lifecycle_identity(
        env=env, raw_adb=raw_adb, root=root / "identity_before", config=config,
        expected_adb_pid=expected_adb_pid, expected_emulator_grpc_pid=expected_emulator_grpc_pid,
    )
    issues: list[str] = []
    state = None
    error = None
    try:
        state = env.get_state(wait_to_stabilize=False)
    except Exception as exc:  # frozen live boundary records exact failure
        error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        issues.append(f"GET_STATE:{type(exc).__name__}:{exc}")
    after = lifecycle_identity(
        env=env, raw_adb=raw_adb, root=root / "identity_after", config=config,
        expected_adb_pid=expected_adb_pid, expected_emulator_grpc_pid=expected_emulator_grpc_pid,
    )
    issues.extend(lifecycle_identity_issues(
        before=before, after=after, expected_adb_pid=expected_adb_pid,
        expected_emulator_grpc_pid=expected_emulator_grpc_pid,
        expected_forwarder_pid=expected_forwarder_pid,
    ))
    artifacts: dict[str, Any] = {}
    metrics: dict[str, Any] = {"element_count": 0, "oracle_candidate_count": 0}
    if state is not None:
        try:
            pixels = state.pixels
            elements = list(state.ui_elements)
            forest = state.forest
            pixel_validation = validate_pixels(pixels, tuple(config["sampling"]["expected_pixel_shape"]))
            forest_bytes = deterministic_forest_bytes(forest)
            element_bytes, element_manifest = serialize_ui_elements(elements)
            forest_manifest = protobuf_field_manifest(forest)
            candidates = derive_stable_oracle_candidates(
                elements, expected_package=app["package"],
                screen_width=config["sampling"]["screen_width"],
                screen_height=config["sampling"]["screen_height"],
            )
            png = io.BytesIO()
            Image.fromarray(pixels).save(png, format="PNG")
            artifacts = {
                "screenshot_png": save_bytes(root / "same_observation.png", png.getvalue()),
                "forest_pb": save_bytes(root / "accessibility_forest.pb", forest_bytes),
                "elements_json": save_bytes(root / "accessibility_elements.json", element_bytes),
                "element_manifest": save_json(root / "element_manifest.json", element_manifest),
                "forest_manifest": save_json(root / "forest_manifest.json", forest_manifest),
                "oracle_candidates": save_json(root / "oracle_candidates.json", candidates),
            }
            env_packages = sorted({getattr(item, "package_name", None) for item in elements if getattr(item, "package_name", None)})
            before["qualified"] = before["qualified"] and before["transport"]["mode"] == "emulator_guest_plaintext_insecure_server"
            after["qualified"] = after["qualified"] and after["transport"]["mode"] == "emulator_guest_plaintext_insecure_server"
            issues.extend(qualify_observation(
                elements=elements,
                expected_package=app["package"],
                foreground_packages={
                    "activity_packages": after["activity_packages"],
                    "window_packages": after["window_packages"],
                    "env_packages": env_packages,
                },
                oracle_candidates=candidates,
                pixel_validation=pixel_validation,
                forest_bytes=forest_bytes,
                identity_before=before,
                identity_after=after,
            ))
            metrics = {
                "element_count": len(elements),
                "element_packages": env_packages,
                "oracle_candidate_count": len(candidates),
                "pixel": pixel_validation,
                "forest_bytes": len(forest_bytes),
                "elements_bytes": len(element_bytes),
            }
        except Exception as exc:
            issues.append(f"SERIALIZATION:{type(exc).__name__}:{exc}")
            error = error or {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
    record = {
        "passed": not issues,
        "app": app,
        "foreground": foreground,
        "identity_before": before,
        "identity_after": after,
        "metrics": metrics,
        "issues": issues,
        "error": error,
        "artifacts": artifacts,
        "generation_calls": 0,
    }
    save_json(root / "observation_record.json", record)
    return record


def cleanup(
    *, env: Any | None, raw_adb: RawAdb | None, root: Path, config: dict[str, Any],
    last_package: str | None, sidecar_port: int | None, expected_adb_pid: int | None,
    expected_emulator_grpc_pid: int | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {"env_close": "not_created", "records": {}, "issues": []}
    if env is not None:
        try:
            env.close()
            result["env_close"] = "closed"
        except Exception as exc:
            result["env_close"] = "failed"
            result["issues"].append(f"ENV_CLOSE:{type(exc).__name__}:{exc}")
    if raw_adb is not None:
        timeout = config["sampling"]["command_timeout_seconds"]
        commands = [
            ("disable_grpc", ["shell", "am", "broadcast", "-a", "accessibility_forwarder.intent.action.DISABLE_GRPC", "-n", FORWARDER_RECEIVER]),
            ("disable_tree", ["shell", "am", "broadcast", "-a", "accessibility_forwarder.intent.action.DISABLE_ACCESSIBILITY_TREE_LOGS", "-n", FORWARDER_RECEIVER]),
            ("press_home", ["shell", "input", "keyevent", "3"]),
        ]
        if last_package:
            commands.append(("force_stop_last_app", ["shell", "am", "force-stop", last_package]))
        for name, command in commands:
            record, _, _ = raw_adb.run(command, root=root, name=name, timeout=timeout)
            result["records"][name] = record
            if record["returncode"] != 0 or record["timed_out"] or not record["adb_identity_continuous"]:
                result["issues"].append(f"CLEANUP_COMMAND:{name}")
    result["adb_5037_pids"] = listener_pids(5037)
    result["adb_5038_pids"] = listener_pids(config["runtime"]["adb_server_port"])
    result["emulator_grpc_pids"] = listener_pids(config["runtime"]["emulator_grpc_port"])
    result["sidecar_pids"] = listener_pids(sidecar_port) if sidecar_port else []
    if result["adb_5037_pids"]:
        result["issues"].append("CLEANUP_FORBIDDEN_5037")
    if expected_adb_pid is not None and result["adb_5038_pids"] != [expected_adb_pid]:
        result["issues"].append("CLEANUP_ADB_IDENTITY")
    if expected_emulator_grpc_pid is not None and result["emulator_grpc_pids"] != [expected_emulator_grpc_pid]:
        result["issues"].append("CLEANUP_EMULATOR_IDENTITY")
    if result["sidecar_pids"]:
        result["issues"].append("CLEANUP_SIDECAR_LISTENER_RESIDUE")
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
        raise RuntimeError(f"OUTPUT_ROOT_ALREADY_EXISTS:{output_root}")
    output_root.mkdir(parents=True)
    (output_root / ".gitattributes").write_text("**/*.bin -text\n", encoding="ascii")

    protected_before = {name: sha256_path(REPOSITORY_ROOT / name) for name in config["protected_wip"]}
    if protected_before != config["protected_wip"]:
        raise RuntimeError(f"PROTECTED_WIP_DRIFT:{protected_before}")
    started = utc_now()
    status = "FAIL_LIFECYCLE_REBIND"
    first_broken_edge: str | None = None
    raw_adb: RawAdb | None = None
    env = None
    sidecar_port: int | None = None
    adb_pid: int | None = None
    emulator_pid: int | None = None
    emulator_record: dict[str, Any] | None = None
    forwarder_pid = ""
    last_package: str | None = None
    rebind: dict[str, Any] = {"passed": False, "first_broken_edge": "NOT_RUN"}
    settings_records: list[dict[str, Any]] = []
    grid_records: list[dict[str, Any]] = []
    primary_error = None
    cleanup_result: dict[str, Any] = {}
    try:
        managed = ManagedAdb(
            binary=REPOSITORY_ROOT / config["runtime"]["adb_binary"],
            expected_hash=config["runtime"]["adb_binary_sha256"],
            port=config["runtime"]["adb_server_port"],
            serial=config["runtime"]["device_serial"],
        )
        raw_adb = RawAdb(managed)
        adb_pid = managed.owner_pid
        emulator_pid, emulator_record = emulator_identity(config)
        if listener_pids(5037):
            raise RuntimeError(f"FORBIDDEN_5037_LISTENER:{listener_pids(5037)}")

        apk_record, apk_raw, _ = raw_adb.run(
            ["shell", "pm", "path", config["accessibility_service"]["package"]],
            root=output_root / "preflight", name="forwarder_pm_path",
            timeout=config["sampling"]["command_timeout_seconds"],
        )
        apk_path = apk_raw.decode("utf-8", errors="replace").strip().split("package:", 1)[-1]
        hash_record, hash_raw, _ = raw_adb.run(
            ["shell", "sha256sum", apk_path], root=output_root / "preflight",
            name="forwarder_apk_sha256sum", timeout=config["sampling"]["command_timeout_seconds"],
        )
        apk_hash = hash_raw.decode("ascii", errors="replace").strip().split()[0] if hash_raw.strip() else ""
        if apk_record["returncode"] != 0 or hash_record["returncode"] != 0 or apk_hash != config["accessibility_service"]["installed_apk_sha256"]:
            raise RuntimeError(f"FORWARDER_APK_IDENTITY:{apk_hash}")

        rebind = rebind_forwarder(
            raw_adb=raw_adb, root=output_root / "lifecycle_rebind", config=config,
            expected_adb_pid=adb_pid,
        )
        if not rebind["passed"]:
            first_broken_edge = rebind["first_broken_edge"]
        else:
            forwarder_pid = rebind["forwarder_pid"]
            env = load_explicit_guest_sidecar_env(
                adb_path=str((REPOSITORY_ROOT / config["runtime"]["adb_binary"]).resolve()),
                adb_server_port=config["runtime"]["adb_server_port"],
                console_port=config["runtime"]["console_port"],
                grpc_port=config["runtime"]["emulator_grpc_port"],
            )
            runtime_identity = sidecar_runtime_identity(env)
            sidecar_port = runtime_identity["sidecar_host_port"]
            if len(runtime_identity["broadcasts"]) != 3 or any(record["status"] != 1 for record in runtime_identity["broadcasts"]):
                raise RuntimeError(f"EXPLICIT_BROADCAST_AUDIT:{runtime_identity['broadcasts']}")
            if listener_pids(sidecar_port) != [os.getpid()]:
                raise RuntimeError(f"SIDECAR_LISTENER_IDENTITY:{listener_pids(sidecar_port)}:{os.getpid()}")

            settings_launch = launch_and_wait(
                raw_adb=raw_adb, root=output_root / "settings_qualification" / "launch",
                app=config["settings_scene"], config=config,
            )
            last_package = config["settings_scene"]["package"]
            if not settings_launch["passed"]:
                status = "FAIL_SETTINGS_QUALIFICATION"
                first_broken_edge = "SETTINGS_FOREGROUND"
            else:
                status = "FAIL_SETTINGS_QUALIFICATION"
                for index in range(1, config["sampling"]["settings_observations"] + 1):
                    record = capture_observation(
                        env=env, raw_adb=raw_adb,
                        root=output_root / "settings_qualification" / f"observation_{index:02d}",
                        config=config, app=config["settings_scene"], foreground=settings_launch["witnesses"],
                        expected_adb_pid=adb_pid, expected_emulator_grpc_pid=emulator_pid,
                        expected_forwarder_pid=forwarder_pid,
                    )
                    settings_records.append(record)
                    if not record["passed"]:
                        first_broken_edge = f"SETTINGS_OBSERVATION_{index:02d}:{record['issues'][0] if record['issues'] else 'UNKNOWN'}"
                        break
                if len(settings_records) == 3 and all(record["passed"] for record in settings_records):
                    status = "FAIL_DEV_GRID"
                    for round_index in range(1, config["grid"]["rounds"] + 1):
                        for app in config["grid"]["apps"]:
                            cell_id = f"R{round_index:02d}-{app['dev_app_id']}"
                            cell_root = output_root / "dev_grid" / cell_id
                            launched = launch_and_wait(raw_adb=raw_adb, root=cell_root / "launch", app=app, config=config)
                            last_package = app["package"]
                            if not launched["passed"]:
                                cell = {"cell_id": cell_id, "passed": False, "app": app, "launch": launched, "issues": ["FOREGROUND"]}
                            else:
                                observation = capture_observation(
                                    env=env, raw_adb=raw_adb, root=cell_root / "observation",
                                    config=config, app=app, foreground=launched["witnesses"],
                                    expected_adb_pid=adb_pid, expected_emulator_grpc_pid=emulator_pid,
                                    expected_forwarder_pid=forwarder_pid,
                                )
                                cell = {"cell_id": cell_id, "passed": observation["passed"], "app": app, "launch": launched, "observation": observation, "issues": observation["issues"]}
                            save_json(cell_root / "cell_result.json", cell)
                            grid_records.append(cell)
                            if not cell["passed"]:
                                first_broken_edge = f"GRID:{cell_id}:{cell['issues'][0] if cell['issues'] else 'UNKNOWN'}"
                                break
                        if first_broken_edge:
                            break
                    if len(grid_records) == config["grid"]["required_cells"] and all(record["passed"] for record in grid_records):
                        status = "PASS_12_OF_12_DEV"
                        first_broken_edge = None
    except Exception as exc:
        primary_error = {"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()}
        if first_broken_edge is None:
            first_broken_edge = f"EXCEPTION:{type(exc).__name__}:{exc}"
    finally:
        cleanup_result = cleanup(
            env=env, raw_adb=raw_adb, root=output_root / "cleanup", config=config,
            last_package=last_package, sidecar_port=sidecar_port,
            expected_adb_pid=adb_pid, expected_emulator_grpc_pid=emulator_pid,
        )
        if status == "PASS_12_OF_12_DEV" and not cleanup_result.get("passed"):
            status = "FAIL_CLEANUP"
            first_broken_edge = cleanup_result["issues"][0]

    protected_after = {name: sha256_path(REPOSITORY_ROOT / name) for name in config["protected_wip"]}
    completion = {
        "schema_version": "role_binding_timing.phase_b2_10.lifecycle_completion.v0.2.10",
        "status": status,
        "first_broken_edge": first_broken_edge,
        "started_at": started,
        "completed_at": utc_now(),
        "development_contaminated": True,
        "held_out_eligible": False,
        "generation_calls": 0,
        "model_tokens": 0,
        "rebind": rebind,
        "settings": {
            "required": 3, "completed": len(settings_records),
            "passed": sum(record["passed"] for record in settings_records),
            "records": settings_records,
        },
        "grid": {
            "authorized": len(settings_records) == 3 and all(record["passed"] for record in settings_records),
            "required": 12, "completed": len(grid_records),
            "passed": sum(record["passed"] for record in grid_records),
            "records": grid_records,
        },
        "runtime": {
            "adb_pid": adb_pid, "emulator_grpc_pid": emulator_pid,
            "emulator_process": emulator_record, "forwarder_pid": forwarder_pid,
            "sidecar_host_port": sidecar_port,
        },
        "primary_error": primary_error,
        "cleanup": cleanup_result,
        "protected_wip_before": protected_before,
        "protected_wip_after": protected_after,
        "protected_wip_unchanged": protected_before == protected_after == config["protected_wip"],
        "claim_evidence": {
            "accessibility_lifecycle_qualified": status == "PASS_12_OF_12_DEV",
            "v0_3_preparation_authorized": status == "PASS_12_OF_12_DEV",
            "held_out_capture_tested": False,
            "role_binding_hypothesis_tested": False,
            "memory_controller_oracle_efficacy_tested": False,
        },
    }
    schema = json.loads((REPOSITORY_ROOT / config["schema"]).read_text(encoding="utf-8"))
    schema_errors = [error.message for error in Draft202012Validator(schema).iter_errors(completion)]
    completion["schema_errors"] = schema_errors
    completion_path = output_root / "qualification_completion.json"
    if completion_path.exists():
        raise RuntimeError("DUPLICATE_TERMINAL_COMPLETION")
    write_json_atomic(completion_path, completion)

    artifacts = []
    for path in sorted(output_root.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.json":
            artifacts.append({"path": path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_path(path)})
    write_json_atomic(output_root / "artifact_manifest.json", {"schema_version": "role_binding_timing.phase_b2_10.lifecycle_manifest.v0.2.10", "artifacts": artifacts})
    print(json.dumps({
        "status": status, "first_broken_edge": first_broken_edge,
        "settings": f"{completion['settings']['passed']}/{completion['settings']['required']}",
        "grid": f"{completion['grid']['passed']}/{completion['grid']['required']}",
        "schema_errors": schema_errors,
    }, indent=2))
    return 0 if status == "PASS_12_OF_12_DEV" and not schema_errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
