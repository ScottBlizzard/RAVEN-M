from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "implementation/scripts/audit_p3_scer_r2.py"


def load_module():
    spec = importlib.util.spec_from_file_location("audit_p3_scer_r2", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_p3_raw_gap_closed_but_annotation_gate_fails_closed() -> None:
    module = load_module()
    report = module.build(ROOT)
    assert report["hard_gates"]["raw_r2_materialization"]["status"] == "PASS"
    assert report["hard_gates"]["visible_only_annotation_packet"]["status"] == "FAIL"
    assert report["status"] == "PREFLIGHT_INVALID_NO_LIVE"
    assert report["generation_calls"] == 0
    assert report["live_authorized"] is False
    assert report["adjudication"]["not_zero_of_seven"] is True
    assert report["content_sha256"] == module.content_sha256(report)


def test_p3_projection_binds_exact_fixed_seven_and_r2_successes() -> None:
    module = load_module()
    report = module.build(ROOT)
    rows = report["observable_scheduler_projection"]["fixed_seven"]
    assert [row["task_name"] for row in rows] == module.FIXED_SEVEN
    episodes = report["observable_scheduler_projection"]["episodes"]
    assert len(episodes) == 19
    assert sum(row["success"] for row in episodes) == 6
    assert report["existing_direction_evidence"]["sys_nag_v4_success_count"] == 6
    assert report["existing_direction_evidence"]["sys_nag_v4_reward_sum"] == 6.5


def test_committed_p3_report_matches_recomputation_when_present() -> None:
    module = load_module()
    output = ROOT / module.OUTPUT
    if not output.exists():
        return
    assert json.loads(output.read_text(encoding="utf-8")) == module.build(ROOT)
