"""Structural process identity, continuous history, and failure snapshots for INFRA-M5."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time
from typing import Any, Callable, Iterable

import psutil

from raven_m.role_binding_timing.infra_m1_runtime import listener_pids
from raven_m.role_binding_timing.infra_m4_terminal_accounting import (
    atomic_write_bytes,
    atomic_write_json,
    safe_jsonable,
    utc_now,
)


RELEVANT_NAMES = {
    "adb.exe",
    "emulator.exe",
    "qemu-system-x86_64-headless.exe",
    "crashpad_handler.exe",
    "netsimd.exe",
}
CORE_ROLES = ("adb_server", "emulator_launcher", "qemu")


def normalized_path(value: str | None) -> str:
    if not value:
        return ""
    return str(Path(value).resolve()).replace("/", "\\").casefold()


def normalized_command(value: str | Iterable[str] | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        raw = value
    else:
        raw = " ".join(str(item) for item in value)
    return " ".join(raw.replace("/", "\\").split()).casefold()


def identity_key(record: dict[str, Any]) -> str | None:
    pid = record.get("pid")
    created = record.get("create_time")
    if not isinstance(pid, int) or not isinstance(created, (int, float)):
        return None
    return f"{pid}@{float(created):.6f}"


def digest_path(path: str | Path) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def process_record(process: psutil.Process) -> dict[str, Any]:
    try:
        with process.oneshot():
            pid = process.pid
            ppid = process.ppid()
            name = process.name()
            exe = process.exe()
            cmdline_items = process.cmdline()
            create_time = process.create_time()
        return {
            "pid": int(pid),
            "ppid": int(ppid),
            "name": name,
            "exe": exe,
            "cmdline_items": cmdline_items,
            "command_line": " ".join(cmdline_items),
            "create_time": float(create_time),
            "identity_key": f"{int(pid)}@{float(create_time):.6f}",
            "access_error": None,
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as exc:
        try:
            pid = process.pid
        except Exception:
            pid = None
        return {
            "pid": pid,
            "ppid": None,
            "name": None,
            "exe": None,
            "cmdline_items": None,
            "command_line": None,
            "create_time": None,
            "identity_key": None,
            "access_error": f"{type(exc).__name__}:{exc}",
        }


def snapshot_processes() -> list[dict[str, Any]]:
    return [process_record(process) for process in psutil.process_iter()]


def netstat_bytes() -> bytes:
    completed = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"], capture_output=True,
        check=True, timeout=20,
    )
    return bytes(completed.stdout)


def process_index(records: Iterable[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {
        int(record["pid"]): record for record in records
        if isinstance(record.get("pid"), int)
    }


def ancestry_records(
    record: dict[str, Any], by_pid: dict[int, dict[str, Any]], *, limit: int = 12,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[int] = set()
    parent = record.get("ppid")
    for _ in range(limit):
        if not isinstance(parent, int) or parent <= 0 or parent in seen:
            break
        seen.add(parent)
        parent_record = by_pid.get(parent)
        if parent_record is None:
            result.append({"pid": parent, "missing": true_value()})
            break
        result.append(parent_record)
        parent = parent_record.get("ppid")
    return result


def true_value() -> bool:
    """Keep the serialized missing-parent marker explicit and testable."""
    return True


class ExecutableHashCache:
    def __init__(self) -> None:
        self._values: dict[tuple[str, int, int], str] = {}
        self._lock = threading.Lock()

    def get(self, path: str | None) -> str | None:
        if not path:
            return None
        try:
            value = Path(path).resolve()
            stat = value.stat()
            key = (str(value).casefold(), stat.st_size, stat.st_mtime_ns)
            with self._lock:
                cached = self._values.get(key)
            if cached:
                return cached
            digest = sha256(value.read_bytes()).hexdigest()
            with self._lock:
                self._values[key] = digest
            return digest
        except (OSError, PermissionError):
            return None


def enrich_structural_records(
    records: list[dict[str, Any]], cache: ExecutableHashCache,
) -> list[dict[str, Any]]:
    by_pid = process_index(records)
    selected: dict[int, dict[str, Any]] = {}
    relevant = [
        record for record in records
        if str(record.get("name") or "").casefold() in RELEVANT_NAMES
    ]
    for record in relevant:
        if isinstance(record.get("pid"), int):
            selected[record["pid"]] = record
        for parent in ancestry_records(record, by_pid):
            if isinstance(parent.get("pid"), int) and not parent.get("missing"):
                selected[parent["pid"]] = parent
    result = []
    for record in sorted(selected.values(), key=lambda item: int(item["pid"])):
        value = dict(record)
        value["exe_sha256"] = cache.get(value.get("exe"))
        result.append(value)
    return result


def build_snapshot(
    *, gate: str, sequence: int, cache: ExecutableHashCache,
    raw_processes: list[dict[str, Any]] | None = None,
    raw_netstat: bytes | None = None,
) -> dict[str, Any]:
    processes = raw_processes if raw_processes is not None else snapshot_processes()
    network = raw_netstat if raw_netstat is not None else netstat_bytes()
    text = network.decode("utf-8", errors="replace")
    listeners = {
        str(port): listener_pids(text, port)
        for port in (5037, 5038, 5554, 5555, 8554)
    }
    structural = enrich_structural_records(processes, cache)
    return {
        "schema_version": "role_binding_timing.infra_m5.process_snapshot.v1",
        "sequence": sequence,
        "captured_at": utc_now(),
        "captured_monotonic": time.monotonic(),
        "gate": gate,
        "listeners": listeners,
        "all_processes": processes,
        "structural_processes": structural,
        "relevant_identity_keys": [
            identity_key(record) for record in structural
            if str(record.get("name") or "").casefold() in RELEVANT_NAMES
        ],
        "raw_netstat_sha256": sha256(network).hexdigest(),
    }


def save_snapshot(root: Path, snapshot: dict[str, Any], raw_netstat: bytes) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=False)
    netstat_record = atomic_write_bytes(root / "netstat.stdout.bin", raw_netstat, replace=False)
    snapshot = dict(snapshot)
    snapshot["raw_netstat"] = netstat_record
    record = atomic_write_json(root / "process_snapshot.json", snapshot, replace=False)
    return {"snapshot": snapshot, "record": record}


def required_fields_present(record: dict[str, Any]) -> bool:
    return all(
        record.get(key) not in (None, "")
        for key in ("pid", "ppid", "name", "exe", "command_line", "create_time", "identity_key", "exe_sha256")
    )


def command_has_parts(command: str, parts: Iterable[str]) -> bool:
    value = normalized_command(command)
    return all(normalized_command(part) in value for part in parts)


def adb_server_command(command: str) -> bool:
    value = normalized_command(command)
    return bool(re.search(r"(?:^|\\)adb(?:\.exe)?\s+-l\s+tcp:5038\s+fork-server\s+server\s+--reply-fd\s+\d+\s*$", value))


def allowed_bootstrap_adb_command(command: str, *, adb_path: str, serial: str) -> bool:
    value = normalized_command(command)
    prefix = re.escape(normalized_path(adb_path))
    serial_re = re.escape(serial.casefold())
    overlay = re.compile(
        rf"^{prefix}\s+-s\s+{serial_re}\s+shell\s+cmd\s+overlay\s+enable-exclusive\s+"
        rf"--user\s+(?:0|current)\s+--category\s+"
        rf"(?:com\.android\.internal\.emulation\.pixel_6|com\.android\.systemui\.emulation\.pixel_6)\s*$"
    )
    multidisplay = re.compile(
        rf"^{prefix}\s+-s\s+{serial_re}\s+shell\s+am\s+broadcast\s+-a\s+"
        rf"com\.android\.emulator\.multidisplay\.start\s+-n\s+"
        rf"com\.android\.emulator\.multidisplay[\\/](?:com\.android\.emulator\.multidisplay)?\.multidisplayservicereceiver\s+"
        rf"(?:\"?--user\s+0\"?)\s*$"
    )
    return bool(overlay.fullmatch(value) or multidisplay.fullmatch(value))


def allowed_runner_adb_command(command: str, *, adb_path: str, serial: str) -> bool:
    value = normalized_command(command)
    prefix = normalized_path(adb_path)
    if not value.startswith(prefix + " "):
        return False
    if " -p 5037" in value or "tcp:5037" in value:
        return False
    return (
        " -p 5038 " in value
        and (f" -s {serial.casefold()} " in value or " start-server" in value or " kill-server" in value)
    )


@dataclass
class Evaluation:
    passed: bool
    issues: list[str]
    roles: dict[str, str]
    helper_ancestry: dict[str, list[str]]


class StructuralIdentityPolicy:
    """Fail-closed process-role evaluator with write-once core identities."""

    def __init__(self, config: dict[str, Any], *, runner_record: dict[str, Any]) -> None:
        self.config = config
        self.runner_record = runner_record
        self.baseline: dict[str, dict[str, Any]] = {}
        self.baseline_by_pid: dict[int, str] = {}
        self.core: dict[str, dict[str, Any]] = {}
        self.history: dict[str, dict[str, Any]] = {}

    def add_history(self, records: Iterable[dict[str, Any]]) -> None:
        for record in records:
            key = identity_key(record)
            if key:
                self.history[key] = dict(record)

    def freeze_baseline(self, snapshot: dict[str, Any]) -> None:
        if self.baseline:
            raise RuntimeError("BASELINE_ALREADY_FROZEN")
        for record in snapshot["structural_processes"]:
            if str(record.get("name") or "").casefold() not in RELEVANT_NAMES:
                continue
            key = identity_key(record)
            if key is None:
                raise RuntimeError(f"BASELINE_IDENTITY_MISSING:{record.get('pid')}")
            self.baseline[key] = dict(record)
            self.baseline_by_pid[int(record["pid"])] = key
        self.add_history(snapshot["structural_processes"])

    def register_core(self, role: str, record: dict[str, Any]) -> None:
        if role not in CORE_ROLES:
            raise ValueError(f"UNKNOWN_CORE_ROLE:{role}")
        if role in self.core:
            raise RuntimeError(f"CORE_ALREADY_REGISTERED:{role}")
        issues = self._core_shape_issues(role, record, parent_check=False)
        if issues:
            raise RuntimeError(f"CORE_REGISTRATION:{role}:{issues}")
        self.core[role] = dict(record)
        self.add_history([record])

    def _expected_binary(self, role: str) -> tuple[str, str]:
        policy = self.config["process_identity"]["binaries"]
        key = {"adb_server": "adb", "emulator_launcher": "emulator_launcher", "qemu": "qemu"}[role]
        return normalized_path(policy[key]["path"]), policy[key]["sha256"]

    def _core_shape_issues(self, role: str, record: dict[str, Any], *, parent_check: bool = True) -> list[str]:
        issues: list[str] = []
        if not required_fields_present(record):
            issues.append("MISSING_IDENTITY_EVIDENCE")
            return issues
        expected_path, expected_hash = self._expected_binary(role)
        if normalized_path(record.get("exe")) != expected_path:
            issues.append("EXECUTABLE_PATH")
        if record.get("exe_sha256") != expected_hash:
            issues.append("EXECUTABLE_HASH")
        command = str(record.get("command_line") or "")
        if role == "adb_server" and not adb_server_command(command):
            issues.append("COMMAND")
        if role in {"emulator_launcher", "qemu"} and not command_has_parts(command, self.config["runtime"]["emulator_args"]):
            issues.append("COMMAND")
        if parent_check and role == "emulator_launcher" and int(record["ppid"]) != int(self.runner_record["pid"]):
            issues.append("PARENT")
        if parent_check and role == "qemu":
            launcher = self.core.get("emulator_launcher")
            if launcher is None or int(record["ppid"]) != int(launcher["pid"]):
                issues.append("PARENT")
        return issues

    def _ancestry_to_core(
        self, record: dict[str, Any], current: dict[int, dict[str, Any]],
    ) -> tuple[bool, list[str]]:
        target_keys = {
            identity_key(self.core[role]) for role in ("emulator_launcher", "qemu")
            if role in self.core
        }
        chain: list[str] = []
        parent_pid = record.get("ppid")
        seen: set[int] = set()
        for _ in range(self.config["process_identity"]["max_parent_depth"]):
            if not isinstance(parent_pid, int) or parent_pid <= 0 or parent_pid in seen:
                return False, chain
            seen.add(parent_pid)
            candidates = [value for value in current.values() if value.get("pid") == parent_pid]
            candidates.extend(value for value in self.history.values() if value.get("pid") == parent_pid)
            child_time = float(record.get("create_time") or 0)
            candidates = [value for value in candidates if float(value.get("create_time") or 0) <= child_time]
            if not candidates:
                chain.append(f"{parent_pid}@MISSING")
                return False, chain
            parent = max(candidates, key=lambda value: float(value.get("create_time") or 0))
            key = identity_key(parent)
            chain.append(key or f"{parent_pid}@INVALID")
            if key in target_keys:
                return True, chain
            if not self._allowed_wrapper(parent):
                return False, chain
            record = parent
            parent_pid = parent.get("ppid")
        return False, chain

    def _allowed_wrapper(self, record: dict[str, Any]) -> bool:
        if not required_fields_present(record):
            return False
        wrapper = self.config["process_identity"]["binaries"]["command_wrapper"]
        return (
            normalized_path(record.get("exe")) == normalized_path(wrapper["path"])
            and record.get("exe_sha256") == wrapper["sha256"]
            and normalized_path(self.config["process_identity"]["binaries"]["adb"]["path"])
            in normalized_command(record.get("command_line"))
        )

    def _classify_new(
        self, record: dict[str, Any], phase: str, current: dict[int, dict[str, Any]],
    ) -> tuple[str | None, list[str], list[str]]:
        if not required_fields_present(record):
            return None, ["MISSING_IDENTITY_EVIDENCE"], []
        binaries = self.config["process_identity"]["binaries"]
        path = normalized_path(record["exe"])
        digest = record["exe_sha256"]
        command = str(record["command_line"])
        runner_key = identity_key(self.runner_record)
        parent_candidates = [item for item in self.history.values() if item.get("pid") == record.get("ppid")]
        direct_runner = any(identity_key(item) == runner_key for item in parent_candidates) or record.get("ppid") == self.runner_record.get("pid")
        if path == normalized_path(binaries["adb"]["path"]) and digest == binaries["adb"]["sha256"]:
            if direct_runner and allowed_runner_adb_command(command, adb_path=binaries["adb"]["path"], serial=self.config["runtime"]["device_serial"]):
                return "runner_adb_client", [], [runner_key] if runner_key else []
            if allowed_bootstrap_adb_command(command, adb_path=binaries["adb"]["path"], serial=self.config["runtime"]["device_serial"]):
                timing = self._helper_timing_issues(record, "bootstrap_helper_window_seconds")
                if timing:
                    return None, timing, []
                ancestry_ok, chain = self._ancestry_to_core(record, current)
                if not ancestry_ok:
                    return None, ["HELPER_PARENT_CHAIN"], chain
                return "emulator_bootstrap_adb", [], chain
            return None, ["ADB_COMMAND_ROLE"], []
        for role in ("crashpad", "netsimd"):
            spec = binaries[role]
            if path == normalized_path(spec["path"]) and digest == spec["sha256"]:
                timing = self._helper_timing_issues(record, "runtime_helper_window_seconds")
                if timing:
                    return None, timing, []
                ancestry_ok, chain = self._ancestry_to_core(record, current)
                if not ancestry_ok:
                    return None, ["HELPER_PARENT_CHAIN"], chain
                return role, [], chain
        if phase == "cleanup" and path == normalized_path(binaries["emulator_launcher"]["path"]) and digest == binaries["emulator_launcher"]["sha256"]:
            qemu = self.core.get("qemu")
            expected = f"-kill {qemu['pid']} -sleep 20" if qemu else ""
            if expected and expected in normalized_command(command):
                ancestry_ok, chain = self._ancestry_to_core(record, current)
                if ancestry_ok:
                    return "emulator_shutdown_helper", [], chain
                return None, ["HELPER_PARENT_CHAIN"], chain
        return None, ["UNKNOWN_NEW_PROCESS"], []

    def _helper_timing_issues(self, record: dict[str, Any], window_name: str) -> list[str]:
        qemu = self.core.get("qemu")
        if qemu is None:
            return ["HELPER_BEFORE_QEMU_QUALIFICATION"]
        created = record.get("create_time")
        qemu_created = qemu.get("create_time")
        if not isinstance(created, (int, float)) or not isinstance(qemu_created, (int, float)):
            return ["HELPER_TIME_EVIDENCE_MISSING"]
        window = float(self.config["process_identity"][window_name])
        if float(created) < float(qemu_created) or float(created) > float(qemu_created) + window:
            return [f"HELPER_TIME_WINDOW:{window_name}"]
        return []

    def evaluate(
        self, snapshot: dict[str, Any], *, phase: str,
        recent_records: Iterable[dict[str, Any]] = (),
        allow_core_exit: bool = False,
    ) -> Evaluation:
        issues: list[str] = []
        roles: dict[str, str] = {}
        helper_ancestry: dict[str, list[str]] = {}
        listeners = snapshot["listeners"]
        if listeners.get("5037"):
            issues.append(f"FORBIDDEN_5037:{listeners['5037']}")
        current = process_index(snapshot["structural_processes"])
        combined: dict[str, dict[str, Any]] = {}
        for record in [*snapshot["structural_processes"], *recent_records]:
            key = identity_key(record)
            if key and str(record.get("name") or "").casefold() in RELEVANT_NAMES:
                combined[key] = record
        self.add_history(snapshot["structural_processes"])
        self.add_history(recent_records)

        for role, expected in self.core.items():
            pid = int(expected["pid"])
            observed = current.get(pid)
            if observed is None and allow_core_exit:
                continue
            if observed is None:
                issues.append(f"CORE_MISSING:{role}:{pid}")
                continue
            if identity_key(observed) != identity_key(expected):
                issues.append(f"CORE_PID_REUSE:{role}:{pid}")
                continue
            shape = self._core_shape_issues(role, observed)
            issues.extend(f"CORE_{role.upper()}:{item}" for item in shape)
            roles[identity_key(observed) or str(pid)] = role

        if "adb_server" in self.core and not allow_core_exit:
            expected_pid = self.core["adb_server"]["pid"]
            if listeners.get("5038") != [expected_pid]:
                issues.append(f"PORT_OWNER:5038:{listeners.get('5038')}:{expected_pid}")
        if "qemu" in self.core and not allow_core_exit:
            expected_pid = self.core["qemu"]["pid"]
            for port in (5554, 5555, 8554):
                if listeners.get(str(port)) != [expected_pid]:
                    issues.append(f"PORT_OWNER:{port}:{listeners.get(str(port))}:{expected_pid}")

        baseline_keys = set(self.baseline)
        core_keys = {identity_key(record) for record in self.core.values()}
        for key, record in sorted(combined.items()):
            pid = int(record["pid"])
            if key in baseline_keys:
                roles[key] = "preexisting_unrelated_no_authority"
                continue
            baseline_key = self.baseline_by_pid.get(pid)
            if baseline_key and baseline_key != key:
                issues.append(f"PID_REUSE:{pid}:{baseline_key}:{key}")
                continue
            if key in core_keys:
                continue
            role, role_issues, chain = self._classify_new(record, phase, current)
            if role:
                roles[key] = role
                helper_ancestry[key] = chain
            else:
                issues.extend(f"PROCESS:{key}:{item}" for item in role_issues)
                if chain:
                    helper_ancestry[key] = chain
        return Evaluation(not issues, sorted(set(issues)), roles, helper_ancestry)


class ContinuousProcessHistory:
    """Bounded sampler that preserves transient processes and parent records."""

    def __init__(self, root: Path, cache: ExecutableHashCache, *, interval_seconds: float) -> None:
        self.root = root.resolve()
        self.cache = cache
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._records: dict[str, dict[str, Any]] = {}
        self._samples = 0
        self._errors: list[str] = []
        self._ndjson = self.root / "process_history.ndjson"

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("PROCESS_HISTORY_ALREADY_STARTED")
        self.root.mkdir(parents=True, exist_ok=False)
        self._thread = threading.Thread(target=self._run, name="infra-m5-process-history", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                records = snapshot_processes()
                structural = enrich_structural_records(records, self.cache)
                event = {
                    "schema_version": "role_binding_timing.infra_m5.process_history_sample.v1",
                    "captured_at": utc_now(), "sample": self._samples + 1,
                    "structural_processes": structural,
                }
                payload = json.dumps(event, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
                with self._lock:
                    with self._ndjson.open("ab") as handle:
                        handle.write(payload); handle.flush(); os.fsync(handle.fileno())
                    for record in structural:
                        key = identity_key(record)
                        if key:
                            self._records[key] = record
                    self._samples += 1
            except Exception as exc:
                with self._lock:
                    self._errors.append(f"{type(exc).__name__}:{exc}")
            self._stop.wait(self.interval_seconds)

    def records(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(value) for value in self._records.values()]

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {"samples": self._samples, "errors": list(self._errors), "records": len(self._records)}

    def stop(self, *, timeout: float = 10.0) -> dict[str, Any]:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)
            if self._thread.is_alive():
                raise RuntimeError("PROCESS_HISTORY_THREAD_DID_NOT_STOP")
        status = self.status()
        if status["errors"]:
            raise RuntimeError(f"PROCESS_HISTORY_ERRORS:{status['errors']}")
        atomic_write_json(self.root / "history_completion.json", status, replace=False)
        return status


class ProcessIdentityMonitor:
    def __init__(
        self, *, root: Path, config: dict[str, Any], runner_record: dict[str, Any],
        snapshot_provider: Callable[[str, int, ExecutableHashCache], tuple[dict[str, Any], bytes]] | None = None,
    ) -> None:
        self.root = root.resolve()
        self.config = config
        self.cache = ExecutableHashCache()
        self.policy = StructuralIdentityPolicy(config, runner_record=runner_record)
        self.snapshot_provider = snapshot_provider or self._default_snapshot
        self.sequence = 0
        self.first_failure = self.root / "first_process_identity_failure.json"
        self.history = ContinuousProcessHistory(
            self.root / "continuous_history", self.cache,
            interval_seconds=config["process_identity"]["continuous_sample_interval_seconds"],
        )
        self._history_started = False

    @staticmethod
    def _default_snapshot(gate: str, sequence: int, cache: ExecutableHashCache) -> tuple[dict[str, Any], bytes]:
        raw = netstat_bytes()
        return build_snapshot(gate=gate, sequence=sequence, cache=cache, raw_netstat=raw), raw

    def start_history(self) -> None:
        self.history.start(); self._history_started = True

    def stop_history(self) -> dict[str, Any]:
        if not self._history_started:
            return {"samples": 0, "errors": [], "records": 0, "not_started": True}
        self._history_started = False
        return self.history.stop()

    def capture(self, *, gate: str, phase: str, mode: str = "enforce") -> dict[str, Any]:
        self.sequence += 1
        snapshot, raw = self.snapshot_provider(gate, self.sequence, self.cache)
        saved = save_snapshot(self.root / "snapshots" / f"{self.sequence:04d}_{gate}", snapshot, raw)
        if mode == "baseline":
            if any(snapshot["listeners"].get(str(port)) for port in (5037, 5038, 5554, 5555, 8554)):
                evaluation = Evaluation(False, ["BASELINE_LISTENER_PRESENT"], {}, {})
            else:
                self.policy.freeze_baseline(snapshot)
                evaluation = Evaluation(True, [], {key: "preexisting_unrelated_no_authority" for key in self.policy.baseline}, {})
        elif mode == "discovery":
            if snapshot["listeners"].get("5037"):
                evaluation = Evaluation(False, [f"FORBIDDEN_5037:{snapshot['listeners']['5037']}"], {}, {})
            else:
                self.policy.add_history(snapshot["structural_processes"])
                self.policy.add_history(self.history.records())
                evaluation = Evaluation(True, [], {}, {})
        elif mode == "cleanup_after_exit":
            evaluation = self.policy.evaluate(
                snapshot, phase=phase,
                recent_records=self.history.records(),
                allow_core_exit=True,
            )
        else:
            evaluation = self.policy.evaluate(
                snapshot, phase=phase,
                recent_records=self.history.records(),
            )
        result = {
            "passed": evaluation.passed,
            "issues": evaluation.issues,
            "roles": evaluation.roles,
            "helper_ancestry": evaluation.helper_ancestry,
            "snapshot": saved["record"],
            "snapshot_sequence": self.sequence,
            "gate": gate,
            "phase": phase,
        }
        atomic_write_json(
            self.root / "snapshots" / f"{self.sequence:04d}_{gate}" / "evaluation.json",
            result, replace=False,
        )
        if not evaluation.passed:
            failure = {
                "schema_version": "role_binding_timing.infra_m5.first_process_identity_failure.v1",
                "recorded_at": utc_now(), "gate": gate, "phase": phase,
                "issues": evaluation.issues, "roles": evaluation.roles,
                "helper_ancestry": evaluation.helper_ancestry,
                "triggering_snapshot": snapshot,
                "continuous_history_status": self.history.status(),
            }
            if not self.first_failure.exists():
                atomic_write_json(self.first_failure, failure, replace=False)
        return result

    def register_core_from_snapshot(self, *, role: str, snapshot_path: Path, pid: int) -> dict[str, Any]:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        record = process_index(snapshot["structural_processes"]).get(pid)
        if record is None:
            raise RuntimeError(f"CORE_PID_NOT_IN_SNAPSHOT:{role}:{pid}")
        self.policy.register_core(role, record)
        return record


def runner_identity(cache: ExecutableHashCache | None = None) -> dict[str, Any]:
    value = process_record(psutil.Process(os.getpid()))
    value["exe_sha256"] = (cache or ExecutableHashCache()).get(value.get("exe"))
    if not required_fields_present(value):
        raise RuntimeError(f"RUNNER_IDENTITY_MISSING:{value}")
    return value


def minimal_m5_completion(*, run_id: str, status: str, first_edge: str | None) -> dict[str, Any]:
    return {
        "schema_version": "role_binding_timing.infra_m5.completion.v1",
        "terminal_mode": "minimal_fallback",
        "run_id": run_id, "status": status, "first_broken_edge": first_edge,
        "completed_at": utc_now(), "generation_calls": 0, "model_tokens": 0,
        "held_out_captures": 0, "development_contaminated": True,
        "held_out_eligible": False, "process_identity": {}, "runtime": {},
        "burn_in": {"passed": False, "required_cycles": 24, "completed_cycles": 0, "passed_cycles": 0, "elapsed_seconds": 0.0, "records": []},
        "a11y": {"authorized": False, "settings": {"required": 3, "completed": 0, "passed": 0}, "grid": {"required": 12, "completed": 0, "passed": 0}},
        "cleanup": {}, "log_seal": {"passed": False, "records": [], "temporary_root_removed": False},
        "protected_wip_unchanged": True,
        "claim_evidence": {"process_identity_qualified": False, "exclusive_5038_registration": False, "burn_in_qualified": False, "a11y_tested": False, "a11y_qualified": False, "v0_3_preparation_authorized": False, "held_out_tested": False, "role_binding_hypothesis_tested": False},
    }


def finalize_m5_completion(
    *, output_root: Path, journal: Any, run_id: str, status: str,
    rich_completion: dict[str, Any] | None,
) -> dict[str, Any]:
    canonical = output_root / "qualification_completion.json"
    if canonical.exists():
        raise RuntimeError("DUPLICATE_TERMINAL_COMPLETION")
    journal.record(phase="terminal", event="start", status="RUNNING", details={"requested_status": status})
    first_edge = journal.first_edge()
    fallback = minimal_m5_completion(run_id=run_id, status=status, first_edge=first_edge)
    if status != "PASS_12_OF_12_DEV" and not first_edge:
        first_edge = f"TERMINAL_STATUS_WITHOUT_EDGE:{status}"
        journal.record(phase="terminal", event="status_without_edge", status="FAIL", first_broken_edge=first_edge)
        fallback["first_broken_edge"] = first_edge
    atomic_write_json(canonical, fallback, replace=False)
    mode = "minimal_fallback"
    rich_error = None
    if rich_completion is not None:
        try:
            rich = dict(rich_completion)
            rich.update({
                "schema_version": "role_binding_timing.infra_m5.completion.v1",
                "terminal_mode": "rich", "run_id": run_id, "status": status,
                "first_broken_edge": journal.first_edge(), "completed_at": utc_now(),
                "generation_calls": 0, "model_tokens": 0, "held_out_captures": 0,
            })
            atomic_write_json(canonical, rich, replace=True)
            mode = "rich"
        except Exception as exc:
            rich_error = {"type": type(exc).__name__, "message": str(exc)}
            journal.record(
                phase="terminal", event="rich_serialization", status="FAIL",
                first_broken_edge=f"TERMINAL_RICH_SERIALIZATION:{type(exc).__name__}:{exc}",
                details=rich_error,
            )
    journal.record(phase="terminal", event="end", status="PASS", details={"terminal_mode": mode, "rich_error": rich_error})
    final = json.loads(canonical.read_text(encoding="utf-8"))
    final.update({
        "terminal_mode": mode, "first_broken_edge": journal.first_edge(),
        "last_completed_phase": journal.last_completed_phase(),
        "journal_entry_count": len(journal.read_entries()),
        "journal_terminal_event_present": True,
    })
    if rich_error:
        final["rich_serialization_error"] = rich_error
    atomic_write_json(canonical, final, replace=True)
    atomic_write_json(output_root / "terminal_writer_receipt.json", {
        "schema_version": "role_binding_timing.infra_m5.terminal_receipt.v1",
        "terminal_mode": mode, "canonical_path": str(canonical),
        "canonical_sha256": sha256(canonical.read_bytes()).hexdigest(),
        "first_broken_edge": journal.first_edge(),
        "journal_entry_count": len(journal.read_entries()),
        "rich_error": rich_error,
    }, replace=False)
    return final
