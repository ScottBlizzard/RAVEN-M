"""Strict screenshot-only source-object extraction diagnostic."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


VISIBLE_OBJECT_EXTRACTOR_SYSTEM_PROMPT = """You are a strict screenshot-only record extractor.
Use only text visibly present in the supplied screenshot and the task wording.
Do not infer hidden rows, do not complete truncated records, and do not use outside knowledge.
Return exactly one JSON object with this schema and no markdown or extra text:
{"objects":[{"identifier":"exact visible object name or title"}]}
If no complete task-relevant object identifier is visibly supported, return {"objects":[]}.
Never invent an identifier."""


def build_visible_object_extractor_user_prompt(task_goal: str, extraction_rule: str) -> str:
    return (
        f"Task: {task_goal}\n"
        f"Selection rule: {extraction_rule}\n"
        "Extract only complete object identifiers visibly supported on this screenshot. "
        "Preserve the visible spelling. Apply the selection rule only when its required "
        "predicate is visible for the same record."
    )


@dataclass(frozen=True)
class VisibleObjectExtraction:
    identifiers: tuple[str, ...]


def parse_visible_object_extraction(content: str) -> VisibleObjectExtraction:
    try:
        payload: Any = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"response is not exact JSON: {exc}") from exc
    if not isinstance(payload, dict) or set(payload) != {"objects"}:
        raise ValueError("response must contain exactly the objects key")
    objects = payload["objects"]
    if not isinstance(objects, list):
        raise ValueError("objects must be a list")
    identifiers: list[str] = []
    for index, item in enumerate(objects):
        if not isinstance(item, dict) or set(item) != {"identifier"}:
            raise ValueError(f"objects[{index}] must contain exactly identifier")
        identifier = item["identifier"]
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError(f"objects[{index}].identifier must be a non-empty string")
        identifiers.append(identifier.strip())
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("duplicate identifiers are not allowed")
    return VisibleObjectExtraction(identifiers=tuple(identifiers))
