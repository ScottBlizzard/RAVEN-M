"""Frozen authority-context and canonical-view gates for INFRA-M14.

The future ``trusted_initializer_factory`` fixture is a separately locked DEV
harness capability, not an M14 runtime API. The implementation and fixture are
absent at freeze time; this file is NOT RUN.
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
RUN_ID = "infra-m14-dev-run"
SESSION_ID = "infra-m14-dev-session"
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
    exe = f"C:/infra-m14-fixture/{name}.exe"
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
    runner = _row(114, 1400.0, 1, "runner")
    support = _row(214, 1401.0, 114, "support")
    candidate = _row(314, 1402.0, 214, "client")
    unrelated = _row(414, 1403.0, 1, "unrelated")
    rows = [runner, support, candidate, unrelated]
    raw = {
        "schema_version": "role_binding_timing.infra_m14.raw_process_snapshot.fixture.v1",
        "sample_sequence": 14,
        "sample_time_utc": "2026-08-05T03:14:00Z",
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


def _initializer(
    trusted_initializer_factory,
    *,
    runner=None,
    known=None,
    ports=None,
    config_sha=CONFIG_SHA256,
    lock_sha=INPUT_LOCK_SHA256,
    run_id=RUN_ID,
    session_id=SESSION_ID,
    expected_runner_sha=None,
):
    _, original_runner, _, _, _, original_known = _fixture()
    return trusted_initializer_factory(
        runner_record=copy.deepcopy(runner or original_runner),
        known_paths=copy.deepcopy(known or original_known),
        controlled_ports=copy.deepcopy(EXACT_PORTS if ports is None else ports),
        config_sha256=config_sha,
        input_lock_sha256=lock_sha,
        run_identity=run_id,
        session_identity=session_id,
        bootstrap_sample_identity="infra-m14-frozen-dev-bootstrap-001",
        expected_runner_record_sha256=expected_runner_sha or _canonical_sha(original_runner),
    )


def _context(trusted_initializer_factory, **overrides):
    return _sut().create_locked_authority_context(
        _initializer(trusted_initializer_factory, **overrides)
    )


def _derive(raw, context):
    return _sut().derive_authorization_views(raw_snapshot=raw, authority_context=context)


def _seal(raw, context):
    derived = _derive(raw, context)
    return _sut().seal_authorization_views(
        raw_snapshot=raw,
        derived_views={name: derived[name] for name in VIEW_NAMES},
        candidate_ancestry=derived["candidate_ancestry"],
        authority_context=context,
        implementation_sha256=_sut().implementation_sha256(),
        implementation_blob_oid=_sut().implementation_blob_oid(),
    )


def _verify(raw, sealed, context):
    return _sut().verify_sealed_authorization_views(
        raw_snapshot=raw,
        supplied_sealed_view=sealed,
        authority_context=context,
        implementation_sha256=_sut().implementation_sha256(),
        implementation_blob_oid=_sut().implementation_blob_oid(),
    )


def _assert_reject(callable_, code):
    with pytest.raises(_sut().M14ContractError) as caught:
        callable_()
    assert caught.value.code == code
    return caught.value


def _mutate_both(raw, pid, field, value):
    for collection in ("all_processes", "structural_processes"):
        row = next(item for item in raw[collection] if item["pid"] == pid)
        row[field] = copy.deepcopy(value)


def _rewrite_public_hashes(sealed):
    sealed["partition_hashes"] = {
        name: _canonical_sha(sealed["views"][name]) for name in VIEW_NAMES
    }
    sealed["complete_view_sha256"] = _canonical_sha(
        {
            "bindings": sealed["bindings"],
            "views": sealed["views"],
            "candidate_ancestry": sealed["candidate_ancestry"],
            "partition_hashes": sealed["partition_hashes"],
        }
    )
    payload = copy.deepcopy(sealed)
    payload.pop("seal_sha256", None)
    sealed["seal_sha256"] = _canonical_sha(payload)


def test_original_runner_initializer_creates_one_opaque_context(trusted_initializer_factory):
    initializer = _initializer(trusted_initializer_factory)
    context = _sut().create_locked_authority_context(initializer)
    assert type(context).__name__ == "LockedAuthorityContext"
    assert not isinstance(context, dict)
    _assert_reject(
        lambda: _sut().create_locked_authority_context(initializer),
        "INITIALIZER_ALREADY_CONSUMED",
    )


def test_ordinary_dictionary_cannot_forge_context():
    forged = {
        "runner_record": _fixture()[1],
        "known_paths": _fixture()[-1],
        "controlled_ports": EXACT_PORTS,
        "config_sha256": CONFIG_SHA256,
        "input_lock_sha256": INPUT_LOCK_SHA256,
    }
    _assert_reject(
        lambda: _sut().create_locked_authority_context(forged),
        "TRUSTED_INITIALIZER_CAPABILITY_REQUIRED",
    )


@pytest.mark.parametrize("operation", [copy.copy, copy.deepcopy, pickle.dumps])
def test_context_cannot_be_copied_or_serialized(trusted_initializer_factory, operation):
    context = _context(trusted_initializer_factory)
    with pytest.raises(TypeError):
        operation(context)


@pytest.mark.parametrize("operation", [copy.copy, copy.deepcopy, pickle.dumps])
def test_initializer_cannot_be_copied_or_serialized(trusted_initializer_factory, operation):
    initializer = _initializer(trusted_initializer_factory)
    with pytest.raises(TypeError):
        operation(initializer)


@pytest.mark.parametrize(
    "ports",
    [
        [],
        [5038, 5554, 5555, 8554],
        [5037, 5038, 5554, 5555, 8554, 9999],
        [5037, 5038, 5554, 5555, 8554, 8554],
        [8554, 5555, 5554, 5038, 5037],
        [5037, "5038", 5554, 5555, 8554],
    ],
)
def test_controlled_ports_require_exact_ordered_set(trusted_initializer_factory, ports):
    initializer = _initializer(trusted_initializer_factory, ports=ports)
    _assert_reject(
        lambda: _sut().create_locked_authority_context(initializer),
        "CONTROLLED_PORT_LOCK_MISMATCH",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("create_time", 9999.0),
        ("exe", "C:/substituted/runner.exe"),
        ("exe_sha256", "0" * 64),
        ("command_line", ["C:/substituted/runner.exe"]),
    ],
)
def test_raw_runner_identity_path_hash_or_command_substitution_fails(
    trusted_initializer_factory, field, value
):
    raw, runner, _, _, _, _ = _fixture()
    context = _context(trusted_initializer_factory)
    _mutate_both(raw, runner["pid"], field, value)
    _assert_reject(lambda: _derive(raw, context), "CONTEXT_RUNNER_MISMATCH")


@pytest.mark.parametrize("replacement_index", [2, 4])
def test_unrelated_or_support_record_cannot_be_bootstrap_runner(
    trusted_initializer_factory, replacement_index
):
    fixture = _fixture()
    original_runner = fixture[1]
    substituted = fixture[replacement_index]
    initializer = _initializer(
        trusted_initializer_factory,
        runner=substituted,
        expected_runner_sha=_canonical_sha(original_runner),
    )
    _assert_reject(
        lambda: _sut().create_locked_authority_context(initializer),
        "BOOTSTRAP_RUNNER_MISMATCH",
    )


@pytest.mark.parametrize(
    ("config_sha", "lock_sha", "code"),
    [
        ("0" * 64, INPUT_LOCK_SHA256, "CONFIG_LOCK_MISMATCH"),
        (CONFIG_SHA256, "0" * 64, "INPUT_LOCK_MISMATCH"),
    ],
)
def test_context_rejects_config_or_input_lock_substitution(
    trusted_initializer_factory, config_sha, lock_sha, code
):
    initializer = _initializer(
        trusted_initializer_factory, config_sha=config_sha, lock_sha=lock_sha
    )
    _assert_reject(lambda: _sut().create_locked_authority_context(initializer), code)


def test_unknown_listener_owner_pid_fails_closed(trusted_initializer_factory):
    raw, _, _, _, _, _ = _fixture()
    raw["all_tcp_listener_ports_by_pid"] = {"99999": [5038]}
    context = _context(trusted_initializer_factory)
    _assert_reject(lambda: _derive(raw, context), "UNKNOWN_LISTENER_OWNER")


def test_listener_owner_pid_reuse_or_ambiguity_fails_closed(trusted_initializer_factory):
    raw, _, _, candidate, _, _ = _fixture()
    duplicate = copy.deepcopy(candidate)
    duplicate["create_time"] += 100.0
    raw["all_processes"].append(copy.deepcopy(duplicate))
    raw["structural_processes"].append(copy.deepcopy(duplicate))
    raw["all_tcp_listener_ports_by_pid"] = {str(candidate["pid"]): [5038]}
    context = _context(trusted_initializer_factory)
    _assert_reject(lambda: _derive(raw, context), "LISTENER_OWNER_IDENTITY_AMBIGUOUS")


@pytest.mark.parametrize("case", ["missing_parent", "wrong_root", "cycle", "depth_overflow"])
def test_candidate_like_row_requires_complete_chain_to_exact_context_runner(
    trusted_initializer_factory, case
):
    raw, runner, support, candidate, unrelated, _ = _fixture()
    if case == "missing_parent":
        _mutate_both(raw, candidate["pid"], "ppid", 99999)
    elif case == "wrong_root":
        _mutate_both(raw, candidate["pid"], "ppid", unrelated["pid"])
    elif case == "cycle":
        _mutate_both(raw, support["pid"], "ppid", candidate["pid"])
    else:
        previous = candidate["pid"]
        added = []
        for index in range(17):
            node = _row(1000 + index, 2000.0 + index, runner["pid"], f"deep_{index}")
            if added:
                added[-1]["ppid"] = node["pid"]
            else:
                _mutate_both(raw, previous, "ppid", node["pid"])
            added.append(node)
        for node in added:
            raw["all_processes"].append(copy.deepcopy(node))
            raw["structural_processes"].append(copy.deepcopy(node))
    context = _context(trusted_initializer_factory)
    error = _assert_reject(
        lambda: _derive(raw, context),
        "INCOMPLETE_CANDIDATE_ANCESTRY",
    )
    assert error.detail["partial_views_emitted"] is False
    assert error.detail["support_projection_count"] == 0


def test_complete_chain_is_required_before_candidate_or_support_materialization(
    trusted_initializer_factory,
):
    raw, _, support, candidate, _, _ = _fixture()
    _mutate_both(raw, candidate["pid"], "ppid", 99999)
    context = _context(trusted_initializer_factory)
    error = _assert_reject(
        lambda: _derive(raw, context), "INCOMPLETE_CANDIDATE_ANCESTRY"
    )
    assert [support["pid"], candidate["pid"]] == error.detail["withheld_pids"]
    assert error.detail["partial_views_emitted"] is False


def test_complete_chain_produces_candidate_and_support_only_after_validation(
    trusted_initializer_factory,
):
    raw, _, support, candidate, _, _ = _fixture()
    context = _context(trusted_initializer_factory)
    derived = _derive(raw, context)
    assert {(row["pid"], row["create_time"]) for row in derived["project_authorization_candidates"]} == {
        (candidate["pid"], candidate["create_time"])
    }
    assert {(row["pid"], row["create_time"]) for row in derived["support_only_ancestry_nodes"]} == {
        (support["pid"], support["create_time"])
    }


@pytest.mark.parametrize(
    ("view", "field", "value"),
    [
        ("trusted_runner_root", "name", "tampered"),
        ("project_authorization_candidates", "exe", "C:/tampered.exe"),
        ("support_only_ancestry_nodes", "command_line", ["C:/tampered.exe"]),
        ("unrelated_observed_processes", "accessibility_status", "tampered"),
    ],
)
def test_exact_canonical_row_equality_survives_caller_public_rehash(
    trusted_initializer_factory, view, field, value
):
    raw, _, _, _, _, _ = _fixture()
    context = _context(trusted_initializer_factory)
    sealed = _seal(raw, context)
    sealed["views"][view][0][field] = value
    _rewrite_public_hashes(sealed)
    _assert_reject(
        lambda: _verify(raw, sealed, context), "SEALED_CANONICAL_VIEW_MISMATCH"
    )


@pytest.mark.parametrize("operation", ["extra", "missing", "duplicate", "reorder"])
def test_extra_missing_duplicate_or_reordered_view_content_rejects(
    trusted_initializer_factory, operation
):
    raw, _, _, _, _, _ = _fixture()
    context = _context(trusted_initializer_factory)
    sealed = _seal(raw, context)
    rows = sealed["views"]["unrelated_observed_processes"]
    if operation == "extra":
        rows[0]["extra"] = True
    elif operation == "missing":
        rows[0].pop("name")
    elif operation == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    else:
        sealed["candidate_ancestry"][0]["chain"] = list(
            reversed(sealed["candidate_ancestry"][0]["chain"])
        )
    _rewrite_public_hashes(sealed)
    _assert_reject(lambda: _verify(raw, sealed, context), "SEALED_CANONICAL_VIEW_MISMATCH")


def test_cross_context_sealed_view_replay_is_rejected(trusted_initializer_factory):
    raw, _, _, _, _, _ = _fixture()
    context_a = _context(trusted_initializer_factory, session_id="session-a")
    context_b = _context(trusted_initializer_factory, session_id="session-b")
    sealed_a = _seal(raw, context_a)
    _assert_reject(
        lambda: _verify(raw, sealed_a, context_b), "AUTHORITY_CONTEXT_MISMATCH"
    )


def test_visibly_identical_contexts_remain_distinct_capabilities(trusted_initializer_factory):
    raw, _, _, _, _, _ = _fixture()
    context_a = _context(trusted_initializer_factory, session_id="session-a")
    context_b = _context(trusted_initializer_factory, session_id="session-a")
    assert context_a is not context_b
    sealed_a = _seal(raw, context_a)
    _assert_reject(
        lambda: _verify(raw, sealed_a, context_b), "AUTHORITY_CONTEXT_MISMATCH"
    )
