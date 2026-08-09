"""Fail-closed mapping from MobileUse actions to RAVEN canonical actions."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping


COORDINATE_MAX = 999
ALLOWED_UPSTREAM_ACTIONS = frozenset(
    {"click", "swipe", "type", "system_button", "answer", "terminate"}
)
PROHIBITED_ACTIONS = frozenset(
    {
        "open", "open_app", "launch_app", "stop_app", "open_link", "key",
        "clear_text", "take_note", "long_press", "wait", "shell", "adb",
        "focus", "ui_element", "accessibility_node",
    }
)


@dataclass(frozen=True)
class MobileUseMappedAction:
    upstream_name: str
    upstream_parameters: dict[str, Any]
    canonical: dict[str, Any] | None
    terminal_status: str | None = None

    @property
    def is_terminal(self) -> bool:
        return self.terminal_status is not None

    def audit_record(self) -> dict[str, Any]:
        return {
            "upstream_name": self.upstream_name,
            "upstream_parameters": self.upstream_parameters,
            "canonical": self.canonical,
            "terminal_status": self.terminal_status,
        }


class MobileUseActionAdapter:
    """Validate the frozen seven-action interface before environment access."""

    @staticmethod
    def assert_single_action_output(content: str) -> None:
        if not isinstance(content, str):
            raise ValueError("Operator output must be text")
        if len(re.findall(r'<tool_call\b', content)) > 1:
            raise ValueError("Multiple tool calls are prohibited")
        if len(re.findall(r'"name"\s*:\s*"mobile_use"', content)) != 1:
            raise ValueError("Operator output must contain exactly one mobile_use call")

    @staticmethod
    def _parameters(action: Any) -> tuple[str, dict[str, Any]]:
        if isinstance(action, Mapping):
            name = action.get("name")
            parameters = action.get("parameters", {})
        else:
            name = getattr(action, "name", None)
            parameters = getattr(action, "parameters", {})
        if not isinstance(name, str) or not isinstance(parameters, Mapping):
            raise ValueError("Malformed MobileUse action")
        return name, dict(parameters)

    @staticmethod
    def _coord(value: Any, field: str) -> tuple[float, float]:
        if (
            not isinstance(value, (tuple, list))
            or len(value) != 2
            or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in value)
        ):
            raise ValueError(f"{field} must contain two numeric coordinates")
        x, y = float(value[0]), float(value[1])
        if not (0 <= x <= COORDINATE_MAX and 0 <= y <= COORDINATE_MAX):
            raise ValueError(f"{field} must be inside [0,{COORDINATE_MAX}]")
        return x / COORDINATE_MAX, y / COORDINATE_MAX

    @staticmethod
    def _exact(parameters: Mapping[str, Any], allowed: set[str]) -> None:
        extras = set(parameters) - allowed
        if extras:
            raise ValueError(f"Unsupported action parameter(s): {sorted(extras)!r}")

    def map(self, action: Any) -> MobileUseMappedAction:
        name, parameters = self._parameters(action)
        if name in PROHIBITED_ACTIONS or name not in ALLOWED_UPSTREAM_ACTIONS:
            raise ValueError(f"Prohibited MobileUse action: {name!r}")
        canonical: dict[str, Any] | None
        terminal: str | None = None
        if name == "click":
            self._exact(parameters, {"coordinate"})
            x, y = self._coord(parameters.get("coordinate"), "coordinate")
            canonical = {"type": "tap", "x": x, "y": y}
        elif name == "swipe":
            self._exact(parameters, {"coordinate", "coordinate2"})
            x, y = self._coord(parameters.get("coordinate"), "coordinate")
            x2, y2 = self._coord(parameters.get("coordinate2"), "coordinate2")
            canonical = {
                "type": "swipe", "x": x, "y": y, "x2": x2, "y2": y2,
                "duration_ms": 500,
            }
        elif name == "type":
            self._exact(parameters, {"text"})
            text = parameters.get("text")
            if not isinstance(text, str) or not text:
                raise ValueError("type.text must be a non-empty string")
            canonical = {"type": "type_text", "text": text, "clear_text": False}
        elif name == "system_button":
            self._exact(parameters, {"button"})
            button = parameters.get("button")
            if button not in {"Back", "Home"}:
                raise ValueError("Only Back and Home system buttons are permitted")
            canonical = {"type": "press_back" if button == "Back" else "press_home"}
        elif name == "answer":
            self._exact(parameters, {"text"})
            text = parameters.get("text")
            if not isinstance(text, str):
                raise ValueError("answer.text must be a string")
            canonical = {"type": "answer", "text": text}
        else:
            self._exact(parameters, {"status"})
            status = parameters.get("status")
            if status not in {"success", "failure"}:
                raise ValueError("terminate.status must be success or failure")
            canonical = None
            terminal = status
        return MobileUseMappedAction(name, parameters, canonical, terminal)
