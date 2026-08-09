"""Build and verify clean baseline snapshots for all 11 scored C0 apps."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import traceback

import run_mobileuse_c0 as c0
from raven_m.public_frameworks.mobileuse.c0_reset import (
    _ensure_osmand_marker_schema,
    _setup_app_checked,
    _setup_markor_146,
)


OUTPUT = c0.pf01.REPOSITORY_ROOT / (
    "evidence/public_framework/mobileuse_c0/C0_SNAPSHOT_PREFLIGHT.json"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    args = parser.parse_args()

    report = {
        "schema": "raven_m.c0.snapshot_preflight.v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "generation_calls": 0,
        "status": "fail",
        "errors": [],
        "source_freeze": c0.current_freeze(),
        "device_identity": c0.device_identity(args.adb_path, args.console_port),
        "apps": [],
    }
    env = None
    try:
        from android_world.env import adb_utils
        from android_world.env.setup_device import apps
        from android_world.utils import app_snapshot, file_utils

        mapping = {
            "chrome": apps.ChromeApp,
            "broccoli app": apps.RecipeApp,
            "markor": apps.MarkorApp,
            "open tracks sports tracker": apps.OpenTracksApp,
            "osmand": apps.OsmAndApp,
            "pro expense": apps.ExpenseApp,
            "retro music": apps.RetroMusicApp,
            "simple calendar pro": apps.SimpleCalendarProApp,
            "simple gallery pro": apps.SimpleGalleryProApp,
            "simple sms messenger": apps.SimpleSMSMessengerApp,
            "vlc": apps.VlcApp,
        }
        env = c0.pf01.env_launcher.load_and_setup_env(
            console_port=args.console_port, emulator_setup=False,
            freeze_datetime=True, adb_path=args.adb_path, grpc_port=args.grpc_port,
            a11y_method=c0.pf01.android_world_controller.A11yMethod.UIAUTOMATOR,
        )
        for name, app_class in mapping.items():
            if name == "markor":
                _setup_markor_146(env)
            else:
                response = adb_utils.clear_app_data(
                    app_class.package_name(), env.controller
                )
                adb_utils.check_ok(response, f"Could not preclear {name}")
                _setup_app_checked(app_class, env)
                if name == "osmand":
                    _ensure_osmand_marker_schema(env)
            app_snapshot.clear_snapshot(name, env.controller)
            app_snapshot.save_snapshot(name, env.controller)
            snapshot_path = app_snapshot._snapshot_path(name)
            exists = file_utils.check_directory_exists(snapshot_path, env.controller)
            if not exists:
                raise RuntimeError(f"Snapshot was not created for {name}")
            report["apps"].append({
                "name": name,
                "package": app_class.package_name(),
                "snapshot_path": snapshot_path,
                "pass": True,
            })
        env.reset(go_home=True)
        report["status"] = "pass"
    except Exception as exc:
        report["errors"].append({
            "type": type(exc).__name__, "message": str(exc),
            "traceback": traceback.format_exc(),
        })
    finally:
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
