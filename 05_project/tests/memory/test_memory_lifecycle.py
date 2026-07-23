from __future__ import annotations

from hashlib import sha256
import json

import pytest

from raven_m.memory.models import MemoryItem, MemorySource
from raven_m.memory.store import EpisodeMemoryStore


def make_item(
    memory_id: str = "m_0001",
    *,
    episode_id: str = "episode-a",
    value: str = "alpha",
    status: str = "observed",
    origin: str = "direct_visual_observation",
) -> MemoryItem:
    return MemoryItem(
        memory_id=memory_id,
        episode_id=episode_id,
        memory_type="episodic_fact",
        content={
            "subject": "source_note",
            "predicate": "contains_text",
            "object": value,
            "natural_language": f"The source note contains {value}.",
        },
        task_id="DevTask",
        created_step=1,
        last_confirmed_step=1,
        source=MemorySource(
            observation_ids=("obs_000001",),
            screenshot_paths=("screen.png",),
            screenshot_sha256=("0" * 64,),
        ),
        evidence={"origin": origin, "action_outcome": "text_visible"},
        verification_status=status,
        page_signature="screen:aaa",
    )


def test_model_only_inference_cannot_start_observed() -> None:
    item = make_item(origin="model_inference")
    with pytest.raises(ValueError, match="model-only"):
        item.validate()


def test_cross_episode_write_is_rejected() -> None:
    store = EpisodeMemoryStore(episode_id="episode-a")
    with pytest.raises(ValueError, match="Cross-episode"):
        store.write(make_item(episode_id="episode-b"))


def test_persistent_store_creates_empty_audit_log(tmp_path) -> None:
    event_path = tmp_path / "memory_events.jsonl"
    EpisodeMemoryStore(episode_id="episode-a", event_path=event_path)
    assert event_path.is_file()
    assert event_path.read_text(encoding="utf-8") == ""


def test_append_only_lifecycle_replays_identically() -> None:
    store = EpisodeMemoryStore(episode_id="episode-a")
    store.write(make_item())
    store.transition(
        "m_0001",
        status="verified",
        step=2,
        reason="second_direct_confirmation",
    )
    store.add_route(
        "m_0001",
        step=3,
        route="FACT",
        score=0.9,
        reliability=0.88,
    )
    replayed = EpisodeMemoryStore.replay(
        episode_id="episode-a",
        events=json.loads(json.dumps(store.events)),
    )
    assert replayed.get("m_0001").to_dict() == store.get("m_0001").to_dict()
    assert replayed.events == store.events


def test_conflicting_values_emit_contradiction() -> None:
    store = EpisodeMemoryStore(episode_id="episode-a")
    first = make_item()
    second = make_item("m_0002", value="beta")
    store.write(first)
    conflicts = store.find_conflicts(second)
    store.write(second)
    assert [item.memory_id for item in conflicts] == ["m_0001"]
    store.mark_contradiction("m_0001", "m_0002", step=2)
    assert store.get("m_0001").verification_status == "contradicted"
    assert store.get("m_0002").verification_status == "contradicted"
    assert store.events[-1]["event"] == "contradiction"


def test_provenance_file_and_hash_are_checked(tmp_path) -> None:
    screenshot = tmp_path / "screen.png"
    screenshot.write_bytes(b"fixture")
    digest = sha256(b"fixture").hexdigest()
    item = make_item()
    item.source = MemorySource(
        observation_ids=("obs_000001",),
        screenshot_paths=("screen.png",),
        screenshot_sha256=(digest,),
    )
    store = EpisodeMemoryStore(episode_id="episode-a")
    store.write(item)
    assert store.verify_provenance(tmp_path) == []
    screenshot.write_bytes(b"changed")
    assert store.verify_provenance(tmp_path) == [
        "m_0001:hash_mismatch:screen.png"
    ]
