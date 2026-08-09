"""No-model emulator qualification for C0 action and reset semantics."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import traceback

from PIL import Image
import numpy as np

import run_mobileuse_c0 as c0
from raven_m.public_frameworks.mobileuse.c0_controller import C0NativeMobileUseController
from raven_m.public_frameworks.mobileuse.c0_reset import (
    initialize_task_with_native_resets, tear_down_without_recents_hang,
)


OUTPUT_DIR = c0.pf01.REPOSITORY_ROOT / "evidence/public_framework/mobileuse_c0/live_preflight"
OUTPUT = c0.pf01.REPOSITORY_ROOT / "evidence/public_framework/mobileuse_c0/C0_LIVE_EMULATOR_PREFLIGHT.json"


class _NoGenerationClient:
    model_id = c0.MODEL_ID
    model_revision = c0.MODEL_REVISION
    base_url = "http://127.0.0.1:9"

    def generate_messages(self, **kwargs):  # pragma: no cover
        raise RuntimeError("Live C0 preflight must not call a model")


def _foreground(env):
    from android_world.env import adb_utils

    current, response = adb_utils.get_current_activity(env.controller, timeout_sec=10)
    adb_utils.check_ok(response, "Could not read foreground activity")
    return current


def _save(state, name: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"{name}.png"
    Image.fromarray(state.pixels).convert("RGB").save(path)
    return str(path.relative_to(c0.pf01.REPOSITORY_ROOT)).replace("\\", "/")


def _find(state, predicate, label: str):
    matches = [element for element in state.ui_elements if predicate(element)]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one {label}, found {len(matches)}")
    return matches[0]


def _center(element) -> tuple[int, int]:
    box = element.bbox_pixels
    return ((int(box.x_min) + int(box.x_max)) // 2, (int(box.y_min) + int(box.y_max)) // 2)


def _is_text_field(element) -> bool:
    """Accept both AndroidWorld's flag and Markor's real EditText metadata."""
    return bool(getattr(element, "is_editable", False)) or (
        getattr(element, "class_name", "") == "android.widget.EditText"
        and bool(getattr(element, "is_focusable", False))
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    args = parser.parse_args()

    static = json.loads(c0.PREFLIGHT_PATH.read_text(encoding="utf-8"))
    if static.get("status") != "pass" or static.get("file_sha256") != c0.current_freeze():
        raise RuntimeError("Run the current C0 static preflight before live qualification")
    snapshots = json.loads(c0.SNAPSHOT_PREFLIGHT_PATH.read_text(encoding="utf-8"))
    if (
        snapshots.get("status") != "pass"
        or snapshots.get("source_freeze") != c0.current_freeze()
        or snapshots.get("device_identity")
        != c0.device_identity(args.adb_path, args.console_port)
    ):
        raise RuntimeError("Run the current C0 snapshot preflight before live qualification")

    report = {
        "schema": "raven_m.c0.live_emulator_preflight.v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "generation_calls": 0,
        "status": "fail",
        "errors": [],
        "source_freeze": c0.current_freeze(),
        "device_identity": c0.device_identity(args.adb_path, args.console_port),
        "checks": {},
        "screenshots": [],
    }
    env = None
    tasks = []
    try:
        if OUTPUT_DIR.is_dir():
            shutil.rmtree(OUTPUT_DIR)
        env = c0.pf01.env_launcher.load_and_setup_env(
            console_port=args.console_port, emulator_setup=False,
            freeze_datetime=True, adb_path=args.adb_path, grpc_port=args.grpc_port,
            a11y_method=c0.pf01.android_world_controller.A11yMethod.UIAUTOMATOR,
        )
        registered_imes = subprocess.run(
            [args.adb_path, "-s", f"emulator-{args.console_port}", "shell", "ime", "list", "-s"],
            check=True, capture_output=True, text=True, timeout=30,
        ).stdout.splitlines()
        adb_ime = "com.android.adbkeyboard/.AdbIME"
        report["checks"]["adb_keyboard_registered"] = {
            "required": adb_ime,
            "registered": registered_imes,
            "pass": adb_ime in registered_imes,
        }
        if adb_ime not in registered_imes:
            raise RuntimeError("The frozen ADB keyboard is not registered on the scored emulator")
        registry_value = c0.pf01.registry.TaskRegistry().get_registry(
            c0.pf01.registry.TaskRegistry.ANDROID_WORLD_FAMILY
        )
        specs = {item["task_id"]: item for item in c0.load_specs()}

        # Exercise every reset-bearing app that occurs in the frozen 19 tasks.
        reset_reports = []
        covered = set()
        for task_id in c0.TASK_ORDER:
            task = c0.pf01.instantiate_verified(registry_value, specs[task_id])
            relevant = set(task.app_names) & {"audio recorder", "camera", "tasks", "markor", "simple calendar pro", "chrome"}
            tasks.append(task)
            audit = initialize_task_with_native_resets(task, env)
            env.reset(go_home=bool(getattr(task, "start_on_home_screen", True)))
            hide = getattr(env, "hide_automation_ui", None)
            if callable(hide):
                hide()
            post_initialize = env.get_state(wait_to_stabilize=True)
            post_activity = _foreground(env)
            audit["post_initialize_foreground"] = post_activity
            audit["post_initialize_home_pass"] = "nexuslauncher" in (post_activity or "")
            if not audit["post_initialize_home_pass"]:
                raise RuntimeError(
                    f"Task {task_id} did not return Home before its first model observation"
                )
            reset_reports.append(audit)
            covered.update(audit["completed_resets"])
            tear_down_without_recents_hang(task, env)
            tasks.pop()
            env.reset(go_home=True)
        expected = {
            name
            for spec in specs.values()
            for name in c0.pf01.instantiate_verified(registry_value, spec).app_names
            if name in {"audio recorder", "camera", "tasks", "markor", "simple calendar pro", "chrome"}
        }
        report["checks"]["scored_relevant_app_resets"] = {
            "expected": sorted(expected), "covered": sorted(covered),
            "pass": covered == expected, "audits": reset_reports,
        }
        if covered != expected:
            raise RuntimeError(f"Reset coverage mismatch: expected={expected}, covered={covered}")

        markor_prefs = subprocess.run(
            [
                args.adb_path, "-s", f"emulator-{args.console_port}", "shell",
                "su", "0", "cat",
                "/data/data/net.gsantner.markor/shared_prefs/app.xml",
            ],
            check=True, capture_output=True, text=True, timeout=30,
        ).stdout
        extension_match = re.search(
            r'<string name="pref_key__new_file_dialog_lastused_extension">([^<]+)</string>',
            markor_prefs,
        )
        markor_extension = extension_match.group(1) if extension_match else None
        report["checks"]["markor_last_used_extension_is_clean"] = {
            "value": markor_extension,
            "pass": markor_extension is None,
        }
        if markor_extension is not None:
            raise RuntimeError(
                "Markor reset retained a task-contaminated last-used extension: "
                f"{markor_extension!r}"
            )

        env.reset(go_home=True)
        initial = env.get_state(wait_to_stabilize=True)
        report["screenshots"].append(_save(initial, "00_home_before"))
        controller = C0NativeMobileUseController(
            _NoGenerationClient(), env=env, episode_id="C0_LIVE_NO_MODEL",
            episode_dir=OUTPUT_DIR / "controller", max_steps=3, max_tokens=64,
        )
        from mobile_use.schema.schema import Action

        controller.bridge.execute_action(Action("open", {"text": "markor"}))
        opened = env.get_state(wait_to_stabilize=True)
        report["screenshots"].append(_save(opened, "01_markor_open"))
        report["checks"]["open_app_name"] = {
            "foreground": _foreground(env),
            "pass": (_foreground(env) or "").startswith("net.gsantner.markor/"),
        }
        if not report["checks"]["open_app_name"]["pass"]:
            raise RuntimeError("open('markor') did not resolve to Markor")

        search = _find(opened, lambda x: getattr(x, "content_description", "") == "Search", "Markor search control")
        controller.bridge.execute_action(Action("click", {"coordinate": _center(search)}))
        focused = env.get_state(wait_to_stabilize=True)
        editable = _find(focused, _is_text_field, "editable search field")
        sentinel = "C0NoEnter7319"
        controller.bridge.execute_action(Action("type", {"text": sentinel}))
        typed = env.get_state(wait_to_stabilize=True)
        report["screenshots"].append(_save(typed, "02_typed_without_enter"))
        typed_values = [
            (getattr(x, "text", "") or "") for x in typed.ui_elements
            if _is_text_field(x)
        ]
        sentinel_count = sum(value.count(sentinel) for value in typed_values)
        typed_present = sentinel_count == 1 and any(value == sentinel for value in typed_values)
        still_markor = (_foreground(env) or "").startswith("net.gsantner.markor/")
        report["checks"]["type_without_enter"] = {
            "editable_values": typed_values, "sentinel_exact_count": sentinel_count,
            "foreground_still_markor": still_markor,
            "pass": typed_present and still_markor,
        }
        if not typed_present or not still_markor:
            raise RuntimeError("C0 type either failed or triggered an unintended Enter/navigation")

        typed_editable = _find(typed, _is_text_field, "typed search field")
        controller.bridge.execute_action(Action("long_press", {"coordinate": _center(typed_editable), "time": 1.0}))
        long_pressed = env.get_state(wait_to_stabilize=True)
        report["screenshots"].append(_save(long_pressed, "03_long_pressed"))
        long_press_changed = not np.array_equal(
            np.asarray(typed.pixels), np.asarray(long_pressed.pixels)
        )
        controller.bridge.execute_action(Action("wait", {"time": 0.2}))
        report["checks"]["long_press_and_wait"] = {
            "observable_screen_change": long_press_changed,
            "pass": long_press_changed,
        }
        if not long_press_changed:
            raise RuntimeError("C0 long_press produced no observable selection feedback")

        controller.bridge.execute_action(Action("clear_text", {}))
        cleared = env.get_state(wait_to_stabilize=True)
        report["screenshots"].append(_save(cleared, "04_cleared"))
        cleared_editable = _find(
            cleared, _is_text_field,
            "cleared search field",
        )
        cleared_value = getattr(cleared_editable, "text", "") or ""
        cleared_markor = (_foreground(env) or "").startswith("net.gsantner.markor/")
        # Markor exposes the empty field's accessibility hint ("Search") as
        # element.text.  The transition from our unique sentinel to this
        # frozen empty-state hint is the observable clear assertion.
        cleared_ok = cleared_value in {"", "Search"} and cleared_markor
        report["checks"]["clear_text"] = {
            "editable_value": cleared_value,
            "foreground_still_markor": cleared_markor,
            "pass": cleared_ok,
        }
        if not cleared_ok:
            raise RuntimeError("C0 clear_text did not leave the active Markor field empty")

        controller.bridge.execute_action(Action("system_button", {"button": "Enter"}))
        enter_activity = _foreground(env)
        enter_ok = (enter_activity or "").startswith("net.gsantner.markor/")
        report["checks"]["enter"] = {"foreground": enter_activity, "pass": enter_ok}
        if not enter_ok:
            raise RuntimeError("C0 Enter unexpectedly left Markor")

        controller.bridge.execute_action(Action("press_back", {}))
        backed = env.get_state(wait_to_stabilize=True)
        report["screenshots"].append(_save(backed, "05_back_after_search"))
        back_activity = _foreground(env)
        back_ok = (back_activity or "").startswith("net.gsantner.markor/")
        report["checks"]["back"] = {"foreground": back_activity, "pass": back_ok}
        if not back_ok:
            raise RuntimeError("C0 Back unexpectedly left Markor")

        controller.bridge.execute_action(Action("open", {"text": "settings"}))
        settings_before = env.get_state(wait_to_stabilize=True)
        report["screenshots"].append(_save(settings_before, "06_settings_before_swipe"))
        settings_height, settings_width = settings_before.pixels.shape[:2]
        controller.bridge.execute_action(Action(
            "swipe",
            {
                "coordinate": [settings_width // 2, round(settings_height * 0.72)],
                "coordinate2": [settings_width // 2, round(settings_height * 0.30)],
            },
        ))
        settings_after = env.get_state(wait_to_stabilize=True)
        report["screenshots"].append(_save(settings_after, "07_settings_after_swipe"))
        swipe_activity = _foreground(env)
        swipe_changed = not np.array_equal(
            np.asarray(settings_before.pixels), np.asarray(settings_after.pixels)
        )
        swipe_ok = (swipe_activity or "").startswith("com.android.settings/") and swipe_changed
        report["checks"]["swipe"] = {
            "foreground": swipe_activity,
            "observable_screen_change": swipe_changed,
            "pass": swipe_ok,
        }
        if not swipe_ok:
            raise RuntimeError("C0 swipe did not visibly scroll the Settings list")

        controller.bridge.execute_action(Action("open", {"text": "markor"}))
        markor_before_key = env.get_state(wait_to_stabilize=True)
        controller.bridge.execute_action(Action("key", {"text": "VOLUME_DOWN"}))
        after_volume = env.get_state(wait_to_stabilize=True)
        volume_overlay_changed = not np.array_equal(
            np.asarray(markor_before_key.pixels), np.asarray(after_volume.pixels)
        )
        controller.bridge.execute_action(Action("key", {"text": "VOLUME_UP"}))
        controller.bridge.execute_action(Action("system_button", {"button": "Menu"}))
        menu_activity = _foreground(env)
        key_ok = (menu_activity or "").startswith("net.gsantner.markor/")
        report["checks"]["key_and_menu"] = {
            "foreground": menu_activity,
            "volume_overlay_changed": volume_overlay_changed,
            "pass": key_ok and volume_overlay_changed,
        }
        if not key_ok or not volume_overlay_changed:
            raise RuntimeError("C0 key/Menu sequence unexpectedly left Markor")

        controller.bridge.execute_action(Action("system_button", {"button": "Home"}))
        home = env.get_state(wait_to_stabilize=True)
        report["screenshots"].append(_save(home, "08_home_after"))
        home_activity = _foreground(env)
        home_ok = "nexuslauncher" in (home_activity or "")
        report["checks"]["home"] = {"foreground": home_activity, "pass": home_ok}
        if not home_ok:
            raise RuntimeError("C0 Home did not return to launcher")

        if controller.bridge.execution_errors:
            raise RuntimeError(f"Bridge recorded execution errors: {controller.bridge.execution_errors}")
        report["status"] = "pass"
    except Exception as exc:
        report["errors"].append({
            "type": type(exc).__name__, "message": str(exc),
            "traceback": traceback.format_exc(),
        })
    finally:
        for task in tasks:
            try:
                tear_down_without_recents_hang(task, env)
            except Exception:
                pass
        if env is not None:
            try:
                env.reset(go_home=True)
            finally:
                env.close()
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
