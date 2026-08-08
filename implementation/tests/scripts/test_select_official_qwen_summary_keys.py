from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "select_official_qwen_summary_keys.py"
)


def test_selects_exact_key_and_drops_unfinished_siblings(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    output = tmp_path / "selected.json"
    source.write_text(
        json.dumps(
            {
                "in_progress_episode_ids": ["B_7_running"],
                "episodes": [
                    {"task_name": "A", "seed": 7, "success": False},
                    {"task_name": "B", "seed": 7, "success": True},
                ],
            }
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(source),
            str(output),
            "--key",
            "A:7",
            "--selection-reason",
            "fixture",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["selected_keys"] == ["A:7"]
    assert payload["in_progress_episode_ids"] == []
    assert payload["episodes"] == [
        {"task_name": "A", "seed": 7, "success": False}
    ]
