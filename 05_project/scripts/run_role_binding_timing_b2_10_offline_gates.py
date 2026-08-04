"""Capture the B2.10 pre-mutation offline gates with byte-exact outputs."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
OUTPUT_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/phase_b2_10_accessibility_forwarder_lifecycle_offline_gates_v2"
PYTHON = REPOSITORY_ROOT / "06_local_runtime/envs/androidworld/Scripts/python.exe"
EXPECTED_FULL_FAILURE = (
    "tests/scripts/test_protocol_v2_2_r78_h17_candidate.py::"
    "test_r78_candidate_static_manifest_validation_passes"
)
PROTECTED = {
    "05_project/src/raven_m/controller/episode_controller.py": "fc0e82e0fde90119365d4f685f080eb4519bf2f602e4bda58de5d4809a40fe33",
    "05_project/src/raven_m/controller/protocol_v2_guard.py": "ff89d6b70be4b4738646d262beb67d7b7e932e9eb95956d940b1c5000a999d10",
    "05_project/tests/scripts/test_protocol_v2_2_r79_r78_trace_replay.py": "5bb1f1e3de673a1072cfee62938b761a62fd69c187d5eadf54bc46b115a3fd0a",
}


def digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def file_digest(path: Path) -> str:
    return digest(path.read_bytes())


def run_gate(gate_id: str, command: list[str], *, cwd: Path, timeout: float) -> dict[str, Any]:
    root = OUTPUT_ROOT / gate_id
    root.mkdir(parents=True, exist_ok=False)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, text=False, check=False, timeout=timeout)
        stdout, stderr = bytes(result.stdout), bytes(result.stderr)
        returncode, timed_out = result.returncode, False
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = bytes(exc.stdout or b""), bytes(exc.stderr or b"")
        returncode, timed_out = None, True
    stdout_path, stderr_path = root / "stdout.bin", root / "stderr.bin"
    stdout_path.write_bytes(stdout)
    stderr_path.write_bytes(stderr)
    return {
        "gate_id": gate_id, "command": command,
        "cwd": cwd.relative_to(REPOSITORY_ROOT).as_posix(),
        "returncode": returncode, "timed_out": timed_out,
        "wall_time_seconds": time.monotonic() - started,
        "stdout": {"path": stdout_path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": len(stdout), "sha256": digest(stdout)},
        "stderr": {"path": stderr_path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": len(stderr), "sha256": digest(stderr)},
        "stdout_text": stdout.decode("utf-8", errors="replace"),
    }


def listener_pids(netstat: str, port: int) -> list[int]:
    result = []
    for line in netstat.splitlines():
        fields = line.split()
        if len(fields) >= 5 and fields[0].upper() == "TCP" and fields[3].upper() == "LISTENING" and fields[1].rsplit(":", 1)[-1] == str(port):
            pid = int(fields[-1])
            if pid not in result:
                result.append(pid)
    return result


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise RuntimeError("OFFLINE_GATE_OUTPUT_NOT_FRESH")
    OUTPUT_ROOT.mkdir(parents=True)
    (OUTPUT_ROOT / ".gitattributes").write_text("**/*.bin -text\n", encoding="ascii")
    gates = [
        run_gate(
            "focused",
            [str(PYTHON), "-m", "pytest", "tests/role_binding_timing/test_androidenv_sidecar_runtime_v0_2_10.py", "-q", "--color=no"],
            cwd=PROJECT_ROOT, timeout=180.0,
        ),
        run_gate(
            "namespace",
            [str(PYTHON), "-m", "pytest", "tests/role_binding_timing", "-q", "--color=no"],
            cwd=PROJECT_ROOT, timeout=420.0,
        ),
        run_gate(
            "full_regression",
            [str(PYTHON), "-m", "pytest", "tests", "-q", "--color=no"],
            cwd=PROJECT_ROOT, timeout=1200.0,
        ),
    ]
    focused_pass = gates[0]["returncode"] == 0 and not gates[0]["timed_out"]
    namespace_pass = gates[1]["returncode"] == 0 and not gates[1]["timed_out"]
    failed_nodes = [
        item.replace("\\", "/")
        for item in re.findall(r"^FAILED\s+([^\s]+)", gates[2]["stdout_text"], flags=re.MULTILINE)
    ]
    full_accepted = gates[2]["returncode"] == 1 and not gates[2]["timed_out"] and failed_nodes == [EXPECTED_FULL_FAILURE]

    module_path = PROJECT_ROOT / "src/raven_m/role_binding_timing/androidenv_sidecar_runtime_v0_2_10.py"
    module_text = module_path.read_text(encoding="utf-8")
    forbidden_literals = ["com.android.settings", "com.google.android.deskclock", "org.tasks", "broccoli", "H17", "r79"]
    source_isolation = {
        "forbidden_hits": [item for item in forbidden_literals if item in module_text],
        "required_hits": {
            item: item in module_text
            for item in ("add_insecure_port", "IMPLICIT_ANDROIDENV_REFRESH_FORBIDDEN", "ADB_PORT_NOT_FROZEN_5038", "explicit_forwarder_broadcast_args")
        },
    }
    source_isolation["passed"] = not source_isolation["forbidden_hits"] and all(source_isolation["required_hits"].values())

    netstat = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, check=False, timeout=20).stdout
    runtime_preflight = {
        "adb_5037_listener_pids": listener_pids(netstat, 5037),
        "adb_5038_listener_pids": listener_pids(netstat, 5038),
        "emulator_grpc_8554_listener_pids": listener_pids(netstat, 8554),
        "generation_calls": 0,
        "androidenv_sessions_created": 0,
        "device_mutations": 0,
    }
    runtime_preflight["passed"] = (
        not runtime_preflight["adb_5037_listener_pids"]
        and len(runtime_preflight["adb_5038_listener_pids"]) == 1
        and len(runtime_preflight["emulator_grpc_8554_listener_pids"]) == 1
    )
    protected = {relative: file_digest(REPOSITORY_ROOT / relative) for relative in PROTECTED}
    protected_pass = protected == PROTECTED
    result = {
        "schema_version": "role_binding_timing.phase_b2_10.offline_gates.v0.2.10",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generation_calls": 0,
        "held_out_captures": 0,
        "androidenv_sessions_created": 0,
        "device_mutations": 0,
        "focused_pass": focused_pass,
        "namespace_pass": namespace_pass,
        "full_regression_accepted": full_accepted,
        "full_regression_expected_only_failure": EXPECTED_FULL_FAILURE,
        "full_regression_observed_failed_nodes": failed_nodes,
        "source_isolation": source_isolation,
        "runtime_preflight": runtime_preflight,
        "protected_wip_hashes": protected,
        "protected_wip_pass": protected_pass,
        "gates": [{key: value for key, value in gate.items() if key != "stdout_text"} for gate in gates],
    }
    result["overall_pass"] = all((focused_pass, namespace_pass, full_accepted, source_isolation["passed"], runtime_preflight["passed"], protected_pass))
    temporary = OUTPUT_ROOT / "offline_gate_result.json.partial"
    final = OUTPUT_ROOT / "offline_gate_result.json"
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, final)
    print(json.dumps({"overall_pass": result["overall_pass"], "failed_nodes": failed_nodes, "runtime_preflight": runtime_preflight}, sort_keys=True))
    return 0 if result["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
