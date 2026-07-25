from pathlib import Path
import json
import sys


SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import run_frozen_hard_suite_hotfix_003 as hotfix  # noqa: E402


def test_attempt_04_requires_model_success_then_adb_failure(
    tmp_path: Path,
) -> None:
    path = tmp_path / "events.jsonl"
    events = [
        {
            "event": "episode_start",
            "episode_id": "suite_cell_a4",
        },
        {
            "event": "step",
            "model_calls": [
                {
                    "call_id": "call",
                    "raven_meta": {
                        "backend_id": hotfix.frozen.EXPECTED_BACKEND,
                        "latency_seconds": 8.0,
                    },
                }
            ],
            "execution_error": {"type": "AdbControllerError"},
        },
        {
            "event": "episode_error",
            "error": {"type": "AdbControllerError"},
        },
    ]
    path.write_text(
        "\n".join(json.dumps(event) for event in events) + "\n",
        encoding="utf-8",
    )
    evidence = hotfix.validate_attempt_04_emulator_failure(path)
    assert evidence["episode_id"] == "suite_cell_a4"
    assert evidence["model_call_id"] == "call"


def test_smoke_gate_checks_registry_and_screen(tmp_path: Path) -> None:
    path = tmp_path / "smoke.json"
    path.write_text(
        json.dumps(
            {
                "status": "ok",
                "registered_android_world_tasks": 116,
                "screen_shape": [2400, 1080, 3],
            }
        ),
        encoding="utf-8",
    )
    assert hotfix.validate_cold_restart_smoke(path)["status"] == "ok"
