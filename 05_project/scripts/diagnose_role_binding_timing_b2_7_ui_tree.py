"""Run the frozen B2.7 DEV-only UI-tree export diagnostic matrix."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
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

from qualify_role_binding_timing_b2_5_infrastructure import (  # noqa: E402
    ManagedAdb,
    framework_check,
    listener_pids,
    reset_app,
    save_bytes,
    sha256_path,
    write_json_atomic,
)
from raven_m.role_binding_timing.infrastructure_v0_2_5 import (  # noqa: E402
    parse_foreground_witnesses,
    validate_png,
)
from raven_m.role_binding_timing.ui_tree_export_v0_2_7 import (  # noqa: E402
    classify_root_cause,
    parse_state_markers,
    qualify_paths,
    validate_xml_bytes,
)


DIAGNOSIS_FREEZE_TAG = "role-binding-timing-b2.7-diagnosis-freeze-20260804"


def sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


class RawAdb:
    """Byte-preserving explicit-port ADB wrapper with auditable identity checks."""

    def __init__(self, managed: ManagedAdb) -> None:
        self.managed = managed

    @property
    def owner_pid(self) -> int:
        return self.managed.owner_pid

    def command(self, args: list[str]) -> list[str]:
        return [
            str(self.managed.binary),
            "-P",
            str(self.managed.port),
            "-s",
            self.managed.serial,
            *args,
        ]

    def run(self, args: list[str], *, timeout: float) -> tuple[dict[str, Any], bytes, bytes]:
        before = listener_pids(self.managed.port)
        if before != [self.owner_pid]:
            raise RuntimeError(f"ADB_IDENTITY_BEFORE:{before}")
        started = time.monotonic()
        stdout = b""
        stderr = b""
        try:
            result = subprocess.run(
                self.command(args), capture_output=True, text=False, check=False, timeout=timeout
            )
            stdout = bytes(result.stdout)
            stderr = bytes(result.stderr)
            returncode = result.returncode
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            stdout = bytes(exc.stdout or b"")
            stderr = bytes(exc.stderr or b"")
            returncode = None
            timed_out = True
        elapsed = time.monotonic() - started
        after = listener_pids(self.managed.port)
        record = {
            "command": self.command(args),
            "returncode": returncode,
            "timed_out": timed_out,
            "wall_time_seconds": elapsed,
            "stdout_sha256": sha256_bytes(stdout),
            "stdout_bytes": len(stdout),
            "stderr_sha256": sha256_bytes(stderr),
            "stderr_bytes": len(stderr),
            "adb_listener_pids_before": before,
            "adb_listener_pids_after": after,
            "adb_identity_continuous": before == [self.owner_pid] and after == [self.owner_pid],
        }
        return record, stdout, stderr


def persist_command(
    *, raw_adb: RawAdb, args: list[str], root: Path, name: str, timeout: float
) -> tuple[dict[str, Any], bytes, bytes]:
    record, stdout, stderr = raw_adb.run(args, timeout=timeout)
    stdout_artifact = save_bytes(root / f"{name}.stdout.bin", stdout)
    stderr_artifact = save_bytes(root / f"{name}.stderr.bin", stderr)
    record["stdout_artifact"] = stdout_artifact
    record["stderr_artifact"] = stderr_artifact
    return record, stdout, stderr


def collect_state_markers(
    *, raw_adb: RawAdb, root: Path, prefix: str, timeout: float
) -> dict[str, Any]:
    commands = {
        "power": ["shell", "dumpsys", "power"],
        "display": ["shell", "dumpsys", "display"],
        "window_policy": ["shell", "dumpsys", "window", "policy"],
        "device_idle": ["shell", "dumpsys", "deviceidle"],
    }
    records: dict[str, Any] = {}
    decoded: dict[str, str] = {}
    for name, args in commands.items():
        record, stdout, _ = persist_command(
            raw_adb=raw_adb, args=args, root=root, name=f"{prefix}.{name}", timeout=timeout
        )
        records[name] = record
        decoded[name] = stdout.decode("utf-8", errors="replace")
    markers = parse_state_markers(
        power=decoded["power"],
        display=decoded["display"],
        window_policy=decoded["window_policy"],
        device_idle=decoded["device_idle"],
    )
    markers["command_records"] = records
    markers["adb_identity_continuous"] = all(
        item["adb_identity_continuous"] for item in records.values()
    )
    return markers


def collect_readiness_sample(
    *,
    raw_adb: RawAdb,
    root: Path,
    index: int,
    expected_package: str,
    screen_size: tuple[int, int],
    timeout: float,
) -> dict[str, Any]:
    sample_root = root / "scene_readiness" / f"sample_{index:02d}"
    sample_root.mkdir(parents=True, exist_ok=False)
    activity_record, activity_raw, _ = persist_command(
        raw_adb=raw_adb,
        args=["shell", "dumpsys", "activity", "activities"],
        root=sample_root,
        name="activity_activities",
        timeout=timeout,
    )
    window_record, window_raw, _ = persist_command(
        raw_adb=raw_adb,
        args=["shell", "dumpsys", "window", "displays"],
        root=sample_root,
        name="window_displays",
        timeout=timeout,
    )
    process_record, process_raw, _ = persist_command(
        raw_adb=raw_adb,
        args=["shell", "pidof", expected_package],
        root=sample_root,
        name="process",
        timeout=timeout,
    )
    screenshot_record, screenshot, _ = persist_command(
        raw_adb=raw_adb,
        args=["exec-out", "screencap", "-p"],
        root=sample_root,
        name="screenshot",
        timeout=timeout,
    )
    witnesses = parse_foreground_witnesses(
        activity_raw.decode("utf-8", errors="replace"),
        window_raw.decode("utf-8", errors="replace"),
    )
    screenshot_validation = None
    screenshot_error = None
    try:
        screenshot_validation = validate_png(screenshot, screen_size)
    except Exception as exc:
        screenshot_error = f"{type(exc).__name__}:{exc}"
    passed = (
        expected_package in witnesses["activity_packages"]
        and expected_package in witnesses["window_packages"]
        and process_record["returncode"] == 0
        and bool(process_raw.strip())
        and screenshot_validation is not None
        and all(
            record["adb_identity_continuous"]
            for record in (activity_record, window_record, process_record, screenshot_record)
        )
    )
    sample = {
        "sample": index,
        "passed": passed,
        "witnesses": witnesses,
        "process_stdout": process_raw.decode("utf-8", errors="replace").strip(),
        "screenshot_validation": screenshot_validation,
        "screenshot_error": screenshot_error,
        "records": {
            "activity": activity_record,
            "window": window_record,
            "process": process_record,
            "screenshot": screenshot_record,
        },
    }
    write_json_atomic(sample_root / "sample.json", sample)
    return sample


def collect_dump_attempt(
    *,
    raw_adb: RawAdb,
    root: Path,
    precondition: str,
    form: dict[str, Any],
    repeat: int,
    expected_package: str,
    remote_root: str,
    direct_target: str,
    timeout: float,
) -> dict[str, Any]:
    attempt_id = f"{precondition}.{form['id']}.r{repeat:02d}"
    attempt_root = root / "matrix" / precondition / form["id"] / f"repeat_{repeat:02d}"
    attempt_root.mkdir(parents=True, exist_ok=False)
    remote_target = (
        f"{remote_root}/rbt_b27_{precondition}_{form['id']}_r{repeat:02d}.xml"
        if form["transport"] == "remote_file"
        else direct_target
    )
    markers_before = collect_state_markers(
        raw_adb=raw_adb, root=attempt_root, prefix="before", timeout=timeout
    )
    ls_before, _, _ = persist_command(
        raw_adb=raw_adb,
        args=["shell", "ls", "-l", remote_target],
        root=attempt_root,
        name="target_ls_before",
        timeout=timeout,
    )
    stat_before, _, _ = persist_command(
        raw_adb=raw_adb,
        args=["shell", "stat", "-c", "%n|%s|%f|%Y", remote_target],
        root=attempt_root,
        name="target_stat_before",
        timeout=timeout,
    )
    if form["transport"] == "remote_file" and stat_before["returncode"] == 0:
        raise RuntimeError(f"REMOTE_TARGET_PREEXISTED:{remote_target}")
    command = ["shell" if form["transport"] == "remote_file" else "exec-out", "uiautomator", "dump"]
    if form["compressed"]:
        command.append("--compressed")
    command.append(remote_target)
    dump_record, dump_stdout, _ = persist_command(
        raw_adb=raw_adb, args=command, root=attempt_root, name="dump", timeout=timeout
    )
    ls_after, _, _ = persist_command(
        raw_adb=raw_adb,
        args=["shell", "ls", "-l", remote_target],
        root=attempt_root,
        name="target_ls_after",
        timeout=timeout,
    )
    stat_after, _, _ = persist_command(
        raw_adb=raw_adb,
        args=["shell", "stat", "-c", "%n|%s|%f|%Y", remote_target],
        root=attempt_root,
        name="target_stat_after",
        timeout=timeout,
    )
    cat_record = None
    cleanup_record = None
    if form["transport"] == "remote_file":
        cat_record, candidate, _ = persist_command(
            raw_adb=raw_adb,
            args=["exec-out", "cat", remote_target],
            root=attempt_root,
            name="candidate_cat",
            timeout=timeout,
        )
        cleanup_record, _, _ = persist_command(
            raw_adb=raw_adb,
            args=["shell", "rm", "-f", remote_target],
            root=attempt_root,
            name="target_cleanup",
            timeout=timeout,
        )
    else:
        candidate = dump_stdout
    candidate_artifact = save_bytes(attempt_root / "candidate.raw.bin", candidate)
    validation = validate_xml_bytes(candidate, expected_package=expected_package)
    if validation.payload:
        payload_artifact = save_bytes(attempt_root / "validated_payload.xml", validation.payload)
    else:
        payload_artifact = None
    markers_after = collect_state_markers(
        raw_adb=raw_adb, root=attempt_root, prefix="after", timeout=timeout
    )
    records = [dump_record, ls_before, stat_before, ls_after, stat_after]
    if cat_record is not None:
        records.append(cat_record)
    if cleanup_record is not None:
        records.append(cleanup_record)
    identity_continuous = (
        markers_before["adb_identity_continuous"]
        and markers_after["adb_identity_continuous"]
        and all(item["adb_identity_continuous"] for item in records)
    )
    attempt = {
        "attempt_id": attempt_id,
        "precondition": precondition,
        "form_id": form["id"],
        "transport": form["transport"],
        "compressed": form["compressed"],
        "repeat": repeat,
        "remote_target": remote_target,
        "dump_executed": True,
        "state_markers_before": markers_before,
        "state_markers_after": markers_after,
        "target_before": {"ls": ls_before, "stat": stat_before},
        "dump_record": dump_record,
        "target_after": {"ls": ls_after, "stat": stat_after},
        "cat_record": cat_record,
        "cleanup_record": cleanup_record,
        "candidate_artifact": candidate_artifact,
        "validated_payload_artifact": payload_artifact,
        "xml_validation": validation.as_dict(),
        "adb_identity_continuous": identity_continuous,
    }
    write_json_atomic(attempt_root / "attempt.json", attempt)
    return attempt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "configs" / "role_binding_timing" / "phase_b2_7_ui_tree_export_diagnosis.json",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=PROJECT_ROOT / "schemas" / "role_binding_timing_ui_tree_export_diagnosis.v0_2_7.schema.json",
    )
    parser.add_argument("--diagnosis-commit", required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    schema_path = args.schema.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if config["generation_calls_authorized"] != 0 or config["generation_eligible"] is not False:
        raise RuntimeError("GENERATION_BOUNDARY")
    tag_commit = subprocess.check_output(
        ["git", "rev-list", "-n", "1", DIAGNOSIS_FREEZE_TAG], cwd=REPOSITORY_ROOT, text=True
    ).strip()
    if tag_commit != args.diagnosis_commit:
        raise RuntimeError("DIAGNOSIS_FREEZE_TAG_MISMATCH")
    output_root = REPOSITORY_ROOT / config["output_root"]
    if output_root.exists():
        raise RuntimeError("DIAGNOSIS_OUTPUT_NOT_FRESH")
    output_root.mkdir(parents=True)
    started = time.monotonic()
    managed: ManagedAdb | None = None
    raw_adb: RawAdb | None = None
    framework_before = None
    setup_records: dict[str, Any] = {}
    readiness_samples: list[dict[str, Any]] = []
    attempts: list[dict[str, Any]] = []
    precondition_markers: dict[str, Any] = {}
    logcat_records: dict[str, Any] = {}
    primary_error = None
    cleanup = None
    try:
        managed = ManagedAdb(
            binary=REPOSITORY_ROOT / config["runtime"]["adb_binary"],
            expected_hash=config["runtime"]["adb_binary_sha256"],
            port=config["runtime"]["adb_server_port"],
            serial=config["runtime"]["device_serial"],
        )
        raw_adb = RawAdb(managed)
        framework_before = framework_check(managed, ["package", "window", "activity"])
        if not framework_before["passed"]:
            raise RuntimeError("FRAMEWORK_BEFORE_FAILED")
        reset_before = reset_app(managed, config["scene"]["package"], config["matrix"]["command_timeout_seconds"])
        setup_records["reset_before"] = reset_before
        if not reset_before["passed"]:
            raise RuntimeError("RESET_BEFORE_FAILED")
        launch_record, _, _ = persist_command(
            raw_adb=raw_adb,
            args=["shell", "am", "start", "-n", config["scene"]["component"]],
            root=output_root / "setup",
            name="launch_nonwait",
            timeout=config["matrix"]["command_timeout_seconds"],
        )
        setup_records["launch_nonwait"] = launch_record
        if launch_record["returncode"] != 0 or launch_record["timed_out"]:
            raise RuntimeError("SCENE_LAUNCH_COMMAND_FAILED")
        time.sleep(config["setup"]["launch_settle_seconds"])
        consecutive = 0
        for index in range(1, config["setup"]["readiness_attempts"] + 1):
            sample = collect_readiness_sample(
                raw_adb=raw_adb,
                root=output_root,
                index=index,
                expected_package=config["scene"]["package"],
                screen_size=tuple(config["runtime"]["screen_size"]),
                timeout=config["matrix"]["command_timeout_seconds"],
            )
            readiness_samples.append(sample)
            consecutive = consecutive + 1 if sample["passed"] else 0
            if consecutive >= config["setup"]["readiness_consecutive"]:
                break
            if index < config["setup"]["readiness_attempts"]:
                time.sleep(config["setup"]["readiness_gap_seconds"])
        if consecutive < config["setup"]["readiness_consecutive"]:
            raise RuntimeError("SCENE_READINESS_FAILED")
        help_record, _, _ = persist_command(
            raw_adb=raw_adb,
            args=["shell", "uiautomator"],
            root=output_root / "diagnostics",
            name="uiautomator_usage",
            timeout=config["matrix"]["command_timeout_seconds"],
        )
        setup_records["uiautomator_usage"] = help_record
        clear_record, _, _ = persist_command(
            raw_adb=raw_adb,
            args=["logcat", "-c"],
            root=output_root / "diagnostics",
            name="logcat_clear",
            timeout=config["matrix"]["command_timeout_seconds"],
        )
        setup_records["logcat_clear"] = clear_record
        for precondition in config["matrix"]["preconditions"]:
            if precondition["apply_wake"]:
                wake_records = []
                for command_index, command in enumerate(config["setup"]["wake_commands"], start=1):
                    record, _, _ = persist_command(
                        raw_adb=raw_adb,
                        args=command,
                        root=output_root / "preconditions" / precondition["id"],
                        name=f"wake_{command_index:02d}",
                        timeout=config["matrix"]["command_timeout_seconds"],
                    )
                    wake_records.append(record)
                setup_records["wake_commands"] = wake_records
            phase_markers = collect_state_markers(
                raw_adb=raw_adb,
                root=output_root / "preconditions" / precondition["id"],
                prefix="verified",
                timeout=config["matrix"]["command_timeout_seconds"],
            )
            precondition_markers[precondition["id"]] = phase_markers
            if precondition["apply_wake"] and not phase_markers["interactive_verified"]:
                raise RuntimeError("WAKE_INTERACTIVE_PRECONDITION_FAILED")
            for form in config["matrix"]["forms"]:
                for repeat in range(1, config["matrix"]["repeats"] + 1):
                    attempt = collect_dump_attempt(
                        raw_adb=raw_adb,
                        root=output_root,
                        precondition=precondition["id"],
                        form=form,
                        repeat=repeat,
                        expected_package=config["scene"]["package"],
                        remote_root=config["matrix"]["remote_root"],
                        direct_target=config["matrix"]["direct_target"],
                        timeout=config["matrix"]["command_timeout_seconds"],
                    )
                    attempts.append(attempt)
                    print(
                        json.dumps(
                            {
                                "batch": "B2.7_UI_TREE_DEV",
                                "attempt": attempt["attempt_id"],
                                "xml_valid": attempt["xml_validation"]["valid"],
                                "completed": len(attempts),
                                "planned": 16,
                            }
                        ),
                        flush=True,
                    )
                    if not attempt["adb_identity_continuous"]:
                        raise RuntimeError("ADB_IDENTITY_DRIFT")
                    time.sleep(config["matrix"]["attempt_gap_seconds"])
        tags = ",".join(config["diagnostics"]["logcat_tags"])
        log_record, _, _ = persist_command(
            raw_adb=raw_adb,
            args=["logcat", "-d", "-t", str(config["diagnostics"]["logcat_tail_lines"]), "-v", "threadtime"],
            root=output_root / "diagnostics",
            name="logcat_tail",
            timeout=config["matrix"]["command_timeout_seconds"],
        )
        log_record["requested_tags_for_review"] = tags
        logcat_records["tail"] = log_record
        accessibility_record, _, _ = persist_command(
            raw_adb=raw_adb,
            args=["shell", "dumpsys", "accessibility"],
            root=output_root / "diagnostics",
            name="accessibility_after",
            timeout=config["matrix"]["command_timeout_seconds"],
        )
        logcat_records["accessibility"] = accessibility_record
    except Exception as exc:
        primary_error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback_sha256": sha256_bytes(traceback.format_exc().encode("utf-8")),
        }
    finally:
        if managed is not None:
            try:
                cleanup = reset_app(managed, config["scene"]["package"], config["matrix"]["command_timeout_seconds"])
            except Exception as exc:
                cleanup = {"passed": False, "error": f"{type(exc).__name__}:{exc}"}
    qualified = qualify_paths(attempts, config["matrix"]["repeats"])
    classification = classify_root_cause(
        attempts=attempts,
        qualified_paths=qualified,
        baseline_interactive=bool(precondition_markers.get("observed", {}).get("interactive_verified")),
        wake_interactive=bool(precondition_markers.get("wake_dismiss_verified", {}).get("interactive_verified")),
    )
    final_pids = listener_pids(config["runtime"]["adb_server_port"])
    matrix_complete = (
        primary_error is None
        and len(attempts) == 16
        and cleanup is not None
        and cleanup.get("passed") is True
        and managed is not None
        and final_pids == [managed.owner_pid]
    )
    classification["matrix_complete"] = matrix_complete
    classification["task_agnostic_acquisition_authorized"] = bool(
        classification["task_agnostic_acquisition_authorized"] and matrix_complete
    )
    result = {
        "schema_version": "role_binding_timing.ui_tree_export_diagnosis.v0_2_7",
        "study_id": config["study_id"],
        "diagnosis_freeze_commit": args.diagnosis_commit,
        "generation_calls": 0,
        "generation_eligible": False,
        "dev_contaminated": True,
        "held_out_eligible": False,
        "source_hashes": {
            "config": sha256_path(config_path),
            "schema": sha256_path(schema_path),
            "runner": sha256_path(Path(__file__)),
            "logic": sha256_path(PROJECT_ROOT / "src/raven_m/role_binding_timing/ui_tree_export_v0_2_7.py"),
        },
        "server_owner": managed.owner if managed is not None else {
            "listener_pid": final_pids[0] if len(final_pids) == 1 else 1,
            "binary_sha256": config["runtime"]["adb_binary_sha256"],
            "port": 5038,
            "device_serial": config["runtime"]["device_serial"],
            "fallback_to_5037": False,
        },
        "framework_before": framework_before,
        "setup_records": setup_records,
        "scene_readiness": {
            "required_consecutive": config["setup"]["readiness_consecutive"],
            "samples": readiness_samples,
            "passed": len(readiness_samples) >= config["setup"]["readiness_consecutive"]
            and all(item["passed"] for item in readiness_samples[-config["setup"]["readiness_consecutive"] :]),
        },
        "precondition_markers": precondition_markers,
        "attempts": attempts,
        "logcat_records": logcat_records,
        "classification": classification,
        "cleanup": cleanup,
        "wall_time_seconds": time.monotonic() - started,
        "terminal_audit": {
            "primary_error": primary_error,
            "schema_errors": [],
            "planned_attempts": 16,
            "completed_attempts": len(attempts),
            "valid_attempts": sum(item["xml_validation"]["valid"] for item in attempts),
            "final_listener_pids": final_pids,
            "generation_calls": 0,
            "implementation_freeze_authorized": classification["task_agnostic_acquisition_authorized"],
            "v0_3_preparation_authorized": False,
            "write_policy": "atomic_exactly_once",
        },
    }
    errors = sorted(Draft202012Validator(schema).iter_errors(result), key=lambda error: list(error.path))
    result["terminal_audit"]["schema_errors"] = [error.message for error in errors]
    if errors:
        result["classification"]["task_agnostic_acquisition_authorized"] = False
        result["terminal_audit"]["implementation_freeze_authorized"] = False
    result_path = output_root / "ui_tree_export_diagnosis.v0_2_7.json"
    write_json_atomic(result_path, result)
    print(
        json.dumps(
            {
                "result": str(result_path),
                "root_cause": result["classification"]["root_cause"],
                "authorized": result["classification"]["task_agnostic_acquisition_authorized"],
                "generation_calls": 0,
            },
            indent=2,
        )
    )
    return 0 if result["classification"]["task_agnostic_acquisition_authorized"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
