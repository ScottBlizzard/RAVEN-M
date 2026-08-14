from raven_m.official_qwen_mobile.a1r6_goal_anchored_pending import GoalAnchoredPendingMemory, MECHANISM_ID


def test_goal_anchor_is_exact_bounded_and_committed() -> None:
    memory = GoalAnchoredPendingMemory()
    text, audit = memory.read({"goal": "Delete A, B, and C"})
    assert "ORIGINAL GOAL REQUIREMENTS: Delete A, B, and C" in text
    assert "Locating or opening an item is not completion." in text
    event = memory.commit_injection(audit["ticket_id"], "prompt")
    assert event["exact_injected_text"] == text
    assert event["mechanism_id"] == MECHANISM_ID


def test_goal_anchor_does_not_change_r5_transition_invalidation() -> None:
    memory = GoalAnchoredPendingMemory()
    memory.observe_step(source_step=0, action_summary="MEMORY[observed=list; verified=none; pending=delete A and B] | tap", canonical_action={"type":"tap","x":.2,"y":.2}, transition={"same_shape":True,"changed_pixel_fraction_gt_5":.2}, source_call_id="c", source_response_sha256="r", source_screenshot_sha256="s")
    event = memory.observe_step(source_step=1, action_summary="I opened A.", canonical_action={"type":"tap","x":.2,"y":.2}, transition={"same_shape":True,"changed_pixel_fraction_gt_5":.8}, source_call_id="c1", source_response_sha256="r1", source_screenshot_sha256="s1")
    assert event["write_kind"] == "invalid_prefix_transition_invalidated"
    assert memory.active is None


def test_empty_goal_fails_to_duplicate_unknown_content() -> None:
    memory = GoalAnchoredPendingMemory(); text, audit = memory.read({})
    assert "ORIGINAL GOAL" not in text
    assert audit["mechanism_id"] == MECHANISM_ID
