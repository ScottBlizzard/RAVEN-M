"""Task-literal-grounded generic completion policy for EEST-AC v0.2."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from raven_m.eest_ac.observation_v0_2 import ObservationFingerprint
from raven_m.eest_ac.task_roles import TaskRoleFrame


def _terms(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", value.casefold()))


@dataclass(frozen=True)
class CompletionResult:
    satisfied: bool
    reason: str


class CompletionPolicyV02:
    """Close only deterministic requirements derived from exact task spans."""

    @staticmethod
    def _screen_matches_target(
        target: str,
        observation: ObservationFingerprint,
    ) -> bool:
        target_terms = _terms(target)
        if not target_terms or not observation.a11y_available:
            return False
        haystack = " ".join(
            (*observation.visible_texts, *observation.package_names)
        ).casefold()
        return all(term in haystack for term in target_terms)

    def current_screen_satisfies(
        self,
        *,
        frame: TaskRoleFrame,
        observation: ObservationFingerprint,
    ) -> CompletionResult:
        if frame.intent != "open_target" or frame.destination is None:
            return CompletionResult(False, "no_deterministic_current_screen_rule")
        if self._screen_matches_target(frame.destination.text, observation):
            return CompletionResult(True, "parsed_open_target_visible_on_stable_screen")
        return CompletionResult(False, "parsed_open_target_not_visible")

    def after_action_satisfies(
        self,
        *,
        frame: TaskRoleFrame,
        action: dict[str, Any],
        observation: ObservationFingerprint,
    ) -> CompletionResult:
        current = self.current_screen_satisfies(frame=frame, observation=observation)
        if current.satisfied:
            return current
        if frame.intent != "open_target" or frame.destination is None:
            return CompletionResult(False, "no_deterministic_action_rule")
        if action.get("type") != "open_app":
            return CompletionResult(False, "action_does_not_open_app")
        action_target = " ".join(str(action.get("app_name", "")).casefold().split())
        role_target = " ".join(frame.destination.text.casefold().split())
        if action_target != role_target:
            return CompletionResult(False, "open_app_target_mismatch")
        return CompletionResult(False, "target_action_executed_but_screen_unverified")
