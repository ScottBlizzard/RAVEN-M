from pathlib import Path
from types import SimpleNamespace

import numpy as np

from raven_m.models.transformers_client import ModelCall
from raven_m.official_qwen_mobile.controller import OfficialQwenMobileController
from raven_m.official_qwen_mobile.numeric_answer_guard import (
    NumericAnswerConsistencyGuard,
)


class AnswerClient:
    sampling = {}

    def generate(self, **kwargs) -> ModelCall:
        del kwargs
        content = (
            "Thought: two qualifying activities are visible.\n"
            "Action: Calculate the total duration of A (1 hour 45 minutes) "
            "and B (1 hour 15 minutes) in minutes.\n"
            "<tool_call>\n"
            '{"name":"mobile_use","arguments":{"action":"answer","text":"165"}}'
            "\n</tool_call>"
        )
        return ModelCall(
            call_id="call", episode_id="episode", idempotency_key="key",
            image_sha256="image", image_sha256s=("image",),
            prompt_sha256="prompt", request_sha256="request",
            response_sha256="response", content=content,
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            raven_meta={"latency_seconds": 0.1, "transport_attempts": 1},
        )


def _response(summary: str, arguments: str) -> str:
    return (
        f"Thought: synthetic.\nAction: {summary}\n<tool_call>\n"
        f'{{"name":"mobile_use","arguments":{arguments}}}'
        "\n</tool_call>"
    )


class TerminalSequenceClient:
    sampling = {}

    def __init__(self):
        self.contents = [
            _response("Wait for export processing.", '{"action":"wait","time":2}'),
            _response(
                "MEMORY[verified=file exported; pending=None] | Terminate success.",
                '{"action":"terminate","status":"success"}',
            ),
            _response("Tap the visible confirmation.", '{"action":"click","coordinate":[500,500]}'),
        ]
        self.prompts = []

    def generate(self, **kwargs) -> ModelCall:
        self.prompts.append(kwargs["user_prompt"])
        index = len(self.prompts) - 1
        content = self.contents[index]
        return ModelCall(
            call_id=f"call-{index}", episode_id="episode", idempotency_key=f"key-{index}",
            image_sha256="image", image_sha256s=("image",),
            prompt_sha256=f"prompt-{index}", request_sha256=f"request-{index}",
            response_sha256=f"response-{index}", content=content,
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            raven_meta={"latency_seconds": 0.1, "transport_attempts": 1},
        )


class PendingMemory:
    def prompt_history(self, history):
        return list(history)

    def read(self, *, context):
        del context
        text = "VERIFIED: file prepared\nPENDING: save the prepared file"
        return text, {"rendered_chars": len(text)}

    def record_protocol(self, summary):
        return {"summary": summary}

    def history_summary(self, summary):
        return summary.rsplit("|", 1)[-1].strip()

    def observe_step(self, **kwargs):
        del kwargs
        return {"observed": True}

    def audit_record(self):
        return {"schema": "synthetic_pending", "active": True}


class Mapped:
    def __init__(self, canonical):
        self.canonical = dict(canonical)

    def audit_record(self):
        return {
            "canonical": dict(self.canonical), "screen_size": [10, 20],
            "upstream_action": {"action_type": self.canonical["type"]},
        }


class CapturingAdapter:
    def __init__(self):
        self.executed = None

    def map_action(self, action, *, screen_width, screen_height):
        del screen_width, screen_height
        return Mapped(action)

    def execute(self, env, mapped):
        del env
        self.executed = dict(mapped.canonical)


class Env:
    def reset(self, *, go_home):
        assert go_home

    def hide_automation_ui(self):
        return None

    def get_state(self, *, wait_to_stabilize):
        assert wait_to_stabilize
        return SimpleNamespace(pixels=np.zeros((20, 10, 3), dtype=np.uint8), ui_elements=[])


class Task:
    name = "SyntheticDurationTask"
    goal = "Return the total duration as one integer"
    params = {}

    def __init__(self, adapter):
        self.adapter = adapter

    def initialize_task(self, env):
        del env

    def is_successful(self, env):
        del env
        return float(self.adapter.executed == {"type": "answer", "text": "180"})

    def tear_down(self, env):
        del env


def test_controller_executes_corrected_action_and_audits_both_values(tmp_path: Path) -> None:
    adapter = CapturingAdapter()
    summary = OfficialQwenMobileController(
        AnswerClient(), adapter=adapter, max_steps=1,
        answer_consistency_guard=NumericAnswerConsistencyGuard(),
    ).run(
        env=Env(), task=Task(adapter), episode_id="episode",
        episode_dir=tmp_path / "episode", seed=7,
    )
    assert summary["success"] is True
    step = summary["steps"][0]
    assert step["decision"]["canonical_action"]["text"] == "165"
    assert step["mapped_action"]["canonical"]["text"] == "180"
    assert step["answer_consistency_guard"]["overridden"] is True
    assert step["answer_consistency_guard"]["proposed_action"]["text"] == "165"
    assert step["answer_consistency_guard"]["executed_action"]["text"] == "180"
    assert summary["answer_consistency_guard"]["counters"]["action_override_count"] == 1


def test_runner_wires_sys_nag_as_distinct_arm() -> None:
    runner = Path("implementation/scripts/run_official_qwen_mobile.py").read_text(
        encoding="utf-8"
    )
    assert '"sys_nag"' in runner
    assert "NumericAnswerConsistencyGuard" in runner
    assert "answer_consistency_guard=answer_consistency_guard" in runner
    assert '"pending_terminal_suppression": True' in runner
    assert '"route_recurrence_suppression": True' in runner
    assert '"task_order": "blocking_A1R2_success_6_then_frozen_manifest_remainder"' in runner


def test_controller_blocks_one_pending_terminal_after_wait(tmp_path: Path) -> None:
    client = TerminalSequenceClient()
    adapter = CapturingAdapter()
    summary = OfficialQwenMobileController(
        client,
        adapter=adapter,
        max_steps=3,
        working_memory=PendingMemory(),
        answer_consistency_guard=NumericAnswerConsistencyGuard(),
    ).run(
        env=Env(), task=Task(adapter), episode_id="episode",
        episode_dir=tmp_path / "terminal", seed=7,
    )
    assert summary["steps"][1]["pending_terminal_consistency_guard"]["blocked"] is True
    assert summary["steps"][1]["executed"] is False
    assert "TERMINAL CONSISTENCY CHECK" in client.prompts[2]
    assert summary["answer_consistency_guard"]["counters"]["terminal_block_count"] == 1
