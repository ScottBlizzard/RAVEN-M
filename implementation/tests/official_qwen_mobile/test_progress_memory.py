from pathlib import Path
from types import SimpleNamespace

import numpy as np

from raven_m.models.transformers_client import ModelCall
from raven_m.official_qwen_mobile.controller import OfficialQwenMobileController
from raven_m.official_qwen_mobile.progress_memory import (
    RepeatedNoProgressGuard,
    VerifiedProgressMemory,
    action_signature,
)


def _snapshot(ui: str = "ui-a", activity: str = "pkg/.Main") -> dict:
    return {
        "visible_state": ui,
        "ui_sha256": ui,
        "foreground": {"activity": activity},
    }


def _no_change() -> dict:
    return {
        "changed_pixel_fraction_gt_5": 0.0,
        "activity_changed": False,
        "ui_sha_changed": False,
    }


def test_progress_memory_is_single_state_and_does_not_duplicate_history() -> None:
    memory = VerifiedProgressMemory(max_chars=1200)
    summary = (
        "PROGRESS[observed=CANARY-4721 visible; verified=form opened; "
        "pending=save record; expected=save confirmation appears] | Tap Save."
    )
    write = memory.observe_step(
        source_step=2,
        action_summary=summary,
        canonical_action={"type": "tap", "x": 0.8, "y": 0.1},
        transition=_no_change(),
        source_call_id="call",
        source_response_sha256="response",
        source_screenshot_sha256="screen",
    )
    assert write["written"] is True
    rendered, audit = memory.read()
    assert "CANARY-4721" in rendered
    assert "no_visible_change" in rendered
    assert audit["nonempty"] is True
    assert memory.history_summary(summary) == "Tap Save."
    assert "PROGRESS[" not in memory.history_summary(summary)


def test_guard_allows_two_no_progress_executions_then_blocks_jittered_repeat() -> None:
    guard = RepeatedNoProgressGuard(no_progress_threshold=2, max_blocks=2)
    before = _snapshot()
    after = _snapshot()
    first = {"type": "tap", "x": 0.501, "y": 0.081}
    jittered = {"type": "tap", "x": 0.499, "y": 0.085}
    assert action_signature(first) == action_signature(jittered)
    assert guard.assess(before=before, action=first)["blocked"] is False
    guard.observe(before=before, after=after, action=first, transition=_no_change())
    assert guard.assess(before=before, action=jittered)["blocked"] is False
    guard.observe(before=before, after=after, action=jittered, transition=_no_change())
    assessment = guard.assess(before=before, action=first)
    assert assessment["blocked"] is True
    assert guard.record_block(assessment)["cost_stop"] is False
    assert guard.record_block(assessment)["cost_stop"] is True


def test_guard_never_blocks_after_real_visible_change() -> None:
    guard = RepeatedNoProgressGuard(no_progress_threshold=2, max_blocks=2)
    action = {"type": "tap", "x": 0.5, "y": 0.08}
    guard.observe(
        before=_snapshot("a"),
        after=_snapshot("b"),
        action=action,
        transition={
            "changed_pixel_fraction_gt_5": 0.2,
            "activity_changed": False,
            "ui_sha_changed": True,
        },
    )
    assert guard.assess(before=_snapshot("a"), action=action)["blocked"] is False


def test_guard_ignores_hidden_activity_and_ui_metadata() -> None:
    guard = RepeatedNoProgressGuard(no_progress_threshold=2, max_blocks=2)
    visible_a = {
        "visible_state": "same-visible-screen",
        "ui_sha256": "hidden-ui-a",
        "foreground": {"activity": "hidden/.A"},
    }
    visible_b = {
        "visible_state": "same-visible-screen",
        "ui_sha256": "hidden-ui-b",
        "foreground": {"activity": "hidden/.B"},
    }
    action = {"type": "tap", "x": 0.5, "y": 0.08}
    guard.observe(before=visible_a, after=visible_b, action=action, transition=_no_change())
    guard.observe(before=visible_a, after=visible_b, action=action, transition=_no_change())
    assert guard.assess(before=visible_b, action=action)["blocked"] is True


def test_different_executed_action_resets_consecutive_block_sequence() -> None:
    guard = RepeatedNoProgressGuard(no_progress_threshold=2, max_blocks=2)
    snapshot = _snapshot()
    first = {"type": "tap", "x": 0.5, "y": 0.08}
    different = {"type": "press_back"}
    for _ in range(2):
        guard.observe(before=snapshot, after=snapshot, action=first, transition=_no_change())
    blocked = guard.assess(before=snapshot, action=first)
    assert guard.record_block(blocked)["cost_stop"] is False
    guard.observe(
        before=snapshot,
        after=snapshot,
        action=different,
        transition=_no_change(),
    )
    assert guard.record_block(blocked)["cost_stop"] is False


class _Client:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(self, **kwargs) -> ModelCall:
        self.prompts.append(kwargs["user_prompt"])
        index = len(self.prompts)
        if index == 1:
            content = (
                "Thought: test the control.\n"
                "Action: PROGRESS[observed=CANARY-A2; verified=none; "
                "pending=finish; expected=page changes] | Tap the control.\n"
                '<tool_call>{"name":"mobile_use","arguments":{"action":"click",'
                '"coordinate":[500,500]}}</tool_call>'
            )
        else:
            content = (
                "Thought: stop.\n"
                "Action: PROGRESS[observed=none; verified=none; pending=none; "
                "expected=none] | Finish.\n"
                '<tool_call>{"name":"mobile_use","arguments":{"action":"terminate",'
                '"status":"success"}}</tool_call>'
            )
        return ModelCall(
            call_id=f"call-{index}",
            episode_id="episode",
            idempotency_key=f"key-{index}",
            image_sha256="image",
            image_sha256s=("image",),
            prompt_sha256=f"prompt-{index}",
            request_sha256=f"request-{index}",
            response_sha256=f"response-{index}",
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
    name = "FakeA2Task"
    goal = "Use the A2 canary"
    params = {"canary": "CANARY-A2"}

    def initialize_task(self, env) -> None:
        del env

    def is_successful(self, env) -> float:
        del env
        return 0.0

    def tear_down(self, env) -> None:
        del env


def test_controller_a2_injects_outcome_memory_and_keeps_evaluator_hidden(
    tmp_path: Path,
) -> None:
    client = _Client()
    summary = OfficialQwenMobileController(
        client,
        adapter=_Adapter(),
        working_memory=VerifiedProgressMemory(max_chars=1200),
        cost_guard=RepeatedNoProgressGuard(no_progress_threshold=2, max_blocks=2),
    ).run(
        env=_Env(),
        task=_Task(),
        episode_id="episode",
        episode_dir=tmp_path / "episode",
        seed=20260806,
    )
    assert "CANARY-A2" not in client.prompts[0]
    assert "CANARY-A2" in client.prompts[1]
    assert "PROGRESS[" not in summary["steps"][0]["history_after"][0]
    assert summary["memory_mechanism"]["active"] is True
    assert summary["cost_guard"]["block_count"] == 0
    assert summary["evaluator_reward"] == 0.0
    assert summary["success"] is False
