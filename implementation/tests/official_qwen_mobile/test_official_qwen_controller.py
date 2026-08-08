from pathlib import Path
from types import SimpleNamespace

import numpy as np

from raven_m.models.transformers_client import ModelCall
from raven_m.official_qwen_mobile.controller import OfficialQwenMobileController


class Client:
    def generate(self, **kwargs) -> ModelCall:
        del kwargs
        content = (
            "Thought: the task appears complete.\n"
            "Action: Finish the task.\n"
            "<tool_call>\n"
            '{"name":"mobile_use","arguments":{"action":"terminate","status":"success"}}'
            "\n</tool_call>"
        )
        return ModelCall(
            call_id="call",
            episode_id="episode",
            idempotency_key="key",
            image_sha256="image",
            image_sha256s=("image",),
            prompt_sha256="prompt",
            request_sha256="request",
            response_sha256="response",
            content=content,
            usage={},
            raven_meta={},
        )


class Env:
    def reset(self, *, go_home: bool) -> None:
        assert go_home

    def hide_automation_ui(self) -> None:
        return None

    def get_state(self, *, wait_to_stabilize: bool):
        assert wait_to_stabilize
        return SimpleNamespace(pixels=np.zeros((20, 10, 3), dtype=np.uint8))


class Task:
    name = "FakeTask"
    goal = "Make a persistent change"
    params = {"value": "x"}

    def initialize_task(self, env) -> None:
        del env

    def is_successful(self, env) -> float:
        del env
        return 0.0

    def tear_down(self, env) -> None:
        del env


class ClickThenFinishClient:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, **kwargs) -> ModelCall:
        del kwargs
        self.calls += 1
        if self.calls == 1:
            content = (
                "Thought: tap the visible control.\n"
                "Action: tap.\n"
                "<tool_call>\n"
                '{"name":"mobile_use","arguments":{"action":"click","coordinate":[500,500]}}'
                "\n</tool_call>"
            )
        else:
            content = (
                "Thought: done.\nAction: Finish the task.\n<tool_call>\n"
                '{"name":"mobile_use","arguments":{"action":"terminate","status":"success"}}'
                "\n</tool_call>"
            )
        return ModelCall(
            call_id=f"call-{self.calls}",
            episode_id="episode",
            idempotency_key="key",
            image_sha256="image",
            image_sha256s=("image",),
            prompt_sha256="prompt",
            request_sha256="request",
            response_sha256="response",
            content=content,
            usage={},
            raven_meta={"latency_seconds": 1.25, "transport_attempts": 1},
        )


class Mapped:
    def audit_record(self):
        return {
            "canonical": {"type": "click", "x": 500, "y": 500},
            "screen_size": [10, 20],
            "actual_pixels": {"x": 5, "y": 10},
            "upstream_action": {"action_type": "click", "x": 5, "y": 10},
        }


class Adapter:
    def __init__(self) -> None:
        self.executions = 0

    def map_action(self, action, *, screen_width, screen_height):
        del action, screen_width, screen_height
        return Mapped()

    def execute(self, env, mapped) -> None:
        del env, mapped
        self.executions += 1


class ChangingEnv(Env):
    def __init__(self) -> None:
        self.captures = 0

    def get_state(self, *, wait_to_stabilize: bool):
        assert wait_to_stabilize
        value = min(self.captures, 1)
        self.captures += 1
        return SimpleNamespace(
            pixels=np.full((20, 10, 3), value * 255, dtype=np.uint8),
            ui_elements=[],
        )


def test_model_success_claim_does_not_override_androidworld_evaluator(
    tmp_path: Path,
) -> None:
    summary = OfficialQwenMobileController(Client()).run(
        env=Env(),
        task=Task(),
        episode_id="episode",
        episode_dir=tmp_path / "episode",
        seed=7,
    )
    assert summary["model_claimed_status"] == "success"
    assert summary["evaluator_reward"] == 0.0
    assert summary["success"] is False


def test_layered_audit_reuses_post_action_state_without_extra_capture(
    tmp_path: Path,
) -> None:
    env = ChangingEnv()
    adapter = Adapter()
    summary = OfficialQwenMobileController(
        ClickThenFinishClient(),
        adapter=adapter,
    ).run(
        env=env,
        task=Task(),
        episode_id="episode",
        episode_dir=tmp_path / "episode",
        seed=7,
    )
    assert env.captures == 2
    assert adapter.executions == 1
    first = summary["steps"][0]
    assert first["layers"]["L3_execution"]["completed"] is True
    assert first["layers"]["L4_transition_progress"]["exactly_unchanged"] is False
    assert first["after"]["screenshot"] == "step_000_after.png"
    assert summary["steps"][1]["before"]["pixel_sha256"] == first["after"]["pixel_sha256"]


def test_transition_attestation_replaces_unverified_semantic_summary() -> None:
    controller = OfficialQwenMobileController(
        Client(),
        history_policy="transition_attested_action_summaries_v1",
    )
    committed, applied, reason = controller._committed_history_summary(
        model_action_summary="I saved all requested waypoints.",
        canonical_action={"type": "tap", "x": 0.5, "y": 0.5},
        transition={
            "changed_pixel_fraction_gt_5": 0.0,
            "activity_changed": False,
            "ui_sha_changed": False,
        },
    )
    assert applied is True
    assert reason == "no_observable_transition"
    assert "saved all requested waypoints" not in committed
    assert "semantic effect" in committed
    assert "do not repeat" in committed


def test_transition_attestation_preserves_summary_when_ui_changes() -> None:
    controller = OfficialQwenMobileController(
        Client(),
        history_policy="transition_attested_action_summaries_v1",
    )
    committed, applied, reason = controller._committed_history_summary(
        model_action_summary="I opened the target details.",
        canonical_action={"type": "tap", "x": 0.5, "y": 0.5},
        transition={
            "changed_pixel_fraction_gt_5": 0.01,
            "activity_changed": False,
            "ui_sha_changed": True,
        },
    )
    assert committed == "I opened the target details."
    assert applied is False
    assert reason is None
