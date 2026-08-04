"""Deterministic two-call prompt construction with one logical fact occurrence."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from raven_m.role_binding_timing.contract import canonical_json, load_contract
from raven_m.role_binding_timing.token_audit import (
    TokenCounter,
    build_exact_neutral_block,
)


@dataclass(frozen=True)
class PromptInstance:
    base_family_id: str
    role_ambiguity: str
    task_without_value: str
    source_entity_id: str
    destination_entity_id: str
    field: str
    value: str
    candidate_targets: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class PromptPair:
    fact_timing: str
    fact_block: str
    neutral_block: str
    call_1_messages: tuple[dict[str, str], ...]
    call_2_messages: tuple[dict[str, str], ...]


def fact_block(instance: PromptInstance) -> str:
    payload = {
        "field": instance.field,
        "source_entity_id": instance.source_entity_id,
        "value": instance.value,
    }
    return "FACT_BLOCK=" + canonical_json(payload)


def canonical_grounding_commitment(grounding: dict[str, Any]) -> str:
    selected = {
        "destination_entity_id": grounding["destination_entity_id"],
        "destination_target_id": grounding["destination_target_id"],
        "source_entity_id": grounding["source_entity_id"],
    }
    return canonical_json(selected)


def _common_context(instance: PromptInstance) -> str:
    targets = [
        {
            "entity_id": item["entity_id"],
            "target_id": item["target_id"],
            "widget_role": item["widget_role"],
        }
        for item in instance.candidate_targets
    ]
    return "\n".join(
        [
            f"BASE_FAMILY={instance.base_family_id}",
            f"ROLE_AMBIGUITY={instance.role_ambiguity}",
            f"TASK_WITHOUT_VALUE={instance.task_without_value}",
            "TARGET_CANDIDATES=" + canonical_json(targets),
            "CURRENT_SCREENSHOT_AND_UI_TREE=hash-locked attachments",
        ]
    )


def build_prompt_pair(
    *,
    instance: PromptInstance,
    fact_timing: str,
    grounding: dict[str, Any],
    counter: TokenCounter,
    contract: dict[str, Any] | None = None,
) -> PromptPair:
    contract = contract or load_contract()
    if fact_timing not in contract["factorial"]["fact_timing"]:
        raise ValueError(f"Unknown fact timing: {fact_timing}")
    if instance.role_ambiguity not in contract["factorial"]["role_ambiguity"]:
        raise ValueError(f"Unknown role ambiguity: {instance.role_ambiguity}")
    fact = fact_block(instance)
    forbidden = (
        instance.source_entity_id,
        instance.destination_entity_id,
        instance.field,
        instance.value,
    )
    neutral = build_exact_neutral_block(
        fact_block=fact,
        counter=counter,
        forbidden=forbidden,
    )
    early_block = fact if fact_timing == "early" else neutral
    late_block = neutral if fact_timing == "early" else fact
    common = _common_context(instance)
    user_1 = "\n".join(
        [common, early_block, contract["grounding_instruction"]]
    )
    assistant_commitment = canonical_grounding_commitment(grounding)
    user_2 = "\n".join(
        [
            "CANONICAL_GROUNDING_COMMITMENT=" + assistant_commitment,
            late_block,
            contract["action_instruction"],
        ]
    )
    call_1 = (
        {"role": "system", "content": contract["system_prompt"]},
        {"role": "user", "content": user_1},
    )
    call_2 = (
        {"role": "system", "content": contract["system_prompt"]},
        {"role": "user", "content": user_1},
        {"role": "assistant", "content": assistant_commitment},
        {"role": "user", "content": user_2},
    )
    transcript = "\n".join(item["content"] for item in call_2)
    if transcript.count(fact) != 1:
        raise ValueError("Each logical two-call transcript must contain the fact once.")
    if instance.value in neutral:
        raise ValueError("Neutral block leaked the fact value.")
    return PromptPair(
        fact_timing=fact_timing,
        fact_block=fact,
        neutral_block=neutral,
        call_1_messages=call_1,
        call_2_messages=call_2,
    )
