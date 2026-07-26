from __future__ import annotations

import pytest

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
