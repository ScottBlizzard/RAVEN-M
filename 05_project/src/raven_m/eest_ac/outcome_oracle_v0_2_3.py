"""Task-agnostic action-conditioned outcome oracle for EEST-AC v0.2.3."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT_PATH = PROJECT_ROOT / "contracts/eest_ac_outcome_oracle.v0_2_3.json"
DEFAULT_SCHEMA_PATH = PROJECT_ROOT / "schemas/eest_ac_outcome_trace.v0_2_3.schema.json"
SHA256_PATTERN = "^[a-f0-9]{64}$"


class OutcomeOracleError(ValueError):
    pass


@dataclass(frozen=True)
class OracleDecisionV023:
    decision: str
    confidence_label: str
    confidence: float
    rule_id: str
    required_witnesses: tuple[str, ...]
    optional_witnesses: tuple[str, ...]
    vetoes: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    input_sha256: str
    contract_sha256: str

    def record(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "confidence_label": self.confidence_label,
            "confidence": self.confidence,
            "rule_id": self.rule_id,
            "required_witnesses": list(self.required_witnesses),
            "optional_witnesses": list(self.optional_witnesses),
            "vetoes": list(self.vetoes),
            "missing_evidence": list(self.missing_evidence),
            "input_sha256": self.input_sha256,
            "contract_sha256": self.contract_sha256,
        }


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def value_sha256(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def context_route_signature(package_names: list[str], activity: str | None) -> str:
    return value_sha256({"package_names": sorted(package_names), "activity": activity})


def load_contract(path: Path = DEFAULT_CONTRACT_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != "eest_ac_outcome_oracle.v0_2_3":
        raise OutcomeOracleError("Unexpected oracle contract version.")
    if value.get("terminal_window") != 2:
        raise OutcomeOracleError("Terminal window changed.")
    if value.get("decision_vocabulary") != ["accept", "reject", "uncertain"]:
        raise OutcomeOracleError("Decision vocabulary changed.")
    classes = value.get("input", {}).get("action_classes")
    if classes != ["scroll", "open_app", "navigation_press"]:
        raise OutcomeOracleError("Action class catalog changed.")
    if set(value.get("policies", {})) != set(classes):
        raise OutcomeOracleError("Action policy catalog is incomplete.")
    if value.get("authority", {}).get("pixel_can_authorize_accept") is not False:
        raise OutcomeOracleError("Pixels may not authorize accept.")
    return value


def _observation_schema() -> dict[str, Any]:
    nullable_hash = {"oneOf": [{"type": "null"}, {"type": "string", "pattern": SHA256_PATTERN}]}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": load_contract()["input"]["observation_required"],
        "properties": {
            "pixel_sha256": {"type": "string", "pattern": SHA256_PATTERN},
            "a11y_available": {"type": "boolean"},
            "a11y_sha256": nullable_hash,
            "page_content_sha256": nullable_hash,
            "package_names": {"type": "array", "items": {"type": "string", "minLength": 1}, "uniqueItems": True},
            "activity": {"oneOf": [{"type": "null"}, {"type": "string", "minLength": 1}]},
            "route_signature": nullable_hash,
        },
    }


def build_trace_schema(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = contract or load_contract()
    observation = _observation_schema()
    resolver = {
        "type": "object",
        "additionalProperties": False,
        "required": contract["input"]["resolver_required"],
        "properties": {
            "target_packages": {"type": "array", "items": {"type": "string", "minLength": 1}, "uniqueItems": True},
            "target_activities": {"type": "array", "items": {"type": "string", "minLength": 1}, "uniqueItems": True},
            "provenance_sha256": {"oneOf": [{"type": "null"}, {"type": "string", "pattern": SHA256_PATTERN}]},
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://eaglelab.example/eest-ac/outcome-trace.v0_2_3.schema.json",
        "type": "object",
        "additionalProperties": contract["input"]["additional_properties"],
        "required": contract["input"]["required"],
        "properties": {
            "trace_id": {"type": "string", "pattern": "^[A-Za-z0-9_.-]{1,64}$"},
            "action_class": {"enum": contract["input"]["action_classes"]},
            "action": {"type": "object", "minProperties": 1},
            "resolver": {"oneOf": [{"type": "null"}, resolver]},
            "pre": observation,
            "post": {"type": "array", "minItems": contract["terminal_window"], "maxItems": 8, "items": observation},
        },
    }


def parse_trace_v0_2_3(raw: str, schema_path: Path = DEFAULT_SCHEMA_PATH) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OutcomeOracleError(f"TRACE_JSON_INVALID:{exc}") from exc
    errors = sorted(
        Draft202012Validator(json.loads(schema_path.read_text(encoding="utf-8"))).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        path = ".".join(str(part) for part in errors[0].absolute_path) or "$"
        raise OutcomeOracleError(f"TRACE_SCHEMA_INVALID:{path}:{errors[0].message}")
    return value


def _decision(
    *,
    trace: dict[str, Any],
    contract: dict[str, Any],
    decision: str,
    rule_id: str,
    required: list[str] | tuple[str, ...] = (),
    optional: list[str] | tuple[str, ...] = (),
    vetoes: list[str] | tuple[str, ...] = (),
    missing: list[str] | tuple[str, ...] = (),
) -> OracleDecisionV023:
    confidence = contract["confidence"][decision]
    return OracleDecisionV023(
        decision=decision,
        confidence_label=confidence["label"],
        confidence=float(confidence["value"]),
        rule_id=rule_id,
        required_witnesses=tuple(required),
        optional_witnesses=tuple(optional),
        vetoes=tuple(vetoes),
        missing_evidence=tuple(missing),
        input_sha256=value_sha256(trace),
        contract_sha256=file_sha256(DEFAULT_CONTRACT_PATH),
    )


def _missing_observation(observation: dict[str, Any], prefix: str) -> list[str]:
    missing = []
    if not observation["package_names"]:
        missing.append(f"{prefix}.package_names")
    if not observation["route_signature"]:
        missing.append(f"{prefix}.route_signature")
    if not observation["a11y_available"]:
        missing.append(f"{prefix}.a11y_available")
    if not observation["a11y_sha256"]:
        missing.append(f"{prefix}.a11y_sha256")
    if not observation["page_content_sha256"]:
        missing.append(f"{prefix}.page_content_sha256")
    return missing


def _context_contradictory(observation: dict[str, Any]) -> bool:
    if observation["route_signature"] is None:
        return False
    return observation["route_signature"] != context_route_signature(
        observation["package_names"], observation["activity"]
    )


def _terminal(trace: dict[str, Any], contract: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str], list[str], list[str]]:
    samples = trace["post"][-int(contract["terminal_window"]):]
    missing = []
    for index, sample in enumerate(samples):
        missing.extend(_missing_observation(sample, f"terminal[{index}]"))
    contradictions = ["contradictory_context_identity"] if any(_context_contradictory(sample) for sample in samples) else []
    stable_fields = ("package_names", "activity", "route_signature", "a11y_sha256", "page_content_sha256")
    unstable = [field for field in stable_fields if samples[0][field] != samples[1][field]]
    optional = []
    if samples[0]["pixel_sha256"] == samples[1]["pixel_sha256"]:
        optional.append("terminal_pixels_stable")
    else:
        optional.append("terminal_pixels_unstable")
    return samples, missing, contradictions, unstable + optional


def evaluate_trace_v0_2_3(trace: dict[str, Any], contract: dict[str, Any] | None = None) -> OracleDecisionV023:
    contract = contract or load_contract()
    action_class = trace["action_class"]
    pre = trace["pre"]
    terminal, missing, contradictions, status = _terminal(trace, contract)
    first, last = terminal
    optional = [item for item in status if item.startswith("terminal_pixels_")]
    unstable = [item for item in status if not item.startswith("terminal_pixels_")]
    if contradictions or _context_contradictory(pre):
        return _decision(
            trace=trace, contract=contract, decision="reject", rule_id="GENERIC_CONTRADICTORY_CONTEXT",
            vetoes=["contradictory_context_identity"], optional=optional,
        )
    if missing:
        return _decision(
            trace=trace, contract=contract, decision="uncertain", rule_id="GENERIC_MISSING_CRITICAL_EVIDENCE",
            missing=sorted(set(missing)), optional=optional,
        )
    if unstable:
        return _decision(
            trace=trace, contract=contract, decision="reject", rule_id="GENERIC_TERMINAL_SEMANTIC_INSTABILITY",
            vetoes=["terminal_semantic_instability", *[f"unstable:{item}" for item in unstable]], optional=optional,
        )
    pixels_changed = pre["pixel_sha256"] != last["pixel_sha256"]
    if pixels_changed:
        optional.append("pixels_changed")

    if action_class == "scroll":
        pre_missing = _missing_observation(pre, "pre")
        if pre_missing:
            return _decision(
                trace=trace, contract=contract, decision="uncertain", rule_id="SCROLL_MISSING_PRE_EVIDENCE",
                missing=pre_missing, optional=optional,
            )
        if pre["route_signature"] != last["route_signature"]:
            return _decision(
                trace=trace, contract=contract, decision="reject", rule_id="SCROLL_CONTEXT_TRANSITION",
                required=["terminal_semantics_stable"], vetoes=["context_transition"], optional=optional,
            )
        if pre["page_content_sha256"] != last["page_content_sha256"]:
            return _decision(
                trace=trace, contract=contract, decision="accept", rule_id="SCROLL_STABLE_A11Y_CHANGE",
                required=["pre_a11y_available", "terminal_semantics_stable", "same_route_context", "stable_page_content_changed"],
                optional=optional,
            )
        return _decision(
            trace=trace, contract=contract, decision="reject", rule_id="SCROLL_STABLE_NO_SEMANTIC_CHANGE",
            required=["terminal_semantics_stable", "same_route_context"],
            vetoes=["stable_no_semantic_change", *( ["pixel_only_change"] if pixels_changed else [] )], optional=optional,
        )

    if action_class == "open_app":
        resolver = trace["resolver"]
        if resolver is None or not resolver["target_packages"] or not resolver["provenance_sha256"]:
            return _decision(
                trace=trace, contract=contract, decision="uncertain", rule_id="OPEN_APP_MISSING_RESOLVER_TARGET",
                missing=["resolver.target_packages_or_provenance"], optional=optional,
            )
        targets = set(resolver["target_packages"])
        terminal_packages = set(last["package_names"])
        if not targets.intersection(terminal_packages):
            return _decision(
                trace=trace, contract=contract, decision="reject", rule_id="OPEN_APP_WRONG_TARGET",
                required=["resolver_target_available", "terminal_semantics_stable"], vetoes=["wrong_target"], optional=optional,
            )
        activity_targets = set(resolver["target_activities"])
        if activity_targets and last["activity"] not in activity_targets:
            return _decision(
                trace=trace, contract=contract, decision="reject", rule_id="OPEN_APP_WRONG_ACTIVITY",
                required=["resolver_target_available", "terminal_semantics_stable"], vetoes=["wrong_target"], optional=optional,
            )
        pre_matches = bool(targets.intersection(pre["package_names"]))
        if pre_matches and pre["route_signature"] == last["route_signature"] and pre["page_content_sha256"] == last["page_content_sha256"]:
            return _decision(
                trace=trace, contract=contract, decision="reject", rule_id="OPEN_APP_ALREADY_TARGET_NOOP",
                required=["resolver_target_available", "terminal_semantics_stable", "terminal_target_match"],
                vetoes=["already_target_noop"], optional=optional,
            )
        return _decision(
            trace=trace, contract=contract, decision="accept", rule_id="OPEN_APP_STABLE_RESOLVER_TARGET",
            required=["resolver_target_available", "terminal_semantics_stable", "terminal_target_match", "not_already_target_noop"],
            optional=[*optional, *( ["activity_target_match"] if activity_targets else [] ), *( ["page_content_changed"] if pre["page_content_sha256"] != last["page_content_sha256"] else [] )],
        )

    if action_class == "navigation_press":
        route_changed = pre["route_signature"] != last["route_signature"]
        page_changed = pre["page_content_sha256"] != last["page_content_sha256"]
        if route_changed or page_changed:
            transition = "cross_context_transition" if route_changed else "same_context_page_change"
            return _decision(
                trace=trace, contract=contract, decision="accept", rule_id="NAV_STABLE_SEMANTIC_TRANSITION",
                required=["terminal_semantics_stable", "cross_context_transition_or_same_context_page_change"],
                optional=[*optional, transition],
            )
        return _decision(
            trace=trace, contract=contract, decision="reject", rule_id="NAV_STABLE_NOOP",
            required=["terminal_semantics_stable"],
            vetoes=["stable_noop", *( ["pixel_only_change"] if pixels_changed else [] )], optional=optional,
        )
    raise OutcomeOracleError(f"Unsupported action class: {action_class}")
