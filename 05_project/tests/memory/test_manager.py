from __future__ import annotations

from hashlib import sha256

from raven_m.memory.manager import RavenMemoryManager, TransitionObservation


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
    failures = [
        item
        for item in manager.store.all_items()
        if item.memory_type == "failure"
    ]
    assert len(failures) == 1
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
