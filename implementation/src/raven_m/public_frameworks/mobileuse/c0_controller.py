"""C0: released MobileUse MultiAgent protocol on the required Qwen3-VL-32B.

C0 adds no RAVEN-M memory mechanism.  It restores the released prompts,
six-role schedule, coordinate scaling, and action space that PF01/B2 had
constrained, while retaining audited transport/logging and fail-closed crash
containment.
"""

from __future__ import annotations

import base64
from hashlib import sha256
import json
from pathlib import Path
import time
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


class _C0RequestCaptureVLM:
    """Persist exact dynamic prompt text and ordered image placeholders."""

    def __init__(self, base: Any, *, role: str, episode_dir: Path, log: Any) -> None:
        self.base = base
        self.role = role
        self.log = log
        self.episode_dir = Path(episode_dir)
        self.directory = self.episode_dir / "model_requests"
        self.directory.mkdir(parents=True, exist_ok=True)

    def predict(self, messages: list[dict[str, Any]], stream: bool = False, **kwargs: Any) -> Any:
        call_index = int(getattr(self.base, "call_index", 0))
        label = f"{self.role.lower()}_{call_index:04d}"
        captured: list[dict[str, Any]] = []
        for message in messages:
            content = message.get("content")
            if isinstance(content, str):
                captured.append({"role": message.get("role"), "content": content})
                continue
            items = []
            for item in content or []:
                if item.get("type") == "text":
                    items.append({"type": "text", "text": item.get("text")})
                else:
                    url = (item.get("image_url") or {}).get("url", "")
                    items.append({
                        "type": "image_url",
                        "data_url_sha256": sha256(url.encode("utf-8")).hexdigest(),
                    })
            captured.append({"role": message.get("role"), "content": items})
        path = self.directory / f"{label}.json"
        payload = json.dumps(captured, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        path.write_text(payload, encoding="utf-8")
        self.log.write(
            "L0", "model_request_payload", role=self.role, call_label=label,
            path=str(path.relative_to(self.episode_dir)),
            sha256=sha256(payload.encode("utf-8")).hexdigest(),
        )
        return self.base.predict(messages, stream=stream, **kwargs)


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

        for role, role_object in {
            "Operator": self.agent.operator,
            "Reflector": self.agent.reflector,
            "Progressor": self.agent.progressor,
            "TrajectoryReflector": self.agent.trajectory_reflector,
            "AnswerAgent": self.agent.answer_agent,
            "GlobalReflector": self.agent.global_reflector,
        }.items():
            role_object.vlm = _C0RequestCaptureVLM(
                role_object.vlm, role=role, episode_dir=Path(self.episode_dir), log=self.log
            )

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
                self.log.write(
                    "L1", "operator_native_retry_exhausted",
                    reason="consume_step_without_action_then_allow_recovery",
                )
                return None, None, None, None
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

        # The released controller allows one parse-exhausted step to recover on
        # the next decision, but its trajectory detector can dereference that
        # empty action. Filter only the detector's read-only proxy; preserve the
        # original trajectory and model-visible history unchanged.
        raw_detect = self.agent.trajectory_reflector.detect

        def safe_detect(_instance: Any, episode_data: Any) -> list[str]:
            valid = [
                step for step in episode_data.trajectory
                if getattr(step, "action", None) is not None
                and getattr(step, "exec_env_state", None) is not None
            ]
            omitted = len(episode_data.trajectory) - len(valid)
            if omitted:
                from types import SimpleNamespace
                self.log.write(
                    "L3", "trajectory_detector_omitted_invalid_steps",
                    omitted=omitted, total=len(episode_data.trajectory),
                )
                return raw_detect(SimpleNamespace(trajectory=valid))
            return raw_detect(episode_data)

        self.agent.trajectory_reflector.detect = MethodType(
            safe_detect, self.agent.trajectory_reflector
        )

        self.bridge.action_adapter = native
        self.bridge.execution_errors = []
        android_adapter = AndroidWorldAdapter()

        def execute_native(bridge: Any, action: Any) -> str:
            from android_world.env import adb_utils

            def issue_checked(command: list[str], label: str) -> Any:
                response = adb_utils.issue_generic_request(
                    command, bridge.env.controller, timeout_sec=60.0
                )
                adb_utils.check_ok(response, label)
                return response

            try:
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
                    raise RuntimeError("take_note unexpectedly reached environment bridge")
                action_index = bridge.native_actions
                bridge.log.write(
                    "L2", "environment_action_start",
                    native_action_index=action_index,
                    canonical=mapped.canonical, bridge_action=mapped.bridge_action,
                    screen_size=[int(width), int(height)],
                )

                # MobileUse types without pressing Enter. AndroidWorld's
                # generic input_text action presses Enter, so C0 uses checked
                # ADB calls for the entire physical action vocabulary.
                if mapped.upstream_name == "type":
                    text = mapped.upstream_parameters["text"]
                    if any(ord(char) > 127 for char in text):
                        encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
                        for command in (
                            ["shell", "ime", "enable", "com.android.adbkeyboard/.AdbIME"],
                            ["shell", "ime", "set", "com.android.adbkeyboard/.AdbIME"],
                        ):
                            issue_checked(command, "C0 could not enable ADB keyboard")
                        # The IME selection acknowledgement can precede the
                        # service binding on a freshly restored emulator.
                        time.sleep(3.0)
                        issue_checked(
                            ["shell", "am", "broadcast", "-a", "ADB_INPUT_B64", "--es", "msg", encoded],
                            "C0 non-ASCII input broadcast failed",
                        )
                        time.sleep(1.0)
                        issue_checked(
                            ["shell", "ime", "disable", "com.android.adbkeyboard/.AdbIME"],
                            "C0 could not restore keyboard after typing",
                        )
                    else:
                        issue_checked(
                            ["shell", "input", "text", text],
                            "C0 ASCII input failed",
                        )
                    time.sleep(len(text) * 0.1)
                elif mapped.upstream_name == "clear_text":
                    # Exact released MobileUse ADB-keyboard clear sequence. An
                    # empty AndroidWorld input_text action is a silent no-op.
                    commands = (
                        # ``d.shell([..., " "])`` in released MobileUse keeps
                        # a literal-space argv. The generic adb bridge would
                        # collapse it to an empty argument, so use Android's
                        # documented input-text space escape instead.
                        ["shell", "input", "text", "%s"],
                        ["shell", "ime", "enable", "com.android.adbkeyboard/.AdbIME"],
                        ["shell", "ime", "set", "com.android.adbkeyboard/.AdbIME"],
                    )
                    for command in commands:
                        issue_checked(command, "C0 clear-text preparation failed")
                    # ``ime set`` returns before the newly selected input
                    # method is necessarily bound to the focused EditText.
                    # A first activation on the benchmark emulator took just
                    # over one second and silently ignored ADB_CLEAR_TEXT.
                    # Keep the released action semantics, but wait for the
                    # keyboard service to be ready instead of racing it.
                    time.sleep(3.0)
                    issue_checked(
                        ["shell", "am", "broadcast", "-a", "ADB_CLEAR_TEXT"],
                        "C0 clear-text broadcast failed",
                    )
                    time.sleep(1.0)
                    issue_checked(
                        ["shell", "ime", "disable", "com.android.adbkeyboard/.AdbIME"],
                        "C0 could not restore keyboard after clear_text",
                    )
                elif mapped.canonical is not None:
                    android_action = android_adapter.map_action(
                        mapped.canonical, screen_width=int(width), screen_height=int(height)
                    )
                    canonical_type = mapped.canonical["type"]
                    actual = android_action.actual_pixels
                    if canonical_type == "tap":
                        issue_checked(
                            ["shell", "input", "tap", str(actual["x"]), str(actual["y"])],
                            "C0 click failed",
                        )
                    elif canonical_type in {"long_press", "swipe"}:
                        x2 = actual["x"] if canonical_type == "long_press" else actual["x2"]
                        y2 = actual["y"] if canonical_type == "long_press" else actual["y2"]
                        issue_checked(
                            adb_utils.generate_swipe_command(
                                actual["x"], actual["y"], x2, y2,
                                mapped.canonical["duration_ms"],
                            ),
                            f"C0 {canonical_type} failed",
                        )
                    elif canonical_type == "press_back":
                        issue_checked(["shell", "input", "keyevent", "BACK"], "C0 Back failed")
                    elif canonical_type == "press_home":
                        issue_checked(["shell", "input", "keyevent", "HOME"], "C0 Home failed")
                    elif canonical_type == "press_enter":
                        issue_checked(["shell", "input", "keyevent", "ENTER"], "C0 Enter failed")
                    elif canonical_type == "wait":
                        time.sleep(mapped.canonical["duration_ms"] / 1000.0)
                    elif canonical_type == "answer":
                        bridge.env.interaction_cache = mapped.canonical["text"]
                    else:  # pragma: no cover - adapter is exhaustive.
                        raise ValueError(f"Unsupported checked C0 action: {canonical_type}")
                elif mapped.bridge_action is not None:
                    if mapped.bridge_action["type"] == "key":
                        # A hallucinated key token is a model-action failure,
                        # not an infrastructure invalidity. ADB generally
                        # returns OK/no-op; a rejected token is logged below.
                        issue_checked(
                            ["shell", "input", "keyevent", mapped.bridge_action["text"]],
                            "C0 key transport/execution failed",
                        )
                        model_rejection = None
                        command = None
                    elif mapped.bridge_action["type"] == "open_app_name":
                        app_name = mapped.bridge_action["text"]
                        activity = adb_utils.get_adb_activity(app_name)
                        if activity is not None:
                            issue_checked(
                                ["shell", "am", "start", "-W", "-n", activity],
                                "C0 known-app launch failed",
                            )
                            expected_package = activity.split("/", 1)[0]
                            command = None
                            model_rejection = None
                        else:
                            command = ["shell", "monkey", "-p", app_name, "1"]
                            expected_package = app_name
                            model_rejection = None
                    else:  # pragma: no cover - adapter exhaustively validates.
                        raise ValueError(f"Unsupported bridge action: {mapped.bridge_action}")
                    if command is not None:
                        issue_checked(command, "C0 open transport/execution failed")
                    if mapped.bridge_action["type"] == "open_app_name" and model_rejection is None:
                        for _ in range(10):
                            current, response = adb_utils.get_current_activity(
                                bridge.env.controller, timeout_sec=10.0
                            )
                            adb_utils.check_ok(response, "C0 foreground verification failed")
                            if current and current.split("/", 1)[0] == expected_package:
                                break
                            time.sleep(0.5)
                        else:
                            if activity is None:
                                model_rejection = (
                                    f"open target {app_name!r} did not foreground an installed package"
                                )
                            else:
                                raise RuntimeError(
                                    f"C0 known app did not foreground {expected_package!r}; current={current!r}"
                                )
                    if model_rejection is not None:
                        bridge.log.write(
                            "L2", "environment_model_action_rejected",
                            native_action_index=action_index,
                            reason=model_rejection,
                        )
                else:  # pragma: no cover
                    raise ValueError("Non-terminal action has no execution mapping")
                bridge.log.write(
                    "L2", "environment_action_complete",
                    native_action_index=action_index,
                    outcome="model_action_rejected" if locals().get("model_rejection") else "executed",
                )
                bridge.native_actions += 1
                time.sleep(2.0)
                return ""
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                bridge.execution_errors.append(error)
                bridge.log.write(
                    "L2", "environment_action_error",
                    native_action_index=bridge.native_actions, error=error,
                )
                raise

        self.bridge.execute_action = MethodType(execute_native, self.bridge)

        native_step = self.agent.step

        def stop_on_environment_error(_agent: Any) -> Any:
            step = native_step()
            if self.bridge.execution_errors:
                raise RuntimeError(
                    "C0 environment execution invalid: "
                    + self.bridge.execution_errors[-1]
                )
            return step

        self.agent.step = MethodType(stop_on_environment_error, self.agent)


__all__ = ["ARM_ID", "C0NativeMobileUseController", "MobileUseRunResult"]
