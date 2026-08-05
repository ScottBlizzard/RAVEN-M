"""Proof-bound process views and run-local attestation issuance for INFRA-M13.

This module is deliberately independent of prior runtime implementations.
Public SHA-256 values are content addresses only. Authorization comes from
fresh raw-and-locked recomputation with exact canonical equality, followed by
membership in the current process-local issuer ledger.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import secrets
import threading
from typing import Any, Mapping, Sequence


CONTRACT_VERSION = "infra-m13-proof-bound-role-views-v1"
CONTRACT_SHA256 = "52A2914DCB4152B30CDBA50F5F0E8E3CF8EF1C614694E5544ABE7EB253418519"
CONTROLLED_PORT_UNIVERSE = frozenset({5037, 5038, 5554, 5555, 8554})
MAX_PARENT_DEPTH = 16
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
_SEALED_KEYS = frozenset(
    {
        "schema_version",
        "bindings",
        "views",
        "candidate_ancestry",
        "partition_hashes",
        "complete_view_sha256",
        "seal_sha256",
    }
)
_VERIFIED_SEAL_CAPABILITY = object()


class M13ContractError(RuntimeError):
    """Fail-closed contract violation with a stable machine-readable code."""

    def __init__(self, code: str, detail: Any | None = None):
        self.code = code
        self.detail = detail
        message = code if detail is None else f"{code}:{detail}"
        super().__init__(message)


def _fail(code: str, detail: Any | None = None) -> None:
    raise M13ContractError(code, detail)


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise M13ContractError("CANONICAL_SERIALIZATION_FAILURE", str(exc)) from exc


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest().upper()


def implementation_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()


def implementation_blob_oid() -> str:
    raw = Path(__file__).read_bytes()
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw, usedforsecurity=False).hexdigest()


def _deepcopy_json(value: Any) -> Any:
    return json.loads(canonical_bytes(value).decode("utf-8"))


def _normalized_hash(value: Any) -> str:
    if not isinstance(value, str) or len(value) != 64:
        _fail("MISSING_EXE_SHA256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise M13ContractError("MISSING_EXE_SHA256") from exc
    return value.upper()


def _normalized_path(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail("MISSING_EXE_PATH")
    return value.strip().replace("/", "\\").rstrip("\\").casefold()


def _normalized_command(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        compact = " ".join(value.split())
        if not compact:
            _fail("MISSING_COMMAND_LINE")
        return (compact,)
    if isinstance(value, (list, tuple)) and value:
        parts = tuple(str(item) for item in value)
        if any(not item for item in parts):
            _fail("MISSING_COMMAND_LINE")
        return parts
    _fail("MISSING_COMMAND_LINE")


def _identity(row: Mapping[str, Any]) -> tuple[int, float]:
    pid = row.get("pid")
    create_time = row.get("create_time")
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        _fail("MISSING_PID")
    if not isinstance(create_time, (int, float)) or isinstance(create_time, bool):
        _fail("MISSING_CREATE_TIME")
    return pid, float(create_time)


def _identity_json(identity: tuple[int, float]) -> list[Any]:
    return [identity[0], identity[1]]


def _coerce_identity(value: Any) -> tuple[int, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        _fail("IDENTITY_MALFORMED")
    return _identity({"pid": value[0], "create_time": value[1]})


def _command_from_row(row: Mapping[str, Any]) -> Any:
    if row.get("command_line") not in (None, "", []):
        return row.get("command_line")
    return row.get("cmdline_items")


def _is_access_denied(row: Mapping[str, Any]) -> bool:
    status = str(row.get("accessibility_status", "")).casefold()
    error = str(row.get("access_error", "")).casefold()
    return "denied" in status or "denied" in error


def _sample_sequence(raw_snapshot: Mapping[str, Any]) -> int:
    value = raw_snapshot.get("sample_sequence", raw_snapshot.get("sequence"))
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        _fail("SAMPLE_SEQUENCE_MISSING")
    return value


def _sample_time(raw_snapshot: Mapping[str, Any]) -> str:
    value = raw_snapshot.get("sample_time_utc", raw_snapshot.get("captured_at"))
    if value is None:
        captured = raw_snapshot.get("captured_epoch")
        if isinstance(captured, (int, float)) and not isinstance(captured, bool):
            value = f"epoch:{captured:.9f}"
    if not isinstance(value, str) or not value:
        _fail("SAMPLE_TIME_MISSING")
    return value


def _listener_map(raw_snapshot: Mapping[str, Any]) -> dict[int, list[int]]:
    if raw_snapshot.get("listener_evidence_complete") is not True:
        _fail("LISTENER_EVIDENCE_INCOMPLETE")
    source = raw_snapshot.get("all_tcp_listener_ports_by_pid")
    if not isinstance(source, Mapping):
        _fail("LISTENER_EVIDENCE_INCOMPLETE")
    result: dict[int, list[int]] = {}
    for raw_pid, raw_ports in source.items():
        try:
            pid = int(raw_pid)
        except (TypeError, ValueError) as exc:
            raise M13ContractError("LISTENER_EVIDENCE_MALFORMED") from exc
        if not isinstance(raw_ports, list) or any(
            not isinstance(port, int) or isinstance(port, bool) or port <= 0
            for port in raw_ports
        ):
            _fail("LISTENER_EVIDENCE_MALFORMED", pid)
        normalized = sorted(set(raw_ports))
        if len(normalized) != len(raw_ports):
            _fail("LISTENER_EVIDENCE_MALFORMED", pid)
        result[pid] = normalized
    return result


def _validate_contract_binding(
    contract_version: str,
    contract_sha256: str,
    classifier_implementation_sha256: str,
) -> None:
    if contract_version != CONTRACT_VERSION:
        _fail("CLASSIFIER_BINDING_MISMATCH")
    if not isinstance(contract_sha256, str) or contract_sha256.upper() != CONTRACT_SHA256:
        _fail("CLASSIFIER_BINDING_MISMATCH")
    if (
        not isinstance(classifier_implementation_sha256, str)
        or classifier_implementation_sha256.upper() != implementation_sha256()
    ):
        _fail("CLASSIFIER_BINDING_MISMATCH")


def _raw_rows(raw_snapshot: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    rows = raw_snapshot.get(key)
    if not isinstance(rows, list):
        _fail("OBSERVATION_UNIVERSE_MISSING", key)
    result: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            _fail("PROCESS_RECORD_MALFORMED", key)
        result.append(_deepcopy_json(dict(row)))
    return result


def _index_rows(rows: Sequence[Mapping[str, Any]], source: str) -> dict[tuple[int, float], dict[str, Any]]:
    by_identity: dict[tuple[int, float], dict[str, Any]] = {}
    by_pid: dict[int, tuple[int, float]] = {}
    for source_row in rows:
        row = dict(source_row)
        identity = _identity(row)
        if identity in by_identity:
            _fail("DUPLICATE_PROCESS_IDENTITY", {"source": source, "identity": identity})
        previous = by_pid.get(identity[0])
        if previous is not None:
            if previous != identity:
                _fail("PID_CREATE_TIME_REUSE", identity[0])
            _fail("DUPLICATE_PID", identity[0])
        by_pid[identity[0]] = identity
        by_identity[identity] = row
    return by_identity


def _canonical_equal(left: Any, right: Any) -> bool:
    return canonical_bytes(left) == canonical_bytes(right)


def _fuse_sources(raw_snapshot: Mapping[str, Any]) -> tuple[dict[tuple[int, float], dict[str, Any]], bool]:
    if raw_snapshot.get("observation_universe_complete") is not True:
        _fail("OBSERVATION_UNIVERSE_TRUNCATED")
    errors = raw_snapshot.get("observation_universe_capture_errors")
    if errors not in ([], None):
        _fail("OBSERVATION_UNIVERSE_CAPTURE_ERRORS", errors)
    all_rows = _raw_rows(raw_snapshot, "all_processes")
    structural_rows = _raw_rows(raw_snapshot, "structural_processes")
    all_index = _index_rows(all_rows, "all_processes")
    structural_index = _index_rows(structural_rows, "structural_processes")
    legacy_compatibility = str(raw_snapshot.get("schema_version", "")).startswith(
        "role_binding_timing.infra_m9."
    )
    extra_structural = set(structural_index) - set(all_index)
    if extra_structural:
        _fail("OBSERVATION_UNIVERSE_MISMATCH", sorted(extra_structural))
    if not legacy_compatibility and set(structural_index) != set(all_index):
        _fail("OBSERVATION_UNIVERSE_MISMATCH")
    fused: dict[tuple[int, float], dict[str, Any]] = {}
    for identity in sorted(all_index):
        base = copy.deepcopy(all_index[identity])
        rich = structural_index.get(identity)
        if rich is not None:
            for field in set(base) & set(rich):
                if not _canonical_equal(base[field], rich[field]):
                    _fail(
                        "RAW_SOURCE_FIELD_CONFLICT",
                        {"identity": _identity_json(identity), "field": field},
                    )
            base.update(copy.deepcopy(rich))
        fused[identity] = base
    return fused, legacy_compatibility


def _reject_raw_authority_labels(raw_snapshot: Mapping[str, Any]) -> None:
    for collection in ("all_processes", "structural_processes"):
        for row in _raw_rows(raw_snapshot, collection):
            overlap = sorted(FORBIDDEN_RAW_AUTHORITY_FIELDS & set(row))
            if overlap:
                _fail(
                    "RAW_AUTHORITY_LABEL_PRESENT",
                    {"collection": collection, "pid": row.get("pid"), "fields": overlap},
                )


def _validate_critical_row(row: Mapping[str, Any], *, require_hash: bool = True) -> None:
    _identity(row)
    ppid = row.get("ppid")
    if not isinstance(ppid, int) or isinstance(ppid, bool) or ppid < 0:
        _fail("MISSING_PARENT_PID")
    if _is_access_denied(row):
        _fail("CRITICAL_FIELD_ACCESS_DENIED", row.get("pid"))
    _normalized_path(row.get("exe"))
    if require_hash:
        _normalized_hash(row.get("exe_sha256"))
    _normalized_command(_command_from_row(row))


def _canonical_known_paths(locked_known_paths: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if not isinstance(locked_known_paths, Sequence) or isinstance(locked_known_paths, (str, bytes)):
        _fail("LOCKED_INPUT_MALFORMED")
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for entry in locked_known_paths:
        if not isinstance(entry, Mapping):
            _fail("LOCKED_INPUT_MALFORMED")
        role = entry.get("logical_role")
        if not isinstance(role, str) or not role:
            _fail("LOCKED_INPUT_MALFORMED")
        path = _normalized_path(entry.get("normalized_path"))
        digest = _normalized_hash(entry.get("exe_sha256"))
        key = (path, digest)
        if key in seen:
            _fail("LOCKED_INPUT_MALFORMED", "duplicate_known_path")
        seen.add(key)
        result.append({"logical_role": role, "normalized_path": path, "exe_sha256": digest})
    return sorted(result, key=lambda item: (item["normalized_path"], item["exe_sha256"], item["logical_role"]))


def _canonical_ports(controlled_ports: Sequence[int]) -> list[int]:
    if not isinstance(controlled_ports, Sequence) or isinstance(controlled_ports, (str, bytes)):
        _fail("LOCKED_INPUT_MALFORMED")
    ports = list(controlled_ports)
    if any(not isinstance(port, int) or isinstance(port, bool) for port in ports):
        _fail("LOCKED_INPUT_MALFORMED")
    normalized = sorted(set(ports))
    if len(normalized) != len(ports) or not set(normalized).issubset(CONTROLLED_PORT_UNIVERSE):
        _fail("LOCKED_INPUT_MALFORMED")
    return normalized


def _runner_match(
    fused: Mapping[tuple[int, float], Mapping[str, Any]],
    locked_runner_record: Mapping[str, Any],
    legacy_compatibility: bool,
) -> tuple[tuple[int, float], dict[str, Any]]:
    if not isinstance(locked_runner_record, Mapping):
        _fail("LOCKED_INPUT_MALFORMED")
    identity = _identity(locked_runner_record)
    observed = fused.get(identity)
    if observed is None:
        same_pid = [key for key in fused if key[0] == identity[0]]
        if same_pid:
            _fail("LOCKED_RUNNER_IDENTITY_MISMATCH")
        _fail("LOCKED_RUNNER_IDENTITY_MISMATCH")
    _validate_critical_row(observed)
    if _normalized_path(observed.get("exe")) != _normalized_path(locked_runner_record.get("exe")):
        _fail("LOCKED_RUNNER_IDENTITY_MISMATCH")
    locked_hash = locked_runner_record.get("exe_sha256")
    if locked_hash is None and legacy_compatibility:
        locked_hash = observed.get("exe_sha256")
    if _normalized_hash(observed.get("exe_sha256")) != _normalized_hash(locked_hash):
        _fail("LOCKED_RUNNER_IDENTITY_MISMATCH")
    if _normalized_command(_command_from_row(observed)) != _normalized_command(
        _command_from_row(locked_runner_record)
    ):
        _fail("LOCKED_RUNNER_IDENTITY_MISMATCH")
    return identity, copy.deepcopy(observed)


def _controlled_listener_ports(
    listeners: Mapping[int, Sequence[int]], pid: int, controlled_ports: Sequence[int]
) -> list[int]:
    return sorted(set(listeners.get(pid, [])) & set(controlled_ports))


def _proof_row(
    source: Mapping[str, Any],
    *,
    raw_snapshot_sha256: str,
    sample_sequence: int,
    sample_time_utc: str,
    listener_ports: Sequence[int],
    view_name: str,
    candidate_reasons: Sequence[str] = (),
) -> dict[str, Any]:
    value = _deepcopy_json(dict(source))
    identity = _identity(source)
    value["identity_key"] = _identity_json(identity)
    value["source_record_sha256"] = canonical_sha256(dict(source))
    value["raw_snapshot_sha256"] = raw_snapshot_sha256
    value["sample_sequence"] = sample_sequence
    value["sample_time_utc"] = sample_time_utc
    value["listener_evidence_complete"] = True
    value["listener_ports"] = list(listener_ports)
    value["derived_view"] = view_name
    value["role_authority"] = view_name == "project_authorization_candidates"
    value["adoptable"] = False
    value["kill_target"] = False
    value["cleanup_target"] = False
    if view_name == "project_authorization_candidates":
        value["authorization_candidate_reasons"] = list(candidate_reasons)
    return value


def _view_identities(rows: Sequence[Mapping[str, Any]]) -> set[tuple[int, float]]:
    return {_identity(row) for row in rows}


def _find_ancestry(
    candidate_identity: tuple[int, float],
    fused: Mapping[tuple[int, float], Mapping[str, Any]],
    by_pid: Mapping[int, tuple[int, float]],
    runner_identity: tuple[int, float],
) -> tuple[list[dict[str, Any]], bool]:
    candidate = fused[candidate_identity]
    parent_pid = candidate.get("ppid")
    seen: set[int] = set()
    chain: list[dict[str, Any]] = []
    complete = False
    for _ in range(MAX_PARENT_DEPTH):
        if not isinstance(parent_pid, int) or isinstance(parent_pid, bool) or parent_pid <= 0:
            break
        if parent_pid in seen:
            _fail("PARENT_CHAIN_CYCLE", parent_pid)
        seen.add(parent_pid)
        parent_identity = by_pid.get(parent_pid)
        if parent_identity is None:
            break
        parent = fused[parent_identity]
        _validate_critical_row(parent)
        chain.append(
            {
                "pid": parent_identity[0],
                "identity_key": _identity_json(parent_identity),
                "status": "OBSERVED",
            }
        )
        if parent_identity == runner_identity:
            complete = True
            break
        parent_pid = parent.get("ppid")
    return chain, complete


def derive_authorization_views(
    raw_snapshot: Mapping[str, Any],
    locked_runner_record: Mapping[str, Any],
    locked_known_paths: Sequence[Mapping[str, Any]],
    controlled_ports: Sequence[int],
    contract_version: str,
    contract_sha256: str,
    implementation_sha256: str,
) -> dict[str, Any]:
    if not isinstance(raw_snapshot, Mapping):
        _fail("OBSERVATION_UNIVERSE_MISSING")
    _validate_contract_binding(contract_version, contract_sha256, implementation_sha256)
    _reject_raw_authority_labels(raw_snapshot)
    listeners = _listener_map(raw_snapshot)
    ports = _canonical_ports(controlled_ports)
    known_paths = _canonical_known_paths(locked_known_paths)
    fused, legacy_compatibility = _fuse_sources(raw_snapshot)
    runner_identity, runner = _runner_match(fused, locked_runner_record, legacy_compatibility)
    raw_hash = canonical_sha256(dict(raw_snapshot))
    sequence = _sample_sequence(raw_snapshot)
    sample_time = _sample_time(raw_snapshot)
    by_pid = {identity[0]: identity for identity in fused}

    known_pairs = {
        (entry["normalized_path"], entry["exe_sha256"]) for entry in known_paths
    }
    candidate_reasons: dict[tuple[int, float], list[str]] = {}
    for identity, row in fused.items():
        if identity == runner_identity:
            continue
        reasons: list[str] = []
        path = row.get("exe")
        digest = row.get("exe_sha256")
        if path is not None and digest is not None:
            pair = (_normalized_path(path), _normalized_hash(digest))
            if pair in known_pairs:
                reasons.append("LOCKED_PROJECT_BINARY_PATH_AND_HASH")
        owned = _controlled_listener_ports(listeners, identity[0], ports)
        if owned:
            reasons.append("CONTROLLED_PORT_OWNER:" + ",".join(str(port) for port in owned))
        if reasons:
            _validate_critical_row(row)
            candidate_reasons[identity] = reasons

    support_identities: set[tuple[int, float]] = set()
    ancestry: list[dict[str, Any]] = []
    candidate_set = set(candidate_reasons)
    for candidate_identity in sorted(candidate_reasons):
        chain, complete = _find_ancestry(candidate_identity, fused, by_pid, runner_identity)
        for node in chain:
            identity = _coerce_identity(node["identity_key"])
            if identity != runner_identity and identity not in candidate_set:
                support_identities.add(identity)
        ancestry.append(
            {
                "candidate_identity_key": _identity_json(candidate_identity),
                "complete_within_bound": complete,
                "chain": chain,
            }
        )

    for identity in sorted(support_identities):
        owned = _controlled_listener_ports(listeners, identity[0], ports)
        if owned:
            _fail("SUPPORT_CONTROLLED_PORT_CONFLICT", {"identity": identity, "ports": owned})

    unrelated = set(fused) - candidate_set - support_identities - {runner_identity}
    views = {
        "trusted_runner_root": [
            _proof_row(
                runner,
                raw_snapshot_sha256=raw_hash,
                sample_sequence=sequence,
                sample_time_utc=sample_time,
                listener_ports=listeners.get(runner_identity[0], []),
                view_name="trusted_runner_root",
            )
        ],
        "project_authorization_candidates": [
            _proof_row(
                fused[identity],
                raw_snapshot_sha256=raw_hash,
                sample_sequence=sequence,
                sample_time_utc=sample_time,
                listener_ports=listeners.get(identity[0], []),
                view_name="project_authorization_candidates",
                candidate_reasons=candidate_reasons[identity],
            )
            for identity in sorted(candidate_set)
        ],
        "support_only_ancestry_nodes": [
            _proof_row(
                fused[identity],
                raw_snapshot_sha256=raw_hash,
                sample_sequence=sequence,
                sample_time_utc=sample_time,
                listener_ports=listeners.get(identity[0], []),
                view_name="support_only_ancestry_nodes",
            )
            for identity in sorted(support_identities)
        ],
        "unrelated_observed_processes": [
            _proof_row(
                fused[identity],
                raw_snapshot_sha256=raw_hash,
                sample_sequence=sequence,
                sample_time_utc=sample_time,
                listener_ports=listeners.get(identity[0], []),
                view_name="unrelated_observed_processes",
            )
            for identity in sorted(unrelated)
        ],
    }
    identities = {name: _view_identities(views[name]) for name in VIEW_NAMES}
    disjoint = all(
        not identities[left] & identities[right]
        for index, left in enumerate(VIEW_NAMES)
        for right in VIEW_NAMES[index + 1 :]
    )
    covered = set().union(*identities.values()) == set(fused)
    if not disjoint:
        _fail("DERIVED_VIEW_OVERLAP")
    if not covered:
        _fail("DERIVED_VIEW_COVERAGE_MISMATCH")
    return {
        "schema_version": "role_binding_timing.infra_m13.authorization_views.v1",
        **views,
        "candidate_ancestry": ancestry,
        "views_disjoint": True,
        "universe_covered": True,
        "sample_sequence": sequence,
        "sample_time_utc": sample_time,
        "raw_snapshot_sha256": raw_hash,
        "legacy_m9_compatibility_projection": legacy_compatibility,
    }


def _views_only(derived: Mapping[str, Any]) -> dict[str, Any]:
    return {name: copy.deepcopy(derived[name]) for name in VIEW_NAMES}


def _binding_payload(
    raw_snapshot: Mapping[str, Any],
    locked_runner_record: Mapping[str, Any],
    locked_known_paths: Sequence[Mapping[str, Any]],
    controlled_ports: Sequence[int],
    contract_version: str,
    contract_sha256: str,
    classifier_implementation_sha256: str,
    classifier_implementation_blob_oid: str,
) -> dict[str, Any]:
    listeners = _listener_map(raw_snapshot)
    return {
        "raw_snapshot_sha256": canonical_sha256(dict(raw_snapshot)),
        "locked_runner_record_sha256": canonical_sha256(dict(locked_runner_record)),
        "locked_known_paths_sha256": canonical_sha256(_canonical_known_paths(locked_known_paths)),
        "controlled_ports_sha256": canonical_sha256(_canonical_ports(controlled_ports)),
        "controlled_port_evidence_sha256": canonical_sha256(listeners),
        "contract_version": contract_version,
        "contract_sha256": contract_sha256.upper(),
        "implementation_sha256": classifier_implementation_sha256.upper(),
        "implementation_blob_oid": classifier_implementation_blob_oid,
    }


def _partition_hashes(views: Mapping[str, Any]) -> dict[str, str]:
    return {name: canonical_sha256(views[name]) for name in VIEW_NAMES}


def _complete_view_hash(
    bindings: Mapping[str, Any],
    views: Mapping[str, Any],
    candidate_ancestry: Sequence[Mapping[str, Any]],
    partition_hashes: Mapping[str, Any],
) -> str:
    return canonical_sha256(
        {
            "bindings": bindings,
            "views": views,
            "candidate_ancestry": candidate_ancestry,
            "partition_hashes": partition_hashes,
        }
    )


def seal_authorization_views(
    raw_snapshot: Mapping[str, Any],
    derived_views: Mapping[str, Any],
    candidate_ancestry: Sequence[Mapping[str, Any]],
    locked_runner_record: Mapping[str, Any],
    locked_known_paths: Sequence[Mapping[str, Any]],
    controlled_ports: Sequence[int],
    contract_version: str,
    contract_sha256: str,
    implementation_sha256: str,
    implementation_blob_oid: str,
) -> dict[str, Any]:
    _validate_contract_binding(contract_version, contract_sha256, implementation_sha256)
    if implementation_blob_oid != globals()["implementation_blob_oid"]():
        _fail("CLASSIFIER_BINDING_MISMATCH")
    expected = derive_authorization_views(
        raw_snapshot,
        locked_runner_record,
        locked_known_paths,
        controlled_ports,
        contract_version,
        contract_sha256,
        implementation_sha256,
    )
    expected_views = _views_only(expected)
    if set(derived_views) != set(VIEW_NAMES) or not _canonical_equal(derived_views, expected_views):
        _fail("SEALED_CANONICAL_VIEW_MISMATCH")
    if not _canonical_equal(candidate_ancestry, expected["candidate_ancestry"]):
        _fail("CANDIDATE_ANCESTRY_MISMATCH")
    bindings = _binding_payload(
        raw_snapshot,
        locked_runner_record,
        locked_known_paths,
        controlled_ports,
        contract_version,
        contract_sha256,
        implementation_sha256,
        implementation_blob_oid,
    )
    views = copy.deepcopy(expected_views)
    ancestry = copy.deepcopy(expected["candidate_ancestry"])
    partition_hashes = _partition_hashes(views)
    sealed = {
        "schema_version": "role_binding_timing.infra_m13.sealed_authorization_views.v1",
        "bindings": bindings,
        "views": views,
        "candidate_ancestry": ancestry,
        "partition_hashes": partition_hashes,
        "complete_view_sha256": _complete_view_hash(
            bindings, views, ancestry, partition_hashes
        ),
    }
    sealed["seal_sha256"] = canonical_sha256(sealed)
    return sealed


class _VerifiedSealedView:
    __slots__ = (
        "sealed_view",
        "recomputed",
        "birth_raw_snapshot",
        "locked_runner_record",
        "locked_known_paths",
        "controlled_ports",
        "_capability",
    )

    def __init__(
        self,
        capability: object,
        *,
        sealed_view: Mapping[str, Any],
        recomputed: Mapping[str, Any],
        birth_raw_snapshot: Mapping[str, Any],
        locked_runner_record: Mapping[str, Any],
        locked_known_paths: Sequence[Mapping[str, Any]],
        controlled_ports: Sequence[int],
    ):
        if capability is not _VERIFIED_SEAL_CAPABILITY:
            _fail("VERIFIED_SEAL_CAPABILITY_REQUIRED")
        self.sealed_view = copy.deepcopy(dict(sealed_view))
        self.recomputed = copy.deepcopy(dict(recomputed))
        self.birth_raw_snapshot = copy.deepcopy(dict(birth_raw_snapshot))
        self.locked_runner_record = copy.deepcopy(dict(locked_runner_record))
        self.locked_known_paths = copy.deepcopy(list(locked_known_paths))
        self.controlled_ports = list(controlled_ports)
        self._capability = capability

    def __reduce__(self):
        raise TypeError("verified sealed views are process-local capabilities")


def _detect_pid_reuse_against_sealed(
    raw_snapshot: Mapping[str, Any], supplied_sealed_view: Mapping[str, Any]
) -> None:
    rows = raw_snapshot.get("all_processes")
    if not isinstance(rows, list):
        return
    current: dict[int, tuple[int, float]] = {}
    for row in rows:
        if isinstance(row, Mapping):
            identity = _identity(row)
            current[identity[0]] = identity
    views = supplied_sealed_view.get("views")
    if not isinstance(views, Mapping):
        return
    for name in VIEW_NAMES:
        stored_rows = views.get(name)
        if not isinstance(stored_rows, list):
            continue
        for row in stored_rows:
            if not isinstance(row, Mapping):
                continue
            identity = _identity(row)
            observed = current.get(identity[0])
            if observed is not None and observed != identity:
                _fail("PID_CREATE_TIME_REUSE", identity[0])


def verify_sealed_authorization_views(
    raw_snapshot: Mapping[str, Any],
    supplied_sealed_view: Mapping[str, Any],
    locked_runner_record: Mapping[str, Any],
    locked_known_paths: Sequence[Mapping[str, Any]],
    controlled_ports: Sequence[int],
    contract_version: str,
    contract_sha256: str,
    implementation_sha256: str,
    implementation_blob_oid: str,
) -> _VerifiedSealedView:
    if not isinstance(supplied_sealed_view, Mapping):
        _fail("SEALED_VIEW_MALFORMED")
    if set(supplied_sealed_view) != set(_SEALED_KEYS):
        _fail("SEALED_CANONICAL_VIEW_MISMATCH")
    _validate_contract_binding(contract_version, contract_sha256, implementation_sha256)
    if implementation_blob_oid != globals()["implementation_blob_oid"]():
        _fail("CLASSIFIER_BINDING_MISMATCH")
    supplied_bindings = supplied_sealed_view.get("bindings")
    if not isinstance(supplied_bindings, Mapping):
        _fail("SEALED_VIEW_MALFORMED")
    expected_bindings = _binding_payload(
        raw_snapshot,
        locked_runner_record,
        locked_known_paths,
        controlled_ports,
        contract_version,
        contract_sha256,
        implementation_sha256,
        implementation_blob_oid,
    )
    if supplied_bindings.get("controlled_port_evidence_sha256") != expected_bindings[
        "controlled_port_evidence_sha256"
    ]:
        _fail("CONTROLLED_PORT_EVIDENCE_MISMATCH")
    if supplied_bindings.get("locked_runner_record_sha256") != expected_bindings[
        "locked_runner_record_sha256"
    ] or supplied_bindings.get("locked_known_paths_sha256") != expected_bindings[
        "locked_known_paths_sha256"
    ] or supplied_bindings.get("controlled_ports_sha256") != expected_bindings[
        "controlled_ports_sha256"
    ]:
        _fail("LOCKED_INPUT_MISMATCH")
    classifier_fields = (
        "contract_version",
        "contract_sha256",
        "implementation_sha256",
        "implementation_blob_oid",
    )
    if any(supplied_bindings.get(field) != expected_bindings[field] for field in classifier_fields):
        _fail("CLASSIFIER_BINDING_MISMATCH")
    if supplied_bindings.get("raw_snapshot_sha256") != expected_bindings["raw_snapshot_sha256"]:
        _detect_pid_reuse_against_sealed(raw_snapshot, supplied_sealed_view)
        _fail("RAW_SNAPSHOT_MISMATCH")

    recomputed = derive_authorization_views(
        raw_snapshot,
        locked_runner_record,
        locked_known_paths,
        controlled_ports,
        contract_version,
        contract_sha256,
        implementation_sha256,
    )
    supplied_views = supplied_sealed_view.get("views")
    if not isinstance(supplied_views, Mapping) or set(supplied_views) != set(VIEW_NAMES):
        _fail("SEALED_CANONICAL_VIEW_MISMATCH")
    expected_views = _views_only(recomputed)
    if not _canonical_equal(supplied_views, expected_views):
        _fail("SEALED_CANONICAL_VIEW_MISMATCH")
    supplied_ancestry = supplied_sealed_view.get("candidate_ancestry")
    if not _canonical_equal(supplied_ancestry, recomputed["candidate_ancestry"]):
        _fail("CANDIDATE_ANCESTRY_MISMATCH")

    expected_partitions = _partition_hashes(expected_views)
    if not _canonical_equal(supplied_sealed_view.get("partition_hashes"), expected_partitions):
        _fail("PARTITION_HASH_MISMATCH")
    expected_complete = _complete_view_hash(
        expected_bindings,
        expected_views,
        recomputed["candidate_ancestry"],
        expected_partitions,
    )
    if supplied_sealed_view.get("complete_view_sha256") != expected_complete:
        _fail("COMPLETE_VIEW_HASH_MISMATCH")
    seal_payload = copy.deepcopy(dict(supplied_sealed_view))
    stored_seal = seal_payload.pop("seal_sha256", None)
    if stored_seal != canonical_sha256(seal_payload):
        _fail("SEALED_VIEW_HASH_MISMATCH")
    return _VerifiedSealedView(
        _VERIFIED_SEAL_CAPABILITY,
        sealed_view=supplied_sealed_view,
        recomputed=recomputed,
        birth_raw_snapshot=raw_snapshot,
        locked_runner_record=locked_runner_record,
        locked_known_paths=locked_known_paths,
        controlled_ports=controlled_ports,
    )


class RunLocalIssuerLedger:
    """Opaque, nonserializable, process-local issuance authority."""

    __slots__ = ("_lock", "_instance_token", "_runs", "_entries")

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._instance_token = secrets.token_hex(32)
        self._runs: dict[str, dict[str, Any]] = {}
        self._entries: dict[str, dict[str, Any]] = {}

    def __reduce__(self):
        raise TypeError("run-local issuer ledgers cannot be serialized")

    def __copy__(self):
        raise TypeError("run-local issuer ledgers cannot be copied")

    def __deepcopy__(self, memo):
        raise TypeError("run-local issuer ledgers cannot be copied")


def create_run_local_issuer_ledger() -> RunLocalIssuerLedger:
    return RunLocalIssuerLedger()


def _require_ledger(ledger: Any) -> RunLocalIssuerLedger:
    if not isinstance(ledger, RunLocalIssuerLedger):
        _fail("ISSUER_LEDGER_REQUIRED")
    return ledger


def begin_issuer_run(ledger: RunLocalIssuerLedger, run_id: str) -> dict[str, Any]:
    ledger = _require_ledger(ledger)
    if not isinstance(run_id, str) or not run_id:
        _fail("RUN_ID_MALFORMED")
    with ledger._lock:
        existing = ledger._runs.get(run_id)
        if existing is not None:
            if existing["tombstoned"]:
                _fail("RUN_TOMBSTONED")
            _fail("RUN_ALREADY_ACTIVE")
        state = {
            "run_id": run_id,
            "run_nonce": secrets.token_hex(32),
            "epoch": 0,
            "active": True,
            "tombstoned": False,
            "ledger_instance_token": ledger._instance_token,
        }
        ledger._runs[run_id] = state
        return copy.deepcopy(state)


def _session_state(
    ledger: RunLocalIssuerLedger,
    issuer_session: Mapping[str, Any],
    *,
    permit_tombstone: bool = False,
) -> dict[str, Any]:
    if not isinstance(issuer_session, Mapping):
        _fail("ISSUER_SESSION_REQUIRED")
    run_id = issuer_session.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        _fail("ISSUER_SESSION_REQUIRED")
    state = ledger._runs.get(run_id)
    if state is None:
        _fail("ISSUER_LEDGER_ENTRY_MISSING")
    if issuer_session.get("ledger_instance_token") != ledger._instance_token:
        _fail("ISSUER_SESSION_NOT_OWNED")
    if state["tombstoned"] and not permit_tombstone:
        _fail("RUN_TOMBSTONED")
    if issuer_session.get("run_nonce") != state["run_nonce"]:
        _fail("RUN_NONCE_MISMATCH")
    if issuer_session.get("epoch") != state["epoch"]:
        _fail("RUN_EPOCH_MISMATCH")
    if not state["active"] and not permit_tombstone:
        _fail("RUN_NOT_ACTIVE")
    return state


def _records_by_identity(recomputed: Mapping[str, Any]) -> dict[tuple[int, float], dict[str, Any]]:
    result: dict[tuple[int, float], dict[str, Any]] = {}
    for name in VIEW_NAMES:
        for row in recomputed[name]:
            identity = _identity(row)
            if identity in result:
                _fail("DERIVED_VIEW_OVERLAP")
            result[identity] = copy.deepcopy(row)
    return result


def _candidate_and_chain(
    recomputed: Mapping[str, Any], candidate_identity: tuple[int, float]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidate = next(
        (
            copy.deepcopy(row)
            for row in recomputed["project_authorization_candidates"]
            if _identity(row) == candidate_identity
        ),
        None,
    )
    if candidate is None:
        _fail("IDENTITY_NOT_DERIVED_CANDIDATE")
    ancestry_matches = [
        item
        for item in recomputed["candidate_ancestry"]
        if _coerce_identity(item.get("candidate_identity_key")) == candidate_identity
    ]
    if len(ancestry_matches) != 1:
        _fail("CANDIDATE_ANCESTRY_MISMATCH")
    ancestry = ancestry_matches[0]
    if ancestry.get("complete_within_bound") is not True:
        _fail("MISSING_PARENT_CHAIN")
    nodes = ancestry.get("chain")
    if not isinstance(nodes, list) or not nodes:
        _fail("MISSING_PARENT_CHAIN")
    records = _records_by_identity(recomputed)
    chain = [candidate]
    for node in nodes:
        if not isinstance(node, Mapping) or node.get("status") != "OBSERVED":
            _fail("MISSING_PARENT_CHAIN")
        identity = _coerce_identity(node.get("identity_key"))
        record = records.get(identity)
        if record is None:
            _fail("MISSING_PARENT_CHAIN")
        chain.append(copy.deepcopy(record))
    return candidate, chain


def _attestation_payload(attestation: Mapping[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(dict(attestation))
    payload.pop("attestation_sha256", None)
    return payload


def _attestation_content_hash(attestation: Mapping[str, Any]) -> str:
    return canonical_sha256(_attestation_payload(attestation))


def _attestation_ledger_digest(attestation: Mapping[str, Any]) -> str:
    return canonical_sha256(dict(attestation))


def issue_temporal_attestation(
    verified_sealed_view: _VerifiedSealedView,
    candidate_identity_key: Any,
    ledger: RunLocalIssuerLedger,
    issuer_session: Mapping[str, Any],
) -> dict[str, Any]:
    ledger = _require_ledger(ledger)
    if not isinstance(verified_sealed_view, _VerifiedSealedView) or (
        verified_sealed_view._capability is not _VERIFIED_SEAL_CAPABILITY
    ):
        _fail("VERIFIED_SEAL_CAPABILITY_REQUIRED")
    candidate_identity = _coerce_identity(candidate_identity_key)
    candidate, chain = _candidate_and_chain(verified_sealed_view.recomputed, candidate_identity)
    if candidate.get("derived_view") != "project_authorization_candidates":
        _fail("IDENTITY_NOT_DERIVED_CANDIDATE")
    with ledger._lock:
        state = _session_state(ledger, issuer_session)
        attestation_id = secrets.token_hex(32)
        while attestation_id in ledger._entries:
            attestation_id = secrets.token_hex(32)
        attestation = {
            "schema_version": "role_binding_timing.infra_m13.temporal_attestation.v1",
            "run_id": state["run_id"],
            "run_nonce": state["run_nonce"],
            "epoch": state["epoch"],
            "attestation_id": attestation_id,
            "candidate_identity_key": _identity_json(candidate_identity),
            "birth_candidate_record": copy.deepcopy(candidate),
            "birth_chain": copy.deepcopy(chain),
            "sealed_view": copy.deepcopy(verified_sealed_view.sealed_view),
            "birth_raw_snapshot": copy.deepcopy(verified_sealed_view.birth_raw_snapshot),
        }
        attestation["attestation_sha256"] = _attestation_content_hash(attestation)
        digest = _attestation_ledger_digest(attestation)
        ledger._entries[attestation_id] = {
            "run_id": state["run_id"],
            "run_nonce": state["run_nonce"],
            "epoch": state["epoch"],
            "attestation_id": attestation_id,
            "canonical_attestation_digest": digest,
            "active": True,
        }
        return copy.deepcopy(attestation)


def _ledger_precheck(
    attestation: Mapping[str, Any],
    ledger: RunLocalIssuerLedger,
    issuer_session: Mapping[str, Any],
) -> dict[str, Any]:
    state = _session_state(ledger, issuer_session)
    if not isinstance(attestation, Mapping):
        _fail("ATTESTATION_MALFORMED")
    if attestation.get("run_id") != state["run_id"]:
        _fail("CROSS_RUN_REPLAY")
    if attestation.get("run_nonce") != state["run_nonce"]:
        _fail("RUN_NONCE_MISMATCH")
    if attestation.get("epoch") != state["epoch"]:
        _fail("RUN_EPOCH_MISMATCH")
    attestation_id = attestation.get("attestation_id")
    if not isinstance(attestation_id, str) or not attestation_id:
        _fail("ISSUER_LEDGER_ENTRY_MISSING")
    entry = ledger._entries.get(attestation_id)
    if entry is None:
        _fail("ISSUER_LEDGER_ENTRY_MISSING")
    if not entry.get("active"):
        _fail("ATTESTATION_REVOKED")
    for field in ("run_id", "run_nonce", "epoch", "attestation_id"):
        if entry.get(field) != attestation.get(field):
            _fail("ISSUER_LEDGER_ENTRY_MISMATCH", field)
    supplied_hash = attestation.get("attestation_sha256")
    if supplied_hash != _attestation_content_hash(attestation):
        _fail("ATTESTATION_HASH_MISMATCH")
    if entry.get("canonical_attestation_digest") != _attestation_ledger_digest(attestation):
        _fail("ISSUER_LEDGER_DIGEST_MISMATCH")
    return entry


def _current_fused(raw_snapshot: Mapping[str, Any]) -> dict[tuple[int, float], dict[str, Any]]:
    _reject_raw_authority_labels(raw_snapshot)
    _listener_map(raw_snapshot)
    fused, _ = _fuse_sources(raw_snapshot)
    return fused


def _find_pid(
    fused: Mapping[tuple[int, float], Mapping[str, Any]], pid: int
) -> tuple[tuple[int, float], dict[str, Any]] | None:
    matches = [(identity, copy.deepcopy(row)) for identity, row in fused.items() if identity[0] == pid]
    if len(matches) > 1:
        _fail("DUPLICATE_PID", pid)
    return matches[0] if matches else None


def verify_temporal_attestation(
    attestation: Mapping[str, Any],
    current_raw_snapshot: Mapping[str, Any],
    locked_runner_record: Mapping[str, Any],
    locked_known_paths: Sequence[Mapping[str, Any]],
    controlled_ports: Sequence[int],
    contract_version: str,
    contract_sha256: str,
    implementation_sha256: str,
    implementation_blob_oid: str,
    ledger: RunLocalIssuerLedger,
    issuer_session: Mapping[str, Any],
) -> dict[str, Any]:
    ledger = _require_ledger(ledger)
    with ledger._lock:
        _ledger_precheck(attestation, ledger, issuer_session)
        birth_raw = attestation.get("birth_raw_snapshot")
        sealed = attestation.get("sealed_view")
        if not isinstance(birth_raw, Mapping) or not isinstance(sealed, Mapping):
            _fail("ATTESTATION_BIRTH_EVIDENCE_MISSING")
        verified = verify_sealed_authorization_views(
            birth_raw,
            sealed,
            locked_runner_record,
            locked_known_paths,
            controlled_ports,
            contract_version,
            contract_sha256,
            implementation_sha256,
            implementation_blob_oid,
        )
        candidate_identity = _coerce_identity(attestation.get("candidate_identity_key"))
        expected_candidate, expected_chain = _candidate_and_chain(
            verified.recomputed, candidate_identity
        )
        if not _canonical_equal(attestation.get("birth_candidate_record"), expected_candidate):
            _fail("BIRTH_CANDIDATE_MISMATCH")
        if not _canonical_equal(attestation.get("birth_chain"), expected_chain):
            _fail("BIRTH_CHAIN_MISMATCH")

        try:
            current_views = derive_authorization_views(
                current_raw_snapshot,
                locked_runner_record,
                locked_known_paths,
                controlled_ports,
                contract_version,
                contract_sha256,
                implementation_sha256,
            )
        except M13ContractError as exc:
            if exc.code == "LOCKED_RUNNER_IDENTITY_MISMATCH":
                raise M13ContractError("RUNNER_ROOT_IDENTITY_MISMATCH", exc.detail) from exc
            raise
        fused = _current_fused(current_raw_snapshot)
        current = _find_pid(fused, candidate_identity[0])
        for birth_parent in expected_chain[1:-1]:
            parent_identity = _identity(birth_parent)
            current_parent = _find_pid(fused, parent_identity[0])
            if current_parent is not None and current_parent[0] != parent_identity:
                _fail("PARENT_PID_REUSE", parent_identity[0])
        if current is None:
            return {
                "accepted": True,
                "candidate_identity_key": _identity_json(candidate_identity),
                "historical_only": True,
                "current_authority": False,
                "decision": "ACCEPT_HISTORICAL_CLASSIFICATION_ONLY",
            }
        current_identity, current_record = current
        if current_identity != candidate_identity:
            _fail("CHILD_PID_REUSE", candidate_identity[0])
        _validate_critical_row(current_record)
        if _normalized_path(current_record.get("exe")) != _normalized_path(
            expected_candidate.get("exe")
        ):
            _fail("CURRENT_HISTORY_CONFLICT")
        if _normalized_hash(current_record.get("exe_sha256")) != _normalized_hash(
            expected_candidate.get("exe_sha256")
        ):
            _fail("CURRENT_HISTORY_CONFLICT")
        if _normalized_command(_command_from_row(current_record)) != _normalized_command(
            _command_from_row(expected_candidate)
        ):
            _fail("CURRENT_HISTORY_CONFLICT")
        if candidate_identity not in _view_identities(
            current_views["project_authorization_candidates"]
        ):
            _fail("CURRENT_CANDIDATE_NOT_AUTHORIZED")
        return {
            "accepted": True,
            "candidate_identity_key": _identity_json(candidate_identity),
            "historical_only": False,
            "current_authority": True,
            "decision": "ACCEPT_CURRENT_BIRTH_PROVENANCE",
        }


def terminate_issuer_run(
    ledger: RunLocalIssuerLedger, issuer_session: Mapping[str, Any]
) -> dict[str, Any]:
    ledger = _require_ledger(ledger)
    with ledger._lock:
        state = _session_state(ledger, issuer_session, permit_tombstone=True)
        if state["tombstoned"]:
            _fail("RUN_TOMBSTONED")
        state["active"] = False
        state["tombstoned"] = True
        state["epoch"] += 1
        revoked = 0
        for entry in ledger._entries.values():
            if entry.get("run_id") == state["run_id"] and entry.get("run_nonce") == state["run_nonce"]:
                if entry.get("active"):
                    revoked += 1
                entry["active"] = False
        return {
            "run_id": state["run_id"],
            "tombstoned": True,
            "revoked_entries": revoked,
            "epoch": state["epoch"],
        }


def evaluate_temporal_replay(
    attestations: Sequence[Mapping[str, Any]],
    current_raw_snapshot: Mapping[str, Any],
    locked_runner_record: Mapping[str, Any],
    locked_known_paths: Sequence[Mapping[str, Any]],
    controlled_ports: Sequence[int],
    contract_version: str,
    contract_sha256: str,
    implementation_sha256: str,
    implementation_blob_oid: str,
    ledger: RunLocalIssuerLedger,
    issuer_session: Mapping[str, Any],
) -> dict[str, Any]:
    historical = 0
    historical_authority = 0
    current_count = 0
    for attestation in attestations:
        decision = verify_temporal_attestation(
            attestation,
            current_raw_snapshot,
            locked_runner_record,
            locked_known_paths,
            controlled_ports,
            contract_version,
            contract_sha256,
            implementation_sha256,
            implementation_blob_oid,
            ledger,
            issuer_session,
        )
        if decision["historical_only"]:
            historical += 1
            if decision["current_authority"]:
                historical_authority += 1
        else:
            current_count += 1
    return {
        "historical_exited_count": historical,
        "historical_exited_authority_count": historical_authority,
        "current_attested_count": current_count,
        "support_role_authority_count": 0,
        "support_cleanup_target_count": 0,
    }


__all__ = [
    "CONTRACT_SHA256",
    "CONTRACT_VERSION",
    "M13ContractError",
    "RunLocalIssuerLedger",
    "begin_issuer_run",
    "canonical_bytes",
    "canonical_sha256",
    "create_run_local_issuer_ledger",
    "derive_authorization_views",
    "evaluate_temporal_replay",
    "implementation_blob_oid",
    "implementation_sha256",
    "issue_temporal_attestation",
    "seal_authorization_views",
    "terminate_issuer_run",
    "verify_sealed_authorization_views",
    "verify_temporal_attestation",
]
