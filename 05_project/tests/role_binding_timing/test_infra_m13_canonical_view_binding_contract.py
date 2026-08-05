"""Frozen canonical-view gates for INFRA-M13.

This is a post-diagnosis DEV engineering contract, not held-out evidence.
The implementation is intentionally absent at freeze time. Do not execute
this file before a separately reviewed implementation lock exists.
"""

from __future__ import annotations

import copy
import hashlib
import importlib
import json
from pathlib import Path

import pytest

from raven_m.role_binding_timing.infra_m9_authorization_views import derive_process_views


MODULE = "raven_m.role_binding_timing.infra_m13_proof_bound_attestation"
ROOT = Path(__file__).resolve().parents[3]
CONTRACT_VERSION = "infra-m13-proof-bound-role-views-v1"
CONTRACT_SHA256 = "52A2914DCB4152B30CDBA50F5F0E8E3CF8EF1C614694E5544ABE7EB253418519"
CONTROLLED_PORTS = [5037, 5038, 5554, 5555, 8554]
VIEW_NAMES = (
    "trusted_runner_root",
    "project_authorization_candidates",
    "support_only_ancestry_nodes",
    "unrelated_observed_processes",
)


def _sut():
    return importlib.import_module(MODULE)


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def _canonical_sha(value) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _row(pid: int, ctime: float, ppid: int, name: str):
    exe = f"C:/infra-m13-fixture/{name}.exe"
    return {
        "pid": pid,
        "create_time": ctime,
        "ppid": ppid,
        "name": name,
        "exe": exe,
        "exe_sha256": _sha_text(exe.lower()),
        "command_line": [exe, "--fixture"],
        "accessibility_status": "accessible",
        "access_error": None,
    }


def _fixture():
    runner = _row(101, 1000.0, 1, "runner")
    support = _row(201, 1001.0, 101, "wrapper")
    candidate = _row(301, 1002.0, 201, "client")
    unrelated = _row(401, 1003.0, 1, "unrelated")
    rows = [runner, support, candidate, unrelated]
    raw = {
        "schema_version": "role_binding_timing.infra_m13.raw_process_snapshot.fixture.v1",
        "sample_sequence": 13,
        "sample_time_utc": "2026-08-05T01:13:00Z",
        "observation_universe_complete": True,
        "observation_universe_capture_errors": [],
        "all_processes": copy.deepcopy(rows),
        "structural_processes": copy.deepcopy(rows),
        "all_tcp_listener_ports_by_pid": {},
        "listener_evidence_complete": True,
    }
    known = [
        {
            "logical_role": "client",
            "normalized_path": candidate["exe"],
            "exe_sha256": candidate["exe_sha256"],
        }
    ]
    return raw, runner, known, (candidate["pid"], candidate["create_time"])


def _derive(raw=None, runner=None, known=None, ports=None):
    base_raw, base_runner, base_known, _ = _fixture()
    return _sut().derive_authorization_views(
        raw_snapshot=raw or base_raw,
        locked_runner_record=runner or base_runner,
        locked_known_paths=known or base_known,
        controlled_ports=ports or CONTROLLED_PORTS,
        contract_version=CONTRACT_VERSION,
        contract_sha256=CONTRACT_SHA256,
        implementation_sha256=_sut().implementation_sha256(),
    )


def _seal(raw=None, runner=None, known=None, ports=None):
    base_raw, base_runner, base_known, _ = _fixture()
    actual_raw = raw or base_raw
    actual_runner = runner or base_runner
    actual_known = known or base_known
    actual_ports = ports or CONTROLLED_PORTS
    derived = _derive(actual_raw, actual_runner, actual_known, actual_ports)
    return _sut().seal_authorization_views(
        raw_snapshot=actual_raw,
        derived_views={name: derived[name] for name in VIEW_NAMES},
        candidate_ancestry=derived["candidate_ancestry"],
        locked_runner_record=actual_runner,
        locked_known_paths=actual_known,
        controlled_ports=actual_ports,
        contract_version=CONTRACT_VERSION,
        contract_sha256=CONTRACT_SHA256,
        implementation_sha256=_sut().implementation_sha256(),
        implementation_blob_oid=_sut().implementation_blob_oid(),
    )


def _verify(sealed, raw=None, runner=None, known=None, ports=None):
    base_raw, base_runner, base_known, _ = _fixture()
    return _sut().verify_sealed_authorization_views(
        raw_snapshot=raw or base_raw,
        supplied_sealed_view=sealed,
        locked_runner_record=runner or base_runner,
        locked_known_paths=known or base_known,
        controlled_ports=ports or CONTROLLED_PORTS,
        contract_version=CONTRACT_VERSION,
        contract_sha256=CONTRACT_SHA256,
        implementation_sha256=_sut().implementation_sha256(),
        implementation_blob_oid=_sut().implementation_blob_oid(),
    )


def _assert_reject(callable_, code: str):
    with pytest.raises(_sut().M13ContractError) as caught:
        callable_()
    assert caught.value.code == code


def _rewrite_all_public_hashes(sealed):
    """Model an attacker recomputing every caller-visible content hash."""
    sealed["partition_hashes"] = {
        name: _canonical_sha(sealed["views"][name]) for name in VIEW_NAMES
    }
    for name in VIEW_NAMES:
        for row in sealed["views"][name]:
            if "partition_sha256" in row:
                row["partition_sha256"] = sealed["partition_hashes"][name]
    complete_payload = {
        "bindings": sealed["bindings"],
        "views": sealed["views"],
        "candidate_ancestry": sealed["candidate_ancestry"],
        "partition_hashes": sealed["partition_hashes"],
    }
    sealed["complete_view_sha256"] = _canonical_sha(complete_payload)
    seal_payload = copy.deepcopy(sealed)
    seal_payload.pop("seal_sha256", None)
    sealed["seal_sha256"] = _canonical_sha(seal_payload)


def _mutate_raw_both(raw, pid, field, value):
    for collection in ("all_processes", "structural_processes"):
        row = next(item for item in raw[collection] if item["pid"] == pid)
        if value is _DELETE:
            row.pop(field, None)
        else:
            row[field] = copy.deepcopy(value)


_DELETE = object()


def _identities(rows):
    return {(row["pid"], row["create_time"]) for row in rows}


def test_baseline_four_views_are_rederived_and_cover_the_universe():
    derived = _derive()
    assert _identities(derived["trusted_runner_root"]) == {(101, 1000.0)}
    assert _identities(derived["project_authorization_candidates"]) == {(301, 1002.0)}
    assert _identities(derived["support_only_ancestry_nodes"]) == {(201, 1001.0)}
    assert _identities(derived["unrelated_observed_processes"]) == {(401, 1003.0)}
    assert derived["views_disjoint"] is True
    assert derived["universe_covered"] is True


@pytest.mark.parametrize(
    "field",
    [
        "role",
        "observed_class",
        "view_class",
        "authorization_candidate_reasons",
        "role_authority",
        "adoptable",
        "kill_target",
        "cleanup_target",
    ],
)
@pytest.mark.parametrize("collection", ["all_processes", "structural_processes"])
def test_raw_authority_self_labels_are_rejected_in_both_sources(field, collection):
    raw, runner, known, _ = _fixture()
    raw[collection][2][field] = "caller_asserted"
    _assert_reject(lambda: _derive(raw, runner, known), "RAW_AUTHORITY_LABEL_PRESENT")


@pytest.mark.parametrize(
    ("source_view", "pid"),
    [("support_only_ancestry_nodes", 201), ("unrelated_observed_processes", 401)],
)
def test_noncandidate_cannot_be_moved_to_candidate_even_after_full_public_rehash(source_view, pid):
    raw, runner, known, _ = _fixture()
    sealed = _seal(raw, runner, known)
    row = next(item for item in sealed["views"][source_view] if item["pid"] == pid)
    sealed["views"][source_view].remove(row)
    sealed["views"]["project_authorization_candidates"].append(row)
    _rewrite_all_public_hashes(sealed)
    _assert_reject(
        lambda: _verify(sealed, raw, runner, known),
        "SEALED_CANONICAL_VIEW_MISMATCH",
    )


def test_fake_trusted_runner_is_rejected():
    raw, _, known, _ = _fixture()
    fake = copy.deepcopy(raw["all_processes"][-1])
    _assert_reject(lambda: _derive(raw, fake, known), "LOCKED_RUNNER_IDENTITY_MISMATCH")


def test_candidate_reason_tamper_is_rejected_after_full_public_rehash():
    raw, runner, known, _ = _fixture()
    sealed = _seal(raw, runner, known)
    sealed["views"]["project_authorization_candidates"][0][
        "authorization_candidate_reasons"
    ] = ["CALLER_ASSERTED_REASON"]
    _rewrite_all_public_hashes(sealed)
    _assert_reject(lambda: _verify(sealed, raw, runner, known), "SEALED_CANONICAL_VIEW_MISMATCH")


def test_known_path_configuration_tamper_is_rejected():
    raw, runner, known, _ = _fixture()
    sealed = _seal(raw, runner, known)
    changed = copy.deepcopy(known)
    changed[0]["normalized_path"] = "C:/infra-m13-fixture/other.exe"
    _assert_reject(lambda: _verify(sealed, raw, runner, changed), "LOCKED_INPUT_MISMATCH")


def test_controlled_port_evidence_tamper_is_rejected():
    raw, runner, known, _ = _fixture()
    raw["all_tcp_listener_ports_by_pid"] = {"401": [8554]}
    sealed = _seal(raw, runner, known)
    current = copy.deepcopy(raw)
    current["all_tcp_listener_ports_by_pid"] = {}
    _assert_reject(
        lambda: _verify(sealed, current, runner, known),
        "CONTROLLED_PORT_EVIDENCE_MISMATCH",
    )


@pytest.mark.parametrize(
    ("binding", "value"),
    [
        ("contract_version", "wrong-version"),
        ("contract_sha256", "0" * 64),
        ("implementation_sha256", "0" * 64),
        ("implementation_blob_oid", "0" * 40),
    ],
)
def test_classifier_or_implementation_binding_tamper_is_rejected(binding, value):
    raw, runner, known, _ = _fixture()
    sealed = _seal(raw, runner, known)
    sealed["bindings"][binding] = value
    _rewrite_all_public_hashes(sealed)
    _assert_reject(lambda: _verify(sealed, raw, runner, known), "CLASSIFIER_BINDING_MISMATCH")


def test_sealed_view_raw_snapshot_mismatch_is_rejected():
    raw, runner, known, _ = _fixture()
    sealed = _seal(raw, runner, known)
    current = copy.deepcopy(raw)
    _mutate_raw_both(current, 401, "command_line", ["C:/changed.exe"])
    _assert_reject(lambda: _verify(sealed, current, runner, known), "RAW_SNAPSHOT_MISMATCH")


def test_same_pid_different_create_time_is_rejected():
    raw, runner, known, _ = _fixture()
    sealed = _seal(raw, runner, known)
    current = copy.deepcopy(raw)
    _mutate_raw_both(current, 301, "create_time", 9999.0)
    _assert_reject(lambda: _verify(sealed, current, runner, known), "PID_CREATE_TIME_REUSE")


@pytest.mark.parametrize(
    ("view_name", "field", "value"),
    [
        ("trusted_runner_root", "name", "tampered-runner"),
        ("project_authorization_candidates", "exe", "C:/tampered-candidate.exe"),
        ("support_only_ancestry_nodes", "command_line", ["C:/tampered-support.exe"]),
        ("unrelated_observed_processes", "accessibility_status", "tampered"),
    ],
)
def test_any_partition_nonidentity_field_tamper_rejects_after_rehash(view_name, field, value):
    raw, runner, known, _ = _fixture()
    sealed = _seal(raw, runner, known)
    sealed["views"][view_name][0][field] = value
    _rewrite_all_public_hashes(sealed)
    _assert_reject(lambda: _verify(sealed, raw, runner, known), "SEALED_CANONICAL_VIEW_MISMATCH")


@pytest.mark.parametrize("view_name", VIEW_NAMES)
@pytest.mark.parametrize("operation", ["add", "delete"])
def test_extra_or_missing_row_field_is_rejected_after_rehash(view_name, operation):
    raw, runner, known, _ = _fixture()
    sealed = _seal(raw, runner, known)
    row = sealed["views"][view_name][0]
    if operation == "add":
        row["attacker_extra"] = "not-allowed"
    else:
        row.pop("name")
    _rewrite_all_public_hashes(sealed)
    _assert_reject(lambda: _verify(sealed, raw, runner, known), "SEALED_CANONICAL_VIEW_MISMATCH")


def test_source_record_hash_string_cannot_mask_row_tamper_after_rehash():
    raw, runner, known, _ = _fixture()
    sealed = _seal(raw, runner, known)
    row = sealed["views"]["support_only_ancestry_nodes"][0]
    row["exe"] = "C:/attacker/replaced.exe"
    row["source_record_sha256"] = _canonical_sha(row)
    _rewrite_all_public_hashes(sealed)
    _assert_reject(lambda: _verify(sealed, raw, runner, known), "SEALED_CANONICAL_VIEW_MISMATCH")


@pytest.mark.parametrize("mutation", ["field", "reorder", "insert", "delete"])
def test_candidate_ancestry_is_exactly_recomputed_and_compared(mutation):
    raw, runner, known, _ = _fixture()
    sealed = _seal(raw, runner, known)
    ancestry = sealed["candidate_ancestry"]
    if mutation == "field":
        ancestry[0]["complete_within_bound"] = False
    elif mutation == "reorder":
        ancestry[0]["chain"] = list(reversed(ancestry[0]["chain"]))
    elif mutation == "insert":
        ancestry[0]["chain"].insert(0, copy.deepcopy(ancestry[0]["chain"][0]))
    else:
        ancestry[0]["chain"].pop()
    _rewrite_all_public_hashes(sealed)
    _assert_reject(lambda: _verify(sealed, raw, runner, known), "CANDIDATE_ANCESTRY_MISMATCH")


def test_all_processes_and_structural_processes_field_conflict_fails_closed():
    raw, runner, known, _ = _fixture()
    raw["structural_processes"][2]["command_line"] = ["C:/conflict.exe"]
    _assert_reject(lambda: _derive(raw, runner, known), "RAW_SOURCE_FIELD_CONFLICT")


def test_missing_structural_universe_row_fails_closed():
    raw, runner, known, _ = _fixture()
    raw["structural_processes"] = raw["structural_processes"][:-1]
    _assert_reject(lambda: _derive(raw, runner, known), "OBSERVATION_UNIVERSE_MISMATCH")


def _merge(base, override):
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _resolve_overlay(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if "base_config" not in data:
        return data
    return _merge(_resolve_overlay(ROOT / data["base_config"]), data.get("overrides", {}))


def test_exact_locked_m9_deriver_membership_compatibility_replay():
    config = _resolve_overlay(
        ROOT / "05_project/configs/role_binding_timing/infra_m9_authorization_view_separation.json"
    )
    known = [
        {
            "logical_role": name,
            "normalized_path": entry["path"],
            "exe_sha256": entry["sha256"],
        }
        for name, entry in sorted(config["process_identity"]["binaries"].items())
        if name in {"adb", "emulator_launcher", "qemu", "crashpad", "netsimd"}
    ]
    snapshot_root = ROOT / (
        "05_project/artifacts/role_binding_timing/infra_m9_authorization_view_separation/"
        "process_identity/snapshots"
    )
    paths = sorted(snapshot_root.glob("*/process_snapshot.json"))
    assert paths
    for path in paths:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        runner = copy.deepcopy(snapshot["process_views"]["trusted_runner_root"])
        expected, _, _, _ = derive_process_views(snapshot, config=config, runner_record=runner)
        raw = copy.deepcopy(snapshot)
        raw.pop("process_views", None)
        actual = _derive(raw, runner, known, CONTROLLED_PORTS)
        for view_name in VIEW_NAMES:
            expected_rows = expected[view_name]
            if isinstance(expected_rows, dict):
                expected_rows = [expected_rows]
            assert _identities(actual[view_name]) == _identities(expected_rows), path
