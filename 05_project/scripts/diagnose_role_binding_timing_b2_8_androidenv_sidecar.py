"""Run the frozen B2.8 zero-model Settings AndroidEnv sidecar diagnosis."""

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
from raven_m.role_binding_timing.androidenv_sidecar_runtime_v0_2_8 import (  # noqa: E402
    load_explicit_sidecar_env,
    sidecar_runtime_identity,
)
from raven_m.role_binding_timing.androidenv_sidecar_v0_2_8 import (  # noqa: E402
    ROUTE_LABEL,
    canonical_json_bytes,
    derive_stable_oracle_candidates,
    deterministic_forest_bytes,
    protobuf_field_manifest,
    qualify_observation,
    serialize_ui_elements,
    sha256_bytes,
    validate_pixels,
)
from raven_m.role_binding_timing.infrastructure_v0_2_5 import (  # noqa: E402
    parse_foreground_witnesses,
)


FREEZE_TAG = "role-binding-timing-b2.8-sidecar-diagnosis-freeze-20260804"
PROTECTED_WIP = {
    "05_project/src/raven_m/controller/episode_controller.py": "fc0e82e0fde90119365d4f685f080eb4519bf2f602e4bda58de5d4809a40fe33",
    "05_project/src/raven_m/controller/protocol_v2_guard.py": "ff89d6b70be4b4738646d262beb67d7b7e932e9eb95956d940b1c5000a999d10",
    "05_project/tests/scripts/test_protocol_v2_2_r79_r78_trace_replay.py": "5bb1f1e3de673a1072cfee62938b761a62fd69c187d5eadf54bc46b115a3fd0a",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def artifact(path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(REPOSITORY_ROOT).as_posix(),
        "sha256": sha256_path(path),
        "bytes": path.stat().st_size,
    }


def save_bytes(path: Path, value: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    return artifact(path)


def save_json_canonical(path: Path, value: Any) -> dict[str, Any]:
    return save_bytes(path, canonical_json_bytes(value))


def verify_file_hashes(records: dict[str, str]) -> list[str]:
    issues = []
    for relative, expected in records.items():
        path = REPOSITORY_ROOT / relative
        actual = sha256_path(path) if path.exists() else None
        if actual != expected:
            issues.append(f"HASH_MISMATCH:{relative}:{actual}:{expected}")
    return issues


class RawAdb:
    """Byte-preserving official-ADB client with explicit 5038 continuity."""

    def __init__(self, managed: ManagedAdb) -> None:
        self.managed = managed

    def command(self, args: list[str]) -> list[str]:
        return [
            str(self.managed.binary), "-P", str(self.managed.port), "-s", self.managed.serial, *args
        ]

    def run(self, args: list[str], *, root: Path, name: str, timeout: float) -> tuple[dict[str, Any], bytes, bytes]:
        before = listener_pids(self.managed.port)
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
        after = listener_pids(self.managed.port)
        record = {
            "command": self.command(args),
            "returncode": returncode,
            "timed_out": timed_out,
            "wall_time_seconds": time.monotonic() - started,
            "stdout_sha256": sha256_bytes(stdout),
            "stdout_bytes": len(stdout),
            "stderr_sha256": sha256_bytes(stderr),
            "stderr_bytes": len(stderr),
            "adb_listener_pids_before": before,
            "adb_listener_pids_after": after,
            "adb_identity_continuous": before == [self.managed.owner_pid] and after == [self.managed.owner_pid],
        }
        root.mkdir(parents=True, exist_ok=True)
        record["stdout_artifact"] = save_bytes(root / f"{name}.stdout.bin", stdout)
        record["stderr_artifact"] = save_bytes(root / f"{name}.stderr.bin", stderr)
        return record, stdout, stderr


def _process_identity(pid: int, *, expected_path: Path, expected_hash: str) -> tuple[dict[str, Any], list[str]]:
    record = process_record(pid)
    actual_path = Path(record["executable_path"]).resolve()
    actual_hash = sha256_path(actual_path)
    issues = []
    if actual_path != expected_path.resolve():
        issues.append(f"PROCESS_PATH:{actual_path}:{expected_path.resolve()}")
    if actual_hash != expected_hash:
        issues.append(f"PROCESS_HASH:{actual_hash}:{expected_hash}")
    record["executable_path"] = str(actual_path)
    record["binary_sha256"] = actual_hash
    return record, issues


def collect_identity(
    *, raw_adb: RawAdb, root: Path, config: dict[str, Any], sidecar: dict[str, Any]
) -> dict[str, Any]:
    runtime = config["runtime"]
    service = config["accessibility_service"]
    records: dict[str, Any] = {}
    payloads: dict[str, bytes] = {}
    commands = {
        "enabled_services": ["shell", "settings", "get", "secure", "enabled_accessibility_services"],
        "accessibility_enabled": ["shell", "settings", "get", "secure", "accessibility_enabled"],
        "forwarder_pm_path": ["shell", "pm", "path", service["package"]],
        "accessibility_dump": ["shell", "dumpsys", "accessibility"],
        "activity_activities": ["shell", "dumpsys", "activity", "activities"],
        "window_displays": ["shell", "dumpsys", "window", "displays"],
    }
    for name, command in commands.items():
        record, stdout, _ = raw_adb.run(
            command, root=root, name=name, timeout=config["diagnostic"]["command_timeout_seconds"]
        )
        records[name] = record
        payloads[name] = stdout
    pm_text = payloads["forwarder_pm_path"].decode("utf-8", errors="replace").strip()
    apk_path = pm_text.split("package:", 1)[1].strip() if pm_text.startswith("package:") else ""
    if apk_path:
        record, stdout, _ = raw_adb.run(
            ["shell", "sha256sum", apk_path],
            root=root,
            name="forwarder_apk_sha256sum",
            timeout=config["diagnostic"]["command_timeout_seconds"],
        )
        records["forwarder_apk_sha256sum"] = record
        apk_hash = stdout.decode("ascii", errors="replace").strip().split()[0] if stdout.strip() else ""
    else:
        apk_hash = ""
    adb_pids = listener_pids(runtime["adb_server_port"])
    grpc_pids = listener_pids(runtime["emulator_grpc_port"])
    fallback = listener_pids(5037)
    host_sidecar_pids = listener_pids(int(sidecar["sidecar_host_port"]))
    issues: list[str] = []
    adb_process = None
    grpc_process = None
    if adb_pids == [raw_adb.managed.owner_pid]:
        adb_process, process_issues = _process_identity(
            adb_pids[0],
            expected_path=REPOSITORY_ROOT / runtime["adb_binary"],
            expected_hash=runtime["adb_binary_sha256"],
        )
        issues.extend(f"ADB_{item}" for item in process_issues)
    else:
        issues.append(f"ADB_LISTENER:{adb_pids}:{raw_adb.managed.owner_pid}")
    if len(grpc_pids) == 1:
        grpc_process, process_issues = _process_identity(
            grpc_pids[0],
            expected_path=REPOSITORY_ROOT / runtime["emulator_binary"],
            expected_hash=runtime["emulator_binary_sha256"],
        )
        issues.extend(f"GRPC_{item}" for item in process_issues)
    else:
        issues.append(f"GRPC_LISTENER:{grpc_pids}")
    enabled = payloads["enabled_services"].decode("utf-8", errors="replace").strip()
    accessibility_enabled = payloads["accessibility_enabled"].decode("utf-8", errors="replace").strip()
    dump_text = payloads["accessibility_dump"].decode("utf-8", errors="replace")
    if enabled != service["component"]:
        issues.append(f"A11Y_ENABLED_COMPONENT:{enabled}")
    if accessibility_enabled != "1":
        issues.append(f"A11Y_GLOBAL_DISABLED:{accessibility_enabled}")
    if service["component"] not in dump_text:
        issues.append("A11Y_COMPONENT_ABSENT_FROM_DUMPSYS")
    if apk_hash != service["installed_apk_sha256"]:
        issues.append(f"A11Y_APK_HASH:{apk_hash}")
    if fallback:
        issues.append(f"FORBIDDEN_5037_LISTENER:{fallback}")
    if os.getpid() not in host_sidecar_pids:
        issues.append(f"SIDECAR_HOST_LISTENER:{host_sidecar_pids}:{os.getpid()}")
    if not all(item["adb_identity_continuous"] for item in records.values()):
        issues.append("ADB_IDENTITY_DRIFT_DURING_IDENTITY_CAPTURE")
    witnesses = parse_foreground_witnesses(
        payloads["activity_activities"].decode("utf-8", errors="replace"),
        payloads["window_displays"].decode("utf-8", errors="replace"),
    )
    return {
        "qualified": not issues,
        "issues": issues,
        "adb_pid": adb_pids[0] if len(adb_pids) == 1 else -1,
        "adb_process": adb_process,
        "emulator_grpc_pid": grpc_pids[0] if len(grpc_pids) == 1 else -1,
        "emulator_grpc_process": grpc_process,
        "fallback_5037_listener_pids": fallback,
        "sidecar_host_listener_pids": host_sidecar_pids,
        "a11y_component": enabled,
        "a11y_component_config_sha256": service["component_sha256"],
        "a11y_apk_path": apk_path,
        "a11y_apk_sha256": apk_hash,
        "a11y_dump_sha256": sha256_bytes(payloads["accessibility_dump"]),
        "activity_packages": witnesses["activity_packages"],
        "window_packages": witnesses["window_packages"],
        "records": records,
        **sidecar,
    }


def collect_foreground_sample(
    *, raw_adb: RawAdb, root: Path, index: int, expected_package: str, timeout: float
) -> dict[str, Any]:
    sample_root = root / f"sample_{index:02d}"
    activity_record, activity_raw, _ = raw_adb.run(
        ["shell", "dumpsys", "activity", "activities"],
        root=sample_root,
        name="activity_activities",
        timeout=timeout,
    )
    window_record, window_raw, _ = raw_adb.run(
        ["shell", "dumpsys", "window", "displays"],
        root=sample_root,
        name="window_displays",
        timeout=timeout,
    )
    process_record_, process_raw, _ = raw_adb.run(
        ["shell", "pidof", expected_package], root=sample_root, name="process", timeout=timeout
    )
    witnesses = parse_foreground_witnesses(
        activity_raw.decode("utf-8", errors="replace"),
        window_raw.decode("utf-8", errors="replace"),
    )
    passed = (
        expected_package in witnesses["activity_packages"]
        and expected_package in witnesses["window_packages"]
        and process_record_["returncode"] == 0
        and bool(process_raw.strip())
        and all(item["adb_identity_continuous"] for item in (activity_record, window_record, process_record_))
    )
    sample = {
        "index": index,
        "passed": passed,
        "witnesses": witnesses,
        "process_stdout": process_raw.decode("utf-8", errors="replace").strip(),
        "records": {"activity": activity_record, "window": window_record, "process": process_record_},
    }
    write_json_atomic(sample_root / "sample.json", sample)
    return sample


def reset_scene(raw_adb: RawAdb, root: Path, package: str, timeout: float) -> dict[str, Any]:
    records = {}
    for name, args in (
        ("press_home", ["shell", "input", "keyevent", "3"]),
        ("force_stop", ["shell", "am", "force-stop", package]),
    ):
        record, _, _ = raw_adb.run(args, root=root, name=name, timeout=timeout)
        records[name] = record
    issues = [name for name, record in records.items() if record["returncode"] != 0 or record["timed_out"] or not record["adb_identity_continuous"]]
    return {"passed": not issues, "issues": issues, "records": records}


def verify_artifacts(records: list[dict[str, Any]]) -> list[str]:
    issues = []
    for record in records:
        path = REPOSITORY_ROOT / record["path"]
        if not path.exists() or path.stat().st_size != record["bytes"] or sha256_path(path) != record["sha256"]:
            issues.append(f"ARTIFACT_MISMATCH:{record['path']}")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "configs/role_binding_timing/phase_b2_8_androidenv_sidecar_diagnosis.json",
    )
    parser.add_argument("--freeze-commit", required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config["generation_calls_authorized"] != 0 or config["generation_eligible"] is not False:
        raise RuntimeError("GENERATION_BOUNDARY")
    lock_path = PROJECT_ROOT / "configs/role_binding_timing/phase_b2_8_androidenv_sidecar_diagnosis.lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    freeze_commit = subprocess.check_output(
        ["git", "rev-list", "-n", "1", FREEZE_TAG], cwd=REPOSITORY_ROOT, text=True
    ).strip()
    if freeze_commit != args.freeze_commit:
        raise RuntimeError(f"FREEZE_TAG_MISMATCH:{freeze_commit}:{args.freeze_commit}")
    hash_issues = verify_file_hashes(lock["locked_files"])
    protected_before = {path: sha256_path(REPOSITORY_ROOT / path) for path in PROTECTED_WIP}
    if hash_issues or protected_before != PROTECTED_WIP:
        raise RuntimeError(f"LOCK_OR_PROTECTED_HASH_FAILURE:{hash_issues}:{protected_before}")
    schema_path = REPOSITORY_ROOT / config["schema"]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    output_root = REPOSITORY_ROOT / config["output_root"]
    if output_root.exists():
        raise RuntimeError("DIAGNOSIS_OUTPUT_NOT_FRESH")
    output_root.mkdir(parents=True)
    started = time.monotonic()
    managed: ManagedAdb | None = None
    raw_adb: RawAdb | None = None
    env = None
    sidecar = None
    state_calls = 0
    primary_error = None
    qualification_passed = False
    readiness_samples: list[dict[str, Any]] = []
    setup: dict[str, Any] = {}
    identity_before = None
    identity_after = None
    observation_record = None
    observation_artifacts: list[dict[str, Any]] = []
    cleanup: dict[str, Any] = {}
    try:
        managed = ManagedAdb(
            binary=REPOSITORY_ROOT / config["runtime"]["adb_binary"],
            expected_hash=config["runtime"]["adb_binary_sha256"],
            port=config["runtime"]["adb_server_port"],
            serial=config["runtime"]["device_serial"],
        )
        if managed.owner_pid != lock["runtime_preflight"]["adb_5038_listener_pid"]:
            raise RuntimeError(
                f"ADB_PID_CHANGED_SINCE_FREEZE:{managed.owner_pid}:"
                f"{lock['runtime_preflight']['adb_5038_listener_pid']}"
            )
        raw_adb = RawAdb(managed)
        if listener_pids(5037):
            raise RuntimeError(f"FORBIDDEN_5037_LISTENER_PREFLIGHT:{listener_pids(5037)}")
        grpc_pids = listener_pids(config["runtime"]["emulator_grpc_port"])
        if len(grpc_pids) != 1:
            raise RuntimeError(f"EMULATOR_GRPC_LISTENER_PREFLIGHT:{grpc_pids}")
        if grpc_pids[0] != lock["runtime_preflight"]["emulator_grpc_8554_listener_pid"]:
            raise RuntimeError(
                f"EMULATOR_GRPC_PID_CHANGED_SINCE_FREEZE:{grpc_pids[0]}:"
                f"{lock['runtime_preflight']['emulator_grpc_8554_listener_pid']}"
            )
        _, grpc_issues = _process_identity(
            grpc_pids[0],
            expected_path=REPOSITORY_ROOT / config["runtime"]["emulator_binary"],
            expected_hash=config["runtime"]["emulator_binary_sha256"],
        )
        if grpc_issues:
            raise RuntimeError(f"EMULATOR_GRPC_IDENTITY_PREFLIGHT:{grpc_issues}")
        for service_name in ("package", "window", "activity"):
            record, stdout, _ = raw_adb.run(
                ["shell", "service", "check", service_name],
                root=output_root / "preflight",
                name=f"framework_{service_name}",
                timeout=config["diagnostic"]["command_timeout_seconds"],
            )
            if record["returncode"] != 0 or b"not found" in stdout.casefold():
                raise RuntimeError(f"FRAMEWORK_PREFLIGHT:{service_name}")
        env = load_explicit_sidecar_env(
            adb_path=str((REPOSITORY_ROOT / config["runtime"]["adb_binary"]).resolve()),
            adb_server_port=config["runtime"]["adb_server_port"],
            console_port=config["runtime"]["console_port"],
            grpc_port=config["runtime"]["emulator_grpc_port"],
        )
        sidecar = sidecar_runtime_identity(env)
        setup["sidecar"] = sidecar
        setup["reset_before"] = reset_scene(
            raw_adb,
            output_root / "setup/reset_before",
            config["diagnostic"]["package"],
            config["diagnostic"]["command_timeout_seconds"],
        )
        if not setup["reset_before"]["passed"]:
            raise RuntimeError(f"RESET_BEFORE:{setup['reset_before']['issues']}")
        launch_record, _, _ = raw_adb.run(
            ["shell", "am", "start", "-n", config["diagnostic"]["component"]],
            root=output_root / "setup",
            name="launch_nonwait",
            timeout=config["diagnostic"]["command_timeout_seconds"],
        )
        setup["launch"] = launch_record
        if launch_record["returncode"] != 0 or launch_record["timed_out"] or not launch_record["adb_identity_continuous"]:
            raise RuntimeError("LAUNCH_COMMAND_FAILED")
        consecutive = 0
        for index in range(1, config["diagnostic"]["foreground_attempts"] + 1):
            sample = collect_foreground_sample(
                raw_adb=raw_adb,
                root=output_root / "foreground_readiness",
                index=index,
                expected_package=config["diagnostic"]["package"],
                timeout=config["diagnostic"]["command_timeout_seconds"],
            )
            readiness_samples.append(sample)
            consecutive = consecutive + 1 if sample["passed"] else 0
            if consecutive >= config["diagnostic"]["foreground_required_consecutive"]:
                break
            time.sleep(config["diagnostic"]["foreground_interval_seconds"])
        if consecutive < config["diagnostic"]["foreground_required_consecutive"]:
            raise RuntimeError("FOREGROUND_READINESS_FAILED")
        time.sleep(config["diagnostic"]["post_foreground_settle_seconds"])
        identity_before = collect_identity(
            raw_adb=raw_adb,
            root=output_root / "observation/identity_before",
            config=config,
            sidecar=sidecar,
        )
        if not identity_before["qualified"]:
            raise RuntimeError(f"IDENTITY_BEFORE:{identity_before['issues']}")
        env_activity_before = env.foreground_activity_name
        state_calls += 1
        state = env.get_state(wait_to_stabilize=config["diagnostic"]["wait_to_stabilize"])
        env_activity_after = env.foreground_activity_name
        current_sidecar = sidecar_runtime_identity(env)
        identity_after = collect_identity(
            raw_adb=raw_adb,
            root=output_root / "observation/identity_after",
            config=config,
            sidecar=current_sidecar,
        )
        observation_root = output_root / "observation/payload"
        pixel_validation = validate_pixels(
            state.pixels, tuple(config["diagnostic"]["expected_pixel_shape"])
        )
        pixel_raw = state.pixels.tobytes(order="C")
        raw_pixel_artifact = save_bytes(observation_root / "pixels.raw.bin", pixel_raw)
        png_buffer = io.BytesIO()
        Image.fromarray(state.pixels).save(png_buffer, format="PNG")
        png_artifact = save_bytes(observation_root / "pixels.same_state.png", png_buffer.getvalue())
        forest_raw = deterministic_forest_bytes(state.forest)
        forest_artifact = save_bytes(observation_root / "accessibility_forest.pb", forest_raw)
        protobuf_manifest = protobuf_field_manifest(state.forest)
        protobuf_manifest_artifact = save_json_canonical(
            observation_root / "accessibility_forest.field_manifest.canonical.json", protobuf_manifest
        )
        element_raw, field_manifest = serialize_ui_elements(state.ui_elements)
        elements_artifact = save_bytes(observation_root / "ui_elements.canonical.json", element_raw)
        field_manifest_artifact = save_json_canonical(
            observation_root / "ui_elements.field_type_manifest.canonical.json", field_manifest
        )
        width = config["diagnostic"]["expected_pixel_shape"][1]
        height = config["diagnostic"]["expected_pixel_shape"][0]
        candidates = derive_stable_oracle_candidates(
            state.ui_elements,
            expected_package=config["diagnostic"]["package"],
            screen_width=width,
            screen_height=height,
        )
        def activity_package(value: str) -> list[str]:
            package = value.split("/", 1)[0].strip() if value else ""
            return [package] if package else []
        foreground = {
            "activity_packages": identity_after["activity_packages"],
            "window_packages": identity_after["window_packages"],
            "env_packages": sorted(set(activity_package(env_activity_before) + activity_package(env_activity_after))),
            "env_activity_before": env_activity_before,
            "env_activity_after": env_activity_after,
        }
        issues = qualify_observation(
            elements=state.ui_elements,
            expected_package=config["diagnostic"]["package"],
            foreground_packages=foreground,
            oracle_candidates=candidates,
            pixel_validation=pixel_validation,
            forest_bytes=forest_raw,
            identity_before=identity_before,
            identity_after=identity_after,
        )
        observation_artifacts = [
            raw_pixel_artifact,
            png_artifact,
            forest_artifact,
            protobuf_manifest_artifact,
            elements_artifact,
            field_manifest_artifact,
        ]
        issues.extend(verify_artifacts(observation_artifacts))
        observation_record = {
            "schema_version": "role_binding_timing.androidenv_sidecar.observation.v0.2.8",
            "route_label": ROUTE_LABEL,
            "development_contaminated": True,
            "held_out_eligible": False,
            "generation_calls": 0,
            "same_get_state_observation": True,
            "expected_package": config["diagnostic"]["package"],
            "foreground": foreground,
            "identity_before": identity_before,
            "identity_after": identity_after,
            "screenshot": {
                **pixel_validation,
                "raw_artifact": raw_pixel_artifact,
                "png_artifact": png_artifact,
            },
            "accessibility": {
                "element_count": len(state.ui_elements),
                "element_field_count": field_manifest["field_count"],
                "forest_artifact": forest_artifact,
                "elements_artifact": elements_artifact,
                "field_manifest_artifact": field_manifest_artifact,
                "protobuf_manifest_artifact": protobuf_manifest_artifact,
                "forest_sha256": sha256_bytes(forest_raw),
                "elements_sha256": sha256_bytes(element_raw),
                "element_packages": sorted({item.package_name for item in state.ui_elements if item.package_name}),
                "oracle_candidates": candidates,
            },
            "qualification": {"passed": not issues, "issues": issues},
        }
        errors = sorted(error.message for error in validator.iter_errors(observation_record))
        if errors:
            raise RuntimeError(f"OBSERVATION_SCHEMA:{errors}")
        write_json_atomic(output_root / "observation/observation_record.json", observation_record)
        if issues:
            raise RuntimeError(f"OBSERVATION_QUALIFICATION:{issues}")
        qualification_passed = True
    except Exception as exc:  # terminal evidence must survive every failed layer
        primary_error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        if raw_adb is not None:
            try:
                cleanup["reset_after"] = reset_scene(
                    raw_adb,
                    output_root / "cleanup/reset_after",
                    config["diagnostic"]["package"],
                    config["diagnostic"]["command_timeout_seconds"],
                )
            except Exception as exc:
                cleanup["reset_after_error"] = f"{type(exc).__name__}:{exc}"
        if env is not None:
            try:
                env.close()
                cleanup["env_close"] = "closed"
            except Exception as exc:
                cleanup["env_close_error"] = f"{type(exc).__name__}:{exc}"
        cleanup["adb_5038_listener_pids_after"] = listener_pids(config["runtime"]["adb_server_port"])
        cleanup["adb_5037_listener_pids_after"] = listener_pids(5037)
        cleanup["emulator_grpc_8554_listener_pids_after"] = listener_pids(config["runtime"]["emulator_grpc_port"])
    if cleanup.get("reset_after", {}).get("passed") is not True:
        qualification_passed = False
    if cleanup.get("env_close") != "closed":
        qualification_passed = False
    if managed is not None and cleanup["adb_5038_listener_pids_after"] != [managed.owner_pid]:
        qualification_passed = False
    if cleanup["adb_5037_listener_pids_after"]:
        qualification_passed = False
    protected_after = {path: sha256_path(REPOSITORY_ROOT / path) for path in PROTECTED_WIP}
    if protected_after != PROTECTED_WIP:
        qualification_passed = False
    completion = {
        "schema_version": "role_binding_timing.phase_b2_8.diagnosis_completion.v0.2.8",
        "status": "PASS_SETTINGS_DIAGNOSTIC" if qualification_passed and primary_error is None else "FAIL_SETTINGS_DIAGNOSTIC",
        "route_label": ROUTE_LABEL,
        "development_contaminated": True,
        "held_out_eligible": False,
        "generation_calls": 0,
        "generation_eligible": False,
        "explicit_get_state_calls": state_calls,
        "started_at": utc_now(),
        "wall_time_seconds": time.monotonic() - started,
        "freeze_commit": args.freeze_commit,
        "freeze_tag": FREEZE_TAG,
        "protected_wip_before": protected_before,
        "protected_wip_after": protected_after,
        "setup": setup,
        "readiness_sample_count": len(readiness_samples),
        "readiness_pass_sequence": [item["passed"] for item in readiness_samples],
        "identity_before_qualified": identity_before.get("qualified") if identity_before else None,
        "identity_after_qualified": identity_after.get("qualified") if identity_after else None,
        "observation_record_written": (output_root / "observation/observation_record.json").exists(),
        "primary_error": primary_error,
        "cleanup": cleanup,
        "claim_evidence": {
            "androidenv_sidecar_settings_route_qualified": qualification_passed and primary_error is None,
            "xml_equivalence_tested": False,
            "held_out_capture_tested": False,
            "oracle_efficacy_tested": False,
            "role_binding_hypothesis_tested": False,
            "memory_or_controller_efficacy_tested": False,
        },
    }
    write_json_atomic(output_root / "diagnosis_completion.json", completion)
    print(json.dumps({"status": completion["status"], "output_root": str(output_root), "state_calls": state_calls}, sort_keys=True))
    return 0 if completion["status"] == "PASS_SETTINGS_DIAGNOSTIC" else 2


if __name__ == "__main__":
    raise SystemExit(main())
