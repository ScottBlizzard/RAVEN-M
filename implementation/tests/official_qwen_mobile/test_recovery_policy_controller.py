from __future__ import annotations

from pathlib import Path
from hashlib import sha256
from types import SimpleNamespace
from typing import Any

import numpy as np

from raven_m.models.transformers_client import ModelCall
from raven_m.official_qwen_mobile.controller import OfficialQwenMobileController
from raven_m.official_qwen_mobile.sys_trrc_recovery import (
    OneShotTriggeredRecoveryPolicy,
)


def _call(call_id: str, content: str, *, tokens: int) -> ModelCall:
    return ModelCall(
        call_id=call_id,
        episode_id="episode",
        idempotency_key=f"key-{call_id}",
        image_sha256="image",
        image_sha256s=("image",),
        prompt_sha256=f"prompt-{call_id}",
        request_sha256=f"request-{call_id}",
        response_sha256=f"response-{call_id}",
        content=content,
        usage={"prompt_tokens": tokens - 1, "completion_tokens": 1, "total_tokens": tokens},
        raven_meta={"latency_seconds": 0.1, "transport_attempts": 1},
    )


CLICK = (
    "Thought: tap the visible control.\n"
    "Action: MEMORY[observed=x; verified=none; pending=finish] | tap.\n"
    "<tool_call>\n"
    '{"name":"mobile_use","arguments":{"action":"click","coordinate":[500,500]}}'
    "\n</tool_call>"
)
FINISH = (
    "Thought: done.\n"
    "Action: MEMORY[observed=x; verified=done; pending=none] | Finish.\n"
    "<tool_call>\n"
    '{"name":"mobile_use","arguments":{"action":"terminate","status":"success"}}'
    "\n</tool_call>"
)


class FakeClient:
    def __init__(self, order: list[str], *, fail_aux: bool = False) -> None:
        self.order = order
        self.fail_aux = fail_aux
        self.kwargs: list[dict[str, Any]] = []
        self.normal_calls = 0

    def generate(self, **kwargs: Any) -> ModelCall:
        self.kwargs.append(dict(kwargs))
        label = str(kwargs["call_label"])
        self.order.append(f"client:{label}")
        if label.startswith("aux_recovery_"):
            if self.fail_aux:
                raise ConnectionError("aux transport failed")
            return _call("aux", "Inspect the visible state and choose a different route.", tokens=3)
        self.normal_calls += 1
        return _call(
            f"normal-{self.normal_calls}",
            CLICK if self.normal_calls == 1 else FINISH,
            tokens=5,
        )


class ActualPolicyClient:
    def __init__(self) -> None:
        self.normal_calls = 0
        self.kwargs: list[dict[str, Any]] = []

    def generate(self, **kwargs: Any) -> ModelCall:
        self.kwargs.append(dict(kwargs))
        label = str(kwargs["call_label"])
        if label.startswith("aux_recovery_"):
            content = (
                "ASSESSMENT: The repeated action left the visible screen unchanged.\n"
                "RECOMMENDATION: Inspect another visible route to the pending requirement.\n"
                "VISIBLE_CHECK: Check whether a different relevant screen becomes visible."
            )
            prompt_tokens, completion_tokens = 500, 30
        else:
            self.normal_calls += 1
            content = CLICK if self.normal_calls <= 2 else FINISH
            prompt_tokens, completion_tokens = 20, 5
        image_path = Path(kwargs["image_path"])
        image_sha = sha256(image_path.read_bytes()).hexdigest()
        prompt_sha = sha256(
            (
                str(kwargs["system_prompt"])
                + "\n\0\n"
                + str(kwargs["user_prompt"])
            ).encode("utf-8")
        ).hexdigest()
        return ModelCall(
            call_id=label,
            episode_id="episode",
            idempotency_key=f"key-{label}",
            image_sha256=image_sha,
            image_sha256s=(image_sha,),
            prompt_sha256=prompt_sha,
            request_sha256=sha256(label.encode()).hexdigest(),
            response_sha256=sha256(content.encode()).hexdigest(),
            content=content,
            usage={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
            raven_meta={"latency_seconds": 0.1, "transport_attempts": 1},
        )


class FakeMemory:
    def __init__(self, order: list[str]) -> None:
        self.order = order
        self.reads = 0
        self.pending: str | None = None

    def read(self, context: dict[str, Any] | None = None):
        del context
        self.order.append("memory.read")
        self.reads += 1
        self.pending = f"r2-{self.reads}"
        return "EXACT R2 MEMORY", {
            "ticket_id": self.pending,
            "nonempty": True,
            "rendered_sha256": "r2",
        }

    def commit_injection(self, ticket_id: str, final_prompt_sha256: str):
        assert ticket_id == self.pending
        self.order.append("memory.commit")
        self.pending = None
        return {"ticket_id": ticket_id, "final_prompt_sha256": final_prompt_sha256}

    def cancel_injection(self, ticket_id: str, reason: str):
        assert ticket_id == self.pending
        self.pending = None
        return {"ticket_id": ticket_id, "reason": reason}

    def history_summary(self, action_summary: str) -> str:
        return action_summary.split(" | ", 1)[-1]

    def write(self, *, source_step: int, **_: Any):
        self.order.append(f"memory.write:{source_step}")
        return {"source_step": source_step}

    def audit_record(self):
        return {"mechanism_id": "fake_exact_r2", "pending_ticket": self.pending}


class FakeRecoveryPolicy:
    def __init__(
        self,
        order: list[str],
        *,
        initially_eligible: bool = False,
        remain_eligible: bool = False,
    ) -> None:
        self.order = order
        self.eligible = initially_eligible
        self.remain_eligible = remain_eligible
        self.used = False
        self.cancelled = False
        self.observations = 0
        self.closed = False

    def prepare_aux(self, context: dict[str, Any]):
        step = int(context["request_step"])
        self.order.append(f"policy.prepare:{step}")
        if not self.eligible:
            return None
        if self.used and not self.remain_eligible:
            return None
        return {
            "ticket_id": f"aux-ticket-{step}",
            "system_prompt": "Recovery analysis only; do not emit an action.",
            "user_prompt": "Diagnose the visible non-progress state.",
            "max_tokens": 64,
        }

    def commit_aux(self, ticket_id: str, call: ModelCall):
        self.order.append("policy.commit_aux")
        assert ticket_id.startswith("aux-ticket-")
        assert isinstance(call, ModelCall)
        self.used = True
        self.eligible = self.remain_eligible
        return {
            "ticket_id": ticket_id,
            "injection_ticket_id": "inject-ticket",
            "injection_text": "RECOVERY HINT: use a visibly different route.",
        }

    def count_advice_prompt_tokens(self, base_text: str, final_text: str) -> int:
        assert final_text != base_text
        return 7

    def commit_normal_injection(
        self, ticket_id: str, final_prompt_sha256: str, call: ModelCall
    ):
        self.order.append("policy.commit_normal")
        assert ticket_id == "inject-ticket"
        assert len(final_prompt_sha256) == 64
        assert isinstance(call, ModelCall)
        return {"ticket_id": ticket_id, "normal_call_id": call.call_id}

    def cancel_aux(self, ticket_id: str, reason: str):
        self.order.append("policy.cancel_aux")
        self.cancelled = True
        return {"ticket_id": ticket_id, "reason": reason}

    def cancel_normal_injection(self, ticket_id: str, reason: str):
        self.order.append("policy.cancel_normal")
        return {"ticket_id": ticket_id, "reason": reason}

    def observe_transition(self, *, source_step: int, before_pixels, after_pixels, **_: Any):
        self.order.append(f"policy.observe:{source_step}")
        assert isinstance(before_pixels, np.ndarray)
        assert isinstance(after_pixels, np.ndarray)
        before_pixels[:] = 99  # The controller must have passed isolated copies.
        after_pixels[:] = 99
        self.observations += 1
        self.eligible = True
        return {"source_step": source_step, "eligible_created": True}

    def close_episode(self, reason: str):
        self.order.append("policy.close")
        self.closed = True
        return {"reason": reason, "closed": True}

    def audit_record(self):
        return {
            "mechanism_id": "fake_recovery",
            "used": self.used,
            "cancelled": self.cancelled,
            "observations": self.observations,
            "closed": self.closed,
        }


class Env:
    def __init__(self) -> None:
        self.captures = 0

    def reset(self, *, go_home: bool) -> None:
        assert go_home

    def hide_automation_ui(self) -> None:
        return None

    def get_state(self, *, wait_to_stabilize: bool):
        assert wait_to_stabilize
        value = min(self.captures, 1)
        self.captures += 1
        return SimpleNamespace(
            pixels=np.full((20, 10, 3), value, dtype=np.uint8),
            ui_elements=[],
        )


class Task:
    name = "FakeTask"
    goal = "Make a persistent change"
    params = {"value": "x"}

    def initialize_task(self, env: Any) -> None:
        del env

    def is_successful(self, env: Any) -> float:
        del env
        return 0.0

    def tear_down(self, env: Any) -> None:
        del env


class Mapped:
    def audit_record(self):
        return {
            "canonical": {"type": "click", "x": 0.5, "y": 0.5},
            "screen_size": [10, 20],
            "actual_pixels": {"x": 5, "y": 10},
            "upstream_action": {"action_type": "click", "x": 5, "y": 10},
        }


class Adapter:
    def __init__(self) -> None:
        self.executions = 0

    def map_action(self, action: dict[str, Any], *, screen_width: int, screen_height: int):
        del action, screen_width, screen_height
        return Mapped()

    def execute(self, env: Any, mapped: Any) -> None:
        del env, mapped
        self.executions += 1


def _run(
    tmp_path: Path,
    *,
    policy: FakeRecoveryPolicy | None,
    client: FakeClient,
    memory: FakeMemory,
    adapter: Adapter,
    env: Any | None = None,
    max_tokens: int = 128,
):
    return OfficialQwenMobileController(
        client,
        max_steps=3,
        max_tokens=max_tokens,
        adapter=adapter,
        working_memory=memory,
        recovery_policy=policy,
    ).run(
        env=env or Env(),
        task=Task(),
        episode_id="episode",
        episode_dir=tmp_path / "episode",
        seed=7,
    )


def test_aux_runs_before_r2_read_observe_runs_after_r2_write_and_counts_all_calls(
    tmp_path: Path,
) -> None:
    order: list[str] = []
    policy = FakeRecoveryPolicy(order)
    client = FakeClient(order)
    memory = FakeMemory(order)
    adapter = Adapter()
    summary = _run(
        tmp_path, policy=policy, client=client, memory=memory, adapter=adapter
    )

    assert order.index("memory.write:0") < order.index("policy.observe:0")
    assert order.index("policy.prepare:1") < order.index("client:aux_recovery_001")
    assert order.index("client:aux_recovery_001") < order.index("memory.read", 4)
    assert order.index("policy.commit_aux") < order.index("client:official_step_001")
    assert adapter.executions == 1
    assert summary["normal_decision_call_count"] == 2
    assert summary["aux_recovery_call_count"] == 1
    assert summary["model_call_count"] == 3
    assert summary["model_call_breakdown"] == {
        "normal_decision": 2,
        "aux_recovery": 1,
        "total": 3,
    }
    assert len(summary["auxiliary_model_call_attempts"]) == 1
    assert summary["steps"][1]["recovery"]["normal_injection"][
        "injection_commit"
    ]["normal_call_id"] == "normal-2"
    normal_second = next(
        item for item in client.kwargs if item["call_label"] == "official_step_001"
    )
    assert "EXACT R2 MEMORY" in normal_second["user_prompt"]
    assert "RECOVERY HINT" in normal_second["user_prompt"]
    assert summary["steps"][1]["before"]["pixel_sha256"] == summary["steps"][0][
        "after"
    ]["pixel_sha256"]
    assert policy.closed is True


def test_controller_fail_closes_before_a_second_auxiliary_call(tmp_path: Path) -> None:
    order: list[str] = []
    policy = FakeRecoveryPolicy(order, initially_eligible=True, remain_eligible=True)
    client = FakeClient(order)
    summary = _run(
        tmp_path,
        policy=policy,
        client=client,
        memory=FakeMemory(order),
        adapter=Adapter(),
    )
    assert summary["error"]["type"] == "RuntimeError"
    assert "more than one auxiliary" in summary["error"]["message"]
    assert summary["aux_recovery_call_count"] == 1
    assert sum(
        item["call_label"].startswith("aux_recovery_") for item in client.kwargs
    ) == 1


def test_aux_transport_failure_is_cancelled_and_audited(tmp_path: Path) -> None:
    order: list[str] = []
    policy = FakeRecoveryPolicy(order, initially_eligible=True)
    client = FakeClient(order, fail_aux=True)
    summary = _run(
        tmp_path,
        policy=policy,
        client=client,
        memory=FakeMemory(order),
        adapter=Adapter(),
    )
    assert summary["error"]["type"] == "ConnectionError"
    assert summary["normal_decision_call_count"] == 0
    assert summary["aux_recovery_call_count"] == 0
    assert summary["model_call_count"] == 0
    assert summary["auxiliary_model_call_attempts"][0]["model_call"] is None
    assert summary["auxiliary_model_call_attempts"][0]["cancellation"][
        "ticket_id"
    ] == "aux-ticket-0"
    assert policy.cancelled is True


def test_no_policy_preserves_historical_summary_shape(tmp_path: Path) -> None:
    order: list[str] = []
    client = FakeClient(order)
    summary = _run(
        tmp_path,
        policy=None,
        client=client,
        memory=FakeMemory(order),
        adapter=Adapter(),
    )
    assert summary["model_call_count"] == len(summary["steps"]) == 2
    for key in (
        "normal_decision_call_count",
        "aux_recovery_call_count",
        "model_call_breakdown",
        "auxiliary_model_call_attempts",
        "recovery_episode_close",
        "recovery_mechanism",
    ):
        assert key not in summary
    assert all("recovery" not in step for step in summary["steps"])
    assert all(not item["call_label"].startswith("aux_recovery_") for item in client.kwargs)


def test_actual_sys_trrc_policy_closes_multimodal_aux_and_injection_chain(
    tmp_path: Path,
) -> None:
    def projector(system_prompt: str, user_prompt: str, screenshot_path: str) -> dict:
        del system_prompt, user_prompt
        path = Path(screenshot_path)
        return {
            "schema": "test_projection",
            "current_screenshot_sha256": sha256(path.read_bytes()).hexdigest(),
            "exact_multimodal_input_tokens": 500,
        }

    policy = OneShotTriggeredRecoveryPolicy(
        mode="full", token_projector=projector,
        text_delta_counter=lambda base, final: 7,
    )
    client = ActualPolicyClient()
    order: list[str] = []
    constant_env = Env()
    constant_env.captures = 1
    summary = _run(
        tmp_path,
        policy=policy,  # type: ignore[arg-type]
        client=client,  # type: ignore[arg-type]
        memory=FakeMemory(order),
        adapter=Adapter(),
        env=constant_env,
        max_tokens=256,
    )
    assert summary["error"] is None
    assert summary["normal_decision_call_count"] == 3
    assert summary["aux_recovery_call_count"] == 1
    assert summary["model_call_count"] == 4
    audit = summary["recovery_mechanism"]
    assert audit["counters"]["trigger_count"] == 1
    assert audit["counters"]["aux_committed_count"] == 1
    assert audit["counters"]["injection_committed_count"] == 1
    aux_kwargs = next(
        item
        for item in client.kwargs
        if str(item["call_label"]).startswith("aux_recovery_")
    )
    assert aux_kwargs["request_timeout_seconds"] == 60.0
    injected_step = summary["steps"][2]
    assert injected_step["recovery"]["normal_injection"][
        "injection_commit"
    ]["normal_call_id"] == "official_step_002"
