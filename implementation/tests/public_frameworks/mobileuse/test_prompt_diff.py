from types import SimpleNamespace

from raven_m.public_frameworks.mobileuse.prompt_adapter import adapt_prompts


def prompt(system="screen {resized_width}x{resized_height}"):
    return SimpleNamespace(
        system_prompt=system,
        init_tips="- safe\n- use `open` action\n- use long press\n- use `clear_text`",
        observation_prompt="screen {resized_width} {image_placeholder}",
        a11y_tree_prompt="accessibility {a11y_tree}",
    )


def test_every_prompt_change_has_an_authorized_label():
    operator = prompt()
    answer = prompt("The screen's resolution is {resized_width}x{resized_height}. You may call one or more functions to assist with the user query.")
    changes = adapt_prompts(operator, answer)
    allowed = {"ACTION_NAME", "ACTION_SCHEMA", "COORDINATE_RANGE", "UNSUPPORTED_TOOL_REMOVAL", "ENDPOINT_IDENTIFIER"}
    assert changes
    assert all(change.labels and set(change.labels) <= allowed for change in changes)
    active = operator.system_prompt + operator.init_tips
    for prohibited in ("clear_text", "long_press", '"open"', "take_note", '"key"', '"wait"'):
        assert prohibited not in active
    assert "[0,999]" in active
