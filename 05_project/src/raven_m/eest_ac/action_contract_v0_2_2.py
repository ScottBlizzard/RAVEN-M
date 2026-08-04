"""Single-source full decision-envelope contract for EEST-AC v0.2.2."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable

from jsonschema import Draft202012Validator

from raven_m.eest_ac.action_contract_v0_2_1 import (
    ActionContractError,
    NormalizedAction,
    normalize_action as normalize_action_v0_2_1,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT_PATH = PROJECT_ROOT / "contracts/eest_ac_decision_envelope.v0_2_2.json"
DEFAULT_SCHEMA_PATH = PROJECT_ROOT / "schemas/eest_ac_decision.v0_2_2.schema.json"
DEFAULT_PROMPT_PATH = PROJECT_ROOT / "prompts/eest_ac/executor_v0_2_2.md"

EXPECTED_ACTION_TYPES = {
    "tap", "long_press", "swipe", "type_text", "press_back",
    "press_home", "press_enter", "open_app", "answer", "wait",
}
CONTROL_FIELDS = ("status", "action", "evidence", "citations")
EXPECTED_OBSERVATION_CONTRACT = {
    "delay_seconds": 1.0,
    "maximum_post_observations": 4,
    "terminal_window_observations": 2,
    "terminal_require_a11y": True,
    "terminal_equal_fields": ["pixel_sha256", "a11y_sha256", "package_names"],
    "required_change_field": "state_signature",
    "required_change_relation": "terminal_differs_from_pre",
    "fallback_policy": "none",
    "frozen_before_live_generation": True,
}


class DecisionEnvelopeError(ActionContractError):
    """A complete decision cannot be accepted without bounded model repair."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        validation_errors: Iterable[str] = (),
        rejected_action: Any = None,
        rejected_control: Any = None,
        action_was_invalid: bool = False,
        authority_plane: str = "control_plane",
        repair_allowed: bool = True,
        fingerprint_fields: Iterable[str] = CONTROL_FIELDS,
    ) -> None:
        super().__init__(code, message)
        self.validation_errors = tuple(validation_errors)
        self.rejected_action = rejected_action
        self.rejected_control = rejected_control
        self.action_was_invalid = action_was_invalid
        self.authority_plane = authority_plane
        self.repair_allowed = repair_allowed
        self.fingerprint_fields = tuple(fingerprint_fields)


@dataclass(frozen=True)
class IntentMetadataV022:
    raw_sha256: str
    raw_length_codepoints: int
    normalized_length_codepoints: int
    display_value: str
    display_length_codepoints: int
    display_truncated: bool
    display_max_codepoints: int
    metadata_normalized: bool
    provenance: tuple[str, ...]

    def record(self) -> dict[str, Any]:
        return {
            "raw_sha256": self.raw_sha256,
            "raw_length_codepoints": self.raw_length_codepoints,
            "normalized_length_codepoints": self.normalized_length_codepoints,
            "display_value": self.display_value,
            "display_length_codepoints": self.display_length_codepoints,
            "display_truncated": self.display_truncated,
            "display_max_codepoints": self.display_max_codepoints,
            "metadata_normalized": self.metadata_normalized,
            "provenance": list(self.provenance),
        }


@dataclass(frozen=True)
class ParsedDecisionV022:
    decision: dict[str, Any]
    control_plane: dict[str, Any]
    canonicalization: NormalizedAction | None
    intent_metadata: IntentMetadataV022
    schema_sha256: str
    contract_sha256: str
    extraction_used: bool
    control_plane_valid: bool = True


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def load_contract(path: Path = DEFAULT_CONTRACT_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != "eest_ac_decision_envelope.v0_2_2":
        raise ActionContractError("CONTRACT_VERSION", "Unexpected decision-envelope contract version.")
    envelope = value.get("envelope")
    if not isinstance(envelope, dict) or envelope.get("required") != [
        "status", "action", "intent", "evidence", "citations"
    ]:
        raise ActionContractError("CONTRACT_ENVELOPE", "Frozen top-level field order/requirements changed.")
    fields = envelope.get("fields", {})
    if set(fields) != set(envelope["required"]):
        raise ActionContractError("CONTRACT_FIELDS", "Every top-level field must have one policy entry.")
    if fields["intent"].get("authority") != "observability_plane":
        raise ActionContractError("CONTRACT_INTENT_AUTHORITY", "Intent must remain descriptive metadata.")
    for name in CONTROL_FIELDS:
        if fields[name].get("authority") != "control_plane":
            raise ActionContractError("CONTRACT_CONTROL_AUTHORITY", f"{name} must remain control-plane.")
    if fields["intent"].get("metadata_only_repair_calls") != 0:
        raise ActionContractError("CONTRACT_METADATA_REPAIR", "Metadata-only repair budget must be zero.")
    if value.get("generation", {}).get("max_new_tokens") != 256:
        raise ActionContractError("CONTRACT_TOKEN_CAP", "Generation cap must remain 256.")
    if value.get("qualification_observation_contract") != EXPECTED_OBSERVATION_CONTRACT:
        raise ActionContractError(
            "CONTRACT_OBSERVATION_POLICY",
            "Frozen terminal settling-window contract changed.",
        )
    actions = value.get("actions")
    if not isinstance(actions, list) or {item.get("type") for item in actions} != EXPECTED_ACTION_TYPES:
        raise ActionContractError("CONTRACT_ACTION_TYPES", "Canonical action catalog changed.")
    if len(actions) != len(EXPECTED_ACTION_TYPES):
        raise ActionContractError("CONTRACT_ACTION_COUNT", "Canonical action types must be unique.")
    for item in actions:
        if item["required"][0] != "type" or item["example"].get("type") != item["type"]:
            raise ActionContractError("CONTRACT_ACTION_EXAMPLE", f"Malformed action {item['type']}.")
        allowed = {"type", *item["fields"]}
        if set(item["required"]) | set(item["optional"]) != allowed:
            raise ActionContractError("CONTRACT_ACTION_FIELDS", f"Field partition failed for {item['type']}.")
    return value


def _field_schema(spec: dict[str, Any]) -> dict[str, Any]:
    kind = spec["kind"]
    if kind == "coordinate":
        return {"type": "number", "minimum": 0.0, "maximum": 1.0}
    if kind == "enum":
        return {"enum": spec["values"]}
    result: dict[str, Any] = {"type": kind}
    for key in ("minimum", "maximum", "minLength", "maxLength", "pattern"):
        if key in spec:
            result[key] = spec[key]
    return result


def action_variant_schema(item: dict[str, Any]) -> dict[str, Any]:
    properties = {"type": {"const": item["type"]}}
    properties.update({name: _field_schema(spec) for name, spec in item["fields"].items()})
    result: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "required": item["required"],
        "properties": properties,
    }
    if item.get("dependent_required"):
        result["dependentRequired"] = item["dependent_required"]
    return result


def action_schema(
    contract: dict[str, Any] | None = None,
    *,
    phases: set[str] | None = None,
) -> dict[str, Any]:
    contract = contract or load_contract()
    return {
        "oneOf": [
            action_variant_schema(item)
            for item in contract["actions"]
            if phases is None or item["phase"] in phases
        ]
    }


def _evidence_schema(policy: dict[str, Any]) -> dict[str, Any]:
    item = policy["item"]
    return {
        "type": "array",
        "maxItems": policy["max_items"],
        "items": {
            "type": "object",
            "additionalProperties": item["additional_properties"],
            "required": item["required"],
            "properties": {name: _field_schema(spec) for name, spec in item["fields"].items()},
        },
    }


def _citation_schema(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "array",
        "maxItems": policy["max_items"],
        "uniqueItems": policy["unique_items"],
        "items": dict(policy["item"]),
    }


def build_decision_schema(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = contract or load_contract()
    envelope = contract["envelope"]
    fields = envelope["fields"]
    all_actions = action_schema(contract)
    properties: dict[str, Any] = {
        "status": {"type": fields["status"]["type"], "enum": fields["status"]["enum"]},
        "action": {"oneOf": [{"type": "null"}, all_actions]},
        # Length is intentionally unbounded. Unicode-whitespace non-emptiness is parser-enforced.
        "intent": {"type": "string", "minLength": 1},
        "evidence": _evidence_schema(fields["evidence"]),
        "citations": _citation_schema(fields["citations"]),
    }
    all_of: list[dict[str, Any]] = []
    for status, relation in envelope["phase_relations"].items():
        variants = []
        if relation["allow_null"]:
            variants.append({"type": "null"})
        if relation["action_phases"]:
            variants.append(action_schema(contract, phases=set(relation["action_phases"])))
        action_rule = variants[0] if len(variants) == 1 else {"oneOf": variants}
        all_of.append({
            "if": {"properties": {"status": {"const": status}}, "required": ["status"]},
            "then": {"properties": {"action": action_rule}},
        })
    if envelope["authority_relations"]["evidence_requires_known_citation"]:
        all_of.append({
            "if": {"properties": {"evidence": {"minItems": 1}}, "required": ["evidence"]},
            "then": {"properties": {"citations": {"minItems": 1}}},
        })
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://eaglelab.example/eest-ac/decision.v0_2_2.schema.json",
        "type": "object",
        "additionalProperties": envelope["additional_properties"],
        "required": envelope["required"],
        "properties": properties,
        "allOf": all_of,
    }


def render_action_reference(contract: dict[str, Any] | None = None) -> str:
    contract = contract or load_contract()
    lines = []
    for item in contract["actions"]:
        lines.append(
            f"- {item['type']} [phase={item['phase']};required={','.join(item['required'])};"
            f"optional={','.join(item['optional']) or 'none'};adapter={item['adapter_operation']}]: "
            f"{_canonical_json(item['example'])}"
        )
    return "\n".join(lines)


def render_envelope_reference(contract: dict[str, Any] | None = None) -> str:
    contract = contract or load_contract()
    envelope = contract["envelope"]
    intent = envelope["fields"]["intent"]
    phases = "; ".join(
        f"{name}:null={rule['allow_null']},phases={','.join(rule['action_phases']) or 'none'}"
        for name, rule in envelope["phase_relations"].items()
    )
    return "\n".join((
        f"required_top_level={','.join(envelope['required'])};additional_properties={str(envelope['additional_properties']).lower()}",
        "authority: status/action/evidence/citations=control_plane; intent=observability_plane",
        f"phase_relations: {phases}",
        "evidence: max_items=1; fields=entity,field,value,scope; nonempty evidence requires one known citation",
        "citations: max_items=1; unique; syntax=(ev:|task:)ID; caller allowlist enforced",
        f"intent: required nonempty JSON string after Unicode whitespace normalization; no length rejection; "
        f"display_max_codepoints={intent['display_max_codepoints']};metadata_only_repair_calls=0",
    ))


def render_executor_prompt(contract: dict[str, Any] | None = None) -> str:
    contract = contract or load_contract()
    return f"""You control Android from the authoritative current screenshot. Return exactly one compact JSON object and no prose or markdown. max_new_tokens={contract['generation']['max_new_tokens']}.

AUTHORITATIVE FULL DECISION ENVELOPE:
{render_envelope_reference(contract)}

CANONICAL ACTIONS:
{render_action_reference(contract)}

For status=continue emit one continue-phase action. For status=done use action=null or the done-phase answer action. For status=fail use action=null. Coordinates are normalized decimals in [0,1]. Never clamp. Never emit recent_app, action_details, action_args, or an ambiguous generic action.

Intent is descriptive observability metadata only. It must be a nonempty string after whitespace normalization. Its length never authorizes or invalidates an otherwise legal command; long display text is deterministically logged without a repair call.

Evidence and citations are control-plane authorization. Use evidence=[] and citations=[] unless the prompt explicitly provides a visible fact and an AVAILABLE_CITATIONS allowlist. Never invent a citation. Current screenshot is authoritative for visible UI.

Use exactly one reversible action requested by the qualification instruction. Do not wait for hypothetical changes. Complete example: {{"status":"continue","action":{{"type":"tap","x":0.5,"y":0.5}},"intent":"open control","evidence":[],"citations":[]}}
"""


def _extract_json_object(raw: str) -> tuple[dict[str, Any], bool]:
    try:
        value = json.loads(raw.strip())
    except json.JSONDecodeError:
        fenced = re.fullmatch(r"\s*```(?:json)?\s*(\{.*\})\s*```\s*", raw, re.DOTALL | re.IGNORECASE)
        if fenced is None:
            raise DecisionEnvelopeError("NO_JSON_OBJECT", "Response is not one JSON object.")
        try:
            value = json.loads(fenced.group(1))
        except json.JSONDecodeError as exc:
            raise DecisionEnvelopeError("MALFORMED_JSON", str(exc)) from exc
        extraction_used = True
    else:
        extraction_used = False
    if not isinstance(value, dict):
        raise DecisionEnvelopeError("TOP_LEVEL_NOT_OBJECT", "Top-level JSON must be an object.")
    return value, extraction_used


def normalize_intent_metadata(raw_intent: Any, contract: dict[str, Any] | None = None) -> tuple[str, IntentMetadataV022]:
    contract = contract or load_contract()
    if not isinstance(raw_intent, str):
        raise DecisionEnvelopeError(
            "INTENT_NOT_STRING",
            "intent must be a JSON string.",
            authority_plane="observability_schema_critical",
            fingerprint_fields=("intent",),
        )
    normalized = " ".join(raw_intent.split())
    if not normalized:
        raise DecisionEnvelopeError(
            "INTENT_EMPTY_AFTER_NORMALIZATION",
            "intent must be nonempty after Unicode whitespace normalization.",
            authority_plane="observability_schema_critical",
            fingerprint_fields=("intent",),
        )
    limit = int(contract["envelope"]["fields"]["intent"]["display_max_codepoints"])
    truncated = len(normalized) > limit
    display = normalized[:limit]
    provenance: list[str] = []
    if normalized != raw_intent:
        provenance.append("whitespace_normalized")
    if truncated:
        provenance.append(f"display_truncated_{limit}_codepoints")
    if not provenance:
        provenance.append("canonical_metadata")
    metadata = IntentMetadataV022(
        raw_sha256=sha256(raw_intent.encode("utf-8")).hexdigest(),
        raw_length_codepoints=len(raw_intent),
        normalized_length_codepoints=len(normalized),
        display_value=display,
        display_length_codepoints=len(display),
        display_truncated=truncated,
        display_max_codepoints=limit,
        metadata_normalized=normalized != raw_intent or truncated,
        provenance=tuple(provenance),
    )
    return normalized, metadata


def _validation_errors(value: Any, schema: dict[str, Any]) -> list[str]:
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda item: list(item.absolute_path))
    rendered = []
    for error in errors[:16]:
        path = ".".join(str(part) for part in error.absolute_path) or "$"
        rendered.append(f"{path}: {error.message}")
    return rendered


def _control_plane(value: dict[str, Any]) -> dict[str, Any]:
    return {name: value.get(name) for name in CONTROL_FIELDS}


def _validate_authority(
    value: dict[str, Any],
    *,
    allowed_citations: frozenset[str],
) -> None:
    citations = value["citations"]
    unknown = [item for item in citations if item not in allowed_citations]
    if unknown:
        raise DecisionEnvelopeError(
            "UNKNOWN_CITATION",
            f"citations are not present in caller allowlist: {unknown!r}",
            validation_errors=(f"citations: unknown references {unknown!r}",),
            rejected_action=value.get("action"),
            rejected_control=_control_plane(value),
        )


def parse_decision_v0_2_2(
    raw: str,
    *,
    contract_path: Path = DEFAULT_CONTRACT_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    allowed_citations: Iterable[str] = (),
) -> ParsedDecisionV022:
    contract = load_contract(contract_path)
    value, extraction_used = _extract_json_object(raw)
    try:
        normalized_intent, intent_metadata = normalize_intent_metadata(value.get("intent"), contract)
    except DecisionEnvelopeError as exc:
        exc.rejected_action = value.get("action")
        exc.rejected_control = _control_plane(value)
        raise
    candidate = dict(value)
    candidate["intent"] = normalized_intent
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = _validation_errors(candidate, schema)
    normalized_action: NormalizedAction | None = None
    action_was_invalid = False
    normalization_error: ActionContractError | None = None
    if errors and isinstance(candidate.get("action"), dict):
        try:
            normalized_action = normalize_action_v0_2_1(candidate["action"], contract)
        except ActionContractError as exc:
            normalization_error = exc
            action_was_invalid = True
        else:
            normalized_candidate = dict(candidate)
            normalized_candidate["action"] = normalized_action.action
            normalized_errors = _validation_errors(normalized_candidate, schema)
            if not normalized_errors:
                candidate = normalized_candidate
                errors = []
            else:
                errors = normalized_errors
    if errors:
        code = normalization_error.code if normalization_error else "DECISION_CONTROL_SCHEMA_INVALID"
        message = normalization_error.message if normalization_error else "; ".join(errors)
        raise DecisionEnvelopeError(
            code,
            message,
            validation_errors=errors,
            rejected_action=value.get("action"),
            rejected_control=_control_plane(value),
            action_was_invalid=action_was_invalid,
        )
    if isinstance(candidate.get("action"), dict) and normalized_action is None:
        normalized_action = NormalizedAction(dict(candidate["action"]), False, ("canonical_input",))
    _validate_authority(candidate, allowed_citations=frozenset(allowed_citations))
    logged = dict(candidate)
    logged["intent"] = intent_metadata.display_value
    return ParsedDecisionV022(
        decision=logged,
        control_plane=_control_plane(candidate),
        canonicalization=normalized_action,
        intent_metadata=intent_metadata,
        schema_sha256=file_sha256(schema_path),
        contract_sha256=file_sha256(contract_path),
        extraction_used=extraction_used,
    )


def build_repair_prompt(
    *,
    original_user_prompt: str,
    raw_output: str,
    error: DecisionEnvelopeError,
    contract: dict[str, Any] | None = None,
) -> str:
    contract = contract or load_contract()
    legal = " | ".join(_canonical_json(item["example"]) for item in contract["actions"])
    diagnostics = list(error.validation_errors) or [f"{error.code}:{error.message}"]
    return "\n".join((
        original_user_prompt,
        "DECISION_ENVELOPE_CONTROL_REPAIR_V0_2_2",
        "Return only one corrected full decision JSON object. No prose, markdown, or explanation.",
        f"AUTHORITY_PLANE:{error.authority_plane}",
        f"FAILURE_CODE:{error.code}",
        "VALIDATION_ERRORS:" + " || ".join(diagnostics),
        f"REJECTED_CONTROL:{_canonical_json(error.rejected_control)}",
        "FULL_ENVELOPE_RULES:" + render_envelope_reference(contract).replace("\n", " || "),
        "LEGAL_CANONICAL_ACTION_EXAMPLES:" + legal,
        "Correct control/schema-critical fields only. Intent must be a nonempty string after whitespace normalization; intent length alone is never an error.",
        "Use only AVAILABLE_CITATIONS from the original prompt. Return every required top-level field and no extra field.",
        "REJECTED_FULL_OUTPUT:" + raw_output[:2400],
    ))


def _repair_fingerprint(raw: str, fields: Iterable[str]) -> str | None:
    try:
        value, _ = _extract_json_object(raw)
    except DecisionEnvelopeError:
        return None
    return _canonical_json({name: value.get(name) for name in fields})


def assert_not_identical_invalid_repair(
    *,
    initial_raw: str,
    repaired_raw: str,
    initial_error: DecisionEnvelopeError,
) -> None:
    initial = _repair_fingerprint(initial_raw, initial_error.fingerprint_fields)
    repaired = _repair_fingerprint(repaired_raw, initial_error.fingerprint_fields)
    if initial is not None and repaired == initial:
        raise DecisionEnvelopeError(
            "REPAIR_IDENTICAL_INVALID_CONTROL",
            "Repair repeated the same invalid authority-bearing fields.",
            rejected_action=initial_error.rejected_action,
            rejected_control=initial_error.rejected_control,
            action_was_invalid=initial_error.action_was_invalid,
            authority_plane=initial_error.authority_plane,
            repair_allowed=False,
            fingerprint_fields=initial_error.fingerprint_fields,
        )
