from __future__ import annotations

import json

from implementation.scripts.replay_a1r3_stale_resistant_pending import replay
from raven_m.official_qwen_mobile import a1r3_contract as contract


def test_formal_replay_is_current_reproducible_and_authorizing() -> None:
    suite = contract.REPOSITORY_ROOT / (
        "runs/a1r2_cvp/official_qwen_20260814T145307_50081981"
    )
    current = replay(suite)
    frozen = json.loads(contract.OFFLINE_REPLAY_PATH.read_text(encoding="utf-8"))
    for key in (
        "schema",
        "status",
        "errors",
        "generation_calls",
        "mechanism_id",
        "source",
        "totals",
        "sentinel_tasks",
        "episodes",
    ):
        assert current[key] == frozen[key]
    assert frozen["content_sha256"] == contract.content_sha256(frozen)
    totals = frozen["totals"]
    assert frozen["status"] == "PASS"
    assert totals["valid_episode_count"] == 19
    assert totals["nonreinforcing_state_write_count"] >= 100
    assert totals["failure_evidence_read_episode_count"] >= 2
    assert totals["projected_render_ratio_vs_a1r2"] <= 0.75
