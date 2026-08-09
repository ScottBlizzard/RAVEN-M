"""Per-task app-state isolation matching MobileUse's documented benchmark."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import time
from types import MethodType
from typing import Any


RESET_APP_NAMES = (
    "audio recorder", "camera", "tasks", "markor",
    "simple calendar pro", "chrome",
)


def _setup_markor_146(target_env: Any) -> None:
    """Reset the frozen Markor APK despite its icon-only onboarding.

    AndroidWorld's generic setup looks for textual NEXT/DONE controls. Markor
    2.10 (APK 146) exposes only a bottom-right arrow in this emulator, so that
    helper silently leaves IntroActivity open. Drive the same five onboarding
    pages by a resolution-relative tap, then verify MainActivity and a clean
    last-used-extension preference.
    """
    from android_world.env import adb_utils
    from android_world.env.setup_device import apps

    clear_response = adb_utils.clear_app_data(
        apps.MarkorApp.package_name(), target_env.controller
    )
    adb_utils.check_ok(clear_response, "Could not clear Markor app data")
    start_response = adb_utils.issue_generic_request(
        [
            "shell", "am", "start", "-W", "-n",
            "net.gsantner.markor/net.gsantner.markor.activity.MainActivity",
        ],
        target_env.controller,
        timeout_sec=60.0,
    )
    adb_utils.check_ok(start_response, "Could not start Markor onboarding")
    # ``am start -W`` returns before this old Chrome build is input-ready on
    # the 2GB AVD. Touching it after only three seconds itself triggers an ANR
    # (confirmed by ApplicationExitInfo). Let the cold first-run UI settle
    # before sending any input.
    time.sleep(12.0)
    state = target_env.get_state(wait_to_stabilize=True)
    height, width = state.pixels.shape[:2]

    def issue(command: list[str], label: str) -> None:
        response = adb_utils.issue_generic_request(
            command, target_env.controller, timeout_sec=60.0
        )
        adb_utils.check_ok(response, label)

    for _ in range(10):
        current, response = adb_utils.get_current_activity(
            target_env.controller, timeout_sec=10.0
        )
        adb_utils.check_ok(response, "Could not inspect Markor onboarding")
        if current and current.endswith("net.gsantner.markor.activity.MainActivity"):
            break
        if not current or not current.endswith("net.gsantner.markor.activity.IntroActivity"):
            raise RuntimeError(f"Unexpected Markor setup activity: {current!r}")
        issue(
            ["shell", "input", "tap", str(round(width * 0.91)), str(round(height * 0.94))],
            "Could not advance Markor onboarding",
        )
        time.sleep(2.0)
    else:
        raise RuntimeError("Markor onboarding did not reach MainActivity")

    # The changelog dialog is deterministic on the frozen APK. Dismiss it only
    # when an OK control is actually visible; never blind-tap the file browser.
    state = target_env.get_state(wait_to_stabilize=True)
    ok_elements = [
        element for element in state.ui_elements
        if (getattr(element, "text", "") or "").strip().upper() == "OK"
    ]
    if len(ok_elements) == 1:
        box = ok_elements[0].bbox_pixels
        issue(
            [
                "shell", "input", "tap",
                str((int(box.x_min) + int(box.x_max)) // 2),
                str((int(box.y_min) + int(box.y_max)) // 2),
            ],
            "Could not dismiss Markor changelog",
        )
        time.sleep(1.0)
    current, response = adb_utils.get_current_activity(
        target_env.controller, timeout_sec=10.0
    )
    adb_utils.check_ok(response, "Could not verify Markor foreground")
    if not current or not current.endswith("net.gsantner.markor.activity.MainActivity"):
        raise RuntimeError(f"Markor reset did not reach MainActivity: {current!r}")
    prefs_response = adb_utils.issue_generic_request(
        [
            "shell", "su", "0", "cat",
            "/data/data/net.gsantner.markor/shared_prefs/app.xml",
        ],
        target_env.controller,
        timeout_sec=60.0,
    )
    adb_utils.check_ok(prefs_response, "Could not inspect clean Markor preferences")
    prefs = prefs_response.generic.output.decode("utf-8", errors="replace")
    if "pref_key__app_first_start_current_version" not in prefs:
        raise RuntimeError("Markor onboarding completion was not persisted")
    if "pref_key__new_file_dialog_lastused_extension" in prefs:
        raise RuntimeError("Markor reset retained a task-contaminated extension")
    force_stop = adb_utils.issue_generic_request(
        ["shell", "am", "force-stop", apps.MarkorApp.package_name()],
        target_env.controller,
        timeout_sec=60.0,
    )
    adb_utils.check_ok(force_stop, "Could not close Markor after reset")


def _setup_chrome_109_once(target_env: Any) -> None:
    """Reach Chrome's clean post-onboarding state without UIAutomator.

    Chrome 109 consumes enough memory that a UIAutomator dump can be OOM-killed
    on the frozen 2GB AVD. The APK, resolution, and three first-run screens are
    frozen, so use their verified coordinates and then validate both the real
    foreground activity and Chrome's persisted first-run flags.
    """
    from android_world.env import adb_utils
    from android_world.env.setup_device import apps

    package_name = apps.ChromeApp.package_name()
    cleared = adb_utils.clear_app_data(package_name, target_env.controller)
    adb_utils.check_ok(cleared, "Could not clear Chrome before setup")
    activity = adb_utils.get_adb_activity("chrome")
    if not activity:
        raise RuntimeError("Frozen AndroidWorld has no Chrome activity mapping")
    launched = adb_utils.start_activity(
        activity, extra_args=[], env=target_env.controller, timeout_sec=60.0
    )
    adb_utils.check_ok(launched, "Could not launch Chrome during setup")

    size_response = adb_utils.issue_generic_request(
        ["shell", "wm", "size"], target_env.controller, timeout_sec=60.0
    )
    adb_utils.check_ok(size_response, "Could not inspect frozen display size")
    size_text = size_response.generic.output.decode("utf-8", errors="replace")
    if "1080x2400" not in size_text:
        raise RuntimeError(f"Chrome setup requires frozen 1080x2400 AVD: {size_text!r}")

    def tap(x: int, y: int, label: str, delay: float) -> None:
        response = adb_utils.issue_generic_request(
            ["shell", "input", "tap", str(x), str(y)],
            target_env.controller,
            timeout_sec=60.0,
        )
        adb_utils.check_ok(response, label)
        time.sleep(delay)

    time.sleep(3.0)
    def current_activity() -> str | None:
        current, response = adb_utils.get_current_activity(
            target_env.controller, timeout_sec=10.0
        )
        adb_utils.check_ok(response, "Could not inspect Chrome setup activity")
        return current

    # Chrome 109 exposes either a newer "Use without an account" page or the
    # older terms -> sync sequence.
    tap(540, 1790, "Could not choose account-free Chrome setup", 10.0)
    current = current_activity()
    if current and "FirstRunActivity" in current:
        # The newer-page coordinate was inert on the old welcome page.
        tap(540, 2211, "Could not accept Chrome terms", 8.0)
        current = current_activity()
    if current and "FirstRunActivity" in current:
        # Old flow: decline sync. This coordinate is inert on the newer page,
        # and the final activity/pref checks below fail closed if it did not act.
        tap(150, 2240, "Could not decline Chrome sync", 10.0)
    # Both flows show the same notification rationale after the main activity
    # settles. Cold startup can display it well after the activity has changed,
    # so allow it to render before selecting its left "No thanks" button. The
    # persisted RequestCount below proves the dialog was actually processed.
    time.sleep(15.0)
    tap(280, 1480, "Could not dismiss Chrome notification promo", 5.0)

    current = current_activity()
    if not current or package_name not in current or "FirstRunActivity" in current:
        raise RuntimeError(f"Chrome onboarding did not reach main activity: {current!r}")
    prefs_response = adb_utils.issue_generic_request(
        [
            "shell", "su", "0", "cat",
            "/data/data/com.android.chrome/shared_prefs/com.android.chrome_preferences.xml",
        ],
        target_env.controller,
        timeout_sec=60.0,
    )
    adb_utils.check_ok(prefs_response, "Could not inspect Chrome first-run state")
    prefs = prefs_response.generic.output.decode("utf-8", errors="replace")
    required = (
        '<boolean name="first_run_tos_accepted" value="true" />',
        '<boolean name="first_run_signin_complete" value="true" />',
        'name="Chrome.NotificationPermission.RequestCount" value="1"',
    )
    missing = [item for item in required if item not in prefs]
    if missing:
        raise RuntimeError(f"Chrome first-run state is incomplete: missing={missing}")
    stopped = adb_utils.issue_generic_request(
        ["shell", "am", "force-stop", package_name],
        target_env.controller,
        timeout_sec=60.0,
    )
    adb_utils.check_ok(stopped, "Could not close Chrome after setup")


def _setup_chrome_109(target_env: Any) -> None:
    """Create the verified post-onboarding Chrome state without UIAutomator.

    The stock UI setup is not reliable on the frozen 2GB AVD: unrelated Google
    processes can make System UI/Launcher ANR before Chrome receives a tap.
    Generate Chrome's own base files, then apply only the five values produced
    by the already-observed successful onboarding. A frozen device-side script,
    a clean relaunch, activity checks, window checks, and persisted-value checks
    make this an auditable environment normalization rather than a silent skip.
    """
    from android_world.env import adb_utils

    def issue(command: list[str], label: str) -> Any:
        response = adb_utils.issue_generic_request(
            command, target_env.controller, timeout_sec=60.0
        )
        adb_utils.check_ok(response, label)
        return response

    for package in (
        "com.google.android.googlequicksearchbox",
        "com.google.android.apps.maps",
        "com.google.android.apps.photos",
        "com.google.android.apps.youtube.music",
        "com.google.android.gm",
        "com.google.android.youtube",
        "com.google.android.calendar",
        "com.google.android.apps.messaging",
        "com.google.android.as",
    ):
        issue(
            ["shell", "am", "force-stop", package],
            f"Could not stop unrelated background package {package}",
        )
    for package in (
        "com.android.systemui", "com.google.android.apps.nexuslauncher"
    ):
        issue(
            [
                "shell", "su", "0", "sh", "-c",
                f"pid=$(pidof {package}); test -z \"$pid\" || kill -9 $pid",
            ],
            f"Could not restart {package} before Chrome setup",
        )
    time.sleep(20.0)

    package_name = "com.android.chrome"
    cleared = adb_utils.clear_app_data(package_name, target_env.controller)
    adb_utils.check_ok(cleared, "Could not clear Chrome before setup")
    activity = adb_utils.get_adb_activity("chrome")
    if not activity:
        raise RuntimeError("Frozen AndroidWorld has no Chrome activity mapping")
    launched = adb_utils.start_activity(
        activity, extra_args=[], env=target_env.controller, timeout_sec=60.0
    )
    adb_utils.check_ok(launched, "Could not create Chrome base state")
    time.sleep(15.0)
    issue(
        ["shell", "am", "force-stop", package_name],
        "Could not stop Chrome before state normalization",
    )

    local_script = (
        Path(__file__).resolve().parents[4]
        / "scripts/android_c0_set_chrome_prefs.sh"
    )
    if not local_script.is_file():
        raise RuntimeError(f"Missing frozen Chrome state script: {local_script}")
    remote_script = "/data/local/tmp/c0_chrome/android_c0_set_chrome_prefs.sh"
    target_env.controller.push_file(
        str(local_script), remote_script, timeout_sec=60.0
    )
    issue(
        ["shell", "su", "0", "chmod", "755", remote_script],
        "Could not make Chrome state script executable",
    )
    issue(
        ["shell", "su", "0", "sh", remote_script],
        "Could not normalize Chrome post-onboarding state",
    )

    launched = adb_utils.start_activity(
        activity, extra_args=[], env=target_env.controller, timeout_sec=60.0
    )
    adb_utils.check_ok(launched, "Could not verify normalized Chrome state")
    time.sleep(25.0)
    current, response = adb_utils.get_current_activity(
        target_env.controller, timeout_sec=10.0
    )
    adb_utils.check_ok(response, "Could not inspect normalized Chrome activity")
    if not current or package_name not in current or "FirstRunActivity" in current:
        raise RuntimeError(f"Chrome normalization did not reach main activity: {current!r}")
    windows = issue(
        ["shell", "dumpsys", "window"],
        "Could not inspect Chrome window state",
    ).generic.output.decode("utf-8", errors="replace")
    if "AppErrorDialog" in windows or "Application Error" in windows:
        raise RuntimeError("Chrome normalization left an application-error dialog")
    prefs = issue(
        [
            "shell", "su", "0", "cat",
            "/data/data/com.android.chrome/shared_prefs/com.android.chrome_preferences.xml",
        ],
        "Could not inspect normalized Chrome preferences",
    ).generic.output.decode("utf-8", errors="replace")
    required = (
        '<boolean name="first_run_flow" value="true" />',
        '<boolean name="first_run_tos_accepted" value="true" />',
        '<boolean name="first_run_signin_complete" value="true" />',
        'name="Chrome.NotificationPermission.RequestCount" value="1"',
        'name="Chrome.NotificationPermission.RationaleTimestamp" value="1786290000000"',
    )
    missing = [item for item in required if item not in prefs]
    if missing:
        raise RuntimeError(f"Chrome normalized state is incomplete: missing={missing}")
    issue(
        ["shell", "am", "force-stop", package_name],
        "Could not close Chrome after state verification",
    )


def _ensure_osmand_marker_schema(target_env: Any) -> None:
    """Create OsmAnd's marker schema once, then leave the table empty.

    OsmAnd 4.6 does not create ``map_markers_db`` merely by reaching the map.
    AndroidWorld's OsmAndMarker evaluator nevertheless clears the table before
    every task. Trigger the app's own schema creation with one temporary marker,
    delete that row, and verify the clean empty-table invariant before the
    baseline snapshot is saved.
    """
    from android_world.env import adb_utils

    db_path = "/data/data/net.osmand/databases/map_markers_db"

    def issue(command: list[str], label: str) -> Any:
        response = adb_utils.issue_generic_request(
            command, target_env.controller, timeout_sec=60.0
        )
        adb_utils.check_ok(response, label)
        return response

    activity = adb_utils.get_adb_activity("osmand")
    if not activity:
        raise RuntimeError("Frozen AndroidWorld has no OsmAnd activity mapping")
    issue(
        ["shell", "am", "start", "-W", "-n", activity],
        "Could not launch OsmAnd for marker-schema setup",
    )
    time.sleep(8.0)
    # If the upstream setup missed its first-run control this selects
    # SKIP DOWNLOAD; on the normal map screen the same point is inert.
    issue(
        ["shell", "input", "tap", "850", "2265"],
        "Could not finish OsmAnd first-run setup",
    )
    time.sleep(8.0)
    issue(
        ["shell", "input", "swipe", "540", "1100", "540", "1100", "1200"],
        "Could not create OsmAnd temporary location",
    )
    time.sleep(4.0)
    issue(
        ["shell", "input", "tap", "405", "2145"],
        "Could not create OsmAnd temporary marker",
    )
    time.sleep(5.0)
    issue(
        ["shell", "su", "0", "test", "-f", db_path],
        "OsmAnd did not create map_markers_db",
    )
    table = issue(
        [
            "shell", "su", "0", "sqlite3", db_path, ".tables",
        ],
        "Could not inspect OsmAnd marker schema",
    )
    tables = table.generic.output.decode("utf-8", errors="replace").split()
    if "map_markers" not in tables:
        raise RuntimeError("OsmAnd map_markers table was not created")
    issue(
        [
            "shell", "su", "0", "sqlite3", db_path,
            "DELETE/**/FROM/**/map_markers;",
        ],
        "Could not clear the temporary OsmAnd marker",
    )
    remaining = issue(
        [
            "shell", "su", "0", "sqlite3", db_path,
            "SELECT/**/marker_id/**/FROM/**/map_markers/**/LIMIT/**/1;",
        ],
        "Could not verify clean OsmAnd marker table",
    )
    if remaining.generic.output.decode("utf-8", errors="replace").strip():
        raise RuntimeError("OsmAnd baseline snapshot retained a marker")
    issue(
        ["shell", "am", "force-stop", "net.osmand"],
        "Could not close OsmAnd after marker-schema setup",
    )


def _setup_app_checked(app_class: Any, target_env: Any) -> None:
    """Run an AndroidWorld app setup with checked, 60-second ADB helpers.

    AndroidWorld's stock ``launch_app`` hard-codes a five-second timeout and
    several setup classes ignore the response from ``clear_app_data``. Chrome
    can legitimately need longer than five seconds for a cold first launch on
    the frozen emulator. Keep each upstream setup routine intact, but make its
    transport operations fail closed and allow the same 60-second latency used
    by C0's scored action bridge.
    """
    from android_world.env import adb_utils

    if str(getattr(app_class, "app_name", "")) == "chrome":
        _setup_chrome_109(target_env)
        return

    original_launch_app = adb_utils.launch_app
    original_clear_app_data = adb_utils.clear_app_data

    def checked_launch(app_name: str, controller: Any) -> str:
        if app_name in adb_utils._DEFAULT_URIS:  # pylint: disable=protected-access
            response = adb_utils._launch_default_app(  # pylint: disable=protected-access
                app_name, controller, timeout_sec=60.0
            )
        else:
            activity = adb_utils.get_adb_activity(app_name)
            if activity is None:
                response = adb_utils.issue_generic_request(
                    ["shell", "monkey", "-p", app_name, "1"],
                    controller,
                    timeout_sec=60.0,
                )
            else:
                response = adb_utils.start_activity(
                    activity, extra_args=[], env=controller, timeout_sec=60.0
                )
        adb_utils.check_ok(response, f"Could not launch {app_name} during setup")
        return app_name

    def checked_clear(package_name: str, controller: Any) -> Any:
        response = original_clear_app_data(package_name, controller)
        adb_utils.check_ok(
            response, f"Could not clear {package_name} during app setup"
        )
        return response

    adb_utils.launch_app = checked_launch
    adb_utils.clear_app_data = checked_clear
    try:
        try:
            app_class.setup(target_env)
        except ValueError:
            # Some Android special permissions/default-app choices survive
            # ``pm clear``. The upstream setup then cannot find a first-run
            # button because the desired system state is already active. Only
            # accept those cases after directly verifying the intended state;
            # every other UI mismatch remains a hard failure.
            app_name = str(getattr(app_class, "app_name", ""))
            package_name = app_class.package_name()
            if app_name == "simple gallery pro":
                response = adb_utils.issue_generic_request(
                    ["shell", "appops", "get", package_name,
                     "MANAGE_EXTERNAL_STORAGE"],
                    target_env.controller,
                    timeout_sec=60.0,
                )
                adb_utils.check_ok(response, "Could not inspect Gallery app-op")
                output = response.generic.output.decode("utf-8", errors="replace")
                if "MANAGE_EXTERNAL_STORAGE: allow" not in output:
                    raise
            elif app_name == "simple sms messenger":
                response = adb_utils.issue_generic_request(
                    ["shell", "settings", "get", "secure",
                     "sms_default_application"],
                    target_env.controller,
                    timeout_sec=60.0,
                )
                adb_utils.check_ok(response, "Could not inspect default SMS app")
                selected = response.generic.output.decode(
                    "utf-8", errors="replace"
                ).strip()
                if selected != package_name:
                    raise
            elif app_name == "vlc":
                appop = adb_utils.issue_generic_request(
                    ["shell", "appops", "get", package_name,
                     "MANAGE_EXTERNAL_STORAGE"],
                    target_env.controller,
                    timeout_sec=60.0,
                )
                adb_utils.check_ok(appop, "Could not inspect VLC app-op")
                db = adb_utils.issue_generic_request(
                    ["shell", "su", "0", "test", "-f",
                     "/data/data/org.videolan.vlc/app_db/vlc_media.db"],
                    target_env.controller,
                    timeout_sec=60.0,
                )
                adb_utils.check_ok(db, "VLC media database was not created")
                output = appop.generic.output.decode("utf-8", errors="replace")
                if "MANAGE_EXTERNAL_STORAGE: allow" not in output:
                    raise
            else:
                raise
    finally:
        adb_utils.launch_app = original_launch_app
        adb_utils.clear_app_data = original_clear_app_data


def initialize_task_with_native_resets(task: Any, env: Any) -> dict[str, Any]:
    """Run normal AndroidWorld initialization plus MobileUse app resets.

    The reset is inserted immediately after AndroidWorld restores each app
    snapshot and before the concrete task initializes its seeded state. This is
    the same lifecycle location used by the MadeAgents AndroidWorld fork.
    """
    from android_world.env.setup_device import apps
    from android_world.utils import app_snapshot

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
        # AndroidWorld's stock implementation suppresses missing/corrupt
        # snapshot errors. C0 restores non-reset apps fail-closed and rebuilds
        # the documented reset apps from clean app data.
        for name in task.app_names:
            if not name or name == "clipper":
                continue
            if name not in mapping:
                app_snapshot.restore_snapshot(name, target_env.controller)
                continue
            # setup.setup_app suppresses ValueError and would let a failed
            # reset masquerade as success. C0 requires reset failure to stop
            # the suite, so execute the same two operations without suppression.
            if name == "markor":
                _setup_markor_146(target_env)
            else:
                from android_world.env import adb_utils
                preclear = adb_utils.clear_app_data(
                    mapping[name].package_name(), target_env.controller
                )
                adb_utils.check_ok(preclear, f"Could not clear {name} before setup")
                _setup_app_checked(mapping[name], target_env)
            app_snapshot.clear_snapshot(name, target_env.controller)
            app_snapshot.save_snapshot(name, target_env.controller)
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


def tear_down_without_recents_hang(task: Any, env: Any) -> None:
    """Run task-specific cleanup while skipping Android's deprecated stack removal.

    The frozen emulator hangs on ``am stack remove 0`` inside AndroidWorld's
    cosmetic close-recents helper. Task-specific data cleanup still runs; C0
    then returns Home separately in the runner.
    """
    from android_world.env import adb_utils
    from android_world.utils import app_snapshot

    original_close_recents = adb_utils.close_recents
    original_initialize_apps = task._initialize_apps

    def fail_closed_restore(_task: Any, target_env: Any) -> None:
        # BaseTask.tear_down() calls _initialize_apps() again, but the stock
        # implementation catches RuntimeError and continues. A missing or
        # corrupt snapshot would then silently contaminate the following C0
        # episode. Preserve the normal teardown lifecycle while making every
        # scored-app restore a hard qualification requirement.
        for name in task.app_names:
            if name and name != "clipper":
                app_snapshot.restore_snapshot(name, target_env.controller)

    task._initialize_apps = MethodType(fail_closed_restore, task)
    adb_utils.close_recents = lambda _controller: None
    try:
        task.tear_down(env)
    finally:
        adb_utils.close_recents = original_close_recents
        task._initialize_apps = original_initialize_apps


__all__ = [
    "RESET_APP_NAMES", "initialize_task_with_native_resets",
    "tear_down_without_recents_hang",
]
