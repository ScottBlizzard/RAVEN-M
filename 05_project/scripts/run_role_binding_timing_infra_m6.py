"""Run the frozen INFRA-M6 display-observability maintenance chain."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.role_binding_timing.infra_m4_terminal_accounting import atomic_write_json, safe_jsonable  # noqa: E402
from raven_m.role_binding_timing.infra_m6_display_observability import (  # noqa: E402
    M6ProcessIdentityMonitor,
    evaluate_display_quorum,
)


def load_m5() -> Any:
    path = PROJECT_ROOT / "scripts/run_role_binding_timing_infra_m5.py"
    spec = importlib.util.spec_from_file_location("frozen_infra_m5_runner_for_m6", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("M5_RUNNER_LOAD_FAILURE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M5 = load_m5()


def _save(path: Path, value: Any) -> None:
    atomic_write_json(path, safe_jsonable(value), replace=False)


def _commands(*, include_setup: bool = False) -> dict[str, list[str]]:
    commands = {
        "package": ["shell", "service", "check", "package"],
        "window": ["shell", "service", "check", "window"],
        "activity": ["shell", "service", "check", "activity"],
        "power": ["shell", "dumpsys", "power"],
        "display": ["shell", "dumpsys", "display"],
        "window_displays": ["shell", "dumpsys", "window", "displays"],
        "window_policy": ["shell", "dumpsys", "window", "policy"],
        "activities": ["shell", "dumpsys", "activity", "activities"],
        "surfaceflinger": ["shell", "dumpsys", "SurfaceFlinger", "--display-id"],
        "screenshot": ["exec-out", "screencap", "-p"],
    }
    if include_setup:
        return {
            "get_state": ["get-state"],
            "boot_completed": ["shell", "getprop", "sys.boot_completed"],
            "wake": ["shell", "input", "keyevent", "224"],
            "dismiss_keyguard": ["shell", "wm", "dismiss-keyguard"],
            "home": ["shell", "input", "keyevent", "3"],
            **{f"service_{name}" if name in {"package", "window", "activity"} else name: value for name, value in commands.items()},
        }
    return commands


def _evaluate(
    config: dict[str, Any], records: dict[str, Any], payloads: dict[str, bytes],
    errors: dict[str, bytes], *, service_prefix: str = "",
) -> dict[str, Any]:
    required_commands = [
        f"{service_prefix}{name}" for name in ("package", "window", "activity")
    ] + ["power", "display", "window_displays", "window_policy", "activities", "screenshot"]
    command_issues = [
        f"COMMAND:{name}" for name in required_commands
        if name not in records or not M5.M2.strict_ok(records[name], errors[name])
    ]
    services = {
        name: M5.M2.parse_framework_service(payloads.get(f"{service_prefix}{name}", b""), name)
        for name in ("package", "window", "activity")
    }
    service_issues = [f"SERVICE:{name}" for name, passed in services.items() if not passed]
    geometry = tuple(config["display_quorum"]["expected_geometry"])
    surface_ok = (
        "surfaceflinger" in records
        and M5.M2.strict_ok(records["surfaceflinger"], errors["surfaceflinger"])
    )
    quorum = evaluate_display_quorum(
        display=payloads.get("display", b"").decode("utf-8", errors="replace"),
        power=payloads.get("power", b"").decode("utf-8", errors="replace"),
        window_displays=payloads.get("window_displays", b"").decode("utf-8", errors="replace"),
        window_policy=payloads.get("window_policy", b"").decode("utf-8", errors="replace"),
        surfaceflinger=payloads.get("surfaceflinger", b"").decode("utf-8", errors="replace"),
        surfaceflinger_command_succeeded=surface_ok,
        screenshot=payloads.get("screenshot", b""),
        expected_geometry=geometry,
        minimum_png_bytes=config["display_quorum"]["minimum_png_bytes"],
    )
    activity_issue = [] if payloads.get("activities", b"").strip() else ["ACTIVITY_DUMP_EMPTY"]
    issues = command_issues + service_issues + activity_issue + [f"DISPLAY_QUORUM:{item}" for item in quorum["issues"]]
    return {"passed": not issues and quorum["passed"], "issues": issues, "services": services, "display_quorum": quorum}


def framework_ready(config: dict[str, Any], root: Path, monitor: M6ProcessIdentityMonitor) -> dict[str, Any]:
    prefix = M5.M2.adb_prefix(config, 5038)
    setup: dict[str, Any] = {}
    for name, args in (
        ("wake", ["shell", "input", "keyevent", "224"]),
        ("dismiss_keyguard", ["shell", "wm", "dismiss-keyguard"]),
        ("home", ["shell", "input", "keyevent", "3"]),
    ):
        before = monitor.capture(gate=f"framework_setup_{name}_before", phase="framework")
        if not before["passed"]:
            return {"passed": False, "first_broken_edge": f"PROCESS_IDENTITY:{before['issues'][0]}", "setup": setup, "attempts": []}
        record, _, stderr = M5.M1.run_raw(prefix + args, root=root / "setup", name=name, timeout=15)
        after = monitor.capture(gate=f"framework_setup_{name}_after", phase="framework")
        setup[name] = {"record": record, "before_identity": before, "after_identity": after}
        if not after["passed"]:
            return {"passed": False, "first_broken_edge": f"PROCESS_IDENTITY:{after['issues'][0]}", "setup": setup, "attempts": []}
        if not M5.M2.strict_ok(record, stderr):
            return {"passed": False, "first_broken_edge": f"FRAMEWORK_SETUP:{name}", "setup": setup, "attempts": []}

    attempts: list[dict[str, Any]] = []
    consecutive = 0
    for index in range(1, config["maintenance"]["framework_stable_attempts"] + 1):
        attempt_root = root / f"attempt_{index:02d}"
        before = monitor.capture(gate=f"framework_{index:02d}_before", phase="framework")
        if not before["passed"]:
            return {"passed": False, "first_broken_edge": f"PROCESS_IDENTITY:{before['issues'][0]}", "setup": setup, "attempts": attempts}
        records, payloads, errors = M5.run_commands(
            commands={name: prefix + args for name, args in _commands().items()},
            root=attempt_root / "raw", timeout=config["display_quorum"]["command_timeout_seconds"],
        )
        after = monitor.capture(gate=f"framework_{index:02d}_after", phase="framework")
        evaluated = _evaluate(config, records, payloads, errors)
        issues = [*after["issues"], *evaluated["issues"]]
        passed = not issues and evaluated["passed"]
        consecutive = consecutive + 1 if passed else 0
        attempt = {
            "index": index, "passed": passed, "consecutive": consecutive,
            "before_identity": before, "after_identity": after, "issues": issues,
            "services": evaluated["services"], "display_quorum": evaluated["display_quorum"], "records": records,
        }
        _save(attempt_root / "attempt.json", attempt)
        attempts.append(attempt)
        if issues and after["issues"]:
            return {"passed": False, "first_broken_edge": f"PROCESS_IDENTITY:{after['issues'][0]}", "setup": setup, "attempts": attempts}
        if consecutive >= config["maintenance"]["framework_stable_required_consecutive"]:
            return {"passed": True, "first_broken_edge": None, "setup": setup, "attempts": attempts}
        if index < config["maintenance"]["framework_stable_attempts"]:
            time.sleep(config["maintenance"]["framework_stable_interval_seconds"])
    failure = {"first_broken_edge": "DISPLAY_FRAMEWORK_QUORUM_NOT_STABLE", "last_attempt": attempts[-1] if attempts else None}
    _save(root / "display_quorum_failure_snapshot.json", failure)
    return {"passed": False, "first_broken_edge": "DISPLAY_FRAMEWORK_QUORUM_NOT_STABLE", "setup": setup, "attempts": attempts}


def burn_in(config: dict[str, Any], root: Path, monitor: M6ProcessIdentityMonitor) -> dict[str, Any]:
    prefix = M5.M2.adb_prefix(config, 5038)
    burn = config["burn_in"]
    started = time.monotonic()
    records_out: list[dict[str, Any]] = []
    edge = None
    commands = _commands(include_setup=True)
    for index in range(1, burn["cycles"] + 1):
        cell_root = root / f"cycle_{index:02d}"
        before = monitor.capture(gate=f"burn_{index:02d}_before", phase="burn_in")
        issues = list(before["issues"])
        command_records: dict[str, Any] = {}
        payloads: dict[str, bytes] = {}
        errors: dict[str, bytes] = {}
        if not issues:
            command_records, payloads, errors = M5.run_commands(
                commands={name: prefix + args for name, args in commands.items()},
                root=cell_root / "raw", timeout=burn["command_timeout_seconds"],
            )
        after = monitor.capture(gate=f"burn_{index:02d}_after", phase="burn_in")
        issues.extend(after["issues"])
        evaluated = {"passed": False, "issues": [], "services": {}, "display_quorum": {}}
        if not issues and len(command_records) == len(commands):
            evaluated = _evaluate(config, command_records, payloads, errors, service_prefix="service_")
            issues.extend(evaluated["issues"])
            if payloads.get("get_state", b"").strip() != b"device":
                issues.append("DEVICE_STATE")
            if payloads.get("boot_completed", b"").strip() != b"1":
                issues.append("BOOT_STATE")
        elif not issues:
            issues.append("COMMAND_SET_INCOMPLETE")
        passed = not issues and evaluated["passed"]
        if not passed:
            edge = f"CYCLE_{index:02d}:{issues[0]}"
        cell = {
            "index": index, "passed": passed, "before_identity": before, "after_identity": after,
            "issues": issues, "services": evaluated["services"],
            "display_quorum": evaluated["display_quorum"], "records": command_records,
        }
        _save(cell_root / "cycle_result.json", cell)
        records_out.append(cell)
        if not passed:
            _save(root / "display_quorum_failure_snapshot.json", {"first_broken_edge": edge, "cycle": cell})
            break
        if index < burn["cycles"]:
            time.sleep(burn["cycle_interval_seconds"])
    elapsed = time.monotonic() - started
    passed = len(records_out) == burn["cycles"] and all(item["passed"] for item in records_out) and elapsed >= burn["minimum_elapsed_seconds"]
    if len(records_out) == burn["cycles"] and all(item["passed"] for item in records_out) and elapsed < burn["minimum_elapsed_seconds"]:
        edge = "MINIMUM_BURN_IN_DURATION"
    return {
        "passed": passed, "first_broken_edge": edge, "required_cycles": burn["cycles"],
        "completed_cycles": len(records_out), "passed_cycles": sum(bool(item["passed"]) for item in records_out),
        "elapsed_seconds": elapsed, "records": records_out,
    }


def main() -> int:
    # M5 remains immutable. These replacements affect only this loaded module instance.
    M5.ProcessIdentityMonitor = M6ProcessIdentityMonitor
    M5.framework_ready = framework_ready
    M5.burn_in = burn_in
    return M5.main()


if __name__ == "__main__":
    raise SystemExit(main())
