from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from raven_m.eest_ac.action_adapter_v0_2_1 import EestActionAdapterV021
from raven_m.eest_ac.action_contract_v0_2_1 import (
    ActionContractError,
    DecisionContractError,
    action_schema,
    assert_not_identical_invalid_repair,
    build_decision_schema,
    build_repair_prompt,
    load_contract,
    normalize_action,
    parse_decision_v0_2_1,
    render_executor_prompt,
)


ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = ROOT.parent
SCHEMA = ROOT / "schemas/eest_ac_decision.v0_2_1.schema.json"
PROMPT = ROOT / "prompts/eest_ac/executor_v0_2_1.md"
V02_RUN = REPOSITORY_ROOT / "runs/eest_ac_v0_2_blind_smoke_20260803"


def decision(action: dict, *, status: str = "continue") -> str:
    return json.dumps(
        {
            "status": status,
            "action": action,
            "intent": "qualification",
            "evidence": [],
            "citations": [],
        },
        separators=(",", ":"),
    )


def test_generated_prompt_and_schema_equal_contract_rendering() -> None:
    contract = load_contract()
    assert json.loads(SCHEMA.read_text(encoding="utf-8")) == build_decision_schema(contract)
    assert PROMPT.read_text(encoding="utf-8") == render_executor_prompt(contract)
    prompt = render_executor_prompt(contract)
    for item in contract["actions"]:
        assert json.dumps(
            item["example"],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ) in prompt
        assert f"required={','.join(item['required'])}" in prompt


def test_every_contract_example_passes_schema_and_adapter_matrix() -> None:
    contract = load_contract()
    validator = Draft202012Validator(action_schema(contract))
    adapter = EestActionAdapterV021()
    rows = adapter.conformance_matrix()
    assert len(rows) == 10
    assert {row["type"] for row in rows} == {item["type"] for item in contract["actions"]}
    assert all(row["adapter_conformant"] for row in rows)
    for item in contract["actions"]:
        assert not list(validator.iter_errors(item["example"]))


def test_status_action_matrix_makes_answer_reachable_only_for_done() -> None:
    answer = {"type": "answer", "text": "x"}
    assert parse_decision_v0_2_1(decision(answer, status="done")).decision["action"] == answer
    with pytest.raises(DecisionContractError):
        parse_decision_v0_2_1(decision(answer, status="continue"))
    with pytest.raises(DecisionContractError):
        parse_decision_v0_2_1(decision({"type": "tap", "x": 0.5, "y": 0.5}, status="done"))


@pytest.mark.parametrize(
    ("direction", "expected"),
    [
        ("up", (0.5, 0.3)),
        ("down", (0.5, 0.7)),
        ("left", (0.3, 0.5)),
        ("right", (0.7, 0.5)),
    ],
)
def test_direction_distance_normalization(direction: str, expected: tuple[float, float]) -> None:
    result = normalize_action(
        {"type": "swipe", "x": 0.5, "y": 0.5, "direction": direction, "distance": 0.2}
    )
    assert result.changed
    assert result.action["x2"] == pytest.approx(expected[0])
    assert result.action["y2"] == pytest.approx(expected[1])
    assert result.action["duration_ms"] == 500


def test_signed_delta_normalization_preserves_sign_and_duration() -> None:
    result = normalize_action(
        {"type": "swipe", "x": 0.5, "y": 0.7, "dx": -0.1, "dy": -0.4, "duration_ms": 700}
    )
    assert result.action == {
        "type": "swipe",
        "x": 0.5,
        "y": 0.7,
        "x2": pytest.approx(0.4),
        "y2": pytest.approx(0.3),
        "duration_ms": 700,
    }
    assert "duration_preserved" in result.provenance


@pytest.mark.parametrize(
    ("action", "code"),
    [
        ({"type": "press", "key": "recent_app"}, "UNSUPPORTED_PRESS_KEY_RECENT_APP"),
        ({"type": "swipe", "x": 0.5, "y": 0.9, "dx": 0.0, "dy": 0.2}, "NORMALIZATION_ENDPOINT_OUT_OF_BOUNDS"),
        ({"type": "swipe", "x": 0.5, "y": 0.5, "direction": "up", "distance": 0.2, "dx": 0, "dy": -0.2}, "MIXED_SWIPE_DIALECT"),
        ({"type": "swipe", "x": 0.5, "y": 0.5, "dx": 0.1}, "INCOMPLETE_OR_EXTRA_SWIPE_FIELDS"),
        ({"type": "swipe", "x": 0.5, "y": 0.5, "dx": 0, "dy": 0}, "ZERO_SWIPE_DELTA"),
    ],
)
def test_unsafe_or_ambiguous_aliases_fail_closed(action: dict, code: str) -> None:
    with pytest.raises(ActionContractError) as caught:
        normalize_action(action)
    assert caught.value.code == code


@pytest.mark.parametrize(
    ("key", "canonical"),
    [("back", "press_back"), ("home", "press_home"), ("enter", "press_enter")],
)
def test_semantically_unique_press_aliases(key: str, canonical: str) -> None:
    result = normalize_action({"type": "press", "key": key})
    assert result.action == {"type": canonical}
    assert result.changed


def test_repair_prompt_exposes_action_missing_extra_and_legal_forms() -> None:
    raw = decision({"type": "tap", "x": 0.5, "extra": 1})
    with pytest.raises(DecisionContractError) as caught:
        parse_decision_v0_2_1(raw)
    prompt = build_repair_prompt(
        original_user_prompt="QUALIFY",
        raw_output=raw,
        error=caught.value,
    )
    assert "REJECTED_ACTION:" in prompt
    assert "VALIDATION_ERRORS:" in prompt
    assert "required field" in prompt or "missing" in prompt
    assert "Additional properties" in prompt or "extra" in prompt
    assert "LEGAL_CANONICAL_ACTION_EXAMPLES:" in prompt
    assert "Return only one corrected full decision JSON object" in prompt


def test_identical_invalid_repair_has_deterministic_failure_code() -> None:
    raw = decision({"type": "press", "key": "recent_app"})
    with pytest.raises(DecisionContractError) as caught:
        parse_decision_v0_2_1(raw)
    with pytest.raises(DecisionContractError) as repeated:
        assert_not_identical_invalid_repair(
            initial_raw=raw,
            repaired_raw=raw,
            initial_error=caught.value,
        )
    assert repeated.value.code == "REPAIR_IDENTICAL_INVALID_ACTION"


def _maximum_value(spec: dict) -> object:
    if spec["kind"] == "coordinate":
        return 1.0
    if spec["kind"] == "integer":
        return spec["maximum"]
    if spec["kind"] == "boolean":
        return True
    if spec["kind"] == "string":
        return "x" * spec["maxLength"]
    raise AssertionError(spec)


def test_maximum_schema_serializations_are_bounded_for_256_token_certificate() -> None:
    contract = load_contract()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    sizes = []
    for item in contract["actions"]:
        action = {"type": item["type"]}
        for field, spec in item["fields"].items():
            if field in item["required"]:
                action[field] = _maximum_value(spec)
        value = {
            "status": item["phase"],
            "action": action,
            "intent": "i" * 24,
            "evidence": [
                {"entity": "e" * 16, "field": "f" * 16, "value": "v" * 40, "scope": "cross_page"}
            ],
            "citations": ["task:" + "c" * 35],
        }
        assert not list(validator.iter_errors(value))
        sizes.append(len(json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")))
    # The exact frozen Qwen tokenizer count is produced as an offline certificate;
    # this catches accidental unbounded/verbose schema growth locally.
    assert max(sizes) < 1000


def test_frozen_v0_2_raw_shape_count_is_18_and_repair_actions_repeat() -> None:
    batch = json.loads((V02_RUN / "batch_complete.json").read_text(encoding="utf-8"))
    roles = Counter()
    repeats = 0
    outputs = 0
    for cell in batch["results"]:
        summary = json.loads((REPOSITORY_ROOT / cell["episode_summary_path"]).read_text(encoding="utf-8"))
        initial = None
        for record in summary["model_call_records"]:
            outputs += 1
            roles[record["role"]] += 1
            action = json.loads(record["content"])["action"]
            if record["role"] == "executor":
                initial = action
            else:
                repeats += int(action == initial)
    assert outputs == 18
    assert roles == {"executor": 9, "executor_repair": 9}
    assert repeats == 9
