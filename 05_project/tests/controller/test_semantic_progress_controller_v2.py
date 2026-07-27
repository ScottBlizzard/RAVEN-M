from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from raven_m.controller.episode_controller import EpisodeController
from raven_m.controller.protocol_v2_guard import ProtocolV2DecisionGuard
from raven_m.history.policies import RavenMemoryPolicy
from raven_m.models.transformers_client import ModelCall


class RepeatingSaveClient:
    def generate(self, **kwargs) -> ModelCall:
        decision = {
            "status": "continue",
            "action": {"type": "tap", "x": 0.94, "y": 0.085},
            "expected_outcome": "The event is saved.",
            "decision_summary": "Tap save.",
            "state_delta": [],
            "memory_citations": [],
            "completion_evidence": [],
        }
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
            content=json.dumps(decision),
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
            },
            raven_meta={},
        )


class SemanticFailureEnv:
    def __init__(self) -> None:
        self.state_call_count = 0
        self.execute_count = 0

    def reset(self, go_home: bool) -> None:
        assert go_home

    def hide_automation_ui(self) -> None:
        pass

    def get_state(self, wait_to_stabilize: bool):
        assert wait_to_stabilize
        self.state_call_count += 1
        elements = [
            SimpleNamespace(
                package_name="calendar",
                text="Meeting with Marketing",
                resource_id="title",
            ),
            SimpleNamespace(
                package_name="calendar",
                text="08:00",
                resource_id="start_time",
            ),
            SimpleNamespace(
                package_name="calendar",
                text="00:30",
                resource_id="end_time",
            ),
            SimpleNamespace(
                package_name="com.android.systemui",
                text=f"15:{40 + self.state_call_count}",
            ),
        ]
        if self.state_call_count == 2:
            elements.append(
                SimpleNamespace(
                    package_name="calendar",
                    text="The event cannot end earlier than it starts",
                    class_name="android.widget.Toast",
                )
            )
        return SimpleNamespace(
            pixels=np.full(
                (32, 24, 3),
                self.state_call_count,
                dtype=np.uint8,
            ),
            ui_elements=elements,
        )

    def execute_action(self, action) -> None:
        assert action.action_type == "click"
        self.execute_count += 1


class CalendarTask:
    name = "SimpleCalendarAddOneEvent"
    goal = "Create the requested calendar event."
    params = {}

    def initialize_task(self, env) -> None:
        del env

    def is_successful(self, env) -> float:
        del env
        return 0.0

    def tear_down(self, env) -> None:
        del env


def test_controller_routes_visible_failure_and_blocks_repeat(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[2]
    env = SemanticFailureEnv()
    controller = EpisodeController(
        client=RepeatingSaveClient(),  # type: ignore[arg-type]
        system_prompt="v2.1",
        max_steps=4,
        max_model_calls=4,
        history_policy=RavenMemoryPolicy(),
        action_schema_path=root / "schemas/action.raven.v2.schema.json",
        decision_guard=ProtocolV2DecisionGuard(),
        protocol_v2=True,
    )
    episode_dir = tmp_path / "episode"
    summary = controller.run(
        env=env,
        task=CalendarTask(),
        episode_id="semantic-failure-v2-1",
        episode_dir=episode_dir,
        seed=1,
        protocol="androidworld_protocol_v2_1_exploratory",
        variant="M0",
    )
    assert env.execute_count == 1
    assert summary["termination_reason"] == (
        "model_output_invalid_after_repair"
    )
    assert summary["failure_code"] == "MODEL_OUTPUT_INVALID_AFTER_REPAIR"
    first = summary["steps"][0]
    assert first["screenshot_changed"]
    assert not first["protocol_v2_guard"]["semantic_changed"]
    assert first["protocol_v2_guard"]["new_visible_failures"] == [
        "The event cannot end earlier than it starts"
    ]
    assert first["history_update"]["details"]["visible_failure_texts"] == [
        "The event cannot end earlier than it starts"
    ]
    memory_events = [
        json.loads(line)
        for line in (episode_dir / "memory_events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    failure_writes = [
        event
        for event in memory_events
        if event.get("event") == "write"
        and event.get("item", {}).get("memory_type") == "failure"
    ]
    assert len(failure_writes) == 1
