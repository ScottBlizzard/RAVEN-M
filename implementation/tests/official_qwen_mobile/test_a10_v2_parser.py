from __future__ import annotations

from raven_m.official_qwen_mobile.a10_v2_obligation_branch_frontier import parse_goal, target_masks


def test_recipe_constraint_is_exact_two_anchor_bundle() -> None:
    anchors, groups, _ = parse_goal("Delete the recipes from Broccoli app that use zucchini in the directions.")
    assert [(a.normalized, a.role) for a in anchors] == [("zucchini", "HEAD"), ("directions", "QUALIFIER")]
    assert len(groups) == 1
    assert groups[0].render_label == "zucchini in directions"
    assert groups[0].persistent_open and groups[0].kind == "FILTER_SET"


def test_parser_metamorphism_and_app_exclusion() -> None:
    anchors, groups, _ = parse_goal("Delete the records from Cedar app that use quince in the notes.")
    assert [a.normalized for a in anchors] == ["quince", "notes"]
    assert groups[0].render_label == "quince in notes"


def test_exclude_constraint_keeps_polarity_in_render_label() -> None:
    _, groups, _ = parse_goal("Delete items without nuts in the ingredients.")
    assert groups[0].polarity == "EXCLUDE"
    assert groups[0].render_label == "exclude nuts in ingredients"


def test_qualifier_only_does_not_set_group_bit() -> None:
    anchors, groups, _ = parse_goal("Delete records that use quince in the notes.")
    anchor_mask, group_mask = target_masks("inspect the notes", {"type": "tap"}, anchors, groups)
    assert anchor_mask != 0
    assert group_mask == 0
    _, group_mask = target_masks("inspect notes for quince", {"type": "tap"}, anchors, groups)
    assert group_mask == 1
