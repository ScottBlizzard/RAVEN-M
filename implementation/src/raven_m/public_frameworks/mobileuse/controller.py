"""Wrapper around the locked upstream MobileUse MultiAgent schedule."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import sys
from types import MethodType, SimpleNamespace
from typing import Any

import numpy as np
from PIL import Image

from raven_m.env.androidworld_adapter import AndroidWorldAdapter
from raven_m.models.vllm_multi_image_client import VLLMMultiImageClient

from .action_adapter import MobileUseActionAdapter
from .logging import LayeredEventLog
from .prompt_adapter import adapt_prompts, write_prompt_change_manifest


ARM_ID = "PF01_MOBILEUSE_HR_QWEN3VL32B_AW_HARD_S20260806_V1"
EXPECTED_ROLES = (
    "Operator", "Reflector", "Progressor", "TrajectoryReflector",
    "AnswerAgent", "GlobalReflector",
)
ROLE_IMAGE_LIMITS = {
    "Operator": (1, 1),
    "Reflector": (2, 2),
    "Progressor": (0, 0),
    "TrajectoryReflector": (0, 0),
    "AnswerAgent": (1, 1),
    "GlobalReflector": (1, 3),
}


def _vendor_root() -> Path:
    return Path(__file__).resolve().parents[4] / "third_party" / "mobile_use" / "upstream"


def load_upstream() -> tuple[Any, Any]:
    root = _vendor_root()
    if not root.is_dir():
        raise RuntimeError(f"Locked MobileUse source is missing: {root}")
    module = sys.modules.get("mobile_use")
    if module is not None:
        location = Path(getattr(module, "__file__", "")).resolve()
        if root not in location.parents:
            raise RuntimeError(f"Uncontrolled mobile_use import: {location}")
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from mobile_use.agents.multi_agent import MultiAgent
    from mobile_use.schema.schema import EnvState

    return MultiAgent, EnvState


def _image_count(messages: list[dict[str, Any]]) -> int:
    return sum(
        1
        for message in messages
        for item in (message.get("content") if isinstance(message.get("content"), list) else [])
        if item.get("type") == "image_url"
    )


class AuditedRoleVLM:
    """Expose the upstream `predict` API while using the frozen client."""

    def __init__(
        self,
        client: VLLMMultiImageClient,
        *,
        role: str,
        episode_id: str,
        log: LayeredEventLog,
        max_tokens: int = 32768,
    ) -> None:
        if role not in ROLE_IMAGE_LIMITS:
            raise ValueError(f"Unregistered MobileUse role: {role}")
        self.client = client
        self.role = role
        self.episode_id = episode_id
        self.log = log
        self.max_tokens = max_tokens
        self.call_index = 0

    def predict(self, messages: list[dict[str, Any]], stream: bool = False, **kwargs: Any) -> Any:
        if stream:
            raise ValueError("Streaming is disabled in the frozen arm")
        unexpected = set(kwargs) - {"logprobs"}
        if unexpected:
            raise ValueError(f"Unfrozen VLM arguments: {sorted(unexpected)!r}")
        if kwargs.get("logprobs"):
            raise ValueError("reflect_on_demand/logprobs must remain disabled")
        count = _image_count(messages)
        minimum, maximum = ROLE_IMAGE_LIMITS[self.role]
        if not minimum <= count <= maximum:
            raise ValueError(
                f"{self.role} requires {minimum}..{maximum} image(s), received {count}"
            )
        call_label = f"{self.role.lower()}_{self.call_index:04d}"
        self.log.write(
            "L0", "model_request", role=self.role, call_label=call_label,
            image_count=count,
        )
        call = self.client.generate_messages(
            messages=messages,
            episode_id=self.episode_id,
            call_label=call_label,
            role=self.role,
            expected_images=count,
            max_tokens=self.max_tokens,
        )
        self.call_index += 1
        self.log.write("L0", "model_response", role=self.role, **call.audit_record())
        if self.role in {"Reflector", "Progressor", "TrajectoryReflector", "GlobalReflector"}:
            self.log.write(
                "L3", "auxiliary_role_response", role=self.role,
                call_id=call.call_id, content=call.content,
            )
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content=call.content),
                logprobs=None,
            )],
            usage=call.usage,
            model=self.client.model_id,
        )


class AndroidWorldEnvironmentBridge:
    """Provide only screenshot/package/time to MobileUse; keep audit data separate."""

    def __init__(
        self,
        env: Any,
        *,
        env_state_class: Any,
        episode_dir: Path,
        log: LayeredEventLog,
    ) -> None:
        self.env = env
        self.env_state_class = env_state_class
        self.episode_dir = Path(episode_dir)
        self.episode_dir.mkdir(parents=True, exist_ok=True)
        self.log = log
        self.action_adapter = MobileUseActionAdapter()
        self.android_adapter = AndroidWorldAdapter()
        self.snapshot_index = 0
        self.native_actions = 0

    @staticmethod
    def _ui_records(state: Any) -> list[dict[str, Any]]:
        records = []
        for element in getattr(state, "ui_elements", ()) or ():
            if isinstance(element, dict):
                records.append({str(k): repr(v) if not isinstance(v, (str, int, float, bool, type(None))) else v for k, v in element.items()})
            else:
                records.append({
                    key: repr(value) if not isinstance(value, (str, int, float, bool, type(None))) else value
                    for key, value in vars(element).items() if not key.startswith("_")
                })
        return records

    def _device_time(self) -> str | None:
        try:
            from android_world.env import adb_utils

            response = adb_utils.issue_generic_request(
                ["shell", "date"], self.env.controller, timeout_sec=10.0
            )
            output = getattr(getattr(response, "generic", None), "output", b"")
            return output.decode(errors="replace").strip() or None
        except Exception:
            return None

    def _foreground_package(self, fallback: str | None) -> str | None:
        try:
            from android_env.proto import adb_pb2
            from android_world.env import adb_utils

            activity, response = adb_utils.get_current_activity(
                self.env.controller, timeout_sec=10.0
            )
            if response.status == adb_pb2.AdbResponse.Status.OK and activity:
                return activity.split("/", 1)[0]
        except Exception:
            pass
        return fallback

    def get_state(self) -> Any:
        state = self.env.get_state(wait_to_stabilize=True)
        pixels = np.asarray(state.pixels)
        image = Image.fromarray(pixels).convert("RGB")
        label = f"snapshot_{self.snapshot_index:05d}"
        screenshot = self.episode_dir / f"{label}.png"
        image.save(screenshot)
        ui_records = self._ui_records(state)
        ui_path = self.episode_dir / f"{label}.ui.json"
        ui_path.write_text(
            json.dumps(ui_records, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        packages = sorted({
            str(record.get("package_name") or record.get("package") or "")
            for record in ui_records
            if record.get("package_name") or record.get("package")
        })
        fallback_package = packages[0] if len(packages) == 1 else None
        foreground_package = self._foreground_package(fallback_package)
        self.log.write(
            "L2", "environment_snapshot", snapshot_index=self.snapshot_index,
            screenshot=str(screenshot.name), screenshot_sha256=sha256(screenshot.read_bytes()).hexdigest(),
            pixel_sha256=sha256(pixels.tobytes()).hexdigest(), ui_record=ui_path.name,
            ui_node_count=len(ui_records), ui_packages=packages,
            foreground_package=foreground_package,
            model_accessible_fields=["pixels", "package", "device_time"],
            model_accessible_a11y_tree=False,
        )
        self.snapshot_index += 1
        # Crucial isolation boundary: audit UI records are never attached here.
        return self.env_state_class(
            pixels=image,
            package=foreground_package,
            a11y_tree=None,
            device_time=self._device_time(),
        )

    def execute_action(self, action: Any) -> str:
        mapped = self.action_adapter.map(action)
        self.log.write("L1", "parsed_action", **mapped.audit_record())
        if mapped.is_terminal or mapped.canonical is None:
            raise RuntimeError("Terminal actions must be handled by the upstream controller")
        state = self.env.get_state(wait_to_stabilize=False)
        pixels = np.asarray(state.pixels)
        screen_height, screen_width = pixels.shape[:2]
        android_action = self.android_adapter.map_action(
            mapped.canonical,
            screen_width=screen_width,
            screen_height=screen_height,
        )
        self.log.write("L2", "environment_action_start", native_action_index=self.native_actions, **android_action.audit_record())
        self.android_adapter.execute(self.env, android_action)
        self.log.write("L2", "environment_action_complete", native_action_index=self.native_actions)
        self.native_actions += 1
        return ""


@dataclass
class MobileUseRunResult:
    episode_data: Any
    answer: str | None
    native_actions: int
    log_path: Path


class MobileUseController:
    """Construct and run the exact locked upstream controller with adapters."""

    def __init__(
        self,
        client: VLLMMultiImageClient,
        *,
        env: Any,
        episode_id: str,
        episode_dir: Path,
        max_steps: int,
        max_tokens: int = 32768,
    ) -> None:
        MultiAgent, EnvState = load_upstream()
        self.episode_dir = Path(episode_dir)
        self.episode_dir.mkdir(parents=True, exist_ok=True)
        self.log = LayeredEventLog(
            self.episode_dir / "events.jsonl", arm_id=ARM_ID, episode_id=episode_id
        )
        dummy_vlm = {
            "model_name": client.model_id,
            "api_key": "local-no-external-network",
            "base_url": client.base_url,
            "max_retry": 3,
            "retry_waiting_seconds": 2,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }
        self.agent = MultiAgent(
            vlm=dummy_vlm,
            max_steps=int(max_steps),
            max_action_retry=3,
            reflect_on_demand=False,
            enable_pre_reflection=True,
            planner=None,
            note_taker=None,
            operator={"enabled": True, "name": "Operator", "prompt_config": "operator.yaml", "include_a11y_tree": False, "knowledge": None},
            answer_agent={"enabled": True, "name": "AnswerAgent", "prompt_config": "answer_agent.yaml", "knowledge": None},
            reflector={"enabled": True, "prompt_config": "reflector.yaml"},
            trajectory_reflector={
                "enabled": True, "prompt_config": "trajectory_reflector.yaml",
                "evoke_every_steps": 5, "cold_steps": 3, "detect_error": True,
                "num_histories": "auto", "num_latest_screenshots": 0,
                "max_repeat_action": 3, "max_repeat_action_series": 2,
                "max_repeat_screen": 3, "max_fail_count": 3,
            },
            global_reflector={"enabled": True, "prompt_config": "global_reflector.yaml", "num_latest_screenshots": 3},
            progressor={"enabled": True, "prompt_config": "progressor.yaml"},
        )
        role_objects = {
            "Operator": self.agent.operator,
            "Reflector": self.agent.reflector,
            "Progressor": self.agent.progressor,
            "TrajectoryReflector": self.agent.trajectory_reflector,
            "AnswerAgent": self.agent.answer_agent,
            "GlobalReflector": self.agent.global_reflector,
        }
        enabled = tuple(name for name, value in role_objects.items() if value is not None)
        if enabled != EXPECTED_ROLES:
            raise RuntimeError(f"Enabled role drift: {enabled!r}")
        if self.agent.planner is not None or self.agent.note_taker is not None:
            raise RuntimeError("Prohibited MobileUse role was instantiated")
        # The root agent's generic VLM and alternative class registry are not
        # used by MultiAgent.step. Remove them so only the six selected role
        # wrappers remain reachable during a scored episode.
        self.agent.vlm = None
        self.agent.subagent_map = {
            "Operator": type(self.agent.operator),
            "AnswerAgent": type(self.agent.answer_agent),
        }
        changes = adapt_prompts(self.agent.operator.prompt, self.agent.answer_agent.prompt)
        write_prompt_change_manifest(self.episode_dir / "prompt_changes.json", changes)
        for role, role_object in role_objects.items():
            role_object.vlm = AuditedRoleVLM(
                client, role=role, episode_id=episode_id, log=self.log,
                max_tokens=max_tokens,
            )
        # Keep the released parser and correction loop, but normalize its
        # coordinate size and reject privileged or multiple tool calls.
        action_adapter = MobileUseActionAdapter()
        original_parse = self.agent.operator.parse_response
        parse_attempt = 0

        def parse_operator(_instance: Any, content: str, *args: Any, **kwargs: Any) -> Any:
            nonlocal parse_attempt
            parse_attempt += 1
            try:
                action_adapter.assert_single_action_output(content)
                parsed = original_parse(
                    content, size=(999, 999), raw_size=(999, 999)
                )
                mapped = action_adapter.map(parsed[1])
                if mapped.upstream_name == "answer":
                    raise ValueError(
                        "Operator answer is role-invalid; terminate and use AnswerAgent"
                    )
            except Exception as exc:
                self.log.write(
                    "L1", "operator_parse_invalid", attempt=parse_attempt,
                    raw_output=content, error=f"{type(exc).__name__}: {exc}",
                )
                if parse_attempt >= 3:
                    parse_attempt = 0
                    self.log.write(
                        "L1", "operator_output_invalid",
                        reason="three_total_parse_attempts_exhausted",
                    )
                    # The released loop would otherwise request an unused fourth
                    # response. Returning no action consumes the native decision
                    # without executing the environment.
                    return None, None, None, None
                raise
            self.log.write(
                "L1", "operator_parse_valid", attempt=parse_attempt,
                raw_output=content, action=repr(parsed[1]),
            )
            parse_attempt = 0
            return parsed

        self.agent.operator.parse_response = MethodType(parse_operator, self.agent.operator)
        original_answer_parse = self.agent.answer_agent.parse_response

        def parse_answer(_instance: Any, content: str, *args: Any, **kwargs: Any) -> Any:
            action_adapter.assert_single_action_output(content)
            parsed = original_answer_parse(content, size=(999, 999), raw_size=(999, 999))
            mapped = action_adapter.map(parsed[1])
            if mapped.upstream_name != "answer":
                raise ValueError("AnswerAgent may emit only answer")
            return parsed

        self.agent.answer_agent.parse_response = MethodType(parse_answer, self.agent.answer_agent)
        self.bridge = AndroidWorldEnvironmentBridge(
            env, env_state_class=EnvState, episode_dir=self.episode_dir, log=self.log
        )
        self.agent.env = self.bridge
        self.env = env
        self.android_adapter = AndroidWorldAdapter()

    def run(self, goal: str) -> MobileUseRunResult:
        self.log.write("L0", "episode_start", goal=goal, max_steps=self.agent.max_steps)
        self.agent.reset(goal=goal)
        episode_data = self.agent.episode_data
        for step_index in range(self.agent.max_steps):
            self.agent.curr_step_idx = step_index
            step_data = self.agent.step()
            episode_data.num_steps = step_index + 1
            episode_data.status = self.agent.status
            self.log.write(
                "L1", "operator_decision_complete", step_index=step_index,
                action=repr(getattr(step_data, "action", None)),
                status=repr(self.agent.status),
            )
            before_state = getattr(step_data, "curr_env_state", None)
            after_state = getattr(step_data, "exec_env_state", None)
            before_pixels = getattr(before_state, "pixels", None)
            after_pixels = getattr(after_state, "pixels", None)
            before_hash = (
                sha256(before_pixels.tobytes()).hexdigest()
                if before_pixels is not None else None
            )
            after_hash = (
                sha256(after_pixels.tobytes()).hexdigest()
                if after_pixels is not None else None
            )
            self.log.write(
                "L4", "step_progress_state", step_index=step_index,
                before_package=getattr(before_state, "package", None),
                after_package=getattr(after_state, "package", None),
                before_pixel_sha256=before_hash,
                after_pixel_sha256=after_hash,
                screenshot_changed=(
                    before_hash != after_hash
                    if before_hash is not None and after_hash is not None
                    else None
                ),
                progress=getattr(step_data, "progress", None),
                reflection_outcome=getattr(step_data, "reflection_outcome", None),
                reflection_error=getattr(step_data, "reflection_error", None),
                trajectory_reflection_outcome=getattr(
                    step_data, "trajectory_reflection_outcome", None
                ),
                trajectory_reflection_error=getattr(
                    step_data, "trajectory_reflection_error", None
                ),
                global_evaluation_result=getattr(
                    step_data, "evaluation_result", None
                ),
                global_evaluation_reason=getattr(
                    step_data, "evaluation_reason", None
                ),
            )
            status_name = getattr(self.agent.status, "name", None)
            if status_name in {"FINISHED", "FAILED"}:
                episode_data.message = f"Agent status: {status_name}"
                break
        else:
            episode_data.message = "Agent reached frozen native decision budget"
        answer = None
        if episode_data.trajectory:
            answer = episode_data.trajectory[-1].answer
        if answer is not None:
            mapped = self.android_adapter.map_action(
                {"type": "answer", "text": answer}, screen_width=1, screen_height=1
            )
            self.android_adapter.execute(self.env, mapped)
            self.log.write("L5", "answer_submitted", answer=answer)
        self.log.write(
            "L5", "controller_terminal", status=repr(episode_data.status),
            message=episode_data.message, answer=answer,
            native_actions=self.bridge.native_actions,
        )
        return MobileUseRunResult(
            episode_data=episode_data,
            answer=answer,
            native_actions=self.bridge.native_actions,
            log_path=self.log.path,
        )
