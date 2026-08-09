"""B2 Clean MobileUse controller built on the frozen PF01 adapter.

The B2 arm intentionally keeps MobileUse's free-text trajectory/progress state.
It changes only implementation validity, auxiliary-call scheduling, and terminal
evidence handling so that a later memory intervention has a clean control.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from types import MethodType, SimpleNamespace
from typing import Any, Callable

import numpy as np

from .controller import MobileUseController, MobileUseRunResult, load_upstream


ARM_ID = "B2_CLEAN_MOBILEUSE_QWEN3VL32B_AW_HARD_DEV_S20260806_V1"
REFLECTION_CADENCE = 4
PROGRESS_CADENCE = 4
MAX_GLOBAL_CHECKS = 2


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _step_features(agent: Any) -> dict[str, Any]:
    step = agent.trajectory[-1]
    before = getattr(step, "curr_env_state", None)
    after = getattr(step, "exec_env_state", None)
    before_pixels = getattr(before, "pixels", None)
    after_pixels = getattr(after, "pixels", None)
    unchanged = None
    if before_pixels is not None and after_pixels is not None:
        unchanged = np.array_equal(np.asarray(before_pixels), np.asarray(after_pixels))
    before_package = getattr(before, "package", None)
    after_package = getattr(after, "package", None)
    package_changed = bool(
        before_package and after_package and before_package != after_package
    )
    action = getattr(step, "action", None)
    return {
        "step_index": int(getattr(step, "step_idx", len(agent.trajectory) - 1)),
        "action_name": getattr(action, "name", None),
        "screen_unchanged": unchanged,
        "before_package": before_package,
        "after_package": after_package,
        "package_changed": package_changed,
        "reflection_outcome": getattr(step, "reflection_outcome", None),
    }


def _reflector_schedule(features: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    step_number = features["step_index"] + 1
    if step_number == 1:
        reasons.append("first_action")
    if step_number % REFLECTION_CADENCE == 0:
        reasons.append("cadence")
    if features["screen_unchanged"] is True:
        reasons.append("screen_unchanged")
    if features["package_changed"]:
        reasons.append("package_changed")
    if features["action_name"] == "type":
        reasons.append("typed_value")
    return bool(reasons), reasons


def _progressor_schedule(features: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    step_number = features["step_index"] + 1
    if step_number == 1:
        reasons.append("first_action")
    if step_number % PROGRESS_CADENCE == 0:
        reasons.append("cadence")
    if features["package_changed"]:
        reasons.append("package_changed")
    if (
        features["action_name"] == "type"
        and features["reflection_outcome"] not in {"B", "C"}
    ):
        reasons.append("confirmed_type")
    return bool(reasons), reasons


class _ScheduledRoleVLM:
    """Skip deterministic auxiliary calls without pretending they were generated."""

    def __init__(
        self,
        base: Any,
        *,
        role: str,
        agent: Any,
        log: Any,
        schedule: Callable[[dict[str, Any]], tuple[bool, list[str]]],
    ) -> None:
        self.base = base
        self.role = role
        self.agent = agent
        self.log = log
        self.schedule = schedule

    def predict(self, messages: list[dict[str, Any]], stream: bool = False, **kwargs: Any) -> Any:
        features = _step_features(self.agent)
        generate, reasons = self.schedule(features)
        self.log.write(
            "L0",
            "role_schedule_decision",
            role=self.role,
            generate=generate,
            reasons=reasons or ["no_trigger"],
            **features,
        )
        if generate:
            return self.base.predict(messages, stream=stream, **kwargs)

        if self.role == "Reflector":
            content = (
                "### Outcome ###\nSKIPPED\n"
                "### Error Description ###\nNone\n"
                "### Explanation ###\nNo frozen B2 reflection trigger fired."
            )
        elif self.role == "Progressor":
            previous = ""
            if len(self.agent.trajectory) > 1:
                previous = getattr(self.agent.trajectory[-2], "progress", None) or ""
            content = f"### Completed contents ###\n{previous}"
        else:  # pragma: no cover - construction rejects this branch.
            raise ValueError(f"Unsupported scheduled role: {self.role}")
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content), logprobs=None)],
            usage={},
            model=getattr(self.base.client, "model_id", None),
        )


class _DormantUpstreamVLM:
    """Avoid constructing unused OpenAI clients before audited VLM injection."""

    def __init__(self, **kwargs: Any) -> None:
        self.config = dict(kwargs)

    def predict(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        raise RuntimeError("Dormant upstream VLM must be replaced before execution")


class CleanMobileUseController(MobileUseController):
    """PF01 plus pre-registered reliability and cost-control policies."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Upstream constructs seven standalone OpenAI clients and PF01 replaces
        # all of them immediately with the audited local transport. Suppress
        # that unused construction in B2; the finally block prevents global
        # import state from leaking to another controller.
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
        # The parent writes no event before ``run``. Rebinding here gives every
        # B2 event a distinct arm id while retaining the audited transport.
        self.log.arm_id = ARM_ID
        self._global_veto_count = 0

        from mobile_use.schema.schema import Action

        # PF01 returned an empty action after three parser failures. That empty
        # trajectory entry later crashed the upstream trajectory detector. B2
        # converts parser exhaustion into an explicit, valid task failure.
        parent_parse = self.agent.operator.parse_response

        def parse_operator(_instance: Any, content: str, *p_args: Any, **p_kwargs: Any) -> Any:
            parsed = parent_parse(content, *p_args, **p_kwargs)
            if parsed[1] is not None:
                return parsed
            action = Action(name="terminate", parameters={"status": "failure"})
            action_s = json.dumps(
                {"name": "mobile_use", "arguments": {"action": "terminate", "status": "failure"}},
                sort_keys=True,
            )
            self.log.write(
                "L1",
                "operator_fail_closed",
                reason="three_total_parse_attempts_exhausted",
                terminal_status="failure",
            )
            return "Parser exhausted; fail closed.", action, action_s, "Terminate with failure."

        self.agent.operator.parse_response = MethodType(parse_operator, self.agent.operator)

        # A failed environment action can also leave an empty historical action.
        # Filter only inside the detector; the original trajectory remains intact
        # for auditing and for the model-visible history.
        parent_detect = self.agent.trajectory_reflector.detect

        def safe_detect(_instance: Any, episode_data: Any) -> list[str]:
            valid_steps = [
                step for step in episode_data.trajectory
                if getattr(step, "action", None) is not None
                and getattr(step, "exec_env_state", None) is not None
            ]
            omitted = len(episode_data.trajectory) - len(valid_steps)
            if omitted:
                self.log.write(
                    "L3",
                    "trajectory_detector_omitted_invalid_steps",
                    omitted=omitted,
                    total=len(episode_data.trajectory),
                )
            proxy = SimpleNamespace(trajectory=valid_steps)
            return parent_detect(proxy)

        self.agent.trajectory_reflector.detect = MethodType(
            safe_detect, self.agent.trajectory_reflector
        )

        self.agent.reflector.vlm = _ScheduledRoleVLM(
            self.agent.reflector.vlm,
            role="Reflector",
            agent=self.agent,
            log=self.log,
            schedule=_reflector_schedule,
        )
        self.agent.progressor.vlm = _ScheduledRoleVLM(
            self.agent.progressor.vlm,
            role="Progressor",
            agent=self.agent,
            log=self.log,
            schedule=_progressor_schedule,
        )

        # Treat uncertainty and malformed terminal judgments as vetoes. A veto
        # can be issued twice; the third finish claim is allowed to terminate so
        # this policy cannot create an unbounded review loop.
        parent_global_parse = self.agent.global_reflector.parse_response

        def parse_global(_instance: Any, content: str) -> tuple[str, str]:
            result, reason = parent_global_parse(content)
            normalized = result.strip().lower()
            if normalized.startswith("success"):
                return "Success", reason
            if normalized.startswith("failed"):
                return "Failed", reason
            self.log.write(
                "L5",
                "completion_uncertain_veto",
                raw_result=result,
                reason=reason,
            )
            return "Failed (uncertain or malformed)", reason

        self.agent.global_reflector.parse_response = MethodType(
            parse_global, self.agent.global_reflector
        )

        parent_step = self.agent.step

        def clean_step(agent_instance: Any) -> Any:
            if (
                agent_instance.status is None
                and agent_instance.episode_data.finish_count > 0
                and self._global_veto_count < MAX_GLOBAL_CHECKS
            ):
                self.log.write(
                    "L5",
                    "completion_recheck_armed",
                    prior_finish_count=agent_instance.episode_data.finish_count,
                    prior_veto_count=self._global_veto_count,
                )
                agent_instance.episode_data.finish_count = 0
            step = parent_step()
            if getattr(step, "evaluation_result", None) is not None:
                self._global_veto_count += 1
            return step

        self.agent.step = MethodType(clean_step, self.agent)
        self._adapt_b2_prompts()

    def _adapt_b2_prompts(self) -> None:
        changes: list[dict[str, str]] = []

        def append(role: str, prompt: Any, field: str, addition: str) -> None:
            before = getattr(prompt, field)
            after = before.rstrip() + "\n\n" + addition.strip() + "\n"
            setattr(prompt, field, after)
            changes.append({
                "role": role,
                "field": field,
                "before_sha256": _digest(before),
                "after_sha256": _digest(after),
            })

        append(
            "Operator",
            self.agent.operator.prompt,
            "response_prompt",
            """### Completion integrity
Terminate with success only after the current UI visibly verifies the requested result wherever the app permits verification. An intended action, action description, reflection, or progress summary is not proof. If the result is uncertain, inspect the relevant detail or list state before terminating.""",
        )
        append(
            "Reflector",
            self.agent.reflector.prompt,
            "response_prompt",
            """A visible screen change alone does not prove the intended state change. Judge whether the before/after evidence supports the stated action effect; otherwise choose an error outcome.""",
        )
        append(
            "Progressor",
            self.agent.progressor.prompt,
            "continue_progress_response",
            """Do not turn an intended action into a completed fact. Preserve earlier progress when the latest effect is unverified or the reflector reports failure.""",
        )
        append(
            "GlobalReflector",
            self.agent.global_reflector.prompt,
            "response_prompt",
            """Only screenshot-visible state is completion evidence. Thoughts, action descriptions, progress summaries, and prior finish claims are not evidence. If any required predicate cannot be verified from the screenshots, return Uncertain rather than Success.""",
        )
        path = Path(self.episode_dir) / "b2_prompt_changes.json"
        path.write_text(
            json.dumps(changes, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


__all__ = ["ARM_ID", "CleanMobileUseController", "MobileUseRunResult"]
