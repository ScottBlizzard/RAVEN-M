"""Fail-closed observation privilege and evaluator-leakage checks."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from .arm_registry import ArmSpec


FORBIDDEN_EVALUATOR_KEYS = frozenset({"evaluator", "evaluator_state", "reward", "ground_truth", "golden_answer", "success", "task_params"})
STRUCTURED_KEYS = frozenset({"ui_tree", "accessibility_tree", "ui_elements", "som", "marked_screenshot"})


def content_hash(value: bytes | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.encode("utf-8")
    return sha256(value).hexdigest()


def audit_observation(observation: dict[str, Any], arm: ArmSpec) -> dict[str, Any]:
    keys = {str(key).casefold() for key in observation}
    leaked = sorted(keys & FORBIDDEN_EVALUATOR_KEYS)
    if leaked:
        raise RuntimeError(f"Evaluator state leakage: {leaked}")
    if arm.pixel_only:
        structured = sorted(keys & STRUCTURED_KEYS)
        if structured:
            raise RuntimeError(f"Structured observation leaked to pixel-only arm: {structured}")
    return dict(observation)


def pixel_effect_class(before: bytes, after_2s: bytes, after_5s: bytes) -> str:
    hashes = (content_hash(before), content_hash(after_2s), content_hash(after_5s))
    if hashes[0] == hashes[1] == hashes[2]:
        return "STRICT_NO_EFFECT"
    if hashes[0] != hashes[1] and hashes[0] == hashes[2]:
        return "TRANSIENT_EFFECT"
    return "OBSERVABLE_EFFECT"
