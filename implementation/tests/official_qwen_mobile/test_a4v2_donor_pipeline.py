from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from implementation.scripts.build_a4v2_donor_source_lock import (
    _episode_valid,
    _events_valid,
)


ROOT = Path(__file__).resolve().parents[3]


def _digest(value: object) -> str:
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def test_materialized_required_manifest_is_exact_and_self_hashed() -> None:
    path = ROOT / "evidence/a4v2/A4V2_DONOR_ACQUISITION_MANIFEST_V2.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    body = {key: value for key, value in payload.items() if key != "content_sha256"}
    assert payload["content_sha256"] == _digest(body)
    assert len(payload["tasks"]) == 14
    assert payload["androidworld_worktree_identity"]["head"] == payload["androidworld_commit"]
    assert len(payload["androidworld_worktree_identity"]["tracked_diff_sha256"]) == 64
    assert all(row["optional"] is False for row in payload["tasks"])
    sports = [row for row in payload["tasks"] if row["route_id"] == "opentracks_retrieve_duration"]
    assert [(row["task_class"], row["task_seed"]) for row in sports] == [
        ("SportsTrackerActivityDuration", 20260842),
        ("SportsTrackerActivityDuration", 20260843),
    ]
    osm = [row for row in payload["tasks"] if row["route_id"] == "osmand_open_location_result"]
    assert len(osm) == 2


def test_donor_validity_requires_single_transport_and_evaluator_closure(tmp_path: Path) -> None:
    episode = {
        "error": None,
        "lifecycle_errors": [],
        "model_call_count": 1,
        "steps": [{"model_call": {"raven_meta": {"transport_attempts": 1}}}],
    }
    assert _episode_valid(episode)
    episode["steps"][0]["model_call"]["raven_meta"]["transport_attempts"] = 2
    assert not _episode_valid(episode)

    events = tmp_path / "events.jsonl"
    complete_episode = {
        "episode_id": "ep", "task_name": "Task", "seed": 7,
        "step_count": 1, "steps": [{}], "evaluator_reward": 1.0,
        "model_claimed_status": "success", "success": True,
        "termination_reason": "model_terminate_success",
    }
    rows = [
        {"event": "episode_start", "episode_id": "ep", "task_name": "Task", "seed": 7},
        {"event": "task_initialized"},
        {"event": "step"},
        {"event": "evaluator_result", "reward": 1.0, "visible_to_agent": False, "model_claimed_status": "success"},
        {"event": "task_torn_down"},
        {"event": "post_episode_reset"},
        {"event": "episode_complete", "success": True, "termination_reason": "model_terminate_success"},
    ]
    events.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    assert _events_valid(events, episode=complete_episode)
    complete_episode["evaluator_reward"] = 0.0
    assert not _events_valid(events, episode=complete_episode)


def test_runner_freezes_donor_and_scoring_claim_boundaries() -> None:
    source = (ROOT / "implementation/scripts/run_official_qwen_mobile.py").read_text(encoding="utf-8")
    assert "a4v2_donor_acquisition_v1" in source
    assert "a0_official_qwen3vl32b_screenshot_only_donor_acquisition" in source
    assert "single_http_attempt_no_automatic_retry" in source
    assert "post_observed_seed20260806_fixed_seven_workflow_transfer_diagnostic" in source
