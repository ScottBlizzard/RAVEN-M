"""Disjoint process authorization views for INFRA-M9.

The complete OS snapshot is the observation universe.  Project authority is
available only to an explicitly derived candidate view; ancestry support and
unrelated rows remain evidence-only.
"""

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
    identity_key,
    netstat_bytes,
    normalized_command,
    normalized_path,
    process_index,
    save_snapshot,
    snapshot_processes,
)
from raven_m.role_binding_timing.infra_m7_adb_authority import (
    annotate_listener_evidence,
    listener_ports_by_pid,
)
from raven_m.role_binding_timing.infra_m8_full_snapshot_ancestry import (
    M8ProcessIdentityMonitor,
    M8StructuralIdentityPolicy,
    build_m8_snapshot,
    canonical_hash,
    compact_identity_universe,
)


CONTROLLED_PORTS = frozenset({5037, 5038, 5554, 5555, 8554})
DIRECT_BINARY_KEYS = ("adb", "emulator_launcher", "qemu", "crashpad", "netsimd")
VIEW_NAMES = (
    "project_authorization_candidates",
    "support_only_ancestry_nodes",
    "unrelated_observed_processes",
)


def _pid_groups(records: Iterable[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = {}
    for record in records:
        pid = record.get("pid")
        if isinstance(pid, int):
            result.setdefault(pid, []).append(record)
    return result


def _listener_map(snapshot: dict[str, Any]) -> dict[int, list[int]]:
    raw = snapshot.get("all_tcp_listener_ports_by_pid", {})
    result: dict[int, list[int]] = {}
    if not isinstance(raw, dict):
        return result
    for pid, ports in raw.items():
        try:
            numeric_pid = int(pid)
        except (TypeError, ValueError):
            continue
        if isinstance(ports, list) and all(isinstance(port, int) for port in ports):
            result[numeric_pid] = sorted(set(ports))
    return result


def _rich_index(snapshot: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return process_index(snapshot.get("structural_processes", []))


def _runner_matches(observed: dict[str, Any] | None, frozen: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if observed is None:
        return False, ["TRUSTED_RUNNER_ROOT_MISSING"]
    if identity_key(observed) != identity_key(frozen):
        issues.append("TRUSTED_RUNNER_ROOT_PID_REUSE")
    if normalized_path(observed.get("exe")) != normalized_path(frozen.get("exe")):
        issues.append("TRUSTED_RUNNER_ROOT_PATH_DRIFT")
    if normalized_command(observed.get("command_line")) != normalized_command(frozen.get("command_line")):
        issues.append("TRUSTED_RUNNER_ROOT_COMMAND_DRIFT")
    return not issues, issues


def _known_direct_paths(config: dict[str, Any]) -> set[str]:
    binaries = config["process_identity"]["binaries"]
    return {
        normalized_path(binaries[key]["path"])
        for key in DIRECT_BINARY_KEYS
    }


def derive_process_views(
    snapshot: dict[str, Any], *, config: dict[str, Any], runner_record: dict[str, Any],
) -> tuple[dict[str, Any], dict[int, dict[str, Any]], dict[int, dict[str, Any]], list[str]]:
    """Derive four disjoint views from one complete process observation."""
    issues: list[str] = []
    universe = snapshot.get("all_processes")
    if snapshot.get("observation_universe_complete") is not True:
        issues.append("OBSERVATION_UNIVERSE_TRUNCATED")
    if snapshot.get("observation_universe_capture_errors") not in ([], None):
        issues.append("OBSERVATION_UNIVERSE_CAPTURE_ERRORS")
    if not isinstance(universe, list):
        universe = []
        issues.append("OBSERVATION_UNIVERSE_MISSING")
    groups = _pid_groups(universe)
    full_index: dict[int, dict[str, Any]] = {}
    for pid, rows in groups.items():
        if len(rows) != 1:
            issues.append(f"OBSERVATION_UNIVERSE_PID_AMBIGUITY:{pid}")
            continue
        full_index[pid] = dict(rows[0])

    runner_pid = runner_record.get("pid")
    runner = full_index.get(int(runner_pid)) if isinstance(runner_pid, int) else None
    _, runner_issues = _runner_matches(runner, runner_record)
    issues.extend(runner_issues)

    rich = _rich_index(snapshot)
    listeners = _listener_map(snapshot)
    known_paths = _known_direct_paths(config)
    candidate_reasons: dict[int, list[str]] = {}
    for pid, source in full_index.items():
        if pid == runner_pid:
            continue
        path = normalized_path(source.get("exe"))
        if path and path in known_paths:
            candidate_reasons.setdefault(pid, []).append("LOCKED_PROJECT_BINARY_PATH")
        controlled = sorted(set(listeners.get(pid, [])) & CONTROLLED_PORTS)
        if controlled:
            candidate_reasons.setdefault(pid, []).append(
                "CONTROLLED_PORT_OWNER:" + ",".join(str(port) for port in controlled)
            )

    candidates: list[dict[str, Any]] = []
    for pid in sorted(candidate_reasons):
        source = {**full_index[pid], **rich.get(pid, {})}
        source["listener_evidence_complete"] = snapshot.get("listener_evidence_complete") is True
        source["listener_ports"] = listeners.get(pid, [])
        source["authorization_candidate_reasons"] = candidate_reasons[pid]
        candidates.append(source)
        full_index[pid] = source

    candidate_pids = set(candidate_reasons)
    support_pids: set[int] = set()
    ancestry: list[dict[str, Any]] = []
    max_depth = int(config["process_identity"]["max_parent_depth"])
    for candidate in candidates:
        child_pid = int(candidate["pid"])
        parent_pid = candidate.get("ppid")
        seen: set[int] = set()
        chain: list[dict[str, Any]] = []
        complete = True
        for _ in range(max_depth):
            if not isinstance(parent_pid, int) or parent_pid <= 0:
                break
            if parent_pid in seen:
                chain.append({"pid": parent_pid, "status": "CYCLE"})
                complete = False
                break
            seen.add(parent_pid)
            parent = full_index.get(parent_pid)
            if parent is None:
                chain.append({"pid": parent_pid, "status": "MISSING"})
                complete = False
                break
            parent_key = identity_key(parent)
            chain.append({"pid": parent_pid, "identity_key": parent_key, "status": "OBSERVED"})
            if parent_pid == runner_pid:
                break
            if parent_pid not in candidate_pids:
                support_pids.add(parent_pid)
            parent_pid = parent.get("ppid")
        else:
            chain.append({"pid": parent_pid, "status": "DEPTH_EXCEEDED"})
            complete = False
        ancestry.append({
            "candidate_pid": child_pid,
            "candidate_identity_key": identity_key(candidate),
            "complete_within_bound": complete,
            "chain": chain,
        })

    support = [dict(full_index[pid]) for pid in sorted(support_pids - candidate_pids) if pid != runner_pid]
    unrelated_pids = set(full_index) - candidate_pids - support_pids
    if isinstance(runner_pid, int):
        unrelated_pids.discard(runner_pid)
    unrelated = [dict(full_index[pid]) for pid in sorted(unrelated_pids)]

    candidate_index = process_index(candidates)
    support_index = process_index(support)
    unrelated_index = process_index(unrelated)
    if set(candidate_index) & set(support_index):
        issues.append("VIEW_OVERLAP:CANDIDATE_SUPPORT")
    if set(candidate_index) & set(unrelated_index):
        issues.append("VIEW_OVERLAP:CANDIDATE_UNRELATED")
    if set(support_index) & set(unrelated_index):
        issues.append("VIEW_OVERLAP:SUPPORT_UNRELATED")
    classified = set(candidate_index) | set(support_index) | set(unrelated_index)
    expected = set(full_index) - ({int(runner_pid)} if isinstance(runner_pid, int) else set())
    if classified != expected:
        issues.append("VIEW_COVERAGE_MISMATCH")
    for record in support:
        owned = sorted(set(listeners.get(int(record["pid"]), [])) & CONTROLLED_PORTS)
        if owned:
            issues.append(f"SUPPORT_NODE_OWNS_CONTROLLED_PORT:{record['pid']}:{owned}")

    root_view = dict(runner) if runner is not None else dict(runner_record)
    root_view["frozen_identity_key"] = identity_key(runner_record)
    root_view["authority"] = "ANCESTRY_ROOT_ONLY"
    root_view["project_role_authority"] = False
    view = {
        "schema_version": "role_binding_timing.infra_m9.process_views.v1",
        "source_snapshot_schema": snapshot.get("schema_version"),
        "source_universe_sha256": canonical_hash(universe),
        "trusted_runner_root": root_view,
        "project_authorization_candidates": candidates,
        "support_only_ancestry_nodes": support,
        "unrelated_observed_processes": unrelated,
        "candidate_ancestry": ancestry,
        "view_hashes": {
            "trusted_runner_root": canonical_hash(root_view),
            "project_authorization_candidates": canonical_hash(candidates),
            "support_only_ancestry_nodes": canonical_hash(support),
            "unrelated_observed_processes": canonical_hash(unrelated),
        },
        "counts": {
            "observation_universe": len(universe),
            "trusted_runner_root": 1 if runner is not None else 0,
            "project_authorization_candidates": len(candidates),
            "support_only_ancestry_nodes": len(support),
            "unrelated_observed_processes": len(unrelated),
        },
        "type_assertions": {
            "views_disjoint": not any(item.startswith("VIEW_OVERLAP") for item in issues),
            "universe_covered": "VIEW_COVERAGE_MISMATCH" not in issues,
            "support_has_no_controlled_port": not any(item.startswith("SUPPORT_NODE_OWNS_CONTROLLED_PORT") for item in issues),
            "support_role_authority": False,
            "unrelated_role_authority": False,
        },
        "issues": sorted(set(issues)),
        "passed": not issues,
    }
    return view, full_index, candidate_index, sorted(set(issues))


def validate_attached_views(snapshot: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    """Reject stale/corrupt prederived views rather than trusting their labels."""
    attached = snapshot.get("process_views")
    if attached is None:
        return []
    if not isinstance(attached, dict):
        return ["ATTACHED_PROCESS_VIEWS_MALFORMED"]
    issues: list[str] = []
    for name in ("trusted_runner_root", *VIEW_NAMES):
        if canonical_hash(attached.get(name)) != canonical_hash(expected.get(name)):
            issues.append(f"ATTACHED_VIEW_MISMATCH:{name}")
    support = attached.get("support_only_ancestry_nodes", [])
    if isinstance(support, list):
        controlled_pids = {
            int(pid)
            for pid, ports in _listener_map(snapshot).items()
            if set(ports) & CONTROLLED_PORTS
        }
        for record in support:
            if isinstance(record, dict) and record.get("pid") in controlled_pids:
                issues.append(f"ATTACHED_SUPPORT_OWNS_CONTROLLED_PORT:{record.get('pid')}")
    return sorted(set(issues))


def build_m9_snapshot(
    *, gate: str, sequence: int, cache: ExecutableHashCache,
    config: dict[str, Any], runner_record: dict[str, Any],
    raw_processes: list[dict[str, Any]] | None = None,
    raw_netstat: bytes | None = None,
) -> dict[str, Any]:
    processes = raw_processes if raw_processes is not None else snapshot_processes()
    network = raw_netstat if raw_netstat is not None else netstat_bytes()
    value = build_m8_snapshot(
        gate=gate, sequence=sequence, cache=cache,
        raw_processes=processes, raw_netstat=network,
    )
    value["schema_version"] = "role_binding_timing.infra_m9.process_snapshot.v1"
    view, _, _, _ = derive_process_views(value, config=config, runner_record=runner_record)
    value["process_views"] = view
    value["view_contract"] = {
        "observation_universe": "all_processes",
        "trusted_runner_root": "process_views.trusted_runner_root",
        "project_authorization_candidates": "process_views.project_authorization_candidates",
        "support_only_ancestry_nodes": "process_views.support_only_ancestry_nodes",
        "unrelated_observed_processes": "process_views.unrelated_observed_processes",
        "role_policy_input": "project_authorization_candidates_only",
    }
    return value


class M9StructuralIdentityPolicy(M8StructuralIdentityPolicy):
    """Apply role policies only to the explicit project-candidate view."""

    def _derive(self, snapshot: dict[str, Any]) -> tuple[dict[str, Any], dict[int, dict[str, Any]], dict[int, dict[str, Any]], list[str]]:
        view, universe, candidates, issues = derive_process_views(
            snapshot, config=self.config, runner_record=self.runner_record,
        )
        issues.extend(validate_attached_views(snapshot, view))
        issues.extend(snapshot.get("process_view_input_validation_issues", []))
        return view, universe, candidates, sorted(set(issues))

    def freeze_baseline(self, snapshot: dict[str, Any]) -> None:
        if self.baseline:
            raise RuntimeError("BASELINE_ALREADY_FROZEN")
        _, _, candidates, issues = self._derive(snapshot)
        if issues:
            raise RuntimeError(f"BASELINE_VIEW_INVALID:{issues}")
        for record in candidates.values():
            key = identity_key(record)
            if key is None:
                raise RuntimeError(f"BASELINE_CANDIDATE_IDENTITY_MISSING:{record.get('pid')}")
            self.baseline[key] = dict(record)
            self.baseline_by_pid[int(record["pid"])] = key
        self.add_history(candidates.values())

    def evaluate(
        self, snapshot: dict[str, Any], *, phase: str,
        recent_records: Iterable[dict[str, Any]] = (), allow_core_exit: bool = False,
    ) -> Evaluation:
        view, universe_current, candidate_current, issues = self._derive(snapshot)
        roles: dict[str, str] = {}
        helper_ancestry: dict[str, list[str]] = {}
        listeners = snapshot.get("listeners", {})
        if listeners.get("5037"):
            issues.append(f"FORBIDDEN_5037:{listeners['5037']}")
        if issues:
            return Evaluation(False, sorted(set(issues)), roles, helper_ancestry)

        recent = list(recent_records)
        combined: dict[str, dict[str, Any]] = {}
        for record in [*candidate_current.values(), *recent]:
            key = identity_key(record)
            if key:
                combined[key] = record
        self.add_history(candidate_current.values())
        self.add_history(recent)

        for role, expected in self.core.items():
            pid = int(expected["pid"])
            observed = candidate_current.get(pid)
            if observed is None and allow_core_exit:
                continue
            if observed is None:
                issues.append(f"CORE_MISSING:{role}:{pid}")
                continue
            if identity_key(observed) != identity_key(expected):
                issues.append(f"CORE_PID_REUSE:{role}:{pid}")
                continue
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
                roles[key] = "preexisting_candidate_no_authority"
                continue
            baseline_key = self.baseline_by_pid.get(pid)
            if baseline_key and baseline_key != key:
                issues.append(f"PID_REUSE:{pid}:{baseline_key}:{key}")
                continue
            if key in core_keys:
                continue
            role, role_issues, chain = self._classify_new(record, phase, universe_current)
            if role:
                roles[key] = role
                helper_ancestry[key] = chain
            else:
                issues.extend(f"PROCESS:{key}:{item}" for item in role_issues)
                if chain:
                    helper_ancestry[key] = chain

        candidate_keys = set(combined)
        unauthorized_role_keys = set(roles) - candidate_keys
        if unauthorized_role_keys:
            issues.append(f"ROLE_ASSIGNED_OUTSIDE_CANDIDATE_VIEW:{sorted(unauthorized_role_keys)}")
        support_keys = {identity_key(row) for row in view["support_only_ancestry_nodes"] if identity_key(row)}
        unrelated_keys = {identity_key(row) for row in view["unrelated_observed_processes"] if identity_key(row)}
        if set(roles) & (support_keys | unrelated_keys):
            issues.append("SUPPORT_OR_UNRELATED_GRANTED_ROLE")
        return Evaluation(not issues, sorted(set(issues)), roles, helper_ancestry)


class M9ContinuousProcessHistory:
    """Persist the full observation universe and four derived views; retain only candidates for role history."""

    def __init__(
        self, root: Path, cache: ExecutableHashCache, *, interval_seconds: float,
        config: dict[str, Any], runner_record: dict[str, Any],
    ) -> None:
        self.root = root.resolve()
        self.cache = cache
        self.interval_seconds = interval_seconds
        self.config = config
        self.runner_record = runner_record
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
        self._thread = threading.Thread(target=self._run, name="infra-m9-disjoint-view-history", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                captured = time.monotonic()
                raw = snapshot_processes()
                network = netstat_bytes()
                snapshot = build_m8_snapshot(
                    gate="continuous_history", sequence=self._samples + 1, cache=self.cache,
                    raw_processes=raw, raw_netstat=network,
                )
                view, _, _, issues = derive_process_views(
                    snapshot, config=self.config, runner_record=self.runner_record,
                )
                if issues:
                    raise RuntimeError(f"PROCESS_VIEW_DERIVATION:{issues}")
                candidates = view["project_authorization_candidates"]
                current: set[str] = set()
                with self._lock:
                    for source in candidates:
                        key = identity_key(source)
                        if key is None:
                            continue
                        current.add(key)
                        prior = self._records.get(key, {})
                        record = dict(source)
                        record["history_first_seen_monotonic"] = prior.get("history_first_seen_monotonic", captured)
                        record["history_last_seen_monotonic"] = captured
                        record["history_exit_observed"] = False
                        record["history_max_listener_ports"] = sorted(
                            set(prior.get("history_max_listener_ports", [])) | set(record.get("listener_ports", []))
                        )
                        self._records[key] = record
                    for key in self._active - current:
                        if key in self._records:
                            self._records[key]["history_exit_observed"] = True
                            self._records[key]["history_exit_observed_monotonic"] = captured
                    self._active = current
                    self._samples += 1
                    compact = compact_identity_universe(raw)
                    event = {
                        "schema_version": "role_binding_timing.infra_m9.process_history_sample.v1",
                        "captured_at": utc_now(),
                        "captured_monotonic": captured,
                        "sample": self._samples,
                        "observation_identity_universe": compact,
                        "observation_identity_universe_sha256": canonical_hash(compact),
                        "trusted_runner_root": view["trusted_runner_root"],
                        "project_authorization_candidates": candidates,
                        "support_only_ancestry_nodes": compact_identity_universe(view["support_only_ancestry_nodes"]),
                        "unrelated_observed_processes": compact_identity_universe(view["unrelated_observed_processes"]),
                        "view_hashes": view["view_hashes"],
                        "view_type_assertions": view["type_assertions"],
                        "all_tcp_listener_ports_by_pid": {
                            str(pid): ports for pid, ports in listener_ports_by_pid(network).items()
                        },
                        "raw_netstat_sha256": sha256(network).hexdigest(),
                    }
                    with self._ndjson.open("ab") as handle:
                        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n")
                        handle.flush()
                        os.fsync(handle.fileno())
            except Exception as exc:
                with self._lock:
                    self._errors.append(f"{type(exc).__name__}:{exc}")
            self._stop.wait(self.interval_seconds)

    def records(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(value) for value in self._records.values()]

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "samples": self._samples,
                "errors": list(self._errors),
                "records": len(self._records),
                "active": len(self._active),
                "history_authority_view": "project_authorization_candidates_only",
            }

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


class M9ProcessIdentityMonitor(M8ProcessIdentityMonitor):
    """Use and persist disjoint views at every gate and failure."""

    def __init__(
        self, *, root: Path, config: dict[str, Any], runner_record: dict[str, Any],
        snapshot_provider: Callable[[str, int, ExecutableHashCache], tuple[dict[str, Any], bytes]] | None = None,
    ) -> None:
        super().__init__(root=root, config=config, runner_record=runner_record, snapshot_provider=snapshot_provider)
        self.policy = M9StructuralIdentityPolicy(config, runner_record=runner_record)
        self.history = M9ContinuousProcessHistory(
            self.root / "continuous_history", self.cache,
            interval_seconds=config["process_identity"]["continuous_sample_interval_seconds"],
            config=config, runner_record=runner_record,
        )

    def _default_snapshot(self, gate: str, sequence: int, cache: ExecutableHashCache) -> tuple[dict[str, Any], bytes]:
        raw = netstat_bytes()
        return build_m9_snapshot(
            gate=gate, sequence=sequence, cache=cache, config=self.policy.config,
            runner_record=self.policy.runner_record, raw_netstat=raw,
        ), raw

    def _prepare_snapshot(self, snapshot: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
        expected, _, _, issues = derive_process_views(
            snapshot, config=self.policy.config, runner_record=self.policy.runner_record,
        )
        input_issues = validate_attached_views(snapshot, expected)
        value = dict(snapshot)
        value["schema_version"] = "role_binding_timing.infra_m9.process_snapshot.v1"
        value["process_view_input_validation_issues"] = input_issues
        value["process_views"] = expected
        value["view_contract"] = {
            "observation_universe": "all_processes",
            "trusted_runner_root": "process_views.trusted_runner_root",
            "project_authorization_candidates": "process_views.project_authorization_candidates",
            "support_only_ancestry_nodes": "process_views.support_only_ancestry_nodes",
            "unrelated_observed_processes": "process_views.unrelated_observed_processes",
            "role_policy_input": "project_authorization_candidates_only",
        }
        return value, expected, sorted(set(issues + input_issues))

    def capture(self, *, gate: str, phase: str, mode: str = "enforce") -> dict[str, Any]:
        self.sequence += 1
        supplied, raw = self.snapshot_provider(gate, self.sequence, self.cache)
        snapshot, view, view_issues = self._prepare_snapshot(supplied)
        root = self.root / "snapshots" / f"{self.sequence:04d}_{gate}"
        saved = save_snapshot(root, snapshot, raw)
        view_record = atomic_write_json(root / "derived_process_views.json", view, replace=False)
        candidates = view["project_authorization_candidates"]
        if mode == "baseline":
            issues = list(view_issues)
            if any(snapshot.get("listeners", {}).get(str(port)) for port in CONTROLLED_PORTS):
                issues.append("BASELINE_LISTENER_PRESENT")
            if issues:
                evaluation = Evaluation(False, sorted(set(issues)), {}, {})
            else:
                self.policy.freeze_baseline(snapshot)
                evaluation = Evaluation(
                    True, [], {key: "preexisting_candidate_no_authority" for key in self.policy.baseline}, {},
                )
        elif mode == "discovery":
            issues = list(view_issues)
            if snapshot.get("listeners", {}).get("5037"):
                issues.append(f"FORBIDDEN_5037:{snapshot['listeners']['5037']}")
            if not issues:
                self.policy.add_history(candidates)
                self.policy.add_history(self.history.records())
            evaluation = Evaluation(not issues, sorted(set(issues)), {}, {})
        elif mode == "cleanup_after_exit":
            evaluation = self.policy.evaluate(
                snapshot, phase=phase, recent_records=self.history.records(), allow_core_exit=True,
            )
        else:
            evaluation = self.policy.evaluate(
                snapshot, phase=phase, recent_records=self.history.records(),
            )
        result = {
            "schema_version": "role_binding_timing.infra_m9.process_evaluation.v1",
            "passed": evaluation.passed,
            "issues": evaluation.issues,
            "roles": evaluation.roles,
            "helper_ancestry": evaluation.helper_ancestry,
            "runner_client_ledger": dict(self.policy.authorized_runner_clients),
            "snapshot": saved["record"],
            "derived_process_views": view_record,
            "view_type_assertions": view["type_assertions"],
            "snapshot_sequence": self.sequence,
            "gate": gate,
            "phase": phase,
        }
        atomic_write_json(root / "evaluation.json", result, replace=False)
        if not evaluation.passed and not self.first_failure.exists():
            atomic_write_json(self.first_failure, {
                "schema_version": "role_binding_timing.infra_m9.first_process_identity_failure.v1",
                "recorded_at": utc_now(),
                "gate": gate,
                "phase": phase,
                "issues": evaluation.issues,
                "roles": evaluation.roles,
                "helper_ancestry": evaluation.helper_ancestry,
                "runner_client_ledger": dict(self.policy.authorized_runner_clients),
                "triggering_snapshot": saved["snapshot"],
                "derived_process_views": view,
                "derived_process_views_record": view_record,
                "continuous_history_status": self.history.status(),
            }, replace=False)
        return result

    def register_core_from_snapshot(self, *, role: str, snapshot_path: Path, pid: int) -> dict[str, Any]:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        view, _, candidates, issues = self.policy._derive(snapshot)
        if issues:
            raise RuntimeError(f"CORE_REGISTRATION_VIEW_INVALID:{issues}")
        record = candidates.get(pid)
        if record is None:
            support = process_index(view["support_only_ancestry_nodes"])
            unrelated = process_index(view["unrelated_observed_processes"])
            if pid in support:
                raise RuntimeError(f"CORE_PID_IS_SUPPORT_ONLY:{role}:{pid}")
            if pid in unrelated:
                raise RuntimeError(f"CORE_PID_IS_UNRELATED:{role}:{pid}")
            raise RuntimeError(f"CORE_PID_NOT_IN_CANDIDATE_VIEW:{role}:{pid}")
        self.policy.register_core(role, record)
        return record
