"""Collect one frozen B2.6 DEV launch-observability evidence bundle."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from qualify_role_binding_timing_b2_5_infrastructure import (  # noqa: E402
    ManagedAdb,
    framework_check,
    listener_pids,
    reset_app,
    save_bytes,
    save_text,
    sha256_path,
    write_json_atomic,
)
from raven_m.role_binding_timing.infrastructure_v0_2_5 import (  # noqa: E402
    parse_foreground_witnesses,
    parse_ui_tree,
    sha256_bytes,
    validate_png,
)
from raven_m.role_binding_timing.launch_diagnosis_v0_2_6 import (  # noqa: E402
    classify_post_wait_samples,
    task_agnostic_timeout_correction_authorized,
)


DIAGNOSIS_FREEZE_TAG = "role-binding-timing-b2.6-diagnosis-freeze-20260804"


def _compact_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in result.items()
        if key not in {"stdout", "stderr"}
    }


def _source_packages(activity: str, window: str, *, source: str) -> list[str]:
    witnesses = parse_foreground_witnesses(activity, window)
    return witnesses["activity_packages"] if source == "activity" else witnesses["window_packages"]


def _collect_sample(
    *,
    adb: ManagedAdb,
    root: Path,
    phase: str,
    index: int,
    expected_package: str,
    screen_size: tuple[int, int],
    timeout: float,
) -> dict[str, Any]:
    sample_root = root / phase / f"sample_{index:02d}"
    sample_root.mkdir(parents=True, exist_ok=False)
    text_commands = {
        "boot_sys": ["shell", "getprop", "sys.boot_completed"],
        "boot_dev": ["shell", "getprop", "dev.bootcomplete"],
        "bootanim": ["shell", "getprop", "init.svc.bootanim"],
        "power": ["shell", "dumpsys", "power"],
        "window_policy": ["shell", "dumpsys", "window", "policy"],
        "display": ["shell", "dumpsys", "display"],
        "activity_activities": ["shell", "dumpsys", "activity", "activities"],
        "activity_top": ["shell", "dumpsys", "activity", "top"],
        "window_windows": ["shell", "dumpsys", "window", "windows"],
        "window_displays": ["shell", "dumpsys", "window", "displays"],
        "process": ["shell", "pidof", expected_package],
    }
    records: dict[str, Any] = {}
    artifacts: dict[str, Any] = {}
    raw: dict[str, str] = {}
    for name, command in text_commands.items():
        result = adb.text(command, timeout=timeout)
        raw[name] = str(result["stdout"])
        records[name] = _compact_result(result)
        artifacts[name] = save_text(sample_root / f"{name}.txt", str(result["stdout"]))

    remote_xml = f"/sdcard/rbt_b26_{phase}_{index:02d}.xml"
    dump = adb.text(["shell", "uiautomator", "dump", remote_xml], timeout=timeout)
    xml_result, raw_xml = adb.bytes(["exec-out", "cat", remote_xml], timeout=timeout)
    artifacts["ui_tree"] = save_bytes(sample_root / "ui.xml", raw_xml)
    ui_tree_usable = False
    ui_packages: list[str] = []
    ui_error = None
    try:
        if dump["returncode"] != 0 or dump["timed_out"] or xml_result["returncode"] != 0:
            raise RuntimeError("UI_DUMP_COMMAND_FAILED")
        tree = parse_ui_tree(raw_xml)
        ui_packages = sorted({node.package for node in tree.nodes if node.package})
        ui_tree_usable = True
    except Exception as exc:
        ui_error = f"{type(exc).__name__}:{exc}"

    screenshot_result, screenshot = adb.bytes(["exec-out", "screencap", "-p"], timeout=timeout)
    artifacts["screenshot"] = save_bytes(sample_root / "screenshot.png", screenshot)
    screenshot_usable = False
    screenshot_error = None
    screenshot_validation = None
    try:
        if screenshot_result["returncode"] != 0 or screenshot_result["timed_out"]:
            raise RuntimeError("SCREENSHOT_COMMAND_FAILED")
        screenshot_validation = validate_png(screenshot, screen_size)
        screenshot_usable = True
    except Exception as exc:
        screenshot_error = f"{type(exc).__name__}:{exc}"

    foreground_packages = {
        "activity_activities": _source_packages(raw["activity_activities"], "", source="activity"),
        "activity_top": _source_packages(raw["activity_top"], "", source="activity"),
        "window_windows": _source_packages("", raw["window_windows"], source="window"),
        "window_displays": _source_packages("", raw["window_displays"], source="window"),
    }
    process_active = records["process"]["returncode"] == 0 and bool(raw["process"].strip())
    sample = {
        "sample": index,
        "phase": phase,
        "boot_complete": {
            "sys_boot_completed": raw["boot_sys"].strip(),
            "dev_bootcomplete": raw["boot_dev"].strip(),
            "bootanim": raw["bootanim"].strip(),
        },
        "power_markers": {
            "interactive_true": "mInteractive=true" in raw["power"],
            "wakefulness_awake": "Wakefulness: Awake" in raw["power"] or "mWakefulness=Awake" in raw["power"],
            "keyguard_showing": "showing=true" in raw["window_policy"].casefold(),
            "display_on": "state=ON" in raw["display"] or "mScreenState=ON" in raw["display"],
        },
        "foreground_packages": foreground_packages,
        "process_active": process_active,
        "process_stdout": raw["process"].strip(),
        "ui_tree_usable": ui_tree_usable,
        "ui_packages": ui_packages,
        "ui_error": ui_error,
        "screenshot_usable": screenshot_usable,
        "screenshot_error": screenshot_error,
        "screenshot_validation": screenshot_validation,
        "command_records": records,
        "ui_dump_record": _compact_result(dump),
        "ui_cat_record": _compact_result(xml_result),
        "screenshot_record": _compact_result(screenshot_result),
        "artifacts": artifacts,
        "expected_package": expected_package,
    }
    write_json_atomic(sample_root / "sample.json", sample)
    sample["sample_record"] = {
        "path": (sample_root / "sample.json").relative_to(REPOSITORY_ROOT).as_posix(),
        "sha256": sha256_path(sample_root / "sample.json"),
    }
    return sample


def _collect_logcat(adb: ManagedAdb, root: Path, tag: str, timeout: float) -> dict[str, Any]:
    result = adb.text(["logcat", "-d", "-v", "threadtime", "-s", f"{tag}:V", "*:S"], timeout=timeout)
    artifact = save_text(root / "logcat" / f"{tag}.txt", str(result["stdout"]))
    return {"result": _compact_result(result), "artifact": artifact}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT / "configs" / "role_binding_timing" / "phase_b2_6_launch_diagnosis.json",
    )
    parser.add_argument("--diagnosis-commit", required=True)
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config["generation_calls_authorized"] != 0 or config["generation_eligible"] is not False:
        raise RuntimeError("GENERATION_BOUNDARY")
    tag_commit = subprocess.check_output(
        ["git", "rev-list", "-n", "1", DIAGNOSIS_FREEZE_TAG], cwd=REPOSITORY_ROOT, text=True
    ).strip()
    if tag_commit != args.diagnosis_commit:
        raise RuntimeError("DIAGNOSIS_FREEZE_TAG_MISMATCH")
    root = REPOSITORY_ROOT / config["output_root"]
    if root.exists():
        raise RuntimeError("DIAGNOSIS_OUTPUT_NOT_FRESH")
    root.mkdir(parents=True)
    scene = config["scene"]
    sampling = config["sampling"]
    started = time.monotonic()
    adb = ManagedAdb(
        binary=REPOSITORY_ROOT / config["runtime"]["adb_binary"],
        expected_hash=config["runtime"]["adb_binary_sha256"],
        port=config["runtime"]["adb_server_port"],
        serial=config["runtime"]["device_serial"],
    )
    pre_samples: list[dict[str, Any]] = []
    post_wait_samples: list[dict[str, Any]] = []
    post_nonwait_samples: list[dict[str, Any]] = []
    primary_error = None
    cleanup = None
    wait_result = None
    nonwait_result = None
    framework_before = None
    logcats: dict[str, Any] = {}
    try:
        framework_before = framework_check(adb, ["package", "window", "activity"])
        if not framework_before["passed"]:
            raise RuntimeError("FRAMEWORK_BEFORE_FAILED")
        reset_before = reset_app(adb, scene["package"], sampling["command_timeout_seconds"])
        if not reset_before["passed"]:
            raise RuntimeError("RESET_BEFORE_FAILED")
        pre_samples.append(
            _collect_sample(
                adb=adb,
                root=root,
                phase="pre",
                index=1,
                expected_package=scene["package"],
                screen_size=tuple(config["runtime"]["screen_size"]),
                timeout=sampling["ui_dump_timeout_seconds"],
            )
        )
        logcat_clear = adb.text(["logcat", "-c"], timeout=10)
        if logcat_clear["returncode"] != 0 or logcat_clear["timed_out"]:
            raise RuntimeError("LOGCAT_CLEAR_FAILED")
        wait_result = adb.text(
            ["shell", "am", "start", "-W", "-n", scene["component"]],
            timeout=sampling["command_timeout_seconds"],
        )
        save_text(root / "launch" / "wait_stdout.txt", str(wait_result["stdout"]))
        save_text(root / "launch" / "wait_stderr.txt", str(wait_result["stderr"]))
        for index in range(1, sampling["post_wait_samples"] + 1):
            post_wait_samples.append(
                _collect_sample(
                    adb=adb,
                    root=root,
                    phase="post_wait",
                    index=index,
                    expected_package=scene["package"],
                    screen_size=tuple(config["runtime"]["screen_size"]),
                    timeout=sampling["ui_dump_timeout_seconds"],
                )
            )
            if index < sampling["post_wait_samples"]:
                time.sleep(sampling["sample_gap_seconds"])
        nonwait_result = adb.text(
            ["shell", "am", "start", "-n", scene["component"]],
            timeout=sampling["command_timeout_seconds"],
        )
        save_text(root / "launch" / "nonwait_stdout.txt", str(nonwait_result["stdout"]))
        save_text(root / "launch" / "nonwait_stderr.txt", str(nonwait_result["stderr"]))
        for index in range(1, sampling["post_nonwait_samples"] + 1):
            post_nonwait_samples.append(
                _collect_sample(
                    adb=adb,
                    root=root,
                    phase="post_nonwait",
                    index=index,
                    expected_package=scene["package"],
                    screen_size=tuple(config["runtime"]["screen_size"]),
                    timeout=sampling["ui_dump_timeout_seconds"],
                )
            )
            if index < sampling["post_nonwait_samples"]:
                time.sleep(sampling["sample_gap_seconds"])
        for tag in ("ActivityTaskManager", "WindowManager", "SurfaceFlinger"):
            logcats[tag] = _collect_logcat(adb, root, tag, sampling["command_timeout_seconds"])
    except Exception as exc:
        primary_error = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback_sha256": sha256_bytes(traceback.format_exc().encode("utf-8")),
        }
    finally:
        try:
            cleanup = reset_app(adb, scene["package"], sampling["command_timeout_seconds"])
        except Exception as exc:
            cleanup = {"passed": False, "error": f"{type(exc).__name__}:{exc}"}
    classification = classify_post_wait_samples(post_wait_samples, scene["package"])
    correction_authorized = task_agnostic_timeout_correction_authorized(classification)
    result = {
        "schema_version": "role_binding_timing.launch_diagnosis.v0_2_6",
        "study_id": config["study_id"],
        "generation_calls": 0,
        "generation_eligible": False,
        "dev_contaminated": True,
        "held_out_eligible": False,
        "diagnosis_freeze_commit": args.diagnosis_commit,
        "source_hashes": {
            "config": sha256_path(config_path),
            "runner": sha256_path(Path(__file__)),
            "classifier": sha256_path(PROJECT_ROOT / "src/raven_m/role_binding_timing/launch_diagnosis_v0_2_6.py"),
        },
        "server_owner": adb.owner,
        "framework_before": framework_before,
        "wait_launch": wait_result,
        "nonwait_launch": nonwait_result,
        "pre_samples": pre_samples,
        "post_wait_samples": post_wait_samples,
        "post_nonwait_samples": post_nonwait_samples,
        "logcats": logcats,
        "classification": classification,
        "task_agnostic_timeout_correction_authorized": correction_authorized,
        "primary_error": primary_error,
        "cleanup": cleanup,
        "terminal_listener_pids": listener_pids(config["runtime"]["adb_server_port"]),
        "wall_time_seconds": time.monotonic() - started,
    }
    write_json_atomic(root / "launch_diagnosis.v0_2_6.json", result)
    print(
        json.dumps(
            {
                "result": str(root / "launch_diagnosis.v0_2_6.json"),
                "outcome": classification["outcome"],
                "correction_authorized": correction_authorized,
                "generation_calls": 0,
            },
            indent=2,
        )
    )
    return 0 if primary_error is None else 2


if __name__ == "__main__":
    raise SystemExit(main())
