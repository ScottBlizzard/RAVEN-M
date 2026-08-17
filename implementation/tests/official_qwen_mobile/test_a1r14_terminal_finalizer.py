from __future__ import annotations
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
SUITES = sorted((ROOT / "runs/a1r14_rgvr").glob("official_qwen_*"))
SUITE = SUITES[-1] if SUITES else ROOT / "runs/a1r14_rgvr/missing"
spec = importlib.util.spec_from_file_location("f", ROOT / "implementation/scripts/finalize_a1r14_rgvr_terminal.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.skipif(not SUITE.is_dir(), reason="formal A1-R14 suite unavailable")
def test_partial_exposure_is_sealed_without_overclaim(tmp_path: Path) -> None:
    result = module.finalize(SUITE, tmp_path / "result.json")
    assert result["classification"] == "PARTIAL_EXPOSURE_OBSERVATION_REGEX_COVERAGE_REFUTED"
    assert result["outcome"]["retained_values"] == ["7"]
    assert result["claim_boundary"]["nonempty_value_read_observed"] is False
    assert result["closure"]["generation_calls_during_finalization"] == 0
