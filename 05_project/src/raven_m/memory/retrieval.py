"""Deterministic reliability-aware retrieval and prompt rendering."""

from __future__ import annotations

from dataclasses import asdict
import json
import re
from typing import Iterable

from raven_m.memory.models import (
    MemoryConfig,
    MemoryItem,
    RetrievalFeatures,
    RetrievalQuery,
    RoutedMemory,
)
from raven_m.memory.store import EpisodeMemoryStore


def _tokens(value: object) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", str(value).lower()))


def _lexical_relevance(item: MemoryItem, query: RetrievalQuery) -> float:
    memory_tokens = _tokens(item.content.get("natural_language", ""))
    memory_tokens |= _tokens(item.content.get("subject", ""))
    memory_tokens |= _tokens(item.content.get("predicate", ""))
    query_tokens = set()
    for term in (
        *query.task_terms,
        *query.required_variables,
        *query.open_completion_requirements,
    ):
        query_tokens |= _tokens(term)
    if not memory_tokens or not query_tokens:
        return 0.0
    return len(memory_tokens & query_tokens) / len(memory_tokens | query_tokens)


def compute_features(
    item: MemoryItem,
    query: RetrievalQuery,
    config: MemoryConfig,
) -> RetrievalFeatures:
    verification = {
        "verified": 1.0,
        "observed": 0.75,
        "candidate": 0.35,
    }.get(item.verification_status, 0.0)
    origin = item.evidence.get("origin")
    outcome = 1.0 if item.evidence.get("action_outcome") else 0.6
    if origin == "model_inference":
        outcome = min(outcome, 0.25)
    provenance = 1.0 if (
        item.source.observation_ids or item.source.action_ids
    ) else 0.0
    if item.source.screenshot_paths:
        provenance = min(
            1.0,
            provenance
            + 0.25
            * int(
                len(item.source.screenshot_paths)
                == len(item.source.screenshot_sha256)
            ),
        )
    page_match = float(
        not item.page_signature
        or not query.page_signature
        or item.page_signature == query.page_signature
    )
    app_match = float(
        not item.app_id_observed
        or not query.app_label_observed
        or item.app_id_observed.lower() == query.app_label_observed.lower()
    )
    context = min(page_match, app_match)
    scope_compatible = item.validity.get("scope") == "episode" and context > 0
    subgoal_match = float(
        not item.subgoal_id
        or not query.current_subgoal_id
        or item.subgoal_id == query.current_subgoal_id
    )
    contradiction = float(item.verification_status == "contradicted")
    stale = float(
        item.verification_status
        in {"stale", "revoked", "superseded", "archived"}
    )
    failure_transfer = float(
        item.memory_type == "failure"
        and (
            not item.page_signature
            or not query.page_signature
            or item.page_signature != query.page_signature
        )
    )
    return RetrievalFeatures(
        relevance=_lexical_relevance(item, query),
        subgoal_match=subgoal_match,
        page_match=page_match,
        verification=verification,
        outcome=outcome,
        provenance=provenance,
        context=context,
        recency=config.recency(item, query.step_id),
        contradiction=contradiction,
        stale=stale,
        failure_transfer=failure_transfer,
        scope_compatible=scope_compatible,
    )


def score_item(
    item: MemoryItem,
    query: RetrievalQuery,
    config: MemoryConfig,
) -> RoutedMemory:
    features = compute_features(item, query, config)
    reliability = max(
        0.0,
        min(
            1.0,
            config.verification_weight * features.verification
            + config.outcome_weight * features.outcome
            + config.provenance_weight * features.provenance
            + config.context_weight * features.context
            + config.recency_weight * features.recency
            - config.contradiction_penalty * features.contradiction
            - config.stale_penalty * features.stale
            - config.failure_transfer_penalty * features.failure_transfer,
        ),
    )
    score = (
        config.relevance_weight * features.relevance
        + config.subgoal_weight * features.subgoal_match
        + config.page_weight * features.page_match
        + config.retrieval_recency_weight * features.recency
        + (
            config.retrieval_reliability_weight * reliability
            if config.reliability_aware
            else 0.0
        )
        - (
            config.retrieval_contradiction_penalty * features.contradiction
            if config.reliability_aware
            else 0.0
        )
        - (
            config.retrieval_stale_penalty * features.stale
            if config.reliability_aware
            else 0.0
        )
    )

    if item.memory_type == "failure" and not features.scope_compatible:
        route = "SUPPRESS"
    elif (
        item.verification_status == "contradicted"
        and features.scope_compatible
    ):
        route = "ALERT"
    elif item.verification_status in {
        "contradicted",
        "stale",
        "revoked",
        "superseded",
        "archived",
    }:
        route = (
            "ALERT"
            if (
                item.memory_type == "failure"
                or item.verification_status == "contradicted"
            )
            and score >= config.alert_min
            else "SUPPRESS"
        )
    elif (
        item.memory_type == "failure"
        and features.scope_compatible
        and score >= config.alert_min
    ):
        route = "ALERT"
    elif (
        reliability >= config.fact_threshold
        and features.scope_compatible
        and not features.contradiction
    ):
        route = "FACT"
    elif (
        reliability >= config.hypothesis_threshold
        and score >= config.retrieve_min
    ):
        route = "HYPOTHESIS"
    else:
        route = "SUPPRESS"
    return RoutedMemory(
        item=item,
        route=route,
        score=score,
        reliability=reliability,
        features=features,
    )


def _estimated_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def retrieve_and_route(
    *,
    query: RetrievalQuery,
    store: EpisodeMemoryStore,
    config: MemoryConfig,
    used_by: str = "executor",
) -> list[RoutedMemory]:
    routed = [
        score_item(item, query, config) for item in store.active_items()
    ]
    priority = {"FACT": 0, "ALERT": 1, "HYPOTHESIS": 2, "SUPPRESS": 3}
    routed.sort(
        key=lambda value: (
            priority[value.route],
            -value.score,
            value.item.memory_id,
        )
    )
    quotas = {
        "working": config.working_quota,
        "episodic_fact": config.episodic_quota,
        "failure": config.failure_quota,
        "page_hint": config.page_hint_quota,
    }
    used = {key: 0 for key in quotas}
    selected: list[RoutedMemory] = []
    token_count = 0
    for value in routed:
        if value.route == "SUPPRESS":
            store.add_route(
                value.item.memory_id,
                step=query.step_id,
                route=value.route,
                score=value.score,
                reliability=value.reliability,
                used_by=used_by,
            )
            continue
        memory_type = value.item.memory_type
        if used[memory_type] >= quotas[memory_type]:
            continue
        rendered = json.dumps(
            {
                "memory_id": value.item.memory_id,
                "route": value.route,
                "status": value.item.verification_status,
                "content": value.item.content["natural_language"],
                "source": list(value.item.source.observation_ids)
                + list(value.item.source.action_ids),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        item_tokens = _estimated_tokens(rendered)
        if selected and token_count + item_tokens > config.memory_prompt_tokens:
            continue
        selected.append(value)
        used[memory_type] += 1
        token_count += item_tokens
        store.add_route(
            value.item.memory_id,
            step=query.step_id,
            route=value.route,
            score=value.score,
            reliability=value.reliability,
            used_by=used_by,
        )
    return selected


def render_bundle(values: Iterable[RoutedMemory]) -> str:
    records = []
    for value in values:
        records.append(
            {
                "memory_id": value.item.memory_id,
                "type": value.item.memory_type,
                "route": value.route,
                "status": value.item.verification_status,
                "reliability": round(value.reliability, 4),
                "content": value.item.content["natural_language"],
                "scope": value.item.validity.get("scope"),
                "page_signature": value.item.page_signature,
                "provenance": {
                    "observations": list(value.item.source.observation_ids),
                    "actions": list(value.item.source.action_ids),
                    "screenshot_sha256": list(
                        value.item.source.screenshot_sha256
                    ),
                },
                "features": asdict(value.features),
            }
        )
    return json.dumps(
        {"schema_version": "memory_bundle.v1", "items": records},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
