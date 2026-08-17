from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "implementation/scripts/finalize_sys_nag_v4_complete.py"
SPEC = importlib.util.spec_from_file_location("finalize_sys_nag_v4_complete", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

SUITE = ROOT / "runs/sys_nag_v4/official_qwen_20260816T041833_e5618ea5"
RECEIPT = ROOT / "evidence/sys_nag_v4/SYS_NAG_V4_LIVE_RECEIPT.json"


def test_result_cannot_be_written_into_raw_suite(tmp_path: Path) -> None:
    suite = tmp_path / "suite"
    suite.mkdir()
    with pytest.raises(module.FinalizationError, match="output_must_not_modify_raw_suite"):
        module.write_result(suite / "aggregate.json", suite, {"schema": "x"})


@pytest.mark.skipif(not SUITE.is_dir(), reason="ignored formal live suite unavailable")
def test_complete_suite_closes_and_discloses_defects() -> None:
    result = module.finalize(SUITE, RECEIPT)
    assert result["status"] == "COMPLETE_19_VALID_EPISODES_POSTHOC_FINALIZED_AFTER_AGGREGATION_BUG"
    assert result["closure"]["valid_episode_count"] == 19
    assert result["closure"]["resolved_invalid_attempt_count"] == 2
    assert result["performance"]["success_count"] == 6
    assert result["performance"]["reward_sum"] == 6.5
    assert result["interventions"]["route_block_count"] == 4
    assert result["interventions"]["route_block_full_success_count"] == 0
    assert result["paired_reference"]["success_delta"] == 0
    assert result["integrity"]["evidence_integrity_status"] == "PASS"
    assert len(result["disclosed_defects"]) == 2
    assert result["content_sha256"] == module.content_sha256(result)


@pytest.mark.skipif(not SUITE.is_dir(), reason="ignored formal live suite unavailable")
def test_checkpoint_byte_drift_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    original = module.file_sha256

    def drift(path: Path) -> str:
        if path.resolve() == (SUITE / "checkpoint.json").resolve():
            return "0" * 64
        return original(path)

    monkeypatch.setattr(module, "file_sha256", drift)
    with pytest.raises(module.FinalizationError, match="checkpoint_file_hash"):
        module.finalize(SUITE, RECEIPT)


@pytest.mark.skipif(not SUITE.is_dir(), reason="ignored formal live suite unavailable")
def test_summary_hash_drift_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    original = module._load

    def tampered(path: Path, code: str):
        value = original(path, code)
        if path.name == "checkpoint.json":
            value = copy.deepcopy(value)
            value["sys_nag_valid_entries"][0]["summary_sha256"] = "0" * 64
        return value

    monkeypatch.setattr(module, "_load", tampered)
    with pytest.raises(module.FinalizationError, match="checkpoint_content_digest"):
        module.finalize(SUITE, RECEIPT)


@pytest.mark.skipif(not SUITE.is_dir(), reason="ignored formal live suite unavailable")
def test_current_receipt_identity_drift_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
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
