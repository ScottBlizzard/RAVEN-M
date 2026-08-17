from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "implementation/scripts/finalize_a1r13d_evr_terminal.py"
SUITES = sorted((ROOT / "runs/a1r13d_evr").glob("official_qwen_*"))
SUITE = SUITES[-1] if SUITES else ROOT / "runs/a1r13d_evr/missing"
spec = importlib.util.spec_from_file_location("finalize_a1r13d_evr_terminal", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.skipif(not SUITE.is_dir(), reason="formal A1-R13D suite unavailable")
def test_target_failure_is_sealed_without_causal_overclaim(tmp_path: Path) -> None:
    result = module.finalize(SUITE, tmp_path / "result.json")
    assert result["status"] == "TERMINAL_VALID_SCIENTIFIC_FAILURE"
    assert result["classification"] == "TARGET_NO_EXPOSURE_TRIGGER_CONTRACT_REFUTED"
    assert result["outcome"]["evr_counters"]["activation_count"] == 0
    assert result["claim_boundary"]["evr_effect_evaluated"] is False
    assert result["closure"]["generation_calls_during_finalization"] == 0
    assert result["closure"]["not_run_by_protocol_count"] == 18
