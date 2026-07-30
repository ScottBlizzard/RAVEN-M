"""Deterministic mapping from canonical actions to AndroidWorld actions."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any


_ATOMIC_CLEAR_AND_TYPE_TIMEOUT_SECONDS = 10.0
_ATOMIC_CLEAR_AND_TYPE_MAX_TIMEOUT_SECONDS = 120.0


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
    def _atomic_clear_and_type_command(text: str, adb_utils: Any) -> list[str]:
        """Build one retry-idempotent shell request for clear-and-type.

        AndroidEnv retries a timed-out ADB command below this adapter. Keeping
        select-all, delete, and every input token in the same shell request
        ensures that each such retry clears any prefix left by its predecessor.
        Tokenization preserves AndroidWorld's word-wise input behavior.
        """
        command = [
            "shell",
            "input",
            "keycombination",
            "113",
            "29",
            "&&",
            "input",
            "keyevent",
            "67",
            "&&",
            "sleep",
            "1",
        ]
        for token in adb_utils._split_words_and_newlines(text):
            command.append("&&")
            if token == "\n":
                command.extend(["input", "keyevent", "66"])
            else:
                command.extend(
                    ["input", "text", adb_utils._adb_text_format(token)]
                )
        return command

    @staticmethod
    def _atomic_clear_and_type_timeout(text: str, adb_utils: Any) -> float:
        """Scale one compound request without allowing an unbounded stall."""
        input_operation_count = sum(
            1 for _ in adb_utils._split_words_and_newlines(text)
        )
        return min(
            _ATOMIC_CLEAR_AND_TYPE_MAX_TIMEOUT_SECONDS,
            max(
                _ATOMIC_CLEAR_AND_TYPE_TIMEOUT_SECONDS,
                float(input_operation_count + 2),
            ),
        )

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
        from android_env.proto import adb_pb2
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
        if (
            action_type == "type_text"
            and mapped.canonical.get("clear_text", False)
            and mapped.canonical.get("text")
        ):
            pixels = mapped.actual_pixels
            if "x" in pixels:
                env.execute_action(
                    json_action.JSONAction(
                        action_type="click",
                        x=pixels["x"],
                        y=pixels["y"],
                    )
                )
                time.sleep(1.0)

            command = self._atomic_clear_and_type_command(
                mapped.canonical["text"],
                adb_utils,
            )
            response = adb_utils.issue_generic_request(
                command,
                env.controller,
                timeout_sec=self._atomic_clear_and_type_timeout(
                    mapped.canonical["text"],
                    adb_utils,
                ),
            )
            if response.status != adb_pb2.AdbResponse.Status.OK:
                raise RuntimeError(
                    "Atomic clear-and-type ADB request failed: "
                    f"status={response.status}, "
                    f"error={response.error_message!r}"
                )
            adb_utils.press_enter_button(env.controller)
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
