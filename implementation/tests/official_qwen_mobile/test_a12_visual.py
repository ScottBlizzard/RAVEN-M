from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from raven_m.official_qwen_mobile.a12_minimal_action_divergence import (
    A12VisibleInputError,
    changed_pixel_fraction,
    compare_screens,
    describe_visual_state,
    extract_visible_rgb_only,
)


def rgb(height: int = 25, width: int = 40, value: int = 0) -> np.ndarray:
    return np.full((height, width, 3), value, dtype=np.uint8)


def test_exact_and_status_bar_crop() -> None:
    base = rgb()
    changed = base.copy(); changed[0] = 255; changed[-1] = 255
    assert describe_visual_state(base).exact_sha256 == describe_visual_state(changed).exact_sha256


def test_near_and_frozen_distance_boundaries() -> None:
    descriptor = describe_visual_state(rgb())
    zero = replace(descriptor, exact_sha256="y", luma_q=tuple([0] * 144))
    dl_boundary = replace(descriptor, exact_sha256="x", luma_q=tuple([1] * 129 + [0] * 15))
    assert compare_screens(dl_boundary, zero)[0] == "NEAR"  # largest representable DL <= .06
    dl_over = replace(dl_boundary, luma_q=tuple([1] * 130 + [0] * 14))
    assert compare_screens(dl_over, zero)[0] == "NONE"

    def edges(count: int) -> str:
        bits = np.zeros(264, dtype=np.uint8); bits[:count] = 1
        return np.packbits(bits, bitorder="big").tobytes().hex()

    de_boundary = replace(zero, exact_sha256="de", edge_bits_hex=edges(31))
    de_over = replace(zero, exact_sha256="deo", edge_bits_hex=edges(32))
    assert compare_screens(de_boundary, zero)[0] == "NEAR"
    assert compare_screens(de_over, zero)[0] == "NONE"
    dv_under = replace(zero, exact_sha256="dvu", luma_q=tuple([1] * 100 + [0] * 44), edge_bits_hex=edges(19))
    dv_over = replace(zero, exact_sha256="dvo", luma_q=tuple([1] * 100 + [0] * 44), edge_bits_hex=edges(20))
    assert compare_screens(dv_under, zero)[0] == "NEAR"
    assert compare_screens(dv_over, zero)[0] == "NONE"


def test_changed_fraction_inclusive_threshold_and_shape_change() -> None:
    before = rgb()
    exact_boundary = before.copy(); exact_boundary[0, 0, 0] = 6
    over = exact_boundary.copy(); over[0, 1, 0] = 6
    assert changed_pixel_fraction(before, exact_boundary) == 0.001
    assert changed_pixel_fraction(before, over) > 0.001
    assert changed_pixel_fraction(before, rgb(width=41)) == 1.0


def test_rgba_and_noncontiguous_are_legal() -> None:
    rgba = np.zeros((25, 8, 4), dtype=np.uint8); rgba[:, :, 3] = 255
    assert extract_visible_rgb_only({"pixels": rgba}).shape == (25, 8, 3)
    wide = np.zeros((25, 16, 3), dtype=np.uint8)
    noncontiguous = wide[:, ::2, :]
    assert not noncontiguous.flags.c_contiguous
    assert describe_visual_state(noncontiguous).crop_shape[1] == 8


def test_same_mean_different_layout_is_rejected_by_edges() -> None:
    left = rgb(width=48)
    right = left.copy()
    # Equal quantities of dark/light pixels but opposite spatial layouts.
    left[:, :24] = 255
    right[:, 24:] = 255
    assert compare_screens(describe_visual_state(left), describe_visual_state(right))[0] == "NONE"


@pytest.mark.parametrize(
    "pixels",
    [
        np.zeros((25, 8, 3), dtype=np.float32),
        np.full((25, 8, 3), np.nan, dtype=np.float32),
        np.full((25, 8, 3), -1, dtype=np.int16),
        np.full((25, 8, 3), 256, dtype=np.int16),
        np.zeros((24, 8, 3), dtype=np.uint8),
        np.zeros((25, 7, 3), dtype=np.uint8),
        np.zeros((25, 8, 2), dtype=np.uint8),
    ],
)
def test_invalid_rgb_is_rejected(pixels: np.ndarray) -> None:
    with pytest.raises(A12VisibleInputError):
        describe_visual_state(pixels)
