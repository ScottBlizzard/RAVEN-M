from hashlib import sha256
from types import SimpleNamespace

import numpy as np

from raven_m.models.transformers_client import ModelCall
from raven_m.public_frameworks.mobileuse.controller import MobileUseController


class FakeClient:
    model_id = "Qwen/Qwen3-VL-32B-Instruct"
    model_revision = "revision"
    backend_id = "fake"
    base_url = "http://127.0.0.1:18000"

    def __init__(self):
        self.calls = []
        self.outputs = {
            "Operator": [
                'Thought: tap.\nAction: tap center.\n<tool_call>\n{"name": "mobile_use", "arguments": {"action": "click", "coordinate": [500, 500]}}\n</tool_call>',
                'Thought: done.\nAction: finish.\n<tool_call>\n{"name": "mobile_use", "arguments": {"action": "terminate", "status": "success"}}\n</tool_call>',
            ],
            "Reflector": ["### Outcome ###\nA\n### Error Description ###\nNone\n### Explanation ###\nok"],
            "Progressor": ["### Completed contents ###\nTapped center"],
            "AnswerAgent": ['Thought: answer.\nAction: answer.\n<tool_call>\n{"name": "mobile_use", "arguments": {"action": "answer", "text": "done"}}\n</tool_call>'],
            "GlobalReflector": ["### Result ###\nPassed\n### Reason ###\nVisible completion"],
            "TrajectoryReflector": [],
        }

    def generate_messages(self, *, messages, episode_id, call_label, role, expected_images, max_tokens):
        self.calls.append(role)
        content = self.outputs[role].pop(0)
        digest = sha256(content.encode()).hexdigest()
        return ModelCall(
            call_id=call_label, episode_id=episode_id, idempotency_key=call_label,
            image_sha256="", image_sha256s=(), prompt_sha256=digest,
            request_sha256=digest, response_sha256=digest, content=content,
            usage={}, raven_meta={"role": role},
        )


class FakeState:
    def __init__(self):
        self.pixels = np.zeros((100, 100, 3), dtype=np.uint8)
        self.ui_elements = []


class FakeEnv:
    def __init__(self):
        self.actions = []
        self.interaction_cache = None
        self.controller = object()

    def get_state(self, wait_to_stabilize=True):
        return FakeState()

    def execute_action(self, action):
        self.actions.append(action)


def test_upstream_schedule_one_action_then_finish(tmp_path):
    client = FakeClient()
    env = FakeEnv()
    controller = MobileUseController(
        client, env=env, episode_id="fixture", episode_dir=tmp_path,
        max_steps=3,
    )
    result = controller.run("Tap the center, then finish")
    assert client.calls == [
        "Operator", "Reflector", "Progressor", "Operator",
        "AnswerAgent", "GlobalReflector",
    ]
    assert len(env.actions) == 1
    assert result.native_actions == 1
    assert env.interaction_cache == "done"


def test_three_invalid_operator_outputs_do_not_trigger_unused_fourth_call(tmp_path):
    client = FakeClient()
    client.outputs["Operator"] = ["invalid one", "invalid two", "invalid three"]
    env = FakeEnv()
    controller = MobileUseController(
        client, env=env, episode_id="invalid", episode_dir=tmp_path,
        max_steps=1,
    )
    result = controller.run("fixture")
    assert client.calls == ["Operator", "Operator", "Operator"]
    assert result.native_actions == 0
    assert env.actions == []
