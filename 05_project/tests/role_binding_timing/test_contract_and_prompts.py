from __future__ import annotations

from copy import deepcopy
import json

import pytest

from raven_m.role_binding_timing.contract import (
    ContractError,
    assert_contract_budget,
    assert_generated_schema_conformance,
    load_contract,
)
from raven_m.role_binding_timing.prompts import (
    PromptInstance,
    build_prompt_pair,
)
from raven_m.role_binding_timing.token_audit import (
    HuggingFaceChatTokenCounter,
    TokenAuditError,
    WhitespaceTokenCounter,
    assert_pair_token_match,
    build_exact_neutral_block,
)


def instance() -> PromptInstance:
    return PromptInstance(
        base_family_id="BF-001",
        role_ambiguity="high",
        task_without_value="Enter the requested source field in the destination field.",
        source_entity_id="E1",
        destination_entity_id="E2",
        field="reference code",
        value="PX-4917",
        candidate_targets=(
            {"target_id": "A", "entity_id": "E1", "widget_role": "input"},
            {"target_id": "B", "entity_id": "E2", "widget_role": "input"},
        ),
    )


def grounding(target: str = "B") -> dict[str, object]:
    return {
        "phase": "grounding",
        "destination_target_id": target,
        "source_entity_id": "E1",
        "destination_entity_id": "E2",
        "confidence": 0.8,
    }


def test_contract_is_single_schema_source_and_budget_is_frozen() -> None:
    contract = load_contract()
    assert_generated_schema_conformance(contract)
    assert_contract_budget(contract)
    assert contract["novelty_status"] == "UNRESOLVED"
    assert contract["generation_eligible"] is False


def test_budget_drift_is_rejected() -> None:
    changed = deepcopy(load_contract())
    changed["model"]["calls_per_cell"] = 3
    with pytest.raises(ContractError, match="budget drifted"):
        assert_contract_budget(changed)


def test_early_late_transcripts_have_one_logical_fact_and_equal_tokens() -> None:
    counter = WhitespaceTokenCounter()
    early = build_prompt_pair(
        instance=instance(),
        fact_timing="early",
        grounding=grounding(),
        counter=counter,
    )
    late = build_prompt_pair(
        instance=instance(),
        fact_timing="late",
        grounding=grounding(),
        counter=counter,
    )
    for pair in (early, late):
        transcript = "\n".join(item["content"] for item in pair.call_2_messages)
        assert transcript.count(pair.fact_block) == 1
        assert "PX-4917" not in pair.neutral_block
        assert "E1" not in pair.neutral_block
        assert "E2" not in pair.neutral_block
    counts = assert_pair_token_match(
        early_call_1=list(early.call_1_messages),
        early_call_2=list(early.call_2_messages),
        late_call_1=list(late.call_1_messages),
        late_call_2=list(late.call_2_messages),
        counter=counter,
        tolerance=0,
    )
    assert counts["absolute_total_difference"] == 0


def test_neutral_block_fails_closed_on_forbidden_leak() -> None:
    class Counter:
        def count_text(self, text: str) -> int:
            return 1

        def count_messages(self, messages: list[dict[str, str]]) -> int:
            return len(messages)

    with pytest.raises(TokenAuditError, match="leaked"):
        build_exact_neutral_block(
            fact_block="fact",
            counter=Counter(),
            forbidden=("neutral",),
        )


def test_unknown_condition_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown fact timing"):
        build_prompt_pair(
            instance=instance(),
            fact_timing="middle",
            grounding=grounding(),
            counter=WhitespaceTokenCounter(),
        )


def test_huggingface_counter_reads_input_ids_not_batchencoding_keys() -> None:
    class FakeTokenizer:
        def apply_chat_template(self, *args: object, **kwargs: object) -> dict[str, list[int]]:
            return {"input_ids": list(range(19)), "attention_mask": [1] * 19}

    counter = object.__new__(HuggingFaceChatTokenCounter)
    counter.tokenizer = FakeTokenizer()
    assert counter.count_messages(
        [{"role": "user", "content": "a prompt with several words"}]
    ) == 19
