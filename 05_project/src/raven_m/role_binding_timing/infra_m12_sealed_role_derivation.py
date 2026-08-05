"""Sealed role derivation and run-local temporal attestation for INFRA-M12.

Roles are never accepted from raw process rows. Every authorization decision
is recomputed from a complete atomic process snapshot and locked inputs. This
module contains no task, application, coordinate, model, or live-runtime code.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import threading
from typing import Any, Iterable, Mapping, Sequence

from raven_m.role_binding_timing.infra_m5_process_identity import (
    normalized_command,
    normalized_path,
)
from raven_m.role_binding_timing.infra_m9_authorization_views import (
    derive_process_views as derive_m9_process_views,
)


CLASSIFIER_VERSION = "infra-m12-derive-authorization-views-v1"
CLASSIFIER_CONTRACT_SHA256 = "973192F1D6153F099D9BCC38E784B4C9E2F5203F9CAC77910B349BCCE31D70A0"
DEFAULT_CONTROLLED_PORTS = (5037, 5038, 5554, 5555, 8554)
MAX_PARENT_DEPTH = 12
VIEW_NAMES = (
    "trusted_runner_root",
    "project_authorization_candidates",
    "support_only_ancestry_nodes",
    "unrelated_observed_processes",
)
FORBIDDEN_RAW_AUTHORITY_FIELDS = frozenset(
    {
        "role",
        "observed_class",
        "view_class",
        "authority",
        "role_authority",
        "authorization_candidate_reasons",
        "trusted_runner",
        "adoptable",
        "kill_target",
        "cleanup_target",
    }
)
DERIVED_PROOF_FIELDS = frozenset(
    {
        "source_record_sha256",
        "raw_snapshot_sha256",
        "partition_sha256",
        "sample_sequence",
        "sample_time_utc",
        "role_authority",
        "adoptable",
        "kill_target",
        "cleanup_target",
        "authorization_candidate_reasons",
    }
)


class AuthorizationViewError(RuntimeError):
    """Fail-closed authorization-view error carrying a stable code."""

    def __init__(self, code: str, detail: str | None = None):
        self.code = code
        self.detail = detail
        super().__init__(code if detail is None else f"{code}:{detail}")


class TemporalAttestationError(RuntimeError):
    """Fail-closed temporal-attestation error carrying a stable code."""

    def __init__(self, code: str, detail: str | None = None):
        self.code = code
        self.detail = detail
        super().__init__(code if detail is None else f"{code}:{detail}")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest().upper()


def implementation_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()


def implementation_blob_oid() -> str:
    raw = Path(__file__).read_bytes()
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw, usedforsecurity=False).hexdigest()


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _identity_tuple(record: Mapping[str, Any]) -> tuple[int, float]:
    pid = record.get("pid")
    created = record.get("create_time")
    if not _is_int(pid):
        raise AuthorizationViewError("MISSING_PID")
    if not _is_number(created):
        raise AuthorizationViewError("MISSING_CREATE_TIME")
    return int(pid), float(created)


def _identity_text(identity: tuple[int, float]) -> str:
    return f"{identity[0]}@{identity[1]:.6f}"


def _coerce_identity(value: Any) -> tuple[int, float]:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        pid, created = value
        if _is_int(pid) and _is_number(created):
            return int(pid), float(created)
    if isinstance(value, str) and "@" in value:
        pid_text, created_text = value.split("@", 1)
        try:
            return int(pid_text), float(created_text)
        except ValueError:
            pass
    raise AuthorizationViewError("INVALID_IDENTITY_KEY")


def _sample_metadata(raw_snapshot: Mapping[str, Any]) -> tuple[int, str]:
    sequence = raw_snapshot.get("sample_sequence", raw_snapshot.get("sequence"))
    timestamp = raw_snapshot.get("sample_time_utc", raw_snapshot.get("captured_at"))
    if not _is_int(sequence):
        raise AuthorizationViewError("MISSING_SAMPLE_SEQUENCE")
    if not isinstance(timestamp, str) or not timestamp.strip():
        raise AuthorizationViewError("MISSING_SAMPLE_TIME")
    if "sample_sequence" in raw_snapshot and "sequence" in raw_snapshot:
        if raw_snapshot["sample_sequence"] != raw_snapshot["sequence"]:
            raise AuthorizationViewError("SAMPLE_SEQUENCE_CONFLICT")
    if "sample_time_utc" in raw_snapshot and "captured_at" in raw_snapshot:
        if raw_snapshot["sample_time_utc"] != raw_snapshot["captured_at"]:
            raise AuthorizationViewError("SAMPLE_TIME_CONFLICT")
    return int(sequence), timestamp.strip()


def _normalized_hash(value: Any) -> str:
    return str(value or "").strip().upper()


def _field_conflicts(field: str, left: Any, right: Any) -> bool:
    if left in (None, "", []) or right in (None, "", []):
        return False
    if field == "exe":
        return normalized_path(str(left)) != normalized_path(str(right))
    if field in {"command_line", "cmdline_items"}:
        return normalized_command(left) != normalized_command(right)
    if field == "exe_sha256":
        return _normalized_hash(left) != _normalized_hash(right)
    return left != right


def _validate_no_authority_labels(rows: Iterable[Mapping[str, Any]]) -> None:
    for row in rows:
        forbidden = sorted(FORBIDDEN_RAW_AUTHORITY_FIELDS & set(row))
        if forbidden:
            raise AuthorizationViewError("RAW_AUTHORITY_LABEL_PRESENT", ",".join(forbidden))


def _index_complete_universe(rows: Any) -> tuple[dict[int, dict[str, Any]], dict[int, tuple[int, float]]]:
    if not isinstance(rows, list):
        raise AuthorizationViewError("OBSERVATION_UNIVERSE_MISSING")
    by_pid: dict[int, dict[str, Any]] = {}
    identities: dict[int, tuple[int, float]] = {}
    for raw in rows:
        if not isinstance(raw, dict):
            raise AuthorizationViewError("PROCESS_RECORD_MALFORMED")
        identity = _identity_tuple(raw)
        pid = identity[0]
        if pid in by_pid:
            if identities[pid] != identity:
                raise AuthorizationViewError("PID_CREATE_TIME_REUSE")
            raise AuthorizationViewError("DUPLICATE_PID")
        by_pid[pid] = copy.deepcopy(raw)
        identities[pid] = identity
    return by_pid, identities


def _index_structural(rows: Any) -> tuple[dict[int, dict[str, Any]], dict[int, tuple[int, float]]]:
    if not isinstance(rows, list):
        raise AuthorizationViewError("STRUCTURAL_PROCESS_SOURCE_MISSING")
    by_pid: dict[int, dict[str, Any]] = {}
    identities: dict[int, tuple[int, float]] = {}
    for raw in rows:
        if not isinstance(raw, dict):
            raise AuthorizationViewError("STRUCTURAL_PROCESS_RECORD_MALFORMED")
        identity = _identity_tuple(raw)
        pid = identity[0]
        if pid in by_pid:
            if identities[pid] != identity:
                raise AuthorizationViewError("PID_CREATE_TIME_REUSE")
            raise AuthorizationViewError("DUPLICATE_STRUCTURAL_PID")
        by_pid[pid] = copy.deepcopy(raw)
        identities[pid] = identity
    return by_pid, identities


def _merge_sources(raw_snapshot: Mapping[str, Any]) -> tuple[dict[int, dict[str, Any]], int, str, str]:
    if raw_snapshot.get("observation_universe_complete") is not True:
        raise AuthorizationViewError("OBSERVATION_UNIVERSE_TRUNCATED")
    capture_errors = raw_snapshot.get("observation_universe_capture_errors")
    if capture_errors not in ([], None):
        raise AuthorizationViewError("OBSERVATION_UNIVERSE_CAPTURE_ERRORS")
    if raw_snapshot.get("listener_evidence_complete") is not True:
        raise AuthorizationViewError("LISTENER_EVIDENCE_INCOMPLETE")
    sequence, timestamp = _sample_metadata(raw_snapshot)
    all_rows = raw_snapshot.get("all_processes")
    structural_rows = raw_snapshot.get("structural_processes")
    if not isinstance(all_rows, list) or not isinstance(structural_rows, list):
        raise AuthorizationViewError("PROCESS_SOURCE_MISSING")
    _validate_no_authority_labels(all_rows)
    _validate_no_authority_labels(structural_rows)
    universe, universe_identities = _index_complete_universe(all_rows)
    structural, structural_identities = _index_structural(structural_rows)

    for pid, rich in structural.items():
        if pid not in universe:
            raise AuthorizationViewError("UNIVERSE_RECORD_OMISSION", str(pid))
        if universe_identities[pid] != structural_identities[pid]:
            raise AuthorizationViewError("PID_CREATE_TIME_REUSE", str(pid))
        base = universe[pid]
        for field in ("ppid", "exe", "exe_sha256", "command_line", "cmdline_items"):
            if field in base and field in rich and _field_conflicts(field, base[field], rich[field]):
                raise AuthorizationViewError("PROCESS_SOURCE_FIELD_CONFLICT", f"{pid}:{field}")
        merged = dict(base)
        for key, value in rich.items():
            if value not in (None, "", []):
                merged[key] = copy.deepcopy(value)
            elif key not in merged:
                merged[key] = copy.deepcopy(value)
        universe[pid] = merged

    raw_hash = canonical_sha256(raw_snapshot)
    for record in universe.values():
        identity = _identity_tuple(record)
        record["identity_key"] = _identity_text(identity)
        source_payload = {key: value for key, value in record.items() if key not in DERIVED_PROOF_FIELDS}
        record["source_record_sha256"] = canonical_sha256(source_payload)
        record["raw_snapshot_sha256"] = raw_hash
        record["sample_sequence"] = sequence
        record["sample_time_utc"] = timestamp
    return universe, sequence, timestamp, raw_hash


def _listener_map(raw_snapshot: Mapping[str, Any], universe: Mapping[int, Mapping[str, Any]]) -> dict[int, list[int]]:
    raw = raw_snapshot.get("all_tcp_listener_ports_by_pid")
    if not isinstance(raw, dict):
        raise AuthorizationViewError("LISTENER_EVIDENCE_MALFORMED")
    result: dict[int, list[int]] = {}
    for pid_value, ports_value in raw.items():
        try:
            pid = int(pid_value)
        except (TypeError, ValueError) as exc:
            raise AuthorizationViewError("LISTENER_PID_MALFORMED") from exc
        if pid not in universe:
            raise AuthorizationViewError("LISTENER_OWNER_NOT_IN_UNIVERSE", str(pid))
        if not isinstance(ports_value, list) or not all(_is_int(port) for port in ports_value):
            raise AuthorizationViewError("LISTENER_PORTS_MALFORMED", str(pid))
        result[pid] = sorted(set(int(port) for port in ports_value))
    return result


def _normalize_controlled_ports(ports: Sequence[int]) -> tuple[int, ...]:
    if not isinstance(ports, (list, tuple)) or not ports:
        raise AuthorizationViewError("CONTROLLED_PORT_SET_MALFORMED")
    if not all(_is_int(port) and 0 < int(port) <= 65535 for port in ports):
        raise AuthorizationViewError("CONTROLLED_PORT_SET_MALFORMED")
    normalized = tuple(sorted(set(int(port) for port in ports)))
    if len(normalized) != len(ports):
        raise AuthorizationViewError("CONTROLLED_PORT_SET_DUPLICATE")
    return normalized


def _normalize_known_paths(entries: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if not isinstance(entries, (list, tuple)):
        raise AuthorizationViewError("LOCKED_KNOWN_PATHS_MALFORMED")
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise AuthorizationViewError("LOCKED_KNOWN_PATH_ENTRY_MALFORMED")
        logical_role = entry.get("logical_role")
        path = entry.get("normalized_path")
        digest = entry.get("exe_sha256")
        if not isinstance(logical_role, str) or not logical_role:
            raise AuthorizationViewError("LOCKED_KNOWN_PATH_ENTRY_MALFORMED")
        if not isinstance(path, str) or not normalized_path(path):
            raise AuthorizationViewError("LOCKED_KNOWN_PATH_ENTRY_MALFORMED")
        if not isinstance(digest, str) or len(digest.strip()) != 64:
            raise AuthorizationViewError("LOCKED_KNOWN_PATH_ENTRY_MALFORMED")
        pair = (normalized_path(path), _normalized_hash(digest))
        if pair in seen:
            raise AuthorizationViewError("LOCKED_KNOWN_PATH_DUPLICATE")
        seen.add(pair)
        result.append(
            {
                "logical_role": logical_role,
                "normalized_path": pair[0],
                "exe_sha256": pair[1],
            }
        )
    return sorted(result, key=lambda item: (item["normalized_path"], item["exe_sha256"], item["logical_role"]))


def _derive_m9_compatibility_replay(
    raw_snapshot: Mapping[str, Any],
    locked_runner_record: Mapping[str, Any],
    locked_known_paths: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Replay the locked M9 classifier without producing authority-eligible output."""

    all_rows = raw_snapshot.get("all_processes")
    structural_rows = raw_snapshot.get("structural_processes")
    if not isinstance(all_rows, list) or not isinstance(structural_rows, list):
        raise AuthorizationViewError("PROCESS_SOURCE_MISSING")
    _validate_no_authority_labels(all_rows)
    _validate_no_authority_labels(structural_rows)
    if raw_snapshot.get("observation_universe_complete") is not True:
        raise AuthorizationViewError("OBSERVATION_UNIVERSE_TRUNCATED")
    if raw_snapshot.get("observation_universe_capture_errors") not in ([], None):
        raise AuthorizationViewError("OBSERVATION_UNIVERSE_CAPTURE_ERRORS")
    if raw_snapshot.get("listener_evidence_complete") is not True:
        raise AuthorizationViewError("LISTENER_EVIDENCE_INCOMPLETE")
    sequence, timestamp = _sample_metadata(raw_snapshot)
    known = _normalize_known_paths(locked_known_paths)
    required_roles = {"adb", "emulator_launcher", "qemu", "crashpad", "netsimd"}
    by_role = {entry["logical_role"]: entry for entry in known}
    if not required_roles <= set(by_role):
        raise AuthorizationViewError("M9_COMPATIBILITY_LOCKED_PATHS_INCOMPLETE")
    compatibility_config = {
        "process_identity": {
            "max_parent_depth": MAX_PARENT_DEPTH,
            "binaries": {
                role: {"path": by_role[role]["normalized_path"]}
                for role in sorted(required_roles)
            },
        }
    }
    view, _, _, issues = derive_m9_process_views(
        dict(raw_snapshot),
        config=compatibility_config,
        runner_record=dict(locked_runner_record),
    )
    return {
        "schema_version": "role_binding_timing.infra_m12.m9_compatibility_replay.v1",
        "classifier_version": CLASSIFIER_VERSION,
        "classifier_contract_sha256": CLASSIFIER_CONTRACT_SHA256,
        "classifier_implementation_sha256": implementation_sha256(),
        "compatibility_replay_only": True,
        "authority_eligible": False,
        "raw_snapshot_sha256": canonical_sha256(raw_snapshot),
        "sample_sequence": sequence,
        "sample_time_utc": timestamp,
        "trusted_runner_root": [copy.deepcopy(view["trusted_runner_root"])],
        "project_authorization_candidates": copy.deepcopy(view["project_authorization_candidates"]),
        "support_only_ancestry_nodes": copy.deepcopy(view["support_only_ancestry_nodes"]),
        "unrelated_observed_processes": copy.deepcopy(view["unrelated_observed_processes"]),
        "candidate_ancestry": copy.deepcopy(view["candidate_ancestry"]),
        "type_assertions": {
            "views_disjoint": view["type_assertions"]["views_disjoint"],
            "universe_covered": view["type_assertions"]["universe_covered"],
            "support_role_authority": False,
            "support_controlled_port_owner": view["type_assertions"]["support_has_no_controlled_port"],
            "caller_role_labels_used": False,
            "compatibility_replay_issues": list(issues),
        },
        "input_hashes": {
            "locked_runner_record_sha256": canonical_sha256(locked_runner_record),
            "locked_known_paths_sha256": canonical_sha256(known),
            "controlled_ports_sha256": canonical_sha256(list(DEFAULT_CONTROLLED_PORTS)),
            "controlled_port_evidence_sha256": canonical_sha256(
                raw_snapshot.get("all_tcp_listener_ports_by_pid", {})
            ),
        },
        "raw_identity_by_pid": {
            str(row["pid"]): (
                _identity_text((int(row["pid"]), float(row["create_time"])))
                if _is_int(row.get("pid")) and _is_number(row.get("create_time"))
                else None
            )
            for row in all_rows
            if _is_int(row.get("pid"))
        },
    }


def _critical_record(record: Mapping[str, Any]) -> None:
    _identity_tuple(record)
    if not isinstance(record.get("exe"), str) or not record.get("exe"):
        raise AuthorizationViewError("MISSING_EXE")
    digest = record.get("exe_sha256")
    if not isinstance(digest, str) or len(digest.strip()) != 64:
        raise AuthorizationViewError("MISSING_EXE_SHA256")
    command = record.get("command_line", record.get("cmdline_items"))
    if command in (None, "", []):
        raise AuthorizationViewError("MISSING_COMMAND_LINE")
    access_status = str(record.get("accessibility_status") or "").casefold()
    access_error = record.get("access_error")
    if access_status == "access_denied" or access_error not in (None, ""):
        raise AuthorizationViewError("CRITICAL_FIELD_ACCESS_DENIED")


def _runner_match(
    universe: Mapping[int, Mapping[str, Any]],
    locked_runner_record: Mapping[str, Any],
    *,
    compatibility_replay: bool,
) -> dict[str, Any]:
    locked_identity = _identity_tuple(locked_runner_record)
    observed = universe.get(locked_identity[0])
    if observed is None or _identity_tuple(observed) != locked_identity:
        raise AuthorizationViewError("LOCKED_RUNNER_IDENTITY_MISMATCH")
    if normalized_path(observed.get("exe")) != normalized_path(locked_runner_record.get("exe")):
        raise AuthorizationViewError("LOCKED_RUNNER_IDENTITY_MISMATCH")
    if normalized_command(observed.get("command_line", observed.get("cmdline_items"))) != normalized_command(
        locked_runner_record.get("command_line", locked_runner_record.get("cmdline_items"))
    ):
        raise AuthorizationViewError("LOCKED_RUNNER_IDENTITY_MISMATCH")
    locked_hash = _normalized_hash(locked_runner_record.get("exe_sha256"))
    observed_hash = _normalized_hash(observed.get("exe_sha256"))
    if locked_hash:
        if observed_hash != locked_hash:
            raise AuthorizationViewError("LOCKED_RUNNER_IDENTITY_MISMATCH")
    elif not compatibility_replay:
        raise AuthorizationViewError("MISSING_EXE_SHA256")
    _critical_record(observed) if not compatibility_replay else None
    return copy.deepcopy(observed)


def _record_for_view(record: Mapping[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(dict(record))
    value["role_authority"] = False
    value["adoptable"] = False
    value["kill_target"] = False
    value["cleanup_target"] = False
    return value


def _view_identities(rows: Iterable[Mapping[str, Any]]) -> set[tuple[int, float]]:
    return {_identity_tuple(row) for row in rows}


def derive_authorization_views(
    raw_snapshot: Mapping[str, Any],
    locked_runner_record: Mapping[str, Any],
    locked_known_paths: Sequence[Mapping[str, Any]],
    controlled_ports: Sequence[int],
    classifier_version: str,
    classifier_contract_sha256: str,
    classifier_implementation_sha256: str,
) -> dict[str, Any]:
    """Derive four disjoint views without trusting caller-supplied roles."""

    if classifier_version != CLASSIFIER_VERSION:
        raise AuthorizationViewError("CLASSIFIER_VERSION_MISMATCH")
    if _normalized_hash(classifier_contract_sha256) != CLASSIFIER_CONTRACT_SHA256:
        raise AuthorizationViewError("CLASSIFIER_CONTRACT_HASH_MISMATCH")
    if _normalized_hash(classifier_implementation_sha256) != implementation_sha256():
        raise AuthorizationViewError("CLASSIFIER_IMPLEMENTATION_HASH_MISMATCH")
    if not isinstance(raw_snapshot, Mapping) or not isinstance(locked_runner_record, Mapping):
        raise AuthorizationViewError("DERIVATION_INPUT_MALFORMED")

    compatibility_replay = str(raw_snapshot.get("schema_version") or "").startswith(
        "role_binding_timing.infra_m9."
    ) and not _normalized_hash(locked_runner_record.get("exe_sha256"))
    if compatibility_replay:
        return _derive_m9_compatibility_replay(
            raw_snapshot,
            locked_runner_record,
            locked_known_paths,
        )
    universe, sequence, timestamp, raw_hash = _merge_sources(raw_snapshot)
    listeners = _listener_map(raw_snapshot, universe)
    ports = _normalize_controlled_ports(controlled_ports)
    known = _normalize_known_paths(locked_known_paths)
    runner = _runner_match(universe, locked_runner_record, compatibility_replay=False)
    runner_pid = _identity_tuple(runner)[0]

    known_pairs = {(item["normalized_path"], item["exe_sha256"]) for item in known}
    candidate_reasons: dict[int, list[str]] = {}
    for pid, record in universe.items():
        if pid == runner_pid:
            continue
        pair = (normalized_path(record.get("exe")), _normalized_hash(record.get("exe_sha256")))
        if pair in known_pairs:
            candidate_reasons.setdefault(pid, []).append("LOCKED_PROJECT_BINARY_PATH_AND_HASH")
        owned = sorted(set(listeners.get(pid, [])) & set(ports))
        if owned:
            candidate_reasons.setdefault(pid, []).append(
                "CONTROLLED_PORT_OWNER:" + ",".join(str(port) for port in owned)
            )

    candidate_pids = set(candidate_reasons)
    ancestry: list[dict[str, Any]] = []
    proven_support_pids: set[int] = set()
    for candidate_pid in sorted(candidate_pids):
        candidate = universe[candidate_pid]
        chain: list[dict[str, Any]] = []
        provisional_support: set[int] = set()
        seen: set[int] = set()
        parent_pid = candidate.get("ppid")
        complete = False
        failure = None
        for _ in range(MAX_PARENT_DEPTH):
            if not _is_int(parent_pid) or int(parent_pid) <= 0:
                failure = "MISSING"
                break
            parent_pid = int(parent_pid)
            if parent_pid in seen:
                failure = "CYCLE"
                break
            seen.add(parent_pid)
            parent = universe.get(parent_pid)
            if parent is None:
                failure = "MISSING"
                chain.append({"pid": parent_pid, "status": "MISSING"})
                break
            chain.append(
                {
                    "pid": parent_pid,
                    "identity_key": _identity_text(_identity_tuple(parent)),
                    "status": "OBSERVED",
                    "sample_sequence": sequence,
                    "sample_time_utc": timestamp,
                }
            )
            if parent_pid == runner_pid:
                complete = True
                break
            if parent_pid not in candidate_pids:
                provisional_support.add(parent_pid)
            parent_pid = parent.get("ppid")
        else:
            failure = "DEPTH_EXCEEDED"
        if complete:
            proven_support_pids.update(provisional_support)
        ancestry.append(
            {
                "candidate_pid": candidate_pid,
                "candidate_identity_key": _identity_text(_identity_tuple(candidate)),
                "complete_within_bound": complete,
                "failure": failure,
                "chain": chain,
                "sample_sequence": sequence,
                "sample_time_utc": timestamp,
            }
        )

    if candidate_pids and not any(row["complete_within_bound"] for row in ancestry):
        # If a candidate has an otherwise observable ancestry chain that reaches
        # a different root, the caller-supplied runner is not the locked root.
        # A chain missing at its first parent remains a distinct missing-chain
        # condition and is rejected by attestation issuance.
        if any(any(node.get("status") == "OBSERVED" for node in row["chain"]) for row in ancestry):
            raise AuthorizationViewError("LOCKED_RUNNER_IDENTITY_MISMATCH")

    for ancestry_row in ancestry:
        for node in ancestry_row["chain"]:
            pid = node.get("pid")
            if pid in candidate_pids and pid != runner_pid:
                owned = sorted(set(listeners.get(pid, [])) & set(ports))
                if owned and pid not in {
                    row["candidate_pid"] for row in ancestry if row["candidate_pid"] == pid
                }:
                    raise AuthorizationViewError("SUPPORT_CONTROLLED_PORT_CONFLICT")
                candidate_record = universe.get(pid)
                if candidate_record and not any(
                    reason == "LOCKED_PROJECT_BINARY_PATH_AND_HASH"
                    for reason in candidate_reasons.get(pid, [])
                ):
                    raise AuthorizationViewError("SUPPORT_CONTROLLED_PORT_CONFLICT")

    candidates: list[dict[str, Any]] = []
    for pid in sorted(candidate_pids):
        record = universe[pid]
        _critical_record(record)
        value = _record_for_view(record)
        value["authorization_candidate_reasons"] = sorted(candidate_reasons[pid])
        candidates.append(value)

    support: list[dict[str, Any]] = []
    for pid in sorted(proven_support_pids - candidate_pids - {runner_pid}):
        record = universe[pid]
        _critical_record(record)
        if set(listeners.get(pid, [])) & set(ports):
            raise AuthorizationViewError("SUPPORT_CONTROLLED_PORT_CONFLICT")
        support.append(_record_for_view(record))

    excluded = candidate_pids | proven_support_pids | {runner_pid}
    unrelated = [_record_for_view(universe[pid]) for pid in sorted(set(universe) - excluded)]
    root = _record_for_view(runner)

    candidate_ids = _view_identities(candidates)
    support_ids = _view_identities(support)
    unrelated_ids = _view_identities(unrelated)
    if candidate_ids & support_ids or candidate_ids & unrelated_ids or support_ids & unrelated_ids:
        raise AuthorizationViewError("VIEW_PARTITIONS_OVERLAP")
    expected_ids = {_identity_tuple(row) for pid, row in universe.items() if pid != runner_pid}
    if candidate_ids | support_ids | unrelated_ids != expected_ids:
        raise AuthorizationViewError("VIEW_UNIVERSE_COVERAGE_MISMATCH")

    return {
        "schema_version": "role_binding_timing.infra_m12.authorization_views.v1",
        "classifier_version": CLASSIFIER_VERSION,
        "classifier_contract_sha256": CLASSIFIER_CONTRACT_SHA256,
        "classifier_implementation_sha256": implementation_sha256(),
        "compatibility_replay_only": compatibility_replay,
        "authority_eligible": not compatibility_replay,
        "raw_snapshot_sha256": raw_hash,
        "sample_sequence": sequence,
        "sample_time_utc": timestamp,
        "trusted_runner_root": [root],
        "project_authorization_candidates": candidates,
        "support_only_ancestry_nodes": support,
        "unrelated_observed_processes": unrelated,
        "candidate_ancestry": ancestry,
        "type_assertions": {
            "views_disjoint": True,
            "universe_covered": True,
            "support_role_authority": False,
            "support_controlled_port_owner": False,
            "caller_role_labels_used": False,
        },
        "input_hashes": {
            "locked_runner_record_sha256": canonical_sha256(locked_runner_record),
            "locked_known_paths_sha256": canonical_sha256(known),
            "controlled_ports_sha256": canonical_sha256(list(ports)),
            "controlled_port_evidence_sha256": canonical_sha256(listeners),
        },
        "raw_identity_by_pid": {
            str(pid): _identity_text(_identity_tuple(record)) for pid, record in sorted(universe.items())
        },
    }


def _partition_payload(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for row in rows:
        value = copy.deepcopy(dict(row))
        value.pop("partition_sha256", None)
        payload.append(value)
    return sorted(payload, key=lambda item: _identity_tuple(item))


def hash_partitions(views: Mapping[str, Any]) -> dict[str, str]:
    return {
        name: canonical_sha256(_partition_payload(views.get(name, [])))
        for name in VIEW_NAMES
    }


def _candidate_reason_map(views: Mapping[str, Any]) -> dict[tuple[int, float], tuple[str, ...]]:
    return {
        _identity_tuple(row): tuple(row.get("authorization_candidate_reasons", []))
        for row in views.get("project_authorization_candidates", [])
    }


def _validate_supplied_views(expected: Mapping[str, Any], supplied: Mapping[str, Any]) -> None:
    expected_candidates = _view_identities(expected.get("project_authorization_candidates", []))
    supplied_candidates = _view_identities(supplied.get("project_authorization_candidates", []))
    if expected_candidates != supplied_candidates:
        raise AuthorizationViewError("DERIVED_PARTITION_CLASS_TAMPER")
    if _candidate_reason_map(expected) != _candidate_reason_map(supplied):
        raise AuthorizationViewError("CANDIDATE_REASON_TAMPER")
    for name in ("trusted_runner_root", "support_only_ancestry_nodes", "unrelated_observed_processes"):
        if _view_identities(expected.get(name, [])) != _view_identities(supplied.get(name, [])):
            raise AuthorizationViewError("RECOMPUTED_VIEW_MISMATCH")


def seal_derived_view(
    raw_snapshot: Mapping[str, Any],
    derived_views: Mapping[str, Any],
    locked_runner_record: Mapping[str, Any],
    locked_known_paths: Sequence[Mapping[str, Any]],
    controlled_ports: Sequence[int],
    classifier_version: str,
    classifier_contract_sha256: str,
    classifier_implementation_sha256: str,
    classifier_implementation_blob_oid: str,
) -> dict[str, Any]:
    if not isinstance(derived_views, Mapping):
        raise AuthorizationViewError("DERIVED_VIEW_MALFORMED")
    expected = derive_authorization_views(
        raw_snapshot,
        locked_runner_record,
        locked_known_paths,
        controlled_ports,
        classifier_version,
        classifier_contract_sha256,
        classifier_implementation_sha256,
    )
    if expected.get("compatibility_replay_only"):
        raise AuthorizationViewError("COMPATIBILITY_REPLAY_NOT_AUTHORITY_ELIGIBLE")
    _validate_supplied_views(expected, derived_views)
    if classifier_implementation_blob_oid != implementation_blob_oid():
        raise AuthorizationViewError("CLASSIFIER_IMPLEMENTATION_BLOB_MISMATCH")

    views = {name: copy.deepcopy(expected[name]) for name in VIEW_NAMES}
    partition_hashes = hash_partitions(views)
    for name, rows in views.items():
        for row in rows:
            row["partition_sha256"] = partition_hashes[name]
    complete_hash = canonical_sha256(
        {
            "partitions": partition_hashes,
            "candidate_ancestry": expected["candidate_ancestry"],
            "sample_sequence": expected["sample_sequence"],
            "sample_time_utc": expected["sample_time_utc"],
        }
    )
    sealed = {
        "schema_version": "role_binding_timing.infra_m12.sealed_authorization_view.v1",
        "views": views,
        "candidate_ancestry": copy.deepcopy(expected["candidate_ancestry"]),
        "raw_snapshot_sha256": expected["raw_snapshot_sha256"],
        "raw_identity_by_pid": copy.deepcopy(expected["raw_identity_by_pid"]),
        "sample_sequence": expected["sample_sequence"],
        "sample_time_utc": expected["sample_time_utc"],
        "classifier_binding": {
            "classifier_version": CLASSIFIER_VERSION,
            "classifier_contract_sha256": CLASSIFIER_CONTRACT_SHA256,
            "classifier_implementation_sha256": implementation_sha256(),
            "classifier_implementation_blob_oid": implementation_blob_oid(),
        },
        "locked_input_hashes": copy.deepcopy(expected["input_hashes"]),
        "partition_hashes": partition_hashes,
        "complete_view_sha256": complete_hash,
        "authority_eligible": True,
    }
    sealed["seal_sha256"] = canonical_sha256(sealed)
    return sealed


def _current_identity_map(raw_snapshot: Mapping[str, Any]) -> dict[str, str]:
    rows = raw_snapshot.get("all_processes")
    if not isinstance(rows, list):
        raise AuthorizationViewError("OBSERVATION_UNIVERSE_MISSING")
    result: dict[str, str] = {}
    for row in rows:
        identity = _identity_tuple(row)
        pid = str(identity[0])
        if pid in result:
            raise AuthorizationViewError("DUPLICATE_PID")
        result[pid] = _identity_text(identity)
    return result


def _proof_mismatch_code(stored: Mapping[str, Any], expected: Mapping[str, Any]) -> str | None:
    if stored.get("sample_sequence") != expected.get("sample_sequence"):
        return "CROSS_SAMPLE_STITCHING"
    if stored.get("sample_time_utc") != expected.get("sample_time_utc"):
        return "CROSS_SAMPLE_STITCHING"
    if stored.get("source_record_sha256") != expected.get("source_record_sha256"):
        return "SOURCE_RECORD_HASH_MISMATCH"
    if stored.get("raw_snapshot_sha256") != expected.get("raw_snapshot_sha256"):
        return "RAW_SNAPSHOT_HASH_MISMATCH"
    return None


def recompute_and_verify_sealed_view(
    raw_snapshot: Mapping[str, Any],
    sealed_view: Mapping[str, Any],
    locked_runner_record: Mapping[str, Any],
    locked_known_paths: Sequence[Mapping[str, Any]],
    controlled_ports: Sequence[int],
) -> dict[str, Any]:
    if not isinstance(sealed_view, Mapping):
        raise AuthorizationViewError("SEALED_VIEW_MALFORMED")
    binding = sealed_view.get("classifier_binding")
    if not isinstance(binding, Mapping):
        raise AuthorizationViewError("CLASSIFIER_BINDING_MISSING")
    if binding.get("classifier_version") != CLASSIFIER_VERSION:
        raise AuthorizationViewError("CLASSIFIER_VERSION_MISMATCH")
    if _normalized_hash(binding.get("classifier_contract_sha256")) != CLASSIFIER_CONTRACT_SHA256:
        raise AuthorizationViewError("CLASSIFIER_CONTRACT_HASH_MISMATCH")
    if _normalized_hash(binding.get("classifier_implementation_sha256")) != implementation_sha256():
        raise AuthorizationViewError("CLASSIFIER_IMPLEMENTATION_HASH_MISMATCH")
    if binding.get("classifier_implementation_blob_oid") != implementation_blob_oid():
        raise AuthorizationViewError("CLASSIFIER_IMPLEMENTATION_BLOB_MISMATCH")

    known = _normalize_known_paths(locked_known_paths)
    ports = _normalize_controlled_ports(controlled_ports)
    locked_hashes = sealed_view.get("locked_input_hashes")
    if not isinstance(locked_hashes, Mapping):
        raise AuthorizationViewError("LOCKED_INPUT_BINDING_MISSING")
    if locked_hashes.get("locked_runner_record_sha256") != canonical_sha256(locked_runner_record):
        raise AuthorizationViewError("LOCKED_RUNNER_RECORD_HASH_MISMATCH")
    if locked_hashes.get("locked_known_paths_sha256") != canonical_sha256(known):
        raise AuthorizationViewError("LOCKED_KNOWN_PATHS_HASH_MISMATCH")
    if locked_hashes.get("controlled_ports_sha256") != canonical_sha256(list(ports)):
        raise AuthorizationViewError("CONTROLLED_PORT_SET_HASH_MISMATCH")

    current_identity = _current_identity_map(raw_snapshot)
    stored_identity = sealed_view.get("raw_identity_by_pid")
    if not isinstance(stored_identity, Mapping):
        raise AuthorizationViewError("SEALED_IDENTITY_MAP_MISSING")
    for pid in set(current_identity) & set(stored_identity):
        if current_identity[pid] != stored_identity[pid]:
            raise AuthorizationViewError("PID_CREATE_TIME_REUSE")

    raw_listeners = _listener_map(raw_snapshot, {int(row["pid"]): row for row in raw_snapshot.get("all_processes", [])})
    if locked_hashes.get("controlled_port_evidence_sha256") != canonical_sha256(raw_listeners):
        raise AuthorizationViewError("CONTROLLED_PORT_EVIDENCE_MISMATCH")
    current_raw_hash = canonical_sha256(raw_snapshot)
    if sealed_view.get("raw_snapshot_sha256") != current_raw_hash:
        raise AuthorizationViewError("RAW_SNAPSHOT_HASH_MISMATCH")

    expected = derive_authorization_views(
        raw_snapshot,
        locked_runner_record,
        locked_known_paths,
        controlled_ports,
        CLASSIFIER_VERSION,
        CLASSIFIER_CONTRACT_SHA256,
        implementation_sha256(),
    )
    supplied_views = sealed_view.get("views")
    if not isinstance(supplied_views, Mapping):
        raise AuthorizationViewError("SEALED_VIEW_PARTITIONS_MISSING")
    _validate_supplied_views(expected, supplied_views)

    expected_by_view = {
        name: {_identity_tuple(row): row for row in expected[name]} for name in VIEW_NAMES
    }
    for name in VIEW_NAMES:
        for stored in supplied_views.get(name, []):
            if name == "support_only_ancestry_nodes" and any(
                stored.get(flag) is not False
                for flag in ("role_authority", "adoptable", "kill_target", "cleanup_target")
            ):
                raise AuthorizationViewError("SUPPORT_AUTHORITY_TAMPER")
            expected_record = expected_by_view[name].get(_identity_tuple(stored))
            if expected_record is None:
                raise AuthorizationViewError("RECOMPUTED_VIEW_MISMATCH")
            mismatch = _proof_mismatch_code(stored, expected_record)
            if mismatch:
                raise AuthorizationViewError(mismatch)

    recomputed_partitions = hash_partitions(supplied_views)
    stored_partitions = sealed_view.get("partition_hashes")
    if not isinstance(stored_partitions, Mapping):
        raise AuthorizationViewError("PARTITION_HASH_MISSING")
    for name in VIEW_NAMES:
        if stored_partitions.get(name) != recomputed_partitions[name]:
            raise AuthorizationViewError("PARTITION_HASH_MISMATCH")
        for row in supplied_views.get(name, []):
            if row.get("partition_sha256") != stored_partitions.get(name):
                raise AuthorizationViewError("PARTITION_HASH_MISMATCH")

    expected_complete = canonical_sha256(
        {
            "partitions": dict(stored_partitions),
            "candidate_ancestry": expected["candidate_ancestry"],
            "sample_sequence": expected["sample_sequence"],
            "sample_time_utc": expected["sample_time_utc"],
        }
    )
    if sealed_view.get("complete_view_sha256") != expected_complete:
        raise AuthorizationViewError("COMPLETE_VIEW_HASH_MISMATCH")
    seal_payload = copy.deepcopy(dict(sealed_view))
    stored_seal_hash = seal_payload.pop("seal_sha256", None)
    if stored_seal_hash != canonical_sha256(seal_payload):
        raise AuthorizationViewError("SEALED_VIEW_HASH_MISMATCH")
    return {"valid": True, "recomputed_views": expected}


_RUN_EPOCHS: dict[str, int] = {}
_RUN_EPOCHS_LOCK = threading.Lock()


def _run_epoch(run_id: str) -> int:
    with _RUN_EPOCHS_LOCK:
        return _RUN_EPOCHS.get(run_id, 0)


def expire_run_local_attestations(run_id: str) -> None:
    if not isinstance(run_id, str) or not run_id:
        raise TemporalAttestationError("RUN_ID_MALFORMED")
    with _RUN_EPOCHS_LOCK:
        _RUN_EPOCHS[run_id] = _RUN_EPOCHS.get(run_id, 0) + 1


def _temporalize(error: AuthorizationViewError, *, current: bool = False) -> TemporalAttestationError:
    code = error.code
    if current and code == "LOCKED_RUNNER_IDENTITY_MISMATCH":
        code = "RUNNER_ROOT_IDENTITY_MISMATCH"
    return TemporalAttestationError(code, error.detail)


def issue_temporal_attestation(
    raw_snapshot: Mapping[str, Any],
    locked_runner_record: Mapping[str, Any],
    locked_known_paths: Sequence[Mapping[str, Any]],
    controlled_ports: Sequence[int],
    classifier_version: str,
    classifier_contract_sha256: str,
    classifier_implementation_sha256: str,
    classifier_implementation_blob_oid: str,
    candidate_identity_key: Any,
    run_id: str,
) -> dict[str, Any]:
    if not isinstance(run_id, str) or not run_id:
        raise TemporalAttestationError("RUN_ID_MALFORMED")
    try:
        views = derive_authorization_views(
            raw_snapshot,
            locked_runner_record,
            locked_known_paths,
            controlled_ports,
            classifier_version,
            classifier_contract_sha256,
            classifier_implementation_sha256,
        )
        sealed = seal_derived_view(
            raw_snapshot,
            views,
            locked_runner_record,
            locked_known_paths,
            controlled_ports,
            classifier_version,
            classifier_contract_sha256,
            classifier_implementation_sha256,
            classifier_implementation_blob_oid,
        )
        candidate_identity = _coerce_identity(candidate_identity_key)
    except AuthorizationViewError as error:
        raise _temporalize(error) from error

    candidate = next(
        (
            row
            for row in views["project_authorization_candidates"]
            if _identity_tuple(row) == candidate_identity
        ),
        None,
    )
    if candidate is None:
        raise TemporalAttestationError("IDENTITY_NOT_DERIVED_CANDIDATE")
    ancestry = next(
        (
            row
            for row in views["candidate_ancestry"]
            if row["candidate_identity_key"] == _identity_text(candidate_identity)
        ),
        None,
    )
    if not ancestry or ancestry.get("complete_within_bound") is not True:
        raise TemporalAttestationError("MISSING_PARENT_CHAIN")
    chain_records: list[dict[str, Any]] = [copy.deepcopy(candidate)]
    all_view_rows = {
        _identity_text(_identity_tuple(row)): row
        for name in VIEW_NAMES
        for row in views[name]
    }
    for node in ancestry["chain"]:
        identity = node.get("identity_key")
        if identity not in all_view_rows:
            raise TemporalAttestationError("MISSING_PARENT_CHAIN")
        chain_records.append(copy.deepcopy(all_view_rows[identity]))
    attestation = {
        "schema_version": "role_binding_timing.infra_m12.temporal_attestation.v1",
        "valid": True,
        "run_id": run_id,
        "run_epoch": _run_epoch(run_id),
        "sample_sequence": views["sample_sequence"],
        "sample_time_utc": views["sample_time_utc"],
        "candidate_identity_key": candidate_identity,
        "birth_candidate_record": copy.deepcopy(candidate),
        "birth_chain": chain_records,
        "sealed_view": sealed,
        "birth_raw_snapshot": copy.deepcopy(raw_snapshot),
    }
    attestation["attestation_sha256"] = canonical_sha256(attestation)
    return attestation


def _find_pid(raw_snapshot: Mapping[str, Any], pid: int) -> dict[str, Any] | None:
    rows = raw_snapshot.get("all_processes")
    if not isinstance(rows, list):
        return None
    matches = [row for row in rows if isinstance(row, dict) and row.get("pid") == pid]
    if len(matches) > 1:
        raise TemporalAttestationError("DUPLICATE_PID")
    return copy.deepcopy(matches[0]) if matches else None


def verify_temporal_attestation(
    attestation: Mapping[str, Any],
    current_raw_snapshot: Mapping[str, Any],
    locked_runner_record: Mapping[str, Any],
    locked_known_paths: Sequence[Mapping[str, Any]],
    controlled_ports: Sequence[int],
    classifier_version: str,
    classifier_contract_sha256: str,
    classifier_implementation_sha256: str,
    classifier_implementation_blob_oid: str,
    run_id: str,
) -> dict[str, Any]:
    if not isinstance(attestation, Mapping):
        raise TemporalAttestationError("ATTESTATION_MALFORMED")
    if attestation.get("run_id") != run_id:
        raise TemporalAttestationError("CROSS_RUN_REPLAY")
    if attestation.get("run_epoch") != _run_epoch(run_id):
        raise TemporalAttestationError("ATTESTATION_EXPIRED")
    if classifier_version != CLASSIFIER_VERSION:
        raise TemporalAttestationError("CLASSIFIER_VERSION_MISMATCH")
    if _normalized_hash(classifier_contract_sha256) != CLASSIFIER_CONTRACT_SHA256:
        raise TemporalAttestationError("CLASSIFIER_CONTRACT_HASH_MISMATCH")
    if _normalized_hash(classifier_implementation_sha256) != implementation_sha256():
        raise TemporalAttestationError("CLASSIFIER_IMPLEMENTATION_HASH_MISMATCH")
    if classifier_implementation_blob_oid != implementation_blob_oid():
        raise TemporalAttestationError("CLASSIFIER_IMPLEMENTATION_BLOB_MISMATCH")

    birth_raw = attestation.get("birth_raw_snapshot")
    sealed = attestation.get("sealed_view")
    if not isinstance(birth_raw, Mapping) or not isinstance(sealed, Mapping):
        raise TemporalAttestationError("ATTESTATION_BIRTH_EVIDENCE_MISSING")
    try:
        recompute_and_verify_sealed_view(
            birth_raw,
            sealed,
            locked_runner_record,
            locked_known_paths,
            controlled_ports,
        )
    except AuthorizationViewError as error:
        raise _temporalize(error) from error

    candidate_identity = _coerce_identity(attestation.get("candidate_identity_key"))
    birth_candidate = attestation.get("birth_candidate_record")
    if not isinstance(birth_candidate, Mapping) or _identity_tuple(birth_candidate) != candidate_identity:
        raise TemporalAttestationError("BIRTH_CANDIDATE_IDENTITY_MISMATCH")
    birth_chain = attestation.get("birth_chain")
    if not isinstance(birth_chain, list) or len(birth_chain) < 2:
        raise TemporalAttestationError("MISSING_PARENT_CHAIN")

    for node in birth_chain:
        if node.get("sample_sequence") != attestation.get("sample_sequence"):
            raise TemporalAttestationError("CROSS_SAMPLE_STITCHING")
        if node.get("sample_time_utc") != attestation.get("sample_time_utc"):
            raise TemporalAttestationError("CROSS_SAMPLE_STITCHING")
    attestation_payload = copy.deepcopy(dict(attestation))
    stored_attestation_hash = attestation_payload.pop("attestation_sha256", None)
    if stored_attestation_hash != canonical_sha256(attestation_payload):
        raise TemporalAttestationError("ATTESTATION_HASH_MISMATCH")

    try:
        current_views = derive_authorization_views(
            current_raw_snapshot,
            locked_runner_record,
            locked_known_paths,
            controlled_ports,
            classifier_version,
            classifier_contract_sha256,
            classifier_implementation_sha256,
        )
    except AuthorizationViewError as error:
        raise _temporalize(error, current=True) from error

    current_candidate_by_pid = _find_pid(current_raw_snapshot, candidate_identity[0])
    if current_candidate_by_pid is not None:
        if _identity_tuple(current_candidate_by_pid) != candidate_identity:
            raise TemporalAttestationError("CHILD_PID_REUSE")
    for node in birth_chain[1:-1]:
        identity = _identity_tuple(node)
        current_parent = _find_pid(current_raw_snapshot, identity[0])
        if current_parent is not None and _identity_tuple(current_parent) != identity:
            raise TemporalAttestationError("PARENT_PID_REUSE")

    if current_candidate_by_pid is None:
        return {
            "accepted": True,
            "candidate_identity_key": candidate_identity,
            "historical_only": True,
            "current_authority": False,
            "decision": "ACCEPT_HISTORICAL_CLASSIFICATION_ONLY",
        }
    if normalized_path(current_candidate_by_pid.get("exe")) != normalized_path(birth_candidate.get("exe")):
        raise TemporalAttestationError("CURRENT_HISTORY_CONFLICT")
    if _normalized_hash(current_candidate_by_pid.get("exe_sha256")) != _normalized_hash(
        birth_candidate.get("exe_sha256")
    ):
        structural = next(
            (
                row
                for row in current_raw_snapshot.get("structural_processes", [])
                if row.get("pid") == candidate_identity[0]
            ),
            current_candidate_by_pid,
        )
        if _normalized_hash(structural.get("exe_sha256")) != _normalized_hash(
            birth_candidate.get("exe_sha256")
        ):
            raise TemporalAttestationError("CURRENT_HISTORY_CONFLICT")
    if normalized_command(
        current_candidate_by_pid.get("command_line", current_candidate_by_pid.get("cmdline_items"))
    ) != normalized_command(birth_candidate.get("command_line", birth_candidate.get("cmdline_items"))):
        raise TemporalAttestationError("CURRENT_HISTORY_CONFLICT")
    if candidate_identity not in _view_identities(current_views["project_authorization_candidates"]):
        raise TemporalAttestationError("CURRENT_CANDIDATE_NOT_AUTHORIZED")
    return {
        "accepted": True,
        "candidate_identity_key": candidate_identity,
        "historical_only": False,
        "current_authority": True,
        "decision": "ACCEPT_CURRENT_BIRTH_PROVENANCE",
    }


def evaluate_temporal_replay(
    attestations: Sequence[Mapping[str, Any]],
    current_raw_snapshot: Mapping[str, Any],
    locked_runner_record: Mapping[str, Any],
    locked_known_paths: Sequence[Mapping[str, Any]],
    controlled_ports: Sequence[int],
    classifier_version: str,
    classifier_contract_sha256: str,
    classifier_implementation_sha256: str,
    classifier_implementation_blob_oid: str,
    run_id: str,
) -> dict[str, Any]:
    if not isinstance(attestations, (list, tuple)):
        raise TemporalAttestationError("ATTESTATION_SET_MALFORMED")
    historical = 0
    historical_authority = 0
    current = 0
    support_role_authority = 0
    support_cleanup_targets = 0
    decisions: list[dict[str, Any]] = []
    for attestation in attestations:
        decision = verify_temporal_attestation(
            attestation,
            current_raw_snapshot,
            locked_runner_record,
            locked_known_paths,
            controlled_ports,
            classifier_version,
            classifier_contract_sha256,
            classifier_implementation_sha256,
            classifier_implementation_blob_oid,
            run_id,
        )
        decisions.append(decision)
        if decision["historical_only"]:
            historical += 1
            historical_authority += int(bool(decision["current_authority"]))
        else:
            current += 1
        for row in attestation["sealed_view"]["views"]["support_only_ancestry_nodes"]:
            support_role_authority += int(bool(row.get("role_authority")))
            support_cleanup_targets += int(bool(row.get("cleanup_target")))
    return {
        "historical_exited_count": historical,
        "historical_exited_authority_count": historical_authority,
        "current_attested_count": current,
        "support_role_authority_count": support_role_authority,
        "support_cleanup_target_count": support_cleanup_targets,
        "decisions": decisions,
    }
