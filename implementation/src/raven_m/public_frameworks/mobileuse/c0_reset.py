"""Per-task app-state isolation matching MobileUse's documented benchmark."""

from __future__ import annotations

from datetime import datetime, timezone
from types import MethodType
from typing import Any


RESET_APP_NAMES = (
    "audio recorder", "camera", "tasks", "markor",
    "simple calendar pro", "chrome",
)


def initialize_task_with_native_resets(task: Any, env: Any) -> dict[str, Any]:
    """Run normal AndroidWorld initialization plus MobileUse app resets.

    The reset is inserted immediately after AndroidWorld restores each app
    snapshot and before the concrete task initializes its seeded state. This is
    the same lifecycle location used by the MadeAgents AndroidWorld fork.
    """
    from android_world.env.setup_device import apps, setup

    mapping = {
        "audio recorder": apps.AudioRecorder,
        "camera": apps.CameraApp,
        "tasks": apps.TasksApp,
        "markor": apps.MarkorApp,
        "simple calendar pro": apps.SimpleCalendarProApp,
        "chrome": apps.ChromeApp,
    }
    relevant = [name for name in task.app_names if name in mapping]
    original = task._initialize_apps
    completed: list[str] = []

    def isolated_initialize(_task: Any, target_env: Any) -> None:
        original(target_env)
        for name in relevant:
            setup.setup_app(mapping[name], target_env)
            completed.append(name)

    task._initialize_apps = MethodType(isolated_initialize, task)
    try:
        task.initialize_task(env)
    finally:
        task._initialize_apps = original
    return {
        "schema": "raven_m.c0.app_reset_audit.v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "task_class": task.__class__.__name__,
        "declared_apps": list(task.app_names),
        "reset_policy_apps": list(RESET_APP_NAMES),
        "required_resets": relevant,
        "completed_resets": completed,
        "pass": completed == relevant,
        "lifecycle": "after_snapshot_restore_before_seeded_task_state",
    }


__all__ = ["RESET_APP_NAMES", "initialize_task_with_native_resets"]
