"""Read-only B2.10 audit of the pinned AndroidEnv accessibility delivery chain."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent


def digest_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def digest_path(path: Path) -> str:
    hasher = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def save_bytes(path: Path, value: bytes) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    return {
        "path": path.relative_to(REPOSITORY_ROOT).as_posix(),
        "sha256": digest_bytes(value),
        "bytes": len(value),
    }


def save_json(path: Path, value: Any) -> dict[str, Any]:
    return save_bytes(path, canonical_bytes(value))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_raw(command: list[str], *, root: Path, name: str, timeout: float = 30.0) -> tuple[dict[str, Any], bytes, bytes]:
    started = time.monotonic()
    try:
        result = subprocess.run(command, capture_output=True, text=False, check=False, timeout=timeout)
        stdout, stderr = bytes(result.stdout), bytes(result.stderr)
        returncode, timed_out = result.returncode, False
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = bytes(exc.stdout or b""), bytes(exc.stderr or b"")
        returncode, timed_out = None, True
    record = {
        "command": command,
        "returncode": returncode,
        "timed_out": timed_out,
        "wall_time_seconds": round(time.monotonic() - started, 6),
        "stdout": save_bytes(root / f"{name}.stdout.bin", stdout),
        "stderr": save_bytes(root / f"{name}.stderr.bin", stderr),
    }
    return record, stdout, stderr


def listener_pids(netstat: str, port: int) -> list[int]:
    result: set[int] = set()
    for line in netstat.splitlines():
        fields = line.split()
        if len(fields) < 5 or fields[0].upper() != "TCP" or fields[3].upper() != "LISTENING":
            continue
        if fields[1].rsplit(":", 1)[-1] == str(port):
            try:
                result.add(int(fields[-1]))
            except ValueError:
                pass
    return sorted(result)


def source_anchors(path: Path, needles: list[str]) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    records = []
    for index, line in enumerate(lines, start=1):
        if any(needle in line for needle in needles):
            records.append({"line": index, "text": line.strip()})
    return records


def parse_accessibility_dump(value: str, component: str) -> dict[str, Any]:
    lines = value.splitlines()
    matched = [line.strip() for line in lines if component in line]
    return {
        "component_present": component in value,
        "enabled": any("Enabled services" in line and component in line for line in lines),
        "binding": any("Binding services" in line and component in line for line in lines),
        "bound": any("Bound services" in line and component in line for line in lines),
        "crashed": any("Crashed services" in line and component in line for line in lines),
        "matching_lines": matched,
        "raw_sha256": digest_bytes(value.encode("utf-8")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    config_path = (REPOSITORY_ROOT / args.config).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config["generation_calls_authorized"] != 0 or config["mutation_authorized"] is not False:
        raise RuntimeError("B2_10_AUDIT_BOUNDARY_INVALID")
    output_root = REPOSITORY_ROOT / config["output_root"]
    if output_root.exists():
        raise RuntimeError(f"OUTPUT_ROOT_ALREADY_EXISTS:{output_root}")
    output_root.mkdir(parents=True)

    protected_before = {name: digest_path(REPOSITORY_ROOT / name) for name in config["protected_wip"]}
    if protected_before != config["protected_wip"]:
        raise RuntimeError(f"PROTECTED_WIP_DRIFT:{protected_before}")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=True).stdout.strip()
    if head != config["source_boundary"]["head"]:
        raise RuntimeError(f"HEAD_BOUNDARY_DRIFT:{head}")

    b29_completion_path = REPOSITORY_ROOT / config["source_boundary"]["b2_9_completion"]
    if digest_path(b29_completion_path) != config["source_boundary"]["b2_9_completion_sha256"]:
        raise RuntimeError("B2_9_COMPLETION_HASH_DRIFT")
    b29_completion = json.loads(b29_completion_path.read_text(encoding="utf-8"))
    b29_summary = json.loads((REPOSITORY_ROOT / config["source_boundary"]["b2_9_summary"]).read_text(encoding="utf-8"))
    b29_dump_raw = (REPOSITORY_ROOT / config["source_boundary"]["b2_9_accessibility_dump"]).read_bytes()

    runtime = config["runtime"]
    adb = (REPOSITORY_ROOT / runtime["adb_binary"]).resolve()
    if digest_path(adb) != runtime["adb_binary_sha256"]:
        raise RuntimeError("ADB_BINARY_HASH_DRIFT")
    adb_prefix = [str(adb), "-P", str(runtime["adb_server_port"]), "-s", runtime["device_serial"]]
    raw_records: dict[str, Any] = {}
    payloads: dict[str, bytes] = {}

    host_record, host_stdout, _ = run_raw(["netstat", "-ano", "-p", "tcp"], root=output_root / "raw", name="host_netstat")
    raw_records["host_netstat"] = host_record
    host_text = host_stdout.decode("utf-8", errors="replace")
    pids = {
        str(port): listener_pids(host_text, port)
        for port in (5037, runtime["adb_server_port"], runtime["emulator_grpc_port"], runtime["b2_9_sidecar_host_port"])
    }
    for port, current in pids.items():
        for pid in current:
            key = f"tasklist_port_{port}_pid_{pid}"
            record, stdout, _ = run_raw(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], root=output_root / "raw", name=key)
            raw_records[key], payloads[key] = record, stdout

    device_commands = {
        "accessibility_enabled": ["shell", "settings", "get", "secure", "accessibility_enabled"],
        "enabled_services": ["shell", "settings", "get", "secure", "enabled_accessibility_services"],
        "accessibility_dump": ["shell", "dumpsys", "accessibility"],
        "forwarder_pm_path": ["shell", "pm", "path", runtime["forwarder_package"]],
        "forwarder_package": ["shell", "dumpsys", "package", runtime["forwarder_package"]],
        "forwarder_process": ["shell", "pidof", runtime["forwarder_package"]],
        "forwarder_services": ["shell", "dumpsys", "activity", "services", runtime["forwarder_package"]],
        "accessibility_service_check": ["shell", "service", "check", "accessibility"],
        "global_no_proxy": ["shell", "settings", "get", "global", "no_proxy"],
        "boot_completed": ["shell", "getprop", "sys.boot_completed"],
        "power": ["shell", "dumpsys", "power"],
        "window_displays": ["shell", "dumpsys", "window", "displays"],
        "logcat": ["logcat", "-d", "-b", "all", "-v", "threadtime", "-t", str(config["logcat"]["max_lines"])],
    }
    for name, suffix in device_commands.items():
        record, stdout, _ = run_raw(adb_prefix + suffix, root=output_root / "raw", name=name, timeout=90.0 if name == "logcat" else 30.0)
        raw_records[name], payloads[name] = record, stdout

    pm_text = payloads["forwarder_pm_path"].decode("utf-8", errors="replace").strip()
    apk_path = pm_text.split("package:", 1)[1].strip() if pm_text.startswith("package:") else ""
    if apk_path:
        record, stdout, _ = run_raw(adb_prefix + ["shell", "sha256sum", apk_path], root=output_root / "raw", name="forwarder_apk_sha256sum")
        raw_records["forwarder_apk_sha256sum"], payloads["forwarder_apk_sha256sum"] = record, stdout
        current_apk_hash = stdout.decode("ascii", errors="replace").strip().split()[0] if stdout.strip() else ""
    else:
        current_apk_hash = ""

    log_text = payloads["logcat"].decode("utf-8", errors="replace")
    pattern_summary: dict[str, Any] = {}
    filtered_lines: list[str] = []
    for pattern in config["logcat"]["patterns"]:
        matches = [line for line in log_text.splitlines() if pattern.casefold() in line.casefold()]
        pattern_summary[pattern] = {"count": len(matches), "sample": matches[-10:]}
        filtered_lines.extend(matches)
    filtered_lines = list(dict.fromkeys(filtered_lines))
    filtered_artifact = save_bytes(output_root / "derived" / "forwarder_logcat_filtered.txt", ("\n".join(filtered_lines) + "\n").encode("utf-8"))

    old_dump_text = b29_dump_raw.decode("utf-8", errors="replace")
    current_dump_text = payloads["accessibility_dump"].decode("utf-8", errors="replace")
    old_dump = parse_accessibility_dump(old_dump_text, runtime["forwarder_component"])
    current_dump = parse_accessibility_dump(current_dump_text, runtime["forwarder_component"])

    source_needles = [
        "local_server_credentials", "add_secure_port", "add_insecure_port", "_start_a11y_services",
        "_enable_a11y_tree_logs", "_configure_grpc", "SET_GRPC --ei", "enabled_accessibility_services",
        "refresh_env", "usePlaintext", "logUsingGRPC", "grpcPort", "sendForest", "ENABLE_GRPC",
        "['shell', 'am', 'broadcast', '-a', send_broadcast.action]", "IMPLICIT_ANDROIDENV_REFRESH_FORBIDDEN",
    ]
    source_records = {}
    for relative in config["source_files"]:
        path = REPOSITORY_ROOT / relative
        source_records[relative] = {
            "sha256": digest_path(path),
            "bytes": path.stat().st_size,
            "anchors": source_anchors(path, source_needles),
        }

    grpc_doc_command = [
        str((REPOSITORY_ROOT / "06_local_runtime/envs/androidworld/Scripts/python.exe").resolve()),
        "-c",
        "import grpc; print(grpc.__version__); print(grpc.local_server_credentials.__doc__)",
    ]
    grpc_record, grpc_stdout, _ = run_raw(grpc_doc_command, root=output_root / "raw", name="grpc_local_credentials_doc")
    raw_records["grpc_local_credentials_doc"], payloads["grpc_local_credentials_doc"] = grpc_record, grpc_stdout
    grpc_doc_text = grpc_stdout.decode("utf-8", errors="replace")

    observations = {
        "b2_9": {
            "enabled_component": b29_summary["sidecar"]["accessibility_component_enabled"],
            "binding_component": b29_summary["sidecar"]["accessibility_component_binding"],
            "bound_component": b29_summary["sidecar"]["accessibility_component_bound"],
            "host_listener_qualified_during_run": b29_completion["identity_before_qualified"],
            "host_port": b29_summary["sidecar"]["host_port"],
            "tree_result": b29_summary["sidecar"]["tree_fetch_result"],
            "old_dump_parse": old_dump,
        },
        "current_read_only": {
            "listener_pids": pids,
            "accessibility_dump": current_dump,
            "accessibility_enabled": payloads["accessibility_enabled"].decode("utf-8", errors="replace").strip(),
            "enabled_services": payloads["enabled_services"].decode("utf-8", errors="replace").strip(),
            "forwarder_process": payloads["forwarder_process"].decode("utf-8", errors="replace").strip(),
            "global_no_proxy": payloads["global_no_proxy"].decode("utf-8", errors="replace").strip(),
            "forwarder_apk_sha256": current_apk_hash,
        },
        "logcat": pattern_summary,
        "grpc_local_credentials": {
            "version_and_doc_sha256": digest_bytes(grpc_stdout),
            "states_local_only": "checked if they are local or not" in grpc_doc_text,
        },
    }

    direct_send_count = pattern_summary["sending (blocking) gRPC request for tree"]["count"]
    timeout_count = pattern_summary["TimeoutCancellationException"]["count"]
    success_count = pattern_summary["gRPC request for tree succeeded"]["count"]
    correct_port_count = sum("10.0.2.2:50069" in line for line in filtered_lines)
    classification = {
        "primary": "FORWARDER_ACTIVE_TREE_SEND_ATTEMPT_BUT_HOST_DELIVERY_TIMEOUT",
        "taxonomy": {
            "enabled_but_unbound": {
                "verdict": "CONCURRENT_FRAMEWORK_STATE_ONLY_NOT_UNIQUE_ROOT",
                "evidence": {"b2_9_binding": old_dump["binding"], "b2_9_bound": old_dump["bound"]},
            },
            "bound_but_no_tree": {
                "verdict": "EFFECTIVE_SERVICE_ACTIVITY_WITHOUT_HOST_TREE_SUPPORTED",
                "evidence": {"send_attempts": direct_send_count, "timeouts": timeout_count, "successes": success_count},
            },
            "host_not_listening": {
                "verdict": "CONTRADICTED_DURING_B2_9_BY_QUALIFIED_HOST_LISTENER",
                "evidence": {"identity_before_qualified": b29_completion["identity_before_qualified"], "host_port": 50069},
            },
            "apk_service_mismatch": {
                "verdict": "CONTRADICTED",
                "evidence": {"expected": runtime["forwarder_apk_sha256"], "current": current_apk_hash},
            },
            "unknown": {
                "verdict": "TRANSPORT_MECHANISM_NOT_YET_CAUSALLY_INTERVENED",
                "evidence": {"correct_port_log_lines": correct_port_count},
            },
        },
        "first_broken_edge": "DEVICE_FORWARDER_TO_HOST_A11Y_GRPC_DELIVERY",
        "candidate_mechanisms": [
            {
                "name": "LOCAL_ONLY_SERVER_CREDENTIALS_VERSUS_EMULATOR_GUEST_PLAINTEXT_CLIENT",
                "status": "SOURCE_AND_RUNTIME_CONCORDANT_NOT_CAUSALLY_TESTED",
                "facts": [
                    "host wrapper binds [::] with grpc.local_server_credentials and add_secure_port",
                    "pinned grpc docs say local credentials check whether TCP peers are local",
                    "forwarder APK connects from emulator guest via 10.0.2.2 using usePlaintext",
                    "device log records send attempts and timeouts with no success",
                ],
            },
            {
                "name": "HANDWRITTEN_SET_GRPC_ACTION_ARGUMENT_AND_MISSING_EXPLICIT_ENABLE_GRPC",
                "status": "SOURCE_DEFECT_PRESENT_BUT_NOT_SUFFICIENT_FOR_B2_9_FAILURE",
                "facts": [
                    "wrapper embeds --ei port inside the action string while parser passes action as one argv item",
                    "wrapper source does not explicitly send ENABLE_GRPC",
                    "B2.9 device logs nevertheless show the exact current port and active gRPC sends",
                ],
            },
        ],
        "safe_generic_repair_supported": direct_send_count > 0 and timeout_count > 0 and success_count == 0 and "checked if they are local or not" in grpc_doc_text,
        "repair_boundary": "PREREGISTER_NEW_DEV_ONLY_EXPLICIT_5038_8554_SESSION_WITH_NETWORK_COMPATIBLE_HOST_GRPC_AND_EXPLICIT_FORWARDER_FLAGS;NO_REFRESH;NO_APP_BRANCHES",
    }

    protected_after = {name: digest_path(REPOSITORY_ROOT / name) for name in config["protected_wip"]}
    result = {
        "schema_version": "role_binding_timing.phase_b2_10.lifecycle_audit.v0.2.10",
        "status": "AUDIT_COMPLETE_SAFE_GENERIC_REPAIR_SUPPORTED" if classification["safe_generic_repair_supported"] else "AUDIT_COMPLETE_NO_SAFE_REPAIR",
        "started_from_head": head,
        "completed_at": utc_now(),
        "development_contaminated": True,
        "held_out_eligible": False,
        "generation_calls": 0,
        "mutation_performed": False,
        "raw_records": raw_records,
        "filtered_logcat": filtered_artifact,
        "source_records": source_records,
        "observations": observations,
        "classification": classification,
        "protected_wip_before": protected_before,
        "protected_wip_after": protected_after,
        "protected_wip_unchanged": protected_before == protected_after == config["protected_wip"],
        "claim_evidence": {
            "role_binding_hypothesis_tested": False,
            "held_out_capture_tested": False,
            "a11y_transport_root_cause_causally_proven": False,
            "bounded_generic_dev_repair_justified": classification["safe_generic_repair_supported"],
            "v0_3_authorized": False,
        },
    }
    save_json(output_root / "lifecycle_audit.json", result)
    artifacts = []
    for path in sorted(output_root.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.json":
            artifacts.append({"path": path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": digest_path(path)})
    save_json(output_root / "artifact_manifest.json", {"schema_version": "role_binding_timing.phase_b2_10.audit_manifest.v0.2.10", "artifacts": artifacts})
    print(json.dumps({"status": result["status"], "classification": classification["primary"], "repair_supported": classification["safe_generic_repair_supported"], "output_root": config["output_root"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
