"""Frozen screenshot-only completion verifier protocol."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any


COMPLETION_VERIFIER_SYSTEM_PROMPT = r"""You are a strict mobile-task completion evidence auditor. You receive a task and one current screenshot captured immediately before another agent claimed success. Judge only whether this screenshot is sufficient to allow that success claim.

Rules:
- CONFIRMED requires visible evidence that every task requirement, including the exact object, value, field, container, operation, multiplicity, and destination, is satisfied.
- A page transition, generic success toast, opened detail page, related object, or the other agent's claim is insufficient when it does not prove the exact task predicate.
- Do not assume that an unseen earlier action succeeded.
- If any required fact is hidden, ambiguous, contradicted, or only indirectly suggested, choose INSUFFICIENT.

Output exactly one JSON object and nothing else:
{"verdict":"CONFIRMED or INSUFFICIENT","reason":"one concise sentence","visible_evidence":["short visible fact"]}"""


@dataclass(frozen=True)
class CompletionVerdict:
    verdict: str
    reason: str
    visible_evidence: tuple[str, ...]


def build_completion_verifier_user_prompt(task_goal: str) -> str:
    return (
        "Task: " + str(task_goal).strip() + "\n"
        "Does the attached current screenshot provide sufficient visible "
        "evidence to allow a success claim?"
    )


def parse_completion_verdict(raw: str) -> CompletionVerdict:
    try:
        payload: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"verifier output is not exact JSON: {exc}") from exc
    if not isinstance(payload, dict) or set(payload) != {
        "verdict",
        "reason",
        "visible_evidence",
    }:
        raise ValueError("verifier JSON requires exactly verdict, reason, visible_evidence")
    verdict = payload["verdict"]
    if verdict not in {"CONFIRMED", "INSUFFICIENT"}:
        raise ValueError("verdict must be CONFIRMED or INSUFFICIENT")
    reason = payload["reason"]
    evidence = payload["visible_evidence"]
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("reason must be a non-empty string")
    if not isinstance(evidence, list) or not all(
        isinstance(item, str) and item.strip() for item in evidence
    ):
        raise ValueError("visible_evidence must be a list of non-empty strings")
    return CompletionVerdict(
        verdict=verdict,
        reason=reason.strip(),
        visible_evidence=tuple(item.strip() for item in evidence),
    )
