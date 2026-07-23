from hashlib import sha256
from pathlib import Path

import pytest

from raven_m.actions.schema import ActionValidationError
from raven_m.history.policies import HistoryEntry, RavenMemoryPolicy


def test_raven_policy_rejects_unavailable_citation(tmp_path: Path) -> None:
    policy = RavenMemoryPolicy()
    policy.reset(
        episode_dir=tmp_path,
        goal="Read the note",
        episode_id="episode-a",
        task_id="DevTask",
    )
    policy.context()
    with pytest.raises(ActionValidationError, match="unavailable"):
        policy.validate_decision({"memory_citations": ["m_9999"]})


def test_raven_policy_writes_state_delta(tmp_path: Path) -> None:
    screenshot = tmp_path / "step_000_after.png"
    before_screenshot = tmp_path / "step_000_before.png"
    screenshot.write_bytes(b"fixture")
    before_screenshot.write_bytes(b"before")
    digest = sha256(b"fixture").hexdigest()
    before_digest = sha256(b"before").hexdigest()
    policy = RavenMemoryPolicy()
    policy.reset(
        episode_dir=tmp_path,
        goal="Read alpha from the note",
        episode_id="episode-a",
        task_id="DevTask",
    )
    update = policy.observe(
        HistoryEntry(
            step=0,
            decision_summary="Read the title.",
            action={"type": "tap", "x": 0.5, "y": 0.5},
            observed_outcome="The note opened.",
            screenshot_path=screenshot,
            screenshot_sha256=digest,
            before_screenshot_path=before_screenshot,
            before_screenshot_sha256=before_digest,
            expected_outcome="The note opens.",
            state_delta=(
                {
                    "kind": "fact",
                    "subject": "note_title",
                    "predicate": "equals",
                    "object": "Alpha",
                    "natural_language": "The note title is Alpha.",
                    "evidence": "direct_screen",
                },
            ),
        ),
        episode_id="episode-a",
        remaining_model_calls=0,
    )
    assert update.details["written_memory_ids"] == ["m_0001"]
    item = policy.manager.store.get("m_0001")
    assert item.source.screenshot_paths == ("step_000_before.png",)
    assert item.source.screenshot_sha256 == (before_digest,)
    assert policy.manager.store.verify_provenance(tmp_path) == []
    context = policy.context().rendered
    assert '"memory_id":"m_0001"' in context
