"""C0: released MobileUse MultiAgent protocol on the required Qwen3-VL-32B.

C0 adds no RAVEN-M memory mechanism.  It restores the released prompts,
six-role schedule, coordinate scaling, and action space that PF01/B2 had
constrained, while retaining audited transport/logging and fail-closed crash
containment.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from types import MethodType
from typing import Any

import numpy as np

from raven_m.env.androidworld_adapter import AndroidWorldAdapter

from .c0_action_adapter import C0NativeActionAdapter
from .controller import MobileUseController, MobileUseRunResult, load_upstream


ARM_ID = "C0_NATIVE_MOBILEUSE_QWEN3VL32B_AW_HARD_S20260806_V1"


class _DormantUpstreamVLM:
    """Prevent creation of unused network clients before audited injection."""

    def __init__(self, **kwargs: Any) -> None:
        self.config = dict(kwargs)

    def predict(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        raise RuntimeError("Dormant upstream VLM was not replaced")


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


class C0NativeMobileUseController(MobileUseController):
    """Full native MobileUse control, without a new memory intervention."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        load_upstream()
        import mobile_use.agents.base as base_module
        import mobile_use.agents.sub_agent as sub_agent_module

        base_factory = base_module.VLMWrapper
        sub_agent_factory = sub_agent_module.VLMWrapper
        base_module.VLMWrapper = _DormantUpstreamVLM
        sub_agent_module.VLMWrapper = _DormantUpstreamVLM
        try:
            super().__init__(*args, **kwargs)
        finally:
            base_module.VLMWrapper = base_factory
            sub_agent_module.VLMWrapper = sub_agent_factory

        self.log.arm_id = ARM_ID
        native = C0NativeActionAdapter()

        # PF01 mechanically restricted these two prompts. C0 restores the
        # exact released YAML objects; all other role prompts were untouched.
        from mobile_use.default_prompts.prompt_type import load_prompt

        restricted_operator_sha = _digest(self.agent.operator.prompt.system_prompt)
        restricted_answer_sha = _digest(self.agent.answer_agent.prompt.system_prompt)
        self.agent.operator.prompt = load_prompt("operator", "operator.yaml")
        self.agent.answer_agent.prompt = load_prompt("answer_agent", "answer_agent.yaml")
        (Path(self.episode_dir) / "prompt_changes.json").write_text(
            json.dumps({
                "schema": "raven_m.c0.native_prompt_restore.v1",
                "operator": {
                    "from_pf01_sha256": restricted_operator_sha,
                    "native_sha256": _digest(self.agent.operator.prompt.system_prompt),
                    "source": "mobile_use/default_prompts/operator.yaml",
                },
                "answer_agent": {
                    "from_pf01_sha256": restricted_answer_sha,
                    "native_sha256": _digest(self.agent.answer_agent.prompt.system_prompt),
                    "source": "mobile_use/default_prompts/answer_agent.yaml",
                },
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        # Restore the released parser and its actual resized->raw coordinate
        # conversion. The third invalid response becomes an explicit failure,
        # so a model-format error is scored instead of crashing the suite.
        raw_operator_parse = type(self.agent.operator).parse_response.__get__(
            self.agent.operator, type(self.agent.operator)
        )
        parse_attempt = 0
        from mobile_use.schema.schema import Action

        def parse_operator(_instance: Any, content: str, *p_args: Any, **p_kwargs: Any) -> Any:
            nonlocal parse_attempt
            parse_attempt += 1
            try:
                parsed = raw_operator_parse(content)
                raw_width, raw_height = self.agent.operator.raw_size
                native.map(
                    parsed[1], screen_width=int(raw_width), screen_height=int(raw_height)
                )
            except Exception as exc:
                self.log.write(
                    "L1", "operator_parse_invalid", attempt=parse_attempt,
                    raw_output=content, error=f"{type(exc).__name__}: {exc}",
                )
                if parse_attempt < int(self.agent.max_action_retry):
                    raise
                parse_attempt = 0
                action = Action(name="terminate", parameters={"status": "failure"})
                self.log.write(
                    "L1", "operator_fail_closed",
                    reason="native_parser_retries_exhausted", terminal_status="failure",
                )
                return (
                    "Parser retries exhausted; fail closed.", action,
                    json.dumps([{"name": "mobile_use", "arguments": {"action": "terminate", "status": "failure"}}]),
                    "Terminate with failure after invalid output.",
                )
            self.log.write(
                "L1", "operator_parse_valid", attempt=parse_attempt,
                raw_output=content, action=repr(parsed[1]),
            )
            parse_attempt = 0
            return parsed

        self.agent.operator.parse_response = MethodType(parse_operator, self.agent.operator)

        raw_answer_parse = type(self.agent.answer_agent).parse_response.__get__(
            self.agent.answer_agent, type(self.agent.answer_agent)
        )

        def parse_answer(_instance: Any, content: str, *p_args: Any, **p_kwargs: Any) -> Any:
            parsed = raw_answer_parse(content)
            raw_width, raw_height = self.agent.answer_agent.raw_size
            mapped = native.map(
                parsed[1], screen_width=int(raw_width), screen_height=int(raw_height)
            )
            if mapped.upstream_name != "answer":
                raise ValueError("AnswerAgent may emit only answer")
            return parsed

        self.agent.answer_agent.parse_response = MethodType(
            parse_answer, self.agent.answer_agent
        )

        self.bridge.action_adapter = native
        android_adapter = AndroidWorldAdapter()

        def execute_native(bridge: Any, action: Any) -> str:
            state = bridge.env.get_state(wait_to_stabilize=False)
            pixels = np.asarray(state.pixels)
            height, width = pixels.shape[:2]
            mapped = native.map(
                action, screen_width=int(width), screen_height=int(height)
            )
            bridge.log.write("L1", "parsed_action", **mapped.audit_record())
            if mapped.is_terminal:
                raise RuntimeError("Terminal actions are handled by MultiAgent")
            if mapped.upstream_name == "take_note":
                # MultiAgent consumes take_note before environment execution.
                raise RuntimeError("take_note unexpectedly reached environment bridge")
            bridge.log.write(
                "L2", "environment_action_start",
                native_action_index=bridge.native_actions,
                canonical=mapped.canonical, bridge_action=mapped.bridge_action,
                screen_size=[int(width), int(height)],
            )
            if mapped.canonical is not None:
                android_action = android_adapter.map_action(
                    mapped.canonical, screen_width=int(width), screen_height=int(height)
                )
                android_adapter.execute(bridge.env, android_action)
            elif mapped.bridge_action is not None:
                from android_world.env import adb_utils

                if mapped.bridge_action["type"] == "key":
                    command = ["shell", "input", "keyevent", mapped.bridge_action["text"]]
                elif mapped.bridge_action["type"] == "open_package":
                    command = [
                        "shell", "monkey", "-p", mapped.bridge_action["package"],
                        "-c", "android.intent.category.LAUNCHER", "1",
                    ]
                else:  # pragma: no cover - adapter exhaustively validates.
                    raise ValueError(f"Unsupported bridge action: {mapped.bridge_action}")
                adb_utils.issue_generic_request(command, bridge.env.controller)
            else:  # pragma: no cover
                raise ValueError("Non-terminal action has no execution mapping")
            bridge.log.write(
                "L2", "environment_action_complete",
                native_action_index=bridge.native_actions,
            )
            bridge.native_actions += 1
            return ""

        self.bridge.execute_action = MethodType(execute_native, self.bridge)


__all__ = ["ARM_ID", "C0NativeMobileUseController", "MobileUseRunResult"]
