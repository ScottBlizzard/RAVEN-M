from __future__ import annotations

from raven_m.eest_ac.compiler import ActionNeed, ContextCompiler
from raven_m.eest_ac.models import EvidenceScope, EvidenceSource
from raven_m.eest_ac.state import (
    EvidenceLedger,
    GoalLedger,
    RecoveryRegistry,
    TaskLiteralStore,
)


SOURCE_PAGE = "1" * 64
DESTINATION_PAGE = "2" * 64


def _state():
    task = TaskLiteralStore(
        "Text the address of the event to Morgan that Avery just sent me."
    )
    return task, GoalLedger(task), EvidenceLedger(), RecoveryRegistry()


def test_cross_page_replay_keeps_typed_binding() -> None:
    task, goals, evidence, recoveries = _state()
    address = evidence.add(
        entity="Avery",
        field="event_address",
        value="123 Main St",
        source=EvidenceSource.CURRENT_SCREEN,
        scope=EvidenceScope.CROSS_PAGE,
        acquisition_step=2,
        source_sha256=SOURCE_PAGE,
        expected_source_sha256=SOURCE_PAGE,
        relevance_tags=("send", "Morgan"),
        visible_texts=("Avery", "123 Main St"),
    )
    context = ContextCompiler().compile(
        task_literals=task,
        goal_ledger=goals,
        evidence_ledger=evidence,
        recovery_registry=recoveries,
        current_screen_sha256=DESTINATION_PAGE,
        need=ActionNeed(entities=("Avery", "Morgan"), fields=("event_address",), intent="send"),
    )
    assert [item["evidence_id"] for item in context["selected_evidence"]] == [
        address.evidence_id
    ]


def test_old_current_page_fact_is_not_routed_to_new_page() -> None:
    task, goals, evidence, recoveries = _state()
    evidence.add(
        entity="Avery",
        field="header_label",
        value="Conversation",
        source=EvidenceSource.CURRENT_SCREEN,
        scope=EvidenceScope.CURRENT_PAGE,
        acquisition_step=1,
        source_sha256=SOURCE_PAGE,
        expected_source_sha256=SOURCE_PAGE,
        visible_texts=("Avery", "Conversation"),
    )
    context = ContextCompiler().compile(
        task_literals=task,
        goal_ledger=goals,
        evidence_ledger=evidence,
        recovery_registry=recoveries,
        current_screen_sha256=DESTINATION_PAGE,
    )
    assert context["selected_evidence"] == []
    assert context["authority"]["current_screenshot"] == "highest_for_current_page"


def test_current_page_fact_is_available_only_on_its_source_screen() -> None:
    task, goals, evidence, recoveries = _state()
    item = evidence.add(
        entity="Avery",
        field="header_label",
        value="Conversation",
        source=EvidenceSource.CURRENT_SCREEN,
        scope=EvidenceScope.CURRENT_PAGE,
        acquisition_step=1,
        source_sha256=SOURCE_PAGE,
        expected_source_sha256=SOURCE_PAGE,
        visible_texts=("Avery", "Conversation"),
    )
    context = ContextCompiler().compile(
        task_literals=task,
        goal_ledger=goals,
        evidence_ledger=evidence,
        recovery_registry=recoveries,
        current_screen_sha256=SOURCE_PAGE,
    )
    assert context["selected_evidence"][0]["evidence_id"] == item.evidence_id
