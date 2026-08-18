from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from implementation.scripts.finalize_a4v2_result import SEVEN, build


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def _digest(value: object) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _file_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _suite(root: Path, rewards: list[float]) -> Path:
    signature = {
        "experiment_id": "A4V2_FAITHFUL_OFFLINE_AWM_QWEN3VL32B_AW_HARD_S20260806_V1",
        "method": "a4v2_faithful_offline_awm_memory_v1",
        "a4v2_launch_receipt_sha256": "1" * 64,
        "a4v2_preflight_sha256": "2" * 64,
        "a4v2_workflow_bank_sha256": "3" * 64,
        "a4v2_campaign_stage": "fixed_seven",
    }
    _write(root / "run_signature.json", signature)
    summaries = []
    entries = []
    aggregate_rows = []
    for index, (task, reward) in enumerate(zip(SEVEN, rewards)):
        episode_id = f"{task}_{index}"
        episode = {
                "episode_id": episode_id,
                "task_name": task,
                "seed": 20260806,
                "evaluator_reward": reward,
                "success": reward == 1.0,
                "error": None,
                "lifecycle_errors": [],
                "started_at": "2026-08-19T00:00:00+00:00",
                "finished_at": "2026-08-19T00:00:01+00:00",
                "model_call_count": 1,
                "executed_action_count": 1,
                "steps": [
                    {
                        "model_call": {
                            "response_sha256": f"response{index}",
                            "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
                            "raven_meta": {"transport_attempts": 1},
                        },
                        "decision": {"canonical_action": {"type": "tap", "x": 0.5, "y": 0.5}},
                    }
                ],
                "memory_mechanism": {
                    "nonempty_read_count": 1,
                    "retrievals": [{"retrieved_ids": [f"workflow_{index}"]}],
                },
                "run_metadata": {
                    "run_signature_sha256": _digest(signature),
                    "live_server_receipt_sha256": "1" * 64,
                },
            }
        episode_path = root / "episodes" / episode_id / "episode.json"
        _write(episode_path, episode)
        (episode_path.with_name("events.jsonl")).write_text("{}\n", encoding="utf-8")
        summaries.append(episode)
        entries.append({
            "task_name": task, "seed": 20260806, "episode_id": episode_id,
            "episode_json_sha256": _file_sha(episode_path),
            "summary_sha256": _digest(episode),
            "run_signature_sha256": _digest(signature),
        })
        aggregate_rows.append({"task_name": task, "episode_id": episode_id, "reward": reward, "success": reward == 1.0})
    _write(root / "aggregate.json", {"per_task": aggregate_rows})
    checkpoint = {
        "schema": "a4v2.scored_checkpoint.v1",
        "experiment_id": signature["experiment_id"],
        "mechanism_id": signature["method"],
        "run_signature_sha256": _digest(signature),
        "valid_summaries": summaries,
        "a4v2_valid_entries": entries,
        "invalid_attempts": [],
    }
    checkpoint["content_sha256"] = _digest(checkpoint)
    _write(root / "checkpoint.json", checkpoint)
    return root


def test_seven_failure_seals_remaining_twelve(tmp_path: Path) -> None:
    result = build(_suite(tmp_path / "seven", [1, 1, 1, 0, 1, 1, 1]))
    assert result["status"] == "SEALED_SEVEN_DIAGNOSTIC_NO_RELEASE"
    assert result["performance"]["seven_success_count"] == 6
    assert result["performance"]["remaining12_released"] is False
    assert sum(row["execution_status"] == "NOT_RUN_BY_7_OF_7_GATE" for row in result["tasks"]) == 12
    assert result["content_sha256"]
