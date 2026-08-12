from __future__ import annotations

import json
from copy import deepcopy

import numpy as np
import pytest

from raven_m.official_qwen_mobile.a11_confirmed_route_contraction import (
    A11IntegrityError,
    A11VisibleInputError,
    ConfirmedRouteContractionECOBFMemory,
    extract_goal_anchors,
    target_anchor_mask,
)


def screen(kind: int) -> np.ndarray:
    image = np.zeros((90, 160, 3), dtype=np.uint8)
    if kind == 0:
        image[12:36, 12:75] = (240, 30, 30)
    elif kind == 1:
        image[45:82, 84:150] = (20, 240, 20)
    elif kind == 2:
        image[10:80, 70:92] = (20, 20, 245)
    elif kind == 3:
        image[35:56, 8:152] = (220, 220, 20)
    else:
        image[8 + kind:30 + kind, 20:140] = (25 * kind % 255, 130, 230)
    return image


def tap(x: float = .5, y: float = .5) -> dict[str, object]:
    return {"type": "tap", "x": x, "y": y}


def act(memory: ConfirmedRouteContractionECOBFMemory, step: int, goal: str, before: np.ndarray, after: np.ndarray, action: dict[str, object], summary: str) -> dict[str, object]:
    memory.read({"goal": goal, "before": {"pixels": before}})
    return memory.observe_step(source_step=step, before={"pixels": before}, after={"pixels": after}, canonical_action=action, action_summary=summary, source_response_sha256=f"{step:064x}")


def test_recipe_constraint_parser_exact_and_app_exclusion() -> None:
    goal = "Delete the recipes from Broccoli app that use zucchini in the directions."
    anchors = extract_goal_anchors(goal)
    constraints = [item for item in anchors if item.role == "CONSTRAINT"]
    assert len(constraints) == 1
    constraint = constraints[0]
    assert (constraint.predicate, constraint.constraint_value, constraint.constraint_scope) == ("USE", "zucchini", "DIRECTIONS")
    assert constraint.persistent_open is True
    assert all("broccoli" not in item.normalized and "app" not in item.normalized for item in anchors)
    assert target_anchor_mask("Search for zucchini", {"type": "tap"}, anchors) == 1
    assert target_anchor_mask("Open directions", {"type": "tap"}, anchors) == 0


def test_constraint_parser_fixed_edge_cases() -> None:
    anchors = extract_goal_anchors("Delete entries that use zucchini from Broccoli app")
    assert [(item.predicate, item.constraint_value) for item in anchors if item.role == "CONSTRAINT"] == [("USE", "zucchini")]
    equality = extract_goal_anchors("Delete entries with title is Project X")
    assert [(item.predicate, item.constraint_scope, item.constraint_value) for item in equality if item.role == "CONSTRAINT"] == [("EQUAL", "TITLE", "Project X")]
    assert not [item for item in extract_goal_anchors("Delete entries that use one two three four five six seven in directions") if item.role == "CONSTRAINT"]
    duration = extract_goal_anchors("Delete entries that take 2 hrs to prepare")
    assert [(item.predicate, item.constraint_scope, item.constraint_value) for item in duration if item.role == "CONSTRAINT"] == [("TAKE", "PREPARATION_DURATION", "2 hrs")]
    assert len(duration) == 1


def test_first_route_is_benign_and_second_same_route_matures_t2() -> None:
    memory = ConfirmedRouteContractionECOBFMemory()
    goal = "Explore the application"
    act(memory, 0, goal, screen(0), screen(1), tap(.2, .2), "Open panel")
    first = act(memory, 1, goal, screen(1), screen(0), {"type": "press_back"}, "Return")
    assert first["route_resolutions"][0]["classification"] == "NOVEL_EXPLORATION_RETURN"
    assert not any(item.kind == "CONFIRMED_ROUTE_TRAP" for item in memory.trigger_candidates)
    act(memory, 2, goal, screen(0), screen(1), tap(.2, .2), "Open panel")
    second = act(memory, 3, goal, screen(1), screen(0), {"type": "press_back"}, "Return")
    assert any(item["path"] == "route_recurrence" for item in second["route_confirmations"])
    candidates = [item for item in memory.trigger_candidates if item.kind == "CONFIRMED_ROUTE_TRAP"]
    assert len(candidates) == 1 and candidates[0].support_count >= 2
    text, audit = memory.read({"goal": goal, "before": {"pixels": screen(0)}})
    assert text and audit["trigger_kind"] == "CONFIRMED_ROUTE_TRAP"


def test_two_no_progress_attempts_mature_t1_and_one_shot() -> None:
    memory = ConfirmedRouteContractionECOBFMemory()
    goal = "Explore the application"
    act(memory, 0, goal, screen(0), screen(0), tap(.4, .4), "Open item")
    act(memory, 1, goal, screen(0), screen(0), tap(.4, .4), "Open item")
    assert any(item.kind == "BAD_BRANCH_REPEAT" for item in memory.trigger_candidates)
    text, audit = memory.read({"goal": goal, "before": {"pixels": screen(0)}})
    assert text and audit["trigger_kind"] == "BAD_BRANCH_REPEAT"
    again, second = memory.read({"goal": goal, "before": {"pixels": screen(0)}})
    assert again == "" and second["reason"] == "cooldown"


def test_t3_requires_four_registered_decision_visits_and_three_adverse() -> None:
    memory = ConfirmedRouteContractionECOBFMemory()
    goal = "Explore the application"
    for step in range(4):
        act(memory, step, goal, screen(0), screen(0), tap(.4, .4), "Open item")
    assert any(item.kind == "CONTRACTED_FRONTIER" and item.support_count >= 3 for item in memory.trigger_candidates)
    frontier = next(iter(memory.frontiers.values()))
    assert frontier.visit_count == 4  # observe source/destination never double-register.


def test_t4_repeated_text_after_bad_outcome() -> None:
    memory = ConfirmedRouteContractionECOBFMemory()
    goal = "Enter a search"
    action = {"type": "type_text", "text": "needle", "clear_text": False}
    act(memory, 0, goal, screen(0), screen(0), action, "Search for needle")
    act(memory, 1, goal, screen(0), screen(0), action, "Search for needle")
    assert any(item.kind == "VALUE_REENTRY_AFTER_BAD_OUTCOME" and item.support_count == 2 for item in memory.trigger_candidates)


def test_t0_partial_obligation_escape_after_two_decision_screens() -> None:
    memory = ConfirmedRouteContractionECOBFMemory()
    goal = 'Create "Alpha" and "Beta"'
    act(memory, 0, goal, screen(0), screen(1), tap(.2, .2), "Create Alpha")
    assert memory.escape_watches
    act(memory, 1, goal, screen(1), screen(3), tap(.3, .3), "Open another page")
    act(memory, 2, goal, screen(3), screen(4), tap(.4, .4), "Inspect another page")
    candidates = [item for item in memory.trigger_candidates if item.kind == "PARTIAL_OBLIGATION_ESCAPE"]
    assert len(candidates) == 1
    assert candidates[0].support_count == 2
    assert candidates[0].expires_step == candidates[0].maturity_step + 6


def test_late_return_revises_durable_without_double_count() -> None:
    memory = ConfirmedRouteContractionECOBFMemory()
    goal = "Explore the application"
    act(memory, 0, goal, screen(0), screen(1), tap(.2, .2), "Open panel")
    # Reuse the same after-screen object as the next source.  The descriptor
    # may merge visually but remains deterministic; choose distinct layouts
    # that are not a standard match for the original source.
    act(memory, 1, goal, screen(1), screen(3), tap(.3, .3), "Open subsection")
    act(memory, 2, goal, screen(3), screen(4), tap(.4, .4), "Inspect")
    act(memory, 3, goal, screen(4), screen(5), tap(.5, .5), "Inspect")
    durable = act(memory, 4, goal, screen(5), screen(6), tap(.6, .6), "Inspect")
    assert any(item["outcome"] == "DURABLE_DEPARTURE" for item in durable["route_resolutions"])
    late = act(memory, 5, goal, screen(6), screen(0), {"type": "press_back"}, "Return")
    assert any(item["outcome"] == "LATE_RETURN" for item in late["route_resolutions"])
    receipt = next(item for item in memory.attempt_receipts if item.source_step == 0)
    assert receipt.resolved_outcome == "LATE_RETURN"


def test_phase_switch_keeps_episode_global_cooldown() -> None:
    memory = ConfirmedRouteContractionECOBFMemory()
    goal = 'Create "Alpha" and "Beta"'
    memory._initialize_goal(goal)
    candidate = memory._make_candidate("BAD_BRANCH_REPEAT", 0, "manual", memory._describe(screen(0)), ["r1", "r2"], .8, 1.0, 0.0, 0.0, {"branch": "tap", "branch_ids": ["b"]})
    memory._enqueue(candidate)
    text, _ = memory.read({"goal": goal, "before": {"pixels": screen(0)}})
    assert text
    old_last = memory.last_nonempty_read_step
    memory._switch_phase(1, memory.item_open_mask(), memory.item_open_mask())
    assert memory.last_nonempty_read_step == old_last
    fresh = memory._make_candidate("BAD_BRANCH_REPEAT", 1, "manual2", memory._describe(screen(0)), ["r3", "r4"], .8, 1.0, 0.0, 0.0, {"branch": "tap", "branch_ids": ["b2"]})
    memory._enqueue(fresh)
    assert memory.read({"goal": goal, "before": {"pixels": screen(0)}})[1]["reason"] == "cooldown"


def test_audit_bounds_and_decision_boundary() -> None:
    memory = ConfirmedRouteContractionECOBFMemory()
    goal = "Explore the application"
    for step in range(12):
        before = screen(step % 4)
        after = screen((step + 1) % 4)
        act(memory, step, goal, before, after, tap((step % 10 + 1) / 12, (step % 20 + 1) / 24), "Open panel")
    audit = memory.audit_record()
    assert audit["schema"] == "a11_crc_ecobf_audit_v1"
    assert audit["causal_boundary"]["model_calls_added"] == 0
    assert audit["capacity"]["serialized_audit_bytes"] <= 131072
    assert len(json.dumps(audit, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()) == audit["capacity"]["serialized_audit_bytes"]


def test_true_max_frontier_branch_exemplar_audit_is_bounded() -> None:
    memory = ConfirmedRouteContractionECOBFMemory()
    goal = "Explore the application"
    act(memory, 0, goal, screen(0), screen(0), tap(.2, .2), "Open item")
    base = next(iter(memory.frontiers.values()))
    branch = next(iter(base.branches.values()))
    memory.frontiers = {}
    for frontier_index in range(16):
        frontier = deepcopy(base)
        frontier.frontier_id = f"max_frontier_{frontier_index:02d}"
        frontier.visual_exemplars = [memory._describe(screen(index)) for index in (0, 1, 3)]
        frontier.branches = {}
        for branch_index in range(5):
            item = deepcopy(branch)
            item.branch_id = f"max_branch_{frontier_index:02d}_{branch_index}"
            item.branch_key = f"key_{frontier_index:02d}_{branch_index}"
            item.canonical_action_sha256s = [f"{branch_index:064x}"] * 3
            frontier.branches[item.branch_key] = item
        memory.frontiers[frontier.frontier_id] = frontier
    memory.attempt_receipts = [deepcopy(memory.attempt_receipts[0]) for _ in range(32)]
    for index, receipt in enumerate(memory.attempt_receipts):
        receipt.attempt_id = f"max_receipt_{index:02d}"
        receipt.branch_id = f"max_branch_{index % 16:02d}_{index % 5}"
    memory.trigger_candidates = []
    for index in range(8):
        item = memory._make_candidate("BAD_BRANCH_REPEAT", index, f"max_frontier_{index:02d}", memory._describe(screen(index % 4)), [f"r{index}a", f"r{index}b"], .8, 1.0, 0.0, 0.0, {"branch": "tap", "branch_ids": [f"b{index}"]})
        memory.trigger_candidates.append(item)
    audit = memory.audit_record()
    assert audit["frontiers"]["current_count"] == 16
    assert audit["branches"]["current_count"] == 80
    assert audit["attempts"]["retained_count"] == 32
    assert audit["triggers"]["candidate_count"] == 8
    assert audit["capacity"]["serialized_audit_bytes"] <= 131072


def test_post_read_causal_fields_update_only_after_real_actions() -> None:
    memory = ConfirmedRouteContractionECOBFMemory()
    goal = "Explore the application"
    memory._initialize_goal(goal)
    candidate = memory._make_candidate("BAD_BRANCH_REPEAT", 0, "manual", memory._describe(screen(0)), ["r1", "r2"], .8, 1.0, 0.0, 0.0, {"branch": "tap", "branch_ids": ["old_branch"]})
    memory._enqueue(candidate)
    text, _ = memory.read({"goal": goal, "before": {"pixels": screen(0)}})
    assert text
    initial = memory.read_events[0]
    assert initial["next_action_was_novel"] is None
    assert initial["escaped_frontier_within_3"] is None
    transitions = [(0, 1), (1, 3), (3, 4), (4, 5), (5, 6)]
    for step, (before_kind, after_kind) in enumerate(transitions):
        memory.observe_step(source_step=step, before={"pixels": screen(before_kind)}, after={"pixels": screen(after_kind)}, canonical_action=tap(.1 + step * .1, .2), action_summary="Open another panel")
    event = memory.read_events[0]
    assert event["next_action_branch_id"]
    assert event["next_action_was_novel"] is True
    assert event["escaped_frontier_within_3"] is True
    assert event["returned_within_4"] is False
    assert isinstance(event["anchor_confidence_delta_within_4"], float)
    assert isinstance(event["constraint_confidence_delta_within_4"], float)


def test_invalid_inputs_and_monotonic_steps() -> None:
    memory = ConfirmedRouteContractionECOBFMemory()
    with pytest.raises(A11VisibleInputError):
        memory.read({"goal": "x", "before": {"pixels": np.zeros((10, 10, 3), dtype=np.uint8)}})
    memory.read({"goal": "x", "before": {"pixels": screen(0)}})
    with pytest.raises(A11IntegrityError):
        memory.observe_step(source_step=2, before={"pixels": screen(0)}, after={"pixels": screen(0)}, canonical_action=tap(), action_summary="tap")
