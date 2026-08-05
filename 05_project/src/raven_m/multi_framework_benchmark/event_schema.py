"""Normalized event validation and immutable JSONL writing."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "multi_framework_event.v0.2"
REQUIRED_EVENT_FIELDS = (
    "schema_version", "run_id", "arm_id", "lane", "reproduction_label",
    "source_repo", "source_commit", "checkpoint_id", "checkpoint_revision",
    "code_license", "model_license", "runtime_hash", "dependency_lock_hash",
    "prompt_hash", "task_id", "task_class", "task_seed", "task_params_hash",
    "attempt_id", "rerun_of", "step_index", "timestamp_utc",
    "observation_privileges", "screenshot_hash_before",
    "screenshot_hash_after_2s", "screenshot_hash_after_5s",
    "ui_tree_hash_before", "ui_tree_hash_after", "model_role", "call_id",
    "input_tokens", "output_tokens", "latency_seconds", "raw_prompt_path",
    "raw_response_path", "raw_response_hash", "parse_status",
    "feedback_event", "feedback_type", "action_raw_path", "action_canonical",
    "action_execute_status", "pixel_effect_class", "tree_effect_class",
    "finish_claim", "evaluator_reward", "validity_class", "failure_edge",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def digest(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def validate_event(event: dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_EVENT_FIELDS if field not in event]
    if missing:
        raise ValueError(f"Missing normalized event fields: {missing}")
    if event["schema_version"] != SCHEMA_VERSION:
        raise ValueError("Event schema version drift")
    if event["step_index"] < 0 or event["input_tokens"] < 0 or event["output_tokens"] < 0:
        raise ValueError("Negative counters are invalid")
    if not isinstance(event["feedback_event"], bool) or not isinstance(event["finish_claim"], bool):
        raise ValueError("Boolean event fields must be booleans")


def append_event(path: Path, event: dict[str, Any]) -> None:
    validate_event(event)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(canonical_json(event) + "\n")


def validate_events(events: Iterable[dict[str, Any]]) -> None:
    for event in events:
        validate_event(event)
