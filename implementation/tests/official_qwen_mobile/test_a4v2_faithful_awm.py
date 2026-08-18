from __future__ import annotations

from hashlib import sha256

import pytest

from raven_m.official_qwen_mobile.a4v2_faithful_awm import (
    FaithfulOfflineWorkflowMemory,
    SCHEMA,
    UPSTREAM_COMMIT,
    classify_goal,
    json_sha256,
    validate_bank,
)


def _sha(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _bank(*, operation: str = "delete") -> dict:
    workflows = [
        {
            "workflow_id": "expense_delete_common_v1",
            "route": {
                "app": "pro_expense",
                "operation": operation,
                "object_family": "expense_record",
                "constraint_family": "*",
            },
            "donor_ids": ["d1", "d2", "d3"],
            "donor_task_classes": ["ExpenseDeleteMultiple", "ExpenseDeleteSingle"],
            "donor_seeds": [11, 12, 13],
            "text": "1. Locate the target record using visible fields. 2. Open its delete control and confirm deletion from visible UI evidence.",
            "induction_response_sha256": _sha("induced response"),
        }
    ]
    return {
        "schema": SCHEMA,
        "status": "ready",
        "frozen": True,
        "scored_hard_inputs_used": False,
        "induction": {
            "mode": "offline_model_induced",
            "generation_calls": 1,
            "upstream_commit": UPSTREAM_COMMIT,
            "model_id": "test-inducer",
            "prompt_sha256": _sha("prompt"),
        },
        "workflows": workflows,
        "bank_sha256": json_sha256(workflows),
    }


def test_exact_operation_match_injects_and_is_read_only() -> None:
    memory = FaithfulOfflineWorkflowMemory(bank_payload=_bank())
    rendered, audit = memory.read(
        {"goal": "Delete the following expenses from Arduia Pro Expense: A, B."}
    )
    assert "expense_delete_common_v1" in rendered
    assert audit["retrieved_count"] == 1
    assert memory.observe_step(source_step=1)["bank_updated"] is False
    assert memory.audit_record()["model_calls_added_during_scoring"] == 0


def test_same_app_different_operation_is_never_a_fallback() -> None:
    memory = FaithfulOfflineWorkflowMemory(bank_payload=_bank(operation="add"))
    rendered, audit = memory.read(
        {"goal": "Delete the following expenses from Arduia Pro Expense: A, B."}
    )
    assert rendered == ""
    assert audit["retrieved_count"] == 0


def test_route_classifier_covers_all_seven_preregistered_families() -> None:
    goals = [
        "Open task.html in Chrome, click five times, and enter their product.",
        "Delete the following expenses from Pro Expense.",
        "Create a playlist in Retro Music and export it.",
        "In Simple Calendar Pro, create a calendar event.",
        "What was the total duration of running activities in OpenTracks?",
        "Delete recipes from Broccoli that use garlic in the directions.",
        "Add a location marker in OsmAnd.",
    ]
    routes = [classify_goal(goal) for goal in goals]
    assert all(route is not None for route in routes)
    assert len({(route.app, route.operation) for route in routes if route}) == 7


def test_bank_rejects_single_donor_and_old_generic_fallback() -> None:
    payload = _bank()
    payload["workflows"][0]["donor_ids"] = ["d1"]
    payload["workflows"][0]["donor_seeds"] = [11]
    payload["bank_sha256"] = json_sha256(payload["workflows"])
    with pytest.raises(ValueError, match="two independent donors"):
        validate_bank(payload)

    payload = _bank()
    payload["workflows"][0]["text"] = (
        "1. perform the visible done operation. 2. Continue until finished."
    )
    payload["bank_sha256"] = json_sha256(payload["workflows"])
    with pytest.raises(ValueError, match="forbidden A4-v1 fallback"):
        validate_bank(payload)


def test_bank_hash_and_induction_provenance_are_mandatory() -> None:
    payload = _bank()
    payload["bank_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash drifted"):
        validate_bank(payload)

    payload = _bank()
    payload["induction"]["generation_calls"] = 0
    with pytest.raises(ValueError, match="induction provenance"):
        validate_bank(payload)

