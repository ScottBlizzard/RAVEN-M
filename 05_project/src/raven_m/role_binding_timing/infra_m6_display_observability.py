"""Display-observability quorum and cleanup-only identity semantics for INFRA-M6."""

from __future__ import annotations

import io
import re
from typing import Any

from PIL import Image

from raven_m.role_binding_timing.infra_m5_process_identity import (
    ProcessIdentityMonitor,
    StructuralIdentityPolicy,
    identity_key,
    normalized_command,
    normalized_path,
    process_index,
    required_fields_present,
)


def _present(text: str, expression: str) -> bool:
    return bool(re.search(expression, text, flags=re.IGNORECASE | re.MULTILINE))


def _plane(required: dict[str, bool], optional: dict[str, bool], vetoes: list[str]) -> dict[str, Any]:
    missing = [name for name, value in required.items() if not value]
    return {
        "passed": not missing and not vetoes,
        "required_witnesses": required,
        "optional_witnesses": optional,
        "missing_required": missing,
        "vetoes": vetoes,
    }


def parse_display_service(text: str, *, expected_geometry: tuple[int, int]) -> dict[str, Any]:
    width, height = expected_geometry
    device_lines = [line for line in text.splitlines() if "DisplayDeviceInfo{" in line and "type INTERNAL" in line]
    physical_on = any(
        _present(line, r"\bstate\s+ON\b")
        and not _present(line, r"\bstate\s+(?:OFF|DOZE|DOZE_SUSPEND|UNKNOWN)\b")
        for line in device_lines
    )
    committed_seen = any(_present(line, r"\bcommittedState\b") for line in device_lines)
    committed_on = not committed_seen or any(_present(line, r"\bcommittedState\s+ON\b") for line in device_lines)
    logical_on = _present(text, r"^\s*mState\s*=\s*ON\s*$") or _present(
        text, r"(?:mBase|mOverride)?DisplayInfo\s*=\s*DisplayInfo\{[^\n]+\bstate\s+ON\b"
    )
    geometry = any(
        _present(line, rf"\b{width}\s*x\s*{height}\b") for line in device_lines
    ) or _present(text, rf"\b(?:real|app|logicalWidth|logicalHeight)[^\n]*{width}[^\n]*{height}\b")
    off = any(_present(line, r"\bstate\s+(?:OFF|DOZE|DOZE_SUSPEND)\b") for line in device_lines)
    committed_bad = committed_seen and any(
        _present(line, r"\bcommittedState\s+(?:OFF|DOZE|DOZE_SUSPEND|UNKNOWN)\b") for line in device_lines
    )
    vetoes = []
    if off:
        vetoes.append("INTERNAL_DISPLAY_NOT_ON")
    if committed_bad:
        vetoes.append("COMMITTED_DISPLAY_NOT_ON")
    return _plane(
        {
            "internal_physical_display_on": physical_on,
            "internal_committed_display_on_or_unreported": committed_on,
            "logical_display_on": logical_on,
            "expected_geometry": geometry,
        },
        {"committed_state_reported": committed_seen, "internal_device_record_present": bool(device_lines)},
        vetoes,
    )


def parse_power(text: str) -> dict[str, Any]:
    awake = _present(text, r"^\s*mWakefulness\s*=\s*Awake\s*$")
    hal_interactive = _present(text, r"^\s*mHalInteractiveModeEnabled\s*=\s*true\s*$")
    suspend_blocker = _present(text, r"^\s*mHoldingDisplaySuspendBlocker\s*=\s*true\s*$")
    vetoes = []
    if _present(text, r"^\s*mWakefulness\s*=\s*(?:Asleep|Dozing)\s*$"):
        vetoes.append("WAKEFULNESS_NOT_AWAKE")
    if _present(text, r"^\s*mHalInteractiveModeEnabled\s*=\s*false\s*$"):
        vetoes.append("HAL_NOT_INTERACTIVE")
    return _plane(
        {"wakefulness_awake": awake, "hal_interactive": hal_interactive, "display_suspend_blocker": suspend_blocker},
        {"stay_on": _present(text, r"^\s*mStayOn\s*=\s*true\s*$")},
        vetoes,
    )


def parse_window_state(displays: str, policy: str, *, expected_geometry: tuple[int, int]) -> dict[str, Any]:
    width, height = expected_geometry
    focus = _present(displays, r"^\s*mCurrentFocus=Window\{") and not _present(displays, r"^\s*mCurrentFocus=null\s*$")
    visible = _present(displays, r"\bvisible=true\s+visibleRequested=true\b") or _present(
        displays, r"\bisOnScreen=true\b"
    )
    screen_on = (
        _present(policy, r"\bscreenState=SCREEN_STATE_ON\b")
        and _present(policy, r"\binteractiveState=INTERACTIVE_STATE_AWAKE\b")
    ) or (
        _present(displays, r"\bmScreenOnEarly=true\b")
        and _present(displays, r"\bmScreenOnFully=true\b")
    )
    geometry = _present(displays, rf"\binit={width}x{height}\b.*\bcur={width}x{height}\b")
    vetoes = []
    if _present(policy, r"\bscreenState=SCREEN_STATE_OFF\b"):
        vetoes.append("WINDOW_POLICY_SCREEN_OFF")
    if _present(policy, r"\binteractiveState=INTERACTIVE_STATE_SLEEP\b"):
        vetoes.append("WINDOW_POLICY_NOT_INTERACTIVE")
    return _plane(
        {"focused_window": focus, "visible_surface_or_task": visible, "screen_on_policy": screen_on, "expected_geometry": geometry},
        {"keyguard_not_showing": not _present(policy + "\n" + displays, r"(?:mShowingLockscreen|showing)=true")},
        vetoes,
    )


def parse_surfaceflinger(text: str, *, command_succeeded: bool) -> dict[str, Any]:
    stripped = text.strip()
    if not command_succeeded or not stripped:
        return {
            "passed": True,
            "available": False,
            "required_witnesses": {},
            "optional_witnesses": {"surfaceflinger_display_evidence": False},
            "missing_required": [],
            "vetoes": [],
        }
    explicit_bad = _present(stripped, r"(?:display|power)[^\n]*(?:OFF|DISCONNECTED|DISABLED)")
    evidence = _present(
        stripped,
        r"(?:Physical display|Display\s+0|displayId|DisplayDevice|HWC layers|activeDisplay|Composition Display)",
    )
    vetoes = ["SURFACEFLINGER_EXPLICITLY_INACTIVE"] if explicit_bad else []
    # Available-but-unrecognized output is contradictory/insufficient, not silently ignored.
    if not evidence and not vetoes:
        vetoes.append("SURFACEFLINGER_OUTPUT_UNRECOGNIZED")
    return {
        "passed": not vetoes,
        "available": True,
        "required_witnesses": {},
        "optional_witnesses": {"surfaceflinger_display_evidence": evidence},
        "missing_required": [],
        "vetoes": vetoes,
    }


def validate_screencap(
    raw: bytes, *, expected_geometry: tuple[int, int], minimum_bytes: int,
) -> dict[str, Any]:
    issues: list[str] = []
    if len(raw) < minimum_bytes:
        issues.append("PNG_BYTES_BELOW_MINIMUM")
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        issues.append("PNG_SIGNATURE")
    size: tuple[int, int] | None = None
    mode: str | None = None
    extrema: list[list[int]] | None = None
    unique_sampled: int | None = None
    try:
        with Image.open(io.BytesIO(raw)) as image:
            image.verify()
        with Image.open(io.BytesIO(raw)) as image:
            rgb = image.convert("RGB")
            rgb.load()
            size = rgb.size
            mode = rgb.mode
            extrema = [[int(low), int(high)] for low, high in rgb.getextrema()]
            sampled = rgb.resize((min(64, rgb.width), min(64, rgb.height)))
            packed = sampled.tobytes()
            unique_sampled = len({packed[index:index + 3] for index in range(0, len(packed), 3)})
    except Exception as exc:
        issues.append(f"PNG_DECODE:{type(exc).__name__}:{exc}")
    if size is not None and size != expected_geometry:
        issues.append(f"PNG_GEOMETRY:{size}:{expected_geometry}")
    if extrema is not None and not any(low != high for low, high in extrema):
        issues.append("PNG_UNIFORM_PIXELS")
    if unique_sampled is not None and unique_sampled < 2:
        issues.append("PNG_NONTRIVIAL_SAMPLE")
    return {
        "passed": not issues,
        "bytes": len(raw),
        "size": list(size) if size else None,
        "mode": mode,
        "channel_extrema": extrema,
        "sampled_unique_colors": unique_sampled,
        "issues": issues,
    }


def evaluate_display_quorum(
    *, display: str, power: str, window_displays: str, window_policy: str,
    surfaceflinger: str, surfaceflinger_command_succeeded: bool, screenshot: bytes,
    expected_geometry: tuple[int, int], minimum_png_bytes: int,
) -> dict[str, Any]:
    planes = {
        "display_service": parse_display_service(display, expected_geometry=expected_geometry),
        "power": parse_power(power),
        "window": parse_window_state(window_displays, window_policy, expected_geometry=expected_geometry),
        "surfaceflinger": parse_surfaceflinger(surfaceflinger, command_succeeded=surfaceflinger_command_succeeded),
        "screencap": validate_screencap(screenshot, expected_geometry=expected_geometry, minimum_bytes=minimum_png_bytes),
    }
    required = ("display_service", "power", "window", "screencap")
    issues = [f"{name}:{issue}" for name in required for issue in (
        planes[name].get("missing_required", []) + planes[name].get("vetoes", []) + planes[name].get("issues", [])
    )]
    if not planes["surfaceflinger"]["passed"]:
        issues.extend(f"surfaceflinger:{item}" for item in planes["surfaceflinger"]["vetoes"])
    passed = all(planes[name]["passed"] for name in required) and planes["surfaceflinger"]["passed"]
    return {
        "schema_version": "role_binding_timing.infra_m6.display_quorum.v1",
        "passed": passed,
        "decision": "PASS" if passed else "FAIL_CLOSED",
        "required_planes": list(required),
        "optional_planes": ["surfaceflinger"],
        "planes": planes,
        "issues": issues,
        "legacy_marker_authoritative": False,
        "screenshot_alone_authoritative": False,
    }


class M6StructuralIdentityPolicy(StructuralIdentityPolicy):
    """M5 structural policy plus one exact cleanup-only shutdown ancestry."""

    def _classify_new(
        self, record: dict[str, Any], phase: str, current: dict[int, dict[str, Any]],
    ) -> tuple[str | None, list[str], list[str]]:
        if phase == "cleanup":
            accepted, issues, chain = self._exact_shutdown_chain(record, current)
            if accepted:
                return "emulator_shutdown_helper", [], chain
            binaries = self.config["process_identity"]["binaries"]
            if required_fields_present(record) and normalized_path(record.get("exe")) == normalized_path(
                binaries["emulator_launcher"]["path"]
            ):
                return None, issues or ["SHUTDOWN_CHAIN_REJECTED"], chain
        return super()._classify_new(record, phase, current)

    def _exact_shutdown_chain(
        self, record: dict[str, Any], current: dict[int, dict[str, Any]],
    ) -> tuple[bool, list[str], list[str]]:
        issues: list[str] = []
        chain: list[str] = []
        if not required_fields_present(record):
            return False, ["SHUTDOWN_HELPER_IDENTITY_MISSING"], chain
        qemu = self.core.get("qemu")
        if qemu is None:
            return False, ["SHUTDOWN_QEMU_NOT_REGISTERED"], chain
        binaries = self.config["process_identity"]["binaries"]
        if normalized_path(record.get("exe")) != normalized_path(binaries["emulator_launcher"]["path"]):
            return False, ["SHUTDOWN_HELPER_PATH"], chain
        if record.get("exe_sha256") != binaries["emulator_launcher"]["sha256"]:
            issues.append("SHUTDOWN_HELPER_HASH")
        shutdown = self.config["process_identity"]["shutdown_helper"]
        expected_child = normalized_command(
            f"{shutdown['command_executable']} -kill {qemu['pid']} -sleep {shutdown['sleep_seconds']}"
        )
        if normalized_command(record.get("command_line")) != expected_child:
            issues.append("SHUTDOWN_HELPER_COMMAND")
        history_by_pid = process_index(self.history.values())
        candidates = {**history_by_pid, **current}
        parent = candidates.get(record.get("ppid"))
        if parent is None or not required_fields_present(parent):
            return False, [*issues, "SHUTDOWN_CMD_PARENT_MISSING"], chain
        chain.append(identity_key(parent) or f"{parent.get('pid')}@INVALID")
        wrapper = binaries["command_wrapper"]
        if normalized_path(parent.get("exe")) != normalized_path(wrapper["path"]):
            issues.append("SHUTDOWN_CMD_PATH")
        if parent.get("exe_sha256") != wrapper["sha256"]:
            issues.append("SHUTDOWN_CMD_HASH")
        expected_cmd = normalized_command(
            f"/C {shutdown['command_executable']} -kill {qemu['pid']} "
            f"-sleep {shutdown['sleep_seconds']} >nul 2>&1"
        )
        if normalized_command(parent.get("command_line")) != expected_cmd:
            issues.append("SHUTDOWN_CMD_COMMAND")
        if parent.get("ppid") != qemu.get("pid"):
            issues.append("SHUTDOWN_CMD_PARENT")
        if float(parent.get("create_time") or 0) > float(record.get("create_time") or 0):
            issues.append("SHUTDOWN_PARENT_TIME")
        if float(parent.get("create_time") or 0) < float(qemu.get("create_time") or 0):
            issues.append("SHUTDOWN_BEFORE_QEMU")
        chain.append(identity_key(qemu) or f"{qemu.get('pid')}@INVALID")
        return not issues, issues, chain


class M6ProcessIdentityMonitor(ProcessIdentityMonitor):
    """Use the M6 policy while preserving M5 snapshots/history/journal behavior."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.policy = M6StructuralIdentityPolicy(kwargs["config"], runner_record=kwargs["runner_record"])
