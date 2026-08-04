from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from raven_m.role_binding_timing.infra_m3_log_lifecycle import (
    create_live_root,
    live_root_issues,
    prove_handle_closed,
    seal_live_logs,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPOSITORY_ROOT / "05_project/configs/role_binding_timing/infra_m3_external_log_maintenance_a11y.json"
SCHEMA_PATH = REPOSITORY_ROOT / "05_project/schemas/role_binding_timing_infra_m3_completion.v1.schema.json"
RUNNER_PATH = REPOSITORY_ROOT / "05_project/scripts/run_role_binding_timing_infra_m3.py"
PROTOCOL_PATH = REPOSITORY_ROOT / "04_protocols/role_binding_timing/INFRA_M3_EXTERNAL_LOG_MAINTENANCE_AND_A11Y_V1.md"


def test_rejects_repository_and_artifact_live_roots(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    artifact = repository / "05_project" / "artifacts"
    artifact.mkdir(parents=True)
    required_parent = tmp_path / "external"
    assert "LIVE_ROOT_INSIDE_REPOSITORY" in live_root_issues(
        repository / "live", repository_root=repository,
        forbidden_roots=[artifact], required_parent=required_parent,
    )
    issues = live_root_issues(
        artifact / "old_result" / "live", repository_root=repository,
        forbidden_roots=[artifact], required_parent=required_parent,
    )
    assert "LIVE_ROOT_INSIDE_REPOSITORY" in issues
    assert any(item.startswith("LIVE_ROOT_INSIDE_FORBIDDEN:") for item in issues)


def test_external_fresh_live_root_is_accepted(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    artifact = repository / "artifacts"
    repository.mkdir()
    parent = tmp_path / "runtime_temp"
    live = create_live_root(
        temp_parent=parent, repository_root=repository,
        forbidden_roots=[artifact], prefix="m3_",
    )
    assert live.parent == parent.resolve()
    assert not live_root_issues(
        live, repository_root=repository,
        forbidden_roots=[artifact], required_parent=parent,
    )


def test_seal_requires_owners_and_parent_handles_closed(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    live = tmp_path / "live"
    live.mkdir()
    (live / "stdout.bin").write_bytes(b"x")
    kwargs = dict(
        live_root=live, result_root=repository / "result", names=["stdout.bin"],
        repository_root=repository, forbidden_roots=[repository / "artifacts"],
        required_temp_parent=tmp_path,
    )
    with pytest.raises(RuntimeError, match="LIVE_LOG_OWNER_STILL_RUNNING"):
        seal_live_logs(**kwargs, owners_gone=False, parent_handles_closed=True)
    with pytest.raises(RuntimeError, match="PARENT_LOG_HANDLES_NOT_CLOSED"):
        seal_live_logs(**kwargs, owners_gone=True, parent_handles_closed=False)
    assert not (repository / "result").exists()


def test_handle_probe_failure_prevents_copy(tmp_path: Path) -> None:
    source = tmp_path / "stdout.bin"
    source.write_bytes(b"held")

    def fail_rename(_source: str | os.PathLike[str], _destination: str | os.PathLike[str]) -> None:
        raise PermissionError("simulated open descendant handle")

    with pytest.raises(RuntimeError, match="LIVE_LOG_HANDLE_NOT_CLOSED"):
        prove_handle_closed(source, rename=fail_rename)
    assert source.read_bytes() == b"held"


def test_closed_logs_seal_once_with_exact_hashes(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    live = tmp_path / "live"
    live.mkdir()
    payloads = {"emulator.stdout.bin": b"stdout\x00", "emulator.stderr.bin": b"stderr\xff"}
    for name, payload in payloads.items():
        (live / name).write_bytes(payload)
    result = repository / "artifacts" / "m3" / "finalized_live_logs"
    records = seal_live_logs(
        live_root=live, result_root=result, names=payloads,
        repository_root=repository, forbidden_roots=[repository / "artifacts"],
        required_temp_parent=tmp_path, owners_gone=True, parent_handles_closed=True,
    )
    assert len(records) == 2
    for record in records:
        payload = payloads[record["name"]]
        assert record["sha256"] == hashlib.sha256(payload).hexdigest()
        assert record["handle_closed_before_copy"] is True
        assert record["sealed_once"] is True
    with pytest.raises(RuntimeError, match="SEALED_RESULT_ALREADY_EXISTS"):
        seal_live_logs(
            live_root=live, result_root=result, names=payloads,
            repository_root=repository, forbidden_roots=[repository / "artifacts"],
            required_temp_parent=tmp_path, owners_gone=True, parent_handles_closed=True,
        )


def test_config_freezes_external_logging_and_gate_order() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    logs = config["log_lifecycle"]
    assert Path(logs["temp_parent"]).is_absolute()
    assert not str(Path(logs["temp_parent"]).resolve()).casefold().startswith(str(REPOSITORY_ROOT.resolve()).casefold())
    assert logs["frozen_log_inputs"] == []
    assert logs["live_log_names"] == ["emulator.stdout.bin", "emulator.stderr.bin"]
    assert config["runtime"]["registration_environment"] == {"ANDROID_ADB_SERVER_PORT": "5038"}
    assert config["runtime"]["forbidden_adb_port"] == 5037
    assert config["burn_in"]["cycles"] == 24
    assert config["burn_in"]["minimum_elapsed_seconds"] >= 180
    assert config["sampling"]["settings_observations"] == 3
    assert config["grid"]["required_cells"] == 12
    assert config["generation_calls_authorized"] == 0


def test_source_isolation_and_no_prior_frozen_log_path() -> None:
    joined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (RUNNER_PATH, CONFIG_PATH, PROTOCOL_PATH)
    )
    assert "infra_m1_maintenance_burnin/maintenance/start/emulator.stdout.bin" not in joined
    assert "adb_prefix(config, 5037" not in RUNNER_PATH.read_text(encoding="utf-8")
    assert "ANDROID_ADB_SERVER_PORT" in joined
    assert "seal_live_logs" in RUNNER_PATH.read_text(encoding="utf-8")
    for forbidden in ("H17", "r79", "fixed coordinate", "phone number"):
        assert forbidden.casefold() not in RUNNER_PATH.read_text(encoding="utf-8").casefold()


def minimal_completion() -> dict[str, object]:
    return {
        "schema_version": "role_binding_timing.infra_m3.completion.v1",
        "status": "RUNTIME_UNSTABLE",
        "first_broken_edge": "DEV_TEST",
        "generation_calls": 0,
        "model_tokens": 0,
        "runtime": {},
        "burn_in": {"passed": False, "required_cycles": 24, "completed_cycles": 0, "passed_cycles": 0, "elapsed_seconds": 0, "records": []},
        "a11y": {"authorized": False, "settings": {}, "grid": {}},
        "cleanup": {},
        "log_seal": {"passed": False, "records": [], "temporary_root_removed": False},
        "protected_wip_unchanged": True,
        "claim_evidence": {
            "exclusive_5038_registration": False,
            "burn_in_qualified": False,
            "a11y_tested": False,
            "a11y_qualified": False,
            "v0_3_preparation_authorized": False,
            "held_out_tested": False,
            "role_binding_hypothesis_tested": False,
        },
    }


def test_completion_schema_and_corruption() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    assert not list(validator.iter_errors(minimal_completion()))
    corrupt = minimal_completion()
    corrupt["generation_calls"] = 1
    assert list(validator.iter_errors(corrupt))
