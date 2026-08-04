"""Runner-owned ADB-client authority and listener-bearing history for INFRA-M7."""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Callable

from raven_m.role_binding_timing.infra_m4_terminal_accounting import atomic_write_json, utc_now
from raven_m.role_binding_timing.infra_m5_process_identity import (
    Evaluation,
    ExecutableHashCache,
    RELEVANT_NAMES,
    build_snapshot,
    enrich_structural_records,
    identity_key,
    netstat_bytes,
    normalized_path,
    process_index,
    required_fields_present,
    save_snapshot,
    snapshot_processes,
)
from raven_m.role_binding_timing.infra_m6_display_observability import (
    M6ProcessIdentityMonitor,
    M6StructuralIdentityPolicy,
)


def listener_ports_by_pid(raw_netstat: bytes) -> dict[int, list[int]]:
    """Parse all Windows TCP LISTENING rows; malformed rows never create authority."""
    text = raw_netstat.decode("utf-8", errors="replace")
    result: dict[int, set[int]] = {}
    expression = re.compile(
        r"^\s*TCP\s+(?:\[[^\]]+\]|[^\s:]+):(\d+)\s+\S+\s+LISTENING\s+(\d+)\s*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    for port, pid in expression.findall(text):
        result.setdefault(int(pid), set()).add(int(port))
    return {pid: sorted(ports) for pid, ports in sorted(result.items())}


def annotate_listener_evidence(records: list[dict[str, Any]], raw_netstat: bytes) -> list[dict[str, Any]]:
    listeners = listener_ports_by_pid(raw_netstat)
    annotated = []
    for source in records:
        record = dict(source)
        pid = record.get("pid")
        record["listener_evidence_complete"] = True
        record["listener_ports"] = listeners.get(int(pid), []) if isinstance(pid, int) else []
        annotated.append(record)
    return annotated


def build_m7_snapshot(
    *, gate: str, sequence: int, cache: ExecutableHashCache,
    raw_processes: list[dict[str, Any]] | None = None,
    raw_netstat: bytes | None = None,
) -> dict[str, Any]:
    processes = raw_processes if raw_processes is not None else snapshot_processes()
    network = raw_netstat if raw_netstat is not None else netstat_bytes()
    value = build_snapshot(
        gate=gate, sequence=sequence, cache=cache,
        raw_processes=processes, raw_netstat=network,
    )
    value["schema_version"] = "role_binding_timing.infra_m7.process_snapshot.v1"
    value["structural_processes"] = annotate_listener_evidence(value["structural_processes"], network)
    value["all_tcp_listener_ports_by_pid"] = {
        str(pid): ports for pid, ports in listener_ports_by_pid(network).items()
    }
    value["listener_evidence_complete"] = True
    value["captured_epoch"] = time.time()
    return value


def _argv(record: dict[str, Any]) -> list[str] | None:
    value = record.get("cmdline_items")
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        return None
    return list(value)


class M7StructuralIdentityPolicy(M6StructuralIdentityPolicy):
    """Authorize structurally owned short-lived clients without harmless argv lists."""

    def __init__(self, config: dict[str, Any], *, runner_record: dict[str, Any]) -> None:
        super().__init__(config, runner_record=runner_record)
        self.authorized_runner_clients: dict[str, dict[str, Any]] = {}

    def _classify_new(
        self, record: dict[str, Any], phase: str, current: dict[int, dict[str, Any]],
    ) -> tuple[str | None, list[str], list[str]]:
        binaries = self.config["process_identity"]["binaries"]
        if required_fields_present(record) and normalized_path(record.get("exe")) == normalized_path(binaries["adb"]["path"]):
            key = identity_key(record)
            observed = current.get(int(record["pid"]))
            current_same = observed is not None and identity_key(observed) == key
            # Every observed form of a previously authorized identity is rechecked for listeners/lifetime.
            if key in self.authorized_runner_clients:
                issues = self._continuing_client_issues(record, current_same=current_same)
                ledger = self.authorized_runner_clients[key]
                return (ledger["role"], [], ledger["ancestry"]) if not issues else (None, issues, ledger["ancestry"])
            # Direct runner ownership is the authority boundary.  An ADB process
            # presenting the runner's explicit global-port prefix is also routed
            # through this check so a wrong parent receives an explicit fail-closed
            # diagnosis instead of falling through to a less specific M5 role.
            # Emulator bootstrap clients use a different argv shape and remain M5
            # roles.
            argv = _argv(record)
            has_runner_port_prefix = (
                argv is not None
                and len(argv) >= 3
                and argv[1].casefold() == "-p"
            )
            if record.get("ppid") == self.runner_record.get("pid") or has_runner_port_prefix:
                return self._authorize_runner_client(record, phase=phase, current=current)
        return super()._classify_new(record, phase, current)

    def _common_client_issues(
        self, record: dict[str, Any], *, current: dict[int, dict[str, Any]], check_age: bool,
    ) -> tuple[list[str], list[str], list[str] | None]:
        issues: list[str] = []
        runner_key = identity_key(self.runner_record)
        ancestry = [runner_key] if runner_key else []
        argv = _argv(record)
        if argv is None:
            return ["RUNNER_CLIENT_ARGV_MISSING"], ancestry, None
        binaries = self.config["process_identity"]["binaries"]
        if normalized_path(argv[0]) != normalized_path(binaries["adb"]["path"]):
            issues.append("RUNNER_CLIENT_ARGV_EXECUTABLE")
        if record.get("exe_sha256") != binaries["adb"]["sha256"]:
            issues.append("RUNNER_CLIENT_HASH")
        # The runner freezes the global ADB server selector as the first option.
        # A later ``-p`` belongs to an ADB subcommand (notably ``screencap -p``)
        # and therefore must not be misread as another server-port selector.
        if len(argv) < 3 or argv[1].casefold() != "-p":
            issues.append("RUNNER_CLIENT_PORT_AMBIGUOUS_OR_MISSING")
        elif argv[2] != "5038":
            issues.append("RUNNER_CLIENT_PORT_NOT_5038")
        if record.get("ppid") != self.runner_record.get("pid"):
            issues.append("RUNNER_CLIENT_PARENT")
        runner_current = current.get(int(self.runner_record["pid"]))
        if runner_current is None or identity_key(runner_current) != runner_key:
            issues.append("RUNNER_PARENT_IDENTITY_NOT_CURRENT")
        created = record.get("create_time")
        runner_created = self.runner_record.get("create_time")
        if not isinstance(created, (int, float)) or not isinstance(runner_created, (int, float)) or float(created) < float(runner_created):
            issues.append("RUNNER_CLIENT_CREATION_ORDER")
        if record.get("listener_evidence_complete") is not True:
            issues.append("RUNNER_CLIENT_LISTENER_EVIDENCE_MISSING")
        ports = record.get("listener_ports")
        if not isinstance(ports, list):
            issues.append("RUNNER_CLIENT_LISTENER_EVIDENCE_MALFORMED")
        elif ports:
            issues.append(f"RUNNER_CLIENT_OWNS_LISTENER:{ports}")
        historical_ports = record.get("history_max_listener_ports", [])
        if not isinstance(historical_ports, list):
            issues.append("RUNNER_CLIENT_HISTORY_LISTENER_EVIDENCE_MALFORMED")
        elif historical_ports:
            issues.append(f"RUNNER_CLIENT_HISTORY_OWNS_LISTENER:{historical_ports}")
        if check_age and isinstance(created, (int, float)):
            age = time.time() - float(created)
            if age < -1.0:
                issues.append("RUNNER_CLIENT_CREATION_IN_FUTURE")
            if age > float(self.config["runner_adb_client"]["max_active_lifetime_seconds"]):
                issues.append("RUNNER_CLIENT_LIFETIME_EXCEEDED")
        return issues, ancestry, argv

    @staticmethod
    def _server_kind(argv: list[str]) -> str:
        lowered = [token.casefold() for token in argv]
        if "start-server" in lowered:
            return "start"
        if "kill-server" in lowered:
            return "kill"
        if "nodaemon" in lowered or "fork-server" in lowered or "server" in lowered:
            return "forbidden"
        return "ordinary"

    def _authorize_runner_client(
        self, record: dict[str, Any], *, phase: str, current: dict[int, dict[str, Any]],
    ) -> tuple[str | None, list[str], list[str]]:
        issues, ancestry, argv = self._common_client_issues(record, current=current, check_age=True)
        if argv is None:
            return None, issues, ancestry
        kind = self._server_kind(argv)
        role = "runner_adb_client"
        if kind == "forbidden":
            issues.append("RUNNER_CLIENT_SERVER_MODE_FORBIDDEN")
        elif kind == "start":
            role = "runner_adb_server_lifecycle_start"
            if phase != "launch":
                issues.append(f"RUNNER_CLIENT_START_SERVER_PHASE:{phase}")
        elif kind == "kill":
            role = "runner_adb_server_lifecycle_stop"
            if phase != "cleanup":
                issues.append(f"RUNNER_CLIENT_KILL_SERVER_PHASE:{phase}")
        key = identity_key(record)
        if not issues and key:
            self.authorized_runner_clients[key] = {
                "role": role,
                "authorized_phase": phase,
                "authorized_at_epoch": time.time(),
                "argv_sha256": sha256(json.dumps(argv, ensure_ascii=False).encode("utf-8")).hexdigest(),
                "ancestry": ancestry,
            }
            return role, [], ancestry
        return None, issues or ["RUNNER_CLIENT_IDENTITY_KEY_MISSING"], ancestry

    def _continuing_client_issues(self, record: dict[str, Any], *, current_same: bool) -> list[str]:
        current = {int(self.runner_record["pid"]): self.runner_record}
        issues, _, argv = self._common_client_issues(record, current=current, check_age=current_same)
        key = identity_key(record)
        ledger = self.authorized_runner_clients.get(key or "", {})
        if argv is not None:
            observed_hash = sha256(json.dumps(argv, ensure_ascii=False).encode("utf-8")).hexdigest()
            if observed_hash != ledger.get("argv_sha256"):
                issues.append("RUNNER_CLIENT_ARGV_IDENTITY_DRIFT")
        return issues


class M7ContinuousProcessHistory:
    """250 ms process history with complete per-identity TCP listener evidence."""

    def __init__(self, root: Path, cache: ExecutableHashCache, *, interval_seconds: float) -> None:
        self.root = root.resolve()
        self.cache = cache
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._records: dict[str, dict[str, Any]] = {}
        self._active: set[str] = set()
        self._samples = 0
        self._errors: list[str] = []
        self._ndjson = self.root / "process_history.ndjson"

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("PROCESS_HISTORY_ALREADY_STARTED")
        self.root.mkdir(parents=True, exist_ok=False)
        self._thread = threading.Thread(target=self._run, name="infra-m7-listener-history", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                captured_monotonic = time.monotonic()
                network = netstat_bytes()
                records = annotate_listener_evidence(
                    enrich_structural_records(snapshot_processes(), self.cache), network,
                )
                current: set[str] = set()
                with self._lock:
                    for record in records:
                        key = identity_key(record)
                        if key is None:
                            continue
                        current.add(key)
                        prior = self._records.get(key, {})
                        enriched = dict(record)
                        enriched["history_first_seen_monotonic"] = prior.get("history_first_seen_monotonic", captured_monotonic)
                        enriched["history_last_seen_monotonic"] = captured_monotonic
                        enriched["history_exit_observed"] = False
                        enriched["history_max_listener_ports"] = sorted(set(prior.get("history_max_listener_ports", [])) | set(record["listener_ports"]))
                        self._records[key] = enriched
                    for key in self._active - current:
                        if key in self._records:
                            self._records[key]["history_exit_observed"] = True
                            self._records[key]["history_exit_observed_monotonic"] = captured_monotonic
                    self._active = current
                    self._samples += 1
                    event = {
                        "schema_version": "role_binding_timing.infra_m7.process_history_sample.v1",
                        "captured_at": utc_now(), "captured_monotonic": captured_monotonic,
                        "sample": self._samples, "listener_evidence_complete": True,
                        "all_tcp_listener_ports_by_pid": {str(pid): ports for pid, ports in listener_ports_by_pid(network).items()},
                        "structural_processes": records,
                        "raw_netstat_sha256": sha256(network).hexdigest(),
                    }
                    with self._ndjson.open("ab") as handle:
                        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n")
                        handle.flush(); os.fsync(handle.fileno())
            except Exception as exc:
                with self._lock:
                    self._errors.append(f"{type(exc).__name__}:{exc}")
            self._stop.wait(self.interval_seconds)

    def records(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(value) for value in self._records.values()]

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {"samples": self._samples, "errors": list(self._errors), "records": len(self._records), "active": len(self._active)}

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


class M7ProcessIdentityMonitor(M6ProcessIdentityMonitor):
    """M7 snapshots, policy, history, and write-once trigger persistence."""

    def __init__(
        self, *, root: Path, config: dict[str, Any], runner_record: dict[str, Any],
        snapshot_provider: Callable[[str, int, ExecutableHashCache], tuple[dict[str, Any], bytes]] | None = None,
    ) -> None:
        super().__init__(root=root, config=config, runner_record=runner_record, snapshot_provider=snapshot_provider)
        self.policy = M7StructuralIdentityPolicy(config, runner_record=runner_record)
        self.history = M7ContinuousProcessHistory(
            self.root / "continuous_history", self.cache,
            interval_seconds=config["process_identity"]["continuous_sample_interval_seconds"],
        )

    @staticmethod
    def _default_snapshot(gate: str, sequence: int, cache: ExecutableHashCache) -> tuple[dict[str, Any], bytes]:
        raw = netstat_bytes()
        return build_m7_snapshot(gate=gate, sequence=sequence, cache=cache, raw_netstat=raw), raw

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
            evaluation = self.policy.evaluate(snapshot, phase=phase, recent_records=self.history.records(), allow_core_exit=True)
        else:
            evaluation = self.policy.evaluate(snapshot, phase=phase, recent_records=self.history.records())
        result = {
            "schema_version": "role_binding_timing.infra_m7.process_evaluation.v1",
            "passed": evaluation.passed, "issues": evaluation.issues,
            "roles": evaluation.roles, "helper_ancestry": evaluation.helper_ancestry,
            "runner_client_ledger": dict(self.policy.authorized_runner_clients),
            "snapshot": saved["record"], "snapshot_sequence": self.sequence,
            "gate": gate, "phase": phase,
        }
        atomic_write_json(self.root / "snapshots" / f"{self.sequence:04d}_{gate}" / "evaluation.json", result, replace=False)
        if not evaluation.passed and not self.first_failure.exists():
            atomic_write_json(self.first_failure, {
                "schema_version": "role_binding_timing.infra_m7.first_process_identity_failure.v1",
                "recorded_at": utc_now(), "gate": gate, "phase": phase,
                "issues": evaluation.issues, "roles": evaluation.roles,
                "helper_ancestry": evaluation.helper_ancestry,
                "runner_client_ledger": dict(self.policy.authorized_runner_clients),
                "triggering_snapshot": snapshot,
                "continuous_history_status": self.history.status(),
            }, replace=False)
        return result
