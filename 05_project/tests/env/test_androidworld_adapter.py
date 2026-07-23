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
