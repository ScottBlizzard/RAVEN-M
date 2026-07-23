import json
from pathlib import Path
import sys


SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from sample_retrieval_audit import collect  # noqa: E402


def test_collect_excludes_terminal_route_without_decision(
    tmp_path: Path,
) -> None:
    episode_dir = tmp_path / "episodes" / "01_M0_Task_seed1"
    episode_dir.mkdir(parents=True)
    episode = {
        "episode_id": "episode",
        "variant": "M0",
        "task_name": "Task",
        "task_goal": "Do the task.",
        "steps": [
            {
                "step": 0,
                "before_screenshot": "step_000_before.png",
                "decision": {
                    "decision_summary": "Use the memory.",
                    "action": {"type": "wait", "duration_ms": 1000},
                    "memory_citations": ["m_0001"],
                },
            }
        ],
    }
    (episode_dir / "episode.json").write_text(
        json.dumps(episode),
        encoding="utf-8",
    )
    item = {
        "memory_id": "m_0001",
        "memory_type": "episodic_fact",
        "verification_status": "observed",
        "content": {"natural_language": "The form is visible."},
        "source": {"screenshot_paths": ["step_000_before.png"]},
    }
    events = [
        {"event": "write", "item": item},
        {
            "event": "route",
            "event_index": 1,
            "step": 0,
            "memory_id": "m_0001",
            "route": "HYPOTHESIS",
            "score": 0.6,
            "reliability": 0.7,
        },
        {
            "event": "route",
            "event_index": 2,
            "step": 1,
            "memory_id": "m_0001",
            "route": "HYPOTHESIS",
            "score": 0.6,
            "reliability": 0.7,
        },
    ]
    (episode_dir / "memory_events.jsonl").write_text(
        "\n".join(json.dumps(event) for event in events),
        encoding="utf-8",
    )

    candidates = collect(tmp_path)
    assert len(candidates) == 1
    assert candidates[0]["step"] == 0
    assert candidates[0]["current_screenshot"] == "step_000_before.png"
