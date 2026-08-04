"""Full-snapshot ancestry and separate authorization view for INFRA-M8."""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Callable, Iterable

from raven_m.role_binding_timing.infra_m4_terminal_accounting import atomic_write_json, utc_now
from raven_m.role_binding_timing.infra_m5_process_identity import (
    Evaluation,
    ExecutableHashCache,
    RELEVANT_NAMES,
    identity_key,
    netstat_bytes,
    normalized_path,
    process_index,
    required_fields_present,
    save_snapshot,
    snapshot_processes,
)
from raven_m.role_binding_timing.infra_m6_display_observability import M6StructuralIdentityPolicy
from raven_m.role_binding_timing.infra_m7_adb_authority import (
    M7ProcessIdentityMonitor,
    M7StructuralIdentityPolicy,
    _argv,
    annotate_listener_evidence,
    build_m7_snapshot,
    listener_ports_by_pid,
)


def canonical_hash(value: Any) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def compact_identity_universe(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Lossless for existence, parent traversal, creation identity and PID reuse."""
    fields = ("pid", "ppid", "name", "exe", "create_time", "identity_key", "access_error")
    return [{field: record.get(field) for field in fields} for record in records]


def build_m8_snapshot(
    *, gate: str, sequence: int, cache: ExecutableHashCache,
    raw_processes: list[dict[str, Any]] | None = None,
    raw_netstat: bytes | None = None,
) -> dict[str, Any]:
    processes = raw_processes if raw_processes is not None else snapshot_processes()
    network = raw_netstat if raw_netstat is not None else netstat_bytes()
    value = build_m7_snapshot(gate=gate, sequence=sequence, cache=cache,
                              raw_processes=processes, raw_netstat=network)
    value["schema_version"] = "role_binding_timing.infra_m8.process_snapshot.v1"
    value["observation_universe_complete"] = True
    value["observation_universe_capture_errors"] = []
    value["view_contract"] = {
        "observation_universe": "all_processes",
        "authorization_candidates": "structural_processes",
        "observation_universe_sha256": canonical_hash(value["all_processes"]),
        "authorization_candidates_sha256": canonical_hash(value["structural_processes"]),
        "observation_universe_count": len(value["all_processes"]),
        "authorization_candidate_count": len(value["structural_processes"]),
    }
    return value


def _pid_groups(records: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = {}
    for record in records:
        pid = record.get("pid")
        if isinstance(pid, int):
            result.setdefault(pid, []).append(record)
    return result


def derive_authorization_view(
    snapshot: dict[str, Any], *, runner_record: dict[str, Any],
) -> tuple[dict[str, Any], dict[int, dict[str, Any]], dict[int, dict[str, Any]], list[str]]:
    """Validate and join two domains without granting roles to universe-only rows."""
    issues: list[str] = []
    universe = snapshot.get("all_processes")
    candidates = snapshot.get("structural_processes")
    if snapshot.get("observation_universe_complete") is not True:
        issues.append("OBSERVATION_UNIVERSE_TRUNCATED")
    if snapshot.get("observation_universe_capture_errors") not in ([], None):
        issues.append("OBSERVATION_UNIVERSE_CAPTURE_ERRORS")
    if not isinstance(universe, list):
        universe = []; issues.append("OBSERVATION_UNIVERSE_MISSING")
    if not isinstance(candidates, list):
        candidates = []; issues.append("AUTHORIZATION_VIEW_MISSING")
    groups = _pid_groups(universe)
    full_index: dict[int, dict[str, Any]] = {}
    for pid, records in groups.items():
        if len(records) != 1:
            issues.append(f"OBSERVATION_UNIVERSE_PID_AMBIGUITY:{pid}")
        else:
            full_index[pid] = records[0]
    candidate_index: dict[int, dict[str, Any]] = {}
    candidate_links = []
    for candidate in candidates:
        pid = candidate.get("pid")
        key = identity_key(candidate)
        if not isinstance(pid, int) or key is None:
            issues.append("AUTHORIZATION_CANDIDATE_IDENTITY_MISSING"); continue
        if pid in candidate_index:
            issues.append(f"AUTHORIZATION_VIEW_PID_AMBIGUITY:{pid}"); continue
        observed = full_index.get(pid)
        matches = observed is not None and identity_key(observed) == key
        candidate_links.append({"pid": pid, "candidate_identity": key,
                                "universe_identity": identity_key(observed) if observed else None,
                                "matches": matches})
        if not matches:
            issues.append(f"AUTHORIZATION_VIEW_UNIVERSE_MISMATCH:{pid}")
        else:
            # Overlay the hash/listener-enriched candidate on the full-universe
            # record for ancestry traversals that require richer wrapper evidence.
            full_index[pid] = {**observed, **candidate}
            candidate_index[pid] = candidate
    runner_pid = runner_record.get("pid")
    runner_key = identity_key(runner_record)
    current_runner = full_index.get(int(runner_pid)) if isinstance(runner_pid, int) else None
    if current_runner is None:
        issues.append("OBSERVATION_UNIVERSE_RUNNER_MISSING")
    elif identity_key(current_runner) != runner_key:
        issues.append("OBSERVATION_UNIVERSE_RUNNER_PID_REUSE")
    record = {
        "schema_version": "role_binding_timing.infra_m8.authorization_view.v1",
        "source_snapshot_schema": snapshot.get("schema_version"),
        "source_universe_sha256": canonical_hash(universe),
        "source_candidate_sha256": canonical_hash(candidates),
        "observation_universe_complete": snapshot.get("observation_universe_complete") is True,
        "observation_universe_count": len(universe),
        "authorization_candidate_count": len(candidates),
        "runner_identity": runner_key,
        "runner_observed_identity": identity_key(current_runner) if current_runner else None,
        "candidate_links": candidate_links,
        "authorization_candidates": candidates,
        "issues": sorted(set(issues)),
        "passed": not issues,
    }
    return record, full_index, candidate_index, sorted(set(issues))


class M8StructuralIdentityPolicy(M7StructuralIdentityPolicy):
    """Use the full universe for ancestry, the candidate view for role authority."""

    def _common_client_issues(
        self, record: dict[str, Any], *, current: dict[int, dict[str, Any]], check_age: bool,
    ) -> tuple[list[str], list[str], list[str] | None]:
        issues, ancestry, argv = super()._common_client_issues(record, current=current, check_age=check_age)
        issues = [item for item in issues if item != "RUNNER_PARENT_IDENTITY_NOT_CURRENT"]
        runner_pid = self.runner_record.get("pid")
        expected_key = identity_key(self.runner_record)
        observed = current.get(int(runner_pid)) if isinstance(runner_pid, int) else None
        if observed is None:
            issues.append("RUNNER_PARENT_MISSING_FROM_OBSERVATION_UNIVERSE")
        elif identity_key(observed) != expected_key:
            issues.append("RUNNER_PARENT_PID_REUSE")
        return sorted(set(issues)), ancestry, argv

    def _classify_new(
        self, record: dict[str, Any], phase: str, current: dict[int, dict[str, Any]],
    ) -> tuple[str | None, list[str], list[str]]:
        binaries = self.config["process_identity"]["binaries"]
        if required_fields_present(record) and normalized_path(record.get("exe")) == normalized_path(binaries["adb"]["path"]):
            key = identity_key(record)
            observed = current.get(int(record["pid"]))
            current_same = observed is not None and identity_key(observed) == key
            if key in self.authorized_runner_clients:
                issues, ancestry, argv = self._common_client_issues(record, current=current, check_age=current_same)
                ledger = self.authorized_runner_clients[key]
                if argv is not None:
                    observed_hash = sha256(json.dumps(argv, ensure_ascii=False).encode("utf-8")).hexdigest()
                    if observed_hash != ledger.get("argv_sha256"):
                        issues.append("RUNNER_CLIENT_ARGV_IDENTITY_DRIFT")
                return (ledger["role"], [], ledger["ancestry"]) if not issues else (None, sorted(set(issues)), ancestry)
            argv = _argv(record)
            has_runner_port_prefix = argv is not None and len(argv) >= 3 and argv[1].casefold() == "-p"
            if record.get("ppid") == self.runner_record.get("pid") or has_runner_port_prefix:
                return self._authorize_runner_client(record, phase=phase, current=current)
        return M6StructuralIdentityPolicy._classify_new(self, record, phase, current)

    def _ancestry_to_core(
        self, record: dict[str, Any], current: dict[int, dict[str, Any]],
    ) -> tuple[bool, list[str]]:
        """Traverse only the current complete universe; stale history grants no ancestry."""
        target_keys = {identity_key(self.core[role]) for role in ("emulator_launcher", "qemu") if role in self.core}
        chain: list[str] = []; parent_pid = record.get("ppid"); seen: set[int] = set()
        child_time = record.get("create_time")
        for _ in range(self.config["process_identity"]["max_parent_depth"]):
            if not isinstance(parent_pid, int) or parent_pid <= 0 or parent_pid in seen:
                return False, chain
            seen.add(parent_pid); parent = current.get(parent_pid)
            if parent is None:
                chain.append(f"{parent_pid}@MISSING_CURRENT_UNIVERSE"); return False, chain
            parent_time = parent.get("create_time")
            if not isinstance(child_time, (int, float)) or not isinstance(parent_time, (int, float)) or float(parent_time) > float(child_time):
                chain.append(f"{parent_pid}@CREATION_MISMATCH"); return False, chain
            key = identity_key(parent); chain.append(key or f"{parent_pid}@IDENTITY_MISSING")
            if key in target_keys:
                return True, chain
            if not self._allowed_wrapper(parent):
                return False, chain
            record = parent; child_time = parent_time; parent_pid = parent.get("ppid")
        return False, chain

    def evaluate(
        self, snapshot: dict[str, Any], *, phase: str,
        recent_records: Iterable[dict[str, Any]] = (), allow_core_exit: bool = False,
    ) -> Evaluation:
        view, universe_current, candidate_current, issues = derive_authorization_view(
            snapshot, runner_record=self.runner_record,
        )
        roles: dict[str, str] = {}
        helper_ancestry: dict[str, list[str]] = {}
        listeners = snapshot.get("listeners", {})
        if listeners.get("5037"):
            issues.append(f"FORBIDDEN_5037:{listeners['5037']}")
        if issues:
            return Evaluation(False, sorted(set(issues)), roles, helper_ancestry)
        combined: dict[str, dict[str, Any]] = {}
        recent = list(recent_records)
        for record in [*snapshot["structural_processes"], *recent]:
            key = identity_key(record)
            if key and str(record.get("name") or "").casefold() in RELEVANT_NAMES:
                combined[key] = record
        self.add_history(snapshot["structural_processes"]); self.add_history(recent)

        for role, expected in self.core.items():
            pid = int(expected["pid"]); observed = candidate_current.get(pid)
            if observed is None and allow_core_exit:
                continue
            if observed is None:
                issues.append(f"CORE_MISSING:{role}:{pid}"); continue
            if identity_key(observed) != identity_key(expected):
                issues.append(f"CORE_PID_REUSE:{role}:{pid}"); continue
            issues.extend(f"CORE_{role.upper()}:{item}" for item in self._core_shape_issues(role, observed))
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
                roles[key] = "preexisting_unrelated_no_authority"; continue
            baseline_key = self.baseline_by_pid.get(pid)
            if baseline_key and baseline_key != key:
                issues.append(f"PID_REUSE:{pid}:{baseline_key}:{key}"); continue
            if key in core_keys:
                continue
            role, role_issues, chain = self._classify_new(record, phase, universe_current)
            if role:
                roles[key] = role; helper_ancestry[key] = chain
            else:
                issues.extend(f"PROCESS:{key}:{item}" for item in role_issues)
                if chain:
                    helper_ancestry[key] = chain
        return Evaluation(not issues, sorted(set(issues)), roles, helper_ancestry)


class M8ContinuousProcessHistory:
    """Complete compact identity universe plus rich authorization candidates."""

    def __init__(self, root: Path, cache: ExecutableHashCache, *, interval_seconds: float) -> None:
        self.root = root.resolve(); self.cache = cache; self.interval_seconds = interval_seconds
        self._stop = threading.Event(); self._thread: threading.Thread | None = None
        self._lock = threading.Lock(); self._records: dict[str, dict[str, Any]] = {}
        self._active: set[str] = set(); self._samples = 0; self._errors: list[str] = []
        self._ndjson = self.root / "process_history.ndjson"

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("PROCESS_HISTORY_ALREADY_STARTED")
        self.root.mkdir(parents=True, exist_ok=False)
        self._thread = threading.Thread(target=self._run, name="infra-m8-full-universe-history", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        from raven_m.role_binding_timing.infra_m5_process_identity import enrich_structural_records
        while not self._stop.is_set():
            try:
                captured = time.monotonic(); raw = snapshot_processes(); network = netstat_bytes()
                candidates = annotate_listener_evidence(enrich_structural_records(raw, self.cache), network)
                universe = compact_identity_universe(raw); current: set[str] = set()
                with self._lock:
                    for source in candidates:
                        key = identity_key(source)
                        if key is None:
                            continue
                        current.add(key); prior = self._records.get(key, {}); record = dict(source)
                        record["history_first_seen_monotonic"] = prior.get("history_first_seen_monotonic", captured)
                        record["history_last_seen_monotonic"] = captured; record["history_exit_observed"] = False
                        record["history_max_listener_ports"] = sorted(set(prior.get("history_max_listener_ports", [])) | set(record["listener_ports"]))
                        self._records[key] = record
                    for key in self._active - current:
                        if key in self._records:
                            self._records[key]["history_exit_observed"] = True
                            self._records[key]["history_exit_observed_monotonic"] = captured
                    self._active = current; self._samples += 1
                    event = {
                        "schema_version": "role_binding_timing.infra_m8.process_history_sample.v1",
                        "captured_at": utc_now(), "captured_monotonic": captured, "sample": self._samples,
                        "observation_universe_complete": True,
                        "observation_identity_universe": universe,
                        "observation_identity_universe_sha256": canonical_hash(universe),
                        "authorization_candidates": candidates,
                        "authorization_candidates_sha256": canonical_hash(candidates),
                        "listener_evidence_complete": True,
                        "all_tcp_listener_ports_by_pid": {str(pid): ports for pid, ports in listener_ports_by_pid(network).items()},
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
            return {"samples": self._samples, "errors": list(self._errors), "records": len(self._records),
                    "active": len(self._active), "complete_identity_universe_each_sample": not self._errors}

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


class M8ProcessIdentityMonitor(M7ProcessIdentityMonitor):
    """Persist complete trigger snapshots and separately derived authorization views."""

    def __init__(
        self, *, root: Path, config: dict[str, Any], runner_record: dict[str, Any],
        snapshot_provider: Callable[[str, int, ExecutableHashCache], tuple[dict[str, Any], bytes]] | None = None,
    ) -> None:
        super().__init__(root=root, config=config, runner_record=runner_record, snapshot_provider=snapshot_provider)
        self.policy = M8StructuralIdentityPolicy(config, runner_record=runner_record)
        self.history = M8ContinuousProcessHistory(self.root / "continuous_history", self.cache,
            interval_seconds=config["process_identity"]["continuous_sample_interval_seconds"])

    @staticmethod
    def _default_snapshot(gate: str, sequence: int, cache: ExecutableHashCache) -> tuple[dict[str, Any], bytes]:
        raw = netstat_bytes()
        return build_m8_snapshot(gate=gate, sequence=sequence, cache=cache, raw_netstat=raw), raw

    def capture(self, *, gate: str, phase: str, mode: str = "enforce") -> dict[str, Any]:
        self.sequence += 1
        snapshot, raw = self.snapshot_provider(gate, self.sequence, self.cache)
        saved = save_snapshot(self.root / "snapshots" / f"{self.sequence:04d}_{gate}", snapshot, raw)
        view, _, _, view_issues = derive_authorization_view(snapshot, runner_record=self.policy.runner_record)
        view_record = atomic_write_json(self.root / "snapshots" / f"{self.sequence:04d}_{gate}" / "derived_authorization_view.json", view, replace=False)
        if mode == "baseline":
            issues = list(view_issues)
            if any(snapshot.get("listeners", {}).get(str(port)) for port in (5037, 5038, 5554, 5555, 8554)):
                issues.append("BASELINE_LISTENER_PRESENT")
            if issues:
                evaluation = Evaluation(False, sorted(set(issues)), {}, {})
            else:
                self.policy.freeze_baseline(snapshot)
                evaluation = Evaluation(True, [], {key: "preexisting_unrelated_no_authority" for key in self.policy.baseline}, {})
        elif mode == "discovery":
            issues = list(view_issues)
            if snapshot.get("listeners", {}).get("5037"):
                issues.append(f"FORBIDDEN_5037:{snapshot['listeners']['5037']}")
            if not issues:
                self.policy.add_history(snapshot["structural_processes"]); self.policy.add_history(self.history.records())
            evaluation = Evaluation(not issues, sorted(set(issues)), {}, {})
        elif mode == "cleanup_after_exit":
            evaluation = self.policy.evaluate(snapshot, phase=phase, recent_records=self.history.records(), allow_core_exit=True)
        else:
            evaluation = self.policy.evaluate(snapshot, phase=phase, recent_records=self.history.records())
        result = {
            "schema_version": "role_binding_timing.infra_m8.process_evaluation.v1",
            "passed": evaluation.passed, "issues": evaluation.issues, "roles": evaluation.roles,
            "helper_ancestry": evaluation.helper_ancestry,
            "runner_client_ledger": dict(self.policy.authorized_runner_clients),
            "snapshot": saved["record"], "derived_authorization_view": view_record,
            "snapshot_sequence": self.sequence, "gate": gate, "phase": phase,
        }
        atomic_write_json(self.root / "snapshots" / f"{self.sequence:04d}_{gate}" / "evaluation.json", result, replace=False)
        if not evaluation.passed and not self.first_failure.exists():
            atomic_write_json(self.first_failure, {
                "schema_version": "role_binding_timing.infra_m8.first_process_identity_failure.v1",
                "recorded_at": utc_now(), "gate": gate, "phase": phase, "issues": evaluation.issues,
                "roles": evaluation.roles, "helper_ancestry": evaluation.helper_ancestry,
                "runner_client_ledger": dict(self.policy.authorized_runner_clients),
                "triggering_snapshot": snapshot, "derived_authorization_view": view,
                "derived_authorization_view_record": view_record,
                "continuous_history_status": self.history.status(),
            }, replace=False)
        return result
