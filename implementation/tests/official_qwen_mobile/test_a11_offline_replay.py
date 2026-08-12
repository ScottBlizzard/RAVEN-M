from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "evidence/a11/A11_OFFLINE_REPLAY_REPORT.json"


def test_committed_a11_real_replay_is_zero_generation_and_not_misreported() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["schema"] == "a11_offline_replay_report_v1"
    assert report["generation_calls"] == 0
    assert report["verification"]["status"] == "pass"
    assert report["verification"]["verified_file_count"] == 1668
    assert report["verification"]["verified_total_bytes"] == 442138413
    assert report["episode_count"] == 27
    assert report["a6_qualifying_segments"] == 23
    assert report["status"] == "fail"
    assert report["errors"]
    current_core = ROOT / "implementation/src/raven_m/official_qwen_mobile/a11_confirmed_route_contraction.py"
    from hashlib import sha256
    assert report["mechanism_source_sha256"] == sha256(current_core.read_bytes()).hexdigest()


def test_a11_competent_sparse_gate_passes_without_single_route_delivery() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    gate = report["competent_sparse_gate"]
    assert gate["status"] == "pass"
    assert gate["total_nonempty_reads"] == 1
    assert gate["total_read_density"] <= 0.04
    assert gate["single_closed_route_delivery_count"] == 0
    assert gate["support_count_below_two_delivery_count"] == 0
