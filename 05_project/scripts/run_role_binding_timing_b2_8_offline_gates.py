"""Capture auditable stdout/stderr for the B2.8 pre-live offline gates."""

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
OUTPUT_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/phase_b2_8_androidenv_sidecar_offline_gates_v2"
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
        result = subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=False,
            check=False,
            timeout=timeout,
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
    stdout_path = root / "stdout.bin"
    stderr_path = root / "stderr.bin"
    stdout_path.write_bytes(stdout)
    stderr_path.write_bytes(stderr)
    return {
        "gate_id": gate_id,
        "command": command,
        "cwd": cwd.relative_to(REPOSITORY_ROOT).as_posix(),
        "returncode": returncode,
        "timed_out": timed_out,
        "wall_time_seconds": time.monotonic() - started,
        "stdout": {"path": stdout_path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": len(stdout), "sha256": digest(stdout)},
        "stderr": {"path": stderr_path.relative_to(REPOSITORY_ROOT).as_posix(), "bytes": len(stderr), "sha256": digest(stderr)},
        "stdout_text": stdout.decode("utf-8", errors="replace"),
    }


def main() -> int:
    if OUTPUT_ROOT.exists():
        raise RuntimeError("OFFLINE_GATE_OUTPUT_NOT_FRESH")
    OUTPUT_ROOT.mkdir(parents=True)
    commands = [
        (
            "focused",
            [str(PYTHON), "-m", "pytest", "tests/role_binding_timing/test_androidenv_sidecar_v0_2_8.py", "-q", "--color=no"],
            PROJECT_ROOT,
            180.0,
        ),
        (
            "namespace",
            [str(PYTHON), "-m", "pytest", "tests/role_binding_timing", "-q", "--color=no"],
            PROJECT_ROOT,
            300.0,
        ),
        (
            "full_regression",
            [str(PYTHON), "-m", "pytest", "tests", "-q", "--color=no"],
            PROJECT_ROOT,
            900.0,
        ),
    ]
    gates = [
        run_gate(gate_id, command, cwd=cwd, timeout=timeout)
        for gate_id, command, cwd, timeout in commands
    ]
    focused_pass = gates[0]["returncode"] == 0 and not gates[0]["timed_out"]
    namespace_pass = gates[1]["returncode"] == 0 and not gates[1]["timed_out"]
    failed_nodes = [
        item.replace("\\", "/")
        for item in re.findall(r"^FAILED\s+([^\s]+)", gates[2]["stdout_text"], flags=re.MULTILINE)
    ]
    full_accepted = (
        gates[2]["returncode"] == 1
        and not gates[2]["timed_out"]
        and failed_nodes == [EXPECTED_FULL_FAILURE]
    )
    protected = {relative: file_digest(REPOSITORY_ROOT / relative) for relative in PROTECTED}
    protected_pass = protected == PROTECTED
    result = {
        "schema_version": "role_binding_timing.phase_b2_8.offline_gates.v0.2.8",
        "superseded_pre_freeze_gate": {
            "path": "05_project/artifacts/role_binding_timing/phase_b2_8_androidenv_sidecar_offline_gates/offline_gate_result.json",
            "reason": "runner_cwd_was_repository_root_but_legacy_eest_replay_resolves_schemas_relative_to_05_project"
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generation_calls": 0,
        "held_out_captures": 0,
        "androidenv_get_state_calls": 0,
        "focused_pass": focused_pass,
        "namespace_pass": namespace_pass,
        "full_regression_accepted": full_accepted,
        "full_regression_expected_only_failure": EXPECTED_FULL_FAILURE,
        "full_regression_observed_failed_nodes": failed_nodes,
        "protected_wip_hashes": protected,
        "protected_wip_pass": protected_pass,
        "overall_pass": focused_pass and namespace_pass and full_accepted and protected_pass,
        "gates": [{key: value for key, value in gate.items() if key != "stdout_text"} for gate in gates],
    }
    result_path = OUTPUT_ROOT / "offline_gate_result.json"
    temporary = result_path.with_suffix(".json.partial")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, result_path)
    print(json.dumps({"overall_pass": result["overall_pass"], "failed_nodes": failed_nodes}, sort_keys=True))
    return 0 if result["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
