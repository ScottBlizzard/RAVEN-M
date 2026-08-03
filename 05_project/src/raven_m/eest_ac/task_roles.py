"""Deterministic exact-span task roles shared by every EEST-AC v0.2 arm."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
from typing import Any


def _digest(value: Any) -> str:
    return sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class ExactSpan:
    text: str
    start: int
    end: int

    def record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TaskRoleFrame:
    goal_sha256: str
    intent: str
    source: ExactSpan | None
    requested_field: ExactSpan | None
    destination: ExactSpan | None
    parse_rule: str
    frame_sha256: str

    def record(self) -> dict[str, Any]:
        return {
            "goal_sha256": self.goal_sha256,
            "intent": self.intent,
            "source": self.source.record() if self.source else None,
            "requested_field": (
                self.requested_field.record() if self.requested_field else None
            ),
            "destination": self.destination.record() if self.destination else None,
            "parse_rule": self.parse_rule,
            "frame_sha256": self.frame_sha256,
        }

    @property
    def has_transfer_roles(self) -> bool:
        return all((self.source, self.requested_field, self.destination))


class TaskRoleParseError(ValueError):
    """Task literal is ambiguous or unsupported by the frozen generic grammar."""


class TaskRoleParser:
    """Parse linguistic transfer relations without task/app/name branches.

    The grammar is deliberately small and fail-closed. Every emitted value is
    an exact slice of the immutable task literal.
    """

    _FLAGS = re.IGNORECASE | re.DOTALL
    _TRANSFER_PATTERNS = (
        (
            "transfer_to_then_relative_source",
            re.compile(
                r"^(?:text|send|share|forward|message|copy)\s+"
                r"(?P<field>.+?)\s+(?:to|with)\s+"
                r"(?P<destination>.+?)\s+(?:that|which)\s+"
                r"(?P<source>.+?)\s+(?:just\s+)?"
                r"(?:sent|shared|gave|provided|texted|messaged)\b",
                _FLAGS,
            ),
        ),
        (
            "transfer_field_of_source_to_destination",
            re.compile(
                r"\b(?:share|send|forward|copy)\s+"
                r"(?P<field>.+?)\s+(?:of|from)\s+"
                r"(?P<source>.+?)\s+(?:with|to)\s+"
                r"(?P<destination>.+?)"
                r"(?=\s+(?:via|using|in)\b|[.;]|$)",
                _FLAGS,
            ),
        ),
        (
            "transfer_to_destination_with_source_field",
            re.compile(
                r"\b(?:send|share|forward|copy)\s+"
                r"(?:a\s+)?(?:message|text)?\s*to\s+"
                r"(?P<destination>.+?)\s+with\s+(?:the\s+)?"
                r"(?P<source>.+?)\s+"
                r"(?P<field>content|text|value|address|number|details?)\b",
                _FLAGS,
            ),
        ),
    )
    _OPEN_PATTERN = re.compile(
        r"^open\s+(?:the\s+)?(?P<destination>.+?)\s+app(?:\b|[.])",
        _FLAGS,
    )

    @staticmethod
    def _span(goal: str, match: re.Match[str], group: str) -> ExactSpan:
        start, end = match.span(group)
        while start < end and goal[start].isspace():
            start += 1
        while end > start and goal[end - 1].isspace():
            end -= 1
        if start >= end:
            raise TaskRoleParseError(f"Empty exact span for {group}.")
        return ExactSpan(goal[start:end], start, end)

    @staticmethod
    def _frame(
        *,
        goal: str,
        intent: str,
        source: ExactSpan | None,
        requested_field: ExactSpan | None,
        destination: ExactSpan | None,
        parse_rule: str,
    ) -> TaskRoleFrame:
        goal_hash = sha256(goal.encode("utf-8")).hexdigest()
        body: dict[str, Any] = {
            "goal_sha256": goal_hash,
            "intent": intent,
            "source": source.record() if source else None,
            "requested_field": requested_field.record() if requested_field else None,
            "destination": destination.record() if destination else None,
            "parse_rule": parse_rule,
        }
        return TaskRoleFrame(
            goal_sha256=goal_hash,
            intent=intent,
            source=source,
            requested_field=requested_field,
            destination=destination,
            parse_rule=parse_rule,
            frame_sha256=_digest(body),
        )

    def parse(self, goal: str, *, require_transfer: bool = False) -> TaskRoleFrame:
        if not isinstance(goal, str) or not goal.strip():
            raise TaskRoleParseError("A non-empty task literal is required.")
        candidates: list[TaskRoleFrame] = []
        for rule, pattern in self._TRANSFER_PATTERNS:
            match = pattern.search(goal)
            if match is None:
                continue
            candidates.append(
                self._frame(
                    goal=goal,
                    intent="transfer_value",
                    source=self._span(goal, match, "source"),
                    requested_field=self._span(goal, match, "field"),
                    destination=self._span(goal, match, "destination"),
                    parse_rule=rule,
                )
            )
        unique = {item.frame_sha256: item for item in candidates}
        if len(unique) > 1:
            raise TaskRoleParseError("Ambiguous transfer-role parse.")
        if unique:
            return next(iter(unique.values()))
        if require_transfer:
            raise TaskRoleParseError("No supported transfer relation in task literal.")
        open_match = self._OPEN_PATTERN.search(goal)
        if open_match is not None:
            return self._frame(
                goal=goal,
                intent="open_target",
                source=None,
                requested_field=None,
                destination=self._span(goal, open_match, "destination"),
                parse_rule="open_target_app",
            )
        return self._frame(
            goal=goal,
            intent="opaque_closed_task",
            source=None,
            requested_field=None,
            destination=None,
            parse_rule="fail_closed_opaque",
        )


def verify_exact_spans(goal: str, frame: TaskRoleFrame) -> bool:
    """Recheck that every role remains an exact immutable task slice."""
    if sha256(goal.encode("utf-8")).hexdigest() != frame.goal_sha256:
        return False
    for value in (frame.source, frame.requested_field, frame.destination):
        if value is not None and goal[value.start : value.end] != value.text:
            return False
    body = frame.record()
    expected = body.pop("frame_sha256")
    return _digest(body) == expected
