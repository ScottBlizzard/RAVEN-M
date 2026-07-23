from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts/apply_retrieval_audit_labels.py"
SPEC = importlib.util.spec_from_file_location(
    "apply_retrieval_audit_labels",
    SCRIPT,
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def rows(route: str = "HYPOTHESIS") -> list[dict[str, str]]:
    return [
        {
            "audit_id": f"R{index:03d}",
            "route": route,
            "fact_supported_label": "",
            "relevant_label": "",
            "route_appropriate_label": "",
            "useful_label": "",
            "harmful_label": "",
            "utility_label": "",
            "review_notes": "",
        }
        for index in range(1, 51)
    ]


def payload(*, useful: str = "yes", note: str = "") -> dict:
    return {
        "schema_version": "retrieval_labels.v1",
        "review_status": "completed_single_reviewer",
        "items": [
            {
                "audit_id": f"R{index:03d}",
                "relevant_label": "yes",
                "route_appropriate_label": "yes",
                "fact_supported_label": "yes",
                "useful_label": useful,
                "harmful_label": "no",
                "review_notes": note,
            }
            for index in range(1, 51)
        ],
    }


def test_apply_labels_derives_utility() -> None:
    output = MODULE.apply_labels(rows(), payload())
    assert len(output) == 50
    assert {item["utility_label"] for item in output} == {"yes"}
    assert {item["fact_supported_label"] for item in output} == {""}


def test_negative_label_requires_note() -> None:
    with pytest.raises(ValueError, match="needs a note"):
        MODULE.apply_labels(rows(), payload(useful="no"))


def test_fact_requires_support_label() -> None:
    value = payload(note="Unsupported visible state.")
    del value["items"][0]["fact_supported_label"]
    with pytest.raises(ValueError, match="needs fact_supported_label"):
        MODULE.apply_labels(rows("FACT"), value)
