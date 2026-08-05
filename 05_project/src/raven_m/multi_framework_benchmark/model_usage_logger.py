"""Per-cell model-call and token budget enforcement."""

from __future__ import annotations

from dataclasses import dataclass


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class UsageBudget:
    native_action_budget: int
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def call_ceiling(self) -> int:
        return min(4 * self.native_action_budget, 240)

    @property
    def input_ceiling(self) -> int:
        return min(20_000 * self.native_action_budget, 1_000_000)

    @property
    def output_ceiling(self) -> int:
        return min(2_048 * self.native_action_budget, 131_072)

    def add_call(self, input_tokens: int, output_tokens: int) -> None:
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("Token counts must be non-negative")
        new = (self.calls + 1, self.input_tokens + input_tokens,
               self.output_tokens + output_tokens)
        if new[0] > self.call_ceiling:
            raise BudgetExceeded("model_call_ceiling")
        if new[1] > self.input_ceiling:
            raise BudgetExceeded("input_token_ceiling")
        if new[2] > self.output_ceiling:
            raise BudgetExceeded("output_token_ceiling")
        self.calls, self.input_tokens, self.output_tokens = new
