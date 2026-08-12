"""A11 Confirmed Route-Contraction ECOBF memory.

The implementation is episode-local and deterministic.  Its decision state is
derived only from the query, model-visible RGB, already executed canonical
actions, and policy-authored action summaries.  It never calls a model and it
does not filter, replace, or terminate actions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import math
import re
import unicodedata
from typing import Any, Iterable

import numpy as np

from .a10_obligation_branch_frontier import (
    VisualDescriptor,
    canonical_action_family as _a10_action_family,
    changed_pixel_fraction,
    describe_visual_state,
    visual_distance,
    visual_match,
)


MECHANISM_ID = "a11_confirmed_route_contraction_ecobf_v1"
EXPERIMENT_ID = "A11_CRC_ECOBF_QWEN3VL32B_AW_HARD_T20260806_G3407_V1"
AUDIT_SCHEMA = "a11_crc_ecobf_audit_v1"


class A11VisibleInputError(RuntimeError):
    """The controller did not provide legal model-visible RGB."""


class A11IntegrityError(RuntimeError):
    """A frozen A11 identity, ordering, capacity, or rendering rule failed."""


def _norm(value: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value)).casefold().split())


def _anchor_norm(value: Any) -> str:
    return re.sub(r"[_\W]+", " ", _norm(value), flags=re.UNICODE).strip()


def _compact(value: Any, limit: int) -> str:
    text = " ".join(str(value).split()).strip()
    return text if len(text) <= limit else text[: max(0, limit - 3)].rstrip() + "..."


def _json_sha(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _sat(value: int) -> int:
    return min(255, max(0, int(value)))


def _visible_rgb(snapshot: dict[str, Any]) -> np.ndarray:
    pixels = np.asarray(snapshot.get("pixels"))
    if (
        pixels.ndim != 3
        or pixels.shape[0] < 25
        or pixels.shape[1] < 8
        or pixels.shape[2] < 3
        or not np.issubdtype(pixels.dtype, np.integer)
    ):
        raise A11VisibleInputError("A11 requires integer model-visible RGB")
    if pixels.size and (int(pixels.min()) < 0 or int(pixels.max()) > 255):
        raise A11VisibleInputError("A11 RGB values must be within [0,255]")
    return np.ascontiguousarray(pixels[:, :, :3])


def _descriptor_audit(value: VisualDescriptor) -> dict[str, Any]:
    return {
        "exact_sha256": value.exact_sha256,
        "descriptor_sha256": value.descriptor_sha256,
        "luma_q_packed_hex": "".join(format(item, "x") for item in value.luma_q),
        "edge_bits_hex": value.edge_bits_hex,
        "crop_shape": value.crop_shape,
    }


def _round_floats(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {key: _round_floats(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_round_floats(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_round_floats(item) for item in value)
    return value


_OPERATION_LEXICON = (
    ("DELETE", ("delete", "remove", "erase")),
    ("TRANSFER", ("send", "share", "sms", "export")),
    ("TRANSFORM", ("merge", "transcribe", "copy", "convert")),
    ("CREATE_OR_ADD", ("add", "create", "save", "make", "mark")),
    ("QUERY_OR_CALCULATE", ("find", "calculate", "total", "report", "list", "what")),
    ("NAVIGATE", ("open", "launch", "navigate")),
)


def classify_operation(goal: str) -> str:
    text = _norm(goal)
    for label, words in _OPERATION_LEXICON:
        if any(re.search(rf"\b{re.escape(word)}\b", text) for word in words):
            return label
    return "OTHER"


_INTENT_LEXICON = (
    ("COMMIT", ("delete", "remove", "add", "create", "save", "send", "share", "submit", "confirm", "merge", "copy", "mark", "export")),
    ("OPEN_OR_SELECT", ("open", "launch", "navigate", "select", "choose")),
    ("INPUT_OR_SEARCH", ("type", "enter", "fill", "search")),
    ("INSPECT", ("inspect", "check", "view", "read", "find", "calculate")),
    ("RECOVER", ("back", "return", "close", "cancel")),
    ("SCROLL", ("scroll", "swipe")),
    ("WAIT", ("wait",)),
    ("ANSWER", ("answer",)),
)


def classify_intent(summary: str, action: dict[str, Any]) -> str:
    text = _norm(summary)
    for label, words in _INTENT_LEXICON:
        if any(re.search(rf"\b{re.escape(word)}\b", text) for word in words):
            return label
    return {
        "type_text": "INPUT_OR_SEARCH",
        "swipe": "SCROLL",
        "press_back": "RECOVER",
        "wait": "WAIT",
        "answer": "ANSWER",
    }.get(str(action.get("type") or ""), "OTHER")


def canonical_action_family(action: dict[str, Any]) -> tuple[Any, ...]:
    try:
        return _a10_action_family(action)
    except Exception as exc:  # A11 exposes only its own integrity boundary.
        raise A11IntegrityError(str(exc)) from exc


WORD = r"[^\W_]+(?:[-’'][^\W_]+)*"
PREDICATE_MAP = {
    "use": "USE", "uses": "USE", "contain": "CONTAIN", "contains": "CONTAIN",
    "include": "INCLUDE", "includes": "INCLUDE", "have": "HAVE", "has": "HAVE",
    "take": "TAKE", "takes": "TAKE", "last": "LAST", "lasts": "LAST",
    "cost": "COST", "costs": "COST", "match": "MATCH", "matches": "MATCH",
    "equal": "EQUAL", "equals": "EQUAL", "is": "EQUAL", "are": "EQUAL",
}
FIELD_MAP = {
    "direction": "DIRECTIONS", "directions": "DIRECTIONS",
    "ingredient": "INGREDIENTS", "ingredients": "INGREDIENTS",
    "title": "TITLE", "titles": "TITLE", "name": "NAME", "names": "NAME",
    "description": "DESCRIPTION", "descriptions": "DESCRIPTION",
    "note": "NOTES", "notes": "NOTES", "category": "CATEGORY", "categories": "CATEGORY",
    "date": "DATE", "dates": "DATE", "time": "TIME", "times": "TIME",
    "duration": "DURATION", "durations": "DURATION", "distance": "DISTANCE", "distances": "DISTANCE",
    "amount": "AMOUNT", "amounts": "AMOUNT", "location": "LOCATION", "locations": "LOCATION",
    "filename": "FILENAME", "filenames": "FILENAME", "content": "CONTENT", "contents": "CONTENT",
}
PURPOSE_SCOPE = {"prepare": "PREPARATION_DURATION", "cook": "PREPARATION_DURATION", "complete": "COMPLETION_DURATION"}
APP_SCOPE_RE = re.compile(
    rf"\b(?:from|in|into|to|using|via)\s+(?:the\s+)?(?P<app>{WORD}(?:\s+{WORD}){{0,3}})\s+(?:app|application)\b",
    re.IGNORECASE | re.UNICODE,
)
REL_HEAD_RE = re.compile(
    r"\b(?P<relative>that|which)\s+(?:(?P<negation>do\s+not|does\s+not|don't|doesn't|not)\s+)?"
    r"(?P<predicate>use|uses|contain|contains|include|includes|have|has|take|takes|last|lasts|cost|costs|match|matches|equal|equals)\b",
    re.IGNORECASE | re.UNICODE,
)
ATTRIBUTE_HEAD_RE = re.compile(
    rf"\b(?:with|whose)\s+(?:the\s+)?(?P<field>{'|'.join(sorted(FIELD_MAP, key=len, reverse=True))})\s+"
    r"(?P<predicate>is|are|equal|equals|contain|contains|include|includes|have|has)\b",
    re.IGNORECASE | re.UNICODE,
)
SCALAR_TAIL_RE = re.compile(
    r"^\s*(?P<value>\d+(?:\.\d+)?(?:\s*(?:h|hr|hrs|hour|hours|min|mins|minute|minutes|km|m|meter|meters|dollar|dollars))?)"
    r"(?:\s+to\s+(?P<purpose>prepare|cook|complete))?\b",
    re.IGNORECASE | re.UNICODE,
)
GENERIC_VALUE_TOKENS = {
    "a", "an", "the", "any", "all", "some", "each", "every", "this", "that", "these", "those",
    "it", "them", "they", "one", "ones", "app", "application", "item", "items", "entry", "entries",
    "record", "records", "file", "files", "note", "notes", "recipe", "recipes", "expense", "expenses",
    "song", "songs", "activity", "activities", "event", "events", "playlist", "playlists", "transaction", "transactions",
    *PREDICATE_MAP.keys(), "in", "on", "at", "from", "to", "into", "within", "inside", "under", "using", "via",
    *FIELD_MAP.keys(),
}
_TAIL_STOP = {"and", "or", "but", "then", "from", "to", "into", "using", "via"}


@dataclass
class AnchorEvidence:
    event_kind: str
    source_step: int
    weight: float


@dataclass
class GoalAnchor:
    anchor_id: str
    role: str
    literal: str
    normalized: str
    source_kind: str
    source_offset: int
    specificity_weight: int
    predicate: str | None = None
    constraint_value: str = ""
    constraint_scope: str | None = None
    negated: bool = False
    persistent_open: bool = False
    confidence: float = 0.0
    status: str = "OPEN"
    last_evidence_step: int | None = None
    evidence_events: list[AnchorEvidence] = field(default_factory=list)
    contradiction_count: int = 0
    ever_supported: bool = False


@dataclass(frozen=True)
class _AnchorCandidate:
    priority: int
    offset: int
    end: int
    source_kind: str
    literal: str
    role: str
    predicate: str | None = None
    constraint_value: str = ""
    scope: str | None = None
    negated: bool = False


def _tokens_with_spans(text: str, start: int, max_tokens: int = 7) -> list[tuple[str, int, int]]:
    result: list[tuple[str, int, int]] = []
    for match in re.finditer(WORD, text[start:], re.UNICODE):
        absolute_start, absolute_end = start + match.start(), start + match.end()
        gap = text[start if not result else result[-1][2]:absolute_start]
        if re.search(r"[,.;:!?()]", gap):
            break
        token = match.group(0)
        if token.casefold() in _TAIL_STOP:
            break
        result.append((token, absolute_start, absolute_end))
        if len(result) >= max_tokens:
            break
    return result


def _valid_constraint_value(value: str, span: tuple[int, int], app_spans: list[tuple[int, int]]) -> bool:
    tokens = re.findall(WORD, value, re.UNICODE)
    normalized = _anchor_norm(value)
    return bool(
        1 <= len(tokens) <= 6
        and 2 <= len(normalized) <= 48
        and not any(max(span[0], left) < min(span[1], right) for left, right in app_spans)
        and all(token.casefold() not in {"app", "application"} for token in tokens)
        and tokens[0].casefold() not in {"in", "on", "at", "from", "to", "into", "within", "inside", "under", "using", "via"}
        and tokens[-1].casefold() not in {"in", "on", "at", "from", "to", "into", "within", "inside", "under", "using", "via"}
        and any(token.casefold() not in GENERIC_VALUE_TOKENS for token in tokens)
    )


def extract_goal_anchors(goal: str, max_anchors: int = 8) -> list[GoalAnchor]:
    """Frozen deterministic parser; intentionally has no bare-app regex."""
    text = unicodedata.normalize("NFKC", str(goal))
    app_spans = [match.span("app") for match in APP_SCOPE_RE.finditer(text)]
    candidates: list[_AnchorCandidate] = []

    for head in REL_HEAD_RE.finditer(text):
        predicate = PREDICATE_MAP[head.group("predicate").casefold()]
        tail_start = head.end()
        if predicate in {"TAKE", "LAST", "COST"}:
            scalar = SCALAR_TAIL_RE.match(text[tail_start:])
            if scalar:
                start, end = tail_start + scalar.start("value"), tail_start + scalar.end("value")
                value = scalar.group("value")
                scope = PURPOSE_SCOPE.get((scalar.group("purpose") or "").casefold())
                if _valid_constraint_value(value, (start, end), app_spans):
                    candidates.append(_AnchorCandidate(5, head.start(), tail_start + scalar.end(), "relational_constraint", text[head.start():tail_start + scalar.end()], "CONSTRAINT", predicate, value, scope, bool(head.group("negation"))))
        else:
            tokens = _tokens_with_spans(text, tail_start)
            scope = None
            value_tokens = tokens
            for index, (token, start, _) in enumerate(tokens):
                if token.casefold() in {"in", "within", "inside", "under", "on"}:
                    field_index = index + 1
                    if field_index < len(tokens) and tokens[field_index][0].casefold() == "the":
                        field_index += 1
                    if field_index < len(tokens) and tokens[field_index][0].casefold() in FIELD_MAP:
                        scope = FIELD_MAP[tokens[field_index][0].casefold()]
                        value_tokens = tokens[:index]
                    break
            if value_tokens and len(value_tokens) <= 6:
                start, end = value_tokens[0][1], value_tokens[-1][2]
                value = text[start:end]
                if _valid_constraint_value(value, (start, end), app_spans):
                    candidates.append(_AnchorCandidate(5, head.start(), tokens[-1][2] if tokens else end, "relational_constraint", text[head.start():(tokens[-1][2] if tokens else end)], "CONSTRAINT", predicate, value, scope, bool(head.group("negation"))))

    for head in ATTRIBUTE_HEAD_RE.finditer(text):
        tokens = _tokens_with_spans(text, head.end())
        if tokens and len(tokens) <= 6:
            start, end = tokens[0][1], tokens[-1][2]
            value = text[start:end]
            if _valid_constraint_value(value, (start, end), app_spans):
                candidates.append(_AnchorCandidate(5, head.start(), end, "attribute_constraint", text[head.start():end], "CONSTRAINT", PREDICATE_MAP[head.group("predicate").casefold()], value, FIELD_MAP[head.group("field").casefold()], False))

    quote_patterns = (r'"([^"\n]{2,64})"', r"(?<!\w)'([^'\n]{2,64})'(?!\w)", r'`([^`\n]{2,64})`', r'“([^”\n]{2,64})”', r'‘([^’\n]{2,64})’')
    for pattern in quote_patterns:
        for match in re.finditer(pattern, text):
            candidates.append(_AnchorCandidate(4, match.start(1), match.end(1), "quoted", match.group(1), "ITEM"))
    if ":" in text:
        payload_start = text.rfind(":") + 1
        payload = re.split(r"[.!?]", text[payload_start:], maxsplit=1)[0]
        parts = [(item.group(0).strip(), payload_start + item.start()) for item in re.finditer(r"[^,;\n]+", payload) if item.group(0).strip()]
        if len(parts) >= 2:
            for literal, offset in parts:
                if 2 <= len(literal) <= 64:
                    candidates.append(_AnchorCandidate(3, offset, offset + len(literal), "colon_list", literal, "ITEM"))
    marker = re.compile(r"\b(?:following|these|named|called|titled|containing)\b\s*:?[ ]*([^.!?]+)", re.I)
    for match in marker.finditer(text):
        parts = [item.strip() for item in re.split(r"[,;\n]|\band\b", match.group(1), flags=re.I) if item.strip()]
        if len(parts) >= 2:
            cursor = match.start(1)
            for literal in parts:
                offset = text.find(literal, cursor)
                candidates.append(_AnchorCandidate(3, offset, offset + len(literal), "marker_list", literal, "ITEM"))
                cursor = offset + len(literal)
    numeric = re.compile(r"\b(?:\d{1,4}(?:[-/:.]\d{1,4})+|\d+(?:\.\d+)?(?:\s*(?:am|pm|km|mins?|minutes?|h|hrs?|hours?))?)\b", re.I)
    for match in numeric.finditer(text):
        candidates.append(_AnchorCandidate(2, match.start(), match.end(), "numeric_or_time", match.group(0), "VALUE"))
    temporal = "today|tomorrow|yesterday|this week|last week|monday|tuesday|wednesday|thursday|friday|saturday|sunday|january|february|march|april|may|june|july|august|september|october|november|december"
    for match in re.finditer(rf"\b(?:{temporal})\b", text, re.I):
        candidates.append(_AnchorCandidate(2, match.start(), match.end(), "temporal", match.group(0), "VALUE"))

    candidates.sort(key=lambda item: (-item.priority, item.offset, -(item.end - item.offset), _anchor_norm(item.literal)))
    selected: list[_AnchorCandidate] = []
    semantic_keys: set[str] = set()
    for candidate in candidates:
        value = candidate.constraint_value if candidate.role == "CONSTRAINT" else candidate.literal
        normalized = _anchor_norm(value)
        key = f"constraint|{candidate.predicate}|{normalized}|{candidate.scope}|{candidate.negated}" if candidate.role == "CONSTRAINT" else f"simple|{normalized}"
        if len(normalized) < 2 or key in semantic_keys:
            continue
        suppressed = False
        for prior in selected:
            overlap = max(0, min(candidate.end, prior.end) - max(candidate.offset, prior.offset))
            ratio = overlap / max(1, min(candidate.end - candidate.offset, prior.end - prior.offset))
            if ratio >= .8 or (prior.role == "CONSTRAINT" and prior.offset <= candidate.offset and prior.end >= candidate.end):
                suppressed = True
                break
        if suppressed:
            continue
        semantic_keys.add(key)
        selected.append(candidate)
        if len(selected) >= min(8, max_anchors):
            break
    anchors: list[GoalAnchor] = []
    for candidate in selected:
        value = candidate.constraint_value if candidate.role == "CONSTRAINT" else candidate.literal
        normalized = _anchor_norm(value)[:64]
        semantic = [candidate.role, candidate.predicate, normalized, candidate.scope, candidate.negated]
        anchors.append(GoalAnchor(
            anchor_id=f"a11a_{_json_sha(semantic)[:12]}", role=candidate.role,
            literal=_compact(candidate.literal, 64), normalized=normalized,
            source_kind=candidate.source_kind, source_offset=candidate.offset,
            specificity_weight=candidate.priority, predicate=candidate.predicate,
            constraint_value=_compact(candidate.constraint_value, 48), constraint_scope=candidate.scope,
            negated=candidate.negated, persistent_open=candidate.role == "CONSTRAINT",
        ))
    return anchors


def target_anchor_mask(summary: str, action: dict[str, Any], anchors: list[GoalAnchor]) -> int:
    summary_norm = _anchor_norm(summary)
    typed_norm = _anchor_norm(action.get("text") or "") if action.get("type") == "type_text" else ""
    mask = 0
    for index, anchor in enumerate(anchors):
        pattern = rf"(?<!\w){re.escape(anchor.normalized)}(?!\w)"
        if re.search(pattern, summary_norm) or (typed_norm and re.search(pattern, typed_norm)):
            mask |= 1 << index
    return mask


@dataclass
class RouteHop:
    source_step: int
    branch_family_digest: str
    intent_class: str
    target_anchor_mask: int
    source_descriptor_hash: str
    destination_descriptor_hash: str
    immediate_outcome: str
    visible_work: bool
    goal_coupled: bool


@dataclass
class BranchRecord:
    branch_id: str
    branch_key: str
    canonical_family: tuple[Any, ...]
    intent_class: str
    target_anchor_mask: int
    label: str
    latest_intent_excerpt: str
    first_step: int
    last_step: int
    attempt_count: int = 0
    raw_no_progress_count: int = 0
    raw_local_change_count: int = 0
    confirmed_adverse_return_count: int = 0
    benign_return_count: int = 0
    raw_durable_count: int = 0
    failure_confidence: float = 0.0
    escape_confidence: float = 0.0
    canonical_action_sha256s: list[str] = field(default_factory=list)


@dataclass
class FrontierRecord:
    frontier_id: str
    phase_id: int
    item_open_mask: int
    constraint_mask: int
    visual_exemplars: list[VisualDescriptor]
    first_step: int
    last_visit_step: int
    recent_visit_steps: list[int]
    visit_count: int
    branches: dict[str, BranchRecord]
    confirmed_return_count: int = 0
    benign_return_count: int = 0
    durable_departure_count: int = 0
    anchor_confidence_at_first_visit: tuple[float, ...] = ()
    read_count_in_phase: int = 0


@dataclass
class AttemptReceipt:
    attempt_id: str
    source_step: int
    resolve_step: int | None
    frontier_id: str
    branch_id: str
    branch_key: str
    source_exact_sha256: str
    destination_exact_sha256: str
    phase_id: int
    item_open_mask: int
    constraint_mask: int
    target_anchor_mask: int
    intent_class: str
    immediate_outcome: str
    resolved_outcome: str
    route_length: int | None
    anchor_gain: float
    residual_work_credit: float
    touched_anchor_ids: list[str]
    canonical_action_sha256: str
    source_response_sha256: str


@dataclass
class PendingRoute:
    attempt_id: str
    source_step: int
    source_frontier_id: str
    entry_branch_id: str
    entry_branch_key: str
    entry_branch_label: str
    entry_intent: str
    entry_attempt_count_before: int
    entry_bad_confidence: float
    phase_id: int
    item_open_mask: int
    constraint_mask: int
    source_descriptor: VisualDescriptor
    base_anchor_confidences: tuple[float, ...]
    entry_target_mask: int
    base_targeted_mask: int
    route_hops: list[RouteHop] = field(default_factory=list)
    max_anchor_gain: float = 0.0
    phase_masks_unchanged: bool = True
    route_target_mask: int = 0


@dataclass
class LateRouteWatch:
    route: PendingRoute
    durable_step: int
    expires_step: int


@dataclass
class ClosedRouteRecord:
    route_id: str
    source_frontier_id: str
    entry_branch_id: str
    entry_branch_key: str
    phase_id: int
    item_open_mask: int
    constraint_mask: int
    start_step: int
    return_step: int
    route_length: int
    route_length_bucket: str
    return_branch_family_digest: str
    route_core_signature: str
    route_full_signature: str
    anchor_gain: float
    goal_coupled: bool
    visible_work: bool
    target_progress: bool
    entry_novel: bool
    route_core_novel: bool
    novelty_workflow_credit: float
    residual_work_credit: float
    classification: str
    confirmation_step: int | None
    support_receipt_ids: list[str]
    source_descriptor: VisualDescriptor
    confirmation_path: str = ""


@dataclass
class PostReturnWatch:
    route_id: str
    return_step: int
    source_frontier_id: str
    source_descriptor: VisualDescriptor
    entry_branch_key: str
    phase_id: int
    item_open_mask: int
    constraint_mask: int
    base_anchor_confidences: tuple[float, ...]
    candidate_attempt_ids: list[str] = field(default_factory=list)
    expires_step: int = 0


@dataclass
class EscapeWatch:
    source_step: int
    source_frontier_id: str
    anchor_id: str
    remaining_open_mask: int
    source_descriptor: VisualDescriptor
    base_confidences: tuple[float, ...]
    offscreen_count: int = 0


@dataclass
class CommitPhaseWatch:
    source_step: int
    source_descriptor: VisualDescriptor
    left_source: bool = False


@dataclass
class TypedOccurrence:
    source_step: int
    phase_id: int
    item_open_mask: int
    constraint_mask: int
    frontier_id: str
    source_descriptor: VisualDescriptor
    attempt_id: str
    branch_id: str
    base_confidences: tuple[float, ...]
    outcome: str
    left_source: bool = False
    reentered_source: bool = False


@dataclass
class TypedValueRecord:
    value_sha256: str
    normalized_length: int
    occurrences: list[TypedOccurrence]


@dataclass
class TriggerCandidate:
    trigger_id: str
    kind: str
    state: str
    created_step: int
    maturity_step: int
    expires_step: int
    phase_id: int
    item_open_mask: int
    constraint_mask: int
    query_frontier_id: str
    expected_descriptor: VisualDescriptor
    support_count: int
    support_receipt_ids: list[str]
    evidence_strength: float
    contraction_confidence: float
    anchor_gain: float
    workflow_credit: float
    evidence_signature: str
    evidence_payload: dict[str, Any]
    baseline_anchor_confidences: tuple[float, ...] = ()
    delivered: bool = False


_SIMPLE_WEIGHTS = {
    "ACTION_MENTION": .20, "TYPE_EXACT": .25, "COMMIT_INTENT": .20,
    "MATERIAL_VISIBLE_CHANGE": .10, "DURABLE_ROUTE_DEPARTURE": .15,
    "INDEPENDENT_SECOND_SUPPORT": .15, "NO_PROGRESS_COMMIT": -.20,
    "CONFIRMED_ROUTE_RETURN": -.25, "REVERSAL_OR_FAILURE_PROSE": -.45,
    "LATER_REOPEN_ATTEMPT": -.30,
}
_CONSTRAINT_WEIGHTS = {
    "CONSTRAINT_VALUE_MENTION": .20, "CONSTRAINT_TYPE_EXACT": .25,
    "PREDICATE_AND_VALUE_MENTION": .20, "CONSTRAINT_VISIBLE_CHANGE": .10,
    "CONSTRAINT_DURABLE_ROUTE": .10, "INDEPENDENT_SECOND_SUPPORT": .15,
    "NO_PROGRESS_CONSTRAINT_ACTION": -.20, "CONFIRMED_CONSTRAINT_ROUTE_RETURN": -.25,
    "REVERSAL_OR_FAILURE_PROSE": -.45,
}
_FAILURE_PROSE_RE = re.compile(r"\b(?:cancel|undo|failed|failure|error|invalid|not|couldn['’]?t|cannot)\b", re.I)
_COMMIT_RE = re.compile(r"\b(?:delete|remove|add|create|save|send|share|submit|confirm|merge|copy|mark|export)\b", re.I)


class ConfirmedRouteContractionECOBFMemory:
    mechanism_id = MECHANISM_ID

    def __init__(
        self, *, max_anchors: int = 8, max_anchor_events: int = 6,
        max_frontiers: int = 16, max_visual_exemplars: int = 3,
        max_branches_per_frontier: int = 5, max_attempt_receipts: int = 32,
        max_pending_routes: int = 4, max_closed_routes: int = 12,
        max_post_return_watches: int = 4, max_late_route_watches: int = 4,
        max_escape_watches: int = 2, max_typed_value_keys: int = 12,
        max_trigger_candidates: int = 8, max_delivered_signatures: int = 12,
        max_nonempty_reads: int = 5, max_reads_per_phase: int = 2,
        read_cooldown_steps: int = 4, max_chars: int = 420,
        max_utf8_bytes: int = 720, retrieval_score_threshold: float = .70,
        experiment_id: str = EXPERIMENT_ID,
    ) -> None:
        self.experiment_id = str(experiment_id)
        self.max_anchors = min(8, max(1, int(max_anchors)))
        self.max_anchor_events = min(6, max(1, int(max_anchor_events)))
        self.max_frontiers = min(16, max(1, int(max_frontiers)))
        self.max_visual_exemplars = min(3, max(1, int(max_visual_exemplars)))
        self.max_branches_per_frontier = min(5, max(1, int(max_branches_per_frontier)))
        self.max_attempt_receipts = min(32, max(1, int(max_attempt_receipts)))
        self.max_pending_routes = min(4, max(1, int(max_pending_routes)))
        self.max_closed_routes = min(12, max(1, int(max_closed_routes)))
        self.max_post_return_watches = min(4, max(1, int(max_post_return_watches)))
        self.max_late_route_watches = min(4, max(1, int(max_late_route_watches)))
        self.max_escape_watches = min(2, max(1, int(max_escape_watches)))
        self.max_typed_value_keys = min(12, max(1, int(max_typed_value_keys)))
        self.max_trigger_candidates = min(8, max(1, int(max_trigger_candidates)))
        self.max_delivered_signatures = min(12, max(1, int(max_delivered_signatures)))
        self.max_nonempty_reads = min(5, max(1, int(max_nonempty_reads)))
        self.max_reads_per_phase = min(2, max(1, int(max_reads_per_phase)))
        self.read_cooldown_steps = max(4, int(read_cooldown_steps))
        self.max_chars = min(420, max(256, int(max_chars)))
        self.max_utf8_bytes = min(720, max(512, int(max_utf8_bytes)))
        if float(retrieval_score_threshold) != .70:
            raise A11IntegrityError("A11 retrieval threshold is frozen at 0.70")
        self.retrieval_score_threshold = .70

        self.goal_sha256 = ""
        self.operation_class = "OTHER"
        self.anchors: list[GoalAnchor] = []
        self.phase_id = 0
        self.phase_targeted_mask = 0
        self.frontiers: dict[str, FrontierRecord] = {}
        self.attempt_receipts: list[AttemptReceipt] = []
        self.pending_routes: list[PendingRoute] = []
        self.late_route_watches: list[LateRouteWatch] = []
        self.closed_routes: list[ClosedRouteRecord] = []
        self.post_return_watches: list[PostReturnWatch] = []
        self.escape_watches: list[EscapeWatch] = []
        self.commit_phase_watch: CommitPhaseWatch | None = None
        self.typed_value_records: dict[str, TypedValueRecord] = {}
        self.trigger_candidates: list[TriggerCandidate] = []
        self.delivered_signatures: list[str] = []
        self.screen_trace: list[str] = []
        self.read_events: list[dict[str, Any]] = []
        self.phase_switch_events: list[dict[str, Any]] = []
        self.last_observed_step = -1
        self.last_nonempty_read_step: int | None = None
        self.read_count = self.nonempty_read_count = 0
        self.phase_nonempty_read_count = 0
        self.write_attempt_count = self.write_success_count = 0
        self.frontier_merge_count = self.frontier_eviction_count = 0
        self.branch_eviction_count = self.route_eviction_count = 0
        self.trigger_eviction_count = self.duplicate_suppressed_count = 0
        self.phase_switch_count = self.expired_trigger_count = 0
        self.invalidated_trigger_count = 0
        self.max_observed_frontiers = self.max_observed_branches = 0
        self.max_observed_receipts = self.max_rendered_chars = 0
        self.max_rendered_utf8_bytes = 0
        self.created_counts_by_kind: dict[str, int] = {}
        self.delivered_counts_by_kind: dict[str, int] = {}
        self.raw_outcome_counts: dict[str, int] = {}
        self.route_classification_counts: dict[str, int] = {}
        self.route_confirmation_counts = {"recurrence": 0, "post_return": 0}
        self._descriptor_cache: list[tuple[str, VisualDescriptor]] = []
        self._read_baselines: dict[str, dict[str, Any]] = {}
        self._recent_clear_steps: list[int] = []

    def _describe(self, pixels: np.ndarray) -> VisualDescriptor:
        rgb = _visible_rgb({"pixels": pixels})
        digest = sha256(rgb.tobytes()).hexdigest()
        for key, value in reversed(self._descriptor_cache):
            if key == digest:
                return value
        value = describe_visual_state(rgb)
        self._descriptor_cache.append((digest, value))
        self._descriptor_cache = self._descriptor_cache[-4:]
        return value

    def _initialize_goal(self, goal: str) -> None:
        digest = sha256(str(goal).encode("utf-8")).hexdigest()
        if not self.goal_sha256:
            self.goal_sha256 = digest
            self.operation_class = classify_operation(goal)
            self.anchors = extract_goal_anchors(goal, self.max_anchors)
        elif digest != self.goal_sha256:
            raise A11IntegrityError("goal changed within episode")

    def item_open_mask(self) -> int:
        return sum(1 << index for index, anchor in enumerate(self.anchors) if anchor.role != "CONSTRAINT" and anchor.status != "LOCALLY_SUPPORTED")

    def constraint_mask(self) -> int:
        return sum(1 << index for index, anchor in enumerate(self.anchors) if anchor.role == "CONSTRAINT")

    @staticmethod
    def _event_decay(event: AnchorEvidence, step: int) -> float:
        if event.event_kind in {"DURABLE_ROUTE_DEPARTURE", "CONSTRAINT_DURABLE_ROUTE", "INDEPENDENT_SECOND_SUPPORT"}:
            lam = .995
        elif event.weight < 0:
            lam = .99
        else:
            lam = .97
        return event.weight * lam ** max(0, (step - event.source_step) // 6)

    def _add_anchor_event(self, anchor: GoalAnchor, kind: str, step: int) -> AnchorEvidence | None:
        weights = _CONSTRAINT_WEIGHTS if anchor.role == "CONSTRAINT" else _SIMPLE_WEIGHTS
        if kind not in weights or any(item.event_kind == kind and item.source_step == step for item in anchor.evidence_events):
            return None
        event = AnchorEvidence(kind, step, weights[kind])
        anchor.evidence_events.append(event)
        anchor.last_evidence_step = step
        if event.weight <= -.30 and anchor.ever_supported:
            anchor.contradiction_count = _sat(anchor.contradiction_count + 1)
        while len(anchor.evidence_events) > self.max_anchor_events:
            latest_negative = max((item.source_step for item in anchor.evidence_events if item.weight < 0), default=-1)
            eligible = [item for item in anchor.evidence_events if not (item.weight < 0 and item.source_step == latest_negative)]
            victim = min(eligible or anchor.evidence_events, key=lambda item: (abs(self._event_decay(item, step)), item.source_step, item.event_kind))
            anchor.evidence_events.remove(victim)
        return event

    def _refresh_anchors(self, step: int) -> None:
        for anchor in self.anchors:
            anchor.confidence = min(1.0, max(0.0, sum(self._event_decay(item, step) for item in anchor.evidence_events)))
            kinds = {item.event_kind for item in anchor.evidence_events}
            if anchor.role == "CONSTRAINT":
                hard = bool(kinds & {"CONSTRAINT_VALUE_MENTION", "CONSTRAINT_TYPE_EXACT"}) and bool(kinds & {"PREDICATE_AND_VALUE_MENTION", "COMMIT_INTENT"}) and bool(kinds & {"CONSTRAINT_VISIBLE_CHANGE", "CONSTRAINT_DURABLE_ROUTE"})
                if anchor.ever_supported and anchor.contradiction_count:
                    anchor.status = "REOPENED"
                elif anchor.confidence >= .80 and hard:
                    anchor.status, anchor.ever_supported, anchor.contradiction_count = "LOCALLY_APPLIED", True, 0
                elif anchor.confidence >= .35:
                    anchor.status = "ENGAGED"
                else:
                    anchor.status = "OPEN"
            else:
                material_steps = {item.source_step for item in anchor.evidence_events if item.event_kind in {"MATERIAL_VISIBLE_CHANGE", "INDEPENDENT_SECOND_SUPPORT"}}
                hard = bool(kinds & {"ACTION_MENTION", "TYPE_EXACT"}) and "COMMIT_INTENT" in kinds and ("DURABLE_ROUTE_DEPARTURE" in kinds or len(material_steps) >= 2)
                if anchor.ever_supported and anchor.contradiction_count:
                    anchor.status = "REOPENED"
                elif anchor.confidence >= .80 and hard:
                    anchor.status, anchor.ever_supported, anchor.contradiction_count = "LOCALLY_SUPPORTED", True, 0
                elif anchor.confidence >= .60:
                    anchor.status = "PROVISIONAL"
                elif anchor.confidence >= .35:
                    anchor.status = "TOUCHED"
                else:
                    anchor.status = "OPEN"

    def _match_frontier(self, descriptor: VisualDescriptor, phase: int, item_mask: int, constraint_mask: int, *, merge: bool = False) -> tuple[FrontierRecord | None, float]:
        matches: list[tuple[float, int, str, FrontierRecord]] = []
        for frontier in self.frontiers.values():
            if (frontier.phase_id, frontier.item_open_mask, frontier.constraint_mask) != (phase, item_mask, constraint_mask):
                continue
            exact = any(item.exact_sha256 == descriptor.exact_sha256 for item in frontier.visual_exemplars)
            distances = [visual_distance(item, descriptor)[2] for item in frontier.visual_exemplars]
            best = min(distances)
            allowed = exact or (best <= .035 if merge else any(visual_match(item, descriptor) for item in frontier.visual_exemplars))
            if allowed:
                matches.append((0.0 if exact else best, -frontier.last_visit_step, frontier.frontier_id, frontier))
        if not matches:
            return None, 1.0
        matches.sort(key=lambda item: item[:3])
        return matches[0][3], matches[0][0]

    def _frontier(self, descriptor: VisualDescriptor, phase: int, item_mask: int, constraint_mask: int, step: int) -> tuple[FrontierRecord, bool]:
        frontier, _ = self._match_frontier(descriptor, phase, item_mask, constraint_mask, merge=True)
        if frontier is not None:
            if all(visual_distance(item, descriptor)[2] > .02 for item in frontier.visual_exemplars):
                frontier.visual_exemplars.append(descriptor)
                frontier.visual_exemplars = frontier.visual_exemplars[-self.max_visual_exemplars:]
            self.frontier_merge_count += 1
            return frontier, False
        fid = f"a11f_{_json_sha([phase, item_mask, constraint_mask, descriptor.descriptor_sha256])[:16]}"
        frontier = FrontierRecord(fid, phase, item_mask, constraint_mask, [descriptor], step, step, [], 0, {}, anchor_confidence_at_first_visit=tuple(item.confidence for item in self.anchors))
        self.frontiers[fid] = frontier
        self._evict_frontiers(step, fid)
        return frontier, True

    @staticmethod
    def _register_visit(frontier: FrontierRecord, step: int) -> None:
        if not frontier.recent_visit_steps or frontier.recent_visit_steps[-1] != step:
            frontier.recent_visit_steps.append(step)
            frontier.recent_visit_steps = frontier.recent_visit_steps[-8:]
            frontier.visit_count = _sat(frontier.visit_count + 1)
        frontier.last_visit_step = max(frontier.last_visit_step, step)

    @staticmethod
    def _family_label(family: tuple[Any, ...]) -> str:
        if family[0] in {"tap", "long_press"}:
            horizontal = ("left", "middle", "right")[min(2, int(family[1]) // 4)]
            vertical = ("upper", "middle", "lower")[min(2, int(family[2]) // 8)]
            return f"{family[0]} {vertical}-{horizontal}"
        return str(family[0]).replace("type_text", "text") + (f"-{family[1]}" if family[0] == "swipe" else "")

    def _branch(self, frontier: FrontierRecord, family: tuple[Any, ...], intent: str, target_mask: int, summary: str, step: int) -> tuple[BranchRecord, bool]:
        key = _json_sha([family, intent, target_mask])
        if key in frontier.branches:
            return frontier.branches[key], False
        branch = BranchRecord(f"a11b_{_json_sha([frontier.frontier_id, key])[:16]}", key, family, intent, target_mask, _compact(self._family_label(family), 40), _compact(summary, 56), step, step)
        frontier.branches[key] = branch
        self._evict_branches(frontier, step)
        return branch, True

    def _branch_values(self, branch_id: str, step: int) -> tuple[float, float, float, float, float, float]:
        n = r = local = durable = 0.0
        for receipt in self.attempt_receipts:
            if receipt.branch_id != branch_id:
                continue
            event_step = receipt.resolve_step if receipt.resolve_step is not None else receipt.source_step
            decay = .85 ** max(0, (step - event_step) // 8)
            if receipt.resolved_outcome.startswith("NO_PROGRESS"):
                n += decay
            elif receipt.resolved_outcome == "CONFIRMED_ADVERSE_RETURN":
                r += 1.25 * decay
            elif receipt.resolved_outcome == "LATE_CONFIRMED_ADVERSE_RETURN":
                r += .75 * decay
            elif receipt.resolved_outcome == "LOCAL_VISIBLE_CHANGE":
                local += .5 * decay
            elif receipt.resolved_outcome == "DURABLE_DEPARTURE":
                durable += decay
        total = n + r + local + durable
        strength = 1 - math.exp(-.7 * total)
        bad = ((1 + n + r) / (2 + total)) * strength
        escape = ((1 + durable) / (2 + total)) * strength
        return n, r, local, durable, bad, escape

    def _refresh_branches(self, step: int) -> None:
        for frontier in self.frontiers.values():
            for branch in frontier.branches.values():
                _, _, _, _, branch.failure_confidence, branch.escape_confidence = self._branch_values(branch.branch_id, step)

    def _record_raw_outcome(self, branch: BranchRecord | None, outcome: str) -> None:
        self.raw_outcome_counts[outcome] = self.raw_outcome_counts.get(outcome, 0) + 1
        if branch is None:
            return
        if outcome.startswith("NO_PROGRESS"):
            branch.raw_no_progress_count = _sat(branch.raw_no_progress_count + 1)
        elif outcome == "LOCAL_VISIBLE_CHANGE":
            branch.raw_local_change_count = _sat(branch.raw_local_change_count + 1)
        elif outcome in {"CONFIRMED_ADVERSE_RETURN", "LATE_CONFIRMED_ADVERSE_RETURN"}:
            branch.confirmed_adverse_return_count = _sat(branch.confirmed_adverse_return_count + 1)
        elif outcome in {"RETURNED", "LATE_RETURN"}:
            branch.benign_return_count = _sat(branch.benign_return_count + 1)
        elif outcome == "DURABLE_DEPARTURE":
            branch.raw_durable_count = _sat(branch.raw_durable_count + 1)

    @staticmethod
    def _classify_outcome(before: VisualDescriptor, after: VisualDescriptor, before_pixels: np.ndarray, after_pixels: np.ndarray) -> tuple[str, float]:
        changed = changed_pixel_fraction(before_pixels, after_pixels)
        if before.exact_sha256 == after.exact_sha256:
            return "NO_PROGRESS_EXACT", changed
        if changed <= .001:
            return "NO_PROGRESS_NEGLIGIBLE", changed
        if visual_match(before, after):
            return "LOCAL_VISIBLE_CHANGE", changed
        return "DEPARTURE_PENDING", changed

    def _derive_anchor_events(self, step: int, summary: str, action: dict[str, Any], target_mask: int, intent: str, outcome: str) -> list[tuple[str, str]]:
        created: list[tuple[str, str]] = []
        summary_norm = _anchor_norm(summary)
        typed_norm = _anchor_norm(action.get("text") or "") if action.get("type") == "type_text" else ""
        for index, anchor in enumerate(self.anchors):
            if not target_mask & (1 << index):
                continue
            anchor_matches = list(re.finditer(rf"(?<!\w){re.escape(anchor.normalized)}(?!\w)", summary_norm))
            def near(pattern: re.Pattern[str]) -> bool:
                return any(min(abs(left.start() - right.end()), abs(right.start() - left.end())) <= 48 for left in anchor_matches for right in pattern.finditer(summary_norm))
            kinds: list[str] = []
            if anchor.role == "CONSTRAINT":
                if anchor_matches:
                    kinds.append("CONSTRAINT_VALUE_MENTION")
                if typed_norm and re.search(rf"(?<!\w){re.escape(anchor.normalized)}(?!\w)", typed_norm):
                    kinds.append("CONSTRAINT_TYPE_EXACT")
                aliases = [word for word, mapped in PREDICATE_MAP.items() if mapped == anchor.predicate]
                if anchor_matches and any(re.search(rf"\b{word}\b", summary_norm) for word in aliases):
                    kinds.append("PREDICATE_AND_VALUE_MENTION")
                if outcome == "LOCAL_VISIBLE_CHANGE":
                    kinds.append("CONSTRAINT_VISIBLE_CHANGE")
                if outcome.startswith("NO_PROGRESS"):
                    kinds.append("NO_PROGRESS_CONSTRAINT_ACTION")
            else:
                if anchor_matches:
                    kinds.append("ACTION_MENTION")
                if typed_norm and re.search(rf"(?<!\w){re.escape(anchor.normalized)}(?!\w)", typed_norm):
                    kinds.append("TYPE_EXACT")
                if intent == "COMMIT" and near(_COMMIT_RE):
                    kinds.append("COMMIT_INTENT")
                    if outcome.startswith("NO_PROGRESS"):
                        kinds.append("NO_PROGRESS_COMMIT")
                if outcome == "LOCAL_VISIBLE_CHANGE":
                    kinds.append("MATERIAL_VISIBLE_CHANGE")
                if anchor.status == "LOCALLY_SUPPORTED":
                    kinds.append("LATER_REOPEN_ATTEMPT")
            if anchor_matches and near(_FAILURE_PROSE_RE):
                kinds.append("REVERSAL_OR_FAILURE_PROSE")
            for kind in kinds:
                if self._add_anchor_event(anchor, kind, step):
                    created.append((anchor.anchor_id, kind))
            if len({item.source_step for item in anchor.evidence_events if item.weight > 0}) >= 2 and self._add_anchor_event(anchor, "INDEPENDENT_SECOND_SUPPORT", step):
                created.append((anchor.anchor_id, "INDEPENDENT_SECOND_SUPPORT"))
        return created

    def _receipt(self, attempt_id: str) -> AttemptReceipt | None:
        return next((item for item in self.attempt_receipts if item.attempt_id == attempt_id), None)

    def _branch_by_id(self, branch_id: str) -> BranchRecord | None:
        return next((branch for frontier in self.frontiers.values() for branch in frontier.branches.values() if branch.branch_id == branch_id), None)

    def _append_hop(self, pending: PendingRoute, hop: RouteHop) -> None:
        if not pending.route_hops or pending.route_hops[-1].source_step != hop.source_step:
            pending.route_hops.append(hop)
            pending.route_hops = pending.route_hops[-4:]
        pending.route_target_mask |= hop.target_anchor_mask

    @staticmethod
    def _length_bucket(length: int) -> str:
        return "ONE" if length == 1 else "TWO" if length == 2 else "THREE_FOUR"

    def _build_closed_route(self, pending: PendingRoute, step: int, return_family_digest: str) -> ClosedRouteRecord:
        route_mask = pending.route_target_mask
        target_progress = bool((route_mask & pending.item_open_mask) & ~pending.base_targeted_mask)
        goal_coupled = any(item.goal_coupled for item in pending.route_hops)
        visible_work = any(item.visible_work for item in pending.route_hops)
        entry_novel = pending.entry_attempt_count_before == 0
        length = step - pending.source_step
        core_payload = {
            "source_frontier_id": pending.source_frontier_id, "phase_id": pending.phase_id,
            "item_open_mask": pending.item_open_mask, "constraint_mask": pending.constraint_mask,
            "entry_branch_key": pending.entry_branch_key, "return_branch_family": return_family_digest,
            "route_length_bucket": self._length_bucket(length),
        }
        core = _json_sha(core_payload)
        core_novel = not any(item.route_core_signature == core and item.phase_id == pending.phase_id for item in self.closed_routes)
        novelty = .30 * entry_novel + .25 * core_novel + .20 * goal_coupled + .15 * visible_work + .10 * target_progress
        residual = .40 * goal_coupled + .35 * visible_work + .25 * target_progress
        gain = pending.max_anchor_gain
        if gain >= .10 or not pending.phase_masks_unchanged or target_progress or residual >= .35:
            classification = "WORKFLOW_ADVANCE"
        elif novelty >= .50 and pending.entry_bad_confidence < .55:
            classification = "NOVEL_EXPLORATION_RETURN"
        else:
            classification = "PROVISIONAL_ADVERSE_RETURN"
        full = _json_sha({**core_payload, "hops": [item.branch_family_digest for item in pending.route_hops]})
        route = ClosedRouteRecord(
            f"a11route_{core[:10]}_{step}", pending.source_frontier_id, pending.entry_branch_id,
            pending.entry_branch_key, pending.phase_id, pending.item_open_mask, pending.constraint_mask,
            pending.source_step, step, length, self._length_bucket(length), return_family_digest,
            core, full, gain, goal_coupled, visible_work, target_progress, entry_novel, core_novel,
            novelty, residual, classification, None, [pending.attempt_id], pending.source_descriptor,
        )
        self.route_classification_counts[classification] = self.route_classification_counts.get(classification, 0) + 1
        return route

    def _evict_closed_routes(self, step: int) -> None:
        while len(self.closed_routes) > self.max_closed_routes:
            watched = {item.route_id for item in self.post_return_watches}
            victim = min(self.closed_routes, key=lambda item: (2 * (item.confirmation_step is not None) + 1.5 * (item.route_id in watched) + math.exp(-max(0, step - item.return_step) / 8), item.return_step, item.route_id))
            self.closed_routes.remove(victim)
            self.route_eviction_count += 1

    def _confirm_routes(self, current: ClosedRouteRecord, step: int) -> list[tuple[list[ClosedRouteRecord], str, list[str]]]:
        confirmations: list[tuple[list[ClosedRouteRecord], str, list[str]]] = []
        prior = next((item for item in reversed(self.closed_routes[:-1]) if item.route_core_signature == current.route_core_signature and 0 < current.return_step - item.return_step <= 12 and item.phase_id == current.phase_id and item.item_open_mask == current.item_open_mask and item.constraint_mask == current.constraint_mask and item.anchor_gain < .10 and current.anchor_gain < .10 and item.residual_work_credit < .35 and current.residual_work_credit < .35 and not item.target_progress and not current.target_progress), None)
        if prior is not None:
            supports = list(dict.fromkeys(prior.support_receipt_ids + current.support_receipt_ids))[:3]
            confirmations.append(([prior, current], "route_recurrence", supports))
        return confirmations

    def _mark_confirmed(self, routes: list[ClosedRouteRecord], path: str, supports: list[str], step: int) -> None:
        for route in routes:
            route.classification = "CONFIRMED_ADVERSE_RETURN" if route.return_step - route.start_step <= 4 else "LATE_CONFIRMED_ADVERSE_RETURN"
            route.confirmation_step = step
            route.confirmation_path = path
            route.support_receipt_ids = list(dict.fromkeys(route.support_receipt_ids + supports))[:3]
            receipt = self._receipt(route.support_receipt_ids[0]) if route.support_receipt_ids else None
            if receipt and receipt.resolved_outcome not in {"CONFIRMED_ADVERSE_RETURN", "LATE_CONFIRMED_ADVERSE_RETURN"}:
                old = receipt.resolved_outcome
                receipt.resolved_outcome = route.classification
                branch = self._branch_by_id(receipt.branch_id)
                if branch and old in {"RETURNED", "LATE_RETURN"}:
                    branch.benign_return_count = _sat(branch.benign_return_count - 1)
                    self.raw_outcome_counts[old] = max(0, self.raw_outcome_counts.get(old, 0) - 1)
                self._record_raw_outcome(branch, route.classification)
        self.route_confirmation_counts["recurrence" if path == "route_recurrence" else "post_return"] += 1

    def _route_evidence(self, routes: list[ClosedRouteRecord], path: str, step: int) -> tuple[float, float, float]:
        core = routes[-1].route_core_signature
        k = sum(1 for item in self.closed_routes if item.route_core_signature == core and item.confirmation_step is not None)
        q = int(path == "post_return_reversion")
        bad = max((self._branch_values(item.entry_branch_id, step)[4] for item in routes), default=0.0)
        workflow = max((item.residual_work_credit for item in routes), default=0.0)
        evidence = min(1.0, max(0.0, .50 + .20 * min(2, max(0, k - 1)) + .20 * q + .15 * bad - .20 * workflow))
        contraction = min(1.0, .60 + .20 * int(k >= 2) + .20 * q)
        return evidence, contraction, workflow

    def _make_candidate(self, kind: str, step: int, frontier_id: str, descriptor: VisualDescriptor, support_ids: list[str], evidence: float, contraction: float, gain: float, workflow: float, payload: dict[str, Any], expiry: int | None = None) -> TriggerCandidate:
        bounded = {str(key)[:32]: (_compact(value, 56) if isinstance(value, str) else value) for key, value in list(payload.items())[:10]}
        signature = _json_sha({"kind": kind, "phase_id": self.phase_id, "item_open_mask": self.item_open_mask(), "constraint_mask": self.constraint_mask(), "frontier_id": frontier_id, "support_receipt_ids": sorted(support_ids), "evidence_revision": _json_sha(bounded)[:12]})
        return TriggerCandidate(
            f"a11t_{step}_{signature[:12]}", kind, "MATURE", step, step,
            step + (expiry if expiry is not None else (6 if kind == "PARTIAL_OBLIGATION_ESCAPE" else 8)),
            self.phase_id, self.item_open_mask(), self.constraint_mask(), frontier_id, descriptor,
            len(set(support_ids)), list(dict.fromkeys(support_ids))[:4], min(1.0, max(0.0, evidence)),
            min(1.0, max(0.0, contraction)), max(0.0, gain), min(1.0, max(0.0, workflow)),
            signature, bounded, tuple(item.confidence for item in self.anchors),
        )

    def _enqueue(self, candidate: TriggerCandidate) -> bool:
        if candidate.evidence_signature in self.delivered_signatures or any(item.evidence_signature == candidate.evidence_signature and item.state in {"MATURE", "DELIVERED"} for item in self.trigger_candidates):
            self.duplicate_suppressed_count += 1
            return False
        self.trigger_candidates.append(candidate)
        self.created_counts_by_kind[candidate.kind] = self.created_counts_by_kind.get(candidate.kind, 0) + 1
        self._evict_triggers(candidate.created_step)
        return True

    def _obligation_relevance(self) -> float:
        total = sum(item.specificity_weight for item in self.anchors)
        if not total:
            return 1.0
        open_weight = sum(item.specificity_weight for item in self.anchors if item.role != "CONSTRAINT" and item.status != "LOCALLY_SUPPORTED")
        constraint_weight = sum(item.specificity_weight for item in self.anchors if item.role == "CONSTRAINT")
        return min(1.0, (open_weight + .75 * constraint_weight) / total)

    def _score(self, candidate: TriggerCandidate, match_kind: str, step: int) -> tuple[float, dict[str, float]]:
        m = 1.0 if match_kind == "EXACT" else .85
        o = self._obligation_relevance()
        no_gain = 1 - min(1.0, candidate.anchor_gain / .15)
        fresh = math.exp(-max(0, step - candidate.maturity_step) / 8)
        score = m * (.32 * candidate.evidence_strength + .28 * candidate.contraction_confidence + .18 * o + .12 * no_gain + .10 * fresh) - .08 * candidate.workflow_credit
        return score, {"M": m, "E": candidate.evidence_strength, "C": candidate.contraction_confidence, "O": o, "G": no_gain, "F": fresh, "X": candidate.workflow_credit}

    @staticmethod
    def _safe_dynamic(text: str) -> str:
        # The Pro ban applies literally to the final block, including user literals.
        banned = ("completed", "success", "verified by evaluator", "must click", "do not click", "blocked", "forbidden", "terminate now", "the correct action is")
        result = text
        for term in banned:
            result = re.sub(re.escape(term), lambda match: match.group(0)[:1] + "·" + match.group(0)[2:], result, flags=re.I)
        return result

    def _render(self, candidate: TriggerCandidate) -> str:
        unresolved = [item for item in self.anchors if item.role != "CONSTRAINT" and item.status != "LOCALLY_SUPPORTED"]
        constraints = [item for item in self.anchors if item.role == "CONSTRAINT"]
        open_text = ", ".join(f'"{self._safe_dynamic(_compact(item.literal, 18))}"' for item in unresolved[:2]) or "task completion is not established"
        if len(unresolved) > 2:
            open_text += f" (+{len(unresolved)-2})"
        if constraints:
            item = constraints[0]
            scope = (item.constraint_scope or "unspecified").casefold().replace("_", " ")
            constraint_text = f'{(item.predicate or "match").casefold()} "{self._safe_dynamic(_compact(item.constraint_value, 24))}" in {scope}'
            if len(constraints) > 1:
                constraint_text += f" (+{len(constraints)-1})"
        else:
            constraint_text = "none"
        payload = candidate.evidence_payload
        evidence = {
            "PARTIAL_OBLIGATION_ESCAPE": f'"{payload.get("anchor", "an item")}" gained local support; another item stayed open after leaving',
            "BAD_BRANCH_REPEAT": f'{payload.get("branch", "this branch")} had no/negligible screen change {payload.get("count", 2)}x',
            "CONFIRMED_ROUTE_TRAP": "a closed route was confirmed by recurrence or a following bad branch without goal gain",
            "CONTRACTED_FRONTIER": f'{payload.get("visits", 4)} visits/8 actions; {payload.get("adverse", 3)} adverse receipts; branches repeated',
            "VALUE_REENTRY_AFTER_BAD_OUTCOME": "the same text was re-entered after a confirmed bad outcome",
        }[candidate.kind]
        evidence = self._safe_dynamic(_compact(evidence, 72))
        fixed_tail = "Confirmed by 2+ adverse observations after navigation credit. Reassess another action family or target; retry is allowed. Nothing is blocked or selected."
        rendered = f"A11 frontier; past visible evidence only, current screen wins.\nOpen: {_compact(open_text,40)}. Constraint: {_compact(constraint_text,44)}. Evidence: {evidence}.\n{fixed_tail}"
        if len(rendered) > self.max_chars or len(rendered.encode("utf-8")) > self.max_utf8_bytes:
            rendered = f"A11 frontier; past visible evidence only, current screen wins.\nOpen: {_compact(open_text,28)}. Constraint: {_compact(constraint_text,32)}. Evidence: {_compact(evidence,52)}.\n{fixed_tail}"
        if len(rendered) > self.max_chars or len(rendered.encode("utf-8")) > self.max_utf8_bytes:
            raise A11IntegrityError("A11 fixed renderer exceeded frozen budget")
        return rendered

    def _candidate_visual_match(self, candidate: TriggerCandidate, descriptor: VisualDescriptor) -> tuple[str, float]:
        if candidate.expected_descriptor.exact_sha256 == descriptor.exact_sha256:
            return "EXACT", 0.0
        dl, de, dv = visual_distance(candidate.expected_descriptor, descriptor)
        if dl <= .05 and de <= .10 and dv <= .045 and candidate.support_count >= 2:
            return "NEAR", dv
        return "NONE", dv

    def _invalidate_candidates(self, step: int) -> None:
        for candidate in self.trigger_candidates:
            if candidate.state != "MATURE":
                continue
            if step > candidate.expires_step:
                candidate.state = "EXPIRED"
                self.expired_trigger_count += 1
            elif (candidate.phase_id, candidate.item_open_mask, candidate.constraint_mask) != (self.phase_id, self.item_open_mask(), self.constraint_mask()):
                candidate.state = "INVALIDATED"
                self.invalidated_trigger_count += 1
            else:
                baseline = candidate.baseline_anchor_confidences
                current_gain = max(
                    (
                        anchor.confidence - baseline[index]
                        for index, anchor in enumerate(self.anchors)
                        if index < len(baseline)
                    ),
                    default=0.0,
                )
                frontier = self.frontiers.get(candidate.query_frontier_id)
                trusted_escape = bool(
                    frontier
                    and any(
                        branch.escape_confidence >= .55 and branch.raw_durable_count >= 1
                        for branch in frontier.branches.values()
                    )
                )
                if current_gain >= .15 or trusted_escape:
                    candidate.state = "INVALIDATED"
                    self.invalidated_trigger_count += 1

    def read(self, context: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
        context = context or {}
        step = self.read_count
        self.read_count += 1
        self._initialize_goal(str(context.get("goal") or ""))
        descriptor = self._describe(_visible_rgb(dict(context.get("before") or {})))
        self._refresh_anchors(step)
        self._refresh_branches(step)
        frontier, _ = self._frontier(descriptor, self.phase_id, self.item_open_mask(), self.constraint_mask(), step)
        self._register_visit(frontier, step)  # The sole decision-visit registration site.
        self.screen_trace.append(descriptor.descriptor_sha256)
        self.screen_trace = self.screen_trace[-17:]
        self._invalidate_candidates(step)
        reason = "no_eligible_candidate"
        if self.nonempty_read_count >= self.max_nonempty_reads:
            reason = "episode_read_cap"
        elif self.phase_nonempty_read_count >= self.max_reads_per_phase:
            reason = "phase_read_cap"
        elif self.last_nonempty_read_step is not None and step - self.last_nonempty_read_step < self.read_cooldown_steps:
            reason = "cooldown"
        else:
            ranked: list[tuple[Any, ...]] = []
            priority = {"PARTIAL_OBLIGATION_ESCAPE": 5, "CONFIRMED_ROUTE_TRAP": 4, "BAD_BRANCH_REPEAT": 3, "VALUE_REENTRY_AFTER_BAD_OUTCOME": 2, "CONTRACTED_FRONTIER": 1}
            for candidate in self.trigger_candidates:
                if candidate.state != "MATURE" or candidate.evidence_signature in self.delivered_signatures:
                    continue
                if (candidate.phase_id, candidate.item_open_mask, candidate.constraint_mask) != (self.phase_id, self.item_open_mask(), self.constraint_mask()):
                    continue
                if candidate.kind in {"CONFIRMED_ROUTE_TRAP", "CONTRACTED_FRONTIER"} and (candidate.support_count < 2 or candidate.workflow_credit >= .35 or candidate.contraction_confidence < .55):
                    continue
                match_kind, distance = self._candidate_visual_match(candidate, descriptor)
                if match_kind == "NONE":
                    continue
                score, components = self._score(candidate, match_kind, step)
                if score < self.retrieval_score_threshold:
                    continue
                ranked.append((-score, -priority[candidate.kind], 0 if match_kind == "EXACT" else 1, distance, -candidate.maturity_step, candidate.trigger_id, candidate, components, match_kind))
            if ranked:
                ranked.sort(key=lambda item: item[:6])
                candidate, components, match_kind = ranked[0][6], ranked[0][7], ranked[0][8]
                score = -ranked[0][0]
                rendered = self._render(candidate)
                candidate.state, candidate.delivered = "DELIVERED", True
                self.nonempty_read_count += 1
                self.phase_nonempty_read_count += 1
                self.last_nonempty_read_step = step
                self.delivered_signatures.append(candidate.evidence_signature)
                self.delivered_signatures = self.delivered_signatures[-self.max_delivered_signatures:]
                self.delivered_counts_by_kind[candidate.kind] = self.delivered_counts_by_kind.get(candidate.kind, 0) + 1
                event = {
                    "read_id": f"a11r_{step}_{candidate.evidence_signature[:8]}", "step": step,
                    "trigger_id": candidate.trigger_id, "trigger_kind": candidate.kind,
                    "candidate_state_before_read": "MATURE", "maturity_step": candidate.maturity_step,
                    "support_count": candidate.support_count, "support_receipt_ids": candidate.support_receipt_ids,
                    "frontier_id": candidate.query_frontier_id, "phase_id": self.phase_id,
                    "item_open_mask": self.item_open_mask(), "constraint_mask": self.constraint_mask(),
                    "visual_match_kind": match_kind, "visual_distance": ranked[0][3], "score": score,
                    "score_components": components, "workflow_credit": candidate.workflow_credit,
                    "contraction_confidence": candidate.contraction_confidence,
                    "evidence_signature": candidate.evidence_signature, "rendered_text": rendered,
                    "rendered_sha256": sha256(rendered.encode()).hexdigest(), "rendered_chars": len(rendered),
                    "rendered_utf8_bytes": len(rendered.encode()), "retrieved_anchor_ids": [item.anchor_id for item in self.anchors][:3],
                    "retrieved_constraint_ids": [item.anchor_id for item in self.anchors if item.role == "CONSTRAINT"][:2],
                    "retrieved_branch_ids": candidate.evidence_payload.get("branch_ids", []), "retrieved_route_ids": candidate.evidence_payload.get("route_ids", []),
                    "confirmation_path": candidate.evidence_payload.get("confirmation_path", ""),
                    "next_action_branch_id": None, "next_action_was_novel": None,
                    "escaped_frontier_within_3": None, "returned_within_4": None,
                    "anchor_confidence_delta_within_4": 0.0,
                    "constraint_confidence_delta_within_4": 0.0,
                }
                self.read_events.append(event)
                self.read_events = self.read_events[-5:]
                self._read_baselines[event["read_id"]] = {
                    "descriptor": candidate.expected_descriptor,
                    "anchor_confidences": tuple(item.confidence for item in self.anchors),
                    "escaped": False,
                    "returned": False,
                }
                retained_read_ids = {str(item["read_id"]) for item in self.read_events}
                self._read_baselines = {
                    key: value for key, value in self._read_baselines.items()
                    if key in retained_read_ids
                }
                self.max_rendered_chars = max(self.max_rendered_chars, len(rendered))
                self.max_rendered_utf8_bytes = max(self.max_rendered_utf8_bytes, len(rendered.encode()))
                return rendered, {"mechanism_id": self.mechanism_id, "nonempty": True, "reason": "selected", "step": step, "trigger_kind": candidate.kind, "selected_trigger_id": candidate.trigger_id, "score": score, "score_components": components, "rendered_chars": len(rendered), "rendered_utf8_bytes": len(rendered.encode()), "rendered_sha256": sha256(rendered.encode()).hexdigest(), "one_shot": True}
        return "", {"mechanism_id": self.mechanism_id, "nonempty": False, "reason": reason, "step": step, "candidate_count": 0, "rendered_chars": 0, "rendered_utf8_bytes": 0, "rendered_sha256": sha256(b"").hexdigest()}

    def _switch_phase(self, step: int, old_item: int, new_item: int) -> None:
        self.phase_id += 1
        self.phase_switch_count += 1
        self.phase_targeted_mask = 0
        self.phase_nonempty_read_count = 0
        # last_nonempty_read_step intentionally survives: cooldown is episode-global.
        self.phase_switch_events.append({"step": step, "old_item_open_mask": old_item, "new_item_open_mask": new_item, "phase_id": self.phase_id})
        self.phase_switch_events = self.phase_switch_events[-8:]
        for candidate in self.trigger_candidates:
            if candidate.state == "MATURE" and candidate.phase_id != self.phase_id:
                candidate.state = "INVALIDATED"
                self.invalidated_trigger_count += 1

    def _update_post_read_audit(
        self,
        *,
        step: int,
        branch: BranchRecord,
        branch_created: bool,
        after_descriptor: VisualDescriptor,
    ) -> None:
        """Update bounded, retrospective causal fields; never decision state."""
        for event in self.read_events:
            age = step - int(event["step"])
            if age < 0 or age > 4:
                continue
            baseline = self._read_baselines.get(str(event["read_id"]))
            if baseline is None:
                continue
            if event["next_action_branch_id"] is None:
                event["next_action_branch_id"] = branch.branch_id
                event["next_action_was_novel"] = bool(branch_created)
            matches = visual_match(baseline["descriptor"], after_descriptor)
            if age <= 3 and not matches and not baseline["escaped"]:
                baseline["escaped"] = True
                event["escaped_frontier_within_3"] = True
            elif age >= 3 and event["escaped_frontier_within_3"] is None:
                event["escaped_frontier_within_3"] = False
            if baseline["escaped"] and matches and not baseline["returned"]:
                baseline["returned"] = True
                event["returned_within_4"] = True
            elif age >= 4 and event["returned_within_4"] is None:
                event["returned_within_4"] = False
            previous = tuple(baseline["anchor_confidences"])
            item_delta = max(
                (
                    anchor.confidence - previous[index]
                    for index, anchor in enumerate(self.anchors)
                    if index < len(previous) and anchor.role != "CONSTRAINT"
                ),
                default=0.0,
            )
            constraint_delta = max(
                (
                    anchor.confidence - previous[index]
                    for index, anchor in enumerate(self.anchors)
                    if index < len(previous) and anchor.role == "CONSTRAINT"
                ),
                default=0.0,
            )
            event["anchor_confidence_delta_within_4"] = max(
                float(event["anchor_confidence_delta_within_4"]), item_delta
            )
            event["constraint_confidence_delta_within_4"] = max(
                float(event["constraint_confidence_delta_within_4"]), constraint_delta
            )

    def observe_step(self, **kwargs: Any) -> dict[str, Any]:
        self.write_attempt_count += 1
        step = int(kwargs["source_step"])
        if step != self.last_observed_step + 1:
            raise A11IntegrityError("non-monotonic source_step")
        before_pixels = _visible_rgb(dict(kwargs.get("before") or {}))
        after_pixels = _visible_rgb(dict(kwargs.get("after") or {}))
        before_desc, after_desc = self._describe(before_pixels), self._describe(after_pixels)
        action = dict(kwargs.get("canonical_action") or {})
        family = canonical_action_family(action)
        summary = _compact(kwargs.get("action_summary") or "", 256)
        intent = classify_intent(summary, action)
        if action.get("clear_text") or re.search(r"\b(?:clear|erase)\b.{0,32}\b(?:input|text|field|query|search)\b", _norm(summary)):
            self._recent_clear_steps.append(step)
            self._recent_clear_steps = self._recent_clear_steps[-12:]

        self._refresh_anchors(step)
        self._refresh_branches(step)
        old_item, old_constraint = self.item_open_mask(), self.constraint_mask()
        start_conf = tuple(item.confidence for item in self.anchors)
        source, source_created = self._frontier(before_desc, self.phase_id, old_item, old_constraint, step)
        # Observe only matches/creates; it never increments decision visits.
        target_mask = target_anchor_mask(summary, action, self.anchors)
        base_targeted_mask = self.phase_targeted_mask
        self.phase_targeted_mask |= target_mask & old_item
        branch, branch_created = self._branch(source, family, intent, target_mask, summary, step)
        attempt_before = branch.attempt_count
        branch.attempt_count = _sat(branch.attempt_count + 1)
        branch.last_step = step
        branch.latest_intent_excerpt = _compact(summary, 56)
        action_sha = _json_sha(action)
        branch.canonical_action_sha256s.append(action_sha)
        branch.canonical_action_sha256s = branch.canonical_action_sha256s[-3:]
        outcome, changed = self._classify_outcome(before_desc, after_desc, before_pixels, after_pixels)
        attempt_id = f"a11p_{step}_{source.frontier_id[-6:]}_{branch.branch_id[-6:]}"
        receipt = AttemptReceipt(attempt_id, step, None if outcome == "DEPARTURE_PENDING" else step, source.frontier_id, branch.branch_id, branch.branch_key, before_desc.exact_sha256, after_desc.exact_sha256, self.phase_id, old_item, old_constraint, target_mask, intent, outcome, outcome, None, 0.0, 0.0, [item.anchor_id for index, item in enumerate(self.anchors) if target_mask & (1 << index)][:3], action_sha, _compact(kwargs.get("source_response_sha256") or "", 64))
        self.attempt_receipts.append(receipt)
        self.attempt_receipts = self.attempt_receipts[-self.max_attempt_receipts:]
        if outcome != "DEPARTURE_PENDING":
            self._record_raw_outcome(branch, outcome)

        events = self._derive_anchor_events(step, summary, action, target_mask, intent, outcome)
        self._refresh_anchors(step)
        hop = RouteHop(step, _json_sha(family)[:16], intent, target_mask, before_desc.descriptor_sha256[:16], after_desc.descriptor_sha256[:16], outcome, intent in {"COMMIT", "INPUT_OR_SEARCH"} and changed > .001, bool(target_mask))
        for pending in self.pending_routes:
            self._append_hop(pending, hop)
            pending.max_anchor_gain = max(pending.max_anchor_gain, max((item.confidence - pending.base_anchor_confidences[index] for index, item in enumerate(self.anchors)), default=0.0))
            pending.phase_masks_unchanged = pending.phase_masks_unchanged and (pending.phase_id, pending.item_open_mask, pending.constraint_mask) == (self.phase_id, self.item_open_mask(), self.constraint_mask())
        if outcome == "DEPARTURE_PENDING":
            pending = PendingRoute(attempt_id, step, source.frontier_id, branch.branch_id, branch.branch_key, branch.label, intent, attempt_before, branch.failure_confidence, self.phase_id, old_item, old_constraint, before_desc, start_conf, target_mask, base_targeted_mask)
            self._append_hop(pending, hop)
            self.pending_routes.append(pending)
            self.pending_routes.sort(key=lambda item: (item.source_step, item.attempt_id))
            self.pending_routes = self.pending_routes[:self.max_pending_routes]

        closed_now: list[ClosedRouteRecord] = []
        resolutions: list[dict[str, Any]] = []
        retained: list[PendingRoute] = []
        return_digest = _json_sha(family)[:16]
        for pending in self.pending_routes:
            age = step - pending.source_step
            returned = visual_match(pending.source_descriptor, after_desc)
            pending_receipt = self._receipt(pending.attempt_id)
            if returned and 1 <= age <= 4:
                route = self._build_closed_route(pending, step, return_digest)
                self.closed_routes.append(route)
                closed_now.append(route)
                if pending_receipt:
                    pending_receipt.resolve_step, pending_receipt.resolved_outcome, pending_receipt.route_length = step, "RETURNED", age
                    pending_receipt.anchor_gain, pending_receipt.residual_work_credit = route.anchor_gain, route.residual_work_credit
                pending_branch = self._branch_by_id(pending.entry_branch_id)
                self._record_raw_outcome(pending_branch, "RETURNED")
                source_frontier = self.frontiers.get(pending.source_frontier_id)
                if source_frontier:
                    source_frontier.benign_return_count = _sat(source_frontier.benign_return_count + 1)
                if route.classification == "PROVISIONAL_ADVERSE_RETURN":
                    self.post_return_watches.append(PostReturnWatch(route.route_id, step, route.source_frontier_id, route.source_descriptor, route.entry_branch_key, route.phase_id, route.item_open_mask, route.constraint_mask, tuple(item.confidence for item in self.anchors), expires_step=step + 6))
                    self.post_return_watches = self.post_return_watches[-self.max_post_return_watches:]
                resolutions.append({"attempt_id": pending.attempt_id, "outcome": "RETURNED", "route_id": route.route_id, "route_length": age, "classification": route.classification})
                continue
            if age >= 4:
                if pending_receipt:
                    pending_receipt.resolve_step, pending_receipt.resolved_outcome, pending_receipt.route_length = step, "DURABLE_DEPARTURE", age
                self._record_raw_outcome(self._branch_by_id(pending.entry_branch_id), "DURABLE_DEPARTURE")
                self.late_route_watches.append(LateRouteWatch(pending, step, pending.source_step + 8))
                self.late_route_watches.sort(key=lambda item: (item.expires_step, item.route.attempt_id))
                self.late_route_watches = self.late_route_watches[:self.max_late_route_watches]
                resolutions.append({"attempt_id": pending.attempt_id, "outcome": "DURABLE_DEPARTURE", "route_length": age, "entry_intent": pending.entry_intent})
                continue
            retained.append(pending)
        self.pending_routes = retained
        self._evict_closed_routes(step)

        late_retained: list[LateRouteWatch] = []
        for watch in self.late_route_watches:
            pending = watch.route
            age = step - pending.source_step
            if visual_match(pending.source_descriptor, after_desc) and 5 <= age <= 8:
                pending_receipt = self._receipt(pending.attempt_id)
                if pending_receipt:
                    pending_receipt.resolve_step, pending_receipt.resolved_outcome, pending_receipt.route_length = step, "LATE_RETURN", age
                branch_item = self._branch_by_id(pending.entry_branch_id)
                if branch_item:
                    branch_item.raw_durable_count = _sat(branch_item.raw_durable_count - 1)
                self.raw_outcome_counts["DURABLE_DEPARTURE"] = max(0, self.raw_outcome_counts.get("DURABLE_DEPARTURE", 0) - 1)
                self._record_raw_outcome(branch_item, "LATE_RETURN")
                resolutions.append({"attempt_id": pending.attempt_id, "outcome": "LATE_RETURN", "route_length": age, "revised_durable_step": watch.durable_step})
            elif step < watch.expires_step:
                late_retained.append(watch)
        self.late_route_watches = late_retained[-self.max_late_route_watches:]

        confirmations: list[tuple[list[ClosedRouteRecord], str, list[str]]] = []
        for route in closed_now:
            confirmations.extend(self._confirm_routes(route, step))

        post_retained: list[PostReturnWatch] = []
        for watch in self.post_return_watches:
            route = next((item for item in self.closed_routes if item.route_id == watch.route_id), None)
            if route is None or step > watch.expires_step:
                continue
            if step - watch.return_step <= 2 and visual_match(watch.source_descriptor, before_desc):
                _, _, _, _, current_bad, _ = self._branch_values(branch.branch_id, step)
                if branch.branch_key == watch.entry_branch_key or current_bad >= .55:
                    watch.candidate_attempt_ids.append(attempt_id)
                    watch.candidate_attempt_ids = watch.candidate_attempt_ids[-2:]
            confirmed = False
            for candidate_attempt in watch.candidate_attempt_ids:
                item = self._receipt(candidate_attempt)
                if item and item.resolved_outcome in {"NO_PROGRESS_EXACT", "NO_PROGRESS_NEGLIGIBLE", "CONFIRMED_ADVERSE_RETURN", "LATE_CONFIRMED_ADVERSE_RETURN", "RETURNED", "LATE_RETURN"}:
                    gain = max((anchor.confidence - watch.base_anchor_confidences[index] for index, anchor in enumerate(self.anchors)), default=0.0)
                    if gain < .10 and (self.phase_id, self.item_open_mask(), self.constraint_mask()) == (watch.phase_id, watch.item_open_mask, watch.constraint_mask):
                        confirmations.append(([route], "post_return_reversion", [route.support_receipt_ids[0], candidate_attempt]))
                        confirmed = True
                        break
            if not confirmed:
                post_retained.append(watch)
        post_retained.sort(key=lambda item: (item.expires_step, item.route_id))
        self.post_return_watches = post_retained[:self.max_post_return_watches]

        enqueued: list[str] = []
        for routes, path, supports in confirmations:
            if all(item.confirmation_step is not None and item.confirmation_path == path for item in routes):
                continue
            self._mark_confirmed(routes, path, supports, step)
            evidence, contraction, workflow = self._route_evidence(routes, path, step)
            if evidence >= .75:
                source_route = routes[-1]
                candidate = self._make_candidate("CONFIRMED_ROUTE_TRAP", step, source_route.source_frontier_id, source_route.source_descriptor, supports, evidence, contraction, max(item.anchor_gain for item in routes), workflow, {"route_ids": [item.route_id for item in routes], "branch_ids": [item.entry_branch_id for item in routes], "confirmation_path": path, "route_core_occurrences": len(routes)})
                if self._enqueue(candidate):
                    enqueued.append(candidate.trigger_id)

        self._refresh_branches(step)
        new_item = self.item_open_mask()
        phase_switch = old_item != new_item
        if self.commit_phase_watch is not None:
            watch = self.commit_phase_watch
            if not visual_match(watch.source_descriptor, after_desc):
                watch.left_source = True
            elif watch.left_source:
                self.commit_phase_watch = None
            if self.commit_phase_watch is not None and step - watch.source_step >= 4:
                phase_switch = phase_switch or watch.left_source
                self.commit_phase_watch = None
        if not any(item.role != "CONSTRAINT" for item in self.anchors) and intent == "COMMIT" and outcome == "LOCAL_VISIBLE_CHANGE":
            self.commit_phase_watch = CommitPhaseWatch(step, before_desc)
        if phase_switch:
            self._switch_phase(step, old_item, new_item)

        n, r, _, _, bad, _ = self._branch_values(branch.branch_id, step)
        gain = max((item.confidence - source.anchor_confidence_at_first_visit[index] for index, item in enumerate(self.anchors) if source.item_open_mask & (1 << index)), default=0.0)
        retry_exempt = self._retry_exempt(branch, action, before_desc, step, gain)
        if not phase_switch and (n >= 1.70 or (n >= .85 and r >= 1.0)) and bad >= .55 and gain < .15 and not retry_exempt:
            supports = [item.attempt_id for item in self.attempt_receipts if item.branch_id == branch.branch_id and (item.resolved_outcome.startswith("NO_PROGRESS") or item.resolved_outcome == "CONFIRMED_ADVERSE_RETURN")][-4:]
            if len(set(supports)) >= 2:
                candidate = self._make_candidate("BAD_BRANCH_REPEAT", step, source.frontier_id, before_desc, supports, bad, 1.0, gain, 0.0, {"branch": branch.label, "branch_ids": [branch.branch_id], "count": len(supports)})
                if self._enqueue(candidate):
                    enqueued.append(candidate.trigger_id)

        window_receipts = [item for item in self.attempt_receipts if item.frontier_id == source.frontier_id and step - 7 <= item.source_step <= step and item.resolved_outcome != "DEPARTURE_PENDING"]
        visits = len([item for item in source.recent_visit_steps if step - 7 <= item <= step])
        adverse = sum(1.0 if item.resolved_outcome.startswith("NO_PROGRESS") or item.resolved_outcome == "CONFIRMED_ADVERSE_RETURN" else .75 if item.resolved_outcome == "LATE_CONFIRMED_ADVERSE_RETURN" else 0.0 for item in window_receipts)
        branch_keys = [item.branch_key for item in window_receipts]
        unique = len(set(branch_keys))
        pmax = max((branch_keys.count(key) / len(branch_keys) for key in set(branch_keys)), default=0.0)
        contraction = .5 * pmax + .5 * (1 - min(1.0, max(0, unique - 1) / 3))
        last_two_repeated = len(branch_keys) >= 3 and all(key in branch_keys[:index] for index, key in ((len(branch_keys)-2, branch_keys[-2]), (len(branch_keys)-1, branch_keys[-1])))
        trusted_escape = any(item.escape_confidence >= .55 and item.raw_durable_count >= 1 for item in source.branches.values())
        trusted_bad = any(item.failure_confidence >= .55 and (item.raw_no_progress_count >= 2 or item.confirmed_adverse_return_count >= 2 or (item.raw_no_progress_count and item.confirmed_adverse_return_count)) for item in source.branches.values())
        confirmed_core = any(sum(1 for other in self.closed_routes if other.route_core_signature == route.route_core_signature and other.confirmation_step is not None) >= 2 for route in self.closed_routes if route.source_frontier_id == source.frontier_id)
        workflow = max((item.residual_work_credit for item in window_receipts if item.resolved_outcome.startswith("NO_PROGRESS") or "CONFIRMED" in item.resolved_outcome), default=0.0)
        if not phase_switch and visits >= 4 and len(window_receipts) >= 3 and adverse >= 2.5 and unique <= 2 and contraction >= .55 and last_two_repeated and not trusted_escape and not any(item.source_frontier_id == source.frontier_id for item in self.pending_routes) and gain < .15 and workflow < .35 and (trusted_bad or confirmed_core):
            supports = [item.attempt_id for item in window_receipts if item.resolved_outcome.startswith("NO_PROGRESS") or "CONFIRMED" in item.resolved_outcome][-4:]
            candidate = self._make_candidate("CONTRACTED_FRONTIER", step, source.frontier_id, before_desc, supports, min(1.0, adverse / 3), contraction, gain, workflow, {"visits": visits, "adverse": adverse, "branch_ids": list(dict.fromkeys(item.branch_id for item in window_receipts))[:2]})
            if self._enqueue(candidate):
                enqueued.append(candidate.trigger_id)

        if action.get("type") == "type_text":
            normalized_typed = _anchor_norm(action.get("text") or "")
            key = sha256(normalized_typed.encode()).hexdigest()
            record = self.typed_value_records.get(key)
            prior = next((item for item in reversed(record.occurrences if record else []) if step - item.source_step <= 12 and (item.phase_id, item.item_open_mask, item.constraint_mask) == (self.phase_id, old_item, old_constraint) and visual_match(item.source_descriptor, before_desc)), None)
            clear_between = bool(prior) and any(prior.source_step < clear_step <= step for clear_step in self._recent_clear_steps)
            prior_receipt = self._receipt(prior.attempt_id) if prior else None
            prior_gain = max((item.confidence - prior.base_confidences[index] for index, item in enumerate(self.anchors)), default=0.0) if prior else 0.0
            bad_prior = bool(prior and prior_receipt and (prior_receipt.resolved_outcome in {"NO_PROGRESS_EXACT", "NO_PROGRESS_NEGLIGIBLE", "CONFIRMED_ADVERSE_RETURN", "LATE_CONFIRMED_ADVERSE_RETURN"} or (prior.reentered_source and prior_gain < .15)) and (not clear_between or prior.frontier_id == source.frontier_id))
            if bad_prior and not phase_switch:
                evidence = max(.65, self._branch_values(prior.branch_id, step)[4] if prior else 0.0)
                candidate = self._make_candidate("VALUE_REENTRY_AFTER_BAD_OUTCOME", step, source.frontier_id, before_desc, [prior.attempt_id, attempt_id], evidence, .70, gain, 0.0, {"branch_ids": [prior.branch_id, branch.branch_id]})
                if self._enqueue(candidate):
                    enqueued.append(candidate.trigger_id)
            occurrence = TypedOccurrence(step, self.phase_id, old_item, old_constraint, source.frontier_id, before_desc, attempt_id, branch.branch_id, start_conf, outcome)
            if record is None:
                record = TypedValueRecord(key, len(normalized_typed), [])
                self.typed_value_records[key] = record
            record.occurrences.append(occurrence)
            record.occurrences = record.occurrences[-2:]
            while len(self.typed_value_records) > self.max_typed_value_keys:
                victim = min(self.typed_value_records, key=lambda item: (self.typed_value_records[item].occurrences[-1].source_step, item))
                del self.typed_value_records[victim]
        for record in self.typed_value_records.values():
            for occurrence in record.occurrences:
                if occurrence.source_step >= step:
                    continue
                if occurrence.frontier_id != source.frontier_id:
                    occurrence.left_source = True
                elif occurrence.left_source:
                    occurrence.reentered_source = True
                occurrence_receipt = self._receipt(occurrence.attempt_id)
                if occurrence_receipt:
                    occurrence.outcome = occurrence_receipt.resolved_outcome

        commit_gains = [(index, item, item.confidence - start_conf[index]) for index, item in enumerate(self.anchors) if item.role != "CONSTRAINT" and target_mask & (1 << index) and item.confidence - start_conf[index] >= .20]
        if intent == "COMMIT" and len([item for item in self.anchors if item.role != "CONSTRAINT"]) >= 2 and commit_gains:
            gained_index, gained_anchor, _ = max(commit_gains, key=lambda item: (item[2], -item[0]))
            remaining = new_item & ~(1 << gained_index)
            if remaining:
                self.escape_watches.append(EscapeWatch(step, source.frontier_id, gained_anchor.anchor_id, remaining, before_desc, tuple(item.confidence for item in self.anchors)))
                self.escape_watches = self.escape_watches[-self.max_escape_watches:]
        escape_retained: list[EscapeWatch] = []
        for watch in self.escape_watches:
            if watch.source_step == step:
                escape_retained.append(watch)
                continue
            age = step - watch.source_step
            if age > 4 or visual_match(watch.source_descriptor, after_desc):
                continue
            watch.offscreen_count += 1
            open_gain = max((item.confidence - watch.base_confidences[index] for index, item in enumerate(self.anchors) if watch.remaining_open_mask & (1 << index)), default=0.0)
            if open_gain < .10 and watch.offscreen_count >= 2 and not phase_switch:
                anchor = next((item for item in self.anchors if item.anchor_id == watch.anchor_id), None)
                support_ids = [item.attempt_id for item in self.attempt_receipts if watch.source_step <= item.source_step <= step][-2:]
                evidence = min(1.0, .65 + min(.20, max(0.0, (anchor.confidence if anchor else 0.0))) + .10 * max(0, watch.offscreen_count - 2))
                destination, _ = self._frontier(after_desc, self.phase_id, self.item_open_mask(), self.constraint_mask(), step + 1)
                candidate = self._make_candidate("PARTIAL_OBLIGATION_ESCAPE", step, destination.frontier_id, after_desc, support_ids, evidence, .75, open_gain, 0.0, {"anchor": anchor.literal if anchor else "an item"}, expiry=6)
                if self._enqueue(candidate):
                    enqueued.append(candidate.trigger_id)
            elif age < 4 and open_gain < .10:
                escape_retained.append(watch)
        self.escape_watches = escape_retained[-self.max_escape_watches:]

        self._refresh_anchors(step)
        self._refresh_branches(step)
        destination, _ = self._frontier(after_desc, self.phase_id, self.item_open_mask(), self.constraint_mask(), step + 1)
        self._evict_branches(source, step)
        self._evict_frontiers(step, destination.frontier_id)
        self._evict_triggers(step)
        self._update_post_read_audit(
            step=step,
            branch=branch,
            branch_created=branch_created,
            after_descriptor=after_desc,
        )
        self.last_observed_step = step
        self.max_observed_frontiers = max(self.max_observed_frontiers, len(self.frontiers))
        self.max_observed_branches = max(self.max_observed_branches, sum(len(item.branches) for item in self.frontiers.values()))
        self.max_observed_receipts = max(self.max_observed_receipts, len(self.attempt_receipts))
        written = bool(source_created or branch_created or outcome != "DEPARTURE_PENDING" or events or resolutions or confirmations or enqueued or phase_switch)
        if written:
            self.write_success_count += 1
        return {"written": written, "source_step": step, "source_frontier_id": source.frontier_id, "destination_frontier_id": destination.frontier_id, "branch_id": branch.branch_id, "immediate_outcome": outcome, "changed_pixel_fraction": changed, "route_resolutions": resolutions, "route_confirmations": [{"path": path, "route_ids": [item.route_id for item in routes], "support_receipt_ids": supports} for routes, path, supports in confirmations], "anchor_events": [{"anchor_id": anchor_id, "event_kind": event_kind} for anchor_id, event_kind in events], "phase_switch": phase_switch, "phase_id_after": self.phase_id, "trigger_ids_enqueued": enqueued, "candidate_ids_enqueued": list(enqueued)}

    def _retry_exempt(self, branch: BranchRecord, action: dict[str, Any], before: VisualDescriptor, step: int, gain: float) -> bool:
        if branch.intent_class == "WAIT" and branch.raw_no_progress_count < 3:
            return True
        if action.get("type") == "type_text" and action.get("clear_text"):
            return True
        if any(step - item <= 2 for item in self._recent_clear_steps):
            return True
        prior = [item for item in self.attempt_receipts if item.branch_id == branch.branch_id and item.source_step < step]
        if prior:
            receipt = prior[-1]
            if receipt.target_anchor_mask != branch.target_anchor_mask or receipt.resolved_outcome == "DEPARTURE_PENDING" or receipt.anchor_gain >= .10:
                return True
            if receipt.source_exact_sha256 != before.exact_sha256:
                return True
        return False

    def _evict_branches(self, frontier: FrontierRecord, step: int) -> None:
        while len(frontier.branches) > self.max_branches_per_frontier:
            victim = min(frontier.branches.items(), key=lambda pair: (2 * self._branch_values(pair[1].branch_id, step)[4] + self._branch_values(pair[1].branch_id, step)[5] + .5 * bool(pair[1].target_anchor_mask & (self.item_open_mask() | self.constraint_mask())) + math.exp(-max(0, step - pair[1].last_step) / 8), pair[1].last_step, pair[1].branch_id))[0]
            del frontier.branches[victim]
            self.branch_eviction_count += 1

    def _evict_frontiers(self, step: int, current: str) -> None:
        while len(self.frontiers) > self.max_frontiers:
            # All long-lived evidence embeds its descriptor and branch key, so
            # only the current frontier must be pinned.
            protected = {current}
            eligible = [(key, item) for key, item in self.frontiers.items() if key not in protected]
            if not eligible:
                raise A11IntegrityError("frontier capacity exhausted by protected evidence")
            victim = min(eligible, key=lambda pair: (3 * (pair[0] == current) + math.exp(-max(0, step - pair[1].last_visit_step) / 12), pair[1].last_visit_step, pair[0]))[0]
            del self.frontiers[victim]
            self.frontier_eviction_count += 1

    def _evict_triggers(self, step: int) -> None:
        bonus = {"PARTIAL_OBLIGATION_ESCAPE": .25, "CONFIRMED_ROUTE_TRAP": .20, "BAD_BRANCH_REPEAT": .15, "VALUE_REENTRY_AFTER_BAD_OUTCOME": .10, "CONTRACTED_FRONTIER": .05}
        while len(self.trigger_candidates) > self.max_trigger_candidates:
            provisional = [item for item in self.trigger_candidates if item.state == "PROVISIONAL"]
            pool = provisional or self.trigger_candidates
            victim = min(pool, key=lambda item: (item.evidence_strength + item.contraction_confidence + self._obligation_relevance() + math.exp(-max(0, step - item.maturity_step) / 8) + bonus[item.kind], item.maturity_step, item.trigger_id))
            self.trigger_candidates.remove(victim)
            self.trigger_eviction_count += 1

    def audit_record(self) -> dict[str, Any]:
        frontiers = []
        for frontier in self.frontiers.values():
            value = asdict(frontier)
            value["visual_exemplars"] = [_descriptor_audit(item) for item in frontier.visual_exemplars]
            frontiers.append(value)
        def route_audit(route: ClosedRouteRecord) -> dict[str, Any]:
            value = asdict(route)
            value["source_descriptor"] = _descriptor_audit(route.source_descriptor)
            return value
        def pending_audit(pending: PendingRoute) -> dict[str, Any]:
            return {
                "attempt_id": pending.attempt_id,
                "source_step": pending.source_step,
                "source_frontier_id": pending.source_frontier_id,
                "entry_branch_id": pending.entry_branch_id,
                "entry_branch_key_sha256": sha256(pending.entry_branch_key.encode()).hexdigest(),
                "entry_intent": pending.entry_intent,
                "phase_id": pending.phase_id,
                "item_open_mask": pending.item_open_mask,
                "constraint_mask": pending.constraint_mask,
                "source_descriptor": _descriptor_audit(pending.source_descriptor),
                "entry_target_mask": pending.entry_target_mask,
                "route_hop_count": len(pending.route_hops),
                "route_hop_digests": [
                    sha256(json.dumps(asdict(hop), sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:16]
                    for hop in pending.route_hops
                ],
                "max_anchor_gain": pending.max_anchor_gain,
                "phase_masks_unchanged": pending.phase_masks_unchanged,
                "route_target_mask": pending.route_target_mask,
            }
        def post_watch_audit(watch: PostReturnWatch) -> dict[str, Any]:
            return {
                "route_id": watch.route_id,
                "return_step": watch.return_step,
                "source_frontier_id": watch.source_frontier_id,
                "source_descriptor": _descriptor_audit(watch.source_descriptor),
                "entry_branch_key_sha256": sha256(watch.entry_branch_key.encode()).hexdigest(),
                "phase_id": watch.phase_id,
                "item_open_mask": watch.item_open_mask,
                "constraint_mask": watch.constraint_mask,
                "candidate_attempt_ids": watch.candidate_attempt_ids,
                "expires_step": watch.expires_step,
            }
        candidates = []
        for candidate in self.trigger_candidates:
            value = asdict(candidate)
            value["expected_descriptor"] = _descriptor_audit(candidate.expected_descriptor)
            candidates.append(value)
        # Full raw evidence remains available in the bounded runtime objects and
        # hashed receipts.  The audit is intentionally a compact provenance
        # projection so every simultaneous legal capacity state stays <=128KiB.
        compact_frontiers = [
            {
                "frontier_id": item["frontier_id"],
                "phase_id": item["phase_id"],
                "item_open_mask": item["item_open_mask"],
                "constraint_mask": item["constraint_mask"],
                "first_step": item["first_step"],
                "last_visit_step": item["last_visit_step"],
                "visit_count": item["visit_count"],
                "visual_exemplar_sha256s": [entry["exact_sha256"] for entry in item["visual_exemplars"]],
                "branches": [
                    {
                        "branch_id": branch["branch_id"],
                        "branch_key_sha256": sha256(str(branch["branch_key"]).encode()).hexdigest(),
                        "intent_class": branch["intent_class"],
                        "target_anchor_mask": branch["target_anchor_mask"],
                        "attempt_count": branch["attempt_count"],
                        "raw_no_progress_count": branch["raw_no_progress_count"],
                        "confirmed_adverse_return_count": branch["confirmed_adverse_return_count"],
                        "failure_confidence": branch["failure_confidence"],
                        "escape_confidence": branch["escape_confidence"],
                    }
                    for branch in item["branches"].values()
                ],
            }
            for item in frontiers
        ]
        compact_receipts = [
            {
                "attempt_id": item.attempt_id,
                "source_step": item.source_step,
                "resolve_step": item.resolve_step,
                "frontier_id": item.frontier_id,
                "branch_id": item.branch_id,
                "phase_id": item.phase_id,
                "resolved_outcome": item.resolved_outcome,
                "route_length": item.route_length,
                "anchor_gain": item.anchor_gain,
                "residual_work_credit": item.residual_work_credit,
                "source_exact_sha256": item.source_exact_sha256,
                "destination_exact_sha256": item.destination_exact_sha256,
            }
            for item in self.attempt_receipts
        ]
        compact_candidates = [
            {
                "trigger_id": item["trigger_id"], "kind": item["kind"], "state": item["state"],
                "created_step": item["created_step"], "maturity_step": item["maturity_step"],
                "expires_step": item["expires_step"], "query_frontier_id": item["query_frontier_id"],
                "support_count": item["support_count"], "support_receipt_ids": item["support_receipt_ids"],
                "evidence_strength": item["evidence_strength"], "contraction_confidence": item["contraction_confidence"],
                "evidence_signature": item["evidence_signature"], "expected_exact_sha256": item["expected_descriptor"]["exact_sha256"],
            }
            for item in candidates
        ]
        record: dict[str, Any] = {
            "schema": AUDIT_SCHEMA, "mechanism_id": self.mechanism_id, "experiment_id": self.experiment_id,
            "parameters": {"max_anchors": self.max_anchors, "max_anchor_events": self.max_anchor_events, "max_frontiers": self.max_frontiers, "max_visual_exemplars": self.max_visual_exemplars, "max_branches_per_frontier": self.max_branches_per_frontier, "max_attempt_receipts": self.max_attempt_receipts, "max_pending_routes": self.max_pending_routes, "max_closed_routes": self.max_closed_routes, "max_post_return_watches": self.max_post_return_watches, "max_late_route_watches": self.max_late_route_watches, "max_escape_watches": self.max_escape_watches, "max_typed_value_keys": self.max_typed_value_keys, "max_trigger_candidates": self.max_trigger_candidates, "max_nonempty_reads": self.max_nonempty_reads, "max_reads_per_phase": self.max_reads_per_phase, "read_cooldown_steps": self.read_cooldown_steps, "retrieval_score_threshold": self.retrieval_score_threshold, "near": {"dl": .05, "de": .10, "dv": .045}, "route_horizons": {"return": 4, "late_return": 8, "recurrence": 12}},
            "decision_boundary": {"allowed_inputs": ["goal", "before.pixels", "after.pixels", "canonical_action", "action_summary", "source_step"], "ignored_snapshot_fields": ["evaluator_reward", "task_success", "ui_tree", "accessibility", "foreground", "activity", "package", "database_state", "transition"], "model_calls_added": 0, "evaluator_used_for_decision": False, "hidden_ui_used_for_decision": False, "future_information_used": False, "guard_enabled": False, "action_override_count": 0, "forced_termination_count": 0},
            "goal": {"goal_sha256": self.goal_sha256, "operation_class": self.operation_class, "anchor_count": len(self.anchors), "item_anchor_count": sum(item.role == "ITEM" for item in self.anchors), "value_anchor_count": sum(item.role == "VALUE" for item in self.anchors), "constraint_anchor_count": sum(item.role == "CONSTRAINT" for item in self.anchors), "anchors": [asdict(item) for item in self.anchors]},
            "phase": {"current_phase_id": self.phase_id, "item_open_mask": self.item_open_mask(), "constraint_mask": self.constraint_mask(), "phase_switch_count": self.phase_switch_count, "phase_switch_events": self.phase_switch_events},
            "frontiers": {"current_count": len(frontiers), "maximum_observed": self.max_observed_frontiers, "merge_count": self.frontier_merge_count, "eviction_count": self.frontier_eviction_count, "records": compact_frontiers},
            "branches": {"current_count": sum(len(item.branches) for item in self.frontiers.values()), "maximum_observed": self.max_observed_branches, "eviction_count": self.branch_eviction_count},
            "attempts": {"retained_count": len(self.attempt_receipts), "raw_outcome_counts": self.raw_outcome_counts, "receipts": compact_receipts},
            "routes": {"pending_count": len(self.pending_routes), "pending_records": [pending_audit(item) for item in self.pending_routes], "late_watch_count": len(self.late_route_watches), "late_watches": [{"durable_step": item.durable_step, "expires_step": item.expires_step, "attempt_id": item.route.attempt_id, "source_frontier_id": item.route.source_frontier_id, "source_descriptor": _descriptor_audit(item.route.source_descriptor)} for item in self.late_route_watches], "closed_count": len(self.closed_routes), "post_return_watch_count": len(self.post_return_watches), "post_return_watches": [post_watch_audit(item) for item in self.post_return_watches], "classification_counts": self.route_classification_counts, "confirmation_counts": self.route_confirmation_counts, "eviction_count": self.route_eviction_count, "records": [route_audit(item) for item in self.closed_routes]},
            "watches": {"escape_watches": [{"source_step": item.source_step, "source_frontier_id": item.source_frontier_id, "anchor_id": item.anchor_id, "remaining_open_mask": item.remaining_open_mask, "source_descriptor": _descriptor_audit(item.source_descriptor), "offscreen_count": item.offscreen_count} for item in self.escape_watches], "commit_phase_watch": ({"source_step": self.commit_phase_watch.source_step, "source_descriptor": _descriptor_audit(self.commit_phase_watch.source_descriptor), "left_source": self.commit_phase_watch.left_source} if self.commit_phase_watch else None), "typed_value_records": {key: {"value_sha256": value.value_sha256, "normalized_length": value.normalized_length, "occurrences": [{"source_step": item.source_step, "phase_id": item.phase_id, "item_open_mask": item.item_open_mask, "constraint_mask": item.constraint_mask, "frontier_id": item.frontier_id, "source_descriptor": _descriptor_audit(item.source_descriptor), "attempt_id": item.attempt_id, "branch_id": item.branch_id, "outcome": item.outcome, "left_source": item.left_source, "reentered_source": item.reentered_source} for item in value.occurrences]} for key, value in self.typed_value_records.items()}},
            "triggers": {"candidate_count": len(candidates), "mature_count": sum(item.state == "MATURE" for item in self.trigger_candidates), "delivered_count": sum(item.state == "DELIVERED" for item in self.trigger_candidates), "invalidated_count": self.invalidated_trigger_count, "expired_count": self.expired_trigger_count, "duplicate_suppressed_count": self.duplicate_suppressed_count, "created_counts_by_kind": self.created_counts_by_kind, "delivered_counts_by_kind": self.delivered_counts_by_kind, "candidates": compact_candidates},
            "reads": {"read_count": self.read_count, "nonempty_read_count": self.nonempty_read_count, "last_nonempty_read_step": self.last_nonempty_read_step, "delivered_signatures": self.delivered_signatures, "read_events": self.read_events},
            "capacity": {"max_rendered_chars": self.max_rendered_chars, "max_rendered_utf8_bytes": self.max_rendered_utf8_bytes, "max_rendered_tokens": None, "serialized_audit_bytes": 0},
            "write_attempt_count": self.write_attempt_count, "write_success_count": self.write_success_count,
            "model_calls_added": 0, "guard_enabled": False, "action_override_count": 0, "forced_termination_count": 0,
        }
        record["causal_boundary"] = dict(record["decision_boundary"])
        record = _round_floats(record)
        previous = -1
        while previous != record["capacity"]["serialized_audit_bytes"]:
            previous = record["capacity"]["serialized_audit_bytes"]
            record["capacity"]["serialized_audit_bytes"] = len(json.dumps(record, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        return record


__all__ = [
    "AUDIT_SCHEMA", "EXPERIMENT_ID", "MECHANISM_ID", "A11IntegrityError",
    "A11VisibleInputError", "ConfirmedRouteContractionECOBFMemory", "GoalAnchor",
    "extract_goal_anchors", "target_anchor_mask", "classify_operation", "classify_intent",
    "describe_visual_state", "canonical_action_family",
]
