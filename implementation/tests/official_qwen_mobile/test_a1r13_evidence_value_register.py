from __future__ import annotations

from raven_m.official_qwen_mobile.a1r13_evidence_value_register import (
    MECHANISM_ID,
    EvidenceValueRegisterMemory,
)


def _write(memory: EvidenceValueRegisterMemory, step: int, observed: str, pending: str):
    return memory.write(
        source_step=step,
        action_summary=(
            f"MEMORY[observed={observed}; verified=first number recorded; "
            f"pending={pending}] | Click the visible button."
        ),
        source_call_id=f"call-{step}",
        source_response_sha256=f"response-{step}",
        source_screenshot_sha256=f"screen-{step}",
    )


def _commit(memory: EvidenceValueRegisterMemory, step: int) -> str:
    text, audit = memory.read(context={})
    if text:
        memory.commit_injection(str(audit["ticket_id"]), f"prompt-{step}")
    return text


def test_browser_sequence_is_preserved_exactly() -> None:
    memory = EvidenceValueRegisterMemory()
    pending = "click button 4 more times, record numbers, calculate product"
    observed = ["number '1' displayed", "number 8 displayed", "number displayed is 10", "number displayed is 7", "number 2 displayed"]
    for step, value in enumerate(observed, start=13):
        event = _write(memory, step, value, pending)
        assert event["evidence_value_register"]["accepted"] is True
        rendered = _commit(memory, step + 1)
    assert "observed integer sequence = [1, 8, 10, 7, 2]." in rendered
    audit = memory.audit_record()
    assert audit["mechanism_id"] == MECHANISM_ID
    assert [row["value"] for row in audit["evidence_register"]["values"]] == ["1", "8", "10", "7", "2"]
    assert audit["evidence_register"]["counters"]["append_count"] == 5


def test_no_arithmetic_collection_pair_stays_exact_r2() -> None:
    memory = EvidenceValueRegisterMemory()
    event = _write(memory, 1, "number 8 displayed", "tap Save to finish")
    assert event["evidence_value_register"]["accepted"] is False
    text = _commit(memory, 2)
    assert "TRANSIENT MODEL-AUTHORED EVIDENCE" not in text
    assert text.startswith("Latest compact task ledger")


def test_multiple_or_decimal_values_are_rejected() -> None:
    memory = EvidenceValueRegisterMemory()
    pending = "record numbers and calculate product"
    for step, observed in enumerate(("numbers 1 and 8 displayed", "number 1.5 displayed")):
        assert _write(memory, step, observed, pending)["evidence_value_register"]["accepted"] is False
    assert memory.audit_record()["evidence_register"]["values"] == []


def test_explicit_clear_removes_register() -> None:
    memory = EvidenceValueRegisterMemory()
    _write(memory, 1, "number 3 displayed", "record numbers and calculate product")
    memory.write(
        source_step=2,
        action_summary="MEMORY[observed=done; verified=done; pending=none] | Terminate.",
        source_call_id="call-2",
        source_response_sha256="response-2",
        source_screenshot_sha256="screen-2",
    )
    assert memory.audit_record()["evidence_register"]["values"] == []


def test_value_capacity_is_bounded_without_eviction() -> None:
    memory = EvidenceValueRegisterMemory(max_evidence_values=6)
    pending = "record numbers and calculate product"
    for step in range(7):
        _write(memory, step, f"number {step + 1} displayed", pending)
    audit = memory.audit_record()["evidence_register"]
    assert len(audit["values"]) == 6
    assert audit["counters"]["capacity_suppression_count"] == 1


def test_invalid_prefix_does_not_change_register() -> None:
    memory = EvidenceValueRegisterMemory()
    _write(memory, 1, "number 3 displayed", "record numbers and calculate product")
    memory.write(
        source_step=2,
        action_summary="Click the button without a MEMORY prefix.",
        source_call_id="call-2",
        source_response_sha256="response-2",
        source_screenshot_sha256="screen-2",
    )
    assert [row["value"] for row in memory.audit_record()["evidence_register"]["values"]] == ["3"]


def test_decision_boundary_remains_pure_memory() -> None:
    boundary = EvidenceValueRegisterMemory().audit_record()["decision_boundary"]
    assert boundary == {
        "extra_model_calls": 0,
        "action_override_count": 0,
        "forced_termination_count": 0,
        "hidden_ui_used_for_decision": False,
        "evaluator_used_for_decision": False,
        "task_name_rules": False,
        "screen_text_or_ocr_used": False,
        "values_are_model_authored_only": True,
    }
