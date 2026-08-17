from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "implementation/scripts/finalize_a1r13_evr_terminal.py"
SUITES = sorted((ROOT / "runs/a1r13_evr").glob("official_qwen_*"))
SUITE = SUITES[-1] if SUITES else ROOT / "runs/a1r13_evr/missing"
spec = importlib.util.spec_from_file_location("finalize_a1r13_evr_terminal", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.skipif(not SUITE.is_dir(), reason="formal A1-R13 suite unavailable")
def test_terminal_suite_seals_as_silent_unattributed_failure(tmp_path: Path) -> None:
    result = module.finalize(SUITE, tmp_path / "result.json")
    assert result["status"] == "TERMINAL_VALID_SCIENTIFIC_FAILURE"
    assert result["classification"] == "SILENT_PRESERVATION_FAILURE_UNATTRIBUTED"
    assert result["outcome"]["reward"] == 0.0
    assert result["outcome"]["evr_counters"]["activation_count"] == 0
    assert result["closure"]["not_run_by_protocol_count"] == 18
    assert sum(row["execution_status"] == "NOT_RUN_BY_PROTOCOL" for row in result["tasks"]) == 18


@pytest.mark.skipif(not SUITE.is_dir(), reason="formal A1-R13 suite unavailable")
def test_terminal_seal_has_no_generation_or_causal_overclaim(tmp_path: Path) -> None:
    result = module.finalize(SUITE, tmp_path / "result.json")
    assert result["closure"]["generation_calls_during_finalization"] == 0
    assert result["claim_boundary"]["evr_causal_effect_observed"] is False
    assert result["claim_boundary"]["evr_harm_inferred"] is False
    assert result["claim_boundary"]["browser_target_evaluated"] is False
