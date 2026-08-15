from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "implementation/scripts/finalize_a1r3v3_oscnr_gate.py"
SPEC = importlib.util.spec_from_file_location("finalize_a1r3v3_oscnr_gate", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

SUITE = ROOT / "runs/a1r3v3_oscnr/official_qwen_20260815T150827_f10cb784"
RECEIPT = ROOT / "evidence/a1r3_v3/A1R3V3_OSCNR_LIVE_RECEIPT.json"


def test_content_hash_ignores_only_its_own_hash() -> None:
    left = {"schema": "x", "nested": {"value": 1}, "content_sha256": "old"}
    right = {"content_sha256": "new", "nested": {"value": 1}, "schema": "x"}
    assert module.content_sha256(left) == module.content_sha256(right)
    right["nested"]["value"] = 2
    assert module.content_sha256(left) != module.content_sha256(right)


def test_checkpoint_content_tampering_fails_closed() -> None:
    checkpoint = {
        "schema": module.contract.CHECKPOINT_SCHEMA,
        "prospective_arm": "a1r3v3",
        "mechanism_id": module.contract.MECHANISM_ID,
        "experiment_id": module.contract.EXPERIMENT_ID,
        "suite_id": "suite",
        "checkpoint_ordinal": 0,
        "run_signature_sha256": "s" * 64,
    }
    checkpoint["content_sha256"] = module.content_sha256(checkpoint)
    module._validate_checkpoint_document(
        checkpoint, ordinal=0, suite_id="suite", signature_sha="s" * 64
    )
    checkpoint["status"] = "tampered"
    with pytest.raises(module.FinalizationError, match="content_hash"):
        module._validate_checkpoint_document(
            checkpoint, ordinal=0, suite_id="suite", signature_sha="s" * 64
        )


def test_bound_episode_artifact_tampering_fails_closed(tmp_path: Path) -> None:
    artifact = tmp_path / "screen.png"
    artifact.write_bytes(b"original")
    expected = module.file_sha256(artifact)
    assert module._validate_bound_file(tmp_path, "screen.png", expected, "screen") == "screen.png"
    artifact.write_bytes(b"tampered")
    with pytest.raises(module.FinalizationError, match="screen_hash"):
        module._validate_bound_file(tmp_path, "screen.png", expected, "screen")


def test_output_inside_raw_suite_is_rejected(tmp_path: Path) -> None:
    suite = tmp_path / "suite"
    suite.mkdir()
    with pytest.raises(module.FinalizationError, match="output_must_not_modify_raw_suite"):
        module.write_result(suite / "aggregate.json", suite, {"schema": "x"})


@pytest.mark.skipif(not SUITE.is_dir(), reason="ignored formal live suite is not available")
def test_formal_terminal_suite_validates_and_has_exact_18_unrun() -> None:
    result = module.finalize(SUITE, RECEIPT)
    assert result["schema"] == module.contract.RESULT_SCHEMA
    assert result["status"] == "TERMINAL_VALID_SCIENTIFIC_FAILURE"
    assert result["completion"] == "GATE_STOPPED_1_OF_6"
    assert result["closure"]["valid_episode_count"] == 1
    assert result["closure"]["invalid_attempt_count"] == 0
    assert result["closure"]["not_run_by_protocol_count"] == 18
    assert sum(
        row["execution_status"] == "NOT_RUN_BY_PROTOCOL" for row in result["tasks"]
    ) == 18
    assert result["identity"]["source_freeze_content_sha256"] == (
        "cf356211a2281a5fb315108e9a789c5ddee1bbb8d7e73fd4ae575b5b1aa70ac4"
    )
    assert result["verdicts"]["cost"] == "NOT_APPLICABLE_PARTIAL"
    assert result["verdicts"]["mechanism"] == "NOT_OBSERVED_NO_CNR_COMMIT"
    assert result["closure"]["generation_calls_during_finalization"] == 0
    assert result["closure"]["network_calls_during_finalization"] == 0
    assert result["content_sha256"] == module.content_sha256(result)


@pytest.mark.skipif(not SUITE.is_dir(), reason="ignored formal live suite is not available")
def test_run_signature_tampering_is_detected_before_result_build(monkeypatch: pytest.MonkeyPatch) -> None:
    original = module._load_json

    def tampered(path: Path, code: str):
        value = original(path, code)
        if path.name == "run_signature.json":
            value = copy.deepcopy(value)
            value["generation_seed"] = 999
        return value

    monkeypatch.setattr(module, "_load_json", tampered)
    with pytest.raises(module.FinalizationError, match="run_signature_generation_seed"):
        module.finalize(SUITE, RECEIPT)


@pytest.mark.skipif(not SUITE.is_dir(), reason="ignored formal live suite is not available")
def test_receipt_tampering_is_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    original = module._load_json

    def tampered(path: Path, code: str):
        value = original(path, code)
        if path.resolve() == RECEIPT.resolve():
            value = copy.deepcopy(value)
            value["served_model_id"] = "wrong/model"
        return value

    monkeypatch.setattr(module, "_load_json", tampered)
    with pytest.raises(module.FinalizationError, match="receipt_served_model_id"):
        module.finalize(SUITE, RECEIPT)
