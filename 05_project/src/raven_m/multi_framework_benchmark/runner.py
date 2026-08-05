"""Stage authorization and immutable-package guards.

Actual third-party controller launches remain in isolated adapters.  This
module owns only protocol boundaries and never repairs a policy output.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .capability_manifest import minimum_launch_set


@dataclass(frozen=True)
class CellLimits:
    native_action_budget: int

    @property
    def model_calls(self) -> int:
        return min(4 * self.native_action_budget, 240)

    @property
    def input_tokens(self) -> int:
        return min(20_000 * self.native_action_budget, 1_000_000)

    @property
    def output_tokens(self) -> int:
        return min(2_048 * self.native_action_budget, 131_072)

    @property
    def wall_seconds(self) -> int:
        return max(1_800, min(7_200, 90 * self.native_action_budget))


@dataclass(frozen=True)
class StageAuthorization:
    s0_global_pass: bool
    s1_qualified_arms: frozenset[str]
    protected_unchanged: bool
    first_call_manifest_frozen: bool
    evaluator_reset_global_pass: bool
    answer_contract_pass: bool
    schema_validator_pass: bool

    def hard_authorized(self) -> tuple[bool, list[str]]:
        minimum_ok, reasons = minimum_launch_set(set(self.s1_qualified_arms))
        conditions = {
            "S0 global gate failed": self.s0_global_pass,
            "protected hashes changed": self.protected_unchanged,
            "first-call manifest is not frozen": self.first_call_manifest_frozen,
            "evaluator/reset global smoke failed": self.evaluator_reset_global_pass,
            "answer contract failed": self.answer_contract_pass,
            "schema validator failed": self.schema_validator_pass,
        }
        reasons.extend(name for name, passed in conditions.items() if not passed)
        return minimum_ok and all(conditions.values()), reasons


def assert_output_root_is_new(output_root: Path, frozen_roots: tuple[Path, ...]) -> None:
    resolved = output_root.resolve()
    for root in frozen_roots:
        frozen = root.resolve()
        if resolved == frozen or frozen in resolved.parents:
            raise RuntimeError(f"Output root overlaps frozen output: {frozen}")
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError("Output root must be new and empty")


@dataclass(frozen=True)
class HashFreezeGuard:
    expected: Mapping[str, str]

    def verify(self, current: Mapping[str, str]) -> None:
        if dict(current) != dict(self.expected):
            raise RuntimeError("prompt/model/runtime hash drift")


def validate_task_hash_equality(rows: list[dict[str, str]]) -> None:
    grouped: dict[tuple[str, str], set[str]] = {}
    for row in rows:
        key = (str(row["task_id"]), str(row["task_seed"]))
        grouped.setdefault(key, set()).add(row["task_params_hash"])
    drift = [key for key, values in grouped.items() if len(values) != 1]
    if drift:
        raise RuntimeError(f"Task-parameter hash differs across arms: {drift}")


def validate_rerun(original_attempt_id: str, original_validity: str,
                   rerun_of: str | None, prior_rerun_count: int) -> None:
    if original_validity != "INFRA_INVALID":
        raise RuntimeError("Scientific/task failure reruns are forbidden")
    if rerun_of != original_attempt_id:
        raise RuntimeError("Infrastructure rerun must link to original attempt")
    if prior_rerun_count >= 1:
        raise RuntimeError("Only one infrastructure rerun is allowed")
