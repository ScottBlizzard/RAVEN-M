"""Read-only audit of INFRA-M5 display observability for INFRA-M6."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.role_binding_timing.infra_m1_runtime import parse_runtime_state  # noqa: E402


M5_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m5_process_identity_semantics"
OUTPUT_ROOT = PROJECT_ROOT / "artifacts/role_binding_timing/infra_m6_display_observability_audit"
PARSER = PROJECT_ROOT / "src/raven_m/role_binding_timing/infra_m1_runtime.py"
B27_DISPLAY = PROJECT_ROOT / (
    "artifacts/role_binding_timing/phase_b2_7_ui_tree_export_diagnosis/"
    "preconditions/wake_dismiss_verified/verified.display.stdout.bin"
)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def marker(text: str, expression: str) -> bool:
    return bool(re.search(expression, text, flags=re.IGNORECASE | re.MULTILINE))


def record_for(index: int) -> dict[str, Any]:
    root = M5_ROOT / f"readiness/framework/attempt_{index:02d}/raw"
    paths = {name: root / f"{name}.stdout.bin" for name in ("power", "displays", "policy")}
    text = {name: path.read_text(encoding="utf-8", errors="strict") for name, path in paths.items()}
    parsed = parse_runtime_state(text["power"], text["displays"], text["policy"])
    direct = {
        "power_wakefulness_awake": marker(text["power"], r"^\s*mWakefulness=Awake\s*$"),
        "power_stay_on": marker(text["power"], r"^\s*mStayOn=true\s*$"),
        "power_hal_interactive": marker(text["power"], r"^\s*mHalInteractiveModeEnabled=true\s*$"),
        "power_display_suspend_blocker": marker(text["power"], r"^\s*mHoldingDisplaySuspendBlocker=true\s*$"),
        "window_display_geometry": marker(text["displays"], r"\binit=1080x2400\b.*\bcur=1080x2400\b"),
        "window_screen_on_early": marker(text["displays"], r"\bmScreenOnEarly=true\b"),
        "window_screen_on_fully": marker(text["displays"], r"\bmScreenOnFully=true\b"),
        "window_visible_task": marker(text["displays"], r"\bvisible=true\s+visibleRequested=true\b"),
        "window_current_focus": marker(text["displays"], r"^\s*mCurrentFocus=Window\{"),
        "policy_screen_state_on": marker(text["policy"], r"\bscreenState=SCREEN_STATE_ON\b"),
        "policy_interactive_awake": marker(text["policy"], r"\binteractiveState=INTERACTIVE_STATE_AWAKE\b"),
        "legacy_expected_marker_in_window_displays": marker(text["displays"], r"(?:state|mState)\s*(?:=|\s)\s*ON\b"),
    }
    return {
        "attempt": index,
        "raw": {
            name: {
                "path": path.relative_to(REPOSITORY_ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": digest(path),
            }
            for name, path in paths.items()
        },
        "frozen_parser_result": parsed,
        "direct_markers": direct,
        "all_nonlegacy_markers_present": all(value for key, value in direct.items() if key != "legacy_expected_marker_in_window_displays"),
    }


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    records = [record_for(index) for index in range(1, 21)]
    b27 = B27_DISPLAY.read_text(encoding="utf-8", errors="strict")
    b27_markers = {
        "display_device_state_on": marker(b27, r"DisplayDeviceInfo\{[^\n]+\bstate ON, committedState ON\b"),
        "logical_display_mstate_on": marker(b27, r"^\s*mState=ON\s*$"),
        "base_display_state_on": marker(b27, r"mBaseDisplayInfo=DisplayInfo\{[^\n]+\bstate ON, committedState ON\b"),
        "geometry_1080x2400": marker(b27, r"DisplayDeviceInfo\{[^\n]+\b1080 x 2400\b"),
    }
    summary = {
        "attempts": len(records),
        "legacy_parser_display_on_true": sum(item["frozen_parser_result"]["display_on"] for item in records),
        "all_nonlegacy_markers_present": sum(item["all_nonlegacy_markers_present"] for item in records),
        "marker_true_counts": {
            key: sum(item["direct_markers"][key] for item in records)
            for key in records[0]["direct_markers"]
        },
    }
    result = {
        "schema_version": "role_binding_timing.infra_m6.display_observability_audit.v1",
        "audit_date": "2026-08-05",
        "mode": "read_only_existing_evidence",
        "generation_calls": 0,
        "device_mutations": 0,
        "m5_verdict_immutable": "RUNTIME_UNSTABLE:FRAMEWORK_NOT_STABLE",
        "source_identity": {
            "m5_completion_commit": "3493c09c928ad37b004f63314dba0e22f6327df7",
            "m5_completion_sha256": digest(M5_ROOT / "qualification_completion.json"),
            "frozen_parser": {"path": PARSER.relative_to(REPOSITORY_ROOT).as_posix(), "sha256": digest(PARSER)},
            "installed_build_display_format_reference": {
                "development_contaminated": True,
                "held_out_eligible": False,
                "path": B27_DISPLAY.relative_to(REPOSITORY_ROOT).as_posix(),
                "bytes": B27_DISPLAY.stat().st_size,
                "sha256": digest(B27_DISPLAY),
                "markers": b27_markers,
            },
        },
        "summary": summary,
        "attempts": records,
        "classification": {
            "legacy_display_on_false": "MARKER_ABSENCE_OR_COMMAND_VERSION_MISMATCH",
            "physical_display_off": "NOT_ESTABLISHED",
            "usable_rendered_frame": "UNKNOWN",
            "reason": (
                "The frozen parser searched window-display output for state/mState ON. "
                "All M5 samples instead expose screen-on and visible-window witnesses in window/policy, "
                "while the installed-build dumpsys-display format reference contains the expected state ON markers. "
                "M5 captured neither dumpsys display, SurfaceFlinger evidence, nor a framework screencap."
            ),
        },
        "m6_required_evidence": [
            "dumpsys display physical and logical device state",
            "power wakefulness, HAL interactive mode, and display suspend blocker",
            "window display geometry, focused/visible surface, and screen-on policy markers",
            "SurfaceFlinger/display evidence when supported",
            "PNG-decoded screencap with expected geometry, nontrivial bytes, and nonuniform pixels",
        ],
        "claim_boundary": {
            "supported": "M5 display_on=false was a parser/command marker miss, not direct proof of OFF",
            "unsupported": [
                "M5 framebuffer was physically on",
                "M5 produced a usable rendered frame",
                "M5 would have passed a11y or the DEV grid",
                "any role-binding or memory claim",
            ],
        },
    }
    payload = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    audit_path = OUTPUT_ROOT / "display_observability_audit.json"
    audit_path.write_bytes(payload)
    manifest = {
        "schema_version": "role_binding_timing.infra_m6.audit_manifest.v1",
        "artifacts": [{
            "path": audit_path.relative_to(REPOSITORY_ROOT).as_posix(),
            "bytes": len(payload), "sha256": sha256(payload).hexdigest(),
        }],
    }
    (OUTPUT_ROOT / "artifact_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps({"summary": summary, "classification": result["classification"], "b27_markers": b27_markers}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
