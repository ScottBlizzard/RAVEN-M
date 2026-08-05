"""Budgeted bridge to the existing AndroidWorld action adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .action_normalizer import normalize_action


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


def write_answer_contract(interaction_cache: Any, answer: str) -> None:
    """Mechanically write an answer into common AndroidWorld cache shapes."""
    if hasattr(interaction_cache, "answer"):
        interaction_cache.answer = answer
        return
    if isinstance(interaction_cache, dict):
        interaction_cache["answer"] = answer
        return
    raise TypeError("Unsupported AndroidWorld interaction_cache answer contract")
