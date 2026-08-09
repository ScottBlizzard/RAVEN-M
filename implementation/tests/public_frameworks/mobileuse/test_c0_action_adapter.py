import pytest

from raven_m.public_frameworks.mobileuse.c0_action_adapter import C0NativeActionAdapter


@pytest.fixture()
def adapter():
    return C0NativeActionAdapter()


def action(name, **parameters):
    return {"name": name, "parameters": parameters}


def test_native_coordinates_are_scaled_from_real_screenshot(adapter):
    mapped = adapter.map(action("click", coordinate=[199, 99]), screen_width=200, screen_height=100)
    assert mapped.canonical == {"type": "tap", "x": 1.0, "y": 1.0}


@pytest.mark.parametrize(
    ("value", "expected_type"),
    [
        (action("long_press", coordinate=[50, 25], time=1.2), "long_press"),
        (action("swipe", coordinate=[0, 0], coordinate2=[50, 25]), "swipe"),
        (action("clear_text"), "type_text"),
        (action("wait", time=2), "wait"),
        (action("system_button", button="Enter"), "press_enter"),
    ],
)
def test_released_actions_map(adapter, value, expected_type):
    assert adapter.map(value, screen_width=100, screen_height=50).canonical["type"] == expected_type


def test_open_and_key_are_explicit_bridge_actions(adapter):
    assert adapter.map(action("open", text="net.gsantner.markor"), screen_width=100, screen_height=50).bridge_action == {
        "type": "open_package", "package": "net.gsantner.markor"
    }
    assert adapter.map(action("key", text="volume_up"), screen_width=100, screen_height=50).bridge_action == {
        "type": "key", "text": "volume_up"
    }


def test_output_guard_accepts_exactly_one_call(adapter):
    adapter.assert_single_action_output(
        '<answer>[{"name":"mobile_use","arguments":{"action":"wait","time":1}}]</answer>'
    )
    with pytest.raises(ValueError):
        adapter.assert_single_action_output('<answer>[]</answer>')


def test_bad_coordinate_and_shell_like_key_fail_closed(adapter):
    with pytest.raises(ValueError):
        adapter.map(action("click", coordinate=[100, 1]), screen_width=100, screen_height=50)
    with pytest.raises(ValueError):
        adapter.map(action("key", text="HOME;rm"), screen_width=100, screen_height=50)
