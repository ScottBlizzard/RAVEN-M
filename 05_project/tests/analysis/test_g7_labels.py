from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "audit_g7.py"
)
SPEC = spec_from_file_location("audit_g7", SCRIPT)
MODULE = module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def base_row() -> dict[str, str]:
    return {
        "route": "HYPOTHESIS",
        "relevant_label": "yes",
        "route_appropriate_label": "yes",
        "fact_supported_label": "",
        "useful_label": "yes",
        "harmful_label": "no",
    }


def test_expected_utility_requires_all_positive_components() -> None:
    row = base_row()
    assert MODULE.expected_utility(row) == "yes"
    row["harmful_label"] = "yes"
    assert MODULE.expected_utility(row) == "no"


def test_fact_utility_requires_visible_support() -> None:
    row = base_row()
    row["route"] = "FACT"
    row["fact_supported_label"] = "no"
    assert MODULE.expected_utility(row) == "no"
    row["fact_supported_label"] = "yes"
    assert MODULE.expected_utility(row) == "yes"
