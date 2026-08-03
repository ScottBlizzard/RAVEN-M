"""Immutable records for the minimal EEST-AC method."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
from typing import Any


class EvidenceSource(str, Enum):
    TASK_LITERAL = "task_literal"
    CURRENT_SCREEN = "current_screen"
    VERIFIED_TRANSITION = "verified_transition"


class EvidenceScope(str, Enum):
    CURRENT_PAGE = "current_page"
    CROSS_PAGE = "cross_page"
    EPISODE = "episode"


@dataclass(frozen=True)
class TaskLiteral:
    literal_id: str
    text: str
    start: int
    end: int
    goal_sha256: str

    def record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Event:
    event_id: str
    sequence: int
    kind: str
    step: int
    payload_json: str
    previous_event_sha256: str
    event_sha256: str

    @property
    def payload(self) -> dict[str, Any]:
        """Return a fresh copy so callers cannot mutate the logged event."""
        value = json.loads(self.payload_json)
        if not isinstance(value, dict):  # defensive: constructors are internal
            raise TypeError("Event payload is not an object.")
        return value

    def record(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "sequence": self.sequence,
            "kind": self.kind,
            "step": self.step,
            "payload": self.payload,
            "previous_event_sha256": self.previous_event_sha256,
            "event_sha256": self.event_sha256,
        }


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    entity: str
    field: str
    value: str
    source: EvidenceSource
    scope: EvidenceScope
    acquisition_step: int
    source_sha256: str
    relevance_tags: tuple[str, ...] = ()

    def record(self) -> dict[str, Any]:
        value = asdict(self)
        value["source"] = self.source.value
        value["scope"] = self.scope.value
        value["relevance_tags"] = list(self.relevance_tags)
        return value


@dataclass(frozen=True)
class GoalRequirement:
    requirement_id: str
    statement: str
    status: str
    source_literal_id: str
    source_start: int
    source_end: int
    entailment_rule: str

    def record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecoveryRecord:
    recovery_id: str
    state_sha256: str
    action_signature: str
    failed_event_id: str
    observed_step: int
    reason: str

    def record(self) -> dict[str, Any]:
        return asdict(self)
