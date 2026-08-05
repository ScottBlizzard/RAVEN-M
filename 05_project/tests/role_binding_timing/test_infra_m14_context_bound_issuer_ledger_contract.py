"""Frozen context-bound issuer-ledger gates for INFRA-M14.

This is a post-diagnosis DEV engineering contract.  The future
``trusted_initializer_factory`` fixture and M14 implementation are absent at
freeze time, so every test in this file is deliberately NOT RUN.
"""

from __future__ import annotations

import copy
import hashlib
import importlib
import json
import pickle

import pytest


MODULE = "raven_m.role_binding_timing.infra_m14_authority_context_attestation"
CONFIG_SHA256 = "8421E4985DEF834F84D5B22FFC0B2D22FF2A063473861213A64C4990C694C661"
INPUT_LOCK_SHA256 = "11BA21E3DAF4D8ED4BD0D2633E5D2EE9FD9583FB7060169FC3950AE777ADF4A6"
EXACT_PORTS = [5037, 5038, 5554, 5555, 8554]
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
    exe = f"C:/infra-m14-ledger-fixture/{name}.exe"
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


def _snapshot(*, candidate_present=True, sequence=1, candidate_ctime=30.0):
    runner = _row(101, 10.0, 1, "runner")
    support = _row(201, 20.0, 101, "support")
    candidate = _row(301, candidate_ctime, 201, "client")
    unrelated = _row(401, 40.0, 1, "unrelated")
    rows = [runner, support, unrelated]
    if candidate_present:
        rows.insert(2, candidate)
    raw = {
        "schema_version": "role_binding_timing.infra_m14.raw_process_snapshot.fixture.v1",
        "sample_sequence": sequence,
        "sample_time_utc": f"2026-08-05T04:14:{sequence:02d}Z",
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
    return raw, runner, support, candidate, unrelated, known


def _context(
    trusted_initializer_factory,
    *,
    run_id="infra-m14-ledger-run",
    session_id="infra-m14-ledger-session",
):
    _, runner, _, _, _, known = _snapshot()
    initializer = trusted_initializer_factory(
        runner_record=copy.deepcopy(runner),
        known_paths=copy.deepcopy(known),
        controlled_ports=copy.deepcopy(EXACT_PORTS),
        config_sha256=CONFIG_SHA256,
        input_lock_sha256=INPUT_LOCK_SHA256,
        run_identity=run_id,
        session_identity=session_id,
        bootstrap_sample_identity=f"{run_id}:{session_id}:bootstrap",
        expected_runner_record_sha256=_canonical_sha(runner),
    )
    return _sut().create_locked_authority_context(initializer)


def _identity(row):
    return {"pid": row["pid"], "create_time": row["create_time"]}


def _sealed(raw, context):
    derived = _sut().derive_authorization_views(
        raw_snapshot=raw,
        authority_context=context,
    )
    return _sut().seal_authorization_views(
        raw_snapshot=raw,
        derived_views={name: derived[name] for name in VIEW_NAMES},
        candidate_ancestry=derived["candidate_ancestry"],
        authority_context=context,
        implementation_sha256=_sut().implementation_sha256(),
        implementation_blob_oid=_sut().implementation_blob_oid(),
    )


def _verified(raw, context):
    sealed = _sealed(raw, context)
    return _sut().verify_sealed_authorization_views(
        raw_snapshot=raw,
        supplied_sealed_view=sealed,
        authority_context=context,
        implementation_sha256=_sut().implementation_sha256(),
        implementation_blob_oid=_sut().implementation_blob_oid(),
    )


def _session(context):
    ledger = _sut().create_issuer_ledger()
    session = _sut().begin_issuer_run(
        ledger=ledger,
        authority_context=context,
    )
    return ledger, session


def _issue(raw, context, ledger, session):
    candidate = _snapshot()[3]
    verified = _verified(raw, context)
    attestation = _sut().issue_temporal_attestation(
        verified_seal=verified,
        candidate_identity=_identity(candidate),
        ledger=ledger,
        issuer_session=session,
        authority_context=context,
    )
    return verified, attestation


def _verify_attestation(attestation, current_raw, context, ledger, session):
    return _sut().verify_temporal_attestation(
        attestation=attestation,
        current_raw=current_raw,
        ledger=ledger,
        issuer_session=session,
        authority_context=context,
    )


def _assert_reject(callable_, code):
    with pytest.raises(_sut().M14ContractError) as caught:
        callable_()
    assert caught.value.code == code
    return caught.value


def _rehash_attestation(attestation):
    payload = copy.deepcopy(attestation)
    payload.pop("attestation_sha256", None)
    attestation["attestation_sha256"] = _canonical_sha(payload)


def test_issuer_ledger_is_process_local_and_nonserializable():
    ledger = _sut().create_issuer_ledger()
    with pytest.raises(TypeError):
        pickle.dumps(ledger)
    with pytest.raises(TypeError):
        copy.deepcopy(ledger)


def test_same_ledger_run_cannot_switch_context(trusted_initializer_factory):
    context_a = _context(trusted_initializer_factory, session_id="a")
    context_b = _context(trusted_initializer_factory, session_id="b")
    ledger, _ = _session(context_a)
    _assert_reject(
        lambda: _sut().begin_issuer_run(
            ledger=ledger,
            authority_context=context_b,
        ),
        "LEDGER_AUTHORITY_CONTEXT_MISMATCH",
    )


def test_visibly_equal_context_cannot_join_existing_session(trusted_initializer_factory):
    context_a = _context(trusted_initializer_factory, session_id="same")
    context_b = _context(trusted_initializer_factory, session_id="same")
    ledger, _ = _session(context_a)
    assert context_a is not context_b
    _assert_reject(
        lambda: _sut().begin_issuer_run(
            ledger=ledger,
            authority_context=context_b,
        ),
        "LEDGER_AUTHORITY_CONTEXT_MISMATCH",
    )


def test_verified_seal_from_other_context_cannot_issue(trusted_initializer_factory):
    raw, _, _, candidate, _, _ = _snapshot()
    context_a = _context(trusted_initializer_factory, session_id="a")
    context_b = _context(trusted_initializer_factory, session_id="b")
    verified_a = _verified(raw, context_a)
    ledger_b, session_b = _session(context_b)
    _assert_reject(
        lambda: _sut().issue_temporal_attestation(
            verified_seal=verified_a,
            candidate_identity=_identity(candidate),
            ledger=ledger_b,
            issuer_session=session_b,
            authority_context=context_b,
        ),
        "VERIFIED_SEAL_CONTEXT_MISMATCH",
    )


def test_attestation_from_other_context_cannot_verify(trusted_initializer_factory):
    raw, _, _, _, _, _ = _snapshot()
    context_a = _context(trusted_initializer_factory, session_id="a")
    context_b = _context(trusted_initializer_factory, session_id="b")
    ledger_a, session_a = _session(context_a)
    _, attestation = _issue(raw, context_a, ledger_a, session_a)
    ledger_b, session_b = _session(context_b)
    _assert_reject(
        lambda: _verify_attestation(
            attestation, raw, context_b, ledger_b, session_b
        ),
        "ATTESTATION_CONTEXT_MISMATCH",
    )


def test_hand_constructed_attestation_is_not_ledger_member(trusted_initializer_factory):
    raw, _, _, _, _, _ = _snapshot()
    context = _context(trusted_initializer_factory)
    ledger, session = _session(context)
    forged = {
        "run_id": "infra-m14-ledger-run",
        "run_nonce": "0" * 32,
        "attestation_id": "1" * 32,
        "epoch": 1,
        "attestation_sha256": "2" * 64,
    }
    _assert_reject(
        lambda: _verify_attestation(forged, raw, context, ledger, session),
        "ATTESTATION_NOT_ISSUED",
    )


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("run_nonce", "0" * 32, "RUN_NONCE_MISMATCH"),
        ("attestation_id", "1" * 32, "ATTESTATION_ID_MISMATCH"),
        ("epoch", 999, "ISSUER_EPOCH_MISMATCH"),
    ],
)
def test_ledger_nonce_id_and_epoch_are_exact(
    trusted_initializer_factory, field, value, code
):
    raw, _, _, _, _, _ = _snapshot()
    context = _context(trusted_initializer_factory)
    ledger, session = _session(context)
    _, attestation = _issue(raw, context, ledger, session)
    tampered = copy.deepcopy(attestation)
    tampered[field] = value
    _rehash_attestation(tampered)
    _assert_reject(
        lambda: _verify_attestation(tampered, raw, context, ledger, session),
        code,
    )


def test_copy_modify_and_public_rehash_cannot_replace_ledger_digest(
    trusted_initializer_factory,
):
    raw, _, _, _, _, _ = _snapshot()
    context = _context(trusted_initializer_factory)
    ledger, session = _session(context)
    _, attestation = _issue(raw, context, ledger, session)
    tampered = copy.deepcopy(attestation)
    tampered["observability"]["birth_candidate_record"]["command_line"] = [
        "C:/tampered.exe"
    ]
    _rehash_attestation(tampered)
    _assert_reject(
        lambda: _verify_attestation(tampered, raw, context, ledger, session),
        "LEDGER_DIGEST_MISMATCH",
    )


@pytest.mark.parametrize("field", ["exe", "exe_sha256", "command_line"])
def test_birth_candidate_observability_copy_must_match_verified_seal(
    trusted_initializer_factory, field
):
    raw, _, _, _, _, _ = _snapshot()
    context = _context(trusted_initializer_factory)
    ledger, session = _session(context)
    _, attestation = _issue(raw, context, ledger, session)
    tampered = copy.deepcopy(attestation)
    tampered["observability"]["birth_candidate_record"][field] = "tampered"
    _rehash_attestation(tampered)
    _assert_reject(
        lambda: _verify_attestation(tampered, raw, context, ledger, session),
        "LEDGER_DIGEST_MISMATCH",
    )


@pytest.mark.parametrize("operation", ["mutate", "reorder", "insert", "delete"])
def test_birth_chain_is_deterministically_rebuilt_and_exact(
    trusted_initializer_factory, operation
):
    raw, _, _, _, _, _ = _snapshot()
    context = _context(trusted_initializer_factory)
    ledger, session = _session(context)
    _, attestation = _issue(raw, context, ledger, session)
    tampered = copy.deepcopy(attestation)
    chain = tampered["observability"]["birth_chain"]
    if operation == "mutate":
        chain[0]["command_line"] = ["C:/tampered.exe"]
    elif operation == "reorder":
        chain[:] = list(reversed(chain))
    elif operation == "insert":
        chain.insert(0, copy.deepcopy(chain[0]))
    else:
        chain.pop()
    _rehash_attestation(tampered)
    _assert_reject(
        lambda: _verify_attestation(tampered, raw, context, ledger, session),
        "LEDGER_DIGEST_MISMATCH",
    )


def test_candidate_ancestry_cannot_be_substituted_before_issue(
    trusted_initializer_factory,
):
    raw, _, _, candidate, _, _ = _snapshot()
    context = _context(trusted_initializer_factory)
    verified = _verified(raw, context)
    forged = copy.deepcopy(verified)
    forged["candidate_ancestry"][0]["chain"].reverse()
    ledger, session = _session(context)
    _assert_reject(
        lambda: _sut().issue_temporal_attestation(
            verified_seal=forged,
            candidate_identity=_identity(candidate),
            ledger=ledger,
            issuer_session=session,
            authority_context=context,
        ),
        "VERIFIED_SEAL_CAPABILITY_REQUIRED",
    )


def test_support_identity_cannot_receive_attestation(trusted_initializer_factory):
    raw, _, support, _, _, _ = _snapshot()
    context = _context(trusted_initializer_factory)
    verified = _verified(raw, context)
    ledger, session = _session(context)
    _assert_reject(
        lambda: _sut().issue_temporal_attestation(
            verified_seal=verified,
            candidate_identity=_identity(support),
            ledger=ledger,
            issuer_session=session,
            authority_context=context,
        ),
        "CANDIDATE_NOT_AUTHORIZED",
    )


def test_current_exact_candidate_has_current_authority(trusted_initializer_factory):
    raw, _, _, _, _, _ = _snapshot()
    context = _context(trusted_initializer_factory)
    ledger, session = _session(context)
    _, attestation = _issue(raw, context, ledger, session)
    verdict = _verify_attestation(attestation, raw, context, ledger, session)
    assert verdict["classification"] == "current_authority"
    assert verdict["current_authority"] is True


def test_exited_candidate_is_historical_only(trusted_initializer_factory):
    birth, _, _, _, _, _ = _snapshot(sequence=1)
    current, _, _, _, _, _ = _snapshot(candidate_present=False, sequence=2)
    context = _context(trusted_initializer_factory)
    ledger, session = _session(context)
    _, attestation = _issue(birth, context, ledger, session)
    verdict = _verify_attestation(attestation, current, context, ledger, session)
    assert verdict["classification"] == "historical_only"
    assert verdict["current_authority"] is False


@pytest.mark.parametrize("episode", range(12))
def test_twelve_exited_candidate_replay_cases_remain_historical_only(
    trusted_initializer_factory, episode
):
    birth, _, _, _, _, _ = _snapshot(sequence=episode + 1)
    current, _, _, _, _, _ = _snapshot(
        candidate_present=False,
        sequence=episode + 101,
    )
    context = _context(
        trusted_initializer_factory,
        run_id=f"infra-m14-exited-{episode}",
        session_id=f"session-{episode}",
    )
    ledger, session = _session(context)
    _, attestation = _issue(birth, context, ledger, session)
    verdict = _verify_attestation(attestation, current, context, ledger, session)
    assert verdict == {
        "classification": "historical_only",
        "current_authority": False,
        "candidate_identity": _identity(_snapshot()[3]),
    }


def test_one_current_candidate_replay_requires_exact_identity_hash_and_command(
    trusted_initializer_factory,
):
    birth, _, _, candidate, _, _ = _snapshot(sequence=1)
    context = _context(trusted_initializer_factory)
    ledger, session = _session(context)
    _, attestation = _issue(birth, context, ledger, session)
    for field, value in (
        ("create_time", candidate["create_time"] + 1.0),
        ("exe_sha256", "0" * 64),
        ("command_line", ["C:/tampered.exe"]),
    ):
        current, _, _, _, _, _ = _snapshot(sequence=2)
        for collection in ("all_processes", "structural_processes"):
            row = next(item for item in current[collection] if item["pid"] == candidate["pid"])
            row[field] = copy.deepcopy(value)
        _assert_reject(
            lambda current=current: _verify_attestation(
                attestation, current, context, ledger, session
            ),
            "CURRENT_EVIDENCE_CONFLICT",
        )


@pytest.mark.parametrize("which", ["candidate", "parent"])
def test_current_pid_reuse_for_candidate_or_parent_fails_closed(
    trusted_initializer_factory, which
):
    birth, _, support, candidate, _, _ = _snapshot(sequence=1)
    current = copy.deepcopy(birth)
    target = candidate if which == "candidate" else support
    for collection in ("all_processes", "structural_processes"):
        row = next(item for item in current[collection] if item["pid"] == target["pid"])
        row["create_time"] += 1000.0
    context = _context(trusted_initializer_factory)
    ledger, session = _session(context)
    _, attestation = _issue(birth, context, ledger, session)
    _assert_reject(
        lambda: _verify_attestation(attestation, current, context, ledger, session),
        "CURRENT_EVIDENCE_CONFLICT",
    )


def test_empty_new_ledger_rejects_old_process_object(trusted_initializer_factory):
    raw, _, _, _, _, _ = _snapshot()
    context = _context(trusted_initializer_factory)
    old_ledger, old_session = _session(context)
    _, attestation = _issue(raw, context, old_ledger, old_session)
    new_ledger, new_session = _session(context)
    _assert_reject(
        lambda: _verify_attestation(
            attestation, raw, context, new_ledger, new_session
        ),
        "ATTESTATION_NOT_ISSUED",
    )


def test_terminal_atomically_tombstones_and_revokes_all_entries(
    trusted_initializer_factory,
):
    raw, _, _, _, _, _ = _snapshot()
    context = _context(trusted_initializer_factory)
    ledger, session = _session(context)
    _, attestation = _issue(raw, context, ledger, session)
    terminal = _sut().terminate_issuer_run(
        ledger=ledger,
        issuer_session=session,
        authority_context=context,
    )
    assert terminal["tombstoned"] is True
    assert terminal["revoked_entry_count"] == 1
    _assert_reject(
        lambda: _verify_attestation(attestation, raw, context, ledger, session),
        "ISSUER_RUN_TERMINATED",
    )
    _assert_reject(
        lambda: _sut().begin_issuer_run(
            ledger=ledger,
            authority_context=context,
        ),
        "ISSUER_RUN_TOMBSTONED",
    )


def test_terminal_cannot_be_called_with_another_context(trusted_initializer_factory):
    context_a = _context(trusted_initializer_factory, session_id="a")
    context_b = _context(trusted_initializer_factory, session_id="b")
    ledger, session = _session(context_a)
    _assert_reject(
        lambda: _sut().terminate_issuer_run(
            ledger=ledger,
            issuer_session=session,
            authority_context=context_b,
        ),
        "LEDGER_AUTHORITY_CONTEXT_MISMATCH",
    )
