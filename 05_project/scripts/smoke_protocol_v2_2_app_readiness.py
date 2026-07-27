"""Zero-model live smoke for protocol-v2.2 application readiness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
LOCAL_RUNTIME = REPOSITORY_ROOT / "06_local_runtime"
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(LOCAL_RUNTIME / "scripts"))

import androidworld_compat  # noqa: E402,F401
from raven_m.controller.episode_controller import EpisodeController  # noqa: E402
from raven_m.controller.protocol_v2_guard import (  # noqa: E402
    semantic_ui_snapshot,
)
from raven_m.env.androidworld_adapter import AndroidWorldAdapter  # noqa: E402
from protocol_v2_runtime import (  # noqa: E402
    initialize_androidworld_environment,
    utc_now,
    write_json,
)
from run_frozen_hard_suite import (  # noqa: E402
    load_androidworld_env,
    recover_androidworld_env,
)


APPS = (
    "Contacts",
    "Simple Calendar Pro",
    "Pro Expense",
    "Files",
)
SYSTEM_PACKAGES = {
    "com.android.systemui",
    "com.google.android.apps.nexuslauncher",
    "com.google.android.inputmethod.latin",
}


def value(element: Any, field: str) -> Any:
    if isinstance(element, dict):
        return element.get(field)
    return getattr(element, field, None)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adb-path", required=True)
    parser.add_argument("--console-port", type=int, default=5554)
    parser.add_argument("--grpc-port", type=int, default=8554)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT
        / "reports/protocol_v2_2_app_readiness_smoke.json",
    )
    parser.add_argument(
        "--startup-audit",
        type=Path,
        default=REPOSITORY_ROOT
        / "reports/protocol_v2_2_app_readiness_startup_audit.json",
    )
    args = parser.parse_args()

    env, startup = initialize_androidworld_environment(
        audit_path=args.startup_audit,
        load_fn=lambda: load_androidworld_env(
            adb_path=args.adb_path,
            console_port=args.console_port,
            grpc_port=args.grpc_port,
        ),
        recover_fn=lambda: recover_androidworld_env(
            adb_path=args.adb_path,
            console_port=args.console_port,
            grpc_port=args.grpc_port,
            recovery_dir=(
                args.output.parent / "protocol_v2_2_app_readiness_recovery"
            ),
        ),
    )
    controller = EpisodeController(
        client=None,  # type: ignore[arg-type]  # No model call in this smoke.
        system_prompt="",
        protocol_v2=True,
        protocol_v2_2=True,
    )
    adapter = AndroidWorldAdapter()
    records: list[dict[str, Any]] = []
    try:
        for index, app_name in enumerate(APPS, start=1):
            home = env.reset(go_home=True)
            height, width = home.pixels.shape[:2]
            mapped = adapter.map_action(
                {"type": "open_app", "app_name": app_name},
                screen_width=width,
                screen_height=height,
            )
            adapter.execute(env, mapped)
            state, readiness = controller._observe_state(  # noqa: SLF001
                env,
                require_accessibility=True,
            )
            elements = list(getattr(state, "ui_elements", ()))
            snapshot = semantic_ui_snapshot(
                elements,
                fallback_sha256="0" * 64,
            )
            packages = sorted(
                {
                    str(package)
                    for element in elements
                    if (package := value(element, "package_name"))
                }
            )
            application_packages = [
                package
                for package in packages
                if package not in SYSTEM_PACKAGES
            ]
            foreground_package = (
                env.foreground_activity_name.split("/", 1)[0]
                if env.foreground_activity_name
                else None
            )
            screenshot = args.output.with_name(
                f"{args.output.stem}_{index:02d}_{app_name.lower().replace(' ', '_')}.png"
            )
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(state.pixels).save(screenshot)
            passed = (
                snapshot["source"] == "accessibility"
                and snapshot["element_count"] > 0
                and not snapshot["infrastructure_failure_texts"]
                and foreground_package in application_packages
            )
            records.append(
                {
                    "app_name": app_name,
                    "passed": passed,
                    "foreground_activity": env.foreground_activity_name,
                    "foreground_package": foreground_package,
                    "packages": packages,
                    "application_packages": application_packages,
                    "readiness_observations": readiness,
                    "semantic_source": snapshot["source"],
                    "semantic_element_count": snapshot["element_count"],
                    "infrastructure_failure_texts": snapshot[
                        "infrastructure_failure_texts"
                    ],
                    "screenshot": str(screenshot),
                }
            )
    finally:
        env.close()

    passed = (
        len(records) == len(APPS)
        and all(record["passed"] for record in records)
        and startup["last_status"] in {"clean", "recovered"}
    )
    result = {
        "schema_version": "protocol_v2_2_app_readiness_smoke.v1",
        "checked_at": utc_now(),
        "passed": passed,
        "model_calls": 0,
        "gpu_experiment": False,
        "application_count": len(records),
        "applications": records,
        "startup_environment_status": startup["last_status"],
        "startup_environment_failure_count": startup["failure_count"],
        "startup_environment_recovery_success_count": startup[
            "recovery_success_count"
        ],
    }
    write_json(args.output, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
