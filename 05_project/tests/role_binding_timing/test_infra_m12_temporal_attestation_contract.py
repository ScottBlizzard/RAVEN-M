"""Frozen temporal gates for the INFRA-M12 DEV engineering contract.

The offline runner must refuse to execute this file unless the frozen M12
role-derivation test file has already passed unchanged.
"""

from __future__ import annotations

import copy
import hashlib
import importlib

import pytest


MODULE = "raven_m.role_binding_timing.infra_m12_sealed_role_derivation"
RUN_A = "m12-dev-run-a"
RUN_B = "m12-dev-run-b"
VERSION = "infra-m12-derive-authorization-views-v1"
CONTRACT_SHA256 = "973192F1D6153F099D9BCC38E784B4C9E2F5203F9CAC77910B349BCCE31D70A0"
PORTS = [5037, 5038, 5554, 5555, 8554]


def _sut():
    return importlib.import_module(MODULE)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def _row(pid, ctime, ppid, name, path=None):
    exe = path or f"C:/m12-fixture/{name}.exe"
    return {
        "pid": pid,
        "create_time": ctime,
        "ppid": ppid,
        "name": name,
        "exe": exe,
        "exe_sha256": _sha(exe.lower()),
        "command_line": [exe, "--fixture"],
        "accessibility_status": "accessible",
        "access_error": None,
    }


def _sample(sequence=7):
    runner = _row(100, 1000.0, 1, "runner")
    support = _row(200, 1001.0, 100, "support")
    candidate = _row(300, 1002.0, 200, "client")
    unrelated = _row(400, 1003.0, 1, "unrelated")
    rows = [runner, support, candidate, unrelated]
    raw = {
        "schema_version": "role_binding_timing.infra_m12.raw_process_snapshot.fixture.v1",
        "sample_sequence": sequence,
        "sample_time_utc": f"2026-08-05T00:00:{sequence:02d}Z",
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


def _issue(raw=None, runner=None, known=None, candidate_identity=None, run_id=RUN_A):
    base_raw, base_runner, base_known, base_candidate = _sample()
    return _sut().issue_temporal_attestation(
        raw_snapshot=raw or base_raw,
        locked_runner_record=runner or base_runner,
        locked_known_paths=known or base_known,
        controlled_ports=PORTS,
        classifier_version=VERSION,
        classifier_contract_sha256=CONTRACT_SHA256,
        classifier_implementation_sha256=_sut().implementation_sha256(),
        classifier_implementation_blob_oid=_sut().implementation_blob_oid(),
        candidate_identity_key=candidate_identity or base_candidate,
        run_id=run_id,
    )


def _verify(attestation, current=None, runner=None, known=None, run_id=RUN_A):
    base_raw, base_runner, base_known, _ = _sample()
    return _sut().verify_temporal_attestation(
        attestation=attestation,
        current_raw_snapshot=current or base_raw,
        locked_runner_record=runner or base_runner,
        locked_known_paths=known or base_known,
        controlled_ports=PORTS,
        classifier_version=VERSION,
        classifier_contract_sha256=CONTRACT_SHA256,
        classifier_implementation_sha256=_sut().implementation_sha256(),
        classifier_implementation_blob_oid=_sut().implementation_blob_oid(),
        run_id=run_id,
    )


def _assert_reject(callable_, code):
    with pytest.raises(_sut().TemporalAttestationError) as caught:
        callable_()
    assert caught.value.code == code


def _mutate_row(raw, pid, field, value):
    for collection in ("all_processes", "structural_processes"):
        row = next(item for item in raw[collection] if item["pid"] == pid)
        row[field] = value


def test_lossless_support_projection_keeps_proof_fields_without_authority():
    raw, runner, known, candidate = _sample()
    attestation = _issue(raw, runner, known, candidate)
    support = attestation["sealed_view"]["views"]["support_only_ancestry_nodes"][0]
    source = next(row for row in raw["structural_processes"] if row["pid"] == 200)
    for field in ("pid", "create_time", "ppid", "exe", "exe_sha256", "command_line"):
        assert support[field] == source[field]
    for field in (
        "source_record_sha256",
        "raw_snapshot_sha256",
        "partition_sha256",
        "sample_sequence",
        "sample_time_utc",
    ):
        assert support[field]
    assert support["role_authority"] is False
    assert support["adoptable"] is False
    assert support["kill_target"] is False
    assert support["cleanup_target"] is False


def test_same_atomic_sample_attestation_is_accepted():
    raw, runner, known, candidate = _sample()
    attestation = _issue(raw, runner, known, candidate)
    decision = _verify(attestation, raw, runner, known)
    assert decision["accepted"] is True
    assert decision["candidate_identity_key"] == candidate


def test_cross_frame_parent_chain_stitch_is_rejected_even_after_partition_rehash():
    raw, runner, known, candidate = _sample()
    attestation = _issue(raw, runner, known, candidate)
    support = attestation["sealed_view"]["views"]["support_only_ancestry_nodes"][0]
    support["sample_sequence"] += 1
    attestation["sealed_view"]["partition_hashes"] = _sut().hash_partitions(
        attestation["sealed_view"]["views"]
    )
    _assert_reject(lambda: _verify(attestation, raw, runner, known), "CROSS_SAMPLE_STITCHING")


@pytest.mark.parametrize(
    ("pid", "code"),
    [(200, "PARENT_PID_REUSE"), (300, "CHILD_PID_REUSE")],
)
def test_parent_or_child_pid_reuse_is_rejected(pid, code):
    birth, runner, known, candidate = _sample()
    attestation = _issue(birth, runner, known, candidate)
    current = copy.deepcopy(birth)
    _mutate_row(current, pid, "create_time", 9999.0)
    _assert_reject(lambda: _verify(attestation, current, runner, known), code)


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("create_time", None, "MISSING_CREATE_TIME"),
        ("exe_sha256", None, "MISSING_EXE_SHA256"),
        ("command_line", None, "MISSING_COMMAND_LINE"),
    ],
)
def test_missing_critical_support_field_is_rejected(field, value, code):
    raw, runner, known, candidate = _sample()
    _mutate_row(raw, 200, field, value)
    _assert_reject(lambda: _issue(raw, runner, known, candidate), code)


def test_access_denied_critical_support_field_is_rejected():
    raw, runner, known, candidate = _sample()
    _mutate_row(raw, 200, "accessibility_status", "access_denied")
    _mutate_row(raw, 200, "access_error", "AccessDenied")
    _assert_reject(lambda: _issue(raw, runner, known, candidate), "CRITICAL_FIELD_ACCESS_DENIED")


@pytest.mark.parametrize(
    ("field", "code"),
    [
        ("source_record_sha256", "SOURCE_RECORD_HASH_MISMATCH"),
        ("raw_snapshot_sha256", "RAW_SNAPSHOT_HASH_MISMATCH"),
        ("partition_sha256", "PARTITION_HASH_MISMATCH"),
    ],
)
def test_attestation_proof_hash_tamper_is_rejected(field, code):
    raw, runner, known, candidate = _sample()
    attestation = _issue(raw, runner, known, candidate)
    attestation["sealed_view"]["views"]["support_only_ancestry_nodes"][0][field] = "0" * 64
    _assert_reject(lambda: _verify(attestation, raw, runner, known), code)


def test_cross_run_replay_is_rejected():
    raw, runner, known, candidate = _sample()
    attestation = _issue(raw, runner, known, candidate, RUN_A)
    _assert_reject(lambda: _verify(attestation, raw, runner, known, RUN_B), "CROSS_RUN_REPLAY")


def test_current_evidence_conflict_has_priority_over_birth_attestation():
    birth, runner, known, candidate = _sample()
    attestation = _issue(birth, runner, known, candidate)
    current = copy.deepcopy(birth)
    _mutate_row(current, 300, "command_line", ["C:/different-command.exe"])
    _assert_reject(lambda: _verify(attestation, current, runner, known), "CURRENT_HISTORY_CONFLICT")


def test_support_controlled_port_ownership_is_rejected():
    raw, runner, known, candidate = _sample()
    raw["all_tcp_listener_ports_by_pid"] = {"200": [5038]}
    _assert_reject(lambda: _issue(raw, runner, known, candidate), "SUPPORT_CONTROLLED_PORT_CONFLICT")


@pytest.mark.parametrize("field", ["role_authority", "adoptable", "kill_target", "cleanup_target"])
def test_support_authority_or_lifecycle_tamper_is_rejected(field):
    raw, runner, known, candidate = _sample()
    attestation = _issue(raw, runner, known, candidate)
    attestation["sealed_view"]["views"]["support_only_ancestry_nodes"][0][field] = True
    _assert_reject(lambda: _verify(attestation, raw, runner, known), "SUPPORT_AUTHORITY_TAMPER")


def test_support_identity_cannot_masquerade_as_candidate():
    raw, runner, known, _ = _sample()
    _assert_reject(
        lambda: _issue(raw, runner, known, (200, 1001.0)),
        "IDENTITY_NOT_DERIVED_CANDIDATE",
    )


def test_missing_parent_chain_is_rejected():
    raw, runner, known, candidate = _sample()
    for collection in ("all_processes", "structural_processes"):
        raw[collection] = [row for row in raw[collection] if row["pid"] != 200]
    _assert_reject(lambda: _issue(raw, runner, known, candidate), "MISSING_PARENT_CHAIN")


def test_runner_identity_reuse_is_rejected_during_current_recomputation():
    birth, runner, known, candidate = _sample()
    attestation = _issue(birth, runner, known, candidate)
    current = copy.deepcopy(birth)
    _mutate_row(current, 100, "create_time", 5555.0)
    _assert_reject(lambda: _verify(attestation, current, runner, known), "RUNNER_ROOT_IDENTITY_MISMATCH")


def test_terminal_expiry_is_irreversible():
    raw, runner, known, candidate = _sample()
    attestation = _issue(raw, runner, known, candidate)
    _sut().expire_run_local_attestations(RUN_A)
    _assert_reject(lambda: _verify(attestation, raw, runner, known), "ATTESTATION_EXPIRED")


def test_twelve_exited_one_current_replay_never_grants_exited_authority():
    runner = _row(100, 1000.0, 1, "runner")
    rows = [runner]
    known = []
    candidate_keys = []
    for index in range(13):
        support = _row(1000 + index, 2000.0 + index, 100, f"support_{index}")
        candidate = _row(2000 + index, 3000.0 + index, support["pid"], f"client_{index}")
        rows.extend([support, candidate])
        known.append(
            {
                "logical_role": f"client_{index}",
                "normalized_path": candidate["exe"],
                "exe_sha256": candidate["exe_sha256"],
            }
        )
        candidate_keys.append((candidate["pid"], candidate["create_time"]))
    birth = {
        "schema_version": "role_binding_timing.infra_m12.raw_process_snapshot.fixture.v1",
        "sample_sequence": 11,
        "sample_time_utc": "2026-08-05T00:00:11Z",
        "observation_universe_complete": True,
        "observation_universe_capture_errors": [],
        "all_processes": copy.deepcopy(rows),
        "structural_processes": copy.deepcopy(rows),
        "all_tcp_listener_ports_by_pid": {},
        "listener_evidence_complete": True,
    }
    attestations = [
        _issue(birth, runner, known, identity, RUN_A) for identity in candidate_keys
    ]
    live_candidate = next(row for row in rows if row["pid"] == candidate_keys[-1][0])
    current_rows = [runner, live_candidate]
    current = {
        "schema_version": birth["schema_version"],
        "sample_sequence": 12,
        "sample_time_utc": "2026-08-05T00:00:12Z",
        "observation_universe_complete": True,
        "observation_universe_capture_errors": [],
        "all_processes": copy.deepcopy(current_rows),
        "structural_processes": copy.deepcopy(current_rows),
        "all_tcp_listener_ports_by_pid": {},
        "listener_evidence_complete": True,
    }
    result = _sut().evaluate_temporal_replay(
        attestations=attestations,
        current_raw_snapshot=current,
        locked_runner_record=runner,
        locked_known_paths=known,
        controlled_ports=PORTS,
        classifier_version=VERSION,
        classifier_contract_sha256=CONTRACT_SHA256,
        classifier_implementation_sha256=_sut().implementation_sha256(),
        classifier_implementation_blob_oid=_sut().implementation_blob_oid(),
        run_id=RUN_A,
    )
    assert result["historical_exited_count"] == 12
    assert result["historical_exited_authority_count"] == 0
    assert result["current_attested_count"] == 1
    assert result["support_role_authority_count"] == 0
    assert result["support_cleanup_target_count"] == 0
