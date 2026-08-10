from pathlib import Path
from types import SimpleNamespace

import numpy as np

from raven_m.models.transformers_client import ModelCall
from raven_m.official_qwen_mobile.controller import OfficialQwenMobileController
from raven_m.official_qwen_mobile.protocol import build_user_prompt
from raven_m.official_qwen_mobile.working_memory import (
    ActionWorkingMemory,
    append_working_memory,
)


def test_memory_write_read_is_bounded_and_auditable() -> None:
    memory = ActionWorkingMemory(max_items=2, max_chars=1000)
    missing = memory.write(
        source_step=0,
        action_summary="Tap the visible target.",
        source_call_id="c0",
        source_response_sha256="r0",
        source_screenshot_sha256="s0",
    )
    assert missing == {
        "written": False,
        "reason": "memory_prefix_missing_or_empty",
        "source_step": 0,
    }

    first = memory.write(
        source_step=1,
        action_summary=(
            "MEMORY[observed=CANARY-4721; verified=source opened; "
            "pending=enter value] | Tap the destination field."
        ),
        source_call_id="c1",
        source_response_sha256="r1",
        source_screenshot_sha256="s1",
    )
    assert first["written"] is True
    rendered, audit = memory.read()
    assert "CANARY-4721" in rendered
    assert audit["retrieved_ids"] == [first["record"]["memory_id"]]
    assert audit["nonempty"] is True
    assert memory.audit_record()["active"] is True


def test_empty_memory_does_not_change_official_user_prompt() -> None:
    baseline = "official prompt\n"
    assert append_working_memory(baseline, "") == baseline


class _Client:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(self, **kwargs) -> ModelCall:
        self.prompts.append(kwargs["user_prompt"])
        call_index = len(self.prompts)
        if call_index == 1:
            content = (
                "Thought: preserve the visible value before moving.\n"
                "Action: MEMORY[observed=CANARY-4721; verified=none; "
                "pending=finish the task] | Tap the visible control.\n"
                "<tool_call>\n"
                '{"name":"mobile_use","arguments":{"action":"click",'
                '"coordinate":[500,500]}}\n'
                "</tool_call>"
            )
        else:
            content = (
                "Thought: the prior value is available in working memory.\n"
                "Action: MEMORY[observed=none; verified=none; pending=none] | "
                "Finish the task.\n"
                "<tool_call>\n"
                '{"name":"mobile_use","arguments":{"action":"terminate",'
                '"status":"success"}}\n'
                "</tool_call>"
            )
        return ModelCall(
            call_id=f"call-{call_index}",
            episode_id="episode",
            idempotency_key=f"key-{call_index}",
            image_sha256="image",
            image_sha256s=("image",),
            prompt_sha256=f"prompt-{call_index}",
            request_sha256=f"request-{call_index}",
            response_sha256=f"response-{call_index}",
            content=content,
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            raven_meta={"latency_seconds": 0.1, "transport_attempts": 1},
        )


class _Mapped:
    def audit_record(self):
        return {
            "canonical": {"type": "tap", "x": 0.5, "y": 0.5},
            "screen_size": [10, 20],
            "actual_pixels": {"x": 5, "y": 10},
            "upstream_action": {"action_type": "click", "x": 5, "y": 10},
        }


class _Adapter:
    def map_action(self, action, *, screen_width, screen_height):
        del action, screen_width, screen_height
        return _Mapped()

    def execute(self, env, mapped) -> None:
        del env, mapped


class _Env:
    def __init__(self) -> None:
        self.capture_count = 0

    def reset(self, *, go_home: bool) -> None:
        assert go_home

    def hide_automation_ui(self) -> None:
        return None

    def get_state(self, *, wait_to_stabilize: bool):
        assert wait_to_stabilize
        self.capture_count += 1
        return SimpleNamespace(
            pixels=np.full((20, 10, 3), self.capture_count, dtype=np.uint8),
            ui_elements=[],
        )


class _Task:
    name = "FakeMemoryTask"
    goal = "Use the remembered canary"
    params = {"canary": "CANARY-4721"}

    def initialize_task(self, env) -> None:
        del env

    def is_successful(self, env) -> float:
        del env
        return 0.0

    def tear_down(self, env) -> None:
        del env


def test_controller_writes_then_injects_memory_without_overriding_evaluator(
    tmp_path: Path,
) -> None:
    client = _Client()
    memory = ActionWorkingMemory(max_items=6, max_chars=3000)
    summary = OfficialQwenMobileController(
        client,
        adapter=_Adapter(),
        working_memory=memory,
    ).run(
        env=_Env(),
        task=_Task(),
        episode_id="episode",
        episode_dir=tmp_path / "episode",
        seed=20260806,
    )

    assert "CANARY-4721" not in client.prompts[0]
    assert "CANARY-4721" in client.prompts[1]
    assert summary["memory_mechanism"]["write_success_count"] == 1
    assert summary["memory_mechanism"]["nonempty_read_count"] == 1
    assert summary["memory_mechanism"]["active"] is True
    assert summary["steps"][0]["memory_write"]["written"] is True
    assert summary["steps"][1]["memory_read"]["nonempty"] is True
    assert summary["model_claimed_status"] == "success"
    assert summary["evaluator_reward"] == 0.0
    assert summary["success"] is False


def test_controller_without_a1_keeps_official_first_request_exact(
    tmp_path: Path,
) -> None:
    client = _Client()
    summary = OfficialQwenMobileController(
        client,
        adapter=_Adapter(),
    ).run(
        env=_Env(),
        task=_Task(),
        episode_id="baseline-episode",
        episode_dir=tmp_path / "baseline-episode",
        seed=20260806,
    )
    assert client.prompts[0] == build_user_prompt(_Task.goal, [])
    assert summary["memory_mechanism"] is None
