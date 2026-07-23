from pathlib import Path

from raven_m.controller.episode_controller import EpisodeController
from raven_m.history.policies import HistoryPolicy


class UnusedClient:
    pass


class FakeEnv:
    def reset(self, go_home: bool) -> None:
        assert go_home

    def hide_automation_ui(self) -> None:
        pass


class FakeTask:
    name = "NonHardFixture"
    goal = "Do nothing."
    params = {}

    def initialize_task(self, env) -> None:
        del env

    def is_successful(self, env) -> float:
        del env
        return 0.0

    def tear_down(self, env) -> None:
        del env


def test_call_budget_exhaustion_is_scored_agent_failure(
    tmp_path: Path,
) -> None:
    controller = EpisodeController(
        client=UnusedClient(),  # type: ignore[arg-type]
        system_prompt="unused",
        max_steps=2,
        max_model_calls=0,
        history_policy=HistoryPolicy(),
    )
    summary = controller.run(
        env=FakeEnv(),
        task=FakeTask(),
        episode_id="budget-fixture",
        episode_dir=tmp_path / "episode",
        seed=1,
    )
    assert summary["error"] is None
    assert summary["termination_reason"] == "model_call_budget_exhausted"
    assert summary["failure_code"] == "MODEL_CALL_BUDGET_EXHAUSTED"
    assert summary["model_call_count"] == 0
