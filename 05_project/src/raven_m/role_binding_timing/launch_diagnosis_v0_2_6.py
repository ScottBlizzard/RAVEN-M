"""Pure classification logic for the B2.6 DEV launch-observability diagnosis."""

from __future__ import annotations

from typing import Any


FOREGROUND_SOURCES = ("activity_activities", "activity_top", "window_windows", "window_displays")


def classify_post_wait_samples(samples: list[dict[str, Any]], expected_package: str) -> dict[str, Any]:
    if not samples:
        raise ValueError("NO_POST_WAIT_SAMPLES")
    evaluated = []
    for sample in samples:
        source_hits = [
            source
            for source in FOREGROUND_SOURCES
            if expected_package in sample.get("foreground_packages", {}).get(source, [])
        ]
        process_active = sample.get("process_active") is True
        ui_usable = sample.get("ui_tree_usable") is True
        ui_agrees = expected_package in sample.get("ui_packages", [])
        screenshot_usable = sample.get("screenshot_usable") is True
        strict_positive = len(source_hits) >= 2 and ui_usable and ui_agrees and screenshot_usable
        active_signal = bool(source_hits) or process_active
        evaluated.append(
            {
                "sample": sample.get("sample"),
                "source_hits": source_hits,
                "source_hit_count": len(source_hits),
                "process_active": process_active,
                "ui_usable": ui_usable,
                "ui_agrees": ui_agrees,
                "screenshot_usable": screenshot_usable,
                "strict_positive": strict_positive,
                "active_signal": active_signal,
            }
        )
    consecutive_strict = any(
        evaluated[index]["strict_positive"] and evaluated[index + 1]["strict_positive"]
        for index in range(len(evaluated) - 1)
    )
    if consecutive_strict:
        outcome = "A_FALSE_NEGATIVE_LAUNCH_SIGNAL"
        reason = "At least two consecutive samples have >=2 independent foreground sources, usable screenshot, and usable UI tree containing the expected package."
    elif any(item["active_signal"] for item in evaluated):
        outcome = "B_RENDER_OR_UI_OBSERVABILITY_FLOOR"
        reason = "The app has an activity/process signal, but the strict screenshot/UI-tree evidence bundle is incomplete or nonconcordant."
    else:
        outcome = "C_EMULATOR_OR_FRAMEWORK_LIFECYCLE_FLOOR"
        reason = "No post--W sample establishes an active target package or process."
    return {"outcome": outcome, "reason": reason, "samples": evaluated}


def task_agnostic_timeout_correction_authorized(classification: dict[str, Any]) -> bool:
    return classification.get("outcome") == "A_FALSE_NEGATIVE_LAUNCH_SIGNAL"
