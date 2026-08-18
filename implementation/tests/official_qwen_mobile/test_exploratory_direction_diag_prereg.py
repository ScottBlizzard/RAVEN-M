from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TASKS = [
    "BrowserMultiply", "ExpenseDeleteMultiple2", "RetroSavePlaylist",
    "SimpleCalendarAddOneEvent", "SportsTrackerTotalDurationForCategoryThisWeek",
    "RecipeDeleteMultipleRecipesWithConstraint", "OsmAndMarker",
]


def test_three_diag_configs_freeze_independent_identity_and_common_order() -> None:
    paths = sorted((ROOT / "implementation/configs").glob("p*_diag_*_seed20260806.json"))
    assert len(paths) == 3
    configs = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    assert len({item["system_id"] for item in configs}) == 3
    assert len({item["experiment_id"] for item in configs}) == 3
    assert {item["direction"] for item in configs} == {
        "failure_recovery", "long_horizon_coordination", "outcome_completion_judgment"
    }
    assert all(item["seven_task_order"] == TASKS for item in configs)
    assert all(item["non_fail_fast"] is True for item in configs)
    assert all(item["full_suite_release_requires"] == "7/7" for item in configs)


def test_prereg_separates_protocol_validity_from_confirmatory_qualification() -> None:
    text = (ROOT / "protocols/EXPLORATORY_DIRECTION_DIAG_PREREG_2026-08-18.md").read_text(encoding="utf-8")
    assert "Protocol-validity G0 (live blocking)" in text
    assert "Confirmatory qualification (claim limiting, not live blocking)" in text
    assert "P1-DIAG" in text and "P2-DIAG" in text and "P3-DIAG" in text
    assert "non-fail-fast" in text.casefold()
    assert "not held out" in text
