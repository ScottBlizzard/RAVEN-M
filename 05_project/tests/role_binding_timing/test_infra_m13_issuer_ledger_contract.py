"""Frozen issuer-ledger and temporal gates for INFRA-M13.

These DEV engineering tests are post-diagnosis and not held-out. The future
runner must refuse to execute them until the canonical-view gate has passed
unchanged under a separately reviewed implementation lock. At freeze time the
implementation is deliberately absent and this file is not executed.
"""

from __future__ import annotations

import copy
import hashlib
import importlib
import json

import pytest


MODULE = "raven_m.role_binding_timing.infra_m13_proof_bound_attestation"
CONTRACT_VERSION = "infra-m13-proof-bound-role-views-v1"
CONTRACT_SHA256 = "52A2914DCB4152B30CDBA50F5F0E8E3CF8EF1C614694E5544ABE7EB253418519"
PORTS = [5037, 5038, 5554, 5555, 8554]
RUN_A = "infra-m13-dev-run-a"
RUN_B = "infra-m13-dev-run-b"
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
    exe = f"C:/infra-m13-temporal/{name}.exe"
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


def _sample(sequence=13):
    runner = _row(110, 1100.0, 1, "runner")
    support = _row(210, 1101.0, 110, "support")
    candidate = _row(310, 1102.0, 210, "client")
    unrelated = _row(410, 1103.0, 1, "unrelated")
    rows = [runner, support, candidate, unrelated]
    raw = {
        "schema_version": "role_binding_timing.infra_m13.raw_process_snapshot.fixture.v1",
        "sample_sequence": sequence,
        "sample_time_utc": f"2026-08-05T02:00:{sequence:02d}Z",
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


def _derive(raw, runner, known):
    return _sut().derive_authorization_views(
        raw_snapshot=raw,
        locked_runner_record=runner,
        locked_known_paths=known,
        controlled_ports=PORTS,
        contract_version=CONTRACT_VERSION,
        contract_sha256=CONTRACT_SHA256,
        implementation_sha256=_sut().implementation_sha256(),
    )


def _verified_sealed(raw, runner, known):
    derived = _derive(raw, runner, known)
    sealed = _sut().seal_authorization_views(
        raw_snapshot=raw,
        derived_views={name: derived[name] for name in VIEW_NAMES},
        candidate_ancestry=derived["candidate_ancestry"],
        locked_runner_record=runner,
        locked_known_paths=known,
        controlled_ports=PORTS,
        contract_version=CONTRACT_VERSION,
        contract_sha256=CONTRACT_SHA256,
        implementation_sha256=_sut().implementation_sha256(),
        implementation_blob_oid=_sut().implementation_blob_oid(),
    )
    return _sut().verify_sealed_authorization_views(
        raw_snapshot=raw,
        supplied_sealed_view=sealed,
        locked_runner_record=runner,
        locked_known_paths=known,
        controlled_ports=PORTS,
        contract_version=CONTRACT_VERSION,
        contract_sha256=CONTRACT_SHA256,
        implementation_sha256=_sut().implementation_sha256(),
        implementation_blob_oid=_sut().implementation_blob_oid(),
    )


def _open(run_id=RUN_A):
    ledger = _sut().create_run_local_issuer_ledger()
    session = _sut().begin_issuer_run(ledger=ledger, run_id=run_id)
    return ledger, session


def _issue(raw=None, runner=None, known=None, candidate=None, ledger=None, session=None):
    base_raw, base_runner, base_known, base_candidate = _sample()
    actual_raw = raw or base_raw
    actual_runner = runner or base_runner
    actual_known = known or base_known
    actual_candidate = candidate or base_candidate
    actual_ledger, actual_session = (ledger, session) if ledger is not None else _open()
    verified = _verified_sealed(actual_raw, actual_runner, actual_known)
    attestation = _sut().issue_temporal_attestation(
        verified_sealed_view=verified,
        candidate_identity_key=actual_candidate,
        ledger=actual_ledger,
        issuer_session=actual_session,
    )
    return attestation, actual_ledger, actual_session


def _verify(attestation, ledger, session, current=None, runner=None, known=None):
    base_raw, base_runner, base_known, _ = _sample()
    return _sut().verify_temporal_attestation(
        attestation=attestation,
        current_raw_snapshot=current or base_raw,
        locked_runner_record=runner or base_runner,
        locked_known_paths=known or base_known,
        controlled_ports=PORTS,
        contract_version=CONTRACT_VERSION,
        contract_sha256=CONTRACT_SHA256,
        implementation_sha256=_sut().implementation_sha256(),
        implementation_blob_oid=_sut().implementation_blob_oid(),
        ledger=ledger,
        issuer_session=session,
    )


def _assert_reject(callable_, code=None):
    with pytest.raises(_sut().M13ContractError) as caught:
        callable_()
    if code is not None:
        assert caught.value.code == code


def _rehash_attestation(attestation):
    payload = copy.deepcopy(attestation)
    payload.pop("attestation_sha256", None)
    attestation["attestation_sha256"] = _canonical_sha(payload)


def _mutate_raw_both(raw, pid, field, value):
    for collection in ("all_processes", "structural_processes"):
        row = next(item for item in raw[collection] if item["pid"] == pid)
        if value is _DELETE:
            row.pop(field, None)
        else:
            row[field] = copy.deepcopy(value)


_DELETE = object()


def test_run_nonce_and_attestation_ids_are_unpredictable_width_and_distinct():
    ledger_a, session_a = _open("run-a")
    ledger_b, session_b = _open("run-b")
    first, _, _ = _issue(ledger=ledger_a, session=session_a)
    second, _, _ = _issue(ledger=ledger_b, session=session_b)
    assert len(bytes.fromhex(session_a["run_nonce"])) >= 16
    assert len(bytes.fromhex(session_b["run_nonce"])) >= 16
    assert session_a["run_nonce"] != session_b["run_nonce"]
    assert len(bytes.fromhex(first["attestation_id"])) >= 16
    assert first["attestation_id"] != second["attestation_id"]


def test_same_atomic_sample_issued_member_is_accepted():
    raw, runner, known, candidate = _sample()
    attestation, ledger, session = _issue(raw, runner, known, candidate)
    decision = _verify(attestation, ledger, session, raw, runner, known)
    assert decision["accepted"] is True
    assert tuple(decision["candidate_identity_key"]) == candidate


def test_lossless_support_projection_retains_proof_fields_without_authority():
    raw, runner, known, candidate = _sample()
    attestation, _, _ = _issue(raw, runner, known, candidate)
    support = attestation["sealed_view"]["views"]["support_only_ancestry_nodes"][0]
    source = next(row for row in raw["structural_processes"] if row["pid"] == 210)
    for field in ("pid", "create_time", "ppid", "exe", "exe_sha256", "command_line"):
        assert support[field] == source[field]
    for field in (
        "source_record_sha256",
        "raw_snapshot_sha256",
        "sample_sequence",
        "sample_time_utc",
    ):
        assert support[field]
    for field in ("role_authority", "adoptable", "kill_target", "cleanup_target"):
        assert support[field] is False


def test_birth_candidate_is_exactly_extracted_from_verified_sealed_view():
    raw, runner, known, candidate = _sample()
    attestation, _, _ = _issue(raw, runner, known, candidate)
    sealed_candidate = next(
        row
        for row in attestation["sealed_view"]["views"]["project_authorization_candidates"]
        if (row["pid"], row["create_time"]) == candidate
    )
    assert attestation["birth_candidate_record"] == sealed_candidate


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("exe", "C:/forged/candidate.exe"),
        ("exe_sha256", "0" * 64),
        ("command_line", ["C:/forged/candidate.exe", "--forged"]),
    ],
)
def test_birth_candidate_field_tamper_and_rehash_is_rejected(field, value):
    raw, runner, known, candidate = _sample()
    attestation, ledger, session = _issue(raw, runner, known, candidate)
    attestation["birth_candidate_record"][field] = value
    _rehash_attestation(attestation)
    _assert_reject(lambda: _verify(attestation, ledger, session, raw, runner, known))


@pytest.mark.parametrize("mutation", ["field", "reorder", "insert", "delete"])
def test_birth_chain_mutation_and_rehash_is_rejected(mutation):
    raw, runner, known, candidate = _sample()
    attestation, ledger, session = _issue(raw, runner, known, candidate)
    chain = attestation["birth_chain"]
    if mutation == "field":
        chain[0]["command_line"] = ["C:/forged.exe"]
    elif mutation == "reorder":
        chain[:] = list(reversed(chain))
    elif mutation == "insert":
        chain.insert(1, copy.deepcopy(chain[0]))
    else:
        chain.pop(1)
    _rehash_attestation(attestation)
    _assert_reject(lambda: _verify(attestation, ledger, session, raw, runner, known))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("exe", "C:/forged/chain-node.exe"),
        ("exe_sha256", "0" * 64),
        ("command_line", ["C:/forged/chain-node.exe"]),
        ("sample_sequence", 999),
        ("sample_time_utc", "2099-01-01T00:00:00Z"),
        ("source_record_sha256", "0" * 64),
    ],
)
def test_birth_chain_exact_node_fields_are_bound_even_after_rehash(field, value):
    raw, runner, known, candidate = _sample()
    attestation, ledger, session = _issue(raw, runner, known, candidate)
    attestation["birth_chain"][1][field] = value
    _rehash_attestation(attestation)
    _assert_reject(lambda: _verify(attestation, ledger, session, raw, runner, known))


def test_cross_frame_parent_chain_stitch_is_rejected_after_rehash():
    raw, runner, known, candidate = _sample()
    attestation, ledger, session = _issue(raw, runner, known, candidate)
    attestation["birth_chain"][1]["sample_sequence"] += 1
    attestation["birth_chain"][1]["sample_time_utc"] = "2026-08-05T02:59:59Z"
    _rehash_attestation(attestation)
    _assert_reject(lambda: _verify(attestation, ledger, session, raw, runner, known))


def test_candidate_ancestry_mutation_inside_attestation_is_rejected():
    raw, runner, known, candidate = _sample()
    attestation, ledger, session = _issue(raw, runner, known, candidate)
    ancestry = attestation["sealed_view"]["candidate_ancestry"][0]
    ancestry["chain"] = list(reversed(ancestry["chain"]))
    _rehash_attestation(attestation)
    _assert_reject(lambda: _verify(attestation, ledger, session, raw, runner, known))


def test_hand_forged_unissued_attestation_is_rejected_despite_valid_public_hash():
    raw, runner, known, candidate = _sample()
    legitimate, ledger, session = _issue(raw, runner, known, candidate)
    forged = copy.deepcopy(legitimate)
    forged["attestation_id"] = "ab" * 16
    _rehash_attestation(forged)
    _assert_reject(
        lambda: _verify(forged, ledger, session, raw, runner, known),
        "ISSUER_LEDGER_ENTRY_MISSING",
    )


def test_copy_modify_and_rehash_cannot_replace_issuer_membership_digest():
    raw, runner, known, candidate = _sample()
    legitimate, ledger, session = _issue(raw, runner, known, candidate)
    copied = copy.deepcopy(legitimate)
    copied["birth_candidate_record"]["name"] = "modified-copy"
    _rehash_attestation(copied)
    _assert_reject(
        lambda: _verify(copied, ledger, session, raw, runner, known),
        "ISSUER_LEDGER_DIGEST_MISMATCH",
    )


def test_unissued_object_cannot_verify_directly():
    raw, runner, known, candidate = _sample()
    issued, ledger, session = _issue(raw, runner, known, candidate)
    unissued = copy.deepcopy(issued)
    unissued["attestation_id"] = "cd" * 16
    _rehash_attestation(unissued)
    _assert_reject(lambda: _verify(unissued, ledger, session, raw, runner, known))


def test_current_process_ledger_entry_is_mandatory():
    raw, runner, known, candidate = _sample()
    attestation, _, original_session = _issue(raw, runner, known, candidate)
    empty_ledger = _sut().create_run_local_issuer_ledger()
    _assert_reject(
        lambda: _verify(attestation, empty_ledger, original_session, raw, runner, known),
        "ISSUER_LEDGER_ENTRY_MISSING",
    )


@pytest.mark.parametrize(
    ("field", "replacement", "code"),
    [
        ("run_nonce", "01" * 16, "RUN_NONCE_MISMATCH"),
        ("epoch", 999, "RUN_EPOCH_MISMATCH"),
        ("attestation_id", "02" * 16, "ISSUER_LEDGER_ENTRY_MISSING"),
    ],
)
def test_nonce_epoch_or_attestation_id_mismatch_is_rejected(field, replacement, code):
    raw, runner, known, candidate = _sample()
    attestation, ledger, session = _issue(raw, runner, known, candidate)
    attestation[field] = replacement
    _rehash_attestation(attestation)
    _assert_reject(lambda: _verify(attestation, ledger, session, raw, runner, known), code)


def test_simulated_new_verifier_process_empty_ledger_rejects_old_serialized_proof():
    raw, runner, known, candidate = _sample()
    serialized, _, old_session = _issue(raw, runner, known, candidate)
    restored = json.loads(json.dumps(serialized))
    new_process_ledger = _sut().create_run_local_issuer_ledger()
    _assert_reject(
        lambda: _verify(restored, new_process_ledger, old_session, raw, runner, known),
        "ISSUER_LEDGER_ENTRY_MISSING",
    )


def test_cross_run_replay_is_rejected():
    raw, runner, known, candidate = _sample()
    attestation, ledger_a, _ = _issue(raw, runner, known, candidate)
    ledger_b, session_b = _open(RUN_B)
    _assert_reject(
        lambda: _verify(attestation, ledger_b, session_b, raw, runner, known),
        "CROSS_RUN_REPLAY",
    )


@pytest.mark.parametrize(("pid", "code"), [(210, "PARENT_PID_REUSE"), (310, "CHILD_PID_REUSE")])
def test_parent_or_child_pid_reuse_is_rejected(pid, code):
    birth, runner, known, candidate = _sample()
    attestation, ledger, session = _issue(birth, runner, known, candidate)
    current = copy.deepcopy(birth)
    _mutate_raw_both(current, pid, "create_time", 9999.0)
    _assert_reject(lambda: _verify(attestation, ledger, session, current, runner, known), code)


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("create_time", _DELETE, "MISSING_CREATE_TIME"),
        ("exe_sha256", _DELETE, "MISSING_EXE_SHA256"),
        ("command_line", _DELETE, "MISSING_COMMAND_LINE"),
    ],
)
def test_missing_critical_support_fields_fail_before_issue(field, value, code):
    raw, runner, known, candidate = _sample()
    _mutate_raw_both(raw, 210, field, value)
    ledger, session = _open()
    _assert_reject(lambda: _issue(raw, runner, known, candidate, ledger, session), code)


def test_access_denied_critical_support_fails_before_issue():
    raw, runner, known, candidate = _sample()
    _mutate_raw_both(raw, 210, "accessibility_status", "access_denied")
    _mutate_raw_both(raw, 210, "access_error", "AccessDenied")
    ledger, session = _open()
    _assert_reject(
        lambda: _issue(raw, runner, known, candidate, ledger, session),
        "CRITICAL_FIELD_ACCESS_DENIED",
    )


def test_current_evidence_conflict_has_priority():
    birth, runner, known, candidate = _sample()
    attestation, ledger, session = _issue(birth, runner, known, candidate)
    current = copy.deepcopy(birth)
    _mutate_raw_both(current, 310, "command_line", ["C:/different.exe"])
    _assert_reject(
        lambda: _verify(attestation, ledger, session, current, runner, known),
        "CURRENT_HISTORY_CONFLICT",
    )


def test_support_controlled_port_ownership_fails_before_issue():
    raw, runner, known, candidate = _sample()
    raw["all_tcp_listener_ports_by_pid"] = {"210": [5038]}
    ledger, session = _open()
    _assert_reject(
        lambda: _issue(raw, runner, known, candidate, ledger, session),
        "SUPPORT_CONTROLLED_PORT_CONFLICT",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_record_sha256", "0" * 64),
        ("raw_snapshot_sha256", "0" * 64),
        ("partition_sha256", "0" * 64),
    ],
)
def test_stored_proof_hash_tamper_is_rejected_even_after_attestation_rehash(field, value):
    raw, runner, known, candidate = _sample()
    attestation, ledger, session = _issue(raw, runner, known, candidate)
    support = attestation["sealed_view"]["views"]["support_only_ancestry_nodes"][0]
    support[field] = value
    _rehash_attestation(attestation)
    _assert_reject(lambda: _verify(attestation, ledger, session, raw, runner, known))


@pytest.mark.parametrize("field", ["role_authority", "adoptable", "kill_target", "cleanup_target"])
def test_support_authority_or_lifecycle_tamper_is_rejected_after_rehash(field):
    raw, runner, known, candidate = _sample()
    attestation, ledger, session = _issue(raw, runner, known, candidate)
    support = attestation["sealed_view"]["views"]["support_only_ancestry_nodes"][0]
    support[field] = True
    _rehash_attestation(attestation)
    _assert_reject(lambda: _verify(attestation, ledger, session, raw, runner, known))


def test_support_identity_cannot_be_issued_as_candidate():
    raw, runner, known, _ = _sample()
    ledger, session = _open()
    _assert_reject(
        lambda: _issue(raw, runner, known, (210, 1101.0), ledger, session),
        "IDENTITY_NOT_DERIVED_CANDIDATE",
    )


def test_missing_parent_chain_fails_before_issue():
    raw, runner, known, candidate = _sample()
    for collection in ("all_processes", "structural_processes"):
        raw[collection] = [row for row in raw[collection] if row["pid"] != 210]
    ledger, session = _open()
    _assert_reject(
        lambda: _issue(raw, runner, known, candidate, ledger, session),
        "MISSING_PARENT_CHAIN",
    )


def test_runner_identity_reuse_is_rejected_during_current_verification():
    birth, runner, known, candidate = _sample()
    attestation, ledger, session = _issue(birth, runner, known, candidate)
    current = copy.deepcopy(birth)
    _mutate_raw_both(current, 110, "create_time", 7777.0)
    _assert_reject(
        lambda: _verify(attestation, ledger, session, current, runner, known),
        "RUNNER_ROOT_IDENTITY_MISMATCH",
    )


def test_terminal_atomically_revokes_original_and_replay_and_tombstones_run():
    raw, runner, known, candidate = _sample()
    attestation, ledger, session = _issue(raw, runner, known, candidate)
    replay = copy.deepcopy(attestation)
    _sut().terminate_issuer_run(ledger=ledger, issuer_session=session)
    _assert_reject(
        lambda: _verify(attestation, ledger, session, raw, runner, known),
        "RUN_TOMBSTONED",
    )
    _assert_reject(
        lambda: _verify(replay, ledger, session, raw, runner, known),
        "RUN_TOMBSTONED",
    )
    _assert_reject(
        lambda: _sut().begin_issuer_run(ledger=ledger, run_id=RUN_A),
        "RUN_TOMBSTONED",
    )


def test_twelve_exited_one_current_never_grants_exited_current_authority():
    runner = _row(110, 1100.0, 1, "runner")
    rows = [runner]
    known = []
    identities = []
    for index in range(13):
        support = _row(1000 + index, 2000.0 + index, 110, f"support_{index}")
        candidate = _row(2000 + index, 3000.0 + index, support["pid"], f"client_{index}")
        rows.extend([support, candidate])
        known.append(
            {
                "logical_role": f"client_{index}",
                "normalized_path": candidate["exe"],
                "exe_sha256": candidate["exe_sha256"],
            }
        )
        identities.append((candidate["pid"], candidate["create_time"]))
    birth = {
        "schema_version": "role_binding_timing.infra_m13.raw_process_snapshot.fixture.v1",
        "sample_sequence": 20,
        "sample_time_utc": "2026-08-05T02:00:20Z",
        "observation_universe_complete": True,
        "observation_universe_capture_errors": [],
        "all_processes": copy.deepcopy(rows),
        "structural_processes": copy.deepcopy(rows),
        "all_tcp_listener_ports_by_pid": {},
        "listener_evidence_complete": True,
    }
    ledger, session = _open()
    attestations = [
        _issue(birth, runner, known, identity, ledger, session)[0] for identity in identities
    ]
    live_candidate = next(row for row in rows if row["pid"] == identities[-1][0])
    current_rows = [runner, live_candidate]
    current = {
        "schema_version": birth["schema_version"],
        "sample_sequence": 21,
        "sample_time_utc": "2026-08-05T02:00:21Z",
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
        contract_version=CONTRACT_VERSION,
        contract_sha256=CONTRACT_SHA256,
        implementation_sha256=_sut().implementation_sha256(),
        implementation_blob_oid=_sut().implementation_blob_oid(),
        ledger=ledger,
        issuer_session=session,
    )
    assert result["historical_exited_count"] == 12
    assert result["historical_exited_authority_count"] == 0
    assert result["current_attested_count"] == 1
    assert result["support_role_authority_count"] == 0
    assert result["support_cleanup_target_count"] == 0
