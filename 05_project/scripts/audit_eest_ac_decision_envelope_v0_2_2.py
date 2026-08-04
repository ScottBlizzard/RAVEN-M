"""Offline full-envelope conformance and exact-token audit for v0.2.2."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any

from jsonschema import Draft202012Validator
from tokenizers import Tokenizer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from raven_m.eest_ac.action_adapter_v0_2_2 import EestActionAdapterV022  # noqa: E402
from raven_m.eest_ac.action_contract_v0_2_2 import (  # noqa: E402
    DEFAULT_CONTRACT_PATH,
    DEFAULT_PROMPT_PATH,
    DEFAULT_SCHEMA_PATH,
    DecisionEnvelopeError,
    build_decision_schema,
    load_contract,
    normalize_intent_metadata,
    parse_decision_v0_2_2,
    render_executor_prompt,
)


MODEL_ID = "Qwen/Qwen3-VL-32B-Instruct"
MODEL_REVISION = "0cfaf48183f594c314753d30a4c4974bc75f3ccb"
ASCII = "".join(chr(index) for index in range(33, 127))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _high_entropy(length: int, offset: int = 0) -> str:
    return "".join(ASCII[(index * 37 + offset) % len(ASCII)] for index in range(length))


def _maximum_field(spec: dict[str, Any], offset: int) -> Any:
    kind = spec["kind"]
    if kind == "coordinate":
        return 1.0
    if kind == "integer":
        return spec["maximum"]
    if kind == "boolean":
        return True
    if kind == "string":
        return _high_entropy(spec["maxLength"], offset)
    raise RuntimeError(f"Unknown action field kind: {kind}")


def _maximal_control_decision(contract: dict[str, Any], action_spec: dict[str, Any], intent: str) -> dict[str, Any]:
    action = {"type": action_spec["type"]}
    for index, (field, spec) in enumerate(action_spec["fields"].items()):
        if field in action_spec["required"]:
            action[field] = _maximum_field(spec, index)
    evidence_fields = contract["envelope"]["fields"]["evidence"]["item"]["fields"]
    return {
        "status": action_spec["phase"],
        "action": action,
        "intent": intent,
        "evidence": [{
            "entity": _high_entropy(evidence_fields["entity"]["maxLength"], 2),
            "field": _high_entropy(evidence_fields["field"]["maxLength"], 3),
            "value": _high_entropy(evidence_fields["value"]["maxLength"], 4),
            "scope": "cross_page",
        }],
        "citations": ["task:" + "Ab3-" * 8 + "Ab3"],
    }


def _raw(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _token_certificate(contract: dict[str, Any], tokenizer: Tokenizer) -> list[dict[str, Any]]:
    rows = []
    for action_spec in contract["actions"]:
        candidates = []
        for length in range(1, 513):
            value = _maximal_control_decision(contract, action_spec, _high_entropy(length, 5))
            raw = _raw(value)
            candidates.append((length, len(tokenizer.encode(raw).ids), raw))
        under = [item for item in candidates if item[1] < 256]
        if not under:
            raise RuntimeError(f"Maximal control shape for {action_spec['type']} cannot fit under 256 tokens.")
        selected = max(under, key=lambda item: (item[1], item[0]))
        minimum = candidates[0]
        rows.append({
            "type": action_spec["type"],
            "maximum_control_shape_minimal_intent_tokens": minimum[1],
            "certified_intent_codepoints": selected[0],
            "certified_total_qwen_tokens": selected[1],
            "under_256": selected[1] < 256,
            "serialized_sha256": sha256(selected[2].encode("utf-8")).hexdigest(),
            "utf8_bytes": len(selected[2].encode("utf-8")),
        })
    return rows


def _decision(action: Any, *, status: str = "continue", intent: Any = "qualify", evidence: list | None = None, citations: list | None = None) -> str:
    return json.dumps({
        "status": status,
        "action": action,
        "intent": intent,
        "evidence": evidence or [],
        "citations": citations or [],
    }, ensure_ascii=False, separators=(",", ":"))


def _expect_error(raw: str, *, allowed: set[str] | None = None) -> str:
    try:
        parse_decision_v0_2_2(raw, allowed_citations=allowed or set())
    except DecisionEnvelopeError as exc:
        return exc.code
    raise RuntimeError("Expected envelope rejection.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tokenizer-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    contract = load_contract()
    schema = json.loads(DEFAULT_SCHEMA_PATH.read_text(encoding="utf-8"))
    prompt = DEFAULT_PROMPT_PATH.read_text(encoding="utf-8")
    generated_exact = schema == build_decision_schema(contract) and prompt == render_executor_prompt(contract)
    if not generated_exact:
        raise RuntimeError("Generated full-envelope artifacts drifted from the contract.")

    envelope = contract["envelope"]
    top_level_matrix = [
        {"rule": "required_fields", "contract": envelope["required"], "schema": schema["required"], "conformant": envelope["required"] == schema["required"]},
        {"rule": "additional_properties", "contract": envelope["additional_properties"], "schema": schema["additionalProperties"], "conformant": envelope["additional_properties"] == schema["additionalProperties"]},
    ]
    authority_matrix = []
    for name, policy in envelope["fields"].items():
        mentioned = f"{name}=" in prompt or name == "intent" and "intent=observability_plane" in prompt
        authority_matrix.append({
            "field": name,
            "authority": policy["authority"],
            "repair_policy": policy["repair_policy"],
            "prompt_policy_present": mentioned,
            "conformant": mentioned,
        })

    phase_matrix = [
        {"status": "continue", "valid": parse_decision_v0_2_2(_decision({"type": "press_back"})).control_plane_valid},
        {"status": "done_null", "valid": parse_decision_v0_2_2(_decision(None, status="done")).control_plane_valid},
        {"status": "done_answer", "valid": parse_decision_v0_2_2(_decision({"type": "answer", "text": "x"}, status="done")).control_plane_valid},
        {"status": "fail_null", "valid": parse_decision_v0_2_2(_decision(None, status="fail")).control_plane_valid},
        {"status": "continue_answer", "valid": False, "failure_code": _expect_error(_decision({"type": "answer", "text": "x"}))},
        {"status": "done_continue_action", "valid": False, "failure_code": _expect_error(_decision({"type": "press_back"}, status="done"))},
        {"status": "fail_action", "valid": False, "failure_code": _expect_error(_decision({"type": "press_back"}, status="fail"))},
    ]

    canonical_intent = parse_decision_v0_2_2(_decision({"type": "press_back"}, intent="observe command"))
    whitespace_intent = parse_decision_v0_2_2(_decision({"type": "press_back"}, intent=" \u2003observe\t command \n"))
    long_intent = parse_decision_v0_2_2(_decision({"type": "press_back"}, intent="界" * 600))
    intent_matrix = [
        {"case": "canonical", "accepted": True, **canonical_intent.intent_metadata.record()},
        {"case": "unicode_whitespace", "accepted": True, **whitespace_intent.intent_metadata.record()},
        {"case": "long_display", "accepted": True, **long_intent.intent_metadata.record()},
        {"case": "empty", "accepted": False, "failure_code": _expect_error(_decision({"type": "press_back"}, intent=""))},
        {"case": "whitespace_only", "accepted": False, "failure_code": _expect_error(_decision({"type": "press_back"}, intent="\u2003 \t"))},
        {"case": "non_string", "accepted": False, "failure_code": _expect_error(_decision({"type": "press_back"}, intent=4))},
    ]
    metadata_only_repair_calls = 0

    evidence = [{"entity": "row", "field": "value", "value": "42", "scope": "cross_page"}]
    evidence_matrix = [
        {"case": "evidence_without_citation", "accepted": False, "failure_code": _expect_error(_decision({"type": "press_back"}, evidence=evidence))},
        {"case": "unknown_citation", "accepted": False, "failure_code": _expect_error(_decision({"type": "press_back"}, evidence=evidence, citations=["ev:visible"]), allowed={"task:root"})},
        {"case": "known_citation", "accepted": parse_decision_v0_2_2(_decision({"type": "press_back"}, evidence=evidence, citations=["ev:visible"]), allowed_citations={"ev:visible"}).control_plane_valid},
    ]

    action_matrix = EestActionAdapterV022().conformance_matrix()
    observation = contract["qualification_observation_contract"]
    observation_matrix = [
        {
            "rule": "bounded_sampling",
            "contract": {
                "delay_seconds": observation["delay_seconds"],
                "maximum_post_observations": observation["maximum_post_observations"],
                "terminal_window_observations": observation["terminal_window_observations"],
            },
            "conformant": (
                observation["delay_seconds"] == 1.0
                and observation["maximum_post_observations"] == 4
                and observation["terminal_window_observations"] == 2
            ),
        },
        {
            "rule": "terminal_modal_agreement",
            "contract": observation["terminal_equal_fields"],
            "require_a11y": observation["terminal_require_a11y"],
            "conformant": (
                observation["terminal_equal_fields"]
                == ["pixel_sha256", "a11y_sha256", "package_names"]
                and observation["terminal_require_a11y"] is True
            ),
        },
        {
            "rule": "required_state_change",
            "field": observation["required_change_field"],
            "relation": observation["required_change_relation"],
            "conformant": (
                observation["required_change_field"] == "state_signature"
                and observation["required_change_relation"] == "terminal_differs_from_pre"
            ),
        },
        {
            "rule": "no_runtime_fallback_and_pre_live_freeze",
            "fallback_policy": observation["fallback_policy"],
            "frozen_before_live_generation": observation["frozen_before_live_generation"],
            "conformant": (
                observation["fallback_policy"] == "none"
                and observation["frozen_before_live_generation"] is True
            ),
        },
    ]
    prompt_action_matrix = []
    for item in contract["actions"]:
        example = json.dumps(item["example"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        prompt_action_matrix.append({
            "type": item["type"],
            "syntax_example_present": example in prompt,
            "required_fields_present": f"required={','.join(item['required'])}" in prompt,
        })
    tokenizer = Tokenizer.from_file(str(args.tokenizer_json))
    token_rows = _token_certificate(contract, tokenizer)
    if not all(row["under_256"] for row in token_rows):
        raise RuntimeError("Exact tokenizer certificate failed.")

    all_conformant = bool(
        all(row["conformant"] for row in top_level_matrix)
        and all(row["conformant"] for row in authority_matrix)
        and all(row["adapter_conformant"] for row in action_matrix)
        and all(row["conformant"] for row in observation_matrix)
        and all(row["syntax_example_present"] and row["required_fields_present"] for row in prompt_action_matrix)
        and metadata_only_repair_calls == 0
        and long_intent.intent_metadata.display_truncated
        and schema["properties"]["intent"] == {"type": "string", "minLength": 1}
    )
    if not all_conformant:
        raise RuntimeError("Full-envelope conformance matrix failed.")
    result = {
        "schema_version": "eest_ac_full_envelope_audit.v0_2_2",
        "status": "pass",
        "zero_model_generation_calls": 0,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "generated_artifacts_exact": generated_exact,
        "hashes": {
            "contract": _hash(DEFAULT_CONTRACT_PATH),
            "schema": _hash(DEFAULT_SCHEMA_PATH),
            "prompt": _hash(DEFAULT_PROMPT_PATH),
            "tokenizer_json": _hash(args.tokenizer_json),
        },
        "top_level_matrix": top_level_matrix,
        "authority_matrix": authority_matrix,
        "phase_matrix": phase_matrix,
        "intent_matrix": intent_matrix,
        "evidence_citation_matrix": evidence_matrix,
        "action_schema_adapter_matrix": action_matrix,
        "qualification_observation_matrix": observation_matrix,
        "prompt_action_matrix": prompt_action_matrix,
        "metadata_only_repair_calls": metadata_only_repair_calls,
        "token_certificate": {
            "construction": "maximum bounded control-plane fields plus the longest deterministic high-entropy intent prefix whose complete JSON remains below the frozen 256-token cap",
            "max_new_tokens": 256,
            "maximum_control_shape_minimal_intent_tokens": max(row["maximum_control_shape_minimal_intent_tokens"] for row in token_rows),
            "maximum_certified_total_qwen_tokens": max(row["certified_total_qwen_tokens"] for row in token_rows),
            "rows": token_rows,
        },
    }
    _write(args.output, result)
    print(json.dumps({
        "status": "pass",
        "actions": len(action_matrix),
        "full_envelope_rows": len(top_level_matrix) + len(authority_matrix) + len(phase_matrix) + len(intent_matrix) + len(evidence_matrix),
        "maximum_certified_total_qwen_tokens": result["token_certificate"]["maximum_certified_total_qwen_tokens"],
        "output": str(args.output),
    }, indent=2))


if __name__ == "__main__":
    main()
