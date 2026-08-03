from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

import numpy as np

from raven_m.eest_ac.controller import EestAcController
from raven_m.env.androidworld_adapter import MappedAction
from raven_m.models.transformers_client import ModelCall


@dataclass
class FakeState:
    pixels: np.ndarray
    ui_elements: list[dict]


class FakeEnv:
    def __init__(self, states: list[FakeState]) -> None:
        self.states = states
        self.index = 0
        self.interaction_cache = None

    def reset(self, go_home=True):
        if go_home:
            self.index = 0

    def hide_automation_ui(self):
        return None

    def get_state(self, wait_to_stabilize=True):
        return self.states[self.index]


class FakeAdapter:
    def map_action(self, canonical, *, screen_width, screen_height):
        return MappedAction(
            canonical=dict(canonical),
            screen_size=(screen_width, screen_height),
            actual_pixels={},
            upstream_action=None,
        )

    def execute(self, env, mapped):
        if mapped.canonical["type"] == "answer":
            env.interaction_cache = mapped.canonical["text"]
        elif env.index + 1 < len(env.states):
            env.index += 1


class FakeTask:
    name = "HeldOutFakeTask"

    def __init__(self, goal: str) -> None:
        self.goal = goal
        self.params = {"instance": "blind"}

    def initialize_task(self, env):
        return None

    def is_successful(self, env):
        return 1.0 if env.index >= 1 else 0.0

    def tear_down(self, env):
        return None


class FakeClient:
    def __init__(self, responder) -> None:
        self.responder = responder
        self.counter = 0

    def generate(
        self,
        *,
        image_path: Path,
        system_prompt: str,
        user_prompt: str,
        episode_id: str,
        call_label: str,
        max_tokens: int,
        context_images=None,
    ) -> ModelCall:
        self.counter += 1
        content = self.responder(call_label, user_prompt)
        return ModelCall(
            call_id=f"call-{self.counter}",
            episode_id=episode_id,
            idempotency_key=f"key-{self.counter}",
            image_sha256=sha256(image_path.read_bytes()).hexdigest(),
            image_sha256s=(sha256(image_path.read_bytes()).hexdigest(),),
            prompt_sha256=sha256(user_prompt.encode()).hexdigest(),
            request_sha256=f"{self.counter:064x}",
            response_sha256=sha256(content.encode()).hexdigest(),
            content=content,
            usage={"prompt_tokens": 400, "completion_tokens": 80, "total_tokens": 480},
            raven_meta={},
        )


def _screen(*texts: str, value: int = 0) -> FakeState:
    return FakeState(
        pixels=np.full((64, 32, 3), value, dtype=np.uint8),
        ui_elements=[
            {
                "text": text,
                "package_name": "org.example.app",
                "class_name": "android.widget.TextView",
                "is_visible": True,
                "is_enabled": True,
            }
            for text in texts
        ],
    )


def _controller(client, arm: str) -> EestAcController:
    return EestAcController(
        client=client,
        executor_prompt="executor",
        summary_prompt="summary",
        risk_gate_prompt="risk",
        arm=arm,
        max_environment_actions=4,
        max_model_calls=8,
        adapter=FakeAdapter(),
    )


def test_m_slots_routes_cross_page_fact_without_auxiliary_call(tmp_path) -> None:
    decisions = {
        "executor_d000_initial": {
            "status": "continue",
            "action": {"type": "tap", "x": 0.5, "y": 0.5},
            "expected_outcome": "Morgan's conversation opens.",
            "decision_summary": "Open Morgan's conversation.",
            "observed_evidence": [
                {
                    "entity": "Avery",
                    "field": "event_address",
                    "value": "123 Main St",
                    "scope": "cross_page",
                    "relevance_tags": ["send", "Morgan"],
                }
            ],
            "evidence_citations": [],
        },
        "executor_d001_initial": {
            "status": "done",
            "action": None,
            "expected_outcome": "The requested operation is complete.",
            "decision_summary": "The task is complete.",
            "observed_evidence": [],
            "evidence_citations": [],
        },
    }
    client = FakeClient(lambda label, _: json.dumps(decisions[label]))
    env = FakeEnv(
        [
            _screen("Avery", "123 Main St"),
            _screen("Morgan", "Conversation"),
        ]
    )
    result = _controller(client, "M_SLOTS").run(
        env=env,
        task=FakeTask(
            "Text the address of the event to Morgan that Avery just sent me."
        ),
        episode_id="slots-replay",
        episode_dir=tmp_path / "slots",
        seed=1,
        study_id="unit",
    )
    assert result["task_success"]
    assert result["auxiliary_calls"] == 0
    evidence_id = result["evidence_ledger"][0]["evidence_id"]
    routed = result["steps"][1]["context"]["selected_evidence"]
    assert [item["evidence_id"] for item in routed] == [evidence_id]
    assert result["event_log_verified"]


def test_m_risk_gates_terminal_done_but_not_open_app(tmp_path) -> None:
    def respond(label: str, _: str) -> str:
        if label == "executor_d000_initial":
            value = {
                "status": "continue",
                "action": {"type": "open_app", "app_name": "camera"},
                "expected_outcome": "Camera opens.",
                "decision_summary": "Open the camera app.",
                "observed_evidence": [],
                "evidence_citations": ["task:root"],
            }
        elif label == "executor_d001_initial":
            value = {
                "status": "done",
                "action": None,
                "expected_outcome": "Camera is visibly open.",
                "decision_summary": "The task is done.",
                "observed_evidence": [],
                "evidence_citations": ["task:root"],
            }
        elif label == "risk_gate_d001":
            value = {
                "decision": "allow",
                "reason": "The target app is visible.",
                "required_evidence_ids": ["task:root"],
            }
        else:  # pragma: no cover - makes unexpected calls explicit
            raise AssertionError(label)
        return json.dumps(value)

    result = _controller(FakeClient(respond), "M_RISK").run(
        env=FakeEnv([_screen("Home"), _screen("Camera", value=20)]),
        task=FakeTask("Open the camera app."),
        episode_id="risk-negative",
        episode_dir=tmp_path / "risk",
        seed=1,
        study_id="unit",
    )
    assert result["task_success"]
    assert result["risk_gate_count"] == 1
    assert not result["steps"][0]["risk_trigger"]["eligible"]
    assert result["steps"][1]["risk_trigger"]["intent"] == "done"
    assert result["auxiliary_calls"] == 1


def test_b3_match_spends_useful_auxiliary_call_on_same_trigger(tmp_path) -> None:
    def respond(label: str, _: str) -> str:
        if label == "executor_d000_initial":
            return json.dumps(
                {
                    "status": "continue",
                    "action": {"type": "tap", "x": 0.9, "y": 0.9},
                    "expected_outcome": "The message is sent.",
                    "decision_summary": "Tap Send.",
                    "observed_evidence": [],
                    "evidence_citations": [],
                }
            )
        if label == "matched_summary_d000":
            return json.dumps({"summary": "The requested message is ready to send."})
        if label == "executor_d001_initial":
            return json.dumps(
                {
                    "status": "done",
                    "action": None,
                    "expected_outcome": "The sent conversation is visible.",
                    "decision_summary": "The task is done.",
                    "observed_evidence": [],
                    "evidence_citations": [],
                }
            )
        if label == "matched_summary_d001":
            return json.dumps({"summary": "The send transition completed."})
        raise AssertionError(label)

    result = _controller(FakeClient(respond), "B3_MATCH").run(
        env=FakeEnv([_screen("Draft", "Send"), _screen("Sent", value=40)]),
        task=FakeTask("Send the prepared message."),
        episode_id="matched",
        episode_dir=tmp_path / "matched",
        seed=1,
        study_id="unit",
    )
    assert result["task_success"]
    assert result["auxiliary_calls"] == 2
    assert result["ordinary_summary"] == "The send transition completed."
    assert all("neutral_padding" not in json.dumps(item) for item in result["steps"])
