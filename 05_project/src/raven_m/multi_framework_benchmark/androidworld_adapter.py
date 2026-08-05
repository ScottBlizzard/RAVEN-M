"""Budgeted bridge to the existing AndroidWorld action adapter."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Callable

from .action_normalizer import normalize_action


def normalize_guiowl_image_urls(value: Any) -> tuple[Any, int]:
    """Wrap the official GUI-Owl raw PNG base64 as OpenAI data URLs."""
    if isinstance(value, list):
        converted = [normalize_guiowl_image_urls(item) for item in value]
        return [item for item, _ in converted], sum(count for _, count in converted)
    if isinstance(value, tuple):
        converted = [normalize_guiowl_image_urls(item) for item in value]
        return tuple(item for item, _ in converted), sum(count for _, count in converted)
    if not isinstance(value, dict):
        return value, 0
    result = {}
    count = 0
    for key, item in value.items():
        normalized, child_count = normalize_guiowl_image_urls(item)
        result[key] = normalized
        count += child_count
    image_url = result.get("image_url")
    if isinstance(image_url, dict) and isinstance(image_url.get("url"), str):
        url = image_url["url"]
        if not url.startswith(("data:", "http://", "https://", "file:")):
            try:
                decoded = base64.b64decode(url, validate=True)
            except Exception as exc:
                raise ValueError("GUI-Owl supplied an invalid raw image payload") from exc
            if not decoded.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("GUI-Owl raw image payload is not PNG")
            image_url["url"] = "data:image/png;base64," + url
            count += 1
    return result, count


class ActionBudgetExceeded(RuntimeError):
    pass


@dataclass
class ActionBudget:
    ceiling: int
    used: int = 0
    step_multiplier: float = 1.0

    def __post_init__(self) -> None:
        if self.ceiling <= 0:
            raise ValueError("Action ceiling must be positive")
        if self.step_multiplier != 1.0:
            raise ValueError("Protocol v0.2 step multiplier must be exactly 1.0")

    def consume(self) -> None:
        if self.used >= self.ceiling:
            raise ActionBudgetExceeded("native_action_budget")
        self.used += 1


class BudgetedAndroidWorldAdapter:
    """Calls the supplied executor without correcting the selected action."""

    def __init__(self, execute: Callable[[dict[str, Any]], Any], ceiling: int) -> None:
        self._execute = execute
        self.budget = ActionBudget(ceiling)

    def execute(self, raw_action: dict[str, Any]) -> Any:
        canonical = normalize_action(raw_action)
        self.budget.consume()
        return self._execute(canonical)


def write_answer_contract(target: Any, answer: str) -> None:
    """Mechanically write an answer into common AndroidWorld cache shapes."""
    if hasattr(target, "interaction_cache"):
        target.interaction_cache = answer
        return
    if hasattr(target, "answer"):
        target.answer = answer
        return
    if isinstance(target, dict):
        target["answer"] = answer
        return
    raise TypeError("Unsupported AndroidWorld interaction_cache answer contract")
