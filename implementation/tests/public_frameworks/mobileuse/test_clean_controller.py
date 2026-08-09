from collections import Counter
from hashlib import sha256
import sys
from types import ModuleType

import numpy as np

# The vendored package imports its standalone ADB environment from
# ``mobile_use.__init__`` even though these controller tests inject FakeEnv.
sys.modules.setdefault("adbutils", ModuleType("adbutils"))
if "skimage.metrics" not in sys.modules:
    skimage = ModuleType("skimage")
    metrics = ModuleType("skimage.metrics")
    metrics.structural_similarity = lambda left, right: float(
        np.array_equal(left, right)
    )
    skimage.metrics = metrics
    sys.modules["skimage"] = skimage
    sys.modules["skimage.metrics"] = metrics
if "pyregister" not in sys.modules:
    pyregister = ModuleType("pyregister")

    class Registrable:
        _registry = {}

        @classmethod
        def register(cls, name):
            def decorator(target):
                cls._registry[name] = target
                return target

            return decorator

    pyregister.Registrable = Registrable
    sys.modules["pyregister"] = pyregister

from raven_m.models.transformers_client import ModelCall
from raven_m.public_frameworks.mobileuse.clean_controller import (
    ARM_ID,
    CleanMobileUseController,
)


CLICK = (
    'Thought: tap.\nAction: tap.\n<tool_call>\n'
    '{"name": "mobile_use", "arguments": {"action": "click", "coordinate": [500, 500]}}\n'
    '</tool_call>'
)
FINISH = (
    'Thought: done.\nAction: finish.\n<tool_call>\n'
    '{"name": "mobile_use", "arguments": {"action": "terminate", "status": "success"}}\n'
    '</tool_call>'
)
ANSWER = (
    'Thought: answer.\nAction: answer.\n<tool_call>\n'
    '{"name": "mobile_use", "arguments": {"action": "answer", "text": "done"}}\n'
    '</tool_call>'
)


class FakeClient:
    model_id = "Qwen/Qwen3-VL-32B-Instruct"
    model_revision = "revision"
    backend_id = "fake"
    base_url = "http://127.0.0.1:18000"

    def __init__(self, operator_outputs, *, global_outputs=None):
        self.calls = []
        self.outputs = {
            "Operator": list(operator_outputs),
            "Reflector": [
                "### Outcome ###\nA\n### Error Description ###\nNone\n### Explanation ###\nok"
            ] * 20,
            "Progressor": ["### Completed contents ###\nObserved action"] * 20,
            "TrajectoryReflector": [
                "### Outcome ###\nA\n### Error Description ###\nNone\n### Explanation ###\nok"
            ] * 20,
            "AnswerAgent": [ANSWER] * 10,
            "GlobalReflector": list(global_outputs or [
                "### Result ###\nSuccess\n### Reason ###\nVisible completion"
            ] * 10),
        }

    def generate_messages(
        self, *, messages, episode_id, call_label, role, expected_images, max_tokens
    ):
        self.calls.append(role)
        content = self.outputs[role].pop(0)
        digest = sha256(content.encode()).hexdigest()
        return ModelCall(
            call_id=call_label,
            episode_id=episode_id,
            idempotency_key=call_label,
            image_sha256="",
            image_sha256s=(),
            prompt_sha256=digest,
            request_sha256=digest,
            response_sha256=digest,
            content=content,
            usage={},
            raven_meta={"role": role},
        )


class FakeState:
    def __init__(self, value):
        self.pixels = np.full((100, 100, 3), value, dtype=np.uint8)
        self.ui_elements = []


class FakeEnv:
    def __init__(self, *, fail_first_action=False):
        self.actions = []
        self.interaction_cache = None
        self.controller = object()
        self.value = 0
        self.fail_first_action = fail_first_action

    def get_state(self, wait_to_stabilize=True):
        return FakeState(self.value)

    def execute_action(self, action):
        if self.fail_first_action:
            self.fail_first_action = False
            raise RuntimeError("synthetic execution failure")
        self.actions.append(action)
        self.value += 1


def make_controller(client, env, tmp_path, *, episode_id, max_steps):
    controller = CleanMobileUseController(
        client,
        env=env,
        episode_id=episode_id,
        episode_dir=tmp_path,
        max_steps=max_steps,
    )
    execute = lambda target_env, action: target_env.execute_action(action)
    controller.bridge.android_adapter.execute = execute
    controller.android_adapter.execute = execute
    return controller


def test_clean_schedule_reduces_auxiliary_generation(tmp_path):
    client = FakeClient([CLICK, CLICK, CLICK, CLICK, FINISH])
    controller = make_controller(
        client, FakeEnv(), tmp_path, episode_id="schedule", max_steps=5
    )
    result = controller.run("Tap four times, then finish")
    counts = Counter(client.calls)
    assert counts["Operator"] == 5
    assert counts["Reflector"] == 2
    assert counts["Progressor"] == 2
    assert counts["GlobalReflector"] == 1
    assert result.native_actions == 4
    events = result.log_path.read_text(encoding="utf-8")
    assert f'"arm_id": "{ARM_ID}"' in events
    assert '"generate": false' in events


def test_parser_exhaustion_is_valid_fail_closed_not_empty_action(tmp_path):
    client = FakeClient(["invalid one", "invalid two", "invalid three"])
    controller = make_controller(
        client, FakeEnv(), tmp_path, episode_id="parse-fail-closed", max_steps=2
    )
    result = controller.run("fixture")
    assert Counter(client.calls)["Operator"] == 3
    assert result.episode_data.status.name == "FAILED"
    assert result.episode_data.trajectory[-1].action.name == "terminate"
    assert "operator_fail_closed" in result.log_path.read_text(encoding="utf-8")


def test_detector_ignores_prior_execution_failure_without_crashing(tmp_path):
    client = FakeClient([CLICK, CLICK, CLICK])
    controller = make_controller(
        client,
        FakeEnv(fail_first_action=True),
        tmp_path,
        episode_id="safe-detector",
        max_steps=3,
    )
    result = controller.run("fixture")
    assert result.episode_data.num_steps == 3
    assert "trajectory_detector_omitted_invalid_steps" in result.log_path.read_text(
        encoding="utf-8"
    )


def test_uncertain_completion_is_vetoed_twice_then_bounded(tmp_path):
    uncertain = "### Result ###\nUncertain\n### Reason ###\nNot visibly verified"
    client = FakeClient(
        [CLICK, FINISH, FINISH, FINISH],
        global_outputs=[uncertain, uncertain],
    )
    controller = make_controller(
        client, FakeEnv(), tmp_path, episode_id="uncertain-veto", max_steps=4
    )
    result = controller.run("fixture")
    counts = Counter(client.calls)
    assert counts["GlobalReflector"] == 2
    assert result.episode_data.status.name == "FINISHED"
    events = result.log_path.read_text(encoding="utf-8")
    assert events.count("completion_uncertain_veto") == 2
    assert events.count("completion_recheck_armed") == 1
