"""Strict parser for the independent EEST-AC decision contract."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "eest_ac_decision.v0_1.schema.json"


class EestDecisionValidationError(ValueError):
    """The model response is not a valid EEST-AC decision."""


@dataclass(frozen=True)
class ParsedEestDecision:
    decision: dict[str, Any]
    first_pass: bool
    extraction_used: bool
    schema_sha256: str


def schema_sha256(path: Path = DEFAULT_SCHEMA_PATH) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _extract_object(raw: str) -> dict[str, Any]:
    fenced = re.fullmatch(
        r"\s*```(?:json)?\s*(\{.*\})\s*```\s*",
        raw,
        flags=re.DOTALL | re.IGNORECASE,
    )
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        decoder = json.JSONDecoder()
        for index, character in enumerate(raw):
            if character != "{":
                continue
            try:
                value, _ = decoder.raw_decode(raw[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
        raise EestDecisionValidationError("Response contains no JSON object.")
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise EestDecisionValidationError(str(exc)) from exc
    if not isinstance(value, dict):
        raise EestDecisionValidationError("Extracted value is not an object.")
    return value


def parse_eest_decision(
    raw: str,
    *,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    allow_wrapped_json: bool = True,
) -> ParsedEestDecision:
    first_pass = True
    extraction_used = False
    try:
        value = json.loads(raw.strip())
    except json.JSONDecodeError as exc:
        if not allow_wrapped_json:
            raise EestDecisionValidationError(str(exc)) from exc
        first_pass = False
        extraction_used = True
        value = _extract_object(raw)
    if not isinstance(value, dict):
        raise EestDecisionValidationError("Top-level response must be an object.")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda item: list(item.absolute_path),
    )
    if errors:
        rendered = []
        for error in errors[:8]:
            path = ".".join(str(part) for part in error.absolute_path) or "$"
            rendered.append(f"{path}: {error.message}")
        raise EestDecisionValidationError("; ".join(rendered))
    return ParsedEestDecision(
        decision=value,
        first_pass=first_pass,
        extraction_used=extraction_used,
        schema_sha256=schema_sha256(schema_path),
    )
