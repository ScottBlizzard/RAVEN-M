from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts/analyze_case_studies.py"
SPEC = importlib.util.spec_from_file_location("analyze_case_studies", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def selection() -> dict:
    return {
        "cases": [
            {
                "selection_index": 1,
                "cell": "m0_only_success",
                "task_id": "H01",
                "instance_seed": 20260720,
            }
        ]
    }


def test_missing_annotations_create_template_and_block(tmp_path: Path) -> None:
    path = tmp_path / "case_annotations.json"
    with pytest.raises(SystemExit):
        MODULE.load_annotations(
            selection=selection(),
            annotation_path=path,
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["review_status"] == "pending_single_reviewer"
    assert payload["cases"][0]["memory_effect"] == ""


def test_completed_annotations_require_exact_selection(
    tmp_path: Path,
) -> None:
    path = tmp_path / "case_annotations.json"
    payload = MODULE.annotation_template(selection())
    payload["review_status"] = "completed_single_reviewer"
    payload["cases"][0].update(
        {
            "memory_effect": "helpful",
            "m0_evidence_steps": [2, 4],
            "b3_evidence_steps": [3],
            "annotation": "Routed evidence avoided a repeated wrong branch.",
        }
    )
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    observed = MODULE.load_annotations(
        selection=selection(),
        annotation_path=path,
    )
    assert observed[(1, "m0_only_success", "H01", 20260720)][
        "memory_effect"
    ] == "helpful"


def test_completed_annotations_reject_blank_interpretation(
    tmp_path: Path,
) -> None:
    path = tmp_path / "case_annotations.json"
    payload = MODULE.annotation_template(selection())
    payload["review_status"] = "completed_single_reviewer"
    payload["cases"][0]["memory_effect"] = "neutral"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="Missing mechanism annotation"):
        MODULE.load_annotations(
            selection=selection(),
            annotation_path=path,
        )
