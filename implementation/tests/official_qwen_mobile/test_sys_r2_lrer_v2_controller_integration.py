from __future__ import annotations

from pathlib import Path
import json
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from raven_m.models.transformers_client import ModelCall
from raven_m.official_qwen_mobile import controller as controller_module
from raven_m.official_qwen_mobile.controller import OfficialQwenMobileController


CLICK = (
    "Thought: tap the visible control.\n"
    "Action: tap.\n"
    '<tool_call>\n{"name":"mobile_use","arguments":{"action":"click",'
    '"coordinate":[500,500]}}\n</tool_call>'
)
FINISH = (
    "Thought: the requested change is complete.\n"
    "Action: finish.\n"
    '<tool_call>\n{"name":"mobile_use","arguments":{"action":"terminate",'
    '"status":"success"}}\n</tool_call>'
)


def _call(ordinal: int, content: str) -> ModelCall:
    return ModelCall(
        call_id=f"call-{ordinal}",
        episode_id="episode",
        idempotency_key=f"key-{ordinal}",
        image_sha256="image",
        image_sha256s=("image",),
        prompt_sha256=f"prompt-{ordinal}",
        request_sha256=f"request-{ordinal}",
        response_sha256=f"response-{ordinal}",
        content=content,
        usage={"prompt_tokens": 4, "completion_tokens": 1, "total_tokens": 5},
        raven_meta={"latency_seconds": 0.1, "transport_attempts": 1},
    )


class Client:
    def __init__(self, order: list[str]) -> None:
        self.order = order
        self.calls = 0

    def generate(self, **_: Any) -> ModelCall:
        self.order.append("model")
        self.calls += 1
        return _call(self.calls, CLICK if self.calls == 1 else FINISH)


class Env:
    def __init__(self, order: list[str]) -> None:
        self.order = order
        self.captures = 0

    def reset(self, *, go_home: bool) -> None:
        assert go_home

    def hide_automation_ui(self) -> None:
        return None

    def get_state(self, *, wait_to_stabilize: bool):
        assert wait_to_stabilize
        self.order.append("capture")
        self.captures += 1
        return SimpleNamespace(
            pixels=np.full((20, 10, 3), self.captures, dtype=np.uint8),
            ui_elements=[],
        )


class Task:
    name = "FakeTask"
    goal = "Make a persistent visible change"
    params: dict[str, Any] = {}

    def initialize_task(self, env: Any) -> None:
        del env

    def is_successful(self, env: Any) -> float:
        del env
        return 1.0

    def tear_down(self, env: Any) -> None:
        del env


class Mapped:
    def audit_record(self) -> dict[str, Any]:
        return {
            "canonical": {"type": "click", "x": 0.5, "y": 0.5},
            "screen_size": [10, 20],
            "actual_pixels": {"x": 5, "y": 10},
            "upstream_action": {"action_type": "click", "x": 5, "y": 10},
        }


class Adapter:
    def __init__(self, order: list[str]) -> None:
        self.order = order
        self.executions = 0

    def map_action(self, action: dict[str, Any], *, screen_width: int, screen_height: int):
        del action, screen_width, screen_height
        return Mapped()

    def execute(self, env: Any, mapped: Any) -> None:
        del env, mapped
        self.order.append("execute")
        self.executions += 1


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, settle: float):
    order: list[str] = []
    slept: list[float] = []

    def fake_sleep(seconds: float) -> None:
        order.append("sleep")
        slept.append(seconds)

    monkeypatch.setattr(controller_module.time, "sleep", fake_sleep)
    env = Env(order)
    adapter = Adapter(order)
    summary = OfficialQwenMobileController(
        Client(order),
        max_steps=2,
        max_tokens=128,
        adapter=adapter,
        post_action_settle_seconds=settle,
    ).run(
        env=env,
        task=Task(),
        episode_id="episode",
        episode_dir=tmp_path / f"episode-{settle}",
        seed=7,
    )
    return order, slept, env, adapter, summary


def test_fixed_settle_occurs_after_execute_before_the_single_after_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    order, slept, env, adapter, summary = _run(tmp_path, monkeypatch, settle=1.0)
    assert order == ["capture", "model", "execute", "sleep", "capture", "model"]
    assert slept == [1.0]
    assert env.captures == 2  # initial state plus exactly one after-state
    assert adapter.executions == 1
    settle = summary["steps"][0]["layers"]["L3_execution"]["post_action_settle"]
    assert settle["policy"] == "fixed_visible_frame_settle_before_single_capture_v1"
    assert settle["requested_seconds"] == 1.0
    assert settle["additional_model_calls"] == 0
    assert settle["additional_actions"] == 0
    assert settle["additional_state_captures"] == 0


def test_zero_settle_preserves_historical_capture_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    order, slept, env, adapter, summary = _run(tmp_path, monkeypatch, settle=0.0)
    assert order == ["capture", "model", "execute", "capture", "model"]
    assert slept == []
    assert env.captures == 2
    assert adapter.executions == 1
    assert "post_action_settle" not in summary["steps"][0]["layers"]["L3_execution"]
    start = json.loads((tmp_path / "episode-0.0" / "events.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert "post_action_settle_seconds" not in start


@pytest.mark.parametrize("value", [-0.01, float("nan"), float("inf"), 5.01])
def test_invalid_settle_configuration_fails_closed(value: float) -> None:
    with pytest.raises(ValueError, match="post_action_settle_seconds"):
        OfficialQwenMobileController(
            Client([]),
            adapter=Adapter([]),
            post_action_settle_seconds=value,
        )
