"""S0 capability, protected-hash and minimum-set gates."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

from .arm_registry import ARM_REGISTRY, external_families


S0_GATES = (
    "source_pin", "checkpoint_pin", "shard_integrity", "code_license",
    "model_license", "runtime_lock", "runner_support",
    "task_class_support_19_of_19", "answer_support_3_of_3",
    "coordinate_fixtures", "observation_declaration", "evaluator_isolation",
    "budget_enforcement", "logger_schema", "protected_hashes",
)


def validate_capability(value: dict[str, Any]) -> None:
    gates = value.get("gates", {})
    if set(gates) != set(S0_GATES):
        raise ValueError("S0 gate set is incomplete or contains drift")
    expected = all(gates[name] is True for name in S0_GATES)
    if value.get("qualified") is not expected:
        raise ValueError("qualified must equal the conjunction of all 15 S0 gates")


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_protected(repo_root: Path, protected: dict[str, str]) -> dict[str, str]:
    actual: dict[str, str] = {}
    for relative, expected in protected.items():
        value = sha256_file(repo_root / relative)
        actual[relative] = value
        if value.casefold() != expected.casefold():
            raise RuntimeError(f"Protected path drift: {relative}")
    return actual


def minimum_launch_set(qualified_arm_ids: set[str]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    for required in ("CB-PX-B3", "CB-PX-M0"):
        if required not in qualified_arm_ids:
            reasons.append(f"missing required internal arm {required}")
    core = {arm_id for arm_id in qualified_arm_ids
            if arm_id in ARM_REGISTRY and ARM_REGISTRY[arm_id].tier == "A"}
    external = {arm_id for arm_id in core
                if ARM_REGISTRY[arm_id].external_family is not None}
    if len(external) < 2:
        reasons.append("fewer than two external native arms")
    if len(external_families(external)) < 2:
        reasons.append("fewer than two external code/checkpoint families")
    if len(core) < 4:
        reasons.append("fewer than four core arms")
    return not reasons, reasons
