from __future__ import annotations

import numpy as np

from raven_m.official_qwen_mobile.a8_failure_aware_revisit import (
    FailureAwareExactRevisitMemory,
)


def _screen(pattern: int, **hidden: object) -> dict:
    pixels = np.zeros((100, 80, 3), dtype=np.uint8)
    if pattern == 0:
        pixels[:, 40:] = 255
    elif pattern == 1:
        pixels[50:, :] = 255
    else:
        pixels[:, :] = 127
    return {"pixels": pixels, **hidden}


def _step(
    source_step: int,
    *,
    before: int = 0,
    after: int = 0,
    x: float = 0.401,
    y: float = 0.599,
    unchanged: bool = True,
) -> dict:
    return {
        "source_step": source_step,
        "action_summary": "Tap the same visible row again.",
        "canonical_action": {"type": "tap", "x": x, "y": y},
        "transition": {
            "exactly_unchanged": unchanged,
            "changed_pixel_fraction_gt_5": 0.0 if unchanged else 0.5,
            "ui_sha_changed": True,
            "activity_changed": True,
        },
        "before": _screen(before, evaluator_reward=1.0, ui_tree="hidden before"),
        "after": _screen(after, evaluator_reward=0.0, ui_tree="hidden after"),
        "source_response_sha256": f"{source_step:064d}",
    }


def test_aggregates_repeated_no_progress_action_instead_of_duplicate_entries() -> None:
    memory = FailureAwareExactRevisitMemory(max_chars=500)
    for step, x in enumerate((0.401, 0.403, 0.399, 0.402)):
        update = memory.observe_step(**_step(step, x=x))
        assert update["written"] is True
    rendered, read = memory.read(
        {"before": _screen(0, evaluator_reward=999.0, ui_tree="different hidden")}
    )
    assert read["exact_match"] is True
    assert read["state_action_family_count"] == 1
    assert "tried 4x" in rendered
    assert "no/negligible visible change 4x" in rendered
    assert rendered.count("tap@") == 2  # one action fact plus one closed-route fact


def test_reports_exact_closed_navigation_route_without_blocking() -> None:
    memory = FailureAwareExactRevisitMemory(max_chars=500)
    memory.observe_step(**_step(0, before=0, after=1, unchanged=False))
    memory.observe_step(**_step(1, before=1, after=0, unchanged=False, x=0.2, y=0.2))
    rendered, read = memory.read({"before": _screen(0)})
    assert read["closed_route"]["action_count"] == 2
    assert "returned to this exact screen after 2 action(s)" in rendered
    assert "no action is blocked or replaced" in rendered
    audit = memory.audit_record()
    assert audit["guard_enabled"] is False
    assert audit["action_override_count"] == 0


def test_different_visible_pixels_do_not_near_match() -> None:
    memory = FailureAwareExactRevisitMemory()
    memory.observe_step(**_step(0))
    rendered, read = memory.read({"before": _screen(1)})
    assert rendered == ""
    assert read["exact_match"] is False
    assert memory.audit_record()["near_match_enabled"] is False


def test_visible_change_is_observation_not_completion_claim() -> None:
    memory = FailureAwareExactRevisitMemory(max_chars=500)
    memory.observe_step(**_step(0, before=0, after=1, unchanged=False))
    rendered, _ = memory.read({"before": _screen(0)})
    assert "visible change 1x" in rendered
    assert "not task-completion evidence" in rendered
    assert "success" not in rendered.casefold()


def test_audit_proves_controller_only_decision_boundary() -> None:
    memory = FailureAwareExactRevisitMemory(max_states=2, max_actions_per_state=2)
    original = _step(0)["canonical_action"].copy()
    memory.observe_step(**_step(0))
    memory.read({"before": _screen(0, evaluator_reward=1, ui_tree="must be ignored")})
    assert _step(0)["canonical_action"] == original
    audit = memory.audit_record()
    assert audit["model_calls_added"] == 0
    assert audit["evaluator_used_for_decision"] is False
    assert audit["hidden_ui_used_for_decision"] is False
    assert audit["evidence_boundary"] == "policy_action_plus_model_visible_pixel_transition_only"


def test_action_family_provenance_is_bounded() -> None:
    memory = FailureAwareExactRevisitMemory(max_actions_per_state=1)
    for step in range(8):
        memory.observe_step(**_step(step, x=0.401 + step * 0.0001))
    actions = memory.audit_record()["states"][0]["actions"]
    assert len(actions) == 1
    assert len(actions[0]["canonical_action_sha256s"]) == 4
