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
