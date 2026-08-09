"""Enumerated mechanical prompt substitutions for the PF01 action boundary."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any


@dataclass(frozen=True)
class PromptChange:
    role: str
    field: str
    labels: tuple[str, ...]
    before_sha256: str
    after_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "field": self.field,
            "labels": list(self.labels),
            "before_sha256": self.before_sha256,
            "after_sha256": self.after_sha256,
        }


_OPERATOR_SYSTEM = """You are a helpful AI assistant for operating mobile phones. Your goal is to choose the correct actions to complete the user's instruction. Think as if you are a human user operating the phone.

# Tools

Return exactly one `mobile_use` function call per response. The screenshot is addressed on a normalized 1000 by 1000 coordinate grid: both x and y are integers from 0 through 999, independent of the physical screen resolution.

<tools>
{{"type": "function", "function": {{"name_for_human": "mobile_use", "name": "mobile_use", "description": "Use the visible touchscreen only. Choose the center of a visible target and emit at most one action. For a user-answer task, finish with terminate(success); the separate AnswerAgent will produce the answer.", "parameters": {{"properties": {{"action": {{"description": "Allowed Operator actions only.", "enum": ["click", "swipe", "type", "system_button", "terminate"], "type": "string"}}, "coordinate": {{"description": "[x,y] on the normalized [0,999] grid; used by click and swipe.", "type": "array", "items": {{"type": "integer", "minimum": 0, "maximum": 999}}, "minItems": 2, "maxItems": 2}}, "coordinate2": {{"description": "Swipe end [x,y] on the normalized [0,999] grid.", "type": "array", "items": {{"type": "integer", "minimum": 0, "maximum": 999}}, "minItems": 2, "maxItems": 2}}, "text": {{"description": "Text for type.", "type": "string"}}, "button": {{"description": "Permitted system button.", "enum": ["Back", "Home"], "type": "string"}}, "status": {{"description": "Task status for terminate.", "enum": ["success", "failure"], "type": "string"}}}}, "required": ["action"], "type": "object"}}, "args_format": "Format the arguments as a JSON object."}}}}
</tools>"""


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _change(
    changes: list[PromptChange],
    *,
    role: str,
    prompt: Any,
    field: str,
    after: str,
    labels: tuple[str, ...],
) -> None:
    before = getattr(prompt, field)
    if not isinstance(before, str):
        raise TypeError(f"{role}.{field} is not text")
    setattr(prompt, field, after)
    changes.append(PromptChange(role, field, labels, _digest(before), _digest(after)))


def _safe_tips(value: str) -> str:
    prohibited = ("`open`", "long press", "`clear_text`", "clipboard button")
    lines = [line for line in value.splitlines() if not any(token in line.lower() for token in prohibited)]
    return "\n".join(lines).strip()


def adapt_prompts(operator_prompt: Any, answer_prompt: Any) -> list[PromptChange]:
    """Apply only the frozen schema, coordinate, and tool-removal changes."""
    changes: list[PromptChange] = []
    _change(
        changes,
        role="Operator",
        prompt=operator_prompt,
        field="system_prompt",
        after=_OPERATOR_SYSTEM,
        labels=("ACTION_NAME", "ACTION_SCHEMA", "COORDINATE_RANGE", "UNSUPPORTED_TOOL_REMOVAL"),
    )
    _change(
        changes,
        role="Operator",
        prompt=operator_prompt,
        field="init_tips",
        after=_safe_tips(operator_prompt.init_tips),
        labels=("UNSUPPORTED_TOOL_REMOVAL",),
    )
    _change(
        changes,
        role="Operator",
        prompt=operator_prompt,
        field="observation_prompt",
        after=(
            "### Observation ###\nThis is the current screenshot of the phone. "
            "Use the normalized [0,999] coordinate grid described in the tool schema.\n"
            "{image_placeholder}"
        ),
        labels=("COORDINATE_RANGE",),
    )
    _change(
        changes,
        role="Operator",
        prompt=operator_prompt,
        field="a11y_tree_prompt",
        after="",
        labels=("UNSUPPORTED_TOOL_REMOVAL",),
    )
    answer_system = answer_prompt.system_prompt.replace(
        "The screen's resolution is {resized_width}x{resized_height}.",
        "The screenshot uses the experiment's normalized [0,999] coordinate convention."
    ).replace(
        "You may call one or more functions to assist with the user query.",
        "Return exactly one answer function call."
    )
    _change(
        changes,
        role="AnswerAgent",
        prompt=answer_prompt,
        field="system_prompt",
        after=answer_system,
        labels=("ACTION_SCHEMA", "COORDINATE_RANGE"),
    )
    _change(
        changes,
        role="AnswerAgent",
        prompt=answer_prompt,
        field="observation_prompt",
        after=(
            "### Observation ###\nThis is the current screenshot of the phone.\n"
            "{image_placeholder}"
        ),
        labels=("COORDINATE_RANGE",),
    )
    return changes


def write_prompt_change_manifest(path: Any, changes: list[PromptChange]) -> None:
    from pathlib import Path

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps([item.as_dict() for item in changes], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
