from __future__ import annotations

import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
SUITES = sorted((ROOT / "runs/a1r15_eovr").glob("official_qwen_*"))
SUITE = SUITES[-1] if SUITES else ROOT / "runs/a1r15_eovr/missing"
spec = importlib.util.spec_from_file_location("f", ROOT / "implementation/scripts/finalize_a1r15_eovr_terminal.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.skipif(not SUITE.is_dir(), reason="formal A1-R15 suite unavailable")
def test_target_success_without_evr_read_is_sealed_unattributed(tmp_path: Path) -> None:
    result = module.finalize(SUITE, tmp_path / "result.json")
    assert result["classification"] == "TARGET_SUCCESS_WITHOUT_MATURE_EVR_READ_UNATTRIBUTED"
    assert result["outcome"]["reward"] == 1.0
    assert result["outcome"]["retained_values"] == ["8", "2"]
    assert result["outcome"]["rendered_value_read_count"] == 0
    assert result["claim_boundary"]["success_attributed_to_evr"] is False
    assert result["claim_boundary"]["remaining_suite_released"] is False


@pytest.mark.skipif(not SUITE.is_dir(), reason="formal A1-R15 suite unavailable")
def test_finalization_is_cpu_only_and_hash_closed(tmp_path: Path) -> None:
    result = module.finalize(SUITE, tmp_path / "result.json")
    assert result["closure"]["generation_calls_during_finalization"] == 0
    assert result["closure"]["valid_episode_count"] == 1
    assert result["closure"]["not_run_by_protocol_count"] == 18
    assert result["verdicts"]["mechanism"] == "NOT_OBSERVED_NO_EVR_READ"
