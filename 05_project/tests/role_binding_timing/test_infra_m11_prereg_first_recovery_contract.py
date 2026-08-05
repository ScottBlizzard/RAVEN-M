"""Frozen preregistration tests for INFRA-M11.

These tests intentionally import the future M11 implementation lazily. At the
freeze commit that module does not exist, so this suite is NOT RUN and is
expected to fail if executed. Do not weaken or rewrite these tests after
implementation or result inspection.
"""

from __future__ import annotations

import copy
import hashlib
import importlib
import json

import pytest


MODULE = "raven_m.role_binding_timing.infra_m11_prereg_first_recovery"
RUN_ID = "m11-fixture-run-a"
OTHER_RUN_ID = "m11-fixture-run-b"
SAMPLE_TIME = "2026-08-05T00:00:00Z"


def _sut():
    return importlib.import_module(MODULE)


def _canonical_sha(value) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def _record(
    pid: int,
    create_time: float,
    ppid: int,
    parent_identity_key: str | None,
    role: str,
    *,
    sequence: int = 7,
    ports: list[int] | None = None,
):
    row = {
        "identity_key": f"{pid}:{create_time:.6f}",
        "pid": pid,
        "create_time": create_time,
        "ppid": ppid,
        "parent_identity_key": parent_identity_key,
        "exe": f"C:/locked/{role}.exe",
        "exe_sha256": hashlib.sha256(role.encode("utf-8")).hexdigest().upper(),
        "cmdline": [f"C:/locked/{role}.exe", "--frozen-fixture"],
        "sample_sequence": sequence,
        "sample_time_utc": SAMPLE_TIME,
        "accessibility_status": "accessible",
        "access_error": None,
        "listening_ports": list(ports or []),
        "observed_class": role,
    }
    row["source_record_sha256"] = _canonical_sha(row)
    return row


def _seal_sample(records: list[dict], *, sequence: int = 7, run_id: str = RUN_ID):
    rows = copy.deepcopy(records)
    for row in rows:
        row.pop("source_record_sha256", None)
        row.pop("source_snapshot_sha256", None)
        row.pop("partition_sha256", None)
        row["sample_sequence"] = sequence
        row["sample_time_utc"] = SAMPLE_TIME
        row["source_record_sha256"] = _canonical_sha(row)
    raw_basis = {
        "run_id": run_id,
        "sample_sequence": sequence,
        "sample_time_utc": SAMPLE_TIME,
        "records": rows,
    }
    snapshot_hash = _canonical_sha(raw_basis)
    partition_basis = {
        "run_id": run_id,
        "sample_sequence": sequence,
        "source_snapshot_sha256": snapshot_hash,
        "identities": sorted(row["identity_key"] for row in rows),
        "classes": {row["identity_key"]: row["observed_class"] for row in rows},
    }
    partition_hash = _canonical_sha(partition_basis)
    for row in rows:
        row["source_snapshot_sha256"] = snapshot_hash
        row["partition_sha256"] = partition_hash
    return {
        "run_id": run_id,
        "sample_sequence": sequence,
        "sample_time_utc": SAMPLE_TIME,
        "source_snapshot_sha256": snapshot_hash,
        "partition_sha256": partition_hash,
        "records": rows,
    }


def _basic_sample(*, sequence: int = 7, run_id: str = RUN_ID):
    runner = _record(100, 1000.0, 1, None, "trusted_runner", sequence=sequence)
    support = _record(
        200,
        1001.0,
        100,
        runner["identity_key"],
        "support_only",
        sequence=sequence,
    )
    candidate = _record(
        300,
        1002.0,
        200,
        support["identity_key"],
        "runner_owned_adb_client",
        sequence=sequence,
    )
    return _seal_sample([runner, support, candidate], sequence=sequence, run_id=run_id)


def _by_role(sample: dict, role: str) -> dict:
    return next(row for row in sample["records"] if row["observed_class"] == role)


def _attest(sample: dict):
    sut = _sut()
    candidate = _by_role(sample, "runner_owned_adb_client")
    return sut.issue_temporal_attestation(
        run_id=sample["run_id"],
        atomic_sample=sample,
        candidate_identity_key=candidate["identity_key"],
    )


def _verify(attestation: dict, current_sample: dict, *, run_id: str = RUN_ID, terminal=False):
    return _sut().verify_temporal_attestation(
        attestation=attestation,
        current_atomic_sample=current_sample,
        run_id=run_id,
        terminal=terminal,
    )


def test_support_projection_is_lossless_and_never_authoritative():
    sample = _basic_sample()
    source = _by_role(sample, "support_only")
    projected = _sut().project_support_row(source_row=source, atomic_sample=sample)
    required = {
        "identity_key",
        "pid",
        "create_time",
        "ppid",
        "parent_identity_key",
        "exe",
        "exe_sha256",
        "cmdline",
        "sample_sequence",
        "sample_time_utc",
        "source_record_sha256",
        "source_snapshot_sha256",
        "partition_sha256",
        "accessibility_status",
        "access_error",
        "listening_ports",
    }
    assert {key: projected[key] for key in required} == {key: source[key] for key in required}
    assert projected["role_authority"] is False
    assert projected["adoptable"] is False
    assert projected["kill_target"] is False
    assert projected["cleanup_target"] is False


def test_same_atomic_sample_chain_is_accepted():
    sample = _basic_sample()
    attestation = _attest(sample)
    assert attestation["valid"] is True
    assert {node["sample_sequence"] for node in attestation["chain"]} == {sample["sample_sequence"]}
    assert {node["source_snapshot_sha256"] for node in attestation["chain"]} == {
        sample["source_snapshot_sha256"]
    }


def test_cross_frame_stitching_is_rejected():
    sample = _basic_sample()
    broken = copy.deepcopy(sample)
    support = _by_role(broken, "support_only")
    support["sample_sequence"] += 1
    decision = _sut().issue_temporal_attestation(
        run_id=RUN_ID,
        atomic_sample=broken,
        candidate_identity_key=_by_role(broken, "runner_owned_adb_client")["identity_key"],
    )
    assert decision == {"valid": False, "reason_code": "CROSS_SAMPLE_STITCHING"}


@pytest.mark.parametrize("role", ["support_only", "runner_owned_adb_client"])
def test_pid_reuse_is_rejected(role):
    birth = _basic_sample()
    attestation = _attest(birth)
    current = copy.deepcopy(birth)
    target = _by_role(current, role)
    target["create_time"] += 90.0
    target["identity_key"] = f'{target["pid"]}:{target["create_time"]:.6f}'
    decision = _verify(attestation, current)
    expected = "PARENT_PID_REUSE" if role == "support_only" else "CHILD_PID_REUSE"
    assert decision["accepted"] is False
    assert decision["reason_code"] == expected


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        ("create_time", "MISSING_CREATE_TIME"),
        ("exe_sha256", "MISSING_EXE_SHA256"),
        ("cmdline", "MISSING_CMDLINE"),
    ],
)
def test_missing_critical_identity_field_fails_closed(field, reason):
    sample = _basic_sample()
    _by_role(sample, "support_only")[field] = None
    decision = _sut().issue_temporal_attestation(
        run_id=RUN_ID,
        atomic_sample=sample,
        candidate_identity_key=_by_role(sample, "runner_owned_adb_client")["identity_key"],
    )
    assert decision == {"valid": False, "reason_code": reason}


def test_access_denied_on_critical_support_field_fails_closed():
    sample = _basic_sample()
    support = _by_role(sample, "support_only")
    support["accessibility_status"] = "access_denied"
    support["access_error"] = "AccessDenied"
    decision = _sut().issue_temporal_attestation(
        run_id=RUN_ID,
        atomic_sample=sample,
        candidate_identity_key=_by_role(sample, "runner_owned_adb_client")["identity_key"],
    )
    assert decision == {"valid": False, "reason_code": "CRITICAL_FIELD_ACCESS_DENIED"}


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        ("source_record_sha256", "SOURCE_RECORD_HASH_MISMATCH"),
        ("source_snapshot_sha256", "SOURCE_SNAPSHOT_HASH_MISMATCH"),
        ("partition_sha256", "PARTITION_HASH_MISMATCH"),
    ],
)
def test_tampered_hash_fails_closed(field, reason):
    sample = _basic_sample()
    _by_role(sample, "support_only")[field] = "0" * 64
    decision = _sut().issue_temporal_attestation(
        run_id=RUN_ID,
        atomic_sample=sample,
        candidate_identity_key=_by_role(sample, "runner_owned_adb_client")["identity_key"],
    )
    assert decision == {"valid": False, "reason_code": reason}


def test_cross_run_replay_is_rejected():
    sample = _basic_sample()
    decision = _verify(_attest(sample), sample, run_id=OTHER_RUN_ID)
    assert decision == {"accepted": False, "reason_code": "CROSS_RUN_REPLAY"}


def test_current_evidence_conflict_overrides_history():
    birth = _basic_sample()
    current = copy.deepcopy(birth)
    candidate = _by_role(current, "runner_owned_adb_client")
    candidate["cmdline"] = [candidate["exe"], "--different-current-command"]
    decision = _verify(_attest(birth), current)
    assert decision == {"accepted": False, "reason_code": "CURRENT_HISTORY_CONFLICT"}


def test_support_owning_5038_is_rejected():
    sample = _basic_sample()
    _by_role(sample, "support_only")["listening_ports"] = [5038]
    decision = _sut().issue_temporal_attestation(
        run_id=RUN_ID,
        atomic_sample=sample,
        candidate_identity_key=_by_role(sample, "runner_owned_adb_client")["identity_key"],
    )
    assert decision == {"valid": False, "reason_code": "SUPPORT_CONTROLLED_PORT_CONFLICT"}


@pytest.mark.parametrize("field", ["role_authority", "adoptable", "kill_target", "cleanup_target"])
def test_support_privilege_escalation_is_rejected(field):
    sample = _basic_sample()
    support = _by_role(sample, "support_only")
    support[field] = True
    decision = _sut().issue_temporal_attestation(
        run_id=RUN_ID,
        atomic_sample=sample,
        candidate_identity_key=_by_role(sample, "runner_owned_adb_client")["identity_key"],
    )
    assert decision["valid"] is False
    assert decision["reason_code"] == "SUPPORT_AUTHORITY_ESCALATION"


def test_candidate_masquerading_as_support_is_rejected():
    sample = _basic_sample()
    candidate = _by_role(sample, "runner_owned_adb_client")
    candidate["observed_class"] = "support_only"
    decision = _sut().issue_temporal_attestation(
        run_id=RUN_ID,
        atomic_sample=sample,
        candidate_identity_key=candidate["identity_key"],
    )
    assert decision == {"valid": False, "reason_code": "CANDIDATE_CLASS_MASQUERADE"}


def test_missing_parent_chain_segment_is_rejected():
    sample = _basic_sample()
    support_key = _by_role(sample, "support_only")["identity_key"]
    sample["records"] = [row for row in sample["records"] if row["identity_key"] != support_key]
    decision = _sut().issue_temporal_attestation(
        run_id=RUN_ID,
        atomic_sample=sample,
        candidate_identity_key=_by_role(sample, "runner_owned_adb_client")["identity_key"],
    )
    assert decision == {"valid": False, "reason_code": "MISSING_PARENT_CHAIN"}


def test_runner_pid_reuse_is_rejected():
    birth = _basic_sample()
    current = copy.deepcopy(birth)
    runner = _by_role(current, "trusted_runner")
    runner["create_time"] += 1.0
    runner["identity_key"] = f'{runner["pid"]}:{runner["create_time"]:.6f}'
    decision = _verify(_attest(birth), current)
    assert decision == {"accepted": False, "reason_code": "RUNNER_ROOT_IDENTITY_MISMATCH"}


def test_terminal_expiry_is_irreversible():
    sample = _basic_sample()
    attestation = _attest(sample)
    expired = _verify(attestation, sample, terminal=True)
    assert expired["accepted"] is False
    assert expired["reason_code"] == "ATTESTATION_EXPIRED"
    again = _verify(attestation, sample)
    assert again["accepted"] is False
    assert again["reason_code"] == "ATTESTATION_EXPIRED"


def test_m9_shaped_twelve_exited_one_current_replay_preserves_authority_boundary():
    base = _basic_sample()
    runner = _by_role(base, "trusted_runner")
    records = [runner]
    candidate_keys = []
    for index in range(13):
        support = _record(
            1000 + index,
            2000.0 + index,
            runner["pid"],
            runner["identity_key"],
            "support_only",
        )
        candidate = _record(
            2000 + index,
            3000.0 + index,
            support["pid"],
            support["identity_key"],
            "runner_owned_adb_client",
        )
        records.extend([support, candidate])
        candidate_keys.append(candidate["identity_key"])
    birth = _seal_sample(records)
    attestations = [
        _sut().issue_temporal_attestation(
            run_id=RUN_ID,
            atomic_sample=birth,
            candidate_identity_key=key,
        )
        for key in candidate_keys
    ]
    current_records = [
        copy.deepcopy(_by_role(birth, "trusted_runner")),
        copy.deepcopy(next(row for row in birth["records"] if row["identity_key"] == candidate_keys[-1])),
    ]
    current = _seal_sample(current_records, sequence=8)
    result = _sut().evaluate_replay(
        run_id=RUN_ID,
        birth_atomic_sample=birth,
        current_atomic_sample=current,
        attestations=attestations,
        controlled_ports=[5038, 5554, 5555, 8554],
    )
    assert result["historical_exited_count"] == 12
    assert result["historical_exited_authority_count"] == 0
    assert result["current_attested_count"] == 1
    assert result["current_attested_birth_chain_complete"] is True
    assert result["support_role_authority_count"] == 0
    assert result["support_cleanup_target_count"] == 0
