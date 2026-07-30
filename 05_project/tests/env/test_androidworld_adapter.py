from __future__ import annotations

import pytest
from android_env.proto import adb_pb2

from raven_m.env.androidworld_adapter import AndroidWorldAdapter


def test_tap_maps_normalized_coordinates_to_pixels() -> None:
    mapped = AndroidWorldAdapter().map_action(
        {"type": "tap", "x": 0.5, "y": 1.0},
        screen_width=1080,
        screen_height=2400,
    )
    assert mapped.actual_pixels == {"x": 540, "y": 2399}
    assert mapped.upstream_action == {
        "action_type": "click",
        "x": 540,
        "y": 2399,
    }


def test_swipe_preserves_both_coordinate_systems() -> None:
    canonical = {
        "type": "swipe",
        "x": 0.5,
        "y": 0.8,
        "x2": 0.5,
        "y2": 0.2,
        "duration_ms": 500,
    }
    mapped = AndroidWorldAdapter().map_action(
        canonical,
        screen_width=1080,
        screen_height=2400,
    )
    assert mapped.canonical == canonical
    assert mapped.actual_pixels == {
        "x": 540,
        "y": 1919,
        "x2": 540,
        "y2": 480,
    }
    assert mapped.upstream_action is None


def test_adapter_rejects_out_of_bounds_even_without_schema() -> None:
    with pytest.raises(ValueError):
        AndroidWorldAdapter().map_action(
            {"type": "tap", "x": -0.01, "y": 0.5},
            screen_width=1080,
            screen_height=2400,
        )


def test_answer_maps_to_androidworld_terminal_channel() -> None:
    mapped = AndroidWorldAdapter().map_action(
        {
            "type": "answer",
            "text": "Running, Cycling",
            "text_origin": "current_screen",
            "source_memory_ids": [],
        },
        screen_width=1080,
        screen_height=2400,
    )
    assert mapped.upstream_action == {
        "action_type": "answer",
        "text": "Running, Cycling",
    }
    assert mapped.actual_pixels == {}


@pytest.mark.parametrize(
    "canonical",
    [
        {"type": "tap", "x": 0.5, "y": 0.5},
        {
            "type": "long_press",
            "x": 0.5,
            "y": 0.5,
            "duration_ms": 300,
        },
        {
            "type": "swipe",
            "x": 0.5,
            "y": 0.8,
            "x2": 0.5,
            "y2": 0.2,
            "duration_ms": 100,
        },
        {
            "type": "type_text",
            "text": "value",
            "text_origin": "task_literal",
            "source_memory_ids": [],
        },
        {"type": "press_back"},
        {"type": "press_home"},
        {"type": "press_enter"},
        {"type": "open_app", "app_name": "Contacts"},
        {
            "type": "answer",
            "text": "value",
            "text_origin": "current_screen",
            "source_memory_ids": [],
        },
        {"type": "wait", "duration_ms": 250},
    ],
)
def test_every_canonical_action_has_an_execution_path(
    canonical: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Env:
        controller = object()
        interaction_cache = ""

        def __init__(self) -> None:
            self.actions = []

        def execute_action(self, action) -> None:
            self.actions.append(action)

    issued = []
    monkeypatch.setattr(
        "android_world.env.adb_utils.issue_generic_request",
        lambda command, controller: issued.append((command, controller)),
    )
    monkeypatch.setattr(
        "raven_m.env.androidworld_adapter.time.sleep",
        lambda seconds: issued.append(("sleep", seconds)),
    )
    adapter = AndroidWorldAdapter()
    mapped = adapter.map_action(
        canonical,
        screen_width=1080,
        screen_height=2400,
    )
    env = Env()
    adapter.execute(env, mapped)
    if canonical["type"] == "answer":
        assert env.interaction_cache == canonical["text"]
    elif canonical["type"] in {"swipe", "long_press", "wait"}:
        assert issued
    else:
        assert len(env.actions) == 1


def test_clear_text_uses_one_retry_idempotent_compound_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Env:
        controller = object()

        def __init__(self) -> None:
            self.actions = []

        def execute_action(self, action) -> None:
            self.actions.append(action)

    issued = []
    entered = []

    def issue(command, controller, timeout_sec):
        issued.append((command, controller, timeout_sec))
        return adb_pb2.AdbResponse(status=adb_pb2.AdbResponse.Status.OK)

    monkeypatch.setattr(
        "android_world.env.adb_utils.issue_generic_request",
        issue,
    )
    monkeypatch.setattr(
        "android_world.env.adb_utils.press_enter_button",
        lambda controller: entered.append(controller),
    )
    monkeypatch.setattr(
        "raven_m.env.androidworld_adapter.time.sleep",
        lambda seconds: issued.append(("focus_sleep", seconds)),
    )

    adapter = AndroidWorldAdapter()
    mapped = adapter.map_action(
        {
            "type": "type_text",
            "text": "Remember to transfer funds",
            "clear_text": True,
            "text_origin": "task_literal",
            "source_memory_ids": [],
            "x": 0.25,
            "y": 0.5,
        },
        screen_width=1080,
        screen_height=2400,
    )
    env = Env()
    adapter.execute(env, mapped)

    assert len(env.actions) == 1
    assert env.actions[0].as_dict() == {
        "action_type": "click",
        "x": 270,
        "y": 1200,
    }
    assert issued[0] == ("focus_sleep", 1.0)
    assert issued[1] == (
        [
            "shell",
            "input",
            "keycombination",
            "113",
            "29",
            "&&",
            "input",
            "keyevent",
            "67",
            "&&",
            "sleep",
            "1",
            "&&",
            "input",
            "text",
            "Remember",
            "&&",
            "input",
            "text",
            "%s",
            "&&",
            "input",
            "text",
            "to",
            "&&",
            "input",
            "text",
            "%s",
            "&&",
            "input",
            "text",
            "transfer",
            "&&",
            "input",
            "text",
            "%s",
            "&&",
            "input",
            "text",
            "funds",
        ],
        env.controller,
        10.0,
    )
    assert entered == [env.controller]


def test_clear_text_without_coordinates_bypasses_upstream_input_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Env:
        controller = object()

        def execute_action(self, action) -> None:
            raise AssertionError(f"Unexpected upstream action: {action!r}")

    issued = []
    monkeypatch.setattr(
        "android_world.env.adb_utils.issue_generic_request",
        lambda command, controller, timeout_sec: (
            issued.append((command, controller, timeout_sec))
            or adb_pb2.AdbResponse(status=adb_pb2.AdbResponse.Status.OK)
        ),
    )
    monkeypatch.setattr(
        "android_world.env.adb_utils.press_enter_button",
        lambda controller: None,
    )

    adapter = AndroidWorldAdapter()
    mapped = adapter.map_action(
        {
            "type": "type_text",
            "text": "Educational",
            "clear_text": True,
            "text_origin": "task_literal",
            "source_memory_ids": [],
        },
        screen_width=1080,
        screen_height=2400,
    )
    adapter.execute(Env(), mapped)

    command = issued[0][0]
    assert command[:13] == [
        "shell",
        "input",
        "keycombination",
        "113",
        "29",
        "&&",
        "input",
        "keyevent",
        "67",
        "&&",
        "sleep",
        "1",
        "&&",
    ]
    assert command[13:] == ["input", "text", "Educational"]


def test_atomic_clear_text_supports_newlines() -> None:
    from android_world.env import adb_utils

    command = AndroidWorldAdapter._atomic_clear_and_type_command(
        "first\nsecond",
        adb_utils,
    )
    assert command[-11:] == [
        "input",
        "text",
        "first",
        "&&",
        "input",
        "keyevent",
        "66",
        "&&",
        "input",
        "text",
        "second",
    ]


def test_atomic_clear_text_timeout_scales_but_is_bounded() -> None:
    from android_world.env import adb_utils

    assert (
        AndroidWorldAdapter._atomic_clear_and_type_timeout(
            "Educational",
            adb_utils,
        )
        == 10.0
    )
    assert (
        AndroidWorldAdapter._atomic_clear_and_type_timeout(
            " ".join(["word"] * 100),
            adb_utils,
        )
        == 120.0
    )


def test_atomic_clear_text_failure_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Env:
        controller = object()

        def execute_action(self, action) -> None:
            raise AssertionError(f"Unexpected upstream action: {action!r}")

    monkeypatch.setattr(
        "android_world.env.adb_utils.issue_generic_request",
        lambda command, controller, timeout_sec: adb_pb2.AdbResponse(
            status=adb_pb2.AdbResponse.Status.TIMEOUT,
            error_message="Timeout",
        ),
    )
    monkeypatch.setattr(
        "android_world.env.adb_utils.press_enter_button",
        lambda controller: pytest.fail("ENTER must not follow failed input"),
    )

    mapped = AndroidWorldAdapter().map_action(
        {
            "type": "type_text",
            "text": "Educational",
            "clear_text": True,
            "text_origin": "task_literal",
            "source_memory_ids": [],
        },
        screen_width=1080,
        screen_height=2400,
    )
    with pytest.raises(RuntimeError, match="Atomic clear-and-type"):
        AndroidWorldAdapter().execute(Env(), mapped)
