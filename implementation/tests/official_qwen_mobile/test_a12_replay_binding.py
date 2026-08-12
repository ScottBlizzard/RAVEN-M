from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "implementation/scripts/build_a12_reference_segments.py"


def _module():
    spec = importlib.util.spec_from_file_location("a12_reference_builder", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reference_builder_is_independent_of_a12_production_memory() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "from raven_m.official_qwen_mobile.a12" not in source
    assert "import raven_m.official_qwen_mobile.a12" not in source
    assert "A12_OFFLINE_REPLAY_REPORT" not in source


def test_builder_detects_current_frozen_protocol_invalid_evidence() -> None:
    trace_root = ROOT / "runs/a10_offline_replay_materialized"
    if not trace_root.is_dir():
        return
    report = _module().build(trace_root)
    assert report["generation_calls"] == 0
    assert report["frozen_reference_segment_count"] == 23
    assert report["pairwise_support_valid_segment_count"] == 16
    assert report["independently_valid_segment_count"] == 11
    assert report["theoretical_max_after_chronology_cooldown_one_shot_and_cap"] == 11
    verification = report["source"]["materialized_trace_verification"]
    assert verification == {
        "status": "pass",
        "declared_file_count": 1668,
        "observed_total_bytes": 442138413,
        "errors": [],
    }
    assert report["status"] == "protocol_invalid"
    assert report["verdict"] == "A12_PROTOCOL_INVALID"
    assert "a12_theoretical_max_qualifiable_segments_below_20" in report["errors"]


def test_builder_requires_all_23_references_before_any_formal_replay() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert 'if valid_count != 23:' in source
    assert 'if valid_count < 20:' in source
    assert '"status": "pass" if not errors else "protocol_invalid"' in source
