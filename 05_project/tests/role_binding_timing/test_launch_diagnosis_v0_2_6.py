from __future__ import annotations

import pytest

from raven_m.role_binding_timing.launch_diagnosis_v0_2_6 import (
    classify_post_wait_samples,
    task_agnostic_timeout_correction_authorized,
)


PACKAGE = "com.example"


def sample(*, sources: int, ui: bool, screenshot: bool, process: bool = True) -> dict:
    names = ("activity_activities", "activity_top", "window_windows", "window_displays")
    return {
        "sample": 1,
        "foreground_packages": {
            name: [PACKAGE] if index < sources else [] for index, name in enumerate(names)
        },
        "process_active": process,
        "ui_tree_usable": ui,
        "ui_packages": [PACKAGE] if ui else [],
        "screenshot_usable": screenshot,
    }


def test_a_requires_two_consecutive_strict_samples() -> None:
    classification = classify_post_wait_samples(
        [sample(sources=2, ui=True, screenshot=True), sample(sources=3, ui=True, screenshot=True)],
        PACKAGE,
    )
    assert classification["outcome"] == "A_FALSE_NEGATIVE_LAUNCH_SIGNAL"
    assert task_agnostic_timeout_correction_authorized(classification)


def test_single_strict_sample_is_not_a() -> None:
    classification = classify_post_wait_samples(
        [sample(sources=2, ui=True, screenshot=True), sample(sources=1, ui=True, screenshot=True)],
        PACKAGE,
    )
    assert classification["outcome"] == "B_RENDER_OR_UI_OBSERVABILITY_FLOOR"


@pytest.mark.parametrize(
    ("sources", "ui", "screenshot"),
    [(2, False, True), (2, True, False), (1, True, True)],
)
def test_incomplete_bundle_is_b(sources: int, ui: bool, screenshot: bool) -> None:
    classification = classify_post_wait_samples(
        [sample(sources=sources, ui=ui, screenshot=screenshot)], PACKAGE
    )
    assert classification["outcome"] == "B_RENDER_OR_UI_OBSERVABILITY_FLOOR"
    assert not task_agnostic_timeout_correction_authorized(classification)


def test_no_activity_or_process_is_c() -> None:
    classification = classify_post_wait_samples(
        [sample(sources=0, ui=False, screenshot=False, process=False)], PACKAGE
    )
    assert classification["outcome"] == "C_EMULATOR_OR_FRAMEWORK_LIFECYCLE_FLOOR"


def test_empty_samples_rejected() -> None:
    with pytest.raises(ValueError, match="NO_POST_WAIT_SAMPLES"):
        classify_post_wait_samples([], PACKAGE)
