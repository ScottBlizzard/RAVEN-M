"""Native MobileUse action mapping for the C0 public-framework control.

Unlike PF01/B2, C0 preserves the released MobileUse Operator action space.
Coordinates emitted by the released parser are physical screenshot pixels and
are normalized only at the AndroidWorld adapter boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping


NATIVE_ACTIONS = frozenset({
    "open", "click", "long_press", "type", "key", "swipe",
    "press_home", "press_back", "wait", "answer", "system_button",
    "clear_text", "take_note", "terminate",
})
_SAFE_KEY = re.compile(r"^[A-Za-z0-9_]+$")


@dataclass(frozen=True)
class C0MappedAction:
    upstream_name: str
    upstream_parameters: dict[str, Any]
    canonical: dict[str, Any] | None
    bridge_action: dict[str, Any] | None = None
    terminal_status: str | None = None

    @property
    def is_terminal(self) -> bool:
        return self.terminal_status is not None

    def audit_record(self) -> dict[str, Any]:
        return {
            "upstream_name": self.upstream_name,
            "upstream_parameters": self.upstream_parameters,
            "canonical": self.canonical,
            "bridge_action": self.bridge_action,
            "terminal_status": self.terminal_status,
        }


class C0NativeActionAdapter:
    """Validate and map the exact released MultiAgent Operator actions."""

    @staticmethod
    def assert_single_action_output(content: str) -> None:
        if not isinstance(content, str):
            raise ValueError("Operator output must be text")
        blocks = re.findall(r"<answer>(.*?)</answer>", content, flags=re.DOTALL)
        if len(blocks) != 1:
            raise ValueError("Operator output must contain exactly one <answer> block")
        try:
            import json
            calls = json.loads(blocks[0].strip())
        except Exception as exc:
            raise ValueError("Operator action block is not valid JSON") from exc
        if not isinstance(calls, list) or len(calls) != 1:
            raise ValueError("Exactly one MobileUse action is required")

    @staticmethod
    def _parts(action: Any) -> tuple[str, dict[str, Any]]:
        if isinstance(action, Mapping):
            name, parameters = action.get("name"), action.get("parameters", {})
        else:
            name = getattr(action, "name", None)
            parameters = getattr(action, "parameters", {})
        if not isinstance(name, str) or not isinstance(parameters, Mapping):
            raise ValueError("Malformed MobileUse action")
        if name not in NATIVE_ACTIONS:
            raise ValueError(f"Unknown MobileUse action: {name!r}")
        return name, dict(parameters)

    @staticmethod
    def _exact(parameters: Mapping[str, Any], allowed: set[str]) -> None:
        extras = set(parameters) - allowed
        if extras:
            raise ValueError(f"Unsupported action parameter(s): {sorted(extras)!r}")

    @staticmethod
    def _coord(value: Any, field: str, width: int, height: int) -> tuple[float, float]:
        if (
            not isinstance(value, (tuple, list))
            or len(value) != 2
            or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in value)
        ):
            raise ValueError(f"{field} must contain two numeric pixel coordinates")
        x, y = float(value[0]), float(value[1])
        if width < 2 or height < 2 or not (0 <= x < width and 0 <= y < height):
            raise ValueError(
                f"{field}={value!r} is outside screenshot {width}x{height}"
            )
        return x / (width - 1), y / (height - 1)

    def map(
        self, action: Any, *, screen_width: int, screen_height: int
    ) -> C0MappedAction:
        name, p = self._parts(action)
        canonical: dict[str, Any] | None = None
        bridge: dict[str, Any] | None = None
        terminal: str | None = None
        if name in {"click", "long_press"}:
            self._exact(p, {"coordinate", "time"} if name == "long_press" else {"coordinate"})
            x, y = self._coord(p.get("coordinate"), "coordinate", screen_width, screen_height)
            canonical = {"type": "tap" if name == "click" else "long_press", "x": x, "y": y}
            if name == "long_press":
                seconds = p.get("time", 2.0)
                if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not 0 < float(seconds) <= 10:
                    raise ValueError("long_press.time must be in (0,10]")
                canonical["duration_ms"] = round(float(seconds) * 1000)
        elif name == "swipe":
            self._exact(p, {"coordinate", "coordinate2"})
            x, y = self._coord(p.get("coordinate"), "coordinate", screen_width, screen_height)
            x2, y2 = self._coord(p.get("coordinate2"), "coordinate2", screen_width, screen_height)
            canonical = {"type": "swipe", "x": x, "y": y, "x2": x2, "y2": y2, "duration_ms": 500}
        elif name == "type":
            self._exact(p, {"text"})
            text = p.get("text")
            if not isinstance(text, str) or not text:
                raise ValueError("type.text must be a non-empty string")
            canonical = {"type": "type_text", "text": text, "clear_text": False}
        elif name == "clear_text":
            self._exact(p, set())
            canonical = {"type": "type_text", "text": "", "clear_text": True}
        elif name in {"press_home", "press_back"}:
            self._exact(p, set())
            canonical = {"type": name}
        elif name == "system_button":
            self._exact(p, {"button"})
            button = p.get("button")
            mapping = {
                "Back": "press_back", "Home": "press_home", "Enter": "press_enter"
            }
            if button == "Menu":
                bridge = {"type": "key", "text": "MENU"}
            elif button in mapping:
                canonical = {"type": mapping[button]}
            else:
                raise ValueError("Invalid system_button.button")
        elif name == "wait":
            self._exact(p, {"time"})
            seconds = p.get("time", 5.0)
            if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not 0 < float(seconds) <= 30:
                raise ValueError("wait.time must be in (0,30]")
            canonical = {"type": "wait", "duration_ms": round(float(seconds) * 1000)}
        elif name == "open":
            self._exact(p, {"text"})
            text = p.get("text")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("open.text must be a package name")
            bridge = {"type": "open_app_name", "text": text.strip()}
        elif name == "key":
            self._exact(p, {"text"})
            text = p.get("text")
            if not isinstance(text, str) or not _SAFE_KEY.fullmatch(text):
                raise ValueError("key.text must be one safe Android keyevent token")
            bridge = {"type": "key", "text": text}
        elif name == "take_note":
            self._exact(p, {"text"})
            if not isinstance(p.get("text"), str):
                raise ValueError("take_note.text must be text")
            bridge = {"type": "take_note", "text": p["text"]}
        elif name == "answer":
            self._exact(p, {"text"})
            if not isinstance(p.get("text"), str):
                raise ValueError("answer.text must be text")
            canonical = {"type": "answer", "text": p["text"]}
        else:
            self._exact(p, {"status"})
            if p.get("status") not in {"success", "failure"}:
                raise ValueError("terminate.status must be success or failure")
            terminal = p["status"]
        return C0MappedAction(name, p, canonical, bridge, terminal)


__all__ = ["C0MappedAction", "C0NativeActionAdapter", "NATIVE_ACTIONS"]
