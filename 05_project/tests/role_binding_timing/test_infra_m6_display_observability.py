from __future__ import annotations

import io

from PIL import Image
import pytest

from raven_m.role_binding_timing.infra_m4_terminal_accounting import PhaseJournal
from raven_m.role_binding_timing.infra_m5_process_identity import identity_key
from raven_m.role_binding_timing.infra_m6_display_observability import (
    M6StructuralIdentityPolicy,
    evaluate_display_quorum,
    parse_display_service,
    parse_power,
    parse_surfaceflinger,
    parse_window_state,
    validate_screencap,
)
from raven_m.role_binding_timing.infra_m6_terminal import finalize_completion


GEOMETRY = (32, 48)


def png(*, uniform: bool = False, size: tuple[int, int] = GEOMETRY) -> bytes:
    image = Image.new("RGB", size, (0, 0, 0))
    if not uniform:
        for x in range(size[0]):
            for y in range(size[1]):
                image.putpixel((x, y), ((x * 17) % 256, (y * 11) % 256, (x + y) % 256))
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


DISPLAY_ON = """
DisplayDeviceInfo{\"Built-in Screen\": uniqueId=local:0, 32 x 48, type INTERNAL, state ON, committedState ON}
  mState=ON
  mBaseDisplayInfo=DisplayInfo{displayId 0, real 32 x 48, state ON, committedState ON}
"""
POWER_ON = """
  mWakefulness=Awake
  mStayOn=true
  mHalInteractiveModeEnabled=true
  mHoldingDisplaySuspendBlocker=true
"""
WINDOW_ON = """
Display: mDisplayId=0 init=32x48 cur=32x48
  mCurrentFocus=Window{abc u0 launcher}
  visible=true visibleRequested=true
  mScreenOnEarly=true mScreenOnFully=true
"""
POLICY_ON = "screenState=SCREEN_STATE_ON interactiveState=INTERACTIVE_STATE_AWAKE"
SURFACE_ON = "Display 0 HWC layers: active composition"


def quorum(**overrides):
    values = {
        "display": DISPLAY_ON,
        "power": POWER_ON,
        "window_displays": WINDOW_ON,
        "window_policy": POLICY_ON,
        "surfaceflinger": SURFACE_ON,
        "surfaceflinger_command_succeeded": True,
        "screenshot": png(),
        "expected_geometry": GEOMETRY,
        "minimum_png_bytes": 64,
    }
    values.update(overrides)
    return evaluate_display_quorum(**values)


def test_installed_and_supported_display_output_variants() -> None:
    committed = parse_display_service(DISPLAY_ON, expected_geometry=GEOMETRY)
    legacy_variant = parse_display_service(
        'DisplayDeviceInfo{"Internal": 32 x 48, type INTERNAL, state ON}\n'
        'mOverrideDisplayInfo=DisplayInfo{real 32 x 48, state ON}\n',
        expected_geometry=GEOMETRY,
    )
    assert committed["passed"]
    assert legacy_variant["passed"]


def test_true_off_and_contradictory_display_fail_closed() -> None:
    off = DISPLAY_ON.replace("state ON, committedState ON", "state OFF, committedState OFF")
    assert not parse_display_service(off, expected_geometry=GEOMETRY)["passed"]
    contradictory = DISPLAY_ON.replace("committedState ON", "committedState OFF", 1)
    result = parse_display_service(contradictory, expected_geometry=GEOMETRY)
    assert not result["passed"]
    assert "COMMITTED_DISPLAY_NOT_ON" in result["vetoes"]


@pytest.mark.parametrize(
    ("parser", "args"),
    [
        (parse_display_service, {"text": "", "expected_geometry": GEOMETRY}),
        (parse_power, {"text": "mStayOn=true"}),
        (parse_window_state, {"displays": "", "policy": "", "expected_geometry": GEOMETRY}),
    ],
)
def test_missing_required_fields_fail_closed(parser, args) -> None:
    assert not parser(**args)["passed"]


def test_missing_legacy_marker_does_not_mean_off() -> None:
    result = quorum()
    assert result["passed"]
    assert result["legacy_marker_authoritative"] is False


def test_screenshot_alone_is_never_framework_authority() -> None:
    result = quorum(display="", power="", window_displays="", window_policy="")
    assert result["planes"]["screencap"]["passed"]
    assert not result["passed"]
    assert result["screenshot_alone_authoritative"] is False


def test_surfaceflinger_missing_is_optional_but_contradiction_is_veto() -> None:
    unavailable = quorum(surfaceflinger="", surfaceflinger_command_succeeded=False)
    contradiction = quorum(surfaceflinger="Display 0 is OFF", surfaceflinger_command_succeeded=True)
    assert unavailable["passed"]
    assert unavailable["planes"]["surfaceflinger"]["available"] is False
    assert not contradiction["passed"]


@pytest.mark.parametrize(
    "payload,expected_issue",
    [
        (b"not png", "PNG_SIGNATURE"),
        (png(uniform=True), "PNG_UNIFORM_PIXELS"),
        (png(size=(31, 48)), "PNG_GEOMETRY"),
        (png()[:80], "PNG_DECODE"),
    ],
)
def test_png_corruption_and_black_uniform_rejected(payload: bytes, expected_issue: str) -> None:
    result = validate_screencap(payload, expected_geometry=GEOMETRY, minimum_bytes=64)
    assert not result["passed"]
    assert any(item.startswith(expected_issue) for item in result["issues"])


def test_valid_nonuniform_png_records_geometry_and_color_evidence() -> None:
    result = validate_screencap(png(), expected_geometry=GEOMETRY, minimum_bytes=64)
    assert result["passed"]
    assert result["size"] == [32, 48]
    assert result["sampled_unique_colors"] > 1


def proc(pid, name, exe, digest, command, ppid, created):
    return {
        "pid": pid, "ppid": ppid, "name": name, "exe": exe,
        "command_line": command, "cmdline_items": command.split(),
        "create_time": float(created), "identity_key": f"{pid}@{float(created):.6f}",
        "exe_sha256": digest, "access_error": None,
    }


RUNNER = proc(10, "python.exe", "C:/Python/python.exe", "python-hash", "python runner.py", 1, 10)
ADB = proc(20, "adb.exe", "C:/locked/adb.exe", "adb-hash", "adb -L tcp:5038 fork-server server --reply-fd 7", 10, 20)
LAUNCHER = proc(30, "emulator.exe", "C:/locked/emulator.exe", "launcher-hash", "emulator -avd AndroidWorldAvd -port 5554 -grpc 8554 -no-window", 10, 30)
QEMU = proc(40, "qemu-system-x86_64-headless.exe", "C:/locked/qemu.exe", "qemu-hash", "qemu -avd AndroidWorldAvd -port 5554 -grpc 8554 -no-window", 30, 31)


def identity_config():
    return {
        "runtime": {"device_serial": "emulator-5554", "emulator_args": ["-avd", "AndroidWorldAvd", "-port", "5554", "-grpc", "8554", "-no-window"]},
        "process_identity": {
            "continuous_sample_interval_seconds": 0.25,
            "max_parent_depth": 8,
            "bootstrap_helper_window_seconds": 300,
            "runtime_helper_window_seconds": 900,
            "shutdown_helper": {"command_executable": "C:/locked/emulator", "sleep_seconds": 20},
            "binaries": {
                "adb": {"path": "C:/locked/adb.exe", "sha256": "adb-hash"},
                "emulator_launcher": {"path": "C:/locked/emulator.exe", "sha256": "launcher-hash"},
                "qemu": {"path": "C:/locked/qemu.exe", "sha256": "qemu-hash"},
                "crashpad": {"path": "C:/locked/crashpad.exe", "sha256": "crash-hash"},
                "netsimd": {"path": "C:/locked/netsimd.exe", "sha256": "netsim-hash"},
                "command_wrapper": {"path": "C:/Windows/System32/cmd.exe", "sha256": "cmd-hash"},
            },
        },
    }


def qualified_policy():
    policy = M6StructuralIdentityPolicy(identity_config(), runner_record=RUNNER)
    empty = {"structural_processes": [], "listeners": {str(port): [] for port in (5037, 5038, 5554, 5555, 8554)}}
    policy.freeze_baseline(empty)
    for role, value in (("adb_server", ADB), ("emulator_launcher", LAUNCHER), ("qemu", QEMU)):
        policy.register_core(role, value)
    policy.add_history([RUNNER, ADB, LAUNCHER, QEMU])
    return policy


def snapshot(extra):
    return {
        "structural_processes": [RUNNER, ADB, LAUNCHER, QEMU, *extra],
        "listeners": {"5037": [], "5038": [20], "5554": [40], "5555": [40], "8554": [40]},
    }


def shutdown_records():
    wrapper = proc(
        50, "cmd.exe", "C:/Windows/System32/cmd.exe", "cmd-hash",
        "/C C:/locked/emulator -kill 40 -sleep 20 >nul 2>&1", 40, 40,
    )
    helper = proc(
        51, "emulator.exe", "C:/locked/emulator.exe", "launcher-hash",
        "C:/locked/emulator -kill 40 -sleep 20", 50, 41,
    )
    return wrapper, helper


def test_exact_qemu_cmd_official_emulator_shutdown_chain_is_cleanup_only() -> None:
    wrapper, helper = shutdown_records()
    cleanup = qualified_policy().evaluate(snapshot([wrapper, helper]), phase="cleanup")
    framework = qualified_policy().evaluate(snapshot([wrapper, helper]), phase="framework")
    assert cleanup.passed, cleanup.issues
    assert cleanup.roles[identity_key(helper)] == "emulator_shutdown_helper"
    assert cleanup.helper_ancestry[identity_key(helper)] == [identity_key(wrapper), identity_key(QEMU)]
    assert not framework.passed


@pytest.mark.parametrize(
    ("mutation", "needle"),
    [
        ("helper_hash", "SHUTDOWN_HELPER_HASH"),
        ("helper_command", "SHUTDOWN_HELPER_COMMAND"),
        ("wrapper_hash", "SHUTDOWN_CMD_HASH"),
        ("wrapper_command", "SHUTDOWN_CMD_COMMAND"),
        ("wrapper_parent", "SHUTDOWN_CMD_PARENT"),
    ],
)
def test_shutdown_chain_rejects_every_identity_or_ancestry_mismatch(mutation: str, needle: str) -> None:
    wrapper, helper = shutdown_records()
    target, key = {
        "helper_hash": (helper, "exe_sha256"),
        "helper_command": (helper, "command_line"),
        "wrapper_hash": (wrapper, "exe_sha256"),
        "wrapper_command": (wrapper, "command_line"),
        "wrapper_parent": (wrapper, "ppid"),
    }[mutation]
    target[key] = 999 if key == "ppid" else "wrong"
    result = qualified_policy().evaluate(snapshot([wrapper, helper]), phase="cleanup")
    assert not result.passed
    assert any(needle in issue for issue in result.issues)


def test_pid_reuse_cannot_satisfy_shutdown_parent() -> None:
    wrapper, helper = shutdown_records()
    wrapper["create_time"] = 100.0
    wrapper["identity_key"] = "50@100.000000"
    helper["create_time"] = 41.0
    result = qualified_policy().evaluate(snapshot([wrapper, helper]), phase="cleanup")
    assert not result.passed
    assert any("SHUTDOWN_PARENT_TIME" in issue for issue in result.issues)


def test_m6_terminal_fallback_is_exactly_once_and_preserves_first_edge(tmp_path) -> None:
    journal = PhaseJournal(tmp_path / "phase_journal")
    journal.record(phase="framework", event="end", status="FAIL", first_broken_edge="DISPLAY:OFF")
    final = finalize_completion(
        output_root=tmp_path, journal=journal, run_id="test", status="RUNTIME_UNSTABLE",
        rich_completion=None,
    )
    assert final["first_broken_edge"] == "DISPLAY:OFF"
    assert final["generation_calls"] == 0
    assert final["claim_evidence"]["display_quorum_qualified"] is False
    with pytest.raises(RuntimeError, match="DUPLICATE_TERMINAL_COMPLETION"):
        finalize_completion(
            output_root=tmp_path, journal=journal, run_id="test", status="RUNTIME_UNSTABLE",
            rich_completion=None,
        )


def test_m6_rich_terminal_derives_display_claim_without_model_authority(tmp_path) -> None:
    journal = PhaseJournal(tmp_path / "phase_journal")
    rich = {
        "runtime": {"framework": {"passed": True}},
        "burn_in": {"passed": True},
        "claim_evidence": {"held_out_tested": False, "role_binding_hypothesis_tested": False},
    }
    final = finalize_completion(
        output_root=tmp_path, journal=journal, run_id="test", status="PASS_12_OF_12_DEV",
        rich_completion=rich,
    )
    assert final["terminal_mode"] == "rich"
    assert final["claim_evidence"]["display_quorum_qualified"] is True
    assert final["generation_calls"] == final["model_tokens"] == final["held_out_captures"] == 0
