from __future__ import annotations

import json
from dataclasses import replace

import numpy as np
import pytest

from raven_m.official_qwen_mobile.a10_obligation_branch_frontier import (
    A10IntegrityError,
    A10VisibleInputError,
    EvidenceCalibratedObligationBranchFrontierMemory,
    canonical_action_family,
    changed_pixel_fraction,
    classify_intent,
    classify_operation,
    describe_visual_state,
    extract_goal_anchors,
    target_anchor_mask,
    visual_distance,
    visual_match,
)


GOAL = "Delete the following expenses: Bike Repairs, Tuition Fees, Public Transit."


def screen(value: int = 0, *, height: int = 96, width: int = 64) -> np.ndarray:
    pixels = np.full((height, width, 3), value, dtype=np.uint8)
    pixels[20:70, 12:52, 1] = min(255, value + 40)
    return pixels


def observe(memory, step, before, after, summary="Tap the lower-middle delete control.", action=None):
    return memory.observe_step(
        source_step=step,
        action_summary=summary,
        canonical_action=action or {"type": "tap", "x": 0.5, "y": 0.6},
        before={"pixels": before, "evaluator_reward": 999, "ui_tree": "ignored"},
        after={"pixels": after, "task_success": True, "package": "ignored"},
        transition={"evaluator_derived": True},
        source_response_sha256="a" * 64,
        source_screenshot_sha256="b" * 64,
    )


def test_query_normalization_extraction_dedup_and_operation() -> None:
    anchors = extract_goal_anchors(
        'DELETE the following expenses: "Bike Repairs", Bike Repairs, Tuition Fees; Public Transit. on this week at 09:30'
    )
    normalized = [item.normalized for item in anchors]
    assert normalized.count("bike repairs") == 1
    assert "tuition fees" in normalized
    assert len(anchors) <= 8
    assert classify_operation("please delete two records") == "DELETE"
    assert classify_operation("calculate the total") == "QUERY_OR_CALCULATE"


def test_frozen_anchor_parser_uses_last_colon_backticks_and_no_underscore() -> None:
    anchors = extract_goal_anchors(
        "app: delete the following: `Bike_Repairs`, Public Transit"
    )
    normalized = [item.normalized for item in anchors]
    assert "bike repairs" in normalized
    assert "public transit" in normalized
    assert all(not item.startswith("delete the following") for item in normalized)


def test_anchor_parser_preserves_apostrophes_and_duration_suffixes() -> None:
    anchors = extract_goal_anchors(
        "Create at 8h with the title 'Workshop' and the description "
        "'We will plan. Let\'s be punctual.' for 60 mins."
    )
    literals = [item.literal for item in anchors]
    assert "We will plan. Let's be punctual." in literals
    assert "8h" in literals
    assert "60 mins" in literals


def test_reopen_requires_post_support_strong_negative() -> None:
    memory = EvidenceCalibratedObligationBranchFrontierMemory()
    memory._initialize_goal_once("Delete the following: Bike Repairs, Tuition Fees")
    anchor = memory.anchors[0]
    memory._add_anchor_event(anchor, "LATER_REOPEN_ATTEMPT", 0)
    assert anchor.contradiction_count == 0
    anchor.ever_supported = True
    anchor.status = "LOCALLY_SUPPORTED"
    anchor.contradiction_count = 0
    memory._add_anchor_event(anchor, "ROUTE_RETURN", 1)
    memory._refresh_anchors(1)
    assert anchor.status != "REOPENED"
    memory._add_anchor_event(anchor, "LATER_REOPEN_ATTEMPT", 2)
    memory._refresh_anchors(2)
    assert anchor.status == "REOPENED"


def test_visual_exact_near_layout_crop_and_narrow_width() -> None:
    base = screen()
    same = base.copy()
    near = base.copy()
    near[30:35, 20:25] += 1
    top_bar = base.copy()
    top_bar[:3] = 255
    layout = np.flip(base, axis=1).copy()
    d0, d1, dn, dt, dl = map(describe_visual_state, (base, same, near, top_bar, layout))
    assert d0.exact_sha256 == d1.exact_sha256
    assert visual_match(d0, dn)
    assert d0.exact_sha256 == dt.exact_sha256
    assert len(describe_visual_state(np.zeros((25, 8, 3), dtype=np.uint8)).luma_q) == 144
    assert visual_distance(d0, dl)[2] >= 0


@pytest.mark.parametrize(
    "pixels",
    [
        np.zeros((24, 20, 3), dtype=np.uint8),
        np.zeros((25, 7, 3), dtype=np.uint8),
        np.zeros((25, 8, 2), dtype=np.uint8),
        np.zeros((25, 8, 3), dtype=np.float32),
        np.full((25, 8, 3), -1, dtype=np.int16),
        np.full((25, 8, 3), 256, dtype=np.int16),
    ],
)
def test_rgb_validation_rejects_illegal_inputs(pixels: np.ndarray) -> None:
    with pytest.raises(A10VisibleInputError):
        describe_visual_state(pixels)


def test_rgba_and_non_contiguous_integer_inputs_are_legal() -> None:
    rgba = np.zeros((40, 20, 4), dtype=np.uint16)
    assert describe_visual_state(rgba).crop_shape[2] == 3
    non_contiguous = np.zeros((40, 20, 3), dtype=np.uint8)[:, ::2, :]
    assert not non_contiguous.flags.c_contiguous
    describe_visual_state(non_contiguous)


def test_action_families_intent_and_target_mask() -> None:
    assert canonical_action_family({"type": "tap", "x": .01, "y": .01})[:3] == ("tap", 0, 0)
    assert canonical_action_family({"type": "long_press", "x": .5, "y": .5, "duration_ms": 1500})[-1] == "medium"
    assert canonical_action_family({"type": "swipe", "x": .5, "y": .8, "x2": .5, "y2": .1})[1:3] == ("up", "long")
    typed = canonical_action_family({"type": "type_text", "text": "Bike Repairs", "clear_text": False})
    assert typed[0] == "type_text" and typed[2] == "9-32"
    assert classify_intent("I will open then delete", {"type": "tap"}) == "COMMIT"
    anchors = extract_goal_anchors(GOAL)
    assert target_anchor_mask("Delete Bike Repairs", {"type": "tap"}, anchors).bit_count() == 1


def test_changed_fraction_and_immediate_outcomes() -> None:
    base = screen()
    changed = base.copy()
    changed[40:60, 20:40] = 255
    assert changed_pixel_fraction(base, base.copy()) == 0
    assert changed_pixel_fraction(base, changed) > .001
    memory = EvidenceCalibratedObligationBranchFrontierMemory()
    memory.read({"goal": GOAL, "before": {"pixels": base}})
    result = observe(memory, 0, base, base)
    assert result["immediate_outcome"] == "NO_PROGRESS_EXACT"


def test_two_no_progress_attempts_trigger_t1_and_one_shot_read() -> None:
    pixels = screen()
    memory = EvidenceCalibratedObligationBranchFrontierMemory()
    assert memory.read({"goal": GOAL, "before": {"pixels": pixels}})[0] == ""
    assert observe(memory, 0, pixels, pixels)["trigger_ids_enqueued"] == []
    assert memory.read({"goal": GOAL, "before": {"pixels": pixels}})[0] == ""
    second = observe(memory, 1, pixels, pixels)
    assert second["trigger_ids_enqueued"]
    rendered, audit = memory.read({"goal": GOAL, "before": {"pixels": pixels}})
    assert audit["trigger_kind"] == "BAD_BRANCH_REPEAT"
    assert "Nothing is blocked or selected." in rendered
    assert len(rendered) <= 420 and len(rendered.encode()) <= 720
    assert memory.read({"goal": GOAL, "before": {"pixels": pixels}})[0] == ""


def test_route_return_is_resolved_only_after_observed_future_frame() -> None:
    source, destination = screen(), screen(110)
    memory = EvidenceCalibratedObligationBranchFrontierMemory()
    memory.read({"goal": GOAL, "before": {"pixels": source}})
    first = observe(memory, 0, source, destination, summary="Open another page")
    assert first["immediate_outcome"] == "DEPARTURE_PENDING"
    assert memory.audit_record()["routes"]["return_count"] == 0
    returned = observe(memory, 1, destination, source, summary="Return to prior page", action={"type": "press_back"})
    assert any(item["outcome"] == "RETURNED" for item in returned["route_resolutions"])


def test_t2_binds_original_returned_frontier_and_is_readable_there() -> None:
    source, destination = screen(), screen(110)
    memory = EvidenceCalibratedObligationBranchFrontierMemory()
    memory.read({"goal": GOAL, "before": {"pixels": source}})
    observe(memory, 0, source, destination, summary="Open another page")
    returned = observe(
        memory, 1, destination, source, summary="Return to prior page",
        action={"type": "press_back"},
    )
    assert any(item["outcome"] == "RETURNED" for item in returned["route_resolutions"])
    rendered, audit = memory.read({"goal": GOAL, "before": {"pixels": source}})
    assert rendered
    assert audit["trigger_kind"] == "CLOSED_ROUTE_WITHOUT_ADVANCE"


def test_route_return_with_changed_target_mask_is_normal_repeat() -> None:
    source, destination = screen(), screen(110)
    memory = EvidenceCalibratedObligationBranchFrontierMemory()
    memory.read({"goal": GOAL, "before": {"pixels": source}})
    observe(
        memory, 0, source, destination, summary="Select Bike Repairs",
        action={"type": "tap", "x": .2, "y": .2},
    )
    result = observe(
        memory, 1, destination, source, summary="Select Tuition Fees",
        action={"type": "tap", "x": .8, "y": .2},
    )
    assert any(item["outcome"] == "RETURNED" for item in result["route_resolutions"])
    assert not memory.audit_record()["triggers"]["created_counts_by_kind"].get(
        "CLOSED_ROUTE_WITHOUT_ADVANCE", 0
    )


def test_near_match_is_hard_eligible_for_non_t0_trigger() -> None:
    pixels = screen()
    near = pixels.copy()
    near[30:35, 20:25, 0] += 1
    memory = EvidenceCalibratedObligationBranchFrontierMemory()
    memory.read({"goal": GOAL, "before": {"pixels": pixels}})
    observe(memory, 0, pixels, pixels)
    memory.read({"goal": GOAL, "before": {"pixels": pixels}})
    observe(memory, 1, pixels, pixels)
    rendered, audit = memory.read({"goal": GOAL, "before": {"pixels": near}})
    assert rendered
    assert audit["trigger_kind"] == "BAD_BRANCH_REPEAT"


def test_t3_accepts_resolved_local_changes_without_extra_bad_gate() -> None:
    pixels = screen()
    changed = pixels.copy()
    changed[30:40, 20:30, 0] += 8
    assert visual_match(describe_visual_state(pixels), describe_visual_state(changed))
    memory = EvidenceCalibratedObligationBranchFrontierMemory()
    memory.read({"goal": GOAL, "before": {"pixels": pixels}})
    observe(memory, 0, pixels, changed, summary="Inspect row")
    result = observe(memory, 1, changed, pixels, summary="Inspect row")
    kinds = memory.audit_record()["triggers"]["created_counts_by_kind"]
    assert result["trigger_ids_enqueued"]
    assert kinds.get("FRONTIER_COLLAPSE") == 1


def test_t4_route_resolution_is_written_back_and_clear_requires_same_frontier() -> None:
    source, destination, other = screen(), screen(110), screen(210)
    action = {"type": "type_text", "text": "Bike_Repairs", "clear_text": False}
    memory = EvidenceCalibratedObligationBranchFrontierMemory()
    memory.read({"goal": GOAL, "before": {"pixels": source}})
    observe(memory, 0, source, destination, summary="Type Bike Repairs", action=action)
    observe(memory, 1, destination, source, summary="Return", action={"type": "press_back"})
    observe(memory, 2, source, source, summary="Type Bike Repairs", action=action)
    assert memory.audit_record()["triggers"]["created_counts_by_kind"].get(
        "VALUE_REENTRY_AFTER_BAD_OUTCOME"
    ) == 1

    cleared = EvidenceCalibratedObligationBranchFrontierMemory()
    cleared.read({"goal": GOAL, "before": {"pixels": source}})
    observe(cleared, 0, source, source, summary="Type Bike Repairs", action=action)
    observe(
        cleared, 1, source, other, summary="clear input",
        action={"type": "type_text", "text": "other", "clear_text": True},
    )
    observe(cleared, 2, other, other, summary="Type Bike Repairs", action=action)
    assert not cleared.audit_record()["triggers"]["created_counts_by_kind"].get(
        "VALUE_REENTRY_AFTER_BAD_OUTCOME", 0
    )


def test_durable_then_late_return_revision_does_not_use_future_early() -> None:
    source = screen()
    pages = [screen(v) for v in (50, 80, 110, 140, 170, 200)]
    memory = EvidenceCalibratedObligationBranchFrontierMemory()
    memory.read({"goal": "Open and inspect the report", "before": {"pixels": source}})
    observe(memory, 0, source, pages[0], summary="Open report")
    for step in range(1, 5):
        result = observe(memory, step, pages[step - 1], pages[step], summary="Inspect next page", action={"type": "swipe", "x": .5, "y": .8, "x2": .5, "y2": .2})
    assert any(item["outcome"] == "DURABLE_DEPARTURE" for item in result["route_resolutions"])
    result = observe(memory, 5, pages[4], source, summary="Return", action={"type": "press_back"})
    assert any(item["outcome"] == "LATE_RETURN" for item in result["route_resolutions"])
    audit = memory.audit_record()
    assert audit["routes"]["late_return_count"] == 1
    original = next(item for item in audit["attempts"]["receipts"] if item["source_step"] == 0)
    assert original["resolved_outcome"] == "LATE_RETURN"


def test_late_return_removes_matching_anchor_durable_evidence() -> None:
    source = screen()
    pages = [screen(v) for v in (50, 80, 110, 140, 170)]
    goal = 'Delete "Bike Repairs" and "Public Transit".'
    memory = EvidenceCalibratedObligationBranchFrontierMemory()
    memory.read({"goal": goal, "before": {"pixels": source}})
    observe(memory, 0, source, pages[0], summary="Delete Bike Repairs")
    for step in range(1, 5):
        observe(
            memory, step, pages[step - 1], pages[step], summary="Inspect next page",
            action={"type": "swipe", "x": .5, "y": .8, "x2": .5, "y2": .2},
        )
    assert any(
        event["event_kind"] == "DURABLE_ROUTE_DEPARTURE"
        for anchor in memory.audit_record()["goal"]["anchors"]
        for event in anchor["evidence_events"]
    )
    observe(memory, 5, pages[4], source, summary="Return", action={"type": "press_back"})
    assert not any(
        event["event_kind"] == "DURABLE_ROUTE_DEPARTURE"
        for anchor in memory.audit_record()["goal"]["anchors"]
        for event in anchor["evidence_events"]
    )


def test_hidden_metadata_does_not_change_decision_state() -> None:
    pixels = screen()
    left = EvidenceCalibratedObligationBranchFrontierMemory()
    right = EvidenceCalibratedObligationBranchFrontierMemory()
    assert left.read({"goal": GOAL, "before": {"pixels": pixels, "evaluator_reward": 1}}) == right.read({"goal": GOAL, "before": {"pixels": pixels, "evaluator_reward": 0, "ui_tree": {"secret": 1}}})
    for step in range(2):
        common = dict(source_step=step, action_summary="Tap the delete control", canonical_action={"type": "tap", "x": .4, "y": .5}, source_response_sha256="c" * 64)
        a = left.observe_step(**common, before={"pixels": pixels, "task_success": True}, after={"pixels": pixels, "database_state": "done"}, transition={"reward": 1})
        b = right.observe_step(**common, before={"pixels": pixels, "task_success": False, "ui_tree": "x"}, after={"pixels": pixels, "database_state": "not done"}, transition={"reward": 0})
        assert a == b
    assert left.audit_record() == right.audit_record()


def test_descriptor_memoization_is_audit_invariant() -> None:
    pixels, other = screen(), screen(120)
    cached = EvidenceCalibratedObligationBranchFrontierMemory()
    uncached = EvidenceCalibratedObligationBranchFrontierMemory()
    for memory in (cached, uncached):
        memory.read({"goal": GOAL, "before": {"pixels": pixels}})
    for step, (before, after) in enumerate(((pixels, other), (other, pixels), (pixels, pixels))):
        observe(cached, step, before, after, summary="Inspect route")
        cached.read({"goal": GOAL, "before": {"pixels": after}})
        uncached._descriptor_cache.clear()
        observe(uncached, step, before.copy(), after.copy(), summary="Inspect route")
        uncached._descriptor_cache.clear()
        uncached.read({"goal": GOAL, "before": {"pixels": after.copy()}})
    assert cached.audit_record() == uncached.audit_record()


def test_monotonic_integrity_and_goal_binding() -> None:
    pixels = screen()
    memory = EvidenceCalibratedObligationBranchFrontierMemory()
    memory.read({"goal": GOAL, "before": {"pixels": pixels}})
    with pytest.raises(A10IntegrityError):
        observe(memory, 1, pixels, pixels)
    with pytest.raises(A10IntegrityError):
        memory.read({"goal": "different goal", "before": {"pixels": pixels}})


def test_declared_capacities_and_audit_bound() -> None:
    memory = EvidenceCalibratedObligationBranchFrontierMemory()
    pixels = screen()
    memory.read({"goal": GOAL, "before": {"pixels": pixels}})
    for step in range(40):
        before = np.roll(pixels, step % 20, axis=1)
        after = before.copy()
        action = {"type": "tap", "x": (step % 12) / 12 + .001, "y": (step % 23) / 24 + .001}
        observe(memory, step, before, after, action=action)
        memory.read({"goal": GOAL, "before": {"pixels": after}})
    audit = memory.audit_record()
    assert audit["frontiers"]["current_count"] <= 16
    assert all(len(item["branches"]) <= 5 for item in audit["frontiers"]["records"])
    assert audit["attempts"]["retained_count"] <= 32
    assert audit["triggers"]["candidate_count"] <= 8
    assert audit["reads"]["nonempty_read_count"] <= 5
    assert len(json.dumps(audit, ensure_ascii=True).encode()) <= 131072
    assert audit["model_calls_added"] == 0
    assert audit["guard_enabled"] is False
    assert audit["action_override_count"] == 0


def test_true_max_frontier_branch_exemplar_state_stays_below_128_kib() -> None:
    rng = np.random.default_rng(20260812)
    screens = [
        rng.integers(0, 256, (96, 64, 3), dtype=np.uint8)
        for _ in range(16)
    ]
    goal = "Delete " + ", ".join(f'"Item {index}"' for index in range(8))
    memory = EvidenceCalibratedObligationBranchFrontierMemory()
    memory.read({"goal": goal, "before": {"pixels": screens[0]}})
    step = 0
    for pixels in screens:
        for branch_index in range(5):
            observe(
                memory,
                step,
                pixels,
                pixels,
                summary="tap",
                action={
                    "type": "tap",
                    "x": (branch_index + .1) / 12,
                    "y": (branch_index * 4 + .1) / 24,
                },
            )
            step += 1
    # Materialize the legal three-exemplar boundary for every frontier.  The
    # hashes differ while the descriptor payload remains maximally populated.
    for frontier in memory.frontiers.values():
        exemplar = frontier.visual_exemplars[0]
        frontier.visual_exemplars = [
            exemplar,
            replace(exemplar, exact_sha256="1" * 64),
            replace(exemplar, exact_sha256="2" * 64),
        ]
    audit = memory.audit_record()
    assert audit["frontiers"]["current_count"] == 16
    assert sum(len(item["branches"]) for item in audit["frontiers"]["records"]) == 80
    assert all(len(item["visual_exemplars"]) == 3 for item in audit["frontiers"]["records"])
    actual_bytes = len(json.dumps(audit, ensure_ascii=True).encode("utf-8"))
    assert actual_bytes == audit["capacity"]["serialized_audit_bytes"]
    assert actual_bytes <= 131072


def test_phase_read_cap_is_global_across_frontiers() -> None:
    pixels = screen()
    memory = EvidenceCalibratedObligationBranchFrontierMemory()
    memory.read({"goal": GOAL, "before": {"pixels": pixels}})
    for step in range(2):
        observe(memory, step, pixels, pixels)
        memory.read({"goal": GOAL, "before": {"pixels": pixels}})
    # Inject a distinct, eligible candidate through another pair of bad attempts.
    for step in range(2, 8):
        action = {"type": "tap", "x": .1 + (step % 2) * .7, "y": .2}
        observe(memory, step, pixels, pixels, action=action)
        memory.read({"goal": GOAL, "before": {"pixels": pixels}})
    assert memory.audit_record()["reads"]["nonempty_read_count"] <= 2


def test_post_read_behavior_is_filled_from_observed_actions_only() -> None:
    pixels, other = screen(), screen(150)
    memory = EvidenceCalibratedObligationBranchFrontierMemory()
    memory.read({"goal": GOAL, "before": {"pixels": pixels}})
    observe(memory, 0, pixels, pixels)
    memory.read({"goal": GOAL, "before": {"pixels": pixels}})
    observe(memory, 1, pixels, pixels)
    rendered, _ = memory.read({"goal": GOAL, "before": {"pixels": pixels}})
    assert rendered
    observe(memory, 2, pixels, other, action={"type": "tap", "x": .1, "y": .1})
    event = memory.audit_record()["reads"]["read_events"][-1]
    assert event["next_action_branch_id"]
    assert event["next_action_was_novel"] is True
    assert event["escaped_frontier_within_3"] is True
