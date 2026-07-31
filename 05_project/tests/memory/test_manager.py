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


def test_late_semantic_transition_invalidates_page_local_memory(
    tmp_path,
) -> None:
    manager = RavenMemoryManager()
    manager.reset(
        episode_id="episode-late-transition",
        task_id="GenericTask",
        task_goal="Open Search",
        episode_dir=tmp_path,
    )
    old_semantic = sha256(b"old-semantic-page").hexdigest()
    new_semantic = sha256(b"new-semantic-page").hexdigest()
    observation = TransitionObservation(
        step=0,
        decision_summary="Open Search.",
        action={"type": "tap", "x": 0.72, "y": 0.085},
        expected_outcome="Search opens.",
        observed_outcome=(
            "Executed Search; the semantic UI did not change."
        ),
        evidence_outcome="Search was initially unchanged.",
        before_screenshot_path="step_000_before.png",
        before_screenshot_sha256=sha256(b"before").hexdigest(),
        after_screenshot_sha256=sha256(b"after").hexdigest(),
        after_screenshot_path="step_000_after.png",
        before_semantic_ui_sha256=old_semantic,
        after_semantic_ui_sha256=old_semantic,
        state_delta=(
            {
                "kind": "fact",
                "subject": "search_button",
                "predicate": "state",
                "object": "closed",
                "natural_language": "Search is still closed.",
                "evidence": "direct_screen",
                "preconditions": ["same_task", "same_page"],
                "expires_on": ["semantic_page_changed"],
            },
        ),
    )
    written = manager.observe_transition(observation)[
        "written_memory_ids"
    ]
    assert len(written) == 1
    assert manager.store.get(written[0]).verification_status == "observed"

    result = manager.reconcile_late_semantic_transition(
        completed_step=0,
        previous_after_semantic_sha256=old_semantic,
        current_before_semantic_sha256=new_semantic,
    )

    assert result["reconciled"] is True
    assert result["invalidated_memory_ids"] == written
    assert manager.store.get(written[0]).verification_status == "stale"
    assert manager.last_page_signature == manager.page_signature(
        new_semantic,
        semantic=True,
    )
    assert "changed after delayed readiness" in (
        manager.working[-1]["observed_outcome"]
    )


def test_repeated_no_effect_supersedes_action_linked_hypothesis(
    tmp_path,
) -> None:
    manager = RavenMemoryManager()
    manager.reset(
        episode_id="episode-a",
        task_id="GenericTask",
        task_goal="Open the requested control",
        episode_dir=tmp_path,
    )
    semantic = sha256(b"unchanged-semantic-page").hexdigest()
    first = TransitionObservation(
        step=0,
        decision_summary="Tap the control.",
        action={"type": "tap", "x": 0.5, "y": 0.34},
        expected_outcome="The requested control opens.",
        observed_outcome="No semantic change.",
        evidence_outcome="The control remains closed.",
        before_screenshot_path="step_000_before.png",
        before_screenshot_sha256=sha256(b"pixel-before-0").hexdigest(),
        after_screenshot_sha256=sha256(b"pixel-after-0").hexdigest(),
        after_screenshot_path="step_000_after.png",
        before_semantic_ui_sha256=semantic,
        after_semantic_ui_sha256=semantic,
        state_delta=(
            {
                "kind": "progress",
                "subject": "control",
                "predicate": "state",
                "object": "opened",
                "natural_language": "The requested control has opened.",
                "evidence": "direct_screen",
                "confidence": 0.95,
            },
        ),
    )
    first_result = manager.observe_transition(first)
    hypothesis_id = first_result["written_memory_ids"][0]
    hypothesis = manager.store.get(hypothesis_id)
    assert hypothesis.evidence["delta_kind"] == "progress"
    assert hypothesis.evidence["action_signature"] == (
        manager.action_signature(first.action)
    )

    second = TransitionObservation(
        **{
            **first.__dict__,
            "step": 1,
            "before_screenshot_path": "step_001_before.png",
            "after_screenshot_path": "step_001_after.png",
            "before_screenshot_sha256": sha256(
                b"pixel-before-1"
            ).hexdigest(),
            "after_screenshot_sha256": sha256(
                b"pixel-after-1"
            ).hexdigest(),
            "state_delta": (
                {
                        "kind": "progress",
                        "subject": "control",
                        "predicate": "activation",
                        "object": "initiated",
                    "natural_language": (
                        "The requested control has now opened."
                    ),
                    "evidence": "direct_screen",
                    "confidence": 0.97,
                },
            ),
        }
    )
    second_result = manager.observe_transition(second)
    assert second_result["loop_detected"]
    assert hypothesis_id in second_result["invalidated_memory_ids"]
    current_hypotheses = [
        item
        for item in manager.store.all_items()
        if item.created_step == 1 and item.memory_type == "episodic_fact"
    ]
    assert len(current_hypotheses) == 1
    current_hypothesis = current_hypotheses[0]
    assert (
        current_hypothesis.memory_id
        in second_result["invalidated_memory_ids"]
    )
    failures = [
        item
        for item in manager.store.all_items()
        if item.memory_type == "failure"
    ]
    assert len(failures) == 1
    failure = failures[0]
    superseded = manager.store.get(hypothesis_id)
    assert superseded.verification_status == "superseded"
    assert superseded.relations["superseded_by"] == failure.memory_id
    assert current_hypothesis.verification_status == "superseded"
    assert (
        current_hypothesis.relations["superseded_by"]
        == failure.memory_id
    )
    supersession_events = [
        event
        for event in manager.store.events
        if event["event"] == "supersede"
        and event["newer_id"] == failure.memory_id
    ]
    assert {
        event["older_id"] for event in supersession_events
    } == {hypothesis_id, current_hypothesis.memory_id}
    assert all(
        event["event"] == "supersede"
        and event["newer_id"] == failure.memory_id
        and event["reason"]
        == (
            "repeated_action_no_effect_invalidates_"
            "unverified_action_hypothesis"
        )
        for event in supersession_events
    )
    context, routed = manager.context(step=2)
    assert hypothesis_id not in context
    assert current_hypothesis.memory_id not in context
    assert all(value.item.memory_id != hypothesis_id for value in routed)
    assert all(
        value.item.memory_id != current_hypothesis.memory_id
        for value in routed
    )
    assert failure.memory_id in context
    assert routed[0].route == "ALERT"


def test_no_effect_does_not_supersede_independent_visible_fact(
    tmp_path,
) -> None:
    manager = RavenMemoryManager()
    manager.reset(
        episode_id="episode-a",
        task_id="GenericTask",
        task_goal="Inspect the visible value",
        episode_dir=tmp_path,
    )
    semantic = sha256(b"unchanged-semantic-page").hexdigest()
    first = TransitionObservation(
        step=0,
        decision_summary="Tap the control.",
        action={"type": "tap", "x": 0.5, "y": 0.34},
        expected_outcome="The control reacts.",
        observed_outcome="No semantic change.",
        evidence_outcome="The value remains visible.",
        before_screenshot_path="step_000_before.png",
        before_screenshot_sha256=sha256(b"pixel-before-0").hexdigest(),
        after_screenshot_sha256=sha256(b"pixel-after-0").hexdigest(),
        after_screenshot_path="step_000_after.png",
        before_semantic_ui_sha256=semantic,
        after_semantic_ui_sha256=semantic,
        state_delta=(
            {
                "kind": "fact",
                "subject": "visible_value",
                "predicate": "text",
                "object": "alpha",
                "natural_language": "The visible value is alpha.",
                "evidence": "direct_screen",
                "confidence": 0.95,
            },
        ),
    )
    fact_id = manager.observe_transition(first)["written_memory_ids"][0]
    second = TransitionObservation(
        **{
            **first.__dict__,
            "step": 1,
            "before_screenshot_path": "step_001_before.png",
            "after_screenshot_path": "step_001_after.png",
            "before_screenshot_sha256": sha256(
                b"pixel-before-1"
            ).hexdigest(),
            "after_screenshot_sha256": sha256(
                b"pixel-after-1"
            ).hexdigest(),
            "state_delta": (),
        }
    )
    result = manager.observe_transition(second)
    assert result["loop_detected"]
    assert fact_id not in result["invalidated_memory_ids"]
    fact = manager.store.get(fact_id)
    assert fact.verification_status == "observed"
    assert fact.relations["superseded_by"] is None


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


def test_repeated_model_observation_stays_hypothesis(tmp_path) -> None:
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
    repeated = manager.store.get(memory_id)
    assert repeated.verification_status == "observed"
    assert repeated.evidence["independent_confirmations"] == 0
    assert repeated.evidence["model_reobservations"] == 1
    _, second_routes = manager.context(step=2)
    repeated_route = next(
        value for value in second_routes if value.item.memory_id == memory_id
    )
    assert repeated_route.route == "HYPOTHESIS"
