from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from raven_m.controller.episode_controller import EpisodeController
from raven_m.controller.protocol_v2_guard import ProtocolV2DecisionGuard
from raven_m.history.policies import HistoryPolicy
from raven_m.models.transformers_client import ModelCall


class AnswerClient:
    def generate(self, **kwargs) -> ModelCall:
        decision = {
            "status": "done",
            "action": {
                "type": "answer",
                "text": "Running, Cycling",
                "text_origin": "current_screen",
                "source_memory_ids": [],
            },
            "expected_outcome": "The answer is submitted.",
            "decision_summary": "Submit the visible activities.",
            "state_delta": [],
            "memory_citations": [],
        }
        content = json.dumps(decision)
        label = kwargs["call_label"]
        return ModelCall(
            call_id=label,
            episode_id=kwargs["episode_id"],
            idempotency_key=label,
            image_sha256="0" * 64,
            image_sha256s=("0" * 64,),
            prompt_sha256=label,
            request_sha256=label,
            response_sha256=label,
            content=content,
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class AnswerEnv:
    def __init__(self) -> None:
        self.interaction_cache = ""
        self.reset_count = 0

    def reset(self, go_home: bool) -> None:
        assert go_home
        self.reset_count += 1
        if self.reset_count == 1:
            self.interaction_cache = ""

    def hide_automation_ui(self) -> None:
        pass

    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        return SimpleNamespace(
            pixels=np.zeros((32, 24, 3), dtype=np.uint8)
        )

    def execute_action(self, action) -> None:
        assert action.action_type == "answer"
        self.interaction_cache = action.text


class AnswerTask:
    name = "SportsTrackerActivitiesOnDate"
    goal = "What activities were recorded on the requested date?"
    params = {}

    def initialize_task(self, env) -> None:
        del env

    def is_successful(self, env) -> float:
        return float(env.interaction_cache == "Running, Cycling")

    def tear_down(self, env) -> None:
        del env


def model_call(kwargs: dict, content: str) -> ModelCall:
    label = kwargs["call_label"]
    return ModelCall(
        call_id=label,
        episode_id=kwargs["episode_id"],
        idempotency_key=label,
        image_sha256="0" * 64,
        image_sha256s=("0" * 64,),
        prompt_sha256=label,
        request_sha256=label,
        response_sha256=label,
        content=content,
        usage={
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 2,
        },
        raven_meta={},
    )


class VisualSourceClient:
    def __init__(self, *, verdict: str) -> None:
        self.verdict = verdict
        self.requests: list[dict] = []

    def generate(self, **kwargs) -> ModelCall:
        self.requests.append(kwargs)
        label = kwargs["call_label"]
        if label.startswith("critic_step_"):
            content = json.dumps(
                {
                    "schema_version": "critic.v1",
                    "verdict": self.verdict,
                    "issue": (
                        ""
                        if self.verdict == "proceed"
                        else "The exact title is not sufficiently verified."
                    ),
                    "recommended_constraint": (
                        "Open the event detail and re-observe the full title."
                    ),
                    "memory_ids": [],
                }
            )
            return model_call(kwargs, content)
        if label.endswith("_repair"):
            content = json.dumps(
                {
                    "status": "continue",
                    "action": {"type": "tap", "x": 0.5, "y": 0.5},
                    "expected_outcome": "The event detail opens.",
                    "decision_summary": "Open the visible event detail.",
                    "state_delta": [],
                    "memory_citations": [],
                }
            )
            return model_call(kwargs, content)
        content = json.dumps(
            {
                "status": "done",
                "action": {
                    "type": "answer",
                    "text": "Board meeting",
                    "text_origin": "current_screen",
                    "source_memory_ids": [],
                },
                "expected_outcome": "The visible event title is returned.",
                "decision_summary": "Return the fully visible event title.",
                "state_delta": [],
                "memory_citations": [],
            }
        )
        return model_call(kwargs, content)


class VisualSourceEnv:
    def __init__(self) -> None:
        self.interaction_cache = ""
        self.executed_actions: list[str] = []

    def reset(self, go_home: bool) -> None:
        assert go_home
        self.interaction_cache = ""

    def hide_automation_ui(self) -> None:
        pass

    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        return SimpleNamespace(
            pixels=np.zeros((32, 24, 3), dtype=np.uint8),
            ui_elements=[
                {
                    "text": "October 25 (Wed)",
                    "is_visible": True,
                },
                {
                    "text": "16:00 - 16:05",
                    "is_visible": True,
                },
            ],
        )

    def execute_action(self, action) -> None:
        self.executed_actions.append(action.action_type)
        if action.action_type == "answer":
            self.interaction_cache = action.text


class VisualSourceTask:
    name = "SimpleCalendarEventsOnDate"
    goal = "What events do I have October 25 2023? Answer with titles only."
    params = {}

    def initialize_task(self, env) -> None:
        del env

    def is_successful(self, env) -> float:
        return float(env.interaction_cache == "Board meeting")

    def tear_down(self, env) -> None:
        del env


class GoalMutatingVisualSourceTask(VisualSourceTask):
    goal = (
        "What events do I have October 25 2023? "
        "Answer with titles only."
    )

    def initialize_task(self, env) -> None:
        del env
        self.goal = (
            "What events do I have the Wednesday after next? "
            "Answer with titles only."
        )


def test_controller_executes_answer_before_native_evaluator(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    controller = EpisodeController(
        client=AnswerClient(),  # type: ignore[arg-type]
        system_prompt="v2",
        max_steps=2,
        max_model_calls=2,
        history_policy=HistoryPolicy(),
        action_schema_path=root / "schemas/action.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
    )
    summary = controller.run(
        env=AnswerEnv(),
        task=AnswerTask(),
        episode_id="answer-v2",
        episode_dir=tmp_path / "episode",
        seed=1,
        protocol="androidworld_protocol_v2_exploratory",
    )
    assert summary["success"]
    assert summary["termination_reason"] == "model_answer"
    assert summary["executed_action_count"] == 1
    assert summary["steps"][0]["answer_audit"][
        "interaction_cache_matches_answer"
    ]
    assert "evaluator" not in summary["steps"][0]["user_prompt"].lower()
    events = (
        (tmp_path / "episode/events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    answer_event = next(
        index
        for index, line in enumerate(events)
        if '"answer_audit"' in line
    )
    evaluator_event = next(
        index
        for index, line in enumerate(events)
        if '"event": "evaluator_result"' in line
    )
    assert answer_event < evaluator_event
    assert summary["failure_code"] is None


def test_v22_freezes_task_goal_before_initialize_task(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    client = VisualSourceClient(verdict="proceed")
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2",
        max_steps=1,
        max_model_calls=3,
        history_policy=HistoryPolicy(),
        action_schema_path=root / "schemas/action.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
        visual_source_critic_prompt="critic",
    )
    episode_dir = tmp_path / "canonical-goal"
    summary = controller.run(
        env=VisualSourceEnv(),
        task=GoalMutatingVisualSourceTask(),
        episode_id="canonical-goal-v22",
        episode_dir=episode_dir,
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
    )

    absolute_goal = (
        "What events do I have October 25 2023? "
        "Answer with titles only."
    )
    relative_goal = (
        "What events do I have the Wednesday after next? "
        "Answer with titles only."
    )
    executor_request = next(
        request
        for request in client.requests
        if not request["call_label"].startswith("critic_step_")
    )
    assert f"TASK: {absolute_goal}" in executor_request["user_prompt"]
    assert relative_goal not in executor_request["user_prompt"]
    assert summary["task_goal"] == absolute_goal

    events = [
        json.loads(line)
        for line in (episode_dir / "events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    initialized = next(
        event for event in events if event["event"] == "task_initialized"
    )
    assert initialized["task_goal_before_initialization"] == absolute_goal
    assert initialized["task_goal_after_initialization"] == relative_goal
    assert initialized["task_goal_changed"] is True
    assert initialized["effective_task_goal"] == absolute_goal


def test_v22_visual_source_critic_accepts_pixel_visible_answer(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    client = VisualSourceClient(verdict="proceed")
    env = VisualSourceEnv()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2",
        max_steps=1,
        max_model_calls=3,
        history_policy=HistoryPolicy(),
        action_schema_path=root / "schemas/action.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
        visual_source_critic_prompt="critic",
    )
    summary = controller.run(
        env=env,
        task=VisualSourceTask(),
        episode_id="visual-source-accept-v22",
        episode_dir=tmp_path / "accept",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
    )
    assert summary["success"]
    assert env.executed_actions == []
    assert summary["steps"][0]["answer_audit"][
        "interaction_cache_matches_answer"
    ]
    assert summary["model_call_count"] == 2
    assert summary["executor_model_call_count"] == 1
    assert summary["history_model_call_count"] == 1
    parse = summary["steps"][0]["parse"]
    adjudications = parse["completion_adjudications"]
    assert len(adjudications) == 1
    assert adjudications[0]["schema_version"] == (
        "visual_text_source_adjudication.v1"
    )
    assert adjudications[0]["accepted"] is True
    critic_request = next(
        request
        for request in client.requests
        if request["call_label"].startswith("critic_step_")
    )
    payload = json.loads(critic_request["user_prompt"])
    assert payload["trigger"] == "current_screen_text_source_candidate"
    assert payload["answer_candidate"]["text"] == "Board meeting"
    assert payload["accessibility_source_assessment"][
        "source_value_count"
    ] == 2
    assert "source_values" not in payload["accessibility_source_assessment"]


def test_v22_visual_source_rejection_repairs_to_reversible_action(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    client = VisualSourceClient(verdict="reject_completion")
    env = VisualSourceEnv()
    controller = EpisodeController(
        client=client,  # type: ignore[arg-type]
        system_prompt="v2",
        max_steps=1,
        max_model_calls=3,
        history_policy=HistoryPolicy(),
        action_schema_path=root / "schemas/action.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
        protocol_v2_2=True,
        visual_source_critic_prompt="critic",
    )
    summary = controller.run(
        env=env,
        task=VisualSourceTask(),
        episode_id="visual-source-reject-v22",
        episode_dir=tmp_path / "reject",
        seed=1,
        protocol="androidworld_protocol_v2_2_exploratory",
    )
    assert not summary["success"]
    assert env.executed_actions == ["click"]
    assert summary["model_call_count"] == 3
    assert summary["executor_model_call_count"] == 2
    assert summary["history_model_call_count"] == 1
    step = summary["steps"][0]
    assert step["decision"]["status"] == "continue"
    assert step["decision"]["action"]["type"] == "tap"
    assert "VISUAL_SOURCE_ADJUDICATION_REJECTED" in step["parse"][
        "initial_validation_error"
    ]
    repair_request = next(
        request
        for request in client.requests
        if request["call_label"].endswith("_repair")
    )
    assert "do not repeat the candidate" in repair_request[
        "user_prompt"
    ]
    assert len(step["parse"]["completion_adjudications"]) == 1
    assert step["parse"]["completion_adjudications"][0][
        "accepted"
    ] is False
