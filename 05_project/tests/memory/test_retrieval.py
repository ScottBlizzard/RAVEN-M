from __future__ import annotations

from raven_m.memory.models import (
    MemoryConfig,
    MemoryItem,
    MemorySource,
    RetrievalQuery,
)
from raven_m.memory.retrieval import render_bundle, retrieve_and_route
from raven_m.memory.store import EpisodeMemoryStore


def item(
    memory_id: str,
    *,
    memory_type: str = "episodic_fact",
    status: str = "observed",
    page: str = "screen:a",
    text: str = "The note contains alpha.",
) -> MemoryItem:
    return MemoryItem(
        memory_id=memory_id,
        episode_id="episode-a",
        memory_type=memory_type,
        content={
            "subject": "note_text",
            "predicate": "contains",
            "object": "alpha",
            "natural_language": text,
        },
        task_id="DevTask",
        created_step=1,
        last_confirmed_step=1,
        source=MemorySource(
            observation_ids=("obs_000001",),
            screenshot_paths=("screen.png",),
            screenshot_sha256=("0" * 64,),
        ),
        evidence={
            "origin": "direct_visual_observation",
            "action_outcome": "text_visible",
        },
        verification_status=status,
        page_signature=page,
    )


def query() -> RetrievalQuery:
    return RetrievalQuery(
        step_id=2,
        task_terms=("note", "alpha"),
        required_variables=("note_text",),
        page_signature="screen:a",
    )


def test_single_direct_observation_is_only_a_hypothesis() -> None:
    store = EpisodeMemoryStore(episode_id="episode-a")
    store.write(item("m_0001"))
    selected = retrieve_and_route(
        query=query(),
        store=store,
        config=MemoryConfig(),
    )
    assert selected[0].route == "HYPOTHESIS"
    assert selected[0].reliability >= 0.75


def test_verified_reobservation_can_be_fact() -> None:
    store = EpisodeMemoryStore(episode_id="episode-a")
    verified = item("m_0001", status="verified")
    verified.evidence["independent_confirmations"] = 1
    store.write(verified)
    selected = retrieve_and_route(
        query=query(),
        store=store,
        config=MemoryConfig(),
    )
    assert selected[0].route == "FACT"


def test_stale_or_contradicted_memory_is_never_fact() -> None:
    store = EpisodeMemoryStore(episode_id="episode-a")
    store.write(item("m_0001", status="stale"))
    store.write(item("m_0002", status="contradicted"))
    selected = retrieve_and_route(
        query=query(),
        store=store,
        config=MemoryConfig(),
    )
    assert all(value.route != "FACT" for value in selected)
    all_routes = {
        event["memory_id"]: event["route"]
        for event in store.events
        if event["event"] == "route"
    }
    assert all(route != "FACT" for route in all_routes.values())


def test_order_and_quota_are_deterministic() -> None:
    store = EpisodeMemoryStore(episode_id="episode-a")
    for index in range(1, 6):
        store.write(item(f"m_{index:04d}", text=f"note alpha value {index}"))
    config = MemoryConfig(episodic_quota=2)
    first = retrieve_and_route(query=query(), store=store, config=config)
    second = retrieve_and_route(query=query(), store=store, config=config)
    assert len(first) == 2
    assert render_bundle(first) == render_bundle(second)
    assert [value.item.memory_id for value in first] == [
        "m_0001",
        "m_0002",
    ]


def test_global_routed_item_cap_applies_across_memory_types() -> None:
    store = EpisodeMemoryStore(episode_id="episode-a")
    store.write(item("m_0001"))
    store.write(item("m_0002"))
    store.write(
        item(
            "p_0001",
            memory_type="page_hint",
            status="candidate",
            text="The note page may contain alpha.",
        )
    )
    selected = retrieve_and_route(
        query=query(),
        store=store,
        config=MemoryConfig(routed_item_cap=2),
    )
    assert len(selected) == 2
    assert [value.item.memory_id for value in selected] == [
        "m_0001",
        "m_0002",
    ]


def test_action_outcome_requires_later_visual_confirmation_for_fact() -> None:
    store = EpisodeMemoryStore(episode_id="episode-a")
    candidate = item("m_0001")
    candidate.evidence = {
        "origin": "direct_action_outcome",
        "action_outcome": "The screenshot changed.",
        "independent_confirmations": 0,
    }
    store.write(candidate)
    selected = retrieve_and_route(
        query=query(),
        store=store,
        config=MemoryConfig(),
    )
    assert selected[0].route == "HYPOTHESIS"


def test_failure_memory_needs_page_compatibility() -> None:
    store = EpisodeMemoryStore(episode_id="episode-a")
    store.write(
        item(
            "f_0001",
            memory_type="failure",
            page="screen:other",
            text="Repeated save tap had no effect.",
        )
    )
    selected = retrieve_and_route(
        query=query(),
        store=store,
        config=MemoryConfig(),
    )
    assert selected == []
    route = [
        event["route"]
        for event in store.events
        if event["event"] == "route"
    ][-1]
    assert route == "SUPPRESS"
