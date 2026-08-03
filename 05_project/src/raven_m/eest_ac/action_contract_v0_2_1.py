"""Single-source EEST-AC v0.2.1 canonical action contract."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable

from jsonschema import Draft202012Validator


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTRACT_PATH = PROJECT_ROOT / "contracts/eest_ac_action_contract.v0_2_1.json"
DEFAULT_SCHEMA_PATH = PROJECT_ROOT / "schemas/eest_ac_decision.v0_2_1.schema.json"
DEFAULT_PROMPT_PATH = PROJECT_ROOT / "prompts/eest_ac/executor_v0_2_1.md"


class ActionContractError(ValueError):
    """Base error with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}:{message}")
        self.code = code
        self.message = message


class DecisionContractError(ActionContractError):
    """A response could not be made valid without model repair."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        rejected_action: Any = None,
        validation_errors: Iterable[str] = (),
        action_was_invalid: bool = False,
    ) -> None:
        super().__init__(code, message)
        self.rejected_action = rejected_action
        self.validation_errors = tuple(validation_errors)
        self.action_was_invalid = action_was_invalid


@dataclass(frozen=True)
class NormalizedAction:
    action: dict[str, Any]
    changed: bool
    provenance: tuple[str, ...]

    def record(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "changed": self.changed,
            "provenance": list(self.provenance),
        }


@dataclass(frozen=True)
class ParsedDecisionV021:
    decision: dict[str, Any]
    canonicalization: NormalizedAction | None
    schema_sha256: str
    contract_sha256: str
    extraction_used: bool


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load_contract(path: Path = DEFAULT_CONTRACT_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != "eest_ac_action_contract.v0_2_1":
        raise ActionContractError("CONTRACT_VERSION", "Unexpected action-contract version.")
    actions = value.get("actions")
    if not isinstance(actions, list) or len(actions) != 10:
        raise ActionContractError("CONTRACT_ACTION_COUNT", "Exactly ten canonical action types are required.")
    types = [item.get("type") for item in actions]
    expected = {
        "tap", "long_press", "swipe", "type_text", "press_back",
        "press_home", "press_enter", "open_app", "answer", "wait",
    }
    if len(set(types)) != len(types) or set(types) != expected:
        raise ActionContractError("CONTRACT_TYPES", f"Action types differ from the frozen set: {types!r}")
    for item in actions:
        if item["required"][0] != "type" or item["example"].get("type") != item["type"]:
            raise ActionContractError("CONTRACT_EXAMPLE", f"Malformed action entry: {item['type']}")
        allowed = {"type", *item["fields"]}
        if set(item["required"]) | set(item["optional"]) != allowed:
            raise ActionContractError("CONTRACT_FIELDS", f"Required/optional partition failed: {item['type']}")
    return value


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _field_schema(spec: dict[str, Any]) -> dict[str, Any]:
    kind = spec["kind"]
    if kind == "coordinate":
        return {"type": "number", "minimum": 0.0, "maximum": 1.0}
    result: dict[str, Any] = {"type": kind}
    for key in ("minimum", "maximum", "minLength", "maxLength"):
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
    selected = [
        action_variant_schema(item)
        for item in contract["actions"]
        if phases is None or item["phase"] in phases
    ]
    return {"oneOf": selected}


def build_decision_schema(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = contract or load_contract()
    all_actions = action_schema(contract)
    continue_actions = action_schema(contract, phases={"continue"})
    answer_action = action_schema(contract, phases={"done"})
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://eaglelab.example/eest-ac/decision.v0_2_1.schema.json",
        "type": "object",
        "additionalProperties": False,
        "required": ["status", "action", "intent", "evidence", "citations"],
        "properties": {
            "status": {"enum": ["continue", "done", "fail"]},
            "action": {"oneOf": [{"type": "null"}, all_actions]},
            "intent": {"type": "string", "minLength": 1, "maxLength": 24},
            "evidence": {
                "type": "array",
                "maxItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["entity", "field", "value", "scope"],
                    "properties": {
                        "entity": {"type": "string", "minLength": 1, "maxLength": 16},
                        "field": {"type": "string", "minLength": 1, "maxLength": 16},
                        "value": {"type": "string", "minLength": 1, "maxLength": 40},
                        "scope": {"enum": ["current_page", "cross_page", "episode"]},
                    },
                },
            },
            "citations": {
                "type": "array",
                "maxItems": 1,
                "uniqueItems": True,
                "items": {
                    "type": "string",
                    "minLength": 4,
                    "maxLength": 40,
                    "pattern": "^(ev:|task:)[A-Za-z0-9_.-]{1,35}$",
                },
            },
        },
        "allOf": [
            {
                "if": {"properties": {"status": {"const": "continue"}}, "required": ["status"]},
                "then": {"properties": {"action": continue_actions}},
            },
            {
                "if": {"properties": {"status": {"const": "done"}}, "required": ["status"]},
                "then": {"properties": {"action": {"oneOf": [{"type": "null"}, answer_action]}}},
            },
            {
                "if": {"properties": {"status": {"const": "fail"}}, "required": ["status"]},
                "then": {"properties": {"action": {"type": "null"}}},
            },
        ],
        "$defs": {
            "contract_sha256": {"const": file_sha256(DEFAULT_CONTRACT_PATH)},
        },
    }


def render_action_reference(contract: dict[str, Any] | None = None) -> str:
    contract = contract or load_contract()
    lines = []
    for item in contract["actions"]:
        required = ",".join(item["required"])
        optional = ",".join(item["optional"]) or "none"
        phase = item["phase"]
        lines.append(
            f"- {item['type']} [{phase}; required={required}; optional={optional}]: "
            f"{_canonical_json(item['example'])}"
        )
    return "\n".join(lines)


def render_executor_prompt(contract: dict[str, Any] | None = None) -> str:
    contract = contract or load_contract()
    reference = render_action_reference(contract)
    return f"""You control Android from the authoritative current screenshot. Return exactly one compact JSON object with keys status, action, intent, evidence, citations. No prose or markdown. max_new_tokens is 256.

Canonical action contract (these forms and fields are exact):
{reference}

For status=continue use exactly one continue action. For status=done use action=null, except an information-return task may use the answer action. For status=fail use action=null. Coordinates are normalized decimals in [0,1]. A swipe always uses x,y,x2,y2,duration_ms. Never emit direction, distance, dx, dy, action_details, action_args, or a generic press object. recent_app is unsupported.

Use the shared TASK_ROLES literally: source provides the requested field; destination receives that value. Never treat source as destination. Current screenshot has highest authority for visible UI; history is only for cross-page facts and confirmed transitions.

Use one action. Prefer reversible navigation. Do not wait for hypothetical popups or changes absent from the task. If RECOVERY forbids an action in the current stable state, choose a different action type. Use status=done only when the closed task is visibly complete.

For M_SLOTS only, evidence may contain at most one visible entity-field-value fact per decision. Copy entity and value exactly from the current UI, use the shared requested field when applicable, and use cross_page only when the fact will be needed after navigation. Cite only provided task:/ev: IDs. For other modes return evidence=[] and citations=[] unless citing task:root.

Complete minimal decision example: {{"status":"continue","action":{{"type":"tap","x":0.5,"y":0.5}},"intent":"open visible control","evidence":[],"citations":[]}}
"""


def _extract_json_object(raw: str) -> tuple[dict[str, Any], bool]:
    try:
        value = json.loads(raw.strip())
        if not isinstance(value, dict):
            raise DecisionContractError("TOP_LEVEL_NOT_OBJECT", "Top-level JSON must be an object.")
        return value, False
    except json.JSONDecodeError:
        fenced = re.fullmatch(r"\s*```(?:json)?\s*(\{.*\})\s*```\s*", raw, re.DOTALL | re.IGNORECASE)
        if fenced is None:
            raise DecisionContractError("NO_JSON_OBJECT", "Response is not one JSON object.")
        try:
            value = json.loads(fenced.group(1))
        except json.JSONDecodeError as exc:
            raise DecisionContractError("MALFORMED_JSON", str(exc)) from exc
        if not isinstance(value, dict):
            raise DecisionContractError("TOP_LEVEL_NOT_OBJECT", "Top-level JSON must be an object.")
        return value, True


def _ensure_coordinate(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ActionContractError("NORMALIZATION_NON_NUMERIC", f"{name} must be a finite number.")
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ActionContractError("NORMALIZATION_INPUT_OUT_OF_BOUNDS", f"{name}={number} is outside [0,1].")
    return number


def _ensure_duration(value: Any, *, default: int) -> int:
    duration = default if value is None else value
    if isinstance(duration, bool) or not isinstance(duration, int) or not 100 <= duration <= 3000:
        raise ActionContractError("NORMALIZATION_DURATION", "duration_ms must be an integer in [100,3000].")
    return duration


def normalize_action(
    action: Any,
    contract: dict[str, Any] | None = None,
) -> NormalizedAction:
    contract = contract or load_contract()
    if not isinstance(action, dict):
        raise ActionContractError("ACTION_NOT_OBJECT", "action must be an object.")
    action_type = action.get("type")
    validator = Draft202012Validator(action_schema(contract))
    if not list(validator.iter_errors(action)):
        return NormalizedAction(dict(action), False, ("canonical_input",))

    if action_type == "press":
        if set(action) != {"type", "key"}:
            raise ActionContractError("AMBIGUOUS_PRESS_FIELDS", "generic press requires exactly type and key.")
        key = action.get("key")
        mapped = contract["normalization"]["allowed_press_keys"].get(key)
        if mapped is None:
            code = "UNSUPPORTED_PRESS_KEY_RECENT_APP" if key == "recent_app" else "UNSUPPORTED_PRESS_KEY"
            raise ActionContractError(code, f"press key {key!r} has no canonical equivalent.")
        return NormalizedAction({"type": mapped}, True, ("press_key_alias", f"key:{key}"))

    if action_type != "swipe":
        raise ActionContractError("NO_SAFE_NORMALIZATION", f"No safe alias for action type {action_type!r}.")

    base = {"type", "x", "y"}
    direction_fields = {"direction", "distance"}
    delta_fields = {"dx", "dy"}
    has_direction = bool(direction_fields & set(action))
    has_delta = bool(delta_fields & set(action))
    if has_direction and has_delta:
        raise ActionContractError("MIXED_SWIPE_DIALECT", "direction/distance and dx/dy cannot be mixed.")
    allowed_extra = direction_fields if has_direction else delta_fields if has_delta else set()
    required_alias = base | allowed_extra
    allowed = required_alias | {"duration_ms"}
    if not required_alias.issubset(action) or not set(action).issubset(allowed):
        missing = required_alias - set(action)
        extra = set(action) - allowed
        raise ActionContractError(
            "INCOMPLETE_OR_EXTRA_SWIPE_FIELDS",
            f"missing={sorted(missing)!r};extra={sorted(extra)!r}",
        )
    if not (has_direction or has_delta):
        raise ActionContractError("NO_SAFE_NORMALIZATION", "Swipe has no complete supported alias dialect.")

    x = _ensure_coordinate(action["x"], "x")
    y = _ensure_coordinate(action["y"], "y")
    duration = _ensure_duration(
        action.get("duration_ms"),
        default=int(contract["normalization"]["default_swipe_duration_ms"]),
    )
    provenance: list[str]
    if has_direction:
        direction = action["direction"]
        distance = action["distance"]
        if direction not in {"left", "right", "up", "down"}:
            raise ActionContractError("SWIPE_DIRECTION", f"Unknown direction {direction!r}.")
        if isinstance(distance, bool) or not isinstance(distance, (int, float)) or not math.isfinite(float(distance)) or float(distance) <= 0:
            raise ActionContractError("SWIPE_DISTANCE", "distance must be a positive finite number.")
        distance = float(distance)
        dx = distance if direction == "right" else -distance if direction == "left" else 0.0
        dy = distance if direction == "down" else -distance if direction == "up" else 0.0
        provenance = ["direction_distance_to_endpoint", f"direction:{direction}"]
    else:
        dx_raw, dy_raw = action["dx"], action["dy"]
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) for value in (dx_raw, dy_raw)):
            raise ActionContractError("SWIPE_DELTA", "dx and dy must be finite numbers.")
        dx, dy = float(dx_raw), float(dy_raw)
        if dx == 0 and dy == 0:
            raise ActionContractError("ZERO_SWIPE_DELTA", "At least one signed delta must be non-zero.")
        provenance = ["signed_delta_to_endpoint"]
    x2, y2 = x + dx, y + dy
    if not 0.0 <= x2 <= 1.0 or not 0.0 <= y2 <= 1.0:
        raise ActionContractError(
            "NORMALIZATION_ENDPOINT_OUT_OF_BOUNDS",
            f"derived endpoint ({x2},{y2}) is outside [0,1]; clamping is forbidden.",
        )
    canonical = {
        "type": "swipe",
        "x": x,
        "y": y,
        "x2": x2,
        "y2": y2,
        "duration_ms": duration,
    }
    errors = list(validator.iter_errors(canonical))
    if errors:
        raise ActionContractError("NORMALIZATION_INTERNAL_INVALID", errors[0].message)
    provenance.append("duration_preserved" if "duration_ms" in action else "contract_default_duration")
    return NormalizedAction(canonical, True, tuple(provenance))


def _validation_errors(value: Any, schema: dict[str, Any]) -> list[str]:
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda item: list(item.absolute_path))
    rendered = []
    for error in errors[:12]:
        path = ".".join(str(part) for part in error.absolute_path) or "$"
        rendered.append(f"{path}: {error.message}")
    return rendered


def parse_decision_v0_2_1(
    raw: str,
    *,
    contract_path: Path = DEFAULT_CONTRACT_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
) -> ParsedDecisionV021:
    contract = load_contract(contract_path)
    value, extraction_used = _extract_json_object(raw)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    direct_errors = _validation_errors(value, schema)
    if not direct_errors:
        action = value.get("action")
        normalized = NormalizedAction(dict(action), False, ("canonical_input",)) if isinstance(action, dict) else None
        return ParsedDecisionV021(value, normalized, file_sha256(schema_path), file_sha256(contract_path), extraction_used)

    rejected_action = value.get("action")
    action_was_invalid = False
    normalization_error: ActionContractError | None = None
    if isinstance(rejected_action, dict):
        try:
            normalized = normalize_action(rejected_action, contract)
        except ActionContractError as exc:
            normalization_error = exc
            action_was_invalid = True
        else:
            candidate = dict(value)
            candidate["action"] = normalized.action
            candidate_errors = _validation_errors(candidate, schema)
            if not candidate_errors:
                return ParsedDecisionV021(candidate, normalized, file_sha256(schema_path), file_sha256(contract_path), extraction_used)
            direct_errors = candidate_errors

    code = normalization_error.code if normalization_error else "DECISION_SCHEMA_INVALID"
    message = normalization_error.message if normalization_error else "; ".join(direct_errors)
    raise DecisionContractError(
        code,
        message,
        rejected_action=rejected_action,
        validation_errors=direct_errors,
        action_was_invalid=action_was_invalid,
    )


def build_repair_prompt(
    *,
    original_user_prompt: str,
    raw_output: str,
    error: DecisionContractError,
    contract: dict[str, Any] | None = None,
) -> str:
    contract = contract or load_contract()
    legal = " | ".join(_canonical_json(item["example"]) for item in contract["actions"])
    diagnostics = list(error.validation_errors) or [f"{error.code}:{error.message}"]
    return "\n".join(
        (
            original_user_prompt,
            "ACTION_CONTRACT_REPAIR_V0_2_1",
            "Return only one corrected full decision JSON object. No prose, markdown, or explanation.",
            f"REJECTED_ACTION:{_canonical_json(error.rejected_action)}",
            "VALIDATION_ERRORS:" + " || ".join(diagnostics),
            f"FAILURE_CODE:{error.code}",
            "LEGAL_CANONICAL_ACTION_EXAMPLES:" + legal,
            "The action must use exactly one legal form with every required field and no extra field. recent_app is unsupported.",
            "REJECTED_FULL_OUTPUT:" + raw_output[:1800],
        )
    )


def rejected_action_fingerprint(raw: str) -> str | None:
    try:
        value, _ = _extract_json_object(raw)
    except DecisionContractError:
        return None
    action = value.get("action")
    return _canonical_json(action) if isinstance(action, dict) else None


def assert_not_identical_invalid_repair(
    *,
    initial_raw: str,
    repaired_raw: str,
    initial_error: DecisionContractError,
) -> None:
    if not initial_error.action_was_invalid:
        return
    initial = rejected_action_fingerprint(initial_raw)
    repaired = rejected_action_fingerprint(repaired_raw)
    if initial is not None and repaired == initial:
        raise DecisionContractError(
            "REPAIR_IDENTICAL_INVALID_ACTION",
            "Repair repeated the same invalid action object.",
            rejected_action=initial_error.rejected_action,
            action_was_invalid=True,
        )
