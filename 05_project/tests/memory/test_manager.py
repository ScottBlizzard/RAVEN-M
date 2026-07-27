from __future__ import annotations

from hashlib import sha256

from raven_m.memory.manager import RavenMemoryManager, TransitionObservation
from raven_m.memory.models import MemoryConfig


def transition(
    *,
    step: int,
    before: str,
    after: str,
    value: str = "alpha",
) -> TransitionObservation:
    return TransitionObservation(
        step=step,
        decision_summary="Read the note.",
        action={"type": "tap", "x": 0.5, "y": 0.5},
        expected_outcome="The note opens.",
        observed_outcome="The note is visible.",
        evidence_outcome="The previous screen was visible.",
        before_screenshot_path=f"step_{step:03d}_before.png",
        before_screenshot_sha256=before,
        after_screenshot_sha256=after,
        after_screenshot_path=f"step_{step:03d}_after.png",
        state_delta=(
            {
                "kind": "fact",
                "subject": "note_text",
                "predicate": "contains",
                "object": value,
                "natural_language": f"The note contains {value}.",
                "evidence": "direct_screen",
            },
        ),
    )


def test_manager_writes_routes_and_detects_conflict(tmp_path) -> None:
    manager = RavenMemoryManager()
    manager.reset(
        episode_id="episode-a",
        task_id="DevTask",
        task_goal="Read alpha from the note",
        episode_dir=tmp_path,
    )
    first = sha256(b"first").hexdigest()
    manager.observe_transition(
        transition(step=0, before=first, after=first, value="alpha")
    )
    conflicting = transition(
        step=1,
        before=first,
        after=first,
        value="beta",
    )
    conflicting = TransitionObservation(
        **{
            **conflicting.__dict__,
            "action": {"type": "tap", "x": 0.4, "y": 0.5},
        }
    )
    manager.observe_transition(conflicting)
    assert len(manager.store.items) == 2
    assert all(
        item.verification_status == "contradicted"
        for item in manager.store.all_items()
    )
    context, routed = manager.context(step=2)
    assert '"route":"ALERT"' in context
    assert all(value.route != "FACT" for value in routed)


def test_repeated_no_change_action_creates_failure_alert(tmp_path) -> None:
    manager = RavenMemoryManager()
    manager.reset(
        episode_id="episode-a",
        task_id="DevTask",
        task_goal="Save the note",
        episode_dir=tmp_path,
    )
    digest = sha256(b"same").hexdigest()
    no_delta = TransitionObservation(
        step=0,
        decision_summary="Tap save.",
        action={"type": "tap", "x": 0.9, "y": 0.1},
        expected_outcome="The note closes.",
        observed_outcome="No visible change.",
        evidence_outcome="The prior tap had no visible effect.",
        before_screenshot_path="step_000_before.png",
        before_screenshot_sha256=digest,
        after_screenshot_sha256=digest,
        after_screenshot_path="step_000_after.png",
    )
    assert not manager.observe_transition(no_delta)["loop_detected"]
    second = TransitionObservation(**{**no_delta.__dict__, "step": 1})
    result = manager.observe_transition(second)
    assert result["loop_detected"]
    assert not result["semantic_state_used"]
    failures = [
        item
        for item in manager.store.all_items()
        if item.memory_type == "failure"
    ]
    assert len(failures) == 1
    assert failures[0].source.extractor == "deterministic_loop_detector_v1"
    assert failures[0].page_signature.startswith("screen:")
    assert failures[0].evidence["action_outcome"] == (
        "same_action_same_page_no_visual_change"
    )
    context, routed = manager.context(step=2)
    assert routed[0].route == "ALERT"
    assert failures[0].memory_id in context


def test_decision_delta_uses_before_frame_and_previous_outcome(tmp_path) -> None:
    before_path = tmp_path / "step_000_before.png"
    after_path = tmp_path / "step_000_after.png"
    before_path.write_bytes(b"before")
    after_path.write_bytes(b"after")
    before = sha256(b"before").hexdigest()
    after = sha256(b"after").hexdigest()
    manager = RavenMemoryManager()
    manager.reset(
        episode_id="episode-a",
        task_id="DevTask",
        task_goal="Inspect the current page",
        episode_dir=tmp_path,
    )
    observation = transition(step=0, before=before, after=after)
    observation = TransitionObservation(
        **{
            **observation.__dict__,
            "state_delta": (
                {
                    "kind": "progress",
                    "subject": "previous_action",
                    "predicate": "outcome",
                    "object": "opened",
                    "natural_language": "The previous action opened the note.",
                    "evidence": "action_outcome",
                    "preconditions": ["same_task", "same_page"],
                },
            ),
        }
    )
    result = manager.observe_transition(observation)
    item = manager.store.get(result["written_memory_ids"][0])
    assert item.source.screenshot_paths == ("step_000_before.png",)
    assert item.source.screenshot_sha256 == (before,)
    assert item.evidence["action_outcome"] == (
        "The previous screen was visible."
    )
    assert item.verification_status == "stale"
    assert item.memory_type == "episodic_fact"


def test_page_hypothesis_is_candidate_and_retrievable(tmp_path) -> None:
    digest = sha256(b"same").hexdigest()
    manager = RavenMemoryManager()
    manager.reset(
        episode_id="episode-a",
        task_id="DevTask",
        task_goal="Open the settings page",
        episode_dir=tmp_path,
    )
    observation = transition(
        step=0,
        before=digest,
        after=digest,
    )
    observation = TransitionObservation(
        **{
            **observation.__dict__,
            "state_delta": (
                {
                    "kind": "page_hypothesis",
                    "subject": "next_page",
                    "predicate": "identity",
                    "object": "settings",
                    "natural_language": "The next page may be settings.",
                    "evidence": "inference",
                },
            ),
        }
    )
    result = manager.observe_transition(observation)
    item = manager.store.get(result["written_memory_ids"][0])
    assert item.memory_type == "page_hint"
    assert item.verification_status == "candidate"
    context, routed = manager.context(step=1)
    assert item.memory_id in context
    assert routed[0].route == "HYPOTHESIS"


def test_zero_quotas_remove_working_vel_frm_and_psi(tmp_path) -> None:
    manager = RavenMemoryManager(
        MemoryConfig(
            working_quota=0,
            episodic_quota=0,
            failure_quota=0,
            page_hint_quota=0,
        )
    )
    manager.reset(
        episode_id="episode-a",
        task_id="DevTask",
        task_goal="Inspect the page",
        episode_dir=tmp_path,
    )
    digest = sha256(b"same").hexdigest()
    observation = transition(step=0, before=digest, after=digest)
    first = manager.observe_transition(observation)
    second = manager.observe_transition(
        TransitionObservation(**{**observation.__dict__, "step": 1})
    )
    assert first["written_memory_ids"] == []
    assert second["loop_detected"]
    assert second["written_memory_ids"] == []
    assert manager.working == []
    assert manager.store.all_items() == []


def test_visible_failure_writes_observed_typed_failure(tmp_path) -> None:
    manager = RavenMemoryManager()
    manager.reset(
        episode_id="episode-a",
        task_id="CalendarTask",
        task_goal="Save the event",
        episode_dir=tmp_path,
    )
    observation = TransitionObservation(
        step=0,
        decision_summary="Tap save.",
        action={"type": "tap", "x": 0.94, "y": 0.085},
        expected_outcome="The event closes.",
        observed_outcome="A visible validation failure appeared.",
        evidence_outcome="The form was visible.",
        before_screenshot_path="step_000_before.png",
        before_screenshot_sha256=sha256(b"pixel-before").hexdigest(),
        after_screenshot_sha256=sha256(b"pixel-after").hexdigest(),
        after_screenshot_path="step_000_after.png",
        before_semantic_ui_sha256=sha256(b"same-form").hexdigest(),
        after_semantic_ui_sha256=sha256(b"same-form").hexdigest(),
        visible_failure_texts=(
            "The event cannot end earlier than it starts",
        ),
    )
    result = manager.observe_transition(observation)
    assert result["failure_detected"]
    assert result["semantic_state_used"]
    failures = [
        item
        for item in manager.store.all_items()
        if item.memory_type == "failure"
    ]
    assert len(failures) == 1
    assert failures[0].verification_status == "observed"
    assert failures[0].content["predicate"] == "visible_validation_failure"
    context, routed = manager.context(step=1)
    assert failures[0].memory_id in context
    assert routed[0].route == "ALERT"


def test_page_identity_claim_expires_on_semantic_change(tmp_path) -> None:
    manager = RavenMemoryManager()
    manager.reset(
        episode_id="episode-a",
        task_id="CalendarTask",
        task_goal="Inspect October 25",
        episode_dir=tmp_path,
    )
    before_semantic = sha256(b"month-view").hexdigest()
    after_semantic = sha256(b"day-view").hexdigest()
    observation = TransitionObservation(
        step=0,
        decision_summary="Open October 25.",
        action={"type": "tap", "x": 0.5, "y": 0.75},
        expected_outcome="The day view opens.",
        observed_outcome="The semantic UI changed.",
        evidence_outcome="The month view was visible.",
        before_screenshot_path="step_000_before.png",
        before_screenshot_sha256=sha256(b"before").hexdigest(),
        after_screenshot_sha256=sha256(b"after").hexdigest(),
        after_screenshot_path="step_000_after.png",
        before_semantic_ui_sha256=before_semantic,
        after_semantic_ui_sha256=after_semantic,
        state_delta=(
            {
                "kind": "fact",
                "subject": "page",
                "predicate": "identity",
                "object": "calendar month view",
                "natural_language": "The calendar month view is visible.",
                "evidence": "direct_screen",
            },
        ),
    )
    result = manager.observe_transition(observation)
    item = manager.store.get(result["written_memory_ids"][0])
    assert item.validity["preconditions"] == ["same_task", "same_page"]
    assert "semantic_page_changed" in item.validity["expires_on"]
    assert item.verification_status == "stale"
    _, routed = manager.context(step=1)
    assert all(value.item.memory_id != item.memory_id for value in routed)


def test_repeated_direct_observation_promotes_one_item(tmp_path) -> None:
    manager = RavenMemoryManager()
    manager.reset(
        episode_id="episode-a",
        task_id="NoteTask",
        task_goal="Read the note",
        episode_dir=tmp_path,
    )
    semantic = sha256(b"same-semantic-page").hexdigest()
    first = transition(
        step=0,
        before=sha256(b"pixel-a").hexdigest(),
        after=sha256(b"pixel-a").hexdigest(),
    )
    first = TransitionObservation(
        **{
            **first.__dict__,
            "before_semantic_ui_sha256": semantic,
            "after_semantic_ui_sha256": semantic,
        }
    )
    first_result = manager.observe_transition(first)
    memory_id = first_result["written_memory_ids"][0]
    _, first_routes = manager.context(step=1)
    assert first_routes[0].route == "HYPOTHESIS"

    second = transition(
        step=1,
        before=sha256(b"pixel-b").hexdigest(),
        after=sha256(b"pixel-b").hexdigest(),
    )
    second = TransitionObservation(
        **{
            **second.__dict__,
            "before_semantic_ui_sha256": semantic,
            "after_semantic_ui_sha256": semantic,
        }
    )
    second_result = manager.observe_transition(second)
    assert memory_id in second_result["written_memory_ids"]
    episodic = [
        item
        for item in manager.store.all_items()
        if item.memory_type == "episodic_fact"
    ]
    assert len(episodic) == 1
    verified = manager.store.get(memory_id)
    assert verified.verification_status == "verified"
    assert verified.evidence["independent_confirmations"] == 1
    _, second_routes = manager.context(step=2)
    assert second_routes[0].route == "FACT"
