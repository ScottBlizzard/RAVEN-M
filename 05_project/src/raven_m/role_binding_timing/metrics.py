"""Cell-level first-target and role-binding diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
import unicodedata
from typing import Any


@dataclass(frozen=True)
class CellMetrics:
    wrong_target_first_targeting_action: bool
    grounding_destination_correct: bool
    action_target_correct: bool
    post_grounding_drift: bool
    exact_value_recall: bool
    source_as_target: bool
    other_wrong_entity: bool
    correct_target_wrong_widget: bool
    source_role_correct: bool
    destination_role_correct: bool


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def score_cell(
    *,
    grounding: dict[str, Any],
    action: dict[str, Any],
    variant: dict[str, Any],
    expected_value: str,
) -> CellMetrics:
    targets = {item["target_id"]: item for item in variant["candidate_targets"]}
    action_target_id = action["action"]["target_id"]
    action_target = targets[action_target_id]
    destination_target_id = variant["destination_target_id"]
    action_target_correct = action_target_id == destination_target_id
    source_target_id = variant.get("source_target_id")
    source_as_target = source_target_id is not None and action_target_id == source_target_id
    same_destination_entity = (
        action_target["entity_id"] == variant["destination_entity_id"]
    )
    correct_target_wrong_widget = (
        not action_target_correct
        and same_destination_entity
        and action_target["widget_role"] != variant["destination_widget_role"]
    )
    return CellMetrics(
        wrong_target_first_targeting_action=not action_target_correct,
        grounding_destination_correct=(
            grounding["destination_target_id"] == destination_target_id
        ),
        action_target_correct=action_target_correct,
        post_grounding_drift=(
            action["grounded_destination_target_id"]
            != grounding["destination_target_id"]
        ),
        exact_value_recall=(_nfc(action["recalled_value"]) == _nfc(expected_value)),
        source_as_target=source_as_target,
        other_wrong_entity=(
            not action_target_correct
            and not source_as_target
            and not same_destination_entity
        ),
        correct_target_wrong_widget=correct_target_wrong_widget,
        source_role_correct=(
            grounding["source_entity_id"] == variant["source_entity_id"]
        ),
        destination_role_correct=(
            grounding["destination_entity_id"] == variant["destination_entity_id"]
        ),
    )
