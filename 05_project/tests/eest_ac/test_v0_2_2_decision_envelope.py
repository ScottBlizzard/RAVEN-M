from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from raven_m.eest_ac.action_adapter_v0_2_2 import EestActionAdapterV022
from raven_m.eest_ac.action_contract_v0_2_2 import (
    DEFAULT_PROMPT_PATH,
    DEFAULT_SCHEMA_PATH,
    DecisionEnvelopeError,
    action_schema,
    assert_not_identical_invalid_repair,
    build_decision_schema,
    build_repair_prompt,
    load_contract,
    normalize_intent_metadata,
    parse_decision_v0_2_2,
    render_executor_prompt,
)
from raven_m.eest_ac.runtime_v0_2_2 import assert_frozen_adb_server_port


ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = ROOT.parent
V021_CALLS = REPOSITORY_ROOT / "runs/eest_ac_v0_2_1_action_qualification_20260804/probes/01_Q-SWIPE/model_calls.jsonl"


def decision(
    action: dict | None,
    *,
    status: str = "continue",
    intent: object = "qualify command",
    evidence: list | None = None,
    citations: list | None = None,
) -> str:
    return json.dumps({
        "status": status,
        "action": action,
        "intent": intent,
        "evidence": [] if evidence is None else evidence,
        "citations": [] if citations is None else citations,
    }, ensure_ascii=False, separators=(",", ":"))


def test_generated_prompt_and_schema_are_exact() -> None:
    contract = load_contract()
    assert json.loads(DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8")) == build_decision_schema(contract)
    assert DEFAULT_PROMPT_PATH.read_text(encoding="utf-8") == render_executor_prompt(contract)
    assert "maxLength" not in build_decision_schema(contract)["properties"]["intent"]
    assert "metadata_only_repair_calls=0" in render_executor_prompt(contract)
    assert "no length rejection" in render_executor_prompt(contract)


def test_full_action_catalog_schema_and_adapter_conformance() -> None:
    contract = load_contract()
    validator = Draft202012Validator(action_schema(contract))
    rows = EestActionAdapterV022().conformance_matrix()
    assert len(rows) == 10
    assert all(row["adapter_conformant"] for row in rows)
    for item in contract["actions"]:
        assert not list(validator.iter_errors(item["example"]))
        assert json.dumps(item["example"], ensure_ascii=False, sort_keys=True, separators=(",", ":")) in render_executor_prompt(contract)


def test_v0_2_1_contaminated_outputs_recover_as_swipes_with_provenance() -> None:
    records = [json.loads(line) for line in V021_CALLS.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 2
    parsed = [parse_decision_v0_2_2(record["content"]) for record in records]
    assert [item.decision["action"]["type"] for item in parsed] == ["swipe", "swipe"]
    assert [item.intent_metadata.raw_length_codepoints for item in parsed] == [27, 29]
    assert all(item.intent_metadata.provenance == ("canonical_metadata",) for item in parsed)
    assert all(not item.intent_metadata.metadata_normalized for item in parsed)


@pytest.mark.parametrize("text", ["x", "x" * 24, "x" * 27, "x" * 29, "研究动作意图" * 30])
def test_nonempty_intent_length_never_rejects(text: str) -> None:
    parsed = parse_decision_v0_2_2(decision({"type": "press_back"}, intent=text))
    assert parsed.intent_metadata.raw_length_codepoints == len(text)
    assert parsed.intent_metadata.raw_sha256 == sha256(text.encode("utf-8")).hexdigest()


def test_unicode_whitespace_normalization_is_audited() -> None:
    raw = "\u2003 scroll\t current\npage \u00a0"
    parsed = parse_decision_v0_2_2(decision({"type": "press_back"}, intent=raw))
    metadata = parsed.intent_metadata
    assert metadata.display_value == "scroll current page"
    assert metadata.metadata_normalized
    assert metadata.provenance == ("whitespace_normalized",)
    assert metadata.raw_length_codepoints == len(raw)


def test_very_long_intent_is_display_truncated_without_command_change() -> None:
    raw = "界" * 600
    parsed = parse_decision_v0_2_2(decision({"type": "press_back"}, intent=raw))
    assert parsed.control_plane["action"] == {"type": "press_back"}
    assert parsed.intent_metadata.raw_length_codepoints == 600
    assert parsed.intent_metadata.normalized_length_codepoints == 600
    assert parsed.intent_metadata.display_length_codepoints == 256
    assert parsed.intent_metadata.display_truncated
    assert parsed.intent_metadata.provenance == ("display_truncated_256_codepoints",)


@pytest.mark.parametrize(
    ("intent", "code"),
    [
        ("", "INTENT_EMPTY_AFTER_NORMALIZATION"),
        (" \t\n\u2003", "INTENT_EMPTY_AFTER_NORMALIZATION"),
        (3, "INTENT_NOT_STRING"),
        (None, "INTENT_NOT_STRING"),
    ],
)
def test_empty_or_non_string_intent_remains_schema_critical(intent: object, code: str) -> None:
    with pytest.raises(DecisionEnvelopeError) as caught:
        parse_decision_v0_2_2(decision({"type": "press_back"}, intent=intent))
    assert caught.value.code == code
    assert caught.value.authority_plane == "observability_schema_critical"
    assert caught.value.repair_allowed


def test_missing_and_extra_top_level_fields_fail_closed() -> None:
    missing = json.dumps({"status": "continue", "action": {"type": "press_back"}, "intent": "back", "evidence": []})
    with pytest.raises(DecisionEnvelopeError) as caught:
        parse_decision_v0_2_2(missing)
    assert caught.value.code == "DECISION_CONTROL_SCHEMA_INVALID"
    extra = json.loads(decision({"type": "press_back"}))
    extra["hidden"] = "branch"
    with pytest.raises(DecisionEnvelopeError):
        parse_decision_v0_2_2(json.dumps(extra))


def test_status_action_phase_relations_are_strict() -> None:
    assert parse_decision_v0_2_2(decision({"type": "press_back"})).decision["status"] == "continue"
    assert parse_decision_v0_2_2(decision(None, status="done")).decision["action"] is None
    assert parse_decision_v0_2_2(decision({"type": "answer", "text": "x"}, status="done")).decision["action"]["type"] == "answer"
    assert parse_decision_v0_2_2(decision(None, status="fail")).decision["action"] is None
    with pytest.raises(DecisionEnvelopeError):
        parse_decision_v0_2_2(decision({"type": "answer", "text": "x"}, status="continue"))
    with pytest.raises(DecisionEnvelopeError):
        parse_decision_v0_2_2(decision({"type": "press_back"}, status="done"))
    with pytest.raises(DecisionEnvelopeError):
        parse_decision_v0_2_2(decision({"type": "press_back"}, status="fail"))


def test_evidence_requires_known_citation() -> None:
    evidence = [{"entity": "row", "field": "value", "value": "42", "scope": "cross_page"}]
    with pytest.raises(DecisionEnvelopeError):
        parse_decision_v0_2_2(decision({"type": "press_back"}, evidence=evidence))
    with pytest.raises(DecisionEnvelopeError) as unknown:
        parse_decision_v0_2_2(
            decision({"type": "press_back"}, evidence=evidence, citations=["ev:visible"]),
            allowed_citations={"task:root"},
        )
    assert unknown.value.code == "UNKNOWN_CITATION"
    accepted = parse_decision_v0_2_2(
        decision({"type": "press_back"}, evidence=evidence, citations=["ev:visible"]),
        allowed_citations={"ev:visible"},
    )
    assert accepted.control_plane["evidence"] == evidence


@pytest.mark.parametrize(
    ("action", "expected"),
    [
        ({"type": "press", "key": "back"}, "press_back"),
        ({"type": "swipe", "x": 0.5, "y": 0.8, "direction": "up", "distance": 0.6}, "swipe"),
        ({"type": "swipe", "x": 0.5, "y": 0.8, "dx": 0.0, "dy": -0.6}, "swipe"),
    ],
)
def test_safe_action_aliases_still_normalize(action: dict, expected: str) -> None:
    parsed = parse_decision_v0_2_2(decision(action))
    assert parsed.decision["action"]["type"] == expected
    assert parsed.canonicalization is not None and parsed.canonicalization.changed


@pytest.mark.parametrize(
    "action",
    [
        {"type": "press", "key": "recent_app"},
        {"type": "swipe", "x": 0.5, "y": 0.9, "dx": 0.0, "dy": 0.2},
        {"type": "swipe", "x": 0.5, "y": 0.5, "direction": "up", "distance": 0.2, "dx": 0, "dy": -0.2},
    ],
)
def test_unsafe_control_aliases_fail_closed(action: dict) -> None:
    with pytest.raises(DecisionEnvelopeError):
        parse_decision_v0_2_2(decision(action))


def test_repair_prompt_contains_full_envelope_and_control_diagnostics() -> None:
    raw = decision({"type": "tap", "x": 0.5, "extra": 1})
    with pytest.raises(DecisionEnvelopeError) as caught:
        parse_decision_v0_2_2(raw)
    prompt = build_repair_prompt(original_user_prompt="QUALIFY", raw_output=raw, error=caught.value)
    assert "REJECTED_CONTROL:" in prompt
    assert "FULL_ENVELOPE_RULES:" in prompt
    assert "LEGAL_CANONICAL_ACTION_EXAMPLES:" in prompt
    assert "intent length alone is never an error" in prompt


def test_identical_invalid_control_repair_is_deterministic() -> None:
    raw = decision({"type": "press", "key": "recent_app"})
    with pytest.raises(DecisionEnvelopeError) as caught:
        parse_decision_v0_2_2(raw)
    with pytest.raises(DecisionEnvelopeError) as repeated:
        assert_not_identical_invalid_repair(
            initial_raw=raw,
            repaired_raw=raw,
            initial_error=caught.value,
        )
    assert repeated.value.code == "REPAIR_IDENTICAL_INVALID_CONTROL"


def test_intent_policy_is_machine_visible_in_contract_and_schema() -> None:
    contract = load_contract()
    policy = contract["envelope"]["fields"]["intent"]
    assert policy["authority"] == "observability_plane"
    assert policy["display_max_codepoints"] == 256
    assert policy["metadata_only_repair_calls"] == 0
    schema = build_decision_schema(contract)
    assert schema["required"] == contract["envelope"]["required"]
    assert schema["additionalProperties"] is False
    assert schema["properties"]["intent"] == {"type": "string", "minLength": 1}


def test_normalize_intent_metadata_rejects_only_type_or_empty_semantics() -> None:
    normalized, metadata = normalize_intent_metadata("  describe\tcommand  ")
    assert normalized == "describe command"
    assert metadata.display_value == normalized
    with pytest.raises(DecisionEnvelopeError):
        normalize_intent_metadata([])


def test_explicit_adb_server_port_has_no_fallback() -> None:
    assert_frozen_adb_server_port(configured=5038, supplied=5038)
    with pytest.raises(RuntimeError, match="fallback=forbidden"):
        assert_frozen_adb_server_port(configured=5038, supplied=5037)
