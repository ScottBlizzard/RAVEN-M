from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "implementation/scripts/audit_p2_scope_r2.py"


def load_module():
    spec = importlib.util.spec_from_file_location("audit_p2_scope_r2", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_p2_audit_is_fail_closed_and_self_bound() -> None:
    module = load_module()
    report = module.build(ROOT)
    assert report["status"] == "PREFLIGHT_INVALID_NO_LIVE"
    assert report["generation_calls"] == 0
    assert report["live_authorized"] is False
    assert report["hard_gates"]["raw_trace_hash_binding"]["status"] == "PASS"
    assert report["hard_gates"]["dual_blind_semantic_annotation"]["status"] == "FAIL"
    assert report["adjudication"]["seven_task_live_result"] == "NOT_RUN_G0_INVALID"
    assert report["adjudication"]["not_zero_of_seven"] is True
    assert report["content_sha256"] == module.content_sha256(report)


def test_p2_fixed_seven_projection_is_exact() -> None:
    module = load_module()
    report = module.build(ROOT)
    rows = report["observable_projection"]["fixed_seven"]
    assert [row["task_name"] for row in rows] == module.FIXED_SEVEN
    assert len(report["observable_projection"]["episodes"]) == 19
    assert len({row["episode_id"] for row in report["observable_projection"]["episodes"]}) == 19
    assert sum(row["success"] for row in report["observable_projection"]["episodes"]) == 6


def test_committed_report_matches_recomputation_when_present() -> None:
    module = load_module()
    output = ROOT / module.OUTPUT
    if not output.exists():
        return
    observed = json.loads(output.read_text(encoding="utf-8"))
    assert observed == module.build(ROOT)
