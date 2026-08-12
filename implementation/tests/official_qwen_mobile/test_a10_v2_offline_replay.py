from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "evidence/a10_v2/A10_V2_OFFLINE_REPLAY_REPORT.json"


def test_committed_a10_v2_real_replay_is_zero_generation_and_not_misreported() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert report["schema"] == "a10_v2_offline_replay_report_v1"
    assert report["generation_calls"] == 0
    assert report["verification"]["status"] == "pass"
    assert report["verification"]["verified_file_count"] == 1668
    assert report["verification"]["verified_total_bytes"] == 442138413
    assert report["episode_count"] == 27
    assert report["a6_qualifying_segments"] == 23
    assert report["status"] == "fail"
    assert report["errors"]
    current_core = ROOT / "implementation/src/raven_m/official_qwen_mobile/a10_v2_obligation_branch_frontier.py"
    from hashlib import sha256
    assert report["mechanism_source_sha256"] == sha256(current_core.read_bytes()).hexdigest()


def test_a10_v2_a0_competent_history_is_absolutely_silent() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    competent = [
        item for item in report["episodes"]
        if item["role"] == "a0" and item["task_name"] != "RecipeDeleteMultipleRecipesWithConstraint"
    ]
    assert len(competent) == 4
    assert all(item["nonempty_read_count"] == 0 for item in competent)
    assert all(item["mature_trigger_count"] == 0 for item in competent)
    assert all(item["max_rendered_chars"] == 0 for item in competent)
