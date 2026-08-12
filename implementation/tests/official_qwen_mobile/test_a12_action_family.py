from __future__ import annotations

import math
import pytest

from raven_m.official_qwen_mobile.a12_minimal_action_divergence import (
    A12IntegrityError,
    canonical_action_family,
    render_action_label,
)


def test_tap_grid_jitter_and_boundary() -> None:
    assert canonical_action_family({"type": "tap", "x": 0, "y": 0}) == ("tap", 0, 0)
    assert canonical_action_family({"type": "tap", "x": .999, "y": .999}) == ("tap", 11, 23)
    assert canonical_action_family({"type": "tap", "x": .01, "y": .01}) == canonical_action_family({"type": "tap", "x": .02, "y": .02})
    assert canonical_action_family({"type": "tap", "x": 1 / 12, "y": 0}) != ("tap", 0, 0)


def test_long_press_duration_buckets() -> None:
    families = [canonical_action_family({"type": "long_press", "x": .5, "y": .5, "duration_ms": value}) for value in (699, 700, 1500, 1501)]
    assert [item[-1] for item in families] == ["short", "medium", "medium", "long"]


def test_swipe_direction_length_and_start_grid() -> None:
    assert canonical_action_family({"type": "swipe", "x": .1, "y": .1, "x2": .3, "y2": .1}) == ("swipe", "right", "short", 0, 0)
    assert canonical_action_family({"type": "swipe", "x": .4, "y": .4, "x2": .4, "y2": .9}) == ("swipe", "down", "medium", 1, 1)
    assert canonical_action_family({"type": "swipe", "x": .9, "y": .9, "x2": 0, "y2": .9}) == ("swipe", "left", "long", 2, 3)


def test_text_nfkc_hash_text_and_clear_are_identity() -> None:
    composed = canonical_action_family({"type": "type_text", "text": "é", "clear_text": False})
    decomposed = canonical_action_family({"type": "type_text", "text": "e\u0301", "clear_text": False})
    assert composed == decomposed
    assert composed != canonical_action_family({"type": "type_text", "text": "E", "clear_text": False})
    assert composed != canonical_action_family({"type": "type_text", "text": "é", "clear_text": True})


def test_wait_system_answer_and_labels() -> None:
    assert canonical_action_family({"type": "wait", "duration_ms": 700}) == ("wait", "medium")
    for kind in ("press_back", "press_home", "press_enter", "press_recents"):
        family = canonical_action_family({"type": kind})
        assert family == (kind,) and len(render_action_label(family)) <= 48
    answer = canonical_action_family({"type": "answer", "text": "yes"})
    assert answer[0] == "answer" and render_action_label(answer) == "submit the same answer"


@pytest.mark.parametrize(
    "action",
    [
        {"type": "unknown"},
        {"type": "tap", "x": math.nan, "y": .5},
        {"type": "tap", "x": -0.1, "y": .5},
        {"type": "tap", "x": 1.1, "y": .5},
    ],
)
def test_invalid_actions_are_rejected(action: dict) -> None:
    with pytest.raises(A12IntegrityError):
        canonical_action_family(action)
