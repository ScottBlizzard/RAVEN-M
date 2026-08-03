"""Compact action-relevant Context Compiler for EEST-AC v0.2."""

from __future__ import annotations

import json
import re
from typing import Iterable

from raven_m.eest_ac.models import EvidenceRecord, EvidenceScope
from raven_m.eest_ac.recovery_v0_2 import RecoveryRegistryV02
from raven_m.eest_ac.state import EvidenceLedger
from raven_m.eest_ac.task_roles import TaskRoleFrame


def _terms(values: Iterable[str]) -> set[str]:
    return {
        token
        for value in values
        for token in re.findall(r"[\w+.-]+", value.casefold())
        if len(token) > 1
    }


class ContextCompilerV02:
    def __init__(self, *, max_evidence: int = 4, max_chars: int = 2800) -> None:
        if max_evidence < 1 or max_chars < 512:
            raise ValueError("Invalid compact compiler limits.")
        self.max_evidence = max_evidence
        self.max_chars = max_chars

    @staticmethod
    def _score(record: EvidenceRecord, frame: TaskRoleFrame, intent: str) -> tuple[int, int, str]:
        role_terms = _terms(
            item.text
            for item in (frame.source, frame.requested_field, frame.destination)
            if item is not None
        )
        item_terms = _terms((record.entity, record.field, *record.relevance_tags))
        intent_terms = _terms((intent,))
        score = 5 * len(role_terms & item_terms)
        score += 3 * len(intent_terms & item_terms)
        score += 2 if record.scope is EvidenceScope.CROSS_PAGE else 0
        return score, record.acquisition_step, record.evidence_id

    def compile(
        self,
        *,
        frame: TaskRoleFrame,
        evidence_ledger: EvidenceLedger,
        recovery_registry: RecoveryRegistryV02,
        current_state_signature: str,
        current_a11y_sha256: str | None,
        intent: str,
    ) -> dict[str, object]:
        candidates = [
            item
            for item in evidence_ledger.records
            if item.scope is not EvidenceScope.CURRENT_PAGE
            or item.source_sha256 == current_a11y_sha256
        ]
        candidates.sort(
            key=lambda item: self._score(item, frame, intent), reverse=True
        )
        selected = candidates[: self.max_evidence]

        def evidence_record(item: EvidenceRecord) -> dict[str, object]:
            return {
                "id": item.evidence_id,
                "entity": item.entity,
                "field": item.field,
                "value": item.value,
                "scope": item.scope.value,
            }

        payload: dict[str, object] = {
            "authority": "current_screen_over_history",
            "evidence": [evidence_record(item) for item in selected],
            "recovery": [
                {
                    "action": item.canonical_action,
                    "action_class": item.action_class,
                    "instruction": "choose_different_action_class",
                }
                for item in recovery_registry.for_state(current_state_signature)
            ],
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        while len(encoded) > self.max_chars and selected:
            selected.pop()
            payload["evidence"] = [evidence_record(item) for item in selected]
            encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if len(encoded) > self.max_chars:
            raise ValueError("Recovery context alone exceeds compact compiler cap.")
        payload["compiled_chars"] = len(encoded)
        return payload
