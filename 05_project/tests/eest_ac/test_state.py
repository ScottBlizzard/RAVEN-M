from __future__ import annotations

from dataclasses import FrozenInstanceError
import json

import pytest

from raven_m.eest_ac.models import EvidenceScope, EvidenceSource
from raven_m.eest_ac.state import (
    EvidenceLedger,
    EventLog,
    GoalLedger,
    RecoveryRegistry,
    TaskLiteralStore,
)


SCREEN_A = "a" * 64
SCREEN_B = "b" * 64


def test_task_literals_are_exact_and_frozen() -> None:
    store = TaskLiteralStore('Create a note named "alpha" and call +1 555-0100.')
    assert store.literals[0].text == store.goal
    assert any(item.text == "alpha" for item in store.literals)
    assert store.contains_exact("+1 555-0100")
    with pytest.raises(FrozenInstanceError):
        store.literals[0].text = "changed"  # type: ignore[misc]


def test_event_log_is_hash_chained_and_payload_is_not_mutable(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    first = log.append(kind="observation", step=0, payload={"value": "x"})
    mutated_copy = first.payload
    mutated_copy["value"] = "corrupt"
    second = log.append(kind="decision", step=0, payload={"action": "tap"})
    assert first.payload == {"value": "x"}
    assert second.previous_event_sha256 == first.event_sha256
    assert log.verify()
    rows = [json.loads(line) for line in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert rows[0]["payload"] == {"value": "x"}


def test_evidence_requires_visible_entity_value_and_matching_source_hash() -> None:
    ledger = EvidenceLedger()
    record = ledger.add(
        entity="Avery",
        field="event_address",
        value="123 Main St",
        source=EvidenceSource.CURRENT_SCREEN,
        scope=EvidenceScope.CROSS_PAGE,
        acquisition_step=0,
        source_sha256=SCREEN_A,
        expected_source_sha256=SCREEN_A,
        visible_texts=("Avery", "Meet at 123 Main St"),
    )
    assert ledger.get(record.evidence_id) == record
    with pytest.raises(ValueError, match="entity"):
        ledger.add(
            entity="Wrong Person",
            field="event_address",
            value="123 Main St",
            source=EvidenceSource.CURRENT_SCREEN,
            scope=EvidenceScope.CROSS_PAGE,
            acquisition_step=0,
            source_sha256=SCREEN_A,
            expected_source_sha256=SCREEN_A,
            visible_texts=("Avery", "Meet at 123 Main St"),
        )
    with pytest.raises(ValueError, match="source hash"):
        ledger.add(
            entity="Avery",
            field="event_address",
            value="123 Main St",
            source=EvidenceSource.CURRENT_SCREEN,
            scope=EvidenceScope.CROSS_PAGE,
            acquisition_step=0,
            source_sha256=SCREEN_B,
            expected_source_sha256=SCREEN_A,
            visible_texts=("Avery", "Meet at 123 Main St"),
        )


def test_goal_ledger_rejects_invented_requirements() -> None:
    literals = TaskLiteralStore("Open the camera app.")
    goals = GoalLedger(literals)
    with pytest.raises(ValueError, match="exact task-literal"):
        goals.add_literal_requirement(
            statement="Upload a photo",
            source_start=0,
            source_end=4,
        )
    with pytest.raises(ValueError, match="Unregistered"):
        goals.add_literal_requirement(
            statement="Open",
            source_start=0,
            source_end=4,
            entailment_rule="model_proposed",
        )
    assert [item.requirement_id for item in goals.requirements] == ["goal:root"]


def test_recovery_requires_real_executed_no_effect() -> None:
    log = EventLog()
    registry = RecoveryRegistry()
    proposal = log.append(
        kind="decision",
        step=0,
        payload={"canonical_action": {"type": "tap", "x": 0.2, "y": 0.3}},
    )
    with pytest.raises(ValueError, match="confirmed no-effect"):
        registry.register_confirmed_no_effect(proposal)
    changed = log.append(
        kind="transition",
        step=0,
        payload={
            "outcome": "changed",
            "action_executed": True,
            "before_semantic_sha256": SCREEN_A,
            "after_semantic_sha256": SCREEN_B,
            "canonical_action": {"type": "tap", "x": 0.2, "y": 0.3},
        },
    )
    with pytest.raises(ValueError, match="confirmed no-effect"):
        registry.register_confirmed_no_effect(changed)
    no_effect = log.append(
        kind="transition",
        step=1,
        payload={
            "outcome": "no_effect_confirmed",
            "action_executed": True,
            "before_semantic_sha256": SCREEN_B,
            "after_semantic_sha256": SCREEN_B,
            "canonical_action": {"type": "tap", "x": 0.4, "y": 0.5},
        },
    )
    recovery = registry.register_confirmed_no_effect(no_effect)
    assert registry.for_state(SCREEN_B) == (recovery,)
