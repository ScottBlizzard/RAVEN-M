"""Strict parsers for grounding and first-target action decisions."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from jsonschema import Draft202012Validator

from raven_m.role_binding_timing.contract import action_schema, grounding_schema


class DecisionParseError(ValueError):
    """A model output did not satisfy the frozen decision contract."""


@dataclass(frozen=True)
class ParsedGrounding:
    value: dict[str, Any]


@dataclass(frozen=True)
class ParsedAction:
    value: dict[str, Any]


def _strict_json(raw: str) -> dict[str, Any]:
    if raw != raw.strip() or raw.startswith("```"):
        raise DecisionParseError("Output must be one bare JSON object.")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DecisionParseError(f"Invalid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise DecisionParseError("Decision must be a JSON object.")
    return value


def _validate(
    value: dict[str, Any],
    schema: dict[str, Any],
    allowed_target_ids: set[str],
) -> None:
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda item: list(item.path),
    )
    if errors:
        message = "; ".join(error.message for error in errors[:3])
        raise DecisionParseError(message)
    target_keys = ["destination_target_id", "grounded_destination_target_id"]
    for key in target_keys:
        if key in value and value[key] not in allowed_target_ids:
            raise DecisionParseError(f"Unknown target ID in {key}: {value[key]}")
    action = value.get("action")
    if isinstance(action, dict) and action.get("target_id") not in allowed_target_ids:
        raise DecisionParseError(
            f"Unknown action target ID: {action.get('target_id')}"
        )


def parse_grounding(raw: str, *, allowed_target_ids: set[str]) -> ParsedGrounding:
    value = _strict_json(raw)
    _validate(value, grounding_schema(), allowed_target_ids)
    return ParsedGrounding(value=value)


def parse_action(raw: str, *, allowed_target_ids: set[str]) -> ParsedAction:
    value = _strict_json(raw)
    _validate(value, action_schema(), allowed_target_ids)
    return ParsedAction(value=value)
