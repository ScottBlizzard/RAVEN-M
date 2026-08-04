from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from raven_m.role_binding_timing.infra_m4_terminal_accounting import PhaseJournal
from raven_m.role_binding_timing.infra_m9_terminal import finalize_completion, minimal_completion


ROOT = Path(__file__).resolve().parents[3]


def runner():
    path = ROOT / "05_project/scripts/run_role_binding_timing_infra_m9.py"
    spec = importlib.util.spec_from_file_location("m9_runner_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_overlay_resolves_zero_generation_disjoint_view_contract() -> None:
    value = runner().resolve_overlay(
        ROOT / "05_project/configs/role_binding_timing/infra_m9_authorization_view_separation.json"
    )
    assert value["generation_calls_authorized"] == 0 and value["generation_eligible"] is False
    assert value["runtime"]["adb_server_port"] == 5038 and value["runtime"]["fallback_to_5037"] is False
    views = value["process_views"]
    assert views["role_policy_input"] == "project_authorization_candidates_only"
    assert views["support_role_authority"] is False
    assert views["unrelated_role_authority"] is False


def test_overlay_base_drift_fails_closed(tmp_path: Path) -> None:
    module = runner()
    source = json.loads((ROOT / "05_project/configs/role_binding_timing/infra_m9_authorization_view_separation.json").read_text(encoding="utf-8"))
    source["base_config_sha256"] = "0" * 64
    path = tmp_path / "overlay.json"
    path.write_text(json.dumps(source), encoding="utf-8")
    try:
        module.resolve_overlay(path)
    except RuntimeError as exc:
        assert "M8_BASE_CONFIG_DRIFT" in str(exc)
    else:
        raise AssertionError("drift accepted")


def test_terminal_schema_accepts_failure_and_rejects_generation(tmp_path: Path) -> None:
    journal = PhaseJournal(tmp_path / "journal")
    journal.record(phase="launch", event="end", status="FAIL", first_broken_edge="EDGE")
    value = finalize_completion(
        output_root=tmp_path, journal=journal, run_id="test",
        status="PROCESS_IDENTITY_FAILED", rich_completion=None,
    )
    schema = json.loads((ROOT / "05_project/schemas/role_binding_timing_infra_m9_completion.v1.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    assert not list(validator.iter_errors(value))
    value["generation_calls"] = 1
    assert list(validator.iter_errors(value))


def test_pass_requires_complete_chain_and_view_claim() -> None:
    value = minimal_completion(run_id="test", status="PASS_12_OF_12_DEV", first_edge=None)
    value.update(last_completed_phase="seal", journal_entry_count=10, journal_terminal_event_present=True)
    schema = json.loads((ROOT / "05_project/schemas/role_binding_timing_infra_m9_completion.v1.schema.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(value))
