from pathlib import Path
import sys


SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from run_frozen_hard_suite import (  # noqa: E402
    EXPECTED_BACKEND,
    EXPECTED_REVISION,
    classify_infrastructure,
    load_formal_infrastructure_attempts,
    recovery_stdio_paths,
    wait_for_model_service,
)
from run_method_dev_suite import task_instance_hash  # noqa: E402
from run_protocol_v2_gate_e import (  # noqa: E402
    classify_gate_e_infrastructure,
)


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


def test_emulator_lifecycle_recovery_uses_file_backed_stdio(
    tmp_path: Path,
) -> None:
    stop_paths = recovery_stdio_paths(tmp_path, 1)
    start_paths = recovery_stdio_paths(tmp_path, 2)
    assert stop_paths == (
        tmp_path / "stop_emulator_stdout.log",
        tmp_path / "stop_emulator_stderr.log",
    )
    assert start_paths == (
        tmp_path / "start_emulator_stdout.log",
        tmp_path / "start_emulator_stderr.log",
    )
    assert recovery_stdio_paths(tmp_path, 3) is None


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
    visible_anr = {
        "error": {
            "type": "VisibleInfrastructureFailure",
            "message": (
                "INFRA_EMULATOR_ANR: "
                "Process system isn't responding"
            ),
        }
    }
    assert classify_infrastructure(adb_failure) == "INFRA_EMULATOR_LOST"
    assert classify_infrastructure(visible_anr) == "INFRA_EMULATOR_ANR"
    assert classify_infrastructure(method_failure) is None
    assert classify_infrastructure({"error": None}) is None


def test_gate_e_classifies_accessibility_tree_loss_as_emulator_loss() -> None:
    accessibility_loss = {
        "error": {
            "type": "RuntimeError",
            "message": "Could not get a11y tree.",
        }
    }
    method_failure = {
        "error": {
            "type": "RoleValidationError",
            "message": "planner response was invalid",
        }
    }
    assert classify_infrastructure(accessibility_loss) is None
    assert classify_gate_e_infrastructure(accessibility_loss) == (
        "INFRA_EMULATOR_LOST"
    )
    assert classify_gate_e_infrastructure(method_failure) is None
    assert classify_gate_e_infrastructure({"error": None}) is None


class RecoveringClient:
    def __init__(self) -> None:
        self.calls = 0

    def health(self) -> dict:
        self.calls += 1
        if self.calls < 3:
            raise ConnectionError("tunnel unavailable")
        return {
            "backend": EXPECTED_BACKEND,
            "revision": EXPECTED_REVISION,
        }


def test_model_recovery_waits_without_spending_episode_retry(
    tmp_path: Path,
) -> None:
    client = RecoveringClient()
    clock = iter([0.0, 0.0, 1.0, 2.0, 2.0])
    health = wait_for_model_service(
        client,
        recovery_dir=tmp_path,
        max_wait_seconds=10,
        poll_seconds=1,
        sleep_fn=lambda _: None,
        monotonic_fn=lambda: next(clock),
    )
    assert health["backend"] == EXPECTED_BACKEND
    assert client.calls == 3
    audit = (tmp_path / "model_service_recovery.json").read_text(
        encoding="utf-8"
    )
    assert '"status": "recovered"' in audit
    assert audit.count('"healthy": false') == 2


def test_model_recovery_rejects_backend_drift(tmp_path: Path) -> None:
    class DriftedClient:
        def health(self) -> dict:
            return {
                "backend": "different_backend",
                "revision": EXPECTED_REVISION,
            }

    try:
        wait_for_model_service(
            DriftedClient(),
            recovery_dir=tmp_path,
            max_wait_seconds=0,
            sleep_fn=lambda _: None,
        )
    except RuntimeError as exc:
        assert "differs from the frozen" in str(exc)
    else:
        raise AssertionError("Backend drift must fail immediately.")


def test_formal_attempt_state_resumes_without_resetting_cap(
    tmp_path: Path,
) -> None:
    path = tmp_path / "infrastructure_attempts.json"
    path.write_text(
        """{
  "schema_version": "formal_infrastructure_attempts.v1",
  "attempts": [
    {
      "attempt": 1,
      "goal_sha256": "goal",
      "params_sha256": "params",
      "code": "INFRA_MODEL_UNAVAILABLE"
    },
    {
      "attempt": 2,
      "goal_sha256": "goal",
      "params_sha256": "params",
      "code": "INFRA_EMULATOR_LOST"
    }
  ]
}
""",
        encoding="utf-8",
    )
    attempts, pair_hash = load_formal_infrastructure_attempts(path)
    assert len(attempts) == 2
    assert pair_hash == ("goal", "params")
    assert len(attempts) + 1 == 3


def test_formal_attempt_state_rejects_noncontiguous_history(
    tmp_path: Path,
) -> None:
    path = tmp_path / "infrastructure_attempts.json"
    path.write_text(
        """{
  "schema_version": "formal_infrastructure_attempts.v1",
  "attempts": [
    {
      "attempt": 2,
      "goal_sha256": "goal",
      "params_sha256": "params"
    }
  ]
}
""",
        encoding="utf-8",
    )
    try:
        load_formal_infrastructure_attempts(path)
    except RuntimeError as exc:
        assert "not contiguous" in str(exc)
    else:
        raise AssertionError("Noncontiguous attempts must be rejected.")
