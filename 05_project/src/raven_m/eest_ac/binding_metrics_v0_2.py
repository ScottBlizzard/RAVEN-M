"""Three-layer binding labels for EEST-AC v0.2 post-batch analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


def _norm(value: Any) -> str:
    return " ".join(str(value).casefold().split())


def _contains(container: Any, value: str) -> bool:
    return bool(value) and _norm(value) in _norm(container)


def _field_terms(value: str) -> tuple[str, ...]:
    ignored = {"the", "a", "an", "of", "from", "entire"}
    return tuple(token for token in _norm(value).split() if token not in ignored)


@dataclass(frozen=True)
class ThreeLayerBinding:
    capture: str
    destination_retention: str
    destination_action: str

    def record(self) -> dict[str, str]:
        return {
            "source_field_value_capture": self.capture,
            "destination_role_retention": self.destination_retention,
            "value_to_destination_action": self.destination_action,
        }


def _candidate_memory_records(summary: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for item in summary.get("evidence_ledger", []):
        if isinstance(item, dict):
            yield item
    ordinary = summary.get("ordinary_summary")
    if ordinary:
        yield {"free_text": ordinary}
    for step in summary.get("steps", []):
        decision = step.get("decision", {})
        for item in decision.get("evidence", []):
            if isinstance(item, dict):
                yield item


def label_three_layers(
    summary: dict[str, Any],
    *,
    expected_value: str,
) -> ThreeLayerBinding:
    """Label one episode using only post-batch unblinded gold and raw audit fields."""
    frame = summary["task_role_frame"]
    source = frame["source"]["text"]
    field = frame["requested_field"]["text"]
    destination = frame["destination"]["text"]
    field_terms = _field_terms(field)

    capture = "missing"
    for item in _candidate_memory_records(summary):
        if "free_text" in item:
            text = item["free_text"]
            if _contains(text, expected_value) and _contains(text, source) and all(
                _contains(text, term) for term in field_terms
            ):
                capture = "correct"
                break
            if _contains(text, expected_value):
                capture = "value_without_source_field_binding"
        else:
            value_correct = _norm(item.get("value")) == _norm(expected_value)
            source_correct = _norm(item.get("entity")) == _norm(source)
            field_correct = _norm(item.get("field")) == _norm(field)
            if value_correct and source_correct and field_correct:
                capture = "correct"
                break
            if value_correct:
                capture = "wrong_source_or_field"
            elif source_correct and field_correct:
                capture = "wrong_value"

    value_steps = []
    for step in summary.get("steps", []):
        action = step.get("decision", {}).get("action")
        if (
            step.get("executed")
            and isinstance(action, dict)
            and action.get("type") in {"type_text", "answer"}
            and _norm(action.get("text")) == _norm(expected_value)
        ):
            value_steps.append(step)
    if not value_steps:
        return ThreeLayerBinding(capture, "missing", "not_attempted")

    value_step = value_steps[-1]
    decision_text = value_step.get("decision", {}).get("intent", "")
    visible = "\n".join(value_step.get("before_visible_texts", []))
    destination_seen = _contains(decision_text, destination) or _contains(visible, destination)
    source_seen = _contains(decision_text, source) or _contains(visible, source)
    if destination_seen:
        retention = "correct"
    elif source_seen:
        retention = "source_as_destination"
    else:
        retention = "missing_or_other"

    if destination_seen:
        action_label = "correct"
    elif source_seen:
        action_label = "wrong_destination"
    else:
        action_label = "destination_unverifiable"
    return ThreeLayerBinding(capture, retention, action_label)
