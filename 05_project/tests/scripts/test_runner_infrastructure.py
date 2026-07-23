from pathlib import Path
import sys


SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from run_frozen_hard_suite import classify_infrastructure  # noqa: E402
from run_method_dev_suite import task_instance_hash  # noqa: E402


class DummyTask:
    def __init__(self, goal: str, params: dict) -> None:
        self.goal = goal
        self.params = params


def test_task_instance_hash_is_stable_and_sensitive() -> None:
    first = task_instance_hash(DummyTask("goal", {"b": 2, "a": 1}))
    reordered = task_instance_hash(DummyTask("goal", {"a": 1, "b": 2}))
    changed = task_instance_hash(DummyTask("goal", {"a": 1, "b": 3}))
    assert first == reordered
    assert first != changed


def test_only_classified_infrastructure_is_retriable() -> None:
    adb_failure = {
        "error": {
            "type": "AdbControllerError",
            "message": "adb shell input text timed out",
        }
    }
    method_failure = {
        "error": {
            "type": "RoleValidationError",
            "message": "planner response was invalid",
        }
    }
    assert classify_infrastructure(adb_failure) == "INFRA_EMULATOR_LOST"
    assert classify_infrastructure(method_failure) is None
    assert classify_infrastructure({"error": None}) is None
