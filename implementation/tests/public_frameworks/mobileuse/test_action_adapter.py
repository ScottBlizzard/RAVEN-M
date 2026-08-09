import pytest

from raven_m.public_frameworks.mobileuse.action_adapter import MobileUseActionAdapter


def test_coordinate_boundaries_and_mapping():
    adapter = MobileUseActionAdapter()
    mapped = adapter.map({"name": "click", "parameters": {"coordinate": [0, 999]}})
    assert mapped.canonical == {"type": "tap", "x": 0.0, "y": 1.0}
    swipe = adapter.map({
        "name": "swipe",
        "parameters": {"coordinate": [999, 0], "coordinate2": [0, 999]},
    })
    assert swipe.canonical["x"] == 1.0
    assert swipe.canonical["y2"] == 1.0


@pytest.mark.parametrize(
    "name",
    ["open", "open_app", "launch_app", "stop_app", "open_link", "key", "clear_text", "take_note", "long_press", "wait", "shell", "adb"],
)
def test_prohibited_actions_fail_closed(name):
    with pytest.raises(ValueError):
        MobileUseActionAdapter().map({"name": name, "parameters": {}})


def test_text_unicode_buttons_answer_and_terminal():
    adapter = MobileUseActionAdapter()
    assert adapter.map({"name": "type", "parameters": {"text": "浙江大学 你好"}}).canonical["text"] == "浙江大学 你好"
    assert adapter.map({"name": "system_button", "parameters": {"button": "Back"}}).canonical["type"] == "press_back"
    assert adapter.map({"name": "system_button", "parameters": {"button": "Home"}}).canonical["type"] == "press_home"
    assert adapter.map({"name": "answer", "parameters": {"text": "42"}}).canonical == {"type": "answer", "text": "42"}
    assert adapter.map({"name": "terminate", "parameters": {"status": "success"}}).terminal_status == "success"


def test_multiple_actions_rejected():
    content = '<tool_call>{"name":"mobile_use"}</tool_call><tool_call>{"name":"mobile_use"}</tool_call>'
    with pytest.raises(ValueError, match="Multiple"):
        MobileUseActionAdapter.assert_single_action_output(content)


def test_extra_parameters_and_out_of_range_rejected():
    adapter = MobileUseActionAdapter()
    with pytest.raises(ValueError):
        adapter.map({"name": "click", "parameters": {"coordinate": [1000, 2]}})
    with pytest.raises(ValueError):
        adapter.map({"name": "type", "parameters": {"text": "x", "clear_text": True}})
    with pytest.raises(ValueError):
        adapter.map({"name": "system_button", "parameters": {"button": "Enter"}})
