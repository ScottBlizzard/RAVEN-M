from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from raven_m.role_binding_timing.ui_tree_export_v0_2_7 import (
    classify_root_cause,
    extract_xml_payload,
    parse_state_markers,
    qualify_paths,
    validate_xml_bytes,
)


ROOT = Path(__file__).resolve().parents[2]


def valid_xml(package: str = "com.example") -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<hierarchy rotation="0"><node index="0" text="Settings" resource-id="com.example:id/title" '
        f'class="android.widget.TextView" package="{package}" content-desc="" clickable="false" '
        'enabled="true" bounds="[0,0][100,100]"/></hierarchy>'
    ).encode()


def attempt(
    *,
    precondition: str,
    form_id: str,
    repeat: int,
    valid: bool,
    transport: str = "remote_file",
    envelope_found: bool | None = None,
) -> dict:
    return {
        "precondition": precondition,
        "form_id": form_id,
        "repeat": repeat,
        "transport": transport,
        "compressed": False,
        "xml_validation": {
            "valid": valid,
            "envelope_found": valid if envelope_found is None else envelope_found,
        },
        "adb_identity_continuous": True,
        "state_markers_before": {"interactive_verified": True},
    }


def test_extracts_xml_from_direct_stdout_wrapper() -> None:
    raw = b"warning before\n" + valid_xml() + b"\nUI hierarchy dumped to: /dev/tty\n"
    assert extract_xml_payload(raw) == valid_xml()
    result = validate_xml_bytes(raw, expected_package="com.example")
    assert result.valid
    assert result.root_tag == "hierarchy"
    assert result.node_count == 1
    assert result.semantic_node_count == 1


def test_rejects_missing_truncated_and_multiple_envelopes() -> None:
    assert not validate_xml_bytes(b"UI hierarchy dumped", expected_package=None).valid
    assert not validate_xml_bytes(valid_xml()[:-5], expected_package=None).valid
    try:
        extract_xml_payload(valid_xml() + valid_xml())
    except ValueError as exc:
        assert "MULTIPLE_XML_ENVELOPES" in str(exc)
    else:
        raise AssertionError("multiple XML envelopes were accepted")


def test_rejects_wrong_package_and_content_free_tree() -> None:
    assert not validate_xml_bytes(valid_xml("com.other"), expected_package="com.example").valid
    raw = (
        '<?xml version="1.0"?><hierarchy><node package="com.example" text="" '
        'content-desc="" resource-id=""/></hierarchy>'
    ).encode()
    assert "NO_SEMANTIC_NODES" in (validate_xml_bytes(raw, expected_package="com.example").error or "")


def test_interactive_parser_uses_display_marker_missing_from_b2_6_power_parser() -> None:
    markers = parse_state_markers(
        power="mWakefulness=Awake",
        display="mInteractive=true\nstate=ON",
        window_policy="showing=false",
        device_idle="mDeepIdleMode=false\nmLightIdleMode=false",
    )
    assert markers["interactive_verified"] is True
    assert markers["display_interactive"] is True
    assert markers["power_interactive"] is False


def test_interactive_parser_fails_closed_for_keyguard_or_sleep() -> None:
    assert not parse_state_markers(
        power="mWakefulness=Asleep",
        display="mInteractive=true\nstate=ON",
        window_policy="showing=false",
        device_idle="",
    )["interactive_verified"]
    assert not parse_state_markers(
        power="mWakefulness=Awake",
        display="mInteractive=true\nstate=ON",
        window_policy="showing=true",
        device_idle="",
    )["interactive_verified"]


def test_path_qualification_requires_both_repeats_identity_and_interactivity() -> None:
    attempts = [
        attempt(precondition="observed", form_id="file_normal", repeat=1, valid=True),
        attempt(precondition="observed", form_id="file_normal", repeat=2, valid=True),
    ]
    assert len(qualify_paths(attempts, 2)) == 1
    attempts[1]["adb_identity_continuous"] = False
    assert qualify_paths(attempts, 2) == []


def test_root_cause_noninteractive_transition() -> None:
    attempts = [
        attempt(precondition="observed", form_id="file_normal", repeat=1, valid=False),
        attempt(precondition="wake_dismiss_verified", form_id="file_normal", repeat=1, valid=True),
        attempt(precondition="wake_dismiss_verified", form_id="file_normal", repeat=2, valid=True),
    ]
    result = classify_root_cause(
        attempts=attempts,
        qualified_paths=qualify_paths(attempts, 2),
        baseline_interactive=False,
        wake_interactive=True,
    )
    assert result["root_cause"] == "DEVICE_NON_INTERACTIVE_OR_IDLE_STATE_FAILURE"


def test_root_cause_remote_file_creation() -> None:
    attempts = [
        attempt(precondition="observed", form_id="stdout_normal", repeat=1, valid=True, transport="direct_stdout"),
        attempt(precondition="observed", form_id="stdout_normal", repeat=2, valid=True, transport="direct_stdout"),
        attempt(precondition="observed", form_id="file_normal", repeat=1, valid=False),
        attempt(precondition="observed", form_id="file_normal", repeat=2, valid=False),
    ]
    result = classify_root_cause(
        attempts=attempts,
        qualified_paths=qualify_paths(attempts, 2),
        baseline_interactive=True,
        wake_interactive=True,
    )
    assert result["root_cause"] == "REMOTE_PATH_OR_FILE_CREATION_FAILURE"


def test_root_cause_parser_and_tool_failure() -> None:
    parser_attempt = attempt(
        precondition="observed", form_id="file_normal", repeat=1, valid=False, envelope_found=True
    )
    assert classify_root_cause(
        attempts=[parser_attempt],
        qualified_paths=[],
        baseline_interactive=True,
        wake_interactive=True,
    )["root_cause"] == "PARSER_OR_CAPTURE_BUG"
    tool_attempt = attempt(
        precondition="wake_dismiss_verified",
        form_id="file_normal",
        repeat=1,
        valid=False,
        envelope_found=False,
    )
    assert classify_root_cause(
        attempts=[tool_attempt],
        qualified_paths=[],
        baseline_interactive=True,
        wake_interactive=True,
    )["root_cause"] == "UIAUTOMATOR_TOOL_FAILURE"


def test_config_matrix_schema_and_boundaries() -> None:
    config = json.loads(
        (ROOT / "configs/role_binding_timing/phase_b2_7_ui_tree_export_diagnosis.json").read_text(
            encoding="utf-8"
        )
    )
    schema = json.loads(
        (ROOT / "schemas/role_binding_timing_ui_tree_export_diagnosis.v0_2_7.schema.json").read_text(
            encoding="utf-8"
        )
    )
    assert config["generation_calls_authorized"] == 0
    assert config["generation_eligible"] is False
    assert config["held_out_eligible"] is False
    assert config["runtime"]["adb_server_port"] == 5038
    assert config["runtime"]["fallback_to_5037"] is False
    assert len(config["matrix"]["preconditions"]) * len(config["matrix"]["forms"]) * config["matrix"]["repeats"] == 16
    assert {form["transport"] for form in config["matrix"]["forms"]} == {
        "remote_file",
        "direct_stdout",
    }
    assert {form["compressed"] for form in config["matrix"]["forms"]} == {False, True}
    Draft202012Validator.check_schema(schema)


def test_runner_has_explicit_port_and_preserves_raw_streams() -> None:
    source = (ROOT / "scripts/diagnose_role_binding_timing_b2_7_ui_tree.py").read_text(encoding="utf-8")
    assert '"-P"' in source
    assert '"{name}.stdout.bin"' in source
    assert '"{name}.stderr.bin"' in source
    assert '"-P", "5037"' not in source
    assert '"fallback_to_5037": False' in source
    assert "generation_calls\": 0" in source
