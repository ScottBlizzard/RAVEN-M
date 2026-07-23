"""Strict parsing and validation for the shared mobile action contract."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "action.v1.schema.json"


class ActionValidationError(ValueError):
    """Raised when a model response is not a valid canonical decision."""


@dataclass(frozen=True)
class ParsedDecision:
    decision: dict[str, Any]
    first_pass: bool
    extraction_used: bool
    schema_sha256: str


def load_action_schema(path: Path = DEFAULT_SCHEMA_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def schema_sha256(path: Path = DEFAULT_SCHEMA_PATH) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _extract_single_json_object(raw: str) -> dict[str, Any]:
    fenced = re.fullmatch(
        r"\s*```(?:json)?\s*(\{.*\})\s*```\s*",
        raw,
        flags=re.DOTALL | re.IGNORECASE,
    )
    candidates = [fenced.group(1)] if fenced else []
    decoder = json.JSONDecoder()
    for index, character in enumerate(raw):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(raw[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            candidates.append(json.dumps(value, ensure_ascii=False))
            break
    if not candidates:
        raise ActionValidationError("Response does not contain a JSON object.")
    try:
        value = json.loads(candidates[0])
    except json.JSONDecodeError as exc:
        raise ActionValidationError(f"Extracted JSON is invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise ActionValidationError("The extracted response is not an object.")
    return value


def _format_validation_errors(
    validator: Draft202012Validator,
    value: dict[str, Any],
) -> str:
    errors = sorted(
        validator.iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if not errors:
        return ""
    rendered = []
    for error in errors[:8]:
        path = ".".join(str(part) for part in error.absolute_path) or "$"
        rendered.append(f"{path}: {error.message}")
    return "; ".join(rendered)


def parse_action_response(
    raw: str,
    *,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    allow_wrapped_json: bool = True,
) -> ParsedDecision:
    """Parse a response and report whether it was strict first-pass JSON."""
    first_pass = True
    extraction_used = False
    try:
        value = json.loads(raw.strip())
    except json.JSONDecodeError as exc:
        if not allow_wrapped_json:
            raise ActionValidationError(f"Response is not strict JSON: {exc}") from exc
        first_pass = False
        extraction_used = True
        value = _extract_single_json_object(raw)

    if not isinstance(value, dict):
        raise ActionValidationError("Top-level response must be a JSON object.")
    schema = load_action_schema(schema_path)
    validator = Draft202012Validator(schema)
    message = _format_validation_errors(validator, value)
    if message:
        raise ActionValidationError(message)
    return ParsedDecision(
        decision=value,
        first_pass=first_pass,
        extraction_used=extraction_used,
        schema_sha256=schema_sha256(schema_path),
    )
