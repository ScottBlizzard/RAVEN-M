"""No-model smoke test of protocol-v2 answer on a live AndroidWorld env."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import random


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(REPOSITORY_ROOT / "06_local_runtime/scripts"))

import androidworld_compat  # noqa: E402,F401
from android_env.proto import adb_pb2  # noqa: E402
from android_world.env import interface  # noqa: E402
from android_world.task_evals.information_retrieval import (  # noqa: E402
    proto_utils,
)
from android_world.task_evals.information_retrieval.information_retrieval_registry import (  # noqa: E402
    InformationRetrievalRegistry,
)
from raven_m.env.androidworld_adapter import AndroidWorldAdapter  # noqa: E402


class AdbOnlyController:
    """Minimal live-ADB controller for the answer branch's overlay intent."""

    def __init__(self, adb_path: str, serial: str) -> None:
        self.adb_path = adb_path
        self.serial = serial

    def execute_adb_call(self, request):
        args = list(request.generic.args)
        completed = subprocess.run(
            [self.adb_path, "-s", self.serial, *args],
            check=False,
            capture_output=True,
            timeout=20,
        )
        status = (
            adb_pb2.AdbResponse.Status.OK
            if completed.returncode == 0
            else adb_pb2.AdbResponse.Status.ADB_ERROR
        )
        return adb_pb2.AdbResponse(status=status)

    def press_home(self) -> None:
        subprocess.run(
            [
                self.adb_path,
                "-s",
                self.serial,
                "shell",
                "input",
                "keyevent",
                "HOME",
            ],
            check=True,
            capture_output=True,
            timeout=20,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--serial", default="emulator-5554")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT
        / "reports/protocol_v2_live_android_answer_smoke.json",
    )
    args = parser.parse_args()
    text = "protocol-v2-answer-smoke"
    result = {
        "schema_version": "protocol_v2_live_android_answer_smoke.v1",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "console_port": args.console_port,
        "serial": args.serial,
        "integration_mode": "AsyncAndroidEnv answer cache plus live ADB health",
        "model_calls": 0,
        "gpu_experiment": False,
    }
    env = None
    controller = AdbOnlyController(args.adb_path, args.serial)
    try:
        print("stage=connect_live_adb", flush=True)
        controller.press_home()
        env = interface.AsyncAndroidEnv(controller)  # type: ignore[arg-type]
        print("stage=pre_smoke_reset", flush=True)
        env.interaction_cache = ""
        print("stage=map_answer", flush=True)
        mapped = AndroidWorldAdapter().map_action(
            {
                "type": "answer",
                "text": text,
                "text_origin": "task_literal",
                "source_memory_ids": [],
            },
            screen_width=1080,
            screen_height=2400,
        )
        print("stage=execute_answer", flush=True)
        AndroidWorldAdapter().execute(env, mapped)
        print("stage=verify_cache", flush=True)
        initial_cache_matches = env.interaction_cache == text
        random.seed(20260726)
        task_class = InformationRetrievalRegistry().registry[
            "SportsTrackerActivitiesOnDate"
        ]
        task = task_class(task_class.generate_random_params())
        proto_utils.initialize_proto(task.task, task.params)
        task.initialized = True
        expected_answers = proto_utils.get_expected_answer(task.task)
        correct_answer = ", ".join(
            str(value) for value in expected_answers
        )
        isolation_cycles = []
        for cycle in range(3):
            env.interaction_cache = ""
            empty_score = float(task.is_successful(env))
            correct = AndroidWorldAdapter().map_action(
                {
                    "type": "answer",
                    "text": correct_answer,
                    "text_origin": "deterministic_calculation",
                    "source_memory_ids": [],
                },
                screen_width=1080,
                screen_height=2400,
            )
            AndroidWorldAdapter().execute(env, correct)
            correct_score = float(task.is_successful(env))
            env.interaction_cache = ""
            isolation_cycles.append(
                {
                    "cycle": cycle + 1,
                    "empty_score": empty_score,
                    "correct_score": correct_score,
                    "cache_empty_after_reset": not env.interaction_cache,
                }
            )
        wrong = AndroidWorldAdapter().map_action(
            {
                "type": "answer",
                "text": "__known_wrong_answer__",
                "text_origin": "task_literal",
                "source_memory_ids": [],
            },
            screen_width=1080,
            screen_height=2400,
        )
        AndroidWorldAdapter().execute(env, wrong)
        wrong_score = float(task.is_successful(env))
        env.interaction_cache = ""
        fixture_passed = bool(
            initial_cache_matches
            and all(
                item["empty_score"] == 0.0
                and item["correct_score"] == 1.0
                and item["cache_empty_after_reset"]
                for item in isolation_cycles
            )
            and wrong_score == 0.0
            and not env.interaction_cache
        )
        result.update(
            {
                "mapped_upstream_action": mapped.upstream_action,
                "initial_interaction_cache_matches": initial_cache_matches,
                "fixture_task": task.name,
                "expected_answer_count": len(expected_answers),
                "correct_answer_sha256": sha256(
                    correct_answer.encode("utf-8")
                ).hexdigest(),
                "isolation_cycles": isolation_cycles,
                "wrong_answer_score": wrong_score,
                "cache_empty_after_wrong_answer_reset": (
                    not env.interaction_cache
                ),
                "passed": fixture_passed,
            }
        )
    except Exception as exc:
        result.update(
            {
                "passed": False,
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            }
        )
    finally:
        if env is not None:
            try:
                print("stage=post_smoke_reset", flush=True)
                env.interaction_cache = ""
                controller.press_home()
                result["post_smoke_reset"] = True
            except Exception as exc:
                result["post_smoke_reset"] = False
                result["reset_error"] = {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("passed") and result.get("post_smoke_reset") else 1


if __name__ == "__main__":
    raise SystemExit(main())
