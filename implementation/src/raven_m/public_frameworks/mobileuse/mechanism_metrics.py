"""Deterministic post-hoc mechanism metrics; never fed back to the agent."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any


CROSS_APP_PACKAGES = {
    "BrowserMultiply": ("com.google.android.documentsui", "com.android.chrome"),
    "ExpenseAddMultipleFromGallery": ("com.simplemobiletools.gallery.pro", "com.arduia.expense"),
    "ExpenseAddMultipleFromMarkor": ("net.gsantner.markor", "com.arduia.expense"),
    "MarkorCreateNoteAndSms": ("net.gsantner.markor", "com.simplemobiletools.smsmessenger"),
    "MarkorTranscribeVideo": ("org.videolan.vlc", "net.gsantner.markor"),
    "RecipeAddMultipleRecipesFromImage": ("com.simplemobiletools.gallery.pro", "com.flauschcode.broccoli"),
    "RecipeAddMultipleRecipesFromMarkor": ("net.gsantner.markor", "com.flauschcode.broccoli"),
    "RecipeAddMultipleRecipesFromMarkor2": ("net.gsantner.markor", "com.flauschcode.broccoli"),
    "SaveCopyOfReceiptTaskEval": ("com.simplemobiletools.gallery.pro", "com.google.android.documentsui"),
}


def extract(events_path: Path, *, task_name: str, reward: float) -> dict[str, Any]:
    records = [
        json.loads(line)
        for line in Path(events_path).read_text(encoding="utf-8").splitlines()
    ]
    progress = [record for record in records if record["event"] == "step_progress_state"]
    packages = [record.get("after_package") or record.get("before_package") for record in progress]
    packages = [package for package in packages if package]
    reflection = Counter(
        record.get("reflection_outcome") for record in progress
        if record.get("reflection_outcome")
    )
    trajectory = Counter(
        record.get("trajectory_reflection_outcome") for record in progress
        if record.get("trajectory_reflection_outcome")
    )
    global_results = [
        record.get("global_evaluation_result") for record in progress
        if record.get("global_evaluation_result")
    ]
    source = destination = None
    source_step = destination_step = None
    category = "not_applicable"
    if task_name in CROSS_APP_PACKAGES:
        source, destination = CROSS_APP_PACKAGES[task_name]
        source_step = next((index for index, package in enumerate(packages) if package == source), None)
        destination_step = next((index for index, package in enumerate(packages) if package == destination), None)
        if source_step is None:
            category = "source_not_reached"
        elif destination_step is None or destination_step <= source_step:
            category = "source_only"
        else:
            category = "destination_reached"
    terminal = next(
        (record for record in reversed(records) if record["event"] == "controller_terminal"),
        {},
    )
    status = str(terminal.get("status") or "")
    claimed_finish = "FINISHED" in status
    return {
        "schema": "raven_m.mobileuse.mechanism_metrics.v1",
        "posthoc_only_not_agent_visible": True,
        "task_name": task_name,
        "reward": float(reward),
        "success": float(reward) == 1.0,
        "step_count": len(progress),
        "unique_packages": sorted(set(packages)),
        "screenshot_changed_steps": sum(record.get("screenshot_changed") is True for record in progress),
        "screenshot_unchanged_steps": sum(record.get("screenshot_changed") is False for record in progress),
        "nonempty_progress_steps": sum(bool(record.get("progress")) for record in progress),
        "reflection_outcomes": dict(sorted(reflection.items())),
        "trajectory_reflection_outcomes": dict(sorted(trajectory.items())),
        "global_results": global_results,
        "claimed_finish": claimed_finish,
        "false_success": claimed_finish and float(reward) != 1.0,
        "expected_source_package": source,
        "expected_destination_package": destination,
        "source_entry_step": source_step,
        "destination_entry_step": destination_step,
        "handoff_action_span": (
            destination_step - source_step
            if source_step is not None and destination_step is not None and destination_step > source_step
            else None
        ),
        "cross_app_stage": category,
    }
