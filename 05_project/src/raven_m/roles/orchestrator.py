"""Schema-validated, conditional Planner and Critic calls."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from jsonschema import Draft202012Validator

from raven_m.models.transformers_client import ModelCall, TransformersClient


PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class RoleResult:
    role: str
    output: dict[str, Any] | None
    calls: tuple[ModelCall, ...]
    error: dict[str, Any] | None = None


def _extract_object(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.strip())
    except json.JSONDecodeError:
        fenced = re.fullmatch(
            r"\s*```(?:json)?\s*(\{.*\})\s*```\s*",
            raw,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if not fenced:
            raise ValueError("Role response is not one JSON object.")
        value = json.loads(fenced.group(1))
    if not isinstance(value, dict):
        raise ValueError("Role response must be an object.")
    return value


def _validate(raw: str, schema_path: Path) -> dict[str, Any]:
    value = _extract_object(raw)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        rendered = []
        for error in errors[:8]:
            path = ".".join(str(part) for part in error.absolute_path) or "$"
            rendered.append(f"{path}: {error.message}")
        raise ValueError("; ".join(rendered))
    return value


def _validate_memory_ids(
    *,
    role: str,
    value: dict[str, Any],
    allowed_memory_ids: set[str],
) -> None:
    cited: set[str] = set()
    if role == "critic":
        cited.update(value.get("memory_ids", []))
    elif role == "planner":
        for requirement in value.get("completion_requirements", []):
            cited.update(requirement.get("evidence_memory_ids", []))
    unknown = cited - allowed_memory_ids
    if unknown:
        raise ValueError(
            "Role cited unavailable memory IDs: " + ", ".join(sorted(unknown))
        )


class RoleOrchestrator:
    def __init__(
        self,
        *,
        client: TransformersClient,
        planner_prompt: str,
        critic_prompt: str,
    ) -> None:
        self.client = client
        self.prompts = {
            "planner": planner_prompt,
            "critic": critic_prompt,
        }
        self.schemas = {
            "planner": PROJECT_ROOT / "schemas" / "plan.v1.schema.json",
            "critic": PROJECT_ROOT / "schemas" / "critic.v1.schema.json",
        }

    @staticmethod
    def _repair_prompt(
        *,
        role: str,
        user_prompt: str,
        validation_error: str,
    ) -> str:
        if role == "planner":
            contract = (
                "Rebuild the object from scratch; do not copy the invalid "
                "response. Use exactly the plan.v1 shape in the system "
                "prompt. Emit one completion_requirements array containing "
                "one object, and close it with `}]` before the "
                "`plan_summary` key. Check every `{}` and `[]` pair."
            )
        else:
            contract = (
                "Rebuild the object from scratch; do not copy the invalid "
                "response. Use exactly the critic.v1 shape and enumerations "
                "in the system prompt. Check every `{}` and `[]` pair."
            )
        return (
            user_prompt
            + "\nVALIDATION_ERROR:"
            + validation_error
            + "\nREPAIR_CONTRACT:"
            + contract
            + f"\nReturn only one corrected {role} JSON object."
        )

    def call(
        self,
        *,
        role: str,
        image_path: Path,
        payload: dict[str, Any],
        episode_id: str,
        step: int,
        remaining_model_calls: int,
        allowed_memory_ids: set[str] | None = None,
    ) -> RoleResult:
        if role not in self.prompts:
            raise ValueError(f"Unknown role: {role}")
        if remaining_model_calls < 1:
            return RoleResult(
                role=role,
                output=None,
                calls=(),
                error={
                    "type": "RoleBudgetExhausted",
                    "message": f"No model-call budget for {role}.",
                },
            )
        user_prompt = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        initial = self.client.generate(
            image_path=image_path,
            system_prompt=self.prompts[role],
            user_prompt=user_prompt,
            episode_id=episode_id,
            call_label=f"{role}_step_{step:03d}_initial",
            max_tokens=256,
        )
        calls = [initial]
        try:
            output = _validate(initial.content, self.schemas[role])
            _validate_memory_ids(
                role=role,
                value=output,
                allowed_memory_ids=allowed_memory_ids or set(),
            )
            return RoleResult(role=role, output=output, calls=tuple(calls))
        except ValueError as initial_error:
            if remaining_model_calls < 2:
                return RoleResult(
                    role=role,
                    output=None,
                    calls=tuple(calls),
                    error={
                        "type": "RoleValidationError",
                        "initial": str(initial_error),
                    },
                )
            repaired = self.client.generate(
                image_path=image_path,
                system_prompt=self.prompts[role],
                user_prompt=self._repair_prompt(
                    role=role,
                    user_prompt=user_prompt,
                    validation_error=str(initial_error),
                ),
                episode_id=episode_id,
                call_label=f"{role}_step_{step:03d}_repair",
                max_tokens=256,
            )
            calls.append(repaired)
            try:
                output = _validate(repaired.content, self.schemas[role])
                _validate_memory_ids(
                    role=role,
                    value=output,
                    allowed_memory_ids=allowed_memory_ids or set(),
                )
            except ValueError as repair_error:
                return RoleResult(
                    role=role,
                    output=None,
                    calls=tuple(calls),
                    error={
                        "type": "RoleValidationError",
                        "initial": str(initial_error),
                        "repair": str(repair_error),
                    },
                )
            return RoleResult(role=role, output=output, calls=tuple(calls))
