"""Zero-model, zero-device evaluator-readable answer fixtures for H17-H19."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import random
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "03_code/third_party/android_world"))
sys.path.insert(0, str(REPO_ROOT / "06_local_runtime/scripts"))

try:
    import androidworld_compat  # noqa: F401
except ImportError:
    pass

from android_world.task_evals.information_retrieval import proto_utils  # noqa: E402
from android_world.task_evals.information_retrieval.information_retrieval_registry import InformationRetrievalRegistry  # noqa: E402
from raven_m.multi_framework_benchmark.androidworld_adapter import write_answer_contract  # noqa: E402


TASKS = (
    "SportsTrackerActivitiesOnDate",
    "SportsTrackerTotalDistanceForCategoryOverInterval",
    "SportsTrackerTotalDurationForCategoryThisWeek",
)


class OfflineEnv:
    interaction_cache = ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "artifacts/multi_framework_benchmark/s0_v0_2/answer_fixtures.json")
    args = parser.parse_args()
    registry = InformationRetrievalRegistry().registry
    rows = []
    for task_index, name in enumerate(TASKS):
        seed = 2026080600 + task_index
        random.seed(seed)
        task_class = registry[name]
        task = task_class(task_class.generate_random_params())
        proto_utils.initialize_proto(task.task, task.params)
        task.initialized = True
        expected = proto_utils.get_expected_answer(task.task)
        answer = ", ".join(str(value) for value in expected)
        env = OfflineEnv()
        empty_score = float(task.is_successful(env))
        write_answer_contract(env, answer)
        correct_score = float(task.is_successful(env))
        write_answer_contract(env, "__known_wrong_answer__")
        try:
            wrong_score = float(task.is_successful(env))
        except ValueError:
            wrong_score = 0.0
        rows.append({
            "task_class": name,
            "seed": seed,
            "expected_answer_sha256": sha256(answer.encode("utf-8")).hexdigest(),
            "empty_score": empty_score,
            "correct_score": correct_score,
            "wrong_score": wrong_score,
            "passed": empty_score == 0.0 and correct_score == 1.0 and wrong_score == 0.0,
        })
    result = {
        "schema_version": "multi_framework_answer_fixture.v0.2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model_calls": 0,
        "android_actions": 0,
        "tasks": rows,
        "passed": len(rows) == 3 and all(row["passed"] for row in rows),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
