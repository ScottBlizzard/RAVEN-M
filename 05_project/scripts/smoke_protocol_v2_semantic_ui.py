"""No-model live Android smoke for protocol-v2.1 semantic UI state."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
LOCAL_RUNTIME = REPOSITORY_ROOT / "06_local_runtime"
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
sys.path.insert(0, str(LOCAL_RUNTIME / "scripts"))

import androidworld_compat  # noqa: E402,F401
from raven_m.controller.protocol_v2_guard import (  # noqa: E402
    semantic_ui_snapshot,
)
from protocol_v2_runtime import (  # noqa: E402
    initialize_androidworld_environment,
    utc_now,
    write_json,
)
from run_frozen_hard_suite import (  # noqa: E402
    load_androidworld_env,
    recover_androidworld_env,
)


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
        / "reports/protocol_v2_semantic_ui_smoke.json",
    )
    parser.add_argument(
        "--startup-audit",
        type=Path,
        default=REPOSITORY_ROOT
        / "reports/protocol_v2_semantic_ui_startup_audit.json",
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
                args.output.parent / "protocol_v2_semantic_ui_recovery"
            ),
        ),
    )
    try:
        env.reset(go_home=True)
        state = env.get_state(wait_to_stabilize=True)
        elements = list(getattr(state, "ui_elements", ()))
        snapshot = semantic_ui_snapshot(
            elements,
            fallback_sha256="0" * 64,
        )
    finally:
        env.close()

    system_ui_count = sum(
        value(element, "package_name") == "com.android.systemui"
        for element in elements
    )
    passed = (
        bool(elements)
        and snapshot["source"] == "accessibility"
        and snapshot["element_count"] > 0
        and snapshot["sha256"] != "0" * 64
        and startup["last_status"] in {"clean", "recovered"}
    )
    result = {
        "schema_version": "protocol_v2_semantic_ui_smoke.v1",
        "checked_at": utc_now(),
        "passed": passed,
        "model_calls": 0,
        "gpu_experiment": False,
        "raw_ui_element_count": len(elements),
        "raw_system_ui_element_count": system_ui_count,
        "semantic_snapshot": snapshot,
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
