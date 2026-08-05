"""Frozen role-source gates for the INFRA-M12 DEV engineering contract.

This file must be run and pass before temporal-attestation tests. The future
implementation module is deliberately absent at freeze time, so the suite is
not executed in the freeze phase.
"""

from __future__ import annotations

import copy
import hashlib
import importlib
import json
from pathlib import Path

import pytest

from raven_m.role_binding_timing.infra_m9_authorization_views import derive_process_views


MODULE = "raven_m.role_binding_timing.infra_m12_sealed_role_derivation"
ROOT = Path(__file__).resolve().parents[3]
CLASSIFIER_VERSION = "infra-m12-derive-authorization-views-v1"
CLASSIFIER_CONTRACT_SHA256 = "973192F1D6153F099D9BCC38E784B4C9E2F5203F9CAC77910B349BCCE31D70A0"
CONTROLLED_PORTS = [5037, 5038, 5554, 5555, 8554]


def _sut():
    return importlib.import_module(MODULE)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def _row(pid, create_time, ppid, name, *, exe=None, exe_sha256=None, command_line=None):
    path = exe or f"C:/fixture/{name}.exe"
    return {
        "pid": pid,
        "create_time": create_time,
        "ppid": ppid,
        "name": name,
        "exe": path,
        "exe_sha256": exe_sha256 or _sha(path.lower()),
        "command_line": command_line or [path, "--fixture"],
        "accessibility_status": "accessible",
        "access_error": None,
    }


def _fixture():
    runner = _row(100, 1000.0, 1, "runner")
    support = _row(200, 1001.0, 100, "wrapper")
    candidate = _row(300, 1002.0, 200, "locked_client")
    unrelated = _row(400, 1003.0, 1, "unrelated")
    raw = {
        "schema_version": "role_binding_timing.infra_m12.raw_process_snapshot.fixture.v1",
        "sample_sequence": 7,
        "sample_time_utc": "2026-08-05T00:00:00Z",
        "observation_universe_complete": True,
        "observation_universe_capture_errors": [],
        "all_processes": [runner, support, candidate, unrelated],
        "structural_processes": copy.deepcopy([runner, support, candidate, unrelated]),
        "all_tcp_listener_ports_by_pid": {},
        "listener_evidence_complete": True,
    }
    known = [
        {
            "logical_role": "locked_client",
            "normalized_path": candidate["exe"],
            "exe_sha256": candidate["exe_sha256"],
        }
    ]
    return raw, runner, known


def _derive(raw=None, runner=None, known=None, ports=None, version=None, contract_hash=None):
    base_raw, base_runner, base_known = _fixture()
    return _sut().derive_authorization_views(
        raw_snapshot=raw or base_raw,
        locked_runner_record=runner or base_runner,
        locked_known_paths=known or base_known,
        controlled_ports=ports or CONTROLLED_PORTS,
        classifier_version=version or CLASSIFIER_VERSION,
        classifier_contract_sha256=contract_hash or CLASSIFIER_CONTRACT_SHA256,
        classifier_implementation_sha256=_sut().implementation_sha256(),
    )


def _seal(raw=None, runner=None, known=None, ports=None):
    base_raw, base_runner, base_known = _fixture()
    actual_raw = raw or base_raw
    actual_runner = runner or base_runner
    actual_known = known or base_known
    views = _derive(actual_raw, actual_runner, actual_known, ports)
    return _sut().seal_derived_view(
        raw_snapshot=actual_raw,
        derived_views=views,
        locked_runner_record=actual_runner,
        locked_known_paths=actual_known,
        controlled_ports=ports or CONTROLLED_PORTS,
        classifier_version=CLASSIFIER_VERSION,
        classifier_contract_sha256=CLASSIFIER_CONTRACT_SHA256,
        classifier_implementation_sha256=_sut().implementation_sha256(),
        classifier_implementation_blob_oid=_sut().implementation_blob_oid(),
    )


def _assert_reject(callable_, code):
    with pytest.raises(_sut().AuthorizationViewError) as caught:
        callable_()
    assert caught.value.code == code


def _ids(rows):
    return {(row["pid"], row["create_time"]) for row in rows}


def test_roles_are_derived_from_locked_inputs_not_raw_labels():
    raw, runner, known = _fixture()
    view = _derive(raw, runner, known)
    assert _ids(view["trusted_runner_root"]) == {(100, 1000.0)}
    assert _ids(view["project_authorization_candidates"]) == {(300, 1002.0)}
    assert _ids(view["support_only_ancestry_nodes"]) == {(200, 1001.0)}
    assert _ids(view["unrelated_observed_processes"]) == {(400, 1003.0)}
    assert view["type_assertions"]["views_disjoint"] is True
    assert view["type_assertions"]["universe_covered"] is True


@pytest.mark.parametrize(
    "field",
    ["role", "observed_class", "view_class", "authorization_candidate_reasons", "trusted_runner"],
)
def test_raw_self_label_is_rejected(field):
    raw, runner, known = _fixture()
    raw["all_processes"][2][field] = "project_authorization_candidates"
    _assert_reject(lambda: _derive(raw, runner, known), "RAW_AUTHORITY_LABEL_PRESENT")


def test_support_cannot_be_relabelled_as_candidate_in_sealed_partition():
    raw, runner, known = _fixture()
    sealed = _seal(raw, runner, known)
    support = sealed["views"]["support_only_ancestry_nodes"].pop()
    sealed["views"]["project_authorization_candidates"].append(support)
    _assert_reject(
        lambda: _sut().recompute_and_verify_sealed_view(raw, sealed, runner, known, CONTROLLED_PORTS),
        "DERIVED_PARTITION_CLASS_TAMPER",
    )


def test_unrelated_cannot_be_relabelled_as_candidate_in_sealed_partition():
    raw, runner, known = _fixture()
    sealed = _seal(raw, runner, known)
    unrelated = sealed["views"]["unrelated_observed_processes"].pop()
    sealed["views"]["project_authorization_candidates"].append(unrelated)
    _assert_reject(
        lambda: _sut().recompute_and_verify_sealed_view(raw, sealed, runner, known, CONTROLLED_PORTS),
        "DERIVED_PARTITION_CLASS_TAMPER",
    )


def test_fake_trusted_runner_is_rejected():
    raw, runner, known = _fixture()
    fake = copy.deepcopy(raw["all_processes"][-1])
    _assert_reject(lambda: _derive(raw, fake, known), "LOCKED_RUNNER_IDENTITY_MISMATCH")


def test_candidate_reason_tamper_is_rejected():
    raw, runner, known = _fixture()
    sealed = _seal(raw, runner, known)
    sealed["views"]["project_authorization_candidates"][0]["authorization_candidate_reasons"] = [
        "CALLER_ASSERTED_REASON"
    ]
    _assert_reject(
        lambda: _sut().recompute_and_verify_sealed_view(raw, sealed, runner, known, CONTROLLED_PORTS),
        "CANDIDATE_REASON_TAMPER",
    )


def test_known_path_configuration_tamper_is_rejected():
    raw, runner, known = _fixture()
    sealed = _seal(raw, runner, known)
    tampered = copy.deepcopy(known)
    tampered[0]["normalized_path"] = "C:/fixture/other.exe"
    _assert_reject(
        lambda: _sut().recompute_and_verify_sealed_view(raw, sealed, runner, tampered, CONTROLLED_PORTS),
        "LOCKED_KNOWN_PATHS_HASH_MISMATCH",
    )


def test_controlled_port_evidence_tamper_is_rejected():
    raw, runner, known = _fixture()
    raw["all_tcp_listener_ports_by_pid"] = {"400": [8554]}
    sealed = _seal(raw, runner, known)
    current = copy.deepcopy(raw)
    current["all_tcp_listener_ports_by_pid"] = {}
    _assert_reject(
        lambda: _sut().recompute_and_verify_sealed_view(current, sealed, runner, known, CONTROLLED_PORTS),
        "CONTROLLED_PORT_EVIDENCE_MISMATCH",
    )


def test_derived_partition_class_tamper_is_rejected_even_if_hash_is_rewritten():
    raw, runner, known = _fixture()
    sealed = _seal(raw, runner, known)
    sealed["views"]["unrelated_observed_processes"], sealed["views"]["support_only_ancestry_nodes"] = (
        sealed["views"]["support_only_ancestry_nodes"],
        sealed["views"]["unrelated_observed_processes"],
    )
    sealed["partition_hashes"] = _sut().hash_partitions(sealed["views"])
    _assert_reject(
        lambda: _sut().recompute_and_verify_sealed_view(raw, sealed, runner, known, CONTROLLED_PORTS),
        "RECOMPUTED_VIEW_MISMATCH",
    )


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("classifier_version", "other-version", "CLASSIFIER_VERSION_MISMATCH"),
        ("classifier_contract_sha256", "0" * 64, "CLASSIFIER_CONTRACT_HASH_MISMATCH"),
        ("classifier_implementation_sha256", "0" * 64, "CLASSIFIER_IMPLEMENTATION_HASH_MISMATCH"),
    ],
)
def test_classifier_binding_mismatch_is_rejected(field, value, code):
    raw, runner, known = _fixture()
    sealed = _seal(raw, runner, known)
    sealed["classifier_binding"][field] = value
    _assert_reject(
        lambda: _sut().recompute_and_verify_sealed_view(raw, sealed, runner, known, CONTROLLED_PORTS),
        code,
    )


def test_sealed_view_and_raw_snapshot_mismatch_is_rejected():
    raw, runner, known = _fixture()
    sealed = _seal(raw, runner, known)
    current = copy.deepcopy(raw)
    current["all_processes"][-1]["command_line"] = ["C:/different.exe"]
    _assert_reject(
        lambda: _sut().recompute_and_verify_sealed_view(current, sealed, runner, known, CONTROLLED_PORTS),
        "RAW_SNAPSHOT_HASH_MISMATCH",
    )


def test_same_pid_different_creation_time_is_rejected():
    raw, runner, known = _fixture()
    sealed = _seal(raw, runner, known)
    current = copy.deepcopy(raw)
    current["all_processes"][2]["create_time"] += 10.0
    current["structural_processes"][2]["create_time"] += 10.0
    _assert_reject(
        lambda: _sut().recompute_and_verify_sealed_view(current, sealed, runner, known, CONTROLLED_PORTS),
        "PID_CREATE_TIME_REUSE",
    )


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
    base = _resolve_overlay(ROOT / data["base_config"])
    return _merge(base, data.get("overrides", {}))


def test_exact_frozen_m9_deriver_compatibility_replay():
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
        for view_name in (
            "trusted_runner_root",
            "project_authorization_candidates",
            "support_only_ancestry_nodes",
            "unrelated_observed_processes",
        ):
            expected_rows = expected[view_name]
            if isinstance(expected_rows, dict):
                expected_rows = [expected_rows]
            assert _ids(actual[view_name]) == _ids(expected_rows), path
