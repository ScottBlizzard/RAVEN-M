from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "implementation/scripts/finalize_sys_nag_v2_terminal.py"
SPEC = importlib.util.spec_from_file_location("finalize_sys_nag_v2_terminal", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

SUITE = ROOT / "runs/sys_nag_v2/official_qwen_20260816T024642_c7867dfe"
RECEIPT = ROOT / "evidence/sys_nag_v2/SYS_NAG_V2_LIVE_RECEIPT.json"


def test_result_output_cannot_modify_raw_suite(tmp_path: Path) -> None:
    suite = tmp_path / "suite"
    suite.mkdir()
    with pytest.raises(module.FinalizationError, match="output_must_not_modify_raw_suite"):
        module.write_result(suite / "aggregate.json", suite, {"schema": "x"})


@pytest.mark.skipif(not SUITE.is_dir(), reason="ignored formal live suite unavailable")
def test_formal_suite_closes_exactly() -> None:
    result = module.finalize(SUITE, RECEIPT)
    assert result["schema"] == module.contract.RESULT_SCHEMA
    assert result["status"] == "TERMINAL_VALID_SCIENTIFIC_FAILURE"
    assert result["completion"] == "GATE_STOPPED_2_OF_6"
    assert result["closure"]["valid_episode_count"] == 2
    assert result["closure"]["not_run_by_protocol_count"] == 17
    assert result["closure"]["checkpoint_entry_summary_hashes_valid"] is True
    assert result["guard_observed"]["eligible_count"] == 0
    assert result["integrity"]["disclosed_metadata_defects"] == []
    assert result["content_sha256"] == module.content_sha256(result)


@pytest.mark.skipif(not SUITE.is_dir(), reason="ignored formal live suite unavailable")
def test_unallowlisted_entry_hash_tamper_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    original = module._load

    def tampered(path: Path, code: str):
        value = original(path, code)
        if path.name == "checkpoint.json":
            value = copy.deepcopy(value)
            value["sys_nag_valid_entries"][0]["summary_sha256"] = "0" * 64
        return value

    monkeypatch.setattr(module, "_load", tampered)
    with pytest.raises(module.FinalizationError, match="entry_0_summary_hash"):
        module.finalize(SUITE, RECEIPT)


@pytest.mark.skipif(not SUITE.is_dir(), reason="ignored formal live suite unavailable")
def test_receipt_tamper_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    original = module._load

    def tampered(path: Path, code: str):
        value = original(path, code)
        if path.resolve() == RECEIPT.resolve():
            value = copy.deepcopy(value)
            value["served_model_id"] = "wrong/model"
            value["content_sha256"] = module.content_sha256(value)
        return value

    monkeypatch.setattr(module, "_load", tampered)
    with pytest.raises(module.FinalizationError, match="receipt_served_model_id"):
        module.finalize(SUITE, RECEIPT)
