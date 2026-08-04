from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from raven_m.role_binding_timing.infrastructure_v0_2_5 import (
    derive_dev_locator,
    direct_find_args,
    guarded_call,
    parse_direct_find_output,
    parse_foreground_witnesses,
    parse_ui_tree,
    resolve_locator,
    validate_foreground,
    validate_launch_result,
)


ROOT = Path(__file__).resolve().parents[2]


def xml(nodes: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<hierarchy rotation="0">' + nodes + "</hierarchy>"
    ).encode()


def node(**overrides: str) -> str:
    values = {
        "index": "0",
        "text": "",
        "resource-id": "",
        "class": "android.widget.TextView",
        "package": "com.example",
        "content-desc": "",
        "clickable": "true",
        "enabled": "true",
        "bounds": "[0,0][100,100]",
    }
    values.update(overrides)
    return "<node " + " ".join(f'{key}="{value}"' for key, value in values.items()) + "/>"


def test_foreground_accepts_top_resumed_and_current_focus() -> None:
    witnesses = parse_foreground_witnesses(
        "topResumedActivity=ActivityRecord{abc u0 com.example/.MainActivity t1}",
        "mCurrentFocus=Window{abc u0 com.example/com.example.MainActivity}",
    )
    assert witnesses["activity_packages"] == ["com.example"]
    assert witnesses["window_packages"] == ["com.example"]


def test_foreground_accepts_legacy_mresumed() -> None:
    witnesses = parse_foreground_witnesses(
        "mResumedActivity: ActivityRecord{abc u0 com.example/.Legacy t1}",
        "mFocusedApp=ActivityRecord{abc u0 com.example/.Legacy t1}",
    )
    assert witnesses["activity_components"] == ["com.example/.Legacy"]
    assert witnesses["window_components"] == ["com.example/.Legacy"]


def test_foreground_requires_three_concordant_witnesses() -> None:
    tree = parse_ui_tree(xml(node(package="com.example", text="Open")))
    witnesses = parse_foreground_witnesses(
        "topResumedActivity=ActivityRecord{a u0 com.other/.Main t1}",
        "mCurrentFocus=Window{a u0 com.example/.Main}",
    )
    assert "ACTIVITY_WITNESS_MISSING" in validate_foreground(
        expected_package="com.example", witnesses=witnesses, ui_tree=tree
    )
    assert "CONTRADICTORY_FOREGROUND_WITNESS" in validate_foreground(
        expected_package="com.example", witnesses=witnesses, ui_tree=tree
    )


def test_launch_contract_rejects_timeout_and_unparseable() -> None:
    assert validate_launch_result({"timed_out": True, "returncode": None, "stdout": ""}) == [
        "LAUNCH_TIMEOUT",
        "LAUNCH_NONZERO",
        "LAUNCH_RESULT_UNPARSEABLE",
    ]


def test_launch_contract_accepts_am_start_w() -> None:
    assert not validate_launch_result(
        {"timed_out": False, "returncode": 0, "stdout": "Starting: Intent {}\nStatus: ok\nThisTime: 10"}
    )


def test_locator_prefers_unique_resource_id() -> None:
    tree = parse_ui_tree(
        xml(
            node(**{"resource-id": "com.example:id/save", "content-desc": "Save", "text": "Save"})
            + node(index="1", text="Other", bounds="[0,100][100,200]")
        )
    )
    resolved = resolve_locator(
        tree,
        package="com.example",
        locator={"resource_id": "com.example:id/save", "content_desc": "Save", "text": "Save"},
    )
    assert resolved["strategy"] == "resource_id"


def test_locator_uses_content_description_then_text() -> None:
    tree = parse_ui_tree(xml(node(**{"content-desc": "  Save contact  ", "clickable": "true"})))
    resolved = resolve_locator(tree, package="com.example", locator={"content_desc": "save contact"})
    assert resolved["strategy"] == "content_desc"


def test_locator_uses_nearest_clickable_ancestor() -> None:
    raw = (
        '<?xml version="1.0"?><hierarchy rotation="0">'
        '<node index="0" text="" resource-id="com.example:id/action" class="android.view.View" '
        'package="com.example" content-desc="" clickable="true" enabled="true" bounds="[0,0][200,200]">'
        '<node index="0" text="Save" resource-id="" class="android.widget.TextView" package="com.example" '
        'content-desc="" clickable="false" enabled="true" bounds="[20,20][180,180]"/>'
        "</node></hierarchy>"
    ).encode()
    tree = parse_ui_tree(raw)
    resolved = resolve_locator(tree, package="com.example", locator={"text": "save"})
    assert resolved["resource_id"] == "com.example:id/action"


def test_locator_fails_closed_on_ambiguity() -> None:
    tree = parse_ui_tree(
        xml(node(text="Save") + node(index="1", text="Save", bounds="[0,100][100,200]"))
    )
    with pytest.raises(ValueError, match="LOCATOR_NOT_UNIQUE"):
        resolve_locator(tree, package="com.example", locator={"text": "Save"})


def test_dev_locator_is_deterministic() -> None:
    tree = parse_ui_tree(
        xml(
            node(**{"resource-id": "com.example:id/z"})
            + node(index="1", **{"resource-id": "com.example:id/a", "bounds": "[0,100][100,200]"})
        )
    )
    assert derive_dev_locator(tree, package="com.example") == {"resource_id": "com.example:id/a"}


def test_direct_find_never_uses_remote_shell_or_pipe() -> None:
    args = direct_find_args("/storage/emulated/0/Download")
    assert args == [
        "shell",
        "find",
        "/storage/emulated/0/Download",
        "-maxdepth",
        "1",
        "-type",
        "f",
        "-print",
    ]
    assert "sh" not in args and "|" not in args


def test_direct_find_rejects_escaped_or_proc_output() -> None:
    root = "/storage/emulated/0/Download"
    assert parse_direct_find_output(f"{root}/a.txt\n{root}/b.txt\n", root) == [
        f"{root}/a.txt",
        f"{root}/b.txt",
    ]
    with pytest.raises(ValueError, match="ESCAPED_ROOT"):
        parse_direct_find_output("./proc/1/exe\n", root)


def test_guarded_call_detects_pid_drift_before_and_after() -> None:
    with pytest.raises(RuntimeError, match="IDENTITY_BEFORE"):
        guarded_call(expected_pid=10, witness=lambda: 11, operation=lambda: {"ok": True})
    values = iter([10, 12])
    with pytest.raises(RuntimeError, match="IDENTITY_AFTER"):
        guarded_call(expected_pid=10, witness=lambda: next(values), operation=lambda: {"ok": True})


def test_dev_config_and_certificate_schema_boundaries() -> None:
    config = json.loads(
        (ROOT / "configs/role_binding_timing/phase_b2_5_infrastructure_dev.json").read_text(encoding="utf-8")
    )
    contract = json.loads(
        (ROOT / "contracts/role_binding_timing_collector_infrastructure.v0_2_5.json").read_text(encoding="utf-8")
    )
    schema = json.loads(
        (ROOT / "schemas/role_binding_timing_infrastructure_certificate.v0_2_5.schema.json").read_text(encoding="utf-8")
    )
    assert config["generation_calls_authorized"] == 0
    assert config["generation_eligible"] is False
    assert config["held_out_eligible"] is False
    assert config["pass_rules"]["required_sequences"] == 12
    assert len({app["package"] for app in config["apps"]}) == 4
    assert contract["adb"]["implicit_restart_allowed"] is False
    assert contract["adb"]["fallback_to_5037"] is False
    Draft202012Validator.check_schema(schema)
