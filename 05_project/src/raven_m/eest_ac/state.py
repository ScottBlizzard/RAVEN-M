"""Minimal, auditable same-episode state stores for EEST-AC."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable

from raven_m.eest_ac.models import (
    EvidenceRecord,
    EvidenceScope,
    EvidenceSource,
    Event,
    GoalRequirement,
    RecoveryRecord,
    TaskLiteral,
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: Any) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _normalized_text(value: str) -> str:
    return " ".join(value.casefold().split())


class TaskLiteralStore:
    """One immutable task source plus literal spans derived without a model."""

    def __init__(self, goal: str) -> None:
        if not isinstance(goal, str) or not goal.strip():
            raise ValueError("A non-empty task goal is required.")
        self._goal = goal
        self._goal_sha256 = sha256(goal.encode("utf-8")).hexdigest()
        literals = [
            TaskLiteral(
                literal_id="task:root",
                text=goal,
                start=0,
                end=len(goal),
                goal_sha256=self._goal_sha256,
            )
        ]
        # Quoted strings and explicit numeric/phone-like spans are useful
        # action literals. They remain exact slices of the immutable task.
        spans: set[tuple[int, int]] = set()
        patterns = (
            r"[\"']([^\"']+)[\"']",
            r"(?<!\w)[+()\d][+()\d\-\s]{2,}\d(?!\w)",
        )
        for pattern in patterns:
            for match in re.finditer(pattern, goal):
                start, end = (
                    match.span(1) if match.lastindex else match.span(0)
                )
                spans.add((start, end))
        for index, (start, end) in enumerate(sorted(spans), start=1):
            literals.append(
                TaskLiteral(
                    literal_id=f"task:span:{index:02d}",
                    text=goal[start:end],
                    start=start,
                    end=end,
                    goal_sha256=self._goal_sha256,
                )
            )
        self._literals = tuple(literals)

    @property
    def goal(self) -> str:
        return self._goal

    @property
    def goal_sha256(self) -> str:
        return self._goal_sha256

    @property
    def literals(self) -> tuple[TaskLiteral, ...]:
        return self._literals

    def contains_exact(self, text: str) -> bool:
        return bool(text) and text in self._goal

    def record(self) -> dict[str, Any]:
        return {
            "goal": self._goal,
            "goal_sha256": self._goal_sha256,
            "literals": [item.record() for item in self._literals],
        }


class EventLog:
    """Append-only, hash-chained event log."""

    def __init__(self, output_path: Path | None = None) -> None:
        self._events: list[Event] = []
        self.output_path = output_path
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if output_path.exists() and output_path.stat().st_size:
                raise FileExistsError(
                    f"Refusing to append to a non-empty EventLog: {output_path}"
                )

    @property
    def events(self) -> tuple[Event, ...]:
        return tuple(self._events)

    def append(self, *, kind: str, step: int, payload: dict[str, Any]) -> Event:
        if not kind or step < 0 or not isinstance(payload, dict):
            raise ValueError("Invalid EventLog append request.")
        previous = self._events[-1].event_sha256 if self._events else "0" * 64
        sequence = len(self._events)
        body = {
            "sequence": sequence,
            "kind": kind,
            "step": step,
            "payload": payload,
            "previous_event_sha256": previous,
        }
        event = Event(
            event_id=f"event:{sequence:04d}",
            sequence=sequence,
            kind=kind,
            step=step,
            payload_json=_canonical_json(payload),
            previous_event_sha256=previous,
            event_sha256=_digest(body),
        )
        self._events.append(event)
        if self.output_path is not None:
            with self.output_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(_canonical_json(event.record()) + "\n")
        return event

    def verify(self) -> bool:
        previous = "0" * 64
        for index, event in enumerate(self._events):
            body = {
                "sequence": index,
                "kind": event.kind,
                "step": event.step,
                "payload": event.payload,
                "previous_event_sha256": previous,
            }
            if (
                event.sequence != index
                or event.previous_event_sha256 != previous
                or event.event_sha256 != _digest(body)
            ):
                return False
            previous = event.event_sha256
        return True


class EvidenceLedger:
    """Typed entity-field evidence; no generic lifecycle state."""

    def __init__(self) -> None:
        self._records: list[EvidenceRecord] = []

    @property
    def records(self) -> tuple[EvidenceRecord, ...]:
        return tuple(self._records)

    def add(
        self,
        *,
        entity: str,
        field: str,
        value: str,
        source: EvidenceSource,
        scope: EvidenceScope,
        acquisition_step: int,
        source_sha256: str,
        expected_source_sha256: str | None = None,
        relevance_tags: Iterable[str] = (),
        visible_texts: Iterable[str] = (),
    ) -> EvidenceRecord:
        entity = entity.strip()
        field = field.strip()
        value = value.strip()
        if not entity or not field or not value:
            raise ValueError("Evidence entity, field, and value must be non-empty.")
        if acquisition_step < 0 or not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
            raise ValueError("Evidence requires a valid step and source SHA-256.")
        if (
            expected_source_sha256 is not None
            and source_sha256 != expected_source_sha256
        ):
            raise ValueError("Evidence source hash does not match the observation.")
        if source is EvidenceSource.CURRENT_SCREEN:
            normalized_value = _normalized_text(value)
            normalized_entity = _normalized_text(entity)
            visible = [_normalized_text(item) for item in visible_texts if item]
            if not any(normalized_value in item for item in visible):
                raise ValueError(
                    "Current-screen evidence value is not present in visible UI text."
                )
            if not any(normalized_entity in item for item in visible):
                raise ValueError(
                    "Current-screen evidence entity is not present in visible UI text."
                )
        clean_tags = tuple(
            dict.fromkeys(
                tag.strip().casefold()
                for tag in relevance_tags
                if isinstance(tag, str) and tag.strip()
            )
        )
        identity = {
            "entity": entity,
            "field": field,
            "value": value,
            "source": source.value,
            "scope": scope.value,
            "acquisition_step": acquisition_step,
            "source_sha256": source_sha256,
            "relevance_tags": clean_tags,
        }
        evidence_id = "ev:" + _digest(identity)[:16]
        for item in self._records:
            if item.evidence_id == evidence_id:
                return item
        record = EvidenceRecord(
            evidence_id=evidence_id,
            entity=entity,
            field=field,
            value=value,
            source=source,
            scope=scope,
            acquisition_step=acquisition_step,
            source_sha256=source_sha256,
            relevance_tags=clean_tags,
        )
        self._records.append(record)
        return record

    def get(self, evidence_id: str) -> EvidenceRecord | None:
        return next(
            (item for item in self._records if item.evidence_id == evidence_id),
            None,
        )


class GoalLedger:
    """Closed task requirements with literal-span provenance."""

    ALLOWED_ENTAILMENT_RULES = frozenset({"task_root", "exact_literal"})

    def __init__(self, task_literals: TaskLiteralStore) -> None:
        self._task_literals = task_literals
        self._requirements: list[GoalRequirement] = [
            GoalRequirement(
                requirement_id="goal:root",
                statement=task_literals.goal,
                status="open",
                source_literal_id="task:root",
                source_start=0,
                source_end=len(task_literals.goal),
                entailment_rule="task_root",
            )
        ]

    @property
    def requirements(self) -> tuple[GoalRequirement, ...]:
        return tuple(self._requirements)

    def add_literal_requirement(
        self,
        *,
        statement: str,
        source_start: int,
        source_end: int,
        entailment_rule: str = "exact_literal",
    ) -> GoalRequirement:
        goal = self._task_literals.goal
        if entailment_rule not in self.ALLOWED_ENTAILMENT_RULES:
            raise ValueError("Unregistered requirement entailment rule.")
        if not 0 <= source_start < source_end <= len(goal):
            raise ValueError("Requirement source span is outside the task.")
        if statement != goal[source_start:source_end]:
            raise ValueError("Requirement must equal its exact task-literal span.")
        identity = {
            "statement": statement,
            "source_start": source_start,
            "source_end": source_end,
            "entailment_rule": entailment_rule,
        }
        record = GoalRequirement(
            requirement_id="goal:" + _digest(identity)[:16],
            statement=statement,
            status="open",
            source_literal_id="task:root",
            source_start=source_start,
            source_end=source_end,
            entailment_rule=entailment_rule,
        )
        if all(
            item.requirement_id != record.requirement_id
            for item in self._requirements
        ):
            self._requirements.append(record)
        return record

    def close_root(self) -> None:
        root = self._requirements[0]
        self._requirements[0] = GoalRequirement(
            requirement_id=root.requirement_id,
            statement=root.statement,
            status="satisfied",
            source_literal_id=root.source_literal_id,
            source_start=root.source_start,
            source_end=root.source_end,
            entailment_rule=root.entailment_rule,
        )


class RecoveryRegistry:
    """Recovery hints admitted only after a confirmed executed no-effect."""

    def __init__(self) -> None:
        self._records: list[RecoveryRecord] = []

    @property
    def records(self) -> tuple[RecoveryRecord, ...]:
        return tuple(self._records)

    def register_confirmed_no_effect(self, event: Event) -> RecoveryRecord:
        payload = event.payload
        if (
            event.kind != "transition"
            or payload.get("outcome") != "no_effect_confirmed"
            or payload.get("action_executed") is not True
            or not payload.get("before_semantic_sha256")
            or payload.get("before_semantic_sha256")
            != payload.get("after_semantic_sha256")
            or not isinstance(payload.get("canonical_action"), dict)
        ):
            raise ValueError(
                "Recovery requires an executed transition with confirmed no-effect."
            )
        action_signature = _digest(payload["canonical_action"])
        identity = {
            "state_sha256": payload["before_semantic_sha256"],
            "action_signature": action_signature,
            "failed_event_id": event.event_id,
        }
        record = RecoveryRecord(
            recovery_id="recovery:" + _digest(identity)[:16],
            state_sha256=payload["before_semantic_sha256"],
            action_signature=action_signature,
            failed_event_id=event.event_id,
            observed_step=event.step,
            reason="Do not repeat this exact action in this unchanged semantic state.",
        )
        if all(item.recovery_id != record.recovery_id for item in self._records):
            self._records.append(record)
        return record

    def for_state(self, state_sha256: str) -> tuple[RecoveryRecord, ...]:
        return tuple(
            item for item in self._records if item.state_sha256 == state_sha256
        )
