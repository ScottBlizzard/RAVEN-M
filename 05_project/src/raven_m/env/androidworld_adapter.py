"""Deterministic mapping from canonical actions to AndroidWorld actions."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any


@dataclass(frozen=True)
class MappedAction:
    canonical: dict[str, Any]
    screen_size: tuple[int, int]
    actual_pixels: dict[str, int]
    upstream_action: dict[str, Any] | None

    def audit_record(self) -> dict[str, Any]:
        return {
            "canonical": self.canonical,
            "screen_size": list(self.screen_size),
            "actual_pixels": self.actual_pixels,
            "upstream_action": self.upstream_action,
        }


class AndroidWorldAdapter:
    """Maps normalized screenshot coordinates and rejects unsafe values."""

    @staticmethod
    def _pixel(value: Any, extent: int, field: str) -> int:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{field} must be a number.")
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"{field}={value!r} is outside [0, 1].")
        if extent <= 0:
            raise ValueError(f"Invalid screen extent for {field}: {extent}.")
        return round(float(value) * (extent - 1))

    def map_action(
        self,
        canonical: dict[str, Any],
        *,
        screen_width: int,
        screen_height: int,
    ) -> MappedAction:
        action_type = canonical["type"]
        pixels: dict[str, int] = {}
        for field, extent in (
            ("x", screen_width),
            ("x2", screen_width),
            ("y", screen_height),
            ("y2", screen_height),
        ):
            if field in canonical:
                pixels[field] = self._pixel(canonical[field], extent, field)

        upstream: dict[str, Any] | None
        if action_type == "tap":
            upstream = {
                "action_type": "click",
                "x": pixels["x"],
                "y": pixels["y"],
            }
        elif action_type == "type_text":
            upstream = {
                "action_type": "input_text",
                "text": canonical["text"],
                "clear_text": canonical.get("clear_text", False),
            }
            if "x" in pixels:
                upstream.update(x=pixels["x"], y=pixels["y"])
        elif action_type == "press_back":
            upstream = {"action_type": "navigate_back"}
        elif action_type == "press_home":
            upstream = {"action_type": "navigate_home"}
        elif action_type == "press_enter":
            upstream = {"action_type": "keyboard_enter"}
        elif action_type == "open_app":
            upstream = {
                "action_type": "open_app",
                "app_name": canonical["app_name"],
            }
        elif action_type == "answer":
            upstream = {
                "action_type": "answer",
                "text": canonical["text"],
            }
        elif action_type in {"swipe", "long_press", "wait"}:
            upstream = None
        else:
            raise ValueError(f"Unsupported canonical action: {action_type!r}")

        return MappedAction(
            canonical=dict(canonical),
            screen_size=(screen_width, screen_height),
            actual_pixels=pixels,
            upstream_action=upstream,
        )

    def execute(self, env: Any, mapped: MappedAction) -> None:
        """Execute one already-validated action against an AsyncEnv."""
        from android_world.env import adb_utils, json_action

        action_type = mapped.canonical["type"]
        if action_type == "answer":
            # AndroidWorld's evaluator reads interaction_cache. Its upstream
            # answer branch sets this value and then sends a cosmetic overlay
            # broadcast; the latter can block on an unhealthy overlay service
            # even though the terminal answer is already available. Preserve
            # the benchmark semantics without coupling evaluation to the UI.
            env.interaction_cache = mapped.canonical["text"]
            return
        if mapped.upstream_action is not None:
            env.execute_action(json_action.JSONAction(**mapped.upstream_action))
            return
        if action_type == "swipe":
            pixels = mapped.actual_pixels
            command = adb_utils.generate_swipe_command(
                pixels["x"],
                pixels["y"],
                pixels["x2"],
                pixels["y2"],
                mapped.canonical["duration_ms"],
            )
            adb_utils.issue_generic_request(command, env.controller)
            return
        if action_type == "long_press":
            pixels = mapped.actual_pixels
            command = adb_utils.generate_swipe_command(
                pixels["x"],
                pixels["y"],
                pixels["x"],
                pixels["y"],
                mapped.canonical["duration_ms"],
            )
            adb_utils.issue_generic_request(command, env.controller)
            return
        if action_type == "wait":
            time.sleep(mapped.canonical["duration_ms"] / 1000.0)
            return
        raise ValueError(f"Cannot execute canonical action: {action_type!r}")
