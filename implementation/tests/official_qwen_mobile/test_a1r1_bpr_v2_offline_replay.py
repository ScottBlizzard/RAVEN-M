from __future__ import annotations

from pathlib import Path

from implementation.scripts.replay_a1r1_bpr_v2_offline import reconstruct


ROOT = Path(__file__).resolve().parents[3]


def test_real_a1_replay_reconstructs_exact_denominator_and_gate() -> None:
    report = reconstruct(ROOT / "runs/a1_working_memory/official_qwen_20260810T122419_26573d7c")
    assert report["status"] == "PASS"
    assert report["errors"] == []
    assert report["generation_calls"] == 0
    assert report["R3"]["record_count"] == 514
    assert report["R3"]["joint_fit_count"] == 511
    assert report["R3"]["ordered_records_sha256"] == "2e42b4f1ccffd4cc88f9f1ae19021cb0675eea5729235c03e4b74056f1640f99"
    assert len(report["R3"]["nonfit_records"]) == 3
    assert report["R5_status"] == "PROSPECTIVE_UNKNOWN_PRELIVE"
