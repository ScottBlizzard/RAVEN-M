"""Action-relevant context selection with current-screen precedence."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Iterable

from raven_m.eest_ac.models import EvidenceRecord, EvidenceScope
from raven_m.eest_ac.state import (
    EvidenceLedger,
    GoalLedger,
    RecoveryRegistry,
    TaskLiteralStore,
)


@dataclass(frozen=True)
class ActionNeed:
    entities: tuple[str, ...] = ()
    fields: tuple[str, ...] = ()
    intent: str = ""


class ContextCompiler:
    """Select evidence for the next action; never dump the whole trajectory."""

    def __init__(self, *, max_evidence: int = 8, max_chars: int = 6000) -> None:
        if max_evidence < 1 or max_chars < 512:
            raise ValueError("Context compiler limits are too small.")
        self.max_evidence = max_evidence
        self.max_chars = max_chars

    @staticmethod
    def _terms(values: Iterable[str]) -> set[str]:
        return {
            token
            for value in values
            for token in re.findall(r"[\w+.-]+", value.casefold())
            if len(token) > 1
        }

    def _score(
        self,
        record: EvidenceRecord,
        *,
        goal_terms: set[str],
        need: ActionNeed,
    ) -> tuple[int, int, str]:
        need_entities = self._terms(need.entities)
        need_fields = self._terms(need.fields)
        intent_terms = self._terms((need.intent,))
        entity_terms = self._terms((record.entity,))
        field_terms = self._terms((record.field,))
        tag_terms = self._terms(record.relevance_tags)
        score = 0
        score += 8 * len(entity_terms & need_entities)
        score += 8 * len(field_terms & need_fields)
        score += 5 * len(tag_terms & intent_terms)
        score += 2 * len((entity_terms | field_terms | tag_terms) & goal_terms)
        score += 2 if record.scope is EvidenceScope.CROSS_PAGE else 0
        score += 1 if record.scope is EvidenceScope.EPISODE else 0
        return (score, record.acquisition_step, record.evidence_id)

    def compile(
        self,
        *,
        task_literals: TaskLiteralStore,
        goal_ledger: GoalLedger,
        evidence_ledger: EvidenceLedger,
        recovery_registry: RecoveryRegistry,
        current_screen_sha256: str,
        need: ActionNeed | None = None,
    ) -> dict[str, object]:
        need = need or ActionNeed()
        goal_terms = self._terms(
            item.statement
            for item in goal_ledger.requirements
            if item.status == "open"
        )
        candidates = [
            item
            for item in evidence_ledger.records
            if item.scope is not EvidenceScope.CURRENT_PAGE
            or item.source_sha256 == current_screen_sha256
        ]
        candidates.sort(
            key=lambda item: self._score(
                item,
                goal_terms=goal_terms,
                need=need,
            ),
            reverse=True,
        )
        selected = candidates[: self.max_evidence]
        payload: dict[str, object] = {
            "schema_version": "eest_ac_context.v0_1",
            "authority": {
                "current_screenshot": "highest_for_current_page",
                "history": "cross_page_fields_and_verified_transitions_only",
            },
            "task": {
                "goal_sha256": task_literals.goal_sha256,
                "immutable_goal": task_literals.goal,
            },
            "open_requirements": [
                item.record()
                for item in goal_ledger.requirements
                if item.status == "open"
            ],
            "action_need": {
                "entities": list(need.entities),
                "fields": list(need.fields),
                "intent": need.intent,
            },
            "selected_evidence": [item.record() for item in selected],
            "recovery_for_current_state": [
                item.record()
                for item in recovery_registry.for_state(current_screen_sha256)
            ],
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        while len(encoded) > self.max_chars and selected:
            selected.pop()
            payload["selected_evidence"] = [item.record() for item in selected]
            encoded = json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        if len(encoded) > self.max_chars:
            raise ValueError("Task and goal metadata alone exceed the context cap.")
        payload["compiled_chars"] = len(encoded)
        return payload
