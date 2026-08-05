"""Exactly-once official evaluator bridge."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class EvaluatorOutcome:
    reward: float
    finish_claim: bool
    success: bool
    raw: Any


class EvaluatorBridge:
    def __init__(self, evaluate: Callable[[], Any]) -> None:
        self._evaluate = evaluate
        self._called = False

    def evaluate_once(self, *, finish_claim: bool = False) -> EvaluatorOutcome:
        if self._called:
            raise RuntimeError("Official evaluator must be called exactly once")
        self._called = True
        raw = self._evaluate()
        reward = float(raw.get("reward", 0.0) if isinstance(raw, dict) else raw)
        return EvaluatorOutcome(reward=reward, finish_claim=finish_claim,
                                success=reward > 0.0, raw=raw)
