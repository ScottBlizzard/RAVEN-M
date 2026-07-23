"""Strict parser for the B3 simple-summary contract."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from raven_m.actions.schema import ActionValidationError


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "summary.v1.schema.json"


@dataclass(frozen=True)
class ParsedSummary:
    value: dict[str, Any]
    schema_sha256: str


def parse_summary_response(
    raw: str,
    *,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
) -> ParsedSummary:
    try:
        value = json.loads(raw.strip())
    except json.JSONDecodeError as exc:
        raise ActionValidationError(
            f"Summary response is not strict JSON: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise ActionValidationError("Summary response must be an object.")
    schema_bytes = schema_path.read_bytes()
    schema = json.loads(schema_bytes)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        rendered = []
        for error in errors[:8]:
            path = ".".join(str(part) for part in error.absolute_path) or "$"
            rendered.append(f"{path}: {error.message}")
        raise ActionValidationError("; ".join(rendered))
    return ParsedSummary(
        value=value,
        schema_sha256=sha256(schema_bytes).hexdigest(),
    )
