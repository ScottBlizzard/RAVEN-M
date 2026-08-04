from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from raven_m.role_binding_timing.infra_m4_terminal_accounting import PhaseJournal
from raven_m.role_binding_timing.infra_m7_terminal import finalize_completion, minimal_completion


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def load_runner():
    path = REPOSITORY_ROOT / "05_project/scripts/run_role_binding_timing_infra_m7.py"
    spec = importlib.util.spec_from_file_location("m7_runner_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_overlay_resolves_frozen_m6_without_generation_or_5037_fallback() -> None:
    module = load_runner()
    path = REPOSITORY_ROOT / "05_project/configs/role_binding_timing/infra_m7_runner_adb_authority.json"
    config = module.resolve_overlay(path)
    assert config["protocol_version"] == "role_binding_timing.infra_m7.runner_adb_authority.v1"
    assert config["generation_calls_authorized"] == 0
    assert config["generation_eligible"] is False
    assert config["runtime"]["adb_server_port"] == 5038
    assert config["runtime"]["fallback_to_5037"] is False
    assert config["runner_adb_client"]["ordinary_subcommand_allowlist"] is None


def test_overlay_base_hash_drift_fails_closed(tmp_path: Path) -> None:
    module = load_runner()
    source = json.loads((REPOSITORY_ROOT / "05_project/configs/role_binding_timing/infra_m7_runner_adb_authority.json").read_text(encoding="utf-8"))
    source["base_config_sha256"] = "0" * 64
    path = tmp_path / "overlay.json"; path.write_text(json.dumps(source), encoding="utf-8")
    try:
        module.resolve_overlay(path)
    except RuntimeError as exc:
        assert "M6_BASE_CONFIG_DRIFT" in str(exc)
    else:
        raise AssertionError("drift was accepted")


def test_minimal_terminal_validates_and_rejects_claim_overreach(tmp_path: Path) -> None:
    journal = PhaseJournal(tmp_path / "journal")
    journal.record(phase="framework", event="end", status="FAIL", first_broken_edge="TEST_EDGE")
    value = finalize_completion(output_root=tmp_path, journal=journal, run_id="test", status="RUNTIME_UNSTABLE", rich_completion=None)
    schema = json.loads((REPOSITORY_ROOT / "05_project/schemas/role_binding_timing_infra_m7_completion.v1.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    assert list(validator.iter_errors(value)) == []
    value["generation_calls"] = 1
    assert list(validator.iter_errors(value))


def test_pass_schema_requires_runner_authority_and_complete_chain() -> None:
    value = minimal_completion(run_id="test", status="PASS_12_OF_12_DEV", first_edge=None)
    value.update(last_completed_phase="seal", journal_entry_count=10, journal_terminal_event_present=True)
    schema = json.loads((REPOSITORY_ROOT / "05_project/schemas/role_binding_timing_infra_m7_completion.v1.schema.json").read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(value))
    assert errors
    assert any("True was expected" in error.message or "24 was expected" in error.message for error in errors)
