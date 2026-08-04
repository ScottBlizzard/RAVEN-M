"""Bounded zero-generation-call stress audit for the frozen ADB 5038 route."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.eest_ac.runtime_v0_2_2 import assert_frozen_adb_server_port  # noqa: E402


EXPECTED_ADB_SHA256 = "957e46b8615f7af5b7292a2ddabe98d2e61940c3fb2b0545756507f080613e71"
EXPECTED_SERIAL = "emulator-5554"
EXPECTED_PORT = 5038
ROUNDS = 25


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _server_identity(port: int) -> dict[str, Any]:
    command = (
        f"$c=Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction Stop;"
        "$p=Get-Process -Id $c.OwningProcess -ErrorAction Stop;"
        "[pscustomobject]@{pid=$p.Id;path=$p.Path}|ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    value = json.loads(result.stdout.strip().splitlines()[-1])
    binary = Path(value["path"]).resolve()
    return {"port": port, "pid": value["pid"], "binary": str(binary), "binary_sha256": _hash(binary)}


def _call(adb: Path, port: int, args: list[str]) -> dict[str, Any]:
    command = [str(adb), "-P", str(port), "-s", EXPECTED_SERIAL, *args]
    started = time.monotonic()
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=10)
    elapsed = time.monotonic() - started
    return {
        "command": command[1:],
        "explicit_port": port,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "wall_time_seconds": elapsed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--adb-path", type=Path, required=True)
    parser.add_argument("--adb-server-port", type=int, required=True)
    args = parser.parse_args()
    assert_frozen_adb_server_port(configured=EXPECTED_PORT, supplied=args.adb_server_port)
    fallback_rejected = False
    try:
        assert_frozen_adb_server_port(configured=EXPECTED_PORT, supplied=5037)
    except RuntimeError as exc:
        fallback_rejected = "fallback=forbidden" in str(exc)
    adb = args.adb_path.resolve()
    client_hash = _hash(adb)
    before_server = _server_identity(args.adb_server_port)
    records = []
    command_specs = [
        (["get-serialno"], EXPECTED_SERIAL),
        (["get-state"], "device"),
        (["shell", "getprop", "sys.boot_completed"], "1"),
        (["shell", "echo", "eest_ac_v0_2_2_5038"], "eest_ac_v0_2_2_5038"),
    ]
    for round_index in range(ROUNDS):
        for spec, expected in command_specs:
            record = _call(adb, args.adb_server_port, spec)
            record.update({"round": round_index + 1, "expected_stdout": expected})
            record["passed"] = record["returncode"] == 0 and record["stdout"] == expected
            records.append(record)
            if not record["passed"]:
                break
        if records and not records[-1]["passed"]:
            break
    after_server = _server_identity(args.adb_server_port)
    passed = bool(
        len(records) == ROUNDS * len(command_specs)
        and all(item["passed"] for item in records)
        and all(item["explicit_port"] == EXPECTED_PORT for item in records)
        and fallback_rejected
        and client_hash == EXPECTED_ADB_SHA256
        and before_server["binary_sha256"] == client_hash
        and after_server["binary_sha256"] == client_hash
        and before_server["pid"] == after_server["pid"]
    )
    result = {
        "schema_version": "eest_ac_adb_explicit_port_stress.v0_2_2",
        "status": "pass" if passed else "fail",
        "created_at_utc": _utc_now(),
        "zero_model_generation_calls": 0,
        "rounds_planned": ROUNDS,
        "commands_planned": ROUNDS * len(command_specs),
        "commands_completed": len(records),
        "fallback_to_5037_rejected": fallback_rejected,
        "client": {"binary": str(adb), "binary_sha256": client_hash},
        "server_before": before_server,
        "server_after": after_server,
        "device_serial": EXPECTED_SERIAL,
        "records": records,
    }
    _write(args.output, result)
    print(json.dumps({
        "status": result["status"],
        "commands_completed": len(records),
        "maximum_command_seconds": max((item["wall_time_seconds"] for item in records), default=None),
        "output": str(args.output),
    }, indent=2))
    if not passed:
        raise RuntimeError("Frozen ADB 5038 stress audit failed.")


if __name__ == "__main__":
    main()
